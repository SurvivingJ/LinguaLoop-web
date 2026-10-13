-- Read-only audit for two known exercise defects. Run in the Supabase SQL editor.
-- Assumes exercises(id, exercise_type, content jsonb, language_id, is_active, word_sense_id).

-- 1. jumbled_sentence rows the renderer cannot show: no usable chunks AND no
--    original_sentence to chunk at serve time, or fewer than 3 chunks.
SELECT e.id, e.language_id, e.word_sense_id, e.is_active,
       jsonb_array_length(CASE WHEN jsonb_typeof(e.content->'chunks') = 'array'
                               THEN e.content->'chunks' ELSE '[]'::jsonb END) AS n_chunks,
       (e.content ? 'original_sentence') AS has_sentence
FROM exercises e
WHERE e.exercise_type = 'jumbled_sentence'
  AND e.is_active
  AND jsonb_array_length(CASE WHEN jsonb_typeof(e.content->'chunks') = 'array'
                              THEN e.content->'chunks' ELSE '[]'::jsonb END) < 3
  AND coalesce(btrim(e.content->>'original_sentence'), '') = ''
ORDER BY e.language_id, e.id;

-- 1b. Summary of the above by language.
SELECT e.language_id, count(*) AS unrenderable_active_rows
FROM exercises e
WHERE e.exercise_type = 'jumbled_sentence' AND e.is_active
  AND jsonb_array_length(CASE WHEN jsonb_typeof(e.content->'chunks') = 'array'
                              THEN e.content->'chunks' ELSE '[]'::jsonb END) < 3
  AND coalesce(btrim(e.content->>'original_sentence'), '') = ''
GROUP BY e.language_id ORDER BY 1;

-- 2. definition_match rows whose options mix CJK and non-CJK definitions.
--    Options live at content.options (v1) or content.nl.<code>.options (v2).
WITH opts AS (
  SELECT e.id, e.language_id, e.word_sense_id, o.value AS opt
  FROM exercises e
  CROSS JOIN LATERAL (
    SELECT coalesce(e.content->'options',
                    (SELECT b.value->'options' FROM jsonb_each(e.content->'nl') b LIMIT 1)) AS arr
  ) a
  CROSS JOIN LATERAL jsonb_array_elements_text(
    CASE WHEN jsonb_typeof(a.arr) = 'array' THEN a.arr ELSE '[]'::jsonb END) o
  WHERE e.exercise_type = 'definition_match' AND e.is_active
)
SELECT id, language_id, word_sense_id,
       count(*) FILTER (WHERE opt ~ '[぀-ヿ㐀-鿿]') AS n_cjk,
       count(*) FILTER (WHERE opt !~ '[぀-ヿ㐀-鿿]') AS n_other
FROM opts
GROUP BY id, language_id, word_sense_id
HAVING count(*) FILTER (WHERE opt ~ '[぀-ヿ㐀-鿿]') > 0
   AND count(*) FILTER (WHERE opt !~ '[぀-ヿ㐀-鿿]') > 0
ORDER BY language_id, id;

-- 3. Inspect the five reported exercises.
SELECT id, exercise_type, language_id, is_active, content
FROM exercises
WHERE id IN ('5f2b2c50-9b24-4138-88c1-79d76821d14e',
             'f5141dbd-f10d-4075-acd5-d8dc56c1d22d',
             'ccf797f5-dd70-49d9-8c13-bf1b9d8b767c',
             '2c70a5bd-2662-473d-8c9b-da7b63250115',
             'cd9cbc1d-a210-4070-99eb-f0e53da2a476');
