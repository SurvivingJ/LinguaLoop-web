---
title: Data Model Overview
type: overview
status: complete
tech_page: ./schema.tech.md
last_updated: 2026-11-23
open_questions:
  - "The two one-off backup tables of test tiers (made before the 2026-09 tier re-assignment) are still in the database and nothing reads them. Keep or drop?"
  - "The nightly knowledge-snapshot table is empty on 2026-11-23 (the job that fills it has not produced rows yet); confirm it is scheduled."
---

# Data Model Overview

## Purpose

LinguaDojo's database tracks everything needed to run an adaptive language-learning platform: users and their skill levels, the content they study, how they perform, and the tokens they spend. As of 2026-11-23 the live schema contains **100 tables**, **8 views**, **1 custom enum** (`exercise_source_type`), **23 triggers across 17 tables**, and **214 application functions** (alongside the extension functions from pgvector / pg_trgm / intarray). Every table has row-level security switched on; most of the content and pipeline tables have no policy at all, which means only the backend (with the service key) can read or write them.

Authentication delegates to Supabase `auth.users`; the application's mirror `public.users` references it on `id`. All other tables are in `public`. The database is about 349 MB. The bulk is the generated exercise rows (about 144,000) and the sense definitions with their meaning embeddings (about 73,000 senses of about 20,600 words); since 2026-11-19 the *content* of an exercise (its sentences and options) is no longer stored in the database but in a private file bucket, one file per word sense (ADR-049), so the exercise table only keeps selection data and statistics.

The 2026-09-22 archive removed the conversation, mystery, language-pack, listening-lab and organization areas (marked below); the dropped tables are kept in the sections for history. Areas added since then are described in section 12.

## Conceptual Domains

### 1. Dimension / Lookup Tables (10 tables)

Stable reference data. Cached at startup by [DimensionService](../../services/dimension_service.py) via the service-role client (RLS bypass).

- **dim_languages** (RLS) — Supported target languages with TTS config (`tts_voice_ids` jsonb + `tts_speed`) and grammar tooling flags. As of the 2026-05-05 refactor, the legacy per-task model columns (`prose_model`, `exercise_model`, `vocab_prompt[1-3]_model`, etc.) have been **dropped** — model assignments live on `prompt_templates.model` instead.
- **dim_complexity_tiers** (RLS) — 6 age-based difficulty bands (T1–T6) replacing CEFR, with ELO ranges and word-count ranges.
- **dim_test_types** (RLS) — 11 test types live: `reading`, `listening`, `dictation`, `pinyin` (Chinese), `pitch_accent` (Japanese), `classifier_drill` (Chinese), `counter_drill` (Japanese), plus `grammar`, `vocabulary`, `speaking`, `writing`.
- **dim_question_types** (RLS) — Cognitive-level classifications for MC questions (6 types).
- **dim_subscription_tiers** (RLS) — `free`, `premium`, `enterprise`, `moderator`, `admin` with daily limits, token grants, and admin/moderator flags.
- **dim_status** (RLS) — Shared status dimension (5 codes).
- **dim_lens** (RLS) — 8 topic-generation "angles" (`lens_code` + `prompt_hint`).
- **dim_grammar_patterns** — **ARCHIVED & DROPPED 2026-09-22.** Grammatical structures per language/complexity tier with example sentences.
- **dim_vocabulary** (RLS) — Master lemma dictionary (about 20,600 entries) with frequency ranks, POS, phrase types, semantic classes, component lemmas for multi-word expressions.
- **dim_word_senses** (RLS) — Definitions (two levels: simple / standard), pronunciations, examples and a meaning embedding per vocab entry per definition language, including cross-language glosses (about 73,000 rows on 2026-11-23). Holds most of the database's size, almost all of it embeddings.

### 2. Users & Auth (10 tables in the `user_*` family + `users`)

- **users** (RLS) — Linked to `auth.users` via FK on `id`. Tracks subscription tier, activity stats, soft-delete (`deleted_at` / `anonymized_at`), an old organization link (the organizations tables are archived), exercise preferences JSONB (`session_size`), and the learner's native language.
- **user_languages** (RLS) — Which languages a user is studying.
- **user_skill_ratings** (RLS) — Per-(user, language, test_type) ELO with `last_test_date` for volatility-multiplier calculation.
- **user_tokens** (RLS) — Purchased + bonus + earned + spent token totals with category breakdown.
- **user_vocabulary_knowledge** (RLS) — BKT state per (user, sense): `p_known`, `evidence_count`, `comprehension_correct/wrong`, `word_test_correct/wrong`, `last_evidence_at`, `status` (`unknown`/`learning`/`known`). RLS enabled 2026-05-12 with own_data + service_role + admin_view policies.
- **user_flashcards** (RLS) — FSRS-scheduled review cards per sense (`stability`, `difficulty`, `due_date`, `reps`, `lapses`, `state`). RLS enabled 2026-05-12.
- **user_word_ladder** (RLS) — Per (user, sense) ladder state. RLS enabled 2026-05-12. Phase 8 columns: `family_confidence` (jsonb), `gates_passed` (jsonb), `current_ring` (1-4), `stress_test_score`, `last_exercised_family`. Phase 10 column: `family_success_dates` (jsonb). Legacy Phase 4 counters (`first_try_success_count`, `first_try_failure_count`, `total_attempts`, `last_success_session_date`) are written by `ladder_record_attempt` but only `consecutive_failures` and `last_exercised_family` and `family_success_dates` are read by progression logic.
- **user_exercise_sessions** (RLS) — Cached daily exercise session per (user, language). PK is composite `(user_id, language_id)` — one session per day, replaced on next-day rebuild.
- **user_exercise_history** (RLS) — Anti-repetition table. Auto-populated via `trigger_sync_exercise_history` on `exercise_attempts INSERT`. Purpose-built indexes for 7-day session-builder lookups.
- **user_pack_selections** — Which collocation packs a user has chosen. **ARCHIVED & DROPPED 2026-09-22.**

### 3. Organizations (2 tables — B2B scaffold) — ARCHIVED & DROPPED 2026-09-22

- **organizations** (RLS) — Name, slug, subscription tier, max users, token pool.
- **organization_members** (RLS) — Composite PK `(organization_id, user_id)`, role.

### 4. Content Pipeline — Tests (9 tables)

- **categories** (RLS on, no policy: backend only) — 17 topic buckets with cooldown scheduling.
- **topics** (RLS on, no policy: backend only) — 343 specific concepts with pgvector embeddings for similarity dedup.
- **production_queue** (RLS on, no policy: backend only) — Topic-to-test pipeline state (655 items), unique on `(topic_id, language_id)`.
- **tests** (RLS on, no policy: backend only) — 491 comprehension tests with slug, transcript, audio URL, difficulty, tier, `vocab_sense_ids[]` GIN-indexed, `vocab_sense_stats` jsonb, `vocab_token_map` jsonb, `pinyin_payload` jsonb (Chinese only).
- **questions** (RLS on, no policy: backend only) — 2,316 MC questions (5 per test) with `choices`, `answer`, `answer_explanation`, `sense_ids[]`, `distractor_types` jsonb.
- **test_skill_ratings** (RLS) — Per-(test, test_type) ELO with `total_attempts`.
- **test_attempts** (RLS) — 133 attempts with score, ELO before/after, idempotency key, attempt number, `is_first_attempt`.
- **daily_test_loads** (RLS) — Pre-computed daily test sets per (user, language, load_date). RLS enabled 2026-05-12. ⚠ `user_id` FKs to `auth.users.id`, not `public.users.id` — inconsistent with every other user-owning table; the RLS policy works correctly regardless.
- **daily_test_load_items** (RLS) — Junction table with FK integrity for test IDs (replaces an older JSONB array approach). RLS enabled 2026-05-12; policies join through `load_id -> daily_test_loads.user_id`.
- **question_type_distributions** — Maps difficulty (1-9) to 5 question type slots. **ARCHIVED & DROPPED 2026-09-22;** replaced by a per-tier table of the five question types of a test.

### 5. Content — Exercises & Vocabulary (7 tables)

- **exercises** (RLS on, no policy: backend only) — About 144,000 generated items. Each belongs to a word sense (or a corpus collocation); the old grammar, conversation and style links were dropped with the archive. The exercise text itself lives in the Storage bucket since 2026-11-19; this table keeps type, level, tags, version and statistics. Phase 11 columns: `irt_difficulty`, `irt_discrimination`, `irt_n_attempts`, `irt_calibrated_at`, `irt_se_difficulty`.
- **exercise_attempts** (RLS) — Per-attempt history with `is_first_attempt` flag, `time_taken_ms`, `ladder_level`. RLS enabled 2026-05-12.
- **word_assets** (RLS on, no policy: backend only) — Generated assets per sense (P1 core, P2 exercises, P3 transforms outputs).
- **word_quiz_results** (RLS) — Detailed per-question vocab quiz results. RLS enabled 2026-05-12.
- **vocabulary_review_queue** — Queue for human review of vocab issues. **ARCHIVED & DROPPED 2026-09-22.**

### 6. Content — Corpus & Collocations (4 tables)

- **corpus_sources** (RLS on, no policy: backend only) — 8 ingested text sources per language.
- **corpus_collocations** (RLS on, no policy: backend only) — 40 extracted n-grams with PMI, LMI, t-score, log-likelihood, dependency relation, substitution entropy.
- **collocation_packs** (RLS on, no policy: backend only) — Curated groups (0 rows — scaffolded but unused). **ARCHIVED & DROPPED 2026-09-22.**
- **pack_collocations** (RLS on, no policy: backend only) — Many-to-many join (0 rows). **ARCHIVED & DROPPED 2026-09-22.**

### 7. Style System (3 tables — all empty, in-progress)

- **corpus_style_profiles** (RLS on, no policy: backend only) — Per-source style profile (ngrams, structures, syntactic + discourse + vocab profiles).
- **style_pack_items** (RLS on, no policy: backend only) — Items extracted into style packs. **ARCHIVED & DROPPED 2026-09-22.**
- **pack_style_items** (RLS on, no policy: backend only) — Many-to-many join. **ARCHIVED & DROPPED 2026-09-22.**

### 8. Conversation System (6 tables) — ARCHIVED & DROPPED 2026-09-22

- **conversation_domains** (RLS on, no policy: backend only) — 14 conversational domains.
- **personas** (RLS on, no policy: backend only) — 386 character profiles with archetype, personality jsonb, register, expertise.
- **persona_pairs** (RLS on, no policy: backend only) — 22,951 pre-computed compatible pairs.
- **scenarios** (RLS on, no policy: backend only) — 420 conversation scenarios.
- **conversations** (RLS on, no policy: backend only) — 261 generated dialogues with `turns` jsonb, `corpus_features` jsonb, `quality_score`, `passed_qc`.
- **conversation_generation_queue** (RLS on, no policy: backend only) — Pipeline state.

### 9. Mystery System (6 tables) — ARCHIVED & DROPPED 2026-09-22 (mystery mode no longer exists)

- **mysteries** (RLS) — 1 mystery currently — proof of concept stage.
- **mystery_scenes** (RLS) — 5 scenes for the one mystery.
- **mystery_questions** (RLS) — 10 questions.
- **mystery_progress** (RLS) — User position in a mystery (composite unique on (user_id, mystery_id)).
- **mystery_attempts** (RLS) — Scored attempts.
- **mystery_skill_ratings** (RLS) — Per-mystery ELO.

### 10. Token Economy (2 tables)

- **user_tokens** (RLS) — See Users section above.
- **token_transactions** (RLS) — Full ledger of all token movements with `is_valid` / `invalidated_at` for reversals.

### 11. Infrastructure & Telemetry (5 tables)

- **prompt_templates** (RLS on, no policy: backend only) — 286 versioned LLM prompts per (task, language, version). Unique on `(task_name, language_id, version)`. **Source of truth for model assignment per task** as of 2026-05-05.
- **test_generation_runs** (RLS on, no policy: backend only) — batch-run telemetry records.
- **topic_generation_runs** (RLS on, no policy: backend only) — topic-discovery telemetry records.
- **test_generation_config** (RLS on, no policy: backend only) — key-value config entries.
- **app_error_logs** (RLS) — 21 client-side error reports. `user_id` FK with `ON DELETE SET NULL`.
- **flagged_content** — Content safety flags. **ARCHIVED & DROPPED 2026-09-22.**

### 12. Areas added since the 2026-09 archive (live on 2026-11-23)

Plain-English view; the full column-level description of each is in [[database/schema.tech]] (section 13).

- **Dual-translation grading and guided repair.** A learner reads a passage taken from a test, reproduces it in their own language (or the target one), and the system grades the reproduction with a language model. The database keeps each submission, its grade, every detected error with its category and explanation, a running per-learner error profile, spaced-repetition drill cards built from that profile, the versioned grading rubric and error taxonomy, and one row per grading call (model, cost, result) for audit. A second layer, *guided self-repair*, walks the learner through fixing their own flagged errors step by step: a repair session per submission, an item per error, and an event log of hints, checks and outcomes, plus a due-date queue so unresolved errors come back later. All of these tables are backend-only.
- **Calibration and placement.** A short adaptive vocabulary check measures roughly how many words the learner knows. The database keeps each placement session, each item served and answered (with the options and which one was chosen), the pool of words eligible to be asked, a cache of ready-made wrong options, a block-list of unsafe words, per-learner ability results, and, for Chinese, tone-variant tables so wrong options can differ only in tone. Answers feed the learner's per-word knowledge as their own kind of evidence, and a log records every time placement moved a skill rating.
- **Knowledge report.** A nightly snapshot per learner and language of the inputs behind the "how many words do you know" estimate (calibration bands, counts of tracked and recently practised words). Kept for 120 days. The table is empty on 2026-11-23.
- **Sentence references.** Test transcripts are split into sentences and each sentence has reviewed native-language reference translations with a quality score and a count of independent reviews that agreed; dual-translation passages are windows over these sentences.
- **Exercise content in Storage.** Exercise sentences and options moved out of the database into versioned files in a private bucket (one per word sense), with a version counter on each exercise row and a de-duplication key for the context-free types.
- **Study plans, the weekly plan and the study-time ledger.** A plan per learner and language (daily minutes, which modules to include, new words per day, time zone), the week's targets and progress, and a ledger of measured study seconds that counts each activity once, so weekly minutes add up exactly.
- **Drills and trainers.** Chinese measure words and Japanese counters each have their own dictionary of words, nouns and distractor groups; a per-learner mastery table drives the measure-word drill's levels. A word list a learner uploads is kept as a watchlist that is matched against newly generated tests.
- **Prestudy.** Optional study sessions before a test (words shown, quizzed, readiness) and the follow-up reviews they schedule for the next day.
- **Generation housekeeping.** A queue of words that need exercises regenerated, a review queue for artifacts the automatic judges flagged, per-stage timing of the generation pipelines, selection tuning knobs for the recommended-tests ranking, and trusted devices for sign-in.

## Enum Types

| Enum | Values |
|------|--------|
| `exercise_source_type` | `grammar`, `vocabulary`, `collocation`, `conversation`, `style` |

## Views

Eight views (all run with the caller's rights and are readable only by the backend): `corpus_statistics` (collocations by language, type and n-gram size), `vw_distractor_error_analysis` (which distractor patterns cause errors), `vw_exercise_performance_by_type` (accuracy by exercise type, tier and language), `vw_exercise_type_effectiveness` (knowledge gained per minute by exercise type), `v_ladder_judge_reject_rates` (how often judges reject generated items), `v_sense_family_coverage` (which exercise families a word still lacks), `v_test_difficulty_calibration` and `v_test_difficulty_calibration_summary` (seeded vs observed test difficulty).

## Triggers (the original 11; 23 live across 17 tables, the rest are listed in the technical page)

| Table | Trigger | Timing | Event | Function |
|-------|---------|--------|-------|----------|
| `dim_vocabulary` | `update_vocab_timestamp` | BEFORE | UPDATE | `update_updated_at_column()` |
| `dim_word_senses` | `update_sense_timestamp` | BEFORE | UPDATE | `update_updated_at_column()` |
| `exercise_attempts` | `trigger_sync_exercise_history` | AFTER | INSERT | `sync_exercise_history()` |
| `test_attempts` | `trigger_increment_test_attempts` | AFTER | INSERT | `update_test_attempts_count()` |
| `test_attempts` | `trigger_update_skill_attempts` | AFTER | INSERT | `update_skill_attempts_count()` |
| `tests` | `update_tests_updated_at` | BEFORE | UPDATE | `update_updated_at_column()` |
| `user_languages` | `update_user_languages_updated_at` | BEFORE | UPDATE | `update_updated_at_column()` |
| `user_reports` | `update_user_reports_updated_at` | BEFORE | UPDATE | `update_updated_at_column()` |
| `user_skill_ratings` | `update_user_skill_ratings_updated_at` | BEFORE | UPDATE | `update_updated_at_column()` |
| `users` | `create_user_dependencies_trigger` | AFTER | INSERT | `create_user_dependencies()` |
| `users` | `update_users_updated_at` | BEFORE | UPDATE | `update_updated_at_column()` |

## Key Relationships

```
User ──→ User Skill Ratings (per language + test type) ──→ ELO
User ──→ User Vocabulary Knowledge (per word sense) ──→ BKT p_known
User ──→ User Flashcards (per word sense) ──→ FSRS schedule
User ──→ User Word Ladder (per word sense) ──→ ring + family_confidence + gates
User ──→ Test Attempts ──→ Test ──→ Questions
User ──→ Exercise Attempts ──→ Exercise ──→ Word Sense | Collocation   (grammar, conversation and style links archived)
User ──→ Mystery Progress ──→ Mystery ──→ Scenes ──→ Questions   (archived 2026-09-22)
User ──→ User Tokens ──→ Token Transactions
Test ──→ Test Skill Ratings ──→ ELO (per test type)
Topic ──→ Tests (multiple tests per topic, multi-language fan-out)
Category ──→ Topics ──→ Production Queue
Category ──→ Conversation Domains ──→ Scenarios ──→ Conversations   (archived 2026-09-22)
Personas ──→ Persona Pairs ──→ Conversations   (archived 2026-09-22)
User ──→ Dual-translation Submission ──→ Grade / Errors ──→ Error Profile ──→ Drill Cards;  Submission ──→ Repair Session ──→ Items ──→ Events
User ──→ Placement Session ──→ Responses ──→ Options;  User ──→ Calibration State ──→ Skill Rating Adjustments
Test ──→ Sentences ──→ Reference Translations (per native language)
User ──→ Study Plan ──→ Weekly Plan State;  User ──→ Study-time Ledger
dim_vocabulary ──→ dim_word_senses ──→ Word Assets / Exercises / User Knowledge / Flashcards
dim_languages ──→ (central FK hub: ~30 tables reference it)
```

## Row-Level Security — Audit Snapshot (2026-11-23)

**All 100 tables have RLS enabled.** 42 of them have at least one policy (the learner-owned tables with an own-rows rule, the dimension tables with a read rule, and a few logs); the other 58 have no policy, so with the client privileges revoked only the backend can touch them. The earlier list of "RLS-disabled content tables" no longer applies: the 2026-10 hardening enabled RLS everywhere, revoked every client write privilege (no table grants INSERT, UPDATE or DELETE to the anonymous or signed-in roles) and made the views run with the caller's rights. The technical page lists the exact policies and grants per table.

## Related Pages

- [[database/schema.tech]] — Full DDL: every column, type, FK, index, trigger, RLS policy
- [[database/rpcs.tech]] — Reference for all 214 live functions (signatures, security, who may execute, tables touched) with the older full SQL notes
- [[algorithms/elo-ranking]] — How ELO is calculated
- [[algorithms/vocabulary-ladder]] — Phase 8/10 momentum bands
- [[features/comprehension-tests]] — Test structure and flow
- [[features/exercises]] — Exercise types and sources
- [[features/vocab-dojo]] — Adaptive ladder serving
- [[features/calibration]], [[features/dual-translation]], [[features/dt-guided-self-repair]], [[features/test-sentence-references]], [[features/test-prestudy]] — feature descriptions for the newer areas
