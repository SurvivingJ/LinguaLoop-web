---
title: "ADR-049: Exercise content moves from Postgres to Supabase Storage (one immutable file per sense)"
status: accepted
date: 2026-11-17
---

# ADR-049: Exercise content moves from Postgres to Supabase Storage (one immutable file per sense)

## Context

Supabase Free caps the database at 500 MB and makes the project read-only above it. On
2026-11-17 the database was 523 MB; an emergency clean-up brought it to **470 MB** (`wiki/log.md`
2026-11-17). Measured live the same day (read-only catalog queries):

| Item | Value |
|---|---|
| `exercises` total / heap / indexes / toast | 200 MB / 184 MB / 16 MB / 72 kB |
| `exercises.content` (sum of `pg_column_size`) | **119 MB** (avg 864 B, max 1,888 B per row, stored inline, not TOASTed) |
| `exercises.tags` | 33 MB (stays in the DB, see Decision 11) |
| Rows / senses | 144,374 rows over 11,021 senses: zh 101,029 rows / 7,784 senses (13.0 per sense, max 46); ja 41,506 / 3,041 (13.6, max 23); en 1,829 / 196; plus **10 zh collocation rows with no `word_sense_id`** (never served, 0 attempts) |
| Raw JSON per sense (`octet_length(content::text)`) | zh ≈ 12.7 KB (half of it the `hant` mirror), ja ≈ 8 KB |
| Content-dependent index | `uq_exercises_context_free_variant` UNIQUE on `(word_sense_id, exercise_type, md5(coalesce(content->>'context_sentence','')))` for 8 context-free types (30,491 rows, 7,278 with a context sentence) |
| `storage.objects` average row | 595 B (2 objects today, bucket `llm-logs-archive`) |

A sense with a full ladder costs ~23 KB of database. The content target is 10k zh + 10k ja
words, which will not fit. After this change a sense costs ≈ 8 KB (13 rows × ~450 B without
content, ~1.4 KB of index, ~0.6–0.8 KB of `storage.objects` metadata for its file); 20k senses
≈ 160 MB. The original goal was ~6 KB; the remaining gap is `tags` (≈ 230 B/row, of which
`provenance` 9 MB and judge metadata ~7 MB), which this ADR deliberately leaves in the database.

### Inventory (Phase 0, 2026-11-17)

Every reader and writer of `exercises.content` was found by grepping `services/`, `routes/`,
`scripts/`, `utils/`, `models/`, `web/`, `templates/`, `static/js`, `tests/`, `migrations/`
(not `migrations/archive/`), and by reading the **deployed** function, view and trigger
definitions in project `kpfqrjtfxmujzolwsvdq`. The full table is Appendix A. Findings that
shape the design:

1. **Grading never reads content**, except the server-side re-grade of `cloze_typed`
   (`routes/practice.py::_grade_typed_if_needed`). `record_exercise_attempt`,
   `ladder_record_attempt`, `ladder_apply_progress`, the IRT calibrator, the admission supply
   gate and every view (`v_ladder_judge_reject_rates`, `vw_distractor_error_analysis`,
   `vw_exercise_performance_by_type`, `v_sense_family_coverage`) read metadata or `tags` only.
   `v_ladder_judge_reject_rates` reads `exercises.tags` judge keys and `word_assets.content`,
   not `exercises.content`, so it keeps working unchanged.
2. **Only two deployed RPCs return content**: `get_practice_session` and
   `get_review_ahead_items`. Repo and live bodies match (whitespace-normalised md5).
3. **Content is mutated in place after it is served**: `_prepare_jumbled_items` rewrites
   `jumbled_sentence` content and `_apply_script_variant` swaps zh fields for the `hant` mirror.
   A cache must never hand out a shared object.
4. **One unique index depends on content** (`uq_exercises_context_free_variant`). `DROP COLUMN
   content` would drop it silently and lose the duplicate backstop.
5. **Fan-out per request** (distinct senses whose content is needed):
   session items ≤ ~30 senses (items are capped by minutes; maintenance candidate LIMIT 60),
   the intro-drill block ≤ 40 senses (`INTRO_BLOCK_MAX_WORDS`), prestudy follow-ups ≤ 5,
   extra-round reviews ≤ 10, speed round ≤ 20 after selection (but it reads content for
   **every** mastered sense before selecting today), gate/stress battery 1 sense, the test
   prestudy page **all of the test's linked senses** (live, active tests: zh p50 78 / p90 126 /
   max 306; ja p50 43 / p90 75 / max 89; en p50 43 / p90 270 / max 382, of which only senses
   with exercises are read).
6. **Repo/live drift**: `migrations/phase17_drop_deprecation_wrappers.sql` (TASK-220, wiki says
   "removed 2026-07-14") is not in effect live — `get_exercise_session(uuid,smallint,integer)`
   (the phase-9 body, returns `e.content`), `get_exercise_session(uuid,smallint,integer,numeric)`
   and `get_ladder_session(uuid,smallint,integer)` all exist (service_role only, no Python
   caller). `apply_semdisc_notes(jsonb)` (rewrites `exercises.content`), `semdisc_rewrite_work`
   (1.3 MB) and `backup_semdisc_content_20261115` (19 MB) exist live and are not in the repo.
   `wiki/database/schema.tech.md` lists indexes that do not exist live and omits two that do.
7. `run_parallel` (`services/concurrency.py`) runs nested calls **inline** when called from its
   own `io` pool. `prestudy._load_exercises` already runs inside `run_parallel`, so content
   fetches must not use that pool.

## Decision

### 1. Layout

Private Supabase Storage bucket **`exercise-content`** (`public = false`, file size limit 1 MB,
MIME `application/json`), created by the Phase-1 migration. One file per sense and version:

```
{lang_code}/{word_sense_id}.v{content_version}.json      lang_code = {1:'zh', 2:'en', 3:'ja'}[language_id]
_archive/...                                             cut-over exports; never swept
```

`lang_code` comes from a fixed map in the store (the same map as `intro_drill.LANG_CODE`), not
from `dim_languages` (no lookup, and `dim_languages_rows.csv` in the repo is stale: `cn`/`jp`).

### 2. File format (canonical, write-once)

```json
{"format": 1, "sense_id": 12345, "language_id": 1, "version": 0,
 "exercises": {"<exercise uuid>": <content jsonb, unchanged>, "...": "..."}}
```

Encoded with `json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(',', ':'))`, UTF-8.
`format` and `language_id` were added to the target design so the format can evolve and the sweep
can sanity-check a file. A file contains the content of **every** row of the sense at that version,
active or not (re-activation never touches content). A file is never overwritten.

### 3. Versions

- `exercises.content_version integer NOT NULL DEFAULT 0`. **Version 0 is the backfill export.**
  The column default makes `ADD COLUMN` a catalog-only change; no existing row is rewritten.
  (Changed from the target design, which implied stamping versions onto every row: an `UPDATE` of
  144k rows writes ~190 MB of new row versions into a database at 470 of 500 MB.)
- Every later version comes from `public.exercise_content_version_seq` (global, integer,
  increasing, gaps allowed). Unique numbers make every file name write-once, including the file
  of a writer that loses a race. Within a sense, versions only increase.
- All rows of a sense normally share one version. A sense can briefly have mixed versions only
  if a row was inserted outside the store (`EXERCISE_CONTENT_WRITE=db`); hydration groups by
  `(sense, version)` per item and the next store write re-unifies the sense.

### 4. Concurrency rule (one writer per sense at a time, no lost updates)

**All `INSERT`s into `exercises` and all changes to content go through
`store.write_sense`. `DELETE`s and metadata-only `UPDATE`s (`is_active`, `irt_*`, counts, `tags`)
may stay direct.** Enforced by a static test (TASK-1015).

`write_sense` in `dual` mode is optimistic compare-and-swap on the sense:

1. `exercise_content_begin(sense)` → current version `V`, a fresh version `N` from the sequence,
   and the sense's current rows (ids + metadata).
2. Build the full new file: current content of the surviving rows (file `V`; rows missing from it
   come from the `content` column while it exists) + updates + inserts.
3. Upload `…/{sense}.v{N}.json` with no-overwrite (`x-upsert: false`).
4. `exercise_content_commit(sense, expected_version=V, expected_ids=<ids from 1>, new_version=N,
   deletes, inserts, updates)` takes `pg_advisory_xact_lock(47047, sense)`, checks that the sense's
   version is still `V` **and its row-id set is unchanged**, then applies deletes, inserts and
   content updates and sets `content_version = N` on every row of the sense, in one transaction.
5. On `version_conflict` / `rows_changed` the writer deletes its own file `N` (best effort) and
   retries from step 1 (max 3 attempts, then `ContentWriteConflict`). If the commit call itself
   fails (network, constraint), the file is left for the sweep and the error is raised.

Two writers editing different exercises of one sense therefore serialise: the second commit
fails, rebuilds from the first writer's file and commits a later version. A row deleted or
inserted outside the store between steps 1 and 4 makes the commit fail with `rows_changed`
instead of silently stamping a row whose content the new file lacks.

### 5. Read path and latency bounds

RPCs return ids + metadata only (when asked); Python hydrates content just before the payload
leaves the server.

- Items are grouped by `(language, sense, version)`; one file per group.
- **Process-wide LRU of raw file bytes** keyed `(lang_code, sense_id, version)`, bounded by size
  (`EXERCISE_CONTENT_CACHE_MB`, default 32 MB per process ≈ 2,500 zh senses), **no TTL** (files
  are immutable). Bytes, not parsed dicts: each `hydrate` call parses once per group, so every
  item gets a fresh object (Context finding 3) and memory is ~4× smaller. ADR-042 rejected a
  process-wide plan-row cache because of invalidation; immutable versioned files have none.
- Negative cache: a missing file is not re-fetched for 60 s.
- Misses are fetched on the store's **own** thread pool (`EXERCISE_CONTENT_FETCH_CONCURRENCY`,
  default 16, thread prefix `exc-fetch`), never `services.concurrency`'s pool (Context finding 7).
- **Per-call cap** `EXERCISE_CONTENT_MAX_SENSES_PER_CALL` (default 160 distinct senses; covers
  the zh prestudy p90 of 126) and a **per-call deadline** `EXERCISE_CONTENT_DEADLINE_S` (default
  3.0 s) with a per-GET timeout of 2.0 s. Senses over the cap or past the deadline are treated as
  missing.
- Missing or unreadable file → `exercises.content` for those ids (one batched select per 200 ids)
  with a WARNING, while the column exists (`EXERCISE_CONTENT_DB_FALLBACK`, default on; turned
  off automatically on a "column does not exist" error). Still missing → the item is dropped
  (default) and logged.
- **A session request makes at most two hydrate calls**: the intro-drill block (≤ 40 senses)
  and the final item list (≤ ~30 senses). Cold, each call costs ⌈senses / 16⌉ GET round trips
  run 16 at a time (40 intro senses ≈ 3, 30 item senses ≈ 2), all inside the 3 s deadline; a
  sense fetched once stays in that worker's cache. Warm requests do no network I/O for content and the RPC payload
  shrinks (no content in the jsonb), so warm latency is expected to be flat or better; this is
  verified, not assumed (TASK-1029: warm median and p90 within +10% of the `db` baseline for
  `study-session`, `practice/session`, prestudy and speed round).
- The speed round selects its ≤ 20 items **before** hydrating (it currently reads content for
  every mastered sense). Prestudy hydrates only the senses its word prime drills, plus words the
  learner adds, fetched on demand (Open question 1, answered; built in TASK-1021). The original
  text here ("prestudy hydrates every test sense that has exercises") is superseded.

### 6. Flags

| Flag (`config.py`, read at call time) | Values | Default | Meaning |
|---|---|---|---|
| `EXERCISE_CONTENT_SOURCE` | `db` \| `shadow` \| `storage` | `db` | Read path. `db`: today's behaviour, byte-identical (no extra query, RPCs called with today's arguments, works before the migration). `shadow`: content still served from the DB; files are fetched and compared on a background executor (does not add request latency) and mismatches logged. `storage`: content from files. |
| `EXERCISE_CONTENT_WRITE` | `db` \| `dual` | `db` | Write path. `db`: exactly today's PostgREST calls. `dual`: file first, then rows via the commit RPC, with content still written to the column. Requires the Phase-1 migration. Must be `dual` in **every** environment that writes (web workers and the shells that run upload/fat-seed scripts) before the backfill. |
| `EXERCISE_CONTENT_BUCKET` | text | `exercise-content` | |
| `EXERCISE_CONTENT_CACHE_MB` | int | 32 | per process (2 gunicorn workers → 64 MB) |
| `EXERCISE_CONTENT_FETCH_CONCURRENCY` | int | 16 | |
| `EXERCISE_CONTENT_MAX_SENSES_PER_CALL` | int | 160 | |
| `EXERCISE_CONTENT_DEADLINE_S` / `EXERCISE_CONTENT_HTTP_TIMEOUT_S` | float | 3.0 / 2.0 | |
| `EXERCISE_CONTENT_DB_FALLBACK` | bool | true | |
| `EXERCISE_CONTENT_SHADOW_SAMPLE` | float 0–1 | 1.0 | share of groups compared in shadow |

Unknown values fall back to `db` with one ERROR log. `storage` with `WRITE=db`, or a non-`db`
mode without `SUPABASE_URL` / service key, logs one ERROR (the latter behaves as `db`).

### 7. Schema changes

Phase-1 migration `migrations/exercise_content_storage.sql` (additive, no row rewrite):
`content_version int NOT NULL DEFAULT 0`; `dedupe_key text` (NULL; filled by the commit RPC for
the 8 context-free types as `md5(coalesce(content->>'context_sentence',''))`); the sequence; the
three write-side RPCs (Decision 8); the bucket row.

Phase-1 migration `migrations/exercise_content_session_rpcs.sql`: `get_practice_session` and
`get_review_ahead_items` gain `p_include_content boolean DEFAULT true` (old 5-arg signatures
dropped in the same transaction, so today's 5-argument calls resolve to the new function); every
item gains `content_version`; `content` is present only when `p_include_content`. Bodies are
otherwise the live bodies. Drops the three dead content-returning functions (Context finding 6;
this executes TASK-220's existing decision).

Cut-over `migrations/exercise_content_drop_column.sql` (operator-run, after `storage` has run
clean): batch-backfill `dedupe_key` for existing rows (2,000 rows per batch, plain `VACUUM`
between batches — an unbatched update of 30k rows would add ~40 MB), create
`uq_exercises_context_free_variant_v2 (word_sense_id, exercise_type, dedupe_key)` with the old
predicate, archive and delete the 10 sense-less rows, replace the commit and session RPCs with
versions that never reference `content`, `DROP COLUMN content` (drops the old unique index), then
`VACUUM (FULL, ANALYZE) exercises`. Peak usage during `VACUUM FULL` is the old table plus the new
copy (~80 MB); the 2026-11-17 clean-up did the same at 523 MB.

### 8. RPC contract (normative; c implements, a codes against it)

All three are `SECURITY INVOKER`, `SET search_path = public, pg_temp`, `REVOKE ALL … FROM PUBLIC,
anon, authenticated`, `GRANT EXECUTE … TO service_role`.

`exercise_content_begin(p_sense_id integer) RETURNS jsonb` (VOLATILE):
```json
{"sense_id": 12345, "current_version": 0, "new_version": 4711,
 "rows": [{"id": "uuid", "language_id": 1, "exercise_type": "cloze_completion", "ladder_level": 3,
           "word_asset_id": 99, "is_active": true, "content_version": 0}]}
```
`current_version = COALESCE(max(content_version), 0)` over the sense's rows; `rows` ordered by `id`;
`new_version = nextval('exercise_content_version_seq')`.

`exercise_content_commit(p_sense_id integer, p_expected_version integer, p_expected_ids uuid[],
p_new_version integer, p_delete_ids uuid[] DEFAULT '{}', p_insert_rows jsonb DEFAULT '[]',
p_update_contents jsonb DEFAULT '{}') RETURNS jsonb`:
- Success: `{"ok": true, "version": N, "deleted": d, "inserted": i, "updated": u}`.
- Lost race: `{"ok": false, "reason": "version_conflict" | "rows_changed", "current_version": V}`
  (nothing changed).
- Bad input → `RAISE EXCEPTION … USING ERRCODE = '22023'`: insert row whose `word_sense_id` ≠
  `p_sense_id`; delete/update id not in the sense; `p_new_version <= current`.
- Insert columns: `id, language_id, exercise_type, source_type, word_sense_id,
  corpus_collocation_id, word_asset_id, content (pre-drop only), tags (default '{}'),
  difficulty_static, complexity_tier, ladder_level, pattern_code, is_active (default true),
  generation_batch_id`; `content_version := p_new_version`; `dedupe_key` computed; all other
  columns take their defaults.
- `p_update_contents` is `{"<uuid>": <content>}`; sets `content` (pre-drop only) and recomputes
  `dedupe_key`. `dedupe_key` is always computed from the JSON passed in (`row->'content'`, the
  update value), never from the column, so the post-drop version computes it the same way.
- Finally `UPDATE exercises SET content_version = p_new_version WHERE word_sense_id = p_sense_id
  AND content_version IS DISTINCT FROM p_new_version`.

`exercise_content_live_versions(p_language_id integer) RETURNS jsonb` (STABLE):
`{"<sense_id>": [<version>, …], …}` over all rows of the language with a sense (used by the
backfill and the sweep; one value, so PostgREST's 1,000-row cap does not apply).

### 9. `services/exercise_content/store.py` public interface (normative)

`b`, `c`, `d` and `e` code against this before `a` exists; TASK-1008 lands it first with the
`db`-mode behaviour fully working and the `storage` / `shadow` / `dual` branches delegating to
`reader.py` / `writer.py`.

```python
from services.exercise_content import store   # the only import callers use

READ_MODES  = ('db', 'shadow', 'storage')
WRITE_MODES = ('db', 'dual')
LANGUAGE_CODES = {1: 'zh', 2: 'en', 3: 'ja'}
FILE_FORMAT = 1
COMMIT_LOCK_NAMESPACE = 47047

class ExerciseContentError(Exception): ...
class ContentStorageError(ExerciseContentError): ...   # write path: backend failure, unusable base, corrupt file
class AlreadyExists(ContentStorageError): ...          # backend.put on an existing path
class ContentWriteConflict(ExerciseContentError): ...  # CAS lost max_retries times

@dataclass
class HydrationReport:
    mode: str
    items: int = 0            # items with an id that were considered
    groups: int = 0           # distinct (lang, sense, version) groups
    cache_hits: int = 0
    fetched: int = 0          # groups read from the backend
    db_fallback: int = 0      # items filled from exercises.content
    over_cap: int = 0         # groups skipped by the per-call cap or deadline
    dropped: int = 0          # items removed (drop_missing=True)
    missing_ids: list[str] = field(default_factory=list)
    elapsed_ms: float = 0.0

@dataclass(frozen=True)
class DeleteWhere:
    require_word_asset: bool = False                  # only rows with word_asset_id IS NOT NULL
    ladder_levels: tuple[int, ...] | None = None      # only rows at these levels (None = any)

@dataclass
class WriteResult:
    sense_id: int
    mode: str                 # 'db' | 'dual'
    version: int | None       # committed content_version; None in db mode
    inserted_ids: list[str]
    deleted_count: int
    updated_ids: list[str]
    attempts: int

def read_mode() -> str: ...    # normalised EXERCISE_CONTENT_SOURCE
def write_mode() -> str: ...   # normalised EXERCISE_CONTENT_WRITE

def select_columns(template: str) -> str:
    """PostgREST select list. `template` contains the literal '{content}' exactly once
    (ValueError otherwise). db -> 'content'; shadow -> 'content, content_version';
    storage -> 'content_version'. db mode returns today's select string byte-for-byte.
    Rows to be hydrated must also select id and word_sense_id (or the caller sets them)."""

def rpc_content_args() -> dict:
    """Extra args for get_practice_session / get_review_ahead_items:
    db -> {} (today's call; works before the migration); shadow -> {'p_include_content': True};
    storage -> {'p_include_content': False}."""

def hydrate(items: list[dict], *, language_id: int | None = None, id_key: str = 'id',
            sense_key: str = 'word_sense_id', db=None, drop_missing: bool = True,
            max_senses: int | None = None, deadline_s: float | None = None) -> HydrationReport:
    """Fill item['content'] in place.
    - Considers dicts with a truthy item[id_key]; others (DT error cards, gate/stress markers) are untouched.
    - db: no I/O, no mutation.
    - shadow: no mutation; snapshots canonical(item['content']) per group and queues a background
      comparison against the file (bounded queue of 256; overflow counted, not blocking).
    - storage: items whose 'content' is already non-None are skipped; the rest are grouped by
      (language, item[sense_key], item['content_version']); language = language_id or item['language_id'].
      Cache -> negative cache -> parallel backend GETs (own pool, per-call cap, deadline) ->
      DB fallback -> drop (drop_missing=True; list mutated in place, order kept) or content=None.
      Every item receives an object shared with nothing else (one json parse per group per call;
      a repeated id in one call gets a deepcopy).
    - Never raises for storage or network problems; raises ValueError only for a bad argument."""

def fetch_sense(language_id: int, sense_id: int, version: int) -> dict[str, dict] | None:
    """exercise_id -> content of one file (fresh objects), via the cache. None when missing,
    unreadable or corrupt (logged). Mode-independent. Never raises."""

def write_sense(db, sense_id: int, language_id: int, *, insert_rows: Sequence[dict] = (),
                delete_where: DeleteWhere | None = None,
                update_contents: Mapping[str, dict] | None = None,
                max_retries: int = 3, expected_version: int | None = None) -> WriteResult:
    """Validates first (ValueError, no I/O): every insert row has 'id' (uuid str),
    word_sense_id == sense_id, language_id == language_id and a dict 'content'.
    db mode emits exactly today's calls, in this order, and nothing else:
      delete: db.table('exercises').delete().eq('word_sense_id', sense_id)
              [.not_.is_('word_asset_id', 'null')] [.in_('ladder_level', sorted(levels))].execute()
      insert: db.table('exercises').insert(list(insert_rows)).execute()
      update: per id, db.table('exercises').update({'content': c}).eq('id', id).execute()
    dual mode: Decision 4. update ids must belong to the sense and not be deleted (ValueError).
    expected_version (added after review, 2026-11-17): the version a read-modify-write caller
    read the content it edits at (base_version(rows)). dual mode refuses the write with
    ContentWriteConflict, before any upload and without a retry, when begin reports another
    version. Ignored in db mode. None: no check (blind update, as before).
    Errors: ValueError; ContentWriteConflict; ContentStorageError; PostgREST APIError propagates."""

def base_version(rows: Sequence[dict]) -> int | None:
    """Highest content_version of one sense's rows as read; None when any row has none
    (db read mode selects no version)."""

# Codec / plumbing (pure; used by the backfill, sweep and tests)
def content_path(language_id: int, sense_id: int, version: int) -> str: ...  # 'zh/123.v0.json'
def encode_sense_file(sense_id: int, language_id: int, version: int,
                      exercises: Mapping[str, dict]) -> bytes: ...
def decode_sense_file(data: bytes, *, sense_id: int, version: int) -> dict[str, dict]: ...  # ContentStorageError on mismatch/corrupt
def canonical(content) -> str: ...   # json.dumps(sort_keys=True, ensure_ascii=False, separators=(',', ':'))
def backend() -> 'StorageBackend': ...           # process singleton built from Config
def set_backend(b: 'StorageBackend | None') -> None: ...   # tests; None = rebuild from Config
def reset_state() -> None: ...       # clears cache, negative cache, backend, warn-once flags, shadow queue

# services/exercise_content/backends.py
@dataclass(frozen=True)
class StoredObject:
    path: str                 # full path inside the bucket, e.g. 'zh/123.v0.json'
    size: int | None
    created_at: datetime | None

class StorageBackend(Protocol):
    def get(self, path: str) -> bytes | None: ...         # None = not found; ContentStorageError otherwise
    def put(self, path: str, data: bytes) -> None: ...    # never overwrites: AlreadyExists
    def delete(self, paths: Sequence[str]) -> None: ...
    def list(self, prefix: str) -> Iterator[StoredObject]: ...

class InMemoryBackend:  # dict-backed, thread-safe; records calls; used by every package's tests
    ...
class SupabaseStorageBackend:  # httpx against {SUPABASE_URL}/storage/v1 with the service key (TASK-1009)
    ...
```

The backend talks to the Storage REST API with `httpx` directly instead of `storage3`
(the installed `storage3` differs from `requirements.txt`, and a pooled `httpx.Client` is
thread-safe and keeps connections alive across the fetch pool).

### 10. Roll-out sequence

`db/db` deploy → apply the two Phase-1 migrations → `WRITE=dual` everywhere → backfill v0 files
and verify (file == DB for every row) → `SOURCE=shadow` for at least 7 days with zero
unexplained mismatches → `SOURCE=storage`, latency check → at least 7 days on `storage` without
fallback warnings → archive all content to `_archive/`, cut-over migration, `VACUUM FULL`,
sweep → clean-up (remove `db`/`shadow` reads and the DB fallback). `SOURCE=db` is an instant
rollback at every step before the column drop; after it, the rollback is the `_archive/` export.

### 11. Tags

Inventory: the only serve-time read of a tag key is `tags.variant`
(`LadderService._fetch_exercises_for_levels`, gate/stress batteries). `ladder_level` and
`semantic_class` tag keys are not read at serve time (`ladder_level` is a column). `tags` stays
entirely in the database, so the judge tags and `v_ladder_judge_reject_rates` are untouched.

## Consequences

- Database: ≈ 470 → ~355 MB at cut-over (−119 MB content, −2.3 MB content index, +~1 MB
  `dedupe_key`, +~7–9 MB `storage.objects` rows for ~11k files). At 20k senses ≈ 160 MB for
  exercises; total stays under 500 MB with a modest margin. `storage.objects` lives in the same
  database, so old versions cost DB space until swept: run the sweep after every bulk edit.
- Storage: ~125 MB of JSON today, ~250 MB at 20k senses, inside the Free plan's 1 GB.
  Egress is mostly cold-cache fetches after deploys; to be measured (TASK-1029).
- Content can no longer be fixed with SQL. Every future content fix is a Python script through
  `store.write_sense(update_contents=…)`, which writes a new version. The historical SQL fixes
  (`jumbled_sentence_simplify.sql`, `repair_semantic_discrimination_is_correct_keys.sql`,
  `apply_semdisc_notes`) cannot be re-run after the cut-over.
- Ad-hoc content audits in SQL (`scripts/sql/check_jumbled_and_definition_match.sql`) stop
  working; they become Python over `fetch_sense`.
- A writer needs Storage and the database. A Storage outage blocks content writes (loudly) and,
  after the cut-over, serves sessions without the affected items.
- Every environment that writes content must set `EXERCISE_CONTENT_WRITE=dual` before the
  backfill; a missed shell produces rows that only the DB fallback can serve. The backfill's
  verify pass and the shadow logs catch this before the column is dropped.
- The §4 write rule is a test: `tests/test_exercise_content_write_paths.py` fails on any new
  direct `INSERT` into `exercises` or content `UPDATE` outside `services/exercise_content/`
  (anyone adding a writer, including contributor-facing notes, must route it through
  `store.write_sense`).
- Answer keys stay server-side exactly as now: the bucket is private, read only with the service
  key, and no signed URL is ever issued to a browser.

## Implementation status (Phase 1, integrated 2026-11-17 — TASK-1025)

**Status stays `proposed`**: everything below is in the repo on branch
`claude/dreamy-brahmagupta-40a4gq`, offline-tested; nothing is applied, deployed or flipped
(operator tasks TASK-1026–1030). Both flags default to `db`, which issues exactly the pre-ADR
PostgREST/RPC calls (checked by running the db-mode serve and write paths of the foundation
commit `c3cb106` and of the integrated branch over the same fake database: payloads and recorded
calls are identical for the session, extra round, speed round, `render_all` and scoped regen; the
prestudy payload differs only by the owner's drill-only change).

| Package | Tasks | What exists |
|---|---|---|
| a store | 1008–1011 | `services/exercise_content/` — `store.py` (§9 facade), `backends.py` (`InMemoryBackend`, `SupabaseStorageBackend` over httpx), `cache.py` (`ByteLRU`, `NegativeCache`), `reader.py` (storage/shadow hydration, `fetch_sense`), `shadow.py` (background comparer), `writer.py` (dual-mode CAS writer); `tests/exercise_content_fakes.py` (`FakeContentDB`) |
| b writers | 1012–1015 | `render_all`, `exercise_stage_runner cmd_render`, `queue_drain._regenerate`, `run_generation_batch`, `backfill_exercise_audio.py`, `backfill_hant_mirrors.py` write through `store.write_sense`; static guard `tests/test_exercise_content_write_paths.py` |
| c SQL | 1016–1018 | `migrations/exercise_content_storage.sql`, `…_session_rpcs.sql`, `…_drop_column.sql` (runbook, steps 0–5), each with a `_rollback.sql`; `tests/sql/test_exercise_content_storage.sql`; static tests |
| d readers | 1019–1022 | session, extra round, prestudy follow-ups, intro block, speed round, gate/stress, prestudy (drill-only + on-demand endpoint), typed re-grade, admin preview, reference-set script |
| e scripts | 1023–1024 | `scripts/backfill_exercise_content.py` (export / verify / repair / archive), `scripts/sweep_exercise_content.py` |
| integration | 1025 | `tests/test_exercise_content_integration.py` (scenarios 1–8 of TASK-1025, three flag combinations) |

### Implementation notes on §8 / §9 (where the contract was silent or was tightened)

- **Backend.** `GET /object/{bucket}/{path}` (200 = bytes; 404, or 400 with `statusCode` "404" /
  `error` "not_found" = missing); `POST /object/{bucket}/{path}` with `x-upsert: false`,
  `content-type: application/json`, `cache-control: max-age=31536000, immutable` (any 2xx ok;
  409, or 400 with `statusCode` "409" / `error` "Duplicate" = `AlreadyExists`); `DELETE
  /object/{bucket}` with `{"prefixes": [...]}`, 100 per request; `POST /object/list/{bucket}`
  (limit 1,000, offset paging, folder entries skipped, read eagerly and sorted by path). One
  pooled `httpx.Client` per process per (timeout, concurrency) (`max_connections = concurrency +
  4`), `trust_env` on, no HTTP/2. The service key never appears in repr, logs or exception text.
  `SupabaseStorageBackend(transport=…)` and `close()` exist for tests.
- **Caches.** `ByteLRU` holds raw file bytes, no TTL, refuses an entry larger than a quarter of the
  budget; `NegativeCache` 60 s TTL; both keyed `(lang_code, sense_id, version)`. Fetches run on the
  store's own pool (`exc-fetch_N` threads); the shadow worker is one daemon thread `exc-shadow`;
  the package never imports `services.concurrency` (tested).
- **Read path.** The per-call cap counts `(lang, sense, version)` groups in item order, before the
  cache lookup, so a warm call serves the same items as a cold one. Groups past the cap and groups
  still unfinished at the deadline both count in `over_cap` (and go to the DB fallback). GETs that
  finish after the deadline still fill the caches. A corrupt file is logged at ERROR, evicted and
  negative-cached; a fetch error is not negative-cached. The DB fallback (one `select('id,
  content')` per 200 ids) switches itself off for the process on 42703 / PGRST204 (one ERROR);
  `reset_state()` switches it back on. `HydrationReport.items` counts every item with an id;
  `groups` counts groups that needed content; `fetched` counts files actually returned;
  `missing_ids` is unique, in item order; `db_fallback` counts items.
- **Write path (dual).** Before any upload (`ValueError`): update ids must be rows of the sense and
  not deleted; insert ids must not be surviving rows (re-inserting a deleted id is allowed); every
  `exercise_content_begin` row must have the call's `language_id` (a sense whose rows carry another
  language cannot be dual-written until its data is fixed); rows must be JSON-safe (NaN refused).
  The base is file V, then the `content` column (one `select('id, content')` per 200 ids). A write
  that leaves the sense empty commits without uploading; a write that matches nothing commits
  nothing and returns the current version. Retries pause `uniform(0, 0.02 × attempt)` s. A
  malformed begin/commit response raises `ExerciseContentError`; backend exceptions are wrapped in
  `ContentStorageError`; a commit that raises leaves the file for the sweep.
- **SQL.** `exercise_content_commit` stamps the new version only on the rows it checked (plus the
  inserts), and rejects more input with 22023 than §8 lists (listed in [[database/schema.tech]]);
  static checks run before the lock, row checks after the compare-and-swap, so a lost race never
  raises 22023. Insert rows must carry `source_type` (NOT NULL, no default; 23502 otherwise); keys
  outside the insert column list are ignored. `get_practice_session` appends content with
  `jsonb_set(v_items, '{-1,content}', …)` (a `v_items || obj || CASE …` chain would append the CASE
  result as a separate array element); `p_include_content = NULL` behaves like false. The cut-over
  runbook adds a precondition block (v2 index valid, no context-free row without `dedupe_key`) and
  drops the old index explicitly. `FakeContentDB` was aligned with these checks in TASK-1025.
- **Readers.** One payload difference between modes: a prestudy follow-up item in a session
  carries `content_version` in shadow/storage mode only (its select reads it there; db mode keeps
  today's select string). `session_assembly._hydrate_items` sets `no_content_reason =
  'content_unavailable'` when hydration empties a non-empty item list. The typed re-grade fails
  open on missing content. The admin preview adds `word_sense_id` per exercise.
- **Fix scripts (TASK-1014).** In db mode their select strings now also read `word_sense_id,
  language_id` (intended), and content updates are issued per sense after the sense is processed
  (still one `update({'content': c}).eq('id', id)` per row). In dual mode each touched sense gets
  one new version per run. Rows without a sense are counted `skipped_no_sense`.
- **Backfill (TASK-1023).** Archives are split into deterministic gzip parts of at most 1 MiB (the
  bucket limit), listed with sha256 in `manifest.json`; all `--archive-*` flags need `--language
  all`; archives are never overwritten (identical bytes = already archived). `--repair` needs
  `EXERCISE_CONTENT_WRITE=dual` (exit 2 otherwise). Exit codes 0 clean / 1 findings / 2 refused.
- **Sweep (TASK-1024).** Dry run by default; files with no `created_at` or an unknown name are kept
  and reported; an empty live set next to deletable files deletes nothing unless
  `--allow-empty-live-set`.

### Log lines operators will see (logger `services.exercise_content` unless noted)

- Read: `exercise_content.db_fallback n= senses=` (WARNING), `.db_fallback_error`,
  `.db_fallback_disabled` (ERROR), `.db_fallback_unavailable`, `.missing n= dropped= ids=`,
  `.fetch_error n= first=`, `.corrupt_file` (ERROR), `.missing_file`, `.fetch_sense_error`;
  `services.practice.session_assembly`: `exercise content hydrated (lang= mode=): items= groups=
  cache_hits= fetched= db_fallback= over_cap= dropped= elapsed_ms=` (INFO) and `exercise content
  unavailable: all N session item(s) dropped` (ERROR).
- Shadow: `.shadow_mismatch kind= sense= version= exercise=<id>|* [n=] [error=]` (WARNING);
  `.shadow_summary compared= ok= missing_file= missing_exercise= content_diff= dropped=
  fetch_error=` (INFO, every 500 comparisons).
- Write: `.write sense= version= attempts= inserted= deleted= updated=` (INFO), `.write_conflict`
  (INFO), `.commit_failed … (file left for the sweep)` (ERROR), `.orphan_file` (WARNING).
- Config: `.config unknown …`, `.config … needs SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY; using
  db`, storage-with-db-writes (ERROR, once per process).

### Cut-over completed (2026-11-19, TASK-1027–1030)

`exercises.content` is gone. Exercise content lives only in the private Storage bucket `exercise-content`, one immutable file per sense and version (11,021 v0 files, 125 MB).

**Defaults now in code:**
- `EXERCISE_CONTENT_SOURCE=storage` and `EXERCISE_CONTENT_WRITE=dual` (PR #39).
- A failed GET is retried once, and pooled connections are kept 60 s (PR #40).
- The DB fallback turns itself off on the first "column does not exist".

**Measured:**

| | Before | After |
|---|---|---|
| Database | 523 MB (2026-11-17; 494 MB at the peak, with the 17 MB of Storage-index rows) | **342 MB** |
| `exercises` | 200 MB | 72 MB |

- Storage GET, measured from the agent environment: median 0.18 s, p90 0.24 s.
- Session hydrate: 0.47–0.59 s cold.

**Deviations from §10 (owner decisions 2026-11-18):**
- No 7-day shadow week.
- No Railway flag changes; the defaults changed instead.
- No `--archive-all` gzip copy: every row already had a verified file, and whole-table reads exceed PostgREST's 8 s timeout on the Free instance.

The step-by-step record is in [[tasklist/exercise-content-storage.tasks]] (TASK-1027–1030).

**Remaining:** TASK-1031 removes the transition code: db mode, the fallback, the read/write flags and the pre-drop migration files.

### Live status (2026-11-17, TASK-1026)

Both Phase-1 migrations are live on the only Supabase project; there is no staging project.

- `exercise_content_storage` was applied through the Supabase migration tool. The live bodies and comments are md5-identical to the repo file.
- `exercise_content_session_rpcs` was run by the owner in the SQL editor. The live bodies have CRLF line endings; with `\r` removed they are md5-identical. Any future md5 check against these two bodies must strip `\r` first.
- The deployed app (`main`, pre-ADR-049 code) keeps working: it calls the session RPCs with 5 named arguments, which resolve to the 6-argument functions with `p_include_content` defaulting to true. Checked on production.

The Phase-1 code is not deployed yet, and the flags stay `db`. Next comes the deploy, then TASK-1027.

### Review fixes (independent review of the integrated branch, 2026-11-17)

The reviewer's verdict was *needs fixes*: one major and three minor findings. All four are fixed
on the same branch, with tests:

1. **Major: the cut-over SQL did not enforce its own preconditions.** Step 3 deletes the
   sense-less rows, drops the semdisc leftovers and drops the column. Before the fix, the
   precondition block only checked the v2 index and `dedupe_key`; the archive and verify steps
   were listed in comments only. Step 3a now aborts unless all of these hold:
   - the 6-argument session RPCs exist and no 5-argument overload does;
   - `storage.objects` (bucket `exercise-content`) holds an `_archive/exercises-content-<TAG>/manifest.json`
     from the last 24 hours;
   - `_archive/exercises-no-sense-*.json` exists and is newer than every sense-less row (only
     checked while such rows exist);
   - `_archive/semdisc-20261115/manifest.json` exists (only checked while a semdisc object
     remains);
   - an `_archive/verify-ok/<UTC>.json` from the last 24 hours exists.

   `backfill_exercise_content.py --verify` writes that marker only on a clean full run:
   `--language all`, none of `--senses`, `--limit` or `--dry-run`, and exit 0. Step 0e shows the
   same checks read-only. All eight raise paths and the pass path were run on a scratch
   PostgreSQL 16 instance.
2. **db-mode select drift.** The typed re-grade (`routes/practice.py`) and the reference-set
   script again send exactly the pre-ADR select string in db mode. They add `word_sense_id`, or
   `id, word_sense_id, language_id`, only outside db mode.
3. **Lost updates in read-modify-write scripts.** `write_sense(expected_version=...)` and
   `store.base_version(rows)` are new, see §9. `backfill_exercise_audio`, `backfill_hant_mirrors`
   and `--repair` pass the version they read. A sense written by someone else in the meantime
   is refused rather than overwritten:
   - audio counts it under `failed`;
   - hant counts it under `conflicts`;
   - `--repair` records `repair_failed` and exits 1.

   A re-run picks it up, because all three scripts are idempotent. While reads are `db`, the
   rows carry no version, so the check is off and these scripts behave as before.
4. **The bulk scripts used request-path hydration limits.** The two fix scripts now hydrate each
   100-sense chunk with `max_senses=len(chunk)` and `deadline_s=300`, instead of 160 senses and
   3 s.

### Operational notes for TASK-1026–1030

- Apply order: `exercise_content_storage.sql`, then `exercise_content_session_rpcs.sql`. Roll back
  in reverse (`…_session_rpcs_rollback.sql` only with `SOURCE=db`; `…_storage_rollback.sql` only
  before any dual write); the rollback files refuse otherwise.
- Every shell that runs content writers (stage runner render, `run_generation_batch`, the nightly
  queue drain, the fix scripts, upload/fat-seed) needs `EXERCISE_CONTENT_WRITE=dual` before the
  backfill.
- Smoke-test the real Storage API (get / put / list / delete, the not-found and duplicate
  status shapes, and one archive put of a `.jsonl.gz` part labelled `application/json`) on the
  real bucket before `WRITE=dual`; none of it was exercised against the live service.
- `exercises.pattern_code` is in the commit's insert list; confirm the column exists live (no repo
  migration adds it). `tests/sql/test_exercise_content_storage.sql` on staging exercises the INSERT.
- The cut-over runbook (`exercise_content_drop_column.sql`) runs one step at a time (`psql -f` or
  one statement per SQL-editor run; step 1 repeats until 0 rows, about 16 times). Set
  `EXERCISE_CONTENT_DB_FALLBACK=0` and restart right after step 3. Its rollback's data refill
  (R2) has no script yet.
- Backfill / sweep commands: `python scripts/backfill_exercise_content.py --language {zh,ja,en,all}
  [--dry-run] [--verify [--repair]]`; archives (TASK-1030): `--language all --archive-all <YYYYMMDD>
  --archive-sense-less`, then `--language all --archive-semdisc --semdisc-function-file <file>`
  (export the function first with `select pg_get_functiondef('public.apply_semdisc_notes(jsonb)'::regprocedure);`).
  Then, the same day, run `--language all --verify` until it exits 0; that run writes the
  `_archive/verify-ok/` marker. Run cut-over step 0e: every column must be true before step 3.
  Sweep: `python scripts/sweep_exercise_content.py --language all` (dry run), then `--apply`; run
  after every bulk edit. Reports default to `data/exercise_content_backfill/` and
  `data/exercise_content_sweep/` (not git-ignored).

### Known risks carried forward

- Shadow uses one worker with sequential GETs and a 256-job queue: at high request rates with
  `EXERCISE_CONTENT_SHADOW_SAMPLE=1.0` comparisons are dropped (counted in `dropped`); lower the
  sample rate if it grows.
- After a deadline hit, late GETs keep fetch threads busy; a Storage slowdown longer than the
  deadline queues later calls behind them (each still bounded by its own deadline and the
  fallback). Fetch-pool threads are non-daemon: interpreter exit can wait up to the 2 s GET timeout.
- Mixed-language senses (rows of one sense in two languages) cannot be dual-written (the writer
  refuses); the backfill writes such a sense's file under each language that lists it.
- `--repair` rewrites from DB content. It refuses a sense written by someone else between its
  re-read and its commit (`expected_version`). It is still best run while no bulk writer is
  active.
- The static write guard matches literal table names only (`table(SOME_CONSTANT)` is not seen).

## Open Questions

1. **ANSWERED 2026-11-17 (owner) — prestudy loads only the words it will drill.** The prestudy
   payload carries exercise content only for the senses the prime will drill (the same rule
   `static/js/prestudy/prestudy.js` uses to pick drill words, computed server-side from the
   learner's knowledge), plus a per-sense `has_exercises` flag for every other sense (row ids
   only, no content). When the learner marks a word "I don't know this" (and any other path that
   adds a word to the drill set, e.g. wrong-question follow-ups), the client fetches that word's
   exercises on demand from a new endpoint restricted to the test's senses. Fan-out per request
   drops from all linked senses (zh p90 126, max 306) to the drill set, under the 160-sense cap.
   Built in TASK-1021 (revised); spec in [[features/test-prestudy.tech]].
2. **ANSWERED 2026-11-17 (owner) — archive the semantic-discrimination leftovers.**
   `backup_semdisc_content_20261115`, `semdisc_rewrite_work` and the definition of
   `apply_semdisc_notes(jsonb)` are archived to `_archive/` by the backfill script
   (`--archive-semdisc`, TASK-1023) and dropped in the cut-over migration (TASK-1018), run by the
   operator in TASK-1030.
3. **ANSWERED (decided here, reversible from the archive)** — the 10 zh collocation rows with no
   `word_sense_id` (never served, 0 attempts) cannot be keyed by sense; they are archived to
   `_archive/exercises-no-sense-<date>.json` and deleted at the cut-over.
4. **ANSWERED** — the three dead content-returning functions are dropped in
   `exercise_content_session_rpcs.sql`; this carries out TASK-220's existing decision, which
   `phase17_drop_deprecation_wrappers.sql` did not achieve live.

## Alternatives Considered

- **Stamp `content_version` on every existing row in the backfill** (the original target):
  rewrites all 144k rows (~190 MB of new row versions) on a database 30 MB under its cap.
  Rejected for the v0 default.
- **Per-sense version table** (`exercise_content_versions(sense PK, version)`) instead of a
  column: no row rewrite either and a natural row lock, but every PostgREST reader would need a
  second query (no FK to embed through). Rejected; the advisory lock gives the same serialisation.
- **`V+1` versions with overwrite allowed**: two racing writers write the same path and the
  loser's content can replace the winner's file after the winner commits. Rejected for sequence
  numbers + no-overwrite.
- **Lease/lock row held across the upload**: needs expiry and recovery after a crashed writer.
  CAS with retry is simpler and a crashed writer leaves only an orphan file.
- **One mutable file per sense with a TTL cache**: no version column, but every cache entry can
  be stale and edits need cross-worker invalidation. Rejected (same reasoning as ADR-042).
- **One file per exercise**: ~13× more objects (each ~0.6 KB in `storage.objects`) and ~13× more
  GETs per session. Rejected.
- **Cloudflare R2** (already used for audio, free egress): set up for public audio URLs and a
  second credential set; Supabase Storage sits next to the database and uses the service key.
  Kept possible: the backend is an interface. Revisit if TASK-1029 measures slow cold fetches.
- **Compressing content in place (or dropping the `hant` mirror and converting at serve time)**:
  saves ~half of zh, not enough for 20k senses, and puts OpenCC back on the request path
  (TASK-526 removed it). Rejected.
- **Paid plan**: the developer's constraint is Free.

## Appendix A — Reader / writer inventory of `exercises.content` (2026-11-17)

Package: **a** store, **b** writers, **c** SQL, **d** readers, **e** backfill/sweep, **op**
operator step, **—** no change.

| # | Location | R/W | Path | What it does with content | Package |
|---|---|---|---|---|---|
| 1 | `get_practice_session` (live; `migrations/get_practice_session_language_scope.sql`) | R | serve | returns `content` per item (maintenance LIMIT 60 + acquisition loop ≤ 50 words) | c (+ d caller) |
| 2 | `get_review_ahead_items` (live; `migrations/practice_review_ahead.sql`) | R | serve | returns `content`, ≤ 10 items | c (+ d caller) |
| 3 | `services/practice/session_assembly.py:260` `_practice_session_rpc` (get_session, session floor, extra rounds), `:544` review-ahead call | R | serve | passes RPC items (with content) to the client | d |
| 4 | `services/practice/session_assembly.py:273` `_inject_prestudy_followups` (select at :298) | R | serve | selects content for ≤ 5 follow-up senses, returns it | d |
| 5 | `services/practice/session_assembly.py:729` `_prepare_jumbled_items`, `:764` `_apply_script_variant` (→ `script_serving`) | R (in memory) | serve | inspects/rewrites content in place after selection, not persisted | d (order: after hydrate) |
| 6 | `services/intro_drill.py:326` `build_block` | R | serve | content of ≤ 40 senses' intro exercises (limit 400 rows) into the drill block | d |
| 7 | `services/vocabulary_ladder/speed_round.py:209` `recognition_items` / `_to_item` | R | serve | reads content for every mastered sense, returns ≤ 20 | d (pick, then hydrate) |
| 8 | `services/vocabulary_ladder/ladder_service.py:386` `_fetch_exercises_for_levels` (gate/stress via `routes/vocab_dojo.py`) | R | serve | 1 sense; returns content; reads `tags.variant` | d |
| 9 | `services/prestudy.py:151` `_load_exercises` (`GET /api/tests/<id>/prestudy`) | R | serve | all test senses with exercises; trims fields (`trim_exercise`) | d |
| 10 | `routes/practice.py:273` `_grade_typed_if_needed` | R | serve (POST attempt) | inspects `answer.accepted` to re-grade `cloze_typed` | d |
| 11 | `routes/vocab_admin.py:314` `preview_word` | R | admin | returns one sense's content (+ jumbled prep) | d |
| 12 | `scripts/build_exercise_gen_reference_set.py:295` `fetch_exercise_snapshot` | R | offline eval | snapshots content as `payload` | d |
| 13 | `scripts/sql/check_jumbled_and_definition_match.sql` | R | offline audit (SQL) | inspects `chunks` / `original_sentence` | retire at clean-up (TASK-1031) |
| 14 | `services/vocabulary_ladder/exercise_renderer.py:70` `render_all` (callers: `routes/vocab_admin.py` upload-words + render-exercises, `services/word_list_import/upload_handler.py`, `services/exercise_generation/run_exercise_generation.py`, `scripts/upload_exercises.py`, `scripts/run_content_build.py`, `scripts/render_existing_assets.py`) | W insert | offline/admin | inserts rendered rows | b (callers unchanged) |
| 15 | `services/vocabulary_ladder/queue_drain.py:342` `_regenerate` | W delete+insert | offline (scheduler) | scoped regen: replaces rows at some levels | b |
| 16 | `scripts/run_generation_batch.py:334` | W delete+insert | offline | replaces a sense's ladder rows | b |
| 17 | `scripts/exercise_stage_runner.py:459` `cmd_render` (staged CSV + fat-seed render step; `scripts/fat_seed_runner.py` → `upload_exercises.py --no-render` → here) | W insert | offline | inserts rendered rows | b |
| 18 | `scripts/backfill_exercise_audio.py:216/285/335` | R+W | offline | adds `audio_url` to content; coverage report | b |
| 19 | `scripts/backfill_hant_mirrors.py:92/121` | R+W | offline | rewrites `content.hant` | b |
| 20 | `routes/vocab_admin.py:246` `wipe_word` (DELETE), `:264` `remove_level` (`is_active`); `scripts/retire_zh_fake_words.py` (`is_active`); triggers `exercises_sense_quarantine`, `trg_blocklist_retire_exercises` (`is_active`) | W metadata | admin/offline | no content | — (orphan files swept, e) |
| 21 | `uq_exercises_context_free_variant` (live; `migrations/task743_context_free_exercise_caps.sql`) | R (index expr) | DB constraint | `md5(content->>'context_sentence')` uniqueness | c (`dedupe_key`), op |
| 22 | `get_exercise_session(uuid,smallint,integer)` (live, phase-9 body), `get_exercise_session(…,numeric)`, `get_ladder_session` (live wrappers; drift) | R | dead (no caller) | return content | c (drop) |
| 23 | `apply_semdisc_notes(jsonb)` (live only; drift) + `semdisc_rewrite_work`, `backup_semdisc_content_20261115` (19 MB content copy) | R+W | one-off (2026-11-15) | rewrote semantic-discrimination content | op (owner decision) |
| 24 | Applied historical migrations: `jumbled_sentence_simplify.sql`, `repair_semantic_discrimination_is_correct_keys.sql`, `task743_dedupe_context_free_exercises.sql`, `fix_exercise_language_ids.sql` | R/W | history | one-off rewrites/dedupes | — (cannot be re-run after cut-over) |
| 25 | `tests/sql/test_session_budget_settings.sql:96` | W | SQL test fixture | inserts rows with content | TASK-1031 |
| 26 | Python tests with fake DBs (`tests/test_speed_round.py`, `test_level_scoped_regen.py`, session tests, …) | R/W fakes | tests | | owning package, only if a `db`-mode call changes |

**Status 2026-11-17 (TASK-1025):** rows 3–12 hydrate through `store.select_columns` / `store.hydrate`
/ `store.rpc_content_args` (row 9: drill-only payload + `GET /api/tests/<id>/prestudy/exercises`,
see [[features/test-prestudy.tech]]); rows 14–19 write through `store.write_sense` (row 15:
`DeleteWhere(require_word_asset=True, ladder_levels=<sorted levels> or None)`, new queue detail
codes `content_write_conflict` / `content_storage_error` plus `error_detail`; row 16:
`DeleteWhere(require_word_asset=True)`, a write error fails the sense and queues it for regen;
row 17: a write error blocks the sense; rows 18–19: `select_columns` + `hydrate` in chunks of at
most 100 senses, one `update_contents` write per sense); rows 1, 2, 21, 22, 23 are in the
written-not-applied migrations. The §4 write rule is enforced by
`tests/test_exercise_content_write_paths.py` (token-based scan of `services/`, `routes/`,
`scripts/`, `utils/`, `web/`, excluding `services/exercise_content/`; `ALLOWLIST` empty; a
stale entry fails).

Metadata-only (no change): `services/practice/attempt_recording.py:86/233/242/579`,
`services/practice/new_word_admission.py:789`, `services/prestudy.py:408`,
`routes/tests/prestudy.py:111`, `services/intro_drill.py:426/488`, `services/irt/calibrator.py:151`,
`routes/vocab_admin.py:203`, `services/word_list_import/upload_handler.py:63`,
`scripts/{export_exercise_worklist,simulate_preteach_variants,render_existing_assets}.py`;
live `record_exercise_attempt`, `ladder_record_attempt`, `ladder_apply_progress`,
`ladder_new_word_state`, `prestudy_plan_inputs`, `irt_apply_calibration`, `intro_commit_word`,
`sync_exercise_history`; views `v_ladder_judge_reject_rates` (tags + `word_assets.content`),
`vw_distractor_error_analysis` (tags), `vw_exercise_performance_by_type`,
`v_sense_family_coverage`. In-memory only: `scripts/run_exercise_gen_eval.py` (calls the pure
`build_rows`), `scripts/score_exercise_gen_run.py` (run files). Frontend renderers read
`item.content` from API payloads, whose shape does not change.

## Related Pages

- [[tasklist/exercise-content-storage.tasks]] — Phase-1 work packages a–e and operator steps (TASK-1008–1031)
- [[database/schema.tech]] — `exercises` table
- [[features/practice-engine.tech]] — `get_practice_session` return shape
- [[features/practice-extra-rounds.tech]] — `get_review_ahead_items`
- [[features/test-prestudy]] / [[features/test-prestudy.tech]] — the prestudy page (largest fan-out; drill-only loading)
- [[decisions/ADR-042-request-scoped-caching-and-static-asset-caching]] — latency baseline and the per-request cache
- [[evaluations/latency-2026-11-11]] — benchmark harness reused by TASK-1029
