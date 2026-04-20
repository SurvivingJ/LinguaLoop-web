---
title: Corpus Analysis
type: feature
status: in-progress
tech_page: ./corpus-analysis.tech.md
last_updated: 2026-04-10
open_questions: []
---

# Corpus Analysis

## Purpose

The corpus analysis system ingests text sources and extracts linguistic features — collocations, frequency data, style patterns — that feed into exercise generation and vocabulary tracking. It transforms raw language data into structured learning material.

## User Story

From the system perspective: when conversations are generated or text sources are ingested, the corpus pipeline tokenizes the text, identifies statistically significant word combinations (collocations), analyzes style and register, and stores the results for use by the exercise generator.

## How It Works

1. Text is ingested from a source (generated conversation, imported document).
2. Language-specific tokenizer processes the text (jieba for Chinese, MeCab/unidic for Japanese, standard NLP for European languages).
3. N-grams are extracted and scored:
   - **PMI (Pointwise Mutual Information)** — how much more often words co-occur than expected by chance
   - **Log-likelihood** — statistical significance of co-occurrence
   - **t-score** — another co-occurrence significance measure
4. POS patterns are identified (e.g., ADJ+NOUN, VERB+NOUN).
5. Collocations are stored in `corpus_collocations` and can be grouped into packs.
6. Style analysis identifies register, formality, and domain characteristics.

## Business Rules

- Collocations must meet minimum PMI thresholds to be considered significant.
- Collocation packs group related collocations by theme for exercise generation.

## Related Pages

- [[features/corpus-analysis.tech]] — Technical specification
- [[features/language-packs]] — Packs built from corpus analysis
- [[features/exercises]] — Exercises generated from collocations
