"""Retire Chinese "words" that jieba invented (2026-11-12).

The reviewed non-words in data/lexicon/zh_split_words.txt (人用, 会用, 风一吹,
...) were created as vocabulary from jieba fragments, as were two names
(小明, 纳维; kept whole in the text but unlinked). Since the checked
splitter (services/vocabulary/zh_segmenter.py) no longer produces them, this
script takes them out of the content that already uses them:

- tests.vocab_token_map: each fake token is split into its real pieces
  (人用 -> 人 / 用), each piece linked to the sense that piece already has in
  that test, else the sense most word maps use for it, else its dictionary
  sense (rank 1, Chinese definition); the text is unchanged.
- tests.vocab_sense_ids: the fake senses removed, the pieces' senses added.
- test_sentences: token spans of the affected tests refreshed in place
  (rows updated, never recreated), exactly as build_test_sentences.py
  --repair-token-maps does.
- questions.sense_ids: the fake senses removed.
- exercises: those for the fake senses deactivated (is_active = false).
- calibration_anchor_blocklist: the fake senses added, so calibration never
  asks about them.

dim_vocabulary / dim_word_senses rows are kept (nothing is deleted), so the
change is reversible: --apply first writes every row it will change to
data/zh_segmentation/<date>_retirement_backup.json.gz, and --restore puts them
back (and removes the blocklist rows it added).

Usage:
    python scripts/retire_zh_fake_words.py              # dry run: report only
    python scripts/retire_zh_fake_words.py --apply
    python scripts/retire_zh_fake_words.py --restore data/zh_segmentation/2026-11-12_retirement_backup.json.gz
"""

import argparse
import datetime
import gzip
import json
import logging
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    from _common import admin_db, base_parser, bootstrap, paginate
except ImportError:  # run or imported as scripts.<name>
    from scripts._common import admin_db, base_parser, bootstrap, paginate

bootstrap(log_format='%(message)s')


from services.dual_translation import sentence_refs as sr  # noqa: E402
from services.vocabulary import zh_segmenter  # noqa: E402

log = logging.getLogger('retire_zh_fake_words')
for noisy in ('httpx', 'jieba'):
    logging.getLogger(noisy).setLevel(logging.WARNING)

ZH = 1
REASON = 'zh fake word (jieba fragment), retired 2026-11-12'
# Names that were made vocabulary: kept whole in the text but unlinked (sense
# 0) -- splitting 小明 would link 小 "small" and 明 "bright".
NAMES_KEPT_WHOLE = frozenset({'小明', '纳维'})


def fetch_all(query_fn, page=1000):
    return list(paginate(query_fn, page))


def plan(db) -> dict:
    fakes = zh_segmenter.forced_splits() | NAMES_KEPT_WHOLE
    vocab = fetch_all(lambda: db.table('dim_vocabulary').select('id, lemma').eq('language_id', ZH).order('id'))
    fake_vocab = {v['id']: v['lemma'] for v in vocab if v['lemma'] in fakes}
    lemma_vocab = {v['lemma']: v['id'] for v in vocab if v['lemma'] not in fakes}
    senses = []
    ids = list(fake_vocab)
    for i in range(0, len(ids), 100):
        senses += db.table('dim_word_senses').select('id, vocab_id').in_('vocab_id', ids[i:i + 100]).execute().data or []
    fake_senses = {s['id'] for s in senses}

    tests = fetch_all(lambda: db.table('tests').select('id, slug, transcript, vocab_token_map, vocab_sense_ids')
                      .eq('language_id', ZH).eq('is_active', True).order('id'))
    # surface -> sense ids the word maps use for it (real words only)
    usage = defaultdict(Counter)
    for t in tests:
        for surf, sid in t.get('vocab_token_map') or []:
            if sid and sid not in fake_senses:
                usage[surf.strip()][sid] += 1
    rank1_cache = {}

    def rank1(piece):
        if piece not in rank1_cache:
            vid = lemma_vocab.get(piece)
            sid = 0
            if vid:
                rows = (db.table('dim_word_senses').select('id').eq('vocab_id', vid)
                        .eq('definition_language_id', ZH).order('sense_rank').limit(1).execute().data or [])
                sid = rows[0]['id'] if rows else 0
            rank1_cache[piece] = sid
        return rank1_cache[piece]

    changes = []
    for t in tests:
        tm = t.get('vocab_token_map') or []
        if not any(sid in fake_senses or surf.strip() in fakes for surf, sid in tm):
            continue
        local = defaultdict(Counter)
        for surf, sid in tm:
            if sid and sid not in fake_senses:
                local[surf.strip()][sid] += 1
        new_map, split = [], []
        for surf, sid in tm:
            if surf.strip() in NAMES_KEPT_WHOLE:
                new_map.append([surf, 0])
                split.append(f'{surf}->(unlinked name)')
            elif sid in fake_senses or surf.strip() in fakes:
                pieces = []
                for piece, _ in zh_segmenter._resplit(surf):
                    p = piece.strip()
                    psid = (local[p].most_common(1)[0][0] if local.get(p) else
                            usage[p].most_common(1)[0][0] if usage.get(p) else rank1(p) if p else 0)
                    pieces.append([piece, psid])
                assert ''.join(x for x, _ in pieces) == surf, (t['id'], surf)
                new_map += pieces
                split.append(f"{surf}->{'/'.join(x for x, _ in pieces)}")
            else:
                new_map.append([surf, sid])
        assert ''.join(s for s, _ in new_map) == ''.join(s for s, _ in tm), t['id']
        old_ids = list(t.get('vocab_sense_ids') or [])
        added = [sid for _, sid in new_map if sid and sid not in old_ids]
        new_ids = [s for s in old_ids if s not in fake_senses] + list(dict.fromkeys(added))
        changes.append({'test': t, 'new_map': new_map, 'new_ids': new_ids, 'split': split})

    questions = []
    fs = sorted(fake_senses)
    for i in range(0, len(fs), 100):
        questions += db.table('questions').select('id, sense_ids').overlaps('sense_ids', fs[i:i + 100]).execute().data or []
    questions = list({q['id']: q for q in questions}.values())
    exercises = []
    for i in range(0, len(fs), 100):
        exercises += (db.table('exercises').select('id').in_('word_sense_id', fs[i:i + 100])
                      .eq('is_active', True).execute().data or [])
    blocked = set()
    for i in range(0, len(fs), 100):
        blocked |= {r['sense_id'] for r in (db.table('calibration_anchor_blocklist').select('sense_id')
                                            .in_('sense_id', fs[i:i + 100]).execute().data or [])}
    return {'fake_vocab': fake_vocab, 'fake_senses': fake_senses, 'changes': changes,
            'questions': questions, 'exercises': [e['id'] for e in exercises],
            'to_block': sorted(fake_senses - blocked)}


def report(p: dict) -> None:
    log.info('fake words: %d (%d senses)', len(p['fake_vocab']), len(p['fake_senses']))
    log.info('tests to update: %d', len(p['changes']))
    for c in p['changes'][:10]:
        log.info('  %s: %s', c['test']['slug'][:45], ', '.join(c['split'][:6]))
    unlinked = sum(1 for c in p['changes'] for s, sid in c['new_map'] if s.strip() and not sid
                   and any(s.strip() in x for x in c['split']))
    log.info('pieces left without a sense: %d', unlinked)
    log.info('questions to update: %d', len(p['questions']))
    log.info('exercises to deactivate: %d', len(p['exercises']))
    log.info('senses to add to the calibration blocklist: %d', len(p['to_block']))


def apply(db, p: dict) -> str:
    fake = p['fake_senses']
    backup = {'date': datetime.date.today().isoformat(), 'reason': REASON,
              'fake_vocab': p['fake_vocab'], 'tests': [], 'test_sentences': [],
              'questions': p['questions'], 'exercises_deactivated': p['exercises'],
              'blocklist_added': p['to_block']}
    plans = []
    for c in p['changes']:
        t = c['test']
        spans = sr.segment_with_spans(t['transcript'], 'zh')
        sr.attach_token_spans(spans, c['new_map'])
        rows = (db.table('test_sentences').select('id, idx, char_start, char_end, token_start, token_end')
                .eq('test_id', t['id']).order('idx').execute().data or [])
        by_idx = {sp.idx: sp for sp in spans}
        ok = [r for r in rows if r['idx'] in by_idx and by_idx[r['idx']].char_start == r['char_start']
              and by_idx[r['idx']].char_end == r['char_end']]
        backup['tests'].append({'id': t['id'], 'vocab_token_map': t['vocab_token_map'],
                                'vocab_sense_ids': t['vocab_sense_ids']})
        backup['test_sentences'] += [{'id': r['id'], 'token_start': r['token_start'],
                                      'token_end': r['token_end']} for r in ok]
        plans.append((c, ok, by_idx))
    out_dir = os.path.join(ROOT, 'data', 'zh_segmentation')
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{backup['date']}_retirement_backup.json.gz")
    n = 2
    while os.path.exists(path):  # never overwrite an earlier run's backup
        path = os.path.join(out_dir, f"{backup['date']}_retirement_backup_{n}.json.gz")
        n += 1
    with gzip.open(path, 'wt', encoding='utf-8') as fh:
        json.dump(backup, fh, ensure_ascii=False)
    log.info('backup written: %s', path)

    for c, ok, by_idx in plans:
        db.table('tests').update({'vocab_token_map': c['new_map'], 'vocab_sense_ids': c['new_ids']}) \
            .eq('id', c['test']['id']).execute()
        for r in ok:
            sp = by_idx[r['idx']]
            db.table('test_sentences').update({'token_start': sp.token_start, 'token_end': sp.token_end}) \
                .eq('id', r['id']).execute()
    for q in p['questions']:
        db.table('questions').update({'sense_ids': [s for s in q['sense_ids'] if s not in fake]}) \
            .eq('id', q['id']).execute()
    ids = p['exercises']
    for i in range(0, len(ids), 100):
        db.table('exercises').update({'is_active': False}).in_('id', ids[i:i + 100]).execute()
    if p['to_block']:
        db.table('calibration_anchor_blocklist').insert(
            [{'sense_id': s, 'reason': REASON} for s in p['to_block']]).execute()
    log.info('applied: %d tests, %d questions, %d exercises deactivated, %d senses blocklisted',
             len(plans), len(p['questions']), len(ids), len(p['to_block']))
    return path


def restore(db, path: str) -> None:
    with gzip.open(path, 'rt', encoding='utf-8') as fh:
        b = json.load(fh)
    for t in b['tests']:
        db.table('tests').update({'vocab_token_map': t['vocab_token_map'],
                                  'vocab_sense_ids': t['vocab_sense_ids']}).eq('id', t['id']).execute()
    for r in b['test_sentences']:
        db.table('test_sentences').update({'token_start': r['token_start'], 'token_end': r['token_end']}) \
            .eq('id', r['id']).execute()
    for q in b['questions']:
        db.table('questions').update({'sense_ids': q['sense_ids']}).eq('id', q['id']).execute()
    ids = b['exercises_deactivated']
    for i in range(0, len(ids), 100):
        db.table('exercises').update({'is_active': True}).in_('id', ids[i:i + 100]).execute()
    if b['blocklist_added']:
        db.table('calibration_anchor_blocklist').delete().in_('sense_id', b['blocklist_added']) \
            .eq('reason', b['reason']).execute()
    log.info('restored from %s', path)


def main() -> int:
    ap = base_parser(__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--restore', metavar='BACKUP')
    args = ap.parse_args()
    db = admin_db()
    if args.restore:
        restore(db, args.restore)
        return 0
    p = plan(db)
    report(p)
    if args.apply:
        apply(db, p)
    else:
        log.info('dry run: nothing written (use --apply)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
