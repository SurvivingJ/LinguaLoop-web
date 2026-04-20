---
title: "Language Packs — Task Breakdown"
feature: language-packs
prose_page: ../features/language-packs.md
tech_page: ../features/language-packs.tech.md
total_tasks: 0
done: 0
---

# Language Packs — Task Breakdown

> **Blocked:** Task decomposition cannot proceed until the following design questions are resolved. See [[features/language-packs.tech]] for details.

## Blocking Open Questions

1. **Database schema** — What new tables are needed? `language_packs`, `pack_conversations`, `pack_key_words`, `pack_exercises`, `user_pack_progress`? What are their columns and relationships?

2. **Pack generation orchestrator** — Single script or multi-stage pipeline? How does it coordinate conversation generation → corpus analysis → vocabulary linking → exercise generation?

3. **Progression model** — Is the study path linear (words → snippets → conversations → final test) or adaptive (unlock based on BKT state per word)?

4. **Conversation designation** — How are conversations split between "study material" and "final assessment"? Manual, automatic, or configurable?

5. **Key word selection** — How are NLP-extracted and LLM-suggested key words merged? What's the minimum/maximum word count per pack?

6. **ELO integration** — Does pack completion affect the user's ELO? Are pack conversations rated like regular tests?

## Proposed Task Areas (Pending Confirmation)

Once design is resolved, tasks will likely cover:

1. Database migration — new tables
2. Pack generation orchestrator service
3. Pack serving API endpoints
4. Pack study UI (word study, snippets, conversations)
5. Pack progress tracking
6. Pack browsing/selection UI
7. Integration tests
