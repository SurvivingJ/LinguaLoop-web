-- ============================================================================
-- Phase 9: Daily Mixed Exercise Session — SQL Session Builder
-- Date: 2026-05-12
-- Prerequisites:
--   phase4_schema_evolution.sql  -- user_exercise_history (anti-repetition)
--   phase7_bkt_improvements.sql  -- get_session_senses (due/learning/new)
--   phase8_momentum_bands.sql    -- get_ladder_session (ladder picks)
--
-- Replaces the Python 6-bucket builder in
--   services/exercise_session_service.py::ExerciseSessionService._compute_session
-- with a single SQL RPC. Bucket 5 (ladder content) delegates to
-- get_ladder_session — single source of truth for ladder selection. Bucket 6
-- (virtual jumbled sentences) stays in Python because it depends on
-- language-specific tokenisation (LanguageProcessor.split_sentences/tokenize).
--
-- Sections:
--   9.1  Helper: exercise_type_phase_weight  -- mirrors PHASE_MAP weighting
--   9.2  Helper: tier_window_for_p_known     -- complexity tier window
--   9.3  Helper: tier_to_phase               -- mirrors TIER_TO_PHASE
--   9.4  Core:   get_exercise_session        -- the daily-session RPC
-- ============================================================================


-- ============================================================================
-- 9.1 Helper: exercise_type → phase weight
-- ============================================================================
-- Mirrors services/exercise_generation/config.py::PHASE_MAP and the
-- weighting rule in services/exercise_session_service.py::_get_eligible_types_weighted:
--   Phase A: 100% A types
--   Phase B: 70% B types + 30% A types (fallback)
--   Phase C: 70% C types + 30% B types
--   Phase D: 70% D types + 30% C types
-- Weight = share / |types_in_share|, so each individual type weight is the
-- per-type probability mass in a weighted-random choice.

CREATE OR REPLACE FUNCTION public.exercise_type_phase_weight(
    p_exercise_type text,
    p_phase text  -- 'A' | 'B' | 'C' | 'D'
)
RETURNS numeric
LANGUAGE sql IMMUTABLE
AS $$
    SELECT CASE
        -- Phase A types (3 types)
        WHEN p_exercise_type IN ('text_flashcard', 'listening_flashcard', 'cloze_completion')
            THEN CASE p_phase
                WHEN 'A' THEN 1.0  / 3.0
                WHEN 'B' THEN 0.30 / 3.0
                ELSE 0.0
            END

        -- Phase B types (7 types)
        WHEN p_exercise_type IN (
            'jumbled_sentence', 'spot_incorrect_sentence', 'spot_incorrect_part',
            'tl_nl_translation', 'nl_tl_translation',
            'style_sentence_completion', 'style_transition_fill'
        )
            THEN CASE p_phase
                WHEN 'B' THEN 0.70 / 7.0
                WHEN 'C' THEN 0.30 / 7.0
                ELSE 0.0
            END

        -- Phase C types (7 types)
        WHEN p_exercise_type IN (
            'semantic_discrimination', 'collocation_gap_fill', 'collocation_repair',
            'odd_collocation_out', 'odd_one_out',
            'style_pattern_match', 'style_voice_transform'
        )
            THEN CASE p_phase
                WHEN 'C' THEN 0.70 / 7.0
                WHEN 'D' THEN 0.30 / 7.0
                ELSE 0.0
            END

        -- Phase D types (4 types)
        WHEN p_exercise_type IN (
            'verb_noun_match', 'context_spectrum', 'timed_speed_round', 'style_imitation'
        )
            THEN CASE p_phase
                WHEN 'D' THEN 0.70 / 4.0
                ELSE 0.0
            END

        -- Any other type (e.g. phonetic_recognition, morphology_slot for ladder-only
        -- types when picked outside ladder context) gets a tiny floor weight so it
        -- can still be selected when no weighted-type exercise exists. Mirrors the
        -- Python fallback path that tries "any exercise for this sense".
        ELSE 0.001
    END;
$$;


-- ============================================================================
-- 9.2 Helper: complexity tier window from average p_known
-- ============================================================================
-- Mirrors the heuristic in
-- services/exercise_session_service.py::_get_supplementary_exercises.

CREATE OR REPLACE FUNCTION public.tier_window_for_p_known(p_avg numeric)
RETURNS text[]
LANGUAGE sql IMMUTABLE
AS $$
    SELECT CASE
        WHEN p_avg < 0.20 THEN ARRAY['T1', 'T2']
        WHEN p_avg < 0.40 THEN ARRAY['T2', 'T3']
        WHEN p_avg < 0.60 THEN ARRAY['T3', 'T4']
        WHEN p_avg < 0.80 THEN ARRAY['T4', 'T5']
        ELSE                    ARRAY['T5', 'T6']
    END;
$$;


-- ============================================================================
-- 9.3 Helper: complexity tier → phase letter
-- ============================================================================
-- Mirrors services/conversation_generation/categorical_maps.py::TIER_TO_PHASE.

CREATE OR REPLACE FUNCTION public.tier_to_phase(p_tier text)
RETURNS text
LANGUAGE sql IMMUTABLE
AS $$
    SELECT CASE p_tier
        WHEN 'T1' THEN 'A'
        WHEN 'T2' THEN 'A'
        WHEN 'T3' THEN 'B'
        WHEN 'T4' THEN 'C'
        WHEN 'T5' THEN 'D'
        WHEN 'T6' THEN 'D'
        ELSE 'B'
    END;
$$;


-- ============================================================================
-- 9.4 Core: get_exercise_session
-- ============================================================================
-- Daily mixed session builder. Single round-trip from Python:
--   1. Anti-repetition: scan user_exercise_history for last 7 days
--   2. Pull due/learning/new candidate senses via get_session_senses
--   3. Top up the new bucket from user_flashcards.state='new' if underfilled
--   4. De-dupe senses across buckets (prefer due > learning > new)
--   5. Pull ladder picks via get_ladder_session (max 5)
--   6. For each remaining sense, pick one exercise weighted by phase
--      (ROW_NUMBER over PARTITION BY sense_id ORDER BY type_weight DESC, RANDOM())
--   7. Apply per-bucket caps (40/40/20 of session_size)
--   8. Fill any gap with non-vocabulary supplementary exercises whose
--      complexity_tier falls in the user's tier window
--   9. UNION ALL → ORDER BY priority DESC, RANDOM() → LIMIT session_size
--
-- Virtual jumbled-sentence picks (bucket 6) are NOT produced here — they
-- depend on Python LanguageProcessor and are appended by the caller.

CREATE OR REPLACE FUNCTION public.get_exercise_session(
    p_user_id uuid,
    p_language_id smallint,
    p_session_size integer DEFAULT 20
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
BEGIN
    -- Estimate user's complexity tier window from average p_known.
    -- Falls back to 0.30 (mid-recognition) for users with no vocabulary data.
    SELECT COALESCE(AVG(p_known)::numeric, 0.30)
      INTO v_avg_p
      FROM user_vocabulary_knowledge
     WHERE user_id = p_user_id
       AND language_id = p_language_id;

    v_tiers := tier_window_for_p_known(v_avg_p);

    RETURN QUERY
    WITH
    -- Step 1: Anti-repetition lookup. Replaces the legacy 500-row scan of
    -- exercise_attempts with the indexed Phase 4 history table.
    recent_seen AS (
        SELECT DISTINCT exercise_id
          FROM user_exercise_history
         WHERE user_id = p_user_id
           AND language_id = p_language_id
           AND session_date >= CURRENT_DATE - INTERVAL '7 days'
    ),

    -- Step 2: Candidate senses across due / learning / new buckets.
    raw_senses AS (
        SELECT out_sense_id AS sense_id,
               out_effective_p_known::numeric AS p_known,
               out_bucket AS bucket
          FROM get_session_senses(
              p_user_id, p_language_id,
              v_due_slots * 3, v_learning_slots * 3, v_new_slots * 3
          )
    ),

    -- Step 3: Top up the 'new' bucket from flashcards.state='new' if underfilled.
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

    -- Step 4: De-dupe senses across buckets. Prefer due > learning > new.
    -- Mirrors the Python picked_sense_ids.update() filter chain.
    all_senses AS (
        SELECT sense_id, p_known, bucket
          FROM raw_senses
        UNION ALL
        SELECT sense_id, p_known, bucket
          FROM new_fallback
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

    -- Step 5: Ladder picks via get_ladder_session.
    -- Single source of truth for ladder selection — fixes the broken
    -- ExerciseSessionService._get_ladder_exercises() Python call.
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
            -- Bump ladder priority above vocab so the slot is honoured.
            ls.out_priority + 1.0 AS priority
          FROM get_ladder_session(p_user_id, p_language_id, v_ladder_cap) ls
    ),

    -- Step 6: One exercise per sense (excluding ladder-already-picked senses),
    -- ranked by phase weight then random tie-break.
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
            )                         AS type_weight
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

    -- Step 7: Apply per-bucket caps (40/40/20).
    -- Each sense yields at most one exercise (rn = 1); each bucket is
    -- then truncated to its slot allocation.
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
            -- Priority anchors by bucket; within bucket, higher weight = higher pick order.
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

    -- Step 8: Fill remaining slots with non-vocabulary supplementary exercises.
    -- Excludes anything already in vocab_picks or ladder_picks.
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

    -- Step 9: UNION, ORDER, LIMIT.
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
