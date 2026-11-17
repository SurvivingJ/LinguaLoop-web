"""Two agreeing reviews override the tightness floor (ADR-050, TASK-1033).

Pure functions: the shared window gate, the primed-window selector with
``agreed``, and the faithful-review count the upload script stores. The
GET /next side is in tests/test_dual_translation_next_selection.py.
"""

from services.dual_translation import sentence_refs as sr
from services.dual_translation.passage_builder import select_window_for_primed, window_meets_floor


class TestWindowMeetsFloor:

    def test_agreed_sentences_leave_the_mean(self):
        tight = {0: 0.9, 1: 0.3}
        assert window_meets_floor([0, 1], tight, 0.7) is False
        assert window_meets_floor([0, 1], tight, 0.7, agreed=frozenset({1})) is True

    def test_an_all_agreed_window_passes_whatever_the_scores(self):
        assert window_meets_floor([0, 1], {0: 0.2, 1: 0.3}, 0.7, agreed=frozenset({0, 1})) is True

    def test_unagreed_low_sentences_still_block(self):
        tight = {0: 0.3, 1: 0.3, 2: 0.9}
        assert window_meets_floor([0, 1, 2], tight, 0.7, agreed=frozenset({2})) is False

    def test_unscored_sentences_keep_the_old_rule(self):
        assert window_meets_floor([0, 1], {}, 0.0) is True
        assert window_meets_floor([0, 1], {}, 0.6) is False


class TestPrimedSelector:

    def test_uses_agreement(self):
        rows = [{'idx': i, 'l2_text': '句。', 'sense_ids': [1] if i == 1 else []} for i in range(2)]
        tight = {0: 0.3, 1: 0.3}
        assert select_window_for_primed(rows, [1], [], {0, 1}, tight, 0.7) is None
        assert select_window_for_primed(rows, [1], [], {0, 1}, tight, 0.7, agreed=frozenset({0, 1})) == (0, 1)


class TestFaithfulReviews:

    def test_counts_distinct_runs_with_the_same_text(self):
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
