---
title: "DT Guided Self-Repair — Task Breakdown"
feature: dt-guided-self-repair
prose_page: ../features/dt-guided-self-repair.md
tech_page: ../features/dt-guided-self-repair.tech.md
total_tasks: 17
done: 0
---

# DT Guided Self-Repair — Task Breakdown

Spec: [[features/dt-guided-self-repair.tech]] (section numbers below refer to it). Design:
[[design/dt-feedback/option-2-guided-self-repair/SPEC]] Revision 2. Supersedes the placeholders
TASK-939 and TASK-940 in [[tasklist/dt-single-call-grader.tasks]] (WP-INT updates them).

Drafted 2026-11-14, **not yet reviewed by the owner** (CLAUDE.md §5d). IDs start at TASK-952: the
highest existing id was TASK-941 and ten ids (942–951) are left free for the concurrent grader work.

## Work packages and file ownership

WP-BE and WP-FE run **in parallel** and share **no files**; the API contract and fixtures in tech
§4 are their only interface. WP-INT runs after both.

| Package | Tasks | Files it may touch (nothing else) |
|---|---|---|
| **WP-BE** | 952–959 | `migrations/dt_guided_self_repair.sql`; `services/dual_translation/repair/**`; `routes/dt_repair.py`; `app.py`; `web/rate_limits.py`; `routes/dual_translation.py` (TASK-959 only); `services/study_session/queue.py`; `services/study_session/session.py`; `tests/test_dt_repair_*.py` |
| **WP-FE** | 960–965 | `static/js/dt-repair-sheet.js`; `static/css/dt-repair.css`; `static/js/session/players/dt_repair.js`; `static/js/dual_translation.js`; `static/js/session/players/dual_translation.js`; `static/js/session/player_registry.js`; `static/js/session/controller.js`; `templates/dual_translation.html`; `templates/study_session.html`; `static/i18n/en.json`, `zh.json`, `ja.json`; `tests/unit/dt-repair-sheet.test.js`; `tests/unit/session-dt-repair-player.test.js`; `tests/unit/session-dt-player.test.js`; `tests/unit/player-registry.test.js`; `tests/unit/fixtures/dt-repair/*`; `tests/e2e/dt-repair/*` |
| **WP-INT** | 966–968 | `tests/e2e/dt-repair.spec.js`; `wiki/index.md`; `wiki/log.md`; `wiki/tasklist/master.md`; `wiki/tasklist/dt-single-call-grader.tasks.md`; `wiki/features/dual-translation.tech.md`; `wiki/features/dt-guided-self-repair*.md`; `wiki/tasklist/dt-guided-self-repair.tasks.md` |

Shared rule for WP-BE: do not edit `services/dual_translation/single_call_grader.py`,
`single_call_prompts.py`, `grader_cascade.py`, `config.py` or `migrations/dt_grading_assets.sql`
(the grader agent owns them). Import only what tech §11 lists.

---

## TASK-952: Migration `dt_guided_self_repair.sql`

**Status:** [ ] Not Started
**Feature:** dt-guided-self-repair
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
Write (do not apply) the additive migration creating `dt_repair_session`, `dt_repair_item` and
`dt_repair_event` exactly as tech §9.1, with header comment block (purpose, size estimate from
§9.2, retention note, verification queries), COMMENTs, RLS enabled and client roles revoked.

**Acceptance Criteria:**
- [ ] DDL matches tech §9.1 column-for-column (names, types, CHECKs, defaults, FKs, indexes)
- [ ] Idempotent: only `CREATE TABLE IF NOT EXISTS` / `CREATE [UNIQUE] INDEX IF NOT EXISTS` / `COMMENT` / `ALTER TABLE … ENABLE ROW LEVEL SECURITY` / `REVOKE`; no DROP, DELETE, or ALTER of existing tables
- [ ] `pytest tests/test_migration_security_lint.py -q` passes with the new file
- [ ] `tests/test_dt_repair_migration.py` asserts: the three tables have RLS + REVOKE in the file; no forbidden statements; every enum value in tech §5.5 appears in its CHECK

**Technical Notes:**
Mirror the style of `migrations/dt_grading_assets.sql`. `dt_repair_event.user_id` has no FK on
purpose (§9.1 comment). Search-before-archive: the file redefines nothing, so nothing is archived.

**Files to Create / Modify:**
- `migrations/dt_guided_self_repair.sql` — new
- `tests/test_dt_repair_migration.py` — new static test

**Verification:**
`pytest tests/test_migration_security_lint.py tests/test_dt_repair_migration.py -q` passes. After the
owner applies it (TASK-966): `SELECT relname, relrowsecurity FROM pg_class WHERE relname LIKE 'dt_repair_%';` → three rows, all `t`.

---

## TASK-953: Settings, hint templates and `hints.py`

**Status:** [ ] Not Started
**Feature:** dt-guided-self-repair
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
Create the repair package skeleton, `settings.py` (tech §2, env-read module attributes), the
production hint file built from Track D templates (tech §5.2) and `hints.py`: load + validate,
ladder per subtype (§5.1), rungs (§3.2 table), render kind/clue with the fallback chain (§5.3), and
the leak filter (§5.4).

**Acceptance Criteria:**
- [ ] `hint_templates.json` has `version`, `limits`, `type_neutral` (en/zh/ja) and an entry with `ladder` for all 40 v6 slugs; `label`/`clue` copied from `data/eval/dt_decision_2026-11-14/track_d/templates.json` (`label` ← label, `clue` ← `hint`); no `{c}` anywhere
- [ ] Clues over the length limits are shortened by hand and listed in the commit message (they are AI drafts pending TASK-938)
- [ ] `hints.load()` validates; an invalid file makes `hints.available()` False and logs once, never raises at import
- [ ] `render_kind` falls back template → taxonomy gloss head → English label; `render_clue` falls back to `type_neutral` for a missing template, an empty/unfound `{l}`, or a leak; each returns `(text, lang, hint_source, template_id)`
- [ ] `leaks()` true/false cases from tech §5.4 including zh/ja and a `reference_sentence` correction
- [ ] `tests/test_dt_repair_hints.py` covers all of the above

**Technical Notes:**
`tier0._normalize_l2` for normalisation. Taxonomy glosses via
`grader_cascade.get_active_taxonomy(db)['subtype_glosses']` — pass the taxonomy dict in, keep
`hints.py` pure. Template ids: `"<slug>.<l1>.kind"`, `"<slug>.<l1>.clue"`, `"type_neutral.<l1>"`,
`"gloss.<slug>.<l1>"`.

**Files to Create / Modify:**
- `services/dual_translation/repair/__init__.py`, `settings.py`, `hint_templates.json`, `hints.py` — new
- `tests/test_dt_repair_hints.py` — new

**Verification:**
`pytest tests/test_dt_repair_hints.py -q` passes; `python -c "from services.dual_translation.repair import hints; print(hints.available(), hints.version())"` prints `True repair-hints/2026-11-14.1`.

---

## TASK-954: Sentence model and step planner

**Status:** [ ] Not Started
**Feature:** dt-guided-self-repair
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-953

**Description:**
Implement `sentences.py` (per-pair offsets, local spans, L1 prompt resolution, tech §3.1) and
`planner.py` (eligibility, clean, bypass, primary error, step kind, cap and order, location, rungs,
tech §3.2). Both pure except `sentences.l1_prompts(db, …)`.

**Acceptance Criteria:**
- [ ] `plan(grade, errors, sentence_model, age_tier, hints) -> {eligible, status, steps, direct_items}` implements every rule of §3.2
- [ ] Tests: clean; bypass at 5 flagged sentences and at a score of 1; primary-error ordering; cap of 3 chosen by severity then displayed in passage order; over-cap and `none`-ladder sentences become `direct`; unsure only when every error < threshold; age tier 1–2 downgrade; location false for `span_source='sentence'` and > 40%; point span allowed; rungs per the §3.2 table; ineligible when any `sentence_index` is NULL or tier is v2/v1
- [ ] Tests: offsets with leading/trailing whitespace; merged pairs; L1 rules 1, 2 and 3 (`null`)

**Technical Notes:**
`build_sentence_pairs(gold_l2, reproduction)` must be called with the raw texts (the grader's
offsets refer to them). Range-passage L1 lookup reuses the query shape of
`routes/dual_translation._get_usable_references` (copy it into `sentences.py`; do not import the
route module from services).

**Files to Create / Modify:**
- `services/dual_translation/repair/sentences.py`, `planner.py` — new
- `tests/test_dt_repair_planner.py` — new

**Verification:**
`pytest tests/test_dt_repair_planner.py -q` passes.

---

## TASK-955: Re-check function and outcome classifier

**Status:** [ ] Not Started
**Feature:** dt-guided-self-repair
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-953

**Description:**
Implement `recheck.recheck_sentence` (tech §6.1) on top of the single-call grader's prompt,
schema, call and decoder, and `classify.classify` (tech §6.3) that turns a re-check into
`fixed` / `no_issue_found` / `still_flagged` with the new active error and the compact detail.

**Acceptance Criteria:**
- [ ] One model call, primary slug only, timeout `DT_REPAIR_RECHECK_TIMEOUT_S`; user prompt built from one sentence pair; `prompt_version == single_call_prompts.PROMPT_VERSION`
- [ ] Status mapping: ok / timeout / call_failed / malformed / unsupported (unsupported L2 or taxonomy mismatch makes no call)
- [ ] Low-confidence entries withheld exactly as in grading (follows `DT_SINGLE_CALL_SHOW_LOW_CONFIDENCE`)
- [ ] `llm_calls` row written only for non-ok statuses (`task_name='dt_repair_recheck'`), fail-soft
- [ ] `classify` cases: target present by subtype; by span overlap with a different subtype; new major error → `still_flagged/new_error` and active switches; leftover minor → `fixed`; corrected form absent → `no_issue_found`; `reference_sentence` correction; compact detail ≤ 5 entries, note ≤ 240 chars
- [ ] Tests monkeypatch `single_call_grader.call_structured` (no network): `tests/test_dt_repair_recheck.py`, `tests/test_dt_repair_classify.py`

**Technical Notes:**
Import list and fallbacks in tech §11 (items 1–8). If `single_call_grader._attempt` has no
`timeout` parameter when you start, call `call_structured(..., timeout=…)` and mirror `_attempt`'s
JSON parsing (`clean_json_response` + `json.loads` + shape check). Do not edit grader files.

**Files to Create / Modify:**
- `services/dual_translation/repair/recheck.py`, `classify.py` — new
- `tests/test_dt_repair_recheck.py`, `tests/test_dt_repair_classify.py` — new

**Verification:**
`pytest tests/test_dt_repair_recheck.py tests/test_dt_repair_classify.py -q` passes. Optional live
smoke (costs < $0.001, needs `OPENROUTER_API_KEY`): `python -c` calling `recheck_sentence` on
"It's a sick way to learn by doing." vs "It's a great way to learn by doing." returns status ok
and a `register` error.

---

## TASK-956: Store, scheduling, budget and service orchestration

**Status:** [ ] Not Started
**Feature:** dt-guided-self-repair
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-952, TASK-954, TASK-955

**Description:**
Implement `store.py` (all reads/writes, each a monkeypatch boundary), `scheduling.py` (tech §7.1–
7.3, pure), `budget.py` (§9.3) and `service.py`: `start_session`, `redact`, `session_payload`,
`open_item`, `next_hint`, `check`, `dispute`, `reveal`, `skip`, `finish`, `full_result`,
`practice_due`, `count_due`, `finish_stale`, and `hooks.py` (`after_grade`, `for_cached`).

**Acceptance Criteria:**
- [ ] Every behaviour of tech §4.4–§4.11 implemented in `service.py` (routes stay thin)
- [ ] Check: lock, unchanged (no call), budget/call caps, tier-0 equality (no call), re-check, classify, event write, close rules, auto-reveal at the cap, `client_check_id` replay returns the stored result
- [ ] Answer object built per tech §4.7 (marks merged and sorted, `reference_sentence` corrections unmarked, explanation choice and trimming)
- [ ] Queue rule §7.1 applied on close and on bypass; daily `after_sitting` per §7.3; due selection §7.2 with learner-local day (`services.day_boundary.plan_today_iso`); expiry marking
- [ ] Study time credited per §7.5 through `services.study_time.credit_study_time`
- [ ] `hooks.after_grade` never raises (returns the full contract on any error) and returns redacted / full contracts per tech §4.1
- [ ] `tests/test_dt_repair_scheduling.py` (pure) and `tests/test_dt_repair_service.py` (store + recheck monkeypatched) cover each §4 path, including: no pre-reveal response contains the reference sentence, any `corrected_form`, or any `explanation`

**Technical Notes:**
`full_result` reuses `routes.dual_translation._cached_grade` via a lazy import inside the function
(avoids an import cycle at module load). `grade_tokens_today` moves the logic of
`routes/dual_translation._tokens_used_today` into `budget.py` (copy; TASK-959 makes the route
delegate). Use `supabase` query-builder chains as in `routes/dual_translation.py`; the lock is
`.update({...}).eq('id', id).or_('check_lock_until.is.null,check_lock_until.lt.<now iso>')` and
"acquired" means `resp.data` non-empty.

**Files to Create / Modify:**
- `services/dual_translation/repair/store.py`, `scheduling.py`, `budget.py`, `service.py`, `hooks.py` — new
- `tests/test_dt_repair_scheduling.py`, `tests/test_dt_repair_service.py` — new

**Verification:**
`pytest tests/test_dt_repair_scheduling.py tests/test_dt_repair_service.py -q` passes.

---

## TASK-957: Blueprint `routes/dt_repair.py`, registration and rate limits

**Status:** [ ] Not Started
**Feature:** dt-guided-self-repair
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-956

**Description:**
Expose tech §4.3–§4.11 as `dt_repair_bp` under `/api/dual-translation/repair`, register it in
`app.py`, and add the three limits of tech §9.3 to `web/rate_limits.py`.

**Acceptance Criteria:**
- [ ] Routes and view-function names: `GET /submissions/<int:submission_id>/session` (`get_session`), `GET /submissions/<int:submission_id>/result` (`get_result`), `POST /items/<int:item_id>/open` (`open_item`), `/hint` (`hint`), `/check` (`check`), `/reveal` (`reveal`), `/dispute` (`dispute`), `/skip` (`skip`), `POST /sessions/<int:session_id>/finish` (`finish`), `GET /practice/due` (`practice_due`)
- [ ] Every route: `@supabase_jwt_required`; 503 `REPAIR_DISABLED` when the flag is off; 404/403 ownership; validation → 400 with `error_code`; responses exactly in the tech §4 shapes (envelope rule §4.12)
- [ ] `tests/test_dt_repair_routes.py` in the style of `tests/test_dual_translation_routes.py` (app/client/auth_headers fixtures, `service`/`store` monkeypatched; model boundary `repair.recheck.recheck_sentence` patched): happy path per route, 401, 403, 404, 503, each 409 code, `TEXT_TOO_LONG`
- [ ] Rate-limit entries present (unit test reads `ENDPOINT_LIMITS`)

**Technical Notes:**
Register after `dual_translation_bp` in `app.py`; `init_rate_limits(app)` already runs after
registration. JSON bodies via `request.get_json(silent=True) or {}`.

**Files to Create / Modify:**
- `routes/dt_repair.py` — new
- `app.py` — import + `app.register_blueprint(dt_repair_bp, url_prefix='/api/dual-translation/repair')`
- `web/rate_limits.py` — three entries
- `tests/test_dt_repair_routes.py` — new

**Verification:**
`pytest tests/test_dt_repair_routes.py tests/test_dual_translation_routes.py -q` passes.

---

## TASK-958: Daily-session block `dt_repair`

**Status:** [ ] Not Started
**Feature:** dt-guided-self-repair
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-956

**Description:**
Add the conditional `dt_repair` block to the daily session queue (tech §7.6) using the
`intro_reviews` pattern, and accept it in complete-block.

**Acceptance Criteria:**
- [ ] `queue.dt_repair_status`, `queue.insert_dt_repair`, `DT_REPAIR_BLOCK_ID`/`DT_REPAIR_KIND` as specified; placement before the first `dual_translation` item, else before the first `practice` item, else last
- [ ] `session.build_study_session` adds the block only when status is `check` and `count_due > 0`; `done` keeps it as completed; DT excluded or flag off → no block; a counting failure → no block, logged
- [ ] `complete_block` accepts `dt_repair`; `surface_skill_for('dt_repair')` stays None (no weekly credit)
- [ ] `tests/test_dt_repair_session_block.py`; existing `tests/test_study_session_*.py` still pass

**Technical Notes:**
The count runs inside `_session_reads` (concurrent, `(value, error)` outcome) like `intro_due`.

**Files to Create / Modify:**
- `services/study_session/queue.py`, `services/study_session/session.py`
- `tests/test_dt_repair_session_block.py` — new

**Verification:**
`pytest tests/test_dt_repair_session_block.py tests/test_study_session_ordering.py tests/test_study_session_tail.py -q` passes.

---

## TASK-959: Submit hook and budget wrapper in `routes/dual_translation.py`

**Status:** [?] Blocked — start only after the concurrent single-call grader revision has landed in `routes/dual_translation.py` (rebase on it; the orchestrator confirms)
**Feature:** dt-guided-self-repair
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-956

**Description:**
Wire the repair session into submit (tech §3.3): call `hooks.after_grade` after the two persist
calls and return its dict; call `hooks.for_cached` on the cached-grade path; make
`_tokens_used_today` add `budget.recheck_tokens_today`. Nothing else in the file changes.

**Acceptance Criteria:**
- [ ] Flag off or ineligible grade → response byte-identical to today's (test compares JSON)
- [ ] Open session → redacted contract + `repair`; clean → full + `repair.clean`; bypass → full + `repair.status='bypassed'`
- [ ] Cached path returns the existing session (open → redacted)
- [ ] `hooks` raising → full contract, error logged, status 200
- [ ] Provisional (unpersisted) grade → no session
- [ ] `tests/test_dt_repair_submit_hook.py` passes; `tests/test_dual_translation_routes.py` unchanged and passing

**Technical Notes:**
The hook goes after `_persist_grading_assets` and before the target-word / prestudy / study-time
side effects, but the returned dict replaces only the final `api_success(contract)` argument —
those side effects still read the unredacted `contract`.

**Files to Create / Modify:**
- `routes/dual_translation.py` — the two hook calls and the `_tokens_used_today` change
- `tests/test_dt_repair_submit_hook.py` — new

**Verification:**
`pytest tests/test_dt_repair_submit_hook.py tests/test_dual_translation_routes.py tests/test_dual_translation_single_call_grader.py -q` passes.

---

## TASK-960: Sheet shell, layout, theming and i18n keys

**Status:** [ ] Not Started
**Feature:** dt-guided-self-repair
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
Create `static/js/dt-repair-sheet.js` (classic IIFE, `window.DTRepairSheet.open/close`, tech §8.2)
with the three-zone dialog, scrim, visual-viewport tracking, dots, focus trap and close/Escape,
and `static/css/dt-repair.css` (tech §8.3, §8.10). Add all i18n keys of tech §8.6 to en/zh/ja.

**Acceptance Criteria:**
- [ ] Phone full-screen at `100dvh`/visual-viewport height; ≥ 600 px centred 420 px card, background `inert`; body scroll locked while open and restored on close
- [ ] `kb` and `tight` classes toggle per §8.3; light and dark via app tokens; `prefers-reduced-motion` disables motion
- [ ] Dialog semantics, focus trap, focus return, `aria-live` region per §8.10
- [ ] i18n keys flat in en/zh/ja; `tests/test_i18n_locale_files.py` passes

**Technical Notes:**
Port structure and CSS ideas from `wiki/design/dt-feedback/option-2-guided-self-repair/mockup.html`
(class names prefixed `dtr-`). Use the `tr(key, params, fallback)` helper pattern of
`dt-error-card.js`.

**Files to Create / Modify:**
- `static/js/dt-repair-sheet.js`, `static/css/dt-repair.css` — new
- `static/i18n/en.json`, `zh.json`, `ja.json` — keys

**Verification:**
`npm run lint && npm run lint:css && npm run format:check` pass; `pytest tests/test_i18n_locale_files.py -q` passes.

---

## TASK-961: Fix step — field, underline, hints, checking, unsure

**Status:** [ ] Not Started
**Feature:** dt-guided-self-repair
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-960

**Description:**
Implement the `fix` view and its sub-states (tech §8.4, §8.5 rows from "enter step" to "fix
(unsure) text changed"): labelled field with mirror underline and point marker, IME-safe Enter,
single hint slot, hint button relabelling, checking state with double-submit guard and 7 s abort,
still/same/error messages and the 2-failure degrade to "Show answer", and the unsure variant.

**Acceptance Criteria:**
- [ ] Every request uses the tech §4 shapes; `client_check_id` generated per check and reused on retry; `expected_level` sent on hint
- [ ] Enter never checks while composing (`isComposing` or `keyCode 229`, and one tick after `compositionend`)
- [ ] Unchanged text → `same` with no request
- [ ] Underline follows `where.text` through edits and disappears when edited away; `point` draws an insertion mark
- [ ] Long-sentence type steps and in-field scroll per §8.3; prompt clamp + overlay
- [ ] Focus rules per §8.4 (pointer-fine vs touch)

**Technical Notes:**
The mockup's `paint()`, `slot()`, `check()` are the reference behaviour; replace its scripted
grader with the API. Server-provided texts get `lang` from the response.

**Files to Create / Modify:**
- `static/js/dt-repair-sheet.js`, `static/css/dt-repair.css`

**Verification:**
The fix-view cases of `tests/unit/dt-repair-sheet.test.js` (TASK-965) pass.

---

## TASK-962: Result, clean, success, kept, answer and summary views

**Status:** [ ] Not Started
**Feature:** dt-guided-self-repair
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-960

**Description:**
Implement the remaining views of tech §8.5: `result`, `clean`, `ok`, `kept`, `reveal`/`alt`
(You wrote / Answer blocks with marks, heading variants, explanation), `answer_loading` with its
failure state, `summary` (from finish, client-count fallback), auto-advance, `direct` steps, and
the close/finish path.

**Acceptance Criteria:**
- [ ] Answer view: "You wrote" (= `learner_sentence`, marks in `<del>` line-through) above "Answer" (marks in `<b>` bold + underline), explanation with `lang`; unmarked rendering when both mark lists are empty
- [ ] Auto-advance after `auto_advance_ms` from Fixed/Kept; never under reduced motion; cancelled by any interaction
- [ ] `direct` steps call reveal{reason:'direct'} on display
- [ ] Close / Escape → finish{closed_early:true} (pass) or skip (daily) → `onDone({closedEarly:true})`
- [ ] Every failure row of tech §8.9 handled

**Technical Notes:**
Type steps for the answer view per §8.3 (`fitOrig()` in the mockup).

**Files to Create / Modify:**
- `static/js/dt-repair-sheet.js`, `static/css/dt-repair.css`

**Verification:**
The view cases of `tests/unit/dt-repair-sheet.test.js` (TASK-965) pass.

---

## TASK-963: Open the sheet from the DT page and the session DT player

**Status:** [ ] Not Started
**Feature:** dt-guided-self-repair
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-961, TASK-962

**Description:**
Branch on the submit response's `repair` key in both hosts (tech §8.7): open the sheet for
`open`/`clean`, fetch `/result` after an open session finishes, and fall back to today's views
otherwise. Load the CSS/JS in both templates.

**Acceptance Criteria:**
- [ ] No `repair` key or `bypassed` → exactly today's behaviour (existing unit tests unchanged)
- [ ] A redacted contract is never passed to `renderResult` nor stashed in `dt_feedback_view`
- [ ] After `onDone`, `/result` is fetched (1 retry) and rendered by the existing result view / band screen; failure shows the notice with retry and continue
- [ ] Standalone page resumes an open session after reload via `GET …/session`
- [ ] `window.DTRepairSheet` missing → fetch result and continue (no dead end)

**Technical Notes:**
`templates/dual_translation.html`: script before `dual_translation.js`. `templates/study_session.html`:
`<script defer>` beside `dt-error-card.js`.

**Files to Create / Modify:**
- `static/js/dual_translation.js`, `static/js/session/players/dual_translation.js`
- `templates/dual_translation.html`, `templates/study_session.html`
- `tests/unit/session-dt-player.test.js` — repair branch cases

**Verification:**
`npm run test:unit -- session-dt-player` passes, including new cases for open / clean / bypassed / absent.

---

## TASK-964: Daily practice player `dt_repair`

**Status:** [ ] Not Started
**Feature:** dt-guided-self-repair
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-961, TASK-962

**Description:**
Add the `dt_repair` session player (tech §8.8), register the kind, and label it in the controller.

**Acceptance Criteria:**
- [ ] `player_registry.js`: loader, `KIND_PLAYERS.dt_repair`, `KIND_MODULES.dt_repair`
- [ ] `controller.js`: `KIND_LABELS.dt_repair`
- [ ] Empty due → `onComplete` without opening the sheet; close → `onSkip`; finish → `onComplete`
- [ ] "From your translation on {day}" eyebrow formatted per §8.6
- [ ] `tests/unit/session-dt-repair-player.test.js` new; `tests/unit/player-registry.test.js` extended

**Technical Notes:**
The runner already passes the session language to players; use the same field the DT player uses
for its calls.

**Files to Create / Modify:**
- `static/js/session/players/dt_repair.js` — new
- `static/js/session/player_registry.js`, `static/js/session/controller.js`
- `tests/unit/session-dt-repair-player.test.js` — new; `tests/unit/player-registry.test.js`

**Verification:**
`npm run test:unit -- dt-repair player-registry` passes.

---

## TASK-965: Frontend unit tests and no-scroll harness

**Status:** [ ] Not Started
**Feature:** dt-guided-self-repair
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** TASK-961, TASK-962

**Description:**
Write the fixtures of tech §4.12, the sheet unit tests (tech §8.11) and a no-scroll harness that
ports `verify.cjs` to the real CSS/JS with a stubbed `authFetch`.

**Acceptance Criteria:**
- [ ] `tests/unit/fixtures/dt-repair/*.json` exactly as tech §4.12
- [ ] `tests/unit/dt-repair-sheet.test.js` covers every transition row of tech §8.5 and the cases listed in §8.11
- [ ] `tests/e2e/dt-repair/harness.html` + `noscroll.cjs`: every view/state for en, zh and ja items (including the three longest gold sentences) at 390×844, 375×667, 1280×800, 390×500, 375×340, light and dark — 0 failures; includes the answer-step checks of `verify.cjs`
- [ ] Prints a count like `N checks, 0 failures`

**Technical Notes:**
Run with `NODE_PATH=/opt/node-tools/node_modules node tests/e2e/dt-repair/noscroll.cjs` (the
preinstalled Playwright/Chromium); no app server needed. The harness must load
`/static/css/styles.css` too (tokens) — serve via `file://` paths relative to the repo.

**Files to Create / Modify:**
- `tests/unit/fixtures/dt-repair/*.json`, `tests/unit/dt-repair-sheet.test.js` — new
- `tests/e2e/dt-repair/harness.html`, `tests/e2e/dt-repair/noscroll.cjs` — new

**Verification:**
`npm run test:unit` passes; `NODE_PATH=/opt/node-tools/node_modules node tests/e2e/dt-repair/noscroll.cjs` prints `… 0 failures`.

---

## TASK-966: Apply the migration and verify the grader contract live

**Status:** [?] Blocked — needs the owner to apply `migrations/dt_guided_self_repair.sql` (LIVE-DB) and needs `dt_grading_assets.sql` applied (TASK-935)
**Feature:** dt-guided-self-repair
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** TASK-952, TASK-959, TASK-935

**Description:**
After both work packages merge: re-verify every item of tech §11 against the merged grader code,
then the owner applies the migration; confirm one real submission creates a session.

**Acceptance Criteria:**
- [ ] Each tech §11 field/function checked against the merged code; differences fixed in WP-BE code or recorded in the tech page
- [ ] Migration applied; `tests/sql/check_function_acls.sql` result sets empty
- [ ] One graded submission with an error → `dt_repair_session` row with `status='open'` and items; the submit response is redacted
- [ ] `DT_GUIDED_REPAIR` documented in the deploy env notes (default on)

**Technical Notes:**
If `dt_error_instance.sentence_index` is NULL on new grades, the flow is silently ineligible —
check `DT_GRADING_ASSET_COLUMNS` and the asset migration first.

**Files to Create / Modify:**
- none (apply SQL; env)

**Verification:**
`SELECT status, n_steps FROM dt_repair_session ORDER BY id DESC LIMIT 1;` after a test submission.

---

## TASK-967: Authenticated end-to-end test

**Status:** [?] Blocked — needs a test-account credential (`TEST_USER_PASSWORD` or `TEST_JWT_TOKEN`) or owner permission to mint one with the service-role key; writes to the production DB (tech §14)
**Feature:** dt-guided-self-repair
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** TASK-963, TASK-964, TASK-966

**Description:**
Playwright spec against the running app covering the pass (hint → fix → summary → result view),
a dispute, a reveal, the clean path, and one daily-practice item, with the no-scroll assertion on
each real screen at 390×844.

**Acceptance Criteria:**
- [ ] `tests/e2e/dt-repair.spec.js` passes against `gunicorn wsgi:app --bind 127.0.0.1:5000 --workers 2`
- [ ] Uses a passage from a test the test account has attempted; a planted error makes the grader flag it
- [ ] The daily item is made due by updating `due_on`/`not_before` for the test account's item with the service role (cleanup at the end: set `queue_status='retired'`)
- [ ] Total OpenRouter spend per run < $0.01 (log the event costs)

**Technical Notes:**
Auth: `tests/e2e/auth.setup.js` already supports `TEST_USER_EMAIL` + `TEST_USER_PASSWORD` or
`TEST_JWT_TOKEN`. Chromium: `PW_CHROMIUM_PATH` per `playwright.config.js`.

**Files to Create / Modify:**
- `tests/e2e/dt-repair.spec.js` — new

**Verification:**
`BASE_URL=http://127.0.0.1:5000 npx playwright test tests/e2e/dt-repair.spec.js` passes.

---

## TASK-968: Wiki integration

**Status:** [ ] Not Started
**Feature:** dt-guided-self-repair
**Type:** docs
**Complexity:** S (1-3h)
**Depends On:** TASK-959, TASK-965

**Description:**
Bring the wiki in line after both work packages merge.

**Acceptance Criteria:**
- [ ] `wiki/index.md` lists the two feature pages and this task file
- [ ] `wiki/tasklist/master.md` lists TASK-952–968 with statuses; summary counts updated
- [ ] `wiki/tasklist/dt-single-call-grader.tasks.md`: TASK-939 and TASK-940 marked superseded by this breakdown
- [ ] `wiki/features/dual-translation.tech.md` "Still needed for the guided self-repair flow" replaced by a link to [[features/dt-guided-self-repair.tech]]
- [ ] Feature pages' `status` and any decisions changed during the build updated; `wiki/log.md` entry appended
- [ ] Any deviation found in TASK-966 recorded in tech §11/§12

**Technical Notes:**
CLAUDE.md §6 formats.

**Files to Create / Modify:**
- `wiki/index.md`, `wiki/log.md`, `wiki/tasklist/master.md`, `wiki/tasklist/dt-single-call-grader.tasks.md`, `wiki/features/dual-translation.tech.md`, `wiki/features/dt-guided-self-repair.md`, `wiki/features/dt-guided-self-repair.tech.md`, `wiki/tasklist/dt-guided-self-repair.tasks.md`

**Verification:**
Every `[[link]]` in the changed pages resolves to an existing file (grep).

---
