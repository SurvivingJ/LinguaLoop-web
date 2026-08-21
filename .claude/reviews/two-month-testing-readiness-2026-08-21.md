# Readiness Review: 2-Month Testing Phase

**Reviewed:** 2026-08-21
**Scope:** Session scheduling · Exercise generation · Test generation · Dual translation
**Method:** Code read + live Supabase inspection (project `kpfqrjtfxmujzolwsvdq`) + full pytest run
**Decision:** **REQUEST CHANGES** — two features are ready, two are not.

## Verdict at a glance

| Feature | Verdict | Blocking issue |
|---|---|---|
| Session scheduling | **Ready** | None blocking; starved by content gaps below |
| Test generation | **Ready** | None blocking; difficulty coverage thin |
| Exercise generation | **Not ready** | Japanese has zero content — 0 exercises, 0 word assets |
| Dual translation | **Partially ready** | Grading works; the whole remediation half is dead in 3 independent places |

Validation: pytest **1883 passed, 3 skipped, 0 failed**. The engineering is in good shape.
Every blocker below is a *deployment/content* gap, not a code-quality defect.

---

## CRITICAL

### C1 — `dt_card` and `dt_card_review` do not exist in the live database
**Files:** `migrations/dt_cards.sql` (never applied), `services/dual_translation/cards.py:272,305`,
`routes/dual_translation.py:324,338,622`

I checked 30 migration-defined tables against `information_schema`. **These two are the only ones
missing.** So this is an isolated miss, not systemic drift — but it is load-bearing.

`wiki/tasklist/master.md` marks TASK-612 (`Migration — dt_card, dt_card_review`) as `[x]` Done,
along with TASK-614/615/618 which all depend on those tables. The tables were never created.

**Failure scenario.** `generate_cards_for_queued_entries` early-returns at
`cards.py:267` (`if not entry_ids: return 0`) when the user has no `queued` profile entries, so the
bug is **latent today**. It arms the instant one entry is promoted:

- `GET /api/dual-translation/next` → HTTP 500 on ~**25%** of calls
  (`DT_ERROR_CARD_INTERLEAVE_EVERY` defaults to `4`, `routes/dual_translation.py:66`).
  The `dt_card` query sits inside the handler's outer `try`, so it returns `server_error`.
- `GET /api/dual-translation/cards/due` → HTTP 500 on **every** call.
- Practice Engine sessions → swallowed as a `logger.warning` at
  `services/practice_session_service.py:180` ("non-fatal"). Remediation silently vanishes with no
  user-visible signal — the exact silent-failure class this codebase has been hardening against.

**Fix:** apply `migrations/dt_cards.sql` before the phase starts, or explicitly disable the DT
remediation path. Do not leave it half-wired.

---

## HIGH

### H1 — Japanese has no practice content at all
**Evidence (live):**

| lang | vocab | word_assets | active exercises |
|---|---|---|---|
| en | 3,964 | 43 | 8,857 |
| zh | 3,957 | 183 | 2,848 |
| **ja** | **2,404** | **0** | **0** |

A Japanese learner gets tests (82) and DT passages (21) but **zero Practice Engine content**. Every
acquisition and maintenance slot the scheduler plans for a ja user will fail to hydrate, for two
months. TASK-515 — the top-1,000-sense batch that is the integration gate for this — is still `[~]`
in progress.

At the recorded batch economics (~5.5 min/sense, languages cannot run in parallel), closing this is
roughly **9 hours per 100-sense chunk**. That is a scheduling decision to make *now*, not mid-phase.

**Options:** run the ja batch before launch, or scope the testing phase to en/zh only.

### H2 — DT error synthesis is never scheduled
**Files:** `scripts/dt_nightly_synthesis.py`, `app.py:259-399`

`_initialize_scheduler` registers exactly **5** jobs — IRT calibration (04:00), time-estimate
refresh (04:05), slug health (04:10), generation-queue drain (04:15), study-plan weekly recompute
(Sun 23:00). **DT synthesis is not among them.**

The serving code nonetheless *assumes* it runs. `routes/dual_translation.py:215-216`:

> TASK-610: systematic errors are synthesised OFF the hot path by the nightly job
> (`scripts/dt_nightly_synthesis.py`), which reads these …

So this is stronger than "not scheduled" — **the codebase believes it is scheduled and it is not.**
Nothing ever promotes a subtype to `queued`, so `dt_error_profile_entry` is **empty (0 rows)**
against 16 recorded `dt_error_instance` rows.

*Caveat on this one:* I can only see in-repo scheduling. `Procfile` declares a `web:` process only,
and the script appears in no APScheduler job — but an external scheduler (Heroku Scheduler, a host
crontab) is configured outside the repo and I cannot rule it out from here. **Worth 30 seconds to
confirm**, because the empty `dt_error_profile_entry` table is consistent with either "never
scheduled" or "scheduled but never had enough data to promote".

This is *why* C1 has stayed latent — and it means fixing H2 alone, without C1, is what triggers the
500s. **Fix both together or neither.**

### H3 — No frontend renderer for DT remediation cards
**File:** `static/js/session/players/dual_translation.js:12-18` (explicit in-code acknowledgement)

> `error_card` items are NOT rendered here … no cloze/isolate renderer exists on any surface yet —
> the same gap the standalone page and the practice player have.

Handled gracefully (bounded re-request, then a skip affordance — `MAX_ERROR_CARD_RETRIES = 2`), so
it is not a crash. But combined with C1 and H2 it means **the entire spaced-remediation feature
(TASK-610/612/614/615/618, all marked Done) will generate zero learner signal across the two
months.** If measuring remediation is a goal of the phase, that goal is currently unachievable.

### H4 — Live service code is uncommitted
```
 M services/test_generation/orchestrator.py
 M services/test_generation/agents/question_generator.py
 M services/test_generation/schemas.py
 M services/exercise_generation/judges/base.py
 M services/exercise_generation/judges/distractor_plausibility.py
```
The TASK-727–730 fail-closed judging work — the guard that stops a dead model slug shipping
unjudged questions — **exists only in the working tree.** Starting a two-month phase from an
uncommitted tree means the deployed artifact is unreproducible and a stray `git checkout` reverts
the safety fix. Commit before launch.

---

## MEDIUM

### M1 — Test difficulty coverage has holes
Active tests cluster on the batch parameter `[1,3,6,9]`:

| lang | d1 | d3 | d5 | d6 | d7 | d9 |
|---|---|---|---|---|---|---|
| en | 26 | 26 | 1 | 26 | 1 | 26 |
| ja | 21 | 20 | 1 | 20 | — | 20 |
| zh | 31 | 31 | 1 | 33 | — | 29 |

Difficulties 2, 4, 5, 7, 8 are effectively empty. ELO/IRT matching has nothing at-level for a
mid-band learner, so it will serve off-band content and the resulting ability estimates will be
noisy for exactly the population a testing phase is meant to characterise.

Cheap to fix: at $0.00875/test the spend is negligible; wall clock (~2.9 min/test) is the constraint.
~100 tests across the gap bands is ~5 hours.

### M2 — Content burn-down over 60 days
- **Tests:** 313 active total (en 106 / ja 82 / zh 125). Audio present on ~98%, transcripts 100%.
- **DT passages:** 67 total (en 27 / ja 21 / zh 19). At 12 min/slot, a daily DT user exhausts a
  language's inventory in **~3 weeks**.

Neither is fatal, but both need a top-up plan before week 4, not after.

### M3 — Review queue has no drain process
`generation_review_queue`: **52 pending, 0 resolved, ever.** No human-in-the-loop exists. If the
staged distractor-judge v7 is activated during the phase, question-level review volume goes to
**22–47%** and this queue becomes unmanageable. Recommend keeping v7 inactive (its current state)
and assigning a queue owner.

### M4 — A third of LLM spend is unattributed
`llm_calls` over the last 30 days shows `task_name = 'unknown'` at **206 calls / $0.93** — the
single largest spend line. Cost attribution has a hole, which will make a two-month cost model
unreliable. Worth tracing before the phase, since the phase's economics are a stated goal.

---

## LOW

- **L1** — `tests.audio_generated` is `false` on all 313 rows while `audio_url` is populated on
  ~98%. A stale/unused flag; harmless, but it will mislead anyone querying audio coverage.
- **L2** — Baseline traffic is essentially zero (12 users, 1 study plan, 19 daily loads, 3 DT
  submissions). Nothing in this stack has been exercised under concurrent load. Gunicorn is
  configured `--workers 2 --timeout 120`; APScheduler runs in every worker and relies on Postgres
  advisory locks for safety (correctly implemented — `migrations/study_plan_advisory_lock.sql`,
  key `1467840848`).

---

## What is genuinely ready

**Session scheduling.** The strongest of the four. TASK-700–716 are closed, applied live, and
DB-verified. All scheduler tables exist. Cross-worker safety is real (advisory locks, `coalesce`,
`max_instances=1`). `STUDY_PLAN_ENABLED` gives an env kill switch with no redeploy. The hydration
shortfall instrumentation from TASK-702 will tell you when H1/M1/M2 bite. The scheduler itself is
not the risk — **its inventory is**.

**Test generation.** Mechanically sound. The fail-closed guard landed 2026-08-21 with 14 tests that
were proven to go red when either half of the fix is reverted — that is real evidence, not a
happy-path check. Economics are measured, not estimated ($0.00875/test, 2.9 min/test; ~$8.75 and
~49 h per 1,000). Spend is a non-issue at any plausible scale.

The unresolved distractor-judge calibration (v7 staged inactive, TASK-726 gold set unadjudicated)
is **not** a launch blocker: the live v4/v6 judge on `gemini-3.1-flash-lite` is safe and measured.
What's unresolved is how *finely* it discriminates, which is a research question, not a safety one.

---

## Recommended pre-launch sequence

**Must do (blocking):**
1. Commit the working tree (H4). ~10 min.
2. Decide DT remediation: apply `migrations/dt_cards.sql` **and** schedule synthesis **and** build
   the card renderer — or explicitly disable the path so it cannot half-fire (C1 + H2 + H3).
3. Decide Japanese: run the ja exercise batch, or scope the phase to en/zh (H1).

**Should do:**
4. Generate ~100 tests at difficulties 2/4/5/7/8 (M1). ~5 h wall clock, ~$1.
5. Assign a `generation_review_queue` owner; keep judge v7 inactive (M3).
6. Trace `task_name='unknown'` in `llm_calls` (M4).
7. Plan a week-4 content top-up for tests and DT passages (M2).

**Reconcile:** `wiki/tasklist/master.md` marks TASK-612/614/615/618 as Done when the underlying
tables do not exist. That drift is what hid C1. Worth a verification pass over other `[x]` rows that
claim a live migration.
