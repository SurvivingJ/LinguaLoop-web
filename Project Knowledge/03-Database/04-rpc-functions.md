# RPC Functions

PostgreSQL functions called via `supabase.rpc()`. These execute server-side in single transactions, providing atomicity for operations that touch multiple tables (ELO updates, answer validation, token management).

---

## `process_test_submission` (v2 -- Current)

The primary test submission handler. Accepts raw user responses, validates answers server-side against the `questions` table, calculates ELO changes, and records the attempt atomically.

### Signature

```sql
CREATE OR REPLACE FUNCTION process_test_submission(
  p_user_id          UUID,
  p_test_id          UUID,
  p_language_id      SMALLINT,
  p_test_type_id     SMALLINT,
  p_responses        JSONB,
  p_was_free_test    BOOLEAN DEFAULT TRUE,
  p_idempotency_key  UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER;
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `p_user_id` | `UUID` | Yes | Authenticated user's ID (validated against `auth.uid()`) |
| `p_test_id` | `UUID` | Yes | Test being submitted |
| `p_language_id` | `SMALLINT` | Yes | Language ID from `dim_languages` |
| `p_test_type_id` | `SMALLINT` | Yes | Test type ID from `dim_test_types` |
| `p_responses` | `JSONB` | Yes | Array of `{question_id: UUID, selected_answer: text}` |
| `p_was_free_test` | `BOOLEAN` | No | Default `true`. Controls token deduction |
| `p_idempotency_key` | `UUID` | No | Prevents duplicate processing |

### Response Format (Success)

```json
{
  "success": true,
  "attempt_id": "uuid",
  "attempt_number": 1,
  "is_first_attempt": true,
  "user_elo_before": 1200,
  "user_elo_after": 1218,
  "user_elo_change": 18,
  "test_elo_before": 1400,
  "test_elo_after": 1382,
  "test_elo_change": -18,
  "tokens_cost": 0,
  "score": 4,
  "total_questions": 5,
  "percentage": 80.0,
  "question_results": [
    {
      "question_id": "uuid",
      "selected_answer": "Option B",
      "correct_answer": "Option B",
      "is_correct": true
    }
  ],
  "message": "First attempt - ELO updated"
}
```

### Response Format (Error)

```json
{
  "success": false,
  "error": "Error message",
  "error_detail": "SQLSTATE code"
}
```

### Processing Steps

1. **Security validation**: Checks `p_user_id == auth.uid()` to prevent submission for other users.
2. **Input validation**: Verifies `p_responses` is a non-empty JSONB array.
3. **Answer validation**: Creates a temp table from responses, iterates over `questions` for the test, compares `selected_answer` against `questions.answer` (JSONB extracted via `#>> '{}'`). Case-sensitive string match.
4. **Idempotency check**: If `p_idempotency_key` is provided and matches an existing `test_attempts.idempotency_key`, returns the cached result without re-processing.
5. **Token cost**: Calls `get_test_token_cost(p_user_id)` to determine deduction.
6. **Attempt numbering**: Counts existing attempts for `(user_id, test_id, test_type_id)` and increments.
7. **ELO calculation** (first attempts only): See ELO formula below.
8. **Record insertion**: Inserts into `test_attempts` with before/after ELO snapshots.
9. **Language tracking**: Upserts `user_languages` to track activity.

### ELO Formula (v2)

Used for first attempts only. K-factor is fixed at 32 with no volatility multiplier.

```
expected_user_score = 1.0 / (1.0 + 10^((test_elo - user_elo) / 400))

new_user_elo = user_elo + 32 * (actual_percentage - expected_user_score)
new_test_elo = test_elo + 32 * ((1.0 - actual_percentage) - (1.0 - expected_user_score))

# Clamped to range [400, 3000]
```

Where `actual_percentage` is `score / total_questions` as a decimal (0.0 to 1.0).

### Grants

```sql
GRANT EXECUTE ON FUNCTION process_test_submission TO authenticated;
```

### Invocation

```python
# routes/tests.py line 633
response = supabase_service.rpc('process_test_submission', {
    'p_user_id': current_user_id,
    'p_test_id': test_id,
    'p_language_id': language_id,
    'p_test_type_id': test_type_id,
    'p_responses': db_responses,
    'p_was_free_test': True,
    'p_idempotency_key': str(uuid4())
}).execute()
```

**Source**: `migrations/process_test_submission_v2.sql` lines 1-348

---

## `calculate_elo_rating`

Core ELO calculation with configurable K-factor and volatility multiplier.

### Signature

```sql
CREATE OR REPLACE FUNCTION calculate_elo_rating(
    current_rating          INTEGER,
    opposing_rating         INTEGER,
    actual_score            NUMERIC,   -- 0.0 to 1.0
    k_factor                INTEGER DEFAULT 32,
    volatility_multiplier   NUMERIC DEFAULT 1.0
)
RETURNS INTEGER
LANGUAGE plpgsql IMMUTABLE;
```

### Formula

```
expected_score = 1.0 / (1.0 + 10^((opposing_rating - current_rating) / 400))
adjusted_k     = k_factor * volatility_multiplier
new_rating     = current_rating + adjusted_k * (actual_score - expected_score)

-- Clamped to [400, 3000]
RETURN GREATEST(400, LEAST(3000, ROUND(new_rating)))
```

### Usage

Called by the v1 `process_test_submission` function. The v2 function inlines this logic directly.

**Source**: `migrations/elo_functions.sql` lines 29-49

---

## `calculate_volatility_multiplier`

Calculates a volatility multiplier that increases rating changes for new or returning users/tests.

### Signature

```sql
CREATE OR REPLACE FUNCTION calculate_volatility_multiplier(
    attempts        INTEGER,
    last_date       DATE DEFAULT NULL,
    base_volatility NUMERIC DEFAULT 1.0
)
RETURNS NUMERIC
LANGUAGE plpgsql IMMUTABLE;
```

### Logic

```
multiplier = base_volatility

IF attempts < 10 THEN
    multiplier += 0.5        -- New entity: ratings move faster
END IF

IF last_date IS NOT NULL AND (CURRENT_DATE - last_date) > 90 THEN
    multiplier += 0.5        -- Returning after 90+ day gap
END IF

RETURN multiplier            -- Range: 1.0 to 2.0
```

### Usage

Called by the v1 `process_test_submission` function to amplify K-factor for volatile ratings.

**Source**: `migrations/elo_functions.sql` lines 5-26

---

## `process_test_submission` (v1 -- Original)

The original test submission handler. Accepts a pre-calculated score (not raw responses) and uses volatility multipliers.

### Signature

```sql
CREATE OR REPLACE FUNCTION process_test_submission(
    p_user_id           UUID,
    p_test_id           UUID,
    p_language          TEXT,          -- Language name, not ID
    p_skill_type        TEXT,          -- 'listening', 'reading', 'dictation'
    p_score             INTEGER,
    p_total_questions   INTEGER,
    p_test_mode         TEXT,
    p_tokens_consumed   INTEGER DEFAULT 0,
    p_was_free_test     BOOLEAN DEFAULT TRUE
)
RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER;
```

### Key Differences from v2

| Aspect | v1 | v2 |
|--------|----|----|
| Score input | Pre-calculated `p_score` | Raw `p_responses` JSONB |
| Answer validation | Client-side | Server-side |
| Language parameter | Text name (`'chinese'`) | Integer ID |
| Skill type parameter | Text code (`'reading'`) | Integer ID (`dim_test_types.id`) |
| ELO calculation | Uses `calculate_elo_rating()` + volatility | Inline calculation, K=32 fixed |
| K-factor (user) | 32 * volatility | 32 |
| K-factor (test) | 16 * volatility | 32 |
| Idempotency | Not supported | Via `p_idempotency_key` |
| First-attempt logic | Not tracked | Only first attempts update ELO |
| Return data | Basic ELO changes | Full question results array |

### Response Format

```json
{
  "success": true,
  "attempt_id": "uuid",
  "user_elo_before": 1200,
  "user_elo_after": 1224,
  "user_elo_change": 24,
  "test_elo_before": 1400,
  "test_elo_after": 1392,
  "test_elo_change": -8,
  "score": 4,
  "percentage": 0.8
}
```

**Source**: `migrations/elo_functions.sql` lines 52-209

---

## `get_cefr_config`

Returns CEFR level configuration for a given difficulty.

### Signature

```sql
CREATE OR REPLACE FUNCTION get_cefr_config(p_difficulty INTEGER)
RETURNS TABLE (
    id              INTEGER,
    cefr_code       VARCHAR(2),
    word_count_min  INTEGER,
    word_count_max  INTEGER,
    initial_elo     INTEGER
)
LANGUAGE plpgsql;
```

### Usage

Looks up `dim_cefr_levels` where `p_difficulty BETWEEN difficulty_min AND difficulty_max`. Returns one row.

**Source**: `migrations/test_generation_tables.sql` lines 480-502

---

## `get_question_distribution`

Returns the 5 question type codes for a given difficulty level.

### Signature

```sql
CREATE OR REPLACE FUNCTION get_question_distribution(p_difficulty INTEGER)
RETURNS TABLE (
    question_type_code VARCHAR(30)
)
LANGUAGE plpgsql;
```

### Usage

Unnests the 5 `question_type_*` columns from `question_type_distributions` for the given difficulty. Returns 5 rows.

**Source**: `migrations/test_generation_tables.sql` lines 505-523

---

## `get_recommended_test`

Returns a single recommended test based on the user's ELO rating.

### Signature (inferred from call site)

```sql
FUNCTION get_recommended_test(
    p_user_id       UUID,
    p_language_id   INTEGER
)
RETURNS TABLE (...)    -- Test row data
```

### Usage

```python
# routes/tests.py line 86
result = supabase_service.rpc('get_recommended_test', {
    'p_user_id': user_id,
    'p_language_id': language_id
}).execute()
```

**Source**: `routes/tests.py` lines 86-89

---

## `get_recommended_tests`

Returns multiple recommended tests for the user.

### Signature (inferred from call site)

```sql
FUNCTION get_recommended_tests(
    p_user_id   UUID,
    p_language  TEXT     -- Language name
)
RETURNS TABLE (...)
```

### Usage

```python
# routes/tests.py line 112
result = supabase_service.rpc('get_recommended_tests', {
    'p_user_id': user_id,
    'p_language': language
}).execute()
```

**Source**: `routes/tests.py` lines 112-115

---

## `get_token_balance`

Returns the current token balance for a user.

### Signature (inferred from call site)

```sql
FUNCTION get_token_balance(p_user_id UUID)
RETURNS INTEGER
```

### Usage

Called via the admin client (requires elevated permissions).

```python
# services/auth_service.py line 160
token_balance = self.supabase_admin.rpc('get_token_balance', {
    'p_user_id': user_id
}).execute()
```

**Source**: `services/auth_service.py` lines 160-162

---

## `grant_daily_free_tokens`

Grants free daily tokens to a user (welcome bonus or daily reset).

### Signature (inferred from call site)

```sql
FUNCTION grant_daily_free_tokens(p_user_id UUID)
RETURNS VOID  -- or JSONB
```

### Usage

Called via the admin client when creating a new user.

```python
# services/auth_service.py line 183
self.supabase_admin.rpc('grant_daily_free_tokens', {
    'p_user_id': user_id
}).execute()
```

**Source**: `services/auth_service.py` lines 183-185

---

## `get_test_token_cost`

Returns the token cost for taking a test, based on user's subscription tier.

### Signature (inferred from v2 RPC usage)

```sql
FUNCTION get_test_token_cost(p_user_id UUID)
RETURNS INTEGER
```

### Usage

Called internally by `process_test_submission` v2 (line 140).

**Source**: `migrations/process_test_submission_v2.sql` line 140

---

## `match_topics`

Vector similarity search for topic deduplication using pgvector cosine distance.

### Signature (inferred from call site)

```sql
FUNCTION match_topics(
    query_category      INTEGER,
    query_embedding      VECTOR(1536),
    match_threshold     FLOAT,
    match_count         INTEGER
)
RETURNS TABLE (
    id                  UUID,
    concept_english     TEXT,
    similarity          FLOAT
)
```

### Usage

```python
# services/topic_generation/database_client.py line 418
response = self.client.rpc('match_topics', {
    'query_category': category_id,
    'query_embedding': embedding,
    'match_threshold': 0.85,
    'match_count': 5
}).execute()
```

Returns topics within the same category that have cosine similarity >= threshold.

**Source**: `services/topic_generation/database_client.py` lines 401-428

---

## `get_active_languages`

Returns all active languages ordered by display order.

### Signature (inferred from call site)

```sql
FUNCTION get_active_languages()
RETURNS TABLE (
    id              SMALLINT,
    language_code   VARCHAR,
    language_name   VARCHAR,
    native_name     VARCHAR
)
```

### Usage

```python
# services/topic_generation/database_client.py line 108
response = self.client.rpc('get_active_languages').execute()
```

**Source**: `services/topic_generation/database_client.py` line 108

---

## `get_next_category`

Returns the next eligible category for topic generation, respecting cooldown periods.

### Signature (inferred from call site)

```sql
FUNCTION get_next_category()
RETURNS TABLE (
    id                  INTEGER,
    name                VARCHAR,
    status_id           INTEGER,
    target_language_id  SMALLINT,
    last_used_at        TIMESTAMPTZ,
    cooldown_days       INTEGER
)
```

### Usage

```python
# services/topic_generation/database_client.py line 344
response = self.client.rpc('get_next_category').execute()
```

**Source**: `services/topic_generation/database_client.py` line 344

---

## Related Documents

- [01-schema-overview.md](./01-schema-overview.md) -- High-level architecture and table groups
- [02-tables-reference.md](./02-tables-reference.md) -- Full column-level documentation for every table
- [03-dimension-tables.md](./03-dimension-tables.md) -- Dimension table seed data and lookup patterns
- [05-rls-policies.md](./05-rls-policies.md) -- Row-Level Security policy documentation
- [06-migrations.md](./06-migrations.md) -- Migration file history and changelog
