---
title: "ADR-043: One database call for GET /api/study-session (read bundle) — evaluation"
status: accepted (option B, targeted merges; A deferred)
date: 2026-11-11
---

# ADR-043: One database call for `GET /api/study-session` — evaluation

Status: **proposed**. This is the risk/upside evaluation the developer asked for before any
implementation ([[tasklist/latency.tasks]] TASK-930). Nothing is built.

## Context

After [[decisions/ADR-042-request-scoped-caching-and-static-asset-caching]], the daily-session
GET still makes **14 sequential Supabase round trips** in steady state (today's load already
exists, no new-word intake). Each costs 53–108 ms from Railway (TASK-774), so ~0.7–1.5 s of every
session-page load is network wait. The same GET runs twice per session (page load, and again
at the end-of-session summary for the optional tail).

### The 14 reads (code inventory, 2026-11-11)

| # | Read | Feeds | Hard part |
|---|---|---|---|
| 1 | `user_study_plans` `*` (already memoised) | timezone → "today"; excluded modules; prestudy mode | — |
| 2 | `daily_test_loads` `*` for today | test slots, completion | one row; jsonb lists |
| 3 | `tests` 11 cols `.in_(ids)` | queue titles/slugs | only 3 cols reach the response |
| 4 | `test_skill_ratings` + embed `dim_test_types(type_code)` | ELO per slot | embedded object shape; a null embed ends the loop early (latent bug) |
| 5 | rpc `review_governor_state` | governor, quota | skipped when plan excludes `practice` |
| 6 | rpc `ladder_new_word_state` | quota, tail | uses `now()` |
| 7 | `daily_test_loads` targets/completed_blocks | practice chunks, tail gate | **same row as #2**, re-read only because a write may intervene |
| 8 | `user_word_ladder` `!inner` embed, mastered, **no limit** | speed-round offer (only `len ≥ 10`) | unbounded; gated on #7's `excluded_modules` (not #1's) |
| 9 | `tests.vocab_sense_ids` | prestudy | — |
| 10 | `user_vocabulary_knowledge` `.in_` chunks of 200 | prestudy | >200 senses = more calls |
| 11 | `dim_word_senses` + `dim_vocabulary(frequency_rank)` | prestudy prior | left embed may be null; skipped if all known |
| 12 | `user_calibration_state.ability_zipf` | prestudy prior | — |
| 13 | `exercises.word_sense_id` `.in_` chunks, **no limit** | prestudy estimate | one row per exercise → can hit the PostgREST row cap silently |
| 14 | `dim_languages.new_word_minutes_est` | governor/tail | — |

Conditional reads: intro-review rows (`user_word_ladder` ≤500) + `dim_word_senses` `!inner`
(500-id `in_`). Write paths inside the GET: first-of-day `build_daily_session`, new-word intake
(ladder insert + `set_new_words_shortfall`) and `rebuild_today`.

## The proposal

One `SECURITY DEFINER` SQL function `study_session_bundle(p_user_id, p_language_id)`
(service_role only) returns every read above in one jsonb. Flask calls it first and pre-fills
`services/request_cache.py` under the same keys the existing loaders use, so **all Python
logic stays as is**: each loader finds its data already cached. Any key missing from the bundle
falls back to the loader's own query.

## Upside

| | Today | With the bundle |
|---|---|---|
| Round trips, steady state | 14 (+ chunking for big tests) | **1** |
| Network wait from Railway | ~0.7–1.5 s | ~0.05–0.1 s |
| Saved per session-page visit | — | ~0.7–1.4 s ×2 (load + summary tail) |
| DB work | same queries, 14 separate statements | same queries in one function (less per-statement overhead) |

Side benefits: #2/#7 midnight race (two `now()` calls) disappears; chunked `.in_` lists become
one query; the endpoint's latency stops scaling with the number of linked senses.

## Risks

Ranked by likelihood × impact.

1. **Two sources of truth (high, long-term).** Every bundled read exists twice: the Python
   loader and the SQL bundle. When someone later adds a column or filter to a Python query, the
   bundle keeps serving the old shape **silently** — the loader is never called. This is the
   main cost, and it never goes away.
2. **Stale data after a write inside the GET (high impact).** Intake, `rebuild_today` and the
   first-of-day build all write mid-request. Today only `new_word_state` is invalidated. With
   the bundle, #2/#3/#4/#7/#9–#13 and the governor must all be dropped on any write, or the
   learner is served the pre-rebuild queue. One missed invalidation = wrong session.
3. **"Today" computed in two places.** Python (zoneinfo) vs SQL (`plan_local_date`). They agree
   for valid zones (ADR-022), but a disagreement keys #2/#5/#6/#7 on the wrong day.
4. **Exact JSON shapes.** Embedded objects (#4, #8, #11, intro), numeric/timestamp rendering
   and `None` vs missing keys must match what PostgREST returns, or Python branches differently
   (e.g. #4's null-embed early exit).
5. **Behaviour that differs by design.** #13 (and #8) may be silently truncated by PostgREST's
   row cap today; SQL would return the full answer — a different (more correct) prestudy
   estimate. Must be decided, not discovered.
6. **Gating differences.** #5 is gated on the plan's `excluded_modules`, #8 and intro reads on
   the day's targets. The bundle should compute unconditionally (cheap) and let Python decide.
7. **Payload size.** #8 and #13 are unbounded; the bundle must cap/aggregate them (count ≥ 10;
   distinct sense ids).
8. **Test fakes.** Existing route tests fake the DB with `rpc() → None`; the bundle must treat
   `None`/errors as "no bundle" and fall back.
9. **Blast radius.** Helpers are shared with `/api/tests/daily-load`, Practice, prestudy and the
   study-plan page; memo keys must be namespaced so other endpoints are unaffected.
10. **Security.** Same pattern as existing RPCs (`p_user_id` from the verified JWT, service_role
    only); low risk if the migration follows `migrations/CLAUDE.md`.

## Mitigations (if built)

- **Parity harness:** a script that, for N real users (read-only), calls the bundle and each
  loader directly and diffs the JSON; run before every deploy that touches either side, plus a
  unit test pinning the loader select strings to the bundle's documented contract.
- **Bundle-wide invalidation:** a single `request_cache.invalidate('bundle')` called by every
  writer and after `rebuild_today`; the bundle is used only for steady-state GETs.
- **Date check:** the bundle returns its `today`; Python recomputes from the bundled plan row and
  discards date-keyed entries on mismatch.
- **Graceful fallback:** any RPC error → per-read path (today's behaviour).

## Alternatives

| Option | Round trips | Risk | Effort |
|---|---|---|---|
| **A. Full read bundle** (above) | 14 → 1 | medium–high (risks 1–2 permanent) | L (1–2 days + parity harness) |
| **B. Targeted merges**: reuse #2 for #7 when nothing wrote (−1); #3+#4 in one embedded query (−1); #5+#6 in one RPC (−1); prestudy inputs #9–#13 in one RPC (−4); #14 into the in-memory DimensionService cache (−1) | 14 → ~6 | low: each merge replaces one helper's query, no duplicated logic | M (~1 day) |
| **C. Parallel reads** (threads) | critical path ~5 levels | medium: supabase-py client is not thread-safe here (see playwright.config.js), needs per-thread clients | M |
| **D. Port the whole assembly to SQL** | 1 | high (rewrite of tested Python) | XL |

## Recommendation

**B first, then decide on A with measurements.** B captures ~60% of the round trips (≈0.5–0.8 s
per load from Railway) with none of the permanent two-sources-of-truth cost: each merged read
still has exactly one implementation. If the remaining ~6 calls still matter after B, build A
with the parity harness and bundle-wide invalidation in place from day one.

## Decision (2026-11-11)

Developer: "target merges first" — **option B**. Option A is deferred until B is live and
measured.

## Consequences

Built (repo, 2026-11-11); each merged read keeps its old per-table path as the fallback, so the
app behaves the same before and after `migrations/latency_2026_11_session_merges.sql`:

| # | Merge | Where | Needs migration |
|---|-------|-------|-----------------|
| #2→#7 | targets row reuses the daily-load row read earlier in the request (per-request cache, invalidated on rebuild and on `set_new_words_shortfall`) | `services/test_service.py` `daily_load_row_key`, `routes/study_session.py` | no |
| #3+#4 | test rows + skill ratings in one PostgREST embedded select (falls back to two queries) | `TestService._enrich_daily_load` | no |
| #5+#6 | `review_governor_state` + `ladder_new_word_state` → `new_word_state_inputs` | `PracticeSessionService._new_word_state` | **yes** |
| #9–#13 | prestudy tests / knowledge / frequency / ability / exercise coverage → `prestudy_plan_inputs` | `services/prestudy.py` `plan_for_tests` | **yes** |
| #14 | minutes-per-new-word p50 cached per process for 10 min (failures not cached) | `services/study_plan_service.py` | no |

`services/optional_rpc.py` `call_bundle` treats a missing bundle function (PGRST202) as absent
for 10 minutes, so before the migration each worker pays one failing probe per bundle per
10 minutes.

**Measured before the migration** (repo code vs 5896204, same sandbox → Supabase link, 30
samples, wall ms; full method in [[evaluations/latency-2026-11-11]]):

| Endpoint | run | DB calls | mean | median | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|---|
| `study-session` | before | 14 | 3892 | 3882 | 3943 | 4055 | 4132 | 4144 |
| | after | **11** | 3016 | **3006 (−23%)** | 3056 | 3101 | 3190 | 3222 |
| `practice/session` | before | 18 | 4896 | 4900 | 5019 | 5090 | 5218 | 5256 |
| | after | 18 | 4937 | 4889 (0%) | 4982 | 5346 | 6099 | 6331 |
| `study-plan` | before | 7 | 1901 | 1898 | 1929 | 1930 | 1932 | 1932 |
| | after | **6** | 1703 | **1689 (−11%)** | 1753 | 1771 | 1786 | 1789 |

`practice/session` is unchanged until the migration (its saving is the #5+#6 bundle); its p99
outliers in the after run are single slow Supabase responses, not extra calls. Each round trip
from this sandbox costs ~270 ms, so absolute times are larger than from Railway; the call counts
carry over.

**After the migration** (expected, not yet measured): `study-session` 11 → 6, `practice/session`
18 → 17. Verify with `scripts/check_session_merges_parity.py` (bundle vs per-table reads for real
learners, read-only) and re-run the HTTP harness. Tests: `tests/test_session_merges.py` (14).

What stays harder: two more SQL functions whose outputs must match the Python fallbacks (pinned
by the parity tests and script); the fallbacks can be removed once the bundles have been live for
a while.
