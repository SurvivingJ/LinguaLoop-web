---
title: "Test Generation — Fail-Closed Judging — Task Breakdown"
feature: comprehension-tests
prose_page: ../features/comprehension-tests.md
tech_page: ../features/comprehension-tests.tech.md
total_tasks: 4
done: 4
---

# Test Generation — Fail-Closed Judging — Task Breakdown

`services/exercise_generation/judges/base.py` carries a fail-closed guard built after two
total outages: a delisted OpenRouter model slug made every judge return `safe_accept()` and
a whole batch shipped unjudged. Inside `batch_mode()` a judge *outage* raises
`JudgeUnavailable` and aborts the batch instead of rubber-stamping.

Today that guard is used by `scripts/run_generation_batch.py`, `judges/particle.py`,
`judges/relation.py`, `services/model_health.py`, `services/vocabulary_ladder/asset_pipeline.py`
— **exercise generation only**. Test generation does not use it anywhere (verified by grep,
2026-08-21). A bulk test run with a dead slug or a missing prompt row writes unjudged
questions to `questions` with nothing louder than a log warning.

These four tasks close that, and then measure a 20-test run so a large run has a
go/no-go number.

---

## TASK-727: Wrap both test-generation batch entry points in `batch_mode()`

**Status:** [x] Done (2026-08-21)
**Feature:** comprehension-tests
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
Wire the fail-closed guard into test generation at the two orchestrator methods every
batch caller funnels through, rather than at each of the four caller modules. Wrapping
the orchestrator means a fifth caller cannot forget, and the callers stay ignorant of the
judging contract.

Call sites verified 2026-08-21:

| Module | Line | Method |
|--------|------|--------|
| `routes/admin_local.py` | 1074 | `run_batch()` |
| `routes/admin_local.py` | 1085 | `run()` |
| `scripts/run_test_generation_cli.py` | 131 | `run_batch()` |
| `scripts/run_test_generation.py` | 272 | `run()` (via `run_with_debug_wrapper`) |
| `services/ai_service.py` | 1 | none — a `# LEGACY:` pointer comment only |

**Acceptance Criteria:**
- [x] `TestGenerationOrchestrator.run()` executes its whole body inside `batch_mode()`.
- [x] `TestGenerationOrchestrator.run_batch()` executes its whole body inside `batch_mode()`.
- [x] No caller module is modified — the guard is entered exactly twice in the codebase.
- [x] The serve path is untouched: no change to any judge module's default behaviour, and
      nothing on a learner-facing request path enters `batch_mode()`.
- [x] A test asserts `is_batch_mode()` is True inside `_generate_test` when reached via
      `run_batch()`, and False when `_generate_test` is called directly (the serve-shaped call).

**Technical Notes:**
Import at module top: `from services.exercise_generation.judges.base import batch_mode`.
`batch_mode()` is a re-entrant context manager and restores the previous value on exit, so
nesting (`run()` -> `_process_queue_item` -> anything already in a batch) is safe.

The wrap must sit *outside* each method's existing outer `try`, or the outer `except
Exception` catches `JudgeUnavailable` before the context manager can matter. Cleanest is a
thin public method that opens the context and delegates to a private `_run_impl` /
`_run_batch_impl` holding the current body — but see TASK-728: the outer handlers must
re-raise regardless, so a plain `with` at the top of the body is also acceptable provided
728 lands with it.

**Thread fan-out (item 4 of the brief) — audited, no code change required.**
Grepping `services/test_generation/` for `ThreadPoolExecutor`, `concurrent.futures`,
`as_completed` and `threading` returns **zero** hits: the test-gen pipeline is fully serial.
Vocabulary enrichment (`services/vocabulary/sense_generator.py`, reached from
`_generate_vocabulary`) is also serial and calls no judges. So no
`BatchModeThreadPoolExecutor` / `bind_batch_mode` is needed today. Record this, because the
moment anyone parallelises the generation loop the thread-local flag silently reverts to
fail-open on the workers — the original outage wearing a different hat.

**Files to Create / Modify:**
- `services/test_generation/orchestrator.py` — wrap `run()` and `run_batch()`.
- `tests/test_test_gen_fail_closed.py` — batch-mode-reaches-the-generator assertions.

**Verification:**
`PYTHONPATH=. python -m pytest tests/test_test_gen_fail_closed.py -q`

---

## TASK-728: Audit the orchestrator's exception handlers so `JudgeUnavailable` propagates

**Status:** [x] Done (2026-08-21)
**Feature:** comprehension-tests
**Type:** bug
**Complexity:** M (3-8h)
**Depends On:** TASK-727

**Description:**
This is the actual work; TASK-727 is two lines. `JudgeUnavailable` is an ordinary
`RuntimeError` and `orchestrator.py` has 15 `except Exception` blocks, five of them
wrapped around the generation loop. Left alone they swallow the abort and degrade it into
"that one test quietly failed to generate" — *quieter* than the bug it replaces, and
exactly the failure mode `base.py`'s own module docstring warns about.

Handlers classified 2026-08-21 (line numbers pre-edit):

**On the judge path — must re-raise `JudgeUnavailable`:**

| Line | Scope | Current behaviour |
|------|-------|-------------------|
| 253 | `run()` per queue item | logs, `tests_failed += 1`, `mark_queue_failed`, next item |
| 262 | `run()` outer | logs, sets `metrics.error_message`, returns metrics |
| 333 | `_process_queue_item` per difficulty | logs, continues with other difficulties |
| 1241 | `run_batch()` per test | logs, `tests_failed += 1`, next slot |
| 1277 | `run_batch()` outer | logs, sets `metrics.error_message`, returns metrics |

**Not on the judge path — leave exactly as they are:**
110 (`_write_review_queue_rows`), 451 (difficulty scorer), 477 (title generation),
643 (pinyin payload), 792 + 827 (`_generate_vocabulary` / `_record_vocab_outcome`),
1019 (`APIError` 23505 vocab insert race), 1055 (`_finalize` metrics persist),
1264 (`mark_queue_completed`). None of these can reach a judge — verified by call graph,
and `services/vocabulary/sense_generator.py` contains no judge import.

**Acceptance Criteria:**
- [x] All five judge-path handlers re-raise `JudgeUnavailable` before their generic
      handling, so it reaches the caller of `run()` / `run_batch()` unswallowed.
- [x] The ten non-judge handlers are unchanged.
- [x] `run_batch()` aborting on `JudgeUnavailable` does **not** mark queue items complete
      and does not report the run as a normal finish.
- [x] `question_generator._apply_judges`'s docstring no longer claims "this method never
      raises and never blocks the pipeline" — it now documents that a judge *outage* inside
      a batch raises `JudgeUnavailable` by design, while `accept_item` gaps still never do.
- [x] The comment above the judge gate in `_generate_validated_question` ("Failure mode:
      safe_accept() — judges never block on internal error") is corrected the same way.
- [x] `_apply_judges`'s caller is confirmed not to swallow it: `_generate_validated_question`
      calls `_apply_judges` *outside* the `try` that guards `_generate_single_question`
      (verified — line 244's handler covers generation only). Add a test pinning that, so a
      later refactor that widens the `try` is caught.

**Technical Notes:**
Idiom, at the top of each of the five handlers:

```python
except JudgeUnavailable:
    # A judge outage inside a batch. Aborting loudly is the whole point of
    # batch_mode() — swallowing it here would be quieter than the unjudged
    # content it exists to prevent.
    raise
except Exception as e:
    ...
```

Import `JudgeUnavailable` alongside `batch_mode` at module top. Do not catch-and-wrap: the
message already names the remedy (check `prompt_templates` for an active row with a live
model slug).

**Files to Create / Modify:**
- `services/test_generation/orchestrator.py` — five `except JudgeUnavailable: raise` clauses.
- `services/test_generation/agents/question_generator.py` — docstring + inline comment fixes.
- `tests/test_test_gen_fail_closed.py` — propagation-through-the-loop tests.

**Verification:**
`PYTHONPATH=. python -m pytest tests/ -q` — baseline 1869 passed, 3 skipped.

---

## TASK-729: Prove the guard actually fires

**Status:** [x] Done (2026-08-21)
**Feature:** comprehension-tests
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** TASK-728

**Description:**
House rule from hard experience: four guardrails in this codebase were silently inert for
months because nobody checked one actually fired (NULL `cost_usd` disarming every budget
ceiling; a band-check RPC signature that never existed; an `asset_type` CHECK rejecting all
typed-LLM assets; a per-type audio-field mismatch). A test that only proves the happy path
is not evidence. Make the failure real: an unresolvable judge template/model inside a batch
must abort the batch **and write no questions**.

**Acceptance Criteria:**
- [x] **Fires:** with the distractor-plausibility judge's template unresolvable, `run_batch()`
      raises `JudgeUnavailable` and the fake db records **zero** `questions` inserts and zero
      `tests` inserts for the aborted slot.
- [x] Same assertion for the answer-entailment judge, since they are separate call sites in
      `_apply_judges` and only one of them is exercised first.
- [x] **Serve path unbroken:** the identical judge outage, called *outside* `batch_mode()`,
      still returns `safe_accept()` and still produces a question — a learner waiting on a
      session must keep failing open.
- [x] **`accept_item` unaffected:** a healthy judge response with one unparseable/missing
      per-distractor rating does **not** abort a batch. Assert the batch completes and the
      question survives.
- [x] **Loop does not swallow:** a `JudgeUnavailable` raised at the innermost judge call
      escapes `_generate_validated_question`'s retry loop, `generate_questions`,
      `_generate_test`, `_process_queue_item` and `run_batch`'s per-slot handler — pinned as
      an explicit test, not implied by the end-to-end one.
- [x] No network and no live DB: judges are patched / the template loader is stubbed.

**Technical Notes:**
Mirror `tests/test_batch_mode_propagation.py` for style and framing. The cheapest true
outage to simulate is the one that caused the real incidents: make the judge's
`prompt_templates` lookup raise, which both judges funnel into
`safe_accept(f'template load error: {exc}')` — the exact chokepoint `guard_fail_open`
sits on (`answer_entailment.py:131`, `distractor_plausibility.py:182`).

Judges only run at `difficulty > 2` (`run_judges = difficulty > 2` in `_generate_test`), so
the fixture batch must use difficulty >= 3 or the guard is never reached and the test proves
nothing — this is precisely the "silently inert" trap.

**Files to Create / Modify:**
- `tests/test_test_gen_fail_closed.py` — the whole suite above.

**Verification:**
`PYTHONPATH=. python -m pytest tests/test_test_gen_fail_closed.py -q`, then the full suite.
Additionally: temporarily revert one `except JudgeUnavailable: raise` and confirm the suite
goes **red** — a guard test that passes against the unfixed code is not a guard test.

---

## TASK-730: Measure a 20-test run — cost and wall clock

**Status:** [x] Done (2026-08-21)
**Feature:** comprehension-tests
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** TASK-729

**Description:**
With the guard live, run 20 tests end-to-end and report the two numbers that decide whether
a large run is affordable: **total cost** and **wall clock**, both per-test and in total.
File the result as an evaluation page so the next capacity question has a baseline.

**Acceptance Criteria:**
- [x] 20 tests generated end-to-end through `run_batch()` (not dry-run) with the guard active.
- [x] Cost reported from `llm_calls` where `pipeline = 'test_gen'`, summed on `cost_usd`,
      broken down by `task_name` so the judge share is visible separately from generation.
- [x] Wall clock reported total and per-test, with the dominant stage identified.
- [x] Extrapolation to a large run (per 100 and per 1000 tests) stated for both numbers.
- [x] Any run-level shortfall (vocab shortfalls, tests_failed, judge rejects) reported
      alongside — a cost number without a yield number is not a go/no-go.
- [x] Evaluation page filed and linked from `index.md`.

**Technical Notes:**
**Namespace trap:** judges log to `llm_calls` under `judge_<name>` (e.g.
`judge_distractor_plausibility`), which is *not* their `prompt_templates` task_name.
Querying the prompt-template name shows zero rows for a perfectly healthy judge and would
understate the judge share of spend to nothing.

Bound the query by a timestamp window taken immediately before the run starts, so a
concurrent batch in another workstream cannot contaminate the total.

**Do not activate `test_distractor_plausibility` v7.** Those rows are staged
`is_active = false` on purpose, pending TASK-726's gold set. Unrelated to this work; the
measurement runs against the live judge stack.

**Files to Create / Modify:**
- `wiki/evaluations/test-gen-20-run-2026-08-21.md` — the measurement.
- `wiki/index.md`, `wiki/log.md` — links and log entry.

**Verification:**
The evaluation page states $/test and min/test with the SQL that produced them.

**Result (2026-08-21):** 20/20 generated, 0 failed, 0 vocab shortfalls. **$0.175 total
($0.00875/test)**, **3,532 s (2.9 min/test)**. Judges 38.2% of spend; vocabulary enrichment
82% of wall clock but 16% of spend. Extrapolates to ~$8.75 / ~49 h per 1,000 tests — spend
is a non-issue at any plausible scale, wall clock is the constraint. Two extra query traps
found beyond the documented one: `vocab_senses` is a separate pipeline (16% of the bill
invisible to a `test_gen` filter), and half the `judge_%` rows are zero-cost verdict logs,
so `count(*)` overstates judge calls 2x. Full write-up:
[[evaluations/test-gen-20-run-2026-08-21]].

---
