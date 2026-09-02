-- APPLIED live 2026-08-31. Before: 5 sentences across 5 rows missing
-- `is_correct`. After: 0 missing, 0 non-boolean, 1568 sentences intact,
-- all 392 semantic_discrimination variants still have exactly 1 correct
-- sentence. Idempotent — re-running is a no-op.
-- Repair: hallucinated `is_correct` key names in exercise content
-- =============================================================================
-- CONTEXT
--   Five live semantic_discrimination exercises carry a sentence whose
--   correctness flag was stored under a hallucinated key name instead of
--   `is_correct`:
--
--     is_logger        (00e1218a-8d15-41d2-a014-98da25eca41d)
--     is_equal         (3c3cb25a-3f3f-4e48-8d62-96af09aaf98c)
--     is游戏副本        (545ed349-de5d-4ae3-a848-16a33e726b9f)
--     is游戏副本        (f99f4d11-1700-41ab-9dc9-6b7834d73890)
--     is_context       (fd1450d6-9231-4529-9930-965b942f36d1)
--
--   All five are language_id=1 (zh) and all five are in the `hant` variant
--   only — the simplified sibling in the same row is intact.
--
--   NOT the deterministic converter: services/vocabulary_ladder/
--   script_converter.py:102 does {k: convert(v) for k, v in obj.items()},
--   i.e. keys are preserved and only values converted. These `hant` blocks
--   were LLM-authored. Finding that producer is a separate task (T5.1);
--   this file only repairs the stored rows.
--
--   `is_correct` does not appear anywhere in application code under these
--   stray names, so nothing reads them: the affected sentence effectively has
--   no correctness flag. In every one of the five the stray key's value is
--   `false` and the sentence is a distractor, so the repair is a pure rename
--   preserving the value.
--
--   Guard rails: this rewrites ONLY sentences that (a) lack `is_correct`,
--   (b) have exactly one stray `is*` key, and (c) whose stray value is a
--   boolean. Anything not matching all three is left alone for manual review.
--
-- SAFETY
--   Idempotent — re-running is a no-op once `is_correct` is present.
--   Verification queries at the bottom; run them before and after.
-- =============================================================================

BEGIN;

WITH candidate AS (
    SELECT
        e.id,
        variant.key                             AS variant_key,
        sent.ord                                AS sent_ord,
        sent.value                              AS sentence,
        stray.key                               AS stray_key,
        stray.value                             AS stray_value
    FROM public.exercises e
    CROSS JOIN LATERAL jsonb_each(e.content) AS variant
    CROSS JOIN LATERAL jsonb_array_elements(
        CASE WHEN jsonb_typeof(variant.value->'sentences') = 'array'
             THEN variant.value->'sentences'
             ELSE '[]'::jsonb END
    ) WITH ORDINALITY AS sent(value, ord)
    CROSS JOIN LATERAL jsonb_each(sent.value) AS stray
    WHERE e.exercise_type = 'semantic_discrimination'
      AND NOT (sent.value ? 'is_correct')       -- (a) flag genuinely absent
      AND stray.key <> 'text'
      AND stray.key LIKE 'is%'
      AND jsonb_typeof(stray.value) = 'boolean' -- (c) value is a real bool
),
-- (b) exactly one stray candidate per sentence, else leave for manual review
unambiguous AS (
    SELECT * FROM candidate c
    WHERE (
        SELECT count(*) FROM candidate c2
        WHERE c2.id = c.id
          AND c2.variant_key = c.variant_key
          AND c2.sent_ord = c.sent_ord
    ) = 1
),
repaired_sentences AS (
    SELECT
        u.id,
        u.variant_key,
        u.sent_ord,
        (u.sentence - u.stray_key)
            || jsonb_build_object('is_correct', u.stray_value) AS fixed
    FROM unambiguous u
),
repaired_variants AS (
    SELECT
        r.id,
        r.variant_key,
        jsonb_set(
            e.content -> r.variant_key,
            '{sentences}',
            (
                SELECT jsonb_agg(
                           CASE WHEN s.ord = r.sent_ord THEN r.fixed ELSE s.value END
                           ORDER BY s.ord
                       )
                FROM jsonb_array_elements(
                         e.content -> r.variant_key -> 'sentences'
                     ) WITH ORDINALITY AS s(value, ord)
            )
        ) AS fixed_variant
    FROM repaired_sentences r
    JOIN public.exercises e ON e.id = r.id
)
UPDATE public.exercises e
SET content = jsonb_set(e.content, ARRAY[rv.variant_key], rv.fixed_variant)
FROM repaired_variants rv
WHERE e.id = rv.id;

COMMIT;

-- ──────────────────────────────────────────────────────────────
-- Verification (expect 0 rows after; 5 rows before)
-- ──────────────────────────────────────────────────────────────
-- WITH s AS (
--   SELECT e.id, e.exercise_type, variant.key AS variant, sent
--   FROM public.exercises e
--   CROSS JOIN LATERAL jsonb_each(e.content) variant
--   CROSS JOIN LATERAL jsonb_array_elements(
--     CASE WHEN jsonb_typeof(variant.value->'sentences')='array'
--          THEN variant.value->'sentences' ELSE '[]'::jsonb END) sent
--   WHERE e.is_active
-- )
-- SELECT exercise_type, count(*) FILTER (WHERE NOT (sent ? 'is_correct')) AS missing
-- FROM s GROUP BY 1;
--
-- Each repaired row must still have exactly one correct sentence:
-- WITH s AS (
--   SELECT e.id, variant.key AS variant,
--          count(*) FILTER (WHERE (sent->>'is_correct')::boolean) AS correct_cnt,
--          count(*) AS total
--   FROM public.exercises e
--   CROSS JOIN LATERAL jsonb_each(e.content) variant
--   CROSS JOIN LATERAL jsonb_array_elements(
--     CASE WHEN jsonb_typeof(variant.value->'sentences')='array'
--          THEN variant.value->'sentences' ELSE '[]'::jsonb END) sent
--   WHERE e.exercise_type='semantic_discrimination'
--   GROUP BY 1,2
-- )
-- SELECT * FROM s WHERE correct_cnt <> 1;
