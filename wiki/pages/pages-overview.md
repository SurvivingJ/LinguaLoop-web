---
title: UI Pages Overview
type: page
status: complete
last_updated: 2026-05-12
open_questions: []
---

# UI Pages Overview

## Purpose

LinguaDojo uses server-rendered Jinja2 templates with vanilla JavaScript for client-side interactivity. Each page is a standalone HTML template served by a Flask route. There is no SPA framework, no client-side router, and no separate frontend build step.

## Page Map

All public pages are registered in `_register_web_routes()` ([app.py:301](../../app.py#L301)). All return rendered HTML; data is fetched client-side via the JWT-authenticated `/api/*` endpoints.

| Route | Template | Purpose | Notes |
|-------|----------|---------|-------|
| `/` | (302 → `/login`) | Root redirect | |
| `/login` | `login.html` | Email OTP login | Calls `/api/auth/send-otp` + `/api/auth/verify-otp` |
| `/signup` | `login.html` | Same template as login | OTP flow with `is_registration=true` |
| `/welcome` | `onboarding.html` | First-time user onboarding | |
| `/language-selection` | `language_selection.html` | Pick target language | Reads `/api/metadata` |
| `/tests` | `test_list.html` | Browse ELO-matched test recommendations | Calls `/api/tests/recommended` + `/api/tests/daily-load` |
| `/test/<slug>/preview` | `test_preview.html` | Test details before starting (vocab map, etc.) | Calls `/api/tests/test/<slug>` |
| `/test/<slug>` | `test.html` | Take a comprehension test | Calls `/api/tests/test/<slug>` then `/api/tests/<slug>/submit` |
| `/test/<slug>/pinyin` | `test_pinyin.html` | Pinyin tone trainer (Chinese only) | Calls `/api/tests/test/<slug>` then `/api/tests/<slug>/submit-pinyin` |
| `/profile` | `profile.html` | ELO summary, token balance, history | Calls `/api/users/elo` + `/api/users/tokens` + `/api/tests/history` |
| `/flashcards` | `flashcards.html` | FSRS review session | Calls `/api/flashcards/due` + `/api/flashcards/review` |
| `/exercises` | `exercises.html` | Daily mixed exercise session | Calls `/api/exercises/session` + `/api/exercises/attempt` |
| `/mysteries` | `mystery_list.html` | Browse available mysteries | Calls `/api/mystery/` + `/api/mystery/recommended` |
| `/mystery/<slug>` | `mystery.html` | Play a 5-scene mystery | Calls `/api/mystery/<slug>`, `/scene/<n>`, `/scene/<n>/submit`, `/submit` |
| `/conversations` | `conversation_list.html` | Browse generated conversations | Calls `/api/conversations/` |
| `/conversation/<id>` | `conversation_reader.html` | Read a single conversation with full turns | Calls `/api/conversations/<id>` |
| `/vocab-dojo` | `vocab_dojo.html` | Vocab Dojo: ladder, gates, stress test | Calls `/api/vocab-dojo/session`, `/attempt`, `/gate`, `/gate/result`, `/stress-test`, `/stress-test/result` |
| `/admin/vocab-preview` | `admin_vocab_preview.html` | Per-word exercise spot-check UI | Calls `/api/admin/vocab/word/<sense_id>/preview` |
| `/logout` | (302 → `/login`) | Frontend clears tokens; server-side just redirects | |

## Admin-only pages (admin_app.py)

Available only when the local admin variant is running. Not registered in production.

| Route | Template | Purpose |
|-------|----------|---------|
| `/admin` | `admin_dashboard.html` | Pipeline dashboard — 10 tabs (corpus, topics, tests, exercises, style, conversations, mysteries, pinyin, full pipeline, vocab generate, L1 audio backfill, IRT calibration) plus a Model Arena tab |

## Shared Template

`base.html` — base template with shared navigation, CSS, JS imports, and the `window.LINGUADOJO` global.

## Client-Side Architecture

- **No SPA framework.** Each page is loaded as a full HTML render; client-side JS uses `fetch()` to talk to `/api/*` endpoints.
- **Auth state** is held in localStorage via the Supabase Auth JS client (`@supabase/supabase-js`). The JWT is included on every API call as `Authorization: Bearer <token>`.
- **i18n** lives in `static/i18n/` — JSON dictionaries per locale. The `window.LINGUADOJO` global exposes the current locale and a `t(key)` helper.
- **Audio** for listening tests, mysteries, and L1 vocab exercises is served from `audio.linguadojo.com` (Cloudflare R2). The frontend constructs `audio_url` from the slug if not pre-computed.
- **Admin dashboard** consumes SSE streams from `/admin/api/task-status/<task_id>` to render live progress.

## Static Assets

```
static/
├── css/        # Stylesheets per page + base.css
├── js/         # Per-page bundles + admin-dashboard.js + exercise-renderers.js (per-type rendering)
└── i18n/       # JSON locale dictionaries
```

`static/js/exercise-renderers.js` is the renderer registry for the 21 exercise types — `renderPhonetic`, `renderCloze`, `renderJumbledSentence`, `renderFlashcard`, etc.

## Related Pages

- [[api/rpcs]] — API endpoints called by pages
- [[api/rpcs.tech]] — Full endpoint reference
- [[overview/project.tech]] — Frontend architecture and deployment
