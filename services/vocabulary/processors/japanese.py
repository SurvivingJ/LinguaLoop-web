"""
Japanese Processor — fugashi + UniDic

Segments and lemmatizes Japanese text using fugashi (MeCab wrapper)
with the UniDic-lite dictionary.

UniDic's 'lemma' field returns dictionary forms:
    '食べました' → '食べる'
    '走っている' → '走る'

But 'lemma' identifies the abstract *lexeme*, not the orthography: UniDic
groups kanji variants that share an etymology and reading under one lemma,
e.g. both 速い ("fast") and 早い ("early") lemmatize to the same headword
even though they are different words with different definitions. Using
'lemma' directly for vocab/dictionary lookups conflates them — a click on
速い would resolve to the sense generated for 早い. 'orthBase' preserves
the actual kanji used (still conjugation-normalized: 食べました → 食べる)
so it is used in preference to 'lemma', which is only a fallback for
tokens where orthBase is unavailable.

That preference inverts, however, when the token's surface carries no
kanji at all (a sentence rendered/generated in kana only). 'orthBase' can
only echo back what it sees, so for a bare surface like しろ it returns
しろ literally — indistinguishable at the text level from every unrelated
homophone that also spells しろ (城 "castle", 白 "white", the imperative of
する, ...). Vocab identity is a flat lemma-text key, so a bare, unresolved
kana string doesn't fail closed — it silently collides with whatever
unrelated word first happened to occupy that exact kana spelling in
dim_vocabulary, surfacing that word's definition on click instead (see
TASK unresolved-ja-kana-homophone: おしろ → しろ resolved to an unrelated
なる/為る-family entry rather than 城). 'lemma' in this situation is UniDic's
own best-guess *disambiguation* of the kana into a specific dictionary
headword (often, though not always, with kanji) using its language model —
not perfect, but a real dictionary lookup instead of an accidental text
collision. So for kana-only surfaces, a kanji-bearing 'lemma' is preferred
over the ambiguous raw kana. This does not reopen the 速い/早い problem:
that conflation only happens when 'lemma' is chosen over an *available,
already-disambiguating* kanji orthBase, which is not the case here.

Particles (助詞) and auxiliaries (助動詞) are kept for phrase detection
but flagged as non-content.
"""

import logging
import re
from services.vocabulary.processors.base import BaseLanguageProcessor, LemmaToken
from services.vocabulary.model_cache import model_cache

logger = logging.getLogger(__name__)

_CONTENT_POS = {"名詞", "動詞", "形容詞", "形状詞", "副詞"}
_SKIP_POS = {"助詞", "助動詞", "記号", "補助記号", "空白"}

# CJK Unified Ideographs (+ Extension A). Good enough to tell "has kanji"
# from "kana-only" for vocab-identity purposes — doesn't need to be a full
# script-detection table.
_KANJI_RANGE = re.compile(r'[一-鿿㐀-䶿]')


def _has_kanji(text: str) -> bool:
    return bool(text) and bool(_KANJI_RANGE.search(text))


# Katakana (U+30A1-U+30F6) -> hiragana (U+3041-U+3096) is a flat -0x60
# offset. ー (U+30FC, the long-vowel mark) is shared by both scripts and is
# left as-is. Readings are stored in hiragana for consistency with the rest
# of the app (furigana payloads, etc.) even though UniDic emits katakana.
_KATA_TO_HIRA = {cp: cp - 0x60 for cp in range(0x30A1, 0x30F7)}


def _to_hiragana(katakana: str) -> str:
    return katakana.translate(_KATA_TO_HIRA) if katakana else katakana


def _load_fugashi():
    """Load fugashi tagger with UniDic."""
    from fugashi import Tagger
    return Tagger()


class JapaneseProcessor(BaseLanguageProcessor):
    """Japanese segmentation + lemmatization using fugashi + UniDic."""

    def _get_tagger(self):
        return model_cache.get("fugashi_tagger", _load_fugashi)

    def extract_lemma_tokens(self, text: str) -> list[LemmaToken]:
        tagger = self._get_tagger()
        words = list(tagger(text))

        tokens = []
        for i, word in enumerate(words):
            surface = word.surface
            if not surface.strip():
                continue

            pos = word.feature.pos1
            lemma = self._orth_lemma(word)
            kana = getattr(word.feature, "kanaBase", None) or word.feature.kana

            tokens.append(LemmaToken(
                index=i,
                surface=surface,
                lemma=lemma,
                pos=pos,
                is_stop=pos in _SKIP_POS,
                is_content=pos in _CONTENT_POS,
                reading=_to_hiragana(kana) if kana else '',
            ))

        return tokens

    def tokenize_full(self, text: str) -> list[tuple[str, str, bool, str]]:
        tagger = self._get_tagger()
        result = []
        for word in tagger(text):
            surface = word.surface
            if not surface:
                continue
            pos = word.feature.pos1
            lemma = self._orth_lemma(word)
            is_content = pos in _CONTENT_POS
            # Captured from THIS token's own analysis, in its actual
            # sentence context — not re-derived from `lemma` afterward (see
            # base.py docstring for why that would be unsafe for a lemma
            # like 為る).
            kana = getattr(word.feature, "kanaBase", None) or word.feature.kana
            reading = _to_hiragana(kana) if kana else ''
            result.append((surface, lemma, is_content, reading))
        return result

    @staticmethod
    def _orth_lemma(word) -> str:
        """Vocab-identity key for a fugashi token: orthography-preserving,
        except where the orthography itself is ambiguous kana.

        Prefers 'orthBase' (dictionary form in the surface's own kanji/kana
        orthography) over 'lemma' (abstract lexeme, which merges kanji
        variants like 速い/早い — see module docstring) *when orthBase
        carries kanji*. When orthBase is kana-only — the surface had no
        kanji for it to preserve — a kanji-bearing 'lemma' is preferred
        instead, since raw kana collides across true homophones (城/白/...
        all spell しろ) while 'lemma' is UniDic's own disambiguation attempt.
        Falls back to the raw surface when nothing usable is available.
        """
        feature = word.feature
        orth = getattr(feature, "orthBase", None)
        lemma = feature.lemma

        if orth and orth != '*':
            if not _has_kanji(orth) and lemma and lemma != '*' and _has_kanji(lemma):
                return lemma
            return orth
        if lemma and lemma != '*':
            return lemma
        return word.surface

    def reading_for(self, text: str) -> str:
        """Dictionary-form reading (hiragana) for a short lemma/word string.

        Used to find a token's *homophone family* — every dim_vocabulary
        entry pronounced the same way, regardless of which kanji (if any)
        each one is spelled with — so an ambiguous kana-derived lemma can be
        checked against what else already shares its reading rather than
        trusted blindly. Re-running fugashi on an isolated short string is
        cheap; 'kanaBase' is UniDic's dictionary-form reading (its equivalent
        of orthBase, but for pronunciation instead of spelling).

        Multi-token input (e.g. a lemma that is itself a short phrase) has
        its tokens' readings concatenated. Returns '' for empty/unreadable
        input rather than raising — callers treat that as "no reading
        available, skip the homophone check."
        """
        if not text:
            return ''
        tagger = self._get_tagger()
        parts = []
        for word in tagger(text):
            reading = getattr(word.feature, "kanaBase", None) or word.feature.kana
            parts.append(reading or word.surface)
        return _to_hiragana(''.join(parts))

    def is_ready(self) -> bool:
        try:
            self._get_tagger()
            return True
        except Exception as e:
            logger.error(f"Japanese processor not ready: {e}")
            return False
