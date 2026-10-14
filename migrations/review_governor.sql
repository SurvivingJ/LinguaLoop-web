-- review_governor.sql — review-load governor + new-word quota state helpers
-- =============================================================================
-- TASK-874 (session-budget-settings), Migration 5. Spec:
--   wiki/features/session-budget-settings.tech.md (Migration 5, 'Quota semantics')
--   wiki/decisions/ADR-033-budget-scope-and-new-word-budget.md
--
-- Read-only helpers. Applied BEFORE session_module_exclusions_build_daily_session.sql
-- (build_daily_session calls review_governor_state, new_words_effective and
-- ladder_new_word_state). Depends on session_module_exclusions.sql
-- (user_study_plans.excluded_modules, weekly_plan_states.review_target_minutes) and on
-- task716_local_day_boundary.sql (resolve_plan_timezone).
--
-- Constants mirrored in config.py (change one, change both; test-pinned):
--   REVIEW_BACKLOG_THRESHOLD_DAYS = 1.0
--   REVIEW_ALLOWANCE_FLOOR_MIN    = 3.0
--   REVIEW_ITEM_SECONDS_DEFAULT   = 20.0
--
-- Idempotent: CREATE OR REPLACE only.
-- =============================================================================

-- Pure. Level of the governor for a backlog and a threshold, both in minutes.
CREATE OR REPLACE FUNCTION public.review_governor_level(p_backlog_min numeric, p_threshold_min numeric)
RETURNS text LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE WHEN p_threshold_min IS NULL OR p_threshold_min <= 0 THEN 'normal'
                WHEN p_backlog_min <= p_threshold_min      THEN 'normal'
                WHEN p_backlog_min <= 2 * p_threshold_min  THEN 'reduced'
                ELSE 'paused' END
$$;

-- Pure. Effective new words = quota | floor(quota/2) | 0.
CREATE OR REPLACE FUNCTION public.new_words_effective(p_quota int, p_level text)
RETURNS int LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE p_level WHEN 'paused'  THEN 0
                        WHEN 'reduced' THEN GREATEST(p_quota, 0) / 2     -- integer division = floor
                        ELSE GREATEST(p_quota, 0) END
$$;

-- Median seconds of one timed exercise attempt for this learner and language over 30 days
-- (time_taken_ms between 1000 and 120000); fewer than 20 samples -> 20.0.
-- v1 (ANSWERED 2026-10-13): ALL vocabulary-exercise attempts, no review-only filter
-- (exercise_attempts has no maintenance flag). It is therefore an ESTIMATE of review seconds.
CREATE OR REPLACE FUNCTION public.review_item_seconds(p_user_id uuid, p_language_id smallint)
RETURNS numeric
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $$
    SELECT CASE WHEN COUNT(*) >= 20
                THEN ROUND((percentile_cont(0.5) WITHIN GROUP (ORDER BY ea.time_taken_ms))::numeric / 1000.0, 2)
                ELSE 20.0 END
      FROM public.exercise_attempts ea
      JOIN public.dim_word_senses dws ON dws.id = ea.sense_id
      JOIN public.dim_vocabulary  dv  ON dv.id  = dws.vocab_id AND dv.language_id = p_language_id
     WHERE ea.user_id = p_user_id
       AND ea.created_at >= now() - interval '30 days'
       AND ea.time_taken_ms BETWEEN 1000 AND 120000
$$;

-- {overdue_items, overdue_minutes, due_items, due_minutes, threshold_minutes, item_seconds, level}
--
--   local_start = p_date at 00:00 in the learner's plan timezone (UTC if unset/unknown).
--   Overdue (the backlog): DISTINCT senses with user_flashcards.due_date < p_date, UNION
--     user_word_ladder rows with review_due_at IS NOT NULL AND review_due_at < local_start.
--   Due now: due_date <= p_date, review_due_at < local_start + 1 local day (overdue + due today).
--   Threshold T (minutes) = 1.0 * GREATEST(3.0, review_target_minutes / 7.0), the target
--     from the Monday-start weekly_plan_states row of p_date (none -> the floor).
--   'practice' in user_study_plans.excluded_modules: level 'normal' and all counts/minutes/
--     threshold 0 (the learner turned review off). item_seconds is still reported.
CREATE OR REPLACE FUNCTION public.review_governor_state(
    p_user_id uuid, p_language_id smallint, p_date date
) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $$
DECLARE
    c_threshold_days constant numeric := 1.0;    -- Config.REVIEW_BACKLOG_THRESHOLD_DAYS
    c_floor_min      constant numeric := 3.0;    -- Config.REVIEW_ALLOWANCE_FLOOR_MIN
    v_tz           text;
    v_excluded     text[] := '{}'::text[];
    v_local_start  timestamptz;
    v_local_next   timestamptz;
    v_overdue      int := 0;
    v_due          int := 0;
    v_item_sec     numeric;
    v_review_tgt   numeric;
    v_threshold    numeric;
    v_over_min     numeric;
    v_due_min      numeric;
BEGIN
    SELECT public.resolve_plan_timezone(usp.timezone),
           COALESCE(usp.excluded_modules, '{}'::text[])
      INTO v_tz, v_excluded
      FROM public.user_study_plans usp
     WHERE usp.user_id = p_user_id AND usp.language_id = p_language_id;
    v_tz := COALESCE(v_tz, 'UTC');
    v_excluded := COALESCE(v_excluded, '{}'::text[]);

    v_item_sec := public.review_item_seconds(p_user_id, p_language_id);

    IF 'practice' = ANY(v_excluded) THEN
        RETURN jsonb_build_object(
            'overdue_items', 0, 'overdue_minutes', 0,
            'due_items', 0, 'due_minutes', 0,
            'threshold_minutes', 0, 'item_seconds', v_item_sec,
            'level', 'normal');
    END IF;

    v_local_start := p_date::timestamp AT TIME ZONE v_tz;
    v_local_next  := (p_date + 1)::timestamp AT TIME ZONE v_tz;

    WITH src AS (
        SELECT uf.sense_id, (uf.due_date < p_date) AS is_overdue
          FROM public.user_flashcards uf
         WHERE uf.user_id = p_user_id
           AND uf.language_id = p_language_id
           AND uf.due_date IS NOT NULL
           AND uf.due_date <= p_date
        UNION ALL
        SELECT uwl.sense_id, (uwl.review_due_at < v_local_start) AS is_overdue
          FROM public.user_word_ladder uwl
          JOIN public.dim_word_senses dws ON dws.id = uwl.sense_id
          JOIN public.dim_vocabulary  dv  ON dv.id  = dws.vocab_id
         WHERE uwl.user_id = p_user_id
           AND dv.language_id = p_language_id
           AND uwl.review_due_at IS NOT NULL
           AND uwl.review_due_at < v_local_next
    ), per_sense AS (
        SELECT sense_id, bool_or(is_overdue) AS is_overdue
          FROM src GROUP BY sense_id
    )
    SELECT COUNT(*)::int, (COUNT(*) FILTER (WHERE is_overdue))::int
      INTO v_due, v_overdue
      FROM per_sense;

    SELECT wps.review_target_minutes::numeric
      INTO v_review_tgt
      FROM public.weekly_plan_states wps
     WHERE wps.user_id = p_user_id
       AND wps.language_id = p_language_id
       AND wps.week_start_date = public.week_start_for(p_date);

    v_threshold := c_threshold_days * GREATEST(c_floor_min, COALESCE(v_review_tgt, 0) / 7.0);
    v_over_min  := v_overdue * v_item_sec / 60.0;
    v_due_min   := v_due     * v_item_sec / 60.0;

    RETURN jsonb_build_object(
        'overdue_items',     v_overdue,
        'overdue_minutes',   ROUND(v_over_min, 2),
        'due_items',         v_due,
        'due_minutes',       ROUND(v_due_min, 2),
        'threshold_minutes', ROUND(v_threshold, 2),
        'item_seconds',      v_item_sec,
        'level',             public.review_governor_level(v_over_min, v_threshold));
END
$$;

-- Quota-semantics counts. p_day_start = 00:00 of the learner's local date as timestamptz.
-- A word is the ladder row (user_id, sense_id). started_at = the first exercise_attempts row
-- for that word, matched BY sense_id OR (legacy rows written before exercise_scheduling.sql,
-- sense_id IS NULL) via exercise_id -> exercises.word_sense_id.
--
-- unstarted (U) counts only ladder rows that a session can still actually serve as a NEW word:
--   * word_state IN ('new','active','gated','pre_mastery','relearning')  (the same set the
--     practice-session selector serves; mastered / legacy states are not "unstarted"),
--   * no attempt at all (by sense_id or via exercise_id),
--   * servable: >= 3 active exercises in this language (mirrors
--     services/practice_session_service.LADDER_MIN_EXERCISES_PER_SENSE, the T4.1 supply gate),
--   * admitted within the last 14 days (c_unstarted_max_age_days): an admitted-but-never-started
--     word older than that is abandoned and must not hold the quota shut forever.
-- started_today (ST) counts any ladder row whose first attempt is on/after p_day_start, whatever
-- its state or supply (a word consumed today stays consumed), with the same started_at.
-- {unstarted: int, started_today: int, unstarted_sense_ids: jsonb int array (oldest
--  user_word_ladder.created_at first, ties by sense_id, max 200 -- the same filtered set as U)}
CREATE OR REPLACE FUNCTION public.ladder_new_word_state(
    p_user_id uuid, p_language_id smallint, p_day_start timestamptz)
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  WITH w AS (
    SELECT uwl.sense_id, uwl.created_at AS admitted_at, uwl.word_state,
           LEAST(
             (SELECT MIN(ea.created_at) FROM public.exercise_attempts ea
               WHERE ea.user_id = uwl.user_id AND ea.sense_id = uwl.sense_id),
             (SELECT MIN(ea.created_at) FROM public.exercise_attempts ea
                JOIN public.exercises ex ON ex.id = ea.exercise_id
               WHERE ea.user_id = uwl.user_id AND ea.sense_id IS NULL
                 AND ex.word_sense_id = uwl.sense_id)) AS started_at,
           (SELECT COUNT(*) FROM public.exercises ex
             WHERE ex.word_sense_id = uwl.sense_id AND ex.language_id = p_language_id
               AND ex.is_active) >= 3 AS servable
      FROM public.user_word_ladder uwl
      JOIN public.dim_word_senses dws ON dws.id = uwl.sense_id
      JOIN public.dim_vocabulary  dv  ON dv.id  = dws.vocab_id
     WHERE uwl.user_id = p_user_id AND dv.language_id = p_language_id),
  u AS (
    SELECT sense_id, admitted_at FROM w
     WHERE started_at IS NULL AND servable
       AND word_state IN ('new','active','gated','pre_mastery','relearning')
       AND admitted_at >= now() - interval '14 days')
  SELECT jsonb_build_object(
    'unstarted',     (SELECT COUNT(*) FROM u),
    'started_today', (SELECT COUNT(*) FROM w WHERE started_at >= p_day_start),
    'unstarted_sense_ids', COALESCE((SELECT jsonb_agg(sense_id ORDER BY admitted_at, sense_id)
        FROM (SELECT sense_id, admitted_at FROM u ORDER BY admitted_at, sense_id LIMIT 200) x), '[]'::jsonb));
$$;
-- Uses idx_ea_user_sense_type (user_id, sense_id, exercise_type, created_at DESC) from exercise_scheduling.sql.

-- Backend (service role) only: these read the caller-supplied user's rows.
REVOKE ALL ON FUNCTION public.review_item_seconds(uuid, smallint)                    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.review_governor_state(uuid, smallint, date)            FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ladder_new_word_state(uuid, smallint, timestamptz)     FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.review_item_seconds(uuid, smallint)                 TO service_role;
GRANT EXECUTE ON FUNCTION public.review_governor_state(uuid, smallint, date)         TO service_role;
GRANT EXECUTE ON FUNCTION public.ladder_new_word_state(uuid, smallint, timestamptz)  TO service_role;

COMMENT ON FUNCTION public.review_governor_state(uuid, smallint, date) IS
    'TASK-874: review backlog + governor level (normal|reduced|paused) for a learner/language/local date. '
    'See wiki/features/session-budget-settings.tech.md Migration 5.';
COMMENT ON FUNCTION public.ladder_new_word_state(uuid, smallint, timestamptz) IS
    'TASK-874/871: {unstarted, started_today, unstarted_sense_ids} for the Anki-like new-word quota. '
    'started_at = MIN(exercise_attempts.created_at) per (user, sense).';
