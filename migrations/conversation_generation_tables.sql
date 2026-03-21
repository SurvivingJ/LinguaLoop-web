-- ============================================================================
-- Conversation Generation Pipeline Schema Migration
-- Synthetic Corpus: Persona-driven multi-turn conversation generation
-- ============================================================================
-- Run this migration in Supabase SQL editor before deploying
-- the Python conversation generation services.
-- ============================================================================

-- ==========================================================================
-- 1. conversation_domains: topic domains for conversation generation
-- ==========================================================================

CREATE TABLE IF NOT EXISTS conversation_domains (
    id                          SERIAL PRIMARY KEY,
    category_id                 INTEGER REFERENCES categories(id),
    domain_name                 TEXT NOT NULL,
    description                 TEXT,
    keywords                    TEXT[] DEFAULT '{}',
    suitable_registers          TEXT[] DEFAULT '{}',
    suitable_relationship_types TEXT[] DEFAULT '{}',
    parent_domain               TEXT,
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conv_domains_active ON conversation_domains(is_active) WHERE is_active = TRUE;

-- ==========================================================================
-- 2. personas: AI character profiles for conversation generation
-- ==========================================================================

CREATE TABLE IF NOT EXISTS personas (
    id                  SERIAL PRIMARY KEY,
    name                TEXT NOT NULL,
    language_id         INTEGER NOT NULL REFERENCES dim_languages(id),
    age                 INTEGER CHECK (age BETWEEN 18 AND 80),
    gender              TEXT,
    nationality         TEXT,
    occupation          TEXT,
    archetype           TEXT NOT NULL,
    personality         JSONB NOT NULL DEFAULT '{}',
    register            TEXT CHECK (register IN ('formal','semi-formal','informal')),
    expertise_domains   TEXT[] DEFAULT '{}',
    relationship_types  TEXT[] DEFAULT '{}',
    system_prompt       TEXT NOT NULL,
    generation_method   TEXT NOT NULL CHECK (generation_method IN ('llm','template')),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_personas_language ON personas(language_id);
CREATE INDEX IF NOT EXISTS idx_personas_archetype ON personas(archetype);
CREATE INDEX IF NOT EXISTS idx_personas_register ON personas(register);
CREATE INDEX IF NOT EXISTS idx_personas_active ON personas(is_active) WHERE is_active = TRUE;

-- ==========================================================================
-- 3. persona_pairs: compatibility-scored pairings
-- ==========================================================================

CREATE TABLE IF NOT EXISTS persona_pairs (
    id                  SERIAL PRIMARY KEY,
    persona_a_id        INTEGER NOT NULL REFERENCES personas(id),
    persona_b_id        INTEGER NOT NULL REFERENCES personas(id),
    compatibility_score NUMERIC(3,2) DEFAULT 0.50,
    relationship_type   TEXT,
    dynamic_label       TEXT,
    suitable_domains    TEXT[] DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (persona_a_id, persona_b_id)
);

CREATE INDEX IF NOT EXISTS idx_pairs_persona_a ON persona_pairs(persona_a_id);
CREATE INDEX IF NOT EXISTS idx_pairs_persona_b ON persona_pairs(persona_b_id);

-- ==========================================================================
-- 4. scenarios: conversation contexts with per-persona goals
-- ==========================================================================

CREATE TABLE IF NOT EXISTS scenarios (
    id                          SERIAL PRIMARY KEY,
    domain_id                   INTEGER NOT NULL REFERENCES conversation_domains(id),
    language_id                 INTEGER NOT NULL REFERENCES dim_languages(id),
    title                       TEXT NOT NULL,
    context_description         TEXT NOT NULL,
    goals                       JSONB NOT NULL DEFAULT '{}',
    required_register           TEXT,
    required_relationship_type  TEXT,
    cefr_level                  TEXT CHECK (cefr_level IN ('A1','A2','B1','B2','C1','C2')),
    keywords                    TEXT[] DEFAULT '{}',
    suitable_archetypes         TEXT[] DEFAULT '{}',
    cultural_note               TEXT,
    generation_method           TEXT NOT NULL CHECK (generation_method IN ('llm','template')),
    is_validated                BOOLEAN NOT NULL DEFAULT FALSE,
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scenarios_domain   ON scenarios(domain_id);
CREATE INDEX IF NOT EXISTS idx_scenarios_language  ON scenarios(language_id);
CREATE INDEX IF NOT EXISTS idx_scenarios_cefr      ON scenarios(cefr_level);
CREATE INDEX IF NOT EXISTS idx_scenarios_active    ON scenarios(is_active) WHERE is_active = TRUE;

-- ==========================================================================
-- 5. conversations: generated multi-turn dialogues
-- ==========================================================================

CREATE TABLE IF NOT EXISTS conversations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id             INTEGER NOT NULL REFERENCES scenarios(id),
    persona_pair_id         INTEGER NOT NULL REFERENCES persona_pairs(id),
    language_id             INTEGER NOT NULL REFERENCES dim_languages(id),
    model_used              TEXT NOT NULL,
    temperature             NUMERIC(3,2) NOT NULL,
    turn_count              INTEGER NOT NULL,
    turns                   JSONB NOT NULL,
    corpus_features         JSONB DEFAULT '{}',
    quality_score           NUMERIC(3,2),
    passed_qc               BOOLEAN NOT NULL DEFAULT FALSE,
    generation_batch_id     UUID,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conv_scenario    ON conversations(scenario_id);
CREATE INDEX IF NOT EXISTS idx_conv_language    ON conversations(language_id);
CREATE INDEX IF NOT EXISTS idx_conv_pair        ON conversations(persona_pair_id);
CREATE INDEX IF NOT EXISTS idx_conv_batch       ON conversations(generation_batch_id);
CREATE INDEX IF NOT EXISTS idx_conv_passed_qc   ON conversations(passed_qc);
CREATE INDEX IF NOT EXISTS idx_conv_active      ON conversations(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_conv_turns_gin   ON conversations USING GIN (turns);

-- ==========================================================================
-- 6. conversation_generation_queue: pipeline processing queue
-- ==========================================================================

CREATE TABLE IF NOT EXISTS conversation_generation_queue (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id                 INTEGER NOT NULL REFERENCES scenarios(id),
    persona_pair_id             INTEGER NOT NULL REFERENCES persona_pairs(id),
    language_id                 INTEGER NOT NULL REFERENCES dim_languages(id),
    status_id                   INTEGER NOT NULL DEFAULT 1 REFERENCES dim_status(id),
    conversations_generated     INTEGER DEFAULT 0,
    error_log                   TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at                TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_conv_queue_status ON conversation_generation_queue(status_id);
CREATE INDEX IF NOT EXISTS idx_conv_queue_lang   ON conversation_generation_queue(language_id);

-- ==========================================================================
-- 7. Extend exercises table: add 'conversation' source type + FK
-- ==========================================================================

ALTER TYPE exercise_source_type ADD VALUE IF NOT EXISTS 'conversation';

ALTER TABLE exercises ADD COLUMN IF NOT EXISTS conversation_id UUID REFERENCES conversations(id);

CREATE INDEX IF NOT EXISTS idx_exercises_conversation ON exercises(conversation_id) WHERE conversation_id IS NOT NULL;

-- Recreate the source FK constraint to include conversation_id
ALTER TABLE exercises DROP CONSTRAINT IF EXISTS chk_source_fk;
ALTER TABLE exercises ADD CONSTRAINT chk_source_fk CHECK (
    (grammar_pattern_id IS NOT NULL)::INT +
    (word_sense_id IS NOT NULL)::INT +
    (corpus_collocation_id IS NOT NULL)::INT +
    (conversation_id IS NOT NULL)::INT = 1
);

-- ==========================================================================
-- 8. dim_languages extension: conversation model column
-- ==========================================================================

ALTER TABLE dim_languages
    ADD COLUMN IF NOT EXISTS conversation_model TEXT;

UPDATE dim_languages SET
    conversation_model = 'google/gemini-2.0-flash-001'
WHERE id IN (1, 2, 3)
  AND conversation_model IS NULL;

-- ==========================================================================
-- 9. Prompt templates for conversation generation
-- One row per (task_name, language_id). Prompts are written in the
-- target language so the LLM responds in that language.
-- ==========================================================================

-- ---- conversation_persona_design ----------------------------------------

INSERT INTO prompt_templates (task_name, language_id, version, template_text, description) VALUES
('conversation_persona_design', 2, 1,
 'You are designing a persona for a language learning conversation system.

Domain: {domain_name}
Register: {register}
CEFR Level: {cefr_level}

Generate a detailed persona with the following fields:
- name: A culturally appropriate English name
- age: Between 18 and 80
- gender: male, female, or neutral
- nationality: An English-speaking nationality
- occupation: Related to the domain
- archetype: One of [professional, student, parent, elder, service_worker, creative, academic]
- personality: Object with keys: traits (array of 3-5 traits), speaking_style, quirks
- expertise_domains: Array of 2-3 domains of knowledge
- relationship_types: Array of suitable relationship types
- system_prompt: A 2-3 sentence character instruction for the LLM, written in English

Return a single JSON object with all fields above.',
 'Design an English-speaking persona for conversation generation')
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, language_id, version, template_text, description) VALUES
('conversation_persona_design', 1, 1,
 '你是一个语言学习对话系统的角色设计师。

领域：{domain_name}
语体：{register}
CEFR等级：{cefr_level}

请生成一个详细的中文角色，包含以下字段：
- name：一个文化上合适的中文名字
- age：18到80之间
- gender：male、female或neutral
- nationality：中国
- occupation：与领域相关的职业
- archetype：以下之一 [professional, student, parent, elder, service_worker, creative, academic]
- personality：对象，包含 traits（3-5个性格特征的数组）、speaking_style、quirks
- expertise_domains：2-3个擅长领域的数组
- relationship_types：适合的关系类型数组
- system_prompt：用中文写的2-3句角色指令

返回一个JSON对象，包含以上所有字段。',
 '为对话生成设计一个中文角色')
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, language_id, version, template_text, description) VALUES
('conversation_persona_design', 3, 1,
 'あなたは語学学習会話システムのペルソナデザイナーです。

分野：{domain_name}
レジスター：{register}
CEFRレベル：{cefr_level}

以下のフィールドを含む詳細なペルソナを生成してください：
- name：文化的に適切な日本語の名前
- age：18歳から80歳
- gender：male、female、またはneutral
- nationality：日本
- occupation：分野に関連する職業
- archetype：次のいずれか [professional, student, parent, elder, service_worker, creative, academic]
- personality：traits（3〜5つの性格特性の配列）、speaking_style、quirksを含むオブジェクト
- expertise_domains：2〜3つの専門分野の配列
- relationship_types：適切な関係タイプの配列
- system_prompt：日本語で書かれた2〜3文のキャラクター指示

上記すべてのフィールドを含む単一のJSONオブジェクトを返してください。',
 '会話生成用の日本語ペルソナを設計する')
ON CONFLICT DO NOTHING;

-- ---- conversation_scenario_plan -----------------------------------------

INSERT INTO prompt_templates (task_name, language_id, version, template_text, description) VALUES
('conversation_scenario_plan', 2, 1,
 'You are planning a conversation scenario for language learners.

Domain: {domain_name} — {domain_description}
Persona A: {persona_a_summary}
Persona B: {persona_b_summary}
Relationship: {relationship_type}
Register: {register}
CEFR Level: {cefr_level}

Generate a conversation scenario with:
- title: A short descriptive title in English
- context_description: 2-3 sentences setting the scene in English
- goals: Object with persona_a and persona_b keys, each a 1-sentence goal in English
- keywords: Array of 5-8 English vocabulary items likely to appear
- cultural_note: Optional note about cultural context (null if not applicable)

Return a single JSON object.',
 'Plan an English conversation scenario')
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, language_id, version, template_text, description) VALUES
('conversation_scenario_plan', 1, 1,
 '你是一个为语言学习者规划对话场景的助手。

领域：{domain_name} — {domain_description}
角色A：{persona_a_summary}
角色B：{persona_b_summary}
关系：{relationship_type}
语体：{register}
CEFR等级：{cefr_level}

请生成一个对话场景，包含：
- title：简短的中文标题
- context_description：用中文写的2-3句场景描述
- goals：包含persona_a和persona_b键的对象，每个是一句中文目标
- keywords：5-8个可能出现的中文词汇数组
- cultural_note：关于文化背景的可选说明（如不适用则为null）

返回一个JSON对象。',
 '规划中文对话场景')
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, language_id, version, template_text, description) VALUES
('conversation_scenario_plan', 3, 1,
 'あなたは語学学習者のための会話シナリオを計画する助手です。

分野：{domain_name} — {domain_description}
ペルソナA：{persona_a_summary}
ペルソナB：{persona_b_summary}
関係：{relationship_type}
レジスター：{register}
CEFRレベル：{cefr_level}

以下を含む会話シナリオを生成してください：
- title：日本語の短い説明的なタイトル
- context_description：日本語で書かれた2〜3文の場面設定
- goals：persona_aとpersona_bキーを含むオブジェクト、それぞれ日本語の1文の目標
- keywords：出現しそうな日本語の語彙5〜8個の配列
- cultural_note：文化的背景に関するオプションのメモ（該当しない場合はnull）

単一のJSONオブジェクトを返してください。',
 '日本語の会話シナリオを計画する')
ON CONFLICT DO NOTHING;

-- ---- conversation_generation --------------------------------------------

INSERT INTO prompt_templates (task_name, language_id, version, template_text, description) VALUES
('conversation_generation', 2, 1,
 'You are generating a natural conversation between two people for language learners.

Respond ONLY in English.

Scenario: {context_description}

Persona A — {persona_a_name}:
{persona_a_system_prompt}

Persona B — {persona_b_name}:
{persona_b_system_prompt}

Goal for {persona_a_name}: {goal_persona_a}
Goal for {persona_b_name}: {goal_persona_b}

Generate a natural {turn_count}-turn conversation. Each turn should feel authentic to the persona''s personality and register. The conversation should progress naturally toward both goals.

Return a JSON array of turn objects:
[{{"turn": 0, "speaker": "{persona_a_name}", "persona_id": {persona_a_id}, "text": "..."}}, ...]

Alternate speakers. Use natural English at {cefr_level} level.',
 'Generate a multi-turn English conversation')
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, language_id, version, template_text, description) VALUES
('conversation_generation', 1, 1,
 '你正在为语言学习者生成两个人之间的自然对话。

只用中文回答。使用自然的普通话口语。

场景：{context_description}

角色A — {persona_a_name}：
{persona_a_system_prompt}

角色B — {persona_b_name}：
{persona_b_system_prompt}

{persona_a_name}的目标：{goal_persona_a}
{persona_b_name}的目标：{goal_persona_b}

生成一段自然的{turn_count}轮对话。每一轮都应该符合角色的个性和语体。对话应该自然地朝着两个目标推进。

返回一个JSON数组，包含轮次对象：
[{{"turn": 0, "speaker": "{persona_a_name}", "persona_id": {persona_a_id}, "text": "..."}}, ...]

交替发言。使用{cefr_level}水平的自然中文。',
 '生成多轮中文对话')
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, language_id, version, template_text, description) VALUES
('conversation_generation', 3, 1,
 'あなたは語学学習者のために、二人の間の自然な会話を生成しています。

日本語のみで返答してください。自然な口語表現を使ってください。

シナリオ：{context_description}

ペルソナA — {persona_a_name}：
{persona_a_system_prompt}

ペルソナB — {persona_b_name}：
{persona_b_system_prompt}

{persona_a_name}の目標：{goal_persona_a}
{persona_b_name}の目標：{goal_persona_b}

自然な{turn_count}ターンの会話を生成してください。各ターンはペルソナの性格とレジスターに忠実であるべきです。会話は両方の目標に向かって自然に進むべきです。

ターンオブジェクトのJSON配列を返してください：
[{{"turn": 0, "speaker": "{persona_a_name}", "persona_id": {persona_a_id}, "text": "..."}}, ...]

話者を交互にしてください。{cefr_level}レベルの自然な日本語を使ってください。',
 '多ターンの日本語会話を生成する')
ON CONFLICT DO NOTHING;

-- ---- conversation_analysis ----------------------------------------------

INSERT INTO prompt_templates (task_name, language_id, version, template_text, description) VALUES
('conversation_analysis', 2, 1,
 'Analyze this conversation for language learning features.

Conversation:
{conversation_text}

Target CEFR level: {cefr_level}

Extract:
1. vocabulary: Array of notable English words/phrases with POS tags
2. grammar_patterns: Array of grammar patterns observed (use pattern codes if possible)
3. register_markers: Array of words/phrases that indicate formality level
4. cultural_references: Array of culturally specific elements
5. estimated_cefr: Your estimate of the actual difficulty level

Return a single JSON object with these 5 keys.',
 'Analyze an English conversation for learning features')
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, language_id, version, template_text, description) VALUES
('conversation_analysis', 1, 1,
 '分析这段对话的语言学习特征。

对话内容：
{conversation_text}

目标CEFR等级：{cefr_level}

提取：
1. vocabulary：值得注意的中文词汇/短语数组，附带词性标注
2. grammar_patterns：观察到的语法模式数组（尽可能使用模式代码）
3. register_markers：表示正式程度的词汇/短语数组
4. cultural_references：文化特定元素的数组
5. estimated_cefr：你对实际难度级别的估计

返回一个包含以上5个键的JSON对象。',
 '分析中文对话的学习特征')
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, language_id, version, template_text, description) VALUES
('conversation_analysis', 3, 1,
 'この会話の語学学習特徴を分析してください。

会話内容：
{conversation_text}

目標CEFRレベル：{cefr_level}

以下を抽出してください：
1. vocabulary：注目すべき日本語の単語/フレーズの配列（品詞タグ付き）
2. grammar_patterns：観察された文法パターンの配列（可能であればパターンコードを使用）
3. register_markers：フォーマリティレベルを示す単語/フレーズの配列
4. cultural_references：文化的に特有の要素の配列
5. estimated_cefr：実際の難易度レベルの推定

上記5つのキーを含む単一のJSONオブジェクトを返してください。',
 '日本語会話の学習特徴を分析する')
ON CONFLICT DO NOTHING;
