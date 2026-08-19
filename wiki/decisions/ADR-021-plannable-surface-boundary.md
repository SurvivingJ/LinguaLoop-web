---
title: "ADR-021: Plannable-surface boundary — which surfaces the daily planner owns"
status: accepted
date: 2026-08-07
---

# ADR-021: Plannable-surface boundary — which surfaces the daily planner owns

## Context

The Study Plan orchestrator ([[decisions/ADR-008-study-plan-orchestration-layer]]) budgets a
learner's week across two budgets — Tests and Practice ([[decisions/ADR-009-two-budget-tests-vs-practice]])
— and `build_daily_session` resolves that into a daily queue served by `/session`
([[pages/study-session]]).

Finding **F11** of [[algorithms/daily-session-implementation-analysis.tech]] recorded that no page
stated *which* surfaces are deliberately outside the planner. Four sat in an undefined middle:
`listening_lab`, `mystery`, `dual_translation`, `flashcards`. The ambiguity was not merely
documentary — it was half-modelled in the schema:

- `listening_lab` and `mystery` **already exist as `dim_test_types.type_code` rows**, so they look
  plannable to anything reading that table, yet no template schedules them.
- `dual_translation` and `flashcards` are **not** `dim_test_types` rows at all — they are separate
  surfaces with their own routes, so they cannot be expressed in `target_counts` as it stands.

Consequence of leaving it undecided: a learner's flashcard reviews and dual-translation work are
invisible to the weekly budget, so the plan systematically **under-counts actual study load** and
schedules on top of time the learner has already spent.

A related sub-question was bundled into TASK-711: whether dictation's 80-word transcript cap should
scale with tier. That is decided here only insofar as it affects time budgeting; the content change
itself is tracked as an implementation task.

## Decision

**In the planner:**

| Surface | In planner? | Rationale |
|---|---|---|
| `listening` | **Yes** (already) | Core test skill; ELO-rated. |
| `reading` | **Yes** (already) | Core test skill; ELO-rated. |
| `dictation` | **Yes** (already) | ELO-rated; feeds per-word BKT. |
| `pinyin` | **Yes** (already) | ZH-only; ELO-rated. |
| `pitch_accent` | **Yes** (already) | JA-only; ELO-rated. |
| `classifier_drill` | **Yes** (already) | ZH-only; sentinel-test ELO pattern. |
| Practice (acq + maint) | **Yes** (already) | The Practice budget; chunked ≤10 min. |
| **`flashcards`** | **Yes — to be added** | FSRS reviews are due-driven, recurring and inherently daily. This is the single largest source of under-counted time: reviews happen every day whether the plan knows or not. |
| **`dual_translation`** | **Yes — to be added** | Graded, effortful production work that competes directly with test time. Excluding it makes the Tests budget dishonest. |
| `listening_lab` | **No — deliberately outside** | Long-form, exploratory, self-directed. Forcing it into a daily minute budget fights its design. Its `dim_test_types` row is a modelling artefact, not an intent to schedule it. |
| `mystery` | **No — deliberately outside** | 5-scene gated narrative; session length is set by the story, not by a budget. Same artefact caveat as `listening_lab`. |

**Dictation transcript cap:** the 80-word cap **scales with tier** rather than staying flat.

## Consequences

**Easier:**
- The weekly budget becomes an honest account of study time once flashcards and DT are counted.
- `listening_lab` and `mystery` have a stated reason to be outside the planner, so a future reader
  does not "fix" their absence as a bug — and neither does a future agent.

**Harder / newly constrained:**
- **`flashcards` and `dual_translation` are not `dim_test_types` rows.** Adding them needs a
  plannable-kind concept broader than "test type", or new type codes plus a way to resolve them to
  something that is not an ELO-rated `tests` row. This is the bulk of the implementation cost.
- **Time estimates must be seeded, or they silently default.** `test_time_estimate(p_skill text)`
  COALESCEs `dim_test_types.expected_minutes_p50` (currently **NULL for all 12 type codes**) onto
  hardcoded per-skill constants, with a catch-all **`ELSE 5.0`**. A new surface that is not added to
  that CASE will be budgeted at 5 minutes per item without any error — a silent wrong answer, the
  same failure shape as F3's silent hydration shortfall.
- **Completion signalling.** Every planned surface needs a completion signal reaching
  `record_session_progress` (or an equivalent), or its counters never advance — the exact defect
  TASK-701/F2 fixed for practice.
- **Tier-scaled dictation breaks a uniform time estimate.** `test_time_estimate('dictation')`
  returns a single scalar (6.0). Once transcript length varies by tier, that scalar is wrong at both
  ends and the estimate must become tier-aware, or daily budgets will drift for advanced learners.
- Excluding `listening_lab`/`mystery` means time spent there stays uncounted — accepted knowingly.

## Alternatives Considered

- **Keep all four outside (status quo, documented).** Cheapest and lowest-risk, but preserves the
  under-count. Rejected: flashcards in particular are daily by construction, so the gap is
  systematic rather than occasional.
- **Bring all four in.** Maximally honest budget, but forces long-form exploratory content into a
  minute budget it was not designed for, and multiplies the plannable-kind work. Rejected.
- **Keep the flat 80-word dictation cap.** Predictable per-item duration, which suits a
  minute-budgeted planner. Rejected in favour of challenge progression.
- **Cap dictation by target *time* rather than word count.** Arguably the best fit for a
  minute-budgeted planner, since duration becomes the controlled variable. Rejected for now as the
  most expensive option (needs a per-tier, per-language duration model); revisit if tier-scaled word
  counts prove hard to budget.

## Implementation

Filed as TASK-714 (flashcards + dual_translation as plannable surfaces) and TASK-715 (tier-scaled
dictation cap) in [[tasklist/archive/daily-session-hardening.tasks]]. Resolves finding **F11**.

## Related Pages

- [[features/study-plans.tech]] — the surface boundary table lives here as the canonical reference
- [[algorithms/daily-session-implementation-analysis.tech]] — F11
- [[features/flashcards]], [[features/dual-translation]], [[features/dictation]]
- [[decisions/ADR-008-study-plan-orchestration-layer]], [[decisions/ADR-009-two-budget-tests-vs-practice]]
