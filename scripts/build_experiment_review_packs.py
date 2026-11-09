"""Arm-blind review packs for a test-generation experiment (TASK-923).

Reads data/test_quality/experiments/<TAG>/tests.jsonl for each TAG (one tag
per arm), loads the generated tests (inactive ones included), shuffles them
together, strips every arm marker, and writes:

  <out>/review_NN.md   ~15 tests each, with the review rubric
  <out>/key.json       test_id -> run_tag (do not give this to reviewers)

Reviewers (fresh-context Claude subagents) write <out>/review_NN.json:
  [{"test_id", "question_id", "verdict": "ok|minor|major",
    "group": "<rubric group or empty>", "level_fit": "ok|too_hard|too_easy",
    "note": "..."}]

    python scripts/build_experiment_review_packs.py e1-flag e1-calibrated e1-reject \
        --out data/test_quality/experiments/e1_review
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path[:0] = [ROOT]

RUBRIC = """# Review pack {n}

You are reviewing reading-comprehension tests for language learners. For EVERY
question decide, as a careful native-level teacher of the test's language:

- **verdict** — `major`: wrong answer key, two defensible answers, not
  answerable from the passage, or answer not among the choices. `minor`:
  guessable without reading (answer copied from the passage, absurd or
  all-or-nothing distractors, answer much longer), duplicate of another
  question in the test, partly defensible distractor, vocabulary meaning not
  the in-context one, language error in the question or choices, wrong writing
  system. `ok` otherwise.
- **group** — for minor/major, one of: duplicate, guessable, unsupported_key,
  defensible_distractor, vocab_sense, language_error, level_mismatch,
  wrong_key, two_answers, other.
- **level_fit** — is the *language of the question and choices* right for the
  test's level (tier 1 = young beginner ... tier 6 = advanced)? `ok`,
  `too_hard` or `too_easy`.

Judge only what is on the page. Write a JSON list, one object per question:
`{{"test_id", "question_id", "verdict", "group", "level_fit", "note"}}`.

"""


def load_records(tags):
    recs = []
    for tag in tags:
        path = os.path.join(ROOT, 'data', 'test_quality', 'experiments', tag, 'tests.jsonl')
        with open(path, encoding='utf-8') as f:
            recs += [json.loads(line) for line in f if line.strip()]
    return recs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('tags', nargs='+')
    ap.add_argument('--out', required=True)
    ap.add_argument('--per-pack', type=int, default=15)
    ap.add_argument('--seed', type=int, default=923)
    ap.add_argument('--input-json', help='tests dump instead of the database (for tests)')
    args = ap.parse_args(argv)

    recs = [r for r in load_records(args.tags) if r.get('outcome') == 'pass' and r.get('test_id')]
    ids = [r['test_id'] for r in recs]
    if args.input_json:
        with open(args.input_json, encoding='utf-8') as f:
            tests = [t for t in json.load(f) if t['id'] in set(ids)]
    else:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(ROOT, '.env'))
        from services.supabase_factory import SupabaseFactory, get_supabase_admin
        from scripts.audit_test_quality import load_tests
        if not SupabaseFactory.is_initialized():
            SupabaseFactory.initialize()
        tests = load_tests(get_supabase_admin(), None, ids, True, None)

    random.Random(args.seed).shuffle(tests)
    os.makedirs(args.out, exist_ok=True)
    key = {r['test_id']: r['run_tag'] for r in recs}
    with open(os.path.join(args.out, 'key.json'), 'w', encoding='utf-8') as f:
        json.dump(key, f, indent=1)
    for n in range(0, len(tests), args.per_pack):
        chunk = tests[n:n + args.per_pack]
        lines = [RUBRIC.format(n=n // args.per_pack + 1)]
        for t in chunk:
            lines += [f"## Test {t['id']}", f"language: {t['language_code']} · tier: {t.get('target_age_tier')}",
                      f"title: {t.get('title')}", '', '```', t.get('transcript') or '', '```', '']
            for q in t['questions']:
                lines.append(f"- **{q['question_id']}** ({q.get('type_code')}) {q.get('question_text')}")
                for c in q.get('choices') or []:
                    mark = ' ✓' if c == q.get('answer') else ''
                    lines.append(f"    - {c}{mark}")
            lines.append('')
        with open(os.path.join(args.out, f"review_{n // args.per_pack + 1:02d}.md"), 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    print(f"{len(tests)} tests -> {args.out}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
