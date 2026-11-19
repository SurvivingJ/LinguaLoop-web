-- =============================================================================
-- TEST-ONLY STUB of public.knowledge_calibration_inputs (vocab-placement tech §14, TASK-1079).
-- NOT A MIGRATION. Never apply it to production: the real function is written in
-- migrations/knowledge_calibration_inputs.sql (TASK-1079) and applies the placement
-- instrument rule (§9) that this stub ignores.
--
-- Purpose: lets migrations/knowledge_report_summary.sql (TASK-1036), which embeds the real
-- function, load and run on a throwaway database (local harness or Supabase branch) before
-- TASK-1079 exists. It returns the documented §14 shape computed from LEGACY definition-mode
-- check rows only (report tech §2.6 steps 1-4, ADR-051):
--   A   = calibration_sessions.mode = 'definition', word_language_id = L, answered_at set and
--         <= p_as_of, anchor sense_rank = 1 (p_session_id, when given, restricts A to it)
--   D*  = p_definition_language_id, else the definition language with the most answers of A in
--         (p_as_of - p_window_days, p_as_of]; ties -> later max(answered_at) -> lower id; when no
--         answer falls in the window, the same rule over all of A
--   A*  = window answers with D*, latest answer per anchor_vocab_id
--   bands[b]    = [n, s, c] over A* in calibration_responses.zipf_band b (s = chosen_sense_id NULL)
--   alltime_n   = per-band distinct lemmas with D*, no window (latest answer per lemma)
--   first_at / last_at = min / max answered_at over A*; over A with D* when A* is empty (E1c)
--   rated_known_in_frame = rated-known rank-1 lemmas (report §2.4) in the frame F(L, D*)
--   instrument, pairs, gap = null; placement_eligible = false; stop_reasons = []
-- Signature (§14): (p_user_id uuid, p_language_id smallint, p_as_of timestamptz DEFAULT now(),
--   p_window_days integer DEFAULT 180, p_definition_language_id smallint DEFAULT NULL,
--   p_session_id uuid DEFAULT NULL) RETURNS jsonb, STABLE, SECURITY INVOKER.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.knowledge_calibration_inputs(
    p_user_id uuid,
    p_language_id smallint,
    p_as_of timestamptz DEFAULT now(),
    p_window_days integer DEFAULT 180,
    p_definition_language_id smallint DEFAULT NULL,
    p_session_id uuid DEFAULT NULL)
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
    WITH a AS (
        SELECT cs.definition_language_id AS d, cr.anchor_vocab_id AS v, cr.zipf_band AS band,
               cr.answered_at, cr.chosen_sense_id, cr.is_correct,
               cr.answered_at > p_as_of - make_interval(days => p_window_days) AS in_win
          FROM calibration_sessions cs
          JOIN calibration_responses cr ON cr.session_id = cs.id
          JOIN dim_word_senses an ON an.id = cr.anchor_sense_id AND an.sense_rank = 1
         WHERE cs.user_id = p_user_id AND cs.word_language_id = p_language_id
           AND cs.mode = 'definition'
           AND cr.answered_at IS NOT NULL AND cr.answered_at <= p_as_of
           AND (p_session_id IS NULL OR cs.id = p_session_id)
    ), dstar AS (
        SELECT coalesce(
                   p_definition_language_id,
                   (SELECT a.d FROM a WHERE a.in_win GROUP BY a.d
                     ORDER BY count(*) DESC, max(a.answered_at) DESC, a.d LIMIT 1),
                   (SELECT a.d FROM a GROUP BY a.d
                     ORDER BY count(*) DESC, max(a.answered_at) DESC, a.d LIMIT 1)) AS d
    ), win AS (
        SELECT DISTINCT ON (a.v) a.v, a.band, a.answered_at, a.chosen_sense_id, a.is_correct
          FROM a JOIN dstar ON a.d = dstar.d
         WHERE a.in_win
         ORDER BY a.v, a.answered_at DESC
    ), allt AS (
        SELECT DISTINCT ON (a.v) a.v, a.band, a.answered_at
          FROM a JOIN dstar ON a.d = dstar.d
         ORDER BY a.v, a.answered_at DESC
    ), rk AS (
        SELECT s.vocab_id
          FROM user_vocabulary_knowledge k
          JOIN dim_word_senses s ON s.id = k.sense_id AND s.sense_rank = 1
         WHERE k.user_id = p_user_id AND k.language_id = p_language_id
         GROUP BY s.vocab_id
        HAVING sum(coalesce(k.word_test_correct, 0)) > sum(coalesce(k.word_test_wrong, 0))
           AND (array_agg(k.p_known ORDER BY k.last_evidence_at DESC NULLS LAST,
                          coalesce(k.evidence_count, 0) DESC, k.sense_id))[1] >= 0.75
           AND NOT bool_or(k.status = 'user_marked_unknown')
    )
    SELECT jsonb_build_object(
        'definition_language_id', (SELECT d FROM dstar),
        'instrument', NULL::text,
        'bands', (SELECT jsonb_agg(jsonb_build_array(x.n, x.s, x.c) ORDER BY x.b)
                    FROM (SELECT g.b, count(w.v) AS n,
                                 count(w.v) FILTER (WHERE w.chosen_sense_id IS NULL) AS s,
                                 count(w.v) FILTER (WHERE w.is_correct) AS c
                            FROM generate_series(1, 7) AS g(b)
                            LEFT JOIN win w ON w.band = g.b
                           GROUP BY g.b) x),
        'pairs', NULL::jsonb,
        'gap', NULL::jsonb,
        'alltime_n', (SELECT jsonb_agg(x.n ORDER BY x.b)
                        FROM (SELECT g.b, count(t.v) AS n
                                FROM generate_series(1, 7) AS g(b)
                                LEFT JOIN allt t ON t.band = g.b
                               GROUP BY g.b) x),
        'first_at', coalesce((SELECT min(answered_at) FROM win), (SELECT min(answered_at) FROM allt)),
        'last_at', coalesce((SELECT max(answered_at) FROM win), (SELECT max(answered_at) FROM allt)),
        'placement_eligible', false,
        'stop_reasons', '[]'::jsonb,
        'rated_known_in_frame', (
            SELECT count(*) FROM rk
             WHERE EXISTS (
                 SELECT 1 FROM calibration_anchor_pool p
                   JOIN dim_word_senses ps ON ps.id = p.sense_id AND ps.sense_rank = 1
                  WHERE p.word_language_id = p_language_id
                    AND p.definition_language_id = (SELECT d FROM dstar)
                    AND p.vocab_id = rk.vocab_id
                    AND p.has_embedding
                    AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist bl
                                     WHERE bl.sense_id = p.sense_id))));
$$;

REVOKE ALL ON FUNCTION public.knowledge_calibration_inputs(uuid, smallint, timestamptz, integer, smallint, uuid)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.knowledge_calibration_inputs(uuid, smallint, timestamptz, integer, smallint, uuid)
    TO service_role;
