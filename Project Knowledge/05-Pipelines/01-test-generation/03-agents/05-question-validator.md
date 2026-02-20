# QuestionValidator Agent

**Source:** `services/test_generation/agents/question_validator.py` (~239 lines)

The `QuestionValidator` validates generated questions for structural correctness, content quality, and semantic uniqueness. Unlike other agents, it does not make LLM calls -- all validation is rule-based.

## Class: `QuestionValidator`

### Constructor

```python
def __init__(self):
```

No external dependencies. Initializes an empty `validation_errors` list.

### Method: `validate_question(question, prose, previous_questions) -> Tuple[bool, Optional[str]]`

Validates a single question.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | `Dict` | Question dict with `question`, `choices`, `answer` keys |
| `prose` | `str` | Original prose text (for context validation) |
| `previous_questions` | `List[str]?` | Previously validated question texts |

**Returns:** `(is_valid: bool, error_message: str?)` -- error_message is None when valid.

**Validation Steps:**
1. `_validate_structure(question)` -- checks required fields and types
2. `_validate_content(question)` -- checks content quality
3. `_check_overlap(question_text, previous_questions)` -- checks semantic overlap

### Method: `validate_all_questions(questions, prose) -> Tuple[List[Dict], List[str]]`

Batch validates a list of questions, building up the `previous_questions` list incrementally.

**Returns:** `(valid_questions, error_messages)` -- only valid questions are included in the first list.

### Structural Validation (`_validate_structure`)

| Check | Requirement |
|-------|------------|
| Required fields | `question`, `choices`, `answer` must be present |
| Question text | Must be a string with length >= 5 |
| Choices | Must be a list of exactly 4 items |
| Choice content | Each choice must be a non-empty string |
| Answer | Must be a non-empty string |
| Answer in choices | Stripped answer must match one stripped choice |

### Content Validation (`_validate_content`)

| Check | Severity | Description |
|-------|----------|-------------|
| Question mark | Debug log only | Checks for `?`, `?`, or other question-mark variants |
| Duplicate choices | **Error** | All 4 choices must be unique (case-insensitive) |
| Choice length variety | Debug log only | Flags when all choices have the same length |
| Answer length bias | Debug log only | Flags when the answer is notably the longest option |

### Semantic Overlap Check (`_check_overlap`)

Compares the new question against all previously validated questions using **Jaccard similarity** on word sets:

```
similarity = |intersection(words_new, words_prev)| / |union(words_new, words_prev)|
```

**Threshold:** 0.65 (65% word overlap triggers rejection).

Raises `ValueError` if similarity exceeds the threshold, which causes the question to be rejected.

### Method: `fix_question(question: Dict) -> Dict`

Attempts automatic correction of common issues:
- Normalizes field names (`Question`->`question`, `Options`->`choices`, `Answer`->`answer`).
- Strips whitespace from text fields.
- Converts letter-index answers (`A`, `B`, `C`, `D`) to actual choice text.

Returns the fixed dict (may still be invalid).

---

### Related Documents

- [Pipeline Overview](../01-pipeline-overview.md)
- [Orchestrator](../02-orchestrator.md)
- [QuestionGenerator](./04-question-generator.md)
