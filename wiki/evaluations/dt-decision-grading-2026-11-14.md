---
title: "Cheap grading and feedback for Dual Translation: decision models vs cheap LLMs — Experiment Report"
type: evaluation
status: complete
last_updated: 2026-11-14
open_questions:
  - "OPEN: Do any of these results hold on REAL learner submissions? Every number comes from seeded errors (Tracks A–D) or model-written paraphrases (Track E). A shadow run is the next step."
  - "OPEN: Where do shadow-run results get stored? DT grading is not logged to llm_calls. This question has been open since [[evaluations/jev-dt-tuning-2026-09-27]]."
  - "OPEN: Is gpt-6-luna really more robust than deepseek-v4.1-flash on free translations, or did the GPT-family checker that built the Track E set flatter it?"
  - "OPEN: Which feedback design does the owner choose: focused correction, guided self-repair or pattern coach? All three are proposed; none is selected."
  - "OPEN: All three design specs were written against the September jev grader (error probabilities per sentence, spans from the character diff). A single-call LLM grader returns an error list with spans and no probabilities. How do the specs' confidence states and 'where' marks map onto that output?"
  - "OPEN: Should the grader prompt carry the 'free translations are expected' paragraph? It removes false flags and lowers recall on near-verbatim answers; Track E calls it a product decision."
  - "OPEN: Who does the native-speaker review of a sample of LLM explanations and of the hint templates (AI-drafted, unreviewed)?"
  - "OPEN: Chinese accuracy is weak for every grader tested (.15–.74 for the cheap LLMs, .56 live). Is that acceptable, or does zh need its own work?"
  - "OPEN: Naturalness and range were not attempted. Do they stay with the live grader?"
---

# Cheap grading and feedback for Dual Translation (DT): decision models vs cheap LLMs

**Date:** 2026-11-14 · **OpenRouter spend:** $1.272 of a $3.00 cap, read from the key's usage counter (figure supplied by the experiment's orchestrator). The five track ledgers add up to $1.2691: A $0.1973, B $0.3494, C $0.0665, D $0.2164, E $0.4395. · **No DB writes, no production code changed.**
**Artifacts:** `data/eval/dt_decision_2026-11-14/track_a/` … `track_e/` (each has a `REPORT.md`, `results.json`, harness, cached responses and a `costs.jsonl` ledger).
**Follows:** [[evaluations/jev-dt-tuning-2026-09-27]], which tuned the jev decision model to grade DT and recommended a shadow run.

## 1. Purpose and budget

September showed that jev, a cheap classifier, could grade DT by answering narrow questions per sentence, but it missed about half the errors in Chinese and Japanese and could not write explanations. This experiment asked three things:

1. Can the decision-model pipeline be pushed further, and is jev the right decision model?
2. Is a cheap generative LLM, asked for a structured error list, a better "decision" grader at the same price?
3. Once an error is found, what is the cheapest way to produce feedback a learner can learn from?

Each track had its own budget ($0.55 for A–D, $0.60 for E) with a code guard below it. No guard fired.

| Track | Question | Spend | Calls |
|---|---|---|---|
| A | Diff-focused jev, and a bake-off of other decision models | $0.1973 | 1,788 |
| B | Cheap LLMs returning a structured error list | $0.3494 | 3,419 |
| C | Cascades: jev as router or verifier around a cheap LLM | $0.0665 | 1,308 |
| D | Feedback text: templates vs LLM | $0.2164 | 657 |
| E | Paraphrase stress test of the frozen graders | $0.4395 | 1,494 |

## 2. Bottom line

- **Recommended primary DT grader candidate: `openai/gpt-6-luna`, one call per item, structured output with the error span.** `deepseek/deepseek-v4.1-flash` with the same prompt is the cheaper alternative.
- **Decision models (jev and the others) are not recommended for DT error feedback.** They hold up on near-copies of the reference and break when the learner rephrases: they flag most correct rephrased sentences.
- **Spans should come from the LLM grader, not from the character diff.** On heavily rephrased text the diff is a small local edit for only 12 of 40 errors.
- **Feedback text:** templates for direct corrections, hints and clean-item messages ($0); one LLM call with the live Explainer prompt for explanations; a leak filter in code; supply lexical facts to the prompt.
- **Nothing here was tested on real learner submissions.** The next step is a shadow run, which still needs somewhere to store results.

## 3. Method

**All tracks end in the same place.** Each grader produces a list of errors (type and severity). The unchanged live scoring code (`services/dual_translation/scoring.py`) turns that list into accuracy, fidelity and understandability bands, as in September. QWK measures agreement on an ordered scale; above about .6 is good.

**Gold is for testing only.** The human-adjudicated gold items (30 per language) were scored once per track, on configs frozen beforehand. **Silver is for tuning:** the 101 silver items from September (en 35, zh 34, ja 32), labelled by three Sonnet raters. Tracks A and C used the v5 labels and fixtures (`tests/fixtures/dt_gold/`); Tracks B, D and E used the v6 fixtures (`tests/fixtures/dt_gold_v6`, `dt_silver_v6`). Results labelled post-hoc in the track reports were computed after gold was seen and are not relied on here.

| Track | What was built | Tuned on | Tested on |
|---|---|---|---|
| A | One jev call per changed sentence that carries a marked diff of the two sentences (17 questions), fused with the September call. One config for all languages, chosen from 333 by pooled 5-fold CV. Ten decision models run on the same request. | silver | gold, once; 7 pipelines in one pass, `A_fused` the pre-declared primary |
| B | Six cheap LLMs plus one mid-price model, four prompt variants (bare, + span, + span and ≤15-word explanation, diff-based), strict JSON schema, temperature 0. Variant and severity rule chosen per model on silver. | silver | gold, once |
| C | jev gate → LLM (C1); LLM recall pass → jev verifier (C2); escalation of uncertain items to the recorded live grader (C3); cheap LLM alone and jev alone as references. Rule fixed in advance: among configs within .02 of the best CV score, take the cheapest. | silver | gold, once |
| D | 45 gold items, 56 errors. Detection held constant (gold annotation given to every generator). Hand-written templates vs three LLMs in five styles. Two LLM judges, then manual adjudication of every flagged text. | not tuned | 1,076 texts |
| E | 60 gold items rewritten as free translations by `anthropic/claude-sonnet-5`, each sentence checked by `openai/gpt-6.1-terra`; failed sentences reverted to gold. Three levels: original, moderate (49% of sentences rephrased), heavy (90%). Frozen configs from A and B, nothing retuned. | — | 173 stress items |

Track C's stage-2 models were `qwen/qwen3.7-flash`, `deepseek/deepseek-v4.1-flash` and `anthropic/claude-haiku-5.5`; Track B's Qwen was `qwen/qwen3.8-flash`. The live-grader baseline also differs by track: Track B quotes the v6 gate's arm B, Track C recomputes from the recorded 2026-10-08 per-item outputs on v5 labels. Compare numbers within a track, not across tracks.

## 4. Results by track

### 4.1 Track A: diff-focused jev fixes recall; band gains are within noise

Gold, n=30 per language. `A_fused` is the pre-chosen primary; `A_D_only` is the single-call variant.

| Lang | Config | Precision | Recall | Severity right | acc / fid / und QWK | $ / item |
|---|---|---|---|---|---|---|
| zh | Sept jev | 1.00 | .52 | .75 | .412 / .773 / .737 | .00013 |
| zh | **A_fused** | .95 | .83 | .79 | .386 / .893 / .936 | .00029 |
| zh | A_D_only | .85 | .96 | .82 | .683 / .839 / .936 | .00012 |
| ja | Sept jev | 1.00 | .50 | .54 | .455 / .830 / .712 | .00018 |
| ja | **A_fused** | .93 | .96 | .64 | .589 / .930 / .912 | .00035 |
| ja | A_D_only | .86 | .96 | .84 | .923 / .887 / .787 | .00014 |
| en | Sept jev | .95 | .80 | .75 | .956 / .487 / .724 | .00010 |
| en | **A_fused** | .96 | .92 | .78 | 1.000 / .524 / .907 | .00024 |
| en | A_D_only | .96 | .92 | .74 | .953 / .242 / .952 | .00011 |

- **Recall is fixed.** `A_fused` found 27 of 32 minor, 39 of 41 major and 6 of 6 critical gold errors.
- **Band agreement is not clearly better.** In the paired bootstrap of `A_fused` minus September, only zh fidelity (+.12 [0, .40]), en accuracy (+.04 [0, .17]) and the three understandability gains (+.18 to +.20, lower bound 0) reach zero or above. Every other interval spans zero.
- **zh accuracy is unsolved** by the primary config (.386, against .412 in September and .570 live). `A_D_only` scored .683 on gold but ranked last on silver, so that number is not one to rely on.
- **Severity cannot be learned from jev's probabilities.** No question separates major from minor (single-feature AUC .44–.72). A fitted logistic model gets 68%; the taxonomy's default severity per error type gets 76%.
- **Ensembles did not help measurably:** paraphrased questions, English plus target-language questions, and three cheap models averaged were all within noise on silver.
- **Other decision models.** OpenRouter lists about 38; ten were run on silver and none is clearly better than `typesafe/jev-1.13`. `perplexity/pplx-decider-v1.2` costs about a third as much. `liquid/d1-ultra` scored zh accuracy .92 on gold, the best zh number in the track, but it is the best of seven pipelines looked at on 30 items.

### 4.2 Track B: one cheap LLM call matches or beats the live grader

Gold, n=30 per language. "mean QWK (9)" is the plain mean of the nine language × dimension cells. Cost is the actual charge per item, with provider prompt caching.

| Grader | $ / item | mean QWK (9) | Error recall en / zh / ja | Error precision en / zh / ja | p50 s |
|---|---|---|---|---|---|
| `deepseek/deepseek-v4.1-flash` · span + explanation | 0.000030 | .81 | .96 / .89 / .93 | .96 / .96 / .96 | 1.83 |
| `openai/gpt-6-luna` · span + explanation | 0.000055 | .83 | .93 / .85 / .89 | 1.00 / .96 / .96 | 1.36 |
| `qwen/qwen3.8-flash` · span + explanation | 0.000079 | .84 | .93 / .89 / .81 | 1.00 / .89 / .92 | 1.46 |
| `google/gemini-3.1-flash-lite` · span + explanation | 0.000473 | .76 | .93 / .89 / .89 | 1.00 / .96 / .96 | 1.31 |
| jev step by step (Sept, v5 labels) | 0.00013–0.00023 | .68 | .80 / .52 / .50 | .95 / 1.00 / 1.00 | ~0.3 |
| Live grader, v6 arm B (Oct-08 gate) | 0.025–0.05 | .76 | .93 / .73 / .78 | 1.00 / .95 / 1.00 | minutes (ja) |

- **Cost is at or below jev's:** $0.00002–0.00015 per item actual, $0.00008–0.00025 at uncached list price.
- **Paying more bought nothing.** Gemini 3.1 Flash-Lite at $0.00047 per item scored no better than the $0.00003–0.00008 models.
- **Asking for a span or an explanation did not change accuracy** (silver mean QWK .76 / .76 / .74 for bare / span / explanation). The explanation adds about 10% to cost.
- **Meaning inversions:** the recommended DeepSeek config flagged 6 of 6 on gold as critical, and 17 of 17 on silver. It also typed 3 non-inversion gold errors as `meaning_inversion`.
- **Negative results.** Mistral Small 3.2 and Gemini 2.5 Flash-Lite over-flag acceptable variation (Mistral flagged 17–19 of 19 clean silver items when reading whole sentences; Gemini 2.5 flagged 9 of 10 clean ja gold items). Qwen was not better on Chinese. Chinese accuracy stays weak for every grader (.15–.74; live .56). Naturalness is not solved and range cannot be tested.
- Track B recommended DeepSeek, with GPT-6 Luna as a statistically indistinguishable fallback. Track E changes that order (§4.5).
- For en, jev's September numbers are on the v5 band key and do not compare directly with the v6 rows. zh and ja do.

### 4.3 Track C: cascades with jev lose to the cheap model alone

Gold, pooled over the three languages (n=90), per-language frozen configs. Live-grader figures are recomputed from recorded October outputs.

| Pipeline | mean QWK [95% CI] | Δ vs jev alone [95% CI] | $ / item |
|---|---|---|---|
| jev alone (Sept frozen) | .761 [.59, .86] | — | 0.000136 |
| Live grader (recorded) | .667 [.40, .80] | −.107 [−.30, +.02] | 0.007356 |
| **Cheap LLM alone**, one call per changed sentence | .828 [.68, .92] | +.071 [−.03, +.18] | 0.000079 |
| C1: jev gate → LLM | .651 [.51, .79] | −.100 [−.25, +.08] | 0.000152 |
| C2: LLM recall pass → jev verify | .616 [.45, .78] | −.135 [−.30, +.06] | 0.000036 |

- **The router costs more than the stage it protects.** One jev sentence call costs $0.00008–0.00015; one flash-class call on the same sentence costs about $0.00002. Every jev-first cascade costs more than sending every changed sentence to the cheap model.
- **Neither cascade beat jev alone on gold.** The differences are within noise; in English both were clearly worse in point estimate (.50 and .48 against .72), because of two items where Qwen labelled the with → without inversion `word_choice`.
- **There is no useful "uncertain band".** jev's probabilities for the errors it misses sit at the level of clean sentences. Chinese minor recall goes from .11 to .89 only when 100% of changed sentences are escalated.
- **The jev verifier is a precision filter that costs recall.** No verifier threshold raised gold QWK in any language.
- **Escalating uncertain items to the live grader does not help**, and ordering by jev uncertainty is no better than random.
- **Model selection on silver did not transfer.** The cheap models' rank order on silver is close to the reverse of their order on gold.

### 4.4 Track D: templates for corrections and hints, an LLM for explanations

56 gold errors. "Good" means both judges gave full correctness and at least 1 of 2 on usefulness and clarity. G1 = `qwen/qwen3.7-flash`, G2 = `deepseek/deepseek-v4.1-flash`, G3 = `openai/gpt-6-luna`.

| Style | Template | G1 | G2 | G3 | Note |
|---|---|---|---|---|---|
| Direct correction ("X → Y") | **96%** | 91% | 96% | 96% | Template costs $0 |
| Elicitation hint | **78%** | 64% | 80% | 91% | Template never leaked the answer (0% by judge); LLM hints leaked 9–40% |
| Metalinguistic rule, no answer | 20% | 51% | 76% | 82% | LLMs broke the no-answer rule in 22–66% of texts |
| Explanation (live Explainer prompt) | 55% (live Rule template alone) | 89% | **94%** | **91%** | $0.000033 / $0.000050 / $0.000114 per error-bearing submission |
| Summary on 9 clean items | **9 / 9** | 6 / 9 | 7 / 9 | 8 / 9 | One Qwen summary invented a correction |

- **Wrong texts, after manual adjudication of 39 flagged texts:** Qwen 6 of 269 (2.2%), DeepSeek 1 of 264 (0.4%), GPT-6 Luna 2 of 269 (0.7%), templates 2 of 213. DeepSeek and GPT-6 Luna had none in the explanation style. Qwen is not recommended for learner-facing prose.
- **The two LLM judges cannot count hallucinations.** One flagged 26 texts, the other 15, and they agreed on 2 (κ = 0.08). 27 of the 39 flags were judge errors.
- **Where the LLMs went wrong:** explanations that need a lexical fact the prompt did not supply (a verb's conjugation class, an adjective's class). One Japanese item accounts for 4 of the 12 upheld errors.
- **Where templates went wrong:** a type that covers several different mistakes (`topic_comment`), and a template that asserts a fact based on an upstream label (`word_choice` variants).
- **Guards to add in code:** a leak filter on any LLM hint or rule text, with the template as fallback (the code check agreed with the better judge at κ = 0.74); a length cap per style; never call the LLM for a clean-item summary; pass lexical facts from the dictionary.
- **Cost of the recommended mix:** p × $0.000077 with DeepSeek, where p is the share of submissions with an error; $0.00005 per submission at the gold set's 67%. With GPT-6 Luna, p × $0.000183, about $0.00012.
- Track D also lists the fields a grading result must carry for each style and proposes five additions to `dt_error_instance` for tracking error patterns. Those are proposals for the design work, not decisions.

### 4.5 Track E: on free translations the decision models collapse and the LLMs mostly hold

Pooled over the three languages. "Heavy" = 53 items with 90% of sentences rephrased. Clean rephrased sentences are sentences the verifier accepted as correct.

| Grader | Precision, orig → heavy | Recall, orig → heavy | Clean items flagged, heavy | Correct rephrased sentences flagged, heavy | mean QWK (9), orig → heavy | $ / item, orig → heavy |
|---|---|---|---|---|---|---|
| `openai/gpt-6-luna` | .96 → .91 | .88 → .72 | 0 / 19 | 1 / 152 | .94 → .89 | 0.000051 → 0.000057 |
| `deepseek/deepseek-v4.1-flash` | .96 → .60 | .96 → .82 | 2 / 19 | 12 / 152 | .88 → .71 | 0.000029 → 0.000034 |
| `A_fused` (jev-1.13) | .95 → .42 | .89 → .90 | 10 / 19 | 49 / 152 | .77 → .66 | 0.000247 → 0.000838 |
| `A_D_only` (jev-1.13) | .90 → .25 | .96 → .95 | 18 / 19 | 115 / 152 | .90 → .58 | 0.000116 → 0.000406 |
| D-only on `liquid/d1-ultra` | .94 → .42 | .92 → .85 | 13 / 19 | 47 / 152 | .91 → .65 | 0.000087 → 0.000306 |
| `A_sept_refit` (jev-1.13, no diff) | 1.00 → .72 | .66 → .53 | 0 / 19 | 8 / 152 | .78 → .69 | 0.000130 → 0.000431 |

- **The decision pipelines flag correct rephrased sentences** at 31% (`d1-ultra`), 32% (`A_fused`) and 76% (`A_D_only`). Clean items lost a band in 7, 3 and 15 of 19 cases respectively. The only decision config that does not over-flag is the September-style one, which finds about half the errors.
- **GPT-6 Luna is the most robust:** no clean item flagged at any level, and a false-flag rate of 0.7% on correct rephrased sentences. DeepSeek's rate is 7.9%; almost all of its false flags are minor, and no clean item lost a band under either LLM.
- **Both LLMs lose recall when the error sits in a rephrased sentence.** Of 31 such errors DeepSeek found 27 and GPT-6 Luna 24. The misses are mostly errors that exist only relative to the reference (a near-synonym, a tense, a dropped modifier).
- **The diff stops locating the error.** It is a small local edit for 46 of 49 errors in the original wording, 31 of 49 at moderate and 12 of 40 at heavy paraphrase.
- **The LLM's own span does locate it.** At heavy, whenever an LLM flagged the right sentence its span was on the planted error (27 of 27 for DeepSeek, 24 of 24 for GPT-6 Luna). The limit is recall, not location.
- **The decision pipelines also get 3–4× more expensive** on rephrased text, because they pay per changed sentence.
- **One mitigation was tested:** a "free translations are expected" paragraph in the LLM prompt. DeepSeek's false flags on correct rephrased sentences fell from 12 to 4 of 152 and GPT-6 Luna's from 1 to 0. Recall on the original near-verbatim items fell too (DeepSeek .96 → .82, GPT-6 Luna .88 → .80). It trades missed errors for fewer false alarms.
- **Requiring both LLMs to agree** doubles the cost for no gain over GPT-6 Luna alone.

## 5. Conclusion across the tracks

1. **On seeded near-copy gold items, one cheap generative call per item matches or beats the live grader and beats jev on recall, at or below jev's cost** (Track B: `deepseek/deepseek-v4.1-flash`, `openai/gpt-6-luna`). Cascades with jev as router or verifier lose to the cheap model alone, and a jev call costs more than a flash-class call (Track C). The cheap model's lead over jev on band agreement is inside the noise (+.07, CI −.03 to +.18); its lead on recall, and over the live grader, is not.
2. **Diff-focused jev fixes recall, but its band gains are within noise, severity cannot be learned from its probabilities, and zh accuracy is unsolved** (Track A).
3. **On paraphrased translations the decision-model pipelines collapse.** They flag most correct rephrased sentences, while the LLM graders mostly hold. GPT-6 Luna is the most robust (0 clean items flagged, precision .96 → .91); DeepSeek loses precision (.96 → .60) (Track E). So the recommended primary DT grader candidate is `openai/gpt-6-luna`, single call, structured output with span, with `deepseek/deepseek-v4.1-flash` as the cheaper alternative. Decision models are not recommended for DT error feedback. The character diff is not a reliable error locator on free translations (12 of 40 at heavy paraphrase), so spans should come from the LLM grader.
4. **Feedback text:** templates for direct corrections, hints and clean-item messages ($0); an LLM call with the live Explainer prompt for explanations; a leak filter in code; lexical facts supplied to the prompt (Track D).
5. **Total OpenRouter spend: $1.272 of a $3.00 cap**, from the key's usage counter. The track ledgers sum to $1.2691.

## 6. Caveats

- **n=30 per language, about 70% clean.** Differences under roughly .1 QWK are noise and most intervals are wide. Track E has 16–20 items per language and level.
- **Errors are seeded.** In Tracks A–D every learner text is a near-copy of the reference with planted edits, so the error is always the visible difference. Track E exists because of this, and it shows how much the near-copy assumption flattered the diff-based pipelines.
- **Track E labels are synthetic and model-verified.** No human adjudicated them. The checker, `openai/gpt-6.1-terra`, is from the same family as `gpt-6-luna` and may share its sense of "acceptable", which would flatter GPT-6 Luna's false-alarm rate. That caveat applies to exactly the comparison the recommendation rests on.
- **The paraphrases are not learner writing.** They are fluent, sentence-aligned rewrites by a strong model. Real learners merge and split sentences, drop content and write awkward-but-correct phrases.
- **No native-speaker review of explanations.** Track D's adjudication was done by the track's author. Track C read 27 explanations and found 3 flawed. Templates are AI-drafted and unreviewed.
- **Nothing was tested on real learner submissions.**
- **Several pipelines were scored on gold per track** (seven in Track A). The best-looking cells are optimistically biased.
- **Silver did not predict gold** for model choice (Track C) or for `A_D_only` (Track A). Silver and gold share passages for en and ja.
- **Baselines are quoted or recomputed from recorded outputs, not re-run.**
- **Costs include provider prompt caching** for the LLM graders; expect list price ($0.00008–0.00025 per item) at low or bursty traffic. One run at temperature 0; run-to-run variance was not measured.
- **Naturalness and range were not attempted.**

## 7. Recommendation

1. **Shadow run on real submissions** with `openai/gpt-6-luna` (single call, span + explanation prompt) next to the live DT grader, and `deepseek/deepseek-v4.1-flash` alongside it as the cheaper alternative. At $0.00003–0.00006 per item both can run on every submission. This needs result storage first, which has been an open question since September.
2. **Native-speaker review of a sample** of LLM explanations and hint templates before any of the text is shown to learners.
3. **Do not build on decision models for DT error feedback.** Track A's routing and shadow recommendations assumed near-copy answers and are superseded by Track E for this purpose.
4. **Take spans from the LLM grader**, not from the diff, in whichever feedback design is chosen.
5. **Build the feedback layer as Track D describes:** templates for direct corrections, hints and clean messages; the live Explainer prompt on DeepSeek or GPT-6 Luna for explanations; leak filter, length cap and lexical facts in code.
6. **Decide the "free translations are expected" prompt paragraph as a product question**, after the shadow run shows how much real learners rephrase.
7. **Re-test the model choice on data that is neither this silver nor this gold** before it is fixed.

## 8. Feedback design options (proposed; the owner has not chosen)

Three competing designs for presenting and tracking DT feedback were written alongside the tracks. Each has a spec, a working mockup and screenshots under `wiki/design/dt-feedback/`. All three are `status: planned`. No winner is declared here.

All three specs take their grader numbers from [[evaluations/jev-dt-tuning-2026-09-27]] and assume a jev-style grader. Whichever is chosen needs a pass against §5 above.

**Option 1: Focused Correction** — [[design/dt-feedback/option-1-focused-correction/SPEC]]. After a submission the learner sees their passage with one error promoted to a "Fix this first" card: their sentence, the original, a one-line reason in their L1 and an edit-and-check box. Everything else found is collapsed behind one row. Across sessions the app tracks at most three focus areas, shown as a strip of the last ten chances to use the pattern, and retires each when it stops recurring. It trades completeness for uptake. *Main weakness:* it shows less than the grader knows, so errors outside the one card are fixed more slowly; the spec calls this inherent to the option. Its tracking depends on detecting "chances" from the reference, which is untested, and it makes the long explanation on-demand, a partial deviation from [[decisions/ADR-015-eager-error-explanations]].

**Option 2: Guided Self-Repair** — [[design/dt-feedback/option-2-guided-self-repair/SPEC]]. The app does not show the correction. It marks which sentences have a problem and lets the learner fix them, with help one step at a time on request: where, what kind, a clue, then the answer. Every revision is re-checked by the cheap grader, and every episode ends with the original sentence on screen. Tracking records how much help each error type needed. *Main weakness:* the "where" hint comes from the character diff, which Track E found to be a small local edit for only 12 of 40 errors at heavy paraphrase; the spec itself lists this as unmeasured. It also needs new clue templates written and native-reviewed for every type and language pair, and Track D lists several types where template hints looked weak (on 1–7 errors per type).

**Option 3: Pattern Coach** — [[design/dt-feedback/option-3-pattern-coach/SPEC]]. Feedback on a single translation is deliberately short: each sentence is marked, the reference is shown, and a flagged sentence gets one error-type chip and a one-line templated rule. Every flag is logged by type into a personal pattern profile, counted per chance to make the error and tracked through four states to "under control". The learner's own previously wrong sentences are scheduled for spaced re-translation. It builds on the existing remediation tables. *Main weakness:* the value sits in the long-term profile, which depends on correct error types (top-1 on gold was 81–87% for the DeepSeek config and 77–80% for GPT-6 Luna) and on new "chance" tags for reference sentences. Whether retrying one's own sentence transfers to new sentences is the spec's own main open question, and its marks also come from the diff.

## Related Pages
- [[evaluations/jev-dt-tuning-2026-09-27]] — the September jev experiment this one follows
- [[evaluations/jev-judge-feasibility-2026-09-26]] — the first jev experiment
- [[evaluations/dt-taxonomy-v6-gate-2026-10-08]] — source of the live-grader v6 baseline and recorded outputs
- [[evaluations/dt-grading-v2-2026-07-19]] — live-grader baseline on the v5 gold set
- [[features/dual-translation]] · [[features/dual-translation.tech]] · [[features/dual-translation-remediation.tech]]
- [[algorithms/evidence-first-grading.tech]] — the live detect → verify → score design
- [[business-rules/translation-error-taxonomy]] · [[decisions/ADR-031-dt-taxonomy-v6-merge]] · [[decisions/ADR-015-eager-error-explanations]]
- [[design/dt-feedback/option-1-focused-correction/SPEC]] · [[design/dt-feedback/option-2-guided-self-repair/SPEC]] · [[design/dt-feedback/option-3-pattern-coach/SPEC]]
