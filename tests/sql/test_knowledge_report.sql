-- =============================================================================
-- Knowledge Report database layer — SQL tests (TASK-1034, TASK-1036, TASK-1044)
-- =============================================================================
-- Rollback-only test: synthetic learners, assertions RAISE EXCEPTION, a clean run prints PASS
-- notices, everything is rolled back. It INSERTS synthetic rows (ids >= 9,000,000, users
-- kr000000-...), so run it on the local harness or a Supabase branch, NEVER on production.
--
-- Local harness (PostgreSQL 16; see tests/sql/fixtures/knowledge_report_tables.sql for the order):
--   PG_EXTRA="<abs>/tests/sql/fixtures/knowledge_report_tables.sql \
--             <abs>/migrations/knowledge_report_foundation.sql <abs>/migrations/reference_data_bucket.sql \
--             <abs>/tests/sql/fixtures/knowledge_calibration_inputs_stub.sql \
--             <abs>/migrations/knowledge_report_summary.sql <abs>/migrations/knowledge_report_words.sql" \
--     <harness>/pg.sh kr 55434 reset
--   psql -h /tmp -p 55434 -U postgres -v ON_ERROR_STOP=1 -f tests/sql/test_knowledge_report.sql
-- On a branch where TASK-1079 is applied, the real knowledge_calibration_inputs is used instead of
-- the stub; the calibration assertions below hold for learners without placement sessions.
--
-- Fixtures (as_of = 2026-11-19 12:00:00.123456+00):
--   learner A (ja): 14 meanings on 13 lemmas covering every rule of tech §2.2-§2.12, the
--     de6fd05b calibration band table of tech §2.6 (+ superseded, rank-2, out-of-window,
--     future, unanswered, other-D and pronunciation-mode noise), families, watchlist, ladder,
--     flashcards; learner B (ja) shares senses with A (isolation); learner C has nothing;
--     learner Z (zh) has 6 lemmas for search; Q, R, S only have check sessions (active pairs).
-- =============================================================================

BEGIN;

-- ---- helpers (pg_temp: dropped at ROLLBACK) -------------------------------------------
CREATE FUNCTION pg_temp.as_of() RETURNS timestamptz LANGUAGE sql IMMUTABLE AS
$$ SELECT '2026-11-19 12:00:00.123456+00'::timestamptz $$;
CREATE FUNCTION pg_temp.d(n numeric) RETURNS timestamptz LANGUAGE sql IMMUTABLE AS
$$ SELECT '2026-11-19 12:00:00.123456+00'::timestamptz - make_interval(secs => n * 86400) $$;
CREATE FUNCTION pg_temp.u(c text) RETURNS uuid LANGUAGE sql IMMUTABLE AS
$$ SELECT ('00000000-0000-4000-8000-0000000000' || c)::uuid $$;          -- u('0a') = learner A
CREATE FUNCTION pg_temp.eq(label text, got jsonb, want jsonb) RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
  IF got IS DISTINCT FROM want THEN
    RAISE EXCEPTION 'FAIL %: got %, want %', label, got, want;
  END IF;
  RAISE NOTICE 'PASS %', label;
END $f$;
CREATE FUNCTION pg_temp.ok(label text, cond boolean) RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
  IF cond IS NOT TRUE THEN RAISE EXCEPTION 'FAIL %', label; END IF;
  RAISE NOTICE 'PASS %', label;
END $f$;
-- every page of knowledge_report_words, following next_cursor; returns [[vocab_id, sense_rank], ...]
CREATE FUNCTION pg_temp.page_all(p_user uuid, p_lang smallint, p_def smallint, p_filters jsonb,
                                 p_sort text, p_lim int) RETURNS jsonb LANGUAGE plpgsql AS $f$
DECLARE cur jsonb := NULL; res jsonb; acc jsonb := '[]'; guard int := 0; n int;
BEGIN
  LOOP
    res := knowledge_report_words(p_user, p_lang, p_def, p_filters, p_sort, cur, p_lim, pg_temp.as_of());
    n := jsonb_array_length(res->'rows');
    IF n > p_lim THEN RAISE EXCEPTION 'FAIL page larger than limit (% > %)', n, p_lim; END IF;
    acc := acc || coalesce((SELECT jsonb_agg(jsonb_build_array(r->'vocab_id', r->'sense_rank') ORDER BY o)
                              FROM jsonb_array_elements(res->'rows') WITH ORDINALITY t(r, o)), '[]');
    cur := res->'next_cursor';
    EXIT WHEN cur IS NULL OR cur = 'null'::jsonb;
    IF n <> p_lim THEN RAISE EXCEPTION 'FAIL short page (%) with a next_cursor', n; END IF;
    guard := guard + 1;
    IF guard > 10000 THEN RAISE EXCEPTION 'FAIL paging does not terminate'; END IF;
  END LOOP;
  RETURN acc;
END $f$;
CREATE FUNCTION pg_temp.words(p_user uuid, p_lang smallint, p_filters jsonb DEFAULT '{}', p_sort text DEFAULT 'useful',
                              p_lim int DEFAULT 1000, p_def smallint DEFAULT 2::smallint) RETURNS jsonb LANGUAGE sql AS
$$ SELECT knowledge_report_words(p_user, p_lang, p_def, p_filters, p_sort, NULL, p_lim, pg_temp.as_of()) $$;
CREATE FUNCTION pg_temp.row_of(res jsonb, p_vocab int, p_rank int) RETURNS jsonb LANGUAGE sql AS
$$ SELECT r FROM jsonb_array_elements(res->'rows') r
    WHERE (r->>'vocab_id')::int = p_vocab AND (r->>'sense_rank')::int = p_rank $$;

-- ---- fixtures --------------------------------------------------------------------------
INSERT INTO public.users (id, email)
SELECT pg_temp.u(c), 'kr-' || c || '@example.invalid' FROM unnest(ARRAY['0a','0b','0c','0d','0e','0f','10']) c;
-- 0a = A, 0b = B, 0c = C (empty), 0d = Z (zh), 0e = Q, 0f = R, 10 = S

-- Learner vocabulary: ja lemmas V1..V14, V20 = 9000001..9000014, 9000020; zh Z1..Z6 = 9000101..9000106
INSERT INTO public.dim_vocabulary (id, language_id, lemma, frequency_rank, lemma_traditional, reading) VALUES
  (9000001, 3, 'krv01', 5.6, NULL, 'よみいち'), (9000002, 3, 'krv02', 4.7, NULL, NULL),
  (9000003, 3, 'krv03', 3.2, NULL, 'かんじ'),  (9000004, 3, 'krv04', 4.2, NULL, NULL),
  (9000005, 3, 'krv05', NULL, NULL, NULL),     (9000006, 3, 'krv06', 6.0, NULL, NULL),
  (9000007, 3, 'krv07', 3.7, NULL, NULL),      (9000008, 3, 'krv08', 5.1, NULL, NULL),
  (9000009, 3, 'krv09', 4.6, NULL, NULL),      (9000010, 3, 'krv10', 3.9, NULL, NULL),
  (9000011, 3, 'krv11', 4.4, NULL, NULL),      (9000012, 3, 'krv12', 3.1, NULL, NULL),
  (9000013, 3, 'krv13', 2.5, NULL, NULL),      (9000014, 3, 'krv14', 4.0, NULL, NULL),
  (9000020, 3, 'krv20', 3.0, NULL, NULL),
  (9000101, 1, 'kr你好', 5.0, NULL, NULL),     (9000102, 1, 'kr不错', 4.5, NULL, NULL),
  (9000103, 1, 'kr不过', 4.8, NULL, NULL),     (9000104, 1, 'kr你们', 5.2, 'kr你們', NULL),
  (9000105, 1, 'kra_b%c', 3.0, NULL, NULL),    (9000106, 1, 'kraXbc', 3.0, NULL, NULL);
-- Native standard senses: 9010000 + (v - 9000000) * 10 + rank
INSERT INTO public.dim_word_senses (id, vocab_id, definition_language_id, definition, pronunciation, sense_rank,
                                    definition_level, word_language_id)
SELECT 9010000 + (v - 9000000) * 10 + 1, v, 3, 'native ' || v, 'pron ' || v, 1, 'standard', 3
  FROM unnest(ARRAY[9000001,9000002,9000003,9000004,9000005,9000006,9000007,9000008,9000009,9000010,
                    9000011,9000012,9000013,9000014,9000020]) v;
INSERT INTO public.dim_word_senses (id, vocab_id, definition_language_id, definition, pronunciation, sense_rank,
                                    definition_level, word_language_id) VALUES
  (9010062, 9000006, 3, 'native 9000006 r2', 'pron r2', 2, 'standard', 3),
  (9020011, 9000001, 2, 'en std V1', NULL, 1, 'standard', 3),
  (9020021, 9000002, 2, 'en std V2', NULL, 1, 'standard', 3),
  (9020041, 9000004, 2, 'en std V4', NULL, 1, 'standard', 3),
  (9030031, 9000003, 2, 'en simple V3', NULL, 1, 'simple', 3),
  (9011011, 9000101, 1, 'zh 你好', 'nǐ hǎo (ni3 hao3)', 1, 'standard', 1),
  (9011021, 9000102, 1, 'zh 不错', 'bú cuò', 1, 'standard', 1),
  (9011031, 9000103, 1, 'zh 不过', 'búguò', 1, 'standard', 1),
  (9011041, 9000104, 1, 'zh 你们', 'nǐ men', 1, 'standard', 1),
  (9011051, 9000105, 1, 'zh a_b%c', NULL, 1, 'standard', 1),
  (9011061, 9000106, 1, 'zh aXbc', NULL, 1, 'standard', 1);

-- UVK rows (A unless noted). Columns: user, sense, lang, p, status, evidence, cc, cw, wc, ww, last_evidence_at, created_at
INSERT INTO public.user_vocabulary_knowledge (user_id, sense_id, language_id, p_known, status, evidence_count,
    comprehension_correct, comprehension_wrong, word_test_correct, word_test_wrong, last_evidence_at, created_at) VALUES
  (pg_temp.u('0a'), 9010011, 3, 0.90, 'known',               5, 1, 0, 2, 0, pg_temp.d(2),   pg_temp.d(50)),  -- V1 rated known, checked twice
  (pg_temp.u('0a'), 9020021, 3, 0.50, 'learning',            3, 0, 1, 1, 0, pg_temp.d(1),   pg_temp.d(30)),  -- V2 primary row (latest)
  (pg_temp.u('0a'), 9010021, 3, 0.95, 'known',               9, 2, 0, 1, 0, pg_temp.d(10),  pg_temp.d(40)),  -- V2 second row
  (pg_temp.u('0a'), 9010031, 3, 0.95, 'known',               4, 3, 0, 0, 0, pg_temp.d(5),   pg_temp.d(20)),  -- V3 tests only
  (pg_temp.u('0a'), 9010041, 3, 0.90, 'known',               6, 0, 0, 1, 0, pg_temp.d(1),   pg_temp.d(25)),  -- V4 latest outcome wrong
  (pg_temp.u('0a'), 9010051, 3, 0.80, 'user_marked_unknown', 3, 0, 0, 3, 0, pg_temp.d(70),  pg_temp.d(80)),  -- V5 marked unknown, idle, band 0
  (pg_temp.u('0a'), 9010061, 3, 0.30, 'encountered',         1, 1, 0, 0, 0, pg_temp.d(100), pg_temp.d(100)), -- V6 rank 1, idle
  (pg_temp.u('0a'), 9010062, 3, 0.90, 'known',               4, 0, 0, 2, 0, pg_temp.d(5),   pg_temp.d(60)),  -- V6 rank 2 rated known
  (pg_temp.u('0a'), 9010071, 3, 0.40, 'learning',            6, 0, 0, 1, 3, pg_temp.d(1),   pg_temp.d(15)),  -- V7 flagged
  (pg_temp.u('0a'), 9010081, 3, 0.20, 'learning',            2, 0, 0, 0, 1, pg_temp.d(100), pg_temp.d(120)), -- V8 missed > 90 days ago
  (pg_temp.u('0a'), 9010091, 3, 0.60, 'learning',            2, 0, 0, 0, 0, pg_temp.d(3),   pg_temp.d(3)),   -- V9 tied latest batch
  (pg_temp.u('0a'), 9010101, 3, 0.80, 'probably_known',      3, 0, 0, 1, 1, pg_temp.d(4),   pg_temp.d(45)),  -- V10 quiz last
  (pg_temp.u('0a'), 9010111, 3, 0.50, 'learning',            1, 0, 0, 0, 0, pg_temp.d(2),   pg_temp.d(2)),   -- V11 intro ex_use
  (pg_temp.u('0a'), 9010121, 3, 0.70, 'learning',            1, 0, 0, 0, 0, pg_temp.d(8),   pg_temp.d(8)),   -- V12 intro cloze typed
  (pg_temp.u('0a'), 9010131, 3, 0.50, 'encountered',         1, 0, 0, 0, 0, NULL,           pg_temp.d(9)),   -- V13 no last_evidence_at
  (pg_temp.u('0b'), 9010011, 3, 0.10, 'unknown',             5, 0, 0, 0, 5, pg_temp.d(1),   pg_temp.d(5)),   -- B on A's V1 sense
  (pg_temp.u('0d'), 9011011, 1, 0.50, 'learning',            1, 1, 0, 0, 0, pg_temp.d(1),   pg_temp.d(5)),
  (pg_temp.u('0d'), 9011021, 1, 0.50, 'learning',            1, 1, 0, 0, 0, pg_temp.d(2),   pg_temp.d(5)),
  (pg_temp.u('0d'), 9011031, 1, 0.50, 'learning',            1, 1, 0, 0, 0, pg_temp.d(3),   pg_temp.d(5)),
  (pg_temp.u('0d'), 9011041, 1, 0.50, 'learning',            1, 1, 0, 0, 0, pg_temp.d(4),   pg_temp.d(5)),
  (pg_temp.u('0d'), 9011051, 1, 0.50, 'learning',            1, 1, 0, 0, 0, pg_temp.d(5),   pg_temp.d(5)),
  (pg_temp.u('0d'), 9011061, 1, 0.50, 'learning',            1, 1, 0, 0, 0, pg_temp.d(6),   pg_temp.d(6));

INSERT INTO public.exercises (id, language_id, exercise_type, source_type, word_sense_id)
VALUES ('eeeeeeee-0000-4000-8000-000000000001', 3, 'synonym_antonym_match', 'vocabulary', 9010111);

-- First-try outcomes (O) and family attempts. Columns: user, sense, type, correct, at, first, source, exercise_id
INSERT INTO public.exercise_attempts (user_id, sense_id, exercise_type, is_correct, created_at, is_first_attempt, source, exercise_id) VALUES
  (pg_temp.u('0a'), 9010011, 'definition_match',        true,  pg_temp.d(3),   true,  NULL,       NULL),
  (pg_temp.u('0a'), 9010011, 'definition_match',        false, pg_temp.d(1),   false, NULL,       NULL),  -- not a first try
  (pg_temp.u('0a'), 9010011, 'definition_match',        false, pg_temp.d(-1),  true,  NULL,       NULL),  -- after as_of
  (pg_temp.u('0a'), 9010041, 'definition_match',        true,  pg_temp.d(20),  true,  NULL,       NULL),
  (pg_temp.u('0a'), 9010041, 'definition_match',        true,  pg_temp.d(12),  true,  NULL,       NULL),
  (pg_temp.u('0a'), 9010041, 'definition_match',        false, pg_temp.d(2),   true,  NULL,       NULL),
  (pg_temp.u('0a'), 9010071, 'intro_def_mc',            true,  pg_temp.d(10),  true,  'intro',    NULL),
  (pg_temp.u('0a'), 9010071, 'intro_def_mc',            false, pg_temp.d(6),   true,  'intro',    NULL),
  (pg_temp.u('0a'), 9010071, 'intro_def_mc',            false, pg_temp.d(5),   true,  'intro',    NULL),
  (pg_temp.u('0a'), 9010071, 'intro_def_mc',            false, pg_temp.d(1),   true,  'intro',    NULL),
  (pg_temp.u('0a'), 9010081, 'definition_match',        false, pg_temp.d(100), true,  NULL,       NULL),
  (pg_temp.u('0a'), 9010091, 'intro_read_typed',        true,  pg_temp.d(3),   true,  'intro',    NULL),  -- same timestamp:
  (pg_temp.u('0a'), 9010091, 'intro_cloze_mc',          false, pg_temp.d(3),   true,  'intro',    NULL),  -- wrong wins the tie
  (pg_temp.u('0a'), 9010101, 'semantic_discrimination', false, pg_temp.d(40),  true,  NULL,       NULL),
  (pg_temp.u('0a'), 9010111, 'intro_ex_use',            false, pg_temp.d(2),   true,  'intro',    'eeeeeeee-0000-4000-8000-000000000001'),
  (pg_temp.u('0a'), 9010121, 'intro_cloze_typed',       true,  pg_temp.d(8),   true,  'intro',    NULL),
  (pg_temp.u('0a'), 9010131, 'mystery_type',            true,  pg_temp.d(9),   true,  NULL,       NULL),
  (pg_temp.u('0a'), 9010141, 'definition_match',        true,  pg_temp.d(5),   true,  'prestudy', NULL),  -- V14: outcome, no UVK row
  (pg_temp.u('0a'), 9011011, 'definition_match',        false, pg_temp.d(2),   true,  NULL,       NULL),  -- zh sense: other language
  (pg_temp.u('0b'), 9010041, 'definition_match',        false, pg_temp.d(1),   true,  NULL,       NULL);  -- B
INSERT INTO public.word_quiz_results (user_id, sense_id, is_correct, created_at) VALUES
  (pg_temp.u('0a'), 9010101, true, pg_temp.d(4));

-- Watchlist (A, ja): V1 twice (two senses of one meaning), V2, V6 rank 2, V20 (no UVK row); V3 inactive; a zh row
INSERT INTO public.user_word_watchlist (user_id, sense_id, language_id, upload_batch_id, active) VALUES
  (pg_temp.u('0a'), 9010011, 3, gen_random_uuid(), true),
  (pg_temp.u('0a'), 9020011, 3, gen_random_uuid(), true),
  (pg_temp.u('0a'), 9020021, 3, gen_random_uuid(), true),
  (pg_temp.u('0a'), 9010062, 3, gen_random_uuid(), true),
  (pg_temp.u('0a'), 9010201, 3, gen_random_uuid(), true),
  (pg_temp.u('0a'), 9010031, 3, gen_random_uuid(), false),
  (pg_temp.u('0a'), 9011011, 1, gen_random_uuid(), true),
  (pg_temp.u('0b'), 9010031, 3, gen_random_uuid(), true);
-- Ladder and flashcards on V2's two senses (A) and on V2 for B (must not leak)
INSERT INTO public.user_word_ladder (user_id, sense_id, current_ring, word_state) VALUES
  (pg_temp.u('0a'), 9020021, 2, 'active'), (pg_temp.u('0a'), 9010021, 3, 'gated'), (pg_temp.u('0b'), 9010021, 4, 'mastered');
INSERT INTO public.user_flashcards (user_id, sense_id, language_id, lapses) VALUES
  (pg_temp.u('0a'), 9020021, 3, 1), (pg_temp.u('0a'), 9010021, 3, 4), (pg_temp.u('0b'), 9010021, 3, 9);

-- Calibration fixture for A (ja, D = en): the de6fd05b band table of tech §2.6.
-- Anchor lemmas: vocab 9100000 + b*100 + i, rank-1 sense 9200000 + b*100 + i, rank-2 sense 9300000 + b*100 + i
INSERT INTO public.dim_vocabulary (id, language_id, lemma)
SELECT 9100000 + b * 100 + i, 3, 'krcal_' || b || '_' || i FROM generate_series(1, 7) b, generate_series(1, 30) i;
INSERT INTO public.dim_word_senses (id, vocab_id, definition_language_id, definition, sense_rank, definition_level, word_language_id)
SELECT 9200000 + b * 100 + i, 9100000 + b * 100 + i, 2, 'cal def', 1, 'standard', 3 FROM generate_series(1, 7) b, generate_series(1, 30) i
UNION ALL
SELECT 9300000 + b * 100 + i, 9100000 + b * 100 + i, 2, 'cal def r2', 2, 'standard', 3 FROM generate_series(1, 7) b, generate_series(1, 30) i;
CREATE TEMP TABLE kr_fx (b int PRIMARY KEY, n int, s int, c int) ON COMMIT DROP;
INSERT INTO kr_fx VALUES (1,26,16,7), (2,23,16,5), (3,26,14,9), (4,24,12,9), (5,25,9,13), (6,25,8,15), (7,23,0,21);
-- latest answer of lemma (b, i): pg_temp.d(4 + (7b + i) % 62) minus i seconds
CREATE FUNCTION pg_temp.cal_at(b int, i int) RETURNS timestamptz LANGUAGE sql IMMUTABLE AS
$$ SELECT pg_temp.d(4 + (7 * b + i) % 62) - make_interval(secs => i) $$;
INSERT INTO public.calibration_sessions (id, user_id, word_language_id, definition_language_id, started_at, mode) VALUES
  ('cccccccc-0000-4000-8000-000000000001', pg_temp.u('0a'), 3, 2, pg_temp.d(300), 'definition'),
  ('cccccccc-0000-4000-8000-000000000002', pg_temp.u('0a'), 3, 1, pg_temp.d(10),  'definition'),    -- other D
  ('cccccccc-0000-4000-8000-000000000003', pg_temp.u('0a'), 3, 2, pg_temp.d(10),  'pronunciation'), -- other mode
  ('cccccccc-0000-4000-8000-000000000004', pg_temp.u('0e'), 1, 2, pg_temp.d(10),  'definition'),    -- Q: answer after since
  ('cccccccc-0000-4000-8000-000000000005', pg_temp.u('0f'), 2, 2, pg_temp.d(10),  'pronunciation'), -- R: pronunciation only
  ('cccccccc-0000-4000-8000-000000000006', pg_temp.u('10'), 2, 2, pg_temp.d(90),  'definition');    -- S: answer before since
INSERT INTO public.calibration_responses (session_id, user_id, anchor_sense_id, anchor_vocab_id, zipf_band,
                                          chosen_sense_id, is_correct, served_at, answered_at)
-- the counted latest answers: skips, then correct, then wrong
SELECT 'cccccccc-0000-4000-8000-000000000001'::uuid, pg_temp.u('0a'), 9200000 + f.b * 100 + i, 9100000 + f.b * 100 + i, f.b,
       CASE WHEN i <= f.s THEN NULL WHEN i <= f.s + f.c THEN 9200000 + f.b * 100 + i ELSE 9200000 + f.b * 100 + 30 END,
       (i > f.s AND i <= f.s + f.c), pg_temp.cal_at(f.b, i), pg_temp.cal_at(f.b, i)
  FROM kr_fx f, generate_series(1, f.n) i
UNION ALL  -- superseded earlier answers (opposite outcome, one day before the latest)
SELECT 'cccccccc-0000-4000-8000-000000000001'::uuid, pg_temp.u('0a'), 9200000 + f.b * 100 + i, 9100000 + f.b * 100 + i, f.b,
       9200000 + f.b * 100 + i, NOT (i > f.s AND i <= f.s + f.c),
       pg_temp.cal_at(f.b, i) - interval '1 day', pg_temp.cal_at(f.b, i) - interval '1 day'
  FROM kr_fx f, generate_series(1, 3) i
UNION ALL  -- later rank-2 anchors on the same lemmas: never counted, never supersede
SELECT 'cccccccc-0000-4000-8000-000000000001', pg_temp.u('0a'), 9300000 + f.b * 100 + i, 9100000 + f.b * 100 + i, f.b,
       9300000 + f.b * 100 + i, true, pg_temp.d(1), pg_temp.d(1)
  FROM kr_fx f, generate_series(1, 2) i
UNION ALL  -- three lemmas answered only 200 days ago (band 1): all-time counts only
SELECT 'cccccccc-0000-4000-8000-000000000001', pg_temp.u('0a'), 9200000 + 100 + i, 9100000 + 100 + i, 1,
       9200000 + 100 + i, true, pg_temp.d(200), pg_temp.d(200)
  FROM generate_series(27, 29) i
UNION ALL  -- after as_of; unanswered; other D; other mode
SELECT 'cccccccc-0000-4000-8000-000000000001', pg_temp.u('0a'), 9200701, 9100701, 7, NULL, false, pg_temp.d(-1), pg_temp.d(-1)
UNION ALL
SELECT 'cccccccc-0000-4000-8000-000000000001', pg_temp.u('0a'), 9200224, 9100224, 2, NULL, NULL, pg_temp.d(2), NULL
UNION ALL
SELECT 'cccccccc-0000-4000-8000-000000000002', pg_temp.u('0a'), 9200300 + i, 9100300 + i, 3, 9200300 + i, true, pg_temp.d(3), pg_temp.d(3)
  FROM generate_series(1, 5) i
UNION ALL
SELECT 'cccccccc-0000-4000-8000-000000000003', pg_temp.u('0a'), 9200425, 9100425, 4, 9200425, true, pg_temp.d(3), pg_temp.d(3)
UNION ALL
SELECT 'cccccccc-0000-4000-8000-000000000004', pg_temp.u('0e'), 9200101, 9100101, 1, 9200101, true, pg_temp.d(5), pg_temp.d(5)
UNION ALL
SELECT 'cccccccc-0000-4000-8000-000000000005', pg_temp.u('0f'), 9200102, 9100102, 1, 9200102, true, pg_temp.d(5), pg_temp.d(5)
UNION ALL
SELECT 'cccccccc-0000-4000-8000-000000000006', pg_temp.u('10'), 9200103, 9100103, 1, 9200103, true, pg_temp.d(90), pg_temp.d(90);

-- Frame: V1's en sense in the (3, 2) pool (rated_known_in_frame = 1); a synthetic (2, 3) pool for the frame test
INSERT INTO public.calibration_anchor_pool (word_language_id, definition_language_id, sense_id, vocab_id, lemma,
                                            zipf, zipf_band, has_embedding, has_pronunciation)
VALUES (3, 2, 9020011, 9000001, 'krv01', 5.6, 7, true, false);
INSERT INTO public.dim_vocabulary (id, language_id, lemma)
SELECT 9000200 + i, 2, 'krframe' || i FROM generate_series(1, 6) i;
INSERT INTO public.dim_word_senses (id, vocab_id, definition_language_id, definition, sense_rank, definition_level, word_language_id) VALUES
  (9040001, 9000201, 3, 'f1', 1, 'standard', 2),
  (9040002, 9000202, 3, 'f2', 1, 'standard', 2), (9040012, 9000202, 3, 'f2 simple', 1, 'simple', 2),
  (9040003, 9000203, 3, 'f3 rank 2', 2, 'standard', 2),
  (9040004, 9000204, 3, 'f4', 1, 'standard', 2), (9040005, 9000205, 3, 'f5', 1, 'standard', 2),
  (9040006, 9000206, 3, 'f6', 1, 'standard', 2);
INSERT INTO public.calibration_anchor_pool (word_language_id, definition_language_id, sense_id, vocab_id, lemma,
                                            zipf, zipf_band, has_embedding, has_pronunciation) VALUES
  (2, 3, 9040001, 9000201, 'krframe1', 2.0, 1, true,  false),   -- counted
  (2, 3, 9040002, 9000202, 'krframe2', 2.0, 1, true,  false),   -- counted once (two rank-1 senses)
  (2, 3, 9040012, 9000202, 'krframe2', 2.0, 1, true,  false),
  (2, 3, 9040003, 9000203, 'krframe3', 3.2, 2, true,  false),   -- rank 2: excluded
  (2, 3, 9040004, 9000204, 'krframe4', 3.7, 3, false, false),   -- no embedding: excluded
  (2, 3, 9040005, 9000205, 'krframe5', 3.7, 3, true,  false),   -- blocklisted: excluded
  (2, 3, 9040006, 9000206, 'krframe6', 6.0, 7, true,  false);   -- counted
INSERT INTO public.calibration_anchor_blocklist (sense_id, reason) VALUES (9040005, 'kr test');

-- ---- 1. TASK-1034: catalog, security, table constraints --------------------------------
DO $t$
DECLARE fn text;
BEGIN
  FOREACH fn IN ARRAY ARRAY[
      'public.knowledge_frame_bands()', 'public.knowledge_active_pairs(timestamptz)',
      'public.knowledge_snapshots_prune(integer)',
      'public.knowledge_report_summary(uuid, smallint, timestamptz, integer, timestamptz[])',
      'public.knowledge_report_words(uuid, smallint, smallint, jsonb, text, jsonb, integer, timestamptz)'] LOOP
    PERFORM pg_temp.ok(fn || ' not executable by anon/authenticated/PUBLIC',
      NOT has_function_privilege('anon', fn::regprocedure, 'EXECUTE')
      AND NOT has_function_privilege('authenticated', fn::regprocedure, 'EXECUTE')
      AND NOT EXISTS (SELECT 1 FROM pg_proc p, aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) a
                       WHERE p.oid = fn::regprocedure AND a.grantee = 0 AND a.privilege_type = 'EXECUTE'));
    PERFORM pg_temp.ok(fn || ' executable by service_role', has_function_privilege('service_role', fn::regprocedure, 'EXECUTE'));
    PERFORM pg_temp.ok(fn || ' SECURITY INVOKER + pinned search_path',
      (SELECT NOT p.prosecdef AND p.proconfig @> ARRAY['search_path=public, pg_temp'] FROM pg_proc p WHERE p.oid = fn::regprocedure));
  END LOOP;
  PERFORM pg_temp.eq('volatility', (SELECT jsonb_object_agg(p.proname, p.provolatile::text || '/' || l.lanname)
                                      FROM pg_proc p JOIN pg_language l ON l.oid = p.prolang
                                     WHERE p.pronamespace = 'public'::regnamespace
                                       AND p.proname IN ('knowledge_frame_bands', 'knowledge_active_pairs', 'knowledge_snapshots_prune',
                                                         'knowledge_report_summary', 'knowledge_report_words')),
    '{"knowledge_frame_bands":"s/sql","knowledge_active_pairs":"s/sql","knowledge_snapshots_prune":"v/plpgsql",
      "knowledge_report_summary":"s/sql","knowledge_report_words":"s/sql"}');
  PERFORM pg_temp.ok('snapshots: RLS on, no policy',
    (SELECT relrowsecurity FROM pg_class WHERE oid = 'public.user_knowledge_snapshots'::regclass)
    AND NOT EXISTS (SELECT 1 FROM pg_policy WHERE polrelid = 'public.user_knowledge_snapshots'::regclass));
  PERFORM pg_temp.ok('snapshots: no client privilege',
    NOT has_table_privilege('anon', 'public.user_knowledge_snapshots', 'SELECT, INSERT, UPDATE, DELETE')
    AND NOT has_table_privilege('authenticated', 'public.user_knowledge_snapshots', 'SELECT, INSERT, UPDATE, DELETE'));
  PERFORM pg_temp.ok('snapshots: service_role reads and writes',
    has_table_privilege('service_role', 'public.user_knowledge_snapshots', 'SELECT')
    AND has_table_privilege('service_role', 'public.user_knowledge_snapshots', 'INSERT')
    AND has_table_privilege('service_role', 'public.user_knowledge_snapshots', 'UPDATE')
    AND has_table_privilege('service_role', 'public.user_knowledge_snapshots', 'DELETE'));
  PERFORM pg_temp.eq('snapshots: primary key',
    to_jsonb((SELECT pg_get_constraintdef(oid) FROM pg_constraint
               WHERE conrelid = 'public.user_knowledge_snapshots'::regclass AND contype = 'p')),
    '"PRIMARY KEY (user_id, language_id, snapshot_date)"');
  PERFORM pg_temp.eq('snapshots: foreign keys',
    (SELECT jsonb_agg(pg_get_constraintdef(oid) ORDER BY pg_get_constraintdef(oid)) FROM pg_constraint
      WHERE conrelid = 'public.user_knowledge_snapshots'::regclass AND contype = 'f'),
    '["FOREIGN KEY (cal_definition_language_id) REFERENCES dim_languages(id)", "FOREIGN KEY (language_id) REFERENCES dim_languages(id)", "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"]');
  PERFORM pg_temp.eq('snapshots: 24 columns',
    (SELECT to_jsonb(count(*)) FROM pg_attribute WHERE attrelid = 'public.user_knowledge_snapshots'::regclass
        AND attnum > 0 AND NOT attisdropped), '24');
  PERFORM pg_temp.eq('bucket row',
    (SELECT jsonb_build_object('id', id, 'name', name, 'public', public, 'limit', file_size_limit, 'mime', allowed_mime_types)
       FROM storage.buckets WHERE id = 'reference-data'),
    '{"id":"reference-data","name":"reference-data","public":false,"limit":5242880,"mime":["application/json"]}');
END $t$;

-- table CHECKs, PK and FK
DO $t$
DECLARE st text; r record;
BEGIN
  INSERT INTO public.user_knowledge_snapshots (user_id, language_id, snapshot_date, tracked_words, tracked_meanings,
      rated_known_words, checked_meanings, missed_recent_meanings, idle60_meanings, practised_30_meanings, direct_checks_30,
      cal_definition_language_id, cal_bands, frame_bands, cal_answers, est_kind, est_lo, est_hi, est_label)
  VALUES (pg_temp.u('0a'), 3, '2026-11-19', 251, 251, 69, 109, 10, 95, 41, 164, 2,
          ARRAY[26,23,26,24,25,25,23,16,16,14,12,9,8,0,7,5,9,9,13,15,21]::smallint[],
          ARRAY[577,425,621,655,537,283,77], 172, 1, 850, 1400, 2);
  SELECT method_version, source, computed_at IS NOT NULL AS has_ts INTO r FROM public.user_knowledge_snapshots
   WHERE user_id = pg_temp.u('0a') AND snapshot_date = '2026-11-19';
  PERFORM pg_temp.eq('snapshot defaults', jsonb_build_object('m', r.method_version, 's', r.source, 't', r.has_ts),
                     '{"m":1,"s":"nightly","t":true}');
  FOR r IN SELECT * FROM (VALUES
      ('cal_bands of 20',   'cal_bands = ARRAY[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]::smallint[]', '23514'),
      ('frame_bands of 8',  'frame_bands = ARRAY[1,2,3,4,5,6,7,8]', '23514'),
      ('est_kind 3',        'est_kind = 3', '23514'),
      ('est_label 0',       'est_label = 0', '23514'),
      ('source other',      'source = ''other''', '23514'),
      ('bad D*',            'cal_definition_language_id = 99', '23503')) v(label, setc, code) LOOP
    BEGIN
      EXECUTE 'UPDATE public.user_knowledge_snapshots SET ' || r.setc || ' WHERE user_id = $1' USING pg_temp.u('0a');
      RAISE EXCEPTION 'FAIL % accepted', r.label;
    EXCEPTION WHEN others THEN
      GET STACKED DIAGNOSTICS st = RETURNED_SQLSTATE;
      IF st <> r.code THEN RAISE EXCEPTION 'FAIL % raised % (want %)', r.label, st, r.code; END IF;
      RAISE NOTICE 'PASS snapshot rejects %', r.label;
    END;
  END LOOP;
  BEGIN
    INSERT INTO public.user_knowledge_snapshots (user_id, language_id, snapshot_date, tracked_words, tracked_meanings,
        rated_known_words, checked_meanings, missed_recent_meanings, idle60_meanings, practised_30_meanings, direct_checks_30)
    VALUES (pg_temp.u('0a'), 3, '2026-11-19', 0, 0, 0, 0, 0, 0, 0, 0);
    RAISE EXCEPTION 'FAIL duplicate snapshot accepted';
  EXCEPTION WHEN unique_violation THEN RAISE NOTICE 'PASS snapshot primary key';
  END;
  BEGIN
    INSERT INTO public.user_knowledge_snapshots (user_id, language_id, snapshot_date, tracked_words, tracked_meanings,
        rated_known_words, checked_meanings, missed_recent_meanings, idle60_meanings, practised_30_meanings, direct_checks_30)
    VALUES (gen_random_uuid(), 3, '2026-11-19', 0, 0, 0, 0, 0, 0, 0, 0);
    RAISE EXCEPTION 'FAIL snapshot for an unknown user accepted';
  EXCEPTION WHEN foreign_key_violation THEN RAISE NOTICE 'PASS snapshot user foreign key';
  END;
  DELETE FROM public.user_knowledge_snapshots WHERE user_id = pg_temp.u('0a');
END $t$;

-- ---- 2. TASK-1034: frame, active pairs, prune ------------------------------------------
SELECT pg_temp.eq('frame 2:3 (rank 1, embedding, blocklist, distinct lemmas, missing bands 0)',
                  knowledge_frame_bands()->'2:3', '[2,0,0,0,0,0,1]');
SELECT pg_temp.eq('frame equals the spec SQL for every pair',
  knowledge_frame_bands(),
  (SELECT jsonb_object_agg(k, arr) FROM (
     SELECT l || ':' || d AS k, jsonb_agg(coalesce(n, 0) ORDER BY b) AS arr
       FROM (SELECT DISTINCT word_language_id l, definition_language_id d FROM calibration_anchor_pool) pr
       CROSS JOIN generate_series(1, 7) b
       LEFT JOIN LATERAL (
         SELECT count(DISTINCT p.vocab_id) n FROM calibration_anchor_pool p JOIN dim_word_senses s ON s.id = p.sense_id
          WHERE s.sense_rank = 1 AND p.has_embedding AND p.word_language_id = pr.l AND p.definition_language_id = pr.d
            AND p.zipf_band = b AND p.sense_id NOT IN (SELECT sense_id FROM calibration_anchor_blocklist)) c ON true
      GROUP BY l, d
     HAVING sum(n) > 0) x));

SELECT pg_temp.ok('active pairs: UVK pairs and definition answers after since, once each',
  (SELECT bool_and(want <@ got AND NOT (got @> '[{"user_id":"00000000-0000-4000-8000-00000000000f"}]')
                               AND NOT (got @> '[{"user_id":"00000000-0000-4000-8000-000000000010"}]')
                               AND NOT (got @> '[{"user_id":"00000000-0000-4000-8000-00000000000c"}]'))
     FROM (SELECT knowledge_active_pairs(pg_temp.d(30)) AS got) g,
          unnest(ARRAY['[{"user_id":"00000000-0000-4000-8000-00000000000a","language_id":3}]',
                       '[{"user_id":"00000000-0000-4000-8000-00000000000b","language_id":3}]',
                       '[{"user_id":"00000000-0000-4000-8000-00000000000d","language_id":1}]',
                       '[{"user_id":"00000000-0000-4000-8000-00000000000e","language_id":1}]']::jsonb[]) want));
SELECT pg_temp.ok('active pairs: no duplicate pair',
  (SELECT count(*) = count(DISTINCT e) FROM jsonb_array_elements(knowledge_active_pairs(pg_temp.d(400))) e));
SELECT pg_temp.ok('active pairs: NULL since adds no check-only pair',
  NOT (knowledge_active_pairs(NULL) @> '[{"user_id":"00000000-0000-4000-8000-00000000000e"}]'));

DO $t$
DECLARE today date := (now() AT TIME ZONE 'UTC')::date; mon date; n int; st text;
BEGIN
  mon := today - 200 - (extract(isodow FROM today - 200)::int - 1);       -- a Monday at least 200 days ago
  INSERT INTO public.user_knowledge_snapshots (user_id, language_id, snapshot_date, tracked_words, tracked_meanings,
      rated_known_words, checked_meanings, missed_recent_meanings, idle60_meanings, practised_30_meanings, direct_checks_30)
  SELECT pg_temp.u('0a'), 3, dt, 0, 0, 0, 0, 0, 0, 0, 0
    FROM unnest(ARRAY[mon, mon + 1, today - 121, today - 120, today - 5]) dt
   WHERE dt = mon OR extract(isodow FROM dt) <> 1 OR dt = today - 5;
  n := knowledge_snapshots_prune(120);
  PERFORM pg_temp.eq('prune(120) deletes old non-Monday rows only', to_jsonb(n),
    to_jsonb((SELECT count(*) FROM unnest(ARRAY[mon + 1, today - 121]) dt WHERE extract(isodow FROM dt) <> 1)));
  PERFORM pg_temp.ok('prune keeps the old Monday, the 120-day boundary and recent rows',
    (SELECT array_agg(snapshot_date ORDER BY snapshot_date) FROM public.user_knowledge_snapshots WHERE user_id = pg_temp.u('0a'))
      @> ARRAY[mon, today - 5]
    AND NOT EXISTS (SELECT 1 FROM public.user_knowledge_snapshots
                     WHERE snapshot_date < today - 120 AND extract(isodow FROM snapshot_date) <> 1));
  PERFORM pg_temp.eq('prune default is 120', to_jsonb(knowledge_snapshots_prune()), '0');
  FOREACH n IN ARRAY ARRAY[34, NULL] LOOP
    BEGIN
      PERFORM knowledge_snapshots_prune(n);
      RAISE EXCEPTION 'FAIL prune(%) accepted', n;
    EXCEPTION WHEN invalid_parameter_value THEN
      GET STACKED DIAGNOSTICS st = MESSAGE_TEXT;
      PERFORM pg_temp.eq('prune(' || coalesce(n::text, 'NULL') || ') raises', to_jsonb(st), '"keep_daily_days_too_small"');
    END;
  END LOOP;
  PERFORM pg_temp.eq('prune(35) is allowed', to_jsonb(knowledge_snapshots_prune(35) >= 0), 'true');
  DELETE FROM public.user_knowledge_snapshots WHERE user_id = pg_temp.u('0a');
END $t$;

-- ---- 3. TASK-1036: knowledge_report_summary --------------------------------------------
CREATE TEMP TABLE kr_sum ON COMMIT DROP AS
SELECT knowledge_report_summary(pg_temp.u('0a'), 3::smallint, pg_temp.as_of(), 180,
                                ARRAY[pg_temp.d(30), pg_temp.d(400)]) AS j;
SELECT pg_temp.eq('summary header', (SELECT jsonb_build_object('a', j->'as_of', 'l', j->'language_id', 'm', j->'method_version') FROM kr_sum),
                  jsonb_build_object('a', pg_temp.as_of(), 'l', 3, 'm', 1));
SELECT pg_temp.eq('summary keys (no lists key)', (SELECT jsonb_agg(k ORDER BY k COLLATE "C") FROM kr_sum, jsonb_object_keys(j) k),
  '["activity","as_of","calibration","families","groups","idle60_meanings","language_id","last_seen_at","method_version",
    "missed_recent","rated_known_checked2_words","rated_known_words","states","tracked","watchlist"]');
SELECT pg_temp.eq('tracked (rows, meanings, words) §2.1-§2.2', (SELECT j->'tracked' FROM kr_sum),
                  '{"rows":15,"meanings":14,"words":13}');
SELECT pg_temp.eq('states §2.4 (primary row, marked unknown, rank 2, tie -> wrong)', (SELECT j->'states' FROM kr_sum),
                  '{"missed_last":5,"rated_known":2,"checked":3,"not_checked":4}');
SELECT pg_temp.eq('rated known words (rank 1 only) and checked twice §2.4',
  (SELECT jsonb_build_array(j->'rated_known_words', j->'rated_known_checked2_words') FROM kr_sum), '[2,1]');
SELECT pg_temp.eq('idle60 §2.5', (SELECT j->'idle60_meanings' FROM kr_sum), '3');
SELECT pg_temp.eq('last_seen_at', (SELECT j->'last_seen_at' FROM kr_sum), to_jsonb(pg_temp.d(1)));
SELECT pg_temp.eq('activity §2.10 (first tries, <= as_of, language, quiz)', (SELECT j->'activity' FROM kr_sum),
  '{"d30":{"practised_meanings":9,"direct_outcomes":15,"met_in_texts":4},"d90":{"practised_meanings":9,"direct_outcomes":16,"met_in_texts":4}}');
SELECT pg_temp.eq('missed recently and flag §2.12', (SELECT j->'missed_recent' FROM kr_sum), '{"meanings":4,"flagged":1}');
SELECT pg_temp.eq('groups by band 0..7', (SELECT j->'groups' FROM kr_sum),
  '[{"band":0,"tracked_words":1,"rated_known_words":0},{"band":1,"tracked_words":1,"rated_known_words":0},
    {"band":2,"tracked_words":2,"rated_known_words":0},{"band":3,"tracked_words":2,"rated_known_words":0},
    {"band":4,"tracked_words":2,"rated_known_words":1},{"band":5,"tracked_words":2,"rated_known_words":0},
    {"band":6,"tracked_words":1,"rated_known_words":0},{"band":7,"tracked_words":2,"rated_known_words":1}]');
SELECT pg_temp.eq('families §2.11 (non-intro first tries, 90 days, sufficient statistics)', (SELECT j->'families' FROM kr_sum),
  '[{"family":"form_recognition","n":5,"y":4,"m":3,"syy":6,"syn":8,"snn":11},
    {"family":"semantic_discrimination","n":1,"y":0,"m":1,"syy":0,"syn":0,"snn":1}]');
SELECT pg_temp.eq('watchlist §2.9', (SELECT j->'watchlist' FROM kr_sum),
                  '{"items":4,"rated_known":2,"seen_not_rated":1,"no_evidence":1}');
SELECT pg_temp.eq('calibration: de6fd05b band table of tech §2.6', (SELECT j->'calibration'->'bands' FROM kr_sum),
                  '[[26,16,7],[23,16,5],[26,14,9],[24,12,9],[25,9,13],[25,8,15],[23,0,21]]');
SELECT pg_temp.eq('calibration: D*, answers, window, all-time n, rated known in frame',
  (SELECT jsonb_build_object('d', j->'calibration'->'definition_language_id', 'a', j->'calibration'->'answers',
                             'w', j->'calibration'->'window_days', 'n', j->'calibration'->'alltime_n',
                             'f', j->'calibration'->'rated_known_in_frame') FROM kr_sum),
  '{"d":2,"a":172,"w":180,"n":[29,23,26,24,25,25,23],"f":1}');
SELECT pg_temp.eq('calibration: first and last answer of the counted set',
  (SELECT jsonb_build_array(j->'calibration'->'first_answer_at', j->'calibration'->'last_answer_at',
                            j->'calibration'->'first_at', j->'calibration'->'last_at') FROM kr_sum),
  (SELECT jsonb_build_array(min(t), max(t), min(t), max(t))
     FROM (SELECT pg_temp.cal_at(f.b, i) t FROM kr_fx f, generate_series(1, f.n) i) x));
SELECT pg_temp.eq('calibration: embeds the knowledge_calibration_inputs keys',
  (SELECT jsonb_agg(k ORDER BY k COLLATE "C") FROM kr_sum, jsonb_object_keys(j->'calibration') k),
  '["alltime_n","answers","bands","definition_language_id","first_answer_at","first_at","gap","instrument","last_answer_at",
    "last_at","pairs","placement_eligible","rated_known_in_frame","since","stop_reasons","window_days"]');
SELECT pg_temp.eq('since[1]: latest answers after p_cal_since[1] only',
  (SELECT j->'calibration'->'since'->0 FROM kr_sum),
  (SELECT jsonb_build_object('since', pg_temp.d(30),
            'bands', jsonb_agg(jsonb_build_array(n, s, c) ORDER BY b),
            'first_answer_at', (SELECT min(pg_temp.cal_at(f.b, i)) FROM kr_fx f, generate_series(1, f.n) i WHERE pg_temp.cal_at(f.b, i) > pg_temp.d(30)),
            'last_answer_at', (SELECT max(pg_temp.cal_at(f.b, i)) FROM kr_fx f, generate_series(1, f.n) i WHERE pg_temp.cal_at(f.b, i) > pg_temp.d(30)))
     FROM (SELECT f.b, count(i) n, count(i) FILTER (WHERE i <= f.s) s, count(i) FILTER (WHERE i > f.s AND i <= f.s + f.c) c
             FROM kr_fx f LEFT JOIN generate_series(1, 30) i ON i <= f.n AND pg_temp.cal_at(f.b, i) > pg_temp.d(30)
            GROUP BY f.b) x));
SELECT pg_temp.eq('since[2]: older than the window -> the window set',
  (SELECT j->'calibration'->'since'->1->'bands' FROM kr_sum), (SELECT j->'calibration'->'bands' FROM kr_sum));

SELECT pg_temp.eq('isolation: B sees only B',
  (SELECT jsonb_build_array(s->'tracked', s->'states', s->'watchlist'->'items', s->'activity'->'d30'->'direct_outcomes')
     FROM (SELECT knowledge_report_summary(pg_temp.u('0b'), 3::smallint, pg_temp.as_of()) s) x),
  '[{"rows":1,"words":1,"meanings":1},{"missed_last":0,"rated_known":0,"checked":1,"not_checked":0},1,1]');
SELECT pg_temp.eq('empty learner: zero counts and empty arrays, never NULL',
  (SELECT jsonb_build_array(s->'tracked', s->'states', s->'families', s->'calibration'->'bands', s->'calibration'->'since',
                            s->'calibration'->'answers', s->'watchlist', s->'missed_recent', s->'activity')
     FROM (SELECT knowledge_report_summary(pg_temp.u('0c'), 3::smallint, pg_temp.as_of()) s) x),
  '[{"rows":0,"words":0,"meanings":0},{"missed_last":0,"rated_known":0,"checked":0,"not_checked":0},[],
    [[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]],[],0,
    {"items":0,"rated_known":0,"seen_not_rated":0,"no_evidence":0},{"meanings":0,"flagged":0},
    {"d30":{"practised_meanings":0,"direct_outcomes":0,"met_in_texts":0},"d90":{"practised_meanings":0,"direct_outcomes":0,"met_in_texts":0}}]');
SELECT pg_temp.ok('summary is deterministic (default as_of, NULL p_cal_since)',
  knowledge_report_summary(pg_temp.u('0a'), 3::smallint, pg_temp.as_of(), 180, NULL)->'calibration'->'since' = '[]'
  AND knowledge_report_summary(pg_temp.u('0a'), 3::smallint, pg_temp.as_of())
      = knowledge_report_summary(pg_temp.u('0a'), 3::smallint, pg_temp.as_of()));

-- ---- 4. TASK-1044: knowledge_report_words ----------------------------------------------
CREATE TEMP TABLE kr_w ON COMMIT DROP AS SELECT pg_temp.words(pg_temp.u('0a'), 3::smallint) AS j;
SELECT pg_temp.eq('words: shape', (SELECT jsonb_build_object('n', jsonb_array_length(j->'rows'), 'm', j->'matching',
                                                             'c', j->'next_cursor', 'a', j->'as_of') FROM kr_w),
                  jsonb_build_object('n', 14, 'm', 14, 'c', NULL, 'a', pg_temp.as_of()));
SELECT pg_temp.eq('words: row keys (no numeric p_known, no five-level label)',
  (SELECT jsonb_agg(k ORDER BY k COLLATE "C") FROM kr_w, jsonb_object_keys(j->'rows'->0) k),
  '["app_rates_known","band","checks_correct","checks_wrong","first_seen_at","flashcard_lapses","gloss","gloss_language_id",
    "idle_days","in_word_list","ladder_ring","ladder_state","last_direct","last_seen_at","lemma","lemma_traditional",
    "missed_flag","missed_recent","misses_90","pronunciation","reading","sense_rank","state","tests_correct","tests_wrong",
    "vocab_id","zipf"]');
SELECT pg_temp.eq('words: useful order = tier then -zipf then ids',
  (SELECT jsonb_agg(jsonb_build_array(r->'vocab_id', r->'sense_rank') ORDER BY o) FROM kr_w, jsonb_array_elements(j->'rows') WITH ORDINALITY t(r, o)),
  '[[9000008,1],[9000009,1],[9000011,1],[9000004,1],[9000007,1],[9000002,1],[9000010,1],[9000005,1],
    [9000006,1],[9000003,1],[9000012,1],[9000013,1],[9000006,2],[9000001,1]]');
SELECT pg_temp.eq('words: V2 aggregation, gloss L1 standard, native pronunciation, ladder max ring, flashcard max lapses',
  (SELECT r - 'first_seen_at' - 'last_seen_at' FROM kr_w, pg_temp.row_of(j, 9000002, 1) r),
  '{"vocab_id":9000002,"sense_rank":1,"lemma":"krv02","lemma_traditional":null,"reading":null,"pronunciation":"pron 9000002",
    "gloss":"en std V2","gloss_language_id":2,"zipf":4.7,"band":5,"state":"checked","app_rates_known":false,
    "checks_correct":2,"checks_wrong":0,"tests_correct":2,"tests_wrong":1,"last_direct":null,"idle_days":1,
    "missed_recent":false,"missed_flag":null,"misses_90":0,"ladder_ring":3,"ladder_state":"gated","flashcard_lapses":4,
    "in_word_list":true}');
SELECT pg_temp.eq('words: V2 first and last seen', (SELECT jsonb_build_array(r->'first_seen_at', r->'last_seen_at') FROM kr_w, pg_temp.row_of(j, 9000002, 1) r),
                  jsonb_build_array(pg_temp.d(40), pg_temp.d(1)));
SELECT pg_temp.eq('words: gloss fallback simple / native',
  (SELECT jsonb_build_array(a->'gloss', a->'gloss_language_id', b->'gloss', b->'gloss_language_id')
     FROM kr_w, pg_temp.row_of(j, 9000003, 1) a, pg_temp.row_of(j, 9000012, 1) b),
  '["en simple V3",2,"native 9000012",3]');
SELECT pg_temp.eq('words: gloss in the native language when p_definition_language_id is NULL',
  (SELECT r->'gloss_language_id' FROM pg_temp.row_of(pg_temp.words(pg_temp.u('0a'), 3::smallint, '{}', 'useful', 1000, NULL), 9000001, 1) r), '3');
SELECT pg_temp.eq('words: V7 flag, misses, last direct (intro -> recognition)',
  (SELECT jsonb_build_array(r->'state', r->'missed_recent', r->'missed_flag', r->'misses_90', r->'last_direct')
     FROM kr_w, pg_temp.row_of(j, 9000007, 1) r),
  jsonb_build_array('missed_last', true, '{"wrong":3,"tries":4,"days":3}'::jsonb, 3,
                    jsonb_build_object('at', pg_temp.d(1), 'correct', false, 'family', 'form_recognition')));
SELECT pg_temp.eq('words: last_direct families (tie -> the wrong cloze, quiz, intro ex_* via exercise_id, typed, unmapped)',
  (SELECT jsonb_agg(jsonb_build_array(r->'vocab_id', r->'last_direct'->'correct', r->'last_direct'->'family') ORDER BY r->'vocab_id')
     FROM kr_w, jsonb_array_elements(j->'rows') r
    WHERE (r->>'vocab_id')::int IN (9000001, 9000004, 9000008, 9000009, 9000010, 9000011, 9000012, 9000013)),
  '[[9000001,true,"form_recognition"],[9000004,false,"form_recognition"],[9000008,false,"form_recognition"],
    [9000009,false,"meaning_recall"],[9000010,true,"form_recognition"],[9000011,false,"semantic_discrimination"],
    [9000012,true,"form_production"],[9000013,true,"unmapped"]]');
SELECT pg_temp.eq('words: V8 missed > 90 days ago, V5 idle days and app rating, V13 no last_seen',
  (SELECT jsonb_build_array(a->'state', a->'missed_recent', b->'idle_days', b->'app_rates_known', b->'band',
                            c->'idle_days', c->'last_seen_at', c->'last_direct'->'at')
     FROM kr_w, pg_temp.row_of(j, 9000008, 1) a, pg_temp.row_of(j, 9000005, 1) b, pg_temp.row_of(j, 9000013, 1) c),
  jsonb_build_array('missed_last', false, 70, true, 0, NULL, NULL, pg_temp.d(9)));
SELECT pg_temp.eq('words: in_word_list', (SELECT jsonb_agg(jsonb_build_array(r->'vocab_id', r->'sense_rank') ORDER BY r->'vocab_id', r->'sense_rank')
                                            FROM kr_w, jsonb_array_elements(j->'rows') r WHERE (r->>'in_word_list')::boolean),
                  '[[9000001,1],[9000002,1],[9000006,2]]');

-- state filters equal the summary's counts; every filter
SELECT pg_temp.eq('words: state filters = summary states',
  (SELECT jsonb_object_agg(s, (pg_temp.words(pg_temp.u('0a'), 3::smallint, jsonb_build_object('states', jsonb_build_array(s)), 'useful', 1))->'matching')
     FROM unnest(ARRAY['missed_last','rated_known','checked','not_checked']) s),
  (SELECT j->'states' FROM kr_sum));
SELECT pg_temp.eq('words: filters',
  (SELECT jsonb_object_agg(label, (pg_temp.words(pg_temp.u('0a'), 3::smallint, f))->'matching') FROM (VALUES
     ('empty states', '{"states":[]}'::jsonb), ('two states', '{"states":["checked","not_checked"]}'),
     ('checked_several', '{"checked_several":true}'), ('checked_several off', '{"checked_several":false}'),
     ('missed_recent', '{"missed_recent":true}'), ('idle 60', '{"idle_days":60}'), ('idle 90', '{"idle_days":90}'),
     ('band 7', '{"bands":[7]}'), ('band 0', '{"bands":[0]}'), ('bands 0 7', '{"bands":[0,7]}'), ('bands empty', '{"bands":[]}'),
     ('in_word_list', '{"in_word_list":true}'), ('vocab_ids rank 1', '{"vocab_ids":[9000001,9000006,9000020]}'),
     ('vocab_ids empty', '{"vocab_ids":[]}'), ('combined', '{"states":["missed_last"],"bands":[4]}'),
     ('q prefix', '{"q":"krv0"}'), ('q reading', '{"q":"かん"}'), ('q no toneless for ja', '{"q":"pron"}'),
     ('null filters', 'null')) v(label, f)),
  '{"empty states":14,"two states":7,"checked_several":2,"checked_several off":14,"missed_recent":4,"idle 60":3,"idle 90":2,
    "band 7":3,"band 0":1,"bands 0 7":4,"bands empty":14,"in_word_list":3,"vocab_ids rank 1":2,"vocab_ids empty":0,
    "combined":2,"q prefix":10,"q reading":1,"q no toneless for ja":0,"null filters":14}');
SELECT pg_temp.eq('words: zh search (prefix, traditional, toneless pinyin, LIKE escaping)',
  (SELECT jsonb_object_agg(label, (SELECT jsonb_agg((r->>'vocab_id')::int ORDER BY (r->>'vocab_id')::int)
                                     FROM jsonb_array_elements((pg_temp.words(pg_temp.u('0d'), 1::smallint, jsonb_build_object('q', q)))->'rows') r))
     FROM (VALUES ('不', 'kr不'), ('trad', 'kr你們'), ('nihao', 'nihao'), ('ni', 'ni'), ('bu', 'bu'), ('hao', 'hao'),
                  ('escaped _', E'kra\\_b'), ('unescaped _', 'kra_b'), ('escaped %', E'kr\\%'), ('digits', '123')) v(label, q)),
  '{"不":[9000102,9000103],"trad":[9000104],"nihao":[9000101],"ni":[9000101,9000104],"bu":[9000102,9000103],"hao":null,
    "escaped _":[9000105],"unescaped _":[9000105,9000106],"escaped %":null,"digits":null}');

-- paging: every sort, small pages, no duplicate or gap, same order as one big page
DO $t$
DECLARE s text; lim int; got jsonb; want jsonb;
BEGIN
  FOREACH s IN ARRAY ARRAY['useful','recent','oldest','common','lemma','id','missed'] LOOP
    want := (SELECT jsonb_agg(jsonb_build_array(r->'vocab_id', r->'sense_rank') ORDER BY o)
               FROM jsonb_array_elements((pg_temp.words(pg_temp.u('0a'), 3::smallint, '{}', s))->'rows') WITH ORDINALITY t(r, o));
    FOREACH lim IN ARRAY ARRAY[1, 3, 13, 14] LOOP
      got := pg_temp.page_all(pg_temp.u('0a'), 3::smallint, 2::smallint, '{}', s, lim);
      IF got IS DISTINCT FROM want THEN RAISE EXCEPTION 'FAIL paging % limit %: % vs %', s, lim, got, want; END IF;
    END LOOP;
    IF (SELECT count(DISTINCT e) FROM jsonb_array_elements(want) e) <> 14 THEN RAISE EXCEPTION 'FAIL % not 14 distinct', s; END IF;
    RAISE NOTICE 'PASS paging % (limits 1, 3, 13, 14)', s;
  END LOOP;
  got := pg_temp.page_all(pg_temp.u('0a'), 3::smallint, 2::smallint, '{"states":["missed_last","checked"]}', 'recent', 2);
  PERFORM pg_temp.eq('paging with a filter', to_jsonb(jsonb_array_length(got)), '8');
END $t$;
SELECT pg_temp.eq('words: sort orders',
  (SELECT jsonb_object_agg(s, (SELECT jsonb_agg((r->>'vocab_id')::int * 10 + (r->>'sense_rank')::int ORDER BY o)
                                 FROM jsonb_array_elements((pg_temp.words(pg_temp.u('0a'), 3::smallint, '{}', s))->'rows') WITH ORDINALITY t(r, o)))
     FROM unnest(ARRAY['recent','common','lemma','missed','bogus']) s),
  '{"recent":[90000021,90000041,90000071,90000011,90000111,90000091,90000101,90000031,90000062,90000121,90000051,90000061,90000081,90000131],
    "common":[90000061,90000062,90000011,90000081,90000021,90000091,90000111,90000041,90000101,90000071,90000031,90000121,90000131,90000051],
    "lemma":[90000011,90000021,90000031,90000041,90000051,90000061,90000062,90000071,90000081,90000091,90000101,90000111,90000121,90000131],
    "missed":[90000071,90000041,90000111,90000091,90000101,90000011,90000121,90000131,90000081,90000021,90000031,90000051,90000061,90000062],
    "bogus":[90000081,90000091,90000111,90000041,90000071,90000021,90000101,90000051,90000061,90000031,90000121,90000131,90000062,90000011]}');
SELECT pg_temp.eq('words: limit clamp and cursor element types',
  jsonb_build_array(
    jsonb_array_length((knowledge_report_words(pg_temp.u('0a'), 3::smallint, 2::smallint, '{}', 'useful', NULL, 0, pg_temp.as_of()))->'rows'),
    jsonb_array_length((knowledge_report_words(pg_temp.u('0a'), 3::smallint, 2::smallint, '{}', 'useful', NULL, 5000, pg_temp.as_of()))->'rows'),
    (SELECT jsonb_agg(jsonb_typeof(e)) FROM jsonb_array_elements(
       (knowledge_report_words(pg_temp.u('0a'), 3::smallint, 2::smallint, '{}', 'lemma', NULL, 2, pg_temp.as_of()))->'next_cursor') e)),
  '[1,14,["string","number","number","number","number"]]');
DO $t$
BEGIN
  PERFORM knowledge_report_words(pg_temp.u('0a'), 3::smallint, 2::smallint, '{}', 'useful', '["", "x", 0, 1, 1]', 5, pg_temp.as_of());
  RAISE EXCEPTION 'FAIL malformed cursor accepted';
EXCEPTION WHEN invalid_text_representation THEN RAISE NOTICE 'PASS malformed cursor raises 22P02';
END $t$;
SELECT pg_temp.eq('words: isolation and empty learner',
  jsonb_build_array((pg_temp.words(pg_temp.u('0b'), 3::smallint))->'matching',
                    (SELECT r->'ladder_ring' FROM pg_temp.row_of(pg_temp.words(pg_temp.u('0b'), 3::smallint), 9000001, 1) r),
                    pg_temp.words(pg_temp.u('0c'), 3::smallint) - 'as_of'),
  '[1,null,{"rows":[],"matching":0,"next_cursor":null}]');

-- ---- 5. role checks: service_role runs the functions; clients cannot ---------------------
SET LOCAL ROLE service_role;
SELECT pg_temp.ok('service_role: summary, words, frame, pairs run',
  (knowledge_report_summary(pg_temp.u('0a'), 3::smallint, pg_temp.as_of())->'tracked'->>'meanings')::int = 14
  AND (knowledge_report_words(pg_temp.u('0a'), 3::smallint, 2::smallint, '{}', 'useful', NULL, 5, pg_temp.as_of())->>'matching')::int = 14
  AND knowledge_frame_bands() ? '2:3' AND jsonb_array_length(knowledge_active_pairs(pg_temp.d(30))) >= 4
  AND knowledge_snapshots_prune(120) >= 0);
RESET ROLE;
SET LOCAL ROLE authenticated;
DO $t$
BEGIN
  PERFORM public.knowledge_report_summary('00000000-0000-4000-8000-00000000000a'::uuid, 3::smallint);
  RAISE EXCEPTION 'FAIL authenticated executed knowledge_report_summary';
EXCEPTION WHEN insufficient_privilege THEN RAISE NOTICE 'PASS authenticated cannot execute the summary';
END $t$;
DO $t$
BEGIN
  PERFORM public.knowledge_report_words('00000000-0000-4000-8000-00000000000a'::uuid, 3::smallint, 2::smallint);
  RAISE EXCEPTION 'FAIL authenticated executed knowledge_report_words';
EXCEPTION WHEN insufficient_privilege THEN RAISE NOTICE 'PASS authenticated cannot execute the words RPC';
END $t$;
RESET ROLE;
SET LOCAL ROLE anon;
DO $t$
BEGIN
  PERFORM public.knowledge_frame_bands();
  RAISE EXCEPTION 'FAIL anon executed knowledge_frame_bands';
EXCEPTION WHEN insufficient_privilege THEN RAISE NOTICE 'PASS anon cannot execute the frame';
END $t$;
RESET ROLE;

ROLLBACK;
