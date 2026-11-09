---
title: Japanese Test Review — 2026-11-09
type: evaluation
status: complete
last_updated: 2026-11-09
---

# Japanese Test Review — 2026-11-09

A question-by-question human-style review (four parallel Claude reviewers, one per ~15 tests)
of every active Japanese test: **59 tests, 257 questions**. All tests were generated 2026-08-23/24,
before `question_type_distributions_by_tier` (2026-08-29), stem rotation and the current judges.

Per-question verdicts and suggested fixes: `data/test_quality/ja_review_2026-11-09.csv`
(columns `slug, difficulty, question_id, type_id, verdict, question_text, answer, issues, suggested_fix`;
`question_id = TEST` rows are test-level notes). This is the gold set for
[[tasklist/test-quality-checks.tasks]] TASK-920.

## Results

| Verdict | Questions | Test-level notes |
|---|---|---|
| ok | 164 | — |
| minor | 79 | 23 |
| major | 14 | 1 |

### Majors — all fixed or removed 2026-11-09 (developer applied the SQL by hand)
- Deleted test `ja-d1-the-evolution-of-state-soverei-20260823224041` (incoherent transcript;
  its 2 major questions went with it). Delete needed `word_quiz_results` and
  `question_attempt_results` cleared first (NO ACTION FKs).
- 12 questions re-keyed or given a replacement distractor: wrong keys (往々にして, 摂理),
  two defensible answers (てつだい, 計り知れない, 楔を打ち込む, brutalism q5, parametric q2,
  crayons q1), unsupported keys (他の人, 出荷, gothic q4, carbon q1).
- Verified afterwards: 58 active ja tests, 0 answers not in choices.

**Note for calibration:** those 12 rows and the deleted test's rows in the CSV describe the
*pre-fix* content. Exclude them when scoring against the live library.

### Minor problems, grouped (79)
| Group | n | Deterministic check that targets it |
|---|---|---|
| Duplicate / overlapping questions in a test (mostly two `author_purpose`) | 28 | `duplicate_answer`, `type_mix` |
| Guessable: answer copied from passage, absurd/absolute distractors, length | 13 | `answer_copies_passage`, `absolute_distractors`, `answer_length_outlier` |
| Key only best-by-elimination / needs world knowledge / premise not in text | 13 | none — needs a model |
| A distractor partly defensible | 10 | none — needs a model |
| Vocabulary meaning slightly off in context | 5 | none — needs a model |
| Language errors in stem/choices (typos, simplified chars, English words, ungrammatical) | 7 | `foreign_script`, `latin_in_cjk` (typos and grammar: none) |
| Level mismatch (kanji choices on all-hiragana tests) | 2 | `script_above_level` |
| Belonged to the deleted test | 1 | — |

Roughly **45 of 79** minor problems are in reach of deterministic checks; the rest need the
answer-entailment judge or the planned authoring/review skill.

### Test-level notes (23)
Transcript typos/unnatural Japanese (入り方→入り口, かような→かのような, 纹理, 微型社会, 都市主義,
外傷が出ます, a self-contradiction in haute-couture), tests short of distinct questions, NULL title
(community-garden), title mismatch (great-wall), 3-question test (spoken-word), slug difficulty ≠
stored difficulty (probably expected: under ADR-029 jev assigns the stored tier after generation,
while the slug keeps the requested one — not verified, so not a check).

## Related
- [[features/test-quality-checks]] · [[features/test-quality-checks.tech]]
- [[features/answer-entailment-judge]]
