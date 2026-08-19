# LinguaDojo Wiki Index
Last updated: 2026-08-17 (**Answer-entailment judge A/B completed; campaign system deferred** — 7 models scored against gold labels on 450 items. The advertised 5–10× cost saving **does not exist**: measured best case is 2.74×, and two candidates are *dearer* than the incumbent despite lower list prices, because output-token volume dominates. Three models fail invisibly — `glm-4.7-flash` returns empty content on 47% of calls, which in production becomes a silent accept-everything no-op. The `json_object` 400 landmine was **latent, not active** as previously recorded, and its zh/ja migration is now applied live. No model promotions applied — recommendations await a decision. A generalised 200-model campaign system was designed and **deferred**: zh is already saturated (top four within 0.01 AUC) and TASK-723's Likert migration would invalidate two of its six metric modules. See [[evaluations/entailment-judge-model-ab-2026-08-17]], [[features/judge-eval-campaign]] and `wiki/log.md` 2026-08-17) | Pages: 103

Prior: 2026-08-16 (**Distractor judge language divergence analysed** — the v4 Likert judge's 30% zh reject rate is mostly a judge artefact, not weaker zh content; the review-queue channel is English-only because `qwen3.6-flash` never emits the middle band. Two prompt slots are dead in production (`keywords` never passed, `type_code` printed but never acted on) and band 1 has never fired in 450 distractors. Filed TASK-717–722. See [[evaluations/distractor-judge-language-divergence-2026-08-16]] and `wiki/log.md` 2026-08-16) | Pages: 101

Prior: 2026-08-12 (**Exercise Generation v2 batch closed** — TASK-521 sense-embedding backfill (22,348 senses, 100%), TASK-530 Japanese counter drill (route/template/both modes/nav/i18n + curation), TASK-531 audio backfill (100% coverage), TASK-534 exercise-type effectiveness view + admin page. TASK-526/535/536 **deferred** with unblock conditions recorded; TASK-515 still open — wall-clock bound, not spend bound. Four silent-inertia defects fixed: NULL `cost_usd` disarming every budget ceiling, a band-check RPC signature that never existed, an `asset_type` CHECK rejecting all typed-LLM assets, and a per-type audio-field mismatch. See `wiki/log.md` 2026-08-12) | Pages: 99

## Overview
- [[overview/project]] — What LinguaLoop is and why it exists
- [[overview/project.tech]] — Tech stack, architecture, admin pipeline dashboard

## Features
- [[features/judge-eval-campaign]] — Repeatable multi-model judge screening (dataset + funnel + HTML report) — **PLANNED / DEFERRED 2026-08-17**
- [[features/judge-eval-campaign.tech]] — Tiered funnel, pre-flight gate, metric modules, deferral rationale
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
- [[features/dual-translation]] — **NEW 2026-06-23 (planned)**: L1→L2 back-translation practice; noticing/diff loop; explained errors + spaced remediation
- [[features/dual-translation.tech]] — Feature 1 (grading): data model, OpenRouter cascade, rubric, RPCs
- [[features/dual-translation-remediation.tech]] — Feature 2: error synthesis, FSRS cards, recurrence instrumentation

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
- [[algorithms/translation-grading-cascade]] — **NEW 2026-06-23**: Tier-0-deterministic-first grading ladder for dual translation
- [[algorithms/translation-grading-cascade.tech]] — Tiers, OpenRouter slugs, prompt caching, budget guardrails
- [[algorithms/evidence-first-grading]] — **NEW 2026-07-04 (planned)**: DT grading v2 — scores computed from severity-weighted errors (MQM), Detector/Verifier split, 3-layer explanations, eval harness; research-grounded
- [[algorithms/evidence-first-grading.tech]] — Full v2 spec: derived scoring formulas, taxonomy v5, complete Detector/Verifier/Explainer prompts (EN/ZH/JA), rollout phases
- [[algorithms/daily-session-implementation-analysis]] — **NEW 2026-07-05**: Daily training pipeline audit — 4 verdicts (HTML ready-ish; 6 types covered; scheduling broken ×3; no interleaving)
- [[algorithms/daily-session-implementation-analysis.tech]] — Findings F1–F16 with file/line evidence and fix sketches (weekly seeding, 0-ms practice, silent hydration shortfall, …)

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
- [[pages/study-session]] — **NEW 2026-08-07**: the `/session` Daily Session runner — one ordered, interleaved, resumable queue of tests + practice chunks
- [[pages/study-session.tech]] — Queue-composition algorithm (stable seed, round-robin, ≤10-min practice chunks), `/api/study-session` contract, controller state machine, a11y

## Business Rules
- [[business-rules/auth-and-access]] — Auth, roles, access control
- [[business-rules/translation-error-taxonomy]] — **NEW 2026-06-23**: category×source×severity×error-vs-mistake; per-pair subtypes; promotion rule

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
- [[decisions/ADR-014-reference-first-grading]] — **NEW**: deterministic Tier-0 diff before any LLM (reuses dictation grader)
- [[decisions/ADR-015-eager-error-explanations]] — **NEW**: explanations eager/first-class (overrides brief §4.4 lazy)
- [[decisions/ADR-016-per-pair-error-taxonomy]] — **NEW**: per-user L1 → directed-pair taxonomy + per-L1 references
- [[decisions/ADR-017-dual-translation-standalone-l1l2-mvp]] — **NEW**: standalone surface, L1→L2-only MVP, reuse-as-code
- [[decisions/ADR-018-level-neutral-grading]] — **NEW**: level-neutral grading (difficulty controlled at selection); only naturalness is tier-dependent
- [[decisions/ADR-019-evidence-first-scoring]] — **PROPOSED 2026-07-04**: derived (computed) scores from severity-weighted errors; severity triad; Detector/Verifier roles; instance-specific Application explanation layer (revises ADR-015)
- [[decisions/ADR-021-plannable-surface-boundary]] — **ACCEPTED 2026-08-07, IMPLEMENTED 2026-08-07**: `flashcards` + `dual_translation` join the daily planner as a new queue `kind='surface'` (not new test types); `listening_lab` + `mystery` deliberately stay outside, pinned by test; dictation's 80-word cap scales with tier. Resolves F11 — both new surfaces are explicitly seeded so neither hits `test_time_estimate`'s silent `ELSE 5.0` (TASK-714 / TASK-715)
- [[decisions/ADR-022-local-day-boundary]] — **ACCEPTED 2026-08-07, IMPLEMENTED 2026-08-07**: the daily load rolls over at the learner's local midnight via `user_study_plans.timezone` (UTC fallback), not UTC. Resolves F15 — one shared helper (`services/day_boundary.py` + SQL twin `plan_local_date`) replaced three independent derivations; `week_start_date` moved with it; no backfill (TASK-716)
- [[decisions/ADR-020-late-symbolic-resolution-must-fail-safe]] — **PROPOSED 2026-07-15**: a slug referencing an independently versioned artifact must never fall back into the value space (`enum[0]`); analyses the TASK-637 JA `particle` bug as the 4th instance of one class; proposes fail-safe resolution, a cross-artifact reference test, and `requires_taxonomy_version` pinning

## Task Lists
- [[tasklist/master]] — **Rebuilt 2026-07-13**: incomplete tasks only, cross-checked against the live codebase + Supabase (found Practice Engine Merger and Study Plans nearly fully shipped but unchecked — see the file's "Recently confirmed complete" section)
- [[tasklist/distractor-judge-calibration.tasks]] — **NEW 2026-08-16** (TASK-717–722): fix the distractor judge's two dead prompt slots (`keywords` never passed, `type_code` never acted on), settle judge-harshness vs content-quality with a cross-model A/B, split the rating onto two axes, redefine the review band as uncertainty, give the 18 generator prompts a distractor spec, and rewrite the zh/ja vocab prompts natively. Start at TASK-717.
- [[tasklist/ladder-numeric-keys.tasks]] — **Complete 2026-08-11** (TASK-537–540): numeric-key JSON contract live on all 16 ladder prompts, so English field names no longer contaminate ZH/JA generation; + worked examples (incl. the JA polysemy rule), provider-enforced JSON, judge-polarity regression test. `prompt_version` stayed at 1
- [[tasklist/archive/master-pre-2026-07-13-audit]] — Prior master.md snapshot, superseded
- [[tasklist/archive/practice-merger.tasks]] — Practice Engine merger task breakdown (11/12 done; only TASK-111 open) — archived
- [[tasklist/archive/study-plans.tasks]] — Study Plans task breakdown (19/20 done; only TASK-220 open) — archived
- [[tasklist/archive/ladder-judge-layer.tasks]] — Ladder Judge Layer (Phase 4) — **fully complete**, archived
- [[tasklist/archive/exercise-generation-v2.tasks]] — Exercise Generation v2 (TASK-501–536): consolidation, JA bootstrap, capability matrix, batch run, CJK depth — archived. **2026-08-12:** 521/530/531/534 closed; **526** deferred (needs `content.hant` mirrors from TASK-509's backfill over batch senses), **535** deferred (needs ~50k attempts + TASK-534 data), **536** deferred (needs launch-volume distractor pick-rates); **515** open — ~9 h per 100-sense chunk at ~$0.024/sense
- [[tasklist/archive/language-packs.tasks]] — Language Packs task breakdown (blocked, design resolution needed) — archived
- [[tasklist/archive/dual-translation.tasks]] — Dual Translation (TASK-600–620): 4-stage build — grading MVP, error synthesis, spaced remediation, localisation (TASK-609 confirmed done in the audit) — archived
- [[tasklist/archive/evidence-first-grading.tasks]] — DT Grading v2 (TASK-621–649): measure → prompts → structural → UX + hardening batch; implements ADR-019 — archived
- [[tasklist/archive/daily-session-hardening.tasks]] — Daily Session hardening (TASK-700–713): weekly seeding, practice timing, shortfall telemetry, interleaving, retry slots, UX/a11y — archived

## Lessons
- [[lessons/windows-process-and-network-tools]] — netstat / tasklist / taskkill / wmic — find what owns a port, what command launched a PID, and how to kill stale processes

## Evaluations
- [[evaluations/distractor-judge-language-divergence-2026-08-16]] — **NEW 2026-08-16**: why the v4 distractor judge rejects 30% of zh vs 4% of en, and why the review queue is English-only. Three independent causes: qwen3.6-flash collapses the scale to {5,4,2} (no middle band, and **zero** band-1 ratings in 450 distractors — the "also correct" case has never fired); the scale conflates topical distance with answer-confusability; and the "same subject" rubric is a category error for `vocabulary_context`/`author_purpose`. The judge prompts are faithful translations — prompt drift is ruled out. ~6 of 7 non-vocab zh rejects are **false** rejects. Separately: the zh/ja vocab generator prompts few-shot on English idioms (`'pick up the pieces'`), and no generator prompt in any language contains any distractor guidance. Rejects do **not** queue — review load is 2.7%, not 18%.
- [[evaluations/dt-grading-v2-2026-07-19]] — Evidence-First v2 final eval (TASK-632): Detector/Verifier + derived scoring + rubric v6 candidate; EN span F1 .941 / clean FP .000 / overall QWK .824, JA .880/.100/.419, ZH per page; per-phase progression 622→632; `DT_FRAMEWORK_V2` flipped ON on this pass; v6 live apply owed (TASK-629).
- [[evaluations/dt-grading-baseline-2026-07-05]] — DT grading v1 baseline (TASK-622): Tier-0 near-exact gate resolved 83/90 gold items (all 45 single-error seeds) to full marks before detection; recall is the floor (EN .222 / JA .111 / ZH .000), overall-band QWK EN .516 / JA .186 / ZH .000, clean-FP 0.000 across all L2s; regression floor for TASK-623+.
- [[evaluations/exercise-pipeline-eval-2026-06-09]] — `services/exercise_generation` EN vocab pipeline eval: configured model `google/gemini-flash-1.5` is 404-delisted + missing/inactive templates (dead on arrival); once unblocked, 59% accept / 27% reject over 160 EN exercises (tl_nl_translation degenerate, semantic_discrimination mislabels valid English); cloze judge ships rejected distractors anyway. ZH unmeasured (qwen 429).

## Reviews
- [[reviews/code-review-2026-05-24]] — Python code review of main backend (4 CRITICAL incl. missing Stripe webhook; 9 HIGH; 12 MEDIUM; 5 redundancies). **CR-03 and CR-04 patched 2026-05-24** (commit `8989b0bf`); CR-01 and CR-02 still open.
- [[reviews/exercise-generation-audit-2026-06-07]] — Vocab-ladder generation audit: root cause of 小熊's 0-exercise failure (language-blind `morphological_forms >= 2` gate), 7 latent bugs (destructive regen, English-centric validation, broken non-English corpus extraction), and a prompting-infra audit (judge coverage 1/6 levels; monolith prompts; per-language capability matrix; prompt-per-exercise split).
