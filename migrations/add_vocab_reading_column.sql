-- Add dim_vocabulary.reading — dictionary-form reading in hiragana.
--
-- Used to find a token's *homophone family*: every dim_vocabulary row
-- pronounced the same way, regardless of which kanji (if any) each is
-- spelled with. dim_vocabulary.lemma alone is a flat text key and cannot
-- tell true homophones apart (城/白 both spell しろ; 為る is UniDic's shared
-- kanji spelling straddling する and 成る/なる) — see
-- services/vocabulary/processors/japanese.py and
-- services/vocabulary/kana_homophone_judge.py for the full mechanism this
-- column exists to support.
--
-- NULL for languages/entries not yet populated. Populated automatically
-- going forward at insert time (services/test_generation/orchestrator.py
-- _get_or_create_vocab_id); existing rows are backfilled by
-- scripts/backfill_vocab_reading.py.

ALTER TABLE dim_vocabulary ADD COLUMN IF NOT EXISTS reading TEXT;

CREATE INDEX IF NOT EXISTS idx_dim_vocabulary_reading
    ON dim_vocabulary (language_id, reading)
    WHERE reading IS NOT NULL;

COMMENT ON COLUMN dim_vocabulary.reading IS
    'Dictionary-form reading in hiragana (from UniDic kanaBase for Japanese). '
    'Homophone-family lookup key — see services/vocabulary/kana_homophone_judge.py. '
    'NULL for languages/entries not yet populated.';
