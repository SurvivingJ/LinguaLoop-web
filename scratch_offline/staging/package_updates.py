"""Parse the dictionary UPDATEs of an upload package's SQL and report overwrites of live values.

Upload packages from scratch_offline/package_upload.py end each sense with
    UPDATE dim_vocabulary SET k = v, ... WHERE id = N;      (the sense's word)
    UPDATE dim_word_senses SET k = v, ... WHERE id = M;     (the sense)
This reads those lines from apply_all.sql (plain or .gz), keeps the senses in --senses (or all), and
compares every value with the read-only snapshot in scratch_offline/snap/ (rest_snapshot.py).

Usage (repo root):
    python scratch_offline/staging/package_updates.py APPLY_ALL_SQL[.gz] [--senses ids.txt] [--out report.csv]

dim_vocabulary.part_of_speech differences are not counted: since 2026-11-22 the normalise trigger
stores every tag as the standard label (originals in part_of_speech_raw).
"""
import argparse
import collections
import csv
import gzip
import json
import re

_TOKEN = re.compile(r"\s*(\w+)\s*=\s*('(?:[^']|'')*'(?:::jsonb)?|NULL|-?\d+(?:\.\d+)?|true|false)\s*(,|$)")
_LINE = re.compile(r"UPDATE (dim_word_senses|dim_vocabulary) SET (.*) WHERE id = (\d+);$")


def parse_set(text):
    """`a = 'x', b = '[..]'::jsonb, c = NULL` -> {'a': 'x', 'b': [...], 'c': None}."""
    out, pos = {}, 0
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m:
            raise ValueError(f'cannot parse SET list at: {text[pos:pos + 80]!r}')
        key, raw = m.group(1), m.group(2)
        pos = m.end()
        if raw == 'NULL':
            val = None
        elif raw.startswith("'"):
            is_json = raw.endswith('::jsonb')
            s = raw[1:(-8 if is_json else -1)].replace("''", "'")
            val = json.loads(s) if is_json else s
        elif raw in ('true', 'false'):
            val = raw == 'true'
        else:
            val = float(raw) if '.' in raw else int(raw)
        out[key] = val
    return out


def iter_sense_updates(path):
    """Yield (sense_id, [(vocab_id, vocab_values)], sense_values) in file order."""
    opener = gzip.open if path.endswith('.gz') else open
    pending = []
    with opener(path, 'rt', encoding='utf-8') as fh:
        for line in fh:
            m = _LINE.match(line.strip())
            if not m:
                continue
            table, set_text, row_id = m.group(1), m.group(2), int(m.group(3))
            values = parse_set(set_text)
            if table == 'dim_vocabulary':
                pending.append((row_id, values))
                continue
            yield row_id, pending, values
            pending = []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sql')
    ap.add_argument('--senses', help='file of comma-separated sense ids to keep')
    ap.add_argument('--snapshot-dir', default='scratch_offline/snap')
    ap.add_argument('--out')
    args = ap.parse_args()
    keep = None
    if args.senses:
        keep = {int(x) for x in open(args.senses).read().replace('\n', ',').split(',') if x.strip()}
    snap_v = {r['id']: r for r in json.load(open(f'{args.snapshot_dir}/dim_vocabulary.json'))}
    snap_s = {r['id']: r for r in json.load(open(f'{args.snapshot_dir}/dim_word_senses.json'))}
    set_count, diff_count, rows, senses = collections.Counter(), collections.Counter(), [], 0
    for sid, vocab_updates, sense_values in iter_sense_updates(args.sql):
        if keep is not None and sid not in keep:
            continue
        senses += 1
        for table, rid, values in ([('dim_vocabulary', v, vals) for v, vals in vocab_updates]
                                   + [('dim_word_senses', sid, sense_values)]):
            cur = (snap_v if table == 'dim_vocabulary' else snap_s).get(rid) or {}
            for k, v in values.items():
                set_count[(table, k)] += 1
                if table == 'dim_vocabulary' and k == 'part_of_speech':
                    continue
                if k in cur and cur[k] is not None and cur[k] != v:
                    diff_count[(table, k)] += 1
                    rows.append([table, rid, k, sid, cur[k], v])
    print(f'senses: {senses}')
    for key in sorted(set_count):
        print(key, 'set', set_count[key], 'replaces a different non-null value', diff_count[key])
    if args.out:
        with open(args.out, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['table', 'row_id', 'column', 'sense_id', 'live_value', 'staged_value'])
            w.writerows(rows)


if __name__ == '__main__':
    main()
