---
title: API Surface Overview
type: overview
status: complete
tech_page: ./rpcs.tech.md
last_updated: 2026-05-12
open_questions:
  - "Several admin blueprints (vocab_admin, admin_local, model_arena) have no auth decorators — they rely on deployment posture. Worth tightening before exposing publicly."
  - "Stripe webhook handler is not registered — `process_stripe_payment` RPC is unreachable from HTTP today."
---

# API Surface Overview

## Purpose

LinguaDojo's API is a Flask REST API organised into 15 blueprints (13 production + 2 admin-only). All `/api/*` endpoints are prefixed by blueprint; admin endpoints live under `/admin/*` and are mounted only by the local `admin_app.py` variant. Server-rendered Jinja2 pages call these same endpoints from client-side JavaScript.

## Design Philosophy

- **Blueprint organisation** — each domain (auth, tests, exercises, mystery, etc.) has its own Flask blueprint with a single responsibility.
- **Supabase RPC for atomic operations** — multi-table transactional operations (test submission, ELO calculation, token grants, ladder progression) are implemented as plpgsql RPCs called via the Supabase client. Python wrappers stay thin.
- **Simple reads via Python** — list/get operations use the Supabase Python client's query builder with foreign-key joins.
- **Module-level JWT decorators** — all authenticated endpoints use `@jwt_required` (alias `@supabase_jwt_required`); admin tier checks use `@admin_required`; service-role tokens bypass JWT validation for batch jobs.
- **Pydantic for request validation** — request bodies that need strict schemas use `models/requests.py` Pydantic types (`PaymentIntentRequest`, `WordQuizRequest`, `VocabularyExtractRequest`, `ErrorLogRequest`).

## Blueprint Map (Production)

Registered by `app.py` and shipped to Railway.

| Blueprint | Prefix | Domain | Lines |
|-----------|--------|--------|-------|
| `auth_bp` | `/api/auth` | OTP login, refresh, profile | 165 |
| `tests_bp` | `/api/tests` | Comprehension tests + pinyin | 1126 |
| `exercises_bp` | `/api/exercises` | Daily mixed session | 227 |
| `vocab_dojo_bp` | `/api/vocab-dojo` | Per-word ladder, gates, stress test | 418 |
| `flashcards_bp` | `/api/flashcards` | FSRS review | 243 |
| `vocabulary_bp` | `/api/vocabulary` | Post-test word quiz | 42 |
| `corpus_bp` | `/api/corpus` | Corpus ingest, packs, style | 260 |
| `mystery_bp` | `/api/mystery` | 5-scene murder mystery | 284 |
| `conversations_bp` | `/api/conversations` | Read-only conversation browse | 98 |
| `users_bp` | `/api/users` | Profile, ELO summary, tokens, prefs | 131 |
| `reports_bp` | `/api/reports` | Bug reports | 59 |
| `payments_bp` | `/api/payments` | Token packages + Stripe PaymentIntent | 61 |
| `vocab_admin_bp` | `/api/admin/vocab` | Admin word upload + preview | 450 |

## Blueprint Map (Admin-only — `admin_app.py`)

Mounted only by the local admin variant. Not registered in production.

| Blueprint | Prefix | Domain |
|-----------|--------|--------|
| `admin_local_bp` | `/admin` | Pipeline dashboard (10 tabs) + reference data + task SSE |
| `model_arena_bp` | `/admin/arena` | Head-to-head LLM comparison |

## Core Routes (Non-Blueprint, app.py)

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/health` | GET | none | Service health probe |
| `/api/config` | GET | none | Public feature flags + token costs |
| `/api/metadata` | GET | none | Cached `dim_languages` + `dim_test_types` |
| `/api/vocabulary/extract` | POST | JWT | LLM vocab extraction from arbitrary text |
| `/api/errors/log` | POST | JWT | Frontend error logging to `app_error_logs` |

Plus a dozen web routes (`/login`, `/welcome`, `/tests`, `/test/<slug>`, `/profile`, etc.) — all defined inline in `_register_web_routes`.

## Authentication

`Authorization: Bearer <supabase_jwt>` is required on all `/api/*` routes except the public ones noted above. The middleware sets `g.current_user_id` server-side; the client cannot inject this. If the token matches `SUPABASE_SERVICE_ROLE_KEY`, the request runs as a `'service-account'` identity — used by batch scripts.

See [[api/rpcs.tech]] for the complete endpoint reference: every route, its body/query schema, the underlying RPC, and the success/error shapes.

## Related Pages

- [[api/rpcs.tech]] — Full endpoint specifications (all 15 blueprints)
- [[overview/project.tech]] — Architecture, deployment, scheduler
- [[database/rpcs.tech]] — Postgres RPCs called by the API
