---
title: "Exercise Content in Storage — Task Breakdown"
feature: exercise-content-storage
prose_page: ../decisions/ADR-049-exercise-content-in-storage.md  # no feature page; the ADR is the spec
tech_page: ../decisions/ADR-049-exercise-content-in-storage.md
total_tasks: 24
done: 18
---

# Exercise Content in Storage — Task Breakdown

Source: [[decisions/ADR-049-exercise-content-in-storage]] (proposed 2026-11-17). Exercise
`content` (119 MB of a 470 MB database on the 500 MB Free cap) moves to one immutable JSON file
per sense in the private Storage bucket `exercise-content`. The ADR holds the normative
contracts every task codes against: **§8 RPC contract**, **§9 `store.py` interface**, **§2 file
format**, and **Appendix A** (the reader/writer inventory that these tasks cover row by row).

## How Phase 1 runs

1. **TASK-1008 lands first** (S, ≤ 3 h): the `store.py` facade with the full public interface,
   `db`-mode behaviour working, codec, `InMemoryBackend`, flags. Everything else imports it.
2. Then in parallel: **a** (1009 → 1010, and 1011), **b** (1012, 1013, 1014 → 1015), **c** (1016, 1017 →
   1018), **d** (1019, 1020, 1021, 1022), **e** (1023, 1024).
3. **TASK-1025** integrates and runs everything together offline, then updates the wiki.
4. **TASK-1026–1030 are operator tasks** (live database, deploy, flags, measurement). Not for
   agents. TASK-1031 (agent) cleans up after the column drop.

**Offline rule for every agent task.** No Supabase, OpenRouter or Storage access. Verification
commands are written as `OFFLINE pytest …`, meaning:

```
env -u SUPABASE_URL -u SUPABASE_KEY -u SUPABASE_SERVICE_ROLE_KEY -u OPENROUTER_API_KEY \
    -u EXERCISE_CONTENT_SOURCE -u EXERCISE_CONTENT_WRITE python -m pytest -p no:cacheprovider …
```

Baseline 2026-11-17 on this branch: the 35 existing test files named in this file give
554 passed, 2 failed — `tests/test_transcript_mining.py::test_chinese_mining_rejects_an_in_token_substring`
and `::test_chinese_mining_recovers_a_verb_object_merge` (`jieba` not installed). Those two may
keep failing; nothing else may start failing.

**Integration result 2026-11-17 (TASK-1025).** TASK-1008–1025 are done; TASK-1026–1031 remain (operator
steps, then the clean-up). The cited set still gives 554 passed, 2 failed (the same two) in all
three flag combinations (db/db, shadow/dual, storage/dual). The whole offline suite (`OFFLINE
pytest -q tests`) fails 48 tests and has 1 collection error both on the foundation commit `c3cb106`
and on the integrated branch, with identical test ids: they need `jieba` (36), MeCab/ipadic,
Supabase credentials at import (`tests/test_cross_language_gloss_shape.py`), or are otherwise
environmental (`test_auth_hardening`, `test_contains_whole_word`, the DT v6 fixture tests,
`test_prompt_split_l4_l8`). The conftest pin makes every pytest run behave the same whatever
`EXERCISE_CONTENT_*` the shell exports; the modes themselves are exercised by the package tests and
`tests/test_exercise_content_integration.py`, which set them on `Config` with an `InMemoryBackend`.

**`db` mode must not change behaviour.** With both flags at their default `db`, every reader and
writer issues exactly today's PostgREST/RPC calls (same select strings, same RPC arguments, same
call order). Existing tests must pass without edits; a task may edit an existing test file only
where this file says so.

**Tests in b, d and e do not wait for a.** They monkeypatch `store.read_mode` /
`store.write_mode` / `store.hydrate` / `store.write_sense` (all exist after TASK-1008) with simple
fakes and assert on the calls. The real store runs end to end only in TASK-1025.

## File ownership (shared-file conflicts and how they are resolved)

| File | Owner | Others rely on |
|---|---|---|
| `config.py` (the `EXERCISE_CONTENT_*` flags) | TASK-1008 | flags are read only through `store.read_mode()` / `store.write_mode()` / store internals |
| `tests/conftest.py` (autouse fixture pinning both flags to `db` + `store.reset_state()`) | TASK-1008 | every package's tests |
| `services/exercise_content/store.py` | TASK-1008 only | ADR §9; 1010 and 1011 implement `reader.py` / `writer.py` behind it, never edit `store.py` |
| `services/exercise_content/backends.py` | TASK-1008 creates (Protocol, `StoredObject`, `InMemoryBackend`, `SupabaseStorageBackend` stub); TASK-1009 fills `SupabaseStorageBackend` | sequential inside package a |
| `tests/exercise_content_fakes.py` (`FakeContentDB`) | TASK-1011 | TASK-1025 only; b/d/e tests build their own local fakes |
| `services/vocabulary_ladder/exercise_renderer.py` | TASK-1012 (`render_all` only) | `build_rows` stays pure — `scripts/run_exercise_gen_eval.py` and stage-8 replay call it |
| `routes/vocab_admin.py` | TASK-1022 (`preview_word`) | `wipe_word` (DELETE) and `remove_level` (`is_active`) stay direct — allowed by the write rule (ADR §4), so package b does not touch this file |
| `services/practice/session_assembly.py`, `services/intro_drill.py` | TASK-1019 (one task, both files) | — |
| `migrations/exercise_content_storage.sql` / `…_session_rpcs.sql` / `…_drop_column.sql` | TASK-1016 / 1017 / 1018 | 1018 redefines 1016/1017 functions in its own file |
| Wiki pages | TASK-1025, TASK-1031 | — |

Interfaces between packages: ADR-049 §8 (c ↔ a: RPC names, parameters, JSON shapes, error
codes), §9 (a ↔ b, d, e: Python API), §2 (a ↔ e: file bytes via `store.encode_sense_file`).

---

## TASK-1008: Store facade, flags, `db` mode, codec and in-memory backend (lands first)

**Status:** [x] Done (2026-11-17)
**Feature:** exercise-content-storage
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** none
**Built:** foundation commit `c3cb106` (on `claude/dreamy-brahmagupta-40a4gq`). As specified. Internal plumbing (settings, warn-once, reset hooks, cache slots) lives in `store.py` for packages a's reader/writer/cache.

**Description:**
Create the package every other task imports, with the exact public interface of ADR-049 §9.
`db` read and write modes are fully implemented (they reproduce today's calls); `storage` /
`shadow` reads delegate to `reader.py` and `dual` writes to `writer.py`, which are stubs here
raising `NotImplementedError('TASK-1010')` / `('TASK-1011')`. Also the pure helpers (paths, codec,
`canonical`) and a thread-safe `InMemoryBackend` that all later tests use.

**Acceptance Criteria:**
- [x] `from services.exercise_content import store` exposes every name in ADR §9 with those signatures, dataclass fields and exception hierarchy (`AlreadyExists` ⊂ `ContentStorageError` ⊂ `ExerciseContentError`; `ContentWriteConflict` ⊂ `ExerciseContentError`).
- [x] `config.Config` has the ten `EXERCISE_CONTENT_*` settings of ADR §6 with those defaults, read from the environment; `store.read_mode()` / `write_mode()` read `Config` at call time and normalise case/whitespace; an unknown value returns `'db'` and logs one ERROR per process; a non-`db` read mode with `SUPABASE_URL` or `SUPABASE_SERVICE_ROLE_KEY` unset returns `'db'` with one ERROR; `read_mode()=='storage'` with `write_mode()=='db'` logs one ERROR (still returns `'storage'`).
- [x] `select_columns('id, word_sense_id, exercise_type, {content}, ladder_level')` returns `'id, word_sense_id, exercise_type, content, ladder_level'` (db), `'…, content, content_version, …'` (shadow), `'…, content_version, …'` (storage); a template without `{content}` or with two raises `ValueError`.
- [x] `rpc_content_args()` returns `{}` / `{'p_include_content': True}` / `{'p_include_content': False}` for db / shadow / storage.
- [x] `hydrate()` in db mode makes no backend or db call, leaves `items` deep-equal to the input, returns `HydrationReport(mode='db', items=<count of items with an id>)`.
- [x] `write_sense()` in db mode, against a recording fake db, emits exactly the ADR §9 chains in order: `delete().eq('word_sense_id', s)` [+ `.not_.is_('word_asset_id','null')`] [+ `.in_('ladder_level', sorted(levels))`] `.execute()`; then `insert(list(rows)).execute()`; then one `update({'content': c}).eq('id', id).execute()` per update; returns `WriteResult(mode='db', version=None, inserted_ids=[row ids], deleted_count=len(delete data or []), updated_ids=[…], attempts=1)`. Validation (`ValueError`, before any call): row without `id`, `word_sense_id` ≠ `sense_id`, `language_id` ≠ `language_id`, non-dict `content`.
- [x] `content_path(1,5,0)=='zh/5.v0.json'`, `(2,…)` → `en/`, `(3,…)` → `ja/`, unknown id `9` → `'9/5.v0.json'`. `encode_sense_file` writes the ADR §2 document with `sort_keys=True, ensure_ascii=False, separators=(',', ':')`; `decode_sense_file` round-trips and raises `ContentStorageError` on bad JSON, `format != 1`, or `sense_id`/`version` mismatch. `canonical()` is deterministic for key order.
- [x] `InMemoryBackend`: thread-safe; `put` on an existing path raises `AlreadyExists`; `get` of a missing path returns `None`; `list(prefix)` yields `StoredObject`s sorted by path; `delete` removes; records each call in `.calls` (op, path) and supports `fail_next(op, exc)` and optional per-call `latency_s` for tests; `created_at` settable per object.
- [x] `store.backend()` returns a process singleton (`SupabaseStorageBackend` built from `Config`; constructing it must not do I/O); `set_backend(b)` overrides; `reset_state()` clears backend, cache placeholders, warn-once flags.
- [x] `tests/conftest.py` gains an autouse fixture that sets both flags to `'db'` on `Config` and calls `store.reset_state()` after each test.

**Technical Notes:**
Lazy-import `reader` / `writer` inside the delegating branches so the stubs never load in db
mode. `LANGUAGE_CODES = {1:'zh', 2:'en', 3:'ja'}` (same as `services/intro_drill.py:62`). Use
`logging.getLogger('services.exercise_content')`. No network or Supabase client creation at
import time. Keep `store.py` the only module callers import; everything else is internal.

**Files to Create / Modify:**
- `services/exercise_content/__init__.py` — new, docstring only.
- `services/exercise_content/store.py` — new: ADR §9 facade, db mode, codec, backend singleton.
- `services/exercise_content/backends.py` — new: `StoredObject`, `StorageBackend` Protocol, `InMemoryBackend`, `SupabaseStorageBackend` (constructor stores config; methods raise `NotImplementedError('TASK-1009')`).
- `services/exercise_content/reader.py`, `services/exercise_content/writer.py` — new stubs with the signatures 1010/1011 implement: `reader.hydrate(items, *, language_id, id_key, sense_key, db, drop_missing, max_senses, deadline_s, mode) -> HydrationReport`, `reader.fetch_sense(language_id, sense_id, version)`, `writer.write_sense_dual(db, sense_id, language_id, *, insert_rows, delete_where, update_contents, max_retries) -> WriteResult`.
- `config.py` — the ten flags.
- `tests/conftest.py` — autouse pin fixture.
- `tests/test_exercise_content_store_db_mode.py` — new.

**Verification:**
`OFFLINE pytest tests/test_exercise_content_store_db_mode.py tests/test_speed_round.py tests/test_level_scoped_regen.py tests/test_practice_session_reads.py -q` passes; `ruff check services/exercise_content tests/test_exercise_content_store_db_mode.py` is clean.

---

## TASK-1009: Supabase Storage backend (httpx) and byte-bounded caches

**Status:** [x] Done (2026-11-17)
**Feature:** exercise-content-storage
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** TASK-1008
**Built:** branch `ecs/a-store`, commit `58000de` (merged `2b4b35d`). Additive: `SupabaseStorageBackend(..., transport=None)` keyword and `close()`; the module-level client is one pooled client per (timeout, concurrency) setting; `put` accepts any 2xx, `get` only 200; `list` reads every page eagerly, sorts by path, stops on a short page or a page that adds no new path. `ByteLRU.put` returns bool, plus `discard`, `__contains__`, `__len__`; `clear()` resets the counters; `NegativeCache(max_entries=100_000)` prunes expired keys first.

**Description:**
Implement `SupabaseStorageBackend` against the Storage REST API with a pooled `httpx.Client`
(not `storage3`, ADR §9 note), and the two caches the read path uses: a byte-bounded LRU with no
TTL and a 60-second negative cache for missing files.

**Acceptance Criteria:**
- [x] Base URL `{Config.SUPABASE_URL.rstrip('/')}/storage/v1`; headers `Authorization: Bearer <service key>` and `apikey: <service key>`; bucket `Config.EXERCISE_CONTENT_BUCKET`; one module-level `httpx.Client(timeout=EXERCISE_CONTENT_HTTP_TIMEOUT_S, limits=httpx.Limits(max_connections=concurrency+4, max_keepalive_connections=concurrency))`, created lazily, thread-safe.
- [x] `get(path)`: `GET /object/{bucket}/{path}` → 200 bytes; 404, or 400 whose JSON has `statusCode` `"404"` or `error` `"not_found"` → `None`; any other status, timeout or transport error → `ContentStorageError` (message includes status, not the key).
- [x] `put(path, data)`: `POST /object/{bucket}/{path}` with `x-upsert: false`, `content-type: application/json`, `cache-control: max-age=31536000, immutable` → 200 ok; 409, or 400 whose JSON has `statusCode` `"409"` or `error` `"Duplicate"` → `AlreadyExists`; else `ContentStorageError`.
- [x] `delete(paths)`: `DELETE /object/{bucket}` with JSON `{"prefixes": [...]}` in chunks of 100; empty input makes no request.
- [x] `list(prefix)`: `POST /object/list/{bucket}` JSON `{"prefix": <folder>, "limit": 1000, "offset": n, "sortBy": {"column": "name", "order": "asc"}}`, paging until a short page; skips folder entries (`id` null); yields `StoredObject(path=<prefix folder>/<name>, size=metadata.size, created_at=parsed created_at)`.
- [x] `cache.ByteLRU(max_bytes)`: `get(key) -> bytes | None`, `put(key, data)`, `clear()`, `stats() -> {hits, misses, bytes, entries, evictions}`; evicts least-recently-used until `bytes <= max_bytes`; never stores an entry larger than `max_bytes // 4`; correct under 50 concurrent threads.
- [x] `cache.NegativeCache(ttl_s=60.0, clock=time.monotonic)`: `add(key)`, `contains(key)` (False after the TTL), `clear()`.
- [x] All tests use `httpx.MockTransport`; no network.

**Technical Notes:**
The service key must never appear in logs or exception text. `httpx` honours the proxy CA
environment by default (`trust_env=True`); keep that. Do not add `http2` (no `h2` dependency).

**Files to Create / Modify:**
- `services/exercise_content/backends.py` — implement `SupabaseStorageBackend` (created by TASK-1008).
- `services/exercise_content/cache.py` — new.
- `tests/test_exercise_content_backend.py`, `tests/test_exercise_content_cache.py` — new.

**Verification:**
`OFFLINE pytest tests/test_exercise_content_backend.py tests/test_exercise_content_cache.py -q`; `ruff check services/exercise_content`.

---

## TASK-1010: Read path — `storage` and `shadow` hydration, `fetch_sense`

**Status:** [x] Done (2026-11-17)
**Feature:** exercise-content-storage
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-1008, TASK-1009
**Built:** branch `ecs/a-store`, commit `cf007b5` (merged `2b4b35d`). The per-call cap counts groups in item order before the cache lookup (warm and cold calls serve the same items); `over_cap` includes groups unfinished at the deadline; late GETs still fill the caches; a corrupt file is logged at ERROR, evicted and negative-cached; a fetch error is not negative-cached (one WARNING per call). Shadow: group-level mismatches log `exercise=* n=<count>`, fetch errors add `error=<type>`, the summary adds `fetch_error=`; `shadow.stats()` helper. `reader.hydrate` raises `ValueError` for an unknown mode.

**Description:**
Implement `reader.hydrate` and `reader.fetch_sense` exactly as ADR-049 §5 and §9 describe:
grouping by `(language, sense, version)`, byte LRU, negative cache, parallel fetch on the
store's own pool, per-call cap and deadline, DB fallback, drop/None for misses, fresh objects per
item; and `shadow.py`, the background comparer.

**Acceptance Criteria:**
- [x] Storage mode with `InMemoryBackend`: items get the file's content; items with non-None `content` and items without an id are untouched; drop order preserved; `drop_missing=False` leaves `content=None` and lists `missing_ids`.
- [x] Fresh objects: mutating a hydrated item's content changes neither the cache nor a second `hydrate` of the same group; two items with the same id in one call get distinct objects.
- [x] Parallelism: 10 groups on a backend with `latency_s=0.2` finish in < 0.6 s; fetch threads are named `exc-fetch*`; a call made from a thread named `io_0` (as inside `run_parallel`) is still parallel; `services.concurrency` is not imported by the reader.
- [x] Cap and deadline: 200 groups with `EXERCISE_CONTENT_MAX_SENSES_PER_CALL=160` fetch 160 and report `over_cap=40`; with a backend slower than `deadline_s` the call returns by `deadline_s + 0.2 s` and counts the unfinished groups in `over_cap`.
- [x] Negative cache: a missing file is fetched once in 60 s across calls; a corrupt file (`decode_sense_file` raises) is logged at ERROR and treated as missing.
- [x] DB fallback (`EXERCISE_CONTENT_DB_FALLBACK=true`): one `db.table('exercises').select('id, content').in_('id', chunk)` per 200 missing ids; one WARNING `exercise_content.db_fallback n=… senses=…`; an error with code `42703` or `PGRST204` disables the fallback for the process (one ERROR) and the items count as missing. `db=None` → `services.supabase_factory.get_supabase_admin()` only when the fallback is needed.
- [x] Shadow mode: no mutation; per sampled group a canonical snapshot is queued (queue max 256; overflow increments a counter, never blocks); the worker logs WARNING `exercise_content.shadow_mismatch kind=<missing_file|missing_exercise|content_diff|fetch_error> sense=… version=… exercise=…` and every 500 comparisons INFO `exercise_content.shadow_summary compared=… ok=… missing_file=… missing_exercise=… content_diff=… dropped=…`; `EXERCISE_CONTENT_SHADOW_SAMPLE=0` queues nothing. Tests drain the queue with a helper (`shadow.drain(timeout)`).
- [x] `fetch_sense` uses the cache, returns fresh objects, never raises.
- [x] `HydrationReport` counters match the scenario in every test; `elapsed_ms` set.

**Technical Notes:**
Executor: `ThreadPoolExecutor(max_workers=Config.EXERCISE_CONTENT_FETCH_CONCURRENCY,
thread_name_prefix='exc-fetch')`, created lazily, rebuilt by `store.reset_state()`. Parse with
`json.loads` once per group per call. Items lacking a valid int `content_version` go straight
to the fallback. Language: the `language_id` argument, else `int(item['language_id'])`; neither →
missing. The shadow worker is one daemon thread.

**Files to Create / Modify:**
- `services/exercise_content/reader.py` — implement (stub from 1008).
- `services/exercise_content/shadow.py` — new.
- `tests/test_exercise_content_reader.py` — new.

**Verification:**
`OFFLINE pytest tests/test_exercise_content_reader.py tests/test_exercise_content_store_db_mode.py -q`; `ruff check services/exercise_content`.

---

## TASK-1011: Write path — `dual` mode (file first, then rows by compare-and-swap)

**Status:** [x] Done (2026-11-17)
**Feature:** exercise-content-storage
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-1008
**Built:** branch `ecs/a-store`, commit `8462de4` (merged `2b4b35d`). Extra `ValueError`s before any upload: an insert id that is a surviving row, a begin row in another language, rows that are not JSON-safe. A write that matches nothing commits nothing and returns the current version; a write that leaves the sense empty commits without a file. Retries pause `uniform(0, 0.02 × attempt)` s. `FakeContentDB` was aligned with the SQL's validation in TASK-1025 (`e508f1c`).

**Description:**
Implement `writer.write_sense_dual` (ADR-049 §4 and §9) against the RPC contract of §8, and the
shared `FakeContentDB` that emulates those RPCs and the `exercises` table for tests.

**Acceptance Criteria:**
- [x] New sense: one `exercise_content_begin`, one file `…v{N}.json` containing exactly the inserted rows' content, one `exercise_content_commit` with `p_expected_version=0`, `p_expected_ids=[]`; returns `WriteResult(mode='dual', version=N, …)`.
- [x] Scoped replace with `DeleteWhere(require_word_asset=True, ladder_levels=(4,))`: the new file holds the inserted rows plus the untouched rows' content taken from file `V` (byte-identical after `canonical`); deleted ids absent; `p_delete_ids` equals the matching ids from `begin`.
- [x] `update_contents` for an id not in the sense or being deleted raises `ValueError` before any upload.
- [x] Base content: ids missing from file `V` (or no file) come from one `select('id, content')` on the table; if still missing and not deleted → `ContentStorageError`, no commit.
- [x] Race: a commit injected between `begin` and `commit` makes the first attempt return `version_conflict`; the writer deletes its own file and succeeds on attempt 2 with the injected change preserved in the final file. A row deleted outside the store gives `rows_changed` and the same retry. After `max_retries` conflicts: `ContentWriteConflict`, no rows changed by this writer.
- [x] Two threads updating different exercises of one sense concurrently both end up in the final file (no lost update).
- [x] Commit call raising (network/APIError): the uploaded file is not deleted and the exception propagates. `AlreadyExists` on upload → `ContentStorageError` (sequence numbers must make it impossible).
- [x] After success the new file's bytes are put in the read cache when TASK-1009's cache is present (feature-detect; no hard dependency).
- [x] `FakeContentDB` (in `tests/exercise_content_fakes.py`) implements `rpc('exercise_content_begin'|'exercise_content_commit'|'exercise_content_live_versions', params).execute().data` with ADR §8 semantics (a lock, version/row-set CAS, 22023-style errors as raised `ValueError`s, `dedupe_key` for the 8 context-free types), and `table('exercises')` with `select/insert/delete/update/eq/in_/not_.is_/order/range/limit/execute`, rows in memory, a `has_content_column` switch, and hooks to inject a concurrent change between calls.

**Technical Notes:**
Read the base file with `store.backend().get` + `store.decode_sense_file` (not the reader), so
this task does not depend on TASK-1010. Pass `p_insert_rows` as the row dicts (JSON-safe) and
`p_update_contents` as `{id: content}`. Sort id arrays. Log one INFO
`exercise_content.write sense=… version=… attempts=… inserted=… deleted=… updated=…`.

**Files to Create / Modify:**
- `services/exercise_content/writer.py` — implement (stub from 1008).
- `tests/exercise_content_fakes.py` — new (`FakeContentDB`; re-export `InMemoryBackend`).
- `tests/test_exercise_content_writer.py` — new.

**Verification:**
`OFFLINE pytest tests/test_exercise_content_writer.py tests/test_exercise_content_store_db_mode.py -q`; `ruff check services/exercise_content tests/exercise_content_fakes.py`.

---

## TASK-1012: Renderer and stage-runner render through `store.write_sense`

**Status:** [x] Done (2026-11-17)
**Feature:** exercise-content-storage
**Type:** refactor
**Complexity:** S (1-3h)
**Depends On:** TASK-1008
**Built:** branch `ecs/b-writers`, commit `3b5d83d` (merged `57a7de9`). As specified.

**Description:**
`LadderExerciseRenderer.render_all` is the insert funnel for the admin upload/render routes,
word-list import, `run_exercise_generation`, `scripts/upload_exercises.py`,
`scripts/run_content_build.py` and `scripts/render_existing_assets.py` (Appendix A row 14), so
changing it covers all of them. `scripts/exercise_stage_runner.py cmd_render` (the staged-CSV and
fat-seed render step) inserts directly and changes too.

**Acceptance Criteria:**
- [x] `render_all` builds rows with the unchanged `build_rows` and calls `store.write_sense(self.db, sense_id, language_id, insert_rows=rows)` once; returns `result.inserted_ids`. Any exception (incl. `ContentWriteConflict`, `ContentStorageError`, PostgREST errors) is logged as today and returns `[]`.
- [x] In db mode the fake db sees exactly one `table('exercises').insert(rows).execute()` (today's call).
- [x] `build_rows` makes no store call (test asserts with a recorder).
- [x] `cmd_render`: per sense, the existing-rows refusal is unchanged; `--dry-run` calls nothing; otherwise `store.write_sense(db, sid, language_id, insert_rows=rows)` replaces `db.table('exercises').insert(rows).execute()`; a write error marks the sense blocked and continues.
- [x] Existing tests pass unchanged: `tests/test_definition_match_renderer_wiring.py test_jumbled_renderer_wiring.py test_vocab_ladder_judges.py test_word_list_upload_handler.py test_coverage_gap_fixes.py test_p3_type_gating.py test_l1_headword.py test_exercise_gen_followup_bugs.py test_budget_ceiling_cost_integration.py test_fat_seed.py test_context_free_exercise_caps.py`.

**Technical Notes:**
Do not change callers of `render_all`. Keep the docstring note that `render_all` does not
de-duplicate. In `dual` mode an insert into a sense that already has rows is fine: the writer
merges into the existing file.

**Files to Create / Modify:**
- `services/vocabulary_ladder/exercise_renderer.py` — `render_all` only.
- `scripts/exercise_stage_runner.py` — `cmd_render` only.
- `tests/test_exercise_content_writers_render.py` — new.

**Verification:**
`OFFLINE pytest tests/test_exercise_content_writers_render.py tests/test_definition_match_renderer_wiring.py tests/test_jumbled_renderer_wiring.py tests/test_vocab_ladder_judges.py tests/test_word_list_upload_handler.py tests/test_coverage_gap_fixes.py tests/test_p3_type_gating.py tests/test_l1_headword.py tests/test_exercise_gen_followup_bugs.py tests/test_budget_ceiling_cost_integration.py tests/test_fat_seed.py tests/test_context_free_exercise_caps.py -q` (only the baseline failures, none here).

---

## TASK-1013: Regeneration writers (queue drain, generation batch) through `store.write_sense`

**Status:** [x] Done (2026-11-17)
**Feature:** exercise-content-storage
**Type:** refactor
**Complexity:** S (1-3h)
**Depends On:** TASK-1008
**Built:** branch `ecs/b-writers`, commit `1a602e7` (merged `57a7de9`). Additive: `detail['error_detail'] = str(exc)[:500]` next to the `content_write_conflict` / `content_storage_error` code.

**Description:**
`queue_drain._regenerate` (`services/vocabulary_ladder/queue_drain.py:341-354`) and
`scripts/run_generation_batch.py:333-338` delete a sense's ladder rows (optionally only some
levels) and insert the new set. Both become one `store.write_sense` call with a `DeleteWhere`.

**Acceptance Criteria:**
- [x] queue_drain: `store.write_sense(db, sense_id, language_id, insert_rows=new_rows, delete_where=DeleteWhere(require_word_asset=True, ladder_levels=tuple(sorted(levels)) if levels is not None else None))`; `detail['rendered'] = len(new_rows)` on success; `ContentWriteConflict` / `ContentStorageError` → `detail['error'] = 'content_write_conflict' | 'content_storage_error'`, return `(False, detail)`; the coverage re-check runs only after a successful write.
- [x] run_generation_batch: same call with `DeleteWhere(require_word_asset=True)`; a write error sets `outcome.status = 'failed'` with the error in the log; queue/enqueue behaviour otherwise unchanged.
- [x] db mode: the fake db sees today's chains (`delete().eq(...).not_.is_('word_asset_id','null')[.in_('ladder_level', sorted(levels))].execute()` then `insert(rows).execute()`); `tests/test_level_scoped_regen.py` and `tests/test_generation_batch_workers.py` pass unchanged.

**Files to Create / Modify:**
- `services/vocabulary_ladder/queue_drain.py` — `_regenerate` write block only.
- `scripts/run_generation_batch.py` — the delete/insert block only.
- `tests/test_exercise_content_writers_regen.py` — new.

**Verification:**
`OFFLINE pytest tests/test_exercise_content_writers_regen.py tests/test_level_scoped_regen.py tests/test_generation_batch_workers.py tests/test_ladder_topup.py tests/test_sense_quarantine.py -q`.

---

## TASK-1014: Content fix scripts (audio URLs, Traditional mirrors) through the store

**Status:** [x] Done (2026-11-17)
**Feature:** exercise-content-storage
**Type:** refactor
**Complexity:** S (1-3h)
**Depends On:** TASK-1008
**Built:** branch `ecs/b-writers`, commit `5211684` (merged `57a7de9`). Both scripts page the DB as before, then group rows by sense and call `store.hydrate` once per chunk of at most 100 senses (hydrating per id-ordered page would fetch each sense's file many times). A failed sense write counts the rows it carried as failed. New counters `unavailable` / `content_unavailable` for rows hydrate could not fill. In db mode the select strings now also read `word_sense_id, language_id` and updates are issued per sense after the sense is processed (still one update per row).

**Description:**
`scripts/backfill_exercise_audio.py` and `scripts/backfill_hant_mirrors.py` read content and
rewrite it row by row. They read through `select_columns` + `hydrate` and write once per sense
with `store.write_sense(update_contents=…)`, so in `dual` mode each touched sense gets one new
version instead of one per row.

**Acceptance Criteria:**
- [x] Reads select `store.select_columns('id, exercise_type, word_sense_id, language_id, {content}')` (paged as today) and call `store.hydrate(rows, db=db)` per page, at most 100 senses per call.
- [x] Writes: per sense, collect `{exercise_id: new_content}` and call `store.write_sense(db, sense_id, language_id, update_contents=…)` once; a write error counts every row of that sense as failed and continues.
- [x] `--dry-run` (both scripts) and `report_coverage` make no write call.
- [x] Rows with no `word_sense_id` (the 10 zh collocation rows) are skipped and counted as `skipped_no_sense` (never served; documented in the script docstring).
- [x] Tests (fake db + monkeypatched store) cover: grouping, dry-run, skip, write error.

**Files to Create / Modify:**
- `scripts/backfill_exercise_audio.py`, `scripts/backfill_hant_mirrors.py`.
- `tests/test_exercise_content_fix_scripts.py` — new.

**Verification:**
`OFFLINE pytest tests/test_exercise_content_fix_scripts.py -q`; `python scripts/backfill_hant_mirrors.py --help` and `python scripts/backfill_exercise_audio.py --help` exit 0 offline.

---

## TASK-1015: Static guard — no content write outside the store

**Status:** [x] Done (2026-11-17)
**Feature:** exercise-content-storage
**Type:** test
**Complexity:** XS (<1h)
**Depends On:** TASK-1012, TASK-1013, TASK-1014
**Built:** branch `ecs/b-writers`, commit `24293da` (merged `57a7de9`). Also catches the calls on a name the bare builder was assigned to, adjacent string literals and f-string text. Re-run after all merges: the repo scan is clean.

**Description:**
Enforce ADR-049 §4: inserts into `exercises` and changes to `content` only through
`store.write_sense`.

**Acceptance Criteria:**
- [x] A scanner over `services/`, `routes/`, `scripts/`, `utils/`, `web/` (`*.py`, excluding `services/exercise_content/`) flags a `table('exercises')` / `table("exercises")` chain (up to its `.execute()`, multi-line) that contains `.insert(` or `.upsert(`, or `.update(` whose argument mentions `content`; and string literals matching `INSERT INTO (public\.)?exercises` or `UPDATE (public\.)?exercises\s+SET\s+content`.
- [x] Unit tests of the scanner on synthetic snippets (offending and clean) pass; the repo scan finds nothing; an explicit `ALLOWLIST: dict[str, str]` (path → reason) exists and is empty.

**Files to Create / Modify:**
- `tests/test_exercise_content_write_paths.py` — new.

**Verification:**
`OFFLINE pytest tests/test_exercise_content_write_paths.py -q`.

---

## TASK-1016: Migration — columns, sequence, write-side RPCs, bucket

**Status:** [x] Done (2026-11-17)
**Feature:** exercise-content-storage
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** none
**Built:** branch `ecs/c-sql`, commits `93c653b`, `8c690fd` (merged `67ca70e`). `exercise_content_commit` stamps the new version only on the rows it checked (plus the inserts); more input is rejected with 22023 than ADR §8 lists; `source_type` is required (23502); unknown insert keys are ignored. The SQL scenarios and the full apply/rollback chain were run on a throwaway local PostgreSQL 16 cluster with a stub schema (never the live DB).

**Description:**
`migrations/exercise_content_storage.sql`, written per ADR-049 §7–8 and `migrations/CLAUDE.md`,
**not applied** (TASK-1026 applies it). Additive only: no `UPDATE` of `exercises` (the database is
30 MB under its cap).

**Acceptance Criteria:**
- [x] One transaction: `ALTER TABLE public.exercises ADD COLUMN IF NOT EXISTS content_version integer NOT NULL DEFAULT 0, ADD COLUMN IF NOT EXISTS dedupe_key text;` `CREATE SEQUENCE IF NOT EXISTS public.exercise_content_version_seq AS integer START WITH 1;` with `REVOKE ALL … FROM PUBLIC, anon, authenticated` and `GRANT USAGE, SELECT … TO service_role`.
- [x] `exercise_content_begin`, `exercise_content_commit`, `exercise_content_live_versions` exactly as ADR §8 (signatures, JSON shapes, `pg_advisory_xact_lock(47047, p_sense_id)`, version and row-id-set CAS, `ERRCODE = '22023'` cases, insert column list with defaults, `dedupe_key = md5(coalesce(<row JSON>->'content'->>'context_sentence',''))` (from the JSON passed in, never the column) for exactly the 8 types of `uq_exercises_context_free_variant`, final version stamp). Each: `SECURITY INVOKER`, `SET search_path = public, pg_temp`, REVOKE/GRANT, `COMMENT ON FUNCTION` citing ADR-049.
- [x] `INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types) VALUES ('exercise-content', 'exercise-content', false, 1048576, ARRAY['application/json']) ON CONFLICT (id) DO NOTHING;` and `NOTIFY pgrst, 'reload schema';`.
- [x] Header: purpose, ADR link, "NOT applied", apply order (this file, then `exercise_content_session_rpcs.sql`), the rule that rollback is valid only before `EXERCISE_CONTENT_WRITE=dual` was ever set.
- [x] `migrations/exercise_content_storage_rollback.sql`: drops the three functions, the sequence and both columns (never deletes bucket objects; says so).
- [x] `tests/sql/test_exercise_content_storage.sql` (BEGIN … ROLLBACK, same style as `tests/sql/test_session_budget_settings.sql`, run by the operator on staging): fresh sense begin → `current_version` 0; commit inserts two rows (version N, `dedupe_key` set for a context-free type, NULL otherwise); a stale `p_expected_version` → `version_conflict`, nothing changed; a row deleted between begin and commit → `rows_changed`; insert for another sense → SQLSTATE 22023; update recomputes `dedupe_key`; `live_versions` output shape.
- [x] `tests/test_exercise_content_migration_schema.py` (static, offline): the file contains no `UPDATE public.exercises`; the column is added `NOT NULL DEFAULT 0`; REVOKE/GRANT for every function and the sequence; the 8-type list equals `_CONTEXT_FREE_UNIQUE_TYPES` in `services/vocabulary_ladder/exercise_renderer.py` (parse the source) and the type array of `uq_exercises_context_free_variant` in `migrations/task743_context_free_exercise_caps.sql`; the bucket row has `public` false; `tests/test_migration_security_lint.py` passes.

**Files to Create / Modify:**
- `migrations/exercise_content_storage.sql`, `migrations/exercise_content_storage_rollback.sql` — new.
- `tests/sql/test_exercise_content_storage.sql`, `tests/test_exercise_content_migration_schema.py` — new.

**Verification:**
`OFFLINE pytest tests/test_exercise_content_migration_schema.py tests/test_migration_security_lint.py -q`.

---

## TASK-1017: Migration — session RPCs return ids only on request; drop dead content RPCs

**Status:** [x] Done (2026-11-17)
**Feature:** exercise-content-storage
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** none (applied after TASK-1016's file)
**Built:** branch `ecs/c-sql`, commit `ced9d87` (merged `67ca70e`). `get_practice_session` appends content with `jsonb_set(v_items, '{-1,content}', …)` instead of `|| CASE …` (left-associative `||` would append a separate array element); the strict line rule still holds. `p_include_content = NULL` behaves like false. The rollback refuses once `exercises.content` is gone.

**Description:**
`migrations/exercise_content_session_rpcs.sql`, **not applied**. `get_practice_session` and
`get_review_ahead_items` gain `p_include_content boolean DEFAULT true`; behaviour with the default
is today's output plus a `content_version` key per item. Also drops the three dead live functions
that return content (Appendix A row 22; repo/live drift).

**Acceptance Criteria:**
- [x] One transaction: `DROP FUNCTION IF EXISTS public.get_practice_session(uuid, smallint, text, smallint, numeric);` then `CREATE FUNCTION public.get_practice_session(p_user_id uuid, p_language_id smallint, p_mode text DEFAULT 'auto', p_target_minutes smallint DEFAULT 15, p_user_theta numeric DEFAULT NULL, p_include_content boolean DEFAULT true) RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path = public, pg_temp`. Same pattern for `get_review_ahead_items(…, p_include_content boolean DEFAULT true)` (`LANGUAGE sql VOLATILE`, as live).
- [x] Bodies start from the canonical files (`migrations/get_practice_session_language_scope.sql`, `migrations/practice_review_ahead.sql`; both match live, md5-checked 2026-11-17). Only these edits: selected `e.content` → `CASE WHEN p_include_content THEN e.content END AS content`; add `e.content_version`; each item object gains `'content_version', <value>` and carries `'content'` only when `p_include_content` (`… || CASE WHEN p_include_content THEN jsonb_build_object('content', …) ELSE '{}'::jsonb END`).
- [x] REVOKE ALL FROM PUBLIC, anon, authenticated; GRANT EXECUTE TO service_role; COMMENTs.
- [x] `DROP FUNCTION IF EXISTS public.get_exercise_session(uuid, smallint, integer); … (uuid, smallint, integer, numeric); public.get_ladder_session(uuid, smallint, integer);` and `NOTIFY pgrst, 'reload schema';`.
- [x] `migrations/exercise_content_session_rpcs_rollback.sql`: drops the 6-arg functions and recreates the 5-arg ones verbatim from the canonical files (does not recreate the dead functions). Header: roll back only with `EXERCISE_CONTENT_SOURCE=db`.
- [x] `tests/test_exercise_content_migration_rpcs.py` (static): extracts old and new bodies and diffs them line by line (whitespace-normalised); every removed line contains `content`; every added line contains `content` or `p_include_content`; the three DROPs and the grants are present; `p_include_content boolean DEFAULT true` on both; security lint passes.
- [x] Old migration files are **not** archived here (they stay canonical until the live apply; TASK-1031 archives).

**Files to Create / Modify:**
- `migrations/exercise_content_session_rpcs.sql`, `migrations/exercise_content_session_rpcs_rollback.sql` — new.
- `tests/test_exercise_content_migration_rpcs.py` — new.

**Verification:**
`OFFLINE pytest tests/test_exercise_content_migration_rpcs.py tests/test_migration_security_lint.py -q`.

---

## TASK-1018: Cut-over migration file (written now, run by the operator in TASK-1030)

**Status:** [x] Done (2026-11-17)
**Feature:** exercise-content-storage
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** TASK-1016, TASK-1017
**Built:** branch `ecs/c-sql`, commit `b14f7b2` (merged `67ca70e`). Step 3 starts with a precondition block (v2 index valid, no context-free row without `dedupe_key`) and drops the old index explicitly. Added `migrations/exercise_content_drop_column_rollback.sql` (R1–R5; the data refill R2 has no script yet — follow-up).

**Description:**
`migrations/exercise_content_drop_column.sql`: a step-by-step runbook file (each step runnable
on its own in the SQL editor; `VACUUM` and `CREATE INDEX CONCURRENTLY` steps outside any
transaction) per ADR-049 §7.

**Acceptance Criteria:**
- [x] Step 0 (read-only checks): rows of the 8 types with `dedupe_key IS NULL`; rows with `word_sense_id IS NULL` (expect 10); `pg_database_size`; `pg_total_relation_size('public.exercises')`.
- [x] Step 1 (repeat until 0 rows): `UPDATE public.exercises SET dedupe_key = md5(coalesce(content->>'context_sentence','')) WHERE id IN (SELECT id FROM public.exercises WHERE dedupe_key IS NULL AND exercise_type IN (<8 types>) LIMIT 2000);` then `VACUUM public.exercises;`.
- [x] Step 2: `CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_exercises_context_free_variant_v2 ON public.exercises (word_sense_id, exercise_type, dedupe_key) WHERE is_active AND word_sense_id IS NOT NULL AND exercise_type IN (<8 types>);` + a check that it is valid.
- [x] Step 3 (one transaction): `DELETE FROM public.exercises WHERE word_sense_id IS NULL` (comment: only after `--archive-sense-less`, TASK-1023); `CREATE OR REPLACE` of `exercise_content_commit` (no longer writes a `content` column; still computes `dedupe_key` from the `'content'` JSON key of `p_insert_rows` / `p_update_contents`), `get_practice_session` and `get_review_ahead_items` (never return content; `p_include_content` kept for signature compatibility and ignored); `ALTER TABLE public.exercises DROP COLUMN content;`; `NOTIFY pgrst, 'reload schema';`. `DROP FUNCTION IF EXISTS public.apply_semdisc_notes(jsonb); DROP TABLE IF EXISTS public.backup_semdisc_content_20261115, public.semdisc_rewrite_work;` (owner decision 2026-11-17: archived first by `--archive-semdisc`, TASK-1023; the comment says so).
- [x] Step 4: `VACUUM (FULL, ANALYZE) public.exercises;` with a comment on peak space (old + new copy, ~80 MB) and the 2026-11-17 precedent. Step 5: size queries.
- [x] `tests/test_exercise_content_migration_cutover.py` (static): step order (index v2 before DROP COLUMN; DELETE and DROP in one transaction block), no unquoted `\bcontent\b` token inside the step-3 function bodies (quoted JSON keys like `'content'` are allowed; `p_include_content`, `p_update_contents` and `content_version` do not match the word boundary), the v2 predicate's type list equals the old index's, step 1 has `LIMIT` and `dedupe_key IS NULL`, security lint passes.

**Files to Create / Modify:**
- `migrations/exercise_content_drop_column.sql` — new.
- `tests/test_exercise_content_migration_cutover.py` — new.

**Verification:**
`OFFLINE pytest tests/test_exercise_content_migration_cutover.py tests/test_migration_security_lint.py -q`.

---

## TASK-1019: Practice session and intro-drill readers hydrate content

**Status:** [x] Done (2026-11-17)
**Feature:** exercise-content-storage
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-1008
**Built:** branch `ecs/d1-session-readers`, commit `75fd2ac` (merged `a2b208c`). `_hydrate_items` and the speed round catch an unexpected `hydrate` exception (contract breach): logged; in storage mode content-less items are dropped. Prestudy follow-up items carry `content_version` in shadow/storage mode only (the one payload difference between modes).

**Description:**
The daily-session path (Appendix A rows 3–6). RPC items come back without content in `storage`
mode; one hydrate call fills the final item list just before the post-processors that read
content, and the intro block hydrates its own rows (ADR §5: at most two hydrate calls per
session request).

**Acceptance Criteria:**
- [x] `_practice_session_rpc` passes `**store.rpc_content_args()`; so does the `get_review_ahead_items` call in `_extra_review_items`. In db mode the RPC parameters are exactly today's.
- [x] `_inject_prestudy_followups` selects `store.select_columns('id, word_sense_id, exercise_type, {content}, ladder_level')` (db string unchanged) and copies `content_version` into the item only when the row has it.
- [x] New `_hydrate_items(payload, language_id)`: `store.hydrate(payload['items'], language_id=language_id, id_key='exercise_id', sense_key='sense_id', db=self.db)`; called in `get_session` immediately before `_apply_script_variant`, and in `get_extra_round` immediately before its `_apply_script_variant`. If items were non-empty before and empty after: `payload['no_content_reason'] = 'content_unavailable'` and one ERROR log. One INFO line with the report when `fetched`, `db_fallback` or `dropped` is non-zero.
- [x] `intro_drill.build_block` selects `store.select_columns('id, word_sense_id, exercise_type, {content}, ladder_level')` and calls `store.hydrate(ex_rows, language_id=language_id, db=db)` before grouping.
- [x] Tests (monkeypatched `read_mode` + a fake `hydrate` that fills content from a dict and records calls): storage mode sends `p_include_content: False`; hydrate runs once for items, with the right keys and language, before script-variant and jumbled preparation (call-order recorder); DT error cards and gate/stress markers untouched; all-dropped → `content_unavailable`; the intro block is hydrated once; follow-up items carry `content_version`; extra rounds likewise; db mode output equals today's on the existing fixtures.
- [x] Existing tests pass unchanged: `tests/test_practice_session_reads.py test_practice_extra_rounds.py test_session_merges.py test_latency_caching.py test_intro_drill.py test_practice_session_floor.py test_serve_time_exercise_guards.py test_practice_error_card_injection.py test_script_variant_serving.py test_prestudy_session.py test_ladder_topup.py test_study_session_ordering.py test_study_session_tail.py`.

**Technical Notes:**
Do not hydrate earlier: `route_untaught`, the intro-word filter and `_order_items` do not read
content, and hydrating after them fetches fewer files. Do not run `build_block` on
`run_parallel` (it relies on the per-request cache, which pool threads cannot see).

**Files to Create / Modify:**
- `services/practice/session_assembly.py`, `services/intro_drill.py`.
- `tests/test_exercise_content_session_readers.py` — new.

**Verification:**
`OFFLINE pytest tests/test_exercise_content_session_readers.py tests/test_practice_session_reads.py tests/test_practice_extra_rounds.py tests/test_session_merges.py tests/test_latency_caching.py tests/test_intro_drill.py tests/test_practice_session_floor.py tests/test_serve_time_exercise_guards.py tests/test_practice_error_card_injection.py tests/test_script_variant_serving.py tests/test_prestudy_session.py tests/test_ladder_topup.py tests/test_study_session_ordering.py tests/test_study_session_tail.py -q`.

---

## TASK-1020: Battery readers (speed round, gate/stress) hydrate content

**Status:** [x] Done (2026-11-17)
**Feature:** exercise-content-storage
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-1008
**Built:** branch `ecs/d1-session-readers`, commits `5254a14`, `d95072d` (merged `a2b208c`). As specified.

**Description:**
Appendix A rows 7–8. The speed round today reads content for every mastered sense and then keeps
≤ 20; it must pick first and hydrate only the picked rows. Gate/stress batteries read one sense.

**Acceptance Criteria:**
- [x] `SpeedRoundComposer.recognition_items` selects `store.select_columns('id, exercise_type, {content}, ladder_level, word_sense_id, complexity_tier')` (db string unchanged).
- [x] New `_pick(candidates, size) -> list[row]` holds today's sampling (same `random` calls in the same order); `_select` keeps its signature and returns `[_to_item(r) for r in _pick(...)]`; `compose` calls `_pick`, then `store.hydrate(picked, language_id=language_id, db=self.db)`, then `_to_item`; fewer than `MIN_BATTERY` after hydration → `reason='too_few_items_for_a_battery'`.
- [x] `LadderService._fetch_exercises_for_levels` selects `store.select_columns('id, exercise_type, {content}, complexity_tier, ladder_level, tags, word_sense_id')` (db string unchanged) and hydrates `resp.data` with `language_id` before grouping; `tags.variant` logic unchanged.
- [x] Tests: storage mode hydrates only the ≤ 20 picked rows (not all candidates); dropped items handled; db mode unchanged.
- [x] Existing tests pass unchanged: `tests/test_speed_round.py test_counter_match_round_trip.py test_security_route_hardening.py test_study_session_ordering.py`.

**Files to Create / Modify:**
- `services/vocabulary_ladder/speed_round.py`, `services/vocabulary_ladder/ladder_service.py`.
- `tests/test_exercise_content_battery_readers.py` — new.

**Verification:**
`OFFLINE pytest tests/test_exercise_content_battery_readers.py tests/test_speed_round.py tests/test_counter_match_round_trip.py tests/test_security_route_hardening.py tests/test_study_session_ordering.py -q`.

---

## TASK-1021: Prestudy loads content only for the words it will drill (+ on-demand fetch)

**Status:** [x] Done (2026-11-17)
**Feature:** exercise-content-storage
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-1008
**Built:** branch `ecs/d2-prestudy-routes`, commit `7d64886` (merged `c8bb607`); wiki by TASK-1025. The word-list chip shows only for `has_exercises` words and counts the exercises actually loaded. Spec: [[features/test-prestudy.tech]].

**Description:**
Appendix A row 9, the largest fan-out. Owner decision 2026-11-17 (ADR open question 1): the
prestudy payload carries exercise content only for the senses the prime will drill, plus a
`has_exercises` flag for every linked sense; words the learner adds to the drill set ("I don't
know this", and any other client path that adds words) fetch their exercises on demand. This is a
product change: it applies in every `EXERCISE_CONTENT_SOURCE` mode, not only `storage`.

**Acceptance Criteria:**
- [x] The drill rule is computed server-side and matches the client rule in
  `static/js/prestudy/prestudy.js` exactly (find it: the prime drills unknown/encountered/learning
  words by p_known, see the comments near the stage lists and `status()`); one Python function,
  unit-tested at its boundaries, with a comment pointing at the JS rule and vice versa.
- [x] `build_prestudy_payload` loads content only for drill senses: `_load_exercises(db,
  drill_sense_ids, language_id=...)` selects `store.select_columns('id, word_sense_id,
  exercise_type, {content}, ladder_level')` (db string unchanged), pages as today, then calls
  `store.hydrate(rows, language_id=language_id, db=db)` once before `group_exercises`. The payload
  adds `has_exercises: [sense_id, …]` for all linked senses (from `senses_with_exercises`, row ids
  only).
- [x] New endpoint (in `routes/tests/prestudy.py`, same auth/ownership checks as the payload route)
  returns grouped, trimmed exercises for a list of sense ids; ids outside the test's linked senses
  are ignored; at most 20 senses per call; same `group_exercises`/`trim_exercise` shape as the
  payload.
- [x] `prestudy.js`: `exercisesFor` reads the loaded map; adding a word to the drill set triggers
  one fetch for senses not yet loaded (batched, no duplicate in-flight requests) before that
  word's exercises are needed; per-word counts, minute estimates and "has ladder exercises"
  checks use `has_exercises` instead of the content map; a failed fetch degrades to the
  no-exercise path for that word (no crash, no generation request).
- [x] `request_generation` / `senses_with_exercises` keep using DB row ids, so neither a hydration
  miss nor an unloaded (non-drill) sense ever queues generation (test asserts).
- [x] Tests: drill-rule boundaries; payload contains content only for drill senses and
  `has_exercises` for all; endpoint filters foreign ids and caps at 20; storage mode hydrates
  once with the language; db mode select string unchanged; a JS unit test (vitest, see
  `vitest.config.js`, `tests/unit/`) for the on-demand fetch (dedupe, failure path).
- [x] Existing tests pass: `tests/test_prestudy.py test_prestudy_session.py test_pagination.py
  test_latency_caching.py` (update fixtures only where the payload shape intentionally changed,
  and say which).
- [x] [[features/test-prestudy.tech]] updated by the integrator (TASK-1025) from this task's notes.

**Files to Create / Modify:**
- `services/prestudy.py` — drill rule, `_load_exercises`, `build_prestudy_payload`.
- `routes/tests/prestudy.py` — on-demand exercises endpoint.
- `static/js/prestudy/prestudy.js` — on-demand fetch, `has_exercises`.
- `tests/test_exercise_content_prestudy_reader.py` — new; `tests/unit/prestudy-ondemand.test.js` — new.

**Verification:**
`OFFLINE pytest tests/test_exercise_content_prestudy_reader.py tests/test_prestudy.py tests/test_prestudy_session.py tests/test_pagination.py tests/test_latency_caching.py -q`; `npx vitest run tests/unit/prestudy-ondemand.test.js`.

---

## TASK-1022: Route readers (typed grading, admin preview) and the reference-set script

**Status:** [x] Done (2026-11-17)
**Feature:** exercise-content-storage
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-1008
**Built:** branch `ecs/d2-prestudy-routes`, commit `00684e8` (merged `c8bb607`). The typed re-grade hydrates after the `cloze_typed` type check and fails open on any error. The reference-set script imports the store after `bootstrap()`.

**Description:**
Appendix A rows 10–12: the server-side `cloze_typed` re-grade on `POST /api/practice/attempt`,
the admin word preview, and the offline reference-set snapshot.

**Acceptance Criteria:**
- [x] `_grade_typed_if_needed` selects `store.select_columns('exercise_type, {content}, language_id, word_sense_id')`, sets `row['id'] = exercise_id`, calls `store.hydrate([row], language_id=row.get('language_id'), drop_missing=False, db=get_db())`; content `None` → return `None` (fail open, as on a lookup failure today). If `tests/test_practice_route_tail.py` asserts the select string, update that assertion only.
- [x] `preview_word` selects `store.select_columns('id, exercise_type, {content}, complexity_tier, ladder_level, word_sense_id')` and hydrates before the jumbled preparation; the response gains `word_sense_id` per exercise (admin-only, additive).
- [x] `scripts/build_exercise_gen_reference_set.py::fetch_exercise_snapshot` selects `store.select_columns('id, word_sense_id, language_id, exercise_type, ladder_level, complexity_tier, tags, {content}')` and hydrates; output (`payload`) unchanged.
- [x] Tests cover all three in db and storage modes (monkeypatched store).

**Files to Create / Modify:**
- `routes/practice.py` — `_grade_typed_if_needed` only.
- `routes/vocab_admin.py` — `preview_word` only.
- `scripts/build_exercise_gen_reference_set.py` — `fetch_exercise_snapshot` only.
- `tests/test_exercise_content_route_readers.py` — new; `tests/test_practice_route_tail.py` only if needed as above.

**Verification:**
`OFFLINE pytest tests/test_exercise_content_route_readers.py tests/test_practice_route_tail.py tests/test_security_route_hardening.py -q`.

---

## TASK-1023: Backfill, verify and archive script

**Status:** [x] Done (2026-11-17)
**Feature:** exercise-content-storage
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** TASK-1008
**Built:** branch `ecs/e-backfill`, commits `b9e174d`, `20e8071` (merged `c4ef849`). Archives are deterministic gzip parts of at most 1 MiB (the bucket limit) listed with sha256 in `manifest.json`; every `--archive-*` flag needs `--language all`; `--archive-semdisc` takes `--semdisc-function-file` or `--semdisc-function-rpc` (no RPC was added) and `--semdisc-order`; exit codes 0 / 1 / 2; the state file is used in export mode only.

**Description:**
`scripts/backfill_exercise_content.py` exports existing content as version-0 files, verifies that
every row's DB content equals its file, repairs through the store, and writes the pre-drop archive.
It never updates `exercises` except in `--repair` (≈ 13 rows per repaired sense).

**Acceptance Criteria:**
- [x] CLI: `--language {zh,ja,en,all}` (required), `--senses 1,2,3`, `--limit N`, `--dry-run`, `--verify`, `--repair` (only with `--verify`), `--archive-all TAG`, `--archive-sense-less`, `--batch-senses 200`, `--concurrency 8`, `--state-file PATH` (default `data/exercise_content_backfill/state-{lang}.json`), `--report PATH` (default `data/exercise_content_backfill/report-{lang}-{UTC timestamp}.json`).
- [x] Sense discovery: one `rpc('exercise_content_live_versions', {'p_language_id': id})`; rows per batch of ≤ 200 senses with `services.pagination.fetch_all`, selecting `id, word_sense_id, language_id, exercise_type, is_active, content_version, content`, ordered by `id`.
- [x] Export (default mode): a sense whose rows are all at version 0 gets `store.content_path(lang, sense, 0)` = `store.encode_sense_file(...)` over **all** its rows (active and inactive) via `store.backend().put`; an existing v0 is verified, never overwritten (`AlreadyExists` → verify). Senses at version > 0 are verified only. Uploads run on `ThreadPoolExecutor(concurrency)`.
- [x] `--verify`: no writes; per row, `canonical(DB content) == canonical(file[(sense, row.content_version)][id])`; mismatch kinds `missing_file`, `missing_exercise`, `content_diff`, `mixed_versions`; exit code 1 if any.
- [x] `--repair`: for each sense with a mismatch, `store.write_sense(db, sid, lang, update_contents={id: DB content for every row of the sense})`; refuses (exit 2, message) unless `store.write_mode() == 'dual'`.
- [x] `--archive-all TAG`: per language one gzip JSONL object `_archive/exercises-content-{TAG}/{lang}.jsonl.gz` (one line per row: id, word_sense_id, language_id, exercise_type, is_active, content_version, content) plus `_archive/exercises-content-{TAG}/manifest.json` (row counts and sha256 per object); no overwrite.
- [x] `--archive-sense-less`: the rows with `word_sense_id IS NULL` to `_archive/exercises-no-sense-{YYYYMMDD}.json`.
- [x] `--archive-semdisc` (owner decision 2026-11-17): gzip JSONL of every row of `backup_semdisc_content_20261115` and `semdisc_rewrite_work` to `_archive/semdisc-20261115/{table}.jsonl.gz`, plus `apply_semdisc_notes.sql` (the function definition, read with `pg_get_functiondef` through a read-only RPC or passed in from a file the operator exports — the script must not need SQL-editor access) and a `manifest.json` (row counts, sha256); no overwrite; test with a fake db.
- [x] Resumable: completed sense ids recorded in the state file after each batch; a re-run skips them; `--dry-run` writes nothing (no files, no state) except the report.
- [x] Report JSON: `{language, mode, senses, rows, files_written, files_verified, skipped_from_state, mismatches: [...], anomalies: [...], started_at, finished_at}`.
- [x] Tests with a local fake db and `InMemoryBackend`: export writes one file per sense equal to `encode_sense_file`; a re-run writes nothing; verify finds a tampered content, a missing exercise and a missing file; sense-less rows never enter sense files; dry-run writes nothing; state resume; archive manifest sha256 matches; `--repair` refuses in `db` write mode.

**Files to Create / Modify:**
- `scripts/backfill_exercise_content.py` — new.
- `tests/test_backfill_exercise_content.py` — new.

**Verification:**
`OFFLINE pytest tests/test_backfill_exercise_content.py -q`; `python scripts/backfill_exercise_content.py --help` exits 0 offline.

---

## TASK-1024: Orphan-file sweep script

**Status:** [x] Done (2026-11-17)
**Feature:** exercise-content-storage
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** TASK-1008
**Built:** branch `ecs/e-backfill`, commit `ba132be` (merged `c4ef849`). Added `--allow-empty-live-set` (an empty live set next to deletable files deletes nothing otherwise); default report `data/exercise_content_sweep/report-{lang}-{UTC}.json`.

**Description:**
`scripts/sweep_exercise_content.py` deletes files no row points at (superseded versions, files of a
writer that lost a race or crashed, senses wiped by the admin), after a grace period that protects
writers between upload and commit. Each kept file also costs ~0.6 KB of `storage.objects` in the
database.

**Acceptance Criteria:**
- [x] CLI: `--language {zh,ja,en,all}`, `--apply` (default is a dry run), `--grace-hours 24`, `--report PATH`.
- [x] Live set from `rpc('exercise_content_live_versions')`; files from `store.backend().list('{code}/')`; names parsed with `^(\d+)\.v(\d+)\.json$`.
- [x] Delete iff (sense, version) not live **and** `created_at` older than the grace period; `created_at` missing → keep and report; unparseable names → report, keep; anything under `_archive/` is never listed or touched; deletes batched by 100.
- [x] Report: counts of kept-live, kept-grace, deleted (or would-delete), unknown names, bytes freed.
- [x] Tests with `InMemoryBackend` (settable `created_at`) and a fake RPC cover each rule and the dry run.

**Files to Create / Modify:**
- `scripts/sweep_exercise_content.py` — new.
- `tests/test_sweep_exercise_content.py` — new.

**Verification:**
`OFFLINE pytest tests/test_sweep_exercise_content.py -q`; `python scripts/sweep_exercise_content.py --help` exits 0 offline.

---

## TASK-1025: Phase-1 integration run (offline) and wiki update

**Status:** [x] Done (2026-11-17)
**Feature:** exercise-content-storage
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** TASK-1009, TASK-1010, TASK-1011, TASK-1012, TASK-1013, TASK-1014, TASK-1015, TASK-1016, TASK-1017, TASK-1018, TASK-1019, TASK-1020, TASK-1021, TASK-1022, TASK-1023, TASK-1024
**Built:** `claude/dreamy-brahmagupta-40a4gq`, commits `e508f1c`, `5c98e43` and the wiki commit. Six `--no-ff` merges, no conflicts. Contract fix: `FakeContentDB` aligned with the commit SQL. `tests/test_exercise_content_integration.py` covers scenarios 1–8 in db/db, shadow/dual and storage/dual. The db-mode serve and write paths of `c3cb106` and of the integrated branch were run over the same fake DB: identical payloads and calls (prestudy differs only by the owner's drill-only change). Full suite: the same 48 failures + 1 collection error as `c3cb106` in every flag combination (environment: jieba, MeCab/ipadic, Supabase credentials at import).
**Review fixes (2026-11-17):** the independent review's verdict was *needs fixes* (1 major, 3 minor), all fixed after the integration with tests (see ADR-049, "Review fixes"):
(1) TASK-1018: cut-over step 3a enforces in SQL that the session RPC migration is applied and that the archives plus a verify marker from the last 24 hours are in Storage; step 0e shows the same checks read-only.
(1, cont.) TASK-1023: a clean full `--verify` writes `_archive/verify-ok/<UTC>.json`.
(2) TASK-1022: db mode again sends the pre-ADR select string for the typed re-grade and the reference-set script.
(3) TASK-1011/1014/1023: `write_sense(expected_version=...)` and `store.base_version`. The audio and hant fix scripts and `--repair` refuse a stale read-modify-write instead of overwriting.
(4) TASK-1014: the fix scripts hydrate with offline limits (whole chunk, 300 s).
Full suite after the fixes: 5466 passed, with the same 48 environment failures.

**Description:**
Run the real store, writers, readers, backfill and sweep together over `FakeContentDB` +
`InMemoryBackend`, fix whatever disagrees, then bring the wiki in line.

**Acceptance Criteria:**
- [x] `tests/test_exercise_content_integration.py` scenarios, all offline:
  1. `WRITE=dual`: `render_all` on a new sense → one file, rows at that version, column content equal to the file.
  2. Backfill export over legacy (version-0) rows → v0 files; `--verify` passes.
  3. `queue_drain` scoped regen (levels {4}) in `dual` → new version; other levels' content byte-identical; sweep with grace 0 deletes exactly the superseded file.
  4. `SOURCE=storage`: `get_session` and `get_extra_round` over a fake RPC that honours `p_include_content` → payload equal to the `db`-mode payload on the same fixture (after the same post-processing).
  5. `SOURCE=shadow`: one tampered file → exactly one `content_diff` WARNING; payload equal to `db` mode.
  6. Two threads updating different exercises of one sense → final file holds both edits.
  7. Missing file in `storage`: fallback on → served from the column with a WARNING; fallback off → item dropped, `content_unavailable` when nothing is left.
  8. Prestudy payload and speed round in `storage` equal `db` mode.
- [x] `OFFLINE pytest -q` over the whole suite: no failures beyond the baseline ones noted at the top of this file.
- [x] Wiki: `wiki/database/schema.tech.md` (`exercises`: `content_version`, `dedupe_key`, real index list), `wiki/features/practice-engine.tech.md` (signature + `content_version` in the return shape + `p_include_content`), `wiki/features/practice-extra-rounds.tech.md` (`get_review_ahead_items` signature), this file's statuses, `wiki/tasklist/master.md`, `wiki/log.md`.

**Files to Create / Modify:**
- `tests/test_exercise_content_integration.py` — new.
- Production files of packages a–e only to fix integration defects (name each fix in the log entry).
- The wiki pages above.

**Verification:**
`OFFLINE pytest tests/test_exercise_content_integration.py -q` and `OFFLINE pytest -q`.

---

## TASK-1026: Apply the Phase-1 migrations and deploy with both flags at `db` (OPERATOR)

**Status:** [~] In Progress (both migrations live 2026-11-17; deploy of the Phase-1 code and the app walkthrough pending)
**Feature:** exercise-content-storage
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** TASK-1016, TASK-1017, TASK-1025

**Description:**
Operator task, not for agents (LIVE-DB, owner approval). Deploy the Phase-1 code with
`EXERCISE_CONTENT_SOURCE=db` and `EXERCISE_CONTENT_WRITE=db` (behaviour identical to today; the
code works before the migrations). Then apply `migrations/exercise_content_storage.sql`, then
`migrations/exercise_content_session_rpcs.sql`, on staging first if one exists.

**Acceptance Criteria:**
- [x] Both migrations applied, 2026-11-17:
  - `exercise_content_storage` went in through the Supabase migration tool. Every function body and comment is md5-identical to the repo file.
  - `exercise_content_session_rpcs` was run by the owner in the SQL editor. The editor paste turned line endings into CRLF; with `\r` removed, the bodies are md5-identical to the file, and comments match exactly.
  - No staging project exists.
  - Before applying, the live 5-argument bodies were md5-checked: identical to `get_practice_session_language_scope.sql` and `practice_review_ahead.sql`.
- [ ] `tests/sql/test_exercise_content_storage.sql` inside its own `ROLLBACK` on production: not run yet. It writes, then rolls back, and needs owner approval.
- [x] `tests/sql/check_function_acls.sql` passes for the ADR-049 objects: none of the five functions is executable by `anon` or `authenticated`. Pre-existing violations elsewhere, untouched by these migrations:
  - `anon` holds SELECT on 28 public tables, including `users`, `user_tokens`, `token_transactions` and `trusted_devices`. RLS is on for all of them.
  - RLS is off on `backup_semdisc_content_20261115` and `semdisc_rewrite_work`, which are dropped at the cut-over.
- [x] Live functions:
  - `get_practice_session(uuid,smallint,text,smallint,numeric,boolean)` and `get_review_ahead_items(uuid,smallint,integer,integer,integer[],boolean)` are the only overloads; the three dead functions are gone.
  - Both have `search_path = public, pg_temp` and are callable by `service_role` only.
  - Bucket `exercise-content` exists: `public = false`, 1 MB limit, `application/json`.
- [x] Session RPCs called on production in SQL, the way PostgREST calls them (5 named arguments), for the learner with the largest ladder (zh, maintenance mode):
  - 24 exercise items, all with `content` and `content_version` 0;
  - with `p_include_content => false`: 24 items, no `content` key;
  - review-ahead: 10 of 10 items with `content` and `content_version`.
- [ ] Practice session checked in the app after the deploy.
- [~] Database size: 494,431,379 → 495,873,171 bytes (+1.4 MB).
  - The storage migration accounts for 16 KB.
  - No app table gained rows in the window (`exercises`, `llm_calls`, `app_error_logs`, `exercise_attempts`, `storage.objects`: 0 new rows in 90 minutes) and no other client was connected.
  - The rest is catalog/TOAST overhead from replacing large function bodies; not traced further.

**Verification:**
The catalog queries above, a practice session in the app, `SELECT pg_size_pretty(pg_database_size(current_database()))`.

---

## TASK-1027: Turn on dual writes, backfill and verify (OPERATOR)

**Status:** [ ] Not Started
**Feature:** exercise-content-storage
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** TASK-1026

**Description:**
Operator task. Set `EXERCISE_CONTENT_WRITE=dual` on Railway **and in every shell or `.env` that
runs content scripts** (upload, fat seed, staged authoring, generation batch), restart the web
workers, then backfill `en`, `ja`, `zh` (dry run first) and verify all.

**Acceptance Criteria:**
- [ ] `python scripts/backfill_exercise_content.py --language en --dry-run` report reviewed; then real runs for `en`, `ja`, `zh`.
- [ ] `--verify --language all` exits 0: 0 mismatches, every row's content present in its file.
- [ ] Recorded in `wiki/log.md`: files written, Storage bytes, `storage.objects` rows and size, database size before/after.

**Verification:**
The verify report; `SELECT count(*), pg_size_pretty(pg_total_relation_size('storage.objects')) FROM storage.objects WHERE bucket_id = 'exercise-content'`.

---

## TASK-1028: Shadow reads for at least 7 days (OPERATOR)

**Status:** [ ] Not Started
**Feature:** exercise-content-storage
**Type:** infra
**Complexity:** S (1-3h, spread over ≥ 7 days)
**Depends On:** TASK-1027

**Description:**
Operator task. `EXERCISE_CONTENT_SOURCE=shadow`, restart. Learners still get DB content; files are
compared in the background.

**Acceptance Criteria:**
- [ ] ≥ 7 days and ≥ 2,000 compared groups (`exercise_content.shadow_summary` lines).
- [ ] 0 `content_diff`; every `missing_file` / `missing_exercise` explained (rows written while some writer still had `WRITE=db`) and fixed with `--verify --repair`.
- [ ] A final `--verify --language all` exits 0.

**Verification:**
Railway logs filtered on `exercise_content.shadow_`; the verify report.

---

## TASK-1029: Serve from Storage and measure latency (OPERATOR)

**Status:** [ ] Not Started
**Feature:** exercise-content-storage
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** TASK-1028

**Description:**
Operator task. Measure, flip, measure. Rollback at any time: `EXERCISE_CONTENT_SOURCE=db`.

**Acceptance Criteria:**
- [ ] Baseline with `SOURCE=db` and after with `SOURCE=storage`, same day, same machine: `data/eval/latency-2026-11/harness/bench.py` (1 discarded warm-up, 30 samples) for `study-session`, `practice/session`, `tests/<slug>/prestudy` (a zh test with ≥ 100 linked senses) and `practice/speed-round`. Pass: warm median and p90 each within +10% of baseline (ADR-042 / [[evaluations/latency-2026-11-11]]).
- [ ] Cold cost recorded: the first request after a restart, and the storage GET p50/p95 from the hydrate INFO lines.
- [ ] One full day on `storage` with no `exercise_content.db_fallback` WARNING; results filed under `wiki/evaluations/exercise-content-latency-<date>.md`.

**Verification:**
The bench output and the evaluation page.

---

## TASK-1030: Cut-over — archive, drop the column, VACUUM FULL, sweep (OPERATOR)

**Status:** [ ] Not Started
**Feature:** exercise-content-storage
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** TASK-1029, TASK-1018

**Description:**
Operator task (LIVE-DB, owner approval). Only after ≥ 7 days on `storage` without fallback
warnings.

**Acceptance Criteria:**
- [ ] Same day (step 3a refuses otherwise):
  - `--archive-all <YYYYMMDD>`, `--archive-sense-less` and `--archive-semdisc` written, and the manifests checked;
  - then `--verify --language all` exits 0, which writes `_archive/verify-ok/<UTC>.json`;
  - cut-over step 0e shows every column true.
- [ ] `migrations/exercise_content_drop_column.sql` steps 0–5 run in order; `EXERCISE_CONTENT_DB_FALLBACK=0` set and workers restarted right after step 3.
- [ ] Sessions, prestudy, speed round, gate/stress and typed grading work in the app; `v_ladder_judge_reject_rates` still returns rows.
- [ ] Database size recorded before/after (expected ≈ 470 → ~355 MB); `python scripts/sweep_exercise_content.py --language all` dry run reviewed, then `--apply`.
- [ ] Owner decision 2026-11-17: archive `backup_semdisc_content_20261115`, `semdisc_rewrite_work` and the `apply_semdisc_notes(jsonb)` definition (`backfill_exercise_content.py --archive-semdisc`), verify the manifest, then the cut-over migration drops them (−~21 MB).

**Verification:**
Size queries in step 5; an app walkthrough; `wiki/log.md` entry.

---

## TASK-1031: Post-cut-over clean-up

**Status:** [ ] Not Started
**Feature:** exercise-content-storage
**Type:** refactor
**Complexity:** M (3-8h)
**Depends On:** TASK-1030

**Description:**
Remove the transition code once the column is gone, and make the repo match the live database.

**Acceptance Criteria:**
- [ ] `read_mode()` accepts only `storage` (any other value logs one ERROR and is treated as `storage`); `select_columns` maps `{content}` to `content_version`; `rpc_content_args()` always returns `{'p_include_content': False}`; the DB fallback and `EXERCISE_CONTENT_DB_FALLBACK` are removed; `write_mode` `db` removed (writes always file + commit RPC); the `tests/conftest.py` pin updated; tests adjusted.
- [ ] `tests/sql/test_session_budget_settings.sql` no longer inserts `content`; `scripts/sql/check_jumbled_and_definition_match.sql` deleted or replaced by a Python check over `store.fetch_sense`.
- [ ] Per `migrations/CLAUDE.md`: `git mv` the files fully superseded by the applied migrations (at least `get_practice_session_language_scope.sql`, `practice_review_ahead.sql`; check `phase17_drop_deprecation_wrappers.sql`, `task743_context_free_exercise_caps.sql`, `phase9_get_exercise_session.sql` object by object and keep any multi-object file still canonical for a live object) with rows in `migrations/archive/README.md` and the markers checked.
- [ ] Wiki: `wiki/database/schema.tech.md` (no `content`; `uq_exercises_context_free_variant_v2`), ADR-049 status → accepted with the measured numbers, this file and `master.md` statuses, `wiki/log.md`.

**Files to Create / Modify:**
- `services/exercise_content/*`, `config.py`, `tests/conftest.py`, `tests/test_exercise_content_*.py`, `tests/sql/test_session_budget_settings.sql`, `scripts/sql/check_jumbled_and_definition_match.sql`, `migrations/` (archive moves), `migrations/archive/README.md`, the wiki pages above.

**Verification:**
`OFFLINE pytest -q` (baseline failures only); `git grep -n "'content'" services/exercise_content` shows no DB-column use; `OFFLINE pytest tests/test_migration_security_lint.py -q`.

---
