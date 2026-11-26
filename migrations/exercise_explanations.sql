-- =============================================================================
-- Exercise explanations cache: per-option feedback in the learner's language
-- Spec: wiki/features/exercise-explanations.tech.md; ADR-064.
--
-- *** LIVE-DB: the OWNER applies this file to production (the only Supabase project).
-- *** Agents never apply it. Until it is applied the app still works: explanations are
-- *** generated on demand and kept in process memory only (re-generated after a restart).
--
-- Objects (all new; no existing table, column, index or function is altered):
--   table public.exercise_explanations   one row per (exercise, learner language)
--
-- A "spot the error" item (spot_incorrect_sentence) stores four target-language
-- sentences and, at most, a one-line note on the wrong one in the target
-- language. services/exercise_explanations.py asks a model, once per item and
-- learner language, for each sentence's meaning, why it is right or wrong and
-- (for the wrong one) the corrected sentence, and keeps the answer here so every
-- later learner reads it without a model call.
--
-- Writes only through Flask (service role): RLS on, no policy, no client privilege.
--
-- SIZE: ~1.2 KB per row (four sentences of feedback); the whole ja + zh corpus
--       (~24k spot items) in one learner language would be ~30 MB, but rows are
--       only written for items a learner was actually served.
-- VERIFY (read-only, after apply):
--   SELECT count(*) FROM public.exercise_explanations;        -> 0 right after apply
--   SELECT relrowsecurity FROM pg_class WHERE relname = 'exercise_explanations';  -> true
-- Idempotent: CREATE TABLE IF NOT EXISTS / repeatable REVOKE + GRANT.
-- =============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.exercise_explanations (
    exercise_id     uuid        NOT NULL REFERENCES public.exercises(id) ON DELETE CASCADE,
    nl_language_id  smallint    NOT NULL REFERENCES public.dim_languages(id),
    -- exercises.content_version the explanation was written for; a regenerated
    -- item (new version) is explained afresh and this row overwritten.
    content_version integer     NOT NULL DEFAULT 0,
    -- {"sentences": [{"text", "meaning", "explanation", "correction"}], ...}
    payload         jsonb       NOT NULL,
    model           text,
    prompt_version  smallint    NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (exercise_id, nl_language_id)
);

ALTER TABLE public.exercise_explanations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.exercise_explanations FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.exercise_explanations TO service_role;

COMMENT ON TABLE public.exercise_explanations IS
    'Per-option answer feedback for an exercise in one learner language (ADR-064): '
    'each spot-the-error sentence''s meaning, why it is right or wrong, and the '
    'correction. Written once by services/exercise_explanations.py on first serve; '
    'service role only.';

NOTIFY pgrst, 'reload schema';

COMMIT;
