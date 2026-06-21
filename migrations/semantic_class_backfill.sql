-- TASK-507: semantic_class LLM backfill groundwork
-- (Exercise Generation v2, Phase 0)
--
-- Two parts, both idempotent:
--   1. dim_vocabulary.semantic_class_confidence — records the classifier's
--      per-lemma certainty (0..1). dim_vocabulary.semantic_class itself already
--      exists (TASK-502) with a 6-value CHECK; this column lets us "record
--      gen_confidence" and flag low-confidence rows (those defaulted to
--      'abstract') for later human review:
--          SELECT * FROM dim_vocabulary
--          WHERE semantic_class = 'abstract' AND semantic_class_confidence < 0.6;
--   2. prompt_templates seed rows for task_name='semantic_class_classification',
--      one PER LANGUAGE (zh=1, en=2, ja=3) — the templates are now
--      language-SPECIFIC, not language-agnostic.
--
-- PROMPTING CONVENTION (revised 2026-06-18): for a target-language item the model
-- must only ever read/emit target-language text or numeric indices — never English
-- class words. So each language's template presents the six classes with a
-- TARGET-LANGUAGE legend bound to a NUMBER, and the model returns the NUMBER only.
-- The English enum token is produced solely by the Python mapping at write time
-- (the dim_vocabulary.semantic_class CHECK requires the English token):
--     1=concrete  2=abstract  3=action  4=property  5=function  6=proper
-- Output schema the model returns: {"<id>": [<class 1-6>, <confidence 0..1>]}.
-- The {batch} placeholder is filled by scripts/backfill_semantic_class.py.
--
-- Idempotent re-seed: DELETE then INSERT the canonical rows (no unique constraint
-- exists on (task_name,language_id) so ON CONFLICT is unavailable; the script
-- resolves templates by task_name + language_id, never by id).

ALTER TABLE dim_vocabulary
    ADD COLUMN IF NOT EXISTS semantic_class_confidence real;

COMMENT ON COLUMN dim_vocabulary.semantic_class_confidence IS
    'TASK-507: classifier certainty 0..1 for semantic_class. Rows with class '
    '''abstract'' and confidence < 0.6 were defaulted (low-confidence) and are '
    'flagged for human review.';

DELETE FROM prompt_templates WHERE task_name = 'semantic_class_classification';

-- English (language_id = 2)
INSERT INTO prompt_templates (task_name, template_text, version, is_active, description, language_id, model, provider)
VALUES (
    'semantic_class_classification',
    $tmpl$You are a linguistic classifier for the LinguaLoop vocabulary system. Classify each word into EXACTLY ONE of six semantic classes by its core meaning, part of speech, and definition.

Classes (use the NUMBER):
1 concrete — a physical, tangible thing: objects, substances, body parts, animals, foods, common-noun people/places (table, water, dog, teacher).
2 abstract — an intangible concept, idea, state, emotion, time period, or quantity (freedom, happiness, theory, year, danger).
3 action — a verb, or an event/process (run, decide, rain, develop).
4 property — a quality or attribute: adjectives and most adverbs (tall, quickly, beautiful, red, important).
5 function — a grammatical/function word with little standalone meaning: pronouns, particles, conjunctions, prepositions, determiners, measure words, auxiliaries (the, and, of).
6 proper — a proper noun naming one specific entity: a person, place, organisation, or brand (Beijing, Tanaka, Google).

Rules:
- Pick the single best class for the word's most common usage given its POS and definition.
- A word that primarily names one specific entity is 6, even if it looks like a common noun.
- Measure words, pronouns, and particles are 5, never 1 or 2.
- Confidence is 0.0-1.0; use below 0.6 only when genuinely ambiguous.

Return ONLY a JSON object mapping each item's id (as a string) to a two-element array [class_number 1-6, confidence]. Example: {"1": [3, 0.92], "2": [1, 0.6]}. No words, no commentary, no markdown.

Items:
{batch}$tmpl$,
    2, true,
    'TASK-507 — classify a lemma into the 6-value semantic_class enum (numeric output). flash-tier.',
    2, 'google/gemini-3.5-flash', 'openrouter'
);

-- Chinese (language_id = 1) — fully Chinese legend + rules; numeric output
INSERT INTO prompt_templates (task_name, template_text, version, is_active, description, language_id, model, provider)
VALUES (
    'semantic_class_classification',
    $tmpl$你是 LinguaLoop 词汇系统的语言分类器。请根据每个词的核心意义、词性和释义，把它归入六个语义类别中唯一的一个。

类别（请使用数字编号）：
1 具体——可感知的实物：物体、物质、身体部位、动物、食物，以及作为普通名词的人或地点（如：桌子、水、狗、老师）。
2 抽象——无形的概念、想法、状态、情感、时间段或数量（如：自由、幸福、理论、年份、危险）。
3 动作——动词，或事件、过程（如：跑、决定、下雨、发展）。
4 性质——性质或属性：形容词和大多数副词（如：高、快、漂亮、红、重要）。
5 功能——本身意义较弱的语法/功能词：代词、助词、连词、介词、限定词、量词、助动词（如：的、和、把、个）。
6 专有——指称某一特定实体的专有名词：人名、地名、组织或品牌（如：北京、田中、谷歌）。

规则：
- 根据词性和释义，为该词最常见的用法选择唯一最合适的类别。
- 如果一个词主要用作某一特定实体的名称，即使看起来像普通名词，也归为 6。
- 量词、代词、助词归为 5，绝不归为 1 或 2。
- 置信度为 0.0-1.0；只有在确实难以判断时才低于 0.6。

只返回一个 JSON 对象，把每个条目的 id（字符串）映射到二元数组 [类别编号 1-6, 置信度]。例如：{"1": [3, 0.92], "2": [1, 0.6]}。不要输出任何词语、说明或 markdown。

条目：
{batch}$tmpl$,
    2, true,
    'TASK-507 — 中文语义类别分类（数字输出），flash-tier。',
    1, 'google/gemini-3.5-flash', 'openrouter'
);

-- Japanese (language_id = 3) — fully Japanese legend + rules; numeric output
INSERT INTO prompt_templates (task_name, template_text, version, is_active, description, language_id, model, provider)
VALUES (
    'semantic_class_classification',
    $tmpl$あなたは LinguaLoop 語彙システムの言語分類器です。各語を、その中心的な意味・品詞・語義に基づいて、6 つの意味カテゴリーのうち厳密に 1 つに分類してください。

カテゴリー（番号を使用）：
1 具体——知覚できる実体：物体、物質、体の部分、動物、食べ物、普通名詞としての人や場所（例：机、水、犬、先生）。
2 抽象——無形の概念・考え・状態・感情・時間・数量（例：自由、幸福、理論、年、危険）。
3 動作——動詞、または出来事・過程（例：走る、決める、降る、発展する）。
4 性質——性質や属性：形容詞・形容動詞と多くの副詞（例：高い、速く、美しい、赤い、重要）。
5 機能——単独では意味の薄い文法的・機能語：代名詞、助詞、接続詞、助動詞、連体詞、助数詞（例：は、を、の、と）。
6 固有——特定の実体を指す固有名詞：人名、地名、組織、ブランド（例：東京、田中、グーグル）。

規則：
- 品詞と語義から、その語の最も一般的な用法に対して唯一最適なカテゴリーを選ぶ。
- ある語が主に特定の実体の名称である場合は、普通名詞のように見えても 6 とする。
- 助数詞・代名詞・助詞は 5 であり、1 や 2 にはしない。
- 確信度は 0.0-1.0。本当に判断が難しい場合のみ 0.6 未満にする。

JSON オブジェクトのみを返し、各項目の id（文字列）を二要素配列 [カテゴリー番号 1-6, 確信度] に対応させてください。例：{"1": [3, 0.92], "2": [1, 0.6]}。語句・説明・markdown は出力しないこと。

項目：
{batch}$tmpl$,
    2, true,
    'TASK-507 — 日本語の意味カテゴリー分類（数値出力）、flash-tier。',
    3, 'google/gemini-3.5-flash', 'openrouter'
);
