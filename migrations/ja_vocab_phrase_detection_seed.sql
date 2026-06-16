-- ja_vocab_phrase_detection_seed.sql — JA (language_id=3) vocab_phrase_detection prompt.
-- TASK-505 prerequisite (JA vocabulary bootstrap). The JA extraction batch
-- (scripts/backfill_vocab.py --language ja) hard-fails without an active
-- vocab_phrase_detection row for language_id=3 (services/vocabulary/pipeline.py
-- uses get_template_config, which requires model+provider). ZH/EN already have
-- this row; JA was missing. The sibling extraction prompts
-- (vocab_definition_generation, vocab_sense_selection) already have JA rows.
--
-- Cloned structurally from the ZH/EN vocab_phrase_detection, adapted to Japanese
-- multi-word expressions (複合動詞 / 慣用句 / 複合語・熟語 / 連語). Uses the
-- extraction-layer model (google/gemini-2.5-flash-lite, like ZH/EN) — cheap and
-- fast; the qwen3.7-plus JA decision is for the ladder generation prompts, not
-- this extraction step.
--
-- Idempotent: guarded by WHERE NOT EXISTS (no unique constraint on
-- task_name+language_id+version). Re-running is a no-op.

INSERT INTO prompt_templates (task_name, language_id, version, is_active, provider, model, description, template_text)
SELECT 'vocab_phrase_detection', 3, 1, true, 'openrouter', 'google/gemini-2.5-flash-lite',
       'JA vocab phrase detection (TASK-505) — multi-word expression detection over fugashi lemmas',
$t$あなたは日本語の辞書学を専門とする計算言語学者です。
あなたの仕事は、見出し語（基本形）のリストの中から多語表現（複合表現）を識別することです。

言語的背景：
日本語の単語は活用します。見出し語は基本形です：
「走って」→「走る」、「図書館員たち」→「図書館員」、「より良い」→「良い」。
複合動詞・サ変動詞・慣用句が多く、字面の意味とは異なる意味を持ちます：「取り組む」「立ち上がる」「勉強する」「気を付ける」。

あるテキストが以下の見出し語に分割されています。
各単語の字面の意味の総和とは異なる意味を持つ多語表現をすべて識別してください。

見出し語（縦棒区切り、語順どおり）：
{lemma_list}

原文（参照のみ — 再分割しないこと）：
"""{original_text}"""

識別すべき多語表現の種類：
- phrasal_verb  — 複合動詞、字面どおりでない意味（例：「取り組む」「立ち上がる」）
- idiom         — 慣用句・四字熟語、字面どおりでない意味（例：「気を付ける」「油を売る」）
- compound      — 二語で一つの概念を成す複合語・熟語（例：「図書館」「電車」）
- collocation   — 強く結びつく連語（例：「決定を下す」「風邪を引く」）

規則：
- 原文の表層形ではなく、見出し語リストの形を使うこと。
- 各構成要素は見出し語リストに正しい語順で現れること。
- 字面どおりの組み合わせは識別しないこと。
- 機能語（助詞・助動詞）だけを単独で識別しないこと。
- 最長一致を優先すること。

次の JSON 形式で厳密に返答すること：
{{
  "phrases": [
    {{
      "phrase": "取り組む",
      "components": ["取る", "組む"],
      "phrase_type": "phrasal_verb",
      "reasoning": "字面どおりでない：物事に本気で当たる意味で、取って組む意ではない"
    }}
  ]
}}

多語表現が無い場合は、厳密に次を返すこと：{{"phrases": []}}$t$
WHERE NOT EXISTS (
    SELECT 1 FROM prompt_templates WHERE task_name='vocab_phrase_detection' AND language_id=3
);
