---
title: Haiku blind age-tier re-grade of all active tests
type: evaluation
status: complete
last_updated: 2026-11-07
open_questions:
  - "OPEN: en-d6-is-openclaw-the-self-hosted-20260317115111 is T6 live, both Haiku readers put it at T4/T5, and it was not in the September gold set. Needs a human read."
---

# Haiku blind age-tier re-grade (2026-11-07)

## Purpose
An independent check of every active comprehension test's age tier (T1–T6,
[[decisions/ADR-003-age-tiers]]) against the tiers jev assigned
([[decisions/ADR-029-jev-tier-assignment]]). It answers two questions: do the live tiers hold up
under a fresh blind read, and could cheap Haiku readers stand in as a tier judge or a gold-set
labeller?

## Method
- **Scope:** all 305 active tests (zh 125, en 121, ja 59).
- **Blind batches:** the native-language rubric (`TIER_DISPLAY_NAMES` / `TIER_CONSTRAINTS`
  verbatim, as in `scripts/build_tier_gold_sample.py`) followed by shuffled numbered passages.
  The readers never saw the live tier, the jev score or the title.
- **Readers:** two independent Haiku subagents per batch (36 in all). Each gave a best tier,
  an optional adjacent `alt`, and a one-line reason. Brief: `data/eval/haiku_tier_regrade_2026-11-07/BRIEF.md`.
- **Consensus:** the tier itself where the two readers agree; otherwise the tier both readers
  accept that is nearest their mean; otherwise their mean rounded half up.
- **Validity check:** Haiku's consensus compared with the September two-reader gold sets
  (`data/eval/jev_recalibration_2026-09-27/*_gold_{A,B}.json`, 179 overlapping tests), using the
  ADR-029 hit metric (a match with either gold reader counts as a hit).

## Results

| | n | Haiku A=B exact / ±1 | ρ(jev score, Haiku mean) | live tier = Haiku consensus | live tier inside a reader's accepted set | bias (live − Haiku) |
|---|---|---|---|---|---|---|
| zh | 125 | 99 / 125 | 0.928 | 94 (75%) | 124 | −0.11 |
| en | 121 | 98 / 121 | 0.964 | 91 (75%) | 119 | +0.00 |
| ja | 59 | 43 / 59 | 0.934 | 35 (59%) | 55 | +0.15 |

Every disagreement is at most one tier, apart from four tests (below). jev's ordering and the
Haiku readers' ordering agree closely in all three languages.

### Where Haiku disagrees with the live tiers, and why that is Haiku's bias
The disagreements cluster in two places:
- **ja T6 → T5:** 13 of 25 live-T6 ja tests.
- **zh T2 → T3:** 13 of 46 live-T2 zh tests.

The September gold readers show the same items going the other way. Of the 24 ja tests the gold
put at T6, Haiku called 14 T5. Of the 23 zh tests the gold put at T2, Haiku called 9 T3. Against
that gold:

| | overlap | live tier hits gold | Haiku consensus hits gold | Haiku bias vs gold |
|---|---|---|---|---|
| en | 60 | 46 | 44 | +0.20 |
| ja | 59 | **57** | 44 | −0.08 (compresses T6 to T5) |
| zh | 60 | **53** | 46 | +0.27 (lifts T2 to T3) |

So the live jev tiers (with the ja/zh calibration tables) agree with the stronger readers
better than Haiku does. Haiku tends to pull the top of the ja scale down and the bottom-middle
of the zh scale up.

### Largest disagreements (≥ 1.5 tiers from the live tier)
| Test | Live | Haiku A / B | Sept gold | Reading |
|---|---|---|---|---|
| ja-d9-making-a-peanut-butter-and-jel… | T6 | 4 / 4 | 6 / 6 | Gold sides with live; Haiku keyed on the everyday topic |
| ja-d1-the-evolution-of-the-epistolar… | T2 | 4 / 3 | 2 / 2 | Gold sides with live |
| ja-d6-the-theoretical-underpinnings… | T6 | 4 / 5 | 5 / 5 | Gold says T5, so live is one high (within ADR-029's known ja error) |
| en-d6-is-openclaw-the-self-hosted… | T6 | 4 / 5 | — | Unchecked, needs a human read |

## Conclusions
1. **No re-tier is warranted.** The live tiers hold up: 75% exact agreement in zh and en,
   98% within one tier overall, and where Haiku disagrees systematically, the stronger gold
   readers side with the live tier.
2. **Haiku is not a good enough tier judge or gold labeller** to replace jev or the
   two-reader gold. Its ordering is good (ρ ≈ 0.93–0.96), but its scale is biased per language
   in the same way jev's raw scale was before calibration.
3. **It is useful as a cheap disagreement screen.** The four items above are the review list.
   The one with no gold label (en "openclaw") is the only open action.

## Caveats
Haiku and the September gold are both model readers, not humans. T5 is still thin in every
language. The ja sample is the whole library (59 tests), so its rates are noisy.

## Files
`data/eval/haiku_tier_regrade_2026-11-07/`: `readers/<batch>_{A,B}.json` (raw grades),
`manifest.json` (batch item → test id), `results.json` (per-test live tier, jev score, both
readers, consensus, reasons), `export.py` / `analyze.py` (batch export and metrics; the paths
point at the session scratchpad, so edit `OUT` / `D` to re-run).

## Related Pages
- [[decisions/ADR-029-jev-tier-assignment]]
- [[decisions/ADR-003-age-tiers]]
- [[features/test-tier-assignment]]
- [[evaluations/jev-tier-calibration-2026-09-27]]
