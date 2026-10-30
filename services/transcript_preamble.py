"""Detect and strip generation preambles from test transcripts (TASK-900).

Some ``tests.transcript`` values begin with text the prose writer was never
meant to emit — a note about the requested level, addressed to the prompt
author rather than the learner, e.g.::

    この文章は、T3レベル（B1-B2）の学習者向けに、…について解説します。--- 小さなロボットアームを作ろう！…
    (Note: The prompt designates Level T2, which maps to the B1-B2 intermediate tier …).\\n\\nOrgan donation …
    Level Definitions & Target Audience Analysis:\\n   Target Level: A1-A2 (Beginner)\\n   …\\n\\nLong ago, …

Three preamble shapes are recognised, in this order:

``separator``
    A lead that names a level or tier (``T1``–``T6``, a CEFR code such as
    ``B1-B2``, ``レベル``, ``级别``/``級別``, ``level``) **or** starts with one of
    the meta openers, followed by a ``---`` separator within the first
    :data:`SEPARATOR_WINDOW` characters. Everything up to and including the
    separator and the whitespace after it is stripped.

``sentence``
    A first sentence that starts with one of :data:`SENTENCE_OPENERS`
    (``この文章は``, ``本文``, ``This passage``, ``This article``) with no
    separator. The whole first sentence and the whitespace after it is
    stripped.

``block``
    A leading paragraph (text before the first blank line) that is clearly
    prompt metadata: either a parenthetical note ``(Note: …)`` / ``(…)`` or a
    header line ending in ``:``, **and** naming an explicit tier code
    (``T1``–``T6`` or a CEFR code). The paragraph and the blank line are
    stripped. A bare ``level`` is not enough for this shape — a legitimate
    opening paragraph may well use the word.

A legitimate first sentence that merely contains ``T3`` (``The T3 robot arm
can grip small objects.``) matches none of these: there is no separator, no
meta opener, and it is neither a parenthetical nor a header.

The module has no I/O and no project imports so it can be unit-tested and
imported by both the audit script and later segmenter checks.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

__all__ = [
    'PreambleMatch',
    'SENTENCE_OPENERS',
    'SEPARATOR',
    'SEPARATOR_WINDOW',
    'detect_preamble',
    'strip_preamble',
    'transcript_hash',
]

SEPARATOR = '---'
#: The separator must appear within this many characters of the start.
SEPARATOR_WINDOW = 400
#: A leading paragraph longer than this is prose, not metadata.
BLOCK_WINDOW = 900

SENTENCE_OPENERS: tuple[str, ...] = ('この文章は', '本文', 'This passage', 'This article')

# Explicit tier codes: T1..T6 and CEFR A1..C2 (optionally a range such as B1-B2),
# not embedded in a longer alphanumeric token.
_TIER_CODE = r'(?<![A-Za-z0-9])(?:T[1-6]|[ABC][12](?:\s*[-–~〜]\s*[ABC][12])?)(?![A-Za-z0-9])'
TIER_CODE_RE = re.compile(_TIER_CODE)
# Anything that names a level, including the bare word in three languages.
LEVEL_RE = re.compile(_TIER_CODE + r'|レベル|级别|級別|(?<![A-Za-z])[Ll]evel(?![A-Za-z])')

# Sentence terminators: CJK full stops / marks, or an ASCII terminator followed
# by whitespace or end of text (so "B1-B2" and "e.g." do not end a sentence).
_SENTENCE_END_RE = re.compile(r'[。！？]|[.!?](?=\s|$)')


@dataclass(frozen=True)
class PreambleMatch:
    """A detected preamble. ``cleaned`` is the transcript without it."""
    kind: str          # 'separator' | 'sentence' | 'block'
    preamble: str      # the stripped text, exactly as it appeared (no trailing whitespace)
    cleaned: str


def transcript_hash(text: str) -> str:
    """Hex sha256 of ``text`` as UTF-8 — the value stored in ``tests.transcript_hash``."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _first_sentence_end(text: str) -> int | None:
    """Index just past the first sentence terminator, or None."""
    m = _SENTENCE_END_RE.search(text)
    return m.end() if m else None


def _starts_with_opener(text: str) -> bool:
    return text.lstrip().startswith(SENTENCE_OPENERS)


def _match_separator(text: str) -> PreambleMatch | None:
    window = text[:SEPARATOR_WINDOW]
    pos = window.find(SEPARATOR)
    if pos <= 0:
        return None
    lead = text[:pos]
    lead_stripped = lead.strip()
    if not lead_stripped:
        return None
    # The lead is one or two sentences at most, and must look like metadata.
    if len(_SENTENCE_END_RE.findall(lead_stripped)) > 2:
        return None
    if not (LEVEL_RE.search(lead_stripped) or _starts_with_opener(lead_stripped)):
        return None
    end = pos + len(SEPARATOR)
    # A markdown-style run of dashes (----) counts as the separator too.
    while end < len(text) and text[end] == '-':
        end += 1
    cleaned = text[end:].lstrip()
    if not cleaned:
        return None
    return PreambleMatch('separator', lead.rstrip(), cleaned)


def _match_sentence(text: str) -> PreambleMatch | None:
    if not _starts_with_opener(text):
        return None
    end = _first_sentence_end(text)
    if end is None:
        return None
    cleaned = text[end:].lstrip()
    if not cleaned:
        return None
    return PreambleMatch('sentence', text[:end].strip(), cleaned)


def _match_block(text: str) -> PreambleMatch | None:
    m = re.search(r'\n[ \t]*\n', text[:BLOCK_WINDOW])
    if m is None:
        return None
    block = text[:m.start()]
    stripped = block.strip()
    if not stripped or not TIER_CODE_RE.search(stripped):
        return None
    first_line = stripped.splitlines()[0].rstrip()
    is_parenthetical = stripped.startswith(('(', '（')) and stripped.rstrip('.。').endswith((')', '）'))
    is_header = first_line.endswith((':', '：'))
    if not (is_parenthetical or is_header):
        return None
    cleaned = text[m.end():].lstrip()
    if not cleaned:
        return None
    return PreambleMatch('block', stripped, cleaned)


def detect_preamble(text: str | None) -> PreambleMatch | None:
    """Return the preamble at the start of ``text``, or None when it is clean."""
    if not text:
        return None
    text = text.lstrip('﻿')
    for matcher in (_match_separator, _match_sentence, _match_block):
        found = matcher(text)
        if found is not None:
            return found
    return None


def strip_preamble(text: str) -> str:
    """``text`` without its preamble; unchanged when there is none."""
    found = detect_preamble(text)
    return found.cleaned if found else text
