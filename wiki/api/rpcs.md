---
title: API Surface Overview
type: overview
status: complete
tech_page: ./rpcs.tech.md
last_updated: 2026-11-23
open_questions:
  - "OPEN: The daily free-token grant does not work. `GET /api/users/tokens` calls a database function that does not exist, so it answers an error, and no code grants free tokens. Decide what the token economy should be, then create the function."
  - "OPEN: Buying tokens is off. The payment-intent route was removed because no verified webhook exists to credit the tokens; it comes back with the webhook."
  - "OPEN: Several routes have no caller in this repository (the corpus and admin vocabulary endpoints, the error log, the moderation check, the vocabulary extractor and others, listed in [[api/rpcs.tech]]). Which of them does anything outside the repository use?"
---

# API Surface Overview

## Purpose

LinguaDojo's API is a Flask REST API of 111 endpoints under `/api/`, grouped into 20 route modules (one per domain: auth, tests, practice, study plan and session, dual translation and its guided repair, calibration and placement, knowledge report, flashcards, drills and so on), plus 24 page routes that only serve an HTML shell. There is no separate admin application and no `/admin/*` API: the few operator endpoints live under `/api/admin/vocab` and `/api/corpus` and require an admin account. The pages are rendered in the browser: each page loads its template and then calls the same API as any other client.

## Design Philosophy

- **One module per domain, thin handlers.** A route module checks who is calling, validates the input, calls a service and shapes the answer. The rules live in `services/`, where they can be tested without HTTP.
- **The database does the atomic work.** Anything that must change several tables at once or must not race (grading and recording a test, recording a practice answer, moving a word on the ladder, building the day's session) is one Postgres function called through the Supabase client. For a practice answer the whole recording is a single call; only the spaced-repetition scheduling and its penalty stay in Python.
- **The server decides, the client reports.** The server never trusts the client for who the user is, whether an answer was right (typed answers are re-graded; test answers are checked in the database), whether a battery was passed (batteries are signed and re-scored) or how long something took (timestamps are validated and clamped).
- **Simple reads stay simple.** Lists and lookups use the Supabase query builder directly; hot reads are cached in process for a short time.
- **Failures look the same everywhere.** Under `/api/`, every error (including a wrong URL or an oversized body) is a JSON object with `status`, `error` and a stable `error_code`; unknown page URLs send the visitor to the login page. The auth routes are the older exception: they use their own `success`/`error` bodies.
- **Cost and abuse are limited centrally.** Every API route has a default rate limit per user (or per IP when anonymous); sign-in, language-model-backed and admin routes have stricter ones, and a request body over 1 MiB is refused before any handler runs. Because the app runs as two worker processes with in-memory counters, a client can reach roughly twice each limit unless the counters are moved to Redis.
- **Features can be switched off without a deploy.** The knowledge report, the placement test, guided repair and similar features answer "not found" or "turned off" when their flag is off, and the pages show a "not available" notice.

## What the API covers

| Area | What a learner can do |
|---|---|
| Sign-in | Request an emailed code, verify it, stay signed in on a remembered device, sign out. |
| Tests | List and open tests, take them (reading, listening, dictation, pinyin, pitch accent), see history, study a test's key words beforehand, see its sentences with translations. |
| Daily session and practice | Get today's ordered session, practice items, extra rounds and a speed round; submit each answer; pass the gate and stress-test batteries. |
| Study plan | Read and change daily minutes, modules and new-word settings. |
| Flashcards and drills | Review due cards; do the measure-word and counter drills. |
| Dual translation | Get a passage, submit a translation, repair mistakes with hints, review error cards and see the error profile. |
| Vocabulary check, placement and report | Measure vocabulary on a frequency scale, take the adaptive placement, read "My vocabulary". |
| Word lists | Upload words and watch their status. |
| Account | Preferences, native language, reports to the team. |
| Operators | Admin-only vocabulary and corpus endpoints. |

## What was removed

Mysteries, conversations and language packs were archived on 2026-09-21; the daily exercises endpoints were folded into the practice and study-session endpoints; the local admin dashboard and the Model Arena were deleted; the payment-intent endpoint was removed because there is no way yet to confirm a payment. The listening lab no longer exists as a feature.

## Authentication

Every API route except sign-in, the token package list, the health check, the public configuration and metadata, and the public reading of a test requires `Authorization: Bearer <token>`. The server derives the user from the token; the client cannot set it. A separate batch token (ADR-014) lets scripts call HTTP routes as a service identity; it works only on ordinary authenticated routes and is refused on admin routes. The old rule that the Supabase service key also authenticated requests no longer applies.

See [[api/rpcs.tech]] for the complete reference: every route, its handler, its auth, the database functions and tables it reaches, and the places where it deviates from these rules.

## Related Pages

- [[api/rpcs.tech]] — Full endpoint specifications (all 137 routes)
- [[overview/project]] — What LinguaDojo is
- [[overview/project.tech]] — Architecture, packages, scheduler, gates
- [[features/web-package]] — How the app is wired
- [[features/routes-tests-package]] — The tests route package
- [[database/rpcs.tech]] — Postgres functions called by the API
