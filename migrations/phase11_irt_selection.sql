-- ============================================================================
-- Phase 11: IRT-aware selection inside get_exercise_session
-- Date: 2026-05-12
-- Prerequisites:
--   phase9_get_exercise_session.sql          -- the baseline RPC body
--   add_irt_calibration_metadata.sql         -- irt_n_attempts + irt_calibrated_at
--                                               + irt_compute_user_theta()
--
-- Adds a per-exercise Gaussian weight centered on the learner's theta, so
-- that within a target family (or any sense bucket) we prefer items whose
-- fitted difficulty matches the learner. Falls back to a flat weight of
-- 1.0 for exercises that have not yet accumulated `min_attempts` first
-- attempts — newly-generated content stays selectable until enough data
-- arrives to fit it.
--
-- The IRT term is multiplied INTO the existing `type_weight`, so the phase
-- mix (A/B/C/D) is preserved. Tie-break stays random, so within an exact
-- weight-tie we still get variety.
--
-- The selection-side scale (sigma) is hard-coded at 1.0 logit. That's a
-- reasonable default — within a sigma the weight falls to ~0.6, within
-- 2 sigmas to ~0.13. Tighter than 1.0 collapses to "always the same item",
-- wider than 2.0 erases the targeting signal.
--
-- One new parameter: p_user_theta. If 0.0 (default), the Gaussian
-- collapses around 0.0 — which is the population-mean assumption and is
-- always safe.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_exercise_session(
    p_user_id      uuid,
    p_language_id  smallint,
    p_session_size integer DEFAULT 20,
    p_user_theta   numeric DEFAULT 0.0
)
RETURNS TABLE(
    out_exercise_id     uuid,
    out_sense_id        integer,
    out_exercise_type   text,
    out_content         jsonb,
    out_complexity_tier text,
    out_phase           text,
    out_slot_type       text,
    out_priority        numeric
)
LANGUAGE plpgsql
STABLE
AS $function$
DECLARE
    v_due_slots      integer := ROUND(p_session_size * 0.40)::integer;
    v_learning_slots integer := ROUND(p_session_size * 0.40)::integer;
    v_new_slots      integer := p_session_size - v_due_slots - v_learning_slots;
    v_ladder_cap     integer := LEAST(5, p_session_size);
    v_avg_p          numeric;
    v_tiers          text[];
    v_irt_sigma      numeric := 1.0;
    v_irt_min_n      integer := 20;
BEGIN
    SELECT COALESCE(AVG(p_known)::numeric, 0.30)
      INTO v_avg_p
      FROM user_vocabulary_knowledge
     WHERE user_id = p_user_id
       AND language_id = p_language_id;

    v_tiers := tier_window_for_p_known(v_avg_p);

    RETURN QUERY
    WITH
    recent_seen AS (
        SELECT DISTINCT exercise_id
          FROM user_exercise_history
         WHERE user_id = p_user_id
           AND language_id = p_language_id
           AND session_date >= CURRENT_DATE - INTERVAL '7 days'
    ),

    raw_senses AS (
        SELECT out_sense_id AS sense_id,
               out_effective_p_known::numeric AS p_known,
               out_bucket AS bucket
          FROM get_session_senses(
              p_user_id, p_language_id,
              v_due_slots * 3, v_learning_slots * 3, v_new_slots * 3
          )
    ),

    new_fallback AS (
        SELECT uf.sense_id,
               0.10::numeric AS p_known,
               'new'::text   AS bucket
          FROM user_flashcards uf
         WHERE uf.user_id = p_user_id
           AND uf.language_id = p_language_id
           AND uf.state = 'new'
           AND uf.sense_id NOT IN (SELECT sense_id FROM raw_senses)
         LIMIT v_new_slots
    ),

    all_senses AS (
        SELECT sense_id, p_known, bucket FROM raw_senses
        UNION ALL
        SELECT sense_id, p_known, bucket FROM new_fallback
    ),
    senses_deduped AS (
        SELECT sense_id, p_known, bucket FROM (
            SELECT sense_id, p_known, bucket,
                   ROW_NUMBER() OVER (
                       PARTITION BY sense_id
                       ORDER BY CASE bucket
                           WHEN 'due' THEN 1
                           WHEN 'learning' THEN 2
                           ELSE 3
                       END
                   ) AS bucket_rn
              FROM all_senses
        ) sub
        WHERE bucket_rn = 1
    ),

    ladder_picks AS (
        SELECT
            ls.out_exercise_id   AS exercise_id,
            ls.out_sense_id      AS sense_id,
            ls.out_exercise_type AS exercise_type,
            ls.out_content       AS content,
            NULL::text           AS complexity_tier,
            CASE
                WHEN ls.out_p_known < 0.30 THEN 'A'
                WHEN ls.out_p_known < 0.55 THEN 'B'
                WHEN ls.out_p_known < 0.80 THEN 'C'
                ELSE                            'D'
            END                  AS phase,
            'ladder'::text       AS slot_type,
            ls.out_priority + 1.0 AS priority
          FROM get_ladder_session(p_user_id, p_language_id, v_ladder_cap) ls
    ),

    -- One exercise per sense, ranked by (phase weight × IRT match)
    -- ORDER BY tie-broken with RANDOM(). The IRT term is 1.0 for any
    -- exercise that hasn't yet been calibrated, so newly-generated items
    -- stay selectable.
    sense_candidates AS (
        SELECT
            s.sense_id,
            s.bucket,
            CASE
                WHEN s.p_known < 0.30 THEN 'A'
                WHEN s.p_known < 0.55 THEN 'B'
                WHEN s.p_known < 0.80 THEN 'C'
                ELSE                       'D'
            END                       AS phase,
            e.id                      AS exercise_id,
            e.exercise_type,
            e.content,
            e.complexity_tier,
            exercise_type_phase_weight(
                e.exercise_type,
                CASE
                    WHEN s.p_known < 0.30 THEN 'A'
                    WHEN s.p_known < 0.55 THEN 'B'
                    WHEN s.p_known < 0.80 THEN 'C'
                    ELSE                       'D'
                END
            )
            * CASE
                WHEN e.irt_n_attempts >= v_irt_min_n
                    THEN EXP(
                        -0.5
                        * POWER((e.irt_difficulty - p_user_theta) / v_irt_sigma, 2)
                    )
                ELSE 1.0
              END                     AS type_weight
          FROM senses_deduped s
          JOIN exercises e
            ON e.word_sense_id = s.sense_id
           AND e.language_id   = p_language_id
           AND e.is_active     = TRUE
         WHERE e.id NOT IN (SELECT exercise_id FROM recent_seen)
           AND s.sense_id NOT IN (
               SELECT sense_id FROM ladder_picks WHERE sense_id IS NOT NULL
           )
           AND e.id NOT IN (
               SELECT exercise_id FROM ladder_picks WHERE exercise_id IS NOT NULL
           )
    ),

    ranked_sense_picks AS (
        SELECT *,
               ROW_NUMBER() OVER (
                   PARTITION BY sense_id
                   ORDER BY type_weight DESC, RANDOM()
               ) AS sense_rn
          FROM sense_candidates
    ),

    vocab_picks_capped AS (
        SELECT *,
               ROW_NUMBER() OVER (
                   PARTITION BY bucket
                   ORDER BY type_weight DESC, RANDOM()
               ) AS bucket_rn
          FROM ranked_sense_picks
         WHERE sense_rn = 1
    ),

    vocab_picks AS (
        SELECT
            exercise_id,
            sense_id,
            exercise_type,
            content,
            complexity_tier,
            phase,
            CASE bucket
                WHEN 'due'      THEN 'due_review'
                WHEN 'learning' THEN 'active_learning'
                WHEN 'new'      THEN 'new_word'
                ELSE                 'active_learning'
            END               AS slot_type,
            (CASE bucket
                WHEN 'due'      THEN 0.9
                WHEN 'learning' THEN 0.6
                WHEN 'new'      THEN 0.3
                ELSE                 0.0
            END
            + type_weight * 0.1) AS priority
          FROM vocab_picks_capped
         WHERE (bucket = 'due'      AND bucket_rn <= v_due_slots)
            OR (bucket = 'learning' AND bucket_rn <= v_learning_slots)
            OR (bucket = 'new'      AND bucket_rn <= v_new_slots)
    ),

    supplementary_picks AS (
        SELECT
            e.id                   AS exercise_id,
            NULL::integer          AS sense_id,
            e.exercise_type,
            e.content,
            e.complexity_tier,
            tier_to_phase(e.complexity_tier) AS phase,
            'supplementary'::text  AS slot_type,
            0.1::numeric           AS priority
          FROM exercises e
         WHERE e.language_id     = p_language_id
           AND e.is_active       = TRUE
           AND e.word_sense_id   IS NULL
           AND e.complexity_tier = ANY(v_tiers)
           AND e.id NOT IN (SELECT exercise_id FROM recent_seen)
           AND e.id NOT IN (
               SELECT exercise_id FROM ladder_picks WHERE exercise_id IS NOT NULL
               UNION ALL
               SELECT exercise_id FROM vocab_picks  WHERE exercise_id IS NOT NULL
           )
         ORDER BY RANDOM()
         LIMIT GREATEST(
             0,
             p_session_size
                - (SELECT COUNT(*) FROM ladder_picks WHERE exercise_id IS NOT NULL)
                - (SELECT COUNT(*) FROM vocab_picks)
         )
    ),

    all_picks AS (
        SELECT exercise_id, sense_id, exercise_type, content, complexity_tier,
               phase, slot_type, priority
          FROM ladder_picks
         WHERE exercise_id IS NOT NULL
        UNION ALL
        SELECT exercise_id, sense_id, exercise_type, content, complexity_tier,
               phase, slot_type, priority
          FROM vocab_picks
         WHERE exercise_id IS NOT NULL
        UNION ALL
        SELECT exercise_id, sense_id, exercise_type, content, complexity_tier,
               phase, slot_type, priority
          FROM supplementary_picks
    )

    SELECT exercise_id, sense_id, exercise_type, content, complexity_tier,
           phase, slot_type, priority
      FROM all_picks
     ORDER BY priority DESC, RANDOM()
     LIMIT p_session_size;
END;
$function$;
