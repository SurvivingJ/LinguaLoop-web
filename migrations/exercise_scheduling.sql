-- ============================================================
-- Exercise Scheduling: session cache, user preferences, attempt denormalization
-- ============================================================

-- 1. Single-row-per-user session cache (upserted, never grows)
CREATE TABLE IF NOT EXISTS public.user_exercise_sessions (
    user_id         uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    language_id     integer NOT NULL,
    load_date       date NOT NULL DEFAULT CURRENT_DATE,
    exercise_ids    jsonb NOT NULL,          -- [{exercise_id, sense_id, exercise_type, slot_type, phase}]
    completed_ids   jsonb DEFAULT '[]',      -- [exercise_id, ...]
    session_size    integer NOT NULL,
    created_at      timestamptz DEFAULT now(),
    PRIMARY KEY (user_id, language_id)
);

ALTER TABLE public.user_exercise_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own sessions"
    ON public.user_exercise_sessions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users update own sessions"
    ON public.user_exercise_sessions FOR UPDATE
    USING (auth.uid() = user_id);


-- 2. User exercise preferences (session size, extensible later)
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS exercise_preferences jsonb DEFAULT '{"session_size": 20}';


-- 3. Denormalize exercise_attempts for fast anti-repetition lookups
ALTER TABLE public.exercise_attempts
    ADD COLUMN IF NOT EXISTS exercise_type text,
    ADD COLUMN IF NOT EXISTS sense_id integer;

CREATE INDEX IF NOT EXISTS idx_ea_user_created
    ON public.exercise_attempts(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ea_user_sense_type
    ON public.exercise_attempts(user_id, sense_id, exercise_type, created_at DESC);
