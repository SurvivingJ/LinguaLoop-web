---
title: Weekly Minutes — Technical Specification
type: feature-tech
status: planned
prose_page: ./weekly-minutes.md
last_updated: 2026-10-14
dependencies:
  - "table: study_time_ledger (new)"
  - "RPC: credit_study_time, get_weekly_study_seconds (new)"
  - "table: weekly_plan_states (read target only)"
  - "table: test_attempts (duration_ms, started_at), exercise_attempts (time_taken_ms)"
  - "services/attempt_timing.py, services/day_boundary.py (plan_today), services/practice_session_service.py"
  - "SQL: plan_local_date(user, language), week_start_for(date)"
breaking_change_risk: low
open_questions:
  - "OPEN: exact column/test-type join to split 'test' vs 'drill' in the backfill (TASK-886 verifies against live schema read-only)."
  - "OPEN: whether counts for tests taken with no weekly_plan_states row should also be kept (out of scope; minutes are not affected)."
---

# Weekly Minutes — Technical Specification

## Architecture Overview
```
test submit (routes/tests.py, classifier/counter drill) --> _apply_timing_and_progress --> credit_study_time(kind test|drill)
POST /api/practice/attempt (PracticeSessionService)     --> credit_study_time(kind practice)   [in or out of session]
POST /api/flashcards/review {active_ms,client_event_id} --> credit_study_time(kind flashcard)
POST /api/dual-translation/<id>/submit {active_ms}      --> credit_study_time(kind dual_translation)
POST /api/dual-translation/cards/<id>/review {active_ms,client_event_id} --> same kind
GET  /api/study-plan --> get_weekly_study_seconds(week = plan_today Monday) --> `weekly_study` field --> study_plan.html
```
Decision rationale: [[decisions/ADR-035-study-time-ledger]]. All credits are best-effort and never fail the learner's request (log a warning). Week attribution: the SQL function derives the week from `week_start_for(plan_local_date(user, language))` at credit time (same helpers `record_session_progress` uses, `migrations/task716_local_day_boundary.sql`).

## Defects fixed (verified 2026-10-14)
1. Only practice credits minutes: `record_session_progress` adds `p_delta_seconds` to `practice_completed_{maint,acq}_sec` and ignores `p_delta_minutes`; tests credit counts only (`routes/tests.py:284` `_apply_timing_and_progress` -> `apply_attempt_timing_and_progress`); flashcards/DT pass `p_delta_seconds: 0` (`routes/study_session.py:744`).
2. Page reads `practice_completed_*_min` (`templates/study_plan.html:694`).
3. Reader/writer week mismatch: `routes/study_plan.py:234, 505, 698` use `_monday_of(date.today())` (server date); writer uses learner-local week. `:291, :418` already use `plan_today`.
4. No weekly row: `record_session_progress` returns true and credits nothing.

## Database Impact
New table (see [[database/schema.tech]] to be updated by TASK-896):
```sql
CREATE TABLE public.study_time_ledger (
  id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id         uuid     NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  language_id     smallint NOT NULL REFERENCES public.dim_languages(id),
  week_start_date date     NOT NULL,                 -- learner-local Monday
  kind            text     NOT NULL CHECK (kind IN ('test','practice','flashcard','dual_translation','drill')),
  seconds         integer  NOT NULL CHECK (seconds BETWEEN 1 AND 1200),
  source_table    text     NOT NULL,                 -- 'test_attempts' | 'exercise_attempts' | 'flashcard_review' | 'dt_submission' | 'dt_card_review'
  source_id       text     NOT NULL,                 -- attempt uuid / submission id / client_event_id
  credited_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (kind, source_table, source_id)
);
CREATE INDEX study_time_ledger_week_idx ON public.study_time_ledger (user_id, language_id, week_start_date);
ALTER TABLE public.study_time_ledger ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.study_time_ledger FROM PUBLIC, anon, authenticated;   -- no policy: browser never reads it
```
`kind` meanings: `test` reading/listening/dictation/pinyin/pitch_accent tests; `drill` classifier and counter drills; `practice` vocabulary exercises incl. speed round (`is_speed_round` goes through `/api/practice/attempt`); `flashcard`; `dual_translation` (submissions and error-remediation card reviews).

## API / RPC Surface
### `credit_study_time(p_user_id uuid, p_language_id smallint, p_kind text, p_seconds integer, p_source_table text, p_source_id text): boolean`
- **Purpose:** credit measured seconds to the learner-local current week, once per source.
- **Arguments:** `p_kind` one of the five kinds else `check_violation`; `p_seconds` clamped in SQL by kind (test/drill 1200, practice 300, flashcard 120, dual_translation 900) after `GREATEST(0, ...)`; `p_seconds <= 0` -> no insert, returns false; `p_source_table`/`p_source_id` non-empty.
- **Returns:** `true` newly credited; `false` duplicate or zero. `INSERT ... ON CONFLICT (kind, source_table, source_id) DO NOTHING`.
- **Errors:** `check_violation` on bad kind or empty source.
- **Auth:** `SECURITY DEFINER`, `SET search_path = public, pg_temp`; `REVOKE ALL ... FROM PUBLIC, anon, authenticated; GRANT EXECUTE ... TO service_role`. No `auth.uid()` check needed (service-role only).
- **Side effects:** one ledger row. Does not touch `weekly_plan_states`.
### `get_weekly_study_seconds(p_user_id uuid, p_language_id smallint, p_week_start date): jsonb`
- **Returns:** `{"test":int,"practice":int,"flashcard":int,"dual_translation":int,"drill":int}` seconds, every key present (0 when none). Same grants as above.
### Backfill (`migrations/backfill_study_time_ledger.sql`, idempotent, approval-gated)
Current local week per user/language only. Sources: `test_attempts` (`duration_ms/1000`, clamped 1200, kind `test`, or `drill` for classifier/counter tests), `exercise_attempts` (`time_taken_ms`, with the same estimate fallback as `PracticeSessionService._credited_seconds` when missing or > 300 s, clamp 300, kind `practice`). Keys equal the live keys (`('test_attempts', attempt_id)`, `('exercise_attempts', attempt_id)`) so later replays and the first live credit never double count. Flashcard and DT: no stored timing, not backfilled (state in script header). Uses `ON CONFLICT DO NOTHING`; week from `user_study_plans.timezone` (UTC fallback) via the same SQL helpers.

### Python `services/study_time.py` (new)
- `KIND_CAPS_SECONDS = {'test':1200,'drill':1200,'practice':300,'flashcard':120,'dual_translation':900}` (mirror of SQL; reuse `MAX_CREDITED_ATTEMPT_SECONDS` for test/drill and `PRACTICE_ATTEMPT_MAX_SECONDS` for practice).
- `clamp_active_ms(kind, value) -> int` seconds: junk/negative/NaN -> 0; else `min(value/1000, cap)`; `bool` rejected.
- `credit_study_time(db, user_id, language_id, kind, seconds, source_table, source_id) -> bool`: best-effort RPC wrapper, never raises, logs warning.
- `weekly_study_summary(db, user_id, language_id, week_start, target_minutes) -> dict`.

### Endpoint changes
- Request bodies: `POST /api/flashcards/review` adds optional `active_ms: int` and `client_event_id: uuid`; `POST /api/dual-translation/<id>/submit` adds optional `active_ms`; `POST /api/dual-translation/cards/<id>/review` adds optional `active_ms`, `client_event_id`. Absent -> no credit (old cached JS). Credit source ids: flashcard `client_event_id` (fallback none -> no credit), DT submit `str(submission_id)`, DT card `client_event_id`.
- Tests/drills: seconds from the already validated window (`validate_attempt_window`, `services/attempt_timing.py:55`); no window -> no credit. Source `('test_attempts', str(attempt_id))`.
- Practice: in `PracticeSessionService` after the attempt insert (`practice_session_service.py` ~696), credit `delta_seconds` as kind `practice`, source `('exercise_attempts', str(attempt_id))`, whether or not a session item was supplied.
- `GET /api/study-plan` adds top-level field `weekly_study`:
```json
"weekly_study": {
  "week_start_date": "2026-10-12",
  "studied_seconds": 2040,
  "studied_minutes": 34,
  "target_minutes": 210,
  "by_kind": {
    "test":             {"seconds": 900,  "minutes": 15},
    "practice":         {"seconds": 600,  "minutes": 10},
    "flashcard":        {"seconds": 300,  "minutes": 5},
    "dual_translation": {"seconds": 240,  "minutes": 4},
    "drill":            {"seconds": 0,    "minutes": 0}
  }
}
```
`minutes = round(seconds/60)`; `studied_minutes = round(sum/60)`; `target_minutes = current_week.total_weekly_minutes` or `null` when no weekly row; `week_start_date` = `_monday_of(plan_today(...))`. All five `by_kind` keys always present. Failure degrades to `weekly_study: null` and never fails the GET. `current_week` is unchanged. Same field is added to the recompute/template responses only if they already return `current_week` (not required).

## Component Specification (UI)
### `renderWeekSummary` in `templates/study_plan.html` (~677-720)
- Replaces the "practice min done" tile with a progress bar "Studied this week: {done} / {target} min" (or "Studied this week: {done} min" when `target_minutes` is null), and a breakdown list of five kinds (hidden when zero is fine but all five rendered is simpler: show non-zero kinds, plus a muted empty state). The per-skill counts table is untouched; `practice_target` tile may stay as the planner target. Reads `payload.weekly_study`; if null falls back to hiding the block.
- i18n keys (en, zh, ja, es in `static/i18n/*.json`): `study_plan.studied.progress`, `study_plan.studied.progress_no_target`, `study_plan.studied.breakdown_title`, `study_plan.studied.kind.test|practice|flashcard|dual_translation|drill`, `study_plan.studied.empty`. Remove `study_plan.stat.practice_done` usage (delete key after i18n coverage test passes).
### Client active timer `static/js/active-timer.js` (new, exposes `window.ActiveTimer`)
`start()`, `stop() -> ms`, `reset()`. Counts only while `document.visibilityState === 'visible'` and the last pointer/key/touch event is < 45 s old (idle time beyond 45 s is dropped). Used per flashcard (start when the card face is shown, stop on rating) and per DT submission (start when the passage is shown / reproduction box focused? start when the passage appears, stop on submit). Sends `active_ms` (integer) and a fresh `client_event_id` (`crypto.randomUUID()`, reused on retry of the same card so a retry dedupes).

## Key Architectural Decisions
1. **Decision:** event-row ledger, display-only. **Rationale/alternatives:** [[decisions/ADR-035-study-time-ledger]].
2. **Decision:** credit in Python after the learner's request succeeds (best-effort), SQL does clamp + dedupe. **Rationale:** matches existing hooks; SQL clamp is defense in depth against a bad caller. **Rejected:** extending `apply_attempt_timing_and_progress` (live DB lacks recent columns/functions, forces one more coupled migration; ordering risk, TASK-869).
3. **Decision:** missing test timing earns 0, no estimate. **Rationale:** the developer asked for measured time; the practice-style estimate would reintroduce guessed minutes. **Rejected:** `dim_test_types.expected_minutes_p50` fallback.
4. **Decision:** the planner columns (`practice_completed_*`) are untouched.

## Security Considerations
Consistent with [[decisions/ADR-034-no-client-db-writes]]: table RLS on, no client privileges, writes only via service_role function; clients send only `active_ms`/`client_event_id`, always clamped server-side (Python and SQL), never trusted as seconds; per-source uniqueness bounds replay (a replayed `client_event_id` credits nothing; a client minting fresh ids can add at most the per-credit cap per real request, same trust model as the existing practice `time_taken_ms`). Must pass `tests/test_migration_security_lint.py` and `tests/sql/check_function_acls.sql`.

## Testing Strategy
SQL: duplicate source credited once, clamp per kind, bad kind raises, week = learner-local week for a non-UTC timezone near midnight, no weekly row still credits, ACL (anon/authenticated cannot execute or select), backfill idempotent and second run inserts 0. Python: clamp junk, wrapper never raises, each route credits once and skips when timing missing, `weekly_study` shape and `plan_today` week usage (three call sites). JS (vitest): ActiveTimer visibility/idle behavior, flashcard/DT payload contains `active_ms` + stable `client_event_id` on retry, page renders progress with and without target.

## Rollout
Migrations before code (as TASK-869); until the function exists, Python credit calls fail softly (logged) and `weekly_study` is null so the page hides the block. Live apply and backfill require explicit user approval ([[tasklist/weekly-minutes.tasks]] TASK-896).
