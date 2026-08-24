-- ============================================================================
-- TASK-530 — counter drill sentinel test row.
--
-- migrations/task530_counter_drill_test_type.sql's header claimed the sentinel
-- `tests` row ('__counter_drill_ja') was applied live on 2026-08-08 alongside
-- the drill's tables and RPC. It was not: the row did not exist, so every
-- completed counter drill round 500'd on submit ("Failed to record counter
-- session") because counter_drill_service._fetch_sentinel_test_id() had
-- nothing to find. Discovered and applied live 2026-08-25 while fixing the
-- drill's separate load bug (templates/counter_drill.html called a
-- nonexistent window.authedFetch instead of window.authFetch).
--
-- Mirrors migrations/add_classifier_drill_mode.sql section 4 exactly: the
-- trainer is session-based, not test-bound, but test_attempts /
-- test_skill_ratings expect a real tests.id, so a single is_active=false
-- sentinel row anchors the ELO series without ever surfacing as a
-- recommendable test.
-- ============================================================================

DO $$
DECLARE
    v_sentinel_id    uuid;
    v_counter_tt     smallint;
    v_system_user    uuid;
BEGIN
    SELECT id INTO v_counter_tt
    FROM dim_test_types WHERE type_code = 'counter_drill';

    IF v_counter_tt IS NULL THEN
        RAISE EXCEPTION 'counter_drill test type not found in dim_test_types';
    END IF;

    -- Use the oldest existing user.id as gen_user (NOT NULL FK satisfier).
    SELECT id INTO v_system_user FROM users ORDER BY created_at LIMIT 1;
    IF v_system_user IS NULL THEN
        RAISE EXCEPTION 'No users present; cannot create sentinel test';
    END IF;

    -- Insert sentinel or fetch existing
    INSERT INTO tests (
        gen_user, slug, difficulty, tier, title, transcript,
        language_id, is_active, is_featured, is_custom
    ) VALUES (
        v_system_user, '__counter_drill_ja', 1, 'free-tier',
        'Counter Drill (Japanese)', NULL, 3, false, false, false
    )
    ON CONFLICT (slug) DO UPDATE SET updated_at = now()
    RETURNING id INTO v_sentinel_id;

    -- Seed the test-side ELO anchor at 1400 if not present
    IF NOT EXISTS (
        SELECT 1 FROM test_skill_ratings
        WHERE test_id = v_sentinel_id AND test_type_id = v_counter_tt
    ) THEN
        INSERT INTO test_skill_ratings (test_id, test_type_id, elo_rating, total_attempts)
        VALUES (v_sentinel_id, v_counter_tt, 1400, 0);
    END IF;
END $$;


-- ============================================================================
-- Verification
-- ============================================================================
--   SELECT id, slug, is_active, language_id FROM tests
--   WHERE slug = '__counter_drill_ja';
--   -- expect one row, is_active = false, language_id = 3.
-- ============================================================================
