-- ============================================================
-- Test Generation System - Database Migrations
-- ============================================================
-- Run these SQL statements in Supabase SQL Editor in order.
-- This creates all tables needed for the test generation pipeline.
-- ============================================================

-- ============================================================
-- PART 1: New Dimension Tables
-- ============================================================

-- dim_question_types: 6 semantic question types
CREATE TABLE IF NOT EXISTS dim_question_types (
    id SMALLSERIAL PRIMARY KEY,
    type_code VARCHAR(30) UNIQUE NOT NULL,
    type_name VARCHAR(50) NOT NULL,
    description TEXT,
    cognitive_level INTEGER NOT NULL CHECK (cognitive_level BETWEEN 1 AND 3),
    is_active BOOLEAN DEFAULT TRUE,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed question types
INSERT INTO dim_question_types (type_code, type_name, cognitive_level, description, display_order) VALUES
    ('literal_detail', 'Literal Detail', 1, 'Direct facts from text', 1),
    ('vocabulary_context', 'Vocabulary in Context', 1, 'Word/phrase meaning in passage', 2),
    ('main_idea', 'Main Idea', 2, 'Central theme or purpose', 3),
    ('supporting_detail', 'Supporting Detail', 2, 'Facts supporting main points', 4),
    ('inference', 'Inference', 3, 'Conclusions from implicit info', 5),
    ('author_purpose', 'Author Purpose/Tone', 3, 'Why author wrote, attitude', 6)
ON CONFLICT (type_code) DO NOTHING;

-- dim_cefr_levels: Word counts and initial ELO per CEFR level
CREATE TABLE IF NOT EXISTS dim_cefr_levels (
    id SMALLSERIAL PRIMARY KEY,
    cefr_code VARCHAR(2) UNIQUE NOT NULL,
    difficulty_min INTEGER NOT NULL,
    difficulty_max INTEGER NOT NULL,
    word_count_min INTEGER NOT NULL,
    word_count_max INTEGER NOT NULL,
    initial_elo INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed CEFR levels
INSERT INTO dim_cefr_levels (id, cefr_code, difficulty_min, difficulty_max, word_count_min, word_count_max, initial_elo) VALUES
    (1, 'A1', 1, 2, 80, 150, 875),
    (2, 'A2', 3, 4, 120, 200, 1175),
    (3, 'B1', 5, 5, 200, 300, 1400),
    (4, 'B2', 6, 6, 300, 400, 1550),
    (5, 'C1', 7, 7, 400, 600, 1700),
    (6, 'C2', 8, 9, 600, 900, 1925)
ON CONFLICT (cefr_code) DO NOTHING;

-- question_type_distributions: Which question types for each difficulty
CREATE TABLE IF NOT EXISTS question_type_distributions (
    difficulty INTEGER PRIMARY KEY CHECK (difficulty BETWEEN 1 AND 9),
    question_type_1 VARCHAR(30) REFERENCES dim_question_types(type_code),
    question_type_2 VARCHAR(30) REFERENCES dim_question_types(type_code),
    question_type_3 VARCHAR(30) REFERENCES dim_question_types(type_code),
    question_type_4 VARCHAR(30) REFERENCES dim_question_types(type_code),
    question_type_5 VARCHAR(30) REFERENCES dim_question_types(type_code),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed question distributions
-- Lower difficulties: more literal/vocabulary questions
-- Higher difficulties: more inference/author purpose questions
INSERT INTO question_type_distributions (difficulty, question_type_1, question_type_2, question_type_3, question_type_4, question_type_5) VALUES
    (1, 'literal_detail', 'literal_detail', 'vocabulary_context', 'vocabulary_context', 'main_idea'),
    (2, 'literal_detail', 'literal_detail', 'vocabulary_context', 'vocabulary_context', 'main_idea'),
    (3, 'literal_detail', 'vocabulary_context', 'vocabulary_context', 'main_idea', 'supporting_detail'),
    (4, 'literal_detail', 'vocabulary_context', 'main_idea', 'supporting_detail', 'supporting_detail'),
    (5, 'vocabulary_context', 'main_idea', 'main_idea', 'supporting_detail', 'inference'),
    (6, 'vocabulary_context', 'main_idea', 'supporting_detail', 'inference', 'inference'),
    (7, 'main_idea', 'supporting_detail', 'supporting_detail', 'inference', 'author_purpose'),
    (8, 'main_idea', 'supporting_detail', 'inference', 'inference', 'author_purpose'),
    (9, 'supporting_detail', 'inference', 'inference', 'author_purpose', 'author_purpose')
ON CONFLICT (difficulty) DO UPDATE SET
    question_type_1 = EXCLUDED.question_type_1,
    question_type_2 = EXCLUDED.question_type_2,
    question_type_3 = EXCLUDED.question_type_3,
    question_type_4 = EXCLUDED.question_type_4,
    question_type_5 = EXCLUDED.question_type_5;

-- test_generation_config: Runtime settings
CREATE TABLE IF NOT EXISTS test_generation_config (
    config_key VARCHAR(50) PRIMARY KEY,
    config_value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed config values
INSERT INTO test_generation_config (config_key, config_value, description) VALUES
    ('target_difficulties', '[4, 6, 9]', 'Difficulties to generate per queue item'),
    ('batch_size', '50', 'Max queue items per run'),
    ('system_user_id', 'de6fd05b-0871-45d4-a2d8-0195fdf5355e', 'System user for gen_user field'),
    ('questions_per_test', '5', 'Number of questions per test'),
    ('default_prose_model', 'google/gemini-2.0-flash-exp', 'Default LLM for prose generation'),
    ('default_question_model', 'google/gemini-2.0-flash-exp', 'Default LLM for question generation')
ON CONFLICT (config_key) DO NOTHING;

-- test_generation_runs: Metrics logging
CREATE TABLE IF NOT EXISTS test_generation_runs (
    id SERIAL PRIMARY KEY,
    run_date DATE NOT NULL DEFAULT CURRENT_DATE,
    queue_items_processed INTEGER DEFAULT 0,
    tests_generated INTEGER DEFAULT 0,
    tests_failed INTEGER DEFAULT 0,
    execution_time_seconds INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for metrics queries
CREATE INDEX IF NOT EXISTS idx_test_generation_runs_date
    ON test_generation_runs(run_date);


-- ============================================================
-- PART 2: Modify Existing Tables
-- ============================================================

-- Add question_type_id to questions table
ALTER TABLE questions
    ADD COLUMN IF NOT EXISTS question_type_id SMALLINT REFERENCES dim_question_types(id);

-- Create index for question type lookups
CREATE INDEX IF NOT EXISTS idx_questions_type
    ON questions(question_type_id);

-- Add model config columns to dim_languages
ALTER TABLE dim_languages
    ADD COLUMN IF NOT EXISTS prose_model VARCHAR(100) DEFAULT 'google/gemini-2.0-flash-exp',
    ADD COLUMN IF NOT EXISTS question_model VARCHAR(100) DEFAULT 'google/gemini-2.0-flash-exp',
    ADD COLUMN IF NOT EXISTS tts_voice_ids JSONB DEFAULT '["alloy"]'::jsonb,
    ADD COLUMN IF NOT EXISTS tts_speed DECIMAL(3,2) DEFAULT 1.0,
    ADD COLUMN IF NOT EXISTS grammar_check_enabled BOOLEAN DEFAULT FALSE;

-- Add tracking columns to production_queue
ALTER TABLE production_queue
    ADD COLUMN IF NOT EXISTS tests_generated INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS error_log TEXT;


-- ============================================================
-- PART 3: Prompt Templates for Test Generation
-- ============================================================

-- prose_generation prompt
INSERT INTO prompt_templates (task_name, language_id, template_text, description) VALUES
(
    'prose_generation',
    2,  -- English (universal fallback)
    'Generate a natural, engaging prose passage for language learners.

TOPIC: {topic_concept}
TARGET LANGUAGE: {language}
LANGUAGE CODE: {language_code}
DIFFICULTY: {difficulty}/9
CEFR LEVEL: {cefr_level}
WORD COUNT: {min_words}-{max_words} words
KEYWORDS: {keywords}

Requirements:
- Write ONLY in {language}
- Use vocabulary and grammar appropriate for the CEFR {cefr_level} level
- Create natural, flowing prose suitable for listening comprehension
- Include clear main ideas with supporting details
- Incorporate keywords when possible: {keywords}
- Avoid overly complex vocabulary for lower levels
- For higher levels, include nuanced expressions and complex structures

Style:
- Conversational but informative
- Clear paragraph structure
- Varied sentence lengths
- Culturally appropriate content

Return ONLY the prose text, with no additional commentary or formatting.',
    'Main prompt for generating prose/transcript content'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- question_literal_detail prompt
INSERT INTO prompt_templates (task_name, language_id, template_text, description) VALUES
(
    'question_literal_detail',
    2,  -- English (universal fallback)
    'Generate a LITERAL DETAIL comprehension question in {language}.

PASSAGE:
{prose}

DIFFICULTY: {difficulty}/9
PREVIOUSLY ASKED: {previous_questions}

Instructions:
- Ask about a specific fact explicitly stated in the text
- The answer should be directly findable in the passage
- Create 4 plausible answer options
- Only one option should be correct
- Make sure the question and all options are in {language}

Return ONLY valid JSON:
{{
    "Question": "Your question text here?",
    "Options": ["Option A", "Option B", "Option C", "Option D"],
    "Answer": "The correct option (must match one of Options exactly)"
}}',
    'Literal detail question type prompt'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- question_vocabulary_context prompt
INSERT INTO prompt_templates (task_name, language_id, template_text, description) VALUES
(
    'question_vocabulary_context',
    2,  -- English (universal fallback)
    'Generate a VOCABULARY IN CONTEXT question in {language}.

PASSAGE:
{prose}

DIFFICULTY: {difficulty}/9
PREVIOUSLY ASKED: {previous_questions}

Instructions:
- Ask about the meaning of a word or phrase as used in the passage
- Focus on how context shapes meaning
- Create 4 plausible answer options
- Only one option should be correct
- Make sure the question and all options are in {language}

Return ONLY valid JSON:
{{
    "Question": "Your question text here?",
    "Options": ["Option A", "Option B", "Option C", "Option D"],
    "Answer": "The correct option (must match one of Options exactly)"
}}',
    'Vocabulary in context question type prompt'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- question_main_idea prompt
INSERT INTO prompt_templates (task_name, language_id, template_text, description) VALUES
(
    'question_main_idea',
    2,  -- English (universal fallback)
    'Generate a MAIN IDEA question in {language}.

PASSAGE:
{prose}

DIFFICULTY: {difficulty}/9
PREVIOUSLY ASKED: {previous_questions}

Instructions:
- Ask about the central theme, main point, or overall purpose
- Focus on what the passage is primarily about
- Create 4 plausible answer options
- Only one option should be correct
- Make sure the question and all options are in {language}

Return ONLY valid JSON:
{{
    "Question": "Your question text here?",
    "Options": ["Option A", "Option B", "Option C", "Option D"],
    "Answer": "The correct option (must match one of Options exactly)"
}}',
    'Main idea question type prompt'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- question_supporting_detail prompt
INSERT INTO prompt_templates (task_name, language_id, template_text, description) VALUES
(
    'question_supporting_detail',
    2,  -- English (universal fallback)
    'Generate a SUPPORTING DETAIL question in {language}.

PASSAGE:
{prose}

DIFFICULTY: {difficulty}/9
PREVIOUSLY ASKED: {previous_questions}

Instructions:
- Ask about information that supports or explains the main ideas
- Focus on details that provide evidence or examples
- Create 4 plausible answer options
- Only one option should be correct
- Make sure the question and all options are in {language}

Return ONLY valid JSON:
{{
    "Question": "Your question text here?",
    "Options": ["Option A", "Option B", "Option C", "Option D"],
    "Answer": "The correct option (must match one of Options exactly)"
}}',
    'Supporting detail question type prompt'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- question_inference prompt
INSERT INTO prompt_templates (task_name, language_id, template_text, description) VALUES
(
    'question_inference',
    2,  -- English (universal fallback)
    'Generate an INFERENCE question in {language}.

PASSAGE:
{prose}

DIFFICULTY: {difficulty}/9
PREVIOUSLY ASKED: {previous_questions}

Instructions:
- Ask about something not directly stated but that can be concluded
- Require the reader to "read between the lines"
- Create 4 plausible answer options
- Only one option should be correct
- Make sure the question and all options are in {language}

Return ONLY valid JSON:
{{
    "Question": "Your question text here?",
    "Options": ["Option A", "Option B", "Option C", "Option D"],
    "Answer": "The correct option (must match one of Options exactly)"
}}',
    'Inference question type prompt'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- question_author_purpose prompt
INSERT INTO prompt_templates (task_name, language_id, template_text, description) VALUES
(
    'question_author_purpose',
    2,  -- English (universal fallback)
    'Generate an AUTHOR PURPOSE/TONE question in {language}.

PASSAGE:
{prose}

DIFFICULTY: {difficulty}/9
PREVIOUSLY ASKED: {previous_questions}

Instructions:
- Ask about why the author wrote the passage
- Or ask about the author''s attitude, tone, or intended effect
- Create 4 plausible answer options
- Only one option should be correct
- Make sure the question and all options are in {language}

Return ONLY valid JSON:
{{
    "Question": "Your question text here?",
    "Options": ["Option A", "Option B", "Option C", "Option D"],
    "Answer": "The correct option (must match one of Options exactly)"
}}',
    'Author purpose/tone question type prompt'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- ============================================================
-- PART 3B: Title Generation Prompts
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


-- ============================================================
-- PART 4: Helper Functions (Optional)
-- ============================================================

-- get_cefr_config: Get CEFR config for a difficulty level
CREATE OR REPLACE FUNCTION get_cefr_config(p_difficulty INTEGER)
RETURNS TABLE (
    id INTEGER,
    cefr_code VARCHAR(2),
    word_count_min INTEGER,
    word_count_max INTEGER,
    initial_elo INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id::INTEGER,
        c.cefr_code,
        c.word_count_min,
        c.word_count_max,
        c.initial_elo
    FROM dim_cefr_levels c
    WHERE p_difficulty BETWEEN c.difficulty_min AND c.difficulty_max
    LIMIT 1;
END;
$$;

-- get_question_distribution: Get question types for a difficulty
CREATE OR REPLACE FUNCTION get_question_distribution(p_difficulty INTEGER)
RETURNS TABLE (
    question_type_code VARCHAR(30)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT unnest(ARRAY[
        d.question_type_1,
        d.question_type_2,
        d.question_type_3,
        d.question_type_4,
        d.question_type_5
    ]) AS question_type_code
    FROM question_type_distributions d
    WHERE d.difficulty = p_difficulty;
END;
$$;


-- ============================================================
-- VERIFICATION QUERIES
-- ============================================================
-- Run these to verify the migration worked:

-- SELECT COUNT(*) FROM dim_question_types;  -- Should be 6
-- SELECT COUNT(*) FROM dim_cefr_levels;     -- Should be 6
-- SELECT COUNT(*) FROM question_type_distributions;  -- Should be 9
-- SELECT COUNT(*) FROM test_generation_config;  -- Should be 6
-- SELECT * FROM prompt_templates WHERE task_name LIKE 'question_%';  -- Should be 6 rows
-- SELECT * FROM prompt_templates WHERE task_name = 'prose_generation';  -- Should be 1 row
