# Auth Middleware

Detailed reference for `middleware/auth.py`, which provides authentication and authorization decorators for Flask route handlers.

**File**: `middleware/auth.py`

---

## Overview

The auth middleware module provides two styles of authentication:

1. **Standalone decorators** (preferred for new code): Module-level functions that use `SupabaseFactory` for client access.
2. **Class-based middleware** (legacy compatibility): `AuthMiddleware` class that receives a Supabase client via constructor injection.

Both styles provide the same three decorators: `jwt_required`, `admin_required`, and `tier_required`.

---

## Standalone Decorators

### @jwt_required

The primary authentication decorator. Extracts the JWT from the `Authorization` header, validates it with Supabase Auth, and populates Flask's `g` object with user context.

**Usage:**

```python
from middleware.auth import jwt_required

@app.route('/api/users/profile', methods=['GET'])
@jwt_required
def get_user_profile():
    user_id = g.supabase_claims.get('sub')
    # user_id is guaranteed to be set if we reach this point
```

**Behavior:**

1. Calls `_extract_token(request)` to get the Bearer token.
2. If no token found, returns `401 {"error": "Token missing"}`.
3. Checks if the token matches `SUPABASE_SERVICE_ROLE_KEY` (see [Service Role Bypass](#service-role-bypass)).
4. Calls `supabase.auth.get_user(token)` to validate the JWT with Supabase Auth.
5. If validation fails, returns `401 {"error": "Invalid or expired token"}` or `401 {"error": "Invalid token"}`.
6. On success, sets context variables on `g` (see [Context Variables](#context-variables-set)).

### @admin_required

Restricts access to users with `subscription_tier` in `['admin', 'moderator']`.

**Usage:**

```python
from middleware.auth import admin_required

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def list_all_users():
    # Only admin and moderator users reach this code
```

**Behavior:**

1. Extracts and validates the JWT token (same as `jwt_required`).
2. Queries the `users` table using the **admin client** (bypasses RLS) to fetch the user's `subscription_tier`.
3. If tier is not `'admin'` or `'moderator'`, returns `403 {"error": "Admin access required"}`.
4. On success, sets `g.current_user_id` and `g.current_user`.

**Note:** This decorator does NOT set `g.supabase_claims`. If you need claims, use `@jwt_required` separately or access `g.current_user` directly.

### @tier_required(required_tiers)

Parameterized decorator for flexible subscription tier checks.

**Usage:**

```python
from middleware.auth import tier_required

@app.route('/api/premium/feature', methods=['GET'])
@tier_required(['premium', 'admin'])
def premium_feature():
    # Only premium and admin users reach this code
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `required_tiers` | `list[str]` | List of allowed subscription tier values |

**Behavior:**

1. Extracts and validates the JWT token.
2. Queries the `users` table using the admin client to fetch `subscription_tier`.
3. If the user's tier is not in `required_tiers`, returns `403 {"error": "Requires premium or admin access"}`.
4. On success, sets `g.current_user_id`.

**Available tiers:** `'free'`, `'premium'`, `'moderator'`, `'admin'`

---

## Service Role Bypass

The `@jwt_required` decorator supports a special case where the Bearer token is the Supabase service role key itself. This allows batch scripts and admin tools to call protected endpoints without a user JWT.

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

**When used:** Test generation scripts, topic generation scripts, and other server-side batch operations that need to call API endpoints.

**Note:** `@admin_required` and `@tier_required` do NOT support service role bypass. They always require a real user with a valid subscription tier.

---

## Context Variables Set

After successful authentication via `@jwt_required`, the following variables are available on Flask's `g` object for the duration of the request:

| Variable | Type | Description |
|----------|------|-------------|
| `g.current_user_id` | `str` (UUID) | The authenticated user's ID. Set to `'service-account'` for service role bypass. |
| `g.current_user` | `gotrue.User` | The full Supabase User object. Contains `id`, `email`, `created_at`, `app_metadata`, etc. Not set for service role bypass. |
| `g.user_id` | `str` (UUID) | Alias for `g.current_user_id`. Provided for backwards compatibility. |
| `g.supabase_claims` | `dict` | Dictionary with keys: `sub` (user ID), `email`, `role` (`'authenticated'` or `'service_role'`), `aud` (`'authenticated'`). |

**Accessing user ID in route handlers:**

```python
# Preferred: via claims
user_id = g.supabase_claims.get('sub')

# Also works: direct attribute
user_id = g.current_user_id
```

---

## Helper Functions

### _extract_token(req)

Extracts the JWT token from the `Authorization` header.

```python
def _extract_token(req):
    auth_header = req.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    return None
```

**Returns:** The token string, or `None` if the header is missing or malformed.

### _get_supabase_client()

Lazy-imports and returns the anon Supabase client from `SupabaseFactory`. Uses lazy import to avoid circular dependencies at module load time.

```python
def _get_supabase_client():
    from services.supabase_factory import get_supabase
    return get_supabase()
```

### _get_supabase_admin()

Lazy-imports and returns the service role Supabase client from `SupabaseFactory`.

```python
def _get_supabase_admin():
    from services.supabase_factory import get_supabase_admin
    return get_supabase_admin()
```

---

## Class-Based Middleware (Legacy)

The `AuthMiddleware` class provides the same functionality as the standalone decorators but is bound to a specific Supabase client instance passed via the constructor.

```python
class AuthMiddleware:
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.supabase_admin = _get_supabase_admin()

    def jwt_required(self, f): ...
    def admin_required(self, f): ...
    def tier_required(self, required_tiers): ...
```

**Usage in app.py:**

```python
auth_middleware = AuthMiddleware(app.supabase)
auth_bp.auth_middleware = auth_middleware

# In routes/auth.py:
@auth_bp.route('/some-endpoint')
@auth_bp.auth_middleware.jwt_required
def some_endpoint():
    ...
```

**Differences from standalone decorators:**
- Uses the instance's `self.supabase` client instead of calling `_get_supabase_client()`.
- The `jwt_required` method does NOT support service role bypass.
- The `jwt_required` method does NOT set `g.supabase_claims` or `g.user_id`.
- Only sets `g.current_user_id` and `g.current_user`.

**Recommendation:** Use standalone decorators for new code. The class-based middleware exists for backwards compatibility with the `auth_bp` blueprint.

---

## Error Responses

| Scenario | Status Code | Response Body |
|----------|-------------|---------------|
| No Authorization header | 401 | `{"error": "Token missing"}` |
| Invalid/expired JWT | 401 | `{"error": "Invalid or expired token"}` |
| Supabase Auth error | 401 | `{"error": "Invalid token"}` |
| Non-admin accessing admin route | 403 | `{"error": "Admin access required"}` |
| Wrong tier for tier-restricted route | 403 | `{"error": "Requires <tier1> or <tier2> access"}` |
| Admin/tier auth exception | 403 | `{"error": "Access denied"}` |

---

## Related Documents

- [Request Lifecycle](../../02-Architecture/02-request-lifecycle.md) - How auth middleware fits into the full request flow.
- [Security Model](../../02-Architecture/06-security-model.md) - Broader security context including RLS and token refresh.
- [App Entrypoint](../01-app-entrypoint.md) - How `AuthMiddleware` is instantiated and injected into blueprints.
- [Config Reference](../02-config-reference.md) - JWT and Supabase configuration values.
