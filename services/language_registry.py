"""The one place that says which languages exist and what each one is like.

Every id-to-code map, "is this a CJK language" test, list of language codes a
script accepts and per-language feature gate reads this module. To add a
language, add one ``Language`` below (see wiki/features/language-registry.tech.md
for the rest of the checklist: database row, NLP processors, prompt rows).

Pure data and lookups: this module imports nothing from the application, so
``config.py``, services, scripts and offline tools can all import it.

``status``:
  * ``active``  - selectable in the app; counted in every "valid language" set.
  * ``planned`` - content is being prepared (data/language_packs/<code>/); the
    app does not accept its id, but offline tooling can name it with
    ``include_planned=True``.

The browser's copy is ``static/js/language-registry.js``, written by
``python scripts/build_language_registry_js.py`` (``--check`` in the tests).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Union

ACTIVE = 'active'
PLANNED = 'planned'

# Script families. A family decides how text is joined and typed, not which
# language it is: anything that depends on the language itself is a feature.
CJK = 'cjk'
LATIN = 'latin'

# Feature names. A feature is something the app does for some languages only.
FEATURES = frozenset({
    'pinyin',                     # pinyin payloads, pinyin trainer, hanzi<->pinyin exercises
    'tones',                      # tone identification, tone inventory
    'traditional_variants',       # traditional -> simplified folding of answers
    'furigana',                   # furigana payloads, kanji<->reading exercises
    'pitch_accent',               # pitch-accent payloads and trainer
    'particles',                  # tokenised particles, particle_selection
    'classifier_drill',           # measure-word trainer
    'counter_drill',              # counter trainer
    'grammar_drills',             # /grammar-drill content and tracking
    'pronunciation_calibration',  # the reading / pronunciation mode of calibration and placement
    'translation_exercises',      # tl_nl_translation / nl_tl_translation
})


@dataclass(frozen=True)
class Language:
    id: int
    code: str                     # ISO 639-1; dim_languages.language_code
    name: str                     # lower-case English name ('chinese'), as Config.LANGUAGES had it
    display: str                  # English display name ('Chinese')
    native_name: str              # the language's own name ('中文')
    locale: str                   # BCP 47 tag for TTS, fonts and the html lang attribute
    flag: str
    glyph: str                    # one character shown on the language's seal and cards
    script: str                   # CJK or LATIN
    status: str = ACTIVE
    legacy_codes: tuple = ()      # codes older rows and clients still send ('cn', 'jp')
    wordfreq: Optional[str] = None            # wordfreq language code, None when unsupported
    langdetect: tuple = ()                    # langdetect codes that mean this language
    web_font_sans: Optional[str] = None       # Google Fonts family spec, CJK only
    web_font_serif: Optional[str] = None
    features: frozenset = field(default_factory=frozenset)

    def __post_init__(self):
        unknown = set(self.features) - FEATURES
        if unknown:
            raise ValueError(f'{self.code}: unknown features {sorted(unknown)}')
        if self.script not in (CJK, LATIN):
            raise ValueError(f'{self.code}: unknown script family {self.script!r}')
        if self.status not in (ACTIVE, PLANNED):
            raise ValueError(f'{self.code}: unknown status {self.status!r}')

    @property
    def is_active(self) -> bool:
        return self.status == ACTIVE

    @property
    def is_cjk(self) -> bool:
        return self.script == CJK

    @property
    def spaced(self) -> bool:
        """Words are separated by spaces."""
        return self.script != CJK

    @property
    def token_joiner(self) -> str:
        return ' ' if self.spaced else ''

    @property
    def needs_ime(self) -> bool:
        """Typed answers come through an input method editor."""
        return self.script == CJK

    def has(self, feature: str) -> bool:
        if feature not in FEATURES:
            raise KeyError(f'unknown language feature {feature!r}')
        return feature in self.features


_REGISTRY: tuple = (
    Language(
        id=1, code='zh', name='chinese', display='Chinese', native_name='中文',
        locale='zh-CN', flag='🇨🇳', glyph='中', script=CJK, legacy_codes=('cn',),
        wordfreq='zh', langdetect=('zh-cn', 'zh-tw', 'zh'),
        web_font_sans='Noto+Sans+SC:wght@400;500;700', web_font_serif='Noto+Serif+SC:wght@500;700',
        features=frozenset({'pinyin', 'tones', 'traditional_variants', 'classifier_drill', 'grammar_drills',
                            'pronunciation_calibration', 'translation_exercises'}),
    ),
    Language(
        id=2, code='en', name='english', display='English', native_name='English',
        locale='en-US', flag='🇺🇸', glyph='E', script=LATIN,
        wordfreq='en', langdetect=('en',),
    ),
    Language(
        id=3, code='ja', name='japanese', display='Japanese', native_name='日本語',
        locale='ja-JP', flag='🇯🇵', glyph='日', script=CJK, legacy_codes=('jp',),
        wordfreq='ja', langdetect=('ja',),
        web_font_sans='Noto+Sans+JP:wght@400;500;700', web_font_serif='Noto+Serif+JP:wght@500;700',
        features=frozenset({'furigana', 'pitch_accent', 'particles', 'counter_drill',
                            'pronunciation_calibration', 'translation_exercises'}),
    ),
    # Content pack in data/language_packs/it/; not selectable until its wiring tasks are done.
    Language(
        id=4, code='it', name='italian', display='Italian', native_name='Italiano',
        locale='it-IT', flag='🇮🇹', glyph='I', script=LATIN, status=PLANNED,
        wordfreq='it', langdetect=('it',),
    ),
)


def _check(registry: Iterable[Language]) -> None:
    ids, codes = set(), set()
    for lang in registry:
        for key in (lang.code, *lang.legacy_codes):
            if key in codes:
                raise ValueError(f'language code {key!r} is registered twice')
            codes.add(key)
        if lang.id in ids:
            raise ValueError(f'language id {lang.id} is registered twice')
        ids.add(lang.id)


_check(_REGISTRY)
_BY_ID = {lang.id: lang for lang in _REGISTRY}
_BY_CODE = {key: lang for lang in _REGISTRY for key in (lang.code, *lang.legacy_codes)}

LanguageRef = Union[int, str, Language]


def all_languages(include_planned: bool = False) -> list:
    """Languages in id order. Planned ones only on request."""
    return [lang for lang in _REGISTRY if include_planned or lang.is_active]


def find(ref: LanguageRef, include_planned: bool = False) -> Optional[Language]:
    """The language for an id, a code (current or legacy, any case) or a Language; None when unknown."""
    if isinstance(ref, Language):
        lang = ref
    elif isinstance(ref, bool):
        return None
    elif isinstance(ref, int):
        lang = _BY_ID.get(ref)
    elif isinstance(ref, str):
        key = ref.strip().lower()
        lang = _BY_CODE.get(key)
        if lang is None and key.isdigit():
            lang = _BY_ID.get(int(key))
    else:
        return None
    if lang is None or (not lang.is_active and not include_planned):
        return None
    return lang


def get(ref: LanguageRef, include_planned: bool = False) -> Language:
    """Like ``find`` but raises ``KeyError`` naming what is registered."""
    lang = find(ref, include_planned)
    if lang is None:
        known = ', '.join(f'{x.id}={x.code}' for x in all_languages(include_planned))
        raise KeyError(f'unknown language {ref!r} (registered: {known})')
    return lang


def id_to_code(include_planned: bool = False) -> dict:
    """``{1: 'zh', 2: 'en', 3: 'ja'}`` - a fresh dict each call."""
    return {lang.id: lang.code for lang in all_languages(include_planned)}


def code_to_id(include_planned: bool = False, legacy: bool = False) -> dict:
    """``{'zh': 1, 'en': 2, 'ja': 3}``; with ``legacy`` also ``'cn'`` and ``'jp'``."""
    out = {}
    for lang in all_languages(include_planned):
        out[lang.code] = lang.id
        if legacy:
            for old in lang.legacy_codes:
                out[old] = lang.id
    return out


def id_to_display(include_planned: bool = False) -> dict:
    return {lang.id: lang.display for lang in all_languages(include_planned)}


def code_to_display(include_planned: bool = False) -> dict:
    return {lang.code: lang.display for lang in all_languages(include_planned)}


def ids(include_planned: bool = False) -> list:
    return [lang.id for lang in all_languages(include_planned)]


def codes(include_planned: bool = False) -> list:
    """Codes in id order; use ``sorted(codes())`` where a CLI printed them alphabetically."""
    return [lang.code for lang in all_languages(include_planned)]


def code_of(ref: LanguageRef, default: Optional[str] = None, include_planned: bool = False) -> Optional[str]:
    lang = find(ref, include_planned)
    return lang.code if lang else default


def id_of(ref: LanguageRef, default: Optional[int] = None, include_planned: bool = False) -> Optional[int]:
    lang = find(ref, include_planned)
    return lang.id if lang else default


def has_feature(ref: LanguageRef, feature: str) -> bool:
    """False for an unknown language; KeyError for an unknown feature name."""
    if feature not in FEATURES:
        raise KeyError(f'unknown language feature {feature!r}')
    lang = find(ref, include_planned=True)
    return bool(lang and feature in lang.features)


def ids_with(feature: str, include_planned: bool = False) -> list:
    if feature not in FEATURES:
        raise KeyError(f'unknown language feature {feature!r}')
    return [lang.id for lang in all_languages(include_planned) if feature in lang.features]


def codes_with(feature: str, include_planned: bool = False) -> list:
    return [get(i, include_planned=True).code for i in ids_with(feature, include_planned)]


def cjk_ids(include_planned: bool = False) -> list:
    return [lang.id for lang in all_languages(include_planned) if lang.is_cjk]


def cjk_codes(include_planned: bool = False) -> list:
    return [lang.code for lang in all_languages(include_planned) if lang.is_cjk]


def is_cjk(ref: LanguageRef) -> bool:
    lang = find(ref, include_planned=True)
    return bool(lang and lang.is_cjk)


def token_joiner(ref: LanguageRef) -> str:
    """'' for unspaced scripts, ' ' otherwise (and for an unknown language)."""
    lang = find(ref, include_planned=True)
    return lang.token_joiner if lang else ' '


def needs_ime(ref: LanguageRef) -> bool:
    lang = find(ref, include_planned=True)
    return bool(lang and lang.needs_ime)


def native_language_choices(default_code: str = 'en') -> list:
    """Active languages for a "what is your native language" picker: the default first, then id order."""
    langs = all_languages()
    return [x for x in langs if x.code == default_code] + [x for x in langs if x.code != default_code]


def script_family(ref: LanguageRef) -> str:
    """'cjk' / 'latin'; '' for an unknown language."""
    lang = find(ref, include_planned=True)
    return lang.script if lang else ''


def wordfreq_codes(include_planned: bool = False) -> dict:
    """``{app code: wordfreq code}`` for languages wordfreq covers."""
    return {lang.code: lang.wordfreq for lang in all_languages(include_planned) if lang.wordfreq}


def langdetect_to_code(include_planned: bool = False) -> dict:
    return {ld: lang.code for lang in all_languages(include_planned) for ld in lang.langdetect}


def legacy_config() -> dict:
    """The shape ``Config.LANGUAGES`` has always had: ``{id: {'code', 'name', 'display'}}``."""
    return {lang.id: {'code': lang.code, 'name': lang.name, 'display': lang.display}
            for lang in all_languages()}


def browser_payload() -> dict:
    """What static/js/language-registry.js carries. Planned languages are included and marked."""
    return {'languages': [
        {'id': lang.id, 'code': lang.code, 'name': lang.display, 'nativeName': lang.native_name,
         'locale': lang.locale, 'flag': lang.flag, 'glyph': lang.glyph, 'script': lang.script, 'spaced': lang.spaced,
         'active': lang.is_active, 'legacyCodes': list(lang.legacy_codes),
         'fontSans': lang.web_font_sans, 'fontSerif': lang.web_font_serif,
         'features': sorted(lang.features)}
        for lang in all_languages(include_planned=True)]}
