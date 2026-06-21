-- TASK-509: Traditional Chinese groundwork (dual-store)
-- (Exercise Generation v2, plan §6.7)
--
-- Operator decision: dual-store BOTH scripts at generation time rather than
-- converting at serve time. This migration adds the storage; population is done
-- by scripts/backfill_hant_mirrors.py (lemmas + existing exercise mirrors) and,
-- for new exercises, by LadderExerciseRenderer._render_hant_mirror.
--
-- Idempotent: ADD COLUMN IF NOT EXISTS / CREATE TABLE IF NOT EXISTS.

-- 1. Per-lemma Traditional form. Filled by OpenCC s2twp (phrase-aware) with the
--    overrides table consulted for residual ambiguous lemmas (发→發/髮 class).
ALTER TABLE dim_vocabulary
    ADD COLUMN IF NOT EXISTS lemma_traditional text;

COMMENT ON COLUMN dim_vocabulary.lemma_traditional IS
    'TASK-509: Traditional (Taiwan, s2twp) form of lemma. Simplified lemma stays '
    'in dim_vocabulary.lemma; this is its dual-store mirror.';

-- 2. Curated override table for the residual one-to-many conversions OpenCC's
--    s2twp still gets wrong. ScriptConverter swaps these in with absolute
--    priority over OpenCC. Simplified is the PK so corrections are a simple
--    upsert; re-running the backfill then updates only the affected mirrors.
CREATE TABLE IF NOT EXISTS script_conversion_overrides (
    simplified  text PRIMARY KEY,
    traditional text NOT NULL,
    note        text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE script_conversion_overrides IS
    'TASK-509: human-curated Simplified→Traditional overrides that beat OpenCC '
    's2twp for ambiguous lemmas/phrases. Consulted by ScriptConverter at every '
    'mirror render and lemma backfill.';

-- 3. Serve-time convention (documentation; consumed by TASK-526):
--    users.exercise_preferences is a JSONB column; the key `script_variant`
--    selects which ZH script a learner sees — 'simplified' (default, the base
--    content) or 'traditional' (serve content.hant / lemma_traditional). No
--    column change is needed here; this comment records the contract.
