---
title: Comprehension Tests — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./comprehension-tests.md
last_updated: 2026-04-10
dependencies:
  - "tests table"
  - "questions table"
  - "test_attempts table"
  - "test_skill_ratings table"
  - "user_skill_ratings table"
  - "process_test_submission() RPC"
  - "get_recommended_tests() RPC"
  - "OpenRouter (test generation)"
  - "Azure TTS (audio generation)"
  - "Cloudflare R2 (audio storage)"
breaking_change_risk: medium
---

# Comprehension Tests — Technical Specification

> **Update (2026-05-21):** When `Config.STUDY_PLAN_ENABLED` is true and the user has a `user_study_plans` row for the language, `get_or_create_daily_load` routes through `build_daily_session` (see [[features/study-plans.tech]]) instead of the legacy `_compute_daily_load`. The daily-load row schema is unchanged plus one new column `daily_test_loads.daily_session_targets jsonb` carrying Practice maint/acq minute targets for the day. `test_attempts` gains `started_at timestamptz` and `duration_ms integer` (FE-supplied; server-computed; for future template tuning). See [[decisions/ADR-008-study-plan-orchestration-layer]].

## Architecture Overview

```
Test Generation (admin-triggered):
  Topic Generation → Production Queue → Test Generation → Audio Synthesis → DB

Test Serving (user-facing):
  /api/tests/recommended → get_recommended_tests() RPC → ELO-matched list
  /api/tests/<slug>      → test + questions payload
  /api/tests/submit      → process_test_submission() RPC → atomic grade + ELO update
```

## Database Impact

**Tables read:** `tests`, `questions`, `test_skill_ratings`, `user_skill_ratings`, `dim_test_types`, `dim_languages`
**Tables written:** `test_attempts`, `test_skill_ratings`, `user_skill_ratings`, `user_vocabulary_knowledge`, `users`, `user_tokens`, `token_transactions`

## API / RPC Surface

### `GET /api/tests/recommended`
- **Purpose:** Return ELO-matched test recommendations for current user + language
- **Auth:** JWT required
- **Returns:** List of `{test_id, slug, test_type, title, difficulty_level, elo_rating, elo_diff, tier}`
- **Calls:** `get_recommended_tests(user_id, language)` RPC

### `GET /api/tests/<slug>`
- **Purpose:** Fetch test content for taking
- **Auth:** JWT required
- **Returns:** Test metadata + questions array (choices, no correct answers)

### `POST /api/tests/submit`
- **Purpose:** Submit answers and get graded results
- **Auth:** JWT required
- **Body:** `{test_id, language_id, test_type_id, responses: [{question_id, selected_answer}], idempotency_key?}`
- **Calls:** `process_test_submission()` — atomic RPC that:
  1. Validates auth + input
  2. Grades each question
  3. Checks idempotency
  4. Calculates new ELO for user and test (via `calculate_elo_rating()`)
     - **First attempt:** full K (user K=32 × volatility; test K=16).
     - **Repeat attempt + in today's daily-load retry slot:** reduced K via time-decay factor `clamp(0.20, days_since_last/60, 1.0)` plus a +0.25 improvement bonus if score gained ≥15 percentage points over prior best. See [[algorithms/elo-ranking.tech]] and [[decisions/ADR-006-retry-slot-reduced-elo]].
     - **Repeat attempt off-recommendation:** zero ELO movement (status quo).
  5. Records attempt in `test_attempts` (including `elo_reduction_factor` if applied)
  6. Updates `user_skill_ratings` and `test_skill_ratings`
  7. Handles free test accounting / token deduction
- **Returns:** `{success, attempt_id, score, total, percentage, elo_change, elo_reduction_factor, question_results}`

## Content Generation Pipeline

Manually triggered by admin. Multi-stage:

1. **Topic Generation** (`services/topic_generation/`)
   - `orchestrator.py` coordinates agents: explorer, archivist, gatekeeper, embedder
   - Explorer proposes topics; Gatekeeper filters; Embedder checks similarity via `match_topics()` RPC
   - Approved topics → `topics` table + `production_queue`

2. **Test Generation** (`services/test_generation/`)
   - Picks items from `production_queue`
   - LLM generates prose transcript + 5 MC questions
   - Question validator checks format and correctness
   - → `tests` + `questions` tables

3. **Audio Synthesis** (Azure TTS)
   - Generates speech from transcript
   - Uploads to R2 → `audio_url` on test record

4. **Vocabulary Extraction** (`services/vocabulary/`)
   - Extracts lemmas + senses from transcript
   - Links to `dim_vocabulary` / `dim_word_senses`
   - Sets `vocab_sense_ids` on test record

## Key Architectural Decisions

1. **Atomic test submission via plpgsql RPC**
   - Rationale: Grading, ELO update, token deduction, and attempt recording must be transactional. A single RPC prevents partial state.
   - Alternatives rejected: Multi-step API calls — race conditions on ELO.

2. **Dual ELO (user + test)**
   - Rationale: Tests that many users fail should rise in ELO; tests everyone passes should drop. This makes matching self-correcting.

3. **Expanding-radius test recommendation**
   - Rationale: Start narrow (ELO ±50) and widen to guarantee a result. Prevents dead ends when test pool is small.

## Testing Strategy

- Unit test: ELO calculation with known inputs/outputs
- Integration test: `process_test_submission` with mock user and test data
- Edge cases: double-submit (idempotency), no tests in ELO range, free test limit exhausted

## Related Pages

- [[features/comprehension-tests]] — Prose description
- [[algorithms/elo-ranking.tech]] — ELO formula details
- [[database/schema.tech]] — Table definitions
