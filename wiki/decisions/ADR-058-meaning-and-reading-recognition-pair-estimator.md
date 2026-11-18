---
title: "ADR-058: For Chinese and Japanese the placement reports meaning-and-reading recognition with a pair estimator, pools only same-instrument answers, and shows no exam-level estimate in v1"
status: proposed
date: 2026-11-18
---

# ADR-058: For Chinese and Japanese the placement reports meaning-and-reading recognition with a pair estimator, pools only same-instrument answers, and shows no exam-level estimate in v1

## Context
ADR-051 estimates "words you recognise" from the check's definition-mode answers over the check's own pool.
It uses a per-band guess-corrected share, Jeffreys variance with a finite-population factor, and gates of
10/20/30 answers per band. It has no notion of reading.

The owner asked that the zh/ja placement tell real knowledge from partial knowledge. Kanji and hanzi
meaning and reading are separable: Japanese kanji tests report them as subtests, and Chinese-L1 readers
understand Japanese text without the readings. Products that care (WaniKani, Skritter, Pleco) score them
separately ([[evaluations/vocab-placement-research-2026-11-18]]).

Simulation results (ESTIMATE):
- Meaning-only results over-state meaning-and-reading recognition by +27–30% of the pool for Japanese-L1
  learners of Chinese.
- A model that fitted "meaning and reading" as its own curve over-stated it by up to +8.7%.

Two independent reviews of the first design found the following:
- **The draft's estimated exam-level range could not work.** Its 95% lower bound was 0 for every
  simulated learner. Its point rule placed learners whose true level is HSK 2–5 within one level only
  3–41% of the time, usually too low. The level claim rested on the third of each level that the pool
  holds, on the exchangeability assumption ADR-054 rejected (ESTIMATE, MEASURED).
- **The draft pooled two different instruments.** Check meaning items show the reading and keep the
  cross-CJK headword; placement items do neither. ADR-051 itself rejects pooling instruments of
  different difficulty.
- **The draft's display guard pointed the wrong way.**
- **Its copy over-claimed.** It said "really know", attributed the meaning-minus-reading gap to
  characters, and claimed guessing is neutral.

## Decision
1. **What is claimed.** For zh and ja the headline is **meaning-and-reading recognition**: the rank-1
   meaning and the reading are both recognised in four-option items. For zh the reading means the pinyin
   syllables; tones are not tested in scored items (ADR-057). For ja kana-only words and all en words, it
   is meaning recognition. Copy says "recognised", never "know" on its own.
2. **Pair estimator.** It uses placement pairs only (latest per lemma, 180 days, one D, one instrument).
   Per band, `K_mr = pc/n − (1/3)·prw/n`:
   - `pc` = meaning right and reading right (or meaning right on a reading-exempt word);
   - `prw` = meaning right and reading answered wrong (or meaning answered wrong on an exempt word);
   - IDK answers and missed meanings count only in n;
   - probes never count.

   Variance, interval, rounding and labels are the same as ADR-051. Under the know-or-guess model it is
   unbiased for every skip propensity.
3. **Gap.** "Meaning recognised, reading not" is estimated on the same placement's pair sample, with its
   own interval from the per-word score x ∈ {4/3, 1, −1/3, 0} (tech §5.1). It is shown only when its
   lower bound is clearly above 0. Its cause is not stated.
4. **Instruments.** Every response stores `instrument`. Estimates pool only answers of one instrument
   and one definition language:
   - the result's first range uses this placement's items only;
   - the "combined" line uses all scored answers of the same instrument and D within 180 days.

   Legacy check answers (reading shown, prefix kept) are not pooled with placement answers. They pool
   again only for check answers recorded after the check adopts the bare instrument (TASK-1091).
5. **Report D and instrument rule.** If the window holds an eligible placement, the report uses that
   latest placement's D and the `meaning_bare_v1` instrument. Otherwise ADR-051 rule 1 is unchanged.
6. **Eligibility amendment to ADR-051 rule 1.** An estimate is also eligible:
   - with ≥ 2 answers in every band when the sample contains a placement that stopped by precision, cap,
     time or exhaustion;
   - for a placement's own result after the learner stopped or abandoned it, once the warm-up is complete
     and ≥ 20 scored items were answered ("You ended early, so the range is wider").

   Labels keep ADR-051's per-band minima, so a placement alone is usually "Rough".
7. **Display.**
   - Meaning-and-reading first, then the gap.
   - Because T_m ≥ T_mr, `lo_m := max(lo_m, lo_mr)` and `hi_mr := min(hi_mr, hi_m)`.
   - The result leads with this test's word groups ("guesses included").
   - The method note says the m+r range "may be a little high if readings can be partly guessed" until
     validation V9 measures it. If V9 finds an implied guess rate above 0.30 among unknown readings,
     r = 1/3 for readings is replaced through a revision of this ADR.
8. **No exam-level estimate in v1.** ADR-054's v1 stance (measured coverage buckets only) is unchanged.
   Any later level output needs its own ADR that explicitly revises ADR-054's rationale. That output must:
   - name the subset it measures;
   - pass per-true-level gates on the copy learners would see;
   - be re-validated after the zh pool refresh.
9. One SQL function, `knowledge_calibration_inputs`, supplies the inputs to both the placement result and
   the report. The estimator stays in `services/vocabulary/knowledge_estimate.py`.

## Consequences
- **Easier:**
  - the placement's combined line and My vocabulary agree on the day the placement is taken;
  - cognate learners see a "meaning, not the reading" gap with an honest interval;
  - no new statistics beyond ADR-051's formula applied to a second outcome and a difference;
  - nothing on the page rests on an untestable level mapping.
- **Harder:**
  - two figures to explain;
  - learners with many legacy check answers see the report switch to the placement's instrument (usually
    "Rough" instead of "Medium") until TASK-1091 converts the check;
  - the m+r estimate exists only where placements exist;
  - the goal path gets no level placement in v1.
- **Constrained:**
  - if readings can be partly guessed, m+r is biased up by about +2.4..+4.0% of the pool for cognate
    learners (ESTIMATE), measured by V9;
  - IDK hiding partial knowledge makes both ranges lower-side, measured by forced-guess probes (V8);
  - learners who use IDK more score a little lower than guessers with the same knowledge.

## Alternatives Considered
- **Meaning as the headline, reading as a second line:** hides the owner's distinction for cognate
  learners. Kept as PQ1's alternative.
- **An independent "meaning and reading" curve:** can exceed the meaning curve; over-stated by up to +8.7%.
- **Readings-mode answers from separate sessions:** not conditional on the meaning, so they cannot form
  pairs.
- **Pooling legacy check answers with placement answers:** different instruments. The result would move
  with the learner's history, and the display guard would bind for the wrong reason.
- **The draft's estimated level range** (§2.8a share over frame words, 80% threshold, 95% bounds): lower
  bound always 0; point rule 3–41% within one level for true HSK 2–5; rests on a third of each level.
  Rejected for v1.
- **The draft's display guard** (cap the m+r ends at the meaning ends): bound in 25–37% of placement-only
  results and widened the headline by 3.2–3.8% of the pool.
- **Separate tone dimension from one four-option item:** not measurable; tone is measured by 2-option
  probes instead.

## Related Pages
- [[features/vocab-placement]] · [[features/vocab-placement.tech]] §4, §5, §8, §9
- [[decisions/ADR-051-vocabulary-size-from-calibration-frame]] — the estimator extended here
- [[decisions/ADR-053-daily-knowledge-snapshots]] — retake comparison rule
- [[decisions/ADR-054-exam-word-lists-in-storage]] — unchanged v1 level stance
- [[decisions/ADR-057-adaptive-placement-with-conditional-reading]] · [[decisions/ADR-059-placement-evidence-kind]]
- [[features/knowledge-report]] · [[evaluations/vocab-placement-research-2026-11-18]]
