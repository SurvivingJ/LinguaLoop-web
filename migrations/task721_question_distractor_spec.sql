-- TASK-721: give the 18 question_* generator prompts a distractor
-- specification. STAGED INACTIVE -- see scripts/apply_task721_rows.py.
--
-- Each new body is the incumbent verbatim plus one spliced block, so the
-- diff is attributable to exactly one change. Version numbers are per-row
-- max(version)+1 and are NOT uniform.
--
-- NOTE: four bodies also carry a single-token `JSON` repair. Without it
-- those rows 400 on Alibaba under response_format=json_object and cannot
-- generate at all. See the header of scripts/stage_task721_templates.py.

BEGIN;

-- question_vocabulary_context [zh] v3 -> v4  md5 7318045481c54c7cf6f6111efd8a671b
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider,
   template_text, description)
VALUES ('question_vocabulary_context', 1, 4, false,
        'qwen/qwen3.7-plus', 'openrouter',
        $tpl$你是一位中文母语语言测评专家。请根据提供的短文，从零生成一道四选一的“语境中的词汇”阅读理解题。题目必须完全基于短文语境，考查读者对文中某个汉语词汇单位在特定上下文里含义的理解。

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

构造干扰项时，必须让每个错误选项都“错误但有迷惑性”。干扰项应与短文属于同一学科或领域；一个指向同领域真实事物的干扰项，即使文章从未提到它，也是好的干扰项；没有出现在文中，恰恰就是它错误的原因，不要仅仅因为文章没有提到就回避某个选项。在语境中的词汇题中，这主要指干扰项应属于目标词的语义、语用或熟语解释范围。绝对禁止写出结合题目也可以算作正确的干扰项；只要认真的读者能为它辩护，这道题就有了两个答案，会被整题丢弃。这是危害最大的一种错误。也绝对禁止写出与正确答案同义改写的干扰项，不得与正确答案接近到学习者无法区分。不要跨到另一个学科，例如在讲电路的文章里给出一种情绪，也不要写荒谬无意义的选项。四个选项在长度、句式和信息量上要尽量接近，不要让正确项因形式而暴露。这类题的干扰项，是目标词语的其他义项，因此要针对这个词本身去衡量，而不是针对文章的主题。与文章主题毫无关系的选项在这类题里不算离题，那才是正常情况。最有力的写法是：比喻性表达的字面义；多义词的另一个固定义项；以及在程度、对象或语体色彩上有差别的近义解释。

示例：例文：这次事故起初只是一个小疏漏，若能及时上报并补救，损失不至于扩大。可惜几位主管互相推诿，拖延了两天，最终酿成大祸，可以说是养痈遗患。问题：文中“养痈遗患”最恰当的理解是什么？正确答案：纵容隐患，留下后患。干扰项示例：一、对问题处理不当，反而使矛盾更加尖锐；二、小疏漏没有及时补救，最终使损失扩大；三、放任祸患，遗留后患。其中，第一项是好干扰项，因为它与正确项同属书面固定表达的解释方向，表面与事故扩大有关，但并非该成语的核心义，能迷惑理解不精确的读者。第二项被否决，因为结合题目也可以算作正确，会造成两个答案。第三项被否决，因为它是正确答案的同义改写，学习者无法区分。

八、输出要求
最终只输出一个 JSON 对象，不要输出标题、说明、编号、分析过程、代码框或任何额外文字。对象格式如下：
{{
  "question_text": "文中‘打退堂鼓’最接近的意思是什么？",
  "question_type": "vocabulary_context",
  "choices": ["用鼓声激励大家继续", "中途放弃或退缩", "临时改变原定计划", "把事情推给别人"],
  "answer": "中途放弃或退缩",
  "explanation": "语境写遇到困难后不再坚持，因此这里应理解为中途放弃或退缩。"
}}$tpl$,
        $tpl$TASK-721 v4 (STAGED, inactive): adds a distractor-construction block inverted from the live test_distractor_plausibility rubric (sense family), plus the json-token repair that unbroke json_object calls on Alibaba. Body = the incumbent verbatim + one spliced block.$tpl$)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active     = EXCLUDED.is_active,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       template_text = EXCLUDED.template_text,
       description   = EXCLUDED.description,
       updated_at    = now();

-- question_vocabulary_context [en] v1 -> v2  md5 4509299819866429f4505b14b19745b5
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider,
   template_text, description)
VALUES ('question_vocabulary_context', 2, 2, false,
        'google/gemini-3.5-flash-lite', 'openrouter',
        $tpl$You are generating a **Vocabulary in Context** comprehension question.

Generate exactly ONE multiple-choice question in this JSON format:
{{
  "question_text": "question text here",
  "question_type": "vocabulary_context",
  "choices": ["Choice A", "Choice B", "Choice C", "Choice D"],
  "answer": "Choice B",
  "explanation": "Brief explanation why this is correct"
}}

---

**CRITICAL: AVOID DUPLICATION**
You MUST NOT create questions similar to these already generated:
{previous_questions}

**Uniqueness Requirements:**
- Ask about a DIFFERENT word, phrase, idiom, or saying
- Target DIFFERENT parts of the passage
- Use DIFFERENT question formats
- Avoid repeating vocabulary already tested

---

**Vocabulary in Context Guidelines:**

**For Lower Levels (1-4):**
- Focus on common words or simple phrases that might have multiple meanings
- Test understanding of basic vocabulary in context
- Example: "What does 'bright' mean in this passage?"

**For Mid Levels (5-6):**
- Focus on phrasal verbs, common idioms, or less frequent vocabulary
- Test contextual meaning of expressions
- Example: "What does 'pick up' mean in this context?"

**For Advanced Levels (7-9):**
- **MANDATORY:** Focus on idioms, phrases, sayings, or expressions (NOT individual words)
- Test understanding of figurative language, collocations, or multi-word units
- Example: "What does the phrase 'turn a blind eye' mean in this passage?"

---

**Few-shot Examples:**

**Mid-level Example:**
Passage: "After the storm, the community came together to pick up the pieces and rebuild what was lost."

Question: "What does 'pick up the pieces' mean in this context?"
Choices: ["To collect broken items", "To recover and rebuild after difficulty", "To clean the streets", "To start a new project"]
Correct Answer: "To recover and rebuild after difficulty"
Explanation: "The phrase means to recover from a difficult situation, as shown by the context of rebuilding after the storm."

**Advanced Example (C2):**
Passage: "The CEO turned a blind eye to the accounting irregularities, even though the auditors repeatedly raised concerns."

Question: "What does 'turn a blind eye' mean in this passage?"
Choices: ["To deliberately ignore something", "To not notice something accidentally", "To review carefully", "To express disagreement"]
Answer: "To deliberately ignore something"
Explanation: "The idiom means to intentionally overlook or ignore something, usually something wrong."

---

---

**Building the three wrong choices**

Every wrong choice you write is scored 1-5 after generation, and a choice
scored 1 or 2 discards the whole question. Build to that scale:

- **Stay inside the passage's own subject.** A wrong choice that names a real
  thing from the same subject is a GOOD wrong choice *even when the passage
  never mentions it* — being absent from the text is precisely what makes it
  wrong. Never avoid an option merely because the passage does not contain it.
- **Never write a choice that is also arguably correct.** If a careful reader
  could defend it against your stated answer, the question has two answers and
  is thrown away. This is the most damaging failure mode.
- **Never write a choice that paraphrases the correct answer,** or sits so close
  to it that a learner cannot tell the two apart.
- **Never reach into a different subject** (an emotion offered as a choice in a
  passage about electrical circuits), and never write anything absurd.
- Keep all four choices comparable in length, grammatical shape and level of
  detail, so the answer is not identifiable by its form alone.

For this question type the wrong choices are competing MEANINGS of the target
expression, so weigh them against the word itself, not against the passage's
subject. An option with nothing to do with the passage's topic is NOT off-subject
here — it is the ordinary case. The strongest ones are: the literal reading of a
figurative expression; another established sense of a polysemous word; or a
near-sense that differs in degree, object or register.

Worked example — using the passage above ("The CEO turned a blind eye to the
accounting irregularities"), for the question "What does 'turn a blind eye'
mean?" with the answer "To deliberately ignore something":
  GOOD      — "To lose sight in one eye": the literal reading of the idiom. It
              has nothing to do with accounting, and for THIS question type that
              is correct behaviour, not an off-subject error.
  REJECTED  — "To fail to notice something": a near-sense a reader can defend
              against the answer — arguably correct.
  REJECTED  — "To intentionally overlook something": a synonym of the answer.

---

**Your Task:**
- Base your question on this passage: {prose}
- Difficulty level: {difficulty}/9
- **If difficulty is 7-9, you MUST ask about an idiom, phrase, or multi-word expression, NOT a single word**
- MUST be completely different from previous questions

Return ONLY the JSON object, no additional text.$tpl$,
        $tpl$TASK-721 v2 (STAGED, inactive): adds a distractor-construction block inverted from the live test_distractor_plausibility rubric (sense family), plus the json-token repair that unbroke json_object calls on Alibaba. Body = the incumbent verbatim + one spliced block.$tpl$)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active     = EXCLUDED.is_active,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       template_text = EXCLUDED.template_text,
       description   = EXCLUDED.description,
       updated_at    = now();

-- question_vocabulary_context [ja] v3 -> v4  md5 98fa496a17f1c0bf3dd224ece7f7a0b4
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider,
   template_text, description)
VALUES ('question_vocabulary_context', 3, 4, false,
        'qwen/qwen3.7-plus', 'openrouter',
        $tpl$あなたは日本語母語の言語評価の専門家として、日本語の読解問題を作成してください。以下の資料と難易度に基づき、「文脈における語彙」を問う四択問題を 1 問だけ作ってください。

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

【誤答選択肢の作成方針】
誤答は本文と同じ分野・領域に属すること。本文に書かれていないからといって避けないこと。同じ分野の実在する事物や意味を指す誤答は、本文が一度も触れていなくてもよい。本文に出てこないことこそ、それが誤りである理由になる。ただし、この問題種では同じ分野・領域かどうかは本文の主題ではなく対象語の意味・用法に照らして判断する。本文の話題と直接関係のない意味に見えても、対象語の別の用法として自然なら、話題外ではなく通常の姿である。
最も害が大きいのは、問題に対して正解とも言える選択肢である。注意深い読者が正解として擁護できるなら、答えが二つになり問題は破棄される。正解の言い換えや、学習者が意味のある区別をできないほど正解に近い選択肢も作らないこと。対象語の意味として成立しない別の分野へ踏み込む選択肢、不合理・無意味な選択肢も避けること。四つの選択肢は品詞、文末、長さ、情報量をそろえ、形だけで正解が推測されないようにすること。
この種類で強い誤答は、比喩表現を字義どおりに読んだ解釈、多義語の別の確立した意味、程度・対象・語感が異なる近い意味である。

【例】
既存の中級例文「その店は評判を落としたが、最近ようやく持ち直してきた。」で「持ち直してきた」を問う場合。
良い誤答：再び持ち上げられてきた。対象語を字義どおりに読んだ別の意味で、文脈からは外れるが、語そのものに照らして自然に迷いやすい。
却下される誤答：悪い状態から回復してきた。この文では正解として成立するため、答えが二つになり得る。
却下される誤答：落ち込みから立ち直ってきた。正解と実質的に同じ言い換えで、学習者が区別できない。

【出力形式】
出力は、次の JSON オブジェクトのみとすること。オブジェクトの外に説明文や余分な記号を付けないこと。以下は形式を示す例であり、実際の値は問題に合わせて置き換えること。正解の値は、選択肢のいずれかと完全に一致させること。

{{
  "question_text": "例：文中の（表現）の意味として最も適切なものを選んでください。",
  "question_type": "vocabulary_context",
  "choices": ["例：字義どおりの解釈", "例：文脈に合う解釈", "例：別の慣用的な解釈", "例：関連するが的外れな解釈"],
  "answer": "例：文脈に合う解釈",
  "explanation": "例：この文では、対象語が比喩的に使われているため、この意味が適切である。"
}}$tpl$,
        $tpl$TASK-721 v4 (STAGED, inactive): adds a distractor-construction block inverted from the live test_distractor_plausibility rubric (sense family), plus the json-token repair that unbroke json_object calls on Alibaba. Body = the incumbent verbatim + one spliced block.$tpl$)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active     = EXCLUDED.is_active,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       template_text = EXCLUDED.template_text,
       description   = EXCLUDED.description,
       updated_at    = now();

-- question_author_purpose [zh] v1 -> v2  md5 901f77802698212a4411307b77b7b277
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider,
   template_text, description)
VALUES ('question_author_purpose', 1, 2, false,
        'qwen/qwen3.7-plus', 'openrouter',
        $tpl$你正在生成一个**作者意图/语气**类阅读理解问题。

请严格按照以下 JSON 格式生成**一个**多项选择题：
{{
  "question_text": "问题文本在此",
  "question_type": "author_purpose",
  "choices": ["选项 A", "选项 B", "选项 C", "选项 D"],
  "answer": "选项 B",
  "explanation": "简要说明此答案为何正确"
}}

---

**重要：避免重复**
你**不得**创建与以下已生成问题相似的问题：
{previous_questions}

**唯一性要求：**
- 提问关于**不同方面**的内容（如意图、语气、态度或观点之间的区别）
- 以**不同方式**构建问题
- 聚焦于段落的**不同部分**或整体表达
- 提供**不同类型**的选项

---

**作者意图/语气类问题指南：**
- 聚焦于作者**为何**撰写该段文字，以及其态度、语气或视角
- 考察学生对作者写作目的、立场或情感倾向的理解
- 可提问的内容包括：写作目的（告知、说服、娱乐）、语气（乐观、批判、中立）、态度（支持、怀疑）或组织方式
- 需要分析作者的语言选择、文章结构和整体信息传递
- 所有答案必须有文本证据支持

---

**少量示例：**
段落：“虽然新政策对部分居民有明显好处，但其实施时间表仍令人担忧。仓促的审批流程留下了许多未解答的问题。然而，如果有适当的社区参与和分阶段推行，这些挑战或许能够得到解决。”

问题：“作者对新政策的整体语气是什么？”
选项：[
  "完全反对且充满敌意",
  "谨慎乐观但保留担忧",
  "完全热情且全力支持",
  "中立且漠不关心"
]
正确答案："谨慎乐观但保留担忧"
解释："作者既承认政策的好处，也指出存在的问题，批评了审批过程，但结尾表达了有条件的积极看法（‘或许能够解决’），体现出保留态度下的乐观。"

---

出题时，干扰项必须属于同一学科或领域，同时错误而有迷惑性。作者意图、语气类题目中，干扰项应是读者可能错误归给作者的写作目的、语气或信息；即使文章没有提到，只要它属于同一话题且能构成合理误解，就是好干扰项，未出现正是它错误的原因，不要仅因文章未提到而回避。不要写跨学科选项，不要写荒谬无意义选项。四个选项在长度、句式和信息量上要尽量接近，不要让正确项因形式而暴露。

绝对不要写结合题目也能算正确的干扰项。只要认真读者能为它辩护，题目就会出现两个答案，整题会被丢弃。也绝对不要写正确答案的同义改写，或接近到学习者无法区分的选项。这里的离题指文章毫无迹象的意图，而不是文章碰巧没有提到的话题。最有力的干扰项包括：与文章自身措辞相抵触的立场；把真实存在但只是次要的目的说成主要目的；过窄地只抓一个细节；或过宽地超出文章范围。

示例沿用新政策段落：“虽然新政策对部分居民有明显好处，但其实施时间表仍令人担忧。仓促的审批流程留下了许多未解答的问题。然而，如果有适当的社区参与和分阶段推行，这些挑战或许能够得到解决。”问题：作者对新政策的整体语气是什么？正确答案：谨慎乐观但保留担忧。好干扰项：完全反对且充满敌意。它好在属于同一领域，明显与文中承认好处并提出可解决条件相抵触，但粗心读者可能只看到批评而误选。应否决：既承认好处又担心实施。它也可以算作正确，因为认真读者会认为它就是对原文态度的概括。应否决：审慎乐观但保留疑虑。它是正确答案的同义改写，学习者无法有意义区分。

**你的任务：**
- 问题必须基于以下段落：{prose}
- 难度等级：{difficulty}/9
- 分析作者的写作意图、语气、态度或观点
- 答案需结合语言使用和结构特点提供文本依据
- 必须在关注点上与之前的问题完全不同

仅返回 JSON 对象，不要任何额外文本。$tpl$,
        $tpl$TASK-721 v2 (STAGED, inactive): adds a distractor-construction block inverted from the live test_distractor_plausibility rubric (intent family), plus the json-token repair that unbroke json_object calls on Alibaba. Body = the incumbent verbatim + one spliced block.$tpl$)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active     = EXCLUDED.is_active,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       template_text = EXCLUDED.template_text,
       description   = EXCLUDED.description,
       updated_at    = now();

-- question_author_purpose [en] v1 -> v2  md5 11f463227f1aac5b90f651ad1ffe46d7
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider,
   template_text, description)
VALUES ('question_author_purpose', 2, 2, false,
        'google/gemini-3.5-flash-lite', 'openrouter',
        $tpl$You are generating an **Author Purpose/Tone** comprehension question.

Generate exactly ONE multiple-choice question in this JSON format:
{{
  "question_text": "question text here",
  "question_type": "author_purpose",
  "choices": ["Choice A", "Choice B", "Choice C", "Choice D"],
  "answer": "Choice B",
  "explanation": "Brief explanation why this is correct"
}}

---

**CRITICAL: AVOID DUPLICATION**
You MUST NOT create questions similar to these already generated:
{previous_questions}

**Uniqueness Requirements:**
- Ask about DIFFERENT aspects (purpose vs. tone vs. attitude vs. perspective)
- Frame questions in DIFFERENT ways
- Focus on DIFFERENT sections or the overall passage
- Offer DIFFERENT types of choices

---

**Author Purpose/Tone Guidelines:**
- Focus on WHY the author wrote the passage, their attitude, tone, or perspective
- Test understanding of author's intent, viewpoint, or emotional stance
- May ask about: purpose (inform, persuade, entertain), tone (optimistic, critical, neutral), attitude (supportive, skeptical), or organizational approach
- Require analysis of language choices, structure, and overall message
- Answers must be supported by textual evidence

---

**Few-shot Example:**
Passage: "While the new policy has clear benefits for some residents, concerns remain about its implementation timeline. The rushed approval process left many questions unanswered. However, with proper community input and phased rollout, these challenges could potentially be addressed."

Question: "What is the author's overall tone toward the new policy?"
Choices: [
  "Completely opposed and hostile",
  "Cautiously optimistic with reservations",
  "Entirely enthusiastic and supportive",
  "Neutral and indifferent"
]
Answer: "Cautiously optimistic with reservations"
Explanation: "The author acknowledges both benefits and concerns, expresses criticism of the process, but ends with a conditional positive outlook ('could potentially be addressed')."

---

---

**Building the three wrong choices**

Every wrong choice you write is scored 1-5 after generation, and a choice
scored 1 or 2 discards the whole question. Build to that scale:

- **Stay inside the passage's own subject.** A wrong choice that names a real
  thing from the same subject is a GOOD wrong choice *even when the passage
  never mentions it* — being absent from the text is precisely what makes it
  wrong. Never avoid an option merely because the passage does not contain it.
- **Never write a choice that is also arguably correct.** If a careful reader
  could defend it against your stated answer, the question has two answers and
  is thrown away. This is the most damaging failure mode.
- **Never write a choice that paraphrases the correct answer,** or sits so close
  to it that a learner cannot tell the two apart.
- **Never reach into a different subject** (an emotion offered as a choice in a
  passage about electrical circuits), and never write anything absurd.
- Keep all four choices comparable in length, grammatical shape and level of
  detail, so the answer is not identifiable by its form alone.

For this question type the wrong choices are other purposes, tones or messages a
reader might attribute to the author. "Different subject" here means an intent
the text gives no sign of — *not* a topic the passage happens to omit. The
strongest ones are: a stance the passage's own wording contradicts; a real but
secondary purpose offered as the main one; or a message that is too narrow (one
detail) or too broad (beyond the passage's scope).

Worked example — using the passage above (clear benefits, a rushed approval
process, a conditional positive close), for the question "What is the author's
overall tone?" with the answer "Cautiously optimistic with reservations":
  GOOD      — "Nostalgic for the previous policy": a real authorial stance that
              the passage's forward-looking close plainly contradicts.
  REJECTED  — "Critical of how the policy was approved": the passage does
              criticise the rushed process, so this is arguably correct.
  REJECTED  — "Hopeful but with some concerns": the answer reworded.

---

**Your Task:**
- Base your question on this passage: {prose}
- Difficulty level: {difficulty}/9
- Analyze author's purpose, tone, attitude, or perspective
- Support answer with evidence from language choices and structure
- MUST be different from previous questions in focus

Return ONLY the JSON object, no additional text.$tpl$,
        $tpl$TASK-721 v2 (STAGED, inactive): adds a distractor-construction block inverted from the live test_distractor_plausibility rubric (intent family), plus the json-token repair that unbroke json_object calls on Alibaba. Body = the incumbent verbatim + one spliced block.$tpl$)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active     = EXCLUDED.is_active,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       template_text = EXCLUDED.template_text,
       description   = EXCLUDED.description,
       updated_at    = now();

-- question_author_purpose [ja] v3 -> v4  md5 145911e95c72874956302b70b56d9d28
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider,
   template_text, description)
VALUES ('question_author_purpose', 3, 4, false,
        'qwen/qwen3.7-plus', 'openrouter',
        $tpl$あなたは日本語母語の言語評価の専門家として、筆者の意図や文章の調子を問う読解問題を作成してください。次の文章を読み、四択問題を一問だけ作ります。材料となる文章は{prose}です。難易度は{difficulty}を基準とし、語彙、文の長さ、設問のひねり、選択肢の紛らわしさを調整してください。難易度が低い場合は本文の明示的な手がかりを、高い場合は間接的な表現や言い回しのニュアンスを手がかりにしてください。

すでに出題された質問の一覧である{previous_questions}を確認し、前回と同じ観点にならないようにしてください。問う観点は、書いた目的、文章の調子、筆者の態度、視点、論の進め方のいずれかから選び、前回と異なるものにしてください。このとき、英字の記号や外国語の用語は使わず、日本語で言い分けてください。

設問は、筆者がなぜその文章を書いたのか、その態度・調子・立場を問うものにしてください。筆者の意図、見方、感情的な立場の理解を測ること。書いた目的、文章の調子、立場、論の運び方のうち一つに焦点を当ててください。語の選び方、構成、全体のメッセージの分析を求めること。正解は必ず本文中の根拠に裏づけられていること。選択肢は四つすべて本文の内容から判断できるものにしてください。本文に書かれていない推測や、一般論だけでは正解を導けないようにしてください。誤答の選択肢は、本文の一部を誇張したり、反対の意味に変えたり、範囲を広げすぎたりして、明確に誤りと判断できるものにしてください。正解の位置は固定せず、四つの選択肢のどこにあってもよいようにしてください。

作成例：
文章：新しい働き方として週休三日制が注目されている。生産性の向上や育児・介護との両立を考えると、導入には確かに利点がある。ただし、業種によっては人員確保が難しく、賃金削減を招くおそれもある。したがって、一律に理想と持ち上げるのではなく、職種や企業規模に応じた慎重な設計が不可欠だろう。
質問：この文章における筆者の態度として最も適切なものはどれか。
選択肢：
・週休三日制を全面的に支持している。
・週休三日制に反対している。
・条件付きで導入を認めている。
・導入の可否に関心を持っていない。
正解：条件付きで導入を認めている。
解説：筆者は「確かに利点がある」と述べる一方で、「ただし」「おそれもある」「慎重な設計が不可欠」と留保を示しており、無条件の賛成でも反対でもないため。

誤答の選択肢は、本文と同じ分野・領域に属するものとして作ってください。同じ分野で実際に成り立ちうる意図や調子なら、本文が一度も触れていなくてもよい誤答です。本文に書かれていないことは、誤りである理由であって、避ける理由ではありません。ただし、問題に対して正解とも言える選択肢は固く禁じます。注意深い読者が正解として擁護できるなら、答えが二つになり、問題ごと破棄されます。正解の言い換えや、学習者が区別できないほど正解に近い誤答も固く禁じます。電気回路の文章で感情を選ぶような別の分野の意図、不合理で無意味な選択肢も書かないでください。誤答は、本文の一部を誇張したり、反対の意味に変えたり、範囲を広げすぎたりして、明確に誤りと判断できるものにしてください。四つの選択肢はすべて本文の内容と照らして判断できるものにしてください。本文に書かれていない推測や一般論だけでは正解を導けないようにしてください。四つの選択肢は長さ・文の形・情報量をできるだけ揃え、形だけで正解が分からないようにしてください。この種類の問題では、誤答は読者が筆者に帰しうる別の目的・調子・主張です。ここでの分野が違うとは、本文に何の兆しもない意図のことであり、本文がたまたま触れていない話題のことではありません。最も強い作り方は、本文自身の言い回しと矛盾する立場、実在するが副次的にすぎない目的を主目的として示すもの、細部だけに基づく狭すぎる主張、本文の範囲を超える広すぎる主張です。

例として、週休三日制の文章で「筆者の態度として最も適切なものはどれか」と問う場合を考えます。正解を「条件付きで導入を認めている」とします。良い誤答は「週休三日制を全面的に支持している」です。本文が利点を認めつつ留保を示す同じ話題内の態度であり、不注意な読者が選びかねない一方、明確に誤りと判断できます。却下される誤答は「職種や企業規模に応じた慎重な設計が不可欠だと考えている」です。これは本文の主張そのもので、正解とも言えてしまうためです。却下される誤答は「条件付きで導入を認めている」と実質的に同じ意味の「一定の条件の下で導入を認めている」です。

最終的な出力は、次の JSON 形式のみとしてください。それ以外の説明、記号、注意書きは含めないでください。出力の形式は以下とし、種類を示す値は変えないでください。

{{
  "question_text": "...",
  "question_type": "author_purpose",
  "choices": ["...", "...", "...", "..."],
  "answer": "...",
  "explanation": "..."
}}$tpl$,
        $tpl$TASK-721 v4 (STAGED, inactive): adds a distractor-construction block inverted from the live test_distractor_plausibility rubric (intent family), plus the json-token repair that unbroke json_object calls on Alibaba. Body = the incumbent verbatim + one spliced block.$tpl$)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active     = EXCLUDED.is_active,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       template_text = EXCLUDED.template_text,
       description   = EXCLUDED.description,
       updated_at    = now();

-- question_main_idea [zh] v1 -> v2  md5 73c831478820e0d30ecee9639d4d3aa2
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider,
   template_text, description)
VALUES ('question_main_idea', 1, 2, false,
        'qwen/qwen3.7-plus', 'openrouter',
        $tpl$你正在生成一个**主旨大意**类阅读理解问题。

请严格按照以下 JSON 格式生成**一个**多项选择题：
{{
  "question_text": "问题文本在此",
  "question_type": "main_idea",
  "choices": ["选项 A", "选项 B", "选项 C", "选项 D"],
  "answer": "选项 C",
  "explanation": "简要说明此答案为何正确"
}}

---

**重要：避免重复**
你**不得**创建与以下已生成问题相似的问题：
{previous_questions}

**唯一性要求：**
- 主旨问题的表述方式必须**不同**（例如：提问目的、主题或核心信息的角度不同）
- 使用**不同**的措辞和问题结构
- 提供**不同类型**的干扰项（错误选项）

---

**主旨大意类问题指南：**
- 聚焦于段落的核心主题、主要目的或整体信息
- 要求理解全文大意，而非仅个别细节
- 考察综合信息并识别段落主要讲什么的能力
- 错误选项应具有以下特征之一：过于具体（仅为细节）、过于宽泛（超出段落范围）或事实错误

---

**少量示例：**
段落：“城市农业正在改变世界各地的城市。社区花园为食物贫瘠区提供新鲜农产品，屋顶农场降低建筑能耗，垂直绿化改善空气质量。尽管存在挑战，这些创新展示了城市如何变得更可持续。”

问题：“这段文字的主旨是什么？”
选项：[
  "屋顶农场可以降低能源成本",
  "城市农业面临重大挑战",
  "城市农业项目正在使城市变得更加可持续",
  "社区花园解决了所有城市食品问题"
]
正确答案："城市农业项目正在使城市变得更加可持续"
解释："段落讨论了城市农业的多个益处，并得出结论：这些创新提升了城市的可持续性。"

---

构造主旨大意题的干扰项时，每个错误选项都应明显错误、具有迷惑性，并属于文章同一学科或领域，像读者可能误认为的作者目的、语气或核心信息。某个选项即使文章没有提到，只要它指向同领域的真实内容，也可以是好的干扰项；没有出现在文中，正是它错误的原因，不要因此回避。绝不能写出结合题目也可以算作正确的选项；只要认真的读者能为它辩护，就会出现两个答案。也不能把正确答案换个说法，或写得与正确答案过于接近，使学习者无法区分。不要跨到另一个学科，不要写荒谬无意义的选项。四个选项在长度、句式和信息量上应尽量接近，不要让正确项因形式暴露。主旨题中的离题，指文章毫无迹象的写作意图，而不是文章碰巧没有提到的话题。最有力的干扰项包括：与文章自身措辞相抵触的立场，把真实存在但次要的写作目的说成主要目的，以及过窄地只概括一个细节或过宽地超出文章范围。示例：段落写城市农业带来多种好处，并说这些创新使城市更可持续。正确答案可为“城市农业项目正在使城市变得更加可持续”。好的干扰项可为“屋顶农场可以降低能源成本”，因为它属于同一领域，并与文中真实细节相关，但只是局部信息，不能概括主旨，容易让粗心者误选。应否决“城市农业正在改变世界各地的城市”，因为它也可以被理解为段落核心，认真读者能为它辩护，会造成两个答案。应否决“城市农业让城市变得更可持续”，因为它是正确答案的同义改写，学习者无法区分。

**你的任务：**
- 问题必须基于以下段落：{prose}
- 难度等级：{difficulty}/9
- 必须考虑**整段文字**，而非仅某一部分
- 必须在提问方式上与之前的问题完全不同

仅返回 JSON 对象，不要任何额外文本。$tpl$,
        $tpl$TASK-721 v2 (STAGED, inactive): adds a distractor-construction block inverted from the live test_distractor_plausibility rubric (intent family), plus the json-token repair that unbroke json_object calls on Alibaba. Body = the incumbent verbatim + one spliced block.$tpl$)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active     = EXCLUDED.is_active,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       template_text = EXCLUDED.template_text,
       description   = EXCLUDED.description,
       updated_at    = now();

-- question_main_idea [en] v1 -> v2  md5 dcf426dba8a52418b282a9c59da6d8df
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider,
   template_text, description)
VALUES ('question_main_idea', 2, 2, false,
        'google/gemini-3.5-flash-lite', 'openrouter',
        $tpl$You are generating a **Main Idea** comprehension question.

Generate exactly ONE multiple-choice question in this JSON format:
{{
  "question_text": "question text here",
  "question_type": "main_idea",
  "choices": ["Choice A", "Choice B", "Choice C", "Choice D"],
  "answer": "Choice C",
  "explanation": "Brief explanation why this is correct"
}}

---

**CRITICAL: AVOID DUPLICATION**
You MUST NOT create questions similar to these already generated:
{previous_questions}

**Uniqueness Requirements:**
- Frame the main idea question DIFFERENTLY (e.g., ask about purpose vs. theme vs. central message)
- Use DIFFERENT wording and question structure
- Offer DIFFERENT types of incorrect choices

---

**Main Idea Guidelines:**
- Focus on the central theme, primary purpose, or overall message of the passage
- Require understanding of the passage as a whole, not just individual details
- Test ability to synthesize information and identify what the passage is mainly about
- Wrong answers should be too specific (minor details), too broad (beyond passage scope), or factually incorrect

---

**Few-shot Example:**
Passage: "Urban farming is transforming cities worldwide. Community gardens provide fresh produce in food deserts, rooftop farms reduce building energy costs, and vertical gardens improve air quality. While challenges exist, these innovations show how cities can become more sustainable."

Question: "What is the main idea of this passage?"
Choices: [
  "Rooftop farms can reduce energy costs",
  "Urban farming faces significant challenges", 
  "Urban farming initiatives are making cities more sustainable",
  "Community gardens solve all urban food problems"
]
Answer: "Urban farming initiatives are making cities more sustainable"
Explanation: "The passage discusses multiple benefits of urban farming and concludes that these innovations increase city sustainability."

---

---

**Building the three wrong choices**

Every wrong choice you write is scored 1-5 after generation, and a choice
scored 1 or 2 discards the whole question. Build to that scale:

- **Stay inside the passage's own subject.** A wrong choice that names a real
  thing from the same subject is a GOOD wrong choice *even when the passage
  never mentions it* — being absent from the text is precisely what makes it
  wrong. Never avoid an option merely because the passage does not contain it.
- **Never write a choice that is also arguably correct.** If a careful reader
  could defend it against your stated answer, the question has two answers and
  is thrown away. This is the most damaging failure mode.
- **Never write a choice that paraphrases the correct answer,** or sits so close
  to it that a learner cannot tell the two apart.
- **Never reach into a different subject** (an emotion offered as a choice in a
  passage about electrical circuits), and never write anything absurd.
- Keep all four choices comparable in length, grammatical shape and level of
  detail, so the answer is not identifiable by its form alone.

For this question type the wrong choices are other purposes, tones or messages a
reader might attribute to the author. "Different subject" here means an intent
the text gives no sign of — *not* a topic the passage happens to omit. The
strongest ones are: a stance the passage's own wording contradicts; a real but
secondary purpose offered as the main one; or a message that is too narrow (one
detail) or too broad (beyond the passage's scope).

Worked example — using the passage above (community gardens, rooftop farms and
vertical gardens making cities more sustainable), for the question "What is the
main idea?" with the answer "Urban farming initiatives are making cities more
sustainable":
  GOOD      — "Cities are running out of space for conventional agriculture": a
              real urban-farming talking point that this passage never makes.
  REJECTED  — "Urban farming has several environmental benefits": true of the
              passage and defensible as its main idea — arguably correct.
  REJECTED  — "Urban agriculture is helping cities become more sustainable": the
              answer in synonyms.

---

**Your Task:**
- Base your question on this passage: {prose}
- Difficulty level: {difficulty}/9
- Consider the ENTIRE passage, not just one section
- MUST be different from previous questions in approach

Return ONLY the JSON object, no additional text.$tpl$,
        $tpl$TASK-721 v2 (STAGED, inactive): adds a distractor-construction block inverted from the live test_distractor_plausibility rubric (intent family), plus the json-token repair that unbroke json_object calls on Alibaba. Body = the incumbent verbatim + one spliced block.$tpl$)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active     = EXCLUDED.is_active,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       template_text = EXCLUDED.template_text,
       description   = EXCLUDED.description,
       updated_at    = now();

-- question_main_idea [ja] v3 -> v4  md5 351faa5ac9323c71cfd3ac9820032571
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider,
   template_text, description)
VALUES ('question_main_idea', 3, 4, false,
        'qwen/qwen3.7-plus', 'openrouter',
        $tpl$あなたは日本語の読解問題を作成する専門家です。以下の材料の文章を読み、文章全体の主旨を問う四択問題を 1 問作ってください。

材料の文章：
{prose}

難易度：{difficulty}

既に出題済みの質問：
{previous_questions}

課題：
文章の細部ではなく、文章全体から読み取れる中心主題、筆者の主な目的、全体としてのメッセージを問う問題を 1 問作成すること。情報を統合し、その文章が主として何について書かれているかを見抜く力を測ること。個々の出来事、数字、登場人物の行動だけを確認する問題にはしないこと。

作り方：
正しい選択肢は、文章全体を最もよく要約するものにする。誤答は、次のいずれかにすること。具体的すぎるため一部の細部にとどまるもの、広すぎて文章の範囲を超えるもの、文章の内容に照らして事実として誤っているもの。正解は四つの選択肢のうち一つだけにする。正解の位置は特定の位置に固定せず、内容に応じて決めること。例の配置に引きずられないこと。選択肢には番号や記号を含めず、本文だけを書くこと。

難易度が高い場合は、正解が一文の言い換えにとどまらず、複数の記述を突き合わせないと選べないような選択肢にする。難易度が低い場合は、中心主題を比較的つかみやすくする。ただし、どちらの場合も、文章に現れない一般論や筆者の感情を正解にしないこと。

既に出題済みの質問を参照し、問いの枠組み、表現、誤答の作り方を変え、同じような問題を繰り返さないこと。対比を示すために英字の記号を用いず、日本語の表現で書き分けること。質問文は自然な現代日本語とし、学習者が迷わない表現にすること。

正解の文字列は、選択肢の本文と完全に一致させること。質問文、選択肢、正解、解説はすべて自然な現代日本語にすること。

例：
文章：
昔ながらの商店街では、空き店舗が目立つようになった。そこで地元の人々は、使われていない店を改装し、子どもが放課後に過ごせる場所として開いた。お年寄りが将棋を教え、学生が宿題を見る。買い物のついでに立ち寄る人も増え、店先には笑顔が戻った。この取り組みは、空き店舗の活用にとどまらず、地域のつながりを結び直す試みとなっている。

質問：
この文章の主旨として最も適切なものはどれか。

選択肢：
空き店舗を改装して子どもが過ごす場所を作ったこと。
地域のつながりを回復する試みとして空き店舗活用が機能していること。
空き店舗を使えば、どの商店街でも地域のつながりが必ず回復すること。
お年寄りが将棋を教えることで子どもの学力が向上すること。

正解：
地域のつながりを回復する試みとして空き店舗活用が機能していること。

解説：
文章は、空き店舗の改装という出来事を出発点にしつつ、最終には地域のつながりを結び直す試みとして意味づけている。したがって、地域のつながりを回復する試みとして空き店舗活用が機能しているという選択肢が適切である。空き店舗の改装だけを取り上げる選択肢は具体策の一部にとどまり、どの商店街でも必ず回復するとする選択肢は文章の範囲を超える一般化であり、将棋で学力が向上するとする選択肢は文章にない因果を含んでいる。

例の正解の位置は偶然のものであり、同じ位置を選ぶ必要はない。

誤答選択肢は、本文と同じ分野・領域に属するものから作ること。同じ分野の実在する事柄や観点を指す誤答は、本文が一度もそれに触れていなくてもよい誤答である。本文に出てこないことこそ、それが誤りである理由なので、書かれていないという理由だけで選択肢を避けないこと。ただし、問題に対して正解とも言える誤答を書くことを固く禁じる。注意深い読者が正解に対してそれを擁護できるなら、答えが二つあることになり、問題ごと破棄される。正解の言い換えにあたる誤答や、学習者が意味のある区別をできないほど正解に近い誤答も固く禁じる。別の分野に踏み込まないこと。例えば電気回路の文章で感情や社交的な活動を選択肢に出すようなものは話題外である。不合理・無意味な選択肢も書いてはならない。四つの選択肢は長さ、文の形、情報量をできるだけ揃え、形だけで正解が分からないようにすること。この種類の問題では、誤答は読者が筆者に帰しうる別の目的、調子、主張である。ここでの分野が違うとは、本文に何の兆しもない意図のことであり、本文がたまたま触れていない話題のことではない。最も強い作り方は、本文自身の言い回しと矛盾する立場、実在するが副次的にすぎない目的を主目的として示すもの、細部一つだけに狭すぎる主張、本文の範囲を超える広すぎる主張である。

例は既存の商店街の文章を使う。良い誤答は「空き店舗を改装して子どもが過ごす場所を作ったこと。」である。同じ話題に属し、本文の一部分を正しく拾っているが、中心主題としては狭すぎるため、不注意な読者が選びやすい。却下される誤答は「空き店舗の活用にとどまらず、地域のつながりを結び直す試みとなっていること。」である。これは正解とも言えてしまうため、誤答として置けない。また却下される誤答は「地域のつながりを取り戻す試みとして空き店舗の活用が役立っていること。」である。正解の語句を入れ替えただけで、学習者が区別すべき意味の違いがない。

出力：
次の JSON オブジェクトだけを出力すること。前置き、後書き、見出し、説明文を付けないこと。

{{
  "question_text": "...",
  "question_type": "main_idea",
  "choices": ["...", "...", "...", "..."],
  "answer": "...",
  "explanation": "..."
}}$tpl$,
        $tpl$TASK-721 v4 (STAGED, inactive): adds a distractor-construction block inverted from the live test_distractor_plausibility rubric (intent family), plus the json-token repair that unbroke json_object calls on Alibaba. Body = the incumbent verbatim + one spliced block.$tpl$)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active     = EXCLUDED.is_active,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       template_text = EXCLUDED.template_text,
       description   = EXCLUDED.description,
       updated_at    = now();

-- question_literal_detail [zh] v1 -> v2  md5 0e8515d57912c1be5c388b7eaef98711
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider,
   template_text, description)
VALUES ('question_literal_detail', 1, 2, false,
        'qwen/qwen3.7-plus', 'openrouter',
        $tpl$你正在生成一个**字面细节**类阅读理解问题。

请严格按照以下 JSON 格式生成**一个**多项选择题：
{{
  "question_text": "问题文本在此",
  "question_type": "literal_detail",
  "choices": ["选项 A", "选项 B", "选项 C", "选项 D"],
  "answer": "选项 A",
  "explanation": "简要说明此答案为何正确"
}}

---

**重要：避免重复**
你**不得**创建与以下已生成问题相似的问题：
{previous_questions}

**唯一性要求：**
- 提问关于文中**不同**的事实或细节
- 使用**不同**的提问结构和措辞
- 确保正确答案涵盖**不同**的信息内容
- 聚焦于文章的**多样化部分**

---

**字面细节类问题指南：**
- 聚焦于对文中明确陈述信息的直接事实性回忆
- 提问具体细节：谁、什么、何时、何地、多少
- 考察对原文逐字出现或被转述的具体事实的理解
- 答案必须在文中清晰明确地表达
- 使用符合难度等级的简单、直接语言

---

**少量示例：**
段落："金门大桥于1937年建成。它跨越旧金山湾1.7英里，由工程师约瑟夫·施特劳斯设计。"

问题："金门大桥是何时建成的？"
选项：["1927", "1937", "1947", "1957"]
正确答案："1937"
解释："文中明确指出大桥于1937年建成。"

---

构造字面细节题的干扰项时，四个选项都必须属于文章同一学科或领域。错误选项的价值在于它错误但有迷惑性：它应当是同一领域中文章并不支持的事实或结论。优先使用三类写法：文中从未陈述、但确实属于该领域的真实事物；文中确实提到、却被安到错误的人物、时间、地点或因果上的细节；超出文本证据所能支持范围的结论。某个选项即使文章从未提到，也不要回避；没有出现在文中，恰恰就是它错误的原因。不要跨到另一个学科，例如在讲电路的文章里给出一种情绪；也不要写荒谬无意义的说法。严禁设置结合题目也可算作正确的干扰项：只要认真的读者能为它辩护，题目就有两个答案，会被整题丢弃。严禁把正确答案同义改写，或写得与正确答案过于接近，使学习者无法有意义地区分。四个选项在长度、句式和信息量上应尽量接近，不要让正确项因形式暴露。

示例：段落为“金门大桥于1937年建成。它跨越旧金山湾一点七英里，由工程师约瑟夫·施特劳斯设计。”问题为“金门大桥是何时建成的？”正确答案为“1937年”。干扰项可设为“1927年”“二十世纪三十年代”“1937年建成”。其中，“1927年”是好的，因为它是同一类时间信息，文中没有提到，形式自然且有迷惑性。“二十世纪三十年代”应否决，因为问题问建成时间，它也可算正确，会造成两个答案。“1937年建成”应否决，因为它只是正确答案的同义改写，无法与正确项区分。

**你的任务：**
- 依据以下段落：{prose}
- 难度等级：{difficulty}/9
- 必须在主题和措辞上与之前的问题**完全不同**

仅返回 JSON 对象，不要任何额外文本。$tpl$,
        $tpl$TASK-721 v2 (STAGED, inactive): adds a distractor-construction block inverted from the live test_distractor_plausibility rubric (fact family), plus the json-token repair that unbroke json_object calls on Alibaba. Body = the incumbent verbatim + one spliced block.$tpl$)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active     = EXCLUDED.is_active,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       template_text = EXCLUDED.template_text,
       description   = EXCLUDED.description,
       updated_at    = now();

-- question_literal_detail [en] v1 -> v2  md5 c8cceb0537bc63271968fb84a2fc37b5
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider,
   template_text, description)
VALUES ('question_literal_detail', 2, 2, false,
        'google/gemini-3.5-flash-lite', 'openrouter',
        $tpl$You are generating a **Literal Detail** comprehension question.

Generate exactly ONE multiple-choice question in this JSON format:
{{
  "question_text": "question text here",
  "question_type": "literal_detail",
  "choices": ["Choice A", "Choice B", "Choice C", "Choice D"],
  "answer": "Choice A",
  "explanation": "Brief explanation why this is correct"
}}

---

**CRITICAL: AVOID DUPLICATION**
You MUST NOT create questions similar to these already generated:
{previous_questions}

**Uniqueness Requirements:**
- Ask about DIFFERENT facts or details from the passage
- Use DIFFERENT question structures and wording
- Ensure your correct answer covers DIFFERENT information
- Focus on VARIED parts of the passage

---

**Literal Detail Guidelines:**
- Focus on direct factual recall of explicitly stated information
- Ask about concrete details: who, what, when, where, how many
- Test understanding of specific facts that appear word-for-word or paraphrased
- Answer must be unambiguously stated in the passage
- Use simple, direct language appropriate for the difficulty level

---

**Few-shot Example:**
Passage: "The Golden Gate Bridge was completed in 1937. It spans 1.7 miles across San Francisco Bay and was designed by engineer Joseph Strauss."

Question: "When was the Golden Gate Bridge completed?"
Choices: ["1927", "1937", "1947", "1957"]
Answer: "1937"
Explanation: "The passage explicitly states the bridge was completed in 1937."

---

---

**Building the three wrong choices**

Every wrong choice you write is scored 1-5 after generation, and a choice
scored 1 or 2 discards the whole question. Build to that scale:

- **Stay inside the passage's own subject.** A wrong choice that names a real
  thing from the same subject is a GOOD wrong choice *even when the passage
  never mentions it* — being absent from the text is precisely what makes it
  wrong. Never avoid an option merely because the passage does not contain it.
- **Never write a choice that is also arguably correct.** If a careful reader
  could defend it against your stated answer, the question has two answers and
  is thrown away. This is the most damaging failure mode.
- **Never write a choice that paraphrases the correct answer,** or sits so close
  to it that a learner cannot tell the two apart.
- **Never reach into a different subject** (an emotion offered as a choice in a
  passage about electrical circuits), and never write anything absurd.
- Keep all four choices comparable in length, grammatical shape and level of
  detail, so the answer is not identifiable by its form alone.

For this question type the wrong choices are same-subject facts or conclusions
the passage does not support. The strongest ones are: a real item from the
passage's domain that the text never states; a detail the passage *does* state
but attached to the wrong person, time, place or cause; or a conclusion that
reaches further than the passage's evidence licenses.

Worked example — using the passage above ("...designed by engineer Joseph
Strauss"), for the question "Who designed the Golden Gate Bridge?" with the
answer "Joseph Strauss":
  GOOD      — "Othmar Ammann": a real bridge engineer of the same era and
              domain whom the passage never names; that absence is why he is
              the wrong choice, and a reader who did not check will still be
              tempted.
  REJECTED  — "An American engineer": Strauss was one, so this is arguably
              correct. Two defensible answers, question discarded.
  REJECTED  — "The engineer who designed it": a paraphrase of the answer rather
              than a competitor to it.

---

**Your Task:**
- Base your question on this passage: {prose}
- Difficulty level: {difficulty}/9
- MUST be completely different from previous questions in topic and wording

Return ONLY the JSON object, no additional text.$tpl$,
        $tpl$TASK-721 v2 (STAGED, inactive): adds a distractor-construction block inverted from the live test_distractor_plausibility rubric (fact family), plus the json-token repair that unbroke json_object calls on Alibaba. Body = the incumbent verbatim + one spliced block.$tpl$)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active     = EXCLUDED.is_active,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       template_text = EXCLUDED.template_text,
       description   = EXCLUDED.description,
       updated_at    = now();

-- question_literal_detail [ja] v1 -> v2  md5 73c8903843f2e2439adfe0455c2dcc33
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider,
   template_text, description)
VALUES ('question_literal_detail', 3, 2, false,
        'qwen/qwen3.7-plus', 'openrouter',
        $tpl$あなたは **リテラル・ディテール（文字通りの詳細）** を問う読解作成問題を作成しています。

以下のJSON形式で、正確に1つの多肢選択問題を作成してください：
{{
  "question_text": "ここに質問文",
  "question_type": "literal_detail",
  "choices": ["選択肢A", "選択肢B", "選択肢C", "選択肢D"],
  "answer": "選択肢A",
  "explanation": "なぜこれが正解なのかの簡単な説明"
}}

---

**重要：重複の回避**
すでに作成された以下の質問と類似した質問を作成しては**いけません**：
{previous_questions}

**独自性の要件：**
- 文章内の**異なる**事実や詳細について尋ねること
- **異なる**質問構成や表現を使用すること
- 正解が**異なる**情報をカバーしていることを確認すること
- 文章内の**様々な**部分に焦点を当てること

---

**リテラル・ディテール（文字通りの詳細）のガイドライン：**
- 明示的に記述された情報の事実想起に焦点を当てること
- 具体的な詳細について尋ねること：誰が、何を、いつ、どこで、いくつ
- 一字一句そのまま、あるいは言い換えられて登場する特定の事実の理解を問うこと
- 答えは文章内に曖昧さなく記載されている必要がある
- 難易度に適した、単純で直接的な言葉を使用すること

---

**フューショットの例：**
文章：「ゴールデン・ゲート・ブリッジは1937年に完成した。サンフランシスコ湾をまたいで1.7マイルに広がり、エンジニアのジョセフ・ストラウスによって設計された。」

質問：「ゴールデン・ゲート・ブリッジはいつ完成しましたか？」
選択肢：["1927", "1937", "1947", "1957"]
正解："1937"
説明：「文章は橋が1937年に完成したと明示的に述べています。」

---

誤答選択肢は、本文と同じ分野・領域に属するものから作ること。同じ分野に実在する語や事実なら、本文が一度も触れていなくてもよい誤答になる。本文に書かれていないことは欠点ではなく、誤りである理由そのものである。したがって、本文にないというだけで選択肢を避けないこと。ただし、問題に対して正解とも言える誤答は固く禁じる。注意深い読者が正解として擁護できるなら、答えが二つになり問題ごと破棄される。正解の言い換えや、学習者が区別できないほど正解に近い誤答も固く禁じる。別の分野へ踏み込んではならない。電気回路の文章で感情を選ぶようなものは話題外である。不合理・無意味な選択肢も書かないこと。四つの選択肢は長さ・文の形・情報量をできるだけ揃え、形だけで正解が分からないようにすること。この種類の問題では、誤答は同じ分野に属しながら本文が支持していない事実や結論にする。最も強い作り方は、本文が一度も述べていないがその分野に実在するもの、本文が述べてはいるが人物・時点・場所・因果を取り違えて結びつけた細部、本文の根拠が許す範囲を超えて踏み込んだ結論である。

例は既存の橋の文章を使う。文章「ゴールデン・ゲート・ブリッジは一九三七年に完成した。サンフランシスコ湾をまたいで一・七マイルに広がり、エンジニアのジョセフ・ストラウスによって設計された。」質問「ゴールデン・ゲート・ブリッジはいつ完成しましたか？」正解「一九三七年」。良い誤答は「一九二七年」。同じ歴史・土木の分野に属する実在の年代で、本文が支持せず、不注意な読者が選びかねないため。却下される誤答は「一九三七年」。正解そのもので、正解とも言えてしまう。却下される誤答は「一九三七年に完成」。正解の実質的な言い換えにすぎない。

**あなたのタスク：**
- この文章に基づいて質問を作成してください：{prose}
- 難易度レベル：{difficulty}/9
- 以前の質問とは、トピックや表現において完全に異なっている**必要があります**

JSONオブジェクト**のみ**を返してください。追加のテキストは含めないでください。$tpl$,
        $tpl$TASK-721 v2 (STAGED, inactive): adds a distractor-construction block inverted from the live test_distractor_plausibility rubric (fact family), plus the json-token repair that unbroke json_object calls on Alibaba. Body = the incumbent verbatim + one spliced block.$tpl$)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active     = EXCLUDED.is_active,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       template_text = EXCLUDED.template_text,
       description   = EXCLUDED.description,
       updated_at    = now();

-- question_supporting_detail [zh] v1 -> v2  md5 e134192d6d4a1166c3b90dbb7a7944f6
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider,
   template_text, description)
VALUES ('question_supporting_detail', 1, 2, false,
        'qwen/qwen3.7-plus', 'openrouter',
        $tpl$你正在生成一个**支持性细节**类阅读理解问题。

请严格按照以下 JSON 格式生成**一个**多项选择题：
{{
  "question_text": "问题文本在此",
  "question_type": "supporting_detail",
  "choices": ["选项 A", "选项 B", "选项 C", "选项 D"],
  "answer": "选项 D",
  "explanation": "简要说明此答案为何正确"
}}

---

**重要：避免重复**
你**不得**创建与以下已生成问题相似的问题：
{previous_questions}

**唯一性要求：**
- 聚焦于**不同**的支持性细节、例子或证据
- 提问关于**不同**的关系（因果、举例、原因等）
- 使用段落中**不同部分**的内容
- 以**不同方式**构建问题

---

**支持性细节类问题指南：**
- 聚焦于支持主旨或关键观点的具体事实、例子或理由
- 考察学生对细节与整体概念之间关系的理解
- 可提问原因、结果、例子、证据或解释
- 要求的理解层次高于简单事实记忆，需理解信息间的关联
- 正确答案在文中明确提及，但可能以转述形式出现

---

**少量示例：**
段落：“该公司本季度利润增长了15%。这一增长源于强劲的在线销售和运营成本的降低。新的电子商务平台使网站流量增长了25%。”

问题：“根据段落，哪些因素促成了公司利润的增长？”
选项：[
  "提高价格和推出新产品",
  "强劲的在线销售和降低的运营成本",
  "更多员工和更大的办公室",
  "国际扩展和合作伙伴关系"
]
正确答案："强劲的在线销售和降低的运营成本"
解释："文中明确指出这两个因素是利润增长15%的原因。"

---

构造支持性细节题的干扰项时，应把它们设计成错误但有迷惑性、能让粗心读者误选的选项。干扰项必须与文章属于同一学科或领域，并围绕题目所问的关系展开。一个指向同领域真实事物的干扰项，即使文章从未提到它，也可以是好的干扰项；没有出现在文中，恰恰构成它错误的原因。不要仅仅因为文章没有提到某个合理细节就回避它。

绝对禁止写出结合题目也可以算作正确的干扰项。只要认真的读者能为某个选项辩护，题目就会出现两个答案，整道题会被丢弃。这是危害最大的一种错误。也绝对禁止写出正确答案的同义改写，或接近到学习者无法有意义区分的选项。不要跨到另一个学科，例如在讲公司利润的段落中放入一种情绪或一项社交活动；也不要写荒谬、无意义或明显不可信的选项。

四个选项在长度、句式和信息量上应尽量接近，不要让正确项因为更具体、更完整或更正式而暴露。支持性细节题的干扰项，最好是同一领域中文章并不支持的事实或结论。最有力的写法包括：文中从未陈述、但确实属于该领域的真实事物；文中确实提到、却被安到错误的人物、时间、地点或因果上的细节；以及超出文本证据所能支持范围的结论。

示例：段落为“该公司本季度利润增长了百分之十五。这一增长源于强劲的在线销售和运营成本的降低。新的电子商务平台使网站流量增长了百分之二十五。”问题为“根据段落，哪些因素促成了公司利润的增长？”正确答案为“强劲的在线销售和降低的运营成本”。好的干扰项可以是“提高价格和推出新产品”，因为它属于公司经营领域，听起来合理，但文章并未提到，因此错误且有迷惑性。应否决“在线销售增长”，因为文中已明确说它是利润增长的原因之一，结合题目它也可以算作正确。应否决“线上销售强劲和运营开支减少”，因为它只是正确答案的同义改写。

**你的任务：**
- 问题必须基于以下段落：{prose}
- 难度等级：{difficulty}/9
- 聚焦于**支持或解释**主要观点的细节
- 必须在内容和形式上与之前的问题完全不同

仅返回 JSON 对象，不要任何额外文本。$tpl$,
        $tpl$TASK-721 v2 (STAGED, inactive): adds a distractor-construction block inverted from the live test_distractor_plausibility rubric (fact family), plus the json-token repair that unbroke json_object calls on Alibaba. Body = the incumbent verbatim + one spliced block.$tpl$)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active     = EXCLUDED.is_active,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       template_text = EXCLUDED.template_text,
       description   = EXCLUDED.description,
       updated_at    = now();

-- question_supporting_detail [en] v1 -> v2  md5 8680864fd1f96508b7ad83ceb404a65a
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider,
   template_text, description)
VALUES ('question_supporting_detail', 2, 2, false,
        'google/gemini-3.5-flash-lite', 'openrouter',
        $tpl$You are generating a **Supporting Detail** comprehension question.

Generate exactly ONE multiple-choice question in this JSON format:
{{
  "question_text": "question text here",
  "question_type": "supporting_detail",
  "choices": ["Choice A", "Choice B", "Choice C", "Choice D"],
  "answer": "Choice D",
  "explanation": "Brief explanation why this is correct"
}}

---

**CRITICAL: AVOID DUPLICATION**
You MUST NOT create questions similar to these already generated:
{previous_questions}

**Uniqueness Requirements:**
- Focus on DIFFERENT supporting details, examples, or evidence
- Ask about DIFFERENT relationships (cause-effect, examples, reasons, etc.)
- Use DIFFERENT parts of the passage
- Frame questions in DIFFERENT ways

---

**Supporting Detail Guidelines:**
- Focus on specific facts, examples, or reasons that support the main idea or key points
- Test understanding of how details relate to larger concepts
- May ask about causes, effects, examples, evidence, or explanations
- Require comprehension beyond simple fact recall—need to understand relationships
- Answers are explicitly stated but may be paraphrased

---

**Few-shot Example:**
Passage: "The company's profits increased by 15% this quarter. This growth resulted from strong online sales and reduced operating costs. The new e-commerce platform contributed to a 25% increase in web traffic."

Question: "According to the passage, what factors contributed to the company's profit increase?"
Choices: [
  "Higher prices and new products",
  "Strong online sales and reduced operating costs",
  "More employees and bigger offices",
  "International expansion and partnerships"
]
Answer: "Strong online sales and reduced operating costs"
Explanation: "The passage explicitly states these two factors as reasons for the 15% profit increase."

---

---

**Building the three wrong choices**

Every wrong choice you write is scored 1-5 after generation, and a choice
scored 1 or 2 discards the whole question. Build to that scale:

- **Stay inside the passage's own subject.** A wrong choice that names a real
  thing from the same subject is a GOOD wrong choice *even when the passage
  never mentions it* — being absent from the text is precisely what makes it
  wrong. Never avoid an option merely because the passage does not contain it.
- **Never write a choice that is also arguably correct.** If a careful reader
  could defend it against your stated answer, the question has two answers and
  is thrown away. This is the most damaging failure mode.
- **Never write a choice that paraphrases the correct answer,** or sits so close
  to it that a learner cannot tell the two apart.
- **Never reach into a different subject** (an emotion offered as a choice in a
  passage about electrical circuits), and never write anything absurd.
- Keep all four choices comparable in length, grammatical shape and level of
  detail, so the answer is not identifiable by its form alone.

For this question type the wrong choices are same-subject facts or conclusions
the passage does not support. The strongest ones are: a real item from the
passage's domain that the text never states; a detail the passage *does* state
but attached to the wrong person, time, place or cause; or a conclusion that
reaches further than the passage's evidence licenses.

Worked example — using the passage above (profits up 15% from strong online
sales and reduced operating costs), for the question "What contributed to the
profit increase?" with the answer "Strong online sales and reduced operating
costs":
  GOOD      — "Higher prices and a new product line": ordinary drivers of profit
              in the same domain that the passage never claims, tempting to a
              reader who skimmed.
  REJECTED  — "The new e-commerce platform": the passage credits it with the
              traffic growth behind those online sales, so it is arguably
              correct.
  REJECTED  — "Good internet sales and lower running costs": the answer in
              synonyms.

---

**Your Task:**
- Base your question on this passage: {prose}
- Difficulty level: {difficulty}/9
- Focus on details that SUPPORT or EXPLAIN main points
- MUST be completely different from previous questions

Return ONLY the JSON object, no additional text.$tpl$,
        $tpl$TASK-721 v2 (STAGED, inactive): adds a distractor-construction block inverted from the live test_distractor_plausibility rubric (fact family), plus the json-token repair that unbroke json_object calls on Alibaba. Body = the incumbent verbatim + one spliced block.$tpl$)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active     = EXCLUDED.is_active,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       template_text = EXCLUDED.template_text,
       description   = EXCLUDED.description,
       updated_at    = now();

-- question_supporting_detail [ja] v1 -> v2  md5 063bd05013ae6398a5d5ad52f67fac6a
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider,
   template_text, description)
VALUES ('question_supporting_detail', 3, 2, false,
        'qwen/qwen3.7-plus', 'openrouter',
        $tpl$あなたは **サポーティング・ディテール（裏付けとなる詳細）** を問う読解問題を作成しています。

以下のJSON形式で、正確に1つの多肢選択問題を作成してください：
{{
  "question_text": "ここに質問文",
  "question_type": "supporting_detail",
  "choices": ["選択肢A", "選択肢B", "選択肢C", "選択肢D"],
  "answer": "選択肢D",
  "explanation": "なぜこれが正解なのかの簡単な説明"
}}

---

**重要：重複の回避**
すでに作成された以下の質問と類似した質問を作成しては**いけません**：
{previous_questions}

**独自性の要件：**
- **異なる**裏付けとなる詳細、例、または証拠に焦点を当てること
- **異なる**関係性（原因と結果、例示、理由など）について尋ねること
- 文章内の**異なる**部分を使用すること
- **異なる**方法で質問を構成すること

---

**サポーティング・ディテール（裏付けとなる詳細）のガイドライン：**
- メインアイデアや主要なポイントを支える特定の事実、例、または理由に焦点を当てること
- 詳細がより大きな概念とどのように関連しているかについての理解をテストすること
- 原因、結果、例、証拠、または説明について尋ねる場合がある
- 単純な事実想起を超えた理解（関係性の理解）を要求すること
- 答えは明記されているが、言い換えられている場合がある

---

**フューショットの例：**
文章：「同社の今四半期の利益は15％増加した。この成長は、好調なオンライン販売と運営コストの削減によるものである。新しいEコマースプラットフォームは、ウェブトラフィックの25％増加に貢献した。」

質問：「文章によると、同社の利益増加に貢献した要因は何ですか？」
選択肢：[
  "価格の上昇と新製品",
  "好調なオンライン販売と運営コストの削減",
  "従業員の増員とオフィスの拡大",
  "国際展開とパートナーシップ"
]
正解："好調なオンライン販売と運営コストの削減"
説明：「文章は、15％の利益増加の理由としてこれら2つの要因を明示的に述べています。」

---

誤答は、本文と同じ分野・領域に属するものだけを作ってください。同じ分野に実在する概念、事例、要因、結果であれば、本文が一度も触れていなくても良い誤答です。本文に書かれていないことこそが誤りの理由になるので、未言及というだけで避けないでください。

次の書き方は固く禁じます。第一に、注意深い読者が正解として擁護できる選択肢です。正解の一部だけを取り出したものや、本文から妥当に導ける事実は、答えが二つになり問題全体が無効になります。第二に、正解の言い換えや、意味の区別がほぼできないほど近い表現です。第三に、本文と別の分野に属する選択肢、不合理・無意味な選択肢です。

四つの選択肢は、長さ、文の形、情報量、具体性をそろえ、形だけで正解が分かることを防いでください。この種類の問題では、誤答は同じ分野に属しながら本文が支持していない事実や結論にします。特に、本文には出ないがその分野では自然な要因や例、本文にはあるが人物・時点・場所・因果を取り違えて結びつけた細部、本文の根拠が許す範囲を超えた結論を強く勧めます。

例
文章：「同社の今四半期の利益は十五％増加した。この成長は、好調なオンライン販売と運営コストの削減によるものである。新しい電子商取引の仕組みは、ウェブトラフィックの二十五％増加に貢献した。」
質問：「文章によると、同社の利益増加に貢献した要因は何ですか？」
正解：「好調なオンライン販売と運営コストの削減」
良い誤答：「価格の上昇と新製品」
理由：経営や販売と同じ分野に属し、利益増加の要因として自然だが、文章は述べていないため明らかに見分けられる。
却下される誤答：「好調なオンライン販売」
理由：文章が貢献を認めている要因そのもので、正解とも言えてしまう。
却下される誤答：「インターネット販売の好調と経費の圧縮」
理由：正解を実質的に言い換えただけで、学習者が区別できない。

**あなたのタスク：**
- この文章に基づいて質問を作成してください：{prose}
- 難易度レベル：{difficulty}/9
- メインポイントを**支持**または**説明**する詳細に焦点を当ててください
- 以前の質問とは完全に異なっている**必要があります**

JSONオブジェクト**のみ**を返してください。追加のテキストは含めないでください。$tpl$,
        $tpl$TASK-721 v2 (STAGED, inactive): adds a distractor-construction block inverted from the live test_distractor_plausibility rubric (fact family), plus the json-token repair that unbroke json_object calls on Alibaba. Body = the incumbent verbatim + one spliced block.$tpl$)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active     = EXCLUDED.is_active,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       template_text = EXCLUDED.template_text,
       description   = EXCLUDED.description,
       updated_at    = now();

-- question_inference [zh] v2 -> v3  md5 2112365715d81732dd3b509cbdd1be8b
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider,
   template_text, description)
VALUES ('question_inference', 1, 3, false,
        'qwen/qwen3.7-plus', 'openrouter',
        $tpl$你是一名中文母语的语言测评专家，请根据下面的材料命制一道四选一推理类阅读理解题。

出题材料：{prose}
难度等级（1至9）：{difficulty}
已出问题列表：{previous_questions}

一、考查目标
这道题要考查学生从文本中推出未明说含义的能力。答案不能在原文中被直接说出，也不能只是对细节的简单复述；它必须由文中的人物言行、环境细节、语气停顿、时间关系或因果暗示共同支撑。题干应引导学生听出言外之意，把握人物真实态度、事件潜在原因、情境可能走向或话语背后的限制条件。推理类型可包括推断人物意图、事件原因、关系变化、话语态度、后续可能或隐含限制，但本题只能选择一个最清晰的落点。

二、与已有题目的差异
请先核对已出问题列表。新题在推理类型、关注点、提问方式和答案落点上都要与已有题目明显不同。不要沿用相同线索，不要重复相似问法，不要把旧题只换几个词。若列表为空，则从材料中选择最有推理价值的一处或几处线索自行命题。

三、命题要求
1. 只生成一道题，四个选项，答案唯一。
2. 题干使用自然、规范的现代汉语，可询问“最可能推出”“可以推知”“暗示了什么”等，但不要直接要求学生寻找原文句子。
3. 正确选项必须能够由文中至少一处明确线索经过合理推断得出。线索可以是一个动作、一句含蓄的话、一个时间细节、一次回避、一个停顿、一种称呼或一处环境描写。
4. 正确选项不得照抄原文，也不得只是把原文词句换个说法；它应概括文中没有直接说明但合乎逻辑的含义。
5. 干扰项要与材料相关，表面上看合理，实际上缺少足够文本证据，或存在过度推断、因果颠倒、把可能说成必然、扩大范围、忽视语气限制等问题。
6. 不要依靠生活常识、专业背景或材料之外的信息才能判断答案。所有判断都应回到文本。
7. 四个选项的句式、长度和信息量要尽量接近，不要让正确项因为更具体、更温和、更完整或更像总结而显得突出。
8. 正确选项在四个选项中的位置不能固定。请让正确项自然分布在任意一项，避免形成固定模式。下方示例只展示推理线索和解释写法，其正确项位置不应被模仿为固定规则。
9. 题干、选项和解释都要使用地道中文，避免翻译腔。不得出现外文人名、外文术语、拼音或字母编号。若材料中出现外来名称，应改成符合中文阅读习惯的表达，但不得改变原文信息。
10. 题干不得泄露答案，选项不得互相矛盾到可以轻易排除，也不得出现明显绝对化词语，除非原文足以支持该绝对判断。
11. 题干若使用否定或限制条件，必须表达清楚，避免学生因句式绕口而误判；不要为了增加难度而故意制造歧义。
12. 选项内容应围绕同一推理焦点展开，避免四个选项分散到互不相关的事件上；若材料信息丰富，也应只选取一个最能体现言外之意的焦点。
13. 解释应先列出关键证据，再说明这些证据如何共同推出答案；对每个干扰项都要指出其不成立的原因，但无需逐字复述全部原文。

四、难度控制
请根据难度等级调整推理跨度与干扰强度。较低难度时，线索可相对集中，推理链条较短，正确项与文本证据的距离较近；较高难度时，线索可分散在不同句子中，需要整合语气、动作、场景和人物关系，干扰项也要更接近正确项。但无论难度高低，正确项都必须有充分文本依据，且只能有一个最佳答案。

五、完整示例
以下示例仅展示命题思路、语言风格和解释方式，不要求你使用相同场景，也不代表正确项应放在某一固定位置。请勿照抄示例中的人物、场景、语句或推理落点。

例文：周五下午，社区图书室的窗帘拉得严严实实。赵老师把一摞借阅卡按日期排好，时不时望向门口。小周抱着一箱旧书进来，额头上全是汗。赵老师轻声说：“先别拆，等周主任通知。”小周把箱子放到桌角，压低声音：“刚才在走廊遇见李会计，她说今年的活动经费已经报完了。”赵老师停顿了一下，把最上面那张借阅卡翻了过去：“那就先把书登记上，别写新购。”

问题：根据上述材料，最能合理推出哪一项？

选项：
赵老师已经知道周主任不会来通知。
小周没有参与过图书登记工作。
赵老师想避免让人误会这批旧书来自新经费。
李会计反对图书室举办活动。

正确答案：赵老师想避免让人误会这批旧书来自新经费。

解释：文中赵老师听到活动经费已经报完后，仍要求登记旧书，却特意叮嘱“别写新购”，说明她担心登记方式会让人以为这批书动用了新经费或新采购。这一含义没有直接说出，却由经费报完、压低声音、停顿和叮嘱共同支持。其他选项中，第一项缺少依据，文中只是等待通知，并不能推出不会来通知；第二项无从判断；第四项把经费报完误解为个人反对活动，线索不足。

干扰项必须与材料属于同一学科或同一语境，并围绕同一推理焦点展开。一个指向同领域真实事物的干扰项，即使文章从未提到它，也可以是好的干扰项；没有出现在文中，恰恰是它错误的原因，不要仅仅因为文章没有提到就回避某个选项。这类题的干扰项，是同一领域中文章并不支持的事实或结论。最有力的写法包括：文中从未陈述、但确实属于该领域的真实事物；文中确实提到、却被安到错误的人物、时间、地点或因果上的细节；以及超出文本证据所能支持范围的结论。绝对禁止写出结合题目也可以算作正确的干扰项。只要认真的读者能为它辩护，这道题就有了两个答案，会被整题丢弃，这是危害最大的一种错误。绝对禁止写出正确答案的同义改写，也不得与正确答案接近到学习者无法区分。不要跨到另一个学科，也不要写荒谬无意义的选项。四个选项在长度、句式和信息量上要尽量接近，不要让正确项因更具体、更温和、更完整或更像总结而暴露。

示例沿用图书室材料：题干问根据材料最能合理推出哪一项，正确答案为“赵老师想避免让人误会这批旧书来自新经费”。好的干扰项可写“周主任要求把旧书退回”，因为它同属图书室事务，又与前文等待通知相呼应，文中从未陈述，错误原因清楚，但粗心读者可能误以为通知内容如此。被否决的干扰项不可写“赵老师要求先把旧书登记上，但不要写成新购”，因为它结合题目也可以算作正确，会使答案不唯一。被否决的干扰项也不可写“赵老师担心这批旧书被误认为用新经费购买”，因为它是正确答案的同义改写，学习者无法有意义地区分。

六、输出要求
最终只输出一个 JSON 对象，不要输出任何前言、后记、标题、列表或额外说明，也不要用任何符号包裹输出。请确保该对象可解析，字段名和固定值不得改动、翻译、增删或调整顺序。答案字段必须填写正确选项的完整文字，且与对应选项文字完全一致，不得填写序号或位置。解释字段必须用中文说明正确选项的文本依据、推理过程，并简要说明其他选项为何不成立。

{{
  "question_text": "...",
  "question_type": "inference",
  "choices": ["...", "...", "...", "..."],
  "answer": "...",
  "explanation": "..."
}}$tpl$,
        $tpl$TASK-721 v3 (STAGED, inactive): adds a distractor-construction block inverted from the live test_distractor_plausibility rubric (fact family), plus the json-token repair that unbroke json_object calls on Alibaba. Body = the incumbent verbatim + one spliced block.$tpl$)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active     = EXCLUDED.is_active,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       template_text = EXCLUDED.template_text,
       description   = EXCLUDED.description,
       updated_at    = now();

-- question_inference [en] v1 -> v2  md5 ce9dc7fdc28e04dd2245eb77088491f9
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider,
   template_text, description)
VALUES ('question_inference', 2, 2, false,
        'google/gemini-3.5-flash-lite', 'openrouter',
        $tpl$You are generating an **Inference** comprehension question.

Generate exactly ONE multiple-choice question in this JSON format:
{{
  "question_text": "question text here",
  "question_type": "inference",
  "choices": ["Choice A", "Choice B", "Choice C", "Choice D"],
  "answer": "Choice A",
  "explanation": "Brief explanation why this is correct"
}}

---

**CRITICAL: AVOID DUPLICATION**
You MUST NOT create questions similar to these already generated:
{previous_questions}

**Uniqueness Requirements:**
- Make DIFFERENT types of inferences (predictions, implications, unstated connections)
- Focus on DIFFERENT aspects of the passage
- Ask about DIFFERENT implied information
- Use DIFFERENT reasoning pathways

---

**Inference Guidelines:**
- Focus on conclusions that can be drawn from implicit information in the passage
- Test ability to read between the lines and understand unstated implications
- Require logical reasoning based on passage content
- The answer is NOT explicitly stated but must be strongly supported by passage evidence
- Wrong answers should be plausible but not supported by passage clues

---

**Few-shot Example:**
Passage: "Dr. Martinez checked her watch for the third time and glanced toward the empty doorway. The presentation materials sat ready on the desk, but the chairs remained unfilled. She sighed and opened her laptop to review the slides again."

Question: "What can be inferred about Dr. Martinez's situation?"
Choices: [
  "She is waiting for attendees who are late or not coming",
  "She is preparing for a presentation tomorrow",
  "She prefers to work alone",
  "She is finished with her presentation"
]
Answer: "She is waiting for attendees who are late or not coming"
Explanation: "The repeated watch-checking, glancing at the empty doorway, and ready materials suggest she expected people who have not arrived."

---

---

**Building the three wrong choices**

Every wrong choice you write is scored 1-5 after generation, and a choice
scored 1 or 2 discards the whole question. Build to that scale:

- **Stay inside the passage's own subject.** A wrong choice that names a real
  thing from the same subject is a GOOD wrong choice *even when the passage
  never mentions it* — being absent from the text is precisely what makes it
  wrong. Never avoid an option merely because the passage does not contain it.
- **Never write a choice that is also arguably correct.** If a careful reader
  could defend it against your stated answer, the question has two answers and
  is thrown away. This is the most damaging failure mode.
- **Never write a choice that paraphrases the correct answer,** or sits so close
  to it that a learner cannot tell the two apart.
- **Never reach into a different subject** (an emotion offered as a choice in a
  passage about electrical circuits), and never write anything absurd.
- Keep all four choices comparable in length, grammatical shape and level of
  detail, so the answer is not identifiable by its form alone.

For this question type the wrong choices are same-subject facts or conclusions
the passage does not support. The strongest ones are: a real item from the
passage's domain that the text never states; a detail the passage *does* state
but attached to the wrong person, time, place or cause; or a conclusion that
reaches further than the passage's evidence licenses.

Worked example — using the passage above (Dr. Martinez, the empty doorway, the
unfilled chairs), for the question "What can be inferred about her situation?"
with the answer "She is waiting for attendees who are late or not coming":
  GOOD      — "She has come to the wrong room": entirely plausible in this
              scene, and nothing in the clues supports it — which is exactly why
              it is wrong.
  REJECTED  — "The presentation has not started yet": also a sound inference
              from the same clues, so it is arguably correct.
  REJECTED  — "She is expecting people who have not shown up": the answer
              restated.

---

**Your Task:**
- Base your question on this passage: {prose}
- Difficulty level: {difficulty}/9
- Ask about something IMPLIED but not directly stated
- The inference must be logically sound based on passage clues
- MUST be different from previous questions

Return ONLY the JSON object, no additional text.$tpl$,
        $tpl$TASK-721 v2 (STAGED, inactive): adds a distractor-construction block inverted from the live test_distractor_plausibility rubric (fact family), plus the json-token repair that unbroke json_object calls on Alibaba. Body = the incumbent verbatim + one spliced block.$tpl$)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active     = EXCLUDED.is_active,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       template_text = EXCLUDED.template_text,
       description   = EXCLUDED.description,
       updated_at    = now();

-- question_inference [ja] v1 -> v2  md5 a0f0d1acce2a9d5106a918630ea49245
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider,
   template_text, description)
VALUES ('question_inference', 3, 2, false,
        'qwen/qwen3.7-plus', 'openrouter',
        $tpl$あなたは **推論（インファレンス）** を問う読解問題を作成しています。

以下のJSON形式で、正確に1つの多肢選択問題を作成してください：
{{
  "question_text": "ここに質問文",
  "question_type": "inference",
  "choices": ["選択肢A", "選択肢B", "選択肢C", "選択肢D"],
  "answer": "選択肢A",
  "explanation": "なぜこれが正解なのかの簡単な説明"
}}

---

**重要：重複の回避**
すでに作成された以下の質問と類似した質問を作成しては**いけません**：
{previous_questions}

**独自性の要件：**
- **異なる**タイプの推論（予測、含意、明言されていないつながり）を行うこと
- 文章の**異なる**側面に焦点を当てること
- **異なる**暗黙の情報について尋ねること
- **異なる**論理的道筋を使用すること

---

**推論（インファレンス）のガイドライン：**
- 文章内の暗黙の情報から導き出せる結論に焦点を当てること
- 行間を読み、明言されていない含意を理解する能力をテストすること
- 文章の内容に基づいた論理的推論を要求すること
- 答えは明示的に述べられて**いません**が、文章の証拠によって強く支持されていなければなりません
- 不正解はもっともらしく見えるべきですが、文章の手がかりによって支持されないものであるべきです

---

**フューショットの例：**
文章：「マルティネス博士は3度目の時計を確認し、誰もいない入り口の方をちらっと見た。プレゼンテーション資料は机の上に用意されていたが、椅子は空席のままだった。彼女はため息をつき、再びスライドを見直すためにノートパソコンを開いた。」

質問：「マルティネス博士の状況について何が推測できますか？」
選択肢：[
  "彼女は遅れているか、来ない出席者を待っている",
  "彼女は明日のプレゼンテーションの準備をしている",
  "彼女は一人で働くことを好む",
  "彼女はプレゼンテーションを終えた"
]
正解："彼女は遅れているか、来ない出席者を待っている"
説明：「度重なる時計の確認、誰もいない入り口への視線、準備された資料は、彼女が来るはずの人々が到着していないことを示唆しています。」

---

誤答選択肢は、文章と同じ分野・領域に属するものだけから作ること。同じ分野に実在する事柄や概念を指すなら、文章が一度も触れていなくてもよい。文章に出てこないことこそ、誤答である理由になる。書かれていないというだけで選択肢を避けないこと。
問題に対して正解とも言える誤答を書いてはならない。注意深い読者が正解として擁護できるなら、答えが二つになり、問題全体が破棄される。最も重い失敗である。
正解の言い換えや、学習者が区別できないほど正解に近い誤答も書いてはならない。
別の分野に踏み込む選択肢、不合理・無意味な選択肢も書かないこと。例えば、電気回路の文章で感情や社交的な活動を出すなどは別の分野である。
四つの選択肢は、長さ、文の形、情報量をできるだけ揃え、形だけで正解が分からないようにすること。
この推論問題では、誤答は同じ分野に属しながら文章が支持していない事実や結論にする。特に、文章が述べていないがその分野に実在するもの、文章が述べている人物・時点・場所・因果を取り違えて結びつけた細部、文章の根拠が許す範囲を超えて踏み込んだ結論を強く推奨する。

例：マルティネス博士が時計を確認し、誰もいない入り口を見て、資料を用意したまま空席の椅子を前にため息をつく場面を使う。正解を「彼女は遅れているか、来ない出席者を待っている」とする場合。
良い誤答「彼女は明日のプレゼンテーションの準備をしている」。同じ発表場面の推測だが、文章が示す時点を取り違えている。資料を見直す描写に引かれて不注意な読者が選びやすいが、文章の証拠では支持されない誤りである。
却下される誤答「彼女は誰かが到着するのを待っている」。正解として擁護でき、答えが二つになる。
却下される誤答「彼女は遅刻している参加者を待っている」。正解の実質的な言い換えで、意味のある区別がない。

**あなたのタスク：**
- この文章に基づいて質問を作成してください：{prose}
- 難易度レベル：{difficulty}/9
- 直接述べられていないが、**暗に示されている**ことについて尋ねてください
- 推論は、文章の手がかりに基づき論理的に妥当でなければなりません
- 以前の質問とは異なっている**必要があります**

JSONオブジェクト**のみ**を返してください。追加のテキストは含めないでください。$tpl$,
        $tpl$TASK-721 v2 (STAGED, inactive): adds a distractor-construction block inverted from the live test_distractor_plausibility rubric (fact family), plus the json-token repair that unbroke json_object calls on Alibaba. Body = the incumbent verbatim + one spliced block.$tpl$)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active     = EXCLUDED.is_active,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       template_text = EXCLUDED.template_text,
       description   = EXCLUDED.description,
       updated_at    = now();

COMMIT;
