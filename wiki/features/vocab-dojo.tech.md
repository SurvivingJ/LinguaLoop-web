---
title: Vocab Dojo — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./vocab-dojo.md
last_updated: 2026-05-11
dependencies:
  - "migrations/phase8_momentum_bands.sql — get_ladder_session, ladder_record_attempt, ladder_pass_gate, ladder_graduate"
  - "services/vocabulary_ladder/ladder_service.py — Python wrapper + battery assembly"
  - "services/vocabulary_ladder/config.py — constants"
  - "routes/vocab_dojo.py — six endpoints"
  - "user_word_ladder table (Phase 4 + Phase 8 columns)"
  - "user_vocabulary_knowledge table"
  - "user_flashcards table"
  - "user_exercise_history table (anti-repetition)"
  - "exercises, dim_word_senses, dim_vocabulary tables"
breaking_change_risk: medium
---

# Vocab Dojo — Technical Specification

## Architecture Overview

The dojo is a single SQL-RPC-driven surface. All scheduling, family targeting, anti-repetition, and variant alternation live in `get_ladder_session`. Python only orchestrates lazy ladder-row initialisation, prepares jumbled-sentence content, and dispatches gate / stress-test batteries.

```
GET /api/vocab-dojo/session?language_id=...&count=20
  → _ensure_ladder_rows(user, language)        (lazy init)
  → db.rpc('get_ladder_session', user, language, count)
      WITH candidates, scored, top_words, seen_today,
           word_exercises, selected → 15-column TABLE
  → For each exercise: attach LADDER_LEVELS[level] name/family
  → For 'jumbled_sentence' content lacking 'chunks':
      prepare_jumbled_content(content, language)   (backend tokenisation)
  → Return { exercises: [...], count: N }

POST /api/vocab-dojo/attempt
  → LadderService.record_attempt(...)
  → db.rpc('ladder_record_attempt', ...)
  → Return RPC's JSONB payload unchanged

POST /api/vocab-dojo/gate
  → LadderService.assemble_gate(user, sense, language, gate_name)
  → _fetch_exercises_for_levels(sense, language, ring_levels, battery_size)
      Variant-diverse selection

POST /api/vocab-dojo/gate/result
  → If passed:  ladder_pass_gate (advances ring, sets review_due_at=tomorrow)
  → If failed:  client should already have called record_attempt(context='gate')
                for each battery exercise; this route just returns shape
                { gate, passed: false, word_state: 'active' }

POST /api/vocab-dojo/stress-test
  → LadderService.assemble_stress_test(user, sense, language)
  → Compose 8 exercises by family per STRESS_TEST['composition'],
    falling back to highest available level when family unavailable

POST /api/vocab-dojo/stress-test/result
  → If passed: ladder_graduate (seeds FSRS, sets word_state='mastered')
  → If failed: returns { word_state: 'relearning', stress_test_score, passed: false }

GET /api/vocab-dojo/word/<sense_id>/exercises?language_id=...
  → Preview surface: returns all ladder exercises for a sense + word_assets + metadata
```

## RPC: `get_ladder_session`

[migrations/phase8_momentum_bands.sql:1005-1184](../../migrations/phase8_momentum_bands.sql#L1005-L1184)

```sql
CREATE OR REPLACE FUNCTION public.get_ladder_session(
    p_user_id uuid,
    p_language_id smallint,
    p_count integer DEFAULT 20
) RETURNS TABLE (
    out_sense_id        integer,
    out_exercise_id     uuid,
    out_exercise_type   text,
    out_content         jsonb,
    out_ladder_level    integer,
    out_family          text,
    out_p_known         numeric,
    out_word_state      text,
    out_lemma           text,
    out_definition      text,
    out_pronunciation   text,
    out_variant         text,        -- 'A' | 'B'
    out_is_gate         boolean,     -- word_state = 'gated'
    out_is_stress_test  boolean,     -- word_state = 'pre_mastery'
    out_priority        numeric
)
```

### CTE Pipeline

1. **candidates** — `user_word_ladder` rows for the user with `word_state ∈ ('new','active','gated','pre_mastery','relearning')` AND `review_due_at <= now()` AND at least one active ladder exercise. Computes:
   - `p_known := ladder_compute_p_known(family_confidence)`
   - `overdue_score := LEAST(7, days_overdue) / 7.0`
   - `weakness_score := MAX(0, threshold − min_family_confidence)` where threshold is 0.50 / 0.50 / 0.65 / 0.72 by ring
   - `gate_urgency := word_state='gated' ? 1 : 0`
   - `novelty_score := last_exercised_family IS NULL ? 0.5 : 0`
   - `relapse_score := word_state='relearning' ? 1 : 0`

2. **scored** — adds priority and target_family:
   ```sql
   priority := 0.35·overdue + 0.25·weakness + 0.20·gate + 0.10·novelty + 0.10·relapse
   target_family := (SELECT f FROM unnest(ladder_ring_families(current_ring, active_levels)) f
                     ORDER BY family_confidence[f] ASC LIMIT 1)
   ```

3. **top_words** — `ORDER BY priority DESC LIMIT p_count`.

4. **seen_today** — `SELECT DISTINCT exercise_id FROM user_exercise_history WHERE user_id = p_user_id AND language_id = p_language_id AND session_date = CURRENT_DATE`.

5. **word_exercises** — joins `exercises` (active, ladder_level IS NOT NULL) for each top word; `ROW_NUMBER() OVER (PARTITION BY sense_id ORDER BY ...)`:
   - target-family match first
   - exercises not seen today next
   - variant-alternation third (prefer variant != last-seen for this sense)
   - random tie-break

6. **selected** — `WHERE rn = 1`.

7. Final SELECT joins `dim_word_senses` + `dim_vocabulary` for lemma/definition/pronunciation, returns ordered by priority DESC.

### Performance Notes

- All filters and joins are indexed: `idx_user_word_ladder_review_due`, `idx_user_word_ladder_state`, `idx_exercises_ladder`, `idx_ueh_anti_repeat`, the PK on `dim_word_senses`.
- Empirical: ≤ 50ms for a 20-exercise session on Supabase free tier with ~5k user_word_ladder rows.

### Frontend Branching

- `out_is_gate = true` → the UI should call `/api/vocab-dojo/gate` to fetch a 3-exercise battery instead of serving the single exercise from this row.
- `out_is_stress_test = true` → the UI should call `/api/vocab-dojo/stress-test` for the 8-exercise battery.
- Otherwise → serve the exercise normally and POST results to `/api/vocab-dojo/attempt`.

## RPC: `ladder_record_attempt`

See [[algorithms/vocabulary-ladder.tech]] and [[database/rpcs.tech]] for the full step-by-step. Summary signature:

```
ladder_record_attempt(
    p_user_id uuid, p_sense_id integer, p_exercise_id uuid,
    p_is_correct boolean, p_is_first_attempt boolean,
    p_time_taken_ms integer DEFAULT NULL,
    p_language_id smallint DEFAULT NULL,
    p_exercise_type text DEFAULT NULL,
    p_ladder_level integer DEFAULT NULL,
    p_exercise_context text DEFAULT 'standard'  -- 'standard' | 'gate' | 'stress_test'
) RETURNS jsonb
```

Returns: `is_correct, family, family_confidence, p_known_overall, current_ring, word_state, review_due_at, requeue, gate_pending, stress_test_ready, bkt_p_known, is_lapse`.

## RPC: `ladder_pass_gate` and `ladder_graduate`

Brief signatures (full definitions in [[database/rpcs.tech]]):

```
ladder_pass_gate(p_user_id, p_sense_id, p_gate_name)
  → marks gates_passed[name], current_ring := 3|4, recomputes word_state,
    review_due_at = tomorrow
  → returns: { gate, passed: true, new_ring, word_state, p_known_overall }

ladder_graduate(p_user_id, p_sense_id, p_stress_test_score, p_language_id)
  → seeds FSRS stability/difficulty/due_date from acquisition trace
  → word_state := 'mastered', review_due_at := NULL
  → UPSERT user_flashcards (state='review')
  → returns: { word_state, stress_test_score, fsrs_stability, fsrs_difficulty,
              fsrs_due_date, p_known_overall }
```

## Python: `LadderService.assemble_gate` and `assemble_stress_test`

[services/vocabulary_ladder/ladder_service.py:94-178](../../services/vocabulary_ladder/ladder_service.py#L94-L178)

```python
def assemble_gate(user_id, sense_id, language_id, gate_name) -> list[dict]:
    gate_config = GATES[gate_name]                           # battery_size, etc.
    target_ring = gate_config['unlocks_ring']
    ladder_row = self._get_ladder_row(user_id, sense_id)
    active_levels = ladder_row['active_levels'] or list(range(1, 10))
    ring_levels = [lv for lv in RINGS[target_ring]['levels'] if lv in active_levels]
    return self._fetch_exercises_for_levels(
        sense_id, language_id, ring_levels, gate_config['battery_size']
    )

def assemble_stress_test(user_id, sense_id, language_id) -> list[dict]:
    composition = STRESS_TEST['composition']  # {family: count}
    ladder_row = self._get_ladder_row(user_id, sense_id)
    active_levels = ladder_row['active_levels'] or list(range(1, 10))
    all_needed_levels = []
    for family, count in composition.items():
        family_levels = get_levels_for_family(family, active_levels) or [active_levels[-1]]
        for i in range(count):
            all_needed_levels.append(family_levels[i % len(family_levels)])
    return self._fetch_exercises_for_levels(
        sense_id, language_id, all_needed_levels, len(all_needed_levels)
    )
```

`_fetch_exercises_for_levels` groups by ladder level, picks one per level preferring an unseen variant within the call. (No `user_exercise_history` consultation here — the anti-repetition for batteries is the variant choice, not a date-bounded filter.)

## Anti-Repetition

Two layers:

1. **`get_ladder_session` seen-today filter** — `LEFT JOIN seen_today st ON st.exercise_id = e.id`, then `ORDER BY CASE WHEN st.exercise_id IS NULL THEN 0 ELSE 1 END` in the per-word ranking. The CTE doesn't *eliminate* seen-today exercises (then a learner with only 1 exercise per word would never see anything), it deprioritises them.
2. **`exercises.tags->>'variant'` alternation** — the rank correlated subquery compares against the most recent attempt's ... well, it compares against `exercise_id::text`, which is functionally an "always alternate when both variants are present" rule because no UUID equals `'A'` or `'B'`. The intended behaviour is preserved when paired with the seen-today rule.

## Variant Generation

A/B variants are produced by Prompt 2 and Prompt 3 from different sentence indices in the 10-sentence Prompt 1 output. `exercises.tags` carries `{"variant": "A" | "B"}`. The session builder reads `tags->>'variant'` to alternate.

```
P1 generates sentences[0..9]
P2_A uses sentences[0..3] for L1/L3/L5/L6 distractors
P2_B uses sentences[6..9] for L1/L3/L5/L6 distractors
P3_A uses sentences[1, 4, 4] for L4/L7/L8
P3_B uses sentences[7, 0, 8] for L4/L7/L8
```

(Full assignments in [services/vocabulary_ladder/config.py SENTENCE_ASSIGNMENTS_A/B](../../services/vocabulary_ladder/config.py).)

## Endpoint Surface

| Method | Path | Body / params | Purpose |
|--------|------|---------------|---------|
| GET  | `/api/vocab-dojo/session` | `language_id` (req), `count` (default 20, max 50) | `get_ladder_session` RPC; prepares jumbled content; enriches with ladder_name/family |
| POST | `/api/vocab-dojo/attempt` | `exercise_id`, `sense_id`, `is_correct`, `is_first_attempt`, `time_taken_ms?`, `language_id?`, `exercise_type?`, `ladder_level?`, `exercise_context?` | `ladder_record_attempt` RPC |
| GET  | `/api/vocab-dojo/word/<sense_id>/exercises` | `language_id` | Word preview: all ladder exercises + word_assets + metadata |
| POST | `/api/vocab-dojo/gate` | `sense_id`, `language_id`, `gate_name` (`'gate_a'\|'gate_b'`) | Assemble gate battery (Python) |
| POST | `/api/vocab-dojo/gate/result` | `sense_id`, `gate_name`, `passed` | Pass → `ladder_pass_gate`; Fail → return-only |
| POST | `/api/vocab-dojo/stress-test` | `sense_id`, `language_id` | Assemble 8-exercise stress test battery (Python) |
| POST | `/api/vocab-dojo/stress-test/result` | `sense_id`, `language_id`, `score` (0–1), `passed` | Pass → `ladder_graduate`; Fail → return-only |

All routes require Supabase JWT (`@supabase_jwt_required`).

## Lazy Ladder-Row Init

[routes/vocab_dojo.py:376-418](../../routes/vocab_dojo.py#L376-L418)

```
_ensure_ladder_rows(db, user, language):
  SELECT DISTINCT word_sense_id FROM exercises
    WHERE language_id=lang AND is_active AND ladder_level IS NOT NULL
  SELECT sense_id FROM user_word_ladder
    WHERE user_id=user AND sense_id IN (above)
  For each missing sense_id:
    LadderService.init_ladder(user, sense, language)
```

`init_ladder` derives `active_levels` from semantic_class, seeds `current_level` from BKT p_known via `bkt_to_starting_level`, and UPSERTs the row with `word_state='new'`, `current_ring=1`. Family confidences default to 0.10 each. The `current_level` value is metadata; the dojo uses `current_ring` + `family_confidence` for actual progression.

## Performance

- `get_ladder_session(p_count=20)` resolves in <50ms on indexed tables (~5k ladder rows).
- `_ensure_ladder_rows` is O(senses with exercises) per session request. For < 200 senses this is < 50ms; consider caching the missing-set per request if it grows.
- `assemble_stress_test` does one query per family in the worst case (~6 small queries). Cached per session would be a nice future optimisation but not necessary at current scale.

## Future Direction

- **Daily-session merge into SQL** — ✅ Shipped (Phase 9, 2026-05-12). `get_exercise_session` RPC mirrors this design and delegates ladder picks to `get_ladder_session` internally. See [[algorithms/ladder-implementation-analysis]] and [[database/rpcs.tech]].
- **Level 10 capstone** — `contextual_use` family is weighted but has no live exercise. Stress test composition reserves 2/8 slots for it. Until shipped, the stress-test assembler falls back to the highest available level for those slots.

## Related Pages

- [[features/vocab-dojo]] — Prose description
- [[algorithms/vocabulary-ladder]] — Ring/family/gate model
- [[algorithms/vocabulary-ladder.tech]] — Full ladder spec
- [[algorithms/ladder-implementation-analysis]] — Audit + improvement priorities
- [[features/exercises.tech]] — Exercise table schema
- [[features/flashcards.tech]] — FSRS handoff
- [[database/schema.tech]] — `user_word_ladder`, `user_exercise_history` DDL
- [[database/rpcs.tech]] — RPC definitions
- [[decisions/ADR-005-momentum-bands]] — Why this scheduling shape
