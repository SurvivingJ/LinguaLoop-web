-- ============================================================================
-- Phase 4: Schema Evolution
-- Date: 2026-04-12
--
-- 4.1 Extend user_word_ladder for promotion/demotion tracking
-- 4.2 Create user_exercise_history anti-repetition table
-- 4.3 Normalize dim_languages model columns -> language_model_config
-- 4.4 Junction table for daily_test_loads test IDs
-- ============================================================================


-- ============================================================================
-- 4.1 Extend user_word_ladder with missing tracking columns
-- ============================================================================
-- Wiki spec describes promotion/demotion needing success/failure counters,
-- word state, and review scheduling. Current table only has
-- (user_id, sense_id, current_level, active_levels, updated_at).
-- These columns enable: promote after 2 cross-session successes,
-- demote after 3 consecutive first-attempt failures.

ALTER TABLE public.user_word_ladder
    ADD COLUMN IF NOT EXISTS first_try_success_count integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS first_try_failure_count integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS consecutive_failures integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_attempts integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS word_state text NOT NULL DEFAULT 'active'
        CHECK (word_state IN ('new', 'active', 'fragile', 'stable', 'mastered')),
    ADD COLUMN IF NOT EXISTS last_success_session_date date,
    ADD COLUMN IF NOT EXISTS review_due_at timestamptz;

-- Index for session-building: find words due for review
CREATE INDEX IF NOT EXISTS idx_user_word_ladder_review_due
    ON public.user_word_ladder(user_id, review_due_at)
    WHERE review_due_at IS NOT NULL;

-- Index for finding words by state
CREATE INDEX IF NOT EXISTS idx_user_word_ladder_state
    ON public.user_word_ladder(user_id, word_state);


-- ============================================================================
-- 4.2 Create user_exercise_history table
-- ============================================================================
-- Dedicated anti-repetition table. Replaces the current pattern of scanning
-- 500 rows from exercise_attempts per session build. Purpose-built indexes
-- for the specific lookups the session builder needs.

CREATE TABLE IF NOT EXISTS public.user_exercise_history (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    language_id     smallint NOT NULL REFERENCES public.dim_languages(id),
    exercise_id     uuid NOT NULL REFERENCES public.exercises(id),
    sense_id        integer REFERENCES public.dim_word_senses(id),
    exercise_type   text NOT NULL,
    is_correct      boolean NOT NULL,
    is_first_attempt boolean NOT NULL DEFAULT true,
    session_date    date NOT NULL DEFAULT CURRENT_DATE,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- Primary lookup: anti-repetition (filter by session_date at query time)
CREATE INDEX IF NOT EXISTS idx_ueh_anti_repeat
    ON public.user_exercise_history(user_id, language_id, session_date, exercise_id);

-- Session building: recent exercises by user+language+date
CREATE INDEX IF NOT EXISTS idx_ueh_user_lang_date
    ON public.user_exercise_history(user_id, language_id, session_date DESC);

-- Per-sense history for ladder/BKT queries
CREATE INDEX IF NOT EXISTS idx_ueh_user_sense
    ON public.user_exercise_history(user_id, sense_id, created_at DESC);

-- RLS
ALTER TABLE public.user_exercise_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own exercise history"
    ON public.user_exercise_history
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role full access on exercise history"
    ON public.user_exercise_history
    FOR ALL
    USING (auth.role() = 'service_role');

-- Auto-populate trigger: copy from exercise_attempts on INSERT
CREATE OR REPLACE FUNCTION public.sync_exercise_history()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    INSERT INTO public.user_exercise_history (
        user_id, language_id, exercise_id, sense_id,
        exercise_type, is_correct, is_first_attempt, session_date
    )
    SELECT
        NEW.user_id,
        e.language_id,
        NEW.exercise_id,
        NEW.sense_id,
        NEW.exercise_type,
        NEW.is_correct,
        COALESCE(NEW.is_first_attempt, true),
        CURRENT_DATE
    FROM exercises e
    WHERE e.id = NEW.exercise_id;

    RETURN NEW;
EXCEPTION WHEN OTHERS THEN
    -- Don't block the main insert if history sync fails
    RAISE WARNING 'sync_exercise_history failed: %', SQLERRM;
    RETURN NEW;
END;
$function$;

CREATE TRIGGER trigger_sync_exercise_history
    AFTER INSERT ON public.exercise_attempts
    FOR EACH ROW
    EXECUTE FUNCTION public.sync_exercise_history();

-- Backfill from existing exercise_attempts data
-- (Run manually after deploying; may take a few seconds on large datasets)
-- INSERT INTO user_exercise_history (
--     user_id, language_id, exercise_id, sense_id,
--     exercise_type, is_correct, is_first_attempt, session_date, created_at
-- )
-- SELECT
--     ea.user_id, e.language_id, ea.exercise_id, ea.sense_id,
--     ea.exercise_type, ea.is_correct,
--     COALESCE(ea.is_first_attempt, true),
--     ea.created_at::date, ea.created_at
-- FROM exercise_attempts ea
-- JOIN exercises e ON e.id = ea.exercise_id
-- ON CONFLICT DO NOTHING;


-- ============================================================================
-- 4.3 Normalize dim_languages model columns -> language_model_config
-- ============================================================================
-- dim_languages has 8+ model columns growing unboundedly. A key-value
-- config table is the standard normalization for this pattern.
-- Old columns are NOT dropped here — they will be deprecated after all
-- Python callers migrate to the new table.

CREATE TABLE IF NOT EXISTS public.language_model_config (
    id              integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    language_id     smallint NOT NULL REFERENCES public.dim_languages(id),
    task_key        text NOT NULL,
    model_name      text NOT NULL,
    is_active       boolean NOT NULL DEFAULT true,
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now(),
    UNIQUE (language_id, task_key)
);

CREATE INDEX IF NOT EXISTS idx_lmc_language
    ON public.language_model_config(language_id);

CREATE INDEX IF NOT EXISTS idx_lmc_task
    ON public.language_model_config(task_key, language_id)
    WHERE is_active = true;

-- Migrate existing model data from dim_languages
INSERT INTO public.language_model_config (language_id, task_key, model_name)
SELECT id, 'prose', prose_model FROM dim_languages WHERE prose_model IS NOT NULL
UNION ALL
SELECT id, 'question', question_model FROM dim_languages WHERE question_model IS NOT NULL
UNION ALL
SELECT id, 'exercise', exercise_model FROM dim_languages WHERE exercise_model IS NOT NULL
UNION ALL
SELECT id, 'exercise_sentence', exercise_sentence_model FROM dim_languages WHERE exercise_sentence_model IS NOT NULL
UNION ALL
SELECT id, 'conversation', conversation_model FROM dim_languages WHERE conversation_model IS NOT NULL
UNION ALL
SELECT id, 'vocab_prompt1', vocab_prompt1_model FROM dim_languages WHERE vocab_prompt1_model IS NOT NULL
UNION ALL
SELECT id, 'vocab_prompt2', vocab_prompt2_model FROM dim_languages WHERE vocab_prompt2_model IS NOT NULL
UNION ALL
SELECT id, 'vocab_prompt3', vocab_prompt3_model FROM dim_languages WHERE vocab_prompt3_model IS NOT NULL
ON CONFLICT (language_id, task_key) DO NOTHING;

-- Helper function to look up a model by task key with language fallback
CREATE OR REPLACE FUNCTION public.get_model_for_task(
    p_task_key text,
    p_language_id smallint
)
RETURNS text
LANGUAGE plpgsql
STABLE
AS $function$
DECLARE
    v_model text;
BEGIN
    SELECT model_name INTO v_model
    FROM language_model_config
    WHERE task_key = p_task_key
      AND language_id = p_language_id
      AND is_active = true
    LIMIT 1;

    RETURN v_model;
END;
$function$;

-- NOTE: Old columns on dim_languages are intentionally NOT dropped yet.
-- They will be removed in a future migration after all Python callers
-- are migrated to use language_model_config / get_model_for_task().
-- Columns to deprecate later:
--   prose_model, question_model, exercise_model, exercise_sentence_model,
--   conversation_model, vocab_prompt1_model, vocab_prompt2_model, vocab_prompt3_model


-- ============================================================================
-- 4.4 Junction table for daily_test_loads
-- ============================================================================
-- Replace JSONB arrays (test_ids, completed_test_ids) with a proper
-- junction table. Adds FK integrity on stored test IDs.

CREATE TABLE IF NOT EXISTS public.daily_test_load_items (
    load_id         bigint NOT NULL,
    test_id         uuid NOT NULL REFERENCES public.tests(id),
    is_completed    boolean NOT NULL DEFAULT false,
    completed_at    timestamptz,
    display_order   integer NOT NULL DEFAULT 0,
    PRIMARY KEY (load_id, test_id)
);

-- FK to daily_test_loads (add after table exists)
ALTER TABLE public.daily_test_load_items
    ADD CONSTRAINT daily_test_load_items_load_id_fkey
    FOREIGN KEY (load_id) REFERENCES public.daily_test_loads(id)
    ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_dtli_load
    ON public.daily_test_load_items(load_id);

CREATE INDEX IF NOT EXISTS idx_dtli_test
    ON public.daily_test_load_items(test_id);

-- RLS matching daily_test_loads pattern
-- (daily_test_loads has RLS disabled; items follow same pattern)

-- NOTE: JSONB columns on daily_test_loads (test_ids, completed_test_ids)
-- are NOT dropped yet. They will be removed after Python callers migrate
-- to the junction table. Backfill script should be run manually:
--
-- INSERT INTO daily_test_load_items (load_id, test_id, display_order, is_completed)
-- SELECT
--     dtl.id,
--     (elem #>> '{}')::uuid,
--     (row_number() OVER (PARTITION BY dtl.id))::integer,
--     EXISTS (
--         SELECT 1 FROM jsonb_array_elements_text(dtl.completed_test_ids) ct
--         WHERE ct.value = elem #>> '{}'
--     )
-- FROM daily_test_loads dtl,
--      jsonb_array_elements(dtl.test_ids) WITH ORDINALITY AS arr(elem, ord)
-- ON CONFLICT DO NOTHING;
