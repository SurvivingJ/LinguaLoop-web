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
_CJK_SENTENCE_RE = re.compile(r'[^' + _CJK_TERMINATORS + r']*[' + _CJK_TERMINATORS + r']+|.+')
_LATIN_SENTENCE_RE = re.compile(r'.*?[.!?]+(?=\s|$)|.+', re.DOTALL)
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
_DIGIT_RE = re.compile(r'\d+')
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


def missing_numbers(l2_text: str, l1_text: str) -> list[str]:
    nums_l2 = _DIGIT_RE.findall(normalise_digits(l2_text))
    nums_l1 = normalise_digits(l1_text)
    return [n for n in nums_l2 if n not in nums_l1]


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
