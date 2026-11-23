---
title: LinguaDojo — Technical Specification
type: schema-tech
status: complete
prose_page: ./project.md
last_updated: 2026-11-23
dependencies:
  - "Supabase (PostgreSQL 17 + Auth + RLS + Storage bucket `exercise-content`)"
  - "Flask 3.0 + Gunicorn (2 workers x 8 threads)"
  - "Flask-Limiter, Flask-Compress, Flask-Cors"
  - "OpenRouter (LLM inference, multi-model routing)"
  - "OpenAI (moderation + embeddings)"
  - "Azure Cognitive Services (TTS for listening tests + vocab L1)"
  - "Cloudflare R2 (audio storage)"
  - "Stripe SDK (configured at start-up; no payment route is registered)"
  - "Railway (hosting)"
  - "APScheduler 3.11 (nine nightly/weekly jobs, `web/scheduler.py`)"
  - "scipy / numpy (IRT 2PL fit)"
breaking_change_risk: low
open_questions:
  - "OPEN: the 04:20 UTC watchlist sweep is believed to fail every night (its state table and lock functions are absent live; verified by reading the code and by `to_regclass` / `pg_proc` on 2026-11-23, but the production log of the job was not read). Apply `migrations/word_upload_sweep_advisory_lock_hardened.sql` (it needs a decision on the watermark seed, see `migrations/PENDING-2026-11-23.md`)."
  - "OPEN: the test-suite counts below (6,287 passed, 16 skipped, 0 failed) were reported from a fresh offline run by the coordinating agent; this page's author did not re-run the suite."
  - "OPEN: `type: schema-tech` is the closest allowed value in CLAUDE.md section 8 for an overview tech page (there is no `overview-tech`); consider adding one to the schema."
  - "OPEN: the Python version in production is not recorded in the repository (CI uses 3.13; there is no `runtime.txt`); confirm what Railway runs."
---

# LinguaDojo — Technical Specification

Verified 2026-11-23 against the merged code at commit `0d345e98` and, for the database, read-only against the live project. Companion pages: [[api/rpcs.tech]] (every route), [[features/web-package.tech]] (`web/`), [[features/routes-tests-package.tech]] (`routes/tests/`).

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                            Railway                           │
│  gunicorn wsgi:app  --workers 2 --worker-class gthread       │
│                     --threads 8 --timeout 120   (Procfile)   │
│  ┌────────────────────────────────────────────────────────┐  │
│  │   Flask app (app.create_app), one per worker process   │  │
│  │                                                        │  │
│  │  web/            pages, error envelope, security       │  │
│  │                  headers, rate limits, scheduler       │  │
│  │  routes/         20 route modules (routes/tests/ is    │  │
│  │                  a package)                            │  │
│  │  middleware/     JWT + tier decorators                 │  │
│  │  services/       business logic, engines, pipelines    │  │
│  │  templates/ + static/   Jinja2 shells + vanilla JS     │  │
│  │                                                        │  │
│  │  APScheduler BackgroundScheduler (UTC), 9 jobs, one    │  │
│  │  per worker; each job serialises itself across         │  │
│  │  workers (advisory lock or idempotent upsert)          │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────┬──────────────┬───────────┬────────────────────┘
               │              │           │
     ┌─────────▼──────┐ ┌─────▼────┐ ┌────▼─────────┐
     │   Supabase     │ │OpenRouter│ │ Azure TTS    │
     │ Postgres 17 +  │ │ + OpenAI │ │              │
     │ Auth + Storage │ │ (LLMs)   │ │              │
     └────────────────┘ └──────────┘ └──────────────┘
               │
     ┌─────────▼──────┐
     │ Cloudflare R2  │   (audio files)
     └────────────────┘
```

Offline work (content generation, backfills, evaluation) runs from `scripts/` and the `services/*generation*` packages on a developer machine or through the batch-service token (ADR-014); there is no admin web app any more.

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Backend** | Python / Flask 3.0.3 | Gunicorn gthread, 2 workers x 8 threads (`Procfile`). CI runs Python 3.13. |
| **Frontend** | Jinja2 shells + vanilla ES-module JS + CSS | Server-rendered shells, client-side rendered pages; mobile app shell ([[decisions/ADR-048-mobile-app-shell]]); four locales (`static/i18n/{en,es,ja,zh}.json`). No SPA framework, no bundler. Bootstrap, Font Awesome and Bootstrap Icons are self-hosted under `static/vendor/`; Google Fonts is the only third party. |
| **Database** | PostgreSQL 17.4 via Supabase | Live 2026-11-23: 100 tables in `public`, all with RLS on; 214 non-extension functions in `public` (196 non-trigger). |
| **Exercise content** | Supabase Storage bucket `exercise-content` | One immutable JSON file per sense and version; `exercises.content` no longer exists ([[decisions/ADR-049-exercise-content-in-storage]]). |
| **Auth** | Supabase Auth (OTP) + JWT | `middleware/auth.py`; optional local HS256 verification (`SUPABASE_JWT_SECRET`); batch identity via `BATCH_SERVICE_TOKEN` (the service-role key no longer authenticates HTTP requests). Trusted-device and refresh cookies are HttpOnly. |
| **AI / LLM** | OpenRouter primary; OpenAI for moderation + embeddings; headless `claude -p` transport for backfills | Per-task model assignment in `prompt_templates.model`. |
| **TTS** | Azure Cognitive Services | `dim_languages.tts_voice_ids` is the voice catalogue. |
| **File storage** | Cloudflare R2 | Audio at `audio.linguadojo.com`. |
| **Payments** | Stripe SDK configured at start-up | **No payment route besides `GET /api/payments/token-packages`.** `POST /api/payments/create-intent` was removed; it returns with a verified webhook ([[api/rpcs.tech]]). |
| **Hosting** | Railway | `Procfile`: `web: gunicorn wsgi:app ...`. |
| **NLP** | jieba, pypinyin, fugashi/unidic, pyopenjtalk, wordfreq | Segmentation, pinyin, furigana, pitch accent, frequency. |
| **Cron** | APScheduler `BackgroundScheduler` (in memory) | Nine jobs, below. |
| **IRT** | scipy `minimize` (L-BFGS-B) | `services/irt/calibrator.py`. |
| **FSRS** | `services/vocabulary/fsrs.py` | The scheduler in use; the SQL `fsrs_schedule_review` is not an exact port. |

## Application Structure (package layout at HEAD, line counts by script)

Counts are physical lines of `.py` (or the extension noted) found 2026-11-23, `__pycache__` and `static/vendor/` excluded.

| Path | Files / lines | What it is |
|---|---|---|
| `app.py`, `wsgi.py`, `config.py` | 359 / 14 / 593 | `create_app()` factory and the four inline core routes; the WSGI entry point; the single `Config` class read from environment variables. |
| `web/` | 6 files / 504 | App wiring extracted from `app.py`: `pages.py` (page routes), `errors.py` (error envelope and 404 redirect), `security.py` (headers, report-only CSP, body-size limit), `rate_limits.py`, `scheduler.py`. See [[features/web-package]]. |
| `routes/` | 27 files / 7,400 | One Flask blueprint per module: `auth`, `calibration`, `corpus`, `drills` (builds two blueprints), `dt_repair`, `dual_translation` (2,482 lines), `flashcards`, `knowledge`, `payments`, `practice`, `reports`, `study_plan`, `study_session`, `test_intros`, `users`, `vocab_admin`, `vocab_dojo`, `vocabulary`, `word_list_import`, the package `tests/` (6 files / 1,398 lines; [[features/routes-tests-package]]) and the helper `common.py`. |
| `middleware/` | 2 files / 389 | `auth.py`: `jwt_required`, `admin_required`, `tier_required`, `get_optional_user_id`, token cache and revocation. |
| `models/`, `utils/` | 3 / 227, 5 / 423 | Pydantic request models; response helpers (`responses.py`), validation, question and answer normalisation. |
| `services/` | 257 files / 73,441 | All business logic. 49 top-level modules (auth, test, study plan, attempts, prestudy, calibration, knowledge snapshots, LLM client, Supabase factory, static assets, ...) plus the packages below. |
| `services/practice/` | 5 / 2,711 | Practice engine internals: session assembly, attempt recording, new-word admission; entry point `services/practice_session_service.py`. |
| `services/study_session/` | 3 / 1,113 | Daily session queue composition and its reads/writes. |
| `services/dual_translation/` | 32 / 12,344 | Dual-translation grader cascade, passage and sentence-reference builders, cards, synthesis, guided repair (`repair/`). |
| `services/vocabulary/` | 25 / 5,363 | BKT knowledge service, FSRS, knowledge report, frequency, segmenters. |
| `services/vocabulary_ladder/` | 44 / 13,632 | Ladder service, asset pipeline, exercise renderer, batteries, speed round, queue drain, fat-seed authoring. |
| `services/exercise_content/` | 6 / 2,118 | Storage-backed exercise content store, writer, cache (ADR-049). |
| `services/exercise_generation/`, `test_generation/`, `topic_generation/` | 26 / 4,709; 17 / 6,912; 13 / 2,711 | Generation pipelines (exercises, comprehension tests, topics). |
| `services/corpus/`, `dictation/`, `irt/`, `word_list_import/` | 12 / 2,859; 4 / 502; 2 / 364; 6 / 1,119 | Corpus ingestion and style analysis; dictation grading; IRT calibration; word-list upload and the watchlist sweep. |
| `services/classifier_curation/`, `counter_curation/` | 5 / 202; 5 / 272 | Offline authoring tools for the measure-word and counter drills. |
| `services/model_arena/` | 3 / 123 | Only `llm_runner.py` and `pricing.py`, still imported by the dual-translation grader (`call_model_with_usage`, `fetch_model_list`). The Model Arena itself (routes, UI, runs) is gone. |
| `templates/` | 25 html / 2,722 | One Jinja2 shell per page (list in [[api/rpcs.tech]]). |
| `static/` | js 61 files / 28,212; css 19 / 13,779; `i18n/` 4 json; `vendor/` | Vanilla JS (`pages/`, `session/`, `prestudy/`), styles, locales, self-hosted libraries. |
| `migrations/` | 386 `.sql` (47 under `archive/`) | Append-only SQL; `migrations/CLAUDE.md` holds the rules and `PENDING-2026-11-23.md` the not-yet-applied list. |
| `scripts/` | 120 py / 36,290 | Standalone CLI tools (backfills, seeding, evaluation, sweeps, `dt_nightly_synthesis.py`). |
| `tests/` | 296 py / 77,202 | pytest suite (287 top-level test modules plus `unit/`, `sql/`, `e2e/` (Playwright, not pytest)). Hermetic: see below. |
| `playwright/`, `playwright.config.js`, `vitest.config.js`, `eslint.config.js` | — | Frontend test and lint configuration. |
| `data/`, `prompts/`, `Corpuses/`, `Portal/`, `Project Knowledge/`, `sandbox/`, `scratch_offline/`, `raw/` | — | Working data, static fallback prompts, corpora, unrelated side projects (`Portal/` is excluded from ruff), experiments. Not part of the served app. |
| `wiki/` | — | This wiki. |

There is no local admin app, admin-dashboard or Model Arena route module, exercises, mystery or conversations route module, task-runner service or exercise-session service any more.

## Script write convention

A script under `scripts/` that can write to the live database or Storage writes nothing unless `--apply` is given: a bare run is a dry run, `--dry-run` is accepted as an explicit alias, and `--apply --dry-run` together exits with code 2. The flags come from `scripts/_common.base_parser` (or `add_apply_flags` for one sub-command, as for `exercise_stage_runner.py render`), and `tests/test_scripts_apply_convention_guard.py` fails when a script defines `--dry-run` itself. Exempt, each with its reason in the guard's allowlist: the generation runners whose run is the write (`run_generation_batch.py`, `run_test_generation_cli.py`, `run_ladder_from_existing.py`, and `dt_nightly_synthesis.py`, which the scheduler runs in-process), `dt_rewrite_history_v6.py` (its own four-mode group, already dry run by default), the retired `backfill_gloss_definitions.py`, and five scripts that write only local files. Scripts that write by design with no dry-run flag at all (for example `render_existing_assets.py`, `build_calibration_distractor_cache.py`, `Corpuses/verify_collocations.py`) are listed under TASK-1218 in [[tasklist/review-2026-11-22.tasks]] (2026-11-23).

## Background Scheduler

`web/scheduler.py` declares the jobs as one table (`JOBS`, `Job` dataclass) and `init_scheduler(app)` starts a `BackgroundScheduler(timezone='UTC')` once per process (`coalesce=True`, `max_instances=1`, `replace_existing=True`). It is skipped when `DISABLE_SCHEDULER` is `1`/`true`/`yes` or when the app is created with `TESTING`. With two gunicorn workers there are two schedulers; every job serialises itself across processes (a Postgres advisory-lock pair, or an idempotent upsert) and a job that crashes is logged, never raised. Each job thread gets the longer batch timeout (`SUPABASE_JOB_TIMEOUT`, 120 s).

| Job id | Schedule (UTC) | Target | What it does |
|---|---|---|---|
| `dt_error_synthesis_nightly` | daily 03:50 | `scripts.dt_nightly_synthesis:run_nightly_synthesis` | Clusters the day's `dt_error_instance` rows into `dt_error_profile_entry` and queues error cards, before the morning's first request; advisory lock. |
| `irt_calibration_nightly` | daily 04:00 | `services.irt.calibrator:calibrate_all_active_languages` | 2PL fit of `irt_difficulty` / `irt_discrimination` for every active language; lock `irt_try_lock`. |
| `exercise_time_estimate_refresh` | daily 04:05 | `services.study_plan_service:_refresh_exercise_time_estimates` | RPCs `refresh_practice_time_estimates` (p50 seconds per exercise type and test type, last 30 days, at least 30 samples) and `refresh_new_word_minutes`. |
| `slug_health_nightly` | daily 04:10 | `services.model_health:run_slug_health_check` | Probes the model slugs in use; logs an ERROR naming dead ones; advisory lock. |
| `generation_queue_drain_nightly` | daily 04:15 | `services.vocabulary_ladder.queue_drain:run_nightly_drain` | Enqueues fresh coverage gaps, then drains the generation queue; advisory lock. |
| `word_upload_watchlist_sweep_nightly` | daily 04:20 | `services.word_list_import.sweep_cron:run_watchlist_sweep` | Scans tests created since a watermark and matches them to active `user_word_watchlist` rows. **Currently fails every night:** its state table `word_upload_sweep_state` and its two lock functions do not exist live (checked 2026-11-23); `_read_cursor` raises on the missing table and the runner logs "Word-upload watchlist sweep crashed". Nothing is written. Fix: apply `migrations/word_upload_sweep_advisory_lock_hardened.sql` (pending, needs a watermark-seed decision; `migrations/PENDING-2026-11-23.md` item 9). |
| `knowledge_snapshots_nightly` | daily 04:25 | `services.knowledge_snapshots:run_nightly` | One `user_knowledge_snapshots` row per active (user, language) pair for the UTC day, then prune; idempotent upsert; not gated by `KNOWLEDGE_REPORT_ENABLED` (history must accrue before the page ships, ADR-053). |
| `placement_close_stale_nightly` | daily 04:30 | `services.calibration_placement:run_nightly_close` | Closes placements idle for 24 h as `abandoned`, with a frozen result and the evidence write; skipped while `PLACEMENT_ENABLED_LANGS` is empty. |
| `study_plan_weekly_recompute` | Sundays 23:00 | `services.study_plan_service:_run_weekly_plan_recompute` | `compute_weekly_plan` for every `user_study_plans` row; advisory lock `pg_try_advisory_lock_for_study_plan`. |

The order inside the 04:xx chain is deliberate (comments in `web/scheduler.py`): slug health after IRT, queue drain after the slug probe, the sweep after regeneration, snapshots after the sweep.

## Quality gates

| Gate | Command | State at HEAD |
|---|---|---|
| Python lint | `ruff check .` (rule set `F`, pyflakes; `pyproject.toml`, excludes `archive Portal raw wiki data sandbox scratch_offline node_modules`) | **Zero findings and a blocking CI step** (`.github/workflows/ci.yml`, no `continue-on-error`). |
| Python tests | `python -m pytest -q` | CI job `pytest` (Python 3.13, placeholder Supabase keys, `DISABLE_SCHEDULER=true`). Reported from a fresh offline run: **6,287 passed, 16 skipped, 0 failed**. |
| Frontend | `npm run check` = `lint` (ESLint on `static/js`) + `lint:css` (stylelint) + `format:check` (prettier) | Local gate. CI job `frontend` runs `npm run lint` and `npm run test:unit` (Node 22). |
| Frontend unit tests | `npm run test:unit` (vitest, happy-dom) | CI. |
| End to end | `npm run test:e2e` (Playwright) | `.github/workflows/e2e.yml`, manual (`workflow_dispatch`), needs real secrets. |

**The pytest suite is hermetic.** `tests/conftest.py` sets `LINGUADOJO_SKIP_DOTENV`, pops the credential variables out of the environment before `Config` reads them, and an autouse fixture refuses to build a real Supabase client: a test that touches Supabase fails unless it is marked `live` (selected only with `-m live`) or supplies a fake. `tests/test_suite_hermeticity.py` guards this. `slow` is the other marker (`-m slow`).

## Feature flags and switches

Read from the environment through `config.py` unless noted. Defaults as in code.

| Setting | Default | Effect |
|---|---|---|
| `STUDY_PLAN_ENABLED` | on | Study-plan orchestration, plan progress counters, `POST /api/study-plan/recompute`. |
| `NEW_WORD_DRILL_ENABLED` | on | New-word drill ([[features/new-word-drill.tech]]). |
| `KNOWLEDGE_REPORT_ENABLED` | **off** | `/api/knowledge/*` answer 404; the `/knowledge` page shows "not available yet". |
| `PLACEMENT_ENABLED_LANGS` | empty (off) | Comma-separated `dim_languages` ids for which the vocabulary placement is on; otherwise `/api/calibration/placement/*` answer 404. |
| `ENTITLEMENTS_ENFORCED` | off | Billing gates log `entitlement_shadow_deny` and serve. |
| `RATELIMIT_ENABLED`, `RATELIMIT_STORAGE_URI`, `RATELIMIT_API_DEFAULT` | on, `memory://`, `300 per minute` | Rate limits ([[features/web-package.tech]]). |
| `DT_GUIDED_REPAIR` | on | Guided self-repair routes; off answers `503 REPAIR_DISABLED`. (`services/dual_translation/repair/settings.py`.) |
| `DT_SINGLE_CALL_GRADER` | on | The single-call generative grader (ADR-044); off goes back to the cascade. Related: `DT_SINGLE_CALL_FREE_TRANSLATION`, `_EXPLAINER`, `_SHOW_LOW_CONFIDENCE` (all off), `_LOG_LLM_CALLS` (on), `_MODEL`, `_FALLBACK_MODEL`. |
| `DT_FRAMEWORK_V2` (on), `DT_TIER3_ARBITER_ENABLED` (off), `DT_TAXONOMY_COLUMNS` (on), `DT_GRADING_ASSET_COLUMNS` (on), `DT_CORRECTION_STYLE` (`experiment`), `DT_DAILY_TOKEN_BUDGET` (20000), `DT_ERROR_CARD_INTERLEAVE_EVERY` (4) | | Dual-translation grading and card behaviour. |
| `DISABLE_SCHEDULER` | unset | Keeps a process from scheduling anything (tests, one-off scripts). |
| `BATCH_SERVICE_TOKEN` | unset (off) | Enables the `service-account` identity for HTTP batch jobs; honoured only by `@jwt_required`. |
| `SUPABASE_JWT_SECRET` | unset | Verify HS256 access tokens locally instead of calling Supabase Auth. |
| `LINGUADOJO_SKIP_DOTENV` | unset | `config.py` does not load `.env` (tests, offline tools). |
| `USE_OPENROUTER` | false | LLM transport selection. |

**Removed and ignored if set:** `PRACTICE_ATTEMPT_RPC_ENABLED` (practice attempts are always recorded by the one RPC `record_exercise_attempt`), `QUIZ_DISTRACTORS_BATCH` (the post-test quiz always uses `get_quiz_distractors`, falling back to `get_distractors`), `VOCAB_LADDER_BUNDLE_MODE` (the bundle package was deleted), and the four `EXERCISE_CONTENT_SOURCE/_WRITE/_DB_FALLBACK/_SHADOW_SAMPLE` settings (ADR-049, TASK-1031). A grep of the non-test code finds `QUIZ_DISTRACTORS_BATCH` and `VOCAB_LADDER_BUNDLE_MODE` only in comments.

## Key Architectural Decisions

1. **Server-rendered shells with client-side interactivity.**
   - Rationale: simple deployment, no frontend build, fast enough. The pages are client-side rendered: a route only serves its template.
   - Alternatives rejected: an SPA framework; extra complexity without a clear benefit for this content-heavy product.

2. **Supabase as database + auth + object storage.**
   - Rationale: managed Postgres with auth, RLS and Storage; exercise content moved into Storage to keep the database small ([[decisions/ADR-049-exercise-content-in-storage]]).
   - Alternatives rejected: self-hosted Postgres with custom auth.

3. **OpenRouter for LLM routing.** Per-task model assignment lives on `prompt_templates.model`; OpenAI is used for moderation and embeddings. Alternatives rejected: direct OpenAI only.

4. **DimensionService caching.** Languages, test types and similar rarely change; cached at start-up through the service-role client (also inlined into every page as `window.LINGUA_METADATA`).

5. **SQL-first writes and selection.** Atomic, race-safe, one source of truth: `process_*_submission`, `record_exercise_attempt`, `get_practice_session`, `ladder_*`, `build_daily_session`. Python stays a thin wrapper (FSRS scheduling and the new-word-drill restart are the deliberate exceptions to the attempt RPC).

6. **`prompt_templates` is the single source of truth for LLM model selection** (2026-05-05): generators resolve models through `prompt_service.get_template_config`.

7. **APScheduler in memory + self-serialising jobs.** No persistent jobstore; each job takes its own advisory lock or is an idempotent upsert, so two workers firing the same job is harmless.

8. **Rate limits and request limits at the edge of the app** (`web/rate_limits.py`, `web/security.py`), attached by endpoint name so route modules stay unaware of them.

## Environment Variables

Loaded from `.env` via `config.py` (skipped when `LINGUADOJO_SKIP_DOTENV` is set):

- **Supabase** — `SUPABASE_URL`, `SUPABASE_KEY` (anon), `SUPABASE_SERVICE_ROLE_KEY` (all three required, `Config.validate()`), `SUPABASE_JWT_SECRET`, `SUPABASE_POSTGREST_TIMEOUT` (10 s), `SUPABASE_JOB_TIMEOUT` (120 s)
- **LLM** — `OPENROUTER_API_KEY`, `USE_OPENROUTER`, `OPENAI_API_KEY`, plus per-pipeline tuning (`TEST_GEN_*`, `TOPIC_*`, `DT_*`, `SENSE_*`)
- **TTS** — `SPEECH_KEY`, `SPEECH_REGION`
- **Storage** — `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_ACCOUNT_ID`, `R2_PUBLIC_URL`; `EXERCISE_CONTENT_BUCKET` and its cache/timeout tuning
- **Payments** — `STRIPE_SECRET_KEY` (a webhook secret is not read by any route today)
- **App** — `SECRET_KEY`, `FLASK_DEBUG`, `PORT`, `CORS_ORIGINS`, `MAX_CONTENT_LENGTH` (1 MiB), `BATCH_SERVICE_TOKEN`, `DEVICE_IP_HASH_SALT`, `DAILY_FREE_TOKENS`
- **Scheduler / limits** — `DISABLE_SCHEDULER`, `RATELIMIT_*`

## Removed: the admin dashboard and Model Arena

Earlier versions of this page described a local-only admin app (an `admin_app` entry point, an admin-local route module, ten pipeline tabs streaming progress over SSE through a task-runner service) and a Model Arena (its own route module, `/admin/arena/*`). None of this exists any more: the files, the blueprints and the dashboard's script and template are gone. Content pipelines are run from `scripts/` and the skills in the repository (batch authoring, fat-seed, sense generation), and the vocabulary admin endpoints that remain are the seven `@admin_required` routes under `/api/admin/vocab` plus the page `/admin/vocab-preview` ([[api/rpcs.tech]]). The history of the removed tools is kept in [[features/model-arena.tech]] and the log.

## Related Pages

- [[overview/project]] — What LinguaDojo is and the user-facing story
- [[api/rpcs.tech]] — Full endpoint reference
- [[features/web-package.tech]] — App wiring
- [[features/routes-tests-package.tech]] — The tests route package
- [[database/schema]] — Data model overview
- [[database/schema.tech]] — Full DDL: tables, columns, FKs, indexes, triggers, policies
- [[database/rpcs.tech]] — All Postgres RPCs with signatures and SQL
- [[features/vocab-dojo.tech]] — Vocab ladder, gates, stress test
- [[features/practice-engine.tech]] — The practice engine
- [[features/knowledge-report.tech]], [[features/vocab-placement.tech]] — Knowledge report and placement
