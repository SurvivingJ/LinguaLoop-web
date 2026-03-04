# TestDatabaseClient Reference

**Source:** `services/test_generation/database_client.py`

The `TestDatabaseClient` handles all database interactions for the test generation pipeline. It uses the Supabase admin client (via `SupabaseFactory`) and maintains in-memory caches for dimension tables.

## Data Models

### QueueItem

Represents a row from the `production_queue` table.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID` | Primary key |
| `topic_id` | `UUID` | FK to `topics` |
| `language_id` | `int` | FK to `dim_languages` |
| `status_id` | `int` | FK to `dim_status` |
| `created_at` | `datetime` | Queue insertion timestamp |
| `tests_generated` | `int` | Count of tests produced (default 0) |
| `error_log` | `str?` | Error message if failed |

### Topic

Represents a row from the `topics` table.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID` | Primary key |
| `category_id` | `int` | FK to `categories` |
| `concept_english` | `str` | Topic concept in English |
| `lens_id` | `int` | FK to `dim_lens` |
| `keywords` | `List[str]` | Topic keywords |
| `semantic_signature` | `str?` | Human-readable embedding signature |

### LanguageConfig

Extended language configuration for test generation from `dim_languages`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `int` | -- | Primary key |
| `language_code` | `str` | -- | ISO code (e.g., "zh") |
| `language_name` | `str` | -- | Display name (e.g., "Chinese") |
| `native_name` | `str` | -- | Native name |
| `prose_model` | `str` | `google/gemini-2.0-flash-exp` | LLM model for prose generation |
| `question_model` | `str` | `google/gemini-2.0-flash-exp` | LLM model for question generation |
| `tts_voice_ids` | `List[str]` | `['alloy']` | Azure Neural Voice names |
| `tts_speed` | `float` | `1.0` | TTS playback speed |
| `grammar_check_enabled` | `bool` | `False` | Whether grammar checking is active |

### CEFRConfig

CEFR level configuration from `dim_cefr_levels`.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `int` | Primary key |
| `cefr_code` | `str` | CEFR code (e.g., "A1", "B2") |
| `difficulty_min` | `int` | Lowest difficulty for this level |
| `difficulty_max` | `int` | Highest difficulty for this level |
| `word_count_min` | `int` | Minimum prose word count |
| `word_count_max` | `int` | Maximum prose word count |
| `initial_elo` | `int` | Starting ELO rating for tests |

### QuestionType

Question type definition from `dim_question_types`.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `int` | Primary key |
| `type_code` | `str` | Code (e.g., "literal_detail") |
| `type_name` | `str` | Display name |
| `description` | `str?` | Description text |
| `cognitive_level` | `int` | Cognitive level 1-3 |

### GeneratedTest

Data for inserting a generated test into the `tests` table.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID` | Pre-generated test UUID |
| `slug` | `str` | Unique slug (format: `{lang}-d{diff}-{topic}-{timestamp}`) |
| `language_id` | `int` | FK to `dim_languages` |
| `language_name` | `str` | Language display name |
| `topic_id` | `UUID` | FK to `topics` |
| `topic_name` | `str` | Topic concept for reference |
| `difficulty` | `int` | Difficulty level 1-9 |
| `transcript` | `str` | Generated prose text |
| `gen_user` | `str` | System user UUID |
| `initial_elo` | `int` | Starting ELO rating |
| `audio_url` | `str` | R2 public URL for audio |
| `title` | `str?` | Generated title (nullable) |

### GeneratedQuestion

Data for inserting a generated question into the `questions` table.

| Field | Type | Description |
|-------|------|-------------|
| `test_id` | `UUID` | FK to `tests` |
| `question_id` | `str` | Slug-based ID (e.g., `zh-d3-topic-q1`) |
| `question_text` | `str` | Question text |
| `choices` | `List[str]` | Four answer options |
| `answer` | `str` | Correct answer text |
| `question_type_id` | `int?` | FK to `dim_question_types` |

### TestGenMetrics

Metrics for the `test_generation_runs` table.

| Field | Type | Description |
|-------|------|-------------|
| `run_date` | `datetime` | Run timestamp |
| `queue_items_processed` | `int` | Items processed (default 0) |
| `tests_generated` | `int` | Tests created (default 0) |
| `tests_failed` | `int` | Tests that failed (default 0) |
| `execution_time_seconds` | `int?` | Wall time |
| `error_message` | `str?` | Error if run crashed |

## Methods

### Queue Operations

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_pending_queue_items` | `(limit: int = 50) -> List[QueueItem]` | Fetch pending items for active languages, ordered by `created_at` |
| `update_queue_item_status` | `(queue_id, status_code, tests_generated, error_log)` | Update queue item status and tracking fields |
| `mark_queue_processing` | `(queue_id: UUID)` | Mark as `processing` |
| `mark_queue_completed` | `(queue_id: UUID, tests_generated: int)` | Mark as `active` with count |
| `mark_queue_failed` | `(queue_id: UUID, error_message: str)` | Mark as `rejected` with error |

### Topic Queries

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_topic` | `(topic_id: UUID) -> Optional[Topic]` | Fetch topic by ID |
| `get_category_name` | `(category_id: int) -> str` | Get category name by ID |

### Language Configuration

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_language_config` | `(language_id: int) -> Optional[LanguageConfig]` | Fetch language config with model settings (cached) |

### CEFR Configuration

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_cefr_config` | `(difficulty: int) -> Optional[CEFRConfig]` | Get CEFR config for difficulty (cached) |
| `get_word_count_range` | `(difficulty: int) -> tuple` | Get `(min, max)` word counts |
| `get_initial_elo` | `(difficulty: int) -> int` | Get initial ELO rating |

### Question Types

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_question_types` | `() -> Dict[str, QuestionType]` | Get all active question types (cached) |
| `get_question_distribution` | `(difficulty: int) -> List[str]` | Get ordered type codes for a difficulty |
| `get_question_type_id` | `(type_code: str) -> Optional[int]` | Get type ID by code |
| `get_active_test_types` | `() -> List[dict]` | Fetch active test types from `dim_test_types` |

### Prompt Templates

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_prompt_template` | `(task_name: str, language_id: int) -> Optional[str]` | Fetch prompt template with English fallback |

### Test Insertion

| Method | Signature | Description |
|--------|-----------|-------------|
| `insert_test` | `(test: GeneratedTest) -> str` | Insert test row, returns slug |
| `insert_questions` | `(questions: List[GeneratedQuestion]) -> int` | Batch insert questions |
| `insert_test_skill_ratings` | `(test_id, initial_elo, has_audio)` | Insert skill ratings for active test types |

### Metrics

| Method | Signature | Description |
|--------|-----------|-------------|
| `insert_generation_run` | `(metrics: TestGenMetrics)` | Insert run metrics to `test_generation_runs` |

### Configuration

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_config_value` | `(key: str, default: str?) -> Optional[str]` | Get runtime config from `test_generation_config` table |

### Utilities

| Method | Signature | Description |
|--------|-----------|-------------|
| `generate_test_slug` | `(language_code, difficulty, topic_concept) -> str` | Generate slug: `{lang}-d{diff}-{snippet}-{timestamp}` |
| `clear_caches` | `()` | Clear all in-memory caches |

## Caching

The client maintains in-memory caches for dimension tables to minimize database roundtrips:
- `_language_cache` -- per language_id
- `_cefr_cache` -- all CEFR levels
- `_question_type_cache` -- by type_code
- `_distribution_cache` -- by difficulty
- `_status_cache` -- status_code to ID mapping
- `_config_cache` -- runtime config key/value pairs

---

### Related Documents

- [Pipeline Overview](./01-pipeline-overview.md)
- [Orchestrator](./02-orchestrator.md)
- [Configuration](./04-config.md)
