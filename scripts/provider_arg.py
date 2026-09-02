"""Shared ``--provider`` flag for generation/backfill CLIs.

Routes a whole run to either OpenRouter (pay-per-token, the default) or the
headless Claude Code transport (subscription-billed — services/claude_cli_client.py).

Kept in one place because the switch has three parts that are easy to get partly
right: setting the process default, warning about the model-slug semantics, and
tightening concurrency. A script that sets only the first appears to work and
then quietly saturates the subscription rate limit.

Usage:
    from scripts.provider_arg import add_provider_arg, apply_provider

    add_provider_arg(parser)
    args = parser.parse_args()
    apply_provider(args.provider)
"""

import logging

logger = logging.getLogger(__name__)

# CLI spelling -> llm_service provider name. The CLI uses a hyphen because that
# is how every other flag value in these scripts reads; the service uses an
# underscore because that is a Python-side identifier.
_PROVIDER_ALIASES = {
    'openrouter': 'openrouter',
    'claude-cli': 'claude_cli',
    'claude_cli': 'claude_cli',
    'ollama': 'ollama',
}

# Concurrency ceiling for the CLI transport. Each call is a process spawn against
# a subscription rate limit, not an HTTP request against a metered API — the
# hosted-provider default of 5+ workers trips limits rather than going faster.
CLAUDE_CLI_MAX_CONCURRENCY = 2


def add_provider_arg(parser) -> None:
    """Add ``--provider`` to an argparse parser."""
    parser.add_argument(
        '--provider',
        default='openrouter',
        choices=['openrouter', 'claude-cli', 'ollama'],
        help=(
            'LLM transport. "openrouter" (default) bills per token; '
            '"claude-cli" runs through Claude Code headless mode under your '
            'Claude subscription.'
        ),
    )


def apply_provider(provider: str) -> str:
    """Set the process-wide provider and warn about CLI-specific semantics.

    Returns the resolved llm_service provider name.
    """
    from services.llm_service import set_default_provider

    resolved = _PROVIDER_ALIASES.get(provider)
    if resolved is None:
        raise ValueError(f"Unknown --provider {provider!r}")

    set_default_provider(resolved)

    if resolved == 'claude_cli':
        from services.claude_cli_client import CLAUDE_CLI_MODEL, resolve_executable
        # Probe up front. Without this a missing CLI surfaces as a failure on the
        # first row rather than before the run starts.
        exe = resolve_executable()
        logger.warning(
            "Provider=claude-cli: every prompt_templates model slug is IGNORED; "
            "all calls are served by Claude '%s' via %s. llm_calls.model is "
            "logged as 'claude-cli:<model>' so this run is distinguishable from "
            "OpenRouter runs in evals.",
            CLAUDE_CLI_MODEL, exe,
        )
    return resolved


def clamp_concurrency(provider: str, requested: int) -> int:
    """Lower a hosted-provider worker count to something a subscription tolerates."""
    if _PROVIDER_ALIASES.get(provider) != 'claude_cli':
        return requested
    if requested > CLAUDE_CLI_MAX_CONCURRENCY:
        logger.warning(
            "Reducing concurrency %d -> %d for the claude-cli transport "
            "(process spawn + subscription rate limits).",
            requested, CLAUDE_CLI_MAX_CONCURRENCY,
        )
        return CLAUDE_CLI_MAX_CONCURRENCY
    return requested
