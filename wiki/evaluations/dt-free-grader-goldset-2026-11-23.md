---
title: "DT single-call grader: gold-set check of the two free stand-in models"
type: evaluation
status: complete
last_updated: 2026-11-23
open_questions:
  - "OPEN: ADR-044 has no numeric pass thresholds. This page uses the evidence the owner approved on (validated gpt-6-luna runs, and the heavy-paraphrase result for which deepseek-v4.1-flash was rejected as primary) as the bar. Should ADR-044 get explicit thresholds so later model swaps can be gated mechanically?"
  - "OPEN: Production now grades with models that fail this bar. Revert DT_SINGLE_CALL_MODEL / DT_SINGLE_CALL_FALLBACK_MODEL to the validated pair once the key is funded, or keep grading with free models (and accept more false flags on rephrased answers) in the meantime? Owner decision."
  - "OPEN: The 21 live grades from 2026-11-16 to 11-18 were made by these models. Should they be re-graded or marked, given the false-flag rate on free translations measured here?"
  - "OPEN: In production a free-model call that fails (8 of 294 particle calls here were upstream 429s) goes to the fallback model and then to the configured v1/v2 flow, whose paid models are refused while the key is capped. Is that chain still what is wanted?"
  - "OPEN: If a free model is kept, it needs its own severity rule: rule 'model' costs English accuracy agreement (QWK .82 / .49 against luna's 1.00). Fitting one on gold (as done here for illustration) would be test-set tuning; it should be fitted on silver."
---

# DT single-call grader: gold-set check of the two free stand-in models

## Question

Since 2026-11-16 `config.py` defaults the ADR-044 single-call grader to two free-tier models,
`particle-ai/particle-1:free` (primary) and `nvidia/nemotron-3.5-super-vl:free` (fallback), because the
OpenRouter key hit its spending limit. They were never run against the gold set. Only
`openai/gpt-6-luna` and `deepseek/deepseek-v4.1-flash` were validated
([[decisions/ADR-044-dt-single-call-generative-grader]], [[evaluations/dt-decision-grading-2026-11-14]] §9.1).
Live, 20 grades were made by particle and 1 by nemotron between 2026-11-16 and 11-18.
Do these two models meet the bar ADR-044 was approved on, in the configuration production uses?

## Method

**Production configuration, unchanged.** Every grade went through the unmodified harness
`scripts/run_dt_grading_eval.py --single-call --fixture-set v6 --rubric-file migrations/dt_rubric_v6_seed.sql
--taxonomy-file migrations/dt_taxonomy_v6_seed.sql` and the production code path
(`grader_cascade.grade_submission` → `single_call_grader.grade`). For these slugs that means: the guard
prompt variant `v2_guard` (`single_call_grader.py:449`, slug not in `VALIDATED_MODELS`), severity rule
`model` (`:462`), `reasoning: {enabled: false}` (`REQUEST_EXTRAS`), temperature 0, `max_tokens` 1400,
strict `json_schema`, 30 s timeout, prompt version `dt-single-call/v2-quotes-5dim/2026-11-14`, the same
sanitiser, decode, low-confidence withholding and scoring. One request per configuration was dumped and
checked. The rubric and taxonomy seed files equal the live active rows (v6 / v6; jsonb md5 identical).

**Three configurations.**

| Config | Model | Prompt variant | Why |
|---|---|---|---|
| particle · guard | particle-1:free | `v2_guard` | live since 2026-11-17 |
| nemotron · guard | nemotron-3.5-super-vl:free | `v2_guard` | live fallback |
| particle · unguarded | particle-1:free | `v2` | the first 11 live grades (2026-11-16) predate the guard |

The unguarded variant was produced by adding the slug to `VALIDATED_MODELS` for the run only, which
changes nothing but the guard (the severity rule stays `model`). The other 2026-11-17 code changes
(entry normalisation, de-duplication, injection handling) are present in all three runs, so "unguarded"
reproduces the 11-16 prompt, not the 11-16 code exactly.

**Data.** The full v6 gold set (91 items; scored on the same 90 as ADR-044, 4 of them resolved by Tier 0
without a model call) and, because ADR-044's primary/fallback choice rested on it, the Track E heavy
paraphrase stress set (53 items). One run per configuration; no sampling.

**Isolation.** No Supabase credentials in the process; a read-only fixture stub served the rows the
harness reads (languages; no `dt_passage` rows, as live). `llm_calls` logging off; the v1/v2 fallback
flow and its model boundary blocked; model fallback disabled; every SDK call checked against the two
allowed slugs. Upstream 429s were retried with backoff (8 times, all recovered on the first retry).

**Scoring.** A copy of `data/eval/dt_decision_2026-11-14/prod_check/v2/score.py` (the ADR-044 scorer).
Rescoring the recorded gpt-6-luna runs with it reproduces §9.1 exactly, so the columns compare directly.
Intervals: Wilson 95% for proportions, item-bootstrap 95% for QWK.

## Results

### Gold set (90 items)

| | gpt-6-luna run 1 / run 2 (validated) | particle · guard | nemotron · guard | particle · unguarded |
|---|---|---|---|---|
| Clean items flagged | 0/30 / 0/30 | **2/30** [.02, .21] | 0/30 [0, .11] | 1/30 [.01, .17] |
| Pooled precision | .97 / .99 | .92 [.84, .96] | .97 [.90, .99] | .95 [.87, .98] |
| Pooled recall | .91 / .89 | .89 [.80, .94] | .86 [.77, .92] | .88 [.79, .93] |
| TP / FP / FN | 73/2/7 · 71/1/9 | 71/6/9 | 69/2/11 | 70/4/10 |
| en QWK acc / fid / und | 1.00/.89/.79 · 1.00/.86/.79 | .82/.82/.70 | **.49**/.84/.75 | .82/.82/.70 |
| zh QWK acc / fid / und | .59/.82/.75 · .68/.84/.75 | .62/.84/.74 | .53/.82/.58 | .68/.92/.94 |
| ja QWK acc / fid / und | .92/.91/.76 · .92/.89/.76 | .85/.84/.66 | .75/.85/.73 | .85/.83/.70 |
| en / zh / ja P · R | 1.00·.96 / .96·.96 / .96·.81 (run 1) | .96·.93 / .88·.85 / .92·.89 | 1.00·.93 / .96·.85 / .96·.81 | 1.00·.93 / .88·.81 / .96·.89 |
| Overall band exact (of 86), QWK | 80, .81 / 79, .77 | 78, .65 | 79, .74 | 78, .74 |
| Gold critical errors graded critical | 6/6 | 6/6 | 6/6 | 6/6 |
| Malformed / dropped entries | 0 | 0 (2 low-confidence withheld) | 0 (1 withheld) | 0 |
| Learner quote located exactly | 75/75 | 77/77 | 71/71 | 74/74 |
| Model explanation shown | 72/75 | 76/77 | 63/71 | 73/74 |

QWK intervals are wide at n=30 per language (e.g. zh accuracy, particle guard .62 [.26, .90]). Most gold
cells overlap luna's. The clear differences are English accuracy (severity, below) and clean items flagged:
particle flagged `simple → basic` (en) and `我每当 → 我每次` (zh) as `medium` minor word-choice errors.
ADR-044's first prompt draft was rejected for the same kind of flag.

### Heavy paraphrase (Track E, 53 items, 152 correct rephrased sentences, 19 clean items)

| | gpt-6-luna (validated) | deepseek-v4.1-flash, prompt v1 (rejected as primary) | particle · guard | nemotron · guard | particle · unguarded |
|---|---|---|---|---|---|
| Precision | .94 [.82, .99] | .60 | **.59** [.47, .71] | **.23** [.17, .32] | **.63** [.50, .75] |
| Recall | .85 [.71, .93] | .82 | .88 [.74, .95] | .75 [.60, .86] | .82 [.68, .91] |
| Correct rephrased sentences flagged | 2/152 | 12/152 | 16/152 [.07, .16] | 38/152 [.19, .32] | 11/152 [.04, .13] |
| Clean items flagged | 0/19 | 2/19 | 4/19 | 3/19 | 2/19 |
| en / zh / ja precision | .93 / 1.00 / .92 | — | .65 / .91 / .43 | .58 / .24 / .14 | .87 / 1.00 / .37 |

Nemotron reports almost every rephrased Chinese or Japanese sentence as `word_choice` or `addition`, often
at confidence `high`, so withholding `low` does not help. Particle's false flags are mostly minor and
concentrated in Japanese.

### Severity (rule `model`)

Matched errors, gold `severity_v2` in rows, the model's own severity in columns (pooled over en/zh/ja):

| gold \ model | particle · guard: minor / major / critical | nemotron · guard: minor / major / critical |
|---|---|---|
| minor | 16 / 12 / 0 | 23 / 4 / 0 |
| major | 1 / 30 / 6 | 16 / 17 / 3 |
| critical | 0 / 0 / 6 | 0 / 0 / 6 |

Exact agreement, rule `model` vs rule `prior` (taxonomy default severity of the predicted type unless critical):

| | en | zh | ja | pooled |
|---|---|---|---|---|
| particle · guard | .60 vs .84 | .77 vs .77 | .83 vs .75 | .73 vs .79 |
| nemotron · guard | .52 vs .88 | .77 vs .77 | .73 vs .77 | .67 vs .81 |
| gpt-6-luna run 1 (model's own severity) | .73 vs .92 | .64 vs .84 | .82 vs .82 | .73 vs .86 |

Particle over-grades (12 of 28 gold minors called major, 6 majors called critical); nemotron
under-grades (16 of 36 gold majors called minor). Both validated models use `prior` for English, and
these two need it too: English accuracy QWK .82 (particle) and .49 (nemotron) against luna's 1.00 is the
severity rule, not detection (English P/R matches luna). These rule comparisons are measured on the test
set (n = 21–26 errors per language) and are indicative only.

### Reliability, latency, tokens, cost

- 437 model calls: 294 to particle (286 answered, 8 upstream 429 "temporarily rate-limited upstream", each
  answered after one 15 s retry), 143 to nemotron (all answered). No other slug was called.
- No malformed JSON, no shape failure, no unknown type, no unlocatable quote; every `finish_reason` was `stop`.
- Call latency p50 / p90: particle 1.09 / 2.61 s, nemotron 1.31 / 3.13 s (luna 1.6–1.7 s p50).
- Tokens per graded item: about 2,140–2,320 in and 147–156 out (luna 2,455 / 112). Reported cost $0.

## Verdict

ADR-044 states no numeric thresholds. Measured against the evidence it was approved on (luna: no clean
item flagged on gold, gold P/R about .97–.99 / .89–.91, heavy-paraphrase precision .94 with 2 of 152
correct sentences flagged; deepseek was not made primary at heavy precision .60 and 12 of 152):

| Config | Verdict | Why |
|---|---|---|
| particle · guard (live since 2026-11-17) | **FAILS** | heavy precision .59 vs .94 (16/152 sentences, 4/19 clean items); 2/30 clean gold items flagged vs 0/30 |
| nemotron · guard (live fallback) | **FAILS** | heavy precision .23 vs .94 (38/152 sentences, 3/19 clean items); gold detection otherwise close |
| particle · unguarded (live 2026-11-16) | **FAILS** | heavy precision .63 vs .94 (11/152 sentences, 2/19 clean items); 1/30 clean gold item flagged |

On near-copy gold all three come close to luna on detection. They fail where ADR-044 drew its line
between luna and deepseek: free, rephrased translations, which is what real learners write. Neither has
a fitted severity rule.

## Recommendation

This is a recommendation, not a decision; the owner decides ([[decisions/ADR-044-dt-single-call-generative-grader]] status note, 2026-11-23).

1. Revert `DT_SINGLE_CALL_MODEL` and `DT_SINGLE_CALL_FALLBACK_MODEL` to the validated pair
   (`openai/gpt-6-luna`, `deepseek/deepseek-v4.1-flash`) as soon as the OpenRouter key is funded, as the
   comment in `config.py` already says.
2. If a free model has to stay in the meantime, keep `particle-ai/particle-1:free` as primary and remove
   `nvidia/nemotron-3.5-super-vl:free` as fallback (set `DT_SINGLE_CALL_FALLBACK_MODEL` to blank, which
   disables the model fallback). Nemotron flags 38 of 152 correct rephrased sentences (precision .23);
   particle flags 16 (.59). Both still fail the bar, but nemotron fails by far more.
3. Neither model has a fitted severity rule; see the open questions.

## Limitations

- One run per configuration, on seeded gold errors; the heavy-paraphrase set has 152 correct sentences and 40 errors. Run-to-run variance at temperature 0 is real (luna's zh accuracy QWK ranged
  .52–.68); differences under about .1 QWK are noise.
- Gold errors are seeded and the stress paraphrases are synthetic and model-verified (§6 of
  [[evaluations/dt-decision-grading-2026-11-14]]). No real submissions.
- The gold set has no prompt-injection items, so the guard's purpose was not tested. The guard did not
  measurably change detection (particle guard vs unguarded is within noise).
- `word_choice` variant resolution ran without dictionary reads (`dim_vocabulary` not served), so every
  variant fell back to `default`. This does not affect any metric above (luna's recorded runs were all
  `default` as well).
- Gold passage ids have no `dt_passage` rows, so default age tiers were used, as in the validated runs.
- The "unguarded" run uses today's decode code, not the exact 2026-11-16 code.

## Raw data

The raw results are not yet filed in the repository (the run directory is scratch space; the wiki does not
write to `data/`). Copy to `data/eval/dt_free_grader_2026-11-23/` if kept. Contents: per-item JSONL
(`<config>_<l2>.jsonl`, `<config>_heavy_<l2>.jsonl`), harness reports (`.md`), call and event logs,
the dumped request, the exact command lines, analysis.json, analysis_stress_heavy.json, and the
wrapper offline_eval.py.

## Related Pages
- [[decisions/ADR-044-dt-single-call-generative-grader]]
- [[evaluations/dt-decision-grading-2026-11-14]]
- [[features/dual-translation.tech]]
- [[tasklist/dt-single-call-grader.tasks]]
