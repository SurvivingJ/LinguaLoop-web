-- Add style_pack_item_id FK to exercises and update source FK constraint.
-- Run after style_analysis_tables.sql and vocabulary_ladder_schema.sql.

-- 1. Add the FK column
ALTER TABLE public.exercises
    ADD COLUMN IF NOT EXISTS style_pack_item_id BIGINT REFERENCES public.style_pack_items(id);

CREATE INDEX IF NOT EXISTS idx_exercises_style_item
    ON public.exercises(style_pack_item_id)
    WHERE style_pack_item_id IS NOT NULL;

-- 2. Update chk_source_fk to include style_pack_item_id.
--    Constraint requires at least one source FK to be non-null.
ALTER TABLE public.exercises DROP CONSTRAINT IF EXISTS chk_source_fk;
ALTER TABLE public.exercises ADD CONSTRAINT chk_source_fk CHECK (
    (grammar_pattern_id IS NOT NULL)::int +
    (word_sense_id IS NOT NULL)::int +
    (corpus_collocation_id IS NOT NULL)::int +
    (conversation_id IS NOT NULL)::int +
    (style_pack_item_id IS NOT NULL)::int >= 1
);
