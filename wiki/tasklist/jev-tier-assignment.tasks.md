---
title: "jev Tier Assignment — Task Breakdown"
feature: test-tier-assignment
prose_page: ../features/test-tier-assignment.md
tech_page: ../features/test-tier-assignment.tech.md
total_tasks: 5
done: 5
---

# jev Tier Assignment — Task Breakdown

Decision: [[decisions/ADR-029-jev-tier-assignment]]. Numbers TASK-819–829 are reserved for this
work (the entailment judge took TASK-830–835, see [[tasklist/jev-entailment-judge.tasks]]).
All five tasks are complete; this file records what shipped, for the audit trail.

---

## TASK-819: jev client, classifier and generation wiring

**Status:** [x] Done 2026-09-26
**Type:** feature · **Complexity:** L · **Depends On:** none

Built `services/jev_client.py` (retries, concurrency cap, `llm_calls` logging incl. `cost_usd`
and token counts), `services/tier_classifier.py`, the orchestrator change (classify the finished
passage; assigned tier drives everything stored; `JevError` fails the queue item, no fallback),
migration `task819_jev_tier_assignment.sql` (`tests.age_tier_*`, backup table). Verified by a
live call: `cost_usd` and token counts written.

## TASK-820: Re-tier all active tests

**Status:** [x] Done 2026-09-26 · **Type:** infra · **Complexity:** M · **Depends On:** TASK-819

`scripts/retier_tests_with_jev.py`, migration `task820_apply_jev_retier.sql` (atomic RPC).
305 tests (zh 125, en 121, ja 59), 141 changed tier; verified against the backup: difficulty
changed on exactly those rows, `seeded_elo` untouched, inactive tests untouched. Spot check
(15 per language, one subagent each) found ja +1 tier, en mild, zh compressed.

## TASK-821: Per-language score→tier calibration

**Status:** [x] Done 2026-09-27 · **Type:** feature · **Complexity:** L · **Depends On:** TASK-820

Blind two-reader gold sets (ja 59, zh 60, en 60), `scripts/build_tier_gold_sample.py`,
`scripts/fit_tier_thresholds.py`, `SCORE_THRESHOLDS` for ja (fitted) and zh (uniform −0.25),
en unchanged, `tests.age_tier_calibration`, `scripts/rederive_tiers.py`, backup
`tests_tier_backup_20260927_v1`, migration `task821_tier_calibration.sql`, gold regression
fixtures. Applied live to ja (59) and zh (125). See
[[evaluations/jev-tier-calibration-2026-09-27]].

## TASK-822: Topic tier-fit judge on jev

**Status:** [x] Done 2026-09-26 · **Type:** refactor · **Complexity:** S · **Depends On:** TASK-819

`TierFitJudge` now one score call on concept + distinctive vocabulary; fits when assessed tier
≤ stamped tier; `TIER_READERS`, `best_tier` and the fail-open verdict deleted;
`scripts/backfill_topic_tiers.py` uses `assess`. **Not validated on topic vocabulary lists**
(the feasibility study covered passages only).

## TASK-823: Remove the dead legacy test-creation path

**Status:** [x] Done 2026-09-26 · **Type:** refactor · **Complexity:** S · **Depends On:** none

Deleted `TestService.save_test`, `_create_skill_ratings` and the `/api/tests/generate_test` and
`/custom_test` routes (they inserted a non-existent `tests.topic` column). Also applied
`llm_calls_cost_instrumentation.sql` live so token counts are recorded.

---

## Follow-ups (not filed as tasks)
- Human check of the gold labels; larger gold sets (see [[evaluations/jev-tier-calibration-2026-09-27]]).