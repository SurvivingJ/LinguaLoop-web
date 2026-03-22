-- Migration: Simplify jumbled_sentence exercise storage
-- Strip 'chunks' and 'correct_ordering' from content JSONB,
-- keeping only 'original_sentence' (and 'source_test_id' if present).
-- Word splitting now happens at serve-time via LanguageProcessor.tokenize().

UPDATE exercises
SET content = jsonb_build_object('original_sentence', content->>'original_sentence')
           || CASE WHEN content ? 'source_test_id'
                   THEN jsonb_build_object('source_test_id', content->'source_test_id')
                   ELSE '{}'::jsonb END
WHERE exercise_type = 'jumbled_sentence'
  AND content ? 'chunks';
