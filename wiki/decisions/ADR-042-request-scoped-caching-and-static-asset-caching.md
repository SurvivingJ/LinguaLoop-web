---
title: "ADR-042: Request-scoped read cache, tz_names lookup, and long-cached static assets"
status: accepted
date: 2026-11-11
---

# ADR-042: Request-scoped read cache, tz_names lookup, and long-cached static assets

## Context

A latency audit on 2026-11-11 ([[evaluations/latency-2026-11-11]]) found three causes of
slow pages, in order of size:

1. **`resolve_plan_timezone` scanned `pg_timezone_names` on every call.** That view reads the
   whole tz database from disk: ~55 ms warm, ~300–500 ms on a fresh connection, against
   0.05 ms for the conversion itself. It runs inside `plan_local_date` / `plan_local_day_start`,
   so every test submit (`apply_attempt_timing_and_progress` → `record_session_progress`),
   `credit_study_time`, `review_governor_state` and `build_daily_session` paid it.
2. **The busiest GETs made 16–28 sequential Supabase round trips**, many of them repeats: the
   `user_study_plans` row up to six times per request, the new-word state (plan read +
   `review_governor_state` + `ladder_new_word_state`) up to three times, and
   `dim_test_types` once per skill (6–7×). Each round trip is 50–100 ms from production.
3. **Static files were sent uncompressed and re-checked on every navigation** (Flask's
   default `Cache-Control: no-cache`). Pages also waited for `/api/metadata` and two serial
   i18n fetches before their first real API call, and the session page imported all ten
   players (~256 KB, a 4-level import chain) before it could ask for today's session.

The Railway instance is hobby-tier, so raising gunicorn concurrency was explicitly ruled out
by the developer.

## Decision

1. **`public.tz_names`** holds a snapshot of `pg_timezone_names.name` (primary key).
   `resolve_plan_timezone` looks names up there first and falls back to the old scan only for
   a name missing from the snapshot, so it accepts exactly the same names as before.
   `migrations/latency_2026_11_db.sql`; rollback in `latency_2026_11_db_rollback.sql`.
   **Not yet applied live** (2026-11-11: the Supabase confirmation prompt timed out unanswered).
2. **`services/request_cache.py`**: `memo(key, loader)` caches on `flask.g` for the life of
   one **GET/HEAD** request only. Writes (PUT/POST/…) never read from it, so a handler that
   writes a plan and reads it back always sees the database. Exceptions are never cached.
   Users:
   - `day_boundary.plan_row()` — the whole `user_study_plans` row, read once per GET;
     `plan_timezone`, `plan_today*`, `get_prestudy_mode`, `TestService._user_has_study_plan`,
     `TestService._excluded_modules`, `PracticeSessionService._daily_minutes` /
     `new_word_state`, `StudyPlanService.compute_weekly_plan` and `GET /api/study-plan` all
     go through it.
   - `PracticeSessionService.new_word_state()` — memoised per GET; every write to
     `user_word_ladder` (`_insert_ladder_rows`, `LadderService` upsert, the intro-drill
     writers) and a same-request `rebuild_today` call `request_cache.invalidate(...)`.
3. **`dim_test_types.expected_minutes_p50`** is read as one map per Supabase client and
   cached for 10 minutes (the column is refreshed nightly).
4. **Static assets** (`services/static_assets.py`): every `url_for('static', …)` URL carries
   `?v=<sha1[:10] of the file>`; a versioned request is served with a one-year
   `Cache-Control`, an unversioned one keeps Flask's revalidation. Flask-Compress serves
   gzip/brotli/zstd. i18n JSON gets versions via `window.LINGUA_I18N_VERSIONS`.
5. **Page start-up**: `/api/metadata` is embedded in every page (`window.LINGUA_METADATA`,
   from `DimensionService`'s in-memory cache, no DB work); i18n files load in parallel as soon
   as the script runs; the session page imports players on demand and preloads the ones
   today's queue needs; the test page reuses the preview's copy of `/api/tests/test/<slug>`;
   `authFetch` waits for the head script's token renewal and shares one renewal across all
   401s; `test-intro.js` loads only on test and drill pages.
6. Advisor clean-up in the same migration: four duplicate indexes dropped; 18 indexes on
   foreign keys whose parent rows are actually deleted (`dim_word_senses`, `exercises`,
   `word_assets`, `tests`, …); RLS policies wrap `auth.uid()` / `auth.role()` in a scalar
   sub-select so they are evaluated once per statement.

## Consequences

- Fewer round trips and no tz scan; measured before/after in
  [[evaluations/latency-2026-11-11]].
- New reads of `user_study_plans` in request code should use `day_boundary.plan_row()`; a
  new GET-path writer of `user_study_plans` or `user_word_ladder` must call
  `request_cache.invalidate(...)` (none exists today: plan writes are PUT/POST only).
- After a Postgres/tzdata upgrade, refresh `tz_names`
  (`INSERT INTO tz_names SELECT name FROM pg_timezone_names ON CONFLICT DO NOTHING`).
  Until then a newly added zone still resolves correctly, just slowly.
- Static files changed without changing their bytes cannot go stale (the hash is of the
  content). ES-module imports resolved relative to a module have no `v` and keep
  revalidating (a 304 each), which is correct but not free.
- Cached `user_study_plans` reads now select `*`; the GET route projects its documented
  columns so the response shape is unchanged.

## Alternatives Considered

- **More gunicorn threads/workers** — the biggest concurrency win, rejected by the developer
  to keep a hobby-tier Railway instance's demand low.
- **Process-wide cache of plan rows** — would need cross-worker invalidation on every plan
  write; the per-request cache gets most of the benefit with no staleness.
- **Validating time zones with `now() AT TIME ZONE p_tz` in an exception block** — fast, but
  accepts abbreviations and POSIX offsets that `pg_timezone_names` (and Python's ZoneInfo)
  reject, breaking ADR-022's rule that the SQL and Python sides agree.
- **A tail-only `/api/study-session` view for the end-of-session summary** — rejected: the
  tail gate depends on the full live queue (prestudy blocks, intro reviews, speed round), and
  the call is already off the critical path.
- **One RPC for the whole daily-session assembly** — larger change; left as a follow-up
  (TASK-930).
