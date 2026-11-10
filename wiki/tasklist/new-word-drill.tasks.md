---
title: "New-Word Drill — Task Breakdown"
feature: new-word-drill
prose_page: ../features/new-word-drill.md
tech_page: ../features/new-word-drill.tech.md
total_tasks: 13
done: 13
---

# New-Word Drill — Task Breakdown

Draft for developer review (2026-11-09). All design questions answered 2026-11-09.

---

## TASK-912: Migration — intro columns, attempt source, quota default (LIVE-DB, approval)

**Status:** Done (live applied 2026-11-10)
**Feature:** new-word-drill
**Type:** infra
**Complexity:** S
**Depends On:** none

**Description:**
Add the intro stage state to `user_word_ladder`, allow `exercise_attempts.source = 'intro'`, and
raise the `new_words_per_day` default to 10 for new plans. The migration is written in the repo
and applied live only with approval.

**Acceptance Criteria:**
- [ ] `user_word_ladder` has `intro_stage smallint NULL CHECK 1–4`, `intro_due_date date NULL`, `intro_history jsonb NOT NULL DEFAULT '[]'`, and the partial index `idx_user_word_ladder_intro_due`.
- [ ] `exercise_attempts_source_check` accepts `'intro'` and every existing value.
- [ ] `user_study_plans.new_words_per_day` default is 10. Rows at 5 (the old default) become 10. Other values are unchanged.
- [ ] The migration is idempotent (re-run is a no-op).

**Technical Notes:** see the tech spec, "Migration". Keep the existing values of the source CHECK from `migrations/prestudy_workflow.sql`.

**Files to Create / Modify:**
- `migrations/new_word_drill.sql` — new
- `wiki/database/schema.tech.md` — new columns, CHECK, default

**Verification:** apply to a Supabase branch. `\d user_word_ladder` shows the columns. Insert a plan row without `new_words_per_day` and get 10.

---

## TASK-913: SQL — intro RPCs, ladder-pool exclusion, admission gate, demotion

**Status:** Done — built as word_state 'intro' + Python stage logic (see tech spec "Implementation notes")
**Feature:** new-word-drill
**Type:** feature
**Complexity:** L
**Depends On:** TASK-912

**Description:**
Write `intro_due_words` and `intro_complete_session`. Exclude intro rows from the
`get_practice_session` ladder pool. Teach `ladder_new_word_state` that intro words are servable
with intro content. Change the ring-2 demotion branch of `ladder_record_attempt` to send the word
back to intro stage 1 (full restart).

**Acceptance Criteria:**
- [ ] `intro_due_words` returns due words ordered stage DESC, due date, admission time.
- [ ] `intro_complete_session` advances, repeats or graduates exactly as the tech spec says. Due dates are completion date + 1 / +1 / +2. Replays with a stale `stage` change nothing.
- [ ] Graduation sets ring 2, `word_state = 'active'`, `form_recognition ≥ 0.55`, two form_recognition success dates, `review_due_at = now()`.
- [ ] No ladder exercise for an intro word appears in `get_practice_session` output.
- [ ] A ring-2 demotion sets `intro_stage = 1`, due tomorrow, clears form_recognition success dates and `gate_a`, keeps `intro_history`, and does not touch rings 3–4 behaviour.
- [ ] Both new functions are SECURITY DEFINER and EXECUTE-able only by `service_role`.

**Technical Notes:** the existing ladder functions live in `migrations/phase8_momentum_bands.sql` and its Phase 10 successors. Change them with CREATE OR REPLACE in the new migration file, copying the current live body first. Compare with `pg_get_functiondef` on the branch so no later patch is lost.

**Files to Create / Modify:**
- `migrations/new_word_drill_rpcs.sql` — new
- `tests/sql/new_word_drill_test.sql` — new
- `wiki/algorithms/vocabulary-ladder.tech.md`, `wiki/api/rpcs.tech.md` — document

**Verification:** run `tests/sql/new_word_drill_test.sql` on the branch. All assertions pass.

---

## TASK-914: Shared drill engine extracted from prestudy

**Status:** Done — engine in static/js/session/players/intro_drill.js; prestudy graders reused, not extracted
**Feature:** new-word-drill
**Type:** refactor
**Complexity:** M
**Depends On:** none

**Description:**
Move the item scheduling, requeue and typed-reading graders out of `static/js/prestudy/prestudy.js`
into `static/js/drill/engine.js`. Add the intro criterion mode: counted answers, the gap rule,
distinct formats, the cold-first bump, caps and spacers. Prestudy must behave exactly as before.

**Acceptance Criteria:**
- [ ] `createDrill` API as in the tech spec. Seeded rng gives deterministic order.
- [ ] Vitest covers: gap rule, distinct-format rule, idk never counts, cold miss raises target, cap stops a word as not passed, no word twice in a row, spacer insertion with 1–2 words, en format list without readings.
- [ ] Prestudy's existing vitest cases and a manual run of a ja prime are unchanged.
- [ ] Shared JSON fixtures in `tests/fixtures/intro_drill/` record attempts → expected `counted`/`passed` (used by TASK-915).

**Files to Create / Modify:**
- `static/js/drill/engine.js` — new
- `static/js/prestudy/prestudy.js` — import the engine and graders
- `tests/js/drill_engine.test.js`, `tests/fixtures/intro_drill/*.json` — new

**Verification:** `npx vitest run` passes. Open a ja prestudy page and complete a prime.

---

## TASK-915: Server — intro block builder and completion route

**Status:** Done
**Feature:** new-word-drill
**Type:** feature
**Complexity:** M
**Depends On:** TASK-913, TASK-914

**Description:**
Add `services/intro_drill.py` (`build_block`, `recount`, `complete`). Inject the
`intro_drill` item in `PracticeSessionService.get_session`. Add
`POST /api/practice/intro/complete`. The server recounts `passed` from the attempts using the
TASK-914 fixtures' rules.

**Acceptance Criteria:**
- [ ] The block has words, formats per stage and language, distractors, exercises by group, spacers when fewer than 3 words, and `est_minutes`.
- [ ] Fallbacks work: no reading, no sentence, no exercises.
- [ ] The route writes `exercise_attempts` (source `intro`), one knowledge-evidence row per word (`side_effects=False`), calls `intro_complete_session`, writes minutes to the ledger, and requests generation for words with fewer than 3 exercises.
- [ ] The route rejects senses not in intro at that stage and ignores the client `passed`. A replay is a no-op.
- [ ] pytest: recount matches every fixture, and route validation is covered.

**Files to Create / Modify:**
- `services/intro_drill.py` — new
- `services/practice_session_service.py` — `_inject_intro_block`
- `routes/practice.py` — new route
- `tests/test_intro_drill.py` — new

**Verification:** `pytest tests/test_intro_drill.py`. Call `GET /api/practice/session?mode=auto` for a test user with an intro row due and check the `intro_drill` item.

---

## TASK-916: Session player, practice-mode split, i18n

**Status:** Done
**Feature:** new-word-drill
**Type:** feature
**Complexity:** M
**Depends On:** TASK-915

**Description:**
Add `static/js/session/players/intro_drill.js` and register it. Render typed and MC items with
prestudy markup and ladder items with `exercise-renderers.js`. Post results, with a
`sessionStorage` retry. In practice mode, serve stage 2–4 words as review and hold stage-1 words
for the "Learn new words" prompt.

**Acceptance Criteria:**
- [ ] A block of 3 words runs end to end at phone width. Pips show counted / target.
- [ ] `splitPracticeQueue` splits the intro block by stage, with vitest cases.
- [ ] A failed POST is retried on next load and accepted once.
- [ ] New i18n keys exist in en/zh/ja/es. The i18n locale tests pass.

**Files to Create / Modify:**
- `static/js/session/players/intro_drill.js` — new
- `static/js/session/player_registry.js`, `static/js/session/tail.js`, `static/js/session/controller.js`
- `static/locales/*` (or the project's i18n files) — keys

**Verification:** Playwright at iPhone 13 size completes a block. `npx vitest run` passes. `eslint` is clean.

---

## TASK-917: Admission — intro rows and relaxed supply gate

**Status:** Done
**Feature:** new-word-drill
**Type:** feature
**Complexity:** S
**Depends On:** TASK-913

**Description:**
`_subscribe` (`practice_session_service.py` ~L2015) and `LadderService` row init (`ladder_service.py` ~L225)
create new rows with `intro_stage = 1`, `intro_due_date = today` (learner-local, `day_boundary`),
`review_due_at = NULL`. Admission accepts senses with intro content even when they have fewer than
3 exercises, and queues generation for them.

**Acceptance Criteria:**
- [ ] Newly admitted rows start in intro. Legacy rows are untouched.
- [ ] A sense with a gloss, a sentence and a reading (ja/zh), but 0 exercises, is admitted and appears in the next session's intro block.
- [ ] A generation request with reason `intro` is written for it.
- [ ] Quota arithmetic (`unstarted`, `started_today`) still holds. Covered by pytest.

**Files to Create / Modify:**
- `services/practice_session_service.py`, `services/vocabulary_ladder/ladder_service.py`
- `tests/test_practice_session_admission.py` (or the existing admission test file)

**Verification:** pytest. On a branch, admit 2 words for a test user and fetch the session.

---

## TASK-918: Prestudy words enter the drill

**Status:** Done
**Feature:** new-word-drill
**Type:** feature
**Complexity:** M
**Depends On:** TASK-917

**Description:**
After a prime is recorded, admit drilled senses through `admit_prestudy_words`. A sense that met
the stage-1 criterion enters at stage 2, due tomorrow, with a `source: 'prestudy'` history entry.
Otherwise it enters at stage 1, due today. When the prime drills more words than today's remaining
quota, show the overload notice: words that fit, words over, and extra minutes a day. The
choices are **Queue for later** (default: front of Queue A1) or **Add them all now**
(`POST /api/tests/<id>/prestudy/admit-overflow`). Skip `prestudy_followups` for admitted senses.

**Acceptance Criteria:**
- [ ] A ja prime of 6 words that all met the criterion leaves 6 rows at stage 2, due tomorrow, when the quota allows.
- [ ] With the quota exhausted, the evidence response returns `overflow` and nothing over quota is admitted. The notice shows fit / over / extra minutes. "Queue for later" (or leaving the page) nominates them. "Add them all now" admits them, and the route rejects ids not in the overflow list.
- [ ] Overload notice i18n keys exist in en/zh/ja/es.
- [ ] Existing ladder rows are left alone.
- [ ] `wiki/features/test-prestudy.md` reflects the reversed "never admits" rule.

**Files to Create / Modify:**
- `services/prestudy.py`, `routes/tests.py` (evidence route), `services/practice_session_service.py`
- `static/js/prestudy/prestudy.js` — send per-sense `met` in metrics
- `tests/test_prestudy_session.py`

**Verification:** pytest. Complete a prime on a branch and inspect `user_word_ladder`.

---

## TASK-919: Time estimate and review governor count the intro load

**Status:** Done — governor counts weighted drill reviews (live), forecast adds 10 items per word
**Feature:** new-word-drill
**Type:** feature
**Complexity:** S
**Depends On:** TASK-915

**Description:**
The session estimate, the review forecast and the review-load governor's backlog must include
intro words due: about 7 / 4 / 3 / 3 items per word for stages 1–4, times `review_item_seconds`.
Otherwise 10 new words a day silently adds 25–30 minutes.

**Acceptance Criteria:**
- [ ] The governor backlog includes due stage 2–4 intro words. pytest/SQL test with 30 due intro words moves the level from normal to reduced at the configured threshold.
- [ ] The Study Plan forecast shows intro minutes as part of reviews.
- [ ] Constants are mirrored in `config.py` and pinned by a test.

**Files to Create / Modify:**
- `migrations/review_governor.sql` (CREATE OR REPLACE in a new file), `services/study_plan_service.py`, `config.py`

**Verification:** SQL test and pytest pass. The Study Plan page shows the forecast for a seeded user.

---

## TASK-920: Feature flag and rollout (LIVE-DB, approval)

**Status:** Done — env flag NEW_WORD_DRILL_ENABLED (default on); live smoke test passed
**Feature:** new-word-drill
**Type:** infra
**Complexity:** S
**Depends On:** TASK-912, TASK-913, TASK-915, TASK-916, TASK-917, TASK-918, TASK-919

**Description:**
Gate admission-into-intro and block injection behind a global flag `new_word_drill`
(ADR-013 pattern). Apply the migrations live with approval, enable the flag, and smoke-test with the
developer account in ja.

**Acceptance Criteria:**
- [ ] Flag off: behaviour identical to today. Flag on: new admissions use intro.
- [ ] Live migrations applied with approval. The smoke test passes 3 words through stage 1.

**Files to Create / Modify:** `config.py` / feature-flag table, `wiki/log.md`

**Verification:** with the flag on, admit words, finish stage 1, and check stage 2 is due tomorrow.

---

## TASK-921: Measurement script and baseline

**Status:** Done — baseline [[evaluations/new-word-drill-baseline-2026-11-10]]; re-run at 30 days
**Feature:** new-word-drill
**Type:** test
**Complexity:** S
**Depends On:** TASK-920

**Description:**
Write `scripts/eval_new_word_drill.py` computing the tech spec's measurement set for pre-rollout
words (baseline) and intro words. Write the baseline now and re-run at 30 days.

**Acceptance Criteria:**
- [ ] The baseline page `wiki/evaluations/new-word-drill-baseline-<date>.md` exists.
- [ ] At 30 days, a comparison page reports Gate A / stress-test first-try pass, ring-2 demotion within 14 days, cold-recall correctness by stage, and minutes per graduated word.

**Files to Create / Modify:** `scripts/eval_new_word_drill.py`, `wiki/evaluations/…`

**Verification:** the script runs read-only against live and writes the page.

---

## TASK-922: Practice attempts move the ladder (ADR-041)

**Status:** Done (live function applied 2026-11-10)
**Feature:** new-word-drill · **Type:** bug · **Complexity:** M · **Depends On:** none

`ladder_apply_progress` + call from `record_attempt_with_updates`; `exercise_context` on
`POST /api/practice/attempt`; ring-2 restart hook moved here. Tests:
`tests/test_practice_ladder_progress.py`.

---

## TASK-923: Practice player runs gate and stress-test batteries (ADR-041)

**Status:** Done
**Feature:** new-word-drill · **Type:** feature · **Complexity:** M · **Depends On:** TASK-922

Markers open their battery in place; first-try answers with the battery context; results
submitted to the existing endpoints. Test: `tests/unit/practice-player-battery.test.js`.

---

## TASK-924: Drill cleanups — atomic commit, spacers, shared counting

**Status:** Done
**Feature:** new-word-drill · **Type:** refactor · **Complexity:** M · **Depends On:** TASK-915

`intro_commit_word` (live), spacer items for small drills, `countWord` shared with prestudy.

---
