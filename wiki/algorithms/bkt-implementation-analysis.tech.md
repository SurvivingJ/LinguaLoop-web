---
title: BKT System — Implementation Analysis (Technical)
type: algorithm-tech
status: complete
prose_page: ./bkt-implementation-analysis.md
last_updated: 2026-04-16
dependencies:
  - "bkt_update() — plpgsql IMMUTABLE"
  - "bkt_status() — plpgsql IMMUTABLE"
  - "bkt_update_comprehension() — plpgsql IMMUTABLE (Phase 7: +transit)"
  - "bkt_update_word_test() — plpgsql IMMUTABLE (Phase 7: +transit)"
  - "bkt_update_exercise() — plpgsql IMMUTABLE (Phase 5, Phase 7: +transit)"
  - "bkt_apply_decay() — plpgsql IMMUTABLE (Phase 7: FSRS stability path)"
  - "bkt_effective_p_known() — plpgsql IMMUTABLE (Phase 7: stability+evidence_count)"
  - "bkt_phase() — plpgsql IMMUTABLE (Phase 5)"
  - "bkt_phase_thresholds() — plpgsql IMMUTABLE (Phase 5)"
  - "get_session_senses() — plpgsql STABLE (Phase 7: unified session builder)"
  - "bkt_apply_lapse_penalty() — plpgsql (Phase 7)"
  - "bkt_infer_from_frequency() — plpgsql (Phase 7)"
  - "bkt_contextual_inference() — plpgsql (Phase 7)"
  - "update_vocabulary_from_test() — plpgsql"
  - "update_vocabulary_from_word_test() — plpgsql"
  - "get_word_quiz_candidates() — plpgsql STABLE DEFINER"
  - "get_vocab_recommendations() — plpgsql DEFINER"
  - "services/vocabulary/knowledge_service.py — VocabularyKnowledgeService"
  - "services/vocabulary/fsrs.py — FSRS scheduler"
  - "services/exercise_session_service.py — session builder (RPC consumer)"
  - "services/test_generation/orchestrator.py — per-question sense_ids"
  - "user_vocabulary_knowledge table"
  - "user_flashcards table"
  - "dim_word_senses table"
  - "dim_vocabulary table"
breaking_change_risk: low
---

# BKT System — Implementation Analysis (Technical)

## Architecture Map

```
Evidence Sources:
  ┌─ Comprehension Test ─► process_test_submission() calls app.py
  │     └─► knowledge_svc.update_from_comprehension()
  │           └─► RPC: update_vocabulary_from_test()
  │                 └─► bkt_update_comprehension(p, correct) [slip=0.10, guess=0.25, transit=0.02]
  │                 └─► bkt_status(p_after)
  │                 └─► UPSERT user_vocabulary_knowledge
  │           └─► _trigger_frequency_inference() if p_known >= 0.90
  │           └─► Auto-create flashcards (Python side)
  │     └─► knowledge_svc.apply_contextual_inference()  ◄── Phase 7: dampened update for untested words
  │
  ├─ Word Quiz ─► knowledge_svc.record_word_quiz_results()
  │     └─► For each word:
  │           └─► INSERT word_quiz_results
  │           └─► knowledge_svc.update_from_word_test()
  │                 └─► RPC: update_vocabulary_from_word_test()
  │                       └─► bkt_update_word_test(p, correct) [slip=0.05, guess=0.25, transit=0.05]
  │                 └─► _trigger_frequency_inference() if p_known >= 0.90
  │
  └─ Exercise (Vocab Dojo / Ladder) ─► record_attempt_with_updates()
        └─► INSERT exercise_attempts
        └─► knowledge_svc.update_from_word_test(exercise_type=...)
        └─► _update_fsrs_for_exercise()
              └─► bkt_apply_lapse_penalty() if FSRS lapses increased  ◄── Phase 7

Consumers:
  ┌─ Exercise Session Builder ─► RPC: get_session_senses()  ◄── Phase 7: single RPC
  │     └─► Bucket 'due': FSRS due flashcards with effective_p_known
  │     └─► Bucket 'learning': effective_p_known 0.25–0.75 (entropy-sorted)
  │     └─► Bucket 'new': effective_p_known < 0.30
  │     └─► All decay (FSRS stability + evidence-count fallback) computed in SQL
  │
  ├─ get_vocab_recommendations()
  │     └─► known_sense_ids from user_vocabulary → set intersection with test vocab
  │
  └─ get_word_quiz_candidates()
        └─► p_known BETWEEN 0.25 AND 0.75
        └─► score = p * (1-p) * (1 / ln(frequency_rank))
```

## Core BKT Formula (SQL)

```sql
-- bkt_update(p_current, p_correct, p_slip, p_guess) → numeric
IF p_correct THEN
    p_obs_knows := 1 - p_slip;       -- P(correct | knows) = 1 - slip
    p_obs_not_knows := p_guess;       -- P(correct | doesn't know) = guess
ELSE
    p_obs_knows := p_slip;            -- P(incorrect | knows) = slip
    p_obs_not_knows := 1 - p_guess;   -- P(incorrect | doesn't know) = 1 - guess
END IF;

RETURN CLAMP(0.02, 0.98,
    (p_obs_knows * p_current) /
    (p_obs_knows * p_current + p_obs_not_knows * (1 - p_current))
);
```

This is standard Bayesian posterior update with clamping. Mathematically correct.

## Evidence Flow Analysis

### Comprehension Tests → BKT

`update_vocabulary_from_test()` is a complex CTE:

```
question_senses:  unnest(q.sense_ids) → one row per (sense, is_correct) per question
deduped:          GROUP BY sense_id, bool_or(is_correct) → one row per sense
current_state:    LEFT JOIN user_vocabulary_knowledge → get existing p_known or frequency prior
updated:          bkt_update_comprehension(p_current, is_correct) → compute p_after
upserted:         INSERT ... ON CONFLICT → upsert with evidence counters
```

**Key nuance**: `bool_or` means if a sense appears in 3 questions and the learner gets 1 right and 2 wrong, the sense is treated as **correct** (single positive evidence). This is optimistic — it assumes one correct answer demonstrates knowledge regardless of other failures.

**Phase 7 fix — Per-question sense_ids:** Previously ALL transcript senses were assigned to EVERY question. Now `TestOrchestrator._match_question_senses()` matches vocabulary lemmas against each question's text + choices. Each question only gets the sense_ids for words that actually appear in it. This makes `bool_or` deduplication much more accurate since senses are no longer spuriously shared across questions.

**Phase 7 — Contextual inference:** After the main BKT update, `knowledge_svc.apply_contextual_inference()` applies a dampened update to transcript senses NOT directly tested by any question. Dampening = 0.30 × score_ratio, only fires when score ≥ 50%. This lets each test provide evidence for more words without inflating directly-tested senses.

### Exercises → BKT

**Phase 5 fix:** `update_vocabulary_from_word_test()` now accepts an optional `p_exercise_type text DEFAULT NULL` parameter. When provided, it calls `bkt_update_exercise(p, correct, exercise_type)` which uses exercise-type-specific slip/guess parameters. When NULL, falls back to `bkt_update_word_test(p, correct)` with fixed slip=0.05, guess=0.25.

**Phase 7 — Transit parameter:** All three update functions now apply a transit credit after the Bayesian update: `p_post + (1 - p_post) * P_TRANSIT`. Transit values: comprehension=0.02, recognition=0.05, recall/nuanced=0.08, production=0.10.

**Remaining observation**: The exercise session service (`record_attempt_with_updates()`) calls BKT for **every** exercise attempt, not just first attempts. The ladder service (`record_attempt()`) only calls BKT for first attempts (`if is_first_attempt`). This inconsistency means non-ladder exercises update BKT on retries too, potentially inflating p_known on second/third attempts.

## Table: user_vocabulary_knowledge

| Column | Type | Used By | Notes |
|--------|------|---------|-------|
| `p_known` | numeric | BKT core, session builder, vocab recs | The central probability |
| `status` | text | Session builder filters, UI display | Derived from p_known via bkt_status() |
| `evidence_count` | integer | **Not used in BKT formula** | Tracked but ignored — potential for confidence weighting |
| `comprehension_correct/wrong` | integer | Analytics only | Not used in calculations |
| `word_test_correct/wrong` | integer | Analytics only | Not used in calculations |
| `last_evidence_at` | timestamptz | Decay computation, sense ordering | Used by `bkt_apply_decay()` |

**Phase 7 update**: `evidence_count` is now consumed by the decay fallback path — more evidence = slower forgetting via `half_life = 30 * (1 + 0.5 * ln(1 + evidence_count))`. Future uses:
1. Weight the Bayesian update (more evidence → less change per event)
2. Set a confidence interval on p_known
3. Calibrate slip/guess parameters per sense

## Phase Thresholds: Inconsistency

Two different phase threshold maps exist in the codebase:

**ExerciseSessionService** (`services/exercise_session_service.py:28`):
```python
_PHASE_THRESHOLDS = [(0.30, 'A'), (0.55, 'B'), (0.80, 'C')]  # else D
```

**get_exercise_session RPC** (`wiki/features/vocab-dojo.tech.md`):
```sql
WHEN p_known < 0.40 THEN 'A'
WHEN p_known < 0.65 THEN 'B'
WHEN p_known < 0.80 THEN 'C'
ELSE 'D'
```

**These don't match.** Python uses 0.30/0.55/0.80; SQL uses 0.40/0.65/0.80. A word with p_known=0.35 would be Phase A in Python but Phase A in SQL too (both < 0.40), but at p_known=0.50 it would be Phase B in Python (>0.30) and Phase A in SQL (<0.40). This means the Python session builder and the SQL session builder select different exercise types for the same word.

## Improvements — Implementation Status

### 1. Exercise-Type-Specific BKT — ✅ IMPLEMENTED (Phase 5)

`bkt_update_exercise(p_current, p_correct, p_exercise_type)` — IMMUTABLE function with 4 cognitive tiers:

| Tier | Exercise Types | Slip | Guess | Transit (P7) | Rationale |
|------|---------------|------|-------|-------|-----------|
| Recognition (A) | text_flashcard, listening_flashcard, cloze_completion, phonetic_recognition, definition_match | 0.05 | 0.25 | 0.05 | Easy to guess, hard to slip |
| Recall (B) | jumbled_sentence, tl_nl_translation, nl_tl_translation, spot_incorrect_sentence, spot_incorrect_part, morphology_slot | 0.10 | 0.10 | 0.08 | Moderate both ways |
| Nuanced (C) | semantic_discrimination, collocation_gap_fill, collocation_repair, odd_one_out, odd_collocation_out | 0.15 | 0.20 | 0.08 | Higher slip (subtle distinctions) |
| Production (D) | verb_noun_match, context_spectrum, timed_speed_round, style_imitation | 0.20 | 0.05 | 0.10 | Hard to guess, easy to slip |
| Default | (unrecognized types) | 0.05 | 0.25 | 0.05 | Conservative fallback |

Called by `update_vocabulary_from_word_test()` when `p_exercise_type IS NOT NULL`.

### 2. FSRS Stability-Informed Decay — ✅ IMPLEMENTED (Phase 7, supersedes Phase 5)

**`bkt_apply_decay(p_known, p_last_evidence_at, p_stability, p_evidence_count)`** — IMMUTABLE. Two-path decay:

- **Path A (FSRS):** If `p_stability > 0`, use `retrievability = exp(-days / stability)`. This uses the research-backed FSRS memory model — accounts for spacing, lapses, and difficulty.
- **Path B (fallback):** Evidence-count-scaled half-life: `half_life = 30 * (1 + 0.5 * ln(1 + evidence_count))`. More evidence = slower forgetting.
- Floor: 0.10. No decay within 1 day.

**`bkt_effective_p_known(p_known, p_last_evidence_at, p_stability, p_evidence_count)`** — IMMUTABLE convenience wrapper.

**`get_session_senses(p_user_id, p_language_id, ...)`** — STABLE. Single RPC for session building that returns `(sense_id, effective_p_known, bucket, entropy)` with all decay computed in SQL. Session builders no longer do BKT math in Python.

### 3. Transit Parameter — ✅ IMPLEMENTED (Phase 7)

All three update functions now apply transit credit after Bayesian posterior:
```sql
v_p_post := v_p_post + (1.0 - v_p_post) * v_p_transit;
```

| Evidence Source | Transit |
|---|---|
| Comprehension test | 0.02 |
| Word test (default) | 0.05 |
| Recognition exercise | 0.05 |
| Recall/nuanced exercise | 0.08 |
| Production exercise | 0.10 |

### 4. FSRS Lapse → BKT Penalty — ✅ IMPLEMENTED (Phase 7)

**`bkt_apply_lapse_penalty(p_user_id, p_sense_id)`** — When FSRS records a lapse (rating=AGAIN), applies 20% penalty: `p_known *= 0.80`. Called from both `ExerciseSessionService._update_fsrs_for_exercise()` and `LadderService._update_fsrs()`.

### 5. Frequency-Tier Inference — ✅ IMPLEMENTED (Phase 7)

**`bkt_infer_from_frequency(p_user_id, p_language_id, p_known_sense_id, p_new_p_known)`** — When a rare word reaches "known" (p_known ≥ 0.90), boosts common words with `evidence_count < 3` to their frequency-based prior floor. Called from `knowledge_service.py._trigger_frequency_inference()`.

### 6. Sentence-Level Contextual Inference — ✅ IMPLEMENTED (Phase 7)

**`bkt_contextual_inference(p_user_id, p_language_id, p_contextual_sense_ids, p_score_ratio)`** — Dampened positive BKT update for transcript words not directly tested by any question. Dampening = 0.30 × score_ratio, only fires when score ≥ 50%. Positive-only (never lowers p_known).

**Prerequisite fix:** `TestOrchestrator._match_question_senses()` now assigns per-question sense_ids by matching vocab lemmas against question text + choices, instead of assigning all transcript senses to every question.

### 7. First-Attempt Gating Consistency — ❌ NOT YET IMPLEMENTED

`ExerciseSessionService.record_attempt_with_updates()` still calls BKT on every attempt, not just first attempts. The inconsistency with the ladder service remains.

### 8. Harmonize Phase Thresholds — ✅ IMPLEMENTED (Phase 5)

Canonical SQL functions `bkt_phase()` and `bkt_phase_thresholds()` provide the single source of truth:

| Phase | min_p_known | max_p_known |
|-------|-------------|-------------|
| A | 0.00 | 0.30 |
| B | 0.30 | 0.55 |
| C | 0.55 | 0.80 |
| D | 0.80 | 1.00 |

## Interaction With Other Systems

### BKT → Vocab Dojo Session Builder

**Phase 7:** The session builder now calls a single `get_session_senses()` SQL RPC that returns all candidate senses with decay-applied `effective_p_known` and bucket labels. Python is purely a consumer — no BKT math in application code.

The RPC computes:
1. Bucket assignment: `due` (FSRS due) / `learning` (effective 0.25–0.75) / `new` (effective < 0.30)
2. Entropy score: `p * (1 - p)` for within-bucket prioritization
3. Decay via `bkt_effective_p_known()` with LEFT JOIN to `user_flashcards` for FSRS stability

### BKT ↔ FSRS Bridge (Bidirectional)

**BKT → FSRS:** `VocabularyKnowledgeService._auto_create_flashcards()` creates FSRS cards when BKT status moves to "encountered" or "learning". FSRS initial difficulty set from p_known via `difficulty_from_p_known()`.

**FSRS → BKT (Phase 7):**
1. **Decay:** `bkt_apply_decay()` uses FSRS stability as the decay rate. Low stability (fragile memory) → faster p_known decay.
2. **Lapse penalty:** When FSRS records a lapse, `bkt_apply_lapse_penalty()` reduces p_known by 20%.

### BKT → Vocabulary Ladder

The ladder uses BKT to set starting level via `bkt_to_starting_level()`:

```
p_known < 0.15 → Level 1
p_known < 0.40 → Level 3
p_known < 0.60 → Level 5
p_known < 0.80 → Level 7
p_known ≥ 0.80 → Level 9
```

Ladder exercises update BKT through `update_from_word_test()` and trigger lapse penalty via the FSRS bridge.

### BKT → Comprehension Tests (Phase 7)

**Contextual inference:** Test results now provide evidence for untested vocabulary. After the main BKT update, `apply_contextual_inference()` gives a dampened boost to transcript words not in any question's `sense_ids`.

**Frequency inference:** When any word reaches "known" status, `bkt_infer_from_frequency()` boosts common words, reducing the pool of words that need direct testing.

## Related Pages

- [[algorithms/bkt-implementation-analysis]] — Prose analysis
- [[features/vocabulary-knowledge.tech]] — Original specification
- [[features/vocab-dojo.tech]] — Session builder that consumes BKT
- [[database/rpcs.tech]] — Full RPC SQL definitions
