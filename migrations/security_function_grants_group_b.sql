-- ============================================================================
-- SECURITY (TASK-877, Group B of 2) - every remaining privileged function
-- Date: 2026-10-14
-- REQUIRES USER APPROVAL TO APPLY LIVE.  Apply AFTER
-- security_function_grants_group_a.sql (which must be applied alone first) and
-- BEFORE security_function_auth_checks.sql.
--
-- THE HOLE (plan findings S5, S6, S7, S8, S13, S17)
--   Almost every function in public is executable by PUBLIC / anon /
--   authenticated (live proacl {=X, anon=X, authenticated=X, service_role=X}).
--   Many are SECURITY DEFINER and take a caller-supplied user id
--   (record_session_progress, compute_weekly_plan_persist, build_daily_session,
--   calibration_*, update_classifier_mastery, get_token_balance,
--   anonymize_user_data, ...), so an anon-key caller can read or write any
--   user's data.  The ACL cannot be fixed with `REVOKE ... FROM anon` alone:
--   anon inherits EXECUTE through the PUBLIC grant (`=X`).
--
-- THE FIX
--   Loop over pg_proc (NOT hand-typed signatures) so every overload is covered,
--   including the live 8-arg record_session_progress and, once applied, the
--   pending 10-arg overload, plan_local_date / plan_local_day_start, etc.:
--       REVOKE ALL ON FUNCTION <oid::regprocedure> FROM PUBLIC, anon, authenticated;
--       GRANT EXECUTE ON FUNCTION <oid::regprocedure> TO service_role;
--   `postgres` (owner) keeps its implicit EXECUTE.  Where a SECURITY DEFINER
--   function has no pinned search_path, ALTER FUNCTION ... SET search_path =
--   public, pg_temp (functions already pinned - e.g. the irt_* family with
--   search_path=public - are left alone).
--
-- WHAT IS DELIBERATELY *NOT* REVOKED  (the allowlist - "must stay callable")
--   is_admin(uuid), is_moderator(uuid).  ~20 RLS policies (TO public) call
--   is_admin(auth.uid()) / is_moderator(auth.uid()); policy expressions are
--   evaluated as the invoking role, so anon/authenticated need EXECUTE.
--   Their in-function guard is added by security_function_auth_checks.sql.
--   Allowlist derivation (all verified 2026-10-14, see the report):
--     * static/js, templates: ZERO supabase.rpc / .rpc( calls.  The browser
--       never calls an RPC; supabase/ holds no edge functions.
--     * Python: every .rpc( caller resolves to get_supabase_admin() (service
--       role) - routes/*, services/*; no client is ever given a user JWT
--       (no postgrest.auth / set_session anywhere).  The only anon-client
--       fallbacks are `get_supabase_admin() or get_supabase()` (model_health,
--       judges/base, timing) and `supabase_service or supabase`
--       (routes/users.py, routes/tests.py:1173); they are dead if the service
--       key is configured, and an anon RPC could not work under RLS anyway.
--     * Live pg_depend: the ONLY functions referenced by policies are
--       is_admin/is_moderator; no view, column default or CHECK constraint in
--       public references a public function (guarded again below).
--     * Triggers: trigger functions are not EXECUTE-checked when a trigger
--       fires (only at CREATE TRIGGER), so revoking them (handle_new_user,
--       set_sense_word_language, trg_*, update_*_count, ...) only removes their
--       useless RPC exposure.
--   Result: after this file the only anon/authenticated-executable functions in
--   public are is_admin and is_moderator.
--
-- SCOPE NOTE (SECURITY INVOKER functions)
--   SECURITY INVOKER functions (bkt_*, ladder_*, get_practice_session,
--   update_vocabulary_from_*, tests_containing_sense, ...) are included: the
--   mutating ones take a user id and rely only on table grants/RLS (TASK-880),
--   and every caller is service_role.  Pure immutable helpers are revoked too:
--   the invoker functions that call them run as service_role (granted below).
--
-- DEFAULT PRIVILEGES (TASK-877 owns FUNCTION defaults; TASK-880 owns TABLE
--   defaults).  Supabase installs default ACLs so that every NEW function
--   created by postgres/supabase_admin in public is granted to anon,
--   authenticated and service_role, and PostgreSQL grants EXECUTE to PUBLIC by
--   default.  Section 4 removes both so a forgotten REVOKE in a future
--   migration is no longer an exposure.  Consequence: a future function that a
--   client role legitimately needs must be granted EXPLICITLY.  The PUBLIC
--   revoke is necessarily database-wide for objects created by `postgres`
--   (there is no schema-scoped form for PUBLIC).
--
-- Idempotent and re-runnable (REVOKE/GRANT/ALTER FUNCTION/ALTER DEFAULT
--   PRIVILEGES are no-ops in the target state).  Re-run it after applying any
--   pending migration that creates functions (e.g. grant_daily_free_tokens,
--   review_governor_state, the 10-arg record_session_progress) to sweep them.
--   Fails (rolls back) if a required function name has zero matches, if any
--   policy / default / CHECK / view / index depends on a function being
--   revoked, or if the post-condition does not hold.
--
-- ROLLBACK for one function if a legitimate caller is found:
--   GRANT EXECUTE ON FUNCTION public.<name>(<args>) TO authenticated;
--   (never restore PUBLIC/anon).  Default-privilege rollback:
--   ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
--       GRANT EXECUTE ON FUNCTIONS TO anon, authenticated;
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Pre-flight guards
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    -- Names that exist live (2026-10-14) and MUST match: a rename or drop
    -- would otherwise silently leave a function out of the hardening.
    v_required constant text[] := ARRAY[
        'record_session_progress', 'apply_attempt_timing_and_progress',
        'compute_weekly_plan_persist', 'apply_study_plan_template',
        'build_daily_session', 'compute_weekly_plan_load_signals',
        'plan_local_date', 'update_classifier_mastery', 'irt_apply_calibration',
        'irt_try_lock', 'irt_release_lock',
        'calibration_ability', 'calibration_build_items',
        'calibration_discard_unanswered', 'calibration_record_answer',
        'calibration_refresh_anchor_pool', 'calibration_distractor_cache_coverage',
        'calibration_cache_distractors_chunk', 'apply_calibration_to_skill_ratings',
        'process_pinyin_submission', 'process_pitch_accent_submission',
        'process_classifier_drill_submission', 'process_test_submission',
        'process_dictation_submission',
        'anonymize_user_data', 'add_tokens_atomic', 'get_token_balance',
        'get_classifier_drill_session', 'get_counter_drill_session',
        'max_unlocked_tier', 'batch_lookup_lemmas', 'handle_new_user',
        'get_distractors', 'get_next_category', 'get_active_languages',
        'match_topics', 'match_topics_global',
        'refresh_practice_time_estimates',
        'pg_try_advisory_lock_for_study_plan', 'pg_advisory_unlock_for_study_plan',
        'pg_try_advisory_lock_for_dt_synthesis', 'pg_advisory_unlock_for_dt_synthesis',
        'pg_try_advisory_lock_for_model_health', 'pg_advisory_unlock_for_model_health',
        'pg_try_advisory_lock_for_queue_drain', 'pg_advisory_unlock_for_queue_drain',
        'get_recommended_test', 'get_recommended_tests', 'get_replay_tests',
        'get_vocab_recommendations', 'get_word_quiz_candidates',
        'can_use_free_test', 'get_daily_free_test_limit', 'get_test_token_cost',
        'sense_similarity_to_lemmas', 'semantic_distractors',
        'pronunciation_distractors', 'match_test_passages_by_topic_tier',
        'recommended_tests_ranked', 'selection_vocab_ability',
        'get_practice_session', 'ladder_record_attempt', 'ladder_pass_gate',
        'ladder_graduate', 'irt_compute_user_theta', 'tests_containing_sense',
        'bkt_apply_lapse_penalty', 'bkt_contextual_inference',
        'bkt_infer_from_frequency', 'update_vocabulary_from_test',
        'update_vocabulary_from_word_test', 'update_vocabulary_from_word_tests_batch',
        'calibration_next_anchor', 'calibration_next_anchors',
        'calibration_fill_distractor_cache'
    ];
    -- Called by the repo but created by migrations not yet applied live
    -- (pending branch).  Absent is fine; present gets swept by the loop below.
    v_pending constant text[] := ARRAY[
        'plan_local_day_start', 'grant_daily_free_tokens', 'review_governor_state',
        'set_new_words_shortfall', 'refresh_new_word_minutes', 'get_verb_noun_pairs',
        'ladder_new_word_state', 'process_mystery_submission', 'nearest_senses',
        'review_item_seconds'
    ];
    v_name   text;
    v_n      int;
    v_bad    text;
BEGIN
    FOREACH v_name IN ARRAY v_required LOOP
        SELECT count(*) INTO v_n FROM pg_proc p
        WHERE p.pronamespace = 'public'::regnamespace AND p.proname = v_name;
        IF v_n = 0 THEN
            RAISE EXCEPTION 'TASK-877 group B: required function public.% matched zero functions', v_name;
        END IF;
    END LOOP;

    FOREACH v_name IN ARRAY v_pending LOOP
        SELECT count(*) INTO v_n FROM pg_proc p
        WHERE p.pronamespace = 'public'::regnamespace AND p.proname = v_name;
        IF v_n = 0 THEN
            RAISE NOTICE 'TASK-877 group B: pending function public.% not present yet - re-run this file after its migration', v_name;
        END IF;
    END LOOP;

    -- Nothing that policies, column defaults, CHECK constraints, views/rules or
    -- index expressions evaluate as a client role may be revoked.
    SELECT string_agg(DISTINCT p.oid::regprocedure::text || ' <- ' || d.classid::regclass::text, '; ')
      INTO v_bad
    FROM pg_depend d
    JOIN pg_proc p ON p.oid = d.refobjid AND d.refclassid = 'pg_proc'::regclass
    WHERE p.pronamespace = 'public'::regnamespace
      AND p.proname NOT IN ('is_admin', 'is_moderator')
      AND NOT EXISTS (SELECT 1 FROM pg_depend e WHERE e.classid = 'pg_proc'::regclass AND e.objid = p.oid AND e.deptype = 'e')
      AND (
            d.classid IN ('pg_policy'::regclass, 'pg_attrdef'::regclass,
                          'pg_constraint'::regclass, 'pg_rewrite'::regclass)
         OR (d.classid = 'pg_class'::regclass
             AND EXISTS (SELECT 1 FROM pg_class c WHERE c.oid = d.objid AND c.relkind IN ('i', 'I')))
          );
    IF v_bad IS NOT NULL THEN
        RAISE EXCEPTION 'TASK-877 group B: refusing to revoke functions used by policies/defaults/constraints/views/indexes: %', v_bad;
    END IF;
END
$$;

-- ---------------------------------------------------------------------------
-- 2. Revoke from client roles / grant to service_role / pin search_path
--    Covers EVERY function in public (all overloads) except the allowlist and
--    extension-owned objects (pgvector's operators/casts live in public).
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    r record;
    v_revoked int := 0;
    v_pinned  int := 0;
BEGIN
    FOR r IN
        SELECT p.oid::regprocedure AS sig, p.proname, p.prosecdef,
               EXISTS (SELECT 1 FROM unnest(coalesce(p.proconfig, '{}'::text[])) c
                       WHERE c LIKE 'search_path=%') AS has_sp
        FROM pg_proc p
        WHERE p.pronamespace = 'public'::regnamespace
          AND p.prokind IN ('f', 'p')
          AND p.proname NOT IN ('is_admin', 'is_moderator')       -- allowlist
          AND NOT EXISTS (SELECT 1 FROM pg_depend d
                          WHERE d.classid = 'pg_proc'::regclass AND d.objid = p.oid AND d.deptype = 'e') -- not extension members
        ORDER BY p.proname, p.oid
    LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC, anon, authenticated', r.sig);
        EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO service_role', r.sig);
        v_revoked := v_revoked + 1;
        IF r.prosecdef AND NOT r.has_sp THEN
            EXECUTE format('ALTER FUNCTION %s SET search_path = public, pg_temp', r.sig);
            v_pinned := v_pinned + 1;
            RAISE NOTICE 'TASK-877 group B: pinned search_path on %', r.sig;
        END IF;
    END LOOP;
    RAISE NOTICE 'TASK-877 group B: hardened % functions, pinned search_path on %', v_revoked, v_pinned;
END
$$;

-- ---------------------------------------------------------------------------
-- 3. Allowlist: policies evaluate these as the calling role.  Make the intended
--    grants explicit (no-op if already granted).  PUBLIC is left as it is.
-- ---------------------------------------------------------------------------
GRANT EXECUTE ON FUNCTION public.is_admin(uuid)     TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.is_moderator(uuid) TO anon, authenticated, service_role;

-- ---------------------------------------------------------------------------
-- 4. Default privileges for FUNCTIONS created from now on.
--    (TABLE/SEQUENCE defaults belong to TASK-880.)
-- ---------------------------------------------------------------------------
-- Objects created by postgres (migrations / SQL editor): no implicit PUBLIC
-- EXECUTE (database-wide for postgres-owned functions), and no automatic
-- grant to the client roles in public.  service_role keeps its default grant.
-- WARNING: the PUBLIC revoke below has no IN SCHEMA clause, so it is database-wide
-- for postgres-owned objects.  Functions created later by postgres in ANY schema
-- (e.g. CREATE EXTENSION functions in the extensions schema) get no PUBLIC EXECUTE;
-- grant explicitly to the roles that need them (anon/authenticated) after installs.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE EXECUTE ON FUNCTIONS FROM anon, authenticated;

-- Objects created by supabase_admin (dashboard-managed): same, if the applying
-- role is allowed to alter that role's defaults; otherwise report and continue.
DO $$
BEGIN
    BEGIN
        ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public
            REVOKE EXECUTE ON FUNCTIONS FROM anon, authenticated;
    EXCEPTION WHEN insufficient_privilege OR undefined_object THEN
        RAISE NOTICE 'TASK-877 group B: could not alter supabase_admin default privileges (%); run as supabase_admin if wanted', SQLERRM;
    END;
END
$$;

-- ---------------------------------------------------------------------------
-- 5. Post-condition (aborts and rolls back the whole file if violated)
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    r record;
    v_bad text;
BEGIN
    FOR r IN
        SELECT p.oid::regprocedure AS sig, p.prosecdef, p.proconfig
        FROM pg_proc p
        WHERE p.pronamespace = 'public'::regnamespace
          AND p.prokind IN ('f', 'p')
          AND p.proname NOT IN ('is_admin', 'is_moderator')
          AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_proc'::regclass AND d.objid = p.oid AND d.deptype = 'e')
    LOOP
        IF has_function_privilege('anon', r.sig, 'EXECUTE')
           OR has_function_privilege('authenticated', r.sig, 'EXECUTE') THEN
            RAISE EXCEPTION 'TASK-877 group B: % is still executable by anon/authenticated', r.sig;
        END IF;
        IF NOT has_function_privilege('service_role', r.sig, 'EXECUTE') THEN
            RAISE EXCEPTION 'TASK-877 group B: % is not executable by service_role', r.sig;
        END IF;
        IF r.prosecdef AND NOT EXISTS (SELECT 1 FROM unnest(coalesce(r.proconfig, '{}'::text[])) c
                                       WHERE c LIKE 'search_path=%') THEN
            RAISE EXCEPTION 'TASK-877 group B: SECURITY DEFINER % has no pinned search_path', r.sig;
        END IF;
    END LOOP;
    -- The allowlist must still work for policy evaluation.
    IF NOT (has_function_privilege('authenticated', 'public.is_admin(uuid)'::regprocedure, 'EXECUTE')
        AND has_function_privilege('authenticated', 'public.is_moderator(uuid)'::regprocedure, 'EXECUTE')) THEN
        RAISE EXCEPTION 'TASK-877 group B: is_admin/is_moderator lost authenticated EXECUTE';
    END IF;
END
$$;

COMMIT;

-- Read-only verification after applying (expect exactly is_admin, is_moderator):
--   SELECT p.oid::regprocedure, p.proacl FROM pg_proc p
--   WHERE p.pronamespace='public'::regnamespace AND p.prokind IN ('f','p')
--     AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid=p.oid AND d.deptype='e')
--     AND (has_function_privilege('anon',p.oid,'EXECUTE')
--          OR has_function_privilege('authenticated',p.oid,'EXECUTE'));
--   SELECT defaclrole::regrole, defaclnamespace::regnamespace, defaclacl
--   FROM pg_default_acl WHERE defaclobjtype = 'f';
-- Then: POST /rest/v1/rpc/process_stripe_payment with the anon key -> 401/403,
-- and run a full session-end flow through Flask (study plan, practice session,
-- calibration, classifier drill, IRT calibrator, token flow).
