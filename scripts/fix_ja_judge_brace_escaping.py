"""Escape the literal JSON braces in the four ja ladder judge prompts.

The rows were seeded as a block (ids 186-189) with their example output pasted
as real JSON::

    {"1": {"rating": 5, "reason": "clean"}, ...}

``str.format`` reads ``{"1"`` as a replacement field and raises
``KeyError: '"1"'``. Every en and zh sibling of these four tasks doubles the
braces correctly, so this is a defect in one seeding batch, not a convention.

Consequence: **no ja sense has ever cleared the ladder.** ``VocabAssetPipeline``
calls ``judge_p1_sentences`` before anything else, and the ``.format()`` at
``judges/p1_sentences.py:82`` sits outside the ``try`` that guards template
loading — so the KeyError propagates rather than degrading to ``safe_accept``.
``word_assets`` has 0 ja rows, and this is why.

The fix is mechanical, not editorial: no Japanese is rewritten, only braces are
doubled, so it needs no native-review pass.

Method
------
Doubling every brace would destroy the real placeholders. Instead:

1. Replace each ``{identifier}`` with a sentinel.
2. Double every brace that remains — by construction these are all literal.
3. Restore the sentinels.

Three assertions before anything is written:

* the field-name set is **identical** before and after (proves no real
  placeholder was eaten),
* every field name after the fix is a plain identifier (proves no literal
  brace survived),
* ``format_map`` over an auto-blank mapping succeeds (proves the template can
  actually be rendered).

Versioned, never overwritten — the incumbent is deactivated and a new
``max(version)+1`` row inserted, so rollback is one ``is_active`` flip.

Usage::

    python scripts/fix_ja_judge_brace_escaping.py --dry-run
    python scripts/fix_ja_judge_brace_escaping.py
"""

from __future__ import annotations

import argparse
import os
import re
import string
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

JA = 3

# The four rows the asymmetry scan identified: ja flagged, en+zh clean.
TARGET_TASKS = (
    'ladder_p1_sentence_judge',
    'ladder_l1_distractor_judge',
    'ladder_collocation_judge',
    'ladder_sentence_validity_judge',
)

PLACEHOLDER = re.compile(r'\{([A-Za-z_][A-Za-z0-9_]*)\}')
IDENT = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')


class _Blank(dict):
    def __missing__(self, key):  # noqa: D105
        return ''


def fields_of(text: str) -> list[str]:
    return [f for _, f, _, _ in string.Formatter().parse(text) if f]


def escape_literal_braces(text: str) -> str:
    """Double every brace that is not part of a ``{identifier}`` placeholder."""
    saved: list[str] = []

    def stash(m: re.Match) -> str:
        saved.append(m.group(1))
        return f'\x00{len(saved) - 1}\x00'

    protected = PLACEHOLDER.sub(stash, text)
    doubled = protected.replace('{', '{{').replace('}', '}}')
    for i, name in enumerate(saved):
        doubled = doubled.replace(f'\x00{i}\x00', '{' + name + '}')
    return doubled


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    SupabaseFactory.initialize()
    db = get_supabase_admin()

    rows = (db.table('prompt_templates')
              .select('id, task_name, version, model, provider, template_text')
              .eq('language_id', JA).eq('is_active', True)
              .in_('task_name', list(TARGET_TASKS)).execute().data or [])
    found = {r['task_name']: r for r in rows}

    problems: list[str] = []
    writes: list[tuple] = []

    for task in TARGET_TASKS:
        row = found.get(task)
        if row is None:
            problems.append(f'{task}: no active ja row'); continue

        old = row['template_text']
        before = fields_of(old)
        literal = [f for f in before if not IDENT.fullmatch(f)]
        if not literal:
            problems.append(
                f'{task}: no literal-brace field found — row already fixed or '
                f'drifted since the scan; refusing to write a no-op version')
            continue

        new = escape_literal_braces(old)
        after = fields_of(new)

        # 1. no real placeholder was consumed or invented
        real_before = sorted({f for f in before if IDENT.fullmatch(f)})
        real_after = sorted(set(after))
        if real_before != real_after:
            problems.append(f'{task}: placeholder set changed '
                            f'{real_before} -> {real_after}')
            continue
        # 2. nothing literal survived
        still = [f for f in after if not IDENT.fullmatch(f)]
        if still:
            problems.append(f'{task}: literal braces survive: {still[:5]}')
            continue
        # 3. it actually renders
        try:
            new.format_map(_Blank())
        except Exception as exc:
            problems.append(f'{task}: still unrenderable: {type(exc).__name__}: {exc}')
            continue

        writes.append((row, new, sorted(set(literal))))
        print(f'  READY {task} v{row["version"]} (id {row["id"]})  '
              f'escaped {sorted(set(literal))[:4]}  '
              f'placeholders preserved: {real_before}')

    if problems:
        print('\nABORT — nothing written:')
        for p in problems:
            print(f'  ! {p}')
        return 1

    if args.dry_run:
        print('\nDry run: validation passed, nothing written.')
        return 0

    print('\nApplying:')
    for row, new, literal in writes:
        maxv = (db.table('prompt_templates').select('version')
                  .eq('task_name', row['task_name']).eq('language_id', JA)
                  .order('version', desc=True).limit(1)
                  .execute().data[0]['version'])
        nextv = maxv + 1
        db.table('prompt_templates').insert({
            'task_name': row['task_name'], 'language_id': JA, 'version': nextv,
            'template_text': new, 'is_active': True,
            'model': row['model'], 'provider': row['provider'],
        }).execute()
        db.table('prompt_templates').update({'is_active': False}) \
          .eq('id', row['id']).execute()
        print(f'  WROTE {row["task_name"]} v{row["version"]} -> v{nextv} '
              f'(id {row["id"]} deactivated)')

    print('\nVerifying live state:')
    failures = 0
    for task in TARGET_TASKS:
        r = (db.table('prompt_templates').select('id, version, template_text')
               .eq('task_name', task).eq('language_id', JA).eq('is_active', True)
               .order('version', desc=True).limit(1).execute().data or [None])[0]
        if r is None:
            print(f'  FAIL  {task}: no active row'); failures += 1; continue
        bad = [f for f in fields_of(r['template_text']) if not IDENT.fullmatch(f)]
        try:
            r['template_text'].format_map(_Blank())
            renders = True
        except Exception:
            renders = False
        if bad or not renders:
            print(f'  FAIL  {task} v{r["version"]}: literal={bad[:3]} renders={renders}')
            failures += 1
        else:
            print(f'  OK    {task} v{r["version"]} (id {r["id"]}) renders clean')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
