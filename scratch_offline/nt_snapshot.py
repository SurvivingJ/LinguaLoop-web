"""Snapshot one language's tables into scratch_offline/snap/ for the offline DB shim.

A cloud container cannot reach Supabase, so the fat-seed scripts read the
database from JSON snapshots (scratch_offline/offline_db.py). This builds them
through the Supabase MCP `execute_sql` tool, read-only, in four steps:

    python3 scratch_offline/nt_snapshot.py sizes --lang zh
        prints one SQL query. Run it with execute_sql; it returns a small JSON
        object of estimated bytes per table.
    python3 scratch_offline/nt_snapshot.py queries --lang zh --sizes '<that JSON>'
        writes snap/_snapshot_zh.sql: numbered queries, one per page, each
        returning json_agg rows. Run them one at a time with execute_sql. Pages
        are sized (~2 MB) so that every result is too large to show inline and
        is saved to a tool-results file instead, keeping the rows out of the
        conversation.
    python3 scratch_offline/nt_snapshot.py add <saved result file> [...]
        merges each saved result into snap/<table>.json (rows replace rows
        with the same key; other languages' rows are kept).
    python3 scratch_offline/nt_snapshot.py status --lang zh
        local row counts per table, plus the SQL for the expected counts.

Columns are the ones the scripts read, as in the Japanese snapshot. Embeddings,
user ids and other unused columns are left out; snap/ is gitignored because it
holds table rows.
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nt_lang  # noqa: E402
import spill  # noqa: E402

SNAP = os.environ.get('OFFLINE_SNAP', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'snap'))

# table -> (key, columns, WHERE with {L} = language id, or None for every row)
TABLES = {
    'dim_languages': ('id', '*', None),
    'prompt_templates': ('id', '*', None),
    'calibration_anchor_blocklist': ('sense_id', 'sense_id, reason, added_at', None),
    'corpus_collocations': ('id', '*', 'language_id = {L}'),
    'dim_vocabulary': ('id', 'id, language_id, lemma, lemma_traditional, reading, phrase_type, component_lemmas, '
                       'part_of_speech, frequency_rank, level_tag, semantic_class, semantic_class_confidence, '
                       'created_at, updated_at', 'language_id = {L}'),
    'dim_word_senses': ('id', 'id, vocab_id, definition_language_id, word_language_id, definition, definition_level, '
                        'pronunciation, ipa_pronunciation, example_sentence, morphological_forms, register, '
                        'sense_rank, source, is_validated',
                        'vocab_id IN (SELECT id FROM dim_vocabulary WHERE language_id = {L}) '
                        'AND definition_language_id = {L}'),
    'tests': ('id', 'id, language_id, slug, title, difficulty, style, tier, target_age_tier, is_active, is_custom, '
              'transcript, vocab_sense_ids, vocab_sense_stats, vocab_token_map, furigana_payload, created_at',
              'language_id = {L}'),
    'exercises': ('id', 'id, language_id, word_sense_id, word_asset_id, exercise_type, ladder_level, is_active',
                  'language_id = {L}'),
    'word_assets': ('id', 'id, sense_id, language_id, asset_type, content, model_used, prompt_version, is_valid, '
                    'validation_errors, validation_warnings, generation_batch_id, created_at',
                    'language_id = {L}'),
}
TARGET_BYTES = 2_000_000   # per page (estimated JSON size)
SMALL_BYTES = 300_000      # tables below this ride along with the base query
JSON_FACTOR = 2.0          # JSON text is roughly 2x pg_column_size


def where(table, lang_id):
    w = TABLES[table][2]
    return 'TRUE' if w is None else w.format(L=lang_id)


def select(table, lang_id, part=None):
    key, cols, _ = TABLES[table]
    w = where(table, lang_id)
    if part:
        k, n = part
        w += f' AND abs(hashtext({key}::text)) % {n} = {k}'
    return f'(SELECT json_agg(t) FROM (SELECT {cols} FROM {table} WHERE {w}) t)'


def cmd_sizes(args):
    lid = nt_lang.language_id(args.lang)
    parts = ', '.join(
        f"'{t}', (SELECT coalesce(sum(pg_column_size(t.*)), 0) FROM "
        f"(SELECT {TABLES[t][1]} FROM {t} WHERE {where(t, lid)}) t)" for t in TABLES)
    print(f'SELECT json_build_object({parts}) AS sizes;')


def cmd_queries(args):
    lid = nt_lang.language_id(args.lang)
    sizes = json.loads(args.sizes)
    if isinstance(sizes, list):  # the raw execute_sql row
        sizes = sizes[0]
    if 'sizes' in sizes:
        sizes = sizes['sizes'] if isinstance(sizes['sizes'], dict) else json.loads(sizes['sizes'])
    base, paged = [], []
    for t in TABLES:
        est = float(sizes.get(t, 0)) * JSON_FACTOR
        if est < SMALL_BYTES:
            base.append(t)
        else:
            paged.append((t, max(1, math.ceil(est / TARGET_BYTES))))
    if 'prompt_templates' not in base:  # keep the base query large enough to be saved to a file
        paged = [p for p in paged if p[0] != 'prompt_templates']
        base.append('prompt_templates')
    queries = ['SELECT ' + ', '.join(f'{select(t, lid)} AS {t}' for t in base) + ';']
    for t, n in paged:
        for k in range(n):
            queries.append(f'SELECT {select(t, lid, (k, n))} AS {t};')
    path = os.path.join(SNAP, f'_snapshot_{args.lang}.sql')
    os.makedirs(SNAP, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        for i, q in enumerate(queries, 1):
            fh.write(f'-- {i}/{len(queries)}\n{q}\n\n')
    print(f'{len(queries)} queries -> {path}')
    print('base query tables:', ', '.join(base))
    for t, n in paged:
        print(f'  {t}: {n} page(s)')


def cmd_add(args):
    for f in args.files:
        if f == '-':
            obj = json.load(sys.stdin)
            rows = obj[0] if isinstance(obj, list) else obj
        else:
            rows = spill.load(f)[0]
        for table, v in rows.items():
            if table not in TABLES:
                raise SystemExit(f'{f}: unknown table {table!r}')
            new = (json.loads(v) if isinstance(v, str) else v) or []
            path = os.path.join(SNAP, f'{table}.json')
            old = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else []
            key = TABLES[table][0]
            merged = {r[key]: r for r in old}
            merged.update({r[key]: r for r in new})
            with open(path, 'w', encoding='utf-8') as fh:
                json.dump(list(merged.values()), fh, ensure_ascii=False)
            print(f'{table}: +{len(new)} rows -> {len(merged)} total')


def cmd_status(args):
    lid = nt_lang.language_id(args.lang)
    for t in TABLES:
        path = os.path.join(SNAP, f'{t}.json')
        rows = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else []
        if TABLES[t][2] is None:
            n = len(rows)
        elif t == 'dim_word_senses':
            vocab = {r['id'] for r in json.load(open(os.path.join(SNAP, 'dim_vocabulary.json'), encoding='utf-8'))
                     if r.get('language_id') == lid} if os.path.exists(os.path.join(SNAP, 'dim_vocabulary.json')) else set()
            n = sum(1 for r in rows if r.get('vocab_id') in vocab and r.get('definition_language_id') == lid)
        else:
            n = sum(1 for r in rows if r.get('language_id') == lid)
        print(f'{t}: {n}')
    counts = ', '.join(f"'{t}', (SELECT count(*) FROM {t} WHERE {where(t, lid)})" for t in TABLES)
    print(f'\nexpected counts: SELECT json_build_object({counts}) AS counts;')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('sizes'); p.add_argument('--lang', required=True)
    p = sub.add_parser('queries'); p.add_argument('--lang', required=True); p.add_argument('--sizes', required=True)
    p = sub.add_parser('add'); p.add_argument('files', nargs='+')
    p = sub.add_parser('status'); p.add_argument('--lang', required=True)
    args = ap.parse_args()
    {'sizes': cmd_sizes, 'queries': cmd_queries, 'add': cmd_add, 'status': cmd_status}[args.cmd](args)


if __name__ == '__main__':
    main()
