---
title: Vocabulary-Aware Test Selection — Technical Specification
type: feature-tech
status: planned
prose_page: vocabulary-aware-test-selection.md
last_updated: 2026-09-08
dependencies:
  - "table: user_vocabulary_knowledge (p_known, status, language_id)"
  - "table: user_calibration_state (ability_zipf, ability_se, band_accuracies, items_answered, sessions_pooled, mode, last_run_at), PK (user_id, language_id, mode) — BUILT 2026-09-09 by Calibration Phase 4, APPLIED LIVE (TASK-765, verified 2026-09-10). Selection reads mode='definition' ONLY."
  - "table: dim_complexity_tiers (initial_elo anchors)"
  - "table: dim_vocabulary.frequency_rank (a ZIPF SCORE, not a rank)"
  - "table: dim_word_senses (vocab_id -> dim_vocabulary.id)"
  - "table: tests.vocab_sense_ids, test_skill_ratings, user_skill_ratings"
  - "RPC: get_recommended_tests (LIVE SIGNATURE IS 3-ARG — see §1)"
  - "module: services/test_generation/difficulty_scorer.py (_REF_ZIPF anchors)"
  - "CONTRACT SATISFIED 2026-09-09: Calibration ships ability_zipf as the 85% KNOWN-share crossing, with the 1-in-4 guess floor removed by the estimator so it is knowledge and not accuracy. Verified 5.00 -> 1250 and 3.85 -> 1681, a 431-point swing. See features/calibration.tech Phase 4."
breaking_change_risk: medium
---

# Vocabulary-Aware Test Selection — Technical Specification

## 0. Verified Ground Truth (live, 2026-09-08)

Everything in this section was read from the live database or repo on
2026-09-08. Do not re-derive it; **do** re-verify anything marked DRIFT before
writing a migration.

### 0.1 Two corrections to the briefing

**DRIFT — `get_recommended_tests` is not the archived 2-arg function.** The
briefing names `migrations/archive/task715_get_recommended_tests_tier_cap.sql`
as canonical. The live signature is:

```
get_recommended_tests(p_user_id uuid, p_language_id smallint,
                      p_topic_recency_days smallint DEFAULT 14)
```

The live body is the task715 body **plus** a topic-recency `NOT EXISTS` clause
added by TASK-740 phase5b. Every ranking claim in the briefing still holds
exactly — ELO-only ranking, no `difficulty` filter, no `vocab_sense_ids` read,
no `user_vocabulary_knowledge` — but **any migration must be built on the live
3-arg body**, captured via `pg_get_functiondef`, not on the archive file. This
is the same class of drift recorded in [[process-test-submission-cr04-drift]].

**STALE — the learner is not a cold start.** The briefing says "user has ~no ja
attempts, so `elo_rating` sits at the 1200 default". That was true when TASK-732
was written; it is not true now. Live: 27 Japanese attempts, 21 first attempts,
and ELO has moved off 1200 in all four skills. This does not weaken the
diagnosis — it sharpens it, because we can now measure how badly ELO is failing
rather than argue it a priori (§0.3). It does mean **the seed-only guard alone
would no longer fire for this learner**, which is precisely why §2 specifies a
correction path as well.

### 0.2 Confirmed as briefed

- Ranking is `ABS(test_elo - user_elo)`, `rank_in_type <= 10` per type. ✅
- `tests.difficulty` never filtered; `tests.vocab_sense_ids` never read;
  `user_vocabulary_knowledge` absent from selection entirely. ✅
- `get_vocab_recommendations` dropped at `migrations/drop_unused_rpcs.sql:24`. ✅
- `vocab_sense_ids` coverage: ja 59/59, en 100/121, zh 98/125. ✅
- `dim_vocabulary.frequency_rank` is a **Zipf score, higher = more common**
  (`services/vocabulary_ladder/deterministic/lexicon.py:266`). ✅
- `user_calibration_state` did **not** exist on 2026-09-08. *Update 2026-09-10:*
  it is live (Calibration TASK-766, applied as TASK-765) with a `mode` column; see
  §1.1. It has 0 rows, so every consumer's no-calibration path is the one that
  actually runs today.
- Live `process_test_submission`: user K=32 first-attempt only, furigana
  dampener 0.5, test K=48/24/16, ADR-006 retry damping present, **no CR-04**.
  Clamp `[400, 3000]`.

### 0.3 The measurements that drive the design

**(a) Test ELO is test-type-blind.** 48 of 60 Japanese tests have an *identical*
ELO across all 8 test types. TASK-732 reseeded from prose complexity, which is
type-agnostic by construction.

**(b) The rating system compresses true ability by 5×.** Inverting the Elo
expectation per first attempt (`user = test_elo - 400·log₁₀(1/s - 1)`, `s`
clamped to [0.05, 0.95]):

| type_code | n | avg test ELO | mean % | implied ability | sd | live ELO | error |
|---|---|---|---|---|---|---|---|
| dictation | 1 | 1209 | 87.0 | 1539 | — | 1209 | −330 |
| reading | 8 | 1281 | 73.1 | 1498 | 175 | 1270 | −228 |
| listening | 7 | 1241 | 67.1 | 1396 | 218 | 1248 | −148 |
| pitch_accent | 5 | 1213 | 35.4 | 1091 | 101 | 1182 | **+91** |

True spread **448 points (1091-1539)**; assigned spread **88 points
(1182-1270)**. Note the signs differ: Japanese is mostly too *easy*; pitch
accent alone is too hard, and it dominates the felt experience (6 of 7 attempts
below 50%).

**(c) The MC floor caps ELO's reach.** Equilibrium gap is
`400·log₁₀(1/s − 1)`. At a 25% chance floor that is **−191 ELO**: a learner who
knows nothing still settles ~190 points below the pool, never further. Combined
with Japanese difficulty-1 tests being rated ~1240 (not the T1 midpoint of 875 —
prose adjustment pushed them up), the learner is pinned in roughly 1050-1240
regardless of how many tests they take. **ELO cannot express this gap. That is
the whole argument for the feature.**

Model verified against live rows: user 1188 vs test 1305 at 14.29% predicts
−6 → observed 1188→1182. Exact.

**(d) Vocabulary carries the signal ELO lacks.** Share of a test's senses with
`p_known >= 0.6`, this learner, Japanese:

| difficulty | tests | senses/test | known share | **has any uvk row** |
|---|---|---|---|---|
| 1 | 11 | 12.6 | 72.7% | 89.1% |
| 6 | 24 | 44.0 | 16.6% | 22.9% |
| 9 | 24 | 74.4 | 8.8% | **10.3%** |

**(e) The sparsity trap.** That last column is the design constraint. At
difficulty 9, 90% of senses have *no row at all* — untested, not proven unknown.
A naive `INTERSECT`/`array_length` ratio conflates the two, scores all fresh
content ≈0, and **degrades as the catalogue grows**. §3.2 exists to fix this.

**(f) The Zipf prior is viable.** Senses this learner knows average Zipf 4.79;
those they don't, 3.80 — a full point of separation. Zipf coverage on Japanese
test senses is 97-99% (35 nulls of 1132 at difficulty 9).

---

## 1. Architecture Overview

```
Calibration mode ──► user_calibration_state (ability_zipf, ability_se, ...)
                            │
                            ▼
              calibration_zipf_to_elo(ability_zipf)      [§1.2, SQL, canonical]
                            │
                            ▼
        apply_calibration_to_skill_ratings(...)          [§2, guarded writer]
                    │                    │
                    │                    └──► user_skill_rating_adjustments (audit)
                    ▼
             user_skill_ratings.elo_rating
                            │
   process_test_submission ─┤  (UNMODIFIED — the other writer)
                            ▼
              get_recommended_tests  ──► combined score  [§3]
                            ▲
   user_vocabulary_knowledge│         + Zipf prior from ability_zipf
   tests.vocab_sense_ids ───┘
```

Two writers touch `user_skill_ratings.elo_rating`. They are separated by
**temporal guards, not by code changes to `process_test_submission`** — that
function has already drifted from the repo once and there is no clean copy to
edit against.

### 1.1 Input contract: `user_calibration_state`

Built in parallel by Calibration (TASK-766, live since TASK-765); this feature
consumes it. Shape as shipped:

| column | type | used for |
|---|---|---|
| `user_id` | uuid | key |
| `language_id` | smallint | key |
| `mode` | text, `'definition'` \| `'pronunciation'` | key — **selection reads `mode = 'definition'` only** |
| `sessions_pooled` | integer | diagnostics (ability is pooled across all sessions) |
| `ability_zipf` | numeric | → ELO anchor (§1.2) and the untested-sense prior (§3.2) |
| `ability_se` | numeric | gate: skip the write if too uncertain (§2.2) |
| `band_accuracies` | jsonb | per-type offset evidence (§1.3), diagnostics |
| `items_answered` | integer | gate: skip below 20 |
| `last_run_at` | timestamptz | staleness gate |

The primary key is `(user_id, language_id, mode)`. **The `mode = 'definition'`
rule is binding for every consumer here** — the §2 rating writer, the §3.2 prior
and the §4 tier ceiling. Definition mode measures vocabulary knowledge;
pronunciation mode measures *reading*, a different construct. The two rows are
never averaged, and a pronunciation row must never stand in for a missing
definition row.

**If the shipped table differs, §1.2 and §2 change and nothing else does.**
Everything downstream reads `user_skill_ratings` and `user_vocabulary_knowledge`
as it does today.

### 1.2 `ability_zipf` → ELO (KEY DECISION)

> **PREREQUISITE — pin what `ability_zipf` means before implementing this.**
> The ladder below is the **age-tier** ladder ([[decisions/ADR-003-age-tiers]]):
> T1 "Toddler (4-5)" … T6 "Educated Professional (30+)". Its `_REF_ZIPF` values
> are the **mean Zipf of native-speaker prose** at each age. `ability_zipf` is a
> **threshold on an L2 learner's knowledge curve**. These are different
> statistics and the map is acutely sensitive to which threshold is used.
>
> Measured on this learner's live ja knowledge curve:
>
> | Zipf band | n | known share |
> |---|---|---|
> | 3.01-3.43 | 9 | 0% |
> | 3.51-3.99 | 22 | 36% |
> | 4.04-4.49 | 31 | 65% |
> | 4.51-4.99 | 43 | 72% |
> | 5.00-5.48 | 45 | 96% |
>
> 85%-known threshold ≈ **Zipf 5.0** → maps to **1250**. 50% crossover ≈ **Zipf
> 3.85** → maps to **1681** (T5, "Uni Student") — against a learner who knows
> 17% of the words in T4 content. **A 430-point swing from the definition
> alone**, and the wrong end of it is silently catastrophic.
>
> **Contract: `ability_zipf` MUST be the Zipf level at which the learner's
> known-share crosses `1 − u*` (the retention target, 85% at `u* = 0.15`) —
> not a 50% crossover, not a mean of known senses.** If Calibration ships a
> different construct, this map must be re-derived, not reused.
>
> Corollary for comparison: a passage's *median* Zipf is the right statistic to
> compare a threshold against, not its mean. Live ja d1 tests run mean 4.55 /
> median 4.77 — and the learner is 72% known at 4.51-4.99, matching their
> observed 73.5% at d1. The medians confirm the curve.
>
> **This sensitivity is confined to the seed (§1-2). The coverage term (§3)
> does not depend on the ladder at all** — it compares per-sense `P_known`
> directly and needs no tier mapping. If the contract cannot be settled, ship
> §3 first; it carries most of the value.

Reuse the existing tier ladder rather than inventing a curve. Two arrays already
in the system form a ready-made correspondence:

- `dim_complexity_tiers.initial_elo` (live): 875 / 1175 / 1400 / 1550 / 1700 / 1925
- `difficulty_scorer._REF_ZIPF` (T1-T6): 6.25 / 5.25 / 4.50 / 4.20 / 3.80 / 3.25

Anchor points, monotone decreasing in Zipf (rarer vocabulary → higher ELO):

```
(6.25, 875) (5.25, 1175) (4.50, 1400) (4.20, 1550) (3.80, 1700) (3.25, 1925)
```

Piecewise-linear interpolation between anchors; **clamp to [875, 1925]** — do
not extrapolate past the ladder, because outside it there is no calibration.

> **Single source of truth.** [[two-difficulty-to-tier-maps]] records that three
> copies of the difficulty→tier bands must already be kept in step. Do not add a
> fourth. The anchor table lives in **SQL only**, as
> `public.calibration_zipf_to_elo(numeric) RETURNS integer`, seeded from
> `dim_complexity_tiers` at call time so the ELO half can never drift from the
> tiers. Python reads it through the RPC; the only Python copy is in a test
> fixture that asserts agreement with the SQL.

### 1.3 Per-test-type offsets

The calibration measures *vocabulary*, which is type-neutral. The 448-point
spread in §0.3(b) is a *skill* difference and needs its own term:

```
seed_elo(type) = calibration_zipf_to_elo(ability_zipf) + type_offset(type)
```

Ship v1 with `type_offset = 0` for all four types, with `reading` as the
reference skill. Rationale: the live evidence for non-zero offsets is real but
rests on 21 first attempts from one learner (§0.3(b)), which is enough to
*detect* the compression and nowhere near enough to *fit* the correction. A
fitted offset table is TASK-750, gated on ≥30 first attempts per (language,
type). The measured Japanese residuals are recorded there as the first evidence
row, not as shipped constants.

---

## 2. Guarding the feedback loop

### 2.1 Why a guard is needed

`process_test_submission` writes `user_skill_ratings.elo_rating` on every first
attempt at K=32. An unguarded calibration writer would fight it, and the loser
would be whichever ran last — invisibly.

### 2.2 Write policy

`apply_calibration_to_skill_ratings(p_user_id, p_language_id)` — one call per
calibration run, iterating the four types. For each `(user, language, type)`:

**Hard gates — any failure means skip and audit the reason:**

| gate | rule |
|---|---|
| `G1_no_state` | `user_calibration_state` row missing |
| `G2_low_items` | `items_answered < 20` |
| `G3_high_se` | `ability_se > 0.75` (Zipf units) |
| `G4_stale` | `last_run_at < now() - 90 days` |
| `G5_in_session` | any `test_attempts` row for this (user, language) in the last **1 hour** |
| `G6_rate_limit` | a non-skipped adjustment for this (user, language, type) within **7 days** |

**Then one of two modes:**

- **SEED** — `tests_taken < 5`. Write `seed_elo` directly. Cold start; there is
  no earned rating to damage.

- **CORRECT** — `tests_taken >= 5` **and** `|seed_elo − live_elo| > 200`
  (deadband). Write
  `live_elo + sign(diff) · LEAST(0.25 · |diff|, 150)`.
  Damped to a quarter of the disagreement and capped at 150 points, so
  calibration nudges and the learner's own history dominates.

- Otherwise **NO-OP**, audited as `within_deadband`.

**Final clamp: `[875, 1925]`** — tighter than `process_test_submission`'s
`[400, 3000]`, because a calibration-derived value has no business outside the
ladder that produced it.

Worked example — this learner's pitch accent (live ELO 1182, `tests_taken` 5):
if calibration returns `ability_zipf` implying 1050, `diff = −132`, inside the
200 deadband → NO-OP. If it implies 900, `diff = −282` → move
`min(0.25·282, 150) = 70.5` → **1112**. Never a jump to 900.

### 2.3 Audit trail

New table `user_skill_rating_adjustments` — append-only, **every** decision
including skips:

| column | type | notes |
|---|---|---|
| `id` | bigserial | |
| `user_id`, `language_id`, `test_type_id` | | key |
| `source` | text | `'calibration_seed'` \| `'calibration_correct'` \| `'skipped'` |
| `elo_before`, `elo_after` | integer | equal when skipped |
| `ability_zipf`, `ability_se` | numeric | inputs, for reproducing the decision |
| `seed_elo_computed` | integer | before damping/clamping |
| `tests_taken_at_write` | integer | which mode applied and why |
| `reason` | text | gate code (`G3_high_se`) or `within_deadband` |
| `created_at` | timestamptz | rate-limit source of truth |

Index `(user_id, language_id, test_type_id, created_at DESC)` — serves G6 and
the before/after check in §5.

### 2.4 What is explicitly not touched

`process_test_submission` is **not modified**. Not to add a calibration read,
not to change K, not to add a guard. Live has drifted from repo
([[process-test-submission-cr04-drift]]); the canonical body is the partG
migration and the live definition must be re-read via `pg_get_functiondef`
before anyone touches it. This feature does not need to.

---

## 3. Vocabulary coverage in `get_recommended_tests`

### 3.1 Estimated known-share

For candidate test `t` with senses `S = t.vocab_sense_ids`:

```
known_share(t) = ( Σ_{s ∈ S'} P_known(s) ) / |S'|
unknown(t)     = 1 − known_share(t)
```

where `S'` is `S` restricted to senses resolving to a `dim_vocabulary` row with
a non-null `frequency_rank` (drops the 1-3% with no Zipf, rather than counting
them as unknown).

### 3.2 `P_known(s)` — the dense estimate

```
P_known(s) = uvk.p_known                                            if a uvk row exists
           = σ( k · (zipf(s) − ability_zipf) + ln(0.85 / 0.15) )     otherwise
```

with logistic `σ`, slope `k = 1.5`, and `zipf(s) = dim_vocabulary.frequency_rank`
via `dim_word_senses.vocab_id`.

> **CORRECTION (a), 2026-09-10 — the prior is 0.85 at `ability_zipf`, not 0.5.**
> The original `σ(k·(zipf − ability_zipf))` equals 0.5 at the threshold, i.e. it
> treats `ability_zipf` as a 50% crossover — the construct §1.2 forbids.
> `ability_zipf` is by contract the **85%-known** crossing, so a sense exactly
> there must be 85% likely known; the `ln(0.85/0.15) = 1.7346` offset makes it
> so. Check: slope 1.5 then puts the 50% point `1.7346 / 1.5 = 1.16` Zipf
> **below** the threshold, which matches the live ja curve (85% at ~5.0, 50% at
> ~3.85). Shipped in `migrations/task748_get_recommended_tests_vocab_aware.sql`,
> and pinned by `tests/sql/test_task748_vocab_ranking.sql` (a test whose senses
> sit at `ability_zipf` scores unknown = 0.1496).

**This is the load-bearing part.** Without the prior, §0.3(e) applies: 90% of
difficulty-9 senses have no row, every unseen test scores ≈0 known, the term
ranks all fresh content identically at the bottom, and it gets worse as the
catalogue grows. With it, the estimate is dense from day one and improves as BKT
fills in.

`ability_zipf` is the calibration value (`user_calibration_state`,
`mode = 'definition'` only). With no calibration row, fall back as below; if the
fallback is also unavailable, **skip the vocabulary term entirely** (§3.4
neutral).

> **CORRECTION (b), 2026-09-10 — the fallback is an 85% crossing, not a median.**
> The original fallback, "the learner's own median `zipf` over senses with
> `p_known >= 0.6`", is a location of *known* words — the "mean of known senses"
> construct §1.2 rules out by name. The shipped fallback
> (`selection_vocab_ability()`) estimates the Zipf at which the learner's own
> `user_vocabulary_knowledge` known-share (`p_known >= 0.6`) crosses **85%**:
> 0.5-wide Zipf bands with n ≥ 5, walked from the commonest band down, linearly
> interpolated between band midpoints at the first step from ≥ 85% to < 85%.
> That needs a band on each side; if no such pair exists the crossing is **not
> identifiable** and the term is neutral. Live 2026-09-10 for the one learner with
> data: **ja 5.02** (§1.2 measured "~5.0"), **zh 5.15**; en and every other user
> are `none`. `user_calibration_state` has 0 rows, so **this fallback is the path
> that actually runs today.**

> **Do not read `frequency_rank` as a rank.** It is a Zipf score, higher = more
> common ([[lexicon.py:266]]). The sign convention above is deliberate: a sense
> *more common* than the learner's ability is likely known.

### 3.3 Combined ranking

Replace the sole `ORDER BY ABS(test_elo - user_elo)` with:

```
score(t) = w_elo · |test_elo − user_elo| / 400
         + w_vocab · |unknown(t) − u*| / u_tol
ORDER BY score ASC          -- rank_in_type <= 10 unchanged, now on score
```

Initial constants: `w_elo = 1.0`, `w_vocab = 1.0`, `u* = 0.15`, `u_tol = 0.10`.

**Why `u* = 0.15` and not the 3-7% the dropped RPC aimed at.** Live Japanese
content cannot reach 3-7% unknown for this learner — the *best available* is 27%
unknown at difficulty 1 (§0.3(d)). A 3-7% target would make the vocabulary term
a constant across every candidate and buy nothing. 0.15 is reachable, keeps the
term discriminating, and is a tunable row (§3.5), not a constant to redeploy.
3-7% is recorded as the steady-state goal once the dictionary and BKT coverage
are denser.

A smooth distance-to-target penalty is used rather than a hard band so the
ranker always returns *something* — a band can be empty, a distance cannot.

### 3.4 Graceful degradation (REQUIRED)

A test gets a **neutral** vocabulary term when any of:

- `vocab_sense_ids` is NULL or empty (17% of en, 22% of zh);
- fewer than 5 senses resolve, or `|S'| / |S| < 0.5`;
- no `ability_zipf` and no fallback median (§3.2).

Neutral = **the median penalty across the candidate set for that
(user, type)** — computed in the same CTE — not 0 and not `+∞`:

- 0 would make unlinked tests always win.
- `+∞` would hard-filter them, silently emptying the pool for a fifth of the
  catalogue — the failure the briefing explicitly forbids.

Median means "no opinion", which is the honest encoding and leaves ELO to decide
among them.

### 3.5 Rollback switch — and why not a parameter

Add `w_vocab` as a row in a new one-row-per-key `selection_tuning` table
(`key text primary key, value numeric`), read inside the function. Setting it to
0 reproduces today's ranking **exactly** — verified by the parity test in §6.

**Do not add a defaulted `p_vocab_weight` parameter.** The repo already carries
`migrations/get_recommended_tests_drop_ambiguous_overload.sql`, cleaning up
precisely this: a defaulted parameter creates an ambiguous overload that PostgREST
resolves unpredictably. A settings row also allows instant rollback without
re-applying a migration, and lets §5's shadow mode run both arms.

Keys: `vocab_weight`, `elo_weight`, `unknown_target`, `unknown_tolerance`,
`tier_ceiling_offset`.

### 3.6 Performance

`unnest` over `vocab_sense_ids` (avg 50 senses/test ja, ~102 en/zh) joined to
`user_vocabulary_knowledge` and `dim_vocabulary`, across ≤125 tests per language
— trivially small. Materialise the learner's `uvk` rows in a CTE once rather
than per candidate. Required indexes:

- `user_vocabulary_knowledge (user_id, language_id, sense_id)` — verify it exists.
- `dim_word_senses (id) INCLUDE (vocab_id)` — likely covered by the PK.

If `tests` grows past ~10k per language, precompute `known_share` into a
materialised view keyed by (user, test). Not needed at current volumes; noted so
the decision is deliberate rather than discovered.

---

## 4. Should difficulty/tier become a filter?

**Decision: no. It stays ELO-mediated.** Full reasoning in
[[decisions/ADR-024-vocabulary-aware-test-selection]]; summary:

1. **It recreates the cold-start trap one level up.** A difficulty filter needs
   the learner's difficulty level — the very thing we cannot observe. Vocabulary
   coverage is *measured*; difficulty is an authoring label.
2. **The label does not separate the content.** Live Japanese ELO ranges overlap
   heavily by difficulty: d1 spans 1112-1430, d6 spans 1330-1545. Filtering on
   the label would discard measured signal in favour of a guess.
3. **Vocabulary already does the job better** — 73%/17%/9% across d1/d6/d9 is a
   far cleaner gradient than the ELO ranges.

**One exception, as a safety rail only:** when a calibration row exists, exclude
candidates more than `tier_ceiling_offset` (default 2) tiers above the learner's
calibrated tier. This is what stops an 840-character difficulty-9 dictation
landing on day one — the scenario TASK-732's header called out. It is an
eligibility guard, not a ranking mechanism, and with no calibration it excludes
nothing.

> **AS SHIPPED (TASK-748, 2026-09-10) — the ceiling DEMOTES rather than
> excludes.** Exclusion contradicts §5.1 M5 (per-type count must never fall) and
> ADR-024's "vocabulary may never remove the last candidate from a pool":
> whenever fewer than 10 within-ceiling candidates exist, excluding shrinks the
> pool. So an over-ceiling test ranks after **every** within-ceiling test — the
> day-one d9 dictation still cannot be served while any within-ceiling dictation
> exists, and the count cannot fall. It applies only with a `mode = 'definition'`
> calibration row **and** `vocab_weight > 0`; the learner's tier is the highest
> whose `initial_elo` their calibrated ELO reaches.

---

## 5. Proving it worked

The failure is subjective; the check must not be. Everything below is computable
from columns that **already exist** — `test_attempts` records `percentage`,
`user_elo_before`, `test_elo_before` per attempt. No new instrumentation.

### 5.1 Metrics

| # | Metric | Definition | Japanese baseline (2026-09-08) | Target |
|---|---|---|---|---|
| M1 | **On-target rate** (primary) | share of first attempts with `percentage ∈ [60, 85]` | reading 3/8; **pitch accent 0/5** | ≥ 50% per type |
| M2 | **Below-floor rate** | share of first attempts `< 50%` | **pitch accent 6/7**; overall 7/27 | < 20% |
| M3 | **Ability compression** | `max(implied) − min(implied)` vs `max(live ELO) − min(live ELO)` across types | **448 vs 88** | ratio < 2× |
| M4 | **Served unknown-word rate** | median `unknown(t)` over returned candidates | d1 27% / d6 83% / d9 91% | median → `u*` ± `u_tol` |
| M5 | **Pool health** (regression guard) | candidates returned per (type, call) | must not fall | ≥ today's count, every type |

M5 is the guard on §3.4: if the degradation path is wrong, this is what catches
it before a learner does.

> **OPERATIVE DEFINITIONS (TASK-749, 2026-09-10).** The baseline column above
> reproduces exactly only under these, which differ from the Definition column:
> **M1 is half-open, `60 < pct ≤ 85`** (two ja reading first attempts are stored
> at exactly 60; `[60, 85]` gives 5/8, not 3/8); **M2 counts all attempts**, not
> first attempts (pitch accent 6/7 includes 2 retakes; first-only is 4/5); **M3
> rounds** the per-type implied ability before taking the spread (448, not
> 447.x). `scripts/measure_selection_quality.py` uses these and prints the
> inclusive M1 and first-attempt M2 beside them.

### 5.2 Before/after with n=1

An A/B is unavailable — one live learner. Three checks instead, in order:

1. **Offline replay (the before/after).** For each of the 21 Japanese first
   attempts, reconstruct the candidate set as of that timestamp (`tests` minus
   attempts before it) and re-rank under both arms. Report the distribution of
   `unknown(t)` and `implied difficulty` for the old vs new top-10. This is a
   pure query over history — no writes, repeatable, and it is the honest
   before/after given the sample size.

2. **Shadow mode.** Deploy with `vocab_weight = 0` (behaviour identical) and log
   both rankings on every real call for 7 days. Compare rank correlation and M4.
   Flip the weight only if the shadow deltas match the replay's prediction.

3. **Synthetic fixtures.** Construct learners with known `ability_zipf` and known
   `uvk` rows; assert the ranker returns candidates with `unknown(t)` near `u*`,
   that an unlinked test ranks mid-pack rather than first or last, and that
   `vocab_weight = 0` reproduces today's order exactly.

### 5.3 The confound to state plainly

Fixing selection cannot fix pitch accent alone, because §0.3(a) — test ELO being
type-blind — is a *content seeding* defect, not a *selection* defect. Selecting
better among 60 tests that are all mis-rated for pitch accent has a low ceiling.
Expect M1/M2 to improve most for reading, listening and dictation (where the
learner is under-rated and better selection has room to work), and to improve
for pitch accent only once TASK-751 reseeds per-type ELOs. **If M1 for pitch
accent does not move, that is the expected result, not a failed rollout** — and
M3 is the metric that will show it.

---

## 6. Testing strategy

Run with `PYTHONPATH=. pytest tests/ ...` — an explicit `tests/` path is
required, and "no tests collected" is a hidden import error, not a missing
suite ([[webapp-pytest-needs-pythonpath]]).

**Unit**
- `calibration_zipf_to_elo`: monotone decreasing; exact hits on all six anchors;
  interpolation midpoints; clamping beyond 6.25 and 3.25; SQL and the Python
  fixture agree (§1.2).
- Write policy: one test per gate G1-G6; SEED vs CORRECT boundary at
  `tests_taken = 5`; deadband at exactly 200; damping cap at 150; clamp at 875
  and 1925.
- `P_known`: uvk row wins over prior; prior monotone in Zipf; null
  `frequency_rank` excluded from the denominator, not counted unknown.

**Integration (against a seeded DB)**
- **Parity:** `vocab_weight = 0` returns byte-identical rows to the live 3-arg
  function, same order. This is the rollback guarantee.
- **Degradation:** a test with NULL `vocab_sense_ids` ranks mid-pack; a pool of
  *entirely* unlinked tests returns the same count as today (the pool-emptying
  regression).
- **Audit:** every skip writes a row with the right gate code; a second call
  inside 7 days is refused by G6.
- **Revert-red:** deleting the vocabulary CTE makes the ranking tests fail —
  proving they test the feature and not the fixture.

**Not covered by tests** — the offline replay (§5.2.1) is an analysis script
under `scripts/`, not a test; it depends on live history and must not gate CI.

---

## 7. Security

- `apply_calibration_to_skill_ratings` is `SECURITY DEFINER` and **must**
  re-check `p_user_id = auth.uid()`, matching `process_test_submission`'s first
  statement. It writes ratings; without that check any user could seed another's.
- `get_recommended_tests` keeps its existing `SECURITY DEFINER` +
  `SET search_path TO 'public'`. The new CTEs read only the calling user's `uvk`
  rows — carry `p_user_id` into every one; do not widen the read.
- `selection_tuning` is operator-writable only. No RLS grant to `authenticated`;
  a learner must not be able to tune their own recommender.
- `user_skill_rating_adjustments`: RLS select-own, no client insert.

---

## 8. Migration & rollout

All migrations idempotent `CREATE OR REPLACE`, header stating problem / fix /
safety, plus an `APPLIED LIVE` line, mirroring
`migrations/task732_ja_skill_rating_elo_reseed.sql`.

| order | migration | supersedes |
|---|---|---|
| 1 | `task744_selection_tuning_table.sql` | — |
| 2 | `task745_calibration_zipf_to_elo.sql` | — |
| 3 | `task746_user_skill_rating_adjustments.sql` | — |
| 4 | `task747_apply_calibration_to_skill_ratings.sql` | — |
| 5 | `task748_get_recommended_tests_vocab_aware.sql` | archives the live 3-arg body |

Migration 5 **must** be built by capturing the live definition first:

```sql
SELECT pg_get_functiondef(p.oid) FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' AND p.proname = 'get_recommended_tests';
```

and it must keep the 3-arg signature (`p_topic_recency_days smallint DEFAULT 14`)
so no overload is created. Ship it with `vocab_weight = 0` — inert on arrival,
enabled by a one-row `UPDATE` after §5.2's shadow window.

## 9. Key architectural decisions

1. **Vocabulary ranks, never filters.**
   - *Rationale:* 17-22% of en/zh tests are unlinked; a filter empties their pool.
   - *Rejected:* hard `unknown(t) BETWEEN 0.03 AND 0.07` — the dropped RPC's
     shape, and unreachable against live content.
2. **Untested senses get a Zipf prior, not a zero.**
   - *Rationale:* 90% of difficulty-9 senses have no row; a zero makes the term
     degenerate and worsens as the catalogue grows.
   - *Rejected:* count-only `INTERSECT` ratio (the dropped RPC's approach).
3. **Reuse the tier ladder for the ELO map.**
   - *Rationale:* content was seeded through the same anchors, so learner and
     content land on one scale; adds no fourth copy of the tier bands.
   - *Rejected:* a fitted logistic — no data to fit on (21 attempts, one learner).
4. **Seed-only below 5 attempts, damped+capped correction above.**
   - *Rationale:* the learner is no longer a cold start (§0.1), so seed-only
     alone would never fire for them.
   - *Rejected:* seed-only (inert today); unguarded writes (fights K=32 invisibly).
5. **Settings row, not a function parameter.**
   - *Rationale:* avoids the ambiguous overload the repo already had to clean up.
6. **`process_test_submission` untouched.** See §2.4.

## 10. Related Pages

- [[features/vocabulary-aware-test-selection]] — prose counterpart
- [[decisions/ADR-024-vocabulary-aware-test-selection]]
- [[algorithms/elo-implementation-analysis.tech]]
- [[algorithms/bkt-implementation-analysis.tech]]
- [[database/schema.tech]] · [[api/rpcs.tech]]
- [[tasklist/vocabulary-aware-test-selection.tasks]]
