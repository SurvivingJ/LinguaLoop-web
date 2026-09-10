-- Calibration Phase 1, move 3 — the semantic distractor picker.
-- =============================================================================
-- PROBLEM
--   Calibration shows a word and four definitions. The existing picker,
--   public.get_distractors(), chooses the other three with `ORDER BY random()`.
--   Random options make the item trivially easy and measure almost nothing: a
--   learner who has never seen the word still scores by elimination, because two
--   of the three foils are about unrelated subject matter. To measure vocabulary
--   knowledge the distractors have to be both semantically NEAR and
--   difficulty-MATCHED.
--
--   get_distractors() is left exactly as it is — it is live, it has callers
--   (flashcards), and random foils are the right choice in the contexts that
--   already use it. This is a NEW function, not an overload of that one and not
--   an overload of nearest_senses() (which move 2 dropped as unfixably slow).
--
-- FIX
--   public.semantic_distractors() — an index-backed nearest-neighbour search over
--   dim_word_senses.embedding, filtered to the reader's definition language, with
--   the anchor's own word excluded, ranked by frequency proximity then cosine.
--
-- THE FIVE THINGS THIS GETS RIGHT
--
--   1. EXCLUDING THE ANCHOR'S vocab_id SIBLINGS, not merely the anchor row.
--      Load-bearing, and a direct consequence of the embedding recipe.
--      scripts/backfill_sense_embeddings.build_text() embeds "{lemma}: {definition}",
--      not the definition alone — deliberately, because short generic definitions
--      collapse onto one vector when embedded bare. Because the lemma is INSIDE
--      the embedded text, a word's own other rows (its other definition languages,
--      sense ranks, and simple/standard levels) are overwhelmingly its own nearest
--      neighbours. Filtering only `id <> p_sense_id` would hand back three more
--      definitions of 基本 as the three "distractors" for 基本. Every one correct.
--
--   2. A PER-LANGUAGE-PAIR COSINE FLOOR, not one global constant.
--      A single 0.35 floor is not one threshold — it is seven different thresholds
--      wearing the same number. Measured share of RANDOM, unrelated sense pairs
--      already clearing 0.35: 4.0% in en/en but 21.0% in ja/ja. At a flat 0.35 an
--      en/en item gets genuinely close foils while one ja/ja item in five gets a
--      foil no better than random. The defaults in dim_distractor_bands are the
--      p95 of each pair's measured unrelated distribution, so "above the floor"
--      means the same thing — roughly the top 5% of unrelated — in every pair.
--
--      The floor and ceiling are still PARAMETERS. The table only supplies the
--      default when the caller passes NULL, so re-tuning after response data
--      arrives is an UPDATE, not a redeploy.
--
--   3. FREQUENCY MATCHING THAT READS THE COLUMN CORRECTLY.
--      dim_vocabulary.frequency_rank is a ZIPF SCORE (observed 0.25–6.56, higher
--      = MORE common), not a rank. The name is a historical misnomer; see
--      services/vocabulary_ladder/deterministic/lexicon.py:266. Reading it as a
--      rank inverts every ordering that touches it, pairing the commonest anchors
--      with the rarest foils.
--
--      Frequency is a SOFT key and cosine is the HARD one — which is what "relax
--      the frequency band before relaxing the cosine floor" means in practice.
--      Candidates are tiered 0/1/2 by |zipf difference| and ordered by tier, then
--      cosine. A tier-2 (badly frequency-matched) candidate is therefore only
--      returned when there are not enough tier-0 and tier-1 ones: the band widens
--      by itself and the cosine floor is never lowered to compensate. A
--      frequency-mismatched but semantically tempting foil beats no foil at all.
--
--      1,003 of 11,795 dim_vocabulary rows (8.5%) have a NULL frequency_rank, and
--      so may the anchor. NULL is treated as tier 1 — usable, mildly
--      deprioritised — never as zipf 0, which would read as "maximally rare" and
--      is the same inversion bug in a different costume.
--
--   4. FILTERING TO definition_level = 'standard'.
--      Not cosmetic. At the 'simple' level the cross-language glosses frequently
--      restate the lemma verbatim, so the "definition" IS the prompt word:
--          ja word / zh definition, simple:  508 of 3,563  (14.3%)
--          zh word / ja definition, simple:  461 of 3,914  (11.8%)
--      — expected, since a simple Chinese gloss of a kanji-written Japanese word
--      is often the same characters. At 'standard' level the count is ZERO across
--      all seven pairs. Restricting to standard removes the "option identical to
--      the prompt" defect by construction rather than by special-casing it. (The
--      belt-and-braces guard against a foil whose definition equals the anchor's
--      lemma is kept, for callers that override p_definition_level.)
--
--   5. DROPPING MORPHOLOGICAL VARIANTS OF THE ANCHOR LEMMA.
--      Found by reading 1,400 sampled items rather than by reasoning. The vocab_id
--      exclusion in (1) catches a word's own rows, but precision/precise,
--      trade/trading, agriculture/agricultural and culture/cultural are SEPARATE
--      dim_vocabulary rows, so they sail straight through it — and their
--      definitions are frequently mutually correct. Measured before the guard:
--          en/en  68 of 600 returned foils (11.3%) were same-stem variants
--          zh/en, zh/zh, ja/ja, zh/ja  0.0%
--          ja/en 0.2%, ja/zh 0.3%  (loanword duplicates, e.g. パフォーマンス
--                                   vs パフォーマンス-performance)
--      This is an English-morphology problem, and the rule is self-limiting to
--      alphabetic scripts by construction: it needs a 4-character shared prefix
--      covering 60% of the shorter lemma, which CJK lemmas of 1-3 characters
--      essentially never reach. After the guard: 0 of 600 in every pair, with no
--      increase in short items (the pool has ~50 survivors for 3 slots).
--      Exposed as p_exclude_stem_variants so it can be turned off.
--
-- WHAT COSINE CANNOT DO — READ THIS BEFORE TRUSTING THE CEILING
--   The ceiling is meant to reject a foil that is really a second correct answer.
--   It cannot do that job cleanly, and the numbers say so. Same-word pairs — known
--   duplicates — have a median similarity of only 0.73–0.76, and 88–94% fall BELOW
--   0.88, so the original 0.88 ceiling caught roughly one duplicate in ten. Worse,
--   the two distributions overlap: the unrelated distribution's top (p99 0.43–0.56)
--   sits inside the same-word distribution's bottom (p5 0.33–0.57). There is
--   therefore NO cosine threshold that separates "unrelated" from "duplicate", and
--   no amount of tuning will produce one.
--
--   What that means operationally:
--     * The vocab_id exclusion (1) and the stem guard (5) — not the ceiling — are
--       what actually handle duplicates. They are exact, and that is why the
--       ceiling is allowed to be weak.
--     * DIFFERENT-word synonyms from an unrelated stem (a true also-correct answer,
--       e.g. 因子 against 要因, or 適正 against 妥当 at cosine 0.736) are NOT
--       screened by any of this and WILL get through. In the 1,400-item sample,
--       12–21% of returned foils sat at cosine >= 0.70, which is the band where
--       this risk lives. Catching them needs response data: an option that strong
--       learners pick as often as the key IS a second right answer, and no
--       embedding geometry will tell you that in advance.
--   The 0.75 defaults are therefore PROVISIONAL — a defensible start chosen to sit
--   just above the same-word median, not a measured optimum. The ceiling currently
--   binds on only ~0.2% of returned foils. Revisit once Calibration has logged
--   real answers.
--
-- KNOWN DATA DEFECT SURFACED BY THE SAMPLE (not fixed here)
--   Some en senses are keyed to a multiword idiom but stored under the bare lemma:
--   sense 14968 is lemma "hand" with the definition "Closely connected or
--   associated with something else" — that is "hand in hand". The picker then
--   correctly returns link / couple / connected, and the resulting item is broken
--   because the KEY does not define the prompt. That is a dictionary problem, not
--   a distractor problem, and it needs fixing upstream in dim_word_senses.
--
-- SAFETY
--   - Additive. Creates one table and two functions; changes nothing existing.
--   - Idempotent (CREATE TABLE IF NOT EXISTS / CREATE OR REPLACE / ON CONFLICT).
--   - SECURITY DEFINER with a pinned search_path and the same auth.role() gate
--     get_distractors() uses; RLS is enabled on both tables it reads.
--   - Read-only. No writes, no side effects.
--
-- APPLIED LIVE: 2026-09-08
-- =============================================================================


-- -----------------------------------------------------------------------------
-- The measured bands.
--
-- A table rather than constants in the function body for two reasons: the floors
-- are empirical and will be re-measured as the corpus grows, and keeping the
-- measurement that justifies each number next to the number is the only way the
-- next person can tell a tuned value from a guess.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.dim_distractor_bands (
    word_language_id        smallint NOT NULL REFERENCES public.dim_languages(id),
    definition_language_id  smallint NOT NULL REFERENCES public.dim_languages(id),

    -- Below cos_min a foil is unrelated — filler, not a distractor.
    cos_min                 real     NOT NULL,
    -- Above cos_max a foil is probably a near-duplicate. Weak by nature; see
    -- "WHAT COSINE CANNOT DO" above.
    cos_max                 real     NOT NULL,

    -- Provenance for cos_min. Measured over random unrelated sense pairs.
    unrelated_median        real,
    unrelated_p95           real,
    pct_above_0_35          real,
    measured_on             date,
    notes                   text,

    PRIMARY KEY (word_language_id, definition_language_id),
    CONSTRAINT dim_distractor_bands_band_ordered CHECK (cos_min < cos_max),
    CONSTRAINT dim_distractor_bands_range CHECK (
        cos_min >= 0 AND cos_min <= 1 AND cos_max >= 0 AND cos_max <= 1)
);

COMMENT ON TABLE public.dim_distractor_bands IS
  'Per (word language, definition language) cosine band for semantic_distractors(). cos_min is the p95 of that pair''s measured unrelated-pair distribution, so the floor means the same thing in every pair; a single global floor does not (4% of random en/en pairs clear 0.35 but 21% of ja/ja pairs do). cos_max is PROVISIONAL pending response data — cosine cannot cleanly separate duplicates from unrelated pairs, so the vocab_id exclusion and stem guard do that work instead.';

COMMENT ON COLUMN public.dim_distractor_bands.pct_above_0_35 IS
  'Share of random unrelated pairs that cleared the old global 0.35 floor. This is the evidence that one constant could not serve all seven pairs.';

INSERT INTO public.dim_distractor_bands (
    word_language_id, definition_language_id,
    cos_min, cos_max, unrelated_median, unrelated_p95, pct_above_0_35,
    measured_on, notes)
VALUES
    -- word / definition       floor  ceil  median  p95   %>0.35
    (2, 2,                      0.34, 0.75, 0.200, 0.34,  4.0, DATE '2026-09-08', 'en/en'),
    (3, 2,                      0.36, 0.75, 0.218, 0.358, 5.8, DATE '2026-09-08',
     'ja/en — measured 2026-09-08 AFTER the move-1 backfill. It could not be measured before: this pair had zero embeddings, which is what move 1 fixed. Close to en/en, as expected — the definitions are English either way, so the definition language dominates the floor, not the word language.'),
    (3, 1,                      0.38, 0.75, 0.240, 0.38,  7.7, DATE '2026-09-08', 'ja/zh'),
    (1, 3,                      0.39, 0.75, 0.244, 0.39,  9.7, DATE '2026-09-08', 'zh/ja'),
    (1, 2,                      0.40, 0.75, 0.255, 0.40, 12.7, DATE '2026-09-08', 'zh/en'),
    (1, 1,                      0.41, 0.75, 0.240, 0.41, 12.4, DATE '2026-09-08', 'zh/zh'),
    (3, 3,                      0.44, 0.75, 0.275, 0.44, 21.0, DATE '2026-09-08', 'ja/ja')
ON CONFLICT (word_language_id, definition_language_id) DO NOTHING;

ALTER TABLE public.dim_distractor_bands ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS dim_distractor_bands_read ON public.dim_distractor_bands;
CREATE POLICY dim_distractor_bands_read ON public.dim_distractor_bands
    FOR SELECT TO authenticated, service_role USING (true);

GRANT SELECT ON public.dim_distractor_bands TO authenticated, service_role;


-- -----------------------------------------------------------------------------
-- shared_prefix_len — supports the stem-variant guard (point 5 above).
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.shared_prefix_len(a text, b text)
RETURNS integer
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $function$
    SELECT coalesce(max(i), 0)
    FROM generate_series(0, least(length(a), length(b))) AS i
    WHERE left(lower(a), i) = left(lower(b), i);
$function$;

COMMENT ON FUNCTION public.shared_prefix_len(text, text) IS
  'Length of the common case-insensitive leading prefix of two strings. Used by semantic_distractors() to drop morphological variants of the anchor lemma (precision/precise, agriculture/agricultural), which are different vocab_id rows and so survive the sibling exclusion, but whose definitions are frequently also-correct.';


-- -----------------------------------------------------------------------------
-- semantic_distractors
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.semantic_distractors(
    p_sense_id               integer,
    p_word_language_id       smallint,
    p_definition_language_id smallint,
    p_count                  integer DEFAULT 3,
    p_cos_min                real    DEFAULT NULL,   -- NULL => dim_distractor_bands
    p_cos_max                real    DEFAULT NULL,   -- NULL => dim_distractor_bands
    p_freq_band              real    DEFAULT 1.0,    -- zipf points, tier-0 half-width
    p_definition_level       text    DEFAULT 'standard',
    p_pool                   integer DEFAULT 100,    -- index fetch depth
    p_exclude_stem_variants  boolean DEFAULT true
)
RETURNS TABLE(
    out_sense_id        integer,
    out_vocab_id        integer,
    out_lemma           text,
    out_definition      text,
    out_similarity      real,
    out_frequency       real,     -- zipf score, higher = more common
    out_frequency_delta real,     -- |zipf difference| from the anchor, NULL if unknown
    out_freq_tier       smallint  -- 0 in band, 1 loose or unknown, 2 out of band
)
LANGUAGE plpgsql
STABLE SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
-- NOTE: hnsw.ef_search is set with set_config() in the BODY, not with a
-- function-level `SET hnsw.ef_search TO ...` clause. The declarative form is
-- rejected on Supabase — "42501: permission denied to set parameter" — because
-- the role cannot pin an extension GUC into a function definition.
-- set_config(..., true) is transaction-local and is permitted.
--
-- Load-bearing, and the least obvious line in this file. The pool query filters
-- on both language columns, and those predicates have to be matched against a
-- PARTIAL index (idx_dws_emb_w<N>_d<N>). The planner can only use a partial index
-- when it can PROVE the query's predicate implies the index's — which it cannot do
-- when the value is a plan parameter rather than a constant. plpgsql switches a
-- function to a generic, parameterised plan after about five executions; at that
-- point the partial indexes would stop matching, the plan would fall back to a
-- sequential scan over every embedded sense, and we would be back to the exact
-- 57014 timeout that killed nearest_senses() — but only after the sixth call,
-- which is a horrible way to find out. Forcing a custom plan keeps the language
-- ids folded constants on every execution.
SET plan_cache_mode TO 'force_custom_plan'
AS $function$
DECLARE
    v_embedding   vector(1536);
    v_vocab_id    integer;
    v_lemma       text;
    v_zipf        real;
    v_cos_min     real;
    v_cos_max     real;
    v_pool        integer;
BEGIN
    IF auth.role() NOT IN ('authenticated', 'service_role') THEN
        RAISE EXCEPTION 'Authentication required' USING ERRCODE = '42501';
    END IF;

    -- Index fetch depth. Only definition_level is filtered after the index now
    -- (the pair-keyed indexes absorb both languages), so ~2x is enough: a pool of
    -- 100 leaves ~50 candidates for 3 slots. Capped at 200 — see the measurement
    -- in the move-2 migration for why a large pool is catastrophic, not merely
    -- wasteful (ef_search 400 cost 3,947 ms against 19 ms at 100).
    v_pool := LEAST(GREATEST(COALESCE(p_pool, 100), p_count * 10), 200);

    -- ef_search is the size of the candidate list the graph search keeps. It must
    -- be at least the LIMIT the index scan is asked for, or HNSW recall collapses
    -- and the "nearest" neighbours quietly stop being the nearest — a silent
    -- quality failure, not an error. Default is 40. Transaction-local.
    PERFORM set_config('hnsw.ef_search', v_pool::text, true);

    SELECT s.embedding, s.vocab_id, v.lemma, v.frequency_rank
      INTO v_embedding, v_vocab_id, v_lemma, v_zipf
      FROM dim_word_senses s
      JOIN dim_vocabulary v ON v.id = s.vocab_id
     WHERE s.id = p_sense_id;

    -- No anchor, or an anchor that was never embedded: return no rows rather than
    -- raising. The caller's fallback is get_distractors(); a Calibration item with
    -- random foils is worse than one with semantic foils but far better than an
    -- error, and an unembedded sense is an ordinary, recoverable state.
    IF v_embedding IS NULL THEN
        RETURN;
    END IF;

    -- Parameters win; the measured table is only the default.
    IF p_cos_min IS NULL OR p_cos_max IS NULL THEN
        SELECT b.cos_min, b.cos_max
          INTO v_cos_min, v_cos_max
          FROM dim_distractor_bands b
         WHERE b.word_language_id       = p_word_language_id
           AND b.definition_language_id = p_definition_language_id;
    END IF;

    -- The 0.40 / 0.75 last resort covers a pair with no measured row yet. It is
    -- the middle of the measured floors, not a considered value for that pair.
    v_cos_min := COALESCE(p_cos_min, v_cos_min, 0.40);
    v_cos_max := COALESCE(p_cos_max, v_cos_max, 0.75);

    RETURN QUERY
    WITH pool AS (
        -- Pure index scan. The WHERE clause here is EXACTLY the partial index
        -- predicate and nothing else — every additional filter belongs downstream,
        -- because a filter applied before the LIMIT makes the scan return fewer
        -- than v_pool rows rather than digging deeper for replacements.
        SELECT c.id,
               c.vocab_id,
               c.definition,
               c.definition_level,
               (1 - (c.embedding <=> v_embedding))::real AS similarity
          FROM dim_word_senses c
         WHERE c.word_language_id       = p_word_language_id
           AND c.definition_language_id = p_definition_language_id
           AND c.embedding IS NOT NULL
         ORDER BY c.embedding <=> v_embedding
         LIMIT v_pool
    ),
    filtered AS (
        SELECT p.id,
               p.vocab_id,
               v.lemma,
               p.definition,
               p.similarity,
               v.frequency_rank AS zipf,
               CASE
                   WHEN v_zipf IS NULL OR v.frequency_rank IS NULL THEN NULL
                   ELSE abs(v.frequency_rank - v_zipf)
               END::real AS zipf_delta
          FROM pool p
          JOIN dim_vocabulary v ON v.id = p.vocab_id
         WHERE p.vocab_id <> v_vocab_id                                  -- (1) siblings
           AND p.definition_level = p_definition_level                   -- (4) 'standard'
           AND p.similarity >= v_cos_min                                 -- (2) measured floor
           AND p.similarity <= v_cos_max
           -- An option that literally spells out the prompt word is a broken item.
           -- Redundant at definition_level='standard' (zero such rows corpus-wide)
           -- and kept for callers that override the level.
           AND btrim(p.definition) <> btrim(v_lemma)
           -- (5) morphological variants of the anchor lemma
           AND NOT (
                 p_exclude_stem_variants
                 AND shared_prefix_len(v.lemma, v_lemma) >= 4
                 AND shared_prefix_len(v.lemma, v_lemma)
                     >= 0.6 * least(length(v.lemma), length(v_lemma))
               )
    ),
    tiered AS (
        SELECT f.*,
               CASE                                                      -- (3) soft key
                   WHEN f.zipf_delta IS NULL              THEN 1::smallint
                   WHEN f.zipf_delta <= p_freq_band       THEN 0::smallint
                   WHEN f.zipf_delta <= p_freq_band * 2   THEN 1::smallint
                   ELSE                                        2::smallint
               END AS freq_tier
          FROM filtered f
    ),
    -- One option per WORD. Two senses of the same other-lemma would burn two of
    -- the three slots on a single distractor word.
    per_word AS (
        SELECT DISTINCT ON (t.vocab_id) t.*
          FROM tiered t
         ORDER BY t.vocab_id, t.freq_tier, t.similarity DESC
    ),
    -- ...and one option per definition TEXT. Two different words can carry a
    -- byte-identical gloss, which renders as the same option twice.
    per_text AS (
        SELECT DISTINCT ON (lower(btrim(w.definition))) w.*
          FROM per_word w
         ORDER BY lower(btrim(w.definition)), w.freq_tier, w.similarity DESC
    )
    SELECT r.id, r.vocab_id, r.lemma, r.definition,
           r.similarity, r.zipf, r.zipf_delta, r.freq_tier
      FROM per_text r
     ORDER BY r.freq_tier, r.similarity DESC      -- frequency relaxes before cosine
     LIMIT GREATEST(p_count, 1);
END;
$function$;

REVOKE EXECUTE ON FUNCTION public.semantic_distractors(
    integer, smallint, smallint, integer, real, real, real, text, integer, boolean) FROM anon;
GRANT EXECUTE ON FUNCTION public.semantic_distractors(
    integer, smallint, smallint, integer, real, real, real, text, integer, boolean)
    TO authenticated, service_role;


-- =============================================================================
-- Verification
-- =============================================================================
-- The sampling harness is scripts/dump_calibration_distractors.py. It dumps N
-- items per language pair AND counts the mechanical failure modes. Run it and
-- READ the output — "are these tempting?" is the only question that matters here
-- and it is not answerable by an assertion:
--   PYTHONIOENCODING=utf-8 python -m scripts.dump_calibration_distractors \
--       --per-pair 200 --out calibration_sample.txt
--
-- Result on 1,400 items, 2026-09-08 (200 per pair x 7 pairs):
--   sibling leaks 0 | definition==own lemma 0 | definition==anchor lemma 0
--   definition==anchor definition 0 | duplicate options 0 | short items 1
--   stem-variant foils 0 (was 68/600 in en/en before the guard)
--   mean cosine 0.595-0.632 per pair; floors bind exactly (ja/en min 0.360 vs
--   floor 0.36, en/en min 0.345 vs 0.34, ja/ja min 0.442 vs 0.44)
--
-- Note auth: this RPC raises 42501 unless auth.role() is authenticated or
-- service_role, so it cannot be smoke-tested through a bare SQL console that
-- leaves auth.role() NULL. Call it through the service-role client.
--
-- The sibling exclusion is doing its job — no returned vocab_id may equal the
-- anchor's:
--   SELECT count(*) FROM semantic_distractors(41404, 3::smallint, 2::smallint, 10) d
--    WHERE d.out_vocab_id = (SELECT vocab_id FROM dim_word_senses WHERE id = 41404);
--   -- expect 0
--
-- The plan has NOT degenerated to a sequential scan. Call it more than five times
-- in one session: without `plan_cache_mode = force_custom_plan` the sixth call
-- switches to a generic plan, loses the partial index and takes seconds or times
-- out. All ten should be tens of milliseconds.
--   SELECT count(*) FROM generate_series(1, 10) g,
--        LATERAL semantic_distractors(41404, 3::smallint, 2::smallint, 3);
-- =============================================================================
