---
title: Vocabulary Ladder & Exercise System — Implementation Analysis (Technical)
type: algorithm-tech
status: complete
prose_page: ./ladder-implementation-analysis.md
last_updated: 2026-04-15
dependencies:
  - "services/vocabulary_ladder/ladder_service.py — LadderService"
  - "services/vocabulary_ladder/config.py — LADDER_LEVELS, BKT_TO_LEVEL"
  - "services/vocabulary_ladder/asset_pipeline.py — VocabAssetPipeline"
  - "services/vocabulary_ladder/asset_generators/ — 3 prompt generators"
  - "services/vocabulary_ladder/validators.py — VocabAssetValidator"
  - "services/vocabulary_ladder/exercise_renderer.py"
  - "services/exercise_session_service.py — ExerciseSessionService"
  - "services/exercise_generation/config.py — PHASE_MAP, type registries"
  - "services/vocabulary/knowledge_service.py — VocabularyKnowledgeService"
  - "services/vocabulary/fsrs.py — FSRS scheduler"
  - "exercises table"
  - "exercise_attempts table"
  - "word_assets table"
  - "user_word_ladder table"
  - "user_exercise_sessions table"
  - "user_vocabulary_knowledge table"
  - "user_flashcards table"
breaking_change_risk: medium
---

# Vocabulary Ladder & Exercise System — Implementation Analysis (Technical)

## Architecture: Two Paths

```
Path A: Vocabulary Ladder (per-word progression)
═══════════════════════════════════════════════
  Offline:
    VocabAssetPipeline.generate_for_sense(sense_id)
      → CoreAssetGenerator (Prompt 1: Gemini Flash Lite)
        → definition, collocate, 6 sentences, POS, semantic_class
      → ExerciseAssetGenerator (Prompt 2: Claude Sonnet)
        → L1 phonetic, L3 cloze, L5 collocation gap, L6 semantic disc
      → TransformAssetGenerator (Prompt 3: Claude Sonnet)
        → L4 morphology, L7 spot incorrect, L8 collocation repair
      → VocabAssetValidator → word_assets table → exercises table

  Online:
    LadderService.get_exercises_for_session(user_id, language_id)
      → get_words_for_session: batch-query FSRS + BKT + ladder state
      → batch_fetch_exercises: match (sense_id, level) → exercises
      → enrich with lemma/definition/pronunciation

    LadderService.record_attempt(user_id, sense_id, exercise_id, ...)
      → INSERT exercise_attempts
      → IF first_attempt AND correct: advance ladder level
      → Update BKT via knowledge_svc.update_from_word_test()
      → Update FSRS via schedule_review()


Path B: Daily Exercise Session (mixed sources)
═══════════════════════════════════════════════
  ExerciseSessionService.get_or_create_daily_session(user_id, language_id)
    → Check user_exercise_sessions cache (today's session)
    → If stale, _compute_session():
        Bucket 1 (40%): FSRS due senses → phase-gated exercise selection
        Bucket 2 (40%): BKT uncertainty zone (0.25-0.75) → exercises
        Bucket 3 (20%): New/encountered senses (<0.30) → Phase A exercises
        Bucket 4 (fill): Supplementary grammar/collocation by complexity tier
        Bucket 5 (≤5):  Ladder exercises via LadderService
        Bucket 6 (≤3):  Virtual jumbled sentences from past test transcripts
    → Shuffle → Cache in user_exercise_sessions → Return enriched session
```

## Ladder Config: What's Actually Defined

File: `services/vocabulary_ladder/config.py`

```python
LADDER_LEVELS = {
    1: {'name': 'Phonetic/Orthographic', 'exercise_type': 'phonetic_recognition',    'prompt': 'prompt2'},
    2: {'name': 'Definition Match',      'exercise_type': 'definition_match',        'prompt': 'database'},
    3: {'name': 'Cloze Completion',      'exercise_type': 'cloze_completion',        'prompt': 'prompt2'},
    4: {'name': 'Morphology Slot',       'exercise_type': 'morphology_slot',         'prompt': 'prompt3'},
    5: {'name': 'Collocation Gap',       'exercise_type': 'collocation_gap_fill',    'prompt': 'prompt2'},
    6: {'name': 'Semantic Discrimination','exercise_type': 'semantic_discrimination', 'prompt': 'prompt2'},
    7: {'name': 'Spot Incorrect',        'exercise_type': 'spot_incorrect_sentence', 'prompt': 'prompt3'},
    8: {'name': 'Collocation Repair',    'exercise_type': 'collocation_repair',      'prompt': 'prompt3'},
    9: {'name': 'Jumbled Sentence',      'exercise_type': 'jumbled_sentence',        'prompt': 'local'},
}
```

Generation sources per level:
- **Prompt 2** (Claude Sonnet): Levels 1, 3, 5, 6 — lexical/semantic exercises
- **Prompt 3** (Claude Sonnet): Levels 4, 7, 8 — grammar/structural exercises
- **Database**: Level 2 — definition match from dim_word_senses definitions
- **Local**: Level 9 — jumbled sentence via backend tokenization (no LLM)

BKT → Starting Level mapping:
```python
BKT_TO_LEVEL = [
    (0.15, 1),   # p_known < 0.15 → start at Level 1
    (0.40, 3),   # p_known < 0.40 → start at Level 3
    (0.60, 5),   # p_known < 0.60 → start at Level 5
    (0.80, 7),   # p_known < 0.80 → start at Level 7
    (1.01, 9),   # p_known ≥ 0.80 → start at Level 9
]
```

## LadderService: Attempt Processing Detail

File: `services/vocabulary_ladder/ladder_service.py`, method `record_attempt()`

```
record_attempt(user_id, sense_id, exercise_id, is_correct, is_first_attempt, time_taken_ms)
  │
  ├── Get current ladder row from user_word_ladder
  │     (if not exists: default level=1, active_levels=[1..9])
  │
  ├── INSERT exercise_attempts row
  │
  ├── IF is_first_attempt:
  │     ├── Update BKT: knowledge_svc.update_from_word_test()
  │     ├── IF is_correct:
  │     │     ├── new_level = next_active_level(current, active_levels)
  │     │     ├── UPSERT user_word_ladder with new_level  ◄── IMMEDIATE promotion
  │     │     └── Update FSRS (rating = EASY if <5s, else GOOD)
  │     └── IF not correct:
  │           ├── result['requeue'] = True                ◄── NO demotion
  │           └── Update FSRS (rating = AGAIN)
  │
  └── IF not first_attempt:
        ├── IF correct: requeue = False (move on)
        └── IF not correct: requeue = True (try again)
```

### Missing From Implementation

1. ~~**No `first_try_success_count`**~~ — ✅ Column exists (Phase 4), Python logic not yet updated
2. ~~**No `first_try_failure_count`**~~ — ✅ Column exists (Phase 4), Python logic not yet updated
3. ~~**No `word_state` tracking**~~ — ✅ Column exists (Phase 4, states: new/active/fragile/stable/mastered), Python logic not yet updated
4. **No inter-session validation** — `last_success_session_date` column exists (Phase 4), Python not yet using it
5. **No capstone level** — ladder ends at L9 (jumbled sentence)

## ExerciseSessionService: The 6-Bucket Algorithm

File: `services/exercise_session_service.py`, method `_compute_session()`

### Bucket Distribution

```python
dist = Config.EXERCISE_SLOT_DISTRIBUTION
# Expected: {'due_review': 0.40, 'active_learning': 0.40, 'new_word': 0.20}
# For session_size=20: due=8, learning=8, new=4
```

### Bucket 1: FSRS Due Reviews

```
user_flashcards WHERE due_date <= TODAY AND state IN ('review', 'relearning')
  → JOIN user_vocabulary_knowledge for p_known
  → Phase = _determine_phase(p_known)  [thresholds: 0.30/0.55/0.80]
  → Select exercise by weighted-random type within phase
```

### Bucket 2: Active Learning (BKT Uncertainty)

```
user_vocabulary_knowledge WHERE p_known BETWEEN 0.25 AND 0.75
  AND status NOT IN ('user_marked_unknown', 'unknown')
  → Sort by p*(1-p) DESC (maximum entropy)
  → Select exercises with phase-gated types
```

### Bucket 3: New Words

```
user_vocabulary_knowledge WHERE p_known < 0.30
  AND status IN ('encountered', 'unknown')
  → Fallback: user_flashcards WHERE state = 'new'
  → Phase A exercises only
```

### Bucket 4: Supplementary (Grammar/Collocation)

```
exercises WHERE word_sense_id IS NULL  (non-vocabulary)
  AND complexity_tier IN (estimated from avg p_known)
  → Random selection
```

### Bucket 5: Ladder Exercises (≤5)

```
LadderService.get_words_for_session() → up to 5 words
  → For each: find exercise at current_level
```

### Bucket 6: Virtual Jumbled Sentences (≤3)

```
test_attempts WHERE percentage > 50
  → tests.transcript → split into sentences
  → Filter by word count ≥ 3
  → Create virtual exercises (not stored in DB)
```

### Overflow Redistribution

If any bucket returns fewer exercises than its allocation, remaining slots are filled from other buckets in priority order (due → learning → new). If still not full, supplementary grammar/collocation exercises fill the gap.

## Exercise Selection: Phase-Gated Weighted Sampling

```python
def _get_eligible_types_weighted(phase):
    """Primary phase gets 70%, previous phase gets 30%."""
    # Phase A: 100% A types (no prior phase)
    # Phase B: 70% B types + 30% A types
    # Phase C: 70% C types + 30% B types
    # Phase D: 70% D types + 30% C types
```

Types per phase (from `PHASE_MAP`):
- **A**: text_flashcard, listening_flashcard, cloze_completion
- **B**: jumbled_sentence, spot_incorrect_*, tl_nl_translation, nl_tl_translation, style_sentence_completion, style_transition_fill
- **C**: semantic_discrimination, collocation_gap_fill, collocation_repair, odd_*, style_pattern_match, style_voice_transform
- **D**: verb_noun_match, context_spectrum, timed_speed_round, style_imitation

### N+1 Query Pattern

`_select_exercises_for_senses()` executes one DB query per sense per type attempt. For 8 senses × ~5 type attempts each = ~40 queries. This is the main performance bottleneck.

**Fix**: Batch-fetch all exercises for selected senses in one query, then filter in Python:

```python
# Instead of: for each sense, for each type, query DB
# Do: SELECT * FROM exercises WHERE word_sense_id IN (...) AND language_id = ...
# Then: filter by type in Python
```

## Asset Pipeline: 3-Prompt Flow

File: `services/vocabulary_ladder/asset_pipeline.py`

```
VocabAssetPipeline.generate_for_sense(sense_id, language_id)
  │
  ├── Check existing: _assets_exist() [all 3 types valid?]
  │
  ├── Fetch corpus sentences from tests + conversations
  │
  ├── Prompt 1: CoreAssetGenerator.generate()
  │     → Output: pos, semantic_class, definition, collocate, pronunciation, IPA, syllable_count, 6 sentences, morphological_forms
  │     → Validate: VocabAssetValidator.validate_prompt1()
  │     → Store: word_assets (asset_type='prompt1_core')
  │     → Side effect: update dim_vocabulary.semantic_class + dim_word_senses phonetics
  │
  ├── Compute active_levels from semantic_class
  │
  ├── Prompt 2: ExerciseAssetGenerator.generate()
  │     → Output: L1, L3, L5 (if active), L6 exercises with options + reasoning
  │     → Validate: VocabAssetValidator.validate_prompt2()
  │     → Store: word_assets (asset_type='prompt2_exercises')
  │
  └── Prompt 3: TransformAssetGenerator.generate()
        → Output: L4, L7, L8 (if active) exercises with options + reasoning
        → Validate: VocabAssetValidator.validate_prompt3()
        → Store: word_assets (asset_type='prompt3_transforms')
```

### Corpus Sentence Sourcing

Before generating, the pipeline searches for existing sentences containing the target word:
1. Search test transcripts (`tests.transcript`)
2. Search conversation content (`conversations.content`)
3. Extract sentences containing the lemma
4. These corpus sentences reduce LLM generation needs (Prompt 1 generates `6 - len(corpus)` sentences)

## Database Tables: Actual vs Wiki

### `user_word_ladder` (actual — updated Phase 4)

```sql
CREATE TABLE user_word_ladder (
    user_id                    uuid NOT NULL REFERENCES users(id),
    sense_id                   integer NOT NULL REFERENCES dim_word_senses(id),
    current_level              integer NOT NULL DEFAULT 1 CHECK (current_level BETWEEN 1 AND 9),
    active_levels              integer[] NOT NULL DEFAULT '{1,2,3,4,5,6,7,8,9}',
    updated_at                 timestamptz NOT NULL DEFAULT now(),
    -- Phase 4 additions:
    first_try_success_count    integer NOT NULL DEFAULT 0,
    first_try_failure_count    integer NOT NULL DEFAULT 0,
    consecutive_failures       integer NOT NULL DEFAULT 0,
    total_attempts             integer NOT NULL DEFAULT 0,
    word_state                 text NOT NULL DEFAULT 'active'
                               CHECK (word_state IN ('new', 'active', 'fragile', 'stable', 'mastered')),
    last_success_session_date  date,
    review_due_at              timestamptz,
    PRIMARY KEY (user_id, sense_id)
);

-- Indexes:
CREATE INDEX idx_user_word_ladder_review_due ON user_word_ladder(user_id, review_due_at)
    WHERE review_due_at IS NOT NULL;
CREATE INDEX idx_user_word_ladder_state ON user_word_ladder(user_id, word_state);
```

**Note:** The Phase 4 columns enable the promotion/demotion counter logic (promote after 2 cross-session successes, demote after 3 consecutive first-attempt failures) and word state tracking. The `word_state` values differ from the original wiki proposal (uses `new/active/fragile/stable/mastered` instead of `new/learning/fragile_receptive/stable_receptive/fragile_productive/stable_productive`).

### `exercises` (relevant columns for ladder)

```sql
-- Ladder-specific columns:
ladder_level    integer CHECK (ladder_level BETWEEN 1 AND 9 OR ladder_level IS NULL)
word_sense_id   integer REFERENCES dim_word_senses(id)
word_asset_id   bigint REFERENCES word_assets(id)

-- Ladder-specific indexes:
idx_exercises_ladder (word_sense_id, ladder_level WHERE ladder_level IS NOT NULL)
idx_exercises_sense (word_sense_id WHERE NOT NULL)
```

### `user_exercise_sessions` (daily session cache)

```sql
CREATE TABLE user_exercise_sessions (
    user_id       uuid NOT NULL REFERENCES users(id),
    language_id   integer NOT NULL,
    load_date     date NOT NULL DEFAULT CURRENT_DATE,
    exercise_ids  jsonb NOT NULL,      -- Array of exercise selection dicts
    completed_ids jsonb DEFAULT '[]',  -- Exercise IDs already completed
    session_size  integer NOT NULL,
    PRIMARY KEY (user_id, language_id)
);
```

Session is cached per (user, language) pair. Recomputed when `load_date != today`.

### `user_exercise_history` — ✅ CREATED (Phase 4)

Purpose-built anti-repetition table, auto-populated via trigger from `exercise_attempts`:

```sql
CREATE TABLE user_exercise_history (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id          uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    language_id      smallint NOT NULL REFERENCES dim_languages(id),
    exercise_id      uuid NOT NULL REFERENCES exercises(id),
    sense_id         integer REFERENCES dim_word_senses(id),
    exercise_type    text NOT NULL,
    is_correct       boolean NOT NULL,
    is_first_attempt boolean NOT NULL DEFAULT true,
    session_date     date NOT NULL DEFAULT CURRENT_DATE,
    created_at       timestamptz NOT NULL DEFAULT now()
);

-- Indexes:
CREATE INDEX idx_ueh_anti_repeat ON user_exercise_history(user_id, language_id, session_date, exercise_id);
CREATE INDEX idx_ueh_user_lang_date ON user_exercise_history(user_id, language_id, session_date DESC);
CREATE INDEX idx_ueh_user_sense ON user_exercise_history(user_id, sense_id, created_at DESC);
```

Replaces the old pattern of scanning 500 rows from `exercise_attempts`. The `sync_exercise_history()` trigger copies data on every `exercise_attempts` INSERT.

## Improvements — Implementation Status

### 1. Promotion Counter Schema — ✅ IMPLEMENTED (Phase 4)

Columns added to `user_word_ladder`: `first_try_success_count`, `first_try_failure_count`, `consecutive_failures`, `total_attempts`, `word_state`, `last_success_session_date`, `review_due_at`. See table DDL above.

**Note:** The Python-side `LadderService.record_attempt()` has NOT yet been updated to use these columns. The schema is in place but the promotion/demotion logic still uses the old immediate-promotion behavior. Python code changes needed:

```python
def record_attempt(self, ...):
    if is_first_attempt:
        progress.total_attempts += 1
        if is_correct:
            today = date.today()
            if progress.last_success_session_date != today:
                progress.first_try_success_count += 1
                progress.last_success_session_date = today
            progress.consecutive_failures = 0

            if progress.first_try_success_count >= 2:
                promote(progress)
                progress.first_try_success_count = 0
        else:
            progress.consecutive_failures += 1
            progress.first_try_success_count = 0
            if progress.consecutive_failures >= 3:
                demote(progress)
                progress.consecutive_failures = 0
```

### 2. Session Builder N+1 Fix

Replace per-sense exercise queries with a batch approach:

```python
def _select_exercises_batch(self, senses, language_id, exclude_ids):
    """Batch-fetch all exercises for selected senses in one query."""
    sense_ids = [s['sense_id'] for s in senses]
    resp = (
        self.db.table('exercises')
        .select('id, exercise_type, content, word_sense_id')
        .eq('language_id', language_id)
        .eq('is_active', True)
        .in_('word_sense_id', sense_ids)
        .limit(len(senses) * 10)
        .execute()
    )
    # Group by sense_id
    by_sense = defaultdict(list)
    for row in (resp.data or []):
        if row['id'] not in exclude_ids:
            by_sense[row['word_sense_id']].append(row)

    # For each sense, pick best exercise by phase
    picks = []
    for sense in senses:
        candidates = by_sense.get(sense['sense_id'], [])
        phase = _determine_phase(sense['p_known'])
        eligible_types, weights = _get_eligible_types_weighted(phase)
        # ... weighted selection from candidates
    return picks
```

### 3. Create user_exercise_history Table — ✅ IMPLEMENTED (Phase 4)

Table created with auto-populate trigger. See table DDL in the Database Tables section above.

**Note:** Python-side `_get_recent_exercise_ids()` in `ExerciseSessionService` has NOT yet been updated to query `user_exercise_history` instead of scanning `exercise_attempts`. The table is populated and indexed, but the session builder still uses the old pattern.

### 4. Level 10 Capstone Architecture (Sketch)

```python
# New exercise type: 'capstone_production'
# Generated at runtime, not pre-cached

class CapstoneExercise:
    def generate_prompt(self, sense_id, language_id):
        """Create a translation/production task containing the target word."""
        # Fetch a corpus sentence containing the word
        # Present in NL, ask for TL translation
        # OR: present a scenario, ask learner to write a sentence using the word

    def grade_response(self, user_response, target_word, context):
        """LLM-grade the response for correctness and natural use."""
        # Check: target word present and correctly used
        # Check: grammatically correct
        # Check: semantically appropriate
        # Return: score (0-1), feedback text

# Cost management:
# - Only Level 9 graduates trigger capstone (small population)
# - Cache grading rubrics per sense
# - Use cheap model (Gemini Flash) for grading, not Sonnet
```

## File Inventory

| File | Purpose | Lines |
|------|---------|-------|
| `services/vocabulary_ladder/config.py` | Ladder levels, BKT mapping, POS routing | ~166 |
| `services/vocabulary_ladder/ladder_service.py` | Session building, attempt recording, FSRS/BKT integration | ~515 |
| `services/vocabulary_ladder/asset_pipeline.py` | 3-prompt orchestrator, corpus sourcing, storage | ~404 |
| `services/vocabulary_ladder/validators.py` | Schema + linguistic + pedagogical validation | — |
| `services/vocabulary_ladder/exercise_renderer.py` | Frontend-ready exercise formatting | — |
| `services/vocabulary_ladder/asset_generators/prompt1_core.py` | Gemini Flash: classification + sentences | — |
| `services/vocabulary_ladder/asset_generators/prompt2_exercises.py` | Claude Sonnet: L1,3,5,6 exercises | — |
| `services/vocabulary_ladder/asset_generators/prompt3_transforms.py` | Claude Sonnet: L4,7,8 exercises | — |
| `services/exercise_session_service.py` | Daily session builder (6 buckets) | ~1003 |
| `services/exercise_generation/config.py` | PHASE_MAP, type registries, distributions | ~178 |

## Related Pages

- [[algorithms/ladder-implementation-analysis]] — Prose analysis
- [[algorithms/vocabulary-ladder.tech]] — Original specification
- [[features/exercises.tech]] — Exercise table schema
- [[features/vocab-dojo.tech]] — Exercise serving algorithm
- [[algorithms/bkt-implementation-analysis.tech]] — BKT analysis (feeds into ladder)
- [[database/schema.tech]] — Full table DDL
