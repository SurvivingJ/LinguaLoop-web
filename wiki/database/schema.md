---
title: Data Model Overview
type: overview
status: complete
tech_page: ./schema.tech.md
last_updated: 2026-04-14
open_questions:
  - "Language Packs will need new tables — pack conversations, pack word lists, pack exercise links. Schema TBD."
---

# Data Model Overview

## Purpose

LinguaLoop's database tracks everything needed to run an adaptive language-learning platform: users and their skill levels, the content they study, how they perform, and the tokens they spend. The schema currently contains **62 tables**, **1 custom enum**, **3 views**, **11 triggers**, and **48 application RPCs**.

## Conceptual Domains

### 1. Dimension / Lookup Tables (10 tables)

Lookup tables that rarely change. Cached at startup by DimensionService.

- **dim_languages** (RLS) — supported target languages with per-language AI model config (separate models for exercises, sentences, conversations, vocab prompts), TTS voice IDs, and TTS speed. Model columns are being migrated to `language_model_config` table.
- **language_model_config** — normalized key-value store for per-language LLM model assignments (task_key + model_name). Replaces the growing model columns on dim_languages.
- **dim_complexity_tiers** (RLS) — 6 age-based difficulty bands (replacing CEFR) with ELO ranges and word-count ranges
- **dim_test_types** (RLS) — reading, listening, dictation
- **dim_question_types** (RLS) — cognitive-level classifications for MC questions (6 types)
- **dim_subscription_tiers** (RLS) — free, premium, enterprise with daily limits, token grants, and feature flags (admin, moderator, generate, custom, analytics)
- **dim_status** (RLS) — shared status dimension (5 codes: active, pending, etc.)
- **dim_lens** (RLS) — 8 topic generation "angles" (lens_code + prompt_hint)
- **dim_grammar_patterns** (RLS) — grammatical structures per language/complexity tier with example sentences
- **dim_vocabulary** (RLS) — master lemma dictionary (3,646 entries) with frequency ranks, POS tags, phrase types, semantic classes, and component lemmas for multi-word expressions
- **dim_word_senses** (RLS) — definitions, IPA pronunciations, examples, morphological forms per vocab entry per definition language (3,932 entries). Validated by users.

### 2. Users & Auth (8 tables)

- **users** (RLS) — linked to Supabase auth.users via FK on id; tracks subscription tier, activity stats, soft-delete (deleted_at/anonymized_at), organization membership, exercise preferences (session_size)
- **user_languages** (RLS) — which languages a user is studying (7 active records)
- **user_skill_ratings** (RLS) — per-user, per-language, per-test-type ELO ratings (default 1200)
- **user_tokens** (RLS) — purchased + bonus token balances with spending breakdown (tests, generation, premium features, referrals, achievements)
- **user_vocabulary_knowledge** — BKT probability per word sense (p_known, comprehension/word-test evidence counts, status: unknown/learning/known)
- **user_flashcards** — FSRS-scheduled review cards per word sense (stability, difficulty, reps, lapses, state)
- **user_word_ladder** — tracks current level (1-9) in the vocabulary ladder per word sense, with promotion/demotion counters (first_try_success_count, first_try_failure_count, consecutive_failures), word_state (new/active/fragile/stable/mastered), and review scheduling
- **user_exercise_sessions** (RLS) — daily exercise session state per user per language

### 3. Organizations (2 tables)

- **organizations** (RLS) — B2B multi-tenancy: name, slug, subscription tier, max users, token pool
- **organization_members** (RLS) — user-org role bindings (composite PK, role defaults to 'student')

### 4. Content Pipeline — Tests (9 tables)

- **categories** — 33 topic buckets with cooldown scheduling (cooldown_days, last_used_at, total_topics_generated)
- **topics** — 43 specific concepts with pgvector embeddings for similarity dedup, linked to category + lens
- **production_queue** — topic-to-test generation pipeline state (109 items), status FK to dim_status
- **tests** (RLS) — 254 comprehension tests with slug, transcript, audio URL, difficulty, tier, vocab_sense_ids/stats, generation model
- **questions** (RLS) — 1,223 MC questions (5 per test), typed with answer explanations and sense_ids
- **test_skill_ratings** (RLS) — per-test ELO rating (default 1400, 471 ratings)
- **test_attempts** (RLS) — 48 user submission records with score, ELO before/after, idempotency key, attempt number
- **daily_test_loads** — pre-computed daily test sets per user/language
- **daily_test_load_items** — junction table for daily_test_loads test IDs with FK integrity (replaces JSONB arrays). Tracks completion status and display order.
- **question_type_distributions** — maps difficulty levels to 5 question type slots (9 rows)

### 5. Content — Exercises & Vocabulary (6 tables)

- **exercises** — 7,692 generated items (cloze, translation, etc.) linked to exactly one source type via the `exercise_source_type` enum (grammar, vocabulary, collocation, conversation). Each links to grammar_pattern, word_sense, corpus_collocation, and/or conversation. Includes IRT difficulty/discrimination, ladder_level.
- **exercise_attempts** — user responses with correctness, first-attempt flag, time taken, sense tracking
- **user_exercise_history** (RLS) — purpose-built anti-repetition table. Auto-populated via trigger from exercise_attempts. Purpose-built indexes for session builder lookups (by user+language+date, by user+sense).
- **word_assets** — generated assets per word sense (content JSON, model used, prompt version, validation)
- **word_quiz_results** — detailed per-question results from vocab quizzes (20 results)
- **vocabulary_review_queue** (RLS) — queue for human review of vocab issues (type, proposed definition, resolution)
- **user_pack_selections** (RLS) — which collocation packs a user has chosen (uuid FK to users, composite PK)

### 6. Content — Corpus & Collocations (4 tables)

- **corpus_sources** — 8 ingested text sources per language (type, URL, title, raw text/path, word count)
- **corpus_collocations** — 40 extracted n-grams with PMI, LMI, t-score, log-likelihood, dependency relation, substitution entropy
- **collocation_packs** — curated groups of collocations (name, type, difficulty range, public flag)
- **pack_collocations** — many-to-many link (pack_id + collocation_id unique)

### 7. Conversation System (6 tables)

- **conversation_domains** — 14 conversational topic domains with keywords, suitable registers/relationship types
- **personas** — 386 generated character profiles with archetype, personality JSON, register, expertise domains, system prompt
- **persona_pairs** — 22,951 pair combinations with compatibility score, relationship type, suitable domains
- **scenarios** — 420 conversation scenarios with domain, complexity tier, goals, cultural notes
- **conversations** — 261 generated dialogues with turns (JSONB), corpus features, quality score, QC pass flag
- **conversation_generation_queue** — pipeline for batch conversation generation

### 8. Mystery System (6 tables)

- **mysteries** (RLS) — murder mystery stories with suspects (JSONB), solution, target vocab, generation model
- **mystery_scenes** (RLS) — ordered scenes with transcript, audio URL, clue text/type, target words
- **mystery_questions** (RLS) — comprehension questions per scene with deduction flag
- **mystery_progress** (RLS) — user's current position in a mystery (scene, notebook state, mode)
- **mystery_attempts** (RLS) — scored attempts with ELO before/after
- **mystery_skill_ratings** (RLS) — per-mystery ELO rating (default 1400)

### 9. Token Economy (2 tables)

- **user_tokens** (RLS) — balance tracking (see Users section above)
- **token_transactions** (RLS) — full ledger of all token movements: consumed, added, balance after, action, payment intent, package, test/attempt references, invalidation support

### 10. Infrastructure & Telemetry (6 tables)

- **prompt_templates** — 102 versioned LLM prompts per task per language (unique on task+lang+version)
- **test_generation_runs** — 17 batch run telemetry records (API calls, costs, timing)
- **topic_generation_runs** — 6 topic discovery telemetry records
- **test_generation_config** — 4 key-value config entries
- **app_error_logs** (RLS) — 21 client-side error records. FK on user_id to users with ON DELETE SET NULL.
- **flagged_content** (RLS) — content safety flags with category JSONB

## Enum Types

| Enum | Values |
|------|--------|
| `exercise_source_type` | grammar, vocabulary, collocation, conversation |

## Views

| View | Purpose |
|------|---------|
| `corpus_statistics` | Aggregates collocations by language, type, n-gram size with avg PMI, frequency, validated count |
| `vw_distractor_error_analysis` | Analyzes incorrect cloze exercise attempts by grammar pattern and distractor error type |
| `vw_exercise_performance_by_type` | Exercise accuracy % grouped by exercise type, complexity tier, language |

## Triggers

| Table | Event | Function |
|-------|-------|----------|
| `dim_vocabulary` | BEFORE UPDATE | `update_updated_at_column()` |
| `dim_word_senses` | BEFORE UPDATE | `update_updated_at_column()` |
| `test_attempts` | AFTER INSERT | `update_test_attempts_count()` |
| `test_attempts` | AFTER INSERT | `update_skill_attempts_count()` |
| `exercise_attempts` | AFTER INSERT | `sync_exercise_history()` |
| `tests` | BEFORE UPDATE | `update_updated_at_column()` |
| `user_languages` | BEFORE UPDATE | `update_updated_at_column()` |
| `user_reports` | BEFORE UPDATE | `update_updated_at_column()` |
| `user_skill_ratings` | BEFORE UPDATE | `update_updated_at_column()` |
| `users` | AFTER INSERT | `create_user_dependencies()` |
| `users` | BEFORE UPDATE | `update_updated_at_column()` |

## Key Relationships

```
User ──→ User Skill Ratings (per language + test type) ──→ ELO
User ──→ User Vocabulary Knowledge (per word sense) ──→ BKT p_known
User ──→ User Flashcards (per word sense) ──→ FSRS schedule
User ──→ User Word Ladder (per word sense) ──→ current level (1-9)
User ──→ Test Attempts ──→ Test ──→ Questions
User ──→ Exercise Attempts ──→ Exercise ──→ Grammar Pattern | Word Sense | Collocation | Conversation
User ──→ Mystery Progress ──→ Mystery ──→ Scenes ──→ Questions
User ──→ User Tokens ──→ Token Transactions
Test ──→ Test Skill Ratings ──→ ELO
Topic ──→ Tests (multiple tests per topic)
Category ──→ Topics ──→ Production Queue
Category ──→ Conversation Domains ──→ Scenarios ──→ Conversations
Personas ──→ Persona Pairs ──→ Conversations
dim_vocabulary ──→ dim_word_senses ──→ Word Assets / Exercises / User Knowledge / Flashcards
dim_languages ──→ (central FK hub: nearly every content table references it)
```

## Row-Level Security

27 tables have RLS enabled: app_error_logs, dim_complexity_tiers, dim_grammar_patterns, dim_languages, dim_lens, dim_question_types, dim_status, dim_subscription_tiers, dim_test_types, dim_vocabulary, dim_word_senses, flagged_content, mysteries, mystery_attempts, mystery_progress, mystery_questions, mystery_scenes, mystery_skill_ratings, organization_members, organizations, questions, test_attempts, test_skill_ratings, tests, token_transactions, user_exercise_history, user_exercise_sessions, user_languages, user_pack_selections, user_reports, user_skill_ratings, user_tokens, users, vocabulary_review_queue.

## Related Pages

- [[database/schema.tech]] — Full DDL: every column, type, FK, index, trigger
- [[database/rpcs.tech]] — All 48 application RPCs with full definitions
- [[algorithms/elo-ranking]] — How ELO is calculated
- [[algorithms/vocabulary-ladder]] — 10-level word acquisition ladder
- [[features/comprehension-tests]] — Test structure and flow
- [[features/exercises]] — Exercise types and sources
- [[features/vocab-dojo]] — Adaptive exercise serving
