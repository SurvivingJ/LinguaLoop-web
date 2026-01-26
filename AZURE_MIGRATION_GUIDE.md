# Azure Speech Services Migration Guide

## Overview
The `audio_synthesizer.py` module has been successfully migrated from OpenAI TTS to Microsoft Azure Speech Services.

---

## ✅ Completed Changes

### 1. Code Refactoring
- **File**: `services/test_generation/agents/audio_synthesizer.py`
- Replaced OpenAI SDK with Azure Cognitive Services Speech SDK
- Updated voice selection to use Azure Neural Voices
- Modified audio generation to use Azure Speech Synthesizer

### 2. Dependencies Updated
- **File**: `requirements.txt`
- **Removed**: `openai==1.99.3`
- **Added**: `azure-cognitiveservices-speech==1.40.0`

### 3. Voice Mapping
OpenAI voices have been replaced with Azure Neural Voices:

| Previous (OpenAI) | New (Azure) | Description |
|------------------|-------------|-------------|
| alloy, echo, fable, etc. | en-US-AvaMultilingualNeural | Balanced female |
| - | en-US-AndrewMultilingualNeural | Balanced male |
| - | en-US-BrianMultilingualNeural | Deep male |
| - | en-US-EmmaMultilingualNeural | Professional female |

---

## 🔧 Required Setup Steps

### Step 1: Install Azure Speech SDK
Run the following command to install the new dependency:

```bash
pip install -r requirements.txt
```

### Step 2: Create Azure Speech Service Resource
1. Go to [Azure Portal](https://portal.azure.com)
2. Create a new "Speech Services" resource
3. Choose a region (e.g., `eastus`, `westeurope`, `australiaeast`)
4. Copy the following values:
   - **Key**: Found under "Keys and Endpoint" → KEY 1
   - **Region**: The location you selected during creation

### Step 3: Update Environment Variables
Add the following to your `.env` file:

```env
# Azure Speech Services
SPEECH_KEY=your_azure_speech_key_here
SPEECH_REGION=your_region_here  # e.g., eastus

# Optional: Remove if not used elsewhere
# OPENAI_API_KEY=...
```

### Step 4: Verify Configuration
The system will log a warning if credentials are missing:
```
WARNING: Azure Speech Service credentials not configured - TTS will fail
```

---

## 📝 API Changes

### Constructor Parameters
**Before (OpenAI)**:
```python
synthesizer = AudioSynthesizer(
    openai_api_key="sk-..."
)
```

**After (Azure)**:
```python
synthesizer = AudioSynthesizer(
    speech_key="your_key",
    service_region="eastus"
)
```

### Voice Names
**Before**: `voice="alloy"`
**After**: `voice="en-US-AvaMultilingualNeural"`

### Deprecated Parameters
- `speed`: Azure SDK doesn't support speed adjustment in the same way
- `model`: Azure uses voice names directly instead of models

---

## 🎯 Key Implementation Details

### Audio Format
- Output format: **MP3** (48kHz, 192kbps, Mono)
- This ensures web compatibility and reasonable file sizes

### Memory Streaming
- Uses `audio_config=None` to keep audio data in memory
- Prevents the SDK from attempting to play audio on server speakers

### Error Handling
- Comprehensive error checking with Azure-specific error messages
- Retry logic preserved (3 attempts with exponential backoff)

### R2 Upload
- No changes to R2 upload logic
- Same bucket, same file naming convention
- Same public URL generation

---

## 🧪 Testing Checklist

After setup, verify the following:

- [ ] Environment variables are set correctly
- [ ] Azure Speech SDK is installed (`pip list | grep azure`)
- [ ] Audio generation works without errors
- [ ] Generated MP3 files are valid and playable
- [ ] Files are successfully uploaded to R2
- [ ] Public URLs are accessible
- [ ] Audio quality meets expectations

---

## 💰 Cost Comparison

### OpenAI TTS
- **Pricing**: ~$15 per 1M characters
- **Models**: tts-1, tts-1-hd

### Azure Speech Services
- **Free Tier**: 500K characters/month
- **Standard Pricing**: ~$16 per 1M characters
- **Neural Voices**: Premium quality included in standard pricing

---

## 🔍 Troubleshooting

### Import Error: `azure.cognitiveservices.speech`
**Solution**: Install the package
```bash
pip install azure-cognitiveservices-speech==1.40.0
```

### Error: "Invalid subscription key"
**Solution**: Verify `SPEECH_KEY` in `.env` is correct

### Error: "Invalid region"
**Solution**: Check that `SPEECH_REGION` matches your Azure resource region

### Audio Quality Issues
**Solution**: Try different neural voices or adjust the output format in the code

---

## 📚 Additional Resources

- [Azure Speech Services Documentation](https://docs.microsoft.com/azure/cognitive-services/speech-service/)
- [Azure Neural Voice Gallery](https://speech.microsoft.com/portal/voicegallery)
- [Pricing Calculator](https://azure.microsoft.com/pricing/details/cognitive-services/speech-services/)

---

## 🚀 Next Steps

1. Complete the setup steps above
2. Test audio generation with a sample test
3. Monitor Azure usage in the Azure Portal
4. Consider implementing voice selection based on language/topic
5. Delete this guide once migration is verified

---

**Migration completed**: January 26, 2026
**Status**: ✅ Code complete, environment setup required
