-- Replace leftover English *format metalanguage* in zh/ja prompt rows.
--
-- Companion to migrations/native_zh_ja_prompt_rewrites.sql. That migration
-- replaced whole prompts that were written in English; this one removes the
-- residue: single English words describing output format inside prompts that are
-- otherwise fully in the target language --
--   "不要使用 markdown 代码块", "输出 schema：", "IPA フィールドの音声記号".
--
-- NO LLM WAS INVOLVED. These are mechanical substitutions, listed in
-- scripts/sweep_prompt_metalanguage.py, which is what originally applied them.
--
-- WHY replace() INSTEAD OF LITERAL TEMPLATES
-- ------------------------------------------
-- Embedding 22 full templates (vocab_prompt1_core alone is 3.8k chars) would
-- produce a ~60KB migration nobody can review. Deriving each new row from its
-- source version states the actual edit, and is re-derivable byte-for-byte
-- because the source rows were DEACTIVATED, never modified. Re-running is a
-- no-op: replace() over already-substituted text changes nothing.
--
-- WHAT IS DELIBERATELY NOT TOUCHED
-- --------------------------------
-- Everything else audit_prompt_latin.py reports as Latin in these rows is
-- load-bearing or legitimate, and each was read in context before exclusion:
--   * parser enums/constants: no_relation, no_inflection, no_collocation,
--     corpus_validated, llm_asserted, form_error, estimated_tier, sentence_index,
--     subject_verb_agreement, antonym/synonym, and the
--     plain/polite/honorific/humble/formal/casual list that must match the
--     {register} value injected into ladder_p1_sentence_judge
--   * {word}, {pos}, {semantic_class} ... -- str.format placeholders. A token
--     regex matches INSIDE the braces, which is why the audit appears to report
--     `word` as leaked in a dozen rows. It is not.
--   * `clean` in ladder_p1_sentence_judge [zh] -- an emitted output value
--     (或写"clean", and "reason": "clean" in its own example), not prose.
--   * proper nouns: HSK, JLPT, CEFR, ASCII, LinguaLoop, and the pinyin examples
--     ("qǐ lái" vs "qi3 lai2") that are the whole point of their instruction.
--
-- VERSION NUMBERS ARE NOT UNIFORM. Each step names its own source and target
-- because the incumbents were not all at v1 -- semantic_class_classification was
-- at v2, test_distractor_plausibility at v4 with an inactive v5 already present
-- (hence v6). Always SELECT existing versions before choosing one; assuming v1
-- is how two live rows were destroyed earlier in this workstream.
--
-- vocab_prompt2_exercises [zh] appears TWICE, v2->v3 then v3->v4. The last stray
-- "vs" was found after the sweep had already run; the chain is preserved rather
-- than collapsed so the migration matches what the database actually did.

BEGIN;

-- Expected final state (active row per task/language), captured 2026-08-18:
--   ladder_collocation_judge                   lang 1  v2  md5 2fd8c77be5646e0c5a9b55675c488065
--   ladder_l1_distractor_judge                 lang 1  v2  md5 71592ba873561929cd708bb28ae6178d
--   ladder_l4_morphology_generation            lang 1  v2  md5 c18c939495d42e99bc49a67d81845cb3
--   ladder_l4_morphology_generation            lang 3  v2  md5 20d25b1f5238f97bfbdfdc95d621c926
--   ladder_l8_collocation_repair_generation    lang 1  v2  md5 15409adf7db0c4df5b7110b7e3276ab1
--   ladder_l8_collocation_repair_generation    lang 3  v2  md5 42d1f54f4a5932ec7adccbd957fa7f6c
--   ladder_p1_sentence_judge                   lang 1  v2  md5 56a416ebdedc9086354c1ecc9aed9486
--   ladder_particle_judge                      lang 3  v2  md5 754e7960cf6c70b0c958a7c50dc2c026
--   ladder_particle_selection_generation       lang 3  v2  md5 5f993b248f2c195d304dd53f8f0a2096
--   ladder_relation_judge                      lang 1  v2  md5 c0654c5eb7d4128d3204767839cbef74
--   ladder_relation_judge                      lang 3  v2  md5 2d6abb852d1d83f601ece048287f0957
--   ladder_sentence_validity_judge             lang 1  v2  md5 ca31c5503470d40afb750d06574606e4
--   ladder_syn_ant_generation                  lang 1  v2  md5 4044d5c55db320bdc0973edde6f1c3e0
--   ladder_syn_ant_generation                  lang 3  v2  md5 bf56b630ff6fa60f1384dcd0ebc97fff
--   semantic_class_classification              lang 1  v3  md5 a5e3f6c5ace0f53a86df9374895a7172
--   semantic_class_classification              lang 3  v3  md5 a2d66ab4daaf4dc43fdc3ef3018abb19
--   test_distractor_plausibility               lang 1  v6  md5 8d0083f7e3524987e4b16b18cd41ce71
--   vocab_prompt1_core                         lang 1  v2  md5 cd5cf1f78056fe6f16529a955a823949
--   vocab_prompt1_core                         lang 3  v2  md5 acd4766a17913206940f95509da352cb
--   vocab_prompt2_exercises                    lang 1  v4  md5 fecd8bec5637bf86f4a083dff9a98bba
--   vocab_prompt3_transforms                   lang 1  v2  md5 badf43214eb425b53a9d57edb73ed390

-- ladder_collocation_judge [lang 1] v1 -> v2
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 2, TRUE, model, provider,
       replace(template_text, 'markdown 代码块', '代码块'),
       'v2: English format metalanguage replaced with target-language wording (markdown 代码块). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'ladder_collocation_judge' AND language_id = 1 AND version = 1
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'ladder_collocation_judge' AND language_id = 1 AND version <> 2;

-- ladder_l1_distractor_judge [lang 1] v1 -> v2
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 2, TRUE, model, provider,
       replace(replace(template_text, 'markdown 代码块', '代码块'), 'mǎ vs mā', 'mǎ 与 mā'),
       'v2: English format metalanguage replaced with target-language wording (markdown 代码块, mǎ vs mā). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'ladder_l1_distractor_judge' AND language_id = 1 AND version = 1
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'ladder_l1_distractor_judge' AND language_id = 1 AND version <> 2;

-- ladder_l4_morphology_generation [lang 1] v1 -> v2
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 2, TRUE, model, provider,
       replace(template_text, 'markdown 代码块', '代码块'),
       'v2: English format metalanguage replaced with target-language wording (markdown 代码块). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'ladder_l4_morphology_generation' AND language_id = 1 AND version = 1
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'ladder_l4_morphology_generation' AND language_id = 1 AND version <> 2;

-- ladder_l4_morphology_generation [lang 3] v1 -> v2
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 2, TRUE, model, provider,
       replace(template_text, 'markdown コードフェンス', 'コードフェンス'),
       'v2: English format metalanguage replaced with target-language wording (markdown コードフェンス). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'ladder_l4_morphology_generation' AND language_id = 3 AND version = 1
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'ladder_l4_morphology_generation' AND language_id = 3 AND version <> 2;

-- ladder_l8_collocation_repair_generation [lang 1] v1 -> v2
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 2, TRUE, model, provider,
       replace(template_text, 'markdown 代码块', '代码块'),
       'v2: English format metalanguage replaced with target-language wording (markdown 代码块). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'ladder_l8_collocation_repair_generation' AND language_id = 1 AND version = 1
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'ladder_l8_collocation_repair_generation' AND language_id = 1 AND version <> 2;

-- ladder_l8_collocation_repair_generation [lang 3] v1 -> v2
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 2, TRUE, model, provider,
       replace(template_text, 'markdown コードフェンス', 'コードフェンス'),
       'v2: English format metalanguage replaced with target-language wording (markdown コードフェンス). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'ladder_l8_collocation_repair_generation' AND language_id = 3 AND version = 1
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'ladder_l8_collocation_repair_generation' AND language_id = 3 AND version <> 2;

-- ladder_p1_sentence_judge [lang 1] v1 -> v2
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 2, TRUE, model, provider,
       replace(template_text, 'markdown 代码块', '代码块'),
       'v2: English format metalanguage replaced with target-language wording (markdown 代码块). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'ladder_p1_sentence_judge' AND language_id = 1 AND version = 1
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'ladder_p1_sentence_judge' AND language_id = 1 AND version <> 2;

-- ladder_particle_judge [lang 3] v1 -> v2
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 2, TRUE, model, provider,
       replace(template_text, 'markdown コードフェンス', 'コードフェンス'),
       'v2: English format metalanguage replaced with target-language wording (markdown コードフェンス). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'ladder_particle_judge' AND language_id = 3 AND version = 1
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'ladder_particle_judge' AND language_id = 3 AND version <> 2;

-- ladder_particle_selection_generation [lang 3] v1 -> v2
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 2, TRUE, model, provider,
       replace(template_text, 'markdown コードフェンス', 'コードフェンス'),
       'v2: English format metalanguage replaced with target-language wording (markdown コードフェンス). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'ladder_particle_selection_generation' AND language_id = 3 AND version = 1
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'ladder_particle_selection_generation' AND language_id = 3 AND version <> 2;

-- ladder_relation_judge [lang 1] v1 -> v2
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 2, TRUE, model, provider,
       replace(template_text, 'markdown 代码块', '代码块'),
       'v2: English format metalanguage replaced with target-language wording (markdown 代码块). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'ladder_relation_judge' AND language_id = 1 AND version = 1
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'ladder_relation_judge' AND language_id = 1 AND version <> 2;

-- ladder_relation_judge [lang 3] v1 -> v2
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 2, TRUE, model, provider,
       replace(template_text, 'markdown コードフェンス', 'コードフェンス'),
       'v2: English format metalanguage replaced with target-language wording (markdown コードフェンス). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'ladder_relation_judge' AND language_id = 3 AND version = 1
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'ladder_relation_judge' AND language_id = 3 AND version <> 2;

-- ladder_sentence_validity_judge [lang 1] v1 -> v2
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 2, TRUE, model, provider,
       replace(template_text, 'markdown 代码块', '代码块'),
       'v2: English format metalanguage replaced with target-language wording (markdown 代码块). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'ladder_sentence_validity_judge' AND language_id = 1 AND version = 1
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'ladder_sentence_validity_judge' AND language_id = 1 AND version <> 2;

-- ladder_syn_ant_generation [lang 1] v1 -> v2
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 2, TRUE, model, provider,
       replace(template_text, 'markdown 代码块', '代码块'),
       'v2: English format metalanguage replaced with target-language wording (markdown 代码块). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'ladder_syn_ant_generation' AND language_id = 1 AND version = 1
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'ladder_syn_ant_generation' AND language_id = 1 AND version <> 2;

-- ladder_syn_ant_generation [lang 3] v1 -> v2
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 2, TRUE, model, provider,
       replace(template_text, 'markdown コードフェンス', 'コードフェンス'),
       'v2: English format metalanguage replaced with target-language wording (markdown コードフェンス). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'ladder_syn_ant_generation' AND language_id = 3 AND version = 1
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'ladder_syn_ant_generation' AND language_id = 3 AND version <> 2;

-- semantic_class_classification [lang 1] v2 -> v3
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 3, TRUE, model, provider,
       replace(template_text, 'markdown。', '代码块。'),
       'v3: English format metalanguage replaced with target-language wording (markdown。). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'semantic_class_classification' AND language_id = 1 AND version = 2
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'semantic_class_classification' AND language_id = 1 AND version <> 3;

-- semantic_class_classification [lang 3] v2 -> v3
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 3, TRUE, model, provider,
       replace(template_text, '説明・markdown は', '説明・コードフェンスは'),
       'v3: English format metalanguage replaced with target-language wording (説明・markdown は). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'semantic_class_classification' AND language_id = 3 AND version = 2
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'semantic_class_classification' AND language_id = 3 AND version <> 3;

-- test_distractor_plausibility [lang 1] v4 -> v6
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 6, TRUE, model, provider,
       replace(template_text, 'markdown 代码块', '代码块'),
       'v6: English format metalanguage replaced with target-language wording (markdown 代码块). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'test_distractor_plausibility' AND language_id = 1 AND version = 4
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'test_distractor_plausibility' AND language_id = 1 AND version <> 6;

-- vocab_prompt1_core [lang 1] v1 -> v2
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 2, TRUE, model, provider,
       replace(replace(replace(template_text, '输出 schema：', '输出结构：'), '下游 prompt', '下游提示词'), '字段 IPA 中的国际音标符号', '国际音标字段中的音标符号'),
       'v2: English format metalanguage replaced with target-language wording (输出 schema：, 下游 prompt, 字段 IPA 中的国际音标符号). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'vocab_prompt1_core' AND language_id = 1 AND version = 1
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'vocab_prompt1_core' AND language_id = 1 AND version <> 2;

-- vocab_prompt1_core [lang 3] v1 -> v2
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 2, TRUE, model, provider,
       replace(template_text, 'IPA フィールドの音声記号', '国際音声記号フィールドの音声記号'),
       'v2: English format metalanguage replaced with target-language wording (IPA フィールドの音声記号). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'vocab_prompt1_core' AND language_id = 3 AND version = 1
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'vocab_prompt1_core' AND language_id = 3 AND version <> 2;

-- vocab_prompt2_exercises [lang 1] v2 -> v3
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 3, TRUE, model, provider,
       replace(replace(replace(template_text, '输出 schema：', '输出结构：'), 'prompt 1 规则', '提示词 1 规则'), '状态 vs 完成 vs 活动', '状态／完成／活动'),
       'v3: English format metalanguage replaced with target-language wording (输出 schema：, prompt 1 规则, 状态 vs 完成 vs 活动). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'vocab_prompt2_exercises' AND language_id = 1 AND version = 2
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'vocab_prompt2_exercises' AND language_id = 1 AND version <> 3;

-- vocab_prompt3_transforms [lang 1] v1 -> v2
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 2, TRUE, model, provider,
       replace(replace(template_text, '输出 schema：', '输出结构：'), 'prompt 1 规则', '提示词 1 规则'),
       'v2: English format metalanguage replaced with target-language wording (输出 schema：, prompt 1 规则). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'vocab_prompt3_transforms' AND language_id = 1 AND version = 1
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'vocab_prompt3_transforms' AND language_id = 1 AND version <> 2;

-- vocab_prompt2_exercises [lang 1] v3 -> v4
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
SELECT task_name, language_id, 4, TRUE, model, provider,
       replace(template_text, '及物 vs 不及物', '及物／不及物'),
       'v4: English format metalanguage replaced with target-language wording (及物 vs 不及物). No contract token touched.'
  FROM prompt_templates
 WHERE task_name = 'vocab_prompt2_exercises' AND language_id = 1 AND version = 3
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'vocab_prompt2_exercises' AND language_id = 1 AND version <> 4;

COMMIT;
