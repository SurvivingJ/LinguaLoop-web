-- ============================================================================
-- grammar_drill_tracking.sql - server-side progress for the grammar drills of
-- every language: one summary row per learner, language, topic and practice
-- day, one current-state row per learner, language and topic, and the one
-- function that writes both.
--
-- SHARED STRUCTURE (2026-11-28, ADR-070; owner: "resolve a shared db structure
-- for tracking grammar drill progress"). The same two tables and function
-- serve the Chinese grammar drills (/grammar-drill/zh, language 1, four
-- stages) and the Japanese drills (language 3): particle and grammar skills
-- (/particle-drill, /grammar-drill/ja; seven stages = six rungs and Instant),
-- conjugation forms (topic conj-<form>) and reading categories (topic
-- read-<category>), four stages each. A topic is a skill id; which topics
-- exist, how many stages each has and the shape of `state` are checked per
-- language in services/grammar_drill_tracking.py (Profile). The database only
-- knows: stage 1 to 7, `state` is an object with `u` (highest stage reached,
-- never lowered) and `l` (epoch seconds of the last answer; the later side
-- wins). This file replaces the separate user_drill_progress table that the
-- particle drill had pending (migrations/particle_drill_progress.sql, removed).
-- Date: 2026-11-27   Task: TASK-1259   ADR-066. APPLIED to the live project 2026-11-28
-- (seven-stage version below; VERIFY AFTER values confirmed).
--
-- Owner decisions 2026-11-27: "do you think we could add tracking in? so we
-- can know the user's improvement over time?" then "Do daily with the current
-- space limit raised to 480mb". The database stop line is 480 MB from now on
-- (was 475 MB); the database was 473.15 MB on 2026-11-24.
--
-- WHAT (three new objects, nothing existing is changed)
--   1. TABLE public.grammar_drill_daily, PK (user_id, language_id, topic,
--      practice_day). Counts of FIRST answers that day: answers, correct,
--      timed (first answers that were right; their recall time is the one
--      that is averaged), ms_sum (sum of those recall times in ms, each capped
--      at 30000 by the client; the route and a CHECK enforce
--      ms_sum <= timed * 30000), stage (highest stage unlocked by the end of
--      the day, 1-7; Chinese topics use 1-4), instant, sub_misses (jsonb: sub-point key -> first-try
--      misses, non-zero entries only), updated_at.
--      NO per-answer and NO per-item rows.
--   2. TABLE public.grammar_drill_state, PK (user_id, language_id, topic).
--      state jsonb = { u: highest unlocked stage, r: [four strings, the last
--      30 results per stage as comma-separated signed ms (+ right, - wrong)],
--      q: answers recorded, e: [endless answers, correct, best streak],
--      l: epoch seconds of the last answer }. The per-item review boxes stay
--      in the browser. last_round_key is the idempotency key of the last
--      round written for the row.
--   3. FUNCTION public.record_grammar_drill_round(p_user_id uuid,
--      p_language_id smallint, p_round_key uuid, p_practice_day date,
--      p_topics jsonb) RETURNS jsonb. One transaction per round: for each
--      topic it locks (or creates) the state row, skips the topic when
--      last_round_key already equals p_round_key (a retry), otherwise adds the
--      counts to the daily row (creating it), merges sub_misses, raises stage,
--      sets instant, and merges the state (the higher unlocked stage; the
--      rolling results of whichever side has the later last answer). A topic
--      with answers = 0 (the first upload of a browser's existing progress)
--      writes the state row only and no daily row.
--      Returns { success, recorded, replayed }.
--      p_practice_day is computed by the caller (routes/grammar_drill.py with
--      services/day_boundary.review_today: the app's review day, zone
--      Australia/Sydney). It does NOT depend on public.review_today(), which
--      is itself still pending (fsrs_review_day_aest.sql).
--      Known limit of the one-key idempotency: only the LAST key per row is
--      remembered. A browser sends its queue in order and stops at the first
--      failure, so a retry is always of the last round that browser sent; a
--      retry that arrives after ANOTHER device has written the same topic in
--      between is counted twice. Accepted (a summary, not a ledger).
--
-- SECURITY
--   Tables: RLS on; one SELECT policy each (own rows, role authenticated);
--   no privilege for PUBLIC, anon or authenticated (the policy is there for
--   the day a client reads directly; today only Flask reads, as service_role,
--   which bypasses RLS). Same shape as user_word_watchlist after
--   security_watchlist_reports_no_client_writes.sql.
--   Function: SECURITY DEFINER, search_path public, pg_temp, owner postgres,
--   EXECUTE for service_role only. It trusts p_user_id: the only caller is
--   the Flask route, which passes the id of the verified token.
--
-- SIZE (measured on a scratch PostgreSQL 16 with this file: 202 learners x 39
-- topics x 60 days = 472,680 daily rows, 1 to 3 sub-point entries each with
-- 9 to 20 character keys; pg_total_relation_size / rows):
--   grammar_drill_daily   about 246 bytes per row in all: 167 heap + 79 primary
--                         key index. The floor for this key (uuid + topic text)
--                         with an empty sub_misses is about 150; the sub-point
--                         keys are the rest.
--   grammar_drill_state   about 665 bytes per row with index for a topic with
--                         two stages of results (state 472 B); about 1,250 at
--                         the most (all four windows full of 5-digit times,
--                         state 980 B). At most 39 rows per Chinese learner;
--                         a Japanese learner has one row per skill started
--                         (427 skills, about 35 conjugation and reading
--                         topics), about 330 bytes each with the index.
--   Both tables empty: 32 kB.
--   A learner who practises 3 topics a day for a year: 3 x 365 x 246 B =
--   0.27 MB, plus up to 39 state rows (26 to 49 kB).
--   Headroom on 2026-11-24: 480 - 473.15 = 6.85 MB, i.e. about 29,000 daily
--   rows before the line. Watch it with the first owner query in
--   wiki/tasklist/grammar-drill-tracking-runbook.md (table sizes).
--
-- WHAT A LEARNER WOULD NOTICE: before this file is applied, nothing (the page
-- keeps progress in the browser and its two API calls answer 503, which the
-- page ignores; unsent rounds wait in the browser, at most 60). After: stages
-- and totals follow the learner to another device, and the topic screen and
-- the hub show progress charts.
--
-- PRECONDITIONS: public.users(id) and public.dim_languages(id) exist (they
-- do). The code can be deployed before or after this file.
-- Idempotent: IF NOT EXISTS / CREATE OR REPLACE / DROP POLICY IF EXISTS.
--
-- VERIFY BEFORE (read-only; expect daily, state, fn all NULL, then the size):
--   SELECT to_regclass('public.grammar_drill_daily') AS daily,
--          to_regclass('public.grammar_drill_state') AS state,
--          to_regprocedure('public.record_grammar_drill_round(uuid,smallint,uuid,date,jsonb)') AS fn;
--   SELECT pg_size_pretty(pg_database_size(current_database())) AS db_size,
--          pg_database_size(current_database()) < 480 * 1024 * 1024 AS under_480mb;
--
-- VERIFY AFTER (read-only). Expect: two table rows with rls = true,
-- policies = 1, anon_sel = auth_sel = auth_ins = false; one function row with
-- definer = true, search_path {"search_path=public, pg_temp"},
-- acl {postgres=X/postgres,service_role=X/postgres}, anon_x = auth_x = false:
--   SELECT c.relname, c.relrowsecurity AS rls,
--          (SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public'
--              AND p.tablename = c.relname) AS policies,
--          has_table_privilege('anon', c.oid, 'SELECT') AS anon_sel,
--          has_table_privilege('authenticated', c.oid, 'SELECT') AS auth_sel,
--          has_table_privilege('authenticated', c.oid, 'INSERT') AS auth_ins,
--          pg_size_pretty(pg_total_relation_size(c.oid)) AS size
--     FROM pg_class c
--    WHERE c.oid IN ('public.grammar_drill_daily'::regclass,
--                    'public.grammar_drill_state'::regclass);
--   SELECT p.oid::regprocedure, p.prosecdef AS definer, p.proconfig AS search_path,
--          p.proacl::text AS acl,
--          has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_x,
--          has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_x
--     FROM pg_proc p WHERE p.proname = 'record_grammar_drill_round';
-- Then tests/sql/check_function_acls.sql (every result set empty).
--
-- ROLLBACK: migrations/grammar_drill_tracking_rollback.sql (drops the function
-- and both tables; the recorded history is lost, the browsers keep their own
-- progress and the page works as before).
-- ============================================================================

BEGIN;

-- Columns are ordered widest first so the row has no padding.
CREATE TABLE IF NOT EXISTS public.grammar_drill_daily (
    user_id       uuid         NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    ms_sum        bigint       NOT NULL DEFAULT 0,
    updated_at    timestamptz  NOT NULL DEFAULT now(),
    practice_day  date         NOT NULL,
    answers       integer      NOT NULL,
    correct       integer      NOT NULL DEFAULT 0,
    timed         integer      NOT NULL DEFAULT 0,
    language_id   smallint     NOT NULL REFERENCES public.dim_languages(id),
    stage         smallint     NOT NULL DEFAULT 1,
    instant       boolean      NOT NULL DEFAULT false,
    topic         text         NOT NULL,
    sub_misses    jsonb        NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT grammar_drill_daily_pkey PRIMARY KEY (user_id, language_id, topic, practice_day),
    CONSTRAINT grammar_drill_daily_topic_chk CHECK (topic ~ '^[a-z0-9-]{1,40}$'),
    CONSTRAINT grammar_drill_daily_answers_chk CHECK (answers BETWEEN 1 AND 50000),
    CONSTRAINT grammar_drill_daily_correct_chk CHECK (correct BETWEEN 0 AND answers),
    CONSTRAINT grammar_drill_daily_timed_chk CHECK (timed BETWEEN 0 AND answers),
    CONSTRAINT grammar_drill_daily_ms_chk CHECK (ms_sum BETWEEN 0 AND timed::bigint * 30000),
    CONSTRAINT grammar_drill_daily_stage_chk CHECK (stage BETWEEN 1 AND 7),
    CONSTRAINT grammar_drill_daily_subs_chk CHECK (
        jsonb_typeof(sub_misses) = 'object' AND pg_column_size(sub_misses) < 1024)
);

COMMENT ON TABLE public.grammar_drill_daily IS
  'Grammar drills of every language (zh grammar; ja particles, grammar, '
  'conjugation, reading): one row per learner, language, topic and '
  'practice day (the app review day, Australia/Sydney, computed in Python). '
  'Counts are over FIRST answers. timed = first answers that were right; '
  'ms_sum = their recall time in ms (each at most 30000). sub_misses = '
  'sub-point key -> first-try misses. Written only by '
  'record_grammar_drill_round. ADR-066.';

CREATE TABLE IF NOT EXISTS public.grammar_drill_state (
    user_id         uuid         NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    last_round_key  uuid,
    updated_at      timestamptz  NOT NULL DEFAULT now(),
    language_id     smallint     NOT NULL REFERENCES public.dim_languages(id),
    topic           text         NOT NULL,
    state           jsonb        NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT grammar_drill_state_pkey PRIMARY KEY (user_id, language_id, topic),
    CONSTRAINT grammar_drill_state_topic_chk CHECK (topic ~ '^[a-z0-9-]{1,40}$'),
    CONSTRAINT grammar_drill_state_state_chk CHECK (
        jsonb_typeof(state) = 'object' AND pg_column_size(state) < 4096)
);

COMMENT ON TABLE public.grammar_drill_state IS
  'Grammar drills of every language: the current state of one learner on one '
  'topic, so progress follows the learner across devices. Always {u: highest '
  'stage reached, l: epoch seconds of the last answer}; the rest is per '
  'language (services/grammar_drill_tracking.py). Chinese: {u: highest unlocked stage, '
  'r: [4 strings of comma-separated signed ms, last 30 results per stage], '
  'q: answers, e: [endless answers, correct, best streak], l: epoch seconds '
  'of the last answer}. last_round_key = idempotency key of the last round '
  'written. Written only by record_grammar_drill_round. ADR-066.';

-- Own rows readable, nothing writable; no client privilege at all today.
ALTER TABLE public.grammar_drill_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.grammar_drill_state ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS grammar_drill_daily_select_own ON public.grammar_drill_daily;
CREATE POLICY grammar_drill_daily_select_own ON public.grammar_drill_daily
  AS PERMISSIVE FOR SELECT TO authenticated
  USING ((SELECT auth.uid()) = user_id);

DROP POLICY IF EXISTS grammar_drill_state_select_own ON public.grammar_drill_state;
CREATE POLICY grammar_drill_state_select_own ON public.grammar_drill_state
  AS PERMISSIVE FOR SELECT TO authenticated
  USING ((SELECT auth.uid()) = user_id);

REVOKE ALL ON TABLE public.grammar_drill_daily FROM PUBLIC, anon, authenticated;
REVOKE ALL ON TABLE public.grammar_drill_state FROM PUBLIC, anon, authenticated;
GRANT ALL ON TABLE public.grammar_drill_daily TO service_role;
GRANT ALL ON TABLE public.grammar_drill_state TO service_role;

CREATE OR REPLACE FUNCTION public.record_grammar_drill_round(
    p_user_id      uuid,
    p_language_id  smallint,
    p_round_key    uuid,
    p_practice_day date,
    p_topics       jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    t           jsonb;
    v_topic     text;
    v_answers   integer;
    v_correct   integer;
    v_timed     integer;
    v_ms        bigint;
    v_stage     integer;
    v_instant   boolean;
    v_subs      jsonb;
    v_new       jsonb;
    v_old       jsonb;
    v_prev      uuid;
    v_merged    jsonb;
    v_u         integer;
    v_recorded  integer := 0;
    v_replayed  integer := 0;
BEGIN
    IF p_user_id IS NULL OR p_language_id IS NULL OR p_round_key IS NULL
       OR p_practice_day IS NULL OR p_topics IS NULL
       OR jsonb_typeof(p_topics) <> 'array'
       OR jsonb_array_length(p_topics) NOT BETWEEN 1 AND 10 THEN
        RETURN jsonb_build_object('success', false, 'error', 'bad_arguments');
    END IF;

    -- Topics in name order: two rounds that share topics lock in one order.
    FOR t IN
        SELECT value FROM jsonb_array_elements(p_topics) ORDER BY value->>'topic'
    LOOP
        v_topic   := t->>'topic';
        v_answers := COALESCE((t->>'answers')::integer, 0);
        v_correct := COALESCE((t->>'correct')::integer, 0);
        v_timed   := COALESCE((t->>'timed')::integer, 0);
        v_ms      := COALESCE((t->>'ms_sum')::bigint, 0);
        v_stage   := LEAST(7, GREATEST(1, COALESCE((t->>'stage')::integer, 1)));
        v_instant := COALESCE((t->>'instant')::boolean, false);
        v_subs    := CASE WHEN jsonb_typeof(t->'sub_misses') = 'object'
                          THEN t->'sub_misses' ELSE '{}'::jsonb END;
        v_new     := CASE WHEN jsonb_typeof(t->'state') = 'object'
                          THEN t->'state' END;

        IF v_topic IS NULL OR v_answers < 0 OR v_correct < 0 OR v_correct > v_answers
           OR v_timed < 0 OR v_timed > v_answers
           OR v_ms < 0 OR v_ms > v_timed::bigint * 30000 THEN
            RAISE EXCEPTION 'record_grammar_drill_round: bad topic entry %', v_topic
                USING ERRCODE = '22023';
        END IF;

        -- Create the state row if needed, then lock it. A concurrent call with
        -- the same key waits here and then sees the key below.
        INSERT INTO grammar_drill_state (user_id, language_id, topic)
        VALUES (p_user_id, p_language_id, v_topic)
        ON CONFLICT (user_id, language_id, topic) DO NOTHING;

        SELECT s.last_round_key, s.state INTO v_prev, v_old
          FROM grammar_drill_state s
         WHERE s.user_id = p_user_id AND s.language_id = p_language_id
           AND s.topic = v_topic
           FOR UPDATE;

        IF v_prev = p_round_key THEN
            v_replayed := v_replayed + 1;
            CONTINUE;
        END IF;

        IF v_answers > 0 THEN
            INSERT INTO grammar_drill_daily AS d
                (user_id, language_id, topic, practice_day, answers, correct,
                 timed, ms_sum, stage, instant, sub_misses)
            VALUES
                (p_user_id, p_language_id, v_topic, p_practice_day, v_answers,
                 v_correct, v_timed, v_ms, v_stage, v_instant, v_subs)
            ON CONFLICT (user_id, language_id, topic, practice_day) DO UPDATE
               SET answers    = d.answers + EXCLUDED.answers,
                   correct    = d.correct + EXCLUDED.correct,
                   timed      = d.timed + EXCLUDED.timed,
                   ms_sum     = d.ms_sum + EXCLUDED.ms_sum,
                   stage      = GREATEST(d.stage, EXCLUDED.stage),
                   instant    = EXCLUDED.instant,
                   sub_misses = (
                       SELECT COALESCE(jsonb_object_agg(m.key, m.n), '{}'::jsonb)
                         FROM (SELECT e.key, LEAST(sum(e.value::integer), 50000) AS n
                                 FROM (SELECT * FROM jsonb_each_text(d.sub_misses)
                                       UNION ALL
                                       SELECT * FROM jsonb_each_text(EXCLUDED.sub_misses)) e
                                GROUP BY e.key) m),
                   updated_at = now()
             -- A day's row stops growing at 50,000 answers (the CHECK's limit).
             WHERE d.answers + EXCLUDED.answers <= 50000;
        END IF;

        -- State: the side with the later last answer wins the rolling results;
        -- the unlocked stage never goes down.
        v_old := COALESCE(v_old, '{}'::jsonb);
        IF v_new IS NULL
           OR COALESCE((v_old->>'l')::bigint, 0) > COALESCE((v_new->>'l')::bigint, 0) THEN
            v_merged := v_old;
        ELSE
            v_merged := v_new;
        END IF;
        v_u := LEAST(7, GREATEST(COALESCE((v_old->>'u')::integer, 1),
                                 COALESCE((v_new->>'u')::integer, 1),
                                 v_stage));
        v_merged := jsonb_set(v_merged, '{u}', to_jsonb(v_u), true);

        UPDATE grammar_drill_state s
           SET state = v_merged,
               last_round_key = p_round_key,
               updated_at = now()
         WHERE s.user_id = p_user_id AND s.language_id = p_language_id
           AND s.topic = v_topic;

        v_recorded := v_recorded + 1;
    END LOOP;

    RETURN jsonb_build_object('success', true, 'recorded', v_recorded,
                              'replayed', v_replayed);
END;
$$;

ALTER FUNCTION public.record_grammar_drill_round(uuid, smallint, uuid, date, jsonb) OWNER TO postgres;
REVOKE ALL ON FUNCTION public.record_grammar_drill_round(uuid, smallint, uuid, date, jsonb)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.record_grammar_drill_round(uuid, smallint, uuid, date, jsonb)
  TO service_role;

COMMIT;
