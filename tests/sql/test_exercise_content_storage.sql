-- =============================================================================
-- exercise_content_storage — SQL tests (TASK-984, ADR-047 §8)
-- =============================================================================
-- Rollback-only SQL test, same harness as tests/sql/test_session_budget_settings.sql:
-- assertions RAISE EXCEPTION, a clean run prints PASS notices, everything is rolled back.
-- Requires migrations/exercise_content_storage.sql applied. Run by the operator on staging
-- (TASK-994), or on production only because it ends in ROLLBACK:
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_exercise_content_storage.sql
--
-- Fixture: the lowest-id sense with no exercises that is not on calibration_anchor_blocklist
-- (the quarantine trigger would deactivate its rows). Every row it creates is rolled back;
-- exercise_content_version_seq still advances (sequences are not transactional), which only
-- leaves a gap — gaps are allowed (ADR-047 §3).
-- =============================================================================

BEGIN;

-- ---- 1. Objects, grants and the bucket -----------------------------------------------
DO $test$
DECLARE
  v_fn text;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                  WHERE table_schema = 'public' AND table_name = 'exercises'
                    AND column_name = 'content_version' AND data_type = 'integer'
                    AND is_nullable = 'NO' AND column_default = '0') THEN
    RAISE EXCEPTION 'FAIL exercises.content_version must be integer NOT NULL DEFAULT 0'; END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                  WHERE table_schema = 'public' AND table_name = 'exercises'
                    AND column_name = 'dedupe_key' AND data_type = 'text' AND is_nullable = 'YES') THEN
    RAISE EXCEPTION 'FAIL exercises.dedupe_key must be a nullable text column'; END IF;

  FOREACH v_fn IN ARRAY ARRAY[
      'public.exercise_content_begin(integer)',
      'public.exercise_content_commit(integer, integer, uuid[], integer, uuid[], jsonb, jsonb)',
      'public.exercise_content_live_versions(integer)']
  LOOP
    IF has_function_privilege('anon', v_fn, 'EXECUTE')
       OR has_function_privilege('authenticated', v_fn, 'EXECUTE') THEN
      RAISE EXCEPTION 'FAIL % must not be executable by anon/authenticated', v_fn; END IF;
    IF NOT has_function_privilege('service_role', v_fn, 'EXECUTE') THEN
      RAISE EXCEPTION 'FAIL % must be executable by service_role', v_fn; END IF;
    IF (SELECT p.prosecdef FROM pg_proc p WHERE p.oid = v_fn::regprocedure) THEN
      RAISE EXCEPTION 'FAIL % must be SECURITY INVOKER', v_fn; END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_proc p WHERE p.oid = v_fn::regprocedure
                     AND 'search_path=public, pg_temp' = ANY (p.proconfig)) THEN
      RAISE EXCEPTION 'FAIL % must SET search_path = public, pg_temp', v_fn; END IF;
  END LOOP;

  IF has_sequence_privilege('anon', 'public.exercise_content_version_seq', 'USAGE')
     OR has_sequence_privilege('authenticated', 'public.exercise_content_version_seq', 'USAGE') THEN
    RAISE EXCEPTION 'FAIL exercise_content_version_seq must not be usable by anon/authenticated'; END IF;
  IF NOT has_sequence_privilege('service_role', 'public.exercise_content_version_seq', 'USAGE') THEN
    RAISE EXCEPTION 'FAIL service_role needs USAGE on exercise_content_version_seq (nextval in begin)'; END IF;

  IF NOT EXISTS (SELECT 1 FROM storage.buckets
                  WHERE id = 'exercise-content' AND public IS FALSE
                    AND file_size_limit = 1048576
                    AND allowed_mime_types = ARRAY['application/json']) THEN
    RAISE EXCEPTION 'FAIL bucket exercise-content must exist, private, 1 MB, application/json'; END IF;

  RAISE NOTICE 'exercise_content objects/grants/bucket PASS';
END $test$;

-- ---- 2. begin / commit / CAS / validation / live_versions -----------------------------
DO $test$
DECLARE
  v_sense  integer;
  v_other  integer;
  v_lang   integer;
  v_tone   uuid := gen_random_uuid();   -- context-free type
  v_cloze  uuid := gen_random_uuid();   -- context-bearing type
  v_third  uuid := gen_random_uuid();
  v_rogue  uuid := gen_random_uuid();
  b        jsonb;
  c        jsonb;
  v_n1     integer;
  v_n2     integer;
  v_n3     integer;
  v_ids    uuid[];
  v_state  text;
  r        record;
BEGIN
  SELECT dws.id, dv.language_id INTO v_sense, v_lang
    FROM public.dim_word_senses dws
    JOIN public.dim_vocabulary dv ON dv.id = dws.vocab_id
   WHERE NOT EXISTS (SELECT 1 FROM public.exercises e WHERE e.word_sense_id = dws.id)
     AND NOT EXISTS (SELECT 1 FROM public.calibration_anchor_blocklist q WHERE q.sense_id = dws.id)
   ORDER BY dws.id
   LIMIT 1;
  IF v_sense IS NULL THEN RAISE EXCEPTION 'SETUP FAIL: no sense without exercises'; END IF;
  SELECT dws.id INTO v_other FROM public.dim_word_senses dws WHERE dws.id <> v_sense ORDER BY dws.id LIMIT 1;

  -- 2a. fresh sense: current_version 0, no rows, a fresh positive version
  b := public.exercise_content_begin(v_sense);
  IF (b->>'sense_id')::int <> v_sense OR (b->>'current_version')::int <> 0
     OR b->'rows' <> '[]'::jsonb OR (b->>'new_version')::int < 1 THEN
    RAISE EXCEPTION 'FAIL begin on a fresh sense: %', b; END IF;
  v_n1 := (b->>'new_version')::int;

  -- 2b. commit inserts two rows (tone row omits tags/is_active: defaults '{}' / true)
  c := public.exercise_content_commit(
         v_sense, 0, '{}', v_n1, '{}',
         jsonb_build_array(
           jsonb_build_object('id', v_tone, 'language_id', v_lang, 'exercise_type', 'tone_id_word',
                              'source_type', 'vocabulary', 'word_sense_id', v_sense,
                              'ladder_level', 1, 'content', jsonb_build_object('prompt', 'p1')),
           jsonb_build_object('id', v_cloze, 'language_id', v_lang, 'exercise_type', 'cloze_completion',
                              'source_type', 'vocabulary', 'word_sense_id', v_sense, 'ladder_level', 3,
                              'tags', jsonb_build_object('variant', 'A'), 'is_active', true,
                              'complexity_tier', 'T2',
                              'content', jsonb_build_object('context_sentence', 'S1', 'answer', 'a'))),
         '{}');
  IF c <> jsonb_build_object('ok', true, 'version', v_n1, 'deleted', 0, 'inserted', 2, 'updated', 0) THEN
    RAISE EXCEPTION 'FAIL first commit result: %', c; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_locks l
                  WHERE l.locktype = 'advisory' AND l.pid = pg_backend_pid()
                    AND l.classid = 47047 AND l.objid = v_sense AND l.objsubid = 2) THEN
    RAISE EXCEPTION 'FAIL commit must take pg_advisory_xact_lock(47047, sense)'; END IF;
  SELECT * INTO r FROM public.exercises WHERE id = v_tone;
  IF r.content_version <> v_n1 OR r.dedupe_key IS DISTINCT FROM md5('')
     OR r.tags <> '{}'::jsonb OR r.is_active IS NOT TRUE
     OR r.content <> jsonb_build_object('prompt', 'p1') THEN
    RAISE EXCEPTION 'FAIL inserted context-free row: version % dedupe % tags % active % content %',
      r.content_version, r.dedupe_key, r.tags, r.is_active, r.content; END IF;
  SELECT * INTO r FROM public.exercises WHERE id = v_cloze;
  IF r.content_version <> v_n1 OR r.dedupe_key IS NOT NULL OR r.tags <> '{"variant": "A"}'::jsonb
     OR r.complexity_tier <> 'T2' OR r.content->>'context_sentence' <> 'S1' THEN
    RAISE EXCEPTION 'FAIL inserted context-bearing row: version % dedupe % tags %',
      r.content_version, r.dedupe_key, r.tags; END IF;

  -- 2c. begin again: the version and the rows (ordered by id, metadata keys only)
  b := public.exercise_content_begin(v_sense);
  IF (b->>'current_version')::int <> v_n1 OR jsonb_array_length(b->'rows') <> 2
     OR (b->'rows'->0->>'id')::uuid > (b->'rows'->1->>'id')::uuid
     OR (SELECT array_agg(k ORDER BY k COLLATE "C") FROM jsonb_object_keys(b->'rows'->0) k)
        <> ARRAY['content_version', 'exercise_type', 'id', 'is_active', 'ladder_level',
                 'language_id', 'word_asset_id'] THEN
    RAISE EXCEPTION 'FAIL begin after a commit: %', b; END IF;
  v_n2 := (b->>'new_version')::int;
  IF v_n2 <= v_n1 THEN RAISE EXCEPTION 'FAIL versions must increase: % then %', v_n1, v_n2; END IF;
  SELECT array_agg(x.id ORDER BY x.id) INTO v_ids
    FROM (SELECT (j->>'id')::uuid AS id FROM jsonb_array_elements(b->'rows') j) x;

  -- 2d. stale expected version -> version_conflict, nothing changed
  c := public.exercise_content_commit(v_sense, 0, v_ids, v_n2, ARRAY[v_cloze], '[]', '{}');
  IF c <> jsonb_build_object('ok', false, 'reason', 'version_conflict', 'current_version', v_n1) THEN
    RAISE EXCEPTION 'FAIL stale version must give version_conflict: %', c; END IF;
  IF (SELECT count(*) FROM public.exercises WHERE word_sense_id = v_sense AND content_version = v_n1) <> 2 THEN
    RAISE EXCEPTION 'FAIL version_conflict must change nothing'; END IF;

  -- 2e. a row deleted between begin and commit -> rows_changed, nothing changed
  DELETE FROM public.exercises WHERE id = v_cloze;
  c := public.exercise_content_commit(v_sense, v_n1, v_ids, v_n2, '{}', '[]',
                                      jsonb_build_object(v_tone::text, jsonb_build_object('prompt', 'p2')));
  IF c <> jsonb_build_object('ok', false, 'reason', 'rows_changed', 'current_version', v_n1) THEN
    RAISE EXCEPTION 'FAIL deleted row must give rows_changed: %', c; END IF;
  IF (SELECT content FROM public.exercises WHERE id = v_tone) <> jsonb_build_object('prompt', 'p1') THEN
    RAISE EXCEPTION 'FAIL rows_changed must change nothing'; END IF;

  -- 2f. a row inserted outside the store between begin and commit -> rows_changed too
  INSERT INTO public.exercises (id, language_id, exercise_type, source_type, word_sense_id, content)
  VALUES (v_rogue, v_lang, 'text_flashcard', 'vocabulary', v_sense, '{"front": "x"}');
  c := public.exercise_content_commit(v_sense, v_n1, ARRAY[v_tone], v_n2, '{}', '[]', '{}');
  IF c->>'reason' IS DISTINCT FROM 'rows_changed' THEN
    RAISE EXCEPTION 'FAIL inserted row must give rows_changed: %', c; END IF;
  DELETE FROM public.exercises WHERE id = v_rogue;

  -- 2g. bad input -> SQLSTATE 22023 (insert for another sense, stale p_new_version,
  --     delete/update id outside the sense, update of a deleted row)
  BEGIN
    PERFORM public.exercise_content_commit(v_sense, v_n1, ARRAY[v_tone], v_n2, '{}',
      jsonb_build_array(jsonb_build_object('id', v_third, 'language_id', v_lang,
        'exercise_type', 'cloze_completion', 'source_type', 'vocabulary',
        'word_sense_id', v_other, 'content', '{}'::jsonb)), '{}');
    RAISE EXCEPTION 'FAIL insert row for another sense must raise 22023';
  EXCEPTION WHEN SQLSTATE '22023' THEN v_state := 'ok'; END;
  BEGIN
    PERFORM public.exercise_content_commit(v_sense, v_n1, ARRAY[v_tone], v_n1, '{}', '[]', '{}');
    RAISE EXCEPTION 'FAIL p_new_version <= current must raise 22023';
  EXCEPTION WHEN SQLSTATE '22023' THEN v_state := 'ok'; END;
  BEGIN
    PERFORM public.exercise_content_commit(v_sense, v_n1, ARRAY[v_tone], v_n2, ARRAY[v_rogue], '[]', '{}');
    RAISE EXCEPTION 'FAIL delete id outside the sense must raise 22023';
  EXCEPTION WHEN SQLSTATE '22023' THEN v_state := 'ok'; END;
  BEGIN
    PERFORM public.exercise_content_commit(v_sense, v_n1, ARRAY[v_tone], v_n2, '{}', '[]',
      jsonb_build_object(v_rogue::text, '{}'::jsonb));
    RAISE EXCEPTION 'FAIL update id outside the sense must raise 22023';
  EXCEPTION WHEN SQLSTATE '22023' THEN v_state := 'ok'; END;
  BEGIN
    PERFORM public.exercise_content_commit(v_sense, v_n1, ARRAY[v_tone], v_n2, ARRAY[v_tone], '[]',
      jsonb_build_object(v_tone::text, '{}'::jsonb));
    RAISE EXCEPTION 'FAIL update of a deleted row must raise 22023';
  EXCEPTION WHEN SQLSTATE '22023' THEN v_state := 'ok'; END;
  IF (SELECT count(*) FROM public.exercises WHERE word_sense_id = v_sense) <> 1 THEN
    RAISE EXCEPTION 'FAIL rejected commits must change nothing'; END IF;

  -- 2h. update recomputes dedupe_key; insert + update stamp the new version on every row
  c := public.exercise_content_commit(v_sense, v_n1, ARRAY[v_tone], v_n2, '{}',
         jsonb_build_array(jsonb_build_object('id', v_third, 'language_id', v_lang,
           'exercise_type', 'hanzi_to_pinyin', 'source_type', 'vocabulary', 'word_sense_id', v_sense,
           'ladder_level', 1, 'content', jsonb_build_object('context_sentence', 'S3'))),
         jsonb_build_object(v_tone::text, jsonb_build_object('prompt', 'p2', 'context_sentence', 'S2')));
  IF c <> jsonb_build_object('ok', true, 'version', v_n2, 'deleted', 0, 'inserted', 1, 'updated', 1) THEN
    RAISE EXCEPTION 'FAIL second commit result: %', c; END IF;
  IF (SELECT dedupe_key FROM public.exercises WHERE id = v_tone) IS DISTINCT FROM md5('S2')
     OR (SELECT content->>'prompt' FROM public.exercises WHERE id = v_tone) <> 'p2'
     OR (SELECT dedupe_key FROM public.exercises WHERE id = v_third) IS DISTINCT FROM md5('S3') THEN
    RAISE EXCEPTION 'FAIL update must rewrite content and recompute dedupe_key'; END IF;
  IF EXISTS (SELECT 1 FROM public.exercises WHERE word_sense_id = v_sense AND content_version <> v_n2) THEN
    RAISE EXCEPTION 'FAIL every row of the sense must carry the committed version'; END IF;

  -- 2i. delete through commit
  b := public.exercise_content_begin(v_sense);
  v_n3 := (b->>'new_version')::int;
  c := public.exercise_content_commit(v_sense, v_n2, ARRAY[v_third, v_tone], v_n3, ARRAY[v_third], '[]', '{}');
  IF c <> jsonb_build_object('ok', true, 'version', v_n3, 'deleted', 1, 'inserted', 0, 'updated', 0)
     OR EXISTS (SELECT 1 FROM public.exercises WHERE id = v_third)
     OR (SELECT content_version FROM public.exercises WHERE id = v_tone) <> v_n3 THEN
    RAISE EXCEPTION 'FAIL delete commit: %', c; END IF;

  -- 2j. live_versions: {"<sense>": [versions ascending]}, mixed versions included
  INSERT INTO public.exercises (id, language_id, exercise_type, source_type, word_sense_id, content)
  VALUES (v_rogue, v_lang, 'text_flashcard', 'vocabulary', v_sense, '{"front": "x"}');   -- version 0
  b := public.exercise_content_live_versions(v_lang);
  IF jsonb_typeof(b) <> 'object' OR b->(v_sense::text) <> jsonb_build_array(0, v_n3) THEN
    RAISE EXCEPTION 'FAIL live_versions for sense %: %', v_sense, b->(v_sense::text); END IF;
  IF EXISTS (SELECT 1 FROM jsonb_each(b) j
              WHERE jsonb_typeof(j.value) <> 'array' OR j.key !~ '^[0-9]+$') THEN
    RAISE EXCEPTION 'FAIL live_versions must map sense ids to arrays'; END IF;
  IF public.exercise_content_live_versions(-1) <> '{}'::jsonb THEN
    RAISE EXCEPTION 'FAIL live_versions of an unknown language must be {}'; END IF;

  RAISE NOTICE 'exercise_content begin/commit/CAS/validation/live_versions PASS (sense %, versions % % %)',
    v_sense, v_n1, v_n2, v_n3;
END $test$;

-- ---- 3. The service role can run the write path (sequence USAGE, table grants) ------------
SET LOCAL ROLE service_role;
DO $test$
DECLARE b jsonb;
BEGIN
  b := public.exercise_content_begin(0);   -- no sense 0: reads the table, draws a version
  IF (b->>'new_version')::int < 1 OR (b->>'current_version')::int <> 0 THEN
    RAISE EXCEPTION 'FAIL begin as service_role: %', b; END IF;
  RAISE NOTICE 'exercise_content service_role PASS';
END $test$;
RESET ROLE;

ROLLBACK;
