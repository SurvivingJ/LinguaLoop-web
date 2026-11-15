-- =============================================================================
-- add_exercise_gin_indexes.sql  (rollback of drop_unused_exercise_gin_indexes.sql)
-- =============================================================================
-- Re-creates the two GIN indexes on public.exercises that
-- migrations/drop_unused_exercise_gin_indexes.sql removes. Definitions are
-- copied verbatim from the live database on 2026-11-15 (pg_get_indexdef).
--
-- When to apply: only if something starts filtering exercises by JSON
-- containment or key existence and needs it fast, e.g.
--     content @> '{"word": "..."}'      tags ? 'distractor_rebuild'
--     .contains('content', {...})       (supabase-py / PostgREST cs. filter)
-- Every app path today looks exercises up by word_sense_id / ladder_level /
-- exercise_type (btree indexes), so none of them need this.
--
-- Cost: ~72 MB of database size at ~117k exercises (content 63 MB, tags 9 MB),
-- growing with the table, and a GIN update on every exercise insert/update.
--
-- Locking: a plain CREATE INDEX blocks writes to exercises (not reads) for the
-- build, about a minute each. To avoid blocking generation batches, run the two
-- statements one at a time OUTSIDE a transaction (SQL editor, not a migration
-- runner) with CONCURRENTLY:
--     CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exercises_content_gin ON public.exercises USING gin (content);
--     CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exercises_tags_gin    ON public.exercises USING gin (tags);
--
-- Undo: migrations/drop_unused_exercise_gin_indexes.sql
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_exercises_content_gin ON public.exercises USING gin (content);
CREATE INDEX IF NOT EXISTS idx_exercises_tags_gin    ON public.exercises USING gin (tags);
