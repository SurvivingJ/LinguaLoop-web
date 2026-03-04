# AudioSynthesizer Agent

**Source:** `services/test_generation/agents/audio_synthesizer.py` (~185 lines)

The `AudioSynthesizer` converts prose text to speech using Azure Cognitive Services Speech SDK, then uploads the resulting MP3 to Cloudflare R2 object storage. The public URL is stored on the test record for frontend playback.

## Class: `AudioSynthesizer`

### Constructor

```python
def __init__(self, speech_key=None, service_region=None, r2_config=None):
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `speech_key` | `str?` | Azure Speech Service subscription key (env: `SPEECH_KEY`) |
| `service_region` | `str?` | Azure region (env: `SPEECH_REGION`) |
| `r2_config` | `dict?` | R2 configuration with keys: `account_id`, `access_key_id`, `secret_access_key`, `bucket_name` |

R2 client is initialized via `boto3` with S3-compatible endpoint (`https://{account_id}.r2.cloudflarestorage.com`), signature version `s3v4`, region `auto`.

### Method: `generate_and_upload(text, file_id, voice, speed, model) -> str`

Generates TTS audio and uploads to R2.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `str` | Prose text to synthesize |
| `file_id` | `str` | UUID used as filename (without .mp3 extension) |
| `voice` | `str?` | Azure Neural Voice name (default: `en-US-AvaMultilingualNeural`) |
| `speed` | `float?` | Playback speed (currently unused by Azure SDK) |
| `model` | `str?` | Deprecated parameter |

**Returns:** `str` -- R2 public URL for the uploaded MP3.

**Process:**
1. Configures Azure `SpeechConfig` with subscription key, region, and voice name.
2. Sets output format to `Audio48Khz192KBitRateMonoMp3`.
3. Creates `SpeechSynthesizer` with `audio_config=None` (keeps audio data in memory).
4. Calls `speak_text_async(text).get()` for synchronous synthesis.
5. On success (`SynthesizingAudioCompleted`), extracts `audio_data` bytes.
6. Uploads to R2 via `_upload_to_r2()`.
7. Returns public URL from `Config.get_audio_url(file_id)`.

**Retry:** `@retry` with 3 attempts, exponential backoff (2-10 seconds).

### Method: `_upload_to_r2(slug, audio_data) -> bool`

Uploads binary audio data to the R2 bucket.

- Key: `{slug}.mp3`
- Content-Type: `audio/mpeg`
- Cache-Control: `public, max-age=31536000` (1 year)
- Metadata: `uploaded-by: test-generation`

### Method: `select_voice(voice_ids, language_code) -> str`

Selects a TTS voice for synthesis.

- If `voice_ids` is provided (from `dim_languages.tts_voice_ids`), randomly selects one for variety.
- Default voices (when none configured):
  - `en-US-AvaMultilingualNeural` (female)
  - `en-US-AndrewMultilingualNeural` (male)
  - `en-US-BrianMultilingualNeural` (deep male)
  - `en-US-EmmaMultilingualNeural` (professional female)

### Method: `check_audio_exists(slug) -> bool`

Checks if an audio file already exists in R2 via `head_object`.

### Method: `delete_audio(slug) -> bool`

Deletes an audio file from R2 via `delete_object`.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SPEECH_KEY` | Azure Speech Service subscription key |
| `SPEECH_REGION` | Azure Speech Service region (e.g., `eastus`) |
| `R2_ACCOUNT_ID` | Cloudflare R2 account ID |
| `R2_ACCESS_KEY_ID` | R2 access key |
| `R2_SECRET_ACCESS_KEY` | R2 secret key |
| `R2_BUCKET_NAME` | R2 bucket name (default: `linguadojoaudio`) |

---

### Related Documents

- [Pipeline Overview](../01-pipeline-overview.md)
- [Orchestrator](../02-orchestrator.md)
- [Configuration](../04-config.md)
