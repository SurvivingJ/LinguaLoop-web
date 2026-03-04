# Dimension Tables

All enumerated values in LinguaLoop are stored in `dim_*` tables rather than string enums. This enables runtime configuration changes without code deploys and provides referential integrity through foreign keys. Dimension data is cached in-memory by the Python database clients on first access.

---

## `dim_languages`

Supported target languages with model configuration and TTS settings.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `smallserial` | PK | Auto-increment ID |
| `language_code` | `varchar` | UNIQUE, NOT NULL | ISO-style short code |
| `language_name` | `varchar` | NOT NULL | English name |
| `native_name` | `varchar` | | Name in the language itself |
| `is_active` | `boolean` | DEFAULT `true` | Whether available for generation |
| `display_order` | `integer` | DEFAULT `0` | UI sort order |
| `prose_model` | `varchar(100)` | DEFAULT `'google/gemini-2.0-flash-exp'` | LLM for prose generation |
| `question_model` | `varchar(100)` | DEFAULT `'google/gemini-2.0-flash-exp'` | LLM for question generation |
| `tts_voice_ids` | `jsonb` | DEFAULT `'["alloy"]'` | OpenAI TTS voice IDs |
| `tts_speed` | `decimal(3,2)` | DEFAULT `1.0` | TTS playback speed multiplier |
| `grammar_check_enabled` | `boolean` | DEFAULT `false` | Whether grammar validation is active |

### Seed Data

| id | language_code | language_name | native_name |
|----|--------------|---------------|-------------|
| 1 | `cn` | Chinese | (Chinese characters) |
| 2 | `en` | English | English |
| 3 | `jp` | Japanese | (Japanese characters) |

### Application Usage

- **Caching**: `TestDatabaseClient._language_cache` (keyed by `id`) and `TopicDatabaseClient._language_cache` (keyed by `id`). Also `DimensionService._language_cache` (keyed by `language_code`).
- **Lookup pattern**: Language-specific prompt templates fall back to `language_id=2` (English) when not found.
- **Model config columns** were added by `migrations/test_generation_tables.sql` lines 136-141.

**Source**: `services/test_generation/database_client.py` lines 47-58, 303-354; `services/test_service.py` lines 44-68; `migrations/test_generation_tables.sql` lines 136-141

---

## `dim_test_types`

Test modes that determine how a test is presented to the user.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `smallserial` | PK | Auto-increment ID |
| `type_code` | `varchar` | UNIQUE, NOT NULL | Machine identifier |
| `type_name` | `varchar` | NOT NULL | Human-readable name |
| `requires_audio` | `boolean` | NOT NULL | Whether this mode needs audio |
| `is_active` | `boolean` | DEFAULT `true` | Availability flag |
| `display_order` | `integer` | DEFAULT `0` | UI sort order |

### Seed Data

| id | type_code | type_name | requires_audio |
|----|-----------|-----------|----------------|
| 1 | `listening` | Listening | `true` |
| 2 | `reading` | Reading | `false` |
| 3 | `dictation` | Dictation | `true` |

### Application Usage

- When a test is generated, `test_skill_ratings` rows are created for each active test type. Types requiring audio are skipped if the test has no audio.
- The `process_test_submission` v2 RPC accepts `p_test_type_id` to determine which ELO ratings to update.
- `DimensionService` caches `type_code -> id` mappings at app startup.

**Source**: `services/test_generation/database_client.py` lines 417-429, 650-693; `services/test_service.py` lines 60-68, 118-147

---

## `dim_question_types`

Taxonomy of 6 question types organized across 3 cognitive levels, based on Bloom's taxonomy principles.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `smallserial` | PK | Auto-increment ID |
| `type_code` | `varchar(30)` | UNIQUE, NOT NULL | Machine identifier |
| `type_name` | `varchar(50)` | NOT NULL | Display name |
| `description` | `text` | | What this question type tests |
| `cognitive_level` | `integer` | NOT NULL, CHECK `1-3` | 1=Recall, 2=Understand, 3=Analyze |
| `is_active` | `boolean` | DEFAULT `true` | |
| `display_order` | `integer` | DEFAULT `0` | |
| `created_at` | `timestamptz` | DEFAULT `NOW()` | |

### Seed Data

| id | type_code | type_name | cognitive_level | description |
|----|-----------|-----------|-----------------|-------------|
| 1 | `literal_detail` | Literal Detail | 1 (Recall) | Direct facts from text |
| 2 | `vocabulary_context` | Vocabulary in Context | 1 (Recall) | Word/phrase meaning in passage |
| 3 | `main_idea` | Main Idea | 2 (Understand) | Central theme or purpose |
| 4 | `supporting_detail` | Supporting Detail | 2 (Understand) | Facts supporting main points |
| 5 | `inference` | Inference | 3 (Analyze) | Conclusions from implicit info |
| 6 | `author_purpose` | Author Purpose/Tone | 3 (Analyze) | Why author wrote, attitude |

### Cognitive Level Distribution

Lower difficulty levels emphasize Level 1 (Recall) questions. Higher levels shift toward Level 3 (Analyze):

- **Difficulty 1-2 (A1)**: 80% Recall, 20% Understand
- **Difficulty 3-4 (A2)**: 40% Recall, 40% Understand, 20% Analyze (at difficulty 4)
- **Difficulty 5 (B1)**: 20% Recall, 40% Understand, 20% Analyze
- **Difficulty 6 (B2)**: 20% Recall, 20% Understand, 40% Analyze
- **Difficulty 7-9 (C1-C2)**: 0-20% Recall, 20-40% Understand, 40-60% Analyze

**Source**: `migrations/test_generation_tables.sql` lines 13-32; `services/test_generation/database_client.py` lines 452-523

---

## `dim_cefr_levels`

Maps the internal difficulty scale (1-9) to CEFR levels with word count ranges and initial ELO ratings.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `smallserial` | PK | Auto-increment ID |
| `cefr_code` | `varchar(2)` | UNIQUE, NOT NULL | Standard CEFR code |
| `difficulty_min` | `integer` | NOT NULL | Lowest difficulty in range |
| `difficulty_max` | `integer` | NOT NULL | Highest difficulty in range |
| `word_count_min` | `integer` | NOT NULL | Minimum transcript words |
| `word_count_max` | `integer` | NOT NULL | Maximum transcript words |
| `initial_elo` | `integer` | NOT NULL | Starting ELO for tests at this level |
| `created_at` | `timestamptz` | DEFAULT `NOW()` | |

### Seed Data

| id | cefr_code | difficulty_min | difficulty_max | word_count_min | word_count_max | initial_elo |
|----|-----------|---------------|---------------|---------------|---------------|------------|
| 1 | A1 | 1 | 2 | 80 | 150 | 875 |
| 2 | A2 | 3 | 4 | 120 | 200 | 1175 |
| 3 | B1 | 5 | 5 | 200 | 300 | 1400 |
| 4 | B2 | 6 | 6 | 300 | 400 | 1550 |
| 5 | C1 | 7 | 7 | 400 | 600 | 1700 |
| 6 | C2 | 8 | 9 | 600 | 900 | 1925 |

### Application Usage

- `TestDatabaseClient.get_cefr_config(difficulty)` returns the CEFR row matching a difficulty level. Result is cached in `_cefr_cache`.
- `get_initial_elo(difficulty)` is used when creating `test_skill_ratings` for newly generated tests.
- `get_word_count_range(difficulty)` controls prose generation prompt parameters.
- The `get_cefr_config` RPC function provides the same lookup at the database level.

**Source**: `migrations/test_generation_tables.sql` lines 35-54; `services/test_generation/database_client.py` lines 360-446

---

## `dim_lens`

Exploration perspectives for topic generation. Each topic is generated through a specific "lens" that shapes the angle of the content.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `serial` | PK | Auto-increment ID |
| `lens_code` | `varchar` | UNIQUE, NOT NULL | Machine identifier |
| `display_name` | `varchar` | NOT NULL | Human-readable name |
| `description` | `text` | | What this lens explores |
| `prompt_hint` | `text` | | Hint text injected into LLM prompts |
| `is_active` | `boolean` | DEFAULT `true` | |
| `sort_order` | `integer` | DEFAULT `0` | Display ordering |

### Example Seed Data

Lenses include perspectives such as: `historical`, `cultural`, `scientific`, `practical`, `philosophical`, etc. Each lens steers the topic explorer LLM to generate topics from a specific angle.

### Application Usage

- `TopicDatabaseClient.get_active_lenses()` loads all active lenses into `_lens_cache`.
- `get_lens_by_code(lens_code)` provides O(1) lookup from cache.
- Topics store `lens_id` to record which perspective was used.

**Source**: `services/topic_generation/database_client.py` lines 128-179

---

## `dim_status`

General-purpose status codes used by `production_queue` and `categories`.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `serial` | PK | Auto-increment ID |
| `status_code` | `varchar` | UNIQUE, NOT NULL | Machine identifier |

### Seed Data

| id | status_code |
|----|-------------|
| 1 | `pending` |
| 2 | `processing` |
| 3 | `active` |
| 4 | `rejected` |
| 5 | `cooldown` |

### Application Usage

- Both `TestDatabaseClient._get_status_id()` and `TopicDatabaseClient._get_status_id()` cache the full table for O(1) lookups.
- Default status ID is `1` (pending) if a code is not found.

**Source**: `services/test_generation/database_client.py` lines 752-763; `services/topic_generation/database_client.py` lines 181-192

---

## `question_type_distributions`

Maps each difficulty level (1-9) to a distribution of 5 question types that define the cognitive mix for generated tests.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `difficulty` | `integer` | PK, CHECK `1-9` | Difficulty level |
| `question_type_1` through `question_type_5` | `varchar(30)` | FK -> `dim_question_types.type_code` | Ordered question type slots |
| `created_at` | `timestamptz` | DEFAULT `NOW()` | |

### Seed Data

| Difficulty | Type 1 | Type 2 | Type 3 | Type 4 | Type 5 |
|-----------|--------|--------|--------|--------|--------|
| 1 (A1) | literal_detail | literal_detail | vocabulary_context | vocabulary_context | main_idea |
| 2 (A1) | literal_detail | literal_detail | vocabulary_context | vocabulary_context | main_idea |
| 3 (A2) | literal_detail | vocabulary_context | vocabulary_context | main_idea | supporting_detail |
| 4 (A2) | literal_detail | vocabulary_context | main_idea | supporting_detail | supporting_detail |
| 5 (B1) | vocabulary_context | main_idea | main_idea | supporting_detail | inference |
| 6 (B2) | vocabulary_context | main_idea | supporting_detail | inference | inference |
| 7 (C1) | main_idea | supporting_detail | supporting_detail | inference | author_purpose |
| 8 (C2) | main_idea | supporting_detail | inference | inference | author_purpose |
| 9 (C2) | supporting_detail | inference | inference | author_purpose | author_purpose |

### Application Usage

- `TestDatabaseClient.get_question_distribution(difficulty)` returns a list of 5 type codes.
- The `get_question_distribution` RPC function provides the same data via SQL `unnest`.
- Each type code maps to a specific `prompt_templates` row (e.g., `question_literal_detail`).

**Source**: `migrations/test_generation_tables.sql` lines 57-85; `services/test_generation/database_client.py` lines 478-516

---

## Caching Pattern

All dimension tables are cached in-memory by the database clients to avoid repeated queries:

```
Client                          Cache Key           Lookup
------                          ---------           ------
TestDatabaseClient              _language_cache     language_id -> LanguageConfig
                                _cefr_cache         cefr_id -> CEFRConfig
                                _question_type_cache type_code -> QuestionType
                                _distribution_cache  difficulty -> List[str]
                                _status_cache       status_code -> int
                                _config_cache       config_key -> str

TopicDatabaseClient             _lens_cache         lens_id -> Lens
                                _language_cache     language_id -> Language
                                _status_cache       status_code -> int

DimensionService (test_service) _language_cache     language_code -> int
                                _test_type_cache    type_code -> int
```

Caches are populated on first access and persist for the lifetime of the client instance. Both `TestDatabaseClient.clear_caches()` and `TopicDatabaseClient.clear_caches()` reset all caches.

**Source**: `services/test_generation/database_client.py` lines 133-139, 765-773; `services/topic_generation/database_client.py` lines 90-92, 592-597

---

## Related Documents

- [01-schema-overview.md](./01-schema-overview.md) -- High-level architecture and table groups
- [02-tables-reference.md](./02-tables-reference.md) -- Full column-level documentation for every table
- [04-rpc-functions.md](./04-rpc-functions.md) -- PostgreSQL RPC function reference
- [05-rls-policies.md](./05-rls-policies.md) -- Row-Level Security policy documentation
- [06-migrations.md](./06-migrations.md) -- Migration file history and changelog
