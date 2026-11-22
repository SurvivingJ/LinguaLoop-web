"""Read-only drift check: does a staged upload package still fit the live database?

Usage (repo root; needs SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY; makes GET requests only):
    python scratch_offline/staging/staged_check.py PACKAGE_DIR [--snapshot-dir scratch_offline/snap]

PACKAGE_DIR is an upload package (its word_assets.csv lists the staged senses). Reports, for
the staged senses: how many still exist, how many were edited after the snapshot, how many
already have word_assets or exercises (render refuses those), and how many staged words'
semantic_class / lemma changed live since the snapshot. dim_vocabulary.updated_at is not used:
the part-of-speech standardisation (2026-11-22) touched 15,039 rows without changing content.
"""
import argparse, csv, json, os, sys, urllib.request

csv.field_size_limit(10**9)
U = os.environ['SUPABASE_URL'].rstrip('/') + '/rest/v1/'
K = os.environ['SUPABASE_SERVICE_ROLE_KEY']


def get(table, select, col, ids):
    out = []
    for i in range(0, len(ids), 300):
        chunk = ids[i:i + 300]
        off = 0
        while True:
            q = f"{table}?select={select}&{col}=in.({','.join(map(str, chunk))})&limit=1000&offset={off}"
            req = urllib.request.Request(U + q, headers={'apikey': K, 'Authorization': 'Bearer ' + K})
            rows = json.load(urllib.request.urlopen(req, timeout=60))
            out += rows
            if len(rows) < 1000:
                break
            off += 1000
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('package_dir')
    ap.add_argument('--snapshot-dir', default='scratch_offline/snap')
    ap.add_argument('--since', default='2026-11-17T12:55:00',
                    help='UTC time the snapshot was taken (the 2026-11-17 packages: the default)')
    args = ap.parse_args()
    ids = sorted({int(r['sense_id']) for r in
                  csv.DictReader(open(os.path.join(args.package_dir, 'word_assets.csv'), encoding='utf-8'))})
    snap_v = {r['id']: r for r in json.load(open(os.path.join(args.snapshot_dir, 'dim_vocabulary.json')))}
    ws = get('dim_word_senses', 'id,vocab_id,updated_at', 'id', ids)
    snap_time = args.since
    vids = sorted({r['vocab_id'] for r in ws})
    vv = get('dim_vocabulary', 'id,lemma,semantic_class', 'id', vids)
    wa = get('word_assets', 'sense_id', 'sense_id', ids)
    ex = get('exercises', 'word_sense_id', 'word_sense_id', ids)
    vocab_changed = sum(1 for r in vv if r['id'] in snap_v and (
        r.get('lemma') != snap_v[r['id']].get('lemma')
        or r.get('semantic_class') != snap_v[r['id']].get('semantic_class')))
    print(json.dumps({
        'package': args.package_dir, 'staged_senses': len(ids), 'senses_found': len(ws),
        'snapshot_taken': snap_time,
        'senses_updated_since_snapshot': sum(1 for r in ws if (r.get('updated_at') or '') > snap_time),
        'vocab_lemma_or_semantic_class_changed': vocab_changed,
        'senses_with_word_assets': len({r['sense_id'] for r in wa}),
        'senses_with_exercises': len({r['word_sense_id'] for r in ex}),
    }, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
