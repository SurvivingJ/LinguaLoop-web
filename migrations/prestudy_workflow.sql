-- =============================================================================
-- Test prestudy workflow: sessions, next-day review, ledger kind, exercise
-- attempt source, per-language setting.
-- Spec: wiki/features/test-prestudy.md (Measurement; What it writes; Spacing
-- across days; Triggers; Time, shown honestly).
--
-- *** REQUIRES EXPLICIT USER APPROVAL TO APPLY LIVE. Apply after
-- *** migrations/prestudy_elo_factor.sql. The Flask code degrades gracefully
-- *** until both are applied (prestudy works; nothing is measured or verified).
--
-- Objects:
--   public.prestudy_sessions          (new)  one row per prestudy session
--   public.prestudy_followups         (new)  next-day review senses
--   public.exercise_attempts.source   (new column) 'prestudy' for prime exercises
--   public.user_study_plans.prestudy_mode (new column) 'auto' | 'ask' | 'off'
--   public.study_time_ledger kind     (+ 'prestudy')
--   public.credit_study_time          (redefined: 'prestudy' cap 900 s)
--   public.get_weekly_study_seconds   (redefined: 'prestudy' key)
--
-- credit_study_time / get_weekly_study_seconds were defined in
-- migrations/study_time_ledger.sql, a multi-object file that is still the only
-- record of the ledger table, so it is kept (migrations/CLAUDE.md rule 4).
-- Both bodies below are the live definitions (checked 2026-10-31) plus the
-- 'prestudy' kind and nothing else.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- prestudy_sessions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.prestudy_sessions (
    id                      uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id             smallint    NOT NULL REFERENCES public.dim_languages(id),
    test_id                 uuid        NOT NULL REFERENCES public.tests(id) ON DELETE CASCADE,
    test_type               text        NOT NULL DEFAULT 'reading'
                            CHECK (test_type IN ('reading', 'listening')),
    mode                    text        NOT NULL DEFAULT 'prime'
                            CHECK (mode IN ('prime', 'followup')),
    trigger                 text        NOT NULL DEFAULT 'opt_in'
                            CHECK (trigger IN ('opt_in', 'auto', 'retry')),
    plan_mode               text        CHECK (plan_mode IN ('full', 'light', 'none')),
    session_block_id        text,                   -- daily session item id when run from the session
    load_date               date,                   -- the daily load it belongs to, if any
    unknown_share_at_open   numeric(4,3) CHECK (unknown_share_at_open BETWEEN 0 AND 1),
    words_shown             integer[]   NOT NULL DEFAULT '{}',
    words_quizzed           integer[]   NOT NULL DEFAULT '{}',
    exposures               integer     NOT NULL DEFAULT 0,
    first_try_correct       integer     NOT NULL DEFAULT 0,
    first_try_total         integer     NOT NULL DEFAULT 0,
    idk_count               integer     NOT NULL DEFAULT 0,
    boosters                integer     NOT NULL DEFAULT 0,
    ladder_exercises        integer     NOT NULL DEFAULT 0,
    readiness_score         smallint,
    readiness_n             smallint,
    readiness_rounds        smallint    NOT NULL DEFAULT 0,
    ready                   boolean,
    next_day_review_senses  integer[]   NOT NULL DEFAULT '{}',
    minutes_est             smallint,
    active_seconds          integer     NOT NULL DEFAULT 0 CHECK (active_seconds BETWEEN 0 AND 3600),
    minutes_source          text        NOT NULL DEFAULT 'free'
                            CHECK (minutes_source IN ('tests_share', 'free')),
    tests_dropped_today     smallint    NOT NULL DEFAULT 0,
    followup                jsonb,                  -- post-test follow-up prime result
    produce                 jsonb,                  -- Produce (dual translation) result
    status                  text        NOT NULL DEFAULT 'open'
                            CHECK (status IN ('open', 'completed', 'consumed')),
    attempt_id              uuid,                   -- the test_attempts row it was spent on
    started_at              timestamptz NOT NULL DEFAULT now(),
    completed_at            timestamptz,
    consumed_at             timestamptz
);

CREATE INDEX IF NOT EXISTS prestudy_sessions_user_test_idx
    ON public.prestudy_sessions (user_id, test_id, started_at DESC);
CREATE INDEX IF NOT EXISTS prestudy_sessions_user_lang_idx
    ON public.prestudy_sessions (user_id, language_id, started_at DESC);

ALTER TABLE public.prestudy_sessions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.prestudy_sessions FROM PUBLIC, anon, authenticated;   -- writes and reads via Flask

COMMENT ON TABLE public.prestudy_sessions IS
    'Test prestudy: one row per study session (wiki/features/test-prestudy.md, Measurement). '
    'unknown_share_at_open is a snapshot and is never recomputed. A completed session '
    'within 6 h makes the next first attempt prestudied (0.5x ELO); status consumed + '
    'attempt_id record which attempt spent it. Service role only.';

-- ---------------------------------------------------------------------------
-- prestudy_followups: next-day review inside the Maintenance pool
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.prestudy_followups (
    id              bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id     smallint    NOT NULL REFERENCES public.dim_languages(id),
    sense_id        integer     NOT NULL,
    session_id      uuid        REFERENCES public.prestudy_sessions(id) ON DELETE CASCADE,
    reason          text        NOT NULL
                    CHECK (reason IN ('idk_twice', 'readiness_missed', 'primed_missed_in_test',
                                      'omitted_in_produce')),
    due_date        date        NOT NULL,           -- learner-local day it becomes due
    served_at       timestamptz,
    completed_at    timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, sense_id, due_date)
);

CREATE INDEX IF NOT EXISTS prestudy_followups_due_idx
    ON public.prestudy_followups (user_id, language_id, due_date)
    WHERE completed_at IS NULL;

ALTER TABLE public.prestudy_followups ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.prestudy_followups FROM PUBLIC, anon, authenticated;

COMMENT ON TABLE public.prestudy_followups IS
    'Test prestudy next-day review: senses answered "I don''t know" twice, missed in the '
    'readiness check, primed and still missed in the test, or omitted in Produce. Served '
    'once in the Maintenance practice pool on due_date or later; never a ladder admission '
    'and never counted against new_words_per_day. Service role only.';

-- ---------------------------------------------------------------------------
-- exercise_attempts.source: ladder exercises answered inside a prestudy prime
-- ---------------------------------------------------------------------------
ALTER TABLE public.exercise_attempts ADD COLUMN IF NOT EXISTS source text;
ALTER TABLE public.exercise_attempts DROP CONSTRAINT IF EXISTS exercise_attempts_source_check;
ALTER TABLE public.exercise_attempts
    ADD CONSTRAINT exercise_attempts_source_check
    CHECK (source IS NULL OR source IN ('prestudy')) NOT VALID;
COMMENT ON COLUMN public.exercise_attempts.source IS
    'NULL = practice session (default). ''prestudy'' = answered inside a test prestudy '
    'prime: BKT exercise evidence, no ladder row, no practice minutes (the prestudy '
    'session is credited as a whole).';

-- ---------------------------------------------------------------------------
-- user_study_plans.prestudy_mode: "Prestudy hard tests: auto / ask / off"
-- ---------------------------------------------------------------------------
ALTER TABLE public.user_study_plans ADD COLUMN IF NOT EXISTS prestudy_mode text NOT NULL DEFAULT 'auto';
ALTER TABLE public.user_study_plans DROP CONSTRAINT IF EXISTS user_study_plans_prestudy_mode_check;
ALTER TABLE public.user_study_plans
    ADD CONSTRAINT user_study_plans_prestudy_mode_check
    CHECK (prestudy_mode IN ('auto', 'ask', 'off')) NOT VALID;
COMMENT ON COLUMN public.user_study_plans.prestudy_mode IS
    'Test prestudy trigger for the daily session: auto = a study block before new tests '
    'over 25% unknown and before retry slots; ask = the same tests get a "Study first" '
    'offer on the card; off = opt-in from the card only.';

-- ---------------------------------------------------------------------------
-- study_time_ledger: 'prestudy' kind
-- ---------------------------------------------------------------------------
ALTER TABLE public.study_time_ledger DROP CONSTRAINT IF EXISTS study_time_ledger_kind_check;
ALTER TABLE public.study_time_ledger
    ADD CONSTRAINT study_time_ledger_kind_check
    CHECK (kind IN ('test', 'practice', 'flashcard', 'dual_translation', 'drill', 'prestudy')) NOT VALID;

CREATE OR REPLACE FUNCTION public.credit_study_time(
    p_user_id      uuid,
    p_language_id  smallint,
    p_kind         text,
    p_seconds      integer,
    p_source_table text,
    p_source_id    text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_cap  integer;
    v_secs integer;
    v_week date;
    v_n    integer;
BEGIN
    v_cap := CASE p_kind
        WHEN 'test'             THEN 1200
        WHEN 'drill'            THEN 1200
        WHEN 'practice'         THEN 300
        WHEN 'flashcard'        THEN 120
        WHEN 'dual_translation' THEN 900
        WHEN 'prestudy'         THEN 900
        ELSE NULL
    END;
    IF v_cap IS NULL THEN
        RAISE EXCEPTION 'credit_study_time: invalid kind %', p_kind
            USING ERRCODE = 'check_violation';
    END IF;
    IF p_source_table IS NULL OR btrim(p_source_table) = ''
       OR p_source_id IS NULL OR btrim(p_source_id) = '' THEN
        RAISE EXCEPTION 'credit_study_time: source_table and source_id must be non-empty'
            USING ERRCODE = 'check_violation';
    END IF;
    v_secs := LEAST(GREATEST(0, COALESCE(p_seconds, 0)), v_cap);
    IF v_secs <= 0 THEN
        RETURN false;
    END IF;
    v_week := public.week_start_for(public.plan_local_date(p_user_id, p_language_id));
    INSERT INTO public.study_time_ledger
        (user_id, language_id, week_start_date, kind, seconds, source_table, source_id)
    VALUES
        (p_user_id, p_language_id, v_week, p_kind, v_secs, p_source_table, p_source_id)
    ON CONFLICT (kind, source_table, source_id) DO NOTHING;
    GET DIAGNOSTICS v_n = ROW_COUNT;
    RETURN v_n > 0;
END
$$;

REVOKE ALL ON FUNCTION public.credit_study_time(uuid, smallint, text, integer, text, text)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.credit_study_time(uuid, smallint, text, integer, text, text)
    TO service_role;

COMMENT ON FUNCTION public.credit_study_time IS
    'ADR-035: credit measured seconds to the learner-local current week, once per '
    '(kind, source_table, source_id). Clamps per kind (test/drill 1200, practice 300, '
    'flashcard 120, dual_translation 900, prestudy 900). Raises check_violation on bad kind '
    'or empty source. service_role only.';

CREATE OR REPLACE FUNCTION public.get_weekly_study_seconds(
    p_user_id     uuid,
    p_language_id smallint,
    p_week_start  date
)
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
    SELECT jsonb_build_object(
        'test',             COALESCE(SUM(l.seconds) FILTER (WHERE l.kind = 'test'), 0)::int,
        'practice',         COALESCE(SUM(l.seconds) FILTER (WHERE l.kind = 'practice'), 0)::int,
        'flashcard',        COALESCE(SUM(l.seconds) FILTER (WHERE l.kind = 'flashcard'), 0)::int,
        'dual_translation', COALESCE(SUM(l.seconds) FILTER (WHERE l.kind = 'dual_translation'), 0)::int,
        'drill',            COALESCE(SUM(l.seconds) FILTER (WHERE l.kind = 'drill'), 0)::int,
        'prestudy',         COALESCE(SUM(l.seconds) FILTER (WHERE l.kind = 'prestudy'), 0)::int
    )
    FROM public.study_time_ledger l
    WHERE l.user_id = p_user_id
      AND l.language_id = p_language_id
      AND l.week_start_date = p_week_start
$$;

REVOKE ALL ON FUNCTION public.get_weekly_study_seconds(uuid, smallint, date)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_weekly_study_seconds(uuid, smallint, date)
    TO service_role;

COMMENT ON FUNCTION public.get_weekly_study_seconds IS
    'ADR-035: summed ledger seconds per kind for (user, language, learner-local week '
    'Monday); all six keys always present. service_role only.';

COMMIT;

-- Validate outside the transaction (weaker lock, concurrent-friendly scan).
ALTER TABLE public.exercise_attempts VALIDATE CONSTRAINT exercise_attempts_source_check;
ALTER TABLE public.user_study_plans VALIDATE CONSTRAINT user_study_plans_prestudy_mode_check;
ALTER TABLE public.study_time_ledger VALIDATE CONSTRAINT study_time_ledger_kind_check;
