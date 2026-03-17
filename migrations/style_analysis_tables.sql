-- Style analysis tables for corpus writing-style profiling and packs.
-- Run after corpus_analysis_tables.sql.

-- ── Style profiles: one row per corpus source ──────────────────────────

CREATE TABLE IF NOT EXISTS corpus_style_profiles (
    id                   BIGSERIAL PRIMARY KEY,
    corpus_source_id     BIGINT NOT NULL REFERENCES corpus_sources(id) ON DELETE CASCADE,
    language_id          INTEGER NOT NULL REFERENCES dim_languages(id),

    -- Feature categories (JSONB)
    raw_frequency_ngrams   JSONB DEFAULT '{}',
    characteristic_ngrams  JSONB DEFAULT '{}',
    sentence_structures    JSONB DEFAULT '{}',
    syntactic_preferences  JSONB DEFAULT '{}',
    discourse_patterns     JSONB DEFAULT '{}',
    vocabulary_profile     JSONB DEFAULT '{}',

    -- Metadata
    total_tokens         INTEGER DEFAULT 0,
    total_sentences      INTEGER DEFAULT 0,
    reference_source_id  BIGINT REFERENCES corpus_sources(id),

    created_at           TIMESTAMPTZ DEFAULT NOW(),
    updated_at           TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (corpus_source_id)
);

CREATE INDEX IF NOT EXISTS idx_style_profiles_language
    ON corpus_style_profiles (language_id);


-- ── Style pack items: individual learnable items from profiles ─────────

CREATE TABLE IF NOT EXISTS style_pack_items (
    id               BIGSERIAL PRIMARY KEY,
    corpus_source_id BIGINT NOT NULL REFERENCES corpus_sources(id) ON DELETE CASCADE,
    language_id      INTEGER NOT NULL REFERENCES dim_languages(id),

    item_type        TEXT NOT NULL CHECK (item_type IN (
        'frequent_ngram', 'characteristic_ngram', 'sentence_pattern',
        'syntactic_feature', 'discourse_pattern', 'vocabulary_item'
    )),
    item_text        TEXT NOT NULL,
    item_data        JSONB DEFAULT '{}',
    frequency        INTEGER DEFAULT 0,
    keyness_score    FLOAT DEFAULT 0.0,
    sort_order       INTEGER DEFAULT 0,

    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_style_pack_items_source_type
    ON style_pack_items (corpus_source_id, item_type);


-- ── Join table: packs ↔ style items ───────────────────────────────────

CREATE TABLE IF NOT EXISTS pack_style_items (
    id            BIGSERIAL PRIMARY KEY,
    pack_id       BIGINT NOT NULL REFERENCES collocation_packs(id) ON DELETE CASCADE,
    style_item_id BIGINT NOT NULL REFERENCES style_pack_items(id) ON DELETE CASCADE,
    UNIQUE (pack_id, style_item_id)
);


-- ── Extend pack_type on collocation_packs to include 'style' ──────────

ALTER TABLE collocation_packs
    DROP CONSTRAINT IF EXISTS collocation_packs_pack_type_check;

ALTER TABLE collocation_packs
    ADD CONSTRAINT collocation_packs_pack_type_check
    CHECK (pack_type IN ('author', 'genre', 'topic', 'style'));


-- ── Extend exercise_source_type enum to include 'style' ───────────────

ALTER TYPE exercise_source_type ADD VALUE IF NOT EXISTS 'style';
