-- ============================================================================
-- Phase 13 — Study Plans — apply_attempt_timing_and_progress RPC
-- Date: 2026-05-21
--
-- Post-submission hook called by the route handler right after
-- process_test_submission (or its dictation/pinyin/pitch-accent variants)
-- returns. Does two things atomically:
--
--   1. UPDATEs test_attempts(started_at, duration_ms) from FE-supplied
--      timestamps. duration_ms is server-computed = (finished − started)·1000,
--      validated to (0, 3_600_000) by the test_attempts CHECK constraint.
--
--   2. Calls record_session_progress(..., 'test', skill, 1, duration_minutes)
--      to bump the weekly_plan_states test counter for the right skill.
--
-- Why a hook RPC instead of modifying process_test_submission directly:
--   The submission RPCs are ~250 lines each, entangled with ELO + idempotency
--   + retry-slot factor + furigana. Adding two params would require dropping
--   and recreating each — 4 large migrations. Timing capture is a pure
--   side-effect with no influence on ELO calculation, so isolating it in a
--   hook RPC is cleaner. See [[features/study-plans.tech]] section "Modified
--   existing RPCs".
--
-- Idempotency:
--   - The UPDATE is naturally idempotent (same finished_at − started_at
--     always produces the same duration_ms).
--   - record_session_progress already has its own idempotency via the
--     attempt_id ↔ session_progress_log mapping.
--
-- Tolerant of NULL inputs:
--   - If FE doesn't supply timestamps, the UPDATE is skipped.
--   - If attempt_id doesn't resolve to a test_attempts row, returns
--     {ok: false, reason: 'not_found'}.
--
-- Returns jsonb:
--   { ok: bool, duration_ms: int|null, progress_recorded: bool,
--     skill: text, reason?: text }
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.apply_attempt_timing_and_progress(
    p_attempt_id   uuid,
    p_started_at   timestamptz DEFAULT NULL,
    p_finished_at  timestamptz DEFAULT NULL
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
   SET search_path = public, pg_temp AS $$
DECLARE
    v_attempt        public.test_attempts%ROWTYPE;
    v_duration_ms    int := NULL;
    v_skill          text;
    v_progress_ok    boolean := false;
    v_minutes        int;
BEGIN
    SELECT * INTO v_attempt FROM public.test_attempts WHERE id = p_attempt_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'ok', false, 'reason', 'attempt_not_found',
            'attempt_id', p_attempt_id
        );
    END IF;

    ---------------------------------------------------------------------
    -- 1. Update timing (if FE supplied valid timestamps)
    ---------------------------------------------------------------------
    IF p_started_at IS NOT NULL AND p_finished_at IS NOT NULL THEN
        IF p_finished_at < p_started_at THEN
            -- Clock skew or FE bug — don't poison the data; log and skip
            RAISE WARNING
                '[apply_attempt_timing_and_progress] finished_at < started_at for attempt=%; skipping timing',
                p_attempt_id;
        ELSE
            v_duration_ms := EXTRACT(EPOCH FROM (p_finished_at - p_started_at)) * 1000;
            -- Defensive cap so the CHECK on test_attempts.duration_ms passes.
            -- The CHECK rejects > 3_600_000 (1 hour); we cap silently so a
            -- learner who left the tab open doesn't break the submit flow.
            IF v_duration_ms <= 0 OR v_duration_ms >= 3600000 THEN
                v_duration_ms := NULL;
            ELSE
                UPDATE public.test_attempts
                   SET started_at  = p_started_at,
                       duration_ms = v_duration_ms
                 WHERE id = p_attempt_id;
            END IF;
        END IF;
    END IF;

    ---------------------------------------------------------------------
    -- 2. Bump weekly_plan_states counter via record_session_progress.
    -- Skill is derived from test_attempts.test_type_id → dim_test_types.type_code.
    -- record_session_progress itself returns false on duplicate attempt_id;
    -- we propagate that as progress_recorded=false (not an error).
    ---------------------------------------------------------------------
    SELECT dtt.type_code INTO v_skill
    FROM public.dim_test_types dtt
    WHERE dtt.id = v_attempt.test_type_id;

    IF v_skill IS NOT NULL THEN
        v_minutes := COALESCE(
            ROUND(v_duration_ms::numeric / 60000)::int,
            0
        );
        v_progress_ok := public.record_session_progress(
            p_user_id       => v_attempt.user_id,
            p_language_id   => v_attempt.language_id,
            p_attempt_id    => p_attempt_id,
            p_kind          => 'test',
            p_skill         => v_skill,
            p_delta_count   => 1,
            p_delta_minutes => v_minutes
        );
    END IF;

    RETURN jsonb_build_object(
        'ok',                true,
        'duration_ms',       v_duration_ms,
        'skill',             v_skill,
        'progress_recorded', v_progress_ok
    );
END $$;

COMMENT ON FUNCTION public.apply_attempt_timing_and_progress IS
    'Post-submission hook. UPDATEs test_attempts(started_at, duration_ms) '
    'and calls record_session_progress for Study Plan counter updates. '
    'Tolerant of NULL timestamps (skip timing) and clock skew (skip + warn). '
    'Caps duration_ms to (0, 3_600_000) silently before UPDATE.';

COMMIT;
