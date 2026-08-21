---
title: Distractor gold set — frame construction and pre-rating
type: evaluation
status: in-progress
last_updated: 2026-08-19
open_questions:
  - "OPEN: adjudication is unscheduled. The frame is inert until native zh/en/ja labellers return the sheets; no judge can be scored before then."
  - "OPEN: does the labelling guide reach κ ≥ 0.6 on `confusable`? If not the definitions are the defect and the overlap slice is relabelled before any arm is scored."
---

# Distractor gold set — frame construction and pre-rating

TASK-726, machine half. Built the sample frame, pre-rated it with the two judge models whose
disagreement created the need for a gold set, and shipped the scoring harness. **No labels
exist yet** — the frame is a ruler with no markings on it until native speakers adjudicate.

Related: [[tasklist/distractor-judge-calibration.tasks]] TASK-726,
[[evaluations/distractor-judge-language-divergence-2026-08-16]],
[[evaluations/entailment-likert-v3-rollout-2026-08-19]].

---

## 1. What was built

| Artefact | What it is |
|---|---|
| `data/eval/distractor_gold_frame_2026-08.json` | 573 items, pre-rated, weighted, empty `labels` |
| `data/eval/distractor_gold_frame_2026-08_{zh,en,ja}_primary.csv` | primary labeller sheets |
| `data/eval/distractor_gold_frame_2026-08_{zh,en,ja}_overlap.csv` | 60-item double-labelling slices, for κ |
| `data/eval/distractor_gold_labelling_guide.md` | the label definitions κ will test |
| `scripts/distractor_gold.py` | weighting, κ, AUC, band metrics — all unit-tested |
| `scripts/build_distractor_gold_frame.py` | sample → pre-rate → select → weight → emit |
| `scripts/merge_distractor_gold.py` | labelled sheets → versioned gold file, with the κ gate |
| `scripts/measure_judge_flag_rate.py --gold` | scores an arm against the gold file, reweighted |

**Frame.** 573 items (zh 213, en 180, ja 180) = 191 questions × 3 distractors, exceeding the
task's ≥540 / ≥180-per-language floor. Drawn from `data/eval/task721_before.json` — 179 questions
generated 2026-08-19 by `generate_question_sample.py --templates live` — plus a 12-question zh
top-up generated the same way, because the original run lost one zh cell to a generation failure
and zh would otherwise have landed at 177 items. **The TASK-721 rewrite rows are staged and not
active**, so "live" on 2026-08-19 is still live; a fresh generation run would have cost ~$0.57
and ~40 minutes to reproduce the same content.

`generate_question_sample.py` gained `--exclude-passages` so the top-up drew two passages the
first run had not used. Without it, a second run at a different `--passages` re-picks overlapping
passages and the merged sample carries twelve questions off one passage instead of six.

---

## 2. The disjointness is not an artefact of the frozen sample

TASK-718's finding — that `qwen/qwen3.6-flash` and the gemini flash-lite line reject almost
disjoint sets — was measured on the frozen 150-question sample. It reproduces on **fresh
live-stack content**, harder:

| | items | qwen rejects | gemini rejects | both | Jaccard |
|---|---|---|---|---|---|
| zh | 213 | 35 | 2 | 2 | **0.06** |
| en | 180 | 11 | 0 | 0 | **0.00** |
| ja | 180 | 10 | 1 | 1 | **0.10** |
| all | 573 | 56 (9.8%) | 3 (0.5%) | 3 | 0.05 |

Both arms ran the **live judge prompt** for their language (zh v6, en/ja v4) and differ only in
model, so this is a pure model effect. The English column is the sharpest statement available:
across 180 items the two models agree on **zero** rejects.

The band cross-tab says why no rate could ever have settled it:

```
qwen \ gemini      1      2      3      4      5   none
    1              0      0      0      1      0      0
    2              0      3      1     16     35      0
    3              0      0      0      0      2      0
    4              0      0      1     59    114      2
    5              0      0      2     76    260      1
```

Of the 55 distractors qwen puts in band 2 — *"off-topic, different subject, reject"* — gemini
rates **35 of them 5**, its top band, and 16 more a 4. The models are not mis-scaled versions of
each other; on the disputed population they are opposites. That is the whole case for
adjudicating by hand, restated on current content.

61 items (10.6%) are flagged `disagreement`: 58 verdict disagreements and 3 where gemini returned
no rating at all. Disagreements skew to `vocabulary_context` (19/96) — the same type that has
absorbed every anomaly in this workstream since TASK-717.

---

## 3. Uniform-by-type sampling has been quietly mis-weighting every rate

The frame is uniform by question type (10 questions per type per language) because a per-type
estimate needs a usable n in every cell. Production is not uniform, and not mildly so:

| stratum | frame share | production share | weight |
|---|---|---|---|
| zh/vocabulary_context | 16.9% | 29.5% | 1.75 |
| zh/literal_detail | 15.5% | 24.7% | 1.59 |
| zh/supporting_detail | 16.9% | 5.5% | **0.33** |
| ja/supporting_detail | 16.7% | 5.2% | **0.31** |
| ja/vocabulary_context | 16.7% | 30.0% | 1.80 |

A `supporting_detail` item is carrying 5.4× the weight in a uniform sample that it carries in the
product. Because rejects concentrate in `vocabulary_context`, correcting this moves the numbers:

| arm | raw reject rate | reweighted | ratio |
|---|---|---|---|
| gemini (live judge), all | 0.52% | **0.92%** | 1.77× |
| gemini, zh | 0.94% | 1.64% | 1.75× |
| qwen, all | 9.77% | 10.71% | 1.10× |

**TASK-721's §1 baseline of "0.6% on fresh output" is therefore an under-estimate of the
production reject rate by roughly 1.8×.** It is not wrong about the direction — the 30% / 4% /
12% figures it superseded are still gone — but any acceptance criterion written against 0.6%
should be written against ~0.9%. The correction is now automatic: `frame_weight` is stored per
item and `measure_judge_flag_rate.py --gold` applies it to every published number.

---

## 4. Design decisions worth keeping

1. **The labeller sheets deliberately omit the pre-ratings.** They are in the JSON for the
   harness. Showing an adjudicator what two models thought would anchor them onto exactly the
   judgment the gold set exists to check independently, and a gold set anchored to the models it
   arbitrates is worth nothing.
2. **The whole frame is adjudicated, so enrichment selects nothing.** TASK-726 §1 and §2 are
   internally inconsistent — §1 sizes the frame at 540 and §2 force-includes disagreements out of
   it, which only bites if the frame is larger than the adjudication budget. Adjudicating all 573
   is the cheaper resolution in human time *and* removes the enrichment bias entirely. The
   machinery is built and tested regardless (`--adjudicate N`), because a later top-up may want
   it, and `selection_prob` is stored per item so the correction stays auditable.
3. **Two axes, never collapsed.** `topical_distance` and `confusable` are separate columns
   everywhere. They combine only in `gold_reject`, at the single point a verdict is needed, and
   `confusable = borderline` returns *neither* side rather than being coerced — that population
   is what TASK-720 will redesign the review band around, and coercing it would erase it.
4. **The κ gate is a gate.** `merge_distractor_gold.py` prints a `[BLOCK]` line when κ on
   `confusable` lands below 0.60 and names the remedy: the label definitions are the defect, so
   the guide is revised and the slice relabelled before any judge is scored.
5. **`live` as a prompt version.** The three languages are not on the same judge version — zh is
   v6, en/ja v4 — so no integer can express "the prompt production is running" across a
   three-language arm. `--arms "name=live:model"` now resolves per language to the active row.

---

## 5. Verification

* `tests/test_distractor_gold_frame.py` — 37 tests over the weighting, κ, AUC and selection
  logic, with no DB and no LLM. Two pin the numbers that matter most: a 50/50 enriched selection
  reproduces the frame's true 10% rate after weighting (raw reads 33%), and a uniform frame
  post-stratifies to a 90/10 production mix at weights 1.8 / 0.2.
* Suite: **1843 passed, 3 skipped** (1806 before).
* End-to-end plumbing smoked with *synthetic* labels in the scratchpad — merge, κ gate, and
  `--gold` scoring all run clean, and AUC comes out 0.51 on random labels, confirming the harness
  manufactures no signal of its own. The synthetic file was never written to `data/eval/`.

**Spend: $0.7266** — 382 pre-rating calls (`flag_rate_qwen` $0.6062 at $0.00317/call,
`flag_rate_gemini` $0.1203 at $0.00063/call), plus ~$0.05 for the 12-question zh top-up. All
under `pipeline='diag'`. TASK-726's technical note estimated ~$0.10 for the pre-rating; that
assumed both arms on flash-lite, and qwen is 5× the price.

---

## 6. What is blocked

**Adjudication.** 573 items across three languages, plus a 180-item overlap for κ. Native
speakers only; zh and ja must not be labelled from translation. This is human time, not spend,
and it is the entire remaining cost of TASK-726.

Until it lands, four of the task's seven acceptance criteria cannot be met — the κ figure, the
native-speaker requirement, the harness's gold report, and the re-scoring that settles which of
TASK-718's two models was right. That last one is now free rather than cheap: the frame was
pre-rated with exactly that model pair, so
`measure_judge_flag_rate.py --gold <file>` scores both stored arms against the labels without a
single new call.

TASK-719 and TASK-720 remain blocked behind it, exactly as before — but the blocker is now one
named file waiting on one named activity, rather than "a gold set" with no owner.
