---
title: Database Schema — Technical Specification
type: schema-tech
status: complete
prose_page: ../database/schema.md
last_updated: 2026-11-23
dependencies:
  - "Supabase PostgreSQL"
  - "pgvector extension"
  - "pgcrypto extension"
  - "intarray extension"
open_questions:
  - "calibration_zh_char_readings and calibration_zh_tone_inventory are filled by calibration_refresh_zh_tone_inventory(); how and how often the refresh is run in production is not recorded in the repo (migrations/calibration_zh_tones.sql defines them)."
  - "tests_tier_backup_20260926 and tests_tier_backup_20260927_v1 are one-off snapshots with no reader; decide whether to drop them."
  - "grant_daily_free_tokens is called by the application but does not exist live or in any migration (see rpcs.tech); the users table also lacks the tokens and last_free_token_date columns that routes/users.py selects."
  - "Writers and readers per table come from a grep of routes/, services/, scripts/ and from function bodies; a table touched only through a dynamically built name may be missing a writer."
breaking_change_risk: medium
---

# Database Schema — Technical Specification

> **Study Plans + Practice Engine merger (specified 2026-05-21): applied live, verified 2026-11-23.** Full design in [[features/study-plans.tech#schema]] and [[features/practice-engine.tech]]; ADRs [[decisions/ADR-007-merge-exercises-vocab-dojo]] / [[decisions/ADR-008-study-plan-orchestration-layer]]. Live tables: `dim_exercise_types`, `dim_practice_modes`, `dim_study_plan_templates`, `user_study_plans`, `weekly_plan_states` (sections below). `dim_study_goals` was dropped by the 2026-09-22 archive migration (see the archive table). Live additions on existing tables: `test_attempts.started_at` and `duration_ms`, `daily_test_loads.daily_session_targets` and `completed_blocks`, `user_exercise_sessions.mode` and `target_minutes`, `dim_test_types.expected_minutes_p50`, `dim_languages.new_word_minutes_est`. Corrections to the 2026-05 and 2026-10-13 plans as built: `user_study_plans.new_words_per_day` defaults to 10 (not 5); `excluded_modules`, `budget_scope`, `prestudy_mode` are live; `weekly_plan_states` also carries `skill_values`, `budget_scope`, `review_target_minutes`, `new_words_target`, `new_words_completed`, `acq_target_minutes`, `tail_completed_min`, `tail_new_words_completed`. `calibration_sessions.bkt_applied_at` is live.

## Overview

The schema lives in Supabase PostgreSQL with Row-Level Security (RLS) policies on user-facing tables. It uses a tiered dependency structure (Tier 0 = no FKs, through Tier 5 = deepest dependencies). All tables are in the `public` schema unless otherwise noted. Authentication delegates to Supabase `auth.users` with a mirror `users` table in public.

**Total relations (live, 2026-11-23):** 108 in schema `public`: 100 tables and 8 views (the 2026-05-12 count of 64 is superseded; 28 tables were dropped on 2026-09-22 and about 60 were added since, all listed below). `language_model_config` was dropped by the 2026-05-05 model-routing refactor ([migrations/drop_dim_languages_model_columns.sql](../../migrations/drop_dim_languages_model_columns.sql)).
**Enum types:** 1 (`exercise_source_type`, values `grammar, vocabulary, collocation, conversation, style`; only `vocabulary` and `collocation` rows remain meaningful after the archive)
**Views:** 8, all `security_invoker = true` (see Views)
**Triggers:** 23 across 17 tables (see Triggers)
**RLS coverage:** all 100 tables have RLS enabled; 42 carry at least one policy, the rest are RLS-on with no policy (service role only). No table grants INSERT, UPDATE or DELETE to `anon` or `authenticated`.
**Application functions:** 214 (85 SECURITY DEFINER), plus extension functions; see [[database/rpcs.tech]]. Extensions installed: `plpgsql`, `pg_stat_statements`, `uuid-ossp`, `pgcrypto`, `intarray`, `supabase_vault`, `vector` 0.8.0, `pg_trgm`, `fuzzystrmatch`.
**Storage buckets (private):** `exercise-content`, `reference-data`, `llm-logs-archive`. Sequence `exercise_content_version_seq`.

### Security posture (hardening applied live; verified 2026-11-23)

The 2026-10-14 audit plan ([[decisions/ADR-034-no-client-db-writes]], [[features/security-hardening.tech]], [[tasklist/security-hardening.tasks]]) is in effect in the live database. Checked directly:

- **Table privileges:** `authenticated` holds SELECT only (never INSERT, UPDATE, DELETE) and only on its own-data tables, the dimension tables and a few logs; `anon` holds SELECT only on 28 relations (the dimension tables, `app_error_logs`, `calibration_anchor_blocklist`, `token_transactions`, `trusted_devices`, `user_exercise_history`, `user_test_intros_seen`, `user_tokens`, `users`, the two `tests_tier_backup_*` tables), and RLS filters what it sees. `service_role` holds full privileges everywhere.
- **RLS:** enabled on all 100 tables. `users` has the policies `rls_select`, `rls_insert`, `rls_update`, `rls_delete` (writes service_role only; SELECT own row, admin or service_role); `user_tokens` and `token_transactions` have `rls_select` only; `user_reports` has "Users can view own reports" and no client INSERT grant. The old broad policies (`users_update_own`, `users_admin_all`, `System can update tokens`, `tokens_own_data`, "Admin can view all reports") are gone.
- **Functions:** `anon` and `authenticated` can execute only `is_admin` and `is_moderator`; every other function is service-role only. SECURITY DEFINER functions all pin `search_path` (see [[database/rpcs.tech]]). New functions still receive EXECUTE for `anon`/`authenticated` through the default ACL of the creating role unless the migration revokes it.
- **Views:** all eight are `security_invoker = true`; only `service_role` can SELECT them.
- Open item: the three owner decisions and pending items for the database are listed in section 14 (Pending schema changes).

### Archive of 2026-09-21

28 tables across six groups were exported with their code and docs and were
dropped by [migrations/archive_unused_modules_2026_09_21.sql](../../migrations/archive_unused_modules_2026_09_21.sql)
(**applied 2026-09-22**; database 1,144 MB → 1,098 MB):

| Group | Tables | Archive (local, gitignored) |
|---|---|---|
| Unused (stage 1) | flagged_content, question_type_distributions, vocabulary_review_queue, dim_classifier_example_sentences, dim_study_goals, organizations, organization_members | `archive/db_backups/stage1-unused-tables-2026-09-21.zip` |
| Language packs | collocation_packs, pack_collocations, pack_key_words, pack_style_items, style_pack_items, user_pack_selections | `archive/modules/language-packs-2026-09-21.zip` |
| Listening Lab | listening_lab_passages, listening_lab_sessions | `archive/modules/listening-lab-2026-09-21.zip` |
| Grammar patterns | dim_grammar_patterns | `archive/modules/grammar-patterns-2026-09-21.zip` |
| Conversations | conversation_domains, personas, persona_pairs, scenarios, conversations, conversation_generation_queue (+ 7,352 exercises rows) | `archive/modules/conversations-2026-09-21.zip` |
| Mysteries | mysteries, mystery_scenes, mystery_questions, mystery_attempts, mystery_progress, mystery_skill_ratings | `archive/modules/mysteries-2026-09-21.zip` |

The same migration drops `exercises.{grammar_pattern_id, conversation_id, style_pack_item_id}`,
rebuilds `chk_source_fk`, drops the FKs (not the columns) `user_study_plans.goal_id` and
`tests/users.organization_id`, deletes the 45 conversation/mystery `prompt_templates` rows, and
truncates `llm_calls` after moving 43,605 rows to `archive/db_backups/llm-calls-log-2026-09-21.zip`.
**Kept:** the corpus tables (the vocabulary ladder reads `corpus_collocations`) and
`user_exercise_sessions` (daily practice-session cache, not attempt data).

## Extensions

- **pgvector** -- `vector(1536)` columns for topic embedding similarity search (IVFFlat index)
- **pgcrypto** -- `gen_random_uuid()` for UUID primary keys
- **intarray** -- `gin__int_ops` for integer array intersection (vocab sense overlap)
- **pg_trgm**, **fuzzystrmatch**, **uuid-ossp**, **supabase_vault**, **pg_stat_statements** -- also installed (live 2026-11-23); `vector` is 0.8.0 and also stores `halfvec(512)` sense embeddings

---

## 1. Dimension / Lookup Tables

These tables have no outbound foreign keys (Tier 0). They define the reference data used across the system.

---

### `dim_languages`

Supported languages with TTS settings and grammar tooling. **As of the 2026-05-05 model-routing refactor, the per-task model columns (`prose_model`, `question_model`, `exercise_model`, `exercise_sentence_model`, `conversation_model`, `vocab_prompt1_model`, `vocab_prompt2_model`, `vocab_prompt3_model`) have been dropped** — model assignment per (task_name, language_id) now lives exclusively on [`prompt_templates.model`](#prompt_templates). The 2026-05-12 Chinese TTS migration seeded `tts_voice_ids` with Azure neural voices for the active languages and fixed a long-standing config rot where the English row contained the OpenAI voice catalogue (which the Azure runtime silently ignored).

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
| `tts_voice_ids` | jsonb | YES | (per-language, see below) | Array of Azure neural voice IDs. Seeded 2026-05-12: Chinese row gets `[zh-CN-XiaoxiaoMultilingualNeural, zh-CN-YunxiNeural, zh-CN-YunyangNeural]`; English row gets `[en-US-AvaMultilingualNeural, en-US-AndrewMultilingualNeural, en-US-BrianMultilingualNeural, en-US-EmmaMultilingualNeural]` |
| `tts_speed` | numeric | YES | 1.0 | CHECK: 0.25-4.0. TTS playback speed multiplier |
| `grammar_check_enabled` | boolean | YES | true | Enable LanguageTool grammar validation |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |
| `new_word_minutes_est` | numeric(4,2) | YES |  | CHECK null or 0.5..15.0; nightly estimate of minutes to introduce one new word (`refresh_new_word_minutes`) |

- **Primary Key:** `dim_languages_pkey (id)`
- **Unique:** `dim_languages_language_code_key (language_code)`
- **Indexes:** `idx_dim_languages_active (is_active)`, `idx_dim_languages_code (language_code)`
- **RLS:** Enabled
- **Referenced by:** tests, test_attempts, user_languages, user_skill_ratings, personas, production_queue, prompt_templates, scenarios, conversations, conversation_generation_queue, categories, dim_vocabulary, dim_word_senses, user_vocabulary_knowledge, user_flashcards, dim_grammar_patterns, exercises, corpus_sources, corpus_collocations, collocation_packs, corpus_style_profiles, style_pack_items, word_assets

---

### `dim_test_types`

Test/skill types (reading, listening, dictation, pinyin, pitch_accent).

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
| `expected_minutes_p50` | numeric(4,1) | YES |  | CHECK null or 0 < value < 120; observed p50 minutes (`refresh_practice_time_estimates`) |

- **Primary Key:** `dim_test_types_pkey (id)`
- **Unique:** `dim_test_types_type_code_key (type_code)`
- **Indexes:** `idx_dim_test_types_active (is_active)`, `idx_dim_test_types_code (type_code)`
- **RLS:** Enabled
- **Referenced by:** test_skill_ratings, user_skill_ratings, test_attempts

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
- **Referenced by:** questions (via id), question_type_distributions (via type_code)

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
| `part_of_speech` | text | YES | | One standard label (`services/vocabulary/pos.py` CANONICAL_POS): noun, verb, adjective, adverb, pronoun, preposition, conjunction, particle, measure_word, idiom, phrase, numeral, auxiliary, adnominal, determiner, interjection, other. Normalised on every INSERT/UPDATE by trigger `trg_dim_vocabulary_normalize_pos` (`migrations/standardise_part_of_speech.sql`, live 2026-11-22). Writers send the tagger's or model's tag unchanged. |
| `part_of_speech_raw` | text | YES | | The original tag (jieba / UniDic / spaCy / model label) when it differed from the standard label; set by the trigger and by the 2026-11-22 backfill (15,039 rows). Exercise-authoring prompts are hinted with it (`pos.pos_hint`). |
| `frequency_rank` | real | YES | | A wordfreq 3.1.1 **Zipf score** (0–8, higher = more common), not a rank. 770 NULL rows filled 2026-11-17 (TASK-994, `migrations/task994_vocab_frequency_fill.sql`); 76 stay NULL by design (zh 12, en 20, ja 44). |
| `level_tag` | text | YES | | |
| `semantic_class` | text | YES | | |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |
| `semantic_class_confidence` | real | YES |  | Confidence of `semantic_class` (`semantic_class_backfill.sql`) |
| `lemma_traditional` | text | YES |  | Traditional-script form of a Chinese lemma (`traditional_chinese_groundwork.sql`) |
| `reading` | text | YES |  | Reading of the headword (`add_vocab_reading_column.sql`) |

- **Primary Key:** `dim_vocabulary_pkey (id)`
- **Unique:** `uq_vocab_lemma (language_id, lemma)`
- **Indexes:** `idx_dv_level_tag (level_tag)`, `idx_vocab_components GIN (component_lemmas WHERE NOT NULL)`, `idx_vocab_language (language_id)`, `idx_vocab_lemma_lookup (language_id, lemma text_pattern_ops)`, `idx_vocab_phrase_type (phrase_type WHERE <>'single_word')`
- **Foreign Keys:** `language_id` -> `dim_languages.id`
- **Check:** `dim_vocabulary_part_of_speech_check` — `part_of_speech` is NULL or one of the 17 standard labels (validated 2026-11-22)
- **Triggers:** BEFORE UPDATE -> `update_updated_at_column()`; BEFORE INSERT OR UPDATE OF part_of_speech -> `trg_dim_vocabulary_normalize_pos()` (calls `normalize_pos(text)` → `pos_tag_lookup(text)`; both service_role only); AFTER UPDATE OF language_id -> `propagate_vocab_language_to_senses()`
- **RLS:** Enabled
- **Referenced by:** dim_word_senses, vocabulary_review_queue

---

### `dim_word_senses`

Individual word senses (definitions) linked to vocabulary lemmas. Each sense is
stored at **two definition levels** (`simple` + `standard`) sharing one
`sense_rank` — see [Two-level sense generation](#two-level-sense-generation) below.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | GENERATED ALWAYS AS IDENTITY | PK |
| `vocab_id` | integer | NO | | FK -> dim_vocabulary (ON DELETE CASCADE) |
| `word_language_id` | smallint | NO | | Language of the *word* (denormalised from `dim_vocabulary.language_id` by trigger `set_sense_word_language()`); differs from `definition_language_id` on cross-language gloss rows |
| `definition_language_id` | smallint | NO | | FK -> dim_languages. Language the definition is written in |
| `definition` | text | NO | | Definition for this level, in `definition_language_id` |
| `definition_level` | text | NO | 'standard' | CHECK: simple/standard. `simple` = child (T1/T2) register; `standard` = normal |
| `pronunciation` | text | YES | | Filled deterministically (pypinyin/fugashi), not by the LLM |
| `ipa_pronunciation` | text | YES | | ~150 rows populated |
| `example_sentence` | text | YES | | LLM-generated example (differs from the source sentence) |
| `sense_rank` | integer | NO | 1 | Ordering within vocab_id; shared by both levels of a sense |
| `morphological_forms` | jsonb | YES | | ~150 rows populated |
| `register` | text | YES | | ~150 rows populated (migrations/dim_word_senses_register.sql) |
| `is_validated` | boolean | YES | false | True when `gen_confidence` >= 0.7 and language check passes |
| `gen_confidence` | real | YES | | Self-rated 0..1 from single-call generation (replaces the old validation call) |
| `source` | text | NO | 'llm' | CHECK: llm/manual/llm_gloss. `manual` (admin-curated) is never overwritten by backfill; `llm_gloss` = cross-language gloss |
| `source_ref` | text | YES | | Provenance, e.g. `"deepseek/deepseek-v4-flash v2"` |
| `validation_notes` | text | YES | | |
| `embedding` | halfvec(512) | YES | | text-embedding-3-small of `"{lemma}: {definition}"` (TASK-521), truncated to 512 dims + L2-normalised (≡ API `dimensions=512`), stored fp16. **Only on the native standard row** of a sense (`definition_level='standard'` AND `definition_language_id = word_language_id`), enforced by CHECK `dim_word_senses_embedding_native_standard_chk`; every other row of the sense reads its twin's vector through `sense_embedding(id)` ([[decisions/ADR-038-one-sense-vector-native-standard-512]]). vector(1536) until 2026-09-22, halfvec(768) on every row until 2026-10-29. Writers must use `scripts/backfill_sense_embeddings.py::is_embedded_row` + `sense_vector` — see *Storage* below |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |

**Dropped 2026-09-21** (migrations/dim_word_senses_drop_dead_columns.sql): `usage_notes`,
`semantic_category`, `validated_by` (FK -> users) — NULL in every row — and `usage_frequency`
(only ever its `'common'` default; CHECK common/uncommon/rare/archaic). None had a reader or
writer in code, functions, views, policies or triggers. Do not reintroduce them; historical
DDL in `create_all_tables.sql` and `archive/` still shows them.

- **Primary Key:** `dim_word_senses_pkey (id)`
- **Check:** `dim_word_senses_embedding_native_standard_chk` — `embedding IS NULL OR (definition_level = 'standard' AND definition_language_id = word_language_id)` (2026-10-29)
- **Unique:** `uq_sense_def_level (vocab_id, definition_language_id, definition_level, sense_rank)` — replaced `uq_sense_definition` (migrations/add_sense_levels_and_source.sql, 2026-05-31)
- **Indexes (btree):** `idx_senses_rank (vocab_id, sense_rank)` — also serves plain `vocab_id` lookups and the FK cascade; `idx_senses_lang (definition_language_id)`; `idx_senses_source (source)`; `idx_dim_word_senses_wl_dl_level (word_language_id, definition_language_id, definition_level)`; `idx_dim_word_senses_pronunciation_lookup (word_language_id, definition_level) WHERE pronunciation IS NOT NULL`. `idx_senses_vocab (vocab_id)` was dropped 2026-09-21 as redundant (0.55 vs 0.56 ms on a 150-id lookup).
- **Indexes (HNSW):** none since 2026-09-22 — the seven partial `idx_dws_emb_w{W}_d{D}` indexes (~456 MB) were dropped. Since 2026-10-29 `semantic_distractors()` scans the word language's native standard rows exactly (en 6.6k, zh 4.3k, ja 3.4k vectors) and joins each neighbour to the requested definition language/level row via `uq_sense_def_level`.
- **Helper:** `sense_embedding(p_sense_id integer) RETURNS halfvec` — the twin's vector for any row (SQL, STABLE, service_role only).
- **Foreign Keys:** `vocab_id` -> `dim_vocabulary.id` (CASCADE), `definition_language_id` -> `dim_languages.id`
- **Triggers:** BEFORE UPDATE -> `update_updated_at_column()` (`update_sense_timestamp`); BEFORE INSERT OR UPDATE OF vocab_id -> `set_sense_word_language()` (`trg_dim_word_senses_word_language`)
- **RLS:** Enabled

#### Storage

**Before (2026-09-21):** 960 MB of a 1,144 MB database — ~466 MB TOAST (55,002 float32 1536-d
vectors) and ~456 MB across seven partial HNSW indexes; non-embedding data only ~12 MB.

**After (2026-09-22, `migrations/shrink_sense_embeddings_halfvec768.sql`):** 113 MB; whole
database **252 MB**. Vectors are halfvec(768) (≈1.5 KB each) and there is no ANN index.

Measured trade-offs of the truncation (1536-d → 768-d, live data): cosine correlation 0.980;
top-10 neighbour overlap 92%, top-100 90%; cosines shift up by +0.010–0.019 near the band floor
(per pair) and ~+0.007–0.009 near the top. `dim_distractor_bands.cos_min` was shifted per pair by
the measured amount and `cos_max` by +0.01 (0.75 → 0.76); `sense_neighbours.BAND_MIN` 0.35 → 0.365;
`BAND_MAX` 0.88 unchanged (shift within noise). `calibration_distractor_cache` was cleared and
rebuilt on the new vectors. Growth: ~2 MB per 1,000 new senses. If a language pair grows past
~100k senses, an HNSW index on halfvec(768) costs ~2 KB/row. Undo = re-embed at 1536-d (~$0.03).

**After (2026-10-29, `migrations/sense_vectors_native_standard_512.sql`,
[[decisions/ADR-038-one-sense-vector-native-standard-512]]):** 33 MB; whole database **193 MB**.
One vector per meaning, on the native standard row only (14,230 vectors, was 55,002), halfvec(512).
512-d vs 768-d: correlation 0.983–0.988, top-20 neighbour overlap 90–92%. p95 shift: zh +0.016,
en +0.016, ja +0.012. Bands now: zh pairs `cos_min` 0.445, ja pairs 0.463, en/en 0.366,
`cos_max` 0.77; the four cross-language pairs copy their native pair's band, because they score
native-definition vectors. `sense_neighbours.BAND_MIN` 0.365 → 0.377. The definition-mode
`calibration_distractor_cache` was dropped and rebuilt (162,613 rows). Projected at 10k zh + 10k
ja words: ~75 MB. Since 2026-10-30 that cache is packed one row per anchor and mode (46 → 7 MB,
[[decisions/ADR-039-packed-calibration-distractor-cache]]).

#### Two-level sense generation

Senses are produced by a **single LLM call per word** ([services/vocabulary/sense_generator.py](../../services/vocabulary/sense_generator.py), `SenseGenerator`) on a cheap hosted model (`SENSE_MODEL_DEFAULT` = `deepseek/deepseek-v4-flash`, fallback `qwen/qwen3.6-flash` only on invalid JSON). The call emits numeric-key JSON `{"1":simple, "2":standard, "3":example, "4":pos_int, "5":confidence, "6":should_skip}` and writes **two rows** per sense:

- `definition_level='simple'` — the same meaning rewritten at the lower child age tiers (T1 "The Toddler" / T2 "The Primary Schooler", [ADR-003](../decisions/ADR-003-age-tiers.md)); the T1/T2 `dim_complexity_tiers.description` is injected as the register guide.
- `definition_level='standard'` — the normal learner definition.

`gen_confidence` (key 5) replaces the retired `vocab_validation` LLM call: it sets `is_validated` and flags low-confidence rows for review. POS (key 4) is a language-neutral integer mapped to a canonical string and written to `dim_vocabulary.part_of_speech` when blank. Prompts (`vocab_definition_generation`, `vocab_sense_selection`) are numeric-key, output-language-locked, and exist for zh/en/**ja** (`prompt_templates`, v2; migrations/rewrite_sense_prompts_two_level.sql).

**Read paths must filter `definition_level='standard'`** so the two rows don't fan out duplicates — applied in `get_distractors` and the admin sense lookup. Bulk seeding: [scripts/backfill_senses.py](../../scripts/backfill_senses.py) (resumable via a `simple`-row gate, concurrent, `--language/--model/--limit/--concurrency`; writes only with `--apply`). Inline test-gen passes `prefer_existing=True` to skip already-seeded words.
- **Referenced by:** exercises, word_assets, user_word_ladder, word_quiz_results, user_flashcards, user_vocabulary_knowledge, vocabulary_review_queue

---

### `dim_grammar_patterns` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/modules/grammar-patterns-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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

### ~~`language_model_config`~~ — **DROPPED 2026-05-05**

This table was scaffolded by Phase 4 (2026-04-15) to normalise per-language LLM model assignments away from the growing `dim_languages.*_model` columns, but no code ever read from it. The 2026-05-05 model-routing refactor took a different approach: **`prompt_templates.model` is now the single source of truth** (one row per `(task_name, language_id, version)`, plus a `model` and `provider` column). Both the legacy `dim_languages.*_model` columns and this entire table were dropped by [`migrations/drop_dim_languages_model_columns.sql`](../../migrations/drop_dim_languages_model_columns.sql) and are confirmed absent in the live schema as of 2026-05-12.

The `get_model_for_task(p_task_key text, p_language_id smallint)` RPC still exists in the live DB but its query path is now via `prompt_templates`; verify the SQL body if relying on it.

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
| `native_language_id` | smallint | YES | | FK -> dim_languages. The learner's L1 (added TASK-607, migrations/add_users_native_language.sql). NULL until an onboarding UI sets it — `user_languages` only tracks L2 *study* languages and never recorded this. |
| `has_seen_welcome` | boolean | NO | false | Welcome screen shown (`add_has_seen_welcome.sql`) |

- **Primary Key:** `users_pkey (id)`
- **Unique:** `users_email_key (email)`
- **Indexes:** `idx_users_active (id WHERE deleted_at IS NULL)`, `idx_users_email (email)`, `idx_users_free_test_date (last_free_test_date)`, `idx_users_organization (organization_id WHERE NOT NULL)`, `idx_users_subscription_tier (subscription_tier_id)`
- **Foreign Keys:** `id` -> `auth.users.id`, `subscription_tier_id` -> `dim_subscription_tiers.id`, `organization_id` -> `organizations.id`, `native_language_id` -> `dim_languages.id`
- **Triggers:** AFTER INSERT -> `create_user_dependencies()`, BEFORE UPDATE -> `update_updated_at_column()`
- **RLS:** Enabled. Live policies (2026-11-23): `rls_select` (service_role, own row, or admin), `rls_insert` / `rls_update` / `rls_delete` (service_role only). `authenticated` has SELECT only and no write privilege, so a user can no longer raise their own `subscription_tier_id` (the 2026-10-14 finding is closed; see Security posture).
- **Referenced by:** test_attempts, user_skill_ratings, tests (gen_user), user_languages, user_tokens, token_transactions, flagged_content, user_exercise_sessions, organization_members, vocabulary_review_queue (reviewed_by), user_vocabulary_knowledge, user_flashcards, word_quiz_results, exercise_attempts, user_word_ladder, user_exercise_history, user_pack_selections

---

> **`users_backup` — DROPPED** (Phase 1 migration). Was an empty legacy backup table with no PK.
- **RLS:** Enabled, no policy; `anon`/`authenticated` hold no table grant (service role only). Live 2026-11-23 (the earlier "Disabled" was the 2026-05 state).

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
| `mode` | text | YES |  | CHECK null, `acquisition`, `maintenance` or `auto` |
| `target_minutes` | smallint | YES |  | CHECK null or 1..180 |

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
- **RLS:** Enabled, no policy; `anon`/`authenticated` hold no table grant (service role only). Live 2026-11-23 (the earlier "Disabled" was the 2026-05 state).
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
| `target_age_tier` | smallint | YES |  | FK -> dim_complexity_tiers(id) (`add_topic_age_tier.sql`) |
| `distinctive_vocabulary` | jsonb | NO | `'[]'` | Words distinctive of the topic (`add_topic_age_tier.sql`) |

- **Primary Key:** `topics_pkey (id)`
- **Indexes:** `idx_topics_category (category_id)`, `idx_topics_embedding IVFFlat (embedding vector_cosine_ops, lists=100)`
- **Foreign Keys:** `category_id` -> `categories.id`, `lens_id` -> `dim_lens.id`
- **RLS:** Enabled, no policy; `anon`/`authenticated` hold no table grant (service role only). Live 2026-11-23 (the earlier "Disabled" was the 2026-05 state).
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
- **RLS:** Enabled, no policy; `anon`/`authenticated` hold no table grant (service role only). Live 2026-11-23 (the earlier "Disabled" was the 2026-05 state).

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
| `pitch_payload` | jsonb | YES | | Tokenised pitch-accent data for Japanese tests (pitch trainer) |
| `audio_generated` | boolean | YES | false | |
| `target_age_tier` | smallint | YES | | 1–6 = `dim_complexity_tiers.id`. **The jev-assigned tier of the finished passage** ([[decisions/ADR-029-jev-tier-assignment]]), not the topic's target tier |
| `seeded_elo` | integer | YES | | Lexical-complexity ELO seed from `difficulty_scorer` (NULL on older tests) |
| `age_tier_score` | real | YES | | jev's raw 0 (T1) – 5 (T6) score. `target_age_tier` is derived from it by the language's cut points |
| `age_tier_confidence` | real | YES | | jev confidence for the score answer |
| `age_tier_probabilities` | jsonb | YES | | `{"T1": p, …, "T6": p}` |
| `age_tier_model` | text | YES | | Dated jev snapshot that served the answer |
| `age_tier_calibration` | text | YES | | Which score→tier table: `default`, `ja-2026-09-27`, `zh-2026-09-27` |
| `age_tier_assessed_at` | timestamptz | YES | | |
| `transcript_hash` | text | YES | | Hex sha256 of `transcript`, written by `scripts/audit_transcript_preambles.py` for every active test and read by the sentence segmenter to detect transcript changes (TASK-900, `migrations/tests_transcript_hash.sql`, **planned — not yet applied live**). No trigger: transcripts are edited only by admin tooling. See [[features/test-sentence-references.tech]] |
| `created_at` | timestamptz | YES | now() | |
| `updated_at` | timestamptz | YES | now() | |
| `furigana_payload` | jsonb | YES |  | Furigana annotations of the transcript (`add_furigana_mode.sql`) |
| `passage_hash` | text | YES |  | Hash of the passage for duplicate detection (`task740_phase5_question_passage_dedup.sql`) |
| `passage_embedding` | vector(1536) | YES |  | Passage embedding used by `match_test_passages_by_topic_tier` |

- **Primary Key:** `tests_pkey (id)`
- **Unique:** `tests_slug_key (slug)`
- **Indexes:** `idx_tests_active_tier (is_active, tier WHERE is_active=true)`, `idx_tests_featured (is_featured WHERE is_active=true)`, `idx_tests_language_id (language_id)`, `idx_tests_organization (organization_id WHERE NOT NULL)`, `idx_tests_tier_active (tier, is_active)`, `idx_tests_topic (topic_id)`, `idx_tests_vocab_senses GIN (vocab_sense_ids gin__int_ops)`
- **Foreign Keys:** `gen_user` -> `users.id`, `language_id` -> `dim_languages.id`, `organization_id` -> `organizations.id`, `topic_id` -> `topics.id`
- **Triggers:** BEFORE UPDATE -> `update_updated_at_column()`
- **RLS:** Enabled
- **Referenced by:** test_attempts, questions, test_skill_ratings, token_transactions, user_reports, test_sentences (TASK-901)


**Tier backup tables** (service role only: RLS on, no policies). Restore statements are in `migrations/task819_jev_tier_assignment.sql` and `task821_tier_calibration.sql`.

- `tests_tier_backup_20260926` (`test_id` PK, `target_age_tier`, `difficulty`, `seeded_elo`, `is_active`, `backed_up_at`) — every test before the jev re-tier (307 rows).
- `tests_tier_backup_20260927_v1` (`test_id` PK, `target_age_tier`, `difficulty`, `age_tier_calibration`, `backed_up_at`) — active tests after the first jev pass, before the per-language calibration.

See [[features/test-tier-assignment.tech]].
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
| `distractor_types` | jsonb | YES |  | Distractor type label per option: semantic, grammatical, contextual, null for the correct answer (`add_distractor_types.sql`) |

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
| `elo_reduction_factor` | numeric | YES | NULL | 2026-05-15: populated when reduced-volatility ELO fired on a daily-load retry-slot repeat (anti-grind sentinel). 2026-05-17: now also carries the composed dictation replay K-multiplier when `replay_count > 1`. See [migration](../../migrations/process_test_submission_reduced_repeats.sql), [[decisions/ADR-006-retry-slot-reduced-elo]]. |
| `replay_count` | smallint | YES | NULL | 2026-05-17: dictation-only. NULL for non-dictation rows; ≥ 1 for dictation; `1` = no replay penalty. See [migration](../../migrations/add_dictation_mode.sql). |
| `dictation_word_correct` | integer | YES | NULL | 2026-05-17: dictation-only. Words marked correct after Levenshtein fuzzy tolerance (mirrors `score` for dictation rows). |
| `dictation_word_total` | integer | YES | NULL | 2026-05-17: dictation-only. Canonical tokens after punctuation removal (mirrors `total_questions` for dictation rows). |
| `dictation_diff` | jsonb | YES | NULL | 2026-05-17: dictation-only. Per-token opcode array for the result-screen inline diff. Capped at 200 entries server-side. |
| `created_at` | timestamptz | YES | now() | |
| `furigana_used` | boolean | NO | false | Furigana was on during the attempt; dampens the user K factor (`add_furigana_mode.sql`) |
| `started_at` | timestamptz | YES |  | Client-reported start; written by `apply_attempt_timing_and_progress` |
| `duration_ms` | integer | YES |  | CHECK null or 0 < value < 3,600,000 |
| `prestudied` | boolean | NO | false | A completed prestudy prime preceded the attempt; K factors x0.5 on the first attempt |

- **Primary Key:** `test_attempts_pkey (id)`
- **Unique:** `idx_unique_attempt_idempotency (user_id, idempotency_key WHERE NOT NULL)`
- **Indexes:** `idx_test_attempts_created_at (created_at DESC)`, `idx_test_attempts_language_id (language_id)`, `idx_test_attempts_test_id (test_id)`, `idx_test_attempts_test_type_id (test_type_id)`, `idx_test_attempts_user_id (user_id)`
- **Foreign Keys:** `user_id` -> `users.id`, `test_id` -> `tests.id`, `language_id` -> `dim_languages.id`, `test_type_id` -> `dim_test_types.id`
- **Triggers:** AFTER INSERT -> `update_test_attempts_count()`, AFTER INSERT -> `update_skill_attempts_count()` (x2 triggers)
- **RLS:** Enabled
- **Referenced by:** token_transactions, word_quiz_results, question_attempt_results

---

### `question_attempt_results`

2026-06-06 (Part F #1). One row per gradable comprehension question per attempt — the per-question grain that `process_test_submission` already computed (`v_question_results`) but previously discarded. Mirrors `word_quiz_results`. Powers distractor pick-rate calibration (feeds the distractor-plausibility judge), mis-key detection (strong scorers consistently "wrong" ⇒ LLM keyed the wrong answer), and per-item p-values. Keeps item-grain IRT possible later without a backfill. (A per-question `response_time_ms` column was added by Part F #4 and dropped by Part G — comprehension is order-free, so only total test time is meaningful.)

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | bigint | NO | GENERATED ALWAYS AS IDENTITY | PK |
| `user_id` | uuid | NO | | FK -> users |
| `test_id` | uuid | NO | | FK -> tests |
| `question_id` | uuid | NO | | FK -> questions |
| `attempt_id` | uuid | YES | | FK -> test_attempts |
| `is_correct` | boolean | NO | | |
| `selected_answer` | text | YES | | NULL = question left unanswered (stored via `NULLIF(...,'')`) |
| `correct_answer` | text | YES | | The keyed answer at submission time |
| `is_first_attempt` | boolean | NO | true | Filter to `true` for honest per-item p-values |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `question_attempt_results_pkey (id)`
- **Indexes:** `idx_qar_question (question_id)`, `idx_qar_question_selected (question_id, selected_answer)`, `idx_qar_question_first (question_id, is_first_attempt)`, `idx_qar_test (test_id)`, `idx_qar_user (user_id)`, `idx_qar_attempt (attempt_id)`
- **Foreign Keys:** `user_id` -> `users.id`, `test_id` -> `tests.id`, `question_id` -> `questions.id`, `attempt_id` -> `test_attempts.id`
- **RLS:** Enabled — own-data (`auth.uid() = user_id`) + service-role + admin-view triple, mirroring `word_quiz_results`. Written by `process_test_submission` (SECURITY DEFINER, bypasses RLS) inside a nested `BEGIN/EXCEPTION` so a logging failure can never fail a learner's submission.
- **Source:** [migration](../../migrations/partF_question_attempt_results.sql)

---

### `question_type_distributions` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/db_backups/stage1-unused-tables-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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
| `model` | text | YES |  | Per-template model override |
| `provider` | text | YES |  | Per-template provider override |
| `tier_id` | smallint | YES |  | FK -> dim_complexity_tiers(id) |

- **Primary Key:** `prompt_templates_pkey (id)`
- **Unique:** `idx_prompt_templates_task_lang_ver (task_name, language_id, version)`
- **Indexes:** `idx_prompt_templates_language (language_id)`, `idx_prompt_templates_task_language (task_name, language_id, is_active)`
- **Foreign Keys:** `language_id` -> `dim_languages.id`
- **RLS:** Enabled, no policy; `anon`/`authenticated` hold no table grant (service role only). Live 2026-11-23 (the earlier "Disabled" was the 2026-05 state).

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
- **RLS:** Enabled, no policy; `anon`/`authenticated` hold no table grant (service role only). Live 2026-11-23 (the earlier "Disabled" was the 2026-05 state).

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
- **RLS:** Enabled, no policy; `anon`/`authenticated` hold no table grant (service role only). Live 2026-11-23 (the earlier "Disabled" was the 2026-05 state).

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
- **RLS:** Enabled, no policy; `anon`/`authenticated` hold no table grant (service role only). Live 2026-11-23 (the earlier "Disabled" was the 2026-05 state).

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
| `daily_session_targets` | jsonb | YES |  | Practice minute targets and resolver output of the day |
| `completed_blocks` | jsonb | NO | `'[]'` | Completed daily-session blocks (`phase13_daily_test_loads_completed_blocks.sql`) |

- **Primary Key:** `daily_test_loads_pkey (id)`
- **Unique:** `daily_test_loads_user_id_language_id_load_date_key (user_id, language_id, load_date)`
- **Indexes:** `idx_daily_loads_lookup (user_id, language_id, load_date)`
- **Foreign Keys:** `user_id` -> `public.users.id` ON DELETE CASCADE (fixed 2026-05-13 via [migrations/fix_daily_test_loads_user_id_fk.sql](../../migrations/fix_daily_test_loads_user_id_fk.sql); previously FK'd to `auth.users.id`).
- **RLS:** Enabled (2026-05-12 via [migrations/enable_rls_on_user_owned_tables.sql](../../migrations/enable_rls_on_user_owned_tables.sql)). Policies: `dtl_own_data` (ALL where `auth.uid() = user_id`), `dtl_service_role` (ALL where `auth.role() = 'service_role'`), `dtl_admin_view` (SELECT where `is_admin(auth.uid())`).
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
- **RLS:** Enabled (2026-05-12). No `user_id` column — policies join through `load_id -> daily_test_loads.user_id`. Policies: `dtli_own_data` (ALL where `EXISTS (... daily_test_loads d WHERE d.id = load_id AND d.user_id = auth.uid())`), `dtli_service_role` (ALL where `auth.role() = 'service_role'`), `dtli_admin_view` (SELECT where `is_admin(auth.uid()) OR EXISTS ...`).

---

## 4. Conversation System

Tables for the persona-driven conversation generation pipeline.

---

### `conversation_domains` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/modules/conversations-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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

### `personas` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/modules/conversations-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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

### `persona_pairs` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/modules/conversations-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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

### `scenarios` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/modules/conversations-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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

### `conversations` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/modules/conversations-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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

### `conversation_generation_queue` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/modules/conversations-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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

> **Content lives in Storage (ADR-049, accepted; cut-over done 2026-11-19, TASK-1030; transition
> code removed, TASK-1031).** `content` (119 MB of the then 200 MB table) is gone: it lives only in
> one immutable JSON file per sense and version in the private Storage bucket `exercise-content`
> (`{lang}/{word_sense_id}.v{content_version}.json`, lang = zh/en/ja for language 1/2/3). The
> table keeps selection metadata, `tags` and the IRT/attempt columns. Columns marked *(ADR-049)*
> below are added by `migrations/exercise_content_storage.sql`; `content` was dropped and the
> content-expression unique index replaced by `uq_exercises_context_free_variant_v2` by
> `migrations/exercise_content_drop_column.sql`. No code reads or writes the column any more
> (no `db` read/write mode, no DB fallback). Every `INSERT` into `exercises` and every content
> change must go through `services/exercise_content/store.write_sense` (enforced by
> `tests/test_exercise_content_write_paths.py`); `DELETE`s and metadata-only `UPDATE`s
> (`is_active`, `irt_*`, counts, `tags`) may stay direct. See
> [[decisions/ADR-049-exercise-content-in-storage]], [[tasklist/exercise-content-storage.tasks]].

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `language_id` | integer | NO | | FK -> dim_languages |
| `exercise_type` | text | NO | | Free-text exercise type identifier |
| `source_type` | exercise_source_type | NO | | ENUM: grammar/vocabulary/collocation/conversation/style |
| ~~`grammar_pattern_id`~~ | integer | YES | | **Dropping 2026-09-21** (grammar source archived; 0 non-null) |
| `word_sense_id` | integer | YES | | FK -> dim_word_senses (when source_type='vocabulary') |
| `corpus_collocation_id` | integer | YES | | (when source_type='collocation') |
| ~~`conversation_id`~~ | uuid | YES | | **Dropping 2026-09-21** with the 7,352 conversation exercises (never servable: no word_sense_id) |
| ~~`style_pack_item_id`~~ | bigint | YES | | **Dropping 2026-09-21** (packs archived; 0 non-null) |
| `word_asset_id` | bigint | YES | | FK -> word_assets |
| ~~`content`~~ | — | — | | **Dropped 2026-11-19 (ADR-049 cut-over).** Exercise content lives only in Storage (`exercise-content/{lang}/{word_sense_id}.v{content_version}.json`), read with `store.hydrate` and written with `store.write_sense`. |
| `content_version` *(ADR-049)* | integer | NO | 0 | Version of the sense's content file this row's content is in. 0 = the backfill export (catalog-only `ADD COLUMN`, no row rewrite); later versions come from `exercise_content_version_seq` and are set by `exercise_content_commit` on every row of the sense. Applied live 2026-11-17 (TASK-1026). |
| `dedupe_key` *(ADR-049)* | text | YES | | `md5(coalesce(content->>'context_sentence',''))` for the 8 context-free types (`tone_id_word`, `hanzi_to_pinyin`, `pinyin_to_hanzi`, `kanji_to_reading`, `reading_to_kanji`, `phonetic_recognition`, `classifier_match`, `counter_match`), NULL otherwise. Set by `exercise_content_commit` from the JSON passed in; existing rows back-filled in cut-over step 1 (30,491 rows, 2026-11-18). Applied live 2026-11-17. The key of `uq_exercises_context_free_variant_v2`. |
| `tags` | jsonb | NO | '{}' | |
| `difficulty_static` | numeric | YES | | |
| `irt_difficulty` | numeric | NO | 0.0 | Item Response Theory difficulty (tier-seeded; nightly-fitted once `irt_n_attempts ≥ 20`) |
| `irt_discrimination` | numeric | NO | 1.0 | IRT discrimination parameter (tier-seeded; nightly-fitted once `irt_n_attempts ≥ 20`) |
| `irt_n_attempts` | integer | NO | 0 | Phase 11. Number of first-attempt observations that fed the latest IRT fit. 0 = never calibrated. |
| `irt_calibrated_at` | timestamptz | YES | | Phase 11. Timestamp of the latest successful IRT fit; NULL = still on tier-seeded values. |
| `irt_se_difficulty` | numeric(5,3) | YES | | Phase 11. Standard error of the fitted `irt_difficulty` from the inverse Hessian. NULL when the Hessian wasn't invertible. |
| `complexity_tier` | text | YES | | CHECK: T1-T6 |
| `ladder_level` | integer | YES | | CHECK: 1-9 or NULL. Vocabulary ladder level |
| `pattern_code` | text | YES | | Denormalized grammar pattern code |
| `attempt_count` | integer | NO | 0 | |
| `correct_count` | integer | NO | 0 | |
| `is_active` | boolean | NO | true | |
| `generation_batch_id` | uuid | YES | | |
| `created_at` | timestamptz | NO | now() | |

- **Primary Key:** `exercises_pkey (id)`
- **Indexes (live check 2026-11-17):** `exercises_pkey (id)`, `idx_exercises_ladder (word_sense_id, ladder_level WHERE ladder_level NOT NULL)`, ~~`uq_exercises_context_free_variant`~~ UNIQUE `(word_sense_id, exercise_type, md5(coalesce(content->>'context_sentence','')))` WHERE `is_active` and `exercise_type` is one of the 8 context-free types (`migrations/task743_context_free_exercise_caps.sql`; **dropped with `content` on 2026-11-19**, replaced by `uq_exercises_context_free_variant_v2`, see below), `idx_exercises_sense (word_sense_id WHERE NOT NULL)`, `idx_exercises_word_asset_id (word_asset_id)` (`latency_2026_11_db.sql`), `idx_exercises_type (exercise_type)`, `idx_exercises_tier (complexity_tier)`, `idx_exercises_source (source_type)`, `idx_exercises_language (language_id)`, `idx_exercises_active (is_active WHERE is_active=true)`, `idx_exercises_collocation (corpus_collocation_id WHERE NOT NULL)`, `idx_exercises_irt_calibrated (irt_calibrated_at WHERE NOT NULL)`. **Not live** (listed here before 2026-11-17 in error): `idx_exercises_content_gin`, `idx_exercises_tags_gin`, `idx_exercises_conversation`, `idx_exercises_grammar`, `idx_exercises_style_item`.
- **ADR-049 cut-over (live 2026-11-19):** `uq_exercises_context_free_variant_v2` UNIQUE `(word_sense_id, exercise_type, dedupe_key)` WHERE `is_active AND word_sense_id IS NOT NULL AND exercise_type IN (<the 8 types>)` replaced `uq_exercises_context_free_variant`, which was dropped along with `content`. Sizes after `VACUUM FULL`: heap 55 MB, indexes 16 MB, total 72 MB (was 200 MB).
- **ADR-049 objects (applied live 2026-11-17, TASK-1026):** sequence `public.exercise_content_version_seq` (integer, START 1, gaps allowed; USAGE/SELECT to `service_role` only); Storage bucket `exercise-content` (private, 1 MB file limit, `application/json`; one file per sense and version, `_archive/` for cut-over exports, never swept); RPCs `exercise_content_begin`, `exercise_content_commit`, `exercise_content_live_versions` (see Key Database Functions). The cut-over also deleted the 10 zh collocation rows with no `word_sense_id` (archived by id to `_archive/exercises-no-sense-20261118.json`) and dropped the live-only semdisc leftovers `apply_semdisc_notes(jsonb)`, `backup_semdisc_content_20261115` and `semdisc_rewrite_work` (archived to `_archive/semdisc-20261115/`); all absent live, checked 2026-11-19.
- **Foreign Keys:** `language_id` -> `dim_languages.id`, `grammar_pattern_id` -> `dim_grammar_patterns.id`, `word_sense_id` -> `dim_word_senses.id`, `word_asset_id` -> `word_assets.id`, `conversation_id` -> `conversations.id`, `style_pack_item_id` -> `style_pack_items.id`
- **Constraints:** `chk_source_fk` — at least one of `grammar_pattern_id`, `word_sense_id`, `corpus_collocation_id`, `conversation_id`, `style_pack_item_id` must be non-null. **After the 2026-09-21 archive migration:** rebuilt as at least one of `word_sense_id`, `corpus_collocation_id`.
- **RLS:** Enabled, no policy; `anon`/`authenticated` hold no table grant (service role only). Live 2026-11-23 (the earlier "Disabled" was the 2026-05 state).
- **Referenced by:** exercise_attempts

---

### `exercise_explanations` (NOT applied — `migrations/exercise_explanations.sql`, ADR-064)

Per-option answer feedback for one exercise in one learner language, written once by
`services/exercise_explanations.py` on first serve. Service role only (RLS on, no policy).

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `exercise_id` | uuid | NO | | PK part; FK -> exercises ON DELETE CASCADE |
| `nl_language_id` | smallint | NO | | PK part; FK -> dim_languages |
| `content_version` | integer | NO | 0 | `exercises.content_version` it was written for; a mismatch means stale |
| `payload` | jsonb | NO | | `{"sentences":[{"text","is_correct","meaning","explanation","correction"}]}` |
| `model` | text | YES | | OpenRouter slug that wrote it |
| `prompt_version` | smallint | NO | | `exercise_explanations.PROMPT_VERSION` |
| `created_at` | timestamptz | NO | now() | |

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
| `p_known_before` | numeric | YES |  | BKT p_known before this attempt; set by `record_exercise_attempt` on first attempts |
| `p_known_after` | numeric | YES |  | BKT p_known after this attempt |
| `source` | text | YES |  | CHECK null, `prestudy` or `intro`: attempts made in a prestudy prime or a new-word-drill session |

- **Primary Key:** `exercise_attempts_pkey (id)`
- **Indexes:** `idx_ea_exercise_id (exercise_id)`, `idx_ea_user_created (user_id, created_at DESC)`, `idx_ea_user_response_gin GIN (user_response)`, `idx_ea_user_sense_type (user_id, sense_id, exercise_type, created_at DESC)`
- **Foreign Keys:** `user_id` -> `users.id`, `exercise_id` -> `exercises.id`
- **RLS:** Enabled (2026-05-12 via [migrations/enable_rls_on_user_owned_tables.sql](../../migrations/enable_rls_on_user_owned_tables.sql)). Policies: `ea_own_data` (ALL where `auth.uid() = user_id`), `ea_service_role` (ALL where `auth.role() = 'service_role'`), `ea_admin_view` (SELECT where `is_admin(auth.uid())`).

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
| `validation_warnings` | text[] | YES |  | Non-blocking validation warnings (`phase15_word_assets_validation_warnings.sql`) |

- **Primary Key:** `word_assets_pkey (id)`
- **Unique:** `word_assets_sense_id_asset_type_key (sense_id, asset_type)`
- **Indexes:** `idx_word_assets_batch (generation_batch_id WHERE NOT NULL)`, `idx_word_assets_sense (sense_id)`, `idx_word_assets_valid (sense_id, asset_type WHERE is_valid=true)`
- **Foreign Keys:** `sense_id` -> `dim_word_senses.id`, `language_id` -> `dim_languages.id`
- **RLS:** Enabled, no policy; `anon`/`authenticated` hold no table grant (service role only). Live 2026-11-23 (the earlier "Disabled" was the 2026-05 state).
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
| `placement_correct` | smallint | NO | 0 | Placement answers counted as correct evidence (`placement_evidence_kind.sql`) |
| `placement_wrong` | smallint | NO | 0 | Placement answers counted as wrong evidence |

- **Primary Key:** `user_vocabulary_knowledge_pkey (id)`
- **Unique:** `user_vocabulary_knowledge_user_id_sense_id_key (user_id, sense_id)`
- **Indexes:** `idx_uvk_user_language (user_id, language_id)`, `idx_uvk_user_pknown (user_id, p_known)`, `idx_uvk_user_status (user_id, status)`
- **Foreign Keys:** `user_id` -> `users.id`, `sense_id` -> `dim_word_senses.id`, `language_id` -> `dim_languages.id`
- **RLS:** Enabled (2026-05-12 via [migrations/enable_rls_on_user_owned_tables.sql](../../migrations/enable_rls_on_user_owned_tables.sql)). Policies: `uvk_own_data` (ALL where `auth.uid() = user_id`), `uvk_service_role` (ALL where `auth.role() = 'service_role'`), `uvk_admin_view` (SELECT where `is_admin(auth.uid())`).

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
- **RLS:** Enabled (2026-05-12 via [migrations/enable_rls_on_user_owned_tables.sql](../../migrations/enable_rls_on_user_owned_tables.sql)). Policies: `uf_own_data` (ALL where `auth.uid() = user_id`), `uf_service_role` (ALL where `auth.role() = 'service_role'`), `uf_admin_view` (SELECT where `is_admin(auth.uid())`).

---

### `user_word_ladder`

Per-user vocabulary ladder progression. Canonical progression state is the Phase 8 Momentum Bands columns (`family_confidence`, `current_ring`, `gates_passed`, `stress_test_score`, `last_exercised_family`). The Phase 4 counter columns are still written by `ladder_record_attempt` ([phase8_momentum_bands.sql:664-695](../../migrations/phase8_momentum_bands.sql#L664-L695)) but are not consumed by any progression code path — they survive as observability data. See [[decisions/ADR-005-momentum-bands]].

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `user_id` | uuid | NO | | FK -> users |
| `sense_id` | integer | NO | | FK -> dim_word_senses |
| `current_level` | integer | NO | 1 | CHECK: 1-9; legacy/metadata after Phase 8 |
| `active_levels` | integer[] | NO | '{1,2,3,4,5,6,7,8,9}' | Concrete nouns get [1,2,3,4,6,7,9] |
| `updated_at` | timestamptz | NO | now() | |
| **Phase 4 (counters)** | | | | *Written on every attempt; never read* |
| `first_try_success_count` | integer | NO | 0 | First-attempt successes (lifetime) |
| `first_try_failure_count` | integer | NO | 0 | First-attempt failures (lifetime) |
| `consecutive_failures` | integer | NO | 0 | Reset to 0 on any correct; per-family-tracked via `last_exercised_family` |
| `total_attempts` | integer | NO | 0 | Total attempts across all sessions |
| `word_state` | text | NO | 'active' | CHECK: new/active/gated/pre_mastery/relearning/mastered (Phase 8 rewrote the CHECK; Phase 4 `fragile`/`stable` values migrated to `active`) |
| `last_success_session_date` | date | YES | | Date of last first-attempt success |
| `review_due_at` | timestamptz | YES | | Next scheduled review (NULL for mastered — FSRS owns scheduling) |
| **Phase 8 (Momentum Bands — canonical)** | | | | |
| `family_confidence` | jsonb | NO | `{form_recognition:0.10, meaning_recall:0.10, form_production:0.10, collocation:0.10, semantic_discrimination:0.10, contextual_use:0.10}` | Per-family BKT confidence (clamped 0.02–0.98 at update time) |
| `gates_passed` | jsonb | NO | `{gate_a:false, gate_b:false}` | Threshold gate completion flags |
| `current_ring` | integer | NO | 1 | CHECK: 1-4 |
| `stress_test_score` | real | YES | | Last stress test score (0.0–1.0); NULL if not yet taken |
| `last_exercised_family` | text | YES | | Used by `consecutive_failures` heuristic |
| **Phase 10 (advancement gating + demotion)** | | | | |
| `family_success_dates` | jsonb | NO | `{form_recognition:[], meaning_recall:[], form_production:[], collocation:[], semantic_discrimination:[], contextual_use:[]}` | Per-family ISO date arrays of first-attempt successes, trimmed to most recent 2. Used by ring-advancement cross-session gate (≥ 2 distinct dates required) and reset on demotion for the demoted-into-ring families. |
| **New-word drill (2026-11-10, ADR-040)** | | | | |
| `intro_stage` | smallint | YES | | 1–4 = next intro session to run while `word_state = 'intro'`; NULL otherwise |
| `intro_due_date` | date | YES | | Learner-local date the next intro session is due |
| `intro_history` | jsonb | NO | `'[]'` | One entry per finished intro session `{stage, date, at, target, counted, items, cold_correct, passed, formats}` plus events `{event: queued/overload/restart, source?, met?, at}`; last 12 kept |
| `created_at` | timestamptz | NO | now() |  |

- **Primary Key:** `user_word_ladder_pkey (user_id, sense_id)`
- **Indexes:** `idx_user_word_ladder_user (user_id)`, `idx_user_word_ladder_review_due (user_id, review_due_at WHERE review_due_at IS NOT NULL)`, `idx_user_word_ladder_state (user_id, word_state)`, `idx_user_word_ladder_ring (user_id, current_ring)`, `idx_user_word_ladder_intro_due (user_id, intro_due_date) WHERE word_state = 'intro'`
- **Foreign Keys:** `user_id` -> `users.id`, `sense_id` -> `dim_word_senses.id`
- **CHECK constraints:** `user_word_ladder_word_state_check CHECK (word_state IN ('new','active','gated','pre_mastery','relearning','mastered','intro'))` (`intro` added 2026-11-10), `user_word_ladder_intro_stage_check CHECK (intro_stage IS NULL OR intro_stage BETWEEN 1 AND 4)`, `user_word_ladder_current_ring_check CHECK (current_ring BETWEEN 1 AND 4)`, `user_word_ladder_current_level_check CHECK (current_level BETWEEN 1 AND 9)`
- **RLS:** Enabled (2026-05-12 via [migrations/enable_rls_on_user_owned_tables.sql](../../migrations/enable_rls_on_user_owned_tables.sql)). Policies: `uwl_own_data` (ALL where `auth.uid() = user_id`), `uwl_service_role` (ALL where `auth.role() = 'service_role'`), `uwl_admin_view` (SELECT where `is_admin(auth.uid())`).

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
- **RLS:** Enabled (2026-05-12 via [migrations/enable_rls_on_user_owned_tables.sql](../../migrations/enable_rls_on_user_owned_tables.sql)). Policies: `wqr_own_data` (ALL where `auth.uid() = user_id`), `wqr_service_role` (ALL where `auth.role() = 'service_role'`), `wqr_admin_view` (SELECT where `is_admin(auth.uid())`).

---

### `vocabulary_review_queue` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/db_backups/stage1-unused-tables-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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
- **RLS:** Enabled, no policy; `anon`/`authenticated` hold no table grant (service role only). Live 2026-11-23 (the earlier "Disabled" was the 2026-05 state).
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
- **RLS:** Enabled, no policy; `anon`/`authenticated` hold no table grant (service role only). Live 2026-11-23 (the earlier "Disabled" was the 2026-05 state).
- **Referenced by:** pack_collocations

---

### `collocation_packs` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/modules/language-packs-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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

### `pack_collocations` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/modules/language-packs-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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

### `user_pack_selections` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/modules/language-packs-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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
- **RLS:** Enabled, no policy; `anon`/`authenticated` hold no table grant (service role only). Live 2026-11-23 (the earlier "Disabled" was the 2026-05 state).

---

### `style_pack_items` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/modules/language-packs-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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

### `pack_style_items` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/modules/language-packs-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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

## 7. Mystery System (removed)

Multi-scene narrative mysteries with comprehension questions and ELO matching.

> **Removed.** Tables dropped 2026-09-22; the feature was removed from the codebase 2026-11-23 (TASK-1227). The `dim_test_types` rows `mystery` (id 8) and `listening_lab` (id 12), `questions.pool_source` and the `mystery_*` prompt rows are also gone live (checked 2026-11-23). The sections below are history only.

---

### `mysteries` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/modules/mysteries-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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

### `mystery_scenes` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/modules/mysteries-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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

### `mystery_questions` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/modules/mysteries-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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

### `mystery_progress` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/modules/mysteries-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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

### `mystery_skill_ratings` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/modules/mysteries-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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

### `mystery_attempts` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/modules/mysteries-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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

### `organizations` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/db_backups/stage1-unused-tables-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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

### `organization_members` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/db_backups/stage1-unused-tables-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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

### `llm_calls`

Observability log for every LLM round-trip made through `services/llm_service.py`'s
`call_llm()` (OpenRouter, Ollama, and the headless Claude Code CLI transport). One
row per API call, written centrally by `_log_llm_call()` — no call site inserts
directly, so no pipeline can skip logging by omission. Truncated 2026-09-21
(43,605 rows moved to `archive/db_backups/llm-calls-log-2026-09-21.zip` by
`migrations/archive_unused_modules_2026_09_21.sql`); the table has carried only
smoke-test volume since. `cost_usd`/`latency_ms`/`language_code` are already
populated on every `call_llm()` invocation regardless of pipeline; the seven
columns below (prompt_tokens .. generation_batch_id) are Phase 0 cost-instrumentation
additions ([migrations/llm_calls_cost_instrumentation.sql](../../migrations/llm_calls_cost_instrumentation.sql),
applied live 2026-10-09) aimed specifically at making vocabulary-ladder generation cost
attributable per sense and per call kind.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `pipeline` | text | YES | | e.g. `vocab_ladder`, `test_gen`, `diagnostics` |
| `task_name` | text | YES | | Should match `prompt_templates.task_name`; judges log under `judge_<name>`, not their own prompt's task_name (no wiki page documents this namespace; see `services/exercise_generation/judges/base.py::log_judge_verdict`) |
| `template_version` | integer | YES | | `prompt_templates.version` when applicable |
| `model` | text | YES | | The model actually served by the response (`response.model`) when the provider echoes it, else the requested slug. Claude CLI calls log `claude-cli:<model>` |
| `temperature` | real | YES | | |
| `seed` | integer | YES | | |
| `prompt_hash` | bytea | YES | | sha256 of `system_prompt + '\n' + prompt`, hex-encoded on insert |
| `raw_response` | text | YES | | Full response text/JSON |
| `parsed_ok` | boolean | YES | | |
| `schema_ok` | boolean | YES | | NULL when no Pydantic schema was supplied |
| `judge_verdict` | text | YES | | Set by a *second* row judges write via `log_judge_verdict()`, not by the raw-call row itself |
| `judge_confidence` | real | YES | | |
| `latency_ms` | integer | YES | | Wall-clock time of the API round-trip |
| `cost_usd` | numeric | YES | | `usage.cost` from OpenRouter (requires `extra_body={'usage':{'include': True}}`, only sent to OpenRouter clients). NULL — never fabricated — when the provider reports nothing (Ollama, Claude CLI, or a provider that omits usage accounting) |
| `artifact_id` | uuid | YES | | Optional trace-back UUID (exercise_id, test_id, etc.); NOT the same axis as `sense_id` below |
| `created_at` | timestamptz | YES | now() | |
| `language_code` | text | YES | | Study-language tag (`zh`\|`en`\|`ja`); observability only, does not affect model resolution |
| `prompt_tokens` | integer | YES | | `usage.prompt_tokens` |
| `completion_tokens` | integer | YES | | `usage.completion_tokens` |
| `cached_tokens` | integer | YES | | `usage.prompt_tokens_details.cached_tokens` — portion of the prompt served from a provider-side cache |
| `reasoning_tokens` | integer | YES | | `usage.completion_tokens_details.reasoning_tokens`; NULL for non-reasoning models |
| `sense_id` | integer | YES | | `dim_word_senses.id` this call generated/judged for. No FK (observability tag, not a referential relationship — a sense delete must not be blocked by call history). Threaded via a contextvar (`services.llm_service.generation_context`) set once per sense in `VocabAssetPipeline._generate_for_sense_impl`, so nested generator/judge calls — including those fanned out across `BatchModeThreadPoolExecutor` worker threads — populate it without each call site passing it explicitly |
| `call_role` | text | YES | | CHECK-constrained to `primary`\|`retry`\|`json_repair`\|`repair`\|`salvage`. Defaults to `primary` when a caller doesn't specify one (see `services.llm_service.CALL_ROLE_*` constants) |
| `generation_batch_id` | uuid | YES | | Matches `word_assets.generation_batch_id`. Same contextvar-fallback mechanism as `sense_id`. No FK |

- **Primary Key:** `llm_calls_pkey (id)`
- **Indexes (live 2026-11-23):** `idx_llm_calls_sense_id (sense_id)`, `idx_llm_calls_created_at (created_at)`, `idx_llm_calls_task_created (task_name, created_at DESC)`, `idx_llm_calls_parsed_schema_created (parsed_ok, schema_ok, created_at DESC)`, `idx_llm_calls_pipeline_created (pipeline, created_at DESC)`, `idx_llm_calls_artifact (artifact_id) WHERE artifact_id IS NOT NULL`, `idx_llm_calls_language_pipeline_created (language_code, pipeline, task_name, created_at DESC)`
- **Check constraints (live):** `llm_calls_call_role_check` — `call_role IS NULL OR call_role IN ('primary','retry','json_repair','repair','salvage')`
- **RLS:** Enabled, no policy; `anon` and `authenticated` hold no grant; `service_role` has SELECT and INSERT (and the other write privileges). The earlier text (RLS disabled, indexes pending) described the pre-hardening state.
- **Writer:** `services/llm_service.py::_log_llm_call()` is the sole writer for the raw-call row; `services/exercise_generation/judges/base.py::log_judge_verdict()` writes a second, narrower row (`pipeline`, `task_name`, `model`, `judge_verdict`, `judge_confidence` only) for the classified verdict, so a judge's raw call and its verdict are two rows, not one
- **Degrade path:** `_log_llm_call()` inserts the new columns unconditionally; if the migration hasn't been applied yet in a given environment, `_insert_llm_call_row()` catches the resulting "unknown column" error, logs one WARNING per process, and retries the insert with just the pre-migration columns — so deploying this code ahead of the migration never drops a row, it just logs a thinner one until the migration lands
- **Readers:** `scripts/run_generation_batch.py::spend_since()` (budget ceiling — sums `cost_usd` since a timestamp, no `pipeline`/`language_code` filter, the ceiling is shared across languages; no ADR records that caveat) and `_judge_verdicts_since()` (per-task accept/flag/reject counts for the chunk report)

---

### `flagged_content` — ARCHIVED & DROPPED 2026-09-22

> Exported to `archive/db_backups/stage1-unused-tables-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). No code reads it. Section kept for history.
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

## 11. Test Sentence References (TASK-901 — live)

Sentence-level L2 segmentation of test transcripts and their L1 reference translations
([[features/test-sentence-references.tech]], [[decisions/ADR-037-sentence-level-l1-references]]).
Migration: `migrations/test_sentence_references_schema.sql` (applied live; both tables hold data: Japanese and Chinese references exist for every active test per [[log]] 2026-11-17); the L1-script trigger fix is pending (section 14). SQL test:
`tests/sql/test_sentence_references.sql`. Both tables are service-role only (RLS on, every
client privilege revoked, no policies — [[decisions/ADR-034-no-client-db-writes]]).

### `test_sentences`

One row per sentence of an active test's transcript, written by `scripts/build_test_sentences.py` (TASK-902).

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | bigint | NO | identity | PK |
| `test_id` | uuid | NO | | FK -> tests ON DELETE CASCADE |
| `idx` | smallint | NO | | 0-based sentence index. CHECK >= 0. UNIQUE (test_id, idx) |
| `char_start` | integer | NO | | Half-open code-point span in `tests.transcript`. CHECK >= 0 |
| `char_end` | integer | NO | | CHECK char_end > char_start |
| `token_start` | integer | YES | | Half-open span in `tests.vocab_token_map`. NULL when the test has no token map |
| `token_end` | integer | YES | | CHECK: both token_* NULL, or both set with token_end > token_start >= 0 |
| `l2_text` | text | NO | | The sentence, terminator attached. CHECK length > 0; trigger enforces `l2_text = substr(transcript, char_start+1, char_end-char_start)` |
| `transcript_hash` | text | NO | | sha256 of the transcript at segmentation time; differs from `tests.transcript_hash` when the rows are stale |
| `created_at` | timestamptz | YES | now() | |

- **Primary Key:** `test_sentences_pkey (id)`
- **Unique:** `test_sentences_test_id_idx_key (test_id, idx)`
- **Indexes:** `idx_test_sentences_test_idx (test_id, idx)`
- **Foreign Keys:** `test_id` -> `tests.id` (CASCADE)
- **Triggers:** BEFORE INSERT OR UPDATE OF test_id, char_start, char_end, l2_text -> `test_sentences_check_l2_text()` (check_violation on mismatch or span past the transcript end)
- **RLS:** Enabled, no policies; `REVOKE ALL FROM PUBLIC, anon, authenticated`; `GRANT ALL TO service_role`
- **Referenced by:** test_sentence_references

### `test_sentence_references`

L1 reference translations per sentence, with authoring/review provenance. At most one active row per (sentence, L1).

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | bigint | NO | identity | PK |
| `sentence_id` | bigint | NO | | FK -> test_sentences ON DELETE CASCADE |
| `l1_language_id` | smallint | NO | | FK -> dim_languages |
| `l1_text` | text | NO | | The reference. CHECK length > 0; trigger rejects the test's L2 script (Han for zh; Han or kana for ja; none for en) |
| `author_model` | text | NO | | e.g. `claude-sonnet-5-5` (the authoring subagent's model) |
| `prompt_version` | text | NO | | Skill version string, e.g. `sr-1.0` |
| `arm` | text | YES | | CHECK: `sentencewise` \| `aligned` (pilot) or NULL |
| `reviewer_model` | text | YES | | |
| `review_verdict` | text | NO | 'pending' | CHECK: `pending` \| `pass` \| `rewritten` \| `fail` |
| `tightness` | real | YES | | Tier 0 similarity of the reviewer's blind back-translation to `l2_text`. CHECK 0–1 |
| `entailment_ok` | boolean | YES | | Reviewer's mutual-entailment judgement |
| `is_active` | boolean | NO | false | Partial unique index: one active row per (sentence_id, l1_language_id) |
| `run_id` | text | YES | | RUN directory name (provenance) |
| `created_at` | timestamptz | YES | now() | |
| `faithful_reviews` | smallint | NO | 0 | CHECK >= 0; number of independent reviews that passed the same text; two override the tightness floor ([[decisions/ADR-050-reviewer-agreement-overrides-tightness-floor]]) |

- **Primary Key:** `test_sentence_references_pkey (id)`
- **Unique:** `uq_test_sentence_references_active (sentence_id, l1_language_id) WHERE is_active`
- **Indexes:** `idx_test_sentence_references_sentence (sentence_id, l1_language_id)`, `idx_test_sentence_references_run (run_id WHERE NOT NULL)`
- **Foreign Keys:** `sentence_id` -> `test_sentences.id` (CASCADE), `l1_language_id` -> `dim_languages.id`
- **Triggers:** BEFORE INSERT OR UPDATE OF sentence_id, l1_text -> `test_sentence_references_check_l1_script()` (looks up the test's `dim_languages.language_code` through the sentence; check_violation on a script leak)
- **RLS:** Enabled, no policies; `REVOKE ALL FROM PUBLIC, anon, authenticated`; `GRANT ALL TO service_role`

### `dt_passage` — columns added by the same migration

`dt_passage` itself is specified in [[features/dual-translation.tech]] (`migrations/dual_translation_groundwork.sql`). TASK-901 adds:

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `sentence_start` | smallint | YES | | Inclusive first `test_sentences.idx` of the passage within `source_ref_id`. NULL only on the old whole-passage rows (all deleted 2026-11-17; GET /next never serves a row without a range) |
| `sentence_end` | smallint | YES | | Inclusive last index. CHECK `dt_passage_sentence_range_chk`: both NULL, or both set with 0 <= sentence_start <= sentence_end (added NOT VALID, then validated) |

- **Unique:** `uq_dt_passage_sentence_range (source_ref_id, sentence_start, sentence_end) WHERE both NOT NULL` — a sentence range of a test is extracted once and reused.

---

## 12. Test Prestudy (live)

Migrations: `migrations/prestudy_elo_factor.sql`, then `migrations/prestudy_workflow.sql`
(both applied live; the tables, `test_attempts.prestudied`, `exercise_attempts.source` and `process_test_submission(..., p_prestudied)` exist). Spec: [[features/test-prestudy]]. Both new
tables are service-role only (RLS on, all client privileges revoked, no policy).

### `prestudy_sessions`
One row per prestudy session (the Measurement record).

| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | `gen_random_uuid()` |
| `user_id` | uuid | FK `auth.users` ON DELETE CASCADE |
| `language_id` | smallint | FK `dim_languages` |
| `test_id` | uuid | FK `tests` ON DELETE CASCADE |
| `test_type` | text | `reading` \| `listening` |
| `mode` | text | `prime` (before the attempt) \| `followup` (after it) |
| `trigger` | text | `opt_in` \| `auto` \| `retry` |
| `plan_mode` | text | `full` \| `light` \| `none` |
| `session_block_id`, `load_date` | text, date | set when run from the daily session |
| `unknown_share_at_open` | numeric(4,3) | snapshot, never recomputed |
| `words_shown`, `words_quizzed`, `next_day_review_senses` | int[] | restricted to the test's senses |
| `exposures`, `first_try_correct`, `first_try_total`, `idk_count`, `boosters`, `ladder_exercises` | int | |
| `readiness_score`, `readiness_n`, `readiness_rounds`, `ready` | smallint, smallint, smallint, boolean | |
| `minutes_est`, `active_seconds`, `minutes_source`, `tests_dropped_today` | | `minutes_source` `tests_share` \| `free` |
| `followup`, `produce` | jsonb | follow-up prime and Produce results |
| `status` | text | `open` → `completed` → `consumed` (spent on an attempt) |
| `attempt_id`, `started_at`, `completed_at`, `consumed_at` | | |

Indexes: `(user_id, test_id, started_at DESC)`, `(user_id, language_id, started_at DESC)`.
A completed `prime` row in the last 6 h makes the next submit `prestudied` (server-verified).

### `prestudy_followups`
Next-day review senses. Columns: `id` bigint NN identity (ALWAYS), `user_id` uuid NN (FK `auth.users` ON DELETE CASCADE), `language_id` smallint NN (FK `dim_languages`), `sense_id` integer NN, `session_id` uuid (FK `prestudy_sessions` ON DELETE CASCADE), `reason` text NN, `due_date` date NN, `served_at`, `completed_at` timestamptz, `created_at` timestamptz NN default `now()`; also indexes `idx_prestudy_followups_session_id (session_id)` and `idx_prestudy_sessions_test_id (test_id)` on the sessions table. Written by `record_exercise_attempt` (completion) and `services/prestudy.py`. `UNIQUE (user_id, sense_id, due_date)`; partial index on
`(user_id, language_id, due_date) WHERE completed_at IS NULL`. `reason` ∈ `idk_twice`,
`readiness_missed`, `primed_missed_in_test`, `omitted_in_produce`. Served (one exercise each,
at most 5) inside Maintenance practice sessions; completed by any attempt on that sense.

### Column and function changes
- `test_attempts.prestudied boolean NOT NULL DEFAULT false`; `process_test_submission` gains
  `p_prestudied boolean DEFAULT false` (first attempt: user and test K × 0.5).
- `exercise_attempts.source text` (`NULL` | `prestudy` | `intro`; the CHECK also admits `intro` for new-word-drill sessions): ladder exercises answered in a prime.
- `user_study_plans.prestudy_mode text NOT NULL DEFAULT 'auto'` (`auto` | `ask` | `off`).
- `study_time_ledger.kind` adds `prestudy`; `credit_study_time` caps it at 900 s;
  `get_weekly_study_seconds` returns a `prestudy` key.

## 13. Tables added after 2026-09 (live 2026-11-23; generated from the live catalogue)

Every relation of the live schema that earlier versions of this page lacked. Columns, constraints, indexes, RLS and grants were generated with queries against `pg_catalog` on 2026-11-23 (project `kpfqrjtfxmujzolwsvdq`); writers and readers come from grep of `routes/`, `services/`, `scripts/` and function bodies. Types are Postgres types; "NN" in prose lists means NOT NULL. Together with sections 1 to 12 this covers all 100 live tables; the five older tables that already had a section keep it. `exercises.content` is dropped (content lives in the Storage bucket `exercise-content`, [[decisions/ADR-049-exercise-content-in-storage]]) and is correctly absent from the `exercises` section.

### Dimension and reference tables added after 2026-09

These are lookup/reference tables. Unless stated, writes are done by seed migrations or import scripts with the service key; clients only read.

#### `dim_exercise_types`
Per-exercise-type metadata (family and expected seconds) used for time estimates. Read by `services/study_plan_service.py`, `services/vocabulary_ladder/config.py`, and functions `get_practice_session`, `get_review_ahead_items`, `knowledge_report_summary`, `knowledge_report_words`, `refresh_new_word_minutes`, `refresh_practice_time_estimates` (the last two write the estimates).

| Column | Type | Null | Default |
|---|---|---|---|
| `type_code` | text | NN | |
| `family` | text | NN | CHECK in `form_recognition`,`meaning_recall`,`form_production`,`collocation`,`semantic_discrimination`,`contextual_use`,`fluency` |
| `expected_seconds` | smallint | NN | `45` (CHECK 1..600) |
| `expected_seconds_p50` | numeric(5,1) | | (CHECK null or 0..600) |
| `is_active` | boolean | NN | `true` |
| `context_class` | text | NN | `'context_bearing'` (CHECK `context_free`,`context_bearing`,`not_sense_anchored`) |

PK `type_code`. RLS on with no policy: anon/authenticated hold a SELECT grant but see zero rows; the backend reads it with the service key.

#### `dim_exercise_capabilities`
Which exercise types can be generated per language, by which generator and judge. Read by `services/dimension_service.py`, `services/vocabulary_ladder/config.py`, and the view `v_sense_family_coverage`.

Columns: `language_id` smallint NN, `type_code` text NN, `pos_classes` text[] NN default `'{all}'`, `ladder_level` smallint, `generator` text NN, `requires` text[] NN default `'{}'`, `judge_key` text, `is_enabled` boolean NN default `true`. PK `(language_id, type_code)`; FKs `language_id` -> `dim_languages(id)`, `type_code` -> `dim_exercise_types(type_code)`. RLS on, no policy (same effect as above).

#### `dim_practice_modes`
Practice session modes and their scoring weights. Read by `get_practice_session`. Columns: `mode_id` smallint NN, `name` text NN (UNIQUE), `default_weights` jsonb (CHECK null or an object with keys `alpha`,`beta`,`gamma`,`delta`), `is_active` boolean NN default `true`. PK `mode_id`. RLS on, no policy.

#### `dim_study_plan_templates`
Daily-minutes presets for study plans. Read by `apply_study_plan_template`, `services/study_plan_service.py`, `routes/study_plan.py`.

Columns: `template_id` smallint NN, `language_id` smallint NN, `daily_minutes` smallint NN (CHECK 10..180), `weekly_test_counts` jsonb NN (CHECK object), `practice_total_minutes` smallint NN (CHECK 1..1260), `base_maintenance_share` numeric(3,2) NN default `0.30` (CHECK 0.10..0.60), `practice_minutes_flex_pct` numeric(3,2) NN default `0.25` (CHECK 0..0.50), `is_default` boolean NN default `false`. PK `template_id`; UNIQUE `(language_id, daily_minutes)`; FK `language_id` -> `dim_languages(id)`. RLS policy `dim_study_plan_templates_public_read` (SELECT, public, `true`).

#### `dim_distractor_bands`
Cosine-similarity band used when choosing semantic distractors per language pair. Read by function `semantic_distractors`.

Columns: `word_language_id` smallint NN, `definition_language_id` smallint NN, `cos_min`, `cos_max` real NN (CHECK `cos_min < cos_max`, both within 0..1), `unrelated_median`, `unrelated_p95`, `pct_above_0_35` real, `measured_on` date, `notes` text. PK `(word_language_id, definition_language_id)`; FKs to `dim_languages(id)` on both language columns. RLS policy `dim_distractor_bands_read` (SELECT, roles authenticated and service_role, `true`).

#### `dim_character_components`
Hanzi decomposition (components, radical, strokes) for Chinese. Imported by `scripts/import_character_components.py`; read by `services/vocabulary_ladder/deterministic/lexicon.py`. Columns: `character` text NN (PK), `components` text[] NN default `'{}'`, `radical` text, `stroke_count` smallint, `decomposition` text, `source` text NN, `licence` text NN, `created_at` timestamptz NN default `now()`. GIN index `idx_dim_character_components_components (components)`. RLS policy `dim_character_components_read` (SELECT, public, `true`).

#### Classifier tables (Chinese measure words; Classifier Drill)
Used by `get_classifier_drill_session` / `get_classifier_drill_session_v2`, `max_unlocked_tier`, and the deterministic exercise dictionaries (`services/vocabulary_ladder/deterministic/dictionaries.py`); imported by `scripts/build_classifier_dictionary.py`, `scripts/import_cedict_classifiers.py`. All three: RLS on, no policy, service-role access only (the drill RPCs are SECURITY DEFINER).

- `dim_classifier_distractor_groups`: `id` smallint NN (sequence), `language_id` smallint NN, `label` text NN, `description` text, `created_at` timestamptz NN default `now()`. PK `id`; UNIQUE `(language_id, label)`; FK `language_id` -> `dim_languages(id)`.
- `dim_classifiers`: `id` smallint NN (sequence), `language_id` smallint NN, `hanzi` text NN, `pinyin` text NN, `pinyin_display` text NN, `semantic_label` text NN, `example_nouns` text[] NN default `'{}'`, `frequency_rank` integer NN, `distractor_group_id` smallint NN, `created_at` timestamptz NN default `now()`, `difficulty_tier` smallint NN default `1` (CHECK 1..4). PK `id`; UNIQUE `(language_id, hanzi)`; FKs `distractor_group_id` -> `dim_classifier_distractor_groups(id)`, `language_id` -> `dim_languages(id)`. Indexes `idx_classifiers_group (distractor_group_id)`, `idx_classifiers_tier (language_id, difficulty_tier)`.
- `dim_classifier_noun_pairs`: `id` integer NN (sequence), `language_id` smallint NN, `noun_sense_id` integer, `lemma_text` text NN, `classifier_id` smallint NN, `is_primary` boolean NN default `true`, `frequency_score` numeric NN default `1.0`, `source` text NN default `'curated'`, `created_at` timestamptz NN default `now()`, `example_sentence` text. PK `id`; UNIQUE `(language_id, lemma_text, classifier_id)`; FKs `classifier_id` -> `dim_classifiers(id)` ON DELETE CASCADE, `language_id` -> `dim_languages(id)`, `noun_sense_id` -> `dim_word_senses(id)` ON DELETE SET NULL. Indexes `idx_classifier_noun_pairs_noun_sense (noun_sense_id)`, `idx_classifier_pairs_classifier (classifier_id)`, `idx_classifier_pairs_lemma (language_id, lemma_text)`.

#### Counter tables (Japanese counters; Counter Drill)
Same shape and purpose for Japanese; read by `get_counter_drill_session` and the deterministic dictionaries; imported by `scripts/build_counter_dictionary.py`. All three have RLS with a `SELECT` policy for `public` (`true`) and anon/authenticated SELECT grants.

- `dim_counter_distractor_groups`: `id` smallint NN (sequence), `label` text NN (UNIQUE), `description` text. PK `id`. Policy `dim_counter_groups_read`.
- `dim_counters`: `id` smallint NN (sequence), `language_id` smallint NN default `3`, `counter` text NN, `reading` text NN, `semantic_label` text NN, `example_nouns` text[] NN default `'{}'`, `numeral_readings` jsonb, `frequency_rank` integer, `distractor_group_id` smallint, `difficulty_tier` smallint NN default `1`, `created_at` timestamptz NN default `now()`. PK `id`; UNIQUE `(language_id, counter)`; FK `distractor_group_id` -> `dim_counter_distractor_groups(id)`. Index `idx_counters_lang_group (language_id, distractor_group_id)`. Policy `dim_counters_read`.
- `dim_counter_noun_pairs`: `id` bigint NN (sequence), `language_id` smallint NN default `3`, `lemma_text` text NN, `noun_sense_id` integer, `counter_id` smallint NN, `is_primary` boolean NN default `false`, `frequency_score` real NN default `1.0`, `source` text NN default `'curated'`, `created_at` timestamptz NN default `now()`. PK `id`; UNIQUE `(language_id, lemma_text, counter_id)`; FKs `counter_id` -> `dim_counters(id)` ON DELETE CASCADE, `noun_sense_id` -> `dim_word_senses(id)` ON DELETE SET NULL. Indexes `idx_counter_noun_pairs_counter (counter_id)`, `idx_counter_noun_pairs_lang_lemma (language_id, lemma_text)`, `idx_counter_pairs_sense (noun_sense_id) WHERE noun_sense_id IS NOT NULL`. Policy `dim_counter_noun_pairs_read`.

### Dual-translation tables (grading, error profile, cards, guided repair)

Feature specs: [[features/dual-translation.tech]], [[features/dt-guided-self-repair.tech]] (guided repair), [[decisions/ADR-044-dt-single-call-generative-grader]], [[decisions/ADR-045-dt-guided-self-repair]]. `dt_passage` is documented in section 11 below. All tables here have RLS enabled with **no policy**, and `anon`/`authenticated` hold no grant: they are service-role only (the FastAPI backend with the service key). Every `id` is `bigint GENERATED ALWAYS AS IDENTITY`. Writers are `routes/dual_translation.py` and `services/dual_translation/` unless stated.

#### `dt_submission`
One learner reproduction of a passage. Written by `routes/dual_translation.py` (insert; `skipped_at` update); read by `services/dual_translation/cards.py`, `repair/budget.py`, `scripts/rescore_dt_grades.py`, and the functions `build_daily_session` and `dt_next_inputs`.

| Column | Type | Null | Default |
|---|---|---|---|
| `id` | bigint | NN | identity |
| `user_id` | uuid | NN | |
| `passage_id` | bigint | NN | |
| `l1_language_id` | integer | NN | |
| `reproduction` | text | NN | |
| `modality` | text | NN | `'text'` (CHECK = `text`) |
| `idempotency_key` | text | | |
| `created_at` | timestamptz | | `now()` |
| `correction_style` | text | | CHECK `direct_metalinguistic`,`flag_only` |
| `skipped_at` | timestamptz | | |

FKs: `user_id` -> `users(id)`, `passage_id` -> `dt_passage(id)`, `l1_language_id` -> `dim_languages(id)`. Indexes: `idx_dt_submission_passage (passage_id)`, `idx_dt_submission_user (user_id)`, `idx_dt_submission_user_idempotency (user_id, idempotency_key) WHERE idempotency_key IS NOT NULL` (not unique).

#### `dt_grade`
The grade of a submission (at most one per submission). Written by `routes/dual_translation.py` and `scripts/rescore_dt_grades.py`; read by `repair/store.py`, `repair/budget.py`, `build_daily_session`, `dt_next_inputs`.

Columns: `id` bigint NN identity, `submission_id` bigint NN, `scores` jsonb NN, `overall_band` smallint NN (CHECK 1..4), `diff` jsonb NN, `grader_trace` jsonb NN, `created_at` timestamptz default `now()`. UNIQUE `submission_id`; FK `submission_id` -> `dt_submission(id)` ON DELETE CASCADE.

#### `dt_grading_call`
One row per LLM grading call (primary, fallback or shadow) with cost, latency and parse outcome. Inserted by `routes/dual_translation.py`; created by `migrations/dt_grading_assets.sql`. No application reader (analysis scripts only).

| Column | Type | Null | Default |
|---|---|---|---|
| `id` | bigint | NN | identity |
| `submission_id` | bigint | NN | |
| `flow` | text | NN | |
| `role` | text | NN | CHECK `primary`,`fallback`,`shadow` |
| `model_slug` | text | NN | |
| `provider` | text | | |
| `prompt_version` | text | NN | |
| `prompt_variant` | text | | |
| `severity_rule` | text | | CHECK null or `model`,`prior` |
| `l2_code` | text | | |
| `status` | text | NN | CHECK `ok`,`call_failed`,`malformed_json`,`malformed_shape` |
| `error` | text | | CHECK length <= 300 |
| `finish_reason` | text | | |
| `tokens_in`, `tokens_out`, `cached_tokens`, `reasoning_tokens`, `latency_ms` | integer | | |
| `cost_usd` | numeric(12,8) | | |
| `taxonomy_version`, `rubric_version` | smallint | | |
| `response`, `dropped`, `result` | jsonb | | |
| `errors_raw`, `errors_kept` | smallint | | |
| `raw_response` | text | | CHECK length <= 4000 |
| `raw_truncated` | boolean | NN | `false` |
| `created_at` | timestamptz | NN | `now()` |

FK `submission_id` -> `dt_submission(id)` ON DELETE CASCADE. Indexes `idx_dt_grading_call_created (created_at)`, `idx_dt_grading_call_submission (submission_id)`.

#### `dt_error_instance`
One detected error in a submission. Inserted by `routes/dual_translation.py` (also deleted there); patched by `scripts/dt_backfill_error_spans.py`; read by `repair/store.py`, `cards.py`, `explainer.py`, `scripts/dt_nightly_synthesis.py`.

Columns (NN = not null): `id` bigint NN identity; `submission_id` bigint NN; `span_reproduction` jsonb NN; `span_reference` jsonb NN; `category` text NN (CHECK `grammatical`,`lexical`,`pragmatic_expressional`); `subtype` text NN; `source` text NN (CHECK `interlingual`,`intralingual`); `severity` text NN (CHECK `minor`,`major`,`critical`); `learner_form` text NN; `corrected_form` text NN; `explanation` text NN; `confidence` real NN; `is_mistake` boolean default `false`; `created_at` timestamptz default `now()`; `taxonomy_version` smallint; `explanation_variant` text (CHECK: only when `subtype = 'word_choice'`, one of `wrong_word`,`wrong_sense`,`false_synonym`); `remap_flag` text (CHECK `split_needs_review`); `sentence_index` smallint (CHECK >= 0); `model_severity` text (CHECK `minor`,`major`,`critical`); `model_note` text (CHECK length <= 240); `span_source` text (CHECK `exact`,`normalised`,`fuzzy`,`diff_hunk`,`sentence`); `correction_source` text (CHECK `model_quote`,`aligned_diff`,`reference_sentence`); `confidence_label` text (CHECK `high`,`medium`,`low`); `explanation_source` text (CHECK `model`,`template`,`explainer`). FK `submission_id` -> `dt_submission(id)` (no cascade). Index `idx_dt_error_instance_submission (submission_id)`.

#### `dt_error_profile_entry`
Rolling per-learner error profile: one row per (learner, L1, L2, subtype). Upserted by `scripts/dt_nightly_synthesis.py` and `services/dual_translation/cards.py`; read by `routes/dual_translation.py`.

Columns: `id` bigint NN identity, `user_id` uuid NN, `l1_language_id` integer NN, `l2_language_id` integer NN, `subtype` text NN, `count` integer NN, `severity_rank` real NN, `trend` jsonb, `remediation_status` text NN (CHECK `watching`,`queued`,`drilling`,`resolved`), `updated_at` timestamptz default `now()`, `taxonomy_version` smallint, `remap_flag` text (CHECK `split_needs_review`,`merged`). UNIQUE `(user_id, l1_language_id, l2_language_id, subtype)`; FKs `user_id` -> `users(id)`, both language ids -> `dim_languages(id)`. Indexes `idx_dt_error_profile_entry_severity_rank (user_id, severity_rank DESC)`, `idx_dt_error_profile_entry_status (remediation_status) WHERE remediation_status IN ('queued','drilling')`, `idx_dt_error_profile_entry_user (user_id)`.

#### `dt_card` and `dt_card_review`
Spaced-repetition drill cards built from profile entries, and their review log. `dt_card` is written by `services/dual_translation/cards.py` and `routes/dual_translation.py`; `dt_card_review` is inserted by `routes/dual_translation.py` on review submit. Defined in `migrations/dt_cards.sql`.

- `dt_card`: `id` bigint NN identity, `user_id` uuid NN, `profile_entry_id` bigint, `origin_error_id` bigint, `card_type` text NN (CHECK `cloze`,`isolate_retranslate`), `subtype` text NN, `prompt_payload` jsonb NN, `stability` real, `difficulty` real, `due_date` date, `state` text (CHECK `new`,`learning`,`review`,`relearning`), `reps` integer, `lapses` integer, `last_review` timestamptz, `created_at` timestamptz default `now()`, `updated_at` timestamptz default `now()`, `taxonomy_version` smallint. FKs `origin_error_id` -> `dt_error_instance(id)`, `profile_entry_id` -> `dt_error_profile_entry(id)`, `user_id` -> `users(id)` (none cascade). Indexes `idx_dt_card_due (user_id, due_date) WHERE due_date IS NOT NULL`, `idx_dt_card_origin_error (origin_error_id)`, `idx_dt_card_profile_entry (profile_entry_id)`, `idx_dt_card_subtype (user_id, subtype)`, `idx_dt_card_user (user_id)`.
- `dt_card_review`: `id` bigint NN identity, `card_id` bigint NN, `rating` smallint NN (CHECK 1..4), `was_correct` boolean, `reviewed_at` timestamptz default `now()`. FK `card_id` -> `dt_card(id)`. Indexes `idx_dt_card_review_card (card_id)`, `idx_dt_card_review_reviewed_at (reviewed_at)`.

#### `dt_rubric_version` and `dt_taxonomy_version`
Versioned grading rubric and error taxonomy; at most one active row each (partial unique index on `is_active`). Seeded by migrations (`dt_rubric_v*_seed.sql`, `dt_taxonomy_*_seed.sql`, `dt_taxonomy_v6_activate.sql`) and `scripts/build_dt_taxonomy_v6.py`; read by `services/dual_translation/prompts.py`, `scoring.py`, `grader_cascade.py`, `single_call_prompts.py`. See [[decisions/ADR-031-dt-taxonomy-v6-merge]].

- `dt_rubric_version`: `id` bigint NN identity, `version` integer NN (UNIQUE), `is_active` boolean NN default `false`, `config` jsonb NN, `description` text, `created_at` timestamptz default `now()`. Unique partial index `idx_dt_rubric_version_one_active (is_active) WHERE is_active`.
- `dt_taxonomy_version`: `id` bigint NN identity, `version` integer NN (UNIQUE), `is_active` boolean NN default `false`, `taxonomy` jsonb NN, `description` text, `created_at` timestamptz default `now()`. Unique partial index `idx_dt_taxonomy_version_one_active (is_active) WHERE is_active`.

#### `dt_repair_session`, `dt_repair_item`, `dt_repair_event` (guided self-repair)
Defined in `migrations/dt_guided_self_repair.sql`; written only by `services/dual_translation/repair/store.py` (driven by `service.py`, `recheck.py`, `hooks.py`, `budget.py`). A repair session belongs to one submission, each flagged error becomes an item, each learner action or hint is an append-only event.

`dt_repair_session`: `id` bigint NN identity, `submission_id` bigint NN (UNIQUE), `user_id` uuid NN, `l2_language_id` integer NN, `l1_language_id` integer NN, `status` text NN (CHECK `open`,`finished`,`bypassed`,`abandoned`), `n_sentences`, `n_flagged`, `n_steps` smallint NN (each CHECK >= 0), `grade_tier` text, `prompt_version` text, `hint_version` text NN, `settings` jsonb NN, `closed_early` boolean, `total_ms` integer, `created_at` timestamptz NN default `now()`, `finished_at` timestamptz. FKs: `submission_id` -> `dt_submission(id)` ON DELETE CASCADE, `user_id` -> `users(id)` ON DELETE CASCADE, both languages -> `dim_languages(id)`. Index `idx_dt_repair_session_user_status (user_id, status)`.

`dt_repair_item`: `id` bigint NN identity; `session_id` bigint NN; `user_id` uuid NN; `submission_id` bigint NN; `error_id` bigint NN; `l2_language_id` integer NN; `sentence_index` smallint NN (>= 0); `step_order` smallint (null or >= 0); `step_kind` text NN (CHECK `repair`,`unsure`,`direct`); `ladder` text NN (CHECK `full`,`short`,`none`); `location_available` boolean NN; `subtype` text NN; `severity` text NN (CHECK `minor`,`major`,`critical`); `confidence` real; `repro_start`, `repro_end`, `ref_start`, `ref_end` integer NN (CHECK each end >= its start); `span_start`, `span_end` smallint (both null or both set); `sitting` smallint NN default `0`; `sitting_open` boolean NN default `false`; `hint_level` smallint NN default `0` (CHECK 0..4); `checks_used`, `calls_used` smallint NN default `0`; `last_text` text (CHECK length <= 400); `active` jsonb; `opened_at` timestamptz; `check_lock_until` timestamptz; `outcome` text (CHECK `self_repaired`,`repaired_alternative`,`answer_shown`,`shown_directly`,`disputed`,`skipped`,`unsure_revised`,`unsure_dismissed`,`unsure_skipped`); `answer_reason` text (CHECK `asked`,`auto_cap`,`grader_failed`,`budget`,`direct`); `max_hint_level` smallint (null or 0..4); `n_checks` smallint NN default `0`; `time_ms`, `first_edit_ms` integer; `closed_at` timestamptz; `queue_status` text NN default `'none'` (CHECK `none`,`due`,`resolved`,`retired`,`expired`,`disputed`); `queued_at` timestamptz; `due_on` date; `not_before` timestamptz; `expires_at` timestamptz; `failed_sittings`, `hinted_sittings` smallint NN default `0`; `last_practiced_at` timestamptz; `created_at` timestamptz NN default `now()`. FKs (all ON DELETE CASCADE): `error_id` -> `dt_error_instance(id)`, `session_id` -> `dt_repair_session(id)`, `submission_id` -> `dt_submission(id)`, `user_id` -> `users(id)`; `l2_language_id` -> `dim_languages(id)`. Indexes `idx_dt_repair_item_due (user_id, l2_language_id, due_on) WHERE queue_status = 'due'`, `idx_dt_repair_item_error (error_id)`, `idx_dt_repair_item_session (session_id)`.

`dt_repair_event`: `id` bigint NN identity; `item_id` bigint NN; `user_id` uuid NN; `surface` text NN (CHECK `repair_pass`,`daily_practice`); `sitting` smallint NN; `kind` text NN (CHECK `step_opened`,`hint_shown`,`revision_checked`,`answer_shown`,`disputed`,`kept`,`skipped`,`episode_closed`); `hint_level` smallint NN (0..4); `since_prev_ms` integer; `hint_source` text (CHECK `grader_span`,`template`,`taxonomy_gloss`,`type_neutral`); `hint_template_id` text; `client_check_id` uuid; `text` text (CHECK length <= 400); `result` text (CHECK `fixed`,`no_issue_found`,`still_flagged`,`error`); `result_detail` jsonb; `latency_ms`, `tokens_in`, `tokens_out` integer; `cost_usd` numeric(12,8); `model_slug` text; `prompt_version` text; `created_at` timestamptz NN default `now()`. FK `item_id` -> `dt_repair_item(id)` ON DELETE CASCADE (`user_id` has no FK). Indexes `idx_dt_repair_event_item (item_id)`, `idx_dt_repair_event_user_checks (user_id, created_at) WHERE kind = 'revision_checked'`, unique `uq_dt_repair_event_check (item_id, client_check_id) WHERE client_check_id IS NOT NULL` (idempotent re-check).

### Calibration placement tables

Introduced by `migrations/calibration_sessions_and_ability.sql` and successors (`task769`..`task773b`, `calibration_pronunciation_mode.sql`, `calibration_distractor_cache_packed.sql`, `calibration_bkt_evidence.sql`). Feature spec: [[features/calibration.tech]]. Placement-mode objects (`calibration_placement_*`, `knowledge_*`, `calibration_zh_*`) are defined in `migrations/calibration_placement.sql`, `calibration_placement_rpcs.sql`, `calibration_zh_tones.sql`, `knowledge_report_foundation.sql` and related files, applied live 2026-11-22 (see [[log]]). All tables below have RLS enabled. Convention in this section: "service-role only" means RLS on, no policy, no `anon`/`authenticated` grant, so only the backend (service key) and SECURITY DEFINER functions reach it.

#### `calibration_sessions`
One row per placement run. Written by `calibration_build_items`, `calibration_record_answer`, `calibration_placement_*` RPCs (see [[database/rpcs.tech]]); read by `services/calibration_service.py` and `knowledge_*` functions.

| Column | Type | Null | Default |
|---|---|---|---|
| `id` | uuid | NN | `gen_random_uuid()` |
| `user_id` | uuid | NN | |
| `word_language_id` | smallint | NN | |
| `definition_language_id` | smallint | NN | |
| `started_at` | timestamptz | NN | `now()` |
| `ended_at` | timestamptz | | |
| `items_served`, `items_answered`, `items_correct` | integer | NN | `0` |
| `mode` | text | NN | `'definition'` (CHECK in `definition`,`pronunciation`,`placement`) |
| `bkt_applied_at` | timestamptz | | |
| `stop_reason` | text | | CHECK null or `precision`,`cap`,`time`,`exhausted`,`learner`,`abandoned` |
| `result` | jsonb | | |

PK `id`. FKs: `word_language_id`, `definition_language_id` -> `dim_languages(id)`. Index `idx_calibration_sessions_user (user_id, started_at DESC)`. RLS: policy `calibration_sessions_own` (SELECT, authenticated, `auth.uid() = user_id`); grants authenticated SELECT only.

#### `calibration_responses`
One row per served item (meaning, reading, or sound-pair), answered or not. Written by `calibration_placement_insert_item`, `calibration_build_items`, `calibration_record_answer`, `calibration_placement_answer`; deleted by `calibration_discard_unanswered`.

| Column | Type | Null | Default |
|---|---|---|---|
| `id` | bigint | NN | `nextval('calibration_responses_id_seq')` |
| `session_id` | uuid | NN | |
| `user_id` | uuid | NN | |
| `anchor_sense_id` | integer | NN | |
| `anchor_vocab_id` | integer | NN | |
| `anchor_zipf` | real | | |
| `zipf_band` | smallint | | |
| `chosen_sense_id` | integer | | |
| `is_correct` | boolean | | |
| `latency_ms` | integer | | |
| `served_at` | timestamptz | NN | `now()` |
| `answered_at` | timestamptz | | |
| `item_kind` | text | | CHECK null or `meaning`,`reading`,`sound_pair` |
| `probe_kind` | text | | CHECK null or `recheck`,`reading_after_miss`,`forced_guess`,`sound_pair` |
| `instrument` | text | | CHECK null or `meaning_bare_v1`,`reading_v1`,`reading_tone_v1` |
| `pair_response_id` | bigint | | |
| `option_sense_ids` | integer[] | | |
| `key_position`, `chosen_position` | smallint | | |
| `option_roles`, `option_texts` | text[] | | |
| `reading_exempt` | boolean | | |

PK `id`. FKs: `anchor_sense_id` -> `dim_word_senses(id)`; `pair_response_id` -> `calibration_responses(id)` ON DELETE CASCADE; `session_id` -> `calibration_sessions(id)` ON DELETE CASCADE. Indexes: `idx_calibration_responses_anchor (anchor_sense_id)`, `idx_calibration_responses_pair (pair_response_id) WHERE pair_response_id IS NOT NULL`, `idx_calibration_responses_session (session_id, served_at)`, `idx_calibration_responses_user_vocab_answered (user_id, anchor_vocab_id) WHERE answered_at IS NOT NULL`. RLS: policy `calibration_responses_own` (SELECT, authenticated, own rows). `authenticated` holds no table grant, so the policy is inert for direct client reads: in practice service-role only (it carries the answer key positions).

#### `calibration_response_options`
The options shown for a response (key and distractors) with similarity and frequency, plus which one was chosen. Written by `calibration_build_items`, `calibration_record_answer`; deleted by `calibration_discard_unanswered`. Service-role only (policy-less; carries the answer key, see `migrations/security_calibration_answer_keys.sql`).

| Column | Type | Null | Default |
|---|---|---|---|
| `response_id` | bigint | NN | |
| `sense_id` | integer | NN | |
| `vocab_id` | integer | NN | |
| `is_key` | boolean | NN | |
| `position` | smallint | NN | |
| `similarity`, `frequency` | real | | |
| `freq_tier` | smallint | | |
| `was_chosen` | boolean | NN | `false` |

PK `(response_id, sense_id)`. FK `response_id` -> `calibration_responses(id)` ON DELETE CASCADE. Index `idx_calibration_options_chosen_distractors (sense_id) WHERE was_chosen AND NOT is_key`.

#### `user_calibration_state`
Per learner, per language, per mode summary of placement ability (Zipf scale). Written by `services/calibration_service.py` via PostgREST after a session closes; read by `prestudy_plan_inputs`, `selection_vocab_ability`, `apply_calibration_to_skill_ratings`.

| Column | Type | Null | Default |
|---|---|---|---|
| `user_id` | uuid | NN | |
| `language_id` | smallint | NN | |
| `ability_zipf`, `ability_se` | numeric | | (CHECK `ability_se` null or >= 0) |
| `band_accuracies` | jsonb | NN | `'[]'` |
| `items_answered`, `sessions_pooled` | integer | NN | `0` |
| `mode` | text | NN | `'definition'` (CHECK `definition`,`pronunciation`) |
| `last_run_at` | timestamptz | NN | `now()` |

PK `(user_id, language_id, mode)`. FK `language_id` -> `dim_languages(id)`. Index `idx_user_calibration_state_user (user_id, language_id)`. RLS policy `user_calibration_state_own` (SELECT, authenticated, own rows); authenticated has SELECT only.

#### `calibration_anchor_pool`
Materialised pool of candidate anchor senses by language pair and Zipf band. Refreshed by `calibration_refresh_anchor_pool()`; read by `calibration_next_anchors`, `calibration_placement_candidates`, `knowledge_frame_bands`. Service-role only.

Columns (all NN unless noted): `word_language_id` smallint, `definition_language_id` smallint, `sense_id` integer, `vocab_id` integer, `lemma` text, `definition` text (null), `pronunciation` text (null), `zipf` real, `zipf_band` smallint, `has_embedding` boolean, `has_pronunciation` boolean. PK `(word_language_id, definition_language_id, sense_id)`. Partial indexes `idx_cal_anchor_pool_definition` and `idx_cal_anchor_pool_pronunciation`, both `btree (word_language_id, definition_language_id, zipf_band)` with `WHERE has_embedding` / `WHERE has_pronunciation`.

#### `calibration_anchor_blocklist`
Senses excluded from anchoring and from distractor use (quarantined or otherwise unsafe). Written by `services/vocabulary/sense_quarantine.py` and scripts (`scripts/retire_zh_fake_words.py`, `scripts/screen_sense_definition_mismatch.py`); read by `is_sense_quarantined`, `calibration_*` functions.

Columns: `sense_id` integer NN, `reason` text NN, `added_at` timestamptz NN default `now()`. PK `sense_id`; FK -> `dim_word_senses(id)` ON DELETE CASCADE. RLS policy `calibration_blocklist_read` (SELECT, authenticated, `true`); anon has a SELECT grant but no policy, so reads nothing.

#### `calibration_distractor_cache`
Pre-computed distractor sets per anchor and mode. Written by `calibration_fill_distractor_cache` / `calibration_cache_distractors_chunk` (driven by `scripts/build_calibration_distractor_cache.py`); read by `calibration_cached_options`. Service-role only.

Columns: `anchor_sense_id` integer NN, `mode` text NN (CHECK `definition`,`pronunciation`), `sense_ids` integer[] NN (CHECK cardinality > 0), `similarities` real[] (CHECK null or same cardinality as `sense_ids`), `freq_tiers` smallint[] NN (CHECK same cardinality as `sense_ids`), `built_at` timestamptz NN default `now()`. PK `(anchor_sense_id, mode)`.

#### `calibration_distractor_cache_misses`
Anchors for which the cache build found too few distractors, so they are not retried every run. Written by `calibration_cache_distractors_chunk`; cleared by `calibration_clear_distractor_cache_misses`. Service-role only.

Columns: `mode` text NN (CHECK `definition`,`pronunciation`), `anchor_sense_id` integer NN, `rows_found` smallint NN, `attempted_at` timestamptz NN default `now()`. PK `(mode, anchor_sense_id)`.

#### `calibration_zh_char_readings` and `calibration_zh_tone_inventory`
Chinese tone-variant support for placement reading items. Both are service-role only; `calibration_refresh_zh_tone_inventory()` rebuilds them and `calibration_zh_tone_variants` reads them. Defined in `migrations/calibration_zh_tones.sql` ; read by `services/placement_tones.py` and `scripts/verify_zh_tone_variants.py`.

- `calibration_zh_char_readings`: `hanzi` text NN, `base` text NN, `tone` smallint NN (CHECK 1..5). PK `(hanzi, base, tone)`.
- `calibration_zh_tone_inventory`: `base` text NN, `tones` smallint[] NN (CHECK contained in `{1,2,3,4}`), `built_at` timestamptz NN default `now()`. PK `base`.

### Generation, queue and operations tables

#### `generation_queue`
Work queue of senses that need (re)generation of exercise assets, keyed by reason. Written by `services/vocabulary_ladder/queue_drain.py` (and `services/vocabulary/sense_quarantine.py`, `services/practice/new_word_admission.py`, `routes/word_list_import.py`, which enqueue); defined in `migrations/generation_queue.sql`. Service-role only (RLS on, no policy, no client grant).

| Column | Type | Null | Default |
|---|---|---|---|
| `id` | bigint | NN | identity (ALWAYS) |
| `sense_id` | integer | NN | |
| `language_id` | smallint | NN | |
| `reason` | text | NN | |
| `status` | text | NN | `'pending'` |
| `detail` | jsonb | | |
| `requested_at` | timestamptz | NN | `now()` |
| `completed_at` | timestamptz | | |

UNIQUE `(sense_id, reason)`; FK `sense_id` -> `dim_word_senses(id)`; index `idx_generation_queue_status_requested_at (status, requested_at)`.

#### `generation_review_queue`
Human review queue for generated artifacts the judges flagged. Written by `services/test_generation/orchestrator.py` (through `database_client.py`); migration `migrations/phase14_generation_review_queue.sql`. Service-role only.

Columns: `id` uuid NN default `gen_random_uuid()`, `artifact_kind` text NN (CHECK `test_question`,`exercise`), `artifact_id` uuid NN, `flag_reasons` text[] NN default `'{}'`, `judge_scores` jsonb, `status` text NN default `'pending'` (CHECK `pending`,`approved`,`rejected`,`edited`), `reviewer_id` uuid, `reviewed_at` timestamptz, `created_at` timestamptz NN default `now()`. PK `id`. Indexes `idx_review_queue_artifact_pending (artifact_id) WHERE status = 'pending'`, `idx_review_queue_status_kind_created (status, artifact_kind, created_at DESC)`.

#### `generation_stage_timings`
Per-stage duration log for generation pipelines. Written by `services/timing.py` (callers: `orchestrator.py`, `asset_pipeline.py`); read by `scripts/generation_timing_report.py`; pruned by `purge_old_log_rows`. Service-role only.

Columns: `id` uuid NN default `gen_random_uuid()`, `pipeline` text NN, `stage_name` text NN, `language_code` text, `artifact_id` uuid, `run_id` uuid, `duration_ms` integer NN, `created_at` timestamptz NN default `now()`. PK `id`. Indexes `idx_gen_stage_timings_language (language_code) WHERE language_code IS NOT NULL`, `idx_gen_stage_timings_pipeline_stage_created (pipeline, stage_name, created_at DESC)`, `idx_gen_stage_timings_run (run_id) WHERE run_id IS NOT NULL`.

#### `question_type_distributions_by_tier`
The five question types of a generated test, per complexity tier (replaced the per-difficulty table in `migrations/task740_collapse_difficulty_to_tier_schema.sql`). Read by `services/test_generation/question_mix.py`, `orchestrator.py`, `database_client.py`. Service-role only.

Columns: `id` integer NN (identity BY DEFAULT), `tier_id` smallint NN (UNIQUE), `question_type_1`..`question_type_5` varchar NN, `created_at` / `updated_at` timestamptz default `now()`. PK `id`. FKs: each `question_type_N` -> `dim_question_types(type_code)`; `tier_id` -> `dim_complexity_tiers(id)`.

#### `selection_tuning`
Key/value knobs for test selection (`vocab_weight`, `elo_weight`, `unknown_tolerance`, `combine_mode`). Read by `get_recommended_tests` and `recommended_tests_ranked`; scripts `scripts/measure_selection_quality.py`, `scripts/simulate_preteach_variants.py`. Migrations `task744_selection_tuning_table.sql`, `task780_selection_combine_mode.sql`. Service-role only.

Columns: `key` text NN (PK), `value` numeric, `updated_at` timestamptz NN default `now()`, `value_text` text. CHECKs: `combine_mode` requires `value IS NULL` and `value_text` in (`sum`,`product`), every other key requires numeric `value` and null `value_text`; `unknown_tolerance` > 0; `vocab_weight` and `elo_weight` >= 0.

#### `script_conversion_overrides`
Simplified-to-Traditional Chinese override pairs for the script converter. Read by `services/vocabulary_ladder/script_converter.py`; written by `scripts/backfill_hant_mirrors.py`; migration `traditional_chinese_groundwork.sql`. Columns: `simplified` text NN (PK), `traditional` text NN, `note` text, `created_at` timestamptz NN default `now()`. Service-role only.

#### `tests_tier_backup_20260926` and `tests_tier_backup_20260927_v1`
One-off snapshots taken before the JEV tier re-assignment (`migrations/task819_jev_tier_assignment.sql`, `scripts/retier_tests_with_jev.py`) and the tier calibration (`migrations/task821_tier_calibration.sql`). Not read or written by the running application. Both are RLS on with no policy; `anon` and `authenticated` hold SELECT grants but see no rows. Candidates for removal (open question).

- `tests_tier_backup_20260926`: `test_id` uuid NN (PK), `target_age_tier` smallint, `difficulty` integer, `seeded_elo` integer, `is_active` boolean, `backed_up_at` timestamptz NN default `now()`.
- `tests_tier_backup_20260927_v1`: `test_id` uuid NN (PK), `target_age_tier` smallint, `difficulty` integer, `age_tier_calibration` text, `backed_up_at` timestamptz NN default `now()`.

### Learner state tables added after 2026-09

#### `study_time_ledger`
Idempotent ledger of study seconds credited per week, per learner and language, used by the weekly plan. Written only by the function `credit_study_time` (called by the live function `record_exercise_attempt` and by `services/study_time.py` (wrapper used by `services/attempts.py`, `services/intro_drill.py`); one-off fill in `migrations/backfill_study_time_ledger.sql`); read by `get_weekly_study_seconds`. Migration `study_time_ledger.sql`. Service-role only.

| Column | Type | Null | Default |
|---|---|---|---|
| `id` | bigint | NN | identity (ALWAYS) |
| `user_id` | uuid | NN | |
| `language_id` | smallint | NN | |
| `week_start_date` | date | NN | |
| `kind` | text | NN | CHECK `test`,`practice`,`flashcard`,`dual_translation`,`drill`,`prestudy` |
| `seconds` | integer | NN | CHECK 1..1200 |
| `source_table` | text | NN | |
| `source_id` | text | NN | |
| `credited_at` | timestamptz | NN | `now()` |

UNIQUE `(kind, source_table, source_id)` (the idempotency key); FKs `language_id` -> `dim_languages(id)`, `user_id` -> `auth.users(id)` ON DELETE CASCADE (note: `auth.users`, not `public.users`). Index `study_time_ledger_week_idx (user_id, language_id, week_start_date)`.

#### `user_classifier_mastery`
Per-learner mastery of each Chinese classifier in Classifier Drill. Written by function `update_classifier_mastery`; read by `get_classifier_drill_session_v2` and `max_unlocked_tier`. Migration `task998_classifier_drill_levels.sql`. Service-role only.

Columns: `user_id` uuid NN, `classifier_id` smallint NN, `attempts` integer NN default `0`, `correct` integer NN default `0`, `ewma_accuracy` numeric NN default `0.0`, `current_level` smallint NN default `1` (CHECK 1..4), `last_wrong_streak` smallint NN default `0`, `promoted_at` timestamptz, `last_attempted_at` timestamptz, `created_at`, `updated_at` timestamptz NN default `now()`, `level_attempts` integer. PK `(user_id, classifier_id)`; FKs `classifier_id` -> `dim_classifiers(id)` and `user_id` -> `users(id)`, both ON DELETE CASCADE. Indexes `idx_user_classifier_mastery_classifier (classifier_id)`, `idx_user_classifier_mastery_level (user_id, current_level)`, `idx_user_classifier_mastery_user (user_id)`.

#### `user_skill_rating_adjustments`
Append-only audit of ELO changes made from placement/calibration (seed, correction, or skipped). Written by `apply_calibration_to_skill_ratings`; the trigger function `usra_refuse_update` blocks UPDATEs. Migrations `task746_user_skill_rating_adjustments.sql`, `task747_apply_calibration_to_skill_ratings.sql`.

Columns: `id` bigint NN (sequence default), `user_id` uuid NN, `language_id` smallint NN, `test_type_id` smallint NN, `source` text NN (CHECK `calibration_seed`,`calibration_correct`,`skipped`), `elo_before` integer, `elo_after` integer, `ability_zipf` numeric, `ability_se` numeric, `seed_elo_computed` integer, `tests_taken_at_write` integer, `reason` text NN, `created_at` timestamptz NN default `now()`. CHECKs: `skipped` rows must have `elo_before` equal to `elo_after` (or both null); any non-`skipped` row needs `elo_after`. FKs `language_id` -> `dim_languages(id)`, `test_type_id` -> `dim_test_types(id)`, `user_id` -> `users(id)` ON DELETE CASCADE. Index `idx_usra_user_lang_type_created (user_id, language_id, test_type_id, created_at DESC)`. RLS policy `usra_select_own` (SELECT, authenticated, own rows); authenticated has SELECT only.

#### `user_test_intros_seen`
Which test-type intro cards a learner has dismissed. Written/read by `services/test_intro_service.py`; migration `add_test_intro_seen.sql`. Columns: `user_id` uuid NN, `test_type` text NN, `seen_at` timestamptz NN default `now()`. PK `(user_id, test_type)`; FK `user_id` -> `users(id)` ON DELETE CASCADE. RLS on with no policy (`anon`/`authenticated` have a SELECT grant but see no rows; the service reads with the service key).

#### `trusted_devices`
Remember-this-device tokens for sign-in. Written and read by `services/device_service.py`; migration `trusted_devices.sql`.

Columns: `id` uuid NN default `gen_random_uuid()`, `device_id` uuid NN, `user_id` uuid NN, `token_hash` bytea NN, `generation` integer NN default `1`, `device_label` text, `user_agent` text, `ip_hash` bytea, `created_at` timestamptz NN default `now()`, `last_used_at` timestamptz NN default `now()`, `expires_at` timestamptz NN, `revoked_at` timestamptz, `revoked_reason` text. PK `id`; FK `user_id` -> `users(id)` ON DELETE CASCADE. Indexes `trusted_devices_device_id_idx (device_id)`, unique `trusted_devices_token_hash_idx (token_hash)`, `trusted_devices_user_active_idx (user_id) WHERE revoked_at IS NULL`. RLS policies (all for role `public`, but each tests `auth.role()`): `rls_select` allows service_role or `is_admin(auth.uid())`; `rls_insert` (INSERT, WITH CHECK), `rls_update` and `rls_delete` allow service_role only. `anon` and `authenticated` hold SELECT grants only.

#### `user_study_plans`
One study plan per learner per language (daily minutes, weekday shape, excluded modules, new-words-per-day, budget scope, prestudy mode). Written by `services/study_plan_settings.py` (direct updates and the `apply_study_plan_template` RPC) and `services/study_plan_service.py`; read by `services/day_boundary.py`, `services/study_plan_settings.py`, `services/test_service.py` and the functions `build_daily_session`, `plan_local_date`, `plan_local_day_start`, `review_governor_state`.

| Column | Type | Null | Default |
|---|---|---|---|
| `user_id` | uuid | NN | |
| `language_id` | smallint | NN | |
| `template_id` | smallint | NN | |
| `daily_minutes` | smallint | NN | CHECK 10..180 |
| `weekday_shape` | jsonb | NN | `'[1,1,1,1,1,1,1]'` (CHECK array of length 7) |
| `skill_weight_overrides` | jsonb | NN | `'{}'` (CHECK object) |
| `goal_id` | smallint | | |
| `timezone` | text | NN | `'UTC'` |
| `created_at`, `updated_at` | timestamptz | NN | `now()` |
| `excluded_modules` | text[] | NN | `'{}'` (CHECK subset of `reading`,`listening`,`dictation`,`pinyin`,`classifier_drill`,`pitch_accent`,`flashcards`,`dual_translation`,`practice`) |
| `new_words_per_day` | smallint | NN | `10` (CHECK 0..50) |
| `budget_scope` | text | NN | `'tests_and_review'` (CHECK `tests_and_review`,`tests_only`) |
| `prestudy_mode` | text | NN | `'auto'` (CHECK `auto`,`ask`,`off`) |

PK `(user_id, language_id)`. FKs: `language_id` -> `dim_languages(id)`, `template_id` -> `dim_study_plan_templates(template_id)`, `user_id` -> `auth.users(id)` ON DELETE CASCADE. RLS policy `user_study_plans_self_select` (SELECT, public role, `user_id = auth.uid()`); authenticated has SELECT only.

#### `weekly_plan_states`
The week's plan target and progress per learner and language (Monday-anchored). Written by functions `compute_weekly_plan_persist`, `record_session_progress`, `apply_attempt_timing_and_progress`; read by `build_daily_session`, `compute_weekly_plan_load_signals`, `review_governor_state`, `routes/study_plan.py`, `routes/practice.py`, `routes/drills.py`, `services/study_plan_service.py`, `services/study_session/session.py`.

| Column | Type | Null | Default |
|---|---|---|---|
| `user_id` | uuid | NN | |
| `language_id` | smallint | NN | |
| `week_start_date` | date | NN | CHECK a Monday |
| `target_counts` | jsonb | NN | CHECK object |
| `skill_values` | jsonb | NN | `'{}'` (CHECK object) |
| `completed_counts` | jsonb | NN | `'{}'` (CHECK object) |
| `practice_target_minutes` | smallint | NN | CHECK >= 0 |
| `practice_completed_maint_min`, `practice_completed_acq_min` | smallint | NN | `0` (CHECK >= 0) |
| `maintenance_share`, `acquisition_share` | numeric(3,2) | NN | each 0..1, sum within 0.011 of 1.0 |
| `total_weekly_minutes` | smallint | NN | |
| `session_progress_log` | jsonb | NN | `'{}'` (CHECK object) |
| `computed_at` | timestamptz | NN | `now()` |
| `practice_completed_maint_sec`, `practice_completed_acq_sec` | integer | NN | `0` (CHECK >= 0) |
| `budget_scope` | text | NN | `'tests_and_review'` (CHECK `tests_and_review`,`tests_only`) |
| `review_target_minutes`, `new_words_target`, `new_words_completed`, `acq_target_minutes`, `tail_completed_min`, `tail_new_words_completed` | integer | NN | `0` (one CHECK: all >= 0) |

PK `(user_id, language_id, week_start_date)`. FKs: `language_id` -> `dim_languages(id)`, `user_id` -> `auth.users(id)` ON DELETE CASCADE. Indexes `idx_weekly_plan_states_user_lang (user_id, language_id, week_start_date DESC)`, `idx_weekly_plan_states_week (week_start_date)`. RLS policy `weekly_plan_states_self_select` (SELECT, public role, own rows); authenticated has SELECT only.

#### `user_word_watchlist`
Words a learner uploaded to be matched against newly generated tests (word-list import). Written by `services/word_list_import/upload_handler.py` (insert) and `match_sweep.py` (match columns); read by `build_daily_session`, `knowledge_report_summary`, `knowledge_report_words`, `sweep_cron.py`, `batch_limits.py`. Service-role access in practice: policy `rls_select` (SELECT, public role: service_role, owner, or admin) exists but `authenticated` holds no table grant. See `migrations/security_watchlist_reports_no_client_writes.sql`.

Columns: `id` bigint NN identity (ALWAYS), `user_id` uuid NN, `sense_id` integer NN, `language_id` smallint NN, `upload_batch_id` uuid NN, `created_at` timestamptz NN default `now()`, `ladder_exercises_generated` boolean NN default `false`, `last_matched_test_id` uuid, `last_matched_at` timestamptz, `active` boolean NN default `true`, `last_matched_surfaced_at` timestamptz. FKs: `language_id` -> `dim_languages(id)`, `last_matched_test_id` -> `tests(id)`, `sense_id` -> `dim_word_senses(id)`, `user_id` -> `users(id)` ON DELETE CASCADE. Indexes: `idx_user_word_watchlist_active_sense_id (sense_id) WHERE active = true`, `idx_user_word_watchlist_language_id (language_id)`, `idx_user_word_watchlist_last_matched_test_id (last_matched_test_id) WHERE last_matched_test_id IS NOT NULL`, `idx_user_word_watchlist_pending_word_upload (user_id, language_id) WHERE active = true AND last_matched_test_id IS NOT NULL`, `idx_user_word_watchlist_sense_id (sense_id)`, `idx_user_word_watchlist_upload_batch_id (upload_batch_id)`, `idx_user_word_watchlist_user_id (user_id)`. The watermark table for the nightly sweep (`word_upload_sweep_state`) is **not live**: see the Pending section.

#### `user_knowledge_snapshots`
Nightly per-learner, per-language snapshot of the inputs of the Knowledge Report estimate (calibration bands, tracked-word counts), kept 120 days. Written by `services/knowledge_snapshots.py` and read back by the same job; pruned by `knowledge_snapshots_prune`. Defined in `migrations/knowledge_report_foundation.sql`. Service-role only.

Columns: `user_id` uuid NN, `language_id` smallint NN, `snapshot_date` date NN, `method_version` smallint NN default `1`, `tracked_words`, `tracked_meanings`, `rated_known_words`, `checked_meanings`, `missed_recent_meanings`, `idle60_meanings`, `practised_30_meanings`, `direct_checks_30` integer NN, `cal_definition_language_id` smallint, `cal_bands` smallint[] (CHECK null or length 21), `frame_bands` integer[] (CHECK null or length 7), `cal_answers` integer NN default `0`, `cal_first_answer_at`, `cal_last_answer_at` timestamptz, `est_kind` smallint NN default `0` (CHECK 0..2), `est_lo`, `est_hi` integer, `est_label` smallint (CHECK 1..3), `source` text NN default `'nightly'` (CHECK `nightly`,`manual`), `computed_at` timestamptz NN default `now()`. PK `(user_id, language_id, snapshot_date)`. FKs: `cal_definition_language_id` and `language_id` -> `dim_languages(id)`, `user_id` -> `users(id)` ON DELETE CASCADE.

### `dt_passage` (full live column list, 2026-11-23)
Section 11 documents the TASK-901 additions; for completeness the live table is: `id` bigint NN identity, `l2_language_id` integer NN, `source_kind` text NN (CHECK = `test_transcript`), `source_ref_id` uuid NN, `l2_text` text NN, `age_tier` smallint NN (CHECK 1..6), `register` text, `status` text NN default `'active'` (CHECK `active`,`draft`,`retired`), `created_at` timestamptz default `now()`, `sentence_start`, `sentence_end` smallint. FK `l2_language_id` -> `dim_languages(id)`. Indexes `idx_dt_passage_l2_language (l2_language_id)`, `idx_dt_passage_source (source_kind, source_ref_id)`, `idx_dt_passage_status (status) WHERE status = 'active'`, unique `uq_dt_passage_sentence_range`. Service-role only (RLS on, no policy, no client grant).

---

## 14. Pending schema changes (migration written, NOT applied live)

Verified against the live database on 2026-11-23. The apply sheet with order, pre-checks, post-checks and rollbacks is `migrations/PENDING-2026-11-23.md`; nothing in this section is live. The function side of each item is in [[database/rpcs.tech]] ("Pending function changes").

| Schema effect | File | State today (live) |
|---|---|---|
| Unique index on `user_skill_ratings (user_id, language_id, test_type_id)` and on `test_skill_ratings (test_id, test_type_id)` (`CREATE UNIQUE INDEX CONCURRENTLY`, one statement per run) | `skill_ratings_natural_key_unique.sql` | Absent: live has only the `id` primary keys and the non-unique `idx_user_skill_ratings_language_test_type`, `idx_user_skill_ratings_user_id`, `idx_test_skill_ratings_test_id`, `idx_test_skill_ratings_test_type_id`. Until the ON CONFLICT writers follow, a racing first submission can insert a duplicate rating row. |
| New table `word_upload_sweep_state` (RLS on, no policy, service role only) plus two sweep advisory-lock functions | `word_upload_sweep_advisory_lock_hardened.sql` (replaces the unsafe `word_upload_sweep_advisory_lock.sql`, kept with a STALE/UNSAFE header) | Table and functions absent (`to_regclass` is NULL). The nightly `services/word_list_import/sweep_cron.py` run therefore errors. |
| One-off data fix: delete `dt_card` ids 11 and 12 (a zh entry built from a ja error) and re-queue profile entry 10 | `data_fix_dt_cards_cross_language_20261123.sql` | Both cards still exist. |
| Function-only changes (no table impact): drop of the 4-argument `update_vocabulary_from_word_test`; escaped-range L1 script check (the live trigger function wrongly starts the Han range at U+8C48 instead of U+F900); `prestudy_plan_inputs` definition-mode filter; ON CONFLICT writers in five submission RPCs and `apply_calibration_to_skill_ratings`; drop of `get_quiz_distractors_batch`; `get_word_quiz_candidates` retake fallback | see the list in [[database/rpcs.tech]] | Each file's pre-check hash equals the live body: all unapplied. |

Also written, effect already live (no action): `security_tests_service_role_only.sql`, `security_watchlist_reports_no_client_writes.sql`, `record_exercise_attempt.sql` (comment text only), and the 13 `baseline_*.sql` files (repo copies of live functions that had no definition; each is a no-op).

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

### Analytics and calibration views added after 2026-09

All eight live views (the three above plus these five) are `security_invoker = true` (migration `security_views_invoker.sql`); only `service_role` holds SELECT on them (`anon` and `authenticated` have no grant). None is read by application code except where stated.

- `v_ladder_judge_reject_rates`: per language, ladder level, prompt version and judge key, the number of exercises, rejected and kept items and the reject rate, from `exercises.tags` and `word_assets`. Columns: `language_id`, `ladder_level`, `prompt_version`, `judge_key`, `exercises_n`, `rejected_n`, `kept_n`, `items_n`, `reject_rate`. Created by `phase16_ladder_judge_reject_rates.sql`. No application reader.
- `v_sense_family_coverage`: per sense, the exercise families still missing for its language. Columns: `sense_id`, `language_id`, `missing_families text[]`, `missing_count`, `required_count`. Built on `dim_exercise_capabilities` and `word_assets`; read by `services/vocabulary_ladder/config.py` and `queue_drain.py`.
- `v_test_difficulty_calibration`: per test and test type, seeded ELO vs empirical ELO. Columns: `test_id`, `slug`, `language_id`, `difficulty`, `tier`, `seeded_elo`, `test_type_id`, `empirical_elo`, `total_attempts`, `elo_error`, `abs_elo_error`. `partF_test_difficulty_calibration.sql`.
- `v_test_difficulty_calibration_summary`: one row: `n_tests`, `n_tests_20plus`, `mae_all`, `mae_20plus`, `mean_bias_all`, `mean_bias_20plus`.
- `vw_exercise_type_effectiveness`: per p_known bucket and exercise type, attempts, users, senses, accuracy, mean change in p_known and change per minute (uses `exercise_attempts.p_known_before/after` and `time_taken_ms`, capped at 300 s). Columns: `p_known_bucket`, `exercise_type`, `attempts`, `users`, `senses`, `accuracy`, `mean_delta_p_known`, `total_minutes`, `delta_p_known_per_minute`. `task534_exercise_type_effectiveness.sql`; checked by `scripts/validate_effectiveness_view.py`.

Live column lists of the three older views: `corpus_statistics` (`language_id`, `language_name`, `collocation_type`, `n_gram_size`, `collocation_count`, `avg_pmi`, `avg_frequency`, `validated_count`), `vw_distractor_error_analysis` (`user_id`, `pattern_code`, `error_type`, `error_count`, `first_seen`, `last_seen`), `vw_exercise_performance_by_type` (`exercise_type`, `cefr_level`, `language_id`, `exercise_count`, `total_attempts`, `correct_count`, `accuracy_pct`).

---

## Triggers

| Table | Event | Trigger Name | Function | Description |
|-------|-------|-------------|----------|-------------|
| `dim_vocabulary` | BEFORE UPDATE | -- | `update_updated_at_column()` | Auto-set updated_at |
| `dim_vocabulary` | BEFORE INSERT OR UPDATE OF part_of_speech | `trg_dim_vocabulary_normalize_pos` | `trg_dim_vocabulary_normalize_pos()` | Maps any tag to the standard label; keeps the original in `part_of_speech_raw` (live 2026-11-22) |
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
| `test_sentences` | BEFORE INSERT/UPDATE | `test_sentences_check_l2_text` | `test_sentences_check_l2_text()` | l2_text must equal the transcript span (TASK-901, live) |
| `test_sentence_references` | BEFORE INSERT/UPDATE | `test_sentence_references_check_l1_script` | `test_sentence_references_check_l1_script()` | Reject L2 script (Han / kana) in l1_text (TASK-901, live; the live Han range wrongly starts at U+8C48, fix pending: section 14) |
| `user_study_plans` | BEFORE UPDATE | `trg_user_study_plans_updated_at` | `touch_user_study_plans_updated_at()` | Auto-set updated_at |
| `selection_tuning` | BEFORE UPDATE | `selection_tuning_touch` | `selection_tuning_touch()` | Auto-set updated_at |
| `dim_vocabulary` | AFTER UPDATE | `trg_dim_vocabulary_language_propagate` | `propagate_vocab_language_to_senses()` | Copies a changed language to the vocabulary's senses |
| `dim_word_senses` | BEFORE INSERT/UPDATE | `trg_dim_word_senses_word_language` | `set_sense_word_language()` | Sets `word_language_id` from the vocabulary row |
| `user_skill_rating_adjustments` | BEFORE UPDATE | `usra_append_only` | `usra_refuse_update()` | Refuses UPDATE (append-only audit) |
| `exercises` | BEFORE INSERT/UPDATE | `exercises_sense_quarantine` | `trg_exercises_sense_quarantine()` | Blocks active exercises for quarantined senses |
| `generation_queue` | BEFORE INSERT | `generation_queue_sense_quarantine` | `trg_generation_queue_sense_quarantine()` | Blocks queueing quarantined senses |
| `calibration_anchor_blocklist` | AFTER INSERT | `blocklist_retire_exercises` | `trg_blocklist_retire_exercises()` | Retires exercises of a newly quarantined sense |

**Note (live count 2026-11-23: 23 triggers on 17 tables; the rows above complete the list).** Duplicate trigger `update_skill_attempts_count_trigger` on test_attempts was removed in Phase 1.

---

## Key Database Functions (2026-05 selection of 52; the authoritative reference for all 214 live functions is [[database/rpcs.tech]])

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
- `get_recommended_tests(user_id, language_id)` -> table -- ranked candidate tests

### Exercise Serving (Vocab Dojo, Phase 8 Momentum Bands)
- ~~`get_ladder_session(p_user_id, p_language_id, p_count)`~~ (**dropped live 2026-11-17, ADR-049; absent, checked 2026-11-19**) -> table -- per-word ladder session builder with priority scoring (0.35·overdue + 0.25·weakness + 0.20·gate + 0.10·novelty + 0.10·relapse), family-aware target selection, A/B variant alternation, seen-today anti-repetition
- `ladder_record_attempt(...)` -> jsonb -- atomic family-BKT update, ring/gate evaluation, lapse handling, FSRS schedule on lapse
- `ladder_pass_gate(p_user_id, p_sense_id, p_gate_name)` -> jsonb -- ring advancement after passing a gate battery
- `ladder_graduate(p_user_id, p_sense_id, p_stress_test_score, p_language_id)` -> jsonb -- FSRS handoff (seeds stability/difficulty/due_date) on stress test pass
- Helpers: `ladder_get_family`, `ladder_get_ring`, `ladder_ring_families`, `ladder_compute_p_known`, `fsrs_schedule_review` (FSRS-4.5 port to PostgreSQL)

### Exercise content in Storage (ADR-049; `migrations/exercise_content_storage.sql` applied live 2026-11-17; commit and session RPCs canonical in `migrations/exercise_content_drop_column.sql`, live 2026-11-19)
All three are `SECURITY INVOKER`, `SET search_path = public, pg_temp`, EXECUTE for `service_role` only.
- `exercise_content_begin(p_sense_id integer)` -> jsonb -- `{sense_id, current_version (max content_version, 0 when no rows), new_version (nextval of exercise_content_version_seq), rows: [{id, language_id, exercise_type, ladder_level, word_asset_id, is_active, content_version}] ordered by id}`. No lock. NULL sense -> 22023.
- `exercise_content_commit(p_sense_id integer, p_expected_version integer, p_expected_ids uuid[], p_new_version integer, p_delete_ids uuid[] DEFAULT '{}', p_insert_rows jsonb DEFAULT '[]', p_update_contents jsonb DEFAULT '{}')` -> jsonb -- compare-and-swap commit under `pg_advisory_xact_lock(47047, p_sense_id)`. Lost race: `{ok:false, reason: 'version_conflict' | 'rows_changed', current_version}`, nothing changed (version checked first, then the row-id set). Success: deletes, inserts (`content_version := p_new_version`, `dedupe_key` from `row->'content'`, `tags` default `{}`, `is_active` default true, unknown keys ignored, `source_type` required), content updates (recompute `dedupe_key`), then stamps `p_new_version` on the rows it checked; returns `{ok:true, version, deleted, inserted, updated}`. Bad input raises 22023: NULL required args or NULL array elements, malformed JSON shapes, an insert row without `id`, for another sense or without an object `content`, a delete/update id not in the sense, an update id also deleted, `p_new_version <= current` (malformed uuid/int strings raise 22P02). Static checks run before the lock, row checks after the compare-and-swap, so a lost race never raises 22023. Live since 2026-11-19: the post-drop version (canonical `migrations/exercise_content_drop_column.sql` step 3d, live md5 `e2199ec8…`) still requires and validates the `content` JSON of insert rows and updates and computes `dedupe_key` from it, but stores no content (same contract).
- `exercise_content_live_versions(p_language_id integer)` -> jsonb -- `{"<sense_id>": [versions asc]}` over the language's rows with a sense (one value, so PostgREST's 1,000-row cap does not apply). Used by the sweep (`scripts/sweep_exercise_content.py`, which falls back to keyset pages of `exercises` on a statement timeout); the backfill script that also used it was retired in TASK-1031.
- `get_practice_session(..., p_include_content boolean DEFAULT true)` and `get_review_ahead_items(..., p_include_content boolean DEFAULT true)`: every exercise item carries `content_version` and, since the cut-over (2026-11-19), never `content` (`p_include_content` is accepted and ignored; Python passes false and hydrates from the files). Canonical bodies: `migrations/exercise_content_drop_column.sql` step 3e (live md5 `e2f6089f…` / `4043b817…`, checked 2026-11-19). The 6-argument pre-drop versions (`exercise_content_session_rpcs.sql`, applied 2026-11-17, which also dropped the dead `get_exercise_session` ×2 and `get_ladder_session`, TASK-220 drift) and both Phase-1 rollbacks are in `migrations/archive/` (TASK-1031); the only remaining rollback is `exercise_content_drop_column_rollback.sql`, which also needs a refill of `exercises.content` from Storage.

### Exercise Serving (Daily Mixed Session, Phase 9)
- ~~`get_exercise_session(p_user_id, p_language_id, p_session_size)`~~ (**dropped live 2026-11-17, ADR-049; absent, checked 2026-11-19**) -> table -- single SQL session builder for `/api/exercises/session`. Combines FSRS due, BKT uncertainty, new words, ladder content (delegated to `get_ladder_session`), and supplementary grammar/collocation. Uses `user_exercise_history` (indexed) for 7-day anti-repetition.
- Helpers: `exercise_type_phase_weight` (PHASE_MAP weighting), `tier_window_for_p_known`, `tier_to_phase`

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

### Local day boundary (ADR-022)
- `resolve_plan_timezone(p_tz text)` -> text -- the zone name if Postgres knows it, else `'UTC'`. Since 2026-11-11 (`migrations/latency_2026_11_db.sql`, applied live) looks the name up in **`tz_names`** first and scans `pg_timezone_names` only for a name missing from the snapshot (that scan cost ~55 ms warm / ~300-500 ms cold per call). [[decisions/ADR-042-request-scoped-caching-and-static-asset-caching]]
- `plan_local_date(user, language, at)` / `plan_local_day_start(...)` -- learner-local date / midnight via `resolve_plan_timezone`.

### `tz_names` (2026-11-11)
| Column | Type | Notes |
|---|---|---|
| name | text PK | Snapshot of `pg_timezone_names.name` (~1,200 rows). RLS on, no policies, `SELECT` granted to `service_role` only; read by SECURITY DEFINER callers. Refresh after a Postgres/tzdata upgrade: `INSERT INTO tz_names SELECT name FROM pg_timezone_names ON CONFLICT DO NOTHING`. |

### Indexes in `migrations/latency_2026_11_db.sql` (applied live 2026-11-11)
Foreign-key indexes on children of parents that really are deleted: `exercises(word_asset_id)`,
`user_exercise_history(exercise_id)`, `user_exercise_history(sense_id)`,
`user_vocabulary_knowledge(sense_id)`, `user_word_ladder(sense_id)`, `user_flashcards(sense_id)`,
`word_quiz_results(sense_id)`, `dim_classifier_noun_pairs(noun_sense_id)`,
`user_classifier_mastery(classifier_id)`, `prestudy_followups(session_id)`,
`prestudy_sessions(test_id)`, `token_transactions(attempt_id)`, `token_transactions(test_id)`,
`tests(gen_user)`, `user_skill_ratings(user_id)`, `app_error_logs(user_id)`,
`topic_generation_runs(category_id)`, `corpus_style_profiles(reference_source_id)`.
Dropped duplicates: `idx_cc_validated_lmi`, `idx_counter_pairs_counter`, `idx_counter_pairs_lemma`,
`uq_counter_noun_pairs_lemma_counter` (each an exact copy of an index that stays).
RLS policies now call `(select auth.uid())` / `(select auth.role())` (evaluated once per statement).

### Triggers
- `sync_exercise_history()` -> trigger -- copy exercise_attempts to user_exercise_history (Phase 4)

### Live changes applied 2026-11-17 (reviewed migrations, all backward compatible)

| Migration (repo file = applied name) | Applied version | Effect | Rollback |
|---|---|---|---|
| `migrations/dt_next_inputs.sql` | 20261117030308 | New function `dt_next_inputs(uuid, integer, integer) RETURNS jsonb` (STABLE, SECURITY INVOKER, `search_path = public, pg_temp`, EXECUTE service_role only). Nothing existing changed. Revised in the repo 2026-11-17 (no `legacy` key; same signature and grants), re-apply pending. | `migrations/dt_next_inputs_rollback.sql` (DROP FUNCTION) |
| `migrations/task998_classifier_drill_levels.sql` | 20261117034255 | `ALTER TABLE user_classifier_mastery ADD COLUMN IF NOT EXISTS level_attempts integer` (nullable, catalog-only; 44 rows, all NULL at apply). `CREATE OR REPLACE update_classifier_mastery` (same signature; promotion after 5 answers at the current level). New `get_classifier_drill_session_v2` (DEFINER, service_role only). v1 untouched. | `migrations/task998_classifier_drill_levels_rollback.sql` (exact previous mastery function; drops v2 and the column — loses `level_attempts`) |
| `migrations/task998_classifier_cloze_sentences_fill.sql` | 20261117034512 | Guarded DO-block UPDATE: `dim_classifier_noun_pairs.example_sentence` filled on exactly 661 language-1 rows that were NULL (copied from judged ladder sentences, then active zh test sentences). Re-run after any `scripts/build_classifier_dictionary.py` rebuild. | `migrations/task998_classifier_cloze_sentences_fill_rollback.sql` (NULL on the 661 rows) |
| `migrations/task994_vocab_frequency_fill.sql` | 20261117035509 | Guarded DO-block UPDATE: `dim_vocabulary.frequency_rank` filled on exactly 770 rows that were NULL (zh 229, en 422, ja 119), only where id, lemma and language are unchanged; `updated_at` bumped by `update_vocab_timestamp`. No `user_vocabulary_knowledge` row changed. | `migrations/task994_vocab_frequency_fill_rollback.sql` (resets a row only if it still holds the filled value) |

Integration check 2026-11-17: the four entries are the only migrations applied since 2026-11-14, and
each one's stored statement equals its repo file once comments and whitespace are removed (md5
compared). Readers of the filled `frequency_rank`: `selection_vocab_ability` (moves by ≤ 0.02 Zipf),
`bkt_infer_from_frequency` (can raise low-evidence rows upward), `calibration_anchor_pool` (picks the
words up on its next manual refresh). See [[decisions/ADR-047-basic-word-knowledge-prior]].

---

## RLS Summary (live, 2026-11-23)

All 100 tables have RLS enabled (the 2026-05-12 split of 36 enabled and 28 disabled is obsolete). The eight views run with `security_invoker = true`.

| Group | Tables |
|---|---|
| **RLS on, with at least one policy (42)** | app_error_logs, calibration_anchor_blocklist, calibration_responses, calibration_sessions, daily_test_load_items, daily_test_loads, dim_character_components, dim_complexity_tiers, dim_counter_distractor_groups, dim_counter_noun_pairs, dim_counters, dim_distractor_bands, dim_languages, dim_lens, dim_question_types, dim_status, dim_study_plan_templates, dim_subscription_tiers, dim_test_types, dim_vocabulary, dim_word_senses, exercise_attempts, question_attempt_results, test_attempts, token_transactions, trusted_devices, user_calibration_state, user_exercise_history, user_exercise_sessions, user_flashcards, user_languages, user_reports, user_skill_rating_adjustments, user_skill_ratings, user_study_plans, user_tokens, user_vocabulary_knowledge, user_word_ladder, user_word_watchlist, users, weekly_plan_states, word_quiz_results |
| **RLS on, no policy: service role only (58)** | every other table, including `exercises`, `word_assets`, `llm_calls`, `tests`, `questions`, `test_skill_ratings`, `prompt_templates`, `topics`, `categories`, `corpus_*`, `dt_*`, `generation_*`, `calibration_*` except the three listed above, `prestudy_*`, `study_time_ledger`, `test_sentences`, `test_sentence_references`, `user_knowledge_snapshots`, `user_classifier_mastery`, `user_test_intros_seen`, `selection_tuning`, `script_conversion_overrides`, `tz_names`, `tests_tier_backup_*` |

Tables with a policy but no client table grant (`calibration_responses`, `user_word_watchlist`, and others whose `authenticated` role holds no SELECT) have an inert policy: only the service key reads them. No table grants INSERT, UPDATE or DELETE to `anon` or `authenticated`. The `users` table policies are `rls_select`, `rls_insert`, `rls_update`, `rls_delete`; `user_reports` first referenced `public.users.id` in Phase 2 (was `auth.users.id`).

---

## Related Pages

- [[database/schema]] -- Plain English overview
- [[algorithms/elo-ranking]] -- ELO calculation details
- [[algorithms/vocabulary-ladder]] -- 9-level vocabulary ladder
- [[features/vocabulary-knowledge]] -- BKT model details
- [[features/vocab-dojo.tech]] -- Exercise serving algorithm
- [[api/rpcs.tech]] -- Full RPC specifications
- [[database/rpcs.tech]] -- Function reference for all 214 live functions (signatures, security, execute rights, tables touched, canonical files, pending changes)
- [[features/calibration.tech]], [[features/dual-translation.tech]], [[features/dt-guided-self-repair.tech]], [[features/test-prestudy]], [[features/test-sentence-references.tech]] -- feature specs behind the tables of section 13
