"""LLM_FORCE_PROVIDER=claude_cli keeps a run off OpenRouter entirely."""

import pytest

import services.llm_service as svc
from services import jev_client, tier_classifier
from services.exercise_generation.judges import answer_entailment


class _Stop(Exception):
    pass


def test_forced_provider_parsing(monkeypatch):
    monkeypatch.delenv('LLM_FORCE_PROVIDER', raising=False)
    assert svc.forced_provider() is None
    monkeypatch.setenv('LLM_FORCE_PROVIDER', ' Claude-CLI ')
    assert svc.forced_provider() == 'claude_cli'
    monkeypatch.setenv('LLM_FORCE_PROVIDER', '')
    assert svc.forced_provider() is None


def test_call_llm_overrides_a_pinned_provider(monkeypatch):
    seen = []

    def fake_get_client(provider=None, **kw):
        seen.append(provider)
        raise _Stop

    monkeypatch.setenv('LLM_FORCE_PROVIDER', 'claude_cli')
    monkeypatch.setattr(svc, 'get_client', fake_get_client)
    with pytest.raises(_Stop):
        svc.call_llm('hi', provider='openrouter')
    assert seen == ['claude_cli']


def test_call_llm_unchanged_without_force(monkeypatch):
    seen = []

    def fake_get_client(provider=None, **kw):
        seen.append(provider)
        raise _Stop

    monkeypatch.delenv('LLM_FORCE_PROVIDER', raising=False)
    monkeypatch.setattr(svc, 'get_client', fake_get_client)
    with pytest.raises(_Stop):
        svc.call_llm('hi', provider='openrouter')
    assert seen == ['openrouter']


def test_get_client_by_name_follows_force(monkeypatch):
    monkeypatch.setenv('LLM_FORCE_PROVIDER', 'claude_cli')
    assert svc._resolve_provider(svc.forced_provider() or 'openrouter')[0] == svc.CLAUDE_CLI_BASE_URL


@pytest.mark.parametrize('configured', ['jev', 'shadow', ''])
def test_entailment_leaves_jev_when_forced(monkeypatch, configured):
    monkeypatch.setenv('LLM_FORCE_PROVIDER', 'claude_cli')
    monkeypatch.setenv('ENTAILMENT_JUDGE_BACKEND', configured)
    assert answer_entailment._backend() == 'llm'


def test_entailment_backend_unchanged_without_force(monkeypatch):
    monkeypatch.delenv('LLM_FORCE_PROVIDER', raising=False)
    monkeypatch.setenv('ENTAILMENT_JUDGE_BACKEND', 'jev')
    assert answer_entailment._backend() == 'jev'


def test_call_jev_refuses_when_forced(monkeypatch):
    monkeypatch.setenv('LLM_FORCE_PROVIDER', 'claude_cli')

    def no_network(*a, **kw):
        raise AssertionError('jev must not be called')

    monkeypatch.setattr(jev_client.requests, 'post', no_network)
    with pytest.raises(jev_client.JevError, match='disabled'):
        jev_client.call_jev({'s': 'x'}, {'q': {}})


def test_classify_passage_uses_claude_when_forced(monkeypatch):
    monkeypatch.setenv('LLM_FORCE_PROVIDER', 'claude_cli')
    calls = []

    def fake_call_llm(prompt, **kw):
        calls.append((prompt, kw))
        return kw['schema'](tier=3)

    monkeypatch.setattr(svc, 'call_llm', fake_call_llm)
    monkeypatch.setattr(jev_client, 'call_jev', lambda *a, **k: pytest.fail('jev called'))

    a = tier_classifier.classify_passage('今日は学校に行きました。', 'ja')

    assert a.tier == 3 and a.score == 2.0 and a.expected_tier == 3.0
    assert a.calibration == 'claude-uncalibrated'
    assert a.probabilities == {1: 0.0, 2: 0.0, 3: 1.0, 4: 0.0, 5: 0.0, 6: 0.0}
    assert a.model.startswith('claude-cli:')
    (prompt, kw), = calls
    assert kw['provider'] == 'claude_cli'
    assert '今日は学校に行きました。' in prompt
    assert prompt.count('\n1. ') == 1 and '\n6. ' in prompt


def test_classify_passage_claude_failure_raises_jev_error(monkeypatch):
    monkeypatch.setenv('LLM_FORCE_PROVIDER', 'claude_cli')

    def boom(prompt, **kw):
        raise RuntimeError('cli down')

    monkeypatch.setattr(svc, 'call_llm', boom)
    with pytest.raises(jev_client.JevError, match='claude tier rating failed'):
        tier_classifier.classify_passage('テキスト', 'ja')


def test_prose_writer_client_follows_force(monkeypatch):
    from services.test_generation.agents import prose_writer as pw
    seen = []
    monkeypatch.setenv('LLM_FORCE_PROVIDER', 'claude_cli')
    monkeypatch.setattr(pw, 'get_client', lambda provider=None, **kw: seen.append((provider, kw)) or object())
    pw.ProseWriter(api_key='x')
    assert seen == [('claude_cli', {})]
