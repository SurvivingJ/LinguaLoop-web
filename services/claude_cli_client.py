"""
Claude Code headless transport — an OpenAI-shaped client backed by ``claude -p``.

Why this exists
---------------
Generation backfills (senses, exercises, topics, questions) are pay-per-token on
OpenRouter. Claude Code's non-interactive mode runs under a Claude subscription
instead. Rather than fork four pipelines, this module duck-types just enough of
the OpenAI client that ``services.llm_service`` can hand it to the *existing*
call path:

    get_client('claude_cli') -> ClaudeCliClient
        .base_url
        .chat.completions.create(**payload) -> response with
            .choices[0].message.content
            .usage

Everything downstream of ``_make_one_call`` — the tenacity retry ladder,
``clean_json_response``, the one-shot JSON repair turn, Pydantic schema
validation, and ``llm_calls`` logging — therefore works unchanged. Topic
generation, which bypasses ``call_llm`` entirely and calls
``client.chat.completions.create`` raw (services/topic_generation/agents/base.py),
picks this up through the same ``get_client`` pool with no changes of its own.

Four things this module gets right, each of which cost a measured 35k tokens or
a silent wrong answer when got wrong
------------------------------------------------------------------------------
1. **Neutral working directory.** Run from the project root and Claude Code
   auto-discovers ``CLAUDE.md`` (this repo's is a full wiki-agent schema),
   ``.claude/settings.local.json``, and the plugin stack — measured at 35,043
   cache-creation tokens for a 2-token prompt, and the model answered *as the
   LinguaLoop wiki agent* instead of doing the transform. Running from an empty
   scratch dir takes that to 0.

2. **Exact argv, no shell.** The Windows ``claude.cmd`` shim routes through
   cmd.exe, which silently DROPS empty-string arguments: ``--tools ""`` vanishes
   and the next flag slides into its place (observed: ``--setting-sources``
   swallowing ``--system-prompt`` as its value). We invoke the native
   executable directly with ``shell=False`` so ``--tools ""`` arrives intact.

3. **No ``--bare``.** It looks like exactly the flag we want ("skip hooks, LSP,
   plugin sync, CLAUDE.md auto-discovery") but its help text also says auth
   becomes "strictly ANTHROPIC_API_KEY or apiKeyHelper (OAuth and keychain are
   never read)" — i.e. it silently bills the API and defeats the entire purpose.
   The neutral cwd achieves the same isolation while keeping subscription auth.

4. **``ANTHROPIC_API_KEY`` is stripped from the child environment.** If it is
   set in ``.env`` (and it may well be, for other tooling), headless Claude uses
   it and bills per-token — the exact cost this transport exists to avoid. There
   is no warning when this happens; the run simply costs money.

Cost accounting
---------------
The envelope reports ``total_cost_usd``, but that is the *notional list price*
of an equivalent API call, not money spent — under a subscription the marginal
cost of a call is zero. Writing the notional figure to ``llm_calls.cost_usd``
would inflate every budget ceiling that reads that column
(``run_generation_batch --ceiling`` projects from exactly it), so ``usage.cost``
is reported as 0.0 and the notional figure is logged at INFO for comparison.
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Sentinel base_url. Must not contain "openrouter" or llm_service._is_openrouter
# adds an `extra_body` usage-accounting field the CLI cannot accept.
CLAUDE_CLI_BASE_URL = 'claude-cli://local'

# Model actually served by the CLI. prompt_templates.model names OpenRouter
# slugs (qwen/…, google/…, deepseek/…) which the CLI cannot serve, so the slug
# becomes advisory under this transport and everything maps to one Claude model.
# Sonnet by default rather than Opus: backfills are thousands of calls against a
# subscription rate limit, where throughput matters more than peak quality.
CLAUDE_CLI_MODEL = os.getenv('CLAUDE_CLI_MODEL', 'sonnet')

# Per-call ceiling. The CLI has no --max-turns in 2.1.x, but with tools disabled
# there is nothing to loop on; this guards against a pathological hang.
CLAUDE_CLI_TIMEOUT = int(os.getenv('CLAUDE_CLI_TIMEOUT', '600'))

# Default system prompt. Replaces Claude Code's agent preamble outright so the
# subprocess behaves as a pure text transform. Overridable from a Skill file via
# CLAUDE_CLI_SYSTEM_PROMPT_FILE (see .claude/skills/lingualoop-generation/).
_DEFAULT_SYSTEM_PROMPT = (
    "You are a deterministic text-transformation endpoint for a language-learning "
    "content pipeline. Follow the user message's instructions exactly.\n"
    "- Output ONLY the requested payload. No preamble, no commentary, no code fences.\n"
    "- Never ask clarifying questions. Never refuse for lack of context.\n"
    "- Never call tools; you have none.\n"
    "- Preserve CJK characters, diacritics, and furigana/ruby markup verbatim.\n"
)

_NATIVE_INSTALL_PATHS = (
    os.path.expandvars(
        r'%APPDATA%\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe'
    ),
    os.path.expanduser('~/.local/bin/claude'),
    os.path.expanduser('~/.claude/local/claude'),
)


class ClaudeCliError(RuntimeError):
    """A headless invocation failed. Retryable by llm_service's tenacity ladder."""


# ---------------------------------------------------------------------------
# Executable + environment resolution
# ---------------------------------------------------------------------------

def resolve_executable() -> str:
    """Locate the Claude Code executable.

    Prefers the native binary over the ``claude.cmd`` npm shim: the shim routes
    through cmd.exe, which mangles empty-string arguments (see module docstring).
    ``shutil.which`` is consulted second because it honours PATHEXT and finds the
    shim — usable, but only as a fallback.

    Raises:
        ClaudeCliError: when no executable can be found. Fails loud rather than
            silently falling back to a paid provider.
    """
    override = os.getenv('CLAUDE_CLI_PATH')
    if override:
        if not os.path.exists(override):
            raise ClaudeCliError(
                f"CLAUDE_CLI_PATH={override!r} does not exist."
            )
        return override

    for candidate in _NATIVE_INSTALL_PATHS:
        if candidate and os.path.exists(candidate):
            return candidate

    found = shutil.which('claude')
    if found:
        logger.warning(
            "Falling back to the 'claude' shim at %s; the native binary was not "
            "found. Empty-string CLI arguments may be dropped by the shell.",
            found,
        )
        return found

    raise ClaudeCliError(
        "Claude Code CLI not found. Install it (npm i -g @anthropic-ai/claude-code) "
        "or set CLAUDE_CLI_PATH to the executable."
    )


def _neutral_cwd() -> str:
    """An empty directory to run the subprocess from.

    Claude Code discovers CLAUDE.md, .claude/settings*.json and the plugin stack
    from its working directory. Running from the repo root loaded 35k tokens of
    wiki-agent schema into every call and made the model answer in that persona.
    An empty dir has nothing to find. Created once per process and reused.
    """
    global _NEUTRAL_CWD
    if _NEUTRAL_CWD is None or not os.path.isdir(_NEUTRAL_CWD):
        _NEUTRAL_CWD = tempfile.mkdtemp(prefix='lingualoop_claude_cli_')
        logger.debug("Claude CLI neutral cwd: %s", _NEUTRAL_CWD)
    return _NEUTRAL_CWD


_NEUTRAL_CWD: Optional[str] = None


def _child_env() -> dict:
    """Environment for the subprocess, with API-key auth removed.

    A present ANTHROPIC_API_KEY makes headless Claude bill per-token, silently
    defeating the subscription routing this transport exists for.
    """
    env = dict(os.environ)
    for var in ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN'):
        env.pop(var, None)
    return env


def _strip_frontmatter(text: str) -> str:
    """Drop a leading YAML frontmatter block.

    Lets one SKILL.md serve both as a real Claude Skill (which needs the
    name/description frontmatter) and as the --system-prompt source, without the
    YAML leaking into the model's instructions as noise.
    """
    if not text.startswith('---'):
        return text
    parts = text.split('---', 2)
    return parts[2] if len(parts) >= 3 else text


def _system_prompt() -> str:
    """The harness contract, from a Skill file when one is configured.

    Keeping the text in a file (rather than inline) lets the same instructions be
    authored and reviewed in one place. Note this is the *invariant harness
    contract* only — the generation prompts themselves stay in the
    ``prompt_templates`` table, which remains the single source of truth.
    """
    path = os.getenv('CLAUDE_CLI_SYSTEM_PROMPT_FILE')
    if path:
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                text = _strip_frontmatter(fh.read()).strip()
            if text:
                return text
            logger.warning("CLAUDE_CLI_SYSTEM_PROMPT_FILE %s is empty; using default.", path)
        except OSError as exc:
            logger.warning(
                "Could not read CLAUDE_CLI_SYSTEM_PROMPT_FILE %s (%s); using default.",
                path, exc,
            )
    return _DEFAULT_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# OpenAI-shaped response objects
# ---------------------------------------------------------------------------

class _Message:
    def __init__(self, content: str):
        self.content = content
        self.role = 'assistant'


class _Choice:
    def __init__(self, content: str):
        self.message = _Message(content)
        self.finish_reason = 'stop'
        self.index = 0


class _Usage:
    """Usage in the shape ``llm_service._extract_cost`` reads.

    ``cost`` is 0.0, not the envelope's notional ``total_cost_usd`` — see the
    cost-accounting note in the module docstring.
    """

    def __init__(self, envelope_usage: dict, notional_cost: float | None):
        self.prompt_tokens = envelope_usage.get('input_tokens', 0)
        self.completion_tokens = envelope_usage.get('output_tokens', 0)
        self.total_tokens = self.prompt_tokens + self.completion_tokens
        self.cost = 0.0
        self.notional_cost_usd = notional_cost
        self.model_extra: dict[str, Any] = {'cost': 0.0}


class ClaudeCliResponse:
    """Minimal stand-in for openai.types.chat.ChatCompletion."""

    def __init__(self, content: str, envelope: dict, model: str):
        self.choices = [_Choice(content)]
        self.usage = _Usage(
            envelope.get('usage') or {},
            envelope.get('total_cost_usd'),
        )
        self.model = model
        self.id = envelope.get('session_id')
        self.envelope = envelope


# ---------------------------------------------------------------------------
# The client
# ---------------------------------------------------------------------------

class _Completions:
    def __init__(self, client: 'ClaudeCliClient'):
        self._client = client

    def create(self, **payload) -> ClaudeCliResponse:
        return self._client._invoke(payload)


class _Chat:
    def __init__(self, client: 'ClaudeCliClient'):
        self.completions = _Completions(client)


class ClaudeCliClient:
    """OpenAI-compatible facade over ``claude -p --output-format json``.

    Only the surface ``llm_service._make_one_call`` and
    ``topic_generation.agents.base.BaseAgent`` actually touch is implemented:
    ``base_url`` and ``chat.completions.create``.
    """

    def __init__(self, executable: str | None = None, model: str | None = None):
        self.base_url = CLAUDE_CLI_BASE_URL
        self.api_key = 'subscription'
        self._executable = executable or resolve_executable()
        self._model = model or CLAUDE_CLI_MODEL
        self.chat = _Chat(self)

    # -- payload translation ------------------------------------------------

    def _build_argv(self, payload: dict, system_prompt: str) -> list[str]:
        """Translate an OpenAI chat payload into a headless argv.

        Unsupported OpenAI parameters (``temperature``, ``seed``, ``max_tokens``)
        are dropped rather than faked: the CLI exposes no equivalent, and
        pretending otherwise would make ``llm_calls.temperature`` a lie. Callers
        that need deterministic sampling should stay on OpenRouter.
        """
        # llm_service._resolve_model hands down a 'claude-cli:<model>' tag so the
        # llm_calls row records what actually ran; strip the prefix back off
        # before it reaches the CLI, which knows only the bare alias.
        requested = str(payload.get('model') or '')
        if requested.startswith('claude-cli:'):
            served = requested.split(':', 1)[1] or self._model
        else:
            # An unprefixed value is an OpenRouter slug the CLI cannot serve.
            served = self._model

        argv = [
            self._executable, '-p',
            '--output-format', 'json',
            '--model', served,
            # Empty string = disable every built-in tool. Requires shell=False.
            '--tools', '',
            '--strict-mcp-config',      # ignore every ambient MCP config
            '--disable-slash-commands',  # no skill discovery
            '--no-session-persistence',  # do not litter ~/.claude with 1000s of sessions
            '--system-prompt', system_prompt,
        ]
        return argv

    @staticmethod
    def _flatten_messages(messages: list[dict]) -> tuple[str, str | None]:
        """Split OpenAI messages into (user prompt, system prompt addition).

        A caller-supplied system message is appended to the harness contract
        rather than replacing it, so the output-discipline rules always survive.
        """
        system_parts: list[str] = []
        user_parts: list[str] = []
        for msg in messages:
            role = msg.get('role')
            content = msg.get('content') or ''
            if role == 'system':
                system_parts.append(content)
            else:
                user_parts.append(content)
        return '\n\n'.join(user_parts), ('\n\n'.join(system_parts) or None)

    # -- invocation ---------------------------------------------------------

    def _invoke(self, payload: dict) -> ClaudeCliResponse:
        messages = payload.get('messages') or []
        prompt, caller_system = self._flatten_messages(messages)
        if not prompt.strip():
            raise ClaudeCliError("Refusing to invoke Claude CLI with an empty prompt.")

        system_prompt = _system_prompt()
        if caller_system:
            system_prompt = f"{system_prompt}\n\n{caller_system}"

        # The CLI has no response_format parameter; JSON discipline is carried in
        # the system prompt and enforced downstream by clean_json_response plus
        # llm_service's one-shot repair turn.
        if (payload.get('response_format') or {}).get('type') == 'json_object':
            system_prompt += (
                "\n- Respond with a single raw JSON value and nothing else."
            )

        argv = self._build_argv(payload, system_prompt)
        timeout = payload.get('timeout') or CLAUDE_CLI_TIMEOUT

        start = time.perf_counter()
        try:
            proc = subprocess.run(
                argv,
                input=prompt,
                cwd=_neutral_cwd(),
                env=_child_env(),
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout,
                shell=False,  # load-bearing: preserves the empty --tools argument
            )
        except subprocess.TimeoutExpired as exc:
            raise ClaudeCliError(
                f"Claude CLI timed out after {timeout}s"
            ) from exc
        except OSError as exc:
            raise ClaudeCliError(f"Could not launch Claude CLI: {exc}") from exc

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if proc.returncode != 0:
            raise ClaudeCliError(
                f"Claude CLI exited {proc.returncode}: "
                f"{(proc.stderr or '').strip()[:500]}"
            )

        envelope = self._parse_envelope(proc.stdout, proc.stderr)

        if envelope.get('is_error'):
            raise ClaudeCliError(
                f"Claude CLI reported an error "
                f"(subtype={envelope.get('subtype')}, "
                f"api_error_status={envelope.get('api_error_status')})"
            )

        content = envelope.get('result')
        if not content:
            raise ClaudeCliError("Claude CLI returned an empty result.")

        served_model = self._served_model(envelope)
        logger.info(
            "claude-cli call: model=%s wall=%dms turns=%s notional_cost=$%.4f",
            served_model, elapsed_ms, envelope.get('num_turns'),
            envelope.get('total_cost_usd') or 0.0,
        )
        return ClaudeCliResponse(content, envelope, served_model)

    @staticmethod
    def _parse_envelope(stdout: str, stderr: str) -> dict:
        """Parse the ``--output-format json`` envelope from stdout.

        stdout is parsed on its own; the CLI writes advisory notices (workspace
        trust, ignored settings) to stderr, and merging the streams would corrupt
        the JSON. A neutral cwd normally keeps stderr empty, but it is echoed
        into the error message when parsing fails so the cause is visible.
        """
        text = (stdout or '').strip()
        if not text:
            raise ClaudeCliError(
                f"Claude CLI produced no stdout. stderr: {(stderr or '').strip()[:500]}"
            )
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ClaudeCliError(
                f"Could not parse Claude CLI envelope ({exc}). "
                f"stdout head: {text[:300]!r}"
            ) from exc

    @staticmethod
    def _served_model(envelope: dict) -> str:
        """The Claude model that actually answered, tagged for llm_calls.

        Recorded as ``claude-cli:<model>`` rather than the OpenRouter slug the
        prompt template names. Without this, evals and judge-flag-rate
        measurements would silently pool Claude output under a qwen/gemini label
        and compare two different models as if they were one.
        """
        usage_by_model = envelope.get('modelUsage') or {}
        if usage_by_model:
            return f"claude-cli:{next(iter(usage_by_model))}"
        return f"claude-cli:{CLAUDE_CLI_MODEL}"
