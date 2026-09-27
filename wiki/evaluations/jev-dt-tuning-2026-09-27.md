---
title: "Tuning jev (typesafe/jev-1.13) to grade Dual Translation — Experiment Report"
type: evaluation
status: complete
last_updated: 2026-09-27
open_questions:
  - "OPEN: Does the step-by-step jev grader hold up on REAL learner submissions? Every number here comes from seeded, synthetic errors on 10 passages per language."
  - "OPEN: Should jev run in shadow mode next to the live DT grader? DT grading is not logged to llm_calls, so a shadow run needs its own place to store results first."
  - "OPEN: Is ~50% error recall on zh/ja acceptable for a learner-facing 'what kinds of mistakes you make' report? The errors jev flags are almost always real, but it misses half of the (mostly minor) ones."
  - "OPEN: Naturalness and range are still ungradeable by jev (and still barely testable, because gold barely varies them). Leave them with the live grader?"
  - "OPEN: Should a human spot-check a sample of the silver items (built and adjudicated by three Sonnet raters, not by a human)?"
---

# Tuning jev to grade Dual Translation (DT)

**Date:** 2026-09-26 → 2026-09-27 · **jev spend:** $0.058 of a $2 cap · **No DB writes, no production code changed.**
**Artifacts:** `data/eval/jev_dt_2026-09-26/` (harness, cached responses, silver sets, `results/final_summary.json`).
**Follows:** [[evaluations/jev-judge-feasibility-2026-09-26]] §3.5, where jev asked for DT bands directly did badly on English.

## 1. Bottom line

The change that mattered was how we ask jev. We stopped asking it for a 1–4 band. Instead it answers narrow questions about each sentence, and Python works out the bands the same way the live grader does.

- **English accuracy went from unusable (.095) to .956**, beating the live grader's .778. The "with it" → "without it" answer that jev missed before is now caught and rated critical. All 8 meaning-inversion items (2 gold, 6 silver) were caught.
- **Japanese matches or beats the live grader on all three derived dimensions**: fidelity .830 vs .371, understandability .712 vs .332, accuracy .455 vs .412.
- **Chinese is mixed.** Understandability is better (.737 vs .577), but accuracy (.412 vs .570) and fidelity (.773 vs .891) are worse than the live grader.
- **As a cheap pre-filter**, jev can safely skip 33–37% of ja and en items with no over-grading on the gold set. zh gets almost no benefit (7%).
- **The error-type labels are good enough for a strengths-and-weaknesses report**: jev names the right error type 69% (ja), 75% (zh) and 95% (en) of the time.
- **Cost** is about $0.00013–0.00023 per item, around 200–400× cheaper than the live grader, at about 0.3 s per item versus minutes.
- **Naturalness and range still fail.** They can't be graded this way, and the gold set can't test them properly yet.

**What this is not:** proof that jev can replace the live grader. There are only 30 gold items per language, the errors were planted rather than made by real learners, and most confidence intervals are wide. Read the results as "promising enough to test on real submissions", not "ship it". See §6.

## 2. What we asked jev, and why

jev is a classifier. It answers yes/no, pick-one and 0–N score questions, and returns probabilities. It can't write explanations.

The earlier experiment asked it straight out: "what band is this answer's accuracy?" That fails in English because a meaning flip like with→without is perfectly grammatical, so nothing in the sentence looks wrong.

The live grader doesn't work that way. It finds individual errors, gives each an error type and a severity, and adds up penalties to get the accuracy, fidelity and understandability bands. So we asked jev to do the same thing, one sentence at a time.

1. The reference and learner passages are split into matching sentence pairs. jev sees both **full passages** as context, but each question is about one sentence pair. A sentence identical to the reference is marked clean without a call.
2. **One jev call per sentence** asks, in the learner's language (Chinese questions for zh, Japanese for ja):
   - Is there an error in this sentence? (yes/no)
   - Which error type is it? (pick one from that language's v5 error types, each with a short description in the language itself)
   - Five narrow checks: is a negation reversed? Is a quantity changed? Is who-does-what swapped? Is meaning left out? Is meaning added?
   - How severe is it? We tried several ways of asking; see §3.
3. **Python** does the reasoning. An error type only counts if an error was detected, and severity is set by the chosen rule. The resulting error list goes through the live scoring code (`services/dual_translation/scoring.py`) unchanged, so the bands mean exactly what live bands mean.

Naturalness and range are separate 0–3 score questions, asked once for the whole passage, because the live grader also judges these directly.

## 3. Things we learned along the way

**The weak point was severity, not detection.** The first sentence-by-sentence run got accuracy QWK ≈ 0 in zh and ja, even though jev spotted errors well (detection AUC .75–.95). Swapping in the correct answer for each step in turn showed where the loss came from. Correct severity alone recovered most of the gap (zh accuracy 0 → .53, ja fidelity .57 → .98). Correct detection or correct error type barely helped.

**"Major" doesn't mean "changes the meaning".** We first set severity with "does this change the meaning?": yes meant major, no meant minor. But in the gold labels, *major* means "clearly wrong to a native reader", even when you can still tell what was meant. A wrong resultative complement in Chinese is major without changing the meaning. jev answered the meaning question correctly and was marked wrong for it. The fix was to try four severity rules and let the silver data choose:

| Rule | How severity is decided | Chosen for |
|---|---|---|
| Ask "does it change the meaning?" | yes → major | — (lost everywhere) |
| Ask minor / major / critical directly | jev picks one, from definitions written in that language | **zh** |
| Default severity per error type (from the taxonomy), raised to critical if jev is very sure the meaning changed | Python rule + one jev answer | **ja, en** |
| Ask "would a native reader see this as clearly wrong?" | yes → major | — |

**People disagree about severity too.** Three independent raters built the silver sets (§4). They agreed on whether there was an error 96–100% of the time, but on severity only 62–85%, and on the exact error type 69–92%. So severity is genuinely a judgement call. jev's severity accuracy (54–75%) should be compared with that human-like ceiling, not with 100%.

**A harness bug, found and fixed.** An audit found that clean items whose sentences all matched the reference were silently left out of scoring (n=29 instead of 30). They are now counted as band 4. No chosen setting changed, and the numbers moved by about ±0.02. The same audit found **no leakage**: gold labels are used only for the final comparison, and every setting was chosen on silver.

## 4. Data: gold for testing, silver for tuning

- **Gold (testing only):** the 90 human-adjudicated items in `tests/fixtures/dt_gold/` (30 per language). Nothing was tuned on them.
- **Silver (tuning):** 101 new seeded items (zh 34, ja 32, en 35) in `data/eval/jev_dt_2026-09-26/silver/*_final3.json`.
  - A Sonnet drafter wrote them with the same seeding helper as the gold set (spans are computed, bands come from the frozen scoring rules).
  - Two more Sonnet raters labelled them **blind**. Each field (whether there's an error, error type, severity, naturalness, range) was settled by a 2-of-3 majority, and items with no majority were dropped (zh lost 4 of 38).
  - Silver was weighted towards the error types the gold set barely covers, towards meaning inversions (8 in en), and towards items where naturalness or range really is below 4.
- **Settings** (cutoffs and severity rule, per language) were chosen by 5-fold cross-validation on silver, then frozen before the one gold run.
- **Caveat:** en and ja silver reuse the gold passages (no other tier-3 passages exist), with different planted errors. zh silver adds 4 new passages. Tuning therefore saw the same source text as the test, though never the same learner answers.

## 5. Results (gold, n=30 per language, frozen settings)

QWK measures agreement on an ordered scale; above about .6 is good. It's computed with the same function as `scripts/run_dt_grading_eval.py`, so it's directly comparable with the live grader's numbers from [[evaluations/dt-grading-v2-2026-07-19]]. Brackets are 95% bootstrap intervals.

| Language | Dimension | jev, step by step (this report) | jev asked for a band (before) | Live grader |
|---|---|---|---|---|
| en | accuracy | **.956** [.83, 1.0] | .095 | .778 |
| en | fidelity | .487 [−.05, .76] | .314 | .487 |
| en | understandability | .724 [0, .96] | .205 | .746 |
| zh | accuracy | .412 [0, .76] | .661 | **.570** |
| zh | fidelity | .773 [−.09, .94] | .893 | **.891** |
| zh | understandability | **.737** [−.05, 1.0] | .571 | .577 |
| ja | accuracy | .455 [.01, .77] | .308 | .412 |
| ja | fidelity | **.830** [.44, .96] | .740 | .371 |
| ja | understandability | **.712** [0, .93] | .332 | .332 |

**Reading the intervals:** at n=30, with about 70% of items clean, most intervals are very wide. The differences we can reasonably trust are en accuracy (jev ahead), ja fidelity and understandability (jev ahead), and zh fidelity (live ahead). The rest are **inconclusive**.

Note that in zh, the old single band question beat the new method on accuracy and fidelity. The step-by-step approach isn't better everywhere.

| Language | Error detection: precision / recall / AUC | Error type right, top 1 / top 3 | Severity right |
|---|---|---|---|
| zh | 1.00 / .52 / .966 | 75% / 100% | 75% |
| ja | 1.00 / .50 / .985 | 69% / 92% | 54% |
| en | .95 / .80 / .924 | 95% / 100% | 75% |

**Precision near 1 but recall around 50% in zh and ja** means jev almost never invents an error, but misses about half of them. The misses are mostly minor, so they rarely change a band, which is why QWK still looks acceptable. For an error-type report, it would under-count minor slips.

**Meaning inversions (en):** 8 of 8 were flagged with critical severity: 2 of 2 on gold (including with→without) and 6 of 6 on silver. The silver figure uses the frozen settings rather than a strict nested holdout.

**Naturalness and range:** silver QWK was −.10 to .10 for naturalness and .36–.73 for range. Rewording the questions didn't reliably help. Gold can't test either dimension (range is 4 on all 90 gold items). **Fail.**

### Routing: can jev take the obviously clean items off the live grader?

We treated an item as "confidently clean" when jev's error probability stays below a cutoff on every sentence and every narrow check. The cutoff was fitted on silver so that no routed silver item had a real error.

| Language | Share of gold items routed | Over-graded (routed but had an error) | Off by 2+ bands |
|---|---|---|---|
| en | **36.7%** (11/30) | 0 | 0 |
| ja | **33.3%** (10/30) | 0 | 0 |
| zh | 6.7% (2/30) | 0 | 0 |
| ja, accuracy + understandability only | 53.3% | **12.5%** | 0 |

The looser accuracy + understandability gate, suggested in the earlier report, **routes more but over-grades**, so we'd drop it. "Zero over-grades" rests on 10–11 routed items, so it's encouraging but not a measured error rate.

### Cost and speed

| | jev step by step | Live grader |
|---|---|---|
| Cost per item | $0.00013 (en), $0.00018 (zh), $0.00023 (ja) | about $0.025 (en), $0.042–0.058 (zh/ja) |
| Time per item | about 0.3 s | minutes for ja (detector → verifier cascade) |

## 6. Against the success criteria we set

| Criterion | Result |
|---|---|
| zh/ja accuracy and fidelity at least as good as live | **ja passes; zh fails** (accuracy and fidelity both below live) |
| en accuracy ≥ .60, with→without caught | **Passes** (.956; caught and rated critical) |
| Error type right ≥ 60% | **Passes** in all three (69–95%) |
| Route ≥ 30% with no 2-band misses and ≤ 5% over-grading | **Passes for en and ja; fails for zh** |
| Naturalness/range QWK ≥ .40 on silver | **Fails** |

## 7. Recommendations

1. **Next: shadow mode, not replacement.** Run the step-by-step jev grader next to the live DT grader on real submissions and compare. That needs somewhere to store the results, because DT grading isn't logged to `llm_calls`. This is the only way past the two biggest caveats: synthetic errors and n=30.
2. **Error-type output is the first thing worth building on**, for the planned "your strengths and weaknesses" report. It's cheap, the precision is high, and the error types are mostly right. The report should say it under-counts minor slips.
3. **Routing for en and ja only**, using the full three-dimension gate, and only after the shadow run confirms zero over-grading on real traffic. Not zh.
4. **Keep naturalness and range with the live grader.** To test them at all we'd need gold items where those bands really vary, and human-adjudicated ones, because the Sonnet raters disagreed most on naturalness.
5. **Treat zh as unsolved.** jev detects errors in zh as well as in ja, so the problem is severity and the accuracy/fidelity split. The simpler band question did better on zh fidelity; a mix of the two methods for zh is worth one more try.

## 8. Side findings

- **The dictation grader can't see pure insertions.** While building silver items, drafters found that an inserted word alone never lowers the dictation accuracy check (`services/dictation/grader.py` leaves insertions out of `word_total`). So "addition" and inserted-connective errors are invisible at that stage. It's worth a task if addition errors matter.
- **Short edits can disappear.** Same-length, one-letter-apart word pairs (commands→command) can collapse under the dictation grader's fuzzy matching. This is already documented in the gold README for English morphology, and it also affects agreement, plural and spelling seeds.
- **zh `bei_passive` has no gloss or template** in the v4 zh taxonomy seed; it only exists in the v5 subtype list.

## Related Pages
- [[evaluations/jev-judge-feasibility-2026-09-26]] — the first jev experiment this one follows
- [[evaluations/dt-grading-v2-2026-07-19]] — live-grader baseline on the same gold set
- [[features/dual-translation]] · [[features/dual-translation.tech]]
- [[algorithms/evidence-first-grading.tech]] — the live detect → verify → score design this copies
