-- ============================================================================
-- Dual Translation — dt_card and dt_card_review tables (TASK-612)
-- Date: 2026-07-14
--
-- Pure additive schema change. Implements Feature 2: Error Synthesis + Spaced
-- Remediation. TASK-609 (dt_error_profile_entry) is a prerequisite.
--
-- Creates two tables:
--   1. dt_card: remediation item built from an error_instance/profile entry.
--      Mirrors user_flashcards FSRS state, but keyed to subtype (not sense_id).
--      Error cards are NOT sense-linked.
--   2. dt_card_review: append-only review log for recurrence-reduction
--      instrumentation (was_correct keyed back to subtype).
--
-- Source of truth: wiki/features/dual-translation-remediation.tech.md
-- (§Database Impact).
--
-- Conventions match the rest of the Dual Translation feature:
--   * bigint identity PKs.
--   * language_id columns are `integer REFERENCES dim_languages(id)`.
--   * real (not float) for float values (stability, difficulty).
--   * CHECK constraints for enumerated fields (card_type, state, rating).
--   * created_at / updated_at timestamptz DEFAULT now().
--
-- Idempotent: CREATE TABLE IF NOT EXISTS.
-- ============================================================================

BEGIN;

-- ============================================================================
-- dt_card — remediation item built from error_instance/profile entry
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.dt_card (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id             uuid NOT NULL REFERENCES public.users(id),
    profile_entry_id    bigint REFERENCES public.dt_error_profile_entry(id),
    origin_error_id     bigint REFERENCES public.dt_error_instance(id),
    card_type           text NOT NULL CHECK (card_type IN ('cloze', 'isolate_retranslate')),
    subtype             text NOT NULL,
    prompt_payload      jsonb NOT NULL,
    stability           real,
    difficulty          real,
    due_date            date,
    state               text CHECK (state IN ('new', 'learning', 'review', 'relearning')),
    reps                integer,
    lapses              integer,
    last_review         timestamptz,
    created_at          timestamptz DEFAULT now(),
    updated_at          timestamptz DEFAULT now()
);

COMMENT ON TABLE public.dt_card IS
    'Remediation item built from an error_instance or profile entry. FSRS state '
    '(stability, difficulty, due_date, state, reps, lapses, last_review) mirrors '
    'user_flashcards, but error cards are NOT sense-linked — they are keyed to '
    'subtype (taxonomy category) for interleaving across lessons.';

COMMENT ON COLUMN public.dt_card.user_id IS
    'The learner who will review this error card.';

COMMENT ON COLUMN public.dt_card.profile_entry_id IS
    'FK to dt_error_profile_entry; the aggregate error cluster this card was built from.';

COMMENT ON COLUMN public.dt_card.origin_error_id IS
    'FK to dt_error_instance; the original error that prompted card creation (provenance).';

COMMENT ON COLUMN public.dt_card.card_type IS
    'Card modality: cloze (delete the corrected element inside full sentence, '
    'productive recall) or isolate_retranslate (re-present problem sentence for '
    'back-translation after spaced delay).';

COMMENT ON COLUMN public.dt_card.subtype IS
    'Taxonomy subtype — the cluster/interleave key. Error cards have no sense_id; '
    'they are interleaved by subtype within review sessions.';

COMMENT ON COLUMN public.dt_card.prompt_payload IS
    'Card content and metadata (JSON). Built toward corrected_form. MUST NOT '
    'contain learner_form as the answer target (pedagogically critical). Follows '
    'SuperMemo minimum information principle: one atom per card.';

COMMENT ON COLUMN public.dt_card.stability IS
    'FSRS stability parameter (between-review interval increases exponentially '
    'with stability). Null until first review.';

COMMENT ON COLUMN public.dt_card.difficulty IS
    'FSRS difficulty parameter (percent-correct in learning phase; affects K). '
    'Null until first review.';

COMMENT ON COLUMN public.dt_card.due_date IS
    'Next review date (FSRS). Null until first review.';

COMMENT ON COLUMN public.dt_card.state IS
    'FSRS state: new (not yet reviewed), learning (0 < reps < learning_length), '
    'review (graduated, stable), relearning (failed, re-entering learning).';

COMMENT ON COLUMN public.dt_card.reps IS
    'Total review count (FSRS algorithm).';

COMMENT ON COLUMN public.dt_card.lapses IS
    'Count of failures (state transitioned to relearning). Drives K-factor.';

COMMENT ON COLUMN public.dt_card.last_review IS
    'Timestamp of the most recent review (for analytics and recurrence metric).';

CREATE INDEX IF NOT EXISTS idx_dt_card_user
    ON public.dt_card (user_id);

CREATE INDEX IF NOT EXISTS idx_dt_card_due
    ON public.dt_card (user_id, due_date)
    WHERE due_date IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_dt_card_profile_entry
    ON public.dt_card (profile_entry_id);

CREATE INDEX IF NOT EXISTS idx_dt_card_origin_error
    ON public.dt_card (origin_error_id);

CREATE INDEX IF NOT EXISTS idx_dt_card_subtype
    ON public.dt_card (user_id, subtype);

-- ============================================================================
-- dt_card_review — append-only review log
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.dt_card_review (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    card_id         bigint NOT NULL REFERENCES public.dt_card(id),
    rating          smallint NOT NULL CHECK (rating IN (1, 2, 3, 4)),
    was_correct     boolean,
    reviewed_at     timestamptz DEFAULT now()
);

COMMENT ON TABLE public.dt_card_review IS
    'Append-only review log for error cards. Required for recurrence-reduction '
    'instrumentation: delayed re-test accuracy on previously-errored items. '
    'Monitored metric: if recurrence is not dropping within ~3–4 review cycles, '
    'card formulation may violate minimum-information principle.';

COMMENT ON COLUMN public.dt_card_review.card_id IS
    'FK to dt_card; identifies which card was reviewed.';

COMMENT ON COLUMN public.dt_card_review.rating IS
    'FSRS grade: 1=again (incorrect), 2=hard (barely correct), '
    '3=good (correct), 4=easy (very correct). Drives FSRS state update.';

COMMENT ON COLUMN public.dt_card_review.was_correct IS
    'Explicit tracking for delayed re-test accuracy; complement to '
    'is_correct inference from rating. Keyed back to subtype for dashboard.';

COMMENT ON COLUMN public.dt_card_review.reviewed_at IS
    'Timestamp of review (for analytics, spaced intervals).';

CREATE INDEX IF NOT EXISTS idx_dt_card_review_card
    ON public.dt_card_review (card_id);

CREATE INDEX IF NOT EXISTS idx_dt_card_review_reviewed_at
    ON public.dt_card_review (reviewed_at);

COMMIT;

-- ============================================================================
-- Verification (run manually after migration):
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_schema = 'public' AND table_name = 'dt_card'
-- ORDER BY ordinal_position;
-- Expect 16 columns: id, user_id, profile_entry_id, origin_error_id,
-- card_type, subtype, prompt_payload, stability, difficulty, due_date,
-- state, reps, lapses, last_review, created_at, updated_at.
--
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_schema = 'public' AND table_name = 'dt_card_review'
-- ORDER BY ordinal_position;
-- Expect 5 columns: id, card_id, rating, was_correct, reviewed_at.
--
-- Verify FKs:
-- SELECT constraint_name, constraint_type
-- FROM information_schema.table_constraints
-- WHERE table_schema = 'public' AND table_name IN ('dt_card', 'dt_card_review');
-- Expect: dt_card has 3 FKs (user_id, profile_entry_id, origin_error_id);
-- dt_card_review has 1 FK (card_id).
-- ============================================================================
