---
title: Vocabulary Ladder & Exercise System — Implementation Analysis & Improvements
type: algorithm
status: in-progress
tech_page: ./ladder-implementation-analysis.tech.md
last_updated: 2026-04-11
open_questions:
  - "Should the two session builders (ExerciseSessionService and LadderService) be consolidated?"
  - "When will Level 10 (Capstone Production) be implemented?"
  - "Should demotion be implemented before or after accumulating more attempt data?"
---

# Vocabulary Ladder & Exercise System — Implementation Analysis & Improvements

## Purpose

This page analyses the vocabulary ladder (9-level progression) and exercise serving system as implemented in the codebase, identifies significant discrepancies between documentation and code, and proposes improvements.

## Current State Summary

The system has three major components:

1. **Asset Pipeline** (`VocabAssetPipeline`) — 3-prompt LLM generation of immutable exercise assets per word sense
2. **Ladder Service** (`LadderService`) — Per-user per-word level tracking and session building
3. **Exercise Session Service** (`ExerciseSessionService`) — The primary daily session builder using a 6-bucket algorithm

## Critical Discrepancies: Wiki vs Code

### 1. Nine Levels, Not Ten

The wiki describes a 10-level ladder with Level 10 being "Capstone Production" (free-text, LLM-graded). **The code only defines 9 levels** (config.py LADDER_LEVELS maps 1–9). Level 10 is not implemented — there's no exercise type for it, no generation pipeline, and no runtime LLM grading path.

The `user_word_ladder.current_level` column has a CHECK constraint of 1–9, confirming the 9-level implementation.

### 2. Simplified Promotion (No 2-Session Requirement)

The wiki describes promotion requiring "first-try success in 2 separate spaced-repetition sessions." The code promotes on **any single first-attempt correct answer**:

```python
# ladder_service.py:275-279
if is_correct:
    new_level = next_active_level(current_level, active_levels)
    if new_level:
        self._update_ladder(user_id, sense_id, new_level, active_levels)
```

There's no `first_try_success_count`, no session tracking, no inter-session validation. One correct first attempt = immediate promotion.

### 3. No Demotion

The wiki describes demotion after "2 consecutive first-attempt failures." The code does not implement demotion at all. When a first attempt fails, the exercise is requeued within the session, but the ladder level never decreases:

```python
# ladder_service.py:288-290
else:
    result['requeue'] = True  # Re-serve later in session
    self._update_fsrs(...)     # Update FSRS, but level unchanged
```

### 4. Missing Table: `user_word_progress`

The wiki's vocabulary-ladder.tech.md describes a `user_word_progress` table with columns: `first_try_success_count`, `first_try_failure_count`, `word_state`, `total_attempts`, `review_due_at`. **This table does not exist.** The actual table is `user_word_ladder` with a simpler schema:

| Column | Type | Notes |
|--------|------|-------|
| `user_id` | uuid | PK part 1 |
| `sense_id` | integer | PK part 2 |
| `current_level` | integer | CHECK 1–9 |
| `active_levels` | integer[] | Which levels are active (skips for concrete nouns) |
| `updated_at` | timestamptz | |

No word_state, no attempt counters, no review scheduling at the ladder level.

### 5. Exercise Type Names Differ

| Wiki Level | Wiki Exercise Type | Code Exercise Type | Match? |
|------------|-------------------|-------------------|--------|
| 1 | Listening Flashcard | `phonetic_recognition` | Different name |
| 2 | Text Flashcard | `definition_match` | Different name |
| 3 | Cloze Completion | `cloze_completion` | ✓ |
| 4 | Grammar Slot | `morphology_slot` | Different name |
| 5 | Collocation Gap Fill | `collocation_gap_fill` | ✓ |
| 6 | Semantic Discrimination | `semantic_discrimination` | ✓ |
| 7 | Spot Incorrect Sentence | `spot_incorrect_sentence` | ✓ |
| 8 | Collocation Repair | `collocation_repair` | ✓ |
| 9 | Jumbled Sentence | `jumbled_sentence` | ✓ |
| 10 | Capstone Production | Not implemented | Missing |

### 6. Two Competing Session Builders

The codebase has two independent session-building systems:

- **`ExerciseSessionService`** (the main one) — builds daily sessions with 6 buckets: FSRS due, active learning, new words, supplementary grammar/collocation, ladder exercises, user test sentences
- **`LadderService`** — has its own `get_exercises_for_session()` method that selects words and exercises

`ExerciseSessionService` calls `LadderService` as bucket 5 (limited to 5 exercises per session). But `LadderService` also has a standalone session path via the vocab dojo route.

## What Works Well

### 1. Generate-Once Architecture

The 3-prompt pipeline (`VocabAssetPipeline`) generates immutable exercise assets stored in `word_assets`. This is the right design — exercise content doesn't change, making spaced repetition signals meaningful and avoiding LLM cost on every session.

### 2. POS-Aware Level Routing

Concrete nouns skip collocation levels (5, 8) via `compute_active_levels()`. This avoids pedagogically meaningless exercises and reduces the ladder from 9 to 7 levels for those words.

### 3. BKT-Informed Starting Levels

New words don't start at Level 1 unconditionally. `bkt_to_starting_level()` maps p_known to a starting level, so words the learner probably already knows skip basic recognition exercises. This prevents boredom.

### 4. Language-Specific Adaptation

The language spec system (`en.json`, `zh.json`, `ja.json`) adapts Level 4 exercises based on typological features: morphology for English, particles/measure words for Chinese, both for Japanese.

### 5. Validation Pipeline

Generated exercises pass through schema, linguistic, and pedagogical validation before being stored. Invalid assets are flagged (`is_valid=false`, `validation_errors` array) for admin review.

### 6. Rich Session Composition

`ExerciseSessionService._compute_session()` is a sophisticated 6-bucket algorithm:
1. FSRS due reviews (40%)
2. BKT uncertainty zone (40%)
3. New/encountered words (20%)
4. Supplementary grammar/collocation fill
5. Vocabulary ladder exercises (up to 5)
6. Virtual jumbled sentences from user's past test transcripts

This produces varied, engaging sessions.

## What Needs Improvement

### Priority 1: Implement Proper Promotion Tracking (Medium effort, High impact)

Add promotion counters to `user_word_ladder`:

```sql
ALTER TABLE user_word_ladder
    ADD COLUMN first_try_success_count integer DEFAULT 0,
    ADD COLUMN first_try_failure_count integer DEFAULT 0,
    ADD COLUMN word_state text DEFAULT 'new';
```

Then gate promotion on 2 successes across separate sessions (not just calendar days — actual distinct session IDs):

- Track `last_success_session_id` and `current_success_session_id`
- Promote only when both are non-null and different

### Priority 2: Implement Demotion (Small effort, Medium impact)

When first-attempt failure count reaches 2 consecutive sessions, drop one level:

```python
if not is_correct and is_first_attempt:
    progress.first_try_failure_count += 1
    if progress.first_try_failure_count >= 2:
        prev_level = get_prev_active_level(current_level, active_levels)
        if prev_level:
            update_ladder(user_id, sense_id, prev_level, active_levels)
```

For the final level, demote to the highest stable receptive level (Level 6 or 7).

### Priority 3: Consolidate Session Builders (Medium effort, High impact)

The two session builders create maintenance burden and inconsistency. Consolidate:

- Move ladder-specific logic into `ExerciseSessionService` as a first-class bucket
- Let `LadderService` focus on progression (attempt recording, level management)
- The SQL-based `get_exercise_session` RPC (currently in the wiki but not connected to the Python code) should be the single source of truth for session building

### Priority 4: Implement Level 10 — Capstone Production (Large effort, High impact)

This is the most impactful missing feature. A learner completing 9 levels of receptive/recall exercises hasn't proven they can produce the word. The capstone would:

- Present a target sentence for translation or a prompt requiring the target word
- Use runtime LLM grading (Claude or GPT) to evaluate the response
- Provide detailed feedback on grammatical/semantic accuracy
- Only pass if the target word is used correctly in context

Requires: new exercise type, runtime LLM call, grading rubric, cost management.

### Priority 5: Anti-Repetition at Ladder Level (Small effort, Medium impact)

The `ExerciseSessionService` has anti-repetition guards (cooldown window from `exercise_attempts`), but the `LadderService` doesn't implement any. The same exercise could be served on consecutive sessions. Add:

- Exercise cooldown: same exercise_id not re-served within 3 days
- If only one exercise exists for a (sense, level) pair, skip the word for that session

### Priority 6: IRT Difficulty Calibration (Medium effort, Medium impact)

The `exercises` table already has `irt_difficulty` and `irt_discrimination` columns (defaulting to 0.0 and 1.0). These are never updated from actual attempt data. A background job could periodically fit IRT parameters:

```python
# For each exercise with >20 attempts:
irt_difficulty = -log(correct_count / (attempt_count - correct_count))
```

This would enable adaptive exercise selection — choose exercises at the learner's current difficulty frontier rather than by type alone.

## Quantitative Impact Assessment

| Improvement | Dev Effort | User Impact | Data Risk |
|-------------|-----------|-------------|-----------|
| Proper promotion tracking | M (4–8h) | High — prevents premature advancement | Low (additive schema) |
| Demotion logic | S (2–4h) | Medium — catches regression | Low |
| Consolidate session builders | M (4–8h) | Medium — consistency + maintainability | Low |
| Level 10 capstone | L (2–3d) | Very high — completes the learning arc | Medium (runtime LLM cost) |
| Anti-repetition in ladder | XS (1–2h) | Medium — prevents staleness | None |
| IRT calibration | M (4–8h) | Medium — better exercise targeting | None |

## Related Pages

- [[algorithms/ladder-implementation-analysis.tech]] — Technical details with code references
- [[algorithms/vocabulary-ladder]] — Original ladder design
- [[algorithms/vocabulary-ladder.tech]] — Original ladder technical specification
- [[features/exercises]] — Exercise type inventory
- [[features/vocab-dojo]] — Adaptive exercise serving
- [[features/vocabulary-knowledge]] — BKT integration
- [[algorithms/bkt-implementation-analysis]] — BKT analysis (interacts with ladder)
