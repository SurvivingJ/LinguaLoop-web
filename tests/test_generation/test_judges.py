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

from services.exercise_generation.judges import answer_entailment as ae_mod
from services.exercise_generation.judges import distractor_plausibility as dp_mod
from services.exercise_generation.judges.base import (
    JudgeOutcome,
    classify,
    safe_accept,
    THRESHOLD_ACCEPT,
    THRESHOLD_REJECT,
)
from services.exercise_generation.judges.answer_entailment import judge_answer_entailment
from services.exercise_generation.judges.distractor_plausibility import judge_distractor_plausibility
from services.test_generation.schemas import AnswerEntailmentVerdict, DistractorPlausibilityVerdict

# ---------------------------------------------------------------------------
# Shared fake config
# ---------------------------------------------------------------------------

_AE_CFG = {
    'template': 'passage:{0} question:{1} answer:{2}',
    'model': 'google/gemini-2.5-flash-lite',
    'provider': 'openrouter',
    'version': 1,
}
_DP_CFG = {
    'template': 'passage:{0} question:{1} answer:{2} distractors:{3}',
    'model': 'google/gemini-2.5-flash-lite',
    'provider': 'openrouter',
    'version': 1,
}


@pytest.fixture(autouse=True)
def _seed_caches():
    """Pre-populate per-module _cfg_cache to skip DB lookups."""
    ae_mod._cfg_cache[2] = _AE_CFG
    dp_mod._cfg_cache[2] = _DP_CFG
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

    def _verdict(self, confidence: float, reason: str = 'ok') -> AnswerEntailmentVerdict:
        return AnswerEntailmentVerdict(confidence=confidence, reason=reason)

    def test_accept(self):
        db = MagicMock()
        with patch.object(ae_mod, 'call_llm', return_value=self._verdict(0.9)):
            out = judge_answer_entailment(db, 'passage', 'question?', 'answer', 2)
        assert out.verdict == 'accept'
        assert out.confidence == 0.9

    def test_flag(self):
        db = MagicMock()
        with patch.object(ae_mod, 'call_llm', return_value=self._verdict(0.7)):
            out = judge_answer_entailment(db, 'passage', 'question?', 'answer', 2)
        assert out.verdict == 'flag'

    def test_reject(self):
        db = MagicMock()
        with patch.object(ae_mod, 'call_llm', return_value=self._verdict(0.4)):
            out = judge_answer_entailment(db, 'passage', 'question?', 'answer', 2)
        assert out.verdict == 'reject'

    def test_llm_error_safe_accepts(self):
        db = MagicMock()
        with patch.object(ae_mod, 'call_llm', side_effect=RuntimeError('boom')):
            out = judge_answer_entailment(db, 'passage', 'question?', 'answer', 2)
        assert out.verdict == 'accept'

    def test_template_load_error_safe_accepts(self):
        ae_mod._cfg_cache.clear()
        db = MagicMock()
        with patch.object(ae_mod, 'get_template_config', side_effect=RuntimeError('missing')):
            out = judge_answer_entailment(db, 'passage', 'question?', 'answer', 2)
        assert out.verdict == 'accept'

    def test_reason_propagated(self):
        db = MagicMock()
        with patch.object(ae_mod, 'call_llm', return_value=self._verdict(0.85, 'clearly stated')):
            out = judge_answer_entailment(db, 'passage', 'question?', 'answer', 2)
        assert out.reason == 'clearly stated'


# ---------------------------------------------------------------------------
# distractor_plausibility
# ---------------------------------------------------------------------------

class TestDistractorPlausibility:

    def _verdict(self, confidences, reasons=None) -> DistractorPlausibilityVerdict:
        return DistractorPlausibilityVerdict(
            per_distractor=confidences,
            reasons=reasons or ['ok'] * len(confidences),
        )

    def test_all_accept(self):
        db = MagicMock()
        with patch.object(dp_mod, 'call_llm',
                          return_value=self._verdict([0.9, 0.85, 0.95])):
            outcomes = judge_distractor_plausibility(
                db, 'p', 'q?', 'a', ['d1', 'd2', 'd3'], 2
            )
        assert all(o.verdict == 'accept' for o in outcomes)
        assert len(outcomes) == 3

    def test_one_flag(self):
        db = MagicMock()
        with patch.object(dp_mod, 'call_llm',
                          return_value=self._verdict([0.9, 0.7, 0.9])):
            outcomes = judge_distractor_plausibility(
                db, 'p', 'q?', 'a', ['d1', 'd2', 'd3'], 2
            )
        assert outcomes[1].verdict == 'flag'
        assert outcomes[0].verdict == 'accept'

    def test_one_reject(self):
        db = MagicMock()
        with patch.object(dp_mod, 'call_llm',
                          return_value=self._verdict([0.9, 0.4, 0.9])):
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

    def test_length_mismatch_safe_accepts_all(self):
        db = MagicMock()
        # LLM returns 2 confidences for 3 distractors
        with patch.object(dp_mod, 'call_llm',
                          return_value=self._verdict([0.9, 0.4])):
            outcomes = judge_distractor_plausibility(
                db, 'p', 'q?', 'a', ['d1', 'd2', 'd3'], 2
            )
        assert all(o.verdict == 'accept' for o in outcomes)
        assert len(outcomes) == 3

    def test_template_load_error_safe_accepts_all(self):
        dp_mod._cfg_cache.clear()
        db = MagicMock()
        with patch.object(dp_mod, 'get_template_config', side_effect=RuntimeError('missing')):
            outcomes = judge_distractor_plausibility(
                db, 'p', 'q?', 'a', ['d1', 'd2'], 2
            )
        assert all(o.verdict == 'accept' for o in outcomes)
        assert len(outcomes) == 2
