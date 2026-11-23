---
title: Vocabulary Knowledge Tracking — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./vocabulary-knowledge.md
last_updated: 2026-11-23
dependencies:
  - "user_vocabulary_knowledge table"
  - "user_flashcards table (FSRS stability for decay)"
  - "dim_vocabulary table"
  - "dim_word_senses table"
  - "bkt_update() / bkt_status() functions"
  - "bkt_apply_decay() / bkt_effective_p_known() (Phase 7)"
  - "get_session_senses() RPC (Phase 7)"
  - "bkt_apply_lapse_penalty() / bkt_infer_from_frequency() / bkt_contextual_inference() (Phase 7)"
  - "services/vocabulary/"
  - "services/practice_session_service.py and services/practice/ (the former services/exercise_session_service.py no longer exists)"
  - "services/test_generation/orchestrator.py"
breaking_change_risk: low
open_questions:
  - "Do the four SQL callers of bkt_effective_p_known (compute_weekly_plan_load_signals, get_practice_session, get_review_ahead_items, get_session_senses) all pass four arguments? A two-argument call is ambiguous live (verified 2026-11-23), so they must, but each body was not read."
  - "Pending migrations (not applied as of 2026-11-23): drop_get_quiz_distractors_batch.sql, drop_update_vocabulary_from_word_test_4arg.sql, word_quiz_retake_fallback_hardened.sql. Re-check live before relying on the 'pending' wording below."
---

> **Update 2026-11-23:** the batch quiz-distractor path was removed from the code, `update_vocabulary_from_word_test` and the two decay functions each have two live overloads, and the word-quiz retake band returns no candidates. See [Live function overloads and pending database changes (2026-11-23)](#live-function-overloads-and-pending-database-changes-2026-11-23).

# Vocabulary Knowledge Tracking — Technical Specification

## Architecture Overview

```
Evidence Sources:
  Comprehension Test → process_test_submission()
    → bkt_update_comprehension() [slip=0.10, guess=0.25, transit=0.02]
    → apply_contextual_inference() [dampened update for untested words]
    → _trigger_frequency_inference() [if word reaches "known"]
  Word Quiz → word_quiz_results → bkt_update_word_test() [slip=0.05, guess=0.25, transit=0.05]
  Exercise  → exercise_attempts → bkt_update_exercise() [4 cognitive tiers, transit=0.05-0.10]
  FSRS Lapse → bkt_apply_lapse_penalty() [20% p_known reduction]

Decay (read-time):
  bkt_effective_p_known(p_known, last_evidence_at, stability, evidence_count)
    Path A: FSRS stability → retrievability = exp(-days / stability)
    Path B: evidence-count-scaled half-life (fallback when no flashcard)

Storage:
  user_vocabulary_knowledge: one row per (user_id, sense_id)
    p_known, status, evidence_count, comprehension_correct/wrong, word_test_correct/wrong

Consumption:
  get_session_senses()        → unified RPC returning decay-applied senses with bucket labels
  get_vocab_recommendations() → tests with target unknown %
  get_word_quiz_candidates()  → words in learning zone for quiz serving
```

## Database Impact

**Primary table:** `user_vocabulary_knowledge`
- PK: auto-increment `id`
- Unique: `(user_id, sense_id)`
- Key columns: `p_known` (real, 0-1), `status` (enum), evidence counters

**Indexes:** `idx_uvk_user_language`, `idx_uvk_user_status`, `idx_uvk_user_pknown`

## BKT Formula

Implemented in `bkt_update()` plpgsql function:

```
Given: p_current (prior probability of knowing)
If correct:
  p_obs_knows = 1 - slip
  p_obs_not_knows = guess
If incorrect:
  p_obs_knows = slip
  p_obs_not_knows = 1 - guess

posterior = clamp(0.02, 0.98,
  (p_obs_knows * p_current) / (p_obs_knows * p_current + p_obs_not_knows * (1 - p_current))
)

// Phase 7: Transit credit applied after posterior
p_with_transit = posterior + (1 - posterior) * P_TRANSIT
```

**Parameters by evidence type:**

| Evidence Type | Slip | Guess | Transit | Rationale |
|--------------|------|-------|---------|-----------|
| Comprehension test | 0.10 | 0.25 | 0.02 | Higher slip — knowing a word doesn't guarantee getting an MC question right |
| Word quiz (direct) | 0.05 | 0.25 | 0.05 | Lower slip — direct word knowledge test is more reliable |
| Exercise: Recognition (A) | 0.05 | 0.25 | 0.05 | Easy to guess (4-choice MCQ), hard to slip |
| Exercise: Recall (B) | 0.10 | 0.10 | 0.08 | Moderate both ways |
| Exercise: Nuanced (C) | 0.15 | 0.20 | 0.08 | Subtle distinctions, some guessing from context |
| Exercise: Production (D) | 0.20 | 0.05 | 0.10 | Hard to guess, easy to slip — highest learning credit |

## Status Mapping

`bkt_status()` function:

| p_known Range | Status |
|--------------|--------|
| < 0.20 | `unknown` |
| 0.20 – 0.50 | `encountered` |
| 0.50 – 0.75 | `learning` |
| 0.75 – 0.90 | `probably_known` |
| ≥ 0.90 | `known` |

## Vocabulary Extraction Pipeline

`services/vocabulary/`:
- `pipeline.py` — orchestrates extraction from test transcripts
- `frequency_service.py` — word frequency lookups
- `knowledge_service.py` — BKT state management
- `language_detection.py` — identifies text language
- `phrase_detector.py` — multi-word expression detection
- `sense_generator.py` — LLM-based word sense disambiguation
- Processor per language: `english.py`, `japanese.py`, `chinese.py`

## Decay Model (Phase 7)

```
bkt_effective_p_known(p_known, last_evidence_at, stability, evidence_count):
  days_since = now() - last_evidence_at
  if days_since <= 1: return p_known

  // Path A: FSRS stability available
  if stability > 0:
    retrievability = exp(-days_since / stability)
  // Path B: evidence-count-scaled half-life fallback
  else:
    half_life = 30 * (1 + 0.5 * ln(1 + evidence_count))
    retrievability = 0.5^(days_since / half_life)

  effective_p = 0.10 + (p_known - 0.10) * retrievability
```

Applied at read-time via `get_session_senses()` RPC. Stored `p_known` is never modified by decay.

## Implicit Knowledge Inference (Phase 7)

Two inference mechanisms reduce the number of words requiring direct testing:

1. **Frequency-tier inference** (`bkt_infer_from_frequency`): When a rare word (low frequency_rank) reaches "known" status (p_known ≥ 0.90), common words with `evidence_count < 3` are boosted to their frequency-based prior floor.

2. **Sentence-level contextual inference** (`bkt_contextual_inference`): After a comprehension test, words in the transcript that weren't directly tested get a dampened positive BKT update. Dampening = 0.30 × score_ratio. Only fires when score ≥ 50%.

Both are triggered from `VocabularyKnowledgeService` in Python after RPC calls.

## Key Architectural Decisions

1. **Per-sense tracking, not per-lemma**
   - Rationale: A word like "run" has many senses. Knowing "run a program" doesn't mean knowing "run a marathon". Sense-level tracking is more accurate.

2. **All BKT math in plpgsql, not application code**
   - Rationale: BKT updates happen inside DB transactions. Session building uses `get_session_senses()` RPC that applies decay in SQL. Python never computes BKT probabilities.

3. **Clamping to [0.02, 0.98]**
   - Rationale: Prevents certainty lock-in. Even a "known" word can be forgotten; even an "unknown" word might be guessed correctly.

4. **FSRS stability as decay rate (Phase 7)**
   - Rationale: FSRS already computes per-word stability (memory strength). Using it as the BKT decay parameter is research-backed and bridges the two systems.
   - Alternatives rejected: Flat half-life (ignores word difficulty), unified FSRS model (too much scope creep).

5. **Per-question sense_ids (Phase 7)**
   - Rationale: Each question should only link to vocabulary appearing in its text + choices. This enables accurate contextual inference (distinguishing directly-tested vs. contextually-present words).

## Live function overloads and pending database changes (2026-11-23)

Checked live with `pg_get_function_arguments` and `pg_proc` on 2026-11-23 (read-only).

**Overloads (two live bodies each):**

| Function | Overload | Role |
|----------|----------|------|
| `bkt_apply_decay` | `(p_known numeric, p_last_evidence_at timestamptz, p_half_life_days numeric DEFAULT 60.0)` | Legacy fixed half-life decay (plpgsql, IMMUTABLE): `0.10 + (p_known - 0.10) * 0.5^(days / half_life)`, none within 1 day |
| `bkt_apply_decay` | `(p_known numeric, p_last_evidence_at timestamptz, p_stability real DEFAULT NULL, p_evidence_count integer DEFAULT 0)` | Phase 7 path described under Decay Model (FSRS stability, else evidence-scaled half-life) |
| `bkt_effective_p_known` | `(p_known numeric, p_last_evidence_at timestamptz)` | Legacy wrapper (SQL, IMMUTABLE): `bkt_apply_decay(p_known, p_last_evidence_at, 60.0)` |
| `bkt_effective_p_known` | `(p_known, p_last_evidence_at, p_stability real DEFAULT NULL, p_evidence_count integer DEFAULT 0)` | Phase 7 wrapper used by the session RPCs |

A two-argument `bkt_effective_p_known(numeric, timestamptz)` call fails live as "not unique" (SQLSTATE 42725), because the four-argument overload also matches through its defaults; a four-argument call works. The Decay Model section above describes the four-argument overloads only.

`update_vocabulary_from_word_test` also has two live overloads: `(p_user_id uuid, p_sense_id integer, p_is_correct boolean, p_language_id smallint)` and the same plus `p_exercise_type text DEFAULT NULL`. A call with four arguments matches both and fails as ambiguous. `services/vocabulary/knowledge_service.py` (`update_from_word_test`) sends four named arguments when `exercise_type is None`, and swallows the error, so the knowledge update for an exercise without a type is lost. `migrations/drop_update_vocabulary_from_word_test_4arg.sql` drops the four-argument overload (the five-argument body does the same with `p_exercise_type = NULL`); **it is not applied**. Its only SQL caller, `record_exercise_attempt`, already passes five arguments.

**Quiz distractors.** The batch path (`QUIZ_DISTRACTORS_BATCH` flag, RPC `get_quiz_distractors_batch`) was **removed from the code** on 2026-11-23. Measured live it took 6.5-13.8 s for five words, against about 0.4 s wall time for the per-word `get_quiz_distractors` calls run in parallel. The RPC itself still exists live (checked 2026-11-23); `migrations/drop_get_quiz_distractors_batch.sql` is **pending**. The single `get_quiz_distractors(p_sense_id, p_language_id, p_count, p_definition_language_id)` now samples sense ids first (no definition text or per-row `pos_class` call before the top-N pick); this was applied live on 2026-11-23 (`migrations/get_quiz_distractors_sample_ids_first.sql`; the live body carries its "worked out once" comment) with the same output columns and ordering.

**Retake band.** `get_word_quiz_candidates(p_user_id, p_sense_ids, p_language_id, p_max_words DEFAULT 5)` returns only tracked words with `p_known` in 0.25-0.75. There is no fallback tier outside that band, so on a retake it returns zero candidates and the quiz is not shown. `migrations/word_quiz_retake_fallback_hardened.sql` (adds a second tier from the test's other tracked words, keeping SECURITY DEFINER and `search_path`) is **not applied**, and applying it is an owner decision because learners would see a quiz on retakes again.

## Related Pages

- [[features/vocabulary-knowledge]] — Prose description
- [[algorithms/bkt-implementation-analysis]] — Full BKT audit and improvement history
- [[algorithms/bkt-implementation-analysis.tech]] — Technical analysis with function definitions
- [[database/schema.tech]] — Table DDL
- [[features/flashcards]] — FSRS scheduling
