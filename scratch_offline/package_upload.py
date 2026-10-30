"""Build the DB upload package from captured uploader writes.

    python3 scratch_offline/package_upload.py WRITES.jsonl OUT_DIR [--exclude-csv PREVIOUS/word_assets.csv]

Writes OUT_DIR/apply_all.sql (one transaction), OUT_DIR/chunks/part_NN.sql
(~0.9 MB each, own BEGIN/COMMIT, UPDATEs in the last part), word_assets.csv,
verify.sql and README.md. With --exclude-csv, senses already present in an
earlier package are left out (a delta package).
"""
import argparse
import csv
import json
import os

csv.field_size_limit(10 ** 9)
WA = ['sense_id', 'language_id', 'asset_type', 'content', 'model_used', 'prompt_version',
      'is_valid', 'validation_errors', 'validation_warnings', 'generation_batch_id']
CHUNK = 900_000


def lit(v):
    if v is None:
        return 'NULL'
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, dict):
        return "'" + json.dumps(v, ensure_ascii=False).replace("'", "''") + "'::jsonb"
    if isinstance(v, list):
        if v and all(isinstance(x, str) for x in v):
            return "ARRAY[" + ",".join("'" + x.replace("'", "''") + "'" for x in v) + "]::text[]"
        return "'" + json.dumps(v, ensure_ascii=False).replace("'", "''") + "'::jsonb"
    return "'" + str(v).replace("'", "''") + "'"


def load_writes(path, exclude):
    assets, updates = {}, []
    pending_vocab = []  # the uploader writes dim_vocabulary just before its sense's dim_word_senses
    for line in open(path, encoding='utf-8'):
        d = json.loads(line)
        rows = d['payload'] if isinstance(d['payload'], list) else [d['payload']]
        if d['table'] == 'word_assets' and d['op'] in ('upsert', 'insert'):
            for r in rows:
                if int(r['sense_id']) not in exclude:
                    assets[(int(r['sense_id']), r['asset_type'])] = r  # last write wins
        elif d['op'] == 'update':
            sets = ', '.join(f"{k} = {lit(v)}" for k, v in rows[0].items())
            cond = ' AND '.join(f"{c} = {lit(v)}" for c, v in d['where'])
            stmt = f"UPDATE {d['table']} SET {sets} WHERE {cond};"
            if d['table'] == 'dim_vocabulary':
                pending_vocab.append(stmt)
                continue
            sid = int(dict(d['where']).get('id'))
            if sid not in exclude:
                updates += [('dim_vocabulary', sid, v) for v in pending_vocab]
                updates.append((d['table'], sid, stmt))
            pending_vocab = []
        else:
            raise SystemExit(f"unhandled write: {d['op']} {d['table']}")
    return assets, updates


def insert_stmt(r):
    vals = ', '.join(lit(r.get(c)) for c in WA)
    return (f"INSERT INTO word_assets ({', '.join(WA)}) VALUES ({vals}) "
            "ON CONFLICT (sense_id, asset_type) DO UPDATE SET "
            + ', '.join(f"{c} = EXCLUDED.{c}" for c in WA[3:]) + ";")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('writes')
    ap.add_argument('out')
    ap.add_argument('--exclude-csv', default='')
    ap.add_argument('--title', default='JA word assets — upload package')
    args = ap.parse_args()
    exclude = set()
    if args.exclude_csv:
        exclude = {int(r['sense_id']) for r in csv.DictReader(open(args.exclude_csv, encoding='utf-8'))}
    assets, updates = load_writes(args.writes, exclude)
    senses = sorted({sid for sid, _ in assets})
    stmts = [insert_stmt(r) for _, r in sorted(assets.items())] + [u[2] for u in updates]
    os.makedirs(os.path.join(args.out, 'chunks'), exist_ok=True)
    with open(os.path.join(args.out, 'apply_all.sql'), 'w', encoding='utf-8') as fh:
        fh.write('BEGIN;\n' + '\n'.join(stmts) + '\nCOMMIT;\n')
    parts, cur, size = [], [], 0
    for s in stmts:
        if cur and size + len(s) > CHUNK:
            parts.append(cur); cur, size = [], 0
        cur.append(s); size += len(s) + 1
    if cur:
        parts.append(cur)
    for i, p in enumerate(parts, 1):
        with open(os.path.join(args.out, 'chunks', f'part_{i:02d}.sql'), 'w', encoding='utf-8') as fh:
            fh.write('BEGIN;\n' + '\n'.join(p) + '\nCOMMIT;\n')
    with open(os.path.join(args.out, 'word_assets.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh); w.writerow(WA)
        for _, r in sorted(assets.items()):
            w.writerow([json.dumps(r[c], ensure_ascii=False) if isinstance(r.get(c), (dict, list))
                        else ('' if r.get(c) is None else r[c]) for c in WA])
    types = sorted({t for _, t in assets})
    per_type = {t: sum(1 for _, tt in assets if tt == t) for t in types}
    with open(os.path.join(args.out, 'verify.sql'), 'w', encoding='utf-8') as fh:
        fh.write(f"-- Expected: assets = {len(assets)}, senses = {len(senses)}; per type: {per_type}\n")
        fh.write("WITH ids AS (SELECT unnest(ARRAY[" + ",".join(map(str, senses)) + "]) AS id)\n"
                 "SELECT asset_type, count(*) AS assets, count(DISTINCT sense_id) AS senses\n"
                 "FROM word_assets\nWHERE language_id = 3 AND sense_id IN (SELECT id FROM ids)\n"
                 "GROUP BY ROLLUP (asset_type)\nORDER BY asset_type NULLS LAST;\n")
    n_upd = {t: sum(1 for u in updates if u[0] == t) for t in sorted({u[0] for u in updates})}
    with open(os.path.join(args.out, 'README.md'), 'w', encoding='utf-8') as fh:
        fh.write(f"""# {args.title}

Reviewed fat-seed output for **{len(senses)} Japanese senses** (all passed
`check --source reviewed`; rejected and skipped senses are excluded).
{'Delta package: the ' + str(len(exclude)) + ' senses of the earlier package are excluded.' if exclude else 'Complete package (every reviewed run).'}

| | |
|---|---|
| `word_assets` rows | {len(assets):,} ({len(types)} asset types) |
| UPDATE statements | {sum(n_upd.values()):,} {n_upd} |
| language_id | 3 (ja) |
| source models | Sonnet core / Haiku audits, variants and review (runs r0069+), Sonnet + Opus (earlier runs) |

## Files

- `apply_all.sql` — everything in one transaction ({os.path.getsize(os.path.join(args.out, 'apply_all.sql')) / 1e6:.1f} MB). Use with `psql`.
- `chunks/part_01.sql … part_{len(parts):02d}.sql` — the same statements in ~0.9 MB files, each its
  own `BEGIN … COMMIT`, UPDATEs at the end. For the Supabase SQL editor, run them in order.
- `word_assets.csv` — the asset rows only (no UPDATEs), for Table Editor import.
- `verify.sql` — row counts to run afterwards.

Every INSERT is `ON CONFLICT (sense_id, asset_type) DO UPDATE`, so re-running a
chunk is harmless. Apply with:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f {args.out}/apply_all.sql
```
""")
    print(f'{len(assets)} assets for {len(senses)} senses, {len(updates)} updates, {len(parts)} chunks -> {args.out}')


if __name__ == '__main__':
    main()
