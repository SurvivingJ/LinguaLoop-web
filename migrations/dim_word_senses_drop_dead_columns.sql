-- ============================================================================
-- dim_word_senses: drop four dead columns and one redundant index (2026-09-21)
-- ============================================================================
--
-- Dropped columns — verified unused on 2026-09-21:
--   usage_notes        NULL in all 55,002 rows
--   semantic_category  NULL in all 55,002 rows
--   validated_by       NULL in all 55,002 rows (FK -> users(id) goes with it)
--   usage_frequency    'common' in all 55,002 rows — only ever its column DEFAULT;
--                      no writer sets it (CHECK common/uncommon/rare/archaic goes with it)
--   No references in application code (py/js/html/ts across WebApp and the sibling
--   LinguaLoop projects), public functions/procedures, views, RLS policies or
--   triggers. The only mentions are the historical DDL in create_all_tables.sql,
--   archive/db_schema_live_2026-03-18.sql and the exercise-lab sandbox schema,
--   which are left as records.
--
-- Dropped index:
--   idx_senses_vocab (vocab_id), 1.5 MB. Redundant with idx_senses_rank
--   (vocab_id, sense_rank) and uq_sense_def_level (vocab_id, ...), both leading
--   on vocab_id. Measured on a 150-vocab_id ANY() lookup: 0.55 ms with it,
--   0.56 ms without (planner switches to idx_senses_rank). It is not needed to
--   back the vocab_id FK for ON DELETE from dim_vocabulary — idx_senses_rank does.
--
-- Space: ~2 MB now (NULL columns cost only bitmap bits until the next table
-- rewrite; usage_frequency's 376 kB and the index are reclaimed). The rest of
-- the dead-row / TOAST bloat is reclaimed by the next table rewrite, e.g.
-- migrations/shrink_sense_embeddings_halfvec768.sql.
--
-- Rollback: re-add the columns as nullable (usage_frequency DEFAULT 'common'
-- with its CHECK, validated_by uuid REFERENCES users(id)) and
-- CREATE INDEX idx_senses_vocab ON public.dim_word_senses (vocab_id).
-- No data is lost: the columns held nothing but NULLs and one default.
-- ============================================================================

BEGIN;

ALTER TABLE public.dim_word_senses
    DROP COLUMN IF EXISTS usage_notes,
    DROP COLUMN IF EXISTS semantic_category,
    DROP COLUMN IF EXISTS validated_by,
    DROP COLUMN IF EXISTS usage_frequency;

DROP INDEX IF EXISTS public.idx_senses_vocab;

COMMIT;
