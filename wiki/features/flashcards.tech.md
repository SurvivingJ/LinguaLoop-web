---
title: Flashcards — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./flashcards.md
last_updated: 2026-11-23
dependencies:
  - "user_flashcards table"
  - "dim_word_senses table"
  - "services/vocabulary/fsrs.py"
  - "services/day_boundary.py (REVIEW_TIMEZONE, review_today; TASK-1211)"
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

Routes are in `routes/flashcards.py` (blueprint `/api/flashcards`). The learner-facing page is `/flashcards`, rendered from the page table in `web/pages.py`.

### `GET /api/flashcards/due`
- **Purpose:** Fetch cards due for review
- **Auth:** JWT required
- **Query:** `language_id`
- **Returns:** Array of flashcard objects with word sense details

### `POST /api/flashcards/review`
- **Purpose:** Submit review result and reschedule card
- **Auth:** JWT required
- **Body:** `{card_id, rating}`; `rating` is 1 again, 2 hard, 3 good, 4 easy. Optional `active_ms` and `client_event_id` credit the study-time ledger (see [[features/weekly-minutes.tech]]).
- **Side effects:** Updates FSRS parameters, recalculates `due_date`

### Other endpoints
- `GET /api/flashcards/stats?language_id=` — per-user flashcard statistics.
- `POST /api/flashcards/skip` — delete/archive a card the learner does not want.
- `GET /api/flashcards/page` — renders `flashcards.html` (a JWT-protected template route under the API prefix; not the learner-facing URL).

## Session player link (fixed 2026-11-23)

When the daily-session flashcards player cannot load cards (`renderUnavailable` in `static/js/session/players/flashcards.js`), it offers an "Open page" button. It used to link to `/flashcards/page`, which is not a page route (the template route is `/api/flashcards/page`), so the learner landed on the login page. It now links to `/flashcards`, the real page.

## Review day (TASK-1211)

All FSRS dates use one app-wide review calendar that rolls over at midnight AEST (`Australia/Brisbane`, no daylight saving). `GET /due` filters `due_date.lte.<review_today_iso()>`, `GET /stats` counts `due_date <= review_today_iso()`, and `POST /review` computes `today = review_today()` once and passes it to `schedule_review(card, rating, today)` and to `last_review`. Configured in `services/day_boundary.py` `REVIEW_TIMEZONE` (Python) and `public.review_today()` (SQL, `migrations/fsrs_review_day_aest.sql`, pending apply; PENDING-2026-11-23 group 10). Full reader/writer list, deployment order and the effect on existing cards: [[features/practice-engine.tech]] ("FSRS review day"). Tests: `tests/test_review_day_boundary.py`.

## FSRS Implementation

`services/vocabulary/fsrs.py` implements the FSRS-4 algorithm:
- Calculates new stability based on difficulty, elapsed time, and rating
- Updates difficulty based on response quality
- Computes next review interval from stability

## Related Pages

- [[features/flashcards]] — Prose description
- [[features/vocabulary-knowledge]] — BKT integration
