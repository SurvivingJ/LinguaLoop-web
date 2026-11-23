-- =============================================================================
-- Vocabulary placement — evidence kind (TASK-1081, ADR-059 accepted 2026-11-18)
-- =============================================================================
-- Placement answers are their own evidence kind (vocab-placement tech §10):
--   * two counters on user_vocabulary_knowledge, placement_correct / placement_wrong
--     (fast defaults: no table rewrite);
--   * update_vocabulary_from_placement_batch — the same BKT update as the vocabulary
--     check's update_vocabulary_from_word_tests_batch (bkt_update_word_test: slip 0.05,
--     guess 0.25, transit 0.05; Zipf step prior; duplicates merged with bool_or), but it
--     increments the placement counters and NEVER word_test_correct / word_test_wrong,
--     so placement evidence alone can never make a word "rated known after a direct check".
-- Python (services/placement_evidence.py) decides which word outcomes write (§10 table):
--   meaning ✓ + reading ✓ (or reading-exempt) → correct; meaning ✗ or IDK → wrong;
--   meaning ✓ + reading not ✓ → no write (the word goes to reading practice, A2r).
-- Rollback: placement_evidence_kind_rollback.sql. Owner-applied; no data is changed.
-- =============================================================================

ALTER TABLE public.user_vocabulary_knowledge
  ADD COLUMN IF NOT EXISTS placement_correct smallint NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS placement_wrong   smallint NOT NULL DEFAULT 0;

CREATE OR REPLACE FUNCTION public.update_vocabulary_from_placement_batch(
    p_user_id     uuid,
    p_language_id smallint,
    p_items       jsonb   -- [{"sense_id": int, "is_correct": bool}, ...]
)
RETURNS TABLE(
    out_sense_id        integer,
    out_p_known_before  numeric,
    out_p_known_after   numeric,
    out_status          text
)
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $function$
BEGIN
    IF p_user_id IS NULL OR p_language_id IS NULL THEN
        RAISE EXCEPTION 'user and language are required' USING ERRCODE = '22023';
    END IF;
    IF p_items IS NULL OR jsonb_typeof(p_items) <> 'array' THEN
        RAISE EXCEPTION 'p_items must be a JSON array' USING ERRCODE = '22023';
    END IF;

    RETURN QUERY
    WITH input AS (
        SELECT (r->>'sense_id')::integer  AS sense_id,
               (r->>'is_correct')::boolean AS is_correct
        FROM jsonb_array_elements(p_items) r
        WHERE r ? 'sense_id' AND r ? 'is_correct'
    ),
    deduped AS (
        SELECT sense_id, bool_or(is_correct) AS is_correct
        FROM input
        GROUP BY sense_id
    ),
    current_state AS (
        SELECT d.sense_id, d.is_correct,
               COALESCE(uvk.p_known,
                   CASE
                       WHEN dv.frequency_rank IS NULL THEN 0.10
                       WHEN dv.frequency_rank >= 6.0 THEN 0.85
                       WHEN dv.frequency_rank >= 5.0 THEN 0.65
                       WHEN dv.frequency_rank >= 4.0 THEN 0.35
                       WHEN dv.frequency_rank >= 3.0 THEN 0.15
                       ELSE 0.05
                   END) AS p_current
        FROM deduped d
        JOIN public.dim_word_senses dws ON dws.id = d.sense_id
        JOIN public.dim_vocabulary  dv  ON dv.id  = dws.vocab_id
        LEFT JOIN public.user_vocabulary_knowledge uvk
               ON uvk.user_id = p_user_id AND uvk.sense_id = d.sense_id
    ),
    updated AS (
        SELECT cs.sense_id, cs.p_current AS p_before,
               public.bkt_update_word_test(cs.p_current, cs.is_correct) AS p_after,
               cs.is_correct
        FROM current_state cs
    ),
    upserted AS (
        INSERT INTO public.user_vocabulary_knowledge AS k
            (user_id, sense_id, language_id, p_known, status, evidence_count,
             placement_correct, placement_wrong, last_evidence_at, updated_at)
        SELECT p_user_id, u.sense_id, p_language_id, u.p_after, public.bkt_status(u.p_after), 1,
               CASE WHEN u.is_correct THEN 1 ELSE 0 END,
               CASE WHEN u.is_correct THEN 0 ELSE 1 END,
               now(), now()
        FROM updated u
        ON CONFLICT (user_id, sense_id) DO UPDATE SET
            p_known           = EXCLUDED.p_known,
            status            = CASE WHEN k.status = 'user_marked_unknown' THEN 'user_marked_unknown'
                                     ELSE EXCLUDED.status END,
            evidence_count    = k.evidence_count + 1,
            placement_correct = k.placement_correct + EXCLUDED.placement_correct,
            placement_wrong   = k.placement_wrong + EXCLUDED.placement_wrong,
            last_evidence_at  = now(),
            updated_at        = now()
        RETURNING k.sense_id, k.p_known, k.status
    )
    SELECT upserted.sense_id, COALESCE(u.p_before, 0.10), upserted.p_known, upserted.status
    FROM upserted
    LEFT JOIN updated u ON u.sense_id = upserted.sense_id;
END;
$function$;

REVOKE ALL ON FUNCTION public.update_vocabulary_from_placement_batch(uuid, smallint, jsonb)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.update_vocabulary_from_placement_batch(uuid, smallint, jsonb)
    TO service_role;
