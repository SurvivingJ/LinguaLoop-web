#!/usr/bin/env python3
"""Stage-0 exercise export (senses.csv + prompts.json) for words that are NOT in the live dictionary yet.

    python3 scratch_offline/export_offline_worklist.py data/sense_seeding/ja_jlpt/n1_final.json \
        data/sense_seeding/ja_jlpt/n1_worklist.json data/exercise_seeding/ja/fatseed_jlpt_n1 \
        --ids-out data/sense_seeding/ja_jlpt/n1_provisional_ids.json

Same rows scripts/export_exercise_worklist.py --format csv writes, built through its own functions, but the
per-word lookups (dim_word_senses / dim_vocabulary) come from the definitions file instead of the database.
Each word gets a PROVISIONAL sense id (900000000 + 2*i), written to --ids-out as {lemma: provisional_id};
before upload the words must be created live and every provisional id remapped to its real sense id.
The database is only read (prompt templates, language profile); nothing is written. New words have no test
references, so corpus_sentences is [] exactly as for the N2/N3 exports.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, '/home/user/LinguaLoop-web/scripts')
sys.path.insert(0, '/home/user/LinguaLoop-web')
os.chdir('/home/user/LinguaLoop-web')
from _common import admin_db, bootstrap  # noqa: E402

bootstrap()
import export_exercise_worklist as ex  # noqa: E402
from collections import Counter  # noqa: E402

BASE = 900_000_000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('final')
    ap.add_argument('worklist')
    ap.add_argument('out_dir')
    ap.add_argument('--ids-out', required=True)
    ap.add_argument('--language', default='ja')
    args = ap.parse_args()
    language_id = {'zh': 1, 'en': 2, 'ja': 3}[args.language]

    final = json.load(open(args.final))
    zipf = {w['lemma']: w.get('zipf') for w in json.load(open(args.worklist))}
    ids, word, vocab = {}, {}, {}
    for i, f in enumerate(final):
        sid = BASE + 2 * i
        ids[f['lemma']] = sid
        v = {'lemma': f['lemma'], 'reading': f['reading'], 'part_of_speech': f['pos'],
             'frequency_rank': zipf.get(f['lemma']), 'level_tag': None, 'semantic_class': None}
        vocab[sid] = v
        word[sid] = {'sense_id': sid, 'lemma': f['lemma'], 'pos': ex.pos_hint(v) if hasattr(ex, 'pos_hint') else f['pos'],
                     'definition': f['ja_standard'], 'pronunciation': f['reading'], 'complexity_tier': 'T3'}

    db = admin_db()
    ex.vocab_extras = lambda db, sense_ids, language_id: {s: vocab[s] for s in sense_ids if s in vocab}
    ex.fetch_sense_test_rows = lambda db, sense_ids, language_id, *a, **k: {}
    pipeline = ex.VocabAssetPipeline(db)
    p1_gen = ex.CoreAssetGenerator(db, language_id)
    p1_gen._load_word_data = lambda sense_id: word.get(sense_id)
    header = ex.core_header(db, language_id)
    selected = sorted(word)
    rows = ex.build_csv_rows(db, pipeline, p1_gen, selected, language_id, Counter(), header)
    path = ex.write_csv_run(rows, header, ex.prompts_manifest(db, language_id), args.out_dir,
                            args.language, language_id)
    json.dump(ids, open(args.ids_out, 'w'), ensure_ascii=False, indent=1)
    print(f'{len(rows)} rows -> {path}; provisional ids -> {args.ids_out}')


if __name__ == '__main__':
    main()
