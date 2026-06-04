-- Re-anchor the test_distractor_plausibility judge prompt (lang 1 zh / 2 en / 3 ja).
--
-- Problem: the v1 scale ("1.0 = clearly wrong given the passage; 0.5 = weak;
-- 0.0 = could also be correct OR absurd") let the judge collapse "obviously the
-- wrong answer" into "weak distractor" and score good same-domain wrong options
-- 0.1-0.4. A judge-capture run (zh/en/ja x T1-T6, 2026-06-04) culled ~25 good
-- distractors for merely being the wrong answer (e.g. lever/timer for "which
-- toaster part gets hot?"). A distractor's whole job IS to be the wrong answer.
--
-- Fix: re-anchor so a normal same-domain wrong option is the DEFAULT 0.8-1.0
-- band; only also-correct (oversharp) / absurd / off-topic options fall < 0.3
-- (the hard-reject zone, _DP_HARD_REJECT_BELOW = 0.35 in question_generator).
-- Each "2" entry must be a sentence, never a number (a bare score poisons the
-- regen avoid_context). Mirrored across all three languages.
--
-- Placeholders consumed by str.format() in prompt_service: {0}=passage,
-- {1}=question, {2}=correct answer, {3}=distractors. Literal JSON braces are
-- doubled ({{ }}). Output shape unchanged: {{"1":[scores], "2":[reasons]}}.
--
-- Activation pattern mirrors migrations/explorer_ideation_per_tier_prompts.sql:
-- deactivate the old rows, insert new version=2 rows with is_active=true.
--
-- model/provider MUST be carried over from the v1 rows: prompt_service
-- safe-accepts (fails open) when the active row has no model configured, which
-- would silently bypass the judge entirely. Per-language models mirror v1:
--   lang 1 (zh) deepseek/deepseek-chat | 2 (en) google/gemini-2.5-flash-lite
--   | 3 (ja) qwen/qwen-2.5-72b-instruct ; provider openrouter.

UPDATE prompt_templates
   SET is_active = false, updated_at = now()
 WHERE task_name = 'test_distractor_plausibility';

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text, model, provider) VALUES
('test_distractor_plausibility', 1, 2, true, '干扰项合理性判断（中文，v2 重新校准）：错误本身是必需的，不是缺点。返回 {"1": [置信度,...], "2": [理由,...]}。', $tmpl$你是一位阅读理解题目质量评判员。

文章：
{0}

题目：
{1}

正确答案：
{2}

待评估干扰项：
{3}

请为每个干扰项评分（0.0 到 1.0），衡量它作为"错误但有迷惑性"选项的效果。干扰项的本职就是成为来自同一篇文章、同一领域或同一主题的错误选项——它在事实上不正确、或"显然不是答案"，这是必需的，并不是缺点。不要仅仅因为某个选项是错的、或容易被排除，就压低它的分数。

- 0.8 到 1.0（普通干扰项的默认区间）：一个属于同一文章／领域／主题的错误选项——真实存在的同类事物、合理的误读，或次要（而非主要）的观点。这是正常且良好的情况，大多数干扰项都应落在这一区间。
- 0.3 到 0.6（较弱）：与正确答案几乎相同，或基本上是其同义改写（学习者无法有意义地加以区分）。
- 低于 0.3（拒绝）仅当该选项满足以下之一：(a) 结合文章它也可以算作正确答案；或 (b) 荒谬／离题／涉及文章主题之外的事物，以致没有学习者会考虑选它。

示例。题目："烤面包机的哪个部件会变热？" 正确答案："加热元件"。
- "操作杆" -> 0.9：烤面包机真实存在的部件，显然不是会变热的那个——优质的同领域干扰项。
- "定时旋钮" -> 0.9：另一个真实部件，可能被混淆，但明显错误。
- "海洋潮汐" -> 0.1：离题，与烤面包机毫无关系——拒绝。

"2" 中的每一条都必须是解释该分数的简短句子，绝不能填数字。

仅以如下格式返回有效 JSON（每个干扰项一条，顺序与上述列表一致）：
{{"1": [0.9, 0.85, 0.1], "2": ["烤面包机真实存在的部件，显然不是会变热的那个。", "另一个真实部件，可能被混淆但明显错误。", "离题，与文章无关。"]}}$tmpl$, 'deepseek/deepseek-chat', 'openrouter'),

('test_distractor_plausibility', 2, 2, true, 'Distractor plausibility judge (English, v2 recalibrated): being the wrong answer is required, not a flaw. Returns {"1": [conf,...], "2": [reason,...]}.', $tmpl$You are a reading comprehension question quality judge.

Passage:
{0}

Question:
{1}

Correct answer:
{2}

Distractors to evaluate:
{3}

Score how well each distractor works as a WRONG-but-tempting option (0.0 to 1.0). A distractor's whole job is to be a wrong option drawn from the same passage, domain, or topic — being factually incorrect or "obviously not the answer" is REQUIRED, not a flaw. Do NOT lower a score just because the option is wrong or easy to rule out.

- 0.8 to 1.0 (DEFAULT for a normal distractor): a wrong option that belongs to the same passage / domain / topic — a real sibling item, a plausible misreading, or a secondary (not the main) idea. This is the normal, good case; most distractors should land here.
- 0.3 to 0.6 (weak): nearly identical to the correct answer, or essentially a paraphrase of it (the learner cannot meaningfully choose between them).
- below 0.3 (reject) ONLY when the option is either (a) also arguably CORRECT given the passage, or (b) absurd / off-topic / about something outside the passage's subject, so no learner would ever consider it.

Example. Question: "Which part of the toaster gets hot?" Correct answer: "the heating element".
- "the lever" -> 0.9: a real toaster part, clearly not the hot one — a good same-domain distractor.
- "the timer dial" -> 0.9: another real toaster part, plausibly confused but clearly wrong.
- "the ocean tide" -> 0.1: off-topic, nothing to do with a toaster — reject.

Each entry in "2" MUST be a short sentence explaining the score. Never put a number there.

Respond ONLY with valid JSON in exactly this format (one entry per distractor, in the same order as listed):
{{"1": [0.9, 0.85, 0.1], "2": ["A real toaster part, clearly not the hot one.", "Another real part, plausibly confused but wrong.", "Off-topic and unrelated to the passage."]}}$tmpl$, 'google/gemini-2.5-flash-lite', 'openrouter'),

('test_distractor_plausibility', 3, 2, true, '誤答妥当性判定（日本語、v2 再校正）：誤りであること自体は必須であり、欠点ではない。{"1": [確信度,...], "2": [理由,...]} を返す。', $tmpl$あなたは読解問題の品質評価員です。

文章：
{0}

問題：
{1}

正解：
{2}

評価する誤答選択肢：
{3}

各誤答選択肢について、「誤りだが引っかかりやすい」選択肢としての効果を 0.0〜1.0 で採点してください。誤答選択肢の本来の役割は、同じ文章・分野・話題から取られた「誤った選択肢」であることです。事実として誤っている、あるいは「明らかに正解ではない」ことは必須であり、欠点ではありません。単に誤っている、あるいは簡単に除外できるという理由だけで点数を下げないでください。

- 0.8〜1.0（通常の誤答選択肢の既定値）：同じ文章・分野・話題に属する誤った選択肢——実在する同種のもの、もっともらしい読み違い、または（主旨ではない）副次的な考え。これは正常で良い状態であり、ほとんどの誤答はここに収まるべきです。
- 0.3〜0.6（弱い）：正解とほぼ同一、または実質的にその言い換え（学習者が意味のある区別をできない）。
- 0.3 未満（不合格）は次のいずれかの場合のみ：(a) 文章を踏まえると正解とも言える、または (b) 不合理・話題から外れている・文章の主題の外を指しており、学習者が決して選ばないほどである。

例。問題：「トースターのどの部品が熱くなりますか？」 正解：「加熱エレメント」。
- 「レバー」 -> 0.9：トースターの実在する部品で、熱くなる部品ではないことが明らか——良い同分野の誤答。
- 「タイマーつまみ」 -> 0.9：もう一つの実在する部品で、混同されやすいが明らかに誤り。
- 「海の潮の満ち引き」 -> 0.1：話題から外れ、トースターと無関係——不合格。

「2」の各項目は、その点数を説明する短い文でなければなりません。数字を入れてはいけません。

以下の形式の有効な JSON のみで返してください（誤答の順番どおりに）：
{{"1": [0.9, 0.85, 0.1], "2": ["トースターの実在する部品で、熱くなるものではないことが明らか。", "もう一つの実在する部品で、混同されやすいが明らかに誤り。", "話題から外れており、文章と無関係。"]}}$tmpl$, 'qwen/qwen-2.5-72b-instruct', 'openrouter');
