-- TASK-778: repair Japanese headwords that carry UniDic's loanword gloss.
--
-- UniDic spells a loanword's lexeme as katakana + '-' + source word, with an
-- optional homograph gloss: ノブ-knob, ライト-light（光）, フェア-fair(見本市).
-- Before ede24bd4 (2026-08-26) JapaneseProcessor._orth_lemma returned that
-- string as the headword; the （光） variant kept leaking afterwards because the
-- gloss contains kanji. 344 ja dim_vocabulary rows (2,028 sense rows) were hit.
-- The code fix ships in the same change (services/vocabulary/processors/japanese.py).
--
-- What this does, in one transaction:
--   1. Normalise each dirty lemma: strip '-english' + optional gloss, drop
--      spaces (two were MeCab compounds: ボランティア-volunteer 活動).
--   2. 182 with no clean twin: rename in place.
--   3. 162 with a clean twin (ノブ-knob next to ノブ):
--      a. The twin's standard ja senses were hand-reviewed against the dirty
--         row's (157 pairs). All but the ids in lw_keep are paraphrases of the
--         dirty-origin sense, which is the one tests/exercises/knowledge rows
--         reference. Duplicate rank groups are deleted when nothing references
--         them, otherwise blocklisted.
--      b. Dirty senses are re-parented onto the twin (sense ids unchanged, so
--         token maps, vocab_sense_ids and FKs stay valid), ranks renumbered
--         densely with dirty-origin senses first.
--      c. Word-level references remapped; vocab metadata back-filled; dirty
--         vocab row deleted.
--   4. Quarantine fixes: un-blocklist senses whose only defect was the headword;
--      blocklist ル 53374 ("a katakana letter").
--   5. Six pure-English ja headwords (pesticides, vironment, ...) removed, or
--      blocklisted if anything references them.
--   6. Embeddings of moved/renamed senses nulled ("{lemma}: {definition}" text
--      changed); re-run backfill_sense_embeddings + calibration cache rebuild.
--   7. CHECK constraint so the gloss form can never be stored again.
--
-- APPLIED LIVE 2026-09-14. Must run as ONE transaction (psql -1 -f, or the
-- Supabase apply_migration tool): the ON COMMIT DROP temp tables vanish if a
-- client commits statement by statement, failing with
-- 'relation "lw_map" does not exist'. Re-running after success is a no-op
-- (lw_map is empty, the constraint add is guarded).

BEGIN;

-- ---------------------------------------------------------------- mapping
CREATE TEMP TABLE lw_map ON COMMIT DROP AS
SELECT v.id AS bad_id,
       v.lemma AS old_lemma,
       n.new_lemma,
       c.id AS clean_id
  FROM dim_vocabulary v
 CROSS JOIN LATERAL (
       SELECT replace(regexp_replace(v.lemma,
              '-[A-Za-z][A-Za-z''.-]*(?: [A-Za-z][A-Za-z''.-]*)*(?:（[^）]*）|\([^)]*\))?',
              '', 'g'), ' ', '') AS new_lemma) n
  LEFT JOIN dim_vocabulary c ON c.language_id = 3 AND c.lemma = n.new_lemma
 WHERE v.language_id = 3
   AND v.lemma ~ '-[A-Za-z]';

DO $$
DECLARE bad int; twins int; odd int; dupes int;
BEGIN
    SELECT count(*), count(clean_id) INTO bad, twins FROM lw_map;
    SELECT count(*) INTO odd FROM lw_map WHERE new_lemma = '' OR new_lemma ~ '[A-Za-z()（）]';
    SELECT count(*) INTO dupes FROM (SELECT new_lemma FROM lw_map GROUP BY 1 HAVING count(*) > 1) x;
    RAISE NOTICE 'TASK-778: % dirty lemmas, % with twin', bad, twins;
    IF odd > 0 OR dupes > 0 THEN
        RAISE EXCEPTION 'TASK-778: normalisation unsafe (odd=%, colliding targets=%)', odd, dupes;
    END IF;
END $$;

-- Twin senses reviewed as DISTINCT meanings (kept):
--   53078 スプリング coil spring        53070 パフォーマンス stage performance
--   53224 ケース container              53066 スポークン spoken-word performance
--   53528 ベル bell                     53154/53220 リブ rib (dirty 51716 is rib vault, blocklisted)
--   53374 ル (kept, blocklisted below)  53400 ワール whirl (already blocklisted)
CREATE TEMP TABLE lw_keep (sense_id int PRIMARY KEY) ON COMMIT DROP;
INSERT INTO lw_keep VALUES (53078),(53070),(53224),(53066),(53528),(53154),(53220),(53374),(53400);

-- Senses whose "{lemma}: {definition}" embedding text changes.
CREATE TEMP TABLE lw_moved ON COMMIT DROP AS
SELECT s.id FROM dim_word_senses s JOIN lw_map m ON m.bad_id = s.vocab_id;

-- ------------------------------------------------------------ 6. embeddings
-- FIRST, before any other sense UPDATE: dim_word_senses carries seven partial
-- HNSW indexes (442 MB, mostly cold), and every new tuple version with a
-- non-null vector is re-inserted into one. A NULL vector is not indexed, so
-- nulling up front makes the re-parent / rerank updates below cheap. The first
-- attempt without this hit the 120 s statement timeout. Covers the moved
-- senses (lemma text changed) and every sense of a twin vocab (reranked).
UPDATE dim_word_senses
   SET embedding = NULL
 WHERE embedding IS NOT NULL
   AND vocab_id IN (SELECT bad_id FROM lw_map UNION SELECT clean_id FROM lw_map WHERE clean_id IS NOT NULL);

-- Every sense id referenced by live data, collected once (array columns have
-- no GIN index, so a per-sense ANY() probe would rescan them each time).
CREATE TEMP TABLE lw_refs (sense_id int PRIMARY KEY) ON COMMIT DROP;
INSERT INTO lw_refs
SELECT DISTINCT id FROM (
          SELECT word_sense_id AS id FROM exercises
    UNION SELECT sense_id FROM word_assets
    UNION SELECT sense_id FROM user_vocabulary_knowledge
    UNION SELECT sense_id FROM user_flashcards
    UNION SELECT sense_id FROM user_word_ladder
    UNION SELECT sense_id FROM user_exercise_history
    UNION SELECT sense_id FROM exercise_attempts
    UNION SELECT sense_id FROM word_quiz_results
    UNION SELECT sense_id FROM generation_queue
    UNION SELECT sense_id FROM vocabulary_review_queue
    UNION SELECT sense_id FROM pack_key_words
    UNION SELECT noun_sense_id FROM dim_classifier_noun_pairs
    UNION SELECT noun_sense_id FROM dim_counter_noun_pairs
    UNION SELECT anchor_sense_id FROM calibration_responses
    UNION SELECT chosen_sense_id FROM calibration_responses
    UNION SELECT sense_id FROM calibration_response_options
    UNION SELECT unnest(vocab_sense_ids) FROM tests
    UNION SELECT unnest(sense_ids) FROM questions
    UNION SELECT unnest(vocab_sense_ids) FROM mysteries
    UNION SELECT unnest(sense_ids) FROM mystery_questions
) r WHERE id IS NOT NULL;

-- ------------------------------------------------- 3a. duplicate twin senses
CREATE TEMP TABLE lw_drop_group ON COMMIT DROP AS
SELECT DISTINCT s.vocab_id, s.sense_rank
  FROM dim_word_senses s
  JOIN lw_map m ON m.clean_id = s.vocab_id
 WHERE s.definition_level = 'standard'
   AND s.definition_language_id = 3
   AND s.id NOT IN (SELECT sense_id FROM lw_keep)
   AND EXISTS (SELECT 1 FROM dim_word_senses d
                WHERE d.vocab_id = m.bad_id
                  AND d.definition_level = 'standard'
                  AND d.definition_language_id = 3);

CREATE TEMP TABLE lw_drop ON COMMIT DROP AS
SELECT s.id, (s.id IN (SELECT sense_id FROM lw_refs)) AS referenced
  FROM dim_word_senses s
  JOIN lw_drop_group g USING (vocab_id, sense_rank);

INSERT INTO calibration_anchor_blocklist (sense_id, reason)
SELECT id, 'TASK-778 duplicate of a merged loanword sense (headword was UniDic ''カタカナ-english'' form); referenced, so quarantined rather than deleted'
  FROM lw_drop WHERE referenced
ON CONFLICT (sense_id) DO NOTHING;

-- Derived calibration tables: drop rows for deleted senses (rebuilt afterwards).
DELETE FROM calibration_distractor_cache
 WHERE sense_id IN (SELECT id FROM lw_drop WHERE NOT referenced)
    OR anchor_sense_id IN (SELECT id FROM lw_drop WHERE NOT referenced);
DELETE FROM calibration_anchor_pool
 WHERE sense_id IN (SELECT id FROM lw_drop WHERE NOT referenced);
DELETE FROM dim_word_senses
 WHERE id IN (SELECT id FROM lw_drop WHERE NOT referenced);

-- ------------------------------------------------------ 2. rename, no twin
UPDATE dim_vocabulary v
   SET lemma = m.new_lemma
  FROM lw_map m
 WHERE v.id = m.bad_id AND m.clean_id IS NULL;

-- --------------------------------------------------- 3b. re-parent + rerank
UPDATE dim_word_senses s
   SET vocab_id = m.clean_id,
       sense_rank = s.sense_rank + 100000          -- clear of every twin rank
  FROM lw_map m
 WHERE s.vocab_id = m.bad_id AND m.clean_id IS NOT NULL;

CREATE TEMP TABLE lw_rank ON COMMIT DROP AS
SELECT g.vocab_id, g.sense_rank AS old_rank,
       row_number() OVER (PARTITION BY g.vocab_id
                          ORDER BY (g.sense_rank >= 100000) DESC, g.sense_rank) AS new_rank
  FROM (SELECT DISTINCT s.vocab_id, s.sense_rank
          FROM dim_word_senses s
         WHERE s.vocab_id IN (SELECT clean_id FROM lw_map WHERE clean_id IS NOT NULL)) g;

UPDATE dim_word_senses s SET sense_rank = -r.new_rank
  FROM lw_rank r WHERE s.vocab_id = r.vocab_id AND s.sense_rank = r.old_rank;
UPDATE dim_word_senses SET sense_rank = -sense_rank
 WHERE vocab_id IN (SELECT vocab_id FROM lw_rank) AND sense_rank < 0;

-- ----------------------------------------- 3c. word-level refs + metadata
UPDATE calibration_anchor_pool x SET vocab_id = m.clean_id
  FROM lw_map m WHERE x.vocab_id = m.bad_id AND m.clean_id IS NOT NULL;
UPDATE calibration_distractor_cache x SET vocab_id = m.clean_id
  FROM lw_map m WHERE x.vocab_id = m.bad_id AND m.clean_id IS NOT NULL;
UPDATE calibration_response_options x SET vocab_id = m.clean_id
  FROM lw_map m WHERE x.vocab_id = m.bad_id AND m.clean_id IS NOT NULL;
UPDATE calibration_responses x SET anchor_vocab_id = m.clean_id
  FROM lw_map m WHERE x.anchor_vocab_id = m.bad_id AND m.clean_id IS NOT NULL;
UPDATE vocabulary_review_queue x SET vocab_id = m.clean_id
  FROM lw_map m WHERE x.vocab_id = m.bad_id AND m.clean_id IS NOT NULL;
UPDATE mysteries y
   SET target_vocab_ids = (
       SELECT array_agg(coalesce(m.clean_id, u.x) ORDER BY u.ord)
         FROM unnest(y.target_vocab_ids) WITH ORDINALITY u(x, ord)
         LEFT JOIN lw_map m ON m.bad_id = u.x AND m.clean_id IS NOT NULL)
 WHERE y.target_vocab_ids && (SELECT array_agg(bad_id) FROM lw_map WHERE clean_id IS NOT NULL);

UPDATE dim_vocabulary c
   SET reading          = coalesce(c.reading, b.reading),
       part_of_speech   = coalesce(c.part_of_speech, b.part_of_speech),
       frequency_rank   = coalesce(c.frequency_rank, b.frequency_rank),
       level_tag        = coalesce(c.level_tag, b.level_tag),
       semantic_class   = coalesce(c.semantic_class, b.semantic_class),
       semantic_class_confidence = CASE WHEN c.semantic_class IS NULL
                                        THEN b.semantic_class_confidence
                                        ELSE c.semantic_class_confidence END
  FROM lw_map m JOIN dim_vocabulary b ON b.id = m.bad_id
 WHERE c.id = m.clean_id;

DELETE FROM dim_vocabulary WHERE id IN (SELECT bad_id FROM lw_map WHERE clean_id IS NOT NULL);

-- ------------------------------------------------------ 4. quarantine fixes
-- Quarantined only for the broken headword, which is now fixed:
--   52312 クラム (was クラム-clam; the crumb definition is correct for クラム)
--   39237/46654/46655 コミュニティー作り, 39223/46355/46358 ボランティア活動
-- Un-blocklisting does not reactivate retired exercises (by design, TASK-767).
DELETE FROM calibration_anchor_blocklist
 WHERE sense_id IN (52312, 39237, 46654, 46655, 39223, 46355, 46358);

INSERT INTO calibration_anchor_blocklist (sense_id, reason) VALUES
  (53374, 'TASK-778 definition describes the katakana letter ル, not a word')
ON CONFLICT (sense_id) DO NOTHING;

-- ------------------------------------------------ 5. pure-English ja lemmas
CREATE TEMP TABLE lw_en ON COMMIT DROP AS
SELECT v.id AS vocab_id FROM dim_vocabulary v
 WHERE v.language_id = 3
   AND v.lemma IN ('intermittency', 'lab', 'organisers', 'pesticide', 'pesticides', 'vironment');

CREATE TEMP TABLE lw_en_sense ON COMMIT DROP AS
SELECT s.id, (s.id IN (SELECT sense_id FROM lw_refs)) AS referenced
  FROM dim_word_senses s WHERE s.vocab_id IN (SELECT vocab_id FROM lw_en);

INSERT INTO calibration_anchor_blocklist (sense_id, reason)
SELECT id, 'TASK-778 English word stored as a Japanese headword; referenced, so quarantined rather than deleted'
  FROM lw_en_sense WHERE referenced
ON CONFLICT (sense_id) DO NOTHING;

DELETE FROM calibration_distractor_cache
 WHERE sense_id IN (SELECT id FROM lw_en_sense) OR anchor_sense_id IN (SELECT id FROM lw_en_sense);
DELETE FROM calibration_anchor_pool WHERE sense_id IN (SELECT id FROM lw_en_sense);
DELETE FROM vocabulary_review_queue
 WHERE vocab_id IN (SELECT vocab_id FROM lw_en)
   AND NOT EXISTS (SELECT 1 FROM lw_en_sense WHERE referenced);
DELETE FROM dim_vocabulary
 WHERE id IN (SELECT vocab_id FROM lw_en)
   AND NOT EXISTS (SELECT 1 FROM dim_word_senses s JOIN lw_en_sense e ON e.id = s.id
                    WHERE s.vocab_id = dim_vocabulary.id AND e.referenced);

-- ------------------------------------------------------------- 7. guardrail
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                    WHERE conrelid = 'dim_vocabulary'::regclass
                      AND conname = 'chk_ja_lemma_no_loanword_gloss') THEN
        ALTER TABLE dim_vocabulary
          ADD CONSTRAINT chk_ja_lemma_no_loanword_gloss
          CHECK (language_id <> 3 OR lemma !~ '-[A-Za-z]');
    END IF;
END $$;

-- ------------------------------------------------------------ postconditions
DO $$
DECLARE left_dirty int; orphan_moved int; gaps int;
BEGIN
    SELECT count(*) INTO left_dirty FROM dim_vocabulary WHERE language_id = 3 AND lemma ~ '[A-Za-z]' AND lemma ~ '[ぁ-ヿ一-鿿]';
    SELECT count(*) INTO orphan_moved FROM lw_moved m LEFT JOIN dim_word_senses s ON s.id = m.id WHERE s.id IS NULL;
    SELECT count(*) INTO gaps FROM (
        SELECT vocab_id FROM dim_word_senses
         WHERE vocab_id IN (SELECT vocab_id FROM lw_rank)
         GROUP BY vocab_id HAVING max(sense_rank) <> count(DISTINCT sense_rank) OR min(sense_rank) <> 1) x;
    RAISE NOTICE 'TASK-778: mixed-script ja lemmas left=%, moved senses lost=%, rank gaps=%', left_dirty, orphan_moved, gaps;
    IF left_dirty > 0 OR orphan_moved > 0 OR gaps > 0 THEN
        RAISE EXCEPTION 'TASK-778 postcondition failed';
    END IF;
END $$;

COMMIT;
