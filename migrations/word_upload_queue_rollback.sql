-- word_upload_queue_rollback.sql — undoes word_upload_queue.sql.
-- Queued (not yet done) words are lost; user_word_watchlist rows already
-- written by the queue are kept. Set WORD_LIST_INLINE_GENERATION=true first
-- (or deploy code without the queue), else submissions answer 503.
BEGIN;
DROP TABLE IF EXISTS public.word_upload_queue;
COMMIT;
