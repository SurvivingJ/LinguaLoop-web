---
title: Mysteries — Technical Specification
type: feature-tech
status: deprecated
prose_page: ./mysteries.md
last_updated: 2026-09-22
dependencies:
  - "services/mystery_generation/"
  - "services/mystery_service.py"
  - "routes/mystery.py"
  - "templates/mystery.html, mystery_list.html"
breaking_change_risk: low
---

# Mysteries — Technical Specification

> **ARCHIVED 2026-09-21.** Code (routes/mystery.py, services/mystery_service.py, services/mystery_generation/, both templates), the admin tab, CSS and i18n keys were removed from the codebase; the 6 tables, 2 RPCs and 16 prompt_templates rows are exported in the zip. Everything (code, docs, table rows, DDL, restore notes) is in `archive/modules/mysteries-2026-09-21.zip` (gitignored, local only). The tables were dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). This page is kept for history only.


## Architecture Overview

```
Generation:
  mystery_generation/ → LLM → story with scenes + questions → storage

Serving:
  GET  /api/mystery/list       → available mysteries
  GET  /api/mystery/<slug>     → mystery content + scenes
  POST /api/mystery/<slug>/submit → answer scene questions

Pages:
  /mysteries         → mystery_list.html
  /mystery/<slug>    → mystery.html
```

## Service Layer

- `services/mystery_generation/` — LLM-based story generation with config
- `services/mystery_service.py` — serving logic, progress tracking
- `routes/mystery.py` — Flask blueprint at `/api/mystery`

## Related Pages

- [[features/mysteries]] — Prose description
