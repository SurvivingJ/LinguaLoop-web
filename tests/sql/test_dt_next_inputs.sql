-- =============================================================================
-- dt_next_inputs (migrations/dt_next_inputs.sql) — rollback-only SQL test
-- =============================================================================
-- Run after the migration is applied, as the migration owner (postgres):
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_dt_next_inputs.sql
--
-- Creates nothing permanent (one transaction, ROLLBACK). Uses the learner with
-- the most dt_submission rows. Asserts, printing PASS notices:
--   1. the function exists, is SECURITY INVOKER, STABLE, has search_path set;
--   2. anon and authenticated cannot execute it (service_role can);
--   3. its parts agree with direct queries for that learner: salt / history =
--      distinct served passages, graded flags, open ids, attempted tests,
--      candidate tests (active, in l2, with a usable reference in l1), and
--      that every history row belongs to the learner (no other user's
--      submissions leak in);
--   4. the retired whole-passage pool is not returned (no `legacy` key);
--   5. l2 / l1 resolution with NULL arguments.
-- =============================================================================

BEGIN;

DO $$
DECLARE
  v_user uuid;
  v_l2 integer;
  v_l1 integer;
  j jsonb;
  n bigint;
  m bigint;
  f record;
BEGIN
  SELECT p.prosecdef AS definer, p.provolatile AS vol, p.proconfig::text AS cfg INTO f
    FROM pg_proc p JOIN pg_namespace ns ON ns.oid = p.pronamespace
   WHERE ns.nspname = 'public' AND p.proname = 'dt_next_inputs';
  IF NOT FOUND THEN RAISE EXCEPTION 'FAIL: public.dt_next_inputs missing'; END IF;
  IF f.definer THEN RAISE EXCEPTION 'FAIL: must be SECURITY INVOKER'; END IF;
  IF f.vol <> 's' THEN RAISE EXCEPTION 'FAIL: must be STABLE'; END IF;
  IF f.cfg IS NULL OR f.cfg NOT LIKE '%search_path=public, pg_temp%' THEN
    RAISE EXCEPTION 'FAIL: search_path not pinned (%)', f.cfg; END IF;
  RAISE NOTICE 'PASS: invoker, stable, search_path';

  IF has_function_privilege('anon', 'public.dt_next_inputs(uuid, integer, integer)', 'EXECUTE')
     OR has_function_privilege('authenticated', 'public.dt_next_inputs(uuid, integer, integer)', 'EXECUTE') THEN
    RAISE EXCEPTION 'FAIL: a client role can execute dt_next_inputs';
  END IF;
  IF NOT has_function_privilege('service_role', 'public.dt_next_inputs(uuid, integer, integer)', 'EXECUTE') THEN
    RAISE EXCEPTION 'FAIL: service_role cannot execute dt_next_inputs';
  END IF;
  RAISE NOTICE 'PASS: execute only for service_role';

  SELECT s.user_id INTO v_user FROM public.dt_submission s
   GROUP BY s.user_id ORDER BY count(*) DESC LIMIT 1;
  IF v_user IS NULL THEN RAISE NOTICE 'SKIP: no dt_submission rows'; RETURN; END IF;
  SELECT p.l2_language_id INTO v_l2 FROM public.dt_submission s JOIN public.dt_passage p ON p.id = s.passage_id
   WHERE s.user_id = v_user GROUP BY 1 ORDER BY count(*) DESC LIMIT 1;
  SELECT COALESCE(NULLIF(native_language_id, 0), 2) INTO v_l1 FROM public.users WHERE id = v_user;
  v_l1 := COALESCE(v_l1, 2);

  j := public.dt_next_inputs(v_user, v_l2, NULL);

  IF (j->>'l1')::int <> v_l1 OR (j->>'l2')::int <> v_l2 THEN
    RAISE EXCEPTION 'FAIL: languages % / % (want % / %)', j->>'l1', j->>'l2', v_l1, v_l2; END IF;

  SELECT count(DISTINCT passage_id) INTO n FROM public.dt_submission WHERE user_id = v_user;
  IF (j->>'salt')::bigint <> n THEN RAISE EXCEPTION 'FAIL: salt % <> %', j->>'salt', n; END IF;
  IF jsonb_array_length(j->'history') <> n THEN RAISE EXCEPTION 'FAIL: history rows'; END IF;

  SELECT count(*) INTO m FROM jsonb_array_elements(j->'history') h
   WHERE NOT EXISTS (SELECT 1 FROM public.dt_submission s
                      WHERE s.user_id = v_user AND s.passage_id = (h->>'p')::bigint);
  IF m <> 0 THEN RAISE EXCEPTION 'FAIL: % history rows not of this learner', m; END IF;

  SELECT count(DISTINCT s.passage_id) INTO n FROM public.dt_submission s
    JOIN public.dt_grade g ON g.submission_id = s.id WHERE s.user_id = v_user;
  SELECT count(*) INTO m FROM jsonb_array_elements(j->'history') h WHERE (h->>'g')::boolean;
  IF n <> m THEN RAISE EXCEPTION 'FAIL: graded passages % <> %', m, n; END IF;

  SELECT count(*) INTO m FROM jsonb_array_elements(j->'history') h
   WHERE h->>'o' IS NOT NULL AND NOT EXISTS (
     SELECT 1 FROM public.dt_submission s LEFT JOIN public.dt_grade g ON g.submission_id = s.id
      WHERE s.id = (h->>'o')::bigint AND s.user_id = v_user AND g.id IS NULL
        AND coalesce(s.reproduction, '') = '' AND s.l1_language_id = v_l1);
  IF m <> 0 THEN RAISE EXCEPTION 'FAIL: % open ids are not open submissions of the learner', m; END IF;
  RAISE NOTICE 'PASS: history, graded flags, open submissions';

  SELECT count(DISTINCT test_id) INTO n FROM public.test_attempts WHERE user_id = v_user AND test_id IS NOT NULL;
  IF jsonb_array_length(j->'attempted') <> n THEN RAISE EXCEPTION 'FAIL: attempted tests'; END IF;

  SELECT count(*) INTO n FROM public.tests t
   WHERE t.is_active AND t.language_id = v_l2 AND EXISTS (
     SELECT 1 FROM public.test_sentences s JOIN public.test_sentence_references r ON r.sentence_id = s.id
      WHERE s.test_id = t.id AND r.l1_language_id = v_l1 AND r.is_active
        AND r.review_verdict IN ('pass', 'rewritten'));
  IF jsonb_array_length(j->'tests') <> n THEN
    RAISE EXCEPTION 'FAIL: candidate tests % <> %', jsonb_array_length(j->'tests'), n; END IF;

  RAISE NOTICE 'PASS: attempted, candidate tests';

  IF j ? 'legacy' THEN RAISE EXCEPTION 'FAIL: retired legacy array still returned'; END IF;
  RAISE NOTICE 'PASS: no legacy pool';

  -- NULL l2 resolves to the latest attempt's language.
  j := public.dt_next_inputs(v_user, NULL, NULL);
  SELECT language_id INTO v_l2 FROM public.test_attempts WHERE user_id = v_user
   ORDER BY created_at DESC NULLS LAST, id DESC LIMIT 1;
  IF (j->>'l2')::int IS DISTINCT FROM v_l2 THEN RAISE EXCEPTION 'FAIL: NULL l2 resolution'; END IF;
  RAISE NOTICE 'PASS: NULL argument resolution';
END $$;

ROLLBACK;
