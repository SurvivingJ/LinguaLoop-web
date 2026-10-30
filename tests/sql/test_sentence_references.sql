-- =============================================================================
-- TASK-901 — test_sentences / test_sentence_references (rollback-only SQL test)
-- =============================================================================
-- Pairs with migrations/test_sentence_references_schema.sql, which must already
-- be applied; this file creates nothing permanent. Everything runs inside one
-- transaction that ends in ROLLBACK, so no fixture survives.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_sentence_references.sql
--
-- Run as the migration owner (postgres) so SET LOCAL ROLE anon/authenticated is
-- permitted. Asserts, printing PASS notices:
--   1. the schema objects exist (tables, partial unique index, triggers,
--      dt_passage range columns + partial unique index);
--   2. a second ACTIVE reference for the same (sentence, L1) is rejected
--      (unique_violation), while an inactive duplicate is accepted;
--   3. the script trigger rejects l1_text containing the L2 script
--      (kana and Han for a ja test, Han for a zh test) and accepts clean text;
--   4. the l2_text trigger rejects a span that does not match the transcript;
--   5. SELECT on both tables as anon and authenticated is denied.
--
-- Fixtures: an existing ja (and zh) test with a transcript is used when one
-- exists; otherwise a throw-away tests row is inserted (owned by the first user
-- row) so the file also runs on a stub database.
-- =============================================================================

BEGIN;

CREATE FUNCTION pg_temp.expect_denied(p_role text, p_sql text, p_label text)
RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
  EXECUTE format('SET LOCAL ROLE %I', p_role);
  BEGIN
    EXECUTE p_sql;
    EXECUTE 'RESET ROLE';
    RAISE EXCEPTION 'FAIL: % as % was NOT denied', p_label, p_role;
  EXCEPTION WHEN insufficient_privilege THEN
    EXECUTE 'RESET ROLE';
    RAISE NOTICE 'PASS: % as % denied', p_label, p_role;
  END;
END $f$;

-- Returns the id of a test in p_language_id with a non-empty transcript,
-- inserting a fixture row when none exists.
CREATE FUNCTION pg_temp.fixture_test(p_language_id smallint)
RETURNS uuid LANGUAGE plpgsql AS $f$
DECLARE
  v_id   uuid;
  v_user uuid;
  v_text text;
BEGIN
  SELECT t.id INTO v_id FROM public.tests t
   WHERE t.language_id = p_language_id AND length(coalesce(t.transcript, '')) >= 10
   ORDER BY t.created_at LIMIT 1;
  IF v_id IS NOT NULL THEN RETURN v_id; END IF;

  SELECT u.id INTO v_user FROM public.users u ORDER BY u.created_at LIMIT 1;
  IF v_user IS NULL THEN RAISE EXCEPTION 'no users row to own a fixture test'; END IF;
  v_text := CASE p_language_id
    WHEN 1 THEN '今天天气很好。我们去公园散步。'
    WHEN 3 THEN '今日はいい天気です。公園に行きましょう。'
    ELSE 'The weather is nice today. Let us go to the park.' END;
  INSERT INTO public.tests (gen_user, slug, title, transcript, difficulty, language_id, is_active)
  VALUES (v_user, 'task901-fixture-' || p_language_id || '-' || gen_random_uuid(),
          'TASK-901 fixture', v_text, 3, p_language_id, false)
  RETURNING id INTO v_id;
  RAISE NOTICE 'fixture test inserted for language % (rolled back)', p_language_id;
  RETURN v_id;
END $f$;

-- ---- 1. schema objects ---------------------------------------------------------
DO $$
BEGIN
  IF to_regclass('public.test_sentences') IS NULL THEN
    RAISE EXCEPTION 'FAIL: test_sentences missing — apply migrations/test_sentence_references_schema.sql first';
  END IF;
  IF to_regclass('public.test_sentence_references') IS NULL THEN
    RAISE EXCEPTION 'FAIL: test_sentence_references missing';
  END IF;
  IF to_regclass('public.uq_test_sentence_references_active') IS NULL THEN
    RAISE EXCEPTION 'FAIL: partial unique index uq_test_sentence_references_active missing';
  END IF;
  IF to_regclass('public.uq_dt_passage_sentence_range') IS NULL THEN
    RAISE EXCEPTION 'FAIL: partial unique index uq_dt_passage_sentence_range missing';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                  WHERE table_schema = 'public' AND table_name = 'dt_passage'
                    AND column_name IN ('sentence_start', 'sentence_end')
                 HAVING count(*) = 2) THEN
    RAISE EXCEPTION 'FAIL: dt_passage.sentence_start / sentence_end missing';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                  WHERE table_schema = 'public' AND table_name = 'tests'
                    AND column_name = 'transcript_hash') THEN
    RAISE EXCEPTION 'FAIL: tests.transcript_hash missing — apply migrations/tests_transcript_hash.sql';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_trigger
                  WHERE tgrelid = 'public.test_sentence_references'::regclass
                    AND tgname = 'test_sentence_references_check_l1_script') THEN
    RAISE EXCEPTION 'FAIL: trigger test_sentence_references_check_l1_script missing';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_trigger
                  WHERE tgrelid = 'public.test_sentences'::regclass
                    AND tgname = 'test_sentences_check_l2_text') THEN
    RAISE EXCEPTION 'FAIL: trigger test_sentences_check_l2_text missing';
  END IF;
  IF NOT (SELECT relrowsecurity FROM pg_class WHERE oid = 'public.test_sentences'::regclass)
     OR NOT (SELECT relrowsecurity FROM pg_class WHERE oid = 'public.test_sentence_references'::regclass) THEN
    RAISE EXCEPTION 'FAIL: RLS not enabled on both tables';
  END IF;
  RAISE NOTICE 'PASS: schema objects present (tables, indexes, triggers, columns, RLS on)';
END $$;

-- ---- 2–4. constraints and triggers ---------------------------------------------
DO $$
DECLARE
  v_ja_test  uuid := pg_temp.fixture_test(3::smallint);
  v_zh_test  uuid := pg_temp.fixture_test(1::smallint);
  v_ja_text  text;
  v_zh_text  text;
  v_ja_sent  bigint;
  v_zh_sent  bigint;
  v_en       smallint := 2;
  v_n        integer;
BEGIN
  SELECT transcript INTO v_ja_text FROM public.tests WHERE id = v_ja_test;
  SELECT transcript INTO v_zh_text FROM public.tests WHERE id = v_zh_test;

  -- Sentences: the first 10 code points of each transcript as sentence 0.
  INSERT INTO public.test_sentences (test_id, idx, char_start, char_end, l2_text, transcript_hash)
  VALUES (v_ja_test, 0, 0, 10, substr(v_ja_text, 1, 10), encode(sha256(convert_to(v_ja_text, 'UTF8')), 'hex'))
  RETURNING id INTO v_ja_sent;
  INSERT INTO public.test_sentences (test_id, idx, char_start, char_end, l2_text, transcript_hash)
  VALUES (v_zh_test, 0, 0, 10, substr(v_zh_text, 1, 10), encode(sha256(convert_to(v_zh_text, 'UTF8')), 'hex'))
  RETURNING id INTO v_zh_sent;
  RAISE NOTICE 'PASS: test_sentences rows inserted (l2_text matches transcript span)';

  -- 4. l2_text trigger: a span whose text does not match is rejected.
  BEGIN
    INSERT INTO public.test_sentences (test_id, idx, char_start, char_end, l2_text, transcript_hash)
    VALUES (v_ja_test, 1, 10, 20, 'definitely not the transcript', 'x');
    RAISE EXCEPTION 'FAIL: mismatching l2_text was accepted';
  EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'PASS: l2_text that does not match the transcript span is rejected';
  END;

  -- Duplicate (test_id, idx) is rejected.
  BEGIN
    INSERT INTO public.test_sentences (test_id, idx, char_start, char_end, l2_text, transcript_hash)
    VALUES (v_ja_test, 0, 0, 10, substr(v_ja_text, 1, 10), 'x');
    RAISE EXCEPTION 'FAIL: duplicate (test_id, idx) was accepted';
  EXCEPTION WHEN unique_violation THEN
    RAISE NOTICE 'PASS: UNIQUE (test_id, idx) enforced';
  END;

  -- 3. Script trigger: clean English for a ja sentence is accepted …
  INSERT INTO public.test_sentence_references
    (sentence_id, l1_language_id, l1_text, author_model, prompt_version, is_active, run_id)
  VALUES (v_ja_sent, v_en, 'The weather is nice today.', 'test-model', 'sr-test', true, 'task901-test');
  RAISE NOTICE 'PASS: clean L1 reference accepted and activated';

  -- … kana leaks are rejected …
  BEGIN
    INSERT INTO public.test_sentence_references
      (sentence_id, l1_language_id, l1_text, author_model, prompt_version, is_active)
    VALUES (v_ja_sent, v_en, 'The weather (天気) is nice today.', 'test-model', 'sr-test', false);
    RAISE EXCEPTION 'FAIL: Han in l1_text for a ja sentence was accepted';
  EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'PASS: Han in l1_text rejected for ja test';
  END;
  BEGIN
    INSERT INTO public.test_sentence_references
      (sentence_id, l1_language_id, l1_text, author_model, prompt_version, is_active)
    VALUES (v_ja_sent, v_en, 'It is nice today ですね.', 'test-model', 'sr-test', false);
    RAISE EXCEPTION 'FAIL: kana in l1_text for a ja sentence was accepted';
  EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'PASS: kana in l1_text rejected for ja test';
  END;
  -- … and Han is rejected for a zh sentence too.
  BEGIN
    INSERT INTO public.test_sentence_references
      (sentence_id, l1_language_id, l1_text, author_model, prompt_version, is_active)
    VALUES (v_zh_sent, v_en, 'The weather 天气 is nice.', 'test-model', 'sr-test', false);
    RAISE EXCEPTION 'FAIL: Han in l1_text for a zh sentence was accepted';
  EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'PASS: Han in l1_text rejected for zh test';
  END;
  -- An UPDATE that introduces the L2 script is rejected as well.
  BEGIN
    UPDATE public.test_sentence_references SET l1_text = 'nice 今日' WHERE sentence_id = v_ja_sent;
    RAISE EXCEPTION 'FAIL: UPDATE introducing Han was accepted';
  EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'PASS: UPDATE introducing the L2 script rejected';
  END;

  -- 2. One active reference per (sentence, L1).
  BEGIN
    INSERT INTO public.test_sentence_references
      (sentence_id, l1_language_id, l1_text, author_model, prompt_version, is_active)
    VALUES (v_ja_sent, v_en, 'Today the weather is fine.', 'test-model', 'sr-test', true);
    RAISE EXCEPTION 'FAIL: second ACTIVE reference for the same (sentence, L1) was accepted';
  EXCEPTION WHEN unique_violation THEN
    RAISE NOTICE 'PASS: second active reference for same (sentence, L1) rejected';
  END;
  -- An inactive duplicate (history) is fine.
  INSERT INTO public.test_sentence_references
    (sentence_id, l1_language_id, l1_text, author_model, prompt_version, is_active, review_verdict)
  VALUES (v_ja_sent, v_en, 'Today the weather is fine.', 'test-model', 'sr-test', false, 'fail');
  SELECT count(*) INTO v_n FROM public.test_sentence_references WHERE sentence_id = v_ja_sent;
  IF v_n <> 2 THEN RAISE EXCEPTION 'FAIL: expected 2 references on the ja sentence, found %', v_n; END IF;
  RAISE NOTICE 'PASS: inactive duplicate reference accepted (history kept)';

  -- CHECK constraints on enums / ranges.
  BEGIN
    INSERT INTO public.test_sentence_references
      (sentence_id, l1_language_id, l1_text, author_model, prompt_version, review_verdict)
    VALUES (v_zh_sent, v_en, 'Fine.', 'test-model', 'sr-test', 'maybe');
    RAISE EXCEPTION 'FAIL: review_verdict ''maybe'' was accepted';
  EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'PASS: review_verdict CHECK enforced';
  END;

  -- dt_passage range: both-or-neither and the partial unique index.
  BEGIN
    UPDATE public.dt_passage SET sentence_start = 0 WHERE false;  -- no-op, constraint exists
    PERFORM 1 FROM pg_constraint WHERE conname = 'dt_passage_sentence_range_chk';
    IF NOT FOUND THEN RAISE EXCEPTION 'FAIL: dt_passage_sentence_range_chk missing'; END IF;
    RAISE NOTICE 'PASS: dt_passage_sentence_range_chk present';
  END;

  -- Cascade: deleting the sentence removes its references.
  DELETE FROM public.test_sentences WHERE id = v_zh_sent;
  SELECT count(*) INTO v_n FROM public.test_sentence_references WHERE sentence_id = v_zh_sent;
  IF v_n <> 0 THEN RAISE EXCEPTION 'FAIL: references survived sentence delete'; END IF;
  RAISE NOTICE 'PASS: ON DELETE CASCADE sentence -> references';
END $$;

-- ---- 5. client roles are locked out --------------------------------------------
SET LOCAL request.jwt.claims = '{"sub":"00000000-0000-0000-0000-000000000001","role":"authenticated"}';

SELECT pg_temp.expect_denied('anon',          'SELECT 1 FROM public.test_sentences LIMIT 1',           'SELECT test_sentences');
SELECT pg_temp.expect_denied('authenticated', 'SELECT 1 FROM public.test_sentences LIMIT 1',           'SELECT test_sentences');
SELECT pg_temp.expect_denied('anon',          'SELECT 1 FROM public.test_sentence_references LIMIT 1', 'SELECT test_sentence_references');
SELECT pg_temp.expect_denied('authenticated', 'SELECT 1 FROM public.test_sentence_references LIMIT 1', 'SELECT test_sentence_references');
SELECT pg_temp.expect_denied('authenticated',
  'INSERT INTO public.test_sentences (test_id, idx, char_start, char_end, l2_text, transcript_hash) VALUES (gen_random_uuid(), 0, 0, 1, ''x'', ''x'')',
  'INSERT test_sentences');

DO $$
DECLARE t text; r text; p text;
BEGIN
  FOREACH t IN ARRAY ARRAY['test_sentences', 'test_sentence_references'] LOOP
    FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
      FOREACH p IN ARRAY ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'] LOOP
        IF has_table_privilege(r, 'public.' || t, p) THEN
          RAISE EXCEPTION 'FAIL: % has % on %', r, p, t;
        END IF;
      END LOOP;
    END LOOP;
    IF NOT has_table_privilege('service_role', 'public.' || t, 'SELECT') THEN
      RAISE EXCEPTION 'FAIL: service_role cannot SELECT %', t;
    END IF;
  END LOOP;
  FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
    IF has_function_privilege(r, 'public.test_sentence_references_check_l1_script()', 'EXECUTE')
       OR has_function_privilege(r, 'public.test_sentences_check_l2_text()', 'EXECUTE') THEN
      RAISE EXCEPTION 'FAIL: % can EXECUTE a trigger function', r;
    END IF;
  END LOOP;
  RAISE NOTICE 'PASS: no client privileges on either table or trigger function; service_role intact';
END $$;

SELECT 'ALL PASS — rolling back' AS result;

ROLLBACK;
