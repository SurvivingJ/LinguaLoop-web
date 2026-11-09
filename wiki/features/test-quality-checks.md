---
title: Test Quality Checks
type: feature
status: in-progress
tech_page: test-quality-checks.tech.md
last_updated: 2026-11-09
open_questions:
  - "OPEN: which check mode generation ships with — settled by experiment E1 (TASK-924)"
  - "OPEN: whether tier-specific question templates beat the current ones at T1–T3 — settled by experiment E2 (TASK-927)"
---

# Test Quality Checks

## Purpose
A set of cheap, rule-based checks that run on every comprehension test, in every language
(Chinese, English, Japanese), when it is generated and over the existing library. They catch
the mechanical defects that make a test unfair or sloppy without needing another AI call.

## User Story
A learner taking a test should never see a question where the right answer is obvious because
it is the only long option, where two questions ask the same thing, where a Japanese choice is
written in a Chinese character, or where a beginner's all-hiragana test suddenly offers answers
in kanji. A content creator running a batch should find these problems in a report, not from
learner complaints.

## How It Works
1. **When a test is generated**, each question is checked as soon as it is written. A question
   that breaks a hard rule is thrown away and written again, the same way the existing
   validator works today. A question that breaks a soft rule is kept but put in the review
   queue with the reason.
2. **When the whole test is assembled**, the test is checked as a set: are two questions really
   the same question, is the mix of question types sensible, does it have a title.
3. **Over the existing library**, a read-only audit script runs the same checks on every active
   test and writes a report: which tests, which questions, which rule, per language.
4. The checks run at **every level, including the easiest one**. Today the AI judges are
   switched off for the easiest level, which is how an incoherent beginner test reached learners.

### What the checks look for
| Group | Examples it catches |
|---|---|
| Wrong writing system | Simplified-Chinese characters in Japanese (纹, 变); traditional characters or kana in Chinese; CJK in English; stray English words in a Chinese/Japanese question |
| Too hard for the level | Kanji in the choices of an all-hiragana beginner test |
| Answer gives itself away | Correct answer copied word-for-word from the passage while the wrong ones are not; correct answer far longer than the rest; wrong answers that all use "always / never / completely" |
| Formatting | Choices that start with "A." / "B." (the app adds its own labels) |
| Vocabulary target missing | A vocabulary question about a word the passage doesn't contain (now also for words marked with （…） brackets) |
| Duplicate questions | Two questions in one test with near-identical correct answers, or the same vocabulary word tested twice |
| Test shape | Two author's-purpose questions in one test; no literal-detail question; too few questions; no title |

## Constraints & Edge Cases
- These checks cannot tell whether an answer is *true*. Wrong answer keys, two defensible
  answers and incoherent passages need a model that reads the passage — that is the
  answer-entailment judge and the planned test-authoring skill, not this feature.
- Every check starts as **flag only**. A check only starts rejecting questions after it has been
  measured against human-reviewed questions and shown to be almost never wrong (TASK-920).
- Literal-detail and vocabulary questions are allowed to quote the passage; the copy check skips them.

## Business Rules
- A rejected question is regenerated; it never ships.
- When two questions duplicate each other, the second one is dropped; the test ships if it still meets the minimum question count.
- A flagged question ships and appears in `generation_review_queue`.
- The audit script never writes to the database. Fixes to existing content go through a
  reviewed SQL file the developer applies.

## Open Questions
- OPEN: which check mode ships — calibration (TASK-920) proposes one, an experiment comparing flag-only, calibrated and reject-everything on the same topics decides (TASK-924).
- ANSWERED (developer, 2026-11-09): when two questions in a test duplicate each other, drop the second one; never regenerate the whole test.
- OPEN: level-specific question templates (developer, 2026-11-09: write them) — beginner tests get questions written in beginner language; whether they help is settled by an experiment (TASK-925–927, [[decisions/ADR-040-tier-keyed-question-templates]]).

## Related Pages
- [[features/test-quality-checks.tech]]
- [[tasklist/test-quality-checks.tasks]]
- [[evaluations/ja-test-review-2026-11-09]] — the human review these checks are calibrated against
- [[features/comprehension-tests]]
- [[features/answer-entailment-judge]] — the model-based check that covers what these can't
