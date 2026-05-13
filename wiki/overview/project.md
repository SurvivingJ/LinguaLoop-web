---
title: What Is LinguaDojo
type: overview
status: complete
tech_page: ./project.tech.md
last_updated: 2026-05-12
open_questions:
  - "Stripe webhook handler — `process_stripe_payment` RPC exists but no Flask route currently calls it. Verify the live payment flow."
  - "Subscription tiers beyond free — feature gating not enforced in code yet (column flags exist on dim_subscription_tiers)."
---

# What Is LinguaDojo

> Branding note: the canonical product name is **LinguaDojo** (camel-case), reconciled in [[decisions/ADR-004-brand-name]]. "LinguaLoop" appears throughout some wiki pages and code comments as a historical alias.

## Purpose

LinguaDojo is a web application for active foreign-language practice. It targets translators, test-preparation candidates, and self-directed language learners who want to be *tested and scored*, not just shown flashcards. The system progressively matches material to the edge of each learner's current ability so that every session is challenging but achievable.

## User Story

A learner signs up with an emailed OTP, picks a target language, and is immediately presented with comprehension tests matched to their estimated skill level. As they answer, the system refines its estimate via a dual-ELO rating (user-side and test-side) and a per-word Bayesian Knowledge Tracing (BKT) model. Over time the platform surfaces harder material, tracks which words the learner struggles with, and serves targeted exercises through three distinct surfaces — flashcards (FSRS), the daily mixed-session, and the Vocab Dojo word-by-word ladder.

Beyond individual tests, learners can play **Mysteries** — five-scene murder-mystery stories gated by per-scene comprehension questions. They can browse **Conversations** — simulated dialogues used both as study material and as corpus for collocation extraction. **Language Packs** (themed conversation bundles) are in design but not shipped.

## Core Learning Loop

1. **Assess** — Comprehension tests (reading, listening, dictation, or Chinese pinyin-tone) with 5 MC questions establish the learner's ELO and seed BKT for tested words.
2. **Diagnose** — The system identifies words the learner does not yet know confidently (BKT `p_known < 0.5`) and the families they struggle in (form recognition, semantic discrimination, productive use, etc.).
3. **Practise** — Three surfaces target weak areas:
   - **Daily mixed session** (`/exercises`) — 20 items mixing due reviews, learning-zone words, new words, ladder content, and supplementary grammar/collocation. IRT-weighted item selection within sense as of Phase 11.
   - **Vocab Dojo** (`/vocab-dojo`) — per-word ladder through 10 levels organised into 4 rings × 6 cognitive families, with threshold gates and a pre-mastery stress test.
   - **Flashcards** (`/flashcards`) — FSRS-scheduled review cards.
4. **Review** — Words graduating from Vocab Dojo seed FSRS flashcards with bootstrapped stability.
5. **Progress** — As ELO rises, harder tests, deeper mysteries, and richer ladder rings unlock.

## Key Features

| Feature | Status | Description |
|---------|--------|-------------|
| Comprehension Tests | Working | Reading, listening, dictation, pinyin (Chinese). ELO-matched. |
| Pinyin Tone Trainer | Working | Chinese-only game mode with sandhi rules and polyphone resolution. |
| ELO Ranking | Working | Dual-ELO with restored volatility (Phase 3 fix shipped 2026-05-08). |
| Vocabulary Knowledge (BKT) | Working | Per word sense, with FSRS-stability decay, transit parameter, contextual + frequency inference (Phase 7). |
| Flashcards (FSRS) | Working | Spaced-repetition cards seeded from comprehension + ladder graduation. |
| Daily Mixed Session | Working | SQL-RPC backed (Phase 9), IRT-weighted within sense (Phase 11). |
| Vocab Dojo | Working | Phase 8 Momentum Bands + Phase 10 cross-session gating and ring demotion. |
| Exercises | Working | 21 exercise types across 4 cognitive phases, generated from grammar, vocab, collocations, conversations, and style. |
| Mysteries | Working | 5-scene murder mystery stories gated by per-scene comprehension. |
| Conversations | Working | Read-only browse of generated dialogues; used internally as corpus. |
| Corpus Analysis | Working | Ingestion + collocation extraction + style profiling. |
| Model Arena | Working (admin) | Head-to-head OpenRouter model comparison with blind judge. |
| Token Economy | Partial | Free daily tokens + Stripe PaymentIntent endpoint shipped; webhook handler missing. |
| Language Packs | Planned | Themed conversation bundles with word study + exercises. |

## Who Uses It

- **Individual learners** (current focus) — sign up with email OTP, pick a language, start practising.
- **Schools / language institutes** (future B2B) — `organizations` + `organization_members` tables exist but no current production usage.

## Content Creation

All content is system-generated via LLM pipelines orchestrated through the local admin dashboard (`admin_app.py`, not exposed in production). There is no user-generated or CMS-authored content. Operator triggers a pipeline tab; the work runs in a daemon thread; SSE streams progress.

## Brand & Theming

Per [[decisions/ADR-004-brand-name]], the canonical brand text is `LinguaDojo`. Production reflects this in the page title, the logo wordmark, the `window.LINGUADOJO` global, the four i18n locales, production subdomains (`audio.linguadojo.com`, `library.linguadojo.com`), and the R2 audio bucket. Some wiki text still says "LinguaLoop" as a historical alias.

## Related Pages

- [[overview/project.tech]] — Tech stack, architecture, scheduler, admin endpoints, full directory tree
- [[features/comprehension-tests]] — Test engine details
- [[features/vocab-dojo]] — Vocab ladder + gates + stress test
- [[features/exercises]] — Daily mixed session + 21 exercise types
- [[features/mysteries]] — Mystery system
- [[algorithms/elo-ranking]] — ELO algorithm
- [[algorithms/vocabulary-ladder]] — Phase 8 momentum bands
- [[decisions/ADR-004-brand-name]] — LinguaDojo brand reconciliation
