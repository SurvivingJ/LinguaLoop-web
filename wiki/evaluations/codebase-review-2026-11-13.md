---
title: Codebase Review and Refactor Swarm (2026-11-13)
type: evaluation
status: complete
last_updated: 2026-11-14
open_questions:
  - "Which of the 12 new migration files should be applied live, and in what order?"
  - "Is the app hosted in the same region as the Supabase project (ap-southeast-2)?"
  - "Should /test/<slug>?type=dictation keep redirecting to the dedicated dictation page?"
  - "Which vocabulary-ladder generation pipeline is authoritative (default, bundle, stage runner, fat-seed)?"
---

# Codebase Review and Refactor Swarm (2026-11-13)

## Purpose
Records a five-criterion review (security, latency, minimal lines, modularity, efficiency) of the
Flask app, frontend, database layer and scripts, and the refactor that followed on branch
`claude/lucid-volta-gu0g2l`. Nothing was applied to the live database.

## Method
Eight read-only reviewers, one per area; headline findings re-checked against the code. Then
fourteen implementation agents in two waves, each in its own git worktree with a disjoint file
set, merged one at a time behind the full test suite.

## Results
| Measure | Before | After |
|---|---|---|
| Python tests passing | 4,084 (4 failing) | 4,432 (1 failing, stale) |
| JS unit tests passing | 342 | 431 |
| Lines, excluding data | — | 30,451 added, 39,651 removed (net −9,200) |
| Template lines | ~13,900 | ~2,700 (inline JS/CSS moved to versioned files) |
| Tracked generated data | ~420 MB | untracked |
| Rate limits / body cap | none | Flask-Limiter by endpoint; 1 MB cap |
| CI on push | none | pytest, vitest, eslint |

Sequential database round trips (by analysis or fake-latency measurement, not production):
practice answer 11–13 → 4–5; study-plan GET 6–7 → 2; prestudy GET 8 → 5; daily session 8–9 → 5–6.

## What changed, by area
- **Platform:** gthread workers; app built once per worker; per-thread Supabase client (a shared
  client failed 1–4% of calls under 8 threads); 10 s database timeout; security headers; central
  error handler; `web/` package holds scheduler, pages, errors, rate limits.
- **Security:** logout revokes the session; generic auth errors; word-list quotas and validation;
  SSRF guard on corpus ingest; optional local JWT verification (`SUPABASE_JWT_SECRET`).
- **Routes:** `routes/tests` is a package; logic moved to `services/attempts.py`,
  `services/study_session/`, `services/study_plan_settings.py`, `services/practice/`; one
  `get_db()` accessor; one drill implementation for classifier and counter.
- **Frontend:** session advances immediately and saves in the background; next item prefetched;
  import map with hashed module URLs; standalone test and drill pages are shells that mount the
  session players; auth renewal budget 6 s with proactive refresh.
- **Services and scripts:** retired exercise-generation stack removed (~3,000 lines); judges share
  one runner; 37 applied one-off scripts removed (~10,000 lines); `scripts/_common.py`.
- **Migrations (files only, all need approval to apply):** hardened submission RPC files;
  `security_tests_service_role_only`, `security_calibration_answer_keys`,
  `security_watchlist_reports_no_client_writes`, `perf_attempt_history_indexes`,
  `log_retention_purge`, `process_test_submission_set_based_grading`,
  `get_quiz_distractors_sample_ids_first`, `get_quiz_distractors_batch`,
  `record_exercise_attempt`, `drop_legacy_process_test_submission_overloads`.

## Not done
- Payments and dual-translation grading were left untouched at the developer's request.
- Git history was not rewritten (shallow clone; needs a force-push to `main`).
- The four ladder generation pipelines were not collapsed (a quality decision; see
  [[evaluations/exercise-gen-phase2-2026-10]]).
- No migration was applied; Python paths that need new database objects are behind flags that
  default to off (`PRACTICE_ATTEMPT_RPC_ENABLED`, `QUIZ_DISTRACTORS_BATCH`).
- Spec pages under `features/`, `api/` and `database/` have not been updated for the moved code.

## Related Pages
- [[features/security-hardening]]
- [[evaluations/latency-2026-11-11]]
- [[database/schema.tech]]
- [[api/rpcs.tech]]
