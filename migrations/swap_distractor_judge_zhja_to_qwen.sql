-- Swap the zh + ja distractor-plausibility judge model
--   deepseek/deepseek-v4-flash -> qwen/qwen3.6-flash
--
-- Rationale (A/B 2026-06-06, c:\tmp\ab_qwen_zhja_judge.py): qwen/qwen3.6-flash
-- eliminated deepseek's two defects on zh + ja —
--   (1) the ~14% ja fall-open caused by the model hallucinating extra
--       distractors (5 ratings for 3) -> length mismatch -> safe_accept bypass;
--   (2) the ja reason-language leak (deepseek wrote the Japanese judge's reasons
--       in Chinese).
-- qwen scored 0 fall-opens across 14 calls, 0/33 ja Chinese-leak (all genuine
-- kana), perfect labelled rating sanity (good>=4 / off-topic<=2 / paraphrase=3
-- on both langs), and tighter 15-22s latency. Tradeoff: ~8x per-call cost
-- (~$0.004 vs ~$0.0005), still sub-cent.
--
-- en (language_id=2) is unchanged (google/gemini-3.1-flash-lite).
-- provider stays 'openrouter'. NULL model would safe_accept-bypass the judge,
-- so model is set explicitly.
--
-- Reversible: re-run with model = 'deepseek/deepseek-v4-flash' for the same rows.

update prompt_templates
set model = 'qwen/qwen3.6-flash'
where task_name = 'test_distractor_plausibility'
  and is_active
  and version = 3
  and language_id in (1, 3);
