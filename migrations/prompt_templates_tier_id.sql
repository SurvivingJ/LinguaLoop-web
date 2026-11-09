-- ADR-040: tier-keyed question prompt templates (TASK-925).
--
-- Adds a nullable tier_id to prompt_templates. NULL = the base row every
-- reader uses today. A non-NULL tier_id marks a level-specific question
-- template, read only by the test-generation question loader
-- (DatabaseClient.get_prompt_template(..., tier_id=)) and only while
-- TEST_GEN_TIER_TEMPLATES enables it for the language. Every other reader
-- filters tier_id IS NULL (services/prompt_service.base_rows), so adding
-- tier rows changes nothing until the switch is on.
--
-- Data-only schema change on an existing table: no new function or table,
-- so no grants/RLS change (prompt_templates' existing policies apply).
-- Idempotent.

ALTER TABLE public.prompt_templates
    ADD COLUMN IF NOT EXISTS tier_id smallint NULL
    REFERENCES public.dim_complexity_tiers(id);

COMMENT ON COLUMN public.prompt_templates.tier_id IS
    'ADR-040: NULL = base template for all tiers. Set = level-specific '
    'question template for that complexity tier, used only when '
    'TEST_GEN_TIER_TEMPLATES enables it for the language.';

CREATE INDEX IF NOT EXISTS prompt_templates_task_lang_tier_active_idx
    ON public.prompt_templates (task_name, language_id, tier_id, is_active);

-- idx_prompt_templates_task_lang_ver (task_name, language_id, version) stays:
-- other migrations upsert ON CONFLICT on it. Tier rows therefore take their
-- own version range, 100 + tier (T1 = 101 ...), which never meets a base
-- version; base readers filter tier_id IS NULL, so the number is not used to
-- choose between a tier row and its base row.

-- Verify: column exists and no tier rows yet (expect 0).
SELECT count(*) AS tier_rows FROM public.prompt_templates WHERE tier_id IS NOT NULL;
