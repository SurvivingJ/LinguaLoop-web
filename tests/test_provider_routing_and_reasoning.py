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
    """Despite the name (kept for history): the reasoning payload is an
    ADR-028 change scoped to vocab_ladder; other pipelines keep the
    pre-ADR-028 behaviour of sending no `reasoning` key."""
    client = _Client()
    _call(monkeypatch, client, pipeline='test_gen')

    assert 'reasoning' not in client.chat.completions.last_payload['extra_body']


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
    """LADDER_QWEN_REASONING=off selects the current (2026-10-03) cost-fix
    behaviour -- see the on/off tests further below for the default."""
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'off')
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
    existing to add it to. Requires LADDER_QWEN_REASONING=off; see the on/off
    tests further below for the default ('on')."""
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'off')
    monkeypatch.setenv('LLM_AB_NO_PRICE_ROUTING', '1')
    client = _Client()
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', pipeline='vocab_ladder')

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
    literal reused across calls for different models. Only happens under
    LADDER_QWEN_REASONING=off (the enabled:False path); under the 'on'
    default no provider mutation happens at all for a qwen call."""
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'off')
    client = _Client()
    shared_routing = {'sort': 'price'}
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', pipeline='vocab_ladder',
          provider_routing=shared_routing)

    assert shared_routing == {'sort': 'price'}
    extra_body = client.chat.completions.last_payload['extra_body']
    assert extra_body['provider'] == {'sort': 'price', 'require_parameters': True}


# ---------------------------------------------------------------------------
# LADDER_QWEN_REASONING (ADR-028 Phase-2 attribution flag, 2026-10-03)
# ---------------------------------------------------------------------------

def test_ladder_qwen_reasoning_defaults_to_budget(monkeypatch):
    # TASK-857 (2026-10-09): production default flipped on -> budget.
    monkeypatch.delenv('LADDER_QWEN_REASONING', raising=False)
    assert svc.ladder_qwen_reasoning_mode() == 'budget'


@pytest.mark.parametrize('value', ['off', 'OFF', 'Off', ' off '])
def test_ladder_qwen_reasoning_off_is_case_and_whitespace_insensitive(monkeypatch, value):
    monkeypatch.setenv('LADDER_QWEN_REASONING', value)
    assert svc.ladder_qwen_reasoning_mode() == 'off'


@pytest.mark.parametrize('value', ['on', 'ON', ' on '])
def test_ladder_qwen_reasoning_on_is_selectable_for_rollback(monkeypatch, value):
    monkeypatch.setenv('LADDER_QWEN_REASONING', value)
    assert svc.ladder_qwen_reasoning_mode() == 'on'


@pytest.mark.parametrize('value', ['banana', ''])
def test_ladder_qwen_reasoning_unknown_values_fall_back_to_default_budget(monkeypatch, value):
    monkeypatch.setenv('LADDER_QWEN_REASONING', value)
    assert svc.ladder_qwen_reasoning_mode() == 'budget'


def test_ladder_qwen_reasoning_on_skips_reasoning_param_entirely_for_qwen(monkeypatch):
    """The rollback value (LADDER_QWEN_REASONING=on): restores the Phase-1-measured state for a price-routed
    qwen vocab_ladder call -- no `reasoning` key sent at all (not
    `exclude: True`, which Phase 1's own 2026-09-27 finding showed
    reproducibly empties the response when combined with price routing --
    see `_unsafe_to_disable_reasoning_when_price_routed`'s docstring).
    `require_parameters` is also not added -- that only exists to support
    the `enabled: False` payload the 'off' mode sends."""
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'on')
    client = _Client()
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', pipeline='vocab_ladder')

    extra_body = client.chat.completions.last_payload['extra_body']
    assert 'reasoning' not in extra_body
    assert extra_body['provider'] == {'sort': 'price'}


@pytest.mark.parametrize('value', ['low', 'LOW', 'Low', ' low '])
def test_ladder_qwen_reasoning_low_is_case_and_whitespace_insensitive(monkeypatch, value):
    monkeypatch.setenv('LADDER_QWEN_REASONING', value)
    assert svc.ladder_qwen_reasoning_mode() == 'low'


@pytest.mark.parametrize('value', ['budget', 'BUDGET', 'Budget', ' budget '])
def test_ladder_qwen_reasoning_budget_is_case_and_whitespace_insensitive(monkeypatch, value):
    monkeypatch.setenv('LADDER_QWEN_REASONING', value)
    assert svc.ladder_qwen_reasoning_mode() == 'budget'


def test_ladder_qwen_reasoning_budget_tokens_defaults_to_1024(monkeypatch):
    monkeypatch.delenv('LADDER_QWEN_REASONING_BUDGET', raising=False)
    assert svc.ladder_qwen_reasoning_budget_tokens() == 1024


def test_ladder_qwen_reasoning_budget_tokens_reads_env(monkeypatch):
    monkeypatch.setenv('LADDER_QWEN_REASONING_BUDGET', '2048')
    assert svc.ladder_qwen_reasoning_budget_tokens() == 2048


@pytest.mark.parametrize('value', ['banana', '', '0', '-5', '  '])
def test_ladder_qwen_reasoning_budget_tokens_falls_back_on_bad_value(monkeypatch, value):
    monkeypatch.setenv('LADDER_QWEN_REASONING_BUDGET', value)
    assert svc.ladder_qwen_reasoning_budget_tokens() == 1024


# Per-language budget overrides (ADR-028 Outcome 2026-10-08).
def _clear_budget_env(monkeypatch):
    for n in ('LADDER_QWEN_REASONING_BUDGET', 'LADDER_QWEN_REASONING_BUDGET_ZH',
              'LADDER_QWEN_REASONING_BUDGET_JA', 'LADDER_QWEN_REASONING_BUDGET_EN'):
        monkeypatch.delenv(n, raising=False)


def test_budget_per_language_override_wins_over_global(monkeypatch):
    _clear_budget_env(monkeypatch)
    monkeypatch.setenv('LADDER_QWEN_REASONING_BUDGET', '1500')
    monkeypatch.setenv('LADDER_QWEN_REASONING_BUDGET_ZH', '2048')
    assert svc.ladder_qwen_reasoning_budget_tokens('zh') == 2048
    assert svc.ladder_qwen_reasoning_budget_tokens('ZH') == 2048
    assert svc.ladder_qwen_reasoning_budget_tokens('ja') == 1500
    assert svc.ladder_qwen_reasoning_budget_tokens(None) == 1500
    assert svc.ladder_qwen_reasoning_budget_tokens() == 1500


def test_budget_per_language_falls_back_to_default_1024(monkeypatch):
    _clear_budget_env(monkeypatch)
    assert svc.ladder_qwen_reasoning_budget_tokens('en') == 1024


@pytest.mark.parametrize('value', ['banana', '', '0', '-5'])
def test_budget_bad_per_language_value_falls_through_to_global(monkeypatch, value):
    _clear_budget_env(monkeypatch)
    monkeypatch.setenv('LADDER_QWEN_REASONING_BUDGET', '1200')
    monkeypatch.setenv('LADDER_QWEN_REASONING_BUDGET_JA', value)
    assert svc.ladder_qwen_reasoning_budget_tokens('ja') == 1200


def test_budget_mode_call_uses_language_code_override(monkeypatch):
    _clear_budget_env(monkeypatch)
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'budget')
    monkeypatch.setenv('LADDER_QWEN_REASONING_BUDGET_ZH', '2048')
    client = _Client()
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', pipeline='vocab_ladder',
          language_code='zh')
    assert client.chat.completions.last_payload['extra_body']['reasoning'] == {'max_tokens': 2048}

    client = _Client()
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', pipeline='vocab_ladder',
          language_code='ja')
    assert client.chat.completions.last_payload['extra_body']['reasoning'] == {'max_tokens': 1024}


def test_budget_env_alone_does_not_change_mode(monkeypatch):
    monkeypatch.delenv('LADDER_QWEN_REASONING', raising=False)
    monkeypatch.setenv('LADDER_QWEN_REASONING_BUDGET_ZH', '2048')
    assert svc.ladder_qwen_reasoning_mode() == 'budget'


def test_budget_per_language_production_defaults(monkeypatch):
    _clear_budget_env(monkeypatch)
    assert svc.ladder_qwen_reasoning_budget_tokens('ja') == 1024
    assert svc.ladder_qwen_reasoning_budget_tokens('en') == 1024
    assert svc.ladder_qwen_reasoning_budget_tokens('zh') == 2048
    assert svc.ladder_qwen_reasoning_budget_tokens('ZH') == 2048
    # No / unknown language -> safe 1024 fallback.
    assert svc.ladder_qwen_reasoning_budget_tokens(None) == 1024
    assert svc.ladder_qwen_reasoning_budget_tokens('xx') == 1024


def test_budget_env_overrides_beat_per_language_defaults(monkeypatch):
    _clear_budget_env(monkeypatch)
    monkeypatch.setenv('LADDER_QWEN_REASONING_BUDGET', '3000')
    assert svc.ladder_qwen_reasoning_budget_tokens('zh') == 3000
    monkeypatch.setenv('LADDER_QWEN_REASONING_BUDGET_ZH', '512')
    assert svc.ladder_qwen_reasoning_budget_tokens('zh') == 512


def test_default_call_sends_per_language_budget_and_bumps_max_tokens(monkeypatch):
    monkeypatch.delenv('LADDER_QWEN_REASONING', raising=False)
    _clear_budget_env(monkeypatch)
    client = _Client()
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', pipeline='vocab_ladder',
          max_tokens=250, language_code='zh')
    payload = client.chat.completions.last_payload
    assert payload['extra_body']['reasoning'] == {'max_tokens': 2048}
    assert payload['max_tokens'] == 250 + 2048


def test_rollback_env_on_restores_unbounded_reasoning(monkeypatch):
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'on')
    client = _Client()
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', pipeline='vocab_ladder',
          max_tokens=250, language_code='zh')
    payload = client.chat.completions.last_payload
    assert 'reasoning' not in payload['extra_body']
    assert payload['max_tokens'] == 250


def test_ladder_qwen_reasoning_low_sends_effort_low_for_a_price_routed_qwen_model(monkeypatch):
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'low')
    client = _Client()
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', pipeline='vocab_ladder')

    extra_body = client.chat.completions.last_payload['extra_body']
    assert extra_body['reasoning'] == {'effort': 'low'}
    assert extra_body['provider'] == {'sort': 'price', 'require_parameters': True}


def test_ladder_qwen_reasoning_budget_sends_max_tokens_for_a_price_routed_qwen_model(monkeypatch):
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'budget')
    monkeypatch.setenv('LADDER_QWEN_REASONING_BUDGET', '2048')
    client = _Client()
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', pipeline='vocab_ladder')

    extra_body = client.chat.completions.last_payload['extra_body']
    assert extra_body['reasoning'] == {'max_tokens': 2048}
    assert extra_body['provider'] == {'sort': 'price', 'require_parameters': True}


def test_ladder_qwen_reasoning_budget_defaults_to_1024_tokens(monkeypatch):
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'budget')
    monkeypatch.delenv('LADDER_QWEN_REASONING_BUDGET', raising=False)
    client = _Client()
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', pipeline='vocab_ladder')

    extra_body = client.chat.completions.last_payload['extra_body']
    assert extra_body['reasoning'] == {'max_tokens': 1024}
    assert extra_body['provider']['sort'] == 'price'


# ---------------------------------------------------------------------------
# armD incident (2026-10-05): a right-sized judge max_tokens (250-300) sits
# below the default 1024-token LADDER_QWEN_REASONING=budget reasoning budget,
# and OpenRouter 400s ("max_completion_tokens must be greater than
# thinking_budget") rather than truncating -- 160x ja + 226x zh across
# ladder_l1_distractor_judge / ladder_sentence_validity_judge /
# ladder_relation_judge, all failing open (safe_accept) instead of judging.
# `_make_one_call` now bumps the request's max_tokens to cover the reasoning
# budget whenever one is sent.
# ---------------------------------------------------------------------------

def test_budget_mode_bumps_max_tokens_above_the_reasoning_budget(monkeypatch):
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'budget')
    monkeypatch.setenv('LADDER_QWEN_REASONING_BUDGET', '1024')
    client = _Client()
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', pipeline='vocab_ladder',
          max_tokens=250)

    payload = client.chat.completions.last_payload
    assert payload['extra_body']['reasoning'] == {'max_tokens': 1024}
    # 250 (caller's output cap) + 1024 (reasoning budget) -- strictly greater
    # than the budget alone, so the provider's `max_completion_tokens >
    # thinking_budget` check can never fail.
    assert payload['max_tokens'] == 1274


def test_budget_mode_with_a_custom_budget_still_sums_correctly(monkeypatch):
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'budget')
    monkeypatch.setenv('LADDER_QWEN_REASONING_BUDGET', '2048')
    client = _Client()
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', pipeline='vocab_ladder',
          max_tokens=300)

    payload = client.chat.completions.last_payload
    assert payload['max_tokens'] == 2348


def test_budget_mode_leaves_max_tokens_alone_when_caller_sent_none(monkeypatch):
    """No output cap means nothing for the reasoning budget to collide with
    -- `max_tokens` must stay absent from the payload, not become the bare
    budget value."""
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'budget')
    client = _Client()
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', pipeline='vocab_ladder')

    payload = client.chat.completions.last_payload
    assert 'max_tokens' not in payload


def test_low_mode_does_not_touch_max_tokens(monkeypatch):
    """`effort: 'low'` has no `reasoning.max_tokens` key for this fix to key
    off -- OpenRouter converts effort to a max_tokens percentage itself, so
    the caller's cap must pass through unchanged."""
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'low')
    client = _Client()
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', pipeline='vocab_ladder',
          max_tokens=250)

    payload = client.chat.completions.last_payload
    assert payload['max_tokens'] == 250


def test_on_mode_does_not_touch_max_tokens(monkeypatch):
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'on')
    client = _Client()
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', pipeline='vocab_ladder',
          max_tokens=250)

    payload = client.chat.completions.last_payload
    assert payload['max_tokens'] == 250


def test_budget_bump_does_not_affect_non_qwen_models(monkeypatch):
    """Only the qwen `enabled_false`/budget path ever sets
    `reasoning.max_tokens` -- a non-qwen model's `exclude: True` payload has
    no such key, so its max_tokens must be untouched."""
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'budget')
    client = _Client()
    _call(monkeypatch, client, model='google/gemini-3.5-flash-lite',
          pipeline='vocab_ladder', max_tokens=250)

    payload = client.chat.completions.last_payload
    assert payload['max_tokens'] == 250
    assert payload['extra_body']['reasoning'] == {'exclude': True}


def test_ladder_qwen_reasoning_low_and_budget_do_not_affect_non_qwen_models(monkeypatch):
    for mode in ('low', 'budget'):
        monkeypatch.setenv('LADDER_QWEN_REASONING', mode)
        client = _Client()
        _call(monkeypatch, client, model='google/gemini-3.5-flash-lite',
              pipeline='vocab_ladder')

        extra_body = client.chat.completions.last_payload['extra_body']
        assert extra_body['reasoning'] == {'exclude': True}


def test_ladder_qwen_reasoning_on_does_not_affect_non_qwen_models(monkeypatch):
    """The flag is scoped to the qwen pattern -- a non-qwen model keeps
    getting `exclude: True` regardless of LADDER_QWEN_REASONING."""
    monkeypatch.delenv('LADDER_QWEN_REASONING', raising=False)
    client = _Client()
    _call(monkeypatch, client, model='google/gemini-3.5-flash-lite',
          pipeline='vocab_ladder')

    extra_body = client.chat.completions.last_payload['extra_body']
    assert extra_body['reasoning'] == {'exclude': True}


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


# ---------------------------------------------------------------------------
# 2026-10-04 armB_ja incident: `provider.require_parameters` + `reasoning:
# {'enabled': False}` 404'd ("no endpoints found ... Filter by Parameters")
# for cloze_distractor_judge/ja, whose prompt_templates row was pinned to a
# stale `qwen/qwen-2.5-72b-instruct` slug that still matched the `^qwen/`
# pattern but could not actually serve the reasoning override on either of
# its 2 OpenRouter endpoints. `_make_one_call` now retries once with the
# routing/reasoning overrides stripped instead of failing outright.
# ---------------------------------------------------------------------------

import httpx
from openai import NotFoundError


def _not_found(message: str) -> NotFoundError:
    req = httpx.Request('POST', 'https://openrouter.ai/api/v1/chat/completions')
    resp = httpx.Response(404, request=req, json={'error': {'message': message}})
    return NotFoundError(message, response=resp, body=None)


class _FlakyCompletions:
    """Raises `error` on the first call, then serves `response` normally."""

    def __init__(self, error: Exception, response):
        self._error = error
        self._response = response
        self.payloads: list[dict] = []
        self.calls = 0

    def create(self, **payload):
        self.payloads.append(payload)
        self.calls += 1
        if self.calls == 1:
            raise self._error
        return self._response


class _AlwaysFailCompletions:
    def __init__(self, error: Exception):
        self._error = error
        self.payloads: list[dict] = []

    def create(self, **payload):
        self.payloads.append(payload)
        raise self._error


def _flaky_client(error):
    client = _Client()
    client.chat.completions = _FlakyCompletions(error, _Response())
    return client


def _always_fail_client(error):
    client = _Client()
    client.chat.completions = _AlwaysFailCompletions(error)
    return client


def test_no_endpoints_404_retries_once_without_routing_overrides(monkeypatch):
    client = _flaky_client(_not_found(
        'No endpoints found that can handle the requested parameters.'
    ))
    result = _call(
        monkeypatch, client, model='qwen/qwen-2.5-72b-instruct',
        pipeline='vocab_ladder',
    )

    assert result == {'ok': True}
    assert client.chat.completions.calls == 2
    first, second = client.chat.completions.payloads
    # First attempt carried the normal vocab_ladder overrides...
    assert 'reasoning' in first['extra_body'] or 'provider' in first['extra_body']
    # ...the retry dropped both, rather than repeating the same request.
    assert 'reasoning' not in second['extra_body']
    assert 'provider' not in second['extra_body']
    # Unrelated extra_body fields (cost accounting) survive the strip.
    assert second['extra_body'].get('usage') == {'include': True}


def test_unrelated_404_is_not_retried(monkeypatch):
    """A 404 for a different reason (e.g. a genuinely delisted model) must
    propagate immediately -- stripping routing overrides would not fix it,
    and silently retrying would hide the real failure."""
    client = _always_fail_client(_not_found('The model does not exist.'))

    with pytest.raises(NotFoundError):
        _call(monkeypatch, client, pipeline='vocab_ladder')

    assert client.chat.completions.payloads  # only the one attempt was made
    assert len(client.chat.completions.payloads) == 1


def test_no_endpoints_404_without_routing_overrides_is_not_retried(monkeypatch):
    """When the call never sent reasoning/provider overrides in the first
    place, stripping them is a no-op -- retry would just 404 again, so the
    original error propagates instead of spending a second call."""
    client = _always_fail_client(_not_found(
        'No endpoints found that can handle the requested parameters.'
    ))

    with pytest.raises(NotFoundError):
        _call(
            monkeypatch, client, pipeline='test_gen',
            disable_reasoning=False,
        )

    assert len(client.chat.completions.payloads) == 1


# ---------------------------------------------------------------------------
# TASK-857 follow-up: LADDER_QWEN_REASONING modes are vocab_ladder-only
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('lang,expected', [('ja', 1024), ('en', 1024), ('zh', 2048)])
def test_ladder_qwen_call_gets_per_language_budget_payload(monkeypatch, lang, expected):
    monkeypatch.delenv('LADDER_QWEN_REASONING', raising=False)
    for k in ('LADDER_QWEN_REASONING_BUDGET', 'LADDER_QWEN_REASONING_BUDGET_' + lang.upper()):
        monkeypatch.delenv(k, raising=False)
    client = _Client()
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', pipeline='vocab_ladder',
          language_code=lang)
    extra_body = client.chat.completions.last_payload['extra_body']
    assert extra_body['reasoning'] == {'max_tokens': expected}
    assert extra_body['provider'] == {'sort': 'price', 'require_parameters': True}


@pytest.mark.parametrize('pipeline', ['test_gen', 'dual_translation', None])
@pytest.mark.parametrize('mode', [None, 'on', 'off', 'low', 'budget'])
def test_non_ladder_qwen_call_sends_no_reasoning_key(monkeypatch, pipeline, mode):
    """Pre-ADR-028 baseline (ffb0afe7): non-ladder calls send no `reasoning`
    key, no price routing, no require_parameters, whatever the ladder mode."""
    if mode is None:
        monkeypatch.delenv('LADDER_QWEN_REASONING', raising=False)
    else:
        monkeypatch.setenv('LADDER_QWEN_REASONING', mode)
    client = _Client()
    kwargs = {'pipeline': pipeline} if pipeline else {}
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', language_code='zh', **kwargs)
    extra_body = client.chat.completions.last_payload['extra_body']
    assert 'reasoning' not in extra_body
    assert 'provider' not in extra_body


def test_ladder_rollback_env_on_still_sends_no_reasoning_key(monkeypatch):
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'on')
    client = _Client()
    _call(monkeypatch, client, model='qwen/qwen3.7-plus', pipeline='vocab_ladder',
          language_code='zh')
    assert 'reasoning' not in client.chat.completions.last_payload['extra_body']
