-- Fix the question-type mix for tiers 3, 5 and 6 (test-quality-checks, 2026-11-09).
--
-- The tier mix asked for the same type twice where a passage can only answer it
-- once in a distinct way:
--   T3  literal_detail, vocabulary_context, main_idea, main_idea, supporting_detail
--       -> two main_idea questions (a passage has one main idea)
--   T5  main_idea, supporting_detail, inference, inference, author_purpose
--   T6  supporting_detail, inference, inference, vocabulary_context, author_purpose
--       -> two inference questions; the 2026-11-09 review found same-type pairs
--          are where near-duplicate questions come from.
--
-- New mix (one row per tier; T1, T2, T4 unchanged):
--   T3  literal_detail, literal_detail, vocabulary_context, main_idea, supporting_detail
--       (second main_idea -> literal_detail: T3 stays concrete; detail questions
--        vary with the passage, so a second one doesn't collide)
--   T5  main_idea, supporting_detail, inference, vocabulary_context, author_purpose
--       (second inference -> vocabulary_context: T5 was the only tier from T1 up
--        with no vocabulary question)
--   T6  main_idea, supporting_detail, inference, vocabulary_context, author_purpose
--       (second inference -> main_idea: T6 had none)
-- T4, T5 and T6 now share one mix — one question of each of the five types above
-- literal recall; difficulty comes from the passage, which jev places by tier.
--
-- Data-only: no new objects, no grants needed. Idempotent.

BEGIN;

UPDATE public.question_type_distributions_by_tier AS d
SET question_type_1 = v.t1,
    question_type_2 = v.t2,
    question_type_3 = v.t3,
    question_type_4 = v.t4,
    question_type_5 = v.t5,
    updated_at      = now()
FROM (VALUES
    (3, 'literal_detail', 'literal_detail',    'vocabulary_context', 'main_idea',          'supporting_detail'),
    (5, 'main_idea',      'supporting_detail', 'inference',          'vocabulary_context', 'author_purpose'),
    (6, 'main_idea',      'supporting_detail', 'inference',          'vocabulary_context', 'author_purpose')
) AS v(tier_id, t1, t2, t3, t4, t5)
WHERE d.tier_id = v.tier_id;

COMMIT;

-- Verify: no tier may request any type more than once except literal_detail /
-- vocabulary_context at T1-T3. Expect T3 = LD, LD, VC, MI, SD; T5 = T6 = MI, SD, INF, VC, AP.
SELECT tier_id, question_type_1, question_type_2, question_type_3, question_type_4, question_type_5
FROM public.question_type_distributions_by_tier
ORDER BY tier_id;
