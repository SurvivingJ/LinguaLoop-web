# Assumptions and Constraints

> Source references: `config.py`, `app.py`, `middleware/auth.py`, `routes/tests.py`, `services/test_generation/config.py`, `services/topic_generation/config.py`, `static/js/utils.js`

---

## 1. Architecture Assumptions

### Single-Tenant Application
The application serves a single deployment with all users sharing the same database, services, and configuration. There is no multi-tenancy, workspace isolation, or per-organization settings.

### No WebSockets / Real-Time
All communication is request-response HTTP. There are no WebSocket connections, Server-Sent Events, or real-time push notifications. Test generation progress is not streamed to the client.

### No Internationalization (i18n) Framework
The UI is English-only. While the platform teaches multiple languages, all interface text, error messages, and labels are hardcoded in English. There is no i18n library or translation file system.

### No Admin Panel
There is no admin dashboard or content management interface. Administrative operations (user management, content moderation, metrics review) are performed directly via database queries or Supabase dashboard.

### No Test Suite
There are no automated tests (unit, integration, or end-to-end). There is no testing framework configured, no test directory, and no CI/CD pipeline.

### No CI/CD Pipeline
Deployment is manual. There is no GitHub Actions, Jenkins, or other continuous integration/deployment system configured.

---

## 2. Language Constraints

### Three Languages Hardcoded
The platform supports exactly three languages with fixed IDs in `config.py`:

| ID | Code | Name |
|---|---|---|
| 1 | `cn` | Chinese |
| 2 | `en` | English |
| 3 | `jp` | Japanese |

These IDs are referenced throughout the codebase, database schema, and frontend. Adding a new language requires code changes in multiple locations plus database schema updates (dimension tables, language configs, TTS voice mappings).

### Language-Specific AI Models
Each language uses a different optimal model via OpenRouter:

| Language | Model |
|---|---|
| English | `google/gemini-2.0-flash-001` |
| Chinese | `deepseek/deepseek-chat` |
| Japanese | `qwen/qwen-2.5-72b-instruct` |

Fallback model (when OpenRouter is disabled): `gpt-4o-mini` via OpenAI directly.

---

## 3. Authentication Constraints

### OTP-Only Authentication
The only authentication mechanism is email-based OTP (One-Time Password) via Supabase Auth. There is:
- No password-based login
- No social login (Google, GitHub, etc.)
- No magic link authentication
- No MFA/2FA beyond the OTP itself

### JWT Token Lifecycle
- Access tokens expire after **24 hours** (`JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)`)
- Refresh tokens are provided by Supabase and stored client-side in `localStorage`
- Token refresh is attempted silently on 401 responses
- No token rotation or blacklisting mechanism

---

## 4. Token Economy Constraints

### Fixed Token Costs

| Action | Cost |
|---|---|
| Take a test | 1 token |
| Generate a test | 5 tokens |

### Daily Free Allocation
- **2 free tokens per day** (configurable via `DAILY_FREE_TOKENS` env var)
- Free tokens are granted on first API call of the day (checked against `last_free_token_date`)
- Free tokens do not accumulate across days

### Stripe Payment Packages

| Package | Tokens | Price (USD) |
|---|---|---|
| `starter_10` | 10 | $1.99 |
| `popular_50` | 50 | $7.99 |
| `premium_200` | 200 | $19.99 |

Currency is USD only. No subscription model -- tokens are one-time purchases.

---

## 5. ELO Rating Constraints

### Starting Rating
Both users and tests start with an ELO rating of **1400** (Intermediate level).

### ELO Ranges

| Range | Label | Class |
|---|---|---|
| 0 -- 1199 | Beginner | `badge-beginner` |
| 1200 -- 1399 | Elementary | `badge-elementary` |
| 1400 -- 1599 | Intermediate | `badge-intermediate` |
| 1600 -- 1799 | Advanced | `badge-advanced` |
| 1800+ | Expert | `badge-expert` |

### K-Factor
The K-factor (ELO change sensitivity) is managed by the database RPC function `process_test_submission`. The exact value is configured in PostgreSQL, not in the application code.

### Per-Skill Ratings
Users and tests have separate ELO ratings per test mode (listening, reading, dictation) per language. Ratings are not aggregated across skills or languages.

---

## 6. AI Service Constraints

### Azure TTS Only
Text-to-speech uses Azure Cognitive Services (via OpenAI TTS API compatibility). There is no fallback TTS provider. Audio generation is treated as non-critical -- if it fails, the test is saved without audio.

### OpenRouter vs. OpenAI
- **OpenRouter**: Used for LLM calls (transcript generation, question generation) when `USE_OPENROUTER=true`. Supports language-specific model routing.
- **OpenAI**: Used for TTS, content moderation, and embeddings (`text-embedding-3-small`). Always required regardless of OpenRouter setting.
- Default model when OpenRouter is off: `gpt-4o-mini`

### Embedding Configuration
- Model: `text-embedding-3-small`
- Dimensions: **1536** (fixed, matches pgvector column definition)
- Used for semantic deduplication in topic generation

### Similarity Threshold
- Default: **0.85** cosine similarity
- Topics with embedding similarity >= 0.85 to any existing topic in the same category are rejected as duplicates
- Configurable via `TOPIC_SIMILARITY_THRESHOLD` env var (valid range: 0.5 -- 1.0)

---

## 7. Infrastructure Constraints

### Supabase (PostgreSQL + pgvector)
- Database is hosted on Supabase with Row Level Security (RLS) enabled
- Two client types: anon (respects RLS) and service role (bypasses RLS)
- Critical business logic (ELO calculation, test submission) lives in PostgreSQL RPC functions
- pgvector extension used for embedding storage and similarity search

### Cloudflare R2 Storage
- Audio files stored in R2 bucket `linguadojoaudio`
- Public URL pattern: `https://audio.linguadojo.com/<slug>.mp3`
- Files are MP3 format, named by test UUID/slug
- No CDN cache invalidation mechanism

### CEFR 9-Level Difficulty Scale
Difficulty levels 1--9 map to CEFR levels:

| Difficulty | CEFR |
|---|---|
| 1 | A1 |
| 2 | A1+ |
| 3 | A2 |
| 4 | A2+ |
| 5 | B1 |
| 6 | B1+ |
| 7 | B2 |
| 8 | C1 |
| 9 | C2 |

Each difficulty level has associated word count ranges, initial ELO ratings, and question type distributions defined in database dimension tables.

---

## 8. Frontend Constraints

### Server-Side Rendering + Client-Side Hydration
- HTML pages rendered via Jinja2 templates (Flask `render_template`)
- Page-specific JavaScript fetches data from API endpoints
- No frontend build system (no Webpack, Vite, etc.)
- No frontend framework (React, Vue, etc.)

### Bootstrap 5
- UI framework is Bootstrap 5 (vanilla, no React-Bootstrap or similar)
- Visibility toggling uses `d-none` CSS class
- No custom CSS preprocessor (no SASS/LESS)

### localStorage for State
- JWT token: `localStorage.getItem('jwt_token')`
- Language selection: stored in `localStorage`
- No server-side session state beyond JWT

---

## 9. Operational Constraints

### Batch Processing
- Test generation runs as a batch process (not triggered by user requests in real-time)
- Topic generation runs daily with configurable quotas
- Both pipelines support `dry_run` mode for testing
- Service role key used for batch authentication

### Content Moderation
- OpenAI Moderation API used to check user-submitted content (custom test transcripts)
- Flagged content is recorded in database but not automatically blocked
- No human review workflow

### Rate Limiting
- No application-level rate limiting
- Relies on Supabase and OpenRouter built-in rate limits
- No request queuing or throttling mechanism

---

## Related Documents

- [01-coding-conventions.md](./01-coding-conventions.md) -- Code patterns
- [03-api-response-format.md](./03-api-response-format.md) -- API conventions
- [../12-PRD/01-product-requirements.md](../12-PRD/01-product-requirements.md) -- Product vision
- [../12-PRD/02-feature-specifications/05-token-payments.md](../12-PRD/02-feature-specifications/05-token-payments.md) -- Token economy details
- [../12-PRD/02-feature-specifications/06-elo-progression.md](../12-PRD/02-feature-specifications/06-elo-progression.md) -- ELO system details
