-- ============================================================================
-- Dual Translation — taxonomy v6 columns + v5 snapshot tables (TASK-842)
-- Date: 2026-10-04
--
-- Pure additive schema change for the DT taxonomy v6 cutover
-- (wiki/decisions/ADR-031-dt-taxonomy-v6-merge.md, "User decisions 2026-10-04";
-- wiki/tasklist/dt-taxonomy-v6.tasks.md TASK-842). Safe to apply before any
-- code change: every new column is NULLable with no default, so existing
-- inserts/selects (routes/dual_translation.py, scripts/dt_nightly_synthesis.py,
-- services/dual_translation/cards.py) keep working unchanged.
--
--   1. Version / variant / remap columns on the three subtype-bearing tables.
--      TASK-836 (wiki/evaluations/dt-taxonomy-v6-inventory-2026-10-04.md) swept
--      information_schema for '%subtype%' and probed the jsonb columns: exactly
--      three subtype columns exist — dt_error_instance.subtype,
--      dt_error_profile_entry.subtype, dt_card.subtype — so nothing else needs a
--      taxonomy_version column.
--        * taxonomy_version = the version whose slug vocabulary this row's
--          `subtype` is in (NOT "the version that graded it" — that stays in
--          dt_grade.grader_trace->'prompt_version'->>'taxonomy'). Rows rewritten
--          to v6 names at cutover (TASK-852) therefore carry 6. No FK to
--          dt_taxonomy_version.version (by design; a row must stay readable even
--          if a version row is ever removed). NULL = written before stamping.
--        * dt_error_instance.explanation_variant — word_choice only
--          (wrong_word | wrong_sense | false_synonym, ADR-031 decision 1). The
--          CHECK ties the variant to subtype = 'word_choice', so the grader must
--          null the variant if the Verifier re-types an error (TASK-845).
--        * remap_flag — set only by the TASK-852 rewrite: 'split_needs_review'
--          for rows bulk-remapped off a split v5 type (decision 2); 'merged' on
--          a surviving profile row that absorbed several v5 rows (decision 3).
--
--   2. Empty v5 snapshot tables that the TASK-852 rewrite fills (same
--      transaction, before any change) and its --restore reads back:
--        dt_v5_snapshot_error_instance       (id, subtype, taxonomy_version,
--                                             remap_flag) of every rewritten row
--        dt_v5_snapshot_error_instance_full  full rows of deleted script_choice
--                                             errors (decision 4)
--        dt_v5_snapshot_profile_entry        full rows
--        dt_v5_snapshot_card                 full rows
--        dt_v5_snapshot_card_review          full rows
--      The full-row tables are `LIKE <source>` (column names, types and NOT NULL
--      only — no identity, defaults, CHECKs, indexes or FKs; they hold rows
--      that may since have been deleted from the source) plus
--      `snapshot_at timestamptz DEFAULT now()` and a PRIMARY KEY on id (one
--      snapshot per source row; TASK-852 also fails closed on a non-empty
--      snapshot). They are created AFTER the ALTERs below, so they include the
--      new taxonomy_version / explanation_variant / remap_flag columns.
--      NOTE: LIKE freezes the column list at creation time. A column added to a
--      source table after this migration is NOT in its snapshot table — the
--      TASK-852 snapshot/restore functions must name columns explicitly.
--      RLS is enabled with NO policies (deny-all for anon/authenticated through
--      PostgREST; the service role and the table owner bypass RLS). These rows
--      are every learner's errors, so they must never be API-readable. No
--      auth.* reference, so the file also applies to a plain local Postgres
--      (the TASK-852 apply->restore integration test).
--      Retention: kept until TASK-854 signs off, then dropped by a separate,
--      operator-approved migration.
--
-- Ordering: independent of migrations/dt_taxonomy_v6_seed.sql (TASK-837) —
-- neither touches the other's objects. The TASK-853 runbook applies this file
-- first; it must be applied before DT_TAXONOMY_COLUMNS is turned on (config.py)
-- and before migrations/dt_rewrite_history_v6.sql (TASK-852) is applied.
--
-- Idempotent: ADD COLUMN IF NOT EXISTS, CREATE TABLE IF NOT EXISTS,
-- drop-then-add CHECKs. Per migrations/CLAUDE.md the CHECKs are added NOT VALID
-- inside the transaction (brief lock, no scan) and VALIDATEd after COMMIT
-- (SHARE UPDATE EXCLUSIVE, does not block reads/writes). The new columns are
-- all NULL at that point, so validation cannot fail.
--
-- SEARCH-BEFORE-ARCHIVE (migrations/CLAUDE.md): this file only ADDS columns
-- and constraints to dt_error_instance (dual_translation_groundwork.sql),
-- dt_error_profile_entry (dt_error_profile.sql) and dt_card (dt_cards.sql); it
-- redefines nothing they define, so none of them is superseded.
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1a. dt_error_instance
-- ============================================================================

ALTER TABLE public.dt_error_instance
    ADD COLUMN IF NOT EXISTS taxonomy_version    smallint,
    ADD COLUMN IF NOT EXISTS explanation_variant text,
    ADD COLUMN IF NOT EXISTS remap_flag          text;

ALTER TABLE public.dt_error_instance
    DROP CONSTRAINT IF EXISTS dt_error_instance_explanation_variant_check;
ALTER TABLE public.dt_error_instance
    ADD CONSTRAINT dt_error_instance_explanation_variant_check
    CHECK (
        explanation_variant IS NULL
        OR (subtype = 'word_choice'
            AND explanation_variant IN ('wrong_word', 'wrong_sense', 'false_synonym'))
    ) NOT VALID;

ALTER TABLE public.dt_error_instance
    DROP CONSTRAINT IF EXISTS dt_error_instance_remap_flag_check;
ALTER TABLE public.dt_error_instance
    ADD CONSTRAINT dt_error_instance_remap_flag_check
    CHECK (remap_flag IS NULL OR remap_flag IN ('split_needs_review')) NOT VALID;

COMMENT ON COLUMN public.dt_error_instance.taxonomy_version IS
    'dt_taxonomy_version.version whose slug vocabulary `subtype` is in (TASK-842, '
    'ADR-031). Not "the version that graded it" — that is dt_grade.grader_trace->'
    '''prompt_version''->>''taxonomy''. NULL = written before stamping. No FK.';

COMMENT ON COLUMN public.dt_error_instance.explanation_variant IS
    'word_choice errors only: wrong_word | wrong_sense | false_synonym (ADR-031 '
    'Decision A / user decision 1). CHECK ties it to subtype = ''word_choice''; '
    'NULL for every other subtype.';

COMMENT ON COLUMN public.dt_error_instance.remap_flag IS
    'Set by the v5->v6 history rewrite (TASK-852): ''split_needs_review'' = '
    'bulk-remapped off a split v5 type (particle_wa_ga, particle, '
    'pronoun_reference) to the closest v6 type. NULL otherwise.';

-- ============================================================================
-- 1b. dt_error_profile_entry
-- ============================================================================

ALTER TABLE public.dt_error_profile_entry
    ADD COLUMN IF NOT EXISTS taxonomy_version smallint,
    ADD COLUMN IF NOT EXISTS remap_flag       text;

ALTER TABLE public.dt_error_profile_entry
    DROP CONSTRAINT IF EXISTS dt_error_profile_entry_remap_flag_check;
ALTER TABLE public.dt_error_profile_entry
    ADD CONSTRAINT dt_error_profile_entry_remap_flag_check
    CHECK (remap_flag IS NULL OR remap_flag IN ('split_needs_review', 'merged')) NOT VALID;

COMMENT ON COLUMN public.dt_error_profile_entry.taxonomy_version IS
    'dt_taxonomy_version.version whose slug vocabulary `subtype` is in (TASK-842). '
    'Stamped by the nightly synthesis (TASK-851) and the v6 rewrite (TASK-852). '
    'NULL = written before stamping. No FK.';

COMMENT ON COLUMN public.dt_error_profile_entry.remap_flag IS
    'Set by the v5->v6 history rewrite (TASK-852): ''split_needs_review'' = '
    'remapped off a split v5 type; ''merged'' = survivor row that absorbed '
    'several v5 rows collapsing onto one v6 key. NULL otherwise.';

-- ============================================================================
-- 1c. dt_card
-- ============================================================================

ALTER TABLE public.dt_card
    ADD COLUMN IF NOT EXISTS taxonomy_version smallint;

COMMENT ON COLUMN public.dt_card.taxonomy_version IS
    'dt_taxonomy_version.version whose slug vocabulary `subtype` is in (TASK-842). '
    'Stamped by card generation (TASK-851) and the v6 rewrite (TASK-852). '
    'NULL = written before stamping. No FK.';

-- ============================================================================
-- 2. v5 snapshot tables (empty; filled only by TASK-852's rewrite function)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.dt_v5_snapshot_error_instance (
    id                bigint PRIMARY KEY,
    subtype           text NOT NULL,
    taxonomy_version  smallint,
    remap_flag        text,
    snapshot_at       timestamptz DEFAULT now()
);

COMMENT ON TABLE public.dt_v5_snapshot_error_instance IS
    'TASK-842/852: pre-rewrite (id, subtype, taxonomy_version, remap_flag) of every '
    'dt_error_instance row the v5->v6 history rewrite updates. Read by '
    'dt_restore_history_v5(). No FKs. Dropped after TASK-854 sign-off.';

CREATE TABLE IF NOT EXISTS public.dt_v5_snapshot_error_instance_full (
    LIKE public.dt_error_instance,
    snapshot_at timestamptz DEFAULT now(),
    PRIMARY KEY (id)
);

COMMENT ON TABLE public.dt_v5_snapshot_error_instance_full IS
    'TASK-842/852: full rows of dt_error_instance rows DELETED by the v6 rewrite '
    '(ja script_choice, ADR-031 decision 4). Restored with OVERRIDING SYSTEM VALUE. '
    'No FKs. Dropped after TASK-854 sign-off.';

CREATE TABLE IF NOT EXISTS public.dt_v5_snapshot_profile_entry (
    LIKE public.dt_error_profile_entry,
    snapshot_at timestamptz DEFAULT now(),
    PRIMARY KEY (id)
);

COMMENT ON TABLE public.dt_v5_snapshot_profile_entry IS
    'TASK-842/852: full pre-rewrite rows of every dt_error_profile_entry row the '
    'v6 rewrite updates, merges away or deletes. No FKs. Dropped after TASK-854 '
    'sign-off.';

CREATE TABLE IF NOT EXISTS public.dt_v5_snapshot_card (
    LIKE public.dt_card,
    snapshot_at timestamptz DEFAULT now(),
    PRIMARY KEY (id)
);

COMMENT ON TABLE public.dt_v5_snapshot_card IS
    'TASK-842/852: full pre-rewrite rows of every dt_card row the v6 rewrite '
    'updates (subtype / profile_entry_id repoint) or deletes. No FKs. Dropped '
    'after TASK-854 sign-off.';

CREATE TABLE IF NOT EXISTS public.dt_v5_snapshot_card_review (
    LIKE public.dt_card_review,
    snapshot_at timestamptz DEFAULT now(),
    PRIMARY KEY (id)
);

COMMENT ON TABLE public.dt_v5_snapshot_card_review IS
    'TASK-842/852: full rows of dt_card_review rows DELETED by the v6 rewrite '
    '(reviews of script_choice cards; FKs are NO ACTION so they go child-first). '
    'No FKs. Dropped after TASK-854 sign-off.';

-- Deny-all to API roles: RLS on, no policies. Service role / owner bypass RLS.
ALTER TABLE public.dt_v5_snapshot_error_instance      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dt_v5_snapshot_error_instance_full ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dt_v5_snapshot_profile_entry       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dt_v5_snapshot_card                ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dt_v5_snapshot_card_review         ENABLE ROW LEVEL SECURITY;

COMMIT;

-- ============================================================================
-- 3. Validate the NOT VALID CHECKs outside the exclusive-lock window
--    (migrations/CLAUDE.md). The new columns are all NULL, so these cannot fail.
-- ============================================================================

ALTER TABLE public.dt_error_instance VALIDATE CONSTRAINT dt_error_instance_explanation_variant_check;
ALTER TABLE public.dt_error_instance VALIDATE CONSTRAINT dt_error_instance_remap_flag_check;
ALTER TABLE public.dt_error_profile_entry VALIDATE CONSTRAINT dt_error_profile_entry_remap_flag_check;

-- ============================================================================
-- Verification (run manually after applying):
--
-- New columns (expect 6 rows, all smallint/text, is_nullable = YES):
-- SELECT table_name, column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_schema = 'public'
--   AND table_name IN ('dt_error_instance', 'dt_error_profile_entry', 'dt_card')
--   AND column_name IN ('taxonomy_version', 'explanation_variant', 'remap_flag')
-- ORDER BY table_name, column_name;
--
-- CHECKs present and validated (expect 3 rows, convalidated = true):
-- SELECT conrelid::regclass, conname, convalidated, pg_get_constraintdef(oid)
-- FROM pg_constraint
-- WHERE conname IN ('dt_error_instance_explanation_variant_check',
--                   'dt_error_instance_remap_flag_check',
--                   'dt_error_profile_entry_remap_flag_check');
--
-- Existing rows untouched (expect 0 / 0 / 0 on first apply):
-- SELECT
--   (SELECT count(*) FROM public.dt_error_instance
--     WHERE taxonomy_version IS NOT NULL OR explanation_variant IS NOT NULL
--        OR remap_flag IS NOT NULL) AS ei,
--   (SELECT count(*) FROM public.dt_error_profile_entry
--     WHERE taxonomy_version IS NOT NULL OR remap_flag IS NOT NULL) AS pe,
--   (SELECT count(*) FROM public.dt_card WHERE taxonomy_version IS NOT NULL) AS card;
--
-- Snapshot tables exist, are empty, have RLS on (expect 5 rows, n = 0, rls = t):
-- SELECT c.relname, c.relrowsecurity AS rls,
--        (xpath('/row/n/text()', query_to_xml(
--            format('SELECT count(*) AS n FROM public.%I', c.relname),
--            false, true, '')))[1]::text::int AS n
-- FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
-- WHERE n.nspname = 'public' AND c.relname LIKE 'dt\_v5\_snapshot\_%'
-- ORDER BY c.relname;
--
-- Full-row snapshots mirror their source columns (expect 0 rows — any row is a
-- source column missing from its snapshot):
-- SELECT s.src, s.col FROM (
--   SELECT 'dt_error_instance' AS src, column_name AS col, 'dt_v5_snapshot_error_instance_full' AS snap
--     FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'dt_error_instance'
--   UNION ALL
--   SELECT 'dt_error_profile_entry', column_name, 'dt_v5_snapshot_profile_entry'
--     FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'dt_error_profile_entry'
--   UNION ALL
--   SELECT 'dt_card', column_name, 'dt_v5_snapshot_card'
--     FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'dt_card'
--   UNION ALL
--   SELECT 'dt_card_review', column_name, 'dt_v5_snapshot_card_review'
--     FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'dt_card_review'
-- ) s
-- WHERE NOT EXISTS (
--   SELECT 1 FROM information_schema.columns c
--   WHERE c.table_schema = 'public' AND c.table_name = s.snap AND c.column_name = s.col);
--
-- CHECK smoke (run inside BEGIN; ... ROLLBACK; — each must ERROR with 23514):
-- UPDATE public.dt_error_instance SET explanation_variant = 'wrong_word'
--   WHERE id = (SELECT id FROM public.dt_error_instance WHERE subtype <> 'word_choice' LIMIT 1);
-- UPDATE public.dt_error_instance SET explanation_variant = 'shared_translation'
--   WHERE id = (SELECT id FROM public.dt_error_instance WHERE subtype = 'word_choice' LIMIT 1);
-- ============================================================================
