"""The sentence markup shared by the exercise bank, pattern packs and guides.

    私[わたし]{は|wa-topic}毎朝[まいあさ]七時[しちじ]{に/へ|ni-time}起[お]きます。

* ``漢字[かな]``  furigana: every kanji run is followed by its reading.
* ``{answer|skill}``  a particle slot. ``answer`` may list accepted
  alternatives with ``/`` (the first is canonical); ``skill`` is a catalog
  skill id (optional in guide examples). An answer is kana, or kanji with
  furigana for the compound particles: ``{に対[たい]して|nitaishite}``.
* ``<name>``  a variable, pattern packs only.

``static/js/particles/markup.js`` is the client twin of ``parse``.
"""
import re
from typing import Dict, List, Optional, Tuple

KANJI = r'㐀-䶿一-鿿豈-﫿々〆ヶ'
KANA = r'ぁ-ゖゝゞァ-ヺー'
_TOKEN_RE = re.compile(
    r'\{([^{}|]*)(?:\|([^{}]*))?\}'            # {answer|skill}
    rf'|([{KANJI}]+)\[([^\[\]]*)\]'            # 漢字[かな]
    r'|<([a-z][a-z0-9_]*)>'                    # <var>
)
_KANJI_RE = re.compile(f'[{KANJI}]')
_KANA_ONLY_RE = re.compile(f'^[{KANA}]+$')
_READING_RE = re.compile(r'^[ぁ-ゖー]+$')
_SKILL_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
_STRAY_RE = re.compile(r'[{}\[\]|<>]')
_RUBY_RE = re.compile(rf'([{KANJI}]+)\[([^\[\]]*)\]')


def strip_reading(marked: str) -> str:
    """に対[たい]して -> に対して (the text as displayed)."""
    return _RUBY_RE.sub(lambda m: m.group(1), marked or '')


def reading_of(marked: str) -> str:
    """に対[たい]して -> にたいして (the text as typed in kana)."""
    return _RUBY_RE.sub(lambda m: m.group(2), marked or '')


def answer_errors(marked: str) -> List[str]:
    """Problems with one slot answer or distractor (kana, or kanji with furigana)."""
    errors = []
    for m in _RUBY_RE.finditer(marked or ''):
        if not _READING_RE.match(m.group(2)):
            errors.append(f'reading of {m.group(1)} must be hiragana, got "{m.group(2)}"')
    if not is_kana(_RUBY_RE.sub('', marked or '') or 'あ'):
        errors.append(f'"{marked}" must be kana, or kanji with furigana (対[たい])')
    if not marked:
        errors.append('empty answer')
    return errors


def is_kana(text: str) -> bool:
    return bool(_KANA_ONLY_RE.match(text or ''))


def parse(jp: str, *, allow_vars: bool = False) -> Tuple[List[Dict], List[Dict], List[str]]:
    """Split marked-up text into segments.

    Returns ``(segments, slots, errors)``. A segment is ``{'t': text}``,
    ``{'t': kanji, 'r': reading}``, ``{'slot': index}`` or ``{'var': name}``.
    A slot is ``{'a': canonical, 'alt': [others], 'skill': id or '',
    'raw': [marked answers], 'kana': [their readings]}``; ``a`` and ``alt``
    are the displayed text (furigana removed).
    """
    segments: List[Dict] = []
    slots: List[Dict] = []
    errors: List[str] = []
    pos = 0

    def text_segment(text: str) -> None:
        if not text:
            return
        if _KANJI_RE.search(text):
            errors.append(f'kanji without furigana in "{text}"')
        if _STRAY_RE.search(text):
            errors.append(f'stray markup character in "{text}"')
        segments.append({'t': text})

    for match in _TOKEN_RE.finditer(jp or ''):
        text_segment(jp[pos:match.start()])
        pos = match.end()
        answer, skill, kanji, reading, var = match.groups()
        if kanji is not None:
            if not _READING_RE.match(reading or ''):
                errors.append(f'reading of {kanji} must be hiragana, got "{reading}"')
            segments.append({'t': kanji, 'r': reading})
        elif var is not None:
            if not allow_vars:
                errors.append(f'variable <{var}> outside a pattern pack')
            segments.append({'var': var})
        else:
            answers = [a.strip() for a in (answer or '').split('/')]
            if not answers or not all(answers):
                errors.append(f'empty answer in slot "{match.group(0)}"')
            for a in answers:
                if a:
                    errors += [f'slot answer: {e}' for e in answer_errors(a)]
            shown = [strip_reading(a) for a in answers]
            if len(set(shown)) != len(shown):
                errors.append(f'repeated answer in slot "{match.group(0)}"')
            skill = (skill or '').strip()
            if skill and not _SKILL_RE.match(skill):
                errors.append(f'bad skill id "{skill}"')
            segments.append({'slot': len(slots)})
            slots.append({'a': shown[0] if shown else '', 'alt': shown[1:], 'skill': skill,
                          'raw': answers, 'kana': [reading_of(a) for a in answers]})
    text_segment((jp or '')[pos:])
    return segments, slots, errors


def plain(jp: str, *, blank: Optional[str] = None) -> str:
    """The sentence as plain text (no furigana). ``blank`` replaces slots."""
    segments, slots, _ = parse(jp, allow_vars=True)
    out = []
    for seg in segments:
        if 'slot' in seg:
            out.append(blank if blank is not None else slots[seg['slot']]['a'])
        elif 'var' in seg:
            out.append(f"<{seg['var']}>")
        else:
            out.append(seg['t'])
    return ''.join(out)


def expand(tpl: str, values: Dict[str, str]) -> str:
    """Substitute ``<name>`` variables (text is marked-up Japanese or English)."""
    return re.sub(r'<([a-z][a-z0-9_]*)>', lambda m: values.get(m.group(1), m.group(0)), tpl)
