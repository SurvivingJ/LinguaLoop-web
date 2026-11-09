"""Deterministic, model-free quality checks for comprehension tests (TASK-912–918).

Spec: wiki/features/test-quality-checks.tech.md. Motivation and gold set:
wiki/evaluations/ja-test-review-2026-11-09.md.

Pure module — no DB, no network — so the generator (via QuestionValidator and
the orchestrator) and the read-only library audit
(``scripts/audit_test_quality.py``) run exactly the same code.

Three scopes:

* **passage** — the transcript and title (``run_passage_checks``)
* **question** — one question against its passage (``run_question_checks``)
* **test** — the question set as a whole (``run_test_checks``)

Every check returns ``CheckResult`` objects whose ``severity`` comes from
``resolve_mode(code)``: ``CHECK_MODES`` by default, overridden for a whole run
by the ``TEST_QC_MODES`` environment variable (``flag`` | ``reject`` |
``calibrated``) so experiment arms differ by one variable (TASK-921/924).

These checks cannot tell whether an answer is *true* — wrong keys, two
defensible answers and incoherent passages are the answer-entailment judge's
and the review skill's job.
"""

from __future__ import annotations

import difflib
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, Iterable, List, Literal, Optional, Sequence, Tuple

Severity = Literal['reject', 'flag']
Mode = Literal['off', 'flag', 'reject']
Scope = Literal['passage', 'question', 'test']

# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckResult:
    code: str
    severity: Severity
    scope: Scope
    message: str
    question_index: Optional[int] = None
    field: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------
# Modes
# --------------------------------------------------------------------------

#: Per-check mode used when TEST_QC_MODES is unset or 'calibrated'.
#: Every check ships as 'flag'; TASK-920 calibration and the TASK-924
#: experiment decide promotions. Keep a comment with the evidence next to any
#: change.
CHECK_MODES: Dict[str, Mode] = {
    # Calibrated 2026-11-09 (TASK-920): 242 sampled findings hand-labelled
    # across zh/en/ja, scores in data/test_quality/calibration_2026-11-09/
    # scores.md. Rule: 'reject' needs >= 10 labelled and precision >= 0.9
    # under the current thresholds. Precision is in-sample for the checks
    # whose thresholds were tuned on the same labels (copy, length) —
    # TASK-924 measures the effect on fresh generations.
    'absolute_distractors': 'reject',    # 25/27 = 0.93
    'answer_copies_passage': 'reject',   # 13/13 after min 15 chars, T3+
    'duplicate_answer': 'reject',        # 24/25 = 0.96
    'latin_in_cjk': 'reject',            # 14/14
    'script_above_level': 'reject',      # 12/12
    'answer_length_outlier': 'flag',     # 21/24 = 0.88 after retune
    'type_mix': 'flag',                  # 42/60 = 0.70 (zh 0.35)
    'choice_label_prefix': 'flag',       # 4/4, too few labelled
    'duplicate_stem': 'flag',            # 3/3, too few labelled
    'duplicate_vocab_target': 'flag',    # 3/3 after retune, too few
    'foreign_script': 'flag',            # 2/2 after allowlisting 昇, too few
    'too_few_questions': 'flag',         # 1/1 after T3+ cap, too few
    'missing_title': 'flag',             # 1/1, too few
}

_RUN_MODES = ('flag', 'reject', 'calibrated')


def run_mode() -> str:
    """The run-wide mode from ``TEST_QC_MODES`` (default ``calibrated``)."""
    value = (os.environ.get('TEST_QC_MODES') or 'calibrated').strip().lower()
    if value not in _RUN_MODES:
        raise ValueError(
            f"TEST_QC_MODES must be one of {_RUN_MODES}, got {value!r}"
        )
    return value


def resolve_mode(code: str, override: Optional[str] = None) -> Mode:
    """Effective mode of one check. ``override`` beats the environment."""
    run = override or run_mode()
    base = CHECK_MODES.get(code, 'flag')
    if base == 'off':
        return 'off'
    if run == 'flag':
        return 'flag'
    if run == 'reject':
        return 'reject'
    return base


# --------------------------------------------------------------------------
# Language profiles
# --------------------------------------------------------------------------

_CJK_RE = re.compile(r'[㐀-䶿一-鿿豈-﫿]')
_KANJI_RE = re.compile(r'[一-鿿]')
_KANA_RE = re.compile(r'[぀-ヿ]')
_CJK_OR_KANA_RE = re.compile(r'[぀-ヿ㐀-䶿一-鿿豈-﫿]')
_LATIN_RUN_RE = re.compile(r'[A-Za-z]{2,}')
# Whitespace, ASCII punctuation and the CJK/full-width punctuation blocks.
_STRIP_RE = re.compile(
    r'[\s　-〿＀-／：-＠［-｀｛-･'
    r'!-/:-@\[-`{-~‐-‧・]'
)
_WORD_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def _bigrams(s: str) -> List[str]:
    t = _STRIP_RE.sub('', s or '')
    if len(t) < 2:
        return [t] if t else []
    return [t[i:i + 2] for i in range(len(t) - 1)]


def _words(s: str) -> List[str]:
    return _WORD_RE.findall((s or '').lower())


@dataclass(frozen=True)
class LanguageProfile:
    code: str
    is_cjk: bool
    copy_min_len: int          # chars for CJK, words for en
    absolutes: Tuple[str, ...]
    tokenize: Callable[[str], List[str]] = field(compare=False)

    def length(self, s: str) -> int:
        """Choice length: characters (CJK, punctuation/space stripped) or words."""
        if self.is_cjk:
            return len(_STRIP_RE.sub('', s or ''))
        return len(_words(s))

    def units(self, s: str) -> List[str]:
        """Sequence used for longest-common-run matching."""
        if self.is_cjk:
            return list(_STRIP_RE.sub('', s or ''))
        return _words(s)


_PROFILES: Dict[str, LanguageProfile] = {
    'ja': LanguageProfile(
        code='ja', is_cjk=True, copy_min_len=15,
        absolutes=('すべて', '全て', '完全に', '決して', '常に', '全く', '一切', '必ず', '絶対'),
        tokenize=_bigrams,
    ),
    'zh': LanguageProfile(
        code='zh', is_cjk=True, copy_min_len=15,
        absolutes=('所有', '完全', '绝对', '从不', '总是', '一切', '全部', '永远'),
        tokenize=_bigrams,
    ),
    'en': LanguageProfile(
        code='en', is_cjk=False, copy_min_len=6,
        absolutes=('all', 'always', 'never', 'completely', 'entirely', 'only', 'every', 'none'),
        tokenize=_words,
    ),
}


def get_profile(language_code: str) -> LanguageProfile:
    """Profile for ``ja`` / ``zh`` / ``en``. Unknown code raises ``KeyError``."""
    return _PROFILES[language_code]


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# --------------------------------------------------------------------------
# Question helpers
# --------------------------------------------------------------------------

def _qtext(q: dict) -> str:
    return q.get('question') or q.get('question_text') or ''


def _choices(q: dict) -> List[str]:
    return [c if isinstance(c, str) else str(c) for c in (q.get('choices') or [])]


def _answer(q: dict) -> str:
    a = q.get('answer')
    return a.strip() if isinstance(a, str) else ('' if a is None else str(a))


def _distractors(q: dict) -> List[str]:
    ans = _answer(q)
    out, removed = [], False
    for c in _choices(q):
        if not removed and c.strip() == ans:
            removed = True
            continue
        out.append(c)
    return out


_VOCAB_QUOTE_PATTERNS = [
    re.compile('「([^」]+?)」'),
    re.compile('『([^』]+?)』'),
    re.compile('“([^”]+?)”'),
    re.compile('‘([^’]+?)’'),
    re.compile(r'"([^"]+?)"'),
    re.compile(r"(?:^|[\s(\[{:])'([^']+?)'(?=[\s).\]}?!,;:]|$)"),
    re.compile('（([^）]+?)）'),
    re.compile(r'\(([^)]+?)\)'),
]


def extract_vocab_target(question_text: str) -> Optional[str]:
    """The target word of a vocabulary stem: the SHORTEST quoted/bracketed
    span. Stems often quote the whole sentence and then the word
    (calibration 2026-11-09, zh); the word is the target."""
    spans = [m.strip() for pat in _VOCAB_QUOTE_PATTERNS
             for m in pat.findall(question_text or '') if m.strip()]
    return min(spans, key=len) if spans else None


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------

_QUESTION_CHECKS: List[Tuple[str, Callable]] = []
_TEST_CHECKS: List[Tuple[str, Callable]] = []
_PASSAGE_CHECKS: List[Tuple[str, Callable]] = []


def check(code: str, scope: Scope):
    """Register a check. Question checks: ``(q, passage, profile, tier)``;
    test checks: ``(questions, passage, profile, tier)``; passage checks:
    ``(transcript, title, profile)``. Each yields ``(message, field,
    question_index)`` tuples; the runner builds the CheckResult."""
    if code not in CHECK_MODES:
        raise ValueError(f'check {code!r} missing from CHECK_MODES')

    def deco(fn):
        {'question': _QUESTION_CHECKS, 'test': _TEST_CHECKS,
         'passage': _PASSAGE_CHECKS}[scope].append((code, fn))
        return fn
    return deco


def _emit(code: str, scope: Scope, hits, mode_override, index=None) -> List[CheckResult]:
    mode = resolve_mode(code, mode_override)
    if mode == 'off':
        return []
    out = []
    for message, fld, qidx in hits or ():
        out.append(CheckResult(
            code=code, severity=mode, scope=scope, message=message,
            question_index=index if qidx is None else qidx, field=fld,
        ))
    return out


def run_passage_checks(transcript: str, title: Optional[str], profile: LanguageProfile,
                       mode_override: Optional[str] = None) -> List[CheckResult]:
    results: List[CheckResult] = []
    for code, fn in _PASSAGE_CHECKS:
        if resolve_mode(code, mode_override) == 'off':
            continue
        results += _emit(code, 'passage', list(fn(transcript or '', title, profile)), mode_override)
    return results


def run_question_checks(q: dict, passage: str, profile: LanguageProfile, tier: Optional[int],
                        index: Optional[int] = None,
                        mode_override: Optional[str] = None) -> List[CheckResult]:
    results: List[CheckResult] = []
    for code, fn in _QUESTION_CHECKS:
        if resolve_mode(code, mode_override) == 'off':
            continue
        results += _emit(code, 'question', list(fn(q, passage or '', profile, tier)),
                         mode_override, index)
    return results


def run_test_checks(questions: Sequence[dict], passage: str, profile: LanguageProfile,
                    tier: Optional[int], mode_override: Optional[str] = None) -> List[CheckResult]:
    results: List[CheckResult] = []
    for code, fn in _TEST_CHECKS:
        if resolve_mode(code, mode_override) == 'off':
            continue
        results += _emit(code, 'test', list(fn(list(questions), passage or '', profile, tier)),
                         mode_override)
    return results


def pairwise_duplicate_checks(q: dict, previous: Sequence[dict], profile: LanguageProfile,
                              mode_override: Optional[str] = None) -> List[CheckResult]:
    """Test-scope duplicate checks for one candidate against already-kept
    questions, so the generator can regenerate before accepting it.
    ``question_index`` is the candidate's index (= len(previous))."""
    idx = len(previous)
    results: List[CheckResult] = []
    for code, fn in ((('duplicate_answer', _dup_answer_pair),
                      ('duplicate_vocab_target', _dup_vocab_pair),
                      ('duplicate_stem', _dup_stem_pair))):
        hits = []
        for j, p in enumerate(previous):
            msg = fn(p, q, profile)
            if msg:
                hits.append((f'Q{j + 1}/Q{idx + 1}: {msg}', None, idx))
        results += _emit(code, 'test', hits, mode_override)
    return results


# --------------------------------------------------------------------------
# Script checks (TASK-913)
# --------------------------------------------------------------------------

_OPENCC = None
#: Characters OpenCC t2s changes but which are also standard in simplified
#: text (or whose t2s mapping is context-dependent). Extend from calibration.
ZH_T2S_ALLOWLIST = frozenset('乾著於隻麼裡沖瞭昇')   # 昇: 毕昇 (calibration 2026-11-09)


def _t2s():
    global _OPENCC
    if _OPENCC is None:
        import opencc  # requirements.txt: opencc==1.3.1
        _OPENCC = opencc.OpenCC('t2s')
    return _OPENCC


def _not_jis(ch: str) -> bool:
    try:
        ch.encode('euc_jis_2004')
        return False
    except UnicodeEncodeError:
        return True


def foreign_chars(text: str, profile: LanguageProfile) -> List[str]:
    """Characters that do not belong to the language's writing system."""
    text = text or ''
    bad: List[str] = []
    if profile.code == 'ja':
        bad = [c for c in _CJK_RE.findall(text) if _not_jis(c)]
    elif profile.code == 'zh':
        bad = _KANA_RE.findall(text)
        cjk = ''.join(dict.fromkeys(_CJK_RE.findall(text)))
        if cjk:
            conv = _t2s().convert(cjk)
            if len(conv) == len(cjk):
                bad += [a for a, b in zip(cjk, conv) if a != b and a not in ZH_T2S_ALLOWLIST]
    elif profile.code == 'en':
        bad = _CJK_OR_KANA_RE.findall(text)
    return list(dict.fromkeys(bad))


def _question_fields(q: dict) -> List[Tuple[str, str]]:
    fields = [('question', _qtext(q))]
    fields += [(f'choices[{i}]', c) for i, c in enumerate(_choices(q))]
    return fields


@check('foreign_script', 'question')
def _foreign_script_q(q, passage, profile, tier):
    for fld, text in _question_fields(q):
        bad = foreign_chars(text, profile)
        if bad:
            yield (f"{''.join(bad)} not valid {profile.code} script in {fld}: {text[:60]}", fld, None)


@check('foreign_script', 'passage')
def _foreign_script_p(transcript, title, profile):
    for fld, text in (('transcript', transcript), ('title', title or '')):
        bad = foreign_chars(text, profile)
        if bad:
            yield (f"{''.join(bad)} not valid {profile.code} script in {fld}", fld, None)


@check('latin_in_cjk', 'question')
def _latin_in_cjk(q, passage, profile, tier):
    if not profile.is_cjk:
        return
    plow = (passage or '').lower()
    for fld, text in _question_fields(q):
        for run in _LATIN_RUN_RE.findall(text):
            if run.lower() not in plow:
                yield (f"Latin word {run!r} in {fld} not in passage", fld, None)


@check('script_above_level', 'question')
def _script_above_level(q, passage, profile, tier):
    if profile.code != 'ja' or _KANJI_RE.search(passage or ''):
        return
    for i, c in enumerate(_choices(q)):
        kanji = _KANJI_RE.findall(c)
        if kanji:
            yield (f"kanji {''.join(dict.fromkeys(kanji))} in a choice on a kana-only passage: {c[:40]}",
                   f'choices[{i}]', None)


# --------------------------------------------------------------------------
# Choice-format checks (TASK-914)
# --------------------------------------------------------------------------

LABEL_PREFIX_RE = re.compile(
    r'^\s*(?:[\(（]\s*[A-DＡ-Ｄa-d1-4１-４]\s*[\)）]|[A-DＡ-Ｄa-d1-4１-４][.．)）:：、]|[①-④])\s*'
)


def strip_label_prefixes(choices: List[str], answer: str) -> Tuple[List[str], str, bool]:
    """Remove "A. "-style labels when *all four* choices carry one.

    Returns ``(choices, answer, stripped)``. The answer is mapped to the
    stripped choice it equalled, so answer ∈ choices still holds.
    """
    if len(choices) != 4 or not all(LABEL_PREFIX_RE.match(c or '') for c in choices):
        return choices, answer, False
    new = [LABEL_PREFIX_RE.sub('', c, count=1).strip() for c in choices]
    a = (answer or '').strip()
    for old, nw in zip(choices, new):
        if old.strip() == a:
            return new, nw, True
    return new, LABEL_PREFIX_RE.sub('', a, count=1).strip(), True


@check('choice_label_prefix', 'question')
def _choice_label_prefix(q, passage, profile, tier):
    for i, c in enumerate(_choices(q)):
        if LABEL_PREFIX_RE.match(c or ''):
            yield (f"choice carries its own label: {c[:30]}", f'choices[{i}]', None)


#: Calibrated 2026-11-09: the earlier "> 1.3x the mean distractor" branch
#: produced most false alarms (ja 16/20), and counting English in words
#: flagged answers one word longer. Now characters in every language, the
#: answer must beat the LONGEST distractor by this ratio and margin.
LENGTH_RATIO = 1.4
LENGTH_MIN_MARGIN = 4      # characters


@check('answer_length_outlier', 'question')
def _answer_length_outlier(q, passage, profile, tier):
    ans, ds = _answer(q), _distractors(q)
    if not ds:
        return
    la = _char_len(ans)
    longest = max(_char_len(d) for d in ds)
    if longest and la >= LENGTH_RATIO * longest and la - longest >= LENGTH_MIN_MARGIN:
        yield (f"answer {la} chars vs longest distractor {longest}", 'answer', None)


def _char_len(s: str) -> int:
    return len(_STRIP_RE.sub('', s or ''))


def _has_absolute(s: str, profile: LanguageProfile) -> bool:
    if profile.is_cjk:
        return any(a in s for a in profile.absolutes)
    ws = set(_words(s))
    return any(a in ws for a in profile.absolutes)


@check('absolute_distractors', 'question')
def _absolute_distractors(q, passage, profile, tier):
    ds = _distractors(q)
    hits = [d for d in ds if _has_absolute(d, profile)]
    if len(hits) >= 2 and not _has_absolute(_answer(q), profile):
        yield (f"{len(hits)} distractors use absolute wording, answer does not", 'choices', None)


# --------------------------------------------------------------------------
# Copy check (TASK-915)
# --------------------------------------------------------------------------

COPY_CHECK_TYPES = frozenset({'main_idea', 'inference', 'author_purpose', 'supporting_detail'})
#: Calibrated 2026-11-09: 10-char CJK runs were common phrases (ja FPs);
#: at T1-T2 recognising the passage's own words is the skill being tested.
COPY_MIN_TIER = 3


def longest_common_run(a_units: Sequence[str], b_units: Sequence[str]) -> int:
    if not a_units or not b_units:
        return 0
    sm = difflib.SequenceMatcher(None, a_units, b_units, autojunk=False)
    return sm.find_longest_match(0, len(a_units), 0, len(b_units)).size


@check('answer_copies_passage', 'question')
def _answer_copies_passage(q, passage, profile, tier):
    if q.get('type_code') not in COPY_CHECK_TYPES:
        return
    if tier is not None and tier < COPY_MIN_TIER:
        return
    pu = profile.units(passage)
    run_a = longest_common_run(pu, profile.units(_answer(q)))
    if run_a < profile.copy_min_len:
        return
    best_d = max((longest_common_run(pu, profile.units(d)) for d in _distractors(q)), default=0)
    if run_a >= 2 * max(best_d, 1):
        unit = 'chars' if profile.is_cjk else 'words'
        yield (f"answer copies {run_a} {unit} from the passage; best distractor {best_d}", 'answer', None)


# --------------------------------------------------------------------------
# Duplicate checks (TASK-917)
# --------------------------------------------------------------------------

DUP_ANSWER_THRESHOLD = 0.6
DUP_ANSWER_SAME_TYPE_THRESHOLD = 0.45
DUP_STEM_THRESHOLD = 0.65
STEM_COMPARED_TYPES = frozenset({'literal_detail', 'supporting_detail'})


def _dup_answer_pair(a: dict, b: dict, profile) -> Optional[str]:
    sim = jaccard(profile.tokenize(_answer(a)), profile.tokenize(_answer(b)))
    same = a.get('type_code') and a.get('type_code') == b.get('type_code')
    thr = DUP_ANSWER_SAME_TYPE_THRESHOLD if same else DUP_ANSWER_THRESHOLD
    if sim >= thr:
        return f"answers {sim:.0%} similar (threshold {thr:.0%})"
    return None


def _dup_vocab_pair(a: dict, b: dict, profile) -> Optional[str]:
    if a.get('type_code') != 'vocabulary_context' or b.get('type_code') != 'vocabulary_context':
        return None
    ta, tb = extract_vocab_target(_qtext(a)), extract_vocab_target(_qtext(b))
    if ta and tb and ta == tb:
        return f"same vocabulary target {ta!r}"
    return None


def _dup_stem_pair(a: dict, b: dict, profile) -> Optional[str]:
    if a.get('type_code') not in STEM_COMPARED_TYPES or b.get('type_code') not in STEM_COMPARED_TYPES:
        return None
    sim = jaccard(profile.tokenize(_qtext(a)), profile.tokenize(_qtext(b)))
    if sim >= DUP_STEM_THRESHOLD:
        return f"stems {sim:.0%} similar"
    return None


def _pairs(questions, fn, profile):
    for j in range(1, len(questions)):
        for i in range(j):
            msg = fn(questions[i], questions[j], profile)
            if msg:
                # Index of the SECOND question: that is the one dropped
                # (developer decision 2026-11-09).
                yield (f"Q{i + 1}/Q{j + 1}: {msg}", None, j)
                break


@check('duplicate_answer', 'test')
def _duplicate_answer(questions, passage, profile, tier):
    yield from _pairs(questions, _dup_answer_pair, profile)


@check('duplicate_vocab_target', 'test')
def _duplicate_vocab_target(questions, passage, profile, tier):
    yield from _pairs(questions, _dup_vocab_pair, profile)


@check('duplicate_stem', 'test')
def _duplicate_stem(questions, passage, profile, tier):
    yield from _pairs(questions, _dup_stem_pair, profile)


# --------------------------------------------------------------------------
# Test-shape checks (TASK-918)
# --------------------------------------------------------------------------

#: Calibrated 2026-11-09. A second main_idea or author_purpose question is
#: flagged: labellers found the pair redundant in ja 18/20 and en 17/20 of
#: sampled tests (zh 7/20 — zh pairs more often split attitude vs. technique).
#: Answer overlap did not separate real from false pairs (bigram Jaccard
#: 0.0-0.6 on both sides), so the rule stays a plain count; the fixed tier
#: mix (migrations/fix_question_type_mix_t3_t5_t6.sql) no longer asks for
#: either type twice. "No detail question" fires only up to T4 — above that a
#: higher-order mix is deliberate (zh false alarms were all T5-T6).
WHOLE_PASSAGE_TYPES = ('main_idea', 'author_purpose')
DETAIL_REQUIRED_MAX_TIER = 4


@check('type_mix', 'test')
def _type_mix(questions, passage, profile, tier):
    types = [q.get('type_code') for q in questions]
    for t in WHOLE_PASSAGE_TYPES:
        if types.count(t) > 1:
            yield (f"{types.count(t)} {t} questions (a passage has one)", None, None)
    if (len(types) >= 4 and (tier is None or tier <= DETAIL_REQUIRED_MAX_TIER)
            and not ({'literal_detail', 'supporting_detail'} & set(types))):
        yield ("no literal_detail or supporting_detail question", None, None)


#: Calibrated 2026-11-09: 3 questions on a short T2 passage is fine (en 4/6
#: false alarms were T2 passages under ~100 words).
TOO_FEW_MIN_TIER = 3


@check('too_few_questions', 'test')
def _too_few_questions(questions, passage, profile, tier):
    if (tier is None or tier >= TOO_FEW_MIN_TIER) and len(questions) < 4:
        yield (f"only {len(questions)} questions", None, None)


@check('missing_title', 'passage')
def _missing_title(transcript, title, profile):
    if not (title or '').strip():
        yield ("test has no title", 'title', None)
