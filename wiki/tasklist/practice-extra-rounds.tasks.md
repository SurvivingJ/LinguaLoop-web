---
title: "Practice Extra Rounds — Task Breakdown"
feature: practice-extra-rounds
prose_page: ../features/practice-extra-rounds.md
tech_page: ../features/practice-extra-rounds.tech.md
total_tasks: 3
done: 2
---

# Practice Extra Rounds — Task Breakdown

---

## TASK-897: Practice-mode tail gate ignores tests

**Status:** [x] Done (repo)
**Feature:** practice-extra-rounds
**Type:** bug
**Complexity:** XS
**Depends On:** none

**Description:** `GET /api/study-session?scope=practice` computes the tail gate over non-test
items only; Practice mode sends it.

**Acceptance Criteria:**
- [x] An open test hides the tail without the scope and shows it with `scope=practice`.

**Files to Create / Modify:**
- `routes/study_session.py`, `static/js/session/controller.js`, `tests/test_study_session_tail.py`

**Verification:** `pytest tests/test_study_session_tail.py`

---

## TASK-898: Extra rounds (reviews / new words) in Practice mode

**Status:** [x] Done (repo)
**Feature:** practice-extra-rounds
**Type:** feature
**Complexity:** L
**Depends On:** TASK-897

**Description:** `GET /api/practice/extra`, `PracticeSessionService.get_extra_round`, RPC
`get_review_ahead_items`, "Keep practising" panel and player support, as in
[[features/practice-extra-rounds.tech]].

**Acceptance Criteria:**
- [x] Up to 10 new words per round, admitted past the quota; unstarted words used first.
- [x] Reviews: due first, then review-ahead; previous round's and recently attempted words skipped.
- [x] Panel shows after every round with the last choice selected; beyond-goal warning.
- [x] Attempts update FSRS/BKT and weekly counters (`is_tail`, per-item `session_mode`).

**Files to Create / Modify:**
- `migrations/practice_review_ahead.sql`, `services/practice_session_service.py`,
  `routes/practice.py`, `static/js/session/{tail,controller}.js`,
  `static/js/session/players/practice.js`, `templates/study_session.html`, `static/i18n/*.json`,
  `tests/test_practice_extra_rounds.py`, `tests/unit/session-tail.test.js`

**Verification:** `pytest tests/test_practice_extra_rounds.py`; `npx vitest run tests/unit`

---

## TASK-899: Apply `practice_review_ahead.sql` live and smoke-test

**Status:** [ ] Not Started (LIVE-DB — needs user approval)
**Feature:** practice-extra-rounds
**Type:** infra
**Complexity:** S
**Depends On:** TASK-898

**Description:** Apply the migration, then run `tests/sql/check_function_acls.sql` and call
`get_review_ahead_items` for a learner with reviewed words.

**Acceptance Criteria:**
- [ ] Function exists, service_role-only; ACL check returns empty result sets.
- [ ] Returns at most `p_limit` items, one per sense, none attempted in the last 10 minutes.
- [ ] In Practice mode, a reviews-only round runs past the due queue.

**Verification:** `SELECT public.get_review_ahead_items('<uuid>', 1::smallint, 10, 10, '{}');`

---
