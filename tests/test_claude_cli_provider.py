"""
Headless Claude Code transport + multi-item prompt batching.

Why this file exists
--------------------
Both features fail *silently* when they fail. A dropped CLI argument still
returns a valid-looking answer (from a differently-configured model); a truncated
batch response looks like "the model chose to skip those words". The tests below
pin the specific silent failures found while building it:

* ``--tools ""`` being swallowed by the Windows cmd.exe shim, which shifted every
  later flag by one and made ``--setting-sources`` eat ``--system-prompt``.
* Running from the repo root, where CLAUDE.md auto-discovery loaded 35k tokens
  into every call and the model answered as the project's wiki agent.
* ``ANTHROPIC_API_KEY`` leaking into the child environment, which silently bills
  the API — the exact cost this transport exists to avoid.
* Logging the OpenRouter slug from prompt_templates as the model that answered,
  which would pool Claude output under a qwen/gemini label in every eval.
* A batch losing all N items because one was malformed.
"""

import json
import os
import subprocess
from unittest.mock import patch

import pytest

from services import claude_cli_client as cli
from services.batch_prompting import (
    build_batch_prompt,
    chunked,
    parse_batch_response,
    run_batched,
)


# ---------------------------------------------------------------------------
# Doubles
# ---------------------------------------------------------------------------

def _envelope(result='{"ok": true}', is_error=False, **extra):
    env = {
        'type': 'result',
        'subtype': 'success',
        'is_error': is_error,
        'result': result,
        'session_id': 'sess-1',
        'total_cost_usd': 0.0147,
        'num_turns': 1,
        'usage': {'input_tokens': 10, 'output_tokens': 20},
        'modelUsage': {'claude-sonnet-5': {}},
    }
    env.update(extra)
    return env


class _Completed:
    def __init__(self, stdout, returncode=0, stderr=''):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


@pytest.fixture
def client():
    with patch.object(cli, 'resolve_executable', return_value=r'C:\fake\claude.exe'):
        yield cli.ClaudeCliClient()


def _run_capture(client, payload, stdout=None, **run_kwargs):
    """Invoke the client, returning (response_or_exc, captured subprocess kwargs)."""
    captured = {}

    def fake_run(argv, **kwargs):
        captured['argv'] = argv
        captured.update(kwargs)
        return _Completed(stdout if stdout is not None else json.dumps(_envelope()),
                          **run_kwargs)

    with patch.object(subprocess, 'run', side_effect=fake_run):
        return client.chat.completions.create(**payload), captured


# ---------------------------------------------------------------------------
# Transport: argv construction
# ---------------------------------------------------------------------------

def test_empty_tools_argument_survives_as_its_own_argv_entry(client):
    """`--tools ""` must reach the process as a real empty argument.

    Through cmd.exe the empty string is dropped and the next flag slides into its
    place — observed live as `--setting-sources` consuming `--system-prompt` as
    its value. A list argv with shell=False is the only thing that preserves it.
    """
    _, captured = _run_capture(client, {'messages': [{'role': 'user', 'content': 'hi'}]})
    argv = captured['argv']

    assert '--tools' in argv
    assert argv[argv.index('--tools') + 1] == '', (
        "the empty --tools value was dropped; every later flag is now shifted"
    )
    assert captured['shell'] is False, "shell=True reintroduces cmd.exe arg mangling"


def test_runs_from_a_neutral_directory_not_the_repo(client):
    """CLAUDE.md auto-discovery is cwd-driven; the repo root costs 35k tokens/call."""
    _, captured = _run_capture(client, {'messages': [{'role': 'user', 'content': 'hi'}]})

    cwd = captured['cwd']
    assert cwd and os.path.isdir(cwd)
    assert 'LinguaLoop' not in cwd, (
        "running from the project tree loads CLAUDE.md into every call"
    )


def test_api_key_is_stripped_from_the_child_environment(client):
    """A present ANTHROPIC_API_KEY makes headless Claude bill per token."""
    with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'sk-ant-should-not-leak'}):
        _, captured = _run_capture(client, {'messages': [{'role': 'user', 'content': 'hi'}]})

    assert 'ANTHROPIC_API_KEY' not in captured['env']


def test_prompt_goes_over_stdin_never_argv(client):
    """Windows caps a command line near 32k; CJK prompts also mangle through argv."""
    prompt = '\u6614' * 5000
    _, captured = _run_capture(client, {'messages': [{'role': 'user', 'content': prompt}]})

    assert captured['input'] == prompt
    assert captured['encoding'] == 'utf-8'
    assert not any(len(str(a)) > 10000 for a in captured['argv'])


def test_openrouter_slug_is_replaced_by_the_model_that_actually_runs(client):
    """The CLI serves Claude only; the template's slug cannot be honoured."""
    _, captured = _run_capture(client, {
        'model': 'qwen/qwen3.7-plus',
        'messages': [{'role': 'user', 'content': 'hi'}],
    })
    served = captured['argv'][captured['argv'].index('--model') + 1]

    assert served == cli.CLAUDE_CLI_MODEL
    assert 'qwen' not in served


def test_claude_cli_prefix_is_stripped_before_reaching_the_cli(client):
    """llm_service hands down 'claude-cli:<model>' for honest llm_calls logging."""
    _, captured = _run_capture(client, {
        'model': 'claude-cli:opus',
        'messages': [{'role': 'user', 'content': 'hi'}],
    })

    assert captured['argv'][captured['argv'].index('--model') + 1] == 'opus'


def test_system_message_is_appended_to_the_harness_contract(client):
    """A caller's system message must not displace the output-discipline rules."""
    _, captured = _run_capture(client, {'messages': [
        {'role': 'system', 'content': 'CALLER_SYSTEM_MARKER'},
        {'role': 'user', 'content': 'hi'},
    ]})
    system = captured['argv'][captured['argv'].index('--system-prompt') + 1]

    assert 'CALLER_SYSTEM_MARKER' in system
    assert 'no code fences' in system.lower() or 'No code fences' in system


# ---------------------------------------------------------------------------
# Transport: response handling
# ---------------------------------------------------------------------------

def test_result_is_exposed_in_the_openai_response_shape(client):
    resp, _ = _run_capture(
        client, {'messages': [{'role': 'user', 'content': 'hi'}]},
        stdout=json.dumps(_envelope(result='{"lemma": "\u6614"}')),
    )

    assert resp.choices[0].message.content == '{"lemma": "\u6614"}'


def test_cost_is_reported_as_zero_not_the_notional_list_price(client):
    """total_cost_usd is what an API call *would* have cost, not money spent.

    Writing it to llm_calls.cost_usd would inflate every budget ceiling that
    reads that column (run_generation_batch --ceiling projects from it).
    """
    resp, _ = _run_capture(client, {'messages': [{'role': 'user', 'content': 'hi'}]})

    assert resp.usage.cost == 0.0
    assert resp.usage.model_extra['cost'] == 0.0
    assert resp.usage.notional_cost_usd == pytest.approx(0.0147)


def test_envelope_error_flag_raises(client):
    with pytest.raises(cli.ClaudeCliError):
        _run_capture(
            client, {'messages': [{'role': 'user', 'content': 'hi'}]},
            stdout=json.dumps(_envelope(is_error=True, subtype='error_during_execution')),
        )


def test_nonzero_exit_raises_with_stderr_context(client):
    with pytest.raises(cli.ClaudeCliError, match='boom'):
        _run_capture(
            client, {'messages': [{'role': 'user', 'content': 'hi'}]},
            stdout='', returncode=2, stderr='boom',
        )


def test_unparseable_stdout_raises_rather_than_returning_nothing(client):
    with pytest.raises(cli.ClaudeCliError, match='envelope'):
        _run_capture(
            client, {'messages': [{'role': 'user', 'content': 'hi'}]},
            stdout='not json at all',
        )


def test_empty_prompt_is_refused_before_spawning_a_process(client):
    with pytest.raises(cli.ClaudeCliError, match='empty prompt'):
        client.chat.completions.create(messages=[{'role': 'user', 'content': '   '}])


def test_cli_errors_are_retryable_by_llm_service():
    """The tenacity ladder must cover subprocess faults like it covers HTTP ones."""
    from services.llm_service import _retryable_types
    assert cli.ClaudeCliError in _retryable_types()


# ---------------------------------------------------------------------------
# llm_service wiring
# ---------------------------------------------------------------------------

def test_provider_resolves_to_a_non_openrouter_sentinel():
    """_is_openrouter keys off base_url; a match would add an unsupported field."""
    from services.llm_service import _resolve_provider, _is_openrouter

    base_url, _ = _resolve_provider('claude_cli')
    assert 'openrouter' not in base_url.lower()

    class _Fake:
        pass
    fake = _Fake()
    fake.base_url = base_url
    assert _is_openrouter(fake) is False


def test_resolved_model_is_tagged_so_evals_can_separate_transports():
    from services.llm_service import _resolve_model

    tag = _resolve_model('google/gemini-3.5-flash-lite', None, 'claude_cli')
    assert tag.startswith('claude-cli:')
    assert 'gemini' not in tag


def test_unknown_provider_still_fails_loudly():
    from services.llm_service import _resolve_provider
    with pytest.raises(ValueError, match='claude_cli'):
        _resolve_provider('not-a-provider')


# ---------------------------------------------------------------------------
# Batching
# ---------------------------------------------------------------------------

def test_chunked_covers_every_item_exactly_once():
    items = list(range(205))
    chunks = list(chunked(items, 100))

    assert [len(c) for c in chunks] == [100, 100, 5]
    assert [x for c in chunks for x in c] == items


def test_batch_prompt_labels_items_and_states_the_expected_count():
    prompt = build_batch_prompt(['define A', 'define B', 'define C'])

    assert '### item_1' in prompt and '### item_3' in prompt
    assert 'item_1' in prompt and 'item_3' in prompt
    assert 'define B' in prompt
    assert '3' in prompt


def test_batch_response_parsing_tolerates_key_spelling_variants():
    payloads, failed = parse_batch_response(
        {'item_1': {'a': 1}, 'ITEM 2': {'a': 2}, '3': {'a': 3}}, 3
    )

    assert set(payloads) == {1, 2, 3}
    assert failed == []


def test_null_and_missing_items_are_reported_not_silently_dropped():
    """The caller must learn which rows still need work."""
    payloads, failed = parse_batch_response({'item_1': {'a': 1}, 'item_2': None}, 4)

    assert set(payloads) == {1}
    assert failed == [2, 3, 4]


def test_out_of_range_keys_are_ignored():
    payloads, _ = parse_batch_response({'item_1': {'a': 1}, 'item_99': {'a': 9}}, 2)
    assert set(payloads) == {1}


def test_non_dict_response_fails_the_whole_batch_rather_than_crashing():
    payloads, failed = parse_batch_response(['not', 'an', 'object'], 3)
    assert payloads == {}
    assert failed == [1, 2, 3]


def test_one_bad_item_does_not_lose_the_rest_of_the_batch():
    """The core batching guarantee: blast radius is the item, not the batch."""
    calls = []

    def call(prompt):
        calls.append(prompt)
        if '### item_' in prompt:  # the 4-item batch: item 3 comes back null
            return {'item_1': {'v': 'a'}, 'item_2': {'v': 'b'},
                    'item_3': None, 'item_4': {'v': 'd'}}
        return {'v': 'recovered'}  # the single-item retry

    results = run_batched(
        ['a', 'b', 'c', 'd'],
        render=lambda x: f'define {x}',
        call=call,
        batch_size=4,
    )

    assert results[0] == {'v': 'a'}
    assert results[1] == {'v': 'b'}
    assert results[3] == {'v': 'd'}
    assert results[2] == {'v': 'recovered'}, "the failed item was never retried"
    assert len(calls) > 1


def test_a_whole_batch_failing_falls_back_to_smaller_batches():
    attempts = {'n': 0}

    def call(prompt):
        attempts['n'] += 1
        if attempts['n'] == 1:
            raise RuntimeError("model returned garbage")
        return {f'item_{i}': {'v': i} for i in range(1, 5)}

    results = run_batched(
        list('abcd'), render=lambda x: x, call=call, batch_size=4,
    )

    assert len(results) == 4, "a single bad roll should not lose the batch"


def test_validation_rejects_are_retried_like_missing_items():
    seen = {'n': 0}

    def call(prompt):
        seen['n'] += 1
        if seen['n'] == 1:
            return {'item_1': {'bad': True}, 'item_2': {'good': True}}
        return {'good': True}

    results = run_batched(
        ['x', 'y'],
        render=lambda v: v,
        call=call,
        batch_size=2,
        validate=lambda p: p if p.get('good') else None,
    )

    assert results[0] == {'good': True}
    assert results[1] == {'good': True}


def test_unrenderable_items_do_not_shift_other_items_positions():
    """A dropped item must not silently reassign another item's answer."""
    def call(prompt):
        return {'item_1': {'for': 'a'}, 'item_2': {'for': 'c'}}

    results = run_batched(
        ['a', 'b', 'c'],
        render=lambda x: None if x == 'b' else f'define {x}',
        call=call,
        batch_size=10,
    )

    assert results[0] == {'for': 'a'}
    assert results[2] == {'for': 'c'}
    assert 1 not in results


def test_batch_size_of_one_sends_no_envelope():
    """A batch of one must be byte-identical to the unbatched pipeline."""
    seen = []
    run_batched(['a'], render=lambda x: 'define a', call=lambda p: seen.append(p) or {'v': 1},
                batch_size=1)

    assert seen == ['define a']
    assert '### item_' not in seen[0]


def _count_items(prompt: str) -> int:
    """Count real item headers.

    Counting the substring '### item_' would also match the contract's own
    description of the header format, giving N+1.
    """
    import re
    return len(re.findall(r'^### item_\d+$', prompt, re.MULTILINE))


def test_batch_size_is_capped():
    from services.batch_prompting import MAX_BATCH_SIZE
    sizes = []

    def call(prompt):
        n = _count_items(prompt)
        sizes.append(n)
        return {f'item_{i}': {'v': i} for i in range(1, n + 1)}

    run_batched(list(range(MAX_BATCH_SIZE + 50)),
                render=lambda x: f'i{x}', call=call, batch_size=99999)

    assert max(sizes) <= MAX_BATCH_SIZE
    assert sum(sizes) == MAX_BATCH_SIZE + 50, "every item must still be sent"
