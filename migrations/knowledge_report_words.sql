-- =============================================================================
-- Knowledge Report words RPC (TASK-1044): knowledge_report_words
-- Spec: wiki/features/knowledge-report.tech.md §2.2-§2.5, §2.11 (family of one outcome), §2.12,
-- §6.1; ADR-052 (evidence first), ADR-054 (list filter arrives as vocab_ids).
--
-- *** LIVE-DB: the OWNER applies this file to production. Agents never apply it.
-- No dependency on other new objects (it can be applied any time after review).
--
-- One page of meanings (Pro table, Missed recently tab, export chunks) with evidence state and
-- evidence lead, filters, search, sorts, a 5-tuple keyset and page-only joins for gloss,
-- pronunciation, ladder and flashcards.
--   p_filters (all optional; Flask validates, SQL reads with casts):
--     states text[]        state codes; absent or empty = no filter
--     checked_several bool rated_known AND checks_correct >= 2          (true filters; false = off)
--     missed_recent bool   latest O outcome wrong within 90 days        (true filters; false = off)
--     idle_days int        last_seen_at <= p_as_of - idle_days days
--     bands int[]          coalesce(calibration_zipf_band(zipf), 0) in the array; empty = no filter
--     in_word_list bool    meaning in an active user_word_watchlist row (true filters; false = off)
--     vocab_ids int[]      lemma in the array AND sense_rank = 1; present (even empty) = filter
--     q text               already LIKE-escaped prefix: lemma, lemma_traditional, reading, or (zh,
--                          ASCII q) the toneless key of the native rank-1 pronunciation
--   p_sort: useful | recent | oldest | common | lemma | id | missed (unknown -> useful)
--     keyset (kt text COLLATE "C", k1 float8, k2 float8, vocab_id, sense_rank) ascending:
--       useful  ''      tier 0 missed_last, 1 checked, 2 not_checked, 3 rated_known   -coalesce(zipf, -1)
--       recent  ''      -epoch(last_seen_at)  (NULL -> 0)                             0
--       oldest  ''      epoch(last_seen_at)   (NULL -> 0)                             0
--       common  ''      -coalesce(zipf, -1)                                           0
--       lemma   lemma   0                                                             0
--       id      ''      0                                                             0
--       missed  ''      -misses_90 (Missed recently tab, §2.12)                       -epoch(latest outcome)
--   p_cursor: [kt, k1, k2, vocab_id, sense_rank] of the last row of the previous page (or NULL).
--   p_limit clamped to 1..1000; p_limit + 1 rows fetched to decide next_cursor.
-- Returns {"rows":[...], "next_cursor":[...]|null, "matching":int, "as_of":ts}. No numeric
-- p_known and no five-level label in the output (ADR-052); app_rates_known is a boolean.
-- Latest outcome of a meaning: O ordered by (at DESC, is_correct, ...); outcomes written in one
-- batch share created_at (intro drill formats), so on a tie a wrong outcome counts as the latest.
-- The r / m / o / ol / os / wl / f / st CTE chain is byte-identical to the one in
-- migrations/knowledge_report_summary.sql (checked by tests/test_knowledge_report_migration.py).
-- Reads exercises.exercise_type by primary key for the page rows only (never exercises.content,
-- which ADR-049 dropped). No decay function.
--
-- SIZE: catalog only (one function).
-- VERIFY (read-only, after apply): tests/sql/check_function_acls.sql empty; page de6fd05b/ja with
--   p_limit 50 for every sort and compare with TASK-1044's criteria.
-- Idempotent: CREATE OR REPLACE + repeatable REVOKE / GRANT.
-- Rollback: migrations/knowledge_report_words_rollback.sql
-- =============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.knowledge_report_words(
    p_user_id uuid,
    p_language_id smallint,
    p_definition_language_id smallint,
    p_filters jsonb DEFAULT '{}',
    p_sort text DEFAULT 'useful',
    p_cursor jsonb DEFAULT NULL,
    p_limit integer DEFAULT 50,
    p_as_of timestamptz DEFAULT now())
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
), prm AS (
    SELECT CASE WHEN p_sort IN ('useful', 'recent', 'oldest', 'common', 'lemma', 'id', 'missed')
                THEN p_sort ELSE 'useful' END AS sort,
           greatest(1, least(coalesce(p_limit, 50), 1000)) AS lim,
           coalesce(p_filters, '{}'::jsonb) AS fj
), flt AS (
    SELECT CASE WHEN jsonb_typeof(prm.fj->'states') = 'array' AND jsonb_array_length(prm.fj->'states') > 0
                THEN ARRAY(SELECT jsonb_array_elements_text(prm.fj->'states')) END AS states,
           coalesce(nullif(prm.fj->>'checked_several', '')::boolean, false) AS checked_several,
           coalesce(nullif(prm.fj->>'missed_recent', '')::boolean, false) AS missed_recent,
           nullif(prm.fj->>'idle_days', '')::integer AS idle_days,
           CASE WHEN jsonb_typeof(prm.fj->'bands') = 'array' AND jsonb_array_length(prm.fj->'bands') > 0
                THEN ARRAY(SELECT t.x::integer FROM jsonb_array_elements_text(prm.fj->'bands') AS t(x)) END AS bands,
           coalesce(nullif(prm.fj->>'in_word_list', '')::boolean, false) AS in_word_list,
           coalesce(jsonb_typeof(prm.fj->'vocab_ids') = 'array', false) AS has_vocab_ids,
           nullif(prm.fj->>'q', '') AS q,
           regexp_replace(lower(translate(split_part(coalesce(prm.fj->>'q', ''), ' (', 1),
                                          'āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü', 'aaaaeeeeiiiioooouuuuvvvvv')),
                          '[^a-z]', '', 'g') AS qkey
      FROM prm
), vs AS (
    SELECT DISTINCT t.x::integer AS vocab_id
      FROM prm
     CROSS JOIN jsonb_array_elements_text(CASE WHEN jsonb_typeof(prm.fj->'vocab_ids') = 'array'
                                               THEN prm.fj->'vocab_ids' ELSE '[]'::jsonb END) AS t(x)
), fr AS (
    SELECT st.*
      FROM st CROSS JOIN flt
     WHERE (flt.states IS NULL OR st.state = ANY (flt.states))
       AND (NOT flt.checked_several OR (st.rated_known AND st.wc >= 2))
       AND (NOT flt.missed_recent OR st.missed_recent)
       AND (flt.idle_days IS NULL OR st.last_seen_at <= p_as_of - make_interval(days => flt.idle_days))
       AND (flt.bands IS NULL OR st.band = ANY (flt.bands))
       AND (NOT flt.in_word_list OR st.in_word_list)
       AND (NOT flt.has_vocab_ids OR (st.sense_rank = 1 AND st.vocab_id IN (SELECT vs.vocab_id FROM vs)))
       AND (flt.q IS NULL
            OR st.lemma LIKE flt.q || '%' ESCAPE E'\\'
            OR st.lemma_traditional LIKE flt.q || '%' ESCAPE E'\\'
            OR st.reading LIKE flt.q || '%' ESCAPE E'\\'
            OR (p_language_id = 1 AND flt.q ~ '^[ -~]+$' AND flt.qkey <> ''
                AND EXISTS (
                    SELECT 1 FROM dim_word_senses ns
                     WHERE ns.vocab_id = st.vocab_id AND ns.definition_language_id = p_language_id
                       AND ns.definition_level = 'standard' AND ns.sense_rank = 1
                       AND regexp_replace(lower(translate(split_part(ns.pronunciation, ' (', 1),
                                                          'āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü', 'aaaaeeeeiiiioooouuuuvvvvv')),
                                          '[^a-z]', '', 'g') LIKE flt.qkey || '%')))
), keyed AS (
    SELECT fr.*,
           (CASE WHEN prm.sort = 'lemma' THEN fr.lemma ELSE '' END) COLLATE "C" AS kt,
           (CASE prm.sort
                WHEN 'useful' THEN CASE fr.state WHEN 'missed_last' THEN 0 WHEN 'checked' THEN 1
                                                 WHEN 'not_checked' THEN 2 ELSE 3 END
                WHEN 'recent' THEN -coalesce(extract(epoch FROM fr.last_seen_at)::float8, 0)
                WHEN 'oldest' THEN coalesce(extract(epoch FROM fr.last_seen_at)::float8, 0)
                WHEN 'common' THEN -coalesce(fr.zipf::float8, -1)
                WHEN 'missed' THEN -fr.misses_90
                ELSE 0 END)::float8 AS k1,
           (CASE prm.sort
                WHEN 'useful' THEN -coalesce(fr.zipf::float8, -1)
                WHEN 'missed' THEN -coalesce(extract(epoch FROM fr.latest_at)::float8, 0)
                ELSE 0 END)::float8 AS k2
      FROM fr CROSS JOIN prm
), cur AS (
    SELECT coalesce(jsonb_typeof(p_cursor) = 'array', false) AS has_cursor,
           CASE WHEN jsonb_typeof(p_cursor) = 'array' THEN p_cursor->>0 END AS c_kt,
           CASE WHEN jsonb_typeof(p_cursor) = 'array' THEN (p_cursor->>1)::float8 END AS c_k1,
           CASE WHEN jsonb_typeof(p_cursor) = 'array' THEN (p_cursor->>2)::float8 END AS c_k2,
           CASE WHEN jsonb_typeof(p_cursor) = 'array' THEN (p_cursor->>3)::integer END AS c_vocab_id,
           CASE WHEN jsonb_typeof(p_cursor) = 'array' THEN (p_cursor->>4)::integer END AS c_sense_rank
), pg AS (
    SELECT z.*, row_number() OVER (ORDER BY z.kt, z.k1, z.k2, z.vocab_id, z.sense_rank) AS pos
      FROM (SELECT keyed.*
              FROM keyed CROSS JOIN cur
             WHERE NOT cur.has_cursor
                OR (keyed.kt, keyed.k1, keyed.k2, keyed.vocab_id, keyed.sense_rank)
                   > (cur.c_kt, cur.c_k1, cur.c_k2, cur.c_vocab_id, cur.c_sense_rank)
             ORDER BY keyed.kt, keyed.k1, keyed.k2, keyed.vocab_id, keyed.sense_rank
             LIMIT (SELECT prm.lim + 1 FROM prm)) z
)
SELECT jsonb_build_object(
    'rows', coalesce((
        SELECT jsonb_agg(jsonb_build_object(
                   'vocab_id', pg.vocab_id,
                   'sense_rank', pg.sense_rank,
                   'lemma', pg.lemma,
                   'lemma_traditional', pg.lemma_traditional,
                   'reading', pg.reading,
                   'pronunciation', pr.pronunciation,
                   'gloss', gl.definition,
                   'gloss_language_id', gl.definition_language_id,
                   'zipf', pg.zipf,
                   'band', pg.band,
                   'state', pg.state,
                   'app_rates_known', pg.p_last >= 0.75,
                   'checks_correct', pg.wc,
                   'checks_wrong', pg.ww,
                   'tests_correct', pg.cc,
                   'tests_wrong', pg.cw,
                   'last_direct', CASE WHEN pg.latest_at IS NOT NULL THEN jsonb_build_object(
                       'at', pg.latest_at,
                       'correct', pg.latest_correct,
                       'family', CASE WHEN pg.latest_src = 1 THEN 'form_recognition'   -- word quiz
                                      ELSE coalesce(
                                          (SELECT det.family FROM dim_exercise_types det
                                            WHERE det.type_code = pg.latest_etype),
                                          CASE WHEN pg.latest_etype IN ('intro_def_mc', 'intro_rev_mc',
                                                                        'intro_read_typed', 'intro_read_typed2')
                                                    THEN 'form_recognition'
                                               WHEN pg.latest_etype = 'intro_cloze_mc' THEN 'meaning_recall'
                                               WHEN pg.latest_etype IN ('intro_cloze_typed', 'intro_recall_typed')
                                                    THEN 'form_production'
                                               WHEN pg.latest_etype IN ('intro_ex_use', 'intro_ex_judge')
                                                    THEN (SELECT det2.family
                                                            FROM exercises e
                                                            JOIN dim_exercise_types det2 ON det2.type_code = e.exercise_type
                                                           WHERE e.id = pg.latest_exercise_id::uuid)
                                          END,
                                          'unmapped') END) END,
                   'first_seen_at', pg.first_seen_at,
                   'last_seen_at', pg.last_seen_at,
                   'idle_days', CASE WHEN pg.last_seen_at IS NOT NULL
                                     THEN greatest(0, floor(extract(epoch FROM (p_as_of - pg.last_seen_at)) / 86400))::integer END,
                   'missed_recent', pg.missed_recent,
                   'missed_flag', CASE WHEN pg.flagged THEN jsonb_build_object(
                       'wrong', pg.wrong5, 'tries', pg.tries5, 'days', pg.days5) END,
                   'misses_90', pg.misses_90,
                   'ladder_ring', lad.current_ring,
                   'ladder_state', lad.word_state,
                   'flashcard_lapses', fc.lapses,
                   'in_word_list', pg.in_word_list)
               ORDER BY pg.pos)
          FROM pg
          CROSS JOIN prm
          LEFT JOIN LATERAL (
              -- gloss: L1 standard -> L1 simple -> native standard (uq_sense_def_level lookups)
              SELECT gs.definition, gs.definition_language_id
                FROM (VALUES (1, p_definition_language_id, 'standard'),
                             (2, p_definition_language_id, 'simple'),
                             (3, p_language_id, 'standard')) AS pri(o, d, lvl)
                JOIN dim_word_senses gs
                  ON gs.vocab_id = pg.vocab_id AND gs.definition_language_id = pri.d
                 AND gs.definition_level = pri.lvl AND gs.sense_rank = pg.sense_rank
               ORDER BY pri.o
               LIMIT 1) gl ON true
          LEFT JOIN LATERAL (
              SELECT ns.pronunciation
                FROM dim_word_senses ns
               WHERE ns.vocab_id = pg.vocab_id AND ns.definition_language_id = p_language_id
                 AND ns.definition_level = 'standard' AND ns.sense_rank = pg.sense_rank) pr ON true
          LEFT JOIN LATERAL (
              SELECT l.current_ring, l.word_state
                FROM user_word_ladder l
               WHERE l.user_id = p_user_id AND l.sense_id = ANY (pg.sense_ids)
               ORDER BY l.current_ring DESC, l.sense_id
               LIMIT 1) lad ON true
          LEFT JOIN LATERAL (
              SELECT max(uf.lapses) AS lapses
                FROM user_flashcards uf
               WHERE uf.user_id = p_user_id AND uf.sense_id = ANY (pg.sense_ids)) fc ON true
         WHERE pg.pos <= prm.lim), '[]'::jsonb),
    'next_cursor', (SELECT jsonb_build_array(pg.kt, pg.k1, pg.k2, pg.vocab_id, pg.sense_rank)
                      FROM pg CROSS JOIN prm
                     WHERE pg.pos = prm.lim
                       AND EXISTS (SELECT 1 FROM pg p2 WHERE p2.pos = prm.lim + 1)),
    'matching', (SELECT count(*) FROM fr),
    'as_of', p_as_of);
$$;

REVOKE ALL ON FUNCTION public.knowledge_report_words(uuid, smallint, smallint, jsonb, text, jsonb, integer, timestamptz)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.knowledge_report_words(uuid, smallint, smallint, jsonb, text, jsonb, integer, timestamptz)
    TO service_role;

COMMENT ON FUNCTION public.knowledge_report_words(uuid, smallint, smallint, jsonb, text, jsonb, integer, timestamptz) IS
    'Knowledge Report word table page (TASK-1044, tech §6.1): one keyset page of the learner''s meanings '
    'with evidence state and lead, filters, search and sorts; gloss, pronunciation, ladder and flashcards '
    'joined for page rows only. Read-only; service role only.';

NOTIFY pgrst, 'reload schema';

COMMIT;
