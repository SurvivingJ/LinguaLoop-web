-- Plan 6 addendum: indexes for verification sweep and extraction method

-- Verification sweep: unverified rows ordered by LMI for priority processing
CREATE INDEX IF NOT EXISTS idx_cc_unverified
    ON corpus_collocations (language_id, lmi_score DESC)
    WHERE substitution_entropy IS NULL;

-- Extraction method lookup (admin queries)
CREATE INDEX IF NOT EXISTS idx_cc_extraction_method
    ON corpus_collocations (corpus_source_id, extraction_method);
