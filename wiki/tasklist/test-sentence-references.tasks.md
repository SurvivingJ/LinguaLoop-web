---
title: "Test Sentence References — Task Breakdown"
feature: test-sentence-references
prose_page: ../features/test-sentence-references.md
tech_page: ../features/test-sentence-references.tech.md
total_tasks: 12
done: 11
---

# Test Sentence References — Task Breakdown

Implements [[decisions/ADR-037-sentence-level-l1-references]]. Bulk generation uses Claude
subagents through skills (the word-asset pattern); OpenRouter is used only for live grading.
Sequence: 900 → 901 → 902 → (903, 904, 905, 906 in parallel) → 907 pilot → 908 full run;
909–911 serve the workflow and can start after 901.

---

## TASK-900: Transcript preamble audit and cleanup

**Status:** [x] Done (live 2026-10-30) — 2 en transcripts cleaned (backups in `data/transcript_cleanup/2026-10-30/`), `transcript_hash` on all 305 active tests, `dt_passage` 19 retired
**Feature:** test-sentence-references
**Type:** bug
**Complexity:** S
**Depends On:** none

**Description:**
Some `tests.transcript` values begin with a generation preamble (seen live: "この文章は、T3レベル
（B1-B2）の学習者向けに…---"). It has already leaked into `dt_passage` and its references.
Audit every active test, strip the preamble, recompute `vocab_token_map` alignment, and write
`tests.transcript_hash`. LIVE-DB: the UPDATE needs user approval; the audit is read-only.

**Acceptance Criteria:**
- [ ] `scripts/audit_transcript_preambles.py --dry-run` lists every affected test (id, language, the first 60 chars) and the count per language; patterns: a leading sentence naming a level or tier followed by `---`, or `This passage`/`本文`/`この文章は` as the first sentence.
- [ ] `--apply` strips the preamble, re-derives `vocab_token_map` by re-running the token-map builder for that test only, and sets `transcript_hash` for every active test; a second run reports 0 affected.
- [ ] `dt_passage` rows whose `l2_text` starts with a preamble are set `status = 'retired'`.
- [ ] A unit test with a fixture transcript proves the pattern matcher does not strip a legitimate first sentence that merely contains "T3".

**Technical Notes:**
The token-map builder lives in `services/test_generation/orchestrator.py` (the block that
writes `vocab_token_map`); factor the per-test call out rather than re-running generation.
Keep a JSON backup of every changed transcript under `data/transcript_cleanup/<date>/`.

**Files to Create / Modify:**
- `scripts/audit_transcript_preambles.py` — new
- `migrations/tests_transcript_hash.sql` — adds `tests.transcript_hash text`
- `tests/test_transcript_preamble.py` — new

**Verification:**
`python scripts/audit_transcript_preambles.py --dry-run` then, after approval, `--apply`;
`select count(*) from tests where is_active and transcript like 'この文章は%'` returns 0.

---

## TASK-901: Migration — `test_sentences`, `test_sentence_references`, `dt_passage` range columns

**Status:** [x] Done (live 2026-10-30) — both migrations applied; RLS on, client roles denied, constraint validated
**Feature:** test-sentence-references
**Type:** infra
**Complexity:** S
**Depends On:** TASK-900

**Description:**
Create the two tables and the `dt_passage.sentence_start/sentence_end` columns exactly as in
[[features/test-sentence-references.tech]] §Database Impact, with RLS enabled and no client
grants (ADR-034). LIVE-DB, approval-gated.

**Acceptance Criteria:**
- [ ] Migration applies on a stub Postgres 16 and is idempotent (re-run is a no-op).
- [ ] Partial unique index enforces one active reference per (sentence_id, l1_language_id); inserting a second active row fails.
- [ ] Trigger rejects `l1_text` containing the L2 script for the sentence's test (Han for zh, Han/kana for ja).
- [ ] `select * from test_sentences` as `anon` and `authenticated` is denied.
- [ ] `migrations/CLAUDE.md` catalogue entry added.

**Files to Create / Modify:**
- `migrations/test_sentence_references_schema.sql` — new
- `tests/sql/test_sentence_references.sql` — new
- `wiki/database/schema.tech.md` — add both tables and the `dt_passage` columns

**Verification:**
`psql -f migrations/test_sentence_references_schema.sql` twice; run the SQL test file; live apply
only after approval, then the deny check as `authenticated`.

---

## TASK-902: Segmenter backfill — `scripts/build_test_sentences.py`

**Status:** [x] Done (live 2026-10-30) — 4,698 sentences (zh 2,084 / en 2,343 / ja 271); token spans null for 670 (tests with no word map, plus 26 ja sentences in 8 tests whose stored map no longer matches the transcript). Fixed en boundary tokens (". " straddles the span) before applying
**Feature:** test-sentence-references
**Type:** feature
**Complexity:** M
**Depends On:** TASK-901

**Description:**
Populate `test_sentences` for every active test using
`services/dual_translation/passage_builder.segment_sentences`, storing character spans and
token-map spans. A sentence's `l2_text` must equal the transcript substring, and the token span
must cover exactly the characters of the span (token maps concatenate to the transcript; verified
on the five demo tests).

**Acceptance Criteria:**
- [ ] For every active test, `''.join(sentence.l2_text) == transcript` and spans are contiguous and half-open.
- [ ] Token spans: `''.join(surface for tokens in span) == l2_text`; tests without a token map get NULL token spans and a WARNING line.
- [ ] Re-running with an unchanged `transcript_hash` is a no-op; a changed hash replaces the test's rows and retires its references (`is_active = false`, `review_verdict` unchanged) with a log line.
- [ ] `--dry-run` prints per-language counts (tests, sentences, mean sentences per test, tests under 2 sentences).

**Technical Notes:**
Reuse `_join_sentences` logic in reverse: the segmenter keeps terminators attached, so spans are
recoverable by sequential `find` from the last end offset. Sentence boundaries must be the same
ones the demo page uses (`。！？!?` terminators) or the preview's per-sentence features will
disagree with the references.

**Files to Create / Modify:**
- `scripts/build_test_sentences.py` — new
- `tests/test_build_test_sentences.py` — fixtures: the five demo tests (`data/fixtures/sentence_refs/*.json`) plus one en test

**Verification:**
`python scripts/build_test_sentences.py --dry-run`, then `--apply` (service role);
`select language_id, count(*) from test_sentences group by 1` ≈ zh 125 tests / en 121 / ja 59 with
about 1,900 sentences in total.

---

## TASK-903: Runner and validators — `scripts/sentence_ref_runner.py`, `services/dual_translation/sentence_refs.py`

**Status:** [x] Done — 11 harness tests; review packs split into blind + gold files after the pilot
**Feature:** test-sentence-references
**Type:** infra
**Complexity:** L
**Depends On:** TASK-902

**Description:**
The file-based harness that the two skills drive, mirroring `fat_seed_runner.py`: `export`,
`brief`, `check`, `review-pack`, `assemble`, `status`, with the document shape and the
deterministic checks in the tech page. No command calls a hosted model.

**Acceptance Criteria:**
- [ ] `export --language ja --l1 en --limit 8 --arm aligned --out-dir RUN` writes `worklist.csv` with one row per test (id, title, n_sentences, sentences JSON) and skips tests that already have an active `pass` reference for that L1.
- [ ] `brief RUN --width 6` writes numbered author briefs and `rules_authoring.md`; each brief contains the full passage, the sentence list with indices, the L1, the arm, and the JSON shape.
- [ ] `check RUN` reports per document: `ok` or a list of named failures (`count_mismatch`, `l2_script_leak:<chars>`, `missing_number:<n>`, `preamble`, `length_ratio:<r>`, `duplicate_sentence`); exit code 1 if any fail.
- [ ] `review-pack RUN` writes review packs with author notes stripped and the gold hidden behind a `--- GOLD ---` marker so the reviewer can do the blind back-translation first.
- [ ] `assemble RUN` merges reviewed docs and verdict records into `upload.json`; refuses if any reviewed doc fails `check --source reviewed`.
- [ ] `tightness(l1_backtranslation, l2_text)` uses the dictation grader's normalisation and returns a 0–1 similarity; unit-tested against three hand cases.
- [ ] `status RUN` prints a table: test × L1 → authored / checked / reviewed / assembled / uploaded.

**Technical Notes:**
Proper-noun detection for the number/name check: token-map senses whose `dim_vocabulary.part_of_speech`
is in the proper-noun set, plus katakana runs of length ≥ 3 for ja. Keep the check conservative:
a missing proper noun is a `warn`, not a `fail`, and goes to the reviewer.

**Files to Create / Modify:**
- `scripts/sentence_ref_runner.py` — new
- `services/dual_translation/sentence_refs.py` — new (document model, checks, tightness)
- `tests/test_sentence_refs.py` — new

**Verification:**
Run the chain on a hand-written 2-test RUN under `data/sentence_refs/ja/run_00/` and read
`status`; `pytest tests/test_sentence_refs.py`.

---

## TASK-904: Skill — `sentence-reference-authoring`

**Status:** [x] Done — skill written and exercised on run_00 and 30 pilot briefs
**Feature:** test-sentence-references
**Type:** docs
**Complexity:** S
**Depends On:** TASK-903

**Description:**
`.claude/skills/sentence-reference-authoring/SKILL.md`, modelled on `fat-seed-authoring`: the
orchestrator exports and briefs; one author subagent per brief writes the documents from files
only; `check` loop until clean; hand-off to review. Authors run on Sonnet. Two arms are
described (`sentencewise`: translate one sentence at a time with the passage visible;
`aligned`: translate the passage, then split into the aligned array) and the brief names which
one to use.

**Acceptance Criteria:**
- [ ] The skill states the default slice (8 tests, one language, one L1), the chain table, the subagent prompt text, the document shape, and the rules the author must follow (faithful, natural in L1, one sentence per entry, no added content, numbers and names preserved, no L2 script, no notes inside `l1`).
- [ ] Rules for CJK → en: keep the sentence boundary even when English would merge; keep tense and politeness neutral unless marked; translate loanwords to their English source.
- [ ] Rules for en → zh/ja and zh ↔ ja follow the gloss conventions in `cross-language-glosses`.
- [ ] The skill never asks the orchestrator to write or review a document.
- [ ] `claude plugin eval` or the repo's skill check passes for frontmatter.

**Files to Create / Modify:**
- `.claude/skills/sentence-reference-authoring/SKILL.md` — new

**Verification:**
Dry run the skill on `run_00` with one author subagent; `check` reports `ok` for both tests.

---

## TASK-905: Skill — `sentence-reference-review`

**Status:** [x] Done — skill written and exercised on run_00 and 30 pilot packs; blind/gold split added
**Feature:** test-sentence-references
**Type:** docs
**Complexity:** S
**Depends On:** TASK-903

**Description:**
`.claude/skills/sentence-reference-review/SKILL.md`, modelled on `fat-seed-review`: must run in
a fresh context that has not seen the authoring. Step 1 blind back-translation of every L1
sentence into the L2 (the gold is hidden below a marker the reviewer must not read yet); step 2
reveal the gold, judge mutual entailment, additions, omissions, register, leakage; rewrite what
fails; step 3 write the reviewed document and a verdict record per sentence. The runner computes
tightness from the back-translation. Opus for flagged items and the 15% sample, Sonnet otherwise.

**Acceptance Criteria:**
- [ ] The skill makes the blind-first ordering a hard rule and tells the reviewer to write the back-translation file before scrolling past the marker.
- [ ] Verdict record shape: `{test_id, l1, sentence_idx, verdict: pass|rewritten|fail, entailment_ok, back_translation, notes}`; the runner adds `tightness`.
- [ ] A `fail` is allowed only when the sentence cannot be rendered faithfully from the gold (e.g. the gold itself is corrupt); otherwise the reviewer rewrites.
- [ ] The skill names the Opus/Sonnet split and how the orchestrator selects the sample (stratified by language and sentence length).

**Files to Create / Modify:**
- `.claude/skills/sentence-reference-review/SKILL.md` — new

**Verification:**
Hand the `run_00` review pack to a fresh subagent; verdict records parse; `assemble` succeeds.

---

## TASK-906: Upload path — `scripts/upload_sentence_references.py`

**Status:** [x] Done (repo) — 5 planning tests on a fake client; live `--dry-run` after TASK-901
**Feature:** test-sentence-references
**Type:** infra
**Complexity:** S
**Depends On:** TASK-901, TASK-903

**Description:**
Load `upload.json` into `test_sentence_references` through the service-role client, one
transaction per test, verifying `transcript_hash`, with provenance columns filled from the
document and verdict records, and `--dry-run` printing the plan. Activation rules per the tech
page.

**Acceptance Criteria:**
- [ ] `--dry-run` prints per test: sentences, L1, verdicts, how many rows would be inserted and which existing active rows would be deactivated; inserts nothing.
- [ ] A hash mismatch for any test skips that test with an ERROR line and continues.
- [ ] Only `pass`/`rewritten` rows become active; `fail` rows are inserted inactive for the record.
- [ ] Re-uploading the same `upload.json` inserts nothing (idempotent on `run_id` + sentence + L1).

**Files to Create / Modify:**
- `scripts/upload_sentence_references.py` — new
- `tests/test_upload_sentence_references.py` — new (mocked client)

**Verification:**
`python scripts/upload_sentence_references.py RUN --dry-run`; then `--apply` on `run_00` and
`select count(*) from test_sentence_references where run_id = 'run_00'`.

---

## TASK-907: Two-arm pilot (30 tests per language) and evaluation page

**Status:** [x] Done (live 2026-10-30) — [[evaluations/sentence-refs-pilot-2026-10-30]]; 2,072 references uploaded, sentencewise arm active (1,035 rows; the one failed zh sentence stays inactive), aligned arm inactive
**Feature:** test-sentence-references
**Type:** test
**Complexity:** M
**Depends On:** TASK-904, TASK-905, TASK-906

**Description:**
Run both arms on the same 30 tests per language (ja, zh with L1 en; en with L1 zh), authored by
two independent author pools, reviewed blind by the review skill, and report tightness,
entailment pass rate, rewrite rate and leakage rate per arm and language. Pick the arm and set
the tightness floor. Stratify the Opus review sample at 15%.

**Acceptance Criteria:**
- [ ] `data/sentence_refs/pilot_YYYY-MM-DD/{ja,zh,en}/{sentencewise,aligned}/` each hold a complete RUN with `status` all `uploaded` (the pilot is uploaded inactive; activation happens in TASK-908 for the winner).
- [ ] `wiki/evaluations/sentence-refs-pilot-YYYY-MM-DD.md` reports per arm × language: n sentences, median and p10 tightness, entailment pass %, rewrite %, leakage %, author turns, reviewer turns; plus 10 worst sentences per arm with the reviewer's notes.
- [ ] Decision recorded: winning arm, tightness floor (proposed p10 of the winner, rounded to 0.05), and any rule changes to the authoring skill.
- [ ] The three OPEN questions on the prose page are answered or re-stated with evidence.

**Verification:**
The evaluation page exists, the tasklist and ADR-037 are updated with the decision, and
`select arm, count(*) from test_sentence_references group by 1` shows both arms.

---

## TASK-908: Full run — all active tests, winning arm

**Status:** [ ] Not Started — unblocked by TASK-907; needs TASK-901 applied live first
**Feature:** test-sentence-references
**Type:** feature
**Complexity:** L
**Depends On:** TASK-907

**Description:**
Author, review and upload references for every active test for the first L1 set (en for ja/zh
tests; zh for en tests), activate `pass`/`rewritten` rows, then retire `dt_passage` rows whose
tests are fully covered. Second L1 set (ja for zh tests, zh for ja tests, ja for en tests) as a
follow-on slice once a learner with that L1 exists.

**Acceptance Criteria:**
- [ ] Every active test with ≥ 2 sentences has an active reference for every sentence in the first L1 set; `status` shows no gaps.
- [ ] Coverage query per language = 100% of sentences; tightness floor met by ≥ 90% of sentences; the rest are listed for a second review pass.
- [ ] `dt_passage` rows for fully covered tests are `retired`; existing `dt_submission` history still resolves.
- [ ] Author and reviewer turn counts recorded in the log (the cost of this run is agent time, not OpenRouter spend).

**Verification:**
`scripts/sentence_ref_runner.py status` across all RUN dirs; the coverage SQL in the tech page.

---

## TASK-909: Serving — sentences endpoint, passage-from-sentences, primed-window selector

**Status:** [x] Done (repo) — sentences endpoint, passage-from-sentences (also creates the dt_submission row the submit route needs — deviation from the tech page, recorded), `select_window_for_primed`; 44 tests
**Feature:** test-sentence-references
**Type:** feature
**Complexity:** M
**Depends On:** TASK-901

**Description:**
`GET /api/tests/<slug>/sentences`, `POST /api/dual-translation/passage-from-sentences` and
`passage_builder.select_window_for_primed` exactly as specified in the tech page, including the
`produce` withholding rule, the 422 fallback when a sentence lacks a reference, and find-or-create
on the `dt_passage` range index.

**Acceptance Criteria:**
- [ ] Sentences endpoint returns spans that reproduce the transcript; in `?mode=produce` before the attempt is submitted, `l2_text` is absent.
- [ ] `select_window_for_primed` returns the expected range on the five demo fixtures (the demo's `chooseWindow` is the reference implementation) and never returns a range with a missing or retired reference.
- [ ] `passage-from-sentences` called twice with the same range returns the same `passage_id`.
- [ ] Route tests cover 403 (not attempted), 422 (no reference), 409 (stale hash).

**Files to Create / Modify:**
- `routes/tests.py`, `routes/dual_translation.py`, `services/dual_translation/passage_builder.py`
- `tests/test_sentence_endpoints.py`, `tests/test_window_selector.py`

**Verification:**
`pytest tests/test_sentence_endpoints.py tests/test_window_selector.py`; manual: open a prestudied
test, submit, call the endpoint, confirm the reference only.

---

## TASK-910: Grader target words → per-word production evidence

**Status:** [x] Done (repo, 2 gaps) — `classify_target_words` + per-sense word-test evidence via the batch RPC (`side_effects=False`), signed `primed_token`, result table; GAPS (TODO in `routes/dual_translation.py`): no `exercise_attempts` row (table has no `source` column) and no `prestudy_followups` append (queue not built yet); i18n keys use English fallbacks pending locale files
**Feature:** test-sentence-references
**Type:** feature
**Complexity:** M
**Depends On:** TASK-909

**Description:**
Pass `primed_sense_ids` through `grade()`; after the cascade, classify each as `produced`,
`variant` or `omitted` using the token-map surface, the lemma, and `dt_error_instance` span
overlap; write one `user_vocabulary_knowledge` evidence row per sense with the exercise-evidence
parameters of the `contextual_use` family and `exercise_attempts.source = 'prestudy_produce'`;
return the rows to the client for the diff screen. No ladder admission.

**Acceptance Criteria:**
- [ ] Unit tests: produced (exact surface), variant (lemma present, surface absent), omitted, and an error-instance span that covers the surface counts as `variant` with the error subtype attached.
- [ ] `contextual_use` family confidence on `user_word_ladder` is updated only when a ladder row already exists; otherwise only `user_vocabulary_knowledge` moves.
- [ ] Omitted senses are appended to the session's next-day review list (`prestudy_followups`, see [[features/test-prestudy]]).
- [ ] The DT result template renders the per-word table under the diff.

**Files to Create / Modify:**
- `services/dual_translation/grader_cascade.py`, `routes/dual_translation.py`, `templates/dual_translation.html`, `static/js/dual_translation.js`
- `tests/test_dt_target_words.py`

**Verification:**
`pytest tests/test_dt_target_words.py`; submit a Produce reproduction on the demo window and see
the per-word rows.

---

## TASK-911: Preview uses `test_sentences` (sentence playback and cloze)

**Status:** [x] Done (repo) — `static/js/session/sentences.js`, player renders server spans with client fallback, hidden reference toggle; 15 vitest
**Feature:** test-sentence-references
**Type:** refactor
**Complexity:** S
**Depends On:** TASK-902

**Description:**
Replace the client-side sentence split in the prestudy preview and the passage-cloze stage with
the server's `test_sentences` spans so the preview, the cloze and the Produce window agree on
boundaries; show the L1 reference as a tappable line under each sentence in the preview when the
learner asks for it (off by default).

**Acceptance Criteria:**
- [ ] The preview renders sentences from the endpoint; the cloze stage builds its blank from the same span.
- [ ] A test without sentence rows falls back to the client split with a console warning, never a blank preview.
- [ ] Reference line is hidden by default and never shown in `produce` mode.

**Files to Create / Modify:**
- `static/js/session/players/reading_listening.js`, prestudy view files from the prestudy tasks
- `tests/unit/prestudy-sentences.test.js`

**Verification:**
vitest; open the preview on a test with sentence rows and on one without.
