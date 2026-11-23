"""Shared pool/list loader for the placement simulation (standard library only).
Builds the check pool per language from read-only exports: dict.json words subsampled per Zipf band to the
measured frame sizes N_b, matched to HSK 3.0 (2025) / JLPT community lists. Untrusted list files are only read."""
import csv, json, random, re, collections

FRAME = {'ja': [577, 425, 621, 655, 537, 283, 77], 'zh': [303, 617, 742, 691, 664, 435, 171]}
LANGID = {'zh': 1, 'ja': 3}
NLEV = {'zh': 7, 'ja': 5}
LEVEL_NAMES = {'zh': ['HSK1', 'HSK2', 'HSK3', 'HSK4', 'HSK5', 'HSK6', 'HSK7-9'], 'ja': ['N5', 'N4', 'N3', 'N2', 'N1']}


def band_of(z):
    for b, t in ((7, 5.5), (6, 5.0), (5, 4.5), (4, 4.0), (3, 3.5), (2, 3.0)):
        if z >= t:
            return b
    return 1


def is_han(c):
    return '一' <= c <= '鿿' or '㐀' <= c <= '䶿' or c == '々'


def is_hira(c):
    return 'ぁ' <= c <= 'ゟ' or c == 'ー'


def is_kata(c):
    return '゠' <= c <= 'ヿ' or c == 'ー'


def kata2hira(s):
    return ''.join(chr(ord(c) - 0x60) if 0x30A1 <= ord(c) <= 0x30F6 else c for c in s)


def expand_zh(entry):  # same rule as mock/scripts/build_data.py:103
    e = re.sub(r'[0-9０-９]+$', '', entry.strip())
    forms = []
    for alt in re.split(r'[|｜]', e):
        alt = alt.replace('…', '').replace('...', '')
        m = re.search(r'（(.*?)）|\((.*?)\)', alt)
        if m:
            inner = m.group(1) or m.group(2) or ''
            forms += [alt[:m.start()] + alt[m.end():], alt[:m.start()] + inner + alt[m.end():]]
        else:
            forms.append(alt)
    return [f for f in forms if f]


def load_pool(scr, lang):
    rows = json.load(open(f'{scr}/mock/data/dict.json', encoding='utf-8'))['dict']
    ids = json.load(open(f'{scr}/placement/sim/data/anchor_pool_ids.json', encoding='utf-8'))
    pool_ids = set(ids[f'{LANGID[lang]}_def_en'])      # live calibration_anchor_pool, definition language en (read-only SELECT)
    pron_ids = set(ids[f'{LANGID[lang]}_pron'])         # live pool rows with has_pronunciation
    rows = [r for r in rows if r[0] == LANGID[lang] and r[4] is not None and r[1] in pool_ids]
    by = collections.defaultdict(list)
    for r in rows:
        by[band_of(r[4])].append(r)
    rng = random.Random(7 + LANGID[lang])
    pool = []
    for b in range(1, 8):
        cand = sorted(by[b], key=lambda r: r[1])
        pool += rng.sample(cand, FRAME[lang][b - 1])
    words = []
    for r in pool:
        lemma, reading, z = r[2], (r[3] or ''), float(r[4])
        if lang == 'zh':
            reading = reading.split(' (')[0]
        han = sum(1 for c in lemma if is_han(c))
        kana_only = han == 0 and all(is_hira(c) or is_kata(c) for c in lemma)
        kata_only = kana_only and any(is_kata(c) and c != 'ー' for c in lemma) and not any(is_hira(c) and c != 'ー' for c in lemma)
        words.append(dict(vid=r[1], lemma=lemma, reading=reading, z=z, band=band_of(z), han=han, n=len(lemma),
                          kana_only=kana_only if lang == 'ja' else False, kata_only=kata_only if lang == 'ja' else False,
                          has_r=(r[1] in pron_ids) and not (lang == 'ja' and kana_only), lev=0))
    # exam levels (lowest level wins); unmatched list entries are "not in the pool"
    lists = f'{scr}/kr/lists'
    idx = collections.defaultdict(list)
    for i, w in enumerate(words):
        idx[w['lemma']].append(i)
    matched = collections.Counter(); listed = collections.Counter()
    if lang == 'zh':
        for li, lv in enumerate(['1', '2', '3', '4', '5', '6', '7-9']):
            seen = set()
            for line in open(f'{lists}/krmanik_HSK-3.0/2025/HSK_Level_{lv}_words.txt', encoding='utf-8'):
                raw = line.strip()
                if not raw:
                    continue
                forms = expand_zh(raw)
                if not forms or forms[0] in seen:
                    continue
                seen.add(forms[0]); listed[li + 1] += 1
                hit = next((f for f in forms if f in idx), None)
                if hit is None:
                    continue
                matched[li + 1] += 1
                for i in idx[hit]:
                    if words[i]['lev'] == 0:
                        words[i]['lev'] = li + 1
    else:
        rd = collections.defaultdict(list)
        for i, w in enumerate(words):
            rd[kata2hira(w['reading'] or w['lemma'])].append(i)
        for li, lv in enumerate(['n5', 'n4', 'n3', 'n2', 'n1']):
            seen = set()
            with open(f'{lists}/jamsinclair_open-anki-jlpt-decks/{lv}.csv', encoding='utf-8') as fh:
                for row in csv.DictReader(fh):
                    ex, kana = (row.get('expression') or '').strip(), (row.get('reading') or '').strip()
                    key = (ex, kana)
                    if key in seen or not ex:
                        continue
                    seen.add(key); listed[li + 1] += 1
                    hits = list(idx.get(ex, []))
                    if not hits:
                        cands = rd.get(kata2hira(kana or ex), [])
                        exk = {c for c in ex if is_han(c)}
                        if not exk:   # kana expression: same reading, kana lemma
                            hits = [i for i in cands if words[i]['han'] == 0]
                        else:
                            hits = [i for i in cands if exk & {c for c in words[i]['lemma'] if is_han(c)}]
                    if not hits:
                        continue
                    matched[li + 1] += 1
                    for i in hits[:1]:
                        if words[i]['lev'] == 0:
                            words[i]['lev'] = li + 1
    return words, dict(listed=dict(listed), matched=dict(matched))


if __name__ == '__main__':
    import sys
    scr = sys.argv[1]
    for lang in ('zh', 'ja'):
        words, info = load_pool(scr, lang)
        print(lang, 'pool', len(words), 'bands', [sum(1 for w in words if w['band'] == b) for b in range(1, 8)])
        print('  list entries per level', info['listed'], 'matched into pool', info['matched'])
        lev = collections.Counter(w['lev'] for w in words)
        print('  pool words per level (0=unlisted)', dict(sorted(lev.items())))
        print('  pool words by band x level:')
        for b in range(1, 8):
            print('   band', b, [sum(1 for w in words if w['band'] == b and w['lev'] == L) for L in range(0, NLEV[lang] + 1)])
        if lang == 'ja':
            print('  kana-only', sum(w['kana_only'] for w in words), 'katakana-only', sum(w['kata_only'] for w in words),
                  'with kanji', sum(1 for w in words if w['han'] > 0), 'reading item available', sum(w['has_r'] for w in words))
        else:
            print('  single-char', sum(1 for w in words if w['n'] == 1), 'multi-char', sum(1 for w in words if w['n'] >= 2),
                  'reading item available', sum(w['has_r'] for w in words))
        print('  duplicate lemmas', sum(1 for v in collections.Counter(w['lemma'] for w in words).values() if v > 1))
