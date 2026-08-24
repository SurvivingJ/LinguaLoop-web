"""Apply prose_generation ja v4: stop telling T1/T2 to avoid kanji.

Context: TASK-733's v2 CEFR tier split (and the v1 row before it) told the
model to write T1/T2 passages mostly in hiragana ("use only basic/N5 kanji,
everything else in hiragana"). Two independent problems came out of that:

  1. Pedagogically pointless — furigana_service.py + tests.furigana_payload
     + the frontend furigana toggle already exist specifically so beginners
     can read kanji-bearing text. The kanji-avoidance clause worked against
     infrastructure that was built to solve exactly this.
  2. Broke the word-definition popover — fugashi/UniDic (used for both the
     transcript tokenizer and furigana generation) relies on kanji to
     disambiguate word boundaries in Japanese. Kana-only passages caused it
     to mis-segment text, producing wrong sense_id matches in
     vocab_token_map (observed live: "とが", a meaningless substring of
     おと+が ["sound"+subject particle], matched to sense 41307 = 研ぐ
     ["to sharpen a blade"]). Clicking words in these tests popped up wrong
     definitions.

Live measurement (2026-08-23): 8 of 15 ja difficulty=1 tests generated that
day had zero kanji, vs 0% in every batch before the TASK-733 rewrite.

Fix: only the kanji-avoidance bullet in the T1 and T2 blocks changes. Every
other line (grammar/vocab/register rules, T3-T6, generation parameters,
algorithm steps) is byte-identical to the live v3 row (data/eval/task733/
prose_generation_ja.txt) with only the "LinguaLoop" brand mention already
absent per v3's own change.

Usage::

    python scripts/apply_ja_prose_furigana_fix.py --dry-run   # show the plan
    python scripts/apply_ja_prose_furigana_fix.py             # write, then verify
    python scripts/apply_ja_prose_furigana_fix.py --verify    # verify only
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFT_PATH = os.path.join(ROOT, 'data', 'eval', 'prose_generation_ja_v4.txt')

TASK_NAME = 'prose_generation'
LANGUAGE_ID = 3  # ja
NEW_VERSION = 4
MODEL = 'qwen/qwen3.7-plus'
PROVIDER = 'openrouter'
DESCRIPTION = (
    'v4: T1/T2 no longer tell the model to avoid kanji ("N5 kanji only, '
    'rest hiragana"). Replaced with a standard-orthography instruction that '
    'defers reading difficulty to the existing furigana pipeline '
    '(furigana_service.py / tests.furigana_payload / frontend furigana '
    'toggle). Fixes both the pedagogical mismatch and fugashi mis-segmenting '
    'kana-only passages, which was corrupting vocab_token_map sense matches '
    'in the word-definition popover. No other line changed from v3.'
)


def read_draft_lf() -> str:
    with open(DRAFT_PATH, encoding='utf-8', newline='') as handle:
        return handle.read().replace('\r\n', '\n')


def detect_eol(text: str) -> str:
    return '\r\n' if '\r\n' in text else '\n'


def md5(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def get_incumbent(db) -> dict:
    rows = (db.table('prompt_templates')
              .select('id, version, is_active, template_text')
              .eq('task_name', TASK_NAME)
              .eq('language_id', LANGUAGE_ID)
              .eq('is_active', True)
              .execute().data)
    if len(rows) != 1:
        raise RuntimeError(
            f'expected exactly 1 active row for {TASK_NAME}/ja, found {len(rows)}'
        )
    return rows[0]


def apply(db, dry_run: bool) -> str:
    draft_lf = read_draft_lf()
    incumbent = get_incumbent(db)
    eol = detect_eol(incumbent['template_text'])
    body = draft_lf.replace('\n', eol) if eol == '\r\n' else draft_lf

    print(f'  incumbent: id={incumbent["id"]} v{incumbent["version"]} '
          f'active={incumbent["is_active"]}')
    print(f'  new: {TASK_NAME} [ja] -> v{NEW_VERSION}  eol={"CRLF" if eol == chr(13)+chr(10) else "LF"}  '
          f'{len(body)} chars  md5 {md5(body)}')

    if dry_run:
        return body

    (db.table('prompt_templates')
       .update({'is_active': False})
       .eq('id', incumbent['id'])
       .execute())

    (db.table('prompt_templates')
       .upsert({
           'task_name': TASK_NAME,
           'language_id': LANGUAGE_ID,
           'version': NEW_VERSION,
           'is_active': True,
           'model': MODEL,
           'provider': PROVIDER,
           'template_text': body,
           'description': DESCRIPTION,
       }, on_conflict='task_name,language_id,version')
       .execute())

    return body


def verify(db) -> int:
    problems = 0
    expected = md5(read_draft_lf())

    rows = (db.table('prompt_templates')
              .select('id, version, is_active, template_text')
              .eq('task_name', TASK_NAME)
              .eq('language_id', LANGUAGE_ID)
              .execute().data)

    target = next((r for r in rows if r['version'] == NEW_VERSION), None)
    print(f'\n{"task_name":<20} {"v":<3} {"active":<7} {"md5 match":<10} rows')
    print('-' * 55)

    if target is None:
        print(f'{TASK_NAME:<20} -   MISSING v{NEW_VERSION}')
        return 1

    matches = md5(target['template_text'].replace('\r\n', '\n')) == expected
    active_ok = bool(target['is_active']) is True
    active_count = sum(1 for r in rows if r['is_active'])

    flag = ''
    if not matches:
        flag += ' MD5-MISMATCH'
        problems += 1
    if not active_ok:
        flag += ' NOT-ACTIVE'
        problems += 1
    if active_count != 1:
        flag += f' ACTIVE-ROWS={active_count}'
        problems += 1

    print(f'{TASK_NAME:<20} {target["version"]:<3} {str(bool(target["is_active"])):<7} '
          f'{str(matches):<10} {len(rows)} version(s){flag}')

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true', help='show the plan, write nothing')
    parser.add_argument('--verify', action='store_true', help='verify only, write nothing')
    args = parser.parse_args()

    SupabaseFactory.initialize()
    db = get_supabase_admin()

    if not args.verify:
        print('plan:' if args.dry_run else 'applying:')
        apply(db, args.dry_run)
        if args.dry_run:
            return 0

    problems = verify(db)
    print(f'\n{"OK — all rows verified" if not problems else f"{problems} PROBLEM(S)"}')
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
