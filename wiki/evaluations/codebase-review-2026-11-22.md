---
title: Codebase Review, Clean-up and Wiki Sync (2026-11-22 to 2026-11-23)
type: evaluation
status: complete
last_updated: 2026-11-23
open_questions:
  - "OPEN (TASK-1202): which dual-translation grader model pair is the production default, given that the two free defaults failed the gold set?"
  - "OPEN (TASK-1203): re-grade or only mark the 21 live grades made by unvalidated models?"
  - "OPEN (TASK-1206): accept ADR-061 (one transactional write per DT submission)?"
  - "OPEN (TASK-1207): accept ADR-062 (retire dt_card review cards, choose the /next window in SQL)?"
  - "OPEN (TASK-1208): accept ADR-063 (fat-seed as the bulk ladder path, nightly drain as the only top-up)?"
  - "ANSWERED 2026-11-23 (TASK-1210): the token economy is retired; see 'After the review (2026-11-23)'."
  - "ANSWERED 2026-11-23 (TASK-1221): the owner confirmed no outside client calls the API; 20 caller-less routes removed, /api/health, /api/tests/ and the admin vocab preview kept; see 'After the review (2026-11-23)'."
  - "OPEN (TASK-1224): keep or unschedule the nightly watchlist sweep?"
  - "ANSWERED 2026-11-23 (TASK-1227): Mystery and Listening Lab removed by hand; see 'After the review (2026-11-23)'."
  - "OPEN (TASK-1231): the wiki structure decisions (index header, log order, duplicate ADR numbers, off-schema directories, rpcs.tech rewrite, dangling lesson links)."
---

# Codebase Review, Clean-up and Wiki Sync (2026-11-22 to 2026-11-23)

## Purpose
Records the second whole-codebase review of LinguaLoop (the first is
[[evaluations/codebase-review-2026-11-13]]), the fixes that followed on branch
`claude/busy-hawking-pvgz8d`, and the wiki sync. The review ran from 2026-11-22 to 2026-11-23.
Nothing was deployed and no migration was applied; every database change is a file for the owner
([[tasklist/review-2026-11-22.tasks]]).

## Method
An orchestrated multi-agent review: a recon pass; eight area reviewers (routes, dual translation,
practice and ladder, LLM generation, frontend, database, scripts and skills, tests) plus two
wiki-lint agents; every medium or high finding re-checked by a separate verifier given only the
claim; ten fix packages in isolated worktrees, with a failing test first for each bug fix;
integration one package at a time with the gates run after each merge; an independent review of the
combined diff; one fix round; then the wiki sync in six batches.

About 190 findings were raised. Three were refuted and dropped: "the `/next` fallback is dead
code", "the difficulty badge class is undefined" and "the `is_admin` / `is_moderator` grants expose
something". About a dozen were corrected in their numbers.

## Results
Before = start of the review (commit `e985875`); after = the pushed tip of the branch.

| Measure | Before | After |
|---|---|---|
| Offline pytest | 5,805 passed, 1 failed, 1 collection error | 6,301 passed, 0 failed, 0 errors |
| ruff | 112 errors, non-blocking | 0 errors, blocking CI gate |
| ESLint warnings | 41 | 2 |
| Frontend unit tests | 743 | 846 |
| Database calls per practice answer | 12 (first attempt with a card), 10, 9, 5 | 2, 2, 1, 1 |
| DT error-card generation | 2 + 8 round trips per queued entry | constant 9 |
| DT submit: sequential reads before grading | 8 | 5 |
| Failing headless LLM call | 6 subprocess runs | 3 |
| Worst-case HTTP attempts per transient fault | 9 | 3 |
| New-word supply check | 2-3 queries | 1 |
| Fix packages alone | — | 143 files, +11,656 / -6,632 lines (services about -2,800, scripts about -1,100) |
| Tables and views documented | about 50 of 108 | 108 of 108 |
| Functions documented | about 104 of 214 | 214 of 214 |
| Routes documented | partial | all 137 |

Notes. The 6,301 count includes about 420 tests that arrived with the merged calibration branch.
The suite can no longer reach Supabase: it gives identical results with and without credentials and
in random order, except one order-dependent test that came from the merged branch (TASK-1219).
Production timings were not measured; the round-trip numbers come from analysis and fake-latency
runs. In the wiki, the six batches created 12 pages and updated 89 (dead repository paths fixed in
every page touched), and this record, the task file, the index, the log and the lint fixes came on
top.

## What changed, by area
- **Tests and CI:** the suite is offline and order-independent; ruff is a blocking gate; the test
  write path that reached live was closed (see Incident). See [[features/routes-tests-package.tech]].
- **Dual translation:** card generation batched (TASK-1003); the language filter in `cards.py`
  fixed (a zh drill had been built from a ja error); submit reads reduced. Specs updated in
  [[features/dual-translation.tech]] and [[features/dt-guided-self-repair.tech]]; proposed
  [[decisions/ADR-061-one-transactional-write-per-dt-submission]] and
  [[decisions/ADR-062-retire-dt-card-and-select-next-window-in-sql]].
- **Practice and vocabulary ladder:** `record_exercise_attempt` is the only attempt path (1-2
  database calls); the old multi-call path and its flag were deleted. See
  [[features/practice-package.tech]] and [[features/study-session-package.tech]].
- **LLM plumbing and generation:** fewer subprocess runs and HTTP retries on failure; bundle mode
  and the batch distractor flag removed; routing and judging follow-ups are left for the owner
  (TASK-1222). Proposed [[decisions/ADR-063-vocabulary-ladder-generation-paths]].
- **Frontend:** ESLint warnings 41 to 2, 103 more unit tests; dead code removed; heavier changes
  (page weight, CSP) not done. See [[features/web-package.tech]].
- **Scripts and dead code:** about 1,100 net lines removed from scripts and about 2,800 from
  services; deleted modules include parts of `model_arena`.
- **Migrations (files written, none applied):** the nine pending files in
  `migrations/PENDING-2026-11-23.md` (`drop_update_vocabulary_from_word_test_4arg`,
  `test_sentence_references_l1_script_escapes`, `prestudy_plan_inputs_definition_mode`,
  `skill_ratings_natural_key_unique`, `skill_ratings_writers_on_conflict`,
  `drop_get_quiz_distractors_batch`, `data_fix_dt_cards_cross_language_20261123`,
  `word_quiz_retake_fallback_hardened`, `word_upload_sweep_advisory_lock_hardened`); 13
  `baseline_*.sql` definitions for live functions that had no repository definition; superseded
  files moved to `migrations/archive/`. Order and checks: TASK-1201.
- **Merged branch:** `claude/beautiful-planck-0fftk4` (62 commits: vocabulary placement and the
  knowledge report) was merged; its specs are in [[features/vocab-placement.tech]] and the
  knowledge-report pages.
- **Evaluation:** the two free dual-translation grader models fail the gold set:
  [[evaluations/dt-free-grader-goldset-2026-11-23]].
- **Decisions recorded:** amendment of [[decisions/ADR-047-basic-word-knowledge-prior]] (repeated
  recent misses override "known"; owner kept the code), a note on
  [[decisions/ADR-028-exercise-gen-cost-under-1c]], and proposed ADR-061, ADR-062 and ADR-063.

### After the review (2026-11-23)
Owner decisions, each on its own branch and merged with the gates re-run. After the first three
(offline pytest 6,311 passed, 16 skipped, 0 failed; ruff clean; frontend 846 unit tests passed; 136 URL
rules) three more followed the same day; the final gates are in the last bullets below.
- **Token economy retired (TASK-1210, Done):** `GET /api/users/tokens`, the payments blueprint,
  `services/payment_service.py`, the token config, the `stripe` pin and the token fields in the
  login, config and health payloads are removed; 11 tests added, 8 removed (6,301 to 6,304). No SQL.
  The token pages are deprecated; a future design is proposed in [[features/token-economy]].
- **Mystery and Listening Lab removed (TASK-1227, Done):** done by hand, not by cherry-picking
  82a80de; `UNPLANNED_TEST_TYPES` and its 8 guard tests are gone (6,304 to 6,296). Nothing was
  live, so no migration.
- **FSRS review day at midnight Sydney time (TASK-1211, code done, SQL pending):** one app-wide review
  zone (`services/day_boundary.py` `REVIEW_TIMEZONE`, `Australia/Sydney`; first set as AEST/Brisbane, changed to Sydney by a later owner decision the same day) for the schedule and the
  `last_review` stamp; the per-learner local-day design is not pursued. 15 tests added (6,296 to
  6,311). `migrations/fsrs_review_day_aest.sql` (with a rollback) is group 10 of
  `migrations/PENDING-2026-11-23.md` and is applied together with the deploy.
- **Review day zone is Australia/Sydney (TASK-1211):** `REVIEW_TIMEZONE` is `Australia/Sydney`, so the
  review day follows Sydney daylight saving. The deploy window for
  `migrations/fsrs_review_day_aest.sql` is 00:00 to 13:00 UTC while daylight saving is in force (11:00 to
  midnight Sydney time) and 00:00 to 14:00 UTC otherwise; existing cards fall due up to 11 hours earlier
  during daylight saving. Branch `followup/fsrs-sydney`: 2 tests added (6,311 to 6,313). SQL still pending
  as group 10.
- **Unused API routes removed (TASK-1221, Done):** the owner confirmed no outside client calls the API,
  so 20 routes with no caller in the repository were removed with the code only they used, and the
  corpus blueprint is gone (136 to 116 URL rules). `/api/health`, `/api/tests/` and the admin vocabulary
  preview stay. 40 tests removed, 66 added (6,313 to 6,339). No SQL.
- **Scripts write only with `--apply` (TASK-1218, partly done):** 29 scripts and
  `exercise_stage_runner.py render` now dry-run unless given `--apply`, a guard test scans `scripts/`
  for the convention, six skills were updated; 155 tests added (6,339 to 6,494). Still open: the
  transactional classifier rebuild, the sentence-reference upload RPCs and `Corpuses/ingest_corpus.py`.
  Final gates after all three: offline pytest 6,494 passed, 16 skipped, 0 failed; ruff clean; frontend
  846 unit tests passed, `npm run check` 0 errors with 2 warnings; 116 URL rules.
- Recorded for the owner: the provider key will be funded and the validated DT grader models set
  (TASK-1202, still open; config defaults unchanged until then).

## Incident
On 2026-11-23 at 00:31 UTC a review agent ran the test suite with credentials present and the
network open. The suite's own write path wrote 38 test rows to the live database (26 `llm_calls`,
12 `generation_stage_timings`). The cause was closed in the code. Cleanup SQL was given to the
owner (TASK-1229).

## Not done
- Lazy-loading `/session` assets and CSP enforcement (TASK-1215, TASK-1216): no E2E safety net in
  the review environment.
- Database size reductions (TASK-1217), the rest of TASK-1218 (the convention and skill text are done).
  (Payments and the token economy, TASK-1210, FSRS dating, TASK-1211, unused routes, TASK-1221, and
  the `--apply` convention were decided or done on 2026-11-23: see "After the review".)
- Grader model choice, prompt text and judging logic: the owner's, validated against gold sets
  (TASK-1202, TASK-1205).
- Nothing was deployed and no migration was applied by the review.

## Related Pages
- [[tasklist/review-2026-11-22.tasks]]
- [[evaluations/codebase-review-2026-11-13]]
- [[evaluations/dt-free-grader-goldset-2026-11-23]]
- [[database/schema.tech]]
- [[api/rpcs.tech]]
- [[decisions/ADR-061-one-transactional-write-per-dt-submission]]
- [[decisions/ADR-062-retire-dt-card-and-select-next-window-in-sql]]
- [[decisions/ADR-063-vocabulary-ladder-generation-paths]]
