---
title: "ADR-014: Reference-First Deterministic Grading for Dual Translation"
status: accepted
date: 2026-06-22
---

# ADR-014: Reference-First Deterministic Grading for Dual Translation

## Context
The Dual Translation feature grades a learner's L2 reproduction against an existing gold L2
reference. This is reference-based assessment, not open-ended essay scoring, so a large fraction
of grading can be resolved by string alignment before any LLM call. LinguaDojo already ships a
Levenshtein diff grader for [[features/dictation]] (`services/dictation/grader.py`).

## Decision
Grade through a tier-0-first cascade ([[algorithms/translation-grading-cascade.tech]]):
a free deterministic pre-pass (normalise → diff via the reused dictation grader → exact/near
match awards full marks with zero model calls → embedding gate + result cache) runs always and
first; only genuine divergences escalate to OpenRouter model tiers. The diff/alignment artifact
is a **primary output** (it is the noticing surface), not a byproduct of scoring.

## Consequences
- **Easier/cheaper:** most submissions cost zero or near-zero tokens; the diff UI is free.
- **Easier:** reuses an existing, tested grader instead of new alignment code.
- **Harder:** short multi-sentence passages produce fuzzier diffs than single-word dictation, so
  Tier 0 routes-and-aligns rather than fully auto-marking non-trivial cases.
- **Constrained:** the gold reference must exist and be stored per passage.

## Alternatives Considered
1. **Always send to an LLM.** Simpler pipeline, but wasteful and slow for the many near-exact
   reproductions; rejected on cost.
2. **New bespoke alignment engine.** Rejected — the dictation grader already does this.
