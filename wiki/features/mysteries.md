---
title: Mysteries
type: feature
status: deprecated
tech_page: ./mysteries.tech.md
last_updated: 2026-09-22
open_questions:
  - "How does mystery difficulty calibrate — age-tier-based, ELO-based, or manual?"
  - "Are mystery scenes generated all at once or incrementally?"
  - "Does mystery performance feed into ELO or BKT?"
---

# Mysteries

> **ARCHIVED 2026-09-21.** Code (routes/mystery.py, services/mystery_service.py, services/mystery_generation/, both templates), the admin tab, CSS and i18n keys were removed from the codebase; the 6 tables, 2 RPCs and 16 prompt_templates rows are exported in the zip. Everything (code, docs, table rows, DDL, restore notes) is in `archive/modules/mysteries-2026-09-21.zip` (gitignored, local only). The tables were dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). This page is kept for history only.


## Purpose

Mysteries are murder-mystery stories that combine narrative engagement with language comprehension assessment. Each story is split into scenes, with comprehension questions gating progression from one scene to the next.

## User Story

A learner browses the mystery list and picks a story. They read the first scene of a murder mystery in their target language. To unlock the next scene, they must correctly answer comprehension questions about what they've read. The story unfolds scene by scene, blending entertainment with active comprehension practice.

## How It Works

1. Admin triggers mystery generation for a language and difficulty level.
2. LLM generates a multi-scene murder mystery story with characters, clues, and a resolution.
3. Each scene has associated comprehension questions.
4. Learner reads scene → answers questions → if correct, next scene unlocks.
5. The final scene reveals the solution.

## Constraints & Edge Cases

- A learner who fails scene questions should be able to retry.
- Mystery progress should persist across sessions.
- Stories should be long enough to be engaging but short enough per scene for focused reading practice.

## Business Rules

- Mysteries are system-generated, not user-created.
- Generation is manually triggered by admin.
- Each mystery has a slug for URL routing.

## Related Pages

- [[features/mysteries.tech]] — Technical specification
- [[features/comprehension-tests]] — Shared MC question format
