-- =============================================================================
-- New-word drill load in the review governor (TASK-919, ADR-040)
--
-- review_governor_state (canonical body was migrations/review_governor.sql;
-- that file still defines other live objects, so it is not archived) now also
-- counts due new-word-drill reviews: intro sessions 2-4 (and session-1
-- restarts/overloads), each weighted by its expected items (4 / 3 / 3; 7 for a
-- session 1). due_items / overdue_items are therefore review ITEMS, which is
-- what the minutes conversion (items x item_seconds) always assumed.
-- Idempotent.
-- =============================================================================

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
        SELECT uf.sense_id, (uf.due_date < p_date) AS is_overdue, 1 AS items
          FROM public.user_flashcards uf
         WHERE uf.user_id = p_user_id
           AND uf.language_id = p_language_id
           AND uf.due_date IS NOT NULL
           AND uf.due_date <= p_date
        UNION ALL
        SELECT uwl.sense_id, (uwl.review_due_at < v_local_start) AS is_overdue, 1 AS items
          FROM public.user_word_ladder uwl
          JOIN public.dim_word_senses dws ON dws.id = uwl.sense_id
          JOIN public.dim_vocabulary  dv  ON dv.id  = dws.vocab_id
         WHERE uwl.user_id = p_user_id
           AND dv.language_id = p_language_id
           AND uwl.review_due_at IS NOT NULL
           AND uwl.review_due_at < v_local_next
        UNION ALL
        -- New-word drill reviews (sessions 2-4, restarts, overloads): one row
        -- per due intro word, weighted by its expected items
        -- (services/intro_drill.INTRO_STAGE_ITEMS_EST). Brand-new stage-1
        -- words are new words, not reviews, and are not counted.
        SELECT uwl.sense_id, (uwl.intro_due_date < p_date) AS is_overdue,
               CASE uwl.intro_stage WHEN 2 THEN 4 WHEN 3 THEN 3 WHEN 4 THEN 3 ELSE 7 END AS items
          FROM public.user_word_ladder uwl
          JOIN public.dim_word_senses dws ON dws.id = uwl.sense_id
          JOIN public.dim_vocabulary  dv  ON dv.id  = dws.vocab_id
         WHERE uwl.user_id = p_user_id
           AND dv.language_id = p_language_id
           AND uwl.word_state = 'intro'
           AND uwl.intro_due_date <= p_date
           AND (uwl.intro_stage >= 2
                OR uwl.intro_history @> '[{"event": "restart"}]'::jsonb
                OR uwl.intro_history @> '[{"event": "overload"}]'::jsonb)
    ), per_sense AS (
        SELECT sense_id, bool_or(is_overdue) AS is_overdue, MAX(items) AS items
          FROM src GROUP BY sense_id
    )
    SELECT COALESCE(SUM(items), 0)::int, COALESCE(SUM(items) FILTER (WHERE is_overdue), 0)::int
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

REVOKE ALL ON FUNCTION public.review_governor_state(uuid, smallint, date) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.review_governor_state(uuid, smallint, date) TO service_role;
