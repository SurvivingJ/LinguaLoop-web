# TopicGenConfig

`TopicGenConfig` is a dataclass that holds all configuration for the topic generation system. Every field can be overridden via environment variables. A module-level singleton provides convenient access.

## Source Reference

| File | Path |
|------|------|
| Config | `services/topic_generation/config.py` (lines 1-116) |

## Class: `TopicGenConfig`

**Location:** `services/topic_generation/config.py`, line 17

**Type:** `@dataclass`

### Configuration Fields

#### Generation Parameters

| Field | Type | Default | Env Var | Description |
|-------|------|---------|---------|-------------|
| `daily_topic_quota` | `int` | `5` | `TOPIC_DAILY_QUOTA` | Maximum topics approved per run |
| `similarity_threshold` | `float` | `0.85` | `TOPIC_SIMILARITY_THRESHOLD` | Cosine similarity threshold for duplicate detection (0.5-1.0) |
| `max_candidates_per_run` | `int` | `10` | `TOPIC_MAX_CANDIDATES` | Number of candidates requested from Explorer |

#### LLM Configuration (via OpenRouter)

| Field | Type | Default | Env Var | Description |
|-------|------|---------|---------|-------------|
| `llm_model` | `str` | `google/gemini-2.0-flash-exp` | `TOPIC_LLM_MODEL` | Model identifier for Explorer and Gatekeeper |
| `llm_temperature` | `float` | `0.8` | `TOPIC_LLM_TEMPERATURE` | Temperature for Explorer ideation (high for creativity) |

#### Embedding Configuration (via OpenAI)

| Field | Type | Default | Env Var | Description |
|-------|------|---------|---------|-------------|
| `embedding_model` | `str` | `text-embedding-3-small` | `TOPIC_EMBEDDING_MODEL` | OpenAI embedding model |
| `embedding_dimensions` | `int` | `1536` | (not configurable) | Fixed dimension count for `text-embedding-3-small` |

#### Gatekeeper Configuration

| Field | Type | Default | Env Var | Description |
|-------|------|---------|---------|-------------|
| `gatekeeper_temperature` | `float` | `0.3` | `TOPIC_GATEKEEPER_TEMPERATURE` | Low temperature for deterministic YES/NO decisions |
| `gatekeeper_short_circuit_threshold` | `int` | `3` | `TOPIC_GATEKEEPER_SHORT_CIRCUIT` | Stop after N consecutive rejections per topic |

#### Operational Settings

| Field | Type | Default | Env Var | Description |
|-------|------|---------|---------|-------------|
| `dry_run` | `bool` | `False` | `TOPIC_DRY_RUN` | Skip all database writes when `"true"` |
| `log_level` | `str` | `INFO` | `TOPIC_LOG_LEVEL` | Logging level for `services.topic_generation` logger |

#### API Keys

| Field | Type | Default | Env Var | Description |
|-------|------|---------|---------|-------------|
| `openrouter_api_key` | `Optional[str]` | `None` | `OPENROUTER_API_KEY` | API key for OpenRouter (Explorer + Gatekeeper LLM calls) |
| `openai_api_key` | `Optional[str]` | `None` | `OPENAI_API_KEY` | API key for OpenAI (embedding generation) |

---

### Post-Initialization (`__post_init__`)

**Lines:** 69-79

Called automatically after dataclass construction:

1. Logs a warning if `OPENROUTER_API_KEY` is not set.
2. Logs a warning if `OPENAI_API_KEY` is not set.
3. Sets the logging level for the `services.topic_generation` logger to the value of `log_level`.

---

### Method: `validate()`

**Lines:** 81-99

```python
def validate(self) -> bool:
```

Checks all required configuration is present and valid. Returns `True` if configuration is valid, `False` otherwise.

**Validation rules:**

| Check | Error Message |
|-------|--------------|
| `openrouter_api_key` must be set | `"OPENROUTER_API_KEY is required"` |
| `openai_api_key` must be set | `"OPENAI_API_KEY is required"` |
| `daily_topic_quota >= 1` | `"TOPIC_DAILY_QUOTA must be >= 1"` |
| `0.5 <= similarity_threshold <= 1.0` | `"TOPIC_SIMILARITY_THRESHOLD must be between 0.5 and 1.0"` |

All errors are logged individually via `logger.error()` before returning `False`.

---

## Singleton Pattern

**Lines:** 102-115

Two access patterns are provided:

### 1. `get_topic_gen_config()` function

**Lines:** 106-111

Lazy singleton. Creates the instance on first call and returns the cached instance on subsequent calls.

```python
_config_instance: Optional[TopicGenConfig] = None

def get_topic_gen_config() -> TopicGenConfig:
    global _config_instance
    if _config_instance is None:
        _config_instance = TopicGenConfig()
    return _config_instance
```

### 2. `topic_gen_config` module-level instance

**Line:** 115

Eagerly created at module import time:

```python
topic_gen_config = TopicGenConfig()
```

This is the instance used by all agents and the orchestrator (`from .config import topic_gen_config`).

---

## Environment Variable Override Pattern

All fields use `dataclasses.field(default_factory=lambda: ...)` to read environment variables at instantiation time. This means:

- Environment variables are read once when the config object is created.
- Changing environment variables after instantiation has no effect on the existing instance.
- The `topic_gen_config` module-level instance is created at import time, so env vars must be set before the module is first imported.

## Related Documents

- [01-pipeline-overview.md](./01-pipeline-overview.md) -- Pipeline architecture overview
- [02-orchestrator.md](./02-orchestrator.md) -- Orchestrator that reads config at runtime
- [03-agents/](./03-agents/) -- Agents that consume config values
