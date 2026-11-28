"""Deterministic checks for particle-drill content (read-only).

    python scripts/particle_drill_validate.py                 # everything
    python scripts/particle_drill_validate.py items/ni-time.jsonl packs/ni-time.json
    python scripts/particle_drill_validate.py --summary       # counts per skill vs target

Paths are relative to data/particle_drill/ja/. Exit code 1 when any error is
found. The format is described in data/particle_drill/AUTHORING.md.
"""
import argparse
import itertools
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from services.particle_drill import markup  # noqa: E402

# PD_COURSE picks the course directory: 'ja' (particles, the default) or 'ja-grammar'.
COURSE = os.environ.get('PD_COURSE', 'ja')
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     '..', 'data', 'particle_drill', COURSE))
VERB_CLASSES = {'godan', 'ichidan', 'suru', 'kuru'}
ADJ_CLASSES = {'i', 'na'}
_ASCII_LETTER = re.compile(r'[A-Za-z]')
_JP_CHAR = re.compile(r'[぀-ヿ㐀-鿿]')


def load_catalog(root=ROOT):
    with open(os.path.join(root, 'catalog.json'), encoding='utf-8') as fh:
        return json.load(fh)


def skill_of(path):
    """items/ni-time.jsonl and the part file items/ni-time__2.jsonl -> ni-time."""
    return os.path.basename(path).rsplit('.', 1)[0].split('__')[0]


def check_item(item, file_skill, skills, *, pack_expansion=False):
    """Errors for one exercise item (dict)."""
    errs = []
    if not isinstance(item, dict):
        return ['not a JSON object']
    extra = set(item) - {'jp', 'en', 'f', 'd', 'why', 'lv'}
    if extra:
        errs.append(f'unknown fields {sorted(extra)}')
    jp, en = item.get('jp'), item.get('en')
    if not isinstance(jp, str) or not jp:
        return errs + ['jp missing']
    segments, slots, perrs = markup.parse(jp)
    errs += perrs
    if not slots:
        return errs + ['no {slot} in jp']
    text = markup.plain(jp)
    if re.search(r'[0-9０-９]', text):
        errs.append('digits: write numbers in kanji with a reading, or in kana')
    if re.search(r'[A-Za-z]', text):
        errs.append('latin letters in the Japanese sentence')
    if not (6 <= len(text) <= 70):
        errs.append(f'sentence length {len(text)} outside 6-70')
    if not pack_expansion and text[-1] not in '。？！?!':
        errs.append('sentence must end with 。？ or ！')
    if not isinstance(en, str) or not _ASCII_LETTER.search(en or ''):
        errs.append('en missing')
    elif _JP_CHAR.search(en):
        errs.append('en contains Japanese')
    f = item.get('f')
    if not isinstance(f, int) or isinstance(f, bool) or not (0 <= f < len(slots)):
        return errs + [f'f must index a slot (0..{len(slots) - 1})']
    for i, slot in enumerate(slots):
        if not slot['skill']:
            errs.append(f'slot {i} has no skill id')
        elif slot['skill'] not in skills:
            errs.append(f'slot {i}: unknown skill "{slot["skill"]}"')
    focus = slots[f]
    is_clinic = file_skill.startswith('x-')
    if file_skill and not is_clinic and focus['skill'] != file_skill:
        errs.append(f'focus slot skill "{focus["skill"]}" is not this file\'s skill "{file_skill}"')
    d = item.get('d')
    if not isinstance(d, list) or not all(isinstance(x, str) and x for x in d):
        errs.append('d must be a list of strings')
    else:
        need = 1 if is_clinic else 3
        if not (need <= len(d) <= 3):
            errs.append(f'd needs {need if need == 3 else "1-3"} distractors, got {len(d)}')
        if len(set(d)) != len(d):
            errs.append('repeated distractor')
        # Kanji areas of the grammar course: 'reading' shows the kanji and asks its
        # reading; 'kanji' shows the reading and asks the written form.
        ask = (skills.get(file_skill) or {}).get('ask') if isinstance(skills, dict) else None
        accepted = {focus['a'], *focus['alt'], *focus['kana']}
        if ask == 'kanji':
            accepted = {focus['a'], *focus['alt']}
        has_kanji = re.compile(r'[㐀-鿿々]')
        if ask and not has_kanji.search(focus['a']):
            errs.append('focus slot must be a word written with kanji')
        for x in d:
            if markup.strip_reading(x) in accepted or (ask != 'kanji' and markup.reading_of(x) in accepted):
                errs.append(f'distractor "{x}" is an accepted answer')
            errs += [f'distractor {e}' for e in markup.answer_errors(x)]
            if ask == 'reading' and not markup.is_kana(x):
                errs.append(f'distractor "{x}" must be a reading in kana')
            if ask == 'kanji':
                if not has_kanji.search(x):
                    errs.append(f'distractor "{x}" must be written with kanji')
                elif markup.reading_of(x) not in focus['kana']:
                    errs.append(f'distractor "{x}" must carry the answer\'s reading')
        if len({markup.strip_reading(x) for x in d}) != len(d) and len(set(d)) == len(d):
            errs.append('repeated distractor')
    why = item.get('why')
    if not isinstance(why, str) or not (15 <= len(why) <= 200):
        errs.append('why must be 15-200 characters')
    lv = item.get('lv')
    if lv not in (1, 2, 3, 4, 5):
        errs.append('lv must be 1-5')
    return errs


def check_items_file(path, skills):
    file_skill = skill_of(path)
    errs, seen, count = [], {}, 0
    if file_skill not in skills:
        errs.append(f'{path}: file name is not a catalog skill id')
    with open(path, encoding='utf-8') as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except ValueError as exc:
                errs.append(f'{path}:{n}: invalid JSON ({exc})')
                continue
            count += 1
            for e in check_item(item, file_skill, skills):
                errs.append(f'{path}:{n}: {e}')
            if isinstance(item, dict) and isinstance(item.get('jp'), str):
                key = markup.plain(item['jp'])
                if key in seen:
                    errs.append(f'{path}:{n}: duplicate of line {seen[key]}')
                seen.setdefault(key, n)
    return errs, count


def pack_combinations(pack):
    names = list(pack['vars'])
    return names, itertools.product(*(range(len(pack['vars'][n])) for n in names))


def expand_pack(pack, choice):
    """One concrete item from a pack. ``choice`` maps var name -> value index."""
    jp_vals = {n: pack['vars'][n][i][0] for n, i in choice.items()}
    en_vals = {n: pack['vars'][n][i][1] for n, i in choice.items()}
    return {'jp': markup.expand(pack['tpl'], jp_vals), 'en': markup.expand(pack['en'], en_vals),
            'f': pack['f'], 'd': pack['d'], 'why': pack['why'], 'lv': pack['lv']}


def check_packs_file(path, skills):
    file_skill = skill_of(path)
    errs = []
    try:
        with open(path, encoding='utf-8') as fh:
            packs = json.load(fh)
    except ValueError as exc:
        return [f'{path}: invalid JSON ({exc})'], 0
    if not isinstance(packs, list):
        return [f'{path}: must be a JSON array of packs'], 0
    ids = set()
    for k, pack in enumerate(packs):
        where = f'{path}[{k}]'
        if not isinstance(pack, dict):
            errs.append(f'{where}: not an object')
            continue
        missing = {'id', 'tpl', 'en', 'f', 'd', 'why', 'lv', 'vars'} - set(pack)
        if missing:
            errs.append(f'{where}: missing {sorted(missing)}')
            continue
        if pack['id'] in ids:
            errs.append(f'{where}: duplicate id {pack["id"]}')
        ids.add(pack['id'])
        vars_ = pack['vars']
        if not isinstance(vars_, dict) or not vars_:
            errs.append(f'{where}: vars must be a non-empty object')
            continue
        bad = False
        for name, values in vars_.items():
            if f'<{name}>' not in pack['tpl']:
                errs.append(f'{where}: var <{name}> not used in tpl')
            if f'<{name}>' not in pack['en']:
                errs.append(f'{where}: var <{name}> not used in en')
            if (not isinstance(values, list) or len(values) < 4 or not all(
                    isinstance(v, list) and len(v) == 2 and all(isinstance(x, str) and x for x in v)
                    for v in values)):
                errs.append(f'{where}: var {name} needs at least 4 [japanese, english] pairs')
                bad = True
            elif len({v[0] for v in values}) != len(values):
                errs.append(f'{where}: var {name} repeats a value')
        for name in re.findall(r'<([a-z][a-z0-9_]*)>', pack['tpl'] + pack['en']):
            if name not in vars_:
                errs.append(f'{where}: <{name}> has no values')
                bad = True
        if bad:
            continue
        names, combos = pack_combinations(pack)
        total = 1
        for n in names:
            total *= len(vars_[n])
        if total < 100:
            errs.append(f'{where}: only {total} combinations (need 100+)')
        # Every value is exercised at least once: check each var's values against
        # the first value of the others, plus the diagonal.
        choices = []
        for n in names:
            for i in range(len(vars_[n])):
                choices.append({m: (i if m == n else 0) for m in names})
        for i in range(max(len(vars_[n]) for n in names)):
            choices.append({n: i % len(vars_[n]) for n in names})
        reported = set()
        for choice in choices:
            for e in check_item(expand_pack(pack, choice), file_skill, skills):
                if e not in reported:
                    reported.add(e)
                    errs.append(f'{where} ({pack["id"]}): {e}')
    return errs, len(packs)


def print_expansions(path, limit=36):
    """Sample sentences of every pack: each value of each variable at least three times."""
    with open(path, encoding='utf-8') as fh:
        packs = json.load(fh)
    for pack in packs:
        names, combos = pack_combinations(pack)
        combos = list(combos)
        step = max(1, len(combos) // limit)
        # A stride that is coprime with the value counts walks every value of every variable.
        while any(step % len(pack['vars'][n]) == 0 for n in names if len(pack['vars'][n]) > 1) and step > 1:
            step += 1
        print(f"== {pack['id']}  ({len(combos)} combinations)  f={pack['f']}  d={pack['d']}")
        for combo in combos[::step][:limit + 12]:
            item = expand_pack(pack, dict(zip(names, combo)))
            _, slots, _ = markup.parse(item['jp'])
            focus = slots[item['f']]['a'] if 0 <= item['f'] < len(slots) else '?'
            print(f"  {markup.plain(item['jp'])}  [{focus}]  {item['en']}")
    return 0


def _check_example(jp, where, errs):
    _, slots, perrs = markup.parse(jp)
    errs += [f'{where}: {e}' for e in perrs]
    return slots


def check_guide_file(path, catalog):
    groups = {g['id']: g for st in catalog['stages'] for g in st['groups']}
    gid = os.path.basename(path)[:-len('.json')]
    errs = []
    try:
        with open(path, encoding='utf-8') as fh:
            guide = json.load(fh)
    except ValueError as exc:
        return [f'{path}: invalid JSON ({exc})']
    if gid not in groups:
        return [f'{path}: file name is not a catalog group id']
    if not isinstance(guide.get('intro'), str) or len(guide['intro']) < 60:
        errs.append(f'{path}: intro missing or under 60 characters')
    got = guide.get('skills')
    if not isinstance(got, list):
        return errs + [f'{path}: skills must be a list']
    want = groups[gid]['skills']
    if [s.get('id') for s in got if isinstance(s, dict)] != want:
        errs.append(f'{path}: skills must be exactly {want} in this order')
    for s in got:
        if not isinstance(s, dict):
            continue
        where = f'{path}:{s.get("id")}'
        for key, lo in (('rule', 20), ('explain', 200), ('tip', 15)):
            if not isinstance(s.get(key), str) or len(s[key]) < lo:
                errs.append(f'{where}: {key} missing or under {lo} characters')
        pats = s.get('patterns')
        if not isinstance(pats, list) or not pats or not all(isinstance(p, str) and p for p in pats):
            errs.append(f'{where}: patterns must be a non-empty list of strings')
        ex = s.get('examples')
        if not isinstance(ex, list) or len(ex) < 4:
            errs.append(f'{where}: needs at least 4 examples')
        else:
            for i, e in enumerate(ex):
                if not isinstance(e, dict) or not e.get('jp') or not e.get('en'):
                    errs.append(f'{where}: example {i} needs jp and en')
                    continue
                if not _check_example(e['jp'], f'{where} example {i}', errs):
                    errs.append(f'{where}: example {i} marks no {{particle}}')
        for i, c in enumerate(s.get('contrast') or []):
            if not isinstance(c, dict) or not c.get('vs') or not c.get('note'):
                errs.append(f'{where}: contrast {i} needs vs and note')
        for i, m in enumerate(s.get('mistakes') or []):
            if not isinstance(m, dict) or not m.get('bad') or not m.get('good') or not m.get('note'):
                errs.append(f'{where}: mistake {i} needs bad, good and note')
                continue
            _check_example(m['bad'], f'{where} mistake {i} bad', errs)
            _check_example(m['good'], f'{where} mistake {i} good', errs)
    return errs


def check_katakana_file(path):
    """reading/katakana.json: loanwords for the speed-reading drill."""
    errs = []
    try:
        with open(path, encoding='utf-8') as fh:
            rows = json.load(fh)
    except ValueError as exc:
        return [f'{path}: invalid JSON ({exc})'], 0
    if not isinstance(rows, list):
        return [f'{path}: must be a JSON array'], 0
    seen = set()
    for i, r in enumerate(rows):
        where = f'{path}[{i}]'
        if not isinstance(r, dict) or not isinstance(r.get('k'), str) or not isinstance(r.get('en'), str):
            errs.append(f'{where}: needs k and en')
            continue
        if not re.match(r'^[ァ-ヺー]{2,9}$', r['k']):
            errs.append(f'{where}: k must be 2-9 katakana')
        if not _ASCII_LETTER.search(r['en']):
            errs.append(f'{where}: en missing')
        if r.get('lv') not in (1, 2, 3, 4, 5):
            errs.append(f'{where}: lv must be 1-5')
        if r['k'] in seen:
            errs.append(f'{where}: duplicate {r["k"]}')
        seen.add(r['k'])
    return errs, len(rows)


def check_lexicon_file(path):
    name = os.path.basename(path)
    errs = []
    try:
        with open(path, encoding='utf-8') as fh:
            rows = json.load(fh)
    except ValueError as exc:
        return [f'{path}: invalid JSON ({exc})'], 0
    classes = VERB_CLASSES if name.startswith('verbs') else ADJ_CLASSES
    seen = set()
    for i, r in enumerate(rows if isinstance(rows, list) else []):
        where = f'{path}[{i}]'
        if not isinstance(r, dict) or not all(isinstance(r.get(k), str) and r[k] for k in ('d', 'k', 'c', 'en')):
            errs.append(f'{where}: needs d, k, c, en')
            continue
        if r['c'] not in classes:
            errs.append(f'{where}: class {r["c"]} not in {sorted(classes)}')
        if not re.match(r'^[ぁ-ゖー]+$', r['k']):
            errs.append(f'{where}: k must be hiragana')
        if r.get('lv') not in (1, 2, 3, 4, 5):
            errs.append(f'{where}: lv must be 1-5')
        if (r['d'], r['k']) in seen:
            errs.append(f'{where}: duplicate {r["d"]}')
        seen.add((r['d'], r['k']))
        d, k, c = r['d'], r['k'], r['c']
        if name.startswith('verbs'):
            if r.get('t') not in ('t', 'i'):
                errs.append(f'{where}: t must be "t" (transitive) or "i" (intransitive)')
            if d[-1] != k[-1]:
                errs.append(f'{where}: d and k must end with the same kana')
            if c == 'ichidan' and not (k.endswith('る') and len(k) > 1 and k[-2] in 'いきしちにひみりぎじびぴえけせてねへめれげぜでべぺ'):
                errs.append(f'{where}: ichidan verb must end in -iru / -eru')
            if c == 'godan' and k[-1] not in 'うくぐすつぬぶむる':
                errs.append(f'{where}: godan verb must end in an u-row kana')
            if c == 'suru' and not k.endswith('する'):
                errs.append(f'{where}: suru verb must end in する')
            if c == 'kuru' and not k.endswith('くる'):
                errs.append(f'{where}: kuru verb must end in くる')
        else:
            if c == 'i' and not (d.endswith('い') and k.endswith('い')):
                errs.append(f'{where}: i-adjective must end in い')
            if c == 'na' and (d.endswith('な') or d.endswith('だ')):
                errs.append(f'{where}: na-adjective is listed without な / だ')
    return errs, len(rows) if isinstance(rows, list) else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('paths', nargs='*', help='files relative to data/particle_drill/ja (default: all)')
    ap.add_argument('--summary', action='store_true', help='print item counts per skill against the target')
    ap.add_argument('--expand', metavar='PACK_FILE', help='print sample sentences of every pack in a file')
    ap.add_argument('--root', default=ROOT)
    args = ap.parse_args()
    if args.expand:
        return print_expansions(args.expand if os.path.isabs(args.expand) else os.path.join(args.root, args.expand))
    catalog = load_catalog(args.root)
    skills = {s['id']: s for s in catalog['skills']}
    paths = [p if os.path.isabs(p) else os.path.join(args.root, p) for p in args.paths]
    if not paths:
        for sub in ('items', 'packs', 'guides', 'conjugation', 'reading'):
            d = os.path.join(args.root, sub)
            if os.path.isdir(d):
                paths += sorted(os.path.join(d, f) for f in os.listdir(d)
                                if f.endswith('.json') or f.endswith('.jsonl'))
    all_errs, counts, packs = [], {}, 0
    for path in paths:
        if not os.path.exists(path):
            all_errs.append(f'{path}: file not found')
            continue
        kind = os.path.basename(os.path.dirname(path))
        if kind == 'items':
            errs, n = check_items_file(path, skills)
            counts[skill_of(path)] = counts.get(skill_of(path), 0) + n
        elif kind == 'packs':
            errs, n = check_packs_file(path, skills)
            packs += n
        elif kind == 'guides':
            errs = check_guide_file(path, catalog)
        elif kind == 'reading':
            errs = check_katakana_file(path)[0]
        elif kind == 'conjugation':
            errs = [] if os.path.basename(path).startswith('guide') else check_lexicon_file(path)[0]
        else:
            errs = [f'{path}: unknown content directory "{kind}"']
        all_errs += errs
    for e in all_errs[:400]:
        print(os.path.relpath(e, args.root) if e.startswith(args.root) else e)
    if len(all_errs) > 400:
        print(f'... and {len(all_errs) - 400} more')
    if args.summary:
        short = [(s['id'], counts.get(s['id'], 0), s['n']) for s in catalog['skills']
                 if counts.get(s['id'], 0) < s['n']]
        print(f'items {sum(counts.values())} in {len(counts)} files; pattern packs {packs}; '
              f'skills under target {len(short)}')
        for sid, have, want in short:
            print(f'  {sid}: {have}/{want}')
    print(f'{len(paths)} files checked, {len(all_errs)} errors')
    return 1 if all_errs else 0


if __name__ == '__main__':
    sys.exit(main())
