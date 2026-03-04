# Coding Conventions

> Source references: `config.py`, `app.py`, `middleware/auth.py`, `routes/tests.py`, `routes/auth.py`, `routes/reports.py`, `static/js/utils.js`, `services/test_generation/config.py`, `services/topic_generation/config.py`

---

## 1. Python Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Files/modules | `snake_case` | `auth_service.py`, `test_generation/` |
| Classes | `PascalCase` | `AuthService`, `TestGenConfig` |
| Functions/methods | `snake_case` | `get_test_by_slug()`, `send_otp()` |
| Constants | `UPPER_SNAKE_CASE` | `VALID_LANGUAGE_IDS`, `DAILY_FREE_TOKENS` |
| Blueprint variables | `snake_case` with `_bp` suffix | `tests_bp`, `auth_bp`, `reports_bp` |
| Logger variables | Always `logger` | `logger = logging.getLogger(__name__)` |
| Private helpers | Leading underscore | `_extract_token()`, `_setup_cors()` |

---

## 2. Import Ordering

Imports follow a strict three-group convention separated by blank lines:

```python
# 1. Standard library
from functools import wraps
from datetime import datetime, timezone
from uuid import uuid4
import logging
import os

# 2. Third-party packages
from flask import Blueprint, request, jsonify, g
from flask_cors import CORS
import stripe

# 3. Internal/project modules
from config import Config
from middleware.auth import jwt_required
from services.test_service import TestService
```

Within each group, `from` imports appear before plain `import` statements. Lazy imports are used inside functions to avoid circular dependencies:

```python
def _get_supabase_client():
    """Lazy import to avoid circular deps"""
    from services.supabase_factory import get_supabase
    return get_supabase()
```

---

## 3. Configuration Pattern

The application uses a **Config class singleton** in `config.py` as the single source of truth for all settings:

```python
class Config:
    """Application configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'temp-secret-change-in-production')
    LANGUAGES = {
        1: {'code': 'cn', 'name': 'chinese', 'display': 'Chinese'},
        2: {'code': 'en', 'name': 'english', 'display': 'English'},
        3: {'code': 'jp', 'name': 'japanese', 'display': 'Japanese'},
    }

    @staticmethod
    def get_language_name(language_id: int) -> str:
        return Config.LANGUAGE_ID_TO_NAME.get(language_id, 'unknown')
```

Sub-system configurations (test generation, topic generation) use **Python dataclasses** with environment variable defaults and a module-level singleton:

```python
@dataclass
class TestGenConfig:
    batch_size: int = field(
        default_factory=lambda: int(os.getenv('TEST_GEN_BATCH_SIZE', '50'))
    )

    def validate(self) -> bool:
        """Check if all required configuration is present."""
        ...

# Module-level singleton
test_gen_config = TestGenConfig()
```

---

## 4. Blueprint Pattern

All routes are organized into Flask Blueprints registered in `app.py`:

```python
# Route file (routes/tests.py)
tests_bp = Blueprint("tests", __name__)

@tests_bp.route('/generate_test', methods=['POST'])
@supabase_jwt_required
def generate_test():
    ...

# Registration (app.py)
app.register_blueprint(tests_bp, url_prefix='/api/tests')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(reports_bp, url_prefix='/api/reports')
```

Services are attached to blueprints or the app object at registration time:

```python
def _register_blueprints(app):
    auth_bp.auth_service = app.auth_service
    auth_bp.auth_middleware = auth_middleware
```

---

## 5. Application Factory Pattern

The app uses Flask's factory pattern in `app.py`:

```python
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.url_map.strict_slashes = False

    _setup_cors(app)
    _initialize_services(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_core_routes(app)
    _register_web_routes(app)

    return app

app = create_app()
```

Each initialization step is a private function prefixed with `_`. Services are stored as app-level attributes (`app.supabase_service`, `app.openai_service`, etc.).

---

## 6. Data Models: Dataclasses

Pipeline data models use Python `dataclass` with optional fields and typed annotations:

```python
@dataclass
class GeneratedTest:
    id: UUID
    slug: str
    language_id: int
    difficulty: int
    transcript: str
    title: Optional[str] = None

@dataclass
class QueueItem:
    id: UUID
    topic_id: UUID
    language_id: int
    status_id: int
    created_at: datetime
    tests_generated: int = 0
    error_log: Optional[str] = None
```

---

## 7. Frontend JavaScript Conventions

### IIFE Pattern
Page-specific JavaScript uses immediately-invoked function expressions or self-contained `<script>` blocks. Shared utilities are exposed via a global namespace:

```javascript
window.LinguaUtils = {
    escapeHtml,
    getDifficultyLabel,
    apiGet,
    apiPost,
    ...
};
```

### Utility Functions
Shared client code lives in `static/js/utils.js` and follows these conventions:

- **Global namespace**: `window.LinguaUtils` object with all exports
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `ELO_RANGES`, `LANGUAGE_FLAGS`)
- **Functions**: `camelCase` (e.g., `getAuthHeaders()`, `apiRequest()`)
- **DOM helpers**: Use Bootstrap `d-none` class for visibility (`show()`, `hide()`, `toggle()`)
- **API calls**: Always use `getAuthHeaders()` which reads JWT from `localStorage`
- **Conditional debug logging**: `debugLog()` controlled by `DEBUG` constant

### Auth Token Storage
JWT tokens are stored in `localStorage` and read for every API call:

```javascript
function getAuthHeaders() {
    const token = localStorage.getItem('jwt_token') || LINGUADOJO.jwt_token;
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
    };
}
```

---

## 8. Authentication Decorators

Routes use standalone decorator functions from `middleware/auth.py`:

```python
from middleware.auth import jwt_required as supabase_jwt_required

@tests_bp.route('/generate_test', methods=['POST'])
@supabase_jwt_required
def generate_test():
    user_id = g.supabase_claims.get('sub')
    ...
```

Three decorator levels:
- `@jwt_required` -- Any authenticated user
- `@admin_required` -- `subscription_tier` in `['admin', 'moderator']`
- `@tier_required(['premium', 'admin'])` -- Specific subscription tiers

Authenticated user data is set on Flask's `g` object:
- `g.current_user_id` -- UUID string
- `g.current_user` -- Full Supabase user object
- `g.supabase_claims` -- Dict with `sub`, `email`, `role`

---

## 9. Logging Conventions

```python
import logging
logger = logging.getLogger(__name__)

# Levels used:
logger.debug(f"Test slug: {slug}")           # Internal detail
logger.info(f"Test saved: {slug}")            # Normal operations
logger.warning(f"Audio generation failed")     # Non-critical failures
logger.error(f"RPC call failed: {error}")      # Errors requiring attention
logger.exception(f"Generation run failed: {e}")# Error with stack trace
```

Logging format configured in `app.py`:
```python
logging.basicConfig(
    level=logging.INFO if not config_class.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

Pipeline orchestrators use visual separators for run boundaries:
```python
logger.info("=" * 60)
logger.info("Starting Test Generation Run")
logger.info("=" * 60)
```

---

## 10. Service Architecture

Services are initialized via a factory pattern and stored on the Flask `app` object:

| Attribute | Service | Purpose |
|---|---|---|
| `app.supabase` | Anon client | RLS-protected queries |
| `app.supabase_service` | Admin client | Bypasses RLS |
| `app.openai_service` | AI service | Transcript/question/audio generation |
| `app.r2_service` | R2Service | Cloudflare R2 audio storage |
| `app.auth_service` | AuthService | OTP auth |
| `app.prompt_service` | PromptService | Prompt template management |
| `app.test_service` | TestService | Test CRUD operations |

Each service initializes with error handling and logs its status:
```python
try:
    app.r2_service = R2Service(Config) if Config.R2_ACCESS_KEY_ID else None
    app.logger.info(f"R2 service: {'enabled' if app.r2_service else 'disabled'}")
except Exception as e:
    app.logger.error(f"R2 service error: {e}")
    app.r2_service = None
```

---

## Related Documents

- [02-error-handling.md](./02-error-handling.md) -- Error handling patterns
- [03-api-response-format.md](./03-api-response-format.md) -- API response conventions
- [05-assumptions-and-constraints.md](./05-assumptions-and-constraints.md) -- Technical constraints
