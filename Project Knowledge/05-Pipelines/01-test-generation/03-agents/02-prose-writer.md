# ProseWriter Agent

**Source:** `services/test_generation/agents/prose_writer.py` (~158 lines)

The `ProseWriter` generates reading passage / listening transcript content for comprehension tests. It produces prose in the target language at a specified CEFR difficulty level.

## Class: `ProseWriter`

### Constructor

```python
def __init__(self, api_key: str = None, model: str = None):
```

- `api_key`: OpenRouter API key (defaults to `test_gen_config.openrouter_api_key`)
- `model`: LLM model (defaults to `test_gen_config.default_prose_model`)
- Initializes an `OpenAI` client with `base_url='https://openrouter.ai/api/v1'`

### Method: `generate_prose(...) -> str`

Generates a prose passage for a test.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `topic_concept` | `str` | Topic in target language (translated) |
| `language_name` | `str` | Target language name (e.g., "Spanish") |
| `language_code` | `str` | ISO language code (e.g., "es") |
| `difficulty` | `int` | Difficulty level 1-9 |
| `word_count_min` | `int` | Minimum word count from CEFR config |
| `word_count_max` | `int` | Maximum word count from CEFR config |
| `keywords` | `list?` | Keywords in target language |
| `cefr_level` | `str?` | CEFR level code (e.g., "A1", "B2") |
| `prompt_template` | `str?` | Custom template from `prompt_templates` table |
| `model_override` | `str?` | Per-call model override from `dim_languages` |

**Returns:** `str` -- generated prose text in the target language.

**Prompt Template Placeholders:**
When a database template is provided, these placeholders are filled:
- `{topic_concept}` -- translated topic
- `{keywords}` -- comma-separated keyword string
- `{cefr_level}` -- e.g., "B2"
- `{min_words}` / `{max_words}` -- word count range
- `{language}` / `{language_code}` / `{difficulty}`

If no template is provided, a hardcoded default prompt is used with the same parameters.

**Retry:** `@retry` with 3 attempts, exponential backoff (2-10 seconds).

**Temperature:** Uses `test_gen_config.prose_temperature` (default 0.9) for creative variety.

### Method: `_clean_response(content: str) -> str`

Post-processes LLM output:
1. Strips markdown code blocks.
2. Unwraps JSON objects (tries keys: `prose`, `transcript`, `text`, `content`).
3. Removes leading/trailing quotes.

### Method: `reset_call_count() -> None`

Resets `api_call_count` to 0.

## CEFR Level Mapping

If `cefr_level` is not provided, the agent maps difficulty to CEFR internally:

| Difficulty | CEFR |
|------------|------|
| 1-2 | A1 |
| 3-4 | A2 |
| 5 | B1 |
| 6 | B2 |
| 7 | C1 |
| 8-9 | C2 |

---

### Related Documents

- [Pipeline Overview](../01-pipeline-overview.md)
- [Orchestrator](../02-orchestrator.md)
- [TopicTranslator](./01-topic-translator.md)
- [QuestionGenerator](./04-question-generator.md)
