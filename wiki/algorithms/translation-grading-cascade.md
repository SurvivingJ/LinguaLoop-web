---
title: Translation Grading Cascade
type: algorithm
status: planned
tech_page: ./translation-grading-cascade.tech.md
last_updated: 2026-06-22
---

# Translation Grading Cascade

## Purpose
Grade a learner's L2 reproduction against an existing gold L2 reference as cheaply as possible
without sacrificing quality on the dimensions that matter most (accuracy, understandability).

## How It Works
Grading runs as a ladder where each rung is more expensive than the last, and most submissions
never leave the first, free rung:

1. **Free deterministic pass.** The system normalises both texts and computes a word-level diff
   (the same engine the Dictation feature already uses). If the reproduction matches the gold
   exactly or near-exactly, it gets full marks with zero AI cost. A cheap similarity check and a
   result cache catch repeats and tiny variations for free too.
2. **Cheap model pass.** Only reproductions that genuinely differ go to a low-cost model, which
   tags grammatical/lexical (accuracy) errors where the gold makes the answer near-certain.
3. **Mid model pass.** The fuzzy, human-divergent judgements — understandability, fidelity and
   register, and the deliberately low-stakes naturalness — only run when they weren't settled
   earlier or the cheap pass was unsure.
4. **Expensive model — off by default.** Reserved for rare disputed cases and one-off
   calibration content; never in the normal per-submission path.

The single biggest saving is **prompt caching**: the rubric, the per-age-tier band descriptors,
the calibration examples and the per-language instructions are identical on every submission, so
they are cached once and only the learner's text is billed fresh.

## Constraints & Edge Cases
- We use **OpenRouter**, which has no batch-discount tier — so "batching" means moving work
  off the live path (nightly), and the real savings come from the free pass + prompt caching.
- If the daily budget is exceeded, grading **degrades** to the free + cheap passes rather than
  failing the learner.
- Explanations of *why* each error is an error are generated **eagerly** (not lazily), because
  that explanation is the core learning payload — see [[decisions/ADR-015-eager-error-explanations]].

## Related Pages
- [[algorithms/translation-grading-cascade.tech]] — tiers, slugs, caching, budget guardrails
- [[features/dual-translation]] — the feature this powers
- [[features/dictation]] — source of the reused diff engine
