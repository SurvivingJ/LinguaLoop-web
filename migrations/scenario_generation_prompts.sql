-- ============================================================
-- Prompt templates for batch scenario generation
-- Task: scenario_batch_generation
-- Languages: 1=Chinese, 2=English, 3=Japanese
-- ============================================================

-- English (language_id=2)
INSERT INTO prompt_templates (task_name, language_id, version, template_text, description) VALUES
('scenario_batch_generation', 2, 1,
 'You are designing conversation scenarios for a language learning application.

Generate {count} UNIQUE and REALISTIC conversation scenarios for:
- Domain: {domain_name} — {domain_description}
- Domain keywords: {domain_keywords}
- Language/Culture: {language_name}
- Target CEFR difficulty: {cefr_level}
- Suitable registers: {suitable_registers}
- Suitable relationship types: {suitable_relationship_types}

Each scenario must:
1. Be culturally authentic for {language_name} speakers — NOT a translated Western situation
2. Give each speaker a GENUINELY DIFFERENT goal, perspective, or emotional position
3. Be specific enough that the speakers have something real to disagree about or explore
4. Be able to sustain 10-14 turns of natural dialogue without running out of content
5. Contain vocabulary and cultural references natural to this domain

IMPORTANT: Do NOT repeat any of these existing scenario titles:
{existing_titles}

Return ONLY valid JSON with this exact structure:
{{
  "scenarios": [
    {{
      "title": "Short descriptive title in English",
      "context_description": "2-3 sentences setting the scene. Where are they? What is the situation?",
      "goals": {{
        "persona_a": "What does speaker A want to achieve or resolve?",
        "persona_b": "What does speaker B want — and how does it differ from A?"
      }},
      "keywords": ["word1", "word2", "word3", "word4", "word5", "word6"],
      "suitable_archetypes": ["archetype_a", "archetype_b"],
      "required_register": "one of: {suitable_registers}",
      "required_relationship_type": "one of: {suitable_relationship_types}",
      "cefr_level": "{cefr_level}",
      "cultural_note": "One sentence noting any culturally specific element."
    }}
  ]
}}

Valid archetypes: protective_parent, rebellious_teen, supportive_sibling, wise_grandparent, nagging_relative, new_parent, hopeless_romantic, commitment_phobe, long_term_partner, jealous_partner, supportive_spouse, new_dater, loyal_best_friend, party_animal, wise_counselor, competitive_friend, ambitious_climber, burnt_out_worker, inspiring_mentor, strict_boss, new_employee, patient_service_worker, demanding_customer, helpful_neighbor, gossip_enthusiast, social_media_addict, community_organizer

Make every scenario GENUINELY DIFFERENT from the others. Avoid generic or cliched situations.',
 'Batch scenario generation prompt for English conversations');

-- Chinese (language_id=1)
INSERT INTO prompt_templates (task_name, language_id, version, template_text, description) VALUES
('scenario_batch_generation', 1, 1,
 '你是一个语言学习应用的对话场景设计师。

为以下条件生成 {count} 个独特且真实的对话场景：
- 领域：{domain_name} — {domain_description}
- 领域关键词：{domain_keywords}
- 语言/文化：{language_name}
- 目标CEFR难度：{cefr_level}
- 适用语体：{suitable_registers}
- 适用关系类型：{suitable_relationship_types}

每个场景必须：
1. 对{language_name}母语者来说文化上真实可信——不是翻译的西方场景
2. 给每个说话者一个真正不同的目标、观点或情感立场
3. 足够具体，让说话者有实质性的分歧或探讨内容
4. 能够支撑10-14轮自然对话而不会缺少话题
5. 包含该领域自然出现的词汇和文化元素

重要：不要重复以下已有的场景标题：
{existing_titles}

只返回有效的JSON，使用以下结构：
{{
  "scenarios": [
    {{
      "title": "简短的英文描述性标题",
      "context_description": "2-3句中文描述场景。他们在哪里？是什么情况？",
      "goals": {{
        "persona_a": "说话者A想要达成或解决什么？",
        "persona_b": "说话者B想要什么——与A有何不同？"
      }},
      "keywords": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5", "关键词6"],
      "suitable_archetypes": ["archetype_a", "archetype_b"],
      "required_register": "{suitable_registers}中的一个",
      "required_relationship_type": "{suitable_relationship_types}中的一个",
      "cefr_level": "{cefr_level}",
      "cultural_note": "一句话说明该场景中特有的中国文化元素。"
    }}
  ]
}}

有效的角色原型：protective_parent, rebellious_teen, supportive_sibling, wise_grandparent, nagging_relative, new_parent, hopeless_romantic, commitment_phobe, long_term_partner, jealous_partner, supportive_spouse, new_dater, loyal_best_friend, party_animal, wise_counselor, competitive_friend, ambitious_climber, burnt_out_worker, inspiring_mentor, strict_boss, new_employee, patient_service_worker, demanding_customer, helpful_neighbor, gossip_enthusiast, social_media_addict, community_organizer

确保每个场景彼此真正不同。避免笼统或老套的情境。场景应反映真实的中国社会生活。',
 'Batch scenario generation prompt for Chinese conversations');

-- Japanese (language_id=3)
INSERT INTO prompt_templates (task_name, language_id, version, template_text, description) VALUES
('scenario_batch_generation', 3, 1,
 'あなたは語学学習アプリの会話シナリオデザイナーです。

以下の条件で{count}個のユニークでリアルな会話シナリオを生成してください：
- 分野：{domain_name} — {domain_description}
- 分野キーワード：{domain_keywords}
- 言語/文化：{language_name}
- 目標CEFRレベル：{cefr_level}
- 適切なレジスター：{suitable_registers}
- 適切な関係タイプ：{suitable_relationship_types}

各シナリオの条件：
1. {language_name}話者にとって文化的に本物であること——西洋の場面を翻訳したものではないこと
2. 各話者に本当に異なる目標、視点、または感情的立場を与えること
3. 話者が本当に意見を交わしたり探求したりできるほど具体的であること
4. 10〜14ターンの自然な対話を維持できる内容であること
5. この分野に自然な語彙と文化的要素を含むこと

重要：以下の既存のシナリオタイトルを繰り返さないでください：
{existing_titles}

以下の構造で有効なJSONのみを返してください：
{{
  "scenarios": [
    {{
      "title": "英語での簡潔な説明的タイトル",
      "context_description": "2-3文で日本語でシーンを設定。彼らはどこにいますか？状況は何ですか？",
      "goals": {{
        "persona_a": "話者Aは何を達成または解決したいですか？",
        "persona_b": "話者Bは何を望んでいますか——Aとどう違いますか？"
      }},
      "keywords": ["単語1", "単語2", "単語3", "単語4", "単語5", "単語6"],
      "suitable_archetypes": ["archetype_a", "archetype_b"],
      "required_register": "{suitable_registers}のいずれか",
      "required_relationship_type": "{suitable_relationship_types}のいずれか",
      "cefr_level": "{cefr_level}",
      "cultural_note": "このシナリオに特有の日本文化の要素を一文で説明。"
    }}
  ]
}}

有効なアーキタイプ：protective_parent, rebellious_teen, supportive_sibling, wise_grandparent, nagging_relative, new_parent, hopeless_romantic, commitment_phobe, long_term_partner, jealous_partner, supportive_spouse, new_dater, loyal_best_friend, party_animal, wise_counselor, competitive_friend, ambitious_climber, burnt_out_worker, inspiring_mentor, strict_boss, new_employee, patient_service_worker, demanding_customer, helpful_neighbor, gossip_enthusiast, social_media_addict, community_organizer

各シナリオが本当に異なるようにしてください。ありふれた状況は避けてください。シナリオは日本社会の実際の生活を反映すべきです。',
 'Batch scenario generation prompt for Japanese conversations');
