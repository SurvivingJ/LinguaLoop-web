-- Move the live ja test_answer_entailment judge off qwen/qwen-2.5-72b-instruct
-- onto google/gemini-3.5-flash-lite.
--
-- Applied live 2026-08-19 (TASK-723).
--
-- WHY
-- ---
-- TASK-723 activated the v3 Likert prompt in all three languages on
-- 2026-08-19 10:11:32Z. Measured the same day on the frozen 150-question gold
-- sample (data/eval/entailment_sample_150.json, structural labels: the correct
-- answer is entailed, its distractors are not), holding the v3 prompt fixed
-- and varying ONLY the model:
--
--   ja arm                          AUC    false-accept  false-reject  band-3
--   qwen/qwen-2.5-72b-instruct     0.870      18/100        1/50        24.7%
--   google/gemini-3.5-flash-lite   0.940       2/100        5/50         2.7%
--   deepseek/deepseek-chat         0.798      33/100        4/50         4.0%
--
-- zh (deepseek-chat) and en (gemini-3.5-flash-lite) score 0.990 / 0.982 on the
-- same prompt, so the ja deficit was the model, not the ja prompt and not ja
-- content -- the same conclusion TASK-718 reached about qwen for the distractor
-- judge. This is the one active judge row the 2026-08-16 sweep
-- (consolidate_gemini_on_3_5_flash_lite.sql) could not reach, because it swept
-- gemini rows only and this row was on qwen.
--
-- The trade is 18% -> 2% false-accept for 2% -> 10% false-reject. This judge is
-- the answer-hallucination guard: a false accept ships an unsupported answer to
-- a learner, a false reject regenerates a question. The trade is in the right
-- direction for what the guard is for.
--
-- Template text is untouched -- only the model column -- so no line-ending or
-- JSON-token risk. Verified by readback: ja v3 length 494 and body md5
-- df168c48f2b9b92ea53715438788b680 unchanged, "JSON" token present.
--
-- Cache note: services/exercise_generation/judges/answer_entailment.py caches
-- template config for the process lifetime (_cfg_cache, never invalidated), so
-- this takes effect on the next app start.

UPDATE prompt_templates pt
SET    model      = 'google/gemini-3.5-flash-lite',
       updated_at = now()
FROM   dim_languages dl
WHERE  dl.id = pt.language_id
  AND  pt.task_name = 'test_answer_entailment'
  AND  dl.language_code = 'ja'
  AND  pt.version = 3
  AND  pt.is_active = true;
