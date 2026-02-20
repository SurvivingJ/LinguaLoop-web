# TitleGenerator Agent

**Source:** `services/test_generation/agents/title_generator.py` (~208 lines)

The `TitleGenerator` creates concise, difficulty-appropriate titles for listening comprehension tests. Titles are generated in the target language and their complexity scales with the CEFR level.

## Class: `TitleGenerator`

### Constructor

```python
def __init__(self, api_key: str = None, model: str = None):
```

- `api_key`: OpenRouter API key (defaults to `test_gen_config.openrouter_api_key`)
- `model`: LLM model (defaults to `test_gen_config.default_question_model` -- uses the lighter question model)
- Initializes an `OpenAI` client with `base_url='https://openrouter.ai/api/v1'`

### Method: `generate_title(...) -> str`

Generates a title for a test based on its prose content.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `prose` | `str` | The generated prose/transcript text |
| `topic_concept` | `str` | Topic concept (translated to target language) |
| `difficulty` | `int` | Difficulty level 1-9 |
| `cefr_level` | `str` | CEFR level code (e.g., "A1", "B2") |
| `language_name` | `str` | Target language name |
| `language_code` | `str` | ISO language code |
| `prompt_template` | `str?` | Custom template from `prompt_templates` table |
| `model_override` | `str?` | Per-call model override |

**Returns:** `str` -- title text in the target language.

**Prompt Template Placeholders:**
- `{prose}` -- full prose text
- `{topic_concept}` -- translated topic
- `{difficulty}` -- 1-9 integer
- `{cefr_level}` -- e.g., "B2"
- `{language}` / `{language_code}`

**Language-Specific Templates:**
The database stores separate `title_generation` prompt templates per language (English, Chinese, Japanese), allowing culturally appropriate title styling.

**Retry:** `@retry` with 3 attempts, exponential backoff (2-10 seconds).

**Temperature:** Fixed at 0.7 for moderate creativity.

### Title Length by Difficulty

The default prompt scales title complexity:

| Difficulty | CEFR | Style Guidance |
|------------|------|---------------|
| 1-2 | A1 | Very simple and short (3-6 words) |
| 3-4 | A2 | Simple and concise (4-8 words) |
| 5 | B1 | Clear and straightforward (5-10 words) |
| 6 | B2 | Moderately descriptive (6-12 words) |
| 7 | C1 | Sophisticated and nuanced (8-15 words) |
| 8-9 | C2 | Complex and detailed (10-18 words) |

### Method: `_clean_response(content: str) -> str`

Post-processes LLM output:
1. Strips markdown code blocks.
2. Unwraps JSON objects (tries keys: `title`, `Title`, `text`, `content`).
3. Removes leading/trailing quotes.
4. Strips common LLM prefixes (`Title: `, `title: `, `TITLE: `).

### Error Handling

Title generation failures are **non-fatal** in the orchestrator. If the agent raises an exception, the test is saved with `title = NULL`.

---

### Related Documents

- [Pipeline Overview](../01-pipeline-overview.md)
- [Orchestrator](../02-orchestrator.md)
- [ProseWriter](./02-prose-writer.md)
