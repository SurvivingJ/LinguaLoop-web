# ArchivistAgent

The Archivist agent manages topic memory and semantic deduplication. It constructs semantic signatures from topic metadata, generates embeddings, and queries the database for similar existing topics to ensure every new topic is sufficiently distinct.

## Source Reference

| File | Path |
|------|------|
| Archivist Agent | `services/topic_generation/agents/archivist.py` (lines 1-206) |

## Class: `ArchivistAgent`

**Location:** `services/topic_generation/agents/archivist.py`, line 18

**Note:** Unlike Explorer and Gatekeeper, the Archivist does **not** extend `BaseAgent` because it does not make direct LLM calls. It composes the `EmbeddingService` and `TopicDatabaseClient` instead.

### Purpose

The Archivist serves as the pipeline's memory. It prevents the system from generating topics that are too similar to existing ones within the same category. It does this through vector similarity search using cosine distance on 1536-dimensional embeddings stored in the `topics` table via pgvector.

### Constructor

**Lines:** 21-38

```python
def __init__(
    self,
    db_client: TopicDatabaseClient,
    embedder: EmbeddingService
):
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `db_client` | `TopicDatabaseClient` | Database client for topic queries |
| `embedder` | `EmbeddingService` | Embedding generation service |

On initialization, loads the lens cache by calling `self.db.get_active_lenses()`.

---

### Method: `construct_semantic_signature()`

**Lines:** 49-84

Builds a human-readable signature string that captures the semantic essence of a topic. This string is what gets embedded for similarity comparison.

```python
def construct_semantic_signature(
    self,
    category_name: str,
    concept: str,
    lens: Lens,
    keywords: List[str]
) -> str:
```

#### Input Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `category_name` | `str` | Category name (e.g., `"Horses"`) |
| `concept` | `str` | Topic concept description |
| `lens` | `Lens` | Lens object with `display_name` |
| `keywords` | `List[str]` | Keyword tags (max 5 used) |

#### Output Format

```
"{category}: {concept} [{lens_display_name}] ({keyword1}, keyword2, ...)"
```

**Example:**
```
"Horses: The history of farriery [Historical] (blacksmith, iron, medieval)"
```

Keywords are capped at 5 to prevent overly long signatures. If no keywords are provided, the parenthetical section is omitted.

---

### Method: `check_novelty()`

**Lines:** 86-154

The core deduplication method. Generates an embedding for the signature and checks it against existing topics in the same category.

```python
def check_novelty(
    self,
    category_id: int,
    semantic_signature: str,
    threshold: float = None
) -> Tuple[bool, Optional[str], List[float]]:
```

#### Input Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `category_id` | `int` | required | Category to search within |
| `semantic_signature` | `str` | required | Formatted topic signature |
| `threshold` | `float` | `topic_gen_config.similarity_threshold` | Cosine similarity threshold |

#### Processing Logic

1. **Generate embedding** (line 122) -- Calls `self.embedder.embed_single(semantic_signature)` to get a 1536-dimensional vector.
2. **Query for similar topics** (lines 129-133) -- Calls `self.db.find_similar_topics()` which invokes the `match_topics` Supabase RPC. This performs a cosine similarity search within the specified category, returning up to 5 matches above the threshold.
3. **Evaluate results** (lines 135-154):
   - If matches are found, the topic is rejected. The rejection reason includes the similarity score and the concept of the most similar existing topic.
   - If no matches are found, the topic is considered novel.

#### Output

Returns a 3-tuple:

| Index | Type | Description |
|-------|------|-------------|
| 0 | `bool` | `True` if topic is novel (no similar topics found above threshold) |
| 1 | `Optional[str]` | Human-readable rejection reason, or `None` if novel |
| 2 | `List[float]` | The generated 1536-dim embedding (returned for reuse by the orchestrator to avoid re-embedding during topic insertion) |

#### Error Handling

- If embedding generation returns an empty list, returns `(False, "Embedding generation failed", [])`.
- Database query errors propagate up (handled by the orchestrator's top-level try/except).

---

### Method: `batch_check_novelty()`

**Lines:** 156-205

Checks novelty for multiple candidates in a loop. Currently processes sequentially (not batched at the embedding level).

```python
def batch_check_novelty(
    self,
    category_id: int,
    category_name: str,
    candidates: List[dict],
    lenses: Dict[str, Lens]
) -> List[Tuple[dict, bool, Optional[str], List[float]]]:
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `category_id` | `int` | Category FK |
| `category_name` | `str` | Category name for signature construction |
| `candidates` | `List[dict]` | Candidate dicts with `concept`, `lens_code`, `keywords` |
| `lenses` | `Dict[str, Lens]` | Lens lookup by code |

Returns a list of 4-tuples: `(candidate, is_novel, rejection_reason, embedding)`.

Candidates with unknown lens codes are immediately rejected.

---

### Method: `get_lens_by_id()`

**Lines:** 45-47

Lens lookup from the internal cache. Returns `Optional[Lens]`.

---

### LLM/API Calls

The Archivist itself makes **no LLM calls**. It delegates to:

| Service | Provider | Purpose |
|---------|----------|---------|
| `EmbeddingService.embed_single()` | OpenAI | Generate embedding vectors for semantic signatures |
| `TopicDatabaseClient.find_similar_topics()` | Supabase RPC (`match_topics`) | Cosine similarity search via pgvector |

### Configuration Dependencies

| Config Field | Usage |
|-------------|-------|
| `similarity_threshold` | Default threshold for novelty checks (0.85) |

## Related Documents

- [01-explorer-agent.md](./01-explorer-agent.md) -- Upstream: generates the candidates the Archivist checks
- [03-gatekeeper-agent.md](./03-gatekeeper-agent.md) -- Downstream: validates approved topics per language
- [04-embedding-service.md](./04-embedding-service.md) -- Embedding generation used by the Archivist
- [../05-database-client.md](../05-database-client.md) -- Database queries for similarity search
