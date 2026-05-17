# tests/test_audio_synthesizer_ssml.py
"""Pure-function tests for the SSML helpers added in Phase 2.

These exercise the static methods only — no Azure SDK, no R2, no instance
construction needed. The class import goes through `azure.cognitiveservices.speech`
and boto3 at module level, but no credentials are required for static-method
access.
"""

import pytest

from services.test_generation.agents.audio_synthesizer import AudioSynthesizer


# ---------------------------------------------------------------------------
# _build_ssml — rate string correctness
# ---------------------------------------------------------------------------

class TestBuildSsmlRate:
    """The four target speeds map to the exact rate strings the plan calls for.

    Regression guard: a previous draft used int((speed - 1.0) * 100) which
    truncates toward zero. For speed=0.9 the float math gives -9.99999...
    so int() returns -9, producing '-9%' instead of '-10%'. round() must be
    used.
    """

    def test_slow_tier(self):
        ssml = AudioSynthesizer._build_ssml(
            'hello', 'en-US-AvaMultilingualNeural', 0.75
        )
        assert 'rate="-25%"' in ssml

    def test_slow_minus_ten_tier(self):
        ssml = AudioSynthesizer._build_ssml(
            'hello', 'en-US-AvaMultilingualNeural', 0.90
        )
        # The 0.9 case is the float-truncation trap — must be -10%, not -9%.
        assert 'rate="-10%"' in ssml
        assert 'rate="-9%"' not in ssml

    def test_unity_tier(self):
        ssml = AudioSynthesizer._build_ssml(
            'hello', 'en-US-AvaMultilingualNeural', 1.00
        )
        assert 'rate="+0%"' in ssml

    def test_fast_tier(self):
        ssml = AudioSynthesizer._build_ssml(
            'hello', 'en-US-AvaMultilingualNeural', 1.15
        )
        # 1.15 is the other float-truncation trap — 14.999... truncated is +14%.
        assert 'rate="+15%"' in ssml
        assert 'rate="+14%"' not in ssml


# ---------------------------------------------------------------------------
# _build_ssml — XML structure + escaping
# ---------------------------------------------------------------------------

class TestBuildSsmlStructure:
    """The SSML envelope is well-formed and routes text through XML escape."""

    def test_envelope_contains_voice_and_prosody(self):
        ssml = AudioSynthesizer._build_ssml(
            'hello', 'en-US-AvaMultilingualNeural', 0.75
        )
        assert ssml.startswith('<speak version="1.0" xml:lang="en-US">')
        assert '<voice name="en-US-AvaMultilingualNeural">' in ssml
        assert '<prosody rate="-25%">hello</prosody>' in ssml
        assert ssml.endswith('</voice></speak>')

    def test_text_is_xml_escaped(self):
        ssml = AudioSynthesizer._build_ssml(
            'Tom & Jerry <ran> away', 'en-US-AvaMultilingualNeural', 1.00
        )
        # The < and > and & characters must be escaped or Azure rejects the SSML.
        assert 'Tom &amp; Jerry &lt;ran&gt; away' in ssml
        assert '<ran>' not in ssml.replace('<prosody', '').replace('<voice', '').replace('<speak', '')

    def test_chinese_voice_yields_zh_cn_lang(self):
        ssml = AudioSynthesizer._build_ssml(
            'hello', 'zh-CN-XiaoxiaoNeural', 1.00
        )
        assert 'xml:lang="zh-CN"' in ssml

    def test_japanese_voice_yields_ja_jp_lang(self):
        ssml = AudioSynthesizer._build_ssml(
            'hello', 'ja-JP-NanamiNeural', 1.00
        )
        assert 'xml:lang="ja-JP"' in ssml


# ---------------------------------------------------------------------------
# _voice_to_lang
# ---------------------------------------------------------------------------

class TestVoiceToLang:
    """Voice-id parsing falls back gracefully on malformed input."""

    @pytest.mark.parametrize('voice,expected_lang', [
        ('en-US-AvaMultilingualNeural', 'en-US'),
        ('en-US-AndrewMultilingualNeural', 'en-US'),
        ('zh-CN-XiaoxiaoNeural', 'zh-CN'),
        ('ja-JP-NanamiNeural', 'ja-JP'),
        ('ko-KR-SunHiNeural', 'ko-KR'),
        ('fr-FR-DeniseNeural', 'fr-FR'),
    ])
    def test_well_formed_voices(self, voice, expected_lang):
        assert AudioSynthesizer._voice_to_lang(voice) == expected_lang

    def test_malformed_voice_falls_back_to_en_us(self):
        assert AudioSynthesizer._voice_to_lang('weird') == 'en-US'

    def test_empty_voice_falls_back_to_en_us(self):
        assert AudioSynthesizer._voice_to_lang('') == 'en-US'

    def test_none_voice_falls_back_to_en_us(self):
        # The implementation uses `(voice or "").split('-')` so None is safe.
        assert AudioSynthesizer._voice_to_lang(None) == 'en-US'
