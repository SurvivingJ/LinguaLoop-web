-- ============================================================
-- BKT Vocabulary Tracking, Word Quiz, and SRS Flashcards
-- ============================================================

-- 1. Per-word BKT knowledge state
CREATE TABLE IF NOT EXISTS public.user_vocabulary_knowledge (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.users(id),
    sense_id INTEGER NOT NULL REFERENCES public.dim_word_senses(id),
    language_id SMALLINT NOT NULL REFERENCES public.dim_languages(id),

    -- BKT state
    p_known NUMERIC(5,4) NOT NULL DEFAULT 0.10,
    status TEXT NOT NULL DEFAULT 'unknown'
        CHECK (status IN ('unknown','encountered','learning','probably_known','known','user_marked_unknown')),

    -- Evidence counters
    evidence_count INTEGER DEFAULT 0,
    comprehension_correct INTEGER DEFAULT 0,
    comprehension_wrong INTEGER DEFAULT 0,
    word_test_correct INTEGER DEFAULT 0,
    word_test_wrong INTEGER DEFAULT 0,

    -- Timestamps
    last_evidence_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, sense_id)
);

CREATE INDEX IF NOT EXISTS idx_uvk_user_language ON user_vocabulary_knowledge(user_id, language_id);
CREATE INDEX IF NOT EXISTS idx_uvk_user_status ON user_vocabulary_knowledge(user_id, status);
CREATE INDEX IF NOT EXISTS idx_uvk_user_pknown ON user_vocabulary_knowledge(user_id, p_known);


-- 2. Add sense_ids to questions
ALTER TABLE public.questions ADD COLUMN IF NOT EXISTS sense_ids INTEGER[];


-- 3. SRS flashcard state
CREATE TABLE IF NOT EXISTS public.user_flashcards (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.users(id),
    sense_id INTEGER NOT NULL REFERENCES public.dim_word_senses(id),
    language_id SMALLINT NOT NULL REFERENCES public.dim_languages(id),

    -- FSRS scheduling state
    stability REAL DEFAULT 0,
    difficulty REAL DEFAULT 0.3,
    due_date DATE,
    last_review TIMESTAMPTZ,
    reps INTEGER DEFAULT 0,
    lapses INTEGER DEFAULT 0,
    state TEXT DEFAULT 'new'
        CHECK (state IN ('new','learning','review','relearning')),

    -- Card content (cached at creation)
    example_sentence TEXT,
    audio_url TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, sense_id)
);

CREATE INDEX IF NOT EXISTS idx_uf_user_due ON user_flashcards(user_id, language_id, due_date);
CREATE INDEX IF NOT EXISTS idx_uf_user_state ON user_flashcards(user_id, state);


-- 4. Word quiz results
CREATE TABLE IF NOT EXISTS public.word_quiz_results (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.users(id),
    attempt_id UUID REFERENCES public.test_attempts(id),
    sense_id INTEGER NOT NULL REFERENCES public.dim_word_senses(id),
    is_correct BOOLEAN NOT NULL,
    selected_answer TEXT,
    correct_answer TEXT,
    response_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wqr_user ON word_quiz_results(user_id);
CREATE INDEX IF NOT EXISTS idx_wqr_attempt ON word_quiz_results(attempt_id);


-- 5. Add level_tag to dim_vocabulary for HSK/JLPT imports
ALTER TABLE public.dim_vocabulary ADD COLUMN IF NOT EXISTS level_tag TEXT;
CREATE INDEX IF NOT EXISTS idx_dv_level_tag ON dim_vocabulary(level_tag);


-- ============================================================
-- BKT FUNCTIONS
-- ============================================================

-- Core BKT update (immutable, reusable)
CREATE OR REPLACE FUNCTION bkt_update(
    p_current NUMERIC,
    p_correct BOOLEAN,
    p_slip NUMERIC DEFAULT 0.10,
    p_guess NUMERIC DEFAULT 0.25
)
RETURNS NUMERIC AS $$
DECLARE
    p_obs_knows NUMERIC;
    p_obs_not_knows NUMERIC;
BEGIN
    IF p_correct THEN
        p_obs_knows := 1 - p_slip;
        p_obs_not_knows := p_guess;
    ELSE
        p_obs_knows := p_slip;
        p_obs_not_knows := 1 - p_guess;
    END IF;

    RETURN GREATEST(0.02, LEAST(0.98,
        (p_obs_knows * p_current) /
        (p_obs_knows * p_current + p_obs_not_knows * (1 - p_current))
    ));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Comprehension test update (weak signal)
CREATE OR REPLACE FUNCTION bkt_update_comprehension(
    p_current NUMERIC,
    p_correct BOOLEAN
)
RETURNS NUMERIC AS $$
BEGIN
    RETURN bkt_update(p_current, p_correct, 0.10, 0.25);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Word test update (strong signal)
CREATE OR REPLACE FUNCTION bkt_update_word_test(
    p_current NUMERIC,
    p_correct BOOLEAN
)
RETURNS NUMERIC AS $$
BEGIN
    RETURN bkt_update(p_current, p_correct, 0.05, 0.25);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Derive status from p_known
CREATE OR REPLACE FUNCTION bkt_status(p_known NUMERIC)
RETURNS TEXT AS $$
BEGIN
    RETURN CASE
        WHEN p_known < 0.20 THEN 'unknown'
        WHEN p_known < 0.50 THEN 'encountered'
        WHEN p_known < 0.75 THEN 'learning'
        WHEN p_known < 0.90 THEN 'probably_known'
        ELSE 'known'
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;


-- ============================================================
-- MAIN BKT UPDATE FUNCTION (called after test submission)
-- ============================================================

CREATE OR REPLACE FUNCTION update_vocabulary_from_test(
    p_user_id UUID,
    p_language_id SMALLINT,
    p_question_results JSONB  -- [{question_id, is_correct}]
)
RETURNS TABLE(
    out_sense_id INTEGER,
    out_p_known_before NUMERIC,
    out_p_known_after NUMERIC,
    out_status TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH question_senses AS (
        SELECT
            unnest(q.sense_ids) AS sense_id,
            (qr->>'is_correct')::boolean AS is_correct
        FROM jsonb_array_elements(p_question_results) qr
        JOIN questions q ON q.id = (qr->>'question_id')::uuid
        WHERE q.sense_ids IS NOT NULL
          AND array_length(q.sense_ids, 1) > 0
    ),
    deduped AS (
        SELECT qs.sense_id, bool_or(qs.is_correct) AS is_correct
        FROM question_senses qs
        GROUP BY qs.sense_id
    ),
    current_state AS (
        SELECT
            d.sense_id,
            d.is_correct,
            COALESCE(
                uvk.p_known,
                CASE
                    WHEN dv.frequency_rank IS NULL THEN 0.10
                    WHEN dv.frequency_rank >= 6.0 THEN 0.85
                    WHEN dv.frequency_rank >= 5.0 THEN 0.65
                    WHEN dv.frequency_rank >= 4.0 THEN 0.35
                    WHEN dv.frequency_rank >= 3.0 THEN 0.15
                    ELSE 0.05
                END
            ) AS p_current
        FROM deduped d
        JOIN dim_word_senses dws ON dws.id = d.sense_id
        JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
        LEFT JOIN user_vocabulary_knowledge uvk
            ON uvk.user_id = p_user_id AND uvk.sense_id = d.sense_id
    ),
    updated AS (
        SELECT
            cs.sense_id,
            cs.p_current AS p_before,
            bkt_update_comprehension(cs.p_current, cs.is_correct) AS p_after,
            cs.is_correct
        FROM current_state cs
    ),
    upserted AS (
        INSERT INTO user_vocabulary_knowledge
            (user_id, sense_id, language_id, p_known, status,
             evidence_count, comprehension_correct, comprehension_wrong,
             last_evidence_at, updated_at)
        SELECT
            p_user_id, u.sense_id, p_language_id,
            u.p_after, bkt_status(u.p_after),
            1,
            CASE WHEN u.is_correct THEN 1 ELSE 0 END,
            CASE WHEN u.is_correct THEN 0 ELSE 1 END,
            NOW(), NOW()
        FROM updated u
        ON CONFLICT (user_id, sense_id) DO UPDATE SET
            p_known = EXCLUDED.p_known,
            status = CASE
                WHEN user_vocabulary_knowledge.status = 'user_marked_unknown'
                THEN 'user_marked_unknown'
                ELSE EXCLUDED.status
            END,
            evidence_count = user_vocabulary_knowledge.evidence_count + 1,
            comprehension_correct = user_vocabulary_knowledge.comprehension_correct + EXCLUDED.comprehension_correct,
            comprehension_wrong = user_vocabulary_knowledge.comprehension_wrong + EXCLUDED.comprehension_wrong,
            last_evidence_at = NOW(),
            updated_at = NOW()
        RETURNING sense_id, p_known, status
    )
    SELECT
        upserted.sense_id,
        COALESCE(u.p_before, 0.10),
        upserted.p_known,
        upserted.status
    FROM upserted
    LEFT JOIN updated u ON u.sense_id = upserted.sense_id;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- WORD TEST BKT UPDATE (called after word quiz)
-- ============================================================

CREATE OR REPLACE FUNCTION update_vocabulary_from_word_test(
    p_user_id UUID,
    p_sense_id INTEGER,
    p_is_correct BOOLEAN,
    p_language_id SMALLINT
)
RETURNS TABLE(
    out_sense_id INTEGER,
    out_p_known_before NUMERIC,
    out_p_known_after NUMERIC,
    out_status TEXT
) AS $$
DECLARE
    v_p_current NUMERIC;
    v_p_new NUMERIC;
    v_status TEXT;
BEGIN
    -- Get current p_known or compute prior
    SELECT COALESCE(uvk.p_known,
        CASE
            WHEN dv.frequency_rank IS NULL THEN 0.10
            WHEN dv.frequency_rank >= 6.0 THEN 0.85
            WHEN dv.frequency_rank >= 5.0 THEN 0.65
            WHEN dv.frequency_rank >= 4.0 THEN 0.35
            WHEN dv.frequency_rank >= 3.0 THEN 0.15
            ELSE 0.05
        END
    ) INTO v_p_current
    FROM dim_word_senses dws
    JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
    LEFT JOIN user_vocabulary_knowledge uvk
        ON uvk.user_id = p_user_id AND uvk.sense_id = p_sense_id
    WHERE dws.id = p_sense_id;

    IF v_p_current IS NULL THEN
        v_p_current := 0.10;
    END IF;

    v_p_new := bkt_update_word_test(v_p_current, p_is_correct);
    v_status := bkt_status(v_p_new);

    INSERT INTO user_vocabulary_knowledge
        (user_id, sense_id, language_id, p_known, status,
         evidence_count, word_test_correct, word_test_wrong,
         last_evidence_at, updated_at)
    VALUES (
        p_user_id, p_sense_id, p_language_id,
        v_p_new, v_status,
        1,
        CASE WHEN p_is_correct THEN 1 ELSE 0 END,
        CASE WHEN p_is_correct THEN 0 ELSE 1 END,
        NOW(), NOW()
    )
    ON CONFLICT (user_id, sense_id) DO UPDATE SET
        p_known = EXCLUDED.p_known,
        status = CASE
            WHEN user_vocabulary_knowledge.status = 'user_marked_unknown'
            THEN 'user_marked_unknown'
            ELSE EXCLUDED.status
        END,
        evidence_count = user_vocabulary_knowledge.evidence_count + 1,
        word_test_correct = user_vocabulary_knowledge.word_test_correct + EXCLUDED.word_test_correct,
        word_test_wrong = user_vocabulary_knowledge.word_test_wrong + EXCLUDED.word_test_wrong,
        last_evidence_at = NOW(),
        updated_at = NOW();

    RETURN QUERY SELECT p_sense_id, v_p_current, v_p_new, v_status;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- WORD QUIZ CANDIDATE SELECTION
-- ============================================================

CREATE OR REPLACE FUNCTION get_word_quiz_candidates(
    p_user_id UUID,
    p_sense_ids INTEGER[],
    p_language_id SMALLINT,
    p_max_words INTEGER DEFAULT 5
)
RETURNS TABLE(
    out_sense_id INTEGER,
    out_lemma TEXT,
    out_definition TEXT,
    out_pronunciation TEXT,
    out_p_known NUMERIC,
    out_score NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        uvk.sense_id,
        dv.lemma,
        dws.definition,
        dws.pronunciation,
        uvk.p_known,
        (uvk.p_known * (1 - uvk.p_known) *
         (1.0 / GREATEST(1.0, ln(GREATEST(1.0, COALESCE(dv.frequency_rank, 1.0)::numeric))))
        ) AS score
    FROM user_vocabulary_knowledge uvk
    JOIN dim_word_senses dws ON dws.id = uvk.sense_id
    JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
    WHERE uvk.user_id = p_user_id
      AND uvk.sense_id = ANY(p_sense_ids)
      AND uvk.p_known BETWEEN 0.25 AND 0.75
      AND uvk.status != 'user_marked_unknown'
    ORDER BY score DESC
    LIMIT p_max_words;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- DISTRACTOR GENERATION
-- ============================================================

CREATE OR REPLACE FUNCTION get_distractors(
    p_sense_id INTEGER,
    p_language_id SMALLINT,
    p_count INTEGER DEFAULT 3
)
RETURNS TABLE(out_definition TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT dws.definition
    FROM dim_word_senses dws
    JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
    WHERE dv.language_id = p_language_id
      AND dws.id != p_sense_id
      AND dws.vocab_id != (SELECT vocab_id FROM dim_word_senses WHERE id = p_sense_id)
      AND dws.sense_rank = 1
    ORDER BY random()
    LIMIT p_count;
END;
$$ LANGUAGE plpgsql;
