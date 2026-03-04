# EmbeddingService

The Embedding Service generates text embeddings using OpenAI's embedding API. It is used by the Archivist agent for semantic similarity checks and by the import orchestrator for topic storage.

## Source Reference

| File | Path |
|------|------|
| Embedding Service | `services/topic_generation/agents/embedder.py` (lines 1-104) |

## Class: `EmbeddingService`

**Location:** `services/topic_generation/agents/embedder.py`, line 23

**Note:** This class does **not** extend `BaseAgent`. It manages its own OpenAI client directly because it uses the Embeddings API, not Chat Completions.

### Purpose

The Embedding Service converts text strings (semantic signatures) into 1536-dimensional floating-point vectors. These vectors are stored alongside topics in the database and used for cosine similarity searches to prevent semantic duplication.

### Constructor

**Lines:** 26-44

```python
def __init__(self, api_key: str = None, model: str = None):
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | `topic_gen_config.openai_api_key` | OpenAI API key |
| `model` | `str` | `topic_gen_config.embedding_model` | Embedding model identifier |

Initializes:
- `self.dimensions`: Set from `topic_gen_config.embedding_dimensions` (fixed at 1536)
- `self.client`: `OpenAI(api_key=...)` instance
- `self.api_call_count`: Starts at 0

**Raises:** `ValueError` if no API key is available.

---

### Method: `embed_batch()`

**Lines:** 46-86

Generates embeddings for multiple texts in a single API call.

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Exception,)),
    reraise=True
)
def embed_batch(self, texts: List[str]) -> List[List[float]]:
```

#### Input Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `texts` | `List[str]` | Strings to embed (max 2048 items per call per OpenAI limits) |

#### Processing Logic

1. Returns empty list if `texts` is empty.
2. **Sanitize input** (lines 70-73): Replaces newlines with spaces, strips whitespace, and truncates each text to 8000 characters.
3. Calls `self.client.embeddings.create()` with the cleaned texts and model name.
4. Increments `self.api_call_count`.
5. Extracts embedding vectors from the response in order.

#### Output

Returns `List[List[float]]` -- one 1536-dimensional vector per input text, in the same order as the input.

#### Retry Logic

Uses `tenacity` with:
- Max 3 attempts
- Exponential backoff: 2s, 4s, 8s (capped at 10s)
- Retries on any `Exception`
- Re-raises after exhausting retries

---

### Method: `embed_single()`

**Lines:** 88-99

Convenience wrapper for embedding a single text string.

```python
def embed_single(self, text: str) -> List[float]:
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `str` | String to embed |

Calls `embed_batch([text])` and returns the first result, or an empty list if the batch returned nothing.

---

### Method: `reset_call_count()`

**Lines:** 101-103

Resets `self.api_call_count` to 0.

---

### API Calls

| API | Provider | Model | Dimensions |
|-----|----------|-------|------------|
| Embeddings | OpenAI | `topic_gen_config.embedding_model` (default: `text-embedding-3-small`) | 1536 |

The number of API calls depends on usage:
- **Generation pipeline:** One call per candidate that reaches the Archivist (each `check_novelty` call embeds one signature).
- **Import pipeline:** One call per imported topic entry.

### Configuration Dependencies

| Config Field | Usage |
|-------------|-------|
| `openai_api_key` | Authentication for OpenAI |
| `embedding_model` | Model selection (default: `text-embedding-3-small`) |
| `embedding_dimensions` | Fixed at 1536 for `text-embedding-3-small` |

## Related Documents

- [02-archivist-agent.md](./02-archivist-agent.md) -- Primary consumer of the Embedding Service
- [01-explorer-agent.md](./01-explorer-agent.md) -- Upstream agent that generates candidates
- [../04-config.md](../04-config.md) -- Configuration including embedding settings
