"""TASK-749 — the metric maths behind scripts/measure_selection_quality.py.

Pure functions only; the script itself reads live history and is not a test.
The baseline numbers pinned here are the 2026-09-08 Japanese audit
(features/vocabulary-aware-test-selection.tech §0.3(b), §5.1).
"""

import math

import pytest

from scripts import measure_selection_quality as m


# --- implied ability ---------------------------------------------------------

def test_implied_ability_reproduces_the_dictation_baseline():
    # dictation, n=1: test ELO 1209 at 87% -> implied 1539 (§0.3(b)).
    assert round(m.implied_ability(1209, 87.0)) == 1539


def test_implied_ability_is_the_test_elo_at_fifty_percent():
    assert m.implied_ability(1300, 50.0) == pytest.approx(1300)


@pytest.mark.parametrize('pct,s', [(100.0, 0.95), (0.0, 0.05), (97.0, 0.95), (2.0, 0.05)])
def test_implied_ability_clamps_the_score(pct, s):
    expected = 1200 - 400 * math.log10(1 / s - 1)
    assert m.implied_ability(1200, pct) == pytest.approx(expected)
    assert math.isfinite(m.implied_ability(1200, pct))


def test_implied_ability_at_the_chance_floor_is_191_below():
    # §0.3(c): at a 25% floor the equilibrium gap is 400·log10(3) = 190.8.
    assert m.implied_ability(1200, 25.0) == pytest.approx(1200 - 190.85, abs=0.01)


# --- M1 / M2 -----------------------------------------------------------------

def test_on_target_band_is_half_open_like_the_baseline():
    # (60, 85]: exactly 60 is OFF target — that is what makes the recorded
    # 2026-09-08 ja reading baseline 3/8 (two first attempts sit at exactly 60).
    assert m.on_target([59.99, 60.0, 72.0, 85.0, 85.01]) == (2, 5)
    assert m.on_target([59.99, 60.0, 72.0, 85.0, 85.01], inclusive_low=True) == (3, 5)


def test_on_target_reproduces_the_ja_reading_baseline():
    ja_reading_first = [75, 100, 100, 50, 75, 75, 60, 60]
    assert m.on_target(ja_reading_first) == (3, 8)


def test_on_target_ignores_missing_scores():
    assert m.on_target([None, 70.0]) == (1, 1)


def test_below_floor_is_strict():
    assert m.below_floor([49.99, 50.0, 10.0]) == (2, 3)


def test_attempt_percentage_prefers_the_stored_column_then_score():
    assert m.attempt_percentage({'percentage': 42.5, 'score': 1, 'total_questions': 7}) == 42.5
    assert m.attempt_percentage({'percentage': None, 'score': 1, 'total_questions': 7}) == \
        pytest.approx(14.2857, abs=1e-4)
    assert m.attempt_percentage({'percentage': None, 'score': 0, 'total_questions': 0}) is None


# --- M3 ----------------------------------------------------------------------

def test_compression_reproduces_the_448_vs_88_baseline():
    implied = {'dictation': 1539, 'reading': 1498, 'listening': 1396, 'pitch_accent': 1091}
    live = {'dictation': 1209, 'reading': 1270, 'listening': 1248, 'pitch_accent': 1182}
    out = m.compression(implied, live)
    assert out['implied_spread'] == 448
    assert out['live_spread'] == 88
    assert out['ratio'] == pytest.approx(448 / 88)


def test_compression_uses_only_types_present_in_both():
    out = m.compression({'reading': 1500, 'pinyin': 900}, {'reading': 1200, 'listening': 1300})
    assert out['types'] == ['reading']
    assert out['implied_spread'] == 0


# --- distribution helpers ----------------------------------------------------

def test_quantiles_interpolate_and_skip_none():
    q = m.quantiles([0.1, None, 0.3, 0.2, 0.4])
    assert q['n'] == 4
    assert q['median'] == pytest.approx(0.25)
    assert q['p25'] == pytest.approx(0.175)
    assert q['p75'] == pytest.approx(0.325)


def test_quantiles_of_nothing():
    assert m.quantiles([None]) == {'n': 0, 'median': None, 'p25': None, 'p75': None}


def test_band_share_uses_u_star_plus_minus_tolerance():
    # [0.05, 0.25] inclusive.
    assert m.band_share([0.05, 0.15, 0.25, 0.26, 0.04]) == pytest.approx(3 / 5)
    assert m.band_share([None]) is None


def test_jaccard():
    assert m.jaccard([1, 2, 3], [2, 3, 4]) == pytest.approx(0.5)
    assert m.jaccard([], []) is None


def test_spearman_perfect_and_inverse():
    assert m.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert m.spearman([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)


def test_spearman_handles_ties_and_missing():
    rho = m.spearman([1, 1, 2, None, 3], [5, 6, 7, 100, 8])
    assert rho == pytest.approx(0.9486833, abs=1e-6)
    assert m.spearman([1, None], [2, 3]) is None
