# Request Lifecycle

This document traces the full lifecycle of an authenticated API request through the LinguaLoop backend, using `GET /api/tests/recommended` as a concrete example.

---

## Sequence Diagram

```mermaid
sequenceDiagram
    participant B as Browser
    participant F as Flask App
    participant M as Middleware (jwt_required)
    participant S as Supabase Auth
    participant R as Route Handler
    participant SV as Service Layer
    participant DB as Supabase DB

    B->>F: GET /api/tests/recommended (Authorization: Bearer <jwt>)
    F->>M: @jwt_required decorator
    M->>M: Extract token from Authorization header
    M->>S: supabase.auth.get_user(token)
    S-->>M: User object (id, email)
    M->>M: Set g.current_user_id, g.supabase_claims
    M->>R: Pass to route handler
    R->>SV: Get recommended tests
    SV->>DB: RPC: get_recommended_tests(user_id, language_id)
    DB-->>SV: Test data
    SV-->>R: Formatted response
    R-->>B: JSON {status: "success", data: [...]}
```

---

## Step-by-Step Breakdown

### 1. Browser Sends Request

The browser (or any HTTP client) sends a request with the JWT token in the `Authorization` header:

```
GET /api/tests/recommended HTTP/1.1
Host: app.lingualoop.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: application/json
```

The JWT was obtained during login via Supabase OTP authentication and stored in `localStorage` on the client side.

### 2. Flask Receives the Request

Flask's URL routing matches `/api/tests/recommended` to the corresponding route handler in `routes/tests.py` (registered via the `tests_bp` blueprint with prefix `/api/tests`).

Before the route handler executes, the `@jwt_required` decorator (from `middleware/auth.py`) intercepts the request.

### 3. Middleware: Token Extraction

The `_extract_token(request)` helper extracts the token from the `Authorization` header:

```python
def _extract_token(req):
    auth_header = req.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    return None
```

If no token is found, the middleware immediately returns a `401` response:

```json
{"error": "Token missing"}
```

### 4. Middleware: Service Role Key Check

Before calling Supabase Auth, the middleware checks if the token matches the `SUPABASE_SERVICE_ROLE_KEY` environment variable. This allows batch scripts and admin tools to authenticate without a user JWT:

```python
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

### 5. Middleware: Supabase Auth Validation

For regular user tokens, the middleware calls Supabase Auth to validate the JWT:

```python
supabase = _get_supabase_client()
user_response = supabase.auth.get_user(token)
```

This makes an HTTPS call to Supabase's `auth.getUser()` endpoint, which:
- Verifies the JWT signature
- Checks token expiration (24-hour window)
- Returns the full user object if valid

### 6. Middleware: Set Request Context

On successful validation, the middleware populates Flask's `g` object with user context:

```python
g.current_user_id = user_response.user.id   # UUID string
g.current_user = user_response.user          # Full Supabase User object
g.user_id = user_response.user.id            # Alias
g.supabase_claims = {
    'sub': user_response.user.id,
    'email': user_response.user.email,
    'role': 'authenticated',
    'aud': 'authenticated'
}
```

These values are available to all downstream code within the same request.

### 7. Route Handler Executes

The route handler is intentionally thin. It extracts query parameters, calls the appropriate service method, and formats the response:

```python
@tests_bp.route('/recommended', methods=['GET'])
@jwt_required
def get_recommended_tests():
    user_id = g.supabase_claims.get('sub')
    language_id = request.args.get('language_id', type=int)
    # ... call service, return JSON
```

### 8. Service Layer: Business Logic

The service layer (`TestService`) handles the actual business logic, including database queries, data transformation, and any cross-cutting concerns:

```python
# TestService calls Supabase RPC or queries
result = client.rpc('get_recommended_tests', {
    'p_user_id': user_id,
    'p_language_id': language_id
}).execute()
```

### 9. Database: Supabase PostgreSQL

The Supabase client sends a REST API call to the PostgreSQL database. Depending on which client is used:
- **Anon client**: Respects Row-Level Security (RLS) policies. The user can only see their own data.
- **Service client**: Bypasses RLS. Used for admin queries and cross-user operations.

### 10. Response Returned

The response flows back through the layers:

```json
{
    "status": "success",
    "data": [
        {
            "id": "uuid-here",
            "title": "Daily Life in Tokyo",
            "slug": "daily-life-in-tokyo-b1",
            "difficulty": 4,
            "language_id": 3
        }
    ]
}
```

---

## Error Paths

### 401 Unauthorized - Missing Token

```
Request: GET /api/tests/recommended (no Authorization header)
Response: 401 {"error": "Token missing"}
```

Occurs when the `Authorization` header is absent or does not start with `Bearer `.

### 401 Unauthorized - Invalid/Expired Token

```
Request: GET /api/tests/recommended (Authorization: Bearer <expired-jwt>)
Response: 401 {"error": "Invalid or expired token"}
```

Occurs when `supabase.auth.get_user(token)` fails, either because:
- The JWT signature is invalid
- The token has expired (past the 24-hour window)
- The user has been deleted or deactivated

### 403 Forbidden - Insufficient Tier

For routes protected by `@admin_required` or `@tier_required`:

```
Request: GET /api/admin/users (Authorization: Bearer <valid-free-tier-jwt>)
Response: 403 {"error": "Admin access required"}
```

Occurs when the user's `subscription_tier` in the `users` table does not match the required tier list.

### 500 Internal Server Error

```
Request: GET /api/tests/recommended (Authorization: Bearer <valid-jwt>)
Response: 500 {"error": "Internal server error", "status": "internal_error"}
```

Occurs when an unhandled exception is raised in the route handler or service layer. The error is logged with a full traceback via `app.logger.error()`. For API routes, a JSON error is returned. For web routes, `error.html` is rendered.

---

## CORS Handling

All `/api/*` requests pass through CORS middleware configured in `_setup_cors()`:

1. **Preflight (OPTIONS)**: The `handle_preflight` before-request handler returns appropriate CORS headers immediately without invoking the route handler.
2. **Allowed Origins**: Configured via the `CORS_ORIGINS` environment variable. Defaults to `localhost` on ports 49640, 3000, and 5000.
3. **Credentials**: `supports_credentials: True` allows cookies and Authorization headers.
4. **Max Age**: Preflight responses are cached for 86400 seconds (24 hours).

---

## Related Documents

- [System Architecture](./01-system-architecture.md) - Overall system structure and external dependencies.
- [Auth Middleware](../04-Backend/04-middleware/01-auth-middleware.md) - Detailed documentation of the authentication decorators.
- [Security Model](./06-security-model.md) - Token validation, RLS, and authorization tiers.
