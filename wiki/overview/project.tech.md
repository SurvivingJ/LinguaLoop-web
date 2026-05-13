---
title: LinguaDojo — Technical Specification
type: overview-tech
status: complete
prose_page: ./project.md
last_updated: 2026-05-12
dependencies:
  - "Supabase (PostgreSQL + Auth + RLS)"
  - "Flask 2.x + Gunicorn"
  - "OpenRouter (LLM inference, multi-model routing)"
  - "OpenAI (moderation + embeddings)"
  - "Azure Cognitive Services (TTS for listening tests + vocab L1)"
  - "Cloudflare R2 (audio storage)"
  - "Stripe (payments)"
  - "Railway (hosting)"
  - "APScheduler (nightly IRT calibration cron)"
  - "scipy (IRT MLE fit)"
breaking_change_risk: low
---

# LinguaDojo — Technical Specification

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                            Railway                           │
│  ┌────────────────────────────────────────────────────────┐  │
│  │   Flask Application (Gunicorn via Procfile)            │  │
│  │                                                        │  │
│  │  ┌──────────┐  ┌──────────┐  ┌─────────────┐           │  │
│  │  │  Routes  │  │ Services │  │ Middleware  │           │  │
│  │  │ (15 BPs) │  │ (10 dirs)│  │ (Auth/JWT)  │           │  │
│  │  └────┬─────┘  └────┬─────┘  └──────┬──────┘           │  │
│  │       │             │               │                  │  │
│  │  ┌────▼─────────────▼───────────────▼──────────────┐   │  │
│  │  │            Jinja2 Templates                     │   │  │
│  │  │      (HTML + vanilla JS + CSS — no SPA)         │   │  │
│  │  └─────────────────────────────────────────────────┘   │  │
│  │                                                        │  │
│  │  ┌─────────────────────────────────────────────────┐   │  │
│  │  │   APScheduler BackgroundScheduler               │   │  │
│  │  │   irt_calibration_nightly @ 04:00 UTC           │   │  │
│  │  └─────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────┬──────────────┬───────────┬────────────────────┘
               │              │           │
     ┌─────────▼──────┐ ┌─────▼────┐ ┌────▼─────────┐
     │   Supabase     │ │ OpenRouter│ │ Azure TTS    │
     │ (Postgres 17 + │ │ + OpenAI │ │ (Speech SDK) │
     │  Auth + RLS)   │ │ (LLMs)   │ │              │
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
| **Backend** | Python 3.11 / Flask 2.x | Gunicorn WSGI via Procfile |
| **Frontend** | Jinja2 + vanilla JS + CSS | Server-rendered, no SPA framework |
| **Database** | PostgreSQL 17 via Supabase | 64 tables, RLS on ~36 of them, 77 application RPCs (plus extension functions) |
| **Auth** | Supabase Auth (OTP) + JWT | Custom middleware validates Supabase JWTs; service-role bypass for batch jobs |
| **AI / LLM** | OpenRouter primary, OpenAI for moderation + embeddings | Per-task model assignment lives in `prompt_templates.model` (single source of truth as of 2026-05-05) |
| **TTS** | Azure Cognitive Services | `dim_languages.tts_voice_ids` jsonb is the voice catalogue per language. Chinese voices seeded 2026-05-12. |
| **File Storage** | Cloudflare R2 | Audio at `audio.linguadojo.com`. Deterministic slugs for idempotent re-renders. |
| **Payments** | Stripe | Token purchase packages. Webhook handler not yet wired in the prod app — verify before claiming end-to-end. |
| **Hosting** | Railway | Deployed via Procfile (`web: gunicorn wsgi:app`). |
| **NLP** | jieba, langdetect, unidic, pypinyin | Chinese/Japanese tokenization, language detection, pinyin |
| **Cron** | APScheduler `BackgroundScheduler` (in-memory) | Nightly IRT calibration. Cross-worker safety via Postgres advisory lock. |
| **IRT** | scipy.optimize.minimize (L-BFGS-B) | 2PL MLE fitter in `services/irt/calibrator.py` |
| **FSRS** | `services/vocabulary/fsrs.py` (Python) mirrors the SQL `fsrs_schedule_review` | 4.5 algorithm |

## Application Structure

```
WebApp/
├── app.py                     # Flask factory create_app(); registers blueprints, scheduler
├── admin_app.py               # Local-only variant — mounts admin_local_bp + model_arena_bp
├── wsgi.py                    # Production WSGI entry point
├── config.py                  # Unified Config from env vars
├── Procfile                   # Railway deployment
├── requirements.txt
├── db_schema_live.sql         # Snapshot of live DB schema (not authoritative — use Supabase)
│
├── middleware/
│   └── auth.py                # jwt_required / admin_required / tier_required + AuthMiddleware class
│
├── routes/                    # 15 Flask Blueprints + 2 admin-only
│   ├── auth.py                # /api/auth — OTP login, refresh, profile
│   ├── tests.py               # /api/tests — comprehension tests (1126 lines)
│   ├── exercises.py           # /api/exercises — daily mixed session (Phase 9 RPC-backed)
│   ├── vocab_dojo.py          # /api/vocab-dojo — per-word ladder + gates + stress test
│   ├── flashcards.py          # /api/flashcards — FSRS review
│   ├── vocabulary.py          # /api/vocabulary — word quiz submission
│   ├── corpus.py              # /api/corpus — ingest, packs, style packs
│   ├── mystery.py             # /api/mystery — 5-scene murder mystery
│   ├── conversations.py       # /api/conversations — read-only browse
│   ├── users.py               # /api/users — ELO, tokens, prefs
│   ├── payments.py            # /api/payments — token packages + Stripe PaymentIntent
│   ├── reports.py             # /api/reports — bug reports
│   ├── vocab_admin.py         # /api/admin/vocab — admin word upload + preview
│   ├── admin_local.py         # /admin/* — pipeline dashboard (only via admin_app.py)
│   └── model_arena.py         # /admin/arena/* — head-to-head model comparison
│
├── services/                  # Business logic (10 packages + 14 top-level files)
│   ├── ai_service.py          # OpenAI client wrapper (moderation, embeddings)
│   ├── auth_service.py        # OTP send/verify, profile, session
│   ├── dimension_service.py   # Cached dim_* lookups + parse_language_id
│   ├── exercise_session_service.py  # Daily session orchestrator (Phase 9, slim)
│   ├── llm_output_cleaner.py  # JSON-extract / repair from LLM responses
│   ├── llm_service.py         # OpenRouter LLM client
│   ├── mystery_service.py     # Mystery progress + scene + finale submission
│   ├── payment_service.py     # Stripe + token RPC wrappers
│   ├── pinyin_service.py      # Pypinyin pipeline + sandhi engine
│   ├── prompt_service.py      # prompt_templates loader (model/provider lookup)
│   ├── r2_service.py          # Cloudflare R2 uploads
│   ├── service_factory.py     # ServiceFactory(Config) — OpenAI client wiring
│   ├── supabase_factory.py    # SupabaseFactory — get_supabase / get_supabase_admin
│   ├── task_runner.py         # run_in_thread + is_task_stopped (admin SSE backend)
│   ├── test_service.py        # Test fetch + ELO summary + daily load
│   │
│   ├── test_generation/       # Comprehension test pipeline (orchestrator, agents, db_client)
│   ├── topic_generation/      # Topic discovery + embedding dedup pipeline
│   ├── exercise_generation/   # 21 exercise types — orchestrator, generators/, validators
│   │   └── audio_voice.py     # Language-aware Azure voice picker (2026-05-12)
│   ├── conversation_generation/  # Personas + pairs + scenarios + dialogues
│   ├── mystery_generation/    # Mystery story + scene + question agents
│   ├── vocabulary/            # NLP: pipeline, FSRS, knowledge_service (BKT), frequency
│   ├── vocabulary_ladder/     # Phase 8/10 momentum bands + asset pipeline + renderer
│   ├── corpus/                # Ingestion, collocation extraction, style analysis, packs
│   ├── model_arena/           # Head-to-head LLM comparison (arena_service, judge_prompts)
│   └── irt/                   # Phase 11 — 2PL MLE calibrator (scipy.optimize)
│
├── templates/                 # Jinja2 — 18 templates
├── static/                    # css/, js/, i18n/
├── migrations/                # 55+ SQL migrations, append-only
├── models/                    # Pydantic request schemas
├── utils/                     # validation, responses, question_validator
├── prompts/                   # Static fallback prompts (live prompts in prompt_templates)
├── scripts/                   # Standalone CLI batch tools (backfill_*.py, run_*.py, seed_*.py)
├── data/
│   └── arena_runs/            # Persisted Model Arena results (JSON)
├── tests/                     # Python tests
└── wiki/                      # This wiki (CLAUDE.md, MEMORY.md, etc.)
```

## Background Scheduler

[app.py:201](../../app.py#L201) — `_initialize_scheduler(app)` boots an APScheduler `BackgroundScheduler(timezone='UTC')` per worker. Currently one job:

| Job ID | Trigger | Function | Notes |
|--------|---------|----------|-------|
| `irt_calibration_nightly` | `CronTrigger(hour=4, minute=0)` | `services.irt.calibrator.calibrate_all_active_languages` | `coalesce=True, max_instances=1, replace_existing=True`. Cross-worker safety via `irt_try_lock` advisory lock — duplicate fires across gunicorn workers exit cleanly. |

Disable via `DISABLE_SCHEDULER=true` (tests, one-off CLI runs).

## Key Architectural Decisions

1. **Server-rendered with client-side interactivity.**
   - Rationale: Simpler deployment, no separate frontend build, fast enough for the current feature set.
   - Alternatives rejected: SPA (React/Vue) — added complexity without clear benefit for this content-heavy product.

2. **Supabase as database + auth.**
   - Rationale: Managed PostgreSQL with built-in auth, RLS, and real-time. Reduces infrastructure management.
   - Alternatives rejected: Self-hosted Postgres + custom auth — more ops burden.

3. **OpenRouter for LLM routing.**
   - Rationale: Single API, multiple providers. Per-task model assignment (e.g. Qwen for Chinese, Gemini for English prose, Claude for distractor generation) is stored on `prompt_templates.model`.
   - Alternatives rejected: Direct OpenAI — less model flexibility. (OpenAI is still used for moderation + embeddings.)

4. **DimensionService caching.**
   - Rationale: Languages, test types, question types, complexity tiers rarely change. Cached at startup via service-role client to avoid repeated DB calls and bypass RLS.

5. **SQL-first BKT + session selection (Phases 7, 8, 9, 11).**
   - Rationale: Atomic, race-safe, single source of truth. Python is a thin wrapper around `get_exercise_session` / `get_ladder_session` / `ladder_record_attempt` / `process_test_submission`. Reduces drift between transactional updates and read paths.

6. **prompt_templates is the single source of truth for LLM model selection** (refactor 2026-05-05).
   - The legacy `dim_languages.{prose,question,exercise,conversation,vocab_prompt[1-3]}_model` columns were dropped. Every generator now resolves its model via `prompt_service.get_template_config(task_name, language_id)`.

7. **APScheduler in-memory + advisory-lock concurrency** for nightly jobs.
   - Rationale: Simpler than a persistent jobstore (no Redis/PG queue layer). The lock makes duplicate fires harmless; observability comes from logs.

## Environment Variables

Loaded from `.env` via `config.py`:

- **Supabase** — `SUPABASE_URL`, `SUPABASE_KEY` (anon), `SUPABASE_SERVICE_ROLE_KEY`
- **LLM** — `OPENROUTER_API_KEY`, `USE_OPENROUTER`, `OPENAI_API_KEY`
- **TTS** — `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`
- **Storage** — `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_ENDPOINT_URL`
- **Payments** — `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- **App** — `SECRET_KEY`, `JWT_SECRET_KEY`, `FLASK_DEBUG`, `PORT`
- **Scheduler** — `DISABLE_SCHEDULER` (opt-out for tests)

## Admin Pipeline Dashboard

The admin dashboard is the operator interface for content generation pipelines. It is **not a user-facing feature** — it lives only in the local admin variant (`admin_app.py`) and is not registered by production `app.py`.

### Mounting

```python
# admin_app.py
from app import create_app
from routes.admin_local import admin_local_bp
from routes.model_arena import model_arena_bp

app = create_app()
app.register_blueprint(admin_local_bp, url_prefix='/admin')
app.register_blueprint(model_arena_bp, url_prefix='/admin/arena')
```

### Architecture

- Entry point: `admin_app.py`
- Route file: [routes/admin_local.py](../../routes/admin_local.py) (~1186 lines, 10 pipeline tabs + reference data lookups)
- Template: [templates/admin_dashboard.html](../../templates/admin_dashboard.html)
- JavaScript: [static/js/admin-dashboard.js](../../static/js/admin-dashboard.js) — vanilla JS event wiring + SSE consumption
- Background tasks: [services/task_runner.py](../../services/task_runner.py) — `run_in_thread()` spawns daemon threads with `QueueLogHandler` for log streaming
- Stop mechanism: `is_task_stopped()` checks a `threading.Event`; frontend POSTs `/admin/api/task-stop/<task_id>` to set it

### Pipeline Tabs (10)

| Tab | Endpoint | Runner | Purpose |
|-----|----------|--------|---------|
| Corpus Ingestion | `POST /admin/api/run/corpus-ingest` | `CorpusIngestionService` | URL/text → tokenise, extract collocations, optional style analysis |
| Topic Generation | `POST /admin/api/run/topic-generation` | `TopicGenerationOrchestrator` | Auto-generate or insert topics + queue for languages |
| Test Generation | `POST /admin/api/run/test-generation` | `TestGenerationOrchestrator` | Drain `production_queue` |
| Exercise Generation | `POST /admin/api/run/exercise-generation` | `run_grammar_batch` / `run_vocabulary_batch` / `run_collocation_batch` | Per-source-type batches |
| Style Analysis | `POST /admin/api/run/style-analysis` | `CorpusIngestionService._run_style_pipeline` | Style profile extraction |
| Conversations | `POST /admin/api/run/conversation-generation` | `ConversationBatchProcessor` | Per-domain dialogue batches |
| Mysteries | `POST /admin/api/run/mystery-generation` | `MysteryGenerationOrchestrator` | Murder mystery batches |
| Pinyin Backfill | `POST /admin/api/run/pinyin-backfill` | `pinyin_service.process_passage` | Recompute `tests.pinyin_payload` |
| Full Pipeline | `POST /admin/api/run/full-pipeline` | 6-step orchestrator | End-to-end per-language idempotent chain |
| Vocab Generate | `POST /admin/api/run/vocab-generate` | `VocabAssetPipeline` + `LadderExerciseRenderer` + AudioSynthesizer | Per-sense L1-L8 ladder build |
| L1 Audio Backfill | `POST /admin/api/run/l1-audio-backfill` | `AudioSynthesizer` + `audio_voice.pick_voice` | Regenerate audio_url on active L1 exercises |
| IRT Calibration | `POST /admin/api/run/irt-calibration` | `services.irt.calibrator.calibrate_language` | 2PL MLE fit of `irt_difficulty` / `irt_discrimination` |

(That's 12 listed but two — Vocab Generate and L1 Audio Backfill — share the Vocab Browser tab; the dashboard nav lists 10 distinct tabs.)

### Full Pipeline (per-language, single click)

All steps idempotent; sequential with stop checks between each.

1. **Vocab Backfill** (`VocabBackfillRunner`) — extract vocab from unprocessed tests; create `dim_vocabulary` + `dim_word_senses`; write `vocab_sense_ids` + `vocab_token_map` to tests.
2. **Token Map Backfill** (`TokenMapBackfillRunner`) — fill missing `vocab_token_map` with `create_missing=True`.
3. **Question Sense IDs** — match vocab lemmas against question text/choices, write per-question `sense_ids[]`.
4. **Test Skill Ratings** — create `test_skill_ratings` rows for tests lacking them.
5. **Exercise Backfill** — generate exercises for senses + patterns + style items without exercises.
6. **Collocation Exercises** — generate exercises for collocations without exercises.

### Model Arena (separate tab on the same page)

[routes/model_arena.py](../../routes/model_arena.py) — head-to-head OpenRouter model comparison. Blind-judged across prose generation and comprehension questions; persisted to `data/arena_runs/<task_id>.json`. See [[features/model-arena.tech]].

### Vocab Preview

[routes/vocab_admin.py](../../routes/vocab_admin.py) — blueprint at `/api/admin/vocab` (registered in production `app.py`, not just admin_app.py). Page route `/admin/vocab-preview` renders `admin_vocab_preview.html`. ⚠ No auth decorators on the blueprint handlers — relies on deployment posture.

## Related Pages

- [[overview/project]] — What LinguaDojo is and the user-facing story
- [[database/schema]] — Data model overview
- [[database/schema.tech]] — Full DDL: tables, columns, FKs, indexes, triggers, policies
- [[database/rpcs.tech]] — All Postgres RPCs with signatures and SQL
- [[api/rpcs]] — API design philosophy
- [[api/rpcs.tech]] — Full endpoint reference (all 15 blueprints + admin + core + web)
- [[features/language-packs.tech]] — Pack generation pipeline
- [[features/vocab-dojo.tech]] — Vocab ladder + gates + stress test
- [[features/exercises.tech]] — Daily mixed session
- [[features/model-arena.tech]] — Model Arena admin tool
- [[features/exercise-generation-prompts]] — Verbatim P1/P2/P3 prompt templates
