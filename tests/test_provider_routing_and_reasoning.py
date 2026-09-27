"""TASK-813 / ADR-028 continuation — OpenRouter provider price routing +
reasoning disabled.

Two independent levers, both OpenRouter-only and both safety-gated:

  * `provider_routing` (`extra_body['provider']`) defaults to
    `{'sort': 'price'}` for `pipeline='vocab_ladder'` calls, and to nothing
    for every other pipeline, unless the caller passes an explicit value.
  * `disable_reasoning` defaults True for every pipeline, but is never sent
    to a model that needs reasoning mode to function at all
    (`_is_reasoning_only_model`) -- sending it there would break the call,
    not just leave it unaffected. The payload shape is per-model: most
    models get `extra_body['reasoning'] = {'exclude': True}`. Validated
    qwen-family models (`_use_enabled_false_reasoning_param`) get
    `{'enabled': False}` instead -- ADR-028 continuation (2026-09-28) found
    that `exclude: True` only hides reasoning from the response while
    OpenRouter still generates and bills it (85-90% of qwen/qwen3.7-plus
    completion tokens on vocab_ladder tasks were silently reasoning_tokens).
    When such a call is also price-routed, `provider.require_parameters =
    True` is added too, which is what actually fixes the "cheapest provider
    returns empty content" failure TASK-813 previously worked around by
    leaving reasoning ON for a price-routed qwen call.

DB-free and network-free: the OpenAI client is a hand-built double whose
`.create()` just records the payload it was given.
"""

import os

import pytest

import services.llm_service as svc


class _Usage:
    def __init__(self):
        self.model_extra = {}


class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)


class _Response:
    def __init__(self, content='{"ok": true}'):
        self.choices = [_Choice(content)]
        self.usage = _Usage()
        self.model = None


class _Completions:
    def __init__(self, response):
        self._response = response
        self.last_payload = None

    def create(self, **payload):
        self.last_payload = payload
        return self._response


class _Chat:
    def __init__(self, response):
        self.completions = _Completions(response)


class _Client:
    def __init__(self, base_url='https://openrouter.ai/api/v1'):
        self.base_url = base_url
        self.chat = _Chat(_Response())


def _call(monkeypatch, client, **kwargs):
    monkeypatch.setattr(svc, 'get_client', lambda *a, **kw: client)
    monkeypatch.setattr(svc, '_log_llm_call', lambda **kw: None)
    return svc.call_llm(
        'prompt', model=kwargs.pop('model', 'google/gemini-3.5-flash-lite'),
        response_format='json_object', provider='openrouter',
        task_name='unit_probe', **kwargs,
    )


# ---------------------------------------------------------------------------
# provider_routing default
# ---------------------------------------------------------------------------

def test_default_provider_routing_applied_for_vocab_ladder(monkeypatch):
    client = _Client()
    _call(monkeypatch, client, pipeline='vocab_ladder')

    assert client.chat.completions.last_payload['extra_body']['provider'] == {
        'sort': 'price'}


def test_no_default_provider_routing_for_an_unlisted_pipeline(monkeypatch):
    """Only the pipelines named in `_PRICE_ROUTED_PIPELINES` get this default
    -- ADR-028's cost work targets vocab_ladder, not every pipeline."""
    client = _Client()
    _call(monkeypatch, client, pipeline='test_gen')

    assert 'provider' not in client.chat.completions.last_payload['extra_body']


def test_explicit_provider_routing_overrides_the_default(monkeypatch):
    client = _Client()
    _call(monkeypatch, client, pipeline='vocab_ladder',
          provider_routing={'sort': 'throughput'})

    assert client.chat.completions.last_payload['extra_body']['provider'] == {
        'sort': 'throughput'}


def test_explicit_provider_routing_applies_to_any_pipeline(monkeypatch):
    client = _Client()
    _call(monkeypatch, client, pipeline='test_gen',
          provider_routing={'sort': 'price'})

    assert client.chat.completions.last_payload['extra_body']['provider'] == {
        'sort': 'price'}


# ---------------------------------------------------------------------------
# reasoning disabled by default
# ---------------------------------------------------------------------------

def test_reasoning_excluded_by_default(monkeypatch):
    client = _Client()
    _call(monkeypatch, client, pipeline='vocab_ladder')

    assert client.chat.completions.last_payload['extra_body']['reasoning'] == {
        'exclude': True}


def test_reasoning_excluded_by_default_for_any_pipeline(monkeypatch):
    """disable_reasoning defaults True everywhere, not just vocab_ladder --
    a reasoning mode silently engaging is a cross-pipeline risk."""
    client = _Client()
    _call(monkeypatch, client, pipeline='test_gen')

    assert client.chat.completions.last_payload['extra_body']['reasoning'] == {
        'exclude': True}


def test_reasoning_not_sent_to_a_reasoning_only_model(monkeypatch):
    client = _Client()
    _call(monkeypatch, client, model='qwen/qwen3.8-max', pipeline='vocab_ladder')

    assert 'reasoning' not in client.chat.completions.last_payload['extra_body']
    # The provider-routing default still applies -- only reasoning is gated.
    assert client.chat.completions.last_payload['extra_body']['provider'] == {
        'sort': 'price'}


def test_reasoning_not_sent_when_caller_opts_out(monkeypatch):
    client = _Client()
    _call(monkeypatch, client, pipeline='vocab_ladder', disable_reasoning=False)

    assert 'reasoning' not in client.chat.completions.last_payload['extra_body']


def test_reasoning_and_routing_absent_for_a_non_openrouter_client(monkeypatch):
    client = _Client(base_url='http://localhost:11434/v1')
    _call(monkeypatch, client, pipeline='vocab_ladder')

    assert 'extra_body' not in client.chat.completions.last_payload


# ---------------------------------------------------------------------------
# ADR-028 Phase 1 rollout finding + continuation: price-routing + naive
# reasoning-exclude together reproducibly returned empty content from the
# cheapest qwen provider (live A/B on ladder_l4_morphology_generation /
# ladder_word_family_generation, qwen/qwen3.7-plus, EN, 2026-09-27). The
# 2026-09-28 continuation A/B (2 zh + 2 ja senses, full generate-for-sense
# pipeline) found the actual fix: `reasoning: {'enabled': False}` +
# `provider.require_parameters: True` -- not leaving reasoning ON, which
# Phase 1 showed silently cost 85-90% of completion tokens as
# reasoning_tokens on these tasks.
# ---------------------------------------------------------------------------

def test_reasoning_disabled_via_enabled_false_for_a_price_routed_qwen_model(monkeypatch):
    client = _Client()
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', pipeline='vocab_ladder')

    extra_body = client.chat.completions.last_payload['extra_body']
    assert extra_body['reasoning'] == {'enabled': False}
    # Price routing (the cost win) is kept, plus require_parameters so the
    # cheapest provider that doesn't support the reasoning param is skipped
    # instead of silently returning empty content for it.
    assert extra_body['provider'] == {'sort': 'price', 'require_parameters': True}


def test_reasoning_disabled_via_enabled_false_for_qwen_without_price_routing(monkeypatch):
    """`enabled: False` is the validated qwen payload regardless of price
    routing -- only `require_parameters` is conditional on a provider dict
    existing to add it to."""
    client = _Client()
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', pipeline='test_gen')

    extra_body = client.chat.completions.last_payload['extra_body']
    assert extra_body['reasoning'] == {'enabled': False}
    assert 'provider' not in extra_body


def test_reasoning_still_excluded_for_non_qwen_model_with_price_routing(monkeypatch):
    """Only the validated qwen family gets `enabled: False` -- a price-routed
    non-qwen model keeps the default `exclude: True` payload, and no
    require_parameters is added."""
    client = _Client()
    _call(monkeypatch, client, model='google/gemini-3.5-flash-lite',
          pipeline='vocab_ladder')

    extra_body = client.chat.completions.last_payload['extra_body']
    assert extra_body['reasoning'] == {'exclude': True}
    assert extra_body['provider'] == {'sort': 'price'}


def test_provider_routing_dict_is_not_mutated_in_place(monkeypatch):
    """`require_parameters` is added to a copy -- a caller-supplied
    provider_routing dict must come back untouched, since it may be a
    literal reused across calls for different models."""
    client = _Client()
    shared_routing = {'sort': 'price'}
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', pipeline='vocab_ladder',
          provider_routing=shared_routing)

    assert shared_routing == {'sort': 'price'}
    extra_body = client.chat.completions.last_payload['extra_body']
    assert extra_body['provider'] == {'sort': 'price', 'require_parameters': True}


@pytest.mark.parametrize('model', [
    'qwen/qwen3.7-plus',
    'QWEN/QWEN3.7-PLUS',
    'qwen/qwen-2.5-72b-instruct',
])
def test_unsafe_to_disable_reasoning_when_price_routed_matches_qwen_family(model):
    assert svc._unsafe_to_disable_reasoning_when_price_routed(model) is True


@pytest.mark.parametrize('model', [
    'google/gemini-3.5-flash-lite',
    'anthropic/claude-sonnet-5',
    'deepseek/deepseek-v4-flash',
    None,
    '',
])
def test_unsafe_to_disable_reasoning_when_price_routed_leaves_other_models_alone(model):
    assert svc._unsafe_to_disable_reasoning_when_price_routed(model) is False


# ---------------------------------------------------------------------------
# _use_enabled_false_reasoning_param
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('model', [
    'qwen/qwen3.7-plus',
    'QWEN/QWEN3.7-PLUS',
    'qwen/qwen-2.5-72b-instruct',
])
def test_use_enabled_false_reasoning_param_matches_qwen_family(model):
    assert svc._use_enabled_false_reasoning_param(model) is True


@pytest.mark.parametrize('model', [
    'google/gemini-3.5-flash-lite',
    'anthropic/claude-sonnet-5',
    'deepseek/deepseek-v4-flash',
    None,
    '',
])
def test_use_enabled_false_reasoning_param_leaves_other_models_alone(model):
    assert svc._use_enabled_false_reasoning_param(model) is False


# ---------------------------------------------------------------------------
# _is_reasoning_only_model
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('model', [
    'qwen/qwen3.8-max',
    'QWEN/QWEN3.8-MAX',
    'some-vendor/model-thinking',
    'some-vendor/model-reasoning',
])
def test_is_reasoning_only_model_matches_known_families(model):
    assert svc._is_reasoning_only_model(model) is True


@pytest.mark.parametrize('model', [
    'google/gemini-3.5-flash-lite',
    'qwen/qwen3.7-plus',
    'anthropic/claude-sonnet-5',
    'deepseek/deepseek-v4-flash',
    None,
    '',
])
def test_is_reasoning_only_model_does_not_flag_ordinary_models(model):
    assert svc._is_reasoning_only_model(model) is False


# ---------------------------------------------------------------------------
# Regression guard: no vocab_ladder task_name currently resolves to a
# reasoning-only model. Needs live Supabase credentials -- the prompt/model
# assignment lives in prompt_templates, not in code, so this can only check
# reality, not a frozen fixture, without risking silent staleness the moment
# a model is reassigned via the DB.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get('SUPABASE_URL'),
    reason='needs Supabase credentials; prompt_templates is the source of truth',
)
def test_no_active_vocab_ladder_model_resolves_to_a_reasoning_class_model():
    from services.supabase_factory import SupabaseFactory, get_supabase_admin

    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()

    resp = (
        db.table('prompt_templates')
        .select('task_name, language_id, model')
        .eq('is_active', True)
        .execute()
    )
    offending = [
        row for row in (resp.data or [])
        if (row.get('task_name') or '').startswith(('vocab_', 'ladder_'))
        and svc._is_reasoning_only_model(row.get('model'))
    ]
    assert not offending, (
        f'active vocab_ladder prompt row(s) resolve to a reasoning-only '
        f'model, which would silently break under disable_reasoning=True '
        f'if this gate is ever bypassed: {offending}'
    )
