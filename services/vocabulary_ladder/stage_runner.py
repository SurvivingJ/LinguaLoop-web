# services/vocabulary_ladder/stage_runner.py
"""Pure half of the staged CSV exercise-authoring chain (TASK-797).

The chain (wiki/features/csv-exercise-authoring.tech.md §3):

    0   export        senses.csv + prompts.json            (DB read)
    1   core          vocab_prompt1_core                   author
    2   judge core    ladder_p1_sentence_judge             judge (fresh context)
    2b  bridge        level plan + P2/P3/L4/L8/typed prompts (DB read, no write)
    3   exercises     vocab_prompt2_exercises   A/B        author
    4   transforms    vocab_prompt3_transforms  A/B        author
    5   split         L4 / L8 / typed LLM types A/B        author
    6   judge items   the renderer's own judges            judge (fresh context)
    7   assemble      the two batch/answers pairs upload_exercises.py reads

Every stage is ``prepare`` (write call prompts) → someone answers them →
``collect`` (parse, validate per unit, merge). A unit that fails is marked and
the others carry on; stage 7 drops any sense missing an upstream answer and
says why.

This module holds everything that needs no database: unit enumeration, the
item_N envelope (reused from services.batch_prompting, not re-implemented),
per-unit validation, the judge contract and its rubber-stamp gate, and the
stage-7 assembly. scripts/exercise_stage_runner.py owns the DB-touching steps.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from services.batch_prompting import build_batch_prompt, parse_batch_response

# stage number -> output file written by collect/bridge/assemble
STAGE_FILES = {
    1: '01_core.json',
    2: '02_core.judged.json',
    3: '03_exercises.json',
    4: '04_transforms.json',
    5: '05_split.json',
    6: '06_items.judged.json',
    8: '08_render_judges.json',
}
# Stage 8: the renderer's own judges, answered by a subagent and replayed at
# render time, so building the exercise rows makes no API call either.
RENDER_JUDGE_STAGE = 8
PLAN_FILE = '02b_plan.json'
PLAN_CSV = 'plan.csv'
UPLOAD_DIR = '07_upload'

AUTHOR_STAGES = (1, 3, 4, 5)
JUDGE_STAGES = (2, 6)

# Items per call. Stage 1 writes ten sentences per sense; stage 6 carries
# several judge prompts per sense. Per-stage on purpose (spec §7, OPEN).
DEFAULT_WIDTH = {1: 8, 2: 8, 3: 8, 4: 8, 5: 12, 6: 4, 8: 10}

VERDICTS = ('accept', 'rewrite', 'reject')

STATUS_OK, STATUS_SKIP, STATUS_FAILED = 'ok', 'skip', 'failed'


class StageError(Exception):
    """A run-level problem: stop, do not write downstream files."""


# ---------------------------------------------------------------------------
# Units
# ---------------------------------------------------------------------------

@dataclass
class Unit:
    """One item in a call: one sense, or one (sense, variant, part)."""
    unit_id: str
    sense_id: int
    body: str
    variant: str | None = None
    part: str | None = None
    original: Any = None          # judge stages: the artifact being judged
    meta: dict = field(default_factory=dict)


def unit_id(sense_id: int, variant: str | None = None, part: str | None = None) -> str:
    return ':'.join(str(p) for p in (sense_id, variant, part) if p is not None)


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

def read_json(path: str):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def write_json(path: str, value) -> None:
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(value, fh, ensure_ascii=False, indent=2)


def stage_output(run_dir: str, stage: int) -> dict:
    path = os.path.join(run_dir, STAGE_FILES[stage])
    return read_json(path) if os.path.exists(path) else {'stage': stage, 'units': {}}


def _round_numbers(base: str) -> list[int]:
    return sorted(int(d[6:]) for d in (os.listdir(base) if os.path.isdir(base) else [])
                  if d.startswith('round_') and d[6:].isdigit())


def next_round_dir(run_dir: str, stage: int) -> str:
    """One past the highest existing round — never a gap, since collect
    always reads the highest."""
    base = os.path.join(run_dir, f'stage{stage}')
    rounds = _round_numbers(base)
    return os.path.join(base, f'round_{(rounds[-1] if rounds else 0) + 1:02d}')


def latest_round_dir(run_dir: str, stage: int) -> str:
    base = os.path.join(run_dir, f'stage{stage}')
    rounds = _round_numbers(base)
    if not rounds:
        raise StageError(f'stage {stage} has not been prepared')
    return os.path.join(base, f'round_{rounds[-1]:02d}')


# ---------------------------------------------------------------------------
# Prepare: units -> envelope call files
# ---------------------------------------------------------------------------

def write_calls(round_dir: str, stage: int, units: list[Unit], width: int,
                preamble: str = '', blocked: dict[str, dict] | None = None) -> dict:
    """Chunk ``units`` into item_N envelopes; one prompt file per call.

    Always enveloped, even a call of one, so the answering side has a single
    response shape: ``{"item_1": ..., "item_k": ...}``. ``blocked`` records
    units that could not be prepared, as ``{unit_id: {sense_id, reason}}``.
    """
    if not units and not blocked:
        raise StageError(f'stage {stage}: nothing to prepare')
    width = max(1, width)
    calls = []
    for n, start in enumerate(range(0, len(units), width), 1):
        chunk = units[start:start + width]
        name = f'call_{n:03d}'
        prompt = build_batch_prompt([u.body for u in chunk])
        if preamble:
            prompt = f'{preamble.strip()}\n\n{prompt}'
        path = os.path.join(round_dir, f'{name}.prompt.md')
        os.makedirs(round_dir, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(prompt)
        calls.append({'call': name, 'units': [u.unit_id for u in chunk],
                      'response_file': f'{name}.response.json'})
    manifest = {
        'stage': stage,
        'width': width,
        'calls': calls,
        'units': {u.unit_id: {'sense_id': u.sense_id, 'variant': u.variant,
                              'part': u.part, 'original': u.original, **u.meta}
                  for u in units},
        'blocked': blocked or {},
    }
    os.makedirs(round_dir, exist_ok=True)
    write_json(os.path.join(round_dir, 'manifest.json'), manifest)
    return manifest


# ---------------------------------------------------------------------------
# Collect: responses -> validated per-unit results
# ---------------------------------------------------------------------------

def canon(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def validate_author_payload(payload) -> tuple[str, Any, str | None]:
    """(status, answer, reason) for one authored item.

    Structural only: the real remap + VocabAssetValidator run in the bridge
    (core) and at stage-6 prepare (exercises), through upload_exercises.
    """
    if isinstance(payload, dict) and payload.get('skip') is True:
        return STATUS_SKIP, None, str(payload.get('reason') or 'no reason given')
    if not isinstance(payload, dict) or not payload:
        return STATUS_FAILED, None, 'answer is not a non-empty JSON object'
    return STATUS_OK, payload, None


def validate_judge_payload(payload, original) -> tuple[str, dict | None, str | None]:
    """(status, record, reason) for one judged item.

    The record is ``{judged, verdict, changed, answer, ratings, notes}``.
    ``changed`` is checked against the actual diff: a judge that claims a
    rewrite it did not make, or rewrites while claiming it did not, is a
    failed item — the flag is the audit trail and must not lie.
    """
    if not isinstance(payload, dict):
        return STATUS_FAILED, None, 'judge response is not an object'
    if payload.get('judged') is not True:
        return STATUS_FAILED, None, 'judged is not true'
    verdict = payload.get('verdict')
    if verdict not in VERDICTS:
        return STATUS_FAILED, None, f'verdict {verdict!r} not in {VERDICTS}'
    changed = payload.get('changed')
    if not isinstance(changed, bool):
        return STATUS_FAILED, None, 'changed is not a boolean'
    answer = payload.get('answer')
    if verdict != 'reject' and not isinstance(answer, dict):
        return STATUS_FAILED, None, 'answer is missing (required unless verdict=reject)'
    if answer is None:
        answer = original
    actually_changed = canon(answer) != canon(original)
    if changed != actually_changed:
        return STATUS_FAILED, None, (
            f'changed={changed} but the answer is '
            f'{"different from" if actually_changed else "identical to"} the input')
    if verdict == 'rewrite' and not changed:
        return STATUS_FAILED, None, 'verdict=rewrite with changed=false'
    if verdict == 'accept' and changed:
        return STATUS_FAILED, None, 'verdict=accept with changed=true (use rewrite)'
    return STATUS_OK, {
        'judged': True, 'verdict': verdict, 'changed': changed, 'answer': answer,
        'ratings': payload.get('ratings'), 'notes': str(payload.get('notes') or ''),
    }, None


def collect_round(round_dir: str, stage: int) -> dict[str, dict]:
    """Parse every response in a round; one result per unit, never silent."""
    manifest = read_json(os.path.join(round_dir, 'manifest.json'))
    judge = stage in JUDGE_STAGES
    results: dict[str, dict] = {}
    # Units that could not even be prepared (e.g. an answer the validator
    # rejects before judging) are recorded as failed, never silently absent.
    for uid, info in (manifest.get('blocked') or {}).items():
        results[uid] = {'sense_id': info['sense_id'], 'variant': None, 'part': None,
                        'status': STATUS_FAILED, 'reason': info['reason']}
    for call in manifest['calls']:
        ids = call['units']
        path = os.path.join(round_dir, call['response_file'])
        if not os.path.exists(path):
            for uid in ids:
                results[uid] = _result(manifest, uid, STATUS_FAILED,
                                       reason=f'no response file {call["response_file"]}')
            continue
        try:
            data = read_json(path)
        except json.JSONDecodeError as exc:
            data = None
            parse_error = f'response is not JSON: {exc}'
        else:
            parse_error = None
        payloads, _missing = parse_batch_response(data, len(ids))
        for pos, uid in enumerate(ids, 1):
            if pos not in payloads:
                results[uid] = _result(manifest, uid, STATUS_FAILED,
                                       reason=parse_error or f'item_{pos} missing or null')
                continue
            if judge:
                original = manifest['units'][uid]['original']
                status, record, reason = validate_judge_payload(payloads[pos], original)
                results[uid] = _result(manifest, uid, status, reason=reason,
                                       **(record or {}))
            else:
                status, answer, reason = validate_author_payload(payloads[pos])
                results[uid] = _result(manifest, uid, status, reason=reason,
                                       answer=answer)
    return results


def _result(manifest: dict, uid: str, status: str, reason: str | None = None, **extra) -> dict:
    unit = manifest['units'][uid]
    out = {'sense_id': unit['sense_id'], 'variant': unit.get('variant'),
           'part': unit.get('part'), 'status': status}
    if reason:
        out['reason'] = reason
    out.update({k: v for k, v in extra.items() if v is not None or k == 'answer'})
    if status != STATUS_OK:
        out.pop('answer', None)
    return out


def merge_results(existing: dict, results: dict[str, dict], stage: int) -> dict:
    """Later rounds overwrite the units they re-ran; others are kept."""
    units = dict(existing.get('units') or {})
    units.update(results)
    merged = {'stage': stage, 'units': units}
    if stage in JUDGE_STAGES:
        merged['rubber_stamp'] = is_rubber_stamp(units)
    return merged


def is_rubber_stamp(units: dict[str, dict]) -> bool:
    """True when every judged item came back unchanged.

    That is the signature of a judge that read nothing, not of a clean batch
    (spec §3.2), and it fails the run.
    """
    judged = [u for u in units.values() if u.get('status') == STATUS_OK]
    return bool(judged) and not any(u.get('changed') for u in judged)


def require_judged(run_dir: str, stage: int) -> dict:
    """The judged output, or StageError if it is missing or a rubber stamp."""
    path = os.path.join(run_dir, STAGE_FILES[stage])
    if not os.path.exists(path):
        raise StageError(f'stage {stage} (judge) has not been collected — '
                         f'a judge pass that did not run is recorded as not run')
    out = read_json(path)
    if out.get('rubber_stamp'):
        raise StageError(f'stage {stage} is a rubber stamp: every judged item '
                         f'is changed:false. Re-run the judging skill in a fresh '
                         f'context.')
    return out


# ---------------------------------------------------------------------------
# Judge bodies
# ---------------------------------------------------------------------------

JUDGE_RETURN_CONTRACT = """\
Return, for this item, ONE JSON object:
{
  "judged": true,
  "verdict": "accept" | "rewrite" | "reject",
  "changed": true | false,
  "ratings": <the JSON each judge prompt above asks for, keyed by judge name>,
  "answer": <the artifact, in the same numeric-key contract, with every part a
             judge rated 2 or below rewritten so it would pass; unchanged if
             nothing needed it>,
  "notes": "<one line: what you changed and why>"
}
verdict=accept requires changed=false; verdict=rewrite requires changed=true;
verdict=reject drops the sense (answer may be omitted). changed is checked
against the actual diff, so it must be truthful."""


def judge_body(title: str, judge_prompts: list[dict], artifact, guidance: str = '') -> str:
    """One judge item: the captured judge prompts, the artifact, the contract."""
    parts = [f'## {title}']
    if guidance:
        parts.append(guidance.strip())
    if not judge_prompts:
        parts.append('(No judge prompt fired for this artifact. Review it against '
                     'the contract it was written to and return accept or rewrite.)')
    for n, jp in enumerate(judge_prompts, 1):
        label = jp.get('task_name') or 'judge'
        ver = jp.get('template_version')
        parts.append(f'### Judge prompt {n}: {label}'
                     + (f' (v{ver})' if ver is not None else '')
                     + f'\n{jp["prompt"].strip()}')
    parts.append('### Artifact under review\n```json\n'
                 + json.dumps(artifact, ensure_ascii=False, indent=2) + '\n```')
    parts.append(JUDGE_RETURN_CONTRACT)
    return '\n\n'.join(parts)


# ---------------------------------------------------------------------------
# Capturing the prompts real judges would send
# ---------------------------------------------------------------------------

class PromptCaptured(Exception):
    """Raised in place of an LLM call; judges fail open on it."""


@contextlib.contextmanager
def _call_llm_swapped(stand_in, prefix: str = 'services.'):
    """Replace ``call_llm`` with ``stand_in`` in every loaded ``services.*`` module."""
    import services.llm_service as llm_service
    real = llm_service.call_llm

    def swap(to):
        for name, module in list(sys.modules.items()):
            if not (name.startswith(prefix) or module is llm_service):
                continue
            current = getattr(module, 'call_llm', None)
            if current is real or current is stand_in:
                module.call_llm = to

    swap(stand_in)
    try:
        yield
    finally:
        # Sweep again rather than restoring a remembered list: a judge module
        # first imported *inside* the block bound the stand-in at import time
        # and would otherwise keep it for the rest of the process.
        llm_service.call_llm = real
        swap(real)


@contextlib.contextmanager
def capture_llm_calls(prefix: str = 'services.'):
    """Swap ``call_llm`` for a recorder in every loaded ``services.*`` module.

    Lets the real judge functions and the real renderer build their prompts
    exactly as they would live — nothing about prompt construction is copied
    — while no request is sent. Every judge fails open on an exception outside
    batch mode, so the calling code runs to completion.
    """
    captured: list[dict] = []

    def recorder(prompt, *args, **kwargs):
        captured.append({'task_name': kwargs.get('task_name'),
                         'template_version': kwargs.get('template_version'),
                         'prompt': prompt})
        raise PromptCaptured('captured, not sent')

    with _call_llm_swapped(recorder, prefix):
        yield captured


def prompt_key(task_name: str | None, prompt: str) -> str:
    """Stable id for one exact judge request (task label + full prompt text)."""
    import hashlib
    return hashlib.sha256(f'{task_name}\n{prompt}'.encode('utf-8')).hexdigest()[:20]


@contextlib.contextmanager
def replay_llm_calls(answers: dict[str, Any], prefix: str = 'services.'):
    """Answer ``call_llm`` from a subagent's stored answers — never the network.

    ``answers`` maps :func:`prompt_key` → the parsed JSON the judge prompt asks
    for. A request with no stored answer is recorded in the yielded ``misses``
    list and raised as :class:`PromptCaptured` (the judge then fails open), so
    the caller must discard any result built while ``misses`` is non-empty.
    """
    import copy
    misses: list[dict] = []

    def responder(prompt, *args, **kwargs):
        key = prompt_key(kwargs.get('task_name'), prompt)
        if key in answers:
            return copy.deepcopy(answers[key])
        misses.append({'key': key, 'task_name': kwargs.get('task_name'),
                       'template_version': kwargs.get('template_version'),
                       'prompt': prompt})
        raise PromptCaptured('no stored subagent answer for this prompt')

    with _call_llm_swapped(responder, prefix):
        yield misses


RENDER_JUDGE_CONTRACT = """\
Answer the judge prompt above exactly as the judge model would: return only
the JSON object it asks for, with its own keys and its own rating scale. Judge
the candidates as given; do not rewrite them."""


def render_judge_body(task_name: str | None, version, prompt: str, sense_ids: list[int]) -> str:
    head = f'## {task_name or "judge"}' + (f' (v{version})' if version is not None else '')
    head += f' — sense {", ".join(str(s) for s in sense_ids)}'
    return f'{head}\n\n{prompt.strip()}\n\n{RENDER_JUDGE_CONTRACT}'


# ---------------------------------------------------------------------------
# Stage 7: assemble the uploader's inputs
# ---------------------------------------------------------------------------

def variant_parts(variant: dict) -> list[str]:
    """The answer parts a plan variant needs: p2, p3, l4, l8, typed:<code>."""
    parts = [p for p in ('p2', 'p3', 'l4', 'l8') if p in variant]
    parts += [f'typed:{code}' for code in sorted(variant.get('typed') or {})]
    return parts


def exercise_answer_for(sense_id: int, item: dict, stage_units: dict[int, dict]
                        ) -> tuple[dict | None, list[str]]:
    """Reassemble one sense's A/B answer from stages 3-5, or say what is missing."""
    missing: list[str] = []
    entry: dict = {'sense_id': sense_id}
    for v, variant in item['variants'].items():
        ans: dict = {}
        for part in variant_parts(variant):
            stage = 3 if part == 'p2' else 4 if part == 'p3' else 5
            uid = unit_id(sense_id, v, part)
            unit = stage_units[stage].get(uid)
            if not unit or unit.get('status') != STATUS_OK:
                reason = (unit or {}).get('reason') or 'not answered'
                missing.append(f'stage {stage} {uid}: {reason}')
                continue
            if part.startswith('typed:'):
                ans.setdefault('typed', {})[part.split(':', 1)[1]] = unit['answer']
            else:
                ans[part] = unit['answer']
        if variant.get('typed') is not None:
            ans.setdefault('typed', {})
        entry[v] = ans
    return (None if missing else entry), missing


def assemble(run_dir: str, batch_no: int = 1) -> dict:
    """Stage 7: write the two batch/answers pairs; account for every sense."""
    plan = read_json(os.path.join(run_dir, PLAN_FILE))
    judged_core = require_judged(run_dir, 2)['units']
    judged_items = require_judged(run_dir, 6)['units']
    stage_units = {s: stage_output(run_dir, s)['units'] for s in (3, 4, 5)}

    dropped: dict[str, str] = dict(plan.get('dropped') or {})
    core_items, core_answers, ex_items, ex_answers = [], [], [], []

    for item in plan['exercise_items']:
        sid = item['sense_id']
        key = str(sid)
        core_item = plan['core_items'][key]
        judged = judged_items.get(key)
        if not judged or judged.get('status') != STATUS_OK:
            _, missing = exercise_answer_for(sid, item, stage_units)
            dropped[key] = ('stage 6: ' + ((judged or {}).get('reason') or 'not judged')
                            + (f' ({"; ".join(missing)})' if missing else ''))
            continue
        if judged['verdict'] == 'reject':
            dropped[key] = f'stage 6 judge rejected: {judged.get("notes") or "no notes"}'
            continue
        core = judged_core.get(key)
        if not core or core.get('status') != STATUS_OK or core.get('verdict') == 'reject':
            dropped[key] = 'stage 2: core not accepted'
            continue
        core_items.append(core_item)
        core_answers.append({'sense_id': sid, 'answer': core['answer']})
        ex_items.append(item)
        ex_answers.append({'sense_id': sid, **judged['answer']})

    accounted = {str(i['sense_id']) for i in ex_items} | set(dropped)
    unaccounted = [s for s in plan['all_sense_ids'] if str(s) not in accounted]
    for s in unaccounted:
        dropped[str(s)] = 'no stage produced a result for this sense'

    out_dir = os.path.join(run_dir, UPLOAD_DIR)
    header = {'language': plan['language'], 'language_id': plan['language_id'],
              'batch': batch_no}
    stem = f'batch_{batch_no:03d}'
    files = {
        'core_batch': os.path.join(out_dir, f'{stem}.core.batch.json'),
        'core_answers': os.path.join(out_dir, f'{stem}.core.json'),
        'exercises_batch': os.path.join(out_dir, f'{stem}.exercises.batch.json'),
        'exercises_answers': os.path.join(out_dir, f'{stem}.exercises.json'),
        'dropped': os.path.join(out_dir, 'dropped.json'),
    }
    write_json(files['core_batch'], {**header, 'stage': 'core', 'count': len(core_items),
                                     **plan.get('core_header', {}), 'items': core_items})
    write_json(files['core_answers'], core_answers)
    write_json(files['exercises_batch'], {**header, 'stage': 'exercises',
                                          'count': len(ex_items),
                                          **plan.get('exercise_header', {}),
                                          'items': ex_items})
    write_json(files['exercises_answers'], ex_answers)
    write_json(files['dropped'], dropped)
    return {'files': files, 'kept': len(ex_items), 'dropped': dropped}
