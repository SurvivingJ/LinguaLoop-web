"""Language settings shared by the tool-free fat-seed scripts.

The prompts were written for Japanese. Set NT_LANG (ja | zh | en; default ja)
and every system prompt has "Japanese" replaced by the language's name, so the
Japanese prompts stay byte-identical. nt_pipeline.py and nt_experiment.py set
NT_LANG for the scripts they start.
"""
import os

LANGUAGES = {  # code -> (name, dim_languages.id)
    'ja': ('Japanese', 3),
    'zh': ('Chinese', 1),
    'en': ('English', 2),
}


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
