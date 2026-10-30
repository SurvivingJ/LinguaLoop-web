"""Collect reviewer-flagged mined (corpus) sentences that use the target in the
wrong sense, only inside a compound, or as a prefix. Output: issues/corpus_wrong_sense.csv"""
import csv, glob, json, os, re

ROOT = 'data/exercise_seeding/ja'
KEY = re.compile(r'mined|corpus', re.I)
BAD = re.compile(r'sense|compound|prefix|literal|別義|複合|接頭|drift|inside|only in|wrong', re.I)

def mined_sentences(run):
    out, cur, grab = {}, None, False
    for f in glob.glob(f'{run}/fat_seed/briefs/*.md'):
        for line in open(f, encoding='utf-8'):
            m = re.match(r'## sense (\d+):', line)
            if m:
                cur, grab = int(m.group(1)), False
                out[cur] = []
                continue
            if cur is None:
                continue
            if line.startswith('- mined sentences'):
                grab = True
                continue
            if grab:
                m = re.match(r'\s+(\d+)\. (.*)', line)
                if m:
                    out[cur].append((int(m.group(1)), m.group(2).strip()))
                else:
                    grab = False
    return out

rows = []
for run in sorted(glob.glob(f'{ROOT}/wf*/r*') + glob.glob(f'{ROOT}/fatseed_*')):
    revs = glob.glob(f'{run}/fat_seed/review/*.json')
    if not revs:
        continue
    mined = None
    for rf in revs:
        try:
            v = json.load(open(rf, encoding='utf-8'))
        except Exception:
            continue
        notes = v.get('notes') or ''
        if not (KEY.search(notes) and BAD.search(notes)):
            continue
        if mined is None:
            mined = mined_sentences(run)
        sid = v['sense_id']
        lemma = ''
        doc = f'{run}/fat_seed/reviewed/{sid}.json'
        if os.path.exists(doc):
            lemma = json.load(open(doc, encoding='utf-8')).get('lemma', '')
        sents = mined.get(sid, [])
        rows.append({
            'sense_id': sid, 'lemma': lemma, 'run': os.path.relpath(run, ROOT),
            'verdict': v.get('verdict', ''),
            'mined_sentences': ' | '.join(f'{i}. {t}' for i, t in sents),
            'reviewer_note': notes.replace('\n', ' '),
        })

os.makedirs(f'{ROOT}/issues', exist_ok=True)
with open(f'{ROOT}/issues/corpus_wrong_sense.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print(len(rows), 'flagged senses')
