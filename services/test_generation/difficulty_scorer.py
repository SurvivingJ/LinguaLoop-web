"""
Test Generation — Lexical Complexity → Seed ELO

Estimates a test's a-priori ELO from the prose's lexical properties, so the
new-test cold-start uses content-derived signal instead of relying on the
operator's tier guess alone.

Signal:
  * mean_zipf            — content-token mean Zipf frequency
  * p10_zipf             — 10th percentile (rarest 10% of tokens)
  * unknown_word_pct     — fraction with Zipf < 1.0 (effectively unknown to wordfreq)
  * mean_sentence_len    — tokens per sentence
  * type_token_ratio     — unique tokens / total tokens

Output: integer ELO in [400, 3000], anchored on the tier's midpoint and
adjusted by deviation from per-difficulty reference points.

Calibration status:
  Initial coefficients (W_ZIPF, W_LEN, W_TTR) are a-priori — no fit yet
  because test_attempts is empty in the live database. Once tests accumulate
  >= 20 attempts each, a follow-up step can regress
      target = test_skill_ratings.elo_rating
      features = TestDifficultySignal(prose, language)
      anchor = tier_initial_elo
  and refit the three weights. Until then, the scorer is an informed prior:
  better than a hardcoded tier-only map, but not yet validated against
  empirical learner performance.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, asdict
from typing import Optional

from wordfreq import tokenize as wf_tokenize, zipf_frequency

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# App language code → wordfreq language code (mirrors frequency_service).
# App codes are ISO 639-1; wordfreq uses the same codes here so the ISO
# entries are direct passthroughs. Full names kept for callers that pass
# language *names* (e.g. via Config.get_model_for_language).
_LANG_MAP: dict[str, str] = {
    'en': 'en',
    'zh': 'zh',
    'ja': 'ja',
    'english': 'en',
    'chinese': 'zh',
    'japanese': 'ja',
}

# Tokens with Zipf below this are treated as "unknown to wordfreq" in
# the unknown_word_pct signal. zipf_frequency returns 0.0 for OOV words.
_UNKNOWN_ZIPF_CEIL = 1.0

# Per-difficulty reference points for an "average" passage at that level.
# Derived from informal samples of training-set tests, not fitted.
# Lower Zipf = rarer vocabulary; longer sentence = harder; higher TTR =
# more lexical variety.
_REF_ZIPF: dict[int, float] = {
    1: 6.5, 2: 6.0, 3: 5.5, 4: 5.0, 5: 4.5, 6: 4.2, 7: 3.8, 8: 3.5, 9: 3.0,
}
_REF_SENT_LEN: dict[int, float] = {
    1: 7,   2: 9,   3: 11,  4: 13,  5: 15,  6: 18,  7: 22,  8: 26,  9: 30,
}
_REF_TTR: dict[int, float] = {
    1: 0.35, 2: 0.40, 3: 0.45, 4: 0.50, 5: 0.55,
    6: 0.60, 7: 0.62, 8: 0.65, 9: 0.70,
}

# Coefficients: how many ELO points per unit deviation from reference.
#   * 1 Zipf point rarer  -> +150 ELO  (negative weight: zipf low = hard)
#   * 5 tokens longer     -> +50 ELO   (10 per token)
#   * +0.1 TTR            -> +50 ELO   (500 per 1.0 TTR unit)
# Tunable here without redeploying.
_W_ZIPF: float = -150.0
_W_LEN:  float = 10.0
_W_TTR:  float = 500.0

# Sentence delimiters across English / Chinese / Japanese.
_SENT_SPLIT = re.compile(r'[.!?。！？]+\s*')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TestDifficultySignal:
    """Lexical-complexity readout for a passage."""
    mean_zipf: float
    p10_zipf: float
    unknown_word_pct: float
    mean_sentence_len: float
    type_token_ratio: float
    n_tokens: int
    n_sentences: int

    def as_dict(self) -> dict:
        return asdict(self)


def score_passage(prose: str, language_code: str) -> TestDifficultySignal:
    """Compute the lexical signal for a passage.

    Returns sensible zeros on empty / unparseable input rather than raising;
    callers should treat the zero signal as "use tier midpoint without
    adjustment".
    """
    wf_lang = _to_wf_lang(language_code)
    tokens = _tokenize(prose, wf_lang, language_code)
    sentences = [s for s in _SENT_SPLIT.split(prose or '') if s.strip()]

    if not tokens:
        return TestDifficultySignal(0.0, 0.0, 0.0, 0.0, 0.0, 0, len(sentences))

    zipfs = [_safe_zipf(t, wf_lang) for t in tokens]
    known = [z for z in zipfs if z >= _UNKNOWN_ZIPF_CEIL]
    n = len(zipfs)

    mean_z = sum(zipfs) / n
    sorted_z = sorted(zipfs)
    p10_idx = max(0, int(0.1 * n) - 1)
    p10_z = sorted_z[p10_idx]
    unknown_pct = 1.0 - (len(known) / n)

    n_sent = max(len(sentences), 1)
    mean_sent_len = n / n_sent
    ttr = len(set(tokens)) / n

    return TestDifficultySignal(
        mean_zipf=round(mean_z, 3),
        p10_zipf=round(p10_z, 3),
        unknown_word_pct=round(unknown_pct, 3),
        mean_sentence_len=round(mean_sent_len, 2),
        type_token_ratio=round(ttr, 3),
        n_tokens=n,
        n_sentences=n_sent,
    )


def seed_test_elo(
    prose: str,
    language_code: str,
    target_difficulty: int,
    tier_initial_elo: int,
) -> tuple[int, TestDifficultySignal]:
    """Compute seed ELO + the signal that produced it.

    Returns (elo, signal). ELO is clamped to [400, 3000].

    target_difficulty is the operator-chosen tier (1..9); tier_initial_elo
    is the midpoint ELO for that tier (from dim_complexity_tiers). The scorer
    nudges that midpoint up or down based on how the prose's lexical
    complexity compares to the reference points for the target difficulty.
    """
    sig = score_passage(prose, language_code)

    if sig.n_tokens == 0:
        # No content — no adjustment.
        logger.warning(
            "seed_test_elo: empty signal for language=%s difficulty=%d; "
            "falling back to tier midpoint %d",
            language_code, target_difficulty, tier_initial_elo,
        )
        return (max(400, min(3000, int(tier_initial_elo))), sig)

    d = _clamp_difficulty(target_difficulty)
    ref_zipf = _REF_ZIPF[d]
    ref_len = _REF_SENT_LEN[d]
    ref_ttr = _REF_TTR[d]

    # If >50% of tokens have no Zipf data (e.g. JP without MeCab installed),
    # the mean_zipf reading is unreliable — suppress the Zipf adjustment and
    # let sentence-length + TTR carry the signal instead.
    use_zipf = sig.unknown_word_pct <= 0.5
    delta_zipf = (sig.mean_zipf - ref_zipf) if use_zipf else 0.0
    delta_len = sig.mean_sentence_len - ref_len
    delta_ttr = sig.type_token_ratio - ref_ttr

    adjustment = _W_ZIPF * delta_zipf + _W_LEN * delta_len + _W_TTR * delta_ttr
    elo = int(round(tier_initial_elo + adjustment))
    elo = max(400, min(3000, elo))

    logger.debug(
        "seed_test_elo: base=%d adj=%+.0f -> %d "
        "(zipf %.2f vs ref %.2f, len %.1f vs ref %.0f, ttr %.2f vs ref %.2f)",
        tier_initial_elo, adjustment, elo,
        sig.mean_zipf, ref_zipf, sig.mean_sentence_len, ref_len,
        sig.type_token_ratio, ref_ttr,
    )
    return (elo, sig)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_zipf(token: str, wf_lang: str) -> float:
    """Look up zipf_frequency, returning 0.0 on any failure.

    wordfreq's `zipf_frequency` re-tokenises the input internally (to handle
    compound words), and the Japanese path requires the optional MeCab C
    extension. If MeCab is missing we transparently degrade to 0.0 (treated
    as "unknown") for that token; this keeps the Zipf signal silent for JP
    rather than crashing the whole scorer, while sentence-length and TTR
    continue to contribute.
    """
    try:
        return zipf_frequency(token, wf_lang)
    except Exception:
        return 0.0


def _to_wf_lang(language_code: str) -> str:
    code = (language_code or '').lower()
    if code not in _LANG_MAP:
        raise ValueError(
            f"difficulty_scorer: no language mapping for {language_code!r}. "
            f"Known: {sorted(set(_LANG_MAP))}"
        )
    return _LANG_MAP[code]


def _tokenize(text: str, wf_lang: str, app_lang: str) -> list[str]:
    """Tokenize text into content words.

    Uses wordfreq.tokenize for languages it supports natively (en, zh).
    Japanese falls back to fugashi because wordfreq's ja path requires the
    optional MeCab C extension, which is not installed in this environment.
    """
    if not text or not text.strip():
        return []

    if wf_lang == 'ja':
        return _tokenize_ja(text)

    try:
        return [t for t in wf_tokenize(text, wf_lang) if t.strip()]
    except Exception as exc:
        logger.warning(
            "wordfreq tokenize failed for lang=%s (%s); "
            "falling back to whitespace split",
            wf_lang, exc,
        )
        return [t.strip(',.;:!?"\'()[]{}—-') for t in text.split() if t.strip()]


def _tokenize_ja(text: str) -> list[str]:
    """Japanese tokenisation via fugashi (already used by furigana_service)."""
    try:
        from fugashi import Tagger
        tagger = Tagger()
        return [
            w.surface for w in tagger(text)
            if w.surface.strip() and not _SENT_SPLIT.fullmatch(w.surface)
        ]
    except Exception as exc:
        logger.warning(
            "fugashi tokenize failed (%s); falling back to character split",
            exc,
        )
        # Char-level fallback: strip whitespace, treat each char as a token.
        return [c for c in text if c.strip()]


def _clamp_difficulty(d: Optional[int]) -> int:
    if d is None:
        return 5
    return max(1, min(9, int(d)))
