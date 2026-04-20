---
title: API Surface Overview
type: overview
status: in-progress
tech_page: ./rpcs.tech.md
last_updated: 2026-04-10
open_questions: []
---

# API Surface Overview

## Purpose

LinguaLoop's API is a Flask REST API organized into blueprints. All endpoints are prefixed with `/api/` and require JWT authentication (via Supabase Auth) unless noted otherwise. Server-rendered pages call these same endpoints from client-side JavaScript.

## Design Philosophy

- **Blueprint organization** — each domain (auth, tests, exercises, etc.) has its own Flask blueprint
- **Supabase RPC for complex operations** — multi-table transactional operations (test submission, token management) are implemented as plpgsql RPCs called via the Supabase client
- **Simple reads via Python** — list/get operations use the Supabase Python client's query builder
- **JWT middleware** — all authenticated endpoints use `@supabase_jwt_required` decorator

## Blueprint Map

| Blueprint | Prefix | Domain |
|-----------|--------|--------|
| `auth_bp` | `/api/auth` | Login, signup, session management |
| `tests_bp` | `/api/tests` | Comprehension test CRUD and submission |
| `exercises_bp` | `/api/exercises` | Exercise serving and submission |
| `flashcards_bp` | `/api/flashcards` | FSRS review sessions |
| `vocabulary_bp` | `/api/vocabulary` | Vocabulary extraction and lookup |
| `corpus_bp` | `/api/corpus` | Corpus management and pack selection |
| `mystery_bp` | `/api/mystery` | Mystery story serving |
| `conversations_bp` | `/api/conversations` | Conversation browsing |
| `users_bp` | `/api/users` | Profile and settings |
| `reports_bp` | `/api/reports` | Bug reports and feedback |
| `payments_bp` | `/api/payments` | Stripe checkout and webhooks |
| `vocab_dojo_bp` | `/api/vocab-dojo` | Vocab Dojo exercises (new) |
| `vocab_admin_bp` | `/api/admin/vocab` | Admin vocabulary preview |

## Core Routes (Non-Blueprint)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Service health check |
| `/api/config` | GET | Public feature flags |
| `/api/metadata` | GET | Languages and test types |
| `/api/vocabulary/extract` | POST | Vocabulary extraction from text |

## Related Pages

- [[api/rpcs.tech]] — Full endpoint specifications
- [[overview/project.tech]] — Architecture overview
