"""GET /api/dual-translation/next serves windows of reviewed sentence
references (TASK-976, ADR-037).

Pure functions (``plan_sentence_windows``, ``pick_next_window``) are tested
directly; the route-side selector against a canned fake DB whose filters are
no-ops (the same convention as test_dual_translation_routes.py), with the two
embedded reads monkeypatched where the canned data would otherwise be
ambiguous.
"""

import routes.dual_translation as dt_routes
from services.dual_translation.passage_builder import pick_next_window, plan_sentence_windows


# ---------------------------------------------------------------------------
# plan_sentence_windows
# ---------------------------------------------------------------------------

class TestPlanSentenceWindows:

    def test_packs_a_covered_run_into_two_to_four_sentence_windows(self):
        idxs = list(range(7))
        assert plan_sentence_windows(idxs, set(idxs), {}, 0.0) == [(0, 3), (4, 6)]

    def test_short_tail_is_rebalanced_not_dropped(self):
        idxs = list(range(5))
        assert plan_sentence_windows(idxs, set(idxs), {}, 0.0) == [(0, 2), (3, 4)]

    def test_a_missing_reference_splits_the_run(self):
        idxs = list(range(6))
        refs_ok = {0, 1, 3, 4, 5}
        assert plan_sentence_windows(idxs, refs_ok, {}, 0.0) == [(0, 1), (3, 5)]

    def test_isolated_sentence_gets_no_window(self):
        assert plan_sentence_windows([0, 1, 2], {0, 2}, {}, 0.0) == []

    def test_window_below_floor_on_mean_tightness_is_dropped(self):
        idxs = [0, 1, 2, 3]
        tight = {0: 0.9, 1: 0.9, 2: 0.3, 3: 0.4}
        # one window (0-3): mean 0.625 < 0.7
        assert plan_sentence_windows(idxs, set(idxs), tight, 0.7) == []
        assert plan_sentence_windows(idxs, set(idxs), tight, 0.6) == [(0, 3)]

    def test_no_tightness_passes_only_a_zero_floor(self):
        idxs = [0, 1]
        assert plan_sentence_windows(idxs, set(idxs), {}, 0.0) == [(0, 1)]
        assert plan_sentence_windows(idxs, set(idxs), {}, 0.6) == []

    def test_unsorted_input(self):
        assert plan_sentence_windows([3, 1, 0, 2], {0, 1, 2, 3}, {}, 0.0) == [(0, 3)]


# ---------------------------------------------------------------------------
# pick_next_window
# ---------------------------------------------------------------------------

class TestPickNextWindow:

    def test_first_unpractised_window_in_candidate_order(self):
        cands = [
            {'test_id': 'a', 'windows': [(0, 3), (4, 6)]},
            {'test_id': 'b', 'windows': [(0, 1)]},
        ]
        practised = {'a': {0: '2026-11-01', 1: '2026-11-01'}}
        assert pick_next_window(cands, practised) == {'test_id': 'a', 'start': 4, 'end': 6, 'fresh': True}

    def test_overlapping_practice_from_another_range_counts(self):
        cands = [{'test_id': 'a', 'windows': [(0, 3)]}, {'test_id': 'b', 'windows': [(0, 1)]}]
        practised = {'a': {3: '2026-11-01'}}  # e.g. a Produce window 2-3 overlaps
        assert pick_next_window(cands, practised)['test_id'] == 'b'

    def test_all_practised_serves_the_least_recently_practised(self):
        cands = [
            {'test_id': 'a', 'windows': [(0, 1), (2, 3)]},
            {'test_id': 'b', 'windows': [(0, 1)]},
        ]
        practised = {
            'a': {0: '2026-11-10', 1: '2026-11-10', 2: '2026-11-12', 3: '2026-11-12'},
            'b': {0: '2026-11-11', 1: '2026-11-11'},
        }
        assert pick_next_window(cands, practised) == {'test_id': 'a', 'start': 0, 'end': 1, 'fresh': False}

    def test_none_without_windows(self):
        assert pick_next_window([], {}) is None
        assert pick_next_window([{'test_id': 'a', 'windows': []}], {}) is None


# ---------------------------------------------------------------------------
# Route-side selector
# ---------------------------------------------------------------------------

class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, name):
        self.db, self.name = db, name

    def __getattr__(self, attr):  # select/eq/in_/order/limit/... are no-ops
        return lambda *a, **k: self

    def insert(self, payload):
        self.db.calls.append((self.name, 'insert', payload))
        return self

    def execute(self):
        return _Result(self.db.tables.get(self.name, []))


class _DB:
    def __init__(self, tables):
        self.tables, self.calls = tables, []

    def table(self, name):
        return _Query(self, name)


def _rows(n, hash_='h1', tight=0.9):
    return [{'idx': i, 'l2_text': f'句{i}。', 'transcript_hash': hash_,
             'l1_text': f'Sentence {i}.', 'tightness': tight} for i in range(n)]


def _db(tests, passage=None):
    return _DB({
        'test_attempts': [{'test_id': 't-new', 'created_at': '2026-11-16'},
                          {'test_id': 't-old', 'created_at': '2026-11-01'},
                          {'test_id': 't-new', 'created_at': '2026-10-01'}],
        'tests': tests,
        'dt_passage': [passage or {'id': 77, 'age_tier': 3, 'l2_language_id': 1, 'status': 'active'}],
    })


ZH_NEW = {'id': 't-new', 'language_id': 1, 'difficulty': 4, 'transcript_hash': 'h1'}
ZH_OLD = {'id': 't-old', 'language_id': 1, 'difficulty': 4, 'transcript_hash': 'h1'}


class TestSelectNextSentenceWindow:

    def test_serves_first_window_of_most_recent_test(self, monkeypatch):
        monkeypatch.setattr(dt_routes, '_window_material', lambda db, ids, l1: {'t-new': _rows(5), 't-old': _rows(4)})
        monkeypatch.setattr(dt_routes, '_practised_sentences', lambda db, uid: {})
        got = dt_routes._select_next_passage(_db([ZH_NEW, ZH_OLD]), 'u1', 2)
        assert got == {'passage_id': 77, 'l1_text': 'Sentence 0. Sentence 1. Sentence 2.',
                       'age_tier': 3, 'l2_language_id': 1}

    def test_skips_practised_windows(self, monkeypatch):
        monkeypatch.setattr(dt_routes, '_window_material', lambda db, ids, l1: {'t-new': _rows(4), 't-old': _rows(2)})
        monkeypatch.setattr(dt_routes, '_practised_sentences',
                            lambda db, uid: {'t-new': {i: '2026-11-17' for i in range(4)}})
        db = _db([ZH_NEW, ZH_OLD])
        got = dt_routes._select_next_passage(db, 'u1', 2)
        assert got['l1_text'] == 'Sentence 0. Sentence 1.'

    def test_tests_in_the_learners_l1_are_not_candidates(self, monkeypatch):
        seen = {}

        def material(db, ids, l1):
            seen['ids'] = ids
            return {}
        monkeypatch.setattr(dt_routes, '_window_material', material)
        monkeypatch.setattr(dt_routes, '_practised_sentences', lambda db, uid: {})
        en = {'id': 't-new', 'language_id': 2, 'difficulty': 4, 'transcript_hash': 'h1'}
        assert dt_routes._select_next_sentence_window(_db([en, ZH_OLD]), 'u1', 2) is None
        assert seen['ids'] == ['t-old']

    def test_stale_sentence_rows_are_not_served(self, monkeypatch):
        monkeypatch.setattr(dt_routes, '_window_material',
                            lambda db, ids, l1: {'t-new': _rows(4, hash_='old'), 't-old': _rows(2)})
        monkeypatch.setattr(dt_routes, '_practised_sentences', lambda db, uid: {})
        db = _db([ZH_NEW, ZH_OLD])
        got = dt_routes._select_next_sentence_window(db, 'u1', 2)
        assert got['l1_text'] == 'Sentence 0. Sentence 1.'  # from t-old

    def test_below_floor_windows_are_not_served(self, monkeypatch):
        monkeypatch.setattr(dt_routes, '_window_material',
                            lambda db, ids, l1: {'t-new': _rows(4, tight=0.5)})
        monkeypatch.setattr(dt_routes, '_practised_sentences', lambda db, uid: {})
        assert dt_routes._select_next_sentence_window(_db([ZH_NEW]), 'u1', 2) is None

    def test_retired_range_passage_is_not_served(self, monkeypatch):
        monkeypatch.setattr(dt_routes, '_window_material', lambda db, ids, l1: {'t-new': _rows(2)})
        monkeypatch.setattr(dt_routes, '_practised_sentences', lambda db, uid: {})
        db = _db([ZH_NEW], passage={'id': 5, 'age_tier': 3, 'l2_language_id': 1, 'status': 'retired'})
        assert dt_routes._select_next_sentence_window(db, 'u1', 2) is None

    def test_no_attempts_means_no_window(self):
        assert dt_routes._select_next_sentence_window(_DB({'test_attempts': []}), 'u1', 2) is None

    def test_falls_back_to_legacy_passages(self, monkeypatch):
        monkeypatch.setattr(dt_routes, '_window_material', lambda db, ids, l1: {})
        db = _db([ZH_NEW])
        db.tables['dt_passage'] = [{'id': 7, 'l2_text': 'gold', 'age_tier': 3, 'l2_language_id': 1}]
        db.tables['dt_passage_reference'] = [{'l1_text': 'legacy'}]
        got = dt_routes._select_next_passage(db, 'u1', 2)
        assert got['passage_id'] == 7 and got['l1_text'] == 'legacy'


class TestEmbeddedReads:

    def test_window_material_groups_by_test(self):
        db = _DB({'test_sentence_references': [
            {'l1_text': 'A.', 'tightness': 0.8, 'review_verdict': 'pass',
             'test_sentences': {'test_id': 't1', 'idx': 1, 'l2_text': '甲。', 'transcript_hash': 'h'}},
            {'l1_text': 'B.', 'tightness': 0.9, 'review_verdict': 'rewritten',
             'test_sentences': {'test_id': 't1', 'idx': 0, 'l2_text': '乙。', 'transcript_hash': 'h'}},
            {'l1_text': 'C.', 'tightness': 0.9, 'review_verdict': 'fail',
             'test_sentences': {'test_id': 't1', 'idx': 2, 'l2_text': '丙。', 'transcript_hash': 'h'}},
        ]})
        got = dt_routes._window_material(db, ['t1'], 2)
        assert sorted(r['idx'] for r in got['t1']) == [0, 1]

    def test_practised_counts_submitted_and_skipped_only(self):
        db = _DB({'dt_submission': [
            {'created_at': '2026-11-17T10:00', 'reproduction': '答え', 'skipped_at': None,
             'dt_passage': {'source_ref_id': 't1', 'sentence_start': 0, 'sentence_end': 1}},
            {'created_at': '2026-11-16T10:00', 'reproduction': '', 'skipped_at': '2026-11-16T10:01',
             'dt_passage': {'source_ref_id': 't1', 'sentence_start': 1, 'sentence_end': 2}},
            {'created_at': '2026-11-15T10:00', 'reproduction': '', 'skipped_at': None,
             'dt_passage': {'source_ref_id': 't1', 'sentence_start': 3, 'sentence_end': 4}},
            {'created_at': '2026-11-14T10:00', 'reproduction': 'x', 'skipped_at': None,
             'dt_passage': {'source_ref_id': 't2', 'sentence_start': None, 'sentence_end': None}},
        ]})
        got = dt_routes._practised_sentences(db, 'u1')
        assert got == {'t1': {0: '2026-11-17T10:00', 1: '2026-11-17T10:00', 2: '2026-11-16T10:00'}}


# ---------------------------------------------------------------------------
# ADR-047: two independent reviews of the same text override the floor
# ---------------------------------------------------------------------------

from services.dual_translation import sentence_refs as sr  # noqa: E402
from services.dual_translation.passage_builder import (  # noqa: E402
    select_window_for_primed, window_meets_floor,
)


class TestFloorOverride:

    def test_agreed_sentences_leave_the_mean(self):
        tight = {0: 0.9, 1: 0.3}
        assert window_meets_floor([0, 1], tight, 0.7) is False
        assert window_meets_floor([0, 1], tight, 0.7, agreed=frozenset({1})) is True

    def test_an_all_agreed_window_passes_whatever_the_scores(self):
        tight = {0: 0.2, 1: 0.3}
        assert window_meets_floor([0, 1], tight, 0.7, agreed=frozenset({0, 1})) is True

    def test_unagreed_low_sentences_still_block(self):
        tight = {0: 0.3, 1: 0.3, 2: 0.9}
        assert window_meets_floor([0, 1, 2], tight, 0.7, agreed=frozenset({2})) is False

    def test_plan_sentence_windows_uses_agreement(self):
        idxs = [0, 1, 2, 3]
        tight = {0: 0.9, 1: 0.9, 2: 0.3, 3: 0.4}
        assert plan_sentence_windows(idxs, set(idxs), tight, 0.7) == []
        assert plan_sentence_windows(idxs, set(idxs), tight, 0.7, agreed=frozenset({2, 3})) == [(0, 3)]

    def test_primed_selector_uses_agreement(self):
        rows = [{'idx': i, 'l2_text': '句。', 'sense_ids': [1] if i == 1 else []} for i in range(2)]
        tight = {0: 0.3, 1: 0.3}
        assert select_window_for_primed(rows, [1], [], {0, 1}, tight, 0.7) is None
        assert select_window_for_primed(rows, [1], [], {0, 1}, tight, 0.7, agreed=frozenset({0, 1})) == (0, 1)

    def test_faithful_reviews_counts_distinct_runs_with_the_same_text(self):
        new = {'sentence_id': 1, 'l1_language_id': 2, 'l1_text': 'A.', 'review_verdict': 'pass'}
        existing = [
            {'sentence_id': 1, 'l1_language_id': 2, 'l1_text': 'A.', 'review_verdict': 'pass', 'run_id': 'r1'},
            {'sentence_id': 1, 'l1_language_id': 2, 'l1_text': 'A.', 'review_verdict': 'fail', 'run_id': 'r2'},
            {'sentence_id': 1, 'l1_language_id': 2, 'l1_text': 'A!', 'review_verdict': 'pass', 'run_id': 'r3'},
            {'sentence_id': 1, 'l1_language_id': 1, 'l1_text': 'A.', 'review_verdict': 'pass', 'run_id': 'r4'},
            {'sentence_id': 1, 'l1_language_id': 2, 'l1_text': 'A.', 'review_verdict': 'pass', 'run_id': 'new'},
        ]
        assert sr.faithful_reviews(new, 'new', existing) == 2
        assert sr.faithful_reviews(dict(new, review_verdict='fail'), 'new', existing) == 0
        assert sr.FLOOR_OVERRIDE_REVIEWS == 2

    def test_next_serves_a_below_floor_window_two_reviewers_agreed_on(self, monkeypatch):
        rows = [dict(r, agreed=True) for r in _rows(2, tight=0.3)]
        monkeypatch.setattr(dt_routes, '_window_material', lambda db, ids, l1: {'t-new': rows})
        monkeypatch.setattr(dt_routes, '_practised_sentences', lambda db, uid: {})
        assert dt_routes._select_next_sentence_window(_db([ZH_NEW]), 'u1', 2)['l1_text'] == 'Sentence 0. Sentence 1.'

    def test_window_material_flags_agreement(self):
        db = _DB({'test_sentence_references': [
            {'l1_text': 'A.', 'tightness': 0.3, 'review_verdict': 'pass', 'faithful_reviews': 2,
             'test_sentences': {'test_id': 't1', 'idx': 0, 'l2_text': '甲。', 'transcript_hash': 'h'}},
            {'l1_text': 'B.', 'tightness': 0.3, 'review_verdict': 'pass', 'faithful_reviews': 1,
             'test_sentences': {'test_id': 't1', 'idx': 1, 'l2_text': '乙。', 'transcript_hash': 'h'}},
        ]})
        got = {r['idx']: r['agreed'] for r in dt_routes._window_material(db, ['t1'], 2)['t1']}
        assert got == {0: True, 1: False}
