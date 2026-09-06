-- ============================================================================
-- Word-upload recurring match-sweep — advisory-lock RPCs + cursor table
-- Date: 2026-09-05
-- Task: Step 5 of wiki/tasklist/word-list-import.plan.md ("Word List Upload
--       -> Ladder Exposure + Matched Test Queueing", v3)
--
-- Two helper RPCs the recurring watchlist match-sweep
-- (services/word_list_import/sweep_cron.run_watchlist_sweep) calls through the
-- supabase client to serialise itself across gunicorn workers. Same pattern as
-- the weekly Study-Plan recompute (migrations/study_plan_advisory_lock.sql),
-- the nightly IRT calibrator (migrations/add_irt_calibration_metadata.sql),
-- the model-slug health probe (migrations/task510_model_health_advisory_lock.sql),
-- the generation-queue drain (migrations/task517_queue_drain_advisory_lock.sql)
-- and the DT error-synthesis cron (migrations/dt_synthesis_advisory_lock.sql):
-- postgrest cannot invoke the built-in pg_try_advisory_lock(bigint) directly
-- with a positional bigint via the supabase-py rpc() helper, so we wrap it
-- around a fixed key.
--
--   pg_try_advisory_lock_for_word_upload_sweep() — true iff this session
--                                                   took the lock.
--   pg_advisory_unlock_for_word_upload_sweep()   — releases the session's
--                                                   lock.
--
-- Lock key 1465209719 = 0x57555377 = ASCII 'WUSw' (Word-Upload Sweep).
-- Verified distinct from every other advisory-lock key already defined in
-- this repo (grepped `pg_try_advisory_lock(` across migrations/, excluding
-- migrations/archive/ per migrations/CLAUDE.md — archived files are history,
-- not live definitions, but none turned up there either):
--   8901234567890123  irt_try_lock()                              (nightly IRT calibrator)
--   1467840848         pg_try_advisory_lock_for_study_plan()       (weekly Study-Plan recompute)
--   1298417772         pg_try_advisory_lock_for_model_health()     (nightly slug-health probe)
--   1363440238         pg_try_advisory_lock_for_queue_drain()      (nightly generation-queue drain)
--   1146377081         pg_try_advisory_lock_for_dt_synthesis()     (nightly DT error synthesis)
-- 1465209719 matches none of the above. Computed as the big-endian byte value
-- of the 4 ASCII characters 'W','U','S','w' (0x57 0x55 0x53 0x77), the same
-- "pack 4 ASCII bytes into an int4-range bigint" convention every file above
-- documents for its own key (NOTE: the study-plan file's own comment claims
-- its key decodes to ASCII 'StPP', but 1467840848 = 0x577D7950 = bytes
-- "W}yP", not "StPP" — a pre-existing documentation slip in that file, not
-- reproduced here; this file's own key was verified to decode back to 'WUSw'
-- via `int.from_bytes(b'WUSw', 'big')` before being committed).
--
-- Session-level lock: run_watchlist_sweep() acquires it at the top and
-- releases it in a finally, on the same connection — identical shape to
-- every sibling cron listed above.
--
-- ----------------------------------------------------------------------------
-- Cursor table
-- ----------------------------------------------------------------------------
-- The sweep needs "tests created since the last sweep" so it never rescans
-- the whole `tests` table. Grepped this repo first for an existing generic
-- job-cursor table (`cron_state` / `job_cursors` / `sync_state` or similar) —
-- none exists; every other nightly job in this codebase is either a stateless
-- full recompute (Study-Plan pacer, IRT calibrator) or already has its own
-- queue table with its own progress marker (generation_queue.status/
-- requested_at). None of those shapes fit "a single scalar watermark", so a
-- new, dedicated, single-row table is added here rather than repurposing one
-- of those.
--
-- `tests.id` is a `uuid PRIMARY KEY DEFAULT gen_random_uuid()` (see
-- migrations/create_all_tables.sql), not a sequential/sortable key, so an
-- ID-based cursor is not possible — this MUST be a `tests.created_at`
-- watermark instead.
--
-- Single-row singleton (`id` pinned to 1 via CHECK), matching the shape of
-- the other tiny scalar-state tables in this repo (e.g. generation_queue's
-- per-row status columns, scaled down to a table that only ever needs one
-- row). No RLS: like generation_queue (migrations/generation_queue.sql,
-- no RLS block), this is an internal cron-state table only ever touched by
-- the service-role admin client, never by an end-user request — there is no
-- per-user data in it to protect.
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.pg_try_advisory_lock_for_word_upload_sweep()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT pg_try_advisory_lock(1465209719::bigint);
$$;

CREATE OR REPLACE FUNCTION public.pg_advisory_unlock_for_word_upload_sweep()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT pg_advisory_unlock(1465209719::bigint);
$$;

CREATE TABLE IF NOT EXISTS public.word_upload_sweep_state (
    id                     smallint     PRIMARY KEY DEFAULT 1,
    last_swept_created_at  timestamptz  NOT NULL DEFAULT '-infinity'::timestamptz,
    updated_at             timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT word_upload_sweep_state_singleton CHECK (id = 1)
);

COMMENT ON TABLE public.word_upload_sweep_state IS
  'Singleton watermark for the recurring word-upload watchlist match sweep '
  '(wiki/tasklist/word-list-import.plan.md Step 5, '
  'services/word_list_import/sweep_cron.run_watchlist_sweep). '
  'last_swept_created_at is the MAX(tests.created_at) actually observed by '
  'the most recent successful sweep pass that found at least one new test — '
  'a run that finds zero new tests leaves this column untouched. Only ever '
  'advanced forward, never read as an exact log of "when the cron last ran" '
  '(see updated_at for that).';

COMMENT ON COLUMN public.word_upload_sweep_state.last_swept_created_at IS
  'Exclusive lower bound: the next sweep queries tests.created_at > this '
  'value. Defaults to -infinity so a fresh install''s first run scans every '
  'existing test exactly once. Advanced to MAX(created_at) of the batch just '
  'processed, never to wall-clock now() — see '
  'services/word_list_import/sweep_cron.py module docstring for the '
  'clock-skew rationale (a value we actually observed in a committed row is '
  'never ahead of reality; an optimistic "now()" can be, and an uncommitted '
  'transaction that lands with a created_at before that "now()" but becomes '
  'visible only after it would then be silently skipped forever).';

-- Seed the single row. ON CONFLICT DO NOTHING makes this migration safe to
-- re-run without clobbering a watermark a live sweep has already advanced.
INSERT INTO public.word_upload_sweep_state (id, last_swept_created_at)
VALUES (1, '-infinity'::timestamptz)
ON CONFLICT (id) DO NOTHING;

COMMIT;


-- ----------------------------------------------------------------------------
-- Verification (run manually after applying — not executed by this file)
-- ----------------------------------------------------------------------------
-- SELECT proname FROM pg_proc
-- WHERE proname LIKE '%word_upload_sweep%' ORDER BY proname;
-- Expect: pg_advisory_unlock_for_word_upload_sweep,
--         pg_try_advisory_lock_for_word_upload_sweep.
--
-- SELECT public.pg_try_advisory_lock_for_word_upload_sweep();   -- expect true
-- SELECT public.pg_try_advisory_lock_for_word_upload_sweep();   -- true again:
--     -- a session-level lock nests, so re-taking it in the SAME session
--     -- proves nothing. Test contention from a SECOND connection.
-- SELECT public.pg_advisory_unlock_for_word_upload_sweep();     -- once per acquire
--
-- SELECT objid, mode, granted FROM pg_locks
--  WHERE locktype = 'advisory' AND objid = 1465209719;
--
-- SELECT * FROM public.word_upload_sweep_state;   -- exactly one row, id = 1
-- ============================================================================
