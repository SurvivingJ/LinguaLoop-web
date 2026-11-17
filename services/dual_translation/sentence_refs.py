"""Sentence-level L1 references for test transcripts (ADR-037, TASK-902/903).

Pure functions shared by scripts/build_test_sentences.py (segmentation with
spans), scripts/sentence_ref_runner.py (document checks, review packs,
tightness) and scripts/upload_sentence_references.py (activation rules).

Nothing here touches the database or a model.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field, asdict
from difflib import SequenceMatcher
from typing import Iterable, Optional

# The sentence regexes are copied from passage_builder (importing it pulls in the
# whole LLM stack, which the offline harness must not need). tests/test_sentence_refs.py
# asserts they are still identical to passage_builder's when that module imports.
_CJK_CODES = frozenset({'zh', 'ja'})
_CJK_TERMINATORS = '。！？…!?'
# Closing quotes/brackets that follow a terminator stay with the sentence they
# close: 她说：“……很重要。”她的意思是 splits after ”, not before it, and
# This is "training data." The app ... splits after the closing ".
_CLOSERS = '”’」』）)》〉】]"\''
_CJK_SENTENCE_RE = re.compile(r'[^' + _CJK_TERMINATORS + r']*[' + _CJK_TERMINATORS + r']+'
                              r'[' + re.escape(_CLOSERS) + r']*|.+')
_LATIN_SENTENCE_RE = re.compile(r'.*?[.!?]+[' + re.escape(_CLOSERS) + r']*(?=\s|$)|.+', re.DOTALL)
_WHITESPACE_RE = re.compile(r'\s+')


def segment_sentences(text: Optional[str], language_code: str) -> list[str]:
    """Same output as passage_builder.segment_sentences (kept in sync by test)."""
    cleaned = _WHITESPACE_RE.sub(' ', (text or '')).strip()
    if not cleaned:
        return []
    pattern = _CJK_SENTENCE_RE if (language_code or '').lower() in _CJK_CODES else _LATIN_SENTENCE_RE
    return [m.group(0).strip() for m in pattern.finditer(cleaned) if m.group(0).strip()]

PROMPT_VERSION = 'sr-1.0'
ARMS = ('sentencewise', 'aligned')
VERDICTS = ('pending', 'pass', 'rewritten', 'fail')
USABLE_VERDICTS = ('pass', 'rewritten')
#: Independent reviews of the exact same text (distinct runs) at which a
#: reference skips the tightness floor in window selection (ADR-049).
FLOOR_OVERRIDE_REVIEWS = 2
LANG_CODE = {1: 'zh', 2: 'en', 3: 'ja'}
LANG_ID = {v: k for k, v in LANG_CODE.items()}

# ---------------------------------------------------------------------------
# Segmentation with spans
# ---------------------------------------------------------------------------

@dataclass
class SentenceSpan:
    idx: int
    char_start: int
    char_end: int          # half-open
    text: str
    token_start: Optional[int] = None
    token_end: Optional[int] = None  # half-open


def transcript_hash(transcript: str) -> str:
    return hashlib.sha256((transcript or '').encode('utf-8')).hexdigest()


def segment_with_spans(transcript: str, language_code: str) -> list[SentenceSpan]:
    """Split the RAW transcript into sentences and keep character spans.

    Uses the same terminator regexes as passage_builder.segment_sentences, but
    on the uncollapsed text so that spans index into `tests.transcript`
    directly. Leading/trailing whitespace of each match is trimmed off the span.
    The stripped texts equal `segment_sentences(transcript)` whenever the
    transcript has no internal runs of whitespace inside a sentence; that
    equality is asserted by the backfill script.
    """
    text = transcript or ''
    pattern = _CJK_SENTENCE_RE if (language_code or '').lower() in _CJK_CODES else _LATIN_SENTENCE_RE
    out: list[SentenceSpan] = []
    for m in pattern.finditer(text):
        s, e = m.start(), m.end()
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if s >= e:
            continue
        out.append(SentenceSpan(idx=len(out), char_start=s, char_end=e, text=text[s:e]))
    return out


def attach_token_spans(spans: list[SentenceSpan], token_map: Optional[list]) -> list[str]:
    """Fill token_start/token_end for each span from `tests.vocab_token_map`
    ([[surface, sense_id], ...], whose surfaces concatenate to the transcript).
    Returns a list of warnings (one per sentence that could not be covered
    exactly); such sentences keep None spans.
    """
    warnings: list[str] = []
    if not token_map:
        for sp in spans:
            sp.token_start = sp.token_end = None
        return ['no token map']
    offsets = []
    pos = 0
    for surf, _ in token_map:
        offsets.append((pos, pos + len(surf)))
        pos += len(surf)
    for sp in spans:
        # A token belongs to the sentence when it overlaps the span and the part
        # of it outside the span is whitespace only. English token maps attach
        # the following space to sentence-final punctuation (". "), so that
        # token straddles the boundary by one blank character.
        members = []
        for i, (a, b) in enumerate(offsets):
            if b <= sp.char_start or a >= sp.char_end:
                continue
            surf = token_map[i][0]
            outside = surf[:max(0, sp.char_start - a)] + surf[max(0, sp.char_end - a):]
            if outside.strip():
                members = None  # a token carries real text across the boundary
                break
            members.append(i)
        if members:
            inside = ''.join(token_map[i][0] for i in members)
            if inside.strip() == sp.text:
                sp.token_start, sp.token_end = members[0], members[-1] + 1
                continue
        sp.token_start = sp.token_end = None
        warnings.append(f'sentence {sp.idx}: token map does not align with span {sp.char_start}-{sp.char_end}')
    return warnings


def repair_token_map(transcript: str, token_map: list) -> Optional[list]:
    """Re-insert whitespace that a tokenizer dropped from `token_map`.

    Some Japanese word maps omit spaces and newlines, so their surfaces no
    longer concatenate to the transcript. This walks both in step and adds the
    missing whitespace back as [ws, 0] tokens (no sense link). Every existing
    token, and its sense id, is kept unchanged and in order. Returns the
    repaired map, or None when the difference is anything other than missing
    whitespace (those maps need a real rebuild).
    """
    out: list = []
    pos = 0
    text = transcript or ''
    for surf, sid in token_map:
        ws = ''
        while pos < len(text) and not text.startswith(surf, pos) and text[pos].isspace():
            ws += text[pos]
            pos += 1
        if ws:
            out.append([ws, 0])
        if not text.startswith(surf, pos):
            return None
        out.append([surf, sid])
        pos += len(surf)
    tail = text[pos:]
    if tail:
        if tail.strip():
            return None
        out.append([tail, 0])
    return out if ''.join(t for t, _ in out) == text else None


def senses_in_span(token_map: list, token_start: int, token_end: int) -> list[int]:
    return [sid for _, sid in token_map[token_start:token_end] if sid]


# ---------------------------------------------------------------------------
# Script / preamble helpers
# ---------------------------------------------------------------------------

_HAN = r'㐀-䶿一-鿿豈-﫿'
_KANA = r'぀-ヿㇰ-ㇿ'
_SCRIPT_RE = {
    'zh': re.compile(f'[{_HAN}]'),
    'ja': re.compile(f'[{_HAN}{_KANA}]'),
    'en': re.compile(r'[A-Za-z]'),
}
PREAMBLE_RE = re.compile(
    r'^\s*(?:この文章は|本文|本篇|This (?:passage|article|text)|The following (?:passage|text))'
    r'|---'
)
_PUNCT_RE = re.compile(r'[\s　。、，．,.!！?？:：;；"“”\'‘’「」『』()（）\[\]【】\-—–…·・]')

LENGTH_RATIO_BOUNDS = {       # len(l1) / len(l2), fitted loosely; the pilot refits
    ('ja', 'en'): (1.2, 7.0), ('zh', 'en'): (1.2, 6.0),
    ('en', 'zh'): (0.15, 0.9), ('en', 'ja'): (0.2, 1.2),
    ('ja', 'zh'): (0.3, 1.5), ('zh', 'ja'): (0.6, 3.0),
}


def leaked_script(l1_text: str, l2_code: str) -> list[str]:
    """Characters of the L2 script found in an L1 reference."""
    rx = _SCRIPT_RE.get(l2_code)
    if not rx:
        return []
    found = sorted(set(rx.findall(l1_text or '')))
    if l2_code == 'en':
        # Latin letters in a zh/ja reference are tolerated for proper nouns and
        # acronyms; only flag long runs.
        runs = re.findall(r'[A-Za-z]{4,}', l1_text or '')
        return sorted(set(runs))
    return found


def normalise_digits(s: str) -> str:
    return unicodedata.normalize('NFKC', s or '')


# Numbers are compared by value, not by digit string: "102万" is satisfied by
# "1,020,000" or "1.02 million" (or "102 wan"), "1000" by "1,000", and a "5" in
# the original is NOT satisfied by the "5" inside "15" or "2015".
_NUM = r'\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?'
_CJK_UNITS = {'百': (100,), '千': (1000,), '万': (10 ** 4,), '萬': (10 ** 4,),
              '亿': (10 ** 8,), '億': (10 ** 8,), '兆': (10 ** 12, 10 ** 6)}  # zh 兆 is also "mega"
_EN_SCALES = {'hundred': 100, 'thousand': 10 ** 3, 'million': 10 ** 6, 'billion': 10 ** 9,
              'trillion': 10 ** 12}
_CJK_MENTION_RE = re.compile(f'(?:(?:{_NUM})[{"".join(_CJK_UNITS)}])+(?:{_NUM})?')
_EN_MENTION_RE = re.compile(f'({_NUM})(?:\\s*({"|".join(_EN_SCALES)})\\b)?', re.IGNORECASE)
_NUM_RE = re.compile(_NUM)
_MONTHS = ('january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
           'september', 'october', 'november', 'december')
# Full English month names count as a mention (so 11月 is carried by "November");
# 'may' only when capitalised, to keep the modal verb out.
_MONTH_RE = re.compile(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\b')


def _dec(token: str):
    from decimal import Decimal
    return Decimal(token.replace(',', ''))


def _cjk_values(mention: str) -> set:
    """Values a digit+unit mention like 102万 / 1亿2000万 / 3千 can stand for: the
    compound value (both readings of 兆), plus the bare number when there is one part."""
    parts = re.findall(f'({_NUM})([{"".join(_CJK_UNITS)}])?', mention)
    readings = {0}
    for alt in range(2):  # second pass reads 兆 as 10**6
        total = section = 0
        for num, unit in parts:
            v = _dec(num)
            if not unit:
                section += v
            elif unit in ('百', '千'):
                section += v * _CJK_UNITS[unit][0]
            else:
                m = _CJK_UNITS[unit][min(alt, len(_CJK_UNITS[unit]) - 1)]
                total += (section + v) * m
                section = 0
        readings.add(total + section)
    readings.discard(0)
    if len(parts) == 1:
        readings.add(_dec(parts[0][0]))
    return readings


def _number_mentions(text: str) -> list[tuple[str, set]]:
    """``[(label, {values})]`` for every number written with digits in ``text``."""
    # NFKC turns the full-width comma into ',', which would glue a CJK list
    # (100，200) into one grouped number; keep it a separator.
    t = unicodedata.normalize('NFKC', (text or '').replace('，', '、'))
    out, taken = [], []
    for m in _CJK_MENTION_RE.finditer(t):
        out.append((m.group(0), _cjk_values(m.group(0))))
        taken.append(m.span())
    for m in _EN_MENTION_RE.finditer(t):
        if any(a <= m.start() < b for a, b in taken):
            continue
        v = _dec(m.group(1))
        vals = {v}
        if m.group(2):
            vals.add(v * _EN_SCALES[m.group(2).lower()])
        if t[m.end():m.end() + 2] == '世纪' and v == int(v) and 1 <= v <= 30:
            vals |= {(v - 1) * 100 + y for y in range(100)}  # 20世纪 -> any year 1900-1999
        if t[m.end():m.end() + 2] == '年代' and v == int(v) and 0 <= v < 100 and v % 10 == 0:
            vals |= {1900 + v, 2000 + v}  # 70年代 -> the 1970s
        if t[m.end():m.end() + 1] == '月' and 1 <= v <= 12 and v == int(v):
            vals.add(_MONTHS[int(v) - 1])  # 11月 -> 'november'
        out.append((m.group(1), vals))
    for name in _MONTH_RE.findall(t):
        out.append((name, {name.lower()}))
    return out


def missing_numbers(l2_text: str, l1_text: str) -> list[str]:
    """Numbers written with digits in the gold that the reference does not carry
    (by value; scale words and 万/亿/千 are understood on both sides)."""
    def norm(vals):
        return {v.normalize() if hasattr(v, 'normalize') else v for v in vals}
    have: set = set()
    for _, vals in _number_mentions(l1_text):
        have |= norm(vals)
    return [label for label, vals in _number_mentions(l2_text)
            if any(not isinstance(v, str) for v in vals) and not (norm(vals) & have)]


def has_preamble(text: str) -> bool:
    return bool(PREAMBLE_RE.search(text or ''))


# ---------------------------------------------------------------------------
# Tightness (Tier 0): similarity of a blind back-translation to the gold
# ---------------------------------------------------------------------------

def _norm_for_tightness(text: str, language_code: str) -> list[str]:
    t = unicodedata.normalize('NFKC', text or '').lower()
    t = _PUNCT_RE.sub('', t) if language_code in _CJK_CODES else re.sub(r'[^\w\s]', '', t)
    if language_code in _CJK_CODES:
        return list(t)
    return t.split()


def tightness(back_translation: str, gold: str, language_code: str) -> float:
    """0..1 character (CJK) or word (en) similarity, same spirit as the dictation
    grader's Tier 0: normalise, align, ratio of matched units."""
    a = _norm_for_tightness(gold, language_code)
    b = _norm_for_tightness(back_translation, language_code)
    if not a:
        return 0.0
    return round(SequenceMatcher(None, a, b, autojunk=False).ratio(), 4)


# ---------------------------------------------------------------------------
# Document model and checks
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    test_id: str
    l1: str
    ok: bool
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def validate_doc(doc: dict, sentences: list[dict], l2_code: str) -> CheckResult:
    """Deterministic checks (tech page §Deterministic checks).

    `sentences` is the canonical list [{idx, l2_text}, ...] for the test.
    """
    test_id = str(doc.get('test_id', '?'))
    l1 = str(doc.get('l1', '?'))
    res = CheckResult(test_id=test_id, l1=l1, ok=True)
    fail, warn = res.failures.append, res.warnings.append

    if doc.get('l2') != l2_code:
        fail(f'l2_mismatch:{doc.get("l2")}!={l2_code}')
    if doc.get('arm') not in ARMS:
        fail(f'arm_invalid:{doc.get("arm")}')
    if not doc.get('prompt_version'):
        fail('prompt_version_missing')
    items = doc.get('sentences') or []
    if len(items) != len(sentences):
        fail(f'count_mismatch:{len(items)}!={len(sentences)}')
    seen_l1: dict[str, int] = {}
    for i, (it, canon) in enumerate(zip(items, sentences)):
        if it.get('idx') != i or canon.get('idx') != i:
            fail(f'idx_order:{i}')
        if (it.get('l2') or '') != canon.get('l2_text', ''):
            fail(f'l2_changed:{i}')
        l1_text = (it.get('l1') or '').strip()
        if not l1_text:
            fail(f'empty_l1:{i}')
            continue
        leak = leaked_script(l1_text, l2_code)
        if leak:
            fail(f'l2_script_leak:{i}:{"".join(leak)[:12]}')
        miss = missing_numbers(canon.get('l2_text', ''), l1_text)
        if miss:
            fail(f'missing_number:{i}:{",".join(miss)}')
        if has_preamble(l1_text) or has_preamble(canon.get('l2_text', '')):
            fail(f'preamble:{i}')
        lo, hi = LENGTH_RATIO_BOUNDS.get((l2_code, l1), (0.1, 10.0))
        ratio = len(l1_text) / max(1, len(canon.get('l2_text', '')))
        if not (lo <= ratio <= hi):
            fail(f'length_ratio:{i}:{ratio:.2f}')
        if l1_text in seen_l1:
            fail(f'duplicate_sentence:{i}={seen_l1[l1_text]}')
        seen_l1[l1_text] = i
        if re.search(r'\((?:note|lit\.|literally)', l1_text, re.I):
            warn(f'author_note_in_l1:{i}')
    res.ok = not res.failures
    return res


def strip_author_notes(doc: dict) -> dict:
    clean = {k: v for k, v in doc.items() if k != 'author_notes'}
    clean['sentences'] = [{'idx': s.get('idx'), 'l2': s.get('l2'), 'l1': s.get('l1')} for s in doc.get('sentences', [])]
    return clean


def verdict_ok(v: dict) -> bool:
    return v.get('verdict') in ('pass', 'rewritten')


def faithful_reviews(new_row: dict, run_id: str, existing: Iterable[dict]) -> int:
    """How many independent reviews (distinct run_id) passed or wrote this
    exact text for this (sentence, L1), counting the new row's own review.
    ``existing`` rows carry sentence_id, l1_language_id, l1_text, run_id,
    review_verdict. A row whose verdict is not usable counts 0 (ADR-049)."""
    if new_row.get('review_verdict') not in USABLE_VERDICTS:
        return 0
    runs = {run_id}
    for e in existing:
        if (e.get('sentence_id') == new_row['sentence_id']
                and e.get('l1_language_id') == new_row['l1_language_id']
                and e.get('l1_text') == new_row['l1_text']
                and e.get('review_verdict') in USABLE_VERDICTS):
            runs.add(e.get('run_id'))
    return len(runs)


def activation_plan(new_rows: Iterable[dict], existing_active: dict[tuple[int, int], int]) -> dict:
    """Decide which new rows become active and which existing rows deactivate.

    new_rows: dicts with sentence_id, l1_language_id, review_verdict.
    existing_active: {(sentence_id, l1_language_id): row_id}.
    """
    activate, deactivate = [], []
    for r in new_rows:
        key = (r['sentence_id'], r['l1_language_id'])
        if r.get('review_verdict') in ('pass', 'rewritten'):
            activate.append(key)
            if key in existing_active:
                deactivate.append(existing_active[key])
    return {'activate': activate, 'deactivate': sorted(set(deactivate))}


def doc_path_name(test_id: str, l1: str) -> str:
    return f'{test_id}.{l1}.json'


def load_json(path: str):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def dump_json(path: str, obj) -> None:
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
