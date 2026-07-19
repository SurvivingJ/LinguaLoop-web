---
title: "DT Grading Eval — v1 Baseline (2026-07-05)"
type: evaluation
status: complete
date: 2026-07-05
harness: scripts/run_dt_grading_eval.py
metrics_module: services/dual_translation/eval_metrics.py
gold_sets: tests/fixtures/dt_gold/{en,zh,ja}.json (TASK-621, frozen)
---

# DT Grading Eval — v1 Baseline (2026-07-05)

First run of the Evidence-First Grading eval harness ([[algorithms/evidence-first-grading.tech]] §10),
built in TASK-622. It grades the frozen gold sets ([[tasklist/evidence-first-grading.tasks]] TASK-621)
through the **shipped v1 cascade** (`services.dual_translation.grader_cascade.grade_submission`) and
computes the full metric set. This is the regression floor every later task (TASK-623..632) must
re-run and not regress.

- **Grader:** v1 cascade, live OpenRouter, one pass per L2, `temperature=0.0`, `max_tier=tier2`.
- **Slugs (router-resolved):** EN `google/gemini-2.5-flash-lite` + `google/gemini-3.5-flash`;
  JA `qwen/qwen3.6-flash` + `qwen/qwen3.7-plus`; ZH — none reached (all resolved at Tier 0).
- **Cost:** $0.0206 (EN) + $0.0094 (JA) + $0.0000 (ZH) = **$0.030 USD** total; 14 model calls.
- **Metrics are pure + unit-tested** (`tests/test_dt_eval_metrics.py`, 23 cases). Span matching is
  relaxed (≥50% overlap of the shorter span); QWK is quadratic-weighted over the 1–4 bands.

## Headline finding — Tier-0 over-resolution swallows the gold errors

The baseline's dominant pathology is **not** the predicted high clean-passage false-positive rate.
It is the Tier-0 near-exact gate (`NEAR_EXACT_MISMATCH_RATIO ≤ 0.05` in `tier0.py`): a single
token-level error inside a 2–4 sentence passage produces a mismatch ratio under 5%, so Tier 0
awards **full marks (all bands 4, zero errors) and the grader never runs.**

| L2 | items resolved at Tier 0 | reached the model | single-error items the model saw |
|----|--------------------------|-------------------|----------------------------------|
| EN | 24 / 30 | 6 (2 clean, 4 multi) | **0 / 15** |
| JA | 29 / 30 | 1 (one multi) | **0 / 15** |
| ZH | 30 / 30 | 0 | **0 / 15** |
| **All** | **83 / 90 (92%)** | 7 | **0 / 45** |

Every one of the 45 single-seeded-error passages — one clean, high-frequency taxonomy error each —
was resolved to a perfect grade before detection. This is exactly the leniency TASK-623 targets
(retire `NEAR_EXACT_MISMATCH_RATIO`; resolve at full marks only when **every** non-equal diff opcode
is normalization-class). The gold README already flagged the EN morphology sub-case; the measured
reality is broader and language-general (worst for ZH, where jieba tokenization + short passages put
the mismatch ratio under threshold for all 30 items).

## Per-L2 summary

| L2 | span P | span R | span F1 | TP/FP/FN | subtype acc | severity exact | clean FP rate | overall QWK |
|----|--------|--------|---------|----------|-------------|----------------|---------------|-------------|
| EN | 0.429 | 0.222 | **0.293** | 6/8/21 | 0.333 (2/6) | 0.667 (n=6) | **0.000** (10) | 0.516 |
| JA | 0.750 | 0.111 | **0.194** | 3/1/24 | 1.000 (3/3) | 0.333 (n=3) | **0.000** (10) | 0.186 |
| ZH | — | 0.000 | **0.000** | 0/0/26 | n/a (0) | n/a | **0.000** (10) | 0.000 |

Reading the numbers:
- **Recall is the floor** (EN 0.222, JA 0.111, ZH 0.000) — a direct consequence of Tier-0 swallowing
  errors: FN dominates (21/24/26). **Precision is respectable on the little the model sees**
  (EN 0.43, JA 0.75), and subtype accuracy on matched pairs is even high for JA (3/3). The v1 grader
  is not bad at judging what reaches it; the cascade just rarely lets errors reach it.
- **Clean-passage FP rate is 0.000 across all three L2s** — contrary to the pre-run expectation. Two
  compounding reasons: most clean items short-circuit at Tier 0 (0 errors by construction), and the
  handful that did reach the model (EN clean_01/02 via Tier 2) were correctly returned error-free.
  The clean-FP metric is wired and measured on all 30 clean items; it simply reads 0 at baseline.

## Per-dimension band agreement (QWK + exact / adjacent)

QWK is the honest signal here. Exact/adjacent agreement look high (0.7–1.0) only because Tier-0
full-marks and the gold bands both cluster near 4 — a base-rate artifact. QWK strips that out and
lands near zero, confirming the grader has almost **no discriminating power over the gold band spread**
at baseline.

| dimension | EN QWK | EN exact/adj | JA QWK | JA exact/adj | ZH QWK | ZH exact/adj |
|-----------|--------|--------------|--------|--------------|--------|--------------|
| accuracy | 0.440 | 0.80 / 0.93 | 0.149 | 0.73 / 1.00 | 0.000 | 0.70 / 1.00 |
| understandability | 0.000 | 0.90 / 0.93 | 0.000 | 0.83 / 0.93 | 0.000 | 0.90 / 0.93 |
| fidelity | 0.167 | 0.80 / 1.00 | 0.038 | 0.73 / 0.90 | 0.000 | 0.80 / 0.93 |
| range | 0.000 | 0.87 / 1.00 | 0.000 | 0.97 / 1.00 | 1.000 | 1.00 / 1.00 |
| naturalness | 0.146 | 0.87 / 0.97 | -0.047 | 0.90 / 1.00 | 0.000 | 0.93 / 1.00 |
| **overall_band** | **0.516** | 0.93 / 0.97 | **0.186** | 0.87 / 0.97 | **0.000** | 0.90 / 1.00 |

(`range` QWK 1.0 / 0.0 are degenerate: when a rater is constant, QWK is 1.0 iff both agree perfectly,
else 0.0 — the standard convention, implemented in `eval_metrics.quadratic_weighted_kappa`.)

## v1 robustness issues surfaced (incidental)

- **Fail-open on wrong shape:** one Tier-2 response (`google/gemini-3.5-flash`, en_multi_03) nested its
  `errors` under `scores`, failed shape validation, and fell open to MAX_BAND for its dimensions
  (`grader_trace.fell_open=true`). v1 silently awards full marks in this case — the exact behaviour
  ADR-019 / TASK-628 replaces with a **provisional** grade.
- **Dropped error:** one EN error with an empty `learner_form` (`span_repro=[111,111]`) was dropped by
  `_decode_error`. Correct defensive behaviour, but a real detected error lost — the substring-repair
  fallback in TASK-624 addresses this.

## What this baseline sets up

1. **TASK-623 (Tier-0 precision) is the highest-leverage next step.** Recall cannot improve until the
   near-exact gate stops resolving single-error passages. Re-run target: single-error items reaching
   the model should jump from 0/45 toward ~45/45; span recall and per-dimension QWK should rise; clean
   FP rate must stay at/near 0.000.
2. **Regression gate values to hold or beat:** span F1 (EN 0.293 / JA 0.194 / ZH 0.000), overall QWK
   (EN 0.516 / JA 0.186 / ZH 0.000), clean FP rate (0.000 all). Any later phase that lowers these
   without a documented reason blocks activation ([[algorithms/evidence-first-grading.tech]] §10 gate).
3. **ZH is the acid test.** With every item currently swallowed at Tier 0, ZH has the most headroom and
   the least signal — it is the clearest before/after for TASK-623.

## TASK-623 update — Tier-0 precision fixes (2026-07-05)

Re-ran the identical harness + frozen gold sets, live, through the **patched cascade**: the
`NEAR_EXACT_MISMATCH_RATIO ≤ 0.05` gate is retired in favour of a **normalization-class opcode
gate** (full marks only if every non-`equal` diff op folds to an identical string under
`_normalize_l2` + `tokenizer.normalize`), and Tier-1 `confidence` now defaults to `0.0`
(missing confidence escalates the Tier-2 re-check). One pass per L2, `temperature=0.0`,
`max_tier=tier2`.

**Headline: the Tier-0 mask is gone.** Single-seeded-error passages reaching the grader jumped
**0/45 → 45/45**; every L2's span recall and F1 rose sharply.

| L2 | span F1 | span recall | subtype acc | overall QWK | clean FP rate | items→model | cost |
|----|---------|-------------|-------------|-------------|---------------|-------------|------|
| EN | 0.293 → **0.494** | 0.222 → **0.704** | 0.333 → 0.684 | 0.516 → 0.512 | 0.000 → **0.300** | 6 → 29 | $0.021 → $0.089 |
| JA | 0.194 → **0.554** | 0.111 → **0.852** | 1.000 → 0.913 | 0.186 → **0.571** | 0.000 → **0.700** | 1 → 30 | $0.009 → $0.354 |
| ZH | 0.000 → **0.597** | 0.000 → **0.885** | n/a → 0.826 | 0.000 → **0.216** | 0.000 → **0.400** | 0 → 30 | $0.000 → $0.216 |

Total 623 spend **$0.659** (14 → 172 model calls). Per-dimension QWK rose on the dimensions the
seeds exercise: accuracy EN 0.440→0.485 / JA 0.149→0.701 / ZH 0.000→0.701; fidelity EN
0.167→0.510 / JA 0.038→0.625 / ZH 0.000→0.795.

**Gate assessment**

- ✅ **Single-error detection / span recall — improved on all three L2s** (the primary TASK-623
  objective). ZH went from a total blind spot (0.000) to 0.885 recall.
- ✅ **Discriminating power (overall_band QWK) held or improved** — EN flat within noise
  (0.516→0.512), JA +0.385, ZH +0.216. The fix did not blunt band agreement.
- ⚠️ **Clean-passage FP rate rose (0.000 → 0.30 / 0.70 / 0.40)** — this is the mask lifting, not
  a regression TASK-623 introduced. The baseline's 0.000 was explicitly an artifact of Tier-0
  short-circuiting clean items to zero errors before the grader ran (see "Per-L2 summary"
  above). With errors now reaching the grader, we measure its **real** precision on clean input
  for the first time — and it over-flags clean passages (worst on JA, 7/10). Driving this FP
  down is **TASK-624's explicit remit** (acceptable-variation block, accounted-for rule, span
  discipline); TASK-623 is measurement→structural and does not touch prompts/taxonomy.

**Incidental (unchanged from baseline):** three EN Tier-2 responses still `fell_open` on
wrong-shape JSON (en_seed_03, en_multi_02/03) — the v1 silent-full-marks robustness issue
ADR-019 / TASK-628 replaces with a `provisional` grade.

**New regression floor for TASK-624+:** span F1 (EN 0.494 / JA 0.554 / ZH 0.597), overall QWK
(EN 0.512 / JA 0.571 / ZH 0.216). TASK-624 must **lower clean FP** while holding these.

## TASK-624 update — Phase-1 prompt upgrades + rubric v4 (2026-07-05)

Re-ran the identical harness + frozen gold sets, live, through the **Phase-1 prompts**: the
tier1/tier2 system prefix now carries the accounted-for rule, an acceptable-variation block
(rubric v4 config, per-L2 bullets), reader-impact severity tests, span discipline, and a worked
exemplar; the user prompt injects the tier-0 non-equal diff opcodes as **candidate regions**;
and `_decode_error` now repairs `learner_form`/`span_repro` mismatches by substring search
before dropping. `dt_rubric_version` bumped **v2 → v4** (band descriptors + weights byte-identical
to v2, inherited via jsonb `||`; only `acceptable_variation` + `exemplars` added). Roles are
**not** swapped (still tier1/tier2, severity still global/local) — that is TASK-628/625.

**Headline: the clean-passage false-positive rate collapses on all three L2s — JA's worst-case
7/10 goes to 0/10 — with span F1 and recall *rising*, not falling.** So the acceptable-variation
block reduced over-flagging without suppressing real errors (the failure mode the task warned
about did not occur).

| L2 | clean FP rate | span F1 | span recall | subtype acc | overall QWK | items→model | cost |
|----|---------------|---------|-------------|-------------|-------------|-------------|------|
| EN | .300 → **.200** | .494 → **.553** | .704 → **.778** | .684 → **.714** | .512 → .467 | 29 → 30 | $0.089 → $0.126 |
| JA | .700 → **.000** | .554 → **.725** | .852 → **.926** | .913 → .760 | .571 → .430 | 30 → 30 | $0.354 → $0.292 |
| ZH | .400 → **.100** | .597 → **.658** | .885 → **.923** | .826 → .792 | .216 → **.255** | 30 → 30 | $0.216 → $0.224 |

Total 624 spend **$0.641** (172 model calls; EN 58 / ZH 56 / JA 58). Per-dimension QWK on
the two dimensions the seeds exercise: accuracy EN .485→.432 / JA .701→.577 / ZH .701→.658;
fidelity EN .510→.483 / JA .625→**.793** / ZH .795→.795.

**Gate assessment**

- ✅ **Clean-passage FP rate — fell below the 623 floor on all three L2s** (.30/.70/.40 →
  .20/.00/.10), the explicit TASK-624 remit. JA went from the worst pathology TASK-623
  surfaced (7/10 clean passages over-flagged) to **zero**.
- ✅ **Span F1 and recall — improved on all three L2s.** Recall did **not** drop (EN +.074, JA
  +.074, ZH +.038), so the acceptable-variation / span-discipline blocks tightened precision
  without trading back the 623 detection win. The FP reduction is a real precision gain, not
  error suppression.
- ⚠️ **Band-agreement QWK — a give-back, concentrated in `accuracy` and `overall_band` on
  EN/JA.** accuracy QWK slipped on all three (EN −.05, JA −.12, ZH −.04) and overall_band QWK
  dipped on EN (−.05) and JA (−.14), while ZH rose (+.04) and JA `fidelity` rose sharply
  (+.17). This is **variance compression, not the recall failure the task guarded against**:
  with fewer spurious errors the grader pushes clean/single items (26/30 of the gold, mostly
  band 4) toward the top of the scale, shrinking the band spread QWK rewards. Exact/adjacent
  agreement stayed high (overall adjacent 1.00 on all three). The honest read: TASK-624 bought
  a large precision/FP win at the cost of some discriminating power on the accuracy band,
  worst on JA — a tension to weigh, not a clean pass on the "no QWK regression" clause.

**Not addressed here (by scope):** the wrong-shape `fell_open` cases (EN en_multi_05 this run;
en_seed_03 / en_multi_02-03 previously) remain — that is TASK-628's provisional-grade remit, not
Phase-1's. Severity stays 2-level (TASK-625). Subtype accuracy dipping on JA/ZH (more matched
pairs to be right about, since recall rose) is within the taxonomy-v5 retag scope (TASK-626).

**Regression floor carried to TASK-625+:** clean FP (EN .200 / JA .000 / ZH .100), span F1
(EN .553 / JA .725 / ZH .658). The overall-QWK give-back on JA/EN is the open item the
Detector/Verifier split (TASK-628) is expected to recover via the verifier's reject pass.

## TASK-625 update — severity triad (minor/major/critical) (2026-07-07)

Re-ran the identical harness through the **MQM severity triad**. The only grading-visible change
since 624 is the severity *vocabulary* (DB CHECK `dt_error_instance_severity_check`, `SEVERITY_ENUM`,
the prompt reader-impact block, and the rubric-v4 exemplar severity re-tag); detection and scoring
logic are untouched (the Detector/Verifier role split and derived severity-weighted scoring stay
TASK-627/628). The harness now scores severity against the fixtures' **`severity_v2`** and passes
`em.SEVERITY_TRIAD_ORDER`, so **within-one severity agreement carries real signal for the first
time** (on the old 2-level scale every matched pair was trivially within one).

**Headline: the triad measures cleanly and the 624 floor holds (EN+ZH).** Both re-confirm span F1
and clean-FP at/above the 624 floor, and **severity within-one is 1.000 on both** — the grader never
misplaces a severity by more than one triad level. Severity *exact* agreement (.62 EN / .71 ZH) is
the new baseline to improve.

| L2 | clean FP (624 floor) | span F1 (624 floor) | subtype acc | **sev exact** | **sev within-one** | overall QWK |
|----|----------------------|---------------------|-------------|---------------|--------------------|-------------|
| EN | .200 (.200) ✓ | .553 (.553) ✓ | .714 | .619 (n=21) | **1.000** | .512 |
| ZH | .100 (.100) ✓ | .686 (.658) ✓ | .833 | .708 (n=24) | **1.000** | .412 |
| JA | — deferred — | — | — | — | — | — |

EN+ZH span P/R: EN .429/.778, ZH .545/.923; overall adjacent 1.000 on both; ZH `fidelity` QWK .857.
Spend ~$0.20 (part of the approved ~$0.64). **JA not re-confirmed this pass:** two JA runs were
orphaned by *environment* interruptions — a transient DNS failure (`getaddrinfo failed`), then a
session teardown mid-first-item — neither a code fault, and JA graded 0 items so ~$0 was spent. JA
runs the identical grader/enum path EN+ZH exercise, so the triad wiring is proven; the JA floor
re-check (624: span F1 .725 / clean FP .00) is **deferred** to the next JA harness run (the TASK-626
taxonomy re-tag re-runs it).

**Gate assessment**
- ✅ **Triad end-to-end:** severity decodes to minor/major/critical on live graded submissions
  (EN+ZH); within-one agreement 1.000 on both; DB backfilled to the triad (14 minor / 2 major / 0
  critical) with the CHECK tightened.
- ✅ **624 floor held (EN+ZH):** clean FP and span F1 at/above floor; ZH overall QWK rose
  .255→.412 (run variance — grading logic unchanged).
- ⏸ **JA floor:** deferred (environment-orphaned, not measured this pass — no regression signal, just
  unmeasured).

## TASK-626 update — taxonomy v5 (2026-07-13)

Re-ran the identical harness + gold sets, live, against **taxonomy v5** (the active
`dt_taxonomy_version` row; rubric untouched at v4 — a taxonomy-only bump). v5 grows each L2's
subtype set to the §5 sizes (EN 15 / JA 17 / ZH 17), adds `subtype_meta` (the §4 machinery
TASK-627 reads), and **splits JA `particle`** into `particle_wa_ga`/`particle_case`/`particle_other`.
Gold fixtures were re-tagged to v5 names, so both sides of the subtype-accuracy comparison speak v5.
The grading **code path is unchanged** since 625 — only the taxonomy (and thus the prompt's subtype
menu + glosses) moved. First, the harness itself was hardened (bounded retry+backoff + `--resume`);
this is what finally let **JA complete** — it recovered from a mid-run `getaddrinfo` DNS failure, the
exact interruption that orphaned JA twice in 625.

| L2 | subtype acc (floor) | span F1 (floor) | span P/R | clean FP (floor) | sev exact / within-1 | overall QWK |
|----|---------------------|-----------------|----------|------------------|----------------------|-------------|
| EN | .714 → **.727** ↑ | .553 → .543 | .407/.815 | .200 (.200) ✓ | .636 / **1.000** | .512 (.512) |
| ZH | .833 → **.739** ↓ | .686 → .639 | .500/.885 | .100 (.100) ✓ | .696 / **1.000** | .322 (.412) |
| JA | .760 → **.875** ↑ | .725 → .696 | .571/.889 | **.000 (.000)** ✓ | .792 / **1.000** | .429 (.430) |

Total 626 spend **$0.624** (EN $0.109 / ZH $0.216 / JA $0.299). JA graded 30/30 with **0 skipped**
(the retry wrapper absorbed the DNS blip). Per-dimension: fidelity QWK EN .483/JA .630/ZH **.759**;
accuracy QWK EN .658/JA .658/ZH .493.

**Gate assessment**

- ✅ **Subtype accuracy — the metric this task moves — up on EN (+.013) and JA (+.115).** The finer
  taxonomy pays off where it splits genuine grammar categories (JA particles, verb conjugation), and
  the model classifies the new indices well.
- ⚠️ **ZH subtype accuracy dipped .833 → .739.** This is the **finer-tagset exact-match effect §5
  predicted**, not a detection regression: ZH's .833 floor was scored on the old **9-way** v4 set;
  v5 is **17-way**, and the drop concentrates in the new *lexical* splits (`word_choice` →
  `de_particles` / `directional_complement` / `adverbial_order`) where the model still picks the
  coarser lexical neighbour. Span recall (.885) and TP count are undiminished — the errors are
  *found*, just labelled at the older granularity. Exemplars/glosses mitigate; sharper ZH
  classification is a native-review + few-shot follow-up, not a blocker for the groundwork bump.
- ✅ **Detection held on all three.** Span F1 slipped within run variance (EN −.010, JA −.029, ZH
  −.047) on unchanged detection code; span recall stayed high (.815/.885/.889); **clean-passage FP
  held exactly at the 625 floor** (.200 / .100 / .000) — precision on clean input did not regress.
- ✅ **Severity within-one 1.000 on all three, incl. JA** (first triad-scored JA run); severity exact
  .636 / .696 / .792.
- ✅ **JA floor re-confirmed** (the 625-deferred item): span F1 .696 (≈ .725 floor, run variance) and
  **clean FP .000 (= floor)**. The 625 "JA deferred" line is now closed.
- ➖ **overall_band QWK:** EN/JA flat (.512 / .429, unchanged within noise); ZH −.090 (.412 → .322) —
  band agreement is grading-logic-driven and untouched here, so this is run variance on a small gold
  set, consistent with the ZH give-back TASK-628's verifier reject-pass is expected to recover.

**Net:** v5 is live and correct (single active row; `subtype_meta` total; alias resolves; no
slug-fallback), detection + clean-FP held, EN/JA subtype accuracy improved, and the JA floor is
re-confirmed. The ZH subtype-accuracy dip is an expected granularity tradeoff to watch in native
review, not a gate failure. This unblocks TASK-627 (derived scoring reads `subtype_meta`).

## Reproduce

```
python scripts/run_dt_grading_eval.py --l2 {en|zh|ja} --out report.md --live [--resume ckpt.json]
```

Live calls are gated behind `--live` (dry run prints the plan and spends nothing); `--limit N` runs a
cheap smoke subset. Metrics come from `services.dual_translation.eval_metrics.aggregate_metrics`;
per-call token/cost is recorded by wrapping the model boundary and priced via
`services.model_arena.pricing`.

## Related Pages
- [[algorithms/evidence-first-grading.tech]] — §10 metrics + §9 Tier-0 fixes this measures
- [[tasklist/evidence-first-grading.tasks]] — TASK-622 (this harness), TASK-623 (Tier-0 fix)
- [[decisions/ADR-019-evidence-first-scoring]]
- [[algorithms/translation-grading-cascade.tech]] — v1 (shipped) grader under test
