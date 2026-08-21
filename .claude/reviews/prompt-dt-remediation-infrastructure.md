# Handoff prompt — DT remediation infrastructure

Copy everything below the line into a fresh session.

---

Fix the Dual Translation spaced-remediation infrastructure. It is broken in three independent
places and **the order of the fixes matters** — doing them in the wrong order arms a live 500.

## Background (verified 2026-08-21 — do not re-derive)

Live DB is Supabase project `kpfqrjtfxmujzolwsvdq`. I checked 30 migration-defined tables against
`information_schema`; findings below are confirmed, not inferred.

1. **`dt_card` and `dt_card_review` do not exist in the live database.**
   `migrations/dt_cards.sql` was written (TASK-612, dated 2026-07-14) but never applied. These are
   the **only** two missing tables of the 30 checked — an isolated miss, not systemic drift.
2. **DT synthesis is not scheduled.** `app.py::_initialize_scheduler` registers exactly 5 jobs
   (IRT 04:00, time-estimate 04:05, slug-health 04:10, queue-drain 04:15, study-plan weekly
   Sun 23:00). `scripts/dt_nightly_synthesis.py` is not among them — yet
   `routes/dual_translation.py:215-216` documents it as "the nightly job". The codebase believes
   it is scheduled. Consequence: `dt_error_profile_entry` is **empty (0 rows)** against 16
   `dt_error_instance` rows.
   *Unverified:* an external scheduler (Heroku Scheduler, host crontab) is configured outside the
   repo and I could not rule it out. **Check this first** — see Step 0.
3. **No frontend renderer** for `cloze` / `isolate_retranslate` cards on any of the three surfaces.
   `static/js/session/players/dual_translation.js:12-18` says so in-code.

`wiki/tasklist/master.md` marks TASK-612, 614, 615 and 618 all as `[x]` Done. They are not.
Treat every `[x]` in that file that claims a live migration as unverified until you check the
live schema — that drift is exactly what hid this.

**Why order matters.** `services/dual_translation/cards.py:267` early-returns
(`if not entry_ids: return 0`) before touching `dt_card` when the user has no `queued` profile
entries. That is the only reason this is latent. **Schedule synthesis before applying the
migration and you get:** `GET /api/dual-translation/next` failing on ~25% of calls
(`DT_ERROR_CARD_INTERLEAVE_EVERY` defaults to 4, `routes/dual_translation.py:66`), `/cards/due`
failing on every call, and the Practice Engine silently swallowing it as a `logger.warning`
(`services/practice_session_service.py:180`).

## Step 0 — Confirm the scheduling gap is real

Before writing anything, confirm no external scheduler already runs
`scripts/dt_nightly_synthesis.py`. `Procfile` declares only a `web:` process. If an external
scheduler **is** running it, the migration in Step 1 becomes urgent rather than merely required,
and Step 2 is a no-op. Report which case you found.

## Step 1 — Apply the migration (must be first)

Apply `migrations/dt_cards.sql` to the live project via Supabase MCP. It is idempotent
(`CREATE TABLE IF NOT EXISTS`) and purely additive; its FK targets (`users`,
`dt_error_profile_entry`, `dt_error_instance`) all exist.

Verify with the queries in the migration's own trailer: expect **16 columns** on `dt_card`,
**5** on `dt_card_review`, 3 FKs on `dt_card` and 1 on `dt_card_review`. Do not skip this — the
whole point of this task is that a migration was assumed applied and never was.

## Step 2 — Schedule the synthesis job

Add a job to `app.py::_initialize_scheduler` following the existing pattern exactly:
`coalesce=True`, `max_instances=1`, `replace_existing=True`, wrapped in try/except so a crash
cannot kill the scheduler.

**APScheduler runs in every gunicorn worker** (`Procfile`: `--workers 2`), so this job needs a
Postgres advisory lock like its neighbours — otherwise both workers synthesise concurrently and
race on the `(user_id, l1_language_id, l2_language_id, subtype)` upsert. Follow
`migrations/study_plan_advisory_lock.sql` (key `1467840848` = 'StPP'). Add a **new pair of RPCs
with a distinct key** for DT; do not reuse either existing key (the IRT job uses
`8901234567890123`). PostgREST cannot invoke `pg_try_advisory_lock(bigint)` positionally through
supabase-py, which is why these are wrapped RPCs rather than a direct call.

Schedule it **before** the 04:15 queue drain and after grading has settled — 03:50 UTC is a
reasonable slot, but it must not overlap the 04:00–04:15 chain. The entry point is
`run(db, window_days=..., threshold=..., user_id=None, dry_run=False)` in
`scripts/dt_nightly_synthesis.py`; knobs come from `DT_SYNTHESIS_WINDOW_DAYS` (default 30) and
`DT_SYNTHESIS_PROMOTE_THRESHOLD` (default 3). Import it the same lazy way the other jobs import
their services.

## Step 3 — Build the card renderer

Two card types, both with `answer` as the target. **The answer is always `corrected_form`, never
`learner_form`** — `migrations/dt_cards.sql` calls this "pedagogically critical" and the payload
builders enforce it. Do not invert it in the UI.

| card_type | `prompt_payload` shape |
|---|---|
| `cloze` | `{prompt, answer}` |
| `isolate_retranslate` | `{l1_context, target_sentence, answer}` |

Three surfaces need it:

1. **Daily-session DT player** — `static/js/session/players/dual_translation.js`. Currently
   re-requests `/next` up to `MAX_ERROR_CARD_RETRIES = 2` then offers a skip. Replace that
   workaround; remove the stale comment at lines 12-18 when you do.
2. **Standalone DT page** — `static/js/dual_translation.js`. Same `/next` envelope,
   `{type:'error_card', card_id, card_type, subtype, prompt_payload, ...}`.
3. **Practice player** — `static/js/session/players/practice.js:86` currently filters error
   cards out alongside gate and stress markers. Injected item shape is
   `{id:"dt-error-<card_id>", exercise_type:"dt_error_card", type:"error_card",
   is_error_exercise:true, word_sense_id:null, card_id, card_type, subtype, prompt_payload,
   state, due_date}`.

**Grade submission goes to `POST /api/dual-translation/cards/<card_id>/review` with
`{rating: 1-4, was_correct?: bool}` — NOT to `POST /api/practice/attempt`.** FSRS state lives on
`dt_card`. Getting this wrong on the practice surface would write the review into the wrong
system and silently corrupt the recurrence metric this feature exists to measure.

Any new user-facing string needs a key in **all four** `static/i18n/*.json` files, or the page
renders the raw key.

## Step 4 — Prove it works

The project convention (set by TASK-729) is that a happy-path test is not evidence a guard fires.
Four guardrails in this codebase were silently inert for months. So:

- Unit tests for the renderer payload handling and the grade-submission target.
- An end-to-end test that a promoted profile entry produces `dt_card` rows and that a due card
  is served, rendered and gradeable.
- **Revert-check:** confirm the suite goes red when the fix is removed. Report the counts.
- A test that pins the answer target as `corrected_form`.

Baseline is **1883 passed, 3 skipped, 0 failed** (`PYTHONPATH=. python -m pytest tests/`). Note
that "no tests collected" means an import error, not an empty suite — the `PYTHONPATH=.` and the
explicit `tests/` path are both required.

Then verify live, end to end: run synthesis against real `dt_error_instance` data (there are 16
rows), confirm `dt_error_profile_entry` populates, confirm cards materialise, and confirm
`GET /api/dual-translation/next` serves and renders an `error_card` without a 500.

## Constraints

- **Do not** run the test-generation or exercise-generation batches. Those are a later stage.
- Commit the existing uncommitted work first if it is still uncommitted — 5 live service files
  including `services/test_generation/orchestrator.py` carry the TASK-727–730 fail-closed judge
  guard and exist only in the working tree.
- Wiki updates: reconcile TASK-612/614/615/618 in `wiki/tasklist/master.md` to reflect reality,
  and log the session in `wiki/log.md`. Note that an ECC fact-force hook gates wiki writes
  (block-then-retry per file); if it blocks repeatedly, say so rather than silently skipping.
- Report honestly what you could not verify. This whole task exists because four tasks were
  marked Done on a migration that never ran.

---

## What follows this (do not start these yet)

**Stage 2 — readiness re-check.** Re-verify all four features against a 2-month no-changes run:
live schema vs. every `[x]` migration claim, scheduler job list, content inventory per language,
and the latent-failure surfaces. Prior review:
`.claude/reviews/two-month-testing-readiness-2026-08-21.md`.

**Stage 3 — content generation.** Japanese has **0 exercises and 0 word_assets** (en 8,857 /
zh 2,848), and tests exist only at difficulties 1/3/6/9. Both need closing before the phase.
Budget from measured rates: tests ~$0.00875 and ~2.9 min each; exercises ~5.5 min/sense with no
cross-language parallelism (~9 h per 100-sense chunk). Wall clock is the constraint, not spend.
