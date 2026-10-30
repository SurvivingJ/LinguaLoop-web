"""Frozen quality judge for fat-seed documents (the optimisation gate).

A high-effort Opus call with no tools reads each finished document and lists
defects. The prompt, model and effort are fixed so every experiment arm is
scored by the same judge; the score is derived by code from the defects
(10 - 3*fatal - 1*major - 0.3*minor, floored at 0), never by the model.

    python3 scratch_offline/nt_judge.py RUN [--source reviewed] [--batch 3]

Writes RUN/fat_seed/judge.<source>.v2<tag>.json and appends usage to
nt_usage.jsonl under tags `judge:*` (excluded from pipeline cost).

Proxy judging (Track C, measurement only): `--model M --effort E` runs the
SAME rubric with a cheaper model/effort and writes to a distinct file,
RUN/fat_seed/judge.<source>.v2.<M>-<E>[-b<batch>]<tag>.json, so it never
collides with the frozen judge's output. The frozen file name is used only
when model and effort are the frozen pair (opus/high).

Each sense's result stores `doc_sha` (hash of the judged document) and `judged_at`;
a resume re-judges only senses whose document changed, keeps hash-less legacy
results and reports them as unverified_legacy. `_meta.passes` records each
pass's start time (top-level key; every reader filters on `score`).

`--rubric 3` adds scope rules (file suffix v3); `--rubric 4` additionally
injects each sense's gold mined sentences (from RUN/senses.csv or --senses)
into the prompt, allows 4-8 level_1 options and polite forms (suffix v4).
"""
import argparse
import datetime
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nt_author import REPO, runner, load, save, call_model  # noqa: E402
from nt_review import checklist  # noqa: E402

MODEL, EFFORT = 'opus', 'high'  # frozen: never change between arms
JUDGE_VERSION = 2  # bump when the rubric changes; every arm must be re-judged
DEFAULT_BATCH = 3

SYSTEM = """You are the final quality judge for Japanese vocabulary-ladder
exercise documents in LinguaLoop. You have no tools. You do not fix anything;
you list defects. Reply with ONE fenced ```json block and nothing else.

Standards: the live judge prompts below (ignore their output formats) and the
checklist after them. Judge every block of both variants A and B and the core.
A block of the form {{"declined": "..."}} is out of scope: do not report it.

Severity:
- fatal: the item cannot be used as is. Wrong or ambiguous correct answer, a
  distractor that is also correct or fits the blank, a level_6 wrong sentence
  that is a correct use of THIS sense (a natural sentence that uses a
  DIFFERENT sense of the word is the intended level_6 design and is not a
  defect), a level_7 pair that is identical or where the
  "incorrect" sentence is correct, a sentence that uses another sense of the
  word, ungrammatical Japanese in a sentence a learner must read as correct,
  A and B sharing the same distractors.
- major: misleading but usable. A wrong or empty explanation, a distractor that
  is not a real word or does not sound alike (level_1), a level_1 pair that
  differs only in pitch accent, unnatural but grammatical Japanese, a
  collocate distractor that is in fact a common collocate, an explanation that
  contradicts the core definition.
- minor: style. Register mismatch, slightly awkward phrasing, a weak but valid
  distractor, inconsistent orthography.

Be exhaustive and concrete: name the JSON path of every defect. Do not invent
defects; "no defects" for a block is a valid outcome.

=== judge prompts ===
{judges}

=== checklist ===
{checklist}

=== output ===
{{"<sense_id>": {{"defects": [{{"path": "variants.A.level_3.options[2]",
   "severity": "fatal"|"major"|"minor", "problem": "…"}}],
  "sense_fit": "ok"|"wrong_sense"|"duplicate_sense"}}}}
"""

W = {'fatal': 3.0, 'major': 1.0, 'minor': 0.3}


def score(defects):
    return max(0.0, 10.0 - sum(W.get(d.get('severity'), 1.0) for d in defects))


RUBRIC_V3 = """
Scope rules (v3):
- Sentences whose sentence_source is "mined" are corpus-attested and cannot
  be edited: never report their naturalness, register or tier. Report a mined
  sentence only if it uses a different sense of the word, and then only once,
  as one defect on core.sentences[i].
- The core definition and sense_fingerprint restate the sense the author was
  GIVEN. Do not report that they are wrong, duplicate another sense, or that
  the sense itself is doubtful; set sense_fit accordingly and move on.
- Count one root cause once: an unnatural anchor sentence is one defect on
  the core sentence, not an extra defect on every block that uses it.
- "Fits the blank" / "also correct" is fatal only when the alternative
  reading is available in plain or polite register at the learner's tier;
  readings that need honorific, classical or dialectal grammar are at most
  minor.
- Polite です/ます in a sentence whose register is declared plain is not a
  defect at tiers T1-T2. particle_selection A and B drawing from the same
  small particle set is minor, not fatal, unless the distractor lists are
  identical.
"""


RUBRIC_V4 = """
Scope rules (v4):
- Each sense below may list MINED sentences: corpus-attested text quoted
  verbatim, which the author may not edit. Mined sentences are out of scope
  for naturalness, register, tier, length, style and furigana of the text
  itself: never report those. Report a mined sentence only if it uses a
  different sense of the word, and then only once, as one defect on
  core.sentences[i].
- The core definition and sense_fingerprint restate the sense the author was
  GIVEN. Do not report that they are wrong, duplicate another sense, or that
  the sense itself is doubtful; set sense_fit accordingly and move on.
- Count one root cause once: an unnatural anchor sentence is one defect on
  the core sentence, not an extra defect on every block that uses it.
- "Fits the blank" / "also correct" is fatal only when the alternative
  reading is available in plain or polite register at the learner's tier;
  readings that need honorific, classical or dialectal grammar are at most
  minor.
- Polite です/ます forms are never a register defect on their own, at any
  tier, even when the declared register is plain. Report register only when
  ONE sentence mixes plain and polite styles, or uses honorific, literary or
  dialectal style that clashes with the declared register.
- level_1 may legitimately have 4 to 8 options (the author over-generates
  and a later filter trims the list): never report the option count. Report
  only distractors that are not real words, do not sound alike, or differ
  only in pitch accent.
- particle_selection A and B drawing from the same small particle set is
  minor, not fatal, unless the distractor lists are identical.
"""


def doc_sha(doc):
    """Content hash of the judged document (canonical JSON), stored per sense so a resume can tell
    whether the document changed since it was judged."""
    return hashlib.sha256(json.dumps(doc, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()[:16]


def load_mined(run, senses_path=None):
    """{sid: [mined sentence texts]} from the run's senses.csv (or an explicit path); {} if none."""
    import csv
    path = senses_path or os.path.join(run, 'senses.csv')
    if not os.path.exists(path):
        return {}
    csv.field_size_limit(10 ** 9)
    out = {}
    for row in csv.DictReader(open(path, encoding='utf-8', newline='')):
        texts = [x.get('text') for x in json.loads(row.get('corpus_sentences') or '[]') if x.get('text')]
        if texts:
            out[str(row['sense_id'])] = texts
    return out


def output_name(source, model, effort, batch, tag, rubric=JUDGE_VERSION):
    """File name for a judge pass; the frozen judge keeps its historic name."""
    proxy = ''
    if (model, effort) != (MODEL, EFFORT):
        proxy = f'.{model}-{effort}' + (f'-b{batch}' if batch != DEFAULT_BATCH else '')
    return f'judge.{source}.v{rubric}{proxy}{tag}.json'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run')
    ap.add_argument('--source', default='reviewed')
    ap.add_argument('--batch', type=int, default=DEFAULT_BATCH)
    ap.add_argument('--tag', default='', help='suffix for a repeat judging (repeatability check)')
    ap.add_argument('--model', default=MODEL, help='PROXY judge model (writes to a distinct file); frozen=opus')
    ap.add_argument('--effort', default=EFFORT, help='PROXY judge effort (writes to a distinct file); frozen=high')
    ap.add_argument('--rubric', type=int, default=JUDGE_VERSION, choices=(2, 3, 4),
                    help='rubric version; 3 adds the scope rules (mined sentences, given definition out of scope); '
                         '4 also injects the gold mined sentences per sense, allows 4-8 level_1 options and polite forms')
    ap.add_argument('--senses', default=None, help='rubric 4: senses.csv with corpus_sentences (default RUN/senses.csv)')
    args = ap.parse_args()
    args.run = os.path.relpath(os.path.abspath(args.run), REPO)
    os.chdir(REPO)
    judges_path = os.path.join(args.run, 'fat_seed', 'rules_judges.md')
    if not os.path.exists(judges_path):
        runner('review-pack', args.run)
    system = SYSTEM.format(judges=open(judges_path, encoding='utf-8').read(), checklist=checklist())
    if args.rubric == 3:
        system = system.replace('=== judge prompts ===', RUBRIC_V3 + '\n=== judge prompts ===', 1)
    mined = {}
    if args.rubric == 4:
        system = system.replace('=== judge prompts ===', RUBRIC_V4 + '\n=== judge prompts ===', 1)
        mined = load_mined(args.run, args.senses)
        if not mined:
            print(f'  [rubric 4] no mined sentences found ({args.senses or os.path.join(args.run, "senses.csv")})', flush=True)

    src = os.path.join(args.run, 'fat_seed', args.source)
    out_path = os.path.join(args.run, 'fat_seed', output_name(args.source, args.model, args.effort, args.batch, args.tag, args.rubric))
    results = load(out_path) if os.path.exists(out_path) else {}
    started = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    meta = results.setdefault('_meta', {'passes': []})  # top-level record; every reader filters on 'score'
    meta['passes'].append({'started': started, 'model': args.model, 'effort': args.effort, 'rubric': args.rubric,
                           'batch': args.batch, 'source': args.source})
    sids = sorted(int(f[:-5]) for f in os.listdir(src))
    todo = []
    unverified = []  # judged before hashes existed: kept as-is, cannot be checked against the document
    rejudged = []  # document changed since it was judged: judged again
    for s in sids:
        doc = load(os.path.join(src, f'{s}.json'))
        if doc.get('skip') or 'variants' not in doc:
            results[str(s)] = {'defects': [], 'skipped': True, 'score': None}
        elif str(s) not in results:
            todo.append(s)
        elif 'doc_sha' not in results[str(s)]:
            unverified.append(s)
        elif results[str(s)]['doc_sha'] != doc_sha(doc):
            rejudged.append(s)
            todo.append(s)
    if unverified or rejudged:
        print(f'  [resume] {len(unverified)} unverified (judged before hashing), {len(rejudged)} changed -> re-judged: '
              f'{rejudged}', flush=True)
    for i in range(0, len(todo), args.batch):
        batch = todo[i:i + args.batch]
        parts = []
        for s in batch:
            doc = load(os.path.join(src, f'{s}.json'))
            part = f'### sense {s}\n```json\n{json.dumps(doc, ensure_ascii=False)}\n```'
            if args.rubric == 4:
                part += (f'\nMined sentences for sense {s} (verbatim corpus text; out of scope for naturalness/register/'
                         f'tier; report only wrong-sense use, once): {json.dumps(mined.get(str(s), []), ensure_ascii=False)}')
            parts.append(part)
        prompt = 'Judge each document below.\n\n' + '\n\n'.join(parts) + f'\n\nReturn results for: {batch}'
        out = call_model(args, system, prompt, f'judge:{batch[0]}+{len(batch)}')
        for s in batch:
            r = out.get(str(s)) or {'defects': [{'severity': 'fatal', 'path': '', 'problem': 'judge returned nothing'}]}
            r['score'] = score(r.get('defects', []))
            r['doc_sha'] = doc_sha(load(os.path.join(src, f'{s}.json')))
            r['judged_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
            results[str(s)] = r
        save(out_path, results)
    meta['passes'][-1]['judged'] = len(todo)
    save(out_path, results)
    scored = [r for r in results.values() if isinstance(r, dict) and r.get('score') is not None]
    sev = {k: sum(1 for r in scored for d in r['defects'] if d.get('severity') == k) for k in W}
    n = len(scored) or 1
    print(json.dumps({'senses': len(scored), 'mean_score': round(sum(r['score'] for r in scored) / n, 2),
                      'fatal_per_sense': round(sev['fatal'] / n, 2), 'major_per_sense': round(sev['major'] / n, 2),
                      'minor_per_sense': round(sev['minor'] / n, 2),
                      'clean_senses': sum(1 for r in scored if not r['defects']),
                      'judged_now': len(todo), 'rejudged_changed': len(rejudged), 'unverified_legacy': len(unverified),
                      'file': out_path}), flush=True)


if __name__ == '__main__':
    main()
