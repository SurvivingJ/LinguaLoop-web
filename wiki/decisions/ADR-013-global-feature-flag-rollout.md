---
title: "ADR-013: Global Config Flag for Study Plan Rollout (Immediate Flip + Rollback)"
status: accepted
date: 2026-05-21
---

# ADR-013: Global Config Flag for Study Plan Rollout (Immediate Flip + Rollback)

## Context

The Study Plan orchestrator ([[decisions/ADR-008-study-plan-orchestration-layer]]) replaces the current `_compute_daily_load` algorithm. Several rollout strategies were evaluated:

1. **Per-user opt-in column + Config kill switch.** `user_study_plans.is_active`; allows cohort A/B.
2. **Pure Config global flag.** One `Config.STUDY_PLAN_ENABLED` constant; all-or-nothing.
3. **New generic `feature_flags` table.** `(flag_name, enabled, percentage_rollout)`. Long-term reusable infrastructure.

LinguaLoop's existing codebase uses Config constants + per-row booleans for feature gates (see `tests.is_active`, `is_featured`, tier-based access in `routes/tests.py`). There is no prior feature-flag framework.

We also need to decide what *governs the flip*:

a. **Staging soak + shadow-mode dry-run + 1-week observation post-flip with rollback threshold.** Most cautious; longest cycle.
b. **Staging soak only, then flip.** Skips production shadow phase.
c. **Immediate flip + monitor.** Highest risk; fastest. Viable only if rollback is trivial.

## Decision

Use a **single global Config flag** (`Config.STUDY_PLAN_ENABLED`), no per-user opt-in column for V1. Rollout strategy: **staging soak first, then immediate production flip + monitor.** Rollback by toggling the Config constant.

Rollout sequence:
1. Ship all migrations with `Config.STUDY_PLAN_ENABLED = False` — schema-only, no behavior change.
2. Ship the merged Practice service with deprecation wrappers — Practice merger ships independently of the orchestrator.
3. Staging soak: manually create `user_study_plans` rows for 10 seeded staging users (covering new / mid-ladder / advanced / lapsed cohorts). Run `compute_weekly_plan` + `build_daily_session` daily for 2 weeks; manually inspect for sanity.
4. Backfill staging — verify all active staging users get a default plan.
5. Backfill production — `Config.STUDY_PLAN_ENABLED` still `False`, so `user_study_plans` rows are created but the adapter doesn't fire.
6. **Flip:** set `Config.STUDY_PLAN_ENABLED = True` and deploy.
7. Monitor 7 days: DAU, session-completion-rate, sessions-per-DAU, tests-per-session, practice-minutes-per-session.
8. **Rollback** by toggling the Config flag if any metric drops > 10% from pre-flip baseline. Rollback is instant; old `_compute_daily_load` resumes; `weekly_plan_states` rows simply go unread.

`get_or_create_daily_load` checks both `Config.STUDY_PLAN_ENABLED` and the presence of a `user_study_plans` row for the user+language; if either is false, falls through to legacy `_compute_daily_load`. The route is identical externally.

## Consequences

- **Easier:** No new infrastructure (no `feature_flags` table). Matches the codebase's existing patterns. Rollback is one constant toggle, no migration.
- **Easier:** The flag is small and obvious in `Config.py`. A developer debugging "why is the new plan not firing" has one place to look.
- **Easier:** Backfilling rows ahead of the flip means the moment we flip, everyone has a plan ready — no race condition between flip and first-user weekly recompute.
- **Harder:** No per-user A/B cohorting in V1. We cannot run a "10% of users get the new plan" experiment without code changes.
- **Harder:** "Immediate flip + monitor" carries more risk than shadow-mode. Mitigated by (a) staging soak qualifying functional correctness; (b) the rollback being a Config toggle (revert PR + deploy ≈ 15 minutes); (c) backfill being non-destructive (legacy `_compute_daily_load` still works on flag-off).
- **Constrained:** If A/B becomes a need later, V2 adds `user_study_plans.is_active boolean` (or equivalent) and the gate becomes `STUDY_PLAN_ENABLED AND user_study_plans.is_active`. No schema migration disrupts existing data.

## Alternatives Considered

1. **Per-user opt-in column.** Recommended in the planning round for cohort A/B. Rejected in favor of the simpler global flag because V1 has no specific A/B hypothesis; we want to ship and observe, not experiment.

2. **New generic `feature_flags` table.** Useful long-term but introduces a pattern this codebase doesn't have. Rejected: build it when we need it for more than one flag.

3. **Staging soak + shadow-mode logging in prod before flip.** The shadow phase would run both `_compute_daily_load` AND `build_daily_session` for each daily-load request, serving the old, logging the new for diff analysis. Stronger pre-flip confidence. Rejected by the user as too slow for the value; the cheap rollback path makes immediate flip acceptable.

## Related Pages

- [[features/study-plans.tech]] — Rollout sequence in full.
- [[decisions/ADR-008-study-plan-orchestration-layer]] — The layer this gates.
