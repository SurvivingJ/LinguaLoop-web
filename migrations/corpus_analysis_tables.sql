-- ============================================================
-- Plan 5: Corpus Analysis Pipeline — Table Definitions
-- ============================================================
-- Run this migration in Supabase SQL editor before deploying
-- the Python corpus analysis services.
-- ============================================================

-- =============================================
-- corpus_sources: metadata for each ingested text
-- =============================================
CREATE TABLE IF NOT EXISTS corpus_sources (
    id              BIGSERIAL PRIMARY KEY,
    source_type     TEXT NOT NULL CHECK (source_type IN ('url', 'text', 'author')),
    source_url      TEXT,
    source_title    TEXT NOT NULL,
    language_id     INTEGER NOT NULL REFERENCES dim_languages(id),
    tags            TEXT[] DEFAULT '{}',
    raw_text        TEXT,
    raw_text_path   TEXT,
    word_count      INTEGER DEFAULT 0,
    processed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- corpus_collocations: scored n-grams extracted from corpus sources
-- head_word and collocate are required by exercise generators
-- (services/exercise_generation/generators/collocation.py)
-- =============================================
CREATE TABLE IF NOT EXISTS corpus_collocations (
    id                BIGSERIAL PRIMARY KEY,
    corpus_source_id  BIGINT NOT NULL REFERENCES corpus_sources(id) ON DELETE CASCADE,
    language_id       INTEGER NOT NULL REFERENCES dim_languages(id),
    collocation_text  TEXT NOT NULL,
    head_word         TEXT,
    collocate         TEXT,
    n_gram_size       INTEGER NOT NULL,
    frequency         INTEGER NOT NULL DEFAULT 0,
    pmi_score         FLOAT DEFAULT 0.0,
    log_likelihood    FLOAT DEFAULT 0.0,
    t_score           FLOAT DEFAULT 0.0,
    collocation_type  TEXT DEFAULT 'collocation'
        CHECK (collocation_type IN ('collocation', 'fixed_phrase', 'discourse_marker')),
    pos_pattern       TEXT DEFAULT '',
    tags              TEXT[] DEFAULT '{}',
    is_validated      BOOLEAN DEFAULT FALSE,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- collocation_packs: user-facing curated sets
-- =============================================
CREATE TABLE IF NOT EXISTS collocation_packs (
    id                BIGSERIAL PRIMARY KEY,
    pack_name         TEXT NOT NULL,
    description       TEXT DEFAULT '',
    language_id       INTEGER NOT NULL REFERENCES dim_languages(id),
    tags              TEXT[] DEFAULT '{}',
    source_type       TEXT DEFAULT 'corpus',
    pack_type         TEXT DEFAULT 'topic'
        CHECK (pack_type IN ('author', 'genre', 'topic')),
    total_items       INTEGER DEFAULT 0,
    difficulty_range  TEXT,
    is_public         BOOLEAN DEFAULT TRUE,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- pack_collocations: join table linking packs to collocations
-- =============================================
CREATE TABLE IF NOT EXISTS pack_collocations (
    id              BIGSERIAL PRIMARY KEY,
    pack_id         BIGINT NOT NULL REFERENCES collocation_packs(id) ON DELETE CASCADE,
    collocation_id  BIGINT NOT NULL REFERENCES corpus_collocations(id) ON DELETE CASCADE,
    UNIQUE (pack_id, collocation_id)
);

-- =============================================
-- user_pack_selections: tracks which packs a user has opted into
-- =============================================
CREATE TABLE IF NOT EXISTS user_pack_selections (
    id         BIGSERIAL PRIMARY KEY,
    user_id    TEXT NOT NULL,
    pack_id    BIGINT NOT NULL REFERENCES collocation_packs(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, pack_id)
);

-- =============================================
-- Indexes
-- =============================================

-- All collocations for a source, ordered by PMI
CREATE INDEX IF NOT EXISTS idx_corpus_collocations_source_pmi
    ON corpus_collocations (corpus_source_id, pmi_score DESC);

-- Language + PMI range queries (cross-source pack creation, browse)
CREATE INDEX IF NOT EXISTS idx_corpus_collocations_lang_pmi
    ON corpus_collocations (language_id, pmi_score DESC);

-- Collocation text lookup for deduplication
CREATE INDEX IF NOT EXISTS idx_corpus_collocations_text_lang
    ON corpus_collocations (language_id, collocation_text);

-- Filter by type (discourse_marker, fixed_phrase, collocation)
CREATE INDEX IF NOT EXISTS idx_corpus_collocations_type
    ON corpus_collocations (language_id, collocation_type);

-- head_word lookups (used by OddCollocationOutGenerator._fetch_natural_collocates)
CREATE INDEX IF NOT EXISTS idx_corpus_collocations_head_word
    ON corpus_collocations (head_word, pmi_score DESC);

-- Find unprocessed sources for background jobs
CREATE INDEX IF NOT EXISTS idx_corpus_sources_unprocessed
    ON corpus_sources (processed_at) WHERE processed_at IS NULL;

-- pack_collocations: lookups in both directions
CREATE INDEX IF NOT EXISTS idx_pack_collocations_pack
    ON pack_collocations (pack_id);
CREATE INDEX IF NOT EXISTS idx_pack_collocations_collocation
    ON pack_collocations (collocation_id);
