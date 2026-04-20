---
title: Conversation Generation — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./conversations.md
last_updated: 2026-04-10
dependencies:
  - "services/conversation_generation/"
  - "routes/conversations.py"
  - "OpenRouter (LLM)"
  - "scenarios table"
breaking_change_risk: low
---

# Conversation Generation — Technical Specification

## Architecture Overview

The conversation generation pipeline uses a multi-agent, tiered-LLM architecture. Scenario planning uses expensive models for reasoning; dialogue execution uses cheaper models for structured output.

```
Admin triggers generation
  → Stage 1: Scenario Matrix Builder (Pro/Opus tier)
    → Batch of 20-50 scenario seeds per domain
    → Ensures sub-topic variety and semantic field coverage

  → Stage 2: Scenario Expander (Mini/Flash tier)
    → Expands each seed into full scenario blueprint
    → Adds narrative_arc, context_description, goals, keywords

  → Stage 3: Conversation Generation (Mini/Flash tier)
    → PersonaDesigner agent → character creation
    → Pairing engine → persona matchmaking
    → TemplateGenerator → dialogue text with internal_monologue
    → QualityChecker → validation

  → Stage 4: Post-Processing
    → ConversationAnalyzer → vocab/grammar extraction
    → ExerciseAdapter → exercise material
    → Storage
```

## Scenario Generation (Upgraded)

### Step 1: Matrix Builder (Pro/Opus Tier)

Generates varied scenario seeds in batches. The expensive model sees all existing scenarios to guarantee variety and prevent mode collapse.

**Prompt template:**
```text
You are mapping out a language learning curriculum for the domain: "{domain_name}".
We currently have scenarios covering: [{list_of_existing_scenario_titles}].

Generate 20 completely new, highly varied conversation scenario seeds.
Focus on specific "Micro-Conflicts" or "Information Gaps."
Ensure a wide spread across sub-topics within the domain.

Return a JSON array of objects:
[{
  "title": "Short title",
  "core_conflict": "1-sentence description of the disagreement or information gap",
  "target_semantic_field": "3-5 specific vocabulary concepts this will elicit",
  "target_age_tier": "1-6 (Toddler/Primary Schooler/Young Teen/High Schooler/Uni Student/Educated Professional)",
  "required_register": "formal/informal/neutral",
  "required_relationship_type": "family/friends/strangers/colleagues/service"
}]
```

### Step 2: Scenario Expander (Mini/Flash Tier)

Each seed is expanded into a full scenario blueprint with narrative pacing.

**Prompt template:**
```text
You are an expert curriculum designer. Expand this scenario seed into a full blueprint for a {target_language} conversation.

Seed Data:
Title: {seed.title}
Conflict: {seed.core_conflict}
Target Concepts: {seed.target_semantic_field}
Age Tier: {seed.target_age_tier}
Register: {seed.required_register}
Relationship: {seed.required_relationship_type}

Available Archetypes: [{list_of_valid_archetypes}]

Return a JSON object with context_description and goals in {target_language}:
{
  "title": "...",
  "core_conflict": "...",
  "context_description": "2-3 sentences in {target_language}. MUST include a specific inciting incident.",
  "narrative_arc": [
    "Turn 1-2: [Setup]",
    "Turn 3-4: [Complication]",
    "Turn 5-6: [Resolution]"
  ],
  "goals": { "persona_a": "...", "persona_b": "..." },
  "keywords": ["word1", "word2", ...],
  "suitable_archetypes": ["archetype1", "archetype2"],
  "cultural_note": "...",
  "required_register": "...",
  "required_relationship_type": "...",
  "age_tier": "..."
}
```

### Step 3: Dialogue Generation (Mini/Flash Tier)

Uses narrative_arc and semantic_field for pacing and vocabulary control.

**Key prompt additions vs. original:**
- `narrative_arc` prevents rushing to resolution
- `semantic_field` provides soft vocabulary targeting (natural inclusion, not forced)
- `internal_monologue` per turn improves persona consistency (stripped before storage)
- Natural conversational fillers and hesitations explicitly allowed

## Database: Scenarios Table Additions

```sql
ALTER TABLE scenarios
ADD COLUMN core_conflict TEXT,
ADD COLUMN narrative_arc TEXT[];
```

These columns support the two-step generation pipeline and provide richer metadata for pack assembly.

## Service Layer

```
services/conversation_generation/
├── batch_processor.py        # Orchestrates batch generation
├── pairing.py                # Pairs personas for conversations
├── scenario_generator.py     # Creates conversation scenarios (upgraded)
├── template_generator.py     # Generates dialogue text
├── quality_checker.py        # Validates output quality
├── exercise_adapter.py       # Converts to exercise material
├── archetypes.py             # Character archetype definitions
├── categorical_maps.py       # Topic/style categorization
├── config.py                 # Generation settings
├── database_client.py        # DB operations
├── llm_client.py             # OpenRouter wrapper
└── agents/
    ├── persona_designer.py   # LLM agent: character creation
    ├── scenario_planner.py   # LLM agent: situation design
    └── conversation_analyzer.py  # LLM agent: content analysis
```

## LLM Tier Strategy

| Stage | Model Tier | Why |
|-------|-----------|-----|
| Scenario Matrix | Pro/Opus | Requires high reasoning for variety, sees full batch context |
| Scenario Expansion | Mini/Flash | Structured formatting task, low reasoning needed |
| Dialogue Generation | Mini/Flash | Executing a well-defined plan, not reasoning from scratch |
| Quality Check | Mini/Flash | Pattern matching against known quality criteria |
| Register Classification | Mini/Flash | Batched classification, simple taxonomy |

## Comprehension Question Generation

When generating questions from conversations for pack assessment:

**Prompt template (Mini/Flash tier):**
```text
Here is a conversation transcript. The learner is studying these specific domain terms found in the text: {target_vocabulary}.

Write 5 multiple-choice comprehension questions.
- 2 questions must test general understanding of the situation.
- 3 questions MUST test understanding of plot points revolving around the {target_vocabulary}.
- Do not ask for definitions. Ask questions where the correct answer proves contextual understanding.

Return JSON: [{ "question": "...", "options": ["...", "...", "...", "..."], "correct_index": 0, "tested_word_id": 123 }]
```

## API Surface

### `GET /api/conversations/list`
- **Purpose:** List available conversations for a language
- **Auth:** JWT required

### `GET /api/conversations/<id>`
- **Purpose:** Fetch conversation content
- **Auth:** JWT required

## Related Pages

- [[features/conversations]] — Prose description
- [[features/language-packs.tech]] — Pack integration
- [[features/corpus-analysis.tech]] — Post-generation analysis
