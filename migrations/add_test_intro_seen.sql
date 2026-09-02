-- First-time "what is this test / how do I do it" explainer popup.
--
-- One row per (user, test_type) the user has ever been shown the intro for.
-- test_type is the same plain string code used throughout the frontend
-- (reading, listening, dictation, pinyin, pitch_accent, classifier_drill,
-- counter_drill) — not a dim_test_types FK, since a couple of these
-- (classifier_drill, counter_drill) are infinite-drill features that don't
-- have a dim_test_types row of their own, and the frontend never has the
-- numeric id handy at the point it needs to ask "has this user seen this?".
--
-- Mirrors users.has_seen_welcome (migrations/add_has_seen_welcome.sql) but as
-- a table instead of a single boolean column, since there are several
-- independent "seen" flags here rather than one.
CREATE TABLE IF NOT EXISTS public.user_test_intros_seen (
    user_id     uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    test_type   text NOT NULL,
    seen_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, test_type)
);

ALTER TABLE public.user_test_intros_seen ENABLE ROW LEVEL SECURITY;

-- All access goes through the admin client (service role), same as
-- users.has_seen_welcome — see services/test_intro_service.py. No
-- policies are defined for the anon/authenticated roles, so RLS denies
-- everything except service-role access by default.
