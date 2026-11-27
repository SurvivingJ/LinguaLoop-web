---
title: UI Pages Overview
type: page
status: complete
last_updated: 2026-11-16
open_questions: []
---

# UI Pages Overview

## Purpose

LinguaDojo uses server-rendered Jinja2 templates with vanilla JavaScript for client-side interactivity. Each page is a standalone HTML template served by a Flask route. There is no SPA framework, no client-side router, and no separate frontend build step.

## Navigation and Layout (mobile redesign, 2026-11-16)

Every page sits in one app shell ([[pages/app-shell]], [[decisions/ADR-048-mobile-app-shell]]) in
one of three modes:

- **Tab pages** — phones (< 768 px): slim top bar (study-language chip, Report, light/dark toggle) and
  a bottom tab bar: **Today** `/session` · **Practice** `/session?mode=practice` · **Tests** `/tests` ·
  **Me** `/profile`. No hamburger menu, no footer. Wide screens (≥ 768 px): the tabs move into the top
  bar with Calibration, Measure Words (zh) / Counters (ja), Report and the UI-language, theme and
  account menus; the footer returns. These pages scroll normally.
- **Task pages** — one task per screen: Back pill, title/subtitle header, a scrolling stage and a
  pinned action dock; no tabs or top bar; the document never scrolls. `/session` switches into this
  mode at runtime while an item runs.
- **Bare pages** — login and onboarding (`hide_navbar`).

Each row's Notes start with the page's shell mode (*tab*, *task*, *bare*). Everything that left the phone top bar (Study
Plan, Word List, Calibration, drills, Language Selection, DT error profile, theme / appearance /
UI-language pickers, Report, Logout) is linked from the Me page.

## Page Map

All public pages are registered from the `PAGES` table in `web/pages.py` (`register_pages(app)`; `/` and `/logout` redirect to `/login`). All return rendered HTML; data is fetched client-side via the JWT-authenticated `/api/*` endpoints.

| Route | Template | Purpose | Notes |
|-------|----------|---------|-------|
| `/` | (302 → `/login`) | Root redirect | |
| `/login` | `login.html` | Email OTP login | *bare*. Calls `/api/auth/send-otp` + `/api/auth/verify-otp` |
| `/signup` | `login.html` | Same template as login | *bare*. OTP flow with `is_registration=true` |
| `/welcome` | `onboarding.html` | First-time user onboarding | *bare*. |
| `/language-selection` | `language_selection.html` | Pick target language | *task* (reached from the study-language chip and Me). Reads `/api/metadata` |
| `/tests` | `test_list.html` | Browse ELO-matched test recommendations | *tab* (Tests). Calls `/api/tests/recommended` + `/api/tests/daily-load` |
| `/session` | `study_session.html` | **Daily Session runner** — one ordered, interleaved queue of test slots + practice chunks on a single page, resumable | *tab* (Today; Practice with `?mode=practice`) on the start card and summary, *task* at runtime while an item runs (`LinguaShell.setTaskMode`). Calls `GET /api/study-session` (queue) → per-item players; completion via `POST /api/tests/daily-load/complete` (tests) and `POST /api/study-session/complete-block` (practice chunks). See [[pages/study-session]] |
| `/study-plan` | `study_plan.html` | Per-language weekly plan settings (template, daily minutes, weekday shape, skill overrides) | *task* (from Me). Calls `GET/PUT /api/study-plan`, `POST /api/study-plan/recompute`, `GET /api/study-plan/templates` |
| `/test/<slug>/preview` | `test_preview.html` | Test details before starting (vocab map, etc.) | *task*. Calls `/api/tests/test/<slug>` |
| `/test/<slug>` | `test.html` | Take a comprehension test | *task*; reading/listening player puts its clock in the header's right slot. Calls `/api/tests/test/<slug>` then `/api/tests/<slug>/submit` |
| `/test/<slug>/pinyin` | `test_pinyin.html` | Pinyin tone trainer (Chinese only) | *task*. Calls `/api/tests/test/<slug>` then `/api/tests/<slug>/submit-pinyin` |
| `/test/<slug>/pitch-accent` | `test_pitch_accent.html` | Japanese pitch-accent trainer (Quick + Contour) | *task*. Calls `/api/tests/test/<slug>` then `/api/tests/<slug>/submit-pitch-accent` |
| `/test/<slug>/dictation` | `test_dictation.html` | Listen + type the full transcript | *task*. Calls `/api/tests/test/<slug>` then `/api/tests/<slug>/submit-dictation` |
| `/classifier-drill` | `classifier_drill.html` | Chinese classifier (量词) infinite drill, MC + Typed | *task* (from Me / desktop bar, zh only). Calls `/api/classifier-drill/*` |
| `/grammar-drill` | `grammar_drill.html` | Chinese grammar drills: 39 topics, four-stage ladder, Mixed review, Endless ([[features/grammar-drills]]) | *task* (from Me, zh only). Loads `static/data/grammar/zh/*.json`; progress in localStorage, copied to the server through `POST /api/grammar-drill/round` and `GET /api/grammar-drill/progress` (2026-11-27, migration pending; the page works without them) |
| `/dual-translation` | `dual_translation.html` | L1→L2 back-translation practice + graded feedback | *task*. Calls `/api/dual-translation/next` + `/submit` |
| `/dual-translation/profile` | `dual_translation_profile.html` | Ranked error-profile dashboard | *task*, Back = history (from Me). Calls `/api/dual-translation/profile` |
| ~~`/listening-lab`, `/listening-lab/<slug>`~~ **(removed 2026-09-21 — archived)** | `listening_lab_list.html`, `listening_lab.html` | Listening Lab (feature-flagged — registered only when enabled) | |
| `/profile` | `profile.html` | ELO summary, token balance, history | *tab* (**Me**): also the settings hub on phones — Study Plan, Calibration, Word List, DT error profile, Measure Words / Counters, Language Selection, appearance / theme / UI-language pickers, Report, Logout. Calls `/api/users/elo` + `/api/users/tokens` + `/api/tests/history` |
| `/flashcards` | `flashcards.html` | FSRS review session | *task*. Calls `/api/flashcards/due` + `/api/flashcards/review` |
| `/test/<slug>/prestudy` | `test_prestudy.html` | Test prestudy (word prime before a test) | *task*. See [[features/test-prestudy]] |
| `/word-list` | `word_list.html` | Learner's word list | *task* (from Me / desktop user menu). |
| `/calibration` | `calibration.html` | Vocabulary calibration | *task* (from Me / desktop bar). See [[features/calibration]] |
| `/counter-drill` | `counter_drill.html` | Japanese counter drill | *task* (from Me / desktop bar, ja only). |
| ~~`/exercises`~~ | — | **RETIRED 2026-07-14 (TASK-220)** — route + `exercises.html` deleted; practice now lives in the `/session` runner | `/api/exercises/session` 302s to `/api/practice/session` |
| ~~`/mysteries`~~ **(removed 2026-09-21 — archived)** | `mystery_list.html` | Browse available mysteries | Calls `/api/mystery/` + `/api/mystery/recommended` |
| ~~`/mystery/<slug>`~~ **(removed 2026-09-21 — archived)** | `mystery.html` | Play a 5-scene mystery | Calls `/api/mystery/<slug>`, `/scene/<n>`, `/scene/<n>/submit`, `/submit` |
| ~~`/conversations`~~ **(removed 2026-09-21 — archived)** | `conversation_list.html` | Browse generated conversations | Calls `/api/conversations/` |
| ~~`/conversation/<id>`~~ **(removed 2026-09-21 — archived)** | `conversation_reader.html` | Read a single conversation with full turns | Calls `/api/conversations/<id>` |
| ~~`/vocab-dojo`~~ | — | **RETIRED 2026-07-14 (TASK-220)** — route + `vocab_dojo.html` deleted; ladder/gates/stress-test are served by the unified Practice player | `/api/vocab-dojo/session` 302s to `/api/practice/session?mode=acquisition` |
| `/admin/vocab-preview` | `admin_vocab_preview.html` | Per-word exercise spot-check UI | *tab* (base shell; admin). Calls `/api/admin/vocab/word/<sense_id>/preview` |
| `/logout` | (302 → `/login`) | Frontend clears tokens; server-side just redirects | |

## Admin-only pages (admin_app.py)

Available only when the local admin variant is running. Not registered in production.

| Route | Template | Purpose |
|-------|----------|---------|
| `/admin` | `admin_dashboard.html` | Pipeline dashboard — tabs (corpus, topics, tests, exercises, style, pinyin, full pipeline, vocab generate, L1 audio backfill, IRT calibration) plus a Model Arena tab |

## Shared Template

`base.html` — the app shell (since 2026-11-16): tab / task / bare modes, phone top bar and bottom tab bar, desktop top bar, task header (Back pill, title, glyph, end slot) and dock, `#reportModal` / `#nativeLanguageModal` (bottom sheets on phones), shared CSS and JS imports and the `window.LINGUADOJO` global. Task mode is set per page with `{% set task_mode = true %}` and `task_*` / `dock` blocks, or at runtime with `window.LinguaShell`. Full spec: [[pages/app-shell.tech]].

## Client-Side Architecture

- **No SPA framework.** Each page is loaded as a full HTML render; client-side JS uses `fetch()` to talk to `/api/*` endpoints.
- **Auth state** is held in localStorage via the Supabase Auth JS client (`@supabase/supabase-js`). The JWT is included on every API call as `Authorization: Bearer <token>`.
- **i18n** lives in `static/i18n/` — JSON dictionaries per locale. The `window.LINGUADOJO` global exposes the current locale and a `t(key)` helper.
- **Audio** for listening tests and L1 vocab exercises is served from `audio.linguadojo.com` (Cloudflare R2). The frontend constructs `audio_url` from the slug if not pre-computed.
- **Themes** are applied before first paint by `static/js/pages/base-head.js` and managed by `window.LinguaTheme` (`static/js/theme-manager.js`): the default "Dojo" palette (light/dark, follows the system unless forced) plus Still Water, Midnight, Sakura, Forest and Inkstone & Vermilion. See [[pages/app-shell]].
- **Admin dashboard** consumes SSE streams from `/admin/api/task-status/<task_id>` to render live progress.

## Static Assets

```
static/
├── css/        # styles.css (tokens, six themes, shared .ld-* components, Bootstrap restyle),
│               # redesign/*.css (per-area, loaded on every page), pages/*.css, dt-repair.css
├── js/         # Per-page bundles + admin-dashboard.js + exercise-renderers.js (per-type rendering)
└── i18n/       # JSON locale dictionaries
```

`static/js/exercise-renderers.js` is the renderer registry for the 21 exercise types — `renderPhonetic`, `renderCloze`, `renderJumbledSentence`, `renderFlashcard`, etc.

## Related Pages

- [[pages/app-shell]] / [[pages/app-shell.tech]] — the shell, navigation, themes and shared components
- [[decisions/ADR-048-mobile-app-shell]] — why the shell is one task per screen
- [[api/rpcs]] — API endpoints called by pages
- [[api/rpcs.tech]] — Full endpoint reference
- [[overview/project.tech]] — Frontend architecture and deployment
