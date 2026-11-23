-- ============================================================================
-- prestudy_plan_inputs_definition_mode_rollback.sql - rollback of
-- migrations/prestudy_plan_inputs_definition_mode.sql
--
-- Restores public.prestudy_plan_inputs exactly as live on 2026-11-23 (body md5
-- a61bafd7599d66920b4be55147798117: ability_zipf from any calibration mode).
-- Learner-visible: yes, in reverse (the ja learner's prior goes back to 5.49).
-- VERIFY AFTER (read-only; expect body_md5 = a61bafd7599d66920b4be55147798117,
-- filters_mode = false, anon_x = auth_x = false):
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
