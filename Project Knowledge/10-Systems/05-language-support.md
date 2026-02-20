# Language Support

## Supported Languages

| ID | Code | Name | Display |
|----|------|------|---------|
| 1 | cn | chinese | Chinese |
| 2 | en | english | English |
| 3 | jp | japanese | Japanese |

## Per-Language LLM Models (OpenRouter)

| Language | Transcript Model | Question Model |
|----------|-----------------|----------------|
| English | google/gemini-2.0-flash-001 | google/gemini-2.0-flash-001 |
| Chinese | deepseek/deepseek-chat | deepseek/deepseek-chat |
| Japanese | qwen/qwen-2.5-72b-instruct | qwen/qwen-2.5-72b-instruct |

## Per-Language TTS Voices

Configured in `dim_languages.tts_voice_ids` (JSONB). Azure Neural Voices.

## Language-Specific Prompt Templates

- **title_generation**: Separate templates for English, Chinese, Japanese
- **Other prompts**: English fallback with `{language}` placeholder

## Config Sources

- **`Config.LANGUAGES`**: Static mapping in `config.py`
- **`Config.AI_MODELS`**: Model selection per language
- **`dim_languages` table**: Dynamic config (TTS voices, model overrides, speed)
- **`DimensionService`**: Cached runtime lookups

## Related Documents

- [04-audio-pipeline.md](04-audio-pipeline.md) - TTS voice selection and audio generation
- [06-cefr-difficulty-mapping.md](06-cefr-difficulty-mapping.md) - Per-language title length guidelines
- [01-elo-rating-system.md](01-elo-rating-system.md) - Per-language ELO ratings
