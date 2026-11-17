---
title: "ADR-047: Exercise content moves from Postgres to Supabase Storage (one immutable file per sense)"
status: proposed
date: 2026-11-17
---

# ADR-047: Exercise content moves from Postgres to Supabase Storage (one immutable file per sense)

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
may stay direct.** Enforced by a static test (TASK-983).

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
  verified, not assumed (TASK-997: warm median and p90 within +10% of the `db` baseline for
  `study-session`, `practice/session`, prestudy and speed round).
- The speed round selects its ≤ 20 items **before** hydrating (it currently reads content for
  every mastered sense). Prestudy hydrates every test sense that has exercises; at the default
  cap a zh test with more than 160 such senses loses exercises for the excess senses once the
  column is gone (Open question 1).

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

`b`, `c`, `d` and `e` code against this before `a` exists; TASK-976 lands it first with the
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
                max_retries: int = 3) -> WriteResult:
    """Validates first (ValueError, no I/O): every insert row has 'id' (uuid str),
    word_sense_id == sense_id, language_id == language_id and a dict 'content'.
    db mode emits exactly today's calls, in this order, and nothing else:
      delete: db.table('exercises').delete().eq('word_sense_id', sense_id)
              [.not_.is_('word_asset_id', 'null')] [.in_('ladder_level', sorted(levels))].execute()
      insert: db.table('exercises').insert(list(insert_rows)).execute()
      update: per id, db.table('exercises').update({'content': c}).eq('id', id).execute()
    dual mode: Decision 4. update ids must belong to the sense and not be deleted (ValueError).
    Errors: ValueError; ContentWriteConflict; ContentStorageError; PostgREST APIError propagates."""

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
class SupabaseStorageBackend:  # httpx against {SUPABASE_URL}/storage/v1 with the service key (TASK-977)
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
  Egress is mostly cold-cache fetches after deploys; to be measured (TASK-997).
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
- Answer keys stay server-side exactly as now: the bucket is private, read only with the service
  key, and no signed URL is ever issued to a browser.

## Open Questions

1. **OPEN — prestudy fan-out.** The prestudy page needs the content of every linked sense that
   has exercises (zh p90 126, max 306). The default per-call cap of 160 senses and 3 s deadline
   keep it bounded; until the cut-over, senses over the cap are served from the column, after it
   they show no ladder exercises. Accept this and measure in TASK-997 (default, built in
   TASK-989), or change the page to request exercises only for the words it will drill (a
   product change to `static/js/prestudy/prestudy.js`, which counts exercises per word for every
   sense)? Phase 1 is not blocked.
2. **OPEN — semantic-discrimination rewrite leftovers.** `backup_semdisc_content_20261115`
   (19 MB, the only rollback copy of the 2026-11-15 rewrite), `semdisc_rewrite_work` (1.3 MB) and
   the live-only `apply_semdisc_notes(jsonb)` were kept on 2026-11-17 because no Storage archive
   was possible. With the bucket in place: archive to `_archive/` and drop at the cut-over
   (TASK-998), or keep? Not blocking.
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
  Kept possible: the backend is an interface. Revisit if TASK-997 measures slow cold fetches.
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
| 13 | `scripts/sql/check_jumbled_and_definition_match.sql` | R | offline audit (SQL) | inspects `chunks` / `original_sentence` | retire at clean-up (TASK-999) |
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
| 25 | `tests/sql/test_session_budget_settings.sql:96` | W | SQL test fixture | inserts rows with content | TASK-999 |
| 26 | Python tests with fake DBs (`tests/test_speed_round.py`, `test_level_scoped_regen.py`, session tests, …) | R/W fakes | tests | | owning package, only if a `db`-mode call changes |

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

- [[tasklist/exercise-content-storage.tasks]] — Phase-1 work packages a–e and operator steps (TASK-976–999)
- [[database/schema.tech]] — `exercises` table
- [[features/practice-engine.tech]] — `get_practice_session` return shape
- [[features/practice-extra-rounds.tech]] — `get_review_ahead_items`
- [[features/test-prestudy]] — the prestudy page (largest fan-out)
- [[decisions/ADR-042-request-scoped-caching-and-static-asset-caching]] — latency baseline and the per-request cache
- [[evaluations/latency-2026-11-11]] — benchmark harness reused by TASK-997
