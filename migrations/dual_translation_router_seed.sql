-- dual_translation_router_seed.sql — prompt_templates rows for the dual-translation
-- grading-cascade model router (TASK-600).
-- Source of truth: wiki/algorithms/translation-grading-cascade.tech.md,
-- wiki/features/dual-translation.tech.md (Reconciliation: model-access row).
--
-- This migration does NOT seed grading prompt text — the L2-only, numerical-index
-- grader prompts are TASK-606's services/dual_translation/prompts.py. Each row here
-- exists purely to give services/dual_translation/router.resolve_tier() a
-- (task_name, language_id) -> (model, provider) lookup; template_text carries a
-- short human-readable note (NOT NULL on prompt_templates) and is never read by the
-- router.
--
-- Tiers (task_name): dual_translation_tier1 (cheap) / tier2 (mid) / tier3
-- (expensive, ships OFF per the cascade spec — reserved for rare low-confidence
-- escalation or calibration; defaults to the tier2 slug until a product decision
-- picks a genuine escalation model).
--
-- Slugs — flash-style, language-dependent (EN -> Gemini-flash family, ZH/JA ->
-- Qwen-flash family), chosen from slugs already confirmed live elsewhere in this
-- repo (wiki/features/exercise-generation-v2.md "Current healthy assignments";
-- wiki/log.md 2026-06-09 qwen-max post-mortem). Do NOT use qwen/qwen-max or
-- google/gemini-flash-1.5 — both are confirmed 404-delisted on OpenRouter (memory
-- `prompt-template-model-slug-rot`).
--   EN (language_id=2): tier1 google/gemini-2.5-flash-lite, tier2/3 google/gemini-3.5-flash
--   ZH (language_id=1): tier1 qwen/qwen3.6-flash,           tier2/3 qwen/qwen3.7-plus
--   JA (language_id=3): tier1 qwen/qwen3.6-flash,           tier2/3 qwen/qwen3.7-plus
--
-- Idempotency: prompt_templates has NO unique (task_name,language_id,version)
-- constraint (only PK on id), so each INSERT is guarded by
-- `WHERE NOT EXISTS (... task_name=? AND language_id=?)`. Re-running is a no-op.

-- ── tier1 (cheap) ────────────────────────────────────────────────────────────

INSERT INTO prompt_templates (task_name, language_id, version, is_active, provider, model, description, template_text)
SELECT 'dual_translation_tier1', 1, 1, true, 'openrouter', 'qwen/qwen3.6-flash',
       'Dual-translation grading cascade, Tier 1 (cheap) — ZH', 'Model-routing row only; no prompt text (see services/dual_translation/prompts.py).'
WHERE NOT EXISTS (
  SELECT 1 FROM prompt_templates WHERE task_name = 'dual_translation_tier1' AND language_id = 1
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, provider, model, description, template_text)
SELECT 'dual_translation_tier1', 2, 1, true, 'openrouter', 'google/gemini-2.5-flash-lite',
       'Dual-translation grading cascade, Tier 1 (cheap) — EN', 'Model-routing row only; no prompt text (see services/dual_translation/prompts.py).'
WHERE NOT EXISTS (
  SELECT 1 FROM prompt_templates WHERE task_name = 'dual_translation_tier1' AND language_id = 2
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, provider, model, description, template_text)
SELECT 'dual_translation_tier1', 3, 1, true, 'openrouter', 'qwen/qwen3.6-flash',
       'Dual-translation grading cascade, Tier 1 (cheap) — JA', 'Model-routing row only; no prompt text (see services/dual_translation/prompts.py).'
WHERE NOT EXISTS (
  SELECT 1 FROM prompt_templates WHERE task_name = 'dual_translation_tier1' AND language_id = 3
);

-- ── tier2 (mid) ──────────────────────────────────────────────────────────────

INSERT INTO prompt_templates (task_name, language_id, version, is_active, provider, model, description, template_text)
SELECT 'dual_translation_tier2', 1, 1, true, 'openrouter', 'qwen/qwen3.7-plus',
       'Dual-translation grading cascade, Tier 2 (mid) — ZH', 'Model-routing row only; no prompt text (see services/dual_translation/prompts.py).'
WHERE NOT EXISTS (
  SELECT 1 FROM prompt_templates WHERE task_name = 'dual_translation_tier2' AND language_id = 1
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, provider, model, description, template_text)
SELECT 'dual_translation_tier2', 2, 1, true, 'openrouter', 'google/gemini-3.5-flash',
       'Dual-translation grading cascade, Tier 2 (mid) — EN', 'Model-routing row only; no prompt text (see services/dual_translation/prompts.py).'
WHERE NOT EXISTS (
  SELECT 1 FROM prompt_templates WHERE task_name = 'dual_translation_tier2' AND language_id = 2
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, provider, model, description, template_text)
SELECT 'dual_translation_tier2', 3, 1, true, 'openrouter', 'qwen/qwen3.7-plus',
       'Dual-translation grading cascade, Tier 2 (mid) — JA', 'Model-routing row only; no prompt text (see services/dual_translation/prompts.py).'
WHERE NOT EXISTS (
  SELECT 1 FROM prompt_templates WHERE task_name = 'dual_translation_tier2' AND language_id = 3
);

-- ── tier3 (expensive, default OFF — placeholder slug = tier2 until a genuine
--    escalation model is chosen; never in the per-submission hot path) ───────

INSERT INTO prompt_templates (task_name, language_id, version, is_active, provider, model, description, template_text)
SELECT 'dual_translation_tier3', 1, 1, true, 'openrouter', 'qwen/qwen3.7-plus',
       'Dual-translation grading cascade, Tier 3 (expensive, default OFF) — ZH', 'Model-routing row only; no prompt text (see services/dual_translation/prompts.py).'
WHERE NOT EXISTS (
  SELECT 1 FROM prompt_templates WHERE task_name = 'dual_translation_tier3' AND language_id = 1
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, provider, model, description, template_text)
SELECT 'dual_translation_tier3', 2, 1, true, 'openrouter', 'google/gemini-3.5-flash',
       'Dual-translation grading cascade, Tier 3 (expensive, default OFF) — EN', 'Model-routing row only; no prompt text (see services/dual_translation/prompts.py).'
WHERE NOT EXISTS (
  SELECT 1 FROM prompt_templates WHERE task_name = 'dual_translation_tier3' AND language_id = 2
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, provider, model, description, template_text)
SELECT 'dual_translation_tier3', 3, 1, true, 'openrouter', 'qwen/qwen3.7-plus',
       'Dual-translation grading cascade, Tier 3 (expensive, default OFF) — JA', 'Model-routing row only; no prompt text (see services/dual_translation/prompts.py).'
WHERE NOT EXISTS (
  SELECT 1 FROM prompt_templates WHERE task_name = 'dual_translation_tier3' AND language_id = 3
);

-- Verification (run manually after migration):
-- SELECT task_name, language_id, model, provider, is_active
-- FROM prompt_templates
-- WHERE task_name LIKE 'dual_translation_tier%'
-- ORDER BY task_name, language_id;
-- Expect 9 rows; language_id=2 (EN) on google/gemini-* slugs, language_id IN (1,3)
-- (ZH/JA) on qwen/* slugs.
