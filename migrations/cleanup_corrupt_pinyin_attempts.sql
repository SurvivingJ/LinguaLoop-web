-- ============================================================================
-- One-off cleanup: remove corrupted pinyin attempts produced by the broken
-- synthetic-response path. Resets user/test ELO ratings for pinyin back to
-- defaults so the next attempt starts from a clean slate.
-- ============================================================================
-- Background: prior to process_pinyin_submission, pinyin submissions went
-- through process_test_submission which validated the synthetic answer string
-- against real MC questions. Every pinyin attempt was scored 0/N (N = # of MC
-- questions on the test), percentage = 0, and ELO dropped accordingly. None
-- of these rows reflect actual user performance.
--
-- Pre-checks confirmed:
--   - token_transactions and word_quiz_results have 0 rows referencing pinyin
--     attempts, so DELETE will not violate any FK.
--   - pinyin test_type_id = 11.
-- ============================================================================

DO $$
DECLARE
  v_pinyin_type_id smallint;
  v_attempts_deleted integer;
  v_test_ids_to_recount uuid[];
BEGIN
  SELECT id INTO v_pinyin_type_id FROM dim_test_types WHERE type_code = 'pinyin';
  IF v_pinyin_type_id IS NULL THEN
    RAISE EXCEPTION 'pinyin test type not found in dim_test_types';
  END IF;

  -- Capture affected test_ids before delete so we can recompute tests.total_attempts.
  -- The AFTER INSERT trigger update_test_attempts_count bumped tests.total_attempts
  -- on each corrupt insert, but there's no AFTER DELETE trigger to reverse it.
  SELECT ARRAY_AGG(DISTINCT test_id)
  INTO v_test_ids_to_recount
  FROM test_attempts
  WHERE test_type_id = v_pinyin_type_id;

  DELETE FROM test_attempts WHERE test_type_id = v_pinyin_type_id;
  GET DIAGNOSTICS v_attempts_deleted = ROW_COUNT;
  RAISE NOTICE 'Deleted % corrupt pinyin attempts', v_attempts_deleted;

  -- Recompute tests.total_attempts for any test that had a pinyin attempt,
  -- so the count reflects only real (non-pinyin) attempts that remain.
  IF v_test_ids_to_recount IS NOT NULL THEN
    UPDATE tests t
    SET total_attempts = (
      SELECT COUNT(*) FROM test_attempts ta WHERE ta.test_id = t.id
    )
    WHERE t.id = ANY(v_test_ids_to_recount);
  END IF;

  -- Reset pinyin user_skill_ratings to defaults (matches RPC's get-or-create path).
  UPDATE user_skill_ratings
  SET
    elo_rating = 1200,
    tests_taken = 0,
    last_test_date = NULL,
    updated_at = NOW()
  WHERE test_type_id = v_pinyin_type_id;

  -- Reset pinyin test_skill_ratings to the original defaults set by add_pinyin_mode.sql.
  UPDATE test_skill_ratings
  SET
    elo_rating = 1400,
    total_attempts = 0,
    updated_at = NOW()
  WHERE test_type_id = v_pinyin_type_id;
END $$;
