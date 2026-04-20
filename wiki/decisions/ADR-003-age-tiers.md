---
title: "ADR-003: Age Tier Difficulty System Replacing CEFR"
status: accepted
date: 2026-04-10
---

# ADR-003: Age Tier Difficulty System Replacing CEFR

## Context

LinguaLoop needs a difficulty calibration system for exercises and content generation. CEFR (Common European Framework of Reference for Languages) is the standard academic framework, but it has practical limitations when used as LLM generation instructions — LLMs produce more natural and appropriately-leveled content when guided by age-appropriate language descriptions rather than abstract proficiency labels.

## Decision

Replace CEFR labels with a **6-tier Age-Based Difficulty System** for all content generation. The tiers are:

| Tier | Name | Age Analog | Approx. CEFR | Vocab Size |
|------|------|-----------|-------------|------------|
| 1 | The Toddler | 4–5 | A1 | ~500 |
| 2 | The Primary Schooler | 8–9 | A2 | ~2,000 |
| 3 | The Young Teen | 13–14 | B1 | ~5,000 |
| 4 | The High Schooler | 16–17 | B2 | ~10,000 |
| 5 | The Uni Student | 19–21 | C1 | ~15,000+ |
| 6 | The Educated Professional | 30+ | C2 | ~25,000+ |

Each tier includes specific LLM instruction text that constrains vocabulary, sentence complexity, and topic appropriateness.

## Consequences

- **Easier:** LLMs produce more natural, appropriately-leveled content when given age-based instructions vs abstract CEFR labels.
- **Easier:** The age metaphor is intuitive for developers and content reviewers — "would a 13-year-old say this?" is easier to judge than "is this B1?"
- **Harder:** Existing CEFR references in the database (`cefr_level` columns) need to be migrated or mapped.
- **Harder:** Users familiar with CEFR may need a mapping table in the UI.
- **Constrained:** The approximate CEFR mapping is not exact — some edge cases may fall between tiers.

## Alternatives Considered

1. **Keep CEFR** — Standard and widely understood, but LLMs struggle to consistently distinguish between adjacent levels (B1 vs B2).
2. **Numeric 1-10 scale** — More granular but lacks the intuitive anchoring that age descriptions provide.
3. **Hybrid (CEFR + age instructions)** — Considered, but adds complexity without clear benefit. The age tier IS the instruction; CEFR is just a rough mapping for external communication.
