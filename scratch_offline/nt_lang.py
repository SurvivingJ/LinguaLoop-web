"""Language settings shared by the tool-free fat-seed scripts.

The prompts were written for Japanese. Set NT_LANG (a registered language code: ja | zh | en | ...; default ja)
and every system prompt has "Japanese" replaced by the language's name, so the
Japanese prompts stay byte-identical. nt_pipeline.py and nt_experiment.py set
NT_LANG for the scripts they start.
"""
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.append(_REPO)  # appended: the fat-seed scripts' own modules keep precedence
from services import language_registry  # noqa: E402

# code -> (name, dim_languages.id), from services/language_registry.py. Planned
# languages are included: content is authored before the app accepts the language.
LANGUAGES = {lang.code: (lang.display, lang.id)
             for lang in language_registry.all_languages(include_planned=True)}


def code():
    lang = os.environ.get('NT_LANG', 'ja')
    if lang not in LANGUAGES:
        raise SystemExit(f'NT_LANG={lang!r}: expected one of {sorted(LANGUAGES)}')
    return lang


def name(lang=None):
    return LANGUAGES[lang or code()][0]


def language_id(lang=None):
    return LANGUAGES[lang or code()][1]


def localise(system_prompt):
    """Name the target language in a system prompt (a no-op for Japanese)."""
    lang = code()
    if lang == 'ja':
        return system_prompt
    n = name(lang)
    article = 'an' if n[0] in 'AEIOU' else 'a'
    return system_prompt.replace('a Japanese', f'{article} {n}').replace('Japanese', n)
