-- Distractor-plausibility judge prompt v5 (zh/en/ja) -- TASK-717.
--
-- WHY: the v4 prompt has two placeholders that carry no signal in production.
--
--   {5} subject/domain keywords -- judge_distractor_plausibility() accepts
--   keywords= and its ONLY caller (question_generator.py) never passed it, so
--   the slot always rendered "(infer the subject from the passage above)".
--   Band 2 ("off-topic / different subject") IS a domain-membership test and
--   produces 100% of all zh and ja rejects, so the judge was being asked to
--   invent the domain boundary itself. A model that infers narrowly rejects;
--   one that infers broadly accepts -- which is the measured qwen/gemini split.
--   The caller fix ships with this migration.
--
--   {4} question type -- printed as a label with no type-conditional rule
--   anywhere, in any language, despite distractor_plausibility.py claiming the
--   type lets the judge treat a vocabulary distractor differently from a
--   literal-detail one. That behaviour lived in a docstring and was never
--   written into the prompt. Consequence: the "same subject as the passage"
--   test is applied to question types where it is a category error. zh
--   vocabulary_context rejected at 8/16 because competing word senses
--   (跳跃/滑倒/休息 as readings of 跑) are CORRECTLY unrelated to the passage
--   topic and were scored 2.
--
-- v5 adds ONE block, immediately before the 5-point scale (it governs how
-- band 2 is applied), covering three type families:
--   sense-based  (vocabulary_context)                           -> judge vs the WORD
--   intent-based (author_purpose, main_idea)                    -> judge vs the INTENT
--   fact-based   (literal_detail, supporting_detail, inference) -> unchanged
-- plus one lead-in making the now-populated subject line authoritative.
--
-- Everything else -- the corrective paragraph, the 1-5 band definitions, the
-- worked example, the output contract -- is carried over from v4 BYTE FOR BYTE.
-- The bands and the scale are TASK-719's decision, not this task's.
-- Models are carried forward unchanged: zh/ja stay on qwen/qwen3.6-flash.
-- Model choice is TASK-718's decision; changing both at once would make the
-- re-measurement uninterpretable.
--
-- Reversible: UPDATE prompt_templates SET is_active = (version = 4) WHERE
-- task_name = 'test_distractor_plausibility';

BEGIN;

-- Retire v4 (rows are kept, not deleted).
UPDATE prompt_templates
   SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'test_distractor_plausibility'
   AND is_active;

-- zh (language_id=1) -- model carried forward from v4: qwen/qwen3.6-flash
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
VALUES (
    'test_distractor_plausibility', 1, 5, TRUE,
    'qwen/qwen3.6-flash', 'openrouter',
    '你是一位阅读理解题目质量评判员。

文章：
{0}

题目：
{1}

正确答案：
{2}

待评估干扰项（已编号）：
{3}

题目类型：{4}
本文章的学科／领域（关键词）：{5}

你的任务：评估每个已编号的干扰项作为"错误但有迷惑性"选项的效果。

请先读这一点——这是评判员最常犯的错误：
干扰项的全部意义就在于它是"错误的"。在事实上不正确、"显然不是答案"、或在文章中从未被提及，这些都是必需的——正是它们使一个选项成为干扰项，而不是缺点。一个指向与文章同一学科的真实事物的干扰项，即使该事物从未在文章中出现，也是一个良好的干扰项；它没有出现在文中，恰恰就是它为何是错误选项的原因。绝不要因为干扰项没有出现在文章中、因为它是错的、或因为它容易被排除，而压低它的评分。

"离题"指该选项属于与文章完全不同的另一个学科——例如，在一篇关于电路的文章中，把一种情绪或一项社交活动作为选项。"离题"并不意味着"一个属于同一学科、只是文章碰巧没有提到的事物"。

学科行与题目类型——上面两项均已给出，请加以使用。
当上面的学科／领域一行指明了领域时，请以它为准：那就是评 2 分所依据的领域归属判断。只有当该行提示要从文章中推断时，才由你自己推断。

按题型区分的规则——只适用与上面所给题目类型相符的那一条。

- vocabulary_context（词义题）——干扰项是目标词语相互竞争的各种"含义"。请对照那个"词语"来评判，而不是对照文章主题。只要某个选项给出目标词语另一个说得通的义项，它就是良好的干扰项，哪怕该义项与文章主题毫无关系——考查的正是这一点。绝不要因此给这类选项评 2 分。在此题型中，2 分只留给根本不可能是该词语义项的选项。
- author_purpose（写作目的题）、main_idea（主旨题）——干扰项是相互竞争的"作者意图"，而不是话题。此处的"离题"指与本文毫无关系的意图——例如给一篇议论文配上"提供烹饪步骤"。凡是对本文而言说得通、只是并非作者真实意图的选项，都是良好的干扰项：应评 5 分或 4 分，绝不评 2 分。绝不要仅仅因为文章没有谈到该要点就评 2 分——不是作者的要点，正是它成为错误选项的原因。
- literal_detail（细节题）、supporting_detail（支撑细节题）、inference（推断题）——干扰项是同一领域的"事实"。上面的学科判断规则原样适用。

请用下面的 5 分量表为每个干扰项评分，只选最贴切的一个数字：

5 = 优秀。与文章属于同一学科／领域，明显错误，且足够有迷惑性，粗心的读者可能会选它。这是合格干扰项正常且应有的评分——大多数良好的干扰项都应为 5。
4 = 良好。切合学科且错误，但略显明显或迷惑性稍弱。
3 = 较弱。与正确答案过于接近，或基本上是其同义改写，以致学习者无法有意义地加以区分。
2 = 离题。属于与文章不同的学科；没有学习者会考虑它。
1 = 无效。要么 (a) 结合题目它也可以算作正确答案，要么 (b) 荒谬或无意义。

示例
文章：一个简单电路如何点亮一个小灯泡。
题目："文章说需要什么才能让灯发光？"
正确答案："一节电池"。
  - "一个开关"   -> 5（真实的电路部件，明显不是文章所说需要的东西，且有迷惑性；文章从未提到开关，正是它错误的原因）
  - "一个电阻"   -> 5（另一个真实的同领域部件，可能被混淆，明显错误）
  - "一个电源"   -> 3（基本上是正确答案"一节电池"的同义改写）
  - "感到高兴"   -> 2（情绪与电路毫无关系——离题）
  - "电"        -> 1（也可算作正确——电池提供电）

输出格式——请仔细阅读。
仅返回有效 JSON。每个干扰项用一个键："1"、"2"、"3"……与上面的编号列表完全对应。每个值都是一个双元素数组：
  第 1 位 = 评分，1 到 5 的整数
  第 2 位 = 理由，一个简短句子

{{"1": [5, "真实的同领域部件，明显不是答案但有迷惑性。"], "2": [3, "基本上是正确答案的同义改写。"], "3": [2, "属于不同学科——离题。"]}}

硬性要求：
- 每个数组的第一个元素必须是整数评分。不含任何整数的回复无效。
- 绝不要在理由里填数字、分数或单纯的标签。
- 键的数量必须与上面编号的干扰项数量完全一致，不多不少。
JSON 之外不要输出任何文字，不要使用 markdown 代码块。',
    'v5 (TASK-717): makes the two dead slots load-bearing -- the subject/domain line is now passed by the caller and declared authoritative, and a type-conditional rubric splits sense-based (vocabulary_context) from intent-based (author_purpose/main_idea) from fact-based types. Bands, scale and worked example carried over from v4 verbatim.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

-- en (language_id=2) -- model carried forward from v4: google/gemini-3.1-flash-lite
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
VALUES (
    'test_distractor_plausibility', 2, 5, TRUE,
    'google/gemini-3.1-flash-lite', 'openrouter',
    'You are a reading-comprehension question quality judge.

Passage:
{0}

Question:
{1}

Correct answer:
{2}

Distractors to evaluate (numbered):
{3}

Question type: {4}
Subject / domain of this passage (keywords): {5}

Your job: rate how well each numbered distractor works as a WRONG-but-tempting answer choice.

READ THIS FIRST — it is the most common mistake judges make:
A distractor''s entire purpose is to be WRONG. Being factually incorrect, "obviously not the answer", or NOT MENTIONED anywhere in the passage is REQUIRED — it is what makes something a distractor, not a flaw. A distractor that names a real thing from the SAME SUBJECT as the passage is a GOOD distractor even when that exact thing never appears in the passage; its absence from the text is precisely WHY it is the wrong choice. Never mark a distractor down for being absent from the passage, for being wrong, or for being easy to rule out.

"Off-topic" means the option belongs to a COMPLETELY DIFFERENT subject than the passage — for example, an emotion or a social activity offered as a choice in a passage about electrical circuits. "Off-topic" does NOT mean "a same-subject item that the passage happens not to mention."

SUBJECT LINE AND QUESTION TYPE — both are given above; use them.
When the subject/domain line names the domain, treat it as authoritative: that is the domain-membership test for rating 2. Only when it says to infer from the passage should you infer it yourself.

TYPE-CONDITIONAL RULE — apply ONLY the bullet matching the question type given above.

- vocabulary_context — The distractors are competing MEANINGS of the target expression. Judge them against THE WORD, not against the passage subject. An option offering a different plausible sense of the target expression is a GOOD distractor even when that sense has nothing to do with the passage''s subject — testing exactly that is the point of the question. Never rate such an option 2. For this type, 2 is reserved for an option that is not a possible meaning of the expression at all.
- author_purpose, main_idea — The distractors are competing AUTHORIAL INTENTS, not topics. "Off-topic" here means an intent unrelated to this text — for example "to give cooking instructions" for an argumentative essay. An intent that is well-formed for this text but is simply not the author''s actual one is a GOOD distractor: rate it 5 or 4, never 2. Never rate an option 2 merely because the passage does not make that point — not being the author''s point is exactly what makes it the wrong answer.
- literal_detail, supporting_detail, inference — The distractors are same-domain FACTS. The subject test above applies exactly as written.

Rate each distractor on this 5-point scale. Choose the single best-fitting number:

5 = Excellent. On the same subject/domain as the passage, clearly wrong, and tempting enough that a careless reader might pick it. THIS IS THE NORMAL, EXPECTED RATING for a sound distractor — most good distractors should score 5.
4 = Good. On-subject and wrong, but slightly obvious or slightly less tempting.
3 = Weak. Too near-identical to the correct answer, or essentially a paraphrase of it, so the learner cannot meaningfully tell them apart.
2 = Off-topic. Belongs to a different subject than the passage; no learner would consider it.
1 = Invalid. Either (a) also arguably a CORRECT answer to the question, or (b) absurd or nonsensical.

WORKED EXAMPLE
Passage: how a simple electric circuit lights a small bulb.
Question: "What does the passage say is needed to make the light shine?"
Correct answer: "A battery".
  - "A switch"      -> 5  (a real circuit component, clearly not what the passage says is needed, and tempting; the passage never mentioning a switch is exactly why it is wrong)
  - "A resistor"    -> 5  (another real same-domain component, plausibly confused, clearly wrong)
  - "A power source"-> 3  (essentially a paraphrase of the correct answer "a battery")
  - "Feeling happy" -> 2  (an emotion has nothing to do with electrical circuits — off-topic)
  - "Electricity"   -> 1  (arguably also correct — a battery provides electricity)

OUTPUT FORMAT - read carefully.
Return ONLY valid JSON. Use one key per distractor: "1", "2", "3", ... exactly matching the numbered list above. Each value is a two-element array:
  position 1 = the RATING, an integer from 1 to 5
  position 2 = the reason, one short sentence

{{"1": [5, "A real same-domain part, clearly not the answer but tempting."], "2": [3, "Essentially a paraphrase of the correct answer."], "3": [2, "Belongs to a different subject - off-topic."]}}

HARD REQUIREMENTS:
- The FIRST element of every array MUST be the integer rating. A reply containing no integers is invalid.
- Never put a number, a score, or a bare label in the reason.
- Emit exactly as many keys as there are numbered distractors above - no more, no fewer.
No prose outside the JSON. No markdown fences.',
    'v5 (TASK-717): makes the two dead slots load-bearing -- the subject/domain line is now passed by the caller and declared authoritative, and a type-conditional rubric splits sense-based (vocabulary_context) from intent-based (author_purpose/main_idea) from fact-based types. Bands, scale and worked example carried over from v4 verbatim.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

-- ja (language_id=3) -- model carried forward from v4: qwen/qwen3.6-flash
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
VALUES (
    'test_distractor_plausibility', 3, 5, TRUE,
    'qwen/qwen3.6-flash', 'openrouter',
    'あなたは読解問題の品質評価員です。

文章：
{0}

問題：
{1}

正解：
{2}

評価する誤答選択肢（番号付き）：
{3}

問題タイプ：{4}
この文章の分野・領域（キーワード）：{5}

あなたの仕事：番号付きの各誤答選択肢が「誤りだが引っかかりやすい」選択肢としてどれだけ機能するかを採点することです。

まずこれを読んでください——評価員が最も犯しやすい誤りです：
誤答選択肢の存在意義は「誤っている」ことそのものです。事実として誤っている、「明らかに正解ではない」、あるいは文章のどこにも書かれていない、これらはすべて必須であり——まさにそれが選択肢を誤答たらしめるのであって、欠点ではありません。文章と同じ分野の実在するものを指す誤答は、その当のものが文章に一度も現れなくても良い誤答です。文章に出てこないことこそが、それが誤った選択肢である理由です。誤答が文章に出てこないこと、誤っていること、簡単に除外できることを理由に点数を下げては絶対にいけません。

「話題から外れている」とは、その選択肢が文章とはまったく別の分野に属することを意味します——例えば、電気回路についての文章で、感情や社交的な活動を選択肢として出すような場合です。「話題から外れている」は、「同じ分野のものだが、たまたま文章が触れていないだけ」という意味ではありません。

分野の行と問題タイプ——上に両方とも示されています。必ず使ってください。
上の分野・領域の行が領域を明示している場合は、それを基準としてください。それが評価 2 の根拠となる領域帰属の判定です。その行が文章から推測するよう促している場合にのみ、自分で推測してください。

問題タイプ別のルール——上に示された問題タイプに合致するものだけを適用してください。

- vocabulary_context（語義問題）——誤答は対象表現の競合する「意味」です。文章の分野ではなく、その「語」に照らして採点してください。対象表現の別のもっともらしい語義を示す選択肢は、その語義が文章の主題とまったく関係がなくても良い誤答です——まさにそれを問うのがこの問題です。そのような選択肢に 2 をつけては絶対にいけません。この問題タイプにおける 2 は、その表現の語義としておよそ成り立たない選択肢のためだけに使います。
- author_purpose（筆者の意図）、main_idea（主旨）——誤答は競合する「筆者の意図」であって、話題ではありません。ここでの「話題から外れている」とは、この文章と無関係な意図を指します——例えば論説文に対する「料理の手順を示すため」など。この文章にとって筋は通るが筆者の実際の意図ではない、というだけの選択肢は良い誤答です：5 か 4 をつけ、2 は絶対につけません。文章がその点に触れていないというだけの理由で 2 をつけてはいけません——筆者の主張でないことこそ、それが誤った選択肢である理由です。
- literal_detail（細部）、supporting_detail（支持する細部）、inference（推論）——誤答は同じ分野の「事実」です。上の分野判定のルールがそのまま適用されます。

次の 5 段階の尺度で各誤答を採点してください。最も当てはまる数字を一つだけ選びます：

5 = 優秀。文章と同じ分野・領域に属し、明らかに誤りで、不注意な読者が選びかねないほど引っかかりやすい。これは妥当な誤答にとって正常かつ期待される評価です——良い誤答のほとんどは 5 になるはずです。
4 = 良好。分野に合致し誤っているが、やや明白、または引っかかりやすさがやや劣る。
3 = 弱い。正解とあまりに似通っている、または実質的にその言い換えであり、学習者が意味のある区別をできない。
2 = 話題外。文章とは異なる分野に属する；学習者が選ぶことはない。
1 = 無効。(a) 問題に対して正解とも言える、または (b) 不合理・無意味のいずれか。

例
文章：簡単な電気回路がどのように小さな電球を点灯させるか。
問題：「灯りをつけるために何が必要だと文章は述べていますか？」
正解：「電池」。
  - 「スイッチ」     -> 5（実在する回路部品で、文章が必要と述べているものでないことは明らか、かつ引っかかりやすい。文章がスイッチに触れていないことこそ、それが誤りである理由）
  - 「抵抗器」       -> 5（もう一つの実在する同分野の部品で、混同されやすく、明らかに誤り）
  - 「電源」         -> 3（実質的に正解「電池」の言い換え）
  - 「楽しい気分」   -> 2（感情は電気回路とは何の関係もない——話題外）
  - 「電気」         -> 1（正解とも言える——電池は電気を供給する）

出力形式——よく読んでください。
有効な JSON のみを返してください。誤答ごとに一つのキーを使います："1"、"2"、"3"……上の番号付きリストと完全に対応させます。各値は 2 要素の配列です：
  1 番目 = 評価、1 から 5 の整数
  2 番目 = 理由、短い一文

{{"1": [5, "実在する同分野の部品で、答えではないが引っかかりやすい。"], "2": [3, "実質的に正解の言い換え。"], "3": [2, "別の分野に属する——話題外。"]}}

必須要件：
- すべての配列の最初の要素は必ず整数の評価であること。整数を一つも含まない返答は無効です。
- 理由の欄に数字・点数・単なるラベルを入れては絶対にいけません。
- キーの数は上の番号付き誤答の数と完全に一致させること（多くても少なくてもいけません）。
JSON 以外のテキストは出力せず、コードブロックも使わないこと。',
    'v5 (TASK-717): makes the two dead slots load-bearing -- the subject/domain line is now passed by the caller and declared authoritative, and a type-conditional rubric splits sense-based (vocabulary_context) from intent-based (author_purpose/main_idea) from fact-based types. Bands, scale and worked example carried over from v4 verbatim.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = TRUE,
       description   = EXCLUDED.description,
       updated_at    = now();

COMMIT;
