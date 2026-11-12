-- Rollback for migrations/latency_2026_11_db.sql. Not applied; kept for an
-- operator who needs to undo it. Restores the pre-2026-11-11 objects exactly.

-- 1. resolve_plan_timezone back to the pg_timezone_names scan.
CREATE OR REPLACE FUNCTION public.resolve_plan_timezone(p_tz text)
 RETURNS text
 LANGUAGE sql
 STABLE
AS $function$
    SELECT COALESCE(
        (SELECT n.name
         FROM pg_timezone_names n
         WHERE n.name = btrim(COALESCE(p_tz, ''))
         LIMIT 1),
        'UTC'
    )
$function$;
REVOKE ALL ON FUNCTION public.resolve_plan_timezone(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.resolve_plan_timezone(text) TO service_role;
DROP TABLE IF EXISTS public.tz_names;

-- 2. The four duplicate indexes.
CREATE INDEX IF NOT EXISTS idx_cc_validated_lmi ON public.corpus_collocations
    USING btree (language_id, is_validated, lmi_score DESC) WHERE (is_validated = true);
CREATE INDEX IF NOT EXISTS idx_counter_pairs_counter ON public.dim_counter_noun_pairs USING btree (counter_id);
CREATE INDEX IF NOT EXISTS idx_counter_pairs_lemma ON public.dim_counter_noun_pairs USING btree (language_id, lemma_text);
CREATE UNIQUE INDEX IF NOT EXISTS uq_counter_noun_pairs_lemma_counter
    ON public.dim_counter_noun_pairs USING btree (language_id, lemma_text, counter_id);

-- 3. The foreign-key indexes.
DROP INDEX IF EXISTS public.idx_exercises_word_asset_id;
DROP INDEX IF EXISTS public.idx_user_exercise_history_exercise_id;
DROP INDEX IF EXISTS public.idx_user_exercise_history_sense_id;
DROP INDEX IF EXISTS public.idx_user_vocabulary_knowledge_sense_id;
DROP INDEX IF EXISTS public.idx_user_word_ladder_sense_id;
DROP INDEX IF EXISTS public.idx_user_flashcards_sense_id;
DROP INDEX IF EXISTS public.idx_word_quiz_results_sense_id;
DROP INDEX IF EXISTS public.idx_classifier_noun_pairs_noun_sense;
DROP INDEX IF EXISTS public.idx_user_classifier_mastery_classifier;
DROP INDEX IF EXISTS public.idx_prestudy_followups_session_id;
DROP INDEX IF EXISTS public.idx_prestudy_sessions_test_id;
DROP INDEX IF EXISTS public.idx_token_transactions_attempt_id;
DROP INDEX IF EXISTS public.idx_token_transactions_test_id;
DROP INDEX IF EXISTS public.idx_tests_gen_user;
DROP INDEX IF EXISTS public.idx_user_skill_ratings_user_id;
DROP INDEX IF EXISTS public.idx_app_error_logs_user_id;
DROP INDEX IF EXISTS public.idx_topic_generation_runs_category_id;
DROP INDEX IF EXISTS public.idx_corpus_style_profiles_ref_source;

-- 4. Unwrap ( SELECT auth.uid() AS uid ) / ( SELECT auth.role() AS role ) in RLS policies.
DO $$
DECLARE
    p   record;
    pat constant text := '\(\s*SELECT auth\.(uid|role)\(\) AS (uid|role)\s*\)';
    q   text;
    wc  text;
    stmt text;
BEGIN
    FOR p IN
        SELECT policyname, tablename, qual, with_check
          FROM pg_policies
         WHERE schemaname = 'public'
           AND (COALESCE(qual, '') ~* pat OR COALESCE(with_check, '') ~* pat)
    LOOP
        q  := regexp_replace(p.qual,       pat, 'auth.\1()', 'gi');
        wc := regexp_replace(p.with_check, pat, 'auth.\1()', 'gi');
        stmt := format('ALTER POLICY %I ON public.%I', p.policyname, p.tablename);
        IF q  IS NOT NULL THEN stmt := stmt || format(' USING (%s)', q);       END IF;
        IF wc IS NOT NULL THEN stmt := stmt || format(' WITH CHECK (%s)', wc); END IF;
        EXECUTE stmt;
    END LOOP;
END $$;
