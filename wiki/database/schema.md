---
title: Data Model Overview
type: overview
status: complete
tech_page: ./schema.tech.md
last_updated: 2026-05-12
open_questions:
  - "Language Packs will need new tables — pack conversations, pack word lists, pack exercise links. Design pending."
  - "21 content/infrastructure tables remain RLS-disabled after the 2026-05-12 RLS hardening (the 7 user-owning tables were locked down). Decide whether the remaining content tables (exercises, corpus_*, conversations, personas, scenarios, prompt_templates, word_assets, etc.) stay deliberately public or get RLS too."
---

# Data Model Overview

## Purpose

LinguaDojo's database tracks everything needed to run an adaptive language-learning platform: users and their skill levels, the content they study, how they perform, and the tokens they spend. As of 2026-05-12 the schema contains **64 tables**, **1 custom enum** (`exercise_source_type`), **3 views**, **11 triggers across 8 tables**, and **~77 application RPCs** (alongside ~199 extension functions from pgvector / pg_trgm / intarray).

Authentication delegates to Supabase `auth.users`; the application's mirror `public.users` references it on `id`. All other tables are in `public`. Total database size is small (low single-digit MB) — the largest tables are `persona_pairs` (22.9k rows, a near-Cartesian compatibility matrix), `exercises` (11.2k generated items), `dim_word_senses` (9.9k), and `dim_vocabulary` (7.1k lemmas).

## Conceptual Domains

### 1. Dimension / Lookup Tables (10 tables)

Stable reference data. Cached at startup by [DimensionService](../../services/dimension_service.py) via the service-role client (RLS bypass).

- **dim_languages** (RLS) — Supported target languages with TTS config (`tts_voice_ids` jsonb + `tts_speed`) and grammar tooling flags. As of the 2026-05-05 refactor, the legacy per-task model columns (`prose_model`, `exercise_model`, `vocab_prompt[1-3]_model`, etc.) have been **dropped** — model assignments live on `prompt_templates.model` instead.
- **dim_complexity_tiers** (RLS) — 6 age-based difficulty bands (T1–T6) replacing CEFR, with ELO ranges and word-count ranges.
- **dim_test_types** (RLS) — `reading`, `listening`, `dictation`, `pinyin` (Chinese-only).
- **dim_question_types** (RLS) — Cognitive-level classifications for MC questions (6 types).
- **dim_subscription_tiers** (RLS) — `free`, `premium`, `enterprise` with daily limits, token grants, and admin/moderator flags.
- **dim_status** (RLS) — Shared status dimension (5 codes).
- **dim_lens** (RLS) — 8 topic-generation "angles" (`lens_code` + `prompt_hint`).
- **dim_grammar_patterns** (RLS) — Grammatical structures per language/complexity tier with example sentences.
- **dim_vocabulary** (RLS) — Master lemma dictionary (7,071 entries) with frequency ranks, POS, phrase types, semantic classes, component lemmas for multi-word expressions.
- **dim_word_senses** (RLS) — Definitions, IPA pronunciations, examples, morphological forms per vocab entry per definition language (9,868 entries).

### 2. Users & Auth (10 tables in the `user_*` family + `users`)

- **users** (RLS) — Linked to `auth.users` via FK on `id`. Tracks subscription tier, activity stats, soft-delete (`deleted_at` / `anonymized_at`), organization membership, exercise preferences JSONB (`session_size`).
- **user_languages** (RLS) — Which languages a user is studying.
- **user_skill_ratings** (RLS) — Per-(user, language, test_type) ELO with `last_test_date` for volatility-multiplier calculation.
- **user_tokens** (RLS) — Purchased + bonus + earned + spent token totals with category breakdown.
- **user_vocabulary_knowledge** (RLS) — BKT state per (user, sense): `p_known`, `evidence_count`, `comprehension_correct/wrong`, `word_test_correct/wrong`, `last_evidence_at`, `status` (`unknown`/`learning`/`known`). RLS enabled 2026-05-12 with own_data + service_role + admin_view policies.
- **user_flashcards** (RLS) — FSRS-scheduled review cards per sense (`stability`, `difficulty`, `due_date`, `reps`, `lapses`, `state`). RLS enabled 2026-05-12.
- **user_word_ladder** (RLS) — Per (user, sense) ladder state. RLS enabled 2026-05-12. Phase 8 columns: `family_confidence` (jsonb), `gates_passed` (jsonb), `current_ring` (1-4), `stress_test_score`, `last_exercised_family`. Phase 10 column: `family_success_dates` (jsonb). Legacy Phase 4 counters (`first_try_success_count`, `first_try_failure_count`, `total_attempts`, `last_success_session_date`) are written by `ladder_record_attempt` but only `consecutive_failures` and `last_exercised_family` and `family_success_dates` are read by progression logic.
- **user_exercise_sessions** (RLS) — Cached daily exercise session per (user, language). PK is composite `(user_id, language_id)` — one session per day, replaced on next-day rebuild.
- **user_exercise_history** (RLS) — Anti-repetition table. Auto-populated via `trigger_sync_exercise_history` on `exercise_attempts INSERT`. Purpose-built indexes for 7-day session-builder lookups.
- **user_pack_selections** (RLS) — Which collocation packs a user has chosen.

### 3. Organizations (2 tables — B2B scaffold, no production data)

- **organizations** (RLS) — Name, slug, subscription tier, max users, token pool.
- **organization_members** (RLS) — Composite PK `(organization_id, user_id)`, role.

### 4. Content Pipeline — Tests (9 tables)

- **categories** (⚠ RLS DISABLED) — 33 topic buckets with cooldown scheduling.
- **topics** (⚠ RLS DISABLED) — 43 specific concepts with pgvector embeddings for similarity dedup.
- **production_queue** (⚠ RLS DISABLED) — Topic-to-test pipeline state (109 items), unique on `(topic_id, language_id)`.
- **tests** (RLS) — 254 comprehension tests with slug, transcript, audio URL, difficulty, tier, `vocab_sense_ids[]` GIN-indexed, `vocab_sense_stats` jsonb, `vocab_token_map` jsonb, `pinyin_payload` jsonb (Chinese only).
- **questions** (RLS) — 1,223 MC questions (5 per test) with `choices`, `answer`, `answer_explanation`, `sense_ids[]`, `distractor_types` jsonb.
- **test_skill_ratings** (RLS) — Per-(test, test_type) ELO with `total_attempts`.
- **test_attempts** (RLS) — 49 attempts with score, ELO before/after, idempotency key, attempt number, `is_first_attempt`.
- **daily_test_loads** (RLS) — Pre-computed daily test sets per (user, language, load_date). RLS enabled 2026-05-12. ⚠ `user_id` FKs to `auth.users.id`, not `public.users.id` — inconsistent with every other user-owning table; the RLS policy works correctly regardless.
- **daily_test_load_items** (RLS) — Junction table with FK integrity for test IDs (replaces an older JSONB array approach). RLS enabled 2026-05-12; policies join through `load_id -> daily_test_loads.user_id`.
- **question_type_distributions** (⚠ RLS DISABLED) — Maps difficulty (1-9) to 5 question type slots.

### 5. Content — Exercises & Vocabulary (7 tables)

- **exercises** (⚠ RLS DISABLED — content table, deliberately readable) — 11,195 generated items. Source via the `exercise_source_type` enum (`grammar`, `vocabulary`, `collocation`, `conversation`, `style`); FK to exactly one of `grammar_pattern_id`, `word_sense_id`, `corpus_collocation_id`, `conversation_id`, `style_pack_item_id`, `word_asset_id`. Phase 11 columns: `irt_difficulty`, `irt_discrimination`, `irt_n_attempts`, `irt_calibrated_at`, `irt_se_difficulty`.
- **exercise_attempts** (RLS) — Per-attempt history with `is_first_attempt` flag, `time_taken_ms`, `ladder_level`. RLS enabled 2026-05-12.
- **word_assets** (⚠ RLS DISABLED) — Generated assets per sense (P1 core, P2 exercises, P3 transforms outputs).
- **word_quiz_results** (RLS) — Detailed per-question vocab quiz results. RLS enabled 2026-05-12.
- **vocabulary_review_queue** (RLS) — Queue for human review of vocab issues.

### 6. Content — Corpus & Collocations (4 tables)

- **corpus_sources** (⚠ RLS DISABLED) — 8 ingested text sources per language.
- **corpus_collocations** (⚠ RLS DISABLED) — 40 extracted n-grams with PMI, LMI, t-score, log-likelihood, dependency relation, substitution entropy.
- **collocation_packs** (⚠ RLS DISABLED) — Curated groups (0 rows — scaffolded but unused).
- **pack_collocations** (⚠ RLS DISABLED) — Many-to-many join (0 rows).

### 7. Style System (3 tables — all empty, in-progress)

- **corpus_style_profiles** (⚠ RLS DISABLED) — Per-source style profile (ngrams, structures, syntactic + discourse + vocab profiles).
- **style_pack_items** (⚠ RLS DISABLED) — Items extracted into style packs.
- **pack_style_items** (⚠ RLS DISABLED) — Many-to-many join.

### 8. Conversation System (6 tables)

- **conversation_domains** (⚠ RLS DISABLED) — 14 conversational domains.
- **personas** (⚠ RLS DISABLED) — 386 character profiles with archetype, personality jsonb, register, expertise.
- **persona_pairs** (⚠ RLS DISABLED) — 22,951 pre-computed compatible pairs.
- **scenarios** (⚠ RLS DISABLED) — 420 conversation scenarios.
- **conversations** (⚠ RLS DISABLED) — 261 generated dialogues with `turns` jsonb, `corpus_features` jsonb, `quality_score`, `passed_qc`.
- **conversation_generation_queue** (⚠ RLS DISABLED) — Pipeline state.

### 9. Mystery System (6 tables)

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

- **prompt_templates** (⚠ RLS DISABLED) — 111 versioned LLM prompts per (task, language, version). Unique on `(task_name, language_id, version)`. **Source of truth for model assignment per task** as of 2026-05-05.
- **test_generation_runs** (⚠ RLS DISABLED) — 17 batch-run telemetry records.
- **topic_generation_runs** (⚠ RLS DISABLED) — 6 topic-discovery telemetry records.
- **test_generation_config** (⚠ RLS DISABLED) — 4 key-value config entries.
- **app_error_logs** (RLS) — 21 client-side error reports. `user_id` FK with `ON DELETE SET NULL`.
- **flagged_content** (RLS) — Content safety flags.

## Enum Types

| Enum | Values |
|------|--------|
| `exercise_source_type` | `grammar`, `vocabulary`, `collocation`, `conversation`, `style` |

## Views

| View | Purpose |
|------|---------|
| `corpus_statistics` | Aggregates collocations by language, type, n-gram size with avg PMI, frequency, validated count |
| `vw_distractor_error_analysis` | Analyses incorrect cloze exercise attempts by grammar pattern and distractor error type |
| `vw_exercise_performance_by_type` | Exercise accuracy % grouped by exercise type, complexity tier, language |

## Triggers (11 across 8 tables)

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
User ──→ Exercise Attempts ──→ Exercise ──→ Grammar Pattern | Word Sense | Collocation | Conversation | Style Pack Item
User ──→ Mystery Progress ──→ Mystery ──→ Scenes ──→ Questions
User ──→ User Tokens ──→ Token Transactions
Test ──→ Test Skill Ratings ──→ ELO (per test type)
Topic ──→ Tests (multiple tests per topic, multi-language fan-out)
Category ──→ Topics ──→ Production Queue
Category ──→ Conversation Domains ──→ Scenarios ──→ Conversations
Personas ──→ Persona Pairs ──→ Conversations
dim_vocabulary ──→ dim_word_senses ──→ Word Assets / Exercises / User Knowledge / Flashcards
dim_languages ──→ (central FK hub: ~30 tables reference it)
```

## Row-Level Security — Audit Snapshot

**RLS enabled (41 tables):** users, user_languages, user_skill_ratings, user_tokens, user_reports, user_exercise_sessions, user_exercise_history, user_pack_selections, **user_vocabulary_knowledge, user_flashcards, user_word_ladder, word_quiz_results, exercise_attempts, daily_test_loads, daily_test_load_items** (last 7 enabled 2026-05-12 — see [migrations/enable_rls_on_user_owned_tables.sql](../../migrations/enable_rls_on_user_owned_tables.sql)), tests, test_skill_ratings, test_attempts, questions, token_transactions, flagged_content, app_error_logs, vocabulary_review_queue, mysteries, mystery_attempts, mystery_progress, mystery_questions, mystery_scenes, mystery_skill_ratings, organization_members, organizations, dim_languages, dim_test_types, dim_subscription_tiers, dim_status, dim_lens, dim_question_types, dim_complexity_tiers, dim_vocabulary, dim_word_senses, dim_grammar_patterns.

**⚠ RLS DISABLED (23 tables — content/infrastructure, no per-user state):** categories, topics, production_queue, topic_generation_runs, prompt_templates, question_type_distributions, test_generation_config, test_generation_runs, exercises, corpus_sources, corpus_collocations, collocation_packs, pack_collocations, conversation_domains, personas, persona_pairs, scenarios, conversations, conversation_generation_queue, word_assets, corpus_style_profiles, style_pack_items, pack_style_items.

The remaining 21 are content/infrastructure tables — they don't hold per-user state. Decide whether to lock them down or treat them as deliberately public. None hold sensitive personal data; the anon key can already read all of `tests`, `questions`, and `mysteries` via existing RLS policies.

## Related Pages

- [[database/schema.tech]] — Full DDL: every column, type, FK, index, trigger, RLS policy
- [[database/rpcs.tech]] — All ~77 application RPCs with full SQL definitions
- [[algorithms/elo-ranking]] — How ELO is calculated
- [[algorithms/vocabulary-ladder]] — Phase 8/10 momentum bands
- [[features/comprehension-tests]] — Test structure and flow
- [[features/exercises]] — Exercise types and sources
- [[features/vocab-dojo]] — Adaptive ladder serving
