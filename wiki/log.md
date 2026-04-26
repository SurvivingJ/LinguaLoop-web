# Activity Log

## 2026-04-25 feature | Full Pipeline admin tab

Source: `routes/admin_local.py`, `templates/admin_dashboard.html`, `static/js/admin-dashboard.js`, `scripts/backfill_question_sense_ids.py`.

**Pages updated: 5**
- `overview/project.tech.md` — Rewrote Admin Pipeline Dashboard section: replaced outdated `/admin/vocab` description with full 9-tab dashboard architecture, including endpoint/runner table for all tabs and detailed Full Pipeline step breakdown
- `features/exercises.md` — Added Full Pipeline as generation trigger in Business Rules; corrected Exercise Sources (added conversation + style, removed outdated study_pack)
- `features/exercises.tech.md` — Added Full Pipeline to Architecture Overview diagram; added backfill scripts to Generator Architecture tree; added architectural decision #6 (unified backfill orchestrator)
- `pages/pages-overview.md` — Added `/admin` route with `admin_dashboard.html` template
- `log.md` — This entry

Notes: The Full Pipeline tab is the 9th admin dashboard tab. It orchestrates 6 existing backfill scripts sequentially (vocab → token maps → question sense IDs → skill ratings → exercises → collocations) via `_do_full_pipeline()` in `admin_local.py`. All steps are idempotent with per-step try/except. Also fixed exercises.md which listed an outdated `study_pack` source type instead of the actual `conversation` and `style` source types.

---

## 2026-04-24 update | Style analysis schema added to wiki

Source: `migrations/style_analysis_tables.sql`, `migrations/style_exercise_fk.sql`.

**Pages updated: 3**
- `database/schema.tech.md` — Added 3 tables (`corpus_style_profiles`, `style_pack_items`, `pack_style_items`), added `style_pack_item_id` FK + `chk_source_fk` constraint to `exercises`, added 'style' to `exercise_source_type` enum, updated `collocation_packs.pack_type` CHECK, updated table count 62 → 65
- `features/corpus-analysis.tech.md` — Added style tables to Database Impact section and dependencies
- `wiki/log.md` — This entry

Notes: These tables were created by `style_analysis_tables.sql` (applied after `corpus_analysis_tables.sql`) and `style_exercise_fk.sql` but had never been documented in the wiki. The style exercise generators and orchestrator wiring were also added in this session (see backfill audit).

---

## 2026-04-21 ingest | Pinyin Tone Trainer feature

Source: `migrations/add_pinyin_mode.sql`, `services/pinyin_service.py`, `routes/tests.py`, `templates/test_pinyin.html`, `scripts/batch_generate_pinyin.py`.

**Pages created: 2**
- `features/pinyin-trainer.md` — Prose: Chinese tone-guessing game, sandhi rules, polyphone handling, user flow
- `features/pinyin-trainer.tech.md` — Tech spec: pypinyin pipeline, token schema, submit-pinyin endpoint, batch script, architectural decisions

**Pages updated: 4**
- `database/schema.tech.md` — Added `pinyin_payload` JSONB column to `tests` table; updated `dim_test_types` description to include pinyin
- `database/schema.md` — Updated `dim_test_types` description to include pinyin
- `features/comprehension-tests.md` — Added Pinyin Tones to Test Types list; added cross-reference to pinyin-trainer page
- `index.md` — Added 2 pinyin-trainer pages, page count 41 → 43, updated date

**Key details:**
1. **Chinese-only** test mode using existing test transcripts as source material
2. **Pre-computed pinyin_payload** JSONB on `tests` table — tokenised characters with base/context tones, sandhi rules, word context
3. **Deterministic sandhi engine** — third-tone, yi, bu rules applied via `pinyin_service._apply_sandhi()`
4. **Polyphone handling** — jieba segmentation + 45-char watchlist + optional DeepSeek LLM resolution (batch only)
5. **Reuses `process_test_submission` RPC** with synthetic accuracy-based response for ELO updates
6. **Keyboard arrows + touch swipes** mapped to tone contours (right=T1, up=T2, left=T3, down=T4, tap/space=neutral)
7. **Batch backfill script** (`scripts/batch_generate_pinyin.py`) with --resolve-polyphones and --dry-run flags

---

## 2026-04-16 implementation | Phase 7 BKT improvements

Source: `migrations/phase7_bkt_improvements.sql`, code changes in 5 Python files.

**Pages updated: 7**
- `algorithms/bkt-implementation-analysis.md` — Rewrote "What's Missing" → "What's Been Fixed" for 7 items; updated remaining gaps (3); replaced proposed improvements table with implementation history
- `algorithms/bkt-implementation-analysis.tech.md` — Updated architecture map (transit, lapse penalty, contextual inference, get_session_senses RPC); marked 6 improvements as implemented; updated evidence flow analysis; rewrote BKT↔FSRS interaction as bidirectional
- `features/vocabulary-knowledge.md` — Added decay, contextual inference, frequency inference, transit, lapse penalty to How It Works; updated constraints and business rules
- `features/vocabulary-knowledge.tech.md` — Updated architecture diagram; added full parameter table with transit; added decay model section; added implicit knowledge inference section; added 2 new architectural decisions
- `database/rpcs.tech.md` — Updated 3 existing functions (bkt_update_comprehension +transit, bkt_update_word_test +transit, bkt_update_exercise +transit); replaced 2 Phase 5 functions with Phase 7 versions (bkt_apply_decay 4-param, bkt_effective_p_known 4-param); added 5 new functions (get_session_senses, bkt_apply_lapse_penalty, bkt_infer_from_frequency, bkt_contextual_inference). RPC count 48→53
- `index.md` — Updated BKT page descriptions, RPC counts
- `log.md` — This entry

**Key changes in Phase 7:**
1. **Transit parameter P(T)** added to all 3 BKT update functions (0.02 comprehension, 0.05 recognition, 0.08 recall/nuanced, 0.10 production)
2. **FSRS stability-informed decay** replaces flat 60-day half-life — uses `exp(-days/stability)` with evidence-count-scaled fallback
3. **get_session_senses() RPC** — single SQL function replaces 3 Python fetch methods. All BKT math now in PostgreSQL only
4. **FSRS lapse → BKT penalty** — 20% p_known reduction on FSRS lapse, bridges the reverse FSRS→BKT gap
5. **Frequency-tier inference** — knowing rare words auto-boosts common words with low evidence
6. **Sentence-level contextual inference** — dampened BKT update for untested transcript words (0.30 × score_ratio)
7. **Per-question sense_ids** — questions now link only to vocabulary in their text + choices, not all transcript senses

**Code changes:**
- `migrations/phase7_bkt_improvements.sql` — 9 SQL functions (3 updated, 6 new)
- `services/exercise_session_service.py` — Removed Python decay logic + 3 fetch methods + stability map helper; replaced with single `get_session_senses()` RPC call
- `services/vocabulary/knowledge_service.py` — Added `apply_contextual_inference()`, `_trigger_frequency_inference()`, `apply_lapse_penalty()`
- `services/vocabulary_ladder/ladder_service.py` — Added lapse penalty trigger in `_update_fsrs()`
- `services/test_generation/orchestrator.py` — Fixed per-question sense_ids via `_match_question_senses()`
- `routes/tests.py` — Wired contextual inference after comprehension BKT update

---

## 2026-04-15 ingest | Phase 1-6 SQL migrations sync

Source: `migrations/phase1_quick_wins.sql`, `phase2_schema_cleanup.sql`, `phase3_rpc_fixes.sql`, `phase4_schema_evolution.sql`, `phase5_algorithm_fixes.sql`, `phase6_security_hardening.sql`.

**Pages updated: 7**
- `database/schema.md` — Table count 60→62, RPC count 43→48, RLS count 18→27, removed users_backup, added 3 new tables (user_exercise_history, language_model_config, daily_test_load_items), updated triggers list
- `database/schema.tech.md` — Renamed dim_complexity_tiers PK/sequence, enabled RLS on 8 tables with policies, rewrote user_pack_selections (text→uuid), added 7 columns to user_word_ladder, added 3 full table definitions, fixed FKs (user_reports, app_error_logs), fixed user_exercise_sessions.language_id type, updated triggers and Key Database Functions
- `database/rpcs.tech.md` — Removed 2 dropped RPCs (process_test_submission-old, migrate_test_json), added 7 new functions (bkt_update_exercise, bkt_apply_decay, bkt_effective_p_known, bkt_phase, bkt_phase_thresholds, get_model_for_task, sync_exercise_history), updated 12 existing RPCs (security model changes, parameter fixes, implementation fixes), rebuilt Security Summary (43→48 functions, 19→24 DEFINER)
- `algorithms/elo-ranking.tech.md` — Re-enabled volatility multiplier, asymmetric K-factors (32 user/16 test), get_recommended_test now excludes attempted tests
- `algorithms/bkt-implementation-analysis.tech.md` — Marked 3 improvements as implemented: exercise-type BKT (4 cognitive tiers), temporal decay (60-day half-life), canonical phase thresholds (bkt_phase/bkt_phase_thresholds)
- `algorithms/ladder-implementation-analysis.tech.md` — Updated user_word_ladder DDL (7 new columns), marked user_exercise_history as created, updated Missing From Implementation list, marked 2 improvement proposals as implemented (schema only, Python pending)
- `index.md` — Updated table/RPC counts, last_updated date

**Key changes by phase:**
1. Phase 1: Dropped duplicate trigger, 2 dead RPCs, empty users_backup table; fixed get_prompt_template (language_code→language_id)
2. Phase 2: Rebuilt user_pack_selections with uuid FK; fixed user_reports FK; fixed user_exercise_sessions type; renamed dim_complexity_tiers PK
3. Phase 3: Re-enabled ELO volatility with asymmetric K (32/16); fixed get_recommended_test exclusion; implemented can_use_free_test and get_token_balance; O(1 trigger increments; added auth to get_distractors
4. Phase 4: Extended user_word_ladder (7 columns); created user_exercise_history + trigger; created language_model_config + helper; created daily_test_load_items junction table
5. Phase 5: Created 5 BKT functions (exercise-type params, temporal decay, phase thresholds); added exercise_type param to update_vocabulary_from_word_test
6. Phase 6: Enabled RLS on 8 tables (users, 5 dim tables, app_error_logs); hardened 5 RPCs to SECURITY DEFINER + search_path

---

## 2026-04-11 analysis | ELO, BKT, and Ladder implementation audit

Source: Full codebase analysis — all Python services, SQL RPCs, database schema, exercise generation pipeline.

**Pages created: 6**
- `algorithms/elo-implementation-analysis.md` — ELO prose analysis: volatility bug, recommendation gaps, improvements
- `algorithms/elo-implementation-analysis.tech.md` — ELO technical analysis with fix code and schema proposals
- `algorithms/bkt-implementation-analysis.md` — BKT prose analysis: missing transit, no decay, type-agnostic params
- `algorithms/bkt-implementation-analysis.tech.md` — BKT technical analysis with improvement code
- `algorithms/ladder-implementation-analysis.md` — Ladder prose analysis: 9 vs 10 levels, no demotion, competing session builders
- `algorithms/ladder-implementation-analysis.tech.md` — Ladder technical analysis with consolidation proposals

**Pages updated: 1**
- `index.md` — Added 6 new pages, page count 35 → 41

**Critical findings:**
1. **ELO volatility intentionally removed in V2** — V1 migration called volatility; V2 migration inlined ELO calc without it. K-factor changed from asymmetric (32 user / 16 test) to symmetric 32. Helper functions left in DB but disconnected.
2. **BKT has only 2 of 4 standard parameters** — missing transit P(T) and has no temporal decay. All exercise types use identical slip/guess regardless of cognitive demand.
3. **Ladder has 9 levels, not 10** — Level 10 (Capstone Production) is documented but not implemented. No demotion logic exists. Promotion is immediate on single first-attempt success (designed as 2-session requirement).
4. **Phase threshold inconsistency** — Python session builder uses 0.30/0.55/0.80 thresholds; SQL RPC uses 0.40/0.65/0.80. Same word gets different exercise types depending on code path.
5. **Two competing session builders** — ExerciseSessionService (6-bucket daily) and LadderService (standalone) with different selection logic.
6. **N+1 query pattern** — ExerciseSessionService._select_exercises_for_senses() runs ~40 individual DB queries per session build.
7. **`user_word_progress` table from wiki does not exist** — actual table is `user_word_ladder` with simpler schema.
8. **`user_exercise_history` table from wiki does not exist yet** — anti-repetition uses exercise_attempts scan.
9. ~~**Missing UNIQUE constraints**~~ — CORRECTED: live schema (`db_schema_live.sql`) confirms both `user_skill_ratings` and `test_skill_ratings` DO have UNIQUE constraints on their natural keys. Wiki `schema.tech.md` omitted them.

**Improvement priorities identified (17 total):**
- ELO: wire up volatility (XS), exclude attempted in single rec (XS), vocab-ELO primary (S), adaptive K (M), Glicko-2 (L)
- BKT: exercise-type params (S), temporal decay (M), transit parameter (XS), BKT-FSRS sync (S), data-driven calibration (L)
- Ladder: promotion tracking (M), demotion logic (S), consolidate builders (M), Level 10 capstone (L), anti-repetition (XS), IRT calibration (M), N+1 fix (S), user_exercise_history table (S)

---

## 2026-04-10 bootstrap | Initial wiki creation

Session summary: Full wiki bootstrap from codebase analysis + developer interview.

**Pages created:** 28
- 2 overview pages (project + tech)
- 2 database pages (schema + tech)
- 14 feature pages (7 features x prose + tech)
- 2 algorithm pages (ELO + tech)
- 2 API pages (overview + tech)
- 1 pages overview
- 1 business rules page
- 2 ADRs
- 1 master task list
- 1 feature task stub (language-packs, blocked)

**Open questions remaining:** 18 (across language-packs, vocab-dojo, mysteries, conversations, token-economy, auth)

**Key findings from bootstrap interview:**
- Current priority: Language Pack generation pipeline
- Stack: Flask + Jinja2 + Supabase + OpenRouter + Azure TTS + R2 + Stripe on Railway
- Language Packs are themed conversation bundles with word study → exercises → comprehension progression
- All content is system-generated, manually triggered by admin
- Conversations serve as corpus for vocabulary extraction (not standalone feature)
- Vocab Dojo is a new feature being built for adaptive exercise serving
- Future B2B play via organizations, but individual users are current focus

## 2026-04-10 ingest | Raw documents + user answers to 18 lint questions

**Sources processed:**
- `raw/LinguaLoop Vocabulary Acquisition Pipeline.md` — 10-level exercise ladder spec (Nation's framework)
- `raw/TASK_ Using the specification below, design a rese.md` — Full pipeline report: 3-prompt architecture, age tiers, word states, promotion/demotion
- `raw/# Task_Analyse and interrogate the following plan,.md` — Study pack design: corpus-first, adaptive learning arc, inverted density, scenario generation
- `raw/The big question with linguadojo exercises is_ how.md` — Exercise serving algorithm: ExerciseScheduler, session composition, anti-repetition
- `raw/I want to eventually add the ability to track a us.md` — Test recommendation via set-based vocab matching (not embeddings)
- User's 18 answers to lint report questions (age tiers, NLP in DB, admin dashboard, etc.)

**Pages created: 5**
- `algorithms/vocabulary-ladder.md` — 10-level receptive-to-productive word acquisition
- `algorithms/vocabulary-ladder.tech.md` — Nation's framework, language specs, POS routing
- `features/vocab-dojo.tech.md` — ExerciseScheduler, anti-repetition, get_exercise_session RPC
- `decisions/ADR-003-age-tiers.md` — Age-tier difficulty system replacing CEFR

**Pages substantially rewritten: 7**
- `features/language-packs.md` — Corpus-first design, adaptive cycle, pack mastery tiers
- `features/language-packs.tech.md` — 7-stage pipeline, new tables, runtime orchestrator
- `features/exercises.md` — 21 types in 4 phases, age-tier table
- `features/exercises.tech.md` — 3-prompt LLM pipeline, numeric JSON schema, validation
- `features/vocab-dojo.md` — Full adaptive serving spec, 40/40/20 session split
- `features/conversations.tech.md` — Two-step scenario generation (Matrix Builder + Expander)
- `features/comprehension-tests.md` — 90-95% vocab coverage for recommendations

**Pages updated: 3**
- `database/schema.tech.md` — Added 7 new tables, 4 column additions, exercise session RPC
- `overview/project.tech.md` — Added admin pipeline dashboard spec
- `index.md` — Added 5 new pages, updated descriptions, page count 28 → 33

**Key decisions confirmed:**
- Corpus-first architecture (conversations generated naturally, vocab extracted post-hoc)
- Age tiers replace CEFR for LLM generation (ADR-003)
- Generate-once, use-forever: all exercise assets immutable after validation
- NLP analysis via Supabase pg_text_analysis plugin (in-database)
- Set-based vocabulary matching for test recommendations (not vector embeddings)
- Admin manually triggers pipelines via dashboard; no automated scheduling

**Open questions resolved: 14 of 18** (from bootstrap lint report)

## 2026-04-11 ingest | Complete Supabase database map

Source: Live Supabase project (kpfqrjtfxmujzolwsvdq) via MCP connector — direct SQL queries + list_tables API.

**Data pulled:**
- 60 tables with full column details (types, nullable, defaults, RLS status)
- 100+ foreign key constraints from information_schema
- All indexes (btree, GIN, IVFFlat)
- 11 triggers
- 1 custom enum (exercise_source_type)
- 3 views (corpus_statistics, vw_distractor_error_analysis, vw_exercise_performance_by_type)
- 43 application RPCs/functions with full SQL definitions
- 199 extension functions (pgvector, intarray, pg_trgm) catalogued but not documented

**Pages rewritten: 2**
- `database/schema.md` — Complete rewrite with 10 domains, 60 tables, row counts, RLS status, enum/view/trigger summaries
- `database/schema.tech.md` — Complete rewrite from Supabase data: every column, type, FK, index, trigger

**Pages created: 1**
- `database/rpcs.tech.md` — All 43 application RPCs with full function bodies, categorized by domain

**Pages updated: 2**
- `index.md` — Added rpcs.tech, updated schema descriptions, page count 33 → 35
- `log.md` — This entry

**Key findings:**
- 18 tables have RLS enabled (all user-facing + content tables)
- dim_languages is the central FK hub — nearly every content table references it
- 43 custom RPCs cover: auth (is_admin, is_moderator), ELO (update_elo_ratings, record_test_attempt), tokens (atomic add/consume), vocab (BKT updates, stats), exercises (session management), mysteries, and utilities
- users table FK to auth.users.id (Supabase auth integration)
- users_backup table exists (empty, legacy, no PK)
- pgvector extension in use (topics.embedding with IVFFlat index, 100 lists)
- intarray extension in use (tests.vocab_sense_ids with gin__int_ops)
