-- ============================================================
-- Migration: Add Title Generation Prompt Templates
-- Date: 2026-01-11
-- Description: Adds prompt templates for title generation in English, Chinese, and Japanese
-- ============================================================

-- title_generation prompt - English (universal fallback)
INSERT INTO prompt_templates (task_name, language_id, template_text, description, version) VALUES
(
    'title_generation',
    2,  -- English (language_id=2)
    'Generate a concise, engaging title for this listening comprehension passage.

PASSAGE:
{prose}

TOPIC: {topic_concept}
DIFFICULTY: {difficulty}/9
CEFR LEVEL: {cefr_level}
TARGET LANGUAGE: {language}

Requirements:
- Write the title ONLY in {language}
- Adapt the title length and complexity to match the difficulty level:
  * Difficulty 1-2 (A1): Very simple, 3-6 words, basic vocabulary
  * Difficulty 3-4 (A2): Simple, 4-8 words, straightforward language
  * Difficulty 5 (B1): Clear, 5-10 words, everyday vocabulary
  * Difficulty 6 (B2): Moderately descriptive, 6-12 words, varied vocabulary
  * Difficulty 7 (C1): Sophisticated, 8-15 words, nuanced expressions
  * Difficulty 8-9 (C2): Complex, 10-18 words, advanced vocabulary and structures
- Capture the main theme or subject of the passage
- Make it engaging and informative
- Do NOT include quotation marks, formatting, or extra commentary

Return ONLY the title text in {language}, nothing else.',
    'Universal prompt for generating test titles',
    1
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- title_generation prompt - Chinese (language_id=1)
INSERT INTO prompt_templates (task_name, language_id, template_text, description, version) VALUES
(
    'title_generation',
    1,  -- Chinese
    '为这段听力理解文章生成一个简洁、吸引人的标题。

文章内容：
{prose}

主题：{topic_concept}
难度：{difficulty}/9
CEFR级别：{cefr_level}
目标语言：{language}

要求：
- 标题必须用{language}书写
- 根据难度级别调整标题的长度和复杂度：
  * 难度1-2（A1）：非常简单，5-10个字符，基础词汇
  * 难度3-4（A2）：简单明了，8-15个字符，常用词汇
  * 难度5（B1）：清晰，10-18个字符，日常词汇
  * 难度6（B2）：适度描述性，12-22个字符，多样词汇
  * 难度7（C1）：精致，15-28个字符，细腻表达
  * 难度8-9（C2）：复杂，18-35个字符，高级词汇和结构
- 捕捉文章的主要主题或内容
- 使其引人入胜且富有信息性
- 不要包含引号、格式或额外的评论

只返回用{language}写的标题文本，不要其他内容。',
    'Chinese-specific prompt for generating test titles',
    1
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- title_generation prompt - Japanese (language_id=3)
INSERT INTO prompt_templates (task_name, language_id, template_text, description, version) VALUES
(
    'title_generation',
    3,  -- Japanese
    'このリスニング理解の文章のための簡潔で魅力的なタイトルを生成してください。

文章：
{prose}

トピック：{topic_concept}
難易度：{difficulty}/9
CEFRレベル：{cefr_level}
対象言語：{language}

要件：
- タイトルは{language}のみで書いてください
- 難易度レベルに応じてタイトルの長さと複雑さを調整：
  * 難易度1-2（A1）：非常にシンプル、5-12文字、基本語彙
  * 難易度3-4（A2）：シンプル、8-16文字、わかりやすい言葉
  * 難易度5（B1）：明確、10-20文字、日常語彙
  * 難易度6（B2）：やや記述的、12-25文字、多様な語彙
  * 難易度7（C1）：洗練された、15-30文字、ニュアンスのある表現
  * 難易度8-9（C2）：複雑、18-35文字、高度な語彙と構造
- 文章の主なテーマまたは主題を捉える
- 魅力的で情報性の高いものにする
- 引用符、書式設定、または追加のコメントを含めないでください

{language}で書かれたタイトルテキストのみを返してください。他には何も返さないでください。',
    'Japanese-specific prompt for generating test titles',
    1
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- Verify insertion
SELECT task_name, language_id, description
FROM prompt_templates
WHERE task_name = 'title_generation'
ORDER BY language_id;
