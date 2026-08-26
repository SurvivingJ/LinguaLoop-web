-- Applied live 2026-08-25. Record of the deletion executed via
-- scripts/audit_kana_fragments.py's findings — see that script and
-- services/vocabulary/kana_homophone_judge.py::classify_kana_lemma for how
-- these 11 rows were identified as UniDic segmentation fragments (a
-- sub-word piece registered as if it were a standalone word, carrying the
-- definition of the longer compound/conjugation it was actually cut from)
-- rather than genuine standalone Japanese words.
--
-- Zero references confirmed across every table with a sense_id-shaped
-- column before deletion: exercise_attempts, exercises, generation_queue,
-- mysteries, mystery_questions, user_exercise_history, user_word_ladder,
-- word_quiz_results, tests, questions, word_assets,
-- user_vocabulary_knowledge, user_flashcards, vocabulary_review_queue.
--
-- Rows: きゅう/にゅう (fragments of 牛乳), ぎゅう (牛地), しゅっ (排出),
-- さっ (さっと), すい (吸い), たん (炭素), ふう (ふうふう),
-- ばっ (ぱっと/ばかり), くい (self-flagged misrecording), つうつう
-- (交通/通学 compound).

DELETE FROM dim_word_senses
WHERE vocab_id IN (20948,20949,22897,20720,21754,21756,22195,22285,22570,21149,21747);

DELETE FROM dim_vocabulary
WHERE id IN (20948,20949,22897,20720,21754,21756,22195,22285,22570,21149,21747);
