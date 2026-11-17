-- Dual translation GET /next read bundle, 2026-11-17 (TASK-990, TASK-989, TASK-991).
--
-- One read-only function returning everything routes/dual_translation.py
-- `_choose_next` needs for one learner, so GET /api/dual-translation/next makes
-- one database round trip for its reads instead of ~16 sequential ones
-- (measured 2026-11-17 from the sandbox: zh 17 round trips / 6.4 s,
-- ja 19 / 5.5 s). Python keeps the whole selection order; it falls back to
-- the old per-table reads when this function is missing or fails
-- (routes/dual_translation.py `_next_inputs`).
--
-- SECURITY INVOKER, like the other read bundles (latency_2026_11_session_merges.sql):
-- Flask calls it as service_role, which already holds every privilege it needs.
-- Execute is revoked from PUBLIC/anon/authenticated, so no client can call it
-- with someone else's user id; the route passes the user id from the verified JWT.
--
-- Requires dt_submission.skipped_at (migrations/dt_submission_skip.sql, applied first):
-- history[].sk says whether the learner skipped the open submission.
--
-- New object only (no existing function, table or policy is changed).
-- Rollback: migrations/dt_next_inputs_rollback.sql
--   (DROP FUNCTION public.dt_next_inputs(uuid, integer, integer);)
--
-- Revised 2026-11-17: the `legacy` array (whole-passage dt_passage rows with a
-- dt_passage_reference) is gone; that pool was retired and its rows deleted,
-- and GET /next serves sentence windows only. Same signature and grants;
-- re-apply this file to replace the earlier definition.
--
-- Revised 2026-11-17 (ADR-049, TASK-1009): each tests[] entry also carries `ag`,
-- the idx of usable sentences whose active reference two independent reviews
-- passed (test_sentence_references.faithful_reviews >= 2, from
-- migrations/test_sentence_references_faithful_reviews.sql, applied first).
-- Additive key: a reader that does not know `ag` ignores it. Same signature
-- and grants.
--
-- Arguments
--   p_user_id  the learner (from the verified JWT, never from the client)
--   p_l2       the study language; NULL = language of the learner's latest attempt
--   p_l1       the reference language; NULL = users.native_language_id, else 2 (English)
--
-- Returns jsonb
--   l1, l2            the resolved languages (l2 NULL: no language known)
--   salt              number of distinct passages ever served to the learner
--   attempted         ids of every test the learner has attempted (any language)
--   history[]         one row per passage served to the learner:
--                     p passage id, ls last served, g graded, lg last graded at,
--                     b band of the latest grade, o newest open submission id
--                     (no grade, empty reproduction, same L1), sk whether the
--                     learner skipped that open submission, l2, st status,
--                     t source test, s/e sentence range, a age tier
--   tests[]           active tests in l2 with at least one usable sentence
--                     reference in l1: id, h transcript hash, d difficulty,
--                     at attempted, elo distance to the learner's level
--                     (min over test types of |test ELO - learner ELO (1200 when
--                     unrated)|, the get_recommended_tests rule; NULL when unrated)
--                     rows: that test's sentences in idx order as [sentence id,
--                     idx, fresh (hash matches the test), usable reference,
--                     tightness, chars of l2_text]
--                     ag: idx of usable, fresh sentences whose reference two
--                     independent reviews agreed on (NULL when none, ADR-049)
--   ranges[]          every sentence-window dt_passage of those tests:
--                     id, t, s, e, st status, a age tier
--   texts[]           [sentence id, l2_text, l1_text] of the usable sentences of
--                     the first 3 tests in the default order (attempted first by
--                     rotation key, then unattempted by ELO distance then rotation
--                     key) that still have 2+ usable sentences outside served
--                     windows: a prefetch so a new window needs no extra read.
--                     Python never relies on it: a miss costs one read.

CREATE OR REPLACE FUNCTION public.dt_next_inputs(p_user_id uuid, p_l2 integer, p_l1 integer)
RETURNS jsonb
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
    WITH lang AS (
        SELECT COALESCE(
                   p_l2,
                   (SELECT a.language_id::integer FROM public.test_attempts a
                     WHERE a.user_id = p_user_id
                     ORDER BY a.created_at DESC NULLS LAST, a.id DESC LIMIT 1)) AS l2,
               COALESCE(
                   p_l1,
                   (SELECT NULLIF(u.native_language_id, 0) FROM public.users u WHERE u.id = p_user_id),
                   2) AS l1
    ), att AS (
        SELECT DISTINCT a.test_id FROM public.test_attempts a
         WHERE a.user_id = p_user_id AND a.test_id IS NOT NULL
    ), subs AS (
        SELECT s.id, s.passage_id, s.created_at, s.reproduction, s.l1_language_id,
               s.skipped_at, g.created_at AS graded_at, g.overall_band
          FROM public.dt_submission s
          LEFT JOIN public.dt_grade g ON g.submission_id = s.id
         WHERE s.user_id = p_user_id
    ), hist AS (
        SELECT sb.passage_id,
               max(sb.created_at) AS last_served,
               bool_or(sb.graded_at IS NOT NULL) AS graded,
               max(sb.graded_at) AS last_graded_at,
               (array_agg(sb.overall_band ORDER BY sb.graded_at DESC NULLS LAST, sb.id DESC))[1] AS last_band,
               max(sb.id) FILTER (WHERE sb.graded_at IS NULL
                                    AND coalesce(sb.reproduction, '') = ''
                                    AND sb.l1_language_id = (SELECT l1 FROM lang)) AS open_id,
               -- skipped state of that same (newest) open submission
               (array_agg(sb.skipped_at IS NOT NULL ORDER BY sb.id DESC)
                    FILTER (WHERE sb.graded_at IS NULL
                              AND coalesce(sb.reproduction, '') = ''
                              AND sb.l1_language_id = (SELECT l1 FROM lang)))[1] AS open_skipped
          FROM subs sb
         GROUP BY sb.passage_id
    ), hp AS (
        SELECT h.*, p.l2_language_id, p.status, p.source_ref_id, p.sentence_start,
               p.sentence_end, p.age_tier
          FROM hist h JOIN public.dt_passage p ON p.id = h.passage_id
    ), salt AS (
        SELECT count(*) AS n FROM hist
    ), cand AS (
        SELECT t.id, t.transcript_hash, t.difficulty, t.language_id,
               (t.id IN (SELECT test_id FROM att)) AS attempted
          FROM public.tests t
         WHERE t.is_active
           AND t.language_id = (SELECT l2 FROM lang)
           AND EXISTS (
               SELECT 1 FROM public.test_sentences s
                 JOIN public.test_sentence_references r ON r.sentence_id = s.id
                WHERE s.test_id = t.id
                  AND r.l1_language_id = (SELECT l1 FROM lang)
                  AND r.is_active
                  AND r.review_verdict IN ('pass', 'rewritten'))
    ), elo AS (
        SELECT tsr.test_id,
               min(abs(tsr.elo_rating - COALESCE(usr.elo_rating, 1200))) AS elo_diff
          FROM public.test_skill_ratings tsr
          JOIN cand c ON c.id = tsr.test_id
          LEFT JOIN public.user_skill_ratings usr
                 ON usr.user_id = p_user_id
                AND usr.language_id = c.language_id
                AND usr.test_type_id = tsr.test_type_id
         WHERE tsr.elo_rating IS NOT NULL
         GROUP BY tsr.test_id
    ), sent AS (
        SELECT s.test_id, s.id, s.idx,
               (NULLIF(c.transcript_hash, '') IS NULL OR s.transcript_hash = c.transcript_hash) AS fresh,
               (r.sentence_id IS NOT NULL) AS ref_ok,
               r.tightness,
               (COALESCE(r.faithful_reviews, 0) >= 2) AS agreed,
               char_length(s.l2_text) AS chars
          FROM cand c
          JOIN public.test_sentences s ON s.test_id = c.id
          LEFT JOIN public.test_sentence_references r
                 ON r.sentence_id = s.id
                AND r.l1_language_id = (SELECT l1 FROM lang)
                AND r.is_active
                AND r.review_verdict IN ('pass', 'rewritten')
    ), served_idx AS (
        SELECT DISTINCT hp.source_ref_id AS test_id, gs.idx
          FROM hp, generate_series(hp.sentence_start::integer, hp.sentence_end::integer) AS gs(idx)
         WHERE hp.sentence_start IS NOT NULL AND hp.sentence_end IS NOT NULL
    ), ranked AS (
        SELECT c.id, c.attempted, e.elo_diff,
               encode(sha256(convert_to(p_user_id::text || '|' || c.id::text || '|'
                                        || (SELECT n FROM salt)::text, 'UTF8')), 'hex') AS rot
          FROM cand c
          LEFT JOIN elo e ON e.test_id = c.id
         WHERE (SELECT count(*) FROM sent s
                 WHERE s.test_id = c.id AND s.fresh AND s.ref_ok
                   AND NOT EXISTS (SELECT 1 FROM served_idx si
                                    WHERE si.test_id = c.id AND si.idx = s.idx)) >= 2
    ), prefetch AS (
        SELECT r.id FROM ranked r
         ORDER BY r.attempted DESC,
                  CASE WHEN r.attempted THEN NULL ELSE r.elo_diff END ASC NULLS LAST,
                  r.rot
         LIMIT 3
    )
    SELECT jsonb_build_object(
        'l1', (SELECT l1 FROM lang),
        'l2', (SELECT l2 FROM lang),
        'salt', (SELECT n FROM salt),
        'attempted', COALESCE((SELECT jsonb_agg(test_id) FROM att), '[]'::jsonb),
        'history', COALESCE((SELECT jsonb_agg(jsonb_build_object(
                     'p', hp.passage_id, 'ls', hp.last_served, 'g', hp.graded,
                     'lg', hp.last_graded_at, 'b', hp.last_band, 'o', hp.open_id,
                     'sk', COALESCE(hp.open_skipped, false),
                     'l2', hp.l2_language_id, 'st', hp.status, 't', hp.source_ref_id,
                     's', hp.sentence_start, 'e', hp.sentence_end, 'a', hp.age_tier))
                     FROM hp), '[]'::jsonb),
        'tests', COALESCE((SELECT jsonb_agg(jsonb_build_object(
                     'id', c.id, 'h', c.transcript_hash, 'd', c.difficulty,
                     'at', c.attempted, 'elo', e.elo_diff,
                     'rows', (SELECT jsonb_agg(jsonb_build_array(
                                  s.id, s.idx, s.fresh, s.ref_ok, round(s.tightness::numeric, 3), s.chars)
                                  ORDER BY s.idx)
                                FROM sent s WHERE s.test_id = c.id),
                     'ag', (SELECT jsonb_agg(s.idx ORDER BY s.idx)
                              FROM sent s
                             WHERE s.test_id = c.id AND s.fresh AND s.ref_ok AND s.agreed)))
                     FROM cand c LEFT JOIN elo e ON e.test_id = c.id), '[]'::jsonb),
        'ranges', COALESCE((SELECT jsonb_agg(jsonb_build_object(
                     'id', p.id, 't', p.source_ref_id, 's', p.sentence_start,
                     'e', p.sentence_end, 'st', p.status, 'a', p.age_tier))
                     FROM public.dt_passage p
                    WHERE p.source_ref_id IN (SELECT id FROM cand)
                      AND p.sentence_start IS NOT NULL
                      AND p.sentence_end IS NOT NULL), '[]'::jsonb),
        'texts', COALESCE((SELECT jsonb_agg(jsonb_build_array(s.id, s.l2_text, r.l1_text))
                     FROM public.test_sentences s
                     JOIN public.test_sentence_references r
                       ON r.sentence_id = s.id
                      AND r.l1_language_id = (SELECT l1 FROM lang)
                      AND r.is_active
                      AND r.review_verdict IN ('pass', 'rewritten')
                    WHERE s.test_id IN (SELECT id FROM prefetch)), '[]'::jsonb)
    )
$$;

REVOKE ALL ON FUNCTION public.dt_next_inputs(uuid, integer, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.dt_next_inputs(uuid, integer, integer) TO service_role;

COMMENT ON FUNCTION public.dt_next_inputs(uuid, integer, integer) IS
    'Read bundle for GET /api/dual-translation/next (TASK-990): served history, candidate '
    'passages, tests and sentence-window materials for one learner. Read-only; service_role only.';
