-- phase15_word_assets_validation_warnings.sql
-- Add validation_warnings column to word_assets.
-- Warnings are non-blocking quality flags (e.g. low morphological form count)
-- that do not invalidate the asset but are worth surfacing for review.

ALTER TABLE public.word_assets
    ADD COLUMN IF NOT EXISTS validation_warnings text[];
