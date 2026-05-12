---
title: Vocabulary Ladder & Exercise System — Implementation Analysis
type: algorithm
status: in-progress
tech_page: ./ladder-implementation-analysis.tech.md
last_updated: 2026-05-12
open_questions:
  - "Are the legacy Phase 4 columns first_try_success_count and first_try_failure_count still useful now that consecutive_failures drives demotion and a new family_success_dates JSONB drives advancement? They remain written but never read; candidates for removal in a future migration."
---

# Vocabulary Ladder & Exercise System — Implementation Analysis

## Purpose

This page is the **current audit** of how the vocabulary ladder is implemented, what's working, and what should change. The previous audit (last_updated 2026-04-11) described a per-level chain with first-try-success counters and "no demotion." That audit is now obsolete: Phase 8 (2026-04-18, [migrations/phase8_momentum_bands.sql](../../migrations/phase8_momentum_bands.sql)) replaced the chain with a **Momentum Bands** model — per-family BKT × four rings × two threshold gates × stress test. See [[decisions/ADR-005-momentum-bands]] for why. This audit refreshes the analysis against the post-Phase-8 codebase as of 2026-05-11.

## What's Actually There

Three layers:

1. **Asset Pipeline** (`VocabAssetPipeline`) — 3-prompt LLM generation of immutable per-sense exercises into `word_assets` and `exercises`. Phase 8 added A/B variants and bumped Prompt 1 sentence count to 10.
2. **Ladder Service** ([services/vocabulary_ladder/ladder_service.py](../../services/vocabulary_ladder/ladder_service.py)) — thin Python wrapper around three RPCs (`ladder_record_attempt`, `ladder_pass_gate`, `ladder_graduate`). Adds Python-side battery assembly for gates and stress tests. **Has no session-building responsibilities anymore.** The old `get_exercises_for_session()` and `get_words_for_session()` methods are gone.
3. **Session Builders** — two SQL surfaces, each backed by a single RPC:
   - **`/api/vocab-dojo/session`** → `get_ladder_session` SQL RPC. [routes/vocab_dojo.py:14-70](../../routes/vocab_dojo.py#L14-L70).
   - **`/api/exercises/session`** → `get_exercise_session` SQL RPC (Phase 9, 2026-05-12). The Python service is now a thin wrapper that calls the RPC, appends up to 3 virtual jumbled-sentence picks (language-specific tokenisation stays Python), caches, and enriches. The previously broken bucket-5 disappears: ladder content is sourced from `get_ladder_session` inside the new RPC.

The full ladder picture is documented in [[algorithms/vocabulary-ladder.tech]].

## Where the Previous Audit Was Wrong

The 2026-04-11 audit listed six "critical discrepancies." All six now read differently:

| 2026-04-11 claim | 2026-05-11 reality |
|---|---|
| Ladder is 9 levels, not 10. Level 10 Capstone Production is missing. | Still 9 live exercise types. But a sixth cognitive family (`contextual_use`) is reserved in `FAMILY_WEIGHTS` with weight 0.18 and slot for the future capstone. Its absence caps any word's overall p_known at ≈ 0.92 until L10 ships. |
| Promotion happens on any single first-try success. | Replaced. Promotion is now ring-based: a ring clears when every required family meets its threshold (R1/R2: 0.50, R3: 0.65, R4: 0.72). R2→R3 and R3→R4 are additionally gated by 3-exercise threshold gates. R4 cleared + Gate B passed + p_known ≥ 0.88 + every active family ≥ 0.72 → 8-exercise stress test → `mastered` + FSRS handoff. |
| No demotion exists in the code. | Partially true. Mastered words that fail are demoted to `relearning` via the lapse path, with a 30% extra confidence penalty on the failed family. Pre-mastery words can never lose a ring or fail back to a lower ring — even repeated failure only erodes family confidence. |
| The `user_word_progress` table is missing. | Confirmed — never created. The single live table is `user_word_ladder` with Phase 4 + Phase 8 columns combined. |
| Exercise type names differ from the wiki ladder. | Resolved. The earlier wiki used learner-facing names (e.g. "Listening Flashcard"). Code uses precise names (`phonetic_recognition`). [[algorithms/vocabulary-ladder.tech]] now uses the code names. |
| Two competing session builders. | As of Phase 9 (2026-05-12), two paths, both SQL-RPC-driven: `get_ladder_session` for the dojo, `get_exercise_session` for the daily mixed session. The Python `ExerciseSessionService` shrank from a 6-bucket builder (~1000 lines) to a thin wrapper (~500 lines) that calls the RPC, appends virtual picks, caches, and enriches. `LadderService` is RPC-only. |

## What Works Well

### Atomic, transaction-safe progression in SQL

Every attempt path goes through one RPC (`ladder_record_attempt`) that locks the user's ladder row `FOR UPDATE`, performs all confidence / ring / state / FSRS updates, and returns a single JSONB payload. No Python-level race conditions are possible. Side effects are auditable via one function.

### Family-level skill resolution

A word's profile is now a six-vector (`family_confidence` JSONB), not a single scalar. The session builder picks the *weakest family in the current ring* as the target — so two learners with the same overall p_known but different family profiles get materially different next exercises.

### Single source of truth for the dojo

`get_ladder_session` is the entire dojo session builder. Priority weights, anti-repetition (seen-today filter against `user_exercise_history`), and variant alternation are all in one SQL function. No Python orchestration to keep in sync.

### Frontend-friendly RPC returns

Both `get_ladder_session` and `ladder_record_attempt` return everything the frontend needs in one trip: gate flags, stress-test readiness, family confidences, overall p_known, FSRS data. The frontend can branch to the gate/stress-test flow without an extra round trip.

### Concrete-noun routing preserved

`ladder_ring_families(ring, active_levels)` consults `active_levels` so a concrete noun's R2 doesn't require collocation. The Phase 8 model didn't break the Phase 2 POS-aware routing.

### A/B variants

Phase 8 added optional A/B exercise variants for several types. The session builder alternates them by reading `exercises.tags->>'variant'` and comparing against `user_exercise_history`. Reduces memorisation effects without changing the offline asset pipeline shape.

## What Needs Improvement

### Priority 1: ✅ Resolved (Phase 9, 2026-05-12)

Daily-session bucket-5 was rebuilt in SQL. The Python `ExerciseSessionService._compute_session()` is replaced by a call to the new `get_exercise_session` RPC ([migrations/phase9_get_exercise_session.sql](../../migrations/phase9_get_exercise_session.sql)). Inside that RPC, ladder content comes from `get_ladder_session` — single source of truth for ladder selection. The four Python helpers that backed the broken bucket (`_select_exercises_for_senses`, `_get_supplementary_exercises`, `_get_ladder_exercises`, `_get_recent_exercise_ids`) were deleted along with the module-level phase-weighting helpers.

### Priority 2: ✅ Resolved (Phase 10, 2026-05-12)

Phase 10 layers two counter-driven behaviours onto `ladder_record_attempt` ([migrations/phase10_ladder_advancement_demotion.sql](../../migrations/phase10_ladder_advancement_demotion.sql)):

- **Cross-session advancement gate.** A new `family_success_dates` JSONB column tracks per-family first-attempt-success calendar dates (trimmed to the most recent 2). Ring advancement now requires both (a) family confidence ≥ ring threshold AND (b) ≥ 2 distinct dates in the family's success-date array. Prevents same-day farming.
- **Ring demotion.** When `consecutive_failures ≥ 3` on a family that gates the current ring, the word drops one ring. The gate guarding exit from the dropped-into ring resets (gate_a on demote→R2, gate_b on demote→R3); other gates survive. `family_success_dates` for the demoted-into-ring required families is cleared. R1 is the floor.

The legacy `first_try_success_count` and `first_try_failure_count` columns remain written but unread — flagged as open_question for a future cleanup.

### Priority 3: ✅ Resolved (Phase 9, 2026-05-12)

Shipped together with Priority 1. The `get_exercise_session` RPC mirrors `get_ladder_session` in shape: a single CTE pipeline (recent-seen → session_senses → ladder_picks → vocab_picks → supplementary_picks → UNION ALL → priority-ordered LIMIT). The Python service is ~500 lines (down from ~1000) and contains no scheduling logic — it's call → append virtual → cache → enrich.

### Priority 4: Ship the L10 capstone — `contextual_use` family (L, Very high impact)

`contextual_use` is weighted into overall p_known at 0.18 but has no live exercise type. This means every word's overall p_known is capped at ≈ 0.92 (the contribution of the 0.10 default for `contextual_use`). The stress test composition reserves 2/8 slots for `contextual_use` exercises that don't exist — `assemble_stress_test` falls back to the highest available level. Once shipped, a Level 10 free-text capstone graded by a small LLM would close this loop. Needs: new exercise type, runtime LLM call, grading rubric, cost management.

### Priority 5: IRT difficulty calibration ✅ Resolved (Phase 11)

Shipped 2026-05-12 as [migrations/add_irt_calibration_metadata.sql](../../migrations/add_irt_calibration_metadata.sql) (3 new columns + `irt_apply_calibration` / `irt_compute_user_theta` RPCs) + [migrations/phase11_irt_selection.sql](../../migrations/phase11_irt_selection.sql) (Gaussian IRT weight inside `get_exercise_session`). The fitter is [services/irt/calibrator.py](../../services/irt/calibrator.py) — 2PL MLE via `scipy.optimize.minimize`, with a tier-seed prior pull (k=10 pseudocounts) so newly-eligible items don't swing on one cohort. Runs nightly at 04:00 UTC via APScheduler ([app.py](../../app.py)), guarded by a Postgres advisory lock. Triggerable on demand from the admin dashboard's IRT Calibration tab.

## Quantitative Impact Assessment

| Improvement | Dev effort | User impact | Data risk | Status |
|-------------|-----------|-------------|-----------|--------|
| Fix daily-session bucket-5 + consolidate daily-session into SQL | M (1–2d) | High — restores daily ladder slot, one source of truth | Low | ✅ Phase 9, 2026-05-12 |
| Cross-session advancement gating + ring demotion (counter-driven) | M (4–8h) | Medium — guards against single-day farming; structural step-back signal | Low | ✅ Phase 10, 2026-05-12 |
| L10 capstone (`contextual_use`) | L (2–3d) | Very high — unlocks mastery ceiling | Medium (runtime LLM cost) | Open |
| IRT calibration | M (4–8h) | Medium — better targeting within a family | None | ✅ Phase 11, 2026-05-12 |

## Related Pages

- [[algorithms/ladder-implementation-analysis.tech]] — Technical analysis with code references
- [[algorithms/vocabulary-ladder]] — Current ladder design (Momentum Bands)
- [[algorithms/vocabulary-ladder.tech]] — Current ladder technical specification
- [[features/exercises]] — Exercise type inventory
- [[features/vocab-dojo]] — Adaptive exercise serving
- [[features/vocabulary-knowledge]] — BKT integration (overall p_known)
- [[algorithms/bkt-implementation-analysis]] — BKT analysis (interacts with ladder)
- [[decisions/ADR-005-momentum-bands]] — Decision behind the refactor
