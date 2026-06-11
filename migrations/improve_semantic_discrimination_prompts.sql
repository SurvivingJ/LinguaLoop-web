-- ============================================================================
-- Constrain semantic_discrimination distractor generation
-- Date: 2026-06-09
--
-- Source: wiki/evaluations/exercise-pipeline-eval-2026-06-09.md (HIGH #4).
--
-- The old prompts produced two failure modes:
--   * Gibberish "wrong" sentences for concrete words (trivially eliminable).
--   * "Wrong" sentences that are actually VALID English in another sense of a
--     polysemous word -> two correct answers / keyed-answer bug.
--
-- The new prompts require each wrong sentence to be (a) a fluent, realistic
-- misuse (not nonsense) and (b) genuinely wrong in EVERY sense of the word,
-- and add a per-sentence `reason` so the ladder sentence-validity judge gets a
-- labeled reason to rule against. Placeholders unchanged:
--   {word} {definition} {complexity_tier} {example_sentence}
--
-- Idempotent: straight UPDATE by id; re-running restores the same text.
-- ============================================================================

-- English (id 70)
UPDATE public.prompt_templates SET template_text = E'Word: {word}\nDefinition: {definition}\nLevel: {complexity_tier}\nExample context: {example_sentence}\n\nGenerate 4 sentences using "{word}":\n- 1 correct, natural usage of THIS sense (the definition above)\n- 3 plausible-but-wrong usages\n\nRules for the 3 wrong sentences (critical):\n- Each must be a fluent, realistic sentence a learner could mistakenly write — NOT gibberish or nonsense. Put "{word}" in a grammatical slot or context it does not belong in for this sense (wrong register, wrong collocation, or wrong context).\n- Each wrong sentence MUST be genuinely incorrect for "{word}" in EVERY sense of the word. Do NOT produce a sentence that is valid English under a different meaning of "{word}" — that would create a second correct answer.\n- Keep all four sentences at a similar length and {complexity_tier} level.\n\nReturn JSON:\n{{"sentences": [{{"text": "...", "is_correct": true}}, {{"text": "...", "is_correct": false, "reason": "why this misuse is wrong"}}, {{"text": "...", "is_correct": false, "reason": "..."}}, {{"text": "...", "is_correct": false, "reason": "..."}}], "explanation": "Why the correct sentence is correct and the others are wrong."}}\n\nPut the correct sentence first.',
    updated_at = now()
WHERE id = 70;

-- Chinese (id 44)
UPDATE public.prompt_templates SET template_text = E'词语：{word}\n定义：{definition}\n级别：{complexity_tier}\n示例语境：{example_sentence}\n\n生成 4 个使用"{word}"的句子：\n- 1 个正确、自然地体现上述定义（该义项）的用法\n- 3 个貌似合理但错误的用法\n\n关于这 3 个错误句子的规则（重要）：\n- 每个句子都必须是流畅、真实、学习者可能写错的句子，绝不能是无意义的乱句。请把"{word}"放在该义项不适用的语法或语境位置（语域错误、搭配错误或语境错误）。\n- 每个错误句子对"{word}"的所有义项都必须是真正错误的。不要生成在该词另一义项下其实成立的句子——那会产生第二个正确答案。\n- 四个句子的长度和 {complexity_tier} 级别应保持相近。\n\n返回 JSON：\n{{"sentences": [{{"text": "...", "is_correct": true}}, {{"text": "...", "is_correct": false, "reason": "该误用为何错误"}}, {{"text": "...", "is_correct": false, "reason": "..."}}, {{"text": "...", "is_correct": false, "reason": "..."}}], "explanation": "..."}}\n\n将正确句子放在首位。',
    updated_at = now()
WHERE id = 44;

-- Japanese (id 71)
UPDATE public.prompt_templates SET template_text = E'語彙：{word}\n定義：{definition}\nレベル：{complexity_tier}\n例文の文脈：{example_sentence}\n\n「{word}」を使った4つの文を生成してください：\n- 上記の定義（この語義）を正しく自然に用いた文を1つ\n- もっともらしいが間違った用法を3つ\n\n3つの間違った文に関する規則（重要）：\n- 各文は、学習者が誤って書きうる自然で流暢な文でなければならず、無意味な文であってはなりません。「{word}」をこの語義では成立しない文法・文脈の位置に置いてください（語域の誤り、コロケーションの誤り、文脈の誤り）。\n- 各間違い文は「{word}」のいかなる語義においても本当に誤りでなければなりません。別の語義では成立してしまう文を作らないでください——第2の正解が生じます。\n- 4つの文は長さと {complexity_tier} レベルを揃えてください。\n\nJSONで返してください：\n{{"sentences": [{{"text": "...", "is_correct": true}}, {{"text": "...", "is_correct": false, "reason": "この誤用が間違っている理由"}}, {{"text": "...", "is_correct": false, "reason": "..."}}, {{"text": "...", "is_correct": false, "reason": "..."}}], "explanation": "..."}}\n\n正しい文を最初に置いてください。',
    updated_at = now()
WHERE id = 71;
