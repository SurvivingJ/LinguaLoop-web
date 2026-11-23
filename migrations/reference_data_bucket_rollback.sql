-- =============================================================================
-- Rollback of migrations/reference_data_bucket.sql (TASK-1034; tech §5.2).
-- *** LIVE-DB: the OWNER runs it. It refuses while the bucket still holds any file:
-- *** delete the word-list files first (Storage dashboard or API).
-- If the project refuses a direct DELETE on storage.buckets, remove the empty bucket in the
-- Storage dashboard instead (as migrations/archive/exercise_content_storage_rollback.sql advises).
-- =============================================================================

BEGIN;

DO $guard$
BEGIN
  IF EXISTS (SELECT 1 FROM storage.objects WHERE bucket_id = 'reference-data') THEN
    RAISE EXCEPTION 'reference_data_bucket rollback: delete the bucket''s files first (Storage dashboard or API)';
  END IF;
END
$guard$;

DELETE FROM storage.buckets WHERE id = 'reference-data';

COMMIT;
