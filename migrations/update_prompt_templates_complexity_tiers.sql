-- Migration: Replace CEFR references in prompt templates with complexity tier system
-- Affects:
--   conversation_generation     v1 → v2 (adds tier + constraint, CoT, narrative arc, semantic field, register)
--   conversation_analysis       v1 → v2 (cefr_level → complexity_tier, estimated_cefr → estimated_tier)
--   scenario_batch_generation   v2 → v3 (cefr_level → complexity_tier, adds tier_legend)

BEGIN;

-- ── Deactivate old versions ────────────────────────────────────────────────

UPDATE prompt_templates SET is_active = false
WHERE task_name = 'conversation_generation' AND version = 1;

UPDATE prompt_templates SET is_active = false
WHERE task_name = 'conversation_analysis' AND version = 1;

UPDATE prompt_templates SET is_active = false
WHERE task_name = 'scenario_batch_generation' AND version = 2;

-- ── conversation_generation v2 ─────────────────────────────────────────────

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
  'conversation_generation', 1, 2, true,
  'v2: complexity tier + constraint, CoT internal monologue, narrative arc, semantic field, register',
  $$你正在为语言学习者生成两个人之间的自然对话。

只用中文回答。使用自然的普通话口语。

场景：{context_description}

角色A — {persona_a_name}：
{persona_a_system_prompt}

角色B — {persona_b_name}：
{persona_b_system_prompt}

{persona_a_name}的目标：{goal_persona_a}
{persona_b_name}的目标：{goal_persona_b}

复杂程度：{complexity_tier}
语言要求：{complexity_constraint}

语体：{register}

领域词汇（请自然融入对话）：{semantic_field}

{narrative_arc}

重要：在每一轮中，先用 `internal_monologue` 简要记录该说话者的感受和意图，再写 `text`。内心独白在入库前会被剔除。

生成一段自然的{turn_count}轮对话。每一轮都应符合角色的个性和语体。对话应自然朝着两个目标推进。

返回轮次对象的JSON数组：
[{{"turn": 0, "speaker": "{persona_a_name}", "persona_id": {persona_a_id}, "internal_monologue": "...", "text": "..."}}, ...]

交替发言。语言难度符合上述复杂程度要求。$$
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
  'conversation_generation', 2, 2, true,
  'v2: complexity tier + constraint, CoT internal monologue, narrative arc, semantic field, register',
  $$You are generating a natural conversation between two people for language learners.

Respond ONLY in English.

Scenario: {context_description}

Persona A — {persona_a_name}:
{persona_a_system_prompt}

Persona B — {persona_b_name}:
{persona_b_system_prompt}

Goal for {persona_a_name}: {goal_persona_a}
Goal for {persona_b_name}: {goal_persona_b}

Complexity: {complexity_tier}
Language constraint: {complexity_constraint}

Register: {register}

Domain vocabulary to weave in naturally: {semantic_field}

{narrative_arc}

IMPORTANT: For each turn, first write an `internal_monologue` briefly noting what this speaker feels and intends, then write the `text`. The internal monologue will be stripped before storage.

Generate a natural {turn_count}-turn conversation. Each turn should feel authentic to the persona's personality and register. The conversation should progress naturally toward both goals.

Return a JSON array of turn objects:
[{{"turn": 0, "speaker": "{persona_a_name}", "persona_id": {persona_a_id}, "internal_monologue": "...", "text": "..."}}, ...]

Alternate speakers. Match the language complexity level described above.$$
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
  'conversation_generation', 3, 2, true,
  'v2: complexity tier + constraint, CoT internal monologue, narrative arc, semantic field, register',
  $$あなたは語学学習者のために、二人の間の自然な会話を生成しています。

日本語のみで返答してください。自然な口語表現を使ってください。

シナリオ：{context_description}

ペルソナA — {persona_a_name}：
{persona_a_system_prompt}

ペルソナB — {persona_b_name}：
{persona_b_system_prompt}

{persona_a_name}の目標：{goal_persona_a}
{persona_b_name}の目標：{goal_persona_b}

複雑さレベル：{complexity_tier}
言語制約：{complexity_constraint}

レジスター：{register}

自然に織り込む分野の語彙：{semantic_field}

{narrative_arc}

重要：各ターンで、まず `internal_monologue` にこの話者の気持ちと意図を簡潔にメモし、それから `text` を書いてください。内部モノローグは保存前に削除されます。

自然な{turn_count}ターンの会話を生成してください。各ターンはペルソナの性格とレジスターに忠実であるべきです。会話は両方の目標に向かって自然に進むべきです。

ターンオブジェクトのJSON配列を返してください：
[{{"turn": 0, "speaker": "{persona_a_name}", "persona_id": {persona_a_id}, "internal_monologue": "...", "text": "..."}}, ...]

話者を交互にしてください。上記の複雑さレベルに合った日本語を使ってください。$$
);

-- ── conversation_analysis v2 ───────────────────────────────────────────────

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
  'conversation_analysis', 1, 2, true,
  'v2: complexity tier replaces CEFR; estimated_tier replaces estimated_cefr',
  $$分析这段对话的语言学习特征。

对话内容：
{conversation_text}

目标复杂程度等级：{complexity_tier}

提取：
1. vocabulary：值得注意的中文词汇/短语数组，附带词性标注
2. grammar_patterns：观察到的语法模式数组（尽可能使用模式代码）
3. register_markers：表示正式程度的词汇/短语数组
4. cultural_references：文化特定元素的数组
5. estimated_tier：你对实际复杂程度等级的估计（T1–T6）

返回一个包含以上5个键的JSON对象。$$
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
  'conversation_analysis', 2, 2, true,
  'v2: complexity tier replaces CEFR; estimated_tier replaces estimated_cefr',
  $$Analyze this conversation for language learning features.

Conversation:
{conversation_text}

Target complexity tier: {complexity_tier}

Extract:
1. vocabulary: Array of notable English words/phrases with POS tags
2. grammar_patterns: Array of grammar patterns observed (use pattern codes if possible)
3. register_markers: Array of words/phrases that indicate formality level
4. cultural_references: Array of culturally specific elements
5. estimated_tier: Your estimate of the actual complexity tier (T1–T6)

Return a single JSON object with these 5 keys.$$
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
  'conversation_analysis', 3, 2, true,
  'v2: complexity tier replaces CEFR; estimated_tier replaces estimated_cefr',
  $$この会話の語学学習特徴を分析してください。

会話内容：
{conversation_text}

目標複雑さ等級：{complexity_tier}

以下を抽出してください：
1. vocabulary：注目すべき日本語の単語/フレーズの配列（品詞タグ付き）
2. grammar_patterns：観察された文法パターンの配列（可能であればパターンコードを使用）
3. register_markers：フォーマリティレベルを示す単語/フレーズの配列
4. cultural_references：文化的に特有の要素の配列
5. estimated_tier：実際の複雑さ等級の推定（T1–T6）

上記5つのキーを含む単一のJSONオブジェクトを返してください。$$
);

-- ── scenario_batch_generation v3 ──────────────────────────────────────────

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
  'scenario_batch_generation', 1, 3, true,
  'v3: complexity tier replaces CEFR; adds tier_legend placeholder',
  $$你是一个语言学习应用的对话场景设计师。
所有生成内容的目标语言是：{language_name}。

为以下条件生成 {count} 个独特且真实的对话场景：
- 领域：{domain_name} — {domain_description}
- 领域关键词：{domain_keywords}
- 语言/文化：{language_name}
- 目标复杂程度等级：{complexity_tier}
- 适用语体：{suitable_registers}
- 适用关系类型：{suitable_relationship_types}

每个场景必须：
1. 对{language_name}母语者来说文化上真实可信——不是翻译的西方场景
2. 给每个说话者一个真正不同的目标、观点或情感立场
3. 足够具体，让说话者有实质性的分歧或探讨内容
4. 能够支撑10-14轮自然对话而不会缺少话题
5. 包含该领域自然出现的词汇和文化元素

关键要求：所有字符串值必须用中文。JSON输出中不要包含英文（等级代码和角色原型代码除外）。

复杂程度等级说明：
{tier_legend}

重要：不要重复以下已有的场景标题：
{existing_titles}

输出格式：严格使用数字键，按照以下对照表。

键值对照表：
"1" = 标题（用中文写的简短描述性标题）
"2" = 场景描述（2-3句中文描述场景背景）
"3" = 目标（对象，"1" = 说话者A的目标，"2" = 说话者B的目标，均用中文）
"4" = 关键词（5-8个中文词汇的数组）
"5" = 适用角色原型（从下方列表中选择2个原型代码的数组）
"6" = 要求的语体（从以下选项中选择一个：{suitable_registers}）
"7" = 要求的关系类型（从以下选项中选择一个：{suitable_relationship_types}）
"8" = 复杂程度等级（输出代码：{complexity_tier}，必须从T1–T6中选择）
"9" = 文化说明（用中文写一句话说明该场景中特有的文化元素）

只返回有效的JSON，使用以下结构：
{{
  "scenarios": [
    {{
      "1": "...",
      "2": "...",
      "3": {{"1": "...", "2": "..."}},
      "4": ["...", "...", "..."],
      "5": ["archetype_a", "archetype_b"],
      "6": "...",
      "7": "...",
      "8": "{complexity_tier}",
      "9": "..."
    }}
  ]
}}

有效的角色原型：protective_parent, rebellious_teen, supportive_sibling, wise_grandparent, nagging_relative, new_parent, hopeless_romantic, commitment_phobe, long_term_partner, jealous_partner, supportive_spouse, new_dater, loyal_best_friend, party_animal, wise_counselor, competitive_friend, ambitious_climber, burnt_out_worker, inspiring_mentor, strict_boss, new_employee, patient_service_worker, demanding_customer, helpful_neighbor, gossip_enthusiast, social_media_addict, community_organizer

确保每个场景彼此真正不同。避免笼统或老套的情境。场景应反映真实的中国社会生活。$$
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
  'scenario_batch_generation', 2, 3, true,
  'v3: complexity tier replaces CEFR; adds tier_legend placeholder',
  $$You are designing conversation scenarios for a language learning application.
The target language for ALL generated content is: {language_name}.

Generate {count} UNIQUE and REALISTIC conversation scenarios for:
- Domain: {domain_name} — {domain_description}
- Domain keywords: {domain_keywords}
- Language/Culture: {language_name}
- Target complexity tier: {complexity_tier}
- Suitable registers: {suitable_registers}
- Suitable relationship types: {suitable_relationship_types}

Each scenario must:
1. Be culturally authentic for {language_name} speakers — NOT a translated Western situation
2. Give each speaker a GENUINELY DIFFERENT goal, perspective, or emotional position
3. Be specific enough that the speakers have something real to disagree about or explore
4. Be able to sustain 10-14 turns of natural dialogue without running out of content
5. Contain vocabulary and cultural references natural to this domain

CRITICAL: ALL string values MUST be in {language_name}. Do NOT include other languages in the JSON output (except for tier codes and archetype codes).

Complexity tier reference:
{tier_legend}

IMPORTANT: Do NOT repeat any of these existing scenario titles:
{existing_titles}

OUTPUT FORMAT: Use STRICTLY NUMERIC KEYS according to this legend.

Key Legend:
"1" = Title (short descriptive title in {language_name})
"2" = Context Description (2-3 sentences setting the scene in {language_name})
"3" = Goals (object with "1" = speaker A goal, "2" = speaker B goal, both in {language_name})
"4" = Keywords (array of 5-8 {language_name} vocabulary words)
"5" = Suitable Archetypes (array of 2 archetype codes from the list below)
"6" = Required Register (choose exactly one from: {suitable_registers})
"7" = Required Relationship Type (choose exactly one from: {suitable_relationship_types})
"8" = Complexity Tier (output the code: {complexity_tier}, must be one of T1–T6)
"9" = Cultural Note (one sentence in {language_name} noting any culturally specific element)

Return ONLY valid JSON with this exact structure:
{{
  "scenarios": [
    {{
      "1": "...",
      "2": "...",
      "3": {{"1": "...", "2": "..."}},
      "4": ["...", "...", "..."],
      "5": ["archetype_a", "archetype_b"],
      "6": "...",
      "7": "...",
      "8": "{complexity_tier}",
      "9": "..."
    }}
  ]
}}

Valid archetypes: protective_parent, rebellious_teen, supportive_sibling, wise_grandparent, nagging_relative, new_parent, hopeless_romantic, commitment_phobe, long_term_partner, jealous_partner, supportive_spouse, new_dater, loyal_best_friend, party_animal, wise_counselor, competitive_friend, ambitious_climber, burnt_out_worker, inspiring_mentor, strict_boss, new_employee, patient_service_worker, demanding_customer, helpful_neighbor, gossip_enthusiast, social_media_addict, community_organizer

Make every scenario GENUINELY DIFFERENT from the others. Avoid generic or cliched situations.$$
);

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text)
VALUES (
  'scenario_batch_generation', 3, 3, true,
  'v3: complexity tier replaces CEFR; adds tier_legend placeholder',
  $$あなたは語学学習アプリの会話シナリオデザイナーです。
すべての生成コンテンツの対象言語は：{language_name}です。

以下の条件で{count}個のユニークでリアルな会話シナリオを生成してください：
- 分野：{domain_name} — {domain_description}
- 分野キーワード：{domain_keywords}
- 言語/文化：{language_name}
- 目標複雑さ等級：{complexity_tier}
- 適切なレジスター：{suitable_registers}
- 適切な関係タイプ：{suitable_relationship_types}

各シナリオの条件：
1. {language_name}話者にとって文化的に本物であること——西洋の場面を翻訳したものではないこと
2. 各話者に本当に異なる目標、視点、または感情的立場を与えること
3. 話者が本当に意見を交わしたり探求したりできるほど具体的であること
4. 10〜14ターンの自然な対話を維持できる内容であること
5. この分野に自然な語彙と文化的要素を含むこと

重要な要件：すべての文字列値は日本語で書いてください。JSON出力に英語を含めないでください（等級コードとアーキタイプコードを除く）。

複雑さ等級の説明：
{tier_legend}

重要：以下の既存のシナリオタイトルを繰り返さないでください：
{existing_titles}

出力形式：以下の凡例に従い、厳密に数字キーを使用してください。

キー凡例：
"1" = タイトル（日本語での簡潔な説明的タイトル）
"2" = 場面設定（日本語で2〜3文でシーンを設定）
"3" = 目標（オブジェクト、"1" = 話者Aの目標、"2" = 話者Bの目標、いずれも日本語）
"4" = キーワード（5〜8個の日本語の語彙の配列）
"5" = 適切なアーキタイプ（下記リストから2つのアーキタイプコードの配列）
"6" = 必要なレジスター（次の選択肢から1つ選択：{suitable_registers}）
"7" = 必要な関係タイプ（次の選択肢から1つ選択：{suitable_relationship_types}）
"8" = 複雑さ等級（コードを出力：{complexity_tier}、T1〜T6から選ぶこと）
"9" = 文化メモ（このシナリオに特有の文化的要素を日本語で一文で説明）

以下の構造で有効なJSONのみを返してください：
{{
  "scenarios": [
    {{
      "1": "...",
      "2": "...",
      "3": {{"1": "...", "2": "..."}},
      "4": ["...", "...", "..."],
      "5": ["archetype_a", "archetype_b"],
      "6": "...",
      "7": "...",
      "8": "{complexity_tier}",
      "9": "..."
    }}
  ]
}}

有効なアーキタイプ：protective_parent, rebellious_teen, supportive_sibling, wise_grandparent, nagging_relative, new_parent, hopeless_romantic, commitment_phobe, long_term_partner, jealous_partner, supportive_spouse, new_dater, loyal_best_friend, party_animal, wise_counselor, competitive_friend, ambitious_climber, burnt_out_worker, inspiring_mentor, strict_boss, new_employee, patient_service_worker, demanding_customer, helpful_neighbor, gossip_enthusiast, social_media_addict, community_organizer

各シナリオが本当に異なるようにしてください。ありふれた状況は避けてください。シナリオは日本社会の実際の生活を反映すべきです。$$
);

COMMIT;
