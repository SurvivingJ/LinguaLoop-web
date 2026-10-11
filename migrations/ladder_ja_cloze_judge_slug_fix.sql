-- Fix the ja (language_id=3) `cloze_distractor_judge` row's stale model slug.
--
-- Background (2026-10-04 armB_ja eval incident, see the long comment at
-- services/llm_service.py's `_is_no_endpoints_for_parameters` /
-- `_strip_param_routing`): this row was pinned to `qwen/qwen-2.5-72b-instruct`,
-- which still matches the `^qwen/` family pattern that
-- `_use_enabled_false_reasoning_param` uses to pick the validated
-- `reasoning: {'enabled': False}` + `provider.require_parameters: True`
-- payload for qwen calls -- but qwen-2.5-72b-instruct only has 2 OpenRouter
-- endpoints, and strict parameter filtering eliminated both of them every
-- time ("No endpoints found that can handle the requested parameters" /
-- failed_routing_step: "Filter by Parameters"). `_make_one_call` now has a
-- transport-layer retry-once-without-overrides fallback for exactly this
-- shape of 404, so the judge no longer fails outright -- but every call still
-- burns a wasted first attempt, and the underlying data problem (wrong model
-- pinned) was never fixed at the source.
--
-- `qwen/qwen-2.5-72b-instruct` is NOT delisted on OpenRouter (confirmed live
-- 2026-10-05: the model page is still active) -- this is a config/data
-- inconsistency, not a dead slug. Every other active ja ladder-adjacent judge
-- row (ladder_particle_judge, ladder_collocation_judge,
-- ladder_l1_distractor_judge, ladder_relation_judge,
-- ladder_sentence_validity_judge, ladder_p1_sentence_judge) already runs on
-- `qwen/qwen3.7-plus`; this row was simply never migrated alongside them.
--
-- Template is carried over verbatim from v1 (id=156) -- this is a model-only
-- fix, not a prompt rewrite. It already contains "JSON" (the output-shape
-- instruction), confirmed via a read-only prompt_templates query
-- (ADR-028 cost-work session, 2026-10-05). Note: there is already an
-- inactive v2 row (id=252) for this task_name/language_id from an earlier,
-- abandoned attempt whose template_text does NOT contain "JSON" -- this
-- migration does not touch or reactivate that row; it lands as v3.
--
-- en (language_id=2, google/gemini-3.5-flash-lite) and zh (language_id=1,
-- deepseek/deepseek-chat) rows for this task_name are untouched.
--
-- NOT APPLIED as of this file's authorship (ADR-028 cost-work session,
-- 2026-10-05) -- drafted for review only, per that session's instructions.

-- Deactivate every existing ja row for this task (both v1 and the abandoned
-- v2), then insert the fixed version.
UPDATE prompt_templates
   SET is_active = false, updated_at = now()
 WHERE task_name = 'cloze_distractor_judge'
   AND language_id = 3;

INSERT INTO prompt_templates
       (task_name, language_id, version, is_active, description, template_text, model, provider)
SELECT task_name, language_id, 3, true,
       description || ' [v3: model slug fixed qwen/qwen-2.5-72b-instruct -> qwen/qwen3.7-plus, matching the other active ja ladder judges; template unchanged from v1]',
       template_text, 'qwen/qwen3.7-plus', provider
  FROM prompt_templates
 WHERE task_name = 'cloze_distractor_judge'
   AND language_id = 3
   AND version = 1;

-- --------------------------------------------------------------------------
-- Rollback: deactivate v3 and reactivate v1.
-- --------------------------------------------------------------------------
-- UPDATE prompt_templates SET is_active = false, updated_at = now()
--  WHERE task_name = 'cloze_distractor_judge' AND language_id = 3 AND version = 3;
-- UPDATE prompt_templates SET is_active = true, updated_at = now()
--  WHERE task_name = 'cloze_distractor_judge' AND language_id = 3 AND version = 1;

-- --------------------------------------------------------------------------
-- Other prompt_templates rows checked for stale/delisted model slugs during
-- this session's read-only survey of all active rows (130 total, 69 on a
-- qwen model). None of the below were confirmed delisted on OpenRouter (spot
-- -checked live 2026-10-05) and none are touched by this migration -- listed
-- here only as candidates worth a closer look, not as confirmed bugs:
--
--   * qwen/qwen-2.5-72b-instruct (1 row -- the one this migration fixes)
--   * qwen/qwen3.6-flash (2 rows: dual_translation_tier1, lang 1 + 3) --
--     older qwen generation than qwen3.7-plus used everywhere else active;
--     model page confirmed still live, and this may be an intentional
--     cheaper-model choice for tier1 rather than drift -- not touched here.
--   * deepseek/deepseek-chat (2 rows: cloze_distractor_judge lang=1 v1,
--     and one inactive v2 of the same) -- model page confirmed still live;
--     distinct from `deepseek/deepseek-v4-flash` used elsewhere in the repo,
--     but not confirmed stale -- may be an intentional per-task choice.
--   * anthropic/claude-sonnet-5 (5 rows) -- current-generation slug, not
--     flagged as stale by this survey; listed only for completeness since it
--     was the next most-common non-qwen/non-gemini model.
-- --------------------------------------------------------------------------
