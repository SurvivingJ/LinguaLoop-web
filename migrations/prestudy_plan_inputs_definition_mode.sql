-- ============================================================================
-- prestudy_plan_inputs_definition_mode.sql - read only the definition-mode
-- calibration ability as the prestudy knowledge prior
-- Date: 2026-11-23   Review: pkg8 (coordinator item 1). NOT APPLIED.
--
-- *** LEARNER-VISIBLE ***
--
-- WHAT: CREATE OR REPLACE public.prestudy_plan_inputs(uuid, smallint, uuid[]).
-- The body is the live definition (pg_get_functiondef 2026-11-23, CRLF
-- normalised to LF; equal by body hash a61bafd7599d66920b4be55147798117 to
-- migrations/latency_2026_11_session_merges.sql) with ONE line added to the
-- ability_zipf sub-select:  AND ucs.mode = 'definition'
-- ('definition' = services/calibration_service.py MODE_DEFINITION; alias ucs
-- as in the live body). Attributes as live: LANGUAGE sql, STABLE, SECURITY
-- INVOKER, search_path public, pg_temp, owner postgres, EXECUTE service_role
-- only.
--
-- WHY: user_calibration_state's key is (user_id, language_id, mode), and the
-- live sub-select takes any one row (LIMIT 1) for the user and language, so a
-- pronunciation-mode ability can become the definition-knowledge prior for
-- prestudy. The Python twin (services/prestudy.py _ability_zipf) is being
-- changed to filter mode = 'definition' in another package; this keeps the
-- RPC path and the Python fallback path in agreement.
--
-- WHAT A LEARNER WOULD NOTICE: one Japanese learner (the only non-NULL ability
-- live is a ja pronunciation row, ability_zipf 5.49) gets prestudy new-word
-- counts computed from the default prior 5.0 (DEFAULT_ABILITY_ZIPF) instead of
-- 5.49, so somewhat more words count as unknown in prestudy. Everyone else:
-- no change (no definition-mode ability is set live, so they already get 5.0).
--
-- PRECONDITIONS: none in order with code (the Python change and this file can
-- land in either order; until both are live, the two paths may disagree for
-- that learner). Live body unchanged since 2026-11-23 (VERIFY BEFORE).
--
-- VERIFY BEFORE (read-only; expect body_md5 = a61bafd7599d66920b4be55147798117,
-- filters_mode = false, definer = false, volatility = s, search_path
-- {public, pg_temp}, anon_x = auth_x = false):
-- VERIFY AFTER (same query; expect body_md5 = 3930ef881bc04a4782479f4e4fce1bf3, filters_mode = true,
-- the other columns unchanged):
--   SELECT md5(regexp_replace(regexp_replace(p.prosrc, '--[^\n]*', '', 'g'), '\s', '', 'g')) AS body_md5,
--          p.prosrc LIKE '%ucs.mode = ''definition''%' AS filters_mode,
--          p.prosecdef AS definer, p.provolatile AS volatility, p.proconfig AS search_path,
--          has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_x,
--          has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_x
--     FROM pg_proc p WHERE p.oid = 'public.prestudy_plan_inputs(uuid,smallint,uuid[])'::regprocedure;
--   -- whose prior changes (expect, before: one ja pronunciation row 5.49;
--   -- after applying, the function returns NULL ability_zipf for that learner
--   -- because no definition-mode ability exists):
--   SELECT user_id, language_id, mode, ability_zipf FROM public.user_calibration_state
--    WHERE ability_zipf IS NOT NULL ORDER BY mode;
--
-- ROLLBACK: migrations/prestudy_plan_inputs_definition_mode_rollback.sql
-- (the live body verbatim).
--
-- After applying: this file is canonical for prestudy_plan_inputs;
-- latency_2026_11_session_merges.sql keeps a stale copy (it is the only record
-- of new_word_state_inputs, so keep it; do not re-run it).
--
-- Idempotent: CREATE OR REPLACE + REVOKE/GRANT; safe to re-run.
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.prestudy_plan_inputs(p_user_id uuid, p_language_id smallint, p_test_ids uuid[])
 RETURNS jsonb
 LANGUAGE sql
 STABLE
 SET search_path TO 'public', 'pg_temp'
AS $function$
    WITH t AS (
        SELECT id, vocab_sense_ids FROM public.tests WHERE id = ANY (p_test_ids)
    ), ids AS (
        SELECT DISTINCT s AS sense_id
          FROM t, unnest(coalesce(t.vocab_sense_ids, '{}'::integer[])) AS s
         WHERE s IS NOT NULL
    ), k AS (
        SELECT uvk.sense_id, uvk.p_known, uvk.status, uvk.evidence_count
          FROM public.user_vocabulary_knowledge uvk
          JOIN ids ON ids.sense_id = uvk.sense_id
         WHERE uvk.user_id = p_user_id
    ), f AS (
        SELECT ws.id, v.frequency_rank
          FROM public.dim_word_senses ws
          LEFT JOIN public.dim_vocabulary v ON v.id = ws.vocab_id
         WHERE ws.id IN (SELECT sense_id FROM ids)
           AND ws.id NOT IN (SELECT sense_id FROM k)
    )
    SELECT jsonb_build_object(
        'tests', coalesce((SELECT jsonb_agg(jsonb_build_object(
                     'id', t.id, 'vocab_sense_ids', to_jsonb(t.vocab_sense_ids))) FROM t), '[]'::jsonb),
        'knowledge', coalesce((SELECT jsonb_agg(jsonb_build_object(
                     'sense_id', k.sense_id, 'p_known', k.p_known,
                     'status', k.status, 'evidence_count', k.evidence_count)) FROM k), '[]'::jsonb),
        'freq', coalesce((SELECT jsonb_agg(jsonb_build_object(
                     'id', f.id, 'frequency_rank', f.frequency_rank)) FROM f), '[]'::jsonb),
        'ability_zipf', (SELECT ucs.ability_zipf FROM public.user_calibration_state ucs
                          WHERE ucs.user_id = p_user_id AND ucs.language_id = p_language_id
                            AND ucs.mode = 'definition'
                          LIMIT 1),
        'with_exercises', coalesce((SELECT jsonb_agg(DISTINCT e.word_sense_id)
                                      FROM public.exercises e
                                     WHERE e.is_active
                                       AND e.word_sense_id IN (SELECT sense_id FROM ids)), '[]'::jsonb))
$function$;

ALTER FUNCTION public.prestudy_plan_inputs(uuid, smallint, uuid[]) OWNER TO postgres;
REVOKE ALL ON FUNCTION public.prestudy_plan_inputs(uuid, smallint, uuid[]) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.prestudy_plan_inputs(uuid, smallint, uuid[]) TO service_role;

COMMIT;
