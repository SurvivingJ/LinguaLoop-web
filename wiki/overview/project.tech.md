---
title: LinguaLoop — Technical Specification
type: overview-tech
status: in-progress
prose_page: ./project.md
last_updated: 2026-04-10
dependencies:
  - "Supabase (PostgreSQL + Auth + RLS)"
  - "Flask 2.x"
  - "OpenRouter (LLM inference)"
  - "Azure Cognitive Services (TTS)"
  - "Cloudflare R2 (audio storage)"
  - "Stripe (payments)"
  - "Railway (hosting)"
breaking_change_risk: low
---

# LinguaLoop — Technical Specification

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                      Railway                            │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Flask Application (Gunicorn via Procfile)        │  │
│  │                                                   │  │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │  │
│  │  │  Routes   │  │ Services │  │  Middleware     │  │  │
│  │  │ (Blueprints)│ (Business │  │  (Auth JWT)    │  │  │
│  │  │          │  │  Logic)  │  │                │  │  │
│  │  └────┬─────┘  └────┬─────┘  └───────┬────────┘  │  │
│  │       │              │                │           │  │
│  │  ┌────▼──────────────▼────────────────▼────────┐  │  │
│  │  │              Jinja2 Templates               │  │  │
│  │  │         (HTML + vanilla JS + CSS)           │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
└──────────────┬──────────────┬───────────┬───────────────┘
               │              │           │
     ┌─────────▼──────┐ ┌────▼─────┐ ┌───▼──────────┐
     │   Supabase      │ │ OpenRouter│ │ Azure TTS    │
     │ (PostgreSQL +   │ │ (LLM API)│ │ (Speech)     │
     │  Auth + RLS)    │ │          │ │              │
     └────────────────┘ └──────────┘ └──────────────┘
               │
     ┌─────────▼──────┐  ┌─────────────────┐
     │ Cloudflare R2  │  │     Stripe       │
     │ (Audio files)  │  │  (Payments)      │
     └────────────────┘  └─────────────────┘
```

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Backend** | Python 3.11 / Flask | Gunicorn WSGI via Procfile |
| **Frontend** | Jinja2 + vanilla JS + CSS | Server-rendered, no SPA framework |
| **Database** | PostgreSQL via Supabase | ~30+ tables, RLS policies, 40+ plpgsql functions |
| **Auth** | Supabase Auth + JWT | Custom middleware validates Supabase JWTs |
| **AI / LLM** | OpenRouter | Language-specific model routing (Gemini, DeepSeek, Qwen) |
| **TTS** | Azure Cognitive Services | Text-to-speech for listening tests |
| **File Storage** | Cloudflare R2 | Audio files for listening tests |
| **Payments** | Stripe | Token purchase packages |
| **Hosting** | Railway | Deployed via Procfile |
| **NLP** | jieba, langdetect, unidic | Chinese/Japanese tokenization, language detection |

## Application Structure

```
WebApp/
├── app.py                    # Flask app factory
├── config.py                 # Unified configuration (env vars)
├── wsgi.py                   # WSGI entry point
├── Procfile                  # Railway deployment
├── requirements.txt          # Python dependencies
│
├── middleware/
│   └── auth.py               # Supabase JWT validation middleware
│
├── routes/                   # Flask Blueprints
│   ├── auth.py               # /api/auth — login, signup, session
│   ├── tests.py              # /api/tests — comprehension tests
│   ├── exercises.py          # /api/exercises — exercise serving
│   ├── flashcards.py         # /api/flashcards — FSRS review
│   ├── vocabulary.py         # /api/vocabulary — vocab extraction
│   ├── corpus.py             # /api/corpus — corpus management
│   ├── mystery.py            # /api/mystery — mystery stories
│   ├── conversations.py      # /api/conversations — conversation corpus
│   ├── reports.py            # /api/reports — user bug reports
│   ├── users.py              # /api/users — profile, settings
│   ├── payments.py           # /api/payments — Stripe integration
│   ├── vocab_dojo.py         # /api/vocab-dojo — vocab dojo (new)
│   └── vocab_admin.py        # /api/admin/vocab — admin preview
│
├── services/
│   ├── test_generation/      # Comprehension test generation pipeline
│   ├── topic_generation/     # Topic discovery + embedding pipeline
│   ├── exercise_generation/  # Exercise generation from grammar/vocab/collocations
│   ├── conversation_generation/ # Simulated dialogue generation
│   ├── mystery_generation/   # Murder mystery story generation
│   ├── vocabulary/           # NLP pipeline: tokenization, BKT, FSRS, frequency
│   ├── vocabulary_ladder/    # Vocab Dojo adaptive serving (new)
│   ├── corpus/               # Corpus analysis: collocations, style, packs
│   ├── test_service.py       # Test serving + ELO matching
│   ├── auth_service.py       # Auth helpers
│   ├── payment_service.py    # Stripe integration
│   ├── ai_service.py         # OpenAI client wrapper
│   ├── llm_service.py        # OpenRouter LLM client
│   ├── r2_service.py         # Cloudflare R2 file operations
│   ├── prompt_service.py     # Prompt template management
│   └── dimension_service.py  # Cached dimension table lookups
│
├── templates/                # Jinja2 HTML templates
├── static/                   # CSS, JS, images
├── models/                   # Pydantic request models
├── utils/                    # Validation helpers
├── prompts/                  # Prompt template definitions
└── migrations/               # SQL migration files
```

## Key Architectural Decisions

1. **Server-rendered with client-side interactivity**
   - Rationale: Simpler deployment, no separate frontend build, good enough for the current feature set.
   - Alternatives rejected: SPA (React/Vue) — added complexity without clear benefit for this use case.

2. **Supabase as database + auth**
   - Rationale: Managed PostgreSQL with built-in auth, RLS, and real-time. Reduces infrastructure management.
   - Alternatives rejected: Self-hosted Postgres + custom auth — more ops burden.

3. **OpenRouter for LLM routing**
   - Rationale: Single API, multiple model providers. Language-specific model selection (e.g. DeepSeek for Chinese, Qwen for Japanese).
   - Alternatives rejected: Direct OpenAI API — less model flexibility.

4. **Dimension table caching via DimensionService**
   - Rationale: Languages, test types, age tiers rarely change. Cached at startup to avoid repeated DB calls.

## Environment Variables

Key configuration loaded from `.env` via `config.py`:
- `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- `OPENROUTER_API_KEY`, `USE_OPENROUTER`
- `OPENAI_API_KEY` (for embeddings/TTS fallback)
- `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`
- `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_ENDPOINT_URL`
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- `SECRET_KEY`, `JWT_SECRET_KEY`
- `FLASK_DEBUG`

## Admin Pipeline Dashboard

The admin dashboard (`/admin/vocab`) is the primary interface for manually triggering and monitoring content generation pipelines. It is **not** a user-facing feature — it is an internal tool for the developer/admin.

### Requirements
- **Manual trigger** for each pipeline stage (conversation generation → vocabulary extraction → exercise generation → validation)
- **Per-stage controls** — ability to run individual stages independently
- **Debugging stats** — success/failure counts, error messages, stage timing for each pipeline run
- **Spot-check UI** — preview generated content (conversations, exercises, vocabulary items) directly from the dashboard before approving
- **Pipeline status** — visual indicator of which stages have completed, which are pending, which failed

### Architecture
- Route: `routes/vocab_admin.py` (Blueprint: `/api/admin/vocab`)
- Template: `templates/admin_vocab_preview.html`
- All generation runs locally (no serverless/cloud functions) — the admin triggers pipelines via the dashboard, generation executes server-side
- Pipeline telemetry stored in `test_generation_runs` table (reused for all pipeline types)

## Related Pages

- [[overview/project]] — What LinguaLoop is
- [[database/schema]] — Data model
- [[api/rpcs]] — API surface
- [[features/language-packs.tech]] — Pack generation pipeline
- [[features/vocab-dojo.tech]] — Exercise serving system
