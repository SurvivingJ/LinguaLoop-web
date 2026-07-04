-- Add users.native_language_id — the learner's L1, needed by Dual Translation
-- (TASK-607, routes/dual_translation.py GET /next) to pick which
-- dt_passage_reference to serve. No existing column tracked this:
-- user_languages is the L2 *study*-language enrollment table (see
-- Project Knowledge/12-PRD/02-feature-specifications/08-language-selection.md),
-- not a native-language designation — there was previously no place in the
-- schema to record a user's L1 at all.
--
-- Nullable: no onboarding UI captures this yet (future task). Until a user
-- sets it, callers must fall back to a default (English, id=2) rather than
-- assume non-null — see routes/dual_translation.py.

ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS native_language_id smallint REFERENCES public.dim_languages(id);

COMMENT ON COLUMN public.users.native_language_id IS
    'Learner''s native/L1 language (dual-translation TASK-607). NULL until '
    'the user sets it explicitly — no onboarding UI exists yet. Callers must '
    'default rather than assume non-null.';
