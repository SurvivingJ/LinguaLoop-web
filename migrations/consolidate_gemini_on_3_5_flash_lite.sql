-- Consolidate EVERY gemini slug onto `google/gemini-3.5-flash-lite`.
-- Date: 2026-08-16
--
-- POLICY (operator decision, 2026-08-16): one gemini slug across the whole
-- system. This applies to JUDGES as well as generators, so it is the one place
-- the judge exclusion in generator_model_routing_policy.sql does not hold.
--
-- SLUG VERIFIED LIVE before applying, against
-- `services.model_arena.pricing.fetch_model_list()` (OpenRouter /api/v1/models).
-- Do not skip this check on a future slug change: the delisting of
-- `qwen/qwen-max` 404'd every Explorer and Gatekeeper call and produced no
-- topics at all, because those agents have no fail-open path -- see the incident
-- note at services/topic_generation/config.py:50-65. `google/gemini-3.5-flash-lite`
-- and `google/gemini-3.5-flash-lite:batch` were both present at apply time.
--
-- SUPERSEDES, for the gemini value only:
--   * distractor_judge_model_zh_ja_gemini.sql  (set the judge to 3.1-flash-lite)
--   * generator_model_routing_policy.sql       (set en generators to 3.1-flash-lite)
-- Both files remain canonical for their POLICY -- which languages route to which
-- vendor, the sonnet-5 carve-out, the judge exclusion list, and the measured
-- evidence behind the zh/ja judge swap. Only the gemini slug moves here.
--
-- COVERED SOURCE SLUGS (active rows):
--   google/gemini-3.1-flash-lite   26  en generators + test_distractor_plausibility (all 3 langs)
--   google/gemini-2.5-flash-lite   11  judges: cloze_distractor_judge, dual_translation_tier1,
--                                      ladder_collocation/l1_distractor/p1_sentence/relation/
--                                      sentence_validity/word_family judges,
--                                      test_answer_entailment, translation_uniqueness_judge
--   google/gemini-3.5-flash         2  dual_translation_tier2/tier3 (en)
--
-- NOT CHANGED: inactive rows keep the slug they actually ran under -- they are
-- the historical record and rewriting them would destroy it. `model IS NULL`
-- prompt-text-only rows are untouched by design (they resolve a model from a
-- sibling row via prompt_service.get_template_text). Non-gemini slugs
-- (qwen/qwen3.7-plus, anthropic/claude-sonnet-5, deepseek/deepseek-chat,
-- qwen/qwen-2.5-72b-instruct, qwen/qwen3.6-flash) are out of scope.
--
-- NOTE ON THE JUDGE A/B: test_answer_entailment is about to be measured
-- cross-model. This sets its en arm's production value; the experiment varies
-- the model explicitly and does not read this column.
--
-- IDEMPOTENT: the `model <> target` predicate makes a re-run a no-op.

BEGIN;

UPDATE public.prompt_templates
   SET model = 'google/gemini-3.5-flash-lite',
       updated_at = now()
 WHERE is_active = true
   AND model LIKE 'google/gemini-%'
   AND model <> 'google/gemini-3.5-flash-lite';

COMMIT;

-- Verification (run manually):
-- SELECT model, count(*) FROM public.prompt_templates
-- WHERE is_active = true GROUP BY 1 ORDER BY 2 DESC;
-- Expect exactly ONE google/* slug: google/gemini-3.5-flash-lite.
