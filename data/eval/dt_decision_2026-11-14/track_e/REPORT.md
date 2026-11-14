# Track E — do the cheap DT graders survive free translation? (paraphrase stress test)

**Date:** 2026-11-14 · **OpenRouter spend:** $0.4395 of a $0.60 budget (1,494 logged calls in `costs.jsonl`, all from `usage.cost`; the code guard at $0.55 never fired) · **Nothing written outside this directory, no production code changed, nothing committed.**

> **The labels in this set are synthetic by construction and model-verified. No human adjudicated them.** One model rewrote the gold learner texts, a second model checked them. Every number below inherits that.

## 1. Bottom line

- **The decision-model pipelines break on free translation.** On the original gold wording they flag 2–5 of 21 clean items. When most sentences are rephrased, `A_fused` flags 10 of 19 clean items, `liquid/d1-ultra` 13 of 19, and `A_D_only` 18 of 19. At sentence level, `A_fused` calls 49 of 152 correct rephrased sentences an error (32%), `d1-ultra` 47 (31%), `A_D_only` 115 (76%). Recall stays high (.85–.95) because they flag almost everything that differs.
- **The LLM graders hold up much better, and `gpt-6-luna` better than the recommended `deepseek-v4.1-flash`.** Luna flagged 0 of 19 clean heavily rephrased items and 1 of 152 correct rephrased sentences. DeepSeek flagged 2 of 19 clean items and 12 of 152 sentences, plus 9 more spurious flags inside sentences that also held a real error; its precision fell from .96 to .60. Almost all of these false flags are minor: 1 of DeepSeek's and none of Luna's was major or critical, and no clean item lost a band under either LLM.
- **Both LLMs lose recall when the error sits in a rephrased sentence.** Of 31 planted errors that survived into a rephrased sentence, DeepSeek found 27 and Luna 24; every one DeepSeek missed and 5 of the 7 Luna missed had been found in the original wording. The misses are mostly errors that only exist relative to the reference (a near-synonym, a tense, a dropped modifier): once the sentence is free, they look like legitimate variation.
- **The ranking changes.** On the original wording the five graders are close (mean QWK .77–.94). On heavy paraphrase the order is Luna (.89), DeepSeek (.71), `A_fused` (.66), `d1-ultra` (.65), `A_D_only` (.58). The decision-model pipelines are no longer usable for learner-facing feedback as frozen, and Luna overtakes DeepSeek.
- **The diff stops locating the error.** The reference-versus-learner diff is "a small local edit" for 46 of 49 errors in the original wording, 31 of 49 at moderate and 12 of 40 at heavy paraphrase. The hint UI cannot rely on it for freer text. The LLM's own span can: whenever an LLM flagged the right sentence, its span was on the planted error (27 of 27 for DeepSeek, 24 of 24 for Luna at heavy), and every span returned on rephrased text was a verbatim substring of the learner text.
- **The decision pipelines also get 3–4× more expensive** on rephrased text, because they pay per changed sentence: `A_fused` rises from $0.00025 to $0.00084 per item. The LLM graders stay at $0.00003–0.00006.
- **One cheap mitigation was tested: a "free translations are expected" paragraph added to the LLM prompt.** It cut DeepSeek's false flags on correct rephrased sentences from 12 to 4 of 152 and Luna's from 1 to 0, at no cost. It also lowered recall on the original near-verbatim items (DeepSeek .96 → .82, Luna .88 → .80). It trades missed errors for fewer false alarms; it does not fix the problem.

**Main caveat.** The paraphrases were written by `anthropic/claude-sonnet-5` and accepted by `openai/gpt-6.1-terra`. They are fluent, sentence-aligned rewrites of the reference, not real learner writing, and a GPT-family checker decided what counts as "acceptable", which may favour `gpt-6-luna` on false alarms. With 16–20 items per language and level, per-language cells are noisy; the pooled sentence-level counts (§4.2) are the numbers to trust.

## 2. The stress set

**Source.** 20 gold items per language from `tests/fixtures/dt_gold_v6` (the 30 v5-derived items Track B used): 7 clean, 10 single-error, 3 multi-error, chosen with a fixed seed, always including the two meaning-inversion items. That is 49 planted errors (en 16, zh 16, ja 17).

**Generation.** For each item, `anthropic/claude-sonnet-5` (temperature 0.7, reasoning off, `max_tokens` 800) rewrote every learner sentence as a free translation of the same content: different word order, synonyms, restructured clauses, same register, one learner sentence per reference sentence. It was told to carry each planted error over unchanged (same wrong form, same type and severity, still fixable by replacing one short fragment) and to return that fragment, which becomes the gold span. Error sentences it returned unchanged (14, mostly seven-word English sentences) got a second, single-sentence pass; 7 of those passed.

**Verification.** `openai/gpt-6.1-terra` (temperature 0, reasoning off) audited every sentence, knowing which errors were planted: is each planted error really present and still an error, and is there any other problem (grammar, word choice, meaning shift against the reference, register, unnatural phrasing)? Any objection, even a minor one, failed the sentence.

**Fix policy.** A failed sentence is reverted to the original gold learner sentence, which is clean or carries its original seeded error by construction. No failed sentence was kept.

| | count |
|---|---|
| Sentences generated | 228 (60 items) |
| Passed and kept as rephrased | 193 (85%) |
| Reverted: verifier found an unintended problem (all rated minor by the verifier) | 20 (9%) |
| Reverted: verifier said the planted error was no longer a real error | 7 (3%) |
| Reverted: generator left the error sentence unchanged, or declined | 8 (4%) |
| Items dropped from `heavy` (fewer than 2/3 of sentences rephrased) | 7 of 60 (12%): en 1, zh 2, ja 4 |

The verifier's rejections were mostly small meaning shifts ("crucial" for "important", 満足感 for 達成感) and seven cases where rephrasing had made the planted error legitimate (for example 洗很多次 is fine after 就算). That second group shows the check did real work.

**Levels.**

| Level | What it is | Items en/zh/ja | Sentences rephrased | Planted errors (in a rephrased sentence) |
|---|---|---|---|---|
| `orig` | the 60 gold items unchanged; graded from the Track A/B caches at no cost | 20/20/20 | 0 of 228 | 49 (0) |
| `moderate` | a random half of each item's sentences rephrased, the rest verbatim gold | 20/20/20 | 111 of 228 (49%) | 49 (18) |
| `heavy` | every sentence that passed verification rephrased | 19/18/16 | 183 of 204 (90%) | 40 (31) |

`stress_set.jsonl` holds all 173 items in the gold fixture schema plus `level`, `base_id`, `sentences_paraphrased`, per-error `in_paraphrased_sentence`, and both v6 and v5 expected bands. Expected bands are the gold bands, since the error set is unchanged.

## 3. What was run

All configs are frozen as the tracks left them. Nothing was retuned.

| Grader | Config | Calls |
|---|---|---|
| `deepseek/deepseek-v4.1-flash` | Track B `p1_expl` prompt; severity rule prior (en, ja) / model (zh) | 1 per item |
| `openai/gpt-6-luna` | Track B `p1_expl` prompt; severity rule prior (en) / model (zh, ja) | 1 per item |
| `A_fused` on `typesafe/jev-1.13` | Track A frozen: mean of arm-D and Sept detection ≥ .3, Sept error type, critical ≥ .7, graded severity | Sept request + arm D per changed sentence |
| `A_D_only` on `typesafe/jev-1.13` | Track A frozen: arm-D detection ≥ .3, D error type, critical ≥ .6, default severity | arm D per changed sentence |
| `liquid/d1-ultra` D-only | the config Track A fitted on that model's silver: detection ≥ .5, critical ≥ .6, default severity | arm D per changed sentence |
| `A_sept_refit` on jev-1.13 (free extra) | Track A frozen Sept-only config, scored from the same Sept calls | Sept request per changed sentence |

Metrics use each track's own code and conventions, so the columns match their reports: Track B graders are scored on error spans with the live `eval_metrics` against v6 labels and bands; Track A pipelines are scored per changed sentence pair against v5 labels and bands. Because those two precision/recall definitions differ, §4.2 gives one common sentence-level count for all graders. The D2 call that Track A sent alongside arm D was skipped, because neither frozen config reads it; `A_fused` cost here is therefore two calls per changed sentence, not three.

## 4. Results

### 4.1 Pooled over the three languages

"Clean items flagged" counts clean items given at least one error; the bracket is how many of those got a major or critical error. Mean QWK is the plain mean of the nine language × dimension cells (accuracy, fidelity, understandability). The `orig` rows are the same 60 base items in their gold wording.

| Grader | level | n | precision | recall (TP/FP/FN) | type top-1 | clean items flagged (maj+) | clean items with a band < 4 | mean QWK (9 cells) | exact band acc/fid/und | $/item |
|---|---|---|---|---|---|---|---|---|---|---|
| deepseek-v4.1-flash p1_expl | orig | 60 | .96 | .96 (47/2/2) | .81 | 1/21 (0) | 0/21 | .88 | .88/.92/.97 | 0.000029 |
| deepseek-v4.1-flash p1_expl | moderate | 60 | .74 | .82 (40/14/9) | .80 | 3/21 (0) | 0/21 | .77 | .80/.87/.97 | 0.000028 |
| deepseek-v4.1-flash p1_expl | heavy | 53 | .60 | .82 (33/22/7) | .76 | 2/19 (0) | 0/19 | .71 | .87/.83/.91 | 0.000034 |
| gpt-6-luna p1_expl | orig | 60 | .96 | .88 (43/2/6) | .81 | 0/21 (0) | 0/21 | .94 | .95/.93/.98 | 0.000051 |
| gpt-6-luna p1_expl | moderate | 60 | .95 | .78 (38/2/11) | .84 | 0/21 (0) | 0/21 | .88 | .93/.95/.95 | 0.000054 |
| gpt-6-luna p1_expl | heavy | 53 | .91 | .72 (29/3/11) | .83 | 0/19 (0) | 0/19 | .89 | .93/.93/.94 | 0.000057 |
| A_fused (jev-1.13) | orig | 60 | .95 | .89 (42/2/5) | .76 | 2/21 (0) | 0/21 | .77 | .85/.90/.95 | 0.000247 |
| A_fused (jev-1.13) | moderate | 60 | .60 | .89 (42/28/5) | .64 | 9/21 (1) | 3/21 | .67 | .77/.78/.90 | 0.000575 |
| A_fused (jev-1.13) | heavy | 53 | .42 | .90 (36/49/4) | .64 | 10/19 (1) | 3/19 | .66 | .81/.75/.94 | 0.000838 |
| A_D_only (jev-1.13) | orig | 60 | .90 | .96 (45/5/2) | .89 | 5/21 (0) | 0/21 | .90 | .93/.93/.98 | 0.000116 |
| A_D_only (jev-1.13) | moderate | 60 | .40 | .96 (45/69/2) | .84 | 19/21 (4) | 11/21 | .76 | .85/.62/.92 | 0.000277 |
| A_D_only (jev-1.13) | heavy | 53 | .25 | .95 (38/116/2) | .82 | 18/19 (8) | 15/19 | .58 | .76/.36/.83 | 0.000406 |
| D_only (liquid/d1-ultra) | orig | 60 | .94 | .92 (43/3/4) | .86 | 3/21 (0) | 0/21 | .91 | .97/.90/.97 | 0.000087 |
| D_only (liquid/d1-ultra) | moderate | 60 | .59 | .87 (41/29/6) | .85 | 13/21 (3) | 4/21 | .84 | .88/.85/.92 | 0.000208 |
| D_only (liquid/d1-ultra) | heavy | 53 | .42 | .85 (34/47/6) | .79 | 13/19 (4) | 7/19 | .65 | .83/.66/.89 | 0.000306 |
| A_sept_refit (jev-1.13) | orig | 60 | 1.00 | .66 (31/0/16) | .81 | 0/21 (0) | 0/21 | .78 | .85/.92/.95 | 0.000130 |
| A_sept_refit (jev-1.13) | moderate | 60 | .81 | .64 (30/7/17) | .80 | 0/21 (0) | 0/21 | .73 | .83/.90/.93 | 0.000298 |
| A_sept_refit (jev-1.13) | heavy | 53 | .72 | .53 (21/8/19) | .71 | 0/19 (0) | 0/19 | .69 | .83/.87/.94 | 0.000431 |

- Recall barely moves for the decision pipelines and falls for the LLMs (DeepSeek .96 → .82, Luna .88 → .72).
- Precision collapses for the decision pipelines (.90–.95 → .25–.42) and for DeepSeek (.96 → .60). Luna keeps .91.
- Clean items losing a band: none for either LLM; 3, 7 and 15 of 19 for `A_fused`, `d1-ultra` and `A_D_only`.
- `A_sept_refit`, which asks jev about the whole passage with "acceptable variation is not an error" and no diff, flags no clean item at any level, but finds only about half the errors (.66 → .53). It is the only decision-model config that does not over-flag, and it is the one Track A set out to replace for its low recall.

### 4.2 Sentence level, one definition for every grader

A sentence counts as flagged if the grader reports any error in it. "Verbatim sentence" means the learner sentence is the gold sentence, unchanged.

| Grader | level | errors found, rephrased sentence | errors found, verbatim sentence | clean REPHRASED sentences flagged | …flagged major/critical | clean verbatim-edit sentences flagged |
|---|---|---|---|---|---|---|
| deepseek-v4.1-flash p1_expl | orig | 0/0 | 45/47 | 0/0 | 0/0 | 1/18 |
| deepseek-v4.1-flash p1_expl | moderate | 14/18 | 25/29 | 7/93 | 0/93 | 1/11 |
| deepseek-v4.1-flash p1_expl | heavy | 27/31 | 6/9 | 12/152 | 1/152 | 0/3 |
| gpt-6-luna p1_expl | orig | 0/0 | 43/47 | 0/0 | 0/0 | 0/18 |
| gpt-6-luna p1_expl | moderate | 14/18 | 23/29 | 0/93 | 0/93 | 0/11 |
| gpt-6-luna p1_expl | heavy | 24/31 | 5/9 | 1/152 | 0/152 | 0/3 |
| A_fused (jev-1.13) | orig | 0/0 | 42/47 | 0/0 | 0/0 | 2/18 |
| A_fused (jev-1.13) | moderate | 18/18 | 24/29 | 27/93 | 4/93 | 1/11 |
| A_fused (jev-1.13) | heavy | 30/31 | 6/9 | 49/152 | 4/152 | 0/3 |
| A_D_only (jev-1.13) | orig | 0/0 | 45/47 | 0/0 | 0/0 | 5/18 |
| A_D_only (jev-1.13) | moderate | 18/18 | 27/29 | 67/93 | 10/93 | 2/11 |
| A_D_only (jev-1.13) | heavy | 30/31 | 8/9 | 115/152 | 21/152 | 1/3 |
| D_only (liquid/d1-ultra) | orig | 0/0 | 43/47 | 0/0 | 0/0 | 3/18 |
| D_only (liquid/d1-ultra) | moderate | 15/18 | 26/29 | 28/93 | 5/93 | 1/11 |
| D_only (liquid/d1-ultra) | heavy | 26/31 | 8/9 | 47/152 | 8/152 | 0/3 |
| A_sept_refit (jev-1.13) | orig | 0/0 | 31/47 | 0/0 | 0/0 | 0/18 |
| A_sept_refit (jev-1.13) | moderate | 12/18 | 18/29 | 7/93 | 1/93 | 0/11 |
| A_sept_refit (jev-1.13) | heavy | 17/31 | 4/9 | 8/152 | 0/152 | 0/3 |

The same planted errors, original wording against rephrased sentence (heavy level, 31 errors):

| Grader | n errors | found in both | found only in original | found only when rephrased | missed in both |
|---|---|---|---|---|---|
| deepseek-v4.1-flash p1_expl | 31 | 27 | 4 | 0 | 0 |
| gpt-6-luna p1_expl | 31 | 24 | 5 | 0 | 2 |
| A_fused (jev-1.13) | 31 | 30 | 0 | 0 | 1 |
| A_D_only (jev-1.13) | 31 | 30 | 0 | 0 | 1 |
| D_only (liquid/d1-ultra) | 31 | 25 | 3 | 1 | 2 |

- False-flag rate on correct rephrased sentences at heavy: Luna 0.7%, DeepSeek 7.9%, `d1-ultra` 31%, `A_fused` 32%, `A_D_only` 76%.
- Errors in sentences left verbatim are also found slightly less often once the surrounding sentences are rephrased (DeepSeek 45/47 → 25/29, Luna 43/47 → 23/29 at moderate). The heavy figures (6/9, 5/9) are not comparable: those nine are the errors the verifier refused to accept in rephrased form, a harder subset.

### 4.3 Per language and level

Gold numbers for the full 30-item sets, as reported by Tracks A and B, are in the table after these three.

**en**

| Grader | level | n | P | R | TP/FP/FN | type top-1 | clean items flagged (maj+) | clean rephrased sentences flagged | QWK acc/fid/und | exact acc/fid/und | $/item | p50 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek-v4.1-flash p1_expl | orig | 20 | .94 | 1.00 | 16/1/0 | .75 | 0/7 (0) | 0/0 | .92/.97/1.00 | .95/.95/1.00 | 0.000018 | 1.91 |
| deepseek-v4.1-flash p1_expl | moderate | 20 | .88 | .94 | 15/2/1 | .87 | 1/7 (0) | 0/35 | .79/1.00/.96 | .90/1.00/.95 | 0.000022 | 1.55 |
| deepseek-v4.1-flash p1_expl | heavy | 19 | .62 | .87 | 13/8/2 | .85 | 2/7 (0) | 6/57 | .89/.97/.96 | .95/.95/.95 | 0.000027 | 1.39 |
| gpt-6-luna p1_expl | orig | 20 | 1.00 | .94 | 15/0/1 | .80 | 0/7 (0) | 0/0 | 1.00/.97/.95 | 1.00/.95/.95 | 0.000041 | 1.19 |
| gpt-6-luna p1_expl | moderate | 20 | 1.00 | .81 | 13/0/3 | .77 | 0/7 (0) | 0/35 | .89/.97/.90 | .95/.95/.90 | 0.000042 | 1.2 |
| gpt-6-luna p1_expl | heavy | 19 | .92 | .80 | 12/1/3 | .75 | 0/7 (0) | 1/57 | .89/.97/.90 | .95/.95/.90 | 0.000045 | 1.2 |
| A_fused (jev-1.13) | orig | 20 | 1.00 | .94 | 15/0/1 | .87 | 0/7 (0) | 0/0 | 1.00/.44/.95 | 1.00/.90/.95 | 0.000193 | 0.34 |
| A_fused (jev-1.13) | moderate | 20 | .83 | .94 | 15/3/1 | .80 | 1/7 (0) | 3/35 | .72/.53/.95 | .95/.85/.95 | 0.000486 | 0.4 |
| A_fused (jev-1.13) | heavy | 19 | .67 | .93 | 14/7/1 | .86 | 2/7 (0) | 7/57 | .72/.41/1.00 | .95/.79/1.00 | 0.000681 | 0.43 |
| A_D_only (jev-1.13) | orig | 20 | 1.00 | .94 | 15/0/1 | .87 | 0/7 (0) | 0/0 | .97/.64/.95 | .95/.95/.95 | 0.000101 | 0.28 |
| A_D_only (jev-1.13) | moderate | 20 | .50 | .94 | 15/15/1 | .93 | 5/7 (1) | 15/35 | .97/.32/.95 | .95/.85/.95 | 0.000257 | 0.37 |
| A_D_only (jev-1.13) | heavy | 19 | .33 | .93 | 14/29/1 | .93 | 6/7 (2) | 29/57 | .95/.04/.95 | .90/.58/.95 | 0.000361 | 0.39 |
| D_only (liquid/d1-ultra) | orig | 20 | 1.00 | .94 | 15/0/1 | .87 | 0/7 (0) | 0/0 | 1.00/.64/.95 | 1.00/.95/.95 | 0.000077 | 0.48 |
| D_only (liquid/d1-ultra) | moderate | 20 | .72 | .81 | 13/5/3 | .85 | 2/7 (0) | 5/35 | .94/.64/.90 | .90/.95/.90 | 0.000195 | 0.5 |
| D_only (liquid/d1-ultra) | heavy | 19 | .60 | .80 | 12/8/3 | .83 | 2/7 (0) | 8/57 | .94/.44/.90 | .90/.90/.90 | 0.000275 | 0.53 |

**zh**

| Grader | level | n | P | R | TP/FP/FN | type top-1 | clean items flagged (maj+) | clean rephrased sentences flagged | QWK acc/fid/und | exact acc/fid/und | $/item | p50 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek-v4.1-flash p1_expl | orig | 20 | .93 | .88 | 14/1/2 | .79 | 1/7 (0) | 0/0 | .54/.94/.93 | .75/.90/.95 | 0.000032 | 1.8 |
| deepseek-v4.1-flash p1_expl | moderate | 20 | .77 | .62 | 10/3/6 | .70 | 1/7 (0) | 2/30 | .21/.91/1.00 | .70/.85/1.00 | 0.000028 | 1.73 |
| deepseek-v4.1-flash p1_expl | heavy | 18 | .89 | .61 | 8/1/5 | .62 | 0/7 (0) | 1/53 | .37/.74/.77 | .78/.89/.94 | 0.000038 | 1.47 |
| gpt-6-luna p1_expl | orig | 20 | .93 | .81 | 13/1/3 | .77 | 0/7 (0) | 0/0 | .74/.97/1.00 | .90/.95/1.00 | 0.000053 | 1.56 |
| gpt-6-luna p1_expl | moderate | 20 | .92 | .69 | 11/1/5 | .91 | 0/7 (0) | 0/30 | .88/.97/1.00 | .95/.95/1.00 | 0.000056 | 1.35 |
| gpt-6-luna p1_expl | heavy | 18 | .88 | .54 | 7/1/6 | .86 | 0/7 (0) | 0/53 | .68/.94/1.00 | .89/.89/1.00 | 0.000059 | 1.23 |
| A_fused (jev-1.13) | orig | 20 | .92 | .73 | 11/1/4 | .82 | 1/7 (0) | 0/0 | .47/.94/1.00 | .80/.90/1.00 | 0.000249 | 0.37 |
| A_fused (jev-1.13) | moderate | 20 | .55 | .73 | 11/9/4 | .73 | 3/7 (0) | 9/30 | .52/.86/.87 | .70/.90/.90 | 0.000580 | 0.41 |
| A_fused (jev-1.13) | heavy | 18 | .32 | .77 | 10/21/3 | .60 | 5/7 (0) | 21/53 | .29/.86/.87 | .72/.89/.89 | 0.000919 | 0.48 |
| A_D_only (jev-1.13) | orig | 20 | .82 | .93 | 14/3/1 | .79 | 3/7 (0) | 0/0 | .76/.94/1.00 | .90/.90/1.00 | 0.000117 | 0.36 |
| A_D_only (jev-1.13) | moderate | 20 | .34 | .93 | 14/27/1 | .71 | 7/7 (2) | 26/30 | .50/.82/.93 | .70/.70/.95 | 0.000278 | 0.39 |
| A_D_only (jev-1.13) | heavy | 18 | .20 | .92 | 12/48/1 | .67 | 7/7 (3) | 47/53 | .46/.57/.90 | .67/.39/.89 | 0.000441 | 0.41 |
| D_only (liquid/d1-ultra) | orig | 20 | .87 | .87 | 13/2/2 | .92 | 2/7 (0) | 0/0 | 1.00/.97/1.00 | 1.00/.95/1.00 | 0.000088 | 0.47 |
| D_only (liquid/d1-ultra) | moderate | 20 | .54 | .87 | 13/11/2 | .92 | 6/7 (2) | 11/30 | .82/.91/.93 | .90/.85/.95 | 0.000212 | 0.5 |
| D_only (liquid/d1-ultra) | heavy | 18 | .38 | .85 | 11/18/2 | .82 | 6/7 (2) | 18/53 | .61/.60/.72 | .83/.56/.89 | 0.000338 | 0.64 |

**ja**

| Grader | level | n | P | R | TP/FP/FN | type top-1 | clean items flagged (maj+) | clean rephrased sentences flagged | QWK acc/fid/und | exact acc/fid/und | $/item | p50 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek-v4.1-flash p1_expl | orig | 20 | 1.00 | 1.00 | 17/0/0 | .88 | 0/7 (0) | 0/0 | .88/.88/.85 | .95/.90/.95 | 0.000037 | 1.97 |
| deepseek-v4.1-flash p1_expl | moderate | 20 | .62 | .88 | 15/9/2 | .80 | 1/7 (0) | 5/28 | .53/.81/.71 | .80/.75/.95 | 0.000034 | 1.76 |
| deepseek-v4.1-flash p1_expl | heavy | 16 | .48 | 1.00 | 12/13/0 | .75 | 0/5 (0) | 5/42 | .67/.64/.39 | .88/.62/.81 | 0.000039 | 1.79 |
| gpt-6-luna p1_expl | orig | 20 | .94 | .88 | 15/1/2 | .87 | 0/7 (0) | 0/0 | .88/.94/1.00 | .95/.90/1.00 | 0.000059 | 1.28 |
| gpt-6-luna p1_expl | moderate | 20 | .93 | .82 | 14/1/3 | .86 | 0/7 (0) | 0/28 | .73/.90/.71 | .90/.95/.95 | 0.000066 | 1.41 |
| gpt-6-luna p1_expl | heavy | 16 | .91 | .83 | 10/1/2 | .90 | 0/5 (0) | 0/42 | .82/.95/.88 | .94/.94/.94 | 0.000068 | 1.31 |
| A_fused (jev-1.13) | orig | 20 | .94 | 1.00 | 16/1/0 | .62 | 1/7 (0) | 0/0 | .29/.94/.90 | .75/.90/.90 | 0.000298 | 0.36 |
| A_fused (jev-1.13) | moderate | 20 | .50 | 1.00 | 16/16/0 | .44 | 5/7 (1) | 15/28 | -.05/.78/.85 | .65/.60/.85 | 0.000659 | 0.43 |
| A_fused (jev-1.13) | heavy | 16 | .36 | 1.00 | 12/21/0 | .42 | 3/5 (1) | 21/42 | .20/.65/.90 | .75/.56/.94 | 0.000932 | 0.42 |
| A_D_only (jev-1.13) | orig | 20 | .89 | 1.00 | 16/2/0 | 1.00 | 2/7 (0) | 0/0 | .88/.97/1.00 | .95/.95/1.00 | 0.000131 | 0.36 |
| A_D_only (jev-1.13) | moderate | 20 | .37 | 1.00 | 16/27/0 | .88 | 7/7 (1) | 26/28 | .81/.65/.88 | .90/.30/.85 | 0.000296 | 0.36 |
| A_D_only (jev-1.13) | heavy | 16 | .23 | 1.00 | 12/39/0 | .83 | 5/5 (3) | 39/42 | .50/.34/.53 | .69/.06/.62 | 0.000420 | 0.38 |
| D_only (liquid/d1-ultra) | orig | 20 | .94 | .94 | 15/1/1 | .80 | 1/7 (0) | 0/0 | .77/.88/.96 | .90/.80/.95 | 0.000095 | 0.44 |
| D_only (liquid/d1-ultra) | moderate | 20 | .54 | .94 | 15/13/1 | .80 | 5/7 (1) | 12/28 | .67/.85/.92 | .85/.75/.90 | 0.000216 | 0.5 |
| D_only (liquid/d1-ultra) | heavy | 16 | .34 | .92 | 11/21/1 | .73 | 5/5 (2) | 21/42 | .35/.55/.78 | .75/.50/.88 | 0.000308 | 0.52 |

| Grader | en | zh | ja |
|---|---|---|---|
| deepseek-v4.1-flash p1_expl | P .96 R .96 · type .81 · clean 0/10 · QWK .94/.80/.75 · $0.000018 · 1.8 s | P .96 R .89 · type .87 · clean 1/10 · QWK .61/.89/.88 · $0.000033 · 1.8 s | P .96 R .93 · type .84 · clean 0/10 · QWK .92/.83/.70 · $0.000037 · 2.0 s |
| gpt-6-luna p1_expl | P 1.00 R .93 · type .80 · clean 0/10 · QWK 1.00/.84/.79 · $0.000043 · 1.2 s | P .96 R .85 · type .77 · clean 0/10 · QWK .74/.84/.74 · $0.000054 · 1.6 s | P .96 R .89 · type .79 · clean 0/10 · QWK .92/.87/.76 · $0.000066 · 1.4 s |
| A_fused (jev-1.13) | P .96 R .92 · type .83 · QWK 1.00/.52/.91 · exact3 .83 · $0.00024 · 0.35 s | P .95 R .83 · type .74 · QWK .39/.89/.94 · exact3 .70 · $0.00029 · 0.36 s | P .93 R .96 · type .72 · QWK .59/.93/.91 · exact3 .73 · $0.00035 · 0.39 s |
| A_D_only (jev-1.13) | P .96 R .92 · type .78 · QWK .95/.24/.95 · exact3 .80 · $0.00011 · 0.29 s | P .85 R .96 · type .77 · QWK .68/.84/.94 · exact3 .73 · $0.00012 · 0.35 s | P .86 R .96 · type 1.00 · QWK .92/.89/.79 · exact3 .87 · $0.00014 · 0.36 s |
| D_only (liquid/d1-ultra) | P .96 R .92 · type .87 · QWK .98/.53/.79 · exact3 .83 · $0.00008 · 0.48 s | P .88 R .91 · type .95 · QWK .92/.92/.94 · exact3 .87 · $0.00009 · 0.47 s | P .96 R .92 · type .83 · QWK .85/.83/.76 · exact3 .73 · $0.00010 · 0.44 s |

Things worth noting in the per-language cells, all on 16–20 items:

- Japanese is where DeepSeek degrades most: 13 unmatched flags at heavy, fidelity exact-band rate .90 → .63, understandability QWK .85 → .39.
- Chinese is where both LLMs lose most recall (.88 → .62 for DeepSeek, .81 → .54 for Luna), mostly minor measure-word, 的/得 and word-order slips.
- English is the mildest case for every grader, partly because the English gold sentences are six to eight words long and leave little room to rephrase.
- Error-type top-1 on the errors that are found stays at .75–.90 for the LLMs at heavy, except DeepSeek in Chinese (.79 → .62, on 8 matched errors). `A_fused` in Japanese drops from .63 to .42.
- Latency does not change: 1.2–1.9 s p50 for the LLM call, 0.4–0.6 s for the decision calls run in parallel.

### 4.4 Is the diff still a small local edit?

"Small local edit" means at most two diff hunks in the error sentence, covering at most 30% of it (Track B's `diff_hunks`: word-level for English, character-level for Chinese and Japanese). "Highlight mostly on the error" means at least half of the highlighted learner text is the planted error.

| lang | level | gold errors | diff is a small local edit | exactly one diff hunk, on the error | highlight mostly on the error | median hunks in error sentence | median share of sentence highlighted | mean share of highlight that is the error | hunks per clean changed sentence |
|---|---|---|---|---|---|---|---|---|---|
| all | orig | 49 | 46/49 | 43/49 | 47/49 | 1 | .08 | .91 | 1.00 |
| all | moderate | 49 | 31/49 | 27/49 | 32/49 | 1 | .16 | .68 | 2.87 |
| all | heavy | 40 | 12/40 | 12/40 | 16/40 | 2.0 | .42 | .48 | 3.10 |
| en | orig | 16 | 13/16 | 15/16 | 16/16 | 1.0 | .11 | .99 | 1.00 |
| en | moderate | 16 | 10/16 | 11/16 | 14/16 | 1.0 | .16 | .84 | 1.46 |
| en | heavy | 15 | 5/15 | 8/15 | 10/15 | 1 | .41 | .66 | 1.52 |
| zh | orig | 16 | 16/16 | 13/16 | 15/16 | 1.0 | .09 | .88 | 1.00 |
| zh | moderate | 16 | 10/16 | 7/16 | 8/16 | 2.0 | .13 | .59 | 4.00 |
| zh | heavy | 13 | 4/13 | 3/13 | 4/13 | 3 | .50 | .44 | 4.36 |
| ja | orig | 17 | 17/17 | 15/17 | 16/17 | 1 | .06 | .85 | 1.00 |
| ja | moderate | 17 | 11/17 | 9/17 | 10/17 | 1 | .16 | .63 | 3.41 |
| ja | heavy | 12 | 3/12 | 1/12 | 2/12 | 4.0 | .35 | .31 | 3.62 |

At heavy paraphrase the diff highlights 35–50% of a typical error sentence, in one to four hunks, and only .31–.66 of what it highlights is the error. Correct rephrased sentences get three to four hunks each in Chinese and Japanese. A hint UI that points at "the diff" would point at several correct phrases for every wrong one. (Nine of the 40 heavy errors sit in sentences left verbatim, so for errors in rephrased sentences alone the diff is worse than this table shows.)

### 4.5 Does the LLM's own span still find the error?

| Grader | level | errors in rephrased sentences: sentence flagged | …span on the error | errors in verbatim sentences: sentence flagged | …span on the error | spans not found verbatim in learner text |
|---|---|---|---|---|---|---|
| deepseek-v4.1-flash p1_expl | orig | 0/0 | 0/0 | 47/49 | 47/49 | 0 |
| deepseek-v4.1-flash p1_expl | moderate | 14/18 | 13/18 | 27/31 | 27/31 | 0 |
| deepseek-v4.1-flash p1_expl | heavy | 27/31 | 27/31 | 6/9 | 6/9 | 0 |
| gpt-6-luna p1_expl | orig | 0/0 | 0/0 | 45/49 | 43/49 | 1 |
| gpt-6-luna p1_expl | moderate | 14/18 | 14/18 | 25/31 | 24/31 | 0 |
| gpt-6-luna p1_expl | heavy | 24/31 | 24/31 | 5/9 | 5/9 | 0 |

Yes. On rephrased sentences the span is on the planted error every time the sentence is flagged at heavy, and in 13 of 14 (DeepSeek) and 14 of 14 (Luna) cases at moderate. The span is the right thing to drive the hint UI. Its limit is recall, not location.

## 5. Failure examples

**Correct sentences told they were wrong** (frozen configs, heavy level, all sentences the verifier accepted):

| # | Grader | Reference | Learner (correct paraphrase) | What the grader said |
|---|---|---|---|---|
| 1 | deepseek | You learn how to connect wires. | You find out how to join wires together. | `word_choice` minor on "find out"; and a second `word_choice` entry on "join wires together" whose explanation reads "is acceptable; no error" |
| 2 | deepseek | You can move them to a new spot. | You can then move them to a new location. | `addition` minor: "'then' adds a time link not in the source" |
| 3 | deepseek | このロボットアームを作るには、いくつかの部品が必要です。 | このロボットアームを組み立てるには、いくつかの部品が必要になります。 | `addition` minor: 「必要になります」は余分な変化です |
| 4 | deepseek | 猫咪的毛发画得很细致，… | 这只猫的毛发被画得十分细腻，… | `addition` minor: "Adding 被 makes the painting passive" |
| 5 | deepseek | どうやって作るの？ | 作り方はどうするの？ | `register` **major**: "Polite question form needed" (the reference is equally casual) |
| 6 | gpt-6-luna | You write instructions for the Arduino. | You write the instructions for the Arduino. | `article_determiner` minor (Luna's only false flag on a correct rephrased sentence) |
| 7 | A_fused | 它的图案，那个微笑的小猫，永远是我心中最温暖的存在。 | 它上面那个微笑的小猫图案，永远都是我心里最温暖的存在。 | `ba_construction` **major** |
| 8 | A_fused | このシンプルなロボットアームをベースに、さらに色々な機能を追加することもできます。 | このシンプルなロボットアームを土台にして、他にも様々な機能を加えることができます。 | `verb_conjugation` **major** |
| 9 | d1-ultra | 在T恤的胸口位置，有一个小小的、很可爱的图画。 | T恤胸前的位置上印着一幅小巧而讨人喜欢的图画。 | `omission` **major** |

DeepSeek's false flags follow one pattern: it reads any small difference from the reference as `addition` or `word_choice` ("not in the source"). Example 1 shows it sometimes emits an entry and then says in the explanation that there is no error; a code check for that would remove some flags for free. The decision pipelines' false flags have no visible pattern beyond "the diff is large", and their error types on correct sentences are arbitrary. Two or three of DeepSeek's flags are arguable (example 5 is slightly awkward Japanese), so its true false-alarm rate may be a little lower than 12 of 152.

**Real errors missed once the sentence was rephrased** (9 of the 11 misses had been found by the same grader in the original wording):

| Grader | Reference | Learner | Planted error |
|---|---|---|---|
| both LLMs | Building a simple robot arm with Arduino is a fun DIY project. | Putting together a simple robot arm with Arduino **was** a fun DIY project. | `verb_form_tense`, major |
| both LLMs | …is a fun DIY project. | Making a basic robotic arm using Arduino is a **nice** DIY project. | `word_choice`, minor |
| both LLMs | 这个图画是一只正在微笑的小猫，… | 画里是**一个**正在微笑的小猫，… | `measure_word`, minor |
| gpt-6-luna | …更是因为它承载了很多美好的回忆。 | …更是它承载了很多美好的回忆。 | `omission` (因为 dropped), major |
| gpt-6-luna | …さらに色々な機能を追加することもできます。 | …さらに機能を加えていくこともできます。 | `omission` (色々な dropped), minor |

Three of these five ("was", "nice", dropped 色々な) are errors only because the reference says otherwise. In a free translation a grader that has been told "alternative wording is not an error" has no principled way to separate them from paraphrase. That is a limit of the task definition as much as of the graders.

## 6. Mitigation tested

**Prompt paragraph for the LLM graders.** Appended to the frozen `p1_expl` system prompt (text in `run_graders.py`, `MITIGATION`): the learner did not see the reference; different wording, order and structure are expected; report an error only if a specific word or form is wrong in itself or a fact in the reference is changed, reversed or left out; when in doubt, do not report. The fixtures hold no source-language text, so "pass the source text" could not be tested; the paragraph tells the model to judge the message, not the surface.

| Grader | prompt | level | precision | recall (TP/FP/FN) | clean items flagged | clean rephrased sentences flagged | errors found in rephrased sentences | mean QWK (9) | $/item |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-v4.1-flash p1_expl | frozen | orig | .96 | .96 (47/2/2) | 1/21 | 0/0 | 0/0 | .88 | 0.000029 |
| deepseek-v4.1-flash p1_expl | frozen | moderate | .74 | .82 (40/14/9) | 3/21 | 7/93 | 14/18 | .77 | 0.000028 |
| deepseek-v4.1-flash p1_expl | frozen | heavy | .60 | .82 (33/22/7) | 2/19 | 12/152 | 27/31 | .71 | 0.000034 |
| deepseek-v4.1-flash p1_expl | + mitigation | orig | .95 | .82 (40/2/9) | 1/21 | 0/0 | 0/0 | .91 | 0.000034 |
| deepseek-v4.1-flash p1_expl | + mitigation | moderate | .90 | .76 (37/4/12) | 0/21 | 2/93 | 14/18 | .84 | 0.000033 |
| deepseek-v4.1-flash p1_expl | + mitigation | heavy | .81 | .75 (30/7/10) | 0/19 | 4/152 | 25/31 | .71 | 0.000035 |
| gpt-6-luna p1_expl | frozen | orig | .96 | .88 (43/2/6) | 0/21 | 0/0 | 0/0 | .94 | 0.000051 |
| gpt-6-luna p1_expl | frozen | moderate | .95 | .78 (38/2/11) | 0/21 | 0/93 | 14/18 | .88 | 0.000054 |
| gpt-6-luna p1_expl | frozen | heavy | .91 | .72 (29/3/11) | 0/19 | 1/152 | 24/31 | .89 | 0.000057 |
| gpt-6-luna p1_expl | + mitigation | orig | 1.00 | .80 (39/0/10) | 0/21 | 0/0 | 0/0 | .89 | 0.000059 |
| gpt-6-luna p1_expl | + mitigation | moderate | 1.00 | .73 (36/0/13) | 0/21 | 0/93 | 15/18 | .87 | 0.000055 |
| gpt-6-luna p1_expl | + mitigation | heavy | 1.00 | .72 (29/0/11) | 0/19 | 0/152 | 25/31 | .89 | 0.000057 |

- DeepSeek: false flags on correct rephrased sentences 12 → 4 of 152, flagged clean items 2 → 0 of 19, heavy precision .60 → .81. Recall on the original items .96 → .82 (7 more of 49 errors missed) and on heavy .82 → .75.
- Luna: its few false flags go to zero at every level. Recall on the original items .88 → .80, unchanged at heavy.
- It costs nothing (about 90 more prompt tokens).
- Verdict: it helps the "never tell a learner a correct sentence is wrong" risk and hurts recall on near-verbatim text. Whether that trade is right is a product decision. It was written once and not iterated, and it was tested on the same set that motivated it.

**Second opinion from the frozen runs, no extra calls.** Keeping a flag only when both LLMs flag the same sentence:

| level | errors in rephrased sentences: both / either | errors in verbatim sentences: both / either | clean rephrased sentences: both / either |
|---|---|---|---|
| orig | 0 / 0 of 0 | 42 / 46 of 47 | 0 / 0 of 0 |
| moderate | 12 / 16 of 18 | 21 / 27 of 29 | 0 / 7 of 93 |
| heavy | 23 / 28 of 31 | 4 / 7 of 9 | 1 / 12 of 152 |

Requiring agreement leaves 1 false flag in 152 correct rephrased sentences and still finds 23 of 31 errors in rephrased sentences, about the same as Luna alone (1 of 152, 24 of 31). It doubles the cost for no gain over Luna. Using either model's flag raises recall to 28 of 31 but inherits DeepSeek's 12 false flags.

**For the decision pipelines** the only frozen config that does not over-flag is `A_sept_refit` (§4.1), at half the recall. No cheap fix for arm D was found or tested: its questions are built around the marked diff, and the diff is what stops working.

## 7. What this means for the decision

1. If learners are allowed to rephrase, use an LLM grader, not the diff-focused decision pipeline. The frozen arm-D pipelines would tell a learner that a third to three quarters of their correct rephrased sentences contain an error.
2. Between the two LLMs, this set favours `openai/gpt-6-luna` for learner-facing feedback: lower recall than DeepSeek, far fewer false alarms. Track B found them indistinguishable on gold; they are not indistinguishable here. The checker-family caveat in §8 applies to exactly this comparison, so confirm it on real submissions before switching.
3. Drive the hint UI from the LLM's returned span, not from the diff.
4. Expect to miss more reference-relative errors (near-synonyms, tense, dropped modifiers) on free text, whatever the grader. If those must be caught, the exercise has to tell the grader which reference details are obligatory.
5. Budget the decision pipeline, if it is kept for routing, at about $0.0003–0.0009 per item on free text, not $0.0001–0.0003.

## 8. Caveats

1. **Synthetic, model-verified labels.** No human checked any item. A paraphrase the verifier accepted may still contain something a teacher would mark, in which case a "false alarm" was correct; a planted error may have become acceptable without the verifier noticing, in which case a "miss" was correct.
2. **The checker may favour one grader.** `gpt-6.1-terra` decided which paraphrases are acceptable. `gpt-6-luna` is from the same family and may share its sense of "acceptable", which would flatter Luna's false-alarm rate. The 27 sentences the verifier rejected were removed, so the set over-represents paraphrases a GPT model is comfortable with.
3. **Not learner writing.** The rephrased sentences are fluent, native-like rewrites by a strong model, aligned one-to-one with the reference sentences. Real learners merge and split sentences, drop content, and make errors that are not single seeded edits. Sentence merging would hurt the sentence-pair pipelines further; awkward-but-correct learner phrasing may raise the LLMs' false alarms above what is measured here.
4. **Small n.** 16–20 items and 12–17 errors per language and level; 31 errors in rephrased sentences in total. Differences of two or three counts between graders are noise. The large effects (decision-pipeline false alarms, DeepSeek versus Luna precision, diff locality) are far outside that; the recall differences between the two LLMs are not.
5. **Seeded errors survive unevenly.** English error sentences were too short to rephrase in half the cases, and seven errors stopped being errors when rephrased. The errors that remain in rephrased sentences are a selected subset.
6. **`moderate` and `heavy` share sentences.** A rephrased sentence in a moderate item is the same sentence as in the heavy item, so the two levels are not independent samples.
7. **Eras are mixed for `A_fused` on `orig`.** Its Sept-side answers come from the September response files, arm D from Track A's cache; the moderate and heavy calls were all made today.
8. **Costs are actual charges** with provider prompt caching, as in Track B. Generation and verification cost $0.332, above the $0.30 planned, because the generator's prompt tokenised to about 1,200 tokens per item.
9. **One run, temperature 0, no repeat.** Run-to-run variance was not measured.

## 9. Spend

| Stage | Model | Calls | USD |
|---|---|---|---|
| gen | anthropic/claude-sonnet-5 | 60 | 0.2447 |
| grade_a | typesafe/jev-1.13 | 541 | 0.0624 |
| verify | openai/gpt-6.1-terra | 60 | 0.0615 |
| grade_a | liquid/d1-ultra | 236 | 0.0198 |
| regen | anthropic/claude-sonnet-5 | 13 | 0.0189 |
| grade_b | openai/gpt-6-luna | 286 | 0.0161 |
| grade_b | deepseek/deepseek-v4.1-flash | 286 | 0.0094 |
| regen_verify | openai/gpt-6.1-terra | 12 | 0.0067 |
| **Total** | | **1494** | **0.4395** |

Smoke tests (6 items for generation and verification, 5 for each grader family) ran before the full runs and projected about $0.28–0.34 for building the set and about $0.09 for the frozen graders; actual was $0.332 for the set and $0.108 for all grading, including the mitigation runs.

## 10. Files

All under `/home/user/LinguaLoop-web/data/eval/dt_decision_2026-11-14/track_e/`.

| File | What it is |
|---|---|
| `REPORT.md`, `results.json` | this report; pooled and per-language metrics, mitigation, ensemble, paired counts, diff locality, false-flag examples, spend |
| `stress_set.jsonl` | the 173 items (60 orig, 60 moderate, 53 heavy) |
| `build_verify.json`, `build_regen.json`, `build_stats.json` | raw generations, verifier verdicts, the list of reverted sentences with the verifier's reasons |
| `elib.py` | imports Track A and Track B code read-only and points their cache, ledger and budget guard at this directory |
| `build_set.py`, `regen.py`, `assemble.py` | selection, generation, verification, assembly |
| `run_graders.py`, `analyze.py`, `make_report.py` | frozen graders, scoring, tables |
| `runs/` | per-item grader output (`*__p1_expl.jsonl`, `*__p1_expl_mit.jsonl`, `A_rows.jsonl`) |
| `costs.jsonl`, `cache/` | call ledger and cached responses; every script re-runs from cache at no cost |
