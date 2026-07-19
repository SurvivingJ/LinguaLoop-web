"""Unit tests for the dual-translation Tier 0 deterministic pre-pass (TASK-605).

Model-free and DB-free: Tier 0 never calls a model and never touches Supabase,
so these tests exercise services.dual_translation.tier0.grade_tier0 directly
against plain strings, mirroring the style of test_dual_translation_router.py
(focused functions, an autouse cache-clearing fixture, no fixtures heavier
than needed).
"""

import pytest

from services.dual_translation import tier0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_tier0_cache():
    """Tier 0 caches resolved results per (passage_id, normalized_reproduction);
    clear around every test so one test's resubmit never leaks into another."""
    tier0.clear_cache()
    yield
    tier0.clear_cache()


def _assert_full_marks(result: tier0.Tier0Result):
    assert result.resolved is True
    assert result.scores == {dim: 4 for dim in tier0.RUBRIC_DIMENSIONS}
    assert result.overall_band == 4
    assert result.errors == []
    # Tier 0 never calls a model: resolving must cost zero tokens.
    assert result.grader_trace["deterministic_prefilter"] is True
    assert result.grader_trace["tokens"] == {"in": 0, "out": 0}


def _assert_escalated(result: tier0.Tier0Result):
    """Tier 0 declined to resolve — the cascade must grade this one."""
    assert result.resolved is False
    assert result.scores is None
    assert result.overall_band is None
    assert result.grader_trace["deterministic_prefilter"] is False


# ---------------------------------------------------------------------------
# Exact match
# ---------------------------------------------------------------------------

def test_grade_tier0_exact_match_full_marks_no_model_call():
    gold = "The quick brown fox jumps over the lazy dog"

    result = tier0.grade_tier0(passage_id=1, gold_l2=gold, reproduction=gold, language_code="en")

    _assert_full_marks(result)
    assert result.grader_trace == {
        "tier": "tier0",
        "deterministic_prefilter": True,
        "cache_hit": False,
        "tokens": {"in": 0, "out": 0},
        "slugs": [],
    }
    assert isinstance(result.diff, list) and len(result.diff) > 0


# ---------------------------------------------------------------------------
# Single-token errors now escalate (TASK-623 — retired NEAR_EXACT_MISMATCH_RATIO)
# ---------------------------------------------------------------------------

def test_grade_tier0_ja_single_kana_swap_escalates():
    """The headline leniency hole the v1 baseline exposed: a 1-char は→が swap
    in a ~50-char JA passage. Its mismatch ratio (~3%) sat under the old
    NEAR_EXACT_MISMATCH_RATIO 0.05 gate, so Tier 0 awarded full marks before
    the grader ever saw it. Under the normalization-class gate the が→か-folded
    replace opcode is NOT normalization-class (は != か), so it must escalate."""
    gold = "彼女は昨日の午後に図書館へ行って新しい小説を借りてきたと友達に話していましたが、とても面白かったそうです"
    assert len(gold) >= 45  # ~50-char passage per the task
    reproduction = gold.replace("は", "が", 1)

    result = tier0.grade_tier0(passage_id=2, gold_l2=gold, reproduction=reproduction, language_code="ja")

    _assert_escalated(result)
    assert isinstance(result.diff, list) and len(result.diff) > 0


def test_grade_tier0_fuzzy_tolerant_edit_escalates_not_swallowed():
    """The fuzzy-collapse gotcha: 'lazy'->'lazyy' is a >=4-char, edit-distance-1
    replace, so grade_dictation's Levenshtein tolerance marks it correct and
    inflates accuracy to 1.0 — but it is still a 'replace' opcode and a real
    edit. The gate keys on opcode class, not accuracy, so it must escalate
    rather than resolve vacuously at full marks."""
    gold = "The quick brown fox jumps over the lazy dog"
    reproduction = "The quick brown fox jumps over the lazyy dog"

    result = tier0.grade_tier0(passage_id=3, gold_l2=gold, reproduction=reproduction, language_code="en")

    _assert_escalated(result)


def test_grade_tier0_single_wrong_token_in_long_passage_escalates():
    """One genuinely wrong token out of 21 (~4.8% mismatch) used to slip under
    the old ratio gate; now a non-normalization-class replace opcode escalates
    it to the cascade."""
    tokens = [f"word{i}" for i in range(21)]
    gold = " ".join(tokens)
    tokens[10] = "zzz"
    reproduction = " ".join(tokens)

    result = tier0.grade_tier0(passage_id=4, gold_l2=gold, reproduction=reproduction, language_code="en")

    _assert_escalated(result)


# ---------------------------------------------------------------------------
# Normalization-only diffs still resolve at Tier 0 with 0 tokens
# ---------------------------------------------------------------------------

def test_grade_tier0_punctuation_only_diff_resolves_zero_tokens():
    """Punctuation is stripped by tokenizer.normalize before the diff, so a
    punctuation-only difference produces no non-equal opcode and resolves at
    Tier 0 with zero model tokens."""
    gold = "Hello, world! A fine day, indeed."
    reproduction = "Hello world  A fine day indeed"

    result = tier0.grade_tier0(passage_id=11, gold_l2=gold, reproduction=reproduction, language_code="en")

    _assert_full_marks(result)


# ---------------------------------------------------------------------------
# Large diff -> escalate
# ---------------------------------------------------------------------------

def test_grade_tier0_large_diff_does_not_resolve():
    gold = "The quick brown fox jumps over the lazy dog"
    reproduction = "Yesterday I bought several apples at the market downtown"

    result = tier0.grade_tier0(passage_id=4, gold_l2=gold, reproduction=reproduction, language_code="en")

    assert result.resolved is False
    assert result.scores is None
    assert result.overall_band is None
    assert result.grader_trace["deterministic_prefilter"] is False
    assert result.grader_trace["cache_hit"] is False
    assert isinstance(result.diff, list) and len(result.diff) > 0


# ---------------------------------------------------------------------------
# Result cache
# ---------------------------------------------------------------------------

def test_grade_tier0_cache_hit_on_resubmit(monkeypatch):
    calls = {"n": 0}
    real_grade_dictation = tier0.grade_dictation

    def _counting_grade_dictation(*args, **kwargs):
        calls["n"] += 1
        return real_grade_dictation(*args, **kwargs)

    monkeypatch.setattr(tier0, "grade_dictation", _counting_grade_dictation)

    gold = "The quick brown fox jumps over the lazy dog"

    first = tier0.grade_tier0(passage_id=5, gold_l2=gold, reproduction=gold, language_code="en")
    second = tier0.grade_tier0(passage_id=5, gold_l2=gold, reproduction=gold, language_code="en")

    assert calls["n"] == 1  # second call served entirely from cache
    assert first.cache_hit is False
    assert second.cache_hit is True
    assert second.grader_trace["cache_hit"] is True
    assert second.scores == first.scores


def test_grade_tier0_different_passage_id_is_a_cache_miss(monkeypatch):
    """Same reproduction text, different passage -> the cache key includes
    passage_id, so this must not collide with another passage's entry."""
    calls = {"n": 0}
    real_grade_dictation = tier0.grade_dictation

    def _counting_grade_dictation(*args, **kwargs):
        calls["n"] += 1
        return real_grade_dictation(*args, **kwargs)

    monkeypatch.setattr(tier0, "grade_dictation", _counting_grade_dictation)

    gold = "The quick brown fox jumps over the lazy dog"

    tier0.grade_tier0(passage_id=6, gold_l2=gold, reproduction=gold, language_code="en")
    tier0.grade_tier0(passage_id=7, gold_l2=gold, reproduction=gold, language_code="en")

    assert calls["n"] == 2


# ---------------------------------------------------------------------------
# Width / kana normalization (JA)
# ---------------------------------------------------------------------------

def test_grade_tier0_ja_fullwidth_digit_normalization():
    """Full-width '１２' in the gold vs half-width '12' in the reproduction
    must normalize (NFKC) to the same text and match exactly."""
    gold = "今日は１２時に行きます"
    reproduction = "今日は12時に行きます"

    result = tier0.grade_tier0(passage_id=8, gold_l2=gold, reproduction=reproduction, language_code="ja")

    _assert_full_marks(result)


def test_grade_tier0_ja_kana_normalization():
    """Katakana rendering of a word in the reproduction vs hiragana in the
    gold must fold to the same kana (jaconv.kata2hira) and match exactly."""
    gold = "ありがとうございます"
    reproduction = "アリガトウございます"

    result = tier0.grade_tier0(passage_id=9, gold_l2=gold, reproduction=reproduction, language_code="ja")

    _assert_full_marks(result)
