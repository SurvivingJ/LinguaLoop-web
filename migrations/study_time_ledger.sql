-- =============================================================================
-- Weekly minutes: study_time_ledger + credit_study_time + get_weekly_study_seconds
-- ADR-035 (decisions/ADR-035-study-time-ledger.md), spec features/weekly-minutes.tech.md
-- TASK-885.
--
-- *** REQUIRES EXPLICIT USER APPROVAL TO APPLY LIVE. Do not apply from an agent
-- *** session without it (TASK-896 owns rollout: apply this, deploy code, then run
-- *** migrations/backfill_study_time_ledger.sql, then tests/sql/check_function_acls.sql).
--
-- One append-only row per credited source. Dedupe is UNIQUE (kind, source_table,
-- source_id). The week is the learner-LOCAL Monday at credit time:
--   week_start_for(plan_local_date(user, language))   (migrations/task716_local_day_boundary.sql,
--                                                      migrations/phase13_build_daily_session.sql)
-- Works when no weekly_plan_states row exists. Does not touch weekly_plan_states.
-- Writes only via credit_study_time (service_role); no client privileges, no policy.
-- Idempotent: IF NOT EXISTS / CREATE OR REPLACE / repeatable REVOKE+GRANT.
-- Depends on: auth.users, public.dim_languages, public.plan_local_date, public.week_start_for.
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.study_time_ledger (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id     smallint    NOT NULL REFERENCES public.dim_languages(id),
    week_start_date date        NOT NULL,   -- learner-local Monday
    kind            text        NOT NULL
                    CHECK (kind IN ('test','practice','flashcard','dual_translation','drill')),
    seconds         integer     NOT NULL CHECK (seconds BETWEEN 1 AND 1200),
    source_table    text        NOT NULL,   -- 'test_attempts' | 'exercise_attempts' | 'flashcard_review' | 'dt_submission' | 'dt_card_review'
    source_id       text        NOT NULL,   -- attempt uuid / submission id / client_event_id
    credited_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (kind, source_table, source_id)
);

CREATE INDEX IF NOT EXISTS study_time_ledger_week_idx
    ON public.study_time_ledger (user_id, language_id, week_start_date);

ALTER TABLE public.study_time_ledger ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.study_time_ledger FROM PUBLIC, anon, authenticated;   -- no policy: browser never reads it

COMMENT ON TABLE public.study_time_ledger IS
    'ADR-035: append-only measured study seconds per credited source, by kind and '
    'learner-local week. Display only; weekly_plan_states planner columns are separate. '
    'Written only by credit_study_time (service_role).';


-- ---------------------------------------------------------------------------
-- credit_study_time -> true when newly credited, false on duplicate or <= 0 s
-- ---------------------------------------------------------------------------
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

    -- Learner-local week at credit time (same helpers record_session_progress uses).
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
    'flashcard 120, dual_translation 900). Raises check_violation on bad kind or empty source. '
    'service_role only.';


-- ---------------------------------------------------------------------------
-- get_weekly_study_seconds -> {"test":n,"practice":n,"flashcard":n,"dual_translation":n,"drill":n}
-- ---------------------------------------------------------------------------
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
        'drill',            COALESCE(SUM(l.seconds) FILTER (WHERE l.kind = 'drill'), 0)::int
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
    'Monday); all five keys always present. service_role only.';
