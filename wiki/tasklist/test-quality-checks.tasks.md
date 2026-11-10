---
title: "Test Quality Checks — Task Breakdown"
feature: test-quality-checks
prose_page: ../features/test-quality-checks.md
tech_page: ../features/test-quality-checks.tech.md
total_tasks: 16
done: 14
---

# Test Quality Checks — Task Breakdown

Deterministic, model-free checks for comprehension tests in **all languages (zh, en, ja)**, run
at generation time (every tier, including T1) and over the existing library by a read-only audit.
Motivated by [[evaluations/ja-test-review-2026-11-09]]: ~45 of the 79 minor defects found there
are mechanically detectable. Live library at time of writing: zh 125 tests / 616 questions,
en 121 / 551, ja 58 / 253.

Sequence: framework (912) → checks (913–918, parallelisable) → audit (919) → calibration (920)
→ wiring with a switchable mode (921) → experiment harness (923) → **check-mode experiment (924)**
→ remediation of existing content (922). In parallel after 923: level-specific templates
(925 mechanism → 926 authoring → **template experiment 927**).

Developer decisions 2026-11-09: (1) breakdown approved; *which* check mode ships is settled by an
experiment, not by the calibration rule alone (TASK-924); (2) when two questions in a test
duplicate each other, **drop the second one**; (3) write level-specific question templates
([[decisions/ADR-040-tier-keyed-question-templates]], TASK-925–927).

---

## TASK-912: Check framework — `quality_checks.py`, profiles, modes

**Status:** [x] Done (2026-11-09)
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

**Status:** [x] Done (2026-11-09)
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

**Status:** [x] Done (2026-11-09)
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

**Status:** [x] Done (2026-11-09) — thresholds changed by calibration: 15 chars CJK, T3+ only
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

**Status:** [x] Done (2026-11-09)
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

**Status:** [x] Done (2026-11-09)
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

**Status:** [x] Done (2026-11-09)
**Feature:** test-quality-checks
**Type:** feature
**Complexity:** XS (<1h)
**Depends On:** TASK-912

**Description:**
Flag tests whose question set is badly shaped: two author's-purpose questions, no literal or
supporting-detail question, fewer than 4 questions above T1, or no title.

**Acceptance Criteria:**
- [ ] `type_mix` fires on > 1 `author_purpose`, > 1 `main_idea` (a passage has one main idea), or on ≥ 4 questions with neither `literal_detail` nor `supporting_detail`.
- [ ] `too_few_questions` fires on < 4 questions at tier ≥ 2 only.
- [ ] `missing_title` (passage scope) fires on `None` / whitespace title.
- [x] Live table checked 2026-11-09 (`question_type_distributions_by_tier`, columns `tier_id, question_type_1..5`): no tier requests more than one `author_purpose`. **T3 requests `main_idea` twice** (and T5, T6 request `inference` twice). So `type_mix` will fire on every new T3 test until the table changes — raise with the developer before TASK-921 makes it reject; until then it stays `flag`.

**Technical Notes:**
`report_question_mix` (question_mix.py) compares
realised vs requested; `type_mix` is the content rule and must fire on legacy tests generated
before that table existed.

**Files to Create / Modify:**
- `services/test_generation/quality_checks.py`
- `tests/test_quality_checks.py`

**Verification:**
`pytest tests/test_quality_checks.py -q -k "mix or few or title"`.

---

## TASK-919: Read-only library audit — `scripts/audit_test_quality.py`

**Status:** [x] Done (2026-11-09)
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

**Status:** [x] Done (2026-11-09) — see [[evaluations/test-quality-checks-calibration-2026-11-09]]
**Feature:** test-quality-checks
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** TASK-919

**Outcome (2026-11-09):** 242 findings sampled (≤ 20 per check × language), labelled real / false alarm by three fresh-context reviewers (one per language). Thresholds retuned from the false-alarm patterns; five checks moved to `reject`. Full table: [[evaluations/test-quality-checks-calibration-2026-11-09]]. The answer-copy and length checks were tuned on the same labels, so their precision is in-sample — TASK-924 is the out-of-sample test.

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

**Status:** [x] Done (repo, 2026-11-09) — the live smoke run is not done: generation needs an OpenRouter key this environment lacks
**Feature:** test-quality-checks
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-920

**Description:**
Run the checks while tests are generated, at every tier: reject-mode question checks trigger the
existing regenerate loop, flag-mode results go to `generation_review_queue`, test-level duplicates
drop the later question, a passage in the wrong script skips the test.

**Acceptance Criteria:**
- [ ] Mode is switchable per run: env `TEST_QC_MODES` = `flag` (all checks flag) | `reject` (all checks reject) | `calibrated` (use `CHECK_MODES`, the default). Read once per batch and logged at batch start; the CLI's `--qc-modes` (TASK-923) sets it.
- [ ] `QuestionValidator.validate_question` accepts optional `language_code`, `tier`, `previous` keyword args (old positional call still works) and behaves as in the tech spec "Wiring" section.
- [ ] `question_generator.py` validator call (~line 411) passes them; a reject-mode finding produces the existing `stage: 'validator'` rejection record and a regeneration attempt.
- [ ] Orchestrator runs `run_passage_checks` after prose generation and `run_test_checks` after `validate_all_questions`; a reject `duplicate_*` **drops the second question of the pair (developer decision 2026-11-09)** — never regenerates the whole test — then the existing survival floor applies.
- [ ] `_write_review_queue_rows` writes rows for questions with `_quality_flags` (alone or with `_judge_flags`); `flag_reasons` has `qc:<code>` entries; `judge_scores.quality_checks` holds the result dicts.
- [ ] Checks run when `tier_id == 1` (no dependency on `run_judges`).
- [ ] Smoke run with `--dry-run` per language completes with checks active (no DB writes). The measured runs are TASK-924.

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

**Status:** [x] Done — SQL applied by developer 2026-11-10, verified live (the 133 tests needing regeneration remain in the CSV)
**Feature:** test-quality-checks
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-920, TASK-924

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

---

## TASK-923: Experiment harness — inactive runs, fixed topics, arm-blind review, scoring

**Status:** [x] Done (repo, 2026-11-09)
**Feature:** test-quality-checks
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** TASK-919, TASK-921

**Implementation note (2026-11-09):** added `--no-dedup` as well — arms generate the same topic and tier on purpose, and passage dedup (keyed on topic + tier, inactive tests included) would otherwise mark arm B a duplicate of arm A. Topic lists `data/test_quality/experiments/e1_topics.json` / `e2_topics.json` and the runbook `README.md` are committed. Cost is attributed per arm by run window, so arms run one after another.

**Description:**
Everything both experiments (TASK-924, TASK-927) need: generate the same topics under different
arms without exposing the tests to learners, review the output without the reviewer knowing the
arm, and score the arms on one sheet.

**Acceptance Criteria:**
- [ ] `scripts/run_test_generation_cli.py` gains `--inactive` (tests inserted with `is_active = false`), `--topics-file PATH` (JSON list of `{topic_id, tier}`; generates exactly those, in order, ignoring `--count`/`--tier`), `--qc-modes {flag,reject,calibrated}` (sets `TEST_QC_MODES`), `--tier-templates {on,off}` (sets `TEST_GEN_TIER_TEMPLATES`, TASK-925) and `--run-tag TAG`.
- [ ] With `--run-tag`, every generated test id, arm settings, wall clock and survival outcome (including tests that failed the floor) are appended to `data/test_quality/experiments/<TAG>/tests.jsonl`.
- [ ] `scripts/build_experiment_review_packs.py <TAG>...`: merges the runs, shuffles, strips arm labels, and writes review packs of ~15 tests each (`review_NN.md`) with the 2026-11-09 rubric (per question: ok / minor / major + group from [[evaluations/ja-test-review-2026-11-09]] + a `level_fit` verdict: ok / too hard / too easy) and a hidden key file mapping test → arm.
- [ ] `scripts/score_experiment.py <TAG>...` writes `summary.md`: per arm × language × tier — tests attempted, tests failing the survival floor, regenerations per question, $ per test (from `llm_calls`), audit findings per 100 questions (re-run `audit_test_quality.py --test-id …`), review major/minor rates and level-fit rate, with 95% bootstrap intervals for the rates.
- [ ] `--dry-run` still writes nothing.

**Technical Notes:**
Reviews are done by Claude reviewer subagents in fresh contexts, one pack each, like the
2026-11-09 review (no OpenRouter spend for review). Generation itself spends OpenRouter credit —
each experiment task states its budget up front.

**Files to Create / Modify:**
- `scripts/run_test_generation_cli.py`, `services/test_generation/orchestrator.py` (honour `inactive`)
- `scripts/build_experiment_review_packs.py`, `scripts/score_experiment.py` — new
- `tests/test_experiment_scoring.py` — scoring on a synthetic two-arm fixture

**Verification:**
`python scripts/run_test_generation_cli.py --language en --topics-file f.json --inactive --run-tag smoke --dry-run`;
`python scripts/score_experiment.py smoke` on a fixture produces `summary.md`.

---

## TASK-924: Experiment E1 — which check mode should generation ship with? (LIVE writes, approval)

**Status:** [?] Blocked — needs an OpenRouter key and budget approval (est. $2–5); migrations are in
**Feature:** test-quality-checks
**Type:** test
**Complexity:** L (1-2d)
**Depends On:** TASK-923

**Description:**
Generate the same topics under three check modes and pick the one that produces the best tests at
acceptable cost: **A** `flag` (control: today's behaviour plus review-queue rows), **B** `calibrated`
(TASK-920's `CHECK_MODES`), **C** `reject` (every check rejects).

**Acceptance Criteria:**
- [ ] Topics file: 12 topics per language (2 per tier T1–T6), unused by any active test; same file for all three arms. 3 arms × 3 languages × 12 = **108 tests**, all `--inactive`. Developer approves the run and its OpenRouter budget before it starts.
- [ ] Review: all 108 tests reviewed arm-blind via TASK-923 packs.
- [ ] Decision rule, written into the evaluation before unblinding: choose the arm with the lowest (major + minor) per question; **but** reject an arm whose survival-floor failure rate exceeds 10% of tests or whose $/test exceeds 1.5 × arm A. A tie (overlapping 95% intervals) goes to the cheaper arm. The rule may pick different arms per tier band (T1–T3, T4–T6) if the data say so.
- [ ] Winning modes written into `CHECK_MODES` / the default of `TEST_QC_MODES`.
- [ ] Clean-up: the winning arm's tests that the review rated with no major issues are activated; all other experiment tests are deleted (inactive, no attempts — check `test_attempts` count = 0 first).
- [ ] Results: `wiki/evaluations/test-qc-mode-experiment-<date>.md`.

**Verification:**
The evaluation page has the pre-registered rule, the per-arm table and the decision; `CHECK_MODES` in code matches it.

---

## TASK-925: Tier-keyed question templates — migration + loader (LIVE-DB, approval)

**Status:** [x] Done — applied 2026-11-10, verified live
**Feature:** test-quality-checks
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** none

**Implementation note (2026-11-09):** the existing unique index `(task_name, language_id, version)` is kept — other migrations upsert `ON CONFLICT` on it — so tier rows use their own version range, 100 + tier. Readers that can see `question_*` rows (`prompt_service.get_template_config` / `get_template_text`, the test-generation loader) filter `tier_id IS NULL` through `prompt_service.base_rows`, which is skipped until the column exists. `TEST_GEN_TIER_TEMPLATES` accepts `off`, `on`/`all`, or a comma list of language codes. Banded stems live in `stem_rotation.TIER_STEM_POOLS` (main_idea: ja 1-2 kana-only, ja 3-3, zh 1-3, en 1-3).

**Description:**
Implement [[decisions/ADR-040-tier-keyed-question-templates]]: `prompt_templates.tier_id`, a
tier-aware loader for question templates behind `TEST_GEN_TIER_TEMPLATES` (default off), and
tier-banded stem pools.

**Acceptance Criteria:**
- [ ] `migrations/prompt_templates_tier_id.sql`: `alter table prompt_templates add column tier_id smallint null references dim_complexity_tiers(id)`; index on `(task_name, language_id, tier_id, is_active)`. Idempotent (`if not exists`). Developer applies.
- [ ] `DatabaseClient.get_prompt_template(task_name, language_id, required=True, tier_id=None)`: when `tier_id` is given **and** `TEST_GEN_TIER_TEMPLATES` is on, tries the exact-tier row first; otherwise and on miss, uses only `tier_id IS NULL` rows (so existing behaviour is unchanged even after tier rows exist). English fallback unchanged.
- [ ] Every other reader of `prompt_templates` (grep `prompt_templates` and `get_prompt_template(` — 11 call sites today, plus `prompt_service.get_template_config` and `_resolve_models`) filters `tier_id IS NULL` unless it is the question-template path; a test proves model/provider resolution is unchanged when a tier row with a different `model` exists.
- [ ] Orchestrator passes `tier_id` when loading `question_{type}` templates (~line 696).
- [ ] `stem_rotation.STEM_POOLS` accepts an optional band level: `STEM_POOLS[lang][type]` may be a dict `{'1-3': (...), '4-6': (...)}`; `pick_stem` takes `tier` and resolves the band; a plain tuple keeps meaning "all tiers".

**Files to Create / Modify:**
- `migrations/prompt_templates_tier_id.sql` — new
- `services/test_generation/database_client.py`, `services/test_generation/orchestrator.py`, `services/test_generation/stem_rotation.py`, `services/prompt_service.py` (filter)
- `tests/test_tier_templates.py` — new

**Verification:**
`pytest tests/test_tier_templates.py tests/test_stem_rotation.py -q`; after the migration,
`select count(*) from prompt_templates where tier_id is not null` = 0 and a generation `--dry-run`
logs the same template versions as before.

---

## TASK-926: Author tier templates for T1–T3 (zh, en, ja)

**Status:** [x] Done — 27 rows applied 2026-11-10, verified live (same model as base, text = base + level block); native read-through owed
**Feature:** test-quality-checks
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-925

**Implementation note (2026-11-09):** templates are generated, not hand-copied: `scripts/build_tier_question_templates.py` writes `migrations/seed_tier_question_templates.sql`, where each row is `base.template_text || level block` selected from the live base row, so the JSON output section stays byte-identical. 27 rows: T1 literal_detail + vocabulary_context; T2 + main_idea; T3 + supporting_detail (the fixed tier mix), × zh/en/ja. Verified: all 27 render through `str.format` with the generator's placeholders, no Latin in ja/zh blocks beyond HSK/JLPT/JSON.

**Description:**
Write tier-specific question templates for the types the tier table uses at T1–T3
(`literal_detail`, `vocabulary_context`, `main_idea`, `supporting_detail` — 3 + 2 + 3 types per
tier as in `question_type_distributions_by_tier`) in each language, and T1–T3 stem pools for
`main_idea`. Each template starts from the current base row and changes the **language of the
question**, not what is asked.

**Acceptance Criteria:**
- [ ] Level rules written into each template (and summarised in the task's log entry):
  - **ja T1–T2:** stem, choices and answer use only kana plus kanji that appear in the passage; spaced phrasing if the passage is spaced; stem ≤ 25 characters (e.g. `「てつだい」は どういう いみ ですか。`); choices ≤ 15 characters; no 文中の／最も適切なもの register. **ja T3:** kanji at roughly JLPT N4, plain polite stems.
  - **zh T1–T2:** choices use only characters from the passage or HSK 1–2; stem ≤ 15 characters; no 下列/最恰当 register. **zh T3:** HSK ≤ 3 wording.
  - **en T1–T2:** stem ≤ 10 words, choices ≤ 6 words, A1–A2 vocabulary only, no "best expresses / primarily". **en T3:** B1.
  - All tiers: one correct answer stated in the passage (literal) or, for vocab, a meaning a learner at that level could recognise; distractors plausible but clearly wrong from the passage.
- [ ] Rows inserted with `tier_id` set, same `model`/`provider` as the base row, `is_active = true` (inert while `TEST_GEN_TIER_TEMPLATES` is off). Up to 3 tiers × 3 languages × the types each tier uses. Insert SQL in `migrations/seed_tier_question_templates.sql`; developer applies.
- [ ] ja and zh templates pass `scripts/audit_prompt_latin.py` with no content leaks.
- [ ] A `--dry-run` per language × tier with `--tier-templates on` loads the tier rows (logged template id/version).
- [ ] Native-speaker read-through is flagged as owed in the log entry (as with the stem pools); not a blocker for the experiment.

**Technical Notes:**
Pull the current base rows first (`select id, task_name, language_id, version, template_text, model, provider from prompt_templates where is_active and task_name like 'question_%' and tier_id is null`) and keep their output-format sections byte-identical — the parser depends on them.

**Files to Create / Modify:**
- `migrations/seed_tier_question_templates.sql` — new
- `services/test_generation/stem_rotation.py` — T1–T3 `main_idea` pools per language

**Verification:**
`select language_id, tier_id, count(*) from prompt_templates where tier_id is not null group by 1,2` matches the tier table's type counts.

---

## TASK-927: Experiment E2 — do tier templates make better T1–T3 tests? (LIVE writes, approval)

**Status:** [?] Blocked — needs an OpenRouter key and budget approval; templates are in
**Feature:** test-quality-checks
**Type:** test
**Complexity:** L (1-2d)
**Depends On:** TASK-923, TASK-926

**Description:**
Generate the same T1–T3 topics with base templates (**arm A**, `--tier-templates off`) and tier
templates (**arm B**, `on`), with check mode held at E1's winner if TASK-924 is done (else
`flag`), and decide per language × tier whether to switch the default on.

**Acceptance Criteria:**
- [ ] Topics file: 4 topics per tier T1–T3 per language, unused by active tests; same file both arms. 2 arms × 3 languages × 12 = **72 tests**, all `--inactive`. Developer approves run and budget.
- [ ] Arm-blind review of all 72 via TASK-923 packs; `level_fit` is the primary metric.
- [ ] Pre-registered rule: switch a language × tier to tier templates when its `level_fit = ok` rate is higher than arm A's with non-overlapping 95% intervals **and** its (major + minor) rate is not higher. Otherwise keep base templates for that cell.
- [ ] Also reported per arm: `script_above_level` hits (ja), survival-floor failures, $ per test.
- [ ] Default of `TEST_GEN_TIER_TEMPLATES` set per language (e.g. env `TEST_GEN_TIER_TEMPLATES=ja,en`) to the winning cells; losing tier rows set `is_active = false`.
- [ ] Clean-up as in TASK-924 (activate winning-arm tests with no major issues; delete the rest after checking `test_attempts` = 0).
- [ ] Results: `wiki/evaluations/tier-template-experiment-<date>.md`.

**Verification:**
The evaluation page shows the rule, per-cell table and decisions; a `--dry-run` with defaults loads tier rows exactly for the winning cells.

