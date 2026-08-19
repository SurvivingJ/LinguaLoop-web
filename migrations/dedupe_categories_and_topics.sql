-- ============================================================================
-- Merge duplicate categories, dedupe the topics they let through, and make
-- the duplication impossible to repeat.
-- Date: 2026-08-14
--
-- Every category existed twice: ids 1-16 (created 03:01:01) and ids 33-48
-- (created 03:42:03, same day) carried identical names, identical
-- cooldown_days, and target_language_id NULL on both sides — a seed run twice,
-- not a per-language split. Only 'Family' (id 49) was unique.
--
-- Why it matters beyond tidiness: the Archivist's novelty check is scoped per
-- category id — a candidate is compared only against topics sharing its
-- category_id. Two rows named 'History' are therefore two disjoint dedup
-- universes, and a topic generated under id 10 is invisible to the similarity
-- gate for id 42. The 2026-08-14 topic fill ran 24 category rotations and drew
-- each twin in turn (run 1 'History' id 10, run 17 'History' id 42), so the
-- second half of that burst was generated with the first half's output hidden
-- from it.
--
-- Measured before this migration: 21 cross-twin topic pairs at or above the
-- 0.85 similarity threshold the Archivist itself enforces, topping out at
-- 1.000 — "The tactical evolution of zone defense in basketball", stored
-- twice. Each such pair would have been expanded into ~2.6 tests per queue
-- item across 3 languages.
--
-- Ordering matters: categories are merged BEFORE topics are deduped, so the
-- topic pass compares within the merged category and catches both the
-- cross-twin duplicates and the intra-category ones that predate them (e.g.
-- three "Building a simple robot arm ..." variants inside category 13).
--
-- Idempotent: after it runs there are no duplicate names left to merge, the
-- UNIQUE constraint is added only if absent, and the topic pass is a no-op
-- once no pair exceeds the threshold.
-- ============================================================================

BEGIN;

-- ──────────────────────────────────────────────────────────────────────────
-- 1. Category merge
-- ──────────────────────────────────────────────────────────────────────────

-- Canonical row for each name = the lowest id (the original seed).
CREATE TEMP TABLE category_merge ON COMMIT DROP AS
SELECT c.id AS dup_id,
       (SELECT MIN(k.id) FROM public.categories k WHERE k.name = c.name) AS canon_id
FROM public.categories c
WHERE c.id <> (SELECT MIN(k.id) FROM public.categories k WHERE k.name = c.name);

-- Repoint every referencing row. All three FKs are ON DELETE NO ACTION, so
-- this must happen before the DELETE below or it errors out.
UPDATE public.topics t
SET category_id = m.canon_id
FROM category_merge m WHERE t.category_id = m.dup_id;

UPDATE public.topic_generation_runs r
SET category_id = m.canon_id
FROM category_merge m WHERE r.category_id = m.dup_id;

UPDATE public.conversation_domains d
SET category_id = m.canon_id
FROM category_merge m WHERE d.category_id = m.dup_id;

-- Fold the duplicate's counters into the survivor. last_used_at must take the
-- later of the two or the rotation cooldown would immediately re-offer a
-- category that was in fact just used.
UPDATE public.categories c
SET total_topics_generated = COALESCE(c.total_topics_generated, 0) + agg.extra_topics,
    last_used_at           = GREATEST(c.last_used_at, agg.last_used),
    updated_at             = now()
FROM (
    SELECT m.canon_id,
           SUM(COALESCE(d.total_topics_generated, 0)) AS extra_topics,
           MAX(d.last_used_at)                        AS last_used
    FROM category_merge m
    JOIN public.categories d ON d.id = m.dup_id
    GROUP BY m.canon_id
) agg
WHERE c.id = agg.canon_id;

DELETE FROM public.categories c
USING category_merge m
WHERE c.id = m.dup_id;

-- The recurrence guard. create_all_tables.sql declares categories.name as
-- plain `varchar NOT NULL`, which is what allowed the second seed to land.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.categories'::regclass
          AND conname  = 'categories_name_key'
    ) THEN
        ALTER TABLE public.categories
            ADD CONSTRAINT categories_name_key UNIQUE (name);
    END IF;
END $$;

-- ──────────────────────────────────────────────────────────────────────────
-- 2. Topic dedupe (within the now-merged categories)
-- ──────────────────────────────────────────────────────────────────────────
--
-- 0.85 is TOPIC_SIMILARITY_THRESHOLD (services/topic_generation/config.py) —
-- the same bar the Archivist would have applied had it been able to see both
-- sides. Of each near-duplicate pair the OLDER row survives, so downstream
-- references stay pointed at the row that has existed longest.
--
-- Topics with a generated test are never dropped: tests.topic_id is
-- ON DELETE SET NULL, so deleting one would silently orphan a real test
-- rather than failing loudly. One topic in the drop set had a test and is
-- excluded here.

CREATE TEMP TABLE topic_drops ON COMMIT DROP AS
WITH pairs AS (
    SELECT b.id AS drop_id
    FROM public.topics a
    JOIN public.topics b
      ON a.category_id = b.category_id
     AND (a.created_at, a.id) < (b.created_at, b.id)
    WHERE a.embedding IS NOT NULL
      AND b.embedding IS NOT NULL
      AND 1 - (a.embedding <=> b.embedding) >= 0.85
)
SELECT DISTINCT p.drop_id
FROM pairs p
WHERE NOT EXISTS (
    SELECT 1 FROM public.tests te WHERE te.topic_id = p.drop_id
);

-- production_queue.topic_id is ON DELETE NO ACTION — clear the queue rows
-- first. All of them are Pending; nothing in flight is discarded.
DELETE FROM public.production_queue q
USING topic_drops d
WHERE q.topic_id = d.drop_id;

DELETE FROM public.topics t
USING topic_drops d
WHERE t.id = d.drop_id;

COMMIT;

-- ──────────────────────────────────────────────────────────────────────────
-- 3. Verification (run manually after migration)
-- ──────────────────────────────────────────────────────────────────────────
-- -- No duplicate names remain, and the constraint blocks new ones:
-- SELECT name, COUNT(*) FROM public.categories GROUP BY name HAVING COUNT(*) > 1;
--
-- -- No same-category topic pair still exceeds the Archivist's threshold:
-- SELECT COUNT(*) FROM public.topics a JOIN public.topics b
--   ON a.category_id = b.category_id AND a.id < b.id
--  WHERE 1 - (a.embedding <=> b.embedding) >= 0.85;
--
-- -- No queue row points at a deleted topic:
-- SELECT COUNT(*) FROM public.production_queue q
--  WHERE NOT EXISTS (SELECT 1 FROM public.topics t WHERE t.id = q.topic_id);
