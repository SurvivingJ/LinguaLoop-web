-- ============================================================================
-- dim_character_components — CJK character → component index (TASK-529)
-- ============================================================================
-- Powers the visual-similarity tier of the reverse-reading distractor ladder
-- (`reading_to_kanji` / `pinyin_to_hanzi`): when a reading's homophone set is
-- too thin to fill four options, foils are padded with characters that *look*
-- confusable because they share structure — the 张/章/掌 case.
--
-- Consumed by services/vocabulary_ladder/deterministic/lexicon.py
-- (`_load_components`), which reads only `character` and `components`. Every
-- other column is provenance or future headroom, and all are nullable.
--
-- Populated by scripts/import_character_components.py. An EMPTY TABLE IS A
-- SUPPORTED STATE: the generator degrades to homophone + frequency foils and
-- logs at debug. Nothing fails to generate because the import has not run.
--
-- `source` and `licence` are NOT NULL on purpose. This table exists only
-- because third-party data was imported into it, and a row that cannot say
-- where it came from cannot be audited when a licence question is asked. They
-- are per row rather than per run for the same reason — two sources coexist.
--
-- NOTE: this file was written on 2026-08-11 to record a table that had been
-- created live on 2026-08-08 without a repo record (migrations/CLAUDE.md: the
-- directory must reflect the current definition of every object). It is
-- written IF NOT EXISTS and matches the live definition exactly, so applying
-- it to the live DB is a no-op.
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.dim_character_components (
    character     text        PRIMARY KEY,
    components    text[]      NOT NULL DEFAULT '{}'::text[],
    radical       text,
    stroke_count  smallint,
    decomposition text,
    source        text        NOT NULL,
    licence       text        NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.dim_character_components IS
    'CJK character → component index for visual-similarity distractors (TASK-529). '
    'Empty is a supported state; the reverse-reading generator degrades to homophones.';
COMMENT ON COLUMN public.dim_character_components.components IS
    'Flattened component characters, recursively resolved. Queried with GIN && / @>.';
COMMENT ON COLUMN public.dim_character_components.decomposition IS
    'Raw source decomposition expression, kept verbatim for re-derivation.';
COMMENT ON COLUMN public.dim_character_components.licence IS
    'Per-row licence of the source data. NOT NULL so provenance is always answerable.';

-- Membership lookups ("which characters contain 尚?") are the only access
-- pattern besides the full paged scan, and they are array-containment.
CREATE INDEX IF NOT EXISTS idx_dim_character_components_components
    ON public.dim_character_components USING gin (components);

-- Reference data: world-readable, writable only by the service role (which
-- bypasses RLS). The absence of INSERT/UPDATE/DELETE policies is intentional —
-- the import script runs with the service key.
ALTER TABLE public.dim_character_components ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policy
        WHERE polrelid = 'public.dim_character_components'::regclass
          AND polname  = 'dim_character_components_read'
    ) THEN
        CREATE POLICY dim_character_components_read
            ON public.dim_character_components
            FOR SELECT
            USING (true);
    END IF;
END
$$;

COMMIT;


-- ----------------------------------------------------------------------------
-- Verification
-- ----------------------------------------------------------------------------
-- SELECT source, licence, count(*) FROM public.dim_character_components
--  GROUP BY 1, 2 ORDER BY 3 DESC;
--
-- Shared-component neighbours of 掌:
-- SELECT character FROM public.dim_character_components
--  WHERE components && (SELECT components FROM public.dim_character_components
--                        WHERE character = '掌')
--    AND character <> '掌'
--  LIMIT 20;
