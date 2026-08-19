"""
Free-text answer normalisation for typed exercises (TASK-532).

``cloze_typed`` grades by **exact match after normalisation** — operator
decision, and the right one. An LLM grader in the attempt path would add
latency and cost to every fill-in-the-blank, and would be non-deterministic
about whether a learner got it right.

Normalisation therefore carries the whole burden of being fair. It has to
absorb the differences that are *typing artefacts* while preserving the ones
that are *the answer*:

  absorbed                              preserved
  --------                              ---------
  leading/trailing whitespace           spelling
  internal whitespace runs              the lexical choice itself
  ASCII vs full-width forms (ａ vs a)     tone marks in romanisation
  smart vs straight quotes              kana vs kanji (a different answer)
  case (Latin scripts)                  particles, inflectional endings
  Traditional vs Simplified Chinese
  trailing sentence punctuation

The Traditional→Simplified fold is the interesting one. A learner with a
Traditional IME typing 發 for a corpus that stores 发 is *right*, and refusing
that answer would punish them for their keyboard. The fold runs in one
direction only (t2s), so it never rewrites the stored key.

The accepted set
----------------
Beyond the keyed answer, an item accepts the sense's morphological variants
where they are genuinely interchangeable in the blank. That is a per-item
decision made at generation time — this module only compares — so
:func:`build_accepted` is the single place that assembles the list, and it
takes only what the generator hands it.
"""

from __future__ import annotations

import re
import unicodedata

# Sentence-final punctuation a learner may or may not type. Stripped from both
# sides of the comparison; punctuation *inside* the answer is preserved.
_TRAILING_PUNCT = '。．.!！?？,，、;；:：'

_QUOTES = {
    '‘': "'", '’': "'", '“': '"', '”': '"',
    '´': "'", 'ʼ': "'",
}

_WHITESPACE = re.compile(r'\s+')

_converter = None
_converter_loaded = False


def _t2s(text: str) -> str:
    """Fold Traditional Chinese to Simplified, or return ``text`` unchanged.

    OpenCC is optional on the serve path; if it is missing, a ZH learner typing
    Traditional simply fails to match, which is the pre-existing behaviour
    rather than a new error.
    """
    global _converter, _converter_loaded
    if not _converter_loaded:
        _converter_loaded = True
        try:
            from opencc import OpenCC
            _converter = OpenCC('t2s')
        except Exception:
            _converter = None
    if _converter is None:
        return text
    try:
        return _converter.convert(text)
    except Exception:
        return text


def normalize(
    text: str | None,
    language_id: int | None = None,
    fold_case: bool = True,
) -> str:
    """Reduce a typed answer to its comparable form.

    ``language_id`` 1 (Chinese) additionally folds Traditional to Simplified.
    ``fold_case`` is honoured for Latin scripts and is a harmless no-op for
    CJK, where ``str.casefold`` changes nothing.
    """
    if not text:
        return ''

    # NFKC collapses full-width ASCII (ａｂｃ, １２３) onto the plain forms and
    # normalises composed characters. This is what makes an answer typed with a
    # CJK IME comparable to one typed on a US keyboard.
    out = unicodedata.normalize('NFKC', str(text))
    out = ''.join(_QUOTES.get(char, char) for char in out)
    out = _WHITESPACE.sub(' ', out).strip()
    out = out.strip(_TRAILING_PUNCT).strip()

    if language_id == 1:
        out = _t2s(out)
    if fold_case:
        out = out.casefold()
    return out


def matches(
    given: str | None,
    accepted: list[str] | tuple[str, ...] | None,
    language_id: int | None = None,
) -> bool:
    """Whether a typed answer matches any accepted form."""
    if not accepted:
        return False
    needle = normalize(given, language_id)
    if not needle:
        return False
    return any(needle == normalize(item, language_id) for item in accepted)


def build_accepted(
    answer: str,
    variants: list[str] | tuple[str, ...] | None = None,
    language_id: int | None = None,
) -> list[str]:
    """The stored ``answer.accepted[]`` list for an item.

    Keeps the *surface* forms rather than the normalised ones, so stored
    content stays human-reviewable and can be re-normalised if the rules here
    change. Deduplicates on the normalised form, because ``run`` and ``Run``
    are one accepted answer, not two.
    """
    out: list[str] = []
    seen: set[str] = set()
    for candidate in [answer, *(variants or ())]:
        if not candidate:
            continue
        key = normalize(candidate, language_id)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(str(candidate).strip())
    return out


def normalization_spec(language_id: int | None) -> dict:
    """The rules applied, recorded on the item for auditability (§6.4).

    Stored rather than implied so a graded answer can be explained after the
    fact — and so a future change to these rules is visibly a change, not a
    silent re-grading of the existing corpus.
    """
    return {
        'unicode': 'NFKC',
        'whitespace': 'collapse+trim',
        'case': 'fold',
        'trailing_punctuation': 'strip',
        'quotes': 'straighten',
        'script': 't2s' if language_id == 1 else None,
    }
