-- =============================================================================
-- Private Storage bucket `reference-data` for the exam word-list files (TASK-1034)
-- Spec: wiki/features/knowledge-report.tech.md §5.2, §8; ADR-054 (revised 2026-11-18).
--
-- *** LIVE-DB: the OWNER applies this file to production. Agents never apply it.
--
-- Files: word-lists/<list_code>/v<N>.json (immutable, versioned; uploaded by the owner-run
-- scripts/build_word_lists.py --upload, TASK-1053). No table for list data exists.
-- Pattern: the exercise-content bucket, migrations/exercise_content_storage.sql (section 6).
--
-- SIZE: one storage.buckets row (< 1 KB, ESTIMATE); each uploaded file adds one
--       storage.objects row (~0.6 KB). File bytes count against Storage, not the database.
-- VERIFY (read-only, after apply):
--   SELECT id, public, file_size_limit, allowed_mime_types FROM storage.buckets WHERE id = 'reference-data';
--   -> reference-data | f | 5242880 | {application/json}
-- Idempotent: ON CONFLICT DO NOTHING.
-- Rollback: migrations/reference_data_bucket_rollback.sql
-- =============================================================================

BEGIN;

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('reference-data', 'reference-data', false, 5242880, ARRAY['application/json'])   -- 5 MiB per file
ON CONFLICT (id) DO NOTHING;

COMMIT;
-- No storage.objects policy for this bucket: only the service role (which bypasses RLS) reads or writes it.
