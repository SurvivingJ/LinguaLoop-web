# App Entrypoint

Deep dive into `app.py`, the main entry point for the LinguaLoop Flask application.

**File**: `app.py`

---

## Overview

`app.py` defines the `create_app()` factory function and several private helper functions that configure the Flask application. The module also creates a module-level `app` instance and provides a `__main__` block for direct execution.

```python
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
```

---

## create_app(config_class=Config)

The application factory. Creates and fully configures a Flask application instance.

### Step 1: Create Flask Instance and Load Config

```python
app = Flask(__name__)
app.config.from_object(config_class)
```

Loads all attributes from the `Config` class into Flask's configuration dictionary.

### Step 2: Disable Strict Slashes

```python
app.url_map.strict_slashes = False
```

Prevents Flask from issuing `308 Permanent Redirect` when a URL is accessed without a trailing slash (e.g., `/api/tests` vs `/api/tests/`).

### Step 3: Set Secret Key

```python
app.secret_key = config_class.SECRET_KEY if hasattr(config_class, 'SECRET_KEY') else os.urandom(24)
```

Used for Flask session signing. Falls back to a random key if `SECRET_KEY` is not configured.

### Step 4: Configure Logging

```python
logging.basicConfig(
    level=logging.INFO if not config_class.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

Sets the root logger to `DEBUG` when `FLASK_DEBUG=true`, otherwise `INFO`.

### Step 5: Initialize JWTManager

```python
JWTManager(app)
```

Initializes `flask-jwt-extended` for JWT handling. Uses `JWT_SECRET_KEY`, `JWT_ACCESS_TOKEN_EXPIRES`, and `JWT_TOKEN_LOCATION` from config.

### Step 6: Setup CORS

Calls `_setup_cors(app)`. See [CORS Configuration](#_setup_corsapp) below.

### Step 7: Initialize Services

Calls `_initialize_services(app)`. See [Service Initialization](#_initialize_servicesapp) below.

### Step 8: Register Blueprints

Calls `_register_blueprints(app)`. See [Blueprint Registration](#_register_blueprintsapp) below.

### Step 9: Register Error Handlers

Calls `_register_error_handlers(app)`. See [Error Handlers](#_register_error_handlersapp) below.

### Step 10: Register Routes

Calls `_register_core_routes(app)` and `_register_web_routes(app)`. See route sections below.

---

## _setup_cors(app)

Configures CORS for all `/api/*` routes.

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

Also registers a `@app.before_request` handler for `OPTIONS` preflight requests that returns appropriate CORS headers immediately. The handler checks the `Origin` header against `Config.CORS_ORIGINS` and sets `Access-Control-Allow-Origin` accordingly.

---

## _initialize_services(app)

Initializes all external services in dependency order. Each initialization is wrapped in try/except so that a single failure does not prevent the app from starting.

### Supabase Clients

```python
SupabaseFactory.initialize(
    supabase_url=Config.SUPABASE_URL,
    supabase_key=Config.SUPABASE_KEY,
    service_role_key=Config.SUPABASE_SERVICE_ROLE_KEY
)
app.supabase = get_supabase()           # Anon client (respects RLS)
app.supabase_service = get_supabase_admin()  # Service client (bypasses RLS)
```

### AuthService

```python
app.auth_service = AuthService(app.supabase)
```

Handles OTP login, token refresh, and user creation.

### DimensionService + TestService

```python
DimensionService.initialize(app.supabase_service)
app.test_service = get_test_service()
```

`DimensionService` pre-loads `dim_languages` and `dim_test_types` into in-memory caches. `TestService` is retrieved as a singleton.

### ServiceFactory + AIService

```python
service_factory = ServiceFactory(Config)
app.service_factory = service_factory
app.openai_service = service_factory.openai_service if Config.OPENAI_API_KEY else None
```

`ServiceFactory` lazy-loads `AIService`, `PromptService`, and `R2Service` via `@property`.

### R2Service

```python
app.r2_service = R2Service(Config) if Config.R2_ACCESS_KEY_ID else None
```

### Stripe

```python
if Config.STRIPE_SECRET_KEY:
    stripe.api_key = Config.STRIPE_SECRET_KEY
```

Sets the global Stripe API key. No Stripe client object is stored on `app`.

### PromptService

```python
app.prompt_service = PromptService()
```

Loads prompt templates from the filesystem.

### App Attributes Summary

After initialization, the following attributes are available on the `app` object:

| Attribute | Type | Can be None |
|-----------|------|-------------|
| `app.supabase` | `supabase.Client` | Yes (if credentials missing) |
| `app.supabase_service` | `supabase.Client` | Yes (if service role key missing) |
| `app.auth_service` | `AuthService` | Yes |
| `app.test_service` | `TestService` | Yes |
| `app.service_factory` | `ServiceFactory` | Yes |
| `app.openai_service` | `AIService` | Yes (if no API key) |
| `app.r2_service` | `R2Service` | Yes (if no R2 credentials) |
| `app.prompt_service` | `PromptService` | Yes |

---

## _register_blueprints(app)

Registers Flask blueprints and injects dependencies.

```python
auth_middleware = AuthMiddleware(app.supabase)
auth_bp.auth_service = app.auth_service
auth_bp.auth_middleware = auth_middleware

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(tests_bp, url_prefix='/api/tests')
app.register_blueprint(reports_bp, url_prefix='/api/reports')
```

| Blueprint | URL Prefix | File |
|-----------|-----------|------|
| `auth_bp` | `/api/auth` | `routes/auth.py` |
| `tests_bp` | `/api/tests` | `routes/tests.py` |
| `reports_bp` | `/api/reports` | `routes/reports.py` |

The `auth_bp` blueprint receives `auth_service` and `auth_middleware` as attributes for dependency injection.

---

## _register_error_handlers(app)

Registers global error handlers for HTTP error codes.

### 404 Not Found

- **API requests** (`/api/*`): Returns JSON `{"error": "Endpoint not found", "status": "not_found"}`
- **Web requests**: Redirects to login page via `redirect(url_for('login'))`

### 405 Method Not Allowed

Returns JSON for all requests: `{"error": "Method not allowed", "status": "method_not_allowed"}`

### 500 Internal Server Error

- Logs the error and full traceback
- **API requests** (`/api/*`): Returns JSON `{"error": "Internal server error", "status": "internal_error"}`
- **Web requests**: Renders `error.html` template

---

## _register_core_routes(app)

Registers API routes directly on the app (not via blueprints).

| Route | Method | Auth | Description |
|-------|--------|------|-------------|
| `/api/health` | GET | None | Health check. Returns service status for all integrations. |
| `/api/config` | GET | None | Public configuration (feature flags, token costs, daily free tokens). |
| `/api/metadata` | GET | None | Available languages and test types from DimensionService cache. |
| `/api/users/elo` | GET | `@jwt_required` | User's ELO ratings across all languages and skills. |
| `/api/users/tokens` | GET | `@jwt_required` | User's token balance. Grants daily free tokens if applicable. |
| `/api/users/profile` | GET | `@jwt_required` | Full user profile (sensitive fields stripped). |
| `/api/tests/history` | GET | `@jwt_required` | Paginated test attempt history with manual join across tables. |
| `/api/payments/token-packages` | GET | None | Available token packages with pricing. |
| `/api/payments/create-intent` | POST | `@jwt_required` | Creates a Stripe PaymentIntent for token purchase. |

---

## _register_web_routes(app)

Registers HTML page routes that render Jinja2 templates.

| Route | Template | Description |
|-------|----------|-------------|
| `/` | - | Redirects to `/login` |
| `/login` | `login.html` | Login page |
| `/signup` | `login.html` | Signup page (shares login template) |
| `/welcome` | `onboarding.html` | New user onboarding |
| `/language-selection` | `language_selection.html` | Language picker |
| `/tests` | `test_list.html` | Test catalog |
| `/profile` | `profile.html` | User profile page |
| `/test/<slug>/preview` | `test_preview.html` | Test preview (client-side rendered) |
| `/test/<slug>` | `test.html` | Test taking page (client-side rendered) |
| `/logout` | - | Redirects to `/login` |

All web routes serve HTML. Authentication and data fetching happen client-side via JavaScript calling the `/api/*` endpoints.

---

## Related Documents

- [Config Reference](./02-config-reference.md) - All configuration variables loaded by `create_app()`.
- [Auth Middleware](./04-middleware/01-auth-middleware.md) - Authentication decorators used by core routes.
- [System Architecture](../02-Architecture/01-system-architecture.md) - How `app.py` fits in the overall system.
- [Service Dependency Graph](../02-Architecture/03-service-dependency-graph.md) - Initialization order and dependencies.
