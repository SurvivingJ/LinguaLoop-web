-- Japanese senses with no active exercises, ranked by generation demand.
--
-- Demand = how many active tests reference the sense. That ordering is the
-- same one scripts/export_exercise_worklist.py applies, and the same one
-- TASK-784 specifies -- a sense no test uses earns assets last.
--
-- SCOPING (live 2026-09-19, ja):
--   6,710 senses have no exercises
--   1,582 of those are referenced by at least one test   <- the real pool
--     479 are referenced by 2 or more tests              <- start here
--
-- NOTE: this CSV is for scoping and review. The batch-exercise-generation
-- skill does NOT consume it -- it needs the batch JSON from
-- scripts/export_exercise_worklist.py, which carries the live prompt_templates
-- text, the mined corpus sentences and the validation enums. See the footer.
--
-- Run:
--   psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 \
--     -c "\copy (`cat scripts/sql/export_ja_senses_no_exercises.sql`) \
--         TO 'data/exercise_seeding/ja_senses_no_exercises.csv' WITH CSV HEADER"

WITH ex AS (
    SELECT DISTINCT word_sense_id AS sid
    FROM exercises
    WHERE is_active AND word_sense_id IS NOT NULL
),
demand AS (
    SELECT s.sid, COUNT(*) AS n_tests
    FROM tests t
    CROSS JOIN LATERAL unnest(t.vocab_sense_ids) AS s(sid)
    WHERE t.language_id = 3
    GROUP BY 1
)
SELECT
    ws.id                      AS sense_id,
    v.lemma,
    v.reading,
    v.part_of_speech,
    v.frequency_rank           AS zipf,
    v.level_tag,
    v.semantic_class,
    ws.sense_rank,
    ws.definition,
    COALESCE(d.n_tests, 0)     AS blocks_n_tests
FROM dim_word_senses ws
JOIN dim_vocabulary v
      ON v.id = ws.vocab_id
     AND v.language_id = 3
LEFT JOIN ex ON ex.sid = ws.id
LEFT JOIN demand d ON d.sid = ws.id
WHERE ws.definition_language_id = v.language_id   -- own-language senses only;
                                                  -- cross-language glosses share
                                                  -- the vocab key and would double
                                                  -- every row
  AND ex.sid IS NULL
  AND d.n_tests IS NOT NULL                       -- drop to include unreferenced
ORDER BY d.n_tests DESC, v.frequency_rank DESC NULLS LAST, ws.id
