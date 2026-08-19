"""A missing rating must never masquerade as a rating of 3.

Why this file exists: the v3 judge prompt used numeric keys as FIELD SELECTORS
(`{"1": [ratings], "2": [reasons]}`) while the same prompt showed the model a
NUMBERED distractor list and told it to return "one entry per distractor". The
model resolved that ambiguity as key=distractor-index, which left no slot for
the number, so it returned reasons with no ratings at all. The schema then
fabricated a 3 for each missing rating, 3 mapped to 'flag', and 80% of live
verdicts became review-queue entries for judgments nobody had made.

`tests/test_generation/test_judges.py` could not catch this: it builds
`DistractorPlausibilityVerdict` from explicit rating lists and never routes a
raw model response through the normalizer, so all 23 of its tests pass either
way. These tests pin the raw shapes actually observed in `llm_calls`.
"""

from unittest.mock import MagicMock, patch

import services.exercise_generation.judges.distractor_plausibility as dp_mod
from services.exercise_generation.judges.distractor_plausibility import (
    judge_distractor_plausibility,
)
from services.test_generation.schemas import (
    DistractorPlausibilityVerdict,
    likert_to_verdict,
)


def _parse(payload):
    return DistractorPlausibilityVerdict.model_validate(payload)


# ---------------------------------------------------------------------------
# Shapes captured verbatim from llm_calls.raw_response
# ---------------------------------------------------------------------------

def test_reasons_only_as_lists_yields_no_ratings():
    """`{"1": ["reason"], "2": ["reason"], "3": ["reason"]}` — 1 of 4 sampled
    live responses. Not one integer anywhere."""
    v = _parse({'1': ['reason a'], '2': ['reason b'], '3': ['reason c']})
    assert v.per_distractor == [None, None, None]
    assert 3 not in v.per_distractor


def test_reasons_only_as_scalars_yields_no_ratings():
    """`{"1": "reason", "2": "reason", "3": "reason"}` — also observed live."""
    v = _parse({'1': 'reason a', '2': 'reason b', '3': 'reason c'})
    assert v.per_distractor == [None, None, None]


def test_the_well_formed_shape_still_parses():
    """`{"1": [4, "reason"], ...}` — the one sampled response that worked, and
    the shape v4 makes canonical. Must not regress."""
    v = _parse({'1': [4, 'reason a'], '2': [5, 'reason b'], '3': [4, 'reason c']})
    assert v.per_distractor == [4, 5, 4]


def test_field_selector_shape_still_parses():
    """The v3 canonical shape stays supported — rows mid-flight must not break."""
    v = _parse({'1': [5, 3, 2], '2': ['reason a', 'reason b', 'reason c']})
    assert v.per_distractor == [5, 3, 2]


def test_a_partial_gap_keeps_the_real_ratings():
    """One unparseable entry must not discard its neighbours' real judgments."""
    v = _parse({'1': [5, 'reason a'], '2': ['reason b'], '3': [2, 'reason c']})
    assert v.per_distractor == [5, None, 2]


def test_none_survives_validation():
    """`_validate` must treat None as legal, not as out-of-range."""
    v = DistractorPlausibilityVerdict(
        per_distractor=[None, 4], reasons=['a', 'b'])
    assert v.per_distractor == [None, 4]


def test_out_of_range_integers_are_clamped_not_dropped():
    """Pre-existing behaviour, pinned here because it is easy to mistake for a
    gap: `_as_likert` clamps to [1, 5] during normalization, so an out-of-range
    number never becomes None. Only a genuinely absent or non-numeric rating
    does — which is what keeps the None sentinel meaningful."""
    v = _parse({'1': [9, 'reason a'], '2': [-2, 'reason b'], '3': [4, 'reason c']})
    assert v.per_distractor == [5, 1, 4]


# ---------------------------------------------------------------------------
# likert_to_verdict — None is new; everything else must be untouched
# ---------------------------------------------------------------------------

def test_none_maps_to_accept_never_flag():
    assert likert_to_verdict(None) == 'accept'


def test_the_shared_mapping_is_unchanged_for_real_ratings():
    """Seven judges share this helper — only the None branch may differ."""
    assert likert_to_verdict(5) == 'accept'
    assert likert_to_verdict(4) == 'accept'
    assert likert_to_verdict(3) == 'flag'
    assert likert_to_verdict(2) == 'reject'
    assert likert_to_verdict(1) == 'reject'
    # Out-of-range keeps its historic 'flag' default for the other judges.
    assert likert_to_verdict(0) == 'flag'


# ---------------------------------------------------------------------------
# End to end through the judge
# ---------------------------------------------------------------------------

def _outcomes(payload, n=3):
    db = MagicMock()
    verdict = _parse(payload)
    with patch.object(dp_mod, 'call_llm', return_value=verdict), \
         patch.object(dp_mod, 'log_judge_verdict', lambda **kw: None):
        return judge_distractor_plausibility(
            db, 'p', 'q?', 'a', [f'd{i}' for i in range(1, n + 1)], 2
        )


def test_an_unrated_response_accepts_instead_of_queueing_fake_reviews():
    """The whole point: no ratings returned → no review-queue entries."""
    outcomes = _outcomes({'1': ['reason a'], '2': ['reason b'], '3': ['reason c']})
    assert [o.verdict for o in outcomes] == ['accept', 'accept', 'accept']
    assert not any(o.verdict == 'flag' for o in outcomes)


def test_the_unrated_reason_says_so_rather_than_inventing_one():
    outcomes = _outcomes({'1': ['reason a'], '2': ['reason b'], '3': ['reason c']})
    assert all('no rating' in o.reason for o in outcomes)


def test_a_partial_gap_preserves_the_real_verdicts():
    """[5, None, 2] → accept, accept(unjudged), reject. The genuine reject must
    survive; only the gap is waved through."""
    outcomes = _outcomes(
        {'1': [5, 'reason a'], '2': ['reason b'], '3': [2, 'reason c']})
    assert [o.verdict for o in outcomes] == ['accept', 'accept', 'reject']


def test_a_genuine_three_still_flags():
    """v4 must not silence real weak-distractor findings — that is the signal
    the review queue is supposed to carry."""
    outcomes = _outcomes(
        {'1': [5, 'reason a'], '2': [3, 'reason b'], '3': [5, 'reason c']})
    assert [o.verdict for o in outcomes] == ['accept', 'flag', 'accept']
