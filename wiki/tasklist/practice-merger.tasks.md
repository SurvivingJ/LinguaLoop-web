---
title: "Practice Engine Merger — Task Breakdown"
feature: practice-engine
prose_page: ../features/practice-engine.md
tech_page: ../features/practice-engine.tech.md
total_tasks: 12
done: 0
---

# Practice Engine Merger — Task Breakdown

Implements [[decisions/ADR-007-merge-exercises-vocab-dojo]]. Atomic tasks that ship `get_practice_session` and the deprecation wrappers, preserving full ladder mechanics from [[decisions/ADR-005-momentum-bands]]. Order respects dependencies. Numbers in `TASK-1xx` are reserved for the merger work; Study Plan tasks are `TASK-2xx`.

---

## TASK-101: Migration — `dim_exercise_types`

**Status:** [ ] Not Started
**Feature:** practice-engine
**Type:** infra
**Complexity:** S (1–3h)
**Depends On:** none

**Description:**
Create the `dim_exercise_types` registry. Seed `type_code`, `family`, `expected_seconds=45` from `SELECT DISTINCT exercise_type FROM exercises WHERE exercise_type IS NOT NULL`. Map each `type_code` to one of the 6 cognitive families (form_recognition, meaning_recall, form_production, collocation, semantic_discrimination, contextual_use) — use the existing mapping logic in `services/vocabulary_ladder/config.py` (`map_exercise_type_to_family`).

**Acceptance Criteria:**
- [ ] Table created with PK on `type_code`, all NOT NULL columns enforced.
- [ ] Every existing `exercises.exercise_type` value is represented in `dim_exercise_types`.
- [ ] All seeded rows have a non-NULL `family` value.
- [ ] `expected_seconds_p50` is NULL initially.

**Files:**
- `migrations/study_plans_v1/001_dim_exercise_types.sql` — DDL + INSERT.

**Verification:**
`SELECT COUNT(DISTINCT exercise_type) FROM exercises WHERE exercise_type IS NOT NULL;` equals `SELECT COUNT(*) FROM dim_exercise_types;`.

---

## TASK-102: Migration — `dim_practice_modes`

**Status:** [ ] Not Started
**Feature:** practice-engine
**Type:** infra
**Complexity:** XS (<1h)
**Depends On:** none

**Description:**
Create `dim_practice_modes(mode_id PK, name UNIQUE, default_weights jsonb, is_active)`. Seed 3 rows per spec.

**Acceptance Criteria:**
- [ ] Table created.
- [ ] Three rows present: `acquisition`, `maintenance`, `auto`.
- [ ] `default_weights` jsonb for `acquisition` and `maintenance` parses to the spec's α/β/γ/δ values; `auto` row has NULL weights.

**Files:**
- `migrations/study_plans_v1/002_dim_practice_modes.sql`.

**Verification:**
`SELECT name, default_weights FROM dim_practice_modes ORDER BY mode_id;` returns the 3 expected rows.

---

## TASK-103: Migration — `user_exercise_sessions.mode` + `target_minutes`

**Status:** [ ] Not Started
**Type:** infra
**Complexity:** XS
**Depends On:** TASK-102

**Description:**
`ALTER TABLE user_exercise_sessions ADD COLUMN mode text CHECK ..., ADD COLUMN target_minutes smallint`. Rows already present retain NULL — backfill is unnecessary since the table is repurposed and the new logic will write the columns going forward.

**Acceptance Criteria:**
- [ ] Columns added with the spec's CHECK constraint.
- [ ] Existing rows unchanged; no errors.

**Files:**
- `migrations/study_plans_v1/007_alter_user_exercise_sessions_mode.sql`.

**Verification:**
`\d user_exercise_sessions` shows the new columns.

---

## TASK-104: SQL helper `practice_unified_score`

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** S
**Depends On:** TASK-102

**Description:**
Implement the `IMMUTABLE` SQL function exactly as specified in [[algorithms/practice-unified-score.tech]]. Unit-test against hand-computed corner cases.

**Acceptance Criteria:**
- [ ] Function created.
- [ ] For (`a=1`, `b=θ`, `p_known=0.5`, `due_date=today`, `stability=7`, `ladder_priority=1`, weights `acquisition`): output ≥ 0.40·1 + 0.30·1 + 0.25·1 + 0.05·0.5 = 0.975 within 4 decimals.
- [ ] For (no IRT params + due_date NULL + ladder=0): output reduces to γ·norm_bkt only.

**Files:**
- `migrations/practice_merger/practice_unified_score.sql`.
- `tests/sql/test_practice_unified_score.py`.

**Verification:**
`SELECT practice_unified_score(1.0, 0.0, 0.0, 0.5, CURRENT_DATE, 7, CURRENT_DATE, 1.0, 0.40, 0.30, 0.25, 0.05);` returns ~0.975.

---

## TASK-105: RPC `get_practice_session` — Maintenance pool + ranking

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** M (3–8h)
**Depends On:** TASK-101, TASK-102, TASK-104

**Description:**
Implement the Maintenance branch only: candidate pool SQL (`due_or_decayed` CTE, LIMIT 200 pre-rank, full score rank). Skip Acquisition for this task. Return jsonb shape per spec.

**Acceptance Criteria:**
- [ ] RPC created with the spec's signature.
- [ ] `p_mode='maintenance'` returns a jsonb with `mode_resolved='maintenance'` and an `items` array.
- [ ] Items ordered by `practice_unified_score` DESC.
- [ ] `WHERE e.sense_id IS NOT NULL` enforced.
- [ ] Cap at 200 candidates verified via `EXPLAIN ANALYZE`.

**Files:**
- `migrations/practice_merger/get_practice_session.sql` (partial — Maintenance only).

**Verification:**
Seed staging user with 30 FSRS-due cards. Call `get_practice_session(user, lang, 'maintenance', 15)`. Verify ≤ 20 items returned, ordered by score, all `sense_id IS NOT NULL`.

---

## TASK-106: Practice service refactor — `services/practice_session_service.py`

**Status:** [ ] Not Started
**Type:** refactor
**Complexity:** M
**Depends On:** TASK-105

**Description:**
Rename `services/exercise_session_service.py` to `services/practice_session_service.py`. Split into `_acquisition.py`, `_maintenance.py`, `_scoring.py`. The Maintenance path calls the new RPC; Acquisition (next task) preserves the current `get_ladder_session` orchestration until TASK-107.

**Acceptance Criteria:**
- [ ] File renamed; imports updated across the codebase.
- [ ] Submodules created with mode dispatch in the public entry point.
- [ ] No behavioral regression in `/api/exercises/session` (still calls legacy logic).
- [ ] All existing exercise unit tests pass.

**Files:**
- `services/practice_session_service.py` + submodules.
- `routes/exercises.py`, `routes/vocab_dojo.py` — import updates.
- `tests/services/test_*` — import updates.

**Verification:**
`pytest tests/services/` passes. `grep -r "exercise_session_service" --include="*.py"` returns only the import alias if any.

---

## TASK-107: RPC `get_practice_session` — Acquisition pool + iteration

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** L (1–2d)
**Depends On:** TASK-105, TASK-106

**Description:**
Implement Acquisition mode end-to-end: word selection by ladder priority (top 50), per-required-family top-item-by-unified-score selection, inline gate / stress-test battery dispatch, time-budget loop. Cold-ladder auto-subscription falls back to Maintenance per spec.

**Acceptance Criteria:**
- [ ] `p_mode='acquisition'` returns items with `mode='acquisition'` and `family` populated.
- [ ] Per-word `K = len(ring_families(word.current_ring))` items drawn before moving on.
- [ ] Pending gate batteries appear inline (3 items, contiguous).
- [ ] Pending stress tests appear inline (8 items, contiguous).
- [ ] Empty eligible-word pool triggers auto-subscribe (use existing pack-selection helpers); if no packs, falls through to Maintenance; if both empty returns `no_content_reason='no_packs_selected'`.
- [ ] Time budget honored: total `expected_seconds` does not exceed `target_minutes·60` by more than one item.

**Files:**
- `services/practice_session_service.py::_acquisition.py`.
- `migrations/practice_merger/get_practice_session.sql` (completed with auto branch).

**Verification:**
Seed staging user with 20 ladder-active words across mixed rings. Call `get_practice_session(user, lang, 'acquisition', 15)`. Verify: ≤ 5 distinct words anchored, K matches each word's ring, gate batteries inline where pending, total time ≤ 16 min.

---

## TASK-108: Mode dispatch (`auto`) + Maintenance fall-through

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** S
**Depends On:** TASK-107

**Description:**
Implement `auto` mode dispatch (`due_today + decayed >= active_ladder → maintenance`) and the Maintenance-dry → Acquisition fall-through. Each returned item must carry its actual `mode` field so the FE can render section breaks.

**Acceptance Criteria:**
- [ ] `p_mode='auto'` returns `mode_resolved` reflecting the dispatch.
- [ ] When Maintenance pool empties mid-session, subsequent items have `mode='acquisition'`.
- [ ] When Acquisition pool empties (no eligible + no packs), returns `no_content_reason` rather than falling further.

**Files:**
- `services/practice_session_service.py::__init__.py` (orchestrator) — dispatch.
- `migrations/practice_merger/get_practice_session.sql` — finalized.

**Verification:**
Seed user with 1 FSRS-due card + 50 active ladder words. Call `('maintenance', 20)`. Verify: first item mode=maintenance; subsequent items mode=acquisition.

---

## TASK-109: New canonical route `/api/practice/session` + `/api/practice/attempt`

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** S
**Depends On:** TASK-108

**Description:**
Create `routes/practice.py` with GET `/api/practice/session?mode=...&minutes=...&language_id=...&debug=0|1` and POST `/api/practice/attempt`. Register blueprint in `app.py`. Both delegate to `PracticeSessionService`.

**Acceptance Criteria:**
- [ ] Blueprint registered.
- [ ] Auth decorator applied (existing JWT middleware).
- [ ] `debug=1` includes `score_breakdown` in each item; otherwise omitted.
- [ ] Attempt endpoint calls `record_attempt_with_updates(..., session_mode=mode)`.

**Files:**
- `routes/practice.py` (new).
- `app.py` — blueprint registration.

**Verification:**
`curl /api/practice/session?mode=auto&minutes=10&language_id=1` returns 200 with valid jsonb.

---

## TASK-110: Deprecation wrappers — `get_exercise_session`, `get_ladder_session`

**Status:** [ ] Not Started
**Type:** refactor
**Complexity:** S
**Depends On:** TASK-108

**Description:**
Replace the existing `get_exercise_session` and `get_ladder_session` RPC bodies with thin wrappers calling `get_practice_session` with the appropriate mode + minute estimate. Add `RAISE WARNING 'DEPRECATED'`. Existing legacy callers (`/api/exercises/session`, `/api/vocab-dojo/session`) continue to function.

**Acceptance Criteria:**
- [ ] Old RPC names preserved; signatures unchanged; bodies are now wrappers.
- [ ] `RAISE WARNING` appears in pg_log when wrappers fire.
- [ ] Existing route handlers continue to return their previous TABLE row shapes (compatible).
- [ ] Existing integration tests for `/api/exercises/session` and `/api/vocab-dojo/session` still pass.

**Files:**
- `migrations/practice_merger/deprecate_get_exercise_session.sql`.
- `migrations/practice_merger/deprecate_get_ladder_session.sql`.

**Verification:**
Run existing exercise + vocab-dojo route integration tests; all green. Inspect pg_log for the DEPRECATED warning.

---

## TASK-111: Parity tests — Jaccard ≥ 0.70

**Status:** [ ] Not Started
**Type:** test
**Complexity:** M
**Depends On:** TASK-110

**Description:**
Implement parity test per [[features/practice-engine.tech#parity-test-r47]]. Seed 50 staging users across the 4 cohorts; compare old vs new session item sets via Jaccard.

**Acceptance Criteria:**
- [ ] Seeded users created (≥ 10 per cohort).
- [ ] Test runs both old and new RPCs.
- [ ] Median Jaccard ≥ 0.70; min Jaccard ≥ 0.50.
- [ ] CSV report written to `wiki/raw/parity_reports/<date>.csv`.
- [ ] Test fails CI if thresholds not met.

**Files:**
- `tests/integration/test_practice_merger_parity.py`.
- `tests/fixtures/seed_parity_users.sql`.

**Verification:**
`pytest tests/integration/test_practice_merger_parity.py -v` reports pass with summary stats logged.

---

## TASK-112: Nightly `_refresh_exercise_time_estimates` job

**Status:** [ ] Not Started
**Type:** infra
**Complexity:** S
**Depends On:** TASK-101

**Description:**
Add nightly cron entry at 04:05 UTC (5 min after IRT) that refreshes `dim_exercise_types.expected_seconds_p50` from observed P50s when ≥ 30 samples exist in the last 30 days. Same advisory-lock pattern as IRT. Service-layer `expected_seconds(type)` prefers `_p50` when present.

**Acceptance Criteria:**
- [ ] Cron job registered in `app.py:227-251`.
- [ ] UPDATE statement runs only on types with ≥ 30 samples.
- [ ] `expected_seconds(type)` helper returns `_p50` when present, else default.

**Files:**
- `app.py` — cron registration.
- `services/irt/calibrator.py::_refresh_exercise_time_estimates` (or new helper module).

**Verification:**
Seed `exercise_attempts.time_taken_ms` for one type with 50 samples; run job manually; `dim_exercise_types.expected_seconds_p50` for that type updates.

---
