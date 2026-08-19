---
title: Daily Session Runner (`/session`) — Technical Specification
type: page-tech
status: complete
prose_page: study-session.md
last_updated: 2026-08-07
dependencies:
  - "route: app.py::study_session_page() → templates/study_session.html"
  - "blueprint: routes/study_session.py (study_session_bp, url_prefix /api/study-session)"
  - "service: services/test_service.py::get_or_create_daily_load"
  - "RPC: build_daily_session(p_user_id uuid, p_language_id smallint, p_date date)"
  - "table: daily_test_loads (test_ids, daily_session_targets, completed_test_ids, completed_blocks)"
  - "frontend: static/js/session/controller.js + player_registry.js + players/*"
  - "i18n: static/i18n/{en,es,zh,ja}.json (session.*, test_list.*)"
breaking_change_risk: medium
---

# Daily Session Runner (`/session`) — Technical Specification

Prose counterpart: [[pages/study-session]].

## Architecture Overview

```
GET /session ──► app.py::study_session_page()  ──► templates/study_session.html
                                                        │
                              static/js/session/controller.js (ES module)
                                                        │
                       GET /api/study-session?language_id=L
                                                        │
                    routes/study_session.py::get_study_session()
                         │                                   │
        test_service.get_or_create_daily_load()      daily_test_loads
                         │                            .daily_session_targets
        ┌────────────────┴────────────────┐           .completed_blocks
   STUDY_PLAN_ENABLED + plan?        else legacy               │
        │                                                     │
   RPC build_daily_session                                    │
        │                                                     │
        └──────────────► build_session_queue() ◄──────────────┘
                                │
              _round_robin_tests()  +  _build_practice_chunks()
                                │              │
                          _interleave_practice()
                                │
                         ordered queue → controller.js
                                │
                     player_registry.getPlayer(item).mount(stage, ctx)
```

The ordering layer is **pure Python in the route**, not in the RPC — deliberately, so it
can be iterated and unit-tested cheaply (TASK-703 decision).

## API / RPC Surface

### `GET /api/study-session?language_id=<int>`
- **Purpose:** return today's single ordered queue plus resume position.
- **Arguments:** `language_id` (query, required, int; parsed by `parse_language_id`).
- **Returns:**
  ```jsonc
  { "load_date": "YYYY-MM-DD", "language_id": 1, "study_plan_enabled": true,
    "progress": { ... }, "next_index": 0,
    "queue": [
      { "kind": "test", "id": "<uuid>", "slug": "...", "test_type": "listening",
        "title": "...", "elo_rating": 1200, "slot_type": "new|retry|replay",
        "is_completed": false },
      { "kind": "practice", "id": "practice_acq_1", "mode": "acquisition",
        "minutes": 10, "is_completed": false },
      // TASK-714 plannable surfaces — dispatched on `kind`, not `test_type`.
      { "kind": "flashcards", "id": "flashcards_1", "skill": "flashcards",
        "cards": 15, "is_completed": false },
      { "kind": "dual_translation", "id": "dual_translation_1",
        "skill": "dual_translation", "is_completed": false }
    ] }
  ```
  `load_date` is the learner's **local** date (ADR-022 / TASK-716), resolved from
  `user_study_plans.timezone` by `services.day_boundary` — not the UTC date.
- **Errors:** `bad_request` on a missing/invalid `language_id`; `server_error` on
  resolver failure.
- **Auth:** `@supabase_jwt_required`.
- **Side effects:** may create today's `daily_test_loads` row via
  `get_or_create_daily_load` (which itself may lazily trigger `compute_weekly_plan`
  on `E_NOWEEK` — TASK-700).

Surface items are emitted from `daily_session_targets.surface_counts`, which the
resolver populates with **hydrated** (not merely budgeted) counts — a flashcards
block with nothing due is reported as a shortfall rather than served as an empty
block. A `daily_test_loads` row written before TASK-714 has no `surface_counts`
key and degrades to no surface items.

### `POST /api/study-session/complete-block`
- **Purpose:** mark one non-test block done for today — a practice chunk
  (TASK-703) or a surface block (TASK-714).
- **Arguments:** `{ language_id: int, block_id: str }` where `block_id` must be in
  `_valid_block_ids(targets)` — a chunk id today's targets actually generate
  (`practice_acq_1`, `practice_maint_2`, `flashcards_1`, `dual_translation_1`, …).
- **Returns:** success; idempotent append to `daily_test_loads.completed_blocks`.
- **Errors:** `bad_request` on an unknown / not-today `block_id`.
- **Auth:** `@supabase_jwt_required`.
- **Side effects:** for **surface** blocks only, calls
  `record_session_progress(p_kind='surface', p_skill=<flashcards|dual_translation>)`
  so the weekly counter advances. The attempt id is a deterministic uuid5 over
  (user, language, load_date, block_id) — surfaces have no `test_attempts` row,
  and the uuid5 lets the RPC's existing `session_progress_log` dedupe make a
  retried POST a no-op. Practice chunks are **not** credited here: the practice
  service owns their seconds ledger and doing it twice would double-count.
- **Note:** test slots do **not** use this endpoint — they use the pre-existing
  `POST /api/tests/daily-load/complete`.

## Ordering Algorithm

`build_session_queue(tests, targets, completed_blocks, user_id, load_date)`
([routes/study_session.py:178](../../routes/study_session.py#L178)) composes three pure
helpers. Determinism is the contract: two GETs must yield identical order.

1. **`_stable_seed(user_id, load_date)`** — `int(sha256(f"{user_id}:{load_date}")[:8], 16)`.
   Seeds a `random.Random` so ordering is fixed per learner per day.

2. **`_round_robin_tests(tests, rng)`** — groups by `test_type` into an `OrderedDict`,
   `rng.shuffle`s only the *group order*, then drains the groups with a deque
   round-robin. Within a type, resolver order is preserved. Because the interleave
   itself is structural, determinism never depends on the RNG — the seed only decides
   which type leads.

3. **`_build_practice_chunks(targets, completed_blocks)`** — expands the two base blocks
   in `_PRACTICE_BLOCKS` (`practice_acq` → mode `acquisition` /
   `practice_acquisition_min`; `practice_maint` → `maintenance` /
   `practice_maintenance_min`) via `_chunk_minutes(total, max_chunk=10)`
   (`25 → [10, 10, 5]`), producing ids `{base}_{n}` with per-chunk `is_completed`.

4. **`_interleave_practice(test_seq, chunks)`** — inserts chunk *i* before test index
   `((i+1) · T) // (P+1)`, so P chunks land at roughly even fractions through the T
   tests. A trailing-insert guard handles `idx == total_tests`.

**Invariants:** no two same-type tests adjacent while another type has items; practice
appears mid-session; identical order across GETs; `next_index` still points at the first
incomplete item (`_next_incomplete_index`).

## Component Specification

### `controller.js` (ES module, `static/js/session/controller.js`)
- **Module state (`session`):** `languageId`, `queue[]`, `index`, `player`,
  `_completing` (re-entrancy latch).
- **Boot:** `DOMContentLoaded → init()` — reads `localStorage.selectedLanguageId`
  (redirects to `/language-selection` when absent), awaits `LinguaMetadata.load()`,
  then `loadSession()`.
- **`loadSession()`** — `authFetch('/api/study-session?language_id=…')`; throws on
  `!res.ok`; hides the spinner; `showEmpty()` on an empty queue, else `renderStart()`.
- **`runCurrent()`** — skips completed items, destroys the previous player, clears the
  stage, mounts `getPlayer(item)` with `{item, languageId, onComplete, onSkip}`, then
  calls `LinguaI18n.applyToDOM(stage)` — required because `applyToDOM` normally runs
  once at page load, before the stage exists.
- **`persistCompletion(item)`** — POSTs to `/api/tests/daily-load/complete` (tests) or
  `/api/study-session/complete-block` (practice). **Must check `res.ok`**: `authFetch`
  resolves rather than rejects on 4xx/5xx, so a server rejection would otherwise be
  indistinguishable from success.
- **`onItemComplete()`** — guarded by `session._completing`; one silent retry on
  failure, then a toast that warns but still advances (the learner did the work).
- **`onItemSkip()`** — sets `item.skipped = true` and advances **without** marking
  complete, so the item returns on resume.

### Accessibility (TASK-709)
- `#sessionProgress`: `aria-live="polite"`, `data-i18n-aria="session.progress_label"`.
- `#sessionDots`: `role="list"`; each dot `role="listitem"` with
  `aria-label = T('session.dot_label', {type, state})`, built from `itemTypeLabel()`
  and `dotStateLabel()`.
- `showSummary()` renders `<ul class="session-results">` rows (icon, title, type,
  state). Skipped rows differ by **opacity + line-through + amber**, not colour alone.
- `escapeHtml()` guards every interpolated title — they are server-supplied and land in
  both `innerHTML` and an attribute context.
- `data-i18n-aria` is genuinely supported: `static/js/i18n-manager.js:184-187`.
- **i18n contract:** `itemTypeLabel()` resolves `T('test_list.' + test_type)`, so every
  servable `test_type` needs a `test_list.<type>` key in all four locales.
  `test_list.pitch_accent` was missing in all four and was added 2026-08-07 — see
  [[i18n-applytodom-clobbers-defaults]] failure mode.

## Key Architectural Decisions

1. **Decision:** ordering lives in Python (`routes/study_session.py`), not in
   `build_daily_session`.
   - **Rationale:** cheap to iterate and unit-test; the RPC stays a *selection* concern.
   - **Alternatives rejected:** ordering inside the RPC — would have made every
     ordering tweak a migration.
2. **Decision:** determinism via a `(user_id, load_date)` hash seed rather than storing
   the order.
   - **Rationale:** stable resume with no extra column and no write on read.
   - **Alternatives rejected:** persisting queue order in `daily_test_loads`.
3. **Decision:** practice chunk ids are synthesised (`practice_acq_1`), validated
   against today's targets rather than stored in a lookup table.
   - **Rationale:** `completed_blocks` is already jsonb; no schema change.
4. **Decision:** completion failure warns but still advances.
   - **Rationale:** blocking a learner who already did the work is worse than a
     possibly-unrecorded slot; the slot simply reappears tomorrow.

## Security Considerations

- Both endpoints require JWT (`@supabase_jwt_required`); all queries scope to `g.user`.
- `block_id` is validated against `_valid_practice_block_ids(targets)` — an arbitrary
  string cannot be appended to `completed_blocks`.
- `language_id` goes through `parse_language_id`.
- Server-supplied titles are escaped client-side before entering `innerHTML`/attributes.
- Completion is server-side; a client cannot mark another user's slot done.

## Testing Strategy

- **`tests/test_study_session_ordering.py`** (20 tests) — adjacency, determinism across
  two builds, chunk splitting, interleave positions, `next_index` resume.
- **`tests/test_daily_load_shortfall.py`** — hydration-shortfall WARNING (TASK-702).
- **`tests/test_daily_load_retry_slot.py`** — retry-slot contract (TASK-704).
- **`tests/test_daily_load_fallback_type.py`** — legacy fallback type labels (TASK-707).
- **Gaps (explicit):** no automated a11y assertions and no JS unit tests for
  `controller.js`; the ARIA work is verified structurally, not with assistive tech.

## Related Pages

- [[pages/study-session]] — prose counterpart
- [[pages/pages-overview]], [[features/study-plans.tech]], [[features/practice-engine.tech]]
- [[algorithms/daily-session-implementation-analysis.tech]] — findings F1–F16
- [[api/rpcs.tech]], [[database/rpcs.tech]]
