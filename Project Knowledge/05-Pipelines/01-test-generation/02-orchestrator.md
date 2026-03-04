# TestGenerationOrchestrator

**Source:** `services/test_generation/orchestrator.py` (~468 lines)

The `TestGenerationOrchestrator` coordinates the complete test generation workflow. It fetches pending queue items, drives six specialized agents through a structured pipeline, and persists generated tests to the database.

## Class: `TestGenerationOrchestrator`

### Constructor

```python
def __init__(self):
```

1. Validates configuration via `test_gen_config.validate()` -- raises `ValueError` if invalid.
2. Initializes `TestDatabaseClient` for all database operations.
3. Initializes six agents:
   - `TopicTranslator` -- translates topic concepts to target language
   - `ProseWriter` -- generates reading passages
   - `TitleGenerator` -- generates test titles
   - `QuestionGenerator` -- generates MCQ questions
   - `QuestionValidator` -- validates question quality
   - `AudioSynthesizer` -- converts text to speech and uploads audio
4. Initializes metrics tracking (`TestGenMetrics`).

### Method: `run() -> TestGenMetrics`

Main entry point. Executes the full workflow:

1. **Fetch queue items:** Calls `db.get_pending_queue_items(limit=batch_size)`. Filters to active languages only.
2. **Process each item:** Calls `_process_queue_item(item)` inside a try/catch. On success, increments `queue_items_processed` and `tests_generated`. On failure, increments `tests_failed` and marks the queue item as `rejected`.
3. **Finalize:** Calls `_finalize(start_time)` to compute and persist metrics.

Returns `TestGenMetrics` with execution statistics.

### Method: `_process_queue_item(item: QueueItem) -> int`

Processes a single queue item:

1. Marks queue item as `processing`.
2. Loads `Topic` and `LanguageConfig` from database.
3. Gets category name for prompt context.
4. Iterates over `target_difficulties` (default: `[1, 3, 6, 9]`).
5. For each difficulty, calls `_generate_test(...)`.
6. On completion, marks queue item as `active` with the count of tests generated.

Returns the number of tests successfully generated.

### Method: `_generate_test(topic, lang_config, category_name, difficulty) -> bool`

Generates a single test at a specified difficulty level:

| Step | Action | Agent |
|------|--------|-------|
| 0 | Translate topic (skip for English) | TopicTranslator |
| 1 | Generate prose using language-specific template | ProseWriter |
| 1.5 | Generate title (non-fatal on failure) | TitleGenerator |
| 2 | Generate questions per type distribution | QuestionGenerator |
| 3 | Validate questions (min 3 required) | QuestionValidator |
| 3.5 | Generate test UUID for audio filename | -- |
| 4 | Synthesize audio and upload to R2 | AudioSynthesizer |
| 5 | Insert test, questions, and skill ratings | TestDatabaseClient |

Returns `True` on success.

### Method: `_finalize(start_time: float) -> TestGenMetrics`

Computes final metrics:
- `execution_time_seconds` from elapsed wall time.
- Persists metrics to `test_generation_runs` table (skipped in dry_run mode).
- Logs a summary table to the logger.

### Method: `run_single(queue_id: UUID) -> int`

Processes a single queue item by UUID. Used for debugging or targeted re-generation.

## Exception: `NoQueueItemsError`

Raised when no pending queue items are available. Not thrown by the orchestrator itself (it returns early with empty metrics), but available for callers.

## Error Handling Strategy

- **Per-queue-item isolation:** Each queue item is wrapped in its own try/catch. A failure on one item does not prevent processing of subsequent items.
- **Per-difficulty tolerance:** Within a queue item, individual difficulty levels can fail without blocking others.
- **Failed item marking:** On exception, the queue item is marked as `rejected` with the error message stored in `error_log`.
- **Dry run mode:** When `test_gen_config.dry_run` is `True`, no database writes or audio generation occur. All agents still execute their LLM calls for testing.

## Metrics Tracking

The `TestGenMetrics` dataclass tracks:

| Field | Type | Description |
|-------|------|-------------|
| `run_date` | `datetime` | UTC timestamp of run start |
| `queue_items_processed` | `int` | Successfully processed queue items |
| `tests_generated` | `int` | Total tests created |
| `tests_failed` | `int` | Tests that failed to generate |
| `execution_time_seconds` | `int` | Wall time in seconds |
| `error_message` | `str?` | Top-level error if run crashed |

---

### Related Documents

- [Pipeline Overview](./01-pipeline-overview.md)
- [Configuration](./04-config.md)
- [Database Client](./05-database-client.md)
- [Agent Docs](./03-agents/)
