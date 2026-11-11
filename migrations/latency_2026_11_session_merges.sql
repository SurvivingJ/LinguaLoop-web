-- Daily-session read merges, 2026-11-11 (ADR-043 option B, TASK-930).
-- Two read-only bundling functions so GET /api/study-session makes fewer
-- round trips. Python keeps all the logic and falls back to the old per-table
-- reads when these functions are missing or fail (services/practice_session_
-- service.py _new_word_state, services/prestudy.py plan_for_tests).
--
-- Both are SECURITY INVOKER: Flask calls them as service_role, which already
-- holds every privilege they need (and bypasses RLS). Idempotent.
-- Rollback: DROP FUNCTION public.new_word_state_inputs(uuid, smallint, date, timestamptz, boolean);
--           DROP FUNCTION public.prestudy_plan_inputs(uuid, smallint, uuid[]);

-- 1. review_governor_state + ladder_new_word_state in one call.
--    p_with_governor = false mirrors the Python skip when the plan excludes
--    the 'practice' module (governor is then not consulted at all).
CREATE OR REPLACE FUNCTION public.new_word_state_inputs(
    p_user_id uuid, p_language_id smallint, p_date date,
    p_day_start timestamptz, p_with_governor boolean)
RETURNS jsonb
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
    SELECT jsonb_build_object(
        'governor', CASE WHEN p_with_governor
                         THEN public.review_governor_state(p_user_id, p_language_id, p_date)
                    END,
        'ladder',   public.ladder_new_word_state(p_user_id, p_language_id, p_day_start))
$$;

REVOKE ALL ON FUNCTION public.new_word_state_inputs(uuid, smallint, date, timestamptz, boolean)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.new_word_state_inputs(uuid, smallint, date, timestamptz, boolean)
    TO service_role;

-- 2. Everything services.prestudy.plan_for_tests reads, for a day's tests:
--    the tests' linked senses, the learner's knowledge of them, the frequency
--    rank of senses with no knowledge row, the calibration ability, and which
--    senses have at least one active exercise. Replaces five reads (more when
--    a day links >200 senses, which the Python path chunks).
--    `with_exercises` covers every linked sense with DISTINCT; Python narrows
--    it to the senses it asks about. (The old per-row read could be cut short
--    by PostgREST's row cap; this cannot.)
CREATE OR REPLACE FUNCTION public.prestudy_plan_inputs(
    p_user_id uuid, p_language_id smallint, p_test_ids uuid[])
RETURNS jsonb
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
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
$$;

REVOKE ALL ON FUNCTION public.prestudy_plan_inputs(uuid, smallint, uuid[])
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.prestudy_plan_inputs(uuid, smallint, uuid[])
    TO service_role;
