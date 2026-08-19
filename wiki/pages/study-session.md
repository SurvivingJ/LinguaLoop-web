---
title: Daily Session Runner (`/session`)
type: page
status: complete
tech_page: study-session.tech.md
last_updated: 2026-08-07
open_questions:
  - "OPEN — which surfaces are deliberately outside the planner (listening_lab, mystery, dual_translation, flashcards)? Tracked as TASK-711."
  - "OPEN — day boundary is UTC midnight, which lands 07:00–09:00 local for the ZH/JA audience. Keep UTC or resolve through user_study_plans.timezone? Tracked as TASK-712."
---

# Daily Session Runner (`/session`)

## Purpose

One page that runs a learner's whole day of study — comprehension tests and vocabulary
practice together, in a sensible order, on a single screen — instead of making them
discover and stitch together separate surfaces themselves.

## User Story

As a learner, I open one link and just work. I don't want to decide *what* to study
today, or bounce between a tests page and a practice page. I want the app to hand me
today's items one at a time, mix them up so I'm not doing eight listening tests in a
row, and remember where I got to if I close the tab halfway through.

## How It Works

1. **Entry.** The learner arrives from the "Daily Session" navbar item (added by
   TASK-708, present on every authenticated page) or the primary CTA after picking a
   language. The runner reads the selected language from browser storage; with none
   set it redirects to language selection.

2. **Load.** The page asks the server for today's session. The server assembles one
   ordered queue containing today's test slots and today's practice time, split into
   chunks. Each item carries a flag saying whether it is already finished.

3. **Start or resume.** Before starting, the learner sees a one-line summary — how many
   tests, how much practice, how many items are left. If some items are already done the
   button reads "Resume session" instead of "Start session", and the runner jumps
   straight to the first unfinished item.

4. **Ordering.** The queue is deliberately mixed rather than grouped:
   - No two tests of the same type sit next to each other while a different type is
     still available.
   - Practice is broken into chunks of at most ten minutes and spread through the
     session rather than dumped at the end.
   - The order is stable — reloading the page mid-session produces the same order, so
     resuming is never disorienting.

5. **One item at a time.** Each item mounts its own player (listening, reading,
   dictation, pinyin, pitch accent, classifier drill, or practice) into the same stage
   area. A sticky progress header shows a row of dots — one per item — plus a
   done/total count and a progress bar.

6. **Finishing an item.** Completion is recorded on the server so it survives a reload.
   If saving fails the runner retries once, and if that also fails it tells the learner
   their progress may not have saved — but still lets them move on, because they did the
   work. A learner can also skip an item: skipping advances without marking it done, so
   it comes back on the next visit.

7. **Summary.** At the end the learner sees a done/total figure and a per-item list —
   each item's title, its type, and whether it was completed or skipped. Skipped items
   are visually distinct (faded, struck through, and amber rather than green).

8. **Nothing scheduled.** If today's queue is empty, the runner says so and points at
   the Study Plan and the tests browser instead of showing an empty session.

## Constraints & Edge Cases

- **Failure to load is recoverable.** If the session request fails, the error card
  offers a Retry button that re-runs the load. A second failure re-renders the same
  retryable card rather than leaving a dead page.
- **Double-submission.** A player can fire "complete" more than once (e.g. an
  impatient second click). The runner latches the first one so completion is never
  recorded twice — which would otherwise award ELO twice.
- **Resume is server-authoritative.** Completion lives on the server, not in the
  browser, so switching devices mid-day resumes correctly.
- **Skipping is not completing.** A skipped item stays incomplete and reappears; it is
  only marked visually so the learner can tell "I passed on this" from "I haven't got
  there yet".
- **No plan, or no week computed.** The runner still works: the server falls back to a
  legacy daily load rather than showing nothing.
- **Day boundary is UTC.** The day rolls over at UTC midnight regardless of where the
  learner is — see the open question above.

## Business Rules

- Every item in the queue is either a test slot or a practice chunk; there is no third
  kind.
- Practice chunks are capped at ten minutes each.
- An item already completed today is never re-served within the same day.
- The order for a given learner and day is deterministic — the same learner reloading
  gets the same sequence.
- Accessibility: the progress region announces politely as it changes, every dot is
  individually labelled with its type and state, and completed-vs-skipped is conveyed
  by more than colour alone.
- Every user-visible string is a translation key present in **all four** locales
  (en/es/zh/ja) — a missing key renders as the raw key string.

## Open Questions

- **OPEN** — Which surfaces are deliberately outside the daily planner? (TASK-711)
- **OPEN** — Keep the UTC day boundary or resolve it through the plan timezone? (TASK-712)

## Related Pages

- [[pages/study-session.tech]] — technical counterpart
- [[pages/pages-overview]] — full route map
- [[features/study-plans]] — what decides *what* is in today's queue
- [[features/practice-engine]] — what the practice chunks serve
- [[algorithms/daily-session-implementation-analysis]] — the audit (F1–F16) this runner was hardened against
- [[tasklist/archive/daily-session-hardening.tasks]] — TASK-700–713
