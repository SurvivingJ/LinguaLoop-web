---
title: Master Task List
last_updated: 2026-06-11
---

# Master Task List

## Summary

| Status | Count |
|--------|-------|
| Not Started | 63 |
| In Progress | 0 |
| Done | 18 |
| Blocked | 4 |

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

### Ladder Judge Layer (Phase 4)
See [[tasklist/ladder-judge-layer.tasks]] for full spec per task. Implements B3.1 + B3.6 of [[reviews/exercise-generation-audit-2026-06-07]]. Extends the judge layer from L3-only to every LLM-authored ladder level (L1/L5/L6/L7/L8) plus the P1 sentence corpus, en + zh. **Complete** — all four judge chains (P1/L1/collocation/sentence-validity) plus the 4.3 observability layer (reject-rate view + admin dashboard + integration test) shipped; seed migration applied.

| ID | Feature | Title | Status | Complexity | Depends On |
|----|---------|-------|--------|------------|------------|
| TASK-401 | ladder-judge-layer | Generalize renderer judge-meta tag sidecar | [x] | S | — |
| TASK-402 | ladder-judge-layer | P1 sentence judge module | [x] | M | — |
| TASK-403 | ladder-judge-layer | Seed `ladder_p1_sentence_judge` prompts (en+zh) | [x] | M | TASK-402 |
| TASK-404 | ladder-judge-layer | Wire P1 sentence judge into asset_pipeline | [x] | M | 402, 403 |
| TASK-405 | ladder-judge-layer | L1 distractor judge module | [x] | S | TASK-401 |
| TASK-406 | ladder-judge-layer | Seed `ladder_l1_distractor_judge` prompts (en+zh) | [x] | S | TASK-405 |
| TASK-407 | ladder-judge-layer | Wire L1 judge into `_render_phonetic` | [x] | S | 405, 406 |
| TASK-408 | ladder-judge-layer | Collocation judge module (L5+L8) | [x] | M | TASK-401 |
| TASK-409 | ladder-judge-layer | Seed `ladder_collocation_judge` prompts (en+zh) | [x] | S | TASK-408 |
| TASK-410 | ladder-judge-layer | Wire collocation judge into L5/L8; retire L8 hack | [x] | M | 408, 409 |
| TASK-411 | ladder-judge-layer | Sentence-validity judge module (L6+L7) | [x] | M | TASK-401 |
| TASK-412 | ladder-judge-layer | Seed `ladder_sentence_validity_judge` prompts (en+zh) | [x] | S | TASK-411 |
| TASK-413 | ladder-judge-layer | Wire sentence-validity judge into L6/L7 | [x] | M | 411, 412 |
| TASK-414 | ladder-judge-layer | Reject-rate SQL view (judge-as-data) | [x] | M | 404, 407, 410, 413 |
| TASK-415 | ladder-judge-layer | Admin reject-rate dashboard | [x] | S | TASK-414 |
| TASK-416 | ladder-judge-layer | Judge-layer integration test + smoke query | [x] | S | 404, 407, 410, 413 |

### Exercise Generation v2
See [[tasklist/exercise-generation-v2.tasks]] for full spec per task. Implements [[features/exercise-generation-v2]] (design plan, all operator decisions final 2026-06-11). Task IDs map 1:1 to the plan's deliverables (TASK-501 = P0.1 … TASK-536 = P4.3). TASK-515 (the top-1,000 × 3-language batch run) is the integration gate.

| ID | Feature | Title | Status | Complexity | Depends On |
|----|---------|-------|--------|------------|------------|
| TASK-501 | exercise-generation-v2 | Commit 2026-06-10 working tree + verify live state | [x] | XS | — |
| TASK-502 | exercise-generation-v2 | Ratify + migrate `semantic_class` 6-value enum | [x] | S | — |
| TASK-503 | exercise-generation-v2 | Fix `dim_exercise_types.family` + new type rows | [ ] | S | — |
| TASK-504 | exercise-generation-v2 | `dim_exercise_capabilities` table + seeds + wiring | [ ] | M | 502, 503 |
| TASK-505 | exercise-generation-v2 | JA vocab bootstrap (transcripts only; B4 fix) | [ ] | M | — |
| TASK-506 | exercise-generation-v2 | Pronunciation backfill (ZH/JA) + JA `register` column | [ ] | M | TASK-505 |
| TASK-507 | exercise-generation-v2 | `semantic_class` LLM backfill + spot-check | [ ] | M | 502, 505 |
| TASK-508 | exercise-generation-v2 | JA prompt seeds (P1/P2/P3 + 4 judges + gen rows) | [ ] | M | TASK-501 |
| TASK-509 | exercise-generation-v2 | Traditional Chinese groundwork (dual-store + `hant` mirrors) | [ ] | M | TASK-501 |
| TASK-510 | exercise-generation-v2 | Slug health cron + fail-closed batch judges | [ ] | S | TASK-501 |
| TASK-511 | exercise-generation-v2 | `generation_queue` migration | [ ] | XS | — |
| TASK-512 | exercise-generation-v2 | Consolidation — ladder is the sole vocab generator | [ ] | M | TASK-501 |
| TASK-513 | exercise-generation-v2 | Transcript mining as a P1 sentence source | [ ] | M | TASK-512 |
| TASK-514 | exercise-generation-v2 | Robustness: non-destructive regen, P1 retry, matrix-gated L4 | [ ] | M | TASK-504 |
| TASK-515 | exercise-generation-v2 | Batch run — top 1,000 senses × EN/ZH/JA | [ ] | L | 504–511, 513, 514, 519 |
| TASK-516 | exercise-generation-v2 | Deterministic generators (def-match, jumbled, readings, tone) | [ ] | L | 503, 506 |
| TASK-517 | exercise-generation-v2 | Coverage check + batch report + queue drain | [ ] | M | 504, 511 |
| TASK-518 | exercise-generation-v2 | Per-sense legacy exercise dedupe | [ ] | S | TASK-515 |
| TASK-519 | exercise-generation-v2 | Multi-nl content rules (`content.nl` keyed maps) | [ ] | S | TASK-501 |
| TASK-520 | exercise-generation-v2 | Prompt split — L4 + L8 out of P3 monolith | [ ] | M | TASK-515 |
| TASK-521 | exercise-generation-v2 | Sense embeddings (pgvector) | [ ] | M | TASK-501 |
| TASK-522 | exercise-generation-v2 | `synonym_antonym_match` + `word_family` generators | [ ] | L | 504, 521 |
| TASK-523 | exercise-generation-v2 | Collocation grounding for L5/L8 | [ ] | M | TASK-515 |
| TASK-524 | exercise-generation-v2 | Sentence-tier hard gate | [ ] | S | TASK-513 |
| TASK-525 | exercise-generation-v2 | tl_nl uniqueness judge | [ ] | S | TASK-501 |
| TASK-526 | exercise-generation-v2 | Traditional-script serve toggle (practice surfaces) | [ ] | M | 509, 515 |
| TASK-527 | exercise-generation-v2 | JA `particle_selection` generator + judge | [ ] | M | 508, 515 |
| TASK-528 | exercise-generation-v2 | ZH `classifier_match` as ladder L4 | [ ] | M | TASK-504 |
| TASK-529 | exercise-generation-v2 | `reading_to_kanji` / `pinyin_to_hanzi` + component table | [ ] | M | TASK-516 |
| TASK-530 | exercise-generation-v2 | JA counter drill (助数詞) + `counter_match` | [ ] | L | TASK-504 |
| TASK-531 | exercise-generation-v2 | Audio at scale (L1 + listening) | [ ] | M | TASK-515 |
| TASK-532 | exercise-generation-v2 | `cloze_typed` free input (normalised match) | [ ] | M | TASK-515 |
| TASK-533 | exercise-generation-v2 | `timed_speed_round` serve-time composer | [ ] | M | TASK-515 |
| TASK-534 | exercise-generation-v2 | Exercise-type effectiveness view | [?] | M | 515 + launch data |
| TASK-535 | exercise-generation-v2 | Thompson-sampling type tie-breaker | [?] | L | TASK-534 |
| TASK-536 | exercise-generation-v2 | Per-user format prefs + item retirement | [?] | M | TASK-534 |

### Language Packs (existing — unchanged)

| ID | Feature | Title | Status | Complexity | Depends On |
|----|---------|-------|--------|------------|------------|
| — | language-packs | (all tasks blocked) | [?] | — | Design resolution needed |

See [[tasklist/language-packs.tasks]] and [[features/language-packs.tech]] `open_questions` for blockers.

## Notes

The Practice Engine merger (TASK-101 — TASK-112) ships independently from and BEFORE Study Plans (TASK-201 — TASK-220). Study Plans (Tier C) consumes `get_practice_session` for Practice slot hydration, so the merger must be in production and parity-tested first. The order in the master list reflects this — work TASK-101 through TASK-112 before starting TASK-201.

Study Plans tasks include the rollout sequence in TASK-219 (immediate flip + monitor per [[decisions/ADR-013-global-feature-flag-rollout]]); TASK-220 (deprecation cleanup) waits 30 days after a stable launch.
