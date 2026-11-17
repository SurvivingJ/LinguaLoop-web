"""Grading-provider refusals (investigation point 6).

When the grading provider refuses the call — OpenRouter 403 key limit, 402 no
credits, 401 bad key, 429 daily quota — every grader path used to swallow the
error and the submit route returned an empty provisional grade ("Grading didn't
finish", which invites a retry that can never succeed). Now:

* ``services.dual_translation.provider_errors`` classifies those errors and
  records, per grading request, what each model call did;
* every grader call site (single-call ``_attempt``, v2 ``_invoke_model``, v1
  ``_call_tier`` incl. its worker-thread Tier 2) reports into that record;
* the submit route returns 503 ``GRADING_UNAVAILABLE`` and saves nothing when
  a refusal happened and no model answered at all.
"""

import contextvars
import json
import logging
import threading

import httpx
import openai
import pytest

import routes.dual_translation as dt_routes
from config import Config
from services.dimension_service import DimensionService
from services.dual_translation import grader_cascade, provider_errors, single_call_grader as scg, tier0
from services.dual_translation.router import ResolvedRoute
from tests.test_dual_translation_grader_cascade import (
    RUBRIC_CFG, TAXONOMY_CFG, _ten_word_gold, _ten_word_repro_five_wrong,
)
from tests.test_dual_translation_single_call_grader import (
    EN_GOLD, EN_TENSE, RUBRIC_V6, TAXONOMY_V6, _NoDB,
)

LANG_CODES = {1: 'zh', 2: 'en', 3: 'ja'}
_URL = 'https://openrouter.ai/api/v1/chat/completions'


def _status_error(cls, status, message, body=None):
    response = httpx.Response(status, request=httpx.Request('POST', _URL))
    return cls(f"Error code: {status} - {message}", response=response,
               body=body if body is not None else {'error': {'message': message, 'code': status}})


def key_limit():
    return _status_error(openai.PermissionDeniedError, 403, 'Key limit exceeded (total limit)')


def no_credits():
    return _status_error(openai.APIStatusError, 402, 'Insufficient credits')


def bad_key():
    return _status_error(openai.AuthenticationError, 401, 'No auth credentials found')


def daily_quota():
    return _status_error(
        openai.RateLimitError, 429,
        'Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day',
    )


def per_minute():
    return _status_error(openai.RateLimitError, 429, 'Rate limit exceeded: free-models-per-min.')


def timeout():
    return openai.APITimeoutError(request=httpx.Request('POST', _URL))


def server_error():
    return _status_error(openai.InternalServerError, 500, 'Internal Server Error')


# ---------------------------------------------------------------------------
# classify
# ---------------------------------------------------------------------------

class TestClassify:

    @pytest.mark.parametrize('make, status, kind', [
        (key_limit, 403, provider_errors.KIND_FORBIDDEN),
        (no_credits, 402, provider_errors.KIND_CREDITS),
        (bad_key, 401, provider_errors.KIND_AUTH),
        (daily_quota, 429, provider_errors.KIND_QUOTA),
    ])
    def test_refusals(self, make, status, kind):
        refusal = provider_errors.classify(make(), slug='m/x:free', role='primary')
        assert refusal is not None
        assert (refusal.status, refusal.kind, refusal.slug, refusal.role) == (status, kind, 'm/x:free', 'primary')
        assert str(status) in refusal.message

    @pytest.mark.parametrize('make', [per_minute, timeout, server_error,
                                      lambda: RuntimeError('503 upstream overloaded'),
                                      lambda: ValueError('bad json')])
    def test_transient_and_other_failures_are_not_refusals(self, make):
        assert provider_errors.classify(make()) is None

    def test_moderation_403_is_not_a_refusal(self):
        exc = _status_error(openai.PermissionDeniedError, 403, 'Input was flagged by moderation')
        assert provider_errors.classify(exc) is None

    def test_quota_wording_in_the_body_only(self):
        exc = _status_error(openai.RateLimitError, 429, 'Rate limit exceeded',
                            body={'error': {'message': 'Rate limit exceeded',
                                            'metadata': {'raw': 'daily quota reached'}}})
        assert provider_errors.classify(exc).kind == provider_errors.KIND_QUOTA

    def test_message_is_capped(self):
        exc = _status_error(openai.PermissionDeniedError, 403, 'x' * 2000)
        assert len(provider_errors.classify(exc).message) <= 300


# ---------------------------------------------------------------------------
# recorder
# ---------------------------------------------------------------------------

class TestRecorder:

    def test_outside_capture_notes_are_no_ops(self):
        assert provider_errors.note_failure(key_limit()) is not None
        provider_errors.note_answer()

    def test_refused_without_answer(self):
        with provider_errors.capture() as calls:
            provider_errors.note_failure(key_limit(), slug='a', role='primary')
            provider_errors.note_failure(key_limit(), slug='b', role='fallback')
        assert calls.refused_without_answer()
        assert [r['slug'] for r in calls.summary()] == ['a', 'b']

    def test_an_answer_means_not_refused(self):
        with provider_errors.capture() as calls:
            provider_errors.note_failure(key_limit(), slug='a')
            provider_errors.note_answer(slug='b')
        assert not calls.refused_without_answer()

    def test_transient_failures_only_are_not_refused(self):
        with provider_errors.capture() as calls:
            provider_errors.note_failure(timeout())
            provider_errors.note_failure(per_minute())
        assert not calls.refused_without_answer()
        assert calls.failed == 2

    def test_nested_captures_are_independent(self):
        with provider_errors.capture() as outer:
            with provider_errors.capture() as inner:
                provider_errors.note_failure(key_limit())
            provider_errors.note_answer()
        assert inner.refused_without_answer()
        assert not outer.refused_without_answer() and outer.refusals == []

    def test_copied_context_in_a_worker_thread_records_into_the_same_capture(self):
        with provider_errors.capture() as calls:
            ctx = contextvars.copy_context()
            t = threading.Thread(target=ctx.run, args=(provider_errors.note_failure, key_limit()))
            t.start()
            t.join()
        assert len(calls.refusals) == 1


# ---------------------------------------------------------------------------
# Every grader path reports into the capture
# ---------------------------------------------------------------------------

@pytest.fixture
def v6(monkeypatch):
    monkeypatch.setattr(DimensionService, 'get_language_code', classmethod(lambda cls, lid: LANG_CODES.get(lid)))
    monkeypatch.setattr(grader_cascade, 'get_active_rubric', lambda db: RUBRIC_V6)
    monkeypatch.setattr(grader_cascade, 'get_active_taxonomy', lambda db: TAXONOMY_V6)
    monkeypatch.setattr(grader_cascade, 'get_active_rubric_version', lambda db: 6)
    monkeypatch.setattr(grader_cascade, 'get_active_taxonomy_version', lambda db: 6)
    monkeypatch.setattr(Config, 'DT_SINGLE_CALL_MODEL', 'primary/model:free')
    monkeypatch.setattr(Config, 'DT_SINGLE_CALL_FALLBACK_MODEL', 'fallback/model:free')
    monkeypatch.setattr(Config, 'DT_SINGLE_CALL_FREE_TRANSLATION', False)
    monkeypatch.setattr(Config, 'DT_SINGLE_CALL_EXPLAINER', False)
    monkeypatch.setattr(scg, '_log_call', lambda attempt, **kw: None)
    monkeypatch.setattr(
        grader_cascade, 'resolve_tier',
        lambda db, tier, lid, **k: ResolvedRoute(requested_tier=tier, used_tier=tier,
                                                 slug=f'{tier}/model', fell_open=False),
    )
    tier0.clear_cache()
    yield
    tier0.clear_cache()


def _raise(exc_factory):
    def _call(*a, **k):
        raise exc_factory()
    return _call


def _grade(**kwargs):
    return grader_cascade.grade_submission(
        _NoDB(), passage_id=1, gold_l2=EN_GOLD, reproduction=EN_TENSE,
        l2_language_id=2, l1_language_id=1, age_tier=3, **kwargs,
    )


class TestGraderPaths:

    def test_single_call_then_v2_all_refused(self, v6, monkeypatch):
        monkeypatch.setattr(scg, 'call_structured', _raise(key_limit))
        monkeypatch.setattr(grader_cascade, 'call_model_with_usage', _raise(key_limit))
        with provider_errors.capture() as calls:
            contract = _grade(single_call=True, framework_v2=True)
        assert contract.get('overall_band') is None  # what used to reach the learner
        assert calls.refused_without_answer()
        roles = [r['role'] for r in calls.summary()]
        assert roles[:2] == ['primary', 'fallback']
        assert len(roles) >= 3  # the v2 detector was refused too

    def test_single_call_refused_but_v2_answers_is_not_unavailable(self, v6, monkeypatch):
        monkeypatch.setattr(scg, 'call_structured', _raise(daily_quota))
        monkeypatch.setattr(grader_cascade, 'call_model_with_usage',
                            lambda *a, **k: ('not json', 5, 5, 0.1))
        with provider_errors.capture() as calls:
            _grade(single_call=True, framework_v2=True)
        assert calls.refusals and calls.answered >= 1
        assert not calls.refused_without_answer()

    def test_single_call_transient_failure_is_not_a_refusal(self, v6, monkeypatch):
        monkeypatch.setattr(scg, 'call_structured', _raise(timeout))
        monkeypatch.setattr(grader_cascade, 'call_model_with_usage', _raise(server_error))
        with provider_errors.capture() as calls:
            _grade(single_call=True, framework_v2=True)
        assert calls.refusals == [] and calls.failed >= 3
        assert not calls.refused_without_answer()

    def test_v1_concurrent_tier2_records_from_its_worker_thread(self, monkeypatch):
        monkeypatch.setattr(DimensionService, 'get_language_code', classmethod(lambda cls, lid: LANG_CODES.get(lid)))
        monkeypatch.setattr(grader_cascade, 'get_active_rubric', lambda db: RUBRIC_CFG)
        monkeypatch.setattr(grader_cascade, 'get_active_taxonomy', lambda db: TAXONOMY_CFG)
        monkeypatch.setattr(
            grader_cascade, 'resolve_tier',
            lambda db, tier, lid, **k: ResolvedRoute(requested_tier=tier, used_tier=tier,
                                                     slug=f'{tier}-slug', fell_open=False),
        )
        threads = set()

        def _refuse(model, *a, **k):
            threads.add(threading.get_ident())
            raise no_credits()
        monkeypatch.setattr(grader_cascade, 'call_model_with_usage', _refuse)
        tier0.clear_cache()
        with provider_errors.capture() as calls:
            grader_cascade.grade_submission(
                None, passage_id=643, gold_l2=_ten_word_gold(),
                reproduction=_ten_word_repro_five_wrong(),
                l2_language_id=2, l1_language_id=1, age_tier=3, framework_v2=False, single_call=False,
            )
        tier0.clear_cache()
        assert len(threads) == 2  # tier 1 on this thread, tier 2 on the worker
        assert sorted(r['role'] for r in calls.summary()) == ['tier1', 'tier2']
        assert calls.refused_without_answer()


# ---------------------------------------------------------------------------
# Submit route
# ---------------------------------------------------------------------------

class TestSubmitRoute:

    _OWNER = 'test-user-id-123'

    @pytest.fixture
    def wired(self, monkeypatch):
        monkeypatch.setattr(dt_routes, '_get_submission', lambda db, sid: {
            'id': 5, 'user_id': self._OWNER, 'passage_id': 9, 'l1_language_id': 2})
        monkeypatch.setattr(dt_routes, '_cached_grade', lambda db, sid: None)
        monkeypatch.setattr(dt_routes, '_get_passage', lambda db, pid: {
            'id': 9, 'l2_text': 'gold', 'l2_language_id': 3, 'age_tier': 3, 'status': 'active'})
        monkeypatch.setattr(dt_routes, '_tokens_used_today', lambda db, uid: 0)
        persisted = []
        monkeypatch.setattr(dt_routes, '_persist_grade', lambda *a, **k: persisted.append(a))
        monkeypatch.setattr(dt_routes, '_persist_grading_assets', lambda *a, **k: None)
        monkeypatch.setattr(dt_routes, 'credit_study_time', lambda *a, **k: None)
        monkeypatch.setattr(dt_routes.repair_hooks, 'after_grade', lambda db, contract, **kw: contract)
        return persisted

    @staticmethod
    def _grader(*failures, answered=0, band=None):
        def _fake(db, **kwargs):
            for exc in failures:
                provider_errors.note_failure(exc, slug='m/x:free', role='primary')
            for _ in range(answered):
                provider_errors.note_answer(slug='m/y:free', role='fallback')
            return {
                'scores': {} if band is None else {'accuracy': band}, 'overall_band': band,
                'diff': [], 'errors': [], 'provisional': band is None,
                'grader_trace': {'tokens': {'in': 0, 'out': 0}},
            }
        return _fake

    @pytest.mark.parametrize('make', [key_limit, no_credits, bad_key, daily_quota])
    def test_refusal_returns_grading_unavailable_and_saves_nothing(
        self, client, auth_headers, monkeypatch, wired, caplog, make,
    ):
        monkeypatch.setattr(dt_routes, 'grade_submission', self._grader(make(), make()))
        with caplog.at_level(logging.ERROR, logger='routes.dual_translation'):
            resp = client.post('/api/dual-translation/5/submit', headers=auth_headers,
                               json={'reproduction': '猫です'})
        assert resp.status_code == 503
        body = json.loads(resp.data)
        assert body['error_code'] == 'GRADING_UNAVAILABLE' == provider_errors.ERROR_CODE
        assert 'not graded' in body['error']
        assert wired == []  # no dt_grade / dt_error_instance write
        records = [r for r in caplog.records if r.levelno == logging.ERROR
                   and 'DT grading unavailable' in r.getMessage()]
        assert len(records) == 1
        msg = records[0].getMessage()
        assert 'submission=5' in msg and 'm/x:free' in msg and str(make().status_code) in msg

    def test_transient_failure_keeps_the_provisional_path(self, client, auth_headers, monkeypatch, wired):
        monkeypatch.setattr(dt_routes, 'grade_submission', self._grader(timeout(), per_minute()))
        resp = client.post('/api/dual-translation/5/submit', headers=auth_headers,
                           json={'reproduction': '猫です'})
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body['overall_band'] is None and body['provisional'] is True
        assert wired == []

    def test_refusal_then_a_real_grade_is_saved(self, client, auth_headers, monkeypatch, wired):
        monkeypatch.setattr(dt_routes, 'grade_submission', self._grader(key_limit(), answered=1, band=3))
        resp = client.post('/api/dual-translation/5/submit', headers=auth_headers,
                           json={'reproduction': '猫です'})
        assert resp.status_code == 200
        assert json.loads(resp.data)['overall_band'] == 3
        assert len(wired) == 1

    def test_tier0_grade_with_no_model_call_is_saved(self, client, auth_headers, monkeypatch, wired):
        monkeypatch.setattr(dt_routes, 'grade_submission', self._grader(band=4))
        resp = client.post('/api/dual-translation/5/submit', headers=auth_headers,
                           json={'reproduction': 'gold'})
        assert resp.status_code == 200
        assert len(wired) == 1
