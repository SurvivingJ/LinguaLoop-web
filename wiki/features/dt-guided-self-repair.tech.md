---
title: DT Guided Self-Repair — Technical Specification
type: feature-tech
status: planned
prose_page: ./dt-guided-self-repair.md
last_updated: 2026-11-14
dependencies:
  - "design: wiki/design/dt-feedback/option-2-guided-self-repair/SPEC.md (Revision 2) + mockup.html + verify.cjs"
  - "grader: services/dual_translation/single_call_grader.py (ADR-044, prompt v2) — internals listed in §11"
  - "tables read: dt_submission, dt_passage, dt_passage_reference, dt_grade, dt_error_instance, test_sentences, test_sentence_references, users, daily_test_loads, user_study_plans"
  - "tables written: NEW dt_repair_session, dt_repair_item, dt_repair_event; existing study_time_credits (via services.study_time), daily_test_loads.completed_blocks (via complete-block), llm_calls (failed re-checks only)"
  - "routes: NEW routes/dt_repair.py (blueprint dt_repair, /api/dual-translation/repair); hook in routes/dual_translation.py submit"
  - "session queue: services/study_session/queue.py + session.py (new block kind dt_repair)"
  - "frontend: NEW static/js/dt-repair-sheet.js (global DTRepairSheet), static/css/dt-repair.css, static/js/session/players/dt_repair.js"
breaking_change_risk: medium
---

# DT Guided Self-Repair — Technical Specification

Prose: [[features/dt-guided-self-repair]]. Tasks: [[tasklist/dt-guided-self-repair.tasks]].
Design: [[design/dt-feedback/option-2-guided-self-repair/SPEC]] — **Revision 2 (app-style flow)
governs layout**; §1.2 (ladder), §1.4 (which errors get a ladder), §2.1 (recording), §5.2 (span
validation), §5.3 (hint content, leak rule) and §8 (daily practice) govern behaviour except where
this page records a decision that differs (each one is listed in §12 with its reason).

Two agents build this in parallel: **WP-BE** (§3–§7, §9) and **WP-FE** (§8). The API in §4 is the
only interface between them; the fixtures in §4.12 are normative examples. Neither package edits a
file owned by the other (§10).

---

## 1. Architecture Overview

```
Browser (dt-repair-sheet.js)              Flask                                    Postgres / OpenRouter
────────────────────────────              ─────                                    ─────────────────────
POST /api/dual-translation/<sid>/submit ─► submit()  (existing)
                                            grade_submission → contract
                                            _persist_grade, _persist_grading_assets   ─► dt_grade, dt_error_instance
                                            repair.hooks.after_grade(...)              ─► dt_repair_session + dt_repair_item[]
                                          ◄─ eligible & has steps:  REDACTED contract + repair{session}
                                             eligible & clean:      full contract + repair{clean}
                                             not eligible / error:  full contract (no `repair` key)  = today
[sheet opens: result → fix steps]
POST /repair/items/<id>/open            ─► record opened_at / start daily sitting
POST /repair/items/<id>/hint            ─► next rung: where (span) | kind (label) | clue (template)
POST /repair/items/<id>/check           ─► tier-0 equal? ─yes─► fixed (no call)
                                            │ no
                                            recheck.recheck_sentence(ref_sentence, revised)  ─► OpenRouter (1 call, ~1.4 s)
                                            classify → fixed | no_issue_found | still_flagged ─► dt_repair_event
POST /repair/items/<id>/dispute|reveal  ─► close item, return answer{You wrote, Answer, explanation}
POST /repair/sessions/<id>/finish       ─► close open items as skipped, queue (§7.1), summary
GET  /repair/submissions/<sid>/result   ─► full contract (only after finish)  → existing result view

Daily session (study_session.py)        ─► block {kind:'dt_repair', id:'dt_repair'} when ≥1 item due
  player dt_repair.js → GET /repair/practice/due?language_id=L → same sheet, surface daily_practice
  → open / hint / check / reveal / dispute / skip per item → POST /api/study-session/complete-block
```

Key properties:

- The answer for a sentence (reference sentence, corrected form, explanation, diff) is **never in
  a response before that sentence's reveal**. The submit response is redacted while a session is
  open (§4.1); hint texts are rendered server-side from templates and pass a leak filter (§5.4).
- Re-check grades **one revised sentence against its reference sentence** with the single-call
  grader's own prompt, schema and decoder (§6). No new prompt.
- The repair session never changes the grade. `dt_grade` and `dt_error_instance` are read-only to
  this feature.
- Every failure degrades to the answer screen or to today's result view, never to a dead end
  (§8.9).

## 2. Configuration

All new settings live in `services/dual_translation/repair/settings.py`, read from the environment
at import (the same convention as `DT_ERROR_CARD_INTERLEAVE_EVERY` in `routes/dual_translation.py`),
so `config.py` is not touched (it is being edited by the concurrent grader work). Tests
monkeypatch the module attributes.

| Name (env var = attribute) | Default | Meaning |
|---|---|---|
| `DT_GUIDED_REPAIR` | `true` | Feature flag. Off → no session is created, submit returns the full contract exactly as today, all `/repair/*` endpoints return 503 `REPAIR_DISABLED`, and the daily block is never added. Default ON because the grader contract it needs (ADR-044 prompt v2, `DT_SINGLE_CALL_GRADER` default true since 2026-11-14) is available; per-submission eligibility (§3.2) still falls back to today's result view whenever a grade is not a single-call grade. |
| `DT_REPAIR_MAX_TARGETS` | `3` | Max sentences per pass that get the hint ladder (SPEC §1.1 cap). |
| `DT_REPAIR_BYPASS_FLAGGED` | `5` | Flagged sentences at or above which the pass is bypassed (SPEC §1.5). |
| `DT_REPAIR_UNSURE_CONFIDENCE_MAX` | `0.45` | **Provisional.** A sentence whose every error has `confidence` below this is an `unsure` step. With the grader's mapping (high 0.9 / medium 0.6 / low 0.3) only `low` qualifies; such errors only exist when `DT_SINGLE_CALL_SHOW_LOW_CONFIDENCE` is on (default off), so the unsure step is dormant by default. Not tuned. |
| `DT_REPAIR_CHECK_CAP_PASS` | `4` | Failed checks (`still_flagged`) before the answer is shown automatically, repair pass. |
| `DT_REPAIR_CHECK_CAP_DAILY` | `3` | Same, daily practice. |
| `DT_REPAIR_MAX_CALLS_PER_SITTING` | `6` | Hard cap on grader calls per item per sitting, counting failed calls. At the cap, check returns `budget_exhausted` (§4.5). |
| `DT_REPAIR_LOCATION_MAX_SHARE` | `0.4` | A span covering more than this share of the learner sentence is "not locatable" (SPEC §5.2). |
| `DT_REPAIR_RECHECK_TIMEOUT_S` | `5` | Server-side timeout for the re-check call. |
| `DT_REPAIR_TEXT_MAX_CHARS` | `400` | Max revision length (chars, after normalisation). Also rejected if longer than `2 × len(original sentence) + 40`. |
| `DT_REPAIR_DAILY_ITEMS` | `3` | Max items per daily block (SPEC §8.2). |
| `DT_REPAIR_FIRST_DUE_MIN_HOURS` | `20` | First daily due not sooner than this after the episode closed. |
| `DT_REPAIR_EXPIRY_DAYS` | `30` | Unresolved items expire this long after they were queued. |
| `DT_REPAIR_HINTED_RETURN_DAYS` | `3` | Return interval after a daily fix that needed "what kind" or "clue". |
| `DT_REPAIR_FAILED_RETURN_DAYS` | `2,4` | Return intervals after the 1st and 2nd failed daily sitting. |
| `DT_REPAIR_RETIRE_AFTER_FAILED` | `3` | Failed daily sittings before retirement. |
| `DT_REPAIR_MAX_SITTINGS` | `5` | Any item is retired after this many daily sittings (bounds hinted-fix loops). |
| `DT_REPAIR_TOKEN_ALLOWANCE` | `40000` | Re-checks are allowed while today's DT tokens (grades + re-checks) are below `Config.DT_DAILY_TOKEN_BUDGET + this`. |
| `DT_REPAIR_MAX_CHECKS_PER_DAY` | `60` | Max grader re-checks per user per UTC day. |
| `DT_REPAIR_SESSION_STALE_HOURS` | `24` | An `open` session older than this is finished lazily as `abandoned` (§7.4). |
| `DT_REPAIR_AUTO_ADVANCE_MS` | `1600` | Sent to the client in the session payload; client auto-advance delay after Fixed / Kept. |

## 3. Backend design (WP-BE)

New package `services/dual_translation/repair/`:

| Module | Contents | Pure? |
|---|---|---|
| `settings.py` | §2 | yes |
| `hint_templates.json` | §5.2 data file | data |
| `hints.py` | load + validate templates, ladder kind per subtype, rung list, render kind/clue, leak filter | yes |
| `sentences.py` | per-sentence extraction (learner sentence, reference sentence, offsets, local spans), L1 prompt resolution | yes except `l1_prompts(db, ...)` |
| `planner.py` | eligibility, bypass, primary error per sentence, step selection and order | yes |
| `recheck.py` | `recheck_sentence(...)` (§6) — the only model boundary of the feature | no (model call) |
| `classify.py` | re-check result → `fixed / no_issue_found / still_flagged` + new active error (§6.3) | yes |
| `scheduling.py` | queue rules (§7.1–7.3): queued?, first due, next due after a sitting | yes |
| `budget.py` | `tokens_used_today`, `checks_today`, `recheck_allowed` | no (DB) |
| `store.py` | every DB read/write of the three new tables + the existing reads; each function a monkeypatch boundary | no |
| `service.py` | orchestration used by routes: `start_session`, `redact`, `get_session_payload`, `open_item`, `next_hint`, `check`, `dispute`, `reveal`, `skip`, `finish`, `practice_due`, `full_result` | no |
| `hooks.py` | `after_grade(...)`, `for_cached(...)` called by `routes/dual_translation.py` | no |

`routes/dt_repair.py` — new blueprint `dt_repair_bp`, registered in `app.py` with
`url_prefix='/api/dual-translation/repair'`. Every handler: `@supabase_jwt_required`, flag check,
parse/validate, ownership check, call `service`, shape with `api_success` / `api_error`.

### 3.1 Sentence model

For a submission: `pairs = sentence_pairs.build_sentence_pairs(gold_l2, reproduction).pairs`
(deterministic; it is the pairing the grader numbered, so `dt_error_instance.sentence_index`
indexes it). For pair `i`:

- `repro_start, repro_end` = `pair.repro.start/end` moved inward past leading/trailing whitespace
  (so the learner sentence is `reproduction[repro_start:repro_end]`, stripped);
- `ref_start, ref_end` = same for `pair.ref` over `gold_l2`;
- an error's **local learner span** = `span_reproduction − repro_start`, clamped to
  `[0, len(learner_sentence)]`; its **local reference span** = `span_reference − ref_start`, clamped
  likewise. A span not inside its pair after clamping is treated as not locatable.

Only offsets are stored (`dt_repair_item.repro_start/…`), never a copy of the sentence texts
(owner: no duplicated passage text). The learner's sentence is re-sliced from
`dt_submission.reproduction`, the reference sentence from `dt_passage.l2_text`.

**L1 prompt sentence** (`sentences.l1_prompts`), per pair, first rule that applies:

1. Range passage (`dt_passage.sentence_start/end` not null): load `test_sentences` rows
   `idx ∈ [start, end]` and their usable `test_sentence_references` (verdict `pass|rewritten`,
   active, the submission's `l1_language_id`) — the same query as
   `routes/dual_translation._get_usable_references`. If the row count equals
   `len(split_sentences(gold_l2))`, the L1 prompt for pair `i` is the join (`join_sentences`, L1
   code) of the L1 texts of every split reference sentence lying inside `[pair.ref.start,
   pair.ref.end)` (handles merged pairs).
2. Otherwise, the `dt_passage_reference.l1_text` for the submission's L1, split with
   `sentence_pairs.split_sentences`; if its count equals `len(split_sentences(gold_l2))`, the same
   positional join.
3. Otherwise `null`; the client then shows the whole L1 passage (`prompt_l1_passage`, sent once
   per session) clamped to two lines with tap-to-expand (R2.4 rule 3).

### 3.2 Eligibility and step planning (`planner.py`, pure)

Input: the persisted grade (`scores`, `grader_trace`), the submission's `dt_error_instance` rows
(read back after `_persist_grade`, with their `id`s), the sentence model, `age_tier`, hint
templates. Output: `{eligible, status, steps[], direct_items[]}`.

**Eligible** iff all hold:
- `DT_GUIDED_REPAIR` on;
- the grade is persisted (`overall_band` not null; a provisional unpersisted grade gets no session);
- `grader_trace.tier == 'single_call'` **or** `grader_trace.tier == 'tier0'` (exact / near-exact,
  no errors);
- every error row has a non-null `sentence_index` < `len(pairs)`;
- the hint templates loaded and validated at import (§5.2).

Not eligible → no session row, no `repair` key, full contract: today's behaviour.

**Flagged sentences** = distinct `sentence_index` over error rows (`is_mistake` rows included —
the grader does not set it on single-call grades).

**Clean**: no flagged sentences → session `status='finished'`, `n_steps=0`; response carries the
full contract and `repair.clean = true` (the sheet shows "No issues found").

**Bypass** (SPEC §1.5): flagged sentences ≥ `DT_REPAIR_BYPASS_FLAGGED`, or any value in `scores`
equals 1 → session `status='bypassed'`; one item per flagged sentence with `step_kind='direct'`,
`step_order=NULL`, `outcome='shown_directly'`, closed at once and queued (§7.1); response = full
contract + `repair.status='bypassed'`; the client shows today's result view (no sheet).

**Primary error of a sentence** — sort its errors by: severity rank (`critical` 3 > `major` 2 >
`minor` 1) desc; meaning type first (`meaning_inversion`, `contradiction`, `semantic_anomaly`,
`omission`, `addition`); confidence desc; local span start asc; `id` asc. First wins. The other
errors of the sentence are not separate steps; they are marked on the answer screen and the
re-check rule (§6.3) covers new major/critical errors.

**Step kind** of a flagged sentence:
- `unsure` — every error of the sentence has `confidence < DT_REPAIR_UNSURE_CONFIDENCE_MAX`;
- else the primary error's ladder (§5.1): `full` or `short` → candidate `repair` target; `none` →
  `direct`. Age tier 1–2: `full` becomes `short` (SPEC §1.4).

**Cap / selection** — repair candidates ranked by the primary error: severity desc, meaning type
first, confidence desc, sentence index asc. The first `DT_REPAIR_MAX_TARGETS` are `repair` steps;
the rest become `direct` steps (over the cap). Unsure steps are not counted against the cap.

**Order on screen** — all steps (`repair`, `unsure`, `direct`) in **passage order**
(`sentence_index` asc), `step_order` 0..n-1. Since flagged < 5, a pass has at most 4 steps.

**Location** of the primary error (`location_available`): true iff `span_source ∈ {exact,
normalised, fuzzy, diff_hunk}` **and** the local learner span is inside the sentence **and** its
width ≤ `DT_REPAIR_LOCATION_MAX_SHARE × len(learner_sentence)` (a zero-width span is allowed and is
sent as a *point*, §4.3). `span_source = 'sentence'` (sentence-level / unlocatable errors) → false.

**Rungs** (hint levels available, fixed semantics 1 where · 2 kind · 3 clue · 4 answer):

| ladder | location available | rungs |
|---|---|---|
| full | yes | `[1, 2, 3]` |
| full | no | `[2, 3]` (the "where" rung is removed, SPEC §1.5 "Location unknown") |
| short | yes | `[1]` |
| short | no | `[]` (hint button reads "Show answer" from the start) |
| none (`direct`) | — | `[]` |
| unsure | — | `[]`; the span is shown from the start if location available |

### 3.3 Submit hook (`hooks.py` + two edits in `routes/dual_translation.py`)

`after_grade(db, *, user_id, submission_row, passage, contract) -> dict` is called in `submit()`
**after** `_persist_grade` and `_persist_grading_assets`, and returns the dict to send. It never
raises: any exception is logged and the full contract is returned unchanged (no session).

1. Plan (§3.2). Not eligible → return `contract`.
2. Insert `dt_repair_session` (UNIQUE `submission_id`; on conflict re-read the existing row) and
   its items in one `insert(...)` call.
3. Clean / bypassed → `{**contract, 'repair': session_payload}`.
4. Open with steps → `redact(contract) | {'repair': session_payload}`.

`for_cached(db, user_id, submission_id, contract) -> dict` is called on the idempotent cached-grade
path of `submit()` (`_cached_grade` returned non-None): if a session exists and is `open` →
redacted contract + current session payload; if it exists and is closed → full contract + payload;
if none exists → `after_grade` semantics (creates it; covers a crash between grade and session).

`redact(contract)` returns `{scores, overall_band, provisional, target_words (if present),
errors: [], diff: [], highlights: [], redacted: true, n_errors: len(errors)}` — no
`grader_trace` (it holds the model's reference quotes and explanations), no error fields.

`_tokens_used_today` in `routes/dual_translation.py` is changed to
`return base + repair.budget.recheck_tokens_today(db, user_id)` so first grades see re-check spend
(the guardrail is unchanged otherwise).

These are the **only** edits to `routes/dual_translation.py`, and they are applied last, on top
of the concurrent grader agent's final version of that file (TASK-959).

## 4. API contract

Base path `/api/dual-translation/repair`. All endpoints: `Authorization: Bearer <jwt>`
(`middleware.auth.jwt_required`), JSON in/out, success shape `{"status":"success", ...fields}`
(fields spread at top level, `utils.responses.api_success`), error shape
`{"status":"error","error":"<message>","error_code":"<CODE>"}`.

Common errors on every endpoint: 401 (no/invalid token), 503 `REPAIR_DISABLED` (flag off),
404 `NOT_FOUND` (id does not exist), 403 `NOT_OWNER` (row's `user_id` ≠ token user), 400
`BAD_REQUEST` (validation; message names the field), 429 (rate limit, §9.3), 500 (unexpected;
logged).

`surface` is `"repair_pass"` or `"daily_practice"` wherever it appears. Every action body may
carry `since_prev_ms` (int, ms since the learner's previous action on this item; clamped to
0..3,600,000; stored on the event).

### 4.1 `POST /api/dual-translation/<submission_id>/submit` (existing; response extended)

Request unchanged. Response, by case:

| Case | Body |
|---|---|
| not eligible / flag off / hook error | today's full contract, **no `repair` key** |
| clean | full contract + `"repair": {…session, "status":"finished", "clean":true, "steps":[]}` |
| bypassed | full contract + `"repair": {…session, "status":"bypassed", "steps":[]}` |
| open | redacted contract (§3.3) + `"repair": {…session, "status":"open"}` |

Idempotency: unchanged (`dt_grade.submission_id` UNIQUE). A re-submit returns the same session
(§3.3 `for_cached`).

### 4.2 Session payload (shared shape)

```json
{
  "session_id": 501,
  "submission_id": 9001,
  "status": "open",
  "clean": false,
  "surface": "repair_pass",
  "l1": "zh",
  "l2": "en",
  "n_sentences": 4,
  "n_clean": 2,
  "prompt_l1_passage": "这是一个在实践中学习的好方法。…",
  "auto_advance_ms": 1600,
  "steps": [ <Step>, ... ],
  "summary": null
}
```

`n_clean` = `n_sentences − flagged sentences`. `summary` is non-null once finished (§4.9 shape).

**Step** (also used for daily items, §4.10):

```json
{
  "item_id": 7001,
  "position": 0,
  "sentence_index": 0,
  "step_kind": "repair",            // "repair" | "unsure" | "direct"
  "ladder": "full",                 // "full" | "short" | "none"
  "prompt_l1": "这是一个在实践中学习的好方法。",   // or null (§3.1 rule 3)
  "learner_sentence": "It's a sick way to learn by doing.",  // the ORIGINAL submitted sentence
  "hint_rungs": [1, 2, 3],
  "hint_level": 0,                  // current level this sitting (0 = none taken; 4 = answer shown)
  "where": null,                    // Where object when hint_level >= 1 and rung 1 exists, or unsure with location
  "last_text": null,                // latest CHECKED text this sitting (resume), else null
  "checks_used": 0,                 // still_flagged results this sitting
  "check_cap": 4,
  "state": "open",                  // "open" | "closed"
  "outcome": null,                  // when closed: see §5.5 outcome enum
  "from_date": null                 // daily items only: learner-local ISO date of the original submission
}
```

**Never in a Step**: reference sentence, `corrected_form`, `span_reference`, subtype, kind label,
clue, explanation, other errors.

**Where object**: `{"start": 7, "end": 11, "text": "sick", "point": false}` — offsets into the
text the learner currently has in the field (the original sentence before any check, the
`last_text` after a check that returned a fresh span). `point: true` means a zero-width position
(an omission): `start == end`, `text == ""`; the client draws an insertion mark (§8.4).

### 4.3 `GET /repair/submissions/<submission_id>/session`

Read / resume. 200 → `{"session": <§4.2 payload>}`. 404 `NO_SESSION` when the submission has none
(client then shows today's view). If the session is `open` and older than
`DT_REPAIR_SESSION_STALE_HOURS`, it is finished as `abandoned` first (§7.4) and returned closed.

### 4.4 `POST /repair/items/<item_id>/open`

Body `{"surface": "repair_pass"|"daily_practice", "since_prev_ms"?: int}`.

- repair_pass: session must be `open` (else 409 `SESSION_CLOSED`), item `open` (else 409
  `ITEM_CLOSED`). Sets `opened_at` if null (idempotent). Event `step_opened` (first time only).
- daily_practice: item must be `queue_status='due'` and due now (§7.2) (else 409 `NOT_DUE`). If
  no sitting is in progress (`sitting_open=false`), starts one: `sitting += 1`,
  `hint_level = 1 if 1 in rungs else 0`, `checks_used = 0`, `calls_used = 0`, `active` reset to the
  original primary error, `sitting_open=true`, `opened_at=now()`; event `step_opened`. If a sitting
  is in progress and was opened < 2 h ago, resume it (no event). Older → close it as `skipped` and
  start a new one.

200 → `{"step": <Step>}` (with `where` filled when `hint_level ≥ 1`).

### 4.5 `POST /repair/items/<item_id>/hint`

Body `{"surface": ..., "expected_level": int, "since_prev_ms"?: int}`. `expected_level` is the
level the client is asking for (the next rung it believes is due).

Server: next rung = first `r` in `hint_rungs` with `r > hint_level`. If none → 409
`NO_MORE_HINTS` (client must call reveal). If `expected_level ≤ hint_level` (double tap / retry) →
return the hint for the current `hint_level` without changing anything. Else set `hint_level = r`,
write event `hint_shown` and return:

```json
{
  "item_id": 7001,
  "hint_level": 2,
  "hint_number": 2,           // 1-based position of this rung in hint_rungs
  "hint_total": 3,            // len(hint_rungs)
  "hint": {
    "type": "kind",           // "where" | "kind" | "clue"
    "text": "Register — how formal it sounds",   // null for "where" (client string dt_repair.hint_where)
    "lang": "en"              // BCP-47 primary code of `text` (learner L1); null for "where"
  },
  "where": {"start": 7, "end": 11, "text": "sick", "point": false},  // present whenever hint_level >= 1 and rung 1 exists
  "next": "hint"              // "hint" if another rung remains, else "answer"
}
```

What the client is and is not sent, per level:

| Level | Sent | Not sent |
|---|---|---|
| 0 (none) | learner's own sentence, L1 prompt | everything else |
| 1 where | + Where object (offsets + the learner's own words) | subtype, label, clue, any reference text |
| 2 kind | + the kind label in L1 (template or taxonomy gloss head, §5.3) | clue, reference text |
| 3 clue | + clue text (template rendered with the learner's own words, leak-filtered, §5.4) | reference text, corrected form |
| 4 answer | only via reveal / check auto-reveal / dispute (§4.7–4.8) | — |

### 4.6 `POST /repair/items/<item_id>/check`

Body:
```json
{"surface": "repair_pass", "text": "It's a great way to learn by doing.",
 "client_check_id": "1b0c5f3e-…-uuid", "since_prev_ms": 5300, "first_edit_ms": 1200,
 "active_ms": 41000, "client_event_id": "uuid"}
```
`client_check_id` (uuid v4, required) — idempotency key: a replay with the same id returns the
stored result without a new call (UNIQUE `(item_id, client_check_id)`). `first_edit_ms` (ms from
step shown to first keystroke, first check of a sitting only; optional). `active_ms` +
`client_event_id` (optional; daily practice credits study time when the call closes the sitting,
§7.5).

Validation (400 `BAD_REQUEST`): `text` string; after normalisation (NFC, `\r\n|\n|\t` → space,
collapse runs of spaces, trim) non-empty, ≤ `DT_REPAIR_TEXT_MAX_CHARS` and ≤ `2 × len(original) +
40` (else 400 `TEXT_TOO_LONG`). Item must be open (409 `ITEM_CLOSED`); repair_pass needs an open
session; daily needs a sitting in progress (409 `NOT_OPENED`, call open first).

Server steps:
1. **Lock**: `UPDATE dt_repair_item SET check_lock_until = now() + interval '15 s' WHERE id = :id
   AND (check_lock_until IS NULL OR check_lock_until < now())` (PostgREST `.update().eq().or_()`;
   0 rows → 409 `CHECK_IN_PROGRESS`). Released (set null) at the end, in `finally`.
2. **Unchanged**: normalised text equals the normalised `last_text` (or the original sentence if
   no check yet this sitting) → `result: "unchanged"`, no call, no event, `checks_used` unchanged.
3. **Budget** (§9.3): `calls_used ≥ DT_REPAIR_MAX_CALLS_PER_SITTING`, or
   `budget.recheck_allowed(user)` false → close the item with outcome `answer_shown`
   (`answer_reason = 'budget'`), event `answer_shown`, `result: "budget_exhausted"`,
   `closed: true`, with `answer`.
4. **Tier-0 shortcut**: `tier0._normalize_l2(text, l2) == tier0._normalize_l2(reference_sentence, l2)`
   → `result: "fixed"` without a call (`latency_ms = 0`, no tokens).
5. Else `recheck.recheck_sentence(...)` (§6), `calls_used += 1`.
   - status not `ok` → `result: "error"`, `reason: "timeout"|"call_failed"`, event
     `revision_checked` with `result='error'` (text stored), item stays open, `checks_used`
     unchanged.
   - status `ok` → `classify.classify(...)` (§6.3).
6. Write event `revision_checked` (text, result, compact result detail, latency, tokens, cost,
   model, prompt version). Update item: `last_text = text`, `active` (when a new active error),
   `checks_used += 1` on `still_flagged`, `n_checks += 1`.
7. **Close** when: `fixed` → outcome `self_repaired` (unsure step: `unsure_revised`);
   `no_issue_found` → `repaired_alternative` (unsure: `unsure_revised`); `still_flagged` and
   `checks_used ≥ check_cap` → `answer_shown` with `answer_reason='auto_cap'`, `hint_level = 4`,
   events `revision_checked` then `answer_shown`.

Response:
```json
{
  "item_id": 7001,
  "result": "still_flagged",      // fixed | no_issue_found | still_flagged | unchanged | error | budget_exhausted
  "reason": "target_present",     // still_flagged: target_present | new_error; error: timeout | call_failed; else null
  "checks_used": 2,
  "check_cap": 4,
  "hints_used": 1,                // rungs taken this sitting (hint_level mapped to count of rungs <= level)
  "where": {"start": 7, "end": 11, "text": "sick", "point": false},  // still_flagged AND (hint_level >= 1 with rung 1, or unsure) AND location available; else null
  "closed": false,
  "outcome": null,                // when closed: self_repaired | repaired_alternative | answer_shown | unsure_revised
  "auto_reveal": false,           // true when closed by the check cap
  "answer": null                  // Answer object (§4.7) when result is no_issue_found, auto_reveal, or budget_exhausted
}
```

`fixed` deliberately carries no `answer` (the success moment is a beat, R2.3); the full result
screen shows it later.

Latency handling: the request is synchronous; p50 ≈ 1.4 s, p90 ≈ 2.1 s (prod_check v2 grades;
a single sentence is shorter). Server timeout `DT_REPAIR_RECHECK_TIMEOUT_S` (5 s); the client
aborts at 7 s (§8.9). No fallback model on re-check (it would double the worst-case latency).

### 4.7 `POST /repair/items/<item_id>/reveal`

Body `{"surface": ..., "reason": "asked"|"grader_failed"|"direct", "since_prev_ms"?, "active_ms"?, "client_event_id"?}`.

- `asked` — "Show answer" tapped. `grader_failed` — client gave up after 2 consecutive `error`
  checks or 2 failed hint/reveal requests. `direct` — a `direct` step being displayed.
- Open item → close with outcome `answer_shown` (`direct` → `shown_directly`), `hint_level = 4`,
  `answer_reason = reason`, event `answer_shown`. Already closed → return the answer for the
  closed item (idempotent; no new event). Repair pass with session not open → still allowed for
  items already closed (resume), 409 `SESSION_CLOSED` for open items.

Response `{"item_id": 7001, "closed": true, "outcome": "answer_shown", "answer": <Answer>}`.

**Answer object**:
```json
{
  "heading": "compare",                   // "compare" | "no_issue" | "disputed"
  "learner_sentence": "It's a sick way to learn by doing.",   // ORIGINAL submitted sentence ("You wrote")
  "learner_marks": [[7, 11]],             // local spans of every error of the sentence with a locatable span, merged, sorted
  "answer_sentence": "It's a great way to learn by doing.",   // reference sentence ("Answer")
  "answer_marks": [[7, 12]],              // local span_reference of those errors, merged, sorted
  "explanation": "“Sick” for “very good” is slang; neutral writing uses “great”.",
  "explanation_lang": "en",               // learner L1 code
  "l2": "en"
}
```
- `heading`: `no_issue` when the item closed `repaired_alternative`; `disputed` when closed
  `disputed`; else `compare`.
- Marks: an error whose `correction_source = 'reference_sentence'` contributes no mark on either
  side (the whole sentence differs); if no error has a mark, both lists are `[]` and the client
  renders the two sentences unmarked.
- `explanation` (primary error): `model_note` when `explanation_source = 'model'` (the grader's own
  L1 explanation, ≤ 240 chars), else the template `explanation` (rule text). Trimmed to its first
  sentence if longer than 160 chars; never empty (falls back to the kind label).

### 4.8 `POST /repair/items/<item_id>/dispute`

Body `{"surface": ..., "since_prev_ms"?, "active_ms"?, "client_event_id"?}`. "Mine is fine".

- `unsure` step → outcome `unsure_dismissed`, response `{"closed": true, "outcome":
  "unsure_dismissed", "answer": null}` (client shows "Kept as written").
- otherwise → outcome `disputed`, event `disputed`, response with `answer` (`heading: "disputed"`).
  Daily practice: `queue_status = 'disputed'` (removed from practice).
- Already closed → idempotent, returns the stored outcome (+ answer when applicable).

### 4.9 `POST /repair/sessions/<session_id>/finish`

Body `{"closed_early": bool, "active_ms"?: int, "client_event_id"?: uuid}`.

Closes every still-open item: `unsure` → `unsure_skipped`; others → `skipped` (event `skipped`).
Applies the queue rule (§7.1) to every item, sets `status='finished'`, `finished_at`, `total_ms`
(server: `finished_at − created_at`), credits repair time (§7.5). Idempotent: a second call returns
the same summary.

Response:
```json
{"status": "success", "session_id": 501, "session_status": "finished",
 "summary": {"fixed_yourself": 1, "needed_help": 1, "saved_to_practice": 1},
 "result_available": true}
```
(`session_status`, not `status`: the envelope's top-level `status` is `"success"`.)
`fixed_yourself` = items with outcome `self_repaired` or `repaired_alternative`;
`needed_help` = outcome `answer_shown`; `saved_to_practice` = items queued by §7.1 (includes
`shown_directly` and `skipped`).

### 4.10 `GET /repair/submissions/<submission_id>/result`

The full grade contract, exactly as `routes/dual_translation._cached_grade` builds it. 409
`REPAIR_IN_PROGRESS` while the submission's session is `open`. 404 when the submission has no
persisted grade. Ownership checked on `dt_submission.user_id`.

### 4.11 Daily practice

`GET /repair/practice/due?language_id=<int>` → up to `DT_REPAIR_DAILY_ITEMS` due items for that L2
(§7.2 selection), each a Step (§4.2) with `surface: "daily_practice"`, `check_cap:
DT_REPAIR_CHECK_CAP_DAILY`, `from_date` set, `hint_level` as it would be after open (1 if rung 1
exists, else 0) and `where` filled accordingly, `state: "open"`, plus `"total_due": int` (all due
items, for "N more tomorrow" copy if wanted). Read-only: it does not start sittings.

`POST /repair/items/<item_id>/skip` — body `{"surface": "daily_practice", "since_prev_ms"?}`.
Closes the sitting with event `skipped` (episode outcome `skipped`); `due_on` = tomorrow (learner
local), not counted as failed. repair_pass items are skipped only via finish (400 if surface is
repair_pass).

Daily-practice item actions are the same open / hint / check / reveal / dispute endpoints with
`surface: "daily_practice"`. A sitting is closed by: check `fixed`/`no_issue_found`, auto reveal,
reveal, dispute, skip, or budget. On close, §7.3 sets the next state.

### 4.12 Fixtures (normative examples for WP-FE stubs)

WP-FE puts these in `tests/unit/fixtures/dt-repair/` (§10). They follow the shapes above exactly.

`submit_open.json` — redacted submit with two repair steps:
```json
{"status":"success","scores":{"accuracy":3,"fidelity":2,"understandability":3},"overall_band":3,
 "provisional":false,"errors":[],"diff":[],"highlights":[],"redacted":true,"n_errors":2,
 "repair":{"session_id":501,"submission_id":9001,"status":"open","clean":false,"surface":"repair_pass",
  "l1":"zh","l2":"en","n_sentences":4,"n_clean":2,"auto_advance_ms":1600,
  "prompt_l1_passage":"这是一个在实践中学习的好方法。Arduino 是做 DIY 项目的强大工具。你可以用它做很多东西。这个机械臂只是其中一个想法。",
  "summary":null,"steps":[
   {"item_id":7001,"position":0,"sentence_index":0,"step_kind":"repair","ladder":"full",
    "prompt_l1":"这是一个在实践中学习的好方法。","learner_sentence":"It's a sick way to learn by doing.",
    "hint_rungs":[1,2,3],"hint_level":0,"where":null,"last_text":null,"checks_used":0,"check_cap":4,
    "state":"open","outcome":null,"from_date":null},
   {"item_id":7002,"position":1,"sentence_index":2,"step_kind":"repair","ladder":"short",
    "prompt_l1":"你可以用它做很多东西。","learner_sentence":"You can make many things without it.",
    "hint_rungs":[1],"hint_level":0,"where":null,"last_text":null,"checks_used":0,"check_cap":4,
    "state":"open","outcome":null,"from_date":null}]}}
```
`hint_where.json`: `{"status":"success","item_id":7001,"hint_level":1,"hint_number":1,"hint_total":3,"hint":{"type":"where","text":null,"lang":null},"where":{"start":7,"end":11,"text":"sick","point":false},"next":"hint"}`
`hint_kind.json`: as above with `"hint_level":2,"hint_number":2,"hint":{"type":"kind","text":"Register — how formal it sounds","lang":"en"}`.
`hint_clue.json`: `"hint_level":3,"hint_number":3,"hint":{"type":"clue","text":"One word here is casual slang. The passage is plain, neutral writing.","lang":"en"},"next":"answer"`.
`check_still.json`: `{"status":"success","item_id":7001,"result":"still_flagged","reason":"target_present","checks_used":1,"check_cap":4,"hints_used":1,"where":{"start":7,"end":11,"text":"cool","point":false},"closed":false,"outcome":null,"auto_reveal":false,"answer":null}`
`check_fixed.json`: `{"status":"success","item_id":7001,"result":"fixed","reason":null,"checks_used":1,"check_cap":4,"hints_used":1,"where":null,"closed":true,"outcome":"self_repaired","auto_reveal":false,"answer":null}`
`check_alt.json`: `result":"no_issue_found"`, `"outcome":"repaired_alternative"`, `"answer"` with `"heading":"no_issue"`.
`check_auto_reveal.json`: `"result":"still_flagged","checks_used":4,"closed":true,"outcome":"answer_shown","auto_reveal":true,"answer":{…"heading":"compare"}`.
`check_error.json`: `{"status":"success","item_id":7001,"result":"error","reason":"timeout","checks_used":0,"check_cap":4,"hints_used":0,"where":null,"closed":false,"outcome":null,"auto_reveal":false,"answer":null}`
`reveal.json`: `{"status":"success","item_id":7002,"closed":true,"outcome":"answer_shown","answer":{"heading":"compare","learner_sentence":"You can make many things without it.","learner_marks":[[25,35]],"answer_sentence":"You can make many things with it.","answer_marks":[[25,32]],"explanation":"“Without” says the opposite of the prompt (用它 = with it).","explanation_lang":"zh","l2":"en"}}`
`finish.json`: `{"status":"success","session_id":501,"session_status":"finished","summary":{"fixed_yourself":1,"needed_help":1,"saved_to_practice":1},"result_available":true}`
`session.json` (§4.3): `{"status":"success","session":{…the §4.2 object…}}`
`practice_due.json`: `{"status":"success","total_due":2,"items":[{"item_id":8101,"position":0,"sentence_index":1,"step_kind":"repair","ladder":"full","prompt_l1":"你可以学到机器人和电子方面的知识。","learner_sentence":"You can learn on robotics and electronics.","hint_rungs":[1,2,3],"hint_level":1,"where":{"start":8,"end":16,"text":"learn on","point":false},"last_text":null,"checks_used":0,"check_cap":3,"state":"open","outcome":null,"from_date":"2026-11-10"}]}`

**Envelope rule (binding):** every response is an `api_success` dict (top-level
`"status":"success"` plus the fields shown). The §4.2 session object is always nested — under
`"repair"` in §4.1, under `"session"` in §4.3 — so its own `status` field keeps its name. The only
rename is §4.9's top-level `session_status`. Everything else is exactly as shown.

## 5. Ladder content

### 5.1 Ladder kind per v6 subtype (in `hint_templates.json`, `subtypes.<slug>.ladder`)

From SPEC §1.4, completed for every v6 slug (40):

| ladder | subtypes |
|---|---|
| full | measure_word, aspect_negation, de_particle, ba_bei, complement, coverb, separable_verb, wa_ga, case_particle, particle_other, conjugation, tam, counter, transitivity_voice, keigo, article_determiner, agreement, verb_form_tense, plural_number, preposition, complementation, pronoun, modification, clause_linkage, connective, cohesion_connective, word_order, register, omission, addition |
| short | meaning_inversion, contradiction, semantic_anomaly, topic_comment, orthography |
| none | word_choice, collocation, kanji_choice, lexical_form, phrasal_verb |

Additions beyond SPEC §1.4 (it did not list them): the rule-governed slugs above → full;
`topic_comment` → short (Track D: its templates were weak because the type covers several
different mistakes); `orthography` → short (the location is the useful hint for a spelling slip).
A slug missing from the file → `short` and a warning logged once.

### 5.2 Where templates live in production

`services/dual_translation/repair/hint_templates.json`, versioned in git:

```json
{
  "version": "repair-hints/2026-11-14.1",
  "source": "data/eval/dt_decision_2026-11-14/track_d/templates.json (G0, AI-drafted, not native-reviewed)",
  "limits": {"clue_max_latin": 120, "clue_max_cjk": 60, "label_max": 48},
  "type_neutral": {
    "en": "Read your sentence against the prompt, part by part. Where does it say something different?",
    "zh": "把你的句子和原文一部分一部分地对照，哪里说的不一样？",
    "ja": "原文と自分の文を少しずつ比べてみましょう。どこが違うことを言っていますか。"
  },
  "subtypes": {
    "register": {"ladder": "full", "l1": {
      "en": {"label": "Register — how formal it sounds", "clue": "…{l}…"},
      "zh": {"label": "…", "clue": "…"}, "ja": {"label": "…", "clue": "…"}}},
    "...": {}
  }
}
```

- Built once by the BE agent from Track D `templates.json`: `label` ← `per_type[slug][l1].label`,
  `clue` ← `per_type[slug][l1].hint` (the elicitation style: 0% leaks in Track D; the `meta` style
  is not used because its closed-class rules list the answer among the options). `{l}` is the only
  placeholder kept; `{c}` must not appear anywhere in the file (test).
- Coverage today: L1 `en` for all 40 slugs; `zh`/`ja` only for the 20 English-L2 slugs. Missing
  (slug, L1) is filled at run time (§5.3), not invented in the file.
- Not in `dt_taxonomy_version`: changing hint copy must not bump the taxonomy (prompt-cache
  prefix stability) and hints are UI content, not grading config.
- Any edit to a `label` or `clue` bumps `version`. Events store `hint_template_id`
  (`"<slug>.<l1>.<kind|clue>"` or `"type_neutral.<l1>"` or `"gloss.<slug>.<l1>"`) and the session /
  item stores `hint_version`, so the shown text is reproducible without storing it.
- Validated at import (`hints.load()`): JSON parses, every ladder value valid, every clue within
  `limits` after replacing `{l}` with a 6-character stand-in (CJK limit applies when the L1 is zh/ja),
  no `{c}`. Invalid file → the feature is ineligible for every submission (logged once), never a
  crash.

### 5.3 Rendering

- **where** — the primary error's local span in the current text: at level 1 from the original
  span; after a check that returned `still_flagged` with a locatable active error, from that
  error's span in `last_text`. `point = (start == end)`.
- **kind** — `subtypes[slug].l1[L1].label`; else the taxonomy gloss head for that L1
  (`dt_taxonomy_version.taxonomy.subtype_glosses[slug][L1]` up to the first ` — ` / `——` / `—`,
  read via `grader_cascade.get_active_taxonomy(db)`), `hint_source='taxonomy_gloss'`; else the
  English label with `lang:'en'`.
- **clue** — `subtypes[slug].l1[L1].clue` with `{l}` = the active error's learner form in the
  current text; if the template contains `{l}` and that form is empty (point span) or not found in
  the current text, or there is no template for (slug, L1): `type_neutral[L1]`
  (`hint_source='type_neutral'`; L1 outside en/zh/ja → `en`). Then the leak filter (§5.4); a leak →
  `type_neutral[L1]` with `leak_blocked: true` in the event detail.
- L1 = the submission's `l1_language_id` code (the learner's native language), not the UI language.

### 5.4 Leak filter (`hints.leaks(text, learner_form, corrected_form, l2_code) -> bool`)

From Track D (agreed with the better judge at κ = 0.74): normalise all three with
`tier0._normalize_l2(…, l2_code)`; strip from `corrected_form` the longest common prefix and suffix
it shares with `learner_form`; if the remaining fragment is non-empty, occurs in the normalised
text, and does not occur in the normalised `learner_form` → leak. Applied to `clue` only (labels of
closed-class types legitimately list the options, e.g. "Aspect marker (了 / 过 / 着)"). With a
`reference_sentence` correction, the fragment is computed against the whole reference sentence.

### 5.5 Enums

- `outcome` (item / episode): `self_repaired`, `repaired_alternative`, `answer_shown`,
  `shown_directly`, `disputed`, `skipped`, `unsure_revised`, `unsure_dismissed`, `unsure_skipped`.
- `answer_reason`: `asked`, `auto_cap`, `grader_failed`, `budget`, `direct`.
- `queue_status`: `none`, `due`, `resolved`, `retired`, `expired`, `disputed`.
- event `kind`: `step_opened`, `hint_shown`, `revision_checked`, `answer_shown`, `disputed`,
  `kept`, `skipped`, `episode_closed`.
- event `result` (on `revision_checked`): `fixed`, `no_issue_found`, `still_flagged`, `error`.
- `hint_source`: `grader_span`, `template`, `taxonomy_gloss`, `type_neutral`.

## 6. Re-check

### 6.1 `recheck.recheck_sentence`

```python
def recheck_sentence(db, *, reference_sentence: str, revised_sentence: str, l2_code: str,
                     l1_code: str, l2_language_id: int, l1_language_id: int,
                     timeout_s: float = settings.DT_REPAIR_RECHECK_TIMEOUT_S) -> dict
```

Returns:
```python
{"status": "ok" | "call_failed" | "timeout" | "malformed" | "unsupported",
 "errors": [ {"subtype", "severity", "model_severity", "confidence", "confidence_label",
              "span": [s, e],            # into revised_sentence
              "learner_form", "corrected_form", "correction_source", "span_source",
              "model_note"} ],
 "model": str, "prompt_version": str, "prompt_variant": str,
 "tokens": {"in": int, "out": int, "cached": int|None}, "cost_usd": float|None,
 "latency_ms": int}
```

Implementation — reuse, do not fork, the grader (module `services/dual_translation/repair/recheck.py`
imports from `single_call_grader` / `single_call_prompts`; it does not edit them):

1. `sc_prompts.supports(l2_code)` else `unsupported`. Load taxonomy and subtypes exactly as the
   cascade does (`grader_cascade.get_active_taxonomy`, `_resolve_subtypes(taxonomy, l1, l2)`); if
   `TYPE_IDS[l2]` ≠ subtypes → `unsupported`.
2. `pairs = build_sentence_pairs(reference_sentence, revised_sentence).pairs` (usually one pair;
   a sentence containing internal delimiters yields several — fine).
3. `system = sc_prompts.build_system_prompt(l2, free_translation=Config.DT_SINGLE_CALL_FREE_TRANSLATION,
   band_descriptors="")`, `user = sc_prompts.build_user_prompt(pairs, l1, l2)`,
   `schema = sc_prompts.response_schema(l2)`. Same prompt as grading (same `PROMPT_VERSION`), so
   re-check detection is the measured detector; the naturalness/range judgments it also returns
   are ignored.
4. One attempt with the **primary** model only: `single_call_grader._attempt("primary",
   Config.DT_SINGLE_CALL_MODEL, system, user, schema)` with the timeout (pass `timeout_s` through
   `call_structured`'s `timeout` — `_attempt` currently does not forward it; recheck calls
   `call_structured` directly and mirrors `_attempt`'s parsing if `_attempt` gains no timeout
   parameter: see §11 item 6). Timeout → `timeout`; other exception → `call_failed`;
   `malformed_json`/`malformed_shape` → `malformed`.
5. Decode with `single_call_grader._decode(gc, payload["errors"], pairs=pairs, type_ids=…,
   subtypes=…, taxonomy_cfg=…, subtype_meta=…, severity_rule=SEVERITY_RULES[slug][l2] or default,
   l1_code, l2_code, gold_l2=reference_sentence, reproduction=revised_sentence)`. Low-confidence
   entries are withheld exactly as in grading. Map each decoded error to the dict above
   (`span = span_reproduction`).
6. Observability: an `llm_calls` row only when status ≠ ok (task `dt_repair_recheck`, raw response
   ≤ 4000 chars), via `services.llm_service._log_llm_call` — the event row already holds model,
   tokens, cost, latency for successful calls (frugality, §9.1).

Cost: one call ≈ the grade's input (~2.0k tokens, mostly the cached system prompt) and ~60–120
output tokens: about $0.00006–0.00009 (prod_check v2 median grade $0.000093).

### 6.2 What is re-checked

Only the revised sentence against its reference sentence (the pair's `ref` slice). The rest of the
passage is not re-graded and the grade is never updated.

### 6.3 Classification (`classify.classify`, pure)

Inputs: `active` (the item's current target: `{subtype, severity, form, start, end,
corrected_form, correction_source}` — initially the primary error with local offsets), the revised
text, the reference sentence, the re-check errors, `l2_code`.

1. Locate the target in the revised text: occurrences of `active.form` (normalised compare);
   choose the one nearest `active.start`; none (or empty form) → not located.
2. **target_present** iff some re-check error has `subtype == active.subtype`, or its span
   overlaps the located target position.
3. **new_serious** = re-check errors that are not the target match and have applied severity in
   {`major`, `critical`}.
4. Result:
   - target_present → `still_flagged`, `reason='target_present'`; the new `active` = the matching
     error (subtype, severity, form, span, corrected_form).
   - else new_serious non-empty → `still_flagged`, `reason='new_error'`; new `active` = the most
     severe new error (same ordering as §3.2). Later kind/clue hints use the new active subtype; the
     hint level is kept.
   - else if the normalised revised text contains the normalised `active.corrected_form` (or, for
     `correction_source='reference_sentence'`, equals the normalised reference sentence) → `fixed`.
   - else → `no_issue_found`.
   "Fixed" therefore means exactly: the originally flagged error is no longer present in that
   sentence AND no new major/critical error, with the corrected form present. `no_issue_found` is
   the same minus the corrected-form match (a valid alternative); both close the item as repaired.
   Remaining minor errors do not block either.
5. `where` for the response: the new `active` span if `still_flagged`, location available (§3.2
   rule on width, `span_source ≠ 'sentence'`) and (`hint_level ≥ 1` with rung 1, or unsure).

Compact result detail stored on the event (`result_detail` jsonb): `{"r": reason|null,
"e": [[subtype, severity, start, end, conf_label], …≤5], "x": model_note of the active error
≤ 240 chars | absent}`.

## 7. Daily practice integration

### 7.1 What gets queued (exact rule; confirmed against SPEC §8.1 and R2.2)

At item close in the **repair pass** (and for bypass items at creation), `queue_status := 'due'`
iff `step_kind ≠ 'unsure'` and one of:
- outcome `answer_shown` (any `answer_reason`) or `shown_directly` or `skipped`;
- outcome `self_repaired` or `repaired_alternative` with `max_hint_level ≥ 2` (needed "what kind"
  or "clue").

Not queued: fixed with `max_hint_level ≤ 1`, `disputed`, every `unsure_*`. (SPEC §8.1 and this rule
agree; "errors not self-repaired at hint level ≤ 1".) Each queued item keeps `max_hint_level`
(ordering) and `queued_at`. `due_on` = learner-local today + 1 day, `not_before` = close time +
`DT_REPAIR_FIRST_DUE_MIN_HOURS`, `expires_at` = `queued_at` + `DT_REPAIR_EXPIRY_DAYS`.
Learner-local today = `services.day_boundary.plan_today_iso(db, user_id, l2_language_id)`.

### 7.2 Selection

Due items for (user, L2): `queue_status='due' AND due_on <= local_today AND not_before <= now()
AND expires_at > now()`, excluding items whose submission is the one in an `open` repair session
(SPEC "not served while on the same passage"). Before selecting, expired rows
(`expires_at <= now()`) are set `queue_status='expired'` in the same request (cheap, indexed).
Order: meaning-changing subtype first, then `max_hint_level` desc (4 first), then `queued_at` asc.
Limit `DT_REPAIR_DAILY_ITEMS`.

Scheduling is **not** FSRS: existing DT error cards (`dt_card`) use FSRS ratings 1–4, but SPEC §8
specifies fixed intervals and a resolution rule driven by hint level, which FSRS cannot express
without a rating mapping. Fixed rules live in `scheduling.py` (pure).

### 7.3 After a daily sitting closes (`scheduling.after_sitting`, pure)

| Sitting result | Next state |
|---|---|
| fixed / no_issue_found with `max_hint_level ≤ 1` this sitting | `resolved` (removed) |
| fixed / no_issue_found with level 2–3 | stays `due`, `due_on = today + DT_REPAIR_HINTED_RETURN_DAYS`; if this item already had a hinted fix sitting before, still `due` (the next unaided fix resolves it) |
| answer shown (asked, auto after 3 checks, grader failure, budget) | `failed_sittings += 1`; 1 → `due_on = today + 2`; 2 → `today + 4`; 3 (`DT_REPAIR_RETIRE_AFTER_FAILED`) → `retired` |
| disputed | `disputed` (removed; logged for grader QA) |
| skipped | stays `due`, `due_on = today + 1`, not counted |
| any, if `sitting ≥ DT_REPAIR_MAX_SITTINGS` and not resolved | `retired` |

SPEC §8.4 lists "2 days, then 4, then 7" and "retired after 3 such sittings"; both cannot hold, so
this spec uses 2, 4, retire (decision 9 in §12).

"Fixed" is decided by the same re-check (§6), so a valid alternative resolves an item.

### 7.4 Stale sessions

A session `open` for more than `DT_REPAIR_SESSION_STALE_HOURS` is finished as `abandoned` (open
items → `skipped`, queued per §7.1) lazily: on `GET …/session`, on `/practice/due` (for that
user's stale sessions, ≤ 5 per call), and on the next submit by that user. No cron.

### 7.5 Study time

- Repair pass: `finish` credits `clamp_active_ms('dual_translation', active_ms)` capped at 300 s,
  `source_table='dt_repair_session'`, `source_id=session_id` (dedupe by the ledger's UNIQUE).
- Daily: the call that closes a sitting credits up to 120 s, `source_table='dt_repair_event'`,
  `source_id=client_event_id` (required for credit; `services.study_time.parse_client_event_id`).
  Language = the item's `l2_language_id`.

### 7.6 In the daily session queue

Mechanism: the existing block pattern (`intro_reviews`, ADR-040), not a parallel queue.

- `services/study_session/queue.py`: constants `DT_REPAIR_BLOCK_ID = 'dt_repair'`,
  `DT_REPAIR_KIND = 'dt_repair'`; `dt_repair_status(targets, completed_blocks, enabled) -> 'off' |
  'done' | 'check'` (`off` when disabled or `'dual_translation' in excluded_modules`);
  `insert_dt_repair(queue, n_items, done)` places `{kind:'dt_repair', id:'dt_repair', items: n,
  is_completed: done}` immediately before the first `kind == 'dual_translation'` item, else before
  the first `practice` item, else at the end.
- `services/study_session/session.py`: `_session_reads` gains `dt_repair_due` (calls
  `repair.service.count_due(db, user_id, language_id, today)`) when status is `check`;
  `build_study_session` applies `with_dt_repair(queue, status, reads)` after `with_intro_reviews`;
  `complete_block` adds `DT_REPAIR_BLOCK_ID` to `extra_ids`.
- The block is part of `queue` (counts in progress, like `intro_reviews`); it credits no weekly
  counter (`surface_skill_for('dt_repair')` is None) — it is remediation, not a planned slot.
- Any failure counting → no block (logged), never a failed session.

Coexistence with `dt_card`: kept as is. `dt_card` drills subtype clusters promoted by the nightly
synthesis; repair items re-fix one specific sentence. No dedupe between them in this build (open
for TASK-940's measurement of transfer).

## 8. Frontend specification (WP-FE)

### 8.1 Files

| File | Change |
|---|---|
| `static/js/dt-repair-sheet.js` | NEW. Classic script (IIFE) exposing `window.DTRepairSheet` — same pattern as `dt-error-card.js`, because the standalone page is a classic script and session players are ES modules. |
| `static/css/dt-repair.css` | NEW. All sheet styles, scoped under `.dtr-` class prefix. Tokens from `static/css/styles.css` (`--surface`, `--text-primary`, …); defines `--dtr-field-border`, `--dtr-focus` with light and dark values (dark via the app's existing dark-theme selector). |
| `templates/dual_translation.html` | link `css/dt-repair.css` in `extra_css`; `<script src=js/dt-repair-sheet.js>` before `dual_translation.js`. |
| `templates/study_session.html` | link the CSS; `<script defer src=js/dt-repair-sheet.js>` next to `dt-error-card.js`. |
| `static/js/dual_translation.js` | after submit: branch on `repair` (§8.7). |
| `static/js/session/players/dual_translation.js` | after submit: branch on `repair` (§8.7). |
| `static/js/session/players/dt_repair.js` | NEW daily player (§8.8). |
| `static/js/session/player_registry.js` | `dt_repair` loader + `KIND_PLAYERS` + `KIND_MODULES`. |
| `static/js/session/controller.js` | `KIND_LABELS.dt_repair = ['session.dt_repair_heading', 'Fix your sentences']`. |
| `static/i18n/en.json`, `zh.json`, `ja.json` | keys of §8.6 (flat dotted keys; `es` falls back to `en` through `i18n-manager.js`). |

### 8.2 Public API of `DTRepairSheet`

```js
DTRepairSheet.open({
  mode: 'pass' | 'daily',
  session,            // §4.2 payload (pass) — or null for daily
  items,              // Step[] (daily) — or null for pass
  fetch: window.authFetch,     // injectable for tests
  returnFocus: HTMLElement,    // focus target after close (the Submit button / player root)
  onDone: (result) => {},      // pass: {summary, closedEarly}; daily: {completed: n, closedEarly}
}) -> { close() }
```
One sheet at a time; `open` while open closes the previous one first.

### 8.3 Structure and the no-scroll rule

```
<div class="dtr-scrim">  <section class="dtr-sheet" role="dialog" aria-modal="true" aria-labelledby="dtr-h">
  <header class="dtr-hd">  [× close button aria-label]  [progress dots + sr-only "Sentence 1 of 2"] </header>
  <div class="dtr-stage">  (one view)  </div>
  <footer class="dtr-act"> (≤ 2 quiet text buttons, one primary button) </footer>
  <div class="dtr-sr" aria-live="polite" role="status"></div>
</section></div>
```

- Phone (< 600 px wide): sheet `position: fixed; inset: 0; height: var(--dtr-vvh, 100dvh)`,
  following `visualViewport` (height and `offsetTop`) like the mockup's `vv()`, so the action bar
  rides above an open keyboard. ≥ 600 px: centred 420 px card, `max-height: min(760px, 100dvh − 48px)`,
  exercise behind `inert` and dimmed.
- Grid rows `auto 1fr auto`; `.dtr-stage { overflow: hidden; min-height: 0 }`. The body gets
  `overflow: hidden` while the sheet is open (restored on close).
- **Acceptance (no scroll):** at 390×844, 375×667 and 1280×800, light and dark, and with the
  visible height reduced to 500 and 340 px (keyboard simulation), in every view and state of §8.5:
  `document.scrollingElement.scrollHeight <= innerHeight`, no horizontal overflow, `scrollY == 0`,
  every visible element inside the sheet box and none behind the action area. `verify.cjs` is the
  reference; the implementation's equivalent is `tests/e2e/dt-repair/noscroll.cjs` (§8.10).
- Long sentences (R2.4): the field grows with its text; when the mirror overflows, step type
  20 → 18 → 16 → 15 px (classes `f1/f2/f3`); past that the field scrolls inside itself. Prompt
  clamped to 2 lines (`-webkit-line-clamp`); when clamped it becomes a button that opens the full
  prompt as an overlay on the sheet (tap/Enter/Escape closes). Answer view type steps 24 → 20 →
  17 → 15 px, then clamp with tap-to-expand per block. Keyboard open on a short phone (`kb` class:
  width < 600 and visible height < 560): prompt hidden; below 400 px visible height (`tight`): the
  label is visually hidden while a hint is showing (kept for screen readers).
- Test items: the three longest gold sentences (en 69 chars `en_clean_01`, zh 53 `zh_seed_14`,
  ja 82 `ja_seed_02`) — copy them from `mockup.html` `STRESS`.

### 8.4 The field

- `<label for="dtr-ta">` with the pencil icon and "Fix your sentence" (`unsure`: "This part may need
  another look"). Never placeholder text.
- `<div class="dtr-field" lang="{l2}">` containing an `aria-hidden` mirror div (draws the
  underline) under a `<textarea id="dtr-ta" rows="1" spellcheck="false" autocapitalize="off"
  autocomplete="off" autocorrect="off" enterkeyhint="done" aria-describedby="dtr-slot">`,
  pre-filled with `last_text ?? learner_sentence`. 20 px text (never below 16 px: iOS zoom),
  2 px border `--dtr-field-border` (≥ 3:1 on its surface), focus: 4 px solid ring `--dtr-focus` +
  coloured caret.
- Line breaks are stripped on input (one sentence). **Enter submits only when not composing**:
  `if (e.key === 'Enter' && !e.isComposing && e.keyCode !== 229) { e.preventDefault(); check(); }`;
  also track `compositionstart/compositionend` and ignore Enter until 1 tick after
  `compositionend` (Safari fires keydown after compositionend). No checking while typing.
- Underline: the `where` span is re-located on every `input` event by finding `where.text` in the
  current value (nearest occurrence to `where.start`); not found → no underline. A `point` span is
  drawn as an insertion mark (2 px vertical bar with a ▿ glyph, `aria-hidden`) at `start` until the
  value changes. Unsure steps use a dotted underline from the start. The underline is a bottom
  border plus tint, not wavy (CJK legibility); meaning also carried by the "Look at the underlined
  part." text.
- Focus: on pointer-fine devices the textarea is focused with the caret at the end when the fix
  view appears; on touch devices the label receives focus (`tabindex=-1`) so the keyboard does not
  cover the screen before the learner has read it.

### 8.5 State machine (matches mockup views 1:1)

Views (`data-view` on the sheet): `result`, `clean`, `fix`, `ok`, `kept`, `reveal` (heading
compare/disputed), `alt` (reveal with heading no_issue), `summary`; plus transient
`answer_loading` (spinner in the stage while reveal is fetched). `fix` has sub-states in `fieldState`:
`idle`, `checking`, `still`, `same`, `error`, and `hintLoading`.

| From | Event | Request | To |
|---|---|---|---|
| (open, pass) | `session.clean` | — | `clean` |
| (open, pass) | steps present | — | `result` (count = steps.length; label "to fix", or "to look at" if every step is `unsure`/`direct`; "The other {n_clean} look fine." hidden when n_clean = 0) |
| (open, daily) | — | — | `fix` for item 0 |
| result | Start | — | first open step |
| (enter step) | step_kind `direct` | reveal{reason:direct} | `answer_loading` → `reveal` |
| (enter step) | repair / unsure | open | `fix` (idle) |
| fix | type | — | idle (clears `still`/`same`/`error` slot message) |
| fix | Check / Enter, text unchanged vs last checked (client normalisation = §4.6) | none | `same` (slot "That's the same sentence. Change something first.", field shakes once) |
| fix | Check, changed | check | `checking`: primary shows spinner + "Checking…", textarea `readOnly`, quiet buttons disabled, second press ignored, sr "Checking" |
| checking | `fixed` | — | `ok` ("Fixed"; "On your own" if `hints_used == 0` (daily: "Without any more help"), else "With {n} hint(s)"); auto-advance after `auto_advance_ms` unless reduced motion or a pointer/keyboard interaction on the sheet in the meantime |
| checking | `no_issue_found` | — | `alt` (answer from response) |
| checking | `still_flagged`, not closed | — | `still` (slot "Still not quite. Try again, or take a hint." — "…Try again." when no rung left), shake, underline updated from `where`, focus back to field |
| checking | closed with `auto_reveal` or `budget_exhausted` | — | `reveal` |
| checking | `error` | — | `error` (slot "Couldn't check just now — try again."); 2nd consecutive error → primary button becomes "Show answer" (→ reveal{grader_failed}) |
| checking | network failure / 7 s client timeout / non-2xx | — | same as `error` (409 `CHECK_IN_PROGRESS` → keep spinner, retry once after 1 s with the same `client_check_id`) |
| checking | `unchanged` (server) | — | `same` |
| fix | quiet hint button ("Need a hint?" → "Another hint" → "Show answer") | hint{expected_level} or reveal{asked} | `hintLoading` → `fix` with the hint in the slot ("Hint n of N" small line + text with `lang`), replacing what was there; `next == 'answer'` relabels the button "Show answer"; `hint_rungs` empty → button reads "Show answer" from the start |
| fix (unsure) | "Mine is fine" | dispute | `kept` ("Kept as written", "We'll leave this one alone."), auto-advance as `ok` |
| fix (unsure) | text changed | — | "Check" becomes the filled primary button (both buttons equal weight before) |
| fix | "Mine is fine" | dispute | `reveal` heading "Noted. Compare:" |
| reveal / alt / ok / kept | Next ("Finish" on the last step) | — | next open step, or (pass) `summary` after finish, (daily) close + `onDone` |
| summary | Done | — | close; `onDone({summary})` |
| any | × / Escape (Escape first closes a full-text overlay if open) | pass: finish{closed_early:true}; daily: skip for the current item if open | close; `onDone({closedEarly:true})` |

Before showing `summary` the sheet calls finish and renders its `summary` counts ("Fixed
yourself", "Needed help", "Saved to practice"; daily: "Back in practice later"). If finish fails,
the summary shows counts computed client-side from outcomes and Done still works.

Answer view (`reveal`/`alt`): heading (`compare` → "Compare", `no_issue` → "No issue found.
Compare:", `disputed` → "Noted. Compare:"), then block **You wrote** (`learner_sentence` with each
`learner_marks` range in `<del>`: line-through + tint), then block **Answer** (`answer_sentence`
with `answer_marks` in `<b>`: bold + underline), stacked in that order, then the one-line
explanation (`lang = explanation_lang`). Both blocks `lang = l2`. Marking never by colour alone.

Progress dots: one per step, current one longer, done ones filled; sr-only "Sentence {i} of {n}".
Shown on step views only, and only when there is more than one step.

At most two quiet actions and one primary per view (unsure: two neutral buttons). At most three
text elements above the field (daily eyebrow, prompt, label).

### 8.6 i18n

UI chrome via `LinguaI18n` (`T(key, params, fallback)` in modules; `LinguaI18n.t` in the classic
script with the same fallback helper as `dt-error-card.js`), flat keys in `static/i18n/*.json`.
Server-provided texts (kind label, clue, explanation) are already in the learner's L1 and carry
their own `lang`; they are never passed through i18n.

Keys (en text; WP-FE writes zh and ja, marked unreviewed in the commit message):
`dt_repair.dialog_label` Feedback · `dt_repair.close` Close · `dt_repair.progress` Sentence {i} of
{n} · `dt_repair.result_fix_one` sentence to fix · `dt_repair.result_fix_many` sentences to fix ·
`dt_repair.result_look_one` sentence to look at · `dt_repair.result_look_many` sentences to look at
· `dt_repair.result_others_fine` The other {n} look fine. · `dt_repair.start` Start ·
`dt_repair.clean_title` No issues found · `dt_repair.clean_body` Nothing was flagged in your
translation. · `dt_repair.done` Done · `dt_repair.label_fix` Fix your sentence ·
`dt_repair.label_unsure` This part may need another look · `dt_repair.from_date` From your
translation on {day} · `dt_repair.prompt_more` Show the whole prompt · `dt_repair.tap_close` Tap to
close · `dt_repair.check` Check · `dt_repair.checking` Checking… · `dt_repair.hint_need` Need a
hint? · `dt_repair.hint_another` Another hint · `dt_repair.show_answer` Show answer ·
`dt_repair.mine_fine` Mine is fine · `dt_repair.hint_n_of` Hint {n} of {total} ·
`dt_repair.hint_where` Look at the underlined part. · `dt_repair.still` Still not quite. Try again,
or take a hint. · `dt_repair.still_last` Still not quite. Try again. · `dt_repair.same` That's the
same sentence. Change something first. · `dt_repair.check_failed` Couldn't check just now — try
again. · `dt_repair.hint_failed` Couldn't load a hint — try again. · `dt_repair.answer_failed`
Couldn't load the answer. · `dt_repair.retry` Try again · `dt_repair.skip_sentence` Skip this
sentence · `dt_repair.fixed` Fixed · `dt_repair.fixed_own` On your own ·
`dt_repair.fixed_no_more` Without any more help · `dt_repair.fixed_hints_one` With 1 hint ·
`dt_repair.fixed_hints_many` With {n} hints · `dt_repair.kept_title` Kept as written ·
`dt_repair.kept_body` We'll leave this one alone. · `dt_repair.compare` Compare ·
`dt_repair.compare_no_issue` No issue found. Compare: · `dt_repair.compare_disputed` Noted.
Compare: · `dt_repair.you_wrote` You wrote · `dt_repair.answer` Answer · `dt_repair.next` Next ·
`dt_repair.finish` Finish · `dt_repair.summary_title` All done · `dt_repair.summary_daily_title`
Practice done · `dt_repair.summary_fixed` Fixed yourself · `dt_repair.summary_help` Needed help ·
`dt_repair.summary_saved` Saved to practice · `dt_repair.summary_later` Back in practice later ·
`dt_repair.result_load_failed` Couldn't load your full feedback. · `session.dt_repair_heading` Fix
your sentences · `session.dt_repair_none` Nothing to fix today.

Day names for `from_date`: `Intl.DateTimeFormat(uiLang, {weekday: 'long'})` when the date is within
the last 6 days, else `{month: 'short', day: 'numeric'}`.

### 8.7 Coexistence with the current results view

The client does not read a flag; it reacts to the response:

- `repair` absent → today's flow (`renderResult(contract)` on the page; band screen in the session
  player). This is the fallback for flag off, ineligible grades and hook errors.
- `repair.status === 'bypassed'` → today's flow with the (full) contract.
- `repair.clean` → open the sheet (`clean` view); Done → today's result view with the (full)
  contract already in hand.
- `repair.status === 'open'` (`redacted: true`) → open the sheet. `onDone` → `GET
  /repair/submissions/<sid>/result` → today's result view with the full contract. If that fails:
  one retry after 1 s; then a notice `dt_repair.result_load_failed` with "Try again" and (page)
  "Try another" / (session player) "Continue". The redacted contract is never passed to
  `renderResult` or stashed for "See full feedback".
- Page reload with an open session: the standalone page restores via its existing
  `takeFeedbackView` path only for full contracts; for an open session it calls
  `GET /repair/submissions/<sid>/session` when it has a `submission_id` with no grade shown, and
  reopens the sheet at the first open step. (Session player: the runner re-mounts the item and
  `/next` creates a new submission — the abandoned session is finished lazily, §7.4. Accepted.)
- `flag_only` / `direct_metalinguistic` arms keep governing the result view shown after the sheet.

### 8.8 Daily player `static/js/session/players/dt_repair.js`

`mount(container, ctx)`: render a small card ("Fix your sentences", spinner) in `container`;
`GET /api/dual-translation/repair/practice/due?language_id={ctx.languageId}` (the language the
runner already uses for its own calls). `items.length === 0` → `ctx.onComplete({dt_repair: 0})`
immediately (the block completes; no sheet). Else `DTRepairSheet.open({mode:'daily', items,
onDone})`; `onDone({closedEarly})` → `closedEarly ? ctx.onSkip() : ctx.onComplete({dt_repair:
n})`. Fetch failure → the standard unavailable card with "Skip for now" (`ctx.onSkip`). `destroy()`
closes the sheet. Measures `ActiveTimer` per item and sends `active_ms` + `client_event_id` on the
closing call of each item.

### 8.9 Loading, errors, timeouts — never a dead end

| Failure | Behaviour |
|---|---|
| check: network / non-2xx / 7 s abort (`AbortController`) / `result:'error'` | text kept, field editable, slot `check_failed`; 2nd consecutive → primary "Show answer" (reveal{grader_failed}) |
| hint request fails | slot `hint_failed`; hint button stays; 2nd failure → button "Show answer" |
| reveal / dispute fails | `answer_loading` replaced by `answer_failed` + "Try again" + quiet "Skip this sentence" (goes to next step; the item is closed as skipped by finish) |
| open fails | proceed to `fix` anyway (open is bookkeeping); log |
| finish fails | summary from client counts; Done works; result fetch still attempted |
| result fetch fails | §8.7 notice with retry/continue |
| sheet script missing (`!window.DTRepairSheet`) | page: fetch result immediately and render today's view; session player: today's band screen after fetching result |
| any uncaught error inside the sheet | caught at the top-level handler: best-effort `finish{closed_early:true}` (pass), close the sheet, `onDone({closedEarly:true, error:true})`; the host then fetches the result. If `/result` answers 409 `REPAIR_IN_PROGRESS` (finish did not land), the host calls finish once more and retries the result |

### 8.10 Accessibility, motion

- Dialog: `role="dialog"`, `aria-modal="true"`, `aria-labelledby` the current view's heading;
  focus trapped inside the sheet; on close focus returns to `returnFocus`.
- Focus on each view change: the view's `h2` (`tabindex=-1`, `preventScroll`) except `fix` (§8.4).
- `aria-live="polite"` region: "Checking", then the check result text ("Fixed", "Still not quite",
  …), hint text when a hint arrives. Updated in place (text node), not by re-rendering the region.
- Touch targets ≥ 44×44 px; WCAG 2.2 AA contrast; underline, dot shape and icons carry meaning
  without colour; CJK font stacks via `:lang()` and line-height 1.65–1.7 for `lang=zh|ja` runs;
  `lang` on every L1 and L2 run.
- `prefers-reduced-motion: reduce`: no slide/fade, no shake, spinner static (text carries state),
  no auto-advance (Next only).
- No mock or debug control in the flow; nothing about recording is shown.

### 8.11 Frontend tests

- `tests/unit/dt-repair-sheet.test.js` (vitest + happy-dom, `fetch` injected with the §4.12
  fixtures): every transition row of §8.5; Enter during composition does not check
  (`isComposing: true`, and `keyCode 229`); unchanged text makes no request; double press sends one
  request; `client_check_id` reused on retry; answer view has `<del>` in "You wrote" and `<b>` in
  "Answer", in that order, "You wrote" equals `learner_sentence`; reduced motion → no auto-advance;
  the redacted contract is never handed to the host's result renderer.
- `tests/unit/session-dt-repair-player.test.js`: empty due → `onComplete`; close → `onSkip`.
- `tests/unit/session-dt-player.test.js`, `tests/unit/player-registry.test.js`: extended for the
  `repair` branch and the new kind.
- `tests/e2e/dt-repair/harness.html` + `noscroll.cjs`: loads the real CSS/JS with a stubbed
  `authFetch` (fixtures + the three stress sentences) and walks every view and state at the 5
  viewports × light/dark, asserting §8.3 (port of `verify.cjs`, including its answer-step checks).
  Runs with `NODE_PATH=/opt/node-tools/node_modules node tests/e2e/dt-repair/noscroll.cjs`; no
  server needed.

## 9. Database

Migration file (written by WP-BE, applied by the owner): **`migrations/dt_guided_self_repair.sql`**.
Additive, idempotent (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`), no change to
existing tables, conventions of `dt_cards.sql` / `dt_grading_assets.sql` (bigint identity PKs,
`integer` language FKs, `real` for floats, CHECKs for enums, `timestamptz DEFAULT now()`, COMMENTs
on table and non-obvious columns), and the TASK-881 security rule: RLS enabled, `REVOKE ALL … FROM
PUBLIC, anon, authenticated`, no policies (Flask uses the service role; no client reads these).

### 9.1 DDL design

```sql
BEGIN;

CREATE TABLE IF NOT EXISTS public.dt_repair_session (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    submission_id    bigint NOT NULL UNIQUE REFERENCES public.dt_submission(id) ON DELETE CASCADE,
    user_id          uuid   NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    l2_language_id   integer NOT NULL REFERENCES public.dim_languages(id),
    l1_language_id   integer NOT NULL REFERENCES public.dim_languages(id),
    status           text NOT NULL CHECK (status IN ('open','finished','bypassed','abandoned')),
    n_sentences      smallint NOT NULL CHECK (n_sentences >= 0),
    n_flagged        smallint NOT NULL CHECK (n_flagged >= 0),
    n_steps          smallint NOT NULL CHECK (n_steps >= 0),
    grade_tier       text,                 -- grader_trace.tier at creation ('single_call' | 'tier0')
    prompt_version   text,                 -- grader_trace.single_call.prompt_version
    hint_version     text NOT NULL,        -- hint_templates.json version
    settings         jsonb NOT NULL,       -- snapshot: {max_targets, bypass, unsure_max, cap_pass, loc_share}
    closed_early     boolean,
    total_ms         integer,
    created_at       timestamptz NOT NULL DEFAULT now(),
    finished_at      timestamptz
);
CREATE INDEX IF NOT EXISTS idx_dt_repair_session_user_status ON public.dt_repair_session (user_id, status);

CREATE TABLE IF NOT EXISTS public.dt_repair_item (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id        bigint NOT NULL REFERENCES public.dt_repair_session(id) ON DELETE CASCADE,
    user_id           uuid   NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    submission_id     bigint NOT NULL REFERENCES public.dt_submission(id) ON DELETE CASCADE,
    error_id          bigint NOT NULL REFERENCES public.dt_error_instance(id) ON DELETE CASCADE,
    l2_language_id    integer NOT NULL REFERENCES public.dim_languages(id),
    sentence_index    smallint NOT NULL CHECK (sentence_index >= 0),
    step_order        smallint CHECK (step_order IS NULL OR step_order >= 0),
    step_kind         text NOT NULL CHECK (step_kind IN ('repair','unsure','direct')),
    ladder            text NOT NULL CHECK (ladder IN ('full','short','none')),
    location_available boolean NOT NULL,
    subtype           text NOT NULL,
    severity          text NOT NULL CHECK (severity IN ('minor','major','critical')),
    confidence        real,
    repro_start       integer NOT NULL, repro_end integer NOT NULL,   -- learner sentence in dt_submission.reproduction
    ref_start         integer NOT NULL, ref_end   integer NOT NULL,   -- reference sentence in dt_passage.l2_text
    span_start        smallint, span_end smallint,                    -- primary error, local to the learner sentence
    -- live state of the current sitting
    sitting           smallint NOT NULL DEFAULT 0,                    -- 0 = repair pass, n = n-th daily sitting
    sitting_open      boolean NOT NULL DEFAULT false,
    hint_level        smallint NOT NULL DEFAULT 0 CHECK (hint_level BETWEEN 0 AND 4),
    checks_used       smallint NOT NULL DEFAULT 0,
    calls_used        smallint NOT NULL DEFAULT 0,
    last_text         text CHECK (last_text IS NULL OR char_length(last_text) <= 400),
    active            jsonb,                                          -- current target {subtype,severity,form,start,end,corrected_form,correction_source}
    opened_at         timestamptz,
    check_lock_until  timestamptz,
    -- repair-pass episode result
    outcome           text CHECK (outcome IS NULL OR outcome IN ('self_repaired','repaired_alternative',
                        'answer_shown','shown_directly','disputed','skipped',
                        'unsure_revised','unsure_dismissed','unsure_skipped')),
    answer_reason     text CHECK (answer_reason IS NULL OR answer_reason IN ('asked','auto_cap','grader_failed','budget','direct')),
    max_hint_level    smallint CHECK (max_hint_level IS NULL OR max_hint_level BETWEEN 0 AND 4),
    n_checks          smallint NOT NULL DEFAULT 0,
    time_ms           integer,
    first_edit_ms     integer,
    closed_at         timestamptz,
    -- daily-practice queue
    queue_status      text NOT NULL DEFAULT 'none'
                        CHECK (queue_status IN ('none','due','resolved','retired','expired','disputed')),
    queued_at         timestamptz,
    due_on            date,
    not_before        timestamptz,
    expires_at        timestamptz,
    failed_sittings   smallint NOT NULL DEFAULT 0,
    hinted_sittings   smallint NOT NULL DEFAULT 0,
    last_practiced_at timestamptz,
    created_at        timestamptz NOT NULL DEFAULT now(),
    CHECK (repro_end >= repro_start AND ref_end >= ref_start),
    CHECK ((span_start IS NULL) = (span_end IS NULL))
);
CREATE INDEX IF NOT EXISTS idx_dt_repair_item_session ON public.dt_repair_item (session_id);
CREATE INDEX IF NOT EXISTS idx_dt_repair_item_error   ON public.dt_repair_item (error_id);
CREATE INDEX IF NOT EXISTS idx_dt_repair_item_due
    ON public.dt_repair_item (user_id, l2_language_id, due_on) WHERE queue_status = 'due';

CREATE TABLE IF NOT EXISTS public.dt_repair_event (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    item_id          bigint NOT NULL REFERENCES public.dt_repair_item(id) ON DELETE CASCADE,
    user_id          uuid   NOT NULL,      -- denormalised for the daily budget query; no FK (item cascade covers it)
    surface          text NOT NULL CHECK (surface IN ('repair_pass','daily_practice')),
    sitting          smallint NOT NULL,
    kind             text NOT NULL CHECK (kind IN ('step_opened','hint_shown','revision_checked',
                        'answer_shown','disputed','kept','skipped','episode_closed')),
    hint_level       smallint NOT NULL CHECK (hint_level BETWEEN 0 AND 4),
    since_prev_ms    integer,
    -- hint_shown
    hint_source      text CHECK (hint_source IS NULL OR hint_source IN ('grader_span','template','taxonomy_gloss','type_neutral')),
    hint_template_id text,
    -- revision_checked
    client_check_id  uuid,
    text             text CHECK (text IS NULL OR char_length(text) <= 400),
    result           text CHECK (result IS NULL OR result IN ('fixed','no_issue_found','still_flagged','error')),
    result_detail    jsonb,                -- §6.3 compact detail; episode_closed: {outcome, time_ms, n_checks, answer_reason}
    latency_ms       integer,
    tokens_in        integer,
    tokens_out       integer,
    cost_usd         numeric(12, 8),
    model_slug       text,
    prompt_version   text,
    created_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_dt_repair_event_item ON public.dt_repair_event (item_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_dt_repair_event_check
    ON public.dt_repair_event (item_id, client_check_id) WHERE client_check_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_dt_repair_event_user_checks
    ON public.dt_repair_event (user_id, created_at) WHERE kind = 'revision_checked';

ALTER TABLE public.dt_repair_session ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dt_repair_item    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dt_repair_event   ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.dt_repair_session FROM PUBLIC, anon, authenticated;
REVOKE ALL ON public.dt_repair_item    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON public.dt_repair_event   FROM PUBLIC, anon, authenticated;

COMMIT;
```

Plus `COMMENT ON TABLE/COLUMN` for each table and for `active`, `settings`, `result_detail`,
`repro_start/ref_start` (they are offsets, not copies), `queue_status`, `sitting`, and a header
block (purpose, size estimate, retention note, verification queries) in the style of
`dt_grading_assets.sql`. `tests/test_migration_security_lint.py` must pass on the file.

`episode_closed` (one per sitting) carries `result_detail = {"o": outcome, "t": time_ms, "n":
n_checks, "a": answer_reason|null, "h": max_hint_level}` — the per-sitting episode record for daily
practice (the repair-pass episode is also denormalised on the item row).

Existing tables: **read** `dt_submission` (reproduction, user_id, l1_language_id, passage_id,
created_at), `dt_passage` (l2_text, l2_language_id, age_tier, source_ref_id, sentence_start/end),
`dt_passage_reference`, `test_sentences`, `test_sentence_references`, `dt_grade` (scores,
grader_trace), `dt_error_instance` (§11 columns), `dt_taxonomy_version` (via the cascade getter),
`daily_test_loads`, `user_study_plans` (via day_boundary). **Written**: the three new tables;
`study_time_credits` (via `credit_study_time`); `daily_test_loads.completed_blocks` (via the
existing complete-block); `llm_calls` (failed re-checks only).

### 9.2 Size estimate and retention

Per row, UTF-8, including ~60 B tuple/row overhead and index entries:

| Row | Arithmetic | Size |
|---|---|---|
| session | ~110 B fixed + `prompt_version` 40 + `hint_version` 25 + `settings` ~90 + overhead 60 + 2 indexes ~60 | ≈ 0.4 KB |
| item | ~190 B fixed (ints, bools, timestamps) + subtype 15 + `active` ~140 + overhead 60 + 4 index entries ~140 | ≈ 0.55 KB |
| event `hint_shown` / `step_opened` / `answer_shown` | ~70 B + template id ≤ 30 + overhead 60 + 1 index ~35 | ≈ 0.2 KB |
| event `revision_checked` | ~110 B + text 90–150 (30–50 CJK chars × 3 B or 80–120 Latin) + `result_detail` 60–300 + model/prompt ~65 + overhead 60 + 3 indexes ~110 | ≈ 0.55–0.8 KB |
| event `episode_closed` | ~70 + detail ~40 + overhead 60 + index 35 | ≈ 0.2 KB |

Per error-bearing submission, expected (1.5 steps, 1.6 checks, 1 hint per step): 0.4 + 1.5 × (0.55
+ 0.2 open + 0.2 hint + 1.6 × 0.65 + 0.2 closed) ≈ **3.2 KB**. Clean submission: 0.4 KB. With the
gold set's 67% error-bearing share: ≈ **2.3 KB per graded submission**. Worst case (4 steps × (open
+ 3 hints + 4 checks at 0.8 + closed) + session): ≈ **18 KB**. Daily practice: ≈ 1.6 KB per item
sitting, ≤ 3 per user per day ≈ 5 KB per active user-day. Failed re-checks add one `llm_calls` row
(~0.3 KB + raw ≤ 4 KB).

At 100 graded submissions/day plus 50 practising users: ≈ 0.5 MB/day, 15 MB/month. At 1,000/day
plus 500 users: ≈ 5 MB/day, ≈ 150 MB/month — more than a quarter of a ~511 MB database per month,
so at that scale retention must be applied. Not stored (by design): prompts, raw model responses
of successful calls, template hint texts (id + version reproduce them), learner/reference sentence
copies (offsets into existing rows), revisions identical to the previous one (no call, no row).

Retention note (not built in this feature; a follow-up job when `pg_total_relation_size` of the
three tables exceeds 50 MB): delete `step_opened`/`hint_shown` events older than 180 days for
items whose `queue_status ∉ ('due')` (item rows keep `max_hint_level`, `outcome`, `n_checks`);
keep `revision_checked` text indefinitely (the most valuable asset). Measure with
`SELECT pg_size_pretty(sum(pg_total_relation_size(c))) FROM unnest(array['dt_repair_session','dt_repair_item','dt_repair_event']::regclass[]) c;`.

### 9.3 Rate limits and cost cap

- `web/rate_limits.py` `ENDPOINT_LIMITS`: `'dt_repair.check': (('20 per minute; 300 per hour',
  user_or_ip),)`, `'dt_repair.hint': (('60 per minute', user_or_ip),)`,
  `'dt_repair.practice_due': (('30 per minute', user_or_ip),)`. (Endpoint names = blueprint
  `dt_repair` + view function names `check`, `hint`, `practice_due`.)
- Per sitting: `DT_REPAIR_MAX_CALLS_PER_SITTING` grader calls.
- Per user per day: `budget.recheck_allowed(db, user_id)` = `checks_today < DT_REPAIR_MAX_CHECKS_PER_DAY`
  and `grade_tokens_today + recheck_tokens_today < Config.DT_DAILY_TOKEN_BUDGET +
  DT_REPAIR_TOKEN_ALLOWANCE`, where `recheck_tokens_today` sums `tokens_in + tokens_out` of today's
  (UTC, same window as `_tokens_used_today`) `revision_checked` events of the user (partial index),
  and `grade_tokens_today` is the existing `_tokens_used_today` logic (moved into `budget.py`; the
  route keeps a thin wrapper). Worst-case spend per user per day at the cap: 60 × ~$0.00009 ≈
  $0.0054.

## 10. Work packages and file ownership

No file is touched by more than one package. WP-INT runs after both.

**WP-BE (backend) may touch only:**
- `migrations/dt_guided_self_repair.sql` (new)
- `services/dual_translation/repair/` (new package: `__init__.py`, `settings.py`,
  `hint_templates.json`, `hints.py`, `sentences.py`, `planner.py`, `recheck.py`, `classify.py`,
  `scheduling.py`, `budget.py`, `store.py`, `service.py`, `hooks.py`)
- `routes/dt_repair.py` (new)
- `app.py` (register `dt_repair_bp`, one import + one line)
- `web/rate_limits.py` (three entries)
- `routes/dual_translation.py` (the §3.3 hook and `_tokens_used_today` wrapper only — TASK-959,
  last, after the grader agent's work has landed)
- `services/study_session/queue.py`, `services/study_session/session.py`
- tests: `tests/test_dt_repair_hints.py`, `tests/test_dt_repair_planner.py`,
  `tests/test_dt_repair_classify.py`, `tests/test_dt_repair_recheck.py`,
  `tests/test_dt_repair_scheduling.py`, `tests/test_dt_repair_service.py`,
  `tests/test_dt_repair_routes.py`, `tests/test_dt_repair_submit_hook.py`,
  `tests/test_dt_repair_session_block.py`, `tests/test_dt_repair_migration.py` (all new)

**WP-FE (frontend) may touch only:**
- `static/js/dt-repair-sheet.js` (new), `static/css/dt-repair.css` (new)
- `static/js/session/players/dt_repair.js` (new)
- `static/js/dual_translation.js`, `static/js/session/players/dual_translation.js`
- `static/js/session/player_registry.js`, `static/js/session/controller.js`
- `templates/dual_translation.html`, `templates/study_session.html`
- `static/i18n/en.json`, `static/i18n/zh.json`, `static/i18n/ja.json`
- tests: `tests/unit/dt-repair-sheet.test.js`, `tests/unit/session-dt-repair-player.test.js`
  (new), `tests/unit/session-dt-player.test.js`, `tests/unit/player-registry.test.js`,
  `tests/unit/fixtures/dt-repair/*.json` (new), `tests/e2e/dt-repair/harness.html`,
  `tests/e2e/dt-repair/noscroll.cjs` (new)

**WP-INT (after both):** `tests/e2e/dt-repair.spec.js` (new), `wiki/index.md`, `wiki/log.md`,
`wiki/tasklist/master.md`, `wiki/features/dual-translation.tech.md` ("Still needed" section →
link here), `wiki/tasklist/dt-single-call-grader.tasks.md` (TASK-939/940 → superseded by this
breakdown), `wiki/features/dt-guided-self-repair*.md` (status), and applying the migration
(owner).

## 11. Grader contract this feature depends on

Verified against the working tree on 2026-11-14 (commit `ed6e325` + uncommitted edits to
`single_call_grader.py` / `single_call_prompts.py`). The orchestrator should re-verify each item
when the grader work lands; any change here is a breaking change for WP-BE.

Persisted `dt_error_instance` columns (read by `store.py`): `id`, `submission_id`,
`sentence_index` (0-based pair index into `build_sentence_pairs(gold, reproduction)`),
`span_reproduction` `[start,end]` (offsets into the reproduction), `span_reference` `[start,end]`
(offsets into `dt_passage.l2_text`), `subtype` (v6 slug), `severity` (applied:
minor/major/critical), `model_severity`, `confidence` (0.9/0.6/0.3 or 0.5 default),
`confidence_label` (high/medium/low/NULL), `span_source` (exact/normalised/fuzzy/diff_hunk/sentence),
`correction_source` (model_quote/aligned_diff/reference_sentence), `learner_form`,
`corrected_form` (local), `explanation` (template rule text — contains the corrected form),
`model_note` (model's L1 explanation ≤ 240), `explanation_source` (model/template/explainer).
Contract-only: `errors[].explanation_parts.application` (= `model_note` when source is model).
`dt_grade`: `scores` (dict of 1–4 bands), `overall_band`, `grader_trace.tier` (`'single_call'` for
this flow), `grader_trace.single_call.used`, `grader_trace.single_call.prompt_version`.

Module internals imported by `recheck.py` / `hints.py` (no edits):
1. `single_call_grader.call_structured(slug, system, user, *, schema, max_tokens, extra, timeout)`
2. `single_call_grader._decode(gc, raw_errors, *, pairs, type_ids, subtypes, taxonomy_cfg, subtype_meta, severity_rule, l1_code, l2_code, gold_l2, reproduction) -> (errors, per_error, counts)` — errors carry `span_reproduction`, `learner_form`, `corrected_form`, `subtype`, `severity`, `model_severity`, `confidence`, `confidence_label`, `span_source`, `correction_source`, `model_note`
3. `single_call_grader.SEVERITY_RULES`, `DEFAULT_SEVERITY_RULE`, `REQUEST_EXTRAS`, `STATUS_*`
4. `single_call_prompts.supports`, `TYPE_IDS`, `build_system_prompt(l2, free_translation=, band_descriptors=)`, `build_user_prompt(pairs, l1, l2)`, `response_schema(l2)`, `prompt_variant(bool)`, `PROMPT_VERSION`, `MAX_TOKENS`, `TEMPERATURE`
5. `sentence_pairs.build_sentence_pairs`, `split_sentences`; `passage_builder.join_sentences`
6. `single_call_grader._attempt(role, slug, system, user, schema)` — used if it gains a `timeout`
   parameter; otherwise `recheck.py` calls `call_structured(..., timeout=DT_REPAIR_RECHECK_TIMEOUT_S)`
   and parses with `services.llm_output_cleaner.clean_json_response` + `json.loads` exactly as
   `_attempt` does.
7. `grader_cascade.get_active_taxonomy(db)`, `_resolve_subtypes(taxonomy, l1, l2)`;
   `tier0._normalize_l2(text, l2_code)`
8. Config: `DT_SINGLE_CALL_MODEL`, `DT_SINGLE_CALL_FREE_TRANSLATION`,
   `DT_SINGLE_CALL_SHOW_LOW_CONFIDENCE` (behaviour: low entries withheld when off),
   `DT_DAILY_TOKEN_BUDGET`, `DT_GRADING_ASSET_COLUMNS` (must be on and the asset migration applied:
   without the asset columns `sentence_index` is NULL and every grade is ineligible).

## 12. Key Architectural Decisions

1. **Decision:** a separate blueprint and service package, with a two-line hook in the existing
   submit route.
   - **Rationale:** the grader agent is editing `routes/dual_translation.py` concurrently; keeping
     all logic outside it makes the parallel build and the merge safe.
   - **Alternatives rejected:** adding the endpoints to `routes/dual_translation.py` (merge
     conflicts, a 1,200-line file grows further).
2. **Decision:** the session is created inside submit and the submit response is redacted while it
   is open; the full contract is served by a separate endpoint after finish.
   - **Rationale:** the only way the answer is not on the client before reveal; the current
     contract carries `diff`, `corrected_form` and explanations that contain the corrected form.
   - **Alternatives rejected:** client-side hiding (the answer would be in devtools and in the
     `dt_feedback_view` localStorage stash); a separate "start session" call after submit (an
     extra round trip and a window where the unredacted contract was already sent).
3. **Decision:** re-check reuses the grading prompt on a one-pair input, primary model only.
   - **Rationale:** the detector that was measured is the one that judges the revision; no new
     prompt to validate; ~1.4 s.
   - **Alternatives rejected:** re-grading the whole passage (cost and latency ×n, and other
     sentences could change verdict); a new short "is this fixed?" prompt (unmeasured, and a
     yes/no model is the decision-model design the experiment rejected); falling back to the second
     model (doubles worst-case latency inside a 5 s budget).
4. **Decision:** "fixed" = target gone (same subtype or overlapping span absent) AND no new
   major/critical error; `fixed` vs `no_issue_found` split by presence of the corrected form.
   - **Rationale:** the owner's definition; minor leftovers must not trap the learner; a valid
     alternative is credited as repaired (SPEC §1.2).
   - **Alternatives rejected:** string match to the reference (punishes valid alternatives); "no
     errors at all" (a pre-existing minor slip elsewhere in the sentence would block every fix).
5. **Decision:** hint templates in a versioned JSON file in the repair package, not in
   `dt_taxonomy_version`; model-written hints never used at run time.
   - **Rationale:** Track D — templates 0% leaks vs 9–40% for model hints; hint copy is UI content
     whose edits must not bump the grading taxonomy or bust the prompt cache.
   - **Alternatives rejected:** taxonomy JSON (couples UI copy to grading config); a DB table
     (needs an admin UI; reproducibility by version is simpler in git).
6. **Decision:** one step per sentence, working on its most serious error.
   - **Rationale:** matches the mockup (one sentence, one problem per screen); the answer screen
     shows all marks of the sentence.
   - **Alternatives rejected:** one step per error (two screens for the same sentence, confusing
     because both pre-fill the same text).
7. **Decision:** non-hintable and over-cap sentences appear in the sheet as answer screens
   (`direct` steps, revealed on display), not only on the later result screen.
   - **Rationale:** keeps "The other N look fine" true and keeps the pop-up-step-by-step model for
     every flagged sentence (at most 4 screens because ≥ 5 bypasses).
   - **Alternatives rejected:** SPEC §1.1's "goes straight to the existing error card" (the result
     screen would then say sentences "look fine" that were flagged).
8. **Decision:** daily practice items are a new table with fixed-interval rules, served as one
   `dt_repair` block in the existing session queue; `dt_card` is untouched.
   - **Rationale:** `dt_card` is subtype-cluster-keyed, FSRS-rated (1–4), and its `card_type`
     CHECK would need a drop/re-add; SPEC §8 rules are hint-level-based fixed intervals; the
     block pattern (`intro_reviews`) is the existing way to add a conditional item to the session.
   - **Alternatives rejected:** new `dt_card.card_type = 'self_repair'` (FSRS mismatch, destructive
     constraint change, mixes per-instance items into subtype interleaving); a separate practice
     page (a parallel queue).
9. **Decision:** daily failure intervals 2 then 4 days, retire at the 3rd failed sitting.
   - **Rationale:** SPEC §8.4 states both "2, 4, 7" and "retired after 3 such sittings"; the
     retirement rule is the cap that bounds nagging, so it wins.
   - **Alternatives rejected:** 2/4/7 with retirement at the 4th (contradicts the stated cap).
10. **Decision:** feature flag `DT_GUIDED_REPAIR` default ON, with per-grade eligibility; the
    correction-style arm column is not extended.
    - **Rationale:** the grader contract is live by default; ineligible grades fall back to today's
      view automatically; extending the `dt_submission.correction_style` CHECK would need a
      DROP CONSTRAINT. The presence of a `dt_repair_session` row records that the flow ran.
    - **Alternatives rejected:** a third correction-style arm (destructive constraint change, and
      an A/B the owner has not asked for — open question).
11. **Decision:** store offsets, not sentence copies; log successful re-checks only in
    `dt_repair_event`, not in `llm_calls` or `dt_grading_call`.
    - **Rationale:** the owner's size constraint; the event row already carries model, tokens,
      cost, latency and the structured result; `dt_grading_call.submission_id` semantics are
      "grading of the submission".
    - **Alternatives rejected:** `dt_grading_call` rows with `flow='repair_recheck'` (+0.6 KB per
      check, and edits the grader agent's migration).

## 13. Security Considerations

- **Auth/ownership:** every endpoint requires a valid JWT; every item/session/submission is loaded
  and its `user_id` compared with `g.current_user_id` before anything else (403 `NOT_OWNER`).
  Service-account tokens (`sub='service-account'`) never own rows → 403.
- **No answer before reveal:** redacted submit (§3.3), Steps without reference data (§4.2), hint
  rungs (§4.5), leak filter on clues (§5.4), `/result` refuses while open (§4.10). Tests assert
  that no response before reveal contains the reference sentence, any `corrected_form` or
  `explanation` text (route tests compare serialized JSON against those strings).
- **Input limits:** revision ≤ 400 chars and ≤ 2× original + 40; NFC + whitespace normalisation;
  stored as text, never interpolated into SQL (PostgREST) or HTML (client uses `textContent` /
  escaped templates; server texts are escaped by the sheet's `esc()`).
- **Prompt injection:** the revision goes to the model only as the `LRN` line of the fixed
  user-prompt format; output is schema-validated and decoded by the grader's `_decode`; nothing the
  model writes is shown before reveal except via templates (labels/clues are from the file).
- **Cost:** per-sitting, per-day count and token caps (§9.3), endpoint rate limits; the unchanged
  check makes no call; idempotent `client_check_id` prevents double calls on retry.
- **RLS:** enabled with no policies on all three tables; client roles revoked.
- **Concurrency:** `check_lock_until` prevents parallel checks of one item (two tabs).

## 14. Testing Strategy

Backend (pytest, no network; the model boundary is `services.dual_translation.repair.recheck.recheck_sentence`
for route/service tests and `single_call_grader.call_structured` for recheck tests; DB via the
`tests/conftest.py` mock in the style of `tests/test_dual_translation_routes.py`, monkeypatching
`store` functions):
- `hints`: file validates; every v6 slug has a ladder; no `{c}`; clue length limits; fallback
  chain (template → gloss → English; clue → type_neutral); leak filter positives/negatives incl.
  CJK and the closed-class label exemption.
- `planner`: clean; bypass at 5 flagged and at a band of 1; primary error ordering; cap of 3 by
  severity with passage-order display; unsure threshold; ladder by age tier; location rules
  (`sentence` source, > 40%, point span); rungs table.
- `sentences`: offsets with leading/trailing whitespace; merged pairs; the three L1 rules.
- `classify`: target present by subtype and by overlap; new major → still_flagged/new_error with
  active switch; minor leftover → fixed; corrected form missing → no_issue_found; reference_sentence
  correction.
- `recheck`: request built with one pair and the grading prompt version; timeout → `timeout`;
  malformed → `malformed`; low-confidence withheld; unsupported L2.
- `scheduling`: every row of §7.1 and §7.3; due/not_before/expiry with a non-UTC learner day.
- `service`/routes: each endpoint's happy path, ownership 403, 404, flag-off 503, 409 cases
  (closed item, check in progress, no more hints, not due, repair in progress), idempotency
  (`client_check_id` replay, hint `expected_level`, reveal/dispute/finish repeated), unchanged text
  makes no model call, tier-0 equal makes no model call, check cap auto-reveal, budget exhaustion,
  redaction (no reference strings in any pre-reveal response), study-time credit calls.
- submit hook: not-eligible returns the identical contract; clean; bypass; open → redacted;
  cached path; hook exception → full contract; `_tokens_used_today` adds re-check tokens.
- study session: block present only with due items and DT not excluded; position; complete-block
  accepts `dt_repair`; counting failure → no block.
- migration: `tests/test_migration_security_lint.py` passes; a static test asserts RLS + REVOKE
  for the three tables and no DROP/DELETE/ALTER of existing objects.

Frontend: §8.11.

End-to-end (WP-INT, `tests/e2e/dt-repair.spec.js`, Playwright against a running app):
submit a passage with a planted error → sheet → hint → fix → summary → result view; a dispute; a
reveal; daily practice (seed a due item with `not_before`/`due_on` in the past through the service
role, then open the session) — and the no-scroll assertions at 390×844 on each real screen.

**Is an authenticated local E2E run feasible in this sandbox?** Partly. Verified 2026-11-14:
the app's Python dependencies install into a venv and the DT route tests run; `SUPABASE_URL`,
`SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENROUTER_API_KEY` and `TEST_USER_EMAIL` are set and
the Supabase auth endpoint answers; Chromium + Playwright are at `/opt/node-tools/node_modules`.
Missing: `TEST_USER_PASSWORD` / `TEST_JWT_TOKEN`, so `scripts/mint_test_token.py` cannot mint a
token. Two ways: (a) the owner exports `TEST_USER_PASSWORD` (or `TEST_JWT_TOKEN`) and runs
`gunicorn wsgi:app --bind 127.0.0.1:5000 --workers 2` (Procfile shape; `python app.py` is threaded
and unsafe with one Supabase client, per `playwright.config.js`), then `BASE_URL=http://127.0.0.1:5000
PW_CHROMIUM_PATH=… npx playwright test tests/e2e/dt-repair.spec.js`; (b) mint a session with the
service-role key (GoTrue admin `generate_link` type `magiclink` for `TEST_USER_EMAIL`, then
`/auth/v1/verify` with the returned hash) — technically possible here but it is an auth-admin
action on the **production** project, so only with the owner's permission. Either way the E2E run
writes real rows for the test account in the production database (there is no separate staging
project in the env) and spends a few OpenRouter calls (< $0.01), and it needs
`migrations/dt_guided_self_repair.sql` (and `dt_grading_assets.sql`) applied first. The no-scroll
harness (§8.11) needs none of this and runs in the sandbox.

## Related Pages
- [[features/dt-guided-self-repair]] — prose
- [[tasklist/dt-guided-self-repair.tasks]] — tasks
- [[design/dt-feedback/option-2-guided-self-repair/SPEC]] — design (Revision 2)
- [[features/dual-translation.tech]] — grading, single-call grader section
- [[features/dual-translation-remediation.tech]] — `dt_card` (coexists)
- [[decisions/ADR-044-dt-single-call-generative-grader]]
- [[evaluations/dt-decision-grading-2026-11-14]]
- [[features/study-plans.tech]] — session queue
- [[database/schema.tech]] · [[api/rpcs.tech]]
