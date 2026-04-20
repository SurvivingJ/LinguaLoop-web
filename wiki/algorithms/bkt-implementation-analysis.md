---
title: BKT System — Implementation Analysis & Improvements
type: algorithm
status: in-progress
tech_page: ./bkt-implementation-analysis.tech.md
last_updated: 2026-04-16
open_questions:
  - "Should exercise-type-specific slip/guess parameters be calibrated from data or set heuristically?"
  - "Should BKT and FSRS be unified into a single knowledge model long-term (Option 4)?"
---

# BKT System — Implementation Analysis & Improvements

## Purpose

This page analyses the Bayesian Knowledge Tracing implementation as it exists in the codebase, identifies what works well, what's missing, and proposes improvements that would increase the accuracy of the knowledge model and the quality of exercise targeting.

## Current State Summary

BKT in LinguaLoop is a 3-parameter model (slip, guess, and transit) implemented entirely in plpgsql. It tracks a single probability (`p_known`) per user-sense pair, updated by three evidence sources:

1. **Comprehension tests** — weaker signal (slip=0.10, guess=0.25, transit=0.02)
2. **Word quizzes** — stronger signal (slip=0.05, guess=0.25, transit=0.05)
3. **Exercises** — variable signal across 4 cognitive tiers (Phase 5), transit=0.05–0.10

The Python layer (`VocabularyKnowledgeService`) is a thin RPC wrapper. All Bayesian math lives in SQL. Session building uses a single `get_session_senses()` RPC that returns decay-applied effective p_known — no BKT logic in Python.

## What Works Well

### 1. Per-Sense Granularity (ADR-002)

Tracking knowledge at the word-sense level rather than lemma level is the right call. "Run a program" and "run a marathon" are genuinely different knowledge items. The `dim_word_senses` table with LLM-based sense disambiguation makes this feasible.

### 2. Frequency-Based Priors

New words don't start at a flat prior. Instead, the system uses `dim_vocabulary.frequency_rank` to set initial p_known:

| Frequency Rank | Initial p_known | Rationale |
|---------------|----------------|-----------|
| ≥ 6.0 (very common) | 0.85 | Most learners already know "the", "is" |
| ≥ 5.0 | 0.65 | Common words likely known passively |
| ≥ 4.0 | 0.35 | Moderately common — uncertain |
| ≥ 3.0 | 0.15 | Less common — likely unknown |
| < 3.0 or NULL | 0.05–0.10 | Rare — assume unknown |

This avoids wasting exercises on high-frequency words the learner already knows, while being conservative enough to test if the assumption is wrong.

### 3. User Override Preservation

The `user_marked_unknown` status is never overwritten by BKT updates. If a learner explicitly flags a word as unknown, the system respects that signal even if BKT would classify them as "known". This is good UX — it gives the learner agency over their study material.

### 4. Deduplication Logic

`update_vocabulary_from_test()` uses `bool_or` to handle the case where a word sense appears in multiple questions: if *any* question testing that sense was answered correctly, the sense gets a positive update. This prevents double-counting (both positive and negative).

### 5. Auto-Flashcard Creation

When a word moves into the "encountered" or "learning" zone, the system automatically creates an FSRS flashcard for it. The flashcard difficulty is initialized from p_known. This bridges BKT (knowledge state) and FSRS (review scheduling) without manual intervention.

## What's Been Fixed (Phase 5 + Phase 7)

### ✅ Exercise-Type-Specific Parameters (Phase 5)

Four cognitive tiers with different slip/guess profiles: Recognition (A), Recall (B), Nuanced (C), Production (D). See [[algorithms/bkt-implementation-analysis.tech]] for parameter table.

### ✅ Transit Parameter P(T) (Phase 7)

Each evidence source now applies a learning credit after the Bayesian update: comprehension=0.02, recognition=0.05, recall/nuanced=0.08, production=0.10. This makes BKT less pessimistic — even a wrong answer gives a small chance of learning from seeing the correction.

### ✅ FSRS Stability-Informed Decay (Phase 7)

Replaced the flat 60-day half-life with a two-path decay model:
- **Path A**: If FSRS stability is available, use `retrievability = exp(-days / stability)` — research-backed, accounts for spacing and lapse history
- **Path B**: Fallback to evidence-count-scaled half-life `30 * (1 + 0.5 * ln(1 + evidence_count))` — more reviews = slower decay

Applied at read-time via `bkt_effective_p_known()`. The `get_session_senses()` RPC applies this automatically so Python never does BKT math.

### ✅ FSRS Lapse → BKT Penalty (Phase 7)

When FSRS records a lapse (rating=AGAIN), BKT applies a 20% penalty: `p_known *= 0.80`. This bridges the FSRS→BKT gap — fragile words (low FSRS stability) now also have lower p_known.

### ✅ Frequency-Tier Inference (Phase 7)

When a rare word reaches "known" status (p_known ≥ 0.90), common words with little evidence (evidence_count < 3) are boosted to their frequency-based prior floor. If you know "crepuscular", you know "sunset".

### ✅ Sentence-Level Contextual Inference (Phase 7)

Comprehension test results now provide a dampened BKT update to words in the transcript that weren't directly tested by any question. Dampening factor scales with test score (0.30 × score_ratio). Only fires when score ≥ 50%.

### ✅ Per-Question Sense Assignment (Phase 7)

Previously ALL transcript senses were assigned to EVERY question. Now each question's `sense_ids` only contain vocabulary that appears in the question text + answer choices, via `_match_question_senses()`.

## Remaining Gaps

### 1. No Cross-Sense Interference Modeling

Related senses (e.g., synonyms, near-synonyms) are tracked independently. Learning "happy" doesn't affect p_known for "glad". For closely related word senses, there's an opportunity to propagate partial evidence.

### 2. First-Attempt Gating Inconsistency

`ExerciseSessionService.record_attempt_with_updates()` still calls BKT on every attempt (not just first attempts). The ladder service correctly gates on `is_first_attempt`. Non-ladder exercises can inflate p_known on retries.

### 3. Data-Driven Parameter Calibration

All slip/guess/transit values are hand-tuned. With sufficient exercise_attempts data (~50k rows), parameters could be fitted from observed data using EM.

## Implementation History

| Improvement | Phase | Status | Impact |
|-------------|-------|--------|--------|
| Exercise-type params (4 tiers) | Phase 5 | ✅ Done | High — cognitive-tier-aware signal |
| Temporal decay (flat 60-day) | Phase 5 | ✅ Superseded by Phase 7 | — |
| Canonical phase thresholds | Phase 5 | ✅ Done | Medium — single source of truth |
| Transit parameter P(T) | Phase 7 | ✅ Done | Medium — realistic learning model |
| FSRS stability-informed decay | Phase 7 | ✅ Done | High — principled forgetting |
| FSRS lapse → BKT penalty | Phase 7 | ✅ Done | Medium — bridges FSRS/BKT gap |
| Frequency-tier inference | Phase 7 | ✅ Done | Medium — reduces exercise pool |
| Per-question sense_ids fix | Phase 7 | ✅ Done | High — foundational accuracy |
| Sentence-level contextual inference | Phase 7 | ✅ Done | High — implicit knowledge |
| `get_session_senses()` RPC | Phase 7 | ✅ Done | High — all BKT math in SQL |
| First-attempt gating fix | — | ❌ TODO | Medium — prevents BKT inflation |
| Cross-sense propagation | — | ❌ TODO | Medium — deferred |
| Data-driven calibration | — | ❌ TODO (needs ~50k rows) | Very high |

## Related Pages

- [[algorithms/bkt-implementation-analysis.tech]] — Technical details with code references
- [[features/vocabulary-knowledge]] — Original BKT feature description
- [[features/vocabulary-knowledge.tech]] — Original BKT technical specification
- [[features/vocab-dojo]] — Exercise serving that consumes BKT state
- [[features/flashcards]] — FSRS scheduling integration
- [[decisions/ADR-002-bkt-per-sense]] — Per-sense BKT decision record
