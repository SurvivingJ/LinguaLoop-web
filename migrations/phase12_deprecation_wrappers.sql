-- ============================================================================
-- Phase 12 — Practice Engine merger — deprecation wrappers
-- Date: 2026-05-21
--
-- Both legacy RPCs (get_exercise_session, get_ladder_session) are replaced
-- by thin wrappers around get_practice_session, preserving their original
-- TABLE row-shape so existing callers keep working for one release.
--
-- Both wrappers emit RAISE WARNING 'DEPRECATED' once per call so pg_log
-- captures any caller that hasn't migrated. Scheduled for removal in the
-- release after Study Plans rollout (TASK-220).
--
-- See wiki/features/practice-engine.tech.md section "Deprecation wrappers".
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- get_exercise_session: maps the legacy session_size to minutes (× 0.6 per
-- the spec — empirical conversion) and dispatches via 'auto' mode. The
-- returned TABLE shape is preserved; columns the new RPC doesn't populate
-- (out_complexity_tier, out_phase, out_slot_type) are NULL.
-- ---------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.get_exercise_session(uuid, smallint, integer, numeric);

CREATE OR REPLACE FUNCTION public.get_exercise_session(
    p_user_id        uuid,
    p_language_id    smallint,
    p_session_size   integer DEFAULT 20,
    p_user_theta     numeric DEFAULT 0.0
)
RETURNS TABLE (
    out_exercise_id     uuid,
    out_sense_id        integer,
    out_exercise_type   text,
    out_content         jsonb,
    out_complexity_tier text,
    out_phase           text,
    out_slot_type       text,
    out_priority        numeric
) LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_minutes smallint;
    v_payload jsonb;
BEGIN
    RAISE WARNING 'DEPRECATED: get_exercise_session — call get_practice_session(p_mode=auto, ...) instead';

    v_minutes := GREATEST(1, LEAST(180, (p_session_size * 0.6)::smallint));

    v_payload := public.get_practice_session(
        p_user_id, p_language_id, 'auto', v_minutes,
        NULLIF(p_user_theta, 0.0)
    );

    -- Bail early on error payload
    IF v_payload ? 'error' THEN
        RETURN;  -- empty rowset; callers can detect via 0-row result
    END IF;

    RETURN QUERY
    SELECT
        (item->>'exercise_id')::uuid,
        (item->>'sense_id')::integer,
        item->>'exercise_type',
        item->'content',
        NULL::text,                  -- out_complexity_tier (unused post-merger)
        NULL::text,                  -- out_phase           (unused post-merger)
        NULL::text,                  -- out_slot_type       (unused post-merger)
        COALESCE((item->'score_breakdown'->>'unified')::numeric, 0)
    FROM jsonb_array_elements(v_payload->'items') AS item
    WHERE NOT COALESCE((item->>'is_gate_marker')::boolean, false)
      AND NOT COALESCE((item->>'is_stress_test_marker')::boolean, false);
END $$;

COMMENT ON FUNCTION public.get_exercise_session(uuid, smallint, integer, numeric) IS
    'DEPRECATED 2026-05-21. Thin wrapper around get_practice_session(auto). '
    'Scheduled for removal in TASK-220 (T+30 days post Study Plans flip).';

-- ---------------------------------------------------------------------------
-- get_ladder_session: dispatches via 'acquisition' mode. Time conversion is
-- count × 0.5 min (acquisition items are ~30s with batteries inline making
-- avg ~30s usable). Returns the wide TABLE shape the legacy callers expect,
-- including is_gate / is_stress_test markers — which are now derived from
-- the new RPC's is_*_marker rows.
-- ---------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.get_ladder_session(uuid, smallint, integer);

CREATE OR REPLACE FUNCTION public.get_ladder_session(
    p_user_id     uuid,
    p_language_id smallint,
    p_count       integer DEFAULT 20
)
RETURNS TABLE (
    out_sense_id        integer,
    out_exercise_id     uuid,
    out_exercise_type   text,
    out_content         jsonb,
    out_ladder_level    integer,
    out_family          text,
    out_p_known         numeric,
    out_word_state      text,
    out_lemma           text,
    out_definition      text,
    out_pronunciation   text,
    out_variant         text,
    out_is_gate         boolean,
    out_is_stress_test  boolean,
    out_priority        numeric
) LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_minutes smallint;
    v_payload jsonb;
BEGIN
    RAISE WARNING 'DEPRECATED: get_ladder_session — call get_practice_session(p_mode=acquisition, ...) instead';

    v_minutes := GREATEST(1, LEAST(180, (p_count * 0.5)::smallint));

    v_payload := public.get_practice_session(
        p_user_id, p_language_id, 'acquisition', v_minutes, NULL
    );

    IF v_payload ? 'error' THEN
        RETURN;
    END IF;

    RETURN QUERY
    SELECT
        (item->>'sense_id')::integer,
        (item->>'exercise_id')::uuid,
        item->>'exercise_type',
        item->'content',
        (item->>'ladder_level')::integer,
        item->>'family',
        (item->>'p_known')::numeric,
        -- word_state isn't carried in the new payload; derive via lookup
        (SELECT word_state FROM public.user_word_ladder
         WHERE user_id = p_user_id
           AND sense_id = (item->>'sense_id')::integer),
        COALESCE(dv.lemma, ''),
        COALESCE(dws.definition, ''),
        COALESCE(dws.pronunciation, ''),
        COALESCE(item->>'variant', 'A'),
        COALESCE((item->>'is_gate_marker')::boolean, false),
        COALESCE((item->>'is_stress_test_marker')::boolean, false),
        0::numeric                   -- priority unused by callers post-merger
    FROM jsonb_array_elements(v_payload->'items') AS item
    LEFT JOIN public.dim_word_senses dws
        ON dws.id = (item->>'sense_id')::integer
    LEFT JOIN public.dim_vocabulary dv
        ON dv.id = dws.vocab_id;
END $$;

COMMENT ON FUNCTION public.get_ladder_session(uuid, smallint, integer) IS
    'DEPRECATED 2026-05-21. Thin wrapper around get_practice_session(acquisition). '
    'Gate/stress markers from the new RPC are surfaced via out_is_gate / '
    'out_is_stress_test for backwards compatibility. Scheduled for removal '
    'in TASK-220 (T+30 days post Study Plans flip).';

COMMIT;
