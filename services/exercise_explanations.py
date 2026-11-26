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
* ``prepare_items`` (session assembly, new-word drill): attaches what is
  already cached as ``content['option_explanations']`` (aligned with
  ``content['sentences']``) and starts background generation for up to
  ``Config.EXERCISE_EXPLANATION_WARM_PER_REQUEST`` items that have none, so
  they are usually ready before the learner answers.
* ``get_or_generate`` (``GET /api/practice/explanations/<exercise_id>``): what
  the renderer asks for when an item arrived without them; waits for a
  generation already in flight rather than starting a second.

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
from typing import Any, Iterable, Optional

from config import Config

logger = logging.getLogger(__name__)

SPOT = 'spot_incorrect_sentence'          # pick the sentence with an error
PICK = 'semantic_discrimination'          # pick the sentence that uses the word correctly
TYPES = frozenset({SPOT, PICK})
_TASK_NAME = {SPOT: 'spot_error_explanation', PICK: 'pick_sentence_explanation'}
PROMPT_VERSION = 1
TABLE = 'exercise_explanations'

_MEMORY_MAX = 2000
_TABLE_RETRY_S = 300          # after a failed table read, how long to stop asking
_WORKERS = 4
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


def enabled() -> bool:
    return bool(getattr(Config, 'EXERCISE_EXPLANATIONS_ENABLED', True))


def supported(exercise_type: Optional[str]) -> bool:
    return exercise_type in TYPES


def reset_state() -> None:
    """Forget cached explanations and the table state (tests)."""
    global _table_down_until
    with _lock:
        _memory.clear()
        _inflight.clear()
        _table_down_until = 0.0


def _pool() -> ThreadPoolExecutor:
    global _executor
    with _lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(max_workers=_WORKERS, thread_name_prefix='explain')
        return _executor


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
    """``payload``'s entries when they were written for exactly these sentences."""
    entries = (payload or {}).get('sentences') if isinstance(payload, dict) else None
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
                 exercise_type: str = SPOT, target_word: Optional[str] = None) -> tuple[str, str]:
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
        lines.append(line)
    system = (f"You are an experienced {tl} teacher writing answer feedback for a learner whose "
              f"native language is {nl}. You are precise about grammar and meaning and never "
              "invent errors.")
    if pick:
        task = (f'A "pick the correct sentence" exercise in {tl} about the word {word}. The learner '
                f'sees the sentences below and must pick the one that uses {word} correctly; the '
                'others misuse it. Which sentence is correct is already decided and marked; do not '
                'change that judgement.')
        meaning = (f'a natural {nl} translation of what the sentence says (for a wrong sentence, '
                   'what it literally says).')
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
        meaning = (f'a natural {nl} translation of what the sentence says (for the error sentence, '
                   'what it is trying to say).')
        explanation = ('one or two short sentences a learner can follow. For a correct sentence, say '
                       'why it is correct: point to the grammar or word use a learner might doubt. '
                       'For the error sentence, name the mistake precisely and say why it is wrong.')
        shape = ('{"sentences": [{"index": 1, "meaning": "...", "explanation": "...", '
                 '"correction": null}, ...]}')
        extra = (f'- "correction": for the error sentence only, the corrected {tl} sentence, '
                 'changing as little as possible; null for the others.\n')
    user = (
        task + '\n\nSentences:\n' + '\n'.join(lines) + '\n\n'
        f'For EVERY sentence, write in {nl}:\n'
        f'- "meaning": {meaning}\n'
        f'- "explanation": {explanation}\n' + extra + '\n'
        f'Quote {tl} words in {tl} script. Everything else in {nl}. Plain text, no markdown.\n\n'
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
          exercise_type: str = SPOT) -> Optional[list[dict]]:
    """Validated entries (one per sentence, in order), or None when unusable.

    Unusable: not one entry per sentence, an empty explanation, or prose not
    in the learner's script (checked for English, where it is decidable).
    A correction is kept only on the wrong sentence of a spot-the-error item.
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
        correction = (_clean(e.get('correction'), _CAP['correction'])
                      if wrong and exercise_type == SPOT else '')
        out.append({'text': str(s.get('text')).strip(), 'is_correct': not wrong,
                    'meaning': meaning, 'explanation': explanation,
                    'correction': correction or None})
    return out


def _models() -> list[str]:
    primary = (getattr(Config, 'EXERCISE_EXPLANATION_MODEL', '') or '').strip()
    fallback = (getattr(Config, 'EXERCISE_EXPLANATION_FALLBACK_MODEL', '') or '').strip()
    return [m for m in (primary, fallback if fallback != primary else '') if m]


def generate(content: dict, tl_language_id: int, nl_language_id: int,
             exercise_id: Optional[str] = None,
             exercise_type: str = SPOT) -> Optional[tuple[dict, str]]:
    """(payload, model) for one item, or None when no model gave a usable answer."""
    sents = sentences_of(content)
    if sents is None:
        return None
    from services.llm_service import call_llm
    system, user = build_prompt(sents, tl_language_id, nl_language_id, exercise_type,
                                (content or {}).get('target_word'))
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
        entries = parse(raw, sents, nl_language_id, exercise_type)
        if entries is not None:
            return {'sentences': entries}, model
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


def _job(db, exercise_id: str, content: dict, version: int,
         tl_language_id: int, nl_language_id: int, exercise_type: str) -> Optional[dict]:
    key = (exercise_id, nl_language_id)
    try:
        result = generate(content, tl_language_id, nl_language_id, exercise_id, exercise_type)
        if result is None:
            return None
        payload, model = result
        _remember(key, version, payload)
        _write_row(db, exercise_id, nl_language_id, version, payload, model)
        return payload
    finally:
        with _lock:
            _inflight.pop(key, None)


def _start(db, exercise_id: str, content: dict, version: int,
           tl_language_id: int, nl_language_id: int, exercise_type: str = SPOT) -> Future:
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
                                nl_language_id, exercise_type))
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
             type_key: str = 'exercise_type') -> Optional[dict[str, dict]]:
    """The cached rows ``prepare_items`` will need, read from ids and types
    alone so it can run while content is still being fetched. None when
    nothing applies (``prepare_items`` then reads for itself)."""
    if not items or not _wanted(language_id, nl_language_id):
        return None
    ids = sorted({str(i.get(id_key)) for i in items
                  if isinstance(i, dict) and supported(i.get(type_key)) and i.get(id_key)})
    if not ids:
        return None
    return _read_rows(db, ids, int(nl_language_id))


def prepare_items(db, items: list[dict], *, language_id: Optional[int],
                  nl_language_id: Optional[int], id_key: str = 'exercise_id',
                  type_key: str = 'exercise_type', warm_limit: Optional[int] = None,
                  prefetched: Optional[dict[str, dict]] = None) -> int:
    """Attach cached explanations to ``items`` in place; warm the rest.

    ``prefetched``: rows from ``prefetch`` (no table read here then).
    Returns how many generations were started. Never raises.
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
    rows = prefetched if prefetched is not None else \
        _read_rows(db, [eid for _, eid, _ in todo], nl_language_id)
    missing = []
    for item, eid, sents in todo:
        row = rows.get(eid)
        entries = None
        if row is not None and int(row.get('content_version') or 0) == _version(item):
            entries = _aligned(row.get('payload'), sents)
        if entries is not None:
            _remember((eid, nl_language_id), _version(item), row['payload'])
            _attach(item['content'], entries, nl_language_id)
        else:
            missing.append((item, eid))
    limit = Config.EXERCISE_EXPLANATION_WARM_PER_REQUEST if warm_limit is None else warm_limit
    started = 0
    for item, eid in missing[:max(0, int(limit))]:
        _start(db, eid, item['content'], _version(item), language_id, nl_language_id,
               item.get(type_key))
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
        cached = _read_rows(db, [str(exercise_id)], int(nl_language_id)).get(str(exercise_id))
        if cached is not None and int(cached.get('content_version') or 0) == version:
            entries = _aligned(cached.get('payload'), sents)
            if entries is not None:
                _remember(key, version, cached['payload'])
    if entries is None:
        fut = _start(db, str(exercise_id), content, version,
                     int(row.get('language_id') or 0), int(nl_language_id),
                     row.get('exercise_type'))
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
