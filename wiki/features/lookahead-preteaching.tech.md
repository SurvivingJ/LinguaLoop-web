---
title: Lookahead Pre-Teaching — Technical Specification
type: feature-tech
status: planned
prose_page: ./lookahead-preteaching.md
last_updated: 2026-09-19
dependencies:
  - "table: user_word_ladder, user_vocabulary_knowledge, tests.vocab_sense_ids, exercises"
  - "table: generation_queue, daily_test_loads, weekly_plan_states, selection_tuning"
  - "RPC: get_recommended_tests, get_practice_session, build_daily_session, selection_vocab_ability"
  - "service: services/practice_session_service.py (_maybe_top_up_ladder), services/vocabulary_ladder/queue_drain.py"
breaking_change_risk: medium
---

# Lookahead Pre-Teaching — Technical Specification

> Every constant in this spec that is not marked *assumed* was measured. The
> measurements and the variant comparison are in
> [[evaluations/preteach-variants-2026-09-19]]; do not re-derive them here.

---

## 0. Ground truth (live, 2026-09-19)

| fact | ja | zh | en |
|---|---|---|---|
| tests with linked vocabulary | 59 | 98 | 100 |
| distinct senses across those tests | 1,589 | 4,029 | — |
| senses unknown to the live learner | 702 | 1,773 | — |
| …of those, with ≥3 active exercises | 16 | 0 | — |
| senses with *any* active exercise | 74 / 19,668 | 180 / 22,475 | 166 / 9,889 |
| mean Zipf, senses **with** exercises | 4.77 | 4.97 | 5.09 |
| mean Zipf, senses **without** | 3.87 | 4.09 | 4.19 |
| learner `ability_zipf` (`uvk_crossing`) | 5.0251 | 5.1525 | none |

Live engagement: **15 rows in `exercise_attempts`** ever, against 54 in
`test_attempts`; **47 of 47 `user_word_ladder` rows are `word_state = 'new'`**;
5 of the 47 clear the supply gate. `generation_queue` holds 22 rows — 11
`failed`, 7 stuck `running` since 2026-08-21, 4 `done`, **0 with
`reason = 'subscribe_topup'`**.

**Read that table as one sentence: the practice engine can only drill words the
learner already knows.** Sections 1–6 specify the algorithm; §7 specifies the
content work without which the algorithm has no effect.

---

## 1. Architecture Overview

Today the two halves of a day are independent. Tests are chosen by
`get_recommended_tests` (ELO, plus a vocabulary term that is still switched
off); practice is chosen by `get_practice_session` from the ladder and FSRS.
Neither reads the other.

Pre-teaching couples them in one direction only — practice is told what tests
are coming; test selection is not told what practice did, except through
`p_known`, which it already reads.

```
                  ┌─────────────────────────────────────────┐
  (weekly / on    │  open_preteach_cohort(user, lang)       │
   cohort close)  │    1. top-N pool  <- get_recommended_tests
                  │    2. blocking senses (p_known < 0.5)   │
                  │    3. rank by pool demand, C3 order     │
                  │    4. supply gate (>=3 active exercises)│
                  │    5. INSERT preteach_cohorts (+members)│
                  │    6. starved -> generation_queue       │
                  └───────────────┬─────────────────────────┘
                                  │ cohort members
                                  v
  ┌───────────────────────────────────────────────────────┐
  │ practice_session_service._maybe_top_up_ladder         │
  │   Queue C  lookahead   <-- NEW, drained first         │
  │   Queue A  evidence                                   │
  │   Queue B  packs                                      │
  └───────────────┬───────────────────────────────────────┘
                  │ user_word_ladder rows (state 'new')
                  v
  ┌───────────────────────────────────────────────────────┐
  │ get_practice_session(mode='acquisition')              │
  │   ladder_priority boosted for cohort members (§3.3)   │
  │   drills to Ring 2 cleared  (>=2 distinct days)       │
  └───────────────┬───────────────────────────────────────┘
                  │ ladder_record_attempt -> BKT -> p_known
                  v
  ┌───────────────────────────────────────────────────────┐
  │ preteach_cohort_status()  -> ready | waiting | expired │
  │   build_daily_session reads it and orders test slots  │
  └───────────────────────────────────────────────────────┘
```

**The coupling is advisory, never a lock.** `build_daily_session` *prefers* a
released test; it never withholds the catalogue. A learner who asks for a
specific test gets it (§5.3).

---

## 2. Database Impact

### 2.1 New: `preteach_cohorts`

One open cohort per (user, language). Closed rows are kept — they are the only
record of what was taught before which test, and §8's evaluation depends on
them.

```sql
CREATE TABLE public.preteach_cohorts (
    id              bigserial PRIMARY KEY,
    user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id     smallint    NOT NULL REFERENCES public.dim_languages(id),
    opened_at       timestamptz NOT NULL DEFAULT now(),
    deadline_date   date        NOT NULL,
    closed_at       timestamptz,
    close_reason    text CHECK (close_reason IN
                        ('ready','deadline','superseded','no_supply')),
    -- the pool this cohort was derived from, for the §8 counterfactual
    target_test_ids uuid[]      NOT NULL,
    -- snapshot, never recomputed. See §8.1.
    unknown_at_open jsonb       NOT NULL,   -- {test_id: unknown_share}
    unknown_at_close jsonb,
    params          jsonb       NOT NULL    -- {depth, ranking, budget, top_n, u_star}
);

CREATE UNIQUE INDEX preteach_cohorts_one_open
    ON public.preteach_cohorts (user_id, language_id)
    WHERE closed_at IS NULL;

CREATE INDEX preteach_cohorts_user_lang_opened
    ON public.preteach_cohorts (user_id, language_id, opened_at DESC);
```

The partial unique index is the concurrency control: two simultaneous session
requests cannot open two cohorts. The loser catches `23505` and reads the
winner's row.

### 2.2 New: `preteach_cohort_members`

```sql
CREATE TABLE public.preteach_cohort_members (
    cohort_id     bigint   NOT NULL REFERENCES public.preteach_cohorts(id)
                           ON DELETE CASCADE,
    sense_id      integer  NOT NULL REFERENCES public.dim_word_senses(id),
    demand_rank   smallint NOT NULL,   -- how many pool tests this sense blocks
    p_known_open  numeric  NOT NULL,   -- snapshot at open
    p_known_close numeric,
    status        text     NOT NULL DEFAULT 'pending'
                           CHECK (status IN
                             ('pending','subscribed','learned','starved')),
    PRIMARY KEY (cohort_id, sense_id)
);

CREATE INDEX preteach_members_status ON public.preteach_cohort_members
    (cohort_id, status);
```

`starved` is a first-class outcome, not an error: at today's coverage it is the
**majority** outcome (15.7 of 17.5 ja words per test), and §7's roadmap is
driven by counting these rows.

### 2.3 Changed: `generation_queue`

Add `'lookahead'` to the `reason` vocabulary alongside `regen`,
`coverage_gap`, `subscribe_topup` (`services/vocabulary_ladder/queue_drain.py`
lines 38–40), and give the drain a priority order — `lookahead` before
`subscribe_topup` before `coverage_gap` before `regen`. A lookahead row names a
word a real learner is blocked on this week.

**Two defects must be fixed in the same migration or the queue cannot be used
at all** (see [[evaluations/preteach-variants-2026-09-19]] §8):

```sql
ALTER TABLE public.generation_queue
    ADD COLUMN claimed_at timestamptz,
    ADD COLUMN priority   smallint NOT NULL DEFAULT 50;

-- reclaim the 7 rows that have been 'running' since 2026-08-21
UPDATE public.generation_queue
   SET status = 'pending', claimed_at = NULL
 WHERE status = 'running'
   AND requested_at < now() - interval '1 day';
```

`_claim_batch` sets `claimed_at`; any row `running` with
`claimed_at < now() - GENERATION_LEASE` is reclaimable. Without this,
`_open_queue_sense_ids` de-duplicates against the stuck rows forever and those
senses can never be regenerated.

### 2.4 Changed: `selection_tuning`

New rows, all tunable without redeploy, matching the existing `key`/`value`
shape:

| key | value | meaning |
|---|---|---|
| `preteach_enabled` | `0` | master switch, **ships off** |
| `preteach_depth` | `2` | ring to clear before release (§3.2) |
| `preteach_budget` | derived | `ceil(words_per_week * lead_days / 7)`, capped by the eligible pool |
| `preteach_top_n` | `10` | pool size the cohort is derived from |
| `preteach_kappa` | `0` | per-word cost model (§3.1a); 0 until fitted |
| `preteach_ranking` | `value_text = 'per_minute'` | `greedy` \| `frontier` \| `frequency` |
| `preteach_lead_days` | `3` | minimum days before release |
| `preteach_deadline_days` | `10` | hard close |
| `preteach_ready_share` | `0.70` | fraction of the cohort learned to release |

### 2.5 No change

`user_word_ladder`, `user_vocabulary_knowledge`, `exercises`, `tests` and every
ladder RPC are untouched. Pre-teaching chooses *which* senses enter the ladder;
it does not change what the ladder does with them. `daily_test_loads` keeps its
shape — ordering rides in the existing `daily_session_targets` jsonb (§5.2).

---

## 3. The algorithm

### 3.1 Cohort selection — `a2_cohort`, the chosen variant

For learner `u`, language `l`:

```
pool    = top_n tests from get_recommended_tests(u, l), by existing rank
S(t)    = t.vocab_sense_ids resolving to a dim_vocabulary row with frequency_rank
P(s)    = uvk.p_known  if a row exists
        = σ(1.5·(zipf(s) − ability_zipf) + ln(0.85/0.15))  otherwise
B       = { s ∈ ⋃ S(t) : P(s) < 0.50 }            -- blocking senses
demand(s) = |{ t ∈ pool : s ∈ S(t) }|
```

Order `B` by `(−demand(s), key_C(s), s)` and take the first `preteach_budget`
that clear the supply gate. `key_C` is the axis-C tiebreak:

| `preteach_ranking` | `key_C(s)` | rationale |
|---|---|---|
| **`per_minute`** (default) | `value_per_minute(P(s))` descending | points of `p_known` per minute of practice; tracks the best arm at every `kappa` |
| `greedy` | `P(s)` ascending | what `per_minute` degenerates to when `kappa < 0` |
| `frontier` | `P(s)` descending | what `per_minute` degenerates to when `kappa > 0` |
| `frequency` | occurrences in pool descending | best only at exactly `kappa = 0` |

### 3.1a The per-word cost model

Ranking by points per *minute* needs to know what a word costs to teach.

```
items(s) = max(RING2_FLOOR,
               (target_pk - P(s)) * (1 + k*(1 - P(s))) / GAIN_PER_ITEM)
value_per_minute(s) = (target_pk - P(s)) / (items(s) * 45s / 60)
```

`RING2_FLOOR = 6` is structural, not a learning curve: 3 required Ring-2
families x first-attempt successes on 2 distinct calendar days. No word
clears Ring 2 in fewer attempts however well it is already known — which is
why a half-familiar word is at most **2x cheaper**, never 10x.

`k` (kappa) is the only free parameter and it **flips the answer**. Measured
at an equal 30-minute practice budget, ja, in-band share:

| `k` | `frequency` | `frontier` | `greedy` | `per_minute` |
|---|---|---|---|---|
| -0.5 (unfamiliar cheap per point) | 0.339 | 0.305 | **0.407** | **0.407** |
| 0.0 (neutral) | **0.305** | 0.271 | 0.271 | 0.288 |
| +0.5 | 0.237 | **0.254** | 0.237 | **0.254** |
| +1.0 (unfamiliar dear per point) | 0.220 | **0.237** | 0.186 | **0.237** |

`per_minute` matches or beats the best fixed arm everywhere except exactly
`k = 0`, where `frequency`'s pool-demand information wins by 0.017. That is
the case for making it the default.

**`k` is not measurable today** — it needs attempts-to-Ring-2 against
starting `p_known`, and there are 15 `exercise_attempts` in total. Ship
`k = 0` and fit it from `exercise_attempts` once the cohort path has produced
traffic.

**Bound what this axis can carry.** Its entire range is ~0.13 in-band share
(0.407 best to 0.271 worst). The supply gate is worth 0.119 -> 0.983. Axis C
is a tuning question; §7 is the feature.

`P(s)` is exactly [[features/vocabulary-aware-test-selection.tech]] §3.2 and
**must stay a single implementation.** Extract it into
`public.selection_p_known(sense_id, ability_zipf)` and have both
`get_recommended_tests` and this call it; two copies of a formula whose prior
offset has already been corrected once will drift.

**Supply gate.** `count(exercises WHERE word_sense_id = s AND language_id = l
AND is_active) >= 3`, i.e. `LADDER_MIN_EXERCISES_PER_SENSE`, reused verbatim.
Senses failing it are inserted as `status = 'starved'` and enqueued (§3.5).
They are *not* skipped silently — they are the roadmap.

**Ordering constraint.** Demand is the primary key and `key_C` only a tiebreak,
because demand is what makes the cohort 10× cheaper per test than pinning one
test. Inverting them collapses `a2_cohort` back toward `a1_commit`.

### 3.2 Depth — Ring 2 cleared

A cohort member is `learned` when `user_word_ladder.current_ring >= 3`, i.e.
Ring 2 has cleared: every Ring-2 family at confidence ≥ 0.50 **and** first-
attempt successes on ≥ 2 distinct calendar days
([[algorithms/vocabulary-ladder]]).

Measured, on both languages: Ring 1 only puts 36% (ja) / 70% (zh) of the
catalogue in band; Ring 2 puts **98% / 100%**; Gate A adds **nothing** for 66%
more practice time. Ring 2 is not a compromise between the two — it is the
whole effect.

The cross-session gate is why `preteach_lead_days` cannot be 1. Three days is
the floor and it is structural, not a tuning choice.

### 3.3 Priority inside the practice session

Cohort members must win Acquisition's word choice without a new scoring system.
`get_practice_session` already ranks by the unified score with
`α · ladder_priority` dominant in Acquisition ([[algorithms/practice-unified-score]]).
Add a bounded additive bonus to `ladder_priority` for open-cohort members:

```
ladder_priority' = ladder_priority + preteach_boost      -- preteach_boost = 0.25
```

Additive and bounded, so a gated or relapsing word still outranks a fresh
cohort word — relapse handling is more urgent than any lookahead. Do **not**
re-weight `α`: that changes every learner's session, including those with no
cohort.

### 3.4 Readiness and release

```
learned_share = |members WHERE status = 'learned'| / |members WHERE status != 'starved'|

status = 'ready'   when learned_share >= preteach_ready_share (0.70)
                    AND age >= preteach_lead_days
       = 'expired' when age >= preteach_deadline_days
       = 'waiting' otherwise
```

`starved` members are excluded from the denominator. Including them would make
a cohort that is 90% starved permanently unready, which is precisely today's
state — the learner would simply never be served a test again.

On `ready` or `expired` the cohort closes (`close_reason` accordingly), its
`unknown_at_close` is written, and the next call may open a new one.

### 3.5 Starved members → generation demand

Every `starved` member is enqueued via the existing
`queue_drain.enqueue(db, sense_id, language_id, REASON_LOOKAHEAD, detail={...})`
with `priority = 10`. `DEMAND_GENERATION_MAX_PER_CALL = 5` is raised to the
cohort budget for this path — the existing cap was sized for an incidental
signal, and here the starved set *is* the payload.

---

## 4. API / RPC Surface

### `open_preteach_cohort(p_user_id uuid, p_language_id smallint, p_force boolean DEFAULT false) → jsonb`

- **Purpose:** compute and persist the next cohort for a learner.
- **Arguments:** `p_force` bypasses the "an open cohort already exists" guard
  (admin/debug only).
- **Returns:** `{cohort_id, members: [{sense_id, demand_rank, p_known, status}],
  starved_count, deadline_date, params}`; or `{skipped: 'cohort_open',
  cohort_id}`; or `{skipped: 'disabled'}` when `preteach_enabled = 0`.
- **Errors:** `E_NOABILITY` when `selection_vocab_ability` cannot identify a
  crossing **and** there is no `user_calibration_state` row — without
  `ability_zipf` every `P(s)` is a guess and the cohort would be noise. Callers
  treat this as "no cohort", not as a failure.
- **Auth:** `SECURITY DEFINER`, `search_path = public, pg_temp`; the route layer
  passes the authenticated user id and never accepts one from the client.
- **Side effects:** inserts `preteach_cohorts` + members; enqueues starved
  senses.

### `preteach_cohort_status(p_user_id uuid, p_language_id smallint) → jsonb`

- **Purpose:** the readiness read, called by `build_daily_session` and the FE.
- **Returns:** `{cohort_id, state: 'ready'|'waiting'|'expired'|'none',
  learned, pending, starved, learned_share, days_open, target_test_ids}`.
- **Side effects:** none. `STABLE`. Closing is done by `close_preteach_cohort`,
  called from the daily resolver, so a read can never mutate.

### `close_preteach_cohort(p_cohort_id bigint, p_reason text) → jsonb`

Writes `closed_at`, `close_reason`, `unknown_at_close`, and the members'
`p_known_close`. Idempotent — a second call on a closed cohort is a no-op.

### Changed: `build_daily_session(p_user_id, p_language_id, p_date)`

Two additions, both inside the existing shape:

1. **Before the greedy fill**, call `preteach_cohort_status`. If `ready` or
   `expired`, close the cohort; if `none` and `preteach_enabled = 1`, open one.
2. **In the hydration step (§6 of the current body)**, when a cohort is `ready`,
   order the per-skill `get_recommended_tests` result by
   `(test_id = ANY(cohort.target_test_ids)) DESC, ABS(rec.elo_diff)` instead of
   `ABS(rec.elo_diff)` alone.

That is the whole integration: **a tiebreak in an ORDER BY.** The budget
solver, the spacing penalty and the value model are untouched. The released
tests are already in the candidate set — they came from `get_recommended_tests`
when the cohort was opened — so this cannot introduce an unranked test.

`daily_session_targets` gains `preteach: {cohort_id, state, released: [test_id]}`
for the FE and for §8.

### Changed: `practice_session_service._maybe_top_up_ladder`

Queue C is drained first:

```python
fresh = self._nominate_from_lookahead(user_id, language_id, want, subscribed)
source = 'lookahead' if fresh else 'none'
if len(fresh) < want:
    evidence = self._nominate_from_evidence(...)   # Queue A, unchanged
    ...
if len(fresh) < want:
    packs = self._nominate_from_packs(...)          # Queue B, unchanged
```

`_nominate_from_lookahead` reads open-cohort members with
`status = 'pending'`, passes them through `_senses_with_supply` (the same gate
that chose them — cheap, and exercises can be deactivated between open and
drain), marks admitted rows `subscribed`, and returns them. Queues A and B are
not modified.

---

## 5. Behaviour at the edges

### 5.1 No cohort is possible

`open_preteach_cohort` returns `{cohort_id: null, starved_count: N}` when every
blocking word fails the supply gate — **today's state for zh, where 0 of 26.4
blocking words per test are ladder-drillable.** The day composes exactly as it
does now, and N starved senses are enqueued. The feature degrades to a
generation-demand signal, which is the most useful thing it can be until §7
lands.

### 5.2 Cohort ready but the test is already completed

`build_daily_session` carries over `completed_test_ids` (TASK-705). A released
test already completed today is not re-served; the cohort still closes `ready`.

### 5.3 The learner asks for a specific test

Unaffected. Pre-teaching only reorders `build_daily_session`'s hydration. Direct
test routes do not consult cohort state.

### 5.4 Multi-language learners

Cohorts are per (user, language) by the partial unique index. A ja cohort does
not suppress zh intake — the same isolation `_eligible_ladder_count` already
implements by joining through `dim_word_senses → dim_vocabulary`.

### 5.5 The learner stops studying

The deadline closes the cohort at `preteach_deadline_days`. Members not learned
revert to ordinary ladder rows in whatever state they reached; nothing is
unsubscribed. A word half-learned is still a word half-learned.

---

## 6. Key Architectural Decisions

1. **Decision:** derive the cohort from a *pool* of ten tests, not one pinned test.
   - **Rationale:** measured ~10× cheaper — 1.7 words per test brought into band
     versus 17.8 — because shared vocabulary amortises across the pool. It also
     removes the need to commit to a test days ahead.
   - **Alternatives rejected:** `a1_commit` (pin one test) — correct-looking and
     an order of magnitude more expensive. `a3_demand` (catalogue-wide, no
     target) — needs 500 words to reach 68%, versus 15 for 90% on the pool.

2. **Decision:** teach to Ring 2 cleared, not Ring 1 and not mastery.
   - **Rationale:** 36% → **98%** → 98% in band across the three depths, at
     52 / 157 / 261 minutes. Ring 2 is where the entire effect lives.
   - **Alternatives rejected:** a cheap "tomorrow's words" recognition screen —
     it does not move the arithmetic. Full mastery before release — 66% more
     time for zero additional tests.

3. **Decision:** rank by pool demand first, `p_known` ascending as tiebreak.
   - **Rationale:** demand is what makes the cohort cheap; least-known-first won
     at every bounded budget (0.339 vs 0.288 vs 0.271 at 5 words).
   - **Alternatives rejected:** frontier-first — lost on this arithmetic, but see
     the caveat in §9; it ships as a selectable arm rather than being discarded.

4. **Decision:** advisory ordering, never a lock on the catalogue.
   - **Rationale:** a lock converts a content shortage into a dead app. With
     zh at zero drillable blocking words, a locking design would serve that
     learner nothing at all.
   - **Alternatives rejected:** withholding un-prepared tests; a hard vocabulary
     filter — already rejected for selection in
     [[decisions/ADR-024-vocabulary-aware-test-selection]] for the same reason.

5. **Decision:** ship behind `preteach_enabled = 0` and land §7 first.
   - **Rationale:** enabling it on today's inventory produces cohorts of 1–2
     words and changes nothing measurable, while adding a failure surface.
   - **Alternatives rejected:** shipping on to generate demand signal — the
     signal is obtainable from `open_preteach_cohort` in dry-run without
     touching a learner's session.

6. **Decision:** one implementation of `P_known`, shared with the ranker.
   - **Rationale:** the prior offset in §3.2 has already been corrected once
     (0.5 → 0.85 crossing). A second copy would silently diverge from the first.
   - **Alternatives rejected:** reimplementing it in the cohort RPC.

---

## 7. The content work (this is the critical path)

Without this section the rest of the spec is inert. Generate ladder exercises
for demand-ranked senses — senses ordered by how many catalogue tests they
block for learners at this ability.

| senses generated per language | ja tests reachable (59) | zh (98) |
|---|---|---|
| 0 — today | 4 (7%) | 10 (10%) |
| +200 | 12 (20%) | 31 (32%) |
| **+500** | **45 (76%)** | **54 (55%)** |
| +1,500 | 57 (97%) | 87 (89%) |

Total addressable: 702 ja / 1,773 zh. At ~$0.024 and ~5.5 min wall clock per
sense ([[task515-batch-economics]]), **500 senses ≈ $12 and ≈ 46 hours per
language**, serial. Wall clock is the constraint, not spend.

Each sense needs ≥3 active exercises covering Ring 1 and Ring 2 families —
`phonetic_recognition`/`definition_match` plus `cloze_completion` and
`cloze_typed`/`morphology_slot` — which is what
[[features/exercises]]' `batch-exercise-generation` path already produces.

**The demand ranking is a query, not a new system**, and
`open_preteach_cohort(p_force)` in dry-run emits it per learner. The nightly
`enqueue_coverage_gaps` should be re-pointed at it: today it ranks by frequency,
which is exactly how the inventory ended up covering only words the learner
already knows.

---

## 8. Testing Strategy

### 8.1 The evaluation trap — read before designing any A/B

`update_vocabulary_from_test` writes `p_known` **from** test results. So
`unknown(t)` measured after an attempt is contaminated by that attempt's
outcome. Measured directly: the recorded as-of relationship is
**Spearman = −0.584**; recomputing it from current `p_known` on the same 21 ja
attempts gives **r = +0.107** — the sign inverts.

**Therefore:** `unknown_at_open` and `unknown_at_close` are snapshots written by
the RPCs at those instants and are never recomputed. Any analysis that derives
unknown share at analysis time is invalid and will report success regardless of
whether the feature works.

### 8.2 Unit

- `selection_p_known` matches `tests/sql/test_task748_vocab_ranking.sql`'s
  pinned value — a sense at `ability_zipf` scores `unknown = 0.1496`.
- Cohort ordering: demand dominates `key_C`; a sense blocking 4 pool tests
  outranks a less-known sense blocking 1.
- Supply gate: a sense with exactly 2 active exercises is `starved`; with 3 it is
  admitted; with 3 of which one is `is_active = false` it is `starved`.
- Readiness: `starved` excluded from the denominator (a 9-starved/1-learned
  cohort is `ready`, not `waiting`).
- Lease reclaim: a `running` row older than the lease is re-claimable and
  `_open_queue_sense_ids` no longer hides it.

### 8.3 Integration

- `build_daily_session` with a `ready` cohort puts a released test first **and**
  returns the same `used_minutes` and `objective_value` as without one — the
  budget solver must be provably untouched. Assert on a frozen fixture, the way
  TASK-710 proved its consolidation output-identical.
- Concurrency: two parallel `open_preteach_cohort` calls produce one row; the
  loser returns `{skipped: 'cohort_open'}`.
- `preteach_enabled = 0` is output-identical to today across the 20-scenario
  daily-session fixture matrix.

### 8.4 Offline replay

`scripts/simulate_preteach_variants.py` is the harness and must stay read-only.
Re-run it after every generation batch; the number that matters is the gated
in-band share converging on the ceiling arm.

### 8.5 Live A/B (only after §7)

Single axis: `preteach_ranking` `greedy` vs `frontier` (§9). Outcome: test score
at release, against `unknown_at_open` as covariate. **Not** powered at n=1
learner — this waits for real cohort traffic and is recorded as such rather than
run early and over-read.

---

## 9. Open Questions

- **OPEN/BLOCKING for axis C.** The simulation charges 12 items to every word
  regardless of starting `p_known`. BKT assumes otherwise. If a word at 0.45
  clears Ring 2 in fewer attempts than one at 0.05, `frontier` is being
  overcharged and may be the better default. Resolve with §8.5; until then
  `greedy` ships as default and `frontier` as a one-row switch.
- **ANSWERED 2026-09-19.** Neither: **the learner sets `words_per_week`
  directly** (a new column on `user_study_plans`; casual ~20, serious ~100),
  and it replaces `target_new_rate`'s derived `daily_minutes // 6` as the
  ladder intake ceiling. `preteach_budget` derives from it rather than being a
  constant, and the cohort-vs-plan conflict disappears — Queue C already
  *replaces* rather than adds to intake (§4), so the setting governs load
  directly. Two consequences for TASK-793: `target_active_pool` and
  `target_review_rate` are still `daily_minutes`-derived and must be checked
  for coherence against a learner asking for 100 words/week; and at 100/week
  the ja demand pool (1,582 test-referenced senses without exercises) is
  exhausted in ~16 weeks, so §7 is a standing process, not a backfill.
- **OPEN.** `preteach_top_n = 10` is inherited from the existing `rank_in_type`
  cap, not measured. Larger pools should raise sharing and lower words-per-test;
  the simulation can sweep it.
- **ANSWERED 2026-09-19.** The FE does **not** name the target test. Cohort
  progress renders as "words for the week ahead"; the released test appears in
  the day already unlocked, without back-reference. Consequence for TASK-792:
  `preteach` in the `/api/practice/session` payload must **not** carry
  `target_test_ids` — that field stays server-side, or the client can leak it.

## Related Pages

- [[features/lookahead-preteaching]] — prose counterpart
- [[evaluations/preteach-variants-2026-09-19]] — every measurement quoted here
- [[decisions/ADR-026-lookahead-preteaching]] — decisions and rejected alternatives
- [[features/practice-engine.tech]] — the session loop this feeds
- [[features/vocabulary-aware-test-selection.tech]] — `P_known`, `u*`, `selection_tuning`
- [[features/study-plans.tech]] — `build_daily_session`, the budget solver
- [[algorithms/vocabulary-ladder.tech]] — rings, families, cross-session gate
- [[algorithms/practice-unified-score.tech]] — where `preteach_boost` lands
- [[tasklist/lookahead-preteaching.tasks]] — the build
