# GatekeeperAgent

The Gatekeeper agent validates the cultural and linguistic appropriateness of each topic for every target language. It serves as the final quality gate before topics are queued for content generation.

## Source Reference

| File | Path |
|------|------|
| Gatekeeper Agent | `services/topic_generation/agents/gatekeeper.py` (lines 1-185) |
| Base Agent | `services/topic_generation/agents/base.py` (lines 1-120) |

## Class: `GatekeeperAgent`

**Location:** `services/topic_generation/agents/gatekeeper.py`, line 18

**Inherits from:** `BaseAgent`

### Purpose

The Gatekeeper ensures that topics are culturally and linguistically suitable for each target language before they are queued for content generation. A topic about a culture-specific concept may be appropriate for some languages but not others. The Gatekeeper makes this determination by prompting an LLM with the topic details and target language, expecting a YES/NO response.

### Constructor

**Lines:** 24-38

```python
def __init__(self, api_key: str = None, model: str = None):
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | `topic_gen_config.openrouter_api_key` | OpenRouter API key |
| `model` | `str` | `topic_gen_config.llm_model` | LLM model identifier |

Calls `BaseAgent.__init__()` with:
- `base_url`: `https://openrouter.ai/api/v1` (OpenRouter endpoint)
- `name`: `"Gatekeeper"`

Also initializes `self.rejection_count = 0` for tracking.

---

### Method: `validate_for_language()`

**Lines:** 40-100

Validates a single topic for a single target language.

```python
def validate_for_language(
    self,
    candidate: TopicCandidate,
    language: Language,
    prompt_template: str
) -> bool:
```

#### Input Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `candidate` | `TopicCandidate` | Topic with `concept`, `lens_code`, `keywords` |
| `language` | `Language` | Target language with `native_name`, `language_code` |
| `prompt_template` | `str` | Template with placeholders |

#### Template Placeholders

| Placeholder | Source |
|-------------|--------|
| `{topic_concept}` | `candidate.concept` |
| `{lens}` | `candidate.lens_code` |
| `{target_language}` | `language.native_name` |
| `{language_code}` | `language.language_code` |
| `{keywords}` | Comma-separated keywords (max 5), or `"none"` |

#### Processing Logic

1. Formats the prompt template with candidate and language data.
2. Calls `self._call_llm()` with:
   - `json_mode=False` (expects plain text YES/NO response)
   - `temperature=topic_gen_config.gatekeeper_temperature` (default 0.3 for deterministic decisions)
3. Parses the response via `_parse_decision()`.
4. Logs the decision as `APPROVED` or `REJECTED`.

#### Output

Returns `bool`: `True` if approved, `False` if rejected.

#### Error Handling

On any exception during the LLM call:
- Logs the error.
- Increments `self.rejection_count`.
- Returns `False` (fail-safe: reject on error).

---

### Method: `_parse_decision()`

**Lines:** 102-128

Parses the LLM's YES/NO response with progressive matching:

```python
def _parse_decision(self, response: str) -> bool:
```

**Parsing priority:**

1. If response starts with `"yes"` (case-insensitive) -> `True`
2. If response starts with `"no"` (case-insensitive) -> `False`
3. If response contains `"yes"` but not `"no"` -> `True`
4. Otherwise -> `False` (ambiguous responses default to rejection)

This fail-safe approach means the Gatekeeper errs on the side of rejection for unclear LLM outputs.

---

### Method: `validate_for_all_languages()`

**Lines:** 130-180

Validates a topic across all active languages with a short-circuit optimization.

```python
def validate_for_all_languages(
    self,
    candidate: TopicCandidate,
    languages: List[Language],
    prompt_template: str,
    short_circuit_threshold: int = None
) -> List[Language]:
```

#### Input Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `candidate` | `TopicCandidate` | required | Topic to validate |
| `languages` | `List[Language]` | required | All active target languages |
| `prompt_template` | `str` | required | Gatekeeper prompt template |
| `short_circuit_threshold` | `int` | `topic_gen_config.gatekeeper_short_circuit_threshold` (default 3) | Stop after N consecutive rejections |

#### Short-Circuit Logic

If a topic receives N consecutive rejections across languages, it is considered fundamentally unsuitable and validation stops early. This saves API calls for clearly inappropriate topics.

```
consecutive_rejections >= short_circuit_threshold -> break
```

On each approval, `consecutive_rejections` resets to 0.

#### Output

Returns `List[Language]` -- the languages that approved the topic. An empty list means the topic was rejected for all checked languages.

---

### Method: `reset_counts()`

**Lines:** 182-185

Resets both `rejection_count` and the inherited `api_call_count`.

---

### LLM/API Calls

| API | Provider | Model | Temperature | JSON Mode |
|-----|----------|-------|-------------|-----------|
| Chat Completions | OpenRouter | `topic_gen_config.llm_model` (default: `google/gemini-2.0-flash-exp`) | `topic_gen_config.gatekeeper_temperature` (default: 0.3) | No |

Makes **one LLM call per (topic, language) pair**. For a run with 5 approved topics and 3 languages, this could be up to 15 calls (fewer with short-circuiting).

### Configuration Dependencies

| Config Field | Usage |
|-------------|-------|
| `openrouter_api_key` | Authentication for OpenRouter |
| `llm_model` | Model selection |
| `gatekeeper_temperature` | Low temperature for deterministic decisions |
| `gatekeeper_short_circuit_threshold` | Consecutive rejections before stopping |

## Related Documents

- [01-explorer-agent.md](./01-explorer-agent.md) -- Upstream: generates the candidates
- [02-archivist-agent.md](./02-archivist-agent.md) -- Upstream: filters duplicates before Gatekeeper
- [04-embedding-service.md](./04-embedding-service.md) -- Embedding generation (used by Archivist, not Gatekeeper)
- [../02-orchestrator.md](../02-orchestrator.md) -- Orchestrator that drives the Gatekeeper
