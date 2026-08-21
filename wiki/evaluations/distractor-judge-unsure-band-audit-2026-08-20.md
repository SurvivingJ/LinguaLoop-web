---
title: "Is the v7 unsure band honest, or did the wording make a confident model timid?"
type: evaluation
status: complete
last_updated: 2026-08-20
tasks:
  - TASK-719
  - TASK-720
verdict: "Honest. The wording hypothesis is refuted by ablation — removing the nudge DOUBLES the hedging."
open_questions:
  - "Honest uncertainty still is not correctness. Only TASK-726's gold set, or learner response data, can say whether the judge is unsure about the right items."
  - "Band 3 is used as 'medium' rather than 'unsure' unless the prompt pushes hard. Reconciling the band against the judge's own reason text is an untried lever."
---

# Is the v7 unsure band honest, or did the wording make a confident model timid?

Audit of the v7 review band, in two parts: a desk analysis of the 358 calls in
`data/eval/distractor_two_axis_2026-08-20.json`, then the ablation that settles it
(`data/eval/distractor_ablation_2026-08-20.json`, 358 calls, **$0.2980**).

Companion to [[evaluations/distractor-judge-two-axis-2026-08-20]], which reported *that*
review volume jumped 0-3% → 22-47% and left the cause open.

---

## Verdict

**The wording hypothesis is refuted, and it fails in the direction nobody expected.**

Strip every directional cue out of the v7 prompt — both the "use 3 whenever you are unsure,
do not guess a 4 or a 2" nudge **and** the "5 is the normal, expected rating" / "4 is the
target" anchors — and the judge hedges **twice as much**, in all three languages:

| | zh | en | ja | total |
|---|---|---|---|---|
| v7 unsure ratings | 24 | 5 | 12 | **41** |
| ablation (no directional cues) | 39 | 22 | 22 | **83** |

So the "use 3 if unsure" instruction was not manufacturing the review queue. Its effect is
more than cancelled by the confidence anchors v7 kept, and the *net* effect of v7's wording is
**anti**-hedging relative to a neutral prompt. What v7 reports is a **floor** on this model's
uncertainty about confusability, not an inflation of it.

Which inverts the original question. The anomaly was never v7's 22-47%. It was **v4's near-zero
review rate**, produced by a prompt that told the model where to land ("THIS IS THE NORMAL,
EXPECTED RATING for a sound distractor — most good distractors should score 5") and got what it
asked for.

Two qualifications, both load-bearing:

1. **Honest is not the same as correct.** The judge is genuinely unsure; whether it is unsure
   about the *right* items still needs an external criterion (§7).
2. **The nudge does not change how much the judge hedges, but it does change what lands
   there** — from "medium" to "genuinely uncertain" (§5). That is TASK-720's actual
   achievement, and it is a different claim from the one the task made.

---

## 1. First, how big is nothing? (run-to-run drift at temperature 0)

v7 was measured twice on byte-identical content, same model, `temperature=0`.

| lang | unsure, run 1 | run 2 | flag %, run 1 | run 2 |
|---|---|---|---|---|
| zh | 23 | 24 | 17.5% | 19.8% |
| en | 9 | 5 | 7.2% | 6.1% |
| ja | 14 | 12 | 9.4% | 6.7% |

**Temperature 0 is not deterministic here.** ja moved 30% between identical runs. Nothing in
this workstream had established that, and it means single-language swings of a few points are
noise. Only effects that replicate across all three languages are readable.

*This is a correction to [[evaluations/distractor-judge-two-axis-2026-08-20]], which reported
per-language rates (zh 47% / en 22% / ja 28%) without error bars. Those figures carry roughly
±3pp of run-to-run noise. The 0-3% → 22-47% jump is far larger than that and survives; the
per-language ordering within it does not.*

## 2. The ablation

A deletion-only edit of the three v7 bodies (`scripts/build_distractor_judge_ablation.py`).
Every removed span is asserted to appear exactly once, and the body is asserted to shrink —
a silent no-op would produce an "ablation" identical to v7 that reports "the wording made no
difference", which is the most expensive possible failure because it looks like a result.

Removed from **both** ends, because stripping only the pushes toward 3 would build the answer
into the instrument:

| removed | axis |
|---|---|
| "THIS IS THE NORMAL, EXPECTED RATING — most sound distractors score 5" | fit 5 |
| "Use this whenever you are unsure … Do not guess a 4 or a 2 instead" | fit 3 |
| "The target is 4" / "THIS IS THE TARGET" | confusability 4 |
| "Use this whenever you are unsure. Do not guess a 4 or a 2 instead" | confusability 3 |
| zh only: a restatement of the use-3 rule qwen had added to the scoring paragraph | both |

| lang | v7 flag % | ablation flag % |
|---|---|---|
| zh | 19.8% | **29.9%** |
| en | 6.1% | **21.7%** |
| ja | 6.7% | **18.1%** |

en quadrupled its unsure count (5 → 22). The effect replicates independently in three
languages and is an order of magnitude outside the drift measured in §1.

**The fit axis tells the same story.** Under v7 it used band 3 exactly **zero** times across
537 distractors in all three languages — the finding the two-axis report leaned on to argue v7
had not induced general timidity. Under ablation it starts using it (zh 1, en 7, ja 2). The fit
axis's total confidence was itself an artefact of the "5 is normal and expected" anchor.

## 3. What the desk analysis had already ruled out

Before the ablation, five checks on the original run. They did not settle the question but they
constrained it, and two of them now read differently in light of §2.

| candidate | verdict |
|---|---|
| The 3s are random noise | **Ruled out.** Coherent population with a specific signature (§4). |
| v7 made the model less decisive in general | **Ruled out then, and for the wrong reason.** The fit axis stayed decisive — but §2 shows that was the anchor, not the axis. |
| The 3s are the borderline items, between "mildly tempting" and "very tempting" | **Ruled out** (§4). |

## 4. The unsure band's signature: low surface overlap

Character-bigram Jaccard against the correct answer — computed from text, so it cannot inherit
any prompt's bias.

| confusability band | n | median similarity |
|---|---|---|
| 1 — inert | 26 | 0.0697 |
| 2 — mildly tempting | 214 | 0.0777 |
| **3 — not confident** | **46** | **0.0389** |
| 4 — strongly tempting | 247 | 0.0959 |
| 5 — also correct | 1 | 0.0000 |

The confident bands order correctly (1 < 2 < 4), though weakly — P(band 4 more similar than
band 2) is 0.566 against 0.500 for no relationship. Band 3 does not sit between 2 and 4; it
sits below all of them, P(3 > 2) = 0.375.

So the unsure band is not "intermediate on temptingness". It selects **the items with the least
surface overlap with the answer** — precisely where the surface gives no signal and the call
has to be made on semantics and world knowledge. Read alongside §2 and §5 this now looks like
the honest reading: the judge is uncertain exactly where a cheap model should be uncertain.

Worth keeping in view for queue design either way: **the review queue is systematically enriched
for items a human is best placed to adjudicate and a small model is worst placed to.**

## 5. The judge's own reasons — and what the nudge actually buys

The harness discarded reason text until this session (see the defect note below), so this could
not be checked for any earlier run. Share of reasons containing a hedging marker
("may/might/unclear/hard to tell", 可能/难以/不好判断, かもしれ/判断できない/迷…):

| arm | lang | band 1 | band 2 | **band 3** | band 4 |
|---|---|---|---|---|---|
| v7 | zh | 0% | 2% | **29%** | 12% |
| v7 | en | 0% | 1% | **20%** | 5% |
| v7 | ja | 0% | 3% | **8%** | 5% |
| abl | zh | 0% | 6% | **13%** | 12% |
| abl | en | 0% | 1% | **5%** | 2% |
| abl | ja | 8% | 3% | **5%** | 6% |

Under v7, band-3 reasons hedge at 3-20× the rate of band 2 — the prose independently
corroborates the number. Under ablation that separation largely collapses: band 3 hedges no
more than band 4 in zh (13% vs 12%) and barely more in ja.

Reading the ablation's band-3 reasons makes the mechanism obvious. Many are not expressions of
doubt at all — they are confident judgments that restate a *neighbouring band's definition*
while assigning 3:

> "moderately tempting due to context, though absent from the text" *(that is band 4)*
> "多くの学習者はすぐ除外する" — most learners would rule it out at once *(that is band 2)*
> "注意深い読者であれば除外できる" — a careful reader could rule it out *(that is band 4)*
> "混淆度中等" — confusability is medium

**Without the push, the model reverts to using 3 as a midpoint on a scale rather than an
abstention.** So TASK-720's wording change did not create the review volume — the volume is
there regardless — but it did convert the band from "medium" into "unsure", which is what the
task set out to do. The claim in the task's outcome note should be that, not the volume.

It also exposes a residual miscalibration now visible for the first time: some band-3 reasons
contradict their own band. Reconciling the rating against the reason text is a concrete,
untried lever, and it is only auditable because the harness now keeps the reasons.

## 6. Two supporting observations, neither strong enough to lean on

**Language asymmetry.** zh hedges most (13.0%), en least (5.1%), and zh's prompt states the
use-3 rule in three places where en and ja state it in two — qwen added a restatement the brief
never asked for. Consistent with dose-response, but three data points, and normalising by
character count across scripts is meaningless when CJK encodes the same content in half the
characters. §2 now makes this mostly moot: the nudge's sign is wrong for it to be the driver.

**A retracted finding.** The first pass flagged a slot-position gradient in the unsure band
(slot 1: 2.2%, slot 2: 13.5%, slot 3: 10.1%) as a rating-process artefact. The control kills
it — the live arm shows the same gradient on its own scale (ratings ≤ 4 by slot: 13.4% → 33.0%
→ 39.1%). It pre-dates v7. It may not be an artefact at all; generators plausibly write their
strongest distractor first.

## 7. What is still not answered

**"Is the judge unsure about the right items?"** No prompt experiment can reach this. It needs
an external criterion:

* TASK-726's adjudicated gold set (blocked on native-speaker labelling), or
* **learner response data** — the real ground truth for "would a learner confuse this", needing
  no human labelling at all. If served questions carry per-option selection counts, the
  confusability axis can be validated against what learners actually picked. Worth checking
  before spending more human time on adjudication. This frame's questions were never served;
  production questions were.

The activation decision is unchanged: v7 stays staged. But the reason has moved. It is no longer
"we cannot tell whether the judge went timid" — that is answered. It is "a 22-47% review rate is
a real workload, and nothing yet says the items in it are the right ones."

---

## A defect found and fixed on the way

**The harness discarded the judge's reasons.** `measure_judge_flag_rate.py` parsed the
per-distractor reason text, used it for nothing and dropped it, so no measurement run in this
workstream could be audited after the fact and no claim about *why* the judge flagged anything
was checkable. §5 is the first time it has been looked at, and it carried the sharpest finding
in this document.

Fixed: results now store `reasons` and `distractors` per call. Also added `--arms "name=@prefix:"`,
which reads an arm's body from `data/eval/<prefix>_<lang>.txt` instead of `prompt_templates` —
an ablation is a throwaway measurement, and writing throwaway rows into the live template table
to measure them is how TASK-723 destroyed two live rows.

## Related pages

- [[evaluations/distractor-judge-two-axis-2026-08-20]] — the run this audits, and the source of
  the per-language figures corrected in §1
- [[evaluations/distractor-judge-language-divergence-2026-08-16]] — TASK-718
- [[evaluations/distractor-gold-frame-2026-08-19]] — the gold set that answers §7
- [[tasklist/distractor-judge-calibration]] — TASK-719, TASK-720, TASK-726
