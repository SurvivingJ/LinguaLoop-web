---
title: "ADR-051: Estimate vocabulary size from the calibration sample, over the check's own word pool"
status: proposed
date: 2026-11-17
---

# ADR-051: Estimate vocabulary size from the calibration sample, over the check's own word pool

## Context
The Knowledge Report ([[features/knowledge-report]]) must tell a learner roughly how many words
they know, with an honest range, and it is meant to be a reason to pay for Pro, so the number has
to survive scrutiny. Measured on 2026-11-17 ([[features/knowledge-report.tech]] §0, Appendix B):
- Per-word `p_known` is not calibrated: on the 203 attempts with a stored prediction it does worse
  than a per-user constant (Brier 0.205 vs 0.192; 0.309 vs 0.158; AUC 0.62 / 0.46). Rows exist only
  for words the app chose to show, one-event rows are mostly the frequency prior, and reading tests
  and inference move `p_known` without a word-level check. Summing or extrapolating rows reports the
  model's assumptions (971 → 2,553 words for the same learner as the assumed ability moves 6.0 → 4.0).
- The vocabulary check (Calibration, definition mode) is a random within-band sample — but of
  **`calibration_anchor_pool`** for one (word language, definition language), not of the dictionary.
  For ja/en the pool covers 3,175 of 3,422 banded lemmas; for zh/en 3,623 of 12,790 (band 4: 691 of
  4,881). zh pool lemmas are test vocabulary (98% appear in a transcript vs 22% of non-pool lemmas of
  the same frequency), so the pool's known share cannot be applied to the rest. The zh pool is stale
  after the October–November 2026 dictionary seeding.
- The check samples senses; in the en/en pool 38% of items test a meaning with `sense_rank > 1`.
- Anchors repeat across sessions and a wrong answer or skip reveals the key.
- The draft estimator's plug-in variance gave zero-width "good" intervals at the edges, its per-band
  clamp biased beginners upward, a relative-width gate locked beginners out for good, and its
  "naive" alternative skip model assumed below-chance accuracy on skipped words (statistician review
  S1–S4, S9, S10).

## Decision
1. **Instrument.** The headline uses definition-mode check answers only: anchors whose sense has
   `sense_rank = 1`; one definition language per estimate (the one with the most answers in the
   window); the latest answer per anchor lemma; a 180-day window.
2. **Denominator = the check's own word pool (the frame).** `N_b` = lemmas whose rank-1 sense is in
   `calibration_anchor_pool` for (L, D) with `has_embedding` and not blocklisted, per Zipf band
   (`knowledge_frame_bands()`, cached 1 h). Copy: "In the vocabulary check you recognised about X–Y
   of the N {language} words it draws from"; "Words LinguaDojo has not yet put into the check are not
   counted."
3. **Estimator.** Per band `K_b = c_b/n_b − (1/3)·w_b/n_b` (a skip means not known; an attempted unknown
   word is a 1-in-4 guess), **no clamp**; variance from Jeffreys pseudo-counts with a
   finite-population factor; `T = Σ N_b·K_b`, `SD = sqrt(Σ N_b²·Var_b)`; `lo = max(0, T − 1.96 SD)`,
   `hi = min(N, max(T, 0) + 1.96 SD)`. No BKT count ever moves the interval; if the "rated known"
   count exceeds `hi`, a disagreement line asks for a re-check.
4. **Gates and labels.** No estimate below 10 distinct lemmas in any band (E1), or when only answers
   older than the window would pass (E1c, "check out of date"). If `lo = 0`: "Fewer than {hi}"
   (Rough). Otherwise labels by `rel' = 1.96·SD / max(T, 0.10·N)`: Good ≤ 0.15 with every band ≥ 30;
   Medium ≤ 0.30 with every band ≥ 20; Rough ≤ 0.50; above that "Fewer than {hi}" when `hi ≤ N/2`,
   else "too uncertain" with a stated number of further answers per band. Ends are rounded outward to
   two significant figures; the point is a tick, never text.
5. **No alternative skip model in code.** The "naive" correction is not implemented. The copy says
   that skips count as not known and that the true figure is higher if skipped words were partly
   known. Whether skips hide partial knowledge is measured by forced-choice probe items (TASK-1061,
   owner-gated) before the range is used in marketing.
6. The estimator is pure Python (`services/vocabulary/knowledge_estimate.py`) fed by SQL counts and
   reused by the nightly snapshot job.

## Consequences
- Easier: one testable method with a stated denominator. For de6fd05b/ja: **850–1,400 of 3,175,
  Medium**, from 172 answers (ESTIMATE). In simulation the displayed interval or bound covers the true
  count in ≥ 93.7% of runs at 10, 20 and 30 answers per band, with no zero-width output and no
  dead-end state for beginners (ESTIMATE).
- Harder: Chinese figures are "of the 3,623 words the check draws from" until the zh pool is refreshed
  (≈ 5–7 MB of database rows, after the database size gate of OQ13 — OQ29; the exam lists no longer
  share that gate, ADR-054); a refresh changes the denominator, which the growth card
  announces (ADR-053). English needs more answers because only rank-1 items count (or a selector
  change — TASK-1062).
- Constrained: the claim is recognition of the pool's words in a four-option test; the skip rule makes
  it a lower-side figure if "I don't know" hides partial knowledge. Calibration's own ability fit
  scores a skip as a wrong answer, so the two outputs differ until OQ33 is answered; the calibration
  result screen shows the report's range beside its own figure (TASK-1042).

## Alternatives Considered
- **Σ p_known (raw or decayed), rows above a threshold, band × mean p of rows, hybrid prior:** report
  the model's selection and assumptions, not knowledge.
- **Whole-dictionary denominator:** the zh extrapolation rests on words the check never samples and
  that differ from those it does.
- **Pooling definition languages:** pools different frames and instruments of different difficulty.
- **Plug-in (Wald) variance and per-band clamping:** zero-width intervals and +543 words of bias for a
  zh beginner (statistician review S2).
- **"Naive" skip model** (skip counted as a wrong guess): implies below-chance accuracy on skipped
  items; it is not a coherent alternative.
- **Bootstrap interval:** equivalent in the middle of the range but non-deterministic; kept only as a
  validation method.
- **A 20-answers-per-band floor:** hid ranges that were already Medium-precision after one sitting and
  would lock 21-day trialists out (product review P8).
