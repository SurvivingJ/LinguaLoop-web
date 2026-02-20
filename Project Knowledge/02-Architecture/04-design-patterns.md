# Design Patterns

This document catalogs the design patterns used throughout the LinguaLoop codebase, with code examples from the actual implementation.

---

## 1. Factory Pattern

### SupabaseFactory (Singleton Factory with Class-Level State)

`SupabaseFactory` uses class-level attributes to store client instances, making it effectively a singleton without requiring instantiation. Consumers call class methods directly.

**File**: `services/supabase_factory.py`

```python
class SupabaseFactory:
    _anon_client: Optional[Client] = None
    _service_client: Optional[Client] = None
    _initialized: bool = False

    @classmethod
    def initialize(cls, supabase_url, supabase_key, service_role_key=None):
        cls._anon_client = create_client(url, anon_key)
        if service_key:
            cls._service_client = create_client(url, service_key)
        cls._initialized = True

    @classmethod
    def get_anon_client(cls) -> Client:
        if not cls._initialized or not cls._anon_client:
            raise RuntimeError("SupabaseFactory not initialized.")
        return cls._anon_client

    @classmethod
    def get_service_client(cls) -> Optional[Client]:
        if not cls._initialized:
            raise RuntimeError("SupabaseFactory not initialized.")
        return cls._service_client
```

**Usage**: Called once in `_initialize_services(app)`, then consumed everywhere via convenience functions `get_supabase()` and `get_supabase_admin()`.

### ServiceFactory (Lazy-Loading Factory)

`ServiceFactory` delays construction of expensive services (OpenAI client, R2 client) until first access using Python `@property` descriptors.

**File**: `services/service_factory.py`

```python
class ServiceFactory:
    def __init__(self, config):
        self.config = config
        self._ai_service = None
        self._prompt_service = None
        self._r2_service = None

    @property
    def openai_service(self):
        """Initialize AI service with OpenRouter support"""
        if self._ai_service is None:
            if use_openrouter and self.config.OPENROUTER_API_KEY:
                openai_client = OpenAI(
                    api_key=self.config.OPENROUTER_API_KEY,
                    base_url="https://openrouter.ai/api/v1"
                )
                self._ai_service = AIService(openai_client, self.config, ...)
            elif self.config.OPENAI_API_KEY:
                openai_client = OpenAI(api_key=self.config.OPENAI_API_KEY)
                self._ai_service = AIService(openai_client, self.config, ...)
        return self._ai_service

    @property
    def prompt_service(self):
        if self._prompt_service is None:
            self._prompt_service = PromptService()
        return self._prompt_service
```

**Why**: Avoids initializing API clients when they are not needed (e.g., if the request does not involve AI operations).

---

## 2. Singleton Pattern

Three distinct implementations of the singleton pattern appear in the codebase:

### Class-Level State Singleton (SupabaseFactory)

State is stored as class variables. No instance is ever created. All methods are `@classmethod`.

```python
class SupabaseFactory:
    _anon_client: Optional[Client] = None  # Shared across all callers
    _initialized: bool = False
```

### Class-Level Cache Singleton (DimensionService)

Similar approach but specifically for caching lookup tables loaded once at startup.

**File**: `services/test_service.py`

```python
class DimensionService:
    _language_cache: Dict[str, int] = {}
    _test_type_cache: Dict[str, int] = {}
    _languages_metadata: List[Dict] = []
    _test_types_metadata: List[Dict] = []
    _initialized: bool = False

    @classmethod
    def initialize(cls, supabase_client=None):
        """Pre-load dimension tables into cache. Called once at startup."""
        langs = client.table('dim_languages').select('...').execute()
        cls._language_cache = {r['language_code']: r['id'] for r in langs.data}
        cls._initialized = True
```

### Module-Level Singleton (Config Instances)

Both `test_gen_config` and `topic_gen_config` are instantiated at module load time, creating module-level singletons.

**File**: `services/test_generation/config.py`

```python
# Singleton instance - created on import
test_gen_config = TestGenConfig()
```

**File**: `services/topic_generation/config.py`

```python
# Singleton instance - created on import
topic_gen_config = TopicGenConfig()
```

Both modules also provide a `get_*_config()` function with lazy initialization for cases where import-time instantiation should be deferred.

---

## 3. Decorator Pattern

Authentication and authorization are implemented as Python decorators that wrap route handlers, separating cross-cutting concerns from business logic.

**File**: `middleware/auth.py`

### @jwt_required

Extracts and validates the JWT token, sets request context variables.

```python
@app.route('/api/users/elo', methods=['GET'])
@jwt_required
def get_user_elo_ratings():
    user_id = g.supabase_claims.get('sub')  # Set by decorator
    # ... business logic
```

### @admin_required

Extends `jwt_required` behavior with an additional subscription tier check.

```python
@app.route('/api/admin/users', methods=['GET'])
@admin_required
def list_users():
    # Only reaches here if user is 'admin' or 'moderator'
```

### @tier_required(tiers)

Parameterized decorator for flexible tier-based access control.

```python
@app.route('/api/premium/feature', methods=['GET'])
@tier_required(['premium', 'admin'])
def premium_feature():
    # Only reaches here if user's tier is in the provided list
```

**Implementation detail**: All three decorators use `functools.wraps(f)` to preserve the original function's name and docstring, which is critical for Flask's URL routing.

---

## 4. Service Layer Pattern

Routes are intentionally kept thin. They handle HTTP concerns (parameter extraction, response formatting) and delegate all business logic to service classes.

**Route (thin)**:

```python
@tests_bp.route('/recommended', methods=['GET'])
@jwt_required
def get_recommended_tests():
    user_id = g.supabase_claims.get('sub')
    language_id = request.args.get('language_id', type=int)

    result = test_service.get_recommended(user_id, language_id)

    return jsonify({"status": "success", "data": result})
```

**Service (thick)**:

```python
class TestService:
    def get_recommended(self, user_id, language_id):
        # Business logic: query database, filter by user level,
        # exclude already-taken tests, sort by relevance
        result = self.client.rpc('get_recommended_tests', {...}).execute()
        return self._format_tests(result.data)
```

**Benefits**:
- Services can be tested independently of Flask
- Multiple routes can share the same service method
- Business logic changes do not require touching HTTP handling

---

## 5. Multi-Agent Orchestration Pattern

Both generation pipelines follow the same Orchestrator + Agent pattern:

### Structure

```
Orchestrator
  |-- DatabaseClient (data access)
  |-- Agent 1 (single responsibility)
  |-- Agent 2 (single responsibility)
  |-- ...
  |-- Agent N (single responsibility)
```

### TestGenOrchestrator

**File**: `services/test_generation/orchestrator.py`

```python
class TestGenerationOrchestrator:
    def __init__(self):
        self.db = TestDatabaseClient()
        self.topic_translator = TopicTranslator()
        self.prose_writer = ProseWriter()
        self.title_generator = TitleGenerator()
        self.question_generator = QuestionGenerator()
        self.question_validator = QuestionValidator()
        self.audio_synthesizer = AudioSynthesizer()
```

Workflow: Fetch queue item -> Translate topic -> Write prose -> Generate title -> Generate questions -> Validate questions -> Synthesize audio -> Save to DB

### TopicGenOrchestrator

**File**: `services/topic_generation/orchestrator.py`

```python
class TopicGenerationOrchestrator:
    def __init__(self):
        self.db = TopicDatabaseClient()
        self.embedder = EmbeddingService()
        self.explorer = ExplorerAgent()
        self.archivist = ArchivistAgent(self.db, self.embedder)
        self.gatekeeper = GatekeeperAgent()
```

Workflow: Select category -> Explore candidates -> Check novelty (Archivist) -> Validate quality (Gatekeeper) -> Queue approved topics

### Agent Characteristics

- **Stateless**: Agents do not maintain state between calls. All inputs are passed as arguments.
- **Single Responsibility**: Each agent performs exactly one step in the pipeline.
- **Independently Testable**: Agents can be tested with mock inputs without running the full pipeline.
- **Configurable**: Each agent reads from the shared config singleton for model names, temperatures, etc.

---

## 6. Dataclass Models (Data Transfer Objects)

Typed dataclasses serve as data transfer objects between the database layer and service layer, providing type safety and self-documenting structure.

### Test Generation Models

**File**: `services/test_generation/database_client.py`

```python
@dataclass
class QueueItem:
    id: UUID
    topic_id: UUID
    language_id: int
    status_id: int
    created_at: datetime
    tests_generated: int = 0
    error_log: Optional[str] = None

@dataclass
class Topic:
    id: UUID
    category_id: int
    concept_english: str
    lens_id: int
    keywords: List[str]
    semantic_signature: Optional[str] = None

@dataclass
class LanguageConfig:
    id: int
    language_code: str
    language_name: str
    native_name: str
    prose_model: str = 'google/gemini-2.0-flash-exp'
    tts_voice_ids: List[str] = field(default_factory=lambda: ['alloy'])

@dataclass
class CEFRConfig:
    id: int
    cefr_code: str
    difficulty_min: int
    difficulty_max: int
    word_count_min: int
    word_count_max: int
    initial_elo: int

@dataclass
class QuestionType:
    id: int
    type_code: str
    type_name: str
    description: Optional[str]
    cognitive_level: int

@dataclass
class GeneratedTest:
    id: UUID
    slug: str
    language_id: int
    language_name: str
    topic_id: UUID
    topic_name: str
    difficulty: int
    transcript: str
    gen_user: str
    initial_elo: int
    audio_url: str
    title: Optional[str] = None

@dataclass
class GeneratedQuestion:
    test_id: UUID
    question_id: str
    question_text: str
    choices: List[str]
    answer: str
    question_type_id: Optional[int] = None
```

### Topic Generation Models

**File**: `services/topic_generation/database_client.py`

```python
@dataclass
class Category:
    id: int
    name: str
    status_id: int
    target_language_id: Optional[int]
    last_used_at: Optional[datetime]
    cooldown_days: int

@dataclass
class Lens:
    id: int
    lens_code: str
    display_name: str
    description: Optional[str]
    prompt_hint: Optional[str]

@dataclass
class TopicCandidate:
    concept: str
    lens_code: str
    keywords: List[str]
```

**Why dataclasses over dicts**: Dataclasses provide IDE autocompletion, type checking, clear field documentation, and default values. They make the shape of data flowing through the system explicit.

---

## 7. Caching Pattern

The codebase uses in-memory dictionary caches for data that changes infrequently. All caches follow the same pattern: load once, serve from memory, optional `clear_caches()` for testing.

### DimensionService (Startup Pre-Load)

**File**: `services/test_service.py`

```python
class DimensionService:
    _language_cache: Dict[str, int] = {}      # language_code -> id
    _test_type_cache: Dict[str, int] = {}     # type_code -> id
    _languages_metadata: List[Dict] = []       # Full records
    _initialized: bool = False

    @classmethod
    def initialize(cls, supabase_client=None):
        """Called once during app startup in _initialize_services()"""
        langs = client.table('dim_languages').select('...').execute()
        cls._language_cache = {r['language_code']: r['id'] for r in langs.data}
        cls._initialized = True
```

- Loaded at startup before any request is served
- Never refreshed during runtime (dimension tables are stable)
- Class-level storage means all request threads share the same cache

### Database Client Caches (Lazy First-Access)

`TestDatabaseClient` and `TopicDatabaseClient` both cache dimension data on first access rather than at startup, since they run in batch scripts that may not go through `create_app()`.

```python
class TestDatabaseClient:
    def __init__(self):
        self.client = get_supabase_admin()
        # Caches populated on first access
```

### Cache Invalidation

There is no automatic cache invalidation. For testing and development, services expose `clear_caches()` or `reset()` methods:

```python
SupabaseFactory.reset()  # Clears both clients and _initialized flag
```

This is acceptable because the cached data (languages, test types, CEFR levels) is effectively static configuration stored in dimension tables.

---

## Related Documents

- [System Architecture](./01-system-architecture.md) - Where these patterns fit in the overall system.
- [Service Dependency Graph](./03-service-dependency-graph.md) - How the factory and singleton patterns create the dependency tree.
- [Config Reference](../04-Backend/02-config-reference.md) - Configuration values consumed by these patterns.
