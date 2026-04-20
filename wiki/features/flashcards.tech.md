---
title: Flashcards — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./flashcards.md
last_updated: 2026-04-10
dependencies:
  - "user_flashcards table"
  - "dim_word_senses table"
  - "services/vocabulary/fsrs.py"
breaking_change_risk: low
---

# Flashcards — Technical Specification

## Database Impact

**Primary table:** `user_flashcards`
- Unique: `(user_id, sense_id)`
- Key columns: `stability`, `difficulty`, `due_date`, `last_review`, `reps`, `lapses`, `state`
- States: `new`, `learning`, `review`, `relearning`

**Indexes:** `idx_uf_user_due` (user_id, language_id, due_date), `idx_uf_user_state`

## API / RPC Surface

### `GET /api/flashcards/due`
- **Purpose:** Fetch cards due for review
- **Auth:** JWT required
- **Query:** `language_id`
- **Returns:** Array of flashcard objects with word sense details

### `POST /api/flashcards/review`
- **Purpose:** Submit review result and reschedule card
- **Auth:** JWT required
- **Body:** `{flashcard_id, rating}` (rating = recall quality)
- **Side effects:** Updates FSRS parameters, recalculates `due_date`

## FSRS Implementation

`services/vocabulary/fsrs.py` implements the FSRS-4 algorithm:
- Calculates new stability based on difficulty, elapsed time, and rating
- Updates difficulty based on response quality
- Computes next review interval from stability

## Related Pages

- [[features/flashcards]] — Prose description
- [[features/vocabulary-knowledge]] — BKT integration
