"""Tool-free fat-seed review that returns patches instead of documents.

The reviewer model gets the judge rules, each authored document and its plan in
the prompt, has no tools, and replies with a verdict plus JSON-Patch edits per
sense. This script applies the patches, writes reviewed/ and review/ into an
output run directory, runs `check --source reviewed`, and sends failures back
for one patch-only repair.

    python3 scratch_offline/nt_review.py SRC_RUN OUT_RUN [--model opus] [--batch 4]

OUT_RUN gets a copy of SRC_RUN's inputs (words, plans, senses.csv, ...), so the
review can run beside an existing review of the same documents.
"""
import argparse
import copy
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nt_author import REPO, runner, load, save, compact_plan  # noqa: E402

SKILL = os.path.join(REPO, '.claude/skills/fat-seed-review/SKILL.md')

SYSTEM = """You are the strict quality reviewer for vocabulary-ladder exercise
documents that someone else wrote for LinguaLoop (Japanese). You have no tools.
Reply with ONE fenced ```json block and nothing else.

Standards: the live judge prompts below (ignore their output formats) and the
checklist after them. Be strict: a review that finds nothing in several
documents almost certainly did not look. Never edit a sentence whose source is
"mined"; if one is unusable, say so in notes. A block of the form
{{"declined": "..."}} is final: do not patch it and do not report it.

=== judge prompts ===
{judges}

=== checklist ===
{checklist}

=== output ===
For every sense return:
{{"<sense_id>": {{"verdict": "accept"|"rewrite"|"reject",
  "issues": [{{"path": "variants.A.level_3.options[2]", "problem": "…", "fix": "…"}}],
  "patches": [{{"op": "replace"|"add"|"remove", "path": "/variants/A/level_3/options/2", "value": …}}],
  "notes": "…"}}}}
- patches are RFC 6902 JSON-Patch operations against that sense's document
  (JSON Pointer paths, 0-based array indexes). Replace the smallest node that
  fixes the problem: an option object, a sentence object, a field. Do not
  resend unchanged content.
- accept: no patches. rewrite: at least one patch, every patch covered by an
  issue. reject: the core itself is unusable (no patches needed).
"""


def checklist():
    text = open(SKILL, encoding='utf-8').read()
    return text[text.index('## What to check'):text.index('## What you write')].strip()


# --core-only (Track B, additive): review nothing but the ten core sentences
# against the pinned sense. Core sense drift is the largest judged defect class
# of the Haiku author (b_norev100: 0.39 fatal + 0.76 major per sense in the core,
# a third of senses with a drifted sentence, and every block anchored on such a
# sentence inherits the defect). The variants are not shown and not patched in
# the first pass; the normal check / repair pass then fixes anchors.
CORE_ONLY = """
=== scope for this review ===
You see ONLY the core of each document plus the source of each sentence. Judge
every sentence against the given definition and sense_fingerprint:
- does it use the target as an independent word (not inside a compound, not a
  homograph or another reading) in exactly THIS sense?
- is it natural, grammatical Japanese a native speaker would write?
For each failing sentence whose source is "generated", return ONE patch that
replaces the whole sentence object at /core/sentences/<index> with a new
sentence of the same complexity_tier (similar length and grammar), using the
target in the pinned sense, with target_word set to the exact surface form in
the new text. Keep the same inflection class where possible (the exercises
anchored on that sentence need the same form). Never patch a "mined" sentence:
if one is unusable, say so in notes. Patch nothing else. "accept" with no
patches is the expected verdict when all ten sentences are fine.
"""

# --keep-options (Track B, additive): the full Haiku review introduced level_3
# "fits the blank" fatals (0.07 -> 0.11 per sense on gold100) by rewriting
# distractors into context-free ones. Option texts in the cloze/collocation
# blocks may only change when an issue names that option as a second fit or a
# non-word; other option-text patches are discarded (and logged in notes).
KEEP_OPTIONS = """
=== option texts ===
In level_3, level_5 and level_8 do not change an option's text unless your
issue for that exact option says that it also fits the blank (a second correct
answer) or that it is not a real word. When you do replace a distractor, the
issue must say why the NEW word cannot fit the blank. Explanations may be fixed
freely. Patches that change an option text without such an issue are discarded.
"""
_OPTION_BLOCKS = ('level_3', 'level_5', 'level_8')
_FIT_WORDS = re.compile(r'fits? (in )?the blank|also (be |a )?correct|second correct|also fits|also (works|acceptable|'
                        r'natural|grammatical)|not a (real )?word|non-?word|実在しない|正解にな|空欄に入|成り立つ|自然|もう一つの正解',
                        re.I)


def _option_texts(doc, v, block):
    opts = (((doc.get('variants') or {}).get(v) or {}).get(block) or {}).get('options') or []
    return [str(o.get('text', '')) if isinstance(o, dict) else '' for o in opts]


def keep_option_texts(doc, patches, issues):
    """Split patches into (kept, dropped): dropped = option-text changes in level_3/5/8 that no issue justifies."""
    kept, dropped = [], []
    for p in patches:
        path = str(p.get('path', '')) if isinstance(p, dict) else ''
        m = re.match(r'^/variants/(A|B)/(level_3|level_5|level_8)(.*)$', path)
        if not m:
            kept.append(p)
            continue
        v, block, tail = m.groups()
        orig = _option_texts(doc, v, block)
        val = p.get('value')
        changed = []
        if tail == '' and isinstance(val, dict):
            news = [str(o.get('text', '')) if isinstance(o, dict) else '' for o in (val.get('options') or [])]
            changed = [i for i, t in enumerate(news) if i >= len(orig) or t != orig[i]] or ([0] if len(news) != len(orig) else [])
        elif tail == '/options' and isinstance(val, list):
            news = [str(o.get('text', '')) if isinstance(o, dict) else '' for o in val]
            changed = [i for i, t in enumerate(news) if i >= len(orig) or t != orig[i]] or ([0] if len(news) != len(orig) else [])
        else:
            mi = re.match(r'^/options/(\d+|-)(?:/(\w+))?$', tail)
            if not mi:
                kept.append(p)
                continue
            i = len(orig) if mi.group(1) == '-' else int(mi.group(1))
            field = mi.group(2)
            if p.get('op') == 'remove' and field is None:
                changed = [i]
            elif field is None and isinstance(val, dict):
                if i >= len(orig) or str(val.get('text', '')) != orig[i]:
                    changed = [i]
            elif field == 'text':
                if i >= len(orig) or str(val) != orig[i]:
                    changed = [i]
        if not changed:
            kept.append(p)
            continue

        def justified(i):
            for it in issues:
                if not isinstance(it, dict) or f'{v}.{block}' not in str(it.get('path', '')):
                    continue
                text = f"{it.get('path', '')} {it.get('problem', '')} {it.get('fix', '')}"
                named = f'[{i}]' in str(it.get('path', '')) or (i < len(orig) and orig[i] and orig[i] in text)
                if named and _FIT_WORDS.search(text):
                    return True
            return False
        (kept if all(justified(i) for i in changed) else dropped).append(p)
    return kept, dropped


# --plain-core (Track B, additive): the fatal-only reviewer removes core fatals
# (0.39 -> 0.21/sense) but its replacement sentences add core majors (+0.22):
# unnatural or over-long rewrites. Constrain the replacements.
PLAIN_CORE = """
=== replacement core sentences ===
When you replace a core sentence, the new sentence must be short and plain
(tier T1-T3 grammar: plain or です/ます forms, no passive/causative/conditional
chains), use the target in exactly its given sense with a common, natural
collocation, keep the same complexity_tier label and the same inflection class
of the target, and set target_word to the exact surface form in the new text.
Never replace a sentence whose source is "mined".
"""

# --fatal-only (Track B, additive): a reviewer brief restricted to the defects
# that make an item unusable. A weak reviewer does its damage in style patches;
# fatal/sense is also the stable judge metric.
FATAL_ONLY = """
=== scope for this review ===
Report and patch ONLY defects that make an item unusable:
- a correct answer that is wrong, or a second option that is also correct or
  also fits the blank (read every distractor in the blank);
- a level_6 "wrong" sentence that is in fact acceptable Japanese in this sense,
  or whose error is not a misuse of the target;
- a level_7 pair where the incorrect sentence is acceptable, the corrected one
  is still wrong, or the error does not involve the target;
- a sentence a learner must read as correct that is ungrammatical or uses
  another sense of the word; an explanation that states something false.
Do not patch register, style, wording of explanations, or weak-but-valid
distractors; do not mention them. "accept" is the expected verdict for most
documents.
"""


def _parent(doc, path):
    parts = [p.replace('~1', '/').replace('~0', '~') for p in path.lstrip('/').split('/')]
    node = doc
    for p in parts[:-1]:
        node = node[int(p)] if isinstance(node, list) else node[p]
    return node, parts[-1]


def apply_patches(doc, patches):
    doc = copy.deepcopy(doc)
    # RFC 6902: operations apply in order, each against the result of the last.
    for p in patches:
        node, key = _parent(doc, p['path'])
        op = p['op']
        if isinstance(node, list):
            i = len(node) if key == '-' else int(key)
            if op == 'replace':
                node[i] = p['value']
            elif op == 'add':
                node.insert(i, p['value'])
            elif op == 'remove':
                del node[i]
        else:
            if op in ('replace', 'add'):
                node[key] = p['value']
            elif op == 'remove':
                node.pop(key, None)
    return doc


# ---------------------------------------------------------------------------
# Shape validation of patched blocks (Track B hardening, default on).
# A Haiku reviewer replaced a declined level_1 with {"exercise": ..., "correct":
# ..., "options": ["日記", ...]} (bare strings): the production checker's
# _remap_options crashes on string options, and a bare-string option in
# particle_selection passed `check` silently and reached the judge. Every patch
# is applied on its own and the blocks it touches are checked against the Block
# reference; a patch that leaves a malformed block is dropped and recorded.
# ---------------------------------------------------------------------------
try:
    sys.path.insert(0, REPO)
    from services.vocabulary_ladder.fat_seed import ESCAPE_TOKENS
except Exception:  # noqa: BLE001 — keep the reviewer usable without the services package
    ESCAPE_TOKENS = {'level_1': 'no_minimal_pairs', 'level_4': 'no_inflection', 'level_8': 'no_collocation',
                     'synonym_antonym_match': 'no_relation', 'word_family': 'no_family',
                     'particle_selection': 'no_particle_slot'}

OPTION_BLOCKS = ('level_1', 'level_3', 'level_4', 'level_5', 'level_8', 'synonym_antonym_match',
                 'word_family', 'particle_selection')
REQUIRED_FIELDS = {'level_4': ('base_form', 'form_label'), 'level_8': ('error_collocate',),
                   'synonym_antonym_match': ('relation',), 'word_family': ('stem',),
                   'particle_selection': ('blanked_particle', 'error_tags')}


def _text(x):
    return isinstance(x, str) and x.strip() != ''


def block_problem(name, block):
    """Why ``block`` does not have the Block-reference shape for ``name``; None when it does."""
    if not isinstance(block, dict):
        return 'block is not an object'
    if 'declined' in block:
        allowed = ESCAPE_TOKENS.get(name)
        if allowed is None:
            return 'this block cannot be declined'
        if block['declined'] not in (True, allowed):
            return f'declined token must be {allowed!r}'
        if set(block) - {'declined'}:
            return 'a declined block carries other fields'
        return None
    if name in OPTION_BLOCKS:
        opts = block.get('options')
        if not isinstance(opts, list) or not opts:
            return 'options must be a non-empty list of option objects'
        for i, o in enumerate(opts):
            if not isinstance(o, dict):
                return f'options[{i}] is not an object (text / is_correct / explanation)'
            if not _text(o.get('text')):
                return f'options[{i}] has no text'
            if not isinstance(o.get('is_correct'), bool):
                return f'options[{i}].is_correct must be true or false'
            if not _text(o.get('explanation')):
                return f'options[{i}] has no explanation'
            if name == 'word_family' and not _text(o.get('part_of_speech')):
                return f'options[{i}] has no part_of_speech'
        if sum(1 for o in opts if o.get('is_correct') is True) != 1:
            return 'exactly one option must be correct'
        for f in REQUIRED_FIELDS.get(name, ()):
            if block.get(f) in (None, ''):
                return f'missing {f}'
        if name == 'particle_selection':
            if not isinstance(block.get('error_tags'), dict):
                return 'error_tags must be an object'
            correct = [o['text'].strip() for o in opts if o.get('is_correct')]
            if correct and correct[0] != str(block.get('blanked_particle')).strip():
                return 'blanked_particle must equal the correct option'
        return None
    if name == 'level_6':
        if not isinstance(block.get('correct_sentence_index'), int):
            return 'correct_sentence_index must be an integer'
        ws = block.get('wrong_sentences')
        if not isinstance(ws, list) or not ws:
            return 'wrong_sentences must be a non-empty list'
        for i, w in enumerate(ws):
            if not isinstance(w, dict) or not _text(w.get('text')) or not _text(w.get('explanation')):
                return f'wrong_sentences[{i}] must be an object with text and explanation'
        return None
    if name == 'level_7':
        for f in ('incorrect_sentence', 'corrected_sentence', 'error_description'):
            if not _text(block.get(f)):
                return f'missing {f}'
        idx = block.get('correct_sentence_indices')
        if idx is not None and not (isinstance(idx, list) and all(isinstance(i, int) for i in idx)):
            return 'correct_sentence_indices must be a list of integers'
        return None
    return None  # unknown block names: `check` drops surplus blocks itself


def core_problem(core):
    if not isinstance(core, dict):
        return 'core is not an object'
    for i, sent in enumerate(core.get('sentences') or []):
        if not isinstance(sent, dict) or not _text(sent.get('text')) or not _text(sent.get('target_word')):
            return f'core.sentences[{i}] must be an object with text and target_word'
    for i, f in enumerate(core.get('morphological_forms') or []):
        if not isinstance(f, dict) or not _text(f.get('form')):
            return f'core.morphological_forms[{i}] must be an object with form'
    return None


def patched_problem(doc, path):
    """Validate whatever a patch at ``path`` can have changed in ``doc``."""
    parts = [p for p in str(path).split('/') if p != '']
    def variant_problems(v):
        blocks = (doc.get('variants') or {}).get(v)
        if not isinstance(blocks, dict):
            return f'variants.{v} is not an object'
        for name, b in blocks.items():
            prob = block_problem(name, b)
            if prob:
                return f'variants.{v}.{name}: {prob}'
        return None
    if not parts or parts[0] == 'variants' and len(parts) == 1:
        return core_problem(doc.get('core')) or variant_problems('A') or variant_problems('B')
    if parts[0] == 'core':
        return core_problem(doc.get('core'))
    if parts[0] == 'variants':
        v = parts[1]
        if len(parts) == 2:
            return variant_problems(v)
        name = parts[2]
        b = ((doc.get('variants') or {}).get(v) or {}).get(name) if isinstance((doc.get('variants') or {}).get(v), dict) else None
        if b is None:
            return None  # removed block: `check` reports it as missing
        prob = block_problem(name, b)
        return f'variants.{v}.{name}: {prob}' if prob else None
    return None


def apply_patches_checked(doc, patches):
    """Apply patches one at a time; drop any that fails or leaves a malformed block.

    Returns (document, rejected) where rejected lists {op, path, problem}.
    """
    cur = copy.deepcopy(doc)
    rejected = []
    for p in patches:
        if not isinstance(p, dict):
            rejected.append({'op': None, 'path': None, 'problem': 'patch is not an object'})
            continue
        try:
            nxt = apply_patches(cur, [p])
        except (KeyError, IndexError, ValueError, TypeError) as e:
            rejected.append({'op': p.get('op'), 'path': p.get('path'), 'problem': f'patch failed: {e}'})
            continue
        prob = patched_problem(nxt, p.get('path', ''))
        if prob:
            rejected.append({'op': p.get('op'), 'path': p.get('path'), 'problem': prob})
            continue
        cur = nxt
    return cur, rejected


def restore_declines(source, doc):
    """Blocks the source author declined stay declined (skip-l1 runs: the trie builds L1)."""
    restored = []
    for v, blocks in (source.get('variants') or {}).items():
        if not isinstance(blocks, dict):
            continue
        for name, b in blocks.items():
            if isinstance(b, dict) and b.get('declined'):
                cur = ((doc.get('variants') or {}).get(v) or {}).get(name) if isinstance((doc.get('variants') or {}).get(v), dict) else None
                if not (isinstance(cur, dict) and cur.get('declined')):
                    doc.setdefault('variants', {}).setdefault(v, {})[name] = copy.deepcopy(b)
                    restored.append(f'{v}.{name}')
    return restored


def setup_out(src, out):
    if os.path.abspath(src) == os.path.abspath(out):
        return
    for sub in ('words', 'plans', 'briefs'):
        s = os.path.join(src, 'fat_seed', sub)
        d = os.path.join(out, 'fat_seed', sub)
        if os.path.isdir(s) and not os.path.isdir(d):
            shutil.copytree(s, d)
    for f in ('senses.csv', 'prompts.json'):
        shutil.copy(os.path.join(src, f), os.path.join(out, f))
    for f in ('rules_judges.md', 'rules_core.md', 'rules_exercises.md'):
        s = os.path.join(src, 'fat_seed', f)
        if os.path.exists(s):
            shutil.copy(s, os.path.join(out, 'fat_seed', f))


def review(args, system, sids, tag, errors=None):
    from nt_author import call_model
    if errors is None and getattr(args, 'resume', False):
        # --resume (Track B, additive): skip senses already reviewed by an interrupted run
        sids = [s for s in sids
                if not (os.path.exists(os.path.join(args.out, 'fat_seed', 'reviewed', f'{s}.json'))
                        and os.path.exists(os.path.join(args.out, 'fat_seed', 'review', f'{s}.json')))]
    for i in range(0, len(sids), args.batch):
        batch = sids[i:i + args.batch]
        parts = []
        for sid in batch:
            src = 'reviewed' if errors else 'words'
            doc = load(os.path.join(args.out, 'fat_seed', src, f'{sid}.json'))
            plan = load(os.path.join(args.out, 'fat_seed', 'plans', f'{sid}.json'))
            if getattr(args, 'core_only', False) and not errors:
                shown = {k: doc.get(k) for k in ('sense_id', 'lemma', 'core')}
                sources = [s[:1] + s[2:] for s in plan.get('sentences', [])]  # [index, target, source]
                block = (f'### sense {sid}\ncore:\n```json\n{json.dumps(shown, ensure_ascii=False)}\n```\n'
                         f'sentence sources [index, target_word, source]:\n```json\n'
                         f'{json.dumps(sources, ensure_ascii=False)}\n```')
            else:
                block = (f'### sense {sid}\ndocument:\n```json\n{json.dumps(doc, ensure_ascii=False)}\n```\n'
                         f'plan:\n```json\n{json.dumps(compact_plan(plan), ensure_ascii=False)}\n```')
            if errors:
                block += '\nvalidation errors to fix:\n' + '\n'.join(f'- {e}' for e in errors[sid])
            parts.append(block)
        head = ('Review each document below.' if not errors else
                'Your reviewed documents failed validation. Return patches that fix ONLY these errors '
                '(verdict stays as before; list the fixes as issues).')
        prompt = head + '\n\n' + '\n\n'.join(parts) + f'\n\nReturn results for: {batch}'
        out = call_model(args, system, prompt, f'{tag}:{batch[0]}+{len(batch)}')
        for sid in batch:
            r = out.get(str(sid)) or {'verdict': 'rewrite', 'issues': [], 'patches': [],
                                      'notes': 'reviewer returned nothing'}
            base_src = 'reviewed' if errors else 'words'
            doc = load(os.path.join(args.out, 'fat_seed', base_src, f'{sid}.json'))
            if getattr(args, 'core_only', False) and not errors:
                r['patches'] = [p for p in (r.get('patches') or [])
                                if isinstance(p, dict) and str(p.get('path', '')).startswith('/core/sentences/')]
            if getattr(args, 'keep_options', False) and not errors:
                r['patches'], dropped = keep_option_texts(doc, r.get('patches') or [], r.get('issues') or [])
                if dropped:
                    r['dropped_patches'] = dropped
                    r['notes'] = (r.get('notes') or '') + f' [{len(dropped)} option-text patch(es) discarded: no issue names the option as a second fit or non-word]'
            new, rejected = apply_patches_checked(doc, r.get('patches') or [])
            if rejected:
                r['patch_rejected'] = rejected
                r['notes'] = (r.get('notes') or '') + f' [{len(rejected)} patch(es) rejected: ' + \
                    '; '.join(f"{x['path']}: {x['problem']}" for x in rejected) + ']'
            if not getattr(args, 'allow_undecline', False):
                orig = load(os.path.join(args.out, 'fat_seed', 'words', f'{sid}.json'))
                redeclined = restore_declines(orig, new)
                if redeclined:
                    r['redeclined'] = redeclined
                    r['notes'] = (r.get('notes') or '') + f' [restored to declined: {redeclined}]'
            save(os.path.join(args.out, 'fat_seed', 'reviewed', f'{sid}.json'), new)
            rec_path = os.path.join(args.out, 'fat_seed', 'review', f'{sid}.json')
            if errors and os.path.exists(rec_path):
                prev = load(rec_path)
                prev['issues'] = prev.get('issues', []) + r.get('issues', [])
                r = prev
            r.pop('patches', None)
            r['sense_id'] = sid
            save(rec_path, r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--model', default='opus')
    ap.add_argument('--effort', default='medium')
    ap.add_argument('--batch', type=int, default=4)
    ap.add_argument('--fatal-only', action='store_true',
                    help='review only item-breaking defects (no style patches)')
    ap.add_argument('--keep-declines', action='store_true',
                    help='(default behaviour now; kept for old command lines) restore blocks the source declined')
    ap.add_argument('--allow-undecline', action='store_true',
                    help='let the reviewer replace a declined block with a written one')
    ap.add_argument('--plain-core', action='store_true',
                    help='replacement core sentences must be short, plain (T1-T3 grammar) and keep the tier label')
    ap.add_argument('--resume', action='store_true',
                    help='skip senses that already have reviewed/ and review/ files (interrupted run)')
    ap.add_argument('--keep-options', action='store_true',
                    help='discard patches that change level_3/5/8 option texts without a second-fit/non-word issue')
    ap.add_argument('--core-only', action='store_true',
                    help='review only the core sentences against the pinned sense; variants untouched')
    args = ap.parse_args()
    args.src = os.path.relpath(os.path.abspath(args.src), REPO)
    args.out = os.path.relpath(os.path.abspath(args.out), REPO)
    args.run = args.out  # call_model logs usage under args.run
    os.chdir(REPO)
    os.makedirs(os.path.join(args.out, 'fat_seed'), exist_ok=True)
    setup_out(args.src, args.out)
    judges_path = os.path.join(args.out, 'fat_seed', 'rules_judges.md')
    if not os.path.exists(judges_path):
        runner('review-pack', args.out)  # writes rules_judges.md
    judges = open(judges_path, encoding='utf-8').read()
    system = SYSTEM.format(judges=judges, checklist=checklist())
    if args.fatal_only:
        system += FATAL_ONLY
    if args.core_only:
        system += CORE_ONLY
    if args.keep_options:
        system += KEEP_OPTIONS
    if args.plain_core:
        system += PLAIN_CORE

    sids = sorted(int(f[:-5]) for f in os.listdir(os.path.join(args.out, 'fat_seed', 'words')))
    sids = [s for s in sids if os.path.exists(os.path.join(args.out, 'fat_seed', 'plans', f'{s}.json'))]
    review(args, system, sids, 'review')

    def run_check():
        live = [s for s in sids if load(os.path.join(args.out, 'fat_seed', 'review', f'{s}.json'))
                .get('verdict') != 'reject']
        runner('plan', args.out, '--source', 'reviewed')
        runner('check', args.out, '--source', 'reviewed', '--senses', ','.join(map(str, live)))
        res = load(os.path.join(args.out, 'fat_seed', 'check.reviewed.json'))
        return {s: res.get(str(s), {}) for s in live}

    res = run_check()
    bad = {s: r.get('errors') or [r.get('reason') or 'failed'] for s, r in res.items() if r.get('status') != 'ok'}
    print('check after review: failing', len(bad), flush=True)
    if bad:
        review(args, system, list(bad), 'review-repair', errors=bad)
        res = run_check()
    final = [r.get('status') for r in res.values()]
    print('final reviewed check', {k: final.count(k) for k in set(final)}, flush=True)


if __name__ == '__main__':
    main()
