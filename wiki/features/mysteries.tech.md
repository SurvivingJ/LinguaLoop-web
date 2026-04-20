---
title: Mysteries — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./mysteries.md
last_updated: 2026-04-10
dependencies:
  - "services/mystery_generation/"
  - "services/mystery_service.py"
  - "routes/mystery.py"
  - "templates/mystery.html, mystery_list.html"
breaking_change_risk: low
---

# Mysteries — Technical Specification

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
