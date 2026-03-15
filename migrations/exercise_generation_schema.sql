-- ============================================================================
-- Exercise Generation Pipeline Schema Migration
-- Plan 1: Exercise Content Generation Pipeline V3
-- ============================================================================

-- ==========================================================================
-- Task 0.1: dim_grammar_patterns table
-- ==========================================================================

CREATE TABLE IF NOT EXISTS dim_grammar_patterns (
    id                   SERIAL PRIMARY KEY,
    pattern_code         TEXT NOT NULL UNIQUE,
    pattern_name         TEXT NOT NULL,
    description          TEXT NOT NULL,
    user_facing_description TEXT NOT NULL,
    example_sentence     TEXT NOT NULL,
    example_sentence_en  TEXT,
    language_id          INTEGER NOT NULL REFERENCES dim_languages(id),
    cefr_level           TEXT NOT NULL CHECK (cefr_level IN ('A1','A2','B1','B2','C1','C2')),
    category             TEXT NOT NULL CHECK (category IN (
                             'tense','aspect','voice','particles','word_order','modality',
                             'clause_structure','conjugation','honorifics','measure_words','complement'
                         )),
    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_grammar_patterns_language ON dim_grammar_patterns(language_id);
CREATE INDEX IF NOT EXISTS idx_grammar_patterns_cefr     ON dim_grammar_patterns(cefr_level);
CREATE INDEX IF NOT EXISTS idx_grammar_patterns_active   ON dim_grammar_patterns(is_active) WHERE is_active = TRUE;

-- ==========================================================================
-- Task 0.2: exercises table
-- ==========================================================================

DO $$ BEGIN
    CREATE TYPE exercise_source_type AS ENUM ('grammar', 'vocabulary', 'collocation');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS exercises (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    language_id             INTEGER NOT NULL REFERENCES dim_languages(id),
    exercise_type           TEXT NOT NULL,
    source_type             exercise_source_type NOT NULL,
    grammar_pattern_id      INTEGER REFERENCES dim_grammar_patterns(id),
    word_sense_id           INTEGER REFERENCES dim_word_senses(id),
    corpus_collocation_id   INTEGER,  -- FK added when Plan 5 schema is ready
    content                 JSONB NOT NULL,
    tags                    JSONB NOT NULL DEFAULT '{}',
    difficulty_static       NUMERIC(4,2),
    irt_difficulty          NUMERIC(5,3) NOT NULL DEFAULT 0.0,
    irt_discrimination      NUMERIC(5,3) NOT NULL DEFAULT 1.0,
    cefr_level              TEXT CHECK (cefr_level IN ('A1','A2','B1','B2','C1','C2')),
    attempt_count           INTEGER NOT NULL DEFAULT 0,
    correct_count           INTEGER NOT NULL DEFAULT 0,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    generation_batch_id     UUID,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_source_fk CHECK (
        (grammar_pattern_id IS NOT NULL)::INT +
        (word_sense_id IS NOT NULL)::INT +
        (corpus_collocation_id IS NOT NULL)::INT = 1
    )
);

CREATE INDEX IF NOT EXISTS idx_exercises_language     ON exercises(language_id);
CREATE INDEX IF NOT EXISTS idx_exercises_type         ON exercises(exercise_type);
CREATE INDEX IF NOT EXISTS idx_exercises_source       ON exercises(source_type);
CREATE INDEX IF NOT EXISTS idx_exercises_grammar      ON exercises(grammar_pattern_id) WHERE grammar_pattern_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_exercises_sense        ON exercises(word_sense_id) WHERE word_sense_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_exercises_collocation  ON exercises(corpus_collocation_id) WHERE corpus_collocation_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_exercises_cefr         ON exercises(cefr_level);
CREATE INDEX IF NOT EXISTS idx_exercises_active       ON exercises(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_exercises_tags_gin     ON exercises USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_exercises_content_gin  ON exercises USING GIN (content);

-- ==========================================================================
-- Task 0.3: exercise_attempts updates
-- ==========================================================================

ALTER TABLE exercise_attempts
    ADD COLUMN IF NOT EXISTS exercise_id UUID REFERENCES exercises(id);

CREATE INDEX IF NOT EXISTS idx_ea_exercise_id ON exercise_attempts(exercise_id);
CREATE INDEX IF NOT EXISTS idx_ea_user_response_gin ON exercise_attempts USING GIN (user_response);

-- ==========================================================================
-- Task 0.4: dim_languages extension
-- ==========================================================================

ALTER TABLE dim_languages
    ADD COLUMN IF NOT EXISTS exercise_model          TEXT,
    ADD COLUMN IF NOT EXISTS exercise_sentence_model TEXT;

UPDATE dim_languages SET
    exercise_model          = 'google/gemini-flash-1.5',
    exercise_sentence_model = 'google/gemini-flash-1.5'
WHERE id IN (1, 2, 3)
  AND exercise_model IS NULL;

-- ==========================================================================
-- Task 2.1: RPC for vocabulary mining
-- ==========================================================================

CREATE OR REPLACE FUNCTION tests_containing_sense(
    p_sense_id    INTEGER,
    p_language_id INTEGER
)
RETURNS TABLE (
    id              UUID,
    transcript      TEXT,
    difficulty      NUMERIC,
    vocab_token_map JSONB
)
LANGUAGE sql STABLE
AS $$
    SELECT t.id, t.transcript, t.difficulty, t.vocab_token_map
    FROM tests t
    JOIN dim_languages dl ON t.language = dl.code
    WHERE t.vocab_sense_ids @> ARRAY[p_sense_id]
      AND dl.id = p_language_id
      AND t.is_active = TRUE;
$$;

-- ==========================================================================
-- Task 5.8: RPC for verb-noun pair grid assembly
-- ==========================================================================

CREATE OR REPLACE FUNCTION get_verb_noun_pairs(
    p_corpus_source_id INTEGER,
    p_language_id      INTEGER,
    p_pmi_threshold    NUMERIC DEFAULT 3.0
)
RETURNS TABLE (verb_phrase TEXT, noun_phrase TEXT, combined_pmi NUMERIC)
LANGUAGE sql STABLE
AS $$
    SELECT DISTINCT
        split_part(cc.collocation_text, ' ', 1)   AS verb_phrase,
        split_part(cc.collocation_text, ' ', 2)   AS noun_phrase,
        cc.pmi_score                               AS combined_pmi
    FROM corpus_collocations cc
    WHERE cc.pos_pattern       = 'VERB+NOUN'
      AND cc.corpus_source_id  = p_corpus_source_id
      AND cc.language_id       = p_language_id
      AND cc.pmi_score        >= p_pmi_threshold
    ORDER BY combined_pmi DESC
    LIMIT 20;
$$;

-- ==========================================================================
-- Task 7.1: Analytics views
-- ==========================================================================

CREATE OR REPLACE VIEW vw_distractor_error_analysis AS
SELECT
    ea.user_id,
    e.tags->>'grammar_pattern'          AS pattern_code,
    ea.user_response->>'distractor_tag' AS error_type,
    COUNT(*)                             AS error_count,
    MIN(ea.created_at)                   AS first_seen,
    MAX(ea.created_at)                   AS last_seen
FROM exercise_attempts ea
JOIN exercises e ON ea.exercise_id = e.id
WHERE ea.is_correct = FALSE
  AND ea.user_response->>'distractor_tag' IS NOT NULL
  AND e.exercise_type = 'cloze_completion'
GROUP BY 1, 2, 3;

CREATE OR REPLACE VIEW vw_exercise_performance_by_type AS
SELECT
    e.exercise_type,
    e.cefr_level,
    e.language_id,
    COUNT(DISTINCT e.id)             AS exercise_count,
    COUNT(ea.id)                     AS total_attempts,
    SUM(ea.is_correct::INT)          AS correct_count,
    ROUND(
        SUM(ea.is_correct::INT)::NUMERIC / NULLIF(COUNT(ea.id), 0) * 100,
        1
    )                                AS accuracy_pct
FROM exercises e
LEFT JOIN exercise_attempts ea ON ea.exercise_id = e.id
WHERE e.is_active = TRUE
GROUP BY 1, 2, 3;

-- ==========================================================================
-- Task 8.1: Prompt templates
-- ==========================================================================

INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('exercise_sentence_generation', 1,
 'Generate {count} natural {cefr_level}-level sentences in the target language that demonstrate the following:
Pattern: {pattern_code}
Description: {description}
Example: {example_sentence}

Return a JSON array of objects: [{{"sentence": "...", "cefr_level": "{cefr_level}"}}]
Do not include translations. Sentences must be grammatically correct and contextually natural.')
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('vocab_sentence_generation', 1,
 'Generate {count} natural {cefr_level}-level sentences in the target language that use the following word naturally:
Word: {word}
Definition: {definition}

Return a JSON array of objects: [{{"sentence": "...", "cefr_level": "{cefr_level}"}}]
Each sentence must use "{word}" in context. Do not include translations. Sentences must be grammatically correct and contextually natural.')
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('collocation_sentence_generation', 1,
 'Generate {count} natural sentences in the target language that use the following collocation naturally:
Collocation: {collocation_text}
POS pattern: {pos_pattern}

Return a JSON array of objects: [{{"sentence": "...", "cefr_level": "B1"}}]
Each sentence must contain the collocation "{collocation_text}". Do not include translations. Sentences must be grammatically correct and contextually natural.')
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('cloze_distractor_generation', 1,
 'Sentence: {original_sentence}
Blank: {sentence_with_blank}
Correct answer: {correct_answer}
Learner level: {cefr_level}

Generate exactly 3 distractors. For each, assign a tag:
- "semantic": plausible in a different context but wrong here
- "form_error": wrong grammatical form or tense
- "learner_error": the most common mistake at {cefr_level}

Return JSON:
{{"distractors": ["word1","word2","word3"], "distractor_tags": {{"word1":"semantic","word2":"form_error","word3":"learner_error"}}, "explanation": "Brief explanation of correct answer."}}

Put the correct answer first in the options — do NOT shuffle.')
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('tl_nl_translation_generation', 1,
 'Sentence (target language): {tl_sentence}
Native language: {nl_language}

Generate:
1. One accurate {nl_language} translation of the sentence.
2. Two plausible-but-wrong {nl_language} translations (same general topic, different tense/aspect/meaning).

Return JSON:
{{"correct_nl": "...", "wrong_options": ["...", "..."]}}

The correct translation goes first — do NOT shuffle.')
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('nl_tl_translation_generation', 1,
 'Target language sentence: {tl_sentence}
Translate to native language ({nl_language}) and provide grading criteria for a production exercise.

Return JSON:
{{"nl_sentence": "...", "grading_notes": "Key requirements: e.g. must use present perfect continuous, duration marker required.", "acceptable_variants": ["...", "..."]}}')
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('spot_incorrect_generation', 1,
 'Here are three grammatically correct sentences:
1. {sentence_1}
2. {sentence_2}
3. {sentence_3}

Generate one grammatically INCORRECT sentence on the same topic, containing a realistic error a learner would make.
Also provide a parts breakdown identifying the exact error location.

Return JSON:
{{"incorrect_sentence": "...", "error_description": "...", "error_type": "e.g. subject_verb_agreement", "parts": [{{"text": "...", "is_error": false}}, {{"text": "...", "is_error": true, "correct_form": "...", "explanation": "..."}}]}}')
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('semantic_discrimination_generation', 1,
 'Word: {word}
Definition: {definition}
Level: {cefr_level}
Example context: {example_sentence}

Generate 4 sentences using "{word}":
- 1 correct, natural usage
- 3 plausible-but-wrong usages (wrong register, wrong collocation, wrong context)

Return JSON:
{{"sentences": [{{"text": "...", "is_correct": true}}, {{"text": "...", "is_correct": false}}, ...], "explanation": "..."}}

Put the correct sentence first.')
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('odd_one_out_generation', 1,
 'Anchor word: {word} (meaning: {definition})

Generate a group of 4 words/phrases:
- 3 that share a semantic property with "{word}" (e.g. all emotions, all cooking verbs, all formal register)
- 1 that does NOT share that property but is plausibly related

Return JSON:
{{"items": ["word1","word2","word3","odd_word"], "odd_item": "odd_word", "shared_property": "...", "explanation": "..."}}

Put the odd item last in items array.')
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('collocation_gap_fill_generation', 1,
 'Head word: {head_word}
Correct collocate: {collocate}
Sentence: {sentence}

Generate 3 distractor collocates — semantically plausible but unnatural with "{head_word}".

Return JSON:
{{"distractors": ["...", "...", "..."]}}

Do NOT shuffle — distractors are always placed after the correct answer by the application.')
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('collocation_repair_generation', 1,
 'Original sentence: {sentence}
Natural collocate: {collocate} (with head word: {head_word})

Replace "{collocate}" with an unnatural-but-plausible substitute. The resulting sentence should sound "almost right" to a learner.

Return JSON:
{{"sentence_with_error": "...", "error_word": "substitute word", "correct_word": "{collocate}", "explanation": "Why the substitute is unnatural."}}')
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('odd_collocation_out_generation', 1,
 'Head word: {head_word}
Known natural collocates: {natural_collocates}

Generate a group of 4 collocations for "{head_word}":
- 3 natural (including some from the known list)
- 1 that is unnatural but sounds plausible to a learner

Return JSON:
{{"collocations": ["natural1 {head_word}", "natural2 {head_word}", "natural3 {head_word}", "odd {head_word}"], "explanation": "..."}}

Odd item must be last in the array.')
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('context_spectrum_generation', 1,
 'Base sentence: {sentence}
Learner level: {cefr_level}

Generate 3-4 register variants of this sentence (informal -> formal spectrum).
Then create a brief exercise context (e.g. "You are writing a business email") that makes one variant clearly correct.

Return JSON:
{{"variants": ["most appropriate variant", "variant2", "variant3"], "exercise_context": "...", "correct_variant": "most appropriate variant"}}

The correct variant must be first in the variants array.')
ON CONFLICT DO NOTHING;
