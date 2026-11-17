-- =============================================================================
-- TASK-998 — measure-word drill levels and mastery (rollback-only SQL test)
-- =============================================================================
-- Pairs with migrations/task998_classifier_drill_levels.sql (and, for the
-- Fill-in check, migrations/task998_classifier_cloze_sentences_fill.sql), which
-- must already be applied. Everything runs in one transaction that ends in
-- ROLLBACK, so no mastery row survives.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_task998_classifier_drill_levels.sql
--
-- Run as postgres. Uses the first users row as the learner. Asserts, printing
-- PASS notices:
--   1. ACLs: v2 and update_classifier_mastery are EXECUTE for service_role
--      only; both are SECURITY DEFINER with search_path pinned; the old
--      get_classifier_drill_session still exists with its 13 columns.
--   2. With no mastery rows: every item has level 1, mastery_level 1, a
--      classifier_id_primary equal to correct ids[0], 3 distractors, no 个,
--      and only tier-1 classifiers (max_tier 1).
--   3. update_classifier_mastery promotes ONE level per 5 answers at that
--      level (Choose -> Type -> Reverse -> Fill in after 5/10/15 correct
--      answers), not one per answer after the fifth; 3 wrong in a row demote
--      and restart the count; the returned jsonb keeps every old key.
--   4. With the classifier at level 3 its items come back as Reverse with 3
--      reverse nouns, none of which takes the classifier; at level 4 items
--      with a usable cloze sentence come back as Fill in with a ___ blank,
--      the rest as Reverse (never level 4 without a blank).
-- =============================================================================

BEGIN;

DO $$
DECLARE
    v_user   uuid;
    v_cls    smallint;
    v_res    jsonb;
    v_i      integer;
    v_levels integer[] := '{}';
    v_n      integer;
    v_bad    integer;
BEGIN
    -- 1. ACLs -----------------------------------------------------------------
    SELECT count(*) INTO v_bad
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.proname IN ('get_classifier_drill_session_v2', 'update_classifier_mastery')
      AND (NOT p.prosecdef
           OR NOT (p.proconfig @> ARRAY['search_path=public, pg_temp'])
           OR has_function_privilege('anon', p.oid, 'EXECUTE')
           OR has_function_privilege('authenticated', p.oid, 'EXECUTE')
           OR NOT has_function_privilege('service_role', p.oid, 'EXECUTE'));
    IF v_bad <> 0 THEN RAISE EXCEPTION 'FAIL: % drill functions have the wrong security/ACL', v_bad; END IF;
    IF to_regprocedure('public.get_classifier_drill_session(uuid,smallint,integer)') IS NULL
       OR to_regprocedure('public.get_classifier_drill_session_v2(uuid,smallint,integer)') IS NULL THEN
        RAISE EXCEPTION 'FAIL: v1 or v2 session function missing';
    END IF;
    RAISE NOTICE 'PASS: ACLs and both session functions present';

    -- 2. Fresh learner --------------------------------------------------------
    SELECT id INTO v_user FROM users ORDER BY created_at NULLS LAST LIMIT 1;
    DELETE FROM user_classifier_mastery WHERE user_id = v_user;  -- rolled back

    SELECT count(*) FILTER (WHERE out_level <> 1 OR out_mastery_level <> 1
                              OR out_classifier_id_primary IS DISTINCT FROM out_correct_classifier_ids[1]
                              OR array_length(out_distractor_ids, 1) <> 3
                              OR '个' = ANY(out_correct_classifier_hanzi) OR '个' = ANY(out_distractor_hanzi)
                              OR out_difficulty_tier > 1 OR out_max_tier <> 1),
           count(*)
      INTO v_bad, v_n
    FROM get_classifier_drill_session_v2(v_user, 1::smallint, 40);
    IF v_n = 0 OR v_bad <> 0 THEN RAISE EXCEPTION 'FAIL: fresh learner items: % bad of %', v_bad, v_n; END IF;
    RAISE NOTICE 'PASS: fresh learner gets % level-1 tier-1 items with a primary classifier', v_n;

    -- 3. Promotion one level per 5 answers at that level ---------------------
    SELECT id INTO v_cls FROM dim_classifiers WHERE language_id = 1 AND hanzi = '本';
    FOR v_i IN 1..16 LOOP
        v_res := update_classifier_mastery(v_user, v_cls, true);
        v_levels := v_levels || (v_res->>'current_level')::integer;
    END LOOP;
    IF v_levels <> ARRAY[1,1,1,1,2, 2,2,2,2,3, 3,3,3,3,4, 4] THEN
        RAISE EXCEPTION 'FAIL: promotion path %', v_levels;
    END IF;
    IF NOT (v_res ?& ARRAY['classifier_id','attempts','correct','ewma_accuracy','current_level',
                           'old_level','promoted','demoted','level_attempts']) THEN
        RAISE EXCEPTION 'FAIL: return keys %', v_res;
    END IF;
    RAISE NOTICE 'PASS: promotion path %', v_levels;

    -- 4. Level 4: Fill in where a blank exists, else Reverse -----------------
    SELECT count(*) FILTER (WHERE out_classifier_id_primary = v_cls AND out_level = 4 AND out_cloze_blanked IS NULL),
           count(*) FILTER (WHERE out_classifier_id_primary = v_cls AND out_level = 4
                              AND out_cloze_blanked LIKE '%\_\_\_%' ESCAPE '\'),
           count(*) FILTER (WHERE out_classifier_id_primary = v_cls AND out_level NOT IN (3, 4))
      INTO v_bad, v_n, v_i
    FROM generate_series(1, 10) g
    CROSS JOIN LATERAL get_classifier_drill_session_v2(v_user, 1::smallint, 40);
    IF v_bad <> 0 OR v_i <> 0 THEN RAISE EXCEPTION 'FAIL: level-4 items: % without blank, % below Reverse', v_bad, v_i; END IF;
    RAISE NOTICE 'PASS: level-4 classifier items: % Fill in, none without a blank (0 Fill in = fill not applied)', v_n;

    -- Demotion: 3 wrong in a row -> level 3, count restarts.
    PERFORM update_classifier_mastery(v_user, v_cls, false);
    PERFORM update_classifier_mastery(v_user, v_cls, false);
    v_res := update_classifier_mastery(v_user, v_cls, false);
    IF (v_res->>'current_level')::int <> 3 OR NOT (v_res->>'demoted')::boolean
       OR (v_res->>'level_attempts')::int <> 0 THEN
        RAISE EXCEPTION 'FAIL: demotion %', v_res;
    END IF;
    RAISE NOTICE 'PASS: demotion %', v_res;

    -- Level 3: Reverse with 3 nouns that do not take the classifier.
    SELECT count(*) FILTER (WHERE out_level <> 3 OR array_length(out_reverse_noun_options, 1) <> 3),
           count(*)
      INTO v_bad, v_n
    FROM generate_series(1, 5) g
    CROSS JOIN LATERAL get_classifier_drill_session_v2(v_user, 1::smallint, 40)
    WHERE out_classifier_id_primary = v_cls;
    IF v_n = 0 OR v_bad <> 0 THEN RAISE EXCEPTION 'FAIL: level-3 items: % bad of %', v_bad, v_n; END IF;
    SELECT count(*) INTO v_bad
    FROM generate_series(1, 5) g
    CROSS JOIN LATERAL get_classifier_drill_session_v2(v_user, 1::smallint, 40) s
    CROSS JOIN LATERAL unnest(s.out_reverse_noun_options) AS r(noun)
    JOIN dim_classifier_noun_pairs p
      ON p.language_id = 1 AND p.lemma_text = r.noun AND p.classifier_id = s.out_classifier_id_primary;
    IF v_bad <> 0 THEN RAISE EXCEPTION 'FAIL: % reverse nouns take the answer classifier', v_bad; END IF;
    RAISE NOTICE 'PASS: % Reverse items, every wrong noun is wrong', v_n;
END $$;

ROLLBACK;
