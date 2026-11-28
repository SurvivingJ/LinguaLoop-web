"""The learner's own words for the conjugation drill.

The conjugation drill computes every form by rule in the browser
(static/js/particles/conjugate.js), so it needs only three things per word:
dictionary form, reading and conjugation class. This module finds the verbs
and adjectives the learner already knows (``user_vocabulary_knowledge``) and
gives each its class:

* a word in the reviewed word lists (data/particle_drill/ja/conjugation) takes
  its class from there;
* any other word is classified from the UniDic conjugation type of its
  dictionary form (五段 -> godan, 上一段 / 下一段 -> ichidan, サ行変格 -> suru,
  カ行変格 -> kuru; 形容詞 -> i, 形状詞 -> na);
* a word whose forms the rule engine would get wrong is left out (honorific
  ～ます verbs, 問う, single-kanji する verbs such as 愛する, ～ずる verbs,
  multi-word expressions).

No table is written and nothing is stored: the pool is rebuilt from the
learner's current knowledge on each request.
"""
import logging
import re
import threading
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

KNOWN_STATUSES = ('known', 'probably_known', 'learning')
MAX_KNOWN_ROWS = 6000
CHUNK = 200
GLOSS_CHARS = 70
ENGLISH_ID = 2

_HIRAGANA_RE = re.compile(r'^[ぁ-ゖー]+$')
_KANJI_RE = re.compile(r'[㐀-鿿々]')
_I_ROW_E_ROW = 'いきしちにひみりぎじびぴえけせてねへめれげぜでべぺ'
# Godan by type, but their ～ます / command forms are irregular; and 問う / 請う / 乞う (て-form うて).
IRREGULAR = {'いらっしゃる', 'おっしゃる', '仰る', 'くださる', '下さる', 'なさる', '為さる', 'ござる', '御座る',
             '問う', '請う', '乞う', '恋う'}

_tagger = None
_tagger_lock = threading.Lock()
_tagger_failed = False


def _get_tagger():
    """One UniDic tagger per process, or None when fugashi is not installed."""
    global _tagger, _tagger_failed
    if _tagger is None and not _tagger_failed:
        with _tagger_lock:
            if _tagger is None and not _tagger_failed:
                try:
                    import fugashi
                    _tagger = fugashi.Tagger()
                except Exception:  # noqa: BLE001 - the drill still works from the word lists
                    logger.exception("fugashi tagger unavailable; conjugation classes come from the word lists only")
                    _tagger_failed = True
    return _tagger


def to_hiragana(text: str) -> str:
    return ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in text or '')


def _verb_class_ok(lemma: str, reading: str, cls: str) -> bool:
    """The same shape rules the word-list validator applies."""
    if not lemma or not reading or lemma[-1] != reading[-1]:
        return False
    if cls == 'godan':
        return reading[-1] in 'うくぐすつぬぶむる'
    if cls == 'ichidan':
        return reading.endswith('る') and len(reading) > 1 and reading[-2] in _I_ROW_E_ROW
    if cls == 'suru':
        stem = lemma[:-2]
        # 愛する / 略する conjugate partly like godan (愛さない): left out.
        return (lemma.endswith('する') and reading.endswith('する')
                and not (len(stem) == 1 and _KANJI_RE.match(stem)))
    if cls == 'kuru':
        return (lemma.endswith('来る') or lemma.endswith('くる')) and reading.endswith('くる')
    return False


def classify(lemma: str, reading: Optional[str], pos: str, pos_raw: Optional[str] = None,
             tagger=None) -> Optional[Dict[str, str]]:
    """``{'d', 'k', 'c'}`` for a verb or adjective, or None when it cannot be drilled safely.

    ``pos`` is dim_vocabulary.part_of_speech ('verb' / 'adjective'); ``pos_raw`` the
    tagger's own tag where stored (形容詞 / 形状詞 separate い- from な-adjectives).
    """
    lemma = (lemma or '').strip()
    if not lemma or lemma in IRREGULAR or pos not in ('verb', 'adjective'):
        return None
    tagger = tagger or _get_tagger()
    tokens = list(tagger(lemma)) if tagger else []
    kana = to_hiragana((reading or '').strip())
    if not _HIRAGANA_RE.match(kana):
        kana = to_hiragana(''.join((getattr(t.feature, 'kana', None) or t.surface) for t in tokens))
    if not _HIRAGANA_RE.match(kana):
        return None

    if pos == 'adjective':
        tag = pos_raw or (tokens[-1].feature.pos1 if len(tokens) == 1 else '')
        if tag == '形容詞' and lemma.endswith('い') and kana.endswith('い'):
            return {'d': lemma, 'k': kana, 'c': 'i'}
        if tag == '形状詞' and not lemma.endswith(('な', 'だ')):
            return {'d': lemma, 'k': kana, 'c': 'na'}
        return None

    if not tokens:
        return None
    last = tokens[-1].feature
    ctype = getattr(last, 'cType', None) or ''
    if len(tokens) == 1:
        if ctype.startswith('五段'):
            cls = 'godan'
        elif ctype.startswith(('上一段', '下一段')):
            cls = 'ichidan'
        elif ctype.startswith('サ行変格'):
            cls = 'suru'
        elif ctype.startswith('カ行変格'):
            cls = 'kuru'
        else:
            return None
    elif (len(tokens) == 2 and tokens[1].surface == 'する' and ctype.startswith('サ行変格')
          and tokens[0].feature.pos1 == '名詞'):
        cls = 'suru'                                  # 勉強する
    else:
        return None                                   # 持って来る, 気がつく, ...
    if not _verb_class_ok(lemma, kana, cls):
        return None
    return {'d': lemma, 'k': kana, 'c': cls}


def _chunks(values: List, size: int = CHUNK):
    for i in range(0, len(values), size):
        yield values[i:i + size]


def _short_gloss(text: str) -> str:
    text = ' '.join((text or '').split())
    return text if len(text) <= GLOSS_CHARS else text[:GLOSS_CHARS - 1].rstrip() + '…'


def known_words(db, user_id: str, language_id: int, lexicon: Dict[str, List[dict]],
                gloss_language_id: int = ENGLISH_ID) -> Dict[str, object]:
    """The verbs and adjectives this learner knows, ready for the conjugation engine.

    ``lexicon`` is ``{'verbs': [...], 'adjectives': [...]}`` (the reviewed word
    lists). Returns ``{'words': [{d, k, c, en, lv, t?, known: True}], 'verbs': n,
    'adjectives': n, 'skipped': n}``; most confidently known words first.
    """
    rows: List[dict] = []
    offset = 0
    while offset < MAX_KNOWN_ROWS:
        page = (db.table('user_vocabulary_knowledge').select('sense_id, p_known, status')
                .eq('user_id', user_id).eq('language_id', language_id)
                .in_('status', list(KNOWN_STATUSES))
                .order('p_known', desc=True).range(offset, offset + 999).execute().data or [])
        rows += page
        if len(page) < 1000:
            break
        offset += 1000
    if not rows:
        return {'words': [], 'verbs': 0, 'adjectives': 0, 'skipped': 0}

    p_by_sense = {r['sense_id']: float(r.get('p_known') or 0) for r in rows}
    vocab_p: Dict[int, float] = {}
    for part in _chunks(list(p_by_sense)):
        for s in (db.table('dim_word_senses').select('id, vocab_id')
                  .in_('id', part).execute().data or []):
            vocab_p[s['vocab_id']] = max(vocab_p.get(s['vocab_id'], 0.0), p_by_sense.get(s['id'], 0.0))

    vocab: List[dict] = []
    for part in _chunks(list(vocab_p)):
        vocab += (db.table('dim_vocabulary')
                  .select('id, lemma, reading, part_of_speech, part_of_speech_raw, level_tag')
                  .in_('id', part).eq('language_id', language_id)
                  .in_('part_of_speech', ['verb', 'adjective']).execute().data or [])

    glosses: Dict[int, tuple] = {}
    for part in _chunks([v['id'] for v in vocab]):
        for s in (db.table('dim_word_senses').select('vocab_id, definition, sense_rank')
                  .in_('vocab_id', part).eq('definition_language_id', gloss_language_id)
                  .execute().data or []):
            rank = s.get('sense_rank') or 99
            if s.get('definition') and (s['vocab_id'] not in glosses or rank < glosses[s['vocab_id']][0]):
                glosses[s['vocab_id']] = (rank, s['definition'])

    curated = {(w['d'], w['k']): w for name in ('verbs', 'adjectives') for w in lexicon.get(name) or []}
    by_lemma: Dict[str, List[dict]] = {}
    for w in curated.values():
        by_lemma.setdefault(w['d'], []).append(w)

    words, seen, skipped = [], set(), 0
    for v in sorted(vocab, key=lambda v: -vocab_p.get(v['id'], 0.0)):
        lemma = (v.get('lemma') or '').strip()
        kana = to_hiragana((v.get('reading') or '').strip())
        listed = curated.get((lemma, kana)) or (by_lemma[lemma][0] if len(by_lemma.get(lemma, [])) == 1 else None)
        if listed:
            word = {'d': listed['d'], 'k': listed['k'], 'c': listed['c']}
        else:
            word = classify(lemma, v.get('reading'), v.get('part_of_speech'), v.get('part_of_speech_raw'))
        if not word:
            skipped += 1
            continue
        key = (word['d'], word['k'])
        if key in seen:
            continue
        seen.add(key)
        gloss = glosses.get(v['id'], (0, ''))[1] or (listed or {}).get('en', '')
        word.update({'en': _short_gloss(gloss), 'known': True,
                     'lv': (listed or {}).get('lv') or _level(v.get('level_tag'))})
        words.append(word)
    verbs = sum(1 for w in words if w['c'] not in ('i', 'na'))
    return {'words': words, 'verbs': verbs, 'adjectives': len(words) - verbs, 'skipped': skipped}


def _level(level_tag: Optional[str]) -> int:
    """JLPT level from dim_vocabulary.level_tag ('N4', 'jlpt_n4', ...); 3 when unknown."""
    m = re.search(r'[Nn]\s*([1-5])', level_tag or '')
    return int(m.group(1)) if m else 3
