-- TASK-922: mechanical fixes from the 2026-11-09 quality audit.
-- Review, then apply by hand (LIVE-DB). One transaction. Content problems
-- (duplicates, giveaways, off-level choices, English in zh/ja) are NOT fixed
-- here — they are listed in remediation_2026-11-09.csv for regeneration.
--
-- Both fixes also patch tests.furigana_payload, whose `questions[i].choices[j]`
-- token lists mirror the question text (services/furigana_service).

BEGIN;

-- 1. ja ukiyo-e q4: every choice carries its own "A. "-style label (the UI
--    labels choices itself). Strip it from the four choices and the answer.
UPDATE public.questions
SET choices = (
        SELECT jsonb_agg(regexp_replace(c, '^[A-D]\.\s*', '') ORDER BY ord)
        FROM jsonb_array_elements_text(choices) WITH ORDINALITY AS e(c, ord)
    ),
    answer = to_jsonb(regexp_replace(answer #>> '{}', '^[A-D]\.\s*', '')),
    updated_at = now()
WHERE question_id = 'ja-d6-the-process-of-traditional-jap-20260824005420-q4'
  AND choices::text ~ '"A\. ';

--    Furigana tokens: each choice starts with plain tokens "A" then "." —
--    drop those two (guarded: only when they really are the label).
UPDATE public.tests t
SET furigana_payload = jsonb_set(
        t.furigana_payload, '{questions,3,choices}',
        (SELECT jsonb_agg(
                    CASE WHEN ch->0->>'text' IN ('A','B','C','D') AND ch->1->>'text' = '.'
                         THEN (ch - 0) - 0 ELSE ch END
                    ORDER BY ord)
         FROM jsonb_array_elements(t.furigana_payload #> '{questions,3,choices}')
              WITH ORDINALITY AS e(ch, ord)))
WHERE t.slug = 'ja-d6-the-process-of-traditional-jap-20260824005420'
  AND t.furigana_payload #>> '{questions,3,choices,0,0,text}' = 'A';

-- 2. ja socio-economic q2: simplified-Chinese 变 in 「質的变化」 -> 変.
UPDATE public.questions
SET choices = replace(choices::text, '变', '変')::jsonb,
    answer  = replace(answer::text,  '变', '変')::jsonb,
    updated_at = now()
WHERE question_id = 'ja-d6-the-socio-economic-implication-20260824002051-q2';

UPDATE public.tests
SET furigana_payload = replace(furigana_payload::text, '变', '変')::jsonb
WHERE slug = 'ja-d6-the-socio-economic-implication-20260824002051'
  AND furigana_payload::text LIKE '%变%';

COMMIT;

-- Verify: expect fixed = true for both, label_tokens_left = 0, simplified_left = 0.
SELECT q.question_id,
       (q.choices ? (q.answer #>> '{}')) AS fixed,
       q.choices::text ~ '"[A-D]\. ' AS label_left,
       (q.choices::text || q.answer::text) LIKE '%变%' AS simplified_left
FROM public.questions q
WHERE q.question_id IN ('ja-d6-the-process-of-traditional-jap-20260824005420-q4',
                        'ja-d6-the-socio-economic-implication-20260824002051-q2');
SELECT slug,
       (furigana_payload #>> '{questions,3,choices,0,0,text}') AS first_token_q4,
       furigana_payload::text LIKE '%变%' AS simplified_left
FROM public.tests
WHERE slug IN ('ja-d6-the-process-of-traditional-jap-20260824005420',
               'ja-d6-the-socio-economic-implication-20260824002051');
