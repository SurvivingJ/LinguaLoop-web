---
title: Practice Extra Rounds — Technical Specification
type: feature-tech
status: in-progress
prose_page: practice-extra-rounds.md
last_updated: 2026-10-18
dependencies:
  - "get_practice_session (RPC)"
  - "get_review_ahead_items (RPC, new)"
  - "PracticeSessionService.new_word_state / _nominate_new_words / _insert_ladder_rows"
  - "static/js/session/controller.js, tail.js, players/practice.js"
breaking_change_risk: low
---

# Practice Extra Rounds — Technical Specification

## Architecture Overview
```
Practice mode summary → "Keep practising" panel (controller.js)
  Start → queue item {kind:'practice', id:'extra_k', is_extra, is_tail, extra:{reviews,newWords,exclude}}
        → players/practice.js → GET /api/practice/extra
        → PracticeSessionService.get_extra_round
             new words: _admit_extra_new_words → get_practice_session(acquisition), filtered to targets
             reviews:   get_practice_session(maintenance) due items → get_review_ahead_items top-up
        → attempts: POST /api/practice/attempt {session_mode: item.mode, is_tail: true}
  round end → showSummary → panel again (last choice pre-selected)
```

## Database Impact
- New RPC `get_review_ahead_items` (`migrations/practice_review_ahead.sql`), service_role only.
  Pool: `user_flashcards` rows for the language with `reps > 0`, excluding senses attempted in
  the last `p_exclude_recent_minutes` and `p_exclude_sense_ids`. Order: `bkt_effective_p_known`
  ascending, then `due_date` ascending. One active exercise per sense, least recently attempted
  first. Reads `exercise_attempts`, `user_flashcards`, `user_vocabulary_knowledge`, `exercises`,
  `dim_exercise_types`.
- Extra new words insert `user_word_ladder` rows (same shape as daily intake).
  `set_new_words_shortfall` is NOT written.
- No new columns. Early reviews only move due dates forward and do not add to the governor's
  backlog, so the planned `is_extra` attempt column was dropped.

## API / RPC Surface
### `GET /api/practice/extra?language_id&reviews=0|1&new_words=0..10&exclude=1,2`
- **Purpose:** one extra round.
- **Arguments:** `reviews` truthy flag; `new_words` 0..`EXTRA_NEW_WORDS_MAX` (10); `exclude`
  comma-separated sense ids (non-digits ignored, max 200). Needs `reviews=1` or `new_words>0`.
- **Returns:** `{items, tail: true, extra: {requested_new_words, new_words_served,
  new_words_admitted, new_words_beyond_quota, reviews_served}, no_content_reason}`.
  Items have the `/api/practice/session` shape, each with its own `mode`.
- **Errors:** 400 on a missing language, `new_words` out of range or an empty choice; 500 on failure.
- **Auth:** `supabase_jwt_required`.
- **Side effects:** may admit up to `new_words` ladder rows past the daily quota.

### `GET /api/study-session?...&scope=practice`
Same as before, except `scope=practice` makes the tail gate (`_is_main_complete`) ignore
`kind:'test'` items. The queue, `progress` and `next_index` are unchanged.

### `get_review_ahead_items(p_user_id uuid, p_language_id smallint, p_limit int=10, p_exclude_recent_minutes int=10, p_exclude_sense_ids int[]='{}') → jsonb`
Array of items `{exercise_id, sense_id, exercise_type, family, content, ladder_level, p_known,
expected_seconds, mode:'maintenance', review_ahead:true}`. `p_limit` is clamped to 0..50.

## Service
`PracticeSessionService.get_extra_round(user_id, language_id, reviews, new_words, exclude_sense_ids)`
- New words: `targets = (unstarted_sense_ids + admitted)[:n]`, admitting `n - len(unstarted)`
  through `_nominate_new_words` (same supply gate). `new_words_beyond_quota =
  max(0, len(targets) - max(0, E - started_today))`. Items come from
  `get_practice_session(acquisition, minutes = n × minutes_per_new_word)`, filtered to targets
  and ordered by target order.
- Reviews: due Maintenance items (fall-through acquisition items dropped, one per sense, most
  overdue first) up to `EXTRA_REVIEW_ITEMS` (10), topped up by `get_review_ahead_items`.
- Both: `_interleave_extras(reviews, new_word_items)`.
- Then script variant, jumbled prep, and `score_breakdown` removed.

## Component Specification
- `tail.js`: `EXTRA_NEW_WORDS_MAX`, `normalizeExtraChoice`, `isRunnableExtraChoice`,
  `extraRequestUrl`, `extraBeyondQuota`, `makeExtraItem`.
- `controller.js`: `studySessionUrl()` adds `scope=practice` in Practice mode;
  `renderExtraPanel` / `startExtraRound`; `persistCompletion` skips `is_extra` items (no
  complete-block; their attempts already credit weekly counters as tail work); in Practice mode
  `showEmpty` goes to the summary card so the panel can show.
- `players/practice.js`: for `is_extra` items, fetch `/api/practice/extra`, credit each attempt
  with the item's own `mode`, and store `served_sense_ids` on the queue item for the next
  round's `exclude`.
- `templates/study_session.html`: `#sessionExtraPanel`. i18n keys `session.extra.*` (en, zh, ja, es).

## Key Architectural Decisions
See [[decisions/ADR-036-open-ended-practice-beyond-budget]].

## Security Considerations
JWT auth required; `new_words` bounded per request; `exclude` parsed as digits only and capped;
the RPC is service_role only with a fixed `search_path`.

## Testing Strategy
- `tests/test_practice_extra_rounds.py`: route validation and forwarding; admission past the
  quota, unstarted words first, per-round cap, beyond-quota count, due-then-ahead reviews,
  round size, interleave, empty round.
- `tests/test_study_session_tail.py`: `scope=practice` gate.
- `tests/unit/session-tail.test.js`: extra-round helpers.
- Not covered: a SQL test of `get_review_ahead_items` (no local Postgres); a manual check
  after the live apply is needed.
