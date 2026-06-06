-- v3 distractor-plausibility judge: replace the raw 0.0-1.0 FLOAT with a
-- 5-point LIKERT rating (lang 1 zh / 2 en / 3 ja).
--
-- Why: the v2 re-anchor (float) did NOT fix harshness. Measured offline against
-- c:\tmp\judge_labels.json (51 captured en distractors, 2026-06-05), the live
-- en judge (gemini-2.5-flash-lite) wrongly REJECTED 55% of good same-domain
-- distractors — it collapsed "absent from the passage" into "off-topic" and was
-- internally inconsistent (same option 0.80 in one Q, 0.20 in another). Root
-- cause: a small model cannot emit a calibrated, stable 0-1 float. It is far
-- more self-consistent choosing among a few anchored discrete labels.
--
-- Fix: the model now returns an integer 1-5 per distractor. Code maps it to a
-- verdict (services/test_generation/schemas.py likert_to_verdict):
--   5 / 4 -> accept    3 -> flag (weak, kept)    2 / 1 -> reject
-- (2 = off-topic / different subject, 1 = also-correct or absurd). The
-- question-abort condition in question_generator._apply_judges becomes
-- "worst distractor verdict == reject" (i.e. rating <= 2), replacing the old
-- _DP_HARD_REJECT_BELOW = 0.35 float floor.
--
-- The prompt carries: the explicit "absence from the passage is NOT off-topic"
-- clause, a precise definition of off-topic (= a DIFFERENT subject), and a
-- worked circuit example covering the observed failures (switch/resistor -> 5,
-- an emotion -> 2, a synonym-of-answer -> 3, an also-correct option -> 1).
--
-- Placeholders consumed by str.format() in the judge: {0}=passage,
-- {1}=question, {2}=correct answer, {3}=numbered distractors, {4}=question type,
-- {5}=subject/domain keywords. Literal JSON braces are doubled ({{ }}). Output
-- shape: {{"1":[likert ints 1-5], "2":[one-sentence reasons]}}.
--
-- Activation: deactivate all existing rows, insert version=3 with
-- is_active=true. model/provider carried over from v1/v2 (a NULL model makes
-- prompt_service safe-accept / silently bypass the judge). Models unchanged so
-- this isolates the Likert effect from any future judge-model A/B:
--   lang 1 (zh) deepseek/deepseek-chat | 2 (en) google/gemini-2.5-flash-lite
--   | 3 (ja) qwen/qwen-2.5-72b-instruct ; provider openrouter.

UPDATE prompt_templates
   SET is_active = false, updated_at = now()
 WHERE task_name = 'test_distractor_plausibility';

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text, model, provider) VALUES
('test_distractor_plausibility', 1, 3, true, '干扰项合理性判断（中文，v3 李克特 5 分量表）：错误本身是必需的，不是缺点；缺席≠离题。返回 {"1": [1-5 评分,...], "2": [理由,...]}。', $tmpl$你是一位阅读理解题目质量评判员。

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

关于理由字段：每一条都必须是解释该评分的简短句子。绝不要在理由字段里填数字、分数或单纯的标签。

仅以如下格式返回有效 JSON——每个干扰项一条，顺序与上面的编号列表一致：
{{"1": [5, 5, 2], "2": ["真实的同领域部件，明显不是答案但有迷惑性。", "另一个真实部件，可能被混淆。", "属于不同学科——离题。"]}}$tmpl$, 'deepseek/deepseek-chat', 'openrouter'),

('test_distractor_plausibility', 2, 3, true, 'Distractor plausibility judge (English, v3 5-point Likert): being wrong is required; absence from the passage is NOT off-topic. Returns {"1": [1-5 ratings,...], "2": [reasons,...]}.', $tmpl$You are a reading-comprehension question quality judge.

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
A distractor's entire purpose is to be WRONG. Being factually incorrect, "obviously not the answer", or NOT MENTIONED anywhere in the passage is REQUIRED — it is what makes something a distractor, not a flaw. A distractor that names a real thing from the SAME SUBJECT as the passage is a GOOD distractor even when that exact thing never appears in the passage; its absence from the text is precisely WHY it is the wrong choice. Never mark a distractor down for being absent from the passage, for being wrong, or for being easy to rule out.

"Off-topic" means the option belongs to a COMPLETELY DIFFERENT subject than the passage — for example, an emotion or a social activity offered as a choice in a passage about electrical circuits. "Off-topic" does NOT mean "a same-subject item that the passage happens not to mention."

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

For the reason field: each entry MUST be one short sentence explaining the rating. NEVER put a number, score, or bare label in the reason field.

Respond with ONLY valid JSON in exactly this shape — one entry per distractor, in the same order as the numbered list above:
{{"1": [5, 5, 2], "2": ["A real same-domain part, clearly not the answer but tempting.", "Another real component, plausibly confused.", "Belongs to a different subject — off-topic."]}}$tmpl$, 'google/gemini-2.5-flash-lite', 'openrouter'),

('test_distractor_plausibility', 3, 3, true, '誤答妥当性判定（日本語、v3 5段階リッカート）：誤りであること自体は必須であり、文章にないこと＝話題外ではない。{"1": [1-5 の評価,...], "2": [理由,...]} を返す。', $tmpl$あなたは読解問題の品質評価員です。

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

理由の欄について：各項目は、その評価を説明する短い一文でなければなりません。理由の欄に数字・点数・単なるラベルを入れては絶対にいけません。

以下の形式の有効な JSON のみで返してください——誤答ごとに一つ、上の番号順に：
{{"1": [5, 5, 2], "2": ["実在する同分野の部品で、答えではないが引っかかりやすい。", "もう一つの実在する部品で、混同されやすい。", "別の分野に属する——話題外。"]}}$tmpl$, 'qwen/qwen-2.5-72b-instruct', 'openrouter');
