-- =============================================================================
-- Pairs with migrations/task740_phase5b_topic_recency_exclusion.sql, applied
-- live 2026-08-30 (see ADR-023).
-- =============================================================================
-- TASK-740 Phase 5b — get_recommended_tests topic-recency exclusion: SQL
-- unit test. Runs entirely inside a rollback-only transaction. Two tests
-- share one topic; the user has attempted one of them recently. Asserts the
-- OTHER test on the same topic is excluded from get_recommended_tests, and
-- that a third, unrelated-topic test is still returned.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_task740_phase5b_topic_recency.sql
-- =============================================================================

BEGIN;

DO $test$
DECLARE
  v_user     uuid;
  v_lang     smallint := 2;   -- en
  v_topic_a  uuid := gen_random_uuid();
  v_topic_b  uuid := gen_random_uuid();
  v_t1       uuid := gen_random_uuid();  -- topic A, attempted recently
  v_t2       uuid := gen_random_uuid();  -- topic A, never attempted
  v_t3       uuid := gen_random_uuid();  -- topic B, never attempted
  v_cat      integer;
  v_lens     integer;
  v_results  jsonb;
  v_t2_present boolean;
  v_t3_present boolean;
BEGIN
  SELECT id INTO v_user FROM public.users LIMIT 1;
  IF v_user IS NULL THEN RAISE EXCEPTION 'no users row available to satisfy FKs'; END IF;

  SELECT id INTO v_cat FROM public.categories LIMIT 1;
  SELECT id INTO v_lens FROM public.dim_lens LIMIT 1;

  INSERT INTO public.topics(id, category_id, concept_english, lens_id, keywords, target_age_tier, distinctive_vocabulary)
  VALUES
    (v_topic_a, v_cat, '__t740b_topic_a', v_lens, '{}', 1, '{}'),
    (v_topic_b, v_cat, '__t740b_topic_b', v_lens, '{}', 1, '{}');

  INSERT INTO public.tests(id, gen_user, slug, difficulty, tier, title, language_id, is_active, topic_id) VALUES
    (v_t1, v_user, '__t740b_a1', 1, 'free-tier', 'T740b A1', v_lang, true, v_topic_a),
    (v_t2, v_user, '__t740b_a2', 1, 'free-tier', 'T740b A2', v_lang, true, v_topic_a),
    (v_t3, v_user, '__t740b_b1', 1, 'free-tier', 'T740b B1', v_lang, true, v_topic_b);

  INSERT INTO public.test_skill_ratings(test_id, test_type_id, elo_rating) VALUES
    (v_t1, 1, 1200), (v_t2, 1, 1200), (v_t3, 1, 1200);

  -- User attempted v_t1 (topic A) just now.
  INSERT INTO public.test_attempts(
    user_id, test_id, test_type_id, language_id, created_at,
    score, total_questions, user_elo_before, test_elo_before,
    user_elo_after, test_elo_after
  )
  VALUES (v_user, v_t1, 1, v_lang, now(), 0, 1, 1200, 1200, 1200, 1200);

  v_results := (
    SELECT jsonb_agg(to_jsonb(r))
    FROM public.get_recommended_tests(v_user, v_lang, 14::smallint) r
  );

  v_t2_present := EXISTS (
    SELECT 1 FROM jsonb_array_elements(v_results) e WHERE e->>'test_id' = v_t2::text
  );
  v_t3_present := EXISTS (
    SELECT 1 FROM jsonb_array_elements(v_results) e WHERE e->>'test_id' = v_t3::text
  );

  IF v_t2_present THEN
    RAISE EXCEPTION
      'FAIL: v_t2 (same topic as a recently-attempted test) was returned: %', v_results;
  END IF;

  IF NOT v_t3_present THEN
    RAISE EXCEPTION
      'FAIL: v_t3 (unrelated topic) was wrongly excluded: %', v_results;
  END IF;

  RAISE NOTICE 'TASK-740 Phase 5b PASS: same-topic test excluded, unrelated-topic test retained';
END $test$;

ROLLBACK;
