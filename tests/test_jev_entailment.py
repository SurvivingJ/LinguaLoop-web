"""jev backend for the answer-entailment judge.

Four things are pinned, matching the risks of swapping a Likert chat judge for a
probability decision model behind a flag:

1. **The client** speaks the Decisions wire format, retries only what is
   retryable, and records ``cost_usd`` (the column that silently stayed NULL on
   four incumbent judges).
2. **The probability -> verdict mapping** sits on the calibrated cutoffs, at the
   boundaries, in every language, and the prompts are entirely in that language.
3. **Flag switching**: default ``llm`` never touches jev; ``jev`` never touches
   the LLM unless jev fails; ``shadow`` returns the LLM verdict no matter what
   jev does.
4. **Fail-closed behaviour is preserved**: a jev outage falls back to the LLM
   judge, and only a double failure reaches ``safe_accept`` -- which still
   raises ``JudgeUnavailable`` inside ``batch_mode()`` and still fails open when
   serving.

Run: ``PYTHONPATH=. pytest tests/test_jev_entailment.py``
"""

import re
from unittest.mock import MagicMock, patch

import pytest
import requests

import services.exercise_generation.judges.answer_entailment as ae_mod
import services.exercise_generation.judges.answer_entailment_jev as jev_mod
import services.jev_client as jc
from services.exercise_generation.judges.base import (
    JudgeOutcome,
    JudgeUnavailable,
    batch_mode,
)
from services.jev_client import JevError, JevResult
from services.test_generation.schemas import AnswerEntailmentVerdict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resp(status=200, body=None, headers=None):
    r = MagicMock()
    r.status_code = status
    r.headers = headers or {}
    r.json.return_value = body if body is not None else {}
    r.text = str(body)
    return r


def _ok(noul=0.9, cost=0.00004):
    return _resp(200, {
        'id': 'gen-dec-1', 'model': 'typesafe/jev-1.13-20260917',
        'answers': {'entailed': {'type': 'noul', 'noul': noul}},
        'usage': {'input_tokens': 900, 'output_tokens': 12, 'cost': cost},
    })


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test-key')
    monkeypatch.setenv(ae_mod._BACKEND_ENV, 'llm')   # each test opts in to what it needs
    monkeypatch.setattr(jc, '_sleep', lambda _s: None)
    ae_mod._cfg_cache.clear()
    yield
    ae_mod._cfg_cache.clear()


_QUESTIONS = jev_mod.RUBRIC[2]
_STATE = {'passage': 'p', 'question': 'q', 'candidate': 'c'}


def _call(**kw):
    kw.setdefault('log', False)
    return jc.call_jev(_STATE, _QUESTIONS, **kw)


# ---------------------------------------------------------------------------
# 1. Client
# ---------------------------------------------------------------------------

class TestClient:
    def test_success_returns_answers_and_cost(self):
        with patch.object(jc.requests, 'post', return_value=_ok(0.8, 0.00004)) as post:
            res = _call()
        assert res.answers['entailed']['noul'] == 0.8
        assert res.cost_usd == 0.00004
        assert res.model == 'typesafe/jev-1.13-20260917'
        body = post.call_args.kwargs['json']
        assert body['model'] == 'typesafe/jev-1.13'
        assert body['state'] == _STATE and body['questions'] == _QUESTIONS
        assert post.call_args.kwargs['headers']['Authorization'] == 'Bearer test-key'

    def test_key_is_read_at_call_time(self, monkeypatch):
        monkeypatch.delenv('OPENROUTER_API_KEY')
        with patch.object(jc.requests, 'post') as post:
            with pytest.raises(JevError, match='OPENROUTER_API_KEY'):
                _call()
        post.assert_not_called()

    def test_429_honours_retry_after_then_succeeds(self):
        sleeps = []
        with patch.object(jc, '_sleep', sleeps.append), patch.object(
            jc.requests, 'post',
            side_effect=[_resp(429, headers={'Retry-After': '3'}), _ok()],
        ):
            _call()
        assert sleeps == [3.0]

    def test_transient_402_retries(self):
        with patch.object(jc.requests, 'post', side_effect=[
            _resp(402, {'limit_source': 'openrouter_in_flight_budget'}), _ok(),
        ]) as post:
            _call()
        assert post.call_count == 2

    def test_permanent_402_fails_immediately(self):
        with patch.object(jc.requests, 'post',
                          return_value=_resp(402, {'error': 'credits'})) as post:
            with pytest.raises(JevError, match='402'):
                _call()
        assert post.call_count == 1          # retrying cannot help

    def test_5xx_retries_then_raises(self):
        with patch.object(jc.requests, 'post', return_value=_resp(503)) as post:
            with pytest.raises(JevError, match='503'):
                _call(max_retries=2)
        assert post.call_count == 3          # first attempt + 2 retries

    def test_network_error_retries(self):
        with patch.object(jc.requests, 'post', side_effect=[
            requests.ConnectionError('boom'), _ok(),
        ]) as post:
            _call()
        assert post.call_count == 2

    def test_network_error_exhausted_raises_jev_error(self):
        with patch.object(jc.requests, 'post',
                          side_effect=requests.ConnectionError('boom')):
            with pytest.raises(JevError, match='network'):
                _call(max_retries=1)

    def test_other_4xx_is_not_retried(self):
        with patch.object(jc.requests, 'post', return_value=_resp(400, {'e': 'bad'})) as post:
            with pytest.raises(JevError, match='400'):
                _call()
        assert post.call_count == 1

    def test_response_without_answers_raises(self):
        with patch.object(jc.requests, 'post', return_value=_resp(200, {'model': 'x'})):
            with pytest.raises(JevError, match='answers'):
                _call()

    def test_cost_usd_reaches_llm_calls_row_non_null(self):
        """The guardrail this column exists for: NULL cost disarms every ceiling."""
        with patch.object(jc.requests, 'post', return_value=_ok(0.5, 0.000018396)), \
             patch('services.llm_service._log_llm_call') as log:
            jc.call_jev(_STATE, _QUESTIONS, task_name='judge_answer_entailment',
                        language_code='en')
        row = log.call_args.kwargs
        assert row['cost_usd'] == 0.000018396
        assert row['task_name'] == 'judge_answer_entailment'
        assert row['model'] == 'typesafe/jev-1.13-20260917'
        assert row['language_code'] == 'en'
        assert row['judge_confidence'] is None

    def test_missing_cost_is_none_not_zero(self, caplog):
        resp = _ok()
        resp.json.return_value['usage'] = {'input_tokens': 1}
        with patch.object(jc.requests, 'post', return_value=resp):
            res = _call()
        assert res.cost_usd is None          # NULL stays visibly NULL
        assert 'no usage.cost' in caplog.text

    def test_logging_failure_never_breaks_the_call(self):
        with patch.object(jc.requests, 'post', return_value=_ok()), \
             patch('services.llm_service._log_llm_call', side_effect=RuntimeError('db')):
            res = jc.call_jev(_STATE, _QUESTIONS)
        assert res.answers


# ---------------------------------------------------------------------------
# 2. Probability -> verdict, and the prompts
# ---------------------------------------------------------------------------

class TestMapping:
    @pytest.mark.parametrize('lang', [1, 2, 3])
    @pytest.mark.parametrize('p,expected', [
        (0.0, 'reject'), (0.29, 'reject'), (0.2999, 'reject'),
        (0.30, 'flag'), (0.45, 'flag'), (0.5999, 'flag'),
        (0.60, 'accept'), (0.95, 'accept'), (1.0, 'accept'),
    ])
    def test_cutoffs(self, lang, p, expected):
        assert jev_mod.probability_to_verdict(p, lang) == expected

    def test_cutoffs_are_ordered_in_every_language(self):
        for lang, (reject_below, accept_at) in jev_mod.CUTOFFS.items():
            assert 0.0 < reject_below < accept_at <= 1.0, lang

    @pytest.mark.parametrize('lang', [1, 3])
    def test_zh_ja_prompts_are_entirely_in_the_content_language(self, lang):
        q = jev_mod.RUBRIC[lang]['entailed']
        prose = q['instructions'] + q['criteria']['true'] + q['criteria']['false']
        # The only Latin text allowed is the state field names the instruction
        # refers to -- those are protocol, not prose.
        stripped = re.sub(r'passage|question|candidate', '', prose)
        assert not re.search(r'[A-Za-z]', stripped)
        assert re.search(r'[぀-ヿ一-鿿]', prose)

    def test_en_prompt_is_english(self):
        q = jev_mod.RUBRIC[2]['entailed']
        assert q['type'] == 'noul'
        assert not re.search(r'[぀-ヿ一-鿿]', str(q))

    def test_reason_is_in_the_content_language(self):
        for lang, pattern in ((1, r'[一-鿿]'), (3, r'[぀-ヿ]')):
            for v in ('accept', 'flag', 'reject'):
                assert re.search(pattern, jev_mod._REASONS[lang][v])


class TestEvaluate:
    def _patch_call(self, answers, cost=0.00004):
        return patch.object(jev_mod, 'call_jev', return_value=JevResult(
            answers=answers, model='typesafe/jev-1.13-20260917', cost_usd=cost,
            input_tokens=1, output_tokens=1, latency_ms=5,
        ))

    def test_maps_and_synthesises_reason(self):
        with self._patch_call({'entailed': {'type': 'noul', 'noul': 0.12}}) as call:
            v = jev_mod.evaluate('P', 'Q', 'A', 2, task_name='t')
        assert v.verdict == 'reject' and v.probability == 0.12
        assert '0.12' in v.reason
        assert call.call_args.kwargs['state'] == {
            'passage': 'P', 'question': 'Q', 'candidate': 'A'}
        assert call.call_args.kwargs['language_code'] == 'en'

    @pytest.mark.parametrize('answers', [
        {}, {'entailed': {}}, {'entailed': {'noul': None}},
        {'entailed': {'noul': 1.4}}, {'entailed': {'noul': -0.1}},
        {'entailed': {'noul': 'high'}}, {'entailed': {'noul': True}},
    ])
    def test_unusable_noul_is_a_failure_not_an_accept(self, answers):
        with self._patch_call(answers):
            with pytest.raises(JevError):
                jev_mod.evaluate('P', 'Q', 'A', 2, task_name='t')

    def test_unknown_language_raises(self):
        with pytest.raises(JevError):
            jev_mod.evaluate('P', 'Q', 'A', 99, task_name='t')


# ---------------------------------------------------------------------------
# 3. Flag switching
# ---------------------------------------------------------------------------

_CFG = {'template': 'p:{0} q:{1} a:{2}', 'model': 'test-model',
        'provider': 'openrouter', 'version': 3}


def _llm(rating=5):
    return patch.object(ae_mod, 'call_llm',
                        return_value=AnswerEntailmentVerdict(rating=rating, reason='r'))


def _jev(p=0.9):
    return patch.object(ae_mod.answer_entailment_jev, 'call_jev', return_value=JevResult(
        answers={'entailed': {'type': 'noul', 'noul': p}},
        model='typesafe/jev-1.13-20260917', cost_usd=0.00004,
        input_tokens=1, output_tokens=1, latency_ms=5,
    ))


def _judge(lang=2):
    return ae_mod.judge_answer_entailment(MagicMock(), 'P', 'Q?', 'A', lang)


@pytest.fixture
def cfg():
    with patch.object(ae_mod, '_load_cfg', return_value=dict(_CFG)):
        yield


@pytest.fixture(autouse=True)
def _no_db_rows():
    with patch.object(ae_mod, 'log_judge_verdict') as lj, \
         patch('services.llm_service._log_llm_call') as ll:
        ae_mod._test_lj, ae_mod._test_ll = lj, ll
        yield
    del ae_mod._test_lj, ae_mod._test_ll


class TestBackendSwitch:
    @pytest.mark.parametrize('value', [None, '', '  '])
    def test_default_is_jev_and_never_touches_the_llm(self, monkeypatch, cfg, value):
        # TASK-835: unset / blank means DEFAULT_BACKEND, which is jev.
        if value is None:
            monkeypatch.delenv(ae_mod._BACKEND_ENV, raising=False)
        else:
            monkeypatch.setenv(ae_mod._BACKEND_ENV, value)
        assert ae_mod.DEFAULT_BACKEND == 'jev'
        with _llm(5) as llm, _jev(0.9) as jev:
            out = _judge()
        assert out.backend == 'jev' and out.probability == 0.9
        assert out.confidence is None
        jev.assert_called_once()
        llm.assert_not_called()

    def test_explicit_llm_selects_the_llm_judge(self, monkeypatch, cfg):
        monkeypatch.setenv(ae_mod._BACKEND_ENV, 'llm')
        with _llm(5) as llm, _jev() as jev:
            out = _judge()
        assert out.verdict == 'accept' and out.backend == 'llm'
        assert out.confidence == 5.0 and out.probability is None
        llm.assert_called_once()
        jev.assert_not_called()

    @pytest.mark.parametrize('value', ['bogus', 'JEV2'])
    def test_unknown_value_means_llm_not_the_default(self, monkeypatch, cfg, value):
        monkeypatch.setenv(ae_mod._BACKEND_ENV, value)
        with _llm(5) as llm, _jev() as jev:
            out = _judge()
        assert out.backend == 'llm'
        llm.assert_called_once()
        jev.assert_not_called()

    def test_jev_backend_skips_the_llm(self, monkeypatch, cfg):
        monkeypatch.setenv(ae_mod._BACKEND_ENV, 'JeV ')      # case/space tolerant
        with _llm() as llm, _jev(0.95) as jev:
            out = _judge()
        assert out.verdict == 'accept' and out.backend == 'jev'
        assert out.probability == 0.95
        assert out.confidence is None                # never a probability in 1-5 column
        jev.assert_called_once()
        llm.assert_not_called()

    @pytest.mark.parametrize('p,expected', [(0.05, 'reject'), (0.45, 'flag'), (0.8, 'accept')])
    def test_jev_backend_verdicts(self, monkeypatch, cfg, p, expected):
        monkeypatch.setenv(ae_mod._BACKEND_ENV, 'jev')
        with _jev(p):
            out = _judge()
        assert out.verdict == expected
        assert ae_mod._test_lj.call_args.kwargs['confidence'] is None
        assert ae_mod._test_lj.call_args.kwargs['task_name'] == 'judge_answer_entailment'

    def test_jev_backend_judges_in_the_content_language(self, monkeypatch, cfg):
        monkeypatch.setenv(ae_mod._BACKEND_ENV, 'jev')
        with _jev(0.9) as jev:
            _judge(lang=1)
        assert jev.call_args.kwargs['questions'] is jev_mod.RUBRIC[1]

    def test_backend_is_read_per_call_without_restart(self, monkeypatch, cfg):
        with _llm() as llm, _jev() as jev:
            monkeypatch.setenv(ae_mod._BACKEND_ENV, 'llm')
            _judge()
            monkeypatch.setenv(ae_mod._BACKEND_ENV, 'jev')
            _judge()
        assert llm.call_count == 1 and jev.call_count == 1


class TestShadow:
    def test_returns_the_llm_verdict_and_logs_both(self, monkeypatch, cfg):
        monkeypatch.setenv(ae_mod._BACKEND_ENV, 'shadow')
        with _llm(2) as llm, _jev(0.95) as jev:     # they disagree on purpose
            out = _judge()
        assert out.verdict == 'reject' and out.backend == 'llm'
        llm.assert_called_once()
        jev.assert_called_once()
        row = ae_mod._test_ll.call_args.kwargs
        assert row['task_name'] == 'judge_answer_entailment_shadow'
        assert row['judge_verdict'] == 'accept'
        assert row['judge_confidence'] is None
        assert '"live_verdict": "reject"' in row['raw_response']
        assert '"p_yes": 0.95' in row['raw_response']

    def test_jev_failure_cannot_change_the_outcome(self, monkeypatch, cfg):
        monkeypatch.setenv(ae_mod._BACKEND_ENV, 'shadow')
        with _llm(5), patch.object(ae_mod.answer_entailment_jev, 'call_jev',
                                   side_effect=JevError('down')):
            out = _judge()
        assert out.verdict == 'accept' and out.backend == 'llm'
        ae_mod._test_ll.assert_not_called()

    def test_jev_failure_cannot_raise_inside_a_batch(self, monkeypatch, cfg):
        monkeypatch.setenv(ae_mod._BACKEND_ENV, 'shadow')
        with _llm(5), patch.object(ae_mod.answer_entailment_jev, 'call_jev',
                                   side_effect=RuntimeError('anything')):
            with batch_mode():
                out = _judge()
        assert out.verdict == 'accept'

    def test_observer_sees_both_verdicts_and_cannot_break_shadow(self, monkeypatch, cfg):
        monkeypatch.setenv(ae_mod._BACKEND_ENV, 'shadow')
        seen = []
        monkeypatch.setattr(ae_mod, 'shadow_observer', lambda *a: seen.append(a))
        with _llm(5), _jev(0.1):
            out = _judge()
        assert out.verdict == 'accept'
        passage, question, answer, lang, live, jv = seen[0]
        assert (passage, question, answer, lang) == ('P', 'Q?', 'A', 2)
        assert live.verdict == 'accept' and jv.verdict == 'reject'

        def boom(*_a):
            raise RuntimeError('observer bug')
        monkeypatch.setattr(ae_mod, 'shadow_observer', boom)
        with _llm(5), _jev(0.1):
            assert _judge().verdict == 'accept'      # still returned, no raise

    def test_llm_outage_in_batch_still_aborts(self, monkeypatch):
        """Shadow must not weaken the LLM path's own fail-closed contract."""
        monkeypatch.setenv(ae_mod._BACKEND_ENV, 'shadow')
        with patch.object(ae_mod, '_load_cfg', side_effect=RuntimeError('no row')), \
             _jev() as jev:
            with batch_mode():
                with pytest.raises(JudgeUnavailable):
                    _judge()
        jev.assert_not_called()


# ---------------------------------------------------------------------------
# 4. Fail-closed behaviour on jev errors
# ---------------------------------------------------------------------------

def _jev_down(exc=None):
    return patch.object(ae_mod.answer_entailment_jev, 'call_jev',
                        side_effect=exc or JevError('HTTP 402 (credits)'))


class TestJevFailure:
    @pytest.fixture(autouse=True)
    def _jev_backend(self, monkeypatch):
        monkeypatch.setenv(ae_mod._BACKEND_ENV, 'jev')

    def test_jev_error_falls_back_to_the_llm_judge(self, cfg):
        with _jev_down(), _llm(2) as llm:
            out = _judge()
        assert out.verdict == 'reject' and out.backend == 'llm'
        assert out.confidence == 2.0
        llm.assert_called_once()

    def test_unexpected_exception_also_falls_back(self, cfg):
        with _jev_down(ValueError('weird')), _llm(5):
            assert _judge().backend == 'llm'

    def test_unusable_noul_falls_back(self, cfg):
        with _jev(None), _llm(5) as llm:      # noul=None
            out = _judge()
        assert out.backend == 'llm'
        llm.assert_called_once()

    def test_fallback_still_works_inside_a_batch(self, cfg):
        with _jev_down(), _llm(5):
            with batch_mode():
                out = _judge()
        assert out.verdict == 'accept' and out.backend == 'llm'

    def test_both_down_aborts_the_batch(self):
        with _jev_down(), patch.object(ae_mod, '_load_cfg',
                                       side_effect=RuntimeError('no template')):
            with batch_mode():
                with pytest.raises(JudgeUnavailable):
                    _judge()

    def test_llm_call_failure_after_jev_failure_aborts_the_batch(self, cfg):
        with _jev_down(), patch.object(ae_mod, 'call_llm', side_effect=RuntimeError('dead slug')):
            with batch_mode():
                with pytest.raises(JudgeUnavailable):
                    _judge()

    def test_both_down_fails_open_when_serving(self):
        with _jev_down(), patch.object(ae_mod, '_load_cfg',
                                       side_effect=RuntimeError('no template')):
            out = _judge()
        assert out.verdict == 'accept'
        assert isinstance(out, JudgeOutcome)

    def test_healthy_jev_never_calls_the_llm_in_a_batch(self, cfg):
        with _jev(0.9), _llm() as llm:
            with batch_mode():
                out = _judge()
        assert out.backend == 'jev'
        llm.assert_not_called()


# ---------------------------------------------------------------------------
# Call site: the outcome shape survives `_apply_judges`
# ---------------------------------------------------------------------------

class TestApplyJudges:
    """`confidence` is None on jev; the call site must not format it as a float."""

    def _run(self, ae_outcome):
        import services.exercise_generation.judges.distractor_plausibility as dp_mod
        from services.test_generation.agents.question_generator import QuestionGenerator

        q = {'question': 'Q?', 'answer': 'A', 'choices': ['A', 'B', 'C', 'D']}
        accept = JudgeOutcome(verdict='accept', confidence=5.0, reason='ok')
        with patch.object(ae_mod, 'judge_answer_entailment', return_value=ae_outcome), \
             patch.object(dp_mod, 'judge_distractor_plausibility',
                          return_value=[accept] * 3):
            return QuestionGenerator._apply_judges(
                MagicMock(), q_entry=q, prose='P', db=MagicMock(),
                language_id=2, type_code='literal_detail',
            )

    def test_jev_reject_is_recorded_with_probability(self):
        out = JudgeOutcome(verdict='reject', confidence=None, reason='no support',
                           probability=0.07, backend='jev')
        entry, rejection = self._run(out)
        assert entry is None
        assert rejection['probability'] == 0.07
        assert rejection['backend'] == 'jev'
        assert rejection['confidence'] is None
        assert rejection['reason'] == 'no support'

    def test_jev_flag_payload_carries_probability(self):
        out = JudgeOutcome(verdict='flag', confidence=None, reason='unsure',
                           probability=0.45, backend='jev')
        entry, rejection = self._run(out)
        assert rejection is None
        assert entry['_judge_flags']['answer_entailment'] == {
            'confidence': None, 'probability': 0.45, 'backend': 'jev',
            'reason': 'unsure',
        }

    def test_llm_flag_payload_is_unchanged_in_shape(self):
        out = JudgeOutcome(verdict='flag', confidence=3.0, reason='meh')
        entry, _ = self._run(out)
        flag = entry['_judge_flags']['answer_entailment']
        assert flag['confidence'] == 3.0 and flag['backend'] == 'llm'
        assert flag['probability'] is None
