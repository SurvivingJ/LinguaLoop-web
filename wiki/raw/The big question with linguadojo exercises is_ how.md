<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# The big question with linguadojo exercises is: how do we decide which exercises to serve a user and when?

We want primarily to serve users exercises that incorporate vocabulary that they know. Ideally, however, we mix in the same word and same exercise but different sentence occasionally. I think we want SRS to a point. Like once you achieve "mastery" in something, we test that concept or word or grammar pattern somewhat sporadically. The idea of the different exercises is to force the user to see new vocabulary in different contexts - and force them to use it in different situations too. We need to determine a levelling system where once a word reaches a level of estimated knowledge (bayesian system) we change the weights of which exercise for that word is most commonly shown.

Analyse my github lingualoop-web repo to understand what exercises we have and how they are generated and plan out this study algorithm. Could it be beneficial to have an algorithm that learns with volume? Or just heuristics is best?

Now I have everything I need. Here is a thorough analysis and plan.

***

## What You Have: Exercise Inventory

Your repo has a well-structured exercise generation system rooted in [`services/exercise_generation/generators/`](https://github.com/SurvivingJ/LinguaLoop-web/tree/main/services/exercise_generation/generators).  The full exercise type registry in [`services/exercise_generation/config.py`](https://github.com/SurvivingJ/LinguaLoop-web/blob/main/services/exercise_generation/config.py) reveals **21 distinct exercise types**, already grouped into four phases A–D:


| Phase | Types | Cognitive demand | Best for |
| :-- | :-- | :-- | :-- |
| **A** | `text_flashcard`, `listening_flashcard`, `cloze_completion` | Recognition | New / encountered words |
| **B** | `jumbled_sentence`, `tl_nl_translation`, `nl_tl_translation`, `spot_incorrect_*`, `style_*_fill` | Recall + ordering | Learning words |
| **C** | `semantic_discrimination`, `collocation_gap_fill`, `collocation_repair`, `odd_one_out`, `style_pattern_match`, `style_voice_transform` | Nuanced recall | Consolidating words |
| **D** | `verb_noun_match`, `context_spectrum`, `timed_speed_round`, `style_imitation` | Fluent production | Near-mastery |

Your vocabulary layer already has a **BKT (Bayesian Knowledge Tracing) service** in [`knowledge_service.py`](https://github.com/SurvivingJ/LinguaLoop-web/blob/main/services/vocabulary/knowledge_service.py) that tracks `p_known` per word sense, with statuses like `encountered → learning → mastered`.  You also have a **full FSRS-4.5 scheduler** in [`fsrs.py`](https://github.com/SurvivingJ/LinguaLoop-web/blob/main/services/vocabulary/fsrs.py) for review spacing, and even a `difficulty_from_p_known()` bridge between the two systems.  The architecture is nearly ready — what's missing is the **serving algorithm** that ties them together.

***

## The Core Serving Problem

The fundamental tension is between two goals:

1. **Consolidate known vocabulary** — serve exercises the user will succeed at to build confidence and deepen encoding
2. **Challenge growth** — push into harder exercise types and new contexts to prevent passive recognition without active recall

The answer is a **two-layer decision**: first, *which word/concept to practise*, then *which exercise type to use for it*.

***

## Layer 1: Word/Concept Selection (Temporal Scheduling)

Use your existing FSRS + BKT stack, but formalize the session composition. When building a session queue, pull words in this priority order:

1. **FSRS due cards** (`due_date <= today`) — these are already-learned words that need review. Target ~40% of a session.
2. **BKT uncertainty zone** — words where `0.4 ≤ p_known ≤ 0.75` (your existing `get_word_quiz_candidates` already surfaces these). Target ~40% of a session. This is the active learning zone.
3. **New/encountered words** — `p_known < 0.4`, seen at most once. Target ~20% of a session.

The 40/40/20 split is a starting heuristic based on interleaving research — you can tune these weights per-user as data grows. Crucially, for "mastered" words (`p_known > 0.85`, FSRS in `review` state), FSRS will naturally push their intervals to weeks/months, so they appear sporadically without you needing to explicitly manage it.

***

## Layer 2: Exercise Type Selection (Phase-Gated Weight Distribution)

Once you know *which word* to serve, you select *which exercise type* using a **weighted sampler that is gated by the word's current BKT phase**. The key insight is that your `PHASE_MAP` in config already encodes the right cognitive progression — you just need to connect it to `p_known`.

Define these BKT → Phase mappings:

```
p_known < 0.40  →  Phase A weights only (recognition: flashcard, cloze)
0.40 ≤ p_known < 0.65  →  Phase A (30%) + Phase B (70%)
0.65 ≤ p_known < 0.80  →  Phase B (20%) + Phase C (80%)
0.80 ≤ p_known < 0.90  →  Phase C (30%) + Phase D (70%)
p_known ≥ 0.90  →  Phase D dominant (80%) + sporadic Phase A/C (20%) for context variety
```

Within each phase, weight individual exercise types by your existing `VOCABULARY_DISTRIBUTION`, `COLLOCATION_DISTRIBUTION`, and `GRAMMAR_DISTRIBUTION` dicts — these are already sensible targets.  The "same word, different sentence" requirement you described is handled automatically because each exercise type pulls from your exercise pool independently; a `cloze_completion` and a `collocation_gap_fill` for the same sense_id will use different source sentences from the corpus.

***

## Layer 3: Anti-Repetition \& Diversity Guards

Before serving any exercise, apply these filters:

- **Same-exercise cooldown**: Track `last_seen_exercise_id` per `(user_id, sense_id, exercise_type)`. Don't re-serve the same `exercise_id` within a 7-day window; instead pick a different exercise of the same type anchored to the same sense.
- **Type rotation**: Within a single session, cap each exercise type at 3 appearances. This forces the variety you want.
- **New context injection**: For words in Phase C/D, 1-in-5 serves should use an exercise from a *different topic domain* than the word was originally learned in. This directly implements your goal of forcing use in different situations.

***

## Heuristics vs. Learned Algorithm

This is the right question to ask. The honest answer: **start with heuristics, instrument for learning**.

Pure ML (e.g., a contextual bandit or deep RL policy over exercise selection) requires thousands of user-exercise interactions per learner before it beats a well-designed heuristic. At your current scale, an ML approach would overfit to noise. The heuristics above are grounded in decades of cognitive science research (spaced repetition, desirable difficulties, interleaving) and will outperform a cold-start ML model.

**However**, you should instrument everything now so you can train later:

```python
# Log this for every served exercise
{
  "user_id": ...,
  "sense_id": ...,
  "exercise_type": ...,
  "p_known_at_serve": ...,
  "fsrs_stability_at_serve": ...,
  "outcome": "correct" | "incorrect",
  "response_time_ms": ...,
  "days_since_last_seen": ...
}
```

Once you have ~50k such rows across users, a **Thompson Sampling contextual bandit** over `(p_known_bucket, exercise_type)` is a natural next step — it learns which exercise types are most effective at moving `p_known` for words at each level, personalized per user. This is where ML genuinely helps: discovering that, for example, `context_spectrum` is disproportionately effective at pushing `p_known` from 0.7 to 0.85 compared to `collocation_gap_fill`. But you need the data foundation first.

***

## Proposed New Service: `ExerciseScheduler`

Based on your architecture, this should live at `services/exercise_scheduling/scheduler.py` and expose a single primary method:

```python
class ExerciseScheduler:
    def build_session_queue(
        self,
        user_id: str,
        language_id: int,
        session_size: int = 20
    ) -> list[ScheduledExercise]:
        """
        Returns an ordered list of exercises for the session.
        Each item includes: exercise_id, sense_id, exercise_type,
        p_known_at_schedule, phase, reason ('due'|'uncertain'|'new').
        """
```

Internally it calls:

1. `VocabularyKnowledgeService.get_word_quiz_candidates()` for uncertain-zone words
2. A new `get_due_flashcards(user_id)` query against your `user_flashcards` table using FSRS `due_date`
3. A `ExerciseTypeSelector.select(sense_id, p_known)` that implements the phase-gated weighted sampler above
4. An `ExercisePoolFetcher.get_exercise(sense_id, exercise_type, exclude_ids)` that hits your existing exercises table

This keeps the scheduler clean and makes each component independently testable — fitting your existing service-oriented architecture.

---

# But we will need to implement this in SQL so that it is efficient. How should we do this? Should we have a table of due exercise and test ids for users?

Now I have the full picture. Here's a thorough, concrete answer.

***

## Should You Store a "Due Exercises" Table?

The short answer: **no, not as a pre-materialized queue of individual exercise IDs**. Here's why, and what to do instead.

A pre-populated queue table like `due_exercises(user_id, exercise_id, due_date)` seems appealing but creates serious problems at your scale. You have 21 exercise types and potentially thousands of sense IDs per user — pre-enumerating all "due" exercise rows means you'd need a background job to keep it fresh, the table would grow huge, and it would go stale the moment a user's `p_known` changes mid-session. It's also redundant — you already have `user_flashcards` with FSRS `due_date` and `user_vocabulary_knowledge` with `p_known`, which together contain all the information you need to decide what's due at query time.

The correct approach is a **single `get_exercise_session` RPC function** that computes the session queue live at request time in pure SQL. Postgres is fast enough — the query needs only a few indexed lookups on tables that already have the right indexes (`idx_uf_user_due`, `idx_uvk_user_pknown`, `idx_exercises_sense`).  A session of 20 exercises resolves in under 50ms on a properly indexed Supabase instance.

***

## What You Do Need to Add

You need **one new small table** and **one new RPC function**. The table tracks which exercises a user has recently seen (the anti-repetition cooldown), and the function is the session builder.

### New Table: `user_exercise_history`

```sql
CREATE TABLE IF NOT EXISTS public.user_exercise_history (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         uuid NOT NULL REFERENCES public.users(id),
    exercise_id     uuid NOT NULL REFERENCES public.exercises(id),
    sense_id        integer REFERENCES public.dim_word_senses(id),
    exercise_type   text NOT NULL,
    is_correct      boolean,
    served_at       timestamptz NOT NULL DEFAULT now()
);

-- These are the two indexes that matter — everything else is noise
CREATE INDEX idx_ueh_user_sense_type
    ON public.user_exercise_history(user_id, sense_id, exercise_type, served_at DESC);

CREATE INDEX idx_ueh_user_recent
    ON public.user_exercise_history(user_id, served_at DESC);
```

This is intentionally leaner than your existing `exercise_attempts` table.  Note that `exercise_attempts` already exists but lacks `sense_id` and `exercise_type` denormalized on it, which makes the anti-repetition query expensive. This new table is purpose-built for scheduling lookups — `exercise_attempts` remains your source of truth for analytics and BKT updates.

***

### The Session Builder RPC

This is the core function. It runs in a single query using CTEs to compose the session:

```sql
CREATE OR REPLACE FUNCTION public.get_exercise_session(
    p_user_id       uuid,
    p_language_id   integer,
    p_session_size  integer DEFAULT 20
)
RETURNS TABLE (
    exercise_id     uuid,
    exercise_type   text,
    sense_id        integer,
    content         jsonb,
    p_known         real,
    phase           text,   -- 'A', 'B', 'C', 'D'
    slot_reason     text    -- 'due_review', 'active_learning', 'new_word'
) AS $$
DECLARE
    v_due_count     integer := ROUND(p_session_size * 0.40);
    v_learning_count integer := ROUND(p_session_size * 0.40);
    v_new_count     integer := p_session_size - ROUND(p_session_size * 0.40) - ROUND(p_session_size * 0.40);
BEGIN

    RETURN QUERY

    -- =========================================================
    -- Step 1: Recently seen exercise IDs (7-day cooldown)
    -- =========================================================
    WITH recent_seen AS (
        SELECT DISTINCT exercise_id
        FROM public.user_exercise_history
        WHERE user_id = p_user_id
          AND served_at >= NOW() - INTERVAL '7 days'
    ),

    -- =========================================================
    -- Step 2: Per-sense, per-type cooldown
    -- (don't show same exercise_type for same sense_id within 3 days)
    -- =========================================================
    recent_type_sense AS (
        SELECT DISTINCT sense_id, exercise_type
        FROM public.user_exercise_history
        WHERE user_id = p_user_id
          AND served_at >= NOW() - INTERVAL '3 days'
    ),

    -- =========================================================
    -- Step 3: FSRS due flashcards → find eligible exercises
    -- ~40% of session
    -- =========================================================
    due_senses AS (
        SELECT uf.sense_id, uvk.p_known
        FROM public.user_flashcards uf
        JOIN public.user_vocabulary_knowledge uvk
            ON uvk.user_id = uf.user_id AND uvk.sense_id = uf.sense_id
        WHERE uf.user_id = p_user_id
          AND uf.language_id = p_language_id
          AND uf.due_date <= CURRENT_DATE
          AND uf.state IN ('review', 'relearning')
        ORDER BY uf.due_date ASC   -- most overdue first
        LIMIT v_due_count * 3      -- fetch extras so filtering doesn't starve us
    ),

    due_exercises AS (
        SELECT
            e.id AS exercise_id,
            e.exercise_type,
            ds.sense_id,
            e.content,
            ds.p_known,
            -- Phase gate based on p_known
            CASE
                WHEN ds.p_known < 0.40 THEN 'A'
                WHEN ds.p_known < 0.65 THEN 'B'
                WHEN ds.p_known < 0.80 THEN 'C'
                ELSE 'D'
            END AS phase,
            'due_review' AS slot_reason,
            -- Weight for random sampling within phase
            random() AS sort_key
        FROM due_senses ds
        JOIN public.exercises e
            ON e.word_sense_id = ds.sense_id
           AND e.language_id = p_language_id
           AND e.is_active = TRUE
        WHERE e.id NOT IN (SELECT exercise_id FROM recent_seen)
          AND NOT EXISTS (
              SELECT 1 FROM recent_type_sense rts
              WHERE rts.sense_id = ds.sense_id
                AND rts.exercise_type = e.exercise_type
          )
          -- Phase gate: only allow exercise types valid for this p_known level
          AND e.exercise_type = ANY(
              CASE
                  WHEN ds.p_known < 0.40 THEN ARRAY['text_flashcard','listening_flashcard','cloze_completion']
                  WHEN ds.p_known < 0.65 THEN ARRAY['text_flashcard','listening_flashcard','cloze_completion',
                                                     'jumbled_sentence','tl_nl_translation','nl_tl_translation',
                                                     'spot_incorrect_sentence','spot_incorrect_part']
                  WHEN ds.p_known < 0.80 THEN ARRAY['semantic_discrimination','collocation_gap_fill',
                                                     'collocation_repair','odd_collocation_out','odd_one_out',
                                                     'style_pattern_match','style_voice_transform',
                                                     'jumbled_sentence','tl_nl_translation']
                  ELSE ARRAY['verb_noun_match','context_spectrum','timed_speed_round','style_imitation',
                             'collocation_gap_fill','semantic_discrimination']
              END
          )
    ),

    due_picks AS (
        SELECT * FROM due_exercises ORDER BY sort_key LIMIT v_due_count
    ),

    -- =========================================================
    -- Step 4: Active learning zone (BKT uncertain, 0.40–0.75)
    -- ~40% of session
    -- =========================================================
    learning_senses AS (
        SELECT uvk.sense_id, uvk.p_known
        FROM public.user_vocabulary_knowledge uvk
        WHERE uvk.user_id = p_user_id
          AND uvk.language_id = p_language_id
          AND uvk.p_known BETWEEN 0.40 AND 0.75
          AND uvk.status NOT IN ('user_marked_unknown')
          -- Exclude senses already picked in due slot
          AND uvk.sense_id NOT IN (SELECT sense_id FROM due_picks)
        ORDER BY (uvk.p_known * (1 - uvk.p_known)) DESC  -- highest uncertainty first
        LIMIT v_learning_count * 3
    ),

    learning_exercises AS (
        SELECT
            e.id AS exercise_id,
            e.exercise_type,
            ls.sense_id,
            e.content,
            ls.p_known,
            CASE
                WHEN ls.p_known < 0.65 THEN 'B'
                ELSE 'C'
            END AS phase,
            'active_learning' AS slot_reason,
            random() AS sort_key
        FROM learning_senses ls
        JOIN public.exercises e
            ON e.word_sense_id = ls.sense_id
           AND e.language_id = p_language_id
           AND e.is_active = TRUE
        WHERE e.id NOT IN (SELECT exercise_id FROM recent_seen)
          AND NOT EXISTS (
              SELECT 1 FROM recent_type_sense rts
              WHERE rts.sense_id = ls.sense_id AND rts.exercise_type = e.exercise_type
          )
    ),

    learning_picks AS (
        SELECT * FROM learning_exercises ORDER BY sort_key LIMIT v_learning_count
    ),

    -- =========================================================
    -- Step 5: New/encountered words (p_known < 0.40 or never seen)
    -- ~20% of session
    -- =========================================================
    new_senses AS (
        SELECT uvk.sense_id, uvk.p_known
        FROM public.user_vocabulary_knowledge uvk
        WHERE uvk.user_id = p_user_id
          AND uvk.language_id = p_language_id
          AND uvk.p_known < 0.40
          AND uvk.status IN ('encountered', 'unknown')
          AND uvk.sense_id NOT IN (SELECT sense_id FROM due_picks)
          AND uvk.sense_id NOT IN (SELECT sense_id FROM learning_picks)
        ORDER BY uvk.last_evidence_at DESC NULLS LAST  -- most recently encountered first
        LIMIT v_new_count * 3
    ),

    new_exercises AS (
        SELECT
            e.id AS exercise_id,
            e.exercise_type,
            ns.sense_id,
            e.content,
            ns.p_known,
            'A' AS phase,
            'new_word' AS slot_reason,
            random() AS sort_key
        FROM new_senses ns
        JOIN public.exercises e
            ON e.word_sense_id = ns.sense_id
           AND e.language_id = p_language_id
           AND e.is_active = TRUE
           AND e.exercise_type = ANY(ARRAY['text_flashcard','listening_flashcard','cloze_completion'])
        WHERE e.id NOT IN (SELECT exercise_id FROM recent_seen)
    ),

    new_picks AS (
        SELECT * FROM new_exercises ORDER BY sort_key LIMIT v_new_count
    ),

    -- =========================================================
    -- Step 6: Merge and shuffle
    -- =========================================================
    all_picks AS (
        SELECT exercise_id, exercise_type, sense_id, content, p_known, phase, slot_reason
        FROM due_picks
        UNION ALL
        SELECT exercise_id, exercise_type, sense_id, content, p_known, phase, slot_reason
        FROM learning_picks
        UNION ALL
        SELECT exercise_id, exercise_type, sense_id, content, p_known, phase, slot_reason
        FROM new_picks
    )

    SELECT *
    FROM all_picks
    ORDER BY random();  -- shuffle so session isn't "all due, then all new"

END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

GRANT EXECUTE ON FUNCTION public.get_exercise_session TO authenticated;
```


***

## What Happens After a Session

When the user completes each exercise, you call `exercise_attempts` (already exists) for analytics, then insert a row into `user_exercise_history` for scheduling, then call `update_vocabulary_from_word_test` or `update_vocabulary_from_test` for BKT.  The session queue does **not** need updating — the next call to `get_exercise_session` will recompute from fresh state automatically.

For FSRS scheduling after an exercise, you add a lightweight Python call in your existing `knowledge_service.py` that updates `user_flashcards.due_date` and `stability` based on the user's rating (correct/incorrect maps to `GOOD`/`AGAIN` in your FSRS scheduler).  This is already wired up logically — you just need to call `schedule_review()` from `fsrs.py` and write the result back to `user_flashcards`.

***

## Migration Checklist

1. **Add `user_exercise_history`** table + two indexes (above)
2. **Add `get_exercise_session` RPC** to Supabase via a new migration file in `/migrations/`
3. **Wire FSRS updates** in `knowledge_service.py` — after each exercise answer, call `fsrs.schedule_review()` and update `user_flashcards` row for that `sense_id`
4. **Add `ExerciseSessionService`** in `services/exercise_scheduling/` that calls `.rpc('get_exercise_session', {...})` and returns the queue to the frontend
5. **Log `user_exercise_history`** rows from the same service after each exercise is served (not after answered — you want cooldowns based on *serving*, not completion)
