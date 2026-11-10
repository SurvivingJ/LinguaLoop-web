-- =============================================================================
-- New-word drill (wiki/features/new-word-drill.tech.md, ADR-040, TASK-912/913)
--
-- Newly admitted ladder words go through four criterion-based intro sessions
-- (day 0/1/2/4, 5/3/2/2 counted correct answers) before ring 2. Intro progress
-- lives on user_word_ladder in a new word_state 'intro': every existing ladder
-- function filters word_state by an explicit list, so intro rows stay out of
-- get_practice_session / get_ladder_session / build_daily_session with no
-- change to those functions. The stage logic is in services/intro_drill.py.
--
-- Idempotent.
-- =============================================================================

-- 1. word_state 'intro' + intro progress columns
ALTER TABLE public.user_word_ladder DROP CONSTRAINT IF EXISTS user_word_ladder_word_state_check;
ALTER TABLE public.user_word_ladder ADD CONSTRAINT user_word_ladder_word_state_check
    CHECK (word_state IN ('new','active','gated','pre_mastery','relearning','mastered','intro'));

ALTER TABLE public.user_word_ladder
    ADD COLUMN IF NOT EXISTS intro_stage    smallint NULL,
    ADD COLUMN IF NOT EXISTS intro_due_date date     NULL,
    ADD COLUMN IF NOT EXISTS intro_history  jsonb    NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE public.user_word_ladder DROP CONSTRAINT IF EXISTS user_word_ladder_intro_stage_check;
ALTER TABLE public.user_word_ladder ADD CONSTRAINT user_word_ladder_intro_stage_check
    CHECK (intro_stage IS NULL OR intro_stage BETWEEN 1 AND 4);

CREATE INDEX IF NOT EXISTS idx_user_word_ladder_intro_due
    ON public.user_word_ladder (user_id, intro_due_date) WHERE word_state = 'intro';

-- 2. Intro answers are exercise_attempts rows tagged source = 'intro'
ALTER TABLE public.exercise_attempts DROP CONSTRAINT IF EXISTS exercise_attempts_source_check;
ALTER TABLE public.exercise_attempts ADD CONSTRAINT exercise_attempts_source_check
    CHECK (source IS NULL OR source IN ('prestudy', 'intro'));

-- 3. New-word quota: default 10; plans still at the old default 5 move to 10
ALTER TABLE public.user_study_plans ALTER COLUMN new_words_per_day SET DEFAULT 10;
UPDATE public.user_study_plans SET new_words_per_day = 10 WHERE new_words_per_day = 5;

-- 4. ladder_new_word_state: an intro word is servable without 3 exercises
--    (session 1 runs on gloss + sentence + reading), and a word counts as
--    started at its first intro session (intro_history entries with a stage,
--    which includes a prestudy prime that counted as session 1).
CREATE OR REPLACE FUNCTION public.ladder_new_word_state(
    p_user_id uuid, p_language_id smallint, p_day_start timestamptz)
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  WITH w AS (
    SELECT uwl.sense_id, uwl.created_at AS admitted_at, uwl.word_state,
           LEAST(
             (SELECT MIN(ea.created_at) FROM public.exercise_attempts ea
               WHERE ea.user_id = uwl.user_id AND ea.sense_id = uwl.sense_id),
             (SELECT MIN(ea.created_at) FROM public.exercise_attempts ea
                JOIN public.exercises ex ON ex.id = ea.exercise_id
               WHERE ea.user_id = uwl.user_id AND ea.sense_id IS NULL
                 AND ex.word_sense_id = uwl.sense_id),
             (SELECT MIN((e->>'at')::timestamptz) FROM jsonb_array_elements(uwl.intro_history) e
               WHERE e ? 'stage' AND e ? 'at')) AS started_at,
           uwl.word_state = 'intro'
           OR (SELECT COUNT(*) FROM public.exercises ex
                WHERE ex.word_sense_id = uwl.sense_id AND ex.language_id = p_language_id
                  AND ex.is_active) >= 3 AS servable
      FROM public.user_word_ladder uwl
      JOIN public.dim_word_senses dws ON dws.id = uwl.sense_id
      JOIN public.dim_vocabulary  dv  ON dv.id  = dws.vocab_id
     WHERE uwl.user_id = p_user_id AND dv.language_id = p_language_id),
  u AS (
    SELECT sense_id, admitted_at FROM w
     WHERE started_at IS NULL AND servable
       AND word_state IN ('new','active','gated','pre_mastery','relearning','intro')
       AND admitted_at >= now() - interval '14 days')
  SELECT jsonb_build_object(
    'unstarted',     (SELECT COUNT(*) FROM u),
    'started_today', (SELECT COUNT(*) FROM w WHERE started_at >= p_day_start),
    'unstarted_sense_ids', COALESCE((SELECT jsonb_agg(sense_id ORDER BY admitted_at, sense_id)
        FROM (SELECT sense_id, admitted_at FROM u ORDER BY admitted_at, sense_id LIMIT 200) x), '[]'::jsonb));
$$;
REVOKE ALL ON FUNCTION public.ladder_new_word_state(uuid, smallint, timestamptz) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.ladder_new_word_state(uuid, smallint, timestamptz) TO service_role;
