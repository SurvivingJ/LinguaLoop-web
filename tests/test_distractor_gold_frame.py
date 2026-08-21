"""TASK-726 — the distractor gold set's statistics, without a DB or an LLM.

These tests exist because every number this workstream publishes from now on
passes through `scripts/distractor_gold.py`, and the failure mode of a weighting
bug is not a crash — it is a plausible-looking rate that is quietly wrong. Each
test below pins one number that a reviewer could otherwise only take on trust.
"""

from __future__ import annotations

import os
import random
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'scripts'))

from distractor_gold import (  # noqa: E402
    CONFUSABLE,
    TOPICAL_DISTANCE,
    assign_frame_weights,
    band_metrics,
    cohens_kappa,
    confusion_by_axis,
    disagreement,
    explode_items,
    gold_reject,
    pick_overlap_slice,
    primary_label,
    select_for_adjudication,
    verdict_metrics,
    weighted_auc,
)


def _item(lang=1, type_code='literal_detail', **kw):
    it = {
        'item_id': kw.pop('item_id', f'q{random.random()}#0'),
        'qid': 'q', 'lang': lang, 'lang_code': 'zh', 'type_code': type_code,
        'distractor_index': 0, 'distractor': 'd', 'passage': 'p',
        'question': 'q?', 'answer': 'a',
    }
    it.update(kw)
    return it


# ------------------------------------------------------------------ frame build


def test_explode_items_one_row_per_distractor_with_stable_ids():
    rows = [{
        'qid': 'abc', 'lang': 1, 'passage': 'P', 'question': 'Q', 'answer': 'A',
        'distractors': ['d0', 'd1', 'd2'], 'type_code': 'inference',
        'difficulty': 6,
    }]
    items = explode_items(rows)
    assert [it['item_id'] for it in items] == ['abc#0', 'abc#1', 'abc#2']
    assert [it['distractor'] for it in items] == ['d0', 'd1', 'd2']
    assert all(it['lang_code'] == 'zh' for it in items)


@pytest.mark.parametrize('a,b,expected_kind', [
    (5, 5, None),          # identical
    (5, 4, None),          # same verdict, one band apart
    (4, 3, 'verdict'),     # accept vs flag — production acts differently
    (2, 1, None),          # both reject, adjacent
    (5, 3, 'verdict'),     # accept vs flag AND two bands
    (5, 2, 'verdict'),
    (None, 5, 'unrated'),  # a refusal is a disagreement, never agreement
    (3, None, 'unrated'),
])
def test_disagreement_kinds(a, b, expected_kind):
    flag, kind = disagreement(a, b)
    assert kind == expected_kind
    assert flag == (kind is not None)


def test_rating_gap_within_one_verdict_band_is_a_rating_disagreement():
    # 5 and 4 are both 'accept' and adjacent -> agreement. There is no pair
    # inside one verdict band that is >=2 apart except via the accept band,
    # which 5 vs 3 covers as a verdict disagreement. This pins that the
    # 'rating' branch is reachable only through the reject band's 1 vs 2...
    # which is adjacent. So 'rating' is defensive: assert it stays unreachable
    # for the current band map rather than pretending it fires.
    kinds = {disagreement(a, b)[1] for a in (1, 2, 3, 4, 5) for b in (1, 2, 3, 4, 5)}
    assert 'rating' not in kinds
    assert kinds == {None, 'verdict'}


def test_select_all_when_no_budget_is_given():
    items = [_item() for _ in range(10)]
    for it in items[:3]:
        it['disagreement'] = True
    select_for_adjudication(items, None, random.Random(1))
    assert all(it['selected'] for it in items)
    assert all(it['selection_prob'] == 1.0 for it in items)
    # The flag still records what the pre-rating found, even though nothing
    # was enriched — the file must be able to say "enrichment did nothing".
    assert sum(1 for it in items if it['disagreement_selected']) == 3


def test_enrichment_forces_every_disagreement_and_records_fill_probability():
    items = [_item(item_id=f'i{i}') for i in range(100)]
    for it in items[:10]:
        it['disagreement'] = True
    select_for_adjudication(items, 30, random.Random(7))
    chosen = [it for it in items if it['selected']]
    assert len(chosen) == 30
    assert all(it['selected'] for it in items[:10])          # forced
    assert all(it['selection_prob'] == 1.0 for it in items[:10])
    fill = [it for it in items[10:]]
    assert all(it['selection_prob'] == pytest.approx(20 / 90) for it in fill)


def test_weights_undo_disagreement_enrichment():
    """A 50/50 enriched set must reproduce the frame's true reject rate.

    The bias TASK-726 step 2 warns about, in miniature: 10 of 100 items are
    disagreements and all 10 are force-included, so an unweighted rate off the
    selection over-counts them 3x.
    """
    items = [_item(item_id=f'i{i}') for i in range(100)]
    for i, it in enumerate(items):
        it['disagreement'] = i < 10
        it['truth'] = 1.0 if i < 10 else 0.0   # every disagreement is a reject
    select_for_adjudication(items, 30, random.Random(3))
    assign_frame_weights(items, {(1, 'literal_detail'): 1.0})
    sel = [it for it in items if it['selected']]

    raw = sum(it['truth'] for it in sel) / len(sel)
    weighted = (sum(it['truth'] * it['frame_weight'] for it in sel)
                / sum(it['frame_weight'] for it in sel))
    assert raw == pytest.approx(10 / 30)        # biased high, as warned
    assert weighted == pytest.approx(0.10, abs=0.01)   # the frame's real rate


def test_weights_post_stratify_a_uniform_frame_to_the_production_mix():
    # 10 items in each of two types; production is 90/10.
    items = ([_item(type_code='vocabulary_context', item_id=f'v{i}') for i in range(10)]
             + [_item(type_code='supporting_detail', item_id=f's{i}') for i in range(10)])
    select_for_adjudication(items, None, random.Random(1))
    assign_frame_weights(items, {
        (1, 'vocabulary_context'): 0.9, (1, 'supporting_detail'): 0.1,
    })
    voc = [it['frame_weight'] for it in items if it['type_code'] == 'vocabulary_context']
    sup = [it['frame_weight'] for it in items if it['type_code'] == 'supporting_detail']
    assert voc[0] == pytest.approx(1.8)     # 0.9 / 0.5, mean-normalised to 1
    assert sup[0] == pytest.approx(0.2)
    assert sum(voc + sup) == pytest.approx(len(items))


def test_a_type_production_never_generates_gets_zero_weight():
    items = [_item(type_code='inference', item_id=f'i{i}') for i in range(4)]
    items += [_item(type_code='ghost_type', item_id=f'g{i}') for i in range(4)]
    select_for_adjudication(items, None, random.Random(1))
    assign_frame_weights(items, {(1, 'inference'): 1.0})
    assert all(it['frame_weight'] == 0.0
               for it in items if it['type_code'] == 'ghost_type')


def test_unselected_items_carry_zero_weight():
    items = [_item(item_id=f'i{i}') for i in range(20)]
    select_for_adjudication(items, 5, random.Random(2))
    assign_frame_weights(items, {(1, 'literal_detail'): 1.0})
    assert all(it['frame_weight'] == 0.0 for it in items if not it['selected'])


def test_overlap_slice_is_capped_and_spread_over_the_disagreement_flag():
    items = []
    for i in range(60):
        it = _item(type_code=('inference' if i % 2 else 'main_idea'),
                   item_id=f'i{i}')
        it['disagreement'] = i < 12
        items.append(it)
    select_for_adjudication(items, None, random.Random(5))
    pick_overlap_slice(items, 20, random.Random(5))
    slice_ = [it for it in items if it['overlap_slice']]
    assert len(slice_) == 20
    assert any(it['disagreement'] for it in slice_)
    assert any(not it['disagreement'] for it in slice_)
    assert len({it['type_code'] for it in slice_}) == 2


def test_overlap_slice_never_exceeds_the_pool():
    items = [_item(item_id=f'i{i}') for i in range(5)]
    select_for_adjudication(items, None, random.Random(1))
    pick_overlap_slice(items, 60, random.Random(1))
    assert sum(1 for it in items if it['overlap_slice']) == 5


# ------------------------------------------------------------------ gold labels


@pytest.mark.parametrize('label,expected', [
    ({'confusable': 'no', 'also_correct': False}, True),
    ({'confusable': 'yes', 'also_correct': False}, False),
    ({'confusable': 'yes', 'also_correct': True}, True),   # a second right answer
    ({'confusable': 'borderline', 'also_correct': False}, None),
    (None, None),
])
def test_gold_reject_combines_the_axes_only_at_verdict_time(label, expected):
    assert gold_reject(label) is expected


def test_borderline_is_excluded_not_coerced():
    """The review band's population must not be silently pushed to a side."""
    rated = [
        {'band': 3, 'gold': None, 'weight': 1.0},
        {'band': 2, 'gold': True, 'weight': 1.0},
        {'band': 5, 'gold': False, 'weight': 1.0},
    ]
    vm = verdict_metrics(rated)
    assert vm['n_scored'] == 2 and vm['n_borderline'] == 1
    assert vm['precision'] == pytest.approx(1.0)
    assert vm['recall'] == pytest.approx(1.0)


def test_primary_label_is_the_first_labeller_not_an_average():
    it = {'labels': [
        {'labeller_id': 'A', 'confusable': 'yes'},
        {'labeller_id': 'B', 'confusable': 'no'},
    ]}
    assert primary_label(it)['labeller_id'] == 'A'


# ---------------------------------------------------------------------- metrics


def test_cohens_kappa_matches_a_hand_computed_value():
    # 2x2: both labellers say 'yes' 8/10; they agree on 8, disagree on 2.
    pairs = [('yes', 'yes')] * 7 + [('no', 'no')] + [('yes', 'no'), ('no', 'yes')]
    # observed = 0.8; A: yes 8, no 2; B: yes 8, no 2 -> expected = .64+.04 = .68
    assert cohens_kappa(pairs, CONFUSABLE) == pytest.approx((0.8 - 0.68) / 0.32)


def test_cohens_kappa_is_zero_for_chance_agreement():
    pairs = [('yes', 'yes')] * 25 + [('yes', 'no')] * 25 \
        + [('no', 'yes')] * 25 + [('no', 'no')] * 25
    assert cohens_kappa(pairs, CONFUSABLE) == pytest.approx(0.0, abs=1e-9)


def test_cohens_kappa_degenerate_single_category_reports_one_not_nan():
    assert cohens_kappa([('yes', 'yes')] * 10, CONFUSABLE) == 1.0


def test_cohens_kappa_needs_two_pairs():
    assert cohens_kappa([('yes', 'yes')], CONFUSABLE) is None
    assert cohens_kappa([], CONFUSABLE) is None


def test_weighted_auc_perfect_and_inverted_separation():
    scores = [5, 4, 2, 1]
    labels = [True, True, False, False]
    assert weighted_auc(scores, labels) == pytest.approx(1.0)
    assert weighted_auc(scores, [not x for x in labels]) == pytest.approx(0.0)


def test_weighted_auc_counts_ties_as_half():
    assert weighted_auc([3, 3], [True, False]) == pytest.approx(0.5)


def test_weighted_auc_respects_weights():
    # Two positives, one ranked above the negative and one below; the correctly
    # ranked one carries 3x the weight, so AUC must exceed 0.5.
    auc = weighted_auc([5, 1, 3], [True, True, False], [3.0, 1.0, 1.0])
    assert auc == pytest.approx(0.75)


def test_weighted_auc_needs_both_classes():
    assert weighted_auc([1, 2], [True, True]) is None


def test_band_metrics_precision_and_recall_are_weighted():
    rated = [
        {'band': 2, 'gold': True, 'weight': 3.0},    # band 2 catches a real one
        {'band': 2, 'gold': False, 'weight': 1.0},   # and a false one
        {'band': 5, 'gold': True, 'weight': 1.0},    # a miss
        {'band': 5, 'gold': False, 'weight': 1.0},
    ]
    bm = band_metrics(rated)
    assert bm[2]['precision'] == pytest.approx(3.0 / 4.0)
    assert bm[2]['recall'] == pytest.approx(3.0 / 4.0)
    assert bm[5]['precision'] == pytest.approx(0.5)
    assert bm[1]['n'] == 0 and bm[1]['precision'] is None


def test_band_metrics_carries_borderline_counts_per_band():
    rated = [
        {'band': 3, 'gold': None, 'weight': 1.0},
        {'band': 3, 'gold': True, 'weight': 1.0},
    ]
    bm = band_metrics(rated)
    assert bm[3]['n'] == 2 and bm[3]['n_borderline'] == 1
    assert bm[3]['precision'] == pytest.approx(1.0)   # scored on the one it can


def test_confusion_by_axis_exposes_off_diagonal_cells():
    """If the two axes were redundant this table would be diagonal.

    The off-diagonal cell here — an `unrelated` distractor a learner still
    confuses — is the case a single 1-5 scale cannot express, which is the
    whole premise of TASK-719.
    """
    items = [
        {'labels': [{'topical_distance': 'on-topic', 'confusable': 'yes'}]},
        {'labels': [{'topical_distance': 'unrelated', 'confusable': 'yes'}]},
        {'labels': [{'topical_distance': 'unrelated', 'confusable': 'no'}]},
        {'labels': []},
    ]
    tab = confusion_by_axis(items)
    assert tab[('unrelated', 'yes')] == 1
    assert tab[('on-topic', 'yes')] == 1
    assert sum(tab.values()) == 3          # the unlabelled item is not counted


def test_label_vocabularies_are_the_ones_the_task_specifies():
    assert TOPICAL_DISTANCE == ('on-topic', 'related', 'unrelated')
    assert CONFUSABLE == ('yes', 'borderline', 'no')
