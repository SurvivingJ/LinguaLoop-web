---
title: LinguaLoop — Technical Specification
type: overview-tech
status: in-progress
prose_page: ./project.md
last_updated: 2026-04-25
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

The admin dashboard (`/admin`) is the primary interface for manually triggering and monitoring content generation pipelines. It is **not** a user-facing feature — it is an internal tool for the developer/admin.

### Architecture
- Entry point: `admin_app.py` (local-only Flask app)
- Route: `routes/admin_local.py` (Blueprint: `/admin`)
- Template: `templates/admin_dashboard.html` (single-page, 9 tabbed sections)
- JavaScript: `static/js/admin-dashboard.js` (vanilla JS, event wiring + SSE consumption)
- Background tasks: `_run_in_thread()` spawns daemon threads, captures logs via `QueueLogHandler`, streams via Server-Sent Events
- Stop mechanism: `is_task_stopped()` checks a `threading.Event`; frontend POSTs `/api/task-stop/<task_id>`

### Dashboard Tabs (9)

| Tab | Endpoint | Runner | Purpose |
|-----|----------|--------|---------|
| Corpus Ingestion | `POST /api/run/corpus-ingest` | `CorpusIngestionService` | Ingest URL/text/transcripts, extract collocations, optional style analysis |
| Topic Generation | `POST /api/run/topic-generation` | `TopicGenerationOrchestrator` | Auto-generate or manually insert topics + queue for languages |
| Test Generation | `POST /api/run/test-generation` | `TestGenerationOrchestrator` | Generate comprehension tests from production queue |
| Exercise Generation | `POST /api/run/exercise-generation` | `run_grammar_batch`, `run_vocabulary_batch`, `run_collocation_batch` | Generate exercises for selected grammar/vocab/collocation sources |
| Style Analysis | `POST /api/run/style-analysis` | `CorpusIngestionService._run_style_pipeline` | Analyze writing style from existing/new corpus |
| Conversations | `POST /api/run/conversation-generation` | `ConversationBatchProcessor` | Generate dialogues + exercises per domain |
| Mysteries | `POST /api/run/mystery-generation` | `MysteryGenerationOrchestrator` | Generate murder mystery stories |
| Pinyin Backfill | `POST /api/run/pinyin-backfill` | `pinyin_service.process_passage` | Backfill pinyin payloads for Chinese tests |
| **Full Pipeline** | `POST /api/run/full-pipeline` | Orchestrates 6 backfill steps | End-to-end content pipeline for a single language (see below) |

### Full Pipeline Tab

Runs the entire content pipeline end-to-end for a single language with one button click. All steps are idempotent — safe to run repeatedly.

**Steps (sequential, with stop checks between each):**

1. **Vocab Backfill** (`VocabBackfillRunner`) — Extract vocabulary from unprocessed tests, create `dim_vocabulary` + `dim_word_senses`, write `vocab_sense_ids` + `vocab_token_map`
2. **Token Map Backfill** (`TokenMapBackfillRunner`) — Fill `vocab_token_map` for tests that have senses but no token map, with `create_missing=True`
3. **Question Sense IDs** (`run_backfill`) — Match vocab lemmas against question text/choices, write per-question `sense_ids[]`
4. **Test Skill Ratings** (`BackfillRunner`) — Create `test_skill_ratings` rows with difficulty-based ELO for tests missing them
5. **Exercise Backfill** (`ExerciseBackfillRunner`) — Generate exercises for vocabulary senses + grammar patterns + style items without exercises
6. **Collocation Exercises** (`run_collocation_batch` with idempotency wrapper) — Generate exercises for collocations without exercises

### Vocab Preview Dashboard
- Route: `routes/vocab_admin.py` (Blueprint: `/api/admin/vocab`)
- Template: `templates/admin_vocab_preview.html`
- Separate from the main admin dashboard; provides spot-check UI for generated vocabulary items

## Related Pages

- [[overview/project]] — What LinguaLoop is
- [[database/schema]] — Data model
- [[api/rpcs]] — API surface
- [[features/language-packs.tech]] — Pack generation pipeline
- [[features/vocab-dojo.tech]] — Exercise serving system
