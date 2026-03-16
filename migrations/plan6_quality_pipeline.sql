-- ============================================================
-- Plan 6: Corpus Collocation Quality Pipeline — Migration
-- ============================================================
-- Run this migration in Supabase SQL editor.
-- Adds: LMI score, extraction method, dependency relation,
--        substitution entropy, and updated is_validated default.
-- ============================================================

-- Phase 1: LMI score (frequency-weighted PMI for ranking)
ALTER TABLE corpus_collocations
    ADD COLUMN IF NOT EXISTS lmi_score FLOAT DEFAULT 0;

-- Phase 3: Dependency extraction metadata
ALTER TABLE corpus_collocations
    ADD COLUMN IF NOT EXISTS extraction_method VARCHAR(20) DEFAULT 'ngram',
    ADD COLUMN IF NOT EXISTS dependency_relation VARCHAR(20) DEFAULT NULL;

-- Phase 4: Substitution entropy (MLM-based verification score)
ALTER TABLE corpus_collocations
    ADD COLUMN IF NOT EXISTS substitution_entropy FLOAT DEFAULT NULL;

-- Change is_validated default from FALSE to NULL so we can distinguish
-- "not yet verified" from "verified and rejected"
ALTER TABLE corpus_collocations
    ALTER COLUMN is_validated DROP DEFAULT;
ALTER TABLE corpus_collocations
    ALTER COLUMN is_validated SET DEFAULT NULL;

-- Index for pack promotion: only validated, high-quality collocations
CREATE INDEX IF NOT EXISTS idx_corpus_collocations_validated_lmi
    ON corpus_collocations (language_id, is_validated, lmi_score DESC)
    WHERE is_validated = TRUE;
