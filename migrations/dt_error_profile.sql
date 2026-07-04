-- ============================================================================
-- Dual Translation — dt_error_profile_entry migration (TASK-609)
-- Date: 2026-07-04
--
-- Pure additive schema change. Unblocks TASK-610 (mistake gate) and
-- TASK-612 (dt_card tables).
--
-- Creates the dt_error_profile_entry table: aggregated error cluster per
-- learner per subtype. One row per (user, l1↔l2 pair, subtype), updated
-- nightly by the error synthesis pipeline. Drives the error-profile
-- dashboard (self-regulation, never gamified).
--
-- Source of truth: wiki/features/dual-translation-remediation.tech.md
-- (§Database Impact).
--
-- Conventions match the rest of the Dual Translation feature (TASK-602):
--   * bigint identity PKs.
--   * language_id columns are `integer REFERENCES dim_languages(id)`.
--   * real (not float) for float values (severity_rank).
--   * CHECK constraints for enumerated fields.
--   * created_at / updated_at timestamptz DEFAULT now().
--
-- Idempotent: CREATE TABLE IF NOT EXISTS.
-- ============================================================================

BEGIN;

-- ============================================================================
-- dt_error_profile_entry — aggregated error cluster per learner per subtype
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.dt_error_profile_entry (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id             uuid NOT NULL REFERENCES public.users(id),
    l1_language_id      integer NOT NULL REFERENCES public.dim_languages(id),
    l2_language_id      integer NOT NULL REFERENCES public.dim_languages(id),
    subtype             text NOT NULL,
    count               integer NOT NULL,
    severity_rank       real NOT NULL,
    trend               jsonb,
    remediation_status  text NOT NULL CHECK (remediation_status IN ('watching', 'queued', 'drilling', 'resolved')),
    updated_at          timestamptz DEFAULT now(),
    UNIQUE (user_id, l1_language_id, l2_language_id, subtype)
);

COMMENT ON TABLE public.dt_error_profile_entry IS
    'Aggregated error cluster per learner per subtype (l1↔l2 pair). One row '
    'per (user, pair, subtype), upserted nightly by the error synthesis '
    'pipeline. Drives the error-profile dashboard (self-regulation, never '
    'gamified). severity_rank is frequency × severity (global errors rank '
    'first). remediation_status tracks promotion through the pipeline: '
    'watching (monitoring) → queued (ready for SRS) → drilling → resolved.';

COMMENT ON COLUMN public.dt_error_profile_entry.count IS
    'Occurrences of this subtype in the current window (N in W, tunable config).';

COMMENT ON COLUMN public.dt_error_profile_entry.severity_rank IS
    'Frequency × severity; drives ranking on the dashboard. Global errors '
    'have higher severity than local.';

COMMENT ON COLUMN public.dt_error_profile_entry.trend IS
    'Time series data for trend visualization (e.g., "article errors down '
    '40% this month"). jsonb format TBD by TASK-610.';

COMMENT ON COLUMN public.dt_error_profile_entry.remediation_status IS
    'Pipeline state: watching (monitoring, < N occurrences), queued (ready '
    'for SRS, ≥ N occurrences or proceduralization gap), drilling (active '
    'cards due), resolved (user no longer errs on this subtype).';

CREATE INDEX IF NOT EXISTS idx_dt_error_profile_entry_user
    ON public.dt_error_profile_entry (user_id);

CREATE INDEX IF NOT EXISTS idx_dt_error_profile_entry_status
    ON public.dt_error_profile_entry (remediation_status)
    WHERE remediation_status IN ('queued', 'drilling');

CREATE INDEX IF NOT EXISTS idx_dt_error_profile_entry_severity_rank
    ON public.dt_error_profile_entry (user_id, severity_rank DESC);

COMMIT;

-- ============================================================================
-- Verification (run manually after migration):
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_schema = 'public' AND table_name = 'dt_error_profile_entry'
-- ORDER BY ordinal_position;
-- Expect 9 columns: id, user_id, l1_language_id, l2_language_id, subtype,
-- count, severity_rank, trend, remediation_status, updated_at.
-- Then verify composite UNIQUE constraint:
-- SELECT constraint_name, constraint_type
-- FROM information_schema.table_constraints
-- WHERE table_schema = 'public' AND table_name = 'dt_error_profile_entry';
-- Expect: one PRIMARY KEY (id) and one UNIQUE on (user_id, l1_language_id, l2_language_id, subtype).
-- ============================================================================
