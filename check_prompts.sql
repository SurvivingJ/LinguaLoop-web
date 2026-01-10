-- Run this in Supabase SQL Editor to check prompt templates

-- Check which test generation prompts exist
SELECT
    task_name,
    language_id,
    is_active,
    LEFT(template_text, 100) as template_preview,
    created_at
FROM prompt_templates
WHERE task_name IN (
    'prose_generation',
    'question_literal_detail',
    'question_vocabulary_context',
    'question_main_idea',
    'question_supporting_detail',
    'question_inference',
    'question_author_purpose'
)
ORDER BY task_name, language_id;

-- Count them
SELECT
    COUNT(*) as total_test_prompts
FROM prompt_templates
WHERE task_name LIKE 'question_%'
   OR task_name = 'prose_generation';

-- Check one sample to see the format
SELECT
    task_name,
    template_text
FROM prompt_templates
WHERE task_name = 'question_literal_detail'
  AND language_id = 2  -- English (universal fallback)
  AND is_active = TRUE
LIMIT 1;
