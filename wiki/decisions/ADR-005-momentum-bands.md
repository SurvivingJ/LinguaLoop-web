---
title: "ADR-005: Momentum Bands — Family-BKT × Rings × Gates × Stress Test"
status: accepted
date: 2026-04-18
---

# ADR-005: Momentum Bands — Family-BKT × Rings × Gates × Stress Test

## Context

The original ladder design (see [[algorithms/vocabulary-ladder]]) promoted a learner up a 9-level chain on **2 first-attempt successes in separate sessions** and demoted on **2 consecutive first-attempt failures**. The Phase 4 schema migration added the columns needed for that model (`first_try_success_count`, `first_try_failure_count`, `consecutive_failures`, `last_success_session_date`) but the Python promotion path was always a stub: it promoted on a single first-try success and never demoted.

By April 2026, three weaknesses of the original model were clear from real attempt data:

1. **Per-level promotion is too coarse.** Promoting up a single rail in lockstep ignored which *kind* of knowledge had been demonstrated. A learner could pass two L3 cloze attempts and advance to L4 morphology with no evidence that production was actually building.
2. **No partial credit.** A learner could be strong on form-recognition but weak on collocation; a per-level chain couldn't represent that. It treated the word as a single scalar.
3. **Mastery had no exit.** The original spec ended at a single capstone level (L10, never implemented) with no graduation handoff to FSRS-based maintenance. There was no principled way to say "this word is done, schedule it long-term."

## Decision

Replace per-level success counting with a **Momentum Bands** progression model implemented entirely inside SQL RPCs ([migrations/phase8_momentum_bands.sql](../../migrations/phase8_momentum_bands.sql)):

- **Per-family Bayesian confidence.** Each of 6 cognitive families (form_recognition, meaning_recall, form_production, collocation, semantic_discrimination, contextual_use) carries its own BKT confidence on `user_word_ladder.family_confidence` (JSONB). Each exercise updates the confidence of *its* family only, using `learn_rate` / `slip_rate` BKT update rules.
- **Four rings, not nine levels.** R1 (L1–L2) → R2 (L3–L5) → R3 (L6–L7) → R4 (L8–L9). A word stays in its ring until **every required family for that ring** crosses a confidence threshold (R1/R2: 0.50, R3: 0.65, R4: 0.72).
- **Two threshold gates.** R2→R3 requires passing **Gate A** (3-exercise battery, ≥2/3 correct). R3→R4 requires **Gate B** (same shape, harder threshold).
- **Stress test for mastery.** Once R4 clears and overall p_known ≥ 0.88, the word reaches `pre_mastery` and unlocks an 8-exercise stress test (2 form_production / 1 meaning_recall / 1 form_recognition / 1 collocation / 1 semantic_discrimination / 2 contextual_use, ≥6/8 to pass).
- **FSRS handoff on graduation.** A passed stress test calls `ladder_graduate`, which seeds FSRS state (stability `7 + 21·p_known + 6·stress_bonus`, clamped [7, 34]; difficulty `8 − 5·p_known + family_variance_penalty`, clamped [2, 8.5]; first review at `today + round(0.6·stability)` days). The word transitions `word_state = 'mastered'` and `review_due_at = NULL` — FSRS owns scheduling from here on.
- **Momentum band scheduling.** Pre-mastery, the next review is computed from overall p_known (low/medium → tomorrow, high → +2 days). A first-attempt failure always pulls the review back to tomorrow regardless of band.
- **Lapse path.** A mastered word that fails is demoted to `relearning` with an extra 30% confidence penalty on the failed family and `bkt_apply_lapse_penalty` against `user_vocabulary_knowledge`. FSRS receives a "AGAIN" rating via the in-SQL `fsrs_schedule_review` port.

## Consequences

Easier:
- Graduating words have a principled FSRS bootstrap derived from their acquisition trace, not a hardcoded starting interval.
- The session builder ([get_ladder_session](../../migrations/phase8_momentum_bands.sql)) can target a word's *weakest family in the current ring* instead of just the next level.
- A word's profile is now a 6-vector, surfacing strengths and weaknesses for analytics and frontend UX.
- Concrete-noun routing keeps working: the `ladder_ring_families` helper recomputes required families from `active_levels`, so words that skip collocation levels (5, 8) don't get stuck waiting on a family they can't exercise.

Harder:
- The mental model is bigger. Three different progression mechanisms (ring threshold, gate battery, stress test) coexist. Debugging an apparently stuck word requires looking at family confidences *and* gates_passed *and* ring transitions.
- Schema bloat. `user_word_ladder` carries Phase 4 *and* Phase 8 columns. Several Phase 4 columns (`first_try_success_count`, `first_try_failure_count`, `consecutive_failures`, `last_success_session_date`) are still *written* by `ladder_record_attempt` ([phase8_momentum_bands.sql:664-695](../../migrations/phase8_momentum_bands.sql#L664-L695)) but never *read* by any code path. They are de facto observability metrics, not progression drivers.
- The Python `LadderService` becomes a thin RPC wrapper. All progression logic lives in SQL, which is harder to unit-test than Python.

Constrained:
- All progression-state mutation must go through the three core RPCs (`ladder_record_attempt`, `ladder_pass_gate`, `ladder_graduate`). Any future feature that wants to manipulate ring/family state must add a new RPC or extend an existing one — `user_word_ladder` updates from outside these RPCs would leave family confidence and rings out of sync.
- The `word_state` CHECK constraint is now `('new', 'active', 'gated', 'pre_mastery', 'relearning', 'mastered')`. The Phase 4 values `'fragile'` and `'stable'` were data-migrated to `'active'` ([phase8_momentum_bands.sql:61-68](../../migrations/phase8_momentum_bands.sql#L61-L68)) and can no longer be written.

## Alternatives Considered

- **Keep simple per-level + counters.** Rejected: real attempt patterns show family-level skill is uneven, and a single rail can't capture "strong on recognition, weak on production." The Phase 4 schema would have been enough machinery, but it would not have improved the pedagogy.
- **Pure FSRS from day one.** Rejected: FSRS assumes a card has stable acquisition. For words being actively built, the right scheduling signal is "is the weakest family meeting threshold yet?" — not "what was the recall lag?" The Phase 8 design uses FSRS only after graduation, when stability is a meaningful concept.
- **Per-level BKT.** Rejected as confusion: BKT already tracks overall p_known on `user_vocabulary_knowledge`. Adding nine more BKT tracks per word — one per level — would be expensive and noisy (some levels are skipped for some POS). Six cognitive families (~constant per word) is a cleaner factorisation.

## 2026-05-12 amendment: cross-session gating + ring demotion (Phase 10)

After several weeks of running the pure-confidence model, two refinements were layered on without changing the core architecture ([migrations/phase10_ladder_advancement_demotion.sql](../../migrations/phase10_ladder_advancement_demotion.sql)):

- **Cross-session advancement gating.** Ring advancement now requires both (a) family confidence ≥ threshold AND (b) first-attempt successes on ≥ 2 distinct calendar days for each required family. A new `family_success_dates` JSONB column on `user_word_ladder` carries the per-family date history (trimmed to the most recent 2). Restores the cross-session validation the original wiki spec wanted; closes the "same-day farm to advance" gap.
- **Ring demotion.** When `consecutive_failures` reaches 3 on a family that gates the current ring, the word drops one ring. Only the gate guarding exit from the dropped-into ring resets (gate_a on demote→R2, gate_b on demote→R3); other gates survive as lifetime achievements. R1 is the floor.

These reuse the existing Phase 4 counter columns (`consecutive_failures`, `last_exercised_family`) and add one new column. The lapse path (mastered → relearning) is unchanged. The legacy `first_try_success_count`, `first_try_failure_count`, and `last_success_session_date` columns remain written but unread — flagged for future cleanup.
