"""jieba vs Stanza on every active Chinese test transcript (read-only).

See wiki/evaluations/zh-tagger-stanza-vs-jieba-2026-11-12.md. Needs `pip install stanza`
and stanza.download('zh-hans', processors='tokenize,pos') (huggingface.co); reads
tests.json / vocab.json (active zh tests and dim_vocabulary) from the working directory.
"""
import json, time, logging, sys
from collections import Counter, defaultdict
sys.path.insert(0, '/home/user/LinguaLoop-web')
from services.vocabulary.pos import normalize_pos
import jieba, jieba.posseg as pseg
jieba.setLogLevel(logging.ERROR)
import stanza

tests = json.load(open('tests.json'))
texts = [t['transcript'] for t in tests]

t0 = time.time(); J = [[(w.word, w.flag) for w in pseg.lcut(x)] for x in texts]; tj = time.time() - t0
nlp = stanza.Pipeline('zh-hans', dir='/tmp/claude-0/stanza_resources', processors='tokenize,pos',
                      download_method=None, use_gpu=False, verbose=False)
t0 = time.time()
S = []
for x in texts:
    d = nlp(x)
    S.append([(w.text, w.upos, w.xpos) for s in d.sentences for w in s.words])
ts = time.time() - t0
chars = sum(len(x) for x in texts)
print(f'speed: jieba {chars/tj:,.0f} chars/s, stanza {chars/ts:,.0f} chars/s ({ts:.1f}s for {chars} chars)')

def spans(toks):
    out, i = [], 0
    for tok in toks:
        w = tok[0]
        out.append((i, i + len(w), tok)); i += len(w)
    return out

ws = lambda w: not w.strip()
same_b = tot_j = tot_s = 0
pos_agree = pos_tot = 0
pos_dis = Counter(); pos_dis_ex = defaultdict(list)
j_only = Counter(); j_only_ex = {}
for x, j, s in zip(texts, J, S):
    js = [(a, b, t) for a, b, t in spans(j) if not ws(t[0])]
    # stanza drops whitespace; re-anchor its tokens on the text
    ss, i = [], 0
    for t in s:
        k = x.find(t[0], i)
        if k < 0: continue
        ss.append((k, k + len(t[0]), t)); i = k + len(t[0])
    jb = {(a, b): t for a, b, t in js}; sb = {(a, b): t for a, b, t in ss}
    tot_j += len(jb); tot_s += len(sb)
    for key, jt in jb.items():
        if key in sb:
            same_b += 1
            st = sb[key]
            if st[1] in ('PUNCT', 'SYM', 'X'): continue
            jp, sp = normalize_pos(jt[1]), ('measure_word' if st[2] == 'NNB' else normalize_pos(st[1]))
            pos_tot += 1
            if jp == sp: pos_agree += 1
            else:
                pos_dis[(jp, sp)] += 1
                if len(pos_dis_ex[(jp, sp)]) < 6: pos_dis_ex[(jp, sp)].append(f'{jt[0]}[{jt[1]}/{st[1]}]')
        elif len(jt[0]) >= 2 and not any(c in '，。！？、；：“”‘’（）《》' for c in jt[0]):
            j_only[jt[0]] += 1
            if jt[0] not in j_only_ex:
                a, b = key
                j_only_ex[jt[0]] = x[max(0, a - 6):b + 6] + '  →stanza: ' + ' | '.join(
                    t[0] for (c, d, t) in ss if c < b + 4 and d > a - 4)

prec = same_b / tot_j; rec = same_b / tot_s
print(f'segmentation: {same_b} identical tokens; jieba {tot_j}, stanza {tot_s}; agreement F1 {2*prec*rec/(prec+rec):.3f}')
print(f'part of speech on identically split words: {pos_agree}/{pos_tot} agree ({pos_agree/pos_tot:.1%})')
print('\ntop POS disagreements (jieba -> stanza):')
for (a, b), n in pos_dis.most_common(14):
    print(f'  {n:4} {a} -> {b}:  ' + '  '.join(pos_dis_ex[(a, b)]))

vocab = {v['lemma'] for v in json.load(open('vocab.json'))}
jo_in_vocab = [w for w in j_only if w in vocab]
print(f'\njieba-only words (2+ chars) Stanza splits differently: {len(j_only)} distinct; {len(jo_in_vocab)} are in the dictionary')
json.dump({'j_only': j_only.most_common(), 'ex': j_only_ex, 'in_vocab': jo_in_vocab,
           'pos_dis': [[a, b, n, pos_dis_ex[(a, b)]] for (a, b), n in pos_dis.most_common()]},
          open('trial_out.json', 'w'), ensure_ascii=False, indent=1)
for w in ['宗教改革', '人用']:
    hits = [(t[0], t[1], t[2]) for s in S for t in s if t[0] == w]
    print(f'{w}: stanza tags', Counter((h[1], h[2]) for h in hits).most_common(3) or 'never produced as a token')
