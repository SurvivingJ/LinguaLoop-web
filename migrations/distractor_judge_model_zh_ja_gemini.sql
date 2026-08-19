-- TASK-718: move the zh and ja distractor-plausibility judge off qwen3.6-flash
-- onto google/gemini-3.1-flash-lite (the model en has always used).
-- Date: 2026-08-16
--
-- WHY: the 30% zh reject rate is a judge artefact, not weaker zh content. A
-- 2x2x3 factorial over the frozen 150-question sample (identical content in every
-- arm; only prompt version and judge model vary) settles it:
--
--     v4 prompt, question-level rejects       qwen3.6-flash   gemini-3.1-flash-lite
--       zh                                       16/50 (32%)        1/50  (2%)
--       en                                        5/50 (10%)        2/50  (4%)
--       ja                                        4/50  (8%)        3/50  (6%)
--
-- Under a COMMON judge (gemini) zh is the CLEANEST of the three languages, not the
-- worst. Under the other common judge (qwen) zh is 32% against en 10% / ja 8% -- so
-- the effect is a qwen-x-Chinese interaction, not a general harshness gradient, and
-- the content contribution is indistinguishable from zero.
--
-- THE DECISIVE NUMBER: of the 25 zh distractors qwen rated 2 ("belongs to a
-- different subject -- reject"), gemini rated 19 a 4 and 6 a 5. Not one landed in
-- gemini's own reject or review band. Question-level, the two judges' zh reject
-- sets are DISJOINT (both=0, qwen-only=16, gemini-only=1). This corroborates the
-- manual read in evaluations/distractor-judge-language-divergence-2026-08-16 s5,
-- which had already judged ~6 of 7 non-vocabulary zh rejects to be false.
--
-- The largest single bucket moves with the model and with nothing else: zh
-- `vocabulary_context` was 9/16 under qwen in ALL FOUR TASK-717 prompt
-- configurations, and is 1/16 under gemini.
--
-- SECONDARY BENEFITS:
--   * gemini restores a middle band (rating 3) in zh and ja -- qwen emits
--     essentially none -- so `generation_review_queue` stops being English-only.
--     The channel is thin (1 zh / 2 ja per 150 distractors) but no longer zero.
--   * gemini produced the first band-1 ratings ever observed on this judge.
--   * 6.7x cheaper: $0.00047/call vs $0.00313, measured over 300 calls each.
--
-- WHY v5 ROWS TOO: v5 stays inactive (TASK-717 measured it as net harmful, and
-- this run reproduces that under gemini: en 2/50 -> 5/50). But leaving qwen on the
-- v5 rows would silently re-introduce the rejected model the moment anyone
-- activates v5. The model decision is per language, not per prompt version.
--
-- NOT CHANGED: v1-v3 rows are history and keep the model they actually ran under.
-- en (language_id 2) is already on gemini at every version, so the predicate
-- leaves it alone.
--
-- LIMITATION, recorded deliberately: this proves qwen's zh rejects are not
-- reproducible under a second judge. It does NOT prove gemini's acceptances are
-- correct -- inter-judge agreement on the reject class is ~0 (zh 0/25, en 0/10,
-- ja 1/5 distractor-level), so neither model's reject signal is trustworthy in
-- absolute terms yet. A gold-set calibration is still owed (TASK-719 / TASK-720).
--
-- IDEMPOTENT: the `model <>` predicate makes a re-run a no-op.
-- REVERSIBLE: set the model back to 'qwen/qwen3.6-flash' for the same rows.

BEGIN;

UPDATE public.prompt_templates
   SET model = 'google/gemini-3.1-flash-lite',
       updated_at = now()
 WHERE task_name = 'test_distractor_plausibility'
   AND language_id IN (1, 3)          -- zh, ja
   AND version IN (4, 5)              -- 4 = live, 5 = retained candidate
   AND model <> 'google/gemini-3.1-flash-lite';

COMMIT;

-- Verification (run manually):
-- SELECT language_id, version, is_active, model
-- FROM public.prompt_templates
-- WHERE task_name = 'test_distractor_plausibility'
-- ORDER BY language_id, version;
