"""The furigana token stream must be a lossless copy of the input text.

MeCab returns no node for whitespace, so the "\\n\\n" between paragraphs used
to vanish from the payload. The prestudy page places readings by character
offset into the transcript, so every reading after a paragraph break landed
two characters early (えさ over 度 instead of 餌).
"""

from types import SimpleNamespace

import pytest

from services import furigana_service
from services.furigana_service import process_passage


def _joined(tokens):
    return "".join(t["base"] if t["kind"] == "ruby" else t["text"] for t in tokens)


class _FakeWord:
    def __init__(self, surface, kana=None):
        self.surface = surface
        self.feature = SimpleNamespace(kana=kana, pron=None)


def _fake_tagger(words):
    return lambda text: iter(words)


@pytest.fixture
def fake_tagger(monkeypatch):
    def install(words):
        monkeypatch.setattr(furigana_service, "_get_tagger", lambda: _fake_tagger(words))
    return install


def test_paragraph_break_is_kept_as_plain_token(fake_tagger):
    text = "ます。\n\n温度や餌"
    fake_tagger([
        _FakeWord("ます"), _FakeWord("。"),
        _FakeWord("温度", "オンド"), _FakeWord("や"), _FakeWord("餌", "エサ"),
    ])
    tokens = process_passage(text)
    assert _joined(tokens) == text
    assert {"kind": "plain", "text": "\n\n"} in tokens
    # 餌 starts at the same offset in the tokens as in the text.
    offset = 0
    for t in tokens:
        if t.get("base") == "餌":
            break
        offset += len(t["base"] if t["kind"] == "ruby" else t["text"])
    assert offset == text.index("餌")


def test_leading_inner_and_trailing_whitespace(fake_tagger):
    text = "  鶏 の　飼育\n"
    fake_tagger([
        _FakeWord("鶏", "ニワトリ"), _FakeWord("の"), _FakeWord("飼育", "シイク"),
    ])
    assert _joined(process_passage(text)) == text


def test_no_whitespace_unchanged(fake_tagger):
    fake_tagger([_FakeWord("温度", "オンド"), _FakeWord("や")])
    tokens = process_passage("温度や")
    assert [t["kind"] for t in tokens] == ["ruby", "plain"]


def test_real_tagger_round_trips_paragraphs():
    pytest.importorskip("fugashi")
    try:
        furigana_service._get_tagger()
    except Exception as e:  # no UniDic dictionary installed
        pytest.skip(f"MeCab dictionary unavailable: {e}")
    text = "役割を果たしています。\n\n鶏の飼育は、温度や餌が厳密に調整された環境で行われます。"
    tokens = process_passage(text)
    assert len(tokens) > 1  # not the single-token tokenizer-failure fallback
    assert _joined(tokens) == text
    assert any(t.get("base") == "餌" for t in tokens)
