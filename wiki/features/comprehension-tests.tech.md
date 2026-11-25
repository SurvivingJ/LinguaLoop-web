---
title: Comprehension Tests — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./comprehension-tests.md
last_updated: 2026-11-23
open_questions:
  - "OPEN: apply migrations/word_quiz_retake_fallback_hardened.sql so a retake gets a post-test word quiz again? Written, NOT applied live (checked 2026-11-23); it needs a product decision."
  - "OPEN: apply migrations/skill_ratings_natural_key_unique.sql and migrations/skill_ratings_writers_on_conflict.sql (pending; see the concurrency note under POST /api/tests/<slug>/submit)."
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
  /api/tests/<slug>/submit → process_test_submission() RPC → atomic grade + ELO update
```

The `/api/tests` blueprint is the package `routes/tests/` (registered in `app.py` with `url_prefix='/api/tests'`). Module map: `routes/tests/catalog.py` (list, recommended, daily-load, single test, history: `get_recommended_tests`, `get_test`, `get_test_with_ratings`, `get_test_history`), `routes/tests/submit.py` (the four submit handlers: `submit_test_attempt`, `submit_pinyin_attempt`, `submit_pitch_accent_attempt`, `submit_dictation_attempt`), `routes/tests/prestudy.py` ([[features/test-prestudy.tech]]), `routes/tests/sentences.py` ([[features/test-sentence-references.tech]]). Post-submission work (timing, vocabulary tracking, response building) lives in `services/attempts.py`.

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

### `POST /api/tests/<slug>/submit` (`submit_test_attempt` in `routes/tests/submit.py`)
- **Purpose:** Submit answers and get graded results
- **Auth:** JWT required
- **Body:** `{responses: [{question_id, selected_answer}], test_mode ('reading' default | 'listening'), furigana_used?, prestudied?, idempotency_key?}` plus optional timing fields; the test, language and test type are resolved server-side from the slug and `test_mode`.
- **Calls:** `process_test_submission()` — atomic RPC that:
  1. Rejects a missing or mismatched caller (`{success:false, error_code:'unauthorized'}`, which the route maps to HTTP 403 `unauthorized`)
  2. Checks idempotency (a retried key returns the cached attempt without regrading)
  3. Grades every question in one set-based query (since 2026-11; before, a temp table and a per-question loop). Learners see no difference.
  4. Calculates new ELO for user and test (via `calculate_elo_rating()`)
     - **First attempt:** full K (user K=32 × volatility; test K=16).
     - **Repeat attempt + in today's daily-load retry slot:** reduced K via time-decay factor `clamp(0.20, days_since_last/60, 1.0)` plus a +0.25 improvement bonus if score gained ≥15 percentage points over prior best. See [[algorithms/elo-ranking.tech]] and [[decisions/ADR-006-retry-slot-reduced-elo]].
     - **Repeat attempt off-recommendation:** zero ELO movement (status quo).
  5. Records attempt in `test_attempts` (including `elo_reduction_factor` if applied)
  6. Updates `user_skill_ratings` and `test_skill_ratings`. Both rows are read `FOR UPDATE`, so concurrent submissions by one learner run one after the other. **Known limitation:** a row that does not exist yet cannot be locked, and neither rating table has a unique key on its natural key (verified live 2026-11-23), so two simultaneous *first-ever* submissions could each insert a rating row. No duplicates exist today. Fix written but not applied: `migrations/skill_ratings_natural_key_unique.sql`, then `migrations/skill_ratings_writers_on_conflict.sql`. See [[algorithms/elo-implementation-analysis.tech]].
  7. Handles free test accounting / token deduction
- **Returns:** `{result: {...}}` built by `build_submission_response` in `services/attempts.py`: attempt id, score, total, percentage, `user_elo_change` / `test_elo_change` (before, after, change), `elo_reduction_factor`, per-question results, explanations and the optional `word_quiz`.
- **Errors:** an RPC failure is logged server-side and returned as HTTP 500 `{error_code:'submission_failed'}` with no database text (`_submission_failure_response` in `routes/tests/submit.py`). The RPC itself still returns `error: SQLERRM` in its `{success:false}` payload (live 2026-11-23; unlike the pinyin, pitch-accent and dictation RPCs it was not switched to the generic envelope), which is why the route must never forward it.

### Post-test word quiz (`word_quiz` in the submit response)

After grading, `track_vocabulary` (`services/attempts.py`) updates word knowledge and asks `build_quiz_with_distractors` (`services/vocabulary/knowledge_service.py`) for up to 5 words. Candidates come from the live RPC `get_word_quiz_candidates`, which offers **only words with `p_known` between 0.25 and 0.75** (excluding words the learner marked unknown), best information score first. Consequence: after a first attempt has moved most of a test's words out of that band, a **retake can get zero candidates, and then no quiz is shown** (`word_quiz` is null). A tiered fallback that fills remaining slots from the test's other tracked words was written but **never applied**; the current hardened version is `migrations/word_quiz_retake_fallback_hardened.sql` (NOT applied, decision required; its rollback file is alongside). The older `migrations/archive/word_quiz_retake_fallback.sql` is archived and must not be applied (it would drop the live security attributes). Wrong options come from `get_quiz_distractors`, which since 2026-11 samples sense ids first and fetches definitions only for the chosen few (same options, same grants; learners see no difference).

## Content Generation Pipeline

Manually triggered by admin. Multi-stage:

1. **Topic Generation** (`services/topic_generation/`)
   - `services/topic_generation/orchestrator.py` coordinates agents: explorer, archivist, gatekeeper, embedder
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

- The Python suite is hermetic: no test can reach Supabase unless it is marked `live` (`tests/conftest.py`); run those deliberately with `pytest -m live`. Route behaviour is tested with fakes (`tests/test_tests_routes_refactor.py`, `tests/test_submission_rpc_error_envelope.py`).
- Unit test: ELO calculation with known inputs/outputs
- SQL tests run against a scratch database, not through pytest (`tests/sql/`; `tests/sql/test_security_review_2026_11.sql` touches `process_test_submission`). There is no SQL test of the set-based grading or the row locks
- Edge cases: double-submit (idempotency), no tests in ELO range, free test limit exhausted

## Related Pages

- [[features/comprehension-tests]] — Prose description
- [[algorithms/elo-ranking.tech]] — ELO formula details
- [[database/schema.tech]] — Table definitions
