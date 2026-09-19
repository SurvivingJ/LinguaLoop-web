---
title: "Vocabulary-Aware Test Selection — Task Breakdown"
feature: vocabulary-aware-test-selection
prose_page: ../features/vocabulary-aware-test-selection.md
tech_page: ../features/vocabulary-aware-test-selection.tech.md
total_tasks: 12
done: 10
last_updated: 2026-09-17
---

# Vocabulary-Aware Test Selection — Task Breakdown

TASK-744 … TASK-752, plus TASK-779, TASK-780 and TASK-781. Highest existing ID at
time of writing: TASK-743.

**Before starting any task, verify its status against source.** Wiki tasklists
in this repo mark shipped work as not started
([[tasklist-status-drifts-from-code]]).

**Standing constraints for every task here**
- Migrations: idempotent `CREATE OR REPLACE`, header stating problem / fix /
  safety, plus an `APPLIED LIVE` line, mirroring
  `migrations/task732_ja_skill_rating_elo_reseed.sql`.
- Tests: `PYTHONPATH=. pytest tests/ ...` with an explicit `tests/` path.
  "No tests collected" is a hidden import error, not a missing suite.
- Any migration touching an existing RPC must be built on the **live** body from
  `pg_get_functiondef`, never on a repo or archive file.
- `process_test_submission` is **not** modified by any task in this list.

**Dependency order**

```
745 ✓ (delivered by Calibration TASK-766/765: calibration_zipf_to_elo, live)

746 ─► 747 ─► 752
        │
744 ─► 748 ─┴─► 749
        │        750 (blocked: needs ≥30 first attempts per (language, type))
        │        751 (independent, parallel)
        └─► 780 ─► 781 ✓ (replay: weight 0 vs sum vs product — done, 2026-09-17)
```

747 calls `calibration_zipf_to_elo` (745, already live), so it depends on 746
only.

---

## TASK-744: `selection_tuning` settings table

**Status:** [x] Done — applied live 2026-09-10 · **Type:** infra · **Complexity:** XS · **Depends On:** none

**Outcome (2026-09-10).** `migrations/task744_selection_tuning_table.sql` applied
live at 11:34:48 UTC and re-applied at 11:38:01 UTC. The re-run changed nothing
(every `updated_at` still 11:34:48), and an operator-set value (0.42) survived a
seed re-run inside a rolled-back transaction. `authenticated` is refused on both
UPDATE and SELECT (42501). Seeds live: `vocab_weight 0`, `elo_weight 1.0`,
`unknown_target 0.15`, `unknown_tolerance 0.10`, `tier_ceiling_offset 2`. Added
beyond the spec: CHECKs so `unknown_tolerance > 0` and the weights are
non-negative, plus an `updated_at` touch trigger.

**Description:**
One-row-per-key numeric settings table so selection constants are tunable
without redeploying, and so `vocab_weight = 0` is an instant rollback for
TASK-748. A settings row is used rather than a new function parameter because a
defaulted parameter creates the ambiguous overload the repo already had to clean
up once (`migrations/get_recommended_tests_drop_ambiguous_overload.sql`).

**Acceptance Criteria:**
- [ ] `selection_tuning (key text primary key, value numeric not null, updated_at timestamptz default now())`.
- [ ] Seeded: `vocab_weight=0`, `elo_weight=1.0`, `unknown_target=0.15`, `unknown_tolerance=0.10`, `tier_ceiling_offset=2`.
- [ ] `vocab_weight` ships at **0** — inert on arrival.
- [ ] RLS: no insert/update grant to `authenticated`. A learner must not tune their own recommender.
- [ ] Re-running the migration does not reset an operator-modified value (`ON CONFLICT DO NOTHING`).

**Files:** `migrations/task744_selection_tuning_table.sql`

**Verification:** Apply twice; confirm seeds present, second run changes nothing,
and an `UPDATE` from an `authenticated` role is denied.

---

## TASK-745: `calibration_zipf_to_elo` mapping function

**Status:** [x] Done — delivered by Calibration (TASK-766, applied live as TASK-765) · **Type:** feature · **Complexity:** S · **Depends On:** none

**Delivered, not built here.** `public.calibration_zipf_to_elo(numeric)` shipped in
`migrations/calibration_user_state_and_zipf_to_elo.sql` and is live. Verified
2026-09-10: 6.25→875, 5.25→1175, 5.0→1250, 4.5→1400, 4.2→1550, 3.85→1681,
3.8→1700, 3.25→1925, clamping 7.0→875 and 1.0→1925; STABLE, and its ELO anchors
are read from `dim_complexity_tiers` at call time. The former contract block is
resolved: Calibration's `ability_zipf_85` **is** the 85% known-share crossing, and
TASK-764 removed the 1-in-4 guess floor so it measures knowledge, not accuracy.
The planned `migrations/task745_calibration_zipf_to_elo.sql` was therefore never
written, and the Python agreement test lives in
`scripts/verify_calibration_state.py --self-test` rather than
`tests/unit/test_calibration_zipf_to_elo.py`.

**Description:**
Map `user_calibration_state.ability_zipf` to an ELO on the same ladder the
content was seeded from. Anchors pair `dim_complexity_tiers.initial_elo`
(875/1175/1400/1550/1700/1925) with `difficulty_scorer._REF_ZIPF`
(6.25/5.25/4.50/4.20/3.80/3.25), interpolated piecewise-linearly and clamped to
[875, 1925] — no extrapolation past the ladder.

**The ELO half must be read from `dim_complexity_tiers` at call time, not
hardcoded.** Three copies of the difficulty→tier bands already have to be kept
in step ([[two-difficulty-to-tier-maps]]); this must not become a fourth.

**Acceptance Criteria:**
- [ ] `public.calibration_zipf_to_elo(numeric) RETURNS integer`, `IMMUTABLE`-safe or `STABLE` as the tier read requires.
- [ ] Exact hits on all six anchors.
- [ ] Strictly monotone **decreasing** in Zipf (rarer vocabulary → higher ELO).
- [ ] Clamps: `zipf = 8.0 → 875`; `zipf = 1.0 → 1925`; NULL → NULL.
- [ ] `_REF_ZIPF` values sourced from one place; a test asserts SQL and Python agree.

**Technical Notes:**
`frequency_rank` / `ability_zipf` are **Zipf scores, higher = more common**
(`services/vocabulary_ladder/deterministic/lexicon.py:266`). The mapping is
decreasing; getting the sign wrong inverts the whole feature.

**Files:** `migrations/task745_calibration_zipf_to_elo.sql`,
`tests/unit/test_calibration_zipf_to_elo.py`

**Verification:**
`SELECT calibration_zipf_to_elo(z) FROM unnest(ARRAY[6.25,5.25,4.5,4.2,3.8,3.25]) z;`
→ `875,1175,1400,1550,1700,1925`.

---

## TASK-746: `user_skill_rating_adjustments` audit table

**Status:** [x] Done — applied live 2026-09-10 11:49:16 UTC · **Type:** infra · **Complexity:** XS · **Depends On:** none

**Outcome (2026-09-10).** `migrations/task746_user_skill_rating_adjustments.sql`
applied live; 0 rows. All criteria met, plus two not asked for: append-only is
**enforced** by a trigger that refuses UPDATE for every role (DELETE is left
possible so the users FK can cascade), and CHECKs pin `skipped ⇒ elo_before =
elo_after` and `write ⇒ elo_after NOT NULL`. `elo_before`/`elo_after` are NULL
together when the learner had no rating row and nothing was written.

**Description:**
Append-only audit for every calibration-driven rating decision, **including
skips and their reason**. This is both the rate-limit source of truth for
TASK-747 (gate G6) and the evidence trail for TASK-749. Today no rating write in
the system is auditable at all.

**Acceptance Criteria:**
- [ ] Columns per tech spec §2.3, including `reason`, `seed_elo_computed`, `tests_taken_at_write`, `ability_zipf`, `ability_se`.
- [ ] Index `(user_id, language_id, test_type_id, created_at DESC)`.
- [ ] `source` constrained to `calibration_seed | calibration_correct | skipped`.
- [ ] RLS select-own; no client insert.
- [ ] Skipped rows carry `elo_before = elo_after`.

**Files:** `migrations/task746_user_skill_rating_adjustments.sql`

---

## TASK-747: `apply_calibration_to_skill_ratings` guarded writer

**Status:** [x] Done — applied live 2026-09-10 11:52:31 UTC · **Type:** feature · **Complexity:** M · **Depends On:** TASK-746 (TASK-745's map is already live)

**Outcome (2026-09-10).** `migrations/task747_apply_calibration_to_skill_ratings.sql`
applied live and proven by `tests/sql/test_task747_rating_writer.sql`, run on live
inside a rolled-back transaction (the Python integration file named below was not
written — the gates are SQL and are tested in SQL). Evidence:
- **G1 for every real user** — 13 users × 3 languages = 156 G1 audit rows.
  `user_calibration_state` has 0 rows, so G1 is the correct live outcome.
- G2, G3 (se 0.9 and NULL), G4, G5 (an attempt 10 minutes old) and G6 (an
  immediate second call) each skip **and** audit. A deadband no-op does not
  arm G6.
- SEED to 1250 from nothing. Worked examples: **1182 stays 1182** at seed
  1050, and **1182 → 1112** at seed 900.
- A diff of exactly −200 is a no-op; −201 → 1401; `tests_taken` 4 seeds
  undamped. The 150 cap: 1900 → 1750 and 2000 → 1850. The clamp: 700 → 875.
- Another user's JWT and anon are refused. `process_test_submission` md5 is
  identical before and after (`b6b8e04e…209c`).

Deviations: the auth check is stricter than `process_test_submission`'s. That
function's `p_user_id != auth.uid()` lets a NULL subject through; here a NULL
`auth.uid()` is accepted only for `service_role`. The writer covers the four spec
types that have active rating rows in the language, which live **includes
pitch_accent for zh and en** (34 and 38 rows there, a backfill artefact); see
the migration header.

**Description:**
The only path by which calibration writes `user_skill_ratings`. Iterates
reading / listening / dictation / pitch_accent for one (user, language),
applying gates G1-G6 then SEED or CORRECT per tech spec §2.2.

Seed-only is **not** sufficient on its own: the target learner already has 5-12
attempts per Japanese type, so a `tests_taken < 5` rule would never fire for
them. Hence the damped correction path.

**Acceptance Criteria:**
- [ ] Gates G1-G6 each skip **and** write an audit row naming the gate.
- [ ] G5 blocks a write within 1 hour of any `test_attempts` row for that (user, language).
- [ ] G6 blocks a second non-skipped write within 7 days per (user, language, type).
- [ ] SEED when `tests_taken < 5`; CORRECT when `>= 5` **and** `|seed − live| > 200`; else no-op audited `within_deadband`.
- [ ] CORRECT moves by exactly `sign(diff)·min(0.25·|diff|, 150)`.
- [ ] Final clamp `[875, 1925]` — tighter than `process_test_submission`'s `[400, 3000]`.
- [ ] `SECURITY DEFINER` **and** re-checks `p_user_id = auth.uid()`, matching `process_test_submission`'s first statement.
- [ ] `process_test_submission` is byte-identical before and after this task.

**Technical Notes:**
Worked example to pin as a test — pitch accent, live 1182, `tests_taken` 5:
`seed = 1050` → `diff = −132`, inside deadband → **no-op**.
`seed = 900` → `diff = −282` → move 70.5 → **1112**, never a jump to 900.

**Files:** `migrations/task747_apply_calibration_to_skill_ratings.sql`,
`tests/integration/test_calibration_rating_writer.py`

**Verification:**
Capture `pg_get_functiondef` of `process_test_submission` before and after;
diff must be empty. Then run the writer twice in succession and confirm the
second is refused by G6 with an audit row.

---

## TASK-748: vocabulary-aware `get_recommended_tests`

**Status:** [x] Done — applied live 2026-09-10 11:49:05 UTC; **`vocab_weight` raised to 1 by the operator 2026-09-17 — the vocabulary term is now LIVE** · **Type:** feature · **Complexity:** L · **Depends On:** TASK-744

**SWITCHED ON 2026-09-17 (operator).** `selection_tuning.vocab_weight` 1,
`combine_mode` 'sum'. Verified live from the recommender's own output rather than
the settings row: **0 unlinked tests served in any zh type** (7-9 of 10 before),
and `elo_diff` is non-monotonic in 6 of 8 (language, type) lists — impossible on
the weight-0 branch, whose final sort *is* `elo_diff ASC`. Still 10 candidates
per type everywhere, so M5 holds in production and not only in the replay.
`get_recommended_tests` latency measured 5-14 ms → 25-69 ms across all three
languages, against a ~65 ms round trip. **Rollback:
`UPDATE selection_tuning SET value = 0 WHERE key = 'vocab_weight';`**

**Outcome (2026-09-10).** `migrations/task748_get_recommended_tests_vocab_aware.sql`;
live body archived verbatim as
`migrations/archive/task748_prev_get_recommended_tests_live_3arg.sql`
(`tests/test_dictation_tier_cap.py` still reads the older task715 archive,
which is untouched). Three objects: `selection_vocab_ability` and
`recommended_tests_ranked` (service-role only) plus the unchanged-signature
`get_recommended_tests`, whose `vocab_weight = 0` branch is the old query
**verbatim**. That is the rollback guarantee by construction: 48/60 ja tests
share one ELO, so a rewritten ORDER BY could legally break ties differently.
- **Pre-apply proof, live, rollback-only:** all 13 users × en/zh/ja, 39 pairs,
  1,790 rows. At weight 0 every pair is identical in content **and** order to
  the old function, which was itself self-consistent on all 39. At weight 1 no
  per-type count fell (minimum delta 0). Re-run after applying: identical.
  There is 1 `get_recommended_tests` in `pg_proc`.
- **Fixtures** (`tests/sql/test_task748_vocab_ranking.sql`) pass on live. The
  exact expected order holds. The prior gives 0.85 at `ability_zipf` (unknown
  0.1496). uvk evidence beats the prior. A NULL-Zipf sense leaves the
  denominator. An unlinked test gets the cohort median and ranks mid-pack. A
  d9 twin is demoted by the ceiling. A pronunciation row is never read as
  vocabulary. An all-unlinked pool keeps its count.
- **Spec corrections applied:** (a) the prior is 0.85 at `ability_zipf`; (b) the
  no-calibration fallback is the learner's own uvk 85% crossing, not a median.
  Both are recorded in tech spec §3.2.
- **Deviation:** the §4 tier ceiling *demotes* rather than excludes, because
  exclusion contradicts M5. Recorded in §4 and in an amendment to ADR-024.
- Test files: `tests/sql/test_task748_parity.sql` and
  `tests/sql/test_task748_vocab_ranking.sql`. The planned Python integration
  file was not written; there is no DB-backed Python harness for this.

**Description:**
Add the vocabulary coverage term to the ranking. `P_known(s)` is BKT `p_known`
where a row exists, else the Zipf prior `σ(1.5·(zipf − ability_zipf))`. Ranking
becomes the combined score of tech spec §3.3; `rank_in_type <= 10` is retained
but applied to the combined score.

**The Zipf prior is load-bearing, not a nicety.** At difficulty 9 only 10.3% of
a test's senses have any `uvk` row; without the prior the term reads 90% of
content as unknown, scores all fresh tests identically, and degrades as the
catalogue grows.

**Build on the LIVE 3-arg body.** The live signature is
`(uuid, smallint, smallint p_topic_recency_days DEFAULT 14)` — the task715
archive file is 2-arg and stale. Keep the signature identical; creating an
overload is a regression.

**Acceptance Criteria:**
- [ ] Signature unchanged, including `p_topic_recency_days smallint DEFAULT 14`. No new overload in `pg_proc`.
- [ ] Topic-recency `NOT EXISTS` clause from TASK-740 carried through unchanged.
- [ ] `vocab_weight = 0` returns rows **identical in content and order** to the current live function.
- [ ] Unlinked / under-resolved tests get the **cohort median** penalty, not 0 and not `+∞`.
- [ ] A pool of entirely unlinked tests returns the same candidate count as today.
- [ ] Senses with NULL `frequency_rank` are dropped from the denominator, not counted unknown.
- [ ] Tier ceiling applies only when a calibration row exists; excludes nothing without one.
- [ ] Learner's `uvk` rows materialised once in a CTE, not re-read per candidate.
- [ ] `SECURITY DEFINER` + `SET search_path TO 'public'` retained; `p_user_id` carried into every new CTE.

**Files:** `migrations/task748_get_recommended_tests_vocab_aware.sql`,
`tests/integration/test_recommended_tests_vocab.py`;
archive the captured live body under `migrations/archive/`.

**Verification:**
With `vocab_weight = 0`, diff the full result set against a pre-migration
snapshot for all three languages — must be empty. Then set `vocab_weight = 1`
and confirm ordering changes while per-type counts do not fall.

---

## TASK-749: measurement harness and offline replay

**Status:** [x] Done — 2026-09-10 (read-only; `vocab_weight` NOT changed) · **Type:** test · **Complexity:** M · **Depends On:** TASK-747, TASK-748

**Outcome (2026-09-10).** `scripts/measure_selection_quality.py` plus
`tests/test_selection_metrics.py` (metric maths only; it lives in `tests/`
because `tests/unit/` holds JS tests). The 2026-09-08 ja baseline is reproduced
exactly — M1 reading 3/8 and pitch accent 0/5, M2 pitch accent 6/7 (overall
7/27), M3 448 vs 88 — but only under the **operative** definitions the baseline
actually used, which differ from §5.1's wording:
- **M1 is half-open, (60, 85].** Two reading first attempts are stored at
  exactly 60 (3/5); [60, 85] gives 5/8.
- **M2 counts all attempts.** Pitch accent's 7 attempts include 2 retakes;
  over first attempts it is 4/5.
- **M3 rounds** per-type implied abilities before taking the spread.

The replay and the shadow snapshot (`--shadow-out`, a daily JSONL of both arms)
ship in the same script. The shadow mode snapshots live *state*; it does not hook
live requests. Results: [[evaluations/selection-replay-2026-09-10]].

**Description:**
Make the subjective complaint measurable. Computes M1-M5 from tech spec §5.1 —
all from existing columns (`test_attempts.percentage`, `user_elo_before`,
`test_elo_before`); no new instrumentation. Includes the offline replay that
serves as the before/after, since one live learner rules out an A/B.

**Acceptance Criteria:**
- [ ] Reports M1-M5 per (language, test_type) over a date window.
- [ ] Reproduces the 2026-09-08 Japanese baseline exactly: M1 reading 3/8, pitch accent 0/5; M2 pitch accent 6/7; M3 448 vs 88.
- [ ] Replay re-ranks each of the 21 Japanese first attempts against the candidate set **as of that timestamp**, under both arms, and reports the `unknown(t)` distribution of each top-10.
- [ ] Read-only — no writes, safe to re-run.
- [ ] Shadow mode logs both rankings on live calls without changing what is served.
- [ ] Lives under `scripts/`, **not** in `tests/` — it depends on live history and must not gate CI.

**Technical Notes:**
Ability inversion is `user = test_elo − 400·log₁₀(1/s − 1)` with `s` clamped to
[0.05, 0.95]; unclamped, a 100% score is infinite. Note
`log(numeric, numeric)` needs explicit casts in this Postgres.

**Files:** `scripts/measure_selection_quality.py`,
`tests/unit/test_selection_metrics.py` (pure-function metric maths only)

---

## TASK-750: per-test-type ELO offsets (BLOCKED)

**Status:** [?] Blocked · **Type:** feature · **Complexity:** M · **Depends On:** TASK-749

**Blocked on:** ≥30 first attempts per (language, test_type). Live today: reading
8, listening 7, pitch accent 5, dictation 1 — enough to *detect* the 448-point
compression, nowhere near enough to *fit* a correction. *Re-checked 2026-09-10:*
unchanged. ja is reading 8, listening 7, pitch accent 5, dictation 1; zh is
listening 7, reading 6, pinyin 4, classifier 1; en has none. No (language, type)
is within 20 of the gate.

**Description:**
Replace the v1 `type_offset = 0` with fitted per-type offsets, `reading` as
reference. First evidence row, Japanese 2026-09-08:

| type | n | mean % | implied ability | live ELO | error |
|---|---|---|---|---|---|
| dictation | 1 | 87.0 | 1539 | 1209 | −330 |
| reading | 8 | 73.1 | 1498 | 1270 | −228 |
| listening | 7 | 67.1 | 1396 | 1248 | −148 |
| pitch_accent | 5 | 35.4 | 1091 | 1182 | +91 |

**Do not ship these as constants.** They are one learner's residuals, recorded
as the reason the task exists.

---

## TASK-751: per-test-type test ELO reseed

**Status:** [?] Design proposed 2026-09-10 — awaiting a decision (see Technical Notes); nothing reseeded · **Type:** feature · **Complexity:** L · **Depends On:** none (parallel)

**Description:**
Fixes the defect selection cannot: 48 of 60 Japanese tests carry an **identical
ELO across all 8 test types**, because `seed_test_elo` scores prose, which is
type-agnostic. A pitch-accent test and a reading test on the same passage are
rated equally hard; they are not.

This is why the tech spec predicts M1/M2 will move for reading, listening and
dictation before pitch accent. **Selecting better among 60 tests that are all
mis-rated for pitch accent has a low ceiling.**

**Acceptance Criteria:**
- [ ] `test_skill_ratings.elo_rating` varies by `test_type_id` for the same test where the task genuinely differs.
- [ ] Reseed is data-only and idempotent; re-running changes nothing.
- [ ] Tests with real attempt history are **not** reseeded — earned drift is preserved.
- [ ] Follows the TASK-732 header format.

**Technical Notes:**
TASK-732's own header flags a still-unfixed related defect: `dictation_max_words`
splits transcripts on spaces, so Japanese transcripts report 1.1-15 "words"
regardless of length and the dictation cap never excludes anything. Consider
addressing together; it is a separate defect and needs its own decision.

**Design proposal (2026-09-10) — how to derive a per-type ELO for a test with no
attempts.** The spec gives no method. The constraint that decides it is
identifiability. With one learner, the observed quantity per type is
*(user's type ability − test's type offset)*. A test-side offset fitted from
attempts cannot be separated from TASK-750's user-side offset: both explain the
same residual, and fitting both double-counts it.

| option | method | for | against |
|---|---|---|---|
| **A. Pooled residual offset** | `elo(test, type) = elo(test, reading) + δ_type`, with δ taken from pooled first-attempt residuals (implied ability − test ELO) per type. Live ja: pitch accent ≈ −122, reading ≈ +217, so δ_pitch ≈ +339 vs reading. | Ten lines of SQL; directly targets the measured gap. | 5 pitch-accent attempts from one learner. Not identifiable against TASK-750. Keeps every test of a type in the same relative order as its prose. |
| **B. Type-specific content features** | Score each type on what makes *that task* hard, mapped onto the tier ladder the way `seed_test_elo` maps prose. Pitch accent: share of non-heiban words, nakadaka share, mora count, all from `pitch_payload`. Dictation: transcript length in **characters** (which also fixes the space-split bug above) and speech rate. Listening: audio duration / speech rate. Reading: unchanged. | Needs no attempts, so nothing is confounded with TASK-750. Per-test resolution. Deterministic and re-runnable. | Feature → ELO weights are a judgement until data exists. More build: one scorer per type. |
| **C. Hierarchical online offset** | Keep the prose seed and learn `δ_type + ε_test` from every first attempt: a nightly job shrinks ε toward 0 by attempt count, and δ is pooled across tests. | Self-correcting; converges to the truth with traffic. | Needs a writer beside `process_test_submission` (a third ELO writer) or a change to it, which this feature forbids. Until there are several learners it inherits A's confound. |

**Recommendation: B, scoped to pitch_accent first.** It is the one type where
prose is demonstrably the wrong proxy, and its signal already sits in
`pitch_payload`. Map the feature score onto the ladder with the same anchors,
under TASK-732's guard (touch only `total_attempts = 0` rows, idempotent). Then
dictation, bundled with the character-length fix. Fold C in once TASK-750's gate
(≥30 first attempts per type) is met, because by then the confound can be
estimated rather than assumed. A alone is not recommended: it would ship one
learner's residual as a catalogue-wide constant, which TASK-750 already warns
against.

---

## TASK-752: wire calibration completion to the rating writer

**Status:** [x] Done — 2026-09-10 · **Type:** feature · **Complexity:** S · **Depends On:** TASK-747

**Outcome (2026-09-10).**
- **Service.** `services/calibration_service.py` gains
  `apply_calibration_to_ratings()`. `end_session()` calls it **once**, only
  after `write_calibration_state()` has landed and only for definition-mode
  runs. A failure is logged at WARNING and returns None, and the result is
  kept.
- **Output.** The RPC's decisions, refusals included, are returned verbatim as
  `ability.rating_decisions`. No gate is re-implemented in Python.
- **Result view.** `templates/calibration.html` renders each decision
  ("Reading: unchanged — no vocabulary estimate yet"), so a skip is visible.
  15 new i18n keys, verified present in all four locales.
- **Tests.** `tests/test_calibration_completion_wiring.py`, 6 passed. It pins:
  once-after-state, definition-only, non-fatal failure, no call when the state
  write fails, unfiltered pass-through, and a malformed payload.

**Description:**
Call `apply_calibration_to_skill_ratings` when a Calibration run finishes and
`user_calibration_state` has been written. Thin wiring task; all policy lives in
the RPC so this cannot bypass a gate.

**Acceptance Criteria:**
- [ ] Fires once per completed calibration run, after the state write commits.
- [ ] Failure is logged and non-fatal — a calibration result is never lost because the rating write was refused.
- [ ] Does **not** re-implement any gate; a refusal is a normal outcome, not an error.
- [ ] Surfaces the audit rows on the calibration result view so a skip is visible rather than silent.

**Files:** Calibration completion handler (path depends on the parallel build);
`tests/integration/test_calibration_completion_wiring.py`

---

## TASK-779: repair token-map drift

**Status:** [x] Done — applied live 2026-09-15 (47 ja maps rewritten) · **Type:** bug · **Complexity:** S · **Depends On:** none

**Description:**
Precondition for a per-occurrence coverage term (planned TASK-780), which would
read `tests.vocab_token_map` instead of `vocab_sense_ids`. On 2026-09-15 the two
disagreed for most en/ja tests (overlap en 0.88, ja 0.83, zh 1.00).

**Outcome (2026-09-15).** Classified the disagreement first:
- **ja: real drift.** 198 map entries in 47 tests pointed at deleted senses
  (シャツ, デザイン, メンバー…). `task778_ja_loanword_lemma_cleanup.sql` deleted
  "unreferenced" senses, but its reference union covered `vocab_sense_ids`,
  questions, mysteries and calibration, **not `vocab_token_map`** (jsonb). The
  reader rendered those words clickable, with no definition behind them.
- **en: by design, not drift.** 330 linked senses are multi-word lemmas that a
  per-token map cannot carry, and ~325 map tokens are fallback links to words the
  linker did not extract. A rebuild changes neither. TASK-780 must decide how
  phrase senses count under a token basis.
- **zh: clean** (2 fallback links).

`scripts/rebuild_token_maps.py` rebuilds maps using the sense-linking workflow's
shared builder (`build_token_map_with_fallback`), seeded from the test's own
`vocab_sense_ids`. It writes `vocab_token_map` only. It refuses to write a rebuild
that loses a currently working link, still contains a deleted sense, or
reproduces the text less faithfully than the current map. Applied to ja: 47 of 47
written, 0 refused. Live after: ja dangling 198 → 0, overlap 0.83 → 0.95. zh/en
had no targets. **No backup was taken** (a failed backup step did not stop the
chained apply). Every write passed the no-lost-link guard, so what was
overwritten was the dangling pointers plus unchanged links.

**Follow-up 2026-09-16 (steps 1-4 of the gap analysis).**
The remaining ja gap (overlap 0.95) was 107 by-design fallback links plus **73
links whose headword is UniDic's abstract lexeme, not the word as written** —
越える for 超え, 押さえる for 抑え, 付く for 就く. Tests linked before the orthBase
fix (ede24bd4, 2026-08-26) carry them; the token map already had the written form.

- **APPLIED — tokenizer (step 3).** `_orth_lemma` now prefers UniDic's `lemma`
  when `cType` starts `文語`: orthBase gives the classical dictionary form (長し,
  幼し, 若し), which no modern entry matches. Potential verbs carry no such marker
  (拭える has an ordinary cType), so they keep orthBase. 4 new tests.
- **APPLIED — map rebuild.** `rebuild_token_maps.py --language ja --all`: 11
  written, 47 unchanged, 1 refused (潔し would have lost its only link — that test
  is waiting on the re-parent below).
- **APPLIED 2026-09-16 — relink + re-parent (steps 1-2).**
  `scripts/fix_ja_sense_link_variants.py`: **76 links across 33 tests and 3
  questions** repointed to the written form (押さえる→抑える, 越える→超える,
  付く→就く, 早い→速い, ドウジ→童子…), 1 duplicate id collapsed, and **潔し's 6
  senses re-parented onto 潔い** (sense ids unchanged, so every reference
  survives). The other 5 artifact headwords (若し, 長し, 幼し, 引く-他動詞, ドウジ)
  have twins that already carry senses, so they are deferred rather than merged —
  they are now unreferenced rows for the duplicate audit. A following
  `rebuild_token_maps.py --language ja --all` reported all 59 unchanged, which is
  the expected result: re-parenting keeps sense ids, so the maps were already right.
  **Live end state: ja/zh/en all 0 dangling; mean link-vs-map overlap ja 0.985
  (was 0.83), zh 1.000, en 0.880 (structural, see above).**
- **INCONCLUSIVE — duplicate audit (step 4).**
  `scripts/audit_ja_variant_duplicates.py` is read-only and runs, but reading +
  kanji + POS does not separate one word's two spellings from two words that
  merely sound alike: it offers 風邪/風 and こと/コート as merge candidates, while
  putting genuine variants (錆び付く/錆びつく, 生かす/活かす) under `different_pos`
  because `dim_vocabulary.part_of_speech` disagrees with itself. Treat its output
  as a review list for a judge, not a to-do list. Sizing the duplicate problem
  still needs a different method.

**Found, not fixed:**
- The ja processor drops newlines. 6 ja maps (before and after) do not
  concatenate to their transcript, so the reader loses paragraph breaks.
- The remaining ja gap (overlap 0.95) is mostly linked senses whose lemma never
  appears as a token, e.g. homograph-suffixed headwords like `引く-他動詞`.
- Any future sense deletion must check `vocab_token_map` as well.
  `rebuild_token_maps.py --language <l> --dry-run` detects the damage.

**Acceptance Criteria:**
- [x] No live test map references a deleted sense (all languages: 0).
- [x] Rebuild never unlinks a working token (guard + unit test).
- [x] Divergence that is structural (en phrases, fallback links) documented, not "repaired".

**Files:** `scripts/rebuild_token_maps.py`, `tests/test_rebuild_token_maps.py` (8 tests)

**Verification:**
`PYTHONPATH=. pytest tests/test_rebuild_token_maps.py`;
`python scripts/rebuild_token_maps.py --language ja --dry-run` reports 0 targeted.

---

## TASK-780: multiplicative ELO × coverage scoring (`combine_mode`)

**Status:** [x] Done — applied live 2026-09-16 (schema_migrations 20260916134648),
**`combine_mode` = 'sum' and `vocab_weight` = 0 — inert on both switches** ·
**Type:** feature · **Complexity:** M · **Depends On:** TASK-748

**Scope note — this is NOT the per-occurrence task TASK-779 anticipated.**
TASK-779 recorded TASK-780 as "a per-occurrence coverage term reading
`vocab_token_map` instead of `vocab_sense_ids`". That shape was considered and
**dropped**: a linked word appears only 1.15 (ja) / 1.33 (zh) / 1.44 (en) times
per test, so per-occurrence and distinct-word counting nearly coincide, and
distinct-word counting is the better match for "how much new vocabulary must this
learner absorb". Coverage still counts each **distinct** sense in
`vocab_sense_ids` once, and must stay that way. TASK-779's token-map repair
stands on its own merits; it is not a precondition for this.

**Outcome (2026-09-16).** `migrations/task780_selection_combine_mode.sql`. One
new `selection_tuning` key, `combine_mode`, `'sum'` (default) | `'product'`:

```
e = elo_weight·|Δelo|/400      v = vocab_weight·|unknown − u*|/u_tol
sum      score = e + v                  product  score = (1+e)·(1+v)
```

Product is the sum plus the cross term `e·v`, so a candidate wrong on **both**
axes is demoted below one equally wrong on a single axis. A bare `e·v` is not
implemented and must not be: a perfect ELO match with 90% unknown words would
score 0 and rank first.

- **Only `recommended_tests_ranked` changed** — same signature, same
  `RETURNS TABLE`, two additions (the tuning read, and a `CASE` in the `scored`
  CTE whose `ELSE` is the TASK-748 expression verbatim). `get_recommended_tests`
  and `selection_vocab_ability` are untouched (`prosrc` md5 unchanged live), so
  the `vocab_weight = 0` rollback branch is literally the same bytes and
  **`combine_mode` is inert while `vocab_weight` is 0**.
- **Schema.** `selection_tuning` gained a nullable `value_text` column; `value`
  became nullable and a `selection_tuning_value_shape` CHECK now enforces exactly
  one of the two per key (so numeric keys keep their NOT NULL guarantee), plus a
  CHECK restricting `combine_mode` to `sum`/`product`. A 0/1 numeric encoding was
  rejected as unreadable at the moment an operator flips it.
- **No new function parameter** — after `p_as_of` it would have to be defaulted,
  which is the ambiguous overload
  `migrations/get_recommended_tests_drop_ambiguous_overload.sql` already cleaned
  up once. Arms are selected with a transaction-local `UPDATE ... ; ROLLBACK`.
- **Live proof, rollback-only, after applying.** 14 users × en/zh/ja = 42 pairs,
  13,934 ranker rows at weight 1: at `combine_mode = 'sum'` the new function is
  row-identical (content and order) to a frozen copy of the pre-780 body at
  `vocab_weight` **0 and 1**, on all 42; the public RPC is unchanged at
  `vocab_weight = 0` under *either* mode on all 42; and the minimum per-type
  candidate-count delta in product mode is **0** (M5 holds). The frozen copy
  self-verifies against the `prosrc` md5 read before the migration
  (`7b44009489ed1628ba70b8b9e5ed03ad`), so a bad copy fails loudly.
- **Fixtures pass live** (`tests/sql/test_task780_combine_mode.sql`): five
  synthetic ja reading candidates with both terms set exactly. `bad_both`
  (e 0.50, v 0.55) and `bad_elo` (e 1.00, v 0.10) **swap** between modes — sum
  1.05 < 1.10, product 2.325 > 2.200 — `too_hard` (perfect ELO, 90% unknown)
  ranks last in both, the neutral candidate's penalty is the cohort median 0.325
  in both, and every pre-combination column is identical across modes.
- **Nothing was switched on.** `vocab_weight` 0, `combine_mode` 'sum'. Flipping
  either is the operator's call after the TASK-781 replay.

**Acceptance Criteria:**
- [x] `combine_mode = 'sum'` is output-identical to TASK-748, proven against a frozen copy of the old body, not argued from the diff.
- [x] `vocab_weight = 0` still reproduces the pre-TASK-748 ranking exactly (the RPC body is unchanged).
- [x] Product is `(1+e)(1+v)`, never a bare `e·v`; pinned by a test that would rank a 90%-unknown test first under the wrong form.
- [x] §3.4 degradation intact: neutral = cohort MEDIAN raw penalty, computed before the combination, identical in both modes; never 0, never `+∞`.
- [x] M5: no per-type pool size falls, in either mode.
- [x] No defaulted function parameter; exactly 1 `get_recommended_tests` in `pg_proc`.
- [x] Coverage still counts each distinct sense once.
- [x] Revert-red: removing the product branch makes the two arms equal and the fixtures fail by name.

**Files:** `migrations/task780_selection_combine_mode.sql`,
`tests/sql/test_task780_combine_mode.sql`,
`tests/sql/test_task748_parity.sql` (steps 3-4 appended),
`migrations/task748_get_recommended_tests_vocab_aware.sql` (header note:
superseded in part; kept because it is still the only record of the other two
functions).

**Verification:**
```
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_task748_parity.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_task780_combine_mode.sql
SELECT key, value, value_text FROM selection_tuning ORDER BY key;
```

---

## TASK-781: replay the three arms — weight 0 vs sum vs product

**Status:** [x] Done — 2026-09-17 (read-only apart from one restored
`combine_mode` write; **neither switch moved**) · **Type:** test ·
**Complexity:** M · **Depends On:** TASK-748, TASK-749, TASK-780

**Outcome (2026-09-17).** `scripts/measure_selection_quality.py` extended from
two arms to three; full write-up in
[[evaluations/selection-three-arm-replay-2026-09-17]].

**The decision this was built to make: `combine_mode` stays `'sum'`.** On the ja
replay (21 first attempts, 210 top-10 slots per arm) the share of served tests
inside the 5-25% unknown band is **w0 0.786 → sum 0.952 → product 0.938**.
Product is *worse*, and per attempt it is better on **0** of 21, worse on 3,
equal on 18. The two vocabulary arms agree on the top-10 set for 14 of 21
attempts (mean Jaccard 0.939), against 0.395 / 0.391 versus w0 — i.e. **the
vocabulary term is the whole effect; the combination rule is noise on top of it.**

- **Why.** `product = sum + e·v`, so the extra charge lands hardest on candidates
  whose vocabulary term is already large — the ones the term is trying to demote.
  It dilutes its own signal: rho(unknown, score) over all candidates falls from
  0.918 → 0.839 (zh) and 0.961 → 0.913 (ja).
- **The sharper cost is in zh.** 27 of 125 active zh tests carry no
  `vocab_sense_ids` (verified live 2026-09-17) and they sit near the learner's
  ELO. `sum` clears all of them out of every top-10 (0/10 neutral in all four
  types); **`product` lets 2-5 of ten back in** for dictation / listening /
  reading. A neutral candidate carries the cohort median penalty, and product's
  extra `e·v` is smallest where `e` is small — so "no opinion, and close in ELO"
  becomes a mild *reward*, which is exactly what §3.4's median was chosen to
  avoid.
- **M5 holds everywhere.** Minimum per-type pool delta vs w0 is **0** in both
  vocabulary arms, in the replay and in the current-state snapshot.
- **Spearman(unknown of the taken test, its score) = −0.584**, reproducing the
  −0.59 on record. It is **arm-independent** — `unknown_share` is a property of
  (user, test, as-of), not of the ranking — so it validates the vocabulary signal
  rather than comparing arms. Do not read it as an arm metric.
- **`vocab_weight` is the switch worth arguing about**, not `combine_mode`. It is
  still the operator's call and it is still n=1: verified live, 14 users exist
  and exactly **one has ever taken a test**.

**Harness changes.** Arms are `(vocab_weight, combine_mode)` pairs in `ARM_SPEC`;
`--arms` selects a subset. `combine_mode` is a settings row, not an RPC argument,
and the script talks PostgREST, so the product arm **writes** that row and
restores it in a `finally` — and **refuses to do so unless `vocab_weight = 0`**,
because at weight 0 `get_recommended_tests` never reaches the ranker, so the mode
cannot change what a live learner is served. The mode is flipped once per arm,
not once per call, and the script re-reads `selection_tuning` at the end and
prints it (run ended `vocab_weight=0, combine_mode='sum'`).

**A metric trap now surfaced.** `band_share` is computed over candidates that
*have* an unknown share, so an arm serving more unlinked tests scores its band
share over a smaller denominator — zh product's 0.80 is 4 of 5, not 8 of 10. The
served printout now shows the neutral count beside the band share. The ja replay
numbers are unaffected (0 neutral slots in every arm).

**Acceptance Criteria:**
- [x] Three arms replayed — weight 0, sum, product — through the existing harness.
- [x] Share of top-10 inside the 5-25% unknown band reported per arm.
- [x] Spearman of unknown share against score reported, and its arm-independence stated rather than implied.
- [x] Top-10 overlap between arms reported (all three pairings).
- [x] M5 reported per arm; no per-type pool fell.
- [x] Read-only with respect to learner data; the single settings write is guarded, restored, and verified afterwards.
- [x] Neither `vocab_weight` nor `combine_mode` changed.

**Files:** `scripts/measure_selection_quality.py`,
`wiki/evaluations/selection-three-arm-replay-2026-09-17.md`

**Verification:**
```
PYTHONIOENCODING=utf-8 PYTHONPATH=. python -m scripts.measure_selection_quality \
    --until 2026-09-08T23:59:59+00:00 --replay-language 3 --json out.json
SELECT key, value, value_text FROM selection_tuning ORDER BY key;
PYTHONPATH=. pytest tests/test_selection_metrics.py
```

---

## Open Questions

0. **HALF-ANSWERED 2026-09-17 (TASK-781) — does either switch ever move?**
   **`combine_mode`: no, on this evidence.** The replay puts product at 0.938
   in-band against sum's 0.952, better on 0 of 21 attempts, and it re-admits
   unlinked zh tests that sum had cleared out. It stays `'sum'`, live and inert.
   **`vocab_weight`: ANSWERED 2026-09-17 — raised to 1, the term is live.** The
   operator took the n=1 evidence (0.786 → 0.952 in-band, M5 intact) rather than
   run a 7-day shadow window, on the grounds that rollback is one `UPDATE`. What
   is still unmeasured is whether the better-matched serving shows up in
   *scores*: the replay predicts it, live attempts have not tested it yet. See
   [[evaluations/selection-three-arm-replay-2026-09-17]].

1. **OPEN — `u*` target.** Shipping 0.15. The dropped RPC's 3-7% is unreachable:
   best available is 27% unknown at difficulty 1 for this learner. Revisit as
   dictionary and BKT coverage improve.
2. **OPEN — offsets fitted or prior?** See TASK-750. Blocked on data.
3. **ANSWERED 2026-09-09 — what is `ability_zipf`?** The 85% known-share
   crossing, with the guess floor removed (Calibration TASK-764/766). See TASK-745.
4. **ANSWERED 2026-09-09 — `user_calibration_state` shape.** As §1.1 assumed,
   plus `sessions_pooled` and a `mode` column (PK `(user_id, language_id, mode)`).
   Selection and the rating writer read **only** `mode = 'definition'`;
   pronunciation measures reading, not vocabulary, and the two modes are never
   averaged.
5. **ANSWERED 2026-09-08 — difficulty as a hard filter?** No. ADR-024.
6. **ANSWERED 2026-09-08 — seed-only or correction?** Both: seed under 5
   attempts, damped+capped correction above. Seed-only alone would never fire
   for the affected learner.
