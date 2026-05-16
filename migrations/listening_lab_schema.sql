-- ============================================================================
-- Listening Lab - Speed-Graded Listening Comprehension
-- ============================================================================
-- Idempotent: safe to re-run. Drops and recreates listening_lab_* tables.
-- Does NOT drop the questions.pool_source column on re-run (uses IF NOT EXISTS).
--
-- Adds the listening lab feature:
-- 1. New dim_test_types row for 'listening_lab'
-- 2. questions.pool_source column (marks original vs lab_expansion MCQs)
-- 3. listening_lab_passages table (one row per Lab-enrolled listening test)
-- 4. listening_lab_sessions table (per-user, per-passage active session state)
-- 5. RLS policies and grants
-- ============================================================================


-- ============================================================================
-- 0. DROP EXISTING OBJECTS (reverse dependency order)
-- ============================================================================

DROP TABLE IF EXISTS public.listening_lab_sessions CASCADE;
DROP TABLE IF EXISTS public.listening_lab_passages CASCADE;


-- ============================================================================
-- 1. NEW DIM_TEST_TYPES ROW
-- ============================================================================

INSERT INTO dim_test_types (type_code, type_name, description, category, requires_audio, is_active, display_order)
VALUES ('listening_lab', 'Listening Lab', 'Speed-graded listening comprehension (0.75x / 0.9x / 1.0x / 1.15x)', 'comprehension', true, true, 5)
ON CONFLICT (type_code) DO NOTHING;


-- ============================================================================
-- 2. QUESTIONS.POOL_SOURCE COLUMN
-- ============================================================================
-- Marks whether a question row is one of the original 5 served by the canonical
-- test, or a lab_expansion question generated during Listening Lab enrollment.
-- Existing test-serving paths do not filter on this column, so original
-- behavior is preserved (they continue to read all rows for a test_id).

ALTER TABLE public.questions
    ADD COLUMN IF NOT EXISTS pool_source text NOT NULL DEFAULT 'original';

ALTER TABLE public.questions
    DROP CONSTRAINT IF EXISTS chk_questions_pool_source;

ALTER TABLE public.questions
    ADD CONSTRAINT chk_questions_pool_source
    CHECK (pool_source IN ('original', 'lab_expansion'));

CREATE INDEX IF NOT EXISTS idx_questions_test_pool
    ON public.questions(test_id, pool_source);


-- ============================================================================
-- 3. LISTENING_LAB_PASSAGES TABLE
-- ============================================================================
-- One row per listening test that has been enrolled in Listening Lab.
-- Stores the 4 speed-variant audio URLs (pre-generated via Azure SSML) and
-- the voice frozen at enrollment time so re-runs stay consistent.

CREATE TABLE public.listening_lab_passages (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id         uuid NOT NULL UNIQUE REFERENCES public.tests(id),
    language_id     integer NOT NULL REFERENCES public.dim_languages(id),
    audio_url_075   text NOT NULL,
    audio_url_090   text NOT NULL,
    audio_url_100   text NOT NULL,
    audio_url_115   text NOT NULL,
    voice_id        text NOT NULL,
    pool_size       integer NOT NULL CHECK (pool_size >= 20),
    is_active       boolean DEFAULT false,
    enrolled_at     timestamptz DEFAULT now(),
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);

CREATE INDEX idx_lab_passages_language_active
    ON public.listening_lab_passages(language_id)
    WHERE is_active = true;

CREATE INDEX idx_lab_passages_test ON public.listening_lab_passages(test_id);


-- ============================================================================
-- 4. LISTENING_LAB_SESSIONS TABLE
-- ============================================================================
-- Per-user, per-passage session state. current_tier ranges 0..3 while active
-- (0 = 0.75x, 1 = 0.9x, 2 = 1.0x, 3 = 1.15x), and equals 4 once all tiers are
-- complete. tier_results holds the full attempt log shape:
--   {"0": {"attempts": [{"score": 3, "at": "..."}, ...], "passed_at": "..."}}

CREATE TABLE public.listening_lab_sessions (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             uuid NOT NULL REFERENCES public.users(id),
    passage_id          uuid NOT NULL REFERENCES public.listening_lab_passages(id),
    test_id             uuid NOT NULL REFERENCES public.tests(id),
    language_id         integer NOT NULL REFERENCES public.dim_languages(id),
    current_tier        smallint NOT NULL DEFAULT 0 CHECK (current_tier BETWEEN 0 AND 4),
    tiers_passed        smallint[] NOT NULL DEFAULT '{}',
    seen_question_ids   uuid[] NOT NULL DEFAULT '{}',
    active_question_ids uuid[] NOT NULL DEFAULT '{}',
    tier_results        jsonb NOT NULL DEFAULT '{}',
    tokens_consumed     integer NOT NULL DEFAULT 0 CHECK (tokens_consumed >= 0),
    final_attempt_id    uuid REFERENCES public.test_attempts(id),
    started_at          timestamptz DEFAULT now(),
    updated_at          timestamptz DEFAULT now(),
    completed_at        timestamptz,
    abandoned_at        timestamptz
);

CREATE INDEX idx_lab_sessions_user
    ON public.listening_lab_sessions(user_id, completed_at);

CREATE INDEX idx_lab_sessions_passage
    ON public.listening_lab_sessions(passage_id);

CREATE UNIQUE INDEX idx_lab_sessions_one_active_per_user_passage
    ON public.listening_lab_sessions(user_id, passage_id)
    WHERE completed_at IS NULL AND abandoned_at IS NULL;


-- ============================================================================
-- 5. RLS POLICIES
-- ============================================================================

ALTER TABLE public.listening_lab_passages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "read_active_lab_passages" ON public.listening_lab_passages
    FOR SELECT USING (is_active = true);
CREATE POLICY "service_insert_lab_passages" ON public.listening_lab_passages
    FOR INSERT WITH CHECK (true);
CREATE POLICY "service_update_lab_passages" ON public.listening_lab_passages
    FOR UPDATE USING (true);

ALTER TABLE public.listening_lab_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "manage_own_lab_sessions" ON public.listening_lab_sessions
    FOR ALL USING (auth.uid() = user_id);


-- ============================================================================
-- 6. GRANTS
-- ============================================================================

GRANT SELECT ON public.listening_lab_passages TO authenticated;
GRANT ALL    ON public.listening_lab_sessions TO authenticated;
