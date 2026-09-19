---
title: "Lookahead Pre-Teaching — Task Breakdown"
feature: lookahead-preteaching
prose_page: ../features/lookahead-preteaching.md
tech_page: ../features/lookahead-preteaching.tech.md
total_tasks: 12
done: 1
---

# Lookahead Pre-Teaching — Task Breakdown

**Sequencing note.** TASK-783 and TASK-784 are the critical path and are
independent of everything else. The algorithm tasks (785–790) can be built in
parallel, but enabling them before 784 has run produces cohorts of one or two
words. Do not reorder on the grounds that the algorithm is "the real work" — it
is measurably not the constraint.

---

## TASK-782: Variant simulation harness

**Status:** [x] Done (2026-09-19)
**Feature:** lookahead-preteaching
**Type:** infra
**Complexity:** M
**Depends On:** none

Read-only harness scoring pre-teaching variants over the live catalogue.
Delivered as `scripts/simulate_preteach_variants.py`; results in
[[evaluations/preteach-variants-2026-09-19]].

---

## TASK-783: Unjam `generation_queue` and give it a lease + priority

**Status:** [ ] Not Started
**Feature:** lookahead-preteaching
**Type:** bug
**Complexity:** S
**Depends On:** none

**Description:**
Seven `generation_queue` rows have been `status = 'running'` since 2026-08-21
with no lease expiry. `_open_queue_sense_ids` de-duplicates against
`pending`/`running`, so those seven senses can never be re-queued — the queue is
not merely stalled, it is permanently poisoned for those rows. The demand-driven
generation path this feature depends on has never actually run: zero rows carry
`reason = 'subscribe_topup'`. Add a claim lease, reclaim the stuck rows, and add
a priority column so lookahead demand drains ahead of speculative work.

**Acceptance Criteria:**
- [ ] `generation_queue` has `claimed_at timestamptz` and `priority smallint NOT NULL DEFAULT 50`.
- [ ] `_claim_batch` writes `claimed_at`; rows `running` with `claimed_at < now() - GENERATION_LEASE` are re-claimable.
- [ ] The 7 pre-existing `running` rows are reset to `pending` by the migration.
- [ ] `_claim_batch` orders by `priority ASC, requested_at ASC`.
- [ ] `REASON_LOOKAHEAD = 'lookahead'` exists and maps to priority 10.
- [ ] A unit test proves a stale `running` row is re-claimable and is no longer hidden by `_open_queue_sense_ids`.

**Technical Notes:**
Spec §2.3. Lease default 1 hour; the drain's own advisory lock already prevents
concurrent drains, so the lease only has to cover crashes.

**Files to Create / Modify:**
- `migrations/task783_generation_queue_lease.sql` — columns, backfill, reclaim UPDATE
- `services/vocabulary_ladder/queue_drain.py` — `_claim_batch`, `_release`, reason constant, priority
- `tests/test_queue_drain_lease.py` — new

**Verification:**
`select status, count(*) from generation_queue group by 1` shows 0 rows `running`
older than the lease. Then `PYTHONPATH=. python -m pytest tests/test_queue_drain_lease.py`.

---

## TASK-784: Demand-first generation — rank and generate 500 senses per language

**Status:** [ ] Not Started
**Feature:** lookahead-preteaching
**Type:** infra
**Complexity:** XL
**Depends On:** TASK-783

**Description:**
This is the critical path. Exercise generation has been frequency-first, so the
inventory covers the words a learner at this level already knows: the mean Zipf
of a sense *with* exercises is 4.77 (ja) against an `ability_zipf` of 5.03. Of
the ~17 words blocking an average ja test, 1.8 are drillable; in zh, using
ladder levels only, zero are. Re-point generation at demand — how many catalogue
tests a sense blocks — and run 500 senses per language.

**Acceptance Criteria:**
- [ ] A `preteach_demand(language_id)` view or function ranks unknown test-linked senses by the number of tests they block.
- [ ] `enqueue_coverage_gaps` orders by that demand rank instead of frequency.
- [ ] ≥500 ja and ≥500 zh senses have ≥3 active exercises covering Ring 1 and Ring 2 families.
- [ ] Re-running `simulate_preteach_variants.py --language 3` (gated) shows in-band share ≥0.60, up from 0.119.
- [ ] Generation cost and wall clock are recorded in the eval page for the next sizing.

**Technical Notes:**
Ring 1 + Ring 2 families means `phonetic_recognition`/`definition_match` plus
`cloze_completion` and `cloze_typed`/`morphology_slot`.

**Two generation routes exist; pick per batch, do not assume the automated one.**

| route | spend | wall clock | notes |
|---|---|---|---|
| automated (`run_content_build.py`) | ~$0.024/sense | **~5.5 min/sense** — ~46 h per 500 | ~13 serial LLM calls/sense (3 core + ~4 type-gen + ~6 judges), all on `qwen/qwen3.7-plus` for zh/ja |
| **`batch-exercise-generation` skill** | subscription, notional | bounded by authoring passes, 8 senses/batch | the model writes the assets in-session through the real `word_assets` write path; the skill's own header says the 5.5 min/sense automated path "is the reason the backlog exists" |

The skill already ranks its worklist by how many **active tests reference the
sense** — which is most of this task's demand ordering, already built. The
refinement this task adds is filtering to senses the learner does not *know*, not
inventing the ranking. Check `export_exercise_worklist.py` before writing SQL.

Its ranked ja pool is **665 senses** (not 7,118), which matches the 702 unknown
test senses measured independently in
[[evaluations/preteach-variants-2026-09-19]]. The 500-sense target is ~75% of
that pool.

**Do not restate ≈$12 / ≈46 h as the cost of this task without first running
TASK-794** — that figure prices the automated route only.

**Files to Create / Modify:**
- `migrations/task784_preteach_demand.sql` — the demand ranking
- `services/vocabulary_ladder/queue_drain.py` — `coverage_gaps` ordering
- `data/` batch inputs/outputs per the skill's convention

**Verification:**
`PYTHONPATH=. python scripts/simulate_preteach_variants.py --language 3` —
`baseline in band` unchanged, gated `a1_commit/b2_working/c3_greedy` in-band ≥0.60.

---

## TASK-785: Extract `selection_p_known` as the single implementation

**Status:** [ ] Not Started
**Feature:** lookahead-preteaching
**Type:** refactor
**Complexity:** S
**Depends On:** none

**Description:**
`P_known(s)` is defined in `get_recommended_tests` and is about to be needed by
the cohort RPC. Its prior offset has already been corrected once (0.5 → 0.85
crossing); a second copy will diverge. Extract it to one SQL function and have
both call it.

**Acceptance Criteria:**
- [ ] `public.selection_p_known(p_sense_id integer, p_ability_zipf numeric) RETURNS numeric` exists, `IMMUTABLE`.
- [ ] `get_recommended_tests` calls it and is proven output-identical against a frozen copy of its current body.
- [ ] `tests/sql/test_task748_vocab_ranking.sql` still pins `unknown = 0.1496` for a sense at `ability_zipf`.

**Files to Create / Modify:**
- `migrations/task785_selection_p_known.sql`
- `tests/sql/test_task785_p_known_parity.sql` — new

**Verification:** run both SQL test files; the parity test must show zero row differences.

---

## TASK-786: `preteach_cohorts` schema

**Status:** [ ] Not Started
**Feature:** lookahead-preteaching
**Type:** feature
**Complexity:** S
**Depends On:** none

**Description:**
Create `preteach_cohorts` and `preteach_cohort_members` per spec §2.1–2.2,
including the partial unique index that makes "one open cohort per (user,
language)" the concurrency control, and the `unknown_at_open` / `p_known_open`
snapshot columns that §8.1 depends on.

**Acceptance Criteria:**
- [ ] Both tables exist with the columns and CHECK constraints in §2.1–2.2.
- [ ] `preteach_cohorts_one_open` partial unique index exists; a second insert with `closed_at IS NULL` raises `23505`.
- [ ] `status = 'starved'` is a valid member state.
- [ ] RLS policies match the existing per-user tables in this schema.

**Files to Create / Modify:**
- `migrations/task786_preteach_cohorts.sql`
- `tests/sql/test_task786_cohort_schema.sql` — new

**Verification:** apply; attempt two open cohorts for one (user, language) and confirm the unique violation.

---

## TASK-787: `open_preteach_cohort` RPC

**Status:** [ ] Not Started
**Feature:** lookahead-preteaching
**Type:** feature
**Complexity:** L
**Depends On:** TASK-785, TASK-786

**Description:**
Implement cohort selection per §3.1: top-N pool from `get_recommended_tests`,
blocking senses at `P(s) < 0.5`, ordered by `(−demand, key_C, sense_id)`, through
the supply gate, into the tables, with starved members enqueued at priority 10.
Supports `p_force` for dry-run demand extraction.

**Acceptance Criteria:**
- [ ] Returns the §4 shape, including `starved_count`.
- [ ] Demand dominates the axis-C tiebreak — a sense blocking 4 pool tests outranks a less-known sense blocking 1.
- [ ] `preteach_ranking` selects `greedy` | `frontier` | `frequency`; `greedy` is default.
- [ ] Supply gate: 2 active exercises → `starved`; 3 → admitted; 3 with one `is_active = false` → `starved`.
- [ ] `{skipped: 'disabled'}` when `preteach_enabled = 0`; `{skipped: 'cohort_open'}` when one is open and `p_force` is false.
- [ ] `E_NOABILITY` when `selection_vocab_ability` cannot identify a crossing.
- [ ] Starved senses appear in `generation_queue` with `reason = 'lookahead'`.
- [ ] Two concurrent calls yield one cohort.

**Technical Notes:**
`SECURITY DEFINER`, `SET search_path = public, pg_temp`, matching
`build_daily_session`. The route layer supplies the authenticated user id.

**Files to Create / Modify:**
- `migrations/task787_open_preteach_cohort.sql`
- `tests/sql/test_task787_cohort_selection.sql` — new

**Verification:** call with `p_force := true` for the live ja learner; inspect member ordering and `starved_count` against the eval's 1.8 / 15.7 split.

---

## TASK-788: `preteach_cohort_status` + `close_preteach_cohort`

**Status:** [ ] Not Started
**Feature:** lookahead-preteaching
**Type:** feature
**Complexity:** M
**Depends On:** TASK-786

**Description:**
Readiness read (§3.4) and the close path that writes `unknown_at_close` and
`p_known_close`. `preteach_cohort_status` must be `STABLE` — a read may never
mutate — and `starved` members must be excluded from the readiness denominator,
or today's inventory makes every cohort permanently unready.

**Acceptance Criteria:**
- [ ] `preteach_cohort_status` is `STABLE` and returns the §4 shape.
- [ ] A 9-starved / 1-learned cohort reports `ready`, not `waiting`.
- [ ] `state = 'waiting'` until `days_open >= preteach_lead_days`, even at 100% learned.
- [ ] `expired` at `preteach_deadline_days`.
- [ ] `close_preteach_cohort` is idempotent and snapshots `unknown_at_close`.

**Files to Create / Modify:**
- `migrations/task788_preteach_status.sql`
- `tests/sql/test_task788_readiness.sql` — new

**Verification:** fixture cohorts at each state boundary; assert the returned `state`.

---

## TASK-789: Queue C in the ladder intake

**Status:** [ ] Not Started
**Feature:** lookahead-preteaching
**Type:** feature
**Complexity:** M
**Depends On:** TASK-787

**Description:**
Add `_nominate_from_lookahead` to `practice_session_service` and drain it ahead
of the evidence and pack queues (§4). It reads open-cohort members with
`status = 'pending'`, re-checks `_senses_with_supply` (exercises can be
deactivated between open and drain), marks admitted rows `subscribed`, and
returns them. Queues A and B are not modified.

**Acceptance Criteria:**
- [ ] Cohort members are subscribed before any evidence or pack nomination.
- [ ] Members failing the re-check are marked `starved`, not silently skipped.
- [ ] `source` in the existing top-up log line reads `lookahead` / `lookahead+evidence` / etc.
- [ ] With no open cohort, intake is byte-identical to today.
- [ ] `LADDER_TOPUP_MAX_PER_CALL` still bounds the call.

**Files to Create / Modify:**
- `services/practice_session_service.py` — `_maybe_top_up_ladder`, `_nominate_from_lookahead`
- `tests/test_practice_ladder_intake.py` — extend

**Verification:** `PYTHONPATH=. python -m pytest tests/test_practice_ladder_intake.py`.

---

## TASK-790: `preteach_boost` in the unified score

**Status:** [ ] Not Started
**Feature:** lookahead-preteaching
**Type:** feature
**Complexity:** S
**Depends On:** TASK-789

**Description:**
Add a bounded additive bonus (0.25) to `ladder_priority` for open-cohort members
so Acquisition anchors on them (§3.3). Additive and bounded so a gated or
relapsing word still outranks a fresh cohort word. Do not re-weight `α` — that
changes sessions for learners with no cohort.

**Acceptance Criteria:**
- [ ] Cohort members outrank equivalent non-cohort ladder words in Acquisition.
- [ ] A `relearning` word still outranks a `new` cohort word.
- [ ] `α`, `β`, `γ`, `δ` are unchanged.
- [ ] With `preteach_enabled = 0`, session output is identical to today.

**Files to Create / Modify:**
- `migrations/task790_preteach_boost.sql` — `get_practice_session` ladder-priority term
- `tests/sql/test_task790_boost_ordering.sql` — new

**Verification:** fixture ladder with one cohort word and one relapsing word; assert the relapsing word ranks first.

---

## TASK-791: `build_daily_session` release tiebreak

**Status:** [ ] Not Started
**Feature:** lookahead-preteaching
**Type:** feature
**Complexity:** M
**Depends On:** TASK-788

**Description:**
Two additions to the daily resolver (§4): call `preteach_cohort_status` before
the greedy fill (closing or opening as needed), and in hydration order the
per-skill recommendations by `(test_id = ANY(target_test_ids)) DESC,
ABS(elo_diff)`. The budget solver, spacing penalty and value model must be
provably untouched.

**Acceptance Criteria:**
- [ ] A `ready` cohort's released test is hydrated first for its skill.
- [ ] `used_minutes` and `objective_value` are identical with and without a cohort, on a frozen fixture.
- [ ] `daily_session_targets` gains `preteach: {cohort_id, state, released: []}`.
- [ ] With `preteach_enabled = 0`, output is identical across the 20-scenario fixture matrix.
- [ ] A released test already in `completed_test_ids` is not re-served (TASK-705 carry-over preserved).

**Technical Notes:**
The live RPC is the TASK-710 consolidated single-loop body, **not**
`migrations/phase13_build_daily_session.sql` — verify with `pg_get_functiondef`
before editing. See [[resolver-hydration-skill-gap]].

**Files to Create / Modify:**
- `migrations/task791_build_daily_session_preteach.sql`
- `tests/sql/test_task791_preteach_hydration.sql` — new

**Verification:** run the 20-scenario matrix with the flag off and diff against the recorded baseline; then on, with a fixture cohort.

---

## TASK-792: Cohort telemetry and the FE surface

**Status:** [ ] Not Started
**Feature:** lookahead-preteaching
**Type:** feature
**Complexity:** M
**Depends On:** TASK-791

**Description:**
Surface cohort state in the practice and daily-session UI, and expose the
counters the eval needs. The honest framing is "words for the week ahead" —
§6.1 deliberately does not commit to one test, so the UI must not promise one.

**Acceptance Criteria:**
- [ ] `/api/practice/session` response carries `preteach: {cohort_id, learned, pending, starved, state}`.
- [ ] The practice surface shows cohort progress; with no cohort it renders exactly as today.
- [ ] New `data-i18n` keys land in **all four** `static/i18n/*.json` (see [[i18n-applytodom-clobbers-defaults]]).
- [ ] A weekly job records cohort outcomes for §8.5.

**Files to Create / Modify:**
- `routes/practice.py`, `static/js/session/players/practice.js`, `static/i18n/*.json`

**Verification:** open the practice surface with and without an open cohort; confirm no raw i18n keys render.

---

## TASK-793: Reconcile `target_new_rate` with the cohort budget

**Status:** [?] Blocked — needs a product decision
**Feature:** lookahead-preteaching
**Type:** feature
**Complexity:** S
**Depends On:** TASK-789

**Description:**
`target_new_rate` is `daily_minutes // 6` per **week** — 5 words/week at 30
min/day — against a default cohort of 12 words on a 10-day deadline. The two
numbers are inconsistent: sharing one budget makes a cohort take 2.4 weeks and
miss its own deadline every time. Either the cohort holds a separate intake
budget, or `target_new_rate` rises for pre-teach words, or the cohort shrinks.

**Blocked on:** which of the three. The choice changes both the daily minutes a
learner spends on acquisition and how many tests a week the feature can unblock,
so it is not an implementation detail.

**Acceptance Criteria:** (write once unblocked)

---

## TASK-794: Measure the fat-prompt route against the 13-call chain

**Status:** [ ] Not Started
**Feature:** lookahead-preteaching
**Type:** infra
**Complexity:** M
**Depends On:** none

**Description:**
The automated exercise path makes roughly **13 serial LLM calls per sense** —
`vocab_prompt1_core`, `vocab_prompt2_exercises`, `vocab_prompt3_transforms`, the
per-type generators (`ladder_l4_morphology_generation`,
`ladder_l8_collocation_repair_generation`, `ladder_syn_ant_generation`,
`ladder_particle_selection_generation` for ja) and ~6 judges. That call count,
not token spend, is where 5.5 min/sense comes from, and wall clock is the only
binding cost ([[task515-batch-economics]]).

Test the hypothesis that **one call to a stronger model beats thirteen to a
cheap one**: collapse the three core prompts into a single fat prompt that emits
core + exercises + transforms in one response. There is direct precedent —
`gemini-3.5-flash-lite` met a 10s single-call budget at p95 7.7s for fat-seed
generation, while `deepseek-v4-flash` failed at 45–58s on token bloat rather
than reasoning class ([[fat-seed-live-latency-2026-09]]).

**The structural obstacle is real and must be addressed head-on:**
`vocab_prompt2_exercises` and `vocab_prompt3_transforms` are rendered *from*
prompt 1's output, which is why even the human path runs two stages. A fat
prompt has to carry the chain internally rather than break it, and its output
must still validate through the existing `LadderExerciseRenderer` — this task
does **not** get to relax validation to make the numbers work.

**Acceptance Criteria:**
- [ ] The exact call count and per-call latency of the current path is measured on ≥10 ja senses, from `llm_calls` (query `judge_<name>`, not the template key — see [[llm-calls-task-name-namespace]]).
- [ ] A fat single-call prompt is drafted and run on the same ≥10 senses, on ≥2 candidate models.
- [ ] Output is compared against the chain's on: validator pass rate, judge reject rate, and a manual read of 20 exercises.
- [ ] Wall clock and spend per sense reported for: chain, fat-prompt, and the `batch-exercise-generation` skill route.
- [ ] A recommendation per language, filed as an evaluation page. Quality regression is a stop, not a trade — the judges exist because these items are shown to learners.

**Technical Notes:**
Reasoning-class models are not automatically the answer: `qwen3.8-max` needs
`max_tokens` ~16k and 100–330 s/call, and breaks on CJK in JSON mode
([[qwen38-max-is-a-reasoning-model]]) — a single call that takes 5 minutes has
bought nothing. The candidate shape is a fast strong non-reasoning model.
Consider also the `item_N` batch envelope ([[batch-prompting-item-envelope]]),
which is wired for sense-gen only — N senses per call is an independent
multiplier on top of fewer calls per sense.

**Files to Create / Modify:**
- `scripts/measure_exercise_gen_routes.py` — new, read-only
- `wiki/evaluations/exercise-gen-routes-<date>.md` — new

**Verification:**
`PYTHONPATH=. python scripts/measure_exercise_gen_routes.py --language ja --limit 10`;
the report must state wall clock per sense for all three routes side by side.

---
