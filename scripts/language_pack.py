#!/usr/bin/env python3
"""Checks and builds for a new study language's content pack (local files only).

A pack lives in data/language_packs/<lang>/ and is written by the agent team of
the new-language-swarm skill (.claude/skills/new-language-swarm/SKILL.md). This
script is the team's deterministic half: it never calls a model, the database
or the network (only `lexicon-candidates` needs the wordfreq package).

  python scripts/language_pack.py init it --name Italian --native Italiano
  python scripts/language_pack.py validate-profile it
  python scripts/language_pack.py lexicon-candidates it --top 8000
  python scripts/language_pack.py validate-lexicon it
  python scripts/language_pack.py validate-senses it <file.json>
  python scripts/language_pack.py sense-batches it --size 25 [--limit N]   # lexicon -> senses/write_NNN.in.json
  python scripts/language_pack.py merge-senses it
  python scripts/language_pack.py fatseed-worklist it --n 12
  python scripts/language_pack.py validate-dict it <key> [--reviewed]
  python scripts/language_pack.py validate-guide it <guides/slug.json>
  python scripts/language_pack.py validate-batch it <batches/slug-NN.jsonl> [--min-items N]
  python scripts/language_pack.py strip it <batch>      # blind copy for the reviewer
  python scripts/language_pack.py compare it <batch>    # blind answers against the key
  python scripts/language_pack.py validate-fatseed it <doc.json>
  python scripts/language_pack.py validate-test-plan it <tests/plan/tN.json>
  python scripts/language_pack.py validate-tests it <tests/batches/tN-NN.jsonl>
  python scripts/language_pack.py tests-strip it <batch> ; tests-compare it <batch> ; tests-export it
  python scripts/language_pack.py build it [--check] [--static]   # -> <pack>/grammar/built/ (or static/data/grammar/<lang>/)
  python scripts/language_pack.py archive it ; unarchive it [--force]   # bulky parts <-> archive/*.tar.gz
  python scripts/language_pack.py status it [--json]

Every validate command exits 0 when the file is clean and 1 otherwise.
The grammar item contract is the Chinese one (data/grammar_drills/zh/SPEC.md)
with `zh` renamed `tl` and pinyin replaced by the profile's optional
romanisation; scripts/grammar_drills.py stays the tool for Chinese.
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
PACKS = os.path.join(ROOT, 'data', 'language_packs')
BLANK = '___'
EMPTY = '∅'
TYPES = ('cloze', 'order', 'rewrite', 'judge')
MIX_TOLERANCE = 8
ID_RE = re.compile(r'^[a-z0-9-]+-\d{2}-\d{3}$')
POS = ('noun', 'verb', 'adjective', 'adverb', 'pronoun', 'determiner', 'preposition', 'conjunction',
       'numeral', 'interjection', 'particle', 'auxiliary', 'idiom', 'other')
LADDER_STATUS = ('reuse', 'adapt', 'new', 'not_applicable')
GENERATORS = ('llm', 'deterministic')
SUBDIRS = ('lexicon', 'senses', 'dictionaries', 'dictionaries/reviewed', 'grammar/guides', 'grammar/batches',
           'grammar/reviewed', 'grammar/blind', 'grammar/verdicts', 'tests/plan', 'tests/batches', 'tests/reviewed',
           'tests/blind', 'tests/verdicts', 'fat_seed/words', 'fat_seed/reviewed', 'wiring', 'reports', 'archive')


def pack_dir(lang):
    return os.path.join(PACKS, lang)


def P(lang, *parts):
    return os.path.join(pack_dir(lang), *parts)


def load_json(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def read_jsonl(path):
    rows = []
    with open(path, encoding='utf-8') as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append((n, json.loads(line), None))
            except ValueError as e:
                rows.append((n, None, f'not JSON: {e}'))
    return rows


def report(path, problems, n=None, unit='items'):
    rel = os.path.relpath(path, ROOT)
    tail = f', {n} {unit}' if n is not None else ''
    if problems:
        print(f'{rel}: {len(problems)} problem(s){tail}')
        for p in problems:
            print('  ' + p)
        return 1
    print(f'{rel}: OK{tail}')
    return 0


# --------------------------------------------------------------------------
# profile

PROFILE_TEMPLATE = {
    'code': None, 'name': None, 'native_name': None, 'proposed_language_id': None,
    'variety': 'the standard variety the pack is written in, one sentence',
    'learner': 'who the content is written for, e.g. an English speaker at CEFR A1 to B2',
    'text': {
        'allowed_regex': "^[A-Za-zÀ-ÿ' ,.;:?!()\"«»–-]+$",
        'forbidden_regex': '[0-9]',
        'punctuation': " ,.;:?!()\"«»–",
        'token_joiner': ' ',
        'casefold_tokens': True,
        'length_unit': 'words',
        'sentence_min': 3, 'sentence_max': 22,
        'romanisation': None,
    },
    'levels': {'scheme': 'CEFR', 'bands': ['A1', 'A2', 'B1', 'B2', 'C1'],
               'drill_levels': {'1': 'A1-A2 words, short sentence', '2': 'B1', '3': 'B2, longer or two clauses'}},
    'gloss_languages': ['en'],
    'tts_voices': [],
    'nlp': {'tokeniser': None, 'lemmatiser': None, 'notes': None},
    'ladder': [],
    'unique_features': [],
    'dictionaries': [],
    'targets': {'lexicon': 5000, 'senses': 5000, 'grammar_items': 10000},
}


def cmd_init(a):
    d = pack_dir(a.lang)
    for sub in SUBDIRS:
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    path = P(a.lang, 'profile.json')
    if os.path.exists(path):
        print(f'{os.path.relpath(path, ROOT)} already exists; left as it is')
        return 0
    prof = json.loads(json.dumps(PROFILE_TEMPLATE))
    prof.update(code=a.lang, name=a.name, native_name=a.native)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(prof, fh, ensure_ascii=False, indent=2)
    print(f'created {os.path.relpath(d, ROOT)}/ with a profile template')
    return 0


def load_profile(lang):
    path = P(lang, 'profile.json')
    if not os.path.exists(path):
        raise SystemExit(f'no profile at {os.path.relpath(path, ROOT)}; run init first')
    return load_json(path)


def profile_problems(prof, lang):
    errs = []
    for key in ('code', 'name', 'native_name', 'variety', 'learner'):
        if not isinstance(prof.get(key), str) or not prof[key].strip():
            errs.append(f'{key}: missing')
    if prof.get('code') != lang:
        errs.append(f'code: must be {lang!r}')
    if not isinstance(prof.get('proposed_language_id'), int):
        errs.append('proposed_language_id: an integer not used in dim_languages')
    t = prof.get('text') or {}
    for key in ('allowed_regex', 'forbidden_regex'):
        try:
            re.compile(t.get(key) or '')
        except re.error as e:
            errs.append(f'text.{key}: {e}')
    if not t.get('allowed_regex'):
        errs.append('text.allowed_regex: missing')
    if t.get('length_unit') not in ('words', 'chars'):
        errs.append('text.length_unit: words or chars')
    if not (isinstance(t.get('sentence_min'), int) and isinstance(t.get('sentence_max'), int)
            and 0 < t['sentence_min'] < t['sentence_max']):
        errs.append('text.sentence_min / sentence_max: two integers, min < max')
    if not isinstance(t.get('token_joiner'), str):
        errs.append("text.token_joiner: '' for unspaced scripts, ' ' otherwise")
    lv = prof.get('levels') or {}
    if not lv.get('bands') or sorted((lv.get('drill_levels') or {})) != ['1', '2', '3']:
        errs.append('levels: bands and drill_levels 1, 2, 3 are required')
    if not prof.get('gloss_languages'):
        errs.append('gloss_languages: at least one')
    ladder = prof.get('ladder') or []
    if len(ladder) < 8:
        errs.append(f'ladder: {len(ladder)} rows; every exercise type of ja / zh / en needs a decision, '
                    'plus the new ones')
    seen = set()
    for i, r in enumerate(ladder):
        lab = f'ladder[{i}] {r.get("type_code")}'
        if not re.match(r'^[a-z][a-z0-9_]+$', str(r.get('type_code'))):
            errs.append(f'{lab}: type_code')
        if r.get('type_code') in seen:
            errs.append(f'{lab}: listed twice')
        seen.add(r.get('type_code'))
        if r.get('status') not in LADDER_STATUS:
            errs.append(f'{lab}: status must be one of {LADDER_STATUS}')
        if r.get('status') != 'not_applicable':
            if r.get('generator') not in GENERATORS:
                errs.append(f'{lab}: generator must be one of {GENERATORS}')
            if r.get('ladder_level') is not None and not isinstance(r.get('ladder_level'), int):
                errs.append(f'{lab}: ladder_level is an integer or null')
        if r.get('status') in ('new', 'adapt', 'not_applicable') and not str(r.get('note') or '').strip():
            errs.append(f'{lab}: a note saying what changes or why it does not apply')
    feats = prof.get('unique_features') or []
    if len(feats) < 3:
        errs.append(f'unique_features: {len(feats)}; name what this language has that the others do not')
    dict_keys = {d.get('key') for d in prof.get('dictionaries') or []}
    for i, f in enumerate(feats):
        lab = f'unique_features[{i}] {f.get("key")}'
        for key in ('key', 'title', 'why', 'delivered_by'):
            if not str(f.get(key) or '').strip():
                errs.append(f'{lab}: {key} missing')
        if f.get('delivered_by') not in ('ladder', 'dictionary', 'grammar', 'generator', None):
            errs.append(f'{lab}: delivered_by is ladder, dictionary, grammar or generator')
        if f.get('delivered_by') == 'dictionary' and f.get('dictionary') not in dict_keys:
            errs.append(f'{lab}: dictionary {f.get("dictionary")!r} is not in dictionaries')
    for i, d in enumerate(prof.get('dictionaries') or []):
        lab = f'dictionaries[{i}] {d.get("key")}'
        if not re.match(r'^[a-z][a-z0-9_]+$', str(d.get('key'))):
            errs.append(f'{lab}: key')
        if not isinstance(d.get('fields'), dict) or not d['fields']:
            errs.append(f'{lab}: fields')
        if not isinstance(d.get('target'), int):
            errs.append(f'{lab}: target row count')
        for u in d.get('unique') or []:
            if u not in (d.get('fields') or {}) and u + '?' not in (d.get('fields') or {}):
                errs.append(f'{lab}: unique field {u!r} is not a field')
    return errs


def cmd_validate_profile(a):
    return report(P(a.lang, 'profile.json'), profile_problems(load_profile(a.lang), a.lang))


# --------------------------------------------------------------------------
# text checks

class Text:
    def __init__(self, prof):
        t = prof['text']
        self.allowed = re.compile(t['allowed_regex'])
        self.forbidden = re.compile(t['forbidden_regex']) if t.get('forbidden_regex') else None
        self.punct = t.get('punctuation') or ''
        self.joiner = t.get('token_joiner', ' ')
        self.fold = bool(t.get('casefold_tokens'))
        self.unit = t.get('length_unit', 'words')
        self.lo, self.hi = t['sentence_min'], t['sentence_max']
        self.rom = t.get('romanisation')

    def check(self, s, label, errs, sentence=False):
        if not isinstance(s, str) or not s.strip():
            errs.append(f'{label}: missing')
            return
        if s != s.strip() or '  ' in s:
            errs.append(f'{label}: stray spaces')
        if unicodedata.normalize('NFC', s) != s:
            errs.append(f'{label}: not NFC-normalised (combining accents)')
        if not self.allowed.match(s):
            bad = sorted({c for c in s if not self.allowed.match(c)})
            errs.append(f'{label}: characters outside the profile: {"".join(bad)!r}')
        if self.forbidden and self.forbidden.search(s):
            errs.append(f'{label}: contains {self.forbidden.search(s).group(0)!r} (forbidden by the profile)')
        if sentence:
            n = self.length(s)
            if not self.lo <= n <= self.hi:
                errs.append(f'{label}: {n} {self.unit} ({self.lo} to {self.hi} allowed)')

    def length(self, s):
        return len(self.norm(s).split()) if self.unit == 'words' else len(self.strip(s))

    def strip(self, s):
        out = ''.join(' ' if (c in self.punct and self.joiner) else ('' if c in self.punct else c) for c in s)
        return ' '.join(out.split()) if self.joiner else out

    def norm(self, s):
        s = self.strip(s or '')
        return s.casefold() if self.fold else s

    def join(self, tokens):
        return self.norm(self.joiner.join(tokens))


def fill(q, opt):
    out = q
    for part in opt.split('|'):
        out = out.replace(BLANK, '' if part == EMPTY else part, 1)
    return out


def tidy(s):
    """Spacing left by an empty option: 'Vado  a casa' / 'Vado a casa .'"""
    return re.sub(r'\s+([,.;:?!])', r'\1', ' '.join(s.split()))


# --------------------------------------------------------------------------
# grammar: plan, guides, items

def load_plan(lang):
    path = P(lang, 'grammar', 'plan.json')
    if not os.path.exists(path):
        raise SystemExit(f'no grammar plan at {os.path.relpath(path, ROOT)}')
    return load_json(path)


def topic_of(plan, slug):
    return next((t for t in plan['topics'] if t['slug'] == slug), None)


def plan_problems(plan, lang):
    errs = []
    if plan.get('language') != lang:
        errs.append(f'language: must be {lang!r}')
    if not isinstance(plan.get('batch_size'), int):
        errs.append('batch_size: integer')
    cats = {c.get('key') for c in plan.get('categories') or []}
    if len(plan.get('themes') or []) < 10:
        errs.append('themes: at least 10, so parallel batches do not collide')
    seen = set()
    for t in plan.get('topics') or []:
        lab = f'topic {t.get("slug")}'
        if not re.match(r'^[a-z][a-z0-9-]*$', str(t.get('slug'))) or t.get('slug') in seen:
            errs.append(f'{lab}: slug must be lowercase-hyphenated and unique')
        seen.add(t.get('slug'))
        if t.get('cat') not in cats:
            errs.append(f'{lab}: cat is not a category')
        mix = t.get('mix') or {}
        if set(mix) - set(TYPES) or sum(mix.values()) != plan.get('batch_size'):
            errs.append(f'{lab}: mix must use {TYPES} and sum to batch_size')
        if not isinstance(t.get('batches'), int) or t['batches'] < 0:
            errs.append(f'{lab}: batches')
        if len(str(t.get('scope') or '')) < 60:
            errs.append(f'{lab}: scope must spell out what the topic covers (60+ characters)')
        if not str(t.get('title') or '').strip():
            errs.append(f'{lab}: title')
    if not plan.get('topics'):
        errs.append('topics: none')
    return errs


def load_guide(lang, slug):
    path = P(lang, 'grammar', 'guides', slug + '.json')
    return load_json(path) if os.path.exists(path) else None


def check_example(tx, ex, label, errs):
    if not isinstance(ex, dict):
        errs.append(f'{label}: must be an object with tl and en')
        return
    tx.check(ex.get('tl'), f'{label}.tl', errs)
    if not str(ex.get('en') or '').strip():
        errs.append(f'{label}.en: missing')


def guide_problems(lang, path, plan, tx):
    errs = []
    slug = os.path.basename(path)[:-5]
    topic = topic_of(plan, slug)
    if not topic:
        errs.append('file name must be <topic-slug>.json with a topic from plan.json')
    try:
        g = load_json(path)
    except ValueError as e:
        return [f'not JSON: {e}']
    if g.get('topic') != slug:
        errs.append(f'topic: must be {slug!r}')
    if not 60 <= len(str(g.get('summary') or '')) <= 420:
        errs.append('summary: 60 to 420 characters')
    subs = g.get('subs') or []
    keys = [s.get('key') for s in subs if isinstance(s, dict)]
    if not 3 <= len(subs) <= 10 or len(set(keys)) != len(keys):
        errs.append('subs: 3 to 10 sub-points with unique keys')
    for s in subs:
        if not re.match(r'^[a-z][a-z0-9-]*$', str(s.get('key'))):
            errs.append(f'subs {s.get("key")!r}: key must be lowercase-hyphenated')
        for f in ('label', 'focus'):
            if not str(s.get(f) or '').strip():
                errs.append(f'subs {s.get("key")!r}: {f} missing')
    rules = g.get('rules') or []
    if not 3 <= len(rules) <= 12:
        errs.append('rules: 3 to 12')
    for i, r in enumerate(rules):
        if r.get('sub') not in keys:
            errs.append(f'rules[{i}]: sub is not a sub-point key')
        if not str(r.get('rule') or '').strip():
            errs.append(f'rules[{i}]: rule missing')
        exs = r.get('examples') or []
        if not 2 <= len(exs) <= 4:
            errs.append(f'rules[{i}]: 2 to 4 examples')
        for j, ex in enumerate(exs):
            check_example(tx, ex, f'rules[{i}].examples[{j}]', errs)
    used = {r.get('sub') for r in rules}
    for k in keys:
        if k not in used:
            errs.append(f'subs {k!r}: no rule covers it')
    cons = g.get('contrasts') or []
    if not 3 <= len(cons) <= 10:
        errs.append('contrasts: 3 to 10')
    for i, c in enumerate(cons):
        tx.check(c.get('wrong'), f'contrasts[{i}].wrong', errs)
        check_example(tx, c.get('right'), f'contrasts[{i}].right', errs)
        if not str(c.get('why') or '').strip():
            errs.append(f'contrasts[{i}]: why missing')
        if isinstance(c.get('right'), dict) and tx.norm(c.get('wrong')) == tx.norm(c['right'].get('tl')):
            errs.append(f'contrasts[{i}]: wrong and right are the same sentence')
    cheat = g.get('cheat') or []
    if not 3 <= len(cheat) <= 7 or not all(isinstance(c, str) and c.strip() for c in cheat):
        errs.append('cheat: 3 to 7 one-line rules')
    return errs


def item_problems(it, subs, slug, tx):
    errs = []
    if not isinstance(it, dict):
        return ['not an object']
    iid = it.get('id')
    if not isinstance(iid, str) or not ID_RE.match(iid):
        errs.append('id: must look like <topic>-NN-NNN')
    elif slug and not iid.startswith(slug + '-'):
        errs.append(f'id: must start with {slug}-')
    t = it.get('type')
    if t not in TYPES:
        return errs + [f'type: must be one of {TYPES}']
    if subs is not None and it.get('sub') not in subs:
        errs.append(f'sub: {it.get("sub")!r} is not a sub-point of the guide')
    if it.get('lvl') not in (1, 2, 3):
        errs.append('lvl: 1, 2 or 3')
    tl = it.get('tl')
    tx.check(tl, 'tl', errs, sentence=True)
    if not str(it.get('en') or '').strip():
        errs.append('en: missing')
    why = it.get('why')
    if not isinstance(why, str) or not 15 <= len(why) <= 260:
        errs.append('why: 15 to 260 characters')
    allowed = {'id', 'type', 'sub', 'lvl', 'tl', 'en', 'why'}
    if tx.rom:
        allowed |= {'rom', 's_rom', 'src_rom'}
        if not str(it.get('rom') or '').strip():
            errs.append(f'rom: the {tx.rom} of tl is required')
    if t == 'cloze':
        allowed |= {'q', 'opts', 'a'}
        q, opts, a = it.get('q'), it.get('opts'), it.get('a')
        blanks = q.count(BLANK) if isinstance(q, str) else 0
        if blanks not in (1, 2):
            errs.append('q: one blank written ___ (two for paired words)')
        if not (isinstance(opts, list) and 2 <= len(opts) <= 4 and all(isinstance(o, str) and o for o in opts)):
            errs.append('opts: 2 to 4 options')
        elif len({tx.norm(o) for o in opts}) != len(opts):
            errs.append('opts: two options are the same')
        elif not (isinstance(a, int) and not isinstance(a, bool) and 0 <= a < len(opts)):
            errs.append('a: index of the right option')
        elif blanks and isinstance(tl, str):
            for o in opts:
                if len(o.split('|')) != blanks:
                    errs.append(f'opts: {o!r} must have {blanks} part(s) separated by |')
                for part in o.split('|'):
                    if part != EMPTY:
                        tx.check(part, 'opts', errs)
            if tidy(fill(q, opts[a])) != tl:
                errs.append('tl: must equal q with the correct option filled in')
    elif t in ('order', 'rewrite'):
        allowed |= {'tokens', 'alts', 'extra'}
        tokens = it.get('tokens')
        if not (isinstance(tokens, list) and 3 <= len(tokens) <= 10 and all(isinstance(x, str) and x for x in tokens)):
            errs.append('tokens: 3 to 10 tiles')
        elif isinstance(tl, str):
            if tx.join(tokens) != tx.norm(tl):
                errs.append('tokens: joined in order they must equal tl without punctuation')
            if any(c in tx.punct.replace(' ', '') for x in tokens for c in x):
                errs.append('tokens: no punctuation on tiles')
            for alt in it.get('alts') or []:
                if not isinstance(alt, list) or sorted(alt) != sorted(tokens):
                    errs.append('alts: each alternative is another order of exactly the same tiles')
                elif alt == tokens:
                    errs.append('alts: an alternative repeats the main order')
            extra = it.get('extra') or []
            if len(extra) > 2 or any(x in tokens for x in extra):
                errs.append('extra: at most 2 distractor tiles, none of them a real tile')
        if t == 'rewrite':
            allowed |= {'src', 'task'}
            tx.check(it.get('src'), 'src', errs, sentence=True)
            if not str(it.get('task') or '').strip():
                errs.append('task: a short English instruction')
            if isinstance(tl, str) and tx.norm(it.get('src')) == tx.norm(tl):
                errs.append('src: must differ from tl')
    else:
        allowed |= {'s', 'ok'}
        s, ok = it.get('s'), it.get('ok')
        tx.check(s, 's', errs)
        if not isinstance(ok, bool):
            errs.append('ok: true or false')
        elif isinstance(s, str) and isinstance(tl, str):
            if ok and s != tl:
                errs.append('s: when ok is true, s must equal tl')
            if not ok and tx.norm(s) == tx.norm(tl):
                errs.append('tl: when ok is false, tl is the corrected sentence and must differ from s')
    extra_keys = set(it) - allowed
    if extra_keys:
        errs.append('unknown fields: ' + ', '.join(sorted(extra_keys)))
    return errs


def dedup_key(it, tx):
    if it.get('type') == 'cloze':
        return ('cloze', it.get('q'), tx.norm(it.get('tl')))
    return (it.get('type'), tx.norm(it.get('tl')), it.get('src'))


def batch_topic(path, plan):
    m = re.match(r'^([a-z0-9-]+)-(\d{2})\.jsonl$', os.path.basename(path))
    if not m or not topic_of(plan, m.group(1)):
        return None, None
    return m.group(1), m.group(2)


def batch_problems(lang, path, plan, tx, min_items=None):
    slug, batch_no = batch_topic(path, plan)
    problems = []
    if not slug:
        problems.append('file name must be <topic-slug>-<NN>.jsonl with a topic from plan.json')
    topic = topic_of(plan, slug) if slug else None
    guide = load_guide(lang, slug) if slug else None
    subs = [s['key'] for s in guide.get('subs', [])] if guide else None
    if slug and subs is None:
        problems.append(f'no guide for {slug}')
    seen_ids, seen_keys, items = {}, {}, []
    for n, obj, err in read_jsonl(path):
        if err:
            problems.append(f'line {n}: {err}')
            continue
        errs = item_problems(obj, subs, slug, tx)
        iid = obj.get('id', '?') if isinstance(obj, dict) else '?'
        if isinstance(obj, dict):
            if batch_no and isinstance(iid, str) and ID_RE.match(iid) and iid.split('-')[-2] != batch_no:
                errs.append(f'id: batch part must be {batch_no}')
            if iid in seen_ids:
                errs.append(f'id: duplicate of line {seen_ids[iid]}')
            seen_ids.setdefault(iid, n)
            key = dedup_key(obj, tx)
            if key in seen_keys:
                errs.append(f'duplicate content of line {seen_keys[key]}')
            seen_keys.setdefault(key, n)
            items.append(obj)
        problems += [f'line {n} ({iid}): {e}' for e in errs]
    size = plan['batch_size']
    floor = min_items if min_items is not None else size
    if len(items) < floor:
        problems.append(f'{len(items)} items; at least {floor} required')
    if len(items) > size + 10:
        problems.append(f'{len(items)} items; at most {size + 10}')
    if topic and items:
        counts = Counter(i.get('type') for i in items)
        scale = len(items) / size
        tol = max(3, round(MIX_TOLERANCE * scale))
        for typ, target in topic['mix'].items():
            if abs(counts.get(typ, 0) - target * scale) > tol:
                problems.append(f'type mix: {counts.get(typ, 0)} {typ} items, target {round(target * scale)} (±{tol})')
        lv = Counter(i.get('lvl') for i in items)
        if lv.get(1, 0) < 0.25 * len(items) or lv.get(3, 0) < 0.1 * len(items):
            problems.append(f'level mix: lvl1={lv.get(1, 0)} lvl2={lv.get(2, 0)} lvl3={lv.get(3, 0)}; '
                            'need at least 25% level 1 and 10% level 3')
        if subs:
            sc = Counter(i.get('sub') for i in items)
            missing = [s for s in subs if not sc.get(s)]
            if len(missing) > len(subs) // 2:
                problems.append('sub-points: more than half are unused: ' + ', '.join(missing))
        judges = [i for i in items if i.get('type') == 'judge']
        if len(judges) >= 6:
            oks = sum(1 for i in judges if i.get('ok') is True)
            if not 0.3 <= oks / len(judges) <= 0.6:
                problems.append(f'judge items: {oks} of {len(judges)} are correct sentences; keep 30-60%')
        clozes = [i for i in items if i.get('type') == 'cloze' and isinstance(i.get('a'), int)]
        if len(clozes) >= 20 and Counter(i['a'] for i in clozes).most_common(1)[0][1] > 0.5 * len(clozes):
            problems.append('cloze: the correct option sits at the same index in over half the items')
    return items, problems


def resolve(lang, path, sub):
    if os.path.exists(path):
        return path
    cand = P(lang, *sub.split('/'), path)
    return cand if os.path.exists(cand) else path


def cmd_validate_guide(a):
    prof = load_profile(a.lang)
    path = resolve(a.lang, a.path, 'grammar/guides')
    return report(path, guide_problems(a.lang, path, load_plan(a.lang), Text(prof)))


def cmd_validate_plan(a):
    return report(P(a.lang, 'grammar', 'plan.json'), plan_problems(load_plan(a.lang), a.lang))


def cmd_validate_batch(a):
    prof = load_profile(a.lang)
    path = resolve(a.lang, a.path, 'grammar/batches')
    items, problems = batch_problems(a.lang, path, load_plan(a.lang), Text(prof), a.min_items)
    return report(path, problems, len(items))


def blind_paths(lang, batch_path):
    name = os.path.basename(batch_path)[:-6]
    return P(lang, 'grammar', 'blind', name + '.blind.jsonl'), P(lang, 'grammar', 'blind', name + '.answers.jsonl')


def cmd_strip(a):
    path = resolve(a.lang, a.path, 'grammar/batches')
    rows = [o for _, o, e in read_jsonl(path) if not e and isinstance(o, dict)]
    blind, answers = blind_paths(a.lang, path)
    os.makedirs(os.path.dirname(blind), exist_ok=True)
    with open(blind, 'w', encoding='utf-8') as fh:
        for it in rows:
            t = it.get('type')
            if t == 'cloze':
                out = {'id': it['id'], 'type': t, 'q': it.get('q'), 'opts': it.get('opts'), 'en': it.get('en')}
            elif t in ('order', 'rewrite'):
                tiles = sorted((it.get('tokens') or []) + (it.get('extra') or []),
                               key=lambda s: hashlib.md5((it['id'] + s).encode()).hexdigest())
                out = {'id': it['id'], 'type': t, 'tiles': tiles, 'en': it.get('en')}
                if t == 'rewrite':
                    out.update(src=it.get('src'), task=it.get('task'))
            else:
                out = {'id': it['id'], 'type': t, 's': it.get('s')}
            fh.write(json.dumps(out, ensure_ascii=False) + '\n')
    print(f'wrote {os.path.relpath(blind, ROOT)} ({len(rows)} items)')
    print(f'answers go to {os.path.relpath(answers, ROOT)}')
    return 0


def cmd_compare(a):
    tx = Text(load_profile(a.lang))
    path = resolve(a.lang, a.path, 'grammar/batches')
    _, answers = blind_paths(a.lang, path)
    if not os.path.exists(answers):
        print(f'no answers file at {os.path.relpath(answers, ROOT)}')
        return 2
    items = {o['id']: o for _, o, e in read_jsonl(path) if not e and isinstance(o, dict) and 'id' in o}
    got = {o.get('id'): o for _, o, e in read_jsonl(answers) if not e and isinstance(o, dict)}
    flags = []
    for iid, it in items.items():
        ans, t = got.get(iid), it.get('type')
        if ans is None:
            flags.append((iid, 'no blind answer'))
        elif t == 'cloze':
            ok, opts = ans.get('ok'), it.get('opts') or []
            pick = lambda idx: [opts[i] for i in idx if isinstance(i, int) and 0 <= i < len(opts)]  # noqa: E731
            if not isinstance(ok, list):
                flags.append((iid, 'blind answer has no "ok" list'))
            elif it.get('a') not in ok:
                flags.append((iid, f'KEY REJECTED: key={opts[it["a"]]!r}, solver accepted {pick(ok)}'))
            elif len(ok) > 1:
                flags.append((iid, f'AMBIGUOUS: solver also accepted {pick([i for i in ok if i != it["a"]])}'))
        elif t in ('order', 'rewrite'):
            built = tx.norm(str(ans.get('tl', '')))
            accepted = {tx.join(it.get('tokens') or [])} | {tx.join(x) for x in it.get('alts', [])}
            if built not in accepted:
                flags.append((iid, f'DIFFERENT ORDER: solver built {ans.get("tl")!r}; key {it.get("tl")!r} '
                                   '(add it to alts if it is also correct, otherwise fix the item)'))
        elif ans.get('ok') is not it.get('ok'):
            flags.append((iid, f'JUDGEMENT DIFFERS: key ok={it.get("ok")}, solver ok={ans.get("ok")}; '
                               f'sentence {it.get("s")!r}'))
    print(f'{len(items)} items, {len(flags)} flagged')
    for iid, msg in flags:
        print(f'  {iid}: {msg}')
    return 0


def source_files(lang, plan):
    """The reviewed copy of a batch when there is one, else nothing: unreviewed batches are never served."""
    d = P(lang, 'grammar', 'reviewed')
    names = sorted(os.listdir(d)) if os.path.isdir(d) else []
    return [os.path.join(d, n) for n in names if batch_topic(n, plan)[0]]


def cmd_build(a):
    prof, plan = load_profile(a.lang), load_plan(a.lang)
    tx = Text(prof)
    # Built files stay in the pack (and its archive) until the language is served; --static writes the app's path.
    out_dir = os.path.join(ROOT, 'static', 'data', 'grammar', a.lang) if a.static else P(a.lang, 'grammar', 'built')
    by_topic = {t['slug']: [] for t in plan['topics']}
    seen, dropped, invalid = set(), 0, 0
    for path in source_files(a.lang, plan):
        slug, _ = batch_topic(path, plan)
        guide = load_guide(a.lang, slug)
        subs = [s['key'] for s in guide.get('subs', [])] if guide else None
        for _, obj, err in read_jsonl(path):
            if err or item_problems(obj, subs, slug, tx):
                invalid += 1
                continue
            key = tx.norm(obj['tl'])
            shown = tx.norm(obj['s']) if obj['type'] == 'judge' else key
            if key in seen or shown in seen or obj['id'] in seen:
                dropped += 1
                continue
            seen.update((key, shown, obj['id']))
            by_topic[slug].append({k: v for k, v in obj.items() if v not in (None, [], '')})
    manifest = {'language': a.lang, 'fields': {'sentence': 'tl', 'romanisation': 'rom' if tx.rom else None},
                'token_joiner': tx.joiner, 'categories': plan['categories'], 'topics': []}
    files, total = {}, 0
    for t in plan['topics']:
        guide, items = load_guide(a.lang, t['slug']), by_topic[t['slug']]
        if not guide or not items:
            continue
        body = json.dumps({'topic': t['slug'], 'guide': guide, 'items': items}, ensure_ascii=False,
                          separators=(',', ':'))
        files[t['slug'] + '.json'] = body
        total += len(items)
        manifest['topics'].append({
            'slug': t['slug'], 'title': t['title'], 'cat': t['cat'], 'summary': guide.get('summary', ''),
            'subs': [{'key': s['key'], 'label': s['label']} for s in guide.get('subs', [])],
            'count': len(items), 'types': dict(Counter(i['type'] for i in items)),
            'v': hashlib.sha1(body.encode('utf-8')).hexdigest()[:10]})
    manifest['total'] = total
    files['manifest.json'] = json.dumps(manifest, ensure_ascii=False, separators=(',', ':'))
    print(f'{total} items in {len(manifest["topics"])} topics; {dropped} duplicates and {invalid} invalid lines left out')
    if a.check:
        stale = [n for n, b in files.items()
                 if not os.path.exists(os.path.join(out_dir, n))
                 or open(os.path.join(out_dir, n), encoding='utf-8').read() != b]
        print('out of date: ' + ', '.join(stale) if stale else 'static files are up to date')
        return 1 if stale else 0
    os.makedirs(out_dir, exist_ok=True)
    for name, body in files.items():
        with open(os.path.join(out_dir, name), 'w', encoding='utf-8') as fh:
            fh.write(body)
    size = sum(len(b.encode('utf-8')) for b in files.values())
    print(f'wrote {len(files)} files to {os.path.relpath(out_dir, ROOT)} ({size / 1e6:.2f} MB)')
    return 0


# --------------------------------------------------------------------------
# lexicon

def cmd_lexicon_candidates(a):
    try:
        from wordfreq import top_n_list, zipf_frequency
    except ImportError:
        raise SystemExit('pip install wordfreq (see requirements.txt) to list candidates')
    try:
        import simplemma
        lemma_of = lambda w: simplemma.lemmatize(w, lang=a.lang)  # noqa: E731
        lemmatiser = 'simplemma'
    except Exception:
        lemma_of = lambda w: w  # noqa: E731
        lemmatiser = 'none'
    word_re = re.compile(a.word_regex)
    groups = {}
    for w in top_n_list(a.lang, a.top * 4):
        if not word_re.match(w):
            continue
        lem = lemma_of(w).lower()
        g = groups.setdefault(lem, {'f': 0.0, 'forms': []})
        g['f'] += 10 ** zipf_frequency(w, a.lang)
        if len(g['forms']) < 8:
            g['forms'].append(w)
    import math
    rows = sorted(groups.items(), key=lambda kv: -kv[1]['f'])[:a.top]
    out = P(a.lang, 'lexicon', 'candidates.tsv')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(f'# wordfreq top list for {a.lang}, grouped by lemma ({lemmatiser}); zipf = summed over forms\n')
        fh.write('rank\tlemma\tzipf\tforms\n')
        for i, (lem, g) in enumerate(rows, 1):
            fh.write(f'{i}\t{lem}\t{math.log10(g["f"]):.2f}\t{" ".join(g["forms"])}\n')
    print(f'wrote {len(rows)} candidate lemmas to {os.path.relpath(out, ROOT)}')
    return 0


def lexicon_rows(lang):
    d = P(lang, 'lexicon')
    rows = []
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if re.match(r'^lexicon(_\d+)?\.jsonl$', name):
            rows += [(name, n, o, e) for n, o, e in read_jsonl(os.path.join(d, name))]
    return rows


def lexicon_problems(prof, rows):
    errs, seen = [], {}
    bands = set(prof['levels']['bands'])
    word = re.compile(prof['text']['allowed_regex'])
    for name, n, o, e in rows:
        lab = f'{name} line {n}'
        if e or not isinstance(o, dict):
            errs.append(f'{lab}: {e or "not an object"}')
            continue
        if o.get('drop'):
            if not str(o.get('reason') or '').strip():
                errs.append(f'{lab}: a dropped candidate needs a reason')
            continue
        lem = o.get('lemma')
        if not isinstance(lem, str) or not lem or not word.match(lem):
            errs.append(f'{lab}: lemma {lem!r}')
            continue
        if o.get('pos') not in POS:
            errs.append(f'{lab} {lem}: pos must be one of {POS}')
        if o.get('level') not in bands:
            errs.append(f'{lab} {lem}: level must be one of {sorted(bands)}')
        if not isinstance(o.get('zipf'), (int, float)):
            errs.append(f'{lab} {lem}: zipf (from candidates.tsv)')
        if not str(o.get('hint') or '').strip():
            errs.append(f'{lab} {lem}: hint (short English meaning: WHICH word this is)')
        key = (lem, o.get('pos'))
        if key in seen:
            errs.append(f'{lab} {lem}: same lemma and pos as {seen[key]}')
        seen.setdefault(key, lab)
    return errs


def cmd_validate_lexicon(a):
    prof, rows = load_profile(a.lang), lexicon_rows(a.lang)
    kept = sum(1 for _, _, o, e in rows if not e and isinstance(o, dict) and not o.get('drop'))
    return report(P(a.lang, 'lexicon'), lexicon_problems(prof, rows) or ([] if rows else ['no lexicon*.jsonl']),
                  kept, 'lemmas')


# --------------------------------------------------------------------------
# senses

def sense_problems(prof, entries, expect=None):
    errs = []
    glang = prof['gloss_languages']
    tx = Text(prof)
    if not isinstance(entries, list):
        return ['must be a JSON array']
    if expect is not None and [e.get('lemma') for e in entries if isinstance(e, dict)] != expect:
        errs.append('one entry per input word, in the input order')
    for i, s in enumerate(entries):
        if not isinstance(s, dict):
            errs.append(f'[{i}]: not an object')
            continue
        lem = s.get('lemma')
        lab = f'[{i}] {lem}'
        if s.get('skip'):
            if not str(s.get('reason') or '').strip():
                errs.append(f'{lab}: skip needs a reason')
            continue
        if s.get('pos') not in POS:
            errs.append(f'{lab}: pos')
        c = s.get('confidence')
        if not isinstance(c, (int, float)) or not 0 <= c <= 1:
            errs.append(f'{lab}: confidence 0-1')
        for f in ('tl_simple', 'tl_standard', 'example'):
            tx.check(s.get(f), f, e2 := [])
            errs += [f'{lab}: {x}' for x in e2 if 'forbidden' not in x or f == 'example']
        low = str(s.get('tl_simple') or '').casefold()
        if isinstance(lem, str) and re.search(r'(?<!\w)' + re.escape(lem.casefold()) + r'(?!\w)', low):
            errs.append(f'{lab}: tl_simple uses the word itself')
        if len(str(s.get('example') or '')) > 90:
            errs.append(f'{lab}: example over 90 characters')
        if len(str(s.get('tl_standard') or '')) > 240:
            errs.append(f'{lab}: tl_standard over 240 characters')
        gl = s.get('glosses') or {}
        for g in glang:
            pair = gl.get(g) or {}
            sim, std = str(pair.get('simple') or ''), str(pair.get('standard') or '')
            if not sim or not std:
                errs.append(f'{lab}: glosses.{g}.simple / standard missing')
                continue
            if len(sim) > 60:
                errs.append(f'{lab}: glosses.{g}.simple over 60 characters')
            if len(std) > 120:
                errs.append(f'{lab}: glosses.{g}.standard over 120 characters')
            if len(std) <= len(sim):
                errs.append(f'{lab}: glosses.{g}.standard must be longer than simple')
        if not str(s.get('pronunciation') or '').strip():
            errs.append(f'{lab}: pronunciation (IPA or the profile\'s reading)')
    return errs


def cmd_validate_senses(a):
    prof = load_profile(a.lang)
    path = resolve(a.lang, a.path, 'senses')
    try:
        entries = load_json(path)
    except ValueError as e:
        return report(path, [f'not JSON: {e}'])
    expect = None
    src = re.sub(r'\.(out|reviewed)\.json$', '.in.json', path)
    if src != path and os.path.exists(src):
        expect = [w['lemma'] for w in load_json(src)]
    return report(path, sense_problems(prof, entries, expect), len(entries) if isinstance(entries, list) else None,
                  'entries')


def cmd_merge_senses(a):
    """senses/final.json = every *.reviewed.json entry that is not skipped; a batch with no review is left out."""
    prof = load_profile(a.lang)
    d = P(a.lang, 'senses')
    final, unreviewed, bad = [], [], []
    for name in sorted(os.listdir(d)):
        if not name.endswith('.out.json'):
            continue
        rev = os.path.join(d, name.replace('.out.json', '.reviewed.json'))
        if not os.path.exists(rev):
            unreviewed.append(name)
            continue
        entries = load_json(rev)
        if sense_problems(prof, entries):
            bad.append(os.path.basename(rev))
            continue
        final += [e for e in entries if not e.get('skip')]
    with open(os.path.join(d, 'final.json'), 'w', encoding='utf-8') as fh:
        json.dump(final, fh, ensure_ascii=False, indent=1)
    print(f'{len(final)} senses in senses/final.json; unreviewed batches left out: {unreviewed or "none"}; '
          f'failing batches left out: {bad or "none"}')
    return 1 if bad else 0


def cmd_sense_batches(a):
    """Cut the kept lexicon rows that no senses/write_*.in.json holds yet into input batches."""
    d = P(a.lang, 'senses')
    os.makedirs(d, exist_ok=True)
    have, last = set(), 0
    for name in sorted(os.listdir(d)):
        m = re.match(r'^write_(\d+)\.in\.json$', name)
        if m:
            last = max(last, int(m.group(1)))
            have |= {(w['lemma'], w.get('pos')) for w in load_json(os.path.join(d, name))}
    todo = [o for _, _, o, e in lexicon_rows(a.lang)
            if not e and isinstance(o, dict) and not o.get('drop') and (o.get('lemma'), o.get('pos')) not in have]
    todo.sort(key=lambda o: -float(o.get('zipf') or 0))
    if a.limit:
        todo = todo[:a.limit]
    names = []
    for i in range(0, len(todo), a.size):
        last += 1
        name = f'write_{last:03d}.in.json'
        with open(os.path.join(d, name), 'w', encoding='utf-8') as fh:
            json.dump([{k: o.get(k) for k in ('lemma', 'pos', 'level', 'zipf', 'hint')} for o in todo[i:i + a.size]],
                      fh, ensure_ascii=False, indent=1)
        names.append(name)
    print(json.dumps({'batches': names, 'words': len(todo)}))
    return 0


def cmd_fatseed_worklist(a):
    """Pick n reviewed senses for the fat-seed slice: content words, spread over parts of speech.

    Function words (articles, prepositions) are taught by dictionaries and grammar drills, and their
    exercise documents were the weakest in the Italian pilot; --function-words adds them after the rest.
    """
    final = load_json(P(a.lang, 'senses', 'final.json'))
    d = P(a.lang, 'fat_seed')
    done = {n[:-5] for n in os.listdir(os.path.join(d, 'words'))} if os.path.isdir(os.path.join(d, 'words')) else set()
    by_pos = {}
    for s in final:
        if slug(s['lemma'], s['pos']) not in done:
            by_pos.setdefault(s['pos'], []).append(s)
    content = [p for p in ('verb', 'noun', 'adjective', 'adverb') if p in by_pos]
    rest = [p for p in by_pos if p not in content]
    picked = []
    for order in (content, rest if a.function_words or not content else []):
        while len(picked) < a.n and any(by_pos[p] for p in order):
            for pos in order:
                if by_pos[pos] and len(picked) < a.n:
                    picked.append(by_pos[pos].pop(0))
    for s in picked:
        s['doc'] = slug(s['lemma'], s['pos']) + '.json'
    with open(os.path.join(d, 'worklist.json'), 'w', encoding='utf-8') as fh:
        json.dump(picked, fh, ensure_ascii=False, indent=1)
    print(json.dumps({'senses': [s['doc'] for s in picked]}, ensure_ascii=False))
    return 0


def slug(lemma, pos):
    base = unicodedata.normalize('NFKD', lemma).encode('ascii', 'ignore').decode() or 'w'
    return re.sub(r'[^a-z0-9]+', '-', base.lower()).strip('-') + '.' + pos


# --------------------------------------------------------------------------
# dictionaries (the language's own lookup tables: gender, conjugation, classifiers ...)

def check_field(val, spec, label, errs):
    if spec == 'str':
        if not isinstance(val, str) or not val.strip():
            errs.append(f'{label}: text')
    elif spec == 'int':
        if not isinstance(val, int) or isinstance(val, bool):
            errs.append(f'{label}: integer')
    elif spec == 'bool':
        if not isinstance(val, bool):
            errs.append(f'{label}: true or false')
    elif isinstance(spec, list):
        if val not in spec:
            errs.append(f'{label}: {val!r} is not one of {spec}')
    elif isinstance(spec, dict) and 'regex' in spec:
        if not isinstance(val, str) or not re.match(spec['regex'], val):
            errs.append(f'{label}: {val!r} does not match {spec["regex"]}')
    elif isinstance(spec, dict) and 'list' in spec:
        lo = spec.get('min', 0)
        if not isinstance(val, list) or len(val) < lo or len(val) > spec.get('max', 10 ** 6):
            errs.append(f'{label}: a list of at least {lo}')
        else:
            for j, v in enumerate(val):
                check_field(v, spec['list'], f'{label}[{j}]', errs)
    elif isinstance(spec, dict) and 'object' in spec:
        if not isinstance(val, dict):
            errs.append(f'{label}: an object')
        else:
            check_row(val, spec['object'], label, errs)
    else:
        errs.append(f'{label}: the profile has an unknown field spec {spec!r}')


def check_row(row, fields, label, errs):
    names = set()
    for name, spec in fields.items():
        optional = name.endswith('?')
        name = name.rstrip('?')
        names.add(name)
        if name not in row or row[name] is None:
            if not optional:
                errs.append(f'{label}: {name} missing')
            continue
        check_field(row[name], spec, f'{label}.{name}', errs)
    extra = set(row) - names
    if extra:
        errs.append(f'{label}: unknown fields {sorted(extra)}')


def dict_spec(prof, key):
    spec = next((d for d in prof.get('dictionaries') or [] if d.get('key') == key), None)
    if not spec:
        raise SystemExit(f'no dictionary {key!r} in the profile')
    return spec


def dict_files(lang, key, reviewed=False):
    d = P(lang, 'dictionaries', 'reviewed') if reviewed else P(lang, 'dictionaries')
    if not os.path.isdir(d):
        return []
    return [os.path.join(d, n) for n in sorted(os.listdir(d)) if re.match(rf'^{re.escape(key)}(_\d+)?\.jsonl$', n)]


def cmd_validate_dict(a):
    prof = load_profile(a.lang)
    spec = dict_spec(prof, a.key)
    errs, seen, n_rows = [], {}, 0
    files = dict_files(a.lang, a.key, a.reviewed)
    for path in files:
        for n, row, err in read_jsonl(path):
            lab = f'{os.path.basename(path)} line {n}'
            if err or not isinstance(row, dict):
                errs.append(f'{lab}: {err or "not an object"}')
                continue
            n_rows += 1
            check_row(row, spec['fields'], lab, errs)
            if spec.get('unique'):
                key = tuple(json.dumps(row.get(u), ensure_ascii=False) for u in spec['unique'])
                if key in seen:
                    errs.append(f'{lab}: same {"+".join(spec["unique"])} as {seen[key]}')
                seen.setdefault(key, lab)
    if not files:
        errs.append(f'no {a.key}*.jsonl there')
    where = ('dictionaries', 'reviewed', a.key) if a.reviewed else ('dictionaries', a.key)
    return report(P(a.lang, *where), errs, n_rows, 'rows')


# --------------------------------------------------------------------------
# fat-seed documents: shape only (the real validator is scripts/fat_seed_runner.py check, which needs
# the language's prompt templates and capability rows in the database)

OPTION_BLOCKS = {'level_1': (4, 8), 'level_3': (4, 4), 'level_5': (4, 4), 'level_4': (4, 4), 'level_8': (4, 4),
                 'synonym_antonym_match': (4, 4), 'word_family': (4, 4)}
DECLINES = {'level_1': 'no_minimal_pairs', 'level_4': 'no_inflection', 'level_8': 'no_collocation',
            'level_5': 'no_collocation', 'synonym_antonym_match': 'no_relation', 'word_family': 'no_family'}


def fatseed_problems(prof, doc):
    errs = []
    tx = Text(prof)
    extra_blocks = {r['type_code'] for r in prof.get('ladder') or [] if r.get('status') == 'new'
                    and r.get('generator') == 'llm'}
    if not isinstance(doc, dict):
        return ['not an object']
    core = doc.get('core') or {}
    if not str(doc.get('lemma') or '').strip():
        errs.append('lemma: missing')
    if not str(core.get('definition') or '').strip():
        errs.append('core.definition: missing')
    sents = core.get('sentences') or []
    if len(sents) != 10:
        errs.append(f'core.sentences: {len(sents)} (exactly 10)')
    texts = []
    for i, s in enumerate(sents):
        if not isinstance(s, dict):
            errs.append(f'core.sentences[{i}]: an object with text and target_word')
            continue
        tx.check(s.get('text'), f'core.sentences[{i}].text', errs)
        tw = str(s.get('target_word') or '')
        if not tw or not re.search(r'(?<!\w)' + re.escape(tw) + r'(?!\w)', str(s.get('text') or '')):
            errs.append(f'core.sentences[{i}]: target_word {tw!r} is not a whole word of the sentence')
        texts.append(tx.norm(s.get('text')))
    if len(set(texts)) != len(texts):
        errs.append('core.sentences: two are the same')
    variants = doc.get('variants') or {}
    if set(variants) != {'A', 'B'}:
        errs.append('variants: exactly A and B')
    pools = {}
    for v, blocks in variants.items():
        pool = pools.setdefault(v, set())
        for name, b in (blocks or {}).items():
            lab = f'{v}.{name}'
            if not isinstance(b, dict):
                errs.append(f'{lab}: an object')
                continue
            if 'declined' in b:
                if DECLINES.get(name) != b['declined'] and name not in extra_blocks:
                    errs.append(f'{lab}: cannot be declined with {b["declined"]!r}')
                continue
            if name in OPTION_BLOCKS or name in extra_blocks:
                lo, hi = OPTION_BLOCKS.get(name, (3, 6))
                opts = b.get('options') or []
                if not lo <= len(opts) <= hi:
                    errs.append(f'{lab}: {len(opts)} options ({lo} to {hi})')
                if sum(1 for o in opts if isinstance(o, dict) and o.get('is_correct') is True) != 1:
                    errs.append(f'{lab}: exactly one correct option')
                for o in opts:
                    if not isinstance(o, dict) or not str(o.get('text') or '').strip() \
                            or len(str(o.get('explanation') or '')) < 12:
                        errs.append(f'{lab}: every option needs text and a real explanation')
                        break
                    if not o.get('is_correct'):
                        pool.add((name, tx.norm(o['text'])))
                if len({tx.norm(str(o.get('text'))) for o in opts if isinstance(o, dict)}) != len(opts):
                    errs.append(f'{lab}: two options are the same')
            elif name == 'level_6':
                ws = b.get('wrong_sentences') or []
                if len(ws) != 3 or not isinstance(b.get('correct_sentence_index'), int):
                    errs.append(f'{lab}: correct_sentence_index and 3 wrong_sentences')
                for w in ws:
                    tx.check((w or {}).get('text'), f'{lab}.wrong_sentences.text', errs)
                    if len(str((w or {}).get('explanation') or '')) < 12:
                        errs.append(f'{lab}: every wrong sentence needs an explanation')
                    pool.add((name, tx.norm((w or {}).get('text'))))
            elif name == 'level_7':
                inc, cor = b.get('incorrect_sentence'), b.get('corrected_sentence')
                tx.check(inc, f'{lab}.incorrect_sentence', errs)
                tx.check(cor, f'{lab}.corrected_sentence', errs)
                if tx.norm(inc) == tx.norm(cor):
                    errs.append(f'{lab}: the two sentences must differ')
                if len(str(b.get('error_description') or '')) < 12:
                    errs.append(f'{lab}: error_description')
                pool.add((name, tx.norm(inc)))
            else:
                errs.append(f'{lab}: unknown block (not a shared block and not a "new" llm row of the ladder)')
    if set(pools) == {'A', 'B'}:
        shared = pools['A'] & pools['B']
        total = max(1, min(len(pools['A']), len(pools['B'])))
        if len(shared) / total > 0.25:
            errs.append(f'A and B share {len(shared)} of {total} distractors / wrong sentences; write B independently')
    return errs


def cmd_validate_fatseed(a):
    prof = load_profile(a.lang)
    path = resolve(a.lang, a.path, 'fat_seed/words')
    try:
        doc = load_json(path)
    except ValueError as e:
        return report(path, [f'not JSON: {e}'])
    return report(path, fatseed_problems(prof, doc))


# --------------------------------------------------------------------------
# comprehension tests (contract: .claude/skills/new-language-swarm/TEST_SPEC.md)

TEST_TIERS = {1: (35, 70), 2: (70, 120), 3: (120, 190), 4: (190, 280), 5: (280, 400), 6: (400, 650)}
TIER_DIFFICULTY = {1: 1, 2: 3, 3: 5, 4: 6, 5: 7, 6: 9}
QUESTION_TYPES = ('literal_detail', 'vocabulary_context', 'main_idea', 'supporting_detail', 'inference',
                  'author_purpose')
TIER_QUESTION_TYPES = {1: QUESTION_TYPES[:2], 2: QUESTION_TYPES[:4]}
HIGHER_ORDER = ('main_idea', 'inference', 'author_purpose')
CATEGORIES = ('Business & Commerce', 'Cuisine & Food', 'Family', 'Education', 'Work & Careers', 'Health & Medicine',
              'Transportation', 'Architecture', 'Environment', 'Sports & Recreation', 'Language & Literature',
              'Science & Technology', 'Fashion', 'Music & Performance', 'Art & Design', 'History', 'Agriculture')
STYLES = ('academic', 'conversational')
TEST_EXTRA_CHARS = '0123456789%€°/'
SLUG_RE = re.compile(r'^[a-z]{2}-t[1-6]-[a-z0-9]+(?:-[a-z0-9]+)*$')


def test_text(tx, s, label, errs):
    """Passage text: the profile's characters plus digits and a few symbols (passages are read aloud by TTS)."""
    if not isinstance(s, str) or not s.strip():
        errs.append(f'{label}: missing')
        return
    if s != s.strip() or '  ' in s:
        errs.append(f'{label}: stray spaces')
    if unicodedata.normalize('NFC', s) != s:
        errs.append(f'{label}: not NFC-normalised')
    bad = sorted({c for c in s if c not in TEST_EXTRA_CHARS and not tx.allowed.match(c)})
    if bad:
        errs.append(f'{label}: characters outside the profile: {"".join(bad)!r}')


def test_plan_path(lang, tier):
    return P(lang, 'tests', 'plan', f't{tier}.json')


def test_plan_problems(lang, path):
    errs = []
    try:
        plan = load_json(path)
    except ValueError as e:
        return [f'not JSON: {e}'], 0
    m = re.match(r'^t([1-6])\.json$', os.path.basename(path))
    tier = int(m.group(1)) if m else None
    if not m or plan.get('tier') != tier:
        errs.append('file name must be t<tier>.json and "tier" must match')
    slugs, topics, n = set(), set(), 0
    cats = Counter()
    for b in plan.get('batches') or []:
        if not re.match(rf'^t{tier}-\d{{2}}$', str(b.get('id'))):
            errs.append(f'batch id {b.get("id")!r}: must be t{tier}-NN')
        if not b.get('tests'):
            errs.append(f'batch {b.get("id")}: no tests')
        for t in b.get('tests') or []:
            n += 1
            lab = f'{b.get("id")} {t.get("slug")}'
            slug = t.get('slug')
            if not isinstance(slug, str) or not SLUG_RE.match(slug) or not slug.startswith(f'{lang}-t{tier}-'):
                errs.append(f'{lab}: slug must look like {lang}-t{tier}-short-topic')
            if slug in slugs:
                errs.append(f'{lab}: slug used twice')
            slugs.add(slug)
            if t.get('category') not in CATEGORIES:
                errs.append(f'{lab}: category must be one of the 17 app categories')
            cats[t.get('category')] += 1
            if t.get('style') not in STYLES:
                errs.append(f'{lab}: style must be one of {STYLES}')
            topic = str(t.get('topic') or '')
            if len(topic) < 40:
                errs.append(f'{lab}: topic must say what the passage is about (40+ characters)')
            if topic.lower() in topics:
                errs.append(f'{lab}: same topic text as another test')
            topics.add(topic.lower())
    if n >= 12 and len(cats) < min(17, max(6, n // 4)):
        errs.append(f'only {len(cats)} categories used; spread the tests over the app categories')
    if n >= 12 and max(cats.values()) > max(3, 0.15 * n):
        errs.append(f'category {cats.most_common(1)[0][0]!r} has {cats.most_common(1)[0][1]} of {n} tests; spread them')
    return errs, n


def cmd_validate_test_plan(a):
    path = resolve(a.lang, a.path, 'tests/plan')
    errs, n = test_plan_problems(a.lang, path)
    return report(path, errs, n, 'tests')


def planned_tests(lang, batch_id):
    tier = int(batch_id[1])
    path = test_plan_path(lang, tier)
    if not os.path.exists(path):
        return None
    for b in load_json(path).get('batches') or []:
        if b.get('id') == batch_id:
            return b.get('tests') or []
    return None


def one_test_problems(t, tx, lang):
    errs = []
    if not isinstance(t, dict):
        return ['not an object']
    slug, tier = t.get('slug'), t.get('tier')
    if not isinstance(slug, str) or not SLUG_RE.match(slug):
        errs.append('slug: must look like <lang>-t<tier>-short-topic')
    if tier not in TEST_TIERS:
        return errs + ['tier: 1 to 6']
    if isinstance(slug, str) and not slug.startswith(f'{lang}-t{tier}-'):
        errs.append(f'slug: must start with {lang}-t{tier}-')
    if t.get('category') not in CATEGORIES:
        errs.append('category: one of the 17 app categories')
    if t.get('style') not in STYLES:
        errs.append(f'style: one of {STYLES}')
    test_text(tx, t.get('title'), 'title', errs)
    for f in ('title_en', 'topic'):
        if not str(t.get(f) or '').strip():
            errs.append(f'{f}: missing')
    sents = t.get('sentences') or []
    words = 0
    for i, s in enumerate(sents):
        if not isinstance(s, dict):
            errs.append(f'sentences[{i}]: an object with tl and en')
            continue
        test_text(tx, s.get('tl'), f'sentences[{i}].tl', errs)
        if not str(s.get('en') or '').strip():
            errs.append(f'sentences[{i}].en: missing')
        if set(s) - {'tl', 'en', 'speaker'}:
            errs.append(f'sentences[{i}]: unknown fields {sorted(set(s) - {"tl", "en", "speaker"})}')
        if t.get('style') == 'conversational' and not str(s.get('speaker') or '').strip():
            errs.append(f'sentences[{i}]: a conversational passage names the speaker of every sentence')
        words += len(str(s.get('tl') or '').split())
    lo, hi = TEST_TIERS[tier]
    if not lo <= words <= hi:
        errs.append(f'passage: {words} words (tier {tier} takes {lo} to {hi})')
    if len(sents) < 4:
        errs.append('sentences: at least 4')
    qs = t.get('questions') or []
    want = 4 if tier == 1 else 5
    if len(qs) != want:
        errs.append(f'questions: {len(qs)} (tier {tier} takes exactly {want})')
    allowed_types = TIER_QUESTION_TYPES.get(tier, QUESTION_TYPES)
    types = []
    for i, q in enumerate(qs):
        lab = f'questions[{i}]'
        if not isinstance(q, dict):
            errs.append(f'{lab}: an object')
            continue
        if q.get('type') not in allowed_types:
            errs.append(f'{lab}: type must be one of {allowed_types} at tier {tier}')
        types.append(q.get('type'))
        test_text(tx, q.get('text'), f'{lab}.text', errs)
        ch = q.get('choices')
        if not (isinstance(ch, list) and len(ch) == 4 and all(isinstance(c, str) and c.strip() for c in ch)):
            errs.append(f'{lab}: exactly 4 choices')
        else:
            for c in ch:
                test_text(tx, c, f'{lab}.choices', errs)
            if len({tx.norm(c) for c in ch}) != 4:
                errs.append(f'{lab}: two choices are the same')
            lens = [len(c) for c in ch]
            ans = q.get('answer')
            if isinstance(ans, int) and 0 <= ans < 4 and lens[ans] > 1.6 * max(x for j, x in enumerate(lens) if j != ans) \
                    and lens[ans] > 25:
                errs.append(f'{lab}: the correct choice is much longer than every other; it gives itself away')
        ans = q.get('answer')
        if not (isinstance(ans, int) and not isinstance(ans, bool) and 0 <= ans < 4):
            errs.append(f'{lab}: answer is the index (0-3) of the correct choice')
        ev = q.get('evidence')
        if not (isinstance(ev, list) and all(isinstance(x, int) and 0 <= x < len(sents) for x in ev)):
            errs.append(f'{lab}: evidence is a list of sentence indexes')
        elif not ev and q.get('type') not in ('main_idea', 'author_purpose'):
            errs.append(f'{lab}: name the sentence(s) that decide the answer')
        if len(str(q.get('explanation') or '')) < 40:
            errs.append(f'{lab}: explanation (English, 40+ characters: why the key is right and the others are not)')
        if set(q) - {'type', 'text', 'choices', 'answer', 'evidence', 'explanation'}:
            errs.append(f'{lab}: unknown fields')
    if len(set(types)) < 2:
        errs.append('questions: at least two question types')
    if tier >= 3 and not set(types) & set(HIGHER_ORDER):
        errs.append('questions: from tier 3 at least one of main_idea, inference, author_purpose')
    vocab = t.get('vocab') or []
    if not 5 <= len(vocab) <= 14:
        errs.append(f'vocab: {len(vocab)} entries (5 to 14 teachable words of the passage)')
    for i, v in enumerate(vocab):
        if not isinstance(v, dict) or not str(v.get('lemma') or '').strip() or v.get('pos') not in POS \
                or not str(v.get('en') or '').strip():
            errs.append(f'vocab[{i}]: lemma, pos (the tool\'s list) and en')
    extra = set(t) - {'slug', 'tier', 'category', 'topic', 'style', 'title', 'title_en', 'sentences', 'questions',
                      'vocab'}
    if extra:
        errs.append('unknown fields: ' + ', '.join(sorted(extra)))
    return errs


def test_batch_problems(lang, path, tx):
    m = re.match(r'^(t[1-6]-\d{2})\.jsonl$', os.path.basename(path))
    problems, tests = [], []
    if not m:
        problems.append('file name must be t<tier>-NN.jsonl')
    planned = planned_tests(lang, m.group(1)) if m else None
    if m and planned is None:
        problems.append(f'batch {m.group(1)} is not in tests/plan/')
    seen, answers = {}, Counter()
    for n, obj, err in read_jsonl(path):
        if err:
            problems.append(f'line {n}: {err}')
            continue
        slug = obj.get('slug', '?') if isinstance(obj, dict) else '?'
        errs = one_test_problems(obj, tx, lang)
        if slug in seen:
            errs.append(f'slug: duplicate of line {seen[slug]}')
        seen.setdefault(slug, n)
        if isinstance(obj, dict):
            tests.append(obj)
            if m and obj.get('tier') != int(m.group(1)[1]):
                errs.append('tier: does not match the batch')
            for q in obj.get('questions') or []:
                if isinstance(q, dict) and isinstance(q.get('answer'), int):
                    answers[q['answer']] += 1
        problems += [f'line {n} ({slug}): {e}' for e in errs]
    if planned is not None:
        want, got = [t['slug'] for t in planned], [t.get('slug') for t in tests]
        missing = [s for s in want if s not in got]
        extra = [s for s in got if s not in want]
        if extra:
            problems.append('slugs not in the plan: ' + ', '.join(map(str, extra)))
        if len(missing) > max(1, len(want) // 5):
            problems.append('planned tests missing: ' + ', '.join(missing))
    total = sum(answers.values())
    if total >= 16 and answers.most_common(1)[0][1] > 0.4 * total:
        problems.append(f'answer positions: index {answers.most_common(1)[0][0]} is the key in '
                        f'{answers.most_common(1)[0][1]} of {total} questions; spread them')
    return tests, problems


def cmd_validate_tests(a):
    prof = load_profile(a.lang)
    path = resolve(a.lang, a.path, 'tests/batches')
    tests, problems = test_batch_problems(a.lang, path, Text(prof))
    return report(path, problems, len(tests), 'tests')


def tests_blind_paths(lang, path, tag=''):
    name = os.path.basename(path)[:-6] + (f'.{tag}' if tag else '')
    d = P(lang, 'tests', 'blind')
    return {k: os.path.join(d, f'{name}.{k}.jsonl') for k in ('nopassage', 'passage', 'answers_nopassage', 'answers')}


def cmd_tests_strip(a):
    path = resolve(a.lang, a.path, 'tests/batches')
    bp = tests_blind_paths(a.lang, path, a.tag)
    os.makedirs(os.path.dirname(bp['passage']), exist_ok=True)
    rows = [o for _, o, e in read_jsonl(path) if not e and isinstance(o, dict)]
    with open(bp['nopassage'], 'w', encoding='utf-8') as f1, open(bp['passage'], 'w', encoding='utf-8') as f2:
        for t in rows:
            qs = [{'text': q.get('text'), 'choices': q.get('choices')} for q in t.get('questions') or []]
            f1.write(json.dumps({'slug': t.get('slug'), 'questions': qs}, ensure_ascii=False) + '\n')
            f2.write(json.dumps({'slug': t.get('slug'), 'title': t.get('title'),
                                 'passage': [s.get('tl') for s in t.get('sentences') or []], 'questions': qs},
                                ensure_ascii=False) + '\n')
    for k in ('nopassage', 'passage'):
        print(f'wrote {os.path.relpath(bp[k], ROOT)}')
    print(f'answers without the passage -> {os.path.relpath(bp["answers_nopassage"], ROOT)}')
    print(f'answers with the passage    -> {os.path.relpath(bp["answers"], ROOT)}')
    return 0


def cmd_tests_compare(a):
    path = resolve(a.lang, a.path, 'tests/batches')
    bp = tests_blind_paths(a.lang, path, a.tag)
    for k in ('answers_nopassage',) if a.cold_only else ('answers_nopassage', 'answers'):
        if not os.path.exists(bp[k]):
            print(f'no answers file at {os.path.relpath(bp[k], ROOT)}')
            return 2
    tests = {o['slug']: o for _, o, e in read_jsonl(path) if not e and isinstance(o, dict) and 'slug' in o}
    cold = {o.get('slug'): o.get('answers') for _, o, e in read_jsonl(bp['answers_nopassage']) if not e}
    warm = {} if a.cold_only else {o.get('slug'): o.get('answers') for _, o, e in read_jsonl(bp['answers']) if not e}
    flags, n_q, guessed, guessable = [], 0, 0, 0
    for slug, t in tests.items():
        for i, q in enumerate(t.get('questions') or []):
            n_q += 1
            key = q.get('answer')
            w = (warm.get(slug) or [None] * (i + 1))[i] if i < len(warm.get(slug) or []) else None
            c = (cold.get(slug) or [None] * (i + 1))[i] if i < len(cold.get(slug) or []) else None
            lab = f'{slug} q{i + 1} ({q.get("type")})'
            if a.cold_only:
                pass
            elif not isinstance(w, list):
                flags.append(f'{lab}: no answer with the passage')
            elif key not in w:
                flags.append(f'{lab}: KEY REJECTED: key {key}, solver accepted {w}')
            elif len(w) > 1:
                flags.append(f'{lab}: AMBIGUOUS: solver also accepted {[x for x in w if x != key]}')
            if q.get('type') != 'vocabulary_context':
                guessable += 1
                if c == key:
                    guessed += 1
                    flags.append(f'{lab}: GUESSABLE: answered right without the passage')
    print(f'{len(tests)} tests, {n_q} questions, {len(flags)} flags; answered right without the passage: '
          f'{guessed} of {guessable} (chance is 25%)')
    for f in flags:
        print('  ' + f)
    return 0


def reviewed_tests(lang):
    d = P(lang, 'tests', 'reviewed')
    out = []
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if re.match(r'^t[1-6]-\d{2}\.jsonl$', name):
            out += [(name, o) for _, o, e in read_jsonl(os.path.join(d, name)) if not e and isinstance(o, dict)]
    return out


def cmd_tests_export(a):
    """tests/final.jsonl: every reviewed test that passes, once per slug, with the derived fields the app stores."""
    tx = Text(load_profile(a.lang))
    seen, out, bad, dup = set(), [], 0, 0
    for _, t in reviewed_tests(a.lang):
        if one_test_problems(t, tx, a.lang):
            bad += 1
            continue
        if t['slug'] in seen:
            dup += 1
            continue
        seen.add(t['slug'])
        row = dict(t)
        row['difficulty'] = TIER_DIFFICULTY[t['tier']]
        row['transcript'] = ' '.join(s['tl'] for s in t['sentences'])
        out.append(row)
    with open(P(a.lang, 'tests', 'final.jsonl'), 'w', encoding='utf-8') as fh:
        for row in out:
            fh.write(json.dumps(row, ensure_ascii=False) + '\n')
    tiers = Counter(r['tier'] for r in out)
    print(f'{len(out)} tests in tests/final.jsonl ({", ".join(f"T{k}: {tiers[k]}" for k in sorted(tiers))}); '
          f'{bad} invalid and {dup} repeated slugs left out')
    return 0


def cmd_lexicon_dedupe(a):
    """Parallel curators repeat lemmas: keep the first (lowest file, then line) of each lemma + pos, drop the rest."""
    d = P(a.lang, 'lexicon')
    seen, changed = {}, 0
    for name in sorted(os.listdir(d)):
        if not re.match(r'^lexicon(_\d+)?\.jsonl$', name):
            continue
        path, lines, touched = os.path.join(d, name), [], False
        for n, o, e in read_jsonl(path):
            if e:
                continue
            if isinstance(o, dict) and not o.get('drop'):
                key = (str(o.get('lemma')).lower(), o.get('pos'))
                if key in seen:
                    o = {'lemma': o.get('lemma'), 'drop': True, 'reason': f'already in {seen[key]}'}
                    touched = True
                    changed += 1
                else:
                    seen[key] = name
            lines.append(json.dumps(o, ensure_ascii=False))
        if touched:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write('\n'.join(lines) + '\n')
    print(f'{changed} repeated lemma + pos rows marked dropped; {len(seen)} lemmas kept')
    return 0


# --------------------------------------------------------------------------
# archive: the bulky parts of a pack are committed as compressed tarballs

ARCHIVE_PARTS = {
    'lexicon': ['lexicon'],
    'senses': ['senses'],
    'dictionaries': ['dictionaries'],
    'grammar_work': ['grammar/batches', 'grammar/blind', 'grammar/verdicts'],
    'grammar_reviewed': ['grammar/reviewed'],
    'grammar_built': ['grammar/built'],
    'tests_work': ['tests/batches', 'tests/blind', 'tests/verdicts'],
    'tests_reviewed': ['tests/reviewed', 'tests/final.jsonl'],
    'fat_seed': ['fat_seed'],
}


def cmd_archive(a):
    """Write archive/<part>.tar.gz for each bulky part. Same content gives the same bytes (sorted, no timestamps)."""
    import gzip
    import io
    import tarfile
    out_dir = P(a.lang, 'archive')
    os.makedirs(out_dir, exist_ok=True)
    manifest = {}
    for part, rels in ARCHIVE_PARTS.items():
        files = []
        for rel in rels:
            path = P(a.lang, *rel.split('/'))
            if os.path.isfile(path):
                files.append(path)
            for base, dirs, names in os.walk(path) if os.path.isdir(path) else []:
                dirs.sort()
                files += [os.path.join(base, n) for n in sorted(names)]
        if not files:
            continue
        raw = io.BytesIO()
        with tarfile.open(fileobj=raw, mode='w') as tar:
            for f in sorted(files):
                info = tarfile.TarInfo(os.path.relpath(f, pack_dir(a.lang)).replace(os.sep, '/'))
                data = open(f, 'rb').read()
                info.size, info.mtime, info.mode = len(data), 0, 0o644
                tar.addfile(info, io.BytesIO(data))
        target = os.path.join(out_dir, part + '.tar.gz')
        with open(target, 'wb') as fh, gzip.GzipFile(fileobj=fh, mode='wb', mtime=0, compresslevel=9, filename='') as gz:
            gz.write(raw.getvalue())
        manifest[part] = {'files': len(files), 'bytes': raw.getbuffer().nbytes, 'gz_bytes': os.path.getsize(target)}
        print(f'{part}: {len(files)} files, {raw.getbuffer().nbytes / 1e6:.2f} MB -> {os.path.getsize(target) / 1e6:.2f} MB')
    with open(os.path.join(out_dir, 'MANIFEST.json'), 'w', encoding='utf-8') as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
    return 0


def cmd_unarchive(a):
    """Extract archive/*.tar.gz into the pack. Existing files are kept unless --force."""
    import tarfile
    d = P(a.lang, 'archive')
    wrote = kept = 0
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not name.endswith('.tar.gz'):
            continue
        with tarfile.open(os.path.join(d, name)) as tar:
            for m in tar.getmembers():
                target = os.path.normpath(os.path.join(pack_dir(a.lang), m.name))
                if not target.startswith(os.path.normpath(pack_dir(a.lang)) + os.sep) or not m.isfile():
                    continue
                if os.path.exists(target) and not a.force:
                    kept += 1
                    continue
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, 'wb') as fh:
                    fh.write(tar.extractfile(m).read())
                wrote += 1
    print(f'extracted {wrote} files; {kept} existing files kept')
    return 0


# --------------------------------------------------------------------------
# status

def count_lines(paths):
    return sum(sum(1 for _, o, e in read_jsonl(p) if not e) for p in paths)


def status(lang):
    prof = load_profile(lang)
    tx = Text(prof)
    out = {'language': lang, 'profile_problems': len(profile_problems(prof, lang))}
    rows = lexicon_rows(lang)
    out['lexicon'] = {'kept': sum(1 for _, _, o, e in rows if not e and isinstance(o, dict) and not o.get('drop')),
                      'dropped': sum(1 for _, _, o, e in rows if not e and isinstance(o, dict) and o.get('drop')),
                      'target': prof.get('targets', {}).get('lexicon')}
    sd = P(lang, 'senses')
    names = os.listdir(sd) if os.path.isdir(sd) else []
    final = load_json(os.path.join(sd, 'final.json')) if 'final.json' in names else []
    out['senses'] = {'written_batches': sum(n.endswith('.out.json') for n in names),
                     'reviewed_batches': sum(n.endswith('.reviewed.json') for n in names),
                     'final': len(final), 'target': prof.get('targets', {}).get('senses')}
    out['dictionaries'] = {d['key']: {'rows': count_lines(dict_files(lang, d['key'])),
                                      'reviewed_rows': count_lines(dict_files(lang, d['key'], True)),
                                      'target': d.get('target')}
                           for d in prof.get('dictionaries') or []}
    g = {'topics': 0, 'guides': 0, 'batches_planned': 0, 'batches_written': 0, 'batches_reviewed': 0,
         'items_reviewed_valid': 0, 'target': prof.get('targets', {}).get('grammar_items')}
    if os.path.exists(P(lang, 'grammar', 'plan.json')):
        plan = load_plan(lang)
        g['topics'] = len(plan['topics'])
        g['batches_planned'] = sum(t.get('batches', 0) for t in plan['topics'])
        g['guides'] = sum(1 for t in plan['topics'] if load_guide(lang, t['slug']))
        for sub, key in (('batches', 'batches_written'), ('reviewed', 'batches_reviewed')):
            d = P(lang, 'grammar', sub)
            g[key] = sum(1 for n in os.listdir(d) if batch_topic(n, plan)[0]) if os.path.isdir(d) else 0
        for path in source_files(lang, plan):
            slug, _ = batch_topic(path, plan)
            guide = load_guide(lang, slug)
            subs = [s['key'] for s in guide.get('subs', [])] if guide else None
            g['items_reviewed_valid'] += sum(1 for _, o, e in read_jsonl(path)
                                             if not e and not item_problems(o, subs, slug, tx))
    out['grammar'] = g
    fs = {}
    for sub in ('words', 'reviewed'):
        d = P(lang, 'fat_seed', sub)
        docs = [n for n in os.listdir(d) if n.endswith('.json')] if os.path.isdir(d) else []
        fs[sub] = len(docs)
        fs[sub + '_valid'] = sum(1 for n in docs if not fatseed_problems(prof, load_json(os.path.join(d, n))))
    out['fat_seed'] = fs
    tx_t = Text(prof)
    rv = reviewed_tests(lang)
    valid = [t for _, t in rv if not one_test_problems(t, tx_t, lang)]
    td = P(lang, 'tests', 'batches')
    out['tests'] = {'batches_written': len([n for n in os.listdir(td) if n.endswith('.jsonl')]) if os.path.isdir(td) else 0,
                    'batches_reviewed': len({n for n, _ in rv}), 'reviewed': len(rv), 'valid': len(valid),
                    'by_tier': dict(sorted(Counter(t['tier'] for t in valid).items())),
                    'target': prof.get('targets', {}).get('tests')}
    wd = P(lang, 'wiring')
    out['wiring_files'] = sorted(os.listdir(wd)) if os.path.isdir(wd) else []
    return out


def cmd_status(a):
    st = status(a.lang)
    if a.json:
        print(json.dumps(st, ensure_ascii=False, indent=1))
        return 0
    print(f'language pack {a.lang}: profile problems {st["profile_problems"]}')
    lx, se, g, fs = st['lexicon'], st['senses'], st['grammar'], st['fat_seed']
    print(f'  lexicon      {lx["kept"]} lemmas kept, {lx["dropped"]} dropped (target {lx["target"]})')
    print(f'  senses       {se["final"]} final; batches written {se["written_batches"]}, reviewed '
          f'{se["reviewed_batches"]} (target {se["target"]})')
    for key, d in st['dictionaries'].items():
        print(f'  dictionary   {key}: {d["rows"]} rows written, {d["reviewed_rows"]} reviewed (target {d["target"]})')
    print(f'  grammar      {g["topics"]} topics, {g["guides"]} guides; batches planned {g["batches_planned"]}, '
          f'written {g["batches_written"]}, reviewed {g["batches_reviewed"]}; {g["items_reviewed_valid"]} valid '
          f'reviewed items (target {g["target"]})')
    print(f'  fat seed     {fs["words"]} authored ({fs["words_valid"]} valid), {fs["reviewed"]} reviewed '
          f'({fs["reviewed_valid"]} valid)')
    t = st['tests']
    print(f'  tests        {t["valid"]} valid reviewed tests {t["by_tier"]}; batches written {t["batches_written"]}, '
          f'reviewed {t["batches_reviewed"]} (target {t["target"]})')
    print(f'  wiring       {", ".join(st["wiring_files"]) or "nothing yet"}')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)

    def add(name, fn, *extra):
        p = sub.add_parser(name)
        p.add_argument('lang')
        for args, kw in extra:
            p.add_argument(*args, **kw)
        p.set_defaults(fn=fn)

    path = (('path',), {})
    add('init', cmd_init, (('--name',), {'required': True}), (('--native',), {'required': True}))
    add('validate-profile', cmd_validate_profile)
    add('lexicon-candidates', cmd_lexicon_candidates, (('--top',), {'type': int, 'default': 8000}),
        (('--word-regex',), {'default': r"^[^\W\d_]{2,}$"}))
    add('validate-lexicon', cmd_validate_lexicon)
    add('validate-senses', cmd_validate_senses, path)
    add('merge-senses', cmd_merge_senses)
    add('sense-batches', cmd_sense_batches, (('--size',), {'type': int, 'default': 25}),
        (('--limit',), {'type': int, 'default': 0}))
    add('fatseed-worklist', cmd_fatseed_worklist, (('--n',), {'type': int, 'default': 12}),
        (('--function-words',), {'action': 'store_true'}))
    add('validate-dict', cmd_validate_dict, (('key',), {}), (('--reviewed',), {'action': 'store_true'}))
    add('validate-plan', cmd_validate_plan)
    add('validate-guide', cmd_validate_guide, path)
    add('validate-batch', cmd_validate_batch, path, (('--min-items',), {'type': int, 'default': None}))
    add('strip', cmd_strip, path)
    add('compare', cmd_compare, path)
    add('validate-fatseed', cmd_validate_fatseed, path)
    add('build', cmd_build, (('--check',), {'action': 'store_true'}), (('--static',), {'action': 'store_true'}))
    add('validate-test-plan', cmd_validate_test_plan, path)
    add('validate-tests', cmd_validate_tests, path)
    tag = (('--tag',), {'default': ''})
    add('tests-strip', cmd_tests_strip, path, tag)
    add('tests-compare', cmd_tests_compare, path, tag, (('--cold-only',), {'action': 'store_true'}))
    add('tests-export', cmd_tests_export)
    add('lexicon-dedupe', cmd_lexicon_dedupe)
    add('archive', cmd_archive)
    add('unarchive', cmd_unarchive, (('--force',), {'action': 'store_true'}))
    add('status', cmd_status, (('--json',), {'action': 'store_true'}))
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == '__main__':
    sys.exit(main())
