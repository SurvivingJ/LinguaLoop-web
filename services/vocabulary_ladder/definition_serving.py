"""Serve-time native-language options for ``definition_match`` items.

The problem (reported 2026-11-26)
---------------------------------
``deterministic/definition_match.py`` takes the key and its three distractors
from the word's *own-language* definitions (``lexicon._load_entries`` keeps
only rows with ``definition_language_id == language_id``) and files them under
``content.nl.<DEFAULT_NATIVE_LANGUAGE>``. For a Japanese or Chinese word that
is four Japanese / Chinese definitions labelled ``en``. A learner whose native
language is English, studying Japanese, was shown "pick the meaning of 人間"
with four Japanese definitions. About 12,000 stored ja items have this shape
(and the zh ones), in immutable content files, so the fix is at serve time.

What this module does
---------------------
For a learner who reads a different language from the one they study, every
``definition_match`` item is rebuilt from the cross-language gloss rows
(``dim_word_senses`` with ``definition_language_id`` = the learner's language,
the same rows the new-word drill's ``def_mc`` and prestudy already use):

* the key is the gloss of the item's own meaning (same word, same sense rank,
  the item's definition level first, then standard, then simple), and
* the three wrong options are glosses of other words with the same part of
  speech, picked by the generator's own policy (``Lexicon.definitions_near``:
  similar word frequency and similar length first, loosening only when the
  tight pool runs dry), so the item stays answerable only by knowing the word.

An item that cannot be rebuilt (no gloss of its meaning in the learner's
language, or too few distractors) is dropped when its stored options are in a
different script from the learner's language: an exercise the learner cannot
read is worse than one fewer exercise.

The rebuilt content is flat (``options``, ``correct_answer`` and
``correct_definition`` at the top level, no ``nl`` map), which every consumer
reads: ``ExRenderers`` (practice, new-word drill) passes flat content through
``flattenNl`` unchanged, and prestudy's ``trim_exercise`` reads exactly those
keys. Content that declares ``definition_language_id`` equal to the learner's
language is already right and is left alone (a fixed generator can opt out
that way).

Gloss pool cache
----------------
The distractor pool is every gloss of the language in the learner's language
(about 13,400 rows for ja -> en), loaded once per process with the pages
fetched concurrently and kept for ``POOL_TTL_S``. ``warm`` starts that load in
the background so a session request can overlap it with its other reads. A
failed load is remembered for ``FAILED_POOL_TTL_S`` (items are then dropped
rather than shown in the wrong language) so a database blip is not retried on
every request.
"""

from __future__ import annotations

import logging
import random
import re
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from bisect import bisect_left
from typing import Iterable, Optional

from services import language_registry
from services.vocabulary_ladder.deterministic.definition_match import script_family
from services.vocabulary_ladder.deterministic.lexicon import Lexicon, LexEntry

logger = logging.getLogger(__name__)

TYPE = 'definition_match'
DISTRACTORS = 3
POOL_TTL_S = 6 * 3600
FAILED_POOL_TTL_S = 60
POOL_LOAD_TIMEOUT_S = 5.0
_PAGE = 1000                 # PostgREST's default row cap per request
_SENSE_PAGES_PER_WAVE = 16   # gloss pages fetched at once (ja -> en is 14 pages)
_VOCAB_PAGES_PER_WAVE = 8    # vocabulary pages fetched at once (ja is 7 pages)
_IN_CHUNK = 200              # ids per ``in.(...)`` filter
_MIN_SLICE = 40              # smallest distractor slice worth matching on
_OVERSAMPLE = 12             # candidates drawn before the overlap filter
_LEVEL_ORDER = ('standard', 'simple')

_LANG_CODE = language_registry.id_to_code()
_LANG_FAMILY = {lang.code: lang.script for lang in language_registry.all_languages()}


# ---------------------------------------------------------------------------
# Gloss pool
# ---------------------------------------------------------------------------

@dataclass
class GlossPool:
    """Every gloss of one language's words in one other language."""

    language_id: int
    gloss_language_id: int
    ok: bool = True
    loaded_at: float = field(default_factory=time.monotonic)
    # (vocab_id, sense_rank) -> {definition_level: definition}
    glosses: dict[tuple[int, int], dict[str, str]] = field(default_factory=dict)
    # vocab_id -> Zipf frequency (dim_vocabulary.frequency_rank)
    frequency: dict[int, Optional[float]] = field(default_factory=dict)
    # vocab_id -> gloss row ids, so a key's own word never returns as a distractor
    ids_of_vocab: dict[int, set[int]] = field(default_factory=dict)
    # vocab_id -> part of speech
    pos_of: dict[int, Optional[str]] = field(default_factory=dict)
    # distractor lexicons of rank-1 glosses: per (level, part of speech), per
    # level, and all of them
    by_level_pos: dict[tuple[str, str], Lexicon] = field(default_factory=dict)
    by_level: dict[str, Lexicon] = field(default_factory=dict)
    everything: Optional[Lexicon] = None
    # Every row in id order: (id, lemma, definition, part_of_speech), for the
    # new-word drill's option pool (``rows_from``).
    rows: list[tuple[int, str, str, Optional[str]]] = field(default_factory=list)
    _row_ids: list[int] = field(default_factory=list)

    def key_gloss(self, vocab_id: int, sense_rank: int, level: Optional[str]) -> tuple[str, Optional[str]]:
        """The gloss of one meaning and its level: the item's level first."""
        by_level = self.glosses.get((vocab_id, sense_rank)) or {}
        for lv in (level, *_LEVEL_ORDER):
            if lv and by_level.get(lv):
                return by_level[lv], lv
        for lv, text in by_level.items():
            if text:
                return text, lv
        return '', None

    def lexicon_for(self, level: Optional[str], pos: Optional[str] = None) -> Optional[Lexicon]:
        """Where a meaning's wrong options come from: glosses at the key's level
        of words with the same part of speech (a verb's gloss reads "to ...",
        so a noun's among three verbs gives the answer away), widening to the
        level, then to everything, when a slice is too small."""
        for lex in (self.by_level_pos.get((level or '', pos or '')) if pos else None,
                    self.by_level.get(level or '')):
            if lex is not None and len(lex.entries) >= _MIN_SLICE:
                return lex
        return self.everything

    def rows_from(self, min_id: int, limit: int) -> list[tuple[int, str, str, Optional[str]]]:
        """The first ``limit`` rows with id >= ``min_id`` (id order)."""
        start = bisect_left(self._row_ids, min_id)
        return self.rows[start:start + limit]

    def expired(self, now: float) -> bool:
        ttl = POOL_TTL_S if self.ok else FAILED_POOL_TTL_S
        return now - self.loaded_at > ttl


_pools: dict[tuple[int, int], GlossPool] = {}
_loading: dict[tuple[int, int], Future] = {}
_lock = threading.Lock()
_executor: Optional[ThreadPoolExecutor] = None


def _pool_executor() -> ThreadPoolExecutor:
    # Its own pool, not services.concurrency's: run_parallel runs inline on an
    # 'io' thread, which would serialise the page fetches.
    global _executor
    with _lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(max_workers=_SENSE_PAGES_PER_WAVE + _VOCAB_PAGES_PER_WAVE,
                                           thread_name_prefix='gloss-pool')
        return _executor


def reset_cache() -> None:
    """Drop every cached pool (tests; after a gloss backfill)."""
    with _lock:
        _pools.clear()
        _loading.clear()


def _gloss_page(db, language_id: int, gloss_language_id: int, start: int) -> list[dict]:
    # Flat: an embedded dim_vocabulary per row made 16 concurrent pages hit
    # the 8 s statement timeout (2026-11-26); the words are a separate read.
    return (
        db.table('dim_word_senses')
        .select('id, vocab_id, sense_rank, definition_level, definition')
        .eq('word_language_id', language_id)
        .eq('definition_language_id', gloss_language_id)
        .order('id')
        .range(start, start + _PAGE - 1)
        .execute()
    ).data or []


def _vocab_page(db, language_id: int, start: int) -> list[dict]:
    return (
        db.table('dim_vocabulary')
        .select('id, lemma, frequency_rank, part_of_speech')
        .eq('language_id', language_id)
        .order('id')
        .range(start, start + _PAGE - 1)
        .execute()
    ).data or []


def _paged(fetch, per_wave: int) -> list[dict]:
    """Every row of a paged read, ``per_wave`` pages at a time until a short page."""
    executor = _pool_executor()
    rows: list[dict] = []
    start = 0
    while True:
        starts = [start + i * _PAGE for i in range(per_wave)]
        results = [f.result() for f in [executor.submit(fetch, s) for s in starts]]
        for page in results:
            rows.extend(page)
        if any(len(page) < _PAGE for page in results):
            return rows
        start = starts[-1] + _PAGE


def _fetch_rows(db, language_id: int, gloss_language_id: int) -> list[dict]:
    """All gloss rows of the language, each with its word under ``dim_vocabulary``.

    The two paged reads run at the same time (each on a thread of its own
    that fans its pages out over the shared executor).
    """
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix='gloss-pool-read') as pair:
        glosses = pair.submit(_paged, lambda s: _gloss_page(db, language_id, gloss_language_id, s),
                              _SENSE_PAGES_PER_WAVE)
        words = pair.submit(_paged, lambda s: _vocab_page(db, language_id, s),
                            _VOCAB_PAGES_PER_WAVE)
        vocab = {int(v['id']): v for v in words.result() if v.get('id') is not None}
        rows = glosses.result()
    for r in rows:
        r['dim_vocabulary'] = vocab.get(int(r['vocab_id'])) if r.get('vocab_id') is not None else None
    return rows


def _build_pool(language_id: int, gloss_language_id: int, rows: Iterable[dict]) -> GlossPool:
    pool = GlossPool(language_id=language_id, gloss_language_id=gloss_language_id)
    levels: dict[str, list[LexEntry]] = {}
    level_pos: dict[tuple[str, str], list[LexEntry]] = {}
    everything: list[LexEntry] = []
    seen_ids: set[int] = set()
    for r in rows:
        gid, vid = r.get('id'), r.get('vocab_id')
        if gid is None or vid is None or gid in seen_ids:
            continue
        seen_ids.add(gid)
        vocab = r.get('dim_vocabulary') or {}
        pool.rows.append((int(gid), vocab.get('lemma') or '', r.get('definition') or '',
                          vocab.get('part_of_speech')))
        text = (r.get('definition') or '').strip()
        if not text:
            continue
        rank = int(r.get('sense_rank') or 1)
        level = r.get('definition_level') or ''
        freq = vocab.get('frequency_rank')
        pool.glosses.setdefault((vid, rank), {}).setdefault(level, text)
        pos = vocab.get('part_of_speech')
        pool.frequency.setdefault(vid, freq)
        pool.pos_of.setdefault(vid, pos)
        pool.ids_of_vocab.setdefault(vid, set()).add(gid)
        if rank != 1:
            continue                      # distractors are words' main meanings
        entry = LexEntry(sense_id=gid, lemma=vocab.get('lemma') or '', definition=text,
                         pronunciation='', reading_key='', tier=level, frequency=freq,
                         semantic_class=None, sense_rank=rank)
        levels.setdefault(level, []).append(entry)
        if pos:
            level_pos.setdefault((level, pos), []).append(entry)
        everything.append(entry)
    pool.by_level_pos = {k: Lexicon(language_id=language_id, entries=es) for k, es in level_pos.items()}
    pool.by_level = {lv: Lexicon(language_id=language_id, entries=es) for lv, es in levels.items()}
    pool.everything = Lexicon(language_id=language_id, entries=everything)
    pool.rows.sort(key=lambda row: row[0])
    pool._row_ids = [row[0] for row in pool.rows]
    return pool


def _load_pool(db, language_id: int, gloss_language_id: int) -> GlossPool:
    started = time.monotonic()
    try:
        pool = _build_pool(language_id, gloss_language_id,
                           _fetch_rows(db, language_id, gloss_language_id))
    except Exception as exc:
        logger.error('definition gloss pool load failed (lang=%s gloss=%s): %s',
                     language_id, gloss_language_id, exc)
        pool = GlossPool(language_id=language_id, gloss_language_id=gloss_language_id, ok=False)
    else:
        logger.info('definition gloss pool lang=%s gloss=%s: %d meanings in %.0f ms',
                    language_id, gloss_language_id, len(pool.glosses),
                    (time.monotonic() - started) * 1000)
    with _lock:
        _pools[(language_id, gloss_language_id)] = pool
        _loading.pop((language_id, gloss_language_id), None)
    return pool


def _pool_future(db, language_id: int, gloss_language_id: int) -> Optional[Future]:
    """The in-flight load for this pair, started if needed; None when cached."""
    key = (language_id, gloss_language_id)
    now = time.monotonic()
    with _lock:
        cached = _pools.get(key)
        if cached is not None and not cached.expired(now):
            return None
        fut = _loading.get(key)
        if fut is None:
            fut = Future()
            _loading[key] = fut
            start = True
        else:
            start = False
    if start:
        def run():
            try:
                fut.set_result(_load_pool(db, language_id, gloss_language_id))
            except BaseException as exc:  # never leave a waiter hanging
                fut.set_exception(exc)
        _pool_executor().submit(run)
    return fut


def _wants_localising(language_id: Optional[int], nl_language_id: Optional[int]) -> bool:
    return bool(language_id and nl_language_id and int(language_id) != int(nl_language_id))


def warm(db, language_id: Optional[int], nl_language_id: Optional[int]) -> None:
    """Start loading the pool a later ``localise`` will need. Never blocks or raises."""
    if db is None or not _wants_localising(language_id, nl_language_id):
        return
    try:
        _pool_future(db, int(language_id), int(nl_language_id))
    except Exception as exc:
        logger.warning('definition gloss pool warm-up failed: %s', exc)


def get_pool(db, language_id: int, gloss_language_id: int,
             timeout: float = POOL_LOAD_TIMEOUT_S) -> Optional[GlossPool]:
    """The cached pool, waiting up to ``timeout`` for a load in flight."""
    fut = _pool_future(db, language_id, gloss_language_id)
    if fut is not None:
        try:
            return fut.result(timeout=timeout)
        except Exception as exc:
            logger.warning('definition gloss pool not ready (lang=%s gloss=%s): %s',
                           language_id, gloss_language_id, exc)
            return None
    with _lock:
        return _pools.get((language_id, gloss_language_id))


# ---------------------------------------------------------------------------
# Per-request work
# ---------------------------------------------------------------------------

@dataclass
class Plan:
    """What ``apply`` needs: the learner's language, the pool and each item's meaning."""

    language_id: int
    nl_language_id: int
    pool: Optional[GlossPool]
    # native sense id -> (vocab_id, sense_rank, definition_level)
    meanings: dict[int, tuple[int, int, Optional[str]]]


def _sense_id(item: dict, sense_key: str) -> Optional[int]:
    try:
        return int(item.get(sense_key))
    except (TypeError, ValueError):
        return None


def _load_meanings(db, sense_ids: list[int]) -> dict[int, tuple[int, int, Optional[str]]]:
    out: dict[int, tuple[int, int, Optional[str]]] = {}
    for i in range(0, len(sense_ids), _IN_CHUNK):
        part = sense_ids[i:i + _IN_CHUNK]
        for r in (db.table('dim_word_senses')
                  .select('id, vocab_id, sense_rank, definition_level')
                  .in_('id', part).execute().data or []):
            if r.get('id') is None or r.get('vocab_id') is None:
                continue
            out[int(r['id'])] = (int(r['vocab_id']), int(r.get('sense_rank') or 1),
                                 r.get('definition_level'))
    return out


def prepare(db, items: list[dict], *, language_id: Optional[int], nl_language_id: Optional[int],
            sense_key: str = 'sense_id', type_key: str = 'exercise_type') -> Optional[Plan]:
    """Read what localising ``items`` needs (one query plus the cached pool).

    Reads only the items' types and sense ids, so it can run while their
    content is still being fetched. None when nothing needs localising.
    """
    if db is None or not _wants_localising(language_id, nl_language_id):
        return None
    sense_ids = sorted({sid for it in items or []
                        if isinstance(it, dict) and it.get(type_key) == TYPE
                        for sid in [_sense_id(it, sense_key)] if sid is not None})
    if not sense_ids:
        return None
    language_id, nl_language_id = int(language_id), int(nl_language_id)
    warm(db, language_id, nl_language_id)          # overlap the pool with the query below
    try:
        meanings = _load_meanings(db, sense_ids)
    except Exception as exc:
        logger.warning('definition_match meaning lookup failed: %s', exc)
        meanings = {}
    return Plan(language_id=language_id, nl_language_id=nl_language_id,
                pool=get_pool(db, language_id, nl_language_id), meanings=meanings)


def _stored_options(content: dict) -> tuple[list, str]:
    """Options and key as stored (v2 envelope, any block; or v1 flat)."""
    nl = content.get('nl')
    if isinstance(nl, dict):
        for block in nl.values():
            if isinstance(block, dict) and block.get('options'):
                return list(block.get('options') or []), str(block.get('correct_answer') or '')
    return (list(content.get('options') or []),
            str(content.get('correct_answer') or content.get('correct_definition') or ''))


def rebuild(plan: Plan, sense_id: int, content: dict) -> Optional[dict]:
    """``content`` with options in the learner's language, or None when impossible."""
    pool = plan.pool
    meaning = plan.meanings.get(sense_id)
    if pool is None or not pool.ok or meaning is None:
        return None
    vocab_id, rank, level = meaning
    key, key_level = pool.key_gloss(vocab_id, rank, level)
    if not key:
        return None
    lex = pool.lexicon_for(key_level, pool.pos_of.get(vocab_id))
    if lex is None:
        return None
    rng = random.Random(f'{TYPE}:l1:{sense_id}:{plan.nl_language_id}')
    # Oversampled, then any candidate sharing a gloss term with the key is
    # dropped ("simply; merely" beside the key "just a little; merely" makes
    # two options right).
    key_terms = gloss_terms(key)
    distractors = [d for d in lex.definitions_near(
        frequency=pool.frequency.get(vocab_id),
        key_definition=key,
        exclude_sense_ids=pool.ids_of_vocab.get(vocab_id, set()),
        count=_OVERSAMPLE,
        rng=rng,
    ) if not (gloss_terms(d) & key_terms)][:DISTRACTORS]
    if len(distractors) < DISTRACTORS:
        return None
    options = [key] + distractors
    rng.shuffle(options)
    code = _LANG_CODE.get(plan.nl_language_id)
    out = {k: v for k, v in content.items()
           if k not in ('nl', 'schema_version', 'options', 'correct_answer', 'correct_definition')}
    out.update({
        'options': options,
        'correct_answer': key,
        'correct_definition': key,
        'definition_language_id': plan.nl_language_id,
    })
    if code:
        out['nl_language'] = code
    return out


_TERM_SPLIT = re.compile(r'[;,；，、/]')
_LEADING_WORD = re.compile(r'^(?:to|a|an|the|be)\s+', re.IGNORECASE)


def gloss_terms(text: str) -> set[str]:
    """The equivalents a gloss lists before its explanation, normalised:
    'a human; a person — referring to ...' -> {'human', 'person'}."""
    head = (text or '').split(' — ')[0].split('（')[0].split('(')[0]
    out = set()
    for part in _TERM_SPLIT.split(head):
        term = _LEADING_WORD.sub('', part.strip().lower()).strip(' .')
        if term:
            out.add(term)
    return out


def _readable(content: dict, nl_language_id: int) -> bool:
    """Whether the stored options are in the learner's script family."""
    options, key = _stored_options(content)
    sample = key or next((str(o) for o in options if o), '')
    want = _LANG_FAMILY.get(_LANG_CODE.get(nl_language_id, ''), '')
    return bool(sample) and bool(want) and script_family(sample) == want


def apply(plan: Optional[Plan], items: list[dict], *, sense_key: str = 'sense_id',
          type_key: str = 'exercise_type') -> int:
    """Rewrite ``items``' definition_match content in place; return how many were dropped.

    Items whose content already declares the learner's definition language
    are left alone. An item that cannot be rebuilt is kept only when its
    stored options are in the learner's script; otherwise it is removed from
    ``items`` (order kept).
    """
    if plan is None or not items:
        return 0
    keep: list[dict] = []
    dropped = rebuilt = 0
    for item in items:
        if not isinstance(item, dict) or item.get(type_key) != TYPE:
            keep.append(item)
            continue
        content = item.get('content')
        sid = _sense_id(item, sense_key)
        if not isinstance(content, dict) or sid is None:
            keep.append(item)
            continue
        if content.get('definition_language_id') == plan.nl_language_id:
            keep.append(item)
            continue
        new = rebuild(plan, sid, content)
        if new is not None:
            item['content'] = new
            rebuilt += 1
            keep.append(item)
        elif _readable(content, plan.nl_language_id):
            keep.append(item)
        else:
            dropped += 1
    if dropped or rebuilt:
        logger.info('definition_match localised (lang=%s nl=%s): rebuilt=%d dropped=%d',
                    plan.language_id, plan.nl_language_id, rebuilt, dropped)
    items[:] = keep
    return dropped


def localise(db, items: list[dict], *, language_id: Optional[int], nl_language_id: Optional[int],
             sense_key: str = 'sense_id', type_key: str = 'exercise_type') -> int:
    """``prepare`` then ``apply``, for callers with hydrated items in hand."""
    try:
        plan = prepare(db, items, language_id=language_id, nl_language_id=nl_language_id,
                       sense_key=sense_key, type_key=type_key)
    except Exception as exc:
        logger.warning('definition_match localisation skipped: %s', exc)
        plan = None
    if plan is None and _wants_localising(language_id, nl_language_id):
        # Could not prepare (lookup failed): still keep unreadable items out.
        plan = Plan(language_id=int(language_id), nl_language_id=int(nl_language_id),
                    pool=None, meanings={})
    return apply(plan, items, sense_key=sense_key, type_key=type_key)
