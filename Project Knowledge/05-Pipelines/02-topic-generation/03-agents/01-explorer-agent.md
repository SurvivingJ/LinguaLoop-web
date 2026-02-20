# ExplorerAgent

The Explorer agent generates diverse topic candidates by prompting an LLM with a category name and a set of thematic lenses. It is the creative starting point of the topic generation pipeline.

## Source Reference

| File | Path |
|------|------|
| Explorer Agent | `services/topic_generation/agents/explorer.py` (lines 1-181) |
| Base Agent | `services/topic_generation/agents/base.py` (lines 1-120) |

## Class: `ExplorerAgent`

**Location:** `services/topic_generation/agents/explorer.py`, line 19

**Inherits from:** `BaseAgent`

### Purpose

The Explorer is responsible for the ideation phase of the pipeline. Given a category (e.g., "Agriculture") and a list of available lenses (e.g., Historical, Economic, Scientific), it asks an LLM to brainstorm topic ideas. Each idea includes a concept description, a lens assignment, and relevant keywords.

### Constructor

**Lines:** 25-38

```python
def __init__(self, api_key: str = None, model: str = None):
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | `topic_gen_config.openrouter_api_key` | OpenRouter API key |
| `model` | `str` | `topic_gen_config.llm_model` | LLM model identifier |

Calls `BaseAgent.__init__()` with:
- `base_url`: `https://openrouter.ai/api/v1` (OpenRouter endpoint)
- `name`: `"Explorer"`

---

### Method: `generate_candidates()`

**Lines:** 40-118

```python
def generate_candidates(
    self,
    category_name: str,
    active_lenses: List[Lens],
    prompt_template: str,
    num_candidates: int = 10
) -> List[TopicCandidate]:
```

#### Input Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `category_name` | `str` | Category to generate topics for (e.g., `"Agriculture"`) |
| `active_lenses` | `List[Lens]` | Lens objects with `display_name`, `description`, `prompt_hint` |
| `prompt_template` | `str` | Template from `prompt_templates` table with `{category}` and `{available_lenses}` placeholders |
| `num_candidates` | `int` | Target number of candidates (default 10) |

#### Processing Logic

1. **Build lens descriptions** (lines 71-76) -- Formats each lens as `"- {display_name}: {description or prompt_hint}"` and joins them with newlines.
2. **Format prompt** (lines 79-82) -- Substitutes `{category}` and `{available_lenses}` into the prompt template.
3. **Call LLM** (lines 85-89) -- Uses `self._call_llm()` from `BaseAgent` with:
   - `json_mode=True` (requests JSON output format)
   - `temperature=topic_gen_config.llm_temperature` (default 0.8, high creativity)
4. **Parse response** (line 92) -- Calls `_parse_json_response()` to extract the JSON object.
5. **Validate and convert** (lines 98-105) -- Iterates over `data["candidates"]`, validates each item with `_validate_candidate()`, and converts to `TopicCandidate` objects.
6. **Truncate** (line 111) -- Returns at most `num_candidates` items.

#### Output Format

Returns `List[TopicCandidate]` where each item has:

| Field | Type | Description |
|-------|------|-------------|
| `concept` | `str` | English description of the topic idea |
| `lens_code` | `str` | Lowercase lens code (e.g., `"economic"`) |
| `keywords` | `List[str]` | Relevant keyword tags |

#### Expected LLM Response

The LLM is expected to return JSON in this structure:

```json
{
    "candidates": [
        {
            "concept": "The economic impact of precision farming drones",
            "lens": "economic",
            "keywords": ["automation", "technology", "investment"]
        }
    ]
}
```

#### Error Handling

- `json.JSONDecodeError`: Logged and returns empty list.
- General `Exception`: Logged and returns empty list.
- The base `_call_llm()` retries up to 3 times with exponential backoff (2s, 4s, 8s).

---

### Method: `_parse_json_response()`

**Lines:** 120-156

Robust JSON extraction from LLM responses. Handles:

1. Markdown code fences (` ```json ... ``` `)
2. Extra text before/after the JSON object
3. Finding `{` ... `}` boundaries when the response contains surrounding text

Returns an empty `dict` if parsing fails entirely.

---

### Method: `_validate_candidate()`

**Lines:** 158-180

Validates a candidate dictionary has required fields:

- Must contain non-empty `concept` and `lens` keys.
- `concept` must be at least 10 characters long.

Returns `bool`.

---

### LLM/API Calls

| API | Provider | Model | Temperature | JSON Mode |
|-----|----------|-------|-------------|-----------|
| Chat Completions | OpenRouter | `topic_gen_config.llm_model` (default: `google/gemini-2.0-flash-exp`) | `topic_gen_config.llm_temperature` (default: 0.8) | Yes |

Typically makes **1 LLM call per run** (one call generates all candidates for the category).

### Configuration Dependencies

| Config Field | Usage |
|-------------|-------|
| `openrouter_api_key` | Authentication for OpenRouter |
| `llm_model` | Model selection |
| `llm_temperature` | Creativity level for ideation |

## Related Documents

- [02-archivist-agent.md](./02-archivist-agent.md) -- Next stage: novelty checking
- [03-gatekeeper-agent.md](./03-gatekeeper-agent.md) -- Final quality gate
- [04-embedding-service.md](./04-embedding-service.md) -- Embedding generation
- [../02-orchestrator.md](../02-orchestrator.md) -- Orchestrator that drives the Explorer
