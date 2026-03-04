# Environment Variables Reference

This is the canonical list of all environment variables used across the LinguaLoop platform. Variables are grouped by the configuration file that reads them.

## Core Application (`config.py`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | `temp-secret-change-in-production` | Flask secret key for session signing |
| `FLASK_DEBUG` | No | `False` | Enable debug mode (`true`/`false`) |
| `JWT_SECRET_KEY` | Yes | `jwt-secret-change-in-production` | Secret for JWT token signing |
| `CORS_ORIGINS` | No | `http://localhost:49640,http://localhost:3000,http://localhost:5000` | Comma-separated allowed CORS origins |

## AI Services (`config.py`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USE_OPENROUTER` | No | `false` | Enable OpenRouter for language-specific models |
| `OPENROUTER_API_KEY` | Conditional | (empty) | OpenRouter API key (required if `USE_OPENROUTER=true`) |
| `OPENAI_API_KEY` | Yes | None | OpenAI API key for LLM, embeddings, moderation |

## Database (`config.py`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SUPABASE_URL` | Yes | None | Supabase project URL |
| `SUPABASE_KEY` | Yes | None | Supabase anon/public key (respects RLS) |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | None | Supabase service role key (bypasses RLS) |

## Storage - Cloudflare R2 (`config.py`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `R2_ACCESS_KEY_ID` | Yes | None | Cloudflare R2 access key |
| `R2_SECRET_ACCESS_KEY` | Yes | None | Cloudflare R2 secret key |
| `R2_ACCOUNT_ID` | Yes | None | Cloudflare account ID |
| `R2_BUCKET_NAME` | No | `linguadojoaudio` | R2 bucket name |
| `R2_PUBLIC_URL` | No | `https://audio.linguadojo.com` | Public URL for serving audio files |

## Legacy AWS (`config.py`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AWS_ACCESS_KEY_ID` | No | None | Legacy AWS key (kept for backwards compat) |
| `AWS_SECRET_ACCESS_KEY` | No | None | Legacy AWS secret |
| `AWS_S3_BUCKET` | No | None | Legacy S3 bucket name |

## Payments (`config.py`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `STRIPE_SECRET_KEY` | Conditional | None | Stripe secret key (required for payments) |

## Token Economy (`config.py`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DAILY_FREE_TOKENS` | No | `2` | Number of free tokens granted daily |

## Azure Speech Services

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SPEECH_KEY` | Conditional | None | Azure Speech Services API key (required for audio gen) |
| `SPEECH_REGION` | Conditional | None | Azure region (e.g., `eastus`) |

## Test Generation Pipeline (`services/test_generation/config.py`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TEST_GEN_BATCH_SIZE` | No | `50` | Number of tests to generate per batch run |
| `TEST_GEN_QUESTIONS` | No | `5` | Questions per test |
| `TEST_GEN_PROSE_MODEL` | No | `google/gemini-2.0-flash-exp` | LLM model for prose/transcript generation |
| `TEST_GEN_QUESTION_MODEL` | No | `google/gemini-2.0-flash-exp` | LLM model for question generation |
| `TEST_GEN_PROSE_TEMP` | No | `0.9` | Temperature for prose generation |
| `TEST_GEN_QUESTION_TEMP` | No | `0.7` | Temperature for question generation |
| `TEST_GEN_TTS_MODEL` | No | `tts-1` | TTS model identifier |
| `TEST_GEN_TTS_VOICE` | No | `alloy` | Default TTS voice |
| `TEST_GEN_TTS_SPEED` | No | `1.0` | TTS playback speed multiplier |
| `TEST_GEN_MAX_RETRIES` | No | `3` | Max retry attempts per agent operation |
| `TEST_GEN_RETRY_DELAY` | No | `2.0` | Seconds between retries |
| `TEST_GEN_DRY_RUN` | No | `false` | Run without DB writes (`true`/`false`) |
| `TEST_GEN_LOG_LEVEL` | No | `INFO` | Logging level for test generation |
| `TEST_GEN_SYSTEM_USER_ID` | No | `de6fd05b-0871-45d4-a2d8-0195fdf5355e` | UUID credited as test creator |
| `TEST_GEN_TARGET_DIFFICULTIES` | No | `[1, 3, 6, 9]` | JSON array of difficulty levels to generate |

## Topic Generation Pipeline (`services/topic_generation/config.py`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TOPIC_DAILY_QUOTA` | No | `5` | Topics to generate per daily run |
| `TOPIC_SIMILARITY_THRESHOLD` | No | `0.85` | Cosine similarity threshold for deduplication (0.5-1.0) |
| `TOPIC_MAX_CANDIDATES` | No | `10` | Max topic candidates per generation run |
| `TOPIC_LLM_MODEL` | No | `google/gemini-2.0-flash-exp` | LLM model for topic exploration/validation |
| `TOPIC_LLM_TEMPERATURE` | No | `0.8` | Temperature for topic LLM calls |
| `TOPIC_EMBEDDING_MODEL` | No | `text-embedding-3-small` | OpenAI embedding model |
| `TOPIC_GATEKEEPER_TEMPERATURE` | No | `0.3` | Temperature for cultural validation (low = more conservative) |
| `TOPIC_GATEKEEPER_SHORT_CIRCUIT` | No | `3` | Max consecutive rejections before skipping |
| `TOPIC_DRY_RUN` | No | `false` | Run without DB writes |
| `TOPIC_LOG_LEVEL` | No | `INFO` | Logging level for topic generation |

## Server (`wsgi.py`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | No | `8080` | Server port for production deployment |

## Minimum Required for Local Development

```env
# Database (required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Auth (required)
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# AI (required for test/topic generation)
OPENAI_API_KEY=sk-...

# Optional but recommended
USE_OPENROUTER=true
OPENROUTER_API_KEY=sk-or-...
FLASK_DEBUG=true

# Audio generation (optional)
SPEECH_KEY=your-azure-speech-key
SPEECH_REGION=eastus
R2_ACCESS_KEY_ID=your-r2-key
R2_SECRET_ACCESS_KEY=your-r2-secret
R2_ACCOUNT_ID=your-account-id

# Payments (optional for dev)
STRIPE_SECRET_KEY=sk_test_...
```

## Related Documents
- [Config Reference](../04-Backend/02-config-reference.md)
- [Environment Setup](../01-Overview/04-environment-setup.md)
- [Test Generation Config](../05-Pipelines/01-test-generation/04-config.md)
- [Topic Generation Config](../05-Pipelines/02-topic-generation/04-config.md)
