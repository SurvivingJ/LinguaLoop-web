"""The ``anthropic`` provider: Messages API behind the chat.completions facade."""

from types import SimpleNamespace
from unittest.mock import patch

import services.llm_service as svc
from services import anthropic_api_client as ac


class _FakeMessages:
    def __init__(self, message):
        self.message = message
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.message


class _FakeSdk:
    def __init__(self, message):
        self.messages = _FakeMessages(message)

    def with_options(self, **_):
        return self


def _message(text='{"ok": true}', stop='end_turn', model='claude-sonnet-5-5',
             in_tok=1000, out_tok=500):
    return SimpleNamespace(
        content=[SimpleNamespace(type='thinking', thinking=''),
                 SimpleNamespace(type='text', text=text)],
        stop_reason=stop, model=model, id='msg_1',
        usage=SimpleNamespace(input_tokens=in_tok, output_tokens=out_tok,
                              cache_read_input_tokens=0,
                              cache_creation_input_tokens=0),
    )


def _client(message):
    client = ac.AnthropicApiClient.__new__(ac.AnthropicApiClient)
    client.base_url = ac.ANTHROPIC_API_BASE_URL
    client._sdk = _FakeSdk(message)
    client.chat = ac._Chat(client)
    return client


def test_request_drops_openrouter_and_sampling_fields_and_splits_system():
    client = _client(_message())
    client.chat.completions.create(
        model='deepseek/deepseek-v4-flash',
        messages=[{'role': 'system', 'content': 'sys'},
                  {'role': 'user', 'content': 'hi'}],
        temperature=0.0, seed=7, max_tokens=4000,
        response_format={'type': 'json_object'},
        extra_body={'usage': {'include': True}},
    )
    sent = client._sdk.messages.calls[0]
    assert sent['model'] == ac.ANTHROPIC_API_MODEL  # non-Claude slug replaced
    assert sent['system'] == 'sys'
    assert sent['messages'] == [{'role': 'user', 'content': 'hi'}]
    assert sent['max_tokens'] == 4000
    for dropped in ('temperature', 'seed', 'response_format', 'extra_body'):
        assert dropped not in sent


def test_claude_model_is_honoured():
    assert ac.served_model('claude-haiku-5-5') == 'claude-haiku-5-5'
    assert ac.served_model('qwen/qwen3.6-flash') == ac.ANTHROPIC_API_MODEL


def test_response_shape_text_usage_and_list_price_cost():
    resp = _client(_message()).chat.completions.create(
        model='claude-sonnet-5-5', messages=[{'role': 'user', 'content': 'x'}])
    assert resp.choices[0].message.content == '{"ok": true}'  # thinking block skipped
    assert resp.choices[0].finish_reason == 'stop'
    assert svc._extract_usage_tokens(resp)[:2] == (1000, 500)
    # 1000 in x $2/M + 500 out x $10/M
    assert svc._extract_cost(resp) == 0.007


def test_max_tokens_stop_maps_to_length():
    resp = _client(_message(text='', stop='max_tokens')).chat.completions.create(
        model='claude-sonnet-5-5', messages=[{'role': 'user', 'content': 'x'}])
    assert resp.choices[0].finish_reason == 'length'


def test_unpriced_model_reports_no_cost():
    resp = _client(_message(model='claude-unknown-1')).chat.completions.create(
        model='claude-unknown-1', messages=[{'role': 'user', 'content': 'x'}])
    assert svc._extract_cost(resp) is None


def test_provider_resolves_to_anthropic_client_and_claude_model():
    assert svc._resolve_provider('anthropic')[0] == ac.ANTHROPIC_API_BASE_URL
    assert svc._resolve_model('deepseek/deepseek-v4-flash', None, 'anthropic') \
        == ac.ANTHROPIC_API_MODEL
    assert not svc._is_openrouter(_client(_message()))


def test_call_llm_end_to_end_through_the_facade():
    client = _client(_message(text='{"1": "定义"}'))
    with patch.object(svc, 'get_client', lambda *a, **kw: client), \
         patch.object(svc, '_log_llm_call', lambda **kw: None):
        out = svc.call_llm('prompt', model='claude-sonnet-5-5', provider='anthropic',
                           response_format='json_object', task_name='t', pipeline='p')
    assert out == {'1': '定义'}
