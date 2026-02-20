# LinguaLoop/LinguaDojo Project Knowledge

> Comprehensive documentation for the LinguaLoop language learning platform (80 documents).

---

## 🚀 Quick Start

| Goal | Read This |
|------|-----------|
| **New to the project** | [Project Overview](01-Overview/01-project-overview.md) → [Tech Stack](01-Overview/02-tech-stack.md) → [System Architecture](02-Architecture/01-system-architecture.md) |
| **Setting up locally** | [Environment Setup](11-Rules-and-Conventions/06-environment-setup.md) → [Environment Variables](11-Rules-and-Conventions/04-environment-variables.md) |
| **Understanding the database** | [Schema Overview](03-Database/01-schema-overview.md) → [Tables Reference](03-Database/02-tables-reference.md) |
| **Working on frontend** | [Frontend Overview](06-Frontend/01-frontend-overview.md) → [Page Reference](06-Frontend/02-templates/02-page-reference.md) |
| **Understanding AI pipelines** | [Test Gen Overview](05-Pipelines/01-test-generation/01-pipeline-overview.md) + [Topic Gen Overview](05-Pipelines/02-topic-generation/01-pipeline-overview.md) |

---

## 🎯 Task-Based Navigation

| I want to... | Read These |
|--------------|-----------|
| **Add a new API endpoint** | [Request Lifecycle](02-Architecture/02-request-lifecycle.md) → [Auth Middleware](04-Backend/04-middleware/01-auth-middleware.md) → [API Response Format](11-Rules-and-Conventions/03-api-response-format.md) |
| **Modify test generation pipeline** | [Test Gen Overview](05-Pipelines/01-test-generation/01-pipeline-overview.md) → [Orchestrator](05-Pipelines/01-test-generation/02-orchestrator.md) → [Agents](05-Pipelines/01-test-generation/03-agents/) |
| **Modify topic generation pipeline** | [Topic Gen Overview](05-Pipelines/02-topic-generation/01-pipeline-overview.md) → [Orchestrator](05-Pipelines/02-topic-generation/02-orchestrator.md) → [Agents](05-Pipelines/02-topic-generation/03-agents/) |
| **Understand authentication** | [Security Model](02-Architecture/06-security-model.md) → [Auth Middleware](04-Backend/04-middleware/01-auth-middleware.md) → [Client Auth Flow](06-Frontend/04-client-auth-flow.md) → [OTP Auth Spec](12-PRD/02-feature-specifications/01-otp-authentication.md) |
| **Work on the frontend** | [Frontend Overview](06-Frontend/01-frontend-overview.md) → [Base Template](06-Frontend/02-templates/01-base-template.md) → [Static Assets](06-Frontend/03-static-assets.md) |
| **Run batch scripts** | [Scripts Overview](08-Scripts/01-scripts-overview.md) → [Batch Scripts](08-Scripts/04-batch-scripts.md) |
| **Understand the ELO system** | [ELO Rating System](10-Systems/01-elo-rating-system.md) → [ELO Progression Spec](12-PRD/02-feature-specifications/06-elo-progression.md) → [RPC Functions](03-Database/04-rpc-functions.md) |
| **Add a new language** | [Language Support](10-Systems/05-language-support.md) → [Config Reference](04-Backend/02-config-reference.md) → [Dimension Tables](03-Database/03-dimension-tables.md) |
| **Understand payments** | [Token Economy](10-Systems/02-token-economy.md) → [Token Payments Spec](12-PRD/02-feature-specifications/05-token-payments.md) |
| **Modify prompts** | [Prompt Catalog](09-Prompts/01-prompt-catalog.md) → [Prompt Design Guidelines](09-Prompts/02-prompt-design-guidelines.md) |
| **Fix bugs** | [Error Handling](11-Rules-and-Conventions/02-error-handling.md) → [Coding Conventions](11-Rules-and-Conventions/01-coding-conventions.md) |

---

## 📚 Complete Table of Contents

### 01 - Overview (3 docs)
- [01 - Project Overview](01-Overview/01-project-overview.md) — What LinguaDojo is, high-level architecture, key features
- [02 - Tech Stack](01-Overview/02-tech-stack.md) — Every dependency with version and purpose (77 packages)
- [03 - Glossary](01-Overview/03-glossary.md) — Domain terms, abbreviations, naming conventions

### 02 - Architecture (6 docs)
- [01 - System Architecture](02-Architecture/01-system-architecture.md) — Mermaid C4 diagrams at 3 granularity levels
- [02 - Request Lifecycle](02-Architecture/02-request-lifecycle.md) — Sequence diagram of an authenticated request
- [03 - Service Dependency Graph](02-Architecture/03-service-dependency-graph.md) — How services depend on each other
- [04 - Design Patterns](02-Architecture/04-design-patterns.md) — Factory, Singleton, Decorator, Multi-Agent Orchestration
- [05 - Architectural Decisions](02-Architecture/05-architectural-decisions.md) — ADR log with context, decisions, consequences
- [06 - Security Model](02-Architecture/06-security-model.md) — JWT flow, RLS, dual-client pattern

### 03 - Database (6 docs)
- [01 - Schema Overview](03-Database/01-schema-overview.md) — Mermaid ER diagram of all tables
- [02 - Tables Reference](03-Database/02-tables-reference.md) — Every table, column, type, constraint, and relationship
- [03 - Dimension Tables](03-Database/03-dimension-tables.md) — dim_languages, dim_categories, dim_cefr_levels, etc.
- [04 - RPC Functions](03-Database/04-rpc-functions.md) — process_test_submission, calculate_elo_rating, calculate_volatility_multiplier
- [05 - RLS Policies](03-Database/05-rls-policies.md) — Row-Level Security and dual-client pattern
- [06 - Migrations](03-Database/06-migrations.md) — Migration files and execution workflow

### 04 - Backend (4 docs + 4 routes + 1 middleware)
- [01 - App Entrypoint](04-Backend/01-app-entrypoint.md) — app.py create_app(), initialization, blueprint registration
- [02 - Config Reference](04-Backend/02-config-reference.md) — Every config variable with env var mapping
- **Routes:**
  - [01 - Auth Routes](04-Backend/03-routes/01-auth-routes.md) — /api/auth/* endpoints (send-otp, verify-otp, refresh-token, profile, logout)
  - [02 - Test Routes](04-Backend/03-routes/02-test-routes.md) — /api/tests/* endpoints (browse, get, submit, generate, random, recommended)
  - [03 - Report Routes](04-Backend/03-routes/03-report-routes.md) — /api/reports/submit
  - [04 - Core Routes](04-Backend/03-routes/04-core-routes.md) — Health, user profile, token balance, payments
- **Middleware:**
  - [01 - Auth Middleware](04-Backend/04-middleware/01-auth-middleware.md) — @jwt_required, @admin_required, @tier_required decorators

### 05 - Pipelines (20 docs)
- **Test Generation Pipeline (10 docs):**
  - [01 - Pipeline Overview](05-Pipelines/01-test-generation/01-pipeline-overview.md) — End-to-end workflow with sequence diagram
  - [02 - Orchestrator](05-Pipelines/01-test-generation/02-orchestrator.md) — TestGenerationOrchestrator class deep dive
  - **Agents:**
    - [01 - Topic Translator](05-Pipelines/01-test-generation/03-agents/01-topic-translator.md)
    - [02 - Prose Writer](05-Pipelines/01-test-generation/03-agents/02-prose-writer.md)
    - [03 - Title Generator](05-Pipelines/01-test-generation/03-agents/03-title-generator.md)
    - [04 - Question Generator](05-Pipelines/01-test-generation/03-agents/04-question-generator.md)
    - [05 - Question Validator](05-Pipelines/01-test-generation/03-agents/05-question-validator.md)
    - [06 - Audio Synthesizer](05-Pipelines/01-test-generation/03-agents/06-audio-synthesizer.md)
  - [04 - Config](05-Pipelines/01-test-generation/04-config.md) — TestGenConfig reference
  - [05 - Database Client](05-Pipelines/01-test-generation/05-database-client.md) — TestDatabaseClient with all data models

- **Topic Generation Pipeline (10 docs):**
  - [01 - Pipeline Overview](05-Pipelines/02-topic-generation/01-pipeline-overview.md) — End-to-end workflow with sequence diagram
  - [02 - Orchestrator](05-Pipelines/02-topic-generation/02-orchestrator.md) — TopicGenerationOrchestrator class deep dive
  - **Agents:**
    - [01 - Explorer Agent](05-Pipelines/02-topic-generation/03-agents/01-explorer-agent.md)
    - [02 - Archivist Agent](05-Pipelines/02-topic-generation/03-agents/02-archivist-agent.md)
    - [03 - Gatekeeper Agent](05-Pipelines/02-topic-generation/03-agents/03-gatekeeper-agent.md)
    - [04 - Embedding Service](05-Pipelines/02-topic-generation/03-agents/04-embedding-service.md)
  - [04 - Config](05-Pipelines/02-topic-generation/04-config.md) — TopicGenConfig reference
  - [05 - Database Client](05-Pipelines/02-topic-generation/05-database-client.md) — TopicDatabaseClient with all data models

### 06 - Frontend (5 docs)
- [01 - Frontend Overview](06-Frontend/01-frontend-overview.md) — Jinja2 + vanilla JS + Bootstrap 5 architecture, template inheritance diagram
- **Templates:**
  - [01 - Base Template](06-Frontend/02-templates/01-base-template.md) — base.html layout, navbar, authFetch(), report modal, global config
  - [02 - Page Reference](06-Frontend/02-templates/02-page-reference.md) — All 7 child templates (login, language_selection, test_list, test_preview, test, profile, onboarding)
- [03 - Static Assets](06-Frontend/03-static-assets.md) — styles.css (design tokens) + utils.js (helper functions)
- [04 - Client Auth Flow](06-Frontend/04-client-auth-flow.md) — JWT storage, authFetch() wrapper, token refresh, logout, protected pages

### 07 - API Reference (7 docs)
- [01 - API Overview](07-API-Reference/01-api-overview.md) — Base URL, auth scheme, response format, error codes
- [02 - Auth Endpoints](07-API-Reference/02-auth-endpoints.md) — 5 auth endpoints with curl examples
- [03 - Test Endpoints](07-API-Reference/03-test-endpoints.md) — 9 test endpoints with request/response examples
- [04 - User Endpoints](07-API-Reference/04-user-endpoints.md) — User profile and token balance
- [05 - Payment Endpoints](07-API-Reference/05-payment-endpoints.md) — Stripe checkout and webhooks
- [06 - Report Endpoints](07-API-Reference/06-report-endpoints.md) — Issue reporting
- [07 - Utility Endpoints](07-API-Reference/07-utility-endpoints.md) — Health checks and metadata

### 08 - Scripts (4 docs)
- [01 - Scripts Overview](08-Scripts/01-scripts-overview.md) — Purpose and usage of all 10 scripts
- [02 - Run Test Generation](08-Scripts/02-run-test-generation.md) — scripts/run_test_generation.py entry point
- [03 - Run Topic Generation](08-Scripts/03-run-topic-generation.md) — scripts/run_topic_generation.py entry point
- [04 - Batch Scripts](08-Scripts/04-batch-scripts.md) — base_generator.py, batch generation, upload, backfill, verify

### 09 - Prompts (2 docs)
- [01 - Prompt Catalog](09-Prompts/01-prompt-catalog.md) — All prompt templates (file-based + database) with variables and usage
- [02 - Prompt Design Guidelines](09-Prompts/02-prompt-design-guidelines.md) — JSON-only output, double-brace escaping, few-shot examples, deduplication

### 10 - Systems (6 docs)
- [01 - ELO Rating System](10-Systems/01-elo-rating-system.md) — Formula, K-factor, starting values, per-mode ratings
- [02 - Token Economy](10-Systems/02-token-economy.md) — Free daily allocation, costs, Stripe packages, balance tracking
- [03 - Content Moderation](10-Systems/03-content-moderation.md) — OpenAI moderation integration
- [04 - Audio Pipeline](10-Systems/04-audio-pipeline.md) — Azure TTS → Cloudflare R2 → public URL workflow
- [05 - Language Support](10-Systems/05-language-support.md) — 3 languages, per-language models, TTS voices, config
- [06 - CEFR Difficulty Mapping](10-Systems/06-cefr-difficulty-mapping.md) — 9 difficulty levels mapped to CEFR (A1-C2)

### 11 - Rules and Conventions (6 docs)
- [01 - Coding Conventions](11-Rules-and-Conventions/01-coding-conventions.md) — Python patterns, naming, imports, dataclasses, logging
- [02 - Error Handling](11-Rules-and-Conventions/02-error-handling.md) — Flask routes, services, pipelines, DB RPCs, client-side
- [03 - API Response Format](11-Rules-and-Conventions/03-api-response-format.md) — Standard JSON shapes for success/error
- [04 - Environment Variables](11-Rules-and-Conventions/04-environment-variables.md) — Complete list of 30+ env vars
- [05 - Assumptions and Constraints](11-Rules-and-Conventions/05-assumptions-and-constraints.md) — Known limitations and design decisions
- [06 - Environment Setup](11-Rules-and-Conventions/06-environment-setup.md) — Complete local development and production setup guide

### 12 - PRD (9 docs)
- [01 - Product Requirements](12-PRD/01-product-requirements.md) — Full PRD with vision, user journeys, metrics, success criteria
- **Feature Specifications:**
  - [01 - OTP Authentication](12-PRD/02-feature-specifications/01-otp-authentication.md) — Passwordless login with email OTP
  - [02 - Test Taking](12-PRD/02-feature-specifications/02-test-taking.md) — 3 test modes (reading/listening/dictation), audio player, submission
  - [03 - Test Generation](12-PRD/02-feature-specifications/03-test-generation.md) — 6-agent AI pipeline for test creation
  - [04 - Topic Generation](12-PRD/02-feature-specifications/04-topic-generation.md) — 4-agent AI pipeline for topic discovery
  - [05 - Token Payments](12-PRD/02-feature-specifications/05-token-payments.md) — Token economy, Stripe integration, packages
  - [06 - ELO Progression](12-PRD/02-feature-specifications/06-elo-progression.md) — Adaptive difficulty matching with ELO ratings
  - [07 - User Reporting](12-PRD/02-feature-specifications/07-user-reporting.md) — In-app issue reporting with 6 categories
  - [08 - Language Selection](12-PRD/02-feature-specifications/08-language-selection.md) — 3 languages (Chinese, English, Japanese)

---

## 📊 Documentation Statistics

| Section | Documents | Coverage |
|---------|-----------|----------|
| **Overview** | 3 | Project intro, tech stack, glossary |
| **Architecture** | 6 | System design, patterns, security |
| **Database** | 6 | Schema, tables, RPCs, RLS, migrations |
| **Backend** | 9 | Routes, middleware, app structure |
| **Pipelines** | 20 | Test + topic generation (2×10 docs) |
| **Frontend** | 5 | Templates, static assets, auth flow |
| **API Reference** | 7 | All endpoints documented |
| **Scripts** | 4 | Batch operations, maintenance |
| **Prompts** | 2 | Templates, design guidelines |
| **Systems** | 6 | ELO, tokens, audio, languages, CEFR |
| **Conventions** | 6 | Coding style, errors, env vars, setup |
| **PRD** | 9 | Requirements + 8 feature specs |
| **TOTAL** | **80** | **Complete project documentation** |

---

## 🔍 Key Technical Concepts

### Core Technologies
- **Backend**: Flask 3.0.3 (Python 3.11+)
- **Database**: Supabase (PostgreSQL 14 + pgvector)
- **Frontend**: Jinja2 SSR + vanilla JS + Bootstrap 5
- **AI**: OpenAI GPT-4 (test gen) + OpenRouter (topic gen)
- **Audio**: Azure Cognitive Services TTS
- **Storage**: Cloudflare R2
- **Payments**: Stripe
- **Auth**: JWT with OTP (passwordless)

### Architecture Patterns
- **Multi-Agent Orchestration**: 6 agents (test gen) + 4 agents (topic gen)
- **Dual Supabase Client**: anon (RLS) vs service role (bypass RLS)
- **Factory Pattern**: SupabaseFactory, ServiceFactory
- **Singleton**: Config classes (TestGenConfig, TopicGenConfig)
- **Decorator**: @jwt_required, @admin_required, @tier_required

### Key Systems
- **ELO Rating**: Adaptive difficulty matching (K=32, range 400-3000)
- **Token Economy**: 2 free/day, costs 1 (test) / 5 (generate)
- **CEFR Mapping**: 9 difficulty levels → A1-C2
- **Languages**: Chinese (id=1), English (id=2), Japanese (id=3)
- **Test Modes**: Reading, Listening, Dictation

---

## 💡 Common Development Flows

### Adding a New Route
1. Create route function in `routes/` blueprint
2. Add @jwt_required decorator if authenticated
3. Implement business logic using services
4. Return JSON using standard response format
5. Document in API Reference section

### Modifying AI Pipeline
1. Read pipeline overview + orchestrator docs
2. Modify agent class in `services/*/agents/`
3. Update config if new parameters needed
4. Test with scripts/run_*_generation.py
5. Update prompt templates if needed

### Adding Database Table
1. Write CREATE TABLE SQL
2. Execute in Supabase SQL Editor
3. Add to schema overview diagram
4. Document in tables reference
5. Update RLS policies if user-facing

---

## 🆘 Getting Help

### For Development Questions
- **Architecture**: See [System Architecture](02-Architecture/01-system-architecture.md)
- **Database**: See [Schema Overview](03-Database/01-schema-overview.md)
- **API**: See [API Reference](07-API-Reference/01-api-overview.md)
- **Setup**: See [Environment Setup](11-Rules-and-Conventions/06-environment-setup.md)

### For Product Questions
- **Features**: See [PRD](12-PRD/01-product-requirements.md)
- **User Flows**: See feature specifications in [12-PRD/02-feature-specifications/](12-PRD/02-feature-specifications/)

---

## 📝 Documentation Conventions

### File References
Format: `file:line` (e.g., `app.py:147`)

### Mermaid Diagrams
- System architecture uses C4 model
- Workflows use sequence diagrams
- Data models use ER diagrams

### Code Examples
- Python: Type hints shown
- JavaScript: ES6+ syntax
- SQL: PostgreSQL 14 syntax
- Bash: Unix-style (not Windows CMD)

---

**Last Updated**: February 2026
**Total Documents**: 80
**Project Status**: Production-ready comprehensive documentation
