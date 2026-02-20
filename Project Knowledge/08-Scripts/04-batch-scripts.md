# Batch and Utility Scripts

This document covers the non-cron scripts used for bulk test generation, data transformation, distribution verification, and database backfills.

---

## base_generator.py

> **Path:** `scripts/base_generator.py`
> **Role:** Shared abstract base class and configuration for batch generation scripts. Not run directly.

### TOPIC_DIFFICULTY_CONFIGS (line 19)

A nested dictionary mapping `language -> level -> List[(topic, difficulty)]` for three languages (English, Chinese, Japanese) across three tiers (beginner, intermediate, advanced). Each tier contains 9 topic-difficulty pairs with difficulties 1-3 (beginner), 4-6 (intermediate), and 7-9 (advanced).

```python
TOPIC_DIFFICULTY_CONFIGS = {
    'english': {
        'beginner': [('Daily routines', 1), ('Family members', 1), ...],   # 9 pairs
        'intermediate': [('Travel planning', 4), ...],                      # 9 pairs
        'advanced': [('Economic trends', 7), ...],                          # 9 pairs
    },
    'chinese': { ... },
    'japanese': { ... }
}
```

Source: lines 19-125.

### BaseTestGenerator (ABC) (line 131)

Abstract base class that provides the shared run loop, stats tracking, progress reporting, and error logging for all batch generators.

**Constructor:** `__init__(self, name: str = "Batch Test Generation")` -- initializes `self.stats` dict with `total`, `success`, `failed`, `errors`, `start_time`, `end_time`.

**Abstract method:** `generate_test(self, config: Dict) -> bool` -- subclasses implement per-test generation logic.

**Key concrete methods:**

| Method | Line | Description |
|---|---|---|
| `generate_test_configs(count=250)` | 164 | Produces a balanced list of test configs: 83 English, 83 Chinese, 84 Japanese. Each language splits evenly across beginner/intermediate/advanced with remainder distributed round-robin. |
| `run(configs, delay=2.0, start_from=0)` | 205 | Main loop -- iterates configs, calls `generate_test()`, prints progress every 10 tests, applies rate-limiting delay, and saves error log on completion. |
| `record_error(config, error)` | 285 | Appends an error entry (config + message + timestamp) to `self.stats['errors']`. |
| `print_config_summary(configs)` | 293 | Prints per-language counts and difficulty-band distribution. |
| `_save_error_log()` | 270 | Writes `batch_errors_{timestamp}.json` if any errors accumulated. |

---

## batch_generate_tests.py (API Mode)

> **Path:** `scripts/batch_generate_tests.py`
> **Invocation:** `python scripts/batch_generate_tests.py`
> **Requires:** Running Flask backend + JWT token

### APITestGenerator (line 27)

Subclass of `BaseTestGenerator`. Generates tests by calling the Flask API endpoint `POST /api/tests/generate_test`.

**Key details:**
- Uses `requests.Session` with JWT `Authorization: Bearer` header (line 38-41)
- Sends payload: `{language, difficulty, topic, style, tier}` (lines 47-53)
- Timeout per request: 120 seconds (line 58)
- Prints slug prefix and audio status on success (line 64-65)

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `API_BASE_URL` | `http://localhost:5000` | Flask API base URL |
| `BATCH_AUTH_TOKEN` | (required) | JWT token from browser DevTools |
| `TEST_COUNT` | `250` | Number of tests to generate |
| `START_FROM` | `0` | Resume index after interruption |

### How to obtain a JWT token (from script help text, lines 97-102):
1. Login to LinguaDojo via the web app
2. Open browser DevTools > Network tab
3. Look for the `/verify-otp` request
4. Copy `jwt_token` from the response
5. `export BATCH_AUTH_TOKEN='your_token'`

Source: lines 1-134.

---

## batch_generate_to_json.py (Local/JSON Mode)

> **Path:** `scripts/batch_generate_to_json.py`
> **Invocation:** `python scripts/batch_generate_to_json.py`
> **Requires:** OpenRouter or OpenAI API key. No database needed.

### LocalTestGenerator (line 46)

Subclass of `BaseTestGenerator`. Generates tests locally using AI APIs and stores results in memory, saving to `generated_tests_{timestamp}.json` when the run completes.

**AI client initialization** (`initialize_ai_client`, line 56):
- If `USE_OPENROUTER=true` and `OPENROUTER_API_KEY` is set, uses OpenRouter endpoint
- Otherwise falls back to `OPENAI_API_KEY` with standard OpenAI client
- Raises `ValueError` if neither key is available

**Language-specific model config** (line 30):

| Language | Transcript Model | Questions Model |
|---|---|---|
| English | `google/gemini-2.0-flash-001` | `google/gemini-2.0-flash-001` |
| Chinese | `deepseek/deepseek-chat` | `deepseek/deepseek-chat` |
| Japanese | `qwen/qwen-2.5-72b-instruct` | `qwen/qwen-2.5-72b-instruct` |

When not using OpenRouter, all languages default to `gpt-4o-mini` (line 81).

**Test creation flow** (`_create_test`, line 99):
1. `_generate_transcript()` -- formats `transcript_generation` prompt via `PromptService`, calls LLM (temperature=1), extracts transcript from JSON wrapper if needed
2. `_generate_questions()` -- uses a difficulty-based type distribution (line 174-178), generates one question at a time using type-specific prompts (`question_type1`, `question_type2`, `question_type3`)
3. Assembles complete test dict with UUID slug, metadata, and questions

**Question type distribution by difficulty** (line 174):

| Difficulty | Type sequence |
|---|---|
| 1-2 | `[1, 1, 1, 1, 1]` |
| 3-4 | `[1, 1, 1, 2, 2]` |
| 5-6 | `[1, 2, 2, 2, 3]` |
| 7 | `[2, 2, 2, 2, 3]` |
| 8 | `[2, 2, 2, 3, 3]` |
| 9 | `[2, 2, 3, 3, 3]` |

**Run override** (line 248): Sets `delay=0` (no rate limiting needed for local generation) and calls `_save_results()` after the base run loop completes.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `USE_OPENROUTER` | `false` | Use OpenRouter instead of OpenAI |
| `OPENROUTER_API_KEY` | -- | OpenRouter API key |
| `OPENAI_API_KEY` | -- | OpenAI API key (fallback) |
| `TEST_COUNT` | `250` | Number of tests to generate |
| `START_FROM` | `0` | Resume index |

Source: lines 1-308.

---

## upload_tests_to_supabase.py

> **Path:** `scripts/upload_tests_to_supabase.py`
> **Invocation:** `python scripts/upload_tests_to_supabase.py <json_file>`

Uploads tests from a JSON file (produced by `batch_generate_to_json.py`) into Supabase. For each test:
1. Inserts a row into the `tests` table (line 81)
2. Retrieves the auto-generated `test_id`
3. Inserts each question into the `questions` table with the `test_id` foreign key (lines 85-96)

Saves upload errors to `upload_errors_{timestamp}.json` on failure.

### Environment Variables

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (admin access) |
| `GEN_USER_ID` | UUID of the user to attribute tests to (falls back to interactive prompt) |

Source: lines 1-146.

---

## json_to_csv.py

> **Path:** `scripts/json_to_csv.py`
> **Invocation:** `python scripts/json_to_csv.py <json_file>`

Converts a generated-tests JSON file into two CSV files for manual import via the Supabase Dashboard:
- `{base}_tests.csv` -- one row per test, matching the `tests` table schema
- `{base}_questions.csv` -- one row per question, with `choices` and `correct_answer` serialized as JSON strings for the JSONB columns

**Important notes** (from script output, lines 122-129):
- The `gen_user` column in tests CSV is left empty -- must be filled manually before import
- Import order matters due to foreign keys: tests first, then questions
- Each row gets a fresh UUID `id` (line 41)

Source: lines 1-149.

---

## verify_distribution.py

> **Path:** `scripts/verify_distribution.py`
> **Invocation:** `python scripts/verify_distribution.py`

A standalone sanity-check script that simulates the `generate_test_configs()` logic from `BaseTestGenerator` and prints the resulting distribution. Verifies that 250 configs split into 83 English + 83 Chinese + 84 Japanese, each with balanced beginner/intermediate/advanced bands. Exits with a pass/fail message (line 71).

No environment variables or database access required.

Source: lines 1-72.

---

## backfill_test_skill_ratings.py

> **Path:** `scripts/backfill_test_skill_ratings.py`
> **Invocation:** `python scripts/backfill_test_skill_ratings.py [--dry-run]`

A one-shot migration script that creates `test_skill_ratings` rows for tests that are missing them.

### DIFFICULTY_ELO_MAP (line 35)

Maps difficulty levels 1-9 to initial ELO ratings:

| Difficulty | CEFR | ELO |
|---|---|---|
| 1 | A1 | 800 |
| 2 | A1+ | 950 |
| 3 | A2 | 1100 |
| 4 | B1 | 1250 |
| 5 | B1+ | 1400 |
| 6 | B2 | 1550 |
| 7 | C1 | 1700 |
| 8 | C1+ | 1850 |
| 9 | C2 | 2000 |

This mapping mirrors `get_initial_elo()` in the test-generation database client.

### BackfillRunner (line 48)

| Method | Description |
|---|---|
| `get_active_test_types()` | Fetches active entries from `dim_test_types` (listening, reading, dictation, etc.) |
| `get_tests_missing_ratings()` | Finds tests with no rows in `test_skill_ratings` by comparing all test IDs against existing rating `test_id` values |
| `run()` | Iterates missing tests, calls `_process_test()` for each |
| `_process_test(test, active_types)` | For a single test: filters test types by audio availability (types with `requires_audio` need `audio_url`), then batch-inserts rating rows with the mapped ELO, `volatility=1.0`, and `total_attempts=0` |

### Dry-run mode
When `--dry-run` is passed, logs what would be inserted but skips the actual `INSERT` (line 124-126).

Source: lines 1-150.

---

### Source References
- `scripts/base_generator.py` (lines 1-309)
- `scripts/batch_generate_tests.py` (lines 1-134)
- `scripts/batch_generate_to_json.py` (lines 1-308)
- `scripts/upload_tests_to_supabase.py` (lines 1-146)
- `scripts/json_to_csv.py` (lines 1-149)
- `scripts/verify_distribution.py` (lines 1-72)
- `scripts/backfill_test_skill_ratings.py` (lines 1-150)
- `services/prompt_service.py` (lines 1-63)

### Related Documents
- `Project Knowledge/08-Scripts/01-scripts-overview.md`
- `Project Knowledge/08-Scripts/02-run-test-generation.md`
- `Project Knowledge/09-Prompts/01-prompt-catalog.md`
