---
title: ELO System — Implementation Analysis (Technical)
type: algorithm-tech
status: in-progress
prose_page: ./elo-implementation-analysis.md
last_updated: 2026-04-11
dependencies:
  - "calculate_elo_rating() — plpgsql IMMUTABLE"
  - "calculate_volatility_multiplier() — plpgsql IMMUTABLE"
  - "process_test_submission() — plpgsql SECURITY DEFINER"
  - "get_recommended_test() — plpgsql SECURITY DEFINER"
  - "get_recommended_tests() — plpgsql SECURITY DEFINER"
  - "get_vocab_recommendations() — plpgsql SECURITY DEFINER STABLE"
  - "update_skill_attempts_count() — trigger function"
  - "user_skill_ratings table"
  - "test_skill_ratings table"
  - "test_attempts table"
breaking_change_risk: medium
---

# ELO System — Implementation Analysis (Technical)

## Architecture Map

```
User submits test answers (JSON array of question_id + selected_answer)
  │
  └─► process_test_submission() [plpgsql, SECURITY DEFINER]
        │
        ├── Validates auth: p_user_id == auth.uid()
        ├── Validates inputs: p_responses not empty
        ├── Server-side grading: joins temp table to questions
        ├── Idempotency check: idempotency_key in test_attempts
        ├── Token cost: get_test_token_cost()
        ├── Score calculation: count correct / total
        │
        ├── GET OR CREATE user_skill_ratings (default ELO 1200)
        ├── GET OR CREATE test_skill_ratings (default ELO 1400)
        │
        ├── IF first attempt:
        │     ├── Inline ELO calc (NOT calling calculate_elo_rating!)  ◄── BUG
        │     ├── UPDATE user_skill_ratings (elo, tests_taken, last_test_date)
        │     └── UPDATE test_skill_ratings (elo, total_attempts)
        │
        ├── INSERT test_attempts (with elo_before/after snapshots)
        ├── UPSERT user_languages (total_tests_taken, last_test_date)
        │
        └── RETURN jsonb with score, ELO changes, question results

Post-insert triggers:
  test_attempts INSERT → update_skill_attempts_count() → recount total_attempts
  test_attempts INSERT → update_test_attempts_count() → recount per-test
```

## Migration History: V1 → V2

Two migration files document the evolution of the ELO calculation:

### V1 (`migrations/elo_functions.sql`)

The original implementation **correctly** called both helper functions:

```sql
-- V1 used volatility and different K-factors
v_user_volatility := calculate_volatility_multiplier(v_user_tests_taken, v_user_last_date, 1.0);
v_test_volatility := calculate_volatility_multiplier(v_test_attempts, NULL, 1.0);
v_new_user_elo := calculate_elo_rating(v_user_elo, v_test_elo, v_percentage, 32, v_user_volatility);
v_new_test_elo := calculate_elo_rating(v_test_elo, v_user_elo, (1.0 - v_percentage), 16, v_test_volatility);
```

Key V1 differences from V2:
- **Volatility was active** — both user and test got volatility multipliers
- **Test K-factor was 16** (asymmetric with user's 32)
- **Schema used text columns** — `language TEXT` and `skill_type TEXT` instead of FK integer IDs
- Used SELECT-then-INSERT/UPDATE pattern (no ON CONFLICT)

### V2 (`migrations/process_test_submission_v2.sql`) — Current

Rewrote the function with server-side answer grading (p_responses JSONB instead of pre-calculated score). In the process, volatility was **intentionally dropped** and the ELO calc was inlined:

```sql
-- V2: inlined calculation — no volatility, no function calls, symmetric K
DECLARE
  expected_user_score numeric;
  k_factor integer := 32;  -- hardcoded, same for user and test
BEGIN
  expected_user_score := 1.0 / (1.0 + POWER(10, (v_test_elo - v_user_elo) / 400.0));
  v_new_user_elo := ROUND(v_user_elo + k_factor * (v_percentage_decimal - expected_user_score));
  v_new_test_elo := ROUND(v_test_elo + k_factor * ((1.0 - v_percentage_decimal) - (1.0 - expected_user_score)));
  v_new_user_elo := GREATEST(400, LEAST(3000, v_new_user_elo));
  v_new_test_elo := GREATEST(400, LEAST(3000, v_new_test_elo));
END;
```

Key V2 changes:
- **Volatility dropped** — both user and test K-factors are 32 with no volatility multiplier
- **Test K-factor raised from 16 → 32** — tests now shift as fast as users
- **Server-side answer grading** — answers validated against `questions` table, not pre-calculated
- **Idempotency** — `p_idempotency_key UUID` prevents duplicate submissions
- **First-attempt gating** — only first attempts update ELO
- **FK-based schema** — `language_id SMALLINT` and `test_type_id SMALLINT` replace text columns

The helper functions (`calculate_elo_rating`, `calculate_volatility_multiplier`) were **not deleted** — they still exist in the database but are no longer called by any code path.

### Impact Assessment

The volatility removal means:
- **New users** (<10 tests) calibrate at the same speed as established users — slower convergence for newcomers
- **Returning users** (>90 days inactive) get no re-calibration boost — ELO may be stale after long breaks
- **Test K-factor doubling** (16→32) makes test ELO more volatile, which may be intentional for a smaller corpus

### Fix: Re-enable Volatility

Replace the inlined block in V2 with calls to the existing helpers:

```sql
-- Calculate volatility for user (not for test — tests don't get "rusty")
DECLARE
  v_vol numeric;
BEGIN
  v_vol := calculate_volatility_multiplier(v_user_tests_taken, v_user_last_date, 1.0);
  v_new_user_elo := calculate_elo_rating(v_user_elo, v_test_elo, v_percentage_decimal, 32, v_vol);
  v_new_test_elo := calculate_elo_rating(v_test_elo, v_user_elo, 1.0 - v_percentage_decimal, 32, 1.0);
END;
```

The variables `v_user_tests_taken` and `v_user_last_date` are already fetched earlier in the function. No new queries needed.

## Backfill Script: Test ELO Seeding

`scripts/backfill_test_skill_ratings.py` seeds initial test ELO from difficulty level:

```python
DIFFICULTY_ELO_MAP = {
    1: 800,   # A1
    2: 950,   # A1+
    3: 1100,  # A2
    4: 1250,  # B1
    5: 1400,  # B1+  (matches default test_skill_ratings.elo_rating)
    6: 1550,  # B2
    7: 1700,  # C1
    8: 1850,  # C1+
    9: 2000   # C2
}
```

This maps difficulty 1–9 to ELO 800–2000 with ~150 ELO steps. Difficulty 5 matches the default 1400 starting ELO. The script also inserts a `volatility: 1.0` column (V1 remnant, no longer used in V2 ELO calc).

The backfill creates ratings per `(test_id, test_type_id)` pair, filtering by `requires_audio` — tests without audio don't get listening test type ratings.

## Recommendation Functions: Comparison

| Feature | `get_recommended_test` | `get_recommended_tests` | `get_vocab_recommendations` |
|---------|----------------------|------------------------|-----------------------------|
| Returns | 0 or 1 test | Multiple tests | Multiple tests |
| Excludes attempted | **No** | Yes | No (but filters by vocab) |
| Tier check (free/premium) | No | Yes | No |
| ELO matching | Expanding radius | Closest match ranking | ±200 range |
| Vocab-aware | No | No | Yes (3–7% unknown) |
| Performance | 5 sequential queries | 1 CTE | 1 CTE with intarray |

### `get_recommended_test` — Expanding Radius

```
Radii: [50, 100, 250, 500, 10000]
For each radius:
  SELECT random test WHERE elo BETWEEN (user_elo - radius) AND (user_elo + radius)
  IF found → return it
```

**Issues:**
1. No exclusion of previously attempted tests
2. Sequential loop (5 queries worst case) — could be a single CTE with CASE
3. Returns a random test within the first matching radius — not the closest match
4. Doesn't check subscription tier

### `get_recommended_tests` — Closest Match

```
CTE pipeline:
  target_types → user_stats (ELO per type) → all_candidates (ranked by ELO proximity)
    → ROW_NUMBER() OVER (PARTITION BY type_code ORDER BY ABS(elo_diff))
    → WHERE rank_in_type <= 3
    → DISTINCT ON (test_id) — dedup across types
    → ORDER BY elo_diff
```

**This is the better function.** Clean CTE, single query, proper filtering.

### `get_vocab_recommendations` — Vocabulary-Aware

```
Uses intarray & operator for set intersection:
  unknown_pct = (CARDINALITY(vocab_sense_ids) - CARDINALITY(vocab_sense_ids & known_sense_ids))
                / CARDINALITY(vocab_sense_ids)
WHERE unknown_pct BETWEEN 0.03 AND 0.07
ORDER BY ABS(unknown_pct - 0.05)  -- target 5% unknown (i+1 sweet spot)
```

**Pedagogically strongest** — combines ELO proximity (±200) with comprehensible input theory.

## Trigger Performance Concern

`update_skill_attempts_count()` (trigger on `test_attempts` INSERT):

```sql
UPDATE test_skill_ratings
SET total_attempts = (
    SELECT COUNT(*) FROM test_attempts
    WHERE test_id = NEW.test_id AND test_type_id = test_skill_ratings.test_type_id
)
```

This runs a full COUNT on every attempt insert. For a popular test with thousands of attempts, this becomes expensive. Should be replaced with an increment:

```sql
UPDATE test_skill_ratings
SET total_attempts = total_attempts + 1, updated_at = NOW()
WHERE test_id = NEW.test_id AND test_type_id = NEW.test_type_id;
```

Similarly, there's a second trigger `update_test_attempts_count()` that does the same recount. Two triggers doing overlapping COUNT queries on the same INSERT is redundant.

## Tables: Current State

### `user_skill_ratings`
- PK: `id` (uuid)
- Unique: `UNIQUE (user_id, language_id, test_type_id)` — enforced in live schema (`db_schema_live.sql:501`)
- Columns: `elo_rating` (default 1200, CHECK 400–3000), `tests_taken` (CHECK ≥0), `last_test_date`
- Trigger: `update_updated_at_column()`

### `test_skill_ratings`
- PK: `id` (uuid)
- Unique: `UNIQUE (test_id, test_type_id)` — enforced in live schema (`db_schema_live.sql:687`)
- Columns: `elo_rating` (default 1400, CHECK 400–3000), `total_attempts` (CHECK ≥0)

### `test_attempts`
- Stores full ELO audit trail: `user_elo_before`, `user_elo_after`, `test_elo_before`, `test_elo_after`
- Generated column: `percentage` = `score / total_questions * 100`
- Unique idempotency: partial index on `(user_id, idempotency_key) WHERE idempotency_key IS NOT NULL`

## Proposed Improvements: Technical Details

### 1. Adaptive K-Factor

```sql
CREATE OR REPLACE FUNCTION calculate_adaptive_k(
    base_k integer,
    total_questions integer,
    score_pct numeric,
    user_tests_taken integer
) RETURNS numeric AS $$
BEGIN
    -- More questions = more reliable signal = higher K
    -- Clamp between 0.5x and 1.5x base
    RETURN base_k * GREATEST(0.5, LEAST(1.5,
        -- Question count factor: sqrt(questions) / sqrt(10)
        SQRT(total_questions::numeric) / SQRT(10.0)
        -- Extreme score penalty: scores near 0% or 100% suggest mismatch
        * CASE
            WHEN score_pct < 0.10 OR score_pct > 0.90 THEN 0.7
            ELSE 1.0
          END
    ));
END;
$$ LANGUAGE plpgsql IMMUTABLE;
```

### 2. Glicko-2 Schema Extension

```sql
ALTER TABLE user_skill_ratings
    ADD COLUMN rating_deviation numeric DEFAULT 350.0,  -- Glicko-2 RD
    ADD COLUMN rating_volatility numeric DEFAULT 0.06;  -- Glicko-2 σ

ALTER TABLE test_skill_ratings
    ADD COLUMN rating_deviation numeric DEFAULT 350.0;
```

RD decays (increases) with inactivity using the Glicko-2 formula:
`new_RD = min(350, sqrt(RD² + σ²))` applied during each rating period.

### 3. Single-Recommendation Fix

```sql
-- Add to get_recommended_test, inside the LOOP:
AND NOT EXISTS (
    SELECT 1 FROM test_attempts ta
    WHERE ta.user_id = p_user_id AND ta.test_id = t.id
)
```

### ~~4. Missing UNIQUE Constraints~~ — RESOLVED

**Correction**: The live schema (`db_schema_live.sql`) confirms both tables already have the required UNIQUE constraints:
- `user_skill_ratings`: `UNIQUE (user_id, language_id, test_type_id)`
- `test_skill_ratings`: `UNIQUE (test_id, test_type_id)`

The wiki's `database/schema.tech.md` page omitted these constraints, creating the false impression they were missing. No migration needed.

## Related Pages

- [[algorithms/elo-implementation-analysis]] — Prose analysis
- [[algorithms/elo-ranking.tech]] — Original specification
- [[database/rpcs.tech]] — Full RPC SQL definitions
- [[database/schema.tech]] — Table DDL
