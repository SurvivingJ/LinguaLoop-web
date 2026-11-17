-- Measure-word drill: cloze sentences for the Fill-in level. 2026-11-17 (TASK-998).
--
-- DATA FILL ONLY. Writes dim_classifier_noun_pairs.example_sentence, a
-- nullable text column that is NULL on every row today (measured 2026-11-17:
-- 0 of 2,664 language_id=1 rows non-empty) and that nothing else reads
-- (grep of services/, routes/, static/: only get_classifier_drill_session_v2
-- in migrations/task998_classifier_drill_levels.sql uses it).
-- No content is authored here: every sentence is copied verbatim from content
-- already in the database:
--   1. the judged ladder core sentences of Chinese senses
--      (word_assets.asset_type = 'prompt1_core', is_valid), preferred when the
--      sentence's target_word is the noun itself, then
--   2. sentences of active Chinese tests (test_sentences).
-- A sentence qualifies for pair (noun, classifier) when it
--   * is 6-60 characters (fits the phone screen),
--   * contains <numeral or 这/那/几/每/某/半/整><classifier><noun>,
--   * contains the classifier character exactly once (else the blank is given
--     away elsewhere in the sentence),
--   * does not continue the noun into a longer word (书 in 书包, 手 in 手套:
--     the noun + next 1 or 2 characters is neither a dim_vocabulary lemma nor
--     another noun of dim_classifier_noun_pairs),
-- and only single-character, non-个 classifiers and all-Han nouns are filled.
-- One sentence per pair: target_word match, then source, then shortest, then
-- text (deterministic).
--
-- Expected effect (measured 2026-11-17 with the SELECT between the CANDIDATES
-- markers): 661 rows, 551 distinct nouns, 91 classifiers (by tier of the
-- classifier: 176 tier 1, 306 tier 2, 128 tier 3, 51 tier 4). The DO block raises
-- (and so changes nothing) unless exactly that many rows are updated; the
-- reviewer re-measures and adjusts v_expected if the source content changed.
--
-- Note: scripts/build_classifier_dictionary.py deletes and re-inserts every
-- language_id=1 pair, which empties this column again; re-run this file after
-- a dictionary rebuild.
--
-- Rollback: migrations/task998_classifier_cloze_sentences_fill_rollback.sql
-- (sets the column back to NULL on exactly the filled pair ids).

DO $$
DECLARE
    v_expected constant integer := 661;
    v_updated  integer;
BEGIN
    WITH fill AS (
-- BEGIN CANDIDATES
        WITH src AS (
            -- Ladder core sentences (judged, one set per Chinese sense).
            SELECT s->>'text' AS txt, (s->>'target_word') AS target_word, 1 AS src_rank
            FROM word_assets wa
            CROSS JOIN LATERAL jsonb_array_elements(wa.content->'sentences') s
            WHERE wa.language_id = 1 AND wa.is_valid AND wa.asset_type = 'prompt1_core'
              AND jsonb_typeof(wa.content->'sentences') = 'array'
            UNION ALL
            -- Sentences of active Chinese tests.
            SELECT ts.l2_text, NULL, 2
            FROM test_sentences ts JOIN tests t ON t.id = ts.test_id
            WHERE t.language_id = 1 AND t.is_active
        ),
        sent AS (
            SELECT DISTINCT ON (txt) txt, target_word, src_rank
            FROM src
            WHERE txt IS NOT NULL AND char_length(txt) BETWEEN 6 AND 60
            ORDER BY txt, src_rank
        ),
        -- Every "<numeral/demonstrative><2-7 more characters>" run.
        hits AS (
            SELECT sent.txt, sent.target_word, sent.src_rank, m[1] AS tail
            FROM sent
            CROSS JOIN LATERAL regexp_matches(
                sent.txt,
                '[一二三四五六七八九十两几这那每某半整0-9０-９]([^一二三四五六七八九十两几这那每某半整0-9０-９，。！？、；：“”‘’（）《》\s]{2,7})',
                'g') AS m
        ),
        pairs AS (
            SELECT p.id AS pair_id, p.lemma_text, c.hanzi
            FROM dim_classifier_noun_pairs p
            JOIN dim_classifiers c ON c.id = p.classifier_id
            WHERE p.language_id = 1
              AND c.hanzi <> '个'
              AND char_length(c.hanzi) = 1
              AND p.lemma_text ~ '^[一-龥]+$'
              AND (p.example_sentence IS NULL OR p.example_sentence = '')
        ),
        matched AS (
            SELECT pr.pair_id, pr.lemma_text, pr.hanzi, h.txt, h.target_word, h.src_rank,
                   substr(h.tail, 2 + char_length(pr.lemma_text), 2) AS after2
            FROM pairs pr
            JOIN hits h ON left(h.tail, 1) = pr.hanzi
                       AND substr(h.tail, 2) LIKE pr.lemma_text || '%'
        ),
        guarded AS (
            SELECT m.*
            FROM matched m
            WHERE char_length(m.txt) - char_length(replace(m.txt, m.hanzi, '')) = 1
              AND NOT EXISTS (
                  SELECT 1 FROM dim_vocabulary v
                  WHERE v.language_id = 1
                    AND m.after2 <> ''
                    AND v.lemma IN (m.lemma_text || left(m.after2, 1), m.lemma_text || m.after2)
              )
              AND NOT EXISTS (
                  SELECT 1 FROM dim_classifier_noun_pairs p2
                  WHERE p2.language_id = 1
                    AND m.after2 <> ''
                    AND p2.lemma_text IN (m.lemma_text || left(m.after2, 1), m.lemma_text || m.after2)
              )
        )
        SELECT DISTINCT ON (pair_id) pair_id, txt AS example_sentence
        FROM guarded
        ORDER BY pair_id,
                 (target_word = lemma_text) IS TRUE DESC,
                 src_rank,
                 char_length(txt),
                 txt
-- END CANDIDATES
    )
    UPDATE dim_classifier_noun_pairs p
       SET example_sentence = f.example_sentence
      FROM fill f
     WHERE p.id = f.pair_id
       AND (p.example_sentence IS NULL OR p.example_sentence = '');

    GET DIAGNOSTICS v_updated = ROW_COUNT;
    IF v_updated <> v_expected THEN
        RAISE EXCEPTION 'task998 cloze fill: % rows would be updated, expected % - nothing changed',
            v_updated, v_expected;
    END IF;
    RAISE NOTICE 'task998 cloze fill: % rows updated', v_updated;
END $$;
