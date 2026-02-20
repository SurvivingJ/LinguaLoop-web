# Database Schema Overview

LinguaLoop uses **Supabase** (managed PostgreSQL) with the **pgvector** extension for embedding-based similarity search. Data models are defined as Python `dataclasses` (no ORM). Database access is through the Supabase PostgREST client and PostgreSQL RPC functions.

## Architecture

- **Supabase PostgREST**: RESTful access via the `supabase-py` client
- **RPC Functions**: Server-side PostgreSQL functions for atomic operations (ELO calculation, test submission)
- **pgvector**: 1536-dimensional embeddings on the `topics` table for semantic deduplication
- **Row-Level Security (RLS)**: Enforced on user-facing tables; bypassed by the service role client for admin/batch operations
- **No ORM**: Python `dataclasses` map to table rows; queries use the Supabase client builder pattern

## Table Groups

### User Domain
| Table | Purpose |
|-------|---------|
| `users` | Core user profiles, linked to `auth.users` |
| `user_skill_ratings` | Per-user ELO ratings by language and test type |
| `user_languages` | Tracks which languages a user has studied |
| `user_tokens` | Token balance and spending breakdown |
| `token_transactions` | Audit log for all token operations |
| `user_reports` | User-submitted reports |

### Test Domain
| Table | Purpose |
|-------|---------|
| `tests` | Generated tests with transcripts and metadata |
| `questions` | Individual questions belonging to a test |
| `test_attempts` | Records of user test submissions with ELO snapshots |
| `test_skill_ratings` | Per-test ELO ratings by test type |

### Generation Domain
| Table | Purpose |
|-------|---------|
| `topics` | Topic concepts with pgvector embeddings |
| `production_queue` | Topic-language pairs awaiting test generation |
| `categories` | Topic categories with cooldown scheduling |
| `topic_generation_runs` | Metrics for topic generation pipeline runs |
| `test_generation_runs` | Metrics for test generation pipeline runs |
| `test_generation_config` | Runtime configuration key-value store |

### Dimension Tables
| Table | Purpose |
|-------|---------|
| `dim_languages` | Supported languages with model configuration |
| `dim_test_types` | Test modes (listening, reading, dictation) |
| `dim_question_types` | Question taxonomy with cognitive levels |
| `dim_cefr_levels` | CEFR level definitions with word counts and ELO ranges |
| `dim_lens` | Topic exploration perspectives (historical, cultural, etc.) |
| `dim_status` | Status codes for queue and category workflows |

### System Tables
| Table | Purpose |
|-------|---------|
| `prompt_templates` | Versioned LLM prompt templates per task and language |
| `question_type_distributions` | Maps difficulty levels to question type mixes |
| `flagged_content` | Content flagged by moderation |

## Entity-Relationship Diagram

```mermaid
erDiagram
    %% ========== AUTH ==========
    auth_users {
        uuid id PK
    }

    %% ========== USER DOMAIN ==========
    users {
        uuid id PK, FK
        text email UK
        text display_name
        boolean email_verified
        integer total_tests_taken
        integer total_tests_generated
        timestamptz last_activity_at
        date last_free_test_date
        integer free_tests_used_today
        integer total_free_tests_used
        text subscription_tier
        timestamptz created_at
        timestamptz updated_at
        timestamptz last_login
    }

    user_skill_ratings {
        uuid id PK
        uuid user_id FK
        smallint language_id FK
        smallint test_type_id FK
        integer elo_rating
        real volatility
        integer tests_taken
        date last_test_date
        integer current_streak
        integer longest_streak
        timestamptz created_at
        timestamptz updated_at
    }

    user_languages {
        uuid id PK
        uuid user_id FK
        smallint language_id FK
        integer total_tests_taken
        date last_test_date
        timestamptz created_at
        timestamptz updated_at
    }

    user_tokens {
        uuid user_id PK, FK
        integer purchased_tokens
        integer bonus_tokens
        integer total_tokens_earned
        integer total_tokens_spent
        integer total_tokens_purchased
        timestamptz created_at
        timestamptz updated_at
    }

    %% ========== TEST DOMAIN ==========
    tests {
        uuid id PK
        uuid gen_user FK
        text slug UK
        smallint language_id FK
        uuid topic_id FK
        integer difficulty
        text style
        text tier
        text title
        text transcript
        text audio_url
        integer total_attempts
        boolean is_active
        boolean is_featured
        boolean is_custom
        text generation_model
        boolean audio_generated
        timestamptz created_at
        timestamptz updated_at
    }

    questions {
        uuid id PK
        uuid test_id FK
        text question_id
        text question_text
        text question_type
        smallint question_type_id FK
        jsonb choices
        jsonb correct_answer
        text answer_explanation
        integer points
        text audio_url
        timestamptz created_at
        timestamptz updated_at
    }

    test_attempts {
        uuid id PK
        uuid user_id FK
        uuid test_id FK
        smallint test_type_id FK
        smallint language_id FK
        integer score
        integer total_questions
        real percentage
        integer attempt_number
        boolean is_first_attempt
        integer user_elo_before
        integer user_elo_after
        integer test_elo_before
        integer test_elo_after
        integer elo_change
        boolean was_free_test
        integer tokens_consumed
        uuid idempotency_key
        timestamptz created_at
    }

    test_skill_ratings {
        uuid id PK
        uuid test_id FK
        smallint test_type_id FK
        integer elo_rating
        real volatility
        integer total_attempts
        timestamptz created_at
        timestamptz updated_at
    }

    %% ========== GENERATION DOMAIN ==========
    topics {
        uuid id PK
        integer category_id FK
        text concept_english
        integer lens_id FK
        jsonb keywords
        vector embedding
        text semantic_signature
        timestamptz created_at
    }

    production_queue {
        uuid id PK
        uuid topic_id FK
        smallint language_id FK
        integer status_id FK
        integer tests_generated
        text error_log
        timestamptz created_at
        timestamptz processed_at
    }

    categories {
        serial id PK
        varchar name UK
        text description
        integer status_id FK
        smallint target_language_id FK
        integer total_topics_generated
        timestamptz last_used_at
        integer cooldown_days
        timestamptz created_at
        timestamptz updated_at
    }

    %% ========== DIMENSION TABLES ==========
    dim_languages {
        smallserial id PK
        varchar language_code UK
        varchar language_name
        varchar native_name
        boolean is_active
        integer display_order
        varchar prose_model
        varchar question_model
        jsonb tts_voice_ids
        decimal tts_speed
        boolean grammar_check_enabled
    }

    dim_test_types {
        smallserial id PK
        varchar type_code UK
        varchar type_name
        boolean requires_audio
        boolean is_active
        integer display_order
    }

    dim_question_types {
        smallserial id PK
        varchar type_code UK
        varchar type_name
        text description
        integer cognitive_level
        boolean is_active
        integer display_order
        timestamptz created_at
    }

    dim_cefr_levels {
        smallserial id PK
        varchar cefr_code UK
        integer difficulty_min
        integer difficulty_max
        integer word_count_min
        integer word_count_max
        integer initial_elo
        timestamptz created_at
    }

    dim_lens {
        serial id PK
        varchar lens_code UK
        varchar display_name
        text description
        text prompt_hint
        boolean is_active
        integer sort_order
    }

    dim_status {
        serial id PK
        varchar status_code UK
    }

    %% ========== SYSTEM TABLES ==========
    prompt_templates {
        serial id PK
        varchar task_name
        smallint language_id FK
        text template_text
        text description
        integer version
        boolean is_active
        timestamptz created_at
    }

    question_type_distributions {
        integer difficulty PK
        varchar question_type_1 FK
        varchar question_type_2 FK
        varchar question_type_3 FK
        varchar question_type_4 FK
        varchar question_type_5 FK
        timestamptz created_at
    }

    %% ========== RELATIONSHIPS ==========
    auth_users ||--|| users : "id"
    users ||--o{ user_skill_ratings : "user_id"
    users ||--o{ user_languages : "user_id"
    users ||--|| user_tokens : "user_id"
    users ||--o{ test_attempts : "user_id"
    users ||--o{ tests : "gen_user"

    tests ||--o{ questions : "test_id"
    tests ||--o{ test_attempts : "test_id"
    tests ||--o{ test_skill_ratings : "test_id"
    tests }o--|| dim_languages : "language_id"
    tests }o--o| topics : "topic_id"

    questions }o--o| dim_question_types : "question_type_id"

    test_attempts }o--|| dim_languages : "language_id"
    test_attempts }o--|| dim_test_types : "test_type_id"

    test_skill_ratings }o--|| dim_test_types : "test_type_id"
    user_skill_ratings }o--|| dim_languages : "language_id"
    user_skill_ratings }o--|| dim_test_types : "test_type_id"

    topics }o--|| categories : "category_id"
    topics }o--|| dim_lens : "lens_id"

    production_queue }o--|| topics : "topic_id"
    production_queue }o--|| dim_languages : "language_id"
    production_queue }o--|| dim_status : "status_id"

    categories }o--|| dim_status : "status_id"
    categories }o--o| dim_languages : "target_language_id"

    prompt_templates }o--|| dim_languages : "language_id"

    question_type_distributions }o--|| dim_question_types : "question_type_1"
    question_type_distributions }o--|| dim_question_types : "question_type_2"
    question_type_distributions }o--|| dim_question_types : "question_type_3"
    question_type_distributions }o--|| dim_question_types : "question_type_4"
    question_type_distributions }o--|| dim_question_types : "question_type_5"
```

## Key Design Patterns

1. **Dimension Tables**: All enumerated values (languages, test types, statuses, CEFR levels) are stored in `dim_*` tables rather than as string enums. This enables runtime configuration changes without code deploys.

2. **ELO Rating System**: Both users and tests have ELO ratings. Ratings are tracked per (user, language, test_type) and per (test, test_type) combination, enabling fine-grained skill assessment.

3. **Dual-Client Architecture**: The anon client respects RLS for user-facing operations; the service role client bypasses RLS for admin, batch, and generation pipeline operations.

4. **Atomic Submissions**: Test submissions are processed via the `process_test_submission` RPC function, which validates answers, calculates ELO, and updates all related tables in a single transaction.

5. **pgvector Embeddings**: The `topics.embedding` column stores 1536-dimensional OpenAI embeddings. The `match_topics` RPC function uses cosine similarity for semantic deduplication within categories.

---

## Related Documents

- [02-table-reference.md](./02-table-reference.md) -- Full column-level documentation for every table
- [03-dimension-tables.md](./03-dimension-tables.md) -- Dimension table seed data and caching patterns
- [04-rpc-functions.md](./04-rpc-functions.md) -- PostgreSQL RPC function reference
- [05-rls-policies.md](./05-rls-policies.md) -- Row-Level Security policy documentation
- [06-migration-history.md](./06-migration-history.md) -- Migration file history and changelog
