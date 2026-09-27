---
title: "jev tier calibration — blind gold sets, 2026-09-27"
type: evaluation
status: complete
last_updated: 2026-09-27
open_questions:
  - "The gold labels are two model readers per language, not humans; do human labels agree, especially at T5 (and T3 in en)?"
  - "Would 150–200 items per language tighten the ja and zh tables enough to matter?"
---

# jev tier calibration — blind gold sets, 2026-09-27

Decision this feeds: [[decisions/ADR-029-jev-tier-assignment]]. Feature:
[[features/test-tier-assignment.tech]]. Predecessor:
[[evaluations/jev-judge-feasibility-2026-09-26]] §3.4.

## Why

After all 305 active tests were re-tiered with jev (round-half-up), a 15-per-language spot check
(weighted to the largest tier moves and lowest confidence) found ja one tier high, zh
compressed toward T3 and en mildly high. That sample was deliberately extreme, so it could not
say how large the errors were overall or whether a fix helped.

## Method

- **Gold sets.** ja: all 59 active tests. zh and en: 60 tests each, spread evenly across the
  jev score range. Each set was labelled **blind** (rubric in the passage's language; no
  labels, no jev output) by two independent LLM subagents. Data:
  `data/eval/jev_recalibration_2026-09-27/{lang}_blind.md`, `_gold_A.json`, `_gold_B.json`.
- **Hit** = the predicted tier equals either reader's tier. Reader agreement: exact 41/59 (ja),
  52/60 (zh), 54/60 (en); within one tier 100% in all three.
- **Models compared** (`scripts/fit_tier_thresholds.py`): round-half-up; the best single
  uniform offset; five fitted cut points (coordinate ascent, minimum band 0.1). Generalisation
  by 5-fold cross-validation, six repeats.

## Results

| | round-half-up | uniform offset (CV) | fitted cuts (CV) | applied | original pre-jev labels |
|---|---|---|---|---|---|
| ja | 38/59 | 42.0 | **52.5** (57 in-sample, LOO 52) | fitted | 48/59 |
| zh | 44/60 | **52.0** | 51.5 (55 in-sample, LOO 52) | uniform −0.25 | 33/60 |
| en | 46/60 | 44.2 | 47.0 | **none** | 42/60 |

- **ja.** jev's ordering is monotone with the readers' tiers, but the tiers sit at expected
  tier ≈ 1.3 / 2.4–3.6 / 4.0–4.2 / 4.3–5.2 / 5.5 / 5.9. Error by gold tier: T2–T3 +1.0,
  T4 +0.6, T6 0.0 — not constant, so an offset fails. Adding "judge by sentence structure, not
  jargon" to the prompt moved bias only from +0.41 to +0.26 with lower rank correlation, so the
  prompt was left alone. The original labels used only T1/T4/T6.
- **zh.** Error by gold tier: T2 +0.44, T3 +0.29, T6 ≈ 0. The one-parameter shift and the five-cut
  fit tie under cross-validation, so the shift was kept.
- **en.** Nothing beat the default beyond noise (+1 for the fit, −2 for an offset); jev already
  agrees with a reader on 46/60. The spot check's "mild upward bias" was an artefact of the
  sample.
- **Live now vs a blind reader:** ja 57/59, zh 53/60, en 46/60 (first jev pass 38 / 44 / 46;
  original labels 48 / 33 / 42). ja and zh are on the data the tables were fitted to.

## Cost

Calibration calls: ja 59 × 2 prompt variants ≈ $0.0056. Tier classification: ≈ $0.000044 per
passage; a full re-tier of 305 tests ≈ $0.013 in 26 s. Readers: 6 subagent runs.

## Caveats

- Model readers, not humans. A 60-item sample per language is small.
- T5 (ja: two items on which both readers agree; zh: 1–2) and T3 (en: 1–2) are barely
  represented, so the cut points around those tiers are the least certain.
- The zh and en samples are spread over the score range, not random: the hit rates describe
  that sample, not the library's tier mix.
- ja passages are short (mean 203 characters).

## Reproducing

`scripts/build_tier_gold_sample.py --lang zh --n 60`, two blind readers, then
`scripts/fit_tier_thresholds.py --lang zh`. Regression fixtures:
`tests/fixtures/{ja,zh}_tier_calibration_gold.json`.

## Related Pages
- [[decisions/ADR-029-jev-tier-assignment]]
- [[features/test-tier-assignment.tech]]
- [[evaluations/jev-judge-feasibility-2026-09-26]]
