---
title: "ADR-015: Eager, First-Class Error Explanations (override of brief §4.4)"
status: accepted
date: 2026-06-22
---

# ADR-015: Eager, First-Class Error Explanations (override of brief §4.4)

## Context
The implementation brief (§4.4) recommends generating human-readable error explanations
**lazily** — only when a learner opens a given dimension — to save output tokens. However, the
product owner's explicit instruction is that **explaining which errors occurred and why they are
errors is vital**. The explanation is the core pedagogical payload (Schmidt's noticing; Sadler's
"close the gap"), not an optional add-on.

## Decision
Produce an explanation for **every** detected error **eagerly**, at grading time, written in the
learner's L1, and persist it on `dt_error_instance.explanation`. The grader call is **L2-only and
returns numerical indices** (no English, no prose — a standing business rule); the explanation is
then **rendered from a versioned per-subtype × per-L1 template** keyed by the grader's numerical
subtype index, with `corrected_form`/`learner_form` slotted in
([[business-rules/translation-error-taxonomy]]). This makes explanations eager, precise, fully
multilingual, **and cheaper than model prose** — they cost ~zero marginal tokens. A missing
`(subtype, L1)` template falls back to a generic corrected-form string and is flagged for
authoring; it is never blank.

## Consequences
- **Easier:** the learning value is delivered up-front; no second round-trip when a learner opens
  an error.
- **Harder/cost:** higher eager token spend than lazy generation. Mitigated by templating + caching
  and bounded by the per-user/day budget guardrail.
- **Constrained:** `explanation` is a NOT NULL field on every error instance.

## Alternatives Considered
1. **Lazy on-open (brief default).** Cheaper but defers/omits the core learning content; conflicts
   with the explicit product priority. Rejected.
2. **Model-generated prose explanations.** Higher quality on rare nuanced cases, but violates the
   L2-only/numerical-output rule and costs per-error output tokens. Rejected as the default;
   templates keyed by the rich subtype taxonomy are precise enough. A nuanced-case prose path can
   be added later as opt-in if specific subtypes prove under-served.
