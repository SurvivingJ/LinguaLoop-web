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
# Near-exact (fuzzy-equal) match
# ---------------------------------------------------------------------------

def test_grade_tier0_fuzzy_typo_within_tolerance_full_marks():
    """'lazyy' is a single-character insertion on a >=4-char word — within
    services.dictation.grader's Levenshtein fuzzy tolerance, so the overall
    diff still reads as a perfect (accuracy == 1.0) match."""
    gold = "The quick brown fox jumps over the lazy dog"
    reproduction = "The quick brown fox jumps over the lazyy dog"

    result = tier0.grade_tier0(passage_id=2, gold_l2=gold, reproduction=reproduction, language_code="en")

    _assert_full_marks(result)
    assert result.grader_trace["deterministic_prefilter"] is True
    assert result.grader_trace["tokens"] == {"in": 0, "out": 0}


def test_grade_tier0_small_diff_embedding_gate_stub_full_marks():
    """One genuinely wrong token (fails fuzzy tolerance) out of 21 — under
    the stub's NEAR_EXACT_MISMATCH_RATIO threshold, so it still resolves at
    Tier 0 rather than escalating to the cascade."""
    tokens = [f"word{i}" for i in range(21)]
    gold = " ".join(tokens)
    tokens[10] = "zzz"
    reproduction = " ".join(tokens)

    result = tier0.grade_tier0(passage_id=3, gold_l2=gold, reproduction=reproduction, language_code="en")

    _assert_full_marks(result)
    assert result.grader_trace["deterministic_prefilter"] is True


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
