---
title: "ADR-035: Study-time ledger table for weekly minutes"
status: proposed
date: 2026-10-14
---

# ADR-035: Study-time ledger table for weekly minutes

## Context
The Study Plan page shows "practice done" from `weekly_plan_states.practice_completed_{maint,acq}_{sec,min}`, which only vocabulary practice feeds (`record_session_progress`, live 8-arg and the repo 10-arg in `migrations/new_words_completed_accrual.sql`). Tests, flashcards and dual translation credit counts only, and when no `weekly_plan_states` row exists `record_session_progress` returns `true` and drops everything (`new_words_completed_accrual.sql`, the `IF NOT FOUND THEN RETURN true` branch). Developer decisions 2026-10-14 require minutes by kind, for activity inside or outside planned sessions, idempotent, attributed to the learner-local week.

## Decision
Add one append-only event table `public.study_time_ledger`, one row per credited source (`user_id, language_id, week_start_date, kind, seconds, source_table, source_id`) with `UNIQUE (kind, source_table, source_id)`, written only by the SECURITY DEFINER function `credit_study_time` (service_role only). Weekly totals are `SUM(seconds) GROUP BY kind` through `get_weekly_study_seconds`. `weekly_plan_states` is not extended and its planner columns keep their meaning.

## Consequences
- Easier: works with no plan row; idempotency is a unique constraint, not a growing jsonb log; new kinds need no migration beyond a CHECK; backfill is a plain `INSERT ... ON CONFLICT DO NOTHING`; auditable (every minute traces to a source row).
- Harder: a SUM per page load (bounded: a week is at most a few hundred rows per learner and language, index `(user_id, language_id, week_start_date)`); a second place (besides `weekly_plan_states.practice_completed_*`) holds practice seconds, so the two can drift by design: the ledger is for display, the plan columns for planner math.
- Constrained: writes only via the function (ADR-034, `migrations/CLAUDE.md`, `tests/test_migration_security_lint.py`): RLS enabled, all client privileges revoked; no browser read today, so no SELECT policy.

## Alternatives Considered
- **Per-kind columns on `weekly_plan_states`** (`tests_sec`, `flashcards_sec`, ...): fewer tables, but drops credit when the row is missing (or forces seeding a row from a credit path, which races `compute_weekly_plan_persist`), needs the jsonb `session_progress_log` for idempotency (unbounded growth, rewrites the wide row on every attempt, existing log keys are per skill not per source), and every new kind is a column migration on a hot planner table.
- **Seed the weekly row on demand**: couples display to planner computation; rejected for the same race.
- **Compute at read time from raw tables** (`test_attempts`, `exercise_attempts`): no flashcard/DT timing exists, timing would need to be added to each raw table anyway, and clamping policy would live in a query. Raw tables remain the backfill source.
