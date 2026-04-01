-- ============================================================
-- Update scenario_batch_generation prompts to v2 (numeric keys)
--
-- Inserts new version 2 prompt templates that use numeric JSON
-- keys to prevent English leaking into target-language output.
-- The latest version is automatically picked up by
-- get_prompt_template() which orders by version DESC.
-- ============================================================

-- English (language_id=2)
INSERT INTO prompt_templates (task_name, language_id, version, template_text, description) VALUES
('scenario_batch_generation', 2, 2,
 'You are designing conversation scenarios for a language learning application.
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
"8" = Complexity Tier (output the code: {complexity_tier})
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

Make every scenario GENUINELY DIFFERENT from the others. Avoid generic or cliched situations.',
 'Batch scenario generation prompt for English conversations (v2 numeric keys)')
ON CONFLICT DO NOTHING;

-- Chinese (language_id=1)
INSERT INTO prompt_templates (task_name, language_id, version, template_text, description) VALUES
('scenario_batch_generation', 1, 2,
 '你是一个语言学习应用的对话场景设计师。
所有生成内容的目标语言是：{language_name}。

为以下条件生成 {count} 个独特且真实的对话场景：
- 领域：{domain_name} — {domain_description}
- 领域关键词：{domain_keywords}
- 语言/文化：{language_name}
- 目标难度层级：{complexity_tier}
- 适用语体：{suitable_registers}
- 适用关系类型：{suitable_relationship_types}

每个场景必须：
1. 对{language_name}母语者来说文化上真实可信——不是翻译的西方场景
2. 给每个说话者一个真正不同的目标、观点或情感立场
3. 足够具体，让说话者有实质性的分歧或探讨内容
4. 能够支撑10-14轮自然对话而不会缺少话题
5. 包含该领域自然出现的词汇和文化元素

关键要求：所有字符串值必须用中文。JSON输出中不要包含英文（难度层级代码和角色原型代码除外）。

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
"8" = 难度层级（输出代码：{complexity_tier}）
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

确保每个场景彼此真正不同。避免笼统或老套的情境。场景应反映真实的中国社会生活。',
 'Batch scenario generation prompt for Chinese conversations (v2 numeric keys)')
ON CONFLICT DO NOTHING;

-- Japanese (language_id=3)
INSERT INTO prompt_templates (task_name, language_id, version, template_text, description) VALUES
('scenario_batch_generation', 3, 2,
 'あなたは語学学習アプリの会話シナリオデザイナーです。
すべての生成コンテンツの対象言語は：{language_name}です。

以下の条件で{count}個のユニークでリアルな会話シナリオを生成してください：
- 分野：{domain_name} — {domain_description}
- 分野キーワード：{domain_keywords}
- 言語/文化：{language_name}
- 目標難易度ティア：{complexity_tier}
- 適切なレジスター：{suitable_registers}
- 適切な関係タイプ：{suitable_relationship_types}

各シナリオの条件：
1. {language_name}話者にとって文化的に本物であること——西洋の場面を翻訳したものではないこと
2. 各話者に本当に異なる目標、視点、または感情的立場を与えること
3. 話者が本当に意見を交わしたり探求したりできるほど具体的であること
4. 10〜14ターンの自然な対話を維持できる内容であること
5. この分野に自然な語彙と文化的要素を含むこと

重要な要件：すべての文字列値は日本語で書いてください。JSON出力に英語を含めないでください（難易度ティアコードとアーキタイプコードを除く）。

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
"8" = 難易度ティア（コードを出力：{complexity_tier}）
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

各シナリオが本当に異なるようにしてください。ありふれた状況は避けてください。シナリオは日本社会の実際の生活を反映すべきです。',
 'Batch scenario generation prompt for Japanese conversations (v2 numeric keys)')
ON CONFLICT DO NOTHING;
