"""Idiom trainer content: validate the authored lists and cards, and build the static files.

    python scripts/idiom_trainer.py validate FILE [...]     # a list or a cards file
    python scripts/idiom_trainer.py stats
    python scripts/idiom_trainer.py build [--check]         # -> static/data/idioms/<lang>/

Content lives in data/idioms/<lang>/ (lists/, cards/, review/); the contract is
data/idioms/AUTHORING.md. Nothing here reads or writes the database: every
command works on local files only.
"""
import argparse
import hashlib
import json
import os
import re
import sys

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from services.particle_drill import markup  # noqa: E402

DATA = os.path.join(REPO, 'data', 'idioms')
STATIC = os.path.join(REPO, 'static', 'data', 'idioms')
CHUNK = 10

# lang -> [(set key, id code, title in the language, English title, core size)]
SETS = {
    'zh': [('chengyu', 'cy', '成语', 'Chengyu', 200),
           ('guanyong', 'gy', '惯用语', 'Colloquial expressions', 80),
           ('suyu', 'sy', '俗语', 'Sayings', 40)],
    'ja': [('kanyo', 'ky', '慣用句', 'Idioms', 200),
           ('yoji', 'yj', '四字熟語', 'Four-character idioms', 80),
           ('kotowaza', 'kw', 'ことわざ', 'Proverbs', 50)],
}
# The full tier (owner, 2026-11-28: "Write the full tier"): each list is extended
# after its core entries, which keep their place, ids and cards.
FULL = {('zh', 'chengyu'): 600, ('zh', 'guanyong'): 150, ('zh', 'suyu'): 100,
        ('ja', 'kanyo'): 450, ('ja', 'yoji'): 200, ('ja', 'kotowaza'): 120}
LANGUAGE_IDS = {'zh': 1, 'ja': 3}
TAGS = frozenset('effort success failure caution haste joy anger fear sadness relationship speech '
                 'knowledge foolishness change time quantity appearance behaviour luck difficulty '
                 'money work'.split())
REGS = ('spoken', 'written', 'formal', 'neutral')
TONES = ('praise', 'criticism', 'humorous', 'neutral')
LIST_KEYS = ('id', 't', 'r', 'mean', 'lvl', 'tag')
CARD_KEYS = LIST_KEYS + ('lit', 'story', 'use', 'near', 'parts', 'cue', 'ctx', 'bad')

_HAN = re.compile(r'[㐀-鿿]')
_ZH_TEXT = re.compile(r'^[㐀-鿿，]+$')
_ZH_SENT = re.compile(r'^[㐀-鿿，。！？、：；“”‘’（）《》…—·]+$')
_JA_TEXT = re.compile(r'^[ぁ-ゖァ-ヺー㐀-鿿々]+$')
_KANA = re.compile(r'^[ぁ-ゖー]+$')
_EN = re.compile(r'[A-Za-z]')
_CJK = re.compile(r'[぀-ヿ㐀-鿿]')
_BRACED = re.compile(r'\{([^{}]*)\}')


def set_info(lang, key):
    for row in SETS.get(lang, ()):
        if row[0] == key:
            return row
    return None


def where_of(path):
    """(lang, kind, set key, chunk number or None) from a content path."""
    parts = os.path.normpath(os.path.abspath(path)).split(os.sep)
    try:
        lang, kind, name = parts[-3], parts[-2], parts[-1]
    except IndexError:
        return None
    if lang not in SETS or kind not in ('lists', 'cards') or not name.endswith('.json'):
        return None
    stem = name[:-5]
    if kind == 'lists':
        return (lang, kind, stem, None) if set_info(lang, stem) else None
    m = re.match(r'^([a-z]+)-(\d{2})$', stem)
    if not m or not set_info(lang, m.group(1)):
        return None
    return lang, kind, m.group(1), int(m.group(2))


def list_path(lang, key):
    return os.path.join(DATA, lang, 'lists', key + '.json')


def load_json(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def load_list(lang, key):
    path = list_path(lang, key)
    return load_json(path) if os.path.exists(path) else []


def _text(value, lo, hi, label, errs, *, english=True):
    if not isinstance(value, str) or not lo <= len(value) <= hi:
        errs.append(f'{label} must be {lo} to {hi} characters')
        return False
    if english and (not _EN.search(value) or _CJK.search(value)):
        errs.append(f'{label} must be English')
        return False
    return True


def _zh_reading(text, reading, errs):
    import grammar_drills as gd
    gd.check_py(text.replace('，', ''), reading, 'r', errs)


def check_list_entry(row, lang, code, errs):
    """Problems of one list entry (appended to errs); True when its shape is usable."""
    if not isinstance(row, dict):
        errs.append('not an object')
        return False
    missing = [k for k in LIST_KEYS if k not in row]
    if missing:
        errs.append(f'missing {missing}')
        return False
    if not isinstance(row['id'], str) or not re.match(rf'^{code}\d{{3}}$', row['id']):
        errs.append(f'id must be {code} and three digits')
    t, r = row['t'], row['r']
    if not isinstance(t, str) or not isinstance(r, str) or not t or not r:
        errs.append('t and r must be text')
        return False
    if lang == 'zh':
        if not _ZH_TEXT.match(t) or not 2 <= len(t) <= 16 or t.count('，') > 1:
            errs.append('t must be 2 to 16 simplified characters (one comma allowed in a saying)')
        else:
            _zh_reading(t, r, errs)
    else:
        if not _JA_TEXT.match(t) or not 2 <= len(t) <= 20:
            errs.append('t must be 2 to 20 kana and kanji, no furigana')
        if not _KANA.match(r):
            errs.append('r must be the reading in hiragana')
    _text(row['mean'], 3, 70, 'mean', errs)
    if row['lvl'] not in (1, 2, 3):
        errs.append('lvl must be 1, 2 or 3')
    if row['tag'] not in TAGS:
        errs.append('tag is not in the list of themes')
    return True


def check_sentence(s, lang, key, idiom, label, errs):
    """A context sentence with the idiom once in braces."""
    if not isinstance(s, str):
        errs.append(f'{label} missing')
        return
    marked = _BRACED.findall(s)
    if len(marked) != 1 or not marked[0]:
        errs.append(f'{label}: the idiom must appear once, in braces')
        return
    if lang == 'zh':
        plain = s.replace('{', '').replace('}', '')
        if not _ZH_SENT.match(plain):
            errs.append(f'{label}: simplified characters and full-width punctuation only')
        if not 8 <= len(plain) <= 60:
            errs.append(f'{label}: length {len(plain)} outside 8-60')
        form = marked[0]
        if key in ('chengyu', 'suyu'):
            if form != idiom:
                errs.append(f'{label}: the braces must hold {idiom} unchanged')
        elif form[0] != idiom[0] or form[-1] != idiom[-1]:
            errs.append(f'{label}: the braces must run from the first to the last character of {idiom}')
        return
    _segs, slots, perrs = markup.parse(s)
    errs.extend(f'{label}: {e}' for e in perrs)
    plain = markup.plain(s)
    if re.search(r'[0-9０-９A-Za-z]', plain):
        errs.append(f'{label}: no digits or Latin letters')
    if not 8 <= len(plain) <= 70:
        errs.append(f'{label}: length {len(plain)} outside 8-70')
    if key == 'yoji' and slots and idiom not in slots[0]['a']:
        errs.append(f'{label}: the braces must hold {idiom}')


def check_card(card, lang, key, entry, errs):
    if not isinstance(card, dict):
        errs.append('not an object')
        return
    extra = set(card) - set(CARD_KEYS)
    missing = [k for k in CARD_KEYS if k not in card]
    if extra:
        errs.append(f'unknown fields {sorted(extra)}')
    if missing:
        errs.append(f'missing {missing}')
        return
    for k in LIST_KEYS:
        if entry is not None and card[k] != entry[k]:
            errs.append(f'{k} differs from the list ({entry[k]!r})')
    idiom = card['t']
    _text(card['lit'], 5, 120, 'lit', errs)
    story = card['story']
    if story is not None:
        if not isinstance(story, dict) or set(story) != {'text', 'source'}:
            errs.append('story must be null or {text, source}')
        else:
            _text(story['text'], 80, 600, 'story.text', errs)
            _text(story['source'], 2, 80, 'story.source', errs, english=False)
    use = card['use']
    if not isinstance(use, dict) or set(use) != {'reg', 'tone', 'how'}:
        errs.append('use must be {reg, tone, how}')
    else:
        if use['reg'] not in REGS:
            errs.append(f'use.reg must be one of {REGS}')
        if use['tone'] not in TONES:
            errs.append(f'use.tone must be one of {TONES}')
        _text(use['how'], 10, 200, 'use.how', errs, english=False)
    near = card['near']
    if not isinstance(near, list) or len(near) > 2:
        errs.append('near must list 0 to 2 idioms')
    else:
        for i, n in enumerate(near):
            if not isinstance(n, dict) or set(n) != {'t', 'diff'} or not isinstance(n['t'], str) or not n['t']:
                errs.append(f'near[{i}] must be {{t, diff}}')
                continue
            if n['t'] == idiom:
                errs.append(f'near[{i}] is the idiom itself')
            _text(n['diff'], 10, 200, f'near[{i}].diff', errs, english=False)
    parts = card['parts']
    if (not isinstance(parts, list) or len(parts) != 2
            or not all(isinstance(p, str) and p for p in parts) or ''.join(parts) != idiom):
        errs.append('parts must be two pieces that join to the idiom')
    if _text(card['cue'], 20, 200, 'cue', errs) and isinstance(card['mean'], str) \
            and card['mean'].lower() in card['cue'].lower():
        errs.append('cue must not contain the meaning line')
    ctx = card['ctx']
    if not isinstance(ctx, list) or len(ctx) != 6:
        errs.append('ctx must hold exactly 6 contexts')
    else:
        seen = set()
        for i, c in enumerate(ctx):
            if not isinstance(c, dict) or set(c) != {'s', 'en'}:
                errs.append(f'ctx[{i}] must be {{s, en}}')
                continue
            check_sentence(c['s'], lang, key, idiom, f'ctx[{i}]', errs)
            _text(c['en'], 8, 260, f'ctx[{i}].en', errs)
            if c['s'] in seen:
                errs.append(f'ctx[{i}] repeats a context')
            seen.add(c['s'])
    bad = card['bad']
    if not isinstance(bad, list) or len(bad) != 2:
        errs.append('bad must hold exactly 2 misuses')
    else:
        for i, b in enumerate(bad):
            if not isinstance(b, dict) or set(b) != {'s', 'en', 'why'}:
                errs.append(f'bad[{i}] must be {{s, en, why}}')
                continue
            check_sentence(b['s'], lang, key, idiom, f'bad[{i}]', errs)
            _text(b['en'], 5, 260, f'bad[{i}].en', errs)
            _text(b['why'], 15, 200, f'bad[{i}].why', errs)


def chunk_ids(lang, key, n):
    rows = load_list(lang, key)
    return [r['id'] for r in rows[(n - 1) * CHUNK:n * CHUNK]]


def validate_file(path, min_entries=None):
    """Problems of a list or cards file (strings)."""
    where = where_of(path)
    if not where:
        return ['path must be data/idioms/<lang>/lists/<set>.json or cards/<set>-NN.json']
    lang, kind, key, chunk = where
    _key, code, _title, _en, core = set_info(lang, key)
    try:
        rows = load_json(path)
    except (OSError, ValueError) as exc:
        return [f'cannot read: {exc}']
    if not isinstance(rows, list):
        return ['must be a JSON array']
    problems = []
    if kind == 'lists':
        seen_t, seen_id, seen_mean = set(), set(), set()
        for i, row in enumerate(rows):
            errs = []
            if check_list_entry(row, lang, code, errs):
                for field, seen in (('t', seen_t), ('id', seen_id), ('mean', seen_mean)):
                    if row[field] in seen:
                        errs.append(f'{field} listed twice')
                    seen.add(row[field])
            label = row.get('t') if isinstance(row, dict) else i
            problems += [f'[{i}] {label}: {e}' for e in errs]
        floor = core if min_entries is None else min_entries
        if len(rows) < floor:
            problems.append(f'{len(rows)} entries; at least {floor} wanted')
        most = FULL[(lang, key)] + 20
        if len(rows) > most:
            problems.append(f'{len(rows)} entries; at most {most}')
        return problems
    entries = {r['id']: r for r in load_list(lang, key) if isinstance(r, dict) and 'id' in r}
    want = chunk_ids(lang, key, chunk)
    got = [c.get('id') for c in rows if isinstance(c, dict)]
    if got != want:
        problems.append(f'cards must be exactly the list entries {want} in that order (got {got})')
    for i, card in enumerate(rows):
        errs = []
        check_card(card, lang, key, entries.get(card.get('id')) if isinstance(card, dict) else None, errs)
        label = card.get('t') if isinstance(card, dict) else i
        problems += [f'[{i}] {label}: {e}' for e in errs]
    return problems


# --------------------------------------------------------------------------- build
def card_files(lang, key):
    base = os.path.join(DATA, lang, 'cards')
    if not os.path.isdir(base):
        return []
    return sorted(os.path.join(base, n) for n in os.listdir(base) if re.match(rf'^{key}-\d\d\.json$', n))


def built_files(lang):
    """{relative name: text} of the static files for a language; cards that fail validation are left out."""
    out, idioms, sets, skipped = {}, [], [], 0
    taken = set()        # an expression listed in two sets is built once, in the earlier set
    for key, _code, title, en, _core in SETS[lang]:
        entries = load_list(lang, key)
        cards = {}
        for path in card_files(lang, key):
            if validate_file(path):
                skipped += 1
                continue
            for card in load_json(path):
                cards[card['id']] = card
        rows = [cards[e['id']] for e in entries if e['id'] in cards and cards[e['id']]['t'] not in taken]
        taken.update(c['t'] for c in rows)
        body = json.dumps({'set': key, 'cards': rows}, ensure_ascii=False, separators=(',', ':'))
        out[f'{key}.json'] = body
        sets.append({'key': key, 'title': title, 'en': en, 'count': len(rows),
                     'v': hashlib.sha1(body.encode('utf-8')).hexdigest()[:10]})
        # rank: place in the set's list (most useful first); the page starts new idioms by rank
        idioms += [{'id': c['id'], 't': c['t'], 'r': c['r'], 'mean': c['mean'], 'lvl': c['lvl'],
                    'tag': c['tag'], 'set': key, 'rank': n, 'parts': c['parts'], 'story': bool(c['story'])}
                   for n, c in enumerate(rows)]
    manifest = {'language': lang, 'language_id': LANGUAGE_IDS[lang], 'sets': sets,
                'total': len(idioms), 'idioms': idioms}
    out['manifest.json'] = json.dumps(manifest, ensure_ascii=False, separators=(',', ':'))
    return out, skipped


def cmd_build(check_only):
    stale = 0
    for lang in SETS:
        files, skipped = built_files(lang)
        base = os.path.join(STATIC, lang)
        for name, body in files.items():
            path = os.path.join(base, name)
            current = open(path, encoding='utf-8').read() if os.path.exists(path) else None
            if current != body:
                stale += 1
                if not check_only:
                    os.makedirs(base, exist_ok=True)
                    with open(path, 'w', encoding='utf-8') as fh:
                        fh.write(body)
        total = json.loads(files['manifest.json'])['total']
        print(f'{lang}: {total} idioms' + (f'; {skipped} card files left out (invalid)' if skipped else ''))
    if check_only:
        print('static files are up to date' if not stale else f'{stale} static files are out of date')
        return 1 if stale else 0
    print(f'wrote {stale} files' if stale else 'nothing to write')
    return 0


def cmd_stats():
    for lang in SETS:
        for key, _code, title, _en, core in SETS[lang]:
            entries = load_list(lang, key)
            cards = stories = 0
            for path in card_files(lang, key):
                if not validate_file(path):
                    rows = load_json(path)
                    cards += len(rows)
                    stories += sum(1 for c in rows if c['story'])
            print(f'{lang} {key:9s} {title}  list {len(entries):3d} / core {core} / full {FULL[(lang, key)]}'
                  f'  cards {cards:3d}  with a story {stories}')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    v = sub.add_parser('validate')
    v.add_argument('files', nargs='+')
    v.add_argument('--min-entries', type=int)
    b = sub.add_parser('build')
    b.add_argument('--check', action='store_true')
    sub.add_parser('stats')
    args = ap.parse_args(argv)
    if args.cmd == 'build':
        return cmd_build(args.check)
    if args.cmd == 'stats':
        return cmd_stats()
    total = 0
    for f in args.files:
        problems = validate_file(f, args.min_entries)
        total += len(problems)
        for p in problems[:80]:
            print(f'{os.path.relpath(f, REPO)}: {p}')
    print(f'{total} problems')
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main())
