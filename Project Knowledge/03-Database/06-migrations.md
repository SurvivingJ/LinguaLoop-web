# Database Migrations

**Purpose**: Document the database migration strategy and key migration files for the LinguaLoop/LinguaDojo project.

---

## Migration Strategy

**Framework**: None (manual migrations via Supabase SQL Editor)

**Execution**: All migrations are executed manually by pasting SQL into the Supabase SQL Editor.

**Versioning**: File naming convention with descriptive names (no timestamp prefixes or version numbers).

**Rollback**: No automated rollback mechanism. Manual reversal via compensating SQL statements if needed.

---

## Migration Files

All migration files are located in the `migrations/` directory.

### 1. test_generation_tables.sql

**Purpose**: Creates core dimension tables, configuration tables, and seeds prompt templates for test generation.

**Tables Created**:
- `dim_question_types`: 6 question types across 3 cognitive levels
- `dim_cefr_levels`: 6 CEFR levels (A1-C2) mapped to 9 difficulty levels (1-9)
- `question_type_distributions`: Maps difficulty levels to question type percentages
- `test_generation_config`: Configuration settings for test generation
- `test_generation_runs`: Audit log of test generation runs
- `prompt_templates`: Stores prompt templates for different languages

**Prompt Templates Seeded**:
For each language (English, Chinese, Japanese):
- `transcript_generation`: Mono-speaker transcript writer
- `prose_generation_listening`: Prose writer for listening tests
- `title_generation`: Test title generator
- `question_type_1`: Simple recognition questions
- `question_type_2`: Detail and main idea questions
- `question_type_3`: Complex inference questions
- `question_generation_listening`: Legacy question generator (5 questions at once)

**Question Types**:
1. **Simple Recognition** (Cognitive Level 1)
2. **Detail Questions** (Cognitive Level 2)
3. **Main Idea** (Cognitive Level 2)
4. **Inference** (Cognitive Level 3)
5. **Attitude/Tone** (Cognitive Level 3)
6. **Discourse Organization** (Cognitive Level 3)

**CEFR Levels** (with word count ranges and initial ELO):
- A1: 100-200 words, ELO 875
- A2: 200-300 words, ELO 1050
- B1: 300-500 words, ELO 1225
- B2: 500-700 words, ELO 1400
- C1: 700-1000 words, ELO 1575
- C2: 1000+ words, ELO 1750

**Difficulty Distribution Example** (for difficulty level 5):
```
Type 1 (Simple): 10%
Type 2 (Detail): 30%
Type 3 (Main Idea): 30%
Type 4 (Inference): 20%
Type 5 (Attitude): 5%
Type 6 (Discourse): 5%
```

**Source**: `migrations/test_generation_tables.sql`

---

### 2. elo_functions.sql

**Purpose**: Implements ELO rating calculation functions and the original v1 test submission RPC.

**Functions Created**:

#### calculate_volatility_multiplier()
Calculates a volatility multiplier based on:
- Number of attempts (fewer attempts = higher volatility)
- Time since last attempt (longer gap = higher volatility)

**Formula**:
```sql
base_multiplier = 1.0 + (1.0 / (1.0 + attempts * 0.1))
time_gap_days = EXTRACT(EPOCH FROM (now() - last_attempt)) / 86400.0
time_multiplier = 1.0 + (0.1 * LEAST(time_gap_days / 30.0, 1.0))
RETURN base_multiplier * time_multiplier
```

**Used in**: v1 ELO calculation (with volatility)

#### calculate_elo_rating()
Standard ELO rating calculation.

**Parameters**:
- `current_rating`: Current ELO rating
- `opponent_rating`: Opponent's ELO rating
- `score`: Actual score (1.0 for win, 0.0 for loss, 0.5 for draw)
- `k_factor`: ELO K-factor (determines rating change magnitude)

**Formula**:
```sql
expected_score = 1.0 / (1.0 + POW(10.0, (opponent_rating - current_rating) / 400.0))
rating_change = k_factor * (score - expected_score)
new_rating = current_rating + rating_change
RETURN GREATEST(400, LEAST(3000, new_rating))  -- Clamped to [400, 3000]
```

**Source**: `migrations/elo_functions.sql:15-30`

#### process_test_submission (v1)
Original test submission RPC with volatility multiplier.

**Key Features**:
- Client-side answer validation (answers passed in)
- Volatility multiplier applied to user K-factor
- K-factor: 32 for users (with volatility), 16 for tests
- Only first attempts update ELO
- Returns overall score and ELO changes

**Status**: Superseded by v2 (but may still exist for backward compatibility)

**Source**: `migrations/elo_functions.sql:32-200`

---

### 3. process_test_submission_v2.sql

**Purpose**: Updated test submission RPC with server-side validation and improved ELO calculation.

**Function**: `process_test_submission`

**Parameters**:
- `p_user_id` (UUID): User submitting the test
- `p_test_id` (UUID): Test being submitted
- `p_test_mode` (TEXT): Test mode (reading/listening/dictation)
- `p_responses` (JSONB): Array of `{question_id, selected_answer}` objects
- `p_time_taken` (INTEGER): Time in seconds

**Key Improvements over v1**:

1. **Server-Side Answer Validation**:
   ```sql
   -- Fetch correct answers from questions table
   -- Compare with user's selected_answer
   -- Calculate is_correct on server (not trusted from client)
   ```

2. **JSONB Response Format**:
   - Accepts responses as JSONB array instead of individual parameters
   - More flexible for variable number of questions

3. **Uniform K-Factor**:
   - K-factor = 32 for both users and tests (no more 16 for tests)
   - No volatility multiplier (simplified)

4. **Idempotency**:
   - Checks for duplicate submissions within short time window
   - Returns existing result if duplicate detected

5. **Per-Question Results**:
   ```json
   {
     "question_results": [
       {
         "question_id": "uuid",
         "question_text": "...",
         "selected_answer": "...",
         "correct_answer": "...",
         "is_correct": true,
         "answer_explanation": "..."
       }
     ],
     "score": 4,
     "total_questions": 5,
     "user_elo_change": 12.5,
     "test_elo_change": -12.5,
     "new_user_elo": 1212.5,
     "new_test_elo": 1187.5
   }
   ```

6. **Error Handling**:
   ```sql
   EXCEPTION WHEN OTHERS THEN
     RETURN jsonb_build_object(
       'success', false,
       'error', SQLERRM
     );
   ```

**ELO Update Logic**:
```sql
-- Only update on first attempt
is_first_attempt = NOT EXISTS (
  SELECT 1 FROM test_results
  WHERE user_id = p_user_id AND test_id = p_test_id
)

IF is_first_attempt THEN
  -- Calculate score percentage
  score_percentage = correct_count::float / total_questions

  -- Update user ELO (per mode)
  new_user_elo = calculate_elo_rating(
    current_user_elo, current_test_elo, score_percentage, 32
  )

  -- Update test ELO (inverse score)
  new_test_elo = calculate_elo_rating(
    current_test_elo, current_user_elo, 1.0 - score_percentage, 32
  )
END IF
```

**Source**: `migrations/process_test_submission_v2.sql`

---

## Migration Execution Workflow

### 1. Local Development
```bash
# 1. Write migration SQL in migrations/ directory
# 2. Open Supabase SQL Editor
# 3. Paste SQL and execute
# 4. Verify with SELECT queries
```

### 2. Production
```bash
# Same process - no automated deployment
# Manual execution ensures careful review
```

### 3. Rollback
```sql
-- Example: Rollback a table creation
DROP TABLE IF EXISTS table_name CASCADE;

-- Example: Rollback a function
DROP FUNCTION IF EXISTS function_name(param_types);

-- Example: Rollback data insertion
DELETE FROM table_name WHERE condition;
```

---

## Missing Migrations

The following tables exist in the application but their creation migrations are not in the repository:

- `tests`, `questions` (likely created via Supabase UI initially)
- `test_results`, `user_elo_ratings`, `test_skill_ratings`
- `user_tokens`, `token_transactions`
- `topics`, `production_queue`
- `dim_languages`, `dim_categories`, `dim_lenses`, `dim_test_types`
- `reports`, `stripe_payments`, `user_languages`

**Implication**: For fresh deployments, these tables would need to be recreated manually or via schema export.

---

## Best Practices Observed

1. **Idempotent Functions**: RPC functions check for existing data before inserting
2. **Error Handling**: All RPCs have `EXCEPTION WHEN OTHERS` blocks
3. **Data Validation**: Server-side validation in RPCs (don't trust client input)
4. **Audit Logging**: `test_generation_runs` tracks pipeline executions
5. **Prompt Versioning**: `prompt_templates` has `version` and `is_active` fields

---

## Future Considerations

**Recommended Improvements**:
1. Adopt a migration framework (e.g., Alembic, Flyway, or Supabase Migrations)
2. Add timestamped versioning to migration files
3. Create schema.sql with complete DDL for fresh deployments
4. Implement automated rollback scripts
5. Add migration execution tracking table

---

## Related Documents

- [Schema Overview](./01-schema-overview.md)
- [Tables Reference](./02-tables-reference.md)
- [RPC Functions](./04-rpc-functions.md)
- [RLS Policies](./05-rls-policies.md)
- [Test Generation Database Client](../05-Pipelines/01-test-generation/05-database-client.md)
