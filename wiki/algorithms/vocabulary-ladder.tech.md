---
title: Vocabulary Ladder — Technical Specification
type: algorithm-tech
status: in-progress
prose_page: ./vocabulary-ladder.md
last_updated: 2026-04-10
dependencies:
  - "services/vocabulary_ladder/"
  - "services/exercise_generation/"
  - "exercises table"
  - "user_vocabulary_knowledge table"
  - "user_flashcards table"
  - "dim_word_senses table"
breaking_change_risk: medium
---

# Vocabulary Ladder — Technical Specification

## Architecture Overview

The vocabulary ladder is implemented as a 3-prompt LLM generation pipeline that produces immutable exercise assets, plus a runtime progression engine that manages word states and level movement.

```
Generation (background, per word):
  Word Intake → POS/semantic class routing → Language Spec lookup
    → Prompt 1 (Gemini Flash Lite): ground truth assets
    → Prompt 2 (Claude Sonnet): lexical/semantic exercises
    → Prompt 3 (Claude Sonnet): grammar/structural exercises
    → Schema validation → Linguistic validation → Pedagogical validation
    → Immutable storage in exercises table

Runtime (per session):
  Session Builder → selects words by FSRS due date + BKT state
    → Exercise Delivery → assembles UI-ready cards from stored assets
    → User Response → first-attempt tracking + retry loop
    → Progression Engine → promote/demote based on inter-session performance
    → BKT Update + FSRS Scheduling
```

## 3-Prompt Generation Pipeline

### Prompt 1: Ground Truth Generator (Gemini 2.5 Flash Lite)

Generates the base linguistic assets: definition, primary collocate, and 6 correct example sentences with exact target substrings.

**Input:** target_word, POS, tier_description, corpus_sentences (if any), number_needed (6 - len(corpus_sentences))

**Output Schema (numeric keys only):**
```json
{
  "1": "tier-appropriate TL definition",
  "2": "primary TL collocate (or null)",
  "3": [
    { "1": "full sentence", "2": "exact target substring" },
    ...  // exactly 6 items
  ]
}
```

**Sentence allocation:** Sentences 1–3 feed Prompt 2 (Levels 3, 5, 6). Sentences 4–6 feed Prompt 3 (Levels 4, 7, 8). Sentence 6 also feeds Level 9 (jumbled sentence via backend tokenization).

### Prompt 2: Lexical & Semantic Exercises (Claude Sonnet 4.6)

Generates Levels 1, 3, 5 (if active), and 6. The backend dynamically assembles the prompt, omitting instructions for skipped levels.

**Distractor design per level:**
- Level 1: Phonetic/orthographic similarity, zero semantic overlap
- Level 3: Same POS, grammatically valid in blank, contextually nonsensical
- Level 5: Semantically close to correct collocate but statistically unnatural pairing
- Level 6: Grammatically correct sentences but semantically/pragmatically misusing the word

**Output Schema:**
```json
{
  "1": [ { "1": "text", "2": true/false, "3": "TL reasoning" }, ... ],
  "3": [ { "1": "text", "2": true/false, "3": "TL reasoning" }, ... ],
  "5": [ { "1": "text", "2": true/false, "3": "TL reasoning" }, ... ],
  "6": [ { "1": "sentence", "2": true/false, "3": "TL reasoning" }, ... ]
}
```

### Prompt 3: Grammar & Structural Exercises (Claude Sonnet 4.6)

Generates Levels 4, 7, and 8 (if active).

**Distractor design per level:**
- Level 4: Real morphological siblings (or valid particles/measure words), wrong for this context
- Level 7: One sentence with common L2 structural error; three correct sentences
- Level 8: Unnatural collocates that L2 learners frequently substitute via L1 transfer

**Output Schema:**
```json
{
  "4": [ { "1": "text", "2": true/false, "3": "TL reasoning" }, ... ],
  "7": { "1": "error sentence", "2": "corrected sentence", "3": "TL reasoning" },
  "8": [ { "1": "text", "2": true/false, "3": "TL reasoning" }, ... ]
}
```

## Language Specification Files

```json
{
  "EN": {
    "has_morphology": true,
    "morphology_types": ["verb_conjugation", "noun_plural", "comparative_adjective"],
    "has_particles": false,
    "has_measure_words": false,
    "level_4_module": "morphology"
  },
  "ZH": {
    "has_morphology": false,
    "has_particles": true,
    "particle_types": { "aspectual": ["了", "过", "着"], "structural": ["的", "得", "地"] },
    "has_measure_words": true,
    "level_4_module": "particles_or_measure_words"
  },
  "JA": {
    "has_morphology": true,
    "morphology_types": ["verb_conjugation_agglutinative", "adjective_conjugation"],
    "has_particles": true,
    "particle_types": { "case_markers": ["は", "が", "を", "に", "で", "へ", "と", "から", "まで"] },
    "has_measure_words": true,
    "level_4_module": "morphology_and_particles_or_counters"
  }
}
```

## POS Routing Logic

```python
def build_exercise_ladder(word, pos, semantic_class, lang):
    spec = load_language_spec(lang)
    ladder = [1, 2, 3]  # Always levels 1-3

    # Level 4: Language-specific grammar
    if spec["has_morphology"] and pos in ["verb", "adjective"]:
        ladder.append({"level": 4, "submodule": "morphology"})
    if spec["has_morphology"] and pos == "noun":
        ladder.append({"level": 4, "submodule": "morphology_plural"})
    if spec["has_measure_words"] and semantic_class == "concrete_noun":
        ladder.append({"level": 4, "submodule": "measure_word"})
    if spec["has_particles"] and pos == "verb":
        ladder.append({"level": 4, "submodule": "particle_aspectual"})

    # Levels 5, 8: Collocations (skip for concrete nouns)
    if semantic_class != "concrete_noun":
        ladder.extend([5, 8])

    # Levels 6, 7, 9, 10: Universal
    ladder.extend([6, 7, 9, 10])
    return sorted(set(ladder))
```

## Progression Engine

### Database: Word Progress Record

```sql
CREATE TABLE user_word_progress (
    user_id       uuid REFERENCES users(id),
    sense_id      integer REFERENCES dim_word_senses(id),
    current_level integer NOT NULL DEFAULT 1,
    word_state    text NOT NULL DEFAULT 'new',  -- new/learning/fragile_receptive/stable_receptive/fragile_productive/stable_productive
    first_try_success_count integer DEFAULT 0,  -- resets on level change
    first_try_failure_count integer DEFAULT 0,  -- resets on level change
    total_attempts integer DEFAULT 0,
    last_attempt_at timestamptz,
    review_due_at  timestamptz,
    PRIMARY KEY (user_id, sense_id)
);
```

### Promotion/Demotion Rules

```python
def process_attempt(user_id, sense_id, is_correct, is_first_attempt):
    progress = get_progress(user_id, sense_id)

    if not is_first_attempt:
        return  # Only first attempts affect ladder movement

    if is_correct:
        progress.first_try_success_count += 1
        progress.first_try_failure_count = 0
        if progress.first_try_success_count >= 2:
            promote(progress)
    else:
        progress.first_try_failure_count += 1
        progress.first_try_success_count = 0
        if progress.first_try_failure_count >= 2:
            demote(progress)

def promote(progress):
    next_level = get_next_active_level(progress)
    progress.current_level = next_level
    progress.first_try_success_count = 0
    progress.word_state = compute_state(next_level)

def demote(progress):
    if progress.current_level == 10:
        # Return to highest stable receptive level
        progress.current_level = get_highest_stable_level(progress)
    else:
        prev_level = get_prev_active_level(progress)
        progress.current_level = prev_level
    progress.first_try_failure_count = 0
    progress.word_state = compute_state(progress.current_level)
```

## Validation Pipeline

Before any exercise is committed to the database:

1. **Schema validation:** JSON has required numeric keys, 4 options per MCQ, exactly 1 correct
2. **Linguistic validation:** Target substrings appear exactly in sentences, morphology distractors are real forms, collocate fields null only when appropriate
3. **Pedagogical validation:** Distractors obey the intended error axis for each level
4. **Content quality:** No duplicate sentence shapes, no repeated semantic contexts, no tautological explanations

**Human review triggers:** Ambiguity detected, <3 corpus attestations, proper nouns, duplicate sentence templates, weak explanations, malformed JSON.

## Cost Estimates (per word, all 3 prompts)

| Model Combination | Est. Cost per Word | Cost for 10,000 Words |
|-------------------|-------------------|-----------------------|
| Flash Lite + Sonnet 4.6 | ~$0.014 | ~$139 |
| DeepSeek V3 (all prompts) | ~$0.001 | ~$14 |
| Qwen 72B + Qwen3-Max | ~$0.006 | ~$57 |

## Related Pages

- [[algorithms/vocabulary-ladder]] — Prose description
- [[features/exercises.tech]] — Exercise table schema
- [[features/vocab-dojo.tech]] — Exercise serving algorithm
- [[database/schema.tech]] — Full schema
