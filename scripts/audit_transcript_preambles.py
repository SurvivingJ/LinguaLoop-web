#!/usr/bin/env python3
"""
Audit and strip generation preambles from tests.transcript (TASK-900).

Why this exists
    Some transcripts begin with text addressed to the prompt author rather
    than the learner ("この文章は、T3レベル（B1-B2）の学習者向けに…---",
    "(Note: The prompt designates Level T2 …)", "Level Definitions & Target
    Audience Analysis: …"). It has leaked into dt_passage gold spans and would
    leak into test_sentences (TASK-902). The matcher lives in
    services/transcript_preamble.py and is unit-tested in
    tests/test_transcript_preamble.py.

What --dry-run does (read-only)
    Lists every affected ACTIVE test (id, language, kind, first 60 chars),
    the count per language, the dt_passage rows whose l2_text starts with a
    preamble, and how many tests.transcript_hash values would be written.

What --apply does (LIVE-DB, user approval required)
    1. For each affected test: backs the old transcript + token map up to
       data/transcript_cleanup/<date>/<test_id>.json, strips the preamble,
       re-derives vocab_token_map with the generator's own builder
       (services.test_generation.orchestrator.build_token_map_for_test) when
       the test had a map, and writes transcript + vocab_token_map +
       transcript_hash in one UPDATE.
    2. Sets tests.transcript_hash = sha256(transcript) for EVERY active test
       whose stored hash is missing or stale.
    3. Sets dt_passage.status = 'retired' for rows whose l2_text starts with a
       preamble (TASK-902 recreates clean spans from test_sentences).
    A second --apply run reports 0 affected tests.

Requires migrations/tests_transcript_hash.sql applied before --apply.
Re-deriving a token map needs the language's tokenizer (spaCy for en, jieba
for zh, fugashi for ja) installed locally; a test whose map cannot be rebuilt
is skipped and reported, nothing partial is written for it.

Usage:
    python scripts/audit_transcript_preambles.py --dry-run
    python scripts/audit_transcript_preambles.py --dry-run --language ja
    python scripts/audit_transcript_preambles.py --apply
"""

import os
import sys
import json
import argparse
import logging
from datetime import date, datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin
from services.transcript_preamble import detect_preamble, transcript_hash

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('audit_transcript_preambles')

PAGE = 1000
BACKUP_ROOT = os.path.join(ROOT, 'data', 'transcript_cleanup')


# ------------------------------------------------------------------ fetching

def fetch_languages(db) -> dict[int, str]:
    rows = db.table('dim_languages').select('id, language_code').execute().data or []
    return {int(r['id']): r['language_code'] for r in rows}


def fetch_active_tests(db, language_id: int | None, columns: str) -> list[dict]:
    out: list[dict] = []
    offset = 0
    while True:
        q = db.table('tests').select(columns).eq('is_active', True).order('created_at')
        if language_id is not None:
            q = q.eq('language_id', language_id)
        page = q.range(offset, offset + PAGE - 1).execute().data or []
        out.extend(page)
        if len(page) < PAGE:
            return out
        offset += PAGE


def fetch_dt_passages(db) -> list[dict]:
    out: list[dict] = []
    offset = 0
    while True:
        page = db.table('dt_passage').select('id, source_ref_id, l2_language_id, l2_text, status') \
            .neq('status', 'retired').order('id').range(offset, offset + PAGE - 1).execute().data or []
        out.extend(page)
        if len(page) < PAGE:
            return out
        offset += PAGE


# ------------------------------------------------------------------ pure logic

def classify_tests(tests: list[dict]) -> list[dict]:
    """[{test, match}] for every test whose transcript starts with a preamble."""
    affected = []
    for t in tests:
        m = detect_preamble(t.get('transcript'))
        if m is not None:
            affected.append({'test': t, 'match': m})
    return affected


def stale_hash_tests(tests: list[dict], replaced: dict[str, str]) -> list[tuple[str, str]]:
    """(test_id, hash) for every active test whose stored hash is missing or wrong.

    `replaced` maps test_id -> new transcript for tests being cleaned in the
    same run, so their hash is computed from the cleaned text.
    """
    out = []
    for t in tests:
        text = replaced.get(t['id'], t.get('transcript'))
        if not text:
            continue
        h = transcript_hash(text)
        if t.get('transcript_hash') != h:
            out.append((t['id'], h))
    return out


def one_line(text: str, n: int = 60) -> str:
    return (text or '')[:n].replace('\n', '\\n')


# ------------------------------------------------------------------ reporting

def report(affected: list[dict], tests: list[dict], passages: list[dict],
           langs: dict[int, str], hashes_due: int) -> None:
    print()
    print(f"Active tests scanned: {len(tests)}")
    print(f"Affected tests: {len(affected)}")
    if affected:
        print()
        print(f"{'test_id':<38} {'lang':<5} {'kind':<10} first 60 chars")
        for a in affected:
            t = a['test']
            print(f"{t['id']:<38} {langs.get(t['language_id'], t['language_id']):<5} "
                  f"{a['match'].kind:<10} {one_line(t['transcript'])}")
    print()
    print("Affected per language:")
    for lid in sorted(langs):
        n = sum(1 for a in affected if a['test']['language_id'] == lid)
        print(f"  {langs[lid]:<4} (id {lid}): {n}")
    print()
    print(f"dt_passage rows (not retired) whose l2_text starts with a preamble: {len(passages)}")
    for p in passages:
        print(f"  dt_passage {p['id']} (test {p['source_ref_id']}, status {p['status']}): "
              f"{one_line(p['l2_text'])}")
    print()
    print(f"tests.transcript_hash values to write (missing or stale): {hashes_due}")


# ------------------------------------------------------------------ apply

def backup(test: dict, match, new_text: str, new_map, run_day: str) -> str:
    folder = os.path.join(BACKUP_ROOT, run_day)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{test['id']}.json")
    payload = {
        'test_id': test['id'],
        'slug': test.get('slug'),
        'language_id': test['language_id'],
        'backed_up_at': datetime.now(timezone.utc).isoformat(),
        'preamble_kind': match.kind,
        'preamble': match.preamble,
        'old_transcript': test['transcript'],
        'old_vocab_token_map': test.get('vocab_token_map'),
        'old_transcript_hash': test.get('transcript_hash'),
        'new_transcript': new_text,
        'new_vocab_token_map': new_map,
        'new_transcript_hash': transcript_hash(new_text),
    }
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    return path


def rebuild_token_map(db, test: dict, new_text: str, language_code: str):
    """The generator's own builder, for this test only. None when the test had no map."""
    if not test.get('vocab_token_map'):
        return None
    from services.test_generation.orchestrator import build_token_map_for_test
    new_map = build_token_map_for_test(
        db, new_text, language_code, int(test['language_id']),
        sense_ids=[int(s) for s in (test.get('vocab_sense_ids') or [])],
    )
    joined = ''.join(tok[0] for tok in new_map)
    if joined != new_text:
        # The ja processor drops newlines; the old map had the same defect.
        old_joined = ''.join(tok[0] for tok in test['vocab_token_map'])
        if old_joined == test['transcript']:
            raise RuntimeError(
                f"rebuilt token map does not reproduce the transcript for {test['id']} "
                f"(old map did); refusing to write"
            )
        logger.warning("%s: rebuilt token map does not reproduce the transcript exactly "
                       "(nor did the old one); writing anyway", test['id'])
    return new_map


def apply_changes(db, affected: list[dict], tests: list[dict], passages: list[dict],
                  langs: dict[int, str]) -> int:
    run_day = date.today().isoformat()
    replaced: dict[str, str] = {}
    failed = 0

    for a in affected:
        t, m = a['test'], a['match']
        code = langs[int(t['language_id'])]
        try:
            new_map = rebuild_token_map(db, t, m.cleaned, code)
        except Exception as e:  # tokenizer missing, judge failure, mismatch
            failed += 1
            logger.error("SKIP %s (%s): token map rebuild failed: %s", t['id'], code, e)
            continue
        path = backup(t, m, m.cleaned, new_map, run_day)
        update = {
            'transcript': m.cleaned,
            'transcript_hash': transcript_hash(m.cleaned),
        }
        if t.get('vocab_token_map'):
            update['vocab_token_map'] = new_map
        db.table('tests').update(update).eq('id', t['id']).execute()
        replaced[t['id']] = m.cleaned
        logger.info("CLEANED %s (%s, %s): -%d chars, backup %s",
                    t['id'], code, m.kind, len(t['transcript']) - len(m.cleaned),
                    os.path.relpath(path, ROOT))

    due = [(tid, h) for tid, h in stale_hash_tests(tests, replaced) if tid not in replaced]
    for tid, h in due:
        db.table('tests').update({'transcript_hash': h}).eq('id', tid).execute()
    logger.info("transcript_hash written for %d further active test(s)", len(due))

    for p in passages:
        db.table('dt_passage').update({'status': 'retired'}).eq('id', p['id']).execute()
        logger.info("RETIRED dt_passage %d (test %s)", p['id'], p['source_ref_id'])

    logger.info("Done: %d cleaned, %d skipped, %d hashes backfilled, %d passages retired",
                len(replaced), failed, len(due), len(passages))
    return 1 if failed else 0


# ------------------------------------------------------------------ main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true', help='report only (read-only)')
    mode.add_argument('--apply', action='store_true', help='strip preambles and write (LIVE-DB)')
    ap.add_argument('--language', choices=['zh', 'en', 'ja'], help='restrict to one L2')
    args = ap.parse_args()

    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()
    if db is None:
        logger.error("Service-role Supabase client unavailable (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY)")
        return 2

    langs = fetch_languages(db)
    language_id = next((lid for lid, c in langs.items() if c == args.language), None) \
        if args.language else None

    columns = 'id, slug, language_id, transcript, vocab_token_map, vocab_sense_ids'
    has_hash_column = True
    try:
        tests = fetch_active_tests(db, language_id, columns + ', transcript_hash')
    except Exception as e:
        if 'transcript_hash' in str(e):
            has_hash_column = False
            logger.warning("tests.transcript_hash does not exist yet — apply "
                           "migrations/tests_transcript_hash.sql before --apply")
            tests = fetch_active_tests(db, language_id, columns)
        else:
            raise

    affected = classify_tests(tests)
    passages = [p for p in fetch_dt_passages(db)
                if detect_preamble(p.get('l2_text')) is not None
                and (language_id is None or int(p['l2_language_id']) == language_id)]
    hashes_due = len(stale_hash_tests(tests, {a['test']['id']: a['match'].cleaned for a in affected}))

    report(affected, tests, passages, langs, hashes_due)

    if args.dry_run:
        print("\nDry run — nothing written.")
        return 0

    if not has_hash_column:
        logger.error("Refusing --apply: tests.transcript_hash is missing")
        return 2
    return apply_changes(db, affected, tests, passages, langs)


if __name__ == '__main__':
    sys.exit(main())
