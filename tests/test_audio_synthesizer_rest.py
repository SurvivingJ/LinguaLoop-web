"""AudioSynthesizer REST transport (AZURE_TTS_TRANSPORT=rest)."""

import pytest

from services.test_generation.agents.audio_synthesizer import AudioSynthesizer


class _Resp:
    def __init__(self, status_code=200, content=b'ID3fake'):
        self.status_code = status_code
        self.content = content


@pytest.fixture
def synth(monkeypatch):
    monkeypatch.setattr(AudioSynthesizer, '_initialize_r2_client', lambda self: None)
    s = AudioSynthesizer(speech_key='k', service_region='australiaeast', r2_config={})
    uploads = []
    monkeypatch.setattr(s, '_upload_to_r2', lambda fid, data: uploads.append((fid, data)) or True)
    s.uploads = uploads
    return s


def test_transport_defaults_to_sdk(monkeypatch):
    monkeypatch.delenv('AZURE_TTS_TRANSPORT', raising=False)
    assert AudioSynthesizer._tts_transport() == 'sdk'
    monkeypatch.setenv('AZURE_TTS_TRANSPORT', 'bogus')
    assert AudioSynthesizer._tts_transport() == 'sdk'
    monkeypatch.setenv('AZURE_TTS_TRANSPORT', ' REST ')
    assert AudioSynthesizer._tts_transport() == 'rest'


def test_rest_posts_ssml_and_uploads(monkeypatch, synth):
    import httpx
    calls = []

    def fake_post(url, content, headers, timeout):
        calls.append((url, content.decode('utf-8'), headers))
        return _Resp()

    monkeypatch.setenv('AZURE_TTS_TRANSPORT', 'rest')
    monkeypatch.setattr(httpx, 'post', fake_post)
    monkeypatch.setattr('config.Config.get_audio_url', staticmethod(lambda fid: f'https://a/{fid}.mp3'))

    url = synth.generate_and_upload('猫 & 犬', 'abc', voice='ja-JP-NanamiNeural')

    assert url == 'https://a/abc.mp3'
    assert synth.uploads == [('abc', b'ID3fake')]
    (post_url, ssml, headers), = calls
    assert post_url == 'https://australiaeast.tts.speech.microsoft.com/cognitiveservices/v1'
    assert 'xml:lang="ja-JP"' in ssml and 'name="ja-JP-NanamiNeural"' in ssml
    assert '猫 &amp; 犬' in ssml and 'prosody' not in ssml
    assert headers['X-Microsoft-OutputFormat'] == 'audio-48khz-192kbitrate-mono-mp3'


def test_rest_uses_prosody_for_speed(monkeypatch, synth):
    import httpx
    seen = []
    monkeypatch.setenv('AZURE_TTS_TRANSPORT', 'rest')
    monkeypatch.setattr(httpx, 'post', lambda url, content, headers, timeout: seen.append(content.decode()) or _Resp())
    monkeypatch.setattr('config.Config.get_audio_url', staticmethod(lambda fid: fid))
    synth.generate_and_upload('テスト', 'x', voice='ja-JP-NanamiNeural', speed=0.9)
    assert '<prosody rate="-10%">' in seen[0]


def test_rest_http_error_raises(monkeypatch, synth):
    import httpx
    monkeypatch.setenv('AZURE_TTS_TRANSPORT', 'rest')
    monkeypatch.setattr(httpx, 'post', lambda url, content, headers, timeout: _Resp(status_code=401))
    with pytest.raises(Exception, match='HTTP 401'):
        AudioSynthesizer._synthesize_rest(synth, 'テスト', 'ja-JP-NanamiNeural', None, 'x')
    assert synth.uploads == []
