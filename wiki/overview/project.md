---
title: What Is LinguaDojo
type: overview
status: complete
tech_page: ./project.tech.md
last_updated: 2026-11-27
open_questions:
  - "OPEN: Payments. Buying tokens is switched off: the payment-intent route was removed because nothing verified a completed payment and credited the tokens. It returns together with a verified Stripe webhook. Until then the only live token-related page of the API is the package list."
  - "OPEN: The daily free tokens are never granted (the database function behind them does not exist), so token balances do not move. Decide the token economy, then create the function."
  - "OPEN: Subscription tiers beyond free — billing is designed ([[tasklist/billing.tasks]]) but not enforced; `ENTITLEMENTS_ENFORCED` is off."
---

# What Is LinguaDojo

> Branding note: the canonical product name is **LinguaDojo** (camel-case), reconciled in [[decisions/ADR-004-brand-name]]. "LinguaLoop" appears throughout some wiki pages and code comments as a historical alias.

## Purpose

LinguaDojo is a web application for active foreign-language practice. It targets translators, test-preparation candidates, and self-directed language learners who want to be *tested and scored*, not just shown flashcards. The system progressively matches material to the edge of each learner's current ability so that every session is challenging but achievable. It works as a phone app first (the mobile app shell, [[decisions/ADR-048-mobile-app-shell]]) and supports Chinese, Japanese and English as study languages.

## User Story

A learner signs up with an emailed one-time code, picks a target language and can start with a short vocabulary check that places them on a word-frequency scale. From then on the app plans a daily session: comprehension tests matched to their level, practice on the words they are learning, flashcard reviews, and, in the same stream, translation tasks. As they answer, the system refines its estimate with a dual-ELO rating (learner and test) and a per-word Bayesian knowledge model. Over time it surfaces harder material, tracks which words the learner struggles with, and shows what they know.

## Core Learning Loop

1. **Place and assess** — An optional vocabulary placement (about 40 to 60 questions) and ongoing comprehension tests (reading, listening, dictation, Chinese pinyin tones, Japanese pitch accent) establish the learner's level and seed the knowledge model for the words tested.
2. **Prepare** — Before a test the learner can study its key words (prestudy), and new words first go through a short criterion-based drill before they enter the ladder.
3. **Practise** — The daily session mixes: the *Practice* engine (due reviews, learning-zone words and new words, drawn from a per-word ladder with gates and a pre-mastery stress test), flashcard review (FSRS), and the measure-word and counter drills.
4. **Produce** — *Dual translation*: the learner reads a passage in their own language and reproduces it in the language they study; the answer is graded and, with guided self-repair, the learner fixes their own mistakes step by step with hints on request; the sentences they could not fix come back in later practice.
5. **Review and progress** — Words that graduate from the ladder become flashcards; the Knowledge Report ("My vocabulary") shows how many words the learner knows and how that grows. As the rating rises, harder tests and richer ladder rings unlock.

## Key Features

| Feature | Status | Description |
|---------|--------|-------------|
| Comprehension tests | Working | Reading, listening, dictation; ELO-matched; test prestudy and a post-test word quiz. |
| Pinyin tone trainer, pitch-accent trainer | Working | Chinese and Japanese game modes. |
| ELO ranking | Working | Dual-ELO with volatility. |
| Vocabulary knowledge (BKT) | Working | Per word sense, with FSRS-stability decay and contextual and frequency inference. |
| Flashcards (FSRS) | Working | Cards seeded from tests and ladder graduation. |
| Practice engine and daily study session | Working | One SQL-backed session (reviews, learning, new words), time-budgeted by the study plan; optional extra rounds and a speed round. |
| Vocab ladder: gates and stress test | Working | Per-word ladder with rings and families; exercise content is stored in Supabase Storage rather than in the database. |
| New-word drill | Working | Short criterion-based sessions before a new word joins the ladder. |
| Study plan and session budget | Working | Per-language daily minutes, modules and new-word settings; weekly recompute. |
| Dual translation with guided self-repair | Working | Translation reproduction graded by a single-call model grader; error profile, error cards, guided self-repair. |
| Measure-word and counter drills | Working | Chinese measure words and Japanese counters, with per-item mastery for Chinese. |
| Word-list import and watchlist | Working | Learners upload up to 50 words; a nightly sweep is meant to match them to new tests (the sweep currently fails, see the technical page). |
| Vocabulary check (calibration) | Working | Infinite multiple-choice check that measures vocabulary on a frequency scale. |
| Vocabulary placement | Working | Adaptive placement test for Chinese, Japanese and English; always on (no switch); reached from the Me page, the empty "My vocabulary" page and the vocabulary check. New learners are offered it during onboarding after "Have you studied {language} before?". |
| Knowledge Report ("My vocabulary") | Working | Summary and growth of the learner's vocabulary; always on (no switch); nightly snapshots accrue history since 2026-11-24. |
| Mobile app shell | Working | One task per screen, themes, shared components. |
| Corpus analysis | Working (operator) | Ingestion, collocation extraction, style profiling, through admin-only endpoints. |
| Token economy | **Not working** | Token packages are listed, but buying is switched off and the daily free tokens are never granted. |
| Mysteries, conversations, language packs | Archived 2026-09-21 | Built but little used; code and data are in `archive/modules/`. |
| Listening lab, Model Arena, the local admin dashboard | Removed | The listening lab and the head-to-head model comparison tool and the local admin app that drove the content pipelines no longer exist. |
| Payments (create a payment) | Removed | The payment-intent route was removed until a verified webhook exists. |

## Who Uses It

- **Individual learners** (current focus) — sign up with an email code, pick a language, start practising.
- **Schools / language institutes** (future B2B) — `organizations` and `organization_members` tables exist but have no current production usage.

## Content Creation

All content is system-generated by LLM pipelines run by the operator from scripts and authoring skills in the repository (there is no user-generated or CMS-authored content, and no web dashboard for it any more). The learner-facing API only reads finished content, apart from the word-list upload, where a learner can ask for exercises for words of their own. Those words are queued and built offline by the operator with the same skills ([[features/word-upload-queue]]); generating them inside the website is a switch, off by default.

## Brand & Theming

Per [[decisions/ADR-004-brand-name]], the canonical brand text is `LinguaDojo`: page title, logo wordmark, the `window.LINGUADOJO` global, the four locales, production subdomains (`audio.linguadojo.com`, `library.linguadojo.com`) and the audio bucket. Some wiki text still says "LinguaLoop" as a historical alias.

## Related Pages

- [[overview/project.tech]] — Tech stack, package layout, scheduler, gates, flags
- [[api/rpcs]] — The API in plain English
- [[features/comprehension-tests]] — Test engine details
- [[features/practice-engine]] — The practice engine
- [[features/vocab-dojo]] — Vocab ladder, gates, stress test
- [[features/dual-translation]], [[features/dt-guided-self-repair]] — Dual translation and guided self-repair
- [[features/new-word-drill]] — New-word drill
- [[features/knowledge-report]], [[features/vocab-placement]] — Knowledge report and placement
- [[pages/app-shell]] — Mobile app shell
- [[features/mysteries]] — Archived mystery system
- [[algorithms/elo-ranking]] — ELO algorithm
- [[algorithms/vocabulary-ladder]] — Phase 8 momentum bands
- [[decisions/ADR-004-brand-name]] — LinguaDojo brand reconciliation
