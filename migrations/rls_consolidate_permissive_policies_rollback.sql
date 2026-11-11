-- Rollback for migrations/rls_consolidate_permissive_policies.sql (TASK-932).
-- Captured 2026-11-11 by the developer with that file's ROLLBACK GENERATOR query,
-- after TASK-875 / 880 / 882 were applied and before the consolidation: 78 policies
-- on 45 tables. Restores exactly that policy set: drops every policy on those
-- tables (the merged rls_* ones included), then recreates the captured ones.
-- Only for undoing the consolidation; any policy added to these tables later is dropped too.

BEGIN;

DO $$
DECLARE p record;
BEGIN
  FOR p IN SELECT tablename, policyname FROM pg_policies
            WHERE schemaname = 'public'
              AND tablename = ANY (ARRAY['app_error_logs', 'calibration_anchor_blocklist', 'calibration_response_options', 'calibration_responses', 'calibration_sessions', 'daily_test_load_items', 'daily_test_loads', 'dim_character_components', 'dim_complexity_tiers', 'dim_counter_distractor_groups', 'dim_counter_noun_pairs', 'dim_counters', 'dim_distractor_bands', 'dim_languages', 'dim_lens', 'dim_question_types', 'dim_status', 'dim_study_plan_templates', 'dim_subscription_tiers', 'dim_test_types', 'dim_vocabulary', 'dim_word_senses', 'exercise_attempts', 'question_attempt_results', 'test_attempts', 'test_skill_ratings', 'tests', 'token_transactions', 'trusted_devices', 'user_calibration_state', 'user_exercise_history', 'user_exercise_sessions', 'user_flashcards', 'user_languages', 'user_reports', 'user_skill_rating_adjustments', 'user_skill_ratings', 'user_study_plans', 'user_tokens', 'user_vocabulary_knowledge', 'user_word_ladder', 'user_word_watchlist', 'users', 'weekly_plan_states', 'word_quiz_results'])
  LOOP
    EXECUTE format('DROP POLICY %I ON public.%I', p.policyname, p.tablename);
  END LOOP;
END $$;

CREATE POLICY "Admin and service read error logs" ON public.app_error_logs AS PERMISSIVE FOR SELECT TO public USING ((is_admin(( SELECT auth.uid() AS uid)) OR (( SELECT auth.role() AS role) = 'service_role'::text)));
CREATE POLICY "Authenticated insert error logs" ON public.app_error_logs AS PERMISSIVE FOR INSERT TO public WITH CHECK (((( SELECT auth.uid() AS uid) IS NOT NULL) OR (( SELECT auth.role() AS role) = 'service_role'::text)));
CREATE POLICY "Service role manage error logs" ON public.app_error_logs AS PERMISSIVE FOR ALL TO public USING ((( SELECT auth.role() AS role) = 'service_role'::text));
CREATE POLICY calibration_blocklist_read ON public.calibration_anchor_blocklist AS PERMISSIVE FOR SELECT TO authenticated USING (true);
CREATE POLICY "calibration_options_own (select)" ON public.calibration_response_options AS PERMISSIVE FOR SELECT TO authenticated USING ((EXISTS ( SELECT 1
   FROM calibration_responses r
  WHERE ((r.id = calibration_response_options.response_id) AND (r.user_id = ( SELECT auth.uid() AS uid))))));
CREATE POLICY "calibration_responses_own (select)" ON public.calibration_responses AS PERMISSIVE FOR SELECT TO authenticated USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY "calibration_sessions_own (select)" ON public.calibration_sessions AS PERMISSIVE FOR SELECT TO authenticated USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY dtli_admin_view ON public.daily_test_load_items AS PERMISSIVE FOR SELECT TO public USING ((is_admin(( SELECT auth.uid() AS uid)) OR (EXISTS ( SELECT 1
   FROM daily_test_loads d
  WHERE ((d.id = daily_test_load_items.load_id) AND (d.user_id = ( SELECT auth.uid() AS uid)))))));
CREATE POLICY "dtli_own_data (select)" ON public.daily_test_load_items AS PERMISSIVE FOR SELECT TO public USING ((EXISTS ( SELECT 1
   FROM daily_test_loads d
  WHERE ((d.id = daily_test_load_items.load_id) AND (d.user_id = ( SELECT auth.uid() AS uid))))));
CREATE POLICY dtl_admin_view ON public.daily_test_loads AS PERMISSIVE FOR SELECT TO public USING (is_admin(( SELECT auth.uid() AS uid)));
CREATE POLICY "dtl_own_data (select)" ON public.daily_test_loads AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY dim_character_components_read ON public.dim_character_components AS PERMISSIVE FOR SELECT TO public USING (true);
CREATE POLICY "Authenticated read complexity tiers" ON public.dim_complexity_tiers AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.role() AS role) = ANY (ARRAY['authenticated'::text, 'service_role'::text])));
CREATE POLICY "Service role manage complexity tiers" ON public.dim_complexity_tiers AS PERMISSIVE FOR ALL TO public USING ((( SELECT auth.role() AS role) = 'service_role'::text));
CREATE POLICY dim_counter_groups_read ON public.dim_counter_distractor_groups AS PERMISSIVE FOR SELECT TO public USING (true);
CREATE POLICY dim_counter_noun_pairs_read ON public.dim_counter_noun_pairs AS PERMISSIVE FOR SELECT TO public USING (true);
CREATE POLICY dim_counters_read ON public.dim_counters AS PERMISSIVE FOR SELECT TO public USING (true);
CREATE POLICY dim_distractor_bands_read ON public.dim_distractor_bands AS PERMISSIVE FOR SELECT TO authenticated, service_role USING (true);
CREATE POLICY dim_languages_public_read ON public.dim_languages AS PERMISSIVE FOR SELECT TO public USING ((is_active = true));
CREATE POLICY "Authenticated read lens codes" ON public.dim_lens AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.role() AS role) = ANY (ARRAY['authenticated'::text, 'service_role'::text])));
CREATE POLICY "Service role manage lens codes" ON public.dim_lens AS PERMISSIVE FOR ALL TO public USING ((( SELECT auth.role() AS role) = 'service_role'::text));
CREATE POLICY "Authenticated read question types" ON public.dim_question_types AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.role() AS role) = ANY (ARRAY['authenticated'::text, 'service_role'::text])));
CREATE POLICY "Service role manage question types" ON public.dim_question_types AS PERMISSIVE FOR ALL TO public USING ((( SELECT auth.role() AS role) = 'service_role'::text));
CREATE POLICY "Authenticated read status codes" ON public.dim_status AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.role() AS role) = ANY (ARRAY['authenticated'::text, 'service_role'::text])));
CREATE POLICY "Service role manage status codes" ON public.dim_status AS PERMISSIVE FOR ALL TO public USING ((( SELECT auth.role() AS role) = 'service_role'::text));
CREATE POLICY dim_study_plan_templates_public_read ON public.dim_study_plan_templates AS PERMISSIVE FOR SELECT TO public USING (true);
CREATE POLICY dim_tiers_public_read ON public.dim_subscription_tiers AS PERMISSIVE FOR SELECT TO public USING ((is_active = true));
CREATE POLICY dim_test_types_public_read ON public.dim_test_types AS PERMISSIVE FOR SELECT TO public USING ((is_active = true));
CREATE POLICY "Anyone can read vocabulary" ON public.dim_vocabulary AS PERMISSIVE FOR SELECT TO public USING (true);
CREATE POLICY "Anyone can read word senses" ON public.dim_word_senses AS PERMISSIVE FOR SELECT TO public USING (true);
CREATE POLICY ea_admin_view ON public.exercise_attempts AS PERMISSIVE FOR SELECT TO public USING (is_admin(( SELECT auth.uid() AS uid)));
CREATE POLICY "ea_own_data (select)" ON public.exercise_attempts AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY qar_admin_view ON public.question_attempt_results AS PERMISSIVE FOR SELECT TO public USING (is_admin(( SELECT auth.uid() AS uid)));
CREATE POLICY "qar_own_data (select)" ON public.question_attempt_results AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY "Users can view own attempts" ON public.test_attempts AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY attempts_moderator_view ON public.test_attempts AS PERMISSIVE FOR SELECT TO public USING (is_moderator(( SELECT auth.uid() AS uid)));
CREATE POLICY attempts_select_own ON public.test_attempts AS PERMISSIVE FOR SELECT TO public USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY public_free_skill_ratings ON public.test_skill_ratings AS PERMISSIVE FOR SELECT TO public USING ((EXISTS ( SELECT 1
   FROM tests
  WHERE ((tests.id = test_skill_ratings.test_id) AND (tests.is_active = true) AND (tests.tier = 'free-tier'::text)))));
CREATE POLICY public_free_tests ON public.tests AS PERMISSIVE FOR SELECT TO public USING (((is_active = true) AND (tier = 'free-tier'::text)));
CREATE POLICY tests_authenticated_read ON public.tests AS PERMISSIVE FOR SELECT TO authenticated USING ((is_active IS TRUE));
CREATE POLICY tests_moderator_view ON public.tests AS PERMISSIVE FOR SELECT TO public USING (is_moderator(( SELECT auth.uid() AS uid)));
CREATE POLICY "Users can view own transactions" ON public.token_transactions AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY transactions_admin_view ON public.token_transactions AS PERMISSIVE FOR SELECT TO public USING (is_admin(( SELECT auth.uid() AS uid)));
CREATE POLICY transactions_select_own ON public.token_transactions AS PERMISSIVE FOR SELECT TO public USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY td_admin_view ON public.trusted_devices AS PERMISSIVE FOR SELECT TO public USING (is_admin(( SELECT auth.uid() AS uid)));
CREATE POLICY td_service_role ON public.trusted_devices AS PERMISSIVE FOR ALL TO public USING ((( SELECT auth.role() AS role) = 'service_role'::text));
CREATE POLICY "user_calibration_state_own (select)" ON public.user_calibration_state AS PERMISSIVE FOR SELECT TO authenticated USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY "Service role full access on exercise history" ON public.user_exercise_history AS PERMISSIVE FOR ALL TO public USING ((( SELECT auth.role() AS role) = 'service_role'::text));
CREATE POLICY "Users read own exercise history" ON public.user_exercise_history AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY "Users read own sessions" ON public.user_exercise_sessions AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY uf_admin_view ON public.user_flashcards AS PERMISSIVE FOR SELECT TO public USING (is_admin(( SELECT auth.uid() AS uid)));
CREATE POLICY "uf_own_data (select)" ON public.user_flashcards AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY "Users can view own languages" ON public.user_languages AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY user_languages_admin_view ON public.user_languages AS PERMISSIVE FOR SELECT TO public USING (is_admin(( SELECT auth.uid() AS uid)));
CREATE POLICY "Users can create reports" ON public.user_reports AS PERMISSIVE FOR INSERT TO public WITH CHECK ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY "Users can view own reports" ON public.user_reports AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY usra_select_own ON public.user_skill_rating_adjustments AS PERMISSIVE FOR SELECT TO authenticated USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY "Users can view own skill ratings" ON public.user_skill_ratings AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY ratings_admin_view ON public.user_skill_ratings AS PERMISSIVE FOR SELECT TO public USING (is_admin(( SELECT auth.uid() AS uid)));
CREATE POLICY ratings_select_own ON public.user_skill_ratings AS PERMISSIVE FOR SELECT TO public USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY user_study_plans_self_select ON public.user_study_plans AS PERMISSIVE FOR SELECT TO public USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "Users can view own tokens" ON public.user_tokens AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY tokens_admin_view ON public.user_tokens AS PERMISSIVE FOR SELECT TO public USING (is_admin(( SELECT auth.uid() AS uid)));
CREATE POLICY uvk_admin_view ON public.user_vocabulary_knowledge AS PERMISSIVE FOR SELECT TO public USING (is_admin(( SELECT auth.uid() AS uid)));
CREATE POLICY "uvk_own_data (select)" ON public.user_vocabulary_knowledge AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY uwl_admin_view ON public.user_word_ladder AS PERMISSIVE FOR SELECT TO public USING (is_admin(( SELECT auth.uid() AS uid)));
CREATE POLICY "uwl_own_data (select)" ON public.user_word_ladder AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY uww_admin_view ON public.user_word_watchlist AS PERMISSIVE FOR SELECT TO public USING (is_admin(( SELECT auth.uid() AS uid)));
CREATE POLICY uww_own_data ON public.user_word_watchlist AS PERMISSIVE FOR ALL TO public USING ((( SELECT auth.uid() AS uid) = user_id)) WITH CHECK ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY uww_service_role ON public.user_word_watchlist AS PERMISSIVE FOR ALL TO public USING ((( SELECT auth.role() AS role) = 'service_role'::text));
CREATE POLICY "Admin read all users" ON public.users AS PERMISSIVE FOR SELECT TO public USING (is_admin(( SELECT auth.uid() AS uid)));
CREATE POLICY "Service role full access on users" ON public.users AS PERMISSIVE FOR ALL TO public USING ((( SELECT auth.role() AS role) = 'service_role'::text));
CREATE POLICY "Users can view own profile" ON public.users AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.uid() AS uid) = id));
CREATE POLICY "Users read own profile" ON public.users AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.uid() AS uid) = id));
CREATE POLICY users_select_own ON public.users AS PERMISSIVE FOR SELECT TO public USING (((id = ( SELECT auth.uid() AS uid)) AND (deleted_at IS NULL)));
CREATE POLICY weekly_plan_states_self_select ON public.weekly_plan_states AS PERMISSIVE FOR SELECT TO public USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY wqr_admin_view ON public.word_quiz_results AS PERMISSIVE FOR SELECT TO public USING (is_admin(( SELECT auth.uid() AS uid)));
CREATE POLICY "wqr_own_data (select)" ON public.word_quiz_results AS PERMISSIVE FOR SELECT TO public USING ((( SELECT auth.uid() AS uid) = user_id));

DO $$
BEGIN
  IF (SELECT count(*) FROM pg_policies WHERE schemaname = 'public'
        AND tablename = ANY (ARRAY['app_error_logs', 'calibration_anchor_blocklist', 'calibration_response_options', 'calibration_responses', 'calibration_sessions', 'daily_test_load_items', 'daily_test_loads', 'dim_character_components', 'dim_complexity_tiers', 'dim_counter_distractor_groups', 'dim_counter_noun_pairs', 'dim_counters', 'dim_distractor_bands', 'dim_languages', 'dim_lens', 'dim_question_types', 'dim_status', 'dim_study_plan_templates', 'dim_subscription_tiers', 'dim_test_types', 'dim_vocabulary', 'dim_word_senses', 'exercise_attempts', 'question_attempt_results', 'test_attempts', 'test_skill_ratings', 'tests', 'token_transactions', 'trusted_devices', 'user_calibration_state', 'user_exercise_history', 'user_exercise_sessions', 'user_flashcards', 'user_languages', 'user_reports', 'user_skill_rating_adjustments', 'user_skill_ratings', 'user_study_plans', 'user_tokens', 'user_vocabulary_knowledge', 'user_word_ladder', 'user_word_watchlist', 'users', 'weekly_plan_states', 'word_quiz_results'])) <> 78 THEN
    RAISE EXCEPTION 'rollback: policy count differs from the captured 78';
  END IF;
END $$;

COMMIT;
