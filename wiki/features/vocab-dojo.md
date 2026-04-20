---
title: Vocab Dojo
type: feature
status: in-progress
tech_page: ./vocab-dojo.tech.md
last_updated: 2026-04-10
open_questions: []
---

# Vocab Dojo

## Purpose

Vocab Dojo is an adaptive exercise serving system that eliminates decision fatigue from vocabulary practice. It automatically selects which words to practice and which exercise type to serve, based on the learner's BKT state, FSRS review schedule, and position on the vocabulary ladder. The goal is to build both passive recognition and active production of vocabulary.

## User Story

A learner navigates to `/vocab-dojo` and hits "Play." The system serves a session of ~20 exercises with zero decision-making required. The session contains a mix of:

- **Due review words** (~40%) — words the learner has seen before and are due for spaced repetition review
- **Active learning words** (~40%) — words in the BKT "uncertainty zone" (p_known 0.40–0.75), where practice has the most impact
- **New/encountered words** (~20%) — recently encountered words with low p_known, getting their first exercises

For each word, the system selects an exercise type that matches the word's current position on the vocabulary ladder. A word at Level 1 gets a listening flashcard; a word at Level 6 gets a semantic discrimination exercise. The learner never chooses — the system handles everything.

If the learner answers incorrectly, they see an explanation of why their answer was wrong and must attempt again until correct. But only the first attempt counts for progression.

## How It Works

1. System pulls the learner's word inventory: FSRS due cards, BKT uncertain-zone words, and newly encountered words.
2. Session is composed in a 40/40/20 split with anti-repetition guards.
3. For each selected word, the system picks an exercise from the word's current ladder level using phase-gated weighted sampling.
4. Exercises are served in shuffled order (not grouped by category).
5. After each exercise, BKT p_known updates, FSRS scheduling adjusts, and the vocabulary ladder position may change.
6. The next session recomputes from fresh state — no pre-materialized queue needed.

## Phase-Gated Exercise Selection

The exercise type served depends on the word's BKT p_known:

| p_known Range | Phase | Dominant Exercise Types |
|---------------|-------|------------------------|
| < 0.40 | A (Recognition) | text_flashcard, listening_flashcard, cloze_completion |
| 0.40–0.65 | A→B | Phase A (30%) + Phase B (70%): jumbled_sentence, translations, spot_incorrect |
| 0.65–0.80 | B→C | Phase B (20%) + Phase C (80%): semantic_discrimination, collocation exercises, odd_one_out |
| 0.80–0.90 | C→D | Phase C (30%) + Phase D (70%): verb_noun_match, context_spectrum, style exercises |
| ≥ 0.90 | D (Production) | Phase D dominant (80%) + sporadic earlier phases (20%) for context variety |

## Anti-Repetition Guards

- **Exercise cooldown:** Same exercise_id not re-served within 7 days per user per sense
- **Type rotation:** Same exercise_type for same sense_id not repeated within 3 days
- **Session cap:** Each exercise type capped at 3 appearances per session
- **Context injection:** For Phase C/D words, 1-in-5 serves uses an exercise from a different topic domain

## Constraints & Edge Cases

- "Mastered" words (p_known > 0.85, FSRS state = review) naturally appear at wide intervals — no explicit sporadic scheduling needed.
- If not enough exercises exist to fill a session, the system backfills with due reviews or reduces session size.
- Session queue is computed live at request time (not pre-materialized) — relies on existing indexed tables.

## Business Rules

- Sessions are free (no token cost for Vocab Dojo exercises).
- Exercise results feed into both BKT and the vocabulary ladder progression engine.
- Exercise history is logged for future analytics and potential ML-based serving optimization.

## Related Pages

- [[features/vocab-dojo.tech]] — Technical specification with SQL
- [[algorithms/vocabulary-ladder]] — 10-level exercise progression
- [[features/exercises]] — Exercise type inventory
- [[features/vocabulary-knowledge]] — BKT model
- [[features/flashcards]] — FSRS scheduling integration
