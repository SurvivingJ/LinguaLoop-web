"""Unit tests for the LLM judge infrastructure.

Covers:
- base: classify() thresholds, safe_accept()
- answer_entailment: accept / flag / reject / safe-default-keep on error
- distractor_plausibility: per-distractor outcomes, length-mismatch fallback

All LLM transport is mocked via patch.object on the respective judge module's
``call_llm`` name.  Config loading is bypassed by pre-populating the per-module
``_cfg_cache`` dict directly.
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from services.exercise_generation.judges import answer_entailment as ae_mod
from services.exercise_generation.judges import distractor_plausibility as dp_mod
from services.exercise_generation.judges.base import (
    JudgeOutcome,
    JudgeUnavailable,
    batch_mode,
    classify,
    safe_accept,
    THRESHOLD_ACCEPT,
    THRESHOLD_REJECT,
)
from services.exercise_generation.judges.answer_entailment import judge_answer_entailment
from services.exercise_generation.judges.distractor_plausibility import judge_distractor_plausibility
from services.test_generation.schemas import (
    AnswerEntailmentVerdict,
    DistractorPlausibilityVerdict,
    likert_to_verdict,
)

# ---------------------------------------------------------------------------
# Shared fake config
# ---------------------------------------------------------------------------

_AE_CFG = {
    'template': 'passage:{0} question:{1} answer:{2}',
    'model': 'google/gemini-2.5-flash-lite',
    'provider': 'openrouter',
    # v3 is the first Likert row. answer_entailment refuses to judge on
    # anything older (see _is_pre_likert), so a v1 here would make every
    # entailment test below exercise the refusal path instead of the judge.
    'version': 3,
}
_DP_CFG = {
    'template': 'passage:{0} question:{1} answer:{2} distractors:{3}',
    'model': 'google/gemini-2.5-flash-lite',
    'provider': 'openrouter',
    'version': 1,
}


@pytest.fixture(autouse=True)
def _seed_caches():
    """Pre-populate per-module _cfg_cache to skip DB lookups.

    Copies, not the shared dicts: tests that vary one field (e.g. the template
    version) would otherwise mutate the module-level constant and leak into
    every test that ran after them.
    """
    ae_mod._cfg_cache[2] = dict(_AE_CFG)
    dp_mod._cfg_cache[2] = dict(_DP_CFG)
    yield
    ae_mod._cfg_cache.clear()
    dp_mod._cfg_cache.clear()


# ---------------------------------------------------------------------------
# base.py — classify() and safe_accept()
# ---------------------------------------------------------------------------

class TestClassify:
    def test_accept_at_threshold(self):
        assert classify(THRESHOLD_ACCEPT) == 'accept'

    def test_accept_above_threshold(self):
        assert classify(1.0) == 'accept'

    def test_flag_at_lower_bound(self):
        assert classify(THRESHOLD_REJECT) == 'flag'

    def test_flag_mid_range(self):
        assert classify(0.7) == 'flag'

    def test_reject_below_threshold(self):
        assert classify(THRESHOLD_REJECT - 0.01) == 'reject'

    def test_reject_zero(self):
        assert classify(0.0) == 'reject'


class TestSafeAccept:
    def test_returns_accept_verdict(self):
        outcome = safe_accept()
        assert outcome.verdict == 'accept'

    def test_confidence_equals_threshold(self):
        outcome = safe_accept()
        assert outcome.confidence == THRESHOLD_ACCEPT

    def test_custom_reason(self):
        outcome = safe_accept('test error')
        assert 'test error' in outcome.reason


# ---------------------------------------------------------------------------
# answer_entailment
# ---------------------------------------------------------------------------

class TestAnswerEntailment:
    """v2 (TASK-723): the judge reports a 1-5 Likert rating, not a 0-1 float.

    ``confidence`` now carries the rating itself, so these assertions double as
    the guarantee that ``llm_calls.judge_confidence`` holds one scale for this
    task_name — see migrations/null_legacy_judge_confidence.sql.
    """

    def _verdict(self, rating, reason: str = 'ok') -> AnswerEntailmentVerdict:
        return AnswerEntailmentVerdict(rating=rating, reason=reason)

    @pytest.mark.parametrize('rating', [5, 4])
    def test_accept(self, rating):
        db = MagicMock()
        with patch.object(ae_mod, 'call_llm', return_value=self._verdict(rating)):
            out = judge_answer_entailment(db, 'passage', 'question?', 'answer', 2)
        assert out.verdict == 'accept'
        assert out.confidence == float(rating)

    def test_flag(self):
        db = MagicMock()
        with patch.object(ae_mod, 'call_llm', return_value=self._verdict(3)):
            out = judge_answer_entailment(db, 'passage', 'question?', 'answer', 2)
        assert out.verdict == 'flag'
        assert out.confidence == 3.0

    @pytest.mark.parametrize('rating', [2, 1])
    def test_reject(self, rating):
        db = MagicMock()
        with patch.object(ae_mod, 'call_llm', return_value=self._verdict(rating)):
            out = judge_answer_entailment(db, 'passage', 'question?', 'answer', 2)
        assert out.verdict == 'reject'

    def test_numeric_key_shape_maps_to_rating(self):
        """ZH/JA prompts return {"1": rating, "2": reason} — no English keys."""
        obj = AnswerEntailmentVerdict.model_validate({'1': 4, '2': '第二段に明記'})
        assert obj.rating == 4
        assert obj.reason == '第二段に明記'

    def test_out_of_range_rating_rejected(self):
        with pytest.raises(ValidationError):
            AnswerEntailmentVerdict(rating=6, reason='ok')

    def test_legacy_float_scale_rejected_loudly(self):
        """A pre-v2 prompt row against v2 code must fail, never be rescaled.

        The scales overlap at 1 and mean opposite things there, so silently
        rounding 0.85 would invert the verdict on every call.
        """
        with pytest.raises(ValidationError, match='pre-v2'):
            AnswerEntailmentVerdict(rating=0.85, reason='ok')

    def test_legacy_max_confidence_is_invisible_to_the_schema(self):
        """Why the version gate exists, pinned as a fact rather than a comment.

        A legacy row's best-case answer is ``1.0`` — 77% of 391 historical
        responses. It is a structurally valid Likert ``1``, so the schema cannot
        reject it and the verdict *inverts*: maximum confidence becomes a hard
        reject. Nothing below the version gate can catch this.
        """
        obj = AnswerEntailmentVerdict.model_validate({'1': 1.0, '2': 'clearly stated'})
        assert obj.rating == 1
        assert likert_to_verdict(obj.rating) == 'reject'

    def test_pre_likert_row_refuses_before_spending_a_call(self):
        """v3 code against a v1/v2 row must not judge, and must not pay for it."""
        db = MagicMock()
        ae_mod._cfg_cache[2]['version'] = 2
        with patch.object(ae_mod, 'call_llm',
                          side_effect=AssertionError('LLM must not be called')) as spy:
            out = judge_answer_entailment(db, 'passage', 'question?', 'answer', 2)
        spy.assert_not_called()
        assert out.verdict == 'accept'
        assert 'entailment_likert_v2.sql' in out.reason

    @pytest.mark.parametrize('version', [1, 2])
    def test_pre_likert_row_aborts_a_batch(self, version):
        """A scale mismatch is a judge outage: fail closed inside a batch."""
        db = MagicMock()
        ae_mod._cfg_cache[2]['version'] = version
        with batch_mode():
            with patch.object(ae_mod, 'call_llm'):
                with pytest.raises(JudgeUnavailable):
                    judge_answer_entailment(db, 'passage', 'question?', 'answer', 2)

    def test_likert_row_is_judged_normally(self):
        """The gate must not fire on the version it was built for."""
        db = MagicMock()
        with patch.object(ae_mod, 'call_llm', return_value=self._verdict(5)) as spy:
            out = judge_answer_entailment(db, 'passage', 'question?', 'answer', 2)
        spy.assert_called_once()
        assert out.verdict == 'accept'

    def test_unusable_version_does_not_block_judging(self):
        """Only a *known* pre-v3 version blocks; a test double must not."""
        db = MagicMock()
        ae_mod._cfg_cache[2]['version'] = None
        with patch.object(ae_mod, 'call_llm', return_value=self._verdict(4)):
            out = judge_answer_entailment(db, 'passage', 'question?', 'answer', 2)
        assert out.verdict == 'accept'
        assert out.confidence == 4.0

    def test_missing_rating_accepts_without_fabricating_one(self):
        """No rating is not a weak rating — and must not become a number."""
        db = MagicMock()
        with patch.object(ae_mod, 'call_llm',
                          return_value=self._verdict(None, 'judge said nothing')):
            out = judge_answer_entailment(db, 'passage', 'question?', 'answer', 2)
        assert out.verdict == 'accept'
        assert out.confidence is None

    def test_missing_rating_does_not_abort_a_batch(self):
        """accept_item, not safe_accept: the judge answered, one field was empty."""
        db = MagicMock()
        with batch_mode():
            with patch.object(ae_mod, 'call_llm',
                              return_value=self._verdict(None, 'no rating')):
                out = judge_answer_entailment(db, 'passage', 'question?', 'answer', 2)
        assert out.verdict == 'accept'

    def test_llm_error_safe_accepts(self):
        db = MagicMock()
        with patch.object(ae_mod, 'call_llm', side_effect=RuntimeError('boom')):
            out = judge_answer_entailment(db, 'passage', 'question?', 'answer', 2)
        assert out.verdict == 'accept'

    def test_llm_error_aborts_a_batch(self):
        """Judge outage inside a batch must fail closed (TASK-510 contract)."""
        db = MagicMock()
        with batch_mode():
            with patch.object(ae_mod, 'call_llm', side_effect=RuntimeError('boom')):
                with pytest.raises(JudgeUnavailable):
                    judge_answer_entailment(db, 'passage', 'question?', 'answer', 2)

    def test_template_load_error_safe_accepts(self):
        ae_mod._cfg_cache.clear()
        db = MagicMock()
        with patch.object(ae_mod, 'get_template_config', side_effect=RuntimeError('missing')):
            out = judge_answer_entailment(db, 'passage', 'question?', 'answer', 2)
        assert out.verdict == 'accept'

    def test_reason_propagated(self):
        db = MagicMock()
        with patch.object(ae_mod, 'call_llm', return_value=self._verdict(5, 'clearly stated')):
            out = judge_answer_entailment(db, 'passage', 'question?', 'answer', 2)
        assert out.reason == 'clearly stated'


# ---------------------------------------------------------------------------
# distractor_plausibility
# ---------------------------------------------------------------------------

class TestDistractorPlausibility:

    def _verdict(self, ratings, reasons=None) -> DistractorPlausibilityVerdict:
        # v3: per_distractor carries 5-point Likert ratings (5/4=accept,
        # 3=flag, 2/1=reject), not raw 0.0-1.0 floats.
        return DistractorPlausibilityVerdict(
            per_distractor=ratings,
            reasons=reasons or ['ok'] * len(ratings),
        )

    def test_all_accept(self):
        db = MagicMock()
        with patch.object(dp_mod, 'call_llm',
                          return_value=self._verdict([5, 4, 5])):
            outcomes = judge_distractor_plausibility(
                db, 'p', 'q?', 'a', ['d1', 'd2', 'd3'], 2
            )
        assert all(o.verdict == 'accept' for o in outcomes)
        assert len(outcomes) == 3

    def test_one_flag(self):
        db = MagicMock()
        with patch.object(dp_mod, 'call_llm',
                          return_value=self._verdict([5, 3, 5])):
            outcomes = judge_distractor_plausibility(
                db, 'p', 'q?', 'a', ['d1', 'd2', 'd3'], 2
            )
        assert outcomes[1].verdict == 'flag'
        assert outcomes[0].verdict == 'accept'

    def test_one_reject(self):
        db = MagicMock()
        with patch.object(dp_mod, 'call_llm',
                          return_value=self._verdict([5, 2, 5])):
            outcomes = judge_distractor_plausibility(
                db, 'p', 'q?', 'a', ['d1', 'd2', 'd3'], 2
            )
        assert outcomes[1].verdict == 'reject'

    def test_empty_distractors_returns_empty(self):
        db = MagicMock()
        outcomes = judge_distractor_plausibility(db, 'p', 'q?', 'a', [], 2)
        assert outcomes == []

    def test_llm_error_safe_accepts_all(self):
        db = MagicMock()
        with patch.object(dp_mod, 'call_llm', side_effect=RuntimeError('boom')):
            outcomes = judge_distractor_plausibility(
                db, 'p', 'q?', 'a', ['d1', 'd2', 'd3'], 2
            )
        assert all(o.verdict == 'accept' for o in outcomes)
        assert len(outcomes) == 3

    def test_too_few_ratings_safe_accepts_all(self):
        db = MagicMock()
        # LLM returns 2 ratings for 3 distractors — cannot fabricate the third,
        # so safe-accept all.
        with patch.object(dp_mod, 'call_llm',
                          return_value=self._verdict([5, 2])):
            outcomes = judge_distractor_plausibility(
                db, 'p', 'q?', 'a', ['d1', 'd2', 'd3'], 2
            )
        assert all(o.verdict == 'accept' for o in outcomes)
        assert len(outcomes) == 3

    def test_too_many_ratings_truncates_to_n(self):
        db = MagicMock()
        # deepseek-v4-flash intermittently hallucinates extra distractors: it
        # returns 5 ratings for 3 distractors (rows 4-5 are padding/duplicates).
        # The real distractors are rated first and in order, so the judge must
        # TRUNCATE to the first 3 — NOT fall open to accept-all (which would let
        # the rejected distractor through). Captured shape 2026-06-06:
        # per_distractor=[2, 2, 5, 2, 2] for a 3-distractor question.
        ratings = [2, 2, 5, 2, 2]
        reasons = [f'r{i}' for i in range(5)]
        with patch.object(dp_mod, 'call_llm',
                          return_value=self._verdict(ratings, reasons)):
            outcomes = judge_distractor_plausibility(
                db, 'p', 'q?', 'a', ['d1', 'd2', 'd3'], 2
            )
        assert len(outcomes) == 3
        # First three real distractors keep their judgments, in order.
        assert [o.verdict for o in outcomes] == ['reject', 'reject', 'accept']
        assert [o.confidence for o in outcomes] == [2.0, 2.0, 5.0]
        assert [o.reason for o in outcomes] == ['r0', 'r1', 'r2']
        # Must NOT have fallen open (all-accept).
        assert not all(o.verdict == 'accept' for o in outcomes)

    def test_template_load_error_safe_accepts_all(self):
        dp_mod._cfg_cache.clear()
        db = MagicMock()
        with patch.object(dp_mod, 'get_template_config', side_effect=RuntimeError('missing')):
            outcomes = judge_distractor_plausibility(
                db, 'p', 'q?', 'a', ['d1', 'd2'], 2
            )
        assert all(o.verdict == 'accept' for o in outcomes)
        assert len(outcomes) == 2
