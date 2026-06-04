-- Migration: two-level senses + provenance on dim_word_senses
-- Adds graded definition levels (simple/standard), generation provenance, and a
-- self-rated confidence captured from the single-call sense generator.
--
-- Existing rows default to definition_level='standard', source='llm' so every
-- current sense keeps working. Read paths that assume one definition per sense
-- (get_distractors, flashcards) must filter definition_level='standard' so the
-- new simple rows do not fan out duplicates.

ALTER TABLE dim_word_senses
  ADD COLUMN definition_level text NOT NULL DEFAULT 'standard'
    CHECK (definition_level IN ('simple','standard')),
  ADD COLUMN source text NOT NULL DEFAULT 'llm'
    CHECK (source IN ('llm','manual')),
  ADD COLUMN source_ref text,        -- model name + prompt version that produced the row
  ADD COLUMN gen_confidence real;    -- self-rated confidence from single-call generation

-- The old uniqueness was (vocab_id, definition_language_id, definition); two
-- levels share a meaning at the same sense_rank, so key on level + rank instead.
ALTER TABLE dim_word_senses DROP CONSTRAINT uq_sense_definition;
ALTER TABLE dim_word_senses
  ADD CONSTRAINT uq_sense_def_level
  UNIQUE (vocab_id, definition_language_id, definition_level, sense_rank);

CREATE INDEX idx_senses_source ON dim_word_senses(source);
