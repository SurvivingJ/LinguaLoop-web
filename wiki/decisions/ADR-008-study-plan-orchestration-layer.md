---
title: "ADR-008: Study Plan as a Cross-Surface Orchestration Layer"
status: accepted
date: 2026-05-21
---

# ADR-008: Study Plan as a Cross-Surface Orchestration Layer

## Context

Every practice surface in LinguaLoop schedules itself in isolation. `daily_test_loads` fills 8–12 ELO-matched tests. `get_practice_session` (post-merger; see [[decisions/ADR-007-merge-exercises-vocab-dojo]]) fills Practice items per mode. FSRS reviews surface separately. Language-specific trainers (pinyin, measure-word, pitch-accent) each have their own cadence. There is no concept of a weekly target mix or a daily time budget that spans these surfaces.

A learner who opens the app and asks "what should I do today?" gets no coherent answer — they see N CTAs and choose by instinct or habit. Power users overshoot one surface and ignore others; casual users do whatever loads first and stop.

We need a layer that:
- Knows the learner's weekly time budget.
- Knows their weakness profile across skills.
- Allocates time *across* surfaces, not within one.
- Adapts week-over-week to the data.

## Decision

Add a Study Plan layer with two tiers of computation:

- **Tier B — Weekly Adapter.** Cron job `compute_weekly_plan` runs every Sunday 23:00 UTC. For each `(user, language)` pair with an active plan, computes a weakness signal per test skill, allocates weekly test counts via value-weighted Thompson sampling ([[decisions/ADR-010-value-weighted-thompson-skill-mix]]), and rebalances Practice minutes between Maintenance and Acquisition. Outputs persist to `weekly_plan_states`.
- **Tier C — Daily Resolver.** Lazy, on first session request per day. `build_daily_session` reads the current `weekly_plan_states` row, computes today's budget from `weekday_shape · total_weekly_minutes / 7`, and solves a small constrained optimization (≤ 6 test skills + 2 Practice variables; greedy + local swap, ILP fallback) for today's mix. Writes test slots to `daily_test_loads` (reused) and Practice minute targets to a new `daily_test_loads.daily_session_targets jsonb` column.

The orchestrator is *additive*: existing RPCs (`get_recommended_tests`, `get_practice_session`) are the implementation arms. Tier C decides *what mix*; the existing RPCs decide *which specific items*. `get_or_create_daily_load` checks `Config.STUDY_PLAN_ENABLED`; if true and `user_study_plans` row exists, route through `build_daily_session`, else fall through to legacy `_compute_daily_load`. This makes rollback a single Config toggle.

Plans are **per-language, independent**: one `user_study_plans` row per `(user_id, language_id)` with its own `daily_minutes`, `weekday_shape`, and `skill_weight_overrides`. See [[decisions/ADR-011-per-language-independent-budgets]].

Templates seed beginner cadences (30 / 45 / 60 min/day per language). Adapter shifts test counts within `floor = ⌈target · 0.5⌉, ceiling = ⌈target · 1.5⌉`. Practice minutes flex ±25% within the weekly time budget. Maintenance/Acquisition split is bounded `[0.15, 0.50] / [0.50, 0.85]` (never starves retention, never starves new learning).

## Consequences

- **Easier:** A single "Practice" CTA can intelligently route to tests or practice based on what the user needs today, with no UI complexity per surface.
- **Easier:** Telemetry has one place to look ("did this user hit their plan?"). Future personalization (notification timing, adaptive volume, goal-driven biasing) plugs into this layer.
- **Easier:** Each surface's existing logic is preserved — the orchestrator is a thin layer above, not a rewrite. Rollback is a Config toggle.
- **Harder:** Two new tables (`user_study_plans`, `weekly_plan_states`), four new RPCs, two new cron jobs, a settings UI tab, and a backfill SQL to populate existing users.
- **Harder:** Multi-language users have N independent plans; UI must surface this without confusion. The settings tab is per-language.
- **Constrained:** V1 uses shared Sunday 23:00 UTC for all weekly recomputes (not per-user TZ). A `user_study_plans.timezone TEXT DEFAULT 'UTC'` column is added now so V2 can switch to a per-TZ windowed cron without migration.
- **Constrained:** Goals (HSK level, JLPT date) are a V2 follow-up. `user_study_plans.goal_id` is nullable and ignored by the V1 adapter; the V2 spec adds a `goal_pressure(s)` term to the weakness signal.

## Alternatives Considered

1. **Extend each surface with its own time budget.** Each RPC takes a `target_minutes` argument; the UI sums them. Rejected: the surfaces don't know about each other's quotas, so a heavy-test day could starve practice and vice versa. The "what should I do today" question requires a layer that sees all surfaces.

2. **Single monolithic RPC that returns the full day's plan including specific test IDs and practice items.** Rejected: too much coupling. The orchestrator is about *allocation*; item selection is a separate concern with its own optimization (ELO match for tests, unified score for practice). Keeping them split lets each evolve independently.

3. **Client-side orchestration.** The frontend asks each surface for a quota and renders a daily plan. Rejected: requires the FE to replicate the weakness signal and adapter logic; cross-platform (web + future mobile) duplication; harder to A/B and observe.

4. **Per-user opt-in flag from day one.** Lets us cohort-A/B old vs new behavior. Rejected for V1 simplicity in favor of a global `Config.STUDY_PLAN_ENABLED` flag ([[decisions/ADR-013-global-feature-flag-rollout]]); per-user opt-in is a V2 follow-up if we want experimental cohorts.

## Related Pages

- [[features/study-plans]] — Plain-English description.
- [[features/study-plans.tech]] — Full technical specification (Tier B + Tier C pseudocode, schema, RPCs).
- [[algorithms/study-plan-adaptation]] — Adaptation philosophy.
- [[algorithms/study-plan-adaptation.tech]] — Formulas, constants, pseudocode.
- [[decisions/ADR-007-merge-exercises-vocab-dojo]] — The Practice surface the orchestrator allocates against.
- [[decisions/ADR-009-two-budget-tests-vs-practice]] — Why two budgets, not three.
- [[decisions/ADR-010-value-weighted-thompson-skill-mix]] — Tier B allocation algorithm.
- [[decisions/ADR-011-per-language-independent-budgets]] — Per-language model.
- [[decisions/ADR-013-global-feature-flag-rollout]] — Rollout / rollback mechanism.
