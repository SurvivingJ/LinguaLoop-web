---
title: Language Packs — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./language-packs.md
last_updated: 2026-04-10
dependencies:
  - "services/conversation_generation/"
  - "services/exercise_generation/"
  - "services/corpus/"
  - "services/vocabulary/"
  - "services/vocabulary_ladder/"
  - "services/study_packs/ (to be created)"
  - "collocation_packs table (to be evolved or replaced)"
breaking_change_risk: high
open_questions:
  - "Pack completion criteria — exact thresholds for mastery tiers"
  - "Refresh strategy — how to handle new conversations added to existing packs"
---

# Language Packs — Technical Specification

## Architecture Overview

Language Packs follow a **Corpus-First** architecture: conversations are generated naturally, then linguistic features are extracted post-hoc to build the curriculum. This avoids "Franken-text" (conversations unnaturally stuffed with target vocabulary).

```
Pack Generation Pipeline (admin-triggered, multi-stage):

Stage 1: Scenario Matrix (Pro/Opus tier LLM)
  → Generates 20-50 varied scenario seeds per domain batch
  → Ensures sub-topic variety, semantic field coverage
  → Input: domain, existing scenario titles (to avoid overlap)
  → Output: [{title, core_conflict, target_semantic_field, age_tier, register, relationship}]

Stage 2: Scenario Expansion (Mini/Flash tier LLM)
  → Expands each seed into full scenario blueprint
  → Output: {context_description, narrative_arc[], goals, keywords[], archetypes, cultural_note}
  → Stored in scenarios table with core_conflict and narrative_arc columns

Stage 3: Conversation Generation (existing pipeline)
  → PersonaDesigner → ScenarioPlanner → TemplateGenerator → QualityChecker
  → Uses narrative_arc for pacing control
  → Uses semantic_field for vocabulary targeting (soft constraints)
  → Stores in conversations table

Stage 4: Corpus Analysis (NLP + LLM)
  → Supabase text analysis plugin for in-database NLP
  → Extract lemmas, POS tags, collocations (PMI/log-likelihood)
  → LLM register classification (standard/colloquial/slang/idiom) via Mini tier
  → Cross-reference with dim_word_senses for sense disambiguation

Stage 5: Pack Assembly (database logic, no LLM)
  → Frequency aggregation: items appearing in 3+ conversations
  → Top 50-80 items form Core Vocabulary of the pack
  → Conversation designation based on word coverage proportion:
    - High coverage of target words → snippet/mini-test material
    - Low coverage (natural distribution) → final assessment conversations
  → Create pack record + junction tables

Stage 6: Exercise Generation (vocabulary ladder pipeline)
  → For each key word sense, run 3-prompt pipeline:
    Prompt 1 (Gemini Flash Lite): definition, collocate, 6 sentences
    Prompt 2 (Claude Sonnet): lexical/semantic exercises (L1,3,5,6)
    Prompt 3 (Claude Sonnet): grammar/structural exercises (L4,7,8)
  → Store as immutable exercise assets

Stage 7: Comprehension Question Generation (Mini/Flash tier)
  → For full conversations: 5 MCQ questions
  → Questions must target pack vocabulary in context (not generic details)
  → For snippets: 2-4 targeted questions per excerpt
```

## Database Design

### New/Modified Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `study_packs` | Master pack record | `id, domain_id, language_id, pack_name, description, pack_type, item_count, status, created_at` |
| `study_pack_items` | Individual extracted items | `id, language_id, item_category (vocab/collocation/colloquialism/grammar_pattern), item_text, item_data (JSONB), source_conversation_ids (UUID[]), frequency_across_conversations, age_tier, sort_order` |
| `pack_study_items` | Junction: pack ↔ items | `pack_id, study_item_id` |
| `pack_conversations` | Junction: pack ↔ conversations | `pack_id, conversation_id, role (study/snippet/assessment), word_coverage_pct` |
| `user_pack_progress` | User progression state | `user_id, pack_id, mastery_tier (novice/familiar/proficient/mastered), words_studied, words_mastered, last_session_at` |

### Alterations to Existing Tables

- `scenarios`: Add `core_conflict TEXT`, `narrative_arc TEXT[]`
- `exercises`: Add `study_pack_item_id BIGINT FK study_pack_items (nullable)`
- `tests`: Add `study_pack_id BIGINT FK study_packs (nullable)`

## Key Services

### StudyPackExtractor (`services/study_packs/extractor.py`)
- `extract_from_domain(domain_id, language_id) → list[dict]`
- Queries QC-passed conversations, reads corpus_features JSONB
- Aggregates and deduplicates by normalized key (lemma+POS for vocab, text for collocations)
- Counts frequency across conversations, collects source_conversation_ids

### ColloquialismClassifier (`services/study_packs/colloquialism_classifier.py`)
- `classify(items, language_id) → list[dict]`
- LLM-based register classification (standard/colloquial/slang/idiom)
- Batched calls (~50 items per call to avoid output limit issues)

### StudyPackService (`services/study_packs/pack_service.py`)
- `create_pack_from_domain(domain_id, language_id, pack_name, description) → pack_id`
- `refresh_pack(pack_id) → int` — re-extract from latest conversations
- `get_pack_items(pack_id, item_category=None) → list[dict]`
- `designate_conversations(pack_id)` — assigns roles based on word coverage

### StudyPackExerciseAdapter (`services/study_packs/exercise_adapter.py`)
- Builds sentence pools from pack items for exercise generation
- Finds original conversation turns containing each item
- Tags sentences with source='study_pack' and study_pack_item_id

## Runtime: Pack Study Orchestrator

```python
class PackStudyOrchestrator:
    def build_session(self, user_id, pack_id, session_size=20):
        """
        1. Load pack items + user's BKT state for each
        2. Select 5-8 words with lowest concept ELO / not yet seen
        3. Find best conversation from pack's content pool
           (covers most target words, rest are known to user)
        4. Build session: primer exercises → snippet exercises → conversation test
        5. Return ordered exercise queue
        """

    def process_result(self, user_id, exercise_id, is_correct, is_first_attempt):
        """
        1. Update BKT for word sense
        2. Update vocabulary ladder position (promote/demote based on first-attempt)
        3. Update pack mastery tier
        4. If comprehension test: update global ELO
        """
```

## Pack Mastery Calculation

```
mastery_score = weighted_average(concept_elos)
  where weight = 1 / (concept_elo - floor)  # lowest-performing words weighted most

Tier mapping:
  mastery_score < 0.3 → Novice
  mastery_score < 0.6 → Familiar
  mastery_score < 0.85 → Proficient
  mastery_score >= 0.85 → Mastered

Mastery decays slowly over time (FSRS scheduling) — users can return to re-master.
```

## Admin Pipeline Dashboard

The admin interface serves as the manual trigger for pack generation pipelines. Requirements:
- Complete pipeline integration with clear stage progression
- Debugging stats: successes/failures/stages of the pipeline
- Ability to spot-check generated content (conversations, exercises, pack items)
- Manual trigger for each pipeline stage independently
- Batch processing status and error logs

## API / RPC Surface

### `POST /api/study-packs`
- **Purpose:** Create pack from domain
- **Auth:** Admin required
- **Body:** `{domain_id, language_id, pack_name, description}`

### `GET /api/study-packs`
- **Purpose:** List study packs (with user progress if authenticated)
- **Auth:** JWT optional (enriches with user progress)

### `POST /api/study-packs/<id>/refresh`
- **Purpose:** Re-extract from latest conversations
- **Auth:** Admin required

### `POST /api/study-packs/<id>/generate-exercises`
- **Purpose:** Trigger exercise generation for pack items
- **Auth:** Admin required

### `POST /api/study-packs/<id>/generate-tests`
- **Purpose:** Trigger comprehension test generation from pack conversations
- **Auth:** Admin required

### `GET /api/study-packs/<id>/session`
- **Purpose:** Get next study session for user
- **Auth:** JWT required
- **Returns:** Ordered exercise queue with primer + snippet + test items

## Key Architectural Decisions

1. **Corpus-First, not Lexicon-First**
   - Rationale: Conversations generated naturally produce authentic language. Vocabulary extracted post-hoc ensures natural frequency distribution.
   - Alternatives rejected: Forcing target vocabulary into generated text ("Franken-text") — produces unnatural language.

2. **Inverted density logic for conversation designation**
   - Rationale: High density of target words = scaffolding (snippets). Low density (natural) = authentic assessment (final tests). Based on Nation's lexical coverage research: learners need 95-98% known words for unassisted comprehension.
   - Alternatives rejected: High density for final tests — produces unnatural text, measures working memory not comprehension.

3. **Independent study_packs table (not reusing collocation_packs)**
   - Rationale: Study packs are broader than collocation packs. Reusing collocation_packs introduces leaky abstraction and risks cascading data loss on refresh.

4. **Two-step scenario generation (Matrix → Expansion)**
   - Rationale: Single-LLM generation of 100 scenarios causes mode collapse and output limit failures. Matrix approach guarantees variety; expansion handles formatting cheaply.

## Related Pages

- [[features/language-packs]] — Prose description
- [[algorithms/vocabulary-ladder]] — Exercise ladder spec
- [[features/conversations.tech]] — Conversation generation pipeline
- [[features/exercises.tech]] — Exercise generation
- [[features/corpus-analysis.tech]] — Corpus pipeline
- [[features/vocabulary-knowledge.tech]] — BKT integration
- [[database/schema.tech]] — Full schema
