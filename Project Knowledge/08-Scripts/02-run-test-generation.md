# run_test_generation.py

> **Path:** `scripts/run_test_generation.py`
> **Invocation:** `python -m scripts.run_test_generation`
> **Role:** Cron-job entry point for the test-generation pipeline.

## Purpose

Processes items from the `production_queue` table and, for each queue item, generates a complete test consisting of:
1. Translated topic concept
2. Prose / transcript text
3. Comprehension questions
4. TTS audio
5. Test title

The script wraps `TestGenerationOrchestrator` with optional per-agent debug instrumentation.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `TEST_GEN_BATCH_SIZE` | `50` | Maximum queue items to process per run |
| `TEST_GEN_TARGET_DIFFICULTIES` | `[4, 6, 9]` | JSON array of difficulty levels to generate |
| `TEST_GEN_DRY_RUN` | `false` | Set `true` to skip database writes |
| `TEST_GEN_LOG_LEVEL` | `INFO` | Logging level (overridden to `DEBUG` when debug mode is on) |
| `TEST_GEN_DEBUG` | `true` | Enable verbose per-agent debug wrappers |

Source: lines 10-16.

## Key Functions

### `setup_logging()` (line 37)

Configures root logger to stdout. When `TEST_GEN_DEBUG` is `true`:
- Forces log level to `DEBUG`
- Sets `DEBUG` on `services.test_generation`, `services.test_generation.orchestrator`, and `services.test_generation.agents`
- Suppresses `httpx`, `httpcore`, `openai`, `urllib3`, `botocore`, and `boto3` to `WARNING`

### `wrap_agent_with_debug(agent, agent_name, logger)` (line 68)

Monkey-patches a single agent's main method to log entry/exit with timing and full tracebacks on failure. Supported agents:

| `agent_name` | Wrapped Method(s) |
|---|---|
| `topic_translator` | `translate()` |
| `prose_writer` | `generate_prose()` |
| `question_generator` | `generate_questions()` |
| `audio_synthesizer` | `generate_and_upload()`, `select_voice()` |
| `title_generator` | `generate_title()` |

Source: lines 68-173.

### `run_with_debug_wrapper(orchestrator, logger)` (line 176)

1. Calls `wrap_agent_with_debug` for all five agents (line 182-187).
2. Monkey-patches `orchestrator._generate_test` to log language config, topic, difficulty, and category before each generation (lines 193-224).
3. Monkey-patches `orchestrator._process_queue_item` to dump the full language config as JSON and log queue-item metadata (lines 229-269).
4. Calls `orchestrator.run()` and returns the metrics object.

### `main()` (line 275)

**Flow:**

```
1. setup_logging()
2. Import SupabaseFactory, TestGenerationOrchestrator, NoQueueItemsError, test_gen_config
3. SupabaseFactory.initialize()
4. Log configuration (batch_size, target_difficulties, dry_run, models)
5. Create TestGenerationOrchestrator()
6. If DEBUG_MODE -> run_with_debug_wrapper(orchestrator)
   Else           -> orchestrator.run()
7. Log metrics (queue_items_processed, tests_generated, tests_failed, duration)
8. Determine exit code
```

## Exit Codes

| Code | Condition |
|---|---|
| `0` | Successful run, or no pending queue items (`NoQueueItemsError`) |
| `1` | Metrics contain an `error_message`, or zero tests generated despite processing queue items, or `ValueError` (configuration error), or unexpected exception |

Source: lines 330-355.

## Orchestrator Integration

The script delegates all work to `TestGenerationOrchestrator` from `services.test_generation.orchestrator`. The orchestrator returns a metrics dataclass with:
- `queue_items_processed`
- `tests_generated`
- `tests_failed`
- `execution_time_seconds`
- `error_message`

---

### Source References
- `scripts/run_test_generation.py` -- full file (lines 1-359)
- `services/test_generation/orchestrator.py` -- `TestGenerationOrchestrator`, `NoQueueItemsError`
- `services/test_generation/config.py` -- `test_gen_config`

### Related Documents
- `Project Knowledge/08-Scripts/01-scripts-overview.md`
- `Project Knowledge/05-Pipelines/` -- pipeline architecture
- `Project Knowledge/08-Scripts/04-batch-scripts.md`
