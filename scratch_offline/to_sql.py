"""Convert captured uploader writes (writes.jsonl) into an upload-ready SQL file
and a word_assets CSV."""
import csv, json, sys

src, out_sql, out_csv = sys.argv[1:4]

def lit(v):
    if v is None: return 'NULL'
    if isinstance(v, bool): return 'true' if v else 'false'
    if isinstance(v, (int, float)): return str(v)
    if isinstance(v, (dict,)): return "'" + json.dumps(v, ensure_ascii=False).replace("'", "''") + "'::jsonb"
    if isinstance(v, list):
        if all(isinstance(x, str) for x in v) and v and not isinstance(v[0], dict):
            return "ARRAY[" + ",".join("'" + x.replace("'", "''") + "'" for x in v) + "]::text[]"
        return "'" + json.dumps(v, ensure_ascii=False).replace("'", "''") + "'::jsonb"
    return "'" + str(v).replace("'", "''") + "'"

WA = ['sense_id', 'language_id', 'asset_type', 'content', 'model_used', 'prompt_version',
      'is_valid', 'validation_errors', 'validation_warnings', 'generation_batch_id']
assets, stmts = {}, []
for line in open(src, encoding='utf-8'):
    d = json.loads(line)
    rows = d['payload'] if isinstance(d['payload'], list) else [d['payload']]
    if d['table'] == 'word_assets' and d['op'] in ('upsert', 'insert'):
        for r in rows:
            assets[(r['sense_id'], r['asset_type'])] = r  # last write wins
    elif d['op'] == 'update':
        sets = ', '.join(f"{k} = {lit(v)}" for k, v in rows[0].items())
        where = ' AND '.join(f"{c} = {lit(v)}" for c, v in d['where'])
        stmts.append(f"UPDATE {d['table']} SET {sets} WHERE {where};")
    else:
        sys.exit(f"unhandled write: {d['op']} {d['table']}")

with open(out_sql, 'w', encoding='utf-8') as fh:
    fh.write('BEGIN;\n')
    for r in assets.values():
        vals = ', '.join(lit(r.get(c)) for c in WA)
        fh.write(f"INSERT INTO word_assets ({', '.join(WA)}) VALUES ({vals}) "
                 "ON CONFLICT (sense_id, asset_type) DO UPDATE SET "
                 + ', '.join(f"{c} = EXCLUDED.{c}" for c in WA[3:]) + ";\n")
    for s in stmts:
        fh.write(s + '\n')
    fh.write('COMMIT;\n')

with open(out_csv, 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(WA)
    for r in assets.values():
        w.writerow([json.dumps(r[c], ensure_ascii=False) if isinstance(r.get(c), (dict, list))
                    else ('' if r.get(c) is None else r[c]) for c in WA])
print(f'{len(assets)} assets, {len(stmts)} updates')
