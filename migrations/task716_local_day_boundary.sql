-- TASK-716 — local-day boundary: resolve "today" (and the week) through the
--   plan timezone. Implements [[decisions/ADR-022-local-day-boundary]].
--   Also lands TASK-714's 'surface' progress kind (same function body).
-- =============================================================================
-- PROBLEM (F15)
--   The daily load rolled over at UTC midnight — 07:00-09:00 local for the
--   primary ZH/JA audience — so an evening learner's day flipped mid-morning
--   and an interrupted session could be replaced by a NEW day's load before
--   they returned to it. Meanwhile user_study_plans.timezone was collected,
--   stored, and never read.
--
--   weekly_plan_states.week_start_date inherited the same skew:
--   record_session_progress derived it as date_trunc('week', NOW())::date,
--   i.e. the UTC week.
--
-- DECISION — the week moves too (ADR-022 asks for this to be explicit).
--   Leaving the week on UTC while daily loads go local creates a NEW
--   inconsistency precisely at the week edge: for a UTC+9 learner between
--   00:00 and 09:00 local Monday, build_daily_session (which derives its week
--   from the local p_date via week_start_for) would read week W+1's targets
--   while record_session_progress credited week W's counters. Every completion
--   in that window would land in a week the resolver was no longer reading —
--   a silent, self-cancelling counter bug. So record_session_progress now
--   derives its week from public.plan_local_date, matching the resolver.
--
--   week_start_for() and date_trunc('week') are both Monday-anchored, so this
--   changes WHICH moment flips the week, never which weekday it flips on.
--
-- CUTOVER — accept a one-time discontinuity; no backfill.
--   Existing daily_test_loads.load_date and weekly_plan_states.week_start_date
--   rows were written under UTC semantics and are not re-interpretable: the
--   timezone a learner was in when a historical row was written is not
--   recorded anywhere. Backfilling would have to guess it. At cutover, a
--   learner east of UTC may therefore see one day where the previous local
--   date already has a row (served as-is, see the policy note below) or one
--   date with no row (a fresh load is solved). Both are single-day effects on
--   a table whose rows are day-scoped anyway. Historical rows are left alone.
--
-- TIMEZONE-CHANGE POLICY (the backwards-move case ADR-022 flags).
--   If a learner edits their timezone such that the local date moves BACKWARDS
--   onto a date that already has a daily_test_loads row,
--   test_service.get_or_create_daily_load short-circuits on the existing row
--   and returns it verbatim — build_daily_session is never re-invoked, so
--   TASK-705's same-day-safe path is not exercised and no progress can be
--   disturbed. A forward move simply begins a new date. Neither case needs a
--   guard inside the resolver; the guard is the caller's existing-row check,
--   and it is now load-bearing rather than incidental.
--
-- Idempotent: CREATE OR REPLACE throughout.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- resolve_plan_timezone(text) -> text
--
-- FAIL-SAFE BY CONTRACT (ADR-020): returns 'UTC' for NULL, empty, or any
-- string that is not a zone this server knows. It must never raise — V1 plan
-- validation accepted any non-empty string, so unusable values are already
-- stored, and a resolver that threw would take down the daily session for
-- those learners. Route-level validation (routes/study_plan.py) stops NEW bad
-- values; this stops the old ones from mattering.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.resolve_plan_timezone(p_tz text)
RETURNS text LANGUAGE sql STABLE AS $$
    SELECT COALESCE(
        (SELECT n.name
         FROM pg_timezone_names n
         WHERE n.name = btrim(COALESCE(p_tz, ''))
         LIMIT 1),
        'UTC'
    )
$$;

COMMENT ON FUNCTION public.resolve_plan_timezone IS
    'TASK-716: validate a stored plan timezone against pg_timezone_names, '
    'falling back to UTC. Never raises (ADR-020 fail-safe).';


-- ---------------------------------------------------------------------------
-- plan_local_date(user, language, at) -> date
--
-- The SQL twin of services/day_boundary.py::plan_today. RPC bodies that have
-- no Python caller (record_session_progress fires from
-- apply_attempt_timing_and_progress, itself a SQL function) need their own
-- derivation; both sides read the same column and apply the same fallback, so
-- they agree.
--
-- SECURITY DEFINER because callers are already SECURITY DEFINER RPCs reading
-- another user's plan row; the function takes the user id as an argument and
-- reads exactly one column, so it grants nothing new.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.plan_local_date(
    p_user_id     uuid,
    p_language_id smallint,
    p_at          timestamptz DEFAULT NOW()
)
RETURNS date
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_tz text;
BEGIN
    SELECT public.resolve_plan_timezone(usp.timezone)
      INTO v_tz
    FROM public.user_study_plans usp
    WHERE usp.user_id = p_user_id
      AND usp.language_id = p_language_id;

    -- No plan row at all -> UTC, same as an unset timezone.
    IF v_tz IS NULL THEN
        v_tz := 'UTC';
    END IF;

    RETURN (p_at AT TIME ZONE v_tz)::date;
EXCEPTION WHEN OTHERS THEN
    -- Belt and braces: resolve_plan_timezone already guarantees a known zone,
    -- so this can only fire on something pathological. Degrade to UTC rather
    -- than propagate — an exception here would abort a submission that has
    -- already been graded and persisted.
    RETURN (p_at AT TIME ZONE 'UTC')::date;
END
$function$;

COMMENT ON FUNCTION public.plan_local_date IS
    'TASK-716 / ADR-022: the learner''s local calendar date for (user, '
    'language), via user_study_plans.timezone. Falls back to UTC for a missing '
    'plan or an unusable zone. SQL twin of services/day_boundary.py.';


-- ---------------------------------------------------------------------------
-- record_session_progress — week now local (TASK-716) + 'surface' kind
-- (TASK-714).
--
-- Supersedes the function body in phase18_practice_time_seconds.sql. That file
-- is NOT archived: it is still the sole repo record of the
-- practice_completed_maint_sec / practice_completed_acq_sec columns (rule #4).
-- The seconds-ledger behaviour it introduced is carried forward verbatim.
--
-- CHANGES vs phase18:
--   1. v_week_start := week_start_for(plan_local_date(user, language))
--      instead of date_trunc('week', NOW())::date. Same Monday anchor, now
--      the learner's Monday.
--   2. p_kind accepts 'surface' — flashcards / dual_translation completions
--      (ADR-021 / TASK-714). A surface bumps completed_counts[p_skill] exactly
--      like a test does; it just has no test_attempts row behind it, so the
--      caller passes a deterministic uuid5 as p_attempt_id and the existing
--      session_progress_log dedupe makes a retried POST a no-op.
--      Without this, every planned flashcards/DT block would complete on the
--      UI and never move a weekly counter — the F2 / TASK-701 failure mode.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.record_session_progress(
    p_user_id       uuid,
    p_language_id   smallint,
    p_attempt_id    uuid,
    p_kind          text,
    p_skill         text,
    p_delta_count   integer DEFAULT 0,
    p_delta_minutes integer DEFAULT 0,
    p_delta_seconds integer DEFAULT 0
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    -- TASK-716: the learner's local week, matching build_daily_session's
    -- week_start_for(p_date). Was date_trunc('week', NOW())::date (UTC).
    v_week_start  date := public.week_start_for(
                              public.plan_local_date(p_user_id, p_language_id)
                          );
    v_log_key     text;
    v_already     boolean;
    v_updated     integer;
    v_sec         int  := GREATEST(0, COALESCE(p_delta_seconds, 0));
    v_maint_delta int  := 0;
    v_acq_delta   int  := 0;
BEGIN
    IF p_kind NOT IN ('test','surface','practice_maint','practice_acq') THEN
        RAISE EXCEPTION 'invalid p_kind=%; must be test|surface|practice_maint|practice_acq', p_kind
            USING ERRCODE = 'check_violation';
    END IF;
    -- 'surface' carries its skill the same way 'test' does — it is the key
    -- under which completed_counts and session_progress_log are recorded.
    IF p_kind IN ('test','surface') AND p_skill IS NULL THEN
        RAISE EXCEPTION 'p_skill required when p_kind=%', p_kind
            USING ERRCODE = 'check_violation';
    END IF;

    IF p_kind = 'practice_maint' THEN
        v_maint_delta := v_sec;
    ELSIF p_kind = 'practice_acq' THEN
        v_acq_delta := v_sec;
    END IF;

    v_log_key := CASE WHEN p_kind IN ('test','surface') THEN p_skill ELSE p_kind END;

    PERFORM 1 FROM public.weekly_plan_states
        WHERE user_id = p_user_id
          AND language_id = p_language_id
          AND week_start_date = v_week_start;
    IF NOT FOUND THEN
        RETURN true;
    END IF;

    SELECT EXISTS (
        SELECT 1 FROM public.weekly_plan_states
        WHERE user_id = p_user_id
          AND language_id = p_language_id
          AND week_start_date = v_week_start
          AND session_progress_log -> v_log_key ? p_attempt_id::text
    ) INTO v_already;
    IF v_already THEN
        RETURN false;
    END IF;

    UPDATE public.weekly_plan_states
       SET completed_counts =
             CASE
               WHEN p_kind IN ('test','surface') THEN
                 jsonb_set(
                   completed_counts,
                   ARRAY[p_skill],
                   to_jsonb(COALESCE((completed_counts->>p_skill)::int, 0) + p_delta_count)
                 )
               ELSE completed_counts
             END,
           practice_completed_maint_sec = practice_completed_maint_sec + v_maint_delta,
           practice_completed_acq_sec   = practice_completed_acq_sec   + v_acq_delta,
           practice_completed_maint_min =
             ROUND((practice_completed_maint_sec + v_maint_delta) / 60.0)::smallint,
           practice_completed_acq_min =
             ROUND((practice_completed_acq_sec + v_acq_delta) / 60.0)::smallint,
           session_progress_log = jsonb_set(
               session_progress_log,
               ARRAY[v_log_key],
               COALESCE(session_progress_log -> v_log_key, '[]'::jsonb)
                 || to_jsonb(p_attempt_id::text)
           )
     WHERE user_id = p_user_id
       AND language_id = p_language_id
       AND week_start_date = v_week_start;

    GET DIAGNOSTICS v_updated = ROW_COUNT;
    RETURN v_updated > 0;
END
$function$;

COMMENT ON FUNCTION public.record_session_progress IS
    'Idempotently credit one completion to the current weekly_plan_states row. '
    'p_kind: test | surface | practice_maint | practice_acq. TASK-716: the week '
    'is now the learner''s LOCAL week (plan_local_date), matching '
    'build_daily_session. TASK-714: ''surface'' covers flashcards / '
    'dual_translation, which have no test_attempts row — callers pass a '
    'deterministic uuid5 as p_attempt_id so retries dedupe.';

COMMIT;
