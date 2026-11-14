# Track A — pushing the jev decision-model pipeline for Dual Translation grading

**Date:** 2026-11-14 · **Spend:** $0.1973 of a $0.55 budget (1,788 logged calls, `costs.jsonl`) · **No DB writes, no production code changed, nothing committed.**
**Follows:** `wiki/evaluations/jev-dt-tuning-2026-09-27.md` (the "Sept" pipeline). All Sept code and cached responses were reused read-only.

## 1. Bottom line

- **Error recall is fixed; band agreement is not clearly better.** Pointing jev at an explicit diff of the two sentences raised gold error recall from .52 → .83 (zh), .50 → .96 (ja) and .80 → .92 (en), at precision .93–.96 (Sept: .95–1.0). Minor-error recall went from about half to 27 of 32.
- **Band QWK moved mostly inside the noise.** With n=30 per language, almost every 95% interval on the change versus Sept includes zero. The changes that sit at or just above zero are zh fidelity (+.12), en accuracy (+.04) and understandability in all three languages (+.18 to +.20).
- **zh accuracy is still unsolved by the pre-chosen primary config** (.386 vs Sept .412 vs live .570). A single-call variant frozen at the same time scored .683 on gold, but it was the weakest config on silver, so that is not a result to rely on.
- **Severity cannot be learned from jev's probabilities.** No question separates major from minor (single-feature AUC .44–.72; a fitted logistic model gets 68% versus 76% for the taxonomy's default severity per error type). Severity accuracy on gold is .79 / .64 / .78 (Sept .75 / .54 / .75).
- **Ensembles did not help measurably**: paraphrased questions, English + target-language questions, and three cheap models averaged all landed within noise on silver.
- **OpenRouter now lists about 38 decision models, not one.** Ten were run on the identical request on silver; none is clearly better than jev-1.13. Several are cheaper (`perplexity/pplx-decider-v1.2` is about a third of the price).
- **Cost** stays well under the $0.001 target: $0.00024–0.00035 per item for the two-call primary, $0.00011–0.00014 for the single-call variant. Latency is about 0.35–0.4 s per item.

## 2. Why zh failed in September (free diagnosis from the cached responses)

Replaying the Sept responses on zh silver showed three separate causes.

1. **Detection threshold, not detection ability.** jev's `has_error` probability ranked zh errors well (AUC .985) but sat at .08–.36 for structural errors: word order, adverbial order, a dropped 被, register, 的/地. The Sept grid never tried a cutoff below .5, so these were all missed (zh silver recall .45).
2. **The question wording hid form errors.** "Acceptable variation is not an error", asked over two full passages, led jev to treat grammatical-but-wrong structures as acceptable. The same sentences score .67–.98 once the changed characters are marked (§3).
3. **Severity and dimension.** The zh config asked jev for minor/major/critical directly. It under-called major on complements and aspect markers and over-called critical on a directional complement. A wrong error type also moves the penalty between accuracy and fidelity.

One further point explains why better recall does not raise QWK: **one minor error leaves every band at 4**, so missing minor errors costs nothing in band agreement, while a detected error with the wrong type or severity does.

## 3. What was built

**Arm D ("diff-focused"), one call per changed sentence pair.** The request carries the reference sentence, the learner sentence, and a character-level (zh/ja) or word-level (en) diff: changed fragments wrapped in `[[ ]]` plus a numbered change list. Seventeen questions:

| Group | Questions |
|---|---|
| Detection | strict "would a teacher correct any of these changes"; learner-sentence-only grammaticality |
| Bidirectional meaning | reference → learner (meaning lost or altered); learner → reference (meaning added) |
| Eight narrow error families | word order, grammar word/form (per-language examples), register, word choice, written form, omission, addition, connective |
| Severity | "clearly wrong on first read", "message reversed or lost", minor/major/critical choice |
| Error type | the Sept per-language error-type choice |

A small second call (**D2**) added three questions: "are all changes only a script/spelling variant or true synonym" (`variant_ok`), a paraphrase of the detection question, and a structural-versus-surface severity probe. Questions are answered independently, so in production D2 folds into arm D.

**Fusion with the Sept call.** The Sept request (full passages, target-language questions) is better at meaning changes; arm D is better at form errors. The fused pipeline averages the two detection probabilities, takes the error type from the Sept call, calls an error critical when the mean of four meaning-flip signals is ≥ .7, and otherwise uses the taxonomy's default severity for the error type. Meaning-bearing types (word choice, omission, addition) are graded major when the meaning-change score is ≥ .6. The error list then goes through the live scoring code unchanged, as in September.

**Selection.** One config shared by all three languages, chosen on silver by pooled 5-fold cross-validation over 333 configs. The objective was mean QWK + 0.25 × exact-band rate + 0.10 × detection F1. Four configs and the routing cutoffs were frozen in `frozen_config.json` before gold was scored, and gold was scored once.

| Frozen config | Calls per changed sentence | Settings |
|---|---|---|
| **A_fused** (primary, top of silver) | Sept + D + D2 | mean(D, Sept) ≥ .3; Sept error type; critical ≥ .7; graded severity |
| A_fused_prior | same | same, plain default severity |
| A_sept_refit | Sept only | Sept `has_error` ≥ .3 (was .5); default severity |
| A_D_only | D only | D detection ≥ .3; D error type; critical ≥ .6; default severity |

## 4. Gold results (n=30 per language, scored once)

QWK uses the same function as the Sept report. Brackets are 95% bootstrap intervals.

| Lang | Dimension | Live grader | Sept jev | **A_fused** | A_D_only | A_sept_refit |
|---|---|---|---|---|---|---|
| zh | accuracy | .570 | .412 | .386 [−.04, .73] | .683 [.33, .93] | .528 |
| zh | fidelity | .891 | .773 | .893 [.23, .98] | .839 | .818 |
| zh | understandability | .577 | .737 | .936 [0, 1] | .936 | .737 |
| ja | accuracy | .412 | .455 | .589 [.26, .86] | .923 [.73, 1] | .420 |
| ja | fidelity | .371 | .830 | .930 [.63, 1] | .887 | .877 |
| ja | understandability | .332 | .712 | .912 [.47, 1] | .787 | .866 |
| en | accuracy | .778 | .956 | 1.000 | .953 | 1.000 |
| en | fidelity | .487 | .487 | .524 [−.05, .90] | .242 [0, .65] | .444 |
| en | understandability | .746 | .724 | .907 [0, 1] | .952 | .672 |

Paired bootstrap of A_fused minus Sept: only zh fidelity (+.12 [0, .40]), en accuracy (+.04 [0, .17]) and the three understandability gains (+.18 to +.20, lower bound 0) reach zero or above; every other interval spans zero. A_D_only's ja accuracy gain (+.47 [.07, .91]) is the one interval clearly above zero, and it comes from the config that ranked last on silver.

| Lang | Config | Precision | Recall | Missed (of which minor) | Error type top-1 | Severity right | Exact 3-band match | $ / item |
|---|---|---|---|---|---|---|---|---|
| zh | Sept | 1.00 | .52 | 11 (7) | .75 | .75 | — | .00013 |
| zh | **A_fused** | .95 | .83 | 4 (2) | .74 | .79 | .70 | .00029 |
| zh | A_D_only | .85 | .96 | 1 (1) | .77 | .82 | .73 | .00012 |
| ja | Sept | 1.00 | .50 | 13 | .69 | .54 | — | .00018 |
| ja | **A_fused** | .93 | .96 | 1 (1) | .72 | .64 | .73 | .00035 |
| ja | A_D_only | .86 | .96 | 1 (1) | 1.00 | .84 | .87 | .00014 |
| en | Sept | .95 | .80 | 5 | .95 | .75 | — | .00010 |
| en | **A_fused** | .96 | .92 | 2 (2) | .83 | .78 | .83 | .00024 |
| en | A_D_only | .96 | .92 | 2 (2) | .78 | .74 | .80 | .00011 |

Counting every gold error, A_fused found 27 of 32 minor, 39 of 41 major and 6 of 6 critical. Latency is 0.35–0.39 s median per item with calls in parallel (p95 about 0.5 s). The most expensive single item cost $0.00087.

### Routing (cutoffs fitted on silver)

"Routed" means every changed sentence scores below the cutoff. "Over-graded" means a routed item had a gold band below 4.

| Lang | Signal | Routed | Over-graded | Off by 2+ bands | Routed with any gold error |
|---|---|---|---|---|---|
| zh | Sept (reported) | 2/30 (7%) | 0 | 0 | 1 |
| zh | fused or D | **8/30 (27%)** | 0 | 0 | 1 |
| ja | Sept (reported) | 10/30 (33%) | 0 | 0 | 0 |
| ja | D | 12/30 (40%) | 0 | 0 | 2 |
| ja | fused | 14/30 (47%) | **1 (7%)** | 0 | 4 |
| en | Sept (reported) | 11/30 (37%) | 0 | 0 | 2 |
| en | fused / D | 10/30, 11/30 | 0 | 0 | 1 |

zh routing rose from 7% to 27% with no over-grade. The fused cutoff for ja (.6) was too loose and over-graded one item; use the D signal for ja. All of these rest on 8–14 routed items.

## 5. What did not work, and what was within noise

Silver, 5-fold CV, out-of-fold mean QWK over the three dimensions:

| Idea | zh | ja | en | Verdict |
|---|---|---|---|---|
| Sept features, wider cutoff grid | .63 | .81 | .89 | Free recall gain in en; the cutoff floor was the en/zh recall limit |
| Arm D, jev's own severity choice | .64 | .54 | .53 | **Worse.** jev's minor/major choice is not usable |
| Arm D, default severity per type | .68 | .59 | .54 | Recall .93–1.0 but more band errors |
| + `variant_ok` discount | .68 | .66 | .54 | Helps ja (kana/kanji variants stop being flagged) |
| + paraphrase ensemble (2–3 phrasings) | .68 | .61 | .54 | No gain |
| + English and target-language questions | .68 | .64 | — | No gain; detection AUC unchanged |
| + structural-vs-surface severity probe | .69 | .56 | .49 | No gain |
| Three cheap models averaged | .71 | .62 | .54 | Within noise |
| jev + gemini-decision-1 | .74 | .56 | .52 | Within noise |
| D + Sept fused, per-language search | .64 | .62 | .55 | Unstable: per-language selection over ~35 items overfits |

These out-of-fold numbers swing by ±.1–.2 depending on which config each fold picks. That instability is why the final choice was one pooled config, and why the fused config's edge over a plain Sept refit on silver (objective 1.110 vs 1.101) should be read as a tie on bands.

**Severity.** On 78 non-critical silver errors (39 major), the best single question had AUC .72 and "clearly wrong on first read" had .48. A leave-one-out logistic model on ten probabilities scored 68%; the taxonomy default with jev's predicted type scored 76% (81% with the true type); adding the probabilities to the default gave 78%, a two-item difference. Critical is easy (AUC .96–1.0 for every model).

**Per-clause segmentation** was not run separately; the marked diff is a narrower focus than a clause and made it redundant.

## 6. Other decision models on OpenRouter

`/api/v1/models?output_modalities=all` lists about 38 models on `/api/alpha/decisions` (the default listing hides them). All accept the jev request unchanged. Ten were run on arm D for the full silver set:

| Model | $ / call | Detection AUC zh / ja / en | Error type top-1 zh / ja / en | Latency |
|---|---|---|---|---|
| typesafe/jev-1.13 | .00011 | .96 / .82 / 1.00 | .76 / .61 / .83 | 0.4 s |
| typesafe/jev-1.14 | .00011 | .97 / .80 / 1.00 | .76 / .64 / .80 | 0.3 s |
| google/gemini-decision-1 | .00026 | .97 / **.97** / .99 | .82 / .71 / .83 | 0.4 s |
| openai/gpt-6-luna-decisions | .00040 | .98 / .88 / .97 | .58 / .57 / .83 | 0.5 s |
| perplexity/pplx-decider-v1.2 | **.00004** | .98 / .85 / 1.00 | .79 / .50 / .86 | 0.4 s |
| perplexity/pplx-decider-v1.3:free | 0 | .97 / .89 / 1.00 | .88 / .64 / .86 | 0.5 s |
| liquid/d1-ultra | .00008 | .97 / .92 / 1.00 | .82 / .68 / .83 | 0.4 s |
| microsoft/microsoft-decision-1 | .00008 | .97 / .85 / .99 | .82 / .54 / .74 | 0.4 s |
| respan/span-02 | .00004 | .98 / .91 / .99 | .79 / .61 / .80 | 1.0 s |
| morph/reflex | .00009 | .96 / .85 / 1.00 | .79 / .54 / .83 | 0.9 s |

Silver has only 6–8 clean changed sentences per language, so these AUCs are coarse. `upstage/solar-decide` was dropped after the smoke test (11 s per call). jev-1.14 is not better than 1.13 here.

Three were also scored on gold as a single-call D-only pipeline, with cutoffs fitted on each model's own silver:

| Model | zh acc / fid / und | ja acc / fid / und | en acc / fid / und | Recall zh / ja / en | $ / item |
|---|---|---|---|---|---|
| pplx-decider-v1.2 | .49 / .87 / .94 | .77 / .89 / .69 | .98 / .62 / .79 | .87 / .77 / .96 | .00004 |
| liquid/d1-ultra | .92 / .92 / .94 | .85 / .83 / .76 | .98 / .53 / .79 | .91 / .92 / .92 | .00009 |
| gemini-decision-1 | .83 / .58 / .60 | .85 / .83 / .96 | .98 / .62 / .96 | .87 / .88 / .88 | .00028 |

liquid/d1-ultra's zh accuracy of .92 is the best zh number in this report, but it is the best of seven pipelines looked at on 30 items. Treat it as a lead to re-test.

## 7. Recommended frozen config

For a shadow run, send **both calls per changed sentence** (the Sept A3 request and arm D with `variant_ok` folded in) to `typesafe/jev-1.13`, and store every probability. That costs about $0.0003 per item and lets both A_fused and A_D_only be scored from the same data, which is the only way to settle which is better.

- **Report bands from A_fused** (`frozen_config.json` → `configs.A_fused`): it was the pre-chosen primary and is at or above Sept on eight of nine cells.
- **Use the error list for the strengths-and-weaknesses report now.** Recall of .83–.96 at precision ≥ .93 removes the Sept caveat that it under-counts minor slips.
- **Routing:** fused signal for zh (cutoff .35) and en (.5); D signal for ja (.45).
- **Keep severity as the taxonomy default plus the critical override.** Do not spend more on severity questions.
- **Keep naturalness and range with the live grader.** Not touched here.

## 8. Caveats

- **n=30 per language, about 70% clean.** Differences under roughly .1–.2 QWK are noise, and most intervals here are wider than that.
- **Seven pipelines were scored on gold in one pass** (four jev configs, three other models). The best-looking cells are optimistically biased. Only A_fused was the pre-declared primary.
- **Silver and gold disagree about A_D_only**: last on silver, best on gold for zh/ja accuracy. Silver was deliberately weighted to rare error types and was labelled by three Sonnet raters, not a human.
- **The diff assumes the learner text is a near-copy of the reference.** That is true of every seeded item here. Real learners who rephrase whole sentences will produce large diffs, and arm D may lose its advantage or flag far more. This is untested.
- **Precision fell** from 1.0 to .93–.95 in zh/ja (1–2 false flags on 8–9 clean changed sentences; A_D_only has 4).
- **The fused numbers mix eras**: Sept-side probabilities come from the September cache, arm D from today's calls.
- **A_fused's graded severity** beat plain default severity on silver by 0.0025 in the objective. Its gold advantage in en fidelity (.52 vs .24) is one or two items.

## 9. Files

All under `/home/user/LinguaLoop-web/data/eval/dt_decision_2026-11-14/track_a/`.

| File | What it is |
|---|---|
| `results.json` | Headline metrics |
| `frozen_config.json` | Frozen configs, routing cutoffs, silver selection record |
| `results_gold_full.json` | Full gold output including per-item routing lists |
| `results_silver_search.json`, `results_ablations_silver.json`, `results_models_silver.json` | Silver ablations and model bake-off |
| `lib.py`, `reqs.py`, `collect.py`, `feats.py`, `pipeline.py` | Client with budget guard and cache, request builders, decision rules |
| `search.py`, `pooled.py`, `freeze.py`, `freeze2.py`, `ablate.py`, `models_cmp.py`, `eval_gold.py` | Silver search, freezing, analyses, the one gold run |
| `costs.jsonl`, `cache/` | Per-call ledger (tokens, USD from `usage.cost`) and 1,773 cached responses; re-runs are free |

### Spend by model

| Model | Calls | USD |
|---|---|---|
| google/gemini-decision-1 | 204 | .0517 |
| openai/gpt-6-luna-decisions | 115 | .0442 |
| typesafe/jev-1.13 | 485 | .0391 |
| liquid/d1-ultra | 204 | .0163 |
| typesafe/jev-1.14 | 114 | .0123 |
| morph/reflex | 114 | .0100 |
| microsoft/microsoft-decision-1 | 114 | .0087 |
| perplexity/pplx-decider-v1.2 | 205 | .0078 |
| respan/span-02 | 114 | .0049 |
| upstage/solar-decide | 5 | .0023 |
| perplexity/pplx-decider-v1.3:free | 114 | 0 |
| **Total** | **1,788** | **$0.1973** |
