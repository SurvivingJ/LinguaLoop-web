# Prompt Catalog

LinguaDojo uses two kinds of prompt templates: **file-based prompts** stored in the `prompts/` directory (used by the batch scripts and `PromptService`), and **database prompts** stored in the `prompt_templates` Supabase table (used by the production test-generation pipeline).

---

## File-Based Prompts (`prompts/` directory)

These templates are loaded by `PromptService` (`services/prompt_service.py`) via `load_prompt(name)` and formatted with `format_prompt(name, **kwargs)`. Python `str.format()` is used, so literal braces must be doubled (`{{` / `}}`).

### transcript_generation

> **File:** `prompts/transcript_generation.txt`
> **Purpose:** Generates a single-speaker listening-comprehension transcript.
> **Used by:** `LocalTestGenerator._generate_transcript()` in `batch_generate_to_json.py` (line 140), and the production prose-writer agent.

**Variables / Placeholders:**

| Placeholder | Type | Description |
|---|---|---|
| `{language}` | string | Target language (e.g., "english", "chinese") |
| `{difficulty}` | int | Proficiency level 1-9 |
| `{topic}` | string | Topic concept |
| `{style}` | string | Writing style (e.g., "conversational") |

**Output format:** JSON object:
```json
{
  "transcript": "...",
  "difficulty_level": <int>
}
```

**Structure:**
1. Role assignment: "You are a listening-comprehension script writer"
2. Level guidelines for 1-3, 4-6, 7-9 (vocabulary, grammar, speech pace, sentence count)
3. Generation instructions with input variables
4. JSON output specification with double-brace escaping

Source: `prompts/transcript_generation.txt` lines 1-42.

---

### question_generation

> **File:** `prompts/question_generation.txt`
> **Purpose:** Generates a batch of 5 multiple-choice questions with ELO ratings in a single LLM call.
> **Used by:** Production `TestGenerationOrchestrator` (via database templates in production; this file serves as the reference/fallback format).

**Variables / Placeholders:**

| Placeholder | Type | Description |
|---|---|---|
| `{question_id1}` ... `{question_id5}` | string (UUID) | Pre-generated UUIDs for each question |
| `{starting_elo}` | int | Initial ELO rating for all skill types |
| `{timestamp}` | string (ISO) | Timestamp for `last_attempt` |
| `{language}` | string | Target language |
| `{difficulty}` | int | Difficulty level 1-9 |
| `{transcript}` | string | The transcript/prose text |

**Output format:** JSON array of 5 question objects, each containing:
- `id`, `question`, `choices` (4 options), `answer`
- `ratings` object with `listening`, `reading`, and `dictation` sub-objects (each with `rating`, `volatility`, `attempts`, `last_attempt`)

**Level guidelines:**
- Levels 1-3: Simple recognition of high-frequency words
- Levels 4-6: Detail questions and main ideas
- Levels 7-9: Complex inference, attitude, and discourse organization

Source: `prompts/question_generation.txt` lines 1-153.

---

### question_type1

> **File:** `prompts/question_type1.txt`
> **Purpose:** Generates ONE Type 1 question -- simple recognition of high-frequency words.
> **Used by:** `LocalTestGenerator._generate_single_question()` in `batch_generate_to_json.py` (line 196), and the production question-generator agent.

**Variables / Placeholders:**

| Placeholder | Type | Description |
|---|---|---|
| `{previous_questions}` | string | Semicolon-separated list of previously generated questions (or "None") |
| `{language}` | string | Target language |
| `{transcript}` | string | The transcript/prose text |

**Output format:** Single JSON object:
```json
{
  "Question": "...",
  "Answer": "...",
  "Options": ["...", "...", "...", "..."]
}
```

**Key characteristics:**
- Focus on direct word recognition and simple factual recall
- High-frequency vocabulary
- Tests concrete nouns, basic verbs, simple adjectives
- Answers explicitly stated in transcript
- Includes a few-shot example (weather scenario)

Source: `prompts/question_type1.txt` lines 1-37.

---

### question_type2

> **File:** `prompts/question_type2.txt`
> **Purpose:** Generates ONE Type 2 question -- detail questions and main ideas.
> **Used by:** Same as question_type1.

**Variables / Placeholders:** Same as `question_type1` (`{previous_questions}`, `{language}`, `{transcript}`).

**Output format:** Same JSON object format as question_type1.

**Key characteristics:**
- Focus on specific details, main ideas, cause-effect relationships
- Requires understanding of context and connections between ideas
- Tests comprehension of supporting details
- May involve simple inference from explicitly stated information
- Includes a few-shot example (company profits scenario)

Source: `prompts/question_type2.txt` lines 1-37.

---

### question_type3

> **File:** `prompts/question_type3.txt`
> **Purpose:** Generates ONE Type 3 question -- complex inference, attitude, and discourse organization.
> **Used by:** Same as question_type1.

**Variables / Placeholders:** Same as `question_type1` (`{previous_questions}`, `{language}`, `{transcript}`).

**Output format:** Same JSON object format as question_type1.

**Key characteristics:**
- Focus on implied meaning, speaker attitude, discourse structure
- Requires complex inference beyond explicitly stated facts
- Tests understanding of tone, purpose, organizational patterns
- May involve analyzing relationships between different parts of text
- Includes a few-shot example (policy attitude scenario)

Source: `prompts/question_type3.txt` lines 1-37.

---

### prompts/__init__.py

> **File:** `prompts/__init__.py`
> **Purpose:** Makes `prompts/` a Python package. Empty file.

---

## Database Prompts (`prompt_templates` table)

The production test-generation pipeline stores prompt templates in the `prompt_templates` Supabase table rather than reading from files. This enables per-language overrides and versioned rollback without redeployment.

### Table Schema (from `services/test_generation/database_client.py` lines 537-577)

Key columns:
- `task_name` -- template identifier (e.g., `prose_generation`, `question_literal_detail`)
- `language_id` -- FK to `dim_languages` (1=Chinese, 2=English, 3=Japanese)
- `template_text` -- the prompt body
- `version` -- integer, latest version selected via `ORDER BY version DESC LIMIT 1`
- `is_active` -- boolean filter

### Lookup Behavior

The `get_prompt_template(task_name, language_id)` method in the database client (line 529):
1. Queries for `task_name` + `language_id` + `is_active=True`, ordered by `version DESC`, limit 1
2. If not found and `language_id != 2`, falls back to English (`language_id=2`)
3. Returns `None` if neither found (logs a warning)

### How Database Prompts Are Used

In `services/test_generation/orchestrator.py` (line 313), question templates are fetched from the database and passed to the question-generator agent as `prompt_templates` dict keyed by `type_code`. The agent (`services/test_generation/agents/question_generator.py` line 127) uses the database template for each question type if available.

---

## Summary Table

| Template | Type | Variables | Used By | Output Format |
|---|---|---|---|---|
| `transcript_generation` | File | `{language}`, `{difficulty}`, `{topic}`, `{style}` | `LocalTestGenerator`, prose-writer agent | JSON `{transcript, difficulty_level}` |
| `question_generation` | File | `{question_id1-5}`, `{starting_elo}`, `{timestamp}`, `{language}`, `{difficulty}`, `{transcript}` | Production orchestrator (reference format) | JSON array of 5 question objects with ratings |
| `question_type1` | File | `{previous_questions}`, `{language}`, `{transcript}` | `LocalTestGenerator`, question-generator agent | JSON `{Question, Answer, Options}` |
| `question_type2` | File | `{previous_questions}`, `{language}`, `{transcript}` | `LocalTestGenerator`, question-generator agent | JSON `{Question, Answer, Options}` |
| `question_type3` | File | `{previous_questions}`, `{language}`, `{transcript}` | `LocalTestGenerator`, question-generator agent | JSON `{Question, Answer, Options}` |
| `prose_generation` | DB | (language-specific) | Production prose-writer agent | Prose text |
| `question_literal_detail` | DB | (language-specific) | Production question-generator agent | JSON question object |
| (other task_names) | DB | (varies) | Production agents | JSON question object |

---

### Source References
- `prompts/transcript_generation.txt` (lines 1-42)
- `prompts/question_generation.txt` (lines 1-153)
- `prompts/question_type1.txt` (lines 1-37)
- `prompts/question_type2.txt` (lines 1-37)
- `prompts/question_type3.txt` (lines 1-37)
- `prompts/__init__.py` (empty)
- `services/prompt_service.py` (lines 1-63)
- `services/test_generation/database_client.py` (lines 529-577)
- `services/test_generation/agents/question_generator.py` (lines 80-148)
- `services/test_generation/orchestrator.py` (line 313)

### Related Documents
- `Project Knowledge/09-Prompts/02-prompt-design-guidelines.md`
- `Project Knowledge/08-Scripts/04-batch-scripts.md`
- `Project Knowledge/05-Pipelines/` -- pipeline architecture
- `Project Knowledge/03-Database/` -- schema docs for `prompt_templates` table
