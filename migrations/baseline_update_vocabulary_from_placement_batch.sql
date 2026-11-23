-- ============================================================================
-- baseline_update_vocabulary_from_placement_batch.sql — repo record of the live public.update_vocabulary_from_placement_batch
-- ============================================================================
--
-- WHAT: Applies a batch of placement answers (sense_id, is_correct) to user_vocabulary_knowledge with one BKT word-test update per sense, and returns p_known before/after.
-- Used by: No caller in the app code (finding F-08); placement now runs through the calibration_placement_* functions.
--
-- WHY: this function exists live but had no CREATE in any migrations/ file
-- (including archive/): finding F-03 of the 2026-11-23 database review. The
-- definition below is pg_get_functiondef() read from live
-- (kpfqrjtfxmujzolwsvdq) on 2026-11-23, with CRLF line ends normalised to LF,
-- plus the live owner and the live ACL ({postgres=X/postgres,service_role=X/postgres}:
-- EXECUTE for service_role only, nothing for PUBLIC / anon / authenticated).
--
-- WHAT A LEARNER OR THE APP WOULD NOTICE: nothing. Applying this file is a
-- no-op: the body hashes equal to live (md5 of prosrc with -- comments and all
-- whitespace removed = 586c0e8107614a7bf820895be888a8c4), and the attributes, owner and grants
-- are the live ones. It exists so the repo can rebuild the database and so the
-- next change to this function has a file to start from.
--
-- Live this function is SECURITY INVOKER; reproduced as live
-- (advisor function_search_path_mutable, finding F-14, is a separate task).
--
-- PRECONDITIONS: none beyond the tables/functions the body reads, all live.
--
-- VERIFY (read-only; run before and after; expect body_matches = true,
-- definer = false, search_path = {search_path=public, pg_temp}, anon_x = false, auth_x = false,
-- service_x = true):
--   SELECT md5(regexp_replace(regexp_replace(p.prosrc, '--[^\n]*', '', 'g'), '\s', '', 'g'))
--            = '586c0e8107614a7bf820895be888a8c4' AS body_matches,
--          p.prosecdef AS definer, p.proconfig AS search_path, pg_get_userbyid(p.proowner) AS owner,
--          has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_x,
--          has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_x,
--          has_function_privilege('service_role', p.oid, 'EXECUTE') AS service_x
--     FROM pg_proc p WHERE p.oid = 'public.update_vocabulary_from_placement_batch(uuid,smallint,jsonb)'::regprocedure;
--
-- ROLLBACK: none needed (the file changes nothing). If a later edit of this
-- file is applied by mistake, re-apply this file at the commit that added it.
--
-- Idempotent: CREATE OR REPLACE + REVOKE/GRANT; safe to re-run.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.update_vocabulary_from_placement_batch(p_user_id uuid, p_language_id smallint, p_items jsonb)
 RETURNS TABLE(out_sense_id integer, out_p_known_before numeric, out_p_known_after numeric, out_status text)
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
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
ALTER FUNCTION public.update_vocabulary_from_placement_batch(uuid,smallint,jsonb) OWNER TO postgres;
REVOKE ALL ON FUNCTION public.update_vocabulary_from_placement_batch(uuid,smallint,jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.update_vocabulary_from_placement_batch(uuid,smallint,jsonb) TO service_role;
