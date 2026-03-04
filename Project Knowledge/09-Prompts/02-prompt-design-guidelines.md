# Prompt Design Guidelines

**Purpose**: Document the prompt engineering patterns, conventions, and best practices used throughout the LinguaLoop/LinguaDojo AI pipelines.

---

## Core Principles

### 1. JSON-Only Output

**Pattern**: Explicitly instruct the LLM to return only valid JSON with no additional text.

**Template Structure**:
```
Generate exactly ONE multiple-choice question in this JSON format:
{
"Question": "question text here",
"Answer": "answer text",
"Options": ["option 1", "option 2", "option 3", "option 4"]
}

Return ONLY the JSON object, no additional text.
```

**Rationale**:
- Simplifies parsing (no need to extract JSON from markdown)
- Reduces errors from extraneous text
- Enables direct `json.loads()` on LLM response

**Examples**:
- `prompts/question_type1.txt:3-8`
- `prompts/question_type2.txt:3-8`
- `prompts/transcript_generation.txt:38-40`

---

### 2. Double-Brace Escaping

**Problem**: Python's `str.format()` interprets `{variable}` as a placeholder.

**Solution**: Use `{{` and `}}` to output literal braces in the final prompt.

**Example**:
```python
# In template file:
{{
"Question": "question text here",
"Answer": "answer text"
}}

# After Python format():
{
"Question": "question text here",
"Answer": "answer text"
}
```

**Source**: `prompts/question_generation.txt:3-5`, `prompts/transcript_generation.txt:39`

---

### 3. Role Assignment

**Pattern**: Begin prompts with explicit role definition.

**Template**:
```
You are a [specific role description].
```

**Examples**:
- "You are a listening-comprehension question generator." (`prompts/question_type1.txt:1`)
- "You are a listening-comprehension script writer." (`prompts/transcript_generation.txt:1`)

**Benefits**:
- Sets clear context for the LLM
- Defines expected expertise and perspective
- Improves response quality and consistency

---

### 4. Structured Output Schema

**Pattern**: Provide explicit JSON schema before generation task.

**Example**:
```
Generate exactly ONE multiple-choice question in this JSON format:
{{
"Question": "question text here",
"Answer": "answer text",
"Options": ["option 1", "option 2", "option 3", "option 4"]
}}
```

**Benefits**:
- Ensures consistent output structure
- Reduces parsing errors
- Makes field names explicit

**Source**: All question_type prompts (`prompts/question_type1.txt:3-8`)

---

## Advanced Patterns

### 5. Level-Tiered Guidelines

**Pattern**: Provide different instructions for different difficulty levels.

**Structure**:
```
**Levels 1-3:** [Guidelines for beginner]
**Levels 4-6:** [Guidelines for intermediate]
**Levels 7-9:** [Guidelines for advanced]
```

**Example** (`prompts/transcript_generation.txt:7-26`):
```
• Levels 1-3
– Vocabulary: high-frequency concrete words
– Grammar: simple SVO clauses, present tense
– Speech: slow, clear, frequent pauses
– Length: 6-10 short sentences

• Levels 4-6
– Vocabulary: common idioms/phrasal verbs
– Grammar: compound sentences, one or two clauses
– Speech: natural but moderate pace
– Length: 11-18 medium sentences

• Levels 7-9
– Vocabulary: abstract, technical, idiomatic
– Grammar: subordinate clauses, passive voice
– Speech: normal or fast native speed
– Length: 19-30 sentences
```

**Benefits**:
- Ensures difficulty consistency
- Provides concrete targets for each level
- Aligns with CEFR framework

---

### 6. Few-Shot Examples

**Pattern**: Provide concrete examples to guide generation.

**Structure**:
```
**Few-shot Example:**
Transcript: "..."
Question: "..."
Options: [...]
Answer: "..."
```

**Example** (`prompts/question_type1.txt:27-30`):
```
**Few-shot Example:**
Transcript: "The weather today is sunny and warm. Many people are walking in the park."
Question: "What is the weather like today?"
Options: ["Sunny and warm", "Cold and rainy", "Cloudy and cool", "Windy and dry"]
Answer: "Sunny and warm"
```

**Benefits**:
- Demonstrates expected output format
- Provides quality benchmark
- Reduces ambiguity

---

### 7. Deduplication via Context

**Pattern**: Pass previously generated content to avoid duplicates.

**Template Variable**: `{previous_questions}`

**Instruction**:
```
**CRITICAL: AVOID DUPLICATION**
You MUST NOT create questions that are similar to these already generated questions:
{previous_questions}

**Requirements for Uniqueness:**
- Ask about DIFFERENT aspects, topics, or details
- Use DIFFERENT question structures and wording
- Ensure your answer is DIFFERENT from previous answers
```

**Source**: `prompts/question_type1.txt:10-19`, `prompts/question_type2.txt:10-19`

**Usage** (in question_generator.py):
```python
previous_questions = "\n".join([
    f"Q: {q['question_text']} | A: {q['correct_answer']}"
    for q in generated_so_far
])

prompt = template.format(
    previous_questions=previous_questions or "None",
    transcript=transcript,
    language=language
)
```

**Benefits**:
- Prevents repetitive questions
- Ensures diverse coverage of content
- Improves test quality

---

## Language-Specific Prompts

### 8. Per-Language Templates

**Storage**: Database table `prompt_templates`

**Schema**:
```sql
CREATE TABLE prompt_templates (
    id UUID PRIMARY KEY,
    task_name TEXT,          -- e.g., 'explorer_ideation'
    language_id INTEGER,     -- 1=Chinese, 2=English, 3=Japanese
    template TEXT,           -- The prompt template
    version INTEGER,
    is_active BOOLEAN
)
```

**Access Pattern** (in database_client.py):
```python
def get_prompt_template(self, task_name: str, language_id: int) -> str:
    """Fetch prompt template for task and language"""
    response = self.supabase.table('prompt_templates') \
        .select('template') \
        .eq('task_name', task_name) \
        .eq('language_id', language_id) \
        .eq('is_active', True) \
        .order('version', desc=True) \
        .limit(1) \
        .execute()

    if response.data:
        return response.data[0]['template']

    # Fallback to English template if language-specific not found
    return self._get_fallback_template(task_name)
```

**Benefits**:
- Language-specific vocabulary guidelines
- Cultural context adjustments
- Native speaker quality expectations

**Example Tasks**:
- `explorer_ideation`: Topic idea generation
- `gatekeeper_check`: Topic quality review
- `transcript_generation`: Audio script writing
- `question_type_1/2/3`: Question generation by type

**Source**: `services/topic_generation/database_client.py:200-230`

---

## Variable Substitution

### 9. Common Variables

**File-Based Prompts** (in `prompts/` folder):

| Variable | Purpose | Example |
|----------|---------|---------|
| `{language}` | Target language | "Chinese", "English", "Japanese" |
| `{difficulty}` | Difficulty level (1-9) | 5 |
| `{topic}` | Content topic | "Daily routines" |
| `{transcript}` | Audio transcript | Full text |
| `{previous_questions}` | Already generated Qs | List of Q&A pairs |
| `{starting_elo}` | Initial ELO rating | 1400 |
| `{question_id1}` | Question UUID | "uuid-here" |
| `{timestamp}` | ISO timestamp | "2024-01-01T00:00:00Z" |
| `{style}` | Narrative style | "conversational", "formal" |

**Database Prompts**:

Variables are template-specific and injected at runtime by agents.

---

## Validation and Error Handling

### 10. Output Validation

**Pattern**: Validate LLM output before using it.

**Example** (in question_generator.py):
```python
try:
    result = json.loads(llm_response)

    # Validate required fields
    if 'Question' not in result:
        raise ValueError("Missing 'Question' field")
    if 'Answer' not in result:
        raise ValueError("Missing 'Answer' field")
    if 'Options' not in result or len(result['Options']) != 4:
        raise ValueError("Invalid 'Options' field")

    # Validate answer is in options
    if result['Answer'] not in result['Options']:
        raise ValueError("Answer not in options")

    return result

except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON from LLM: {e}")
    return None
except ValueError as e:
    logger.error(f"Validation failed: {e}")
    return None
```

---

### 11. Retry Logic

**Pattern**: Retry generation on failure with exponential backoff.

**Implementation** (in TestGenConfig):
```python
@dataclass
class TestGenConfig:
    max_retries: int = 3
    retry_delay: int = 2  # seconds
    retry_backoff: float = 2.0  # exponential multiplier
```

**Usage**:
```python
for attempt in range(config.max_retries):
    try:
        result = generate_question(prompt)
        if validate(result):
            return result
    except Exception as e:
        if attempt < config.max_retries - 1:
            delay = config.retry_delay * (config.retry_backoff ** attempt)
            time.sleep(delay)
        else:
            raise
```

**Source**: `services/test_generation/config.py:60-65`

---

## Best Practices

### DO:
✅ Be explicit about output format (JSON schema)
✅ Use few-shot examples for complex tasks
✅ Provide level-specific guidelines for difficulty tiers
✅ Pass context to avoid duplicates
✅ Validate LLM output before using
✅ Use role assignment to set context
✅ Escape braces in Python format strings (`{{ }}`)

### DON'T:
❌ Rely on markdown code blocks for JSON (ask for raw JSON)
❌ Use vague instructions ("generate a good question")
❌ Forget to validate required fields in output
❌ Trust LLM arithmetic or fact-checking without verification
❌ Mix multiple tasks in one prompt (separate prompts for separate tasks)
❌ Forget fallback handling for missing language-specific templates

---

## Prompt Template Versioning

**Strategy**: Version field in `prompt_templates` table

**Querying**: Always fetch `is_active=True` with `ORDER BY version DESC LIMIT 1`

**Deployment**:
1. Insert new version with higher version number
2. Test new version
3. Set old version `is_active=False` once validated
4. Keep old versions for rollback

**Example**:
```sql
-- Deploy new version
INSERT INTO prompt_templates (task_name, language_id, template, version, is_active)
VALUES ('question_type_1', 2, '...new template...', 2, true);

-- Deactivate old version
UPDATE prompt_templates
SET is_active = false
WHERE task_name = 'question_type_1' AND language_id = 2 AND version = 1;
```

---

## Related Documents

- [Prompt Catalog](./01-prompt-catalog.md)
- [Question Generator Agent](../05-Pipelines/01-test-generation/03-agents/04-question-generator.md)
- [Prose Writer Agent](../05-Pipelines/01-test-generation/03-agents/02-prose-writer.md)
- [Explorer Agent](../05-Pipelines/02-topic-generation/03-agents/01-explorer-agent.md)
- [Topic Generation Database Client](../05-Pipelines/02-topic-generation/05-database-client.md)
