# LinguaDojo Wiki Index
Last updated: 2026-06-11 (exercise-generation v2 design plan — see log.md 2026-06-11) | Pages: 75

## Overview
- [[overview/project]] — What LinguaLoop is and why it exists
- [[overview/project.tech]] — Tech stack, architecture, admin pipeline dashboard

## Features
- [[features/practice-engine]] — Unified vocabulary practice surface (Acquisition + Maintenance modes; merges Exercises + Vocab Dojo) — **NEW 2026-05-21**
- [[features/practice-engine.tech]] — get_practice_session RPC, unified-score SQL, candidate pools, parity tests
- [[features/study-plans]] — Per-language weekly/daily orchestrator across Tests and Practice budgets — **NEW 2026-05-21**
- [[features/study-plans.tech]] — Tier B/C tech spec, schema, RPCs, rollout, worked example
- [[features/comprehension-tests]] — Reading/listening MC tests with vocab-based recommendations
- [[features/comprehension-tests.tech]] — Test engine technical spec (now plan-driven when STUDY_PLAN_ENABLED)
- [[features/dictation]] — Listen + type the full transcript; per-word BKT signal
- [[features/dictation.tech]] — Grader, RPC, replay K-multiplier, inline diff UI
- [[features/language-packs]] — Corpus-first themed study bundles (current priority)
- [[features/language-packs.tech]] — 7-stage pack generation pipeline
- [[features/exercises]] — **DEPRECATED 2026-05-21** — merged into [[features/practice-engine]] (legacy generation pipeline still canonical here)
- [[features/exercises.tech]] — **DEPRECATED 2026-05-21** — session-time selection moved to practice-engine.tech
- [[features/exercise-generation-prompts]] — Verbatim text of vocab pipeline Prompts 1/2/3
- [[features/exercise-generation-v2]] — **Design plan (2026-06-11)**: unified vocab exercise factory — ladder pipeline as sole vocab generator, capability matrix, 20-type taxonomy, JA bootstrap, 4-phase roadmap
- [[features/vocabulary-knowledge]] — BKT vocabulary tracking with FSRS-informed decay
- [[features/vocabulary-knowledge.tech]] — BKT formula, transit parameter, decay model, inference mechanisms
- [[features/flashcards]] — FSRS spaced-repetition review (now a Maintenance sub-type)
- [[features/flashcards.tech]] — FSRS technical spec
- [[features/mysteries]] — Murder mystery stories gated by comprehension
- [[features/mysteries.tech]] — Mystery generation and serving
- [[features/conversations]] — Simulated dialogue generation for corpus
- [[features/conversations.tech]] — Two-step scenario generation (Matrix Builder + Expander)
- [[features/corpus-analysis]] — NLP pipeline for collocation extraction
- [[features/corpus-analysis.tech]] — Corpus analysis technical spec
- [[features/token-economy]] — Token-based access and Stripe payments
- [[features/token-economy.tech]] — Payment flow technical spec
- [[features/vocab-dojo]] — **DEPRECATED 2026-05-21** — merged into [[features/practice-engine]]
- [[features/vocab-dojo.tech]] — **DEPRECATED 2026-05-21** — get_ladder_session is now a wrapper
- [[features/pinyin-trainer]] — Chinese tone-guessing game mode with sandhi rules
- [[features/pinyin-trainer.tech]] — Pypinyin pipeline, token schema, submit-pinyin endpoint
- [[features/pitch-accent-trainer]] — Japanese pitch-accent game mode (heiban/atamadaka/nakadaka/odaka), Quick + Contour renderers
- [[features/pitch-accent-trainer.tech]] — pyopenjtalk pipeline, mora segmentation, pitch_payload schema, submit-pitch-accent endpoint
- [[features/furigana-overlay]] — Opt-in hiragana ruby annotations on kanji for Japanese tests (with ELO dampener)
- [[features/furigana-overlay.tech]] — fugashi + UniDic generation, payload schema, render path, dampener wiring
- [[features/measure-word-trainer]] — Chinese classifier (量词) infinite drill, MC + Typed modes, curated dictionary
- [[features/measure-word-trainer.tech]] — dim_classifiers schema, session RPC, sentinel-test ELO pattern
- [[features/model-arena]] — Admin tool: head-to-head OpenRouter model comparison (prose + questions, blind-judged)
- [[features/model-arena.tech]] — Arena orchestrator, judge rubrics, OpenRouter pricing integration

## Algorithms
- [[algorithms/practice-unified-score]] — Four-signal scoring for the merged Practice Engine — **NEW 2026-05-21**
- [[algorithms/practice-unified-score.tech]] — Per-term normalization, SQL helper, mode weights, candidate pools
- [[algorithms/study-plan-adaptation]] — Weakness-signal + Thompson bandit + greedy resolver — **NEW 2026-05-21**
- [[algorithms/study-plan-adaptation.tech]] — Formulas, constants, Tier B/C pseudocode
- [[algorithms/elo-ranking]] — Dual-ELO system for user-test matching (feeds Study Plan weakness signal)
- [[algorithms/elo-ranking.tech]] — ELO formula, volatility, recommendation
- [[algorithms/elo-implementation-analysis]] — ELO implementation audit: volatility bug, recommendation gaps, improvements
- [[algorithms/elo-implementation-analysis.tech]] — ELO technical analysis with fix code
- [[algorithms/vocabulary-ladder]] — 10-level receptive-to-productive word acquisition (feeds Practice Engine ladder term)
- [[algorithms/vocabulary-ladder.tech]] — Nation's framework, promotion/demotion, POS routing
- [[algorithms/bkt-implementation-analysis]] — BKT implementation audit: transit, FSRS decay, inference, session RPC (Phase 5+7)
- [[algorithms/bkt-implementation-analysis.tech]] — BKT technical analysis: 9 SQL functions, architecture map, improvement status
- [[algorithms/ladder-implementation-analysis]] — Ladder/exercise audit (Priority-1 integration gap resolved by Practice Engine merger 2026-05-21)
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
- [[decisions/ADR-006-retry-slot-reduced-elo]] — Reduced-volatility ELO on daily-load retry-slot repeats (time-decay factor + improvement bonus)
- [[decisions/ADR-007-merge-exercises-vocab-dojo]] — Merge into a unified Practice Engine with mode-dependent anchoring — **NEW 2026-05-21**
- [[decisions/ADR-008-study-plan-orchestration-layer]] — Add a cross-surface orchestrator with Tier B/C
- [[decisions/ADR-009-two-budget-tests-vs-practice]] — Tests vs Practice budgets + internal Maint/Acq split
- [[decisions/ADR-010-value-weighted-thompson-skill-mix]] — Value-weighted Thompson sampling for weekly test allocation
- [[decisions/ADR-011-per-language-independent-budgets]] — Per-language independent plan rows
- [[decisions/ADR-012-grammar-items-excluded-v1]] — Grammar/style items deferred from V1 Practice pool
- [[decisions/ADR-013-global-feature-flag-rollout]] — Single global Config flag for rollout + immediate-flip strategy

## Task Lists
- [[tasklist/master]] — All tasks, current status
- [[tasklist/practice-merger.tasks]] — Practice Engine merger task breakdown — **NEW 2026-05-21**
- [[tasklist/study-plans.tasks]] — Study Plans task breakdown
- [[tasklist/ladder-judge-layer.tasks]] — Ladder Judge Layer (Phase 4): per-level + P1 judges, reject-rate dashboard — **NEW 2026-06-07**
- [[tasklist/exercise-generation-v2.tasks]] — Exercise Generation v2 (TASK-501–536): consolidation, JA bootstrap, capability matrix, batch run, CJK depth — **NEW 2026-06-11**
- [[tasklist/language-packs.tasks]] — Language Packs task breakdown

## Lessons
- [[lessons/windows-process-and-network-tools]] — netstat / tasklist / taskkill / wmic — find what owns a port, what command launched a PID, and how to kill stale processes

## Evaluations
- [[evaluations/exercise-pipeline-eval-2026-06-09]] — `services/exercise_generation` EN vocab pipeline eval: configured model `google/gemini-flash-1.5` is 404-delisted + missing/inactive templates (dead on arrival); once unblocked, 59% accept / 27% reject over 160 EN exercises (tl_nl_translation degenerate, semantic_discrimination mislabels valid English); cloze judge ships rejected distractors anyway. ZH unmeasured (qwen 429).

## Reviews
- [[reviews/code-review-2026-05-24]] — Python code review of main backend (4 CRITICAL incl. missing Stripe webhook; 9 HIGH; 12 MEDIUM; 5 redundancies). **CR-03 and CR-04 patched 2026-05-24** (commit `8989b0bf`); CR-01 and CR-02 still open.
- [[reviews/exercise-generation-audit-2026-06-07]] — Vocab-ladder generation audit: root cause of 小熊's 0-exercise failure (language-blind `morphological_forms >= 2` gate), 7 latent bugs (destructive regen, English-centric validation, broken non-English corpus extraction), and a prompting-infra audit (judge coverage 1/6 levels; monolith prompts; per-language capability matrix; prompt-per-exercise split).
