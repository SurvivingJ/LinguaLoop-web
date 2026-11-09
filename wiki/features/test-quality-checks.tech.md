---
title: Test Quality Checks — Technical Specification
type: feature-tech
status: in-progress
prose_page: test-quality-checks.md
last_updated: 2026-11-09
dependencies:
  - "services/test_generation/agents/question_validator.py (QuestionValidator)"
  - "services/test_generation/agents/question_generator.py (in-loop validate → regenerate, line ~411)"
  - "services/test_generation/orchestrator.py (validate_all_questions ~739, report_question_mix ~794, _write_review_queue_rows ~100)"
  - "table: generation_review_queue"
  - "table: question_type_distributions_by_tier"
  - "python: difflib (stdlib), codecs euc_jis_2004 (stdlib), opencc==1.3.1 (already in requirements.txt)"
breaking_change_risk: medium
---

# Test Quality Checks — Technical Specification

## Architecture Overview

A new pure module, `services/test_generation/quality_checks.py`, holds every deterministic
check. It has no DB or network access, so the same code runs in three places:

```
prose_writer ──▶ [passage checks] ──▶ question_generator ──▶ QuestionValidator
                                         (per question,        └─▶ [question checks]
                                          regen on reject)              reject → ValueError → regen
                                                                        flag   → q['_quality_flags']
orchestrator: validate_all_questions ──▶ [test checks] ──▶ insert ──▶ generation_review_queue
                                                                        (judge flags + qc flags)

scripts/audit_test_quality.py ── reads tests+questions ──▶ same checks ──▶ CSV + summary (read-only)
```

Deterministic checks run at **every tier including T1**. The LLM judges stay off at T1
(`run_judges = tier_id > 1`, orchestrator ~709); these checks do not depend on that flag.

### Why this is needed even though a validator exists
`QuestionValidator` today checks structure (4 choices, answer ∈ choices, no duplicate choices)
and quoted vocab spans. Three of its checks are no-ops or broken:

1. `_check_overlap` tokenises with `str.split()`. A Japanese or Chinese question has no spaces,
   so it is a single token and Jaccard is 0 unless the two strings are identical. **Within-test
   duplicate detection does not work for ja/zh at all.**
2. The answer-length and "all same length" checks only `logger.debug`.
3. `_QUOTE_PATTERNS` misses fullwidth `（…）` brackets, which is how many ja vocab stems mark
   the target (`文中の（他の人）の意味…`), so those targets are never checked against the passage.

## Database Impact
- **Reads:** `tests`, `questions`, `dim_languages`, `question_type_distributions_by_tier` (audit only).
- **Writes:** `generation_review_queue` only (existing table, existing writer). New
  `flag_reasons` values are prefixed `qc:` (e.g. `qc:answer_copies_passage`); `judge_scores`
  gains a `quality_checks` key holding the list of `CheckResult` dicts.
- No migration.

## API / Module Surface

### `CheckResult` (dataclass, frozen)
- `code: str` — stable snake_case id, e.g. `foreign_script`.
- `severity: Literal['reject','flag']` — resolved from `CHECK_MODES`, not hard-coded in the check.
- `scope: Literal['passage','question','test']`
- `question_index: Optional[int]` — index in the test's question list; `None` for passage/test scope.
- `field: Optional[str]` — `'question' | 'choices[2]' | 'answer' | 'transcript' | 'title'`.
- `message: str` — English, human-readable, includes the offending substring.

### `LanguageProfile` (dataclass) and `get_profile(language_code: str) -> LanguageProfile`
| field | ja | zh | en |
|---|---|---|---|
| `is_cjk` | True | True | False |
| `tokenize(s)` | char bigrams of `s` with whitespace/punctuation removed | same | lowercase `\w+` words |
| `copy_min_len` | 15 chars | 15 chars | 6 words |
| `absolutes` | すべて, 全て, 完全に, 決して, 常に, 全く, 一切, 必ず, 絶対 | 所有, 完全, 绝对, 从不, 总是, 一切, 全部, 永远 | all, always, never, completely, entirely, only, every, none |

`get_profile` raises `KeyError` for an unknown code. Adding a language = adding a profile + a
script rule in `check_foreign_script`.

### `CHECK_MODES: dict[str, Literal['off','flag','reject']]`
Module-level. Calibrated 2026-11-09 ([[evaluations/test-quality-checks-calibration-2026-11-09]]):
`reject` — `absolute_distractors`, `answer_copies_passage`, `duplicate_answer`, `latin_in_cjk`,
`script_above_level`; everything else `flag`. TASK-924 tests this against all-flag and all-reject. Pre-existing validator behaviour (structure, duplicate choices, quoted span) stays
rejecting and is not routed through `CHECK_MODES`.

### `run_passage_checks(transcript: str, title: str | None, profile) -> list[CheckResult]`
### `run_question_checks(q: dict, passage: str, profile, tier: int, index: int) -> list[CheckResult]`
`q` uses generator shape: `question`, `choices` (list[str]), `answer`, `type_code`.
### `run_test_checks(questions: list[dict], passage: str, profile, tier: int) -> list[CheckResult]`
Each returns `[]` when clean. None raise on bad content; they raise only on programmer error.

## The checks

| code | scope | rule | languages |
|---|---|---|---|
| `foreign_script` | passage, question | **ja:** any CJK char not encodable in `euc_jis_2004` (catches simplified 纹 变 们). **zh:** any kana `[぀-ヿ]`; any char changed by OpenCC `t2s` that is not in an allowlist of t2s-ambiguous chars (start with 乾 著 於 隻 — extend during calibration). **en:** any char in CJK/kana blocks. | all |
| `latin_in_cjk` | question | ja/zh: a run `[A-Za-z]{2,}` in stem or a choice that does not occur in the passage (catches "dramatize", "sandwich"). | ja, zh |
| `script_above_level` | question | ja only: if the passage has zero kanji (`[一-鿿]`), any kanji in a choice or the answer. Stem templates are excluded (they are fixed per language and tracked separately). | ja |
| `choice_label_prefix` | question | a choice matches `^\s*(\(?[A-DＡ-Ｄa-d]\)?|[1-4１-４]|[①-④])\s*[.．)）:：、]\s*`. `fix_question` strips the prefix from every choice **and** the answer when all four carry one; the check then only fires if a prefix survives. | all |
| `answer_length_outlier` | question | answer length ≥ 1.4 × the longest distractor **and** ≥ 4 characters longer. Length = characters (punctuation/space stripped) in every language. *(Calibrated; the original mean-based rule was mostly false alarms.)* | all |
| `absolute_distractors` | question | ≥ 2 distractors contain a token from `profile.absolutes` and the answer contains none. | all |
| `answer_copies_passage` | question | tier ≥ 3 and `type_code ∈ {main_idea, inference, author_purpose, supporting_detail}`: `difflib.SequenceMatcher(None, passage, answer).find_longest_match()` (over words for en) has length ≥ `copy_min_len` (15 chars CJK, 6 words en) **and** ≥ 2 × the longest such match of any distractor. | all |
| `vocab_target_missing` | question | extend `_QUOTE_PATTERNS` with `（([^）]+?)）` and `\(([^)]+?)\)` **only for `vocabulary_context`**; for CJK use a span-length limit of ≤ 12 chars instead of `≤ 6 words`. Lives in the existing `check_quoted_phrase_in_passage` (stays rejecting). | all |
| `duplicate_answer` | test | answer–answer similarity = Jaccard of `profile.tokenize`. ≥ 0.6 → fires. Pairs of the same `type_code` use 0.45. | all |
| `duplicate_vocab_target` | test | two `vocabulary_context` questions whose target (the **shortest** quoted/bracketed span) is equal. | all |
| `duplicate_stem` | test | replace `_check_overlap`'s `str.split()` with `profile.tokenize`; compare stems only for `literal_detail` / `supporting_detail` (other types use rotated templates — see `stem_rotation.py` — and would always collide). Threshold unchanged (0.65). | all |
| `type_mix` | test | more than one `author_purpose` or `main_idea`; or `len(questions) ≥ 4`, tier ≤ 4 and no `literal_detail`/`supporting_detail`. | all |
| `too_few_questions` | test | `len(questions) < 4` and `tier ≥ 3`. | all |
| `missing_title` | passage | `title` is None or blank (orchestrator continues with NULL title on title-gen failure, ~691). | all |

Out of scope (need a model): wrong answer key, two defensible answers, ungrammatical or
incoherent text, vocab meaning that doesn't fit context. Those stay with the answer-entailment
judge and the planned authoring/review skill.

## Wiring into generation (TASK-921)
- `QuestionValidator.validate_question(question, prose, previous_questions=None, *, language_code=None, tier=None, previous=None)`.
  New keyword args are optional so existing call sites keep working. When `language_code` is
  given, it calls `run_question_checks`; any result with severity `reject` → `raise ValueError(result.message)`
  (the generator's existing regen loop handles it); `flag` results are appended to
  `question['_quality_flags']`. `previous` (list of already-accepted question dicts) feeds the
  per-pair `duplicate_*` checks so a duplicate is caught while it can still be regenerated.
- Mode switch: env `TEST_QC_MODES` = `flag` | `reject` | `calibrated` (default), so experiment arms differ by one variable.
- `question_generator.py` passes `language_code`, `tier`, `previous` at its validator call (~411).
- Orchestrator: after `validate_all_questions`, call `run_test_checks`; for a `reject`
  `duplicate_*`, drop the second question of the pair (developer decision 2026-11-09) and re-apply the survival floor. Call
  `run_passage_checks` right after prose generation; a `reject` `foreign_script` on the passage
  raises `ValueError` so the test is skipped (the batch runner already counts and continues).
- `_write_review_queue_rows` includes questions with `_quality_flags` as well as `_judge_flags`;
  `flag_reasons` gets `qc:<code>` entries.

## Key Architectural Decisions
1. **Decision:** deterministic, model-free checks in one pure module shared by generation and audit.
   - **Rationale:** the audit and the generator can't drift; checks are unit-testable without mocks.
   - **Alternatives rejected:** an LLM "quality judge" (cost, and it would duplicate jev); SQL-only audit (can't tokenise CJK or run difflib).
2. **Decision:** every new check starts in `flag` mode; promotion to `reject` needs ≥ 0.9 precision in calibration.
   - **Rationale:** a false reject costs a regeneration (or a whole test at T1's survival floor); a false flag costs a review-queue row.
   - **Alternatives rejected:** reject-by-default (would have made T1 survival worse — see the T1 Jaccard note at orchestrator ~747).
3. **Decision:** run at all tiers including T1.
   - **Rationale:** T1 runs no LLM judges, so today it has the least protection; the 2026-11-09 review's only incoherent test was a beginner test.
4. **Decision:** the shipped check mode is chosen by experiment (TASK-924: flag vs calibrated vs reject on identical topics, arm-blind review), not by the calibration rule alone.
   - **Rationale:** precision on old content doesn't show the cost of rejecting during generation (regenerations, survival-floor losses at T1).
5. **Decision:** level-specific question templates, keyed by tier ([[decisions/ADR-040-tier-keyed-question-templates]]), authored for T1–T3 and adopted per language × tier only where experiment E2 (TASK-927) shows they help.
6. **Decision:** CJK similarity via character bigrams rather than fugashi/jieba.
   - **Rationale:** no tokenizer dependency inside the hot path; bigram Jaccard is a standard proxy and is enough for near-duplicate detection. Revisit only if calibration shows it is not.

## Security Considerations
None new: no user input, no writes beyond the existing review-queue writer. The audit script
uses the service-role client read-only and must not contain any `insert/update/delete`.

## Testing Strategy
- `tests/test_quality_checks.py`: one positive and one negative fixture per check per language,
  using real strings from the 2026-11-09 review (纹理, 质的变化, "A. " prefixes, the great-wall
  q1/q2 duplicate, the peanut-butter q3/q4 author_purpose pair, the all-hiragana robot test).
- `tests/test_question_validator.py` (extend or create): `_check_overlap` now detects a ja
  near-duplicate; `（…）` vocab target missing from passage is rejected; legacy call signature
  still works.
- Calibration (TASK-920) is the integration test: the audit over the live library, scored against
  [[evaluations/ja-test-review-2026-11-09]].

## Related
- [[features/test-quality-checks]] · [[tasklist/test-quality-checks.tasks]]
- [[features/comprehension-tests.tech]] · [[features/answer-entailment-judge.tech]]
- [[database/schema.tech]] (`generation_review_queue`)
