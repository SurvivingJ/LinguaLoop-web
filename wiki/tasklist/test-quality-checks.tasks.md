---
title: "Test Quality Checks — Task Breakdown"
feature: test-quality-checks
prose_page: ../features/test-quality-checks.md
tech_page: ../features/test-quality-checks.tech.md
total_tasks: 11
done: 0
---

# Test Quality Checks — Task Breakdown

Deterministic, model-free checks for comprehension tests in **all languages (zh, en, ja)**, run
at generation time (every tier, including T1) and over the existing library by a read-only audit.
Motivated by [[evaluations/ja-test-review-2026-11-09]]: ~45 of the 79 minor defects found there
are mechanically detectable. Live library at time of writing: zh 125 tests / 616 questions,
en 121 / 551, ja 58 / 253.

Sequence: framework (912) → checks (913–918, parallelisable) → audit (919) → calibration (920)
→ wiring (921) → remediation of existing content (922). Wiring comes **after** calibration so the
generator never rejects on an unmeasured rule.

---

## TASK-912: Check framework — `quality_checks.py`, profiles, modes

**Status:** [ ] Not Started
**Feature:** test-quality-checks
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
Create the pure module every later task adds to: the `CheckResult` dataclass, `LanguageProfile`
for ja/zh/en, the `CHECK_MODES` table and the three runner functions. No checks yet beyond a
trivial one used to prove the plumbing.

**Acceptance Criteria:**
- [ ] `services/test_generation/quality_checks.py` exports `CheckResult`, `LanguageProfile`, `get_profile`, `CHECK_MODES`, `run_passage_checks`, `run_question_checks`, `run_test_checks` exactly as in the tech spec.
- [ ] `get_profile('ja'|'zh'|'en')` returns the profile from the spec table; unknown code raises `KeyError`.
- [ ] `profile.tokenize` returns char bigrams for ja/zh (whitespace and punctuation stripped, fullwidth included) and lowercase `\w+` words for en.
- [ ] Check registration is a decorator `@check(code, scope)`; runners iterate the registry, skip codes whose mode is `'off'`, and stamp `severity` from `CHECK_MODES` (default `'flag'`).
- [ ] Module imports nothing from `services.*` that touches the DB or network.

**Technical Notes:**
`CheckResult` is `@dataclass(frozen=True)` with `to_dict()` for JSON. Keep check functions
signature-uniform: question checks `(q, passage, profile, tier) -> list[CheckResult]` (index is
filled in by the runner), test checks `(questions, passage, profile, tier)`.

**Files to Create / Modify:**
- `services/test_generation/quality_checks.py` — new.
- `tests/test_quality_checks.py` — new; profile/tokenizer/registry tests.

**Verification:**
`pytest tests/test_quality_checks.py -q` passes; `python -c "from services.test_generation.quality_checks import get_profile; print(get_profile('ja').tokenize('文中の意味'))"` prints bigrams.

---

## TASK-913: Script checks — `foreign_script`, `latin_in_cjk`, `script_above_level`

**Status:** [ ] Not Started
**Feature:** test-quality-checks
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-912

**Description:**
Catch text in the wrong writing system: simplified-Chinese characters in Japanese, traditional
characters or kana in Chinese, CJK in English, stray English words in ja/zh questions, and kanji
choices on an all-hiragana Japanese passage.

**Acceptance Criteria:**
- [ ] ja: `纹理` and `質的变化` fire `foreign_script`; `紋理`, `変化` do not (rule: char not encodable in `euc_jis_2004`).
- [ ] zh: any kana fires; a traditional char (`這`, `們`) fires; the t2s-ambiguous allowlist (`乾 著 於 隻` to start) does not.
- [ ] en: any CJK/kana char fires.
- [ ] `latin_in_cjk` fires on `"dramatize"` / `"sandwich"` in a ja choice and stays silent when the Latin run also appears in the passage (e.g. `AI`, `DNA`).
- [ ] `script_above_level` fires on the robot test (passage `あたらしいロボットは、おうちで…`, choice `心を許せる存在`) and is silent when the passage contains any kanji.
- [ ] Each runs on stem + choices + answer (question scope) and `foreign_script` also on transcript and title (passage scope).

**Technical Notes:**
zh is stored simplified (live check 2026-11-09: 125/125 active zh transcripts contain simplified
markers, 0 traditional). OpenCC is `opencc==1.3.1` in requirements; build the converter once at
module load (`OpenCC('t2s')`), compare per character. Stem templates are excluded from
`script_above_level` — they are fixed per language and need their own decision (see TASK-922 notes).

**Files to Create / Modify:**
- `services/test_generation/quality_checks.py` — three checks.
- `tests/test_quality_checks.py` — fixtures above.

**Verification:**
`pytest tests/test_quality_checks.py -q -k script`.

---

## TASK-914: Choice-format checks — `choice_label_prefix`, `answer_length_outlier`, `absolute_distractors`

**Status:** [ ] Not Started
**Feature:** test-quality-checks
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-912

**Description:**
Catch choices that give the answer away by form rather than content, and choices carrying their
own letter labels.

**Acceptance Criteria:**
- [ ] `QuestionValidator.fix_question` strips a leading label (`A. `, `(B)`, `Ｃ．`, `1)`, `①`) from all four choices and the answer when **all four** choices carry one; answer still matches a choice afterwards.
- [ ] `choice_label_prefix` fires only if a label survives `fix_question` (e.g. only two choices labelled).
- [ ] `answer_length_outlier` fires on parametric q2 pre-fix shape (answer much longer than distractors) and not on a set of four similar-length choices; thresholds exactly as in the tech spec.
- [ ] `absolute_distractors` fires when ≥ 2 distractors contain profile absolutes (`すべて`, `完全に`; `所有`, `绝对`; `always`, `never`) and the answer has none; silent when the answer also contains one.
- [ ] The two existing `logger.debug` length heuristics in `_validate_content` are removed (superseded).

**Technical Notes:**
Length unit = chars for CJK, words for en (`profile.is_cjk`). For absolutes in en, match whole
words, case-insensitive; in ja/zh, substring match.

**Files to Create / Modify:**
- `services/test_generation/quality_checks.py`
- `services/test_generation/agents/question_validator.py` — `fix_question` label stripping; delete debug heuristics.
- `tests/test_quality_checks.py`

**Verification:**
`pytest tests/test_quality_checks.py -q -k "label or length or absolute"`.

---

## TASK-915: `answer_copies_passage`

**Status:** [ ] Not Started
**Feature:** test-quality-checks
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-912

**Description:**
Flag main-idea, inference, author's-purpose and supporting-detail questions whose correct answer
is lifted from the passage while the distractors are not — learners can pick it by string
matching.

**Acceptance Criteria:**
- [ ] Uses `difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(...)` over characters (CJK) or token lists (en).
- [ ] Fires when answer's longest common run ≥ `profile.copy_min_len` (10 chars / 6 words) **and** ≥ 2 × the best distractor's run.
- [ ] Skips `literal_detail` and `vocabulary_context`.
- [ ] Fixture: the online-craft q3 answer containing `誰に何を求めているか` copied from the passage fires; a paraphrased answer does not.

**Files to Create / Modify:**
- `services/test_generation/quality_checks.py`
- `tests/test_quality_checks.py`

**Verification:**
`pytest tests/test_quality_checks.py -q -k copies`.

---

## TASK-916: Vocabulary target check — fullwidth brackets and CJK span length

**Status:** [ ] Not Started
**Feature:** test-quality-checks
**Type:** bug
**Complexity:** XS (<1h)
**Depends On:** none

**Description:**
`check_quoted_phrase_in_passage` misses ja stems that mark the target with `（…）`
(`文中の（他の人）の意味…`), and its "≤ 6 words" span limit is meaningless for CJK (a 30-char
span is one "word"). Fix both. This check already rejects and stays rejecting.

**Acceptance Criteria:**
- [ ] For `vocabulary_context` only, `（…）` and `(…)` spans are extracted in addition to the existing quote marks.
- [ ] Span-length limit: ≤ 6 words when the span contains spaces, ≤ 12 chars otherwise.
- [ ] A ja vocab stem with `（存在しない語）` is rejected; `（他の人）` against the organ-donation passage passes.
- [ ] Non-vocab question types are unaffected (parentheses in other stems are not checked).

**Technical Notes:**
`check_quoted_phrase_in_passage` takes no type today; add `include_brackets: bool = False` and
pass `True` from the `vocabulary_context` branch in `validate_question`.

**Files to Create / Modify:**
- `services/test_generation/agents/question_validator.py`
- `tests/test_question_validator.py` — create if absent.

**Verification:**
`pytest tests/test_question_validator.py -q`.

---

## TASK-917: Within-test duplicates — `duplicate_answer`, `duplicate_vocab_target`, `duplicate_stem`

**Status:** [ ] Not Started
**Feature:** test-quality-checks
**Type:** bug
**Complexity:** M (3-8h)
**Depends On:** TASK-912, TASK-916

**Description:**
The biggest group in the ja review (28 of 79 minor issues) is two questions in one test asking
the same thing. Today's `_check_overlap` cannot see it: it compares question *stems* with
`str.split()`, which is a single token for ja/zh, and rotated stems would collide anyway.
Compare *answers* (and vocab targets) instead, with a language-aware tokenizer.

**Acceptance Criteria:**
- [ ] `duplicate_answer`: Jaccard of `profile.tokenize(answer_i)` vs `answer_j` ≥ 0.6 fires; same `type_code` pairs use 0.45. Result names both question indices in `message`.
- [ ] `duplicate_vocab_target`: two `vocabulary_context` questions with the same extracted span fire.
- [ ] `duplicate_stem`: `_check_overlap` uses `profile.tokenize`; only compared for `literal_detail` / `supporting_detail` pairs; threshold 0.65 unchanged.
- [ ] Fixtures from the review fire: great-wall q1/q2 (identical), peanut-butter q3/q4 and haute-couture q3/q4 (two `author_purpose` with near-identical keys); a normal 5-question test does not.
- [ ] Each check also has a pairwise helper `(q, previous: list[dict], profile)` so the generator can catch a duplicate before accepting the question (used in TASK-921).

**Technical Notes:**
Pull the target-span extractor out of `check_quoted_phrase_in_passage` into a shared
`extract_vocab_target(question_text) -> Optional[str]`. Keep `_check_overlap`'s signature working
for callers that don't pass a profile (fall back to `str.split()`), so T1's documented Jaccard
behaviour (orchestrator ~747) doesn't change until TASK-921 opts in.

**Files to Create / Modify:**
- `services/test_generation/quality_checks.py`
- `services/test_generation/agents/question_validator.py`
- `tests/test_quality_checks.py`

**Verification:**
`pytest tests/test_quality_checks.py tests/test_question_validator.py -q -k duplicate`.

---

## TASK-918: Test-shape checks — `type_mix`, `too_few_questions`, `missing_title`

**Status:** [ ] Not Started
**Feature:** test-quality-checks
**Type:** feature
**Complexity:** XS (<1h)
**Depends On:** TASK-912

**Description:**
Flag tests whose question set is badly shaped: two author's-purpose questions, no literal or
supporting-detail question, fewer than 4 questions above T1, or no title.

**Acceptance Criteria:**
- [ ] `type_mix` fires on > 1 `author_purpose`, or on ≥ 4 questions with neither `literal_detail` nor `supporting_detail`.
- [ ] `too_few_questions` fires on < 4 questions at tier ≥ 2 only.
- [ ] `missing_title` (passage scope) fires on `None` / whitespace title.
- [ ] Read-only SQL in the task notes run once against live: report whether any `question_type_distributions_by_tier` row requests more than one `author_purpose`. Record the result in the log entry; if any do, raise it with the developer (that table is a design decision, not a fix this task makes).

**Technical Notes:**
Inspect the table's columns first (`select * from question_type_distributions_by_tier limit 5`)
and write the aggregate from what is there. `report_question_mix` (question_mix.py) compares
realised vs requested; `type_mix` is the content rule and must fire on legacy tests generated
before that table existed.

**Files to Create / Modify:**
- `services/test_generation/quality_checks.py`
- `tests/test_quality_checks.py`

**Verification:**
`pytest tests/test_quality_checks.py -q -k "mix or few or title"`.

---

## TASK-919: Read-only library audit — `scripts/audit_test_quality.py`

**Status:** [ ] Not Started
**Feature:** test-quality-checks
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** TASK-913, TASK-914, TASK-915, TASK-916, TASK-917, TASK-918

**Description:**
Run every check over every active test in every language and write a report. This is the tool
for measuring the library and for calibrating thresholds. It must never write to the DB.

**Acceptance Criteria:**
- [ ] CLI: `--lang {zh,en,ja,all}` (default all), `--test-id UUID` (repeatable), `--limit N`, `--out DIR` (default `data/test_quality/audit_<YYYY-MM-DD>/`), `--include-inactive`.
- [ ] Reads `tests` (id, slug, title, transcript, language_id, target_age_tier, is_active) and `questions` (id, test_id, question_id, question_type_id, question_text, choices, answer) via the service client, paged 500 rows at a time; maps `question_type_id` → `type_code` via `dim_question_types`.
- [ ] Runs passage, question and test checks with `CHECK_MODES` **forced to `'flag'` for every code** (the audit reports; it doesn't gate).
- [ ] Writes `findings.csv` (`language, slug, test_id, question_id, scope, code, field, message`) and `summary.md` (counts by language × code; tests with ≥ 1 finding; top 10 tests by finding count).
- [ ] `grep -nE "\.(insert|update|upsert|delete)\(" scripts/audit_test_quality.py` returns nothing.
- [ ] Full run over ~304 tests completes in < 2 minutes.

**Technical Notes:**
Reuse the client construction from an existing read-only script (e.g. `scripts/audit_transcript_preambles.py`).
Tier for checks = `target_age_tier`; if NULL, treat as ≥ 2 and note it in the summary.

**Files to Create / Modify:**
- `scripts/audit_test_quality.py` — new.
- `tests/test_audit_test_quality.py` — runs the report builder on an in-memory fixture of 2 tests.

**Verification:**
`python scripts/audit_test_quality.py --lang ja --limit 5` writes both files; open `summary.md`.

---

## TASK-920: Calibrate against the ja gold set; set `CHECK_MODES`

**Status:** [ ] Not Started
**Feature:** test-quality-checks
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** TASK-919

**Description:**
Measure each check's precision on real content and decide which ones may reject. ja is scored
against the 2026-11-09 review; zh and en (no gold set) by hand-sampling flags.

**Acceptance Criteria:**
- [ ] Full audit run committed under `data/test_quality/audit_<date>/`.
- [ ] ja: join `findings.csv` to `data/test_quality/ja_review_2026-11-09.csv` on `question_id` (excluding the 12 re-keyed questions and the deleted sovereignty test — listed in [[evaluations/ja-test-review-2026-11-09]]); per check report true positives, false positives, and review issues in that check's group that it missed.
- [ ] zh, en: for each check with ≥ 1 finding, hand-label up to 20 findings (all if fewer) as real / false alarm.
- [ ] Rule: a check moves to `'reject'` only with precision ≥ 0.9 over ≥ 10 labelled findings across languages; otherwise stays `'flag'`; a check with precision < 0.5 goes to `'off'` and gets a note on why.
- [ ] `CHECK_MODES` updated in code; t2s allowlist and absolute-word lists extended from false positives found.
- [ ] Results filed as `wiki/evaluations/test-quality-checks-calibration-<date>.md` (per-check table: language, findings, labelled, precision, decision).

**Verification:**
The evaluation page exists and every code in `CHECK_MODES` has a row with its decision.

---

## TASK-921: Wire checks into generation and the review queue

**Status:** [ ] Not Started
**Feature:** test-quality-checks
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-920

**Description:**
Run the checks while tests are generated, at every tier: reject-mode question checks trigger the
existing regenerate loop, flag-mode results go to `generation_review_queue`, test-level duplicates
drop the later question, a passage in the wrong script skips the test.

**Acceptance Criteria:**
- [ ] `QuestionValidator.validate_question` accepts optional `language_code`, `tier`, `previous` keyword args (old positional call still works) and behaves as in the tech spec "Wiring" section.
- [ ] `question_generator.py` validator call (~line 411) passes them; a reject-mode finding produces the existing `stage: 'validator'` rejection record and a regeneration attempt.
- [ ] Orchestrator runs `run_passage_checks` after prose generation and `run_test_checks` after `validate_all_questions`; a reject `duplicate_*` drops the later question, then the existing survival floor applies.
- [ ] `_write_review_queue_rows` writes rows for questions with `_quality_flags` (alone or with `_judge_flags`); `flag_reasons` has `qc:<code>` entries; `judge_scores.quality_checks` holds the result dicts.
- [ ] Checks run when `tier_id == 1` (no dependency on `run_judges`).
- [ ] A 6-test run per language (`python scripts/run_test_generation_cli.py --language <zh|en|ja> --count 6 --type reading`, one test per tier 1–6) completes; record realised rejects/flags per check and whether any test fell below the survival floor because of a new check. (Writes real tests — confirm with the developer before running.)

**Technical Notes:**
Watch T1: the survival floor is 3 of 5 and the orchestrator comment (~747) records T1
literal_detail questions colliding on Jaccard. Only checks calibrated to `reject` can cost a
question, so this is the place to confirm calibration held.

**Files to Create / Modify:**
- `services/test_generation/agents/question_validator.py`
- `services/test_generation/agents/question_generator.py`
- `services/test_generation/orchestrator.py`
- `tests/test_question_validator.py`, plus an orchestrator-level test with a stubbed generator returning a duplicate pair.

**Verification:**
`pytest -q tests/test_question_validator.py tests/test_quality_checks.py`; the 5-test run log
shows `qc:` reasons in `generation_review_queue` (read-only SQL:
`select flag_reasons, count(*) from generation_review_queue where created_at > now() - interval '1 day' group by 1`).

---

## TASK-922: Remediate existing content from the audit (LIVE-DB, approval)

**Status:** [ ] Not Started
**Feature:** test-quality-checks
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-920

**Description:**
Turn the calibrated audit into fixes for the live library across all three languages. Mechanical
defects are fixed by SQL; content defects are queued for regeneration (or the planned
test-authoring skill). The developer applies SQL by hand.

**Acceptance Criteria:**
- [ ] `data/test_quality/remediation_<date>.sql`: one transaction; strips choice label prefixes (and the matching answer) where all four choices carry one; ends with a verify query showing 0 answers outside choices for touched rows.
- [ ] `data/test_quality/remediation_<date>.csv`: every remaining finding with precision-qualified checks, classed `regenerate_question` / `regenerate_test` / `retire_test` / `ignore` with a one-line reason. `duplicate_answer` pairs → `regenerate_question` for the later one; `foreign_script` in a transcript → `regenerate_test`.
- [ ] Before any delete/retire: references checked against **every** FK onto `tests`, `test_attempts` and `questions` (`word_quiz_results`, `question_attempt_results`, `daily_test_load_items`, `token_transactions`, `user_word_watchlist` — the 2026-11-09 delete failed on `word_quiz_results`). Prefer `is_active = false` over delete for tests with attempts.
- [ ] Developer approves and applies; afterwards re-run the audit and record before/after counts in the log.

**Technical Notes:**
The ja kana/kanji level of **stem templates** (`文中の「…」の意味として最も適切なものを選んでください` on T1 hiragana tests) is not fixable by SQL on questions — note it in the CSV and raise it for a per-tier template decision.

**Files to Create / Modify:**
- `data/test_quality/remediation_<date>.sql`, `data/test_quality/remediation_<date>.csv`

**Verification:**
Post-apply audit `summary.md` shows the remediated codes reduced to the `ignore`d residue.
