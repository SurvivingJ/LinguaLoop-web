---
title: Corpus Analysis — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./corpus-analysis.md
last_updated: 2026-04-10
dependencies:
  - "corpus_sources table"
  - "corpus_collocations table"
  - "collocation_packs table"
  - "pack_collocations table"
  - "services/corpus/"
breaking_change_risk: low
---

# Corpus Analysis — Technical Specification

## Service Layer

```
services/corpus/
├── ingestion.py              # Text ingestion pipeline
├── tokenizers.py             # Language-specific tokenization
├── analyzer.py               # N-gram extraction + statistical scoring
├── collocation_tagger.py     # POS pattern identification
├── collocation_validator.py  # Quality filtering
├── classifier.py             # Text classification
├── style_analyzer.py         # Register/formality analysis
├── style_narrative.py        # Narrative style features
├── style_pack_service.py     # Style-based pack creation
├── pack_service.py           # Pack CRUD operations
├── llm_client.py             # LLM for analysis tasks
├── constants.py              # Thresholds, parameters
├── verifier.py               # Output verification
├── tasks.py                  # Background task definitions
└── run_corpus_processing.py  # CLI entry point
```

## Database Impact

- `corpus_sources` — one row per ingested text source
- `corpus_collocations` — extracted n-grams with PMI/LL/t-score, linked to source + language
- `collocation_packs` — named groups with metadata (type, tags, difficulty_range)
- `pack_collocations` — many-to-many join

## Key Database Functions

- `get_top_collocations_for_sources(source_ids[], min_pmi, top_n)` — ranked collocation retrieval
- `get_packs_with_user_selection(language_id, user_id)` — pack list with user selection state

## API Surface

- `GET /api/corpus/packs` — list packs with user selection state
- `POST /api/corpus/packs/select` — toggle pack selection

## Related Pages

- [[features/corpus-analysis]] — Prose description
- [[database/schema.tech]] — Table DDL
