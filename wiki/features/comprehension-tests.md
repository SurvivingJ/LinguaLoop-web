---
title: Comprehension Tests
type: feature
status: in-progress
tech_page: ./comprehension-tests.tech.md
last_updated: 2026-04-10
open_questions:
  - "Content generation pipeline still needs work on quality and consistency"
---

# Comprehension Tests

## Purpose

Comprehension tests are LinguaLoop's core assessment tool. They measure a learner's reading or listening ability in the target language and drive the ELO rating that governs all adaptive content matching.

## User Story

A learner opens the test list page, sees tests recommended for their current level, and picks one. For a **reading test**, they read a passage and answer 5 multiple-choice questions. For a **listening test**, they listen to an audio clip and answer the same 5 questions — the transcript is revealed only after submission. On submit, the system grades their answers, updates both the user's and the test's ELO ratings, and shows results with explanations.

## How It Works

1. User navigates to `/tests` and sees ELO-matched test recommendations.
2. User clicks a test -> preview page shows title, difficulty, type (reading/listening).
3. User starts the test -> passage or audio is presented with 5 MC questions (4 options each).
4. User selects answers and submits.
5. Server grades answers atomically via `process_test_submission` RPC:
   - Scores correct/incorrect per question
   - Calculates new ELO for both user and test
   - Records the attempt with before/after ELO snapshots
   - Updates vocabulary knowledge (BKT) for word senses appearing in the test
   - Deducts tokens if applicable
6. Results page shows score, ELO change, correct answers with explanations.
7. Unknown words from the test are surfaced for flashcard review.

## Test Recommendation Algorithm

The recommendation system uses a **multi-stage filtering pipeline**:

1. **ELO filter** — Tests within +/-200 of the user's ELO rating (indexed query, <10ms)
2. **Vocabulary coverage filter** — Once sufficient user vocabulary data exists, recommend tests where the user knows **>90-95% of the words**. This targets the "i+1" comprehension zone based on Nation's research: learners need 95-98% known words for unassisted comprehension.
3. **Exclusion filter** — Previously attempted tests are excluded
4. **Tier/access filter** — Premium tests only shown to premium users

The vocabulary matching uses **set-based operations** (not vector embeddings): each test stores its unique lemma array, and the system computes `unknown_words = test_lemmas - user_known_lemmas` for each candidate. With proper indexes, this resolves in ~25-30ms for 10,000 tests even with 10,000-word user vocabularies.

## Test Types

- **Reading** — text transcript displayed; user reads and answers
- **Listening** — audio played; transcript hidden until after submission
- **Dictation** — (type exists in schema; implementation status TBD)

## Constraints & Edge Cases

- Tests have a difficulty rating 1-9 and an independent ELO rating (starting at 1400).
- Users start at ELO 1200; ratings clamped to [400, 3000].
- Free-tier users get a limited number of daily free tests; beyond that, tokens are consumed.
- Idempotency key prevents double-submission.
- First attempt is flagged separately from repeat attempts.
- Tests can be tiered: free-tier, premium-tier, enterprise-tier.
- Pack-associated tests (study_pack_id set) follow inverted density logic: final tests use natural word frequency.

## Business Rules

- Each test has exactly 5 questions with 4 answer options.
- A test must be active (`is_active = true`) to appear in recommendations.
- Premium tests are only shown to premium users.
- Previously attempted tests are excluded from recommendations.
- Token cost is determined by the user's subscription tier.
- Pack comprehension tests update both global ELO and per-word BKT.

## Related Pages

- [[features/comprehension-tests.tech]] — Technical specification
- [[algorithms/elo-ranking]] — ELO calculation
- [[features/vocabulary-knowledge]] — BKT updates from test results
- [[features/language-packs]] — Pack-associated comprehension tests
- [[database/schema.tech]] — `tests`, `questions`, `test_attempts`, `test_skill_ratings` tables
