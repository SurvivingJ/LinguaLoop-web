"""Per-option answer explanations in the learner's language (ADR-064).

Why
---
A "spot the error" item (``spot_incorrect_sentence``) shows four sentences in
the language being studied; one has an error. What the corpus stores about it
is the sentences, which one is wrong and, at most, a one-line note on the wrong
one written in the *target* language (``助詞：他動詞「使う」の対象は「を」で示す``).
A learner who picked a correct sentence learned nothing about why it was
correct, and the one note was in the language they are still learning
(reported 2026-11-26).

What
----
For each such item and learner language this module asks a model, once, for
every sentence's meaning, why it is right or wrong and, for the wrong one, the
corrected sentence, all written in the learner's language. The answer is
validated (one entry per sentence, the item's own verdicts, the learner's
script) and kept in ``exercise_explanations`` so every later learner reads it
without a model call. The model is told which sentence is wrong; it explains
the item's key and never re-judges it.

Serving
-------
Lookup order for one item: this process's memory -> the item's own complete
notes (``stored_entries``) -> the sense's pre-written Storage file
(``services/explanation_files.py``, written ahead of time by a batch: the
table is too close to the Free plan's database cap to hold them all) -> the
table -> a model call. A file entry or table row is used only when it was
written for the item's ``content_version`` and its sentences
(``_aligned``); a used one is kept in memory.

* ``prefetch`` (session assembly, beside content hydration): reads the
  Storage files of the items' senses and the table rows concurrently, from
  ids alone, and returns them as one ``Prefetched`` for ``prepare_items``.
* ``prepare_items`` (session assembly, new-word drill): attaches what is
  already cached as ``content['option_explanations']`` (aligned with
  ``content['sentences']``) and starts background generation for up to
  ``Config.EXERCISE_EXPLANATION_WARM_PER_REQUEST`` items that have none, so
  they are usually ready before the learner answers.
* ``get_or_generate`` (``GET /api/practice/explanations/<exercise_id>``): what
  the renderer asks for when an item arrived without them; waits for a
  generation already in flight rather than starting a second.

What is generated at serve time goes to memory and the table, never to a
Storage file: files are immutable and belong to the batch.

Before migrations/exercise_explanations.sql is applied the table read fails;
that is remembered for a few minutes and explanations live only in this
process's memory (``_MEMORY_MAX`` entries).
"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional, Union

from config import Config
from services import explanation_files

logger = logging.getLogger(__name__)

SPOT = 'spot_incorrect_sentence'          # pick the sentence with an error
PICK = 'semantic_discrimination'          # pick the sentence that uses the word correctly
TYPES = frozenset({SPOT, PICK})
_TASK_NAME = {SPOT: 'spot_error_explanation', PICK: 'pick_sentence_explanation'}
# v2 (2026-11-26): a wrong sentence's meaning is its literal translation, so
# the mistake shows ("I boiled the fragments with a broom", not "I swept them
# up"); spot items are told the reviewed corrected sentence. Payloads from an
# older version are not served.
PROMPT_VERSION = 2
TABLE = 'exercise_explanations'

_MEMORY_MAX = 2000
_TABLE_RETRY_S = 300          # after a failed table read, how long to stop asking
_WORKERS = 4
_READ_WORKERS = 8             # file reads run here while the table is read (8 = gunicorn threads)
# The same budget as the content hydration it runs beside: cold Storage reads
# from production take 1-1.5 s, and 2 s missed some (pilot, 2026-11-27).
_FILE_DEADLINE_S = float(getattr(Config, 'EXERCISE_CONTENT_DEADLINE_S', 3.0) or 3.0)
_JOB_FILE_DEADLINE_S = 10.0   # a background job can wait longer before paying for a model
_LLM_TIMEOUT_S = 30
_MAX_TOKENS = 2000
_CAP = {'meaning': 400, 'explanation': 600, 'correction': 300}

_LANG = {1: ('zh', 'Chinese'), 2: ('en', 'English'), 3: ('ja', 'Japanese')}
_FAMILY = {'zh': 'cjk', 'ja': 'cjk', 'en': 'latin'}

_lock = threading.Lock()
_memory: 'OrderedDict[tuple[str, int], tuple[int, dict]]' = OrderedDict()
_inflight: dict[tuple[str, int], Future] = {}
_table_down_until = 0.0
_executor: Optional[ThreadPoolExecutor] = None
_read_executor: Optional[ThreadPoolExecutor] = None


def enabled() -> bool:
    return bool(getattr(Config, 'EXERCISE_EXPLANATIONS_ENABLED', True))


def supported(exercise_type: Optional[str]) -> bool:
    return exercise_type in TYPES


def reset_state() -> None:
    """Forget cached explanations, cached Storage files and the table state (tests)."""
    global _table_down_until
    with _lock:
        _memory.clear()
        _inflight.clear()
        _table_down_until = 0.0
    explanation_files.reset_cache()


def _pool() -> ThreadPoolExecutor:
    global _executor
    with _lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(max_workers=_WORKERS, thread_name_prefix='explain')
        return _executor


def _read_pool() -> ThreadPoolExecutor:
    """Where a Storage file read waits while the caller reads the table. Not ``_pool``
    (its workers can be busy for 30 s with model calls) and not ``services.concurrency``
    (``prefetch`` already runs on one of its threads)."""
    global _read_executor
    with _lock:
        if _read_executor is None:
            _read_executor = ThreadPoolExecutor(max_workers=_READ_WORKERS,
                                                thread_name_prefix='explain-read')
        return _read_executor


# ---------------------------------------------------------------------------
# Content shape
# ---------------------------------------------------------------------------

def sentences_of(content: Any) -> Optional[list[dict]]:
    """The item's sentences, or None when it is not an explainable shape
    (at least two sentences, every one with text, at least one right and one
    wrong)."""
    if not isinstance(content, dict):
        return None
    sents = content.get('sentences')
    if not isinstance(sents, list) or len(sents) < 2:
        return None
    if not all(isinstance(s, dict) and str(s.get('text') or '').strip() for s in sents):
        return None
    if not any(s.get('is_correct') is False for s in sents):
        return None
    if not any(s.get('is_correct') is not False for s in sents):
        return None
    return sents


def stored_entries(sents: list[dict], nl_language_id: int) -> Optional[list[dict]]:
    """Entries built from the item's own per-sentence notes, when they already
    explain every sentence in the learner's language (no model call needed).

    Many pick-the-correct-sentence items carry an English note on every
    sentence; others lack one on the correct sentence, or have only a joined
    note in the target language. Only decidable for an English learner (a
    CJK note could be the target language).
    """
    if _FAMILY.get(_LANG.get(nl_language_id, ('',))[0]) != 'latin':
        return None
    notes = [_clean(s.get('explanation'), _CAP['explanation']) for s in sents]
    if not all(notes) or any(_script_family(n) != 'latin' for n in notes):
        return None
    return [{'text': str(s.get('text')).strip(), 'is_correct': s.get('is_correct') is not False,
             'meaning': '', 'explanation': n, 'correction': None}
            for s, n in zip(sents, notes)]


def _texts(sents: Iterable[dict]) -> list[str]:
    return [str(s.get('text') or '').strip() for s in sents]


def _aligned(payload: Any, sents: list[dict]) -> Optional[list[dict]]:
    """``payload``'s entries when they were written for exactly these sentences
    with the current prompt."""
    if not isinstance(payload, dict) or payload.get('prompt_version') != PROMPT_VERSION:
        return None
    entries = payload.get('sentences')
    if not isinstance(entries, list) or len(entries) != len(sents):
        return None
    if [str(e.get('text') or '').strip() for e in entries] != _texts(sents):
        return None
    return entries


def _attach(content: dict, entries: list[dict], nl_language_id: int) -> None:
    content['option_explanations'] = [
        {'meaning': e.get('meaning') or '', 'explanation': e.get('explanation') or '',
         'correction': e.get('correction') or None}
        for e in entries
    ]
    code = _LANG.get(nl_language_id, (None,))[0]
    if code:
        content['explanation_language'] = code


# ---------------------------------------------------------------------------
# Prompt and validation
# ---------------------------------------------------------------------------

def build_prompt(sents: list[dict], tl_language_id: int, nl_language_id: int,
                 exercise_type: str = SPOT, target_word: Optional[str] = None,
                 corrected: Optional[str] = None) -> tuple[str, str]:
    """(system, user) messages for one item."""
    tl = _LANG.get(tl_language_id, (None, 'the target language'))[1]
    nl = _LANG.get(nl_language_id, (None, 'English'))[1]
    pick = exercise_type == PICK
    word = f'「{target_word.strip()}」' if target_word and target_word.strip() else 'the target word'
    lines = []
    for i, s in enumerate(sents, 1):
        right = s.get('is_correct') is not False
        tag = 'CORRECT' if right else ('WRONG' if pick else 'ERROR')
        line = f"{i}. [{tag}] {str(s.get('text')).strip()}"
        note = str((s.get('explanation') if pick else s.get('error_description')) or '').strip()
        if note and (pick or not right):
            line += f"\n   Teacher's note (may be in another language): {note}"
        if corrected and not pick and not right:
            line += f"\n   Corrected sentence: {corrected.strip()}"
        lines.append(line)
    system = (f"You are an experienced {tl} teacher writing answer feedback for a learner whose "
              f"native language is {nl}. You are precise about grammar and meaning and never "
              "invent errors.")
    if pick:
        task = (f'A "pick the correct sentence" exercise in {tl} about the word {word}. The learner '
                f'sees the sentences below and must pick the one that uses {word} correctly; the '
                'others misuse it. Which sentence is correct is already decided and marked; do not '
                'change that judgement.')
        meaning = (f'a natural {nl} translation of the correct sentence. For a wrong sentence, a '
                   'LITERAL translation of what it actually says, keeping the misuse visible (do '
                   'not translate what it was meant to say).')
        explanation = (f'one or two short sentences a learner can follow. For the correct sentence, '
                       f'say what {word} means here and why it fits. For a wrong sentence, say why '
                       f'{word} does not fit and, where natural, which word would. Where a '
                       f"teacher's note is given, keep its point, written in {nl}.")
        shape = '{"sentences": [{"index": 1, "meaning": "...", "explanation": "..."}, ...]}'
        extra = ''
    else:
        task = (f'A "spot the error" exercise in {tl}. The learner sees the sentences below and must '
                'pick the one that contains an error. Which sentence is wrong is already decided and '
                'marked; do not change that judgement.')
        meaning = (f'for a correct sentence, a natural {nl} translation. For the error sentence, a '
                   'LITERAL translation of what it actually says, mistake included, so the learner '
                   'can see what is wrong (if a wrong verb is used, translate that wrong verb; do '
                   'not translate what it was meant to say).')
        explanation = ('one or two short sentences a learner can follow. For a correct sentence, say '
                       'why it is correct: point to the grammar or word use a learner might doubt. '
                       'For the error sentence, name the mistake precisely and say why it is wrong.')
        shape = ('{"sentences": [{"index": 1, "meaning": "...", "explanation": "...", '
                 '"correction": null}, ...]}')
        extra = (f'- "correction": for the error sentence only, the corrected {tl} sentence, '
                 'changing as little as possible (where a corrected sentence is given above, '
                 'use it exactly); null for the others.\n')
    user = (
        task + '\n\nSentences:\n' + '\n'.join(lines) + '\n\n'
        f'For EVERY sentence, write in {nl}:\n'
        f'- "meaning": {meaning}\n'
        f'- "explanation": {explanation}\n' + extra + '\n'
        f'Quote {tl} words in {tl} script. Everything else in {nl}. Plain text, no markdown. '
        'Do not begin an explanation with a verdict such as "Correct" or "Wrong": the app '
        'shows the verdict.\n\n'
        f'Return only JSON: {shape}'
    )
    return system, user


def _script_family(text: str) -> str:
    from services.vocabulary_ladder.deterministic.definition_match import script_family
    return script_family(text)


def _clean(value: Any, cap: int) -> str:
    text = ' '.join(str(value or '').split())
    return text[:cap].rstrip()


def parse(raw: Any, sents: list[dict], nl_language_id: int,
          exercise_type: str = SPOT, corrected: Optional[str] = None) -> Optional[list[dict]]:
    """Validated entries (one per sentence, in order), or None when unusable.

    Unusable: not one entry per sentence, an empty explanation, or prose not
    in the learner's script (checked for English, where it is decidable).
    A correction is kept only on the wrong sentence of a spot-the-error item;
    ``corrected`` (the reviewed sentence from the item's generation asset)
    takes its place when given.
    """
    entries = raw.get('sentences') if isinstance(raw, dict) else raw
    if not isinstance(entries, list) or len(entries) != len(sents):
        return None
    by_index: dict[int, dict] = {}
    for pos, e in enumerate(entries, 1):
        if not isinstance(e, dict):
            return None
        try:
            idx = int(e.get('index', pos))
        except (TypeError, ValueError):
            idx = pos
        by_index.setdefault(idx, e)
    if sorted(by_index) != list(range(1, len(sents) + 1)):
        by_index = {pos: e for pos, e in enumerate(entries, 1)}
    want_family = _FAMILY.get(_LANG.get(nl_language_id, ('',))[0])
    out = []
    for pos, s in enumerate(sents, 1):
        e = by_index[pos]
        explanation = _clean(e.get('explanation'), _CAP['explanation'])
        meaning = _clean(e.get('meaning'), _CAP['meaning'])
        if not explanation:
            return None
        if want_family == 'latin' and _script_family(explanation) != 'latin':
            return None
        wrong = s.get('is_correct') is False
        correction = ''
        if wrong and exercise_type == SPOT:
            correction = _clean(corrected, _CAP['correction']) if corrected else \
                _clean(e.get('correction'), _CAP['correction'])
        out.append({'text': str(s.get('text')).strip(), 'is_correct': not wrong,
                    'meaning': meaning, 'explanation': explanation,
                    'correction': correction or None})
    return out


def _models() -> list[str]:
    primary = (getattr(Config, 'EXERCISE_EXPLANATION_MODEL', '') or '').strip()
    fallback = (getattr(Config, 'EXERCISE_EXPLANATION_FALLBACK_MODEL', '') or '').strip()
    return [m for m in (primary, fallback if fallback != primary else '') if m]


def generate(content: dict, tl_language_id: int, nl_language_id: int,
             exercise_id: Optional[str] = None, exercise_type: str = SPOT,
             corrected: Optional[str] = None) -> Optional[tuple[dict, str]]:
    """(payload, model) for one item, or None when no model gave a usable answer.

    ``corrected``: the reviewed corrected sentence of a spot item (``stored_correction``).
    """
    sents = sentences_of(content)
    if sents is None:
        return None
    from services.llm_service import call_llm
    system, user = build_prompt(sents, tl_language_id, nl_language_id, exercise_type,
                                (content or {}).get('target_word'), corrected)
    for model in _models():
        try:
            raw = call_llm(
                user, system_prompt=system, model=model, response_format='json',
                temperature=0.2, max_tokens=_MAX_TOKENS, timeout=_LLM_TIMEOUT_S,
                pipeline='exercise_explanations',
                task_name=_TASK_NAME.get(exercise_type, 'exercise_explanation'),
                template_version=PROMPT_VERSION, artifact_id=exercise_id,
                language_code=_LANG.get(tl_language_id, (None,))[0],
            )
        except Exception as exc:
            logger.warning('explanation call failed (model=%s exercise=%s): %s',
                           model, exercise_id, exc)
            continue
        entries = parse(raw, sents, nl_language_id, exercise_type, corrected)
        if entries is not None:
            return {'sentences': entries, 'prompt_version': PROMPT_VERSION}, model
        logger.warning('explanation from %s unusable for exercise %s', model, exercise_id)
    return None


# ---------------------------------------------------------------------------
# Cache: process memory, then the table
# ---------------------------------------------------------------------------

def _remember(key: tuple[str, int], version: int, payload: dict) -> None:
    with _lock:
        _memory[key] = (version, payload)
        _memory.move_to_end(key)
        while len(_memory) > _MEMORY_MAX:
            _memory.popitem(last=False)


def _from_memory(key: tuple[str, int], version: int) -> Optional[dict]:
    with _lock:
        hit = _memory.get(key)
        if hit is None or hit[0] != version:
            return None
        _memory.move_to_end(key)
        return hit[1]


def _table_usable() -> bool:
    return time.monotonic() >= _table_down_until


def _table_failed(exc: Exception) -> None:
    global _table_down_until
    _table_down_until = time.monotonic() + _TABLE_RETRY_S
    logger.warning('%s unavailable (explanations kept in memory only): %s', TABLE, exc)


def _read_rows(db, exercise_ids: list[str], nl_language_id: int) -> dict[str, dict]:
    if not exercise_ids or db is None or not _table_usable():
        return {}
    try:
        rows = (db.table(TABLE).select('exercise_id, content_version, payload')
                .in_('exercise_id', exercise_ids).eq('nl_language_id', nl_language_id)
                .execute().data or [])
    except Exception as exc:
        _table_failed(exc)
        return {}
    return {str(r['exercise_id']): r for r in rows if r.get('exercise_id')}


def _write_row(db, exercise_id: str, nl_language_id: int, version: int,
               payload: dict, model: str) -> None:
    if db is None or not _table_usable():
        return
    try:
        db.table(TABLE).upsert({
            'exercise_id': exercise_id, 'nl_language_id': nl_language_id,
            'content_version': version, 'payload': payload, 'model': model,
            'prompt_version': PROMPT_VERSION,
        }, on_conflict='exercise_id,nl_language_id').execute()
    except Exception as exc:
        _table_failed(exc)


def _version(item: dict) -> int:
    try:
        return int(item.get('content_version') or 0)
    except (TypeError, ValueError):
        return 0


def _sense_of(item: dict) -> Optional[int]:
    """The item's sense: ``sense_id`` in practice payloads, ``word_sense_id`` in
    exercise rows (new-word drill, prestudy, ``get_or_generate``)."""
    value = item.get('sense_id') or item.get('word_sense_id')
    try:
        sense = int(value)
    except (TypeError, ValueError):
        return None
    return sense if sense > 0 else None


def _read_files(language_id: int, nl_language_id: int,
                sense_ids: list[int]) -> dict[str, dict]:
    """Pre-written entries ``{exercise_id: {content_version, model, payload}}`` from the
    senses' Storage files at the current prompt version. Never raises."""
    if not sense_ids or language_id not in _LANG or nl_language_id not in _LANG:
        return {}
    return explanation_files.read_for_senses(language_id, sense_ids, nl_language_id,
                                             PROMPT_VERSION, deadline_s=_FILE_DEADLINE_S)


@dataclass
class Prefetched:
    """What ``prefetch`` read, for ``prepare_items(prefetched=...)``: Storage file entries
    (``files``) and table rows (``rows``), each ``{exercise_id: {'content_version',
    'payload', ...}}``. A file entry is preferred to a row for the same item."""
    files: dict[str, dict] = field(default_factory=dict)
    rows: dict[str, dict] = field(default_factory=dict)


def _read_sources(db, language_id: int, nl_language_id: int, exercise_ids: list[str],
                  sense_ids: list[int]) -> Prefetched:
    """The Storage files of ``sense_ids`` and the table rows of ``exercise_ids``. When
    both are wanted the file read waits on ``_read_pool`` while this thread reads the
    table, so the two round trips overlap."""
    want_rows = bool(exercise_ids) and db is not None and _table_usable()
    if not (want_rows and sense_ids):
        return Prefetched(files=_read_files(language_id, nl_language_id, sense_ids),
                          rows=_read_rows(db, exercise_ids, nl_language_id))
    try:
        pending: Optional[Future] = _read_pool().submit(
            _read_files, language_id, nl_language_id, sense_ids)
    except RuntimeError:                  # pool shut down (interpreter exit)
        pending = None
    rows = _read_rows(db, exercise_ids, nl_language_id)
    if pending is None:
        return Prefetched(files=_read_files(language_id, nl_language_id, sense_ids), rows=rows)
    try:
        files = pending.result(timeout=_FILE_DEADLINE_S + 1.0)
    except Exception as exc:              # read_for_senses keeps its own deadline
        logger.warning('explanation files read did not finish: %s: %s',
                       type(exc).__name__, exc)
        files = {}
    return Prefetched(files=files, rows=rows)


def _usable(cached: Any, version: int, sents: list[dict]) -> Optional[tuple[list[dict], dict]]:
    """(entries, payload) of a file entry or table row written for this content version
    and these sentences with the current prompt; None otherwise."""
    if not isinstance(cached, dict) or _version(cached) != version:
        return None
    entries = _aligned(cached.get('payload'), sents)
    return None if entries is None else (entries, cached['payload'])


def stored_correction(db, sense_id: Optional[int], content: dict) -> Optional[str]:
    """The reviewed corrected sentence for a spot item's wrong sentence.

    Every spot item is rendered from a ``prompt3_transforms_A|B`` asset whose
    ``level_7`` holds ``incorrect_sentence`` and ``corrected_sentence``; the
    exercise content keeps only the former. None when not found.
    """
    sents = sentences_of(content)
    if db is None or not sense_id or sents is None:
        return None
    wrong = {str(s.get('text')).strip() for s in sents if s.get('is_correct') is False}
    try:
        rows = (db.table('word_assets').select('content').eq('sense_id', int(sense_id))
                .in_('asset_type', ['prompt3_transforms_A', 'prompt3_transforms_B'])
                .execute().data or [])
    except Exception as exc:
        logger.warning('explanation: corrected-sentence lookup failed for sense %s: %s',
                       sense_id, exc)
        return None
    for row in rows:
        l7 = ((row.get('content') or {}).get('level_7') or {})
        if str(l7.get('incorrect_sentence') or '').strip() in wrong and l7.get('corrected_sentence'):
            return str(l7['corrected_sentence']).strip()
    return None


def _job(db, exercise_id: str, content: dict, version: int, tl_language_id: int,
         nl_language_id: int, exercise_type: str, sense_id: Optional[int] = None) -> Optional[dict]:
    key = (exercise_id, nl_language_id)
    try:
        # A file read that missed the request's deadline has usually landed by
        # now: serve the pre-written entry instead of paying for a model.
        written = _file_entry(tl_language_id, nl_language_id, sense_id, exercise_id, version,
                              content)
        if written is not None:
            _remember(key, version, written)
            return written
        corrected = stored_correction(db, sense_id, content) if exercise_type == SPOT else None
        result = generate(content, tl_language_id, nl_language_id, exercise_id, exercise_type,
                          corrected)
        if result is None:
            return None
        payload, model = result
        _remember(key, version, payload)
        _write_row(db, exercise_id, nl_language_id, version, payload, model)
        return payload
    finally:
        with _lock:
            _inflight.pop(key, None)


def _file_entry(language_id: int, nl_language_id: int, sense_id: Optional[int],
                exercise_id: str, version: int, content: dict) -> Optional[dict]:
    """The current pre-written payload of one item from its sense's file, or None."""
    if not sense_id or language_id not in _LANG or nl_language_id not in _LANG:
        return None
    try:
        entry = explanation_files.read_for_senses(
            language_id, [int(sense_id)], nl_language_id, PROMPT_VERSION,
            deadline_s=_JOB_FILE_DEADLINE_S).get(str(exercise_id))
    except Exception:
        return None
    sents = sentences_of(content)
    if not entry or sents is None or int(entry.get('content_version') or 0) != version:
        return None
    payload = entry.get('payload')
    return payload if _aligned(payload, sents) is not None else None


def _start(db, exercise_id: str, content: dict, version: int, tl_language_id: int,
           nl_language_id: int, exercise_type: str = SPOT,
           sense_id: Optional[int] = None) -> Future:
    """The generation for this key, started unless one is already running."""
    key = (exercise_id, nl_language_id)
    executor = _pool()                    # outside the lock: _pool takes it too
    with _lock:
        fut = _inflight.get(key)
        if fut is not None:
            return fut
        fut = Future()
        _inflight[key] = fut
    snapshot = dict(content)

    def run():
        try:
            fut.set_result(_job(db, exercise_id, snapshot, version, tl_language_id,
                                nl_language_id, exercise_type, sense_id))
        except BaseException as exc:      # never leave a waiter hanging
            fut.set_exception(exc)

    executor.submit(run)
    return fut


# ---------------------------------------------------------------------------
# Serving
# ---------------------------------------------------------------------------

def _wanted(language_id: Optional[int], nl_language_id: Optional[int]) -> bool:
    return bool(enabled() and language_id and nl_language_id)


def prefetch(db, items: list[dict], *, language_id: Optional[int],
             nl_language_id: Optional[int], id_key: str = 'exercise_id',
             type_key: str = 'exercise_type') -> Optional[Prefetched]:
    """The Storage file entries and table rows ``prepare_items`` will need, read
    from ids, types and senses alone so it can run while content is still being
    fetched (the two reads overlap). None when nothing applies
    (``prepare_items`` then reads for itself)."""
    if not items or not _wanted(language_id, nl_language_id):
        return None
    wanted = [i for i in items
              if isinstance(i, dict) and supported(i.get(type_key)) and i.get(id_key)]
    if not wanted:
        return None
    ids = sorted({str(i.get(id_key)) for i in wanted})
    senses = sorted({s for s in (_sense_of(i) for i in wanted) if s is not None})
    return _read_sources(db, int(language_id), int(nl_language_id), ids, senses)


def prepare_items(db, items: list[dict], *, language_id: Optional[int],
                  nl_language_id: Optional[int], id_key: str = 'exercise_id',
                  type_key: str = 'exercise_type', warm_limit: Optional[int] = None,
                  prefetched: Optional[Union[Prefetched, dict[str, dict]]] = None) -> int:
    """Attach cached explanations to ``items`` in place; warm the rest.

    ``prefetched``: what ``prefetch`` returned (no Storage or table read here
    then). A plain dict, the pre-Storage shape, is taken as the table rows and
    the files are still read here. Returns how many generations were started.
    Never raises.
    """
    if not items or not _wanted(language_id, nl_language_id):
        return 0
    try:
        return _prepare(db, items, int(language_id), int(nl_language_id), id_key, type_key,
                        warm_limit, prefetched)
    except Exception as exc:
        logger.warning('explanations prepare failed (non-fatal): %s', exc)
        return 0


def _prepare(db, items, language_id, nl_language_id, id_key, type_key, warm_limit,
             prefetched=None) -> int:
    todo: list[tuple[dict, str, list[dict]]] = []
    for item in items:
        if not isinstance(item, dict) or not supported(item.get(type_key)):
            continue
        eid, content = item.get(id_key), item.get('content')
        sents = sentences_of(content)
        if not eid or sents is None:
            continue
        entries = stored_entries(sents, nl_language_id) or \
            _aligned(_from_memory((str(eid), nl_language_id), _version(item)), sents)
        if entries is not None:
            _attach(content, entries, nl_language_id)
        else:
            todo.append((item, str(eid), sents))
    if not todo:
        return 0
    if isinstance(prefetched, Prefetched):
        found = prefetched
    else:
        senses = sorted({s for s in (_sense_of(item) for item, _, _ in todo) if s is not None})
        if isinstance(prefetched, dict):
            found = Prefetched(files=_read_files(language_id, nl_language_id, senses),
                               rows=prefetched)
        else:
            found = _read_sources(db, language_id, nl_language_id,
                                  [eid for _, eid, _ in todo], senses)
    missing = []
    for item, eid, sents in todo:
        version = _version(item)
        hit = _usable(found.files.get(eid), version, sents) or \
            _usable(found.rows.get(eid), version, sents)
        if hit is not None:
            entries, payload = hit
            _remember((eid, nl_language_id), version, payload)
            _attach(item['content'], entries, nl_language_id)
        else:
            missing.append((item, eid))
    limit = Config.EXERCISE_EXPLANATION_WARM_PER_REQUEST if warm_limit is None else warm_limit
    started = 0
    for item, eid in missing[:max(0, int(limit))]:
        _start(db, eid, item['content'], _version(item), language_id, nl_language_id,
               item.get(type_key), item.get('sense_id') or item.get('word_sense_id'))
        started += 1
    return started


def get_or_generate(db, exercise_id: str, nl_language_id: int,
                    timeout: float = 25.0) -> tuple[str, Optional[dict]]:
    """One item's explanations for the learner's language.

    Returns (status, payload): 'ready' with the payload, 'pending' (still
    being written: ask again shortly), 'unsupported' (not an explainable
    item) or 'unavailable' (no model gave a usable answer, or disabled).
    """
    if not enabled():
        return 'unavailable', None
    row = _exercise_row(db, exercise_id)
    if row is None or not supported(row.get('exercise_type')):
        return 'unsupported', None
    content, version = row.get('content'), _version(row)
    sents = sentences_of(content)
    if sents is None:
        return 'unsupported', None
    key = (str(exercise_id), int(nl_language_id))
    entries = stored_entries(sents, int(nl_language_id)) or \
        _aligned(_from_memory(key, version), sents)
    if entries is None:
        # The sense's pre-written file first; the table only when it has nothing usable.
        sense = _sense_of(row)
        files = _read_files(int(row.get('language_id') or 0), int(nl_language_id),
                            [sense] if sense is not None else [])
        hit = _usable(files.get(str(exercise_id)), version, sents)
        if hit is None:
            hit = _usable(_read_rows(db, [str(exercise_id)], int(nl_language_id))
                          .get(str(exercise_id)), version, sents)
        if hit is not None:
            entries, payload = hit
            _remember(key, version, payload)
    if entries is None:
        fut = _start(db, str(exercise_id), content, version,
                     int(row.get('language_id') or 0), int(nl_language_id),
                     row.get('exercise_type'), row.get('word_sense_id'))
        try:
            payload = fut.result(timeout=timeout)
        except FutureTimeout:
            return 'pending', None
        except Exception as exc:
            logger.warning('explanation generation failed for %s: %s', exercise_id, exc)
            return 'unavailable', None
        entries = _aligned(payload, sents) if payload else None
        if entries is None:
            return 'unavailable', None
    shaped: dict = {}
    _attach(shaped, entries, int(nl_language_id))
    return 'ready', shaped


def _exercise_row(db, exercise_id: str) -> Optional[dict]:
    """The exercise with its content (ADR-049 store), or None."""
    from services.exercise_content import store
    try:
        rows = (db.table('exercises')
                .select('id, word_sense_id, exercise_type, language_id, content_version, is_active')
                .eq('id', exercise_id).limit(1).execute().data or [])
    except Exception as exc:
        logger.warning('explanation: exercise lookup failed for %s: %s', exercise_id, exc)
        return None
    if not rows or rows[0].get('is_active') is False:
        return None
    row = dict(rows[0])
    try:
        store.hydrate([row], language_id=row.get('language_id'), drop_missing=False)
    except Exception as exc:
        logger.warning('explanation: content lookup failed for %s: %s', exercise_id, exc)
        return None
    return row if row.get('content') is not None else None
