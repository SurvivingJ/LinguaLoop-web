-- Phase 2: age-tier leveling + stored lexical field on topics.
--
-- ADR-003 age tiers (T1-T6) live in dim_complexity_tiers (id 1-6). A topic now
-- carries the tier it was ideated for, so test generation can constrain the
-- difficulty range to that tier's difficulty_min..difficulty_max instead of
-- always spanning the full 1-9 schedule.
--
-- target_age_tier is NULLABLE: legacy rows (and any topic created before this
-- column) stay NULL and fall back to the full difficulty schedule -> no
-- regression for existing data.
--
-- distinctive_vocabulary stores the Explorer's declared lexical field (8-15
-- English headwords, multi-word phrases allowed). Stored now as the yield
-- signal substrate; whether it is also fed into prose generation is a later
-- decision.

ALTER TABLE topics
  ADD COLUMN IF NOT EXISTS target_age_tier smallint REFERENCES dim_complexity_tiers(id),
  ADD COLUMN IF NOT EXISTS distinctive_vocabulary jsonb NOT NULL DEFAULT '[]'::jsonb;

COMMENT ON COLUMN topics.target_age_tier IS
  'ADR-003 age tier 1-6 (FK dim_complexity_tiers.id). NULL = legacy / untiered -> full difficulty schedule.';
COMMENT ON COLUMN topics.distinctive_vocabulary IS
  'Explorer-declared lexical field: 8-15 English headwords (multi-word phrases allowed). Yield signal substrate.';
