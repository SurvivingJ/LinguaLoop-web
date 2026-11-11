-- Latency fixes, 2026-11-11 ([[evaluations/latency-2026-11-11]], ADR-042).
-- Idempotent: safe to re-run. Rollback: migrations/latency_2026_11_db_rollback.sql
--
-- 1. resolve_plan_timezone stops scanning pg_timezone_names.
--    pg_timezone_names reads the whole tz database from disk on every call:
--    ~55 ms warm, ~300-500 ms on a fresh connection. It ran inside
--    plan_local_date / plan_local_day_start, so every test submit
--    (apply_attempt_timing_and_progress -> record_session_progress),
--    credit_study_time, review_governor_state and build_daily_session paid it.
--    The names now live in a keyed table. A name missing from the table (a
--    zone added by a later tzdata release) still falls back to the old scan,
--    so the result is identical for every input: the same set of accepted
--    names, 'UTC' for everything else.

CREATE TABLE IF NOT EXISTS public.tz_names (
    name text PRIMARY KEY
);
COMMENT ON TABLE public.tz_names IS
    'Snapshot of pg_timezone_names.name for resolve_plan_timezone (latency 2026-11). '
    'Refresh after a Postgres/tzdata upgrade: INSERT INTO tz_names SELECT name FROM pg_timezone_names ON CONFLICT DO NOTHING.';

INSERT INTO public.tz_names (name)
SELECT DISTINCT name FROM pg_timezone_names
ON CONFLICT (name) DO NOTHING;

-- Read only by resolve_plan_timezone, whose callers (plan_local_date,
-- plan_local_day_start, build_daily_session, review_governor_state, ...) are
-- SECURITY DEFINER functions owned by postgres and executable by service_role
-- only. No client role needs it, so no policy and no client grant.
ALTER TABLE public.tz_names ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.tz_names FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.tz_names TO service_role;

CREATE OR REPLACE FUNCTION public.resolve_plan_timezone(p_tz text)
 RETURNS text
 LANGUAGE sql
 STABLE
AS $function$
    SELECT CASE
        WHEN btrim(COALESCE(p_tz, '')) = '' THEN 'UTC'
        ELSE COALESCE(
            -- fast path: primary-key lookup
            (SELECT n.name FROM public.tz_names n
              WHERE n.name = btrim(p_tz) LIMIT 1),
            -- slow path, only for names not in the snapshot (COALESCE is lazy)
            (SELECT n.name FROM pg_timezone_names n
              WHERE n.name = btrim(p_tz) LIMIT 1),
            'UTC')
    END
$function$;

REVOKE ALL ON FUNCTION public.resolve_plan_timezone(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.resolve_plan_timezone(text) TO service_role;

-- 2. Duplicate indexes (Supabase advisor 0009). Each dropped index is an exact
--    copy of one that stays; the kept one is the constraint-backed or the
--    more-used copy.
DROP INDEX IF EXISTS public.idx_cc_validated_lmi;                -- = idx_corpus_collocations_validated_lmi
DROP INDEX IF EXISTS public.idx_counter_pairs_counter;           -- = idx_counter_noun_pairs_counter
DROP INDEX IF EXISTS public.idx_counter_pairs_lemma;             -- = idx_counter_noun_pairs_lang_lemma
DROP INDEX IF EXISTS public.uq_counter_noun_pairs_lemma_counter; -- = the UNIQUE constraint's own index

-- 3. Foreign keys whose parent rows really are deleted (dim_word_senses 13k
--    deletes, exercises 8k, word_assets, tests, ...). Without an index each
--    parent delete scans the child table. FKs to never-deleted lookups
--    (dim_languages, dim_test_types, dim_question_types, ...) are left alone:
--    an index there costs writes and buys nothing.
CREATE INDEX IF NOT EXISTS idx_exercises_word_asset_id            ON public.exercises (word_asset_id);
CREATE INDEX IF NOT EXISTS idx_user_exercise_history_exercise_id  ON public.user_exercise_history (exercise_id);
CREATE INDEX IF NOT EXISTS idx_user_exercise_history_sense_id     ON public.user_exercise_history (sense_id);
CREATE INDEX IF NOT EXISTS idx_user_vocabulary_knowledge_sense_id ON public.user_vocabulary_knowledge (sense_id);
CREATE INDEX IF NOT EXISTS idx_user_word_ladder_sense_id          ON public.user_word_ladder (sense_id);
CREATE INDEX IF NOT EXISTS idx_user_flashcards_sense_id           ON public.user_flashcards (sense_id);
CREATE INDEX IF NOT EXISTS idx_word_quiz_results_sense_id         ON public.word_quiz_results (sense_id);
CREATE INDEX IF NOT EXISTS idx_classifier_noun_pairs_noun_sense   ON public.dim_classifier_noun_pairs (noun_sense_id);
CREATE INDEX IF NOT EXISTS idx_user_classifier_mastery_classifier ON public.user_classifier_mastery (classifier_id);
CREATE INDEX IF NOT EXISTS idx_prestudy_followups_session_id      ON public.prestudy_followups (session_id);
CREATE INDEX IF NOT EXISTS idx_prestudy_sessions_test_id          ON public.prestudy_sessions (test_id);
CREATE INDEX IF NOT EXISTS idx_token_transactions_attempt_id      ON public.token_transactions (attempt_id);
CREATE INDEX IF NOT EXISTS idx_token_transactions_test_id         ON public.token_transactions (test_id);
CREATE INDEX IF NOT EXISTS idx_tests_gen_user                     ON public.tests (gen_user);
CREATE INDEX IF NOT EXISTS idx_user_skill_ratings_user_id         ON public.user_skill_ratings (user_id);
CREATE INDEX IF NOT EXISTS idx_app_error_logs_user_id             ON public.app_error_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_topic_generation_runs_category_id  ON public.topic_generation_runs (category_id);
CREATE INDEX IF NOT EXISTS idx_corpus_style_profiles_ref_source   ON public.corpus_style_profiles (reference_source_id);

-- 4. RLS policies evaluate auth.uid() / auth.role() once per statement instead
--    of once per row (Supabase advisor 0003, auth_rls_initplan). Wrapping the
--    call in a scalar sub-select is the documented, semantics-preserving fix.
--    The negative lookbehind skips calls that are already wrapped, so a re-run
--    changes nothing.
DO $$
DECLARE
    p   record;
    pat constant text := '(?<!SELECT )auth\.(uid|role)\(\)';
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
        q  := regexp_replace(p.qual,       pat, '(select auth.\1())', 'gi');
        wc := regexp_replace(p.with_check, pat, '(select auth.\1())', 'gi');
        stmt := format('ALTER POLICY %I ON public.%I', p.policyname, p.tablename);
        IF q  IS NOT NULL THEN stmt := stmt || format(' USING (%s)', q);       END IF;
        IF wc IS NOT NULL THEN stmt := stmt || format(' WITH CHECK (%s)', wc); END IF;
        EXECUTE stmt;
    END LOOP;
END $$;
