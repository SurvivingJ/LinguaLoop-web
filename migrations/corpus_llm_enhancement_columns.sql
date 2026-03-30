-- ============================================================
-- Corpus LLM Enhancement — New Columns
-- ============================================================
-- Adds columns for LLM-enriched data produced by the
-- collocation validator, semantic tagger, and style narrative
-- generator.
-- ============================================================

-- corpus_collocations: LLM validation score and semantic tags
ALTER TABLE corpus_collocations
    ADD COLUMN IF NOT EXISTS pedagogical_score INTEGER,
    ADD COLUMN IF NOT EXISTS semantic_tags     TEXT[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS lmi_score         FLOAT DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS extraction_method TEXT DEFAULT 'ngram',
    ADD COLUMN IF NOT EXISTS dependency_relation TEXT;

-- corpus_style_profiles: LLM-generated narrative summary
ALTER TABLE corpus_style_profiles
    ADD COLUMN IF NOT EXISTS narrative JSONB;

-- Index for filtering by pedagogical score
CREATE INDEX IF NOT EXISTS idx_collocations_pedagogical_score
    ON corpus_collocations (pedagogical_score)
    WHERE pedagogical_score IS NOT NULL;

-- GIN index for semantic tag filtering
CREATE INDEX IF NOT EXISTS idx_collocations_semantic_tags
    ON corpus_collocations USING GIN (semantic_tags)
    WHERE semantic_tags != '{}';
