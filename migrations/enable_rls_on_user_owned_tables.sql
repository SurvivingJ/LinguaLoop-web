-- migrations/enable_rls_on_user_owned_tables.sql
-- Closes the RLS audit gap surfaced in the 2026-05-12 wiki audit.
-- 7 user-owning tables had RLS disabled, exposing every user's learning data
-- to anyone holding the anon Supabase key. This migration enables RLS and
-- adds the standard own-data + service-role + admin-view policy triple,
-- mirroring the pattern already used on user_languages / user_skill_ratings
-- / user_tokens / user_exercise_history / user_pack_selections.
--
-- All seven tables are accessed exclusively via get_supabase_admin()
-- (service-role) in the application today, so enabling RLS does not break
-- any existing call site. The own-data policy future-proofs the tables for
-- direct frontend (anon-client) access.
--
-- Idempotent: safe to re-apply. Each CREATE POLICY is paired with
-- DROP POLICY IF EXISTS; ENABLE ROW LEVEL SECURITY is naturally idempotent.

-- ===========================================================================
-- 1. user_vocabulary_knowledge
-- ===========================================================================
ALTER TABLE public.user_vocabulary_knowledge ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS uvk_own_data ON public.user_vocabulary_knowledge;
CREATE POLICY uvk_own_data ON public.user_vocabulary_knowledge
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS uvk_service_role ON public.user_vocabulary_knowledge;
CREATE POLICY uvk_service_role ON public.user_vocabulary_knowledge
  FOR ALL
  USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS uvk_admin_view ON public.user_vocabulary_knowledge;
CREATE POLICY uvk_admin_view ON public.user_vocabulary_knowledge
  FOR SELECT
  USING (is_admin(auth.uid()));


-- ===========================================================================
-- 2. user_flashcards
-- ===========================================================================
ALTER TABLE public.user_flashcards ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS uf_own_data ON public.user_flashcards;
CREATE POLICY uf_own_data ON public.user_flashcards
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS uf_service_role ON public.user_flashcards;
CREATE POLICY uf_service_role ON public.user_flashcards
  FOR ALL
  USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS uf_admin_view ON public.user_flashcards;
CREATE POLICY uf_admin_view ON public.user_flashcards
  FOR SELECT
  USING (is_admin(auth.uid()));


-- ===========================================================================
-- 3. user_word_ladder
-- ===========================================================================
ALTER TABLE public.user_word_ladder ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS uwl_own_data ON public.user_word_ladder;
CREATE POLICY uwl_own_data ON public.user_word_ladder
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS uwl_service_role ON public.user_word_ladder;
CREATE POLICY uwl_service_role ON public.user_word_ladder
  FOR ALL
  USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS uwl_admin_view ON public.user_word_ladder;
CREATE POLICY uwl_admin_view ON public.user_word_ladder
  FOR SELECT
  USING (is_admin(auth.uid()));


-- ===========================================================================
-- 4. word_quiz_results
-- ===========================================================================
ALTER TABLE public.word_quiz_results ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS wqr_own_data ON public.word_quiz_results;
CREATE POLICY wqr_own_data ON public.word_quiz_results
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS wqr_service_role ON public.word_quiz_results;
CREATE POLICY wqr_service_role ON public.word_quiz_results
  FOR ALL
  USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS wqr_admin_view ON public.word_quiz_results;
CREATE POLICY wqr_admin_view ON public.word_quiz_results
  FOR SELECT
  USING (is_admin(auth.uid()));


-- ===========================================================================
-- 5. exercise_attempts
-- ===========================================================================
ALTER TABLE public.exercise_attempts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS ea_own_data ON public.exercise_attempts;
CREATE POLICY ea_own_data ON public.exercise_attempts
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS ea_service_role ON public.exercise_attempts;
CREATE POLICY ea_service_role ON public.exercise_attempts
  FOR ALL
  USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS ea_admin_view ON public.exercise_attempts;
CREATE POLICY ea_admin_view ON public.exercise_attempts
  FOR SELECT
  USING (is_admin(auth.uid()));


-- ===========================================================================
-- 6. daily_test_loads
-- ===========================================================================
ALTER TABLE public.daily_test_loads ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS dtl_own_data ON public.daily_test_loads;
CREATE POLICY dtl_own_data ON public.daily_test_loads
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS dtl_service_role ON public.daily_test_loads;
CREATE POLICY dtl_service_role ON public.daily_test_loads
  FOR ALL
  USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS dtl_admin_view ON public.daily_test_loads;
CREATE POLICY dtl_admin_view ON public.daily_test_loads
  FOR SELECT
  USING (is_admin(auth.uid()));


-- ===========================================================================
-- 7. daily_test_load_items
-- No user_id column — join through load_id -> daily_test_loads(user_id).
-- ===========================================================================
ALTER TABLE public.daily_test_load_items ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS dtli_own_data ON public.daily_test_load_items;
CREATE POLICY dtli_own_data ON public.daily_test_load_items
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.daily_test_loads d
      WHERE d.id = daily_test_load_items.load_id
        AND d.user_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.daily_test_loads d
      WHERE d.id = daily_test_load_items.load_id
        AND d.user_id = auth.uid()
    )
  );

DROP POLICY IF EXISTS dtli_service_role ON public.daily_test_load_items;
CREATE POLICY dtli_service_role ON public.daily_test_load_items
  FOR ALL
  USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS dtli_admin_view ON public.daily_test_load_items;
CREATE POLICY dtli_admin_view ON public.daily_test_load_items
  FOR SELECT
  USING (
    is_admin(auth.uid())
    OR EXISTS (
      SELECT 1 FROM public.daily_test_loads d
      WHERE d.id = daily_test_load_items.load_id
        AND d.user_id = auth.uid()
    )
  );


-- ===========================================================================
-- Verification queries (run after apply)
-- ===========================================================================
-- 1) All 7 tables should report rowsecurity = true:
--    SELECT tablename, rowsecurity FROM pg_tables
--    WHERE schemaname = 'public' AND tablename IN (
--      'user_vocabulary_knowledge','user_flashcards','user_word_ladder',
--      'word_quiz_results','exercise_attempts','daily_test_loads',
--      'daily_test_load_items');
--
-- 2) Each table should have exactly 3 policies:
--    SELECT tablename, count(*) FROM pg_policies
--    WHERE schemaname = 'public' AND tablename IN (
--      'user_vocabulary_knowledge','user_flashcards','user_word_ladder',
--      'word_quiz_results','exercise_attempts','daily_test_loads',
--      'daily_test_load_items')
--    GROUP BY tablename;
