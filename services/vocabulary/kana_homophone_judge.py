"""
Kana-homophone disambiguation for Japanese vocab identity.

Background — see the module docstring on ``JapaneseProcessor`` in
``services/vocabulary/processors/japanese.py`` for the full mechanism. In
short: ``dim_vocabulary.lemma`` is a flat text key, and Japanese has real
homophones (城/白/... all read しろ; 為る is UniDic's shared kanji spelling
straddling both する and 成る/なる). Two structurally different words can
therefore end up sharing one vocab row, and whichever sense got written to
it first silently "wins" for every future token that resolves to the same
text — surfacing an unrelated definition on click.

This module answers two different questions with the same cheap-LLM-judge
shape, and deliberately does NOT live under
``services/exercise_generation/judges/`` — those all answer an
accept/flag/reject question about a single candidate; both judges here
answer a *selection* question over several candidates instead.

pick_homophone_sense
---------------------
Serve-adjacent: runs while a test is being generated for a live learner
request. Given a token's sentence context and every existing
``dim_vocabulary`` row that shares its reading, asks which one (if any) the
token actually is. Fails open to "no match" (None) on any error — a
learner's test generation must never break because this judge is
unreachable, mirroring the fail-open contract in
``services/exercise_generation/judges/base.py``. The caller treats None
exactly like "found zero/one candidate" — i.e. falls through to the
existing create-or-reuse-by-exact-lemma behavior, so an unreachable judge
degrades to today's behavior rather than to a hard failure.

classify_kana_lemma
--------------------
Offline audit tool, not part of any live request path. Given an existing
kana-only ``dim_vocabulary`` row (lemma, POS, its stored definitions), asks
whether it is a genuine standalone dictionary word or a UniDic segmentation
fragment of a longer compound/conjugation that got mistakenly registered on
its own (see scripts/audit_kana_fragments.py). Failure here means "couldn't
classify" (``ok: False``) — the caller must leave the row alone, not assume
an answer.
"""

from __future__ import annotations

import logging

from services.llm_service import call_llm
from services.prompt_service import get_template_config

logger = logging.getLogger(__name__)

_PIPELINE = 'vocab_ja_homophone'

_PICK_TASK = 'judge_kana_homophone_pick'
_PICK_PT = 'ja_kana_homophone_pick'

_FRAGMENT_TASK = 'judge_kana_fragment_check'
_FRAGMENT_PT = 'ja_kana_fragment_check'

# (prompt_templates task_name, language_id) -> cfg. Both tasks are ja-only
# (language_id=3) today, but keyed generally in case that ever changes.
_cfg_cache: dict[tuple[str, int], dict] = {}


def _load_cfg(db, pt_name: str, language_id: int) -> dict:
    key = (pt_name, language_id)
    if key not in _cfg_cache:
        _cfg_cache[key] = get_template_config(db, pt_name, language_id)
    return _cfg_cache[key]


def pick_homophone_sense(
    db,
    *,
    surface: str,
    sentence: str,
    reading: str,
    candidates: list[dict],
    language_id: int,
) -> int | None:
    """Which existing vocab_id (if any) this kana-derived token actually is.

    ``candidates``: dim_vocabulary rows sharing ``reading``, each
    ``{'vocab_id': int, 'lemma': str, 'pos': str | None, 'definition': str}``.
    Callers should only invoke this with >= 2 candidates — 0 or 1 needs no
    judge and should be handled before calling in.

    Returns the chosen vocab_id, or None when the judge says none of the
    candidates fit (a distinct word — the caller's existing
    create-or-reuse-by-lemma path handles that case) or when the judge
    could not run at all.
    """
    if len(candidates) < 2:
        return candidates[0]['vocab_id'] if candidates else None

    try:
        cfg = _load_cfg(db, _PICK_PT, language_id)
    except Exception as exc:
        logger.warning('kana_homophone_pick: template load failed: %s', exc)
        return None

    numbered = '\n'.join(
        f"{i + 1}. {c['lemma']} ({c.get('pos') or '?'}): "
        f"{c.get('definition') or '(no definition)'}"
        for i, c in enumerate(candidates)
    )
    prompt = cfg['template'].format(
        surface=surface,
        sentence=sentence,
        reading=reading,
        candidates_numbered=numbered,
    )

    try:
        result = call_llm(
            prompt,
            model=cfg['model'],
            temperature=0.0,
            response_format='json_object',
            provider=cfg['provider'],
            pipeline=_PIPELINE,
            task_name=_PICK_TASK,
            template_version=cfg['version'],
            language_code='ja',
        )
    except Exception as exc:
        logger.warning('kana_homophone_pick: LLM call failed for %r: %s', surface, exc)
        return None

    if not isinstance(result, dict):
        logger.warning(
            'kana_homophone_pick: non-dict response (%s) for %r',
            type(result).__name__, surface,
        )
        return None

    try:
        choice = int(result.get('choice', 0))
    except (TypeError, ValueError):
        logger.warning('kana_homophone_pick: unparseable choice for %r: %r', surface, result.get('choice'))
        return None

    if choice < 1 or choice > len(candidates):
        return None  # 0 (or out of range) = "none of these fit"
    return candidates[choice - 1]['vocab_id']


def classify_kana_lemma(
    db,
    *,
    lemma: str,
    pos: str | None,
    definitions: list[str],
    language_id: int,
) -> dict:
    """Is a stored kana-only lemma a real word or a segmentation fragment?

    Returns ``{'ok': True, 'is_fragment': bool, 'likely_source_word': str,
    'reason': str}`` on success, ``{'ok': False}`` on any failure — treat
    that as "skip this row", not as a negative classification.
    """
    try:
        cfg = _load_cfg(db, _FRAGMENT_PT, language_id)
    except Exception as exc:
        logger.warning('kana_fragment_check: template load failed: %s', exc)
        return {'ok': False}

    numbered = '\n'.join(f'{i + 1}. {d}' for i, d in enumerate(definitions)) or '(no definitions on file)'
    prompt = cfg['template'].format(
        lemma=lemma,
        pos=pos or '?',
        definitions_numbered=numbered,
    )

    try:
        result = call_llm(
            prompt,
            model=cfg['model'],
            temperature=0.0,
            response_format='json_object',
            provider=cfg['provider'],
            pipeline=_PIPELINE,
            task_name=_FRAGMENT_TASK,
            template_version=cfg['version'],
            language_code='ja',
        )
    except Exception as exc:
        logger.warning('kana_fragment_check: LLM call failed for %r: %s', lemma, exc)
        return {'ok': False}

    if not isinstance(result, dict):
        logger.warning(
            'kana_fragment_check: non-dict response (%s) for %r',
            type(result).__name__, lemma,
        )
        return {'ok': False}

    return {
        'ok': True,
        'is_fragment': bool(result.get('is_fragment')),
        'likely_source_word': str(result.get('likely_source_word') or ''),
        'reason': str(result.get('reason') or ''),
    }
