"""Standard part-of-speech labels for dim_vocabulary.part_of_speech (2026-11-11).

The sense generator's POS legend (services/vocabulary/sense_generator.py
POS_LEGENDS) is the standard list. Words used to be created with whatever tag
the tokenizer produced -- jieba ("n", "nr", "v", "vn"), UniDic ("名詞",
"形状詞"), spaCy ("NOUN", "ADJ") -- next to standard names and Chinese labels
("名词"), so the same class appeared under many spellings.

The database does the standardising: a trigger on dim_vocabulary
(migrations/standardise_part_of_speech.sql) applies ``public.normalize_pos``
to every INSERT/UPDATE of part_of_speech and keeps the original tag in
``part_of_speech_raw``. Writers therefore send the tagger's tag unchanged --
normalising first in Python would hide the original from the trigger. This
module is the Python twin of that mapping (the SQL CASE is generated from
``_TAGS``), pinned by tests/fixtures/lexicon/cases.json (``normalize_pos``).
"""

from __future__ import annotations

from typing import Optional

CANONICAL_POS = (
    'noun', 'verb', 'adjective', 'adverb', 'pronoun', 'preposition', 'conjunction',
    'particle', 'measure_word', 'idiom', 'phrase', 'numeral', 'auxiliary',
    'adnominal', 'determiner', 'interjection', 'other',
)

_TAGS = {
    'noun': ['noun', 'n', 'nr', 'ns', 'nt', 'nz', 'nw', 'ng', 'nrt', 'nrfg', 'vn', 'an', 'f', 's',
             't', 'j', 'propn', 'proper noun', '名词', '名詞', '普通名詞', '固有名詞'],
    'verb': ['verb', 'v', 'vd', 'vg', 'vi', 'vq', '动词', '動詞', '情态动词'],
    'adjective': ['adjective', 'adj', 'a', 'ag', 'b', 'z', '形容词', '形容詞', '形状詞'],
    'adverb': ['adverb', 'adv', 'd', 'dg', 'ad', '副词', '副詞'],
    'pronoun': ['pronoun', 'pron', 'r', 'rr', 'rz', 'rg', '代词', '代名詞'],
    'preposition': ['preposition', 'p', 'adp', '介词'],
    'conjunction': ['conjunction', 'c', 'cconj', 'sconj', '连词', '接続詞'],
    'particle': ['particle', 'u', 'uj', 'ul', 'uz', 'ug', 'uv', 'ud', 'y', 'part', '助词', '助詞'],
    'measure_word': ['measure_word', 'measure word', 'classifier', 'q', '量词', '助数詞'],
    'idiom': ['idiom', 'i', '成语'],  # jieba i = 成语 (four-character idiom)
    'phrase': ['phrase', 'expression', 'l', '惯用语'],  # jieba l = 习用语 (set phrase, e.g. 越来越)
    'numeral': ['numeral', 'm', 'mq', 'num', '数词', '数詞'],
    'auxiliary': ['auxiliary', 'aux', '助動詞'],
    'adnominal': ['adnominal', '連体詞'],
    'determiner': ['determiner', 'det'],
    'interjection': ['interjection', 'intj', 'e', 'o', '叹词', '感動詞'],
    'other': ['other', 'x', 'sym', 'punct', 'h', 'k', 'eng', 'unknown',
              '接頭辞', '接尾辞', '記号', '補助記号'],
}
POS_MAP = {tag: canonical for canonical, tags in _TAGS.items() for tag in tags}


def normalize_pos(tag: Optional[str]) -> Optional[str]:
    """The standard label for any tagger's part-of-speech tag.

    None/blank stays None. UniDic-style subdivided tags ("名詞-普通名詞-一般",
    "名詞,普通名詞") use their head. Anything unrecognised becomes 'other'.
    """
    if tag is None:
        return None
    t = str(tag).strip()
    if not t:
        return None
    head = t.replace(',', '-').split('-')[0].strip()
    return POS_MAP.get(t.lower()) or POS_MAP.get(head.lower()) or 'other'


def pos_hint(vocab: Optional[dict]) -> str:
    """The POS to show an exercise-authoring prompt as a dictionary hint.

    The ladder's Prompt 1 and the staged/fat-seed authoring chain validate the
    model's POS against per-language lists (UniDic 名詞 for ja, 名词 for zh --
    services/vocabulary_ladder/config.py _POS_JA/_POS_ZH). They used to be
    hinted with the stored tag, which for those rows was the tokenizer's own;
    keep giving them that original tag (part_of_speech_raw) where one exists,
    so standardising the column does not change what the prompts see.
    """
    v = vocab or {}
    return (v.get('part_of_speech_raw') or v.get('part_of_speech') or '').strip()
