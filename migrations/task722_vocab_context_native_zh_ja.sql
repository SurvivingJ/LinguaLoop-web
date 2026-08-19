-- question_vocabulary_context: native zh/ja rewrite (TASK-722).
--
-- WHY: the zh and ja rows were literal translations of the English one that kept
-- the ENGLISH lexical targets. Both taught with 'bright', 'pick up' and
-- 'turn a blind eye', and embedded those English idioms INSIDE their CJK
-- few-shot passages -- zh: "共同'pick up the pieces'", ja:
-- "事態を収拾し（pick up the pieces）". A Chinese vocabulary-question generator
-- was therefore being few-shotted on English phrasal verbs, a category Chinese
-- does not have, and 成语/惯用语 (zh) and 慣用句/四字熟語 (ja) were never mentioned
-- at all. Same defect class as the ladder-numeric-keys batch one layer up: that
-- one removed English FIELD NAMES from ZH/JA prompts, this removes English
-- CONTENT.
--
-- Measured leak, counting Latin-script tokens of 2+ chars and excluding the JSON
-- keys / type code / placeholder names that must stay Latin
-- (scripts/rewrite_vocab_context_prompt.py applies the identical metric):
--
--     row                          before -> after
--     zh question_vocabulary_context   21 -> 0
--     ja question_vocabulary_context   24 -> 0
--
-- For scale, counting ONLY real leaks (each row's own type code is machinery and
-- is excluded), every other active row is at 0 except zh question_inference (2:
-- 'Martinez' twice, an English proper name inside a Chinese few-shot passage),
-- ja question_main_idea (2: 'vs') and ja question_author_purpose (6: 'Author',
-- 'Purpose', 'Tone', 'vs' x3 -- English section headings and metalanguage, a
-- milder defect than English lexical TARGETS). vocabulary_context was the
-- outlier by an order of magnitude, exactly as the source analysis claimed.
--
-- HOW: not translated. Each row was authored from scratch in the target language
-- by qwen/qwen3.8-max against a target-language brief, then verified mechanically
-- before landing here -- placeholders present exactly once, JSON braces doubled,
-- str.format() actually executed, and zero non-machinery Latin runs. Both passed
-- on the first attempt. The advanced-level rule is restated in each language's
-- own terms: "multi-word expression" is an English-shaped constraint (English
-- distinguishes idioms by word count), so zh now tests 熟语性/整体性/典故性 and ja
-- tests whether the meaning is 凝固した rather than compositional.
--
-- ALSO FIXED, and not in the original brief: neither incumbent said anything
-- about where the correct answer sits, and question_generator.py does NOT
-- shuffle choices -- whatever order the model emits is the order the learner
-- sees. Both new rows carry an explicit "do not always put the answer first"
-- rule, and their worked examples place the answer in varying positions
-- (zh: 3rd, 4th, 2nd; ja: 3rd, 4th, 2nd) instead of the incumbent's uniform
-- first/second.
--
-- SCOPED TO zh AND ja. The en row is untouched and stays active -- it is not
-- defective, it is the source the other two were mistranslated from.
--
-- TASK-721 will add a distractor-construction block to all 18 question_* rows;
-- these two will take it as v3. Keeping the interventions in separate versions
-- is deliberate, so the reject-rate movement can be attributed to one or the
-- other.
--
-- Reversible: UPDATE prompt_templates SET is_active = (version = 1) WHERE
-- task_name = 'question_vocabulary_context' AND language_id IN (1, 3);

BEGIN;

-- Retire v1 for zh and ja ONLY. en (language_id=2) must stay active.
UPDATE prompt_templates
   SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'question_vocabulary_context'
   AND language_id IN (1, 3)
   AND is_active;

-- zh (language_id=1)
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
VALUES (
    'question_vocabulary_context', 1, 2, TRUE,
    'qwen/qwen3.7-plus', 'openrouter',
    '你是一位中文母语语言测评专家。请根据提供的短文，从零生成一道四选一的“语境中的词汇”阅读理解题。题目必须完全基于短文语境，考查读者对文中某个汉语词汇单位在特定上下文里含义的理解。

输入：
短文：{prose}
难度：{difficulty}
已出现题目：{previous_questions}

一、总体命题原则
1. 目标词或固定表达必须出自短文，且在该短文中语义清楚、自然成立。
2. 题目应考查“在这个语境里为什么是这个意思”，而不是孤立背诵词典义。
3. 全文必须使用地道现代汉语，不得出现外文字母、拼音、外语词或翻译腔。
4. 正确项必须唯一，且能由短文信息支持。
5. 正确答案在四个选项中的位置必须自然分布，不得固定在第一个，也不得形成可预测的位置规律。
6. 不要套用外语短语动词、词数分级或外来习语分类框架；中文级别应依据汉语自身的多义词、惯用语、离合词、成语、谚语、歇后语和书面固定表达来判断。

二、难度等级与中文词汇范畴
难度为一至四时，考查常见多义词或常用词在具体语境中的义项选择。目标可以是单音节或双音节常用词，例如“打”“意思”“东西”“头”“开”“走”等。重点在于同一个词在不同语境中会产生不同义项，读者需要根据上下文判断。

难度为五至六时，考查常见惯用语、固定搭配、离合词或比喻义明显的双音节词。目标应具有一定口语性或熟语性，例如“碰钉子”“打退堂鼓”“收拾”“张罗”“磨合”“拿捏”等。重点在于读者能否识别其超出字面的常用语用意义。

难度为七至九时，必须考查成语、谚语、歇后语或书面语固定表达，而不是一个可以逐字理解的普通词语。判断标准不是字数多少，而是该单位是否具有汉语自身的熟语性、整体性、典故性、劝诫性或固定修辞色彩。若一个表达的意义基本可以由各个字面直接拼合，且没有明显的固定比喻、典故、书面色彩或语用限制，则不属于七至九级考查对象。

三、目标词选择要求
1. 优先选择在短文中承担关键语义、情绪转折或人物态度变化的词语。
2. 不要选择专有名词、人名、地名、机构名，除非其已经产生明确比喻义且符合难度要求。
3. 不要选择过于生僻、古奥、方言过强或普通读者难以理解的词语，除非短文本身提供充分线索。
4. 不要选择纯粹由语法关系造成的临时组合。
5. 七至九级尤其要避免把普通动词、普通形容词或常见双音节词当作高级目标。
6. 如果短文中没有完全符合该难度的目标，可选取最接近该难度且语境支持的表达，但不得凭空添加短文没有的词语。

四、题干设计
题干应简洁明确，通常可问：
1. 文中某个词或表达最接近的意思是什么。
2. 文中某个词或表达最恰当的理解是什么。
3. 某个词在文中所指的情况或态度是什么。
题干必须标明“文中”或“在上述短文中”，避免读者脱离语境作答。

五、选项设计
1. 四个选项均须为中文，长度、句式和表达风格应尽量接近。
2. 正确选项必须准确概括目标词在短文中的语境义。
3. 三个干扰项必须都是该词或表达在汉语中似是而非的解释，可以来自常见义项、字面义、近义但程度不同、对象不同、感情色彩不同、搭配范围不同等。
4. 干扰项不得明显荒谬，不得与正确项意思相同，不得使用“以上皆是”“以上皆非”一类表述。
5. 选项不要引入短文未提供的新事实，也不要变成对短文主旨的概括。
6. 若目标是成语或固定表达，选项应解释其整体意义，不要逐字拆解成不成句的词语堆砌。

六、重复回避
若已出现题目非空，须避免与已出现题目重复。不得重复同一目标词、同一题干句式、同一组选项思路或同一解释角度。若已出现题目为空，则无需比较。

七、示例
以下两个示例仅示范题目方向与选项质量，不得机械照抄。

示例一 中级
例文：他满怀信心地去找负责人谈方案，结果碰了一鼻子灰，回到办公室半天没说话。
问题：文中“碰了一鼻子灰”最接近的意思是什么？
选项：
一 因天气寒冷而感冒不适
二 因为说话直率而得罪别人
三 遭到拒绝或冷遇，事情不顺利
四 在拥挤场所不小心撞到东西
正确答案：第三项
解释：短文写他带着信心去谈方案，回来后情绪低落，说明方案没有被接受或遭到冷淡回应。因此这里应理解为遭到拒绝或冷遇，而不是字面上的身体不适或碰撞。

示例二 高级
例文：这次事故起初只是一个小疏漏，若能及时上报并补救，损失不至于扩大。可惜几位主管互相推诿，拖延了两天，最终酿成大祸，可以说是养痈遗患。
问题：文中“养痈遗患”最恰当的理解是什么？
选项：
一 在困难中互相扶持，共同渡过难关
二 为了眼前利益而损害长远利益
三 对问题处理不当，反而使矛盾更加尖锐
四 纵容隐患，留下后患
正确答案：第四项
解释：短文强调小疏漏没有及时处理，拖延之后酿成大祸。这里应理解为纵容隐患、留下后患。其他选项虽然也涉及困难、利益或矛盾，但不符合该成语在文中的核心含义。

八、输出要求
最终只输出一个对象，不要输出标题、说明、编号、分析过程、代码框或任何额外文字。对象格式如下：
{{
  "question_text": "文中‘打退堂鼓’最接近的意思是什么？",
  "question_type": "vocabulary_context",
  "choices": ["用鼓声激励大家继续", "中途放弃或退缩", "临时改变原定计划", "把事情推给别人"],
  "answer": "中途放弃或退缩",
  "explanation": "语境写遇到困难后不再坚持，因此这里应理解为中途放弃或退缩。"
}}',
    'v2 (TASK-722): authored natively in Chinese, not translated. Targets 多义词 / 惯用语 / 离合词 / 成语 / 谚语 / 歇后语; no English lexical targets or few-shot content. Adds an explicit answer-position rule (choices are never shuffled downstream).'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

-- ja (language_id=3)
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
VALUES (
    'question_vocabulary_context', 3, 2, TRUE,
    'qwen/qwen3.7-plus', 'openrouter',
    'あなたは日本語母語の言語評価の専門家として、日本語の読解問題を作成してください。以下の資料と難易度に基づき、「文脈における語彙」を問う四択問題を 1 問だけ作ってください。

資料：
{prose}

難易度：
{difficulty}

既出問題：
{previous_questions}
既出問題で問われた語彙・表現・文脈と重複しないようにしてください。

【問題作成の方針】
・問う対象は、日本語の語彙単位に限定すること。外国語の語句、ローマ字、アルファベット表記を問題文・選択肢・解説に含めないこと。
・日本語には句動詞という範疇がないため、動詞と補助成分の組み合わせは、複合動詞や慣用表現として扱うこと。
・資料の内容を踏まえ、自然な現代日本語の一文を問題文にすること。問う語句には（ ）を付けて示すこと。
・問題文、選択肢、解説は、資料に現れない語彙を補いすぎず、資料の文脈から自然に導かれる範囲に収めること。
・選択肢は四つとし、どれも文脈に照らして紛らわしい別解釈になるようにすること。明らかに不合理な選択肢は作らないこと。
・選択肢は、品詞や文末の形をそろえ、長さの差で正解が推測されないようにすること。
・正解は 1 から 4 までのどこに置いてもよいが、特定の位置に偏らせないこと。常に 1 番目を正解にしないこと。
・解説では、なぜその意味になるのか、文脈の手掛かりと語彙の性質を簡潔に示すこと。
・語彙の意味は、辞書的な第一義だけに固定せず、資料中の用法を優先すること。
・問題文と選択肢に、資料の主題と無関係な情報を持ち込まないこと。

【難易度別の要件】
・難易度 1 から 4：多義語や基本語が文脈によってどの意味になるかを問うこと。例として「かける」「あたる」「手」のように、一つの語が複数の意味を持つ場合を扱う。
・難易度 5 から 6：慣用句、複合動詞、オノマトペ、比喩的に使われる和語を問うこと。字義どおりとは異なる意味が文脈で決まる表現を選ぶ。
・難易度 7 から 9：四字熟語、ことわざ、故事成語、慣用表現を問うこと。この難易度では、単独の基本語を問わないこと。字義どおりに解釈できる普通の語ではなく、意味が凝固した四字熟語・ことわざ・慣用句であること。

【例題 1（中級相当）】
例文：その店は評判を落としたが、最近ようやく持ち直してきた。
質問：文中の「持ち直してきた」はこの文ではどのような意味か。
選択肢：
1 再び持ち上げられてきた
2 以前の状態を維持してきた
3 悪い状態から回復してきた
4 誰かに支えられてきた
正解：3
解説：「持ち直す」は、悪い状態から良い状態へ回復する意味の複合動詞である。この文では、店の評判や業績が回復してきた意味なので、3 が適切。1 と 4 は「持つ」「直す」を字義どおりに取り過ぎている。2 は維持の意味で、回復のニュアンスが足りない。

【例題 2（上級相当）】
例文：突然の質問に答えられず、彼は右往左往するばかりだった。
質問：文中の「右往左往」はこの文ではどのような意味か。
選択肢：
1 右へ行ったり左へ行ったりする
2 進む方向が定まらない
3 周囲に気を配って忙しい
4 あわてふためいて混乱する
正解：4
解説：「右往左往」は、実際の移動方向ではなく、動揺して混乱し、どうしてよいか分からない様子を表す四字熟語である。この文では、突然の質問に対応できずに混乱している意味なので、4 が適切。1 や 2 は字義どおりの移動解釈で、3 は文脈から導かれる類推に過ぎない。

【出力形式】
出力は、次のオブジェクトのみとすること。オブジェクトの外に説明文や余分な記号を付けないこと。以下は形式を示す例であり、実際の値は問題に合わせて置き換えること。正解の値は、選択肢のいずれかと完全に一致させること。

{{
  "question_text": "例：文中の（表現）の意味として最も適切なものを選んでください。",
  "question_type": "vocabulary_context",
  "choices": ["例：字義どおりの解釈", "例：文脈に合う解釈", "例：別の慣用的な解釈", "例：関連するが的外れな解釈"],
  "answer": "例：文脈に合う解釈",
  "explanation": "例：この文では、対象語が比喩的に使われているため、この意味が適切である。"
}}',
    'v2 (TASK-722): authored natively in Japanese, not translated. Targets 多義語 / 慣用句 / 複合動詞 / オノマトペ / 四字熟語 / ことわざ; no English lexical targets or few-shot content. Adds an explicit answer-position rule (choices are never shuffled downstream).'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

COMMIT;
