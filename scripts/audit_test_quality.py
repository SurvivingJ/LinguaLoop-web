"""Read-only library audit: run every test quality check over every test (TASK-919).

Runs services/test_generation/quality_checks.py over the stored tests and
questions, with every check forced to 'flag' (the audit reports; it never
gates), and writes:

  <out>/findings.csv   language, slug, test_id, tier, question_id, type_code,
                       scope, code, field, message
  <out>/summary.md     counts by language x check, tests with findings,
                       top tests by finding count

It never writes to the database.

Usage::

    python scripts/audit_test_quality.py                    # all languages
    python scripts/audit_test_quality.py --lang ja --limit 5
    python scripts/audit_test_quality.py --test-id <uuid> --test-id <uuid>
    python scripts/audit_test_quality.py --input-json dump.json   # offline

``--input-json`` takes a list of tests, each ``{id, slug, title, transcript,
language_code, target_age_tier, questions: [{id, question_id, question_text,
choices, answer, type_code}]}`` — the same shape ``load_tests`` returns.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from collections import Counter, defaultdict
from datetime import date
from typing import Dict, Iterable, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path[:0] = [ROOT]

from services.test_generation import quality_checks as qc  # noqa: E402

logger = logging.getLogger('audit_test_quality')

PAGE = 500
FIELDS = ['language', 'slug', 'test_id', 'tier', 'question_id', 'type_code',
          'scope', 'code', 'field', 'message']


# ---------------------------------------------------------------- loading

def _paged(query_fn) -> Iterable[dict]:
    start = 0
    while True:
        rows = query_fn(start, start + PAGE - 1).data or []
        yield from rows
        if len(rows) < PAGE:
            return
        start += PAGE


def _answer_text(a) -> str:
    if isinstance(a, str):
        return a
    return '' if a is None else json.dumps(a, ensure_ascii=False)


def load_tests(db, lang: Optional[str], test_ids: List[str], include_inactive: bool,
               limit: Optional[int]) -> List[dict]:
    langs = {r['id']: r['language_code'] for r in
             db.table('dim_languages').select('id, language_code').execute().data}
    types = {r['id']: r['type_code'] for r in
             db.table('dim_question_types').select('id, type_code').execute().data}

    def tq(lo, hi):
        q = db.table('tests').select(
            'id, slug, title, transcript, language_id, target_age_tier, is_active, created_at')
        if not include_inactive:
            q = q.eq('is_active', True)
        if test_ids:
            q = q.in_('id', test_ids)
        if lang:
            lid = next(k for k, v in langs.items() if v == lang)
            q = q.eq('language_id', lid)
        return q.order('created_at').order('id').range(lo, hi).execute()

    tests = list(_paged(tq))
    if limit:
        tests = tests[:limit]
    by_id: Dict[str, dict] = {}
    for t in tests:
        t['language_code'] = langs.get(t['language_id'])
        t['questions'] = []
        by_id[t['id']] = t

    ids = list(by_id)
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]

        def qq(lo, hi, chunk=chunk):
            return (db.table('questions')
                    .select('id, test_id, question_id, question_type_id, question_text, choices, answer')
                    .in_('test_id', chunk).order('question_id').range(lo, hi).execute())
        for q in _paged(qq):
            q['type_code'] = types.get(q['question_type_id'])
            q['answer'] = _answer_text(q.get('answer'))
            by_id[q['test_id']]['questions'].append(q)
    return tests


# ---------------------------------------------------------------- audit

def audit(tests: List[dict]) -> List[dict]:
    rows: List[dict] = []
    for t in tests:
        lang = t.get('language_code')
        if lang not in ('ja', 'zh', 'en'):
            continue
        profile = qc.get_profile(lang)
        tier = t.get('target_age_tier')
        passage = t.get('transcript') or ''
        qs = [dict(q, question=q.get('question_text') or q.get('question') or '')
              for q in t.get('questions', [])]
        base = {'language': lang, 'slug': t.get('slug'), 'test_id': t.get('id'), 'tier': tier}

        for r in qc.run_passage_checks(passage, t.get('title'), profile, mode_override='flag'):
            rows.append(dict(base, question_id='', type_code='', scope=r.scope,
                             code=r.code, field=r.field or '', message=r.message))
        for i, q in enumerate(qs):
            for r in qc.run_question_checks(q, passage, profile, tier, index=i, mode_override='flag'):
                rows.append(dict(base, question_id=q.get('question_id') or '', type_code=q.get('type_code') or '',
                                 scope=r.scope, code=r.code, field=r.field or '', message=r.message))
        for r in qc.run_test_checks(qs, passage, profile, tier, mode_override='flag'):
            q = qs[r.question_index] if r.question_index is not None and r.question_index < len(qs) else {}
            rows.append(dict(base, question_id=q.get('question_id') or '', type_code=q.get('type_code') or '',
                             scope=r.scope, code=r.code, field=r.field or '', message=r.message))
    return rows


def summarise(tests: List[dict], rows: List[dict]) -> str:
    n_tests = Counter(t.get('language_code') for t in tests)
    n_qs = Counter()
    null_tier = 0
    for t in tests:
        n_qs[t.get('language_code')] += len(t.get('questions', []))
        null_tier += t.get('target_age_tier') is None
    langs = sorted(l for l in n_tests if l)
    codes = sorted({r['code'] for r in rows})
    by = Counter((r['language'], r['code']) for r in rows)
    tests_with = defaultdict(set)
    for r in rows:
        tests_with[r['language']].add(r['test_id'])

    out = [f"# Test quality audit — {date.today().isoformat()}", '',
           '| language | tests | questions | tests with ≥1 finding | findings |',
           '|---|---|---|---|---|']
    for l in langs:
        out.append(f"| {l} | {n_tests[l]} | {n_qs[l]} | {len(tests_with[l])} | "
                   f"{sum(v for (lg, _), v in by.items() if lg == l)} |")
    out += ['', '## Findings by check', '',
            '| check | ' + ' | '.join(langs) + ' | total | per 100 questions |',
            '|---|' + '---|' * (len(langs) + 2)]
    total_q = sum(n_qs.values()) or 1
    for c in codes:
        vals = [by[(l, c)] for l in langs]
        out.append(f"| `{c}` | " + ' | '.join(map(str, vals)) +
                   f" | {sum(vals)} | {100 * sum(vals) / total_q:.1f} |")
    top = Counter(r['slug'] for r in rows).most_common(10)
    out += ['', '## Tests with the most findings', '', '| test | findings |', '|---|---|']
    out += [f"| {s} | {n} |" for s, n in top]
    if null_tier:
        out += ['', f"Note: {null_tier} test(s) have no target_age_tier; treated as tier ≥ 2."]
    return '\n'.join(out) + '\n'


def write_outputs(out_dir: str, tests: List[dict], rows: List[dict]) -> None:
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'findings.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(out_dir, 'summary.md'), 'w', encoding='utf-8') as f:
        f.write(summarise(tests, rows))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--lang', choices=['zh', 'en', 'ja', 'all'], default='all')
    ap.add_argument('--test-id', action='append', default=[])
    ap.add_argument('--limit', type=int)
    ap.add_argument('--include-inactive', action='store_true')
    ap.add_argument('--input-json', help='audit a dump instead of the database')
    ap.add_argument('--dump-json', help='also write the loaded tests to this file')
    ap.add_argument('--out', default=os.path.join(
        ROOT, 'data', 'test_quality', f'audit_{date.today().isoformat()}'))
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    logging.getLogger('httpx').setLevel(logging.WARNING)

    if args.input_json:
        with open(args.input_json, encoding='utf-8') as f:
            tests = json.load(f)
        if args.lang != 'all':
            tests = [t for t in tests if t.get('language_code') == args.lang]
        if args.test_id:
            tests = [t for t in tests if t.get('id') in set(args.test_id)]
        if args.limit:
            tests = tests[:args.limit]
    else:
        from dotenv import load_dotenv
        load_dotenv()
        from services.supabase_factory import SupabaseFactory, get_supabase_admin
        if not SupabaseFactory.is_initialized():
            SupabaseFactory.initialize()
        db = get_supabase_admin()
        if db is None:
            logger.error('Service-role Supabase client unavailable')
            return 2
        tests = load_tests(db, None if args.lang == 'all' else args.lang, args.test_id,
                           args.include_inactive, args.limit)
    if args.dump_json:
        with open(args.dump_json, 'w', encoding='utf-8') as f:
            json.dump(tests, f, ensure_ascii=False, default=str)

    rows = audit(tests)
    write_outputs(args.out, tests, rows)
    logger.info('%d tests, %d findings -> %s', len(tests), len(rows), args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
