---
title: Exercises
type: feature
status: in-progress
tech_page: ./exercises.tech.md
last_updated: 2026-04-10
open_questions: []
---

# Exercises

## Purpose

Exercises are targeted practice items that drill specific vocabulary, grammar, or collocations. They bridge the gap between passive comprehension (tests) and active production, helping learners internalize language patterns through a structured 10-level progression from recognition to production.

## User Story

A learner encounters exercises in two contexts:

1. **Vocab Dojo** — An adaptive session of ~20 exercises automatically selected based on the learner's BKT state, FSRS schedule, and vocabulary ladder position. Zero decision-making required.

2. **Language Packs** — Exercises tied to pack vocabulary, served as part of the pack study cycle between word introduction and conversation comprehension.

If the learner answers incorrectly, they see pedagogical reasoning explaining why their choice was wrong, then must attempt again until correct. Only first-attempt correctness counts for vocabulary ladder progression.

## Exercise Types (21 Types, 4 Phases)

The exercise system has 21 distinct exercise types organized into four cognitive phases:

| Phase | Types | Cognitive Demand | Best For |
|-------|-------|-----------------|----------|
| **A** (Recognition) | `text_flashcard`, `listening_flashcard`, `cloze_completion` | Recognition | New/encountered words (p_known < 0.40) |
| **B** (Recall) | `jumbled_sentence`, `tl_nl_translation`, `nl_tl_translation`, `spot_incorrect_sentence`, `spot_incorrect_part`, `style_register_fill`, `style_formality_fill` | Recall + ordering | Learning words (p_known 0.40–0.65) |
| **C** (Nuanced Recall) | `semantic_discrimination`, `collocation_gap_fill`, `collocation_repair`, `odd_one_out`, `odd_collocation_out`, `style_pattern_match`, `style_voice_transform` | Nuanced recall | Consolidating words (p_known 0.65–0.80) |
| **D** (Production) | `verb_noun_match`, `context_spectrum`, `timed_speed_round`, `style_imitation` | Fluent production | Near-mastery words (p_known > 0.80) |

## Difficulty System: Age Tiers

LinguaLoop uses **Age Tiers** for exercise and content difficulty (see [[decisions/ADR-003-age-tiers]]). Age tiers produce more natural LLM-generated content than abstract proficiency labels.

| Tier | Name | Vocab Size | LLM Instruction Gist |
|------|------|------------|----------------------|
| 1 | The Toddler (Age 4–5) | ~500 words | Basic verbs and concrete nouns only. One idea per sentence. |
| 2 | The Primary Schooler (Age 8–9) | ~2,000 words | Compound sentences. Literal, concrete topics. No idioms. |
| 3 | The Young Teen (Age 13–14) | ~5,000 words | Common colloquialisms. Conditional sentences. Natural everyday conversation. |
| 4 | The High Schooler (Age 16–17) | ~10,000 words | Standard adult structures. Moderate domain jargon. Fluent everyday language. |
| 5 | The Uni Student (Age 19–21) | ~15,000+ words | Full standard language. Complex clauses. Cultural idioms. Rich description. |
| 6 | The Educated Professional (Age 30+) | ~25,000+ words | High-register vocabulary. Domain-specific jargon. Advanced rhetoric. |

## Exercise Generation

Exercises are generated using a **3-prompt LLM pipeline** (see [[algorithms/vocabulary-ladder.tech]]):

1. **Prompt 1** (Gemini Flash Lite): Generates definition, primary collocate, and 6 correct sentences
2. **Prompt 2** (Claude Sonnet): Generates lexical/semantic exercises (Levels 1, 3, 5, 6) with per-option pedagogical reasoning
3. **Prompt 3** (Claude Sonnet): Generates grammar/structural exercises (Levels 4, 7, 8) with reasoning

Level 2 (definition match) uses database lookups. Level 9 (jumbled sentence) uses backend tokenization. Level 10 (capstone) uses runtime LLM grading.

All generated assets include TL reasoning for every option (correct and incorrect), enabling instant feedback without runtime LLM calls.

## Exercise Sources

- **Grammar** (`source_type = 'grammar'`) — exercises targeting a specific `dim_grammar_patterns` entry
- **Vocabulary** (`source_type = 'vocabulary'`) — exercises targeting a specific `dim_word_senses` entry
- **Collocation** (`source_type = 'collocation'`) — exercises targeting a specific `corpus_collocations` entry
- **Study Pack** (`source_type = 'study_pack'`) — exercises targeting a `study_pack_items` entry

## Constraints & Edge Cases

- The `chk_source_fk` constraint ensures exactly one source FK is non-null per exercise.
- Exercises track IRT difficulty (`irt_difficulty`, `irt_discrimination`) for future adaptive serving.
- Deactivated exercises (`is_active = false`) are excluded from serving.
- Distractor tags on wrong answers enable error-pattern analytics.
- Per-option reasoning is cached with the exercise — no runtime LLM calls for feedback.

## Business Rules

- Exercises are generated in batches at content creation time (test generation, pack generation, vocabulary ladder pipeline).
- Exercise generation is language-aware — different LLM models per language, with language-spec routing for grammar exercises.
- Each exercise type has its own generator class in `services/exercise_generation/generators/`.
- Generate-once, use-forever: exercises are immutable after validation. Regeneration only via QA repair workflow.

## Related Pages

- [[features/exercises.tech]] — Technical specification
- [[algorithms/vocabulary-ladder]] — 10-level progression system
- [[features/language-packs]] — Exercises within packs
- [[features/vocab-dojo]] — Adaptive exercise serving
- [[features/vocabulary-knowledge]] — BKT updates from exercise results
- [[decisions/ADR-003-age-tiers]] — Age Tier difficulty system
- [[database/schema.tech]] — `exercises`, `exercise_attempts` tables
