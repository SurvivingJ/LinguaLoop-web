-- TASK-819 / TASK-820 (ADR-029): jev tier assignment — schema + reversal backup.
--
-- 1. tests.age_tier_* — jev's answer behind tests.target_age_tier. (tests.tier is
--    the *access* tier, 'free-tier'; hence the age_tier_ prefix.)
-- 2. tests_tier_backup_20260926 — every tests row's pre-change tier, difficulty
--    and seeded_elo, so the re-tier can be reversed:
--
--      UPDATE tests t
--         SET target_age_tier = b.target_age_tier,
--             difficulty      = b.difficulty,
--             seeded_elo      = b.seeded_elo,
--             age_tier_score = NULL, age_tier_confidence = NULL,
--             age_tier_probabilities = NULL, age_tier_model = NULL,
--             age_tier_assessed_at = NULL
--        FROM tests_tier_backup_20260926 b
--       WHERE b.test_id = t.id;
--
-- Idempotent: the backup is only filled when empty, so a re-run can never
-- overwrite the original values with already-re-tiered ones.

ALTER TABLE tests
    ADD COLUMN IF NOT EXISTS age_tier_score        real,
    ADD COLUMN IF NOT EXISTS age_tier_confidence   real,
    ADD COLUMN IF NOT EXISTS age_tier_probabilities jsonb,
    ADD COLUMN IF NOT EXISTS age_tier_model        text,
    ADD COLUMN IF NOT EXISTS age_tier_assessed_at  timestamptz;

COMMENT ON COLUMN tests.age_tier_score IS
    'jev raw score, 0 (T1) .. 5 (T6), probability-weighted; target_age_tier = round-half-up(score)+1';
COMMENT ON COLUMN tests.age_tier_probabilities IS
    'jev probability mass per tier, {"T1": p, ... "T6": p}';

CREATE TABLE IF NOT EXISTS tests_tier_backup_20260926 (
    test_id         uuid PRIMARY KEY,
    target_age_tier smallint,
    difficulty      integer,
    seeded_elo      integer,
    is_active       boolean,
    backed_up_at    timestamptz NOT NULL DEFAULT now()
);

-- Service-role only: no policies, RLS on.
ALTER TABLE tests_tier_backup_20260926 ENABLE ROW LEVEL SECURITY;

INSERT INTO tests_tier_backup_20260926
    (test_id, target_age_tier, difficulty, seeded_elo, is_active)
SELECT t.id, t.target_age_tier, t.difficulty, t.seeded_elo, t.is_active
  FROM tests t
 WHERE NOT EXISTS (SELECT 1 FROM tests_tier_backup_20260926);
