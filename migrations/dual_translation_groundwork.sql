-- ============================================================================
-- Dual Translation — groundwork migration (TASK-602)
-- Date: 2026-06-23
--
-- Pure additive schema change. No changes to any existing table. Creates the
-- 7 dt_* tables that everything else in the Dual Translation feature depends
-- on: dt_passage, dt_passage_reference, dt_submission, dt_grade,
-- dt_error_instance, dt_rubric_version, dt_taxonomy_version.
--
-- Source of truth: wiki/features/dual-translation.tech.md ("Database Impact
-- (new tables)"). dt_error_profile_entry, dt_card, dt_card_review are
-- TASK-609/612 (wiki/features/dual-translation-remediation.tech.md) — NOT
-- created here.
--
-- Conventions mirrored from the rest of this repo (see word_assets in
-- create_all_tables.sql, partF_question_attempt_results.sql):
--   * bigint identity PKs.
--   * language_id columns are `integer REFERENCES dim_languages(id)` even
--     though dim_languages.id is smallint — Postgres FKs across int2/int4
--     are valid (same btree opfamily) and this is the established pattern
--     in every other migration that references dim_languages.
--   * created_at timestamptz DEFAULT now() (added to dt_passage_reference
--     even though the wiki spec table omits it, for consistency with every
--     other dt_* table and repo convention generally).
--
-- One deliberate deviation from the literal wiki spec:
--   dt_passage.source_ref_id is typed `uuid` here, not the spec's `bigint`.
--   tests.id is uuid in the live schema (verified via information_schema),
--   so `bigint` in the spec cannot actually hold a tests.id value — it's
--   stale copy/paste from the generic PK convention, not a deliberate
--   choice. No FK is added to tests(id): like llm_calls.artifact_id, this
--   is a polymorphic source pointer (source_kind is locked to
--   'test_transcript' for now via CHECK, but the column is designed to
--   support other source kinds later without a type change).
--
-- RLS/grants are intentionally NOT part of this migration — out of scope
-- per the TASK-602 brief (acceptance criteria are tables + FKs/CHECKs/
-- UNIQUEs only); ownership enforcement for dt_submission/dt_grade/
-- dt_error_instance is called out in the tech spec as an application-layer
-- check ("Submission ownership check (user_id match) on every grade/read"),
-- not a database-level one. Flag for a follow-up security pass before
-- TASK-607 (routes) ships.
--
-- Idempotent: CREATE TABLE/INDEX IF NOT EXISTS throughout.
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. dt_passage — the L2 gold, sourced from existing corpus (tests.transcript)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.dt_passage (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    l2_language_id  integer NOT NULL REFERENCES public.dim_languages(id),
    source_kind     text NOT NULL CHECK (source_kind = 'test_transcript'),
    source_ref_id   uuid NOT NULL,
    l2_text         text NOT NULL,
    age_tier        smallint NOT NULL CHECK (age_tier BETWEEN 1 AND 6),
    register        text,
    status          text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'draft', 'retired')),
    created_at      timestamptz DEFAULT now()
);

COMMENT ON TABLE public.dt_passage IS
    'L2 gold passages (2-4 sentence spans extracted from tests.transcript). '
    'source_kind is locked to test_transcript for MVP (mystery scenes '
    'excluded per 2026-06-23 notes); source_ref_id is a polymorphic pointer '
    '(no hard FK), matching the llm_calls.artifact_id pattern.';

COMMENT ON COLUMN public.dt_passage.source_ref_id IS
    'id of the originating tests row. uuid (not the wiki spec''s bigint) — '
    'tests.id is uuid in the live schema.';

CREATE INDEX IF NOT EXISTS idx_dt_passage_l2_language
    ON public.dt_passage (l2_language_id);

CREATE INDEX IF NOT EXISTS idx_dt_passage_source
    ON public.dt_passage (source_kind, source_ref_id);

CREATE INDEX IF NOT EXISTS idx_dt_passage_status
    ON public.dt_passage (status)
    WHERE status = 'active';


-- ============================================================================
-- 2. dt_passage_reference — one L1 reference per supported L1, per passage
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.dt_passage_reference (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    passage_id       bigint NOT NULL REFERENCES public.dt_passage(id) ON DELETE CASCADE,
    l1_language_id   integer NOT NULL REFERENCES public.dim_languages(id),
    l1_text          text NOT NULL,
    generator_slug   text,
    created_at       timestamptz DEFAULT now(),
    UNIQUE (passage_id, l1_language_id)
);

COMMENT ON TABLE public.dt_passage_reference IS
    'Generated L1 reference translation per (passage, L1). generator_slug '
    'records provenance (OpenRouter slug used).';


-- ============================================================================
-- 3. dt_submission — a learner's L2 reproduction attempt
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.dt_submission (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id           uuid NOT NULL REFERENCES public.users(id),
    passage_id        bigint NOT NULL REFERENCES public.dt_passage(id),
    l1_language_id    integer NOT NULL REFERENCES public.dim_languages(id),
    reproduction      text NOT NULL,
    modality          text NOT NULL DEFAULT 'text' CHECK (modality = 'text'),
    idempotency_key   text,
    created_at        timestamptz DEFAULT now()
);

COMMENT ON TABLE public.dt_submission IS
    'Learner L2 reproduction attempt against a dt_passage gold. modality is '
    'locked to text for MVP (speech is a future flag per ADR/business-rule '
    'notes).';

CREATE INDEX IF NOT EXISTS idx_dt_submission_user
    ON public.dt_submission (user_id);

CREATE INDEX IF NOT EXISTS idx_dt_submission_passage
    ON public.dt_submission (passage_id);

-- Mirrors idx_test_attempts_user_idempotency (add_test_attempts_idempotency_index.sql):
-- covering partial index for the double-submit latch lookup, not a UNIQUE
-- constraint (most rows have a NULL key).
CREATE INDEX IF NOT EXISTS idx_dt_submission_user_idempotency
    ON public.dt_submission (user_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;


-- ============================================================================
-- 4. dt_grade — the persisted grading contract, one row per submission
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.dt_grade (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    submission_id   bigint NOT NULL UNIQUE REFERENCES public.dt_submission(id) ON DELETE CASCADE,
    scores          jsonb NOT NULL,
    overall_band    smallint NOT NULL CHECK (overall_band BETWEEN 1 AND 4),
    diff            jsonb NOT NULL,
    grader_trace    jsonb NOT NULL,
    created_at      timestamptz DEFAULT now()
);

COMMENT ON TABLE public.dt_grade IS
    'Persisted grading result for a dt_submission (1:1). scores is '
    '{accuracy,understandability,fidelity,range,naturalness} each 1-4; diff '
    'is the token opcode array; grader_trace is {tier, '
    'deterministic_prefilter, cache_hit, tokens{in,out}, slugs[]}.';


-- ============================================================================
-- 5. dt_error_instance — individual tagged errors within a graded submission
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.dt_error_instance (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    submission_id       bigint NOT NULL REFERENCES public.dt_submission(id),
    span_reproduction   jsonb NOT NULL,
    span_reference      jsonb NOT NULL,
    category            text NOT NULL CHECK (category IN ('grammatical', 'lexical', 'pragmatic_expressional')),
    subtype             text NOT NULL,
    source               text NOT NULL CHECK (source IN ('interlingual', 'intralingual')),
    severity            text NOT NULL CHECK (severity IN ('global', 'local')),
    learner_form        text NOT NULL,
    corrected_form       text NOT NULL,
    explanation         text NOT NULL,
    confidence          real NOT NULL,
    is_mistake          boolean DEFAULT false,
    created_at          timestamptz DEFAULT now()
);

COMMENT ON TABLE public.dt_error_instance IS
    'One row per tagged error in a graded submission. subtype is a '
    'language-pair taxonomy key versioned in dt_taxonomy_version, not a '
    'fixed enum. explanation is eager (ADR-015) and NOT NULL by design — '
    'every error must carry a rendered "which rule + why" before this row '
    'is written.';

CREATE INDEX IF NOT EXISTS idx_dt_error_instance_submission
    ON public.dt_error_instance (submission_id);


-- ============================================================================
-- 6. dt_rubric_version — versioned rubric config (dimensions, weights, bands)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.dt_rubric_version (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    version         integer NOT NULL UNIQUE,
    is_active       boolean NOT NULL DEFAULT false,
    config          jsonb NOT NULL,
    description     text,
    created_at      timestamptz DEFAULT now()
);

COMMENT ON TABLE public.dt_rubric_version IS
    'Versioned rubric config: 5 dimensions, default + per-language weights, '
    'band descriptors per age tier (1-6). Never hardcoded in app code. The '
    'active row''s id is referenced by dt_grade.grader_trace so re-scores '
    'are reproducible; a config edit must bump version (prompt-cache '
    'prefix stability).';

CREATE UNIQUE INDEX IF NOT EXISTS idx_dt_rubric_version_one_active
    ON public.dt_rubric_version (is_active)
    WHERE is_active;


-- ============================================================================
-- 7. dt_taxonomy_version — versioned cross-linguistic + per-pair taxonomy
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.dt_taxonomy_version (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    version         integer NOT NULL UNIQUE,
    is_active       boolean NOT NULL DEFAULT false,
    taxonomy        jsonb NOT NULL,
    description     text,
    created_at      timestamptz DEFAULT now()
);

COMMENT ON TABLE public.dt_taxonomy_version IS
    'Versioned taxonomy config: shared cross-linguistic schema (category/ '
    'source/severity) + per-directed-pair subtype tables + per-subtype x '
    'per-L1 explanation templates (see business-rules/'
    'translation-error-taxonomy.md). Never hardcoded in app code. The '
    'active row''s id is referenced by dt_grade.grader_trace.';

CREATE UNIQUE INDEX IF NOT EXISTS idx_dt_taxonomy_version_one_active
    ON public.dt_taxonomy_version (is_active)
    WHERE is_active;

COMMIT;

-- ============================================================================
-- Verification (run manually after migration):
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public' AND table_name LIKE 'dt_%' ORDER BY table_name;
-- Expect 7 rows: dt_error_instance, dt_grade, dt_passage, dt_passage_reference,
-- dt_rubric_version, dt_submission, dt_taxonomy_version.
--
-- SELECT is_nullable FROM information_schema.columns
-- WHERE table_name = 'dt_error_instance' AND column_name = 'explanation';
-- Expect 'NO'.
-- ============================================================================
