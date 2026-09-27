# Can `typesafe/jev-1.13` judge LinguaLoop exercise content? (zh / en / ja)

Experiment date: 2026-09-26. All scripts/data in this directory (`exp_a/`). Repo untouched:
no DB writes, no repo files modified. Read-only Supabase queries via MCP; jev calls via a
thin `requests` client (`jev_client.py`), concurrency 8, retry on 429/transient 402.

**Total spend: $0.0775** (well under the $1 cap). **Important operational finding, not
specific to this experiment:** the shared OpenRouter account ran out of credit entirely
partway through the third run (`total_credits: 70` vs `total_usage: 70.0027`, confirmed via
`GET /api/v1/credits`) — a **hard, permanent 402** (`limit_source: openrouter_credits`), not
the retryable in-flight-budget kind. This blocks *all* OpenRouter calls right now, for every
pipeline in the repo, not just jev. 120 of 1074 distractor-judge requests (11%) failed for
this reason and could not be retried; everything else in this report completed. **The account
needs a top-up before any further LLM work (including production judges/generation) can run.**

---

## 1. Method

Three sub-experiments, each asking jev `noul`/`score` questions with instructions/criteria
written **entirely in the target language** for zh/ja (JSON keys stay ASCII; verified by
inspection of `rubric.py`), against `state` holding the actual sentence/passage/candidate text.

1. **Controlled corruption set** (`controlled_set.py`, `run_controlled.py`): 15 real
   `prompt1_core` sentences per language pulled live from `word_assets` (Supabase, read-only),
   each hand-corrupted into exactly one cell of a 5 defect-type x 3 subtlety grid (particle,
   word-order, verb-form, semantic-anomaly, wrong-sense x obvious/moderate/subtle) = 45 pairs,
   90 sentences. jev asked two `noul` questions per sentence: grammatical? natural/sensible?
   A 20-item (zh/ja, obvious+subtle only) **English-prompt control** re-asks the identical
   questions in English wording over the same zh/ja sentences.
2. **Real-gold entailment** (`run_entailment.py`): 150 qids (50/language) from
   `data/eval/entailment_sample_150.json` (real production passages/questions). Ground truth
   is **structural**: the stated answer = positive (label 1), each of its 3 distractors =
   negative (label 0) — per repo memory this is a free, real, but lower-bound-only signal (a
   distractor is a proxy for "wrong", not the hardest real negative). 600 items, one `noul`
   ("does the passage entail this candidate answer?") call each.
3. **Distractor-plausibility vs. the live judge** (`run_distractor.py`): 358 real production
   records (`data/eval/distractor_ablation_2026-08-20.json`, already scored live by
   `google/gemini-3.5-flash-lite`, the v7 two-axis judge) x ~3 distractors each = 1074 items.
   Passage/question/answer text joined in from the (still-unlabelled, per memory) gold-frame
   CSVs by qid. jev asked the **same two axes the live judge uses** (`fit` 1-5, `confusability`
   1-5, as `score` questions) plus a standalone `noul` "is this definitely wrong / not also
   correct" probe. A jev-side verdict (accept/flag/reject) was derived with the *exact*
   thresholds `services/test_generation/schemas.py:axes_to_verdict` uses, for a fair
   same-content comparison against the live judge's stored verdict.

**No human-adjudicated distractor gold set exists** — `data/eval/distractor_gold_frame_2026-08_*.csv`
is confirmed unlabelled (all `topical_distance`/`confusable`/`also_correct` cells blank on
inspection), matching the repo memory note ("gold frame built, unlabelled"). So (3) is an
**agreement-with-the-incumbent** measurement, not an accuracy-against-truth measurement — and
its own `fit`/`confusability` axes are **not** the same thing as "is this option also
correct", so the standalone `definitely_wrong` probe has no comparison partner at all and is
reported only descriptively.

Cost of the *incumbent* judges: `llm_calls.cost_usd` is **100% NULL** for both
`judge_answer_entailment` (0/150) and `judge_distractor_plausibility` (0/78) right now —
independently reproducing the repo memory's recurring-NULL-cost defect. The nearest real cost
figures available are sibling judges on the same call path: `cloze_distractor_judge` averages
**$0.000265/call** (78 rows with cost) and `judge_ladder_l1_distractor` averages
**$0.00125/call** (61 rows). These are the honest cost baselines used below, not the exact
incumbent judges' own cost.

---

## 2. Headline numbers

| Sub-experiment | zh AUC | en AUC | ja AUC | Agreement w/ incumbent |
|---|---|---|---|---|
| Controlled grammar+naturalness (combined score) | 0.907 | 0.873 | 0.936 | n/a (no incumbent ran on synthetic data) |
| Entailment (real gold, structural) | **1.000** | **1.000** (0.9996) | 0.969 | kappa 0.91 (zh vs deepseek) / 0.91 (en vs gemini) / 0.87 (ja vs gemini) |
| Distractor 3-way verdict vs. live gemini judge | — | — | — | kappa **0.057 (zh) / 0.152 (en) / 0.062 (ja)** — near chance |

Cost: **$0.00002–0.00005/item** across all three experiments (mean $0.0000405/item on
entailment, the largest run). Latency p50 ≈ 0.53s, p95 ≈ 0.62–0.68s, all three experiments.
Both are consistent with the documented pricing ($0.042/M input, $0 output) and P50≈0.22s
provider latency (our p50 is higher, ~0.53s, likely dominated by our own network round-trip
rather than the model — see caveats).

**In one sentence:** jev is an excellent, extremely cheap drop-in for binary/graded
correctness checks where the underlying signal is close to unambiguous (entailment: AUC
0.97-1.00, kappa 0.87-0.91 against the incumbent) — but it does **not** reproduce the live
distractor-plausibility judge's specific two-axis calibration (kappa ~0.06-0.15) because its
`confusability` ratings run systematically lower (mean 2.10 vs. gemini's 2.80 on the same
items) and the live judge's accept/flag/reject thresholds were tuned for gemini's score
distribution, not jev's.

---

## 3. Controlled corruption set — details

Per-language ROC-AUC and best-threshold accuracy (native-language prompts, `combined` =
`grammatical_noul x natural_noul`, n=30 items/language = 15 correct + 15 corrupted):

| Lang | AUC (combined) | Best-threshold acc | Acc @ 0.5 | Precision @ 0.5 | Recall @ 0.5 |
|---|---|---|---|---|---|
| zh | 0.907 | 0.90 (t=0.40) | 0.90 | 0.83 | 1.00 |
| en | 0.873 | 0.87 (t=0.84) | 0.80 | 0.71 | 1.00 |
| ja | 0.936 | 0.90 (t=0.82) | 0.73 | 0.65 | 1.00 |

**Calibration note:** recall is 1.00 at threshold 0.5 in every language — jev never scores a
genuinely correct sentence as defective — but precision is only 0.65–0.83, because jev's noul
scores skew high overall (best thresholds land at 0.4–0.84, not 0.5). **0.5 is not a
well-calibrated cutoff for this rubric**; a deployer would need to pick a per-language
threshold from a calibration sample, exactly as the jev docs themselves recommend.

**Detection rate by defect type** (does the corrupted item score lower than its correct pair,
combined across all 3 languages, n=3 per cell):

| Defect type | obvious | moderate | subtle |
|---|---|---|---|
| particle | 2/3 | 2/3 | 2/3 |
| word_order | 3/3 | 3/3 | 3/3 |
| verb_form | 3/3 | 3/3 | 2/3 |
| semantic_anomaly | 3/3 | 3/3 | 3/3 |
| wrong_sense | 2/3 | 3/3 | 3/3 |

**Particle/measure-word errors are jev's weakest category** — worth noting this held at
*every* subtlety level, including sentences the agent rated "obvious." Two concrete failures,
both zh, both scored *identically* for the correct and corrupted sentence:

- `朋友们没在群里发消息。` (correct) vs. `朋友们没在群里发消息了。` (corrupted: 没...了
  aspect clash) — grammatical 0.91 vs 0.91, natural 0.95 vs **0.96** (corrupted scored
  *higher*).
- `这件毛衣是羊毛的，摸起来很柔软。` (correct, 件) vs. `这个毛衣是羊毛的，摸起来很柔软。`
  (corrupted, 个) — grammatical 0.97 vs 0.97, natural 0.97 vs 0.97. Completely missed.

Caveat on this specific example: **个** as a generic classifier for 毛衣 is common in casual
spoken Mandarin, so this may say more about jev tolerating real-world usage than about a
strict defect — the agent's own "obvious" label may have been too confident here.

**English-prompt control** (zh/ja, obvious+subtle subset only, n=20/language, small-sample):

| Lang | Native-prompt AUC | English-prompt AUC |
|---|---|---|
| zh | 0.907 (full set) / n/a on this subset alone | 0.950 |
| ja | 0.936 (full set) / n/a on this subset alone | 0.880 |

Mixed result, opposite directions: the English-prompt control did *better* for zh and *worse*
for ja on this 20-item subset. Given n=20/language this is well within noise — **no confident
claim that native-language prompting helps or hurts** can be made from this sample; it would
need a much larger control to resolve, especially since the effect sizes (zh +0.04, ja −0.06)
are smaller than what 20 items can reliably distinguish.

---

## 4. Real-gold entailment — details

| Lang | n | AUC | Best acc | Precision/Recall @0.5 | kappa vs incumbent | incumbent model |
|---|---|---|---|---|---|---|
| zh | 200 | 1.000 | 1.000 (t=0.18) | 1.00 / 0.94 | 0.907 | deepseek/deepseek-chat |
| en | 200 | 0.9996 | 0.990 (t=0.36) | 0.98 / 0.98 | 0.910 | google/gemini-3.5-flash-lite |
| ja | 200 | 0.969 | 0.955 (t=0.34) | 0.93 / 0.84 | 0.872 | google/gemini-3.5-flash-lite |

Mean jev score by gold label: zh pos=0.87/neg=0.03, en pos=0.91/neg=0.04, ja pos=0.77/neg=0.07
— strong, clean separation in all three languages, best in zh/en, slightly weaker in ja
(more false negatives: 8/50 answers scored <0.5 despite being the stated correct answer).

**Failure examples** (jev score, gold label, candidate text):

- False negative, zh, score 0.43 (gold=answer): `每周检查数据` — a terse, context-dependent
  answer; likely under-scored because the candidate alone reads as an incomplete fragment
  without re-deriving the passage's framing.
- False negative, zh, score 0.44 (gold=answer): `为了统一各国塑料禁令的执法标准并解决法规碎片化问题`
  — long, abstract paraphrase-style answer to an inference question; jev may be discounting
  paraphrase-distance the way a strict "was this stated" reading would.
- False positive, en, score 0.55 (gold=distractor): `"They play against each other."` — a
  vague statement that happens to be topically consistent with almost any passage about two
  parties, so it is a weak negative to begin with (the structural-gold caveat: a distractor is
  not the hardest possible wrong answer).
- False positive, ja, score 0.91 (gold=distractor): `環境問題が国家の制度設計能力を問う課題であると強調するため`
  — a fluent, on-topic-sounding distractor that a partial reader plausibly would pick too; this
  one looks like a genuinely hard negative, not noise.

---

## 5. Distractor-plausibility vs. the live judge — details

| Lang | n | fit r | confusability r | verdict kappa | raw agreement | jev accept/flag/reject | gemini accept/flag/reject |
|---|---|---|---|---|---|---|---|
| zh | 354 | 0.476 | 0.479 | 0.057 | 54.5% | 216/123/15 | 249/88/17 |
| en | 359 | 0.475 | 0.411 | 0.152 | 57.7% | 192/149/18 | 297/49/13 |
| ja | 241 | 0.273 | 0.359 | 0.062 | 57.1% | 135/102/1 | 212/21/5 |

Per-axis rank correlation is moderate (0.27-0.48) — jev and gemini broadly agree on *which*
distractors are more/less confusable and more/less on-topic — but the derived 3-way verdict
barely beats chance. Root cause, confirmed by comparing raw score distributions on the same
954 items:

| | jev mean | gemini mean |
|---|---|---|
| fit (1-5) | 4.39 | 4.84 |
| confusability (1-5) | 2.10 | 2.80 |

jev's confusability ratings run **systematically lower** than gemini's (median 2.0 vs 2.0, but
jev's 75th percentile is 2.5 vs gemini's 4.0 — gemini's distribution is bimodal around 2/4,
jev's is smoothly concentrated 1.3-2.9). The live judge's thresholds
(`REVIEW_BAND=3`, `CONFUSABILITY_ALSO_CORRECT=5`, `CONFUSABILITY_INERT_MAX=1`) were tuned
against *gemini's* score distribution — porting them unchanged onto jev's differently-shaped
distribution routes many gemini-"accept" items into jev-"flag". This is a **calibration
mismatch, not a disagreement about content** — five representative disagreements:

| Lang | Distractor | jev fit/conf | jev verdict | gemini fit/conf | gemini verdict |
|---|---|---|---|---|---|
| zh | 因为朋友们都劝作者不要买新衣服 | 4.16/1.33 | flag | 5/2 | accept |
| zh | 联合国主导的多边谈判进程是解决跨境塑料污染转移问题的唯一有效途径 | 4.99/2.66 | flag | 5/2 | accept |
| ja | 現代の子どもたちは物語から価値観を学ぶことに興味を示さない | 4.34/2.54 | flag | 5/2 | accept |
| ja | でんしゃ | 3.75/1.66 | accept | 5/1 | flag |
| zh | 仅靠消费者改变购买习惯就能彻底解决快时尚造成的环境危机。 | 4.96/2.62 | flag | 5/4 | accept |

The standalone `definitely_wrong` noul probe (no comparison partner, descriptive only): mean
P(yes) = 0.92 (zh) / 0.95 (en) / 0.90 (ja) — jev says "yes, definitely wrong" for the vast
majority of real production distractors, and correlates weakly *negatively* with gemini's
confusability score (r ≈ −0.20 to −0.28, as expected in direction: higher confusability should
mean less "definitely wrong", though the magnitude is weak). **This axis has no gold and no
matching incumbent question — it cannot be scored for accuracy, only reported.**

---

## 6. Cost and latency

| Sub-experiment | n (ok) | mean cost/item | p50 latency | p95 latency |
|---|---|---|---|---|
| Controlled | 130 | $0.0000201 | 0.53s | 0.62s |
| Entailment | 600 | $0.0000405 | 0.53s | 0.65s |
| Distractor | 954 | $0.0000531 | 0.53s | 0.68s |

Total spend across all three: **$0.0775** of the $1 cap. Per-item cost is 1-2 orders of
magnitude below the cheapest comparable incumbent-judge figure this session could find
(`cloze_distractor_judge` $0.000265/item, `judge_ladder_l1_distractor` $0.00125/item — neither
is the exact judge being displaced, since `judge_distractor_plausibility`'s own `cost_usd` is
NULL; see caveats). Latency (p50 0.53s) is higher than jev's documented P50≈0.22s
provider-side figure — likely our own network/TLS round-trip overhead from this environment,
not a documentation error, since it is stable across all three independent runs (0.53s each).

---

## 7. Honest caveats

- **Sample size.** 45 controlled pairs (15/language) and their 20-item English-prompt control
  subset are small; per-cell detection rates above are literally out of 3. Treat every rate in
  §3 as illustrative, not a stable estimate — a single flipped item moves a cell from 2/3 to
  3/3.
- **Synthetic corruptions are almost certainly easier than real generator errors.** These 45
  corruptions were authored by the agent to be clean, single-defect-type minimal pairs. Real
  exercise-generation failures are messier (multiple confounded defects, generator artifacts,
  partial garbling) — the controlled-set AUCs (0.87-0.94) are an optimistic ceiling, not a
  production-representative estimate.
- **The distractor "gold" is not gold.** No human ever labelled `also_correct`/`confusable`/
  `topical_distance` on the frame used here (confirmed blank on read) — §5's kappa measures
  agreement with an *incumbent model*, not correctness. A low kappa could mean jev is wrong,
  gemini is wrong, or (per §5's finding) neither is "wrong" and the thresholds are simply
  uncalibrated for jev's score distribution.
- **Entailment gold is structural, not human-adjudicated** (memory: "entailment gold labels
  are structural and free"): a distractor is a proxy for a wrong answer, not necessarily the
  hardest real negative a generator would actually produce. The en false positive above
  (`"They play against each other."`) illustrates a genuinely weak negative inflating the
  apparent error rate.
- **English-prompt-control n=20/language is too small to resolve the native-vs-English
  question** the brief asked about; the two languages moved in opposite directions, which is
  what noise looks like at this sample size, not evidence either way.
- **Cost comparison is once-removed.** The exact incumbent judges' `cost_usd` is NULL live
  (independently reproducing a known repo defect); the baselines used are sibling judges on
  the same call path, not the judges being displaced.
- **Language support for jev is undocumented** (per `jev_api_summary.md`) — this experiment's
  strong zh/ja numbers are the best evidence available that it works, but OpenRouter/TypeSafe
  make no formal multilingual guarantee.
- **120 distractor items (11%) never ran**, cut off by the account-wide credit exhaustion
  described at the top — the 954 that did complete are not known to be a biased subsample
  (concurrency-8 submission order, not stratified by language/type), but this was not verified
  beyond checking that all 3 languages are still represented (zh 354, en 359, ja 241 — ja's
  share is visibly smaller, worth a note since ja records may have been later in submission
  order and disproportionately cut).

---

## Files in this directory

`env_setup.py`, `jev_client.py`, `rubric.py`, `controlled_set.py`, `run_controlled.py`,
`run_entailment.py`, `run_distractor.py`, `analyze.py`, `metrics_controlled.py`,
`metrics_entailment.py`, `metrics_distractor.py` — all runnable scripts, no repo files
touched. Raw responses: `controlled_results.json` (130), `entailment_results.json` (600),
`distractor_results.json` (1074, 120 marked `_error`). Computed metrics:
`metrics_controlled.json`, `metrics_entailment.json`, `metrics_distractor.json`.
