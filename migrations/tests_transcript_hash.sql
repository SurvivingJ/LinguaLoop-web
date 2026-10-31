-- ============================================================================
-- tests_transcript_hash.sql — tests.transcript_hash (TASK-900)
-- Date: 2026-10-30
-- Spec: wiki/features/test-sentence-references.tech.md ("Changed: tests")
--       wiki/tasklist/test-sentence-references.tasks.md (TASK-900)
--
-- Adds a nullable text column holding the hex sha256 of tests.transcript.
-- It is maintained by scripts/audit_transcript_preambles.py (which writes it
-- for every active test) and later by scripts/build_test_sentences.py, which
-- uses it to skip tests whose transcript has not changed and to retire
-- test_sentences / test_sentence_references rows when it has. There is
-- deliberately no trigger: transcripts are edited only by admin tooling,
-- and the segmenter must be able to detect "hash is stale" on its own.
--
-- Idempotent: re-running is a no-op. No new tables or functions, so the
-- TASK-881 security rules (RLS / REVOKE) do not apply; tests already has
-- RLS enabled and the column inherits the table's grants.
-- ============================================================================

BEGIN;

ALTER TABLE public.tests
    ADD COLUMN IF NOT EXISTS transcript_hash text;

COMMENT ON COLUMN public.tests.transcript_hash IS
    'Hex sha256 of transcript, written by scripts/audit_transcript_preambles.py '
    'and read by scripts/build_test_sentences.py to detect transcript changes. '
    'NULL until the cleanup script has run for the row (TASK-900).';

COMMIT;
