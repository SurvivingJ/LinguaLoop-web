-- Assert the zh/ja prompt-rewrite state landed, and keep asserting it.
--
-- Companion to:
--   migrations/native_zh_ja_prompt_rewrites.sql      (7 rows re-authored natively)
--   migrations/zh_ja_prompt_metalanguage_sweep.sql   (21 rows swept of metalanguage)
--
-- WHY THIS FILE EXISTS
-- --------------------
-- Those two migrations were applied by scripts/apply_prompt_rewrites.py and
-- scripts/sweep_prompt_metalanguage.py rather than by running the .sql directly:
-- this environment has no psql and no psycopg2, and DATABASE_URL points at a
-- LOCAL dev database (localhost/lingualoop_dev), not Supabase -- running them
-- against it would have hit the wrong database entirely.
--
-- The .sql files and the scripts are generated from the same source of truth
-- (the verified templates in data/eval/), so they cannot disagree. This file
-- closes the loop by checking the claim instead of trusting it.
--
-- WHAT IT GUARANTEES
-- ------------------
-- For every row the two migrations touch:
--   * the expected version exists
--   * md5(template_text) matches the value recorded when it was authored
--   * is_active is what was intended -- including the two cloze rows that are
--     deliberately STAGED INACTIVE pending TASK-719
--   * exactly ONE active row exists per (task_name, language_id)
--
-- That last one is the invariant that actually bites. Earlier in this workstream
-- a version collision overwrote two live `test_answer_entailment` rows and left
-- zh and ja with NO active row: get_template_config raised, the judge fell into
-- its except branch, and the answer-hallucination guard silently became a no-op
-- for two of three languages. Nothing in the write path complained. A count of
-- active rows is the cheapest possible detector for that class of outage.
--
-- Postgres md5() hashes the server-encoded bytes (UTF8 here), which is what
-- Python's hashlib.md5(text.encode('utf-8')) produces -- the two agree.
--
-- SAFE AND IDEMPOTENT: this migration reads and raises. It writes nothing.
-- Re-run it any time as a drift check.

DO $$
DECLARE
    expected CONSTANT text[][] := ARRAY[
        -- task_name, language_id, version, md5, is_active
        ['translation_uniqueness_judge',            '1', '2', '850df6527f728f295f0fdaa5e5503cb8', 't'],
        ['translation_uniqueness_judge',            '3', '2', 'eafabf9ed23f380ce46ddf774d07d7cb', 't'],
        ['question_inference',                      '1', '2', '329a274e55c091c394f8fafe04203ca4', 't'],
        ['question_main_idea',                      '3', '2', 'a7fe0771bfef3093ca01313d21f04560', 't'],
        ['question_author_purpose',                 '3', '2', '992e62cee4b7d27337ec44565ce06904', 't'],
        -- staged: v1 stays live until TASK-719 measures these
        ['cloze_distractor_judge',                  '1', '2', '7a5f6e8f4275cbaf71c019c977fd30d2', 'f'],
        ['cloze_distractor_judge',                  '3', '2', 'fde592a835ac0b58845e401e87e05d18', 'f'],
        -- metalanguage sweep
        ['ladder_collocation_judge',                '1', '2', '2fd8c77be5646e0c5a9b55675c488065', 't'],
        ['ladder_l1_distractor_judge',              '1', '2', '71592ba873561929cd708bb28ae6178d', 't'],
        ['ladder_l4_morphology_generation',         '1', '2', 'c18c939495d42e99bc49a67d81845cb3', 't'],
        ['ladder_l4_morphology_generation',         '3', '2', '20d25b1f5238f97bfbdfdc95d621c926', 't'],
        ['ladder_l8_collocation_repair_generation', '1', '2', '15409adf7db0c4df5b7110b7e3276ab1', 't'],
        ['ladder_l8_collocation_repair_generation', '3', '2', '42d1f54f4a5932ec7adccbd957fa7f6c', 't'],
        ['ladder_p1_sentence_judge',                '1', '2', '56a416ebdedc9086354c1ecc9aed9486', 't'],
        ['ladder_particle_judge',                   '3', '2', '754e7960cf6c70b0c958a7c50dc2c026', 't'],
        ['ladder_particle_selection_generation',    '3', '2', '5f993b248f2c195d304dd53f8f0a2096', 't'],
        ['ladder_relation_judge',                   '1', '2', 'c0654c5eb7d4128d3204767839cbef74', 't'],
        ['ladder_relation_judge',                   '3', '2', '2d6abb852d1d83f601ece048287f0957', 't'],
        ['ladder_sentence_validity_judge',          '1', '2', 'ca31c5503470d40afb750d06574606e4', 't'],
        ['ladder_syn_ant_generation',               '1', '2', '4044d5c55db320bdc0973edde6f1c3e0', 't'],
        ['ladder_syn_ant_generation',               '3', '2', 'bf56b630ff6fa60f1384dcd0ebc97fff', 't'],
        ['semantic_class_classification',           '1', '3', 'a5e3f6c5ace0f53a86df9374895a7172', 't'],
        ['semantic_class_classification',           '3', '3', 'a2d66ab4daaf4dc43fdc3ef3018abb19', 't'],
        ['test_distractor_plausibility',            '1', '6', '8d0083f7e3524987e4b16b18cd41ce71', 't'],
        ['vocab_prompt1_core',                      '1', '2', 'cd5cf1f78056fe6f16529a955a823949', 't'],
        ['vocab_prompt1_core',                      '3', '2', 'acd4766a17913206940f95509da352cb', 't'],
        ['vocab_prompt2_exercises',                 '1', '4', 'fecd8bec5637bf86f4a083dff9a98bba', 't'],
        ['vocab_prompt3_transforms',                '1', '2', 'badf43214eb425b53a9d57edb73ed390', 't']
    ];
    task        text;
    lang        int;
    ver         int;
    want_md5    text;
    want_active boolean;
    got_md5     text;
    got_active  boolean;
    n_active    int;
    failures    text := '';
BEGIN
    FOR i IN 1 .. array_length(expected, 1) LOOP
        task        := expected[i][1];
        lang        := expected[i][2]::int;
        ver         := expected[i][3]::int;
        want_md5    := expected[i][4];
        want_active := expected[i][5] = 't';

        SELECT md5(template_text), is_active
          INTO got_md5, got_active
          FROM prompt_templates
         WHERE task_name = task AND language_id = lang AND version = ver;

        IF NOT FOUND THEN
            failures := failures || format(E'\n  MISSING  %s lang=%s v%s', task, lang, ver);
            CONTINUE;
        END IF;

        IF got_md5 IS DISTINCT FROM want_md5 THEN
            failures := failures || format(
                E'\n  MD5      %s lang=%s v%s: expected %s, found %s',
                task, lang, ver, want_md5, got_md5);
        END IF;

        IF got_active IS DISTINCT FROM want_active THEN
            failures := failures || format(
                E'\n  ACTIVE   %s lang=%s v%s: expected is_active=%s, found %s',
                task, lang, ver, want_active, got_active);
        END IF;

        -- The outage detector: zero active rows makes get_template_config raise.
        SELECT count(*) INTO n_active
          FROM prompt_templates
         WHERE task_name = task AND language_id = lang AND is_active;

        IF n_active <> 1 THEN
            failures := failures || format(
                E'\n  COUNT    %s lang=%s: expected exactly 1 active row, found %s',
                task, lang, n_active);
        END IF;
    END LOOP;

    IF failures <> '' THEN
        RAISE EXCEPTION 'zh/ja prompt rewrite state does not match the migrations:%', failures;
    END IF;

    RAISE NOTICE 'zh/ja prompt rewrite state verified: % rows OK', array_length(expected, 1);
END $$;
