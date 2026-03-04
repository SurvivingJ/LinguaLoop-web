# run_topic_generation.py

> **Path:** `scripts/run_topic_generation.py`
> **Invocation:** `python -m scripts.run_topic_generation`
> **Role:** Cron-job entry point for the topic-generation pipeline.

## Purpose

Generates new topics by invoking an LLM, performs embedding-based similarity deduplication, and inserts accepted topics into the database. The script wraps `TopicGenerationOrchestrator`.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `TOPIC_DAILY_QUOTA` | `5` | Number of topics to generate per run |
| `TOPIC_SIMILARITY_THRESHOLD` | `0.85` | Cosine-similarity threshold for dedup |
| `TOPIC_DRY_RUN` | `false` | Set `true` to test without saving |
| `TOPIC_LOG_LEVEL` | `INFO` | Logging level |

Source: lines 7-11.

## Key Functions

### `setup_logging()` (line 33)

Configures root logger and the `services.topic_generation` logger to the level from `TOPIC_LOG_LEVEL`. Suppresses `httpx` and `httpcore` to `WARNING`.

### `main()` (line 55)

**Flow:**

```
1. setup_logging()
2. Import SupabaseFactory, TopicGenerationOrchestrator,
   NoEligibleCategoryError, topic_gen_config
3. SupabaseFactory.initialize()
4. Log configuration (daily_quota, similarity_threshold, llm_model,
   embedding_model, dry_run)
5. Create TopicGenerationOrchestrator()
6. metrics = orchestrator.run()
7. Determine exit code from metrics
```

## Exit Codes

| Code | Condition | Severity |
|---|---|---|
| `0` | All topics generated (quota met), **or** `NoEligibleCategoryError` (nothing to do) | Success |
| `1` | Partial success -- topics generated but count is below `daily_topic_quota` | Warning |
| `2` | `metrics.error_message` is set, or an unhandled exception | Failure |

Source: lines 13-16 (docstring) and lines 91-112 (implementation).

The three-tier exit-code scheme allows monitoring systems to distinguish between "soft" quota misses (exit 1) and hard failures (exit 2). The `NoEligibleCategoryError` case exits `0` because it is an expected steady-state condition (e.g., all categories already have enough topics).

## Orchestrator Integration

Delegates to `TopicGenerationOrchestrator` from `services.topic_generation.orchestrator`. The orchestrator returns a metrics object with:
- `topics_generated` -- compared against `daily_topic_quota` for exit code
- `error_message` -- triggers exit code 2 when set

Configuration is loaded from `services.topic_generation.config.topic_gen_config`.

## run_topic_import.py (companion script)

`scripts/run_topic_import.py` provides a CLI for importing topics from a JSON file rather than generating them. It uses `TopicImportOrchestrator`.

### Arguments

| Flag | Short | Default | Description |
|---|---|---|---|
| `--file` | `-f` | (required) | Path to JSON file containing topics |
| `--category` | `-t` | `Import: {filename}` | Category name |
| `--lens` | `-e` | `cultural` | Default lens code if not in JSON |
| `--dry-run` | `-d` | `false` | Validate without database changes |
| `--skip-gatekeeper` | -- | `false` | Skip cultural validation |
| `--skip-novelty` | -- | `false` | Skip duplicate checking |
| `--validate-only` | -- | `false` | Only validate JSON format |
| `--verbose` | `-v` | `false` | Enable verbose logging |

### Exit codes

| Code | Condition |
|---|---|
| `0` | Success, or validation passed (`--validate-only`) |
| `1` | Validation errors, or no topics imported (all rejected) |
| `2` | Import error or fatal exception |

### JSON format

```json
{
  "topics": [
    {
      "topic": "Topic concept in English",
      "languages": ["zh", "ja", "en"],
      "keywords": ["optional", "tags"],
      "lens_code": "cultural"
    }
  ]
}
```

Source: `scripts/run_topic_import.py` lines 1-233.

---

### Source References
- `scripts/run_topic_generation.py` -- full file (lines 1-117)
- `scripts/run_topic_import.py` -- full file (lines 1-233)
- `services/topic_generation/orchestrator.py` -- `TopicGenerationOrchestrator`, `NoEligibleCategoryError`
- `services/topic_generation/config.py` -- `topic_gen_config`
- `services/topic_generation/import_orchestrator.py` -- `TopicImportOrchestrator`
- `services/topic_generation/json_importer.py` -- `JSONTopicImporter`

### Related Documents
- `Project Knowledge/08-Scripts/01-scripts-overview.md`
- `Project Knowledge/05-Pipelines/` -- pipeline architecture
- `Project Knowledge/08-Scripts/02-run-test-generation.md`
