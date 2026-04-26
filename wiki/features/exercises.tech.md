---
title: Exercises — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./exercises.md
last_updated: 2026-04-25
dependencies:
  - "exercises table"
  - "exercise_attempts table"
  - "user_exercise_history table (new)"
  - "dim_grammar_patterns table"
  - "dim_word_senses table"
  - "corpus_collocations table"
  - "services/exercise_generation/"
  - "services/exercise_session_service.py"
  - "services/vocabulary_ladder/"
breaking_change_risk: medium
---

# Exercises — Technical Specification

## Architecture Overview

```
Generation (batch, admin-triggered or pack pipeline):
  ExerciseOrchestrator
    → BaseGenerator subclass per type
    → LLM client (OpenRouter, language-specific model)
    → Validator (schema + linguistic + pedagogical)
    → exercises table (immutable after validation)

Full Pipeline (admin dashboard, single-button end-to-end):
  POST /api/run/full-pipeline → _do_full_pipeline()
    → Step 1: VocabBackfillRunner (vocab + senses + token maps)
    → Step 2: TokenMapBackfillRunner (straggler token maps)
    → Step 3: run_backfill (per-question sense_ids)
    → Step 4: BackfillRunner (test skill ratings)
    → Step 5: ExerciseBackfillRunner (vocab + grammar + style)
    → Step 6: run_collocation_batch (collocations, with idempotency)
  All steps idempotent, stoppable between steps via is_task_stopped()

Vocabulary Ladder Generation (per word):
  Word Intake → POS routing → Language Spec
    → Prompt 1 (Gemini Flash Lite): ground truth
    → Prompt 2 (Claude Sonnet): lexical exercises
    → Prompt 3 (Claude Sonnet): grammar exercises
    → Validation pipeline → exercises table

Serving (user-facing, via Vocab Dojo or Pack Study):
  get_exercise_session RPC → phase-gated selection
    → anti-repetition filtering → session queue
  /api/exercises/submit → exercise_attempts + BKT + FSRS + ladder update
```

## Database Impact

**Tables read:** `exercises`, `dim_grammar_patterns`, `dim_word_senses`, `user_vocabulary_knowledge`, `user_flashcards`, `user_exercise_history`
**Tables written:** `exercises` (generation), `exercise_attempts` (submission), `user_exercise_history` (scheduling)

## API / RPC Surface

### `GET /api/exercises/session`
- **Purpose:** Serve a batch of exercises for the current user + language
- **Auth:** JWT required
- **Returns:** Array of exercise objects with content JSONB, phase, slot_reason

### `POST /api/exercises/submit`
- **Purpose:** Record user's answer to an exercise
- **Auth:** JWT required
- **Body:** `{exercise_id, user_response: {...}, is_correct, is_first_attempt}`
- **Side effects:** Creates `exercise_attempts` row; inserts `user_exercise_history` row; updates BKT; updates FSRS; updates vocabulary ladder position

### `RPC: get_exercise_session(user_id, language_id, session_size)`
- **Purpose:** Compute an optimal exercise session from SQL
- **Returns:** exercise_id, exercise_type, sense_id, content, p_known, phase, slot_reason
- **Performance:** <50ms with proper indexes

## Exercise Content Schema (JSONB)

Vocabulary ladder exercises use numeric-key JSON for language safety:

```json
{
  "1": [
    { "1": "option text", "2": true, "3": "TL pedagogical reasoning" },
    { "1": "option text", "2": false, "3": "TL reasoning why wrong" },
    ...
  ]
}
```

Legacy exercises use the original schema:
```json
{
  "prompt": "...",
  "correct_answer": "...",
  "distractors": [
    {"text": "...", "tag": "tense_error"},
    ...
  ],
  "explanation": "...",
  "context_sentence": "..."
}
```

## Generator Architecture

```
services/exercise_generation/
├── orchestrator.py          # Coordinates generation batches
├── base_generator.py        # Abstract base with shared LLM/validation logic
├── language_processor.py    # Language-specific text processing
├── difficulty.py            # Difficulty calibration
├── llm_client.py            # OpenRouter wrapper
├── validators.py            # Output validation
├── config.py                # Generation settings, phase maps, distributions
└── generators/
    ├── cloze.py
    ├── translation.py
    ├── jumbled_sentence.py
    ├── verb_noun_match.py
    ├── collocation.py
    ├── semantic.py
    ├── style.py
    ├── context_spectrum.py
    ├── timed_speed_round.py
    ├── spot_incorrect.py
    ├── style.py
    └── flashcard.py

scripts/                             # Backfill scripts (used by Full Pipeline)
├── backfill_vocab.py                # VocabBackfillRunner: vocab + senses + token maps
├── backfill_token_maps.py           # TokenMapBackfillRunner: straggler token maps
├── backfill_question_sense_ids.py   # Per-question sense_ids matching
├── backfill_test_skill_ratings.py   # Test skill ratings with ELO
└── backfill_exercises.py            # ExerciseBackfillRunner: vocab + grammar + style

services/vocabulary_ladder/
├── scheduler.py             # ExerciseScheduler (session building)
├── progression.py           # Promotion/demotion engine
├── word_intake.py           # Word registration and routing
├── asset_generator.py       # 3-prompt pipeline orchestrator
├── validators.py            # Exercise-specific validation
└── language_specs/
    ├── en.json
    ├── zh.json
    └── ja.json
```

## Key Architectural Decisions

1. **Exercise content as JSONB**
   - Rationale: Different exercise types have radically different content shapes. JSONB avoids column explosion.

2. **Exactly-one-source constraint**
   - Rationale: Every exercise must trace to a specific language element for analytics and adaptive serving.

3. **Numeric-only JSON keys for vocabulary ladder**
   - Rationale: Prevents LLM from hallucinating translated key names in non-English languages.

4. **3-prompt pipeline split (Flash + Sonnet)**
   - Rationale: Sentence generation (Prompt 1) is a compliance task suitable for cheap models. Distractor design (Prompts 2-3) requires pedagogical reasoning suitable for expensive models.

5. **Generate-once, cache-forever**
   - Rationale: Assessment validity requires stable items. LLM output variance (even at temperature=0) makes regeneration unreliable. Spaced repetition signals require item stability.

6. **Full Pipeline as unified backfill orchestrator**
   - Rationale: Running 5+ backfill scripts manually in the correct order is error-prone. A single admin button runs them sequentially with per-step try/except so one failure doesn't block subsequent steps.
   - File: `routes/admin_local.py` — `_do_full_pipeline()` function

## Related Pages

- [[features/exercises]] — Prose description
- [[algorithms/vocabulary-ladder.tech]] — Full ladder specification
- [[features/vocab-dojo.tech]] — Exercise serving algorithm
- [[features/language-packs.tech]] — Pack-specific exercise generation
- [[database/schema.tech]] — `exercises`, `exercise_attempts` DDL
