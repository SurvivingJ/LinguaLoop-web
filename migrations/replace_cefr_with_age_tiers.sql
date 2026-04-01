-- ============================================================
-- Replace CEFR levels with Age-Equivalent Complexity Tiers
--
-- Migrates the entire system from CEFR codes (A1-C2) to
-- age tiers (T1-T6). 1:1 mapping:
--   A1→T1 (Toddler), A2→T2 (Primary), B1→T3 (Young Teen),
--   B2→T4 (High Schooler), C1→T5 (Uni Student), C2→T6 (Professional)
--
-- Affects: dim_cefr_levels, scenarios, exercises, dim_grammar_patterns
-- ============================================================

-- ──────────────────────────────────────────────────────────────
-- 1. dim_cefr_levels → dim_complexity_tiers
-- ──────────────────────────────────────────────────────────────

-- Rename table and column
ALTER TABLE public.dim_cefr_levels RENAME TO dim_complexity_tiers;
ALTER TABLE public.dim_complexity_tiers RENAME COLUMN cefr_code TO tier_code;

-- Drop the unique constraint (not just the index — it's enforced as a constraint)
ALTER TABLE public.dim_complexity_tiers DROP CONSTRAINT IF EXISTS dim_cefr_levels_cefr_code_key;

-- Migrate codes: A1→T1, A2→T2, ... C2→T6
UPDATE public.dim_complexity_tiers SET tier_code = CASE tier_code
  WHEN 'A1' THEN 'T1'
  WHEN 'A2' THEN 'T2'
  WHEN 'B1' THEN 'T3'
  WHEN 'B2' THEN 'T4'
  WHEN 'C1' THEN 'T5'
  WHEN 'C2' THEN 'T6'
END;

-- Update word counts, descriptions, and ELO to match tier definitions
UPDATE public.dim_complexity_tiers SET
  word_count_min = 0, word_count_max = 500,
  description = 'The Toddler (Age 4-5): 500 words, basic verbs/nouns, one idea per sentence',
  initial_elo = 875
WHERE tier_code = 'T1';

UPDATE public.dim_complexity_tiers SET
  word_count_min = 120, word_count_max = 2000,
  description = 'The Primary Schooler (Age 8-9): 2000 words, compound sentences, literal/concrete',
  initial_elo = 1175
WHERE tier_code = 'T2';

UPDATE public.dim_complexity_tiers SET
  word_count_min = 200, word_count_max = 5000,
  description = 'The Young Teen (Age 13-14): 5000 words, colloquialisms, mild idioms, conditionals',
  initial_elo = 1400
WHERE tier_code = 'T3';

UPDATE public.dim_complexity_tiers SET
  word_count_min = 300, word_count_max = 10000,
  description = 'The High Schooler (Age 16-17): 10000 words, standard adult grammar, moderate jargon',
  initial_elo = 1550
WHERE tier_code = 'T4';

UPDATE public.dim_complexity_tiers SET
  word_count_min = 400, word_count_max = 15000,
  description = 'The Uni Student (Age 19-21): 15000+ words, full language breadth, complex clauses',
  initial_elo = 1700
WHERE tier_code = 'T5';

UPDATE public.dim_complexity_tiers SET
  word_count_min = 600, word_count_max = 25000,
  description = 'The Educated Professional (Age 30+): 25000+ words, high-register, domain jargon, rhetoric',
  initial_elo = 1925
WHERE tier_code = 'T6';

-- Recreate unique index with new name
ALTER TABLE public.dim_complexity_tiers ADD CONSTRAINT dim_complexity_tiers_tier_code_key UNIQUE (tier_code);

-- ──────────────────────────────────────────────────────────────
-- 2. scenarios table
-- ──────────────────────────────────────────────────────────────

-- Drop old CHECK constraint and index
ALTER TABLE public.scenarios DROP CONSTRAINT IF EXISTS scenarios_cefr_level_check;
DROP INDEX IF EXISTS public.idx_scenarios_cefr;

-- Rename column
ALTER TABLE public.scenarios RENAME COLUMN cefr_level TO complexity_tier;

-- Migrate data
UPDATE public.scenarios SET complexity_tier = CASE complexity_tier
  WHEN 'A1' THEN 'T1'
  WHEN 'A2' THEN 'T2'
  WHEN 'B1' THEN 'T3'
  WHEN 'B2' THEN 'T4'
  WHEN 'C1' THEN 'T5'
  WHEN 'C2' THEN 'T6'
END WHERE complexity_tier IS NOT NULL;

-- Add new CHECK constraint and index
ALTER TABLE public.scenarios ADD CONSTRAINT scenarios_complexity_tier_check
  CHECK (complexity_tier IN ('T1','T2','T3','T4','T5','T6'));
CREATE INDEX idx_scenarios_tier ON public.scenarios(complexity_tier);

-- ──────────────────────────────────────────────────────────────
-- 3. exercises table
-- ──────────────────────────────────────────────────────────────

ALTER TABLE public.exercises DROP CONSTRAINT IF EXISTS exercises_cefr_level_check;
DROP INDEX IF EXISTS public.idx_exercises_cefr;

ALTER TABLE public.exercises RENAME COLUMN cefr_level TO complexity_tier;

UPDATE public.exercises SET complexity_tier = CASE complexity_tier
  WHEN 'A1' THEN 'T1'
  WHEN 'A2' THEN 'T2'
  WHEN 'B1' THEN 'T3'
  WHEN 'B2' THEN 'T4'
  WHEN 'C1' THEN 'T5'
  WHEN 'C2' THEN 'T6'
END WHERE complexity_tier IS NOT NULL;

ALTER TABLE public.exercises ADD CONSTRAINT exercises_complexity_tier_check
  CHECK (complexity_tier IN ('T1','T2','T3','T4','T5','T6'));
CREATE INDEX idx_exercises_tier ON public.exercises(complexity_tier);

-- ──────────────────────────────────────────────────────────────
-- 4. dim_grammar_patterns table
-- ──────────────────────────────────────────────────────────────

ALTER TABLE public.dim_grammar_patterns DROP CONSTRAINT IF EXISTS dim_grammar_patterns_cefr_level_check;
DROP INDEX IF EXISTS public.idx_grammar_patterns_cefr;

ALTER TABLE public.dim_grammar_patterns RENAME COLUMN cefr_level TO complexity_tier;

UPDATE public.dim_grammar_patterns SET complexity_tier = CASE complexity_tier
  WHEN 'A1' THEN 'T1'
  WHEN 'A2' THEN 'T2'
  WHEN 'B1' THEN 'T3'
  WHEN 'B2' THEN 'T4'
  WHEN 'C1' THEN 'T5'
  WHEN 'C2' THEN 'T6'
END WHERE complexity_tier IS NOT NULL;

ALTER TABLE public.dim_grammar_patterns ADD CONSTRAINT dim_grammar_patterns_complexity_tier_check
  CHECK (complexity_tier IN ('T1','T2','T3','T4','T5','T6'));
CREATE INDEX idx_grammar_patterns_tier ON public.dim_grammar_patterns(complexity_tier);

-- ──────────────────────────────────────────────────────────────
-- 5. Verification queries (run manually after migration)
-- ──────────────────────────────────────────────────────────────
-- SELECT tier_code, description, word_count_min, word_count_max FROM dim_complexity_tiers ORDER BY id;
-- SELECT complexity_tier, count(*) FROM scenarios GROUP BY complexity_tier;
-- SELECT complexity_tier, count(*) FROM exercises GROUP BY complexity_tier;
-- SELECT complexity_tier, count(*) FROM dim_grammar_patterns GROUP BY complexity_tier;
