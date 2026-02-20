# CEFR Difficulty Mapping

## CEFR to Difficulty Mapping

| CEFR | Difficulty | Word Count | Initial ELO | Question Type Focus |
|------|-----------|------------|-------------|-------------------|
| A1 | 1-2 | 80-150 | 875 | Literal detail, vocabulary |
| A2 | 3-4 | 120-200 | 1175 | Literal detail, vocabulary, main idea |
| B1 | 5 | 200-300 | 1400 | Vocabulary, main idea, supporting detail |
| B2 | 6 | 300-400 | 1550 | Main idea, supporting detail, inference |
| C1 | 7 | 400-600 | 1700 | Supporting detail, inference, author purpose |
| C2 | 8-9 | 600-900 | 1925 | Inference, author purpose |

## Question Type Distribution (per difficulty)

| Difficulty | Q1 | Q2 | Q3 | Q4 | Q5 |
|-----------|----|----|----|----|-----|
| 1 | literal_detail | literal_detail | vocabulary_context | vocabulary_context | main_idea |
| 2 | literal_detail | literal_detail | vocabulary_context | vocabulary_context | main_idea |
| 3 | literal_detail | vocabulary_context | vocabulary_context | main_idea | supporting_detail |
| 4 | literal_detail | vocabulary_context | main_idea | supporting_detail | supporting_detail |
| 5 | vocabulary_context | main_idea | main_idea | supporting_detail | inference |
| 6 | vocabulary_context | main_idea | supporting_detail | inference | inference |
| 7 | main_idea | supporting_detail | supporting_detail | inference | author_purpose |
| 8 | main_idea | supporting_detail | inference | inference | author_purpose |
| 9 | supporting_detail | inference | inference | author_purpose | author_purpose |

## Question Types (6 types, 3 cognitive levels)

1. **Literal Detail** (Level 1): Direct facts from text
2. **Vocabulary in Context** (Level 1): Word/phrase meaning
3. **Main Idea** (Level 2): Central theme
4. **Supporting Detail** (Level 2): Evidence/examples
5. **Inference** (Level 3): Implicit conclusions
6. **Author Purpose/Tone** (Level 3): Writing intent/attitude

## Title Length Guidelines (from prompt templates)

| CEFR | English (words) | Chinese (chars) | Japanese (chars) |
|------|----------------|-----------------|------------------|
| A1 | 3-6 | 5-10 | 5-12 |
| A2 | 4-8 | 8-15 | 8-16 |
| B1 | 5-10 | 10-18 | 10-20 |
| B2 | 6-12 | 12-22 | 12-25 |
| C1 | 8-15 | 15-28 | 15-30 |
| C2 | 10-18 | 18-35 | 18-35 |

## Related Documents

- [01-elo-rating-system.md](01-elo-rating-system.md) - Initial ELO values derived from CEFR levels
- [05-language-support.md](05-language-support.md) - Language-specific title length guidelines
- [04-audio-pipeline.md](04-audio-pipeline.md) - Transcript word counts tied to difficulty
