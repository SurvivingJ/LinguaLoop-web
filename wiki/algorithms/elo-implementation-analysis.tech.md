---
title: ELO System — Implementation Analysis (Technical)
type: algorithm-tech
status: in-progress
prose_page: ./elo-implementation-analysis.md
last_updated: 2026-11-23
open_questions:
  - "OPEN: apply migrations/skill_ratings_natural_key_unique.sql and then migrations/skill_ratings_writers_on_conflict.sql (both written, NOT applied live as of 2026-11-23)? Until then the rating tables have no natural-key uniqueness."
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
        │     ├── calculate_volatility_multiplier(user_tests_taken, user_last_date)
        │     ├── calculate_elo_rating(user, test, pct, K=32, vol)   — user-side
        │     ├── calculate_elo_rating(test, user, 1-pct, K=16, 1.0) — test-side
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

## Migration History: V1 → V2 → V3 → V4

Three migration files document the evolution of the ELO calculation:

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

### V2 (`migrations/archive/process_test_submission_v2.sql`)

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

### V3 (`migrations/wire_volatility_and_exclude_attempted.sql`)

Re-wires volatility into the user-side calculation and restores the asymmetric K-factor for tests. The inlined math is replaced with calls to `calculate_volatility_multiplier()` and `calculate_elo_rating()` (which already existed in the live DB but had been disconnected since V2):

```sql
DECLARE
  v_user_volatility numeric;
BEGIN
  v_user_volatility := calculate_volatility_multiplier(
      v_user_tests_taken, v_user_last_date, 1.0
  );

  -- User: K=32 with volatility (1.5x for new users, 2.0x for new + inactive)
  v_new_user_elo := calculate_elo_rating(
      v_user_elo, v_test_elo, v_percentage_decimal, 32, v_user_volatility
  );

  -- Test: K=16, no volatility (tests don't go rusty)
  v_new_test_elo := calculate_elo_rating(
      v_test_elo, v_user_elo, 1.0 - v_percentage_decimal, 16, 1.0
  );
END;
```

V3 differs from V1 in one principled way: V1 applied a volatility multiplier to the test side too (`calculate_volatility_multiplier(v_test_attempts, NULL, 1.0)`). V3 hardcodes test volatility to 1.0 because the inactivity-decay branch of the multiplier doesn't apply to tests — they don't get rusty — and the new-test branch is handled by seeding each test's initial rating from its age tier and a lexical-complexity score at generation time (`seed_test_elo`, see "Test ELO Seeding" below; the old difficulty-map backfill script is deleted). The variables `v_user_tests_taken` and `v_user_last_date` are already fetched earlier in the function; no new queries.

### V4 (`migrations/archive/process_test_submission_reduced_repeats.sql`) — superseded by V5 for the function body

Adds a third ELO-update branch for repeat attempts that come via the daily-load retry slot. Same 7-arg signature; existing callers untouched. Adds `test_attempts.elo_reduction_factor numeric NULL`.

```sql
-- Eligibility (server-side, no client flag):
-- 1. is_first_attempt = false
-- 2. EXISTS in daily_test_loads.test_ids today with slot_type='retry'
-- 3. NOT EXISTS prior test_attempts today on this (user,test) with elo_reduction_factor IS NOT NULL

IF v_is_retry_slot AND NOT v_already_earned_today THEN
    SELECT MAX(created_at),
           MAX((score::numeric / NULLIF(total_questions, 0)::numeric) * 100)
    INTO v_last_attempt_at, v_prev_best
    FROM test_attempts
    WHERE user_id = p_user_id AND test_id = p_test_id;

    v_days_since := EXTRACT(EPOCH FROM (NOW() - COALESCE(v_last_attempt_at, NOW()))) / 86400.0;
    v_base := LEAST(1.0, GREATEST(0.20, v_days_since / 60.0));
    v_bonus := CASE WHEN (v_percentage - v_prev_best) >= 15 THEN 0.25 ELSE 0 END;
    v_factor := LEAST(1.0, v_base + v_bonus);

    -- Compose factor into the volatility argument; K-factors unchanged
    v_new_user_elo := calculate_elo_rating(
        v_user_elo, v_test_elo, v_percentage_decimal, 32,
        v_user_volatility * v_factor
    );
    v_new_test_elo := calculate_elo_rating(
        v_test_elo, v_user_elo, 1.0 - v_percentage_decimal, 16,
        v_factor
    );
    v_record_factor := v_factor;  -- persisted to test_attempts
END IF;
```

Design notes:
- Retry-slot detection is a JSONB element scan against `daily_test_loads.test_ids` (the slot list lives inline in that table; there is no child `daily_test_load_items` table — see [services/test_service.py](../../services/test_service.py)).
- Anti-grind uses `test_attempts.elo_reduction_factor IS NOT NULL` as a same-day sentinel, set atomically by this RPC. The 24h retry-slot cooldown in `_compute_daily_load` already prevents the slot from re-listing the test the same day; the sentinel catches direct-nav retries that bypass the slot UI.
- Factor is composed into the volatility argument (not into K) because `calculate_elo_rating` already multiplies `k * volatility` — composition keeps the K=32/K=16 asymmetry intact.
- The improvement bonus compares against `MAX(percentage)` over all prior attempts, not just the most recent one, so a one-time spike doesn't keep paying out on subsequent repeats.

### V5 (`migrations/process_test_submission_set_based_grading.sql`) — Current (live 2026-11-23)

Same signature (9 arguments, including `p_furigana_used` and `p_prestudied`), return shape, auth gate (`error_code: 'unauthorized'` for a NULL `p_user_id` or a mismatched caller) and ELO maths as V4. Three changes, verified against the live body:
- Grading is one set-based query joining `questions` to the submitted answers (before: a temp table per call and a per-question loop).
- The idempotency-key duplicate check runs before grading, so a retried request returns the cached attempt without regrading.
- The learner's `user_skill_ratings` row and the test's `test_skill_ratings` row are read `FOR UPDATE`, so concurrent submissions for the same learner and test type run one after the other and no longer lose an ELO update. A row that does not exist yet cannot be locked, hence the duplicate-row limitation under "Tables: Current State".
- The outer `EXCEPTION WHEN OTHERS` still returns `{success:false, error: SQLERRM, error_detail: SQLSTATE}`; unlike the pinyin, pitch-accent and dictation functions it was not changed to the generic `submission_failed` envelope (live check 2026-11-23). Learners see no difference from V4.

## Test ELO Seeding

Initial test ratings are written by the test-generation pipeline, not by a backfill.

1. `services/test_generation/orchestrator.py` reads the topic's assigned age tier and its midpoint ELO (`get_tier_initial_elo` in `services/test_generation/database_client.py`, from `dim_complexity_tiers.initial_elo`). A missing tier raises; there is no hardcoded difficulty-to-ELO map.
2. `seed_test_elo(prose, language_code, tier_id, tier_initial_elo)` in `services/test_generation/difficulty_scorer.py` adjusts that midpoint by a weighted lexical score (mean Zipf frequency, sentence length, type-token ratio), clamped to 400..3000. On an empty signal, or if the scorer raises, the tier midpoint is used. The coefficients are an a-priori prior, not fitted to attempts (the module docstring says so).
3. `insert_test_skill_ratings(test_id, initial_elo, has_audio, language_id)` inserts one `test_skill_ratings` row per active test type that applies (types that require audio are skipped when the test has no audio; language-specific types only for their own language, via `Config.test_type_applies_to_language`), `total_attempts = 0`, no `volatility` column (dropped).
4. Sentinel tests used by the drill trainers get their row inside the submission function on first use (`INSERT INTO test_skill_ratings ... 1400`), and a user's row is created at 1200 on their first submission for a language and test type.

Checked live 2026-11-23: 488 active tests, 0 without a rating row, 1,703 rating rows.

**Deleted: scripts/backfill_test_skill_ratings.py.** It mapped difficulty 1 to 9 onto ELO 800 to 2000 and inserted missing rows. It was removed because every active test is already rated and, with no unique constraint on `(test_id, test_type_id)`, re-running it could have inserted duplicate rows. Do not recreate it; to rate a new test type for existing tests, write a one-off migration with `ON CONFLICT` after the natural-key index exists.

## Recommendation Functions: Comparison

| Feature | `get_recommended_test` | `get_recommended_tests` | `get_vocab_recommendations` |
|---------|----------------------|------------------------|-----------------------------|
| Returns | 0 or 1 test | Multiple tests | Multiple tests |
| Excludes attempted | Yes (V3) | Yes | No (but filters by vocab) |
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

**V3 (`migrations/wire_volatility_and_exclude_attempted.sql`)** added a `NOT EXISTS` against `test_attempts` inside the loop's `WHERE` so each radius pass excludes tests the user has attempted.

**Remaining issues:**
1. Sequential loop (5 queries worst case) — could be a single CTE with CASE
2. Returns a random test within the first matching radius — not the closest match
3. Doesn't check subscription tier

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
- PK: `id` (uuid, `gen_random_uuid()`) is the **only** key. Verified live 2026-11-23 with `pg_constraint`/`pg_index`: no unique constraint or index on `(user_id, language_id, test_type_id)`. Other indexes: `(user_id)`, `(language_id, test_type_id)`.
- Columns: `elo_rating` (default 1200, CHECK 400–3000 and 0–4000), `tests_taken` (CHECK ≥0), `last_test_date`, `created_at`, `updated_at`
- Trigger: `update_user_skill_ratings_updated_at` (BEFORE UPDATE, `update_updated_at_column()`)

### `test_skill_ratings`
- PK: `id` (uuid) is the **only** key. No unique constraint or index on `(test_id, test_type_id)` live. Other indexes: `(test_id)`, `(test_type_id)`.
- Columns: `elo_rating` (default 1400, CHECK 400–3000 and 0–4000), `total_attempts` (CHECK ≥0), `created_at`, `updated_at`. No `volatility` or `updated_at` trigger.

Consequence: a first-ever simultaneous submission can create two rows for one natural key (see below). Live duplicate counts on 2026-11-23: 0 for both tables. Pending (written, NOT applied): `migrations/skill_ratings_natural_key_unique.sql` (`CREATE UNIQUE INDEX CONCURRENTLY` on both keys; outside a transaction) and `migrations/skill_ratings_writers_on_conflict.sql` (the five submission RPCs and `apply_calibration_to_skill_ratings` insert with `ON CONFLICT` and re-read the row; must run after the index file, otherwise `42P10`). Rollback file: `migrations/skill_ratings_writers_on_conflict_rollback.sql`. Order and checks: `migrations/PENDING-2026-11-23.md`.

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

### ~~3. Single-Recommendation Fix~~ — APPLIED 2026-05-08

Implemented in `migrations/wire_volatility_and_exclude_attempted.sql` — see "Recommendation Functions" above.

### 4. Missing UNIQUE Constraints — OPEN (pending migrations)

**Correction (2026-11-23).** An earlier version of this page marked this item "resolved" on the strength of a schema snapshot. The live catalog shows otherwise: both rating tables have only their surrogate primary key (see "Tables: Current State"). The fix is written and pending: `migrations/skill_ratings_natural_key_unique.sql`, then `migrations/skill_ratings_writers_on_conflict.sql`.

## Related Pages

- [[algorithms/elo-implementation-analysis]] — Prose analysis
- [[algorithms/elo-ranking.tech]] — Original specification
- [[database/rpcs.tech]] — Full RPC SQL definitions
- [[database/schema.tech]] — Table DDL
