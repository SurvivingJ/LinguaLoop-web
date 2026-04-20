---
title: Vocab Dojo — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./vocab-dojo.md
last_updated: 2026-04-10
dependencies:
  - "services/vocabulary_ladder/"
  - "services/exercise_session_service.py"
  - "user_vocabulary_knowledge table"
  - "user_flashcards table"
  - "exercises table"
  - "user_exercise_history table (new)"
breaking_change_risk: medium
---

# Vocab Dojo — Technical Specification

## Architecture Overview

```
User hits "Play" on Vocab Dojo
  → GET /api/vocab-dojo/session
    → Supabase RPC: get_exercise_session(user_id, language_id, session_size)
      → CTE pipeline: due_senses → learning_senses → new_senses → exercise matching → shuffle
    → Return ordered exercise queue as JSON

User completes exercise
  → POST /api/vocab-dojo/submit
    → Insert user_exercise_history row (for anti-repetition)
    → Update BKT via bkt_update()
    → Update FSRS via schedule_review()
    → Update vocabulary ladder position via progression engine
```

## New Table: user_exercise_history

```sql
CREATE TABLE IF NOT EXISTS public.user_exercise_history (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         uuid NOT NULL REFERENCES public.users(id),
    exercise_id     uuid NOT NULL REFERENCES public.exercises(id),
    sense_id        integer REFERENCES public.dim_word_senses(id),
    exercise_type   text NOT NULL,
    is_correct      boolean,
    is_first_attempt boolean DEFAULT true,
    served_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_ueh_user_sense_type
    ON public.user_exercise_history(user_id, sense_id, exercise_type, served_at DESC);

CREATE INDEX idx_ueh_user_recent
    ON public.user_exercise_history(user_id, served_at DESC);
```

Purpose-built for scheduling lookups. Leaner than exercise_attempts (which remains source of truth for analytics).

## Core RPC: get_exercise_session

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
    phase           text,
    slot_reason     text
) AS $$
DECLARE
    v_due_count     integer := ROUND(p_session_size * 0.40);
    v_learning_count integer := ROUND(p_session_size * 0.40);
    v_new_count     integer := p_session_size - v_due_count - v_learning_count;
BEGIN
    RETURN QUERY

    WITH recent_seen AS (
        SELECT DISTINCT exercise_id
        FROM public.user_exercise_history
        WHERE user_id = p_user_id
          AND served_at >= NOW() - INTERVAL '7 days'
    ),

    recent_type_sense AS (
        SELECT DISTINCT sense_id, exercise_type
        FROM public.user_exercise_history
        WHERE user_id = p_user_id
          AND served_at >= NOW() - INTERVAL '3 days'
    ),

    -- Step 1: FSRS due flashcards (~40%)
    due_senses AS (
        SELECT uf.sense_id, uvk.p_known
        FROM public.user_flashcards uf
        JOIN public.user_vocabulary_knowledge uvk
            ON uvk.user_id = uf.user_id AND uvk.sense_id = uf.sense_id
        WHERE uf.user_id = p_user_id
          AND uf.language_id = p_language_id
          AND uf.due_date <= CURRENT_DATE
          AND uf.state IN ('review', 'relearning')
        ORDER BY uf.due_date ASC
        LIMIT v_due_count * 3
    ),

    due_exercises AS (
        SELECT e.id AS exercise_id, e.exercise_type, ds.sense_id, e.content, ds.p_known,
            CASE
                WHEN ds.p_known < 0.40 THEN 'A'
                WHEN ds.p_known < 0.65 THEN 'B'
                WHEN ds.p_known < 0.80 THEN 'C'
                ELSE 'D'
            END AS phase,
            'due_review' AS slot_reason,
            random() AS sort_key
        FROM due_senses ds
        JOIN public.exercises e ON e.word_sense_id = ds.sense_id
            AND e.language_id = p_language_id AND e.is_active = TRUE
        WHERE e.id NOT IN (SELECT exercise_id FROM recent_seen)
          AND NOT EXISTS (
              SELECT 1 FROM recent_type_sense rts
              WHERE rts.sense_id = ds.sense_id AND rts.exercise_type = e.exercise_type
          )
          AND e.exercise_type = ANY(
              CASE
                  WHEN ds.p_known < 0.40 THEN ARRAY['text_flashcard','listening_flashcard','cloze_completion']
                  WHEN ds.p_known < 0.65 THEN ARRAY['text_flashcard','listening_flashcard','cloze_completion',
                      'jumbled_sentence','tl_nl_translation','nl_tl_translation','spot_incorrect_sentence','spot_incorrect_part']
                  WHEN ds.p_known < 0.80 THEN ARRAY['semantic_discrimination','collocation_gap_fill',
                      'collocation_repair','odd_collocation_out','odd_one_out','style_pattern_match','style_voice_transform',
                      'jumbled_sentence','tl_nl_translation']
                  ELSE ARRAY['verb_noun_match','context_spectrum','timed_speed_round','style_imitation',
                      'collocation_gap_fill','semantic_discrimination']
              END
          )
    ),
    due_picks AS (SELECT * FROM due_exercises ORDER BY sort_key LIMIT v_due_count),

    -- Step 2: Active learning zone (BKT 0.40-0.75) (~40%)
    learning_senses AS (
        SELECT uvk.sense_id, uvk.p_known
        FROM public.user_vocabulary_knowledge uvk
        WHERE uvk.user_id = p_user_id AND uvk.language_id = p_language_id
          AND uvk.p_known BETWEEN 0.40 AND 0.75
          AND uvk.sense_id NOT IN (SELECT sense_id FROM due_picks)
        ORDER BY (uvk.p_known * (1 - uvk.p_known)) DESC
        LIMIT v_learning_count * 3
    ),
    learning_exercises AS (
        SELECT e.id AS exercise_id, e.exercise_type, ls.sense_id, e.content, ls.p_known,
            CASE WHEN ls.p_known < 0.65 THEN 'B' ELSE 'C' END AS phase,
            'active_learning' AS slot_reason, random() AS sort_key
        FROM learning_senses ls
        JOIN public.exercises e ON e.word_sense_id = ls.sense_id
            AND e.language_id = p_language_id AND e.is_active = TRUE
        WHERE e.id NOT IN (SELECT exercise_id FROM recent_seen)
          AND NOT EXISTS (
              SELECT 1 FROM recent_type_sense rts
              WHERE rts.sense_id = ls.sense_id AND rts.exercise_type = e.exercise_type
          )
    ),
    learning_picks AS (SELECT * FROM learning_exercises ORDER BY sort_key LIMIT v_learning_count),

    -- Step 3: New/encountered words (p_known < 0.40) (~20%)
    new_senses AS (
        SELECT uvk.sense_id, uvk.p_known
        FROM public.user_vocabulary_knowledge uvk
        WHERE uvk.user_id = p_user_id AND uvk.language_id = p_language_id
          AND uvk.p_known < 0.40 AND uvk.status IN ('encountered', 'unknown')
          AND uvk.sense_id NOT IN (SELECT sense_id FROM due_picks)
          AND uvk.sense_id NOT IN (SELECT sense_id FROM learning_picks)
        ORDER BY uvk.last_evidence_at DESC NULLS LAST
        LIMIT v_new_count * 3
    ),
    new_exercises AS (
        SELECT e.id AS exercise_id, e.exercise_type, ns.sense_id, e.content, ns.p_known,
            'A' AS phase, 'new_word' AS slot_reason, random() AS sort_key
        FROM new_senses ns
        JOIN public.exercises e ON e.word_sense_id = ns.sense_id
            AND e.language_id = p_language_id AND e.is_active = TRUE
            AND e.exercise_type = ANY(ARRAY['text_flashcard','listening_flashcard','cloze_completion'])
        WHERE e.id NOT IN (SELECT exercise_id FROM recent_seen)
    ),
    new_picks AS (SELECT * FROM new_exercises ORDER BY sort_key LIMIT v_new_count),

    -- Merge and shuffle
    all_picks AS (
        SELECT exercise_id, exercise_type, sense_id, content, p_known, phase, slot_reason
        FROM due_picks
        UNION ALL SELECT exercise_id, exercise_type, sense_id, content, p_known, phase, slot_reason
        FROM learning_picks
        UNION ALL SELECT exercise_id, exercise_type, sense_id, content, p_known, phase, slot_reason
        FROM new_picks
    )
    SELECT * FROM all_picks ORDER BY random();

END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;
```

## ExerciseScheduler Service

```python
# services/vocabulary_ladder/scheduler.py
class ExerciseScheduler:
    def build_session_queue(
        self,
        user_id: str,
        language_id: int,
        session_size: int = 20
    ) -> list[ScheduledExercise]:
        """Calls get_exercise_session RPC, returns ordered exercise list."""

    def log_exercise_served(self, user_id, exercise_id, sense_id, exercise_type):
        """Inserts row into user_exercise_history (cooldown tracking)."""

    def process_response(self, user_id, exercise_id, sense_id, is_correct, is_first_attempt):
        """
        1. Log to exercise_attempts (analytics)
        2. Log to user_exercise_history (scheduling)
        3. Update BKT via bkt_update()
        4. Update FSRS via schedule_review()
        5. Update vocabulary ladder via progression engine
        """
```

## Performance

With proper indexes (`idx_uf_user_due`, `idx_uvk_user_pknown`, `idx_exercises_sense`), the `get_exercise_session` RPC resolves a 20-exercise session in <50ms on a properly indexed Supabase instance.

## Future: ML-Based Optimization

Log all served exercises for future Thompson Sampling contextual bandit:
```json
{
  "user_id": "...",
  "sense_id": "...",
  "exercise_type": "...",
  "p_known_at_serve": 0.62,
  "fsrs_stability_at_serve": 4.2,
  "outcome": "correct",
  "response_time_ms": 3200,
  "days_since_last_seen": 5
}
```

Once ~50k rows exist, train bandit to discover which exercise types are most effective at moving p_known for words at each level.

## Related Pages

- [[features/vocab-dojo]] — Prose description
- [[algorithms/vocabulary-ladder]] — Level progression
- [[features/exercises.tech]] — Exercise table schema
- [[database/schema.tech]] — Full schema
