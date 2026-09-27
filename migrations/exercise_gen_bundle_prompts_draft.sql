-- DRAFT — NOT APPLIED. Phase 2 (TASK-814/815/816), gated on the Phase 0
-- baseline (TASK-808) landing and a Phase 1 (TASK-809-813) non-inferiority
-- score. Do not run this migration until both gates clear and the feature
-- flag below has been wired into code and defaults to OFF.
--
-- Date drafted: 2026-09-26.
--
-- =============================================================================
-- WHAT THIS FILE ADDS (when eventually applied)
-- =============================================================================
-- Two NEW prompt_templates task_name families, one row per language (zh/ja on
-- qwen/qwen3.7-plus per ADR-028 Decision §2; en left on its current
-- generation model pending TASK-817's bake-off, which is Phase 3 and blocked
-- — user: do not do Phase 3. The en model below is a PLACEHOLDER, not a
-- decision):
--
--   vocab_bundle_generation   — replaces, for a bundle-mode sense, the THREE
--                               separate calls (vocab_prompt2_exercises,
--                               vocab_prompt3_transforms, plus the split L4/L8
--                               and typed syn/ant|word_family|particle_selection
--                               generators) with ONE call producing BOTH
--                               variants A and B together, per ADR-028
--                               Decision §4's ~4-5-call/sense target.
--   ladder_bundle_judge       — replaces the 7 render judges (sentence_validity
--                               L6/L7, cloze L3, l1_distractor L1, collocation
--                               L5/L8, particle [ja L4], relation [syn/ant],
--                               word_family [en]) with ONE call, per-item
--                               verdicts keyed so they map back onto the
--                               existing judge result shapes without a
--                               renderer/upload path change. The P1 sentence
--                               judge (`ladder_p1_sentence_judge`) is explicitly
--                               NOT bundled — ADR-028 keeps it separate because
--                               it is what catches compound-word anchoring, the
--                               fat-seed path's known defect class.
--
-- These rows are inserted with `is_active = false` — they exist so the schema/
-- content can be reviewed and iterated on before flipping them live, and so
-- TASK-815/816's implementation can start from a real template row instead of
-- inventing one inline. Flipping `is_active = true` is a separate, explicit
-- step for whoever implements TASK-815/816, done only after the feature flag
-- (below) is wired and a shadow/canary comparison against the reference set
-- (TASK-807 protocol) passes.
--
-- =============================================================================
-- FEATURE FLAG DESIGN (for TASK-815/816's code, not created by this SQL file)
-- =============================================================================
-- Env var: VOCAB_LADDER_BUNDLE_MODE, values "off" (default) | "shadow" | "on".
--   "off"    — current behavior, exactly as today. Bundle prompt rows below
--              are never read even once they're marked is_active. This is the
--              default in every environment, including this migration's own
--              target state immediately after being applied.
--   "shadow" — VocabAssetPipeline runs BOTH the legacy per-prompt path (as
--              today, and what actually gets stored/served) AND the bundle
--              path (call made, response validated, result discarded/logged
--              only — NOT stored to word_assets, NOT rendered). Doubles cost
--              for senses run in shadow mode, by design — this is a
--              measurement mode for comparing bundle-vs-legacy output on real
--              traffic before trusting it, not a production mode. Logged via
--              `call_role` — add a new value ("shadow") to
--              `services.llm_service._VALID_CALL_ROLES` alongside `primary`/
--              `json_repair`/`retry`/`salvage`/`repair` so shadow-mode calls
--              are visible in `llm_calls` and excluded from cost/latency
--              dashboards that assume `primary` means "the call that
--              actually produced what shipped".
--   "on"     — bundle path is the ONLY path; legacy per-prompt generators are
--              not called. This is the end state TASK-815/816 ship to, only
--              after "shadow" mode has cleared TASK-807's non-inferiority
--              thresholds on a real sample (not just the frozen reference
--              set — shadow mode against live traffic is what actually
--              proves the collapse is safe under the full variety of senses
--              the reference set may not cover).
-- Read via `os.getenv('VOCAB_LADDER_BUNDLE_MODE', 'off')` at the top of
-- `VocabAssetPipeline._generate_for_sense_impl` (services/vocabulary_ladder/
-- asset_pipeline.py) — NOT cached at import time, so an operator can flip it
-- between batch runs without a redeploy (the same pattern
-- `LLM_DEFAULT_PROVIDER` already uses via `set_default_provider`).
--
-- =============================================================================
-- OUTPUT SCHEMA (both new task_names) — maps onto EXISTING word_assets /
-- exercises shapes so the renderer and upload path are unchanged
-- =============================================================================
-- vocab_bundle_generation returns:
--   {
--     "A": { "1": [...L1 options...], "3": [...L3 options...],
--            "4": {...L4 fields...} | null, "5": [...L5 options...],
--            "6": {...L6 fields...}, "7": {...L7 fields...},
--            "8": [...L8 options...] | omitted,
--            "syn_ant": {...} | omitted, "word_family": {...} | omitted,
--            "particle_selection": {...} | omitted },
--     "B": { ...same shape, sentence assignments per SENTENCE_ASSIGNMENTS_B... }
--   }
-- Each per-level/per-type fragment is BYTE-SHAPE-IDENTICAL to what
-- `vocab_prompt2_exercises`/`vocab_prompt3_transforms`/the split generators/
-- `typed_llm` generators already return before remap, so
-- `ExerciseAssetGenerator._remap_output`/`TransformAssetGenerator._remap_output`/
-- `SplitLevelGenerator._remap` and every existing validator
-- (`VocabAssetValidator.validate_prompt2`/`validate_prompt3`) can be reused
-- UNCHANGED — the bundle-mode caller in `asset_pipeline.py` just calls one
-- `call_llm` and then dispatches each top-level key to the SAME remap/validate
-- functions that already exist, per variant. This is the point of designing
-- the schema this way: TASK-815 becomes "one call, then N existing remaps",
-- not "N new remaps".
--
-- ladder_bundle_judge returns, keyed by judge axis (so each axis maps onto the
-- existing per-judge caller's expected shape):
--   {
--     "sentence_validity": { "<1-based index>": {"rating": 1-5, "reason": "..."} , ... },
--     "cloze":             { "<1-based index>": {"verdict": "keep|reject", "reason": "..."} , ... },
--     "l1_distractor":     { "<1-based index>": {"verdict": "keep|reject", "reason": "..."} , ... },
--     "collocation":       { "<1-based index>": {"rating": 1-5, "reason": "..."} , ... },
--     "particle":          { "<1-based index>": {"0": 1-5, "1": "..."} , ... }   (ja only),
--     "relation":          { "<1-based index>": {"0": 1-5, "1": "..."} , ... }   (syn/ant only),
--     "word_family":       { "<1-based index>": {"0": 1-5, "1": "..."} , ... }   (en only)
--   }
-- A language/sense that has no candidates for a given axis (e.g. zh has no
-- `word_family` items) simply omits that top-level key — the bundle-judge
-- CALLER in `queue_drain.py`/`exercise_renderer.py` (TASK-816) is responsible
-- for only asking for, and only reading, the axes relevant to that sense's
-- active levels/types, exactly as the 7 separate judges already are only
-- invoked when their level/type is active.
--
-- =============================================================================
-- RULES PRESERVED FROM THE LIVE PROMPTS (verified 2026-09-26 against the zh
-- `vocab_prompt2_exercises` v4, `vocab_prompt3_transforms` v2, and the
-- `ladder_sentence_validity_judge`/`ladder_l1_distractor_judge`/
-- `ladder_collocation_judge`/`ladder_relation_judge`/`ladder_particle_judge`/
-- `ladder_word_family_judge`/`cloze_distractor_judge` v1/v2 rows, zh/ja/en as
-- applicable) — every rule below appears, in substance, in the draft template
-- text following this header:
--   1. L1 is a LISTENING exercise: distractors must be AUDIO-CONFUSABLE (tone
--      confusion for zh; the ja L1 path is deterministic/mora-trie, NOT part
--      of this bundle — see note below) — never a same-meaning synonym, never
--      a pure-homophone (indistinguishable by ear), never a pure
--      shape-similar/different-sound distractor. (ladder_l1_distractor_judge,
--      vocab_prompt2_exercises L1 section)
--   2. Whole-word / compound-word anchoring: the target word's characters must
--      carry the SAME syntactic/semantic role as the locked sense in every
--      sentence and option, across L3/L5/L6/L7/L8 — never let the target
--      appear only as a character-fragment of a different word. (rule 5 in
--      zh P2, rule 4 in zh P3 — "提示词 1 规则 13" cross-reference preserved
--      verbatim as a TODO for whoever finalizes this: confirm what P1 rule 13
--      says today before shipping, since this bundle prompt cannot silently
--      drop a cross-referenced rule it doesn't fully restate)
--   3. L3's four-dimension distractor self-check (语义/搭配/体貌/语域/配价 —
--      semantic/collocation/aspect/register/valency) AND the "synonym
--      substitution audit" (would a common synonym of the target make this
--      distractor correct? if yes, reject it) — both preserved verbatim in
--      the draft below.
--   4. L8's four hard rules (correct option is character-for-character
--      identical to the given collocate; exactly one `true`; no distractor
--      duplicates the correct collocate; distractors share the collocate's
--      part of speech).
--   5. `ladder_relation_judge`'s core finding: a synonym/antonym distractor
--      must be checked against ALL of the target's senses, not just the one
--      being taught — the worked example (走 / 行) is reproduced in the draft
--      so this doesn't get lost in a "shortened for the bundle" summarization.
--   6. `ladder_word_family_judge`'s distinction between "well-formed" and
--      "a real word" (its own worked example, decisionment vs decisive, is
--      reproduced) — en only.
--   7. `ladder_particle_judge`'s "judge whether the sentence is grammatical,
--      NOT whether the meaning changes" rule, with its worked
--      に/へ、は/が、を/が examples — ja only.
--   8. Conservative-judging instruction is uniform across all axes: "when
--      unsure, reject / rate low" — losing a borderline distractor is cheap,
--      keeping an ambiguous one is not. Preserved as a single shared
--      instruction at the top of the bundle judge prompt rather than repeated
--      per axis, since repeating it 7 times in one prompt is exactly the kind
--      of redundant-prefix bloat this whole ADR is trying to remove.
--
-- NOTE ON ja L1 (CORRECTED 2026-09-27 against data/eval/runs/phase2_smoke_ja
-- -- the original note below was wrong about generation, right about
-- render/judging; read both halves):
--   * RENDER TIME: `wiki/decisions/ADR-028...` and this repo's own memory
--     (`ja mora-trie built + wired live`) confirm ja L1 renders via a
--     deterministic phonetic-trie build
--     (`services/vocabulary_ladder/l1_lookup.py`) -- `_render_phonetic`
--     always prefers the trie's candidates over `p2['level_1']` for ja, so
--     `ladder_bundle_judge` for ja correctly has NO `l1_distractor` axis
--     (unaffected by this correction -- L1 verdicts for ja always fall back
--     to `filter_l1_distractors` today, via the `raw.get('l1_distractor')
--     is None despite requests existing` fail-closed path in
--     `judge.py._resolve_distractor_axis`, and that stays true whether or
--     not `vocab_bundle_generation` produces an L1 block).
--   * GENERATION TIME: this does NOT mean `vocab_bundle_generation` for ja
--     can omit the "L1"/"1" key. `active_levels`
--     (`compute_active_levels`/`active_levels_for_context`) and `p2_levels`
--     (`active_levels ∩ PROMPT2_LEVELS`, in `generator.py`) are both
--     language-agnostic and still include level 1 for ja, so
--     `mapping.build_p2_content`'s `validate_prompt2` gate still REQUIRES a
--     "1" key -- exactly like the LIVE (non-bundle) ja
--     `vocab_prompt2_exercises` prompt, which was verified live 2026-09-27
--     to still generate a full L1 section for this same reason, wastefully
--     unused at render time. The ja row below now includes a condensed L1
--     section (v3) for this reason -- omitting it (v2's mistake) made every
--     ja P2 block fail validation and fall back to the legacy per-generator
--     call on all 3 `phase2_smoke_ja` senses (real cost, no output
--     regression, since `BundleGenerator`'s partial-fallback caught it).
--
-- NOTE ON TEMPLATE COMPLETENESS: the template_text values below are DRAFTS —
-- they restate every identified rule but are shorter than production-grade
-- (e.g. they do not reproduce every single worked example verbatim from the
-- 3700-6900-character existing prompts). Per this same file's Phase-2 risk
-- notes and TASK-812's template-reorder caution, native-language review is
-- REQUIRED before `is_active` is ever flipped true — treat every {{...}}
-- placeholder and every rule number below as a checklist for that review, not
-- as finished production copy.
--
-- =============================================================================
-- ROLLBACK
-- =============================================================================
-- These rows are inserted `is_active = false`, so there is nothing to roll
-- back functionally on first application (no existing active row is touched
-- or superseded). To remove entirely:
--   DELETE FROM prompt_templates
--   WHERE task_name IN ('vocab_bundle_generation', 'ladder_bundle_judge')
--     AND version = 1;
--
-- NOTE ON THE en `ladder_bundle_judge` ROW (added after the zh/ja rows below,
-- same drafting pass as everything else in this file): `BundleJudge` in
-- `services/vocabulary_ladder/bundle/judge.py` currently hardcodes
-- `_SUPPORTED_LANGUAGES = frozenset({1, 3})` (zh, ja) — language_id=2 (en)
-- ALWAYS falls back to the per-judge calls today regardless of what is in
-- this table, is_active or not. This row is prepared ahead of that follow-up
-- (widening `_SUPPORTED_LANGUAGES` to include en), not something the current
-- code will read. It also references a `word_family` axis
-- (`word_family_items_numbered`) that has NO corresponding dataclass,
-- resolver, or `prompt_vars` entry in `judge.py` at all yet — unlike
-- `relation`/`particle`, which exist in code but aren't gathered by the
-- wiring patch, `word_family` isn't wired in ANY layer yet. Both gaps must be
-- closed by a follow-up task before this row can ever be flipped `is_active`.

BEGIN;

-- ---------------------------------------------------------------------------
-- vocab_bundle_generation — zh (qwen/qwen3.7-plus)
-- ---------------------------------------------------------------------------
INSERT INTO prompt_templates
    (task_name, template_text, version, is_active, description, language_id, model, provider)
VALUES (
    'vocab_bundle_generation',
    E'角色：你是一位专业的计算语言学家，正在为汉语词汇学习者一次性生成两套（A/B）完整练习题。\n\n'
    E'目标词：{word}\n词性：{pos}\n语义类：{semantic_class}\n学习者级别：{complexity_tier}\n'
    E'释义：{definition}\n首要搭配词：{primary_collocate}\n语域：{register}\n'
    E'义项指纹（用于消歧，勿在输出中复述）：{sense_fingerprint}\n\n'
    E'变体 A 基础例句（含句子索引）：\n{sentences_json_a}\n\n'
    E'变体 B 基础例句（含句子索引）：\n{sentences_json_b}\n\n'
    E'形式变体（L4 构词用）：\n{morphological_forms_json}\n\n'
    E'仅生成以下列出的练习级别 / 类型（两个变体均生成同一集合）：{active_levels_json}\n\n'
    E'== 通用规则（适用于每个级别、两个变体）==\n'
    E'1. 所有输出值必须使用简体中文，不得夹杂英文。仅输出有效 JSON，键为数字字符串。\n'
    E'2. 目标词的字符在所有句子和选项中必须承担与所锁定义项相同的句法/语义角色——禁止把目标字仅作为'
    E'另一个词的字符片段使用（与提示词 1 规则 13 一致；实现前请核对该规则当前文本）。\n'
    E'3. 不确定时从严：宁可舍弃一个临界选项，也不要放过一个其实成立的选项。\n\n'
    E'== 输出键编号约定（必须严格遵守，两套约定并存，不可混用）==\n'
    E'A) "1"/"3"/"5"/"6" 四个小节内部的选项对象使用 1 起始编号：{{"1": 选项文本, "2": 是否正确(true/false), '
    E'"3": 解释}}；"6" 的容器是 {{"1": 正确句索引, "2": [ {{"1": 错句文本, "2": 解释}} ... 3 个]}}。\n'
    E'B) "4"（构词）、"8"（搭配修复）、"syn_ant" 三个小节使用 0 起始编号，容器固定为 '
    E'{{"0": [ {{"0": 选项文本, "1": 是否正确(true/false), "2": 解释}} ... 恰好 4 个，且仅有 1 个 true], '
    E'"1": 该小节的附加字段}}；"4" 的 "1" 是 base_form（词根/原形），另需给出 "2"=form_label（词形标签）；'
    E'"8" 的 "1" 是 error_collocate（植入的错误搭配词，必须是给定搭配词以外的词，且不得与任一选项文本重复）；'
    E'"syn_ant" 的 "1" 是 relation，取值仅能是 "synonym" 或 "antonym"。不适用于本词时，改为返回 '
    E'{{"9": "no_inflection"}}（"4"）/ {{"9": "no_collocation"}}（"8"）/ {{"9": "no_relation"}}（"syn_ant"），'
    E'不要省略该小节的键，也不要返回 null。\n\n'
    E'== L1（听音辨字，仅听力）==\n'
    E'4 个选项，1 正确 = 目标词，3 个干扰项。干扰项必须是真实存在的字/词、与目标词声调混淆但非同义词，'
    E'不得是纯同音同调字，不得是仅形近而读音无关的字（听不出区别的干扰项无意义）。\n\n'
    E'== L3（语境填空）==\n'
    E'用变体各自的句子索引 {level_3_sentence_index_a} / {level_3_sentence_index_b}。3 个干扰项：词性相同、'
    E'语法可填但语义/语境不合适。强制自检：(a) 为每个干扰项标注唯一失效维度（语义/搭配/体貌/语域/配价）之一，'
    E'作为解释前缀；(b) 替换审计——若用目标词的常见近义词替换后此干扰项会变得合理，必须换掉它；3 个干扰项须'
    E'覆盖至少两个不同失效维度。\n\n'
    E'== L4（构词填空，若适用；不适用见上方 "9" 转义约定）==\n'
    E'用句子索引 {level_4_sentence_index_a} / {level_4_sentence_index_b} 中含目标词字符的复合词，'
    E'选一个字符为空缺；3 个干扰字符必须能与复合词其余部分构成真实词但语境不合适。\n\n'
    E'== L5（搭配填空，若在 active_levels_json 内）==\n'
    E'用句子索引 {level_5_sentence_index_a} / {level_5_sentence_index_b}。正确=首要搭配词；3 个干扰项：'
    E'词性相同、语义相近但与目标词搭配不自然或改变义项。\n\n'
    E'== L6（语义辨析）==\n'
    E'以句子索引 {level_6_sentence_index_a} / {level_6_sentence_index_b} 为正确句；生成 3 个新错误句，'
    E'每句用目标词但量词/体标/语序/趋向补语类错误之一（每句尽量不同类别），且满足角色一致性规则。\n\n'
    E'== L7（找错句）==\n'
    E'{level_7_correct_indices_a} / {level_7_correct_indices_b} 为正确句索引；各变体生成 1 个含目标词、'
    E'仅有一个该级别可识别的结构性错误的错句（量词/体标/语序/趋向补语类），错误须为学习者常犯、母语者能立即'
    E'识别的类型。\n\n'
    E'== L8（搭配修复，若适用）==\n'
    E'源句 {level_8_sentence_text_a} / {level_8_sentence_text_b}，正确搭配词 {level_8_collocate_word}。'
    E'硬性规则：正确选项文本必须与给定搭配词字符级完全一致；恰好一个 true；干扰项不得是给定搭配词的重复；'
    E'干扰项须与其词性相同但在此句搭配不自然。\n\n'
    E'== 近义/反义（若在 active_levels_json 内，type=syn_ant）==\n'
    E'生成与目标词在所教义项上构成近义或反义关系的正确项，以及在该义项上明确不构成该关系的干扰项——'
    E'但生成阶段不负责跨义项复核，那是判卷阶段（ladder_bundle_judge）的职责；仍需避免选择目标词在其他常见'
    E'义项下的近义/反义词作为干扰项，以减少后续判卷的驳回率。\n\n'
    E'输出结构（两个变体都用相同键集，仅列出 active_levels_json 中要求的键；见上方两套编号约定）：\n'
    E'{{"A": {{"1": [{{"1":..,"2":..,"3":..}} x4], "3": [{{"1":..,"2":..,"3":..}} x4], '
    E'"4": {{"0": [{{"0":..,"1":..,"2":..}} x4], "1": "base_form", "2": "form_label"}}, '
    E'"5": [{{"1":..,"2":..,"3":..}} x4], '
    E'"6": {{"1": 正确句索引, "2": [{{"1": 错句文本, "2": 解释}} x3]}}, '
    E'"7": {{"1":错句,"2":正确句,"3":说明,"4":[正确索引]}}, '
    E'"8": {{"0": [{{"0":..,"1":..,"2":..}} x4], "1": "error_collocate"}}, '
    E'"syn_ant": {{"0": [{{"0":..,"1":..,"2":..}} x4], "1": "synonym"}}}}, '
    E'"B": {{...同构，使用变体B的句子索引...}}}}',
    2, false,
    'DRAFT (TASK-815, Phase 2, not applied): bundles P2(L1/L3/L5/L6)+P3(L4/L7/L8)+syn_ant for zh, both variants, one call. Gated on baseline + Phase 1 score; feature-flagged VOCAB_LADDER_BUNDLE_MODE (default off). v2: added register/sense_fingerprint inputs and an explicit numeric-key-contract section (v1 left the 1-based P2 vs 0-based split/typed numbering undocumented, and used null for an inapplicable L4/L8/syn_ant instead of the "9" escape every remap function actually expects).',
    1, 'qwen/qwen3.7-plus', 'openrouter'
);

-- ---------------------------------------------------------------------------
-- vocab_bundle_generation — ja (qwen/qwen3.7-plus)
--
-- v3 CORRECTION (2026-09-27, ADR-028 Phase 2 smoke test data/eval/runs/
-- phase2_smoke_ja): v2 omitted L1 on the assumption that "ja L1 renders via
-- the deterministic mora-trie" meant generation-time L1 content was no
-- longer needed either. That assumption was WRONG — confirmed live against
-- the real pipeline: `asset_pipeline.py`'s `active_levels` (from
-- `compute_active_levels`/`active_levels_for_context`, language-agnostic)
-- still includes level 1 for ja, so `p2_levels` (`active_levels ∩
-- PROMPT2_LEVELS`, also language-agnostic — see `generator.py`) still
-- includes 1, and `mapping.build_p2_content`'s `validate_prompt2` gate still
-- REQUIRES a "1" key. The trie only changes what RENDER TIME
-- (`exercise_renderer._render_phonetic`) reads — it always prefers the
-- trie's candidates over `p2['level_1']` for ja and ignores the LLM content
-- entirely, exactly as it already does for the LIVE (non-bundle)
-- `vocab_prompt2_exercises` ja prompt today (verified live 2026-09-27: that
-- prompt DOES still generate a full L1 section, unused at render time,
-- purely to satisfy this same validator gate). v2's omission made EVERY
-- ja P2 block fail validation with "Missing level_1" and fall back to the
-- legacy per-generator call for both variants on all 3 smoke senses — the
-- bundle call still succeeded and cost real money, so this was a pure waste,
-- not a safety issue (`BundleGenerator`'s partial-fallback policy caught it
-- cleanly, per its docstring). v3 restores an L1 section (condensed from the
-- live ja prompt's mora-substitution algorithm) so ja's bundle response
-- satisfies the SAME validator gate the legacy path already satisfies —
-- L1 render behavior for ja is unchanged (still 100% trie-sourced; this
-- content is generated but never read, same waste as today's live prompt,
-- not a new one).
-- ---------------------------------------------------------------------------
INSERT INTO prompt_templates
    (task_name, template_text, version, is_active, description, language_id, model, provider)
VALUES (
    'vocab_bundle_generation',
    E'役割：あなたは日本語語彙学習者向けに、2セット（A/B）の完全な練習問題を一度に生成する計算言語学の専門家です。\n\n'
    E'目標語：{word}\n品詞：{pos}\n意味クラス：{semantic_class}\n学習者レベル：{complexity_tier}\n'
    E'定義：{definition}\n主要な連語：{primary_collocate}\n文体（レジスター）：{register}\n'
    E'語義フィンガープリント（曖昧性解消専用、出力に含めないこと）：{sense_fingerprint}\n\n'
    E'変体A 基礎例文（文インデックス付き）：\n{sentences_json_a}\n\n'
    E'変体B 基礎例文（文インデックス付き）：\n{sentences_json_b}\n\n'
    E'形態変化形（L4用）：\n{morphological_forms_json}\n\n'
    E'{active_levels_json} に列挙されたレベル/タイプのみ生成すること（両変体とも同じ集合）。\n'
    E'注意：このプロンプトの "1"（L1）は生成はするが、実際のレンダリングでは使われない（日本語L1は'
    E'決定的なモーラ辞書から描画される — 既存の非バンドル版 vocab_prompt2_exercises と同じ扱い）。'
    E'それでも検証ゲートが "1" キーの存在を要求するため、省略せず必ず生成すること。\n\n'
    E'== 共通規則 ==\n'
    E'1. 出力値はすべて自然な日本語。JSON のみ、キーは数字文字列。\n'
    E'2. 目標語の文字は、すべての文と選択肢において、固定された語義と同じ統語的/意味的役割を担うこと'
    E'（プロンプト1規則13と一致 — 実装前に現在の文言を確認すること）。\n'
    E'3. 迷った場合は厳格に：境界的な選択肢を捨てる方が、実は正しい選択肢を残すより安全。\n\n'
    E'== 出力キー番号の約束（2つの体系が併存、混同しないこと）==\n'
    E'A) "1"/"3"/"6" 内の選択肢オブジェクトは 1 始まり：{{"1": 選択肢テキスト, "2": 正誤(true/false), "3": 説明}}；'
    E'"6" のコンテナは {{"1": 正しい文のインデックス, "2": [{{"1": 誤文, "2": 説明}} を3個]}}。\n'
    E'B) "4"（助詞選択）、"8"（連語修復）、"syn_ant" は 0 始まり、コンテナは固定で '
    E'{{"0": [{{"0": テキスト, "1": 正誤(true/false), "2": 説明}} を必ず4個、true は1個のみ], '
    E'"1": このセクション固有の追加フィールド}}。"4" の "1" は空欄にした助詞そのもの、"2" は '
    E'{{助詞: 誤用タイプのタグ}} の辞書；"8" の "1" は error_collocate（植えた誤った連語語、与えられた'
    E'連語そのものと重複してはならず、選択肢のいずれとも文字列一致してはならない）；"syn_ant" の "1" は '
    E'relation で "synonym" か "antonym" のみ。該当しない場合はキー自体を省略せず '
    E'{{"9": "no_particle_slot"}}（"4"）/ {{"9": "no_collocation"}}（"8"）/ {{"9": "no_relation"}}（"syn_ant"）'
    E'を返すこと（null は不可）。\n\n'
    E'== L1（聞き取り、リスニング専用 — 生成はするがレンダリングでは使われない。上記の注意を参照）==\n'
    E'4つの選択肢、1つが正解=対象語、誤答3つ。探し方：対象語の読みをモーラに分解し、位置ごとに1モーラだけ'
    E'別のモーラに置き換えた読みを作り、それが国語辞典に載る実在の語かどうかを確認する。実在するものだけを'
    E'採用し、実在しない読みは捨てる（音を合わせるために漢字を組み合わせて語をこしらえるのは最も重い違反 — '
    E'数を満たすために造語するな）。誤答の表記は対象語と同じ字種（漢字/かな）に揃え、対象語の同義語や'
    E'完全な同音同義語であってはならない。\n\n'
    E'== L3（文脈穴埋め）==\n'
    E'文インデックス {level_3_sentence_index_a} / {level_3_sentence_index_b} を使用。誤答3つは同じ品詞で'
    E'文法的には入るが意味/文脈上不適切。\n\n'
    E'== L4（助詞選択、該当する場合。非該当時は上記の "9" 転義規則に従うこと）==\n'
    E'文インデックス {level_4_sentence_index_a} / {level_4_sentence_index_b} の空欄に、正しい助詞と'
    E'3つの誤った助詞を生成。判定基準は「自然な文になるか」であり「意味が同じか」ではない（に/へ、は/が、'
    E'を/が のように、意味が異なっても両方自然な場合は誤答にしないこと）。\n\n'
    E'== L6（意味弁別）==\n'
    E'文インデックス {level_6_sentence_index_a} / {level_6_sentence_index_b} を正しい文とし、目標語を'
    E'含むが統語的に誤った文を3つ生成。\n\n'
    E'== L7（誤文発見）==\n'
    E'{level_7_correct_indices_a} / {level_7_correct_indices_b} を正しい文のインデックスとし、'
    E'目標語を含み学習者レベルで明確に識別可能な誤りを1つ含む文を各変体で生成。\n\n'
    E'== L8（連語修復、該当する場合）==\n'
    E'元文 {level_8_sentence_text_a} / {level_8_sentence_text_b}、正しい連語 {level_8_collocate_word}。'
    E'正解の選択肢テキストは指定された連語と文字レベルで完全一致すること。\n\n'
    E'== 類義語/対義語（type=syn_ant、該当する場合）==\n'
    E'教えている語義における正しい類義語/対義語と、その語義では明確に成立しない誤答を生成。他の一般的な'
    E'語義での類義語/対義語を誤答に選ばないよう注意（最終確認は ladder_bundle_judge が担当）。\n\n'
    E'出力構造（active_levels_json で要求されたキーのみ列挙。ただし "1" は常に含めること — 上記の注意を'
    E'参照。上記2つの番号体系を参照）：\n'
    E'{{"A": {{"1": [{{"1":..,"2":..,"3":..}} x4], "3": [{{"1":..,"2":..,"3":..}} x4], '
    E'"4": {{"0": [{{"0":..,"1":..,"2":..}} x4], "1": "blanked_particle", "2": {{}}}}, '
    E'"6": {{"1": 正しい文のインデックス, "2": [{{"1":..,"2":..}} x3]}}, '
    E'"7": {{"1":誤文,"2":正文,"3":説明,"4":[正しいインデックス]}}, '
    E'"8": {{"0": [{{"0":..,"1":..,"2":..}} x4], "1": "error_collocate"}}, '
    E'"syn_ant": {{"0": [{{"0":..,"1":..,"2":..}} x4], "1": "synonym"}}}}, '
    E'"B": {{...変体Bの文インデックスを使用し同構造...}}}}',
    3, false,
    'DRAFT (TASK-815, Phase 2, not applied): bundles P2(L1/L3/L6)+P3(L4 particle/L7/L8)+syn_ant for ja, both variants, one call. Gated on baseline + Phase 1 score; feature-flagged VOCAB_LADDER_BUNDLE_MODE (default off). v2: added register/sense_fingerprint inputs and an explicit numeric-key-contract section, same correction as the zh row. v3 (2026-09-27, post phase2_smoke_ja): restored the L1 section v2 wrongly dropped -- active_levels/p2_levels/validate_prompt2 are language-agnostic and still require a "1" key for ja (confirmed against the LIVE non-bundle vocab_prompt2_exercises ja prompt, which also still generates one, unused at render time, for the same reason); v2''s omission made every ja P2 block fail validation and fall back to the legacy call on 3/3 smoke senses. Render behavior for ja L1 is UNCHANGED by this fix (still exclusively the deterministic mora-trie, per l1_lookup.build_candidates -- see the header NOTE ON ja L1, also corrected in this pass).',
    3, 'qwen/qwen3.7-plus', 'openrouter'
);

-- ---------------------------------------------------------------------------
-- vocab_bundle_generation — en (PLACEHOLDER MODEL — TASK-817 bake-off is
-- Phase 3 and blocked; do not treat this model choice as decided)
-- ---------------------------------------------------------------------------
INSERT INTO prompt_templates
    (task_name, template_text, version, is_active, description, language_id, model, provider)
VALUES (
    'vocab_bundle_generation',
    E'Role: you are a computational linguist generating TWO complete exercise sets (variants A and '
    E'B) for an English vocabulary learner in one response.\n\n'
    E'Target word: {word}\nPOS: {pos}\nSemantic class: {semantic_class}\nLearner tier: {complexity_tier}\n'
    E'Definition: {definition}\nPrimary collocate: {primary_collocate}\nRegister: {register}\n'
    E'Sense fingerprint (disambiguation only, never echo it in the output): {sense_fingerprint}\n\n'
    E'Variant A base sentences (with sentence index): {sentences_json_a}\n'
    E'Variant B base sentences (with sentence index): {sentences_json_b}\n'
    E'Morphological forms (for L4): {morphological_forms_json}\n\n'
    E'Generate ONLY the levels/types listed in {active_levels_json} (same set for both variants).\n\n'
    E'== General rules ==\n'
    E'1. Output valid JSON only, numeric string keys.\n'
    E'2. The target word''s characters must carry the SAME syntactic/semantic role as the locked '
    E'sense in every sentence and option (matches Prompt 1 rule 13 — verify current wording before '
    E'implementing).\n'
    E'3. When uncertain, be strict: dropping a borderline option is cheaper than keeping one that '
    E'is actually valid.\n\n'
    E'== Output key numbering contract (two conventions, do not mix them) ==\n'
    E'A) Inside "1"/"3"/"5"/"6", option objects are 1-indexed: {{"1": option text, "2": is_correct '
    E'(true/false), "3": explanation}}. "6"''s container is {{"1": correct_sentence_index, '
    E'"2": [{{"1": wrong sentence text, "2": explanation}} x3]}}.\n'
    E'B) "4" (morphology), "8" (collocation repair), "syn_ant" and "word_family" are 0-indexed, fixed '
    E'container shape {{"0": [{{"0": text, "1": is_correct (true/false), "2": explanation}} x4, exactly '
    E'one true], "1": this section''s own extra field}}. "4"''s "1" is base_form and it additionally '
    E'needs "2"=form_label; "8"''s "1" is error_collocate (must differ from the given collocate and '
    E'from every option''s text); "syn_ant"''s "1" is relation, either "synonym" or "antonym"; '
    E'"word_family"''s "1" is stem, and every option in its array additionally needs "3"=part_of_speech. '
    E'When a section does not apply to this word, still emit its key as the escape object — never '
    E'omit the key and never return null: {{"9": "no_inflection"}} for "4", {{"9": "no_collocation"}} '
    E'for "8", {{"9": "no_relation"}} for "syn_ant", {{"9": "no_family"}} for "word_family".\n\n'
    E'== L1 (phonetic recognition, listening only) ==\n'
    E'4 options, 1 correct = target word, 3 distractors. Distractors must be real words that are '
    E'AUDIO-CONFUSABLE with the target (not a synonym, not a pure homograph indistinguishable by '
    E'ear, not a same-meaning alternative).\n\n'
    E'== L3 (cloze) ==\n'
    E'Use sentence index {level_3_sentence_index_a} / {level_3_sentence_index_b}. 3 distractors: '
    E'same POS, grammatical in the slot, wrong for the sentence''s meaning/context/collocation/'
    E'register/valency. Mandatory self-check per distractor: tag exactly one failure dimension '
    E'(semantic / collocational / aspectual / register / valency); run the synonym-substitution '
    E'audit (would a common synonym of the target make this distractor correct here? if yes, '
    E'replace it). The 3 distractors must span at least two different failure dimensions.\n\n'
    E'== L4 (morphology slot, if applicable; use the "9" escape above if not supported) ==\n'
    E'Use sentence index {level_4_sentence_index_a} / {level_4_sentence_index_b}. 3 distractor '
    E'forms must each be real word forms that are wrong for this context.\n\n'
    E'== L5 (collocation gap, if in active_levels_json) ==\n'
    E'Use sentence index {level_5_sentence_index_a} / {level_5_sentence_index_b}. Correct = primary '
    E'collocate; 3 distractors: same POS, semantically close, but an unnatural collocation with the '
    E'target here.\n\n'
    E'== L6 (semantic discrimination) ==\n'
    E'Sentence index {level_6_sentence_index_a} / {level_6_sentence_index_b} is the correct '
    E'sentence; generate 3 new sentences using the target word that are grammatical but semantically/'
    E'pragmatically/collocationally wrong.\n\n'
    E'== L7 (spot the error) ==\n'
    E'{level_7_correct_indices_a} / {level_7_correct_indices_b} are correct-sentence indices; '
    E'generate one new sentence per variant containing the target word with exactly one clearly '
    E'identifiable structural error appropriate to {complexity_tier}.\n\n'
    E'== L8 (collocation repair, if applicable) ==\n'
    E'Source sentence {level_8_sentence_text_a} / {level_8_sentence_text_b}, correct collocate '
    E'{level_8_collocate_word}. Hard rules: the correct option''s text must be character-for-'
    E'character identical to the given collocate; exactly one option is true; no distractor '
    E'duplicates the correct collocate; distractors share the collocate''s POS.\n\n'
    E'== Synonym/antonym (type=syn_ant, if applicable) ==\n'
    E'Generate a correct synonym/antonym for the TAUGHT sense, and distractors that clearly do NOT '
    E'hold that relation for that sense. Avoid picking a distractor that is a synonym/antonym of '
    E'the target under one of its OTHER common senses — final cross-sense verification happens in '
    E'ladder_bundle_judge, but a generation-time miss here costs a judge reject.\n\n'
    E'== Word family (type=word_family, English only, if applicable) ==\n'
    E'Correct answer is a REAL derived word. Distractors must be well-formed but INVENTED — plausible '
    E'morphology that does not correspond to an actual English word (e.g. "decisionment" for the '
    E'-ment family of "decide", when "decisive" is the real form).\n\n'
    E'Output structure (list only the keys active_levels_json asked for; see the two numbering '
    E'conventions above): {{"A": {{"1": [{{"1":..,"2":..,"3":..}} x4], "3": [{{"1":..,"2":..,"3":..}} x4], '
    E'"4": {{"0": [{{"0":..,"1":..,"2":..}} x4], "1": "base_form", "2": "form_label"}}, '
    E'"5": [{{"1":..,"2":..,"3":..}} x4], "6": {{"1": idx, "2": [{{"1":..,"2":..}} x3]}}, '
    E'"7": {{"1":..,"2":..,"3":..,"4":[..]}}, '
    E'"8": {{"0": [{{"0":..,"1":..,"2":..}} x4], "1": "error_collocate"}}, '
    E'"syn_ant": {{"0": [{{"0":..,"1":..,"2":..}} x4], "1": "synonym"}}, '
    E'"word_family": {{"0": [{{"0":..,"1":..,"2":..,"3":..}} x4], "1": "stem"}}}}, '
    E'"B": {{...same shape, variant B sentence indices...}}}}',
    2, false,
    'DRAFT (TASK-815, Phase 2, not applied): bundles P2+P3+syn_ant+word_family for en, both variants, one call. Model set to qwen/qwen3.7-plus per the Phase 2 brief ("en any, qwen/qwen3.7-plus planned"); TASK-817''s bake-off (Phase 3, blocked) is still the actual ratification. Gated on baseline + Phase 1 score; feature-flagged VOCAB_LADDER_BUNDLE_MODE (default off). v2: added register/sense_fingerprint inputs and an explicit numeric-key-contract section, same correction as the zh/ja rows.',
    2, 'qwen/qwen3.7-plus', 'openrouter'
);

-- ---------------------------------------------------------------------------
-- ladder_bundle_judge — zh (qwen/qwen3.7-plus — judges stay on their current
-- models per ADR-028 open question (a); this row's model is a PLACEHOLDER for
-- Phase 2 prototyping only, NOT a decision to move judges onto qwen)
-- ---------------------------------------------------------------------------
INSERT INTO prompt_templates
    (task_name, template_text, version, is_active, description, language_id, model, provider)
VALUES (
    'ladder_bundle_judge',
    E'你是词汇练习题的严格综合评审，需要在一次回答中对多个不同类型的候选项打分。以下是共享原则，'
    E'适用于每一个小节：不确定时从严评判（宁可拒绝一个临界候选项，也不要放过一个其实成立的）；'
    E'每一项都必须评分，不得省略；只返回 JSON，JSON 之外不得有任何文字，不得使用代码块。\n\n'
    E'仅回答以下在本次请求中实际提供的小节（未提供输入的小节请完全省略对应顶层键）：\n\n'
    E'每个小节下面的编号列表可能混合了变体 A 和变体 B 的条目（每行开头以 [A]/[B] 标出所属变体），'
    E'且每一行已自带该条目所需的全部上下文——请只依据该行给出的上下文判断该行，不要与其他行混同。'
    E'编号是跨变体连续的全局编号，返回时必须使用同样的编号作为键。\n\n'
    E'== sentence_validity（L6/L7 错误句判断）==\n'
    E'目标词：{target}\n'
    E'{sentence_validity_pairs_numbered}\n'
    E'对每句评估其"因标注原因而错误"的干净程度，1-5 分（5=明显因标注原因而错；1=实际合乎语法，不能用作错句）。'
    E'返回：{{"<索引>": {{"rating": 1-5, "reason": "..."}}}}\n\n'
    E'== cloze（L3 干扰项）==\n'
    E'{cloze_items_numbered}\n'
    E'对每项判定 keep（明显错误，可安全作为干扰项）或 reject（该项本身也可被'
    E'合理选中，包括同义词/近义词）。返回：{{"<索引>": {{"verdict": "keep|reject", "reason": "..."}}}}\n\n'
    E'== l1_distractor（L1 听力干扰项）==\n'
    E'{l1_items_numbered}\n'
    E'keep = 真实字/词、与目标声调混淆但非同义词；reject = 非真实词，或为同义词，或纯形近而读音无关，'
    E'或与目标完全同音同调。返回：{{"<索引>": {{"verdict": "keep|reject", "reason": "..."}}}}\n\n'
    E'== collocation（L5/L8 搭配干扰项）==\n'
    E'{collocation_items_numbered}\n'
    E'评估其作为"非搭配"的明显程度，1-5 分（5=明显不能搭配；'
    E'1=同样地道的搭配，绝不可作干扰项）。返回：{{"<索引>": {{"rating": 1-5, "reason": "..."}}}}\n\n'
    E'== relation（近义/反义干扰项）==\n'
    E'{relation_items_numbered}\n'
    E'关键规则：必须检查目标词的**所有**义项，不只是所教的那个——例如"走"不是"银行"义"行"的近义词，'
    E'但是"行走"义"行"的近义词；只看所教义项会误判。与**任一**义项构成该关系的候选词一律评 1 分（不可用）。'
    E'1-5 分，5=与任何义项都无关（理想干扰项）。返回：{{"<索引>": {{"0": 1-5, "1": "..."}}}}\n\n'
    E'仅返回上面各小节要求的 JSON，顶层键为本节标题（sentence_validity/cloze/l1_distractor/'
    E'collocation/relation），值为该小节的索引化评分对象。',
    2, false,
    'DRAFT (TASK-816, Phase 2, not applied): bundles sentence_validity+cloze+l1_distractor+collocation+relation render judges for zh into one call, both variants combined into one flat cross-variant numbering per axis (per-item verdicts mapped back to existing judge shapes). Model is a Phase-2 prototyping placeholder, NOT a judge-model decision (ADR-028 open question (a) is unresolved). P1 sentence judge stays separate. Feature-flagged VOCAB_LADDER_BUNDLE_MODE (default off). v2: replaced single-context per-axis placeholders (one sentence/target/correct per axis) with self-contained numbered items, since v1 could not actually represent two variants'' independent contexts in one call.',
    1, 'qwen/qwen3.7-plus', 'openrouter'
);

-- ---------------------------------------------------------------------------
-- ladder_bundle_judge — ja (placeholder model; adds particle, drops l1_distractor
-- per the ja-L1-is-deterministic note above)
-- ---------------------------------------------------------------------------
INSERT INTO prompt_templates
    (task_name, template_text, version, is_active, description, language_id, model, provider)
VALUES (
    'ladder_bundle_judge',
    E'あなたは語彙練習問題の厳格な総合評価者で、一度の応答で複数の異なるタイプの候補を評価します。'
    E'共通原則：迷ったときは厳格に（境界的な候補を却下する方が、実は成立する候補を見逃すより安全）；'
    E'すべての項目を評価すること；JSON のみを返し、それ以外の文章もコードフェンスも禁止。\n\n'
    E'このリクエストで実際に入力が提供されたセクションのみ回答すること（入力がないセクションは'
    E'トップレベルキーごと省略）。\n\n'
    E'各セクションの番号付きリストには変体AとBの項目が混在することがあります（各行の先頭に '
    E'[A]/[B] でどちらの変体かを明記）。各行にはその項目を判定するのに必要な文脈がすべて含まれて'
    E'いるので、他の行の文脈と混同しないこと。番号は変体をまたいだ通し番号で、返答にも同じ番号を'
    E'キーとして使うこと。\n\n'
    E'== sentence_validity（L6/L7 誤文判定）==\n'
    E'目標語：{target}\n'
    E'{sentence_validity_pairs_numbered}\n'
    E'各文について、想定理由通りに誤っている「きれいさ」を1-5で評価（5=明確に想定理由通りに誤り；'
    E'1=実際には文法的に正しく誤文として使えない）。返す形式：{{"<index>": {{"rating": 1-5, "reason": "..."}}}}\n\n'
    E'== cloze（L3 誤答選択肢）==\n'
    E'{cloze_items_numbered}\n'
    E'各候補を keep（明確に誤りで安全な誤答）または reject'
    E'（それ自体も妥当な答えになりうる、類義語含む）と判定。返す形式：'
    E'{{"<index>": {{"verdict": "keep|reject", "reason": "..."}}}}\n\n'
    E'== collocation（L5/L8 連語誤答）==\n'
    E'{collocation_items_numbered}\n'
    E'「連語として不自然である」度合いを1-5で評価'
    E'（5=明確に連語として不自然；1=同様に自然な連語で誤答に使用不可）。'
    E'返す形式：{{"<index>": {{"rating": 1-5, "reason": "..."}}}}\n\n'
    E'== particle（L4 助詞誤答）==\n'
    E'{particle_items_numbered}\n'
    E'重要規則：判定すべきは「自然な文になるか」であり'
    E'「意味が同じか」ではない（に/へ、は/が、を/が のように意味が違っても両方自然な場合は誤答にしないこと）。'
    E'1-5で評価（5=非文/明確に不自然；1=完全に自然で誤答に使用不可）。'
    E'返す形式：{{"<index>": {{"0": 1-5, "1": "..."}}}}\n\n'
    E'上記の各セクションで要求された JSON のみを返すこと。トップレベルキーはセクション名'
    E'（sentence_validity/cloze/collocation/particle）。',
    2, false,
    'DRAFT (TASK-816, Phase 2, not applied): bundles sentence_validity+cloze+collocation+particle render judges for ja into one call, both variants combined into one flat cross-variant numbering per axis. NO l1_distractor axis (ja L1 is deterministic, not judged here). Model is a Phase-2 prototyping placeholder. P1 sentence judge stays separate. Feature-flagged VOCAB_LADDER_BUNDLE_MODE (default off). v2: same self-contained-numbered-items correction as the zh row.',
    3, 'qwen/qwen3.7-plus', 'openrouter'
);

-- ---------------------------------------------------------------------------
-- ladder_bundle_judge — en (google/gemini-3.5-flash-lite — the model is NOT a
-- placeholder here: it is en's actual live per-judge model today, verified
-- 2026-09-27 against cloze_distractor_judge / ladder_l1_distractor_judge /
-- ladder_collocation_judge / ladder_relation_judge /
-- ladder_sentence_validity_judge / ladder_word_family_judge, all
-- language_id=2, version=1, is_active=true — every one of en's judges
-- already shares this one model, unlike zh/ja where the judge model in this
-- file is an unresolved placeholder per ADR-028 open question (a)).
--
-- Adds l1_distractor (en L1 is an LLM judge call, unlike ja's deterministic
-- mora-trie path — see the ja row's note above) and word_family (en-only,
-- per rule 6 in the header's RULES PRESERVED section) relative to the ja row;
-- keeps relation (en also generates syn_ant, per the en
-- vocab_bundle_generation row above); drops particle (ja L4-only).
-- NOT YET READABLE BY CODE — see the ROLLBACK section's note above this
-- block for the two gaps (BundleJudge._SUPPORTED_LANGUAGES, and the missing
-- word_family axis in judge.py entirely) a follow-up task must close first.
-- ---------------------------------------------------------------------------
INSERT INTO prompt_templates
    (task_name, template_text, version, is_active, description, language_id, model, provider)
VALUES (
    'ladder_bundle_judge',
    E'You are a strict, comprehensive judge for vocabulary exercises, scoring several different '
    E'candidate types in one response. Shared principles for every section: when unsure, judge '
    E'strictly — dropping a borderline candidate is cheaper than shipping one that is actually '
    E'usable; every listed item must be rated, none omitted; return JSON only, nothing outside the '
    E'JSON, no markdown code fences.\n\n'
    E'Answer ONLY the sections whose input is actually provided in this request — omit the entire '
    E'top-level key for any section with no input.\n\n'
    E'The numbered list under each section may mix variant A and variant B items (each line starts '
    E'with [A]/[B] marking which variant it belongs to), and each line already carries all the '
    E'context you need to judge it — judge each line only from its own context, never against '
    E'another line. Numbering is one continuous sequence across both variants; return your answer '
    E'keyed by that same numbering.\n\n'
    E'== sentence_validity (L6/L7 wrong-sentence check) ==\n'
    E'Target word: {target}\n'
    E'{sentence_validity_pairs_numbered}\n'
    E'For each sentence, rate 1-5 how cleanly it is wrong FOR ITS LABELED REASON (5 = clearly '
    E'incorrect, exactly for the labeled reason; 3 = borderline; 2 = incorrect, but for a DIFFERENT '
    E'reason than labeled — the shown explanation would mislead the learner; 1 = actually acceptable/'
    E'grammatical, not wrong at all). Return: {{"<index>": {{"rating": 1-5, "reason": "..."}}}}\n\n'
    E'== cloze (L3 distractors) ==\n'
    E'{cloze_items_numbered}\n'
    E'For each distractor: "keep" = grammatical in the slot but clearly semantically, '
    E'collocationally, aspectually, register-wise, or valency-wise wrong in this sentence; "reject" '
    E'= a competent reader could select it as a valid completion here (synonyms and near-synonyms '
    E'must be rejected). Return: {{"<index>": {{"verdict": "keep|reject", "reason": "..."}}}}\n\n'
    E'== l1_distractor (L1 listening distractors) ==\n'
    E'{l1_items_numbered}\n'
    E'"keep" = a real English word genuinely AUDIO-CONFUSABLE with the target (homophone, near-'
    E'homophone, or a minimal pair a learner could mishear) and NOT a synonym of it. "reject" = not '
    E'a real word, OR a synonym/near-synonym, OR similar only in SPELLING and not in sound (e.g. '
    E'"tough" vs "though"), OR the target itself under a different inflection. When unsure whether '
    E'two words are confusable by ear, reject. Return: '
    E'{{"<index>": {{"verdict": "keep|reject", "reason": "..."}}}}\n\n'
    E'== collocation (L5/L8 collocation distractors) ==\n'
    E'{collocation_items_numbered}\n'
    E'Rate 1-5 how clearly each candidate is a genuine NON-collocate of the target in this sentence '
    E'(5 = obviously unnatural/wrong; 3 = borderline; 1 = fully idiomatic and just as correct as the '
    E'given answer — must never be used as a wrong answer). Judge collocational naturalness, not '
    E'mere grammaticality. Return: {{"<index>": {{"rating": 1-5, "reason": "..."}}}}\n\n'
    E'== relation (synonym/antonym distractors, type=syn_ant if applicable) ==\n'
    E'{relation_items_numbered}\n'
    E'Key rule: check the candidate against ALL of the target''s senses, not only the one being '
    E'taught — e.g. "shore" is not a synonym of "bank" (financial institution) but IS a synonym of '
    E'"bank" (riverbank), so a learner reading that sense would pick it. A candidate that holds the '
    E'relation under ANY sense of the target must rate 1 (unusable), even if not under the taught '
    E'sense. Rate 1-5 (5 = unrelated to every sense — an ideal wrong answer; 1 = a full match under '
    E'the taught sense or another sense). Return: {{"<index>": {{"0": 1-5, "1": "..."}}}}\n\n'
    E'== word_family (invented-derivation distractors, English only, type=word_family if applicable) ==\n'
    E'{word_family_items_numbered}\n'
    E'These distractors are supposed to be well-formed but INVENTED — not real English words. Judge '
    E'word-hood, not well-formedness: "decisionment" is well-formed and still not a word (rate 5, a '
    E'safe distractor); "decisive" is a real word (rate 1, unusable) even though it is an obvious '
    E'member of the same family. Count technical, archaic, and dialectal words as real. Rate 1-5 how '
    E'confidently each candidate is NOT a real, current English word (5 = certainly not a word; 3 = '
    E'uncertain, may be technical/archaic; 1 = definitely a real, current word). Return: '
    E'{{"<index>": {{"0": 1-5, "1": "..."}}}}\n\n'
    E'Return only the JSON for the sections above that were actually given input this request. '
    E'Top-level keys: sentence_validity / cloze / l1_distractor / collocation / relation / '
    E'word_family. No prose outside the JSON, no code fences.',
    1, false,
    'DRAFT (TASK-816, Phase 2, not applied): bundles sentence_validity+cloze+l1_distractor+collocation+relation+word_family render judges for en into one call, both variants combined into one flat cross-variant numbering per axis (self-contained numbered items with an [A]/[B] tag per line, the same design zh/ja needed a v2 to reach — en starts there directly since there was no earlier en draft to correct). NO particle axis (ja L4-only). Model is en''s actual current per-judge model (google/gemini-3.5-flash-lite, verified live 2026-09-27 across all six of en''s existing judge task_names), not a placeholder like the zh/ja rows'' model. NOT YET READABLE: BundleJudge._SUPPORTED_LANGUAGES (judge.py) excludes language_id=2 today, and no word_family axis (dataclass/resolver/prompt_var) exists anywhere in judge.py yet — both must be added before this row can be wired or activated. P1 sentence judge stays separate. Feature-flagged VOCAB_LADDER_BUNDLE_MODE (default off).',
    2, 'google/gemini-3.5-flash-lite', 'openrouter'
);

COMMIT;

-- Verification (run manually):
-- SELECT task_name, language_id, version, is_active, model
-- FROM prompt_templates
-- WHERE task_name IN ('vocab_bundle_generation', 'ladder_bundle_judge')
-- ORDER BY task_name, language_id;
-- Expect 6 rows total (3 vocab_bundle_generation: zh/ja/en; 3 ladder_bundle_judge: zh/ja/en),
-- all is_active = false. The en ladder_bundle_judge row is inert until both
-- gaps noted above it (and above the ja row's ROLLBACK note) are closed in code.
