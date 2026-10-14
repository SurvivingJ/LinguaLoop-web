-- new_word_minutes_estimate.sql — nightly per-language cost of one new word
-- =============================================================================
-- TASK-870 (session-budget-settings), Migration 3. Spec:
--   wiki/features/session-budget-settings.tech.md (Migration 3).
--
-- public.refresh_new_word_minutes() RETURNS jsonb  -- {languages_updated: int}
-- Called by services/study_plan_service.py::_refresh_exercise_time_estimates AFTER the
-- refresh_practice_time_estimates RPC succeeds (so dim_exercise_types.expected_seconds_p50
-- is fresh). For each dim_languages row L:
--   1. W = user_word_ladder rows created in the last 30 days whose sense belongs to L.
--   2. items_w = count of that user's exercise_attempts on w.sense_id with created_at in
--      [w.created_at, w.created_at + 24 hours)  (24 hours, not the local day, to avoid a
--      per-row timezone join; documented approximation).
--   3. Needs >= 10 words with items_w >= 1, else new_word_minutes_est is left unchanged.
--   4. items_per_word = AVG(items_w) over those words;
--      median_seconds = percentile_cont(0.5) over those attempts of
--      COALESCE(det.expected_seconds_p50, det.expected_seconds) (dim_exercise_types det;
--      45 = the column default for an attempt whose exercise_type is unknown).
--   5. new_word_minutes_est = LEAST(15.0, GREATEST(0.5, ROUND(items_per_word * median_seconds / 60.0, 2))).
-- Depends on session_module_exclusions.sql (dim_languages.new_word_minutes_est).
-- Service role only. Idempotent: CREATE OR REPLACE.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.refresh_new_word_minutes()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_lang     RECORD;
    v_words    int;
    v_items    numeric;
    v_median   numeric;
    v_updated  int := 0;
BEGIN
    FOR v_lang IN SELECT dl.id FROM public.dim_languages dl LOOP
        WITH w AS (
            SELECT uwl.user_id, uwl.sense_id, uwl.created_at
              FROM public.user_word_ladder uwl
              JOIN public.dim_word_senses dws ON dws.id = uwl.sense_id
              JOIN public.dim_vocabulary  dv  ON dv.id  = dws.vocab_id
             WHERE dv.language_id = v_lang.id
               AND uwl.created_at >= now() - interval '30 days'
        ), att AS (
            SELECT w.user_id, w.sense_id,
                   COALESCE(det.expected_seconds_p50, det.expected_seconds::numeric, 45) AS secs
              FROM w
              JOIN public.exercise_attempts ea
                ON ea.user_id = w.user_id
               AND ea.sense_id = w.sense_id
               AND ea.created_at >= w.created_at
               AND ea.created_at <  w.created_at + interval '24 hours'
              LEFT JOIN public.dim_exercise_types det ON det.type_code = ea.exercise_type
        ), per_word AS (
            SELECT user_id, sense_id, COUNT(*) AS items_w FROM att GROUP BY user_id, sense_id
        )
        SELECT (SELECT COUNT(*) FROM per_word),
               (SELECT AVG(items_w) FROM per_word),
               (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY secs) FROM att)
          INTO v_words, v_items, v_median;

        IF COALESCE(v_words, 0) >= 10 AND v_items IS NOT NULL AND v_median IS NOT NULL THEN
            UPDATE public.dim_languages
               SET new_word_minutes_est =
                     LEAST(15.0, GREATEST(0.5, ROUND(v_items * v_median / 60.0, 2)))
             WHERE id = v_lang.id;
            v_updated := v_updated + 1;
        END IF;
    END LOOP;

    RETURN jsonb_build_object('languages_updated', v_updated);
END
$function$;

REVOKE EXECUTE ON FUNCTION public.refresh_new_word_minutes() FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION public.refresh_new_word_minutes() TO service_role;

COMMENT ON FUNCTION public.refresh_new_word_minutes() IS
    'TASK-870: nightly estimate of minutes to introduce one new word, per language, into '
    'dim_languages.new_word_minutes_est (needs >= 10 words in the last 30 days, else unchanged).';
