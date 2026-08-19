-- Model-routing policy for GENERATOR prompts: zh/ja -> qwen, en -> gemini.
-- Date: 2026-08-16
--
-- POLICY (operator decision, 2026-08-16):
--   * zh (1) and ja (3) generators run `qwen/qwen3.7-plus`.
--   * en (2) generators run `google/gemini-3.1-flash-lite`.
--   * `google/gemini-2.5-flash-lite` is retired from every generator row.
--   * JUDGES are explicitly OUT OF SCOPE -- they stay a per-judge experimental
--     track (see the exclusion list below), because a per-language judge model
--     split is what produced the phantom "zh content is bad" signal that
--     TASK-717 + TASK-718 spent two tasks unwinding.
--   * `anthropic/claude-sonnet-5` rows are PRESERVED as the deliberate premium
--     tier: mystery_plot, mystery_scene, ladder_l4_morphology_generation,
--     ladder_syn_ant_generation, ladder_word_family_generation,
--     vocab_prompt2_exercises, vocab_prompt3_transforms (11 rows, en-heavy).
--   * Rows with `model IS NULL` (23 active) are NOT touched here -- their
--     resolution path is under investigation and populating them could override
--     a code-level default. Separate change if they turn out to need it.
--
-- EXPECTED: 59 rows. zh 18, en 23, ja 18. Breakdown by source model --
--   gemini-2.5-flash-lite -> 34 rows  (prose_generation, all six question_*,
--                                      mystery_clue/deduction/question,
--                                      vocab_phrase_detection, vocab_prompt1_core en)
--   gemini-3.7-flash      -> 18 rows  (conversation_* x4, scenario_batch_generation)
--   gemini-3.5-flash      ->  7 rows  (semantic_class_classification,
--                                      cloze_distractor_generation en,
--                                      exercise_sentence_generation en,
--                                      ladder_l8_collocation_repair_generation en,
--                                      semantic_discrimination_generation en)
--
-- COST: `qwen3.7-plus` measured at $0.00376/call against
-- `gemini-2.5-flash-lite` at $0.00011 (30-day averages over `llm_calls`) -- a 34x
-- unit-cost increase on zh/ja generation, accepted deliberately for CJK quality.
-- en moves are near-neutral ($0.00051) except conversation generation, which
-- drops from gemini-3.7-flash ($0.00117) and is therefore also a capability
-- reduction on long-form dialogue -- accepted as part of the uniform policy.
--
-- WHY A UNIFORM RULE AT ALL: the judge work established that per-language model
-- splits create differences that look like content-quality differences and are
-- not. Holding the model constant per language across the whole generator
-- surface makes cross-language quality comparisons meaningful for the first time.
--
-- NOT CHANGED: inactive rows (history), judge rows, sonnet-5 rows, NULL-model
-- rows. Only `is_active = true`.
--
-- IDEMPOTENT: the trailing `model <> <target>` predicate makes a re-run a no-op.
-- REVERSIBLE only from this file's EXPECTED breakdown -- prior per-row values are
-- not preserved anywhere else, so restoring means re-reading the table above.

BEGIN;

UPDATE public.prompt_templates
   SET model = CASE language_id
                   WHEN 2 THEN 'google/gemini-3.1-flash-lite'
                   ELSE 'qwen/qwen3.7-plus'
               END,
       updated_at = now()
 WHERE is_active = true
   AND model IS NOT NULL
   AND model <> 'anthropic/claude-sonnet-5'
   AND language_id IN (1, 2, 3)
   AND task_name NOT IN (
       -- Judges: experimental track, per operator decision.
       'cloze_distractor_judge',
       'dual_translation_tier1',
       'dual_translation_tier2',
       'dual_translation_tier3',
       'gatekeeper_check',
       'ladder_collocation_judge',
       'ladder_l1_distractor_judge',
       'ladder_p1_sentence_judge',
       'ladder_particle_judge',
       'ladder_relation_judge',
       'ladder_sentence_validity_judge',
       'ladder_word_family_judge',
       'test_answer_entailment',
       'test_distractor_plausibility',
       'translation_uniqueness_judge'
   )
   AND model <> CASE language_id
                    WHEN 2 THEN 'google/gemini-3.1-flash-lite'
                    ELSE 'qwen/qwen3.7-plus'
                END;

COMMIT;

-- Verification (run manually):
-- SELECT model, count(*) FROM public.prompt_templates
-- WHERE is_active = true GROUP BY 1 ORDER BY 2 DESC;
-- Expect NO 'google/gemini-2.5-flash-lite' outside the judge exclusion list.
