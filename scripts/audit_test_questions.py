"""Flag comprehension tests with repeated questions or questions harder than
their passage (read-only). See services/question_audit.py.

Usage:
    python scripts/audit_test_questions.py [--language-id 1] [--csv out.csv]
"""

import argparse
import csv
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.question_audit import audit_test  # noqa: E402
from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402


def _fetch_all(query_fn, page=1000):
    rows, start = [], 0
    while True:
        chunk = query_fn().range(start, start + page - 1).execute().data or []
        rows += chunk
        if len(chunk) < page:
            return rows
        start += page


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--language-id', type=int)
    ap.add_argument('--csv', help='write one row per flagged test')
    args = ap.parse_args()

    SupabaseFactory.initialize()
    db = get_supabase_admin()

    def tests_q():
        q = db.table('tests').select('id, slug, language_id, transcript').eq('is_active', True)
        return q.eq('language_id', args.language_id) if args.language_id else q

    tests = _fetch_all(tests_q)
    by_test = defaultdict(list)
    for q in _fetch_all(lambda: db.table('questions').select('test_id, question_text, choices, answer').order('created_at')):
        by_test[q['test_id']].append(q)

    results = [audit_test(t, by_test.get(t['id'], [])) for t in tests if by_test.get(t['id'])]
    flagged = [r for r in results if r['flagged']]
    per_lang = defaultdict(lambda: [0, 0, 0, 0, 0])
    for r in results:
        s = per_lang[r['language_id']]
        s[0] += 1
        s[1] += bool(r['near_duplicates'])
        s[2] += bool(r['missing_quotes'])
        s[3] += bool(r['above_passage'])
        s[4] += r['flagged']
    print('language  tests  repeats  quotes_not_in_passage  above_passage  flagged')
    for lang, (n, d, m, h, f) in sorted(per_lang.items()):
        print(f'{lang:>8}  {n:>5}  {d:>7}  {m:>21}  {h:>13}  {f:>7}')

    if args.csv:
        with open(args.csv, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['test_id', 'slug', 'language_id', 'questions', 'near_duplicates',
                        'missing_quotes', 'above_passage'])
            for r in flagged:
                w.writerow([r['test_id'], r['slug'], r['language_id'], r['questions'],
                            r['near_duplicates'], r['missing_quotes'], r['above_passage']])
        print(f'wrote {len(flagged)} flagged tests to {args.csv}')


if __name__ == '__main__':
    main()
