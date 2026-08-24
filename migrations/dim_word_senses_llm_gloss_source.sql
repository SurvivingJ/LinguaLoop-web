-- Allow 'llm_gloss' as a dim_word_senses.source value.
--
-- Cross-language gloss rows (a definition of a word written in a language
-- other than the word's own -- e.g. an English gloss for a Japanese sense)
-- are additive dim_word_senses rows: same vocab_id/sense_rank/definition_level,
-- a different definition_language_id. They need their own `source` tag so
-- maintenance scripts (validate_sense_languages.py) and future backfills can
-- tell a gloss apart from a native definition instead of "fixing" it back
-- into the word's own language.
--
-- Table is small (a few thousand rows) -- plain ALTER, no NOT VALID/VALIDATE
-- split needed per migrations/CLAUDE.md's lock-window guidance.
--
-- Applied live 2026-08-23 (project kpfqrjtfxmujzolwsvdq).

ALTER TABLE public.dim_word_senses
    DROP CONSTRAINT dim_word_senses_source_check;

ALTER TABLE public.dim_word_senses
    ADD CONSTRAINT dim_word_senses_source_check
    CHECK (source = ANY (ARRAY['llm'::text, 'manual'::text, 'llm_gloss'::text]));
