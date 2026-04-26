---
title: Database Schema — Technical Specification
type: schema-tech
status: complete
prose_page: ../database/schema.md
last_updated: 2026-04-24
dependencies:
  - "Supabase PostgreSQL"
  - "pgvector extension"
  - "pgcrypto extension"
  - "intarray extension"
breaking_change_risk: medium
---

# Database Schema — Technical Specification

## Overview

The schema lives in Supabase PostgreSQL with Row-Level Security (RLS) policies on user-facing tables. It uses a tiered dependency structure (Tier 0 = no FKs, through Tier 5 = deepest dependencies). All tables are in the `public` schema unless otherwise noted. Authentication delegates to Supabase `auth.users` with a mirror `users` table in public.

**Total tables:** 65 (users_backup dropped; user_exercise_history, language_model_config, daily_test_load_items, corpus_style_profiles, style_pack_items, pack_style_items added)
**Enum types:** 1 (`exercise_source_type`)
**Views:** 3
**Triggers:** 11 across 9 tables

## Extensions

- **pgvector** -- `vector(1536)` columns for topic embedding similarity search (IVFFlat index)
- **pgcrypto** -- `gen_random_uuid()` for UUID primary keys
- **intarray** -- `gin__int_ops` for integer array intersection (vocab sense overlap)

---

## 1. Dimension / Lookup Tables

These tables have no outbound foreign keys (Tier 0). They define the reference data used across the system.

---

### `dim_languages`

Supported languages with AI model configuration, TTS settings, and grammar tooling.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | smallint | NO | nextval('dim_languages_id_seq') | PK |
| `language_code` | varchar | NO | | UNIQUE. Short code (e.g. en, es, fr) |
| `language_name` | varchar | NO | | |
| `native_name` | varchar | YES | | |
| `iso_639_1` | char(2) | YES | | Two-letter ISO 639-1 |
| `iso_639_3` | char(3) | YES | | |
| `is_active` | boolean | YES | true | |
| `display_order` | integer | YES | 0 | |
| `prose_model` | varchar | YES | 'google/gemini-2.5-flash-lite' | LLM model for prose generation (OpenRouter format) |
| `question_model` | varchar | YES | 'google/gemini-2.5-flash-lite' | LLM model for question generation |
| `exercise_model` | text | YES | | |
| `exercise_sentence_model` | text | YES | | |
| `conversation_model` | text | YES | | |
| `vocab_prompt1_model` | text | YES | | |
| `vocab_prompt2_model` | text | YES | | |
| `vocab_prompt3_model` | text | YES | | |
| `tts_voice_ids` | jsonb | YES | '["alloy","echo","fable","onyx","nova","shimmer"]' | Array of OpenAI voice IDs |
| `tts_speed` | numeric | YES | 1.0 | CHECK: 0.25-4.0. TTS playback speed multiplier |
| `grammar_check_enabled` | boolean | YES | true | Enable LanguageTool grammar validation |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `dim_languages_pkey (id)`
- **Unique:** `dim_languages_language_code_key (language_code)`
- **Indexes:** `idx_dim_languages_active (is_active)`, `idx_dim_languages_code (language_code)`
- **RLS:** Enabled
- **Referenced by:** tests, test_attempts, user_languages, user_skill_ratings, personas, production_queue, prompt_templates, scenarios, conversations, conversation_generation_queue, categories, dim_vocabulary, dim_word_senses, user_vocabulary_knowledge, user_flashcards, mysteries, dim_grammar_patterns, mystery_attempts, exercises, corpus_sources, corpus_collocations, collocation_packs, corpus_style_profiles, style_pack_items, word_assets

---

### `dim_test_types`

Test/skill types (reading, listening, dictation, pinyin).

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | smallint | NO | nextval('dim_test_types_id_seq') | PK |
| `type_code` | varchar | NO | | UNIQUE |
| `type_name` | varchar | NO | | |
| `description` | text | YES | | |
| `category` | varchar | YES | | |
| `requires_audio` | boolean | YES | false | Whether this test type requires audio files |
| `is_active` | boolean | YES | true | |
| `display_order` | integer | YES | 0 | |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `dim_test_types_pkey (id)`
- **Unique:** `dim_test_types_type_code_key (type_code)`
- **Indexes:** `idx_dim_test_types_active (is_active)`, `idx_dim_test_types_code (type_code)`
- **RLS:** Enabled
- **Referenced by:** test_skill_ratings, user_skill_ratings, test_attempts, mystery_attempts

---

### `dim_subscription_tiers`

Subscription tier permissions, daily limits, and feature flags.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | smallint | NO | GENERATED ALWAYS AS IDENTITY | PK |
| `tier_code` | varchar | NO | | UNIQUE |
| `tier_name` | varchar | NO | | |
| `display_name` | varchar | NO | | |
| `description` | text | YES | | |
| `daily_free_tests` | integer | NO | 0 | CHECK >= 0 |
| `monthly_token_grant` | integer | NO | 0 | CHECK >= 0 |
| `tokens_per_test` | integer | NO | 10 | CHECK >= 0 |
| `can_generate_tests` | boolean | YES | false | |
| `can_create_custom_tests` | boolean | YES | false | |
| `can_access_analytics` | boolean | YES | false | |
| `max_custom_tests` | integer | YES | 0 | CHECK >= 0 |
| `is_admin` | boolean | YES | false | |
| `is_moderator` | boolean | YES | false | |
| `is_active` | boolean | YES | true | |
| `display_order` | integer | YES | 0 | |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `dim_subscription_tiers_pkey (id)`
- **Unique:** `dim_subscription_tiers_tier_code_key (tier_code)`
- **Indexes:** `idx_subscription_tiers_code (tier_code WHERE is_active=true)`
- **RLS:** Enabled
- **Referenced by:** users, organizations

---

### `dim_complexity_tiers`

Complexity tier configuration including word counts and initial ELO. Replaces CEFR levels.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | smallint | NO | nextval('dim_complexity_tiers_id_seq') | PK |
| `tier_code` | varchar | NO | | UNIQUE (e.g. T1-T6) |
| `difficulty_min` | integer | NO | | |
| `difficulty_max` | integer | NO | | |
| `word_count_min` | integer | NO | | |
| `word_count_max` | integer | NO | | |
| `initial_elo` | integer | NO | | |
| `description` | text | YES | | |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `dim_complexity_tiers_pkey (id)` (renamed from dim_cefr_levels_pkey in Phase 2)
- **Unique:** `dim_complexity_tiers_tier_code_key (tier_code)`
- **RLS:** Enabled (Phase 6). Policies: authenticated read, service_role full access.
- **No outbound FKs, no inbound FKs as a constraint (referenced by convention via tier_code text columns)**

---

### `dim_question_types`

Taxonomy of question types based on cognitive complexity (Bloom's).

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | smallint | NO | nextval('dim_question_types_id_seq') | PK |
| `type_code` | varchar | NO | | UNIQUE |
| `type_name` | varchar | NO | | |
| `description` | text | YES | | |
| `cognitive_level` | integer | NO | | CHECK 1-3. 1=Recognition, 2=Comprehension, 3=Analysis |
| `is_active` | boolean | YES | true | |
| `display_order` | integer | YES | 0 | |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `dim_question_types_pkey (id)`
- **Unique:** `dim_question_types_type_code_key (type_code)`
- **Indexes:** `idx_question_types_active (is_active WHERE is_active=true)`, `idx_question_types_cognitive (cognitive_level)`
- **RLS:** Enabled (Phase 6). Policies: authenticated read, service_role full access.
- **Referenced by:** questions (via id), mystery_questions (via id), question_type_distributions (via type_code)

---

### `dim_status`

Shared status codes for queue/pipeline tables.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | nextval('dim_status_id_seq') | PK |
| `status_code` | varchar | NO | | UNIQUE |
| `status_name` | varchar | NO | | |
| `description` | text | YES | | |
| `is_active` | boolean | YES | true | |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `dim_status_pkey (id)`
- **Unique:** `dim_status_status_code_key (status_code)`
- **RLS:** Enabled (Phase 6). Policies: authenticated read, service_role full access.
- **Referenced by:** categories, production_queue, conversation_generation_queue

---

### `dim_lens`

Topic generation "angles" or perspectives for content variety.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | nextval('dim_lens_id_seq') | PK |
| `lens_code` | varchar | NO | | UNIQUE |
| `display_name` | varchar | NO | | |
| `description` | text | YES | | |
| `prompt_hint` | text | YES | | |
| `is_active` | boolean | YES | true | |
| `sort_order` | integer | YES | 0 | |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `dim_lens_pkey (id)`
- **Unique:** `dim_lens_lens_code_key (lens_code)`
- **RLS:** Enabled (Phase 6). Policies: authenticated read, service_role full access.
- **Referenced by:** topics

---

### `dim_vocabulary`

Master vocabulary lemma registry. Each lemma is unique per language.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | GENERATED ALWAYS AS IDENTITY | PK |
| `language_id` | smallint | NO | | FK -> dim_languages |
| `lemma` | text | NO | | |
| `phrase_type` | text | YES | 'single_word' | |
| `component_lemmas` | text[] | YES | | For multi-word entries |
| `part_of_speech` | text | YES | | |
| `frequency_rank` | real | YES | | |
| `level_tag` | text | YES | | |
| `semantic_class` | text | YES | | |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `dim_vocabulary_pkey (id)`
- **Unique:** `uq_vocab_lemma (language_id, lemma)`
- **Indexes:** `idx_dv_level_tag (level_tag)`, `idx_vocab_components GIN (component_lemmas WHERE NOT NULL)`, `idx_vocab_language (language_id)`, `idx_vocab_lemma_lookup (language_id, lemma text_pattern_ops)`, `idx_vocab_phrase_type (phrase_type WHERE <>'single_word')`
- **Foreign Keys:** `language_id` -> `dim_languages.id`
- **Triggers:** BEFORE UPDATE -> `update_updated_at_column()`
- **RLS:** Enabled
- **Referenced by:** dim_word_senses, vocabulary_review_queue

---

### `dim_word_senses`

Individual word senses (definitions) linked to vocabulary lemmas.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | GENERATED ALWAYS AS IDENTITY | PK |
| `vocab_id` | integer | NO | | FK -> dim_vocabulary |
| `definition_language_id` | smallint | NO | | FK -> dim_languages |
| `definition` | text | NO | | |
| `pronunciation` | text | YES | | |
| `ipa_pronunciation` | text | YES | | |
| `example_sentence` | text | YES | | |
| `usage_notes` | text | YES | | |
| `sense_rank` | integer | NO | 1 | Ordering within vocab_id |
| `usage_frequency` | text | YES | 'common' | CHECK: common/uncommon/rare/archaic |
| `semantic_category` | text | YES | | |
| `morphological_forms` | jsonb | YES | | |
| `is_validated` | boolean | YES | false | |
| `validated_by` | uuid | YES | | FK -> users |
| `validation_notes` | text | YES | | |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `dim_word_senses_pkey (id)`
- **Unique:** `uq_sense_definition (vocab_id, definition_language_id, definition)`
- **Indexes:** `idx_senses_lang (definition_language_id)`, `idx_senses_rank (vocab_id, sense_rank)`, `idx_senses_vocab (vocab_id)`
- **Foreign Keys:** `vocab_id` -> `dim_vocabulary.id`, `definition_language_id` -> `dim_languages.id`, `validated_by` -> `users.id`
- **Triggers:** BEFORE UPDATE -> `update_updated_at_column()`
- **RLS:** Enabled
- **Referenced by:** exercises, word_assets, user_word_ladder, word_quiz_results, user_flashcards, user_vocabulary_knowledge, vocabulary_review_queue

---

### `dim_grammar_patterns`

Grammar pattern definitions for exercise generation.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | nextval('dim_grammar_patterns_id_seq') | PK |
| `pattern_code` | text | NO | | UNIQUE |
| `pattern_name` | text | NO | | |
| `description` | text | NO | | |
| `user_facing_description` | text | NO | | |
| `example_sentence` | text | NO | | |
| `example_sentence_en` | text | YES | | |
| `language_id` | integer | NO | | FK -> dim_languages |
| `complexity_tier` | text | NO | | CHECK: T1-T6 |
| `category` | text | NO | | CHECK: tense/aspect/voice/particles/word_order/modality/clause_structure/conjugation/honorifics/measure_words/complement |
| `is_active` | boolean | NO | true | |
| `created_at` | timestamptz | NO | now() | |

- **Primary Key:** `dim_grammar_patterns_pkey (id)`
- **Unique:** `dim_grammar_patterns_pattern_code_key (pattern_code)`
- **Indexes:** `idx_grammar_patterns_active (is_active WHERE is_active=true)`, `idx_grammar_patterns_language (language_id)`, `idx_grammar_patterns_tier (complexity_tier)`
- **Foreign Keys:** `language_id` -> `dim_languages.id`
- **RLS:** Enabled (Phase 6). Policies: authenticated read, service_role full access.
- **Referenced by:** exercises

---

### `language_model_config`

Normalized key-value store for per-language LLM model assignments (Phase 4). Replaces the growing model columns on `dim_languages`. Old columns are NOT dropped yet — they will be deprecated after all Python callers migrate.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | GENERATED ALWAYS AS IDENTITY | PK |
| `language_id` | smallint | NO | | FK -> dim_languages |
| `task_key` | text | NO | | e.g. prose, question, exercise, exercise_sentence, conversation, vocab_prompt1, vocab_prompt2, vocab_prompt3 |
| `model_name` | text | NO | | OpenRouter model ID |
| `is_active` | boolean | NO | true | |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `language_model_config_pkey (id)`
- **Unique:** `(language_id, task_key)`
- **Indexes:** `idx_lmc_language (language_id)`, `idx_lmc_task (task_key, language_id WHERE is_active=true)`
- **Foreign Keys:** `language_id` -> `dim_languages.id`
- **RLS:** Disabled
- **Helper RPC:** `get_model_for_task(task_key, language_id)` returns model_name with active filter.

---

## 2. User & Auth Tables

---

### `users`

Public mirror of `auth.users`. Auto-created by trigger on auth signup.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | | PK. FK -> auth.users.id |
| `email` | text | NO | | UNIQUE |
| `display_name` | text | YES | | |
| `email_verified` | boolean | YES | false | |
| `subscription_tier_id` | smallint | NO | 1 | FK -> dim_subscription_tiers |
| `organization_id` | uuid | YES | | FK -> organizations |
| `total_tests_taken` | integer | YES | 0 | |
| `total_tests_generated` | integer | YES | 0 | |
| `last_activity_at` | timestamptz | YES | | |
| `last_free_test_date` | date | YES | CURRENT_DATE - 1 day | |
| `free_tests_used_today` | integer | YES | 0 | |
| `total_free_tests_used` | integer | YES | 0 | |
| `exercise_preferences` | jsonb | YES | '{"session_size": 20}' | |
| `deleted_at` | timestamptz | YES | | Soft delete |
| `anonymized_at` | timestamptz | YES | | GDPR anonymization timestamp |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |
| `last_login` | timestamptz | YES | now() | |

- **Primary Key:** `users_pkey (id)`
- **Unique:** `users_email_key (email)`
- **Indexes:** `idx_users_active (id WHERE deleted_at IS NULL)`, `idx_users_email (email)`, `idx_users_free_test_date (last_free_test_date)`, `idx_users_organization (organization_id WHERE NOT NULL)`, `idx_users_subscription_tier (subscription_tier_id)`
- **Foreign Keys:** `id` -> `auth.users.id`, `subscription_tier_id` -> `dim_subscription_tiers.id`, `organization_id` -> `organizations.id`
- **Triggers:** AFTER INSERT -> `create_user_dependencies()`, BEFORE UPDATE -> `update_updated_at_column()`
- **RLS:** Enabled (Phase 6). Policies: users read own profile, users update own profile, service_role full access, admin read all users.
- **Referenced by:** test_attempts, user_skill_ratings, tests (gen_user), user_languages, user_tokens, token_transactions, flagged_content, user_exercise_sessions, organization_members, dim_word_senses (validated_by), vocabulary_review_queue (reviewed_by), user_vocabulary_knowledge, user_flashcards, word_quiz_results, mysteries (gen_user), mystery_progress, mystery_attempts, exercise_attempts, user_word_ladder, user_exercise_history, user_pack_selections

---

> **`users_backup` — DROPPED** (Phase 1 migration). Was an empty legacy backup table with no PK.
- **RLS:** Disabled

---

### `user_languages`

Per-user language enrollment and test tracking.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `user_id` | uuid | NO | | FK -> users |
| `language_id` | smallint | NO | | FK -> dim_languages |
| `total_tests_taken` | integer | YES | 0 | |
| `last_test_date` | date | YES | | |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `user_languages_pkey (id)`
- **Unique:** `user_languages_user_id_language_id_key (user_id, language_id)`
- **Indexes:** `idx_user_languages_language_id (language_id)`
- **Foreign Keys:** `user_id` -> `users.id`, `language_id` -> `dim_languages.id`
- **Triggers:** BEFORE UPDATE -> `update_updated_at_column()`
- **RLS:** Enabled

---

### `user_skill_ratings`

Per-user ELO ratings scoped to language + test type.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `user_id` | uuid | NO | | FK -> users |
| `language_id` | smallint | NO | | FK -> dim_languages |
| `test_type_id` | smallint | NO | | FK -> dim_test_types |
| `elo_rating` | integer | YES | 1200 | CHECK: 400-3000 |
| `tests_taken` | integer | YES | 0 | CHECK >= 0 |
| `last_test_date` | date | YES | | |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `user_skill_ratings_pkey (id)`
- **Unique Constraint:** `UNIQUE (user_id, language_id, test_type_id)`
- **Indexes:** `idx_user_skill_ratings_language_test_type (language_id, test_type_id)`
- **Foreign Keys:** `user_id` -> `users.id`, `language_id` -> `dim_languages.id`, `test_type_id` -> `dim_test_types.id`
- **Triggers:** BEFORE UPDATE -> `update_updated_at_column()`
- **RLS:** Enabled

---

### `user_exercise_sessions`

Tracks a user's current exercise session (exercise set and completion state).

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `user_id` | uuid | NO | | FK -> users |
| `language_id` | smallint | NO | | FK -> dim_languages (fixed in Phase 2: was integer, no FK) |
| `load_date` | date | NO | CURRENT_DATE | |
| `exercise_ids` | jsonb | NO | | Array of exercise UUIDs in session |
| `completed_ids` | jsonb | YES | '[]' | Exercises already completed |
| `session_size` | integer | NO | | |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `user_exercise_sessions_pkey (user_id, language_id)`
- **Foreign Keys:** `user_id` -> `users.id`, `language_id` -> `dim_languages.id` (Phase 2)
- **RLS:** Enabled

---

## 3. Content Pipeline Tables

Tables for topic generation, test creation, and question management.

---

### `categories`

Content categories for topic generation with cooldown rotation.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | nextval('categories_id_seq') | PK |
| `name` | varchar | NO | | |
| `description` | text | YES | | |
| `status_id` | integer | YES | 2 | FK -> dim_status |
| `target_language_id` | integer | YES | | FK -> dim_languages |
| `cooldown_days` | integer | YES | 7 | |
| `last_used_at` | timestamptz | YES | | |
| `total_topics_generated` | integer | YES | 0 | |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `categories_pkey (id)`
- **Indexes:** `idx_categories_rotation (status_id, target_language_id, last_used_at)`
- **Foreign Keys:** `status_id` -> `dim_status.id`, `target_language_id` -> `dim_languages.id`
- **RLS:** Disabled
- **Referenced by:** topics, conversation_domains, topic_generation_runs

---

### `topics`

Generated topic concepts with embedding vectors for similarity deduplication.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `category_id` | integer | NO | | FK -> categories |
| `concept_english` | text | NO | | |
| `lens_id` | integer | NO | | FK -> dim_lens |
| `keywords` | jsonb | YES | '[]' | |
| `embedding` | vector(1536) | YES | | pgvector column |
| `semantic_signature` | text | YES | | |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `topics_pkey (id)`
- **Indexes:** `idx_topics_category (category_id)`, `idx_topics_embedding IVFFlat (embedding vector_cosine_ops, lists=100)`
- **Foreign Keys:** `category_id` -> `categories.id`, `lens_id` -> `dim_lens.id`
- **RLS:** Disabled
- **Referenced by:** production_queue, tests

---

### `production_queue`

Queue of topics awaiting test generation. Each entry produces ~3 tests.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `topic_id` | uuid | NO | | FK -> topics |
| `language_id` | integer | NO | | FK -> dim_languages |
| `status_id` | integer | YES | 1 | FK -> dim_status |
| `rejection_reason` | text | YES | | |
| `processed_at` | timestamptz | YES | | |
| `tests_generated` | integer | YES | 0 | Number of tests created (target: 3) |
| `error_log` | text | YES | | Error message if failed |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `production_queue_pkey (id)`
- **Unique:** `production_queue_topic_id_language_id_key (topic_id, language_id)`
- **Indexes:** `idx_production_queue_status (status_id, created_at)`
- **Foreign Keys:** `topic_id` -> `topics.id`, `language_id` -> `dim_languages.id`, `status_id` -> `dim_status.id`
- **RLS:** Disabled

---

### `tests`

Generated comprehension tests with transcript, audio, and vocabulary annotations.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `gen_user` | uuid | NO | | FK -> users. Who triggered generation |
| `slug` | text | NO | | UNIQUE |
| `title` | text | YES | | |
| `transcript` | text | YES | | |
| `audio_url` | text | YES | | |
| `difficulty` | integer | NO | | CHECK: 1-9 |
| `style` | text | YES | 'academic' | CHECK: academic/conversational/business/casual/technical |
| `tier` | text | NO | 'free-tier' | CHECK: free-tier/premium-tier/enterprise-tier |
| `language_id` | smallint | NO | | FK -> dim_languages |
| `organization_id` | uuid | YES | | FK -> organizations |
| `topic_id` | uuid | YES | | FK -> topics |
| `vocab_sense_ids` | integer[] | YES | '{}' | GIN-indexed array of dim_word_senses IDs |
| `vocab_sense_stats` | jsonb | YES | '{}' | Per-sense statistics |
| `vocab_token_map` | jsonb | YES | | Token-to-sense mapping |
| `total_attempts` | integer | YES | 0 | |
| `is_active` | boolean | YES | true | |
| `is_featured` | boolean | YES | false | |
| `is_custom` | boolean | YES | false | |
| `generation_model` | text | YES | 'gpt-4.1-nano' | |
| `pinyin_payload` | jsonb | YES | | Tokenised pinyin data for Chinese tests (tone trainer) |
| `audio_generated` | boolean | YES | false | |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `tests_pkey (id)`
- **Unique:** `tests_slug_key (slug)`
- **Indexes:** `idx_tests_active_tier (is_active, tier WHERE is_active=true)`, `idx_tests_featured (is_featured WHERE is_active=true)`, `idx_tests_language_id (language_id)`, `idx_tests_organization (organization_id WHERE NOT NULL)`, `idx_tests_tier_active (tier, is_active)`, `idx_tests_topic (topic_id)`, `idx_tests_vocab_senses GIN (vocab_sense_ids gin__int_ops)`
- **Foreign Keys:** `gen_user` -> `users.id`, `language_id` -> `dim_languages.id`, `organization_id` -> `organizations.id`, `topic_id` -> `topics.id`
- **Triggers:** BEFORE UPDATE -> `update_updated_at_column()`
- **RLS:** Enabled
- **Referenced by:** test_attempts, questions, test_skill_ratings, token_transactions, user_reports

---

### `questions`

Individual questions belonging to a test.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `test_id` | uuid | NO | | FK -> tests |
| `question_id` | text | NO | | Logical ID within test |
| `question_text` | text | NO | | |
| `choices` | jsonb | YES | | MC answer choices |
| `answer` | jsonb | NO | | Correct answer(s) |
| `answer_explanation` | text | YES | | |
| `question_type_id` | smallint | YES | | FK -> dim_question_types |
| `sense_ids` | integer[] | YES | | Vocabulary senses tested |
| `points` | integer | YES | 1 | |
| `audio_url` | text | YES | | |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `questions_pkey (id)`
- **Unique:** `unique_question_per_test (test_id, question_id)`
- **Indexes:** `idx_questions_test_id (test_id)`, `idx_questions_type (question_type_id)`
- **Foreign Keys:** `test_id` -> `tests.id`, `question_type_id` -> `dim_question_types.id`
- **RLS:** Enabled

---

### `test_skill_ratings`

Per-test ELO ratings scoped to test type.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `test_id` | uuid | NO | | FK -> tests |
| `test_type_id` | smallint | NO | | FK -> dim_test_types |
| `elo_rating` | integer | YES | 1400 | CHECK: 400-3000 |
| `total_attempts` | integer | YES | 0 | CHECK >= 0 |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `test_skill_ratings_pkey (id)`
- **Unique Constraint:** `UNIQUE (test_id, test_type_id)`
- **Indexes:** `idx_test_skill_ratings_test_id (test_id)`, `idx_test_skill_ratings_test_type_id (test_type_id)`
- **Foreign Keys:** `test_id` -> `tests.id`, `test_type_id` -> `dim_test_types.id`
- **RLS:** Enabled

---

### `test_attempts`

Records each user test completion with ELO snapshots.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `user_id` | uuid | NO | | FK -> users |
| `test_id` | uuid | NO | | FK -> tests |
| `language_id` | smallint | NO | | FK -> dim_languages |
| `test_type_id` | smallint | NO | | FK -> dim_test_types |
| `score` | integer | NO | | CHECK >= 0 |
| `total_questions` | integer | NO | | CHECK > 0 |
| `percentage` | real | YES | GENERATED (score/total_questions * 100) | CHECK: 0-100 |
| `user_elo_before` | integer | NO | | |
| `test_elo_before` | integer | NO | | |
| `user_elo_after` | integer | NO | | |
| `test_elo_after` | integer | NO | | |
| `was_free_test` | boolean | NO | false | |
| `tokens_consumed` | integer | NO | 0 | CHECK >= 0 |
| `idempotency_key` | uuid | YES | | Prevents duplicate submissions |
| `attempt_number` | integer | YES | 1 | |
| `is_first_attempt` | boolean | YES | true | |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `test_attempts_pkey (id)`
- **Unique:** `idx_unique_attempt_idempotency (user_id, idempotency_key WHERE NOT NULL)`
- **Indexes:** `idx_test_attempts_created_at (created_at DESC)`, `idx_test_attempts_language_id (language_id)`, `idx_test_attempts_test_id (test_id)`, `idx_test_attempts_test_type_id (test_type_id)`, `idx_test_attempts_user_id (user_id)`
- **Foreign Keys:** `user_id` -> `users.id`, `test_id` -> `tests.id`, `language_id` -> `dim_languages.id`, `test_type_id` -> `dim_test_types.id`
- **Triggers:** AFTER INSERT -> `update_test_attempts_count()`, AFTER INSERT -> `update_skill_attempts_count()` (x2 triggers)
- **RLS:** Enabled
- **Referenced by:** token_transactions, word_quiz_results

---

### `question_type_distributions`

Defines which question types to generate for each difficulty level (1-9).

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | nextval() | PK |
| `difficulty` | integer | NO | | UNIQUE. CHECK: 1-9 |
| `question_type_1` | varchar | NO | | FK -> dim_question_types.type_code |
| `question_type_2` | varchar | NO | | FK -> dim_question_types.type_code |
| `question_type_3` | varchar | NO | | FK -> dim_question_types.type_code |
| `question_type_4` | varchar | NO | | FK -> dim_question_types.type_code |
| `question_type_5` | varchar | NO | | FK -> dim_question_types.type_code |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `question_type_distributions_pkey (id)`
- **Unique:** `question_type_distributions_difficulty_key (difficulty)`
- **Foreign Keys:** All five `question_type_N` columns -> `dim_question_types.type_code`
- **RLS:** Disabled

---

### `prompt_templates`

Versioned LLM prompt templates scoped to task + language.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | nextval() | PK |
| `task_name` | varchar | NO | | |
| `language_id` | integer | NO | | FK -> dim_languages |
| `template_text` | text | NO | | |
| `version` | integer | YES | 1 | |
| `is_active` | boolean | YES | true | |
| `description` | text | YES | | |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `prompt_templates_pkey (id)`
- **Unique:** `idx_prompt_templates_task_lang_ver (task_name, language_id, version)`
- **Indexes:** `idx_prompt_templates_language (language_id)`, `idx_prompt_templates_task_language (task_name, language_id, is_active)`
- **Foreign Keys:** `language_id` -> `dim_languages.id`
- **RLS:** Disabled

---

### `test_generation_config`

Runtime key-value configuration for the test generation pipeline.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | nextval() | PK |
| `config_key` | varchar | NO | | UNIQUE |
| `config_value` | text | NO | | |
| `description` | text | YES | | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `test_generation_config_pkey (id)`
- **Unique:** `test_generation_config_config_key_key (config_key)`
- **RLS:** Disabled

---

### `test_generation_runs`

Daily metrics/telemetry for the test generation pipeline.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | nextval() | PK |
| `run_date` | date | NO | CURRENT_DATE | |
| `queue_items_processed` | integer | YES | 0 | |
| `tests_generated` | integer | YES | 0 | |
| `tests_failed` | integer | YES | 0 | |
| `prose_api_calls` | integer | YES | 0 | |
| `question_api_calls` | integer | YES | 0 | |
| `audio_api_calls` | integer | YES | 0 | |
| `grammar_checks_performed` | integer | YES | 0 | |
| `total_cost_usd` | numeric | YES | 0 | |
| `execution_time_seconds` | integer | YES | | |
| `error_message` | text | YES | | |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `test_generation_runs_pkey (id)`
- **Indexes:** `idx_test_gen_runs_date (run_date DESC)`
- **RLS:** Disabled

---

### `topic_generation_runs`

Metrics for the topic generation pipeline.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | nextval() | PK |
| `run_date` | date | NO | | |
| `category_id` | integer | YES | | FK -> categories |
| `category_name` | text | YES | | Denormalized for convenience |
| `topics_generated` | integer | YES | 0 | |
| `topics_rejected_similarity` | integer | YES | 0 | |
| `topics_rejected_gatekeeper` | integer | YES | 0 | |
| `candidates_proposed` | integer | YES | 0 | |
| `api_calls_llm` | integer | YES | 0 | |
| `api_calls_embedding` | integer | YES | 0 | |
| `total_cost_usd` | numeric | YES | 0 | |
| `execution_time_seconds` | integer | YES | | |
| `error_message` | text | YES | | |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `topic_generation_runs_pkey (id)`
- **Foreign Keys:** `category_id` -> `categories.id`
- **RLS:** Disabled

---

### `daily_test_loads`

Daily test sets assigned to users for their study session.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | bigint | NO | nextval() | PK |
| `user_id` | uuid | NO | | FK -> auth.users (direct) |
| `language_id` | integer | NO | | |
| `load_date` | date | NO | CURRENT_DATE | |
| `test_ids` | jsonb | NO | | Array of test UUIDs |
| `completed_test_ids` | jsonb | YES | '[]' | |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `daily_test_loads_pkey (id)`
- **Unique:** `daily_test_loads_user_id_language_id_load_date_key (user_id, language_id, load_date)`
- **Indexes:** `idx_daily_loads_lookup (user_id, language_id, load_date)`
- **Foreign Keys:** `user_id` -> `auth.users.id`
- **RLS:** Disabled
- **Note:** JSONB columns (test_ids, completed_test_ids) are being migrated to `daily_test_load_items` junction table.

---

### `daily_test_load_items`

Junction table for daily_test_loads test IDs with FK integrity (Phase 4). Replaces JSONB arrays in daily_test_loads.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `load_id` | bigint | NO | | FK -> daily_test_loads ON DELETE CASCADE |
| `test_id` | uuid | NO | | FK -> tests |
| `is_completed` | boolean | NO | false | |
| `completed_at` | timestamptz | YES | | |
| `display_order` | integer | NO | 0 | |

- **Primary Key:** `(load_id, test_id)` (composite)
- **Indexes:** `idx_dtli_load (load_id)`, `idx_dtli_test (test_id)`
- **Foreign Keys:** `load_id` -> `daily_test_loads.id` ON DELETE CASCADE, `test_id` -> `tests.id`
- **RLS:** Disabled (matches daily_test_loads pattern)

---

## 4. Conversation System

Tables for the persona-driven conversation generation pipeline.

---

### `conversation_domains`

Conversation topic domains linked to content categories.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | nextval() | PK |
| `category_id` | integer | YES | | FK -> categories |
| `domain_name` | text | NO | | |
| `description` | text | YES | | |
| `keywords` | text[] | YES | '{}' | |
| `suitable_registers` | text[] | YES | '{}' | |
| `suitable_relationship_types` | text[] | YES | '{}' | |
| `parent_domain` | text | YES | | |
| `is_active` | boolean | NO | true | |
| `created_at` | timestamptz | NO | now() | |

- **Primary Key:** `conversation_domains_pkey (id)`
- **Indexes:** `idx_conv_domains_active (is_active WHERE is_active=true)`
- **Foreign Keys:** `category_id` -> `categories.id`
- **RLS:** Disabled
- **Referenced by:** scenarios

---

### `personas`

Character profiles for conversation generation.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | nextval() | PK |
| `name` | text | NO | | |
| `language_id` | integer | NO | | FK -> dim_languages |
| `age` | integer | YES | | CHECK: 18-80 |
| `gender` | text | YES | | |
| `nationality` | text | YES | | |
| `occupation` | text | YES | | |
| `archetype` | text | NO | | |
| `personality` | jsonb | NO | '{}' | |
| `register` | text | YES | | CHECK: formal/semi-formal/informal |
| `expertise_domains` | text[] | YES | '{}' | |
| `relationship_types` | text[] | YES | '{}' | |
| `system_prompt` | text | NO | | |
| `generation_method` | text | NO | | CHECK: llm/template |
| `is_active` | boolean | NO | true | |
| `created_at` | timestamptz | NO | now() | |

- **Primary Key:** `personas_pkey (id)`
- **Indexes:** `idx_personas_active (is_active WHERE is_active=true)`, `idx_personas_archetype (archetype)`, `idx_personas_language (language_id)`, `idx_personas_register (register)`
- **Foreign Keys:** `language_id` -> `dim_languages.id`
- **RLS:** Disabled
- **Referenced by:** persona_pairs (persona_a_id, persona_b_id)

---

### `persona_pairs`

Pre-computed compatible pairs of personas for conversations.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | nextval() | PK |
| `persona_a_id` | integer | NO | | FK -> personas |
| `persona_b_id` | integer | NO | | FK -> personas |
| `compatibility_score` | numeric | YES | 0.50 | |
| `relationship_type` | text | YES | | |
| `dynamic_label` | text | YES | | |
| `suitable_domains` | text[] | YES | '{}' | |
| `created_at` | timestamptz | NO | now() | |

- **Primary Key:** `persona_pairs_pkey (id)`
- **Unique:** `persona_pairs_persona_a_id_persona_b_id_key (persona_a_id, persona_b_id)`
- **Indexes:** `idx_pairs_persona_a (persona_a_id)`, `idx_pairs_persona_b (persona_b_id)`
- **Foreign Keys:** `persona_a_id` -> `personas.id`, `persona_b_id` -> `personas.id`
- **RLS:** Disabled
- **Referenced by:** conversations, conversation_generation_queue

---

### `scenarios`

Conversation scenario templates with context and constraints.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | nextval() | PK |
| `domain_id` | integer | NO | | FK -> conversation_domains |
| `language_id` | integer | NO | | FK -> dim_languages |
| `title` | text | NO | | |
| `context_description` | text | NO | | |
| `goals` | jsonb | NO | '{}' | |
| `required_register` | text | YES | | |
| `required_relationship_type` | text | YES | | |
| `complexity_tier` | text | YES | | CHECK: T1-T6 |
| `keywords` | text[] | YES | '{}' | |
| `suitable_archetypes` | text[] | YES | '{}' | |
| `cultural_note` | text | YES | | |
| `generation_method` | text | NO | | CHECK: llm/template |
| `is_validated` | boolean | NO | false | |
| `is_active` | boolean | NO | true | |
| `created_at` | timestamptz | NO | now() | |

- **Primary Key:** `scenarios_pkey (id)`
- **Indexes:** `idx_scenarios_active (is_active WHERE is_active=true)`, `idx_scenarios_domain (domain_id)`, `idx_scenarios_language (language_id)`, `idx_scenarios_tier (complexity_tier)`
- **Foreign Keys:** `domain_id` -> `conversation_domains.id`, `language_id` -> `dim_languages.id`
- **RLS:** Disabled
- **Referenced by:** conversations, conversation_generation_queue

---

### `conversations`

Generated conversations (multi-turn dialogue) between persona pairs.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `scenario_id` | integer | NO | | FK -> scenarios |
| `persona_pair_id` | integer | NO | | FK -> persona_pairs |
| `language_id` | integer | NO | | FK -> dim_languages |
| `model_used` | text | NO | | |
| `temperature` | numeric | NO | | |
| `turn_count` | integer | NO | | |
| `turns` | jsonb | NO | | Array of dialogue turns |
| `corpus_features` | jsonb | YES | '{}' | Extracted linguistic features |
| `quality_score` | numeric | YES | | |
| `passed_qc` | boolean | NO | false | |
| `generation_batch_id` | uuid | YES | | |
| `is_active` | boolean | NO | true | |
| `created_at` | timestamptz | NO | now() | |

- **Primary Key:** `conversations_pkey (id)`
- **Indexes:** `idx_conv_active (is_active WHERE is_active=true)`, `idx_conv_batch (generation_batch_id)`, `idx_conv_language (language_id)`, `idx_conv_pair (persona_pair_id)`, `idx_conv_passed_qc (passed_qc)`, `idx_conv_scenario (scenario_id)`, `idx_conv_turns_gin (turns GIN)`
- **Foreign Keys:** `scenario_id` -> `scenarios.id`, `persona_pair_id` -> `persona_pairs.id`, `language_id` -> `dim_languages.id`
- **RLS:** Disabled
- **Referenced by:** exercises

---

### `conversation_generation_queue`

Queue for scheduling conversation generation jobs.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `scenario_id` | integer | NO | | FK -> scenarios |
| `persona_pair_id` | integer | NO | | FK -> persona_pairs |
| `language_id` | integer | NO | | FK -> dim_languages |
| `status_id` | integer | NO | 1 | FK -> dim_status |
| `conversations_generated` | integer | YES | 0 | |
| `error_log` | text | YES | | |
| `created_at` | timestamptz | NO | now() | |
| `processed_at` | timestamptz | YES | | |

- **Primary Key:** `conversation_generation_queue_pkey (id)`
- **Indexes:** `idx_conv_queue_lang (language_id)`, `idx_conv_queue_status (status_id)`
- **Foreign Keys:** `scenario_id` -> `scenarios.id`, `persona_pair_id` -> `persona_pairs.id`, `language_id` -> `dim_languages.id`, `status_id` -> `dim_status.id`
- **RLS:** Disabled

---

## 5. Vocabulary & Exercise System

Tables for vocabulary knowledge tracking, flashcards, exercises, and the word ladder.

---

### `exercises`

Generated exercises sourced from grammar patterns, vocabulary senses, collocations, conversations, or style pack items.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `language_id` | integer | NO | | FK -> dim_languages |
| `exercise_type` | text | NO | | Free-text exercise type identifier |
| `source_type` | exercise_source_type | NO | | ENUM: grammar/vocabulary/collocation/conversation/style |
| `grammar_pattern_id` | integer | YES | | FK -> dim_grammar_patterns (when source_type='grammar') |
| `word_sense_id` | integer | YES | | FK -> dim_word_senses (when source_type='vocabulary') |
| `corpus_collocation_id` | integer | YES | | (when source_type='collocation') |
| `conversation_id` | uuid | YES | | FK -> conversations (when source_type='conversation') |
| `style_pack_item_id` | bigint | YES | | FK -> style_pack_items (when source_type='style') |
| `word_asset_id` | bigint | YES | | FK -> word_assets |
| `content` | jsonb | NO | | Exercise content (questions, answers, etc.) |
| `tags` | jsonb | NO | '{}' | |
| `difficulty_static` | numeric | YES | | |
| `irt_difficulty` | numeric | NO | 0.0 | Item Response Theory difficulty |
| `irt_discrimination` | numeric | NO | 1.0 | IRT discrimination parameter |
| `complexity_tier` | text | YES | | CHECK: T1-T6 |
| `ladder_level` | integer | YES | | CHECK: 1-9 or NULL. Vocabulary ladder level |
| `pattern_code` | text | YES | | Denormalized grammar pattern code |
| `attempt_count` | integer | NO | 0 | |
| `correct_count` | integer | NO | 0 | |
| `is_active` | boolean | NO | true | |
| `generation_batch_id` | uuid | YES | | |
| `created_at` | timestamptz | NO | now() | |

- **Primary Key:** `exercises_pkey (id)`
- **Indexes:** `idx_exercises_active (is_active WHERE is_active=true)`, `idx_exercises_collocation (corpus_collocation_id WHERE NOT NULL)`, `idx_exercises_content_gin GIN (content)`, `idx_exercises_conversation (conversation_id WHERE NOT NULL)`, `idx_exercises_grammar (grammar_pattern_id WHERE NOT NULL)`, `idx_exercises_ladder (word_sense_id, ladder_level WHERE ladder_level NOT NULL)`, `idx_exercises_language (language_id)`, `idx_exercises_sense (word_sense_id WHERE NOT NULL)`, `idx_exercises_source (source_type)`, `idx_exercises_style_item (style_pack_item_id WHERE NOT NULL)`, `idx_exercises_tags_gin GIN (tags)`, `idx_exercises_tier (complexity_tier)`, `idx_exercises_type (exercise_type)`
- **Foreign Keys:** `language_id` -> `dim_languages.id`, `grammar_pattern_id` -> `dim_grammar_patterns.id`, `word_sense_id` -> `dim_word_senses.id`, `word_asset_id` -> `word_assets.id`, `conversation_id` -> `conversations.id`, `style_pack_item_id` -> `style_pack_items.id`
- **Constraints:** `chk_source_fk` — at least one of `grammar_pattern_id`, `word_sense_id`, `corpus_collocation_id`, `conversation_id`, `style_pack_item_id` must be non-null
- **RLS:** Disabled
- **Referenced by:** exercise_attempts

---

### `exercise_attempts`

Records each exercise attempt by a user.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `user_id` | uuid | NO | | FK -> users |
| `exercise_id` | uuid | YES | | FK -> exercises |
| `exercise_type` | text | YES | | Denormalized |
| `sense_id` | integer | YES | | Denormalized sense reference |
| `user_response` | jsonb | YES | | |
| `is_correct` | boolean | NO | | |
| `is_first_attempt` | boolean | YES | true | |
| `ladder_level` | integer | YES | | |
| `time_taken_ms` | integer | YES | | Response time in milliseconds |
| `created_at` | timestamptz | NO | now() | |

- **Primary Key:** `exercise_attempts_pkey (id)`
- **Indexes:** `idx_ea_exercise_id (exercise_id)`, `idx_ea_user_created (user_id, created_at DESC)`, `idx_ea_user_response_gin GIN (user_response)`, `idx_ea_user_sense_type (user_id, sense_id, exercise_type, created_at DESC)`
- **Foreign Keys:** `user_id` -> `users.id`, `exercise_id` -> `exercises.id`
- **RLS:** Disabled

---

### `user_exercise_history`

Purpose-built anti-repetition table (Phase 4). Auto-populated via `sync_exercise_history()` trigger on `exercise_attempts` INSERT. Replaces the pattern of scanning 500 rows from `exercise_attempts` per session build.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | bigint | NO | GENERATED ALWAYS AS IDENTITY | PK |
| `user_id` | uuid | NO | | FK -> users ON DELETE CASCADE |
| `language_id` | smallint | NO | | FK -> dim_languages |
| `exercise_id` | uuid | NO | | FK -> exercises |
| `sense_id` | integer | YES | | FK -> dim_word_senses |
| `exercise_type` | text | NO | | |
| `is_correct` | boolean | NO | | |
| `is_first_attempt` | boolean | NO | true | |
| `session_date` | date | NO | CURRENT_DATE | |
| `created_at` | timestamptz | NO | now() | |

- **Primary Key:** `user_exercise_history_pkey (id)`
- **Indexes:** `idx_ueh_anti_repeat (user_id, language_id, session_date, exercise_id)`, `idx_ueh_user_lang_date (user_id, language_id, session_date DESC)`, `idx_ueh_user_sense (user_id, sense_id, created_at DESC)`
- **Foreign Keys:** `user_id` -> `users.id` ON DELETE CASCADE, `language_id` -> `dim_languages.id`, `exercise_id` -> `exercises.id`, `sense_id` -> `dim_word_senses.id`
- **RLS:** Enabled. Policies: users read own history, service_role full access.
- **Trigger source:** Auto-populated from `exercise_attempts` via `trigger_sync_exercise_history` AFTER INSERT.

---

### `word_assets`

Pre-generated vocabulary learning assets (prompts/exercises) for word senses.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | bigint | NO | GENERATED ALWAYS AS IDENTITY | PK |
| `sense_id` | integer | NO | | FK -> dim_word_senses |
| `language_id` | integer | NO | | FK -> dim_languages |
| `asset_type` | text | NO | | CHECK: prompt1_core/prompt2_exercises/prompt3_transforms |
| `content` | jsonb | NO | | |
| `model_used` | text | NO | | |
| `prompt_version` | text | NO | 'v1' | |
| `is_valid` | boolean | NO | true | |
| `validation_errors` | text[] | YES | | |
| `generation_batch_id` | uuid | YES | | |
| `created_at` | timestamptz | NO | now() | |

- **Primary Key:** `word_assets_pkey (id)`
- **Unique:** `word_assets_sense_id_asset_type_key (sense_id, asset_type)`
- **Indexes:** `idx_word_assets_batch (generation_batch_id WHERE NOT NULL)`, `idx_word_assets_sense (sense_id)`, `idx_word_assets_valid (sense_id, asset_type WHERE is_valid=true)`
- **Foreign Keys:** `sense_id` -> `dim_word_senses.id`, `language_id` -> `dim_languages.id`
- **RLS:** Disabled
- **Referenced by:** exercises

---

### `user_vocabulary_knowledge`

Bayesian Knowledge Tracing (BKT) state for each user-sense pair.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | bigint | NO | GENERATED ALWAYS AS IDENTITY | PK |
| `user_id` | uuid | NO | | FK -> users |
| `sense_id` | integer | NO | | FK -> dim_word_senses |
| `language_id` | smallint | NO | | FK -> dim_languages |
| `p_known` | numeric | NO | 0.10 | Bayesian probability of knowing |
| `status` | text | NO | 'unknown' | CHECK: unknown/encountered/learning/probably_known/known/user_marked_unknown |
| `evidence_count` | integer | YES | 0 | |
| `comprehension_correct` | integer | YES | 0 | |
| `comprehension_wrong` | integer | YES | 0 | |
| `word_test_correct` | integer | YES | 0 | |
| `word_test_wrong` | integer | YES | 0 | |
| `last_evidence_at` | timestamptz | YES | | |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `user_vocabulary_knowledge_pkey (id)`
- **Unique:** `user_vocabulary_knowledge_user_id_sense_id_key (user_id, sense_id)`
- **Indexes:** `idx_uvk_user_language (user_id, language_id)`, `idx_uvk_user_pknown (user_id, p_known)`, `idx_uvk_user_status (user_id, status)`
- **Foreign Keys:** `user_id` -> `users.id`, `sense_id` -> `dim_word_senses.id`, `language_id` -> `dim_languages.id`
- **RLS:** Disabled

---

### `user_flashcards`

FSRS-based spaced repetition flashcards for vocabulary senses.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | bigint | NO | GENERATED ALWAYS AS IDENTITY | PK |
| `user_id` | uuid | NO | | FK -> users |
| `sense_id` | integer | NO | | FK -> dim_word_senses |
| `language_id` | smallint | NO | | FK -> dim_languages |
| `stability` | real | YES | 0 | FSRS stability parameter |
| `difficulty` | real | YES | 0.3 | FSRS difficulty parameter |
| `due_date` | date | YES | | |
| `last_review` | timestamptz | YES | | |
| `reps` | integer | YES | 0 | |
| `lapses` | integer | YES | 0 | |
| `state` | text | YES | 'new' | CHECK: new/learning/review/relearning |
| `example_sentence` | text | YES | | |
| `audio_url` | text | YES | | |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `user_flashcards_pkey (id)`
- **Unique:** `user_flashcards_user_id_sense_id_key (user_id, sense_id)`
- **Indexes:** `idx_uf_user_due (user_id, language_id, due_date)`, `idx_uf_user_state (user_id, state)`
- **Foreign Keys:** `user_id` -> `users.id`, `sense_id` -> `dim_word_senses.id`, `language_id` -> `dim_languages.id`
- **RLS:** Disabled

---

### `user_word_ladder`

Per-user vocabulary ladder progression (9 levels per sense) with promotion/demotion tracking.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `user_id` | uuid | NO | | FK -> users |
| `sense_id` | integer | NO | | FK -> dim_word_senses |
| `current_level` | integer | NO | 1 | CHECK: 1-9 |
| `active_levels` | integer[] | NO | '{1,2,3,4,5,6,7,8,9}' | Which levels are still in play |
| `first_try_success_count` | integer | NO | 0 | Cross-session success counter for promotion (Phase 4) |
| `first_try_failure_count` | integer | NO | 0 | Failure counter for demotion (Phase 4) |
| `consecutive_failures` | integer | NO | 0 | Consecutive first-attempt failures (Phase 4) |
| `total_attempts` | integer | NO | 0 | Total attempts across all sessions (Phase 4) |
| `word_state` | text | NO | 'active' | CHECK: new/active/fragile/stable/mastered (Phase 4) |
| `last_success_session_date` | date | YES | | Date of last successful session for cross-session validation (Phase 4) |
| `review_due_at` | timestamptz | YES | | Scheduled review time (Phase 4) |
| `updated_at` | timestamptz | NO | now() | |

- **Primary Key:** `user_word_ladder_pkey (user_id, sense_id)`
- **Indexes:** `idx_user_word_ladder_user (user_id)`, `idx_user_word_ladder_review_due (user_id, review_due_at WHERE review_due_at IS NOT NULL)`, `idx_user_word_ladder_state (user_id, word_state)`
- **Foreign Keys:** `user_id` -> `users.id`, `sense_id` -> `dim_word_senses.id`
- **RLS:** Disabled

---

### `word_quiz_results`

Individual word quiz results within a test attempt.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | bigint | NO | GENERATED ALWAYS AS IDENTITY | PK |
| `user_id` | uuid | NO | | FK -> users |
| `attempt_id` | uuid | YES | | FK -> test_attempts |
| `sense_id` | integer | NO | | FK -> dim_word_senses |
| `is_correct` | boolean | NO | | |
| `selected_answer` | text | YES | | |
| `correct_answer` | text | YES | | |
| `response_time_ms` | integer | YES | | |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `word_quiz_results_pkey (id)`
- **Indexes:** `idx_wqr_attempt (attempt_id)`, `idx_wqr_user (user_id)`
- **Foreign Keys:** `user_id` -> `users.id`, `attempt_id` -> `test_attempts.id`, `sense_id` -> `dim_word_senses.id`
- **RLS:** Disabled

---

### `vocabulary_review_queue`

Admin review queue for vocabulary items flagged during generation or validation.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | bigint | NO | GENERATED ALWAYS AS IDENTITY | PK |
| `vocab_id` | integer | NO | | FK -> dim_vocabulary |
| `sense_id` | integer | YES | | FK -> dim_word_senses |
| `issue_type` | text | NO | | CHECK: validation_failed/duplicate_suspected/definition_unclear/offensive_content/llm_error |
| `proposed_definition` | text | YES | | |
| `failure_reason` | text | YES | | |
| `context_sentence` | text | YES | | |
| `status` | text | YES | 'pending' | CHECK: pending/reviewing/resolved/dismissed |
| `reviewed_by` | uuid | YES | | FK -> users |
| `resolution_notes` | text | YES | | |
| `resolved_at` | timestamptz | YES | | |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `vocabulary_review_queue_pkey (id)`
- **Indexes:** `idx_review_status (status WHERE status='pending')`
- **Foreign Keys:** `vocab_id` -> `dim_vocabulary.id`, `sense_id` -> `dim_word_senses.id`, `reviewed_by` -> `users.id`
- **RLS:** Enabled

---

## 6. Corpus, Collocation & Style System

Tables for corpus-based collocation extraction, writing-style profiling, and study packs.

---

### `corpus_sources`

Source texts for collocation extraction.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | bigint | NO | nextval() | PK |
| `source_type` | text | NO | | CHECK: url/text/author |
| `source_url` | text | YES | | |
| `source_title` | text | NO | | |
| `language_id` | integer | NO | | FK -> dim_languages |
| `tags` | text[] | YES | '{}' | |
| `raw_text` | text | YES | | |
| `raw_text_path` | text | YES | | Storage path for large texts |
| `word_count` | integer | YES | 0 | |
| `processed_at` | timestamptz | YES | | |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `corpus_sources_pkey (id)`
- **Indexes:** `idx_corpus_sources_unprocessed (processed_at WHERE processed_at IS NULL)`
- **Foreign Keys:** `language_id` -> `dim_languages.id`
- **RLS:** Disabled
- **Referenced by:** corpus_collocations

---

### `corpus_collocations`

Extracted collocations with statistical association measures.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | bigint | NO | nextval() | PK |
| `corpus_source_id` | bigint | NO | | FK -> corpus_sources |
| `language_id` | integer | NO | | FK -> dim_languages |
| `collocation_text` | text | NO | | |
| `head_word` | text | YES | | |
| `collocate` | text | YES | | |
| `n_gram_size` | integer | NO | | |
| `frequency` | integer | NO | 0 | |
| `pmi_score` | double precision | YES | 0.0 | Pointwise Mutual Information |
| `lmi_score` | double precision | YES | 0 | Local MI |
| `log_likelihood` | double precision | YES | 0.0 | |
| `t_score` | double precision | YES | 0.0 | |
| `substitution_entropy` | double precision | YES | | |
| `collocation_type` | text | YES | 'collocation' | CHECK: collocation/fixed_phrase/discourse_marker |
| `pos_pattern` | text | YES | '' | |
| `extraction_method` | varchar | YES | 'ngram' | |
| `dependency_relation` | varchar | YES | NULL | |
| `tags` | text[] | YES | '{}' | |
| `is_validated` | boolean | YES | | |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `corpus_collocations_pkey (id)`
- **Indexes:** `idx_cc_extraction_method (corpus_source_id, extraction_method)`, `idx_cc_unverified (language_id, lmi_score DESC WHERE substitution_entropy IS NULL)`, `idx_cc_validated_lmi (language_id, is_validated, lmi_score DESC WHERE is_validated=true)`, `idx_corpus_collocations_head_word (head_word, pmi_score DESC)`, `idx_corpus_collocations_lang_pmi (language_id, pmi_score DESC)`, `idx_corpus_collocations_source_pmi (corpus_source_id, pmi_score DESC)`, `idx_corpus_collocations_text_lang (language_id, collocation_text)`, `idx_corpus_collocations_type (language_id, collocation_type)`, `idx_corpus_collocations_validated_lmi (language_id, is_validated, lmi_score DESC WHERE is_validated=true)`
- **Foreign Keys:** `corpus_source_id` -> `corpus_sources.id`, `language_id` -> `dim_languages.id`
- **RLS:** Disabled
- **Referenced by:** pack_collocations

---

### `collocation_packs`

Themed packs of collocations for study.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | bigint | NO | nextval() | PK |
| `pack_name` | text | NO | | |
| `description` | text | YES | '' | |
| `language_id` | integer | NO | | FK -> dim_languages |
| `tags` | text[] | YES | '{}' | |
| `source_type` | text | YES | 'corpus' | |
| `pack_type` | text | YES | 'topic' | CHECK: author/genre/topic/style |
| `total_items` | integer | YES | 0 | |
| `difficulty_range` | text | YES | | |
| `is_public` | boolean | YES | true | |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `collocation_packs_pkey (id)`
- **Foreign Keys:** `language_id` -> `dim_languages.id`
- **RLS:** Disabled
- **Referenced by:** pack_collocations, user_pack_selections, pack_style_items

---

### `pack_collocations`

Junction table: collocation pack <-> collocation.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | bigint | NO | nextval() | PK |
| `pack_id` | bigint | NO | | FK -> collocation_packs |
| `collocation_id` | bigint | NO | | FK -> corpus_collocations |

- **Primary Key:** `pack_collocations_pkey (id)`
- **Unique:** `pack_collocations_pack_id_collocation_id_key (pack_id, collocation_id)`
- **Indexes:** `idx_pack_collocations_collocation (collocation_id)`, `idx_pack_collocations_pack (pack_id)`
- **Foreign Keys:** `pack_id` -> `collocation_packs.id`, `collocation_id` -> `corpus_collocations.id`
- **RLS:** Disabled

---

### `user_pack_selections`

Tracks which collocation packs a user has selected. Rebuilt in Phase 2: user_id fixed from text to uuid, composite PK, proper FKs, RLS enabled.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `user_id` | uuid | NO | | FK -> users ON DELETE CASCADE |
| `pack_id` | bigint | NO | | FK -> collocation_packs ON DELETE CASCADE |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `(user_id, pack_id)` (composite)
- **Foreign Keys:** `user_id` -> `users.id` ON DELETE CASCADE, `pack_id` -> `collocation_packs.id` ON DELETE CASCADE
- **RLS:** Enabled (Phase 2). Policies: users manage own selections, service_role full access.

---

### `corpus_style_profiles`

Writing-style profile for a corpus source. One row per source, containing extracted linguistic features (n-grams, sentence patterns, syntactic preferences, discourse markers) as JSONB.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | bigint | NO | nextval() | PK |
| `corpus_source_id` | bigint | NO | | FK -> corpus_sources ON DELETE CASCADE. UNIQUE |
| `language_id` | integer | NO | | FK -> dim_languages |
| `raw_frequency_ngrams` | jsonb | YES | '{}' | Raw frequency n-gram data |
| `characteristic_ngrams` | jsonb | YES | '{}' | Statistically characteristic n-grams |
| `sentence_structures` | jsonb | YES | '{}' | POS-template sentence patterns |
| `syntactic_preferences` | jsonb | YES | '{}' | e.g. passive_ratio, subordinate clause frequency |
| `discourse_patterns` | jsonb | YES | '{}' | Discourse markers and transitions |
| `vocabulary_profile` | jsonb | YES | '{}' | Vocabulary richness, register indicators |
| `total_tokens` | integer | YES | 0 | |
| `total_sentences` | integer | YES | 0 | |
| `reference_source_id` | bigint | YES | | FK -> corpus_sources. Comparison baseline source |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `corpus_style_profiles_pkey (id)`
- **Unique:** `corpus_style_profiles_corpus_source_id_key (corpus_source_id)`
- **Indexes:** `idx_style_profiles_language (language_id)`
- **Foreign Keys:** `corpus_source_id` -> `corpus_sources.id` ON DELETE CASCADE, `language_id` -> `dim_languages.id`, `reference_source_id` -> `corpus_sources.id`
- **RLS:** Disabled

---

### `style_pack_items`

Individual learnable items extracted from a style profile. Each row represents one characteristic feature (n-gram, sentence pattern, syntactic feature, discourse marker) that can be turned into exercises.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | bigint | NO | nextval() | PK |
| `corpus_source_id` | bigint | NO | | FK -> corpus_sources ON DELETE CASCADE |
| `language_id` | integer | NO | | FK -> dim_languages |
| `item_type` | text | NO | | CHECK: frequent_ngram/characteristic_ngram/sentence_pattern/syntactic_feature/discourse_pattern/vocabulary_item |
| `item_text` | text | NO | | The characteristic text (n-gram, POS template, feature label, marker) |
| `item_data` | jsonb | YES | '{}' | Type-specific metadata (example sentences, frequency, keyness) |
| `frequency` | integer | YES | 0 | Raw occurrence count in source |
| `keyness_score` | float | YES | 0.0 | Statistical distinctiveness vs reference corpus |
| `sort_order` | integer | YES | 0 | Display ordering within a pack |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `style_pack_items_pkey (id)`
- **Indexes:** `idx_style_pack_items_source_type (corpus_source_id, item_type)`
- **Foreign Keys:** `corpus_source_id` -> `corpus_sources.id` ON DELETE CASCADE, `language_id` -> `dim_languages.id`
- **RLS:** Disabled
- **Referenced by:** pack_style_items, exercises

---

### `pack_style_items`

Junction table: collocation pack <-> style item. Links style items into packs (pack_type='style').

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | bigint | NO | nextval() | PK |
| `pack_id` | bigint | NO | | FK -> collocation_packs ON DELETE CASCADE |
| `style_item_id` | bigint | NO | | FK -> style_pack_items ON DELETE CASCADE |

- **Primary Key:** `pack_style_items_pkey (id)`
- **Unique:** `pack_style_items_pack_id_style_item_id_key (pack_id, style_item_id)`
- **Foreign Keys:** `pack_id` -> `collocation_packs.id` ON DELETE CASCADE, `style_item_id` -> `style_pack_items.id` ON DELETE CASCADE
- **RLS:** Disabled

---

## 7. Mystery System

Multi-scene narrative mysteries with comprehension questions and ELO matching.

---

### `mysteries`

Master mystery records (multi-scene listening/reading puzzles).

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `slug` | text | NO | | UNIQUE |
| `language_id` | integer | NO | | FK -> dim_languages |
| `difficulty` | integer | NO | | CHECK: 1-9 |
| `title` | text | NO | | |
| `premise` | text | NO | | |
| `suspects` | jsonb | NO | '[]' | |
| `solution_suspect` | text | NO | | |
| `solution_reasoning` | text | NO | | |
| `archetype` | text | YES | | |
| `target_vocab_ids` | integer[] | YES | '{}' | |
| `vocab_sense_ids` | integer[] | YES | '{}' | |
| `generation_model` | text | YES | 'gpt-4' | |
| `gen_user` | uuid | NO | | FK -> users |
| `is_active` | boolean | YES | true | |
| `total_attempts` | integer | YES | 0 | |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `mysteries_pkey (id)`
- **Unique:** `mysteries_slug_key (slug)`
- **Indexes:** `idx_mysteries_active (is_active WHERE is_active=true)`, `idx_mysteries_difficulty (difficulty)`, `idx_mysteries_language (language_id)`
- **Foreign Keys:** `language_id` -> `dim_languages.id`, `gen_user` -> `users.id`
- **RLS:** Enabled
- **Referenced by:** mystery_scenes, mystery_attempts, mystery_progress, mystery_skill_ratings

---

### `mystery_scenes`

Individual scenes within a mystery (1-5 per mystery).

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `mystery_id` | uuid | NO | | FK -> mysteries |
| `scene_number` | integer | NO | | CHECK: 1-5 |
| `title` | text | NO | | |
| `transcript` | text | NO | | |
| `audio_url` | text | YES | | |
| `clue_text` | text | NO | | |
| `clue_type` | text | YES | 'evidence' | |
| `is_finale` | boolean | YES | false | |
| `target_words` | jsonb | YES | | |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `mystery_scenes_pkey (id)`
- **Unique:** `mystery_scenes_mystery_id_scene_number_key (mystery_id, scene_number)`
- **Indexes:** `idx_mystery_scenes_mystery (mystery_id)`
- **Foreign Keys:** `mystery_id` -> `mysteries.id`
- **RLS:** Enabled
- **Referenced by:** mystery_questions

---

### `mystery_questions`

Questions attached to mystery scenes.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `scene_id` | uuid | NO | | FK -> mystery_scenes |
| `question_text` | text | NO | | |
| `choices` | jsonb | NO | | |
| `answer` | jsonb | NO | | |
| `answer_explanation` | text | YES | | |
| `question_type_id` | integer | YES | | FK -> dim_question_types |
| `sense_ids` | integer[] | YES | | |
| `is_deduction` | boolean | YES | false | Whether this is a deduction question |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `mystery_questions_pkey (id)`
- **Indexes:** `idx_mystery_questions_scene (scene_id)`
- **Foreign Keys:** `scene_id` -> `mystery_scenes.id`, `question_type_id` -> `dim_question_types.id`
- **RLS:** Enabled

---

### `mystery_progress`

User progress through a mystery (save state).

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `user_id` | uuid | NO | | FK -> users |
| `mystery_id` | uuid | NO | | FK -> mysteries |
| `current_scene` | integer | NO | 1 | |
| `scene_responses` | jsonb | YES | '{}' | |
| `notebook_state` | jsonb | YES | '{"clues":[],"suspects":[]}' | |
| `mode` | text | NO | 'reading' | CHECK: reading/listening |
| `started_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |
| `completed_at` | timestamptz | YES | | |

- **Primary Key:** `mystery_progress_pkey (id)`
- **Unique:** `mystery_progress_user_id_mystery_id_key (user_id, mystery_id)`
- **Indexes:** `idx_mystery_progress_user (user_id)`
- **Foreign Keys:** `user_id` -> `users.id`, `mystery_id` -> `mysteries.id`
- **RLS:** Enabled

---

### `mystery_skill_ratings`

Per-mystery ELO ratings (analogous to test_skill_ratings).

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `mystery_id` | uuid | NO | | UNIQUE. FK -> mysteries |
| `elo_rating` | integer | YES | 1400 | CHECK: 400-3000 |
| `volatility` | numeric | YES | 1.0 | |
| `total_attempts` | integer | YES | 0 | |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `mystery_skill_ratings_pkey (id)`
- **Unique:** `mystery_skill_ratings_mystery_id_key (mystery_id)`
- **Foreign Keys:** `mystery_id` -> `mysteries.id`
- **RLS:** Enabled

---

### `mystery_attempts`

Records each user mystery completion with ELO snapshots.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `user_id` | uuid | NO | | FK -> users |
| `mystery_id` | uuid | NO | | FK -> mysteries |
| `language_id` | integer | NO | | FK -> dim_languages |
| `test_type_id` | integer | NO | | FK -> dim_test_types |
| `score` | integer | NO | | CHECK >= 0 |
| `total_questions` | integer | NO | | CHECK > 0 |
| `percentage` | real | YES | GENERATED (score/total_questions * 100) | |
| `user_elo_before` | integer | NO | | |
| `user_elo_after` | integer | NO | | |
| `mystery_elo_before` | integer | NO | | |
| `mystery_elo_after` | integer | NO | | |
| `attempt_number` | integer | YES | 1 | |
| `is_first_attempt` | boolean | YES | true | |
| `idempotency_key` | uuid | YES | | |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `mystery_attempts_pkey (id)`
- **Indexes:** `idx_mystery_attempts_mystery (mystery_id)`, `idx_mystery_attempts_user (user_id)`
- **Foreign Keys:** `user_id` -> `users.id`, `mystery_id` -> `mysteries.id`, `language_id` -> `dim_languages.id`, `test_type_id` -> `dim_test_types.id`
- **RLS:** Enabled

---

## 8. Organization System

Multi-tenant organization support for schools/businesses.

---

### `organizations`

Organization records with subscription tiers and token pools.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `name` | text | NO | | |
| `slug` | text | NO | | UNIQUE |
| `subscription_tier_id` | smallint | NO | | FK -> dim_subscription_tiers |
| `max_users` | integer | YES | | |
| `token_pool` | integer | YES | 0 | CHECK >= 0 |
| `is_active` | boolean | YES | true | |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `organizations_pkey (id)`
- **Unique:** `organizations_slug_key (slug)`
- **Indexes:** `idx_organizations_active (is_active WHERE is_active=true)`, `idx_organizations_slug (slug)`
- **Foreign Keys:** `subscription_tier_id` -> `dim_subscription_tiers.id`
- **RLS:** Enabled
- **Referenced by:** users, tests, organization_members

---

### `organization_members`

Junction table: organization <-> user with role.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `organization_id` | uuid | NO | | FK -> organizations |
| `user_id` | uuid | NO | | FK -> users |
| `role` | text | NO | 'student' | CHECK: student/teacher/admin/owner |
| `joined_at` | timestamptz | YES | now() | |

- **Primary Key:** `organization_members_pkey (organization_id, user_id)`
- **Indexes:** `idx_org_members_org (organization_id)`, `idx_org_members_user (user_id)`
- **Foreign Keys:** `organization_id` -> `organizations.id`, `user_id` -> `users.id`
- **RLS:** Enabled

---

## 9. Token Economy

In-app currency for test access and premium features.

---

### `user_tokens`

Token balance ledger per user.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `user_id` | uuid | NO | | PK. FK -> users |
| `purchased_tokens` | integer | YES | 0 | CHECK >= 0 |
| `bonus_tokens` | integer | YES | 0 | CHECK >= 0 |
| `total_tokens_earned` | integer | YES | 0 | |
| `total_tokens_spent` | integer | YES | 0 | |
| `total_tokens_purchased` | integer | YES | 0 | |
| `tokens_spent_tests` | integer | YES | 0 | |
| `tokens_spent_generation` | integer | YES | 0 | |
| `tokens_spent_premium_features` | integer | YES | 0 | |
| `referral_tokens_earned` | integer | YES | 0 | |
| `achievement_tokens_earned` | integer | YES | 0 | |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `user_tokens_pkey (user_id)`
- **Foreign Keys:** `user_id` -> `users.id`
- **RLS:** Enabled

---

### `token_transactions`

Immutable audit log of every token credit/debit.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `user_id` | uuid | NO | | FK -> users |
| `tokens_consumed` | integer | YES | 0 | CHECK >= 0 |
| `tokens_added` | integer | YES | 0 | CHECK >= 0 |
| `token_balance_after` | integer | NO | | CHECK >= 0 |
| `action` | text | NO | | |
| `payment_intent_id` | text | YES | | Stripe reference |
| `package_id` | text | YES | | |
| `test_id` | uuid | YES | | FK -> tests |
| `attempt_id` | uuid | YES | | FK -> test_attempts |
| `is_valid` | boolean | YES | true | |
| `invalidated_at` | timestamptz | YES | | |
| `invalidation_reason` | text | YES | | |
| `created_by_system` | boolean | YES | true | |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `token_transactions_pkey (id)`
- **Indexes:** `idx_token_transactions_created_at (created_at DESC)`, `idx_token_transactions_user_id (user_id)`
- **Foreign Keys:** `user_id` -> `users.id`, `test_id` -> `tests.id`, `attempt_id` -> `test_attempts.id`
- **RLS:** Enabled

---

## 10. Analytics, Logging & Reporting

---

### `app_error_logs`

Client-side error capture for debugging.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | bigint | NO | nextval() | PK |
| `error_type` | text | NO | | |
| `error_message` | text | NO | | |
| `url` | text | YES | | |
| `user_id` | uuid | YES | | FK -> users ON DELETE SET NULL (Phase 2) |
| `metadata` | jsonb | YES | | |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `app_error_logs_pkey (id)`
- **Indexes:** `idx_app_error_logs_created (created_at)`, `idx_app_error_logs_type (error_type)`
- **Foreign Keys:** `user_id` -> `users.id` ON DELETE SET NULL (Phase 2)
- **RLS:** Enabled (Phase 6). Policies: authenticated insert, admin+service read, service_role full access.

---

### `user_reports`

User-submitted bug reports and feedback.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `user_id` | uuid | NO | | FK -> public.users (fixed in Phase 2, was auth.users) |
| `report_category` | varchar | NO | | CHECK: test_answer_incorrect/test_load_error/website_crash/improvement_idea/audio_quality/other |
| `description` | text | NO | | |
| `current_page` | varchar | YES | | |
| `test_id` | uuid | YES | | FK -> tests |
| `test_type` | varchar | YES | | |
| `user_agent` | text | YES | | |
| `screen_resolution` | varchar | YES | | |
| `status` | varchar | YES | 'pending' | CHECK: pending/reviewing/resolved/dismissed |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

- **Primary Key:** `user_reports_pkey (id)`
- **Indexes:** `idx_user_reports_created_at (created_at DESC)`, `idx_user_reports_status (status)`, `idx_user_reports_test_id (test_id WHERE NOT NULL)`, `idx_user_reports_user_id (user_id)`
- **Foreign Keys:** `user_id` -> `auth.users.id`, `test_id` -> `tests.id`
- **Triggers:** BEFORE UPDATE -> `update_updated_at_column()`
- **RLS:** Enabled

---

### `flagged_content`

AI-generated content flagged by safety checks.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `user_id` | uuid | YES | | FK -> users |
| `content_hash` | text | NO | | |
| `content_type` | text | NO | | |
| `flagged_categories` | jsonb | YES | | |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `flagged_content_pkey (id)`
- **Foreign Keys:** `user_id` -> `users.id`
- **RLS:** Enabled

---

## Enum Types

### `exercise_source_type`

```sql
CREATE TYPE exercise_source_type AS ENUM (
  'grammar',
  'vocabulary',
  'collocation',
  'conversation',
  'style'
);
```

Used by `exercises.source_type` to categorize the origin of each exercise.

---

## Views

### `corpus_statistics`

Aggregates collocations by language, collocation type, and n-gram size. Used for admin dashboards and corpus health monitoring.

### `vw_distractor_error_analysis`

Analyzes incorrect exercise attempts with distractor tags. Joins `exercise_attempts` with `exercises` to surface which distractor patterns cause the most errors, broken down by grammar pattern and distractor tag.

### `vw_exercise_performance_by_type`

Exercise accuracy percentages grouped by exercise type, complexity tier, and language. Used for exercise difficulty calibration and content quality monitoring.

---

## Triggers

| Table | Event | Trigger Name | Function | Description |
|-------|-------|-------------|----------|-------------|
| `dim_vocabulary` | BEFORE UPDATE | -- | `update_updated_at_column()` | Auto-set updated_at |
| `dim_word_senses` | BEFORE UPDATE | -- | `update_updated_at_column()` | Auto-set updated_at |
| `tests` | BEFORE UPDATE | -- | `update_updated_at_column()` | Auto-set updated_at |
| `user_languages` | BEFORE UPDATE | -- | `update_updated_at_column()` | Auto-set updated_at |
| `user_reports` | BEFORE UPDATE | -- | `update_updated_at_column()` | Auto-set updated_at |
| `user_skill_ratings` | BEFORE UPDATE | -- | `update_updated_at_column()` | Auto-set updated_at |
| `users` | BEFORE UPDATE | -- | `update_updated_at_column()` | Auto-set updated_at |
| `users` | AFTER INSERT | -- | `create_user_dependencies()` | Auto-create user_tokens, user_languages, etc. |
| `test_attempts` | AFTER INSERT | -- | `update_test_attempts_count()` | O(1) increment tests.total_attempts (Phase 3: was COUNT(*)) |
| `test_attempts` | AFTER INSERT | -- | `update_skill_attempts_count()` | O(1) increment test_skill_ratings.total_attempts (Phase 3: was COUNT(*)) |
| `exercise_attempts` | AFTER INSERT | `trigger_sync_exercise_history` | `sync_exercise_history()` | Copy to user_exercise_history for anti-repetition (Phase 4) |

**Note:** Duplicate trigger `update_skill_attempts_count_trigger` on test_attempts was removed in Phase 1.

---

## Key Database Functions (52 total)

### ELO & Scoring
- `calculate_elo_rating(current, opposing, actual_score, k_factor, volatility_multiplier)` -> integer
- `calculate_volatility_multiplier(attempts, last_date, base_volatility)` -> numeric
- `process_test_submission(user_id, test_id, language_id, test_type_id, responses, was_free, idempotency_key)` -> jsonb -- atomic test grading + ELO update with volatility (Phase 3)

### BKT (Bayesian Knowledge Tracing)
- `bkt_update(p_current, p_correct, p_slip, p_guess)` -> numeric
- `bkt_update_comprehension(p_current, p_correct)` -> numeric (slip=0.10, guess=0.25)
- `bkt_update_word_test(p_current, p_correct)` -> numeric (slip=0.05, guess=0.25)
- `bkt_update_exercise(p_current, p_correct, p_exercise_type)` -> numeric -- exercise-type-specific BKT (Phase 5)
- `bkt_status(p_known)` -> text -- maps probability to status label
- `bkt_apply_decay(p_known, last_evidence_at, half_life_days)` -> numeric -- temporal decay (Phase 5)
- `bkt_effective_p_known(p_known, last_evidence_at)` -> numeric -- convenience wrapper for decay (Phase 5)
- `bkt_phase(p_known)` -> text -- canonical phase thresholds A/B/C/D (Phase 5)
- `bkt_phase_thresholds()` -> table -- phase threshold table for Python sync (Phase 5)

### Vocabulary
- `batch_lookup_lemmas(lemmas[], language_id)` -> table
- `get_distractors(sense_id, language_id, count)` -> table -- now SECURITY DEFINER with auth check (Phase 3)
- `get_word_quiz_candidates(user_id, sense_ids[], language_id, max_words)` -> table -- now SECURITY DEFINER (Phase 6)
- `get_vocab_recommendations(user_id, language_id, ...)` -> table -- return type updated, now SECURITY DEFINER (Phase 6)
- `update_vocabulary_from_word_test(user_id, sense_id, is_correct, language_id, exercise_type)` -> table -- optional exercise_type routes to bkt_update_exercise (Phase 5)

### Test Serving
- `get_recommended_test(user_id, language_id)` -> tests row -- expanding-radius ELO match, now excludes attempted tests (Phase 3)
- `get_recommended_tests(user_id, language)` -> table -- ranked candidate tests

### Exercise Serving (Vocab Dojo)
- `get_exercise_session(p_user_id, p_language_id, p_session_size)` -> table -- CTE-based session builder with 40/40/20 split (FSRS due / BKT uncertainty / new words)

### Auth & Tokens
- `is_admin(user_id)`, `is_moderator(user_id)` -> boolean
- `handle_new_user()` -> trigger
- `get_token_balance(user_id)` -> integer -- now properly reads user_tokens (Phase 3, was stub returning 0)
- `get_test_token_cost(user_id)` -> integer
- `add_tokens_atomic(...)`, `process_stripe_payment(...)` -> boolean
- `can_use_free_test(user_id)` -> boolean -- now properly checks daily usage (Phase 3, was stub)

### Content
- `get_prompt_template(task_name, language_id)` -> text -- now uses language_id integer (Phase 1, was language_code text)
- `get_next_category()` -> table -- cooldown-aware category rotation, now SECURITY DEFINER (Phase 6)
- `match_topics(category_id, embedding, threshold, count)` -> table -- cosine similarity dedup, now SECURITY DEFINER (Phase 6)
- `get_packs_with_user_selection(language_id, user_id)` -> table -- p_user_id now uuid (Phase 2, was text)
- `get_active_languages()` -> table -- now SECURITY DEFINER (Phase 6)
- `get_model_for_task(task_key, language_id)` -> text -- lookup model from language_model_config (Phase 4)

### User Management
- `anonymize_user_data(user_id)` -> void -- GDPR deletion

### Triggers
- `sync_exercise_history()` -> trigger -- copy exercise_attempts to user_exercise_history (Phase 4)

---

## RLS Summary

| RLS Enabled | Tables |
|-------------|--------|
| **Enabled** | app_error_logs, dim_complexity_tiers, dim_grammar_patterns, dim_languages, dim_lens, dim_question_types, dim_status, dim_subscription_tiers, dim_test_types, dim_vocabulary, dim_word_senses, flagged_content, mysteries, mystery_attempts, mystery_progress, mystery_questions, mystery_scenes, mystery_skill_ratings, organization_members, organizations, questions, test_attempts, test_skill_ratings, tests, token_transactions, user_exercise_history, user_exercise_sessions, user_languages, user_pack_selections, user_reports, user_skill_ratings, user_tokens, users, vocabulary_review_queue |
| **Disabled** | categories, collocation_packs, conversation_domains, conversation_generation_queue, conversations, corpus_collocations, corpus_sources, daily_test_load_items, daily_test_loads, exercise_attempts, exercises, language_model_config, pack_collocations, persona_pairs, personas, production_queue, prompt_templates, question_type_distributions, scenarios, test_generation_config, test_generation_runs, topic_generation_runs, topics, user_flashcards, user_vocabulary_knowledge, user_word_ladder, word_assets, word_quiz_results |

**Note:** `users` table now has RLS enabled (Phase 6) with self-read, self-update, admin-read, and service_role policies. `user_reports` FK corrected to reference `public.users.id` (Phase 2, was `auth.users.id`).

---

## Related Pages

- [[database/schema]] -- Plain English overview
- [[algorithms/elo-ranking]] -- ELO calculation details
- [[algorithms/vocabulary-ladder]] -- 9-level vocabulary ladder
- [[features/vocabulary-knowledge]] -- BKT model details
- [[features/vocab-dojo.tech]] -- Exercise serving algorithm
- [[api/rpcs.tech]] -- Full RPC specifications
