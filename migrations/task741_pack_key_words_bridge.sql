-- TASK-741 (plan §4, T4.4 / T4.7) — pack -> sense bridge, and a ladder
-- intake timestamp.
--
-- Two additive changes, no data loss, safe to run more than once.
--
-- 1. `pack_key_words`. The practice-engine intake path has always queried a
--    table by this name, and it has never existed. The real packs schema is
--    `collocation_packs` bridged by `pack_collocations` to *collocations* —
--    a pack -> sense bridge was never built, so every pack-based intake call
--    threw undefined_table, was caught by a bare `except Exception:
--    logger.warning`, and returned "no candidates". Link 2 of the four broken
--    links in the plan's §4b table.
--
-- 2. `user_word_ladder.created_at`. Ladder intake is capped per *call*, not
--    per day, because there was no column recording when a subscription was
--    made. This is what makes a true per-calendar-day quota expressible.

BEGIN;

-- ---------------------------------------------------------------------
-- 1. pack -> sense bridge
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.pack_key_words (
    pack_id     bigint  NOT NULL
                REFERENCES public.collocation_packs (id) ON DELETE CASCADE,
    sense_id    integer NOT NULL
                REFERENCES public.dim_word_senses (id) ON DELETE CASCADE,
    -- Ordinal within the pack. Intake ranks by frequency rather than by this,
    -- but a curated pack has an intended teaching order and losing it at
    -- import would be irreversible.
    position    integer,
    created_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (pack_id, sense_id)
);

COMMENT ON TABLE public.pack_key_words IS
    'Pack -> word-sense bridge for practice-engine cold-start intake. '
    'Distinct from pack_collocations, which bridges packs to collocations. '
    'Consumed by PracticeSessionService._nominate_from_packs (Queue B).';

-- Intake filters `pack_id IN (...)`; the PK covers that. This index serves the
-- reverse question ("which packs teach this sense?"), which pack curation and
-- the coverage reports need.
CREATE INDEX IF NOT EXISTS idx_pack_key_words_sense
    ON public.pack_key_words (sense_id);

ALTER TABLE public.pack_key_words ENABLE ROW LEVEL SECURITY;

-- Pack contents are public catalogue data, same posture as collocation_packs.
DROP POLICY IF EXISTS pack_key_words_read ON public.pack_key_words;
CREATE POLICY pack_key_words_read
    ON public.pack_key_words FOR SELECT
    USING (true);

-- ---------------------------------------------------------------------
-- 2. ladder subscription timestamp
-- ---------------------------------------------------------------------

-- DEFAULT now() backfills every existing row to "today", which is wrong for
-- rows seeded earlier but harmless: the column exists to bound *future*
-- intake, and a per-day cap that treats the legacy 24 rows as today's intake
-- simply defers the next top-up by one day.
ALTER TABLE public.user_word_ladder
    ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();

COMMENT ON COLUMN public.user_word_ladder.created_at IS
    'When this sense was subscribed to the ladder. Added by TASK-741 so a '
    'per-calendar-day intake quota is expressible; until then intake is '
    'capped per call (LADDER_TOPUP_MAX_PER_CALL).';

CREATE INDEX IF NOT EXISTS idx_user_word_ladder_user_created
    ON public.user_word_ladder (user_id, created_at DESC);

COMMIT;
