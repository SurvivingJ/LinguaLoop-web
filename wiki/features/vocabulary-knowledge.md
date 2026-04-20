---
title: Vocabulary Knowledge Tracking
type: feature
status: in-progress
tech_page: ./vocabulary-knowledge.tech.md
last_updated: 2026-04-16
open_questions: []
---

# Vocabulary Knowledge Tracking

## Purpose

LinguaLoop tracks what each learner knows at the individual word-sense level using Bayesian Knowledge Tracing (BKT). This powers vocabulary-aware test recommendations, exercise targeting, and flashcard scheduling.

## User Story

As a learner takes tests and completes exercises, the system silently builds a model of which words they know and which they don't. A word the learner consistently gets right is marked "known" and stops appearing in drills. A word they struggle with stays in the "learning" zone and is prioritized for review.

## How It Works

1. Every test transcript is analyzed for vocabulary. Each word sense appearing in the test is linked via `vocab_sense_ids`. Each question links to its own specific vocabulary (not all transcript words).
2. When a learner submits a test, the system checks which word senses appeared and whether the learner demonstrated comprehension.
3. The BKT formula updates `p_known` — the probability the learner knows each word:
   - **Comprehension evidence** (from tests): slip=0.10, guess=0.25, transit=0.02
   - **Direct word-test evidence** (from word quizzes): slip=0.05, guess=0.25, transit=0.05
   - **Exercise evidence** (from Vocab Dojo): variable by cognitive tier, transit=0.05–0.10
4. After updating directly-tested words, the system applies **contextual inference** — words in the test transcript that weren't directly tested get a dampened positive boost (if the learner scored ≥ 50%).
5. When a rare word reaches "known" status, **frequency inference** automatically boosts common words that haven't been directly tested yet.
6. Based on `p_known`, each word gets a status label:
   - `< 0.20` → **unknown**
   - `0.20 – 0.50` → **encountered**
   - `0.50 – 0.75` → **learning**
   - `0.75 – 0.90` → **probably_known**
   - `≥ 0.90` → **known**
7. Knowledge **decays over time** using FSRS stability as the decay rate (more stable memories decay slower). Words not reviewed for a long time gradually return toward "unknown".
8. The system uses this to recommend tests where ~3-7% of words are unknown (the "i+1" sweet spot).

## Constraints & Edge Cases

- `p_known` is clamped to [0.02, 0.98] to prevent certainty lock-in.
- Users can manually mark a word as "unknown" (overrides BKT status).
- Evidence from comprehension tests is weaker (higher slip) than from direct word quizzes.
- A word with zero evidence starts at a frequency-based prior (0.05 for rare words, up to 0.85 for very common words).
- Decay is applied at read-time (lazy evaluation) — stored `p_known` is the last-evidence value, not the effective value.
- Contextual inference is positive-only — it never lowers p_known.
- Frequency inference only boosts words with < 3 evidence events to avoid overriding direct evidence.

## Business Rules

- BKT updates happen atomically inside `process_test_submission()`.
- All BKT math lives in PostgreSQL — Python is a thin RPC wrapper.
- The `get_session_senses()` RPC computes decay-applied effective p_known for session building.
- The `get_vocab_recommendations()` RPC uses array intersection (`intarray &`) to find tests with the right unknown-word percentage.
- Word quiz candidates are selected from the "learning zone" (`p_known` between 0.25 and 0.75).
- When FSRS records a lapse (user forgot a word), BKT applies a 20% p_known penalty.

## Related Pages

- [[features/vocabulary-knowledge.tech]] — Technical details
- [[features/comprehension-tests]] — Source of comprehension evidence
- [[features/exercises]] — Source of exercise evidence
- [[features/flashcards]] — FSRS scheduling uses knowledge state
- [[algorithms/elo-ranking]] — ELO and BKT work together for adaptive matching
