-- ============================================================================
-- Murder Mystery Comprehension Mode - Tables, RLS, and Seed Data
-- ============================================================================
-- Idempotent: safe to re-run. Drops and recreates all mystery objects.
--
-- Adds the murder mystery series feature:
-- 1. New dim_test_types row for 'mystery'
-- 2. mysteries table (parallel to tests)
-- 3. mystery_scenes table (5 scenes per mystery)
-- 4. mystery_questions table (MCQs per scene)
-- 5. mystery_progress table (per-user progress tracking)
-- 6. mystery_skill_ratings table (per-mystery ELO)
-- 7. mystery_attempts table (completed mystery records)
-- 8. RLS policies
-- ============================================================================


-- ============================================================================
-- 0. DROP EXISTING OBJECTS (reverse dependency order)
-- ============================================================================

DROP TABLE IF EXISTS public.mystery_attempts CASCADE;
DROP TABLE IF EXISTS public.mystery_skill_ratings CASCADE;
DROP TABLE IF EXISTS public.mystery_progress CASCADE;
DROP TABLE IF EXISTS public.mystery_questions CASCADE;
DROP TABLE IF EXISTS public.mystery_scenes CASCADE;
DROP TABLE IF EXISTS public.mysteries CASCADE;


-- ============================================================================
-- 1. NEW DIM_TEST_TYPES ROW
-- ============================================================================

INSERT INTO dim_test_types (type_code, type_name, description, category, requires_audio, is_active, display_order)
VALUES ('mystery', 'Mystery', 'Murder mystery comprehension series', 'comprehension', false, true, 4)
ON CONFLICT (type_code) DO NOTHING;


-- ============================================================================
-- 2. MYSTERIES TABLE
-- ============================================================================

CREATE TABLE public.mysteries (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug                text NOT NULL UNIQUE,
    language_id         integer NOT NULL REFERENCES public.dim_languages(id),
    difficulty          integer NOT NULL CHECK (difficulty BETWEEN 1 AND 9),
    title               text NOT NULL,
    premise             text NOT NULL,
    suspects            jsonb NOT NULL DEFAULT '[]',
    solution_suspect    text NOT NULL,
    solution_reasoning  text NOT NULL,
    archetype           text,
    target_vocab_ids    integer[] DEFAULT '{}',
    vocab_sense_ids     integer[] DEFAULT '{}',
    generation_model    text DEFAULT 'gpt-4',
    gen_user            uuid NOT NULL REFERENCES public.users(id),
    is_active           boolean DEFAULT true,
    total_attempts      integer DEFAULT 0,
    created_at          timestamptz DEFAULT now(),
    updated_at          timestamptz DEFAULT now()
);

CREATE INDEX idx_mysteries_language ON mysteries(language_id);
CREATE INDEX idx_mysteries_difficulty ON mysteries(difficulty);
CREATE INDEX idx_mysteries_active ON mysteries(is_active) WHERE is_active = true;


-- ============================================================================
-- 3. MYSTERY_SCENES TABLE
-- ============================================================================

CREATE TABLE public.mystery_scenes (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mystery_id      uuid NOT NULL REFERENCES public.mysteries(id) ON DELETE CASCADE,
    scene_number    integer NOT NULL CHECK (scene_number BETWEEN 1 AND 5),
    title           text NOT NULL,
    transcript      text NOT NULL,
    audio_url       text,
    clue_text       text NOT NULL,
    clue_type       text DEFAULT 'evidence',
    is_finale       boolean DEFAULT false,
    target_words    jsonb,
    created_at      timestamptz DEFAULT now(),
    UNIQUE (mystery_id, scene_number)
);

CREATE INDEX idx_mystery_scenes_mystery ON mystery_scenes(mystery_id);


-- ============================================================================
-- 4. MYSTERY_QUESTIONS TABLE
-- ============================================================================

CREATE TABLE public.mystery_questions (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scene_id            uuid NOT NULL REFERENCES public.mystery_scenes(id) ON DELETE CASCADE,
    question_text       text NOT NULL,
    choices             jsonb NOT NULL,
    answer              jsonb NOT NULL,
    answer_explanation  text,
    question_type_id    integer REFERENCES public.dim_question_types(id),
    sense_ids           integer[],
    is_deduction        boolean DEFAULT false,
    created_at          timestamptz DEFAULT now()
);

CREATE INDEX idx_mystery_questions_scene ON mystery_questions(scene_id);


-- ============================================================================
-- 5. MYSTERY_PROGRESS TABLE
-- ============================================================================

CREATE TABLE public.mystery_progress (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES public.users(id),
    mystery_id      uuid NOT NULL REFERENCES public.mysteries(id),
    current_scene   integer NOT NULL DEFAULT 1,
    scene_responses jsonb DEFAULT '{}',
    notebook_state  jsonb DEFAULT '{"suspects": [], "clues": []}',
    mode            text NOT NULL DEFAULT 'reading' CHECK (mode IN ('reading', 'listening')),
    started_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now(),
    completed_at    timestamptz,
    UNIQUE (user_id, mystery_id)
);

CREATE INDEX idx_mystery_progress_user ON mystery_progress(user_id);


-- ============================================================================
-- 6. MYSTERY_SKILL_RATINGS TABLE
-- ============================================================================

CREATE TABLE public.mystery_skill_ratings (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mystery_id      uuid NOT NULL REFERENCES public.mysteries(id) UNIQUE,
    elo_rating      integer DEFAULT 1400 CHECK (elo_rating BETWEEN 400 AND 3000),
    volatility      numeric DEFAULT 1.0,
    total_attempts  integer DEFAULT 0,
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);


-- ============================================================================
-- 7. MYSTERY_ATTEMPTS TABLE
-- ============================================================================
-- Parallel to test_attempts but references mysteries instead of tests.

CREATE TABLE public.mystery_attempts (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             uuid NOT NULL REFERENCES public.users(id),
    mystery_id          uuid NOT NULL REFERENCES public.mysteries(id),
    score               integer NOT NULL CHECK (score >= 0),
    total_questions     integer NOT NULL CHECK (total_questions > 0),
    percentage          real GENERATED ALWAYS AS ((score::real / total_questions::real) * 100) STORED,
    user_elo_before     integer NOT NULL,
    user_elo_after      integer NOT NULL,
    mystery_elo_before  integer NOT NULL,
    mystery_elo_after   integer NOT NULL,
    language_id         integer NOT NULL REFERENCES public.dim_languages(id),
    test_type_id        integer NOT NULL REFERENCES public.dim_test_types(id),
    attempt_number      integer DEFAULT 1,
    is_first_attempt    boolean DEFAULT true,
    idempotency_key     uuid,
    created_at          timestamptz DEFAULT now()
);

CREATE INDEX idx_mystery_attempts_user ON mystery_attempts(user_id);
CREATE INDEX idx_mystery_attempts_mystery ON mystery_attempts(mystery_id);


-- ============================================================================
-- 8. RLS POLICIES
-- ============================================================================

ALTER TABLE mysteries ENABLE ROW LEVEL SECURITY;
CREATE POLICY "read_active_mysteries" ON mysteries
    FOR SELECT USING (is_active = true);
CREATE POLICY "service_insert_mysteries" ON mysteries
    FOR INSERT WITH CHECK (true);
CREATE POLICY "service_update_mysteries" ON mysteries
    FOR UPDATE USING (true);

ALTER TABLE mystery_scenes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "read_scenes" ON mystery_scenes
    FOR SELECT USING (true);
CREATE POLICY "service_insert_scenes" ON mystery_scenes
    FOR INSERT WITH CHECK (true);

ALTER TABLE mystery_questions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "read_questions" ON mystery_questions
    FOR SELECT USING (true);
CREATE POLICY "service_insert_questions" ON mystery_questions
    FOR INSERT WITH CHECK (true);

ALTER TABLE mystery_progress ENABLE ROW LEVEL SECURITY;
CREATE POLICY "manage_own_progress" ON mystery_progress
    FOR ALL USING (auth.uid() = user_id);

ALTER TABLE mystery_skill_ratings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "read_mystery_ratings" ON mystery_skill_ratings
    FOR SELECT USING (true);
CREATE POLICY "service_manage_mystery_ratings" ON mystery_skill_ratings
    FOR ALL USING (true);

ALTER TABLE mystery_attempts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "read_own_mystery_attempts" ON mystery_attempts
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "service_insert_mystery_attempts" ON mystery_attempts
    FOR INSERT WITH CHECK (true);

-- Grant necessary permissions
GRANT SELECT ON mysteries TO authenticated;
GRANT SELECT ON mystery_scenes TO authenticated;
GRANT SELECT ON mystery_questions TO authenticated;
GRANT ALL ON mystery_progress TO authenticated;
GRANT SELECT ON mystery_skill_ratings TO authenticated;
GRANT SELECT ON mystery_attempts TO authenticated;
