-- TASK-715 / TASK-714 — tier-scaled dictation + explicitly-seeded plannable
--   surfaces. Owns public.test_time_estimate (both overloads) and the new
--   public.dictation_max_words.
-- =============================================================================
-- WHY THESE TWO TASKS SHARE ONE FILE
--   Both change the SAME function. TASK-715 makes dictation's estimate
--   tier-aware; TASK-714 seeds 'flashcards' and 'dual_translation' so they
--   stop falling into the catch-all. Splitting them would leave two
--   non-archived files defining test_time_estimate — exactly the drift the
--   migrations CLAUDE.md rules exist to prevent.
--
--   This file also supersedes the test_time_estimate body in
--   phase13_build_daily_session.sql. That file is NOT archived: it remains the
--   sole repo record of public.week_start_for (archive rule #4).
-- =============================================================================
-- PROBLEM 1 (TASK-715, ADR-021) — the flat 80-word dictation cap.
--   get_recommended_tests filtered dictation candidates to transcripts of
--   <= 80 words at EVERY difficulty. Against live content that means the
--   dictation pool is essentially "difficulty 1 only": EN transcripts run
--   ~49-91 words at difficulty 1 but ~78-158 at difficulty 3 and ~259-389 at
--   difficulty 6, so an advancing learner's dictation pool silently empties
--   instead of getting harder. The cap now scales with the complexity tier.
--
--   The caps are MONOTONE INCREASING vs the old flat 80 at every tier, so no
--   test that is eligible today becomes ineligible — existing dictation tests
--   are unaffected and nothing needs regenerating.
--
-- PROBLEM 2 (TASK-715, ADR-021 "Harder / newly constrained") — once transcript
--   length varies by tier, a single scalar estimate for dictation is wrong at
--   both ends and daily budgets drift for advanced learners. Minutes now
--   derive from the tier's word cap:  2.0 + cap/20, which reproduces today's
--   6.0 exactly at T1 and grows to 22.0 at T6.
--
-- PROBLEM 3 (TASK-714, ADR-021) — 'flashcards' and 'dual_translation' are not
--   dim_test_types rows, so the COALESCE onto expected_minutes_p50 can never
--   fire for them and they would land on the catch-all ELSE 5.0: budgeted at
--   five minutes each with no error, ever. Both are seeded explicitly.
--   tests/test_plannable_surfaces.py asserts neither reaches the ELSE branch.
--
-- Idempotent: CREATE OR REPLACE throughout.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- dictation_max_words(difficulty) -> transcript word cap for that tier
--
-- Keyed on the SAME difficulty->tier mapping dim_complexity_tiers already
-- owns, so the cap moves with the tier table rather than duplicating its
-- boundaries. NULL / out-of-range difficulty falls back to the legacy flat 80
-- (fail-safe: an uncalibrated test keeps the old, strictly narrower rule).
--
-- Mirrored in Python by services/dictation/cap.py::DICTATION_MAX_WORDS;
-- tests/test_dictation_tier_cap.py parses this file and asserts they agree.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.dictation_max_words(p_difficulty integer)
RETURNS integer LANGUAGE sql STABLE AS $$
    SELECT COALESCE(
        (
            SELECT CASE ct.tier_code
                       WHEN 'T1' THEN 80
                       WHEN 'T2' THEN 120
                       WHEN 'T3' THEN 160
                       WHEN 'T4' THEN 220
                       WHEN 'T5' THEN 300
                       WHEN 'T6' THEN 400
                   END
            FROM public.dim_complexity_tiers ct
            WHERE p_difficulty BETWEEN ct.difficulty_min AND ct.difficulty_max
            ORDER BY ct.id
            LIMIT 1
        ),
        80
    )
$$;

COMMENT ON FUNCTION public.dictation_max_words IS
    'TASK-715: max dictation transcript length (words) for a test of the given '
    'difficulty, via its dim_complexity_tiers tier. Monotone increasing vs the '
    'former flat 80-word constant; NULL/unknown difficulty falls back to 80.';


-- ---------------------------------------------------------------------------
-- test_time_estimate(skill) -> minutes                 [tier-agnostic]
-- test_time_estimate(skill, difficulty) -> minutes     [tier-aware, TASK-715]
--
-- Two DISTINCT signatures rather than one function with a defaulted second
-- argument: a default would make test_time_estimate('reading') ambiguous
-- against the existing 1-arg function and break every current call site.
--
-- The 1-arg form keeps its meaning — "minutes for a typical slot of this
-- skill" — and stays the right call for skills whose per-item duration does
-- not vary with tier. build_daily_session calls the 2-arg form for dictation
-- (with the learner's expected difficulty when budgeting, and the test's own
-- difficulty when accounting for what was actually hydrated).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.test_time_estimate(p_skill text)
RETURNS numeric LANGUAGE sql STABLE AS $$
    SELECT COALESCE(
        (SELECT expected_minutes_p50 FROM public.dim_test_types
         WHERE type_code = p_skill AND expected_minutes_p50 IS NOT NULL),
        CASE p_skill
            WHEN 'reading'          THEN 6.0
            WHEN 'listening'        THEN 5.0
            WHEN 'dictation'        THEN 6.0   -- T1 anchor; see 2-arg overload
            WHEN 'pinyin'           THEN 4.0
            WHEN 'classifier_drill' THEN 4.0
            WHEN 'pitch_accent'     THEN 4.0
            -- TASK-714 plannable surfaces. NOT dim_test_types rows, so the
            -- COALESCE above can never cover them — seeded here so they never
            -- reach the ELSE. One 'flashcards' slot is a 15-card FSRS review
            -- block; one 'dual_translation' slot is one graded passage.
            WHEN 'flashcards'       THEN 7.0
            WHEN 'dual_translation' THEN 12.0
            ELSE 5.0
        END
    )::numeric
$$;

COMMENT ON FUNCTION public.test_time_estimate(text) IS
    'Expected minutes per budgeted slot of the given skill. Prefers '
    'dim_test_types.expected_minutes_p50 (refreshed nightly from observed P50s) '
    'when set; else a per-skill seed matching Config.TEST_TYPE_MINUTES. The '
    'ELSE 5.0 catch-all is a SILENT default — any new plannable surface must be '
    'added to the CASE (ADR-021). For dictation prefer the 2-arg overload.';


CREATE OR REPLACE FUNCTION public.test_time_estimate(p_skill text, p_difficulty integer)
RETURNS numeric LANGUAGE sql STABLE AS $$
    SELECT CASE
        -- Dictation duration tracks transcript length, which now tracks tier
        -- (TASK-715). 2.0 min fixed overhead (load, first listen, submit) plus
        -- one minute per 20 capped words, i.e. an effective ~20 wpm
        -- listen-and-type rate. Reproduces the legacy 6.0 exactly at T1
        -- (cap 80) and reaches 22.0 at T6 (cap 400).
        --
        -- An observed p50 in dim_test_types still wins when present: real
        -- measurement beats the model. p50 is tier-agnostic today and NULL for
        -- all 12 type codes as of 2026-08-07, so in practice the model applies.
        WHEN p_skill = 'dictation' AND p_difficulty IS NOT NULL THEN
            COALESCE(
                (SELECT expected_minutes_p50 FROM public.dim_test_types
                 WHERE type_code = 'dictation' AND expected_minutes_p50 IS NOT NULL),
                ROUND(2.0 + public.dictation_max_words(p_difficulty) / 20.0, 1)
            )::numeric
        ELSE public.test_time_estimate(p_skill)
    END
$$;

COMMENT ON FUNCTION public.test_time_estimate(text, integer) IS
    'TASK-715: tier-aware minutes per slot. Only dictation varies with '
    'difficulty today; every other skill delegates to the 1-arg form, so this '
    'is always safe to call when a difficulty is in hand.';

COMMIT;
