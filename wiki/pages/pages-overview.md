---
title: UI Pages Overview
type: page
status: in-progress
last_updated: 2026-04-10
open_questions: []
---

# UI Pages Overview

## Purpose

LinguaLoop uses server-rendered Jinja2 templates with vanilla JavaScript for client-side interactivity. Each page is a standalone HTML template served by a Flask route.

## Page Map

| Route | Template | Purpose |
|-------|----------|---------|
| `/` | (redirect) | Redirects to `/login` |
| `/login` | `login.html` | Email/password login + signup |
| `/signup` | `login.html` | Same template as login |
| `/welcome` | `onboarding.html` | New user onboarding flow |
| `/language-selection` | `language_selection.html` | Pick target language |
| `/tests` | `test_list.html` | Browse ELO-matched test recommendations |
| `/test/<slug>/preview` | `test_preview.html` | Test details before starting |
| `/test/<slug>` | `test.html` | Take a comprehension test |
| `/profile` | `profile.html` | User profile and stats |
| `/flashcards` | `flashcards.html` | FSRS review session |
| `/exercises` | `exercises.html` | Exercise practice session |
| `/mysteries` | `mystery_list.html` | Browse available mysteries |
| `/mystery/<slug>` | `mystery.html` | Play a mystery story |
| `/conversations` | `conversation_list.html` | Browse conversations |
| `/conversation/<id>` | `conversation_reader.html` | Read a conversation |
| `/vocab-dojo` | `vocab_dojo.html` | Vocabulary dojo (new) |
| `/admin/vocab-preview` | `admin_vocab_preview.html` | Admin vocab preview |
| `/logout` | (redirect) | Redirects to `/login` |

## Shared Template

`base.html` — base template with shared navigation, CSS, and JS imports.

## Client-Side Architecture

Pages use vanilla JavaScript with `fetch()` calls to `/api/*` endpoints. Authentication state is managed via Supabase Auth JS client stored in localStorage/cookies.

## Related Pages

- [[api/rpcs]] — API endpoints called by pages
- [[overview/project.tech]] — Frontend architecture
