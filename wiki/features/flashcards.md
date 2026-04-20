---
title: Flashcards (FSRS)
type: feature
status: in-progress
tech_page: ./flashcards.tech.md
last_updated: 2026-04-10
open_questions: []
---

# Flashcards (FSRS)

## Purpose

Flashcards provide spaced-repetition review for vocabulary that the learner has encountered through tests and exercises. The scheduling uses the FSRS (Free Spaced Repetition Scheduler) algorithm to optimize review timing.

## User Story

A learner navigates to `/flashcards`. The system shows cards due for review today — each card presents a word in the target language and asks the learner to recall its meaning. After revealing the answer, the learner rates their recall quality. The system reschedules the card accordingly: well-remembered cards come back later; forgotten cards come back sooner.

## How It Works

1. When a learner encounters new words through tests or exercises, flashcard entries are created automatically.
2. Each card tracks FSRS parameters: stability, difficulty, due date, reps, lapses, state.
3. Cards cycle through states: `new` → `learning` → `review` → `relearning` (on lapse).
4. The `/flashcards` page shows cards where `due_date ≤ today`.
5. After review, FSRS recalculates the next due date based on recall quality.

## Constraints & Edge Cases

- One flashcard per user per word sense (unique constraint).
- Cards include example sentences and audio URLs when available.
- A card that lapses too many times may need manual attention.

## Business Rules

- Flashcard creation is automatic upon vocabulary encounter — no manual card creation by users.
- Review sessions show all due cards for the selected language.

## Related Pages

- [[features/flashcards.tech]] — Technical specification
- [[features/vocabulary-knowledge]] — BKT state informs flashcard priority
- [[database/schema.tech]] — `user_flashcards` table
