"""jev client features the tier pipeline relies on (ADR-029), on top of the
retry-policy coverage in test_jev_entailment.py: ``JevError.status``, the
verdict/confidence llm_calls columns, a bounded number of in-flight requests,
and ``cost_usd`` actually reaching the row that is written.
"""

import threading
import time
from types import SimpleNamespace

import pytest

import services.jev_client as jc
from services.jev_client import JevError, call_jev

OK_BODY = {
    'id': 'gen-dec-1',
    'model': 'typesafe/jev-1.13-20260917',
    'answers': {'tier': {'type': 'score', 'score': 2.1, 'confidence': 0.9,
                         'probabilities': {'2': 0.9, '3': 0.1}}},
    'usage': {'input_tokens': 1548, 'output_tokens': 60, 'cost': 0.0000650},
}


def resp(status=200, body=None, headers=None):
    payload = OK_BODY if body is None and status == 200 else (body or {})
    return SimpleNamespace(
        status_code=status, headers=headers or {}, json=lambda: payload,
        text=str(payload),
    )


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'sk-test')
    monkeypatch.setattr(jc, '_sleep', lambda s: None)


def logged_rows(monkeypatch):
    rows = []
    import services.llm_service as llm_service
    monkeypatch.setattr(llm_service, '_log_llm_call', lambda **f: rows.append(f))
    return rows


def post_returning(*steps):
    steps = list(steps)
    return lambda *a, **k: steps.pop(0)


def test_error_carries_the_last_http_status(monkeypatch):
    monkeypatch.setattr(jc.requests, 'post', post_returning(resp(400, {'e': 1})))
    with pytest.raises(JevError) as exc:
        call_jev({}, {})
    assert exc.value.status == 400

    body = {'limit_source': 'openrouter_credits'}
    monkeypatch.setattr(jc.requests, 'post', post_returning(resp(402, body)))
    with pytest.raises(JevError) as exc:
        call_jev({}, {})
    assert exc.value.status == 402

    monkeypatch.setattr(jc.requests, 'post', post_returning(*[resp(503, {})] * 9))
    with pytest.raises(JevError) as exc:
        call_jev({}, {}, max_retries=2)
    assert exc.value.status == 503


def test_network_and_shape_errors_have_no_status(monkeypatch):
    monkeypatch.setattr(jc.requests, 'post', post_returning(resp(200, {'no': 1})))
    with pytest.raises(JevError) as exc:
        call_jev({}, {})
    assert exc.value.status is None


def test_summarize_feeds_verdict_and_confidence(monkeypatch):
    rows = logged_rows(monkeypatch)
    monkeypatch.setattr(jc.requests, 'post', post_returning(resp()))
    call_jev({}, {}, pipeline='tier_assignment', task_name='jev_tier_passage',
             language_code='zh',
             summarize=lambda a: ('T3', a['tier']['confidence']))
    assert len(rows) == 1
    row = rows[0]
    assert row['pipeline'] == 'tier_assignment'
    assert row['task_name'] == 'jev_tier_passage'
    assert row['language_code'] == 'zh'
    assert row['judge_verdict'] == 'T3' and row['judge_confidence'] == 0.9
    assert row['cost_usd'] == pytest.approx(0.000065)
    assert row['input_tokens'] == 1548 and row['output_tokens'] == 60


def test_a_broken_summarize_hook_does_not_lose_the_row(monkeypatch):
    rows = logged_rows(monkeypatch)
    monkeypatch.setattr(jc.requests, 'post', post_returning(resp()))
    call_jev({}, {}, summarize=lambda a: 1 / 0)
    assert len(rows) == 1 and rows[0]['judge_verdict'] is None
    assert rows[0]['cost_usd'] == pytest.approx(0.000065)


def test_concurrency_is_bounded(monkeypatch):
    monkeypatch.setattr(jc, '_semaphore', threading.BoundedSemaphore(2))
    logged_rows(monkeypatch)
    lock = threading.Lock()
    state = {'now': 0, 'peak': 0}

    def post(*a, **k):
        with lock:
            state['now'] += 1
            state['peak'] = max(state['peak'], state['now'])
        time.sleep(0.03)
        with lock:
            state['now'] -= 1
        return resp()

    monkeypatch.setattr(jc.requests, 'post', post)
    threads = [threading.Thread(target=lambda: call_jev({}, {})) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert state['peak'] == 2


def test_cost_usd_reaches_the_llm_calls_insert(monkeypatch):
    """The real logger with a fake Supabase: cost_usd must not go NULL."""
    import services.llm_service as llm_service
    import services.supabase_factory as factory

    inserted = []

    class FakeTable:
        def insert(self, row):
            inserted.append(row)
            return self

        def execute(self):
            return None

    monkeypatch.setattr(
        factory, 'get_supabase_admin',
        lambda: SimpleNamespace(table=lambda name: FakeTable()))
    monkeypatch.setattr(llm_service, '_log_llm_call_csv', lambda row: None)
    monkeypatch.setattr(jc.requests, 'post', post_returning(resp()))

    call_jev({}, {}, task_name='jev_tier_passage', language_code='zh')
    assert len(inserted) == 1
    row = inserted[0]
    assert row['task_name'] == 'jev_tier_passage' and row['language_code'] == 'zh'
    assert row['cost_usd'] == pytest.approx(0.000065)
    assert row['prompt_tokens'] == 1548 and row['completion_tokens'] == 60
    assert row['model'] == 'typesafe/jev-1.13-20260917'
