"""Read-only quality checks for comprehension-test questions (2026-11-11).

The browser walkthrough found tests whose questions repeat each other (two
questions with the same answer, worded almost the same) and questions
written in harder language than the passage they test. These checks flag such
tests for regeneration; they change nothing.

- ``near_duplicates``: pairs of questions in one test that share the correct
  answer and whose question texts are >= DUP_TEXT_RATIO similar. (Similar
  text alone is not enough: Japanese questions share long templates —
  "筆者の態度として最も適切なものはどれか" vs "筆者の論の運び方として…" — and are
  different questions.)
- ``missing_quotes``: words or phrases a question quotes ("turn a blind
  eye", 「出ます」, “变了很多”) that do not occur in the passage -- the question
  asks about text the learner was never shown (found live: the same English
  idiom question attached to several unrelated passages).
- ``unseen_share``: the share of the question's characters (CJK) or content
  words (spaced scripts) that never occur in the passage. Questions paraphrase,
  so only the top ~5% per script is flagged (UNSEEN_FLAG_CJK /
  UNSEEN_FLAG_SPACED, set from the live distribution on 2026-11-11: zh p97
  0.66, ja p97 0.55, en p97 0.89) as "probably above the passage".
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable

DUP_TEXT_RATIO = 0.6
UNSEEN_FLAG_CJK = 0.6
UNSEEN_FLAG_SPACED = 0.85
_QUOTED = re.compile(r'["“「『‘]([^"”」』’]{2,60})["”」』’]')
_CJK = re.compile('[぀-ヿ㐀-鿿]')
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
# Question framing that every question shares; not evidence of difficulty.
_FRAME = re.compile(r'根据文中信息|根据(这段)?文(章|字)内容|根据这段文字|文中|本文|このテキスト|本文によると|最も近い|以下哪个|意思')


def near_duplicates(questions: list[dict]) -> list[tuple[int, int, float]]:
    """(i, j, text similarity) for question pairs that look like repeats."""
    out = []
    for i in range(len(questions)):
        for j in range(i + 1, len(questions)):
            a, b = questions[i], questions[j]
            qa = set(_QUOTED.findall(a.get('question_text') or ''))
            qb = set(_QUOTED.findall(b.get('question_text') or ''))
            if qa and qb and not (qa & qb):
                continue  # same template, different word asked about ("文中の「X」の意味…")
            r = SequenceMatcher(None, a.get('question_text') or '', b.get('question_text') or '').ratio()
            same_answer = (a.get('answer') or '').strip() and a.get('answer') == b.get('answer')
            if same_answer and r >= DUP_TEXT_RATIO:
                out.append((i, j, round(r, 2)))
    return out


# Function words and question framing for spaced scripts; not difficulty.
_STOP = set('''a an the of to in on at for with by from as is are was were be been being am do does did
it its this that these those and or but not no so if then than what which who whom whose why how when
where there here he she they we you i his her their our your my me him them us one ones can could will
would should may might must shall according passage text author following best most likely mean means
meaning true false statement question answer about'''.split())


def _units(text: str, cjk: bool) -> list[str]:
    if cjk:
        return _CJK.findall(text)
    return [w for w in (x.lower() for x in _WORD.findall(text)) if w not in _STOP]


def unseen_share(question: dict, transcript: str) -> float:
    """Share of the question's characters/words not found in the passage."""
    cjk = bool(_CJK.search(transcript or ''))
    text = _FRAME.sub('', ' '.join([question.get('question_text') or ''] + list(question.get('choices') or [])))
    units = _units(text, cjk)
    if not units:
        return 0.0
    seen = set(_units(transcript or '', cjk))
    return round(sum(1 for u in units if u not in seen) / len(units), 2)


def missing_quotes(question: dict, transcript: str) -> list[str]:
    """Quoted words/phrases in the question that the passage does not contain."""
    norm = lambda x: re.sub(r'\s+', ' ', x or '').strip().lower()  # noqa: E731
    passage = norm(transcript)
    out = []
    for q in _QUOTED.findall(question.get('question_text') or ''):
        # American-style punctuation inside the quotes ("ingenuity,") and
        # ellipses joining two excerpts are not part of the quoted text.
        parts = [norm(p).strip(' ,.;:!?，。；：！？、') for p in re.split(r'…+|\.\.\.', q)]
        if any(p and p not in passage for p in parts):
            out.append(q)
    return out


def audit_test(test: dict, questions: Iterable[dict]) -> dict:
    qs = list(questions)
    transcript = test.get('transcript') or ''
    flag = UNSEEN_FLAG_CJK if _CJK.search(transcript) else UNSEEN_FLAG_SPACED
    dups = near_duplicates(qs)
    quotes = [(k, m) for k, q in enumerate(qs) if (m := missing_quotes(q, transcript))]
    hard = [(k, s) for k, q in enumerate(qs) if (s := unseen_share(q, transcript)) > flag]
    return {'test_id': test.get('id'), 'slug': test.get('slug'), 'language_id': test.get('language_id'),
            'questions': len(qs), 'near_duplicates': dups, 'missing_quotes': quotes,
            'above_passage': hard, 'flagged': bool(dups or quotes or hard)}
