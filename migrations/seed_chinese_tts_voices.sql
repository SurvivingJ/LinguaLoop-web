-- ============================================================================
-- Seed Azure neural voices for Chinese and English in dim_languages
-- Date: 2026-05-12
--
-- The current `tts_voice_ids` default (`["alloy","echo","fable","onyx","nova",
-- "shimmer"]`) is the OpenAI TTS voice catalog. The runtime synthesizer at
-- services/test_generation/agents/audio_synthesizer.py is Azure Speech, so
-- those English voice names are silently ignored — Azure falls back to its
-- hardcoded default `en-US-AvaMultilingualNeural`. Chinese (language_id=1)
-- has no voices set at all, so it would also fall back to the English voice
-- (Vocab Dojo L1 played English audio for Chinese learners — the bug we're
-- fixing).
--
-- Updates:
--   id=1 (Chinese):  3 Azure Mandarin neural voices.
--   id=2 (English):  4 Azure English multilingual neural voices.
--
-- The WHERE clause is idempotent: only overwrites OpenAI-format defaults or
-- empty configs, never an operator-curated voice list.
-- ============================================================================

BEGIN;

UPDATE public.dim_languages
   SET tts_voice_ids = '[
           "zh-CN-XiaoxiaoMultilingualNeural",
           "zh-CN-YunxiNeural",
           "zh-CN-YunyangNeural"
       ]'::jsonb,
       tts_speed = 1.0
 WHERE id = 1
   AND (
       tts_voice_ids IS NULL
       OR tts_voice_ids = '[]'::jsonb
       OR tts_voice_ids @> '["alloy"]'::jsonb
   );

UPDATE public.dim_languages
   SET tts_voice_ids = '[
           "en-US-AvaMultilingualNeural",
           "en-US-AndrewMultilingualNeural",
           "en-US-BrianMultilingualNeural",
           "en-US-EmmaMultilingualNeural"
       ]'::jsonb,
       tts_speed = COALESCE(tts_speed, 1.0)
 WHERE id = 2
   AND (
       tts_voice_ids IS NULL
       OR tts_voice_ids = '[]'::jsonb
       OR tts_voice_ids @> '["alloy"]'::jsonb
   );

COMMIT;
