# Architectural Decision Records

## ADR-001: Supabase as Backend-as-a-Service

**Status:** Accepted
**Date:** Project inception

**Context:** The platform needs PostgreSQL, authentication, row-level security, realtime capabilities, and storage. Building and managing each independently is operationally expensive.

**Decision:** Use Supabase as a unified BaaS providing PostgreSQL, Auth (OTP), Row-Level Security (RLS), Storage, and Edge Functions through a single SDK (supabase-py 2.6.0).

**Consequences:**
- (+) Single SDK for database, auth, and storage
- (+) Built-in RLS eliminates manual authorization logic for data access
- (+) Managed PostgreSQL with pgvector extension for embeddings
- (+) OTP auth built-in, no need for custom auth infrastructure
- (-) Vendor lock-in to Supabase's PostgREST query syntax
- (-) Complex operations require RPC functions rather than ORM queries
- (-) No traditional ORM (SQLAlchemy) — all queries use Supabase client

---

## ADR-002: Dual Supabase Clients (Anon vs Service Role)

**Status:** Accepted

**Context:** Supabase RLS policies restrict data access based on the authenticated user's JWT. Some operations (admin lookups, batch processing, cross-user queries) need to bypass RLS.

**Decision:** Create two Supabase clients via `SupabaseFactory` (singleton):
- **Anon client** (`get_supabase()`): Uses anon key, respects RLS policies. Used for user-context operations.
- **Service client** (`get_supabase_admin()`): Uses service role key, bypasses RLS. Used for admin operations, dimension table lookups, batch scripts, and auth operations requiring elevated privileges.

**Consequences:**
- (+) Clean separation of privilege levels
- (+) Batch scripts and admin operations work without RLS constraints
- (+) Single factory ensures consistent client creation
- (-) Developers must choose the correct client for each operation
- (-) Service role key grants full database access — must be protected

---

## ADR-003: OTP-Only Authentication (No Passwords)

**Status:** Accepted

**Context:** Traditional password-based auth requires hashing, password reset flows, and is vulnerable to credential stuffing. The target audience (language learners) benefits from frictionless login.

**Decision:** Use Supabase Auth's OTP (One-Time Password) via email exclusively. No passwords stored or managed. JWT tokens valid for 24 hours with refresh token support.

**Consequences:**
- (+) Zero password management, no credential storage risk
- (+) Simpler signup flow (email only)
- (+) Supabase handles OTP generation, delivery, and verification
- (-) Requires valid email for every login
- (-) Users must check email each session (mitigated by 24h token + refresh)
- (-) Depends on email deliverability

---

## ADR-004: OpenRouter for Language-Specific LLM Routing

**Status:** Accepted

**Context:** Different languages benefit from different LLM models. Chinese comprehension is better with DeepSeek, Japanese with Qwen, English with Gemini. Managing multiple API clients is complex.

**Decision:** Use OpenRouter as a unified LLM gateway. Configure per-language model selection in `Config.AI_MODELS`:
- English: `google/gemini-2.0-flash-001`
- Chinese: `deepseek/deepseek-chat`
- Japanese: `qwen/qwen-2.5-72b-instruct`

Fallback to OpenAI `gpt-4o-mini` when OpenRouter is disabled (`USE_OPENROUTER=false`).

**Consequences:**
- (+) Single API interface for multiple model providers
- (+) Language-optimized content generation
- (+) Easy to swap models per language without code changes
- (-) Adds OpenRouter as a dependency (latency, availability)
- (-) Pricing varies by model — cost less predictable
- (-) `USE_OPENROUTER` toggle adds conditional logic throughout `ai_service.py`

---

## ADR-005: ELO Rating System for Adaptive Difficulty

**Status:** Accepted

**Context:** Users need tests matched to their skill level. Static difficulty assignment doesn't adapt. A dynamic rating system can match users to appropriately challenging tests.

**Decision:** Implement a modified Glicko-2/ELO system where:
- Users start at ELO 1200
- Tests have ELO ratings per skill type (listening, reading, dictation), starting at values mapped from CEFR difficulty
- After each attempt, both user and test ELO are updated via the `process_test_submission` RPC function
- Recommended tests are selected within ±200 ELO of the user's rating

**Consequences:**
- (+) Adaptive difficulty without manual curation
- (+) Tests self-calibrate based on user performance
- (+) Per-skill ratings allow granular progression tracking
- (-) Cold start problem — new users/tests have uncertain ratings
- (-) ELO calculation in database RPC adds complexity
- (-) Volatility parameter adds another dimension to manage

---

## ADR-006: Cloudflare R2 for Audio Storage

**Status:** Accepted

**Context:** Generated audio files (MP3) need to be stored and served publicly. AWS S3 charges per-GB egress fees. Audio files are accessed frequently by users taking tests.

**Decision:** Use Cloudflare R2 (S3-compatible object storage) via boto3. Serve files through a public URL (`https://audio.linguadojo.com`).

**Consequences:**
- (+) Zero egress fees — all audio delivery is free
- (+) S3-compatible API — existing boto3 code works unchanged
- (+) Public URL with custom domain for clean audio links
- (-) Cloudflare ecosystem lock-in
- (-) R2 feature set is smaller than S3 (no lifecycle policies, limited event notifications)

---

## ADR-007: Azure TTS over OpenAI TTS

**Status:** Accepted
**Date:** Migrated (see AZURE_MIGRATION_GUIDE.md)

**Context:** OpenAI TTS was initially used for audio generation. Quality for non-English languages (Chinese, Japanese) was insufficient. More voice variety was needed.

**Decision:** Migrate to Azure Cognitive Services Speech SDK for text-to-speech. Configure language-specific neural voices. Keep OpenAI as TTS fallback model name in config but use Azure SDK for actual synthesis.

**Consequences:**
- (+) Superior multi-language voice quality
- (+) More voice options per language (Azure Neural Voices)
- (+) SSML support for fine-grained speech control
- (-) Azure SDK dependency (`azure-cognitiveservices-speech`)
- (-) Requires Azure subscription and Speech Services resource
- (-) Different API pattern (SDK vs REST)

---

## ADR-008: Server-Rendered Templates (Jinja2) over SPA Framework

**Status:** Accepted

**Context:** The application could use a modern SPA framework (React, Vue) or server-rendered HTML templates. The team is small and the frontend is relatively straightforward.

**Decision:** Use Flask's Jinja2 templates with vanilla JavaScript and Bootstrap 5. No frontend build step, no Node.js dependency, no component framework.

**Consequences:**
- (+) Zero frontend build complexity — no webpack, no npm
- (+) Faster initial page loads (server-rendered HTML)
- (+) Single language stack (Python)
- (+) Bootstrap 5 provides responsive layout out of the box
- (-) No component reuse system — HTML is duplicated across templates
- (-) Complex client-side state (test-taking) is harder without a framework
- (-) Large inline `<script>` blocks in templates (test.html is 1100+ lines)
- (-) No hot module replacement during development

---

## ADR-009: RPC-Heavy Database Operations

**Status:** Accepted

**Context:** Complex operations like ELO calculation, test recommendation, and topic similarity search involve multiple tables and transactional logic. The Supabase PostgREST client doesn't support JOINs or transactions natively.

**Decision:** Implement complex operations as PostgreSQL functions (RPCs) callable via `supabase.rpc()`:
- `process_test_submission` — Score test, calculate ELO, create attempt record atomically
- `get_recommended_test` / `get_recommended_tests` — Match tests to user ELO
- `match_topics` — Vector similarity search via pgvector
- `get_next_category` — Category rotation with cooldown

**Consequences:**
- (+) Atomic operations — no partial state from failed transactions
- (+) Better performance — logic runs in the database, not in Python
- (+) Single round-trip per complex operation
- (-) Business logic split between Python and SQL — harder to test
- (-) RPC functions are harder to version and migrate than app code
- (-) Debugging database functions requires different tooling

---

## ADR-010: Multi-Agent Orchestration Pattern for Content Generation

**Status:** Accepted

**Context:** Test generation requires multiple sequential AI operations: topic translation, prose writing, question generation, validation, title creation, and audio synthesis. Topic generation similarly requires exploration, deduplication, and validation.

**Decision:** Implement an Orchestrator + Agent pattern:
- **Orchestrator** coordinates the workflow, handles errors, tracks metrics
- **Agents** are specialized classes with single responsibilities (e.g., `ProseWriter`, `QuestionGenerator`, `ArchivistAgent`)
- Each agent wraps LLM calls with retry logic, input/output validation, and logging
- Agents are stateless — all state flows through the orchestrator

**Consequences:**
- (+) Clear separation of concerns — each agent is testable independently
- (+) Easy to add new agents or modify individual steps
- (+) Retry logic per agent prevents full pipeline failures
- (+) Metrics tracking at each stage for cost and quality monitoring
- (-) More files and classes than a monolithic approach
- (-) Data must be serialized between agents
- (-) Orchestrator becomes a coordination bottleneck

---

## ADR-011: Token Economy with Stripe

**Status:** Accepted

**Context:** The platform needs a monetization mechanism. Direct subscription gates are too restrictive for casual learners. A token system allows flexible usage.

**Decision:** Implement a token economy:
- 2 free tokens daily (configurable via `DAILY_FREE_TOKENS`)
- Taking a test costs 1 token, generating a test costs 5 tokens
- Tokens purchasable via Stripe in packages (10/$1.99, 50/$7.99, 200/$19.99)
- Token balance tracked in `users.tokens` column

**Consequences:**
- (+) Low barrier to entry with free daily tokens
- (+) Flexible pricing — users pay for what they use
- (+) Stripe handles payment security and PCI compliance
- (-) Token balance must be checked before every action
- (-) Race conditions possible on concurrent token consumption
- (-) Stripe integration adds webhook handling complexity

---

## Related Documents
- [System Architecture](01-system-architecture.md)
- [Security Model](06-security-model.md)
- [Config Reference](../04-Backend/02-config-reference.md)
- [ELO Rating System](../10-Systems/01-elo-rating-system.md)
- [Token Economy](../10-Systems/02-token-economy.md)
