# TopicGenerationOrchestrator

The `TopicGenerationOrchestrator` coordinates the daily topic generation workflow. It initializes all agents, selects a category, drives the Explorer-Archivist-Gatekeeper pipeline, manages the daily quota, and persists metrics.

## Source Reference

| File | Path |
|------|------|
| Orchestrator | `services/topic_generation/orchestrator.py` (lines 1-327) |

## Class: `TopicGenerationOrchestrator`

**Location:** `services/topic_generation/orchestrator.py`, line 42

### Constructor (`__init__`)

**Lines:** 45-63

The constructor validates configuration, initializes the database client and all four agents:

```python
def __init__(self):
```

**Initialization sequence:**

1. Calls `topic_gen_config.validate()` -- raises `ValueError` if API keys are missing or settings are out of range.
2. Creates a `TopicDatabaseClient` instance (uses `SupabaseFactory` internally).
3. Creates `EmbeddingService` -- connects to OpenAI for embedding generation.
4. Creates `ExplorerAgent` -- connects to OpenRouter for topic ideation.
5. Creates `ArchivistAgent` -- receives the database client and embedder for novelty checks.
6. Creates `GatekeeperAgent` -- connects to OpenRouter for cultural validation.
7. Sets `self.metrics` to `None` (populated during `run()`).

**Raises:** `ValueError` if `topic_gen_config.validate()` returns `False`.

---

### Method: `run()`

**Lines:** 65-229

The primary entry point. Executes the complete daily generation workflow and returns execution statistics.

```python
def run(self) -> GenerationMetrics:
```

**Returns:** `GenerationMetrics` dataclass with counts, timings, and cost estimates.

**Workflow steps:**

#### Step 1: Load Dimension Data (lines 91-101)

- Calls `self.db.get_active_languages()` to fetch all active target languages.
- Calls `self.db.get_active_lenses()` to fetch all active lenses and builds a `lens_map` dict keyed by lowercase `lens_code`.
- Raises `ValueError` if either list is empty.

#### Step 2: Select Next Category (lines 103-113)

- Calls `self.db.get_next_category()` which invokes the `get_next_category` Supabase RPC function.
- Raises `NoEligibleCategoryError` if no category is available (all on cooldown).
- Initializes a `GenerationMetrics` dataclass with the selected category's ID and name.

#### Step 3: Fetch Prompt Templates (lines 117-124)

- Loads `explorer_ideation` prompt from `prompt_templates` table.
- Loads `gatekeeper_check` prompt from `prompt_templates` table.
- Raises `ValueError` if either prompt is missing.

#### Step 4: Generate Candidates (lines 126-141)

- Calls `self.explorer.generate_candidates()` with the category name, active lenses, explorer prompt, and `max_candidates_per_run` from config.
- Records `candidates_proposed` and initial `api_calls_llm` count in metrics.
- If no candidates are returned, jumps to finalization.

#### Step 5: Process Candidates (lines 143-208)

Iterates over candidates with a quota guard:

```
for candidate in candidates:
    if approved_count >= topic_gen_config.daily_topic_quota:
        break
```

For each candidate:

1. **Lens validation** -- Looks up `candidate.lens_code` in `lens_map`. Skips unknown lenses.
2. **Semantic signature** -- Calls `self.archivist.construct_semantic_signature()` to build the text representation.
3. **Novelty check** -- Calls `self.archivist.check_novelty()` with category ID, signature, and similarity threshold. If not novel, increments `topics_rejected_similarity` and continues.
4. **Topic insertion** -- If novel and not a dry run, calls `self.db.insert_topic()` with category ID, concept, lens ID, keywords, embedding, and semantic signature. In dry run mode, assigns a nil UUID.
5. **Gatekeeper validation** -- Calls `self._run_gatekeeper()` which delegates to `self.gatekeeper.validate_for_all_languages()`. Returns a list of approved languages.
6. **Queue accumulation** -- For each approved language, appends `(topic_id, language_id)` to the `queue_items` list. Increments `approved_count`.

#### Step 6: Batch Queue Insertion (lines 209-213)

- If not dry run, calls `self.db.batch_insert_queue(queue_items)` to insert all topic-language pairs into `production_queue`.
- In dry run mode, logs what would be queued.

#### Step 7: Update Category (lines 217-221)

- Calls `self.db.update_category_usage(category.id)` to set `last_used_at` to now.
- If any topics were approved, calls `self.db.increment_category_topics()`.

#### Error Handling (lines 225-229)

The entire workflow is wrapped in a `try/except Exception`. On failure:

- The exception is logged with full traceback via `logger.exception()`.
- `self.metrics.error_message` is set to the exception string.
- `_finalize()` is called with `category=None` to still produce a metrics record.

---

### Method: `_run_gatekeeper()`

**Lines:** 231-262

Delegates to `GatekeeperAgent.validate_for_all_languages()` and tracks rejection metrics.

```python
def _run_gatekeeper(
    self,
    candidate: TopicCandidate,
    languages: List[Language],
    prompt_template: str
) -> List[Language]:
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `candidate` | `TopicCandidate` | Topic to validate |
| `languages` | `List[Language]` | All active target languages |
| `prompt_template` | `str` | Gatekeeper prompt with placeholders |

**Returns:** `List[Language]` -- languages that approved the topic.

**Rejection tracking:** Calculates the number of rejections as `total_checked - len(approved)`, where `total_checked` accounts for the short-circuit threshold, and adds this to `self.metrics.topics_rejected_gatekeeper`.

---

### Method: `_finalize()`

**Lines:** 264-326

Calculates final metrics, persists them to the database, and logs a summary.

```python
def _finalize(
    self,
    start_time: float,
    category: Optional[Category]
) -> GenerationMetrics:
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `start_time` | `float` | `time.time()` at workflow start |
| `category` | `Optional[Category]` | Processed category, or `None` on early failure |

**Processing:**

1. Creates a default `GenerationMetrics` if `self.metrics` is `None` (early failure case).
2. Computes `execution_time_seconds`.
3. Sums API call counts: `api_calls_llm` = Explorer calls + Gatekeeper calls; `api_calls_embedding` = Embedder calls.
4. Estimates cost: LLM at ~$0.001/call, embeddings at ~$0.0001/call.
5. If not dry run, calls `self.db.insert_generation_run(self.metrics)` -- wraps in try/except to avoid masking the primary error.
6. Logs a formatted summary block.

**Returns:** The completed `GenerationMetrics` dataclass.

---

## Custom Exception: `NoEligibleCategoryError`

**Lines:** 37-39

Raised when `get_next_category()` returns `None`, indicating all categories are on cooldown. This allows callers to distinguish "no work to do" from actual errors.

```python
class NoEligibleCategoryError(Exception):
    """Raised when no categories are available for generation."""
    pass
```

---

## Configuration Integration

The orchestrator reads the following settings from `topic_gen_config` at runtime:

| Setting | Used In | Purpose |
|---------|---------|---------|
| `daily_topic_quota` | `run()` line 148 | Max topics per run |
| `max_candidates_per_run` | `run()` line 132 | Candidates requested from Explorer |
| `similarity_threshold` | `run()` line 169 | Archivist novelty threshold |
| `gatekeeper_short_circuit_threshold` | `_run_gatekeeper()` line 256 | Consecutive rejections before short-circuit |
| `dry_run` | `run()` lines 178, 210, 218 | Skip all database writes |

## Related Documents

- [01-pipeline-overview.md](./01-pipeline-overview.md) -- High-level pipeline architecture
- [03-agents/](./03-agents/) -- Individual agent documentation
- [04-config.md](./04-config.md) -- Configuration reference
- [05-database-client.md](./05-database-client.md) -- Database client and data models
