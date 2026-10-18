-- ============================================================================
-- practice_review_ahead.sql — open-ended review for Practice mode
-- Date: 2026-10-18
-- Spec: wiki/features/practice-extra-rounds.tech.md
--       wiki/decisions/ADR-036-open-ended-practice-beyond-budget.md
--
-- get_practice_session's Maintenance pool only holds senses due within a week
-- or visibly decayed, so a learner who wants to keep reviewing runs dry. This
-- function serves "review ahead" items: senses the learner has already
-- reviewed (an FSRS row exists), lowest effective p_known first, then earliest
-- due date. One exercise per sense, preferring the exercise the learner has
-- seen least recently. Senses attempted in the last p_exclude_recent_minutes
-- and senses in p_exclude_sense_ids are skipped so consecutive rounds do not
-- loop on the same words.
--
-- Answers go through the normal attempt path: FSRS and BKT update as usual.
-- FSRS accounts for elapsed time, so an early correct answer only stretches
-- the interval a little.
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.get_review_ahead_items(
    p_user_id                  uuid,
    p_language_id              smallint,
    p_limit                    integer   DEFAULT 10,
    p_exclude_recent_minutes   integer   DEFAULT 10,
    p_exclude_sense_ids        integer[] DEFAULT '{}'
) RETURNS jsonb LANGUAGE sql VOLATILE
SET search_path = public, pg_temp
AS $$
    WITH recent AS (
        SELECT DISTINCT ea.sense_id
        FROM public.exercise_attempts ea
        WHERE ea.user_id = p_user_id
          AND ea.sense_id IS NOT NULL
          AND ea.created_at >= now() - make_interval(mins => GREATEST(p_exclude_recent_minutes, 0))
    ),
    pool AS (
        SELECT
            fc.sense_id,
            fc.due_date,
            uvk.p_known,
            public.bkt_effective_p_known(
                COALESCE(uvk.p_known, 0.10), uvk.last_evidence_at,
                fc.stability, COALESCE(uvk.evidence_count, 0)
            ) AS eff_p_known
        FROM public.user_flashcards fc
        LEFT JOIN public.user_vocabulary_knowledge uvk
            ON uvk.user_id = fc.user_id AND uvk.sense_id = fc.sense_id
        WHERE fc.user_id = p_user_id
          AND fc.language_id = p_language_id
          AND COALESCE(fc.reps, 0) > 0
          AND fc.sense_id <> ALL (COALESCE(p_exclude_sense_ids, '{}'))
          AND NOT EXISTS (SELECT 1 FROM recent r WHERE r.sense_id = fc.sense_id)
        ORDER BY eff_p_known ASC NULLS FIRST, fc.due_date ASC NULLS LAST, fc.sense_id
        LIMIT GREATEST(LEAST(p_limit, 50), 0)
    ),
    last_seen AS (
        SELECT ea.exercise_id, max(ea.created_at) AS seen_at
        FROM public.exercise_attempts ea
        JOIN pool p ON p.sense_id = ea.sense_id
        WHERE ea.user_id = p_user_id
        GROUP BY ea.exercise_id
    ),
    picked AS (
        SELECT DISTINCT ON (p.sense_id)
            e.id            AS exercise_id,
            p.sense_id,
            e.exercise_type,
            e.content,
            e.ladder_level,
            public.ladder_get_family(e.ladder_level) AS family,
            p.p_known,
            p.eff_p_known,
            p.due_date,
            COALESCE(det.expected_seconds_p50::int, det.expected_seconds, 45) AS expected_seconds
        FROM pool p
        JOIN public.exercises e
            ON e.word_sense_id = p.sense_id
           AND e.language_id   = p_language_id
           AND e.is_active
        LEFT JOIN public.dim_exercise_types det ON det.type_code = e.exercise_type
        LEFT JOIN last_seen ls ON ls.exercise_id = e.id
        ORDER BY p.sense_id, ls.seen_at ASC NULLS FIRST, random()
    )
    SELECT COALESCE(jsonb_agg(jsonb_build_object(
        'exercise_id',      exercise_id,
        'sense_id',         sense_id,
        'exercise_type',    exercise_type,
        'family',           family,
        'content',          content,
        'ladder_level',     ladder_level,
        'p_known',          p_known,
        'expected_seconds', expected_seconds,
        'mode',             'maintenance',
        'review_ahead',     true
    ) ORDER BY eff_p_known ASC NULLS FIRST, due_date ASC NULLS LAST, sense_id), '[]'::jsonb)
    FROM picked;
$$;

REVOKE ALL ON FUNCTION public.get_review_ahead_items(uuid, smallint, integer, integer, integer[]) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_review_ahead_items(uuid, smallint, integer, integer, integer[]) TO service_role;

COMMENT ON FUNCTION public.get_review_ahead_items(uuid, smallint, integer, integer, integer[]) IS
    'Practice extra rounds: review-ahead items (already-reviewed senses, lowest effective '
    'p_known first), one exercise per sense, skipping recently attempted senses. '
    'See wiki/features/practice-extra-rounds.tech.md.';

COMMIT;
