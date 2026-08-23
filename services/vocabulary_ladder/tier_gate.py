# services/vocabulary_ladder/tier_gate.py
"""
Sentence-tier hard gate (TASK-524).

A deterministic frequency-band screen over P1 and mined sentences. It answers
one question: *is this sentence's lexical profile within reach of a learner at
the sense's tier?* The eval's standing failure was that nothing asked —
"the barista's meticulous extraction protocol yielded an exceptionally nuanced
espresso" shipped as the example sentence for *coffee*.

Why deterministic, and why first:

  * The P1 sentence judge is an LLM call per sentence. Rejecting obvious tier
    misfits with a free local lookup keeps that spend for the judgements only
    a model can make (sense fit, register, whole-word use).
  * Frequency is not a matter of opinion. A screen that can be reasoned about
    from a table is easier to tune than a rubric.

Tokenisation uses ``wordfreq.tokenize`` rather than the project's
``LanguageProcessor``. The frequency tables were built with that tokeniser, so
lookups are apples-to-apples, and it covers zh/ja/en with no spaCy or fugashi
model to install — the gate has to run in CI and in the batch runner alike.

Thresholds live in ``config.TIER_GATE_PROFILES``; see the commentary there for
how they were calibrated.

Usage::

    verdicts = screen_sentences(core_asset['sentences'], language_id=2,
                                tier=tier_for_lemma('coffee', 2))
    bad = [i for i, v in enumerate(verdicts) if not v.passed]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable

from wordfreq import tokenize as wf_tokenize, zipf_frequency

from services.vocabulary_ladder.config import (
    LEMMA_ZIPF_TO_TIER,
    TIER_GATE_DEFAULT_TIER,
    TIER_GATE_LANG_CODES,
    TIER_GATE_PROFILES,
)

logger = logging.getLogger(__name__)

# wordfreq returns 0.0 for a token it has no entry for. Anything at or below
# this is "unknown", not "vanishingly rare" — the two need different handling.
_UNKNOWN_ZIPF_CEIL = 0.01


@dataclass(frozen=True)
class TierVerdict:
    """The outcome of screening one sentence.

    Attributes:
        passed: Whether the sentence is within the tier's band.
        tier: The tier it was screened against.
        reason: Empty when passed; otherwise a short human-readable cause,
            suitable for a repair prompt and for the batch report.
        out_of_band: ``(token, zipf)`` pairs below the tier's soft floor.
        too_rare: ``(token, zipf)`` pairs below the tier's hard floor. Always
            a subset of ``out_of_band``.
        unknown: Tokens wordfreq has no frequency for.
        scored: How many tokens carried a usable frequency.
    """

    passed: bool
    tier: str
    reason: str = ''
    out_of_band: list[tuple[str, float]] = field(default_factory=list)
    too_rare: list[tuple[str, float]] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)
    scored: int = 0


def language_code(language_id: int) -> str | None:
    """wordfreq language code for a language_id, or None if unsupported."""
    return TIER_GATE_LANG_CODES.get(language_id)


def tier_for_zipf(zipf: float | None) -> str:
    """Map a lemma's own Zipf score onto the tier its sentences are held to."""
    if zipf is None:
        return TIER_GATE_DEFAULT_TIER
    for threshold, tier in LEMMA_ZIPF_TO_TIER:
        if zipf >= threshold:
            return tier
    return 'T6'


def tier_for_lemma(lemma: str, language_id: int) -> str:
    """The tier a lemma's example sentences should be screened against.

    Falls back to the default tier for an unsupported language or a lemma
    wordfreq does not know — an unscreened sentence is better than one
    rejected on no evidence.
    """
    code = language_code(language_id)
    if not code or not lemma:
        return TIER_GATE_DEFAULT_TIER
    try:
        score = zipf_frequency(lemma, code)
    except Exception as exc:                      # pragma: no cover - defensive
        logger.warning("Zipf lookup failed for %r/%s: %s", lemma, code, exc)
        return TIER_GATE_DEFAULT_TIER
    if score < _UNKNOWN_ZIPF_CEIL:
        return TIER_GATE_DEFAULT_TIER
    return tier_for_zipf(score)


def _profile(tier: str) -> dict:
    return TIER_GATE_PROFILES.get(tier) or TIER_GATE_PROFILES[TIER_GATE_DEFAULT_TIER]


def profile_for_tier(tier: str) -> dict:
    """Public accessor for a tier's threshold dict.

    ``screen_sentence`` is the only consumer this module was written for, so
    the thresholds were kept behind ``_profile``. A caller that isn't
    screening a sentence — e.g. the ja mora-trie L1 lookup filtering
    single-word distractor candidates by register — needs the raw
    ``hard_floor``/``soft_floor`` values directly rather than a pass/fail
    verdict, hence this thin public wrapper instead of reaching into the
    private function.
    """
    return _profile(tier)


def tokenize(text: str, language_id: int) -> list[str]:
    """Frequency-table-aligned tokens for a sentence.

    Punctuation and whitespace are dropped by wordfreq's tokeniser; CJK is
    segmented (jieba for zh, MeCab-style for ja) rather than split on spaces,
    so there is no ``\\b`` dependency anywhere in this module.
    """
    code = language_code(language_id)
    if not code or not text:
        return []
    try:
        return wf_tokenize(text, code)
    except Exception as exc:                      # pragma: no cover - defensive
        logger.warning("Tokenisation failed for language %s: %s", language_id, exc)
        return []


def _exempt_matcher(
    target_word: str | None, extra_exempt: list[str] | None,
) -> Callable[[str], bool]:
    """Build a predicate for tokens that must not count against the sentence.

    The target word is the *point* of the sentence — a rare sense being taught
    cannot also be the reason its own example is rejected. Morphological forms
    and the lemma count the same way. CJK segmentation may split or merge the
    target, so containment matches in both directions.
    """
    terms = {(target_word or '').strip().lower()}
    for term in (extra_exempt or ()):
        if term:
            terms.add(str(term).strip().lower())
    terms.discard('')

    if not terms:
        return lambda token: False

    def is_exempt(token: str) -> bool:
        low = token.strip().lower()
        if not low:
            return True
        return any(low == t or low in t or t in low for t in terms)

    return is_exempt


def screen_sentence(
    text: str,
    language_id: int,
    tier: str,
    target_word: str | None = None,
    exempt: list[str] | None = None,
) -> TierVerdict:
    """Screen one sentence against a tier's frequency band.

    Fails open for anything it cannot judge: an unsupported language, an empty
    sentence, or a sentence with no scoreable tokens all pass. A gate that
    rejects on absence of evidence would silently starve the pipeline.
    """
    prof = _profile(tier)
    tokens = tokenize(text, language_id)
    if not tokens:
        return TierVerdict(passed=True, tier=tier)

    code = language_code(language_id)
    is_exempt = _exempt_matcher(target_word, exempt)

    out_of_band: list[tuple[str, float]] = []
    too_rare: list[tuple[str, float]] = []
    unknown: list[str] = []
    scored = 0

    for token in tokens:
        if is_exempt(token) or token.isdigit():
            continue
        try:
            score = zipf_frequency(token, code)
        except Exception:                          # pragma: no cover - defensive
            continue
        if score < _UNKNOWN_ZIPF_CEIL:
            unknown.append(token)
            continue
        scored += 1
        if score < prof['soft_floor']:
            out_of_band.append((token, round(score, 2)))
            if score < prof['hard_floor']:
                too_rare.append((token, round(score, 2)))

    if not scored and not unknown:
        return TierVerdict(passed=True, tier=tier)

    def _fail(reason: str) -> TierVerdict:
        return TierVerdict(
            passed=False, tier=tier, reason=reason,
            out_of_band=out_of_band, too_rare=too_rare,
            unknown=unknown, scored=scored,
        )

    if too_rare:
        words = ', '.join(f'{w} (Zipf {z})' for w, z in too_rare[:4])
        return _fail(f'contains vocabulary far above tier {tier}: {words}')

    if len(out_of_band) > prof['max_out_of_band']:
        words = ', '.join(f'{w} (Zipf {z})' for w, z in out_of_band[:6])
        return _fail(
            f'{len(out_of_band)} words above tier {tier} '
            f'(max {prof["max_out_of_band"]}): {words}'
        )

    if len(unknown) > prof['max_unknown']:
        return _fail(
            f'{len(unknown)} unrecognised tokens (max {prof["max_unknown"]}): '
            + ', '.join(unknown[:6])
        )

    return TierVerdict(
        passed=True, tier=tier, out_of_band=out_of_band,
        unknown=unknown, scored=scored,
    )


def screen_sentences(
    sentences: list[dict] | list[str],
    language_id: int,
    tier: str,
    target_word: str | None = None,
    exempt: list[str] | None = None,
) -> list[TierVerdict]:
    """Screen a P1 sentence list, preserving index alignment.

    Accepts either the P1 sentence dicts (``{'text': ..., 'target_word': ...}``)
    or bare strings. Each sentence's own ``target_word`` takes precedence over
    the ``target_word`` argument, which is the fallback for the whole set.
    Output is always the same length as the input — downstream levels address
    sentences positionally.
    """
    verdicts: list[TierVerdict] = []
    for sentence in sentences or []:
        if isinstance(sentence, dict):
            text = sentence.get('text', '')
            per_sentence_target = (
                sentence.get('target_word')
                or sentence.get('target_substring')
                or target_word
            )
        else:
            text = sentence or ''
            per_sentence_target = target_word
        verdicts.append(
            screen_sentence(text, language_id, tier, per_sentence_target, exempt)
        )
    return verdicts


def morph_form_texts(core_asset: dict) -> list[str]:
    """Pull the surface forms out of a P1 asset's ``morphological_forms``.

    Inflections of the target are exempt for the same reason the target is:
    "ran" must not make a sentence about *run* look off-tier.
    """
    forms = (core_asset or {}).get('morphological_forms') or []
    texts: list[str] = []
    for form in forms:
        if isinstance(form, dict):
            value = form.get('form') or form.get('text')
        else:
            value = form
        if value:
            texts.append(str(value))
    return texts
