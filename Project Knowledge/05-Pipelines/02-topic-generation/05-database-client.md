# TopicDatabaseClient

`TopicDatabaseClient` provides all database interactions for the topic generation system. It wraps the Supabase admin client with typed methods and caching for dimension tables.

## Source Reference

| File | Path |
|------|------|
| Database Client | `services/topic_generation/database_client.py` (lines 1-598) |
| Supabase Factory | `services/supabase_factory.py` (imported at line 14) |

---

## Data Models

All models are defined as `@dataclass` classes in `database_client.py`.

### `Category`

**Lines:** 24-31

Represents a row from the `categories` table.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `int` | Primary key |
| `name` | `str` | Category name (e.g., `"Agriculture"`) |
| `status_id` | `int` | FK to `dim_status` |
| `target_language_id` | `Optional[int]` | FK to `dim_languages` (optional) |
| `last_used_at` | `Optional[datetime]` | Timestamp of last generation run |
| `cooldown_days` | `int` | Days to wait before reusing category |

### `Language`

**Lines:** 34-40

Represents a row from the `dim_languages` table.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `int` | Primary key |
| `language_code` | `str` | ISO code (e.g., `"zh"`, `"ja"`, `"en"`) |
| `language_name` | `str` | English name (e.g., `"Chinese"`) |
| `native_name` | `str` | Native name (e.g., `"中文"`) |

### `Lens`

**Lines:** 43-50

Represents a row from the `dim_lens` table.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `int` | Primary key |
| `lens_code` | `str` | Machine-readable code (e.g., `"historical"`) |
| `display_name` | `str` | Human-readable name (e.g., `"Historical"`) |
| `description` | `Optional[str]` | Long description |
| `prompt_hint` | `Optional[str]` | Hint text for LLM prompts |

### `TopicCandidate`

**Lines:** 53-58

Output structure from the Explorer agent. Used as an intermediate representation before database insertion.

| Field | Type | Description |
|-------|------|-------------|
| `concept` | `str` | English description of the topic |
| `lens_code` | `str` | Lens code (e.g., `"economic"`) |
| `keywords` | `List[str]` | Keyword tags |

### `GenerationMetrics`

**Lines:** 61-75

Metrics for the `topic_generation_runs` table. Tracks per-run statistics.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `run_date` | `datetime` | required | Timestamp of the run |
| `category_id` | `int` | required | FK to categories |
| `category_name` | `str` | required | Category name for readability |
| `topics_generated` | `int` | `0` | Topics that passed all gates |
| `topics_rejected_similarity` | `int` | `0` | Rejected by Archivist |
| `topics_rejected_gatekeeper` | `int` | `0` | Rejected by Gatekeeper |
| `candidates_proposed` | `int` | `0` | Total candidates from Explorer |
| `api_calls_llm` | `int` | `0` | Total LLM API calls |
| `api_calls_embedding` | `int` | `0` | Total embedding API calls |
| `total_cost_usd` | `float` | `0.0` | Estimated cost in USD |
| `execution_time_seconds` | `Optional[int]` | `None` | Wall-clock time |
| `error_message` | `Optional[str]` | `None` | Error message if run failed |

---

## Class: `TopicDatabaseClient`

**Location:** `services/topic_generation/database_client.py`, line 82

### Constructor

**Lines:** 85-92

```python
def __init__(self):
```

- Obtains a Supabase admin client via `get_supabase_admin()`.
- Raises `RuntimeError` if the admin client is not available.
- Initializes three caches (all start as `None`):
  - `_lens_cache: Optional[Dict[int, Lens]]`
  - `_language_cache: Optional[Dict[int, Language]]`
  - `_status_cache: Optional[Dict[str, int]]`

---

## Methods: Dimension Table Queries

### `get_active_languages()`

**Lines:** 98-126

Fetches all active target languages via the `get_active_languages` Supabase RPC function. Results are cached after the first call.

```python
def get_active_languages(self) -> List[Language]:
```

**Returns:** `List[Language]` sorted by display order.

### `get_active_lenses()`

**Lines:** 128-161

Queries `dim_lens` table for active lenses, ordered by `sort_order`.

```python
def get_active_lenses(self) -> List[Lens]:
```

**Returns:** `List[Lens]` sorted by sort order. Cached after first call.

### `get_lens_by_code()`

**Lines:** 163-179

Looks up a lens by its code (case-insensitive). Populates the lens cache if needed.

```python
def get_lens_by_code(self, lens_code: str) -> Optional[Lens]:
```

### `get_language_by_code()`

**Lines:** 194-224

Looks up a language by code (e.g., `"zh"`). Tries cache first, falls back to direct database query.

```python
def get_language_by_code(self, language_code: str) -> Optional[Language]:
```

### `get_languages_by_codes()`

**Lines:** 226-264

Batch lookup of multiple languages by code. Tries cache first, queries database for any missing codes.

```python
def get_languages_by_codes(self, codes: List[str]) -> Dict[str, Language]:
```

**Returns:** Dict mapping lowercase language code to `Language` object.

### `_get_status_id()`

**Lines:** 181-192

Internal method. Looks up status ID by code from `dim_status` table, with caching. Defaults to `1` (assumed `"pending"`) if not found.

```python
def _get_status_id(self, status_code: str) -> int:
```

---

## Methods: Category Queries

### `get_category_by_name()`

**Lines:** 270-297

Looks up a category by exact name match.

```python
def get_category_by_name(self, name: str) -> Optional[Category]:
```

### `create_category()`

**Lines:** 299-333

Creates a new category with `active` status and `cooldown_days=0`. Used by the import orchestrator.

```python
def create_category(self, name: str, description: str = None) -> Category:
```

### `get_next_category()`

**Lines:** 335-362

Calls the `get_next_category` Supabase RPC function to select the next eligible category. The RPC handles cooldown logic server-side.

```python
def get_next_category(self) -> Optional[Category]:
```

**Returns:** `Category` or `None` if all categories are on cooldown.

### `update_category_usage()`

**Lines:** 364-379

Updates `last_used_at` and `updated_at` timestamps for a category.

```python
def update_category_usage(self, category_id: int) -> None:
```

### `increment_category_topics()`

**Lines:** 381-395

Increments the `total_topics_generated` counter. Fetches the current value first (not atomic).

```python
def increment_category_topics(self, category_id: int, count: int = 1) -> None:
```

---

## Methods: Topic Queries

### `find_similar_topics()`

**Lines:** 401-428

Vector similarity search within a category using the `match_topics` Supabase RPC.

```python
def find_similar_topics(
    self,
    category_id: int,
    embedding: List[float],
    threshold: float = 0.85
) -> List[Dict]:
```

**RPC Parameters:**

| Parameter | Value |
|-----------|-------|
| `query_category` | `category_id` |
| `query_embedding` | 1536-dimensional vector |
| `match_threshold` | Cosine similarity threshold |
| `match_count` | `5` (max results) |

**Returns:** `List[Dict]` with keys: `id`, `concept_english`, `similarity`.

### `insert_topic()`

**Lines:** 430-468

Inserts a new topic into the `topics` table.

```python
def insert_topic(
    self,
    category_id: int,
    concept: str,
    lens_id: int,
    keywords: List[str],
    embedding: List[float],
    semantic_signature: str
) -> UUID:
```

**Columns written:**

| Column | Source |
|--------|--------|
| `category_id` | Parameter |
| `concept_english` | `concept` parameter |
| `lens_id` | Parameter |
| `keywords` | Parameter (list of strings) |
| `embedding` | Parameter (1536-dim vector) |
| `semantic_signature` | Parameter |

**Returns:** `UUID` -- the generated topic ID.

---

## Methods: Queue Operations

### `batch_insert_queue()`

**Lines:** 474-504

Batch inserts topic-language pairs into the `production_queue` table.

```python
def batch_insert_queue(self, items: List[Tuple[UUID, int]]) -> int:
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `items` | `List[Tuple[UUID, int]]` | List of `(topic_id, language_id)` pairs |

Each row is inserted with `status_id` set to the `"pending"` status ID (looked up from `dim_status`).

**Returns:** `int` -- number of rows inserted.

---

## Methods: Prompt Queries

### `get_prompt_template()`

**Lines:** 510-554

Fetches a prompt template by task name, with language fallback.

```python
def get_prompt_template(self, task_name: str, language_id: int = 2) -> Optional[str]:
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `task_name` | `str` | required | `"explorer_ideation"` or `"gatekeeper_check"` |
| `language_id` | `int` | `2` (English) | Language ID from `dim_languages` |

**Query logic:**
1. Query `prompt_templates` for the specified `task_name`, `language_id`, and `is_active=True`, ordered by `version` descending, limit 1.
2. If not found and `language_id != 2`, retry with `language_id=2` (English fallback).
3. Returns `None` if no template exists.

**Returns:** `Optional[str]` -- template text with `{placeholders}`.

---

## Methods: Metrics

### `insert_generation_run()`

**Lines:** 560-586

Inserts a run metrics record into the `topic_generation_runs` table.

```python
def insert_generation_run(self, metrics: GenerationMetrics) -> None:
```

Converts `run_date` to a date string (`.date().isoformat()`) and `total_cost_usd` to float before insertion.

---

## Methods: Utility

### `clear_caches()`

**Lines:** 592-597

Resets all three internal caches to `None`, forcing fresh database queries on next access.

```python
def clear_caches(self) -> None:
```

---

## Caching Strategy

The client caches three dimension tables after first access:

| Cache | Key Type | Populated By |
|-------|----------|-------------|
| `_lens_cache` | `Dict[int, Lens]` (keyed by ID) | `get_active_lenses()` |
| `_language_cache` | `Dict[int, Language]` (keyed by ID) | `get_active_languages()` |
| `_status_cache` | `Dict[str, int]` (code -> ID) | `_get_status_id()` |

Caches persist for the lifetime of the client instance. Use `clear_caches()` to force a refresh.

## Related Documents

- [01-pipeline-overview.md](./01-pipeline-overview.md) -- Pipeline architecture
- [02-orchestrator.md](./02-orchestrator.md) -- Orchestrator that uses the database client
- [03-agents/02-archivist-agent.md](./03-agents/02-archivist-agent.md) -- Archivist uses `find_similar_topics()`
- [04-config.md](./04-config.md) -- Configuration reference
