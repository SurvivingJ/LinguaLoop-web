-- ============================================================================
-- TASK-522 — widen word_assets.asset_type to admit the typed-LLM asset family.
--
-- The defect this fixes
-- ---------------------
-- word_assets_asset_type_check enumerated the seven asset types that existed
-- before the TASK-520 prompt split. TASK-522 then added a type-registered LLM
-- generator layer (asset_generators/typed_llm.py) writing 'llm_types_A' /
-- 'llm_types_B', and nothing widened the constraint. Every one of those writes
-- failed with 23514.
--
-- It failed quietly in the way that matters: _store_asset catches the error and
-- logs it, so the pipeline reported success for the sense while
-- synonym_antonym_match, word_family and particle_selection produced nothing.
-- The first TASK-515 batch chunk hit it on sense 1 and would have hit it on all
-- 300, at full LLM cost, producing zero typed-LLM exercises — and the batch's
-- valid-rate report would still have read ~100%, because the P1/P2/P3 assets it
-- measures did store.
--
-- Why a pattern and not a longer list
-- -----------------------------------
-- The enumeration is what rotted. asset_type is constructed in code as
-- f'{prefix}_{variant}' (asset_pipeline.py:293,328; typed_llm.py:55), so the
-- constraint now matches that construction directly: the four known prefixes,
-- optionally suffixed with a single-letter variant. Adding a variant C stops
-- being a schema change. Adding a genuinely new PREFIX still is — which is
-- correct, since that is the case a human should look at.
-- ============================================================================

ALTER TABLE public.word_assets
  DROP CONSTRAINT IF EXISTS word_assets_asset_type_check;

ALTER TABLE public.word_assets
  ADD CONSTRAINT word_assets_asset_type_check
  CHECK (asset_type ~ '^(prompt1_core|prompt2_exercises|prompt3_transforms|llm_types)(_[A-Z])?$');

COMMENT ON CONSTRAINT word_assets_asset_type_check ON public.word_assets IS
  'TASK-522. Pattern rather than enumeration: asset_type is built in code as '
  'prefix_variant, so new variants do not require a migration. A new prefix '
  'still does, deliberately.';


-- ============================================================================
-- Verification
-- ============================================================================
-- The four prefixes and their variants are accepted, junk is not:
--   SELECT t, t ~ '^(prompt1_core|prompt2_exercises|prompt3_transforms|llm_types)(_[A-Z])?$'
--   FROM unnest(ARRAY['prompt1_core','prompt2_exercises_A','prompt3_transforms_B',
--                     'llm_types_A','llm_types_B','llm_types_C',
--                     'nonsense','llm_types_','llm_types_AB']) AS t;
--   -- expect true for the first six, false for the last three.
--
-- Typed-LLM assets start landing after the next generation run:
--   SELECT asset_type, count(*) FROM word_assets GROUP BY 1 ORDER BY 2 DESC;
-- ============================================================================
