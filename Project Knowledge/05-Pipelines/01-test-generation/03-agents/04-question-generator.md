# QuestionGenerator Agent

**Source:** `services/test_generation/agents/question_generator.py` (~285 lines)

The `QuestionGenerator` produces multiple-choice comprehension questions for tests. It supports six semantic question types, each with a distinct cognitive focus, and generates questions sequentially to avoid overlap.

## Class: `QuestionGenerator`

### Constructor

```python
def __init__(self, api_key: str = None, model: str = None):
```

- `api_key`: OpenRouter API key (defaults to `test_gen_config.openrouter_api_key`)
- `model`: LLM model (defaults to `test_gen_config.default_question_model`)
- Initializes an `OpenAI` client with `base_url='https://openrouter.ai/api/v1'`

### Supported Question Types

```python
QUESTION_TYPE_PROMPTS = {
    'literal_detail':     { cognitive_level: 1, ... },
    'vocabulary_context': { cognitive_level: 1, ... },
    'main_idea':          { cognitive_level: 2, ... },
    'supporting_detail':  { cognitive_level: 2, ... },
    'inference':          { cognitive_level: 3, ... },
    'author_purpose':     { cognitive_level: 3, ... },
}
```

Each type has a `name`, `instruction` (used in the prompt), and `cognitive_level` (1=recall, 2=understand, 3=analyze).

### Method: `generate_questions(...) -> List[Dict]`

Generates multiple questions for a prose passage.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `prose` | `str` | The prose/transcript text |
| `language_name` | `str` | Target language name |
| `question_type_codes` | `List[str]` | Ordered list of type codes from `question_type_distributions` |
| `difficulty` | `int` | Difficulty level 1-9 (for template formatting) |
| `prompt_templates` | `Dict[str, str]?` | Map of type_code to database template |
| `model_override` | `str?` | Per-call model override |

**Returns:** `List[Dict]` with keys: `question`, `choices` (List[str]), `answer` (str), `type_code` (str).

**Behavior:**
1. Iterates over `question_type_codes` sequentially.
2. For each type, calls `_generate_single_question(...)`, passing `previous_questions` to avoid overlap.
3. On failure for a single question, logs the error and continues with remaining types.
4. Appends each generated question's text to `previous_questions` for the next iteration.

### Method: `_generate_single_question(...) -> Dict`

Generates a single question of a specified type.

**Prompt Template Placeholders:**
- `{prose}` -- full prose text
- `{difficulty}` -- 1-9 integer
- `{previous_questions}` -- semicolon-separated previous question texts, or "None"
- `{language}` -- target language name

**Returns:** `Dict` with keys: `Question`, `Options` (List of 4 strings), `Answer` (str matching one option).

**Retry:** `@retry` with 3 attempts, exponential backoff (2-10 seconds).

**Temperature:** Uses `test_gen_config.question_temperature` (default 0.7).

### JSON Parsing with Recovery

The `_parse_question_response(content)` method handles LLM output:

1. Strips markdown code blocks (`\`\`\`json ... \`\`\``).
2. Finds JSON object boundaries using brace-matching (handles nested braces and string escapes).
3. Parses JSON via `json.loads()`.
4. **Field normalization:** Maps alternative field names to canonical names:
   - `question_text`, `question`, `questionText` -> `Question`
   - `choices`, `options`, `answers` -> `Options`
   - `correct_answer`, `correctAnswer`, `answer` -> `Answer`
5. Validates: `Question` present, exactly 4 `Options`, `Answer` matches one option.
6. **Answer recovery:** If `Answer` does not match an option:
   - Tries letter mapping (A/B/C/D -> index).
   - Tries partial string matching.
   - Falls back to first option as last resort.

### Expected LLM Output Format

```json
{
    "Question": "Question text here?",
    "Options": ["Option A", "Option B", "Option C", "Option D"],
    "Answer": "The correct option text"
}
```

---

### Related Documents

- [Pipeline Overview](../01-pipeline-overview.md)
- [Orchestrator](../02-orchestrator.md)
- [ProseWriter](./02-prose-writer.md)
- [QuestionValidator](./05-question-validator.md)
- [Database Client](../05-database-client.md) -- question type distributions
