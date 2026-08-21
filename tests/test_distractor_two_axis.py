"""The distractor judge's two axes (TASK-719) and its review band (TASK-720).

`tests/test_distractor_missing_rating.py` pins the *single*-axis contract and
must keep passing untouched — that is the point of the compatibility tests here:
a v4/v6 prompt row returns one rating per distractor and v7 code has to produce
byte-identical verdicts from it, because the code deploys before the prompt rows
are activated and would otherwise silently re-judge live content.

What is genuinely new and needs its own coverage:

* the three-element ``[fit, confusability, reason]`` response shape;
* the also-correct failure, which the single-axis scale put in band 1 and which
  fired 3 times in 1,800 ratings — it is detectable on the confusability axis
  independently of how well the distractor fits the subject;
* band 3 as *judge uncertainty* on either axis, with the axis recorded, which is
  the whole payload TASK-720 adds to `generation_review_queue`.
"""

from unittest.mock import MagicMock, patch

import services.exercise_generation.judges.distractor_plausibility as dp_mod
from services.exercise_generation.judges.distractor_plausibility import (
    judge_distractor_plausibility,
)
from services.test_generation.orchestrator import _flag_reasons
from services.test_generation.schemas import (
    AXIS_CONFUSABILITY,
    AXIS_FIT,
    DistractorPlausibilityVerdict,
    axes_to_verdict,
    confusability_to_verdict,
    fit_to_verdict,
    likert_to_verdict,
)


def _parse(payload):
    return DistractorPlausibilityVerdict.model_validate(payload)


def _outcomes(payload, n=3):
    db = MagicMock()
    verdict = _parse(payload)
    with patch.object(dp_mod, 'call_llm', return_value=verdict), \
         patch.object(dp_mod, 'log_judge_verdict', lambda **kw: None):
        return judge_distractor_plausibility(
            db, 'p', 'q?', 'a', [f'd{i}' for i in range(1, n + 1)], 2
        )


# ---------------------------------------------------------------------------
# The v7 response shape
# ---------------------------------------------------------------------------

def test_the_three_element_shape_fills_both_axes():
    """`{"1": [fit, confusability, reason]}` — what the v7 prompt asks for."""
    v = _parse({'1': [5, 4, 'ra'], '2': [4, 5, 'rb'], '3': [2, 1, 'rc']})
    assert v.fit == [5, 4, 2]
    assert v.confusability == [4, 5, 1]
    assert v.reasons == ['ra', 'rb', 'rc']


def test_the_axes_are_positional_not_sorted():
    """fit is the FIRST number and confusability the SECOND, always. Reading
    them by magnitude would silently swap the axes on every distractor whose
    confusability outranks its fit — which is most of the interesting ones."""
    v = _parse({'1': [2, 5, 'ra'], '2': [5, 2, 'rb']})
    assert v.fit == [2, 5]
    assert v.confusability == [5, 2]


def test_the_field_selector_shape_carries_three_arrays():
    """`{"1": [fits], "2": [confusabilities], "3": [reasons]}`. Ambiguous with
    three per-distractor triples until you notice a triple always carries its
    reason string inside its own array."""
    v = _parse({'1': [5, 3, 2], '2': [4, 4, 1], '3': ['ra', 'rb', 'rc']})
    assert v.fit == [5, 3, 2]
    assert v.confusability == [4, 4, 1]
    assert v.reasons == ['ra', 'rb', 'rc']


def test_three_triples_are_not_mistaken_for_field_selectors():
    """The collision case: 3 distractors, keys "1"/"2"/"3", both readings
    structurally plausible. The reason strings settle it."""
    v = _parse({'1': [5, 4, 'ra'], '2': [3, 2, 'rb'], '3': [2, 5, 'rc']})
    assert v.fit == [5, 3, 2]
    assert v.confusability == [4, 2, 5]


def test_named_axis_keys_are_honoured():
    """Models rename fields even when the prompt uses numeric keys."""
    v = _parse([
        {'fit': 5, 'confusability': 4, 'reason': 'ra'},
        {'topical_fit': 2, 'confusable': 5, 'reason': 'rb'},
    ])
    assert v.fit == [5, 2]
    assert v.confusability == [4, 5]


def test_an_index_key_is_never_read_as_an_axis():
    """`{"distractor": 1, ...}` — the position must not masquerade as a rating
    on either axis. Pre-existing guard, re-pinned because the second axis gives
    the stray integer somewhere new to land."""
    v = _parse([
        {'distractor': 1, 'fit': 5, 'confusability': 4, 'reason': 'ra'},
        {'index': 2, 'fit': 4, 'confusability': 2, 'reason': 'rb'},
    ])
    assert v.fit == [5, 4]
    assert v.confusability == [4, 2]


def test_a_short_confusability_axis_pads_with_none_not_a_number():
    v = DistractorPlausibilityVerdict(
        fit=[5, 4, 3], confusability=[4], reasons=['a', 'b', 'c'])
    assert v.confusability == [4, None, None]


# ---------------------------------------------------------------------------
# Backward compatibility with the live (v4 / v6) single-axis rows
# ---------------------------------------------------------------------------

def test_a_single_rating_row_lands_on_fit_with_no_confusability():
    v = _parse({'1': [4, 'ra'], '2': [5, 'rb'], '3': [2, 'rc']})
    assert v.fit == [4, 5, 2]
    assert v.confusability == [None, None, None]


def test_per_distractor_still_reads_as_the_fit_axis():
    """Several call sites and the measurement harness read `per_distractor`."""
    v = DistractorPlausibilityVerdict(
        per_distractor=[5, None, 2], reasons=['a', 'b', 'c'])
    assert v.per_distractor == v.fit == [5, None, 2]


def test_fit_reproduces_the_v4_scale_exactly():
    """The compatibility guarantee, stated as an assertion rather than a
    comment: with no confusability rating, every band maps exactly as
    `likert_to_verdict` mapped it. If this fails, activating v7 code against a
    live v4 row silently re-judges production content."""
    for band in (1, 2, 3, 4, 5, None):
        assert fit_to_verdict(band) == likert_to_verdict(band)
        assert axes_to_verdict(band, None).verdict == likert_to_verdict(band)


def test_a_single_rating_response_produces_v4_verdicts_end_to_end():
    outcomes = _outcomes(
        {'1': [5, 'ra'], '2': [3, 'rb'], '3': [2, 'rc']})
    assert [o.verdict for o in outcomes] == ['accept', 'flag', 'reject']
    assert all(o.axes[AXIS_CONFUSABILITY] is None for o in outcomes)


# ---------------------------------------------------------------------------
# The confusability axis carries the failure the single axis could not see
# ---------------------------------------------------------------------------

def test_also_correct_rejects_however_well_it_fits_the_subject():
    """TASK-719's acceptance criterion. A distractor that is itself arguably
    correct is a broken question no matter how on-subject it is — and on the
    single axis it had to compete with topical distance for the same integer,
    which is why band 1 fired 3 times in 1,800 ratings."""
    for fit in (5, 4, 3, 2, 1):
        av = axes_to_verdict(fit, 5)
        assert av.verdict == 'reject'
        assert AXIS_CONFUSABILITY in av.axes


def test_an_on_subject_but_inert_distractor_is_flagged_not_accepted():
    """The other direction, and the case the single axis scored 4 = accept: a
    real, on-subject option that no learner would ever pick. It is a weak
    question, not a broken one, so it flags rather than rejects."""
    av = axes_to_verdict(5, 1)
    assert av.verdict == 'flag'
    assert av.axes == (AXIS_CONFUSABILITY,)


def test_an_off_subject_but_tempting_distractor_still_rejects_on_fit():
    av = axes_to_verdict(2, 4)
    assert av.verdict == 'reject'
    assert av.axes == (AXIS_FIT,)


def test_the_target_distractor_accepts_and_names_no_axis():
    av = axes_to_verdict(5, 4)
    assert av.verdict == 'accept'
    assert av.axes == ()
    assert av.rating == 5


def test_confusability_is_not_monotone_in_quality():
    """Both ends of this axis are defects and the middle is fine. Stated as a
    test because it is the one property that makes a single ordinal impossible
    and therefore the reason this task exists."""
    assert confusability_to_verdict(5) == 'reject'
    assert confusability_to_verdict(4) == 'accept'
    assert confusability_to_verdict(2) == 'accept'
    assert confusability_to_verdict(1) == 'flag'


def test_the_worst_axis_wins():
    assert axes_to_verdict(2, 5).verdict == 'reject'
    assert axes_to_verdict(3, 5).verdict == 'reject'
    assert axes_to_verdict(3, 4).verdict == 'flag'
    assert axes_to_verdict(5, 3).verdict == 'flag'


def test_both_axes_are_named_when_both_bind():
    av = axes_to_verdict(3, 3)
    assert av.verdict == 'flag'
    assert av.axes == (AXIS_FIT, AXIS_CONFUSABILITY)
    assert av.rating == 3


# ---------------------------------------------------------------------------
# Missing ratings, per axis
# ---------------------------------------------------------------------------

def test_a_missing_axis_cannot_manufacture_a_verdict():
    """The v3 lesson, extended to two axes: None means "no rating", not a weak
    one, so it contributes 'accept' on whichever axis it appears."""
    assert axes_to_verdict(None, None).verdict == 'accept'
    assert axes_to_verdict(None, 4).verdict == 'accept'
    assert axes_to_verdict(5, None).verdict == 'accept'
    assert axes_to_verdict(None, 5).verdict == 'reject'   # a real rating binds
    assert axes_to_verdict(2, None).verdict == 'reject'


def test_no_rating_on_either_axis_accepts_unjudged():
    outcomes = _outcomes({'1': ['ra'], '2': ['rb'], '3': ['rc']})
    assert [o.verdict for o in outcomes] == ['accept'] * 3
    assert all('no rating' in o.reason for o in outcomes)
    # accept_item, so no fabricated score and no axis attribution at all.
    assert all(o.confidence is None and o.axes is None for o in outcomes)


def test_one_rated_axis_is_still_judged():
    """A distractor rated on confusability but not fit must not be waved
    through as "unjudged" — half a judgment is still a judgment."""
    v = DistractorPlausibilityVerdict(
        fit=[None], confusability=[5], reasons=['also correct'])
    with patch.object(dp_mod, 'call_llm', return_value=v), \
         patch.object(dp_mod, 'log_judge_verdict', lambda **kw: None):
        outcomes = judge_distractor_plausibility(
            MagicMock(), 'p', 'q?', 'a', ['d1'], 2)
    assert outcomes[0].verdict == 'reject'
    assert outcomes[0].flag_axes == (AXIS_CONFUSABILITY,)


def test_truncation_keeps_the_two_axes_aligned():
    """The hallucinated-extra-rows path (~14% of ja calls, 2026-06-06) now has
    two lists to truncate. Truncating one and not the other would pair each
    distractor's fit with its neighbour's confusability."""
    v = DistractorPlausibilityVerdict(
        fit=[5, 4, 2, 5, 5],
        confusability=[4, 5, 1, 4, 4],
        reasons=[f'r{i}' for i in range(5)],
    )
    with patch.object(dp_mod, 'call_llm', return_value=v), \
         patch.object(dp_mod, 'log_judge_verdict', lambda **kw: None):
        outcomes = judge_distractor_plausibility(
            MagicMock(), 'p', 'q?', 'a', ['d1', 'd2', 'd3'], 2)
    assert len(outcomes) == 3
    assert [o.axes for o in outcomes] == [
        {AXIS_FIT: 5, AXIS_CONFUSABILITY: 4},
        {AXIS_FIT: 4, AXIS_CONFUSABILITY: 5},
        {AXIS_FIT: 2, AXIS_CONFUSABILITY: 1},
    ]
    assert [o.verdict for o in outcomes] == ['accept', 'reject', 'reject']


# ---------------------------------------------------------------------------
# TASK-720: the review band, and what reaches the queue
# ---------------------------------------------------------------------------

def test_band_three_flags_on_either_axis_and_says_which():
    """The review band is now "the judge is not confident", and the queue has
    to record which of the two questions it was unsure about."""
    outcomes = _outcomes(
        {'1': [3, 4, 'unsure about the subject'],
         '2': [5, 3, 'unsure how tempting'],
         '3': [5, 4, 'fine']})
    assert [o.verdict for o in outcomes] == ['flag', 'flag', 'accept']
    assert outcomes[0].flag_axes == (AXIS_FIT,)
    assert outcomes[1].flag_axes == (AXIS_CONFUSABILITY,)
    assert outcomes[2].flag_axes == ()


def test_queue_flag_reasons_name_the_axis():
    flags = {
        'distractor_plausibility': [
            {'distractor': 'd2', 'confidence': 3.0,
             'axes': {AXIS_FIT: 5, AXIS_CONFUSABILITY: 3},
             'flag_axes': [AXIS_CONFUSABILITY], 'reason': 'unsure'},
        ],
    }
    assert _flag_reasons(flags) == ['distractor_plausibility:confusability']


def test_queue_flag_reasons_dedupe_and_stay_sorted():
    flags = {
        'distractor_plausibility': [
            {'flag_axes': [AXIS_CONFUSABILITY]},
            {'flag_axes': [AXIS_FIT, AXIS_CONFUSABILITY]},
        ],
    }
    assert _flag_reasons(flags) == [
        'distractor_plausibility:confusability',
        'distractor_plausibility:fit',
    ]


def test_queue_flag_reasons_are_unchanged_for_single_axis_judges():
    """answer_entailment has one axis and no attribution, and a distractor flag
    raised by a pre-v7 prompt row has none either. Both must read back exactly
    as they do today so existing queue rows stay comparable."""
    assert _flag_reasons({
        'answer_entailment': {'confidence': 3, 'reason': 'r'},
        'distractor_plausibility': [{'distractor': 'd', 'confidence': 3.0,
                                     'reason': 'r'}],
    }) == ['answer_entailment', 'distractor_plausibility']
