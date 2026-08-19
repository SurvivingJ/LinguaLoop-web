-- ============================================================================
-- TASK-520 — Per-exercise-type prompt split: L4 morphology + L8 collocation
--            repair out of the vocab_prompt3_transforms monolith.
-- Date: 2026-08-09
-- Revised: 2026-08-11 (TASK-537/538) — numeric-key output contract.
--
-- WHY
-- ---
-- vocab_prompt3_transforms asked one model, in one call, for morphology (L4),
-- a crafted wrong sentence (L7) and a collocation repair (L8). Audit findings
-- B3.2 / B3.4: the two failure-prone levels were coupled to the cheap one for
-- model choice, for retry, and for JSON validity — one malformed array killed
-- all three, and a missing L4 forced a regeneration of L7 and L8 as well.
--
-- WHAT THIS FILE DOES
-- -------------------
--   1. Seeds ladder_l4_morphology_generation           v1 for en / zh / ja
--   2. Seeds ladder_l8_collocation_repair_generation   v1 for en / zh / ja
--   3. Records the narrowing on the surviving vocab_prompt3_transforms rows.
--
-- This file only writes these task_names and annotates descriptions; it
-- redefines no existing object, so no older migration is superseded by it.
--
-- RE-RUNNABLE, AND CORRECTIVE (TASK-538)
-- --------------------------------------
-- Every row here is ON CONFLICT ... DO UPDATE, not DO NOTHING. The English
-- rows went live on 2026-08-10 carrying the old named-key contract, and
-- DO NOTHING made a corrected re-run a silent no-op — the file looked applied
-- while the live prompt still asked for English field names. DO UPDATE makes
-- applying this file converge the live rows on the text below whatever state
-- they are in.
--
-- OUTPUT-SCHEMA CONTRACT (enforced in Python before any remap)
-- ------------------------------------------------------------
-- The shape below is bound to prompt_version. It is validated by
-- services/exercise_generation/schemas/ladder_l4_morphology.py and
-- .../ladder_l8_repair.py, whose PROMPT_VERSIONS sets currently contain {1}.
-- **Re-authoring these prompts at v2 without adding 2 to PROMPT_VERSIONS is a
-- hard failure, by design** — an ungated prompt version is refused rather than
-- validated against a schema it may no longer match.
--
-- Keys are NUMERIC, not field names. 0 is always the option array and 9 is
-- always the error escape; each prompt declares its own legend, in its own
-- language, before its rules. The reason is contamination: an English field
-- name like "is_correct" in the output contract of a ZH or JA prompt is English
-- inside the generation context, and it drags the model's prose toward English.
-- Escape *token values* stay English ASCII — they are a closed enum matched by
-- code, never shown to a learner.
--
--   L4 (morphology_slot):
--     {"0": [{"0": str, "1": bool, "2": str} x4], "1": str, "2": str}
--       0 = options, 1 = base_form, 2 = form_label
--       within an option: 0 = text, 1 = is_correct, 2 = explanation
--     Exactly one option carries 1 = true.  Escape: {"9": "no_inflection"}
--
--   L8 (collocation_repair):
--     {"0": [{"0": str, "1": bool, "2": str} x4], "1": str}
--       0 = options, 1 = error_collocate
--     Exactly one option correct; error_collocate must NOT equal any option
--     text (the planted error must not be selectable as the repair).
--     Escape: {"9": "no_collocation"}
--
-- Placeholders are substituted by asset_generators/_renderer.render_template,
-- which only replaces {bare_identifier} tokens — JSON braces in the examples
-- below are left alone and must NOT be doubled. (The judge prompts in
-- syn_ant_word_family_prompts.sql go through str.format and DO double theirs.)
--
-- MODEL RATIONALE (the point of the split)
-- ----------------------------------------
-- L4 needs real morphological knowledge of the target language, so English
-- keeps the Sonnet tier the monolith used. L8 is a naturalness judgement with
-- the collocation judge as a backstop, so English drops to the flash tier —
-- a saving that was simply not expressible while both shared one task_name.
-- zh/ja stay on qwen3.7-plus, matching their P1/P3 rows (see the model-slug
-- health cron, TASK-510: qwen-max was delisted).
-- ============================================================================


-- ----------------------------------------------------------------------------
-- 1. ladder_l4_morphology_generation — English (language_id = 2), v1
-- ----------------------------------------------------------------------------
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_l4_morphology_generation',
    2,
    1,
    $PROMPT$Role: Expert English morphologist writing ONE inflection-slot exercise.

The learner sees the sentence below with the target word blanked out, and picks the correctly inflected form from four options. Your job is to produce those four options.

Keys (the JSON you return uses these numeric keys, never field names):
0: the array of four options
1: the dictionary headword of the target lemma
2: the grammatical name of the CORRECT form
Within each option object:
0: the option text   1: whether it is the correct answer (true / false)   2: the one-clause explanation

Target word (lemma): {word}
Part of speech: {pos}
Semantic class: {semantic_class}
Definition (the ONE sense being taught): {definition}
Sense fingerprint: {sense_fingerprint}
Register: {register}
Complexity tier: {complexity_tier}

The sentence (the blank replaces the target occurrence):
{sentence_text}

The form that currently occupies the slot: {target_word}
Attested morphological forms of this lemma: {morphological_forms_json}
Forms already used as distractors elsewhere in this word's item set — do not reuse: {used_distractors_json}

Rules:
1. Exactly ONE option is correct: the form that grammatically fits the slot in this sentence. It must be the form shown above as occupying the slot.
2. The three distractors must be OTHER inflected forms of the SAME lemma — never a different word, never an invented form. For "decide" the usable distractors are "decided", "deciding", "decides"; "decision" is NOT usable (a derivation, a different word) and "deciden" is NOT usable (invented). Draw from the attested forms where possible; if the lemma has fewer than four real forms, use regular productive inflections of it (plural, -ing, -ed, comparative) that are genuine English words.
3. Each distractor must be grammatically WRONG in this exact slot. If a form would ALSO read acceptably, choose a different one. Example: in "She ___ to the shop yesterday" the answer is "walked", and "had walked" also reads acceptably there — so "had walked" is unusable, while "walks" is a sound distractor because the past-time adverbial rules it out.
4. Every option needs a one-clause explanation naming the grammatical reason it fits or fails (tense, number, agreement, aspect, degree). Explanations are shown to the learner after answering.
5. Key 1 is the dictionary headword. Key 2 names the grammatical form of the CORRECT option, in plain English (e.g. "past simple", "third-person singular", "plural", "comparative").
6. If this lemma genuinely does not inflect, return exactly {"9": "no_inflection"} and nothing else — do not manufacture forms. This covers modals ("must", "ought") and invariant nouns ("information", "equipment").

Return JSON ONLY, no prose and no markdown fences:
{"0": [{"0": "ran", "1": true, "2": "past simple, required by 'yesterday'"}, {"0": "run", "1": false, "2": "bare infinitive cannot carry past reference here"}, {"0": "running", "1": false, "2": "present participle needs an auxiliary"}, {"0": "runs", "1": false, "2": "third-person present clashes with the past-time adverbial"}], "1": "run", "2": "past simple"}$PROMPT$,
    true,
    'anthropic/claude-sonnet-5',
    'openrouter',
    'L4 morphology slot (English), split out of vocab_prompt3_transforms by TASK-520. Own model tier: inflection needs real grammatical knowledge. Numeric-key output contract (TASK-537/538) bound to prompt_version 1 (schemas/ladder_l4_morphology.py).'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
SET template_text = EXCLUDED.template_text,
    is_active     = EXCLUDED.is_active,
    model         = EXCLUDED.model,
    provider      = EXCLUDED.provider,
    description   = EXCLUDED.description;

COMMIT;


-- ----------------------------------------------------------------------------
-- 2. ladder_l4_morphology_generation — Chinese (language_id = 1), v1
-- ----------------------------------------------------------------------------
-- Seeded for completeness. The capability row ('morphology_slot', lang 1) is
-- is_enabled = FALSE — Chinese is analytic, and ZH L4 is served by
-- classifier_match + cloze_typed instead. This row exists so that enabling the
-- matrix flag is a one-line change rather than a prompt-authoring exercise;
-- until then nothing calls it. The prompt is framed as compound completion
-- (the ZH P3 reinterpretation) rather than inflection, because asking a model
-- for Chinese "inflected forms" is exactly how invented morphology got into
-- the corpus in the first place. It is rewritten on the numeric contract along
-- with the rest: an inert row left on the old contract is the one most likely
-- to be enabled years later by someone who does not know it was skipped.
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_l4_morphology_generation',
    1,
    1,
    $PROMPT$角色：你是一位汉语构词法专家，正在编写一道「构词填空」练习。

学习者看到下面的句子，目标词处留空，需从四个选项中选出唯一正确的词形。请生成这四个选项。

键（返回的 JSON 只使用下列数字键，不得使用字段名称）：
0：四个选项组成的数组
1：词条本身
2：正确选项的构词关系名称
每个选项对象内部：
0：选项文字   1：是否为正确答案（true / false）   2：一句话解释

目标词（词条）：{word}
词性：{pos}
语义类：{semantic_class}
释义（正在教授的唯一义项）：{definition}
义项指纹：{sense_fingerprint}
语域：{register}
难度层级：{complexity_tier}

句子（空缺处即目标词出现的位置）：
{sentence_text}

当前填在空缺处的形式：{target_word}
该词条已记录的相关词形：{morphological_forms_json}
本词条其它题目已用过的干扰项，不得重复：{used_distractors_json}

规则：
1. 有且仅有一个选项正确：即在此句空缺处成立的词形，必须与上面「当前填在空缺处的形式」一致。
2. 汉语没有屈折变化。三个干扰项须是与目标词共享语素的**真实存在的**近义 / 同素复合词或派生词（例如 目标「学习」→「学问」「学业」「进修」），绝不可自造词形，也不可添加不存在的词缀。
3. 每个干扰项在此句中必须明显不成立 —— 搭配不当、语体不合或义项不符。若某干扰项读起来也通顺，请换一个。例如「他每天都在___汉语」中「学习」为正解，而「进修」也能读通，因此「进修」不可用作干扰项；「学问」是名词，在此处明显不成立，可以使用。
4. 每个选项都要一句话解释其成立或不成立的构词 / 搭配理由，答题后展示给学习者。
5. 键 1 填该词条本身；键 2 用简明中文说明正确选项的构词关系（例如「动宾式复合词」「同素近义词」「双音节化形式」）。
6. 若该词条确实没有可用于构词对比的同素词（例如「的」「吗」一类虚词），返回 {"9": "no_inflection"}，不要输出其它内容，切勿自造词。

仅返回 JSON，不要任何解说文字，不要 markdown 代码块：
{"0": [{"0": "学习", "1": true, "2": "与「每天」搭配，指持续的求知行为"}, {"0": "学问", "1": false, "2": "名词，指知识本身，不能作此句谓语"}, {"0": "学业", "1": false, "2": "指学习任务，与此处动作义不符"}, {"0": "求学", "1": false, "2": "指到外地上学，语域与此句不合"}], "1": "学习", "2": "同素近义词"}$PROMPT$,
    true,
    'qwen/qwen3.7-plus',
    'openrouter',
    'L4 compound-completion (Chinese), split out by TASK-520. Inert while the ZH morphology_slot capability row stays disabled. Numeric-key output contract (TASK-537/538) bound to prompt_version 1.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
SET template_text = EXCLUDED.template_text,
    is_active     = EXCLUDED.is_active,
    model         = EXCLUDED.model,
    provider      = EXCLUDED.provider,
    description   = EXCLUDED.description;

COMMIT;


-- ----------------------------------------------------------------------------
-- 3. ladder_l4_morphology_generation — Japanese (language_id = 3), v1
-- ----------------------------------------------------------------------------
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_l4_morphology_generation',
    3,
    1,
    $PROMPT$役割：あなたは日本語の活用形を専門とする言語学者で、活用スロット問題を1問作成します。

学習者は下の文の目標語が空欄になったものを見て、4つの選択肢から正しい活用形を選びます。その4つの選択肢を作ってください。

キー（返す JSON は名称ではなく下記の数字キーのみを使う）：
0：4つの選択肢の配列
1：辞書形
2：正解の活用形の名称
各選択肢オブジェクトの内部：
0：選択肢の文字列   1：正解かどうか（true / false）   2：一文の説明

目標語（辞書形）：{word}
品詞：{pos}
意味クラス：{semantic_class}
語義（教える対象の唯一の意味）：{definition}
語義フィンガープリント：{sense_fingerprint}
文体・待遇レベル：{register}
難易度ティア：{complexity_tier}

文（空欄は目標語の出現箇所）：
{sentence_text}

空欄に入っている形：{target_word}
記録済みの活用形：{morphological_forms_json}
この語の他の問題で既に使った誤答。再利用禁止：{used_distractors_json}

規則：
1. 正解はちょうど1つ。この文の空欄で文法的に成立する形であり、上の「空欄に入っている形」と一致すること。
2. 誤答3つは**同じ語**の別の活用形であること。別語や実在しない形は不可。ます形・た形・て形・ない形・可能形・受身形・意向形など、実在する活用から選ぶ。例：「食べる」なら「食べる」「食べて」「食べない」は使えるが、「食事」は別語なので不可、「食べらた」は実在しない形なので不可。
3. 各誤答はこの空欄で明確に不適切であること（時制、態、接続、待遇レベルの不一致）。自然に読めてしまう形は選ばない。例：「昨日パンを___」で正解が「食べた」のとき、「食べました」も自然に読めるため誤答には使えない。「食べる」は「昨日」と衝突するので誤答として適切。
4. 各選択肢に、成立／不成立の文法的理由を一文で付ける。解答後に学習者へ提示される。
5. キー 1 は辞書形。キー 2 は正解の活用形の名称を日本語で（例：「た形（過去）」「て形」「ない形」「可能形」）。
6. 活用しない語（「情報」「本」などの名詞で活用対比が作れない語）の場合は {"9": "no_inflection"} だけを返し、形を捏造しないこと。

JSON のみを返すこと。説明文も markdown コードフェンスも不可：
{"0": [{"0": "食べた", "1": true, "2": "「昨日」があるので過去のた形が必要"}, {"0": "食べる", "1": false, "2": "辞書形では過去を表せない"}, {"0": "食べて", "1": false, "2": "て形は後続要素を要求し文が終わらない"}, {"0": "食べない", "1": false, "2": "否定形は文意と矛盾する"}], "1": "食べる", "2": "た形（過去）"}$PROMPT$,
    true,
    'qwen/qwen3.7-plus',
    'openrouter',
    'L4 morphology slot (Japanese), split out by TASK-520. Numeric-key output contract (TASK-537/538) bound to prompt_version 1 (schemas/ladder_l4_morphology.py).'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
SET template_text = EXCLUDED.template_text,
    is_active     = EXCLUDED.is_active,
    model         = EXCLUDED.model,
    provider      = EXCLUDED.provider,
    description   = EXCLUDED.description;

COMMIT;


-- ----------------------------------------------------------------------------
-- 4. ladder_l8_collocation_repair_generation — English (language_id = 2), v1
-- ----------------------------------------------------------------------------
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_l8_collocation_repair_generation',
    2,
    1,
    $PROMPT$Role: Expert of English collocation writing ONE collocation-repair exercise.

The learner is shown the sentence with a WRONG collocate substituted in, and must repair it by choosing the natural partner of the target word. Produce the four options and the wrong word to plant.

Keys (the JSON you return uses these numeric keys, never field names):
0: the array of four options
1: the wrong collocate to plant in the sentence
Within each option object:
0: the option text   1: whether it is the correct answer (true / false)   2: the one-clause explanation

Target word: {target_word}
Lemma: {word}
Part of speech: {pos}
Semantic class: {semantic_class}
Definition (the ONE sense being taught): {definition}
Sense fingerprint: {sense_fingerprint}
Register: {register}
Complexity tier: {complexity_tier}

The sentence (it already contains the correct collocate):
{sentence_text}

The correct collocate, which occurs in that sentence: {primary_collocate}
Evidence for that collocate: {collocate_grounding}
  corpus_validated = attested in a frequency source; treat it as fixed.
  llm_asserted     = asserted without corpus backing; if it is NOT in fact an
                     idiomatic partner of the target, say so via the key 9
                     escape below rather than building an exercise on it.
Words already used as distractors elsewhere in this word's item set — do not reuse: {used_distractors_json}

Rules:
1. Exactly ONE option is correct: {primary_collocate}, the collocate that actually appears in the sentence.
2. The three distractors must be real, common words of the same part of speech that could grammatically occupy the slot but are NOT idiomatic with the target. Grammatical-but-unnatural is exactly the target ("do homework" vs "make homework"). Never choose a word that a fluent speaker might also accept — for "make a decision", "take a decision" is accepted by many speakers and is therefore unusable, while "build a decision" is sound.
3. Key 1 is the word to plant in the sentence in place of the correct one. It must be a distractor-grade word — clearly wrong with the target — but it MUST NOT be listed among the four options: the learner has to supply the repair, not spot the planted word in the list. Choose the word whose wrongness is clearest. Example: for "brew coffee" with options brew / cook / build / prepare, plant "manufacture" — obviously wrong, and absent from the list.
4. Every option gets a one-clause explanation: why the correct one is idiomatic, and why each wrong one is not.
5. If the target has no genuine fixed collocate here — if {primary_collocate} is a free combination rather than a collocation — return exactly {"9": "no_collocation"} and nothing else. A repair exercise built on a non-collocation teaches a rule that does not exist. Example: "see a house" is a free combination and cannot carry an item; "pay attention" is a real collocation and can.

Return JSON ONLY, no prose and no markdown fences:
{"0": [{"0": "brew", "1": true, "2": "'brew coffee' is the established pairing"}, {"0": "cook", "1": false, "2": "'cook coffee' is not used of beverages"}, {"0": "build", "1": false, "2": "'build' takes constructed objects"}, {"0": "prepare", "1": false, "2": "grammatical but generic; not the fixed partner"}], "1": "manufacture"}$PROMPT$,
    true,
    'google/gemini-3.5-flash',
    'openrouter',
    'L8 collocation repair (English), split out of vocab_prompt3_transforms by TASK-520. Cheaper tier than L4: the collocation judge backstops the semantic call. Numeric-key output contract (TASK-537/538) bound to prompt_version 1 (schemas/ladder_l8_repair.py).'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
SET template_text = EXCLUDED.template_text,
    is_active     = EXCLUDED.is_active,
    model         = EXCLUDED.model,
    provider      = EXCLUDED.provider,
    description   = EXCLUDED.description;

COMMIT;


-- ----------------------------------------------------------------------------
-- 5. ladder_l8_collocation_repair_generation — Chinese (language_id = 1), v1
-- ----------------------------------------------------------------------------
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_l8_collocation_repair_generation',
    1,
    1,
    $PROMPT$角色：你是汉语搭配专家，正在编写一道「搭配纠错」练习。

学习者看到的句子中，正确搭配词被替换成了一个错误的词，需要选出与目标词真正搭配的词来修复它。请生成四个选项和要植入的错误词。

键（返回的 JSON 只使用下列数字键，不得使用字段名称）：
0：四个选项组成的数组
1：要植入句中的错误搭配词
每个选项对象内部：
0：选项文字   1：是否为正确答案（true / false）   2：一句话解释

目标词：{target_word}
词条：{word}
词性：{pos}
语义类：{semantic_class}
释义（正在教授的唯一义项）：{definition}
义项指纹：{sense_fingerprint}
语域：{register}
难度层级：{complexity_tier}

句子（其中已含正确搭配词）：
{sentence_text}

正确搭配词（出现在上句中）：{primary_collocate}
该搭配的证据等级：{collocate_grounding}
  corpus_validated ＝ 已在频率语料中得到验证，视为固定搭配。
  llm_asserted     ＝ 无语料支撑的断言；若它其实并非该目标词的地道搭配，请使用下方的键 9 出口，而不要据此出题。
本词条其它题目已用过的干扰项，不得重复：{used_distractors_json}

规则：
1. 有且仅有一个选项正确：{primary_collocate}，即句中实际出现的搭配词。
2. 三个干扰项须是同词性的真实常用词，在语法上能填入该位置，但与目标词搭配不地道。要点在于「合语法而不合搭配」（如「做作业」对「造作业」）。绝不可选母语者也会接受的词 —— 例如「洗衣服」的位置上「洗涤」也可接受，故不可用；「冲刷」则明显不搭，可以使用。
3. 键 1 是要替换进句子的错误词。它须是干扰项级别、与目标词明显不搭的词，但**不得**出现在四个选项之中 —— 学习者需要自己提供修复词，而不是在列表里认出被植入的词。请选择错误最明显的那个。例如「沏茶」一题，选项为「沏 / 煮 / 做 / 打」时，植入「制造」：明显错误，且不在选项内。
4. 每个选项都要一句话解释：正确项为何地道，错误项为何不地道。
5. 若目标词在此处并无真正的固定搭配 —— 即 {primary_collocate} 只是自由组合而非搭配 —— 只返回 {"9": "no_collocation"}，不要输出其它内容。基于伪搭配出题等于教了一条不存在的规则。例如「看见房子」只是自由组合，不能据此出题；「取得成绩」是真搭配，可以出题。
6. 特别注意量词搭配、动宾固定搭配与体标（了 / 着 / 过）的凝固性。例如量词：「一___牛」应为「头」，而「张」「条」「只」均不搭。

仅返回 JSON，不要任何解说文字，不要 markdown 代码块：
{"0": [{"0": "沏", "1": true, "2": "「沏茶」为固定动宾搭配"}, {"0": "煮", "1": false, "2": "「煮茶」指长时间熬煮，与此处冲泡义不符"}, {"0": "做", "1": false, "2": "泛用动词，不与「茶」构成固定搭配"}, {"0": "打", "1": false, "2": "与「茶」无搭配关系"}], "1": "制造"}$PROMPT$,
    true,
    'qwen/qwen3.7-plus',
    'openrouter',
    'L8 搭配纠错 (Chinese), split out by TASK-520. Covers 量词/动宾/体标 collocation classes. Numeric-key output contract (TASK-537/538) bound to prompt_version 1.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
SET template_text = EXCLUDED.template_text,
    is_active     = EXCLUDED.is_active,
    model         = EXCLUDED.model,
    provider      = EXCLUDED.provider,
    description   = EXCLUDED.description;

COMMIT;


-- ----------------------------------------------------------------------------
-- 6. ladder_l8_collocation_repair_generation — Japanese (language_id = 3), v1
-- ----------------------------------------------------------------------------
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_l8_collocation_repair_generation',
    3,
    1,
    $PROMPT$役割：あなたは日本語のコロケーション（連語）の専門家で、連語修復問題を1問作成します。

学習者には、正しい共起語が誤った語に置き換えられた文が提示され、目標語と本当に結びつく語を選んで修復します。4つの選択肢と、埋め込む誤りの語を作ってください。

キー（返す JSON は名称ではなく下記の数字キーのみを使う）：
0：4つの選択肢の配列
1：文に埋め込む誤りの共起語
各選択肢オブジェクトの内部：
0：選択肢の文字列   1：正解かどうか（true / false）   2：一文の説明

目標語：{target_word}
語（辞書形）：{word}
品詞：{pos}
意味クラス：{semantic_class}
語義（教える対象の唯一の意味）：{definition}
語義フィンガープリント：{sense_fingerprint}
文体・待遇レベル：{register}
難易度ティア：{complexity_tier}

文（正しい共起語を既に含む）：
{sentence_text}

正しい共起語（上の文に出現）：{primary_collocate}
その共起語の根拠：{collocate_grounding}
  corpus_validated ＝ 頻度資料で裏づけ済み。固定的な連語として扱う。
  llm_asserted     ＝ 裏づけのない主張。目標語の慣用的な相手語で「ない」場合は、下のキー 9 の出口を使い、それを土台に出題しないこと。
この語の他の問題で既に使った誤答。再利用禁止：{used_distractors_json}

規則：
1. 正解はちょうど1つ：{primary_collocate}、すなわち文中に実際に現れている共起語。
2. 誤答3つは同じ品詞の実在する一般語で、文法的にはその位置に入るが、目標語との結びつきが慣用的でないもの。「文法的だが不自然」が狙い（「約束を守る」に対する「約束を持つ」など）。母語話者が許容しうる語は選ばないこと —— 例：「約束を交わす」は許容されるため誤答に使えない。「約束を作る」は不自然なので使える。
3. キー 1 は文に埋め込む誤りの語。目標語と明らかに結びつかない誤答相当の語であるが、4つの選択肢に**含めてはならない** —— 学習者は修復語を自分で選ぶのであり、埋め込まれた語を一覧から見つけるのではない。誤りが最も明白なものを選ぶ。例：「約束を守る」の問題で選択肢が「守る / 持つ / 作る / 置く」なら、「製造する」を埋め込む（明らかに誤りで、選択肢に無い）。
4. 各選択肢に一文の説明を付ける：正解がなぜ慣用的か、各誤答がなぜそうでないか。
5. ここで目標語に真の固定連語が存在しない場合 —— {primary_collocate} が連語ではなく自由結合にすぎない場合 —— {"9": "no_collocation"} だけを返すこと。偽の連語に基づく問題は存在しない規則を教えることになる。例：「家を見る」は自由結合なので出題できない。「風邪をひく」は真の連語なので出題できる。
6. 助詞の選択、複合動詞、サ変動詞＋「する」の結びつきに特に注意すること。例：「注意を払う」が正しく、「注意を支払う」は不自然。

JSON のみを返すこと。説明文も markdown コードフェンスも不可：
{"0": [{"0": "守る", "1": true, "2": "「約束を守る」が定着した連語"}, {"0": "持つ", "1": false, "2": "「約束を持つ」とは言わない"}, {"0": "作る", "1": false, "2": "約束を「する」であって「作る」ではない"}, {"0": "置く", "1": false, "2": "目標語との結びつきがない"}], "1": "製造する"}$PROMPT$,
    true,
    'qwen/qwen3.7-plus',
    'openrouter',
    'L8 collocation repair (Japanese), split out by TASK-520. Numeric-key output contract (TASK-537/538) bound to prompt_version 1 (schemas/ladder_l8_repair.py).'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
SET template_text = EXCLUDED.template_text,
    is_active     = EXCLUDED.is_active,
    model         = EXCLUDED.model,
    provider      = EXCLUDED.provider,
    description   = EXCLUDED.description;

COMMIT;


-- ----------------------------------------------------------------------------
-- 7. Record the narrowing on the surviving monolith rows
-- ----------------------------------------------------------------------------
-- The Python side already stops asking: TransformAssetGenerator sends
-- active_levels = ["7"], and the templates emit only the levels named there.
-- The prompt text itself still *describes* L4 and L8, which is now misleading
-- documentation rather than live behaviour, so record the split on the row.
-- The template bodies are intentionally left intact: rewriting three
-- multi-hundred-line prompts to delete two sections they no longer reach is
-- risk with no behavioural payoff, and the L4/L8 sections are exactly the
-- reference material anyone re-authoring the split prompts will want.
--
-- NOTE: this step was held back when the rest of the file was applied on
-- 2026-08-10; it goes live with the TASK-538 rewrite (TASK-540).
BEGIN;

UPDATE public.prompt_templates
SET description = COALESCE(description || ' ', '')
    || '[TASK-520] L4 and L8 no longer requested from this prompt — see '
    || 'ladder_l4_morphology_generation / ladder_l8_collocation_repair_generation. '
    || 'This row now serves L7 (spot-incorrect) only; its L4/L8 sections are unreachable.'
WHERE task_name = 'vocab_prompt3_transforms'
  AND is_active = true
  AND COALESCE(description, '') NOT LIKE '%[TASK-520]%';

COMMIT;


-- ----------------------------------------------------------------------------
-- Verification (run manually after applying)
-- ----------------------------------------------------------------------------
-- SELECT task_name, language_id, version, is_active, model, provider
-- FROM public.prompt_templates
-- WHERE task_name IN ('ladder_l4_morphology_generation',
--                     'ladder_l8_collocation_repair_generation',
--                     'vocab_prompt3_transforms')
-- ORDER BY task_name, language_id, version;
--
-- Expect: 3 rows per new task (language_id 1, 2, 3), all v1 / is_active,
-- and every active vocab_prompt3_transforms row carrying the [TASK-520] note.
--
-- The numeric contract is observable on the row itself — every template_text
-- must carry its key legend ("Keys (" / "键（" / "キー（") and must no longer
-- contain the string '"options"':
--
-- SELECT task_name, language_id,
--        template_text LIKE '%"options"%' AS still_named
-- FROM public.prompt_templates
-- WHERE task_name LIKE 'ladder_l%_generation' ORDER BY 1, 2;
-- -- expect still_named = false on all six
--
-- Reject-rate dashboard: the new prompt_versions appear automatically —
-- llm_calls rows are written with task_name = the split task names and
-- template_version = 1 (see _split_base.SplitLevelGenerator._call_with_retry).
