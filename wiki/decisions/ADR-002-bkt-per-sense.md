---
title: "ADR-002: BKT Vocabulary Tracking at Word-Sense Level"
status: accepted
date: 2026-04-10
---

# ADR-002: BKT Vocabulary Tracking at Word-Sense Level

## Context

LinguaLoop needs to track which words a learner knows. The granularity of tracking matters: tracking at the word level misses polysemy (e.g., "run" has dozens of meanings), while tracking at the individual occurrence level would be too noisy.

## Decision

Use Bayesian Knowledge Tracing (BKT) at the **word sense** level. Each (user, word_sense) pair has an independent `p_known` probability that updates with evidence from comprehension tests and direct word quizzes. Different evidence types have different slip/guess parameters to reflect their reliability.

## Consequences

- **Easier:** Vocabulary recommendations are precise — the system knows which specific meanings a learner struggles with.
- **Easier:** Test selection can target a specific unknown-word percentage (the "i+1" zone).
- **Harder:** Word sense disambiguation must be reliable — wrong sense assignments corrupt the model.
- **Harder:** More rows in `user_vocabulary_knowledge` — O(users * senses encountered).
- **Constrained:** BKT is a simple two-state model. It doesn't capture partial knowledge or context-dependent knowledge.

## Alternatives Considered

1. **Lemma-level tracking** — simpler but loses polysemy. Knowing "bank" (river) doesn't mean knowing "bank" (financial).
2. **Deep Knowledge Tracing (DKT)** — neural approach, potentially more accurate. Rejected for complexity and interpretability concerns.
3. **Simple frequency counting** — not probabilistic, doesn't account for guessing or slipping. Rejected.
