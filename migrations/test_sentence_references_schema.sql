-- ============================================================================
-- test_sentence_references_schema.sql — sentence-level L1 references (TASK-901)
-- Date: 2026-10-30
-- Spec: wiki/features/test-sentence-references.tech.md ("Database Impact")
--       wiki/decisions/ADR-037-sentence-level-l1-references.md
--       wiki/decisions/ADR-034-no-client-db-writes.md
--
-- Creates:
--   * test_sentences            — one row per sentence of an active test's
--                                 transcript (half-open char span + token span).
--   * test_sentence_references  — L1 reference translations per sentence, with
--                                 provenance and the reviewer's verdict; at most
--                                 one *active* row per (sentence, L1).
-- Alters:
--   * dt_passage                — sentence_start / sentence_end (inclusive
--                                 test_sentences.idx range) + partial unique
--                                 index so a range is created once and reused.
--
-- Triggers:
--   * test_sentences_check_l2_text    — l2_text must equal the transcript
--                                       substring the span points at.
--   * test_sentence_references_check_l1_script
--                                     — l1_text may not contain the L2 script
--                                       of the sentence's test: Han for zh,
--                                       Han or kana for ja (dim_languages.
--                                       language_code, ids 1 = zh, 3 = ja).
--
-- Conventions mirrored from dual_translation_groundwork.sql: bigint identity
-- PKs, created_at timestamptz DEFAULT now(). l1_language_id is smallint like
-- dim_languages.id (the dt_* tables use integer; both FK shapes are valid).
--
-- One deliberate reading of the spec: the tech page lists token_start /
-- token_end as NOT NULL *and* "NULL when the test has no token map". They are
-- nullable here with a CHECK that both are null or both are set — 31 active
-- tests have no vocab_token_map, and TASK-902 must still segment them.
--
-- Security (ADR-034 / TASK-881): RLS on, every client privilege revoked, no
-- policies — read and written by Flask (service role) only. Trigger functions
-- are not SECURITY DEFINER; the REVOKE/GRANT is repeated so the file is
-- self-describing.
--
-- Idempotent: safe to re-run (IF NOT EXISTS / DROP TRIGGER IF EXISTS).
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/test_sentence_references_schema.sql
--   then tests/sql/test_sentence_references.sql (rollback-only).
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. test_sentences
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.test_sentences (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    test_id          uuid     NOT NULL REFERENCES public.tests(id) ON DELETE CASCADE,
    idx              smallint NOT NULL CHECK (idx >= 0),
    char_start       integer  NOT NULL CHECK (char_start >= 0),
    char_end         integer  NOT NULL,
    token_start      integer,
    token_end        integer,
    l2_text          text     NOT NULL CHECK (length(l2_text) > 0),
    transcript_hash  text     NOT NULL,
    created_at       timestamptz DEFAULT now(),
    CONSTRAINT test_sentences_test_id_idx_key UNIQUE (test_id, idx),
    CONSTRAINT test_sentences_char_span_chk  CHECK (char_end > char_start),
    CONSTRAINT test_sentences_token_span_chk CHECK (
        (token_start IS NULL AND token_end IS NULL)
        OR (token_start IS NOT NULL AND token_end IS NOT NULL
            AND token_start >= 0 AND token_end > token_start)
    )
);

COMMENT ON TABLE public.test_sentences IS
    'One row per sentence of a test transcript (TASK-901/902). char_* is a '
    'half-open code-point span in tests.transcript; token_* is a half-open span '
    'in tests.vocab_token_map (NULL when the test has no token map). l2_text '
    'equals the transcript substring (enforced by trigger). transcript_hash is '
    'the sha256 of the transcript at segmentation time; a mismatch with '
    'tests.transcript_hash means the rows are stale.';

CREATE INDEX IF NOT EXISTS idx_test_sentences_test_idx
    ON public.test_sentences (test_id, idx);

ALTER TABLE public.test_sentences ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.test_sentences FROM PUBLIC, anon, authenticated;
GRANT ALL ON public.test_sentences TO service_role;

-- l2_text must be exactly the span of the transcript it claims to be.
-- substr() on text counts characters (code points), matching Python slicing.
CREATE OR REPLACE FUNCTION public.test_sentences_check_l2_text()
RETURNS trigger LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
    v_transcript text;
BEGIN
    SELECT t.transcript INTO v_transcript FROM public.tests t WHERE t.id = NEW.test_id;
    IF v_transcript IS NULL THEN
        RAISE EXCEPTION 'test_sentences: test % has no transcript', NEW.test_id
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.char_end > length(v_transcript) THEN
        RAISE EXCEPTION 'test_sentences: span [%, %) exceeds transcript length % for test %',
            NEW.char_start, NEW.char_end, length(v_transcript), NEW.test_id
            USING ERRCODE = 'check_violation';
    END IF;
    IF substr(v_transcript, NEW.char_start + 1, NEW.char_end - NEW.char_start) <> NEW.l2_text THEN
        RAISE EXCEPTION 'test_sentences: l2_text does not match transcript[%:%] for test %',
            NEW.char_start, NEW.char_end, NEW.test_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

REVOKE ALL ON FUNCTION public.test_sentences_check_l2_text() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.test_sentences_check_l2_text() TO service_role;

DROP TRIGGER IF EXISTS test_sentences_check_l2_text ON public.test_sentences;
CREATE TRIGGER test_sentences_check_l2_text
    BEFORE INSERT OR UPDATE OF test_id, char_start, char_end, l2_text
    ON public.test_sentences
    FOR EACH ROW EXECUTE FUNCTION public.test_sentences_check_l2_text();

-- ----------------------------------------------------------------------------
-- 2. test_sentence_references
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.test_sentence_references (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sentence_id      bigint   NOT NULL REFERENCES public.test_sentences(id) ON DELETE CASCADE,
    l1_language_id   smallint NOT NULL REFERENCES public.dim_languages(id),
    l1_text          text     NOT NULL CHECK (length(l1_text) > 0),
    author_model     text     NOT NULL,
    prompt_version   text     NOT NULL,
    arm              text     CHECK (arm IS NULL OR arm IN ('sentencewise', 'aligned')),
    reviewer_model   text,
    review_verdict   text     NOT NULL DEFAULT 'pending'
                     CHECK (review_verdict IN ('pending', 'pass', 'rewritten', 'fail')),
    tightness        real     CHECK (tightness IS NULL OR (tightness >= 0 AND tightness <= 1)),
    entailment_ok    boolean,
    is_active        boolean  NOT NULL DEFAULT false,
    run_id           text,
    created_at       timestamptz DEFAULT now()
);

COMMENT ON TABLE public.test_sentence_references IS
    'L1 reference translation of one test_sentences row (TASK-901, ADR-037). '
    'author_model / prompt_version / run_id are provenance of the authoring '
    'subagent; reviewer_model, review_verdict, tightness (Tier 0 similarity of '
    'the blind back-translation to l2_text, 0-1) and entailment_ok come from the '
    'review skill. At most one is_active row per (sentence_id, l1_language_id). '
    'l1_text may not contain the L2 script of the sentence''s test (trigger).';

-- At most one active reference per (sentence, L1).
CREATE UNIQUE INDEX IF NOT EXISTS uq_test_sentence_references_active
    ON public.test_sentence_references (sentence_id, l1_language_id)
    WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_test_sentence_references_sentence
    ON public.test_sentence_references (sentence_id, l1_language_id);

CREATE INDEX IF NOT EXISTS idx_test_sentence_references_run
    ON public.test_sentence_references (run_id)
    WHERE run_id IS NOT NULL;

ALTER TABLE public.test_sentence_references ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.test_sentence_references FROM PUBLIC, anon, authenticated;
GRANT ALL ON public.test_sentence_references TO service_role;

-- l1_text must not leak the L2 script. The script is derived from the test's
-- language through dim_languages.language_code (1 = zh, 2 = en, 3 = ja), so a
-- future language only needs a new WHEN branch. Han covers the CJK Unified
-- Ideographs block, Extension A, the compatibility block and Extension B;
-- kana covers hiragana, katakana, the phonetic extensions and halfwidth
-- katakana. English L2 has no script check (Latin letters are legitimate in
-- any L1 here).
CREATE OR REPLACE FUNCTION public.test_sentence_references_check_l1_script()
RETURNS trigger LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
    v_l2_code  text;
    v_han      constant text := '[一-鿿㐀-䶿豈-﫿\U00020000-\U0002A6DF]';
    v_kana     constant text := '[぀-ゟ゠-ヿㇰ-ㇿｦ-ﾟ]';
    v_pattern  text;
BEGIN
    SELECT l.language_code INTO v_l2_code
      FROM public.test_sentences s
      JOIN public.tests t ON t.id = s.test_id
      JOIN public.dim_languages l ON l.id = t.language_id
     WHERE s.id = NEW.sentence_id;

    IF v_l2_code IS NULL THEN
        RAISE EXCEPTION 'test_sentence_references: sentence % has no test / language', NEW.sentence_id
            USING ERRCODE = 'foreign_key_violation';
    END IF;

    v_pattern := CASE v_l2_code
        WHEN 'zh' THEN v_han
        WHEN 'ja' THEN v_han || '|' || v_kana
        ELSE NULL
    END;

    IF v_pattern IS NOT NULL AND NEW.l1_text ~ v_pattern THEN
        RAISE EXCEPTION 'test_sentence_references: l1_text contains the L2 (%) script: %',
            v_l2_code, left(NEW.l1_text, 80)
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

REVOKE ALL ON FUNCTION public.test_sentence_references_check_l1_script() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.test_sentence_references_check_l1_script() TO service_role;

DROP TRIGGER IF EXISTS test_sentence_references_check_l1_script ON public.test_sentence_references;
CREATE TRIGGER test_sentence_references_check_l1_script
    BEFORE INSERT OR UPDATE OF sentence_id, l1_text
    ON public.test_sentence_references
    FOR EACH ROW EXECUTE FUNCTION public.test_sentence_references_check_l1_script();

-- ----------------------------------------------------------------------------
-- 3. dt_passage — inclusive sentence index range into test_sentences
-- ----------------------------------------------------------------------------

ALTER TABLE public.dt_passage
    ADD COLUMN IF NOT EXISTS sentence_start smallint NULL,
    ADD COLUMN IF NOT EXISTS sentence_end   smallint NULL;

COMMENT ON COLUMN public.dt_passage.sentence_start IS
    'Inclusive first test_sentences.idx of this passage within source_ref_id '
    '(TASK-901). NULL on rows created before sentence references existed.';
COMMENT ON COLUMN public.dt_passage.sentence_end IS
    'Inclusive last test_sentences.idx of this passage within source_ref_id '
    '(TASK-901). NULL on rows created before sentence references existed.';

-- Both set or both NULL, and a non-empty range. NOT VALID so the existing
-- (all-NULL) rows are not scanned under the exclusive lock; validated after.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'dt_passage_sentence_range_chk'
           AND conrelid = 'public.dt_passage'::regclass
    ) THEN
        ALTER TABLE public.dt_passage
            ADD CONSTRAINT dt_passage_sentence_range_chk CHECK (
                (sentence_start IS NULL AND sentence_end IS NULL)
                OR (sentence_start IS NOT NULL AND sentence_end IS NOT NULL
                    AND sentence_start >= 0 AND sentence_end >= sentence_start)
            ) NOT VALID;
    END IF;
END $$;

-- A given sentence range of a test is extracted once and reused.
CREATE UNIQUE INDEX IF NOT EXISTS uq_dt_passage_sentence_range
    ON public.dt_passage (source_ref_id, sentence_start, sentence_end)
    WHERE sentence_start IS NOT NULL AND sentence_end IS NOT NULL;

COMMIT;

-- Outside the exclusive-lock window (migrations/CLAUDE.md): a no-op re-run is
-- fine, VALIDATE on an already-valid constraint returns immediately.
ALTER TABLE public.dt_passage VALIDATE CONSTRAINT dt_passage_sentence_range_chk;
