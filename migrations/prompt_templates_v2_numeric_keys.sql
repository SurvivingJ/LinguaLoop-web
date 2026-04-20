-- ============================================================
-- Prompt Templates v2: Numerical JSON Keys + Distractor Types
-- ============================================================
-- Updates question generation prompts to use numerical keys (1-5)
-- instead of English keys (Question, Options, Answer).
-- Also adds distractor type tagging (semantic/grammatical/contextual).
--
-- The existing get_prompt_template() query selects is_active=true
-- and orders by version DESC, so setting v1 inactive and inserting
-- v2 as active is sufficient. No code change needed.
-- ============================================================

-- Step 1: Deactivate all existing question prompt templates (version 1)
UPDATE prompt_templates
SET is_active = false, updated_at = now()
WHERE task_name LIKE 'question_%'
  AND is_active = true;

-- Step 2: Insert v2 question templates for each language
-- These use numerical JSON keys and include distractor type instructions.
-- Template variables: {prose}, {difficulty}, {previous_questions}, {language}

-- ── literal_detail ──────────────────────────────────────────

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES
-- English (language_id=2)
('question_literal_detail', 2, 2, true,
 'Literal detail question — numerical keys + distractor types',
 'Generate a comprehension question about a specific fact or detail explicitly stated in the passage.

PASSAGE:
{prose}

DIFFICULTY: {difficulty}/9

PREVIOUSLY ASKED QUESTIONS (do NOT repeat similar questions):
{previous_questions}

Requirements:
1. Write the question and ALL options ONLY in {language}
2. The answer must be directly findable in the passage
3. Create exactly 4 answer options
4. Tag each incorrect option with a distractor type

Return ONLY valid JSON with numerical keys:
{{
    "1": "Your question text",
    "2": ["Option A", "Option B", "Option C", "Option D"],
    "3": "The correct option text (must match one element of key 2)",
    "4": [false, true, false, false],
    "5": ["semantic", null, "contextual", "grammatical"]
}}

Key definitions:
1 = question text
2 = exactly 4 answer options
3 = correct answer (must match one option in key 2)
4 = boolean array (true = correct option)
5 = distractor type per option: null for correct, "semantic"|"grammatical"|"contextual" for wrong options
  - semantic: plausible but wrong meaning
  - grammatical: correct word, wrong form
  - contextual: plausible in another context but not this passage'),

-- Chinese (language_id=1)
('question_literal_detail', 1, 2, true,
 'Literal detail question — numerical keys + distractor types (Chinese)',
 'Generate a comprehension question about a specific fact or detail explicitly stated in the passage.

PASSAGE:
{prose}

DIFFICULTY: {difficulty}/9

PREVIOUSLY ASKED QUESTIONS (do NOT repeat similar questions):
{previous_questions}

CRITICAL: Write the question and ALL options ONLY in {language}. Do not use English.

Requirements:
1. The answer must be directly findable in the passage
2. Create exactly 4 answer options in {language}
3. Tag each incorrect option with a distractor type

Return ONLY valid JSON with numerical keys:
{{
    "1": "question text in {language}",
    "2": ["option A", "option B", "option C", "option D"],
    "3": "correct option text",
    "4": [false, true, false, false],
    "5": ["semantic", null, "contextual", "grammatical"]
}}

Key definitions:
1 = question text, 2 = 4 options, 3 = correct answer, 4 = boolean mask, 5 = distractor types (null=correct, semantic|grammatical|contextual=wrong)'),

-- Japanese (language_id=3)
('question_literal_detail', 3, 2, true,
 'Literal detail question — numerical keys + distractor types (Japanese)',
 'Generate a comprehension question about a specific fact or detail explicitly stated in the passage.

PASSAGE:
{prose}

DIFFICULTY: {difficulty}/9

PREVIOUSLY ASKED QUESTIONS (do NOT repeat similar questions):
{previous_questions}

CRITICAL: Write the question and ALL options ONLY in {language}. Do not use English.

Requirements:
1. The answer must be directly findable in the passage
2. Create exactly 4 answer options in {language}
3. Tag each incorrect option with a distractor type

Return ONLY valid JSON with numerical keys:
{{
    "1": "question text in {language}",
    "2": ["option A", "option B", "option C", "option D"],
    "3": "correct option text",
    "4": [false, true, false, false],
    "5": ["semantic", null, "contextual", "grammatical"]
}}

Key definitions:
1 = question text, 2 = 4 options, 3 = correct answer, 4 = boolean mask, 5 = distractor types (null=correct, semantic|grammatical|contextual=wrong)');

-- ── vocabulary_context ──────────────────────────────────────

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
SELECT 'question_vocabulary_context', lang.id, 2, true,
       'Vocabulary in context — numerical keys + distractor types',
       'Generate a comprehension question about the meaning of a word or phrase as used in the passage.

PASSAGE:
{prose}

DIFFICULTY: {difficulty}/9
PREVIOUSLY ASKED: {previous_questions}

CRITICAL: Write the question and ALL options ONLY in {language}. Do not use English.

Focus on how context shapes meaning. Test whether the reader understands a specific word/phrase in its passage context.

Return ONLY valid JSON:
{{
    "1": "question about a word or phrase meaning in {language}",
    "2": ["option A", "option B", "option C", "option D"],
    "3": "correct option",
    "4": [false, true, false, false],
    "5": ["semantic", null, "contextual", "grammatical"]
}}

Keys: 1=question, 2=4 options, 3=correct answer, 4=boolean mask, 5=distractor types (null=correct, semantic|grammatical|contextual=wrong)'
FROM dim_languages lang WHERE lang.id IN (1, 2, 3);

-- ── main_idea ───────────────────────────────────────────────

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
SELECT 'question_main_idea', lang.id, 2, true,
       'Main idea — numerical keys + distractor types',
       'Generate a comprehension question about the central theme, main point, or overall purpose of the passage.

PASSAGE:
{prose}

DIFFICULTY: {difficulty}/9
PREVIOUSLY ASKED: {previous_questions}

CRITICAL: Write the question and ALL options ONLY in {language}. Do not use English.

Return ONLY valid JSON:
{{
    "1": "question about the main idea in {language}",
    "2": ["option A", "option B", "option C", "option D"],
    "3": "correct option",
    "4": [false, true, false, false],
    "5": ["semantic", null, "contextual", "grammatical"]
}}

Keys: 1=question, 2=4 options, 3=correct answer, 4=boolean mask, 5=distractor types (null=correct, semantic|grammatical|contextual=wrong)'
FROM dim_languages lang WHERE lang.id IN (1, 2, 3);

-- ── supporting_detail ───────────────────────────────────────

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
SELECT 'question_supporting_detail', lang.id, 2, true,
       'Supporting detail — numerical keys + distractor types',
       'Generate a comprehension question about information that supports or explains the main ideas in the passage.

PASSAGE:
{prose}

DIFFICULTY: {difficulty}/9
PREVIOUSLY ASKED: {previous_questions}

CRITICAL: Write the question and ALL options ONLY in {language}. Do not use English.

Return ONLY valid JSON:
{{
    "1": "question about a supporting detail in {language}",
    "2": ["option A", "option B", "option C", "option D"],
    "3": "correct option",
    "4": [false, true, false, false],
    "5": ["semantic", null, "contextual", "grammatical"]
}}

Keys: 1=question, 2=4 options, 3=correct answer, 4=boolean mask, 5=distractor types (null=correct, semantic|grammatical|contextual=wrong)'
FROM dim_languages lang WHERE lang.id IN (1, 2, 3);

-- ── inference ───────────────────────────────────────────────

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
SELECT 'question_inference', lang.id, 2, true,
       'Inference — numerical keys + distractor types',
       'Generate a comprehension question about something not directly stated but that can be concluded from the information given.

PASSAGE:
{prose}

DIFFICULTY: {difficulty}/9
PREVIOUSLY ASKED: {previous_questions}

CRITICAL: Write the question and ALL options ONLY in {language}. Do not use English.

Require reasoning beyond explicitly stated facts. Test the reader''s ability to draw conclusions.

Return ONLY valid JSON:
{{
    "1": "inference question in {language}",
    "2": ["option A", "option B", "option C", "option D"],
    "3": "correct option",
    "4": [false, true, false, false],
    "5": ["semantic", null, "contextual", "grammatical"]
}}

Keys: 1=question, 2=4 options, 3=correct answer, 4=boolean mask, 5=distractor types (null=correct, semantic|grammatical|contextual=wrong)'
FROM dim_languages lang WHERE lang.id IN (1, 2, 3);

-- ── author_purpose ──────────────────────────────────────────

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
SELECT 'question_author_purpose', lang.id, 2, true,
       'Author purpose/tone — numerical keys + distractor types',
       'Generate a comprehension question about why the author wrote the passage, their attitude, or the intended effect on readers.

PASSAGE:
{prose}

DIFFICULTY: {difficulty}/9
PREVIOUSLY ASKED: {previous_questions}

CRITICAL: Write the question and ALL options ONLY in {language}. Do not use English.

Focus on tone, purpose, organizational patterns, or the author''s perspective.

Return ONLY valid JSON:
{{
    "1": "question about author purpose/tone in {language}",
    "2": ["option A", "option B", "option C", "option D"],
    "3": "correct option",
    "4": [false, true, false, false],
    "5": ["semantic", null, "contextual", "grammatical"]
}}

Keys: 1=question, 2=4 options, 3=correct answer, 4=boolean mask, 5=distractor types (null=correct, semantic|grammatical|contextual=wrong)'
FROM dim_languages lang WHERE lang.id IN (1, 2, 3);
