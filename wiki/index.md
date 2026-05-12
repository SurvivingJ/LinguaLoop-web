# LinguaLoop Wiki Index
Last updated: 2026-05-12 (Phase 11 IRT calibration) | Pages: 48

## Overview
- [[overview/project]] — What LinguaLoop is and why it exists
- [[overview/project.tech]] — Tech stack, architecture, admin pipeline dashboard

## Features
- [[features/comprehension-tests]] — Reading/listening MC tests with vocab-based recommendations
- [[features/comprehension-tests.tech]] — Test engine technical spec
- [[features/language-packs]] — Corpus-first themed study bundles (current priority)
- [[features/language-packs.tech]] — 7-stage pack generation pipeline
- [[features/exercises]] — 21 exercise types across 4 phases, age-tier difficulty
- [[features/exercises.tech]] — 3-prompt LLM pipeline, numeric JSON schema, validation
- [[features/exercise-generation-prompts]] — Verbatim text of vocab pipeline Prompts 1/2/3 (current P1 v4 / P2 v2 / P3 v2 active templates + deactivated history)
- [[features/vocabulary-knowledge]] — BKT vocabulary tracking with FSRS-informed decay, contextual + frequency inference
- [[features/vocabulary-knowledge.tech]] — BKT formula, transit parameter, decay model, inference mechanisms
- [[features/flashcards]] — FSRS spaced-repetition review
- [[features/flashcards.tech]] — FSRS technical spec
- [[features/mysteries]] — Murder mystery stories gated by comprehension
- [[features/mysteries.tech]] — Mystery generation and serving
- [[features/conversations]] — Simulated dialogue generation for corpus
- [[features/conversations.tech]] — Two-step scenario generation (Matrix Builder + Expander)
- [[features/corpus-analysis]] — NLP pipeline for collocation extraction
- [[features/corpus-analysis.tech]] — Corpus analysis technical spec
- [[features/token-economy]] — Token-based access and Stripe payments
- [[features/token-economy.tech]] — Payment flow technical spec
- [[features/vocab-dojo]] — Per-word vocabulary ladder serving (ring/family/gate/stress-test progression)
- [[features/vocab-dojo.tech]] — get_ladder_session RPC, priority scoring, gate/stress-test orchestration
- [[features/pinyin-trainer]] — Chinese tone-guessing game mode with sandhi rules
- [[features/pinyin-trainer.tech]] — Pypinyin pipeline, token schema, submit-pinyin endpoint
- [[features/model-arena]] — Admin tool: head-to-head OpenRouter model comparison (prose + questions, blind-judged)
- [[features/model-arena.tech]] — Arena orchestrator, judge rubrics, OpenRouter pricing integration

## Algorithms
- [[algorithms/elo-ranking]] — Dual-ELO system for user-test matching
- [[algorithms/elo-ranking.tech]] — ELO formula, volatility, recommendation
- [[algorithms/elo-implementation-analysis]] — ELO implementation audit: volatility bug, recommendation gaps, improvements
- [[algorithms/elo-implementation-analysis.tech]] — ELO technical analysis with fix code
- [[algorithms/vocabulary-ladder]] — 10-level receptive-to-productive word acquisition
- [[algorithms/vocabulary-ladder.tech]] — Nation's framework, promotion/demotion, POS routing
- [[algorithms/bkt-implementation-analysis]] — BKT implementation audit: transit, FSRS decay, inference, session RPC (Phase 5+7)
- [[algorithms/bkt-implementation-analysis.tech]] — BKT technical analysis: 9 SQL functions, architecture map, improvement status
- [[algorithms/ladder-implementation-analysis]] — Ladder/exercise audit: 9 vs 10 levels, no demotion, competing session builders
- [[algorithms/ladder-implementation-analysis.tech]] — Ladder technical analysis with consolidation proposals

## Database
- [[database/schema]] — Data model overview (10 domains, 62 tables, complete from Supabase)
- [[database/schema.tech]] — Full schema: every table, column, FK, index, trigger, enum, view
- [[database/rpcs.tech]] — All 53 application RPCs with full SQL definitions (Phase 7: +5 BKT functions)

## API
- [[api/rpcs]] — API surface overview (13 blueprints)
- [[api/rpcs.tech]] — Full endpoint specifications
- [[database/rpcs.tech]] — Database-level RPCs (53 functions, full definitions)

## Pages
- [[pages/pages-overview]] — All UI routes and templates

## Business Rules
- [[business-rules/auth-and-access]] — Auth, roles, access control

## Decisions
- [[decisions/ADR-001-dual-elo]] — Dual ELO rating system
- [[decisions/ADR-002-bkt-per-sense]] — BKT at word-sense granularity
- [[decisions/ADR-003-age-tiers]] — Age-tier difficulty replacing CEFR for LLM generation
- [[decisions/ADR-004-brand-name]] — Brand name: LinguaDojo (formal reconciliation of wiki ↔ codebase; alternatives archived)
- [[decisions/ADR-005-momentum-bands]] — Vocabulary ladder switched from first-try counters to family-BKT × rings × gates × stress test (Phase 8)

## Task Lists
- [[tasklist/master]] — All tasks, current status
- [[tasklist/language-packs.tasks]] — Language Packs task breakdown
