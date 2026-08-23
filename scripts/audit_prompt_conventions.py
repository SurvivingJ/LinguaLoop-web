#!/usr/bin/env python3
"""Audit every ACTIVE ``prompt_templates`` row against three house conventions.

Read-only. Writes nothing, calls no model.

    1. LANGUAGE PURITY  — a zh/ja prompt must not carry English prose, and an en
       prompt must not carry CJK prose. Machine contract is NOT a violation:
       ``str.format`` placeholders, JSON keys and parser enum *values* have to
       appear verbatim in every language or the downstream parser breaks. This
       check delegates the machinery/leak split to ``audit_prompt_latin`` rather
       than re-deriving it — see that script's header for why a raw Latin-run
       count is a useless metric.

    2. NUMERIC JSON INDICES — where a prompt dictates a JSON output shape, the
       enumerated fields and option keys should be integer indices, not spelled-
       out labels. Two distinct things count, and they are reported separately
       because they have different failure modes:
         * numeric KEYS   — ``{"0": ..., "1": ...}`` option maps
         * index-valued ENUMS — ``"category": 0`` with a legend, rather than
           ``"category": "grammatical"``
       Note the two live numberings are both legitimate and must not be
       "unified": ladder option maps are 0-based (0 = first option, 9 = escape
       hatch) while P1/P2 maps are 1-based.

    3. AGE TIERS, NOT CEFR — ``VALID_TIERS = T1..T6`` replaced CEFR A1-C2
       project-wide (``services/conversation_generation/categorical_maps.py``,
       which still carries ``CEFR_TO_TIER`` purely as a migration map). A live
       prompt that instructs a model in CEFR bands is off-convention. HSK/JLPT
       mentions are reported separately: they are national exam scales, not the
       CEFR ladder, and may be legitimate vocabulary-selection references.

Every finding is emitted with enough context to be judged by eye; nothing is
auto-classified as a defect that a human would need to re-derive.

Usage::

    python scripts/audit_prompt_conventions.py
    python scripts/audit_prompt_conventions.py --check cefr
    python scripts/audit_prompt_conventions.py --lang zh --verbose
    python scripts/audit_prompt_conventions.py --json > findings.json
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
from scripts.audit_prompt_latin import cjk_ratio, leaks  # noqa: E402

LANG_ID = {'zh': 1, 'en': 2, 'ja': 3}
ID_LANG = {v: k for k, v in LANG_ID.items()}
CJK_LANGS = ('zh', 'ja')

# --- check 3 patterns -------------------------------------------------------
# Word-bounded so 'B1' in 'VITAMIN B12' or a bare 'C2' column ref does not fire.
CEFR_RE = re.compile(r'(?<![A-Za-z0-9])(A1|A2|B1|B2|C1|C2)(?![A-Za-z0-9])')
# NOT \bCEFR\b: CJK codepoints are \w in Python, so 'CEFR等级' / 'CEFRレベル' have no
# word boundary after the R and a \b pattern silently misses every zh/ja row.
CEFR_WORD_RE = re.compile(r'(?<![A-Za-z0-9])CEFR(?![A-Za-z0-9])', re.I)
HSK_RE = re.compile(r'\bHSK\s*-?\s*\d?\b', re.I)
JLPT_RE = re.compile(r'\bJLPT\b|\bN[1-5](?![A-Za-z0-9])')
TIER_RE = re.compile(r'(?<![A-Za-z0-9])T[1-6](?![A-Za-z0-9])')

# --- check 2 patterns -------------------------------------------------------
JSON_KEY_RE = re.compile(r'"([^"\\]{1,40})"\s*:')
# `"field": 0` / `"field": 2,` — an index-valued enum field.
INT_VALUED_RE = re.compile(r'"([A-Za-z_][A-Za-z0-9_]{0,39})"\s*:\s*-?\d+\s*[,}\n]')
# `"field": "snake_case_label"` — a spelled-out enum value. Excludes free-text
# fields, which legitimately hold prose rather than an enum member.
STR_VALUED_RE = re.compile(r'"([A-Za-z_][A-Za-z0-9_]{0,39})"\s*:\s*"([a-z][a-z0-9_]{2,39})"')
FREE_TEXT_KEYS = {
    'question_text', 'explanation', 'reason', 'text', 'prose', 'title', 'sentence',
    'definition', 'answer', 'content', 'topic', 'summary', 'notes', 'gloss',
    'translation', 'example', 'prompt', 'comment', 'rationale', 'feedback',
}
# Mentions that a prompt dictates SOME json output shape at all.
JSON_MENTION_RE = re.compile(r'\bJSON\b|\{\s*"', re.I)


def numeric_key_profile(text: str) -> dict:
    """Split the JSON keys a prompt dictates into numeric vs named, and find
    enum-ish fields carrying a spelled-out label where an index would do."""
    keys = JSON_KEY_RE.findall(text)
    numeric = [k for k in keys if k.isdigit()]
    named = [k for k in keys if not k.isdigit()]
    int_valued = sorted(set(INT_VALUED_RE.findall(text)))
    str_valued = sorted({
        f'{k}="{v}"' for k, v in STR_VALUED_RE.findall(text)
        if k not in FREE_TEXT_KEYS
    })
    return {
        'numeric_keys': len(numeric),
        'named_keys': len(named),
        'index_valued_fields': int_valued,
        'label_valued_fields': str_valued,
        'dictates_json': bool(JSON_MENTION_RE.search(text)),
    }


def tier_profile(text: str) -> dict:
    return {
        'cefr_bands': sorted(set(CEFR_RE.findall(text))),
        'cefr_word': bool(CEFR_WORD_RE.search(text)),
        'hsk': sorted(set(m.strip() for m in HSK_RE.findall(text))),
        'jlpt': sorted(set(JLPT_RE.findall(text))),
        'age_tiers': sorted(set(TIER_RE.findall(text))),
    }


def language_profile(text: str, lang: str) -> dict:
    """Leak profile. For zh/ja this is English-in-CJK (delegated); for en it is
    the mirror image — CJK codepoints in an English prompt."""
    ratio = cjk_ratio(text)
    if lang in CJK_LANGS:
        leaked = leaks(text)
        return {
            'cjk_ratio': round(ratio, 3),
            'leaked_distinct': sorted(set(leaked)),
            'leaked_total': len(leaked),
            'wholly_wrong_language': ratio < 0.10,
        }
    return {
        'cjk_ratio': round(ratio, 3),
        'leaked_distinct': [],
        'leaked_total': 0,
        # An en prompt that is mostly CJK is filed under the wrong language_id.
        'wholly_wrong_language': ratio > 0.25,
    }


def excerpt(text: str, needle: str, width: int = 34) -> str:
    i = text.find(needle)
    if i == -1:
        return ''
    lo, hi = max(0, i - width), min(len(text), i + len(needle) + width)
    return ('…' if lo else '') + text[lo:hi].replace('\n', '⏎') + ('…' if hi < len(text) else '')


def audit_row(row: dict) -> dict:
    text = row['template_text'] or ''
    lang = ID_LANG.get(row['language_id'], str(row['language_id']))
    return {
        'task_name': row['task_name'],
        'lang': lang,
        'version': row['version'],
        'model': row.get('model'),
        'chars': len(text),
        'language': language_profile(text, lang),
        'json': numeric_key_profile(text),
        'tiers': tier_profile(text),
        '_text': text,
    }


def report(results: list[dict], checks: set[str], verbose: bool) -> None:
    counts = ', '.join('%s=%d' % (code, sum(1 for r in results if r['lang'] == code))
                       for code in ('en', 'zh', 'ja'))
    print('Audited %d active prompt rows (%s)\n' % (len(results), counts))

    # ---- 1. language purity ------------------------------------------------
    if 'language' in checks:
        wrong_lang = [r for r in results if r['language']['wholly_wrong_language']]
        leaky = [r for r in results
                 if r['lang'] in CJK_LANGS and r['language']['leaked_total'] and
                 not r['language']['wholly_wrong_language']]
        print('=' * 78)
        print(f'1. LANGUAGE PURITY — {len(wrong_lang)} wrong-language row(s), '
              f'{len(leaky)} row(s) with non-contract leakage')
        print('=' * 78)
        for r in wrong_lang:
            print(f'  WRONG-LANGUAGE  {r["task_name"]:<42} [{r["lang"]}] v{r["version"]} '
                  f'cjk_ratio={r["language"]["cjk_ratio"]}')
        for r in sorted(leaky, key=lambda r: -r['language']['leaked_total']):
            print(f'  LEAK  {r["task_name"]:<42} [{r["lang"]}] v{r["version"]} '
                  f'cjk={r["language"]["cjk_ratio"]} n={r["language"]["leaked_total"]:<3} '
                  f'{r["language"]["leaked_distinct"][:12]}')
            if verbose:
                for tok in r['language']['leaked_distinct'][:6]:
                    print(f'        · {excerpt(r["_text"], tok)}')
        if not wrong_lang and not leaky:
            print('  none')
        print()

    # ---- 2. numeric json indices ------------------------------------------
    if 'json' in checks:
        dictating = [r for r in results if r['json']['dictates_json']]
        with_numeric = [r for r in dictating if r['json']['numeric_keys']]
        with_index_enum = [r for r in dictating if r['json']['index_valued_fields']]
        label_only = [r for r in dictating
                      if r['json']['label_valued_fields']
                      and not r['json']['numeric_keys']
                      and not r['json']['index_valued_fields']]
        print('=' * 78)
        print(f'2. NUMERIC JSON INDICES — {len(dictating)} row(s) dictate a JSON shape; '
              f'{len(with_numeric)} use numeric keys, {len(with_index_enum)} use index-valued '
              f'enums, {len(label_only)} use spelled-out labels only')
        print('=' * 78)
        for r in sorted(label_only, key=lambda r: (r['task_name'], r['lang'])):
            print(f'  LABELS-ONLY  {r["task_name"]:<42} [{r["lang"]}] v{r["version"]} '
                  f'{r["json"]["label_valued_fields"][:6]}')
            if verbose:
                for field in r['json']['label_valued_fields'][:4]:
                    key = '"%s"' % field.split('=')[0]
                    print('        · %s' % excerpt(r['_text'], key))
        if not label_only:
            print('  none')
        print()

    # ---- 3. age tiers, not CEFR -------------------------------------------
    if 'cefr' in checks:
        cefr = [r for r in results if r['tiers']['cefr_bands'] or r['tiers']['cefr_word']]
        exam = [r for r in results if (r['tiers']['hsk'] or r['tiers']['jlpt'])
                and r not in cefr]
        print('=' * 78)
        print(f'3. AGE TIERS vs CEFR — {len(cefr)} row(s) reference CEFR, '
              f'{len(exam)} reference HSK/JLPT only')
        print('=' * 78)
        for r in sorted(cefr, key=lambda r: (r['task_name'], r['lang'])):
            print(f'  CEFR  {r["task_name"]:<42} [{r["lang"]}] v{r["version"]} '
                  f'bands={r["tiers"]["cefr_bands"]} word={r["tiers"]["cefr_word"]} '
                  f'also_has_T1-6={r["tiers"]["age_tiers"]}')
            for band in (r['tiers']['cefr_bands'] or ['CEFR'])[:3]:
                print(f'        · {excerpt(r["_text"], band)}')
        for r in sorted(exam, key=lambda r: (r['task_name'], r['lang'])):
            print(f'  EXAM-SCALE  {r["task_name"]:<42} [{r["lang"]}] v{r["version"]} '
                  f'hsk={r["tiers"]["hsk"]} jlpt={r["tiers"]["jlpt"]}')
            if verbose:
                for tok in (r['tiers']['hsk'] + r['tiers']['jlpt'])[:3]:
                    print(f'        · {excerpt(r["_text"], tok)}')
        if not cefr and not exam:
            print('  none')
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--lang', choices=sorted(LANG_ID), help='restrict to one language')
    parser.add_argument('--task', help='restrict to one task_name')
    parser.add_argument('--check', choices=['language', 'json', 'cefr'], action='append',
                        help='run only these checks (repeatable; default: all)')
    parser.add_argument('--verbose', action='store_true', help='print surrounding context per hit')
    parser.add_argument('--json', dest='as_json', action='store_true',
                        help='emit raw findings as JSON instead of the report')
    args = parser.parse_args()

    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    SupabaseFactory.initialize()
    db = get_supabase_admin()

    query = (db.table('prompt_templates')
               .select('task_name, language_id, version, is_active, model, template_text')
               .eq('is_active', True)
               .in_('language_id', [LANG_ID[args.lang]] if args.lang else list(LANG_ID.values())))
    if args.task:
        query = query.eq('task_name', args.task)
    rows = query.execute().data or []
    if not rows:
        print('No active prompt_templates rows matched.')
        return 1

    results = [audit_row(r) for r in rows]
    results.sort(key=lambda r: (r['task_name'], r['lang']))

    if args.as_json:
        print(json.dumps([{k: v for k, v in r.items() if k != '_text'} for r in results],
                         ensure_ascii=False, indent=2))
        return 0

    report(results, set(args.check or ['language', 'json', 'cefr']), args.verbose)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
