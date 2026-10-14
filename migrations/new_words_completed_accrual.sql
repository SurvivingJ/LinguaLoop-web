-- new_words_completed_accrual.sql — record_session_progress: new-word + tail accrual
-- =============================================================================
-- TASK-872 (session-budget-settings), Migration 4. Spec:
--   wiki/features/session-budget-settings.tech.md (Migration 4, 'Quota semantics')
--
-- Supersedes the record_session_progress body in migrations/task716_local_day_boundary.sql
-- (which itself superseded phase18_practice_time_seconds.sql). All existing logic is carried
-- forward verbatim (local week, 'surface' kind, seconds ledger, per-attempt dedupe). New:
--
--   * p_sense_id bigint DEFAULT NULL, p_is_tail boolean DEFAULT false.
--   * NEW-WORD ACCRUAL. When p_kind = 'practice_acq' AND p_sense_id IS NOT NULL AND the user has
--     a user_word_ladder row for that sense AND the sense's first-ever exercise_attempts row
--     (MIN(created_at) for user + sense) is on or after plan_local_day_start(...) (the current
--     attempt is already inserted when record_attempt_with_updates calls this function) AND
--     session_progress_log->'new_words' does not already contain p_sense_id::text:
--       new_words_completed + 1, append p_sense_id::text to session_progress_log['new_words'],
--       and tail_new_words_completed + 1 when p_is_tail.
--     'new_words' is a reserved session_progress_log key. A word admitted days ago and first
--     attempted today counts; a word admitted today and first attempted tomorrow counts tomorrow.
--     A retried attempt is rejected by the existing per-attempt dedupe before this point.
--   * TAIL MINUTES. When p_is_tail AND p_kind IN ('practice_acq','practice_maint'),
--     tail_completed_min grows by the same whole minutes this call adds to
--     practice_completed_acq_min / practice_completed_maint_min (those are ROUND(sec/60), so the
--     increment is the change of the rounded total). Tail work also counts toward the weekly
--     practice counters.
--
-- Also defines plan_local_day_start(uuid, smallint) -> timestamptz (00:00 of the learner's
-- local date; UTC for a missing plan / unusable zone), the SQL twin of
-- services/day_boundary.py::local_day_start_utc.
--
-- Depends on session_module_exclusions.sql (weekly_plan_states.new_words_completed,
-- tail_completed_min, tail_new_words_completed).
-- Idempotent: DROP FUNCTION IF EXISTS of the old 8-arg signature, then CREATE OR REPLACE.
-- =============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.plan_local_day_start(
    p_user_id     uuid,
    p_language_id smallint
)
RETURNS timestamptz
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

    RETURN public.plan_local_date(p_user_id, p_language_id)::timestamp
           AT TIME ZONE COALESCE(v_tz, 'UTC');
EXCEPTION WHEN OTHERS THEN
    RETURN (NOW() AT TIME ZONE 'UTC')::date::timestamp AT TIME ZONE 'UTC';
END
$function$;

COMMENT ON FUNCTION public.plan_local_day_start IS
    'TASK-872: 00:00 of the learner''s current local date as timestamptz (user_study_plans.timezone, '
    'UTC fallback). SQL twin of services/day_boundary.py::local_day_start_utc.';

-- Avoid an ambiguous overload next to the 10-argument version.
DROP FUNCTION IF EXISTS public.record_session_progress(
    uuid, smallint, uuid, text, text, integer, integer, integer);

CREATE OR REPLACE FUNCTION public.record_session_progress(
    p_user_id       uuid,
    p_language_id   smallint,
    p_attempt_id    uuid,
    p_kind          text,
    p_skill         text,
    p_delta_count   integer DEFAULT 0,
    p_delta_minutes integer DEFAULT 0,
    p_delta_seconds integer DEFAULT 0,
    p_sense_id      bigint  DEFAULT NULL,      -- TASK-872
    p_is_tail       boolean DEFAULT false      -- TASK-872
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    -- TASK-716: the learner's local week, matching build_daily_session's
    -- week_start_for(p_date).
    v_week_start  date := public.week_start_for(
                              public.plan_local_date(p_user_id, p_language_id)
                          );
    v_log_key     text;
    v_already     boolean;
    v_updated     integer;
    v_sec         int  := GREATEST(0, COALESCE(p_delta_seconds, 0));
    v_maint_delta int  := 0;
    v_acq_delta   int  := 0;
    -- TASK-872
    v_new_word    boolean := false;
    v_tail        boolean := COALESCE(p_is_tail, false);
BEGIN
    IF p_kind NOT IN ('test','surface','practice_maint','practice_acq') THEN
        RAISE EXCEPTION 'invalid p_kind=%; must be test|surface|practice_maint|practice_acq', p_kind
            USING ERRCODE = 'check_violation';
    END IF;
    -- 'surface' carries its skill the same way 'test' does.
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

    -- TASK-872: does this attempt START a new word today? (see header)
    IF p_kind = 'practice_acq' AND p_sense_id IS NOT NULL THEN
        SELECT (
                   EXISTS (SELECT 1 FROM public.user_word_ladder uwl
                            WHERE uwl.user_id = p_user_id AND uwl.sense_id = p_sense_id)
               AND COALESCE((SELECT MIN(ea.created_at)
                               FROM public.exercise_attempts ea
                              WHERE ea.user_id = p_user_id
                                AND ea.sense_id = p_sense_id)
                            >= public.plan_local_day_start(p_user_id, p_language_id), false)
               AND NOT COALESCE(wps.session_progress_log -> 'new_words' ? p_sense_id::text, false)
               )
          INTO v_new_word
          FROM public.weekly_plan_states wps
         WHERE wps.user_id = p_user_id
           AND wps.language_id = p_language_id
           AND wps.week_start_date = v_week_start;
        v_new_word := COALESCE(v_new_word, false);
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
           -- TASK-872: tail minutes = change of the rounded practice minutes for this call.
           tail_completed_min = tail_completed_min + CASE
               WHEN v_tail AND p_kind = 'practice_maint' THEN
                 GREATEST(0, ROUND((practice_completed_maint_sec + v_maint_delta) / 60.0)::int
                             - practice_completed_maint_min)
               WHEN v_tail AND p_kind = 'practice_acq' THEN
                 GREATEST(0, ROUND((practice_completed_acq_sec + v_acq_delta) / 60.0)::int
                             - practice_completed_acq_min)
               ELSE 0 END,
           new_words_completed = new_words_completed + CASE WHEN v_new_word THEN 1 ELSE 0 END,
           tail_new_words_completed = tail_new_words_completed
               + CASE WHEN v_new_word AND v_tail THEN 1 ELSE 0 END,
           session_progress_log = jsonb_set(
               CASE WHEN v_new_word THEN
                      jsonb_set(session_progress_log, ARRAY['new_words'],
                                COALESCE(session_progress_log -> 'new_words', '[]'::jsonb)
                                  || to_jsonb(p_sense_id::text))
                    ELSE session_progress_log END,
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
    'is the learner''s LOCAL week (plan_local_date). TASK-714: ''surface'' covers '
    'flashcards / dual_translation (callers pass a deterministic uuid5 as p_attempt_id). '
    'TASK-872: p_sense_id (practice_acq only) counts a word toward new_words_completed on the '
    'local day of its first-ever exercise_attempts row, once per sense per week; p_is_tail also '
    'credits tail_completed_min / tail_new_words_completed.';

-- Review fix: both are SECURITY DEFINER and take a caller-supplied p_user_id, so the default
-- EXECUTE-to-PUBLIC (live: proacl of the pre-existing 8-arg record_session_progress is
-- {=X, anon=X, authenticated=X, service_role=X}) would let any logged-in user credit another
-- user's counters. The only caller is the Flask backend (services.supabase_factory.get_supabase_admin,
-- service role): services/practice_session_service.py and routes/study_session.py.
-- A CREATE of a NEW signature does not inherit the old ACL, so it must be locked down here.
REVOKE ALL ON FUNCTION public.plan_local_day_start(uuid, smallint) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.plan_local_day_start(uuid, smallint) TO service_role;
REVOKE ALL ON FUNCTION public.record_session_progress(
    uuid, smallint, uuid, text, text, integer, integer, integer, bigint, boolean)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.record_session_progress(
    uuid, smallint, uuid, text, text, integer, integer, integer, bigint, boolean)
    TO service_role;

COMMIT;
