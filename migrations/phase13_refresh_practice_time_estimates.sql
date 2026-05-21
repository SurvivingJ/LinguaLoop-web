-- ============================================================================
-- Phase 13 — Study Plans — refresh_practice_time_estimates RPC
-- Date: 2026-05-21
--
-- Nightly job (registered in app.py at 04:05 UTC, 5 min after IRT) refreshes
-- the observed-P50 columns from real attempt durations:
--
--   dim_exercise_types.expected_seconds_p50  ← exercise_attempts.time_taken_ms
--   dim_test_types.expected_minutes_p50      ← test_attempts.duration_ms
--
-- Both updates require ≥ 30 samples from the last 30 days for the type to
-- qualify. Service-layer helpers prefer _p50 when set; otherwise fall back
-- to the seeded Config.TEST_TYPE_MINUTES / dim_exercise_types.expected_seconds
-- defaults.
--
-- Returns jsonb summary { exercise_types_updated, test_types_updated, ran_at }.
--
-- Replaces the Python scaffold in services/study_plan_service.py
-- (_refresh_exercise_time_estimates), which now becomes a thin RPC call.
--
-- See wiki/features/practice-engine.tech.md section "Time accounting" and
-- wiki/features/study-plans.tech.md section "Cron jobs".
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.refresh_practice_time_estimates()
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
   SET search_path = public, pg_temp AS $$
DECLARE
    v_ex_updated     int := 0;
    v_test_updated   int := 0;
    v_window_start   timestamptz := NOW() - INTERVAL '30 days';
    v_min_samples    constant int := 30;
BEGIN
    -- ----- Exercise types: from exercise_attempts.time_taken_ms ------------
    WITH src AS (
        SELECT exercise_type,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY time_taken_ms)
                 / 1000.0 AS p50,
               COUNT(*)   AS n
        FROM public.exercise_attempts
        WHERE time_taken_ms IS NOT NULL
          AND time_taken_ms > 0
          AND created_at >= v_window_start
        GROUP BY exercise_type
        HAVING COUNT(*) >= v_min_samples
    ),
    upd AS (
        UPDATE public.dim_exercise_types det
           SET expected_seconds_p50 = src.p50
          FROM src
         WHERE det.type_code = src.exercise_type
        RETURNING det.type_code
    )
    SELECT COUNT(*) INTO v_ex_updated FROM upd;

    -- ----- Test types: from test_attempts.duration_ms ----------------------
    WITH src AS (
        SELECT ta.test_type_id,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY ta.duration_ms)
                 / 60000.0 AS p50_minutes,
               COUNT(*)    AS n
        FROM public.test_attempts ta
        WHERE ta.duration_ms IS NOT NULL
          AND ta.duration_ms > 0
          AND ta.created_at >= v_window_start
        GROUP BY ta.test_type_id
        HAVING COUNT(*) >= v_min_samples
    ),
    upd AS (
        UPDATE public.dim_test_types dtt
           SET expected_minutes_p50 = ROUND(src.p50_minutes, 1)
          FROM src
         WHERE dtt.id = src.test_type_id
        RETURNING dtt.id
    )
    SELECT COUNT(*) INTO v_test_updated FROM upd;

    RETURN jsonb_build_object(
        'exercise_types_updated', v_ex_updated,
        'test_types_updated',     v_test_updated,
        'window_start',           v_window_start,
        'min_samples',            v_min_samples,
        'ran_at',                 NOW()
    );
END $$;

COMMENT ON FUNCTION public.refresh_practice_time_estimates IS
    'Nightly refresh of dim_exercise_types.expected_seconds_p50 and '
    'dim_test_types.expected_minutes_p50 from observed durations over the '
    'last 30 days, ≥30 samples per type. Called by '
    '_refresh_exercise_time_estimates in services/study_plan_service.py.';

COMMIT;
