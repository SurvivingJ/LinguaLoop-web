-- ============================================================
-- Plan 5: Corpus Analysis Pipeline — RPC Functions and Views
-- ============================================================
-- Run this migration AFTER corpus_analysis_tables.sql
-- ============================================================

-- ============================================================
-- RPC: get_top_collocations_for_sources
-- Aggregates collocations across multiple corpus sources,
-- deduplicates by collocation_text, ranks by max PMI,
-- returns top-N results above a minimum PMI threshold.
-- ============================================================
CREATE OR REPLACE FUNCTION get_top_collocations_for_sources(
    p_source_ids  INTEGER[],
    p_min_pmi     FLOAT,
    p_top_n       INTEGER
)
RETURNS TABLE (
    id                BIGINT,
    collocation_text  TEXT,
    n_gram_size       INTEGER,
    pmi_score         FLOAT,
    log_likelihood    FLOAT,
    t_score           FLOAT,
    lmi_score         FLOAT,
    collocation_type  TEXT,
    pos_pattern       TEXT,
    language_id       INTEGER
)
LANGUAGE SQL
STABLE
AS $$
    -- Subquery: pick the highest-LMI representative for each collocation_text,
    -- then re-sort globally by LMI and apply LIMIT for correct top-N.
    -- Only includes validated collocations (verified by substitution entropy).
    SELECT sub.id, sub.collocation_text, sub.n_gram_size, sub.pmi_score,
           sub.log_likelihood, sub.t_score, sub.lmi_score, sub.collocation_type,
           sub.pos_pattern, sub.language_id
    FROM (
        SELECT DISTINCT ON (cc.collocation_text)
            cc.id,
            cc.collocation_text,
            cc.n_gram_size,
            cc.pmi_score,
            cc.log_likelihood,
            cc.t_score,
            cc.lmi_score,
            cc.collocation_type,
            cc.pos_pattern,
            cc.language_id
        FROM corpus_collocations cc
        WHERE cc.corpus_source_id = ANY(p_source_ids)
          AND cc.pmi_score >= p_min_pmi
          AND (cc.is_validated = TRUE OR cc.is_validated IS NULL)
        ORDER BY cc.collocation_text, cc.lmi_score DESC
    ) sub
    ORDER BY sub.lmi_score DESC
    LIMIT p_top_n;
$$;


-- ============================================================
-- RPC: get_packs_with_user_selection
-- Returns public packs for a language, annotated with
-- whether the requesting user has already selected each.
-- ============================================================
CREATE OR REPLACE FUNCTION get_packs_with_user_selection(
    p_language_id  INTEGER,
    p_user_id      TEXT
)
RETURNS TABLE (
    id               BIGINT,
    pack_name        TEXT,
    description      TEXT,
    pack_type        TEXT,
    tags             TEXT[],
    total_items      INTEGER,
    difficulty_range TEXT,
    is_selected      BOOLEAN
)
LANGUAGE SQL
STABLE
AS $$
    SELECT
        cp.id,
        cp.pack_name,
        cp.description,
        cp.pack_type,
        cp.tags,
        cp.total_items,
        cp.difficulty_range,
        (ups.user_id IS NOT NULL) AS is_selected
    FROM collocation_packs cp
    LEFT JOIN user_pack_selections ups
        ON ups.pack_id = cp.id
       AND ups.user_id = p_user_id
    WHERE cp.language_id = p_language_id
      AND cp.is_public = TRUE
    ORDER BY cp.pack_name;
$$;


-- ============================================================
-- View: corpus_statistics
-- Admin view showing collocation coverage by language and type.
-- ============================================================
CREATE OR REPLACE VIEW corpus_statistics AS
SELECT
    cc.language_id,
    dl.language_name,
    cc.collocation_type,
    cc.n_gram_size,
    COUNT(*)                                           AS collocation_count,
    ROUND(AVG(cc.pmi_score)::NUMERIC, 3)               AS avg_pmi,
    ROUND(AVG(cc.frequency)::NUMERIC, 1)               AS avg_frequency,
    COUNT(*) FILTER (WHERE cc.is_validated = TRUE)      AS validated_count
FROM corpus_collocations cc
JOIN dim_languages dl ON dl.id = cc.language_id
GROUP BY cc.language_id, dl.language_name, cc.collocation_type, cc.n_gram_size
ORDER BY cc.language_id, cc.n_gram_size, cc.collocation_type;
