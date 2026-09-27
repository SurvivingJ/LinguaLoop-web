# services/vocabulary_ladder/bundle/flags.py
"""``VOCAB_LADDER_BUNDLE_MODE`` — the Phase 2 call-collapse feature flag.

Three values, per `migrations/exercise_gen_bundle_prompts_draft.sql`'s
header:

    "off"    (default) — current per-generator/per-judge behaviour, unchanged.
                          The bundle prompt rows are never fetched, even once
                          they exist and are ``is_active``.
    "shadow"           — run the bundle path ALONGSIDE the legacy path, but
                          only ever store/serve the legacy result. The bundle
                          call still happens (so it costs real money) purely
                          to compare outputs/cost on real traffic before the
                          collapse is trusted.
    "on"               — the bundle path is authoritative; the legacy
                          per-generator/per-judge calls are only made as the
                          documented partial-failure fallback.

Read fresh via ``os.getenv`` on every call — NOT cached at import time — so
an operator can flip it between batch runs without a redeploy (the same
pattern ``services.llm_service.set_default_provider`` already uses for
``LLM_DEFAULT_PROVIDER``).
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

ENV_VAR = 'VOCAB_LADDER_BUNDLE_MODE'

MODE_OFF = 'off'
MODE_SHADOW = 'shadow'
MODE_ON = 'on'

_VALID_MODES = frozenset({MODE_OFF, MODE_SHADOW, MODE_ON})


def bundle_mode() -> str:
    """The current mode: one of 'off' | 'shadow' | 'on'.

    An unrecognised value (typo, stale deploy) falls back to 'off' rather
    than raising or silently picking 'on' — a misconfigured flag must never
    turn on an unvalidated call-collapse path by accident. Logged once per
    distinct bad value would require module-level state we deliberately don't
    keep (this function must stay a pure, uncached env read), so it logs on
    every call — acceptable, since this is checked once per sense generation,
    not in a hot loop.
    """
    raw = (os.getenv(ENV_VAR) or MODE_OFF).strip().lower()
    if raw not in _VALID_MODES:
        logger.warning(
            "%s=%r is not one of %s — treating as %r",
            ENV_VAR, raw, sorted(_VALID_MODES), MODE_OFF,
        )
        return MODE_OFF
    return raw


def bundle_enabled() -> bool:
    """True when the bundle generation/judge path should run at all (shadow or on)."""
    return bundle_mode() in (MODE_SHADOW, MODE_ON)


def bundle_authoritative() -> bool:
    """True when the bundle path's output should actually be stored/served."""
    return bundle_mode() == MODE_ON
