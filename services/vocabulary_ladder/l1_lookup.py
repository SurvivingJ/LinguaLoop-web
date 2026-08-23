"""
Deterministic L1 (phonetic recognition) distractor lookup.

Replaces the LLM's job of *finding and verifying* audio-confusable real
words with a lookup against a build-once phonetic trie — see
``.claude/reviews/l1-phonetic-trie-architecture.md`` and
``services/vocabulary_ladder/phonetic_trie/``. Currently **ja only**; zh/en
still generate L1 through the LLM (``vocab_prompt2_exercises``) until their
own tries are built (architecture doc §7 recommends zh next).

``exercise_renderer._render_phonetic`` calls :func:`build_candidates` first.
A ``None`` return means "no trie for this language, or nothing usable came
out of it" — the caller falls back to the existing LLM-generated
``level_1`` asset unchanged, so a coverage gap degrades to today's
behavior rather than silently losing the item.

Candidates that DO come from the trie still go through the existing
``ladder_l1_distractor_judge`` afterwards, unchanged. The trie only
replaces existence/accent verification (the part the judge kept getting
wrong per TASK-735) — it does not replace the judge's one remaining
legitimate job, synonymy and register fit, which nothing about a
pronunciation lookup can check (architecture doc §5).
"""

from __future__ import annotations

import logging
import os
import random

from wordfreq import zipf_frequency

from services.vocabulary.model_cache import model_cache
from services.vocabulary_ladder.phonetic_trie.ja_mora import to_morae
from services.vocabulary_ladder.phonetic_trie.trie import PhoneticTrie
from services.vocabulary_ladder.tier_gate import profile_for_tier, tier_for_lemma

logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_JA_TRIE_PATH = os.path.join(_ROOT, 'data', 'content_builds', 'phonetic_trie', 'ja_mora_trie.pkl')

# language_id -> (trie build artifact path, mora/phoneme tokenizer, wordfreq code).
# Adding zh/en here (once their tries are built, per the architecture doc's
# recommended zh-then-en order) is the only change exercise_renderer.py's
# caller ever needs — it already dispatches purely off this registry.
_TRIE_REGISTRY: dict[int, tuple[str, callable, str]] = {
    3: (_JA_TRIE_PATH, to_morae, 'ja'),  # ja
}

# Sent to the judge, not to the learner — the judge keeps at most 3
# (exercise_renderer._render_phonetic's existing contract). Oversampling
# here is what actually raises the render rate: unlike the LLM path, a
# trie-sourced candidate can never fail on existence or accent, so the only
# way the judge drops one is a real synonymy/register call, and giving it
# more to choose from means one or two such drops don't sink the item.
_MAX_CANDIDATES = 10


def _load_trie(path: str) -> PhoneticTrie | None:
    if not os.path.exists(path):
        logger.warning(
            "Phonetic trie not found at %s -- run scripts/build_ja_mora_trie.py "
            "to build it. Falling back to the LLM-generated level_1 asset.", path,
        )
        return None
    try:
        return PhoneticTrie.load(path)
    except Exception as exc:
        logger.warning("Failed to load phonetic trie from %s: %s", path, exc)
        return None


def _get_trie(language_id: int, path: str) -> PhoneticTrie | None:
    return model_cache.get(f'phonetic_trie_{language_id}', lambda: _load_trie(path))


def available(language_id: int) -> bool:
    """Whether a phonetic trie is registered (and loads) for this language."""
    entry = _TRIE_REGISTRY.get(language_id)
    if not entry:
        return False
    path, _tokenize, _wf_code = entry
    return _get_trie(language_id, path) is not None


# ---------------------------------------------------------------------------
# Explanation templating (architecture doc §5.2: the trie walk already knows
# which unit changed and how, so this is deterministic, not a model's job).
# ---------------------------------------------------------------------------

# Voiced/semi-voiced (dakuten/handakuten) pairs — used to name the classic
# 清濁 contrast (か/が, は/ば/ぱ, ...) the way the live LLM-authored
# explanations already do (confirmed against real word_assets rows for
# 機械/昔). Hiragana only: every mora unit in the trie is hiragana-folded
# (ja_mora.iter_jmdict_entries), so comparisons never need katakana forms.
_DAKUTEN_PAIRS = {
    frozenset(pair) for pair in (
        'かが', 'きぎ', 'くぐ', 'けげ', 'こご',
        'さざ', 'しじ', 'すず', 'せぜ', 'そぞ',
        'ただ', 'ちぢ', 'つづ', 'てで', 'とど',
        'はば', 'はぱ', 'ばぱ', 'ひび', 'ひぴ', 'びぴ',
        'ふぶ', 'ふぷ', 'ぶぷ', 'へべ', 'へぺ', 'べぺ',
        'ほぼ', 'ほぽ', 'ぼぽ',
    )
}


def _is_dakuten_pair(a: str, b: str) -> bool:
    """Whether two mora units differ only by voicing on the same base kana.

    Handles fused yōon morae (きゃ/ぎゃ) by comparing the leading base kana
    and requiring any trailing small kana to match exactly.
    """
    if len(a) != len(b) or a[1:] != b[1:]:
        return False
    return frozenset({a[0], b[0]}) in _DAKUTEN_PAIRS


def _classify_contrast(original: str, substituted: str) -> str:
    """A short Japanese label for what kind of one-mora difference this is.

    Purely descriptive — the judge doesn't read this, so a classification
    that's slightly off costs nothing but a slightly duller sentence. Falls
    back to a generic label rather than guessing at a category that doesn't
    fit, per the closed-enumeration lesson in project memory
    (ja-l1-judge-and-generator-doctrine): this label is prose, not a rule
    the judge enforces, so there's no allow-list risk here, but the habit of
    not overclaiming a category is worth keeping anyway.
    """
    if 'ー' in (original, substituted):
        return '長音（のばす音）の有無'
    if 'っ' in (original, substituted):
        return '促音（つまる音）の有無'
    if 'ん' in (original, substituted):
        return '撥音「ん」の有無'
    if _is_dakuten_pair(original, substituted):
        return '清濁・半濁音の対立'
    return '一部の音の違い'


def _explanation_for(target_word: str, surface: str, position: int, original: str, substituted: str) -> str:
    contrast = _classify_contrast(original, substituted)
    return (
        f'「{surface}」は「{target_word}」と一モーラだけ異なる実在語です'
        f'（{position + 1}モーラ目: 「{original}」→「{substituted}」、{contrast}）。'
    )


def _explanation_for_target(target_word: str, definition: str | None) -> str:
    if definition:
        return f'正解です。「{target_word}」は「{definition}」という意味です。'
    return '正解です。'


# ---------------------------------------------------------------------------
# The public entry point
# ---------------------------------------------------------------------------

def build_candidates(
    target_word: str,
    reading: str,
    language_id: int,
    definition: str | None = None,
) -> dict | None:
    """Deterministic L1 candidate set for one target, or ``None`` if this
    target can't be served this way.

    On success, returns::

        {'correct_answer': target_word,
         'candidates': [surface_form, ...],   # up to _MAX_CANDIDATES, real,
                                               # tier-floored, self excluded
         'explanations': {target_word: '...', surface_form: '...', ...}}

    ``None`` covers every reason this target isn't servable from a trie —
    an unsupported language, a trie that failed to load, an empty reading,
    a target with zero one-mora neighbors, or fewer than 3 surviving the
    register floor — all deliberately collapsed to the same signal so the
    caller's fallback to the LLM-generated asset is a single ``is None``
    check, not a pile of special cases.
    """
    entry = _TRIE_REGISTRY.get(language_id)
    if not entry or not target_word or not reading:
        return None
    path, tokenize, wf_code = entry

    trie = _get_trie(language_id, path)
    if trie is None:
        return None

    units = tokenize(reading)
    if not units:
        return None

    neighbors = trie.one_substitution_neighbors(units)
    if not neighbors:
        return None

    tier = tier_for_lemma(target_word, language_id)
    floor = profile_for_tier(tier)['hard_floor']

    # First (position, original, substituted) seen per surface form wins —
    # a candidate can theoretically be reached at more than one position
    # (rare), and the first hit is as good an explanation as any other.
    by_surface: dict[str, tuple[int, str, str]] = {}
    for n in neighbors:
        if n.surface_form == target_word:
            # Self-collision via one of the target's OWN alternate readings
            # (2026-08-23 finding, e.g. 病気 びょうき vs colloquial びょーき) —
            # not a different word, so it's not a valid distractor no matter
            # how phonetically close it is.
            continue
        if n.surface_form in by_surface:
            continue
        score = zipf_frequency(n.surface_form, wf_code)
        # 0.0 means "wordfreq has no entry for this", not "vanishingly
        # rare" (tier_gate.py's own distinction) — a real word that's
        # merely uncovered by wordfreq's corpus must not be punished for
        # it, or this filter repeats the exact wrong-direction failure
        # (real word thrown out) the architecture doc flagged as B1's risk.
        if 0 < score < floor:
            continue
        by_surface[n.surface_form] = (n.position, n.original_unit, n.substituted_unit)

    if len(by_surface) < 3:
        return None

    surfaces = list(by_surface.keys())
    random.shuffle(surfaces)
    chosen = surfaces[:_MAX_CANDIDATES]

    explanations = {target_word: _explanation_for_target(target_word, definition)}
    for surface in chosen:
        position, original, substituted = by_surface[surface]
        explanations[surface] = _explanation_for(target_word, surface, position, original, substituted)

    return {
        'correct_answer': target_word,
        'candidates': chosen,
        'explanations': explanations,
    }
