-- ============================================================================
-- standardise_part_of_speech.sql — one part-of-speech vocabulary in dim_vocabulary
-- Date: 2026-11-11
--
-- dim_vocabulary.part_of_speech mixed tagsets: the tokenizer's own tag was
-- stored when a word was created (jieba n/nr/v/vn, UniDic 名詞/形状詞, spaCy
-- NOUN/ADJ) next to the sense generator's standard names (noun, verb, …) and
-- Chinese labels (名词). Live 2026-11-11: zh 62% standard, en 11%, ja 6%.
--
-- Standard list = the sense generator's legend (services/vocabulary/
-- sense_generator.py POS_LEGENDS; services/vocabulary/pos.py CANONICAL_POS).
--   * part_of_speech_raw  keeps the original tag (exercise-authoring prompts
--                         that validate against per-language lists still get
--                         it as their hint: services/vocabulary/pos.py pos_hint)
--   * normalize_pos(text) SQL twin of services.vocabulary.pos.normalize_pos
--                         (generated from the same table; tests/fixtures/
--                         lexicon/cases.json "normalize_pos")
--   * trigger             normalises every INSERT/UPDATE of part_of_speech and
--                         keeps the original; writers send the tagger's tag
--                         unchanged (word_resolver, backfill_vocab, asset
--                         pipeline, admin), so the trigger is the one place
--                         the mapping runs. For Chinese only, the sense
--                         generator writes its own label over jieba's guess
--                         (ja UniDic / en spaCy tags are kept; there it only
--                         fills blanks).
--   * backfill            one UPDATE over the non-standard rows
--   * CHECK               added NOT VALID, validated after the backfill commits
--                         (migrations/CLAUDE.md: keep the exclusive lock short)
-- ============================================================================

BEGIN;

ALTER TABLE public.dim_vocabulary ADD COLUMN IF NOT EXISTS part_of_speech_raw text;
COMMENT ON COLUMN public.dim_vocabulary.part_of_speech_raw IS
    'The tagger''s original part-of-speech tag (jieba / UniDic / spaCy / model label) when it '
    'differs from the standard part_of_speech. See migrations/standardise_part_of_speech.sql.';

CREATE OR REPLACE FUNCTION public.pos_tag_lookup(t text)
RETURNS text
LANGUAGE sql
IMMUTABLE
SET search_path = public, pg_temp
AS $$
    -- Generated from services/vocabulary/pos.py _TAGS; keep in step.
    SELECT CASE
        WHEN t = ANY (ARRAY['noun','n','nr','ns','nt','nz','nw','ng','nrt','nrfg','vn','an','f','s','t','j','propn','proper noun','名词','名詞','普通名詞','固有名詞']) THEN 'noun'
        WHEN t = ANY (ARRAY['verb','v','vd','vg','vi','vq','动词','動詞','情态动词']) THEN 'verb'
        WHEN t = ANY (ARRAY['adjective','adj','a','ag','b','z','形容词','形容詞','形状詞']) THEN 'adjective'
        WHEN t = ANY (ARRAY['adverb','adv','d','dg','ad','副词','副詞']) THEN 'adverb'
        WHEN t = ANY (ARRAY['pronoun','pron','r','rr','rz','rg','代词','代名詞']) THEN 'pronoun'
        WHEN t = ANY (ARRAY['preposition','p','adp','介词']) THEN 'preposition'
        WHEN t = ANY (ARRAY['conjunction','c','cconj','sconj','连词','接続詞']) THEN 'conjunction'
        WHEN t = ANY (ARRAY['particle','u','uj','ul','uz','ug','uv','ud','y','part','助词','助詞']) THEN 'particle'
        WHEN t = ANY (ARRAY['measure_word','measure word','classifier','q','量词','助数詞']) THEN 'measure_word'
        WHEN t = ANY (ARRAY['idiom','i','成语']) THEN 'idiom'
        WHEN t = ANY (ARRAY['phrase','expression','l','惯用语']) THEN 'phrase'
        WHEN t = ANY (ARRAY['numeral','m','mq','num','数词','数詞']) THEN 'numeral'
        WHEN t = ANY (ARRAY['auxiliary','aux','助動詞']) THEN 'auxiliary'
        WHEN t = ANY (ARRAY['adnominal','連体詞']) THEN 'adnominal'
        WHEN t = ANY (ARRAY['determiner','det']) THEN 'determiner'
        WHEN t = ANY (ARRAY['interjection','intj','e','o','叹词','感動詞']) THEN 'interjection'
        WHEN t = ANY (ARRAY['other','x','sym','punct','h','k','eng','unknown','接頭辞','接尾辞','記号','補助記号']) THEN 'other'
        ELSE NULL
    END
$$;

CREATE OR REPLACE FUNCTION public.normalize_pos(p_tag text)
RETURNS text
LANGUAGE sql
IMMUTABLE
SET search_path = public, pg_temp
AS $$
    -- None/blank -> NULL; subdivided UniDic tags (名詞-普通名詞-一般, 名詞,普通名詞)
    -- use their head; anything unrecognised -> 'other'.
    SELECT CASE
        WHEN p_tag IS NULL OR btrim(p_tag) = '' THEN NULL
        ELSE COALESCE(
            public.pos_tag_lookup(lower(btrim(p_tag))),
            public.pos_tag_lookup(lower(btrim(split_part(replace(btrim(p_tag), ',', '-'), '-', 1)))),
            'other')
    END
$$;

CREATE OR REPLACE FUNCTION public.trg_dim_vocabulary_normalize_pos()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
    v text;
BEGIN
    IF NEW.part_of_speech IS NULL THEN
        RETURN NEW;
    END IF;
    v := public.normalize_pos(NEW.part_of_speech);
    IF v IS DISTINCT FROM NEW.part_of_speech THEN
        IF v IS NOT NULL THEN
            NEW.part_of_speech_raw := btrim(NEW.part_of_speech);
        END IF;
        NEW.part_of_speech := v;
    END IF;
    RETURN NEW;
END
$$;

REVOKE ALL ON FUNCTION public.pos_tag_lookup(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.pos_tag_lookup(text) TO service_role;
REVOKE ALL ON FUNCTION public.normalize_pos(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.normalize_pos(text) TO service_role;
REVOKE ALL ON FUNCTION public.trg_dim_vocabulary_normalize_pos() FROM PUBLIC, anon, authenticated;

-- Backfill: one pass over the non-standard rows (keeps the original tag).
UPDATE public.dim_vocabulary
   SET part_of_speech_raw = NULLIF(btrim(part_of_speech), ''),
       part_of_speech     = public.normalize_pos(part_of_speech)
 WHERE part_of_speech IS NOT NULL
   AND part_of_speech IS DISTINCT FROM public.normalize_pos(part_of_speech);

DROP TRIGGER IF EXISTS trg_dim_vocabulary_normalize_pos ON public.dim_vocabulary;
CREATE TRIGGER trg_dim_vocabulary_normalize_pos
    BEFORE INSERT OR UPDATE OF part_of_speech ON public.dim_vocabulary
    FOR EACH ROW EXECUTE FUNCTION public.trg_dim_vocabulary_normalize_pos();

ALTER TABLE public.dim_vocabulary DROP CONSTRAINT IF EXISTS dim_vocabulary_part_of_speech_check;
ALTER TABLE public.dim_vocabulary ADD CONSTRAINT dim_vocabulary_part_of_speech_check
    CHECK (part_of_speech IS NULL OR part_of_speech = ANY (ARRAY['noun','verb','adjective','adverb','pronoun','preposition','conjunction','particle','measure_word','idiom','phrase','numeral','auxiliary','adnominal','determiner','interjection','other'])) NOT VALID;

COMMIT;

-- Outside the transaction: scans under SHARE UPDATE EXCLUSIVE (reads/writes continue).
ALTER TABLE public.dim_vocabulary VALIDATE CONSTRAINT dim_vocabulary_part_of_speech_check;
