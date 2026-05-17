-- ============================================================================
-- add_classifier_drill_mode.sql
--
-- Adds the "Measure Words" (classifier_drill) infinite training tool for
-- Chinese (language_id=1). This migration:
--   1. Registers a new dim_test_types row (type_code='classifier_drill').
--   2. Creates three tables to hold the noun -> classifier dictionary:
--        dim_classifier_distractor_groups (semantic confusability buckets)
--        dim_classifiers                  (one row per classifier hanzi)
--        dim_classifier_noun_pairs        (noun lemma -> classifier links)
--   3. Inserts the 12 distractor groups (script populates the rest).
--   4. Creates a sentinel `tests` row (slug='__classifier_drill_zh', hidden
--      from listings) so the trainer can reuse the existing test_attempts
--      and skill-rating infrastructure without schema changes.
--   5. Seeds test_skill_ratings for the new test type.
--      user_skill_ratings rows are created lazily by the submission RPC.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Register classifier_drill in dim_test_types
-- ----------------------------------------------------------------------------
INSERT INTO dim_test_types (type_code, type_name, requires_audio, is_active, display_order)
VALUES ('classifier_drill', 'Measure Words', false, true, 6)
ON CONFLICT (type_code) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 2. Dictionary tables
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_classifier_distractor_groups (
    id          smallserial PRIMARY KEY,
    language_id smallint NOT NULL REFERENCES dim_languages(id),
    label       text NOT NULL,
    description text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (language_id, label)
);

CREATE TABLE IF NOT EXISTS dim_classifiers (
    id                  smallserial PRIMARY KEY,
    language_id         smallint NOT NULL REFERENCES dim_languages(id),
    hanzi               text NOT NULL,
    pinyin              text NOT NULL,
    pinyin_display      text NOT NULL,
    semantic_label      text NOT NULL,
    example_nouns       text[] NOT NULL DEFAULT '{}',
    frequency_rank      integer NOT NULL,
    distractor_group_id smallint NOT NULL REFERENCES dim_classifier_distractor_groups(id),
    created_at          timestamptz NOT NULL DEFAULT now(),
    UNIQUE (language_id, hanzi)
);

CREATE INDEX IF NOT EXISTS idx_classifiers_group ON dim_classifiers(distractor_group_id);

CREATE TABLE IF NOT EXISTS dim_classifier_noun_pairs (
    id              serial PRIMARY KEY,
    language_id     smallint NOT NULL REFERENCES dim_languages(id),
    noun_sense_id   integer REFERENCES dim_word_senses(id) ON DELETE SET NULL,
    lemma_text      text NOT NULL,
    classifier_id   smallint NOT NULL REFERENCES dim_classifiers(id) ON DELETE CASCADE,
    is_primary      boolean NOT NULL DEFAULT true,
    frequency_score numeric NOT NULL DEFAULT 1.0,
    source          text NOT NULL DEFAULT 'curated',
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (language_id, lemma_text, classifier_id)
);

CREATE INDEX IF NOT EXISTS idx_classifier_pairs_lemma
    ON dim_classifier_noun_pairs(language_id, lemma_text);
CREATE INDEX IF NOT EXISTS idx_classifier_pairs_classifier
    ON dim_classifier_noun_pairs(classifier_id);

-- ----------------------------------------------------------------------------
-- 3. Seed distractor groups (build script joins on the label)
-- ----------------------------------------------------------------------------
INSERT INTO dim_classifier_distractor_groups (language_id, label, description) VALUES
    (1, 'general',    'General / fallback'),
    (1, 'people',     'People'),
    (1, 'animals',    'Animals'),
    (1, 'long_thin',  'Long / thin objects'),
    (1, 'flat',       'Flat objects'),
    (1, 'bound',      'Bound objects (books, volumes)'),
    (1, 'vehicles',   'Vehicles'),
    (1, 'containers', 'Container measures'),
    (1, 'places',     'Buildings and places'),
    (1, 'garments',   'Garments and pairs'),
    (1, 'events',     'Events and instances'),
    (1, 'plants',     'Plants and flowers')
ON CONFLICT (language_id, label) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 4. Sentinel test row + test_skill_rating
-- ----------------------------------------------------------------------------
-- The trainer is session-based (not test-bound), but the test_attempts /
-- test_skill_ratings infrastructure expects a real tests.id. A single
-- sentinel row per language provides that anchor; it is is_active=false so
-- it never surfaces in /api/tests/list, /tests, or recommendation outputs.
DO $$
DECLARE
    v_sentinel_id    uuid;
    v_classifier_tt  smallint;
    v_system_user    uuid;
BEGIN
    SELECT id INTO v_classifier_tt
    FROM dim_test_types WHERE type_code = 'classifier_drill';

    -- Use the oldest existing user.id as gen_user (NOT NULL FK satisfier).
    SELECT id INTO v_system_user FROM users ORDER BY created_at LIMIT 1;
    IF v_system_user IS NULL THEN
        RAISE EXCEPTION 'No users present; cannot create sentinel test';
    END IF;

    -- Insert sentinel or fetch existing
    INSERT INTO tests (
        gen_user, slug, difficulty, tier, title, transcript,
        language_id, is_active, is_featured, is_custom
    ) VALUES (
        v_system_user, '__classifier_drill_zh', 1, 'free-tier',
        'Measure Word Drill (Chinese)', NULL, 1, false, false, false
    )
    ON CONFLICT (slug) DO UPDATE SET updated_at = now()
    RETURNING id INTO v_sentinel_id;

    -- Seed the test-side ELO anchor at 1400 if not present
    IF NOT EXISTS (
        SELECT 1 FROM test_skill_ratings
        WHERE test_id = v_sentinel_id AND test_type_id = v_classifier_tt
    ) THEN
        INSERT INTO test_skill_ratings (test_id, test_type_id, elo_rating, total_attempts)
        VALUES (v_sentinel_id, v_classifier_tt, 1400, 0);
    END IF;
END $$;

COMMIT;
