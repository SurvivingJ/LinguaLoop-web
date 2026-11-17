---
title: Test Prestudy — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./test-prestudy.md
last_updated: 2026-11-17
dependencies:
  - "services/prestudy.py (payload, drill rule, on-demand exercises, evidence, follow-ups, daily-session plan)"
  - "routes/tests/prestudy.py (GET payload, GET exercises on demand, POST session / evidence / admit-overflow / produce)"
  - "static/js/prestudy/prestudy.js (page, drill rule twin, on-demand exercise loader)"
  - "services/exercise_content/store.py (select_columns, hydrate; ADR-047)"
  - "exercises, tests, questions, dim_word_senses, user_vocabulary_knowledge, user_calibration_state, prestudy_sessions, prestudy_followups"
breaking_change_risk: medium
---

# Test Prestudy — Technical Specification

This page started with the ADR-047 change to how the page loads ladder exercises (2026-11-17,
TASK-989/993). The other endpoints are summarised from the prose page's "Implementation"
sections; their full behaviour is documented there and in the code docstrings.

## Architecture Overview

```
GET /test/<slug>/prestudy                       templates/test_prestudy.html + prestudy.js
  └─ GET /api/tests/<id>/prestudy               services.prestudy.build_prestudy_payload
       batch 1 (run_parallel): questions.sense_ids, ability_zipf, linked senses (words +
                               glosses), knowledge rows, has_exercises (row ids only)
       drill = drill_sense_ids(linked, senses, knowledge, ability) ∩ has_exercises
       batch 2 (run_parallel): question-only senses + their knowledge, drill exercise content
  └─ GET /api/tests/<id>/prestudy/exercises?sense_ids=…   on demand, ≤ 20 senses per call
  └─ POST …/prestudy/session | …/evidence | …/admit-overflow | …/produce   (unchanged)
```

Exercise content is loaded **only for the senses the word prime drills** (owner decision
2026-11-17, ADR-047 open question 1). This is a product change and applies in every
`EXERCISE_CONTENT_SOURCE` mode, `db` included. It cuts the request's content fan-out from every
linked sense (zh p90 126, max 306) to the drill set, which stays under the store's 160-sense
per-call cap.

## Database Impact

Reads only (see [[database/schema.tech]]):

- `exercises`: `has_exercises` reads `word_sense_id` of active rows of the prime-renderable
  types (`EXERCISE_FIELDS`) for the linked senses, paged (`fetch_all`, 200 senses per `in_`).
  Drill content: `store.select_columns('id, word_sense_id, exercise_type, {content},
  ladder_level')` — exactly `'id, word_sense_id, exercise_type, content, ladder_level'` in `db`
  mode, `content_version` instead of `content` in `storage` mode — for the drill senses only,
  then one `store.hydrate(rows, language_id=<test language>, db=db)` before `group_exercises`.
- `tests`, `questions`, `dim_word_senses` (+ `dim_vocabulary`), `user_vocabulary_knowledge`,
  `user_calibration_state`: unchanged.

No new table, column or index. Request count: two concurrent batches, as before; a test with
question-only senses calls `_load_senses` / `_load_knowledge` twice (once per batch).

## API / RPC Surface

### `GET /api/tests/<identifier>/prestudy`
- **Purpose:** everything the prestudy page needs for one test.
- **Auth:** `jwt_required`; the test must be active (`_find_test_for_prestudy`, slug then uuid).
- **Returns:** `{status, test, questions: [{sense_ids}], senses, knowledge, exercises,
  has_exercises, gloss_language_id, ability_zipf}`; with `?mode=followup` also
  `followup_sense_ids`, `attempt_id`, `primed_sense_ids`.
  - `exercises`: `{"<sense_id>": [{id, type, group, level, c}]}` for the **drill senses only**
    (at most `MAX_EXERCISES_PER_TYPE` = 2 per type, fields trimmed by `trim_exercise`).
  - `has_exercises`: sorted `[sense_id, …]` of every linked sense with at least one active row of
    a prime-renderable type. Built from row ids, never from content, so a Storage miss cannot
    hide a sense's exercises.
- **Errors:** 404 unknown/inactive test; 400 follow-up mode without an attempt.
- **Never returns** question text, choices or answers.

### `GET /api/tests/<identifier>/prestudy/exercises?sense_ids=11,12,…` (new, TASK-989)
- **Purpose:** exercises of words that joined the drill set on the page ("I don't know this"),
  or of drill words the payload lacked.
- **Arguments:** `sense_ids` — comma-separated, deduplicated in order. 400 unless 1–20 distinct
  tokens (`prestudy.MAX_ON_DEMAND_SENSES` = 20, checked before any DB read). Tokens that are not
  ASCII digits, or not in `tests.vocab_sense_ids`, are silently ignored. Question-only senses are
  not served.
- **Auth:** `jwt_required` + the same active-test lookup as the payload route; 404 for an
  unknown test.
- **Returns:** `{status, sense_ids: [served ids], exercises: {"<sid>": [{id, type, group, level,
  c}]}}` — the payload's `exercises` shape. A served sense with no usable exercise has no key.
- **Side effects:** none. It never queues generation.
- **Service:** `prestudy.on_demand_exercises(db, test, ids) -> (served, exercises)`, which uses the
  same `_load_exercises` (select + one hydrate) as the payload.

### Other prestudy endpoints (unchanged by ADR-047)
`POST …/prestudy/session` (opens a `prestudy_sessions` row), `POST …/prestudy/evidence` (word-test
evidence, exercise attempts with `source='prestudy'`, follow-ups, generation requests),
`POST …/prestudy/admit-overflow`, `POST …/prestudy/produce`. See [[features/test-prestudy]]
"Implementation" and "Workflow completed".

## The drill rule (one rule, two implementations)

`services/prestudy.py::drill_sense_ids(sense_ids, senses, knowledge, ability) -> list[int]` is the
server rule; `static/js/prestudy/prestudy.js` `isDrilled(p, added)` / `drillSenseIds(payload)` is
its client twin. A linked sense is drilled when:

1. it has an entry in the payload's `senses` map (the page ignores a linked sense without one), and
2. its p_known is below `DRILL_MAX_P = 0.75`: the learner's `user_vocabulary_knowledge.p_known`
   when there is a row, otherwise the Zipf prior
   `1 / (1 + exp(-(1.5 × (freq − ability) + ln(0.85/0.15))))`, or 0.3 when `freq` is null.

The client also drills every word the learner added. Both sides replay
`tests/unit/fixtures/prestudy-drill-rule.json`; a Python test checks that the JS constants
(`DRILL_MAX_P`, `MAX_FETCH_SENSES`) match the Python ones. `plan_for_tests` (daily-session plan)
uses the same function. The payload's drill set is `drill_sense_ids(...) ∩ has_exercises`.

## Component Specification (prestudy.js)

- `S.hasEx`: a `Set` of sense ids (strings) from `has_exercises`. An older server without the
  field: the keys of `exercises` are used and nothing is fetched.
- `createExerciseLoader({exercises, hasExercises, usable, url, fetchImpl, batchSize})` (also on
  `window.LinguaPrestudy`):
  - `ensure(sids)`: one GET per batch of up to `MAX_FETCH_SENSES` (20) senses that are in
    `hasExercises`, not loaded, not pending and not failed; never two requests in flight for one
    sense; resolves (never rejects) when every request carrying one of `sids` has settled.
  - A failed request marks its senses failed: no exercises, no retry, one `console.warn`. The
    word stays on the no-exercise path for this visit.
  - `waiting(sids)`, `isPending`, `isLoaded`, `hasFailed`.
- Triggers: "I don't know this" (`toggleAdded`) starts the fetch at once; `buildQuiz` waits for
  pending fetches (body shows `common.loading`, Next disabled); a word added mid-prime is
  appended once its exercises arrive. At page load, drill words in `has_exercises` but missing
  from `exercises` are fetched in the background. The light prime and the follow-up never fetch
  (no exercise stages).
- Counts: the minute estimate and the "has ladder exercises" checks read `has_exercises`. The
  word-list chip shows only for `has_exercises` words and its number is the count of usable
  exercises actually loaded (no chip while a fetch is in flight or after it failed).

## Generation requests

`request_generation` still decides from `senses_with_exercises` (DB row ids). A hydration miss,
or a word whose exercises were never loaded on the page, therefore never queues generation
(tested).

## Key Architectural Decisions

1. **Decision:** load content for the drill set only, plus `has_exercises` for every linked
   sense, with an on-demand endpoint for words added later (owner, 2026-11-17).
   - **Rationale:** prestudy was the largest content fan-out (all linked senses); after ADR-047
     each sense is a Storage file, and the zh p90 test would hit the 160-sense per-call cap.
   - **Alternatives rejected:** hydrate every linked sense and raise the cap (slow cold page,
     still capped); paginate the word list (the prime needs exercises for words the learner
     adds anywhere in the passage).
2. **Decision:** the drill rule lives in one Python function with a JS twin tested against a
   shared fixture.
   - **Rationale:** a drift between the two would leave drill words without exercises (the page
     then fetches them on demand, so the failure is slow, not broken).

See [[decisions/ADR-047-exercise-content-in-storage]] (open question 1).

## Security Considerations

- The on-demand endpoint serves only the test's own linked senses, at most 20 per call, and
  rejects an empty or oversized list before any DB read. It returns trimmed exercise fields, the
  same as the payload; answer keys of ladder exercises were already sent to the page (the prime
  grades on the client).
- Scored question text, choices and answers are never sent.

## Testing Strategy

- `tests/test_exercise_content_prestudy_reader.py`: drill-rule boundaries, payload holds content
  for drill senses only and `has_exercises` for all, endpoint filters foreign ids and caps at 20,
  storage mode hydrates once with the language, `db` select string unchanged, generation never
  queued from a hydration miss.
- `tests/unit/prestudy-ondemand.test.js` (vitest): loader batching, dedupe, failure path; the
  shared drill-rule fixture.
- `tests/test_exercise_content_integration.py`: the payload and the on-demand endpoint in
  db / shadow / storage mode equal the `db` payload; in storage mode only the drill senses'
  files are read.
- Existing: `tests/test_prestudy.py`, `test_prestudy_session.py`, `test_pagination.py`,
  `test_latency_caching.py` (unchanged).
- TASK-997 measures the prestudy latency (a zh test with ≥ 100 linked senses) on `storage`.

## Related Pages

- [[features/test-prestudy]] — prose page
- [[decisions/ADR-047-exercise-content-in-storage]] — content in Storage; open question 1
- [[tasklist/exercise-content-storage.tasks]] — TASK-989, TASK-993
- [[api/rpcs.tech]] · [[database/schema.tech]]
