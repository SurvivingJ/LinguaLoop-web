"""Tool-free fat-seed authoring.

The model never touches files or a shell: this script builds each prompt,
calls `claude -p` with tools disabled, parses the JSON reply, writes the word
documents, and runs `plan` / `check` itself. Failing senses get one repair call
with the check errors.

    python3 scratch_offline/nt_author.py data/exercise_seeding/ja/wf2/r0026 \
        [--model sonnet] [--effort low] [--variant-batch 4] [--repairs 2]

Usage per call is appended to RUN/fat_seed/nt_usage.jsonl.
"""
import argparse
import csv
import json
import os
import re
import shlex
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nt_lang  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHEATSHEET = os.path.join(REPO, 'data/exercise_seeding/ja/RULES_CHEATSHEET.md')
SKILL = os.path.join(REPO, '.claude/skills/fat-seed-authoring/SKILL.md')


def block_reference():
    """The skill's "## Block reference" section, up to the next ## heading."""
    text = open(SKILL, encoding='utf-8').read()
    start = text.index('## Block reference')
    end = text.index('\n## ', start + 1)
    return text[start:end].strip()


SYSTEM = """You author vocabulary-ladder exercise data for LinguaLoop, a Japanese
learning app. You have no tools. Reply with ONE fenced ```json block and
nothing else: no preamble, no commentary. Follow the rules below exactly.

{cheatsheet}

{blockref}
"""


def runner(cmd, run, *extra):
    """Run a fat_seed_runner subcommand.

    Through the offline DB shim (scratch_offline/run.py, reads snap/*.json) by
    default; with NT_ONLINE=1 against the real database (needs SUPABASE_URL /
    SUPABASE_KEY in the environment)."""
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    via = [] if os.environ.get('NT_ONLINE') == '1' else ['scratch_offline/run.py']
    p = subprocess.run(
        [sys.executable, *via, 'scripts/fat_seed_runner.py', cmd, run, *extra],
        cwd=REPO, env=env, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


LIMIT_WAIT = 600  # seconds between retries while a usage limit is in force


def _cli(args, system, prompt):
    system = nt_lang.localise(system)  # NT_LANG: name the target language
    p = subprocess.run(
        ['claude', '-p', '--model', args.model, '--effort', args.effort,
         '--tools', '', '--no-session-persistence', '--output-format', 'json',
         '--system-prompt', system],
        input=prompt, capture_output=True, text=True, cwd='/tmp', timeout=1800)
    try:
        return json.loads(p.stdout), p
    except json.JSONDecodeError:
        return None, p


def call_model(args, system, prompt, tag, _retry=False):
    t0 = time.time()
    for attempt in range(60):
        res, p = _cli(args, system, prompt)
        blob = (json.dumps(res) if res else '') + p.stdout + p.stderr
        limited = res is None or res.get('is_error')
        if limited and re.search(r'limit|rate|overloaded|429|529', blob, re.I):
            print(f'  [{tag}] usage limit / overload; waiting {LIMIT_WAIT}s', flush=True)
            time.sleep(LIMIT_WAIT)
            continue
        break
    if res is None:
        raise RuntimeError(f'{tag}: unparseable CLI output: {p.stdout[:500]} {p.stderr[:500]}')
    u = res.get('usage', {})
    rec = {'tag': tag, 'model': args.model, 'effort': args.effort,
           'secs': round(time.time() - t0, 1), 'cost_usd': res.get('total_cost_usd'),
           'input': u.get('input_tokens'), 'output': u.get('output_tokens'),
           'thinking': (u.get('output_tokens_details') or {}).get('thinking_tokens'),
           'cache_read': u.get('cache_read_input_tokens'),
           'cache_create': u.get('cache_creation_input_tokens'),
           'stop': res.get('stop_reason'), 'error': res.get('is_error')}
    with open(os.path.join(args.run, 'fat_seed', 'nt_usage.jsonl'), 'a') as fh:
        fh.write(json.dumps(rec) + '\n')
    print(f"  [{tag}] {rec['secs']}s out={rec['output']} cost=${rec['cost_usd']}", flush=True)
    text = res.get('result') or ''
    m = re.search(r'```json\s*(.*?)```', text, re.S)
    body = m.group(1) if m else text
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        if _retry:
            raise RuntimeError(f'{tag}: reply is not JSON ({e}); stop={rec["stop"]}: {text[:300]}')
        # A malformed reply is a model slip, not a pipeline fault: ask once more.
        print(f'  [{tag}] reply not JSON ({e}); retrying once', flush=True)
        return call_model(args, system, prompt + '\n\nYour previous reply was not valid JSON '
                          f'({e}). Return strictly valid JSON.', tag + ':retry', _retry=True)


def words_path(run, sid):
    return os.path.join(run, 'fat_seed', 'words', f'{sid}.json')


def load(path):
    return json.load(open(path, encoding='utf-8'))


def save(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)


def strip_brief(text):
    """Drop the file-writing instructions; keep the sense data and rules."""
    text = re.sub(r'Run directory:.*?\n', '', text)
    text = re.sub(r'Read `[^`]*rules_core\.md` first:[^\n]*\n', '', text)
    text = text.replace('write `', 'produce `')
    return text


def sibling_table(rows):
    """sense_id -> [(sibling sense_id, definition)] for lemmas with several senses in the run."""
    by = {}
    for r in rows:
        by.setdefault(r['lemma'], []).append((int(r['sense_id']), r.get('definition') or ''))
    return {sid: [(o, d) for o, d in group if o != sid]
            for group in by.values() if len(group) > 1 for sid, _ in group}


def sibling_block(args, sids, heading):
    lines = []
    for sid in sids:
        sibs = (getattr(args, 'siblings', None) or {}).get(int(sid))
        if sibs:
            lines.append(f'- sense {sid} must NOT be readable as: ' + ' / '.join(f'{o}「{d}」' for o, d in sibs))
    if not lines:
        return ''
    return ('\n\n' + heading + '\n' + '\n'.join(lines) + '\n')


SIBLING_CORE = ('Sibling senses of the same word are in this batch. Every sentence must be '
                'unambiguous for ITS OWN sense: a reader must not be able to understand it in a '
                'sibling sense. Choose contexts that exclude the siblings; never write a sentence '
                'that would also fit a sibling definition.')
SIBLING_AUDIT = ('Also: "sense_ok" is false if the sentence reads just as naturally in one of the '
                 'sibling senses listed for that sense. Replacements must exclude the siblings.')


def author_cores(args, system, lemmas):
    idx = load(os.path.join(args.run, 'fat_seed', 'briefs', 'index.json'))
    for brief, sids in idx.items():
        todo = [s for s in sids if not os.path.exists(words_path(args.run, s))]
        if not todo:
            continue
        text = strip_brief(open(os.path.join(args.run, 'fat_seed', 'briefs', brief), encoding='utf-8').read())
        text += sibling_block(args, sids, SIBLING_CORE)
        prompt = (text + '\n\nReturn a JSON object mapping each sense_id (as a string) to its '
                  'document: {"<sense_id>": {"sense_id": …, "lemma": …, "core": {…}}} '
                  f'(or a skip document). Senses to return: {todo}.')
        out = call_model(args, system, prompt, f'core:{brief}')
        for sid in todo:
            doc = out.get(str(sid))
            if doc:
                doc.setdefault('sense_id', sid)
                doc.setdefault('lemma', lemmas[sid])
                doc.pop('variants', None)
                save(words_path(args.run, sid), doc)


def plan_for(run, sid):
    p = os.path.join(run, 'fat_seed', 'plans', f'{sid}.json')
    return load(p) if os.path.exists(p) else None


SKIP_L1 = False  # set by --skip-l1: the ja renderer builds level_1 from the phonetic trie


def compact_plan(plan):
    keep = {k: plan[k] for k in ('lemma', 'semantic_class', 'active_levels', 'blocks') if k in plan}
    keep['sentences'] = [s[:2] for s in plan.get('sentences', [])]
    if SKIP_L1 and 'blocks' in keep:
        keep['blocks'] = {v: {b: spec for b, spec in blocks.items() if b != 'level_1'}
                          for v, blocks in keep['blocks'].items()}
    return keep


def decline_l1(doc, plan):
    if not (SKIP_L1 and plan and doc.get('variants')):
        return
    for v, blocks in (plan.get('blocks') or {}).items():
        if 'level_1' in blocks and v in doc['variants']:
            doc['variants'][v]['level_1'] = {'declined': 'no_minimal_pairs'}


def author_variants(args, system, sids):
    for i in range(0, len(sids), args.variant_batch):
        batch = sids[i:i + args.variant_batch]
        parts = []
        for sid in batch:
            doc = load(words_path(args.run, sid))
            parts.append(f'### sense {sid}: {doc["lemma"]}\ncore:\n```json\n'
                         + json.dumps(doc['core'], ensure_ascii=False)
                         + '\n```\nplan:\n```json\n'
                         + json.dumps(compact_plan(plan_for(args.run, sid)), ensure_ascii=False) + '\n```')
        prompt = ('Write the exercise variants for each sense below. Write exactly the blocks '
                  'the plan lists under blocks.A and blocks.B, using the plan\'s anchor '
                  'sentence, correct answer and given values. Write A and B independently.\n\n'
                  + '\n\n'.join(parts)
                  + '\n\nReturn {"<sense_id>": {"A": {…blocks…}, "B": {…blocks…}}} for: '
                  + str(batch))
        out = call_model(args, system, prompt, f'variants:{batch[0]}+{len(batch)}')
        for sid in batch:
            v = out.get(str(sid))
            if v:
                doc = load(words_path(args.run, sid))
                doc['variants'] = v
                decline_l1(doc, plan_for(args.run, sid))
                save(words_path(args.run, sid), doc)


def compact_plan_variant(plan, variant):
    """compact_plan() restricted to one variant's blocks (for --split-ab)."""
    keep = compact_plan(plan)
    if 'blocks' in keep:
        keep['blocks'] = {variant: keep['blocks'].get(variant, {})}
    return keep


def _sense_part(args, sid, variant=None):
    doc = load(words_path(args.run, sid))
    plan = plan_for(args.run, sid)
    cp = compact_plan_variant(plan, variant) if variant else compact_plan(plan)
    return (f'### sense {sid}: {doc["lemma"]}\ncore:\n```json\n'
            + json.dumps(doc['core'], ensure_ascii=False)
            + '\n```\nplan:\n```json\n' + json.dumps(cp, ensure_ascii=False) + '\n```'), doc


def _variants_of(args, sid):
    return load(words_path(args.run, sid)).get('variants') or {}


def author_variants_split(args, system, sids):
    """--split-ab: variant A and variant B of a batch come from two separate
    calls; the B call sees A and is told to reuse nothing from it."""
    need_a = [s for s in sids if 'A' not in _variants_of(args, s)]
    for i in range(0, len(need_a), args.variant_batch):
        batch = need_a[i:i + args.variant_batch]
        parts = [_sense_part(args, sid, 'A')[0] for sid in batch]
        prompt = ('Write VARIANT A of the exercise blocks for each sense below: exactly the blocks '
                  'the plan lists under blocks.A, using the plan\'s anchor sentence, correct answer '
                  'and given values. Variant B will be written later by someone else.\n\n'
                  + '\n\n'.join(parts)
                  + '\n\nReturn {"<sense_id>": {…A blocks…}} for: ' + str(batch))
        out = call_model(args, system, prompt, f'variants:{batch[0]}+{len(batch)}:A')
        for sid in batch:
            a = out.get(str(sid)) if isinstance(out, dict) else None
            if a:
                doc = load(words_path(args.run, sid))
                doc['variants'] = dict(doc.get('variants') or {}, A=a)
                save(words_path(args.run, sid), doc)
    need_b = [s for s in sids if 'A' in _variants_of(args, s) and 'B' not in _variants_of(args, s)]
    for i in range(0, len(need_b), args.variant_batch):
        batch = need_b[i:i + args.variant_batch]
        parts = []
        for sid in batch:
            part, doc = _sense_part(args, sid, 'B')
            parts.append(part + '\nvariant A, already written by another author (do NOT reuse '
                         'any of its distractor words, wrong sentences, level_7 sentences or '
                         'error patterns):\n```json\n'
                         + json.dumps(doc['variants']['A'], ensure_ascii=False) + '\n```')
        prompt = ('Write VARIANT B of the exercise blocks for each sense below: exactly the blocks '
                  'the plan lists under blocks.B, using the plan\'s anchor sentence, correct answer '
                  'and given values. B is a second, different exercise on the same sense: it must '
                  'share no distractor word with A in the same block, use different wrong '
                  'sentences and error types in level_6, plant a different kind of error in '
                  'level_7, and blank a different particle or use a different distractor set in '
                  'particle_selection.\n\n'
                  + '\n\n'.join(parts)
                  + '\n\nReturn {"<sense_id>": {…B blocks…}} for: ' + str(batch))
        out = call_model(args, system, prompt, f'variants:{batch[0]}+{len(batch)}:B')
        for sid in batch:
            b = out.get(str(sid)) if isinstance(out, dict) else None
            if b:
                doc = load(words_path(args.run, sid))
                doc['variants'] = dict(doc.get('variants') or {}, B=b)
                decline_l1(doc, plan_for(args.run, sid))
                save(words_path(args.run, sid), doc)


SELF_CHECK = """\
You wrote the exercise variants below earlier. Re-read them as a strict
reviewer and fix every defect you find. Hunt for exactly these:
1. level_7: the error is not on the target word; corrected_sentence equals a
   core sentence; incorrect_sentence is not clearly wrong; more than one error.
2. level_3 / level_5 / level_8 / particle_selection: a distractor that gives a
   sayable sentence in the blank; a distractor that any reader excludes without
   knowing the word (off-domain); two distractors that are near-synonyms.
3. level_6: a wrong sentence that is absurd nonsense instead of a plausible
   misuse; one that is wrong for a reason unrelated to the target; one that is
   actually acceptable.
4. Explanations: generic (「形は合うが意味が合わない」 and the like), false, or
   contradicting the core definition; English in error_tags or labels.
5. B reusing A's distractor words, wrong sentences or error patterns.
Keep the plan's anchors, correct answers and given values; keep every block
the plan lists; keep {"declined": …} blocks as they are.

"""


def self_check(args, system, sids):
    """--self-check: one cheap pass by the author model over its own variants
    before `check`. Returns full corrected variants only for changed senses."""
    for i in range(0, len(sids), args.variant_batch):
        batch = sids[i:i + args.variant_batch]
        parts = []
        for sid in batch:
            part, doc = _sense_part(args, sid)
            parts.append(part + '\nvariants:\n```json\n'
                         + json.dumps(doc.get('variants') or {}, ensure_ascii=False) + '\n```')
        prompt = (SELF_CHECK + '\n\n'.join(parts)
                  + '\n\nReturn {"<sense_id>": {"A": {…all A blocks…}, "B": {…all B blocks…}}} '
                  'with the FULL corrected variants for every sense you changed; leave out '
                  'senses that need no change (return {} if none). Senses: ' + str(batch))
        out = call_model(args, system, prompt, f'selfcheck:{batch[0]}+{len(batch)}')
        for sid in batch:
            v = out.get(str(sid)) if isinstance(out, dict) else None
            if isinstance(v, dict) and v.get('A') and v.get('B'):
                doc = load(words_path(args.run, sid))
                doc['variants'] = v
                decline_l1(doc, plan_for(args.run, sid))
                save(words_path(args.run, sid), doc)


def _audit_state(args, name):
    p = os.path.join(args.run, 'fat_seed', f'audit_{name}.json')
    return p, (load(p) if os.path.exists(p) else {})


CORE_AUDIT = """\
You are auditing core sentences you wrote earlier, one check at a time. For
EVERY sentence of every sense below answer, as a JSON object:
  "reading": the reading of the target word IN THAT SENTENCE (hiragana),
  "whole_word": true if the target is an independent word there (false if it
      sits inside a longer word, e.g. 習熟度 for 度, ロックバンド for バンド),
  "sense_ok": true if the target carries the GIVEN definition there (false for
      another sense, another word of the same form, another reading),
  "natural": true if a native speaker would say the sentence as written
      (ordinary collocations, no homophone traps, no redundancy, grammatical).
A written sentence FAILS if reading != the given reading, or whole_word,
sense_ok or natural is false. For each failing WRITTEN sentence (never a
mined one: mined sentences are fixed; audit them but do not replace them)
write ONE replacement with the same complexity_tier and register that passes
every check, with "text", "target_word" (exact surface in text),
"complexity_tier" and "furigana".

"""


def core_audit(args, system, lemmas, rows):
    """--core-audit: one cheap pass per batch that checks reading / whole-word /
    sense / naturalness of every core sentence and regenerates failing ones."""
    state_path, done = _audit_state(args, 'core')
    meta = {int(r['sense_id']): r for r in rows}
    sids = [s for s in lemmas if os.path.exists(words_path(args.run, s))
            and not load(words_path(args.run, s)).get('skip') and str(s) not in done]
    for i in range(0, len(sids), args.variant_batch):
        batch = sids[i:i + args.variant_batch]
        parts = []
        for sid in batch:
            doc = load(words_path(args.run, sid))
            r = meta[sid]
            try:
                mined = {m.get('text') for m in json.loads(r.get('corpus_sentences') or '[]')}
            except json.JSONDecodeError:
                mined = set()
            lines = [f'  {k}: {"[mined] " if s.get("text") in mined else ""}{s.get("text")}'
                     for k, s in enumerate((doc.get('core') or {}).get('sentences') or [])]
            parts.append(f'### sense {sid}: {doc["lemma"]}\nreading: {r.get("reading")}\n'
                         f'definition: {(doc.get("core") or {}).get("definition")}\n'
                         f'tier: {r.get("complexity_tier")}  register: {(doc.get("core") or {}).get("register")}\n'
                         'sentences:\n' + '\n'.join(lines))
        prompt = (CORE_AUDIT + '\n\n'.join(parts) + sibling_block(args, batch, SIBLING_AUDIT)
                  + '\n\nReturn {"<sense_id>": {"audit": {"<index>": {"reading": …, "whole_word": …, '
                  '"sense_ok": …, "natural": …}}, "replacements": {"<index>": {"text": …, '
                  '"target_word": …, "complexity_tier": …, "furigana": …}}}} for: ' + str(batch))
        out = call_model(args, system, prompt, f'coreaudit:{batch[0]}+{len(batch)}')
        for sid in batch:
            res = out.get(str(sid)) if isinstance(out, dict) else None
            done[str(sid)] = {'replaced': []}
            if not isinstance(res, dict):
                continue
            doc = load(words_path(args.run, sid))
            sents = (doc.get('core') or {}).get('sentences') or []
            try:
                mined = {m.get('text') for m in json.loads(meta[sid].get('corpus_sentences') or '[]')}
            except json.JSONDecodeError:
                mined = set()
            for k, rep in (res.get('replacements') or {}).items():
                try:
                    k = int(k)
                except (TypeError, ValueError):
                    continue
                if not (0 <= k < len(sents)) or sents[k].get('text') in mined:
                    continue
                if not (isinstance(rep, dict) and rep.get('text') and rep.get('target_word')
                        and rep['target_word'] in rep['text']):
                    continue
                new = dict(sents[k])
                new.update({f: rep[f] for f in ('text', 'target_word', 'complexity_tier', 'furigana') if rep.get(f)})
                sents[k] = new
                done[str(sid)]['replaced'].append(k)
            doc['core']['sentences'] = sents
            save(words_path(args.run, sid), doc)
        save(state_path, done)
    n = sum(len(v.get('replaced', [])) for v in done.values())
    print(f'core-audit: {n} sentences replaced over {len(done)} senses', flush=True)


CORE_POLISH = """\
You are polishing core sentences you wrote earlier. The reading and the sense
have already been checked; this pass is only about NATURALNESS. For every
WRITTEN sentence (never a [mined] one) ask: would a careful native speaker
write exactly this? Look for a collocation or partner word that is not used
with this word (度を守る → 節度を守る, 志向が合わない → 価値観が合わない), a
particle a native speaker would not choose, redundancy, a missing or vague
referent, a homophone trap (誤りました read as 謝りました), register drift
from the declared one, or wording above the tier. If anything would make a
native speaker pause, REWRITE the sentence minimally: same meaning, same
sense, same reading of the target, same target_word surface, same
complexity_tier and register, natural everyday phrasing, with furigana.
Leave good sentences alone and do not list them. For each rewrite also give
"reading" (the target's reading in the new sentence) and "sense_ok" (true if
it still carries the given definition) so it can be verified.

"""


def core_polish(args, system, lemmas, rows):
    """--core-polish: a second cheap core pass that rewrites written sentences
    a native speaker would not phrase that way (collocation, particle,
    redundancy, register, tier). Runs after --core-audit, before plan."""
    state_path, done = _audit_state(args, 'polish')
    meta = {int(r['sense_id']): r for r in rows}
    sids = [s for s in lemmas if os.path.exists(words_path(args.run, s))
            and not load(words_path(args.run, s)).get('skip') and str(s) not in done]

    def mined_of(sid):
        try:
            return {m.get('text') for m in json.loads(meta[sid].get('corpus_sentences') or '[]')}
        except json.JSONDecodeError:
            return set()

    for i in range(0, len(sids), args.variant_batch):
        batch = sids[i:i + args.variant_batch]
        parts = []
        for sid in batch:
            doc = load(words_path(args.run, sid))
            r = meta[sid]
            mined = mined_of(sid)
            core = doc.get('core') or {}
            lines = [f'  {k}: {"[mined] " if s.get("text") in mined else ""}{s.get("text")}'
                     for k, s in enumerate(core.get('sentences') or [])]
            parts.append(f'### sense {sid}: {doc["lemma"]}\nreading: {r.get("reading")}\n'
                         f'definition: {core.get("definition")}\n'
                         f'tier: {r.get("complexity_tier")}  register: {core.get("register")}\n'
                         'sentences:\n' + '\n'.join(lines))
        prompt = (CORE_POLISH + '\n\n'.join(parts)
                  + '\n\nReturn {"<sense_id>": {"rewrites": {"<index>": {"text": …, "target_word": …, '
                  '"complexity_tier": …, "furigana": …, "reading": …, "sense_ok": true}}}} for: ' + str(batch)
                  + ' (a sense with nothing to rewrite gets {"rewrites": {}}).')
        out = call_model(args, system, prompt, f'corepolish:{batch[0]}+{len(batch)}')
        for sid in batch:
            res = out.get(str(sid)) if isinstance(out, dict) else None
            done[str(sid)] = {'rewritten': []}
            if not isinstance(res, dict):
                continue
            doc = load(words_path(args.run, sid))
            sents = (doc.get('core') or {}).get('sentences') or []
            mined = mined_of(sid)
            given_reading = (meta[sid].get('reading') or '').split('-')[0].strip()
            for k, rep in (res.get('rewrites') or {}).items():
                try:
                    k = int(k)
                except (TypeError, ValueError):
                    continue
                if not (0 <= k < len(sents)) or sents[k].get('text') in mined:
                    continue
                if not (isinstance(rep, dict) and rep.get('text') and rep.get('target_word')
                        and rep['target_word'] in rep['text'] and rep.get('sense_ok') is True):
                    continue
                # The rewrite must keep the given reading (reading column may carry a "-romaji" suffix).
                if given_reading and rep.get('reading') and str(rep['reading']).strip() != given_reading:
                    continue
                if rep['text'] == sents[k].get('text'):
                    continue
                new = dict(sents[k])
                new.update({f: rep[f] for f in ('text', 'target_word', 'complexity_tier', 'furigana') if rep.get(f)})
                sents[k] = new
                done[str(sid)]['rewritten'].append(k)
            doc['core']['sentences'] = sents
            save(words_path(args.run, sid), doc)
        save(state_path, done)
    n = sum(len(v.get('rewritten', [])) for v in done.values())
    print(f'core-polish: {n} sentences rewritten over {len(done)} senses', flush=True)


VARIANT_AUDIT = """\
You are auditing level_6 and level_7 items you wrote earlier, one check at a
time. For each level_6 wrong sentence answer:
  "grammatical": true if the sentence is grammatical as written,
  "only_target_wrong": true if the ONLY problem is the meaning of the target
      word there (false if the error is a particle/inflection slip, an error
      on another word, a factual oddity, or nonsense),
  "actually_wrong": true if a native speaker who knows the word would reject
      it (false if it is an acceptable use, even with odd content).
A wrong sentence FAILS unless all three are true. For each level_7 block
answer:
  "span_on_target": true if incorrect and corrected sentences differ in
      exactly one span containing the target word or the particle/verb
      directly attached to it,
  "incorrect_is_wrong": true if a native speaker would reject the incorrect
      sentence,
  "corrected_is_natural": true if the corrected sentence is natural in the
      GIVEN sense and reading and equals no core sentence.
A level_7 block FAILS unless all three are true. For every failing item write
a replacement: a level_6 wrong sentence built as a natural sentence for a
different sense/word or for a confusable near-synonym with the target put in
its place ({"text", "explanation"}), or a full level_7 block ({"incorrect_sentence",
"corrected_sentence", "error_description", "correct_sentence_indices" unchanged}).

"""


L6_AUDIT = """\
Additional level_6 questions (answer them for EVERY wrong sentence):
  "natural_in_some_context": true if it is a natural, grammatical sentence a
      native speaker would accept in some ordinary context (「その花は、一年中
      ある。」「政府は急な物価上昇を支えた。」 are both natural). If true it CANNOT
      be a wrong sentence: replace it with one that misuses the SENSE, i.e.
      uses the word as if it meant something else, while staying grammatical
      and natural-sounding.
  "explanation_names_confusion": true only if the explanation names the actual
      word that is misused and the sense it is confused with (not the taught
      sense, not a word that is still in the sentence). If false, rewrite the
      explanation (replacement = {"text": unchanged, "explanation": new}).

"""


def variant_audit(args, system, sids):
    """--variant-audit: cheap verdict pass over level_6 / level_7 with
    replacement of failing items only. --l6-audit appends the level_6
    naturalness / explanation questions (L6_AUDIT)."""
    state_path, done = _audit_state(args, 'variants')
    head = VARIANT_AUDIT + (L6_AUDIT if getattr(args, 'l6_audit', False) else '')
    sids = [s for s in sids if str(s) not in done and 'variants' in load(words_path(args.run, s))]
    for i in range(0, len(sids), args.variant_batch):
        batch = sids[i:i + args.variant_batch]
        parts = []
        for sid in batch:
            doc = load(words_path(args.run, sid))
            core = doc.get('core') or {}
            items = {}
            for v in ('A', 'B'):
                var = (doc.get('variants') or {}).get(v) or {}
                items[v] = {k: var.get(k) for k in ('level_6', 'level_7') if isinstance(var.get(k), dict)
                            and 'declined' not in var.get(k)}
            sents = '\n'.join(f'  {k}: {s.get("text")}' for k, s in enumerate(core.get('sentences') or []))
            parts.append(f'### sense {sid}: {doc["lemma"]}\ndefinition: {core.get("definition")}\n'
                         f'core sentences:\n{sents}\nitems:\n```json\n{json.dumps(items, ensure_ascii=False)}\n```')
        prompt = (head + '\n\n'.join(parts)
                  + '\n\nReturn {"<sense_id>": {"A": {"level_6": {"verdicts": [...], "replacements": '
                  '{"<index>": {"text": …, "explanation": …}}}, "level_7": {"verdict": {...}, '
                  '"replacement": {...} or null}}, "B": {...}}} for: ' + str(batch))
        stage = 'l6audit' if getattr(args, 'l6_audit', False) else 'varaudit'  # distinct cost stage per prompt
        out = call_model(args, system, prompt, f'{stage}:{batch[0]}+{len(batch)}')
        for sid in batch:
            res = out.get(str(sid)) if isinstance(out, dict) else None
            done[str(sid)] = {'l6': 0, 'l7': 0}
            if not isinstance(res, dict):
                continue
            doc = load(words_path(args.run, sid))
            for v in ('A', 'B'):
                rv = res.get(v) if isinstance(res.get(v), dict) else {}
                var = (doc.get('variants') or {}).get(v) or {}
                l6 = var.get('level_6')
                reps = ((rv.get('level_6') or {}).get('replacements') or {}) if isinstance(rv.get('level_6'), dict) else {}
                if isinstance(l6, dict) and isinstance(l6.get('wrong_sentences'), list):
                    for k, rep in reps.items():
                        try:
                            k = int(k)
                        except (TypeError, ValueError):
                            continue
                        if 0 <= k < len(l6['wrong_sentences']) and isinstance(rep, dict) and rep.get('text') \
                                and doc['lemma'] and rep.get('explanation'):
                            l6['wrong_sentences'][k] = {'text': rep['text'], 'explanation': rep['explanation']}
                            done[str(sid)]['l6'] += 1
                l7 = var.get('level_7')
                rep7 = (rv.get('level_7') or {}).get('replacement') if isinstance(rv.get('level_7'), dict) else None
                if isinstance(l7, dict) and isinstance(rep7, dict) and rep7.get('incorrect_sentence') \
                        and rep7.get('corrected_sentence') and rep7['incorrect_sentence'] != rep7['corrected_sentence']:
                    new = dict(l7)
                    new.update({f: rep7[f] for f in ('incorrect_sentence', 'corrected_sentence', 'error_description')
                                if rep7.get(f)})
                    var['level_7'] = new
                    done[str(sid)]['l7'] += 1
            save(words_path(args.run, sid), doc)
        save(state_path, done)
    print(f"variant-audit: replaced l6={sum(v['l6'] for v in done.values())} "
          f"l7={sum(v['l7'] for v in done.values())} over {len(done)} senses", flush=True)


def check(args, sids):
    runner('check', args.run, '--senses', ','.join(map(str, sids)))
    return load(os.path.join(args.run, 'fat_seed', 'check.words.json'))


def repair(args, system, failing, round_no):
    for i in range(0, len(failing), args.variant_batch):
        batch = failing[i:i + args.variant_batch]
        parts = []
        for sid, errs in batch:
            doc = load(words_path(args.run, sid))
            plan = plan_for(args.run, sid)
            parts.append(f'### sense {sid}\nerrors:\n' + '\n'.join(f'- {e}' for e in errs)
                         + '\ndocument:\n```json\n' + json.dumps(doc, ensure_ascii=False) + '\n```'
                         + ('\nplan:\n```json\n' + json.dumps(compact_plan(plan), ensure_ascii=False)
                            + '\n```' if plan and plan.get('ok') else ''))
        prompt = ('These documents failed validation. Fix ONLY what the errors name; keep '
                  'everything else unchanged (mined sentences byte-for-byte).\n\n'
                  + '\n\n'.join(parts)
                  + '\n\nReturn {"<sense_id>": <full corrected document>} for: '
                  + str([s for s, _ in batch]))
        out = call_model(args, system, prompt, f'repair{round_no}:{batch[0][0]}+{len(batch)}')
        for sid, _ in batch:
            if str(sid) in out:
                doc = out[str(sid)]
                decline_l1(doc, plan_for(args.run, sid))
                save(words_path(args.run, sid), doc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run')
    ap.add_argument('--model', default='sonnet')
    ap.add_argument('--effort', default='low')
    ap.add_argument('--variant-batch', type=int, default=4)
    ap.add_argument('--repairs', type=int, default=2)
    ap.add_argument('--width', type=int, default=0, help='senses per core brief')
    ap.add_argument('--skip-l1', action='store_true')
    ap.add_argument('--cheatsheet', default=CHEATSHEET)
    ap.add_argument('--split-ab', action='store_true',
                    help='write variant A and variant B in separate calls (the B call sees A)')
    ap.add_argument('--self-check', action='store_true',
                    help='one author-model review pass over the variants before check')
    ap.add_argument('--core-audit', action='store_true',
                    help='reading / whole-word / sense / naturalness audit of core sentences, regenerating failures')
    ap.add_argument('--variant-audit', action='store_true',
                    help='verdict pass over level_6 / level_7 items, replacing failures only')
    ap.add_argument('--core-polish', action='store_true',
                    help='second core pass: rewrite written sentences a native speaker would not phrase that way '
                         '(collocation, particle, redundancy, register, tier); runs after --core-audit')
    ap.add_argument('--core-model', default='', help='model for the core call only (e.g. sonnet)')
    ap.add_argument('--core-audit-model', default='', help='model for the core audit only (e.g. sonnet)')
    ap.add_argument('--core-audit-effort', default='')
    ap.add_argument('--core-effort', default='', help='effort for the core call only')
    ap.add_argument('--sibling-guard', action='store_true',
                    help='name the other senses of the same lemma in the core prompt and core audit')
    ap.add_argument('--l6-audit', action='store_true',
                    help='with --variant-audit: also ask whether each level_6 wrong sentence is natural in '
                         'some context (then it must be replaced) and whether its explanation names the confusion')
    # Extra flags via env (NT_AUTHOR_EXTRA_ARGS="--split-ab") so a driver that
    # builds this command line (nt_experiment.py) needs no change. Additive only.
    args = ap.parse_args(sys.argv[1:] + shlex.split(os.environ.get('NT_AUTHOR_EXTRA_ARGS', '')))
    global SKIP_L1
    SKIP_L1 = args.skip_l1
    args.run = os.path.relpath(os.path.abspath(args.run), REPO)

    system = SYSTEM.format(cheatsheet=open(args.cheatsheet, encoding='utf-8').read(),
                           blockref=block_reference())
    rows = list(csv.DictReader(open(os.path.join(REPO, args.run, 'senses.csv'), encoding='utf-8')))
    lemmas = {int(r['sense_id']): r['lemma'] for r in rows}
    # --sibling-guard: the queue groups the senses of one lemma into the same
    # run, and the author (and the judge) confuse them; name the siblings.
    args.siblings = sibling_table(rows) if args.sibling_guard else {}
    sids = list(lemmas)
    os.chdir(REPO)

    if not os.path.exists(os.path.join(args.run, 'fat_seed', 'briefs', 'index.json')):
        runner('brief', args.run, *(['--width', str(args.width)] if args.width else []))
    print('core', flush=True)
    if args.core_model:
        # --core-model: a stronger model for the core only (the core anchors every block)
        model, effort = args.model, args.effort
        args.model, args.effort = args.core_model, args.core_effort or effort
        try:
            author_cores(args, system, lemmas)
        finally:
            args.model, args.effort = model, effort
    else:
        author_cores(args, system, lemmas)
    if args.core_audit:
        print('core-audit', flush=True)
        if args.core_audit_model:
            # --core-audit-model: a stronger auditor for sense/reading discipline only
            model, effort = args.model, args.effort
            args.model, args.effort = args.core_audit_model, args.core_audit_effort or effort
            try:
                core_audit(args, system, lemmas, rows)
            finally:
                args.model, args.effort = model, effort
        else:
            core_audit(args, system, lemmas, rows)
    if args.core_polish:
        print('core-polish', flush=True)
        core_polish(args, system, lemmas, rows)

    print('plan', flush=True)
    runner('plan', args.run)
    live = [s for s in sids if os.path.exists(words_path(args.run, s))
            and not load(words_path(args.run, s)).get('skip')]
    bad_core = [s for s in live if not (plan_for(args.run, s) or {}).get('ok')]
    if bad_core:
        repair(args, system, [(s, plan_for(args.run, s).get('errors', ['core not plannable'])
                               if plan_for(args.run, s) else ['missing plan']) for s in bad_core], 0)
        runner('plan', args.run)
    ready = [s for s in live if (plan_for(args.run, s) or {}).get('ok')]

    print('variants', flush=True)
    if args.split_ab:
        author_variants_split(args, system, ready)
    else:
        author_variants(args, system, [s for s in ready if 'variants' not in load(words_path(args.run, s))])
    if args.self_check:
        print('self-check', flush=True)
        self_check(args, system, [s for s in ready if 'variants' in load(words_path(args.run, s))])
    if args.variant_audit:
        print('variant-audit', flush=True)
        variant_audit(args, system, ready)

    res = check(args, live)
    # Keep the first-pass errors per sense: the repair loop overwrites check.words.json,
    # so this is the only record of what the lints caught before repair.
    save(os.path.join(args.run, 'fat_seed', 'check.first.json'),
         {str(s): {'status': res.get(str(s), {}).get('status'), 'errors': res.get(str(s), {}).get('errors', [])}
          for s in live})
    first = sum(1 for s in live if res.get(str(s), {}).get('status') == 'ok')
    with open(os.path.join(args.run, 'fat_seed', 'nt_usage.jsonl'), 'a') as fh:
        fh.write(json.dumps({'tag': 'first_pass_check', 'ok': first, 'of': len(live)}) + '\n')
    print(f'first-pass check ok {first}/{len(live)}', flush=True)
    for r in range(1, args.repairs + 1):
        failing = [(s, res[str(s)]['errors']) for s in live
                   if res.get(str(s), {}).get('status') != 'ok']
        if not failing:
            break
        repair(args, system, failing, r)
        runner('plan', args.run)
        res = check(args, live)
    final = {s: res.get(str(s), {}).get('status') for s in live}
    print('final check', {k: list(final.values()).count(k) for k in set(final.values())}, flush=True)


if __name__ == '__main__':
    main()
