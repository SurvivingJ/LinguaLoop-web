-- ============================================================================
-- fsrs_review_day_aest.sql - one app-wide FSRS review day: midnight Sydney time
-- Date: 2026-11-23   Task: TASK-1211 (owner decision). NOT APPLIED.
-- NOTE: the file name is historical ("aest"); the review zone is the IANA zone
-- Australia/Sydney (owner decision 2026-11-23: "Use Sydney time"): UTC+11 in
-- daylight saving (first Sunday in October to first Sunday in April), UTC+10
-- otherwise.
--
-- *** LEARNER-VISIBLE (flashcard due dates roll over at 00:00 Sydney time =
--     13:00 UTC in daylight saving, 14:00 UTC otherwise, instead of 00:00 UTC).
--     MUST SWITCH TOGETHER WITH THE PYTHON DEPLOY. ***
--
-- WHAT
--   1. NEW public.review_today(p_at timestamptz DEFAULT now()) RETURNS date:
--      (p_at AT TIME ZONE 'Australia/Sydney')::date. LANGUAGE sql, STABLE,
--      SECURITY INVOKER, search_path public, pg_temp, EXECUTE service_role only.
--      THE ONE SQL PLACE the review zone is configured (one string literal).
--      Python mirror: services/day_boundary.py REVIEW_TIMEZONE. Change both;
--      tests/test_review_day_boundary.py checks they name the same zone.
--   2. CREATE OR REPLACE of every live SQL function that writes or decides the
--      due-ness of user_flashcards (FSRS) dates. Each body is the LIVE body
--      (equal by body hash to its canonical repo file, listed below; CRLF
--      normalised to LF) with ONLY the FSRS date expression replaced by
--      public.review_today(). Headers are pg_get_functiondef's live headers:
--      language, volatility, SECURITY DEFINER/INVOKER and search_path (or its
--      absence) unchanged; owner unchanged (CREATE OR REPLACE keeps it);
--      REVOKE/GRANT repeat the live ACL {postgres=X, service_role=X}.
--
--   function (canonical file)                         change                                live md5 -> new md5
--   get_session_senses (phase7_bkt_improvements.sql)   due_date <= CURRENT_DATE -> review_today()   b2a2b93d... -> d15a2bcf...
--   get_practice_session (exercise_content_drop_column.sql)
--        adds v_review_today := review_today(); the five FSRS uses of v_today
--        (due count, due-within-7, overdue days, two practice_unified_score
--        "today" args) use it. v_today := CURRENT_DATE stays for the
--        anti-repetition check (user_exercise_history.session_date defaults to
--        CURRENT_DATE, so that comparison must stay on the UTC calendar).        18fd3ccc... -> cd0ccdbd...
--   compute_weekly_plan_load_signals (phase13_compute_weekly_plan_helpers.sql)
--        v_today := CURRENT_DATE -> review_today() (its only use: due_date <= v_today + 7)  73756412... -> 5867f1b6...
--   review_governor_state (new_word_drill_governor.sql)
--        the two user_flashcards comparisons with p_date -> review_today();
--        p_date (study-plan local date) still drives the intro_due_date
--        comparisons, the "reviews done today" window and the week.         bdf56ab2... -> 8932c062...
--   build_daily_session (build_daily_session_dt_agreed.sql)
--        flashcard minutes: uf.due_date <= p_date -> review_today(); every
--        other p_date use (load_date, week, slot accounting) unchanged.     6bf2da32... -> 17b8b5dc...
--   ladder_graduate (phase8_momentum_bands.sql)
--        FSRS card due_date and last_review: CURRENT_DATE -> review_today()  421cedb5... -> 3f911f00...
--   ladder_record_attempt (phase10_ladder_advancement_demotion.sql)
--        lapse path: fsrs_schedule_review(..., CURRENT_DATE) and
--        last_review = CURRENT_DATE -> review_today(). The ladder's OWN dates
--        (family_success_dates, user_word_ladder.review_due_at,
--        last_success_session_date) keep CURRENT_DATE: they are not FSRS.   5ba8b9ee... -> 2d387cf6...
--
--   Not changed (checked): practice_unified_score uses COALESCE(p_today,
--   CURRENT_DATE) and its only caller (get_practice_session) passes a non-NULL
--   date; fsrs_schedule_review takes the review date as an argument;
--   record_exercise_attempt only returns the card row (Python rates it);
--   get_review_ahead_items orders by due_date with no "today";
--   new_word_state_inputs reaches the FSRS dates only through
--   review_governor_state.
--
-- WHY: the FSRS day was the UTC date everywhere. The owner chose one fixed
-- app-wide review time zone ("Use Sydney time") over per-learner local days.
-- The study plan's own timezone keeps governing plan/day-slot accounting only;
-- FSRS due-ness everywhere (flashcard page, practice session, daily session,
-- review governor, weekly load signals) uses review_today().
--
-- PENDING-MIGRATION INTERACTION: none of the other files in
-- migrations/PENDING-2026-11-23.md (groups 1-9) replaces any function in this
-- file, so order relative to them does not matter. If any function's VERIFY
-- BEFORE hash differs, something else changed it: do not apply; re-derive.
--
-- DEPLOYMENT ORDER (with the Python change, commit "FSRS review day: one
-- app-wide review time zone (Sydney) in Python"):
--   While the Sydney date equals the UTC date, old and new code compute the
--   SAME day and a half-switched system behaves identically. That window is
--   00:00 to 13:00 UTC during daylight saving (11:00-24:00 Sydney time; in
--   force on 2026-11-23) and 00:00 to 14:00 UTC otherwise (10:00-24:00 Sydney
--   time). Do both halves inside one such window: deploy the Python first,
--   confirm it is healthy, then apply this file (one transaction) straight
--   after, well before the window closes (13:00 UTC in daylight saving).
--   If the deploy is rolled back, do not apply this file (or apply the
--   rollback inside the window).
--   Worst case if the halves straddle the end of the window (13:00-24:00 UTC
--   in daylight saving, 14:00-24:00 UTC otherwise: at most 11 hours,
--   self-healing at 00:00 UTC): the flashcard page and the practice/daily
--   session disagree by one day about which cards are due today (a card due
--   "tomorrow" on one calendar shows as due on the other), and a card
--   reviewed in that window may be stamped one day earlier or later
--   depending on which path rated it. No data is lost.
--
-- EXISTING ROWS: no backfill. A card stamped on the UTC calendar keeps its
-- due_date; it now becomes due at 00:00 Sydney time on that date (13:00 UTC the
-- day before in daylight saving, 14:00 UTC otherwise) instead of 00:00 UTC,
-- i.e. up to 11 hours EARLIER in daylight saving (10 hours otherwise), never
-- later. Reviews made 13:00-24:00 UTC (14:00-24:00 outside daylight saving)
-- were dated one day behind the Sydney date, so
-- those cards' intervals measured on the new calendar are at most one day
-- shorter (due at most one day early). last_review (timestamptz) keeps the
-- convention "calendar date at 00:00 UTC" for both old and new rows.
--
-- VERIFY BEFORE (read-only; expect ok = true on all seven rows and
-- review_today absent):
-- VERIFY AFTER (expect the new hashes, ok_after = true on all seven, and
-- review_today present, STABLE, not SECURITY DEFINER, service_role-only):
--   SELECT v.fn,
--          md5(regexp_replace(regexp_replace(p.prosrc, '--[^\n]*', '', 'g'), '\s', '', 'g')) = v.before AS ok,
--          md5(regexp_replace(regexp_replace(p.prosrc, '--[^\n]*', '', 'g'), '\s', '', 'g')) = v.after  AS ok_after,
--          p.prosecdef, p.provolatile, p.proconfig
--     FROM (VALUES
--       ('public.get_session_senses(uuid,smallint,integer,integer,integer)', 'b2a2b93dcdeb7b06bc05ec8e8c3ea197', 'd15a2bcf4e4e552366fcd03071ca4992'),
--       ('public.get_practice_session(uuid,smallint,text,smallint,numeric,boolean)', '18fd3ccca9f9cefb73c05a80167f75bd', 'cd0ccdbd558092d1ee85edd1bf1e7198'),
--       ('public.compute_weekly_plan_load_signals(uuid,smallint,date)', '73756412aad05cbc18663cf3b49e93b0', '5867f1b6de30dfc3e92bf9077001788a'),
--       ('public.review_governor_state(uuid,smallint,date)', 'bdf56ab22958f3ff7c5cf2d3798caa2f', '8932c0623022b9158d2739112c2130c2'),
--       ('public.build_daily_session(uuid,smallint,date)', '6bf2da329373c7a4ad8ba9a552bc407d', '17b8b5dceea327448b0f824af8e869a4'),
--       ('public.ladder_graduate(uuid,integer,real,smallint)', '421cedb5dbab42322a6f1be7aa11658a', '3f911f00954625acac90d1741a9987fb'),
--       ('public.ladder_record_attempt(uuid,integer,uuid,boolean,boolean,integer,smallint,text,integer,text)', '5ba8b9ee7faac0303db4fd97bc66b5b7', '2d387cf6bc3c7b9abdccd599b5e2cef5')
--     ) AS v(fn, before, after)
--     JOIN pg_proc p ON p.oid = v.fn::regprocedure;
--   SELECT to_regprocedure('public.review_today(timestamptz)') IS NOT NULL AS has_helper,
--          public.review_today(timestamptz '2026-11-23 12:30+00') AS d_2330_sydney, -- expect 2026-11-23
--          public.review_today(timestamptz '2026-11-23 13:30+00') AS d_0030_sydney;  -- expect 2026-11-24
--
-- ROLLBACK: migrations/fsrs_review_day_aest_rollback.sql (the seven live
-- bodies, then DROP review_today). Roll back the Python together, inside a
-- window (00:00-13:00 UTC in daylight saving, 00:00-14:00 UTC otherwise), for
-- the same reason as above.
--
-- After applying: this file is canonical for the seven functions. Per
-- migrations/CLAUDE.md, check whether each canonical file listed above is now
-- fully superseded before archiving it (several are multi-object files:
-- phase7_bkt_improvements.sql, phase8_momentum_bands.sql,
-- phase13_compute_weekly_plan_helpers.sql, new_word_drill_governor.sql,
-- exercise_content_drop_column.sql, build_daily_session_dt_agreed.sql and
-- phase10_ladder_advancement_demotion.sql may still be the only record of
-- other live objects; keep those).
--
-- Idempotent: CREATE OR REPLACE + REVOKE/GRANT in one transaction; safe to re-run.
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.review_today(p_at timestamptz DEFAULT now())
 RETURNS date
 LANGUAGE sql
 STABLE
 SET search_path = public, pg_temp
AS $function$
    -- THE ONE SQL PLACE the FSRS review day's time zone is set (TASK-1211).
    -- Python mirror: services/day_boundary.py REVIEW_TIMEZONE. Change both.
    SELECT (p_at AT TIME ZONE 'Australia/Sydney')::date
$function$;

REVOKE ALL ON FUNCTION public.review_today(timestamptz) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.review_today(timestamptz) TO service_role;

COMMENT ON FUNCTION public.review_today(timestamptz) IS
  'TASK-1211: today on the app-wide FSRS review calendar (midnight Sydney time, Australia/Sydney). '
  'Every user_flashcards due_date/last_review read or write uses this date. '
  'Python mirror: services/day_boundary.review_today (REVIEW_TIMEZONE).';

-- ---------------------------------------------------------------------------
-- public.get_session_senses(uuid, smallint, integer, integer, integer)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.get_session_senses(p_user_id uuid, p_language_id smallint, p_due_limit integer DEFAULT 30, p_learning_limit integer DEFAULT 30, p_new_limit integer DEFAULT 30)
 RETURNS TABLE(out_sense_id integer, out_effective_p_known numeric, out_bucket text, out_entropy numeric)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    RETURN QUERY

    -- Bucket 1: FSRS due reviews
    (
        SELECT
            uf.sense_id AS out_sense_id,
            bkt_effective_p_known(
                COALESCE(uvk.p_known, 0.50),
                uvk.last_evidence_at,
                uf.stability,
                COALESCE(uvk.evidence_count, 0)
            ) AS out_effective_p_known,
            'due'::text AS out_bucket,
            -- Entropy for tie-breaking: p*(1-p), max at 0.5
            COALESCE(uvk.p_known, 0.50) * (1 - COALESCE(uvk.p_known, 0.50)) AS out_entropy
        FROM user_flashcards uf
        LEFT JOIN user_vocabulary_knowledge uvk
            ON uvk.user_id = uf.user_id AND uvk.sense_id = uf.sense_id
        WHERE uf.user_id = p_user_id
          AND uf.language_id = p_language_id
          AND uf.due_date <= public.review_today()
          AND uf.state IN ('review', 'relearning')
        ORDER BY uf.due_date
        LIMIT p_due_limit
    )

    UNION ALL

    -- Bucket 2: Active learning (uncertainty zone after decay)
    (
        SELECT
            sub.sense_id,
            sub.eff_p,
            'learning'::text,
            sub.eff_p * (1 - sub.eff_p)
        FROM (
            SELECT
                uvk.sense_id,
                bkt_effective_p_known(
                    uvk.p_known,
                    uvk.last_evidence_at,
                    uf.stability,
                    uvk.evidence_count
                ) AS eff_p
            FROM user_vocabulary_knowledge uvk
            LEFT JOIN user_flashcards uf
                ON uf.user_id = uvk.user_id AND uf.sense_id = uvk.sense_id
            WHERE uvk.user_id = p_user_id
              AND uvk.language_id = p_language_id
              -- Widen stored range to catch words that decay into target zone
              AND uvk.p_known BETWEEN 0.20 AND 0.85
              AND uvk.status NOT IN ('user_marked_unknown', 'unknown')
        ) sub
        WHERE sub.eff_p BETWEEN 0.25 AND 0.75
        ORDER BY sub.eff_p * (1 - sub.eff_p) DESC  -- highest entropy first
        LIMIT p_learning_limit
    )

    UNION ALL

    -- Bucket 3: New/encountered senses (low effective p_known)
    (
        SELECT
            sub.sense_id,
            sub.eff_p,
            'new'::text,
            0.0  -- entropy not used for sorting new words
        FROM (
            SELECT
                uvk.sense_id,
                bkt_effective_p_known(
                    uvk.p_known,
                    uvk.last_evidence_at,
                    uf.stability,
                    uvk.evidence_count
                ) AS eff_p,
                uvk.last_evidence_at
            FROM user_vocabulary_knowledge uvk
            LEFT JOIN user_flashcards uf
                ON uf.user_id = uvk.user_id AND uf.sense_id = uvk.sense_id
            WHERE uvk.user_id = p_user_id
              AND uvk.language_id = p_language_id
              AND uvk.p_known < 0.40  -- wider to catch decay
              AND uvk.status IN ('encountered', 'unknown')
        ) sub
        WHERE sub.eff_p < 0.30
        ORDER BY sub.last_evidence_at DESC NULLS LAST
        LIMIT p_new_limit
    );
END;
$function$;

REVOKE ALL ON FUNCTION public.get_session_senses(uuid, smallint, integer, integer, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_session_senses(uuid, smallint, integer, integer, integer) TO service_role;

-- ---------------------------------------------------------------------------
-- public.get_practice_session(uuid, smallint, text, smallint, numeric, boolean)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.get_practice_session(p_user_id uuid, p_language_id smallint, p_mode text DEFAULT 'auto'::text, p_target_minutes smallint DEFAULT 15, p_user_theta numeric DEFAULT NULL::numeric, p_include_content boolean DEFAULT true)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_mode            text;
    v_theta           numeric;
    v_weights         jsonb;
    v_alpha           numeric;
    v_beta            numeric;
    v_gamma           numeric;
    v_delta           numeric;
    v_target_seconds  integer;
    v_elapsed_seconds integer := 0;
    v_items           jsonb := '[]'::jsonb;
    v_no_content      text   := NULL;
    v_session_id      uuid   := gen_random_uuid();
    v_due_today       integer;
    v_decayed_count   integer;
    v_active_ladder   integer;
    v_today           date   := CURRENT_DATE;
    v_review_today    date   := public.review_today();
    v_eligible_count  integer;
    v_word            RECORD;
    v_item            RECORD;
    v_fam             text;
    v_active_levels   integer[] := ARRAY[1,2,3,4,5,6,7,8,9];
BEGIN
    -- =============================================================
    -- 1. Validate inputs
    -- =============================================================
    IF NOT EXISTS (
        SELECT 1 FROM public.dim_languages
        WHERE id = p_language_id AND is_active
    ) THEN
        RETURN jsonb_build_object('error','language_not_active','code','E_LANG');
    END IF;

    IF p_mode NOT IN ('acquisition','maintenance','auto') THEN
        RETURN jsonb_build_object('error','invalid_mode','code','E_MODE');
    END IF;

    IF p_target_minutes IS NULL OR p_target_minutes < 1 OR p_target_minutes > 180 THEN
        RETURN jsonb_build_object('error','target_minutes_out_of_range','code','E_RANGE');
    END IF;

    v_target_seconds := p_target_minutes * 60;

    -- =============================================================
    -- 2. Resolve mode (auto dispatch)
    -- =============================================================
    IF p_mode = 'auto' THEN
        SELECT COUNT(*) INTO v_due_today
        FROM public.user_flashcards fc
        WHERE fc.user_id = p_user_id
          AND fc.language_id = p_language_id
          AND fc.due_date <= v_review_today;

        SELECT COUNT(*) INTO v_decayed_count
        FROM public.user_vocabulary_knowledge uvk
        LEFT JOIN public.user_flashcards fc
            ON fc.user_id = uvk.user_id AND fc.sense_id = uvk.sense_id
        WHERE uvk.user_id = p_user_id
          AND uvk.language_id = p_language_id
          AND public.bkt_effective_p_known(
                uvk.p_known, uvk.last_evidence_at,
                fc.stability, uvk.evidence_count
              ) < uvk.p_known - 0.05;

        SELECT COUNT(*) INTO v_active_ladder
        FROM public.user_word_ladder uwl
        JOIN public.dim_word_senses dws ON dws.id = uwl.sense_id
        JOIN public.dim_vocabulary  dv  ON dv.id  = dws.vocab_id
        WHERE uwl.user_id = p_user_id
          AND dv.language_id = p_language_id
          AND uwl.word_state IN ('active','gated','pre_mastery','relearning');

        v_mode := CASE
            WHEN (v_due_today + v_decayed_count) >= v_active_ladder
                 AND (v_due_today + v_decayed_count) > 0
                THEN 'maintenance'
            ELSE 'acquisition'
        END;
    ELSE
        v_mode := p_mode;
    END IF;

    -- =============================================================
    -- 3. Resolve theta
    -- =============================================================
    v_theta := COALESCE(p_user_theta,
                        public.irt_compute_user_theta(p_user_id, p_language_id),
                        0.0);

    -- =============================================================
    -- 4. Load mode weights
    -- =============================================================
    SELECT default_weights INTO v_weights
    FROM public.dim_practice_modes
    WHERE name = v_mode AND is_active;

    IF v_weights IS NULL THEN
        -- Should never happen given validation above, but defensive.
        RETURN jsonb_build_object('error','invalid_mode_weights','code','E_WEIGHTS');
    END IF;

    v_alpha := (v_weights->>'alpha')::numeric;
    v_beta  := (v_weights->>'beta' )::numeric;
    v_gamma := (v_weights->>'gamma')::numeric;
    v_delta := (v_weights->>'delta')::numeric;

    -- =============================================================
    -- 5. Run mode loop
    -- =============================================================
    IF v_mode = 'maintenance' THEN
        -- ----- Maintenance candidate pool + ranking -----
        FOR v_item IN
            WITH due_or_decayed AS (
                SELECT DISTINCT
                    uvk.sense_id,
                    fc.stability,
                    fc.due_date,
                    uvk.p_known
                FROM public.user_vocabulary_knowledge uvk
                LEFT JOIN public.user_flashcards fc
                    ON fc.user_id = uvk.user_id AND fc.sense_id = uvk.sense_id
                WHERE uvk.user_id = p_user_id
                  AND uvk.language_id = p_language_id
                  AND (
                      (fc.due_date IS NOT NULL AND fc.due_date <= v_review_today + 7)
                      OR public.bkt_effective_p_known(
                            uvk.p_known, uvk.last_evidence_at,
                            fc.stability, uvk.evidence_count
                         ) < uvk.p_known - 0.05
                  )
            ),
            top_senses AS (
                SELECT *,
                    GREATEST(0, (v_review_today - due_date)::numeric
                              / NULLIF(stability, 0)) AS urg
                FROM due_or_decayed
                ORDER BY urg DESC NULLS LAST, sense_id
                LIMIT 200
            ),
            candidates AS (
                SELECT
                    e.id            AS exercise_id,
                    e.word_sense_id AS sense_id,
                    e.exercise_type,
                    e.content_version,
                    e.ladder_level,
                    public.ladder_get_family(e.ladder_level) AS family,
                    COALESCE(det.expected_seconds_p50::int,
                             det.expected_seconds, 45) AS expected_seconds,
                    e.irt_discrimination,
                    e.irt_difficulty,
                    s.stability,
                    s.due_date,
                    s.p_known,
                    uwl.family_confidence,
                    uwl.current_ring,
                    uwl.word_state,
                    uwl.review_due_at,
                    uwl.last_exercised_family,
                    public.practice_unified_score(
                        e.irt_discrimination, e.irt_difficulty, v_theta,
                        s.p_known,
                        s.due_date, s.stability, v_review_today,
                        CASE WHEN uwl.sense_id IS NULL THEN 0
                             ELSE public.ladder_compute_priority(
                                uwl.current_ring, uwl.word_state,
                                uwl.family_confidence, uwl.review_due_at,
                                uwl.last_exercised_family
                             )
                        END,
                        v_alpha, v_beta, v_gamma, v_delta
                    ) AS score
                FROM top_senses s
                JOIN public.exercises e
                    ON e.word_sense_id = s.sense_id
                   AND e.language_id   = p_language_id
                   AND e.is_active
                   AND e.word_sense_id IS NOT NULL
                LEFT JOIN public.dim_exercise_types det
                    ON det.type_code = e.exercise_type
                LEFT JOIN public.user_word_ladder uwl
                    ON uwl.user_id = p_user_id AND uwl.sense_id = e.word_sense_id
            )
            SELECT * FROM candidates
            ORDER BY score DESC
            LIMIT 60                    -- enough to cover 60×30s = 30 min budget
        LOOP
            EXIT WHEN v_elapsed_seconds >= v_target_seconds;
            v_items := v_items || jsonb_build_object(
                'exercise_id',      v_item.exercise_id,
                'sense_id',         v_item.sense_id,
                'exercise_type',    v_item.exercise_type,
                'family',           v_item.family,
                'content_version',  v_item.content_version,
                'ladder_level',     v_item.ladder_level,
                'p_known',          v_item.p_known,
                'expected_seconds', v_item.expected_seconds,
                'mode',             'maintenance'
            );
            v_elapsed_seconds := v_elapsed_seconds + v_item.expected_seconds;
        END LOOP;

        -- ----- Fall-through: if Maintenance dry, continue in Acquisition -----
        IF v_elapsed_seconds < v_target_seconds AND jsonb_array_length(v_items) < 60 THEN
            -- Mark fall-through; continue inline with Acquisition logic
            v_mode := 'acquisition';
            -- Reload weights to Acquisition values for the fall-through items
            SELECT default_weights INTO v_weights
            FROM public.dim_practice_modes WHERE name = 'acquisition';
            v_alpha := (v_weights->>'alpha')::numeric;
            v_beta  := (v_weights->>'beta' )::numeric;
            v_gamma := (v_weights->>'gamma')::numeric;
            v_delta := (v_weights->>'delta')::numeric;
        END IF;
    END IF;

    -- =============================================================
    -- Acquisition path (also runs as fall-through from Maintenance)
    -- =============================================================
    IF v_mode = 'acquisition' AND v_elapsed_seconds < v_target_seconds THEN
        -- Count eligible words for the no-content check.
        -- FIX: scoped to p_language_id via dim_word_senses -> dim_vocabulary
        -- (user_word_ladder has no language of its own — a learner's ladder
        -- row in one language must not mask an empty ladder in another).
        SELECT COUNT(*) INTO v_eligible_count
        FROM public.user_word_ladder uwl
        JOIN public.dim_word_senses dws ON dws.id = uwl.sense_id
        JOIN public.dim_vocabulary  dv  ON dv.id  = dws.vocab_id
        WHERE uwl.user_id = p_user_id
          AND dv.language_id = p_language_id
          AND uwl.word_state IN ('new','active','gated','pre_mastery','relearning')
          AND COALESCE(uwl.review_due_at, '1970-01-01'::timestamptz) <= now();

        IF v_eligible_count = 0 THEN
            -- Caller (Python service) is expected to auto-subscribe from packs
            -- per R4.9 before calling, but if it didn't, we return a marker so
            -- the FE can show the "select a pack" nudge.
            IF jsonb_array_length(v_items) = 0 THEN
                v_no_content := 'no_eligible_words';
            END IF;
        ELSE
            -- Word-anchored loop: top 50 by priority
            FOR v_word IN
                SELECT
                    uwl.sense_id,
                    uwl.current_ring,
                    uwl.word_state,
                    uwl.family_confidence,
                    uwl.review_due_at,
                    uwl.last_exercised_family,
                    uwl.active_levels,
                    public.ladder_compute_priority(
                        uwl.current_ring, uwl.word_state,
                        uwl.family_confidence, uwl.review_due_at,
                        uwl.last_exercised_family
                    ) AS priority
                FROM public.user_word_ladder uwl
                WHERE uwl.user_id = p_user_id
                  AND uwl.word_state IN ('new','active','gated','pre_mastery','relearning')
                  AND COALESCE(uwl.review_due_at, '1970-01-01'::timestamptz) <= now()
                  AND EXISTS (
                    SELECT 1 FROM public.exercises e
                    WHERE e.word_sense_id = uwl.sense_id
                      AND e.language_id = p_language_id
                      AND e.is_active
                      AND e.ladder_level IS NOT NULL
                  )
                ORDER BY priority DESC
                LIMIT 50
            LOOP
                EXIT WHEN v_elapsed_seconds >= v_target_seconds;

                -- For each ring-required family, pick the top-scored item
                FOREACH v_fam IN ARRAY
                    public.ladder_ring_families(
                        v_word.current_ring,
                        COALESCE(v_word.active_levels, v_active_levels)
                    )
                LOOP
                    EXIT WHEN v_elapsed_seconds >= v_target_seconds;

                    SELECT
                        e.id        AS exercise_id,
                        e.exercise_type,
                        e.content_version,
                        e.ladder_level,
                        public.ladder_get_family(e.ladder_level) AS family,
                        COALESCE(det.expected_seconds_p50::int,
                                 det.expected_seconds, 45) AS expected_seconds,
                        uvk.p_known
                    INTO v_item
                    FROM public.exercises e
                    LEFT JOIN public.dim_exercise_types det
                        ON det.type_code = e.exercise_type
                    LEFT JOIN public.user_vocabulary_knowledge uvk
                        ON uvk.user_id = p_user_id AND uvk.sense_id = e.word_sense_id
                    LEFT JOIN public.user_flashcards fc
                        ON fc.user_id = p_user_id AND fc.sense_id = e.word_sense_id
                    WHERE e.word_sense_id = v_word.sense_id
                      AND e.language_id   = p_language_id
                      AND e.is_active
                      AND e.ladder_level IS NOT NULL
                      AND public.ladder_get_family(e.ladder_level) = v_fam
                      -- Anti-repetition: not seen today
                      AND NOT EXISTS (
                        SELECT 1 FROM public.user_exercise_history ueh
                        WHERE ueh.user_id = p_user_id
                          AND ueh.exercise_id = e.id
                          AND ueh.session_date = v_today
                      )
                    ORDER BY public.practice_unified_score(
                        e.irt_discrimination, e.irt_difficulty, v_theta,
                        uvk.p_known,
                        fc.due_date, fc.stability, v_review_today,
                        v_word.priority,
                        v_alpha, v_beta, v_gamma, v_delta
                    ) DESC,
                    RANDOM()
                    LIMIT 1;

                    IF FOUND THEN
                        v_items := v_items || jsonb_build_object(
                            'exercise_id',      v_item.exercise_id,
                            'sense_id',         v_word.sense_id,
                            'exercise_type',    v_item.exercise_type,
                            'family',           v_item.family,
                            'content_version',  v_item.content_version,
                            'ladder_level',     v_item.ladder_level,
                            'p_known',          v_item.p_known,
                            'expected_seconds', v_item.expected_seconds,
                            'mode',             'acquisition'
                        );
                        v_elapsed_seconds := v_elapsed_seconds + v_item.expected_seconds;
                    END IF;
                END LOOP;

                -- Gate marker: word is gated → caller dispatches via
                -- /api/vocab-dojo/gate with the appropriate gate_name.
                IF v_word.word_state = 'gated'
                   AND v_elapsed_seconds < v_target_seconds THEN
                    v_items := v_items || jsonb_build_object(
                        'is_gate_marker',  true,
                        'gate_name',
                            CASE WHEN v_word.current_ring = 2 THEN 'gate_a'
                                 WHEN v_word.current_ring = 3 THEN 'gate_b'
                                 ELSE 'unknown' END,
                        'sense_id',        v_word.sense_id,
                        'expected_seconds', 180,
                        'mode',            'acquisition'
                    );
                    v_elapsed_seconds := v_elapsed_seconds + 180;
                END IF;

                -- Stress-test marker: word is in pre_mastery → caller
                -- dispatches via /api/vocab-dojo/stress-test.
                IF v_word.word_state = 'pre_mastery'
                   AND v_elapsed_seconds < v_target_seconds THEN
                    v_items := v_items || jsonb_build_object(
                        'is_stress_test_marker', true,
                        'sense_id',              v_word.sense_id,
                        'expected_seconds',      420,
                        'mode',                  'acquisition'
                    );
                    v_elapsed_seconds := v_elapsed_seconds + 420;
                END IF;
            END LOOP;
        END IF;
    END IF;

    -- =============================================================
    -- 6. Assemble final response
    -- =============================================================
    IF jsonb_array_length(v_items) = 0 AND v_no_content IS NULL THEN
        v_no_content := 'all_complete';
    END IF;

    RETURN jsonb_build_object(
        'session_id',       v_session_id,
        'mode_requested',   p_mode,
        'mode_resolved',    v_mode,
        'target_minutes',   p_target_minutes,
        'elapsed_seconds',  v_elapsed_seconds,
        'items',            v_items,
        'no_content_reason', v_no_content
    );
END $function$;

REVOKE ALL ON FUNCTION public.get_practice_session(uuid, smallint, text, smallint, numeric, boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_practice_session(uuid, smallint, text, smallint, numeric, boolean) TO service_role;

-- ---------------------------------------------------------------------------
-- public.compute_weekly_plan_load_signals(uuid, smallint, date)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.compute_weekly_plan_load_signals(p_user_id uuid, p_language_id smallint, p_week_start date)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_today       date := public.review_today();
    v_28d_ago     timestamptz := NOW() - INTERVAL '28 days';
    v_14d_ago     timestamptz := NOW() - INTERVAL '14 days';
    v_7d_ago      timestamptz := NOW() - INTERVAL '7 days';
    v_user_mean   numeric;
    v_skills      jsonb;
    v_ladder      jsonb;
    v_fsrs        jsonb;
    v_bkt         jsonb;
    v_prior       jsonb;
BEGIN
    ---------------------------------------------------------------------
    -- Per-skill ELO + recent first-attempt counts.
    -- Each row of user_skill_ratings (per test_type) contributes one
    -- per-skill object keyed by dim_test_types.type_code.
    ---------------------------------------------------------------------
    SELECT AVG(elo_rating) INTO v_user_mean
    FROM public.user_skill_ratings
    WHERE user_id = p_user_id AND language_id = p_language_id;

    SELECT COALESCE(jsonb_object_agg(skill_data.type_code, skill_data.payload), '{}'::jsonb)
    INTO v_skills
    FROM (
        SELECT
            dtt.type_code,
            jsonb_build_object(
                'elo', usr.elo_rating,
                'tests_taken', usr.tests_taken,
                'first_attempt_correct_28d', COALESCE(att.fa_correct, 0),
                'first_attempt_wrong_28d',   COALESCE(att.fa_wrong,   0)
            ) AS payload
        FROM public.user_skill_ratings usr
        JOIN public.dim_test_types dtt ON dtt.id = usr.test_type_id
        LEFT JOIN LATERAL (
            SELECT
                COUNT(*) FILTER (WHERE percentage >= 70) AS fa_correct,
                COUNT(*) FILTER (WHERE percentage <  70) AS fa_wrong
            FROM public.test_attempts ta
            WHERE ta.user_id = p_user_id
              AND ta.language_id = p_language_id
              AND ta.test_type_id = usr.test_type_id
              AND ta.is_first_attempt
              AND ta.created_at >= v_28d_ago
        ) att ON TRUE
        WHERE usr.user_id = p_user_id
          AND usr.language_id = p_language_id
    ) skill_data;

    ---------------------------------------------------------------------
    -- Ladder signals — language filter via dim_word_senses → dim_vocabulary.
    --
    -- IMPORTANT SCHEMA NOTE (patched 2026-05-22 during verification):
    -- user_word_ladder has NO language_id, NO last_exercised_at, NO
    -- created_at columns. Language must be derived via the sense → vocab
    -- join. updated_at is the recency proxy. "new_intro_7d" uses
    -- updated_at + total_attempts=0 (rows just seeded with no drill yet).
    --
    -- subscribed   : any uwl row for this user × this language.
    -- stagnant_14d : updated_at older than 14 days OR NULL.
    -- active_count : word in active learning states.
    -- stuck_count  : ≥3 consecutive_failures, OR active >14 days stale.
    -- new_intro_7d : updated within last 7 days AND total_attempts = 0.
    ---------------------------------------------------------------------
    WITH lang_ladder AS (
        SELECT uwl.*
        FROM public.user_word_ladder uwl
        JOIN public.dim_word_senses dws ON dws.id = uwl.sense_id
        JOIN public.dim_vocabulary   dv  ON dv.id  = dws.vocab_id
        WHERE uwl.user_id = p_user_id
          AND dv.language_id = p_language_id
    )
    SELECT jsonb_build_object(
        'subscribed',   (SELECT COUNT(*) FROM lang_ladder),
        'stagnant_14d', (SELECT COUNT(*) FROM lang_ladder
                         WHERE updated_at IS NULL OR updated_at < v_14d_ago),
        'active_count', (SELECT COUNT(*) FROM lang_ladder
                         WHERE word_state IN ('active','gated','pre_mastery','relearning')),
        'stuck_count',  (SELECT COUNT(*) FROM lang_ladder
                         WHERE consecutive_failures >= 3
                            OR (updated_at IS NOT NULL
                                AND updated_at < v_14d_ago
                                AND word_state IN ('active','gated','pre_mastery'))),
        'new_intro_7d', (SELECT COUNT(*) FROM lang_ladder
                         WHERE updated_at IS NOT NULL
                           AND updated_at >= v_7d_ago
                           AND total_attempts = 0)
    ) INTO v_ladder;

    ---------------------------------------------------------------------
    -- FSRS signals.
    -- lapses_28d   — sum of lapses on flashcards touched in the window.
    -- reviews_28d  — count of reviews in the window (approx via last_review).
    -- due_7d       — cards with due_date in next 7 days.
    ---------------------------------------------------------------------
    SELECT jsonb_build_object(
        'lapses_28d',
            (SELECT COALESCE(SUM(lapses), 0) FROM public.user_flashcards
             WHERE user_id = p_user_id AND language_id = p_language_id
               AND last_review >= v_28d_ago::date),
        'reviews_28d',
            (SELECT COALESCE(SUM(reps), 0) FROM public.user_flashcards
             WHERE user_id = p_user_id AND language_id = p_language_id
               AND last_review >= v_28d_ago::date),
        'due_7d_lookahead',
            (SELECT COUNT(*) FROM public.user_flashcards
             WHERE user_id = p_user_id AND language_id = p_language_id
               AND due_date <= v_today + 7)
    ) INTO v_fsrs;

    ---------------------------------------------------------------------
    -- BKT signals.
    -- known_count_p80 — senses with p_known ≥ 0.80 (denominator for decay
    --                   pressure).
    -- decayed_count   — senses where effective_p_known < raw - 0.05.
    ---------------------------------------------------------------------
    SELECT jsonb_build_object(
        'known_count_p80',
            (SELECT COUNT(*) FROM public.user_vocabulary_knowledge
             WHERE user_id = p_user_id AND language_id = p_language_id
               AND p_known >= 0.80),
        'decayed_count',
            (SELECT COUNT(*)
             FROM public.user_vocabulary_knowledge uvk
             LEFT JOIN public.user_flashcards fc
                ON fc.user_id = uvk.user_id AND fc.sense_id = uvk.sense_id
             WHERE uvk.user_id = p_user_id
               AND uvk.language_id = p_language_id
               AND public.bkt_effective_p_known(
                     uvk.p_known, uvk.last_evidence_at,
                     fc.stability, uvk.evidence_count
                   ) < uvk.p_known - 0.05)
    ) INTO v_bkt;

    ---------------------------------------------------------------------
    -- Prior week (for carry-over decay).
    ---------------------------------------------------------------------
    SELECT to_jsonb(wps.*) INTO v_prior
    FROM public.weekly_plan_states wps
    WHERE user_id = p_user_id
      AND language_id = p_language_id
      AND week_start_date = p_week_start - 7;

    RETURN jsonb_build_object(
        'user_id',       p_user_id,
        'language_id',   p_language_id,
        'week_start',    p_week_start,
        'user_mean_elo', COALESCE(v_user_mean, 1200),
        'skills',        COALESCE(v_skills, '{}'::jsonb),
        'ladder',        v_ladder,
        'fsrs',          v_fsrs,
        'bkt',           v_bkt,
        'prior_week',    v_prior
    );
END $function$;

REVOKE ALL ON FUNCTION public.compute_weekly_plan_load_signals(uuid, smallint, date) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.compute_weekly_plan_load_signals(uuid, smallint, date) TO service_role;

-- ---------------------------------------------------------------------------
-- public.review_governor_state(uuid, smallint, date)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.review_governor_state(p_user_id uuid, p_language_id smallint, p_date date)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    c_threshold_days constant numeric := 1.0;    -- Config.REVIEW_BACKLOG_THRESHOLD_DAYS
    c_floor_min      constant numeric := 3.0;    -- Config.REVIEW_ALLOWANCE_FLOOR_MIN
    v_tz           text;
    v_excluded     text[] := '{}'::text[];
    v_local_start  timestamptz;
    v_local_next   timestamptz;
    v_overdue      int := 0;
    v_due          int := 0;
    v_item_sec     numeric;
    v_review_tgt   numeric;
    v_threshold    numeric;
    v_over_min     numeric;
    v_due_min      numeric;
BEGIN
    SELECT public.resolve_plan_timezone(usp.timezone),
           COALESCE(usp.excluded_modules, '{}'::text[])
      INTO v_tz, v_excluded
      FROM public.user_study_plans usp
     WHERE usp.user_id = p_user_id AND usp.language_id = p_language_id;
    v_tz := COALESCE(v_tz, 'UTC');
    v_excluded := COALESCE(v_excluded, '{}'::text[]);

    v_item_sec := public.review_item_seconds(p_user_id, p_language_id);

    IF 'practice' = ANY(v_excluded) THEN
        RETURN jsonb_build_object(
            'overdue_items', 0, 'overdue_minutes', 0,
            'due_items', 0, 'due_minutes', 0,
            'threshold_minutes', 0, 'item_seconds', v_item_sec,
            'level', 'normal');
    END IF;

    v_local_start := p_date::timestamp AT TIME ZONE v_tz;
    v_local_next  := (p_date + 1)::timestamp AT TIME ZONE v_tz;

    WITH src AS (
        SELECT uf.sense_id, (uf.due_date < public.review_today()) AS is_overdue, 1 AS items
          FROM public.user_flashcards uf
         WHERE uf.user_id = p_user_id
           AND uf.language_id = p_language_id
           AND uf.due_date IS NOT NULL
           AND uf.due_date <= public.review_today()
        UNION ALL
        SELECT uwl.sense_id, (uwl.review_due_at < v_local_start) AS is_overdue, 1 AS items
          FROM public.user_word_ladder uwl
          JOIN public.dim_word_senses dws ON dws.id = uwl.sense_id
          JOIN public.dim_vocabulary  dv  ON dv.id  = dws.vocab_id
         WHERE uwl.user_id = p_user_id
           AND dv.language_id = p_language_id
           AND uwl.review_due_at IS NOT NULL
           AND uwl.review_due_at < v_local_next
        UNION ALL
        -- New-word drill reviews (sessions 2-4, restarts, overloads): one row
        -- per due intro word, weighted by its expected items
        -- (services/intro_drill.INTRO_STAGE_ITEMS_EST). Brand-new stage-1
        -- words are new words, not reviews, and are not counted.
        SELECT uwl.sense_id, (uwl.intro_due_date < p_date) AS is_overdue,
               CASE uwl.intro_stage WHEN 2 THEN 4 WHEN 3 THEN 3 WHEN 4 THEN 3 ELSE 7 END AS items
          FROM public.user_word_ladder uwl
          JOIN public.dim_word_senses dws ON dws.id = uwl.sense_id
          JOIN public.dim_vocabulary  dv  ON dv.id  = dws.vocab_id
         WHERE uwl.user_id = p_user_id
           AND dv.language_id = p_language_id
           AND uwl.word_state = 'intro'
           AND uwl.intro_due_date <= p_date
           AND (uwl.intro_stage >= 2
                OR uwl.intro_history @> '[{"event": "restart"}]'::jsonb
                OR uwl.intro_history @> '[{"event": "overload"}]'::jsonb)
    ), per_sense AS (
        SELECT sense_id, bool_or(is_overdue) AS is_overdue, MAX(items) AS items
          FROM src GROUP BY sense_id
    )
    SELECT COALESCE(SUM(items), 0)::int, COALESCE(SUM(items) FILTER (WHERE is_overdue), 0)::int
      INTO v_due, v_overdue
      FROM per_sense;

    SELECT wps.review_target_minutes::numeric
      INTO v_review_tgt
      FROM public.weekly_plan_states wps
     WHERE wps.user_id = p_user_id
       AND wps.language_id = p_language_id
       AND wps.week_start_date = public.week_start_for(p_date);

    v_threshold := c_threshold_days * GREATEST(c_floor_min, COALESCE(v_review_tgt, 0) / 7.0);
    v_over_min  := v_overdue * v_item_sec / 60.0;
    v_due_min   := v_due     * v_item_sec / 60.0;

    RETURN jsonb_build_object(
        'overdue_items',     v_overdue,
        'overdue_minutes',   ROUND(v_over_min, 2),
        'due_items',         v_due,
        'due_minutes',       ROUND(v_due_min, 2),
        'threshold_minutes', ROUND(v_threshold, 2),
        'item_seconds',      v_item_sec,
        'level',             public.review_governor_level(v_over_min, v_threshold));
END
$function$;

REVOKE ALL ON FUNCTION public.review_governor_state(uuid, smallint, date) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.review_governor_state(uuid, smallint, date) TO service_role;

-- ---------------------------------------------------------------------------
-- public.build_daily_session(uuid, smallint, date)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.build_daily_session(p_user_id uuid, p_language_id smallint, p_date date DEFAULT CURRENT_DATE)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_week_start     date;
    v_state          public.weekly_plan_states%ROWTYPE;
    v_plan           public.user_study_plans%ROWTYPE;
    v_weekday_idx    int;
    v_weekday_w      numeric;
    v_today_budget   numeric;
    -- TASK-732: today's budget split by side, replacing the single
    -- v_today_budget/v_upper_cap pair the combined loop used to share.
    v_test_minutes_total     numeric;
    v_practice_minutes_total numeric;
    v_test_budget            numeric;
    v_practice_budget        numeric;
    v_upper_cap_test         numeric;
    v_upper_cap_practice     numeric;
    v_used_min_test          numeric := 0;
    v_used_min_practice      numeric := 0;
    v_used_min       numeric := 0;
    v_used_min_hyd   numeric := 0;
    v_objective      numeric := 0;
    v_skills_today   text[] := ARRAY[]::text[];
    v_test_ids       jsonb := '[]'::jsonb;
    v_requested_counts jsonb := '{}'::jsonb;
    v_hydrated_counts  jsonb := '{}'::jsonb;
    v_replay_counts    jsonb := '{}'::jsonb;
    v_surface_counts   jsonb := '{}'::jsonb;
    v_maint_min      int := 0;
    v_acq_min        int := 0;
    v_load_id        bigint;
    v_cand           RECORD;
    v_test           RECORD;
    v_spacing_cost   numeric;
    v_hydrated       int;
    v_dict_difficulty int;
    c_alpha_m        constant numeric := 0.02;
    c_alpha_a        constant numeric := 0.02;
    c_gamma          constant numeric := 0.15;
    c_replay_min_age_days constant int := 7;   -- TASK-702: replay age floor (N)
    -- TASK-714 / ADR-021. Plannable but NOT dim_test_types rows and never
    -- resolvable to an ELO-rated `tests` row. Adding a code here without also
    -- seeding test_time_estimate budgets it at the silent ELSE 5.0.
    c_surface_skills constant text[] := ARRAY['flashcards','dual_translation'];
    -- TASK-714: cards per 'flashcards' slot. Mirrors
    -- routes/study_session.py::_FLASHCARD_CARDS_PER_BLOCK and the 7.0-minute
    -- seed in test_time_estimate — change one, change all three.
    c_cards_per_block constant int := 15;
    -- session-modules (TASK-865)
    v_excluded       text[];
    -- session-budget (TASK-865 / ADR-033)
    v_scope          text;
    v_practice_in    boolean;
    v_npd            int;
    v_quota          int;
    v_new_eff        int;
    v_mpnw           numeric;
    v_gov            jsonb;
    v_level          text;
    v_due_min        numeric := 0;
    v_r_main         numeric := 0;
    v_s_words        int := 0;
    v_a_main         numeric := 0;
    v_returned       numeric := 0;
    v_local_midnight timestamptz;
    v_lw             jsonb;
    v_unstarted      int := 0;
    v_started_today  int := 0;
    v_shortfall      int := 0;
    v_prior_shortfall int := 0;
    v_prior_checked  boolean := false;
    v_prior_checked_e int;
BEGIN
    v_week_start := public.week_start_for(p_date);

    SELECT * INTO v_plan
    FROM public.user_study_plans
    WHERE user_id = p_user_id AND language_id = p_language_id;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'error', 'no_user_study_plan',
            'code',  'E_NOPLAN',
            'hint',  'Call apply_study_plan_template first or fall back to legacy daily-load.'
        );
    END IF;

    SELECT * INTO v_state
    FROM public.weekly_plan_states
    WHERE user_id = p_user_id
      AND language_id = p_language_id
      AND week_start_date = v_week_start;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'error', 'no_weekly_plan',
            'code',  'E_NOWEEK',
            'week_start', v_week_start,
            'hint',  'compute_weekly_plan has not run for this user/week. Caller should retry after Tier B fires.'
        );
    END IF;

    v_weekday_idx := EXTRACT(ISODOW FROM p_date)::int - 1;
    v_weekday_w   := COALESCE(
        (v_plan.weekday_shape->>v_weekday_idx)::numeric, 1.0
    );
    v_today_budget := v_state.total_weekly_minutes::numeric * v_weekday_w / 7;

    -- session-modules: excluded modules (never NULL).
    v_excluded := COALESCE(v_plan.excluded_modules, '{}'::text[]);

    -- session-budget: scope comes from the state row (consistent with its own totals); the
    -- new-word quota comes live from the plan so a stale state never hides a setting.
    v_scope       := COALESCE(v_state.budget_scope, 'tests_and_review');
    v_practice_in := (v_scope = 'tests_and_review' AND NOT ('practice' = ANY(v_excluded)));
    v_npd         := COALESCE(v_plan.new_words_per_day, 0);
    v_quota       := public.new_words_for_day(v_npd, v_weekday_w);                 -- Q
    v_mpnw        := public.new_word_minutes(p_language_id);
    v_gov         := public.review_governor_state(p_user_id, p_language_id, p_date);
    v_level       := CASE WHEN 'practice' = ANY(v_excluded) THEN 'normal'
                          ELSE COALESCE(v_gov->>'level', 'normal') END;
    v_new_eff     := public.new_words_effective(v_quota, v_level);                 -- E
    v_due_min     := CASE WHEN 'practice' = ANY(v_excluded) THEN 0
                          ELSE COALESCE((v_gov->>'due_minutes')::numeric, 0) END;

    -- session-budget: prior supply check (same-day rebuild only). Ladder intake writes
    -- new_words_supply_checked = true and the unmet new_words_shortfall through
    -- set_new_words_shortfall; read them BEFORE the row is replaced below. An unchecked
    -- prior row contributes 0.
    SELECT COALESCE((dtl.daily_session_targets->>'new_words_supply_checked')::boolean, false),
           COALESCE((dtl.daily_session_targets->>'new_words_shortfall')::int, 0),
           NULLIF(dtl.daily_session_targets->>'new_words_supply_checked_e', '')::int
      INTO v_prior_checked, v_prior_shortfall, v_prior_checked_e
      FROM public.daily_test_loads dtl
     WHERE dtl.user_id = p_user_id
       AND dtl.language_id = p_language_id
       AND dtl.load_date = p_date;
    IF NOT FOUND OR NOT COALESCE(v_prior_checked, false) THEN
        v_prior_checked   := false;
        v_prior_shortfall := 0;
    END IF;
    -- Review fix: a supply check is valid only for the E it was made under. A mid-day quota
    -- change leaves the stored shortfall stale, so drop it (NULL E = row written before the
    -- key existed: trusted).
    IF v_prior_checked AND v_prior_checked_e IS NOT NULL AND v_prior_checked_e <> v_new_eff THEN
        v_prior_checked   := false;
        v_prior_shortfall := 0;
        v_prior_checked_e := NULL;
    END IF;

    -- TASK-715: the learner's EXPECTED dictation difficulty — the tier whose
    -- seeded initial_elo sits closest to their current dictation ELO. Used to
    -- size dictation slots during BUDGETING, before any concrete test is
    -- known. Defaults to the 1200-ELO tier for an unrated learner.
    SELECT ct.difficulty_max INTO v_dict_difficulty
    FROM public.dim_complexity_tiers ct
    ORDER BY ABS(
        ct.initial_elo - COALESCE(
            (SELECT usr.elo_rating
             FROM public.user_skill_ratings usr
             JOIN public.dim_test_types dtt ON dtt.id = usr.test_type_id
             WHERE usr.user_id = p_user_id
               AND usr.language_id = p_language_id
               AND dtt.type_code = 'dictation'),
            1200
        )
    )
    LIMIT 1;

    -- TASK-732: size each side's "this week still wants X minutes" total
    -- independently of the (unreconciled) weekly_ceiling clamp upstream, then
    -- split today's budget proportionally. v_test_minutes_total mirrors
    -- services/study_plan_service.py's own test_minutes sum (same skills,
    -- same test_time_estimate) so the ratio reflects the real, current
    -- target_counts rather than a stale weekly snapshot.
    SELECT COALESCE(SUM(
        public.test_time_estimate(
            tc.skill_key,
            CASE WHEN tc.skill_key = 'dictation' THEN v_dict_difficulty END
        ) * GREATEST(0,
            tc.target_text::int - COALESCE((v_state.completed_counts->>tc.skill_key)::int, 0)
        )
    ), 0)
      INTO v_test_minutes_total
    FROM jsonb_each_text(v_state.target_counts) AS tc(skill_key, target_text)
    WHERE tc.skill_key <> ALL(v_excluded);   -- session-modules

    -- session-budget: the in-budget practice pool exists only when v_practice_in
    -- (budget_scope = 'tests_and_review' AND 'practice' not excluded). This subsumes the
    -- session-modules `IF 'practice' = ANY(v_excluded)` wrap.
    v_practice_minutes_total := CASE WHEN v_practice_in THEN GREATEST(0,
        ROUND(v_state.practice_target_minutes::numeric)::int
        - v_state.practice_completed_maint_min
        - v_state.practice_completed_acq_min
    ) ELSE 0 END;

    IF v_test_minutes_total + v_practice_minutes_total > 0 THEN
        v_practice_budget := v_today_budget * v_practice_minutes_total
                              / (v_test_minutes_total + v_practice_minutes_total);
    ELSE
        v_practice_budget := 0;
    END IF;
    v_test_budget        := v_today_budget - v_practice_budget;

    -- session-budget: "started" per ADR-033 / Quota semantics. Computed BEFORE v_s_words:
    -- words already started today must not be re-planned by a same-day rebuild.
    v_local_midnight := (p_date::timestamp AT TIME ZONE public.resolve_plan_timezone(v_plan.timezone));
    v_lw            := public.ladder_new_word_state(p_user_id, p_language_id, v_local_midnight);
    v_unstarted     := COALESCE((v_lw->>'unstarted')::int, 0);          -- U
    v_started_today := COALESCE((v_lw->>'started_today')::int, 0);      -- ST

    -- session-budget: the practice side is assigned DIRECTLY (reviews first, then whole new
    -- words, then the rest goes back to tests); the practice candidate INSERTs and the
    -- practice greedy loop no longer exist. "Reviews first, new words second" is a priority
    -- order, not a value ranking.
    -- 1. due reviews first (due = overdue + due today, in minutes)
    v_r_main  := CASE WHEN v_practice_in THEN LEAST(v_practice_budget, v_due_min) ELSE 0 END;
    -- 2. then new words, as many whole words as fit in what is left of the share; after a
    --    supply check, never plan more than the words that can actually be served
    v_s_words := CASE WHEN v_practice_in AND v_new_eff > 0 AND v_mpnw > 0
                      THEN GREATEST(0, LEAST(
                                 GREATEST(0, v_new_eff - v_started_today),
                                 GREATEST(0, v_new_eff - v_started_today - v_prior_shortfall),
                                 FLOOR((v_practice_budget - v_r_main) / v_mpnw)::int))
                      ELSE 0 END;
    v_a_main  := v_s_words * v_mpnw;
    -- 3. unused share minutes return to tests (the budget is never left empty)
    v_returned    := GREATEST(0, v_practice_budget - v_r_main - v_a_main);
    v_test_budget := v_test_budget + v_returned;
    v_maint_min   := ROUND(v_r_main)::int;   -- runner reads practice_maintenance_min
    v_acq_min     := ROUND(v_a_main)::int;   -- runner reads practice_acquisition_min

    -- session-budget: shortfall seed = words still to admit at build time (ladder intake
    -- overwrites it with the final unmet count). The ST term nets out words already started
    -- today (computed above, before v_s_words).
    v_shortfall     := GREATEST(0, v_new_eff - (v_unstarted + v_started_today));
    IF v_prior_checked THEN
        v_shortfall := v_prior_shortfall;   -- a real supply check outranks the seed
    END IF;

    v_upper_cap_test      := v_test_budget * 1.5;
    v_upper_cap_practice  := 0;   -- unused since the practice greedy loop was removed

    DROP TABLE IF EXISTS pg_temp.last3_skills;
    CREATE TEMP TABLE pg_temp.last3_skills (
        skill text NOT NULL
    ) ON COMMIT DROP;

    INSERT INTO pg_temp.last3_skills (skill)
    SELECT dtt.type_code
    FROM public.test_attempts ta
    JOIN public.dim_test_types dtt ON dtt.id = ta.test_type_id
    WHERE ta.user_id = p_user_id
      AND ta.language_id = p_language_id
      AND ta.created_at >= (p_date - 3)::timestamptz
      AND ta.created_at <  (p_date)::timestamptz;

    DROP TABLE IF EXISTS pg_temp.candidates;
    CREATE TEMP TABLE pg_temp.candidates (
        seq            serial,
        kind           text NOT NULL,
        skill          text,
        mins           numeric NOT NULL,
        per_min_value  numeric NOT NULL
    ) ON COMMIT DROP;

    -- One candidate row per still-outstanding slot of every plannable skill.
    -- TASK-714: surface skills get kind='surface' so the hydration loop below
    -- can route them away from get_recommended_tests; the BUDGET loop treats
    -- both kinds identically, which is the whole point — they compete for the
    -- same minutes (now the test/surface side's minutes specifically —
    -- TASK-732).
    -- TASK-715: dictation is sized through the 2-arg, tier-aware estimate.
    INSERT INTO pg_temp.candidates (kind, skill, mins, per_min_value)
    SELECT CASE WHEN skill_key = ANY(c_surface_skills) THEN 'surface' ELSE 'test' END,
           skill_key,
           public.test_time_estimate(
               skill_key,
               CASE WHEN skill_key = 'dictation' THEN v_dict_difficulty END
           ),
           COALESCE((v_state.skill_values->>skill_key)::numeric, 0.10)
             / NULLIF(public.test_time_estimate(
                   skill_key,
                   CASE WHEN skill_key = 'dictation' THEN v_dict_difficulty END
               ), 0)
    FROM jsonb_each_text(v_state.target_counts) AS tc(skill_key, target_text),
         generate_series(1,
           GREATEST(0,
             target_text::int
             - COALESCE((v_state.completed_counts->>skill_key)::int, 0)
           )
         )
    WHERE skill_key <> ALL(v_excluded);   -- session-modules

    -- session-budget: the 'maint' / 'acq' candidate INSERTs are deleted (practice side is
    -- assigned directly above; no 10-minute chunking, no extra-pool candidates).

    -- Per-skill BUDGETED test-slot counts (requested_counts) are recorded in the
    -- SAME greedy pass that computes the budget totals (TASK-710). Created before
    -- the loop so the selection can populate it inline; the TASK-705 carry-over
    -- and TASK-704 retry blocks below still consume a fully-populated table.
    DROP TABLE IF EXISTS pg_temp.skill_counts;
    CREATE TEMP TABLE pg_temp.skill_counts (
        skill text PRIMARY KEY,
        count int NOT NULL
    ) ON COMMIT DROP;

    -- TASK-714: same shape, for surface skills. Kept separate from
    -- skill_counts so the hydration loop, the retry/replay guards and the
    -- chosen_tests bookkeeping below stay exactly as TASK-702/704/705 left
    -- them — a surface can never be mistaken for a test row.
    DROP TABLE IF EXISTS pg_temp.surface_budget;
    CREATE TEMP TABLE pg_temp.surface_budget (
        skill text PRIMARY KEY,
        count int NOT NULL
    ) ON COMMIT DROP;

    -- TASK-732: test/surface candidates now rank ONLY against each other,
    -- bounded by v_test_budget/v_upper_cap_test instead of the shared
    -- v_today_budget/v_upper_cap. Ordering and spacing-cost logic unchanged.
    FOR v_cand IN
        SELECT * FROM pg_temp.candidates
        WHERE kind IN ('test', 'surface')
        ORDER BY per_min_value DESC, seq
    LOOP
        EXIT WHEN v_used_min_test >= v_test_budget;
        CONTINUE WHEN v_used_min_test + v_cand.mins > v_upper_cap_test;

        v_spacing_cost := 0;
        IF NOT (v_cand.skill = ANY(v_skills_today)) THEN
            SELECT c_gamma
                 * COALESCE((SELECT COUNT(*)::numeric FROM pg_temp.last3_skills
                             WHERE skill = v_cand.skill), 0)
                 / 3.0
              INTO v_spacing_cost;

            IF v_spacing_cost > (v_cand.per_min_value * v_cand.mins) THEN
                CONTINUE;
            END IF;
        END IF;

        IF v_cand.kind = 'test' THEN
            IF NOT (v_cand.skill = ANY(v_skills_today)) THEN
                v_skills_today := array_append(v_skills_today, v_cand.skill);
            END IF;
            -- Record the budgeted slot for this skill in-pass (formerly a second,
            -- byte-identical loop over the same candidate order — F12).
            INSERT INTO pg_temp.skill_counts (skill, count) VALUES (v_cand.skill, 1)
            ON CONFLICT (skill) DO UPDATE SET count = pg_temp.skill_counts.count + 1;
        ELSE -- 'surface'
            IF NOT (v_cand.skill = ANY(v_skills_today)) THEN
                v_skills_today := array_append(v_skills_today, v_cand.skill);
            END IF;
            INSERT INTO pg_temp.surface_budget (skill, count) VALUES (v_cand.skill, 1)
            ON CONFLICT (skill) DO UPDATE SET count = pg_temp.surface_budget.count + 1;
        END IF;
        v_used_min_test := v_used_min_test + v_cand.mins;
        v_objective      := v_objective + (v_cand.per_min_value * v_cand.mins)
                                         - v_spacing_cost;
    END LOOP;

    -- session-budget: the TASK-732 practice greedy loop is deleted (see the direct
    -- assignment above). The practice minutes are v_maint_min + v_acq_min.
    v_used_min_practice := v_maint_min + v_acq_min;
    v_used_min := v_used_min_test + v_used_min_practice;

    DROP TABLE IF EXISTS pg_temp.chosen_tests;
    CREATE TEMP TABLE pg_temp.chosen_tests (
        test_id             uuid NOT NULL,
        skill               text NOT NULL,
        slot_type           text NOT NULL DEFAULT 'new',
        original_percentage numeric,         -- populated for slot_type='retry' only
        is_completed        boolean NOT NULL DEFAULT false  -- TASK-705: retained same-day completion
    ) ON COMMIT DROP;

    -- ---------------------------------------------------------------
    -- TASK-705 — same-day re-entrancy. Before rebuilding today's plan, carry
    -- over every slot the learner already COMPLETED today: any element of the
    -- prior row's test_ids whose test_id is present in the prior completed_test_ids.
    -- Each is re-inserted into chosen_tests with its ORIGINAL slot_type /
    -- original_percentage and is_completed=true, and its skill's budgeted count is
    -- decremented so only the still-incomplete slots get re-resolved below
    -- (retained-completed + fresh == today's budget, so used_minutes stays sane).
    -- Seeding these first also excludes them from retry/replay selection (both
    -- guard against chosen_tests) and preserves the completed_test_ids subset test_ids
    -- invariant, since the ON CONFLICT branch keeps completed_test_ids as-is.
    -- No-op on the first call of the day (no prior row -> NULL).
    --
    -- Surfaces need no equivalent: their completion lives in completed_blocks,
    -- which the ON CONFLICT branch never touches, and the runner derives
    -- per-block is_completed from it directly.
    -- ---------------------------------------------------------------
    DECLARE
        v_prior_test_ids  jsonb;
        v_prior_completed jsonb;
    BEGIN
        SELECT dtl.test_ids, dtl.completed_test_ids
          INTO v_prior_test_ids, v_prior_completed
        FROM public.daily_test_loads dtl
        WHERE dtl.user_id = p_user_id
          AND dtl.language_id = p_language_id
          AND dtl.load_date = p_date;

        IF v_prior_completed IS NOT NULL
           AND jsonb_typeof(v_prior_completed) = 'array'
           AND jsonb_array_length(v_prior_completed) > 0 THEN

            INSERT INTO pg_temp.chosen_tests (test_id, skill, slot_type, original_percentage, is_completed)
            SELECT (elem->>'test_id')::uuid,
                   COALESCE(elem->>'test_type', 'listening'),
                   COALESCE(elem->>'slot_type', 'new'),
                   NULLIF(elem->>'original_percentage', '')::numeric,
                   true
            FROM jsonb_array_elements(COALESCE(v_prior_test_ids, '[]'::jsonb)) AS elem
            WHERE jsonb_typeof(elem) = 'object'
              AND elem ? 'test_id'
              AND v_prior_completed ? (elem->>'test_id');

            -- Free one budgeted 'new' slot per retained completed slot of its skill
            -- (when that skill is budgeted today), keeping the day at ~budget.
            UPDATE pg_temp.skill_counts sc
               SET count = sc.count - retained.n
            FROM (
                SELECT skill, COUNT(*) AS n
                FROM pg_temp.chosen_tests
                WHERE is_completed
                GROUP BY skill
            ) retained
            WHERE retained.skill = sc.skill;
            DELETE FROM pg_temp.skill_counts WHERE count <= 0;
        END IF;
    END;

    -- ---------------------------------------------------------------
    -- TASK-704 / ADR-006 retry slot. Reserve AT MOST ONE slot for the worst
    -- sub-70% latest attempt older than the 24h cooldown. Runs BEFORE hydration
    -- so decrementing skill_counts frees one budgeted 'new' slot of the retry's
    -- skill (when that skill is budgeted today), keeping used_minutes ~constant.
    -- Additive (+1 over budget) only when the skill isn't budgeted today.
    -- Reduced-volatility ELO on submission is applied downstream by
    -- process_test_submission scanning slot_type='retry'.
    -- ---------------------------------------------------------------
    DECLARE
        c_poor_threshold  constant numeric := 70;   -- Config.POOR_PERFORMANCE_THRESHOLD
        v_retry_test_id   uuid;
        v_retry_skill     text;
        v_retry_pct       numeric;
    BEGIN
        SELECT latest.test_id, dtt.type_code, latest.percentage
          INTO v_retry_test_id, v_retry_skill, v_retry_pct
        FROM (
            SELECT DISTINCT ON (ta.test_id)
                   ta.test_id, ta.test_type_id, ta.percentage, ta.created_at
            FROM public.test_attempts ta
            WHERE ta.user_id = p_user_id
              AND ta.language_id = p_language_id
            ORDER BY ta.test_id, ta.created_at DESC
        ) latest
        JOIN public.dim_test_types dtt ON dtt.id = latest.test_type_id
        WHERE latest.percentage IS NOT NULL
          AND latest.percentage < c_poor_threshold
          AND latest.created_at < (NOW() - INTERVAL '24 hours')   -- cooldown
          AND latest.test_id NOT IN (SELECT ct.test_id FROM pg_temp.chosen_tests ct)  -- TASK-705
          AND dtt.type_code <> ALL(v_excluded)                                         -- session-modules
        ORDER BY latest.percentage ASC, latest.created_at ASC     -- worst first
        LIMIT 1;

        IF v_retry_test_id IS NOT NULL THEN
            -- Free one budgeted 'new' slot of this skill if it is budgeted today.
            UPDATE pg_temp.skill_counts
               SET count = count - 1
             WHERE skill = v_retry_skill AND count > 0;
            DELETE FROM pg_temp.skill_counts WHERE count <= 0;

            INSERT INTO pg_temp.chosen_tests (test_id, skill, slot_type, original_percentage)
            VALUES (v_retry_test_id, v_retry_skill, 'retry', ROUND(v_retry_pct, 1));
        END IF;
    END;

    -- ---------------------------------------------------------------
    -- word_upload slot (wiki/tasklist/word-list-import.plan.md Step 6).
    -- Reserve AT MOST ONE slot for the most-recently-matched, not-yet-
    -- surfaced watchlist test. Mirrors the TASK-704 retry block immediately
    -- above: single LIMIT-1 pick, guarded against anything already in
    -- chosen_tests (TASK-705 carry-over + retry), decrements skill_counts to
    -- borrow a budgeted 'new' slot of the matched test's skill when that
    -- skill is budgeted today (additive [+1 over budget] otherwise). Runs
    -- BEFORE hydration for the same reason retry does: so the borrow is
    -- visible to the skill_counts the hydration loop below consumes.
    --
    -- Skill resolution: a watchlisted match is a bare test_id (Step 4/5 only
    -- know it satisfied a vocab_sense_ids overlap, not which test_type to
    -- serve it as), so — like get_recommended_tests/get_replay_tests do for
    -- their own candidates — the skill is chosen as whichever active
    -- test_skill_ratings row for that test sits closest to the user's
    -- current ELO in that skill (defaulting unrated skills to 1200, same as
    -- get_recommended_tests).
    --
    -- Eligibility (all must hold):
    --   * wl.active = true, wl.language_id = p_language_id (this build is
    --     already scoped to one language; a match belongs to that scope only).
    --   * wl.last_matched_test_id IS NOT NULL (Step 4/5 found a match).
    --   * not already attempted by this user (surfacing an already-done test
    --     serves no purpose — mirrors get_recommended_tests' NOT EXISTS guard).
    --   * not already present in today's chosen_tests (no double-booking a
    --     retry/carried-over slot onto the same test_id).
    --   * premium gating identical to get_recommended_tests/get_replay_tests
    --     (free-tier tests always eligible; non-free only for premium users).
    --   * "not already surfaced" per the header comment: surfaced_at IS NULL
    --     OR surfaced_at was stamped earlier TODAY (same-day re-entrancy safe).
    -- Tie-break when more than one watchlist row qualifies: most recently
    -- matched first (freshest word upload takes the single daily slot).
    --
    -- On a hit: borrow/extend the budget exactly like retry, insert the
    -- chosen_tests row with slot_type = 'word_upload', and stamp
    -- last_matched_surfaced_at (COALESCE-guarded so a same-day re-solve does
    -- not keep sliding the "first surfaced" timestamp forward).
    -- ---------------------------------------------------------------
    DECLARE
        v_wordup_watchlist_id bigint;
        v_wordup_test_id      uuid;
        v_wordup_skill        text;
        v_wordup_tier_code    text;
        v_wordup_is_premium   boolean;
    BEGIN
        SELECT st.tier_code INTO v_wordup_tier_code
        FROM public.users u
        JOIN public.dim_subscription_tiers st ON st.id = u.subscription_tier_id
        WHERE u.id = p_user_id;
        v_wordup_is_premium := (v_wordup_tier_code NOT ILIKE '%free%');

        SELECT wl.id, wl.last_matched_test_id, dtt.type_code
          INTO v_wordup_watchlist_id, v_wordup_test_id, v_wordup_skill
        FROM public.user_word_watchlist wl
        JOIN public.tests t ON t.id = wl.last_matched_test_id
        JOIN public.test_skill_ratings tsr ON tsr.test_id = t.id
        JOIN public.dim_test_types dtt ON dtt.id = tsr.test_type_id AND dtt.is_active = true
        LEFT JOIN public.user_skill_ratings usr
               ON usr.user_id = wl.user_id
              AND usr.language_id = wl.language_id
              AND usr.test_type_id = tsr.test_type_id
        WHERE wl.user_id = p_user_id
          AND wl.language_id = p_language_id
          AND wl.active = true
          AND wl.last_matched_test_id IS NOT NULL
          AND (
              wl.last_matched_surfaced_at IS NULL
              OR wl.last_matched_surfaced_at::date = p_date
          )
          AND t.is_active = true
          AND (
              t.tier = 'free-tier'
              OR (t.tier != 'free-tier' AND v_wordup_is_premium)
          )
          AND NOT EXISTS (
              SELECT 1 FROM public.test_attempts ta
              WHERE ta.user_id = p_user_id AND ta.test_id = t.id
          )
          AND wl.last_matched_test_id NOT IN (SELECT ct.test_id FROM pg_temp.chosen_tests ct)
          AND dtt.type_code <> ALL(v_excluded)                                         -- session-modules
        ORDER BY wl.last_matched_at DESC NULLS LAST,
                 ABS(tsr.elo_rating - COALESCE(usr.elo_rating, 1200)) ASC
        LIMIT 1;

        IF v_wordup_test_id IS NOT NULL THEN
            -- Free one budgeted 'new' slot of this skill if it is budgeted today.
            UPDATE pg_temp.skill_counts
               SET count = count - 1
             WHERE skill = v_wordup_skill AND count > 0;
            DELETE FROM pg_temp.skill_counts WHERE count <= 0;

            INSERT INTO pg_temp.chosen_tests (test_id, skill, slot_type)
            VALUES (v_wordup_test_id, v_wordup_skill, 'word_upload');

            UPDATE public.user_word_watchlist
               SET last_matched_surfaced_at = COALESCE(last_matched_surfaced_at, NOW())
             WHERE id = v_wordup_watchlist_id;
        END IF;
    END;

    -- ---------------------------------------------------------------
    -- Hydrate test slots (TASK-702).
    --   * classifier_drill  -> per-language sentinel row (no ELO pool).
    --   * every other skill -> never-attempted ELO matches (get_recommended_tests),
    --     then top up any shortfall from get_replay_tests (slot_type='replay').
    -- ---------------------------------------------------------------
    FOR v_test IN
        SELECT sc.skill, sc.count
        FROM pg_temp.skill_counts sc
    LOOP
        IF v_test.skill = 'classifier_drill' THEN
            INSERT INTO pg_temp.chosen_tests (test_id, skill, slot_type)
            SELECT t.id, 'classifier_drill', 'new'
            FROM public.tests t
            WHERE t.language_id = p_language_id
              AND t.slug LIKE '\_\_classifier\_drill\_%'
              AND t.id NOT IN (SELECT ct.test_id FROM pg_temp.chosen_tests ct)  -- TASK-705: no dup w/ retained
            ORDER BY t.id
            LIMIT v_test.count;
        ELSE
            -- One test per topic per day (2026-11-11): two tests on the same
            -- topic in one session let the first give the second away. A topic
            -- already chosen today (retained, retry, word-upload or an earlier
            -- skill's slot) is skipped, and at most one test per topic is
            -- taken here. A shortfall falls through to the replay top-up below.
            INSERT INTO pg_temp.chosen_tests (test_id, skill, slot_type)
            SELECT x.test_id, v_test.skill, 'new'
            FROM (
                SELECT DISTINCT ON (COALESCE(tt.topic_id::text, rec.test_id::text))
                       rec.test_id, rec.elo_diff
                FROM public.get_recommended_tests(p_user_id, p_language_id) rec
                JOIN public.tests tt ON tt.id = rec.test_id
                WHERE rec.test_type = v_test.skill
                  AND rec.test_id NOT IN (SELECT ct.test_id FROM pg_temp.chosen_tests ct)  -- TASK-705: no dup w/ retained/retry
                  AND (tt.topic_id IS NULL OR tt.topic_id NOT IN (
                        SELECT t2.topic_id
                        FROM pg_temp.chosen_tests ct2
                        JOIN public.tests t2 ON t2.id = ct2.test_id
                        WHERE t2.topic_id IS NOT NULL))
                ORDER BY COALESCE(tt.topic_id::text, rec.test_id::text), ABS(rec.elo_diff)
            ) x
            ORDER BY ABS(x.elo_diff)
            LIMIT v_test.count;

            GET DIAGNOSTICS v_hydrated = ROW_COUNT;

            -- Exhausted-pool fallback: top up remaining budgeted slots with
            -- nearest-ELO previously-attempted tests (older than the age floor),
            -- excluding anything already chosen today.
            IF v_hydrated < v_test.count THEN
                INSERT INTO pg_temp.chosen_tests (test_id, skill, slot_type)
                SELECT r.test_id, v_test.skill, 'replay'
                FROM public.get_replay_tests(
                         p_user_id,
                         p_language_id,
                         v_test.skill,
                         c_replay_min_age_days,
                         ARRAY(SELECT ct.test_id FROM pg_temp.chosen_tests ct),
                         (v_test.count - v_hydrated)
                     ) r;
            END IF;
        END IF;
    END LOOP;

    -- ---------------------------------------------------------------
    -- Hydrate SURFACE slots (TASK-714). Each surface is clamped to what its
    -- own pool can actually supply today, so a budgeted-but-unsupplied slot
    -- shows up as a shortfall (hydrated < requested) instead of being emitted
    -- as a block the learner opens to find empty — the F3 failure shape.
    --
    --   flashcards       -> ceil(due cards / 15). "Due" is due_date <= p_date,
    --                       the same predicate GET /api/flashcards/due uses.
    --   dual_translation -> what GET /api/dual-translation/next can serve
    --                       (routes/dual_translation.py _choose_next, 2026-11-17):
    --                       sentence windows only. Counted: active tests in the
    --                       study language, attempted by the learner or not,
    --                       that still have two adjacent sentences with an
    --                       active pass/rewritten reference in the learner's
    --                       L1 (users.native_language_id, else English=2), on
    --                       the current transcript, clearing the language's
    --                       tightness floor (a sentence two independent reviews
    --                       agreed on is left out of the mean, ADR-049), and
    --                       outside every window already
    --                       served to this learner or retired; plus window
    --                       passages the learner was shown and has not had
    --                       graded (in progress or skipped). 0 when the L1 is
    --                       the study language. The whole-passage pool and
    --                       dt_passage_reference are no longer read.
    --
    -- Each predicate deliberately mirrors its serving endpoint rather than
    -- approximating it. A resolver that hydrates against a DIFFERENT rule than
    -- the route serves produces phantom shortfalls (or, worse, blocks the
    -- runner mounts and cannot fill) — the same class of mismatch F3 was.
    -- The dual_translation count is exact on "is there anything" and a lower
    -- bound on "how many": one per test with a fresh window (the route can
    -- cut several windows from a long test), and a 3-4 sentence window whose
    -- mean tightness clears the floor when no adjacent pair does is not
    -- counted. A graded passage is not counted: the route never serves it
    -- again except on an explicit re-serve request.
    -- ---------------------------------------------------------------
    DROP TABLE IF EXISTS pg_temp.surface_counts;
    CREATE TEMP TABLE pg_temp.surface_counts (
        skill     text PRIMARY KEY,
        requested int NOT NULL,
        hydrated  int NOT NULL
    ) ON COMMIT DROP;

    INSERT INTO pg_temp.surface_counts (skill, requested, hydrated)
    SELECT sb.skill,
           sb.count,
           LEAST(
               sb.count,
               CASE sb.skill
                   WHEN 'flashcards' THEN (
                       SELECT CEIL(COUNT(*)::numeric / c_cards_per_block)::int
                       FROM public.user_flashcards uf
                       WHERE uf.user_id = p_user_id
                         AND uf.language_id = p_language_id
                         AND uf.due_date <= public.review_today()
                   )
                   WHEN 'dual_translation' THEN (
                       WITH l1 AS (
                           SELECT COALESCE(
                                      (SELECT NULLIF(u.native_language_id, 0) FROM public.users u
                                        WHERE u.id = p_user_id),
                                      2)::int AS id
                       ), served AS (
                           SELECT dp.id, dp.source_ref_id, dp.sentence_start, dp.sentence_end, dp.status,
                                  bool_or(g.submission_id IS NOT NULL) AS graded
                             FROM public.dt_submission ds
                             JOIN public.dt_passage dp ON dp.id = ds.passage_id
                             LEFT JOIN public.dt_grade g ON g.submission_id = ds.id
                            WHERE ds.user_id = p_user_id
                              AND dp.l2_language_id = p_language_id
                              AND dp.sentence_start IS NOT NULL
                              AND dp.sentence_end IS NOT NULL
                            GROUP BY dp.id, dp.source_ref_id, dp.sentence_start, dp.sentence_end, dp.status
                       ), usable AS (
                           SELECT s.test_id, s.idx, r.tightness,
                                  (COALESCE(r.faithful_reviews, 0) >= 2) AS agreed
                             FROM public.tests t
                             JOIN public.test_sentences s ON s.test_id = t.id
                             JOIN public.test_sentence_references r
                               ON r.sentence_id = s.id
                              AND r.l1_language_id = (SELECT id FROM l1)
                              AND r.is_active
                              AND r.review_verdict IN ('pass', 'rewritten')
                            WHERE t.is_active
                              AND t.language_id = p_language_id
                              AND (NULLIF(t.transcript_hash, '') IS NULL
                                   OR s.transcript_hash = t.transcript_hash)
                              AND NOT EXISTS (
                                  SELECT 1 FROM served sv
                                   WHERE sv.source_ref_id = s.test_id
                                     AND s.idx BETWEEN sv.sentence_start AND sv.sentence_end)
                              AND NOT EXISTS (
                                  SELECT 1 FROM public.dt_passage rp
                                   WHERE rp.source_ref_id = s.test_id
                                     AND rp.status <> 'active'
                                     AND rp.sentence_start IS NOT NULL
                                     AND s.idx BETWEEN rp.sentence_start AND rp.sentence_end)
                       )
                       SELECT CASE WHEN (SELECT id FROM l1) = p_language_id THEN 0 ELSE (
                           (SELECT COUNT(DISTINCT a.test_id)
                              FROM usable a
                              JOIN usable b ON b.test_id = a.test_id AND b.idx = a.idx + 1
                             WHERE (a.agreed AND b.agreed)
                                OR CASE WHEN a.agreed THEN b.tightness
                                        WHEN b.agreed THEN a.tightness
                                        ELSE (SELECT avg(x) FROM (VALUES (a.tightness), (b.tightness)) v(x))
                                   END
                                   >= CASE p_language_id WHEN 1 THEN 0.70 WHEN 2 THEN 0.60
                                                         WHEN 3 THEN 0.65 ELSE 0.60 END)
                           + (SELECT COUNT(*) FROM served sv
                               WHERE NOT sv.graded AND sv.status = 'active')
                       ) END::int
                   )
                   ELSE 0
               END
           )
    FROM pg_temp.surface_budget sb;

    -- Shortfall bookkeeping (kept in daily_session_targets jsonb — no schema change).
    -- TASK-714: surface skills join requested/hydrated so the existing
    -- test_service._log_hydration_shortfalls WARNING covers them unchanged.
    SELECT COALESCE(jsonb_object_agg(skill, count), '{}'::jsonb)
      INTO v_requested_counts
    FROM (
        SELECT skill, count FROM pg_temp.skill_counts
        UNION ALL
        SELECT skill, requested FROM pg_temp.surface_counts
    ) req;

    -- hydrated_counts = primary (never-attempted / sentinel) fill ONLY, so a
    -- slot covered solely by replay still reads as a shortfall vs requested.
    -- NOT is_completed: retained same-day completions (TASK-705) are carried over,
    -- not freshly hydrated, so they must not mask (or inflate) this call's fill.
    SELECT COALESCE(jsonb_object_agg(skill, n), '{}'::jsonb)
      INTO v_hydrated_counts
    FROM (
        SELECT sc.skill, COALESCE(h.n, 0) AS n
        FROM pg_temp.skill_counts sc
        LEFT JOIN (
            SELECT skill, COUNT(*) AS n
            FROM pg_temp.chosen_tests
            WHERE slot_type = 'new' AND NOT is_completed
            GROUP BY skill
        ) h ON h.skill = sc.skill
        UNION ALL
        SELECT skill, hydrated FROM pg_temp.surface_counts
    ) hyd;

    SELECT COALESCE(jsonb_object_agg(skill, n), '{}'::jsonb)
      INTO v_replay_counts
    FROM (
        SELECT skill, COUNT(*) AS n
        FROM pg_temp.chosen_tests
        WHERE slot_type = 'replay' AND NOT is_completed
        GROUP BY skill
    ) rc;

    -- What the runner actually composes queue items from: hydrated surface
    -- slots only. routes/study_session.py reads this key.
    SELECT COALESCE(jsonb_object_agg(skill, hydrated), '{}'::jsonb)
      INTO v_surface_counts
    FROM pg_temp.surface_counts
    WHERE hydrated > 0;

    -- used_minutes now reflects HYDRATED test slots (new + replay) + hydrated
    -- surface slots + practice mins.
    -- TASK-715: dictation is priced at the tier of the test ACTUALLY placed,
    -- not the learner's expected tier, so this stays an honest account even
    -- when hydration lands a passage above or below their level.
    SELECT COALESCE(SUM(
        public.test_time_estimate(
            ct.skill,
            CASE WHEN ct.skill = 'dictation' THEN t.difficulty END
        )
    ), 0)
      INTO v_used_min_hyd
    FROM pg_temp.chosen_tests ct
    LEFT JOIN public.tests t ON t.id = ct.test_id;

    v_used_min_hyd := v_used_min_hyd
                    + COALESCE((
                        SELECT SUM(public.test_time_estimate(skill) * hydrated)
                        FROM pg_temp.surface_counts
                      ), 0)
                    + v_maint_min + v_acq_min;

    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'test_id',   test_id,
                'test_type', skill,
                'slot_type', slot_type
            )
            || CASE WHEN original_percentage IS NOT NULL
                    THEN jsonb_build_object('original_percentage', original_percentage)
                    ELSE '{}'::jsonb END
            ORDER BY skill, slot_type, test_id
        ),
        '[]'::jsonb
    )
      INTO v_test_ids
    FROM pg_temp.chosen_tests;

    INSERT INTO public.daily_test_loads (
        user_id, language_id, load_date,
        test_ids, completed_test_ids, daily_session_targets
    ) VALUES (
        p_user_id, p_language_id, p_date,
        v_test_ids, '[]'::jsonb,
        jsonb_build_object(
            'practice_maintenance_min', v_maint_min,
            'practice_acquisition_min', v_acq_min,
            'resolver_solved_at',       NOW(),
            'objective_value',          v_objective,
            'today_budget_minutes',     v_today_budget,
            -- TASK-732: the budget split itself, for observability.
            'test_budget_minutes',      v_test_budget,
            'practice_budget_minutes',  v_practice_budget,
            'used_minutes',             v_used_min_hyd,
            'budgeted_minutes',         v_used_min,
            'requested_counts',         v_requested_counts,
            'hydrated_counts',          v_hydrated_counts,
            'replay_counts',            v_replay_counts,
            'surface_counts',           v_surface_counts,
            -- session-modules (edit 9): observability; the session route also reads it to gate the speed round.
            'excluded_modules',         to_jsonb(v_excluded),
            -- session-budget (ADR-033)
            'budget_scope',             v_scope,
            'new_words_quota',          v_quota,
            'new_words_effective',      v_new_eff,
            'new_words_in_budget',      v_s_words,
            'new_words_shortfall',      v_shortfall,
            'new_words_supply_checked', v_prior_checked,
            'new_words_supply_checked_e', CASE WHEN v_prior_checked THEN to_jsonb(v_prior_checked_e) END,
            'governor_level',           v_level,
            'review_due_minutes',       v_due_min,
            'review_main_minutes',      v_maint_min,
            'new_word_main_minutes',    v_acq_min,
            'returned_to_tests_minutes', v_returned
        )
    )
    ON CONFLICT (user_id, language_id, load_date) DO UPDATE
        -- TASK-705: do NOT reset completed_test_ids / completed_blocks on a same-day
        -- re-solve. Every completed slot is retained in EXCLUDED.test_ids above, so
        -- the prior completed_test_ids stays a subset of the rebuilt test_ids.
        SET test_ids              = EXCLUDED.test_ids,
            daily_session_targets = EXCLUDED.daily_session_targets
    RETURNING id INTO v_load_id;

    DELETE FROM public.daily_test_load_items WHERE load_id = v_load_id;

    -- Mirror per-slot completion so the items table matches completed_test_ids
    -- after a same-day rebuild (TASK-705). Surfaces are absent by design: they
    -- have no test_id and their completion lives in completed_blocks.
    INSERT INTO public.daily_test_load_items (load_id, test_id, is_completed)
    SELECT v_load_id, ct.test_id, ct.is_completed
    FROM pg_temp.chosen_tests ct
    ON CONFLICT (load_id, test_id) DO NOTHING;

    RETURN jsonb_build_object(
        'load_id',                v_load_id,
        'load_date',              p_date,
        'week_start',             v_week_start,
        'today_budget_minutes',   v_today_budget,
        'test_budget_minutes',    v_test_budget,
        'practice_budget_minutes', v_practice_budget,
        'used_minutes',           v_used_min_hyd,
        'budgeted_minutes',       v_used_min,
        'objective_value',        v_objective,
        'test_ids',               v_test_ids,
        'skills_today',           to_jsonb(v_skills_today),
        'requested_counts',       v_requested_counts,
        'hydrated_counts',        v_hydrated_counts,
        'replay_counts',          v_replay_counts,
        'surface_counts',         v_surface_counts,
        'practice_maintenance_min', v_maint_min,
        'practice_acquisition_min', v_acq_min,
        'excluded_modules',         to_jsonb(v_excluded),
        'budget_scope',             v_scope,
        'new_words_quota',          v_quota,
        'new_words_effective',      v_new_eff,
        'new_words_in_budget',      v_s_words,
        'new_words_shortfall',      v_shortfall,
        'new_words_supply_checked', v_prior_checked,
        'new_words_supply_checked_e', CASE WHEN v_prior_checked THEN to_jsonb(v_prior_checked_e) END,
        'governor_level',           v_level,
        'review_due_minutes',       v_due_min,
        'review_main_minutes',      v_maint_min,
        'new_word_main_minutes',    v_acq_min,
        'returned_to_tests_minutes', v_returned
    );
END $function$;

REVOKE ALL ON FUNCTION public.build_daily_session(uuid, smallint, date) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.build_daily_session(uuid, smallint, date) TO service_role;

-- ---------------------------------------------------------------------------
-- public.ladder_graduate(uuid, integer, real, smallint)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.ladder_graduate(p_user_id uuid, p_sense_id integer, p_stress_test_score real, p_language_id smallint)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ladder RECORD;
    v_fc jsonb;
    v_p_known numeric;
    v_stress_bonus real;
    v_stability real;
    v_difficulty real;
    v_family_stddev numeric;
    v_variance_penalty real;
    v_due_date date;
BEGIN
    SELECT * INTO v_ladder FROM user_word_ladder
    WHERE user_id = p_user_id AND sense_id = p_sense_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'ladder_not_found');
    END IF;

    v_fc := v_ladder.family_confidence;
    v_p_known := ladder_compute_p_known(v_fc);

    -- Stress bonus tiers
    v_stress_bonus := CASE
        WHEN p_stress_test_score >= 0.90 THEN 1.0
        WHEN p_stress_test_score >= 0.80 THEN 0.5
        ELSE 0.0
    END;

    -- FSRS stability from acquisition trace
    v_stability := 7.0 + 21.0 * v_p_known::real + 6.0 * v_stress_bonus;
    v_stability := LEAST(GREATEST(v_stability, 7.0), 34.0);

    -- Family variance penalty for difficulty
    SELECT stddev_pop(kv.value::numeric) INTO v_family_stddev
    FROM jsonb_each_text(v_fc) AS kv
    WHERE kv.key IN (
        'form_recognition', 'meaning_recall', 'form_production',
        'collocation', 'semantic_discrimination'
    );
    v_variance_penalty := LEAST(1.5, COALESCE(v_family_stddev, 0) * 4.0);

    -- FSRS difficulty from acquisition trace
    v_difficulty := 8.0 - 5.0 * v_p_known::real + v_variance_penalty;
    v_difficulty := LEAST(GREATEST(v_difficulty, 2.0), 8.5);

    -- First maintenance review: earlier than full stability (safer at handoff)
    v_due_date := public.review_today() + ROUND(v_stability * 0.6)::integer;

    -- Update user_word_ladder → mastered
    UPDATE user_word_ladder SET
        word_state = 'mastered',
        stress_test_score = p_stress_test_score,
        review_due_at = NULL,  -- FSRS takes over scheduling
        updated_at = now()
    WHERE user_id = p_user_id AND sense_id = p_sense_id;

    -- Initialize or update FSRS flashcard
    INSERT INTO user_flashcards (
        user_id, sense_id, language_id,
        stability, difficulty, due_date, last_review,
        reps, lapses, state,
        created_at, updated_at
    ) VALUES (
        p_user_id, p_sense_id, p_language_id,
        v_stability, v_difficulty, v_due_date, public.review_today(),
        1, 0, 'review',
        now(), now()
    )
    ON CONFLICT (user_id, sense_id) DO UPDATE SET
        stability = EXCLUDED.stability,
        difficulty = EXCLUDED.difficulty,
        due_date = EXCLUDED.due_date,
        last_review = EXCLUDED.last_review,
        state = EXCLUDED.state,
        lapses = 0,
        reps = GREATEST(user_flashcards.reps, 1),
        updated_at = now();

    RETURN jsonb_build_object(
        'word_state', 'mastered',
        'stress_test_score', p_stress_test_score,
        'fsrs_stability', ROUND(v_stability::numeric, 2),
        'fsrs_difficulty', ROUND(v_difficulty::numeric, 2),
        'fsrs_due_date', v_due_date,
        'p_known_overall', v_p_known
    );
END;
$function$;

REVOKE ALL ON FUNCTION public.ladder_graduate(uuid, integer, real, smallint) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.ladder_graduate(uuid, integer, real, smallint) TO service_role;

-- ---------------------------------------------------------------------------
-- public.ladder_record_attempt(uuid, integer, uuid, boolean, boolean, integer, smallint, text, integer, text)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.ladder_record_attempt(p_user_id uuid, p_sense_id integer, p_exercise_id uuid, p_is_correct boolean, p_is_first_attempt boolean, p_time_taken_ms integer DEFAULT NULL::integer, p_language_id smallint DEFAULT NULL::smallint, p_exercise_type text DEFAULT NULL::text, p_ladder_level integer DEFAULT NULL::integer, p_exercise_context text DEFAULT 'standard'::text)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ladder RECORD;
    v_exercise_type text;
    v_ladder_level integer;
    v_language_id smallint;
    v_family text;
    v_fc jsonb;
    v_fc_dates jsonb;
    v_current_conf numeric;
    v_new_conf numeric;
    v_learn_rate numeric;
    v_slip_rate numeric;
    v_p_known_overall numeric;
    v_review_due timestamptz;
    v_word_state text;
    v_current_ring integer;
    v_gates jsonb;
    v_ring_cleared boolean;
    v_gate_pending text;
    v_stress_test_ready boolean := false;
    v_required_families text[];
    v_required_after_demote text[];
    v_min_conf_threshold numeric;
    v_i integer;
    v_old_p_known numeric;
    v_new_bkt numeric;
    v_semantic_class text;
    v_active_levels integer[];
    v_fsrs_result jsonb;
    v_is_lapse boolean := false;
    v_new_consecutive_failures integer;
    v_demoted boolean := false;
    v_family_session_counts jsonb;
BEGIN
    -- =================================================================
    -- 1. Resolve exercise metadata if not provided
    -- =================================================================
    IF p_exercise_type IS NULL OR p_ladder_level IS NULL OR p_language_id IS NULL THEN
        SELECT e.exercise_type, e.ladder_level, e.language_id
        INTO v_exercise_type, v_ladder_level, v_language_id
        FROM exercises e WHERE e.id = p_exercise_id;
    END IF;
    v_exercise_type := COALESCE(p_exercise_type, v_exercise_type);
    v_ladder_level := COALESCE(p_ladder_level, v_ladder_level);
    v_language_id := COALESCE(p_language_id, v_language_id);

    v_family := ladder_get_family(v_ladder_level);

    -- =================================================================
    -- 2. Get or create user_word_ladder row (locked for atomic update)
    -- =================================================================
    SELECT * INTO v_ladder FROM user_word_ladder
    WHERE user_id = p_user_id AND sense_id = p_sense_id
    FOR UPDATE;

    IF NOT FOUND THEN
        SELECT dv.semantic_class INTO v_semantic_class
        FROM dim_word_senses dws
        JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
        WHERE dws.id = p_sense_id;

        v_active_levels := CASE
            WHEN v_semantic_class = 'concrete_noun'
            THEN ARRAY[1,2,3,4,6,7,9]
            ELSE ARRAY[1,2,3,4,5,6,7,8,9]
        END;

        INSERT INTO user_word_ladder (
            user_id, sense_id, current_level, active_levels,
            word_state, current_ring
        ) VALUES (
            p_user_id, p_sense_id, 1, v_active_levels, 'new', 1
        );

        SELECT * INTO v_ladder FROM user_word_ladder
        WHERE user_id = p_user_id AND sense_id = p_sense_id
        FOR UPDATE;
    END IF;

    -- =================================================================
    -- 3. Insert exercise attempt (trigger syncs user_exercise_history)
    -- =================================================================
    INSERT INTO exercise_attempts (
        user_id, exercise_id, sense_id, exercise_type,
        is_correct, is_first_attempt, ladder_level, time_taken_ms
    ) VALUES (
        p_user_id, p_exercise_id, p_sense_id, v_exercise_type,
        p_is_correct, p_is_first_attempt, v_ladder_level, p_time_taken_ms
    );

    -- =================================================================
    -- 4. Update family confidence (BKT learn/slip)
    -- =================================================================
    v_fc := v_ladder.family_confidence;

    CASE p_exercise_context
        WHEN 'gate' THEN
            v_learn_rate := 0.18; v_slip_rate := 0.10;
        WHEN 'stress_test' THEN
            v_learn_rate := 0.20; v_slip_rate := 0.12;
        ELSE
            v_learn_rate := 0.15; v_slip_rate := 0.12;
    END CASE;

    v_current_conf := COALESCE((v_fc->>v_family)::numeric, 0.10);

    IF p_is_correct THEN
        v_new_conf := v_current_conf + (1.0 - v_current_conf) * v_learn_rate;
    ELSE
        v_new_conf := v_current_conf * (1.0 - v_slip_rate);
    END IF;
    v_new_conf := GREATEST(0.02, LEAST(0.98, v_new_conf));

    v_fc := jsonb_set(v_fc, ARRAY[v_family], to_jsonb(ROUND(v_new_conf, 4)));
    v_p_known_overall := ladder_compute_p_known(v_fc);

    -- =================================================================
    -- 4b. Compute updated family_success_dates (Phase 10)
    -- =================================================================
    -- Append CURRENT_DATE to the family's array if today's date isn't
    -- already there, then keep the most recent 2 dates. Used both by
    -- the cross-session gate below and by the UPDATE in step 6.
    v_fc_dates := COALESCE(v_ladder.family_success_dates, '{}'::jsonb);

    IF p_is_correct AND p_is_first_attempt THEN
        v_fc_dates := jsonb_set(
            v_fc_dates,
            ARRAY[v_family],
            COALESCE(
                (
                    SELECT to_jsonb(array_agg(d::text ORDER BY d::date DESC))
                    FROM (
                        SELECT d::date AS d
                        FROM (
                            SELECT jsonb_array_elements_text(
                                COALESCE(v_fc_dates->v_family, '[]'::jsonb)
                            ) AS d
                            UNION
                            SELECT CURRENT_DATE::text AS d
                        ) AS combined
                        GROUP BY d::date
                        ORDER BY d::date DESC
                        LIMIT 2
                    ) AS recent
                ),
                '[]'::jsonb
            )
        );
    END IF;

    -- =================================================================
    -- 4c. Compute updated consecutive_failures (Phase 10)
    -- =================================================================
    -- Compute pre-UPDATE so the demotion check below can read it.
    -- Mirrors the per-family heuristic from Phase 8 (resets on success or
    -- family change).
    v_new_consecutive_failures := CASE
        WHEN p_is_correct THEN 0
        WHEN p_is_first_attempt AND NOT p_is_correct
            AND v_family = COALESCE(v_ladder.last_exercised_family, '')
        THEN COALESCE(v_ladder.consecutive_failures, 0) + 1
        WHEN p_is_first_attempt AND NOT p_is_correct
        THEN 1
        ELSE COALESCE(v_ladder.consecutive_failures, 0)
    END;

    -- =================================================================
    -- 5. Branching: post-mastery lapse vs normal progression
    -- =================================================================
    v_current_ring := v_ladder.current_ring;
    v_gates := v_ladder.gates_passed;
    v_gate_pending := NULL;

    IF v_ladder.word_state = 'mastered' AND NOT p_is_correct THEN
        -- ---------------------------------------------------------
        -- LAPSE PATH: mastered word failed → relearning
        -- ---------------------------------------------------------
        v_is_lapse := true;

        v_new_conf := GREATEST(0.02, v_new_conf * 0.70);
        v_fc := jsonb_set(v_fc, ARRAY[v_family], to_jsonb(ROUND(v_new_conf, 4)));
        v_p_known_overall := ladder_compute_p_known(v_fc);

        v_word_state := 'relearning';
        v_review_due := (CURRENT_DATE + 1)::timestamptz;

        SELECT fsrs_schedule_review(
            uf.stability, uf.difficulty, uf.last_review,
            uf.reps, uf.lapses, uf.state, 1, public.review_today()
        ) INTO v_fsrs_result
        FROM user_flashcards uf
        WHERE uf.user_id = p_user_id AND uf.sense_id = p_sense_id;

        IF v_fsrs_result IS NOT NULL THEN
            UPDATE user_flashcards SET
                stability = (v_fsrs_result->>'stability')::real,
                difficulty = (v_fsrs_result->>'difficulty')::real,
                due_date = (v_fsrs_result->>'due_date')::date,
                state = v_fsrs_result->>'state',
                reps = (v_fsrs_result->>'reps')::integer,
                lapses = (v_fsrs_result->>'lapses')::integer,
                last_review = public.review_today(),
                updated_at = now()
            WHERE user_id = p_user_id AND sense_id = p_sense_id;
        END IF;

    ELSE
        -- ---------------------------------------------------------
        -- NORMAL PATH: scheduling + ring clearing + word_state
        -- ---------------------------------------------------------

        IF v_p_known_overall < 0.45 THEN
            v_review_due := (CURRENT_DATE + 1)::timestamptz;
        ELSIF v_p_known_overall < 0.75 THEN
            v_review_due := (CURRENT_DATE + 1)::timestamptz;
        ELSE
            v_review_due := (CURRENT_DATE + 2)::timestamptz;
        END IF;

        IF NOT p_is_correct AND p_is_first_attempt THEN
            v_review_due := (CURRENT_DATE + 1)::timestamptz;
        END IF;

        -- Confidence threshold check
        v_required_families := ladder_ring_families(v_current_ring, v_ladder.active_levels);
        v_min_conf_threshold := CASE
            WHEN v_current_ring <= 2 THEN 0.50
            WHEN v_current_ring = 3 THEN 0.65
            ELSE 0.72
        END;

        v_ring_cleared := true;
        IF v_required_families IS NOT NULL
           AND array_length(v_required_families, 1) > 0 THEN
            FOR v_i IN 1..array_length(v_required_families, 1) LOOP
                IF COALESCE((v_fc->>v_required_families[v_i])::numeric, 0.10)
                   < v_min_conf_threshold THEN
                    v_ring_cleared := false;
                    EXIT;
                END IF;
            END LOOP;
        END IF;

        -- Cross-session gate (Phase 10):
        -- Every required family must have first-attempt successes on at
        -- least 2 distinct calendar days. Uses the in-memory v_fc_dates
        -- so the same attempt that adds the second date can clear here.
        IF v_ring_cleared
           AND v_required_families IS NOT NULL
           AND array_length(v_required_families, 1) > 0 THEN
            FOR v_i IN 1..array_length(v_required_families, 1) LOOP
                IF jsonb_array_length(
                    COALESCE(v_fc_dates->v_required_families[v_i], '[]'::jsonb)
                ) < 2 THEN
                    v_ring_cleared := false;
                    EXIT;
                END IF;
            END LOOP;
        END IF;

        -- Ring transitions
        IF v_ring_cleared THEN
            IF v_current_ring = 1 THEN
                v_current_ring := 2;
            ELSIF v_current_ring = 2
                  AND NOT COALESCE((v_gates->>'gate_a')::boolean, false) THEN
                v_gate_pending := 'gate_a';
            ELSIF v_current_ring = 3
                  AND NOT COALESCE((v_gates->>'gate_b')::boolean, false) THEN
                v_gate_pending := 'gate_b';
            END IF;
        END IF;

        -- Compute word_state
        v_word_state := CASE
            WHEN v_ladder.word_state = 'mastered'
                THEN 'mastered'
            WHEN v_current_ring >= 4
                AND COALESCE((v_gates->>'gate_b')::boolean, false)
                AND v_ring_cleared
                AND v_p_known_overall >= 0.88
                THEN 'pre_mastery'
            WHEN v_gate_pending IS NOT NULL
                THEN 'gated'
            WHEN v_current_ring <= 1 AND v_p_known_overall < 0.20
                THEN 'new'
            ELSE 'active'
        END;

        -- Stress test readiness
        IF v_word_state = 'pre_mastery' THEN
            v_stress_test_ready := true;
            IF (1 = ANY(v_ladder.active_levels) OR 2 = ANY(v_ladder.active_levels))
               AND COALESCE((v_fc->>'form_recognition')::numeric, 0.10) < 0.72 THEN
                v_stress_test_ready := false;
            END IF;
            IF 3 = ANY(v_ladder.active_levels)
               AND COALESCE((v_fc->>'meaning_recall')::numeric, 0.10) < 0.72 THEN
                v_stress_test_ready := false;
            END IF;
            IF (4 = ANY(v_ladder.active_levels) OR 9 = ANY(v_ladder.active_levels))
               AND COALESCE((v_fc->>'form_production')::numeric, 0.10) < 0.72 THEN
                v_stress_test_ready := false;
            END IF;
            IF (5 = ANY(v_ladder.active_levels) OR 8 = ANY(v_ladder.active_levels))
               AND COALESCE((v_fc->>'collocation')::numeric, 0.10) < 0.72 THEN
                v_stress_test_ready := false;
            END IF;
            IF (6 = ANY(v_ladder.active_levels) OR 7 = ANY(v_ladder.active_levels))
               AND COALESCE((v_fc->>'semantic_discrimination')::numeric, 0.10) < 0.72 THEN
                v_stress_test_ready := false;
            END IF;
        END IF;

        -- ---------------------------------------------------------
        -- Ring demotion (Phase 10)
        -- ---------------------------------------------------------
        -- Trigger when:
        --   - This attempt is a first-attempt failure
        --   - The word is past 'new' (not still being introduced)
        --   - We're not at ring 1 (the floor)
        --   - The failing family is one required by the current ring
        --     (otherwise a stray failure on a non-required family shouldn't
        --     demote — the ring isn't gated by it)
        --   - consecutive_failures will reach 3 with this attempt
        --
        -- Effect:
        --   - Drop one ring
        --   - Reset only the gate that guards exit from the dropped-into
        --     ring (gate_a on demote→R2, gate_b on demote→R3); other gates
        --     survive as lifetime achievements
        --   - Reset family_success_dates of the demoted-into-ring required
        --     families so cross-session stability must be re-established
        --   - Set word_state='active' (clears any 'gated' or 'pre_mastery')
        --   - consecutive_failures resets to 0 in the UPDATE block below
        IF NOT p_is_correct
           AND p_is_first_attempt
           AND v_ladder.word_state NOT IN ('mastered', 'new')
           AND v_current_ring > 1
           AND v_family = ANY(v_required_families)
           AND v_new_consecutive_failures >= 3
        THEN
            v_demoted := true;
            v_current_ring := v_current_ring - 1;

            IF v_current_ring = 2 THEN
                v_gates := jsonb_set(v_gates, ARRAY['gate_a'], 'false'::jsonb);
            ELSIF v_current_ring = 3 THEN
                v_gates := jsonb_set(v_gates, ARRAY['gate_b'], 'false'::jsonb);
            END IF;

            v_required_after_demote := ladder_ring_families(v_current_ring, v_ladder.active_levels);
            IF v_required_after_demote IS NOT NULL
               AND array_length(v_required_after_demote, 1) > 0 THEN
                FOR v_i IN 1..array_length(v_required_after_demote, 1) LOOP
                    v_fc_dates := jsonb_set(
                        v_fc_dates,
                        ARRAY[v_required_after_demote[v_i]],
                        '[]'::jsonb
                    );
                END LOOP;
            END IF;

            v_word_state := 'active';
            v_gate_pending := NULL;
            v_stress_test_ready := false;
        END IF;
    END IF;

    -- =================================================================
    -- 6. Update user_word_ladder
    -- =================================================================
    UPDATE user_word_ladder SET
        family_confidence = v_fc,
        family_success_dates = v_fc_dates,
        gates_passed = v_gates,
        current_ring = v_current_ring,
        word_state = v_word_state,
        review_due_at = v_review_due,
        total_attempts = COALESCE(total_attempts, 0) + 1,
        first_try_success_count = CASE
            WHEN p_is_first_attempt AND p_is_correct
            THEN COALESCE(first_try_success_count, 0) + 1
            ELSE COALESCE(first_try_success_count, 0)
        END,
        first_try_failure_count = CASE
            WHEN p_is_first_attempt AND NOT p_is_correct
            THEN COALESCE(first_try_failure_count, 0) + 1
            ELSE COALESCE(first_try_failure_count, 0)
        END,
        -- On demotion, reset the counter so the demoted-into ring starts
        -- with a clean failure budget. Otherwise use the value computed
        -- in step 4c.
        consecutive_failures = CASE
            WHEN v_demoted THEN 0
            ELSE v_new_consecutive_failures
        END,
        last_success_session_date = CASE
            WHEN p_is_correct AND p_is_first_attempt THEN CURRENT_DATE
            ELSE last_success_session_date
        END,
        last_exercised_family = v_family,
        updated_at = now()
    WHERE user_id = p_user_id AND sense_id = p_sense_id;

    -- =================================================================
    -- 7. Update overall BKT (user_vocabulary_knowledge)
    -- =================================================================
    SELECT uvk.p_known INTO v_old_p_known
    FROM user_vocabulary_knowledge uvk
    WHERE uvk.user_id = p_user_id AND uvk.sense_id = p_sense_id;

    v_new_bkt := bkt_update_exercise(
        COALESCE(v_old_p_known, 0.10), p_is_correct, v_exercise_type
    );

    INSERT INTO user_vocabulary_knowledge (
        user_id, sense_id, language_id, p_known, status,
        evidence_count, last_evidence_at, updated_at
    ) VALUES (
        p_user_id, p_sense_id, v_language_id, v_new_bkt,
        bkt_status(v_new_bkt), 1, now(), now()
    )
    ON CONFLICT (user_id, sense_id) DO UPDATE SET
        p_known = EXCLUDED.p_known,
        status = CASE
            WHEN user_vocabulary_knowledge.status = 'user_marked_unknown'
            THEN 'user_marked_unknown'
            ELSE bkt_status(EXCLUDED.p_known)
        END,
        evidence_count = user_vocabulary_knowledge.evidence_count + 1,
        last_evidence_at = now(),
        updated_at = now();

    IF v_is_lapse THEN
        PERFORM bkt_apply_lapse_penalty(p_user_id, p_sense_id);
    END IF;

    -- =================================================================
    -- 8. Return result
    -- =================================================================
    -- Build family_session_counts: per-family count of distinct cross-session
    -- successes (capped at 2 by the storage trim). Frontend can use this to
    -- show "one more session" advancement progress.
    SELECT jsonb_object_agg(family, jsonb_array_length(dates))
    INTO v_family_session_counts
    FROM jsonb_each(v_fc_dates) AS j(family, dates);

    RETURN jsonb_build_object(
        'is_correct', p_is_correct,
        'family', v_family,
        'family_confidence', v_fc,
        'family_success_sessions', COALESCE(v_family_session_counts, '{}'::jsonb),
        'p_known_overall', v_p_known_overall,
        'current_ring', v_current_ring,
        'word_state', v_word_state,
        'review_due_at', v_review_due,
        'requeue', NOT p_is_correct AND p_is_first_attempt,
        'gate_pending', v_gate_pending,
        'stress_test_ready', v_stress_test_ready,
        'bkt_p_known', ROUND(v_new_bkt::numeric, 4),
        'is_lapse', v_is_lapse,
        'demoted', v_demoted
    );
END;
$function$;

REVOKE ALL ON FUNCTION public.ladder_record_attempt(uuid, integer, uuid, boolean, boolean, integer, smallint, text, integer, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.ladder_record_attempt(uuid, integer, uuid, boolean, boolean, integer, smallint, text, integer, text) TO service_role;

COMMIT;
