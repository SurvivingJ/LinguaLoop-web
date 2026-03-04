# TopicTranslator Agent

**Source:** `services/test_generation/agents/topic_translator.py` (~160 lines)

The `TopicTranslator` translates English topic concepts and keywords into the target language before prose generation. This ensures that downstream agents (ProseWriter, TitleGenerator) receive prompts in the correct language for non-English content.

## Class: `TopicTranslator`

### Constructor

```python
def __init__(self, api_key: str = None, model: str = None):
```

- `api_key`: OpenRouter API key (defaults to `test_gen_config.openrouter_api_key`)
- `model`: LLM model (defaults to `test_gen_config.default_prose_model`)
- Initializes an `OpenAI` client with `base_url='https://openrouter.ai/api/v1'`
- Tracks API call count via `self.api_call_count`

### Method: `translate(topic_concept, keywords, target_language, model_override) -> Tuple[str, List[str]]`

Translates a topic concept and keyword list to the target language.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `topic_concept` | `str` | English topic concept from `topics.concept_english` |
| `keywords` | `List[str]` | English keywords from the topic |
| `target_language` | `str` | Target language name (e.g., "Chinese", "Japanese") |
| `model_override` | `str?` | Optional per-call model override |

**Returns:** `Tuple[str, List[str]]` -- `(translated_concept, translated_keywords)`

**Behavior:**
1. Constructs a prompt requesting natural translation (not word-for-word).
2. Requests JSON output: `{"topic": "...", "keywords": ["..."]}`.
3. Parses JSON from the LLM response, handling markdown code blocks.
4. On JSON parse failure, returns the original English values as fallback.
5. Uses low temperature (0.3) for deterministic translation.

**Retry:** `@retry` with 2 attempts, exponential backoff (1-5 seconds).

### Method: `should_translate(language_code: str) -> bool`

Returns `True` if translation is needed. Returns `False` for English codes: `en`, `en-us`, `en-gb`, `english`.

### Method: `reset_call_count() -> None`

Resets `api_call_count` to 0.

## Data Flow

```
Orchestrator
  |-- topic.concept_english ("The history of farriery")
  |-- topic.keywords (["blacksmith", "horses"])
  |-- lang_config.language_name ("Chinese")
  v
TopicTranslator.translate()
  |-- LLM call via OpenRouter
  v
(translated_concept, translated_keywords)
  |-- Passed to ProseWriter.generate_prose()
  |-- Passed to TitleGenerator.generate_title()
```

---

### Related Documents

- [Pipeline Overview](../01-pipeline-overview.md)
- [Orchestrator](../02-orchestrator.md)
- [ProseWriter](./02-prose-writer.md)
