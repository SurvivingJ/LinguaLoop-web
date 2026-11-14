# Production-path check of the single-call DT grader against v6 gold

**Date:** 2026-11-14 · **OpenRouter spend:** $0.006097 (119 calls, summed from `usage.cost` in the dumped traces; cap was $0.15) · **No DB writes** (the harness reads language ids, passage age tiers and the dictionary; `llm_calls` logging is switched off for eval runs) · **No migration applied.**

## What was run

The production code path, not the experiment harness:
`scripts/run_dt_grading_eval.py --single-call` → `grader_cascade.grade_submission(single_call=True)` → `services/dual_translation/single_call_grader.py`, model `openai/gpt-6-luna`, taxonomy v6 and rubric v6 loaded from their seed files (`--taxonomy-file migrations/dt_taxonomy_v6_seed.sql --rubric-file migrations/dt_rubric_v6_seed.sql --fixture-set v6`).

Scored by `compare.py` the way Track B scored its arms (`track_b/bscore.py`): same `eval_metrics` functions, the 30 v5-derived gold items per language, QWK on accuracy / fidelity / understandability.

## Result

| Lang | Source | acc / fid / und QWK | Precision | Recall |
|---|---|---|---|---|
| en | Track B report (gpt-6-luna · p1_expl) | 1.00 / .84 / .79 | 1.00 | .93 |
| en | **Replay**: production path fed Track B's recorded responses | 1.00 / .84 / .79 | 1.00 | .93 |
| en | **Live** production path | 1.00 / .84 / .79 | 1.00 | .96 |
| zh | Track B report | .74 / .84 / .74 | .96 | .85 |
| zh | **Replay** | .74 / .84 / .74 | .96 | .85 |
| zh | **Live**, run 1 | .59 / .84 / .71 | 1.00 | .81 |
| zh | **Live**, run 2 | .66 / .82 / .74 | 1.00 | .81 |
| ja | Track B report | .92 / .87 / .76 | .96 | .89 |
| ja | **Replay** | .92 / .87 / .76 | .96 | .89 |
| ja | **Live** | .92 / .91 / .76 | .96 | .81 |

- **Replay is exact.** `replay_track_b_cache.py` runs the production path with the model boundary replaced by Track B's response cache. Every one of the 90 requests hit the cache, which is keyed by a hash of the whole request body, so the production prompt, schema, sentence pairing and request parameters are byte-identical to what Track B sent. Every item's bands and error count equal Track B's. The production decode, severity rule and scoring therefore reproduce Track B.
- **Live differs because the model's answers differ between runs**, not because of the code. 20 of 90 items got a different error list than Track B recorded two days of calls earlier (en 5, zh 8, ja 7; listed in `summary.json`): a severity flipped between minor and major, a type swapped (`case_particle` ↔ `particle_other`), or one minor error appeared or disappeared. Two live zh runs differ from each other as well (.59 and .66 accuracy). Temperature is 0; the provider is not deterministic. Track B measured one run and said it had not measured run-to-run variance.
- **Chinese accuracy is the unstable cell** (.59 / .66 / .74 over three runs). The misses are minor-vs-major calls on measure words and 了, the same thing Track B's caveat 5 describes. One item moves this QWK by .05–.15.
- No clean item was flagged in any live run (0 of 30). 6 of 6 meaning inversions were flagged critical.
- No model entry was dropped; 1 span (ja) could not be located and was repaired to its sentence; for 1 of 70 errors the correction shown is the whole reference sentence.
- Fallbacks were not exercised live: all 119 calls returned valid JSON from the primary model.
- p50 latency 1.0–1.2 s. Cost $0.00005 per item on average; the first calls per language cost $0.00015 before the provider's prompt cache warmed.

## Files

- `gold_{en,zh,ja}.md`, `gold_zh_run2.md` — harness reports (their QWK tables use the harness's own metric set, all 31 en items, and include `overall_band`).
- `gold_{en,zh,ja}.jsonl`, `run2_zh.jsonl`, `smoke_en.jsonl` — per-item errors, scores and full `grader_trace`.
- `compare.py` → `summary.json` (first-run numbers, spend, per-item differences from Track B's recorded output).
- `replay_track_b_cache.py` — the zero-cost replay (run from the repo root).
