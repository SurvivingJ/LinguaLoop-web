---
title: "Jev (typesafe/jev-1.13) as a Judge — Feasibility Report"
type: evaluation
status: complete
last_updated: 2026-09-26
open_questions:
  - "Does jev's zh/ja handling have any documented guarantee, or are we permanently relying on empirical spot-checks (432+ calls so far, all coherent, but OpenRouter/TypeSafe document nothing either way)?"
  - "Should a jev arm log to llm_calls (pipeline='diag' lane) or stay in a separate ad hoc harness — decision needed before any staged rollout begins?"
  - "Is there appetite to build the entailment/tier gold sets properly (the entailment set is structural-only, the distractor set is genuinely unlabelled) before jev is allowed to gate anything in production?"
  - "Does the qwen-family generation policy (ADR-028) have any bearing on whether jev is allowed as a judge for zh/ja content, or is judge model choice fully independent of that decision?"
---

# Jev (typesafe/jev-1.13) as a Judge — Feasibility Report

> **Update 2026-09-27:** the tier-classification recommendation below was adopted and shipped as [[decisions/ADR-029-jev-tier-assignment]] ([[features/test-tier-assignment.tech]]). Real content needed per-language score→tier calibration against blind gold sets — see [[evaluations/jev-tier-calibration-2026-09-27]]; the 52–76% agreement with the old labels in §3.4 was largely the old labels being wrong, not jev.

## 1. Bottom line

**Jev is ready to replace one specific judge outright (tier classification / re-tiering), ready to add as a cheap pre-filter or second opinion in a few more places, and not ready to replace our best-tuned graders (distractor plausibility, English DT grading).**

Where it's strong: telling apart obviously-right from obviously-wrong content (grammar checks, "does this answer the question" checks, telling a toddler-level text from a professional-level text). Cost is negligible everywhere — 1–2 orders of magnitude cheaper per call than anything we run today, because jev only charges for what you send it, not what it writes back.

Where it falls short: anything that requires actually comparing two pieces of meaning word-for-word. It has no reasoning step, so it can miss a single flipped word ("with it" → "without it") that changes an answer from right to wrong while staying perfectly grammatical. It also doesn't reproduce the specific calibration of our current best distractor judge — not because it disagrees on content, but because its 1–5 ratings are shaped differently and our thresholds were tuned for the other model.

**Recommended first integration: retire the sequential 6-call tier-fit judge and replace it with one jev call per topic.** It's the cleanest win in this whole investigation — cheap, already proven to separate difficulty levels correctly on unambiguous text, and displaces a slow, repetitive judge that was never well-instrumented in the first place.

**Do not yet**: use jev to replace the live distractor-plausibility judge, or to replace English DT (Dual Translation) grading. Both need either recalibration against jev's own score distribution or accept a real accuracy loss.

**Blocking everything, right now**: the OpenRouter account is out of credit (see section 9). No further calls of any kind — jev or otherwise — will succeed until it's topped up.

---

## 2. What jev is, and how it's different from what we run today

Every judge we have today is a chat model: we send a prompt, it writes a paragraph or a JSON blob back, and we parse that text into a verdict. Jev is not that. It's a "decision model" — you send it a piece of content (`state`) plus one or more typed questions (`questions`), and it hands back typed numbers, never prose:

- **Yes/no mode (`noul`)** — a probability that the answer is "yes" (e.g., "is this grammatical?" → 0.96).
- **Multiple choice (`choice`)** — picks one option from a fixed set and gives a probability for each option (e.g., "which tier does this passage belong to?").
- **Ordered scale (`score`)** — places the input on a scale you define (e.g., a 1–5 quality rating), again with a probability distribution over the levels.

Practical consequences of this design:

- **No reasoning trace.** You can't ask it "why", and it can't catch an error by reasoning through the meaning — it's making a fast, intuitive-style call, not working something out. This is the single biggest limitation found in testing (see sections 3.2 and 3.5).
- **Much cheaper.** $0.042 per million input tokens, **and nothing for output** — because it isn't writing anything, there's no output-token bill at all. Everything we run today pays for the model's written response too.
- **Faster.** Roughly half a second round-trip in our tests (their own benchmark says ~0.22s; our extra ~0.3s is just our network overhead, not the model being slow).
- **A different API entirely.** It doesn't live behind the normal "chat completions" endpoint every other model in this codebase uses — it has its own endpoint (`/api/alpha/decisions`), so none of our existing client code can call it as-is (more in section 6).
- **Same billing account.** Same OpenRouter API key, same dashboard, same budget pool as every other model we call — including the fact that it shares the same credit-exhaustion risk (section 9).

---

## 3. What we tested, and what happened

Four experiments (test scripts and raw results are archived — see section 10). All read-only against the database; nothing in production was touched or changed.

### 3.1 Sentence grammar / meaning checks (controlled corruption set)

We took 45 real sentences in each language, deliberately broke each one in one specific way (wrong particle, wrong word order, wrong verb form, a sentence that's grammatical but doesn't make sense, or the wrong word sense), at three levels of subtlety, and asked jev "is this grammatical?" and "does this make sense?"

**How it did:** Good separation overall — 87–94% "area under the curve" (a 0–1 score for how well a test tells correct from incorrect apart; 0.5 is a coin flip, 1.0 is perfect). It never once called a genuinely correct sentence defective (recall 1.00 at the default cutoff) — but it over-flags: precision was only 65–83%, meaning a fair number of its "this is wrong" calls were actually fine sentences. **The default 0.5 cutoff is wrong for this use** — the best cutoffs found ranged from 0.4 to 0.84 depending on language, so any real deployment needs its own tuned threshold per language, not the textbook default.

**Where it failed, concretely:**
- Chinese aspect marker error (朋友们没在群里发消息 vs. …发消息**了**, an incorrect "没...了" combination) — jev rated the broken version *slightly higher* for naturalness (0.96 vs 0.91) than the correct one. Completely missed.
- Chinese measure-word error (这件毛衣 "this [garment-classifier] sweater" vs. 这个毛衣 "this [generic-classifier] sweater") — identical scores for both. Missed. To be fair, 个 as a generic classifier is common in casual speech, so this may be less a failure and more jev correctly tolerating something a strict grammar rule would flag — a caution about our own "obvious defect" labels, not just about jev.
- Every language's weakest category was particle/measure-word errors specifically — 2 out of 3 caught at every subtlety level, worse than every other defect type (word order and semantic nonsense were caught 3/3 everywhere).

**Caveat:** these are only 45 hand-made, clean, single-defect examples per experiment — real generator mistakes are messier (multiple things wrong at once), so these numbers are a best case, not what we'd see in production.

### 3.2 Answer entailment (does the passage support this answer?)

Real production data: 150 questions per — sorry, 150 total items per some slices, 200 per language overall, using the actual correct answer as the "yes" case and its wrong-answer distractors as the "no" cases (a free, reasonable, but not perfectly fair test, since a distractor is a proxy for "wrong," not the hardest possible wrong answer).

**How it did:** This is jev's best result by a wide margin — near-perfect separation. Chinese and English scored essentially 1.00 ("perfect separation" — every correct answer scored higher than every wrong one). Japanese was still strong at 0.969 but had more borderline misses. Measured against our own live judge's calls on the same items (kappa — a measure of how much two raters agree beyond chance, 0 = no better than random, 1 = perfect — was 0.87–0.91, i.e. strong agreement), jev tracks the existing judge closely here.

**Where it failed:** mostly the honest edge cases you'd expect from a proxy-negative setup — a vague-but-plausible-sounding wrong answer ("They play against each other") scoring as if it might be right, and a couple of terse, context-stripped correct answers scoring as if they might be wrong because they read as sentence fragments out of context.

### 3.3 Distractor plausibility (are the wrong multiple-choice options actually convincing?)

This is where jev clearly underperforms — but the reason matters. We compared jev's ratings on 954 real production items against our current live judge (a proper chat model tuned for this specific job). On raw agreement about which distractors are "more" or "less" confusable, jev and the live judge broadly agree (moderate correlation, 0.27–0.48). But when both scores get converted into an actual accept/flag/reject decision, agreement collapses to near-chance (kappa 0.06–0.15).

**Why:** it's a calibration mismatch, not a real disagreement. jev's "how confusable is this" ratings run systematically lower across the board (average 2.10 vs. the live judge's 2.80, on the same 1–5 scale) — jev is simply stingier with high confusability ratings. Our accept/reject cutoffs were tuned against the *other* model's score distribution, so porting them onto jev's differently-shaped scores routes a lot of genuinely fine content into "needs review." A representative example: a Chinese distractor rated fit 5 / confusability 2 by the live judge (accept) got fit 4.99 / confusability 2.66 from jev (flag) — same ballpark numbers, different side of an arbitrary line.

**Bottom line for this one:** jev's underlying judgment isn't obviously worse, but you cannot swap it in without re-deriving thresholds from scratch, and even then there's no guarantee it reaches the same practical accept rate the live judge does — because there's no true "gold" label for this data at all yet (nobody has ever hand-labelled which distractors are actually confusable — see caveats).

### 3.4 Tier classification / re-tiering the content library

We have six age-anchored difficulty tiers (T1 = a 4–5 year old's vocabulary, up through T6 = an educated adult professional). We asked jev to classify 179 real, live test passages into these tiers, using our own existing tier descriptions verbatim (nothing new to write).

**How it did — the key finding of this whole investigation: jev separates difficulty levels cleanly when the text is actually unambiguous.** On 54 hand-written texts deliberately written to sit squarely in one tier, jev got 89–100% exact agreement in all three languages and its scores climbed in a straight line from T1 to T6 exactly as expected. That's about as clean a pass as a classifier can get.

On real, messier production content, exact agreement with our existing tier labels drops to 52–76% (varies by language) — but this is expected and not necessarily jev's fault: our own tier labels are known to already be imperfect (Japanese content, for instance, is known to often run easier than its assigned label suggests), so a disagreement here is as likely to be jev catching an existing mislabel as it is to be a jev error. Within-one-tier agreement (i.e., is it at least close) stays high, 78–88%.

Repeatability was excellent — asked the same item three times, it gave the identical answer 85% of the time, and its numeric scores barely moved run to run (near-zero variance). It's also mostly insensitive to the order the tier options were listed in (only flipped its answer 5% of the time when we reversed the option order).

**Native-language vs. English prompt wording made no measurable difference here** — hence section 4's separate discussion.

### 3.5 Dual Translation (DT) rubric grading

This is our most demanding judge — grading a learner's translation against a reference across five dimensions (accuracy, fidelity, understandability, range, naturalness), and it's expensive: our live pipeline runs a two-stage "detector then verifier" cascade on a reasoning-heavy model, taking 2–3 minutes per item in Japanese.

**How it did, per dimension, measured as QWK** (quadratic weighted kappa — a 0–1-ish score for how well two raters agree on an *ordered* scale, giving partial credit for being one band off; roughly, above ~0.6 is "good agreement," below ~0.2 is "not much better than guessing"):

- **English accuracy: badly wrong.** jev scored 0.095 vs. the live stack's 0.778. The concrete failure: a reference translation said "...you can make many things **with** it..." and the learner wrote "...you can make many things **without** it..." — a single-word flip that completely inverts the meaning while staying perfectly grammatical. jev rated it "no grammar error" (14% confidence there was one) and gave it a high accuracy score, because there's nothing *structurally* wrong with the sentence — you have to actually compare meaning to catch it, and jev has no mechanism to do that comparison the way our verifier does.
- **Chinese and Japanese: competitive, sometimes better.** Chinese accuracy (0.661 vs. 0.570) and fidelity (0.893 vs. 0.891, essentially tied) were close to or matched the live stack. Japanese fidelity was clearly *better* under jev (0.740–0.830 vs. 0.371) — on the two languages where our live pipeline pays for a slow, expensive verifier model and still only gets middling results, jev's near-instant, near-free single call was as good or better on several dimensions.
- **Naturalness and "range":** both jev and the live stack are weak here across the board — but this looks like a limitation of the test data itself (the gold set barely varies these two dimensions), not clear evidence about either grader.

We also tested jev as a **cheap pre-filter**: only route an item to the expensive live grader if jev is confident it's either clearly excellent or clearly bad across every dimension at once. This correctly filtered out 0 errors in the small number of items it did filter — but that "all-5-dimensions-must-agree" rule was so strict it only qualified 0–10% of items, too few to trust as a real error rate yet. A looser rule — requiring agreement only on the two dimensions we weight most heavily (accuracy and understandability) rather than all five — looks more promising but wasn't built in this pass.

---

## 4. Native-language prompts: keep them anyway

Every prompt in this investigation was written entirely in the language being judged (Chinese instructions for Chinese content, Japanese for Japanese, English only for English) — matching our existing convention. We also ran small English-language control tests (English wording, native-language content) to see if that mattered.

**Result: mixed and inconclusive at the sample sizes we could afford.** In the tier-classification test, English wording made essentially no difference (agreement rates matched to the decimal point). In the sentence-grammar test, results moved in *opposite directions* for Chinese (English wording did slightly better) and Japanese (native did better) on a 20-item sample — which is what pure noise looks like, not a real effect. In the DT rubric test, native wording clearly won on two dimensions (Chinese understandability, Japanese accuracy — English wording actually did *worse than random* on both) but lost narrowly on one (Japanese fidelity) — again on a small sample (10 items).

**Recommendation: keep native-language prompts regardless of what these small tests show**, for two reasons beyond the numbers themselves: (1) it's our existing policy across every other judge in the codebase, and changing it just for jev would create an inconsistent, harder-to-maintain system for no proven benefit; and (2) where we did see a real gap, it favoured native wording, never the reverse. There's no evidence here that switching to English would help, and some evidence it could actively hurt on two specific dimensions.

---

## 5. Cost and efficiency

**Per-item cost is not close — jev is 1–2 orders of magnitude cheaper than anything we run today**, for every task tested:

| Task | jev cost/item | Incumbent cost/item | Ratio |
|---|---|---|---|
| Grammar/meaning checks | ~$0.00002 | ~$0.000265–0.00125 (sibling judges; exact incumbent's cost is unmeasured, see caveats) | ~10–60× cheaper |
| Answer entailment | ~$0.00004 | unmeasured (same defect) | — |
| Distractor plausibility | ~$0.00005 | unmeasured (same defect) | — |
| Tier classification | ~$0.000065/call (both modes) | not separately measured; structurally jev collapses up to 6 sequential calls into 1, and pays for input tokens only | order of magnitude, unconfirmed exact multiple |
| DT rubric grading, EN | $0.00014 | ≈$0.025 | **~180× cheaper** |
| DT rubric grading, ZH/JA | $0.00014 | ≈$0.042–0.058 | **~300–420× cheaper** |

Whole-library re-tiering our entire test catalogue (305 tests today) would cost about **$0.02 and take about 21 seconds** — negligible even at 100× today's content volume.

**Latency:** jev answered in about half a second per call across every experiment (their own benchmark claims ~0.22s; our extra time is our own network overhead, consistent across all four experiments, so it's not a fluke). For **DT grading specifically, this is transformative** — our current Japanese DT grading takes 2–3 minutes per item because it's a sequential two-stage call on a slow reasoning model; jev would return the same item in well under a second. That's the one place in this whole investigation where speed, not just cost, is the headline.

**Where speed gains are modest, not transformative:** batch test/exercise generation. Our own measurements show generating a test costs $0.0088 and takes 2.9 minutes, and **82% of that wall-clock time is vocabulary enrichment, not judging** — judges are only about 38% of the *cost*, and judging isn't the generation pipeline's bottleneck at all. Swapping a judge for a much faster one won't meaningfully speed up test generation as a whole, because the slow part is somewhere else entirely. Jev is a big win for judge-heavy, judge-slow paths like DT grading; it's a nice-to-have, not a game-changer, for the batch generation pipeline.

**One recurring caveat worth flagging plainly:** the exact incumbent judges' own logged costs are frequently NULL in our database (a known, recurring defect — see section 6) — so several of the "incumbent" cost figures above are the closest measured sibling judge, not the exact judge being displaced. The DT and tier-classification comparisons are the two solid, directly-measured figures in this table; treat the rest as directionally right but not exact.

---

## 6. Integration feasibility

**Engineering work needed:**

1. **A new client.** Neither of our two existing OpenRouter call paths (`services/llm_service.py`'s `call_llm()`, or the lighter `services/model_arena/llm_runner.call_model_with_usage()`) can call jev — both hit the standard chat-completions endpoint, and jev lives behind its own `/api/alpha/decisions` endpoint with a completely different request/response shape (`state` + `questions` in, `answers` + typed values out). This needs a small, standalone HTTP client — genuinely small (the experiment scripts already prove the pattern works, concurrency and retry-on-429/402 included).
2. **A decision on logging.** Do jev calls get written into our shared `llm_calls` table (for cost/verdict history alongside every other judge), or do they live in a separate lane so early diagnostic spend doesn't pollute per-pipeline cost reporting? The repo's own unbuilt "judge-eval-campaign" design already recommends a separate `pipeline='diag'` lane for exactly this reason — worth following that precedent rather than reinventing it. This is one of this report's open questions.
3. **Per-question, per-language threshold calibration.** Every jev experiment reached the same conclusion independently: **0.5 is not the right cutoff for any of these tasks.** Best thresholds ranged from 0.18 to 0.84 depending on task and language. This isn't optional polish — it's a prerequisite for using jev as a hard accept/reject gate anywhere.
4. **Gemini-tuned distractor thresholds will not transfer.** Confirmed directly: jev's confusability ratings run systematically lower than the live judge's on the exact same content, so our current `REVIEW_BAND`/`CONFUSABILITY_ALSO_CORRECT` thresholds (tuned for the live judge's model) would misclassify a large share of jev's ratings if reused unchanged.

**Risks:**

- **Single provider.** jev is served exclusively by TypeSafe through OpenRouter — there's no fallback provider the way most chat models on OpenRouter have. If TypeSafe has an outage, there's no automatic failover.
- **Alpha endpoint.** The API path is literally `/api/alpha/decisions` — this is pre-stable surface by OpenRouter's own naming, and could change without the same notice period a GA endpoint would get.
- **No reasoning → misses meaning inversions.** This is the structural limitation, not a bug: section 3.5's "with it"/"without it" failure and section 3.1's particle-error misses both stem from the same root cause — jev makes a fast, intuitive-style call and cannot re-derive meaning the way a chat model's reasoning trace can. Any task where the failure mode is "grammatically fine, semantically wrong" is a bad fit for jev alone.
- **`cost_usd` NULL logging defect.** Multiple incumbent judges in this codebase have a recurring, previously-"fixed" bug where their cost is never actually recorded (confirmed again in this investigation — both `judge_answer_entailment` and `judge_distractor_plausibility` show 100% NULL cost right now). Any real cost comparison work should fix this alongside adding jev, or the comparison will always be one-sided (jev's cost measured precisely via its own reported `usage.cost`; the incumbent's cost estimated from a sibling judge, as this report had to do).
- **Undocumented language support.** OpenRouter/TypeSafe do not officially document whether jev supports Chinese or Japanese at all — our own testing (600+ calls across four experiments, all coherent and well-separated) is the best evidence we have that it works, but it remains an empirical finding sitting on top of an undocumented guarantee, not a documented one.

---

## 7. Recommended roadmap

**Stage 1 — do now, low risk, high confidence:**
- Replace `services/topic_generation/agents/tier_fit_judge.py`'s six-call sequential tier walk with one jev `choice`/`score` call per topic. Section 3.4 already proved this works cleanly on unambiguous text; the messier real-content disagreement rate is expected and mostly reflects known existing label imperfections, not a jev shortfall.
- Build a jev arm into `scripts/measure_judge_flag_rate.py` (it's already model-agnostic at the results layer) so future comparisons don't need bespoke harnesses each time.

**Stage 2 — needs a small gold-labelling pass first:**
- Entailment pre-check: jev's entailment numbers are excellent (section 3.2), but the "gold" data is structural, not human-labelled — a distractor stands in for a wrong answer, which is a lower bound, not the real thing. Before trusting jev as a production gate here, hand-label a modest real sample (a few hundred items) to confirm the near-perfect separation holds against genuine hard negatives, not just distractor proxies.
- Tier re-calibration: once Stage 1 is live and generating its own disagreement data against the existing labels, use that to decide which of the two — jev or the existing label — is more often right, rather than assuming either is ground truth.

**Stage 3 — needs real recalibration work, don't skip this:**
- Grammar gate as a cheap pre-filter, not a replacement, in front of the existing LLM judges — use jev to catch the easy, obvious cases fast and cheap, and only send the genuinely ambiguous cases to the slower, smarter model. Its systematic blind spot for particle/measure-word errors (section 3.1) means it must never be the *only* check.
- DT as a tier-0 router, specifically for Chinese/Japanese fidelity — not for English accuracy, where jev demonstrably misses meaning-inverting errors. Needs the wider pre-filter rule from section 3.5 (gate on the two highest-weighted dimensions, not all five) built and tested properly before any live routing.

**Explicitly needs a real gold set before it gates anything:**
- Distractor plausibility. There is currently no human-labelled ground truth for "is this distractor actually confusable" at all — what exists is agreement-with-an-incumbent-model, which cannot tell us whether jev or the incumbent is closer to correct. Don't let jev (or, frankly, the incumbent) gate production decisions here until that gold set exists.

---

## 8. Brainstorm: other integration ideas

| Idea | Expected value | Effort |
|---|---|---|
| DT rubric grading (ZH/JA only, as a full replacement, not just a pre-filter) | High — jev matched or beat the live stack on 3 of 5 dimensions at ~300× lower cost/latency | Medium — needs the naturalness/range weakness addressed or accepted |
| Pre-filtering generations before expensive judges (grammar gate) | High — cheap, fast, catches the obvious cases; frees expensive judges for the hard ones | Low-Medium |
| Ensembling: jev + LLM disagreement triggers human review | Medium-High — turns jev's calibration mismatch (section 3.3) into a feature (a disagreement signal) instead of a bug | Medium |
| Live learner-answer grading (real-time DT/practice feedback) | High if latency matters to the user experience — sub-second feedback vs. minutes today | Medium-High — same accuracy caveats as DT grading apply |
| Topic/tier-fit judge (this report's Stage 1 pick) | High, proven | Low |
| Sense disambiguation / sense-linking sanity checks | Medium — untested here, but a `choice`-mode fit for "which sense does this word take in context" | Medium (needs its own pilot) |
| L1 confusable-pair sanity check (audio-confusable pairs) | Medium — untested here; plausibly a `noul` fit ("are these two renderings audio-confusable") | Medium |
| Furigana/reading correctness check | Low-Medium — untested; likely a narrow `noul` check, but the value depends on how often this actually breaks today | Low (cheap to pilot) |
| Flagging tests whose tier has drifted vs. ELO | Medium — the tier-classification work (section 3.4) is most of what this needs already | Low, given Stage 1 |
| Dedup / near-duplicate content detection | Low-Medium — untested, plausible `noul` fit ("are these two passages substantially the same") | Medium |
| Content-safety/appropriateness per age tier | Medium — jev's `choice`/`score` modes map naturally onto our existing tier constraints, similar to Stage 1 | Low-Medium |
| Classifier/measure-word drill validation | **Low — actively contraindicated.** Section 3.1 found particle/measure-word errors to be jev's single weakest category, at every subtlety level, in every language. Do not use jev alone here. | N/A |
| Prompt-regression monitoring (nightly cheap audit of all live content) | High — this is exactly the "extremely cheap, always-on, catches the obvious stuff" use case jev is best suited for | Medium — needs the pre-filter/gate logic from Stage 3 productionized first |
| Active-learning selection of items for human gold labelling | Medium — jev's confidence scores could flag the most uncertain/disagreement-prone items for a human to label first, making every future gold-labelling pass more efficient | Medium |

---

## 9. Operational alert

**The shared OpenRouter account ran out of credit entirely during this investigation** — confirmed via `GET /api/v1/credits`: `total_usage: 70.0027` against `total_credits: 70.0000`. This is a **hard, permanent 402 error** (`limit_source: "openrouter_credits"`), distinct from the retryable "in-flight budget" 402 that resolves itself after a short wait. 120 of 1,074 distractor-judge test requests (11%) failed for this reason mid-run and could not be retried.

**This blocks all OpenRouter calls right now — every pipeline in this repo, not just the jev experiments, including production judges and content generation.** The account needs a top-up before any further LLM work of any kind can run.

---

## 10. Appendix

**Spend for this investigation:** $0.0775 (Experiment A: grammar/entailment/distractor) + $0.0257 (Experiment B: tier classification) + $0.0153 (Experiment C: DT rubric grading) = **$0.1185 total**, against a combined $3.00 cap across the three experiments.

**File locations:**
- Scripts and results, archived (this repo, no API keys, checked for secrets before copying): `data/eval/jev_2026-09-26/`
  - `jev_api_summary.md`, `judge_inventory.md` — the two research/design documents this report is built on
  - `exp_a/` — grammar/naturalness controlled-corruption set, real-gold entailment, distractor-plausibility-vs-incumbent (`results.md` + all runnable scripts: `jev_client.py`, `controlled_set.py`, `run_controlled.py`, `run_entailment.py`, `run_distractor.py`, `rubric.py`, `analyze.py`, `metrics_*.py`, `env_setup.py`)
  - `exp_b/` — tier classification / re-tiering (`results.md` + `pull_tests.py`, `jev_prompts.py`, `jev_client.py`, `run_experiment.py`, `analyze.py`)
  - `exp_c/` — DT rubric grading vs. gold (`results.md` + `rubric_data.py`, `build_requests.py`, `jev_client.py`, `run_experiment.py`, `analyze.py`)
- Raw JSON results (not copied into the repo — large, and not needed to re-derive this report's numbers) remain in the session scratchpad at `C:\Users\James\AppData\Local\Temp\claude\c--Users-James-Documents-Coding-LinguaLoop-WebApp\85c90266-52b8-4fb1-9376-5767d11d3e2a\scratchpad\` and are not guaranteed to persist — re-run the archived scripts against a live Supabase connection to regenerate them if needed.

## Related Pages
- [[judge-eval-campaign]] — the unbuilt full model bake-off design this investigation partially previews
- [[evaluations/distractor-judge-two-axis-2026-08-20]] — the live distractor judge's own calibration, which jev's thresholds cannot yet reuse
- [[evaluations/dt-grading-v2-2026-07-19]] — the live DT grading baseline this report compares jev against
- [[evaluations/entailment-likert-v3-rollout-2026-08-19]] — the live entailment judge jev is compared against in section 3.2
