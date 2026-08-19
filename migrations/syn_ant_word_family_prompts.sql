-- ============================================================================
-- TASK-522 — synonym_antonym_match + word_family: generation prompts + judges.
-- Date: 2026-08-09
-- Revised: 2026-08-11 (TASK-537/538) — numeric-key output contract.
--
-- Two new exercise types, four new prompt task_names:
--   ladder_syn_ant_generation        (zh, en, ja)  -> L6 semantic_discrimination
--   ladder_word_family_generation    (en)          -> L4 form_production
--   ladder_relation_judge            (zh, en, ja)  -> syn/ant foil verdicts
--   ladder_word_family_judge         (en)          -> invented-derivation verdicts
--
-- Capability-matrix rows for both types already exist (TASK-504,
-- services/vocabulary_ladder/config.py::_CAPABILITY_SPEC and
-- migrations/dim_exercise_capabilities.sql) with judge_key 'relation' /
-- 'word_family'. This file only supplies the prompts they call.
--
-- This file writes these task_names only; it redefines no existing object, so
-- no older migration is superseded by it.
--
-- RE-RUNNABLE, AND CORRECTIVE (TASK-538)
-- --------------------------------------
-- Every row is ON CONFLICT ... DO UPDATE. The English rows went live on
-- 2026-08-10 on the old named-key contract, and DO NOTHING made a corrected
-- re-run a silent no-op — the file read as applied while the live prompt still
-- asked for English field names.
--
-- ----------------------------------------------------------------------------
-- BRACE CONVENTION — the two prompt families escape differently
-- ----------------------------------------------------------------------------
-- GENERATION prompts are rendered by asset_generators/_renderer.render_template,
-- which substitutes only {bare_identifier} tokens. JSON braces in the examples
-- must be written SINGLE.
--
-- JUDGE prompts are rendered by str.format (judges/relation.py). JSON braces in
-- those examples must be written DOUBLED, {{ }}.
--
-- Getting this backwards produces a KeyError at generation time, not a bad
-- exercise, so it fails loudly — but it is the one thing to check when adding
-- a row here. In this file rows 5-8 are judges.
--
-- ----------------------------------------------------------------------------
-- OUTPUT-SCHEMA CONTRACT
-- ----------------------------------------------------------------------------
-- Bound to prompt_version 1 and enforced before remap by
-- services/exercise_generation/schemas/ladder_typed.py. Re-authoring at v2
-- without adding 2 to PROMPT_VERSIONS is a hard failure, by design.
--
-- Keys are NUMERIC (TASK-537): 0 is always the option array, 9 is always the
-- error escape, and each prompt declares its legend in its own language. English
-- field names inside a ZH/JA prompt are English inside the generation context,
-- which is what this removes.
--
--   syn/ant generation:
--     {"0": [{"0": str, "1": bool, "2": str} x4], "1": "synonym"|"antonym"}
--       0 = options, 1 = relation.  Escape: {"9": "no_relation"}
--     The relation VALUE stays ASCII: code matches it against
--     ladder_typed.RELATIONS, so a localised "近义词" would fail the gate. Every
--     ZH/JA prompt says so explicitly, because a legend in Chinese or Japanese
--     otherwise invites a translated value.
--
--   word_family generation:
--     {"0": [{"0": str, "1": bool, "2": str, "3": str} x4], "1": str}
--       0 = options, 1 = stem; option key 3 = part_of_speech
--       Escape: {"9": "no_family"}
--
--   both judges (Likert v3, per memory distractor-judge-v3-likert):
--     {"<1-based candidate index>": {"0": 1-5, "1": "<short>"}}
--       within an entry: 0 = rating, 1 = reason
--     The TOP level stays keyed by 1-based candidate number — that is the
--     numbering the prompt itself handed the model, not a field name, so there
--     is no English in it to remove.
--     Mapped by schemas.likert_to_verdict — 5/4 accept, 3 flag, 2/1 reject.
--     The rating measures how clearly the candidate is a genuine NON-instance
--     (not a synonym / not a real word): 5 = ideal distractor, 1 = also-correct.
--     Both ladder judges share that polarity by construction: each calls
--     likert_to_verdict on the raw rating with no per-judge threshold.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- 1. ladder_syn_ant_generation — English (2), v1
-- ----------------------------------------------------------------------------
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_syn_ant_generation', 2, 1,
    $PROMPT$Role: Expert English lexicographer writing ONE relation-match exercise.

The learner is shown a word and asked which of four options stands in a stated relation to it. Produce those four options.

Keys (the JSON you return uses these numeric keys, never field names):
0: the array of four options
1: the relation — exactly the ASCII string "synonym" or "antonym"
Within each option object:
0: the option text   1: whether it is the correct answer (true / false)   2: the one-clause explanation

Target word: {word}
Part of speech: {pos}
Semantic class: {semantic_class}
Relation to test: {relation}
Definition — THE ONE SENSE BEING TAUGHT: {definition}
Sense fingerprint (disambiguating gloss / typical collocates): {sense_fingerprint}
Register: {register}
Complexity tier: {complexity_tier}
Example of the sense in use: {example_sentence}
Words already used as distractors elsewhere in this word's item set — do not reuse: {used_distractors_json}

Rules:
1. Exactly ONE option is a genuine {relation} OF THE SENSE ABOVE. Not of the spelling — of that sense. It must be a word an ordinary learner at this tier would plausibly meet.
2. The three distractors must each be a real English word of the same part of speech that is NOT a {relation} of that sense.
3. **The polysemy rule, which matters more than any other here.** A distractor must not be a {relation} of ANY OTHER sense of the target word. "bank" (financial institution) must not take "shore" as a distractor: it is a synonym of the riverbank sense, so a learner reading that sense answers it and is marked wrong.
4. Distractors should be semantically adjacent — same domain or register — not random. "precision" takes "vagueness", "haste", "clutter"; it does not take "bicycle".
5. Every option gets a one-clause explanation naming the relation it does or does not hold.
6. If the sense genuinely has no {relation} at this tier — many concrete nouns have no antonym, e.g. "table" or "window" — return exactly {"9": "no_relation"} and nothing else. Inventing one produces an item with no correct answer.

Return JSON ONLY, no prose and no markdown fences:
{"0": [{"0": "exactness", "1": true, "2": "same sense: freedom from error in measurement"}, {"0": "vagueness", "1": false, "2": "antonym, not synonym"}, {"0": "haste", "1": false, "2": "adjacent domain but unrelated meaning"}, {"0": "clutter", "1": false, "2": "unrelated; no sense of the target means this"}], "1": "synonym"}$PROMPT$,
    true, 'anthropic/claude-sonnet-5', 'openrouter',
    'syn/ant relation MCQ (English), TASK-522. Sense-anchored: the polysemy rule is the defect this prompt exists to avoid. Numeric-key contract (TASK-537/538), schema bound to prompt_version 1.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
SET template_text = EXCLUDED.template_text,
    is_active     = EXCLUDED.is_active,
    model         = EXCLUDED.model,
    provider      = EXCLUDED.provider,
    description   = EXCLUDED.description;

COMMIT;


-- ----------------------------------------------------------------------------
-- 2. ladder_syn_ant_generation — Chinese (1), v1
-- ----------------------------------------------------------------------------
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_syn_ant_generation', 1, 1,
    $PROMPT$角色：你是汉语词汇学专家，正在编写一道「词义关系」练习。

学习者看到一个目标词，须从四个选项中选出与之构成指定关系的那一个。请生成这四个选项。

键（返回的 JSON 只使用下列数字键，不得使用字段名称）：
0：四个选项组成的数组
1：关系类型 —— 必须原样填写 ASCII 字符串 "synonym" 或 "antonym"，供程序识别，切勿译成中文
每个选项对象内部：
0：选项文字   1：是否为正确答案（true / false）   2：一句话解释

目标词：{word}
词性：{pos}
语义类：{semantic_class}
待考关系：{relation}（synonym ＝ 近义词，antonym ＝ 反义词）
释义 —— 正在教授的唯一义项：{definition}
义项指纹（消歧释义 / 典型搭配）：{sense_fingerprint}
语域：{register}
难度层级：{complexity_tier}
该义项的用例：{example_sentence}
本词条其它题目已用过的干扰项，不得重复：{used_distractors_json}

规则：
1. 有且仅有一个选项与**上述义项**构成 {relation} 关系。是与该义项，而非与字形。该词应是此层级学习者可能接触到的常用词。
2. 三个干扰项须是同词性的真实汉语词，且与该义项不构成 {relation} 关系。
3. **多义规则，这是此处最重要的一条。** 干扰项不得与目标词的**任何其它义项**构成该关系。例如「行」取「银行」义时，不可用「走」作干扰项 —— 它是「行走」义的近义词，读该义项的学习者会选它并被判错。
4. 干扰项应语义邻近 —— 同一语域或语义场 —— 而非随机。「精确」可配「模糊」「仓促」「杂乱」，不可配「自行车」。
5. 每个选项都要一句话解释其成立或不成立的关系理由。
6. 若该义项在此层级确实没有 {relation}（许多具体名词没有反义词，例如「桌子」「窗户」），只返回 {"9": "no_relation"}，不要输出其它内容。自造关系会产生没有正确答案的题目。

仅返回 JSON，不要任何解说文字，不要 markdown 代码块：
{"0": [{"0": "精准", "1": true, "2": "同义项：测量上无误差"}, {"0": "模糊", "1": false, "2": "反义而非近义"}, {"0": "仓促", "1": false, "2": "语义场邻近但义不同"}, {"0": "杂乱", "1": false, "2": "无关；目标词任何义项均不表此义"}], "1": "synonym"}$PROMPT$,
    true, 'qwen/qwen3.7-plus', 'openrouter',
    'syn/ant relation MCQ (Chinese), TASK-522. Sense-anchored with the 多义 rule. Numeric-key contract (TASK-537/538), schema bound to prompt_version 1.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
SET template_text = EXCLUDED.template_text,
    is_active     = EXCLUDED.is_active,
    model         = EXCLUDED.model,
    provider      = EXCLUDED.provider,
    description   = EXCLUDED.description;

COMMIT;


-- ----------------------------------------------------------------------------
-- 3. ladder_syn_ant_generation — Japanese (3), v1
-- ----------------------------------------------------------------------------
-- Rule 3 previously stated the polysemy constraint abstractly here — EN names
-- bank/shore, ZH names 行(银行)/走, JA named nothing — which left the single
-- most important rule in the prompt as the only one without a worked example.
-- It now names 甘い: teaching the taste sense, 厳しい is the antonym of the
-- *lenient* sense, so a learner reading that sense picks it and is marked
-- wrong. That is the exact shape of the bank/shore failure in Japanese.
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_syn_ant_generation', 3, 1,
    $PROMPT$役割：あなたは日本語語彙論の専門家で、語義関係の問題を1問作成します。

学習者は目標語を見て、4つの選択肢から指定された関係にある語を選びます。その4つを作ってください。

キー（返す JSON は名称ではなく下記の数字キーのみを使う）：
0：4つの選択肢の配列
1：関係の種類 —— ASCII の "synonym" または "antonym" をそのまま入れる（プログラムが照合するため、日本語に訳さないこと）
各選択肢オブジェクトの内部：
0：選択肢の文字列   1：正解かどうか（true / false）   2：一文の説明

目標語：{word}
品詞：{pos}
意味クラス：{semantic_class}
問う関係：{relation}（synonym ＝ 類義語、antonym ＝ 対義語）
語義 —— 教える対象の唯一の意味：{definition}
語義フィンガープリント：{sense_fingerprint}
文体・待遇レベル：{register}
難易度ティア：{complexity_tier}
その語義の用例：{example_sentence}
この語の他の問題で既に使った誤答。再利用禁止：{used_distractors_json}

規則：
1. 正解はちょうど1つ。**上記の語義**と {relation} の関係にある語であること。表記ではなく語義との関係。このティアの学習者が出会いうる語であること。
2. 誤答3つは同じ品詞の実在する日本語の語で、その語義とは {relation} の関係にないもの。
3. **多義の規則。ここで最も重要。** 誤答は目標語の**他のどの語義**とも当該関係にあってはならない。例：「甘い」の「味が甘い」という語義を教えるとき、「厳しい」を誤答にしてはならない —— それは「採点が甘い」という別語義の対義語であり、その語義で読んだ学習者が選んで不正解にされる。同音異義語・多義語では特に注意すること。
4. 誤答は意味的に隣接していること（同じ分野・語域）。無関係な語ではなく、迷える語を選ぶ。例：「正確」なら「曖昧」「性急」「雑然」は誤答に使えるが、「自転車」は無関係すぎて使えない。
5. 各選択肢に、関係が成立する／しない理由を一文で付ける。
6. その語義にこのティアで {relation} が存在しない場合（具体名詞には対義語がないものが多い。例：「机」「窓」）は {"9": "no_relation"} だけを返すこと。関係を捏造すると正解のない問題になる。

JSON のみを返すこと。説明文も markdown コードフェンスも不可：
{"0": [{"0": "正確", "1": true, "2": "同一語義：誤差がないこと"}, {"0": "曖昧", "1": false, "2": "対義であり類義ではない"}, {"0": "性急", "1": false, "2": "分野は近いが意味が異なる"}, {"0": "雑然", "1": false, "2": "無関係；目標語のどの語義もこれを表さない"}], "1": "synonym"}$PROMPT$,
    true, 'qwen/qwen3.7-plus', 'openrouter',
    'syn/ant relation MCQ (Japanese), TASK-522. Sense-anchored; the polysemy rule now carries a worked 甘い example (TASK-538). Numeric-key contract, schema bound to prompt_version 1.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
SET template_text = EXCLUDED.template_text,
    is_active     = EXCLUDED.is_active,
    model         = EXCLUDED.model,
    provider      = EXCLUDED.provider,
    description   = EXCLUDED.description;

COMMIT;


-- ----------------------------------------------------------------------------
-- 4. ladder_word_family_generation — English (2), v1
-- ----------------------------------------------------------------------------
-- English only. The exercise presupposes productive derivational morphology,
-- which the analytic languages in this corpus do not have; the capability
-- matrix carries a word_family row for language 2 alone.
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_word_family_generation', 2, 1,
    $PROMPT$Role: Expert English morphologist writing ONE word-family exercise.

The learner sees a sentence with a slot, and must pick the correctly DERIVED form of a stem for that slot — a different skill from inflection: "decide" -> "Her ___ was final" -> **decision**.

Keys (the JSON you return uses these numeric keys, never field names):
0: the array of four options
1: the derivational stem
Within each option object:
0: the option text   1: whether it is the correct answer (true / false)   2: the one-clause explanation   3: the part of speech the form would be

Stem word: {word}
Part of speech of the stem: {pos}
Semantic class: {semantic_class}
Definition (the ONE sense being taught): {definition}
Sense fingerprint: {sense_fingerprint}
Register: {register}
Complexity tier: {complexity_tier}

The sentence (the slot is where the target currently sits):
{sentence_text}
The form currently in the slot: {target_word}
Attested forms of this lemma: {morphological_forms_json}
Forms already used as distractors elsewhere in this word's item set — do not reuse: {used_distractors_json}

Rules:
1. Key 1 is the derivational base — the shortest real word the family is built from ("decide", not "decision").
2. Exactly ONE option is correct: the real derived form that fits the slot's grammatical role. Give its part of speech in key 3.
3. **The three distractors must be INVENTED derivations: morphologically well-formed but NOT real English words** ("decidement", "decisionment", "decidal"). That is the skill — a learner who has half-learnt the family recognises the shape without knowing the word.
4. **Never offer a real word as a distractor.** If "decisive" exists, it must not appear. This is the one hard failure mode: a real word among the distractors gives the item two defensible answers. When unsure whether a form is a real word, do not use it.
5. Each invented distractor must use a real English suffix attached in a plausible position — random letter strings teach nothing. "decidement" is usable (real suffix -ment, wrongly attached); "decidzorp" is not.
6. Every option gets a one-clause explanation (key 2) and a part of speech (key 3) naming what the form would be.
7. If the stem has no productive derived form beyond simple inflection — function words such as "the", or stems whose family is inflection only, such as "sheep" — return exactly {"9": "no_family"} and nothing else.

Return JSON ONLY, no prose and no markdown fences:
{"0": [{"0": "decision", "1": true, "2": "the established nominalisation", "3": "noun"}, {"0": "decidement", "1": false, "2": "-ment does not attach to this stem", "3": "noun"}, {"0": "decisionment", "1": false, "2": "double suffixation; not a word", "3": "noun"}, {"0": "decidal", "1": false, "2": "-al is adjectival and not used here", "3": "adjective"}], "1": "decide"}$PROMPT$,
    true, 'anthropic/claude-sonnet-5', 'openrouter',
    'word_family derived-form slot (English), TASK-522. Distractors are invented derivations; the hard rule is that no real word may appear among them. Numeric-key contract (TASK-537/538), schema bound to prompt_version 1.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
SET template_text = EXCLUDED.template_text,
    is_active     = EXCLUDED.is_active,
    model         = EXCLUDED.model,
    provider      = EXCLUDED.provider,
    description   = EXCLUDED.description;

COMMIT;


-- ----------------------------------------------------------------------------
-- 5. ladder_relation_judge — English (2), v1     [str.format — DOUBLED braces]
-- ----------------------------------------------------------------------------
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_relation_judge', 2, 1,
    $PROMPT$You are a strict judge for an English relation-match exercise. The learner must pick the one option that is a {relation} of the target word IN ONE SPECIFIC SENSE. The three others must be genuine non-{relation}s. Rule on each candidate.

Keys (inside each entry the JSON you return uses these numeric keys, never field names):
the top level is keyed by the 1-based candidate number
within each entry — 0: the rating, 1-5   1: the reason, 12 words or fewer

Target word: {target}
The ONE sense being taught: {definition}
Relation being tested: {relation}
The intended correct answer: {correct_answer}
Candidate distractors:
{candidates_numbered}

For EACH candidate, rate 1-5 how clearly it is a genuine NON-{relation} of the target — i.e. how safely it can serve as a wrong answer:
5 = clearly not a {relation} of ANY sense of the target; an ideal wrong answer.
4 = probably not a {relation}; a fluent speaker would not pair them.
3 = borderline; could be argued either way.
2 = probably a {relation} of some sense of the target (likely an also-correct answer).
1 = a full {relation} of the target — of the taught sense OR of another sense of the same word. It must NOT be used as a wrong answer.

**Check every sense of the target word, not only the one being taught.** This is the failure that matters: "shore" is not a synonym of "bank" (financial institution), but it IS a synonym of "bank" (riverbank), so a learner reading that sense picks it and is marked wrong. Any candidate that is a {relation} of any sense rates 1.

When unsure, rate LOW. Dropping a borderline distractor costs one option; shipping an also-correct one costs the item.

Return JSON ONLY, keyed by the 1-based candidate index. Each value is an object that uses these numeric keys, never field names:
0: the rating, 1-5
1: the reason, 12 words or fewer

{{"1": {{"0": 5, "1": "unrelated to every sense of the target"}}, "2": {{"0": 1, "1": "synonym of the riverbank sense"}}}}

Rate EVERY candidate. No prose outside the JSON. No markdown fences.$PROMPT$,
    true, 'google/gemini-2.5-flash-lite', 'openrouter',
    'Relation judge (English), TASK-522: rules whether a syn/ant foil is a genuine non-instance across ALL senses of the target, catching the polysemy also-correct failure. Likert v3, numeric entry keys (TASK-537/538).'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
SET template_text = EXCLUDED.template_text,
    is_active     = EXCLUDED.is_active,
    model         = EXCLUDED.model,
    provider      = EXCLUDED.provider,
    description   = EXCLUDED.description;

COMMIT;


-- ----------------------------------------------------------------------------
-- 6. ladder_relation_judge — Chinese (1), v1
-- ----------------------------------------------------------------------------
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_relation_judge', 1, 1,
    $PROMPT$你是一道汉语「词义关系」练习的严格评审。学习者须选出与目标词在**某一特定义项**上构成 {relation} 关系的唯一选项，其余三项必须确实不构成该关系。请逐项评判候选干扰项。

键（返回的 JSON 在每个条目内部只使用数字键，不得使用字段名称）：
顶层以 1 起始的候选序号为键
每个条目内部 —— 0：评分，1-5   1：理由，不超过 12 字

目标词：{target}
正在教授的唯一义项：{definition}
待考关系：{relation}（synonym ＝ 近义，antonym ＝ 反义）
既定正确答案：{correct_answer}
候选干扰项：
{candidates_numbered}

对每个候选词，评估它作为该目标词的「非 {relation}」有多明确 —— 即作为错误选项有多安全 —— 用 1-5 分：
5 ＝ 与目标词的**任何**义项都不构成该关系；理想错误选项。
4 ＝ 很可能不构成；母语者不会将二者配对。
3 ＝ 临界；两可。
2 ＝ 很可能与目标词的某一义项构成该关系（很可能是另一个正确答案）。
1 ＝ 与目标词构成完整的该关系 —— 无论是所教义项还是**其它义项**。绝不可作错误选项。

**必须逐一检查目标词的所有义项，而不仅是所教的那一个。** 这正是关键失误：「走」不是「行（银行）」的近义词，但它是「行（行走）」的近义词；读后一义项的学习者会选它并被判错。任何与任一义项构成该关系的候选词，一律评 1 分。

不确定时评低分。舍弃一个临界干扰项只损失一个选项，放过一个实为正确的选项则毁掉整道题。

仅返回 JSON，以 1 起始的候选序号为键。每个值都是一个对象，只使用下列数字键，不得使用字段名称：
0：评分，1-5
1：理由，不超过 12 字

{{"1": {{"0": 5, "1": "与任何义项均无关"}}, "2": {{"0": 1, "1": "「行走」义的近义词"}}}}

每项都要评分。JSON 之外不要输出任何文字，不要使用 markdown 代码块。$PROMPT$,
    true, 'qwen/qwen3.7-plus', 'openrouter',
    'Relation judge (Chinese), TASK-522: checks every 义项 of the target, catching the 多义 also-correct failure. Likert v3, numeric entry keys (TASK-537/538).'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
SET template_text = EXCLUDED.template_text,
    is_active     = EXCLUDED.is_active,
    model         = EXCLUDED.model,
    provider      = EXCLUDED.provider,
    description   = EXCLUDED.description;

COMMIT;


-- ----------------------------------------------------------------------------
-- 7. ladder_relation_judge — Japanese (3), v1
-- ----------------------------------------------------------------------------
-- The polysemy paragraph carried no worked example here either; it now names
-- the same 甘い pair as the JA generation prompt, so judge and generator are
-- reasoning about one concrete case rather than two abstractions.
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_relation_judge', 3, 1,
    $PROMPT$あなたは日本語の語義関係問題の厳格な評価者です。学習者は、**ある特定の語義**において目標語と {relation} の関係にある唯一の選択肢を選びます。他の3つは確実にその関係にないものでなければなりません。各候補を判定してください。

キー（返す JSON は各項目の内部では名称ではなく下記の数字キーを使う）：
最上位は 1 起点の候補番号をキーとする
各項目の内部 —— 0：評価、1-5   1：理由、12 語以内

目標語：{target}
教える対象の唯一の語義：{definition}
問う関係：{relation}（synonym ＝ 類義、antonym ＝ 対義）
想定される正解：{correct_answer}
候補の誤答：
{candidates_numbered}

各候補について、目標語の「非 {relation}」であることがどれほど明確か —— 誤答としてどれほど安全か —— を 1-5 で評価：
5 ＝ 目標語の**いかなる語義**とも当該関係にない。理想的な誤答。
4 ＝ おそらく関係にない。母語話者は結びつけない。
3 ＝ 境界的。どちらとも言える。
2 ＝ 目標語のある語義とは当該関係にある可能性が高い（実質もう一つの正解）。
1 ＝ 目標語と完全に当該関係にある —— 教える語義でも、**別の語義**でも。誤答に使ってはならない。

**教える語義だけでなく、目標語のすべての語義を確認すること。** これが決定的な失敗です。例：「甘い」の「味が甘い」語義を教える問題で、「厳しい」は味の語義の対義語ではないが、「採点が甘い」語義の対義語である。したがってその語義で読んだ学習者が選んで不正解にされるため、評価は 1 とする。いずれかの語義と当該関係にある候補はすべて 1 とすること。

判断に迷う場合は低く評価すること。境界的な誤答を落とせば選択肢が1つ減るだけですが、実は正解である選択肢を通せば問題そのものが壊れます。

JSON のみを返すこと。1 起点の候補番号をキーとし、各値は下記の数字キーのみを使うオブジェクト（名称は使わない）：
0：評価、1-5
1：理由、12 語以内

{{"1": {{"0": 5, "1": "どの語義とも無関係"}}, "2": {{"0": 1, "1": "別語義の対義語"}}}}

すべての候補を評価すること。JSON 以外の文章も markdown コードフェンスも不可。$PROMPT$,
    true, 'qwen/qwen3.7-plus', 'openrouter',
    'Relation judge (Japanese), TASK-522: checks every sense of the target for the polysemy also-correct failure, now with a worked 甘い example (TASK-538). Likert v3, numeric entry keys.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
SET template_text = EXCLUDED.template_text,
    is_active     = EXCLUDED.is_active,
    model         = EXCLUDED.model,
    provider      = EXCLUDED.provider,
    description   = EXCLUDED.description;

COMMIT;


-- ----------------------------------------------------------------------------
-- 8. ladder_word_family_judge — English (2), v1
-- ----------------------------------------------------------------------------
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_word_family_judge', 2, 1,
    $PROMPT$You are a strict lexical judge for an English word-family exercise. The distractors in that exercise are deliberately INVENTED derivations — morphologically plausible strings that are NOT real English words. Your job is to catch any that are, in fact, real.

Keys (inside each entry the JSON you return uses these numeric keys, never field names):
the top level is keyed by the 1-based candidate number
within each entry — 0: the rating, 1-5   1: the reason, 12 words or fewer

Derivational stem: {stem}
The intended correct answer (a real word — do not judge this one): {correct_answer}
Candidate distractors:
{candidates_numbered}

For EACH candidate, rate 1-5 how confidently it is NOT a real, current English word:
5 = certainly not a word; no dictionary would list it, and no fluent speaker would accept it.
4 = almost certainly not a word; possibly a rare nonce formation, but not established.
3 = uncertain; it may be a technical, dialectal, or archaic word you are not sure about.
2 = probably a real word, though uncommon or specialised.
1 = definitely a real, current English word — it must NOT be used as an invented distractor.

Judge word-hood, not well-formedness. "decisionment" is well-formed and still not a word (rate 5). "decisive" is a word (rate 1) even though it is an obvious member of the family. Count technical, archaic and chiefly-British words as real words.

When unsure, rate LOW (1-3). A real word smuggled in as an "invented" distractor gives the item two defensible answers, which is a worse outcome than losing a distractor.

Return JSON ONLY, keyed by the 1-based candidate index. Each value is an object that uses these numeric keys, never field names:
0: the rating, 1-5
1: the reason, 12 words or fewer

{{"1": {{"0": 5, "1": "-ment does not attach to this stem; not a word"}}, "2": {{"0": 1, "1": "'decisive' is a standard adjective"}}}}

Rate EVERY candidate. No prose outside the JSON. No markdown fences.$PROMPT$,
    true, 'google/gemini-2.5-flash-lite', 'openrouter',
    'Word-family judge (English), TASK-522: rules whether each "invented" derivation is genuinely not a word, catching a real word smuggled in as a distractor. Likert v3, numeric entry keys (TASK-537/538).'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
SET template_text = EXCLUDED.template_text,
    is_active     = EXCLUDED.is_active,
    model         = EXCLUDED.model,
    provider      = EXCLUDED.provider,
    description   = EXCLUDED.description;

COMMIT;


-- ----------------------------------------------------------------------------
-- Verification (run manually after applying)
-- ----------------------------------------------------------------------------
-- SELECT task_name, language_id, version, is_active, model
-- FROM public.prompt_templates
-- WHERE task_name IN ('ladder_syn_ant_generation', 'ladder_word_family_generation',
--                     'ladder_relation_judge', 'ladder_word_family_judge')
-- ORDER BY task_name, language_id;
--
-- Expect 8 rows: syn_ant x3, word_family_generation x1, relation_judge x3,
-- word_family_judge x1.
--
-- The numeric contract is observable on the row: no template_text may still
-- contain '"rating"' or '"is_correct"'.
--
-- SELECT task_name, language_id,
--        (template_text LIKE '%"rating"%' OR template_text LIKE '%"is_correct"%')
--            AS still_named
-- FROM public.prompt_templates
-- WHERE task_name IN ('ladder_syn_ant_generation', 'ladder_word_family_generation',
--                     'ladder_relation_judge', 'ladder_word_family_judge')
-- ORDER BY 1, 2;
-- -- expect still_named = false on all eight
--
-- Reject rates appear on the dashboard automatically — the judges write
-- llm_calls rows with task_name 'judge_ladder_relation' /
-- 'judge_ladder_word_family' (see judges/relation.py).
