-- TASK-743 (plan §3d, T3d.4) — retire duplicate context-free exercises.
--
-- Run BEFORE task743_context_free_exercise_caps.sql, whose unique index cannot
-- be built while the duplicates are still active.
--
-- Non-destructive: sets is_active = false rather than DELETE. Nothing is lost,
-- attempt history stays attached to the rows that carry it, and the partial
-- unique index is itself keyed on is_active, so deactivating is exactly the
-- mechanism that frees a slot. Reverse it by flipping the flag back on the
-- rows tagged below.
--
-- Scope, measured 2026-08-31 on the live corpus:
--   definition_match       192 rows /  54 senses -> keep 2 each, retire  84
--   pinyin_to_hanzi         50 rows /  27 senses -> keep 1 each, retire  23
--   hanzi_to_pinyin         50 rows /  27 senses -> keep 1 each, retire  23
--   tone_id_word            50 rows /  27 senses -> keep 1 each, retire  23
--   phonetic_recognition    50 rows /  30 senses -> keep 1 each, retire  20
--   kanji_to_reading        14 rows /   7 senses -> keep 1 each, retire   7
--   reading_to_kanji        14 rows /   7 senses -> keep 1 each, retire   7
--   classifier_match         5 rows /   3 senses -> keep 1 each, retire   2
--   synonym_antonym_match    9 rows /   8 senses -> keep 2 each, retire   0
--   counter_match            2 rows /   1 sense  -> keep 1 each, retire   1
--
-- ~190 rows of ~12,000, so the point is not the storage. The point is that the
-- same generation budget then buys breadth — coverage sits at 387 senses
-- against 11,994 the learner has already met in tests — instead of a shuffled
-- repeat of a word that already has one.
--
-- Which row survives: the one with the most attempts (real usage is worth
-- keeping), then the oldest (stable ids), then lowest uuid as a deterministic
-- final tie-break. Idempotent: re-running finds nothing left to deactivate.

BEGIN;

WITH capped AS (
    SELECT
        e.id,
        e.exercise_type,
        row_number() OVER (
            PARTITION BY
                e.word_sense_id,
                e.exercise_type,
                -- The context anchor. Polyphonic hanzi_to_pinyin /
                -- kanji_to_reading items store a context_sentence, and two
                -- readings in two sentences are two real questions.
                coalesce(e.content->>'context_sentence', '')
            ORDER BY
                coalesce(e.attempt_count, 0) DESC,
                e.created_at ASC,
                e.id ASC
        ) AS rn
    FROM public.exercises e
    WHERE e.is_active
      AND e.word_sense_id IS NOT NULL
      AND e.exercise_type IN (
          'tone_id_word', 'hanzi_to_pinyin', 'pinyin_to_hanzi',
          'kanji_to_reading', 'reading_to_kanji', 'phonetic_recognition',
          'classifier_match', 'counter_match',
          'definition_match', 'synonym_antonym_match'
      )
),
surplus AS (
    SELECT id FROM capped
    WHERE rn > CASE
        -- Distractors drawn from other words make a second variant a second
        -- question. A third adds little.
        WHEN exercise_type IN ('definition_match', 'synonym_antonym_match')
            THEN 2
        ELSE 1
    END
)
UPDATE public.exercises e
SET is_active = false,
    tags = coalesce(e.tags, '{}'::jsonb)
           || jsonb_build_object(
                  'retired_by', 'task743_context_free_cap',
                  'retired_at', now()
              )
FROM surplus s
WHERE e.id = s.id;

COMMIT;

-- Verification (run after COMMIT; every row should report surplus = 0):
--
--   SELECT exercise_type,
--          count(*) AS active,
--          count(*) - count(DISTINCT (word_sense_id,
--                     coalesce(content->>'context_sentence',''))) AS surplus
--   FROM public.exercises
--   WHERE is_active AND word_sense_id IS NOT NULL
--     AND exercise_type IN ('tone_id_word','hanzi_to_pinyin','pinyin_to_hanzi',
--         'kanji_to_reading','reading_to_kanji','phonetic_recognition',
--         'classifier_match','counter_match')
--   GROUP BY 1 ORDER BY 1;
