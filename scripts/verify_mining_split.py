#!/usr/bin/env python3
"""Prove the TASK-795 split of _fetch_corpus_sentences changed nothing.

Three results per sense, compared as canonical JSON bytes:

  old   _fetch_corpus_sentences from a git ref (default HEAD), i.e. before the split
  new   _fetch_corpus_sentences as it is now (RPC + mine_sentences)
  bulk  mine_sentences over rows from the CSV export's bulk tests query
        (fetch_sense_test_rows), which is what the CSV export does

old == new proves the refactor preserves behaviour. new == bulk proves that
bulk-exporting the tests once gives the same rows, in the same order, as the
per-sense RPC. Order matters because mining stops at VOCAB_SENTENCES_PER_WORD.

Usage:
    python scripts/verify_mining_split.py --language ja --sense-ids 35053,35069,...
    python scripts/verify_mining_split.py --language ja --sample 12
"""

import os
import sys
import json
import argparse
import importlib.util
import subprocess
import tempfile
import logging

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin

if not SupabaseFactory.is_initialized():
    SupabaseFactory.initialize()

from services.vocabulary_ladder import asset_pipeline as new_module

logging.basicConfig(level=logging.WARNING)
LANG_ID = {'zh': 1, 'en': 2, 'ja': 3}


def load_old_module(ref: str):
    """Import asset_pipeline.py as it was at ``ref``, under a private name."""
    src = subprocess.check_output(
        ['git', 'show', f'{ref}:services/vocabulary_ladder/asset_pipeline.py'],
        cwd=ROOT,
    )
    fd, path = tempfile.mkstemp(suffix='_asset_pipeline_old.py')
    with os.fdopen(fd, 'wb') as fh:
        fh.write(src)
    spec = importlib.util.spec_from_file_location('asset_pipeline_old', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canon(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode('utf-8')


def sample_senses(db, language_id: int, n: int) -> list[int]:
    """Half the most test-referenced senses (mining hits the 10-sentence cap,
    so row order is exercised) and half the rest."""
    import run_content_build as rcb
    test_ids = [r['id'] for r in (
        db.table('tests').select('id').eq('language_id', language_id)
          .eq('is_active', True).limit(2000).execute().data or [])]
    ranked = [s for s, _ in rcb.sense_ids_for_tests(db, test_ids).most_common()]
    top = ranked[:n // 2]
    tail = ranked[len(ranked) // 2: len(ranked) // 2 + (n - len(top))]
    return top + tail


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--language', default='ja', choices=list(LANG_ID))
    parser.add_argument('--sense-ids')
    parser.add_argument('--sample', type=int, default=12)
    parser.add_argument('--ref', default='HEAD')
    args = parser.parse_args()

    db = get_supabase_admin()
    language_id = LANG_ID[args.language]
    senses = ([int(s) for s in args.sense_ids.split(',') if s.strip()]
              if args.sense_ids else sample_senses(db, language_id, args.sample))

    from export_exercise_worklist import fetch_sense_test_rows

    old = load_old_module(args.ref).VocabAssetPipeline(db)
    new = new_module.VocabAssetPipeline(db)
    bulk_rows = fetch_sense_test_rows(db, senses, language_id)

    failures = 0
    for sid in senses:
        a = old._fetch_corpus_sentences(sid, language_id)
        b = new._fetch_corpus_sentences(sid, language_id)
        lemma = new._lemma_for_sense(sid)
        c = new_module.mine_sentences(bulk_rows.get(sid, []), lemma, sid, language_id) if lemma else []
        same_ab = canon(a) == canon(b)
        same_bc = canon(b) == canon(c)
        failures += (not same_ab) + (not same_bc)
        print(f"sense {sid:>6} {lemma!s:<10} mined={len(b):>2}  "
              f"old==new:{'OK ' if same_ab else 'DIFF'}  new==bulk:{'OK ' if same_bc else 'DIFF'}")

    print(f"\n{len(senses)} senses, {failures} mismatch(es)")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
