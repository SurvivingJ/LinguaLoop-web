# Track B — cheap generative LLMs as structured DT "decision" graders

**Date:** 2026-11-14 · **OpenRouter spend:** $0.3494 of a $0.55 budget (3,419 calls, every one logged in `costs.jsonl` from `usage.cost`; code guard at $0.50 never fired) · **No DB access, no production code changed, nothing written outside this directory.**

## 1. Bottom line

- **A $0.00002–0.00008/item LLM call matches or beats the live grader's gold agreement, and beats jev on error recall.** Four cheap models (DeepSeek v4.1 Flash, GPT-6 Luna, Qwen 3.8 Flash, Gemma 4 31B) reach a mean QWK of .75–.84 over the nine language × dimension cells, against .76 for the live grader on the same v6 gold (Oct-08 gate, arm B) and .68 for jev (Sept). Error recall is .78–.96 in all three languages, against jev's .50–.52 in zh/ja and the live grader's .73–.93.
- **Cost is at or below jev's**, not between jev and the live grader: $0.00002–0.00015/item actual (with provider prompt caching), $0.00008–0.00025 at uncached list price. That is roughly 300–2,000× cheaper than the live grader. p50 latency is 0.6–1.9 s.
- **Recommended: `deepseek/deepseek-v4.1-flash`, one call per item, span + ≤15-word explanation (`p1_expl`)**, for all three languages: $0.00003/item actual, error recall .96/.89/.93 (en/zh/ja), precision .96, error type right 81–87%, 6 of 6 gold meaning inversions flagged critical. Unlike jev it returns the span and an explanation. `openai/gpt-6-luna` with the same prompt is statistically indistinguishable and is the fallback.
- **Paying more bought nothing here.** Gemini 3.1 Flash-Lite at $0.00047/item (6–16× the price) scored no better than the $0.00003–0.00008 models on silver or gold.
- **Negative results:** Mistral Small 3.2 and Gemini 2.5 Flash-Lite over-flag acceptable variation (Mistral flagged 17–19 of 19 clean silver items when it reads whole sentences; Gemini 2.5 flagged 9 of 10 clean ja gold items). Qwen was not better than the others on Chinese. Chinese accuracy stays weak for every grader (.15–.74; live .56). Asking for a span or an explanation did not improve accuracy. Naturalness is not solved, and range cannot be tested.
- **Main caveat:** every error is a seeded edit in an otherwise near-verbatim copy of the reference, so the task is close to "classify this visible difference". Real learner reproductions diverge more. With n=30 per language (about 10 items below band 4 per dimension), differences under about .1 QWK are noise, and most confidence intervals are wide.

## 2. What was tested

**Task framing.** The model is a decision model: it returns only a strict-JSON-schema list of errors, each with a v6 error type (ADR-031, the per-language list from `merged_taxonomy.json`), a severity (minor/major/critical) and, depending on the variant, the offending learner span and a ≤15-word explanation. Bands are then computed by the unchanged live `services/dual_translation/scoring.py` (`compute_dimension_bands` with `OFFLINE_SCORING_CONFIG`), and all detection/QWK metrics by the live `services/dual_translation/eval_metrics.py`, the same functions the Oct-08 v6 gate used.

**Rubric.** English instructions; type list with the id, the native name and a one-line definition; "not errors" list (synonyms, contractions, kana/kanji variants, optional punctuation). Severity is defined by reader impact, with the Sept lesson written in: *major = clearly wrong to a native reader, even if the meaning is still obvious; it does not require a change of meaning.* Each type shows its taxonomy default severity as a hint.

**Prompt designs** (all temperature 0, `max_tokens` 300–600, reasoning disabled, `response_format: json_schema` strict):

| Variant | What the model sees | What it returns |
|---|---|---|
| `p1_bare` | all sentence pairs of the item (identical sentences shown once) | sentence no., type, severity |
| `p1_span` | same | + offending learner text, verbatim |
| `p1_expl` | same | + span + explanation (English, ≤15 words) |
| `p2` (minimal evidence-first) | only the sentences that differ, plus numbered differences computed by a Python diff ("reference text => learner text") | per difference: `ok` or type + severity. Spans come from the diff. Items with no difference need no call. |

**Severity rule.** Two zero-cost options, chosen per model and language on silver: `model` (use the model's severity) or `prior` (use the taxonomy default for the predicted type, unless the model said critical). This mirrors the rule the Sept jev work chose.

**Models** (prices pulled live from the OpenRouter models list, $/M tokens in/out): `google/gemini-2.5-flash-lite` (.10/.40, the cheapest Gemini Flash-Lite), `openai/gpt-6-luna` (.10/.50), `deepseek/deepseek-v4.1-flash` (.051/.203), `qwen/qwen3.8-flash` (.15/.47), `mistralai/mistral-small-3.2-24b-instruct` (.10/.30), `google/gemma-4-31b-it` (.20/.40), plus `google/gemini-3.1-flash-lite` (.25/1.50) as one mid-price point, run on `p1_expl` only. `z-ai/glm-5.3-flash` was dropped because its reasoning cannot be turned off.

**Data.** Tuning used `tests/fixtures/dt_silver_v6` (the Sept silver set with v6 labels; en 35, zh 34, ja 32). Testing used `tests/fixtures/dt_gold_v6`, restricted to the 30 v5-derived items per language (the one v6-only en item is excluded so n stays 30). Gold was run once, on frozen configs.

**Selection protocol** (`select_cfg.py`, fixed before gold was touched). Per model, the variant with the highest silver mean QWK (accuracy, fidelity, understandability, averaged over the three languages); then per language the severity rule with the higher silver QWK. A second frozen family is `p1_expl` for the three most precise models plus Gemini 3.1, because the feedback team needs spans and explanations. Frozen choices are in `frozen_configs.json`.

## 3. Silver: prompt design, span and explanation

Means over the six models and three languages (model severity):

| variant | mean QWK | span P | span R | type top-1 | sev exact | clean flagged /114 | $/item | out tok |
|---|---|---|---|---|---|---|---|---|
| p1_bare | .76 | .94 | .92 | .70 | .76 | 25 | 0.000083 | 32 |
| p1_span | .76 | .93 | .91 | .72 | .77 | 26 | 0.000081 | 40 |
| p1_expl | .74 | .93 | .93 | .71 | .77 | 30 | 0.000090 | 61 |
| p2 | .77 | .94 | .89 | .74 | .77 | 16 | 0.000081 | 39 |

- **Span and explanation do not change accuracy.** Mean QWK is .76 / .76 / .74 for bare / span / explanation, detection precision and recall move by .01–.02, and type and severity agreement are flat. All of that is inside the noise. Per model the direction is inconsistent (DeepSeek's type accuracy rises .75 → .82 with explanations; Qwen's and Gemma's do not).
- **What they cost:** the span adds about 8 output tokens and no measurable cost; the explanation adds about 20–30 output tokens, about +10% cost per item ($0.000081 → $0.000090 on average). 2 of 169 explanations in the best config ran past 15 words (max 17).
- **Evidence-first (`p2`) is not cheaper in practice** ($0.000081, same as `p1_span`): the rubric and type list dominate the prompt and are prompt-cached either way. Its real effect is fewer false alarms on clean items (16 vs 25–30 flagged, almost all of the gain on Mistral) at slightly lower recall (.89 vs .91–.93). It also guarantees valid spans. It depends on a clean diff, which is the least realistic part of this data (§6).
- **Severity rule:** the taxonomy prior helps English (mean QWK .81 → .84), hurts Chinese (.75 → .72) and is neutral for Japanese. Same direction as the Sept jev finding (prior for en, direct question for zh).
- **JSON validity:** 100% on every arm but one (Mistral `p2`: 1 of 101 answers referred to a difference number that did not exist). Model-quoted spans were found verbatim in the learner text in all but 2 gold cases.

Full silver grid:

| Model | variant | mean QWK(acc,fid,und) | span P | span R | type top-1 | sev exact | clean flagged (of 19) | $/item | out tok |
|---|---|---|---|---|---|---|---|---|---|
| gemini25fl | p1_bare | .67 | .90 | .98 | .65 | .71 | 7 | 0.000077 | 44 |
| gemini25fl | p1_span | .71 | .88 | .94 | .73 | .79 | 7 | 0.000082 | 54 |
| gemini25fl | p1_expl | .70 | .89 | .96 | .70 | .77 | 8 | 0.000096 | 80 |
| gemini25fl | p2 | .76 | .85 | .96 | .76 | .76 | 9 | 0.000075 | 53 |
| gpt6luna | p1_bare | .80 | 1.00 | .87 | .74 | .83 | 0 | 0.000084 | 25 |
| gpt6luna | p1_span | .79 | .99 | .85 | .74 | .79 | 0 | 0.000049 | 30 |
| gpt6luna | p1_expl | .80 | .99 | .88 | .73 | .78 | 0 | 0.000059 | 50 |
| gpt6luna | p2 | .79 | .98 | .90 | .76 | .80 | 0 | 0.000079 | 32 |
| deepseek41f | p1_bare | .84 | .97 | .88 | .75 | .77 | 0 | 0.000035 | 20 |
| deepseek41f | p1_span | .79 | .97 | .88 | .77 | .76 | 0 | 0.000041 | 26 |
| deepseek41f | p1_expl | .81 | .97 | .92 | .82 | .82 | 1 | 0.000048 | 45 |
| deepseek41f | p2 | .73 | .96 | .80 | .76 | .78 | 0 | 0.000037 | 27 |
| qwen38f | p1_bare | .80 | .98 | .89 | .69 | .78 | 0 | 0.000071 | 36 |
| qwen38f | p1_span | .82 | .99 | .94 | .73 | .81 | 0 | 0.000077 | 46 |
| qwen38f | p1_expl | .76 | .98 | .96 | .69 | .78 | 1 | 0.000085 | 69 |
| qwen38f | p2 | .84 | .95 | .89 | .73 | .79 | 0 | 0.000069 | 41 |
| mistral32 | p1_bare | .67 | .77 | .99 | .60 | .68 | 17 | 0.000102 | 42 |
| mistral32 | p1_span | .69 | .79 | .99 | .59 | .68 | 18 | 0.000106 | 55 |
| mistral32 | p1_expl | .65 | .77 | .98 | .56 | .69 | 19 | 0.000112 | 77 |
| mistral32 | p2 | .69 | .91 | .96 | .67 | .72 | 7 | 0.000097 | 45 |
| gemma4 | p1_bare | .77 | .99 | .88 | .75 | .77 | 1 | 0.000129 | 23 |
| gemma4 | p1_span | .75 | .97 | .87 | .78 | .79 | 1 | 0.000133 | 30 |
| gemma4 | p1_expl | .72 | .96 | .88 | .77 | .78 | 1 | 0.000141 | 48 |
| gemma4 | p2 | .78 | .99 | .84 | .75 | .80 | 0 | 0.000128 | 37 |
| gemini31fl | p1_expl | .79 | .97 | .94 | .74 | .79 | 0 | 0.000486 | 68 |

## 4. Gold: cost versus quality frontier

n=30 per language. QWK cells are accuracy/fidelity/understandability. "mean QWK (9)" is the plain mean of the nine cells. Cost is the actual average charge per graded item. Rows above the baselines are sorted as run: first each model's silver-selected variant, then the `p1_expl` family.

| Grader | $/item (actual) | en acc/fid/und | zh acc/fid/und | ja acc/fid/und | mean QWK (9) | err recall en/zh/ja | err precision en/zh/ja | p50 s |
|---|---|---|---|---|---|---|---|---|
| google/gemini-2.5-flash-lite · p2 | 0.000059 | .93/.89/.95 | .46/.84/.94 | .49/.65/.37 | .72 | .96/1.00/.96 | .93/.90/.74 | 0.62 |
| openai/gpt-6-luna · p1_bare | 0.000080 | 1.00/.84/.79 | .59/.82/.74 | .92/.89/.73 | .81 | .96/.89/.96 | .96/1.00/1.00 | 1.23 |
| deepseek/deepseek-v4.1-flash · p1_bare | 0.000022 | .94/.80/.75 | .52/.89/.90 | .61/.81/.68 | .77 | .96/.89/.96 | .96/.96/1.00 | 1.81 |
| qwen/qwen3.8-flash · p2 | 0.000061 | .93/.82/.63 | .46/.87/.94 | 1.00/.92/.85 | .82 | .89/.89/.85 | 1.00/1.00/1.00 | 1.37 |
| mistralai/mistral-small-3.2-24b-instruct · p2 | 0.000094 | 1.00/.84/.79 | .39/.81/.94 | .64/.78/.96 | .79 | 1.00/.96/.93 | .96/.81/.86 | 1.01 |
| google/gemma-4-31b-it · p2 | 0.000124 | 1.00/.80/.67 | .39/.78/.74 | .75/.85/.79 | .75 | .93/.85/.78 | 1.00/1.00/1.00 | 0.81 |
| deepseek/deepseek-v4.1-flash · p1_expl | 0.000030 | .94/.80/.75 | .61/.89/.88 | .92/.83/.70 | .81 | .96/.89/.93 | .96/.96/.96 | 1.83 |
| qwen/qwen3.8-flash · p1_expl | 0.000079 | 1.00/.80/.67 | .46/.90/.94 | 1.00/.90/.89 | .84 | .93/.89/.81 | 1.00/.89/.92 | 1.46 |
| openai/gpt-6-luna · p1_expl | 0.000055 | 1.00/.84/.79 | .74/.84/.74 | .92/.87/.76 | .83 | .93/.85/.89 | 1.00/.96/.96 | 1.36 |
| google/gemini-3.1-flash-lite · p1_expl | 0.000473 | 1.00/.86/.79 | .15/.78/.74 | .85/.87/.79 | .76 | .93/.89/.89 | 1.00/.96/.96 | 1.31 |
| jev step-by-step (Sept, v5 labels) | 0.00013–0.00023 | .96/.49/.72 | .41/.77/.74 | .46/.83/.71 | .68 | .80/.52/.50 | .95/1.00/1.00 | ~0.3 s |
| live grader, v5 (Jul-19, as quoted in brief) | 0.025–0.05 | .78/.49/.75 | .57/.89/.58 | .41/.37/.33 | .57 | —/—/— | —/—/— | minutes (ja) |
| live grader, v6 arm B (Oct-08 gate) | 0.025–0.05 | .51/.85/.81 | .56/.86/.94 | .41/.93/.93 | .76 | .93/.73/.78 | 1.00/.95/1.00 | minutes (ja) |

How to read the baselines:

- **Live grader, v6 arm B** is the like-for-like baseline: same v6 gold fixtures, same metric code.
- **jev** was scored on the v5 fixtures. For zh and ja the expected bands are identical under v5 and v6, so those cells compare directly. For **en they do not**: v6 moved the two meaning inversions from accuracy to fidelity, so jev's en .96/.49 and the July live en .78/.49 are on a different band key. Scored against the old v5 en bands, every config here gets about .33–.41 accuracy and .27–.43 fidelity for that reason alone (`qwk_vs_v5_bands` in `results.json`).
- Live-grader cost is the Sept report's estimate ($0.025 en, $0.042–0.058 zh/ja).

What the frontier shows:

1. **There is no slope between $0.00002 and $0.0005.** DeepSeek, GPT-6 Luna and Qwen at $0.00003–0.00008 are as good as Gemini 3.1 Flash-Lite at $0.00047 and as good as the live grader at $0.025–0.05, on this data. The frontier is flat, and its low-cost end is the cheapest model.
2. **Against jev:** recall in zh/ja goes from about .50 to .78–.96 at near-equal precision (.89–1.00 for the four precise models), ja accuracy from .46 to .61–1.00, and zh understandability/fidelity are equal or better. The models also return spans and explanations, which jev cannot.
3. **Against the live grader (v6):** en accuracy .93–1.00 vs .51 is large enough to trust, and ja accuracy (.61–1.00 for the four precise models vs .41) probably is. Fidelity and understandability are level or slightly lower (ja und .68–.89 vs .93; en und .63–.79 vs .81), inside the intervals. zh is a tie.
4. **Meaning inversions** (the en "with it" → "without it" class): 2 of 2 flagged and rated critical in every language by every config, except Gemini 2.5 Flash-Lite in ja (1 of 2 critical). On silver the recommended config caught 17 of 17 as critical (en 8, zh 5, ja 4). The cost is some over-use of the label: the recommended config typed 3 non-inversion gold errors as `meaning_inversion` (en 1, ja 2), which makes them critical.

Detail per config and language (bootstrap 95% intervals, 1,000 resamples):

| Config | lang | sev rule | acc [95% CI] | fid [95% CI] | und [95% CI] | nat* | span P/R/F1 (TP/FP/FN) | type top-1 | sev exact | clean items flagged | MI flagged/critical/typed (n=2) | JSON valid | $/item | p50/p90 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemini25fl p2 | en | prior | .93 [.84, 1.00] | .89 [.14, .98] | .95 [.92, 1.00] | .47 | .93/.96/.94 (26/2/1) | .77 | .85 | 1/10 | 2/2/2 | 100% | 0.000041 | 0.62/0.75 |
| gemini25fl p2 | zh | model | .46 [.07, .81] | .84 [-.13, .96] | .94 [.00, 1.00] | .00 | .90/1.00/.94 (26/3/0) | .69 | .65 | 3/10 | 2/2/2 | 100% | 0.000061 | 0.55/2.67 |
| gemini25fl p2 | ja | model | .49 [.16, .78] | .65 [.12, .90] | .37 [.00, .91] | .00 | .74/.96/.84 (26/9/1) | .65 | .69 | 9/10 | 2/1/1 | 100% | 0.000076 | 0.64/1.64 |
| gpt6luna p1_bare | en | prior | 1.00 [1.00, 1.00] | .84 [.43, .98] | .79 [.00, 1.00] | .78 | .96/.96/.96 (26/1/1) | .85 | .89 | 0/10 | 2/2/2 | 100% | 0.000149 | 1.23/2.03 |
| gpt6luna p1_bare | zh | model | .59 [.20, .90] | .82 [.31, .97] | .74 [-.03, 1.00] | .00 | 1.00/.89/.94 (23/0/3) | .83 | .74 | 0/10 | 2/2/2 | 100% | 0.000043 | 1.13/2.11 |
| gpt6luna p1_bare | ja | model | .92 [.72, 1.00] | .89 [.64, 1.00] | .73 [-.03, .97] | .00 | 1.00/.96/.98 (26/0/1) | .85 | .81 | 0/10 | 2/2/2 | 100% | 0.000048 | 1.35/2.39 |
| deepseek41f p1_bare | en | prior | .94 [.71, 1.00] | .80 [.47, .98] | .75 [.00, 1.00] | .47 | .96/.96/.96 (26/1/1) | .81 | .85 | 0/10 | 2/2/2 | 100% | 0.000017 | 1.92/2.91 |
| deepseek41f p1_bare | zh | model | .52 [.14, .84] | .89 [.23, .98] | .90 [.00, 1.00] | .00 | .96/.89/.92 (23/1/3) | .78 | .78 | 1/10 | 2/2/2 | 100% | 0.000017 | 1.69/2.24 |
| deepseek41f p1_bare | ja | model | .61 [.26, .90] | .81 [.56, .97] | .68 [.17, .97] | .00 | 1.00/.96/.98 (26/0/1) | .69 | .69 | 0/10 | 2/2/2 | 100% | 0.000030 | 1.81/2.56 |
| qwen38f p2 | en | prior | .93 [.84, 1.00] | .82 [.54, 1.00] | .63 [-.06, .94] | .47 | 1.00/.89/.94 (24/0/3) | .88 | .88 | 0/10 | 2/2/2 | 100% | 0.000053 | 1.38/2.01 |
| qwen38f p2 | zh | model | .46 [.04, .79] | .87 [.29, .97] | .94 [.00, 1.00] | -.05 | 1.00/.89/.94 (23/0/3) | .70 | .91 | 0/10 | 2/2/2 | 100% | 0.000056 | 1.37/2.81 |
| qwen38f p2 | ja | model | 1.00 [1.00, 1.00] | .92 [.69, .98] | .85 [.49, 1.00] | .00 | 1.00/.85/.92 (23/0/4) | .70 | .83 | 0/10 | 2/2/2 | 100% | 0.000073 | 1.33/1.83 |
| mistral32 p2 | en | model | 1.00 [1.00, 1.00] | .84 [.37, .98] | .79 [.00, 1.00] | .47 | .96/1.00/.98 (27/1/0) | .70 | .85 | 1/10 | 2/2/2 | 100% | 0.000075 | 0.92/2.55 |
| mistral32 p2 | zh | model | .39 [-.03, .71] | .81 [-.11, .94] | .94 [.00, 1.00] | -.05 | .81/.96/.88 (25/6/1) | .64 | .76 | 6/10 | 2/2/2 | 100% | 0.000098 | 1.06/2.7 |
| mistral32 p2 | ja | model | .64 [.33, .89] | .78 [.07, .96] | .96 [.63, 1.00] | -.05 | .86/.93/.89 (25/4/2) | .72 | .76 | 4/10 | 2/2/2 | 100% | 0.000108 | 1.01/2.03 |
| gemma4 p2 | en | prior | 1.00 [1.00, 1.00] | .80 [.47, .98] | .67 [.00, 1.00] | .47 | 1.00/.93/.96 (25/0/2) | .80 | .84 | 0/10 | 2/2/2 | 100% | 0.000104 | 0.81/1.1 |
| gemma4 p2 | zh | model | .39 [-.03, .71] | .78 [.17, .94] | .74 [-.03, 1.00] | .00 | 1.00/.85/.92 (22/0/4) | .68 | .73 | 0/10 | 2/2/2 | 100% | 0.000128 | 0.91/2.93 |
| gemma4 p2 | ja | prior | .75 [.43, 1.00] | .85 [.58, .97] | .79 [.37, 1.00] | .00 | 1.00/.78/.88 (21/0/6) | .67 | .67 | 0/10 | 2/2/2 | 100% | 0.000140 | 0.8/1.74 |
| deepseek41f p1_expl | en | prior | .94 [.73, 1.00] | .80 [.52, .98] | .75 [.00, 1.00] | .47 | .96/.96/.96 (26/1/1) | .81 | .85 | 0/10 | 2/2/2 | 100% | 0.000018 | 1.83/3.04 |
| deepseek41f p1_expl | zh | model | .61 [.29, .84] | .89 [.00, .98] | .88 [-.05, 1.00] | .00 | .96/.89/.92 (23/1/3) | .87 | .74 | 1/10 | 2/2/2 | 100% | 0.000033 | 1.8/3.45 |
| deepseek41f p1_expl | ja | prior | .92 [.76, 1.00] | .83 [.62, .98] | .70 [.26, 1.00] | .00 | .96/.93/.94 (25/1/2) | .84 | .80 | 0/10 | 2/2/2 | 100% | 0.000037 | 1.95/3.09 |
| qwen38f p1_expl | en | prior | 1.00 [1.00, 1.00] | .80 [.47, .98] | .67 [.00, 1.00] | .78 | 1.00/.93/.96 (25/0/2) | .88 | .84 | 0/10 | 2/2/2 | 100% | 0.000078 | 1.46/1.85 |
| qwen38f p1_expl | zh | model | .46 [.09, .78] | .90 [.35, .98] | .94 [.00, 1.00] | -.05 | .89/.89/.89 (23/3/3) | .74 | .83 | 1/10 | 2/2/2 | 100% | 0.000085 | 1.62/3.75 |
| qwen38f p1_expl | ja | model | 1.00 [1.00, 1.00] | .90 [.57, .98] | .89 [.00, 1.00] | .00 | .92/.81/.86 (22/2/5) | .82 | .82 | 0/10 | 2/2/2 | 100% | 0.000073 | 1.42/2.06 |
| gpt6luna p1_expl | en | prior | 1.00 [1.00, 1.00] | .84 [.37, .98] | .79 [.00, 1.00] | .78 | 1.00/.93/.96 (25/0/2) | .80 | .84 | 0/10 | 2/2/2 | 100% | 0.000043 | 1.22/2.13 |
| gpt6luna p1_expl | zh | model | .74 [.38, 1.00] | .84 [.46, .99] | .74 [-.03, 1.00] | .00 | .96/.85/.90 (22/1/4) | .77 | .73 | 0/10 | 2/2/2 | 100% | 0.000054 | 1.56/3.43 |
| gpt6luna p1_expl | ja | model | .92 [.73, 1.00] | .87 [.63, .98] | .76 [.29, 1.00] | .00 | .96/.89/.92 (24/1/3) | .79 | .83 | 0/10 | 2/2/2 | 100% | 0.000066 | 1.36/2.2 |
| gemini31fl p1_expl | en | prior | 1.00 [1.00, 1.00] | .86 [.48, 1.00] | .79 [.00, 1.00] | .47 | 1.00/.93/.96 (25/0/2) | .80 | .88 | 0/10 | 2/2/2 | 100% | 0.000415 | 1.31/1.44 |
| gemini31fl p1_expl | zh | model | .15 [-.17, .53] | .78 [.29, .94] | .74 [-.03, 1.00] | .00 | .96/.89/.92 (23/1/3) | .61 | .83 | 1/10 | 2/2/2 | 100% | 0.000483 | 1.28/1.42 |
| gemini31fl p1_expl | ja | prior | .85 [.64, 1.00] | .87 [.63, .98] | .79 [.37, 1.00] | .65 | .96/.89/.92 (24/1/3) | .71 | .79 | 0/10 | 2/2/2 | 100% | 0.000521 | 1.31/1.5 |

\* Naturalness is a derived proxy (band 3 if any naturalness-type error was reported, else 4), not a model judgement. Gold has only 2–3 items per language below 4, so the column carries almost no information. **Range cannot be computed**: it is 4 on every gold item.

Span precision/recall for `p1_bare` is flattering: with no span, the whole sentence is used as the predicted span, so any reported error in the right sentence counts as a hit.

## 5. Recommendation

| Language | Model + prompt | Severity rule | Gold acc/fid/und | Recall / precision | Type top-1 | $/item (actual / uncached list) |
|---|---|---|---|---|---|---|
| en | `deepseek/deepseek-v4.1-flash` · `p1_expl` | taxonomy prior | .94/.80/.75 | .96/.96 | .81 | $0.000018 / $0.00009 |
| zh | `deepseek/deepseek-v4.1-flash` · `p1_expl` | model's own | .61/.89/.88 | .89/.96 | .87 | $0.000033 / $0.00009 |
| ja | `deepseek/deepseek-v4.1-flash` · `p1_expl` | taxonomy prior | .92/.83/.70 | .93/.96 | .84 | $0.000037 / $0.00009 |

- This was the best explaining config on silver (mean QWK .81, type top-1 .82, 1 of 19 clean items flagged), so the choice does not rest on gold. Gold agrees with it.
- **Fallback / second opinion:** `openai/gpt-6-luna` · `p1_expl` ($0.00005/item, mean gold QWK .83, 0 of 30 clean gold items flagged, p50 1.4 s). `qwen/qwen3.8-flash` is equally good for ja (1.00/.90/.89) but was not better for zh, so there is no case for a zh-specific Qwen route.
- Keep the explanation field on: about +10% cost, no accuracy loss, and it is what makes the output usable as feedback.
- Do not use Mistral Small 3.2 or Gemini 2.5 Flash-Lite for this without the diff-based prompt; they flag acceptable variation.
- DeepSeek was served by Baidu in this run (OpenRouter's routing) and had the slowest p50 (1.8 s). If provider location or latency matters, pin a provider or use GPT-6 Luna.
- Next step is the same as in September: shadow this on real submissions before trusting any of it. At $0.00003/item a shadow run costs nothing.

`best_outputs.jsonl` holds the recommended config's per-item output for all 90 gold and 101 silver items: predicted errors (sentence, char span, learner text, type, model severity, final severity, explanation), predicted and expected bands, and the gold errors for comparison.

## 6. Caveats

1. **Synthetic, local errors.** Reproductions are verbatim copies with 0–4 seeded edits, so the error is always the visible difference between REF and LRN. Real reproductions will paraphrase, and both whole-sentence reading and especially the `p2` diff will be noisier. The clean-item false-positive rates here (0–1 of 10 for the precise models) are measured on clean items that differ from the reference by one acceptable substitution; they say little about heavy paraphrase.
2. **n=30 per language, single run.** Roughly 6–10 items per language sit below band 4 on any dimension, so one item moves QWK by .05–.15. Intervals such as [.00, 1.00] are common. No run-to-run variance was measured (temperature 0, one pass; providers are not guaranteed deterministic).
3. **Tuning and test share passages.** As in September, en and ja silver reuse the gold passages with different planted errors. Only the variant and the severity rule were chosen on silver; the prompts were written once and not iterated.
4. **Costs include prompt caching.** The ~1,000-token rubric is identical for every item in a language, and several providers billed it at a cached rate, so actual cost is 2–4× below uncached list price. At low or bursty traffic expect the list-price figure ($0.00008–0.00025). Either way it is in jev's range.
5. **Chinese accuracy is unsolved** (.15–.74 here, .56 live, .41 jev). The misses are severity calls on grammar slips (minor vs major on 了/过 and measure words) and accuracy-vs-fidelity type confusions (complement labelled omission), not missed errors.
6. **Severity agreement is .65–.91**, level with the live grader's .46–.81 and with the .62–.85 the three silver raters reached among themselves, so it is near the ceiling this data supports.
7. **Explanations were not evaluated.** They read plausibly on a spot check and are in English; nobody judged their correctness or usefulness. That is the feedback team's question.
8. **Baselines are quoted, not re-run.** Live-grader and jev numbers come from the Oct-08 gate and the Sept report; model drift since then is not controlled.

## 7. Spend

| Model | Calls | USD |
|---|---|---|
| google/gemini-3.1-flash-lite | 192 | 0.0920 |
| google/gemma-4-31b-it | 492 | 0.0647 |
| mistralai/mistral-small-3.2-24b-instruct | 492 | 0.0505 |
| qwen/qwen3.8-flash | 581 | 0.0429 |
| openai/gpt-6-luna | 584 | 0.0397 |
| google/gemini-2.5-flash-lite | 492 | 0.0386 |
| deepseek/deepseek-v4.1-flash | 584 | 0.0208 |
| meta-llama/llama-4-scout (smoke only) | 2 | 0.0003 |
| **Total** | **3,419** | **0.3494** |

Smoke tests (2–6 items per model) ran before any full arm and put a silver arm at about $0.012; actual arms cost $0.004–0.013, except Gemini 3.1 at $0.049.

## 8. Files

- `REPORT.md`, `results.json` (frontier, full gold and silver metrics, frozen configs, spend), `best_outputs.jsonl`
- `gold_results.json`, `silver_results.json`, `frozen_configs.json`
- `common.py` (prompts, schemas, diff, OpenRouter client with cache, ledger and budget guard), `run.py`, `bscore.py`, `select_cfg.py`, `final.py`, `make_tables.py`, `export_best.py`
- `runs/*.jsonl` (decoded per-item output of every arm), `cache/` (raw responses keyed by request hash), `costs.jsonl` (ledger)
- Reproduce without spending: `python3 select_cfg.py && python3 final.py && python3 make_tables.py && python3 export_best.py` (all served from cache)
