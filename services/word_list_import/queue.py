"""Word-upload work queue (ADR-069, wiki/features/word-upload-queue.tech.md).

A learner's uploaded words land in ``word_upload_queue`` as raw text. No LLM
runs in the web process: the operator builds the missing assets offline with
the authoring skills (``scripts/word_upload_queue.py export`` writes the
worklists), and :func:`advance` moves each row along as its assets appear.

Row lifecycle::

    pending  --resolve-->  building  --all assets present-->  done
       |                      |
       +--------> failed <----+          (cancelled: operator only)

``resolve`` tokenises the word with the language's processor (local, no LLM)
and looks the lemma up in ``dim_vocabulary``. The web process only ever looks
up; creating a ``dim_vocabulary`` row from learner input is left to the
operator run (``create_vocab=True``), so nothing a learner types reaches the
shared dictionary before the operator has seen it.

The asset checklist (``ASSET_KEYS``, in build order) for a word's primary
sense (lowest-rank native ``standard`` row):

    vocab          dim_vocabulary row exists
    sense          native ``standard`` and ``simple`` rows at that rank
    embedding      the native standard row has its vector
    pronunciation  zh / ja only: the native standard row has ``pronunciation``
    gloss          when ``gloss_language_id`` is set: ``simple`` + ``standard``
                   rows in that language at the same rank
    core           a valid ``prompt1_core`` ``word_assets`` row
    exercises      at least one active ``exercises`` row
    audio          every active audio-bearing exercise has its audio URL

A row is ``done`` when the list is empty. Finishing it writes the learner's
``user_word_watchlist`` row (skipped if they already watch the sense) and runs
the immediate test-match sweep for it. The claim is a conditional update
(``status = 'building'`` -> ``'done'``), so two schedulers finishing the same
row cannot both write a watchlist row.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

TABLE = 'word_upload_queue'

STATUS_PENDING = 'pending'
STATUS_BUILDING = 'building'
STATUS_DONE = 'done'
STATUS_FAILED = 'failed'
STATUS_CANCELLED = 'cancelled'
OPEN_STATUSES = (STATUS_PENDING, STATUS_BUILDING)

ASSET_VOCAB = 'vocab'
ASSET_SENSE = 'sense'
ASSET_EMBEDDING = 'embedding'
ASSET_PRONUNCIATION = 'pronunciation'
ASSET_GLOSS = 'gloss'
ASSET_CORE = 'core'
ASSET_EXERCISES = 'exercises'
ASSET_AUDIO = 'audio'
ASSET_KEYS = (
    ASSET_VOCAB, ASSET_SENSE, ASSET_EMBEDDING, ASSET_PRONUNCIATION,
    ASSET_GLOSS, ASSET_CORE, ASSET_EXERCISES, ASSET_AUDIO,
)

#: Languages whose senses carry a stored pronunciation
#: (scripts/backfill_pronunciations.py: zh pinyin, ja kana).
PRONUNCIATION_LANGUAGE_IDS = frozenset({1, 3})
ENGLISH_ID = 2

#: Audio-bearing exercise types and where each keeps its URL. Mirrors
#: scripts/backfill_exercise_audio.py (AUDIO_TYPES / AUDIO_URL_FIELDS), the
#: script that fills them; keep the two in step.
AUDIO_URL_FIELDS = {
    'phonetic_recognition': 'audio_url',
    'listening_flashcard': 'front_audio_url',
}

_CHUNK = 200


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _chunks(values: list, size: int = _CHUNK):
    for i in range(0, len(values), size):
        yield values[i:i + size]


# ---------------------------------------------------------------------------
# Enqueue (web request)
# ---------------------------------------------------------------------------

def gloss_language_for(db, user_id: str, language_id: int) -> Optional[int]:
    """Language the word's gloss is written in: the learner's native language,
    English when it is unset, ``None`` when that is the word's own language."""
    native = None
    try:
        rows = (db.table('users').select('native_language_id')
                .eq('id', user_id).limit(1).execute().data or [])
        if rows:
            native = rows[0].get('native_language_id')
    except Exception as exc:
        logger.debug('native language lookup failed for %s: %s', user_id, exc)
    target = native or ENGLISH_ID
    return None if target == language_id else int(target)


def enqueue_words(db, user_id: str, language_id: int, words: list[str],
                  upload_batch_id: str, gloss_language_id: Optional[int]) -> int:
    """Insert one ``pending`` row per word; a word this learner already queued
    for this language is left as it is. Returns the number of new rows."""
    if not words:
        return 0
    now = _now()
    rows = [{
        'user_id': user_id,
        'upload_batch_id': upload_batch_id,
        'language_id': language_id,
        'raw_word': word,
        'gloss_language_id': gloss_language_id,
        'status': STATUS_PENDING,
        'missing': [],
        'requested_at': now,
        'updated_at': now,
    } for word in words]
    resp = (db.table(TABLE)
            .upsert(rows, on_conflict='user_id,language_id,raw_word',
                    ignore_duplicates=True)
            .execute())
    return len(resp.data or [])


def count_recent_queue_batches(db, user_id: str, since_iso: str) -> int:
    """Distinct upload batches this learner queued since ``since_iso``.
    Best effort: 0 when the lookup fails."""
    try:
        rows = (db.table(TABLE).select('upload_batch_id')
                .eq('user_id', user_id).gte('requested_at', since_iso)
                .execute().data or [])
        return len({r.get('upload_batch_id') for r in rows if r.get('upload_batch_id')})
    except Exception as exc:
        logger.debug('recent queue batch lookup failed: %s', exc)
        return 0


def open_rows_for_user(db, user_id: str) -> list[dict]:
    """The learner's queue rows that are not ``done`` (done words appear as
    watchlist rows instead)."""
    return (db.table(TABLE)
            .select('id, raw_word, language_id, upload_batch_id, status, missing, '
                    'requested_at, updated_at')
            .eq('user_id', user_id)
            .in_('status', [STATUS_PENDING, STATUS_BUILDING, STATUS_FAILED])
            .order('requested_at', desc=True)
            .limit(500)
            .execute().data or [])


# ---------------------------------------------------------------------------
# Resolve (no LLM)
# ---------------------------------------------------------------------------

class _Tokenizer:
    """One processor pipeline per run; tokenising needs no DB or LLM."""

    def __init__(self):
        self._pipeline = None

    #: Japanese inflection tails a learner types after a verb or adjective
    #: (食べた, 走ります, 美しかった). UniDic splits them off as auxiliaries, and
    #: the shared resolver would then store the compound lemma '食べる た'.
    _JA_TAIL_POS = frozenset({'助動詞'})

    def lemma_item(self, word: str, language_code: str) -> dict:
        from services.vocabulary.pipeline import VocabularyExtractionPipeline
        from services.vocabulary.word_resolver import _tokenize_single_word
        if self._pipeline is None:
            self._pipeline = VocabularyExtractionPipeline(openai_client=None, db_client=None)
        if language_code == 'ja':
            tokens = self._pipeline.get_processor('ja').extract_lemma_tokens(word)
            while len(tokens) > 1 and tokens[-1].pos in self._JA_TAIL_POS:
                tokens = tokens[:-1]
            if len(tokens) == 1:
                t = tokens[0]
                return {'lemma': t.lemma, 'pos': t.pos, 'is_phrase': False,
                        'phrase_type': None, 'components': None,
                        'reading': t.reading or ''}
        return _tokenize_single_word(word, language_code, self._pipeline)


def _lookup_vocab_id(db, lemma: str, language_id: int) -> Optional[int]:
    rows = (db.table('dim_vocabulary').select('id')
            .eq('lemma', lemma).eq('language_id', language_id)
            .limit(1).execute().data or [])
    return rows[0]['id'] if rows else None


def primary_senses(db, vocab_ids: list[int], language_id: int) -> dict[int, dict]:
    """vocab_id -> its lowest-rank native ``standard`` row
    ``{id, sense_rank, source, pronunciation}``."""
    out: dict[int, dict] = {}
    for chunk in _chunks(sorted(set(vocab_ids))):
        rows = (db.table('dim_word_senses')
                .select('id, vocab_id, sense_rank, source, pronunciation')
                .in_('vocab_id', chunk)
                .eq('definition_language_id', language_id)
                .eq('definition_level', 'standard')
                .order('sense_rank')
                .execute().data or [])
        for row in rows:
            current = out.get(row['vocab_id'])
            if current is None or row['sense_rank'] < current['sense_rank']:
                out[row['vocab_id']] = row
    return out


def resolve_rows(db, rows: list[dict], *, create_vocab: bool = False,
                 tokenizer: Optional[_Tokenizer] = None) -> None:
    """Fill ``vocab_id`` (and ``lemma`` in ``detail``) on ``pending`` rows, in
    place. A row whose word has no ``dim_vocabulary`` row stays ``pending``
    with ``missing = ['vocab']`` unless ``create_vocab``; one that cannot be
    tokenised is marked ``failed``. Writes each changed row."""
    from services import language_registry
    from services.vocabulary.word_resolver import get_or_create_vocab_id

    tokenizer = tokenizer or _Tokenizer()
    for row in rows:
        if row.get('status') != STATUS_PENDING or row.get('vocab_id'):
            continue
        language_id = row['language_id']
        code = language_registry.code_of(language_id)
        try:
            item = tokenizer.lemma_item(row['raw_word'], code)
        except Exception as exc:
            _write(db, row, status=STATUS_FAILED, missing=[],
                   detail={**(row.get('detail') or {}), 'reason': f'tokenise: {exc}'})
            continue
        if item.get('is_phrase') and language_registry.is_cjk(language_id):
            # A CJK word the tokeniser split (お茶 -> 御 + 茶) is stored under
            # what the learner typed, not a space-joined token string.
            item = {**item, 'lemma': row['raw_word']}
        detail = {**(row.get('detail') or {}), 'lemma': item['lemma']}
        vocab_id = _lookup_vocab_id(db, item['lemma'], language_id)
        if vocab_id is None and row['raw_word'] != item['lemma']:
            vocab_id = _lookup_vocab_id(db, row['raw_word'], language_id)
        if vocab_id is None and create_vocab:
            vocab_id = get_or_create_vocab_id(db, item, language_id, code)
        if vocab_id is None:
            if row.get('missing') != [ASSET_VOCAB] or row.get('detail') != detail:
                _write(db, row, missing=[ASSET_VOCAB], detail=detail)
            continue
        _write(db, row, status=STATUS_BUILDING, vocab_id=vocab_id, detail=detail)


# ---------------------------------------------------------------------------
# Asset checklist
# ---------------------------------------------------------------------------

def _ids_with(db, table: str, column: str, ids: list[int], build) -> set[int]:
    found: set[int] = set()
    for chunk in _chunks(sorted(set(ids))):
        query = build(db.table(table).select(column).in_(column, chunk))
        found.update(r[column] for r in (query.execute().data or []))
    return found


def _simple_ranks(db, vocab_ids: list[int], language_id: int) -> set[tuple[int, int]]:
    found: set[tuple[int, int]] = set()
    for chunk in _chunks(sorted(set(vocab_ids))):
        rows = (db.table('dim_word_senses').select('vocab_id, sense_rank')
                .in_('vocab_id', chunk)
                .eq('definition_language_id', language_id)
                .eq('definition_level', 'simple')
                .execute().data or [])
        found.update((r['vocab_id'], r['sense_rank']) for r in rows)
    return found


def _glossed(db, vocab_ids: list[int], gloss_language_id: int) -> set[tuple[int, int]]:
    """(vocab_id, sense_rank) with both gloss levels in ``gloss_language_id``."""
    levels: dict[tuple[int, int], set] = {}
    for chunk in _chunks(sorted(set(vocab_ids))):
        rows = (db.table('dim_word_senses').select('vocab_id, sense_rank, definition_level')
                .in_('vocab_id', chunk)
                .eq('definition_language_id', gloss_language_id)
                .in_('definition_level', ['simple', 'standard'])
                .execute().data or [])
        for r in rows:
            levels.setdefault((r['vocab_id'], r['sense_rank']), set()).add(r['definition_level'])
    return {k for k, v in levels.items() if {'simple', 'standard'} <= v}


def _audio_url_of(content: dict, exercise_type: str) -> str:
    value = (content or {}).get(AUDIO_URL_FIELDS.get(exercise_type, 'audio_url'))
    return value.strip() if isinstance(value, str) else ''


def _senses_missing_audio(db, sense_ids: list[int]) -> set[int]:
    """Senses with an active audio-bearing exercise that has no audio URL.
    A sense whose content cannot be read counts as missing (fail closed)."""
    from services.exercise_content import store

    missing: set[int] = set()
    columns = store.select_columns('id, exercise_type, word_sense_id, language_id, {content}')
    for chunk in _chunks(sorted(set(sense_ids)), 100):
        rows = (db.table('exercises').select(columns)
                .in_('word_sense_id', chunk)
                .eq('is_active', True)
                .in_('exercise_type', list(AUDIO_URL_FIELDS))
                .execute().data or [])
        if not rows:
            continue
        wanted = {r['word_sense_id'] for r in rows}
        store.hydrate(rows, max_senses=len(wanted), deadline_s=60.0)
        hydrated = {r['word_sense_id'] for r in rows}
        missing.update(wanted - hydrated)
        for r in rows:
            if not _audio_url_of(r.get('content') or {}, r.get('exercise_type')):
                missing.add(r['word_sense_id'])
    return missing


def check_assets(db, rows: list[dict]) -> dict[int, dict]:
    """Queue row id -> ``{'sense_id': int | None, 'missing': [asset keys]}``
    for rows that have a ``vocab_id``. Reads only; batches every lookup."""
    with_vocab = [r for r in rows if r.get('vocab_id')]
    result: dict[int, dict] = {}
    by_language: dict[int, list[dict]] = {}
    for r in with_vocab:
        by_language.setdefault(r['language_id'], []).append(r)

    for language_id, lang_rows in by_language.items():
        vocab_ids = [r['vocab_id'] for r in lang_rows]
        primary = primary_senses(db, vocab_ids, language_id)
        sense_ids = [p['id'] for p in primary.values()]

        simple = _simple_ranks(db, vocab_ids, language_id)
        embedded = _ids_with(db, 'dim_word_senses', 'id', sense_ids,
                             lambda q: q.not_.is_('embedding', 'null'))
        cored = _ids_with(db, 'word_assets', 'sense_id', sense_ids,
                          lambda q: q.eq('asset_type', 'prompt1_core').eq('is_valid', True))
        exercised = _ids_with(db, 'exercises', 'word_sense_id', sense_ids,
                              lambda q: q.eq('is_active', True))
        no_audio = _senses_missing_audio(db, sorted(exercised)) if exercised else set()
        glossed: dict[int, set] = {}
        for gl in {r.get('gloss_language_id') for r in lang_rows if r.get('gloss_language_id')}:
            glossed[gl] = _glossed(db, vocab_ids, gl)

        for r in lang_rows:
            sense = primary.get(r['vocab_id'])
            if sense is None:
                result[r['id']] = {'sense_id': None, 'missing': [
                    k for k in ASSET_KEYS if k != ASSET_VOCAB
                    and (k != ASSET_PRONUNCIATION or language_id in PRONUNCIATION_LANGUAGE_IDS)
                    and (k != ASSET_GLOSS or r.get('gloss_language_id'))]}
                continue
            sid, key = sense['id'], (r['vocab_id'], sense['sense_rank'])
            missing = []
            if key not in simple:
                missing.append(ASSET_SENSE)
            if sid not in embedded:
                missing.append(ASSET_EMBEDDING)
            if language_id in PRONUNCIATION_LANGUAGE_IDS and not sense.get('pronunciation'):
                missing.append(ASSET_PRONUNCIATION)
            gl = r.get('gloss_language_id')
            if gl and key not in glossed.get(gl, set()):
                missing.append(ASSET_GLOSS)
            if sid not in cored:
                missing.append(ASSET_CORE)
            if sid not in exercised:
                missing.extend([ASSET_EXERCISES, ASSET_AUDIO])
            elif sid in no_audio:
                missing.append(ASSET_AUDIO)
            result[r['id']] = {'sense_id': sid, 'missing': missing}
    return result


# ---------------------------------------------------------------------------
# Finalise
# ---------------------------------------------------------------------------

def _write(db, row: dict, **fields) -> None:
    """Update one queue row and mirror the change onto ``row``."""
    fields['updated_at'] = _now()
    db.table(TABLE).update(fields).eq('id', row['id']).execute()
    row.update(fields)


def _watching(db, user_id: str, sense_id: int) -> bool:
    rows = (db.table('user_word_watchlist').select('id')
            .eq('user_id', user_id).eq('sense_id', sense_id)
            .limit(1).execute().data or [])
    return bool(rows)


def _finish(db, row: dict, sense_id: int) -> Optional[dict]:
    """Claim the row (building -> done) and write its watchlist row.
    Returns the new watchlist row, or None when another run claimed it or the
    learner already watches the sense."""
    now = _now()
    claimed = (db.table(TABLE)
               .update({'status': STATUS_DONE, 'sense_id': sense_id, 'missing': [],
                        'completed_at': now, 'updated_at': now})
               .eq('id', row['id']).eq('status', STATUS_BUILDING)
               .execute().data or [])
    if not claimed:
        return None
    row.update(status=STATUS_DONE, sense_id=sense_id, missing=[], completed_at=now)
    if _watching(db, row['user_id'], sense_id):
        return None
    inserted = (db.table('user_word_watchlist').insert({
        'user_id': row['user_id'],
        'sense_id': sense_id,
        'language_id': row['language_id'],
        'upload_batch_id': row['upload_batch_id'],
        'ladder_exercises_generated': True,
    }).execute().data or [])
    return inserted[0] if inserted else None


def load_open_rows(db, *, language_id: Optional[int] = None,
                   upload_batch_id: Optional[str] = None,
                   ids: Optional[Iterable[int]] = None,
                   statuses: Optional[Iterable[str]] = None) -> list[dict]:
    """Queue rows in scope (default: the open statuses), oldest id first."""
    statuses = list(statuses) if statuses is not None else None
    ids = list(ids) if ids is not None else None

    def build():
        # A fresh builder per page: postgrest's .range() mutates the builder.
        query = (db.table(TABLE)
                 .select('id, user_id, upload_batch_id, language_id, raw_word, '
                         'gloss_language_id, vocab_id, sense_id, status, missing, '
                         'detail, requested_at')
                 .in_('status', list(statuses or OPEN_STATUSES)))
        if language_id is not None:
            query = query.eq('language_id', language_id)
        if upload_batch_id is not None:
            query = query.eq('upload_batch_id', upload_batch_id)
        if ids is not None:
            query = query.in_('id', ids)
        return query.order('id')

    rows: list[dict] = []
    offset = 0
    while True:
        page = build().range(offset, offset + 999).execute().data or []
        rows.extend(page)
        if len(page) < 1000:
            return rows
        offset += 1000


def advance(db, *, language_id: Optional[int] = None,
            upload_batch_id: Optional[str] = None, create_vocab: bool = False,
            db_client=None, sweep: bool = True) -> dict:
    """Resolve, check and finish every open row in scope. No LLM call.

    ``db_client`` (a ``TestDatabaseClient``) is only needed for the test-match
    sweep on newly finished rows; without it the sweep is skipped and the
    nightly sweep picks the rows up.
    """
    rows = load_open_rows(db, language_id=language_id, upload_batch_id=upload_batch_id)
    summary = {'open': len(rows), 'resolved': 0, 'done': 0, 'building': 0,
               'pending': 0, 'failed': 0, 'watchlist_rows': 0}
    if not rows:
        return summary

    before = {r['id']: r.get('vocab_id') for r in rows}
    resolve_rows(db, rows, create_vocab=create_vocab)
    summary['resolved'] = sum(1 for r in rows if r.get('vocab_id') and not before[r['id']])

    checks = check_assets(db, [r for r in rows if r.get('status') == STATUS_BUILDING])
    new_watch: list[dict] = []
    for row in rows:
        check = checks.get(row['id'])
        if check is None:
            continue
        if check['sense_id'] and not check['missing']:
            watch = _finish(db, row, check['sense_id'])
            if watch:
                new_watch.append(watch)
            continue
        if check['missing'] != (row.get('missing') or []) or check['sense_id'] != row.get('sense_id'):
            _write(db, row, missing=check['missing'], sense_id=check['sense_id'])

    for row in rows:
        summary[row['status']] = summary.get(row['status'], 0) + 1
    summary['watchlist_rows'] = len(new_watch)

    if new_watch and sweep and db_client is not None:
        try:
            from services.word_list_import.match_sweep import sweep_immediate_matches
            sweep_immediate_matches(new_watch, db_client)
        except Exception as exc:
            logger.warning('match sweep after queue finish failed: %s', exc)
    return summary


def run_scheduled_advance() -> dict:
    """Scheduler entry point: advance every open row, lookup-only (no new
    dim_vocabulary rows, no LLM). Finishes words whose assets already exist
    and refreshes ``missing`` for the rest."""
    from services.supabase_factory import get_supabase_admin
    db = get_supabase_admin()
    try:
        from services.test_generation.database_client import TestDatabaseClient
        db_client = TestDatabaseClient()
    except Exception as exc:
        logger.warning('queue advance without match sweep: %s', exc)
        db_client = None
    return advance(db, db_client=db_client)
