"""Model router for the dual-translation grading cascade (TASK-600).

Maps named grading tiers (tier1/tier2/tier3) to OpenRouter slugs. The
mapping is never a code constant — it is read from `prompt_templates`,
keyed by `task_name` (the tier) + `language_id` (the L2 being graded), via
the same `get_template_config` helper exercise-gen and the ladder judges
use (services.prompt_service). EN content resolves to a Gemini-flash slug;
ZH/JA resolve to a Qwen slug — that split lives entirely in the seed data
(migrations/dual_translation_router_seed.sql), not in this module.

Before a resolved slug is handed to the caller, it is re-verified against
OpenRouter's live model list (services.model_arena.pricing.fetch_model_list
— the same fetcher/cache the pricing module already maintains, so this adds
no second HTTP client). This repo has been bitten twice by OpenRouter
delisting a configured slug out from under a live pipeline (qwen/qwen-max,
google/gemini-flash-1.5 — see memory `prompt-template-model-slug-rot`), so a
slug missing from that list is treated the same as a 404 from the model
itself: log it and fall open to the next cheaper tier rather than hard-fail
the learner's submission.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from services.model_arena.pricing import fetch_model_list
from services.prompt_service import get_template_config

logger = logging.getLogger(__name__)

PIPELINE = 'dual_translation'

# Cheap -> expensive. Tier 0 (the deterministic diff pre-pass, no model call
# at all — services.dual_translation.tier0, TASK-605) sits below 'tier1' and
# is never reached through this router; it's where the cascade lands when
# even the cheapest paid tier has nothing usable.
TIER_ORDER: list[str] = ['tier1', 'tier2', 'tier3']

# prompt_templates.task_name per tier. The row is additionally keyed by
# language_id (1=ZH, 2=EN, 3=JA), which is how EN ends up on a Gemini-flash
# slug while ZH/JA end up on a Qwen slug without this module knowing it.
TASK_NAME_BY_TIER: dict[str, str] = {
    'tier1': 'dual_translation_tier1',
    'tier2': 'dual_translation_tier2',
    'tier3': 'dual_translation_tier3',
}

_cfg_cache: dict[tuple[str, int], dict] = {}  # (tier, language_id) -> prompt_templates row


@dataclass
class ResolvedRoute:
    """What grading actually used for one cascade step — feeds straight
    into `dt_grade.grader_trace.slugs[]` (the slug actually called, not
    necessarily the one configured for `requested_tier`)."""

    requested_tier: str
    used_tier: str
    slug: str | None
    provider: str = 'openrouter'
    fell_open: bool = False
    reason: str | None = None

    def as_trace_entry(self) -> dict:
        """Shape for one element of `grader_trace.slugs[]`."""
        return {
            'requested_tier': self.requested_tier,
            'tier': self.used_tier,
            'slug': self.slug,
            'fell_open': self.fell_open,
        }


def resolve_tier(db, tier: str, language_id: int, *, verify: bool = True) -> ResolvedRoute:
    """Resolve `tier` to a verified OpenRouter slug for this L2 language.

    Walks the ladder from `tier` down toward 'tier1' if a configured slug is
    missing from `prompt_templates` or has been delisted from OpenRouter,
    logging each fall-open. If even 'tier1' is unusable, returns
    `slug=None` / `used_tier='tier0'` so the caller can fail open to Tier 0
    deterministic marks (the cascade's existing fail-open contract) instead
    of hard-failing the submission.
    """
    if tier not in TIER_ORDER:
        raise ValueError(f"Unknown grading tier {tier!r}; expected one of {TIER_ORDER}")

    start_idx = TIER_ORDER.index(tier)
    for idx in range(start_idx, -1, -1):
        candidate_tier = TIER_ORDER[idx]
        try:
            cfg = _load_cfg(db, candidate_tier, language_id)
        except Exception as exc:
            logger.warning(
                "dual_translation.router: no usable prompt_templates row for "
                "tier=%s lang=%d: %s", candidate_tier, language_id, exc,
            )
            continue

        slug = cfg['model']
        if not verify or _slug_is_listed(slug):
            return ResolvedRoute(
                requested_tier=tier,
                used_tier=candidate_tier,
                slug=slug,
                provider=cfg.get('provider', 'openrouter'),
                fell_open=(candidate_tier != tier),
                reason=None if candidate_tier == tier else f"{tier} slug unavailable",
            )

        logger.warning(
            "dual_translation.router: slug %r for tier=%s lang=%d not found on "
            "OpenRouter's live model list (delisted?); falling open",
            slug, candidate_tier, language_id,
        )

    logger.error(
        "dual_translation.router: every tier from %s down to tier1 is unresolved "
        "for lang=%d; caller must fail open to Tier 0 marks", tier, language_id,
    )
    return ResolvedRoute(
        requested_tier=tier,
        used_tier='tier0',
        slug=None,
        fell_open=True,
        reason='no usable tier; fail open to Tier 0 marks',
    )


def clear_caches() -> None:
    """Test/ops hook: drop the cached prompt_templates rows so the next
    `resolve_tier` call re-reads the DB (e.g. after an operator edits a slug)."""
    _cfg_cache.clear()


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _load_cfg(db, tier: str, language_id: int) -> dict:
    key = (tier, language_id)
    if key not in _cfg_cache:
        task_name = TASK_NAME_BY_TIER[tier]
        _cfg_cache[key] = get_template_config(db, task_name, language_id)
    return _cfg_cache[key]


def _slug_is_listed(slug: str) -> bool:
    """True if `slug` appears in OpenRouter's current /models list.

    `fetch_model_list` keeps its own 1-hour cache (services.model_arena.pricing),
    so this is at most one HTTP round-trip per hour, not per grading call. If
    the list fetch itself fails (network/API outage), assume the slug is
    still valid rather than falling open on an unrelated infra blip.
    """
    try:
        models = fetch_model_list()
    except Exception as exc:
        logger.warning(
            "dual_translation.router: could not fetch OpenRouter model list "
            "(%s); assuming slug %r is still valid", exc, slug,
        )
        return True
    return any(m.get('id') == slug for m in models)
