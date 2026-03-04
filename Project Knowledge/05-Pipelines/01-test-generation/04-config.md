# TestGenConfig Reference

**Source:** `services/test_generation/config.py`

The `TestGenConfig` dataclass holds all configuration for the test generation pipeline. Every field can be overridden via environment variables.

## Dataclass Fields

### Generation Parameters

| Field | Type | Default | Env Variable | Description |
|-------|------|---------|--------------|-------------|
| `batch_size` | `int` | `50` | `TEST_GEN_BATCH_SIZE` | Max queue items to process per run |
| `target_difficulties` | `List[int]` | `[1, 3, 6, 9]` | `TEST_GEN_TARGET_DIFFICULTIES` (JSON) | Difficulty levels to generate tests for |
| `questions_per_test` | `int` | `5` | `TEST_GEN_QUESTIONS` | Number of questions per test |

### LLM Configuration (via OpenRouter)

| Field | Type | Default | Env Variable | Description |
|-------|------|---------|--------------|-------------|
| `default_prose_model` | `str` | `google/gemini-2.0-flash-exp` | `TEST_GEN_PROSE_MODEL` | Default model for ProseWriter and TopicTranslator |
| `default_question_model` | `str` | `google/gemini-2.0-flash-exp` | `TEST_GEN_QUESTION_MODEL` | Default model for QuestionGenerator and TitleGenerator |
| `prose_temperature` | `float` | `0.9` | `TEST_GEN_PROSE_TEMP` | Temperature for prose generation |
| `question_temperature` | `float` | `0.7` | `TEST_GEN_QUESTION_TEMP` | Temperature for question generation |

### TTS Configuration

| Field | Type | Default | Env Variable | Description |
|-------|------|---------|--------------|-------------|
| `default_tts_model` | `str` | `tts-1` | `TEST_GEN_TTS_MODEL` | Default TTS model (legacy, Azure uses voices) |
| `default_tts_voice` | `str` | `alloy` | `TEST_GEN_TTS_VOICE` | Default TTS voice |
| `default_tts_speed` | `float` | `1.0` | `TEST_GEN_TTS_SPEED` | Default playback speed |

### Retry Configuration

| Field | Type | Default | Env Variable | Description |
|-------|------|---------|--------------|-------------|
| `max_retries` | `int` | `3` | `TEST_GEN_MAX_RETRIES` | Max LLM call retries |
| `retry_delay` | `float` | `2.0` | `TEST_GEN_RETRY_DELAY` | Base retry delay in seconds |

### Operational Settings

| Field | Type | Default | Env Variable | Description |
|-------|------|---------|--------------|-------------|
| `dry_run` | `bool` | `false` | `TEST_GEN_DRY_RUN` | Skip database writes and audio generation |
| `log_level` | `str` | `INFO` | `TEST_GEN_LOG_LEVEL` | Logging level for the pipeline |

### Identity

| Field | Type | Default | Env Variable | Description |
|-------|------|---------|--------------|-------------|
| `system_user_id` | `str?` | `de6fd05b-...` | `TEST_GEN_SYSTEM_USER_ID` | UUID written to `tests.gen_user` |

### API Keys

| Field | Type | Default | Env Variable | Description |
|-------|------|---------|--------------|-------------|
| `openrouter_api_key` | `str?` | None | `OPENROUTER_API_KEY` | Required for all LLM calls |
| `openai_api_key` | `str?` | None | `OPENAI_API_KEY` | Required for TTS and embedding calls |

## Validation

`validate() -> bool` checks:
- `OPENROUTER_API_KEY` is set
- `OPENAI_API_KEY` is set
- `batch_size >= 1`
- `target_difficulties` is non-empty
- Each difficulty is between 1 and 9

Returns `False` and logs errors if any check fails.

## Initialization

- `__post_init__` warns if API keys are missing and configures the logging level.
- `TEST_GEN_TARGET_DIFFICULTIES` env var is parsed as JSON array (e.g., `[1,3,6,9]`).
- A singleton convenience alias `test_gen_config` is created at module level.

---

### Related Documents

- [Pipeline Overview](./01-pipeline-overview.md)
- [Orchestrator](./02-orchestrator.md)
