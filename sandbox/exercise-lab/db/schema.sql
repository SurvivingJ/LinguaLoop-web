-- exercise-lab sandbox schema
--
-- WHY THIS EXISTS: prototypes for a new generation pipeline / serving
-- algorithm need a database to read and write, but this sandbox is
-- forbidden from touching Supabase. This file is a SQLite mirror of the
-- SLICE of the production schema that generation + serving prototypes
-- actually need, named and typed to match production as closely as SQLite
-- allows, so a prototype written against this file ports to the real
-- schema with mostly mechanical changes (not a rewrite).
--
-- Sources for column shape: sandbox/exercise-lab/docs/recon-data-surface.md
-- §1 (cites wiki/database/schema.tech.md + migrations/*.sql line numbers).
--
-- Deliberate deviations from production (all FIDELITY GAPS, see README):
--   1. No pgvector. `dim_word_senses.embedding` is a BLOB of packed float32
--      (see lab/embeddings.py:pack_embedding/unpack_embedding). There is no
--      HNSW index - any "nearest neighbour" search in this sandbox is a
--      linear scan in Python, which is fine at this row count but does NOT
--      validate anything about production's index-backed query latency.
--   2. Postgres `text[]`/`jsonb` columns become TEXT columns holding a JSON
--      string (SQLite has no native array/jsonb type). Callers must
--      json.loads()/json.dumps() at the boundary - see lab/db.py helpers.
--   3. No RLS, no auth.uid(), no service-role distinction - this is a
--      single-writer local file, security modeling is out of scope here.
--   4. Foreign keys are declared but SQLite only enforces them when
--      `PRAGMA foreign_keys = ON` is set per-connection (lab/db.py does
--      this for you - raw sqlite3.connect() callers must remember to).
--   5. No triggers, no computed/generated columns, no CHECK-constraint
--      parity with every production constraint - only the ones that matter
--      for a prototype not silently corrupting its own seed data are
--      enforced here (e.g. definition_level CHECK).

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- dim_languages
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_languages (
    id              INTEGER PRIMARY KEY,   -- matches live ids: 1=zh(cn), 2=en, 3=ja(jp)
    language_code   TEXT NOT NULL UNIQUE,  -- literal live values: 'cn','en','jp' (NOT 'zh'/'ja')
    language_name   TEXT NOT NULL,
    native_name     TEXT,
    iso_639_1       TEXT,
    iso_639_3       TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    display_order   INTEGER NOT NULL DEFAULT 0,
    tts_voice_ids   TEXT,                  -- JSON, unseeded (no TTS in this sandbox)
    tts_speed       REAL,
    grammar_check_enabled INTEGER
);

-- ---------------------------------------------------------------------
-- dim_vocabulary  (one row per (language_id, lemma))
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_vocabulary (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    language_id      INTEGER NOT NULL REFERENCES dim_languages(id),
    lemma            TEXT NOT NULL,
    phrase_type      TEXT NOT NULL DEFAULT 'single_word',
    component_lemmas TEXT,                 -- JSON array of strings, or NULL
    part_of_speech   TEXT,
    frequency_rank   REAL,                 -- ZIPF SCORE (0.25-6.56), NOT a rank.
                                            -- Higher = MORE common. Inverting this
                                            -- ordering is a real bug class - see
                                            -- docs/recon-data-surface.md §1 and
                                            -- migrations/calibration_semantic_distractors.sql:39-52.
    level_tag        TEXT,                 -- sandbox-only provenance tag, see README
    semantic_class   TEXT,
    UNIQUE(language_id, lemma)
);
CREATE INDEX IF NOT EXISTS idx_dim_vocabulary_lang ON dim_vocabulary(language_id);
CREATE INDEX IF NOT EXISTS idx_dim_vocabulary_freq ON dim_vocabulary(frequency_rank);

-- ---------------------------------------------------------------------
-- dim_word_senses  (TWO rows per real sense: definition_level simple/standard,
-- sharing one sense_rank - see docs/recon-data-surface.md §1)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_word_senses (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    vocab_id               INTEGER NOT NULL REFERENCES dim_vocabulary(id),
    definition_language_id INTEGER NOT NULL REFERENCES dim_languages(id),
    definition             TEXT,           -- NULL where no local source had one (see README - en gap)
    definition_level       TEXT NOT NULL CHECK (definition_level IN ('simple','standard')),
    pronunciation          TEXT,
    ipa_pronunciation      TEXT,
    example_sentence       TEXT,
    sense_rank             INTEGER NOT NULL DEFAULT 1,
    usage_frequency        REAL,
    semantic_category      TEXT,
    morphological_forms    TEXT,           -- JSON
    is_validated           INTEGER NOT NULL DEFAULT 0,
    gen_confidence         REAL,
    source                 TEXT,           -- 'cedict' | 'jmdict' | 'wordfreq+spacy' | 'manual'
    embedding              BLOB            -- packed float32 vector, or NULL if not computed
                                            -- (see lab/embeddings.py, README "embedding coverage")
);
CREATE INDEX IF NOT EXISTS idx_dim_word_senses_vocab ON dim_word_senses(vocab_id);
CREATE INDEX IF NOT EXISTS idx_dim_word_senses_level ON dim_word_senses(definition_level);

-- ---------------------------------------------------------------------
-- word_assets  (LLM-seed material, per (sense_id, asset_type)).
-- Intentionally seeded with ZERO rows by build_db.py: this sandbox may
-- never call an LLM, and this table's whole purpose in production is to
-- hold LLM output. A later agent's mock_llm-backed prototype generator is
-- the only thing expected to ever INSERT here.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS word_assets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sense_id    INTEGER NOT NULL REFERENCES dim_word_senses(id),
    asset_type  TEXT NOT NULL,   -- prompt1_core | prompt2_exercises[_A/_B] | prompt3_transforms[_A/_B] | ...
    content     TEXT,            -- JSON
    is_valid    INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_word_assets_sense ON word_assets(sense_id);

-- ---------------------------------------------------------------------
-- exercises  (final, servable rows - seeded empty; harness-run prototype
-- generators populate this table, see lab/harness.py)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS exercises (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    language_id         INTEGER NOT NULL REFERENCES dim_languages(id),
    exercise_type       TEXT NOT NULL,
    source_type         TEXT NOT NULL DEFAULT 'vocabulary',
    grammar_pattern_id  INTEGER,
    word_sense_id       INTEGER REFERENCES dim_word_senses(id),
    word_asset_id       INTEGER REFERENCES word_assets(id),
    content             TEXT,     -- JSON
    tags                TEXT,     -- JSON
    difficulty_static   REAL,
    irt_difficulty      REAL,
    irt_discrimination  REAL,
    irt_n_attempts      INTEGER DEFAULT 0,
    irt_calibrated_at   TEXT,
    irt_se_difficulty   REAL,
    complexity_tier     TEXT,     -- T1-T6
    ladder_level        INTEGER,  -- 1-9
    attempt_count       INTEGER NOT NULL DEFAULT 0,
    correct_count       INTEGER NOT NULL DEFAULT 0,
    is_active           INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_exercises_sense ON exercises(word_sense_id);
CREATE INDEX IF NOT EXISTS idx_exercises_lang_type ON exercises(language_id, exercise_type);

-- ---------------------------------------------------------------------
-- tests / questions  (seeded from generated_tests_20251209_225642_*.csv)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tests (
    id                TEXT PRIMARY KEY,   -- source uuid, kept as text (SQLite has no uuid type)
    language_id       INTEGER NOT NULL REFERENCES dim_languages(id),
    slug              TEXT,
    topic             TEXT,
    difficulty        INTEGER,            -- 1-9, legacy axis (see recon-serving.md §5)
    style             TEXT,
    tier              TEXT,
    title             TEXT,
    transcript        TEXT NOT NULL,      -- plain text, unwrapped from the source CSV's
                                           -- ```json-fenced envelope - see build_db.py
    total_attempts    INTEGER NOT NULL DEFAULT 0,
    is_active         INTEGER NOT NULL DEFAULT 1,
    is_featured       INTEGER NOT NULL DEFAULT 0,
    is_custom         INTEGER NOT NULL DEFAULT 0,
    generation_model  TEXT,
    vocab_sense_ids   TEXT,               -- JSON int array. Empty [] for every seeded row:
                                           -- no sense-linking pass has been run in this sandbox
                                           -- (see README - "not wired" list).
    vocab_token_map   TEXT,               -- JSON, empty {} - see above
    created_at        TEXT,
    updated_at        TEXT
);
CREATE INDEX IF NOT EXISTS idx_tests_lang ON tests(language_id);
CREATE INDEX IF NOT EXISTS idx_tests_difficulty ON tests(difficulty);

CREATE TABLE IF NOT EXISTS questions (
    id                 TEXT PRIMARY KEY,
    test_id            TEXT NOT NULL REFERENCES tests(id),
    question_id        TEXT,
    question_text      TEXT NOT NULL,
    question_type      TEXT,
    choices             TEXT,             -- JSON array of strings
    correct_answer     TEXT,              -- literal string, matches one of `choices`
                                           -- (confirmed real-row shape, recon-data-surface.md §1)
    answer_explanation TEXT,
    points             INTEGER NOT NULL DEFAULT 1,
    sense_ids          TEXT,              -- JSON int array, empty [] (not linked, see tests table)
    created_at         TEXT
);
CREATE INDEX IF NOT EXISTS idx_questions_test ON questions(test_id);

-- ---------------------------------------------------------------------
-- user_skill_ratings / user_vocabulary_knowledge - structural only,
-- seeded empty. learner_sim.py operates on its own in-memory dataclasses
-- and does NOT require these tables; they exist so a prototype selector
-- can persist state the way production does, if it wants to.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_skill_ratings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      TEXT NOT NULL,
    language_id  INTEGER NOT NULL REFERENCES dim_languages(id),
    test_type    TEXT NOT NULL,
    elo          REAL NOT NULL DEFAULT 1200,   -- production init/clamp: 400-3000
    updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, language_id, test_type)
);

CREATE TABLE IF NOT EXISTS user_vocabulary_knowledge (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id                TEXT NOT NULL,
    sense_id               INTEGER NOT NULL REFERENCES dim_word_senses(id),
    p_known                REAL NOT NULL DEFAULT 0.10,   -- BKT state, production default
    status                 TEXT NOT NULL DEFAULT 'unknown',
    evidence_count         INTEGER NOT NULL DEFAULT 0,
    comprehension_correct  INTEGER NOT NULL DEFAULT 0,
    comprehension_wrong    INTEGER NOT NULL DEFAULT 0,
    word_test_correct      INTEGER NOT NULL DEFAULT 0,
    word_test_wrong        INTEGER NOT NULL DEFAULT 0,
    UNIQUE(user_id, sense_id)
);

-- ---------------------------------------------------------------------
-- attempts tables - structural only, seeded empty
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS exercise_attempts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        TEXT NOT NULL,
    exercise_id    INTEGER NOT NULL REFERENCES exercises(id),
    user_response  TEXT,     -- JSON
    is_correct     INTEGER NOT NULL,   -- arrives client-computed in production for all but
                                        -- cloze_typed - see docs/recon-data-surface.md §5
    time_taken_ms  INTEGER,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS test_attempts (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id               TEXT NOT NULL,
    test_id               TEXT NOT NULL REFERENCES tests(id),
    score_pct             REAL,
    elo_before            REAL,
    elo_after             REAL,
    test_elo_before       REAL,
    test_elo_after        REAL,
    replay_count          INTEGER NOT NULL DEFAULT 0,
    elo_reduction_factor  REAL,        -- ADR-006 damping factor, NULL on first attempts
    created_at            TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS question_attempt_results (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    test_attempt_id  INTEGER NOT NULL REFERENCES test_attempts(id),
    question_id      TEXT NOT NULL,
    is_correct       INTEGER NOT NULL,
    selected_answer  TEXT,
    correct_answer   TEXT
    -- NOTE: no response_time_ms column - production deliberately dropped it
    -- (migrations/partG_qar_drop_response_time.sql, recon-serving.md §5).
    -- Reproduced here on purpose, not an oversight.
);

-- ---------------------------------------------------------------------
-- Measure-word (classifier/counter) dictionaries
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_classifiers (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    language_id         INTEGER NOT NULL REFERENCES dim_languages(id),
    hanzi               TEXT NOT NULL,
    pinyin              TEXT,
    pinyin_display      TEXT,
    semantic_label      TEXT,
    example_nouns       TEXT,     -- JSON array
    frequency_rank      REAL,
    distractor_group_id INTEGER   -- no distractor_group table in this sandbox slice; always NULL
);

CREATE TABLE IF NOT EXISTS dim_classifier_noun_pairs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    language_id      INTEGER NOT NULL REFERENCES dim_languages(id),
    noun_sense_id    INTEGER REFERENCES dim_word_senses(id),  -- NULL where lemma didn't resolve
                                                               -- against seeded dim_vocabulary
    lemma_text       TEXT NOT NULL,
    classifier_id    INTEGER NOT NULL REFERENCES dim_classifiers(id),
    is_primary       INTEGER NOT NULL DEFAULT 1,
    frequency_score  REAL,
    source           TEXT NOT NULL DEFAULT 'classifier_curation_json'
);
CREATE INDEX IF NOT EXISTS idx_ccnp_classifier ON dim_classifier_noun_pairs(classifier_id);

-- Japanese mirror (助数詞 counters)
CREATE TABLE IF NOT EXISTS dim_counters (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    language_id         INTEGER NOT NULL REFERENCES dim_languages(id),
    kanji               TEXT NOT NULL,
    reading             TEXT,
    reading_display     TEXT,
    semantic_label      TEXT,
    example_nouns       TEXT,     -- JSON array
    frequency_rank      REAL,
    distractor_group_id INTEGER
);

CREATE TABLE IF NOT EXISTS dim_counter_noun_pairs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    language_id      INTEGER NOT NULL REFERENCES dim_languages(id),
    noun_sense_id    INTEGER REFERENCES dim_word_senses(id),
    lemma_text       TEXT NOT NULL,
    counter_id       INTEGER NOT NULL REFERENCES dim_counters(id),
    is_primary       INTEGER NOT NULL DEFAULT 1,
    frequency_score  REAL,
    source           TEXT NOT NULL DEFAULT 'counter_curation_json'
);
CREATE INDEX IF NOT EXISTS idx_cnnp_counter ON dim_counter_noun_pairs(counter_id);
