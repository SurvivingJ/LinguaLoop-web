"""Audit every zh/ja prompt row for English that is *not* machine contract.

A raw count of Latin runs in `prompt_templates.template_text` is useless as a
leakage metric: a natively-authored Chinese prompt still has to contain
`{prose}`, `"question_text"` and the word `JSON`, because `str.format` and the
downstream pydantic parser require them verbatim. This script separates the two.

MACHINERY (never a leak):
  * `str.format` placeholders — both named `{prose}` and positional `{0}`
  * JSON keys — anything matched by `"key":`
  * enum-ish JSON *values* — `"key": "snake_case_value"`, e.g.
    `"question_type": "vocabulary_context"`, which the parser compares against
  * a small fixed set of structural tokens (`JSON`, `null`, `true`, `false`)

Everything else is a LEAK CANDIDATE and is printed with surrounding context so
it can be judged by eye. The distinction that matters is not the count but the
kind:

  * **content leak** — English *inside the material the model is few-shotted on*
    (an English idiom in a Chinese example passage, an English name in a
    Japanese sample text). This teaches the generator the wrong language and is
    the defect TASK-722 fixed.
  * **metalanguage leak** — English instructions around otherwise correct
    target-language content (`Author`, `Purpose`, `Tone`, `vs`). Lower risk, but
    it still pushes the generator toward English framing.
  * **wholly-English row** — the row is an English prompt filed under a CJK
    language_id. Detected separately via the CJK ratio, because run-counting
    alone cannot distinguish "an English prompt" from "a leaky CJK prompt".

Usage::

    python scripts/audit_prompt_latin.py                  # every active zh/ja row
    python scripts/audit_prompt_latin.py --lang zh
    python scripts/audit_prompt_latin.py --task question_inference --verbose
    python scripts/audit_prompt_latin.py --json out.json  # machine-readable
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

LANG_ID = {'zh': 1, 'en': 2, 'ja': 3}
ID_LANG = {v: k for k, v in LANG_ID.items()}

# Underscores bind: `question_text` is ONE run. Splitting on them manufactures
# two unmatchable tokens (`question`, `text`) and reports clean rows as dirty.
LATIN_RUN = re.compile(r'[A-Za-z][A-Za-z_]*')

PLACEHOLDER = re.compile(r'\{([A-Za-z_][A-Za-z0-9_]*)\}')
POSITIONAL = re.compile(r'\{(\d+)\}')
JSON_KEY = re.compile(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:')
# Only a *value that follows a key* counts as an enum. A bare quoted English
# phrase elsewhere in the text is exactly the leak we are hunting.
JSON_ENUM_VALUE = re.compile(r'"[A-Za-z_][A-Za-z0-9_]*"\s*:\s*"([a-z][a-z0-9_]*)"')

STRUCTURAL = frozenset({'JSON', 'json', 'null', 'true', 'false'})

CJK = re.compile(
    r'[぀-ゟ'    # hiragana
    r'゠-ヿ'     # katakana
    r'㐀-䶿'     # CJK ext A
    r'一-鿿'     # CJK unified
    r'豈-﫿]'    # compatibility ideographs
)


def machinery(text: str) -> set[str]:
    """Latin tokens this template cannot survive without."""
    allowed: set[str] = set(STRUCTURAL)
    allowed |= set(PLACEHOLDER.findall(text))
    allowed |= set(JSON_KEY.findall(text))
    allowed |= set(JSON_ENUM_VALUE.findall(text))
    # `{0}`-style templates have no named tokens to allow, but the digits are not
    # Latin runs anyway — listed here only so the intent is explicit.
    return allowed


def leaks(text: str) -> list[str]:
    allowed = machinery(text)
    return [run for run in LATIN_RUN.findall(text)
            if len(run) >= 2 and run not in allowed]


def cjk_ratio(text: str) -> float:
    """Share of CJK among CJK+Latin characters. ~0 means the row is English."""
    cjk = len(CJK.findall(text))
    latin = len(re.findall(r'[A-Za-z]', text))
    total = cjk + latin
    return (cjk / total) if total else 1.0


def contexts(text: str, runs: list[str], width: int = 28) -> list[str]:
    """One snippet per distinct leaked run, so the *kind* of leak is visible."""
    out: list[str] = []
    for run in dict.fromkeys(runs):
        idx = text.find(run)
        if idx < 0:
            continue
        start = max(0, idx - width)
        end = min(len(text), idx + len(run) + width)
        snippet = text[start:end].replace('\n', ' ⏎ ')
        out.append(f'{run!r}: …{snippet}…')
    return out


def classify(text: str, leaked: list[str]) -> str:
    ratio = cjk_ratio(text)
    if ratio < 0.15:
        return 'ENGLISH-ROW'
    if not leaked:
        return 'CLEAN'
    if ratio < 0.75:
        return 'MIXED'
    return 'LEAKY'


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--lang', choices=['zh', 'ja'],
                        help='restrict to one language (default: both)')
    parser.add_argument('--task', help='restrict to one task_name')
    parser.add_argument('--verbose', action='store_true',
                        help='print a context snippet for every leaked run')
    parser.add_argument('--json', metavar='PATH', help='also write machine-readable results')
    parser.add_argument('--all-versions', action='store_true',
                        help='include inactive rows (default: active only)')
    args = parser.parse_args()

    SupabaseFactory.initialize()
    db = get_supabase_admin()

    lang_ids = [LANG_ID[args.lang]] if args.lang else [1, 3]
    query = (db.table('prompt_templates')
               .select('task_name, language_id, version, is_active, model, template_text')
               .in_('language_id', lang_ids))
    if not args.all_versions:
        query = query.eq('is_active', True)
    if args.task:
        query = query.eq('task_name', args.task)
    rows = query.execute().data

    results = []
    for row in rows:
        text = row['template_text'] or ''
        leaked = leaks(text)
        results.append({
            'task_name': row['task_name'],
            'lang': ID_LANG[row['language_id']],
            'version': row['version'],
            'model': row['model'],
            'chars': len(text),
            'cjk_ratio': round(cjk_ratio(text), 3),
            'leaked_total': len(leaked),
            'leaked_distinct': sorted(set(leaked)),
            'status': classify(text, leaked),
        })

    order = {'ENGLISH-ROW': 0, 'MIXED': 1, 'LEAKY': 2, 'CLEAN': 3}
    results.sort(key=lambda r: (order[r['status']], -r['leaked_total'], r['task_name'], r['lang']))

    by_status: dict[str, int] = {}
    for result in results:
        by_status[result['status']] = by_status.get(result['status'], 0) + 1

    print(f'{len(results)} rows\n')
    print(f'{"status":<12} {"task_name":<42} {"lg":<3} {"v":<3} '
          f'{"cjk":<6} {"leak":<5} tokens')
    print('-' * 118)
    for result in results:
        tokens = ', '.join(result['leaked_distinct'][:6])
        if len(result['leaked_distinct']) > 6:
            tokens += f' … (+{len(result["leaked_distinct"]) - 6})'
        print(f'{result["status"]:<12} {result["task_name"]:<42} {result["lang"]:<3} '
              f'{result["version"]:<3} {result["cjk_ratio"]:<6} '
              f'{result["leaked_total"]:<5} {tokens}')

    print()
    for status in ('ENGLISH-ROW', 'MIXED', 'LEAKY', 'CLEAN'):
        if status in by_status:
            print(f'  {status:<12} {by_status[status]}')

    if args.verbose:
        lookup = {(row['task_name'], row['language_id']): row['template_text'] or ''
                  for row in rows}
        for result in results:
            if not result['leaked_distinct']:
                continue
            text = lookup[(result['task_name'], LANG_ID[result['lang']])]
            print(f'\n=== {result["task_name"]} [{result["lang"]}] '
                  f'({result["status"]}) ===')
            for line in contexts(text, leaks(text)):
                print(f'  {line}')

    if args.json:
        with open(args.json, 'w', encoding='utf-8') as handle:
            json.dump(results, handle, ensure_ascii=False, indent=2)
        print(f'\nwrote {args.json}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
