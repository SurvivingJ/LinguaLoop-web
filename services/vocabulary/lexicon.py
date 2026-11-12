"""Small word helpers shared by the multiple-choice builders.

Mirror of static/js/session/lexicon.js and of SQL ``public.pos_class``
(migrations/get_quiz_distractors.sql); tests/fixtures/lexicon/cases.json pins
all three.
"""

from __future__ import annotations

import re
from typing import Optional

_POS_CLASSES = {
    'noun': ['noun', 'n', 'nr', 'ns', 'nt', 'nz', 'nw', 'ng', 'nrt', 'nrfg', 'vn', 'an', 'propn', '名词', '名詞'],
    'verb': ['verb', 'v', 'vd', 'vg', 'vi', 'aux', '动词', '動詞'],
    'adj': ['adjective', 'adj', 'a', 'ag', '形容词', '形容詞', '形状詞'],
    'adv': ['adverb', 'adv', 'd', 'ad', '副词', '副詞'],
    'measure': ['measure_word', 'q', '量词', '助数詞'],
    'pron': ['pronoun', 'pron', 'r', '代词', '代名詞'],
}
POS_LOOKUP = {tag: cls for cls, tags in _POS_CLASSES.items() for tag in tags}

_CJK = re.compile('[぀-ヿ㐀-鿿]')


def pos_class(pos: Optional[str]) -> str:
    """Coarse part-of-speech class; see static/js/session/lexicon.js posClass."""
    tag = str(pos or '').strip().lower()
    return POS_LOOKUP.get(tag, tag)


def mask_headword(text: Optional[str], lemma: Optional[str]) -> Optional[str]:
    """Hide ``lemma`` inside ``text`` ("宗教改革是…" -> "～是…")."""
    if not text or not lemma:
        return text
    if _CJK.search(lemma):
        return text.replace(lemma, '～')
    return re.sub(rf'(?<![\w]){re.escape(lemma)}(?![\w])', '～', text, flags=re.IGNORECASE)
