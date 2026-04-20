---
title: What Is LinguaLoop
type: overview
status: in-progress
tech_page: ./project.tech.md
last_updated: 2026-04-10
open_questions:
  - "Subscription tiers beyond free — what features are gated? (translation practice, vocab tracking mentioned)"
---

# What Is LinguaLoop

## Purpose

LinguaLoop is a web application for active foreign-language practice. It targets translators, test-preparation candidates, and general language learners who want to be *tested and scored*, not just shown flashcards. The system progressively matches material to the edge of each learner's current ability so that every session is challenging but achievable.

## User Story

A learner signs up, picks a target language, and is immediately presented with comprehension tests matched to their estimated skill level. As they answer, the system refines its estimate via an ELO rating and a Bayesian vocabulary-knowledge model. Over time the platform surfaces harder material, tracks which words and grammar the learner struggles with, and generates targeted exercises to close gaps.

Beyond individual tests, learners can study **Language Packs** — themed bundles of simulated conversations (e.g. "Soccer", "Economics", "AI") that teach vocabulary and grammar in context. A Pack walks the learner through word study, contextual exercises, conversation snippets with comprehension questions, and final full-conversation comprehension tests.

## Core Learning Loop

1. **Assess** — comprehension tests (reading or listening) with 5 multiple-choice questions establish the learner's ELO and vocabulary knowledge.
2. **Diagnose** — the system identifies words, phrases, and grammar patterns the learner does not yet know confidently (via BKT probability model).
3. **Practise** — targeted exercises (cloze, translation, jumbled sentence, collocation, semantic, etc.) drill weak areas.
4. **Review** — FSRS-scheduled flashcards resurface words at optimal intervals.
5. **Progress** — as the learner's ELO rises, harder tests and richer Packs are surfaced.

## Key Features

| Feature | Status | Description |
|---------|--------|-------------|
| Comprehension Tests | Working | Reading and listening MC tests, ELO-matched |
| ELO Ranking | Working | Dual-ELO system rating both users and tests |
| Vocabulary Knowledge (BKT) | Working | Bayesian knowledge tracing per word sense |
| Flashcards (FSRS) | Working | Spaced-repetition review cards |
| Exercises | Working | 9+ exercise types generated from grammar, vocab, and collocations |
| Language Packs | In Progress | Themed conversation bundles with word study + exercises |
| Mysteries | Working | Murder-mystery stories gated by comprehension questions per scene |
| Conversation Generation | Working | Simulated dialogues used as corpus for word/phrase extraction |
| Corpus Analysis | Working | NLP pipeline extracting collocations, frequency data, style patterns |
| Token Economy | Working | Free daily tests + purchasable tokens |
| Vocab Dojo | Planned | Adaptive exercise serving for passive + active word acquisition |

## Who Uses It

- **Individual learners** (current focus) — sign up, pick a language, start practising.
- **Schools / language institutes** (future B2B) — organizations with teacher and student roles, shared token pools.

## Content Creation

All content is system-generated via LLM pipelines. There is no user-generated or CMS-authored content. Generation is manually triggered by an admin.

## Related Pages

- [[overview/project.tech]] — Tech stack, architecture, deployment
- [[features/comprehension-tests]] — Test engine details
- [[features/language-packs]] — Pack system design
- [[algorithms/elo-ranking]] — ELO algorithm
