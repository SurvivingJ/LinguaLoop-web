---
title: Vocabulary Ladder — Technical Specification
type: algorithm-tech
status: in-progress
prose_page: ./vocabulary-ladder.md
last_updated: 2026-05-12
dependencies:
  - "services/vocabulary_ladder/ — LadderService, asset pipeline, config"
  - "migrations/phase8_momentum_bands.sql — Momentum Bands core RPCs"
  - "migrations/phase10_ladder_advancement_demotion.sql — cross-session gating + demotion"
  - "routes/vocab_dojo.py — six endpoints (session/attempt/word/gate/stress-test)"
  - "user_word_ladder table (Phase 4 + Phase 8 columns)"
  - "user_vocabulary_knowledge table"
  - "user_flashcards table"
  - "user_exercise_history table"
  - "exercises, word_assets, dim_word_senses, dim_vocabulary tables"
breaking_change_risk: high
---

# Vocabulary Ladder — Technical Specification

## Architecture Overview

Progression state and progression logic live in PostgreSQL. `LadderService` is a thin wrapper around three RPCs (`ladder_record_attempt`, `ladder_pass_gate`, `ladder_graduate`) plus session-builder reads against `get_ladder_session`. Asset generation is a separate offline pipeline.

```
Generation (offline, per word)
  VocabAssetPipeline.generate_for_sense(sense_id)
    Prompt 1 (Gemini Flash Lite): pos, semantic_class, definition, collocate,
        IPA, syllable count, 10 sentences, morphological forms
    Prompt 2 (Claude Sonnet): L1 phonetic, L3 cloze, L5 collocation gap,
        L6 semantic discrimination — optional A/B variants
    Prompt 3 (Claude Sonnet): L4 morphology, L7 spot-incorrect, L8 collocation
        repair — optional A/B variants
    VocabAssetValidator → word_assets → exercises rows (ladder_level filled in)

Runtime (per attempt / per session)
  GET /api/vocab-dojo/session
    → routes/vocab_dojo.py:_ensure_ladder_rows (lazy-init user_word_ladder rows)
    → db.rpc('get_ladder_session', user, language, count)
        → CTE pipeline: candidates → priority scoring → top words →
                        seen-today filter → variant-aware exercise pick

  POST /api/vocab-dojo/attempt
    → LadderService.record_attempt(...)
    → db.rpc('ladder_record_attempt', ...)  -- atomic
        → resolve metadata → lock user_word_ladder row →
          insert exercise_attempts (trigger syncs user_exercise_history) →
          family BKT update → momentum-band / ring / lapse branch →
          UPDATE user_word_ladder → BKT update on user_vocabulary_knowledge

  POST /api/vocab-dojo/gate, /gate/result
    → LadderService.assemble_gate / pass_gate

  POST /api/vocab-dojo/stress-test, /stress-test/result
    → LadderService.assemble_stress_test / graduate
        → ladder_graduate seeds FSRS state and marks word_state='mastered'
```

The daily-mixed-session path (`/api/exercises/session` → `ExerciseSessionService`) is a separate SQL surface: the `get_exercise_session` RPC ([migrations/phase9_get_exercise_session.sql](../../migrations/phase9_get_exercise_session.sql)) calls `get_ladder_session` internally to source ladder content (capped at 5 picks per daily session). Single source of truth for ladder selection. See [[algorithms/ladder-implementation-analysis.tech]] for the full daily-session architecture.

## Cognitive Families

Six families. Each ladder level maps to exactly one. Each attempt updates exactly one family's confidence.

```python
# services/vocabulary_ladder/config.py
FAMILY_WEIGHTS = {
    'form_recognition':         0.12,
    'meaning_recall':           0.18,
    'form_production':          0.20,
    'collocation':              0.16,
    'semantic_discrimination':  0.16,
    'contextual_use':           0.18,  # reserved for future L10 capstone
}
```

`p_known_overall = Σ(family_weight × family_confidence)`. Mirrored in SQL by `ladder_compute_p_known(p_fc jsonb)` for use inside RPCs.

## Level → Ring → Family Map

```python
# services/vocabulary_ladder/config.py — LADDER_LEVELS
1: phonetic_recognition    → R1 / form_recognition
2: definition_match        → R1 / form_recognition
3: cloze_completion        → R2 / meaning_recall
4: morphology_slot         → R2 / form_production
5: collocation_gap_fill    → R2 / collocation
6: semantic_discrimination → R3 / semantic_discrimination
7: spot_incorrect_sentence → R3 / semantic_discrimination
8: collocation_repair      → R4 / collocation
9: jumbled_sentence        → R4 / form_production
```

SQL helpers in `phase8_momentum_bands.sql`:
- `ladder_get_family(level int) → text` — IMMUTABLE
- `ladder_get_ring(level int) → int` — IMMUTABLE
- `ladder_ring_families(ring int, active_levels int[]) → text[]` — IMMUTABLE; consults active_levels so concrete nouns don't require collocation in R2.

## Rings, Gates, Stress Test

```python
RINGS = {
    1: {'levels': [1, 2],    'families': {'form_recognition'},
        'unlock': None},
    2: {'levels': [3, 4, 5], 'families': {'meaning_recall', 'form_production', 'collocation'},
        'unlock': 'r1_cleared'},
    3: {'levels': [6, 7],    'families': {'semantic_discrimination'},
        'unlock': 'gate_a'},
    4: {'levels': [8, 9],    'families': {'collocation', 'form_production'},
        'unlock': 'gate_b'},
}

GATES = {
    'gate_a': {'after_ring': 2, 'unlocks_ring': 3,
               'min_p_known': 0.72, 'min_family_confidence': 0.50,
               'battery_size': 3, 'pass_threshold': 2, 'require_production': True},
    'gate_b': {'after_ring': 3, 'unlocks_ring': 4,
               'min_p_known': 0.84, 'min_family_confidence': 0.65,
               'battery_size': 3, 'pass_threshold': 2, 'require_production': True},
}

STRESS_TEST = {
    'min_p_known': 0.88, 'min_family_confidence': 0.72,
    'battery_size': 8, 'pass_threshold': 6,
    'require_production': True, 'require_contextual': True,
    'max_zero_families': 1,
    'composition': {
        'form_production': 2, 'meaning_recall': 1, 'form_recognition': 1,
        'collocation': 1, 'semantic_discrimination': 1, 'contextual_use': 2,
    },
}
```

Ring-clearing thresholds (canonical, in [phase8_momentum_bands.sql:581-585](../../migrations/phase8_momentum_bands.sql#L581-L585)):

| Ring | Required family confidence | Notes |
|------|----------------------------|-------|
| 1, 2 | ≥ 0.50 | Gate A is checked when R2 clears |
| 3 | ≥ 0.65 | Gate B is checked when R3 clears |
| 4 | ≥ 0.72 | Stress test threshold (same as STRESS_TEST.min_family_confidence) |

**Cross-session advancement gate (Phase 10).** In addition to the confidence threshold, every required family must have first-attempt successes on at least 2 distinct calendar days. The history is stored in `user_word_ladder.family_success_dates` (JSONB), trimmed to the most recent 2 dates per family. The check uses the in-memory mutation of `family_success_dates` so the same attempt that adds the second date can clear the ring.

Pre-mastery additionally requires *every active family*'s confidence ≥ 0.72 (the stress-test-ready check, [phase8_momentum_bands.sql:634-658](../../migrations/phase8_momentum_bands.sql#L634-L658)).

### Ring Demotion (Phase 10)

[migrations/phase10_ladder_advancement_demotion.sql](../../migrations/phase10_ladder_advancement_demotion.sql)

Triggered inside `ladder_record_attempt` after the word_state computation. Conditions:

- `p_is_correct = false AND p_is_first_attempt = true`
- `word_state NOT IN ('mastered', 'new')` — `mastered` follows the lapse path instead; `new` is the introductory state and isn't demoted.
- `current_ring > 1` — R1 is the floor.
- The failing family is in `ladder_ring_families(current_ring, active_levels)` — only families that *gate* the current ring drive demotion.
- `consecutive_failures` (post-update value, per-family via `last_exercised_family`) reaches 3.

Effects:

- `current_ring := current_ring − 1`.
- The gate guarding exit from the dropped-into ring resets: `gate_a := false` on demote→R2, `gate_b := false` on demote→R3. Other gates are lifetime achievements.
- `family_success_dates` for the demoted-into-ring required families is cleared (`'[]'::jsonb`). Cross-session stability must be re-established.
- `consecutive_failures := 0`.
- `word_state := 'active'` (clears any `gated` / `pre_mastery`).

## Family BKT Update

```python
FAMILY_BKT_RATES = {
    'standard':    {'learn': 0.15, 'slip': 0.12},
    'gate':        {'learn': 0.18, 'slip': 0.10},  # gentler on failure
    'stress_test': {'learn': 0.20, 'slip': 0.12},  # bonus on success
}
```

On correct: `new = old + (1 − old) · learn_rate`.
On incorrect: `new = old · (1 − slip_rate)`.
Clamped to `[0.02, 0.98]`. Implemented in [phase8_momentum_bands.sql:489-513](../../migrations/phase8_momentum_bands.sql#L489-L513). Context (`'standard' | 'gate' | 'stress_test'`) is passed through `LadderService.record_attempt(..., exercise_context=...)`.

## Momentum Band Scheduling

```python
MOMENTUM_BANDS = [
    {'name': 'low',    'max_p_known': 0.45, 'interval_days': 1},
    {'name': 'medium', 'max_p_known': 0.75, 'interval_days': 1},
    {'name': 'high',   'max_p_known': 1.01, 'interval_days': 2},
]
```

SQL implementation at [phase8_momentum_bands.sql:566-577](../../migrations/phase8_momentum_bands.sql#L566-L577). A first-attempt failure overrides the band and always schedules `review_due_at = tomorrow`.

## Lapse Path

`word_state = 'mastered'` + `is_correct = false` triggers [phase8_momentum_bands.sql:525-558](../../migrations/phase8_momentum_bands.sql#L525-L558):

1. Standard slip penalty on the failed family.
2. Additional 30% multiplicative penalty on the same family.
3. `word_state = 'relearning'`, `review_due_at = tomorrow`.
4. If a `user_flashcards` row exists, `fsrs_schedule_review(..., p_rating=1, ...)` runs and updates stability / difficulty / due_date / state / lapses.
5. After the main UPDATE, `bkt_apply_lapse_penalty(user, sense)` runs against `user_vocabulary_knowledge`.

## Graduation: FSRS Seeding

`ladder_graduate(p_user_id, p_sense_id, p_stress_test_score, p_language_id)`:

```
stress_bonus    = 1.0 if score ≥ 0.90 else 0.5 if ≥ 0.80 else 0.0
stability       = clamp(7 + 21·p_known + 6·stress_bonus, 7, 34)
family_stddev   = stddev_pop of the 5 active family confidences
variance_penalty= min(1.5, family_stddev · 4)
difficulty      = clamp(8 − 5·p_known + variance_penalty, 2, 8.5)
first_due       = today + round(0.6 · stability)
```

UPSERT into `user_flashcards` (`state='review'`, reps≥1, lapses=0). Side effect: `user_word_ladder.word_state = 'mastered'`, `review_due_at = NULL`, `stress_test_score = score`.

[phase8_momentum_bands.sql:836-933](../../migrations/phase8_momentum_bands.sql#L836-L933).

## Schema: `user_word_ladder`

```sql
CREATE TABLE user_word_ladder (
    -- Original (Phase 1/2)
    user_id                    uuid NOT NULL REFERENCES users(id),
    sense_id                   integer NOT NULL REFERENCES dim_word_senses(id),
    current_level              integer NOT NULL DEFAULT 1 CHECK (current_level BETWEEN 1 AND 9),
    active_levels              integer[] NOT NULL DEFAULT '{1,2,3,4,5,6,7,8,9}',
    updated_at                 timestamptz NOT NULL DEFAULT now(),

    -- Phase 4 (counters; written by Phase 8 RPC, never read for progression)
    first_try_success_count    integer NOT NULL DEFAULT 0,
    first_try_failure_count    integer NOT NULL DEFAULT 0,
    consecutive_failures       integer NOT NULL DEFAULT 0,
    total_attempts             integer NOT NULL DEFAULT 0,
    word_state                 text NOT NULL DEFAULT 'active',
    last_success_session_date  date,
    review_due_at              timestamptz,

    -- Phase 8 (Momentum Bands — canonical progression state)
    family_confidence          jsonb NOT NULL DEFAULT
                               '{"form_recognition":0.10,"meaning_recall":0.10,"form_production":0.10,"collocation":0.10,"semantic_discrimination":0.10,"contextual_use":0.10}',
    gates_passed               jsonb NOT NULL DEFAULT '{"gate_a":false,"gate_b":false}',
    current_ring               integer NOT NULL DEFAULT 1 CHECK (current_ring BETWEEN 1 AND 4),
    stress_test_score          real,
    last_exercised_family      text,

    -- Phase 10 (cross-session gating + demotion)
    family_success_dates       jsonb NOT NULL DEFAULT
                               '{"form_recognition":[],"meaning_recall":[],"form_production":[],"collocation":[],"semantic_discrimination":[],"contextual_use":[]}',

    PRIMARY KEY (user_id, sense_id)
);

-- Phase 8 CHECK constraint (replaces Phase 4 fragile/stable):
ALTER TABLE user_word_ladder
    ADD CONSTRAINT user_word_ladder_word_state_check
    CHECK (word_state IN ('new','active','gated','pre_mastery','relearning','mastered'));

-- Indexes:
CREATE INDEX idx_user_word_ladder_review_due ON user_word_ladder(user_id, review_due_at)
    WHERE review_due_at IS NOT NULL;
CREATE INDEX idx_user_word_ladder_state ON user_word_ladder(user_id, word_state);
CREATE INDEX idx_user_word_ladder_ring  ON user_word_ladder(user_id, current_ring);
```

The Phase 4 counters are updated on every attempt by [phase8_momentum_bands.sql:664-695](../../migrations/phase8_momentum_bands.sql#L664-L695) but no Phase 8 code reads them. They are de facto observability metrics.

## RPC Surface (from [migrations/phase8_momentum_bands.sql](../../migrations/phase8_momentum_bands.sql))

### `ladder_record_attempt(...)` — section 8.6 (extended by Phase 10)

Atomic write path for one exercise attempt.

- **Args:** `p_user_id uuid, p_sense_id int, p_exercise_id uuid, p_is_correct bool, p_is_first_attempt bool, p_time_taken_ms int?, p_language_id smallint?, p_exercise_type text?, p_ladder_level int?, p_exercise_context text` (default `'standard'`; one of `'standard' | 'gate' | 'stress_test'`)
- **Returns JSONB:** `is_correct, family, family_confidence, family_success_sessions, p_known_overall, current_ring, word_state, review_due_at, requeue, gate_pending ('gate_a' | 'gate_b' | null), stress_test_ready, bkt_p_known, is_lapse, demoted`
  - `family_success_sessions` *(new in Phase 10)*: per-family count of distinct calendar days with first-attempt successes, capped at 2 by the storage trim. Frontend can use this to show "one more session" advancement progress.
  - `demoted` *(new in Phase 10)*: true if this attempt triggered a ring drop.
- **Side effects:** locks the `user_word_ladder` row `FOR UPDATE`; inserts `exercise_attempts` (Phase 4 trigger syncs to `user_exercise_history`); updates `user_word_ladder` (all Phase 8 + Phase 4 counter columns + Phase 10 `family_success_dates`); UPSERTs `user_vocabulary_knowledge`; on lapse, calls `fsrs_schedule_review` and updates `user_flashcards`, then `bkt_apply_lapse_penalty`.
- **Phase 10 additions:** cross-session advancement gate (ring clears only if every required family has first-attempt successes on ≥ 2 distinct calendar days); ring demotion when `consecutive_failures ≥ 3` on a ring-gating family, with selective gate reset (only the exit gate of the dropped-into ring) and `family_success_dates` reset for the demoted-into-ring required families.

### `ladder_pass_gate(p_user_id, p_sense_id, p_gate_name)` — section 8.7

Marks a gate as passed and advances the ring. `p_gate_name ∈ {'gate_a','gate_b'}`. Sets `current_ring = 3 | 4`, recomputes `word_state` (may become `pre_mastery`), `review_due_at = tomorrow`. Gate failure is not a separate RPC — Python calls `ladder_record_attempt` for each failed battery exercise with `exercise_context = 'gate'`.

### `ladder_graduate(p_user_id, p_sense_id, p_stress_test_score, p_language_id)` — section 8.8

Graduation handoff. Seeds FSRS (see Graduation section above), sets `word_state='mastered'`, `stress_test_score = score`, `review_due_at = NULL`. UPSERTs `user_flashcards`.

### `get_ladder_session(p_user_id, p_language_id, p_count)` — section 8.10

Session builder. Returns up to `p_count` candidate exercises ordered by priority.

```
priority = 0.35·overdue_score + 0.25·weakness_score
         + 0.20·gate_urgency  + 0.10·novelty_score + 0.10·relapse_score
```

- `overdue_score` = days overdue / 7 (capped at 1.0)
- `weakness_score` = `(ring_threshold − min_family_confidence)` floored at 0
- `gate_urgency` = 1.0 if `word_state='gated'` else 0
- `novelty_score` = 0.5 if `last_exercised_family IS NULL` else 0
- `relapse_score` = 1.0 if `word_state='relearning'` else 0

The CTE pipeline:
1. **candidates** — `word_state ∈ ('new','active','gated','pre_mastery','relearning')` AND `review_due_at <= now()` AND at least one active ladder exercise exists.
2. **scored** — adds priority + target family (weakest in current ring).
3. **top_words** — top N by priority.
4. **seen_today** — anti-repetition (exercises already in `user_exercise_history` for today).
5. **word_exercises** — joins `exercises`, picks one per word, ranking by: target-family match → unseen-today → variant-alternation → random tie-break.
6. Joins lemma/definition/pronunciation, returns 15 columns prefixed `out_`.

Frontend ergonomics: returns `out_is_gate` (true if `word_state='gated'`) and `out_is_stress_test` (true if `word_state='pre_mastery'`) so the UI can branch to the gate/stress-test flow inline. Gate batteries themselves are assembled by `LadderService.assemble_gate` (Python, not SQL).

### Helpers

- `ladder_get_family(level)` — pure level → family map.
- `ladder_get_ring(level)` — pure level → ring map.
- `ladder_ring_families(ring, active_levels)` — required families given active levels (concrete-noun aware).
- `ladder_compute_p_known(p_fc jsonb)` — weighted aggregate.
- `fsrs_schedule_review(stability, difficulty, last_review, reps, lapses, state, rating, review_date)` — PostgreSQL port of `services/vocabulary/fsrs.py`; uses FSRS-4.5 default weights inlined in the function body.

## Python Surface (`services/vocabulary_ladder/`)

`LadderService` in [ladder_service.py](../../services/vocabulary_ladder/ladder_service.py):

- `record_attempt(...)` → thin `ladder_record_attempt` wrapper. All progression logic is in SQL.
- `init_ladder(user, sense, language)` → uses `bkt_to_starting_level(p_known, active_levels)` to seed `current_level` for new rows. **Note:** the seeded `current_level` is only used for backwards-compatibility metadata; the actual progression is driven by `current_ring` + `family_confidence`.
- `assemble_gate(user, sense, language, gate_name)` → fetches up to `GATES[gate_name].battery_size` exercises from the unlocked ring's levels, preferring unseen A/B variants.
- `pass_gate(...)` → `ladder_pass_gate` wrapper.
- `assemble_stress_test(user, sense, language)` → composes the 8-exercise battery per `STRESS_TEST.composition`, falling back to the highest available level when a family has no live exercises.
- `graduate(...)` → `ladder_graduate` wrapper.

Internals: `_get_ladder_row`, `_get_active_levels_for_sense` (reads `dim_vocabulary.semantic_class`, falls back to all 9 levels), `_fetch_exercises_for_levels` (variant-diverse picker).

`config.py` exposes the level/family/ring/gate/stress-test constants used by Python, plus utility functions (`compute_active_levels`, `bkt_to_starting_level`, `next_active_level`, `prev_active_level`, `get_ring_for_level`, `get_family_for_level`, `get_levels_for_ring`, `get_levels_for_family`, `compute_p_known_overall`, `get_momentum_band`, `compute_word_state`).

## Asset Pipeline (offline)

Unchanged from the original 3-prompt pipeline — see [[features/exercises.tech]] and [[features/exercise-generation-prompts]]. Phase 8 changed two things:

- **Prompt 1 now generates 10 sentences (was 6).** See `prompt_templates` row `vocab_prompt1_core` v2 inserted at the bottom of `phase8_momentum_bands.sql`. The extra sentences feed A/B variants.
- **A/B variants.** `word_assets.asset_type` CHECK accepts `prompt2_exercises_A`, `prompt2_exercises_B`, `prompt3_transforms_A`, `prompt3_transforms_B` in addition to the originals. Variant A uses sentence indices 0–5 (the legacy default); Variant B uses 6–9 + select reuse. Variant choice on an exercise is recorded in `exercises.tags->>'variant'` and consumed by `get_ladder_session` for alternation.

## Validation Pipeline

Unchanged — schema → linguistic → pedagogical → content quality. Invalid assets get `is_valid=false` + a `validation_errors` array and never reach the runtime path. See [[features/exercises.tech]] for details.

## Related Pages

- [[algorithms/vocabulary-ladder]] — Prose description
- [[algorithms/ladder-implementation-analysis.tech]] — 2026-05-11 code audit
- [[features/exercises.tech]] — Exercise table schema
- [[features/vocab-dojo.tech]] — Session builder + endpoints
- [[features/flashcards.tech]] — FSRS scheduler (Python source for `fsrs_schedule_review`)
- [[database/schema.tech]] — Full `user_word_ladder` DDL
- [[database/rpcs.tech]] — Full RPC definitions
- [[decisions/ADR-005-momentum-bands]] — Decision record
