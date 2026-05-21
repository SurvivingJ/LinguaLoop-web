-- ============================================================================
-- Phase 12 — Practice Engine merger — get_practice_session RPC
-- Date: 2026-05-21
--
-- Unified Practice surface. Replaces the dual entry points
-- get_exercise_session and get_ladder_session with a single mode-dispatched
-- RPC. See wiki/features/practice-engine.tech.md.
--
-- Modes:
--   acquisition — word-anchored loop. For each top-priority ladder word,
--                 drill K items (one per ring's required family, top-ranked
--                 by unified score within the family). Emit gate / stress
--                 markers inline when word_state is 'gated' / 'pre_mastery';
--                 the route handler dispatches the battery via existing
--                 /api/vocab-dojo/gate and /stress-test endpoints.
--   maintenance — batch-anchored. Pool = FSRS due ≤ +7d OR BKT-decay-flagged.
--                 LIMIT 200 candidates pre-ranked by urgency proxy, then
--                 ranked by unified score. If pool empties before time-up,
--                 falls through to acquisition for the remainder.
--   auto        — dispatch: maintenance if (due_today + decayed) ≥
--                 active_ladder_words, else acquisition.
--
-- V1 candidate pools require exercises.word_sense_id IS NOT NULL (ADR-012).
--
-- Returns jsonb:
--   { session_id, mode_requested, mode_resolved, target_minutes,
--     elapsed_seconds, items: [...], no_content_reason: text | null }
--
-- Each item:
--   { exercise_id, sense_id, exercise_type, family, content, ladder_level,
--     p_known, expected_seconds, mode, is_gate_marker?, gate_name?,
--     is_stress_test_marker? }
--
-- Errors (returned as { error, code }):
--   E_LANG   — language_not_active
--   E_MODE   — invalid_mode
--   E_RANGE  — target_minutes_out_of_range
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Helper: ladder_compute_priority — exposes the existing get_ladder_session
-- priority formula as a callable expression for use across multiple RPCs.
-- Mirrors the CTE in get_ladder_session verbatim (see phase8_momentum_bands).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.ladder_compute_priority(
    p_current_ring     integer,
    p_word_state       text,
    p_family_confidence jsonb,
    p_review_due_at    timestamptz,
    p_last_exercised_family text
) RETURNS numeric LANGUAGE sql IMMUTABLE AS $$
    WITH s AS (
        SELECT
            LEAST(7, GREATEST(0,
                EXTRACT(DAY FROM now() - COALESCE(p_review_due_at, now()))
            )) / 7.0 AS overdue_score,
            GREATEST(0,
                CASE p_current_ring
                    WHEN 1 THEN 0.50
                    WHEN 2 THEN 0.50
                    WHEN 3 THEN 0.65
                    ELSE 0.72
                END
                - LEAST(
                    COALESCE((p_family_confidence->>'form_recognition')::numeric, 0.10),
                    COALESCE((p_family_confidence->>'meaning_recall')::numeric, 0.10),
                    COALESCE((p_family_confidence->>'form_production')::numeric, 0.10),
                    COALESCE((p_family_confidence->>'collocation')::numeric, 0.10),
                    COALESCE((p_family_confidence->>'semantic_discrimination')::numeric, 0.10)
                )
            ) AS weakness_score,
            CASE WHEN p_word_state = 'gated'      THEN 1.0 ELSE 0.0 END AS gate_urgency,
            CASE WHEN p_last_exercised_family IS NULL THEN 0.5 ELSE 0.0 END AS novelty_score,
            CASE WHEN p_word_state = 'relearning' THEN 1.0 ELSE 0.0 END AS relapse_score
    )
    SELECT 0.35*overdue_score + 0.25*weakness_score + 0.20*gate_urgency
         + 0.10*novelty_score + 0.10*relapse_score
    FROM s
$$;

COMMENT ON FUNCTION public.ladder_compute_priority IS
    'Standalone form of the get_ladder_session priority formula. Used by '
    'get_practice_session to rank candidate words in Acquisition mode and '
    'to populate the ladder_priority term of the unified score.';

-- ---------------------------------------------------------------------------
-- Main entry point
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.get_practice_session(
    p_user_id        uuid,
    p_language_id    smallint,
    p_mode           text     DEFAULT 'auto',
    p_target_minutes smallint DEFAULT 15,
    p_user_theta     numeric  DEFAULT NULL
) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_mode            text;
    v_theta           numeric;
    v_weights         jsonb;
    v_alpha           numeric;
    v_beta            numeric;
    v_gamma           numeric;
    v_delta           numeric;
    v_target_seconds  integer;
    v_elapsed_seconds integer := 0;
    v_items           jsonb := '[]'::jsonb;
    v_no_content      text   := NULL;
    v_session_id      uuid   := gen_random_uuid();
    v_due_today       integer;
    v_decayed_count   integer;
    v_active_ladder   integer;
    v_today           date   := CURRENT_DATE;
    v_eligible_count  integer;
    v_word            RECORD;
    v_item            RECORD;
    v_fam             text;
    v_active_levels   integer[] := ARRAY[1,2,3,4,5,6,7,8,9];
BEGIN
    -- =============================================================
    -- 1. Validate inputs
    -- =============================================================
    IF NOT EXISTS (
        SELECT 1 FROM public.dim_languages
        WHERE id = p_language_id AND is_active
    ) THEN
        RETURN jsonb_build_object('error','language_not_active','code','E_LANG');
    END IF;

    IF p_mode NOT IN ('acquisition','maintenance','auto') THEN
        RETURN jsonb_build_object('error','invalid_mode','code','E_MODE');
    END IF;

    IF p_target_minutes IS NULL OR p_target_minutes < 1 OR p_target_minutes > 180 THEN
        RETURN jsonb_build_object('error','target_minutes_out_of_range','code','E_RANGE');
    END IF;

    v_target_seconds := p_target_minutes * 60;

    -- =============================================================
    -- 2. Resolve mode (auto dispatch)
    -- =============================================================
    IF p_mode = 'auto' THEN
        SELECT COUNT(*) INTO v_due_today
        FROM public.user_flashcards fc
        WHERE fc.user_id = p_user_id
          AND fc.language_id = p_language_id
          AND fc.due_date <= v_today;

        SELECT COUNT(*) INTO v_decayed_count
        FROM public.user_vocabulary_knowledge uvk
        LEFT JOIN public.user_flashcards fc
            ON fc.user_id = uvk.user_id AND fc.sense_id = uvk.sense_id
        WHERE uvk.user_id = p_user_id
          AND uvk.language_id = p_language_id
          AND public.bkt_effective_p_known(
                uvk.p_known, uvk.last_evidence_at,
                fc.stability, uvk.evidence_count
              ) < uvk.p_known - 0.05;

        SELECT COUNT(*) INTO v_active_ladder
        FROM public.user_word_ladder uwl
        WHERE uwl.user_id = p_user_id
          AND uwl.word_state IN ('active','gated','pre_mastery','relearning');

        v_mode := CASE
            WHEN (v_due_today + v_decayed_count) >= v_active_ladder
                 AND (v_due_today + v_decayed_count) > 0
                THEN 'maintenance'
            ELSE 'acquisition'
        END;
    ELSE
        v_mode := p_mode;
    END IF;

    -- =============================================================
    -- 3. Resolve theta
    -- =============================================================
    v_theta := COALESCE(p_user_theta,
                        public.irt_compute_user_theta(p_user_id, p_language_id),
                        0.0);

    -- =============================================================
    -- 4. Load mode weights
    -- =============================================================
    SELECT default_weights INTO v_weights
    FROM public.dim_practice_modes
    WHERE name = v_mode AND is_active;

    IF v_weights IS NULL THEN
        -- Should never happen given validation above, but defensive.
        RETURN jsonb_build_object('error','invalid_mode_weights','code','E_WEIGHTS');
    END IF;

    v_alpha := (v_weights->>'alpha')::numeric;
    v_beta  := (v_weights->>'beta' )::numeric;
    v_gamma := (v_weights->>'gamma')::numeric;
    v_delta := (v_weights->>'delta')::numeric;

    -- =============================================================
    -- 5. Run mode loop
    -- =============================================================
    IF v_mode = 'maintenance' THEN
        -- ----- Maintenance candidate pool + ranking -----
        FOR v_item IN
            WITH due_or_decayed AS (
                SELECT DISTINCT
                    uvk.sense_id,
                    fc.stability,
                    fc.due_date,
                    uvk.p_known
                FROM public.user_vocabulary_knowledge uvk
                LEFT JOIN public.user_flashcards fc
                    ON fc.user_id = uvk.user_id AND fc.sense_id = uvk.sense_id
                WHERE uvk.user_id = p_user_id
                  AND uvk.language_id = p_language_id
                  AND (
                      (fc.due_date IS NOT NULL AND fc.due_date <= v_today + 7)
                      OR public.bkt_effective_p_known(
                            uvk.p_known, uvk.last_evidence_at,
                            fc.stability, uvk.evidence_count
                         ) < uvk.p_known - 0.05
                  )
            ),
            top_senses AS (
                SELECT *,
                    GREATEST(0, (v_today - due_date)::numeric
                              / NULLIF(stability, 0)) AS urg
                FROM due_or_decayed
                ORDER BY urg DESC NULLS LAST, sense_id
                LIMIT 200
            ),
            candidates AS (
                SELECT
                    e.id            AS exercise_id,
                    e.word_sense_id AS sense_id,
                    e.exercise_type,
                    e.content,
                    e.ladder_level,
                    public.ladder_get_family(e.ladder_level) AS family,
                    COALESCE(det.expected_seconds_p50::int,
                             det.expected_seconds, 45) AS expected_seconds,
                    e.irt_discrimination,
                    e.irt_difficulty,
                    s.stability,
                    s.due_date,
                    s.p_known,
                    uwl.family_confidence,
                    uwl.current_ring,
                    uwl.word_state,
                    uwl.review_due_at,
                    uwl.last_exercised_family,
                    public.practice_unified_score(
                        e.irt_discrimination, e.irt_difficulty, v_theta,
                        s.p_known,
                        s.due_date, s.stability, v_today,
                        CASE WHEN uwl.sense_id IS NULL THEN 0
                             ELSE public.ladder_compute_priority(
                                uwl.current_ring, uwl.word_state,
                                uwl.family_confidence, uwl.review_due_at,
                                uwl.last_exercised_family
                             )
                        END,
                        v_alpha, v_beta, v_gamma, v_delta
                    ) AS score
                FROM top_senses s
                JOIN public.exercises e
                    ON e.word_sense_id = s.sense_id
                   AND e.language_id   = p_language_id
                   AND e.is_active
                   AND e.word_sense_id IS NOT NULL
                LEFT JOIN public.dim_exercise_types det
                    ON det.type_code = e.exercise_type
                LEFT JOIN public.user_word_ladder uwl
                    ON uwl.user_id = p_user_id AND uwl.sense_id = e.word_sense_id
            )
            SELECT * FROM candidates
            ORDER BY score DESC
            LIMIT 60                    -- enough to cover 60×30s = 30 min budget
        LOOP
            EXIT WHEN v_elapsed_seconds >= v_target_seconds;
            v_items := v_items || jsonb_build_object(
                'exercise_id',      v_item.exercise_id,
                'sense_id',         v_item.sense_id,
                'exercise_type',    v_item.exercise_type,
                'family',           v_item.family,
                'content',          v_item.content,
                'ladder_level',     v_item.ladder_level,
                'p_known',          v_item.p_known,
                'expected_seconds', v_item.expected_seconds,
                'mode',             'maintenance'
            );
            v_elapsed_seconds := v_elapsed_seconds + v_item.expected_seconds;
        END LOOP;

        -- ----- Fall-through: if Maintenance dry, continue in Acquisition -----
        IF v_elapsed_seconds < v_target_seconds AND jsonb_array_length(v_items) < 60 THEN
            -- Mark fall-through; continue inline with Acquisition logic
            v_mode := 'acquisition';
            -- Reload weights to Acquisition values for the fall-through items
            SELECT default_weights INTO v_weights
            FROM public.dim_practice_modes WHERE name = 'acquisition';
            v_alpha := (v_weights->>'alpha')::numeric;
            v_beta  := (v_weights->>'beta' )::numeric;
            v_gamma := (v_weights->>'gamma')::numeric;
            v_delta := (v_weights->>'delta')::numeric;
        END IF;
    END IF;

    -- =============================================================
    -- Acquisition path (also runs as fall-through from Maintenance)
    -- =============================================================
    IF v_mode = 'acquisition' AND v_elapsed_seconds < v_target_seconds THEN
        -- Count eligible words for the no-content check
        SELECT COUNT(*) INTO v_eligible_count
        FROM public.user_word_ladder uwl
        WHERE uwl.user_id = p_user_id
          AND uwl.word_state IN ('new','active','gated','pre_mastery','relearning')
          AND COALESCE(uwl.review_due_at, '1970-01-01'::timestamptz) <= now();

        IF v_eligible_count = 0 THEN
            -- Caller (Python service) is expected to auto-subscribe from packs
            -- per R4.9 before calling, but if it didn't, we return a marker so
            -- the FE can show the "select a pack" nudge.
            IF jsonb_array_length(v_items) = 0 THEN
                v_no_content := 'no_eligible_words';
            END IF;
        ELSE
            -- Word-anchored loop: top 50 by priority
            FOR v_word IN
                SELECT
                    uwl.sense_id,
                    uwl.current_ring,
                    uwl.word_state,
                    uwl.family_confidence,
                    uwl.review_due_at,
                    uwl.last_exercised_family,
                    uwl.active_levels,
                    public.ladder_compute_priority(
                        uwl.current_ring, uwl.word_state,
                        uwl.family_confidence, uwl.review_due_at,
                        uwl.last_exercised_family
                    ) AS priority
                FROM public.user_word_ladder uwl
                WHERE uwl.user_id = p_user_id
                  AND uwl.word_state IN ('new','active','gated','pre_mastery','relearning')
                  AND COALESCE(uwl.review_due_at, '1970-01-01'::timestamptz) <= now()
                  AND EXISTS (
                    SELECT 1 FROM public.exercises e
                    WHERE e.word_sense_id = uwl.sense_id
                      AND e.language_id = p_language_id
                      AND e.is_active
                      AND e.ladder_level IS NOT NULL
                  )
                ORDER BY priority DESC
                LIMIT 50
            LOOP
                EXIT WHEN v_elapsed_seconds >= v_target_seconds;

                -- For each ring-required family, pick the top-scored item
                FOREACH v_fam IN ARRAY
                    public.ladder_ring_families(
                        v_word.current_ring,
                        COALESCE(v_word.active_levels, v_active_levels)
                    )
                LOOP
                    EXIT WHEN v_elapsed_seconds >= v_target_seconds;

                    SELECT
                        e.id        AS exercise_id,
                        e.exercise_type,
                        e.content,
                        e.ladder_level,
                        public.ladder_get_family(e.ladder_level) AS family,
                        COALESCE(det.expected_seconds_p50::int,
                                 det.expected_seconds, 45) AS expected_seconds,
                        uvk.p_known
                    INTO v_item
                    FROM public.exercises e
                    LEFT JOIN public.dim_exercise_types det
                        ON det.type_code = e.exercise_type
                    LEFT JOIN public.user_vocabulary_knowledge uvk
                        ON uvk.user_id = p_user_id AND uvk.sense_id = e.word_sense_id
                    LEFT JOIN public.user_flashcards fc
                        ON fc.user_id = p_user_id AND fc.sense_id = e.word_sense_id
                    WHERE e.word_sense_id = v_word.sense_id
                      AND e.language_id   = p_language_id
                      AND e.is_active
                      AND e.ladder_level IS NOT NULL
                      AND public.ladder_get_family(e.ladder_level) = v_fam
                      -- Anti-repetition: not seen today
                      AND NOT EXISTS (
                        SELECT 1 FROM public.user_exercise_history ueh
                        WHERE ueh.user_id = p_user_id
                          AND ueh.exercise_id = e.id
                          AND ueh.session_date = v_today
                      )
                    ORDER BY public.practice_unified_score(
                        e.irt_discrimination, e.irt_difficulty, v_theta,
                        uvk.p_known,
                        fc.due_date, fc.stability, v_today,
                        v_word.priority,
                        v_alpha, v_beta, v_gamma, v_delta
                    ) DESC,
                    RANDOM()
                    LIMIT 1;

                    IF FOUND THEN
                        v_items := v_items || jsonb_build_object(
                            'exercise_id',      v_item.exercise_id,
                            'sense_id',         v_word.sense_id,
                            'exercise_type',    v_item.exercise_type,
                            'family',           v_item.family,
                            'content',          v_item.content,
                            'ladder_level',     v_item.ladder_level,
                            'p_known',          v_item.p_known,
                            'expected_seconds', v_item.expected_seconds,
                            'mode',             'acquisition'
                        );
                        v_elapsed_seconds := v_elapsed_seconds + v_item.expected_seconds;
                    END IF;
                END LOOP;

                -- Gate marker: word is gated → caller dispatches via
                -- /api/vocab-dojo/gate with the appropriate gate_name.
                IF v_word.word_state = 'gated'
                   AND v_elapsed_seconds < v_target_seconds THEN
                    v_items := v_items || jsonb_build_object(
                        'is_gate_marker',  true,
                        'gate_name',
                            CASE WHEN v_word.current_ring = 2 THEN 'gate_a'
                                 WHEN v_word.current_ring = 3 THEN 'gate_b'
                                 ELSE 'unknown' END,
                        'sense_id',        v_word.sense_id,
                        'expected_seconds', 180,
                        'mode',            'acquisition'
                    );
                    v_elapsed_seconds := v_elapsed_seconds + 180;
                END IF;

                -- Stress-test marker: word is in pre_mastery → caller
                -- dispatches via /api/vocab-dojo/stress-test.
                IF v_word.word_state = 'pre_mastery'
                   AND v_elapsed_seconds < v_target_seconds THEN
                    v_items := v_items || jsonb_build_object(
                        'is_stress_test_marker', true,
                        'sense_id',              v_word.sense_id,
                        'expected_seconds',      420,
                        'mode',                  'acquisition'
                    );
                    v_elapsed_seconds := v_elapsed_seconds + 420;
                END IF;
            END LOOP;
        END IF;
    END IF;

    -- =============================================================
    -- 6. Assemble final response
    -- =============================================================
    IF jsonb_array_length(v_items) = 0 AND v_no_content IS NULL THEN
        v_no_content := 'all_complete';
    END IF;

    RETURN jsonb_build_object(
        'session_id',       v_session_id,
        'mode_requested',   p_mode,
        'mode_resolved',    v_mode,
        'target_minutes',   p_target_minutes,
        'elapsed_seconds',  v_elapsed_seconds,
        'items',            v_items,
        'no_content_reason', v_no_content
    );
END $$;

COMMENT ON FUNCTION public.get_practice_session IS
    'Unified Practice surface. Mode-dispatched, time-budgeted, unified-score-'
    'ranked. Maintenance falls through to Acquisition on dry pool. '
    'Acquisition emits is_gate_marker / is_stress_test_marker rows for the '
    'route handler to materialise via existing battery endpoints. Returns '
    'jsonb with items array and no_content_reason flag.';

COMMIT;
