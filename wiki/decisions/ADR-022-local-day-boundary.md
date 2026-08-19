---
title: "ADR-022: Daily-load day boundary resolves through the plan timezone, not UTC"
status: accepted
date: 2026-08-07
---

# ADR-022: Daily-load day boundary resolves through the plan timezone, not UTC

## Context

Finding **F15** of [[algorithms/daily-session-implementation-analysis.tech]]: the daily load rolls
over at **UTC midnight**. `routes/study_session.py::_today_iso()` is literally
`datetime.now(timezone.utc).date().isoformat()`, and `services/test_service.py` uses UTC dates the
same way. Meanwhile `user_study_plans.timezone` **is** collected and stored
(`routes/study_plan.py`, validated as an opaque non-empty string in V1) and then never read.

For the primary ZH/JA audience (UTC+8/+9) UTC midnight falls at **07:00–09:00 local**. Practical
symptoms:

- A learner studying in the evening has their day roll over mid-morning the next day, so an
  interrupted session can be replaced by a *new* day's load before they return to it.
- "Today's session" does not mean today to the user, which undermines the daily-habit framing the
  whole planner rests on.
- `weekly_plan_states.week_start_date` is `date_trunc('week', NOW())` — also UTC — so the week
  boundary inherits the same skew.

The counter-pressure is that the date is a **key**, not just a display value:
`daily_test_loads` is unique per `(user, language, load_date)`, and every existing row was written
under UTC semantics.

## Decision

Resolve the day boundary through **`user_study_plans.timezone`**: `_today_iso()` (and the
equivalent date derivation in `test_service` / the resolver) returns the learner's **local** date,
not the UTC date. UTC remains the fallback when a plan has no timezone set.

## Consequences

**Easier:**
- "Today" means today for the learner; the daily-habit loop stops fighting the clock.
- `user_study_plans.timezone` stops being stored-but-unused — a small correctness debt cleared.

**Harder / newly constrained — this is the expensive option and the risks are real:**
- **`daily_test_loads` uniqueness semantics change.** The uniqueness key stays `(user, language,
  load_date)`, but `load_date` is now derived from a *per-user* rule rather than a global one. A
  learner who travels or edits their timezone can produce a `load_date` that moves backwards,
  colliding with an existing row (which `build_daily_session`'s TASK-705 same-day-safe path will
  treat as a re-invocation) or skipping a date entirely. A timezone change needs a defined policy.
- **Existing rows carry UTC semantics.** Historical `load_date` values are not re-interpretable.
  Whether to backfill, or simply accept a one-time discontinuity at cutover, must be decided
  explicitly rather than left implicit.
- **The date must be derived in one place.** Today the UTC date is computed independently in at
  least `routes/study_session.py` and `services/test_service.py`. Local-date derivation must be a
  single shared helper that takes the plan timezone, or the two call sites will drift and produce
  *different* "today"s for the same request — a silent, hard-to-trace class of bug.
- **The weekly boundary should follow.** Leaving `week_start_date` on UTC `date_trunc` while daily
  loads go local creates a new inconsistency at the week edge. Either move both or state clearly
  why not.
- **Timezone validation tightens.** V1 accepts any non-empty string; a value that is not a valid
  IANA zone must fail safe to UTC rather than raise inside the resolver — cf.
  [[decisions/ADR-020-late-symbolic-resolution-must-fail-safe]], which is exactly the failure class
  of a slug resolved into the wrong space.

## Alternatives Considered

- **Keep UTC and document it.** Zero risk, zero migration. Rejected: the symptom lands squarely on
  the primary audience, and the field was already being collected on the promise of using it.
- **Configurable rollover offset (e.g. 04:00 local), default UTC.** Fixes the worst symptom —
  mid-morning rollover — while keeping the date key derived from one deterministic rule, so the
  uniqueness problem stays small. A genuinely reasonable middle option; rejected in favour of the
  correct behavior now rather than a second migration later.

## Implementation

Filed as **TASK-716** in [[tasklist/archive/daily-session-hardening.tasks]] — including the
single-helper requirement, the timezone-change policy, the week-boundary question, and the
fail-safe-to-UTC validation. Resolves finding **F15**.

## Related Pages

- [[algorithms/daily-session-implementation-analysis.tech]] — F15
- [[pages/study-session.tech]], [[features/study-plans.tech]]
- [[decisions/ADR-011-per-language-independent-budgets]], [[decisions/ADR-020-late-symbolic-resolution-must-fail-safe]]
