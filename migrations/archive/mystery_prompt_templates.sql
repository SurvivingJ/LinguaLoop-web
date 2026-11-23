-- ============================================================================
-- Mystery Generation Prompt Templates
-- ============================================================================
-- Idempotent: safe to re-run. Deletes existing mystery templates then inserts.
--
-- Per-language prompt templates for the mystery generation pipeline.
-- Each template uses {variable} placeholders substituted at runtime.
--
-- Language IDs: 1=Chinese, 2=English, 3=Japanese
--
-- Task names:
--   mystery_plot       - PlotArchitect: story bible generation
--   mystery_scene      - SceneWriter: scene prose generation
--   mystery_question   - QuestionGenerator: scene MCQ generation
--   mystery_deduction  - QuestionGenerator: finale deduction question
--   mystery_clue       - ClueDesigner: clue text generation
-- ============================================================================


-- ============================================================================
-- 0. DELETE EXISTING MYSTERY TEMPLATES
-- ============================================================================

DELETE FROM prompt_templates
WHERE task_name IN ('mystery_plot', 'mystery_scene', 'mystery_question', 'mystery_deduction', 'mystery_clue');


-- ============================================================================
-- ENGLISH (language_id = 2)
-- ============================================================================

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
    'mystery_plot', 2, 1, true,
    'English mystery plot/story bible generation',
    'Create a murder mystery story bible with these parameters:
- Language: {language_name}
- CEFR Level: {cefr_level}
- Archetype: {archetype}
- Target vocabulary words to include: {target_vocab}

Generate a JSON object with this exact structure:
{{
    "title": "Mystery title in English",
    "premise": "1-2 sentence setup in English",
    "suspects": [
        {{
            "name": "Character name",
            "description": "Brief character description",
            "motive": "Why they might have done it",
            "alibi": "Their claimed alibi"
        }}
    ],
    "solution": {{
        "suspect_name": "Name of the actual killer",
        "reasoning": "How the clues prove their guilt (2-3 sentences)"
    }},
    "scenes": [
        {{
            "scene_number": 1,
            "title": "Scene title",
            "setting": "Where this scene takes place",
            "events": "What happens in this scene (3-4 sentences)",
            "clue_type": "evidence|alibi|testimony|forensic",
            "clue_hint": "What clue is revealed here",
            "vocab_focus": ["word1", "word2"]
        }}
    ]
}}

Include exactly 3-4 suspects and exactly 5 scenes.
ALL text content must be written in English.'
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
    'mystery_scene', 2, 1, true,
    'English mystery scene prose generation',
    'Write Scene {scene_number} of a murder mystery.

Mystery title: {title}
Scene setting: {setting}
Events to cover: {events}
Vocabulary to include: {vocab_words}

Previous scenes summary: {previous_summary}

Write the scene text now in {language_name}:'
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
    'mystery_question', 2, 1, true,
    'English mystery scene MCQ generation',
    'Create {num_questions} multiple-choice comprehension question(s) for this scene:

Scene text:
{scene_text}

Mystery context: {context}

Generate JSON array of questions:
[
    {{
        "question_text": "Question in {language_name}",
        "choices": [
            {{"label": "A", "text": "Option A"}},
            {{"label": "B", "text": "Option B"}},
            {{"label": "C", "text": "Option C"}},
            {{"label": "D", "text": "Option D"}}
        ],
        "correct_answer": "The exact text of the correct option",
        "explanation": "Brief explanation of why this is correct",
        "question_type": "inference|vocabulary|literal"
    }}
]'
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
    'mystery_deduction', 2, 1, true,
    'English mystery finale deduction question',
    'Create 1 deduction question for the finale of a murder mystery.

The learner has collected these clues across 5 scenes:
{clues_summary}

Suspects: {suspects_summary}

The correct answer is: {solution_suspect}

Generate a JSON array with 1 question asking who committed the crime.
Options should be the suspect names. Format:
[
    {{
        "question_text": "Based on the evidence, who is responsible?",
        "choices": [
            {{"label": "A", "text": "Suspect 1 name"}},
            {{"label": "B", "text": "Suspect 2 name"}},
            {{"label": "C", "text": "Suspect 3 name"}},
            {{"label": "D", "text": "Suspect 4 name"}}
        ],
        "correct_answer": "Name of the correct suspect",
        "explanation": "{solution_reasoning}",
        "question_type": "inference",
        "is_deduction": true
    }}
]'
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
    'mystery_clue', 2, 1, true,
    'English mystery clue text generation',
    'Design the clue for Scene {scene_number} of this mystery:

Mystery: {title}
Scene events: {events}
Clue type: {clue_type}
Clue hint from outline: {clue_hint}
Solution: {solution_suspect} did it because: {solution_reasoning}

Previous clues revealed:
{previous_clues}

Generate JSON:
{{
    "clue_text": "The clue text (1-2 sentences in English)",
    "clue_type": "{clue_type}"
}}'
);


-- ============================================================================
-- CHINESE (language_id = 1)
-- ============================================================================

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
    'mystery_plot', 1, 1, true,
    'Chinese mystery plot/story bible generation — prompt in Chinese',
    '请为语言学习平台创建一个谋杀悬疑故事设定，参数如下：
- 语言：{language_name}
- CEFR等级：{cefr_level}
- 类型：{archetype}
- 需要包含的目标词汇：{target_vocab}

请生成以下JSON结构：
{{
    "title": "用中文写的悬疑标题",
    "premise": "用中文写的1-2句故事背景",
    "suspects": [
        {{
            "name": "角色姓名（中文名）",
            "description": "简短的角色描述（中文）",
            "motive": "作案动机（中文）",
            "alibi": "不在场证明（中文）"
        }}
    ],
    "solution": {{
        "suspect_name": "凶手姓名",
        "reasoning": "线索如何证明其有罪（2-3句中文）"
    }},
    "scenes": [
        {{
            "scene_number": 1,
            "title": "场景标题（中文）",
            "setting": "场景地点（中文）",
            "events": "该场景发生的事件（3-4句中文）",
            "clue_type": "evidence|alibi|testimony|forensic",
            "clue_hint": "此处揭示的线索（中文）",
            "vocab_focus": ["词汇1", "词汇2"]
        }}
    ]
}}

要求：3-4个嫌疑人，5个场景。
所有文本内容必须用中文书写。'
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
    'mystery_scene', 1, 1, true,
    'Chinese mystery scene prose generation — prompt in Chinese',
    '请撰写谋杀悬疑故事的第{scene_number}场。

故事标题：{title}
场景设定：{setting}
需要涵盖的事件：{events}
需要包含的词汇：{vocab_words}

前几场概要：{previous_summary}

现在请用{language_name}撰写场景文本：'
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
    'mystery_question', 1, 1, true,
    'Chinese mystery scene MCQ generation — prompt in Chinese',
    '请为以下场景创建{num_questions}道阅读理解选择题：

场景文本：
{scene_text}

悬疑背景：{context}

请生成JSON格式的题目数组：
[
    {{
        "question_text": "用{language_name}写的问题",
        "choices": [
            {{"label": "A", "text": "选项A（{language_name}）"}},
            {{"label": "B", "text": "选项B（{language_name}）"}},
            {{"label": "C", "text": "选项C（{language_name}）"}},
            {{"label": "D", "text": "选项D（{language_name}）"}}
        ],
        "correct_answer": "正确选项的完整文本",
        "explanation": "简要解释为什么正确（{language_name}）",
        "question_type": "inference|vocabulary|literal"
    }}
]'
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
    'mystery_deduction', 1, 1, true,
    'Chinese mystery finale deduction question — prompt in Chinese',
    '请为谋杀悬疑故事的结局创建1道推理题。

学习者在5个场景中收集到以下线索：
{clues_summary}

嫌疑人：{suspects_summary}

正确答案是：{solution_suspect}

请生成包含1道题目的JSON数组，询问谁是凶手。
选项应为嫌疑人姓名。格式：
[
    {{
        "question_text": "根据证据，谁是凶手？",
        "choices": [
            {{"label": "A", "text": "嫌疑人1姓名"}},
            {{"label": "B", "text": "嫌疑人2姓名"}},
            {{"label": "C", "text": "嫌疑人3姓名"}},
            {{"label": "D", "text": "嫌疑人4姓名"}}
        ],
        "correct_answer": "正确嫌疑人的姓名",
        "explanation": "{solution_reasoning}",
        "question_type": "inference",
        "is_deduction": true
    }}
]'
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
    'mystery_clue', 1, 1, true,
    'Chinese mystery clue text generation — prompt in Chinese',
    '请为悬疑故事的第{scene_number}场设计线索：

故事标题：{title}
场景事件：{events}
线索类型：{clue_type}
大纲提示：{clue_hint}
真相：{solution_suspect}是凶手，因为：{solution_reasoning}

已揭示的线索：
{previous_clues}

请生成JSON：
{{
    "clue_text": "线索文本（1-2句中文）",
    "clue_type": "{clue_type}"
}}'
);


-- ============================================================================
-- JAPANESE (language_id = 3)
-- ============================================================================

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
    'mystery_plot', 3, 1, true,
    'Japanese mystery plot/story bible generation — prompt in Japanese',
    '言語学習プラットフォーム用の殺人ミステリーストーリー設定を作成してください。パラメータ：
- 言語：{language_name}
- CEFRレベル：{cefr_level}
- タイプ：{archetype}
- 含めるべき目標語彙：{target_vocab}

以下のJSON構造を生成してください：
{{
    "title": "日本語のミステリータイトル",
    "premise": "日本語の1-2文の背景設定",
    "suspects": [
        {{
            "name": "キャラクター名（日本語名）",
            "description": "簡潔なキャラクター説明（日本語）",
            "motive": "犯行動機（日本語）",
            "alibi": "アリバイ（日本語）"
        }}
    ],
    "solution": {{
        "suspect_name": "犯人の名前",
        "reasoning": "手がかりがどのように犯人を証明するか（2-3文の日本語）"
    }},
    "scenes": [
        {{
            "scene_number": 1,
            "title": "シーンタイトル（日本語）",
            "setting": "場所の説明（日本語）",
            "events": "このシーンで起こること（3-4文の日本語）",
            "clue_type": "evidence|alibi|testimony|forensic",
            "clue_hint": "ここで明らかになる手がかり（日本語）",
            "vocab_focus": ["単語1", "単語2"]
        }}
    ]
}}

容疑者は3-4人、シーンは5つ含めてください。
すべてのテキストは日本語で書いてください。'
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
    'mystery_scene', 3, 1, true,
    'Japanese mystery scene prose generation — prompt in Japanese',
    '殺人ミステリーの第{scene_number}シーンを書いてください。

ミステリータイトル：{title}
シーン設定：{setting}
含めるべき出来事：{events}
含めるべき語彙：{vocab_words}

これまでのシーンの要約：{previous_summary}

{language_name}でシーンのテキストを書いてください：'
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
    'mystery_question', 3, 1, true,
    'Japanese mystery scene MCQ generation — prompt in Japanese',
    '以下のシーンについて{num_questions}問の読解選択問題を作成してください：

シーンテキスト：
{scene_text}

ミステリーの文脈：{context}

以下のJSON形式で問題配列を生成してください：
[
    {{
        "question_text": "{language_name}での質問",
        "choices": [
            {{"label": "A", "text": "選択肢A（{language_name}）"}},
            {{"label": "B", "text": "選択肢B（{language_name}）"}},
            {{"label": "C", "text": "選択肢C（{language_name}）"}},
            {{"label": "D", "text": "選択肢D（{language_name}）"}}
        ],
        "correct_answer": "正解の選択肢の正確なテキスト",
        "explanation": "なぜ正解なのかの簡潔な説明（{language_name}）",
        "question_type": "inference|vocabulary|literal"
    }}
]'
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
    'mystery_deduction', 3, 1, true,
    'Japanese mystery finale deduction question — prompt in Japanese',
    '殺人ミステリーのフィナーレ用に推理問題を1問作成してください。

学習者が5つのシーンで集めた手がかり：
{clues_summary}

容疑者：{suspects_summary}

正解は：{solution_suspect}

犯人を問う1問のJSON配列を生成してください。
選択肢は容疑者の名前にしてください。形式：
[
    {{
        "question_text": "証拠に基づいて、犯人は誰ですか？",
        "choices": [
            {{"label": "A", "text": "容疑者1の名前"}},
            {{"label": "B", "text": "容疑者2の名前"}},
            {{"label": "C", "text": "容疑者3の名前"}},
            {{"label": "D", "text": "容疑者4の名前"}}
        ],
        "correct_answer": "正しい容疑者の名前",
        "explanation": "{solution_reasoning}",
        "question_type": "inference",
        "is_deduction": true
    }}
]'
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
    'mystery_clue', 3, 1, true,
    'Japanese mystery clue text generation — prompt in Japanese',
    'ミステリーの第{scene_number}シーンの手がかりを設計してください：

ミステリータイトル：{title}
シーンの出来事：{events}
手がかりの種類：{clue_type}
アウトラインのヒント：{clue_hint}
真相：{solution_suspect}が犯人です。理由：{solution_reasoning}

これまでに明らかになった手がかり：
{previous_clues}

JSONを生成してください：
{{
    "clue_text": "手がかりのテキスト（1-2文の日本語）",
    "clue_type": "{clue_type}"
}}'
);
