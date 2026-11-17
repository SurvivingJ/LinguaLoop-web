---
title: Test Sentence References — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./test-sentence-references.md
last_updated: 2026-11-17
dependencies:
  - "tests.transcript, tests.vocab_token_map"
  - "services/dual_translation/passage_builder.segment_sentences"
  - "dt_passage, dt_passage_reference, dt_submission (unchanged grading path)"
  - "scripts/fat_seed_runner.py (pattern), scripts/upload_exercises.py (upload pattern)"
  - "Claude subagents via .claude/skills (authoring, review)"
breaking_change_risk: low
---

# Test Sentence References — Technical Specification

## Architecture Overview

```
tests.transcript ──(TASK-900 cleanup)──► tests.transcript (clean, hash)
        │
        ▼ segment_sentences (CJK-aware, existing)
test_sentences (test_id, idx, char span, token span, l2_text, transcript_hash)
        │
        ▼ scripts/sentence_ref_runner.py export → briefs
author subagents (skill: sentence-reference-authoring)  ──► RUN/sentence_refs/docs/<test_id>.<l1>.json
        │  check (deterministic)
        ▼ review-pack
reviewer subagents (skill: sentence-reference-review, fresh context) ──► RUN/sentence_refs/reviewed/… + verdicts
        │  assemble
        ▼ scripts/upload_sentence_references.py (service role, dry run first)
test_sentence_references (sentence_id, l1_language_id, l1_text, provenance, verdict, tightness, is_active)
        │
        ▼ at session time (routes/dual_translation.py)
dt_passage(sentence_start, sentence_end) ← assembled from sentences; reference = join(active refs)
        │
        ▼ existing cascade (OpenRouter, dual_translation_tier1..3) — unchanged
dt_submission / dt_grade / dt_error_instance (+ per-primed-word rows, TASK-910)
```

## Database Impact

### New: `test_sentences`

| column | type | notes |
|---|---|---|
| `id` | bigint PK | |
| `test_id` | uuid NOT NULL | FK → tests ON DELETE CASCADE |
| `idx` | smallint NOT NULL | 0-based sentence index; UNIQUE (test_id, idx) |
| `char_start`, `char_end` | integer NOT NULL | half-open span in `tests.transcript` |
| `token_start`, `token_end` | integer NOT NULL | half-open span in `tests.vocab_token_map`; NULL when the test has no token map |
| `l2_text` | text NOT NULL | the sentence, terminator attached, equal to `substr(transcript, char_start, …)` (CHECK via trigger) |
| `transcript_hash` | text NOT NULL | sha256 of the transcript at segmentation time |
| `created_at` | timestamptz | |

Indexes: `(test_id, idx)`. RLS on (ADR-034); read via Flask only.

### New: `test_sentence_references`

| column | type | notes |
|---|---|---|
| `id` | bigint PK | |
| `sentence_id` | bigint NOT NULL | FK → test_sentences ON DELETE CASCADE |
| `l1_language_id` | smallint NOT NULL | FK → dim_languages |
| `l1_text` | text NOT NULL | the reference; CHECK: no script of the test's L2 (trigger using `dim_languages`) |
| `author_model` | text NOT NULL | e.g. `claude-sonnet-5-5` (the subagent's model) |
| `prompt_version` | text NOT NULL | skill version string |
| `arm` | text | `sentencewise` \| `aligned` (pilot) or NULL |
| `reviewer_model` | text | |
| `review_verdict` | text NOT NULL DEFAULT 'pending' | CHECK: `pending` \| `pass` \| `rewritten` \| `fail` |
| `tightness` | real | Tier 0 similarity of the reviewer's blind back-translation to `l2_text`, 0–1 |
| `entailment_ok` | boolean | reviewer's mutual-entailment judgement |
| `is_active` | boolean NOT NULL DEFAULT false | at most one active per (sentence_id, l1_language_id): partial unique index |
| `run_id` | text | RUN directory name (provenance) |
| `created_at` | timestamptz | |

### Changed: `dt_passage`

Add `sentence_start smallint NULL`, `sentence_end smallint NULL` (inclusive index range in
`test_sentences` for `source_ref_id`), and a partial unique index on
`(source_ref_id, sentence_start, sentence_end)` where both are not null, so a range is created
once and reused. Existing rows keep NULLs.

### Changed: `tests`

Add `transcript_hash text` maintained by the cleanup script; no trigger (transcripts are edited
only by admin tooling).

Migration file: `migrations/test_sentence_references_schema.sql` (TASK-901, LIVE-DB,
approval-gated). Backfill: `scripts/build_test_sentences.py` (TASK-902).

## Generation harness

### Runner — `scripts/sentence_ref_runner.py` (TASK-903)

Mirrors `fat_seed_runner.py`. Commands, all file-based, none calling a hosted model:

| cmd | does |
|---|---|
| `export --language ja --l1 en --limit 30 --arm aligned --out-dir data/sentence_refs/ja/run_NN` | writes `worklist.csv` (test_id, title, n_sentences, sentences as JSON) from `test_sentences` via the admin client, skipping tests with an active reference for that L1 |
| `brief RUN [--width 6]` | writes `RUN/sentence_refs/briefs/author_NN.md` (6 tests each) + `rules_authoring.md` |
| `check RUN [--source docs|reviewed]` | deterministic validation (below); writes `check.json` |
| `review-pack RUN` | writes `RUN/sentence_refs/review_packs/review_NN.md` listing docs + `rules_review.md`; strips author notes |
| `assemble RUN` | merges reviewed docs + verdicts into `RUN/sentence_refs/upload.json` |
| `status RUN` | per test × L1: authored / checked / reviewed / assembled / uploaded |

### Document shape — `RUN/sentence_refs/docs/<test_id>.<l1>.json`

```json
{"test_id": "6eb4ff60-…", "l2": "ja", "l1": "en", "arm": "aligned", "prompt_version": "sr-1.0",
 "sentences": [
   {"idx": 0, "l2": "趣味で手作りした…有効です。", "l1": "If you want to turn the accessories you make as a hobby into income, building an online business is effective."},
   {"idx": 1, "l2": "まずは…", "l1": "First, start selling on the internet."}
 ],
 "author_notes": "optional, stripped before review"}
```

### Deterministic checks (`services/dual_translation/sentence_refs.py`, TASK-903)

- sentence count equals `test_sentences` count and indices are 0..n-1 in order;
- `l1_text` contains no code points of the L2 script (Han for zh, Han/kana for ja, Latin letters
  beyond proper nouns are allowed for en-L2 only); the check lists the offending characters;
- every Arabic numeral and every proper noun detected in `l2` (token-map senses with
  `part_of_speech` in the proper-noun set, plus katakana loanwords for ja) has a counterpart in
  `l1` (digit equality; loanword transliteration via a small table or a reviewer flag);
- no preamble patterns (`この文章は`, `本文`, `This passage`, `---`) in either side;
- length ratio `len(l1)/len(l2)` within per-pair bounds (fitted on the pilot; initial 1.5–6 for
  ja→en, 1.2–5 for zh→en);
- no sentence identical to another sentence's reference in the same doc.

### Review (skill `sentence-reference-review`, TASK-905)

Fresh context. For each document: (1) **blind back-translation** — the reviewer sees only the
L1 sentences and writes an L2 version of each; the runner computes Tier 0 character similarity
against `l2_text` (`services/dictation/grader` normalisation, same as DT Tier 0) → `tightness`;
(2) then the reviewer sees the gold and judges mutual entailment per sentence, flags additions,
omissions, register drift and any L2 leakage, and rewrites failed sentences; (3) writes
`RUN/sentence_refs/reviewed/<test_id>.<l1>.json` and a verdict record
`{sentence_idx, verdict, tightness, entailment_ok, changed}`. Items the deterministic checks
flagged, plus a stratified 15% sample, go to an Opus reviewer; the rest to Sonnet.

### Upload — `scripts/upload_sentence_references.py` (TASK-906)

Reads `upload.json`, resolves `sentence_id` by (test_id, idx) and verifies `transcript_hash`,
inserts `test_sentence_references` rows with provenance, deactivates any previous active row for
the same (sentence, L1) only when the new verdict is `pass` or `rewritten`, in one transaction
per test. `--dry-run` prints the plan; service role only.

### Pilot (TASK-907)

30 tests per language (ja, zh, en), L1 = en for ja/zh and zh for en, two arms:
`sentencewise` (author sees the passage, translates one sentence per turn of the document) and
`aligned` (author translates the passage and splits into the aligned array). Same reviewer skill,
blind to the arm. Report: tightness distribution, entailment pass rate, rewrite rate, leakage rate
per arm and language, in `wiki/evaluations/sentence-refs-pilot-YYYY-MM-DD.md`. Decision rule:
the arm with higher median tightness wins unless its entailment pass rate is more than 3 points
lower. Sets the tightness floor from the distribution.

### Second review of below-floor references — `scripts/sentence_ref_recheck.py` (TASK-908)

`export --out-dir RUN` reads every active `pass`/`rewritten` reference whose tightness is below
the Produce floor for its test language (`services.prestudy.PRODUCE_TIGHTNESS_FLOOR`: zh 0.70,
en 0.60, ja 0.65) and writes packs of 25: a blind file (the L1 target sentence with its L1
neighbours) and a gold file (the L2 sentence, its L2 neighbours, the current reference). An Opus
reviewer in a fresh context back-translates every target blind (`back/NN.json`), then judges
against the gold and rewrites loose references (`verdicts/NN.json`; `fail` only for a broken
gold). `score RUN` reruns the deterministic checks on each final reference, computes tightness
from the new back-translation and writes `upload.json` for the normal upload script, which
replaces only the rechecked sentences. A `fail` row is stored inactive, so the previous reference
stays served. Assemble/upload provenance: `author_model`, `arm` and `prompt_version` are taken
from the authored document in `docs/` when the reviewed copy lacks them (reviewers never open
`docs/`).

## API / RPC Surface

### `GET /api/tests/<slug>/sentences?l1=<code>`
- **Purpose:** sentences with the learner's L1 references for the preview and the Produce window
  chooser.
- **Returns:** `{sentences:[{idx, l2_text, char_start, char_end, token_start, token_end, reference:{l1_text, tightness} | null}]}`;
  `l2_text` is omitted when `?mode=produce` and the test's attempt for today is not yet
  submitted (same withholding rule as `?mode=dictation`).
- **Auth:** JWT. **Errors:** 404 unknown test; 409 if sentence hash ≠ transcript hash (stale).

### `POST /api/dual-translation/passage-from-sentences`
- **Body:** `{test_id, sentence_start, sentence_end, l1_language_id, primed_sense_ids[]}`
- **Purpose:** find or create the `dt_passage` for the range, verify every sentence has an
  active `pass`/`rewritten` reference for that L1, store `primed_sense_ids` on the session.
- **Returns:** `{passage_id, l1_text, n_sentences}`; never `l2_text`.
- **Errors:** 422 if a sentence lacks a reference (the client falls back to the best fully
  covered window); 403 if the test is not attempted (DT's existing rule).
- **Side effects:** `dt_passage` insert (range columns set), nothing else.

### Changed: window selection (`services/dual_translation/passage_builder.py`)
`select_window_for_primed(test_id, primed_sense_ids, l1_language_id, min=2, max=4)`: score each
range by primed senses covered ×10 + wrong-question senses ×3 − chars/100, require full reference
coverage and mean tightness ≥ floor, return the best. Pure function over `test_sentences` rows;
unit-tested against the demo's five tests.

### Changed: `GET /api/dual-translation/next` serves sentence windows (TASK-976, 2026-11-17)

Before: `/next` served only `dt_passage` rows that had a stored `dt_passage_reference`. That
table is empty in production (0 rows on 2026-11-17; every remaining `dt_passage` is a range
passage made by Produce), so `/next` returned 404 to every learner.

Now `_select_next_passage(db, user_id, l1_language_id, l2_language_id=None)`:

1. Candidates: the user's most recently attempted tests (`test_attempts.created_at` desc,
   distinct, at most `NEXT_WINDOW_MAX_TESTS = 30`), active, not in the L1, and in
   `l2_language_id` when the client sends `?language_id=` (the session player sends
   `ctx.languageId`; the standalone page sends `localStorage.selectedLanguageId`).
2. Material: one embedded read, `test_sentence_references` (active, verdict `pass`/`rewritten`,
   the L1) `!inner` `test_sentences` filtered by `test_id IN candidates`. Rows whose
   `transcript_hash` differs from `tests.transcript_hash` are dropped.
3. Windows: `passage_builder.plan_sentence_windows(idxs, refs_ok, tightness, floor)`: runs of
   consecutive covered sentences, each packed into fixed 2–4 sentence windows by
   `window_sentences`; a window is kept only when its mean tightness ≥ the Produce floor for the
   test language (same rule as `select_window_for_primed`).
4. Choice: `passage_builder.pick_next_window(candidates, practised)`: the first window, in
   candidate then transcript order, none of whose sentences the user has practised; else the
   window whose latest practice is oldest. "Practised" = any `dt_submission` (last 500) with a
   non-empty reproduction or a `skipped_at`, on a range passage, sentence-level (so a Produce
   window 2–3 also marks window 0–3 as practised). An opened but unanswered submission does not
   count, so a reload gets the same window.
5. The `dt_passage` for the range is found or created exactly as `passage-from-sentences` does
   (`_find_or_create_range_passage`); a non-active range passage is not served. `l1_text` is the
   joined references. Response shape unchanged.
6. Nothing found → the legacy `dt_passage_reference` path (kept; currently finds nothing).

Tests: `tests/test_dt_next_sentence_windows.py` (21), `tests/unit/session-dt-player.test.js`
(+2). Live read-only check for the main learner on 2026-11-17: 30 candidate tests, 26 with
references, 57 windows, 18 never practised.

### Changed: grader target words (TASK-910)
`grade(submission, target_sense_ids)`: after the cascade, for each target sense locate its
surface in the gold (token map) and in the reproduction (exact surface, else lemma, else
`dt_error_instance` span overlap) → `produced` / `variant` / `omitted`; write one
`user_vocabulary_knowledge` evidence row per sense with the exercise-evidence parameters for the
`contextual_use` family and `exercise_attempts.source = 'prestudy_produce'`.

## Key Architectural Decisions

1. **Sentence grain, assembled windows** — see [[decisions/ADR-037-sentence-level-l1-references]].
2. **Claude agents + skills for bulk content; OpenRouter only for live grading** — developer
   decision 2026-10-30; keeps bulk work off the shared credit account and inside the reviewed
   authoring pattern that word assets use.
3. **Tightness as the quality number** — a reference is good for dual translation when a
   competent back-translation lands near the gold; entailment alone accepts loose paraphrase.
4. **Reviewer blind first, then with gold** — the back-translation must precede seeing the L2,
   or tightness is contaminated (same trap as the unknown-share snapshot).

## Security Considerations

Service-role writes only (ADR-034); RLS on both new tables; no client write path. The sentences
endpoint withholds `l2_text` in produce mode exactly as dictation withholds the transcript.
Reviewer and author documents are repository files, never executed.

## Testing Strategy

- Unit: segmentation spans reproduce the transcript byte-for-byte for every active test (fixture
  from the five demo tests plus one preamble case); deterministic checks reject each failure
  class with a named reason; window selector picks the expected range on the demo fixtures;
  tightness computation equals the dictation grader's normalisation.
- Integration: `export → brief → check → review-pack → assemble → upload --dry-run` on an
  8-test slice with hand-written docs; `passage-from-sentences` creates once and reuses.
- Pilot report as the acceptance gate for the full run.

## Related Pages

- [[features/test-sentence-references]] — prose
- [[decisions/ADR-037-sentence-level-l1-references]]
- [[tasklist/test-sentence-references.tasks]]
- [[features/dual-translation.tech]] — `dt_*` schema, cascade
- [[features/test-prestudy]] — the workflow
- [[features/csv-exercise-authoring.tech]] — the staged authoring pattern
