---
title: "ADR-019: Evidence-First Scoring & Three-Layer Explanations"
status: accepted
date: 2026-07-04
---

# ADR-019: Evidence-First Scoring & Three-Layer Explanations

## Context
The shipped v1 grader (TASK-605/606/616) asks the LLM for gestalt 1–4 bands alongside an
error list, and renders one generic explanation template per (subtype, L1). The product goal
is grading that is *specific* (pinpoints the actual mistake), *precise* (few false alarms),
and *clear* (a band you can justify). Three findings drive this decision:

1. Bands emitted by a model are not reproducible or explainable — nothing links them to the
   errors found. Translation-industry practice (MQM) computes scores from severity-weighted
   error counts instead; LLM-judge research shows evidence-grounded, checklist-style
   decisions are far more reliable than unanchored Likert bands.
2. One template per subtype cannot be instance-specific by construction — the "why" the
   learner reads never mentions their actual sentence. WCF research (Bitchener & Knoch;
   Kang & Han meta-analysis) finds direct correction + metalinguistic explanation most
   effective, and the metalinguistic part is most useful when it addresses the instance.
3. The binary global/local severity axis cannot express the difference between a typo and a
   dropped negation, so neither the scores nor the remediation queue can rank errors well.

## Decision
1. **Scores are computed, not asked for.** Dimension bands for accuracy, fidelity, and
   understandability are pure functions of the confirmed error set (severity weights
   minor=1 / major=5 / critical=25, per-dimension thresholds in `dt_rubric_version.config`).
   The model detects and classifies; Python scores. Only naturalness and range remain
   model-judged, and only with cited evidence spans. Historical grades are re-scorable from
   stored `dt_error_instance` rows without model calls.
2. **Severity becomes a triad** (minor/major/critical) with operationalized reader-impact
   tests, replacing global/local. Requires a CHECK-constraint extension + backfill
   (local→minor, global→major).
3. **The two grading calls become Detector and Verifier.** The detector exhaustively finds
   errors (no scores) guided by the Tier-0 diff; the verifier confirms/rejects/adjusts each
   one, adds what was missed, and judges naturalness/range. Rejecting false positives is an
   explicit, first-class model duty.
4. **Explanations gain a third, instance-specific layer.** Correction (data) + Rule
   (per-subtype × per-L1 template, unchanged from ADR-015) + **Application** — 1–2 model-
   generated L1 sentences explaining why the rule applies to these exact words, produced by
   one cheap batched Explainer call per submission, validated in code, falling back to
   Rule-only. This **revises ADR-015's "never model prose"**: the rule stands for *grading*
   output (Detector/Verifier stay L2-only + numerical), but is relaxed for this single
   non-grading, learner-facing, L1 surface.

## Consequences
- Easier: justifying any band to the learner ("Accuracy 3 — one major particle error");
  regression-testing the grader (errors are the unit, scores are deterministic); re-scoring
  after rubric changes (free); tuning strictness (edit thresholds, not prompts).
- Harder: three model calls on error-bearing submissions (detector, verifier, explainer) vs
  two — bounded by using the cheap slug for detector+explainer; taxonomy/rubric authoring
  load grows (glosses + templates for ~15–17 subtypes per pair, new descriptors).
- Constrained: dimension mapping must be total (every subtype maps to exactly one scored
  dimension); the Application layer may never carry score authority or contradict the
  Correction (enforced by validation + fallback).
- Migration: severity CHECK change is the only schema migration; explanation concatenation
  avoids a dt_error_instance schema change.

## Alternatives Considered
1. **Keep gestalt banding, improve prompts only.** Rejected: better prompts cannot make an
   unanchored band reproducible or explainable; the AES literature shows anchoring helps but
   computed scores remove the variance class entirely.
2. **Fully model-generated explanations (drop templates).** Rejected: loses the expert-
   authored rule quality, versioning, and the L2-only/numerical grading contract; higher
   hallucination surface. The hybrid keeps the template as the trusted core.
3. **Three-level severity inside the model score only (no DB change).** Rejected: the
   remediation queue and error profile need the stored severity to rank; hiding it in the
   score loses the data.
4. **MQM per-word density normalization.** Deferred: passages are uniformly 2–4 sentences
   (selection-controlled), so absolute per-passage thresholds are simpler and legible to
   learners; revisit if passage length becomes variable.

## Related
- [[algorithms/evidence-first-grading]] / [[algorithms/evidence-first-grading.tech]]
- Revises: [[decisions/ADR-015-eager-error-explanations]] (Application layer only)
- Unchanged: [[decisions/ADR-014-reference-first-grading]], [[decisions/ADR-018-level-neutral-grading]]
