# Scripts Overview

All scripts live under `scripts/` and serve one of three roles: **cron-job entry points** (called by a scheduler), **batch utilities** (run manually from the command line), or **data-pipeline helpers** (transform or verify data).

## Script Inventory

| Script | Purpose | Requires Backend | Requires Auth | DB Write | Key Env Vars |
|---|---|---|---|---|---|
| `run_test_generation.py` | Cron entry point -- pulls from `production_queue` and generates complete tests (prose + questions + audio) | No (direct Supabase) | No (service role) | Yes | `TEST_GEN_BATCH_SIZE`, `TEST_GEN_TARGET_DIFFICULTIES`, `TEST_GEN_DRY_RUN`, `TEST_GEN_DEBUG`, `TEST_GEN_LOG_LEVEL` |
| `run_topic_generation.py` | Cron entry point -- generates new topics via LLM with embedding-based dedup | No (direct Supabase) | No (service role) | Yes | `TOPIC_DAILY_QUOTA`, `TOPIC_SIMILARITY_THRESHOLD`, `TOPIC_DRY_RUN`, `TOPIC_LOG_LEVEL` |
| `run_topic_import.py` | CLI tool -- imports topics from a JSON file into the topic generation system | No (direct Supabase) | No (service role) | Yes (unless `--dry-run`) | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` |
| `base_generator.py` | Shared ABC and config for batch scripts -- not run directly | N/A | N/A | N/A | N/A |
| `batch_generate_tests.py` | Batch generate tests via Flask API (requires running backend) | **Yes** | **Yes** (JWT) | Yes (via API) | `API_BASE_URL`, `BATCH_AUTH_TOKEN`, `TEST_COUNT`, `START_FROM` |
| `batch_generate_to_json.py` | Batch generate tests locally to JSON file -- no DB needed | No | No | No | `USE_OPENROUTER`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `TEST_COUNT`, `START_FROM` |
| `upload_tests_to_supabase.py` | Upload a JSON file of generated tests into Supabase | No (direct Supabase) | No (service role) | Yes | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GEN_USER_ID` |
| `json_to_csv.py` | Convert generated-tests JSON into two CSVs (`tests.csv`, `questions.csv`) for Supabase Dashboard import | No | No | No | None |
| `verify_distribution.py` | Standalone sanity check -- prints language/difficulty distribution for 250-test batch configs | No | No | No | None |
| `backfill_test_skill_ratings.py` | One-shot migration -- creates missing `test_skill_ratings` rows using `DIFFICULTY_ELO_MAP` | No (direct Supabase) | No (service role) | Yes (unless `--dry-run`) | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` |

## How to run

All module-style scripts are invoked from the repository root:

```bash
# Cron-job entry points
python -m scripts.run_test_generation
python -m scripts.run_topic_generation

# CLI tools
python -m scripts.run_topic_import --file data/topics.json --dry-run

# Batch utilities (run as plain scripts)
python scripts/batch_generate_tests.py
python scripts/batch_generate_to_json.py
python scripts/upload_tests_to_supabase.py generated_tests_20251209.json
python scripts/json_to_csv.py generated_tests_20251209.json
python scripts/verify_distribution.py
python scripts/backfill_test_skill_ratings.py --dry-run
```

## Typical Workflows

**Production pipeline (automated):**
1. `run_topic_generation.py` -- creates new topics daily
2. `run_test_generation.py` -- picks topics from `production_queue`, generates tests

**Manual bulk-seed (offline):**
1. `batch_generate_to_json.py` -- generate tests to local JSON
2. `upload_tests_to_supabase.py` -- push JSON into database
3. `backfill_test_skill_ratings.py` -- ensure ELO rows exist

**Manual bulk-seed (CSV alternative):**
1. `batch_generate_to_json.py` -- generate tests to local JSON
2. `json_to_csv.py` -- convert to CSV pair
3. Import CSVs via Supabase Dashboard (tests first, then questions)

---

### Source References
- `scripts/run_test_generation.py` (lines 1-359)
- `scripts/run_topic_generation.py` (lines 1-117)
- `scripts/run_topic_import.py` (lines 1-233)
- `scripts/base_generator.py` (lines 1-309)
- `scripts/batch_generate_tests.py` (lines 1-134)
- `scripts/batch_generate_to_json.py` (lines 1-308)
- `scripts/upload_tests_to_supabase.py` (lines 1-146)
- `scripts/json_to_csv.py` (lines 1-149)
- `scripts/verify_distribution.py` (lines 1-72)
- `scripts/backfill_test_skill_ratings.py` (lines 1-150)

### Related Documents
- `Project Knowledge/05-Pipelines/` -- pipeline architecture docs
- `Project Knowledge/08-Scripts/02-run-test-generation.md`
- `Project Knowledge/08-Scripts/03-run-topic-generation.md`
- `Project Knowledge/08-Scripts/04-batch-scripts.md`
- `Project Knowledge/09-Prompts/01-prompt-catalog.md`
