---
title: "ADR-016: Per-Directed-Pair Error Taxonomy (per-user L1)"
status: accepted
date: 2026-06-22
---

# ADR-016: Per-Directed-Pair Error Taxonomy (per-user L1)

## Context
Learners may have any of ZH/EN/JA as their native language (L1) while studying another as L2.
The error taxonomy ([[business-rules/translation-error-taxonomy]]) classifies errors as
**interlingual** (L1 transfer) vs **intralingual** (within-L2). Interlingual classification is
only meaningful relative to a specific L1 — an article-omission transfer error from a Chinese L1
is a different signal than from a Japanese L1.

## Decision
Define the taxonomy with a **shared cross-linguistic schema** (category × source × severity ×
error-vs-mistake) plus **per-directed-pair** subtype tables and weightings, keyed by
(L1_language_id, L2_language_id). The `passage` stores the L2 gold once and an **L1 reference per
supported L1** (`dt_passage_reference`), so one passage serves learners of different L1s. Error
profiles and remediation are scoped per directed pair.

## Consequences
- **Correct:** interlingual transfer detection and remediation reflect the learner's actual L1.
- **Easier reuse:** a single L2 passage serves up to three L1 audiences.
- **Harder:** up to 6 directed pairs to localise (the brief assumed L1=English only). Staged:
  build the shared schema first, then localise pair-by-pair (English L2 first per the brief).
- **Constrained:** L1 references must be generated for each supported L1 before a passage is
  servable to that audience.

## Alternatives Considered
1. **English-only L1.** Simplest (single interlingual rule set), matches the brief's staging, but
   wrong for our actual multi-L1 user base. Rejected.
2. **Ignore L1 (intralingual only).** Loses the interlingual signal that drives much of the
   transfer-error remediation value. Rejected.
