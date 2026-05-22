---
title: Master Task List
last_updated: 2026-05-21
---

# Master Task List

## Summary

| Status | Count |
|--------|-------|
| Not Started | 32 |
| In Progress | 0 |
| Done | 0 |
| Blocked | 1 |

## All Tasks

### Practice Engine Merger
See [[tasklist/practice-merger.tasks]] for full spec per task. Implements [[decisions/ADR-007-merge-exercises-vocab-dojo]].

| ID | Feature | Title | Status | Complexity | Depends On |
|----|---------|-------|--------|------------|------------|
| TASK-101 | practice-engine | Migration — `dim_exercise_types` | [ ] | S | — |
| TASK-102 | practice-engine | Migration — `dim_practice_modes` | [ ] | XS | — |
| TASK-103 | practice-engine | Migration — `user_exercise_sessions.mode + target_minutes` | [ ] | XS | TASK-102 |
| TASK-104 | practice-engine | SQL helper `practice_unified_score` | [ ] | S | TASK-102 |
| TASK-105 | practice-engine | RPC `get_practice_session` (Maintenance branch) | [ ] | M | 101, 102, 104 |
| TASK-106 | practice-engine | Practice service refactor → `practice_session_service.py` | [ ] | M | TASK-105 |
| TASK-107 | practice-engine | RPC `get_practice_session` (Acquisition + iteration) | [ ] | L | 105, 106 |
| TASK-108 | practice-engine | `auto` dispatch + Maintenance fall-through | [ ] | S | TASK-107 |
| TASK-109 | practice-engine | New `/api/practice/session` + `/attempt` routes | [ ] | S | TASK-108 |
| TASK-110 | practice-engine | Deprecation wrappers for legacy RPCs | [ ] | S | TASK-108 |
| TASK-111 | practice-engine | Parity tests (Jaccard ≥ 0.70) | [ ] | M | TASK-110 |
| TASK-112 | practice-engine | Nightly `_refresh_exercise_time_estimates` | [ ] | S | TASK-101 |

### Study Plans
See [[tasklist/study-plans.tasks]] for full spec per task. Implements [[decisions/ADR-008-study-plan-orchestration-layer]].

| ID | Feature | Title | Status | Complexity | Depends On |
|----|---------|-------|--------|------------|------------|
| TASK-201 | study-plans | Migration — `test_attempts.started_at`, `duration_ms` | [ ] | XS | — |
| TASK-202 | study-plans | Migration — `daily_test_loads.daily_session_targets` | [ ] | XS | — |
| TASK-203 | study-plans | Migration — `dim_test_types.expected_minutes_p50` | [ ] | XS | — |
| TASK-204 | study-plans | Migration — `dim_study_plan_templates` + seed (9 rows) | [ ] | S | — |
| TASK-205 | study-plans | Migration — `dim_study_goals` (empty V2 placeholder) | [ ] | XS | — |
| TASK-206 | study-plans | Migration — `user_study_plans` | [ ] | S | 204, 205 |
| TASK-207 | study-plans | Migration — `weekly_plan_states` + index | [ ] | S | TASK-206 |
| TASK-208 | study-plans | RPC `apply_study_plan_template` | [ ] | XS | TASK-206 |
| TASK-209 | study-plans | Python — weakness signal helpers | [ ] | M | TASK-207 |
| TASK-210 | study-plans | RPC `compute_weekly_plan` (Tier B) | [ ] | L | TASK-209 |
| TASK-211 | study-plans | RPC `record_session_progress` | [ ] | S | TASK-207 |
| TASK-212 | study-plans | Wire `record_session_progress` into all submit paths | [ ] | M | 211, 201 |
| TASK-213 | study-plans | RPC `build_daily_session` (Tier C) | [ ] | L | 210, 202 |
| TASK-214 | study-plans | Wire `build_daily_session` into `get_or_create_daily_load` | [ ] | S | TASK-213 |
| TASK-215 | study-plans | Cron — `study_plan_weekly_recompute` (Sun 23:00 UTC) | [ ] | S | TASK-210 |
| TASK-216 | study-plans | `/api/study-plan` endpoints | [ ] | S | 208, 210 |
| TASK-217 | study-plans | Settings UI — Study Plan tab | [ ] | M | TASK-216 |
| TASK-218 | study-plans | Wipe user-state tables for launch (revised 2026-05-22 from backfill) | [ ] | XS | 206, 207 |
| TASK-219 | study-plans | Flag flip + monitoring | [ ] | M | 214, 215, 217, 218 |
| TASK-220 | study-plans | Deprecation cleanup (T+30 days) | [ ] | M | TASK-219 |

### Language Packs (existing — unchanged)

| ID | Feature | Title | Status | Complexity | Depends On |
|----|---------|-------|--------|------------|------------|
| — | language-packs | (all tasks blocked) | [?] | — | Design resolution needed |

See [[tasklist/language-packs.tasks]] and [[features/language-packs.tech]] `open_questions` for blockers.

## Notes

The Practice Engine merger (TASK-101 — TASK-112) ships independently from and BEFORE Study Plans (TASK-201 — TASK-220). Study Plans (Tier C) consumes `get_practice_session` for Practice slot hydration, so the merger must be in production and parity-tested first. The order in the master list reflects this — work TASK-101 through TASK-112 before starting TASK-201.

Study Plans tasks include the rollout sequence in TASK-219 (immediate flip + monitor per [[decisions/ADR-013-global-feature-flag-rollout]]); TASK-220 (deprecation cleanup) waits 30 days after a stable launch.
