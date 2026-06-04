-- Migration: two-level sense prompts (numeric-key, integer POS, JSON-mode) + new ja
--
-- Rewrites the sense pipeline prompts to the house numeric-key convention,
-- collapsing the old 3-call flow (selection -> generation -> validation) into:
--   * vocab_definition_generation : ONE call emitting both definition levels
--       ("1"=simple/child-register, "2"=standard), "3"=new example sentence,
--       "4"=POS integer code (language-neutral), "5"=self-confidence (replaces
--       the separate validation call), "6"=should_skip.
--   * vocab_sense_selection : numeric-key match-or-create for polysemy.
-- vocab_validation is retired (confidence subsumes it).
--
-- Adds ja (language_id=3) rows, previously absent (senses fell back to the
-- English template). Placeholders are filled by SenseGenerator via str.format:
--   generation -> {lemma} {sentence} {simple_register}
--   selection  -> {lemma} {sentence} {definitions_list}
-- Literal JSON braces are doubled ({{ }}) so str.format leaves them intact.

-- ---------------------------------------------------------------------------
-- vocab_definition_generation
-- ---------------------------------------------------------------------------

UPDATE prompt_templates SET version = 2, model = NULL, provider = NULL,
  template_text = $T$你是为中文学习者编写词典的编纂者。
严格要求：除阿拉伯数字外，所有文字只能用简体中文（禁止繁体、英文、拼音）。只输出一个 JSON 对象，不要解释，不要思考过程。
词语：{lemma}
例句：{sentence}
根据该词在例句中的意思（若无例句则取最常用义），输出 JSON（键为数字字符串）：
"1"=极简释义。读者为低龄儿童，写作语域参照：{simple_register}。用最基础的词，一句话讲清一个意思。
"2"=标准学习者释义。
"3"=一个新的中文例句，必须与上面的例句不同。
"4"=词性代码（整数）：1名词 2动词 3形容词 4副词 5代词 6介词 7连词 8助词 9量词 10成语 11数词 0其他。
"5"=置信度（0到1之间的小数）。
"6"=是否跳过（布尔）：仅当该词是专有名词、数字、符号或标点时为 true；介词、助词等功能词（如"把""的"）是正常词语，应为 false。
只输出：{{"1":"","2":"","3":"","4":0,"5":0.0,"6":false}}$T$
WHERE task_name = 'vocab_definition_generation' AND language_id = 1;

UPDATE prompt_templates SET version = 2, model = NULL, provider = NULL,
  template_text = $T$You are a lexicographer writing a dictionary for English learners.
Strict: every value must be in English. Output exactly one JSON object, no explanation, no reasoning.
Word: {lemma}
Example sentence: {sentence}
Based on the word's meaning in the sentence (or its most common meaning if no sentence is given), output JSON (keys are numeric strings):
"1"=A very simple definition. The reader is a young child; register guide: {simple_register}. Use the most basic words, one idea in one sentence.
"2"=A standard learner definition.
"3"=A new English example sentence; it must differ from the sentence above.
"4"=Part-of-speech code (integer): 1 noun 2 verb 3 adjective 4 adverb 5 pronoun 6 preposition 7 conjunction 8 determiner 9 interjection 10 phrase 11 numeral 0 other.
"5"=Confidence (decimal between 0 and 1).
"6"=Should-skip (boolean): true ONLY for proper nouns, numbers, symbols or punctuation; function words (the, of, to) are normal words and must be false.
Output only: {{"1":"","2":"","3":"","4":0,"5":0.0,"6":false}}$T$
WHERE task_name = 'vocab_definition_generation' AND language_id = 2;

INSERT INTO prompt_templates (task_name, language_id, template_text, version, is_active, description)
VALUES ('vocab_definition_generation', 3, $T$あなたは日本語学習者向けの辞書編集者です。
厳守：アラビア数字以外、すべての文字は日本語のみ（英語・ローマ字禁止）。JSON オブジェクトを1つだけ出力し、説明や思考過程は書かない。
語：{lemma}
例文：{sentence}
この文での意味（例文が無ければ最も一般的な意味）に基づき、JSON を出力（キーは数字の文字列）：
"1"=やさしい語釈。読者は幼い子ども、文体の目安：{simple_register}。一番やさしい言葉で、一文で一つの意味を説明する。
"2"=標準的な学習者向け語釈。
"3"=新しい日本語の例文。上の例文とは必ず異なるもの。
"4"=品詞コード（整数）：1名詞 2動詞 3形容詞 4副詞 5代名詞 6助詞 7接続詞 8助動詞 9連体詞 10慣用句 11数詞 0その他。
"5"=確信度（0〜1の小数）。
"6"=スキップすべきか（真偽）：固有名詞・数字・記号・句読点のときだけ true；助詞などの機能語（「が」「を」）は正常な語なので false。
出力のみ：{{"1":"","2":"","3":"","4":0,"5":0.0,"6":false}}$T$,
1, true, 'Two-level sense generation (numeric keys, integer POS, JSON mode)');

-- ---------------------------------------------------------------------------
-- vocab_sense_selection
-- ---------------------------------------------------------------------------

UPDATE prompt_templates SET version = 2, model = NULL, provider = NULL,
  template_text = $T$你是中文词义匹配助手。严格要求：所有文字只能用简体中文，禁止英文。只输出一个 JSON 对象。
词语：{lemma}
例句：{sentence}
已有释义：
{definitions_list}
判断例句中该词的意思是否与上述某条释义一致。输出 JSON：
"1"=匹配的释义编号（整数）；若都不匹配则为 0。
只输出：{{"1":0}}$T$
WHERE task_name = 'vocab_sense_selection' AND language_id = 1;

UPDATE prompt_templates SET version = 2, model = NULL, provider = NULL,
  template_text = $T$You match an English word's meaning to an existing definition. Strict: English only. Output exactly one JSON object.
Word: {lemma}
Example sentence: {sentence}
Existing definitions:
{definitions_list}
Decide whether the word's meaning in the sentence matches one of the definitions above. Output JSON:
"1"=the matching definition number (integer); 0 if none match.
Output only: {{"1":0}}$T$
WHERE task_name = 'vocab_sense_selection' AND language_id = 2;

INSERT INTO prompt_templates (task_name, language_id, template_text, version, is_active, description)
VALUES ('vocab_sense_selection', 3, $T$あなたは日本語の語義マッチング補助です。厳守：すべて日本語のみ、英語禁止。JSON を1つだけ出力。
語：{lemma}
例文：{sentence}
既存の語釈：
{definitions_list}
例文中のこの語の意味が上の語釈のいずれかと一致するか判定。JSON を出力：
"1"=一致する語釈の番号（整数）；どれも合わなければ 0。
出力のみ：{{"1":0}}$T$,
1, true, 'Two-level sense selection (numeric keys)');

-- ---------------------------------------------------------------------------
-- vocab_validation — retired (self-confidence from generation replaces it)
-- ---------------------------------------------------------------------------

UPDATE prompt_templates SET is_active = false
WHERE task_name = 'vocab_validation' AND language_id IN (1, 2);
