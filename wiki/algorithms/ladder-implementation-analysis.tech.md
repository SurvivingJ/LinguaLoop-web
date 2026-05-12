---
title: Vocabulary Ladder & Exercise System — Implementation Analysis (Technical)
type: algorithm-tech
status: in-progress
prose_page: ./ladder-implementation-analysis.md
last_updated: 2026-05-12
dependencies:
  - "migrations/phase8_momentum_bands.sql — Momentum Bands core (1184 lines)"
  - "migrations/phase9_get_exercise_session.sql — daily-session SQL RPC + helpers"
  - "migrations/phase10_ladder_advancement_demotion.sql — cross-session gate + demotion (replaces ladder_record_attempt)"
  - "services/vocabulary_ladder/ladder_service.py — thin Python wrapper (~345 lines)"
  - "services/vocabulary_ladder/config.py — constants and helpers (~448 lines)"
  - "services/vocabulary_ladder/asset_pipeline.py — VocabAssetPipeline"
  - "services/vocabulary_ladder/asset_generators/ — three prompt generators"
  - "services/vocabulary_ladder/validators.py — VocabAssetValidator"
  - "services/exercise_session_service.py — daily mixed-session orchestrator (~500 lines; Phase 9 slim-down)"
  - "routes/vocab_dojo.py — six endpoints"
  - "routes/exercises.py — daily session endpoints"
  - "user_word_ladder, user_vocabulary_knowledge, user_flashcards tables"
  - "exercises, word_assets, exercise_attempts, user_exercise_history tables"
  - "user_exercise_sessions table (daily session cache)"
breaking_change_risk: high
---

# Vocabulary Ladder & Exercise System — Implementation Analysis (Technical)

## Architecture: Two SQL-RPC Surfaces

```
Path A: Vocabulary Dojo (per-word ladder)
═════════════════════════════════════════
  GET /api/vocab-dojo/session   ([routes/vocab_dojo.py:14])
    → _ensure_ladder_rows(): lazy-init user_word_ladder for senses
                              that have exercises but no row yet
    → db.rpc('get_ladder_session', user, language, count)
        WITH candidates AS (...due, exists check...),
             scored AS (...priority + target_family...),
             top_words AS (LIMIT count),
             seen_today AS (...user_exercise_history...),
             word_exercises AS (RANK by family/variant/random),
             selected AS (rn=1)
        → 15-column TABLE return

  POST /api/vocab-dojo/attempt
    → LadderService.record_attempt(...) → ladder_record_attempt RPC

  POST /api/vocab-dojo/gate, /gate/result
    → assemble_gate (Python) → pass_gate (RPC) OR
      record_attempt(exercise_context='gate') per failed item

  POST /api/vocab-dojo/stress-test, /stress-test/result
    → assemble_stress_test (Python) → graduate (RPC, FSRS handoff)


Path B: Daily Mixed Session (Phase 9, single SQL RPC)
═════════════════════════════════════════════════════
  GET /api/exercises/session   ([routes/exercises.py:128])
    → ExerciseSessionService.get_or_create_daily_session()
    → Cache lookup: user_exercise_sessions WHERE load_date = today
    → If stale, _compute_session():
        db.rpc('get_exercise_session', user, language, session_size)
            WITH recent_seen (user_exercise_history, 7-day window),
                 raw_senses (get_session_senses ★),
                 new_fallback (user_flashcards.state='new'),
                 senses_deduped (PARTITION BY sense_id, prefer due>learning>new),
                 ladder_picks (get_ladder_session ★, cap 5),
                 sense_candidates JOIN exercises (phase weight),
                 ranked_sense_picks (ROW_NUMBER per sense),
                 vocab_picks_capped (PARTITION BY bucket, 40/40/20),
                 supplementary_picks (word_sense_id IS NULL, tier window),
                 UNION ALL → priority DESC, RANDOM() → LIMIT
        → Append up to 3 virtual jumbled-sentence picks
          (Python: LanguageProcessor.split_sentences/tokenize)
        → Shuffle
    → cache to user_exercise_sessions → enrich for frontend
```

The Phase 9 RPC delegates to two existing RPCs internally — `get_session_senses` (Phase 7) for due/learning/new bucket assignment with FSRS decay, and `get_ladder_session` (Phase 8) for ladder picks. Family-aware ladder selection lives in one place.

## File Inventory (current)

| File | Purpose | Approx. lines |
|------|---------|--------------|
| `migrations/phase8_momentum_bands.sql` | Canonical: schema + 9 RPCs + new prompt | 1184 |
| `services/vocabulary_ladder/ladder_service.py` | Thin RPC wrapper + battery assembly | 345 |
| `services/vocabulary_ladder/config.py` | Levels, rings, gates, stress test, helpers | 448 |
| `services/vocabulary_ladder/asset_pipeline.py` | 3-prompt orchestrator | ~404 |
| `services/vocabulary_ladder/asset_generators/prompt1_core.py` | Gemini Flash: classification + 10 sentences | — |
| `services/vocabulary_ladder/asset_generators/prompt2_exercises.py` | Sonnet: L1/3/5/6 exercises (A/B variants) | — |
| `services/vocabulary_ladder/asset_generators/prompt3_transforms.py` | Sonnet: L4/7/8 exercises (A/B variants) | — |
| `services/vocabulary_ladder/validators.py` | Schema + linguistic + pedagogical validation | — |
| `services/vocabulary_ladder/exercise_renderer.py` | Frontend-ready formatting | — |
| `services/exercise_session_service.py` | Daily-session orchestrator (RPC call + virtual picks + cache + enrich) | ~500 |
| `migrations/phase9_get_exercise_session.sql` | `get_exercise_session` RPC + phase/tier helpers | ~280 |
| `services/exercise_generation/config.py` | PHASE_MAP, type registries | ~178 |
| `routes/vocab_dojo.py` | Six dojo endpoints | ~419 |

## Ladder Config: What's Defined ([services/vocabulary_ladder/config.py](../../services/vocabulary_ladder/config.py))

```python
LADDER_LEVELS = {
    1: {'name': 'Phonetic/Orthographic',  'exercise_type': 'phonetic_recognition',
        'prompt': 'prompt2', 'family': 'form_recognition',         'ring': 1},
    2: {'name': 'Definition Match',       'exercise_type': 'definition_match',
        'prompt': 'database', 'family': 'form_recognition',        'ring': 1},
    3: {'name': 'Cloze Completion',       'exercise_type': 'cloze_completion',
        'prompt': 'prompt2', 'family': 'meaning_recall',           'ring': 2},
    4: {'name': 'Morphology Slot',        'exercise_type': 'morphology_slot',
        'prompt': 'prompt3', 'family': 'form_production',          'ring': 2},
    5: {'name': 'Collocation Gap',        'exercise_type': 'collocation_gap_fill',
        'prompt': 'prompt2', 'family': 'collocation',              'ring': 2},
    6: {'name': 'Semantic Discrimination','exercise_type': 'semantic_discrimination',
        'prompt': 'prompt2', 'family': 'semantic_discrimination',  'ring': 3},
    7: {'name': 'Spot Incorrect',         'exercise_type': 'spot_incorrect_sentence',
        'prompt': 'prompt3', 'family': 'semantic_discrimination',  'ring': 3},
    8: {'name': 'Collocation Repair',     'exercise_type': 'collocation_repair',
        'prompt': 'prompt3', 'family': 'collocation',              'ring': 4},
    9: {'name': 'Jumbled Sentence',       'exercise_type': 'jumbled_sentence',
        'prompt': 'local', 'family': 'form_production',            'ring': 4},
}
```

Generation sources per level:
- **Prompt 2** (Claude Sonnet): L1, L3, L5, L6 — lexical/semantic
- **Prompt 3** (Claude Sonnet): L4, L7, L8 — grammar/structural
- **Database**: L2 — definition match from `dim_word_senses.definition` (no LLM)
- **Local**: L9 — backend jumbled-sentence tokenisation (no LLM)

BKT → starting level mapping (consumed by `init_ladder` only; runtime progression is family/ring-driven):
```python
BKT_TO_LEVEL = [(0.15, 1), (0.40, 3), (0.60, 5), (0.80, 7), (1.01, 9)]
```

## `ladder_record_attempt` — Attempt Processing Detail

[migrations/phase8_momentum_bands.sql:386-749](../../migrations/phase8_momentum_bands.sql#L386-L749)

```
ladder_record_attempt(user, sense, exercise, is_correct, is_first_attempt,
                       time_ms, language, exercise_type, level, exercise_context)
  │
  ├── 1. Resolve exercise metadata (type, level, language) from exercises
  │      if not provided. Compute family via ladder_get_family(level).
  │
  ├── 2. SELECT user_word_ladder ... FOR UPDATE (lock).
  │      If missing, derive active_levels from semantic_class:
  │        concrete_noun → [1,2,3,4,6,7,9]; else [1,2,3,4,5,6,7,8,9]
  │      INSERT default row (current_level=1, ring=1, state='new').
  │
  ├── 3. INSERT exercise_attempts (Phase 4 trigger syncs user_exercise_history).
  │
  ├── 4. Family BKT update on family_confidence (JSONB).
  │      Context-specific rates:
  │        standard:    learn=0.15 slip=0.12
  │        gate:        learn=0.18 slip=0.10
  │        stress_test: learn=0.20 slip=0.12
  │      Clamp [0.02, 0.98]. Recompute p_known_overall.
  │
  ├── 5. BRANCH:
  │   │
  │   ├── If word_state='mastered' AND NOT correct: LAPSE PATH
  │   │     - Extra 30% penalty on failed family
  │   │     - word_state='relearning', review_due_at=tomorrow
  │   │     - fsrs_schedule_review(..., p_rating=1)
  │   │     - UPDATE user_flashcards
  │   │
  │   └── ELSE: NORMAL PATH
  │         - Momentum band scheduling (low/medium/high → +1/+1/+2 days)
  │         - First-attempt failure overrides to tomorrow
  │         - required_families := ladder_ring_families(current_ring, active_levels)
  │         - min_conf_threshold := 0.50 (R1,R2) | 0.65 (R3) | 0.72 (R4)
  │         - ring_cleared := all required_families ≥ threshold
  │         - Ring transitions:
  │             R1 cleared → R2 (automatic)
  │             R2 cleared, !gate_a → v_gate_pending='gate_a'
  │             R3 cleared, !gate_b → v_gate_pending='gate_b'
  │         - Compute word_state:
  │             R4 + gate_b + ring_cleared + p_known≥0.88 → 'pre_mastery'
  │             gate_pending != null                       → 'gated'
  │             ring≤1, p_known<0.20                       → 'new'
  │             else                                       → 'active'
  │         - If word_state='pre_mastery', check stress_test_ready
  │           (every active family ≥ 0.72).
  │
  ├── 6. UPDATE user_word_ladder
  │      - family_confidence, current_ring, word_state, review_due_at
  │      - Phase 4 counters: total_attempts, first_try_success_count,
  │        first_try_failure_count, consecutive_failures,
  │        last_success_session_date (all written, none read)
  │      - last_exercised_family (used by consecutive_failures heuristic)
  │
  ├── 7. UPSERT user_vocabulary_knowledge via bkt_update_exercise.
  │      If is_lapse: bkt_apply_lapse_penalty.
  │
  └── 8. RETURN jsonb:
        is_correct, family, family_confidence, p_known_overall,
        current_ring, word_state, review_due_at, requeue,
        gate_pending, stress_test_ready, bkt_p_known, is_lapse
```

### Phase 4 counter columns — now mostly wired in (Phase 10, 2026-05-12)

After Phase 10, the read-side of these columns looks like:

| Column | Read by Phase 10? | Effect |
|---|---|---|
| `consecutive_failures` | ✅ | Computed pre-UPDATE into `v_new_consecutive_failures`; demotion fires when ≥ 3 on a ring-gating family |
| `last_exercised_family` | ✅ | Already used by the per-family `consecutive_failures` heuristic |
| `family_success_dates` *(new Phase 10)* | ✅ | Drives cross-session advancement gate (≥ 2 distinct dates per required family) |
| `last_success_session_date` | ❌ | Still written, never read. Redundant with `family_success_dates` |
| `first_try_success_count` | ❌ | Still written, never read |
| `first_try_failure_count` | ❌ | Still written, never read |
| `total_attempts` | ❌ | Still written, never read. Pure observability |

The remaining unread columns (`last_success_session_date`, `first_try_success_count`, `first_try_failure_count`, `total_attempts`) are flagged as open_question on the prose page; candidates for removal in a future schema cleanup.

## `ladder_pass_gate` — Gate Pass

[phase8_momentum_bands.sql:761-822](../../migrations/phase8_momentum_bands.sql#L761-L822)

```
ladder_pass_gate(user, sense, gate_name)
  → SELECT ... FOR UPDATE
  → gates_passed[gate_name] = true
  → new_ring = 3 (gate_a) | 4 (gate_b)
  → word_state: if new_ring≥4 AND gate_b AND p_known≥0.88 → 'pre_mastery' else 'active'
  → review_due_at = tomorrow
  → RETURN: gate, passed=true, new_ring, word_state, p_known_overall
```

Gate **failure** is not a separate RPC. Python calls `ladder_record_attempt` for each failed battery exercise with `exercise_context = 'gate'`. The route then returns `{passed: false, word_state: 'active'}` shape ([routes/vocab_dojo.py:278-280](../../routes/vocab_dojo.py#L278-L280)).

## `ladder_graduate` — Stress Test Pass

[phase8_momentum_bands.sql:836-933](../../migrations/phase8_momentum_bands.sql#L836-L933)

```
ladder_graduate(user, sense, stress_test_score, language)
  → SELECT ... FOR UPDATE
  → p_known := ladder_compute_p_known(family_confidence)
  → stress_bonus := 1.0 (≥0.90) | 0.5 (≥0.80) | 0.0 (else)
  → stability   := clamp(7 + 21·p_known + 6·stress_bonus, 7, 34)
  → family_stddev over the 5 active families
  → variance_penalty := min(1.5, stddev·4)
  → difficulty  := clamp(8 − 5·p_known + variance_penalty, 2, 8.5)
  → due_date    := today + round(0.6·stability)
  → UPDATE user_word_ladder
        word_state='mastered', stress_test_score=score, review_due_at=NULL
  → UPSERT user_flashcards (state='review', reps≥1, lapses=0)
  → RETURN: word_state, stress_test_score, fsrs_stability, fsrs_difficulty,
            fsrs_due_date, p_known_overall
```

## `get_ladder_session` — Session Builder

[phase8_momentum_bands.sql:1005-1184](../../migrations/phase8_momentum_bands.sql#L1005-L1184)

Returns a `TABLE` with 15 `out_*` columns. CTE pipeline:

| CTE | Purpose |
|-----|---------|
| `candidates` | `user_word_ladder` rows with active state and `review_due_at <= now()`, joined to a row in `exercises` with a ladder level. Computes overdue/weakness/gate/novelty/relapse subscores. |
| `scored` | Adds `priority = 0.35·overdue + 0.25·weakness + 0.20·gate + 0.10·novelty + 0.10·relapse` and `target_family` (weakest in current ring). |
| `top_words` | Top `p_count` words by priority. |
| `seen_today` | DISTINCT `exercise_id` from `user_exercise_history` for today's `session_date`. |
| `word_exercises` | Joins `exercises` for each top word, `ROW_NUMBER() OVER (PARTITION BY sense_id ORDER BY target-family-match, seen-today, variant-alternation, random())`. |
| `selected` | `rn = 1`. |
| Final SELECT | Joins `dim_word_senses` + `dim_vocabulary` for lemma/definition/pronunciation. |

Variant alternation logic ([phase8_momentum_bands.sql:1142-1148](../../migrations/phase8_momentum_bands.sql#L1142-L1148)): prefer the variant *not* equal to the most recent exercise the user did for this sense. (The SQL compares variant strings against an exercise-id-cast-to-text via a correlated subquery — a subtle code smell, but functionally correct in tests because `'A' != 'some-uuid'` always.)

## Daily Session: `get_exercise_session` RPC (Phase 9)

[migrations/phase9_get_exercise_session.sql](../../migrations/phase9_get_exercise_session.sql)

```sql
get_exercise_session(p_user_id uuid, p_language_id smallint, p_session_size int DEFAULT 20)
RETURNS TABLE(
    out_exercise_id     uuid,
    out_sense_id        integer,
    out_exercise_type   text,
    out_content         jsonb,
    out_complexity_tier text,
    out_phase           text,        -- 'A'|'B'|'C'|'D'
    out_slot_type       text,        -- 'due_review'|'active_learning'|'new_word'|'ladder'|'supplementary'
    out_priority        numeric
)
```

CTE pipeline:

| # | CTE | Source / Rule |
|---|-----|---------------|
| 1 | `recent_seen` | `user_exercise_history` WHERE `session_date >= today − 7 days` — indexed anti-repetition (replaces the legacy 500-row scan of `exercise_attempts`) |
| 2 | `raw_senses` | `get_session_senses(user, lang, due*3, learning*3, new*3)` — Phase 7 RPC, applies BKT decay + bucket assignment |
| 3 | `new_fallback` | `user_flashcards.state='new'` for senses not in `raw_senses` (top-up if Phase 7 returns < `new_slots`) |
| 4 | `senses_deduped` | `ROW_NUMBER() OVER (PARTITION BY sense_id ORDER BY due>learning>new)`, keep `rn=1` |
| 5 | `ladder_picks` | `get_ladder_session(user, lang, LEAST(5, session_size))` — Phase 8 RPC; priority bumped + 1.0 |
| 6 | `sense_candidates` | JOIN `exercises` per sense; `exercise_type_phase_weight(type, phase)` per row; exclude `recent_seen` + ladder picks |
| 7 | `ranked_sense_picks` | `ROW_NUMBER() OVER (PARTITION BY sense_id ORDER BY type_weight DESC, RANDOM())` |
| 8 | `vocab_picks_capped` | Of `rn=1`s, `ROW_NUMBER() OVER (PARTITION BY bucket ORDER BY type_weight DESC, RANDOM())` |
| 9 | `vocab_picks` | Keep per-bucket `bucket_rn ≤ slot_allocation`; map bucket → slot_type; compute `priority` from bucket anchor + 0.1 × type_weight |
| 10 | `supplementary_picks` | `exercises WHERE word_sense_id IS NULL AND complexity_tier = ANY(tier_window_for_p_known(avg(p_known)))`; cap = `session_size − ladder_picks − vocab_picks` |
| 11 | Final SELECT | UNION ALL → `ORDER BY priority DESC, RANDOM() LIMIT session_size` |

`exercise_type_phase_weight(exercise_type, phase)`: mirrors the Python `_get_eligible_types_weighted` rule — A: 100% A; B: 70% B + 30% A; C: 70% C + 30% B; D: 70% D + 30% C. Any-type fallback gets weight 0.001 so it can still be picked if nothing else is available.

`tier_window_for_p_known(avg)`: returns the same `[T1,T2]` / `[T2,T3]` / … windows as the Python `_get_supplementary_exercises`.

Slot distribution (40/40/20):
- `due_slots := ROUND(session_size * 0.40)` (8 for size=20)
- `learning_slots := ROUND(session_size * 0.40)` (8 for size=20)
- `new_slots := session_size − due − learning` (4 for size=20)
- Ladder cap: `LEAST(5, session_size)`
- Supplementary fills the gap to `session_size`.

### Python wrapper (`ExerciseSessionService._compute_session`)

```python
# services/exercise_session_service.py
resp = self.db.rpc('get_exercise_session', {
    'p_user_id': user_id,
    'p_language_id': language_id,
    'p_session_size': session_size,
}).execute()
picks = [{...} for row in (resp.data or [])]
# Append up to 3 virtual jumbled sentences (language-specific tokenisation)
picks += [...]
random.shuffle(picks)
return picks
```

The Python service now contains zero scheduling logic. The four old helpers (`_select_exercises_for_senses`, `_get_supplementary_exercises`, `_get_ladder_exercises`, `_get_recent_exercise_ids`) were deleted along with the module-level phase-weighting helpers.

### Virtual jumbled sentences (still Python)

Bucket 6 is the one piece that stays in Python because it depends on `LanguageProcessor.split_sentences()` / `tokenize()` — jieba for Chinese, etc. After the RPC returns, `_compute_session` appends up to 3 virtual picks with `exercise_id = f"virtual-jumbled-{uuid4()}"`. The frontend identifies them by the `virtual-` prefix and `is_virtual: true` flag; the `/api/exercises/attempt` route short-circuits them with no DB write.

## Schema: `user_word_ladder` (post-Phase-8)

```sql
-- Phase 1/2 columns
user_id                    uuid NOT NULL REFERENCES users(id),
sense_id                   integer NOT NULL REFERENCES dim_word_senses(id),
current_level              integer NOT NULL DEFAULT 1 CHECK (current_level BETWEEN 1 AND 9),
active_levels              integer[] NOT NULL DEFAULT '{1,2,3,4,5,6,7,8,9}',
updated_at                 timestamptz NOT NULL DEFAULT now(),

-- Phase 4 columns (written by Phase 8 RPC, never read for progression)
first_try_success_count    integer NOT NULL DEFAULT 0,
first_try_failure_count    integer NOT NULL DEFAULT 0,
consecutive_failures       integer NOT NULL DEFAULT 0,
total_attempts             integer NOT NULL DEFAULT 0,
word_state                 text NOT NULL DEFAULT 'active',  -- CHECK rewritten in Phase 8
last_success_session_date  date,
review_due_at              timestamptz,

-- Phase 8 columns (canonical progression state)
family_confidence          jsonb NOT NULL DEFAULT
                           '{"form_recognition":0.10,"meaning_recall":0.10,
                              "form_production":0.10,"collocation":0.10,
                              "semantic_discrimination":0.10,"contextual_use":0.10}',
gates_passed               jsonb NOT NULL DEFAULT '{"gate_a":false,"gate_b":false}',
current_ring               integer NOT NULL DEFAULT 1 CHECK (current_ring BETWEEN 1 AND 4),
stress_test_score          real,
last_exercised_family      text,

PRIMARY KEY (user_id, sense_id)

-- Phase 8 CHECK constraint:
CHECK (word_state IN ('new','active','gated','pre_mastery','relearning','mastered'))

-- Indexes:
idx_user_word_ladder_user        (user_id)
idx_user_word_ladder_review_due  (user_id, review_due_at) WHERE review_due_at IS NOT NULL
idx_user_word_ladder_state       (user_id, word_state)
idx_user_word_ladder_ring        (user_id, current_ring)
```

The Phase 4 word_state values `'fragile'` and `'stable'` were data-migrated to `'active'` and the constraint replaced ([phase8_momentum_bands.sql:61-68](../../migrations/phase8_momentum_bands.sql#L61-L68)).

## Schema: Related

`exercises` ladder columns:
```
ladder_level    integer CHECK (ladder_level BETWEEN 1 AND 9 OR ladder_level IS NULL)
word_sense_id   integer REFERENCES dim_word_senses(id)
word_asset_id   bigint  REFERENCES word_assets(id)
tags            jsonb  -- includes {"variant": "A" | "B"} for variant exercises
```

`user_exercise_history` (Phase 4 anti-repetition table; populated by trigger from `exercise_attempts`):
```sql
id, user_id, language_id, exercise_id, sense_id, exercise_type,
is_correct, is_first_attempt, session_date, created_at
```
Indexed for the anti-repetition query: `(user_id, language_id, session_date, exercise_id)`.

`user_exercise_sessions` (daily session cache, Path B only):
```sql
user_id, language_id, load_date, exercise_ids jsonb, completed_ids jsonb, session_size
PRIMARY KEY (user_id, language_id)
```

## Improvements — Implementation Status

| Item | Status | Notes |
|------|--------|-------|
| Promotion counter schema (Phase 4 columns) | ✅ Added to schema | Written every attempt; never read for progression |
| Family-BKT × rings × gates × stress test (Phase 8) | ✅ Live | Canonical implementation in `phase8_momentum_bands.sql` |
| FSRS handoff on graduation | ✅ Live | `ladder_graduate` seeds stability/difficulty/due_date |
| FSRS-4.5 ported to SQL | ✅ Live | `fsrs_schedule_review` (used on lapse path) |
| A/B exercise variants | ✅ Live | `word_assets.asset_type` CHECK expanded; session builder alternates via `exercises.tags->>'variant'` |
| `user_exercise_history` anti-repetition table | ✅ Live | Trigger-populated; consumed by `get_ladder_session.seen_today` |
| Daily-session N+1 fix | ✅ Live (Phase 9) | Folded into the new RPC: one JOIN over candidate senses replaces ~40 per-sense queries |
| Daily-session bucket-5 → `get_ladder_session` delegation | ✅ Live (Phase 9) | `get_exercise_session` calls `get_ladder_session` internally with `LEAST(5, session_size)` |
| Daily-session → single SQL `get_exercise_session` RPC | ✅ Live (Phase 9) | [migrations/phase9_get_exercise_session.sql](../../migrations/phase9_get_exercise_session.sql) |
| Cross-session promotion gating | ✅ Live (Phase 10) | New `family_success_dates` JSONB; ring clears only if every required family has ≥ 2 distinct success dates |
| Ring demotion on consecutive_failures | ✅ Live (Phase 10) | Triggered when consecutive_failures ≥ 3 on a ring-gating family; resets only the exit gate of the dropped-into ring |
| L10 Capstone Production | Not done | `contextual_use` family weighted but no exercise type; caps overall p_known at ≈0.92 |
| IRT calibration | ✅ Live (Phase 11) | Nightly 2PL fit from `user_exercise_history` (first-attempts only) into `irt_difficulty` / `irt_discrimination`. `get_exercise_session` weights candidate items by `exp(-0.5 · ((b − θ_user)/σ)²)` with σ=1.0 once `irt_n_attempts ≥ 20`; otherwise falls back to flat weight so new content still surfaces. Runner: [services/irt/calibrator.py](../../services/irt/calibrator.py). |

## Asset Pipeline (unchanged shape, Phase 8 tweaks)

Pipeline shape per [[features/exercises.tech]]. Phase 8 changes:
- **Prompt 1 v2** (`vocab_prompt1_core`, language_id=2): generates **10 sentences** (was 6) so A/B variants can pick from disjoint pools. Other prompt templates unchanged.
- **A/B variants:** `word_assets.asset_type` accepts `prompt2_exercises_A`, `prompt2_exercises_B`, `prompt3_transforms_A`, `prompt3_transforms_B`. Variant A consumes sentence indices 0–5; Variant B consumes 6–9 with selective reuse. Variant is stored on each generated `exercises.tags->>'variant'`.

Sentence-to-level assignment (variant A vs B; for asset generators):
```
A: L3=0  L4=1  L5=2  L6=3  L7=4 (correct 0,1,2)  L8=4  L9=5
B: L3=6  L4=7  L5=8  L6=9  L7=0 (correct 6,7,9)  L8=8  L9=3
```

## Related Pages

- [[algorithms/ladder-implementation-analysis]] — Prose analysis
- [[algorithms/vocabulary-ladder.tech]] — Current ladder spec (Momentum Bands)
- [[features/exercises.tech]] — Exercise table schema
- [[features/vocab-dojo.tech]] — Session builder + endpoints
- [[features/flashcards.tech]] — FSRS source for `fsrs_schedule_review`
- [[algorithms/bkt-implementation-analysis.tech]] — BKT analysis (overall p_known)
- [[database/schema.tech]] — Full table DDL
- [[database/rpcs.tech]] — Full RPC definitions
- [[decisions/ADR-005-momentum-bands]] — Decision record
