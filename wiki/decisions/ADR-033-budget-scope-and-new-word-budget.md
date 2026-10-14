---
title: "ADR-033: Budget scope and a daily new-word quota"
status: accepted
date: 2026-10-13
---

# ADR-033: Budget scope and a daily new-word quota

Amends [[decisions/ADR-009-two-budget-tests-vs-practice]]. (File name kept for link stability; it was first
written as "a separate new-word budget".)

## Revision 2026-10-13 (c)

Developer decisions closing four open items (later the same day):

1. **Vocabulary review off with `new_words_per_day > 0` is allowed.** The API does not reject it. The in-budget practice
   share is 0, so all new words go to the optional tail. The settings page shows, under the new-words input,
   "Vocabulary review is off — words you learn won't be reviewed." (`study_plan.session.new_words_no_review_warning`).
2. **Quota semantics are Anki-like.** `new_words_per_day` counts words **started** per local day, not words admitted.
   A word's `started_at` is `MIN(exercise_attempts.created_at)` for the (user, sense); verified that `user_word_ladder`
   has only `created_at` (admission) and no first-attempt column. Admitted-but-unstarted words carry over and are served first.
   Intake is `want = governed_quota − (unstarted admitted + started today)`. The earlier "unstarted words roll over but
   do not count against tomorrow's quota" rule and the `admitted_today` count are removed.
3. **Review forecast `item_seconds`** is the median over all the learner's timed vocabulary-exercise attempts (no review-only
   filter in v1) and is labelled an estimate.
4. **Calibration:** an explicit skip ("I don't know", stored as `chosen_sense_id IS NULL`, `is_correct = false`,
   `answered_at` set) is wrong evidence for BKT and Queue A2; items never answered (`answered_at IS NULL`) are ignored.

## Revision 2026-10-13 (b)

Same day, after the developer's final decisions. **The first version of this ADR put new words in an extra
pool outside `daily_minutes`. That is superseded and removed.** What changed and why:

| Was (first version of this ADR) | Now (this revision) | Why |
|---|---|---|
| New words are an "extra pool" outside `daily_minutes`; the day is longer than the learner's number | `new_words_per_day` is an Anki-style **daily quota inside the planner**. Tier C fits what fits in the in-budget practice share; the remainder is an **optional tail** after the main session | "Daily minutes" should mean what it says; the learner still gets their quota, and nothing is forced |
| `extra_weekly_minutes`, Tier C pool 2 (`x_acq` / `x_maint`, own budget, 1.5x cap) | Removed. The tail is derived live and has no budget | One pool, no second greedy loop |
| `tests_and_review` freed the acquisition minutes by scaling tests/surfaces up (`scale_up_to_target`, about +28% on the ZH 30-minute template) | Removed. Tests are not rescaled; practice-share minutes the day cannot use (no new words available, nothing due) **return to tests** inside the budget | The scale-up changed the shape of every learner's week for a gap that supply shortfalls already create and close |
| `tests_only` put review in an extra pool sized by `REVIEW_EXTRA_CAP_FRACTION` | `tests_only` puts all review and all new words in the tail; the weekly review target still exists but only as a tail target (`REVIEW_TAIL_CAP_FRACTION`) | The in-budget pool holds only tests and surfaces under this scope |
| Shares written `1.0 / 0.0`; `weekly_plan_states_shares_sum` relaxed | Shares are **derived** (`maintenance = review / (review + in-budget acquisition)`) and persisted for observability. The CHECK **stays relaxed** because the derived values reach 1.0 / 0.0 | Acquisition lives in the practice pool again, so a constant 1.0 / 0.0 would mislead; the original bounds cannot hold when `new_words_per_day = 0` |
| Backfill unit OPEN | **Accepted:** `max(1, daily_minutes // 6)` **per day** (5/day at 30 min), about 7x the old per-week rate of `target_new_rate()` | Developer decision, taken knowingly |
| Reviews and new words unordered | **Reviews first**, in the main session and in the tail. A **review-load governor** scales the quota by backlog | A 7x higher new-word rate would otherwise bury the learner in reviews |
| Cold start: calibration writes no vocabulary evidence | Calibration (definition mode) writes **BKT evidence** at `/end`; a single wrong calibration answer admits a sense to Queue A2, below test and word-quiz evidence | Developer decision (4A + 4B) |
| Layout of the settings card open | **Option A**, one card with stacked sections | Developer decision |

Note on the review forecast: the developer's proposed formula ended `... / 60 / 30`. With a 30-day window the
number of words inside the window is `30 * n`, which cancels the `/ 30`, so the forecast is
`n * REVIEWS_PER_NEW_WORD_30D * seconds / 60` (steady state). The `/ 30` form is the load of a single day's cohort,
not the load "in a month". Marked tunable/OPEN in the tech page.

## Context

[[decisions/ADR-009-two-budget-tests-vs-practice]] gave each (user, language) two budgets, Tests
and Practice, with Practice split internally into Maintenance and Acquisition by
`rebalance_practice`. `daily_minutes` covered both. The consequences the developer wants to change:

- The number of new words a learner meets is an output of a pressure formula and a time split, not
  something they can state. Practice minutes fall out of a template constant, so "teach me 5 new
  words a day" has no direct expression.
- Ladder intake is triggered by an eligible-pool floor (`target_active_pool(daily_minutes)`), which
  is a pool size, not a rate.
- A learner who wants `daily_minutes` to mean "tests" and treat vocabulary work as optional has no
  way to say so.

Decided with the developer on 2026-10-13, building on [[decisions/ADR-032-session-module-exclusion]]:

1. Two new per-language settings: a budget scope and a number of new words per day.
2. Flashcards and dual translation count as "tests" for the scope choice.
3. New words are a count of words (a quota), not minutes.
4. The `practice` module now means Vocabulary review only.
5. (Revision (b)) The quota lives inside the planner, with an optional tail, a review-load governor and calibration
   evidence for cold start.

## Decision

1. **Budget scope.** `user_study_plans.budget_scope` is `'tests_and_review'` (default, current
   behaviour) or `'tests_only'`. It decides whether the vocabulary practice share (due reviews, then new words)
   sits inside `daily_minutes` or in the optional tail. Flashcards and `dual_translation` are
   in-budget under both scopes. "Exercises" means only the vocabulary ladder practice.
2. **New-word quota.** `user_study_plans.new_words_per_day smallint`, 0 to 50, a word count and a daily quota.
   0 turns new-word teaching off. Existing rows are backfilled with `max(1, daily_minutes // 6)` **per day**; the
   route sets the same value for new rows; the column default of 5 is only a safety net.
3. **Day model.** Daily session = **main session** (`total_weekly_minutes * weekday weight / 7`, derivation
   unchanged) + **optional tail** (outside the budget, not required for completion, counted toward weekly targets).
   Inside the main session's practice share, **due reviews are scheduled before new words**; unused share minutes return
   to tests. The tail holds the due reviews that did not fit (most overdue first), then the remaining quota
   (`effective quota - started today`, admitted-but-unstarted words first). Under `tests_only`, or with Vocabulary review excluded, the in-budget pool holds only tests
   and surfaces and everything vocabulary-related is in the tail. UI at session end: "Session done — N reviews and M new
   words left today. Keep going?".
4. **Tier B.** `practice_target_minutes` is the practice pool as before the budget settings: the template's practice
   minutes with the flex factor, clamped to `daily_minutes * 7` (zero under `tests_only` or when `practice` is excluded).
   Inside it `rebalance_practice` sizes review by due pressure (`review_share`, 0.15..0.50). In-budget acquisition minutes
   are `min(quota minutes, practice pool - review)`. No scale-up of tests. `tests_only` still sizes a weekly review target
   (cap `REVIEW_TAIL_CAP_FRACTION = 0.5` of `daily_minutes * 7`) as a tail target.
5. **Tier C.** `build_daily_session` fills the in-budget practice share directly: due reviews first, then
   `S = min(E, floor(remaining / minutes_per_new_word))` whole new words, where `E` is the governed quota; leftover
   minutes return to the test budget. There is one pool and no extra-pool loop. After an intake supply check, `S` is
   capped by the words that can be served.
6. **Review-load governor.** `backlog` = minutes of overdue-and-not-done reviews; `T` = one day of review allowance
   (`REVIEW_BACKLOG_THRESHOLD_DAYS = 1.0` times `max(3 min, review_target_minutes / 7)`). Effective new words today =
   quota if `backlog <= T`, `floor(quota / 2)` if `T < backlog <= 2T`, `0` if `backlog > 2T`. UI: "New words paused —
   catching up on N reviews" (or "reduced"). Disabled when Vocabulary review is excluded.
7. **Forecast.** Beside the input: "≈ +X min/day of reviews in a month", `X = n * REVIEWS_PER_NEW_WORD_30D * median review seconds / 60`
   (`n` = average new words per calendar day, `REVIEWS_PER_NEW_WORD_30D = 7` proposed, tunable/OPEN; the median is over all
   timed vocabulary-exercise attempts in v1 and the figure is an estimate, ANSWERED 2026-10-13).
8. **Module rule.** The "at least one module stays included" rule counts `new_words_per_day > 0`
   as an included module.
9. **Ladder intake.** The pool-floor trigger is replaced by a per-local-day quota
   (`want = governed_quota_today - (unstarted admitted + started today)`; a word is started by its first `exercise_attempts` row,
   see Revision (c)). Nominations come from, in order: Queue A1 (unknown words from recent
   tests and word quizzes), Queue A2 (calibration wrongs: a single wrong answer is sufficient, ranked below A1), Queue B
   (lookahead cohorts, empty until [[features/lookahead-preteaching]] ships). The supply gate stays; unmet quota is
   recorded as a shortfall and surfaced.
10. **Cold start (4A + 4B).** 4A: the introductory tests' evidence (A1). 4B: calibration `/end`, definition mode only,
    sends the answered anchors through `update_vocabulary_from_word_tests_batch` (BKT evidence, no ladder or flashcard side
    effects). Provenance is read from the calibration ledger plus one `calibration_sessions.bkt_applied_at` marker.
11. **Minutes per new word** is a per-language nightly estimate stored on
    `dim_languages.new_word_minutes_est`, with `Config.NEW_WORD_MINUTES_DEFAULT = 3.0` as fallback.
12. **Shares.** `maintenance_share` / `acquisition_share` stay in the schema as derived observability values; the
    `weekly_plan_states_shares_sum` CHECK stays relaxed to "valid shares that sum to 1".

Full contract: [[features/session-budget-settings.tech]].

## Consequences

- **Easier:** the learner states new-word volume directly, and the planner no longer has to infer it.
- **Easier:** the two knobs compose with module exclusion; no new queue kinds for the main session, which still reads
  `practice_acquisition_min` / `practice_maintenance_min`.
- **Easier:** the learner's daily number stays true; extra work is explicitly optional.
- **Harder:** the session route gains a live tail (`tail`, `tail_queue`) and the end-of-session prompt; Tier C no longer
  runs a greedy loop on the practice side. Readers of the old Maintenance/Acquisition split (`rebalance_practice` callers
  and tests, `build_daily_session`) change together. The shares CHECK is relaxed because derived shares reach 1.0 / 0.0.
- **Harder:** the quota is high. 5 words a day at 30 minutes fits only about 1 to 2 words inside the main session on a typical
  day (see the worked example); most go to the tail, and the review forecast shows a month-on review load of about 12 min/day.
- **Constrained:** the ADR-009 bounds on maintenance share (0.15..0.50) and acquisition share (0.50..0.85) no longer govern the
  plan. Review share survives as the due-pressure sizing factor `review_share`.
- **Constrained (ANSWERED 2026-10-13):** a learner with no tests taken and no calibration miss receives no new words. This is
  accepted: new learners do calibration mode and some introductory tests (cold start 4A + 4B). See TASK-871 and TASK-873.
- **Behaviour change on rollout:** with the default `tests_and_review` scope the weekly counts and totals do not change;
  the vocabulary composition of each day does (reviews first, whole new words, leftover to tests), and learners gain a
  daily new-word quota about 7x the old rate (accepted).
- **Visible:** the daily total equals `daily_minutes`; the tail is shown as an offer. The cross-language tally counts
  `daily_minutes` only.
- **Supply-limited:** at about 3% exercise coverage most nominations starve, so the quota is often
  unmet. The shortfall is shown, starved nominations feed exercise generation, and the unused minutes return to tests.

## Alternatives Considered

- **New words as minutes.** Rejected: the cost of a word varies by language and learner, so a
  minute target gives an unstated word count. A word count is what the learner means; the minute
  estimate is derived and shown.
- **New words in an extra pool outside `daily_minutes` (this ADR's first version).** Superseded by revision (b): it made the
  day longer than the learner's number and needed a second pool, a second greedy loop and `extra_weekly_minutes`.
- **Scale tests up to absorb freed acquisition minutes (`scale_up_to_target`).** Removed in revision (b): it reshaped every
  learner's week (about +28% on the ZH template) for a gap that unused-minute return already closes.
- **New words first, reviews second.** Rejected: a fixed new-card quota ahead of reviews buries the learner; the governor and
  reviews-first ordering are the standard remedy.
- **Scope as a per-module flag** (each module marked in/out of the budget). Rejected: it multiplies
  states and complicates the redistribution maths. A two-value scope with flashcards and dual
  translation fixed as tests covers the real need.
- **Keep Maintenance/Acquisition shares live, ignore `new_words_per_day` for volume.** Rejected: leaves
  volume learner-invisible and keeps intake driven by a pool floor.
- **Drop the share columns.** Rejected: high blast radius across migrations and readers for no gain.
  They are kept and derived.
- **A `source` column on `user_vocabulary_knowledge` for calibration evidence.** Rejected: one row mixes sources per sense;
  provenance comes from the calibration ledger plus `bkt_applied_at`.
- **Frequency-based cold-start queue for new learners.** Not chosen (developer decision): calibration plus introductory tests
  cover the cold start.
- **Store the new-word cost in its own table.** Rejected for now in favour of a column on
  `dim_languages`, matching how the nightly job already stores observed estimates on dimension rows.

## Related Pages

- [[features/session-budget-settings]] — Plain-English feature page
- [[features/session-budget-settings.tech]] — Technical specification
- [[decisions/ADR-009-two-budget-tests-vs-practice]] — Amended by this ADR
- [[decisions/ADR-032-session-module-exclusion]] — Module exclusion this builds on
- [[decisions/ADR-011-per-language-independent-budgets]] — Per-language scope
- [[decisions/ADR-022-local-day-boundary]] — Local-midnight definition of "today"
- [[features/lookahead-preteaching]] — Queue B for new words
- [[features/calibration]] — Cold-start evidence (4B)
