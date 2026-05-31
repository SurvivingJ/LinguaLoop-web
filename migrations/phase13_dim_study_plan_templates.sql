-- ============================================================================
-- Phase 13 — Study Plans — dim_study_plan_templates + seed
-- Date: 2026-05-21
--
-- Templates are starting points the adapter shifts from. Each
-- (language_id, daily_minutes) cell defines:
--   - weekly_test_counts jsonb — per-skill count target per week
--   - practice_total_minutes  — Practice budget per week (Maint + Acq)
--   - base_maintenance_share  — default 0.30; adapter shifts within
--                                [0.15, 0.50]
--   - practice_minutes_flex_pct — ±25%; adapter shifts within this band
--                                  based on global weakness signal
--   - is_default              — true for the 30-min row per language; used
--                                by the backfill INSERT
--
-- Floor and ceiling per test skill are derived at adapter runtime:
--   floor   = ceil(target * 0.5)
--   ceiling = ceil(target * 1.5)
-- (Not stored; see wiki/features/study-plans.tech.md section "Floor/ceiling".)
--
-- Seeds use (SELECT id FROM dim_languages WHERE language_code = '…') because
-- dim_languages.id is auto-generated and not stable across environments.
--
-- See wiki/features/study-plans.tech.md section "Schema" and ADR-009.
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.dim_study_plan_templates (
    template_id                smallint PRIMARY KEY,
    language_id                smallint NOT NULL REFERENCES public.dim_languages(id),
    daily_minutes              smallint NOT NULL,
    weekly_test_counts         jsonb    NOT NULL,
    practice_total_minutes     smallint NOT NULL,
    base_maintenance_share     numeric(3,2) NOT NULL DEFAULT 0.30,
    practice_minutes_flex_pct  numeric(3,2) NOT NULL DEFAULT 0.25,
    is_default                 boolean  NOT NULL DEFAULT false,
    UNIQUE (language_id, daily_minutes),
    CONSTRAINT dim_study_plan_templates_daily_minutes_range
        CHECK (daily_minutes BETWEEN 10 AND 180),
    CONSTRAINT dim_study_plan_templates_practice_minutes_range
        CHECK (practice_total_minutes > 0 AND practice_total_minutes <= 1260),
    CONSTRAINT dim_study_plan_templates_base_maint_range
        CHECK (base_maintenance_share >= 0.10 AND base_maintenance_share <= 0.60),
    CONSTRAINT dim_study_plan_templates_flex_range
        CHECK (practice_minutes_flex_pct >= 0 AND practice_minutes_flex_pct <= 0.50),
    CONSTRAINT dim_study_plan_templates_weekly_counts_object
        CHECK (jsonb_typeof(weekly_test_counts) = 'object')
);

COMMENT ON TABLE public.dim_study_plan_templates IS
    'Starting-point cadence per (language, daily_minutes). Adapter shifts '
    'within floor/ceiling bounds derived from weekly_test_counts.';

-- ---------------------------------------------------------------------------
-- Seed: Chinese
-- ---------------------------------------------------------------------------
INSERT INTO public.dim_study_plan_templates
    (template_id, language_id, daily_minutes, weekly_test_counts,
     practice_total_minutes, base_maintenance_share, practice_minutes_flex_pct,
     is_default)
SELECT 101, l.id, 30,
       '{"reading":6,"listening":5,"dictation":2,"pinyin":1,"classifier_drill":1}'::jsonb,
       90, 0.30, 0.25, true
FROM public.dim_languages l WHERE l.language_code = 'cn'
ON CONFLICT (template_id) DO NOTHING;

INSERT INTO public.dim_study_plan_templates
    (template_id, language_id, daily_minutes, weekly_test_counts,
     practice_total_minutes, base_maintenance_share, practice_minutes_flex_pct,
     is_default)
SELECT 102, l.id, 45,
       '{"reading":8,"listening":7,"dictation":3,"pinyin":2,"classifier_drill":1}'::jsonb,
       135, 0.30, 0.25, false
FROM public.dim_languages l WHERE l.language_code = 'cn'
ON CONFLICT (template_id) DO NOTHING;

INSERT INTO public.dim_study_plan_templates
    (template_id, language_id, daily_minutes, weekly_test_counts,
     practice_total_minutes, base_maintenance_share, practice_minutes_flex_pct,
     is_default)
SELECT 103, l.id, 60,
       '{"reading":10,"listening":9,"dictation":4,"pinyin":2,"classifier_drill":2}'::jsonb,
       180, 0.30, 0.25, false
FROM public.dim_languages l WHERE l.language_code = 'cn'
ON CONFLICT (template_id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Seed: English
-- ---------------------------------------------------------------------------
INSERT INTO public.dim_study_plan_templates
    (template_id, language_id, daily_minutes, weekly_test_counts,
     practice_total_minutes, base_maintenance_share, practice_minutes_flex_pct,
     is_default)
SELECT 201, l.id, 30,
       '{"reading":7,"listening":6,"dictation":2}'::jsonb,
       100, 0.30, 0.25, true
FROM public.dim_languages l WHERE l.language_code = 'en'
ON CONFLICT (template_id) DO NOTHING;

INSERT INTO public.dim_study_plan_templates
    (template_id, language_id, daily_minutes, weekly_test_counts,
     practice_total_minutes, base_maintenance_share, practice_minutes_flex_pct,
     is_default)
SELECT 202, l.id, 45,
       '{"reading":10,"listening":8,"dictation":3}'::jsonb,
       150, 0.30, 0.25, false
FROM public.dim_languages l WHERE l.language_code = 'en'
ON CONFLICT (template_id) DO NOTHING;

INSERT INTO public.dim_study_plan_templates
    (template_id, language_id, daily_minutes, weekly_test_counts,
     practice_total_minutes, base_maintenance_share, practice_minutes_flex_pct,
     is_default)
SELECT 203, l.id, 60,
       '{"reading":13,"listening":11,"dictation":4}'::jsonb,
       200, 0.30, 0.25, false
FROM public.dim_languages l WHERE l.language_code = 'en'
ON CONFLICT (template_id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Seed: Japanese
-- ---------------------------------------------------------------------------
INSERT INTO public.dim_study_plan_templates
    (template_id, language_id, daily_minutes, weekly_test_counts,
     practice_total_minutes, base_maintenance_share, practice_minutes_flex_pct,
     is_default)
SELECT 301, l.id, 30,
       '{"reading":6,"listening":6,"dictation":2,"pitch_accent":1}'::jsonb,
       95, 0.30, 0.25, true
FROM public.dim_languages l WHERE l.language_code = 'jp'
ON CONFLICT (template_id) DO NOTHING;

INSERT INTO public.dim_study_plan_templates
    (template_id, language_id, daily_minutes, weekly_test_counts,
     practice_total_minutes, base_maintenance_share, practice_minutes_flex_pct,
     is_default)
SELECT 302, l.id, 45,
       '{"reading":8,"listening":8,"dictation":3,"pitch_accent":2}'::jsonb,
       140, 0.30, 0.25, false
FROM public.dim_languages l WHERE l.language_code = 'jp'
ON CONFLICT (template_id) DO NOTHING;

INSERT INTO public.dim_study_plan_templates
    (template_id, language_id, daily_minutes, weekly_test_counts,
     practice_total_minutes, base_maintenance_share, practice_minutes_flex_pct,
     is_default)
SELECT 303, l.id, 60,
       '{"reading":11,"listening":10,"dictation":4,"pitch_accent":3}'::jsonb,
       185, 0.30, 0.25, false
FROM public.dim_languages l WHERE l.language_code = 'jp'
ON CONFLICT (template_id) DO NOTHING;

-- Validate: every active language should have exactly one default template.
DO $$
DECLARE
    v_languages_without_default int;
BEGIN
    SELECT COUNT(*) INTO v_languages_without_default
    FROM public.dim_languages l
    WHERE l.is_active
      AND NOT EXISTS (
        SELECT 1 FROM public.dim_study_plan_templates t
        WHERE t.language_id = l.id AND t.is_default
      );
    IF v_languages_without_default > 0 THEN
        RAISE WARNING '[dim_study_plan_templates] % active languages have no default template — backfill will skip them',
            v_languages_without_default;
    END IF;
END $$;

COMMIT;
