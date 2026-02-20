# Config Reference

Complete reference for `config.py`. The `Config` class is the single source of truth for all application configuration. Values are loaded from environment variables (via `.env` file) with hardcoded defaults where appropriate.

**File**: `config.py`

---

## Configuration Table

### Core Settings

| Variable | Type | Env Var | Default | Description |
|----------|------|---------|---------|-------------|
| `SECRET_KEY` | `str` | `SECRET_KEY` | `'temp-secret-change-in-production'` | Flask secret key for session signing |
| `DEBUG` | `bool` | `FLASK_DEBUG` | `False` | Enable Flask debug mode. Parsed from string `'true'`/`'false'`. |

### JWT Settings

| Variable | Type | Env Var | Default | Description |
|----------|------|---------|---------|-------------|
| `JWT_SECRET_KEY` | `str` | `JWT_SECRET_KEY` | `'jwt-secret-change-in-production'` | Secret key for JWT signing (flask-jwt-extended) |
| `JWT_ACCESS_TOKEN_EXPIRES` | `timedelta` | - | `timedelta(hours=24)` | JWT token expiry duration. Hardcoded. |
| `JWT_TOKEN_LOCATION` | `list[str]` | - | `["headers", "cookies"]` | Where flask-jwt-extended looks for tokens. Hardcoded. |

### CORS

| Variable | Type | Env Var | Default | Description |
|----------|------|---------|---------|-------------|
| `CORS_ORIGINS` | `list[str]` | `CORS_ORIGINS` | `['http://localhost:49640', 'http://localhost:3000', 'http://localhost:5000']` | Comma-separated list of allowed origins. Parsed and stripped. |

### AI Service Configuration

| Variable | Type | Env Var | Default | Description |
|----------|------|---------|---------|-------------|
| `USE_OPENROUTER` | `bool` | `USE_OPENROUTER` | `False` | Enable OpenRouter as LLM gateway instead of direct OpenAI |
| `OPENROUTER_API_KEY` | `str` | `OPENROUTER_API_KEY` | `''` | OpenRouter API key |
| `OPENAI_API_KEY` | `str` | `OPENAI_API_KEY` | `None` | OpenAI API key (used for direct API calls, TTS, embeddings) |
| `AI_MODELS` | `dict` | - | See below | Language-specific model mapping for OpenRouter. Hardcoded. |
| `DEFAULT_AI_MODEL` | `str` | - | `'gpt-4o-mini'` | Fallback model when OpenRouter is disabled or language not found. Hardcoded. |

**AI_MODELS structure:**

```python
AI_MODELS = {
    'english': {
        'transcript': 'google/gemini-2.0-flash-001',
        'questions': 'google/gemini-2.0-flash-001'
    },
    'chinese': {
        'transcript': 'deepseek/deepseek-chat',
        'questions': 'deepseek/deepseek-chat'
    },
    'japanese': {
        'transcript': 'qwen/qwen-2.5-72b-instruct',
        'questions': 'qwen/qwen-2.5-72b-instruct'
    }
}
```

### Database (Supabase)

| Variable | Type | Env Var | Default | Description |
|----------|------|---------|---------|-------------|
| `SUPABASE_URL` | `str` | `SUPABASE_URL` | `None` | Supabase project URL |
| `SUPABASE_KEY` | `str` | `SUPABASE_KEY` | `None` | Supabase anon (public) key. Used for RLS-protected operations. |
| `SUPABASE_SERVICE_ROLE_KEY` | `str` | `SUPABASE_SERVICE_ROLE_KEY` | `None` | Supabase service role key. Bypasses RLS. Used for admin operations. |

### Language Configuration

| Variable | Type | Env Var | Default | Description |
|----------|------|---------|---------|-------------|
| `LANGUAGES` | `dict` | - | `{1: {code:'cn', ...}, 2: {code:'en', ...}, 3: {code:'jp', ...}}` | Language registry. Hardcoded. |
| `VALID_LANGUAGE_IDS` | `set` | - | `{1, 2, 3}` | Derived from `LANGUAGES.keys()` |
| `LANGUAGE_ID_TO_NAME` | `dict` | - | `{1:'chinese', 2:'english', 3:'japanese'}` | Derived lookup: id -> name |
| `LANGUAGE_CODE_TO_ID` | `dict` | - | `{'cn':1, 'en':2, 'jp':3}` | Derived lookup: code -> id |

**LANGUAGES structure:**

```python
LANGUAGES = {
    1: {'code': 'cn', 'name': 'chinese', 'display': 'Chinese'},
    2: {'code': 'en', 'name': 'english', 'display': 'English'},
    3: {'code': 'jp', 'name': 'japanese', 'display': 'Japanese'},
}
```

### Token Economy

| Variable | Type | Env Var | Default | Description |
|----------|------|---------|---------|-------------|
| `TOKEN_COSTS` | `dict` | - | `{'take_test': 1, 'generate_test': 5}` | Token cost per action. Hardcoded. |
| `DAILY_FREE_TOKENS` | `int` | `DAILY_FREE_TOKENS` | `2` | Free tokens granted daily on first API call of the day |
| `TOKEN_PACKAGES` | `dict` | - | See below | Purchasable token packages. Hardcoded. |

**TOKEN_PACKAGES structure:**

```python
TOKEN_PACKAGES = {
    'starter_10':  {'tokens': 10,  'price_cents': 199,  'description': 'Starter pack'},
    'popular_50':  {'tokens': 50,  'price_cents': 799,  'description': 'Most popular'},
    'premium_200': {'tokens': 200, 'price_cents': 1999, 'description': 'Best value'},
}
```

### Payments (Stripe)

| Variable | Type | Env Var | Default | Description |
|----------|------|---------|---------|-------------|
| `STRIPE_SECRET_KEY` | `str` | `STRIPE_SECRET_KEY` | `None` | Stripe secret API key for server-side payment processing |

### Storage (Cloudflare R2)

| Variable | Type | Env Var | Default | Description |
|----------|------|---------|---------|-------------|
| `R2_ACCESS_KEY_ID` | `str` | `R2_ACCESS_KEY_ID` | `None` | R2 access key ID |
| `R2_SECRET_ACCESS_KEY` | `str` | `R2_SECRET_ACCESS_KEY` | `None` | R2 secret access key |
| `R2_ACCOUNT_ID` | `str` | `R2_ACCOUNT_ID` | `None` | Cloudflare account ID |
| `R2_BUCKET_NAME` | `str` | `R2_BUCKET_NAME` | `'linguadojoaudio'` | R2 bucket name for audio files |
| `R2_ENDPOINT_URL` | `str` | - | `'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com'` | Derived S3-compatible endpoint URL. `None` if `R2_ACCOUNT_ID` not set. |
| `R2_PUBLIC_URL` | `str` | `R2_PUBLIC_URL` | `'https://audio.linguadojo.com'` | Public CDN URL for serving audio files |

### Legacy AWS (Backwards Compatibility)

| Variable | Type | Env Var | Default | Description |
|----------|------|---------|---------|-------------|
| `AWS_ACCESS_KEY_ID` | `str` | `AWS_ACCESS_KEY_ID` | `None` | Legacy AWS access key |
| `AWS_SECRET_ACCESS_KEY` | `str` | `AWS_SECRET_ACCESS_KEY` | `None` | Legacy AWS secret key |
| `AWS_S3_BUCKET` | `str` | `AWS_S3_BUCKET` | `None` | Legacy S3 bucket name |

---

## Helper Methods

### `Config.get_audio_url(slug: str) -> str`

Constructs a full audio URL from a test slug.

```python
Config.get_audio_url('daily-life-tokyo-b1')
# Returns: 'https://audio.linguadojo.com/daily-life-tokyo-b1.mp3'
```

### `Config.get_model_for_language(language: str, task: str = 'transcript') -> str`

Returns the optimal LLM model for a given language and task. Falls back to `DEFAULT_AI_MODEL` when OpenRouter is disabled.

```python
# With USE_OPENROUTER=true
Config.get_model_for_language('chinese', 'transcript')
# Returns: 'deepseek/deepseek-chat'

# With USE_OPENROUTER=false
Config.get_model_for_language('chinese', 'transcript')
# Returns: 'gpt-4o-mini'

# Unknown language falls back to english config
Config.get_model_for_language('korean', 'transcript')
# Returns: 'google/gemini-2.0-flash-001'
```

### `Config.get_language_name(language_id: int) -> str`

Converts a language ID to its internal name.

```python
Config.get_language_name(1)   # Returns: 'chinese'
Config.get_language_name(3)   # Returns: 'japanese'
Config.get_language_name(99)  # Returns: 'unknown'
```

### `Config.get_language_id(code: str) -> int`

Converts a language code to its ID.

```python
Config.get_language_id('cn')  # Returns: 1
Config.get_language_id('jp')  # Returns: 3
Config.get_language_id('xx')  # Returns: 1 (default fallback)
```

---

## Environment Variable Summary

All environment variables consumed by Config, in alphabetical order:

| Env Var | Required | Sensitive |
|---------|----------|-----------|
| `AWS_ACCESS_KEY_ID` | No | Yes |
| `AWS_S3_BUCKET` | No | No |
| `AWS_SECRET_ACCESS_KEY` | No | Yes |
| `CORS_ORIGINS` | No | No |
| `DAILY_FREE_TOKENS` | No | No |
| `FLASK_DEBUG` | No | No |
| `JWT_SECRET_KEY` | Production | Yes |
| `OPENAI_API_KEY` | Yes | Yes |
| `OPENROUTER_API_KEY` | If using OpenRouter | Yes |
| `R2_ACCESS_KEY_ID` | If using R2 | Yes |
| `R2_ACCOUNT_ID` | If using R2 | No |
| `R2_BUCKET_NAME` | No | No |
| `R2_PUBLIC_URL` | No | No |
| `R2_SECRET_ACCESS_KEY` | If using R2 | Yes |
| `SECRET_KEY` | Production | Yes |
| `STRIPE_SECRET_KEY` | If using payments | Yes |
| `SUPABASE_KEY` | Yes | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Yes |
| `SUPABASE_URL` | Yes | No |
| `USE_OPENROUTER` | No | No |

---

## Related Documents

- [App Entrypoint](./01-app-entrypoint.md) - How config is loaded and used during app initialization.
- [Design Patterns](../02-Architecture/04-design-patterns.md) - Singleton and factory patterns that consume config.
- [Security Model](../02-Architecture/06-security-model.md) - Security-related configuration values.
