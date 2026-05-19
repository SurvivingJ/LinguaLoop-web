-- ============================================================================
-- update_vocabulary_from_word_tests_batch — batched per-sense word-test BKT
-- ============================================================================
-- Dictation produces N word-level evidence points per submission (often 50-100
-- for a 60-word passage). The original implementation called the single-sense
-- `update_vocabulary_from_word_test` once per word inside the request handler,
-- producing N sequential Supabase round-trips plus N invocations of the
-- downstream `_auto_create_flashcards` / `_trigger_frequency_inference`
-- helpers. At realistic latency this exceeded gunicorn's worker timeout and
-- truncated the response (Chrome: "Content-Length header of network response
-- exceeds response Body").
--
-- This RPC mirrors the existing batched `update_vocabulary_from_test`
-- (comprehension flow) but for direct sense-level word-test evidence, using
-- the stronger `bkt_update_word_test` slip/guess parameters (slip=0.05).
--
-- BEHAVIORAL CHANGE — DEDUP CORRECTNESS FIX:
--   The previous per-word path incremented word_test_correct/wrong once per
--   occurrence; if a word appeared N times in a transcript it received N
--   independent BKT updates. BKT assumes independent samples, which repeated
--   tokens in a single submission violate. This function dedupes via
--   `bool_or` (credit as correct if ANY occurrence was correct) — matching
--   the comprehension batch's behavior and producing one evidence point per
--   unique sense per submission.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.update_vocabulary_from_word_tests_batch(
    p_user_id     uuid,
    p_language_id smallint,
    p_results     jsonb   -- [{"sense_id": int, "is_correct": bool}, ...]
)
RETURNS TABLE(
    out_sense_id        integer,
    out_p_known_before  numeric,
    out_p_known_after   numeric,
    out_status          text
)
LANGUAGE plpgsql
AS $function$
BEGIN
    RETURN QUERY
    WITH input AS (
        SELECT
            (r->>'sense_id')::integer  AS sense_id,
            (r->>'is_correct')::boolean AS is_correct
        FROM jsonb_array_elements(p_results) r
        WHERE r ? 'sense_id' AND r ? 'is_correct'
    ),
    deduped AS (
        SELECT sense_id, bool_or(is_correct) AS is_correct
        FROM input
        GROUP BY sense_id
    ),
    current_state AS (
        SELECT
            d.sense_id,
            d.is_correct,
            COALESCE(uvk.p_known,
                CASE
                    WHEN dv.frequency_rank IS NULL THEN 0.10
                    WHEN dv.frequency_rank >= 6.0 THEN 0.85
                    WHEN dv.frequency_rank >= 5.0 THEN 0.65
                    WHEN dv.frequency_rank >= 4.0 THEN 0.35
                    WHEN dv.frequency_rank >= 3.0 THEN 0.15
                    ELSE 0.05
                END
            ) AS p_current
        FROM deduped d
        JOIN dim_word_senses dws ON dws.id = d.sense_id
        JOIN dim_vocabulary    dv  ON dv.id = dws.vocab_id
        LEFT JOIN user_vocabulary_knowledge uvk
            ON uvk.user_id = p_user_id AND uvk.sense_id = d.sense_id
    ),
    updated AS (
        SELECT
            cs.sense_id,
            cs.p_current AS p_before,
            bkt_update_word_test(cs.p_current, cs.is_correct) AS p_after,
            cs.is_correct
        FROM current_state cs
    ),
    upserted AS (
        INSERT INTO user_vocabulary_knowledge
            (user_id, sense_id, language_id, p_known, status,
             evidence_count, word_test_correct, word_test_wrong,
             last_evidence_at, updated_at)
        SELECT
            p_user_id, u.sense_id, p_language_id,
            u.p_after, bkt_status(u.p_after),
            1,
            CASE WHEN u.is_correct THEN 1 ELSE 0 END,
            CASE WHEN u.is_correct THEN 0 ELSE 1 END,
            NOW(), NOW()
        FROM updated u
        ON CONFLICT (user_id, sense_id) DO UPDATE SET
            p_known = EXCLUDED.p_known,
            status = CASE
                WHEN user_vocabulary_knowledge.status = 'user_marked_unknown'
                THEN 'user_marked_unknown'
                ELSE EXCLUDED.status
            END,
            evidence_count        = user_vocabulary_knowledge.evidence_count + 1,
            word_test_correct     = user_vocabulary_knowledge.word_test_correct + EXCLUDED.word_test_correct,
            word_test_wrong       = user_vocabulary_knowledge.word_test_wrong + EXCLUDED.word_test_wrong,
            last_evidence_at      = NOW(),
            updated_at            = NOW()
        RETURNING sense_id, p_known, status
    )
    SELECT
        upserted.sense_id,
        COALESCE(u.p_before, 0.10),
        upserted.p_known,
        upserted.status
    FROM upserted
    LEFT JOIN updated u ON u.sense_id = upserted.sense_id;
END;
$function$;

GRANT EXECUTE ON FUNCTION public.update_vocabulary_from_word_tests_batch(uuid, smallint, jsonb)
    TO authenticated;
