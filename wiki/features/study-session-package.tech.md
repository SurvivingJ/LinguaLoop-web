---
title: Study Session Package (services/study_session) — Technical Specification
type: feature-tech
status: complete
prose_page: ./study-session-package.md
last_updated: 2026-11-23
dependencies:
  - "services/study_session/queue.py (pure composition) and services/study_session/session.py (reads / writes)"
  - "routes/study_session.py (blueprint study_session_bp, /api/study-session)"
  - "services/test_service.py::get_or_create_daily_load and daily_load_row_key"
  - "services/study_plan_service.py (StudyPlanService.rebuild_today, get_minutes_per_new_word, TAIL_OFFER_MAX_MIN)"
  - "services/practice_session_service.py (admit_daily_new_words, new_word_state, PRESTUDY_FOLLOWUP* constants)"
  - "services/intro_drill.py, services/prestudy.py, services/vocabulary_ladder/speed_round.py, services/dual_translation/repair (service.count_due, settings.DT_GUIDED_REPAIR)"
  - "services/day_boundary.py (plan_today_iso), services/request_cache.py, services/concurrency.py (run_parallel)"
  - "RPC: build_daily_session, record_session_progress; table: daily_test_loads (test_ids, daily_session_targets, completed_blocks)"
  - "static/js/session/controller.js, player_registry.js, tail.js, players/*"
breaking_change_risk: medium
open_questions:
  - "OPEN (known limitation, not fixed): the session's 'today' is the learner's local date, but flashcard (FSRS) due-ness is read in UTC by get_practice_session, get_session_senses, compute_weekly_plan_load_signals and the flashcards route, and in local date by build_daily_session and review_governor_state. All three live plans have timezone UTC (checked 2026-11-23). Detail in [[features/practice-engine.tech]]."
  - "The client sends scope=practice in Practice mode (static/js/session/controller.js); routes/study_session.py does not read a scope parameter. Whether anything server-side was meant to use it was not traced."
---

# Study Session Package (`services/study_session`) — Technical Specification

## Architecture Overview

```
GET /api/study-session?language_id=L
  routes/study_session.py::get_study_session
      parse_language_id; today = plan_today_iso(db, user, language)   (learner-local date)
      services/study_session/session.py::build_study_session(db, user, language, today,
            test_service=get_test_service(), practice_service=get_practice_session_service(),
            mpnw=lambda: minutes_per_new_word(db, language))
  → payload {load_date, language_id, study_plan_enabled, queue, progress, next_index,
             governor, tail, tail_queue}

POST /api/study-session/complete-block  {language_id, block_id}
  routes/study_session.py::complete_block → session.complete_block(...) → {completed_blocks}
```

`queue.py` is pure (imports `Config` and `study_plan_service` only; no database); `session.py` does every read and write. The package was split out of `routes/study_session.py` (the route still re-exports the old private names listed in its import block for tests). Package docstring: "Daily study session: queue composition (queue) and its reads/writes (session)." Mounted at `/api/study-session` in `app.py::_register_blueprints`.

## Module map

### `services/study_session/session.py` (468 lines)
| Name | Signature / role |
|---|---|
| `NoDailyLoad(LookupError)`, `InvalidBlockId(ValueError)` | raised by `complete_block`; `InvalidBlockId.valid_ids` |
| `minutes_per_new_word(db, language_id) -> float` | `_plan.get_minutes_per_new_word`, falls back to `Config.NEW_WORD_MINUTES_DEFAULT` (3.0) |
| `_attempt(fn) -> (value, error)` | runs one read, never raises |
| `_daily_load_with_intake(db, user, language, test_service, practice_service)` | `get_or_create_daily_load`; then `practice_service.admit_daily_new_words`; if `needs_rebuild` and `STUDY_PLAN_ENABLED`: `StudyPlanService(db).rebuild_today` ONCE, invalidates `new_word_state` and `daily_load_row` caches and re-reads the load. Intake failure is logged, never fatal |
| `_today_load_row(db, user, language, today)` | today's `daily_test_loads` row, memoised under `daily_load_row_key` |
| `due_followup_count(db, user, language, today)` | `len(prestudy.due_followup_senses(..., limit=PRESTUDY_FOLLOWUPS_PER_SESSION))`, 0 on failure |
| `intro_review_minutes(n_intro, n_followups)` | `max(1, ceil((n_intro * 4 * INTRO_ITEM_SECONDS + n_followups * 30) / 60))`, 0 if both zero |
| `_session_reads(...)` | concurrent reads (`run_parallel`), each `(value, error)`: `prestudy_plans` (`prestudy.plan_for_tests`), `speed_round` (`has_enough_mastered`), `intro_due` + `followups_due`, `mpnw`, `dt_repair_due` (`repair_service.count_due`). Runs outside the request context, so it reads nothing from the request cache |
| `_speed_round_offered`, `_with_prestudy`, `_intro_reviews_status`, `with_intro_reviews`, `_dt_repair_status`, `with_dt_repair`, `_governor_and_tail` | decorators over the queue (below); each is best effort |
| `build_study_session(db, user, language, today, *, test_service, practice_service, mpnw)` | the GET payload |
| `complete_block(db, user, language, today, block_id) -> List[str]` | validates and appends to `completed_blocks`; raises `NoDailyLoad` / `InvalidBlockId` |
| `record_surface_progress(db, user, language, load_date, block_id)` | `record_session_progress(p_kind='surface', p_skill=..., p_delta_count=1, p_delta_seconds=0)` with `p_attempt_id` = uuid5 over `(user, language, load_date, block_id)` in a fixed namespace, so a retried POST dedupes; skipped when the block has no surface skill or `STUDY_PLAN_ENABLED` is false |

### `services/study_session/queue.py` (644 lines)
Constants: `_PRACTICE_BLOCKS` (`practice_acq` -> mode `acquisition`, key `practice_acquisition_min`; `practice_maint` -> `maintenance`, `practice_maintenance_min`), `_PRACTICE_CHUNK_MAX_MIN = 10`, `_TAIL_BLOCKS = {'maintenance': 'tail_maint', 'acquisition': 'tail_acq'}`, `SURFACE_BLOCKS` (`flashcards`, `dual_translation`; `complete_as` is the `record_session_progress` skill), `_FLASHCARD_CARDS_PER_BLOCK = 15`, `SPEED_ROUND_BLOCK_ID = 'speed_round_1'`, `SPEED_ROUND_KIND = 'speed_round'`, `INTRO_REVIEWS_BLOCK_ID = 'intro_reviews'`, `DT_REPAIR_BLOCK_ID = DT_REPAIR_KIND = 'dt_repair'`, prestudy ids `prestudy_<test_id>`.

Functions: `next_incomplete_index`, `_stable_seed` (sha256 of `user:load_date`, first 8 hex digits), `_chunk_minutes` (25 -> [10, 10, 5]), `build_practice_chunks`, `_surface_counts` (from `daily_session_targets.surface_counts`; missing key means no surfaces), `build_surface_items` (ids `{skill}_{n}`; flashcard items carry `cards: 15`), `valid_block_ids(targets, extra_ids)`, `_round_robin_tests`, `_interleave_practice`, `_tail_offer_max_min` (`_plan.TAIL_OFFER_MAX_MIN`, `Config.TAIL_OFFER_MAX_MIN` = 20), `_is_main_complete`, `_build_tail_queue`, `tail_window_ids`, `compute_governor_and_tail`, `build_session_queue`, `prestudy_block_id`, `apply_prestudy`, `today_prestudy_ids`, `surface_skill_for`, `intro_reviews_status`, `insert_intro_reviews`, `dt_repair_status`, `insert_dt_repair`.

## Queue composition (`build_study_session`)

1. `_daily_load_with_intake` -> `tests`; `load_row` -> `targets = daily_session_targets`, `completed_blocks`; `load_date = daily_load.load_date or today`.
2. `state_outcome` = `practice_service.new_word_state(...)` (usually already in the request cache).
3. `intro_status` = `queue.intro_reviews_status(build_practice_chunks(...), targets, completed_blocks, enabled=intro_drill.ENABLED)`; `dt_repair_status` likewise (`enabled=repair_settings.DT_GUIDED_REPAIR`).
4. `_session_reads`: the speed round is skipped when `'practice'` is in `targets.excluded_modules`; intro counts only when `intro_status == 'check'`; `mpnw` only when a new-word state exists; DT-repair count only when status is `check`.
5. `build_session_queue(tests, targets, completed_blocks, user_id, load_date, speed_round_available)`: items are `kind='test'` (`id, slug, test_type, title, elo_rating, slot_type, is_completed`); order = flashcards first, then `_interleave_practice(round_robin(tests), practice_chunks + dual_translation items)`, then the bonus speed round (`is_bonus`) last. Deterministic per `(user, load_date)`.
6. `apply_prestudy` (via `_with_prestudy`): per test with a plan, adds `prestudy_offer {unknown_share, minutes_est, recommended}`; in mode `auto` inserts a `kind='prestudy'` block before every unfinished retry slot and every unfinished new test whose plan mode is `full` or `light`; mode `ask` recommends only (`full` or retry); mode `off` no blocks. When pending prestudy minutes reach one test slot (`test_budget_minutes / n_tests`), that many unstarted new tests without a block move to the end as optional (`is_bonus`, `deferred_for_prestudy`), before any speed round.
7. `with_intro_reviews`: status `done` keeps the chunk (completed); `check` adds `{kind: practice, id: intro_reviews, mode: maintenance, minutes}` before the first practice item when due drill reviews or follow-ups exist; `covered` / `off` add nothing.
8. `with_dt_repair`: adds `{kind: dt_repair, id: dt_repair, items: n}` before the first `dual_translation` item, else before the first practice item, else at the end, when `n_due > 0`.
9. `_governor_and_tail`: `compute_governor_and_tail(state, queue_without_tests, completed_blocks, mpnw)`; `governor = {level, overdue_items, overdue_minutes, threshold_minutes, new_words_quota, new_words_effective}` (null without a plan); `tail` only when every non-bonus item is complete and something remains: `reviews_left_items = governor.due_items` (0 if `practice` excluded), `new_words_left = max(0, min(E - started_today, unstarted))`, minutes via `item_seconds` (default 20) and `mpnw`; `tail_queue` = chunks of at most 10 minutes, at most 20 minutes per round (reviews first), ids `tail_maint_k` / `tail_acq_k` continuing after completed ones, `is_bonus` and `is_tail` true. Tail items never join `queue`, so `progress` and completion are unchanged.
10. Return `{load_date, language_id, study_plan_enabled: Config.STUDY_PLAN_ENABLED, queue, progress: {completed, total}, next_index, governor, tail, tail_queue}`.

## Completion (`complete_block`)
Reads today's `daily_test_loads` row (`NoDailyLoad` if absent). Valid ids = `valid_block_ids(daily_session_targets, extra_ids = tail_window_ids(blocks) | today_prestudy_ids(test_ids) | {intro_reviews, dt_repair})`, which also includes practice chunk ids, surface ids and `speed_round_1`. Not valid -> `InvalidBlockId`. If the id is new it is appended and written, then `record_surface_progress` runs (best effort; no-op for practice chunks, prestudy, speed round, intro reviews, DT repair and tail ids, which credit through their own services). Tail ids accepted: the next `ceil(20 / 10) = 2` of each kind after those already completed. Test slots complete through `POST /api/tests/daily-load/complete`, not here.

## How `/session` consumes it
`web/pages.py::register_pages` serves `/session` (endpoint `study_session_page`, template `study_session.html`). `static/js/session/controller.js` calls `GET /api/study-session?language_id=L` (plus `&scope=practice` in Practice mode), shows the start card, mounts `player_registry.getPlayer(item)` per queue item (dispatch on `item.kind`: `test`, `practice`, `flashcards`, `dual_translation`, `prestudy`, `dt_repair`, `speed_round`), and POSTs completion: `/api/tests/daily-load/complete` for tests, `/api/study-session/complete-block` for the rest. `tail` and `tail_queue` drive the "Keep going?" panel (`static/js/session/tail.js`). Page spec: [[pages/study-session.tech]]. Practice and intro-review chunks load their items from `GET /api/practice/session?mode=&minutes=` ([[features/practice-package.tech]]).

## Database Impact
Reads `daily_test_loads`, `user_study_plans` (through `day_boundary`), prestudy and intro tables (counts). Writes `daily_test_loads.completed_blocks`, and through `get_or_create_daily_load` / `rebuild_today` the day's targets. `record_session_progress` for surface blocks.

## API / RPC Surface
Both endpoints: `@supabase_jwt_required`, `user_id` from `g.current_user_id`. GET errors: 400 on bad `language_id`; 500 via `api_errors("Failed to build study session")`. POST errors: 400 (invalid language or block id), 404 (no daily load), 500 via `api_errors("Failed to mark block complete")`.

## Key Architectural Decisions
1. **Pure queue module, I/O module separate.** Rationale: ordering is easy to unit-test (`tests/test_study_session_ordering.py`, `test_study_session_tail.py`, `test_plannable_surfaces.py`, `test_prestudy_session.py`). Alternative rejected: ordering in the RPC (every tweak a migration).
2. **Concurrent, individually failing reads.** Each decoration degrades alone. Alternative rejected: one failure fails the page.
3. **Deterministic order from a hash seed**, not a stored order.

## Security Considerations
Block ids are validated against today's targets; a learner can only append to their own `completed_blocks`.

## Testing Strategy
See the test files above. Gap: no test pins the one-rebuild-per-day behaviour end to end against a database.

## Related Pages
- [[features/study-session-package]] — plain-English counterpart
- [[pages/study-session.tech]], [[features/study-plans.tech]], [[features/session-budget-settings.tech]], [[features/session-modules.tech]], [[features/test-prestudy.tech]], [[features/practice-package.tech]]
- [[decisions/ADR-021-plannable-surface-boundary]], [[decisions/ADR-022-local-day-boundary]], [[decisions/ADR-043-one-call-daily-session]]
