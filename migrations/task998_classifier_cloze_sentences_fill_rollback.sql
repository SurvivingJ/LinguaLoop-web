-- Rollback for migrations/task998_classifier_cloze_sentences_fill.sql. Not
-- applied; kept for an operator who needs to undo the fill.
--
-- Previous state (captured 2026-11-17 before writing the fill):
--   SELECT count(*) FROM dim_classifier_noun_pairs
--    WHERE language_id = 1 AND example_sentence IS NOT NULL AND example_sentence <> '';
--   -> 0  (and 0 for every other language_id)
-- So every non-empty example_sentence on a language_id = 1 pair was written by
-- the fill, and restoring the previous state is setting them back to NULL.
-- Nothing else in the repo writes this column (scripts/build_classifier_dictionary.py
-- re-inserts pairs without it).
--
-- Expected effect: as many rows as the fill reported (661 when measured).
-- After the rollback get_classifier_drill_session_v2 serves no Fill-in items;
-- level-4 classifiers are drawn as Reverse.

UPDATE public.dim_classifier_noun_pairs
   SET example_sentence = NULL
 WHERE language_id = 1
   AND example_sentence IS NOT NULL;
