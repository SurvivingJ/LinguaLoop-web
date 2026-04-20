---
title: Vocabulary Ladder
type: algorithm
status: in-progress
tech_page: ./vocabulary-ladder.tech.md
last_updated: 2026-04-10
open_questions: []
---

# Vocabulary Ladder

## Purpose

The Vocabulary Ladder is a 10-level deterministic exercise system that transitions a learner from zero knowledge of a target word to confident, native-like production. It is grounded in Paul Nation's nine-component model of word knowledge, which distinguishes receptive from productive mastery across form, meaning, and use. The core empirical finding driving the design: recognition (receptive) knowledge is acquired before recall (productive) knowledge across all components without exception.

## User Story

When a learner encounters a new word — through a Language Pack, comprehension test, or Vocab Dojo — the system generates a fixed asset pack of exercises for that word. The learner then progresses through increasingly demanding exercise types. Early levels test whether they can recognize the word; middle levels test whether they understand its grammar, collocations, and semantics; upper levels test whether they can use it correctly in context.

The system does not allow the learner to skip levels. If they fail an exercise in a session, they must continue attempting it until they get it right. But only first-attempt correctness counts toward promotion up the ladder — eventual success through retries does not inflate progression.

## How It Works

### The Ten Levels

| Level | Name | What It Tests |
|-------|------|---------------|
| 1 | Listening Flashcard | Can the learner distinguish the word's sound/shape from near-neighbors? |
| 2 | Text Flashcard | Can the learner match the word to its definition? |
| 3 | Cloze Completion | Can the learner place the word correctly in a sentence? |
| 4 | Grammar Slot | Can the learner choose the correct inflected form (morphology) or grammatical element (particles/measure words)? |
| 5 | Collocation Gap Fill | Can the learner recognize the word's natural collocate? (Skipped for concrete nouns) |
| 6 | Semantic Discrimination | Can the learner detect when the word is used in the wrong semantic context? |
| 7 | Spot Incorrect Sentence | Can the learner identify a structural/syntactic error involving the word? |
| 8 | Collocation Repair | Can the learner fix an unnatural collocation? (Skipped for concrete nouns) |
| 9 | Jumbled Sentence | Can the learner assemble the word into a correctly ordered sentence? (No LLM — uses frontend tokenization) |
| 10 | Capstone Production | Can the learner translate a passage containing the word? (Free-text, LLM-graded at runtime) |

Each level tests a **single failure mode**. Level 3 distractors fail contextually; Level 4 distractors fail grammatically; Levels 5/8 fail collocationally; Level 6 fails semantically; Level 7 fails structurally. This separation ensures exercises measure the intended skill, not test-taking instinct.

### Language-Specific Routing

The ladder adapts based on the target language's typological features:

- **English:** Level 4 = morphological inflection (verb conjugation, noun plurals, comparatives)
- **Mandarin Chinese:** Level 4 = measure words (量词) for nouns, aspectual particles (了/过/着) for verbs. Morphology module skipped because Chinese is isolating.
- **Japanese:** Level 4 = both morphology (agglutinative verb/adjective conjugation) AND particles/counters. Dual grammar burden.

### POS Routing

- **Concrete nouns:** Skip Levels 5 and 8 (no strong collocational dependency). Minimum 8 levels.
- **Abstract nouns, verbs, adjectives:** Full 10-level ladder. Collocation exercises are critical for these word types.

### Promotion & Demotion

**Promotion:** A word advances to the next level when the learner achieves first-try success in 2 separate spaced-repetition sessions. Two sessions proves stabilization, not luck.

**Demotion:** A word drops one level when the learner misses the first attempt in 2 consecutive sessions. If the capstone is failed, the word returns to the highest previously stable receptive level.

**In-session behavior:** If the learner answers incorrectly, they see the pedagogical reasoning for why their answer was wrong, then must continue attempting until correct. This forces engagement with the explanation. But eventual success does not count for promotion.

### Word States

Each word lives in one of these states:

| State | Meaning |
|-------|---------|
| `new` | Not yet encountered |
| `learning` | Currently progressing through levels 1–4 |
| `fragile_receptive` | Levels 5–7, not yet stable |
| `stable_receptive` | Consistently correct at receptive levels |
| `fragile_productive` | Levels 8–9, not yet stable |
| `stable_productive` | Passed capstone, productively acquired |

### Generate-Once, Use-Forever

All exercise assets are generated once per word and cached permanently. This is critical for both cost and assessment validity — a learner who encounters the same exercise twice is being tested on the same item, making performance trajectory meaningful. Regenerating exercises would destroy the spaced-repetition signal.

## Constraints & Edge Cases

- The 6 Age Tiers (not CEFR) control the vocabulary and grammar complexity of generated sentences.
- Per-option pedagogical reasoning is generated and cached alongside each exercise, enabling instant feedback without runtime LLM calls.
- A word's active levels are determined at registration time and stored in the database. The ladder is deterministic for a given (word, POS, semantic_class, language) tuple.
- Level 2 uses database definitions (not LLM) — distractor definitions are randomly sampled from other words in the same tier.
- Level 9 uses backend tokenization (e.g., jieba for Chinese) — no LLM generation needed.

## Related Pages

- [[algorithms/vocabulary-ladder.tech]] — Full technical specification
- [[features/exercises]] — Exercise type inventory
- [[features/vocab-dojo]] — Adaptive exercise serving
- [[features/language-packs]] — Pack context for word introduction
- [[features/vocabulary-knowledge]] — BKT integration
- [[decisions/ADR-003-age-tiers]] — Age Tier difficulty system
