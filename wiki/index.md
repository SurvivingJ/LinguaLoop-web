# LinguaDojo Wiki Index
Last updated: 2026-08-21 (**TASK-727–730 done — the fail-closed judge guard is wired into test generation, proven to fire, and a 20-test run is measured.** `batch_mode()` — built after two outages where a delisted model slug made judges silently `safe_accept()` everything — covered exercise generation only; test generation never entered it, so a bulk run with a dead slug wrote unjudged questions with nothing louder than a log warning. Now `run()`/`run_batch()` execute inside the guard (two places, not four callers), and **five judge-path `except Exception` handlers re-raise `JudgeUnavailable`** — the real work, since swallowing it would have degraded a loud abort into "that one test quietly failed", *quieter* than the bug it replaces. 14 tests pin it, including that an unresolvable judge template aborts a real batch **writing nothing**, that the serve path still fails open, and that the suite goes **red** when either half of the fix is reverted. Thread fan-out audited: none exists in test generation, so nothing to carry — but that is now an assumption a future parallelisation would silently break. **Measured run: 20/20 tests, $0.175 ($0.00875/test), 3,532 s (2.9 min/test)** → ~$8.75 / ~49 h per 1,000. **Spend is a non-issue at any scale; wall clock is the constraint and 82% of it is vocabulary enrichment for 16% of the spend.** Judges 38.2% of spend, 2 rejects in 163 calls — the *validator* rejected 17. Suite 1869 → **1883 passed**. See [[evaluations/test-gen-20-run-2026-08-21]] and `wiki/log.md` 2026-08-21) | Pages: 109

Prior: 2026-08-20 (**TASK-719 + TASK-720 done — the distractor judge now rates two axes, and the rows are staged, not activated.** The single 1-5 rating split onto **fit** (is this the passage’s subject?) and **confusability** (would a learner take it for the answer?), the verdict arithmetic moved into `schemas.axes_to_verdict` behind named cut points, and band 3 on *both* axes was redefined as **the judge is not confident**, with the triggering axis written into `generation_review_queue`. v7 prompt rows authored in all three languages (zh/ja natively via qwen3.8-max) and landed `is_active = false`. Measured live-vs-v7 on 179 questions, same model in every cell, 358 calls, $0.2738. **Every v7 flag in every language is a confusability flag** — the fit axis produced zero, and went near-binary (zero 3s anywhere; band 4 collapsed zh 47→2, ja 65→2), so fit alone can no longer stand in for the pair. **The also-correct failure turns out to be rare, not newly detectable**: 1/537 against 3/1,800 for the old band 1 — the same rate — so the case for v7 rests on the review signal, not on that catch. Staged because **question-level review volume goes 0-3% → 22-47%**; the code is live-safe against the current v4/v6 rows, so staging costs nothing. *(Follow-up the same day settled the "honest or timid" half by ablation — it is honest, and v4's near-zero rate was the artefact. The open half is whether the right items are in the queue, which still needs TASK-726. See the audit page below.)* Suite 1843 → **1869 passed**. See [[evaluations/distractor-judge-two-axis-2026-08-20]] and `wiki/log.md` 2026-08-20) | Pages: 107

Prior: 2026-08-19 (**TASK-726 machine half done — the distractor gold-set frame exists; only adjudication remains.** 573 items (zh 213 / en 180 / ja 180) drawn from live-stack output, pre-rated by both TASK-718 models, post-stratified to the production question mix, split into primary + 60-item overlap labeller sheets, with the merge / κ-gate / `--gold` scoring harness shipped and unit-tested. **The reject-set disjointness reproduces on fresh content and is worse than on the frozen 150** — qwen rejects 56/573, gemini 3/573, overlapping on 3; across 180 English items the two models agree on **zero** rejects; and of the 55 distractors qwen bands "off-topic, reject", gemini rates **35 of them 5**. Separately, **uniform-by-type sampling has been mis-weighting every rate in this workstream**: reweighting the live judge to the production question mix moves it **0.52% → 0.92%**, so TASK-721’s "0.6% on fresh output" understates production by ~1.8×. What remains is human time, not spend — native zh/en/ja adjudication — and until it lands no judge in this workstream can be scored. Suite 1806 → **1843 passed**. Spend $0.73. See [[evaluations/distractor-gold-frame-2026-08-19]] and `wiki/log.md` 2026-08-19) | Pages: 105

Prior: 2026-08-17 (**Answer-entailment judge A/B completed; campaign system deferred** — 7 models scored against gold labels on 450 items. The advertised 5–10× cost saving **does not exist**: measured best case is 2.74×, and two candidates are *dearer* than the incumbent despite lower list prices, because output-token volume dominates. Three models fail invisibly — `glm-4.7-flash` returns empty content on 47% of calls, which in production becomes a silent accept-everything no-op. The `json_object` 400 landmine was **latent, not active** as previously recorded, and its zh/ja migration is now applied live. No model promotions applied — recommendations await a decision. A generalised 200-model campaign system was designed and **deferred**: zh is already saturated (top four within 0.01 AUC) and TASK-723's Likert migration would invalidate two of its six metric modules. See [[evaluations/entailment-judge-model-ab-2026-08-17]], [[features/judge-eval-campaign]] and `wiki/log.md` 2026-08-17) | Pages: 103

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
- [[tasklist/test-gen-fail-closed-judging.tasks]] — **Complete 2026-08-21** (TASK-727–730): the `batch_mode()` fail-closed judge guard is wired into exercise generation only, so a bulk *test* run with a delisted model slug ships unjudged questions. Wire it at the two orchestrator batch entry points, audit the 15 `except Exception` blocks so `JudgeUnavailable` is not swallowed, prove the guard fires, then measure 20 tests for cost and wall clock. Blocks any large test-generation run.
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
- [[evaluations/test-gen-20-run-2026-08-21]] — **NEW 2026-08-21** (TASK-730): 20 tests end to end with the fail-closed judge guard live. $0.175 ($0.00875/test), 3,532 s (2.9 min/test), 20/20 generated, 0 vocab shortfalls. Spend is a non-issue at scale (~$8.75/1,000 tests); **wall clock is the constraint and 82% of it is vocabulary enrichment, which is 16% of the spend**. Judges 38.2% of spend. Also documents two `llm_calls` query traps beyond the known one
- [[evaluations/distractor-judge-unsure-band-audit-2026-08-20]] — **NEW 2026-08-20**: does the v7 review band report honest doubt, or did the wording make a confident model timid? **Refuted by ablation, in the unexpected direction** — strip every directional cue from the v7 prompt (both the "use 3 if unsure" nudge AND the "5 is the normal expected rating" / "4 is the target" anchors) and hedging **doubles** in all three languages (41 → 83 unsure ratings; en 5 → 22). v7's wording is *net anti-hedging*, so its 22-47% review rate is a **floor** on this model's uncertainty, not an inflation — and the anomaly was always **v4's near-zero rate**, manufactured by its own anchor. Two further findings: **temperature 0 is not deterministic** (ja moved 30% between identical runs, so the two-axis page's per-language rates carry ±3pp), and the nudge does not change *how much* the judge hedges but does change *what lands there* — band-3 reasons hedge at 3-20× their neighbours under v7 and barely at all under ablation, where the model reverts to using 3 as "medium" and often restates a neighbouring band's definition. Fixed en route: the harness had been discarding the judge's written reasons, so no flag was auditable after the fact. Spend $0.2980.
- [[evaluations/distractor-judge-two-axis-2026-08-20]] — **NEW 2026-08-20** (TASK-719/720): the distractor judge's single 1-5 rating split onto **fit** and **confusability**, with band 3 on both axes redefined as *the judge is not confident* and the triggering axis written into `generation_review_queue`. v7 rows in all three languages, **staged inactive**. Measured live-vs-v7 on 179 questions / 537 distractors, same model in every cell, $0.2738. **100% of flags are confusability flags** — the fit axis produced zero, and went near-binary (zero 3s, band 4 collapsing zh 47→2) — so fit alone now carries almost no information. **The also-correct failure is rare, not newly detectable**: 1/537 vs 3/1,800 for the old band 1, the same rate; the case for v7 rests on the review signal instead. **Question-level review volume 0-3% → 22-47%**, which is what TASK-726's gold set now has to arbitrate. The v7 code is live-safe against v4/v6 rows because `fit`'s bands *are* v4's bands, so no coordinated cutover was needed — the opposite of entailment v3.
- [[evaluations/distractor-gold-frame-2026-08-19]] — **NEW 2026-08-19** (TASK-726): the distractor gold-set **frame** — 573 items (zh 213 / en 180 / ja 180) from live-stack output, pre-rated by both TASK-718 models, post-stratified to the production question mix, plus the merge/κ-gate/scoring harness (37 unit tests). **No labels yet** — native adjudication is the only remaining work and the sole blocker on TASK-719/720. Two findings: the **reject-set disjointness reproduces on fresh content and is worse** (qwen 56 rejects, gemini 3, overlapping on 3; **en agrees on zero** across 180 items; of the 55 items qwen bands "off-topic, reject" gemini rates **35 a 5**) — and **uniform-by-type sampling has been mis-weighting every rate in this workstream**, so reweighting the live judge to production moves it **0.52% → 0.92%** and TASK-721's "0.6% on fresh output" understates production by ~1.8×. Re-scoring TASK-718 is now **free**: the frame was pre-rated with exactly that model pair. Spend $0.73.
- [[evaluations/entailment-likert-v3-rollout-2026-08-19]] — **NEW 2026-08-19** (TASK-723): post-rollout verification of the Likert v3 answer-entailment judge. v3 is **live in all three languages**; the tasklist's "staged, NOT activated" line was stale, and the un-observable third cutover move (restart) is **moot** — no app process exists, so no stale `_cfg_cache` holds a pre-Likert row. **All five bands fire in all three languages, 0 unparsed in 450 calls**, overall AUC 0.957 — first full-scale usage in this judge family, because entailment is genuinely one axis (the distractor bands still conflate two, so TASK-719 stands). ja was the outlier and it was the **model, not the language**: `qwen/qwen-2.5-72b-instruct` → `google/gemini-3.5-flash-lite` lifts AUC 0.870→0.940, false-accept 18%→2%, review load 24.7%→2.7%; applied live. Two premises corrected: "no production telemetry" was a query against the wrong namespace (`prompt_templates.task_name` ≠ `llm_calls.task_name`; 784 rows exist under `judge_answer_entailment`), and the gold set was **never** a blocker for entailment — its labels are structural and free. Live thresholds verified correct (best swept threshold 4.0 everywhere). Spend $0.2135 of $3.
- [[evaluations/distractor-judge-language-divergence-2026-08-16]] — **NEW 2026-08-16**: why the v4 distractor judge rejects 30% of zh vs 4% of en, and why the review queue is English-only. Three independent causes: qwen3.6-flash collapses the scale to {5,4,2} (no middle band, and **zero** band-1 ratings in 450 distractors — the "also correct" case has never fired); the scale conflates topical distance with answer-confusability; and the "same subject" rubric is a category error for `vocabulary_context`/`author_purpose`. The judge prompts are faithful translations — prompt drift is ruled out. ~6 of 7 non-vocab zh rejects are **false** rejects. Separately: the zh/ja vocab generator prompts few-shot on English idioms (`'pick up the pieces'`), and no generator prompt in any language contains any distractor guidance. Rejects do **not** queue — review load is 2.7%, not 18%.
- [[evaluations/dt-grading-v2-2026-07-19]] — Evidence-First v2 final eval (TASK-632): Detector/Verifier + derived scoring + rubric v6 candidate; EN span F1 .941 / clean FP .000 / overall QWK .824, JA .880/.100/.419, ZH per page; per-phase progression 622→632; `DT_FRAMEWORK_V2` flipped ON on this pass; v6 live apply owed (TASK-629).
- [[evaluations/dt-grading-baseline-2026-07-05]] — DT grading v1 baseline (TASK-622): Tier-0 near-exact gate resolved 83/90 gold items (all 45 single-error seeds) to full marks before detection; recall is the floor (EN .222 / JA .111 / ZH .000), overall-band QWK EN .516 / JA .186 / ZH .000, clean-FP 0.000 across all L2s; regression floor for TASK-623+.
- [[evaluations/exercise-pipeline-eval-2026-06-09]] — `services/exercise_generation` EN vocab pipeline eval: configured model `google/gemini-flash-1.5` is 404-delisted + missing/inactive templates (dead on arrival); once unblocked, 59% accept / 27% reject over 160 EN exercises (tl_nl_translation degenerate, semantic_discrimination mislabels valid English); cloze judge ships rejected distractors anyway. ZH unmeasured (qwen 429).

## Reviews
- [[reviews/code-review-2026-05-24]] — Python code review of main backend (4 CRITICAL incl. missing Stripe webhook; 9 HIGH; 12 MEDIUM; 5 redundancies). **CR-03 and CR-04 patched 2026-05-24** (commit `8989b0bf`); CR-01 and CR-02 still open.
- [[reviews/exercise-generation-audit-2026-06-07]] — Vocab-ladder generation audit: root cause of 小熊's 0-exercise failure (language-blind `morphological_forms >= 2` gate), 7 latent bugs (destructive regen, English-centric validation, broken non-English corpus extraction), and a prompting-infra audit (judge coverage 1/6 levels; monolith prompts; per-language capability matrix; prompt-per-exercise split).
