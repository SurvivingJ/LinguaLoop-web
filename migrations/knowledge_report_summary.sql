-- =============================================================================
-- Knowledge Report summary RPC (TASK-1036): knowledge_report_summary
-- Spec: wiki/features/knowledge-report.tech.md §2.2-§2.12, §6.1; ADR-051, ADR-052, ADR-053.
--
-- *** LIVE-DB: the OWNER applies this file to production. Agents never apply it.
-- *** Apply AFTER migrations/knowledge_calibration_inputs.sql (TASK-1079): the calibration block
-- *** embeds that function (TASK-1036 note of 2026-11-18), and this file refuses to load without it.
--
-- One read-only statement returning every aggregate the summary page and the nightly snapshot
-- job need for one (learner, language): tracked counts, evidence states, rated-known words,
-- idle, activity, missed recently and its flag, per-band measured counts, the calibration
-- inputs (knowledge_calibration_inputs + the p_cal_since sets), family sufficient statistics
-- and watchlist buckets. Exam-list buckets are NOT computed here (ADR-054): see
-- knowledge_list_buckets (TASK-1049).
--
-- Rules (tech section in brackets):
--   meaning = (vocab_id, sense_rank); primary row = latest last_evidence_at, then higher
--     evidence_count, then lower sense_id; counters summed over the meaning's rows      [2.2]
--   O = first-try exercise_attempts (any source) + word_quiz_results, <= p_as_of         [2.3]
--   latest outcome = row 1 of O per meaning by (at DESC, is_correct, ...): outcomes written in
--     one batch share created_at (intro drill formats), so on a tie a wrong outcome counts as
--     the latest one ("missed" if any outcome of the latest batch is wrong; spec gap, reported)
--   rated_known = (m.wc > m.ww AND m.p_last >= 0.75 AND NOT m.marked_unknown)              [2.4]
--   state: missed_last > rated_known > checked > not_checked                             [2.4]
--   idle: last_seen_at <= p_as_of - 60 days                                              [2.5]
--   activity d30 / d90 from O and from last_seen_at                                      [2.10]
--   families: non-intro first attempts in 90 days, n y m syy syn snn                     [2.11]
--   missed recently: latest O outcome wrong within 90 days; flag = >= 4 outcomes,
--     >= 3 wrong of the last 5 on >= 2 UTC dates                                         [2.12]
--   watchlist: active user_word_watchlist meanings bucketed by that meaning              [2.9]
-- The r / m / o / ol / os / wl / f / st CTE chain is byte-identical to the one in
-- migrations/knowledge_report_words.sql (tests/test_knowledge_report_migration.py checks it), so
-- the summary's state counts equal the words RPC's state filters.
-- No decay function, no level-tag column, no exercises.content (ADR-049), no MATERIALIZED CTE.
--
-- SIZE: catalog only (one function).
-- VERIFY (read-only, after apply): tests/sql/check_function_acls.sql empty;
--   SELECT knowledge_report_summary('de6fd05b-0871-45d4-a2d8-0195fdf5355e'::uuid, 3::smallint);
--   compare with TASK-1036's criteria (re-run tech Appendix B K2-K5 the same day).
-- Idempotent: CREATE OR REPLACE + repeatable REVOKE / GRANT.
-- Rollback: migrations/knowledge_report_summary_rollback.sql
-- =============================================================================

BEGIN;

DO $guard$
BEGIN
    IF to_regprocedure('public.knowledge_calibration_inputs(uuid, smallint, timestamptz, integer, smallint, uuid)') IS NULL THEN
        RAISE EXCEPTION 'knowledge_report_summary: apply migrations/knowledge_calibration_inputs.sql (TASK-1079) first';
    END IF;
END
$guard$;

CREATE OR REPLACE FUNCTION public.knowledge_report_summary(
    p_user_id uuid,
    p_language_id smallint,
    p_as_of timestamptz DEFAULT now(),
    p_window_days integer DEFAULT 180,
    p_cal_since timestamptz[] DEFAULT '{}')
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
WITH r AS (
    SELECT k.sense_id, k.p_known, k.status,
           coalesce(k.evidence_count, 0) AS evidence_count,
           coalesce(k.comprehension_correct, 0) AS cc, coalesce(k.comprehension_wrong, 0) AS cw,
           coalesce(k.word_test_correct, 0) AS wc, coalesce(k.word_test_wrong, 0) AS ww,
           k.last_evidence_at, k.created_at, s.vocab_id, s.sense_rank
      FROM user_vocabulary_knowledge k
      JOIN dim_word_senses s ON s.id = k.sense_id
     WHERE k.user_id = p_user_id AND k.language_id = p_language_id
), m AS (
    SELECT vocab_id, sense_rank,
           (array_agg(p_known ORDER BY last_evidence_at DESC NULLS LAST, evidence_count DESC, sense_id))[1] AS p_last,
           max(last_evidence_at) AS last_seen_at, min(created_at) AS first_seen_at,
           sum(cc) AS cc, sum(cw) AS cw, sum(wc) AS wc, sum(ww) AS ww,
           sum(evidence_count) AS evidence_events,
           bool_or(status = 'user_marked_unknown') AS marked_unknown,
           array_agg(sense_id ORDER BY sense_id) AS sense_ids
      FROM r
     GROUP BY vocab_id, sense_rank
), o AS (
    SELECT s.vocab_id, s.sense_rank, ea.created_at AS at, ea.is_correct,
           0 AS src, ea.id::text AS oid, ea.exercise_type AS etype, ea.exercise_id
      FROM exercise_attempts ea
      JOIN dim_word_senses s ON s.id = ea.sense_id
     WHERE ea.user_id = p_user_id AND ea.is_first_attempt AND s.word_language_id = p_language_id
       AND ea.created_at <= p_as_of
    UNION ALL
    SELECT s.vocab_id, s.sense_rank, w.created_at, w.is_correct,
           1, w.id::text, NULL::text, NULL::uuid
      FROM word_quiz_results w
      JOIN dim_word_senses s ON s.id = w.sense_id
     WHERE w.user_id = p_user_id AND s.word_language_id = p_language_id
       AND w.created_at <= p_as_of
), ol AS (
    SELECT o.*,
           row_number() OVER (PARTITION BY vocab_id, sense_rank ORDER BY at DESC, is_correct, src, oid) AS rn
      FROM o
), os AS (
    SELECT vocab_id, sense_rank,
           count(*) AS n_out,
           max(at) AS latest_at,
           bool_or(is_correct) FILTER (WHERE rn = 1) AS latest_correct,
           min(src) FILTER (WHERE rn = 1) AS latest_src,
           max(etype) FILTER (WHERE rn = 1) AS latest_etype,
           max(exercise_id::text) FILTER (WHERE rn = 1) AS latest_exercise_id,
           count(*) FILTER (WHERE rn <= 5) AS tries5,
           count(*) FILTER (WHERE rn <= 5 AND NOT is_correct) AS wrong5,
           count(DISTINCT (at AT TIME ZONE 'UTC')::date) FILTER (WHERE rn <= 5 AND NOT is_correct) AS days5,
           count(*) FILTER (WHERE NOT is_correct AND at > p_as_of - interval '90 days') AS misses_90
      FROM ol
     GROUP BY vocab_id, sense_rank
), wl AS (
    SELECT DISTINCT s.vocab_id, s.sense_rank
      FROM user_word_watchlist w
      JOIN dim_word_senses s ON s.id = w.sense_id
     WHERE w.user_id = p_user_id AND w.language_id = p_language_id AND w.active
), f AS (
    SELECT m.vocab_id, m.sense_rank, m.p_last, m.last_seen_at, m.first_seen_at,
           m.cc, m.cw, m.wc, m.ww, m.evidence_events, m.marked_unknown, m.sense_ids,
           v.lemma, v.lemma_traditional, v.reading, v.frequency_rank AS zipf,
           coalesce(calibration_zipf_band(v.frequency_rank), 0) AS band,
           (m.wc > m.ww AND m.p_last >= 0.75 AND NOT m.marked_unknown) AS rated_known,
           coalesce(os.n_out, 0) AS n_out,
           coalesce(NOT os.latest_correct, false) AS latest_wrong,
           os.latest_at, os.latest_correct, os.latest_src, os.latest_etype, os.latest_exercise_id,
           coalesce(os.tries5, 0) AS tries5, coalesce(os.wrong5, 0) AS wrong5,
           coalesce(os.days5, 0) AS days5, coalesce(os.misses_90, 0) AS misses_90,
           (wl.vocab_id IS NOT NULL) AS in_word_list
      FROM m
      JOIN dim_vocabulary v ON v.id = m.vocab_id
      LEFT JOIN os ON os.vocab_id = m.vocab_id AND os.sense_rank = m.sense_rank
      LEFT JOIN wl ON wl.vocab_id = m.vocab_id AND wl.sense_rank = m.sense_rank
), st AS (
    SELECT f.*,
           CASE WHEN f.latest_wrong THEN 'missed_last'
                WHEN f.rated_known THEN 'rated_known'
                WHEN f.wc + f.ww > 0 THEN 'checked'
                ELSE 'not_checked' END AS state,
           (f.latest_wrong AND f.latest_at > p_as_of - interval '90 days') AS missed_recent,
           (f.latest_wrong AND f.latest_at > p_as_of - interval '90 days'
            AND f.n_out >= 4 AND f.wrong5 >= 3 AND f.days5 >= 2) AS flagged
      FROM f
), ci AS (
    -- Calibration block (report §2.6 steps 1-4, placement §9/§14): D*, bands, alltime_n, dates,
    -- rated_known_in_frame come from the shared function so the placement result and the report agree.
    SELECT coalesce(knowledge_calibration_inputs(p_user_id, p_language_id, p_as_of, p_window_days,
                                                 NULL::smallint, NULL::uuid),
                    '{}'::jsonb) AS j
), cal AS (
    -- Legacy check answers for the p_cal_since sets (report §2.10 estimate comparison): definition
    -- mode, rank-1 anchors, answered in (p_as_of - p_window_days, p_as_of].
    SELECT cr.anchor_vocab_id AS v, cr.zipf_band AS band, cr.answered_at, cr.chosen_sense_id,
           cr.is_correct, cs.definition_language_id AS d
      FROM calibration_sessions cs
      JOIN calibration_responses cr ON cr.session_id = cs.id
      JOIN dim_word_senses a ON a.id = cr.anchor_sense_id AND a.sense_rank = 1
     WHERE cs.user_id = p_user_id AND cs.word_language_id = p_language_id AND cs.mode = 'definition'
       AND cr.answered_at IS NOT NULL AND cr.answered_at <= p_as_of
       AND cr.answered_at > p_as_of - make_interval(days => p_window_days)
), sl AS (
    -- since[i]: answers strictly after p_cal_since[i] with today's D*, latest answer per lemma
    -- (disjoint from a snapshot whose cal_last_answer_at = p_cal_since[i]).
    SELECT DISTINCT ON (u.ord, c.v) u.ord, c.v, c.band, c.answered_at, c.chosen_sense_id, c.is_correct
      FROM unnest(p_cal_since) WITH ORDINALITY AS u(ts, ord)
      JOIN cal c ON c.answered_at > u.ts
     WHERE c.d = (SELECT (ci.j->>'definition_language_id')::smallint FROM ci)
     ORDER BY u.ord, c.v, c.answered_at DESC
), fa AS (
    SELECT det.family, s.vocab_id, s.sense_rank,
           count(*) AS n, count(*) FILTER (WHERE ea.is_correct) AS y
      FROM exercise_attempts ea
      JOIN dim_word_senses s ON s.id = ea.sense_id
      JOIN dim_exercise_types det ON det.type_code = ea.exercise_type
     WHERE ea.user_id = p_user_id AND ea.is_first_attempt AND s.word_language_id = p_language_id
       AND coalesce(ea.source, 'practice') <> 'intro'
       AND ea.created_at > p_as_of - interval '90 days' AND ea.created_at <= p_as_of
     GROUP BY det.family, s.vocab_id, s.sense_rank
)
SELECT jsonb_build_object(
    'as_of', p_as_of,
    'language_id', p_language_id,
    'method_version', 1,
    'tracked', (SELECT jsonb_build_object('words', count(DISTINCT st.vocab_id),
                                          'meanings', count(*),
                                          'rows', (SELECT count(*) FROM r))
                  FROM st),
    'states', (SELECT jsonb_build_object(
                          'missed_last', count(*) FILTER (WHERE st.state = 'missed_last'),
                          'rated_known', count(*) FILTER (WHERE st.state = 'rated_known'),
                          'checked', count(*) FILTER (WHERE st.state = 'checked'),
                          'not_checked', count(*) FILTER (WHERE st.state = 'not_checked'))
                 FROM st),
    'rated_known_words', (SELECT count(DISTINCT st.vocab_id) FILTER (WHERE st.sense_rank = 1 AND st.rated_known)
                            FROM st),
    'rated_known_checked2_words', (SELECT count(DISTINCT st.vocab_id)
                                            FILTER (WHERE st.sense_rank = 1 AND st.rated_known AND st.wc >= 2)
                                     FROM st),
    'idle60_meanings', (SELECT count(*) FROM st WHERE st.last_seen_at <= p_as_of - interval '60 days'),
    'last_seen_at', (SELECT max(st.last_seen_at) FROM st),
    'activity', jsonb_build_object(
        'd30', (SELECT jsonb_build_object(
                           'practised_meanings', count(DISTINCT (o.vocab_id, o.sense_rank)),
                           'direct_outcomes', count(*),
                           'met_in_texts', (SELECT count(*) FROM st
                                             WHERE st.last_seen_at > p_as_of - interval '30 days'
                                               AND st.wc + st.ww = 0))
                  FROM o WHERE o.at > p_as_of - interval '30 days'),
        'd90', (SELECT jsonb_build_object(
                           'practised_meanings', count(DISTINCT (o.vocab_id, o.sense_rank)),
                           'direct_outcomes', count(*),
                           'met_in_texts', (SELECT count(*) FROM st
                                             WHERE st.last_seen_at > p_as_of - interval '90 days'
                                               AND st.wc + st.ww = 0))
                  FROM o WHERE o.at > p_as_of - interval '90 days')),
    'missed_recent', (SELECT jsonb_build_object('meanings', count(*) FILTER (WHERE st.missed_recent),
                                                'flagged', count(*) FILTER (WHERE st.flagged))
                        FROM st),
    'groups', (SELECT jsonb_agg(jsonb_build_object('band', x.b, 'tracked_words', x.tw,
                                                   'rated_known_words', x.rk) ORDER BY x.b)
                 FROM (SELECT g.b, count(DISTINCT st.vocab_id) AS tw,
                              count(DISTINCT st.vocab_id) FILTER (WHERE st.sense_rank = 1 AND st.rated_known) AS rk
                         FROM generate_series(0, 7) AS g(b)
                         LEFT JOIN st ON st.band = g.b
                        GROUP BY g.b) x),
    'calibration', (SELECT ci.j || jsonb_build_object(
                        'window_days', p_window_days,
                        'answers', (SELECT coalesce(sum((b.e->>0)::integer), 0)
                                      FROM jsonb_array_elements(coalesce(ci.j->'bands', '[]'::jsonb)) AS b(e)),
                        'first_answer_at', ci.j->'first_at',
                        'last_answer_at', ci.j->'last_at',
                        'since', coalesce((
                            SELECT jsonb_agg(jsonb_build_object(
                                       'since', u.ts,
                                       'bands', (SELECT jsonb_agg(jsonb_build_array(x.n, x.s, x.c) ORDER BY x.b)
                                                   FROM (SELECT g.b, count(sl.v) AS n,
                                                                count(sl.v) FILTER (WHERE sl.chosen_sense_id IS NULL) AS s,
                                                                count(sl.v) FILTER (WHERE sl.is_correct) AS c
                                                           FROM generate_series(1, 7) AS g(b)
                                                           LEFT JOIN sl ON sl.ord = u.ord AND sl.band = g.b
                                                          GROUP BY g.b) x),
                                       'first_answer_at', (SELECT min(sl.answered_at) FROM sl WHERE sl.ord = u.ord),
                                       'last_answer_at', (SELECT max(sl.answered_at) FROM sl WHERE sl.ord = u.ord))
                                   ORDER BY u.ord)
                              FROM unnest(p_cal_since) WITH ORDINALITY AS u(ts, ord)), '[]'::jsonb))
                      FROM ci),
    'families', coalesce((SELECT jsonb_agg(jsonb_build_object('family', x.family, 'n', x.n, 'y', x.y, 'm', x.m,
                                                               'syy', x.syy, 'syn', x.syn, 'snn', x.snn)
                                           ORDER BY x.family)
                            FROM (SELECT fa.family, sum(fa.n) AS n, sum(fa.y) AS y, count(*) AS m,
                                         sum(fa.y * fa.y) AS syy, sum(fa.y * fa.n) AS syn, sum(fa.n * fa.n) AS snn
                                    FROM fa GROUP BY fa.family) x),
                         '[]'::jsonb),
    'watchlist', (SELECT jsonb_build_object(
                             'items', count(*),
                             'rated_known', count(*) FILTER (WHERE st.rated_known),
                             'seen_not_rated', count(*) FILTER (WHERE st.vocab_id IS NOT NULL AND NOT st.rated_known),
                             'no_evidence', count(*) FILTER (WHERE st.vocab_id IS NULL))
                    FROM wl
                    LEFT JOIN st ON st.vocab_id = wl.vocab_id AND st.sense_rank = wl.sense_rank));
$$;

REVOKE ALL ON FUNCTION public.knowledge_report_summary(uuid, smallint, timestamptz, integer, timestamptz[])
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.knowledge_report_summary(uuid, smallint, timestamptz, integer, timestamptz[])
    TO service_role;

COMMENT ON FUNCTION public.knowledge_report_summary(uuid, smallint, timestamptz, integer, timestamptz[]) IS
    'Knowledge Report summary aggregates for one (learner, language) (TASK-1036, tech §6.1): tracked, '
    'states, rated-known words, idle, activity, missed recently, groups, calibration (embeds '
    'knowledge_calibration_inputs + since sets), families, watchlist. Read-only; service role only.';

NOTIFY pgrst, 'reload schema';

COMMIT;
