# Security Model

This document describes the authentication, authorization, and data access controls in LinguaLoop.

---

## 1. Authentication Flow

LinguaLoop uses passwordless OTP (One-Time Password) authentication via Supabase Auth.

```
User enters email
    -> Supabase sends OTP to email
    -> User enters OTP
    -> Supabase Auth returns JWT (access_token) + refresh_token
    -> Client stores both in localStorage
    -> All subsequent API requests include: Authorization: Bearer <jwt>
```

**Token characteristics:**
- **Format**: Standard JWT signed by Supabase
- **Expiry**: 24 hours (`JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)`)
- **Storage**: `localStorage` on the client side
- **Transport**: Sent in the `Authorization: Bearer <token>` header on every API request

---

## 2. Token Validation

Every protected endpoint uses the `@jwt_required` decorator from `middleware/auth.py`.

**Validation sequence:**

```python
# 1. Extract token from Authorization header
token = _extract_token(request)
# Returns None if header missing or malformed -> 401

# 2. Check for service role key bypass (see section 3)
if service_role_key and token == service_role_key:
    # Set service-account identity and skip Supabase Auth
    return f(*args, **kwargs)

# 3. Validate with Supabase Auth
supabase = _get_supabase_client()
user_response = supabase.auth.get_user(token)
# Makes HTTPS call to Supabase -> returns User object or raises exception

# 4. Set request context
g.current_user_id = user_response.user.id    # UUID string
g.current_user = user_response.user           # Full User object
g.user_id = user_response.user.id             # Alias
g.supabase_claims = {
    'sub': user_response.user.id,
    'email': user_response.user.email,
    'role': 'authenticated',
    'aud': 'authenticated'
}
```

**Failure responses:**
- Missing token: `401 {"error": "Token missing"}`
- Invalid/expired token: `401 {"error": "Invalid or expired token"}`
- Supabase Auth unreachable: `401 {"error": "Invalid token"}`

---

## 3. Service Role Bypass

Batch scripts and admin tools can authenticate using the Supabase service role key instead of a user JWT. This is checked before calling Supabase Auth.

```python
service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
if service_role_key and token == service_role_key:
    g.supabase_claims = {
        'sub': 'service-account',
        'role': 'service_role',
        'email': 'batch-service@internal'
    }
    g.current_user_id = 'service-account'
    g.user_id = 'service-account'
    return f(*args, **kwargs)
```

**When used:**
- Test generation pipeline scripts
- Topic generation pipeline scripts
- Administrative batch operations

**Security considerations:**
- The service role key must be kept secret and never exposed to the client
- It bypasses all Supabase RLS policies
- It is stored as an environment variable (`SUPABASE_SERVICE_ROLE_KEY`)
- Requests using this key are identifiable by `g.current_user_id == 'service-account'`

---

## 4. Authorization Tiers

User authorization is based on the `subscription_tier` column in the `users` table.

| Tier | Description | Access Level |
|------|-------------|-------------|
| `free` | Default tier for new users | Standard features, daily token allowance |
| `premium` | Paid subscribers | Premium features, higher limits |
| `moderator` | Content moderators | Admin panel access |
| `admin` | System administrators | Full admin panel access |

### @admin_required

Restricts access to users with `subscription_tier` in `['admin', 'moderator']`.

```python
@app.route('/api/admin/users', methods=['GET'])
@admin_required
def list_users():
    # Only admin and moderator users reach this code
```

**Implementation**: After validating the JWT, queries the `users` table using the admin client (to bypass RLS) and checks the `subscription_tier` field.

### @tier_required(required_tiers)

Flexible tier-based access control accepting a list of allowed tiers.

```python
@app.route('/api/premium/feature', methods=['GET'])
@tier_required(['premium', 'admin'])
def premium_feature():
    # Only premium and admin users reach this code
```

**Failure response**: `403 {"error": "Requires premium or admin access"}`

**Note**: Both decorators use the admin Supabase client (`get_supabase_admin()`) to query the `users` table, bypassing RLS to ensure the tier check always succeeds regardless of the user's own RLS policies.

---

## 5. Row-Level Security (RLS)

Supabase PostgreSQL enforces Row-Level Security policies on all tables. LinguaLoop uses two clients with different RLS behavior:

| Client | Variable | RLS | Used For |
|--------|----------|-----|----------|
| **Anon Client** | `SupabaseFactory._anon_client` | Enforced | User-context operations: reading own tests, submitting answers, profile queries |
| **Service Client** | `SupabaseFactory._service_client` | Bypassed | Admin operations: user lookups for tier checks, batch processing, cross-user queries, dimension table pre-loading |

**Examples of RLS-protected operations (anon client):**
- `GET /api/users/tokens` - User can only read their own token balance
- `GET /api/users/profile` - User can only read their own profile
- `GET /api/tests/recommended` - RLS filters tests by user's language preferences

**Examples of RLS-bypassed operations (service client):**
- `DimensionService.initialize()` - Pre-loads dimension tables (no user context)
- `@admin_required` tier check - Reads any user's `subscription_tier`
- `TestDatabaseClient` / `TopicDatabaseClient` - Batch generation scripts writing tests and topics
- `GET /api/tests/history` - Uses service client to join across `test_attempts` and `tests` tables

---

## 6. Token Refresh

When the JWT approaches expiration, the client can request a new token pair using the refresh token.

```
POST /api/auth/refresh-token
Body: {"refresh_token": "<refresh_token>"}
```

**Server-side flow:**

```python
# In routes/auth.py
result = supabase.auth.refresh_session(refresh_token)
# Returns new access_token + new refresh_token
```

**Response:**
```json
{
    "status": "success",
    "session": {
        "access_token": "<new-jwt>",
        "refresh_token": "<new-refresh-token>",
        "expires_in": 86400
    }
}
```

The client stores the new tokens in `localStorage` and uses the new JWT for subsequent requests. The old refresh token is invalidated.

**Silent refresh**: The frontend JavaScript attempts token refresh proactively before expiration. If the refresh fails (e.g., refresh token expired), the user is redirected to the login page.

---

## 7. Content Moderation

User-submitted content (custom topics, feedback) is checked via the OpenAI Moderation API before processing.

```python
# In AIService
moderation_result = self.client.moderations.create(input=user_content)
if moderation_result.results[0].flagged:
    raise ContentModerationError("Content flagged by moderation API")
```

This prevents inappropriate content from being used as input to the generation pipelines.

---

## 8. CORS Configuration

Cross-Origin Resource Sharing is configured to restrict which origins can make API requests.

**File**: `app.py` (`_setup_cors()`)

```python
CORS(app, resources={
    r"/api/*": {
        "origins": Config.CORS_ORIGINS,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"],
        "supports_credentials": True,
        "max_age": 86400
    }
})
```

**Configuration:**
- **Origins**: Set via `CORS_ORIGINS` environment variable. Defaults to `http://localhost:49640`, `http://localhost:3000`, `http://localhost:5000`.
- **Scope**: Only `/api/*` routes have CORS headers. Static assets and HTML pages are served same-origin.
- **Credentials**: Enabled (`supports_credentials: True`) to allow cookies and Authorization headers.
- **Preflight caching**: 24 hours (`max_age: 86400`).

**Preflight handling**: A `@app.before_request` handler catches `OPTIONS` requests and returns appropriate CORS headers immediately, preventing them from reaching route handlers.

---

## Security Checklist

| Control | Status | Notes |
|---------|--------|-------|
| Passwordless auth (OTP) | Implemented | No password storage required |
| JWT validation on every request | Implemented | Via `@jwt_required` decorator |
| Token expiry | 24 hours | Configurable via `JWT_ACCESS_TOKEN_EXPIRES` |
| Refresh token rotation | Implemented | Old refresh token invalidated on use |
| RLS on all tables | Implemented | Via Supabase PostgreSQL policies |
| Admin tier checks | Implemented | `@admin_required`, `@tier_required` |
| Service role key isolation | Implemented | Server-side only, never sent to client |
| CORS origin restriction | Implemented | Configurable via env var |
| Content moderation | Implemented | OpenAI Moderation API |
| Secrets in env vars | Implemented | All API keys, service keys via `.env` |

---

## Related Documents

- [Request Lifecycle](./02-request-lifecycle.md) - How authentication fits into the request flow.
- [Auth Middleware](../04-Backend/04-middleware/01-auth-middleware.md) - Detailed API reference for authentication decorators.
- [Config Reference](../04-Backend/02-config-reference.md) - Environment variables for security configuration.
