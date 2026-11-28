"""Chinese grammar drills: validate authored items and guides, support blind
review, and build the static files the /grammar-drill page loads.

Content lives in data/grammar_drills/<lang>/ (plan.json, guides/, batches/,
reviewed/); the contract is data/grammar_drills/zh/SPEC.md. Nothing here reads
or writes the database: every command works on local files only.

  python scripts/grammar_drills.py validate FILE.jsonl      # one batch
  python scripts/grammar_drills.py validate-guide FILE.json
  python scripts/grammar_drills.py strip FILE.jsonl         # -> blind/NAME.blind.jsonl
  python scripts/grammar_drills.py compare FILE.jsonl       # blind answers vs keys
  python scripts/grammar_drills.py build                    # -> static/data/grammar/zh/
  python scripts/grammar_drills.py clean                    # mechanical fixes to reviewed/
  python scripts/grammar_drills.py stats
"""

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANG = 'zh'
DATA = os.path.join(ROOT, 'data', 'grammar_drills', LANG)
OUT = os.path.join(ROOT, 'static', 'data', 'grammar', LANG)

BLANK = '___'
EMPTY = '∅'  # an option part meaning "nothing goes in this blank"
TYPES = ('cloze', 'order', 'rewrite', 'judge')
PUNCT = '，。？！、；：“”‘’（）《》…—,.?!;:'
HANZI = re.compile(r'[一-鿿]')
TONE_MARKS = 'āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜńňǹḿ'
MIX_TOLERANCE = 8
ID_RE = re.compile(r'^[a-z-]+-\d{2}-\d{3}$')


# --------------------------------------------------------------------------
# helpers

def load_plan():
    with open(os.path.join(DATA, 'plan.json'), encoding='utf-8') as fh:
        return json.load(fh)


def topic_of(plan, slug):
    for t in plan['topics']:
        if t['slug'] == slug:
            return t
    return None


def guide_path(slug):
    return os.path.join(DATA, 'guides', slug + '.json')


def load_guide(slug):
    path = guide_path(slug)
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def read_jsonl(path):
    """[(line_no, obj | None, error | None)]"""
    rows = []
    with open(path, encoding='utf-8') as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append((n, json.loads(line), None))
            except json.JSONDecodeError as exc:
                rows.append((n, None, f'not JSON: {exc}'))
    return rows


def strip_punct(s):
    return ''.join(ch for ch in s if ch not in PUNCT and not ch.isspace())


def strip_tone(syl):
    out = unicodedata.normalize('NFD', syl)
    out = ''.join(ch for ch in out if unicodedata.category(ch) != 'Mn' or ch == '̈')
    return unicodedata.normalize('NFC', out).replace('ü', 'v').lower()


_readings_cache = {}


def readings(ch):
    if ch not in _readings_cache:
        from pypinyin import pinyin, Style
        got = pinyin(ch, style=Style.TONE, heteronym=True)[0]
        _readings_cache[ch] = set(got)
    return _readings_cache[ch]


_t2s = None


def to_simplified(s):
    global _t2s
    if _t2s is None:
        import opencc
        _t2s = opencc.OpenCC('t2s')
    return _t2s.convert(s)


# Characters OpenCC maps although they are standard simplified in the sense used.
T2S_KEEP = set('着乾借瞭麽么于徵')


def check_zh(text, label, errs):
    if not text or not isinstance(text, str):
        errs.append(f'{label}: missing')
        return
    if re.search(r'[A-Za-z0-9]', text):
        errs.append(f'{label}: Latin letters or digits are not allowed (write numbers in Hanzi)')
    if re.search(r'[,?!;:]', text):
        errs.append(f'{label}: use full-width Chinese punctuation (，。？！；：), not ASCII')
    conv = to_simplified(text)
    bad = [a for a, b in zip(text, conv) if a != b and a not in T2S_KEEP]
    if bad:
        errs.append(f'{label}: traditional characters {"".join(bad)}')


def check_py(zh, py, label, errs):
    """One syllable per Hanzi, space separated, each a real reading of its character."""
    if not isinstance(py, str) or not py.strip():
        errs.append(f'{label}: missing')
        return
    chars = HANZI.findall(zh or '')
    syls = [s for s in re.split(r'[\s' + re.escape(PUNCT) + r']+', py.strip()) if s]
    if len(syls) != len(chars):
        errs.append(f'{label}: {len(syls)} syllables for {len(chars)} characters '
                    '(one syllable per character, separated by spaces)')
        return
    for i, (ch, syl) in enumerate(zip(chars, syls)):
        low = syl.lower()
        if ch == '儿':
            # A full syllable in 儿子 / 女儿 / 儿童; the suffix r elsewhere.
            full = (i + 1 < len(chars) and chars[i + 1] in '子童女科歌') or (i > 0 and chars[i - 1] in '女幼婴少')
            if full and low == 'r':
                errs.append(f'{label}: 儿 is a full syllable here (ér), not the suffix r')
            if low in ('r', 'ér', 'er'):
                continue
        known = readings(ch)
        if low in known:
            continue
        bases = {strip_tone(r) for r in known}
        has_mark = any(c in TONE_MARKS for c in low)
        if strip_tone(low) in bases and not has_mark:
            continue  # neutral tone
        if ch in '不一' and strip_tone(low) in bases:
            continue  # tone change written out
        errs.append(f'{label}: "{syl}" is not a reading of {ch} (known: {", ".join(sorted(known))})')


def fill(q, opt):
    parts = opt.split('|')
    if q.count(BLANK) != len(parts):
        return None
    out = q
    for p in parts:
        out = out.replace(BLANK, '' if p == EMPTY else p, 1)
    return out


def dedup_key(it):
    t = it.get('type')
    if t == 'cloze':
        return ('cloze', it.get('q'), it.get('zh'))
    if t == 'judge':
        return ('judge', it.get('s'))
    return (t, it.get('zh'), it.get('src'))


# --------------------------------------------------------------------------
# item validation

def validate_item(it, subs, topic_slug):
    errs = []
    if not isinstance(it, dict):
        return ['not an object']
    iid = it.get('id')
    if not isinstance(iid, str) or not ID_RE.match(iid):
        errs.append('id: must look like <topic>-<batch 2 digits>-<item 3 digits>')
    elif topic_slug and not iid.startswith(topic_slug + '-'):
        errs.append(f'id: must start with {topic_slug}-')
    typ = it.get('type')
    if typ not in TYPES:
        return errs + [f'type: must be one of {", ".join(TYPES)}']
    if subs is not None and it.get('sub') not in subs:
        errs.append(f'sub: "{it.get("sub")}" is not a sub-point key of this topic ({", ".join(subs)})')
    if it.get('lvl') not in (1, 2, 3):
        errs.append('lvl: must be 1, 2 or 3')
    zh = it.get('zh')
    check_zh(zh, 'zh', errs)
    if isinstance(zh, str):
        n = len(HANZI.findall(zh))
        if n < 3 or n > 34:
            errs.append(f'zh: {n} characters (3 to 34 allowed)')
        check_py(zh, it.get('py'), 'py', errs)
    en = it.get('en')
    if not isinstance(en, str) or len(en.strip()) < 3:
        errs.append('en: missing')
    why = it.get('why')
    if not isinstance(why, str) or not (15 <= len(why) <= 260):
        errs.append('why: 15 to 260 characters of English explanation')

    allowed = {'id', 'type', 'sub', 'lvl', 'zh', 'py', 'en', 'why'}
    if typ == 'cloze':
        allowed |= {'q', 'opts', 'a'}
        q, opts, a = it.get('q'), it.get('opts'), it.get('a')
        if not isinstance(q, str) or BLANK not in q:
            errs.append(f'q: must contain at least one blank written {BLANK}')
        elif q.count(BLANK) > 2:
            errs.append('q: at most two blanks')
        if (not isinstance(opts, list) or not (2 <= len(opts) <= 4)
                or not all(isinstance(o, str) and o for o in opts)):
            errs.append('opts: 2 to 4 non-empty strings')
        elif len(set(opts)) != len(opts):
            errs.append('opts: duplicates')
        elif not isinstance(a, int) or isinstance(a, bool) or not (0 <= a < len(opts)):
            errs.append('a: index of the correct option')
        elif isinstance(q, str) and isinstance(zh, str):
            for o in opts:
                if fill(q, o) is None:
                    errs.append(f'opts: "{o}" has the wrong number of parts for the blanks '
                                f'(separate parts with |, use {EMPTY} for "nothing")')
                    break
                for part in o.split('|'):
                    if part != EMPTY:
                        check_zh(part, 'opts', errs)
            else:
                if fill(q, opts[a]) != zh:
                    errs.append('zh: must equal q with the correct option filled in')
                fills = [fill(q, o) for o in opts]
                if len(set(fills)) != len(fills):
                    errs.append('opts: two options produce the same sentence')
    elif typ in ('order', 'rewrite'):
        allowed |= {'tokens', 'alts', 'extra'}
        tokens = it.get('tokens')
        if (not isinstance(tokens, list) or not (3 <= len(tokens) <= 10)
                or not all(isinstance(t, str) and t for t in tokens)):
            errs.append('tokens: 3 to 10 non-empty strings')
        elif isinstance(zh, str):
            if any(ch in PUNCT for t in tokens for ch in t):
                errs.append('tokens: no punctuation inside tokens')
            if ''.join(tokens) != strip_punct(zh):
                errs.append('tokens: joined in order they must equal zh without punctuation')
            alts = it.get('alts', [])
            if not isinstance(alts, list):
                errs.append('alts: a list of token lists')
            else:
                for alt in alts:
                    if not isinstance(alt, list) or sorted(alt) != sorted(tokens):
                        errs.append('alts: each must be a reordering of exactly the same tokens')
                        break
                    if alt == tokens:
                        errs.append('alts: repeats the main order')
                        break
            extra = it.get('extra', [])
            if not isinstance(extra, list) or len(extra) > 2 or not all(isinstance(e, str) and e for e in extra):
                errs.append('extra: at most 2 distractor tiles')
            elif set(extra) & set(tokens):
                errs.append('extra: a distractor tile equals a real token')
        if typ == 'rewrite':
            allowed |= {'src', 'src_py', 'task'}
            src = it.get('src')
            check_zh(src, 'src', errs)
            if isinstance(src, str):
                check_py(src, it.get('src_py'), 'src_py', errs)
                if isinstance(zh, str) and strip_punct(src) == strip_punct(zh):
                    errs.append('src: identical to the answer')
            task = it.get('task')
            if not isinstance(task, str) or not (5 <= len(task) <= 80):
                errs.append('task: 5 to 80 characters of English instruction')
    elif typ == 'judge':
        allowed |= {'s', 'ok', 's_py'}
        s, ok = it.get('s'), it.get('ok')
        check_zh(s, 's', errs)
        if not isinstance(ok, bool):
            errs.append('ok: true or false')
        elif isinstance(s, str) and isinstance(zh, str):
            if ok and s != zh:
                errs.append('s: when ok is true, s must equal zh')
            if not ok:
                if strip_punct(s) == strip_punct(zh):
                    errs.append('zh: when ok is false, zh is the corrected sentence and must differ from s')
                check_py(s, it.get('s_py'), 's_py', errs)
    extra_keys = set(it) - allowed
    if extra_keys:
        errs.append('unknown fields: ' + ', '.join(sorted(extra_keys)))
    return errs


def batch_topic(path, plan):
    name = os.path.basename(path)
    m = re.match(r'^([a-z-]+)-(\d{2})\.jsonl$', name)
    if not m or not topic_of(plan, m.group(1)):
        return None, None
    return m.group(1), m.group(2)


def validate_file(path, plan, quiet=False, min_items=None):
    slug, batch_no = batch_topic(path, plan)
    problems = []
    if not slug:
        problems.append('file name must be <topic-slug>-<NN>.jsonl with a topic from plan.json')
    topic = topic_of(plan, slug) if slug else None
    guide = load_guide(slug) if slug else None
    subs = [s['key'] for s in guide.get('subs', [])] if guide else None
    if slug and subs is None:
        problems.append(f'guide for {slug} not found at {guide_path(slug)}')
    rows = read_jsonl(path)
    seen_ids, seen_keys = {}, {}
    items = []
    for n, obj, err in rows:
        if err:
            problems.append(f'line {n}: {err}')
            continue
        errs = validate_item(obj, subs, slug)
        iid = obj.get('id', '?') if isinstance(obj, dict) else '?'
        if isinstance(obj, dict):
            if batch_no and isinstance(iid, str) and ID_RE.match(iid) and iid.split('-')[-2] != batch_no:
                errs.append(f'id: batch part must be {batch_no}')
            if iid in seen_ids:
                errs.append(f'id: duplicate of line {seen_ids[iid]}')
            seen_ids.setdefault(iid, n)
            key = dedup_key(obj)
            if key in seen_keys:
                errs.append(f'duplicate content of line {seen_keys[key]}')
            seen_keys.setdefault(key, n)
            items.append(obj)
        for e in errs:
            problems.append(f'line {n} ({iid}): {e}')
    size = plan['batch_size']
    floor = min_items if min_items is not None else size
    if len(items) < floor:
        problems.append(f'{len(items)} items; at least {floor} required')
    if len(items) > size + 10:
        problems.append(f'{len(items)} items; at most {size + 10}')
    if topic and items:
        counts = Counter(i.get('type') for i in items)
        scale = len(items) / size
        for typ, target in topic['mix'].items():
            got = counts.get(typ, 0)
            if abs(got - target * scale) > MIX_TOLERANCE:
                problems.append(f'type mix: {got} {typ} items, target {round(target * scale)} '
                                f'(±{MIX_TOLERANCE})')
        lv = Counter(i.get('lvl') for i in items)
        if lv.get(1, 0) < 0.25 * len(items) or lv.get(3, 0) < 0.1 * len(items):
            problems.append(f'level mix: lvl1={lv.get(1, 0)} lvl2={lv.get(2, 0)} lvl3={lv.get(3, 0)}; '
                            'need at least 25% level 1 and 10% level 3')
        if subs:
            sc = Counter(i.get('sub') for i in items)
            missing = [s for s in subs if sc.get(s, 0) == 0]
            if len(missing) > len(subs) // 2:
                problems.append('sub-points: more than half are unused: ' + ', '.join(missing))
        judges = [i for i in items if i.get('type') == 'judge']
        if len(judges) >= 6:
            oks = sum(1 for i in judges if i.get('ok') is True)
            if not (0.3 <= oks / len(judges) <= 0.6):
                problems.append(f'judge items: {oks} of {len(judges)} are correct sentences; keep 30-60%')
        clozes = [i for i in items if i.get('type') == 'cloze' and isinstance(i.get('a'), int)]
        if len(clozes) >= 20:
            pos = Counter(i['a'] for i in clozes)
            if pos.most_common(1)[0][1] > 0.5 * len(clozes):
                problems.append('cloze: the correct option sits at the same index in over half the '
                                'items; spread the answer position')
    if not quiet:
        if problems:
            print(f'{path}: {len(problems)} problem(s), {len(items)} items')
            for p in problems:
                print('  ' + p)
        else:
            print(f'{path}: OK, {len(items)} items')
    return items, problems


# --------------------------------------------------------------------------
# guide validation

def validate_guide(path, plan, quiet=False):
    problems = []
    slug = os.path.basename(path)[:-5]
    topic = topic_of(plan, slug)
    if not topic:
        problems.append('file name must be <topic-slug>.json with a topic from plan.json')
    try:
        with open(path, encoding='utf-8') as fh:
            g = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f'{path}: {exc}')
        return None, [str(exc)]

    def text(obj, key, lo, hi, label):
        v = obj.get(key) if isinstance(obj, dict) else None
        if not isinstance(v, str) or not (lo <= len(v) <= hi):
            problems.append(f'{label}.{key}: {lo} to {hi} characters')

    def example(ex, label, need_en=True):
        if not isinstance(ex, dict):
            problems.append(f'{label}: must be an object')
            return
        errs = []
        check_zh(ex.get('zh'), 'zh', errs)
        if isinstance(ex.get('zh'), str):
            check_py(ex['zh'], ex.get('py'), 'py', errs)
        if need_en and (not isinstance(ex.get('en'), str) or len(ex['en']) < 2):
            errs.append('en: missing')
        problems.extend(f'{label}: {e}' for e in errs)

    if g.get('topic') != slug:
        problems.append(f'topic: must be "{slug}"')
    text(g, 'summary', 60, 420, 'guide')
    subs = g.get('subs')
    if not isinstance(subs, list) or not (3 <= len(subs) <= 10):
        problems.append('subs: 3 to 10 sub-points')
        subs = []
    keys = []
    for i, s in enumerate(subs):
        if not isinstance(s, dict) or not re.match(r'^[a-z0-9-]{2,30}$', str(s.get('key', ''))):
            problems.append(f'subs[{i}].key: lowercase letters, digits and hyphens')
            continue
        keys.append(s['key'])
        text(s, 'label', 3, 60, f'subs[{i}]')
        text(s, 'focus', 20, 300, f'subs[{i}]')
    if len(set(keys)) != len(keys):
        problems.append('subs: duplicate keys')
    rules = g.get('rules')
    if not isinstance(rules, list) or not (3 <= len(rules) <= 12):
        problems.append('rules: 3 to 12 rules')
        rules = []
    for i, r in enumerate(rules):
        if not isinstance(r, dict):
            problems.append(f'rules[{i}]: must be an object')
            continue
        text(r, 'rule', 10, 220, f'rules[{i}]')
        text(r, 'pattern', 2, 90, f'rules[{i}]')
        if r.get('sub') not in keys:
            problems.append(f'rules[{i}].sub: must be one of the sub-point keys')
        if 'note' in r:
            text(r, 'note', 5, 300, f'rules[{i}]')
        exs = r.get('examples')
        if not isinstance(exs, list) or not (2 <= len(exs) <= 4):
            problems.append(f'rules[{i}].examples: 2 to 4 examples')
            exs = []
        for j, ex in enumerate(exs):
            example(ex, f'rules[{i}].examples[{j}]')
    contrasts = g.get('contrasts')
    if not isinstance(contrasts, list) or not (3 <= len(contrasts) <= 10):
        problems.append('contrasts: 3 to 10 wrong/right pairs')
        contrasts = []
    for i, c in enumerate(contrasts):
        if not isinstance(c, dict):
            problems.append(f'contrasts[{i}]: must be an object')
            continue
        errs = []
        check_zh(c.get('wrong'), 'wrong', errs)
        problems.extend(f'contrasts[{i}]: {e}' for e in errs)
        example(c.get('right'), f'contrasts[{i}].right')
        text(c, 'why', 10, 240, f'contrasts[{i}]')
    cheat = g.get('cheat')
    if (not isinstance(cheat, list) or not (3 <= len(cheat) <= 7)
            or not all(isinstance(c, str) and 5 <= len(c) <= 140 for c in cheat)):
        problems.append('cheat: 3 to 7 one-line reflex rules of 5 to 140 characters')
    unknown = set(g) - {'topic', 'summary', 'subs', 'rules', 'contrasts', 'cheat'}
    if unknown:
        problems.append('unknown fields: ' + ', '.join(sorted(unknown)))
    if not quiet:
        if problems:
            print(f'{path}: {len(problems)} problem(s)')
            for p in problems:
                print('  ' + p)
        else:
            print(f'{path}: OK')
    return g, problems


# --------------------------------------------------------------------------
# blind review

def blind_paths(batch_path):
    name = os.path.basename(batch_path)[:-6]
    base = os.path.join(DATA, 'blind')
    return os.path.join(base, name + '.blind.jsonl'), os.path.join(base, name + '.answers.jsonl')


def cmd_strip(path):
    rows = [obj for _, obj, err in read_jsonl(path) if not err and isinstance(obj, dict)]
    blind, answers = blind_paths(path)
    os.makedirs(os.path.dirname(blind), exist_ok=True)
    with open(blind, 'w', encoding='utf-8') as fh:
        for it in rows:
            t = it.get('type')
            if t == 'cloze':
                out = {'id': it['id'], 'type': t, 'q': it.get('q'), 'opts': it.get('opts'), 'en': it.get('en')}
            elif t in ('order', 'rewrite'):
                # Tiles in a fixed order unrelated to the answer.
                tiles = sorted((it.get('tokens') or []) + (it.get('extra') or []),
                               key=lambda s: hashlib.md5((it['id'] + s).encode()).hexdigest())
                out = {'id': it['id'], 'type': t, 'tiles': tiles, 'en': it.get('en')}
                if t == 'rewrite':
                    out['src'] = it.get('src')
                    out['task'] = it.get('task')
            else:
                out = {'id': it['id'], 'type': t, 's': it.get('s')}
            fh.write(json.dumps(out, ensure_ascii=False) + '\n')
    print(f'wrote {blind} ({len(rows)} items)')
    print(f'write your answers to {answers}')
    return 0


def cmd_compare(path):
    blind, answers = blind_paths(path)
    if not os.path.exists(answers):
        print(f'no answers file at {answers}')
        return 2
    items = {o['id']: o for _, o, e in read_jsonl(path) if not e and isinstance(o, dict) and 'id' in o}
    got = {o.get('id'): o for _, o, e in read_jsonl(answers) if not e and isinstance(o, dict)}
    flags = []
    for iid, it in items.items():
        ans = got.get(iid)
        if ans is None:
            flags.append((iid, 'no blind answer'))
            continue
        t = it.get('type')
        if t == 'cloze':
            ok = ans.get('ok')
            if not isinstance(ok, list):
                flags.append((iid, 'blind answer has no "ok" list'))
            elif it.get('a') not in ok:
                flags.append((iid, f'KEY REJECTED: key={it["opts"][it["a"]]!r}, solver accepted '
                                   f'{[it["opts"][i] for i in ok if isinstance(i, int) and 0 <= i < len(it["opts"])]}'))
            elif len(ok) > 1:
                flags.append((iid, f'AMBIGUOUS: solver also accepted '
                                   f'{[it["opts"][i] for i in ok if i != it["a"] and 0 <= i < len(it["opts"])]}'))
        elif t in ('order', 'rewrite'):
            built = strip_punct(str(ans.get('zh', '')))
            accepted = {''.join(it.get('tokens') or [])} | {''.join(a) for a in it.get('alts', [])}
            if built not in accepted:
                flags.append((iid, f'DIFFERENT ORDER: solver built {ans.get("zh")!r}; key {it.get("zh")!r} '
                                   '(add it to alts if it is also correct, otherwise fix the item)'))
        elif t == 'judge':
            if ans.get('ok') is not it.get('ok'):
                flags.append((iid, f'JUDGEMENT DIFFERS: key ok={it.get("ok")}, solver ok={ans.get("ok")}; '
                                   f'sentence {it.get("s")!r}'))
    print(f'{len(items)} items, {len(flags)} flagged')
    for iid, msg in flags:
        print(f'  {iid}: {msg}')
    return 0


# --------------------------------------------------------------------------
# deterministic clean-up of reviewed batches

FULL_ER_NEXT = '子童女科歌'
FULL_ER_PREV = '女幼婴少'


def _fix_py(zh, py):
    """Mechanical pinyin corrections: erhua 儿 is r, 都 is dōu outside 首都 / 成都."""
    chars = HANZI.findall(zh or '')
    syls = (py or '').split()
    if len(chars) != len(syls):
        return py
    for i, ch in enumerate(chars):
        if ch == '儿':
            full = (i + 1 < len(chars) and chars[i + 1] in FULL_ER_NEXT) or \
                   (i > 0 and chars[i - 1] in FULL_ER_PREV) or i == 0
            if not full and syls[i].lower() in ('ér', 'er'):
                syls[i] = 'r'
        elif ch == '都' and syls[i].lower() == 'dū' and not (i > 0 and chars[i - 1] in '首成'):
            syls[i] = 'dōu'
    return ' '.join(syls)


def _fix_punct(text):
    text = re.sub(r'[，、；：]+([。？！])', r'\1', text)
    text = re.sub(r'([。？！，])[。，]+', r'\1', text)
    return text


def clean_item(it):
    """Returns (item, changed)."""
    before = json.dumps(it, ensure_ascii=False, sort_keys=True)
    for key in ('zh', 'q', 's', 'src'):
        if isinstance(it.get(key), str):
            it[key] = _fix_punct(it[key])
    for zh_key, py_key in (('zh', 'py'), ('s', 's_py'), ('src', 'src_py')):
        if isinstance(it.get(zh_key), str) and isinstance(it.get(py_key), str):
            it[py_key] = _fix_py(it[zh_key], it[py_key])
    if it.get('type') in ('order', 'rewrite') and isinstance(it.get('zh'), str) \
            and it['zh'] and it['zh'][-1] not in '。？！':
        it['zh'] += '。'
    return it, json.dumps(it, ensure_ascii=False, sort_keys=True) != before


def cmd_clean():
    """Apply the mechanical corrections to every reviewed batch, in place."""
    plan = load_plan()
    total = 0
    for path in source_files(plan):
        rows = read_jsonl(path)
        out, changed = [], 0
        for _, obj, err in rows:
            if err:
                continue
            obj, ch = clean_item(obj)
            changed += ch
            out.append(json.dumps(obj, ensure_ascii=False))
        if changed:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write('\n'.join(out) + '\n')
        total += changed
    print(f'{total} items corrected')
    return 0


# --------------------------------------------------------------------------
# build

def source_files(plan):
    """Reviewed batch files, one per (topic, batch)."""
    base = os.path.join(DATA, 'reviewed')
    out = []
    if os.path.isdir(base):
        for name in sorted(os.listdir(base)):
            if name.endswith('.jsonl') and batch_topic(name, plan)[0]:
                out.append(os.path.join(base, name))
    return out


def compact(it):
    out = {k: v for k, v in it.items() if v not in (None, [], '')}
    return out


def cmd_build(check_only=False):
    plan = load_plan()
    by_topic = {t['slug']: [] for t in plan['topics']}
    seen = set()
    dropped_dup = invalid = 0
    for path in source_files(plan):
        slug, _ = batch_topic(path, plan)
        guide = load_guide(slug)
        subs = [s['key'] for s in guide.get('subs', [])] if guide else None
        for _, obj, err in read_jsonl(path):
            if err or validate_item(obj, subs, slug):
                invalid += 1
                continue
            # One sentence is drilled once, whatever the item type.
            key = ('zh', strip_punct(obj['zh']))
            shown = ('zh', strip_punct(obj['s'])) if obj['type'] == 'judge' else key
            if key in seen or shown in seen or obj['id'] in seen:
                dropped_dup += 1
                continue
            seen.add(key)
            seen.add(shown)
            seen.add(obj['id'])
            by_topic[slug].append(compact(obj))
    manifest = {'language': LANG, 'categories': plan['categories'], 'topics': []}
    files = {}
    total = 0
    for t in plan['topics']:
        slug = t['slug']
        guide = load_guide(slug)
        if not guide:
            continue
        items = by_topic[slug]
        body = json.dumps({'topic': slug, 'guide': guide, 'items': items},
                          ensure_ascii=False, separators=(',', ':'))
        files[slug + '.json'] = body
        total += len(items)
        manifest['topics'].append({
            'slug': slug, 'title': t['title'], 'zh': t['zh'], 'cat': t['cat'],
            'summary': guide.get('summary', ''),
            'subs': [{'key': s['key'], 'label': s['label']} for s in guide.get('subs', [])],
            'count': len(items),
            'types': dict(Counter(i['type'] for i in items)),
            'v': hashlib.sha1(body.encode('utf-8')).hexdigest()[:10],
        })
    manifest['total'] = total
    files['manifest.json'] = json.dumps(manifest, ensure_ascii=False, separators=(',', ':'))
    print(f'{total} items in {len(manifest["topics"])} topics; '
          f'{dropped_dup} duplicates and {invalid} invalid lines left out')
    if check_only:
        stale = []
        for name, body in files.items():
            p = os.path.join(OUT, name)
            if not os.path.exists(p) or open(p, encoding='utf-8').read() != body:
                stale.append(name)
        if stale:
            print('out of date: ' + ', '.join(stale))
            return 1
        print('static files are up to date')
        return 0
    os.makedirs(OUT, exist_ok=True)
    for name, body in files.items():
        with open(os.path.join(OUT, name), 'w', encoding='utf-8') as fh:
            fh.write(body)
    size = sum(len(b.encode('utf-8')) for b in files.values())
    print(f'wrote {len(files)} files to {os.path.relpath(OUT, ROOT)} ({size / 1e6:.2f} MB)')
    return 0


def cmd_stats():
    plan = load_plan()
    rows = []
    for t in plan['topics']:
        slug = t['slug']
        n_auth = n_rev = files_auth = files_rev = 0
        for folder in ('batches', 'reviewed'):
            base = os.path.join(DATA, folder)
            if not os.path.isdir(base):
                continue
            for name in os.listdir(base):
                if batch_topic(name, plan)[0] == slug:
                    n = sum(1 for _ in read_jsonl(os.path.join(base, name)))
                    if folder == 'batches':
                        n_auth += n
                        files_auth += 1
                    else:
                        n_rev += n
                        files_rev += 1
        rows.append((slug, t['batches'], os.path.exists(guide_path(slug)), files_auth, n_auth, files_rev, n_rev))
    print(f'{"topic":26} plan guide authored      reviewed')
    for slug, planned, guide, fa, na, fr, nr in rows:
        print(f'{slug:26} {planned:4} {"yes" if guide else "no ":5} {fa:2} files {na:5}  {fr:2} files {nr:5}')
    print(f'{"TOTAL":26} {sum(r[1] for r in rows):4}       {sum(r[3] for r in rows):2} files '
          f'{sum(r[4] for r in rows):5}  {sum(r[5] for r in rows):2} files {sum(r[6] for r in rows):5}')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('validate')
    p.add_argument('files', nargs='+')
    p.add_argument('--min-items', type=int, default=None,
                   help='lowest accepted item count (default: the plan batch size)')
    p = sub.add_parser('validate-guide')
    p.add_argument('files', nargs='+')
    p = sub.add_parser('strip')
    p.add_argument('file')
    p = sub.add_parser('compare')
    p.add_argument('file')
    p = sub.add_parser('build')
    p.add_argument('--check', action='store_true', help='report whether the static files are current')
    sub.add_parser('stats')
    sub.add_parser('clean')
    args = ap.parse_args(argv)
    if args.cmd == 'validate':
        plan = load_plan()
        bad = 0
        for f in args.files:
            _, problems = validate_file(f, plan, min_items=args.min_items)
            bad += bool(problems)
        return 1 if bad else 0
    if args.cmd == 'validate-guide':
        plan = load_plan()
        bad = 0
        for f in args.files:
            _, problems = validate_guide(f, plan)
            bad += bool(problems)
        return 1 if bad else 0
    if args.cmd == 'strip':
        return cmd_strip(args.file)
    if args.cmd == 'compare':
        return cmd_compare(args.file)
    if args.cmd == 'clean':
        return cmd_clean()
    if args.cmd == 'build':
        return cmd_build(check_only=args.check)
    return cmd_stats()


if __name__ == '__main__':
    sys.exit(main())
