#!/usr/bin/env python3
"""Write exercise explanations ahead of time with the Message Batches API (ADR-064).

The owner chose (2026-11-27) to write every Japanese spot-the-error and
pick-the-correct-sentence explanation ahead of time, stored as Storage files
(services/explanation_files.py), billed to their own Anthropic API key
(``CLAUDE_API``) with Claude Sonnet 5.5 through the Message Batches API (half
the standard price). Measured on 20 live items: Sonnet 5.5 at effort medium,
~$0.006 an item standard, ~$0.003 batched, all answers valid.

Stages, each resumable from the run directory (``--run-dir``):

  prepare  senses of the language with no explanation file yet; their content
           from Storage; the items that need one (not explainable or already
           explained by their own English notes: skipped); the reviewed
           corrected sentence of each spot item. Written to manifest.jsonl.
           Read-only: always runs, and is all a run without --apply does.
  submit   one or more Message Batches (BATCH_SIZE requests each) built from
           the manifest with services.explanations_anthropic.request_params
           (the live prompt). Refused when the estimate exceeds --max-usd.
  collect  wait for every batch to end; validate each answer with the live
           parser; write one immutable file per sense with the items that
           passed (services.explanation_files.write_file). Items that failed
           are listed in the report and left for lazy generation at serve time.

Usage:
  python scripts/prewrite_explanations_anthropic_batch.py                    # dry run: inventory + estimate
  python scripts/prewrite_explanations_anthropic_batch.py --limit-senses 20 --apply   # pilot
  python scripts/prewrite_explanations_anthropic_batch.py --apply            # everything
  python scripts/prewrite_explanations_anthropic_batch.py --run-dir DIR --apply       # resume
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Optional

try:
    from _common import bootstrap
except ImportError:  # imported as scripts.<name>
    from scripts._common import bootstrap

ROOT = bootstrap(log_format='%(asctime)s %(levelname)-7s %(name)s: %(message)s')

try:
    import prewrite_exercise_explanations as pw  # noqa: E402
except ImportError:
    from scripts import prewrite_exercise_explanations as pw  # noqa: E402
from config import Config  # noqa: E402
from services import exercise_explanations as xe  # noqa: E402
from services import explanation_files as xf  # noqa: E402
from services import explanations_anthropic as xa  # noqa: E402
from services.exercise_content import store  # noqa: E402

logger = logging.getLogger('prewrite_anthropic_batch')

DEFAULT_MODEL = 'claude-sonnet-5-5'
DEFAULT_EFFORT = 'medium'
DEFAULT_MAX_USD = 80.0
BATCH_SIZE = 5000              # requests per Message Batch (the API allows 100,000 / 256 MB)
POLL_S = 60
FETCH_WORKERS = 16
# Measured 2026-11-27 (20 ja items, effort medium), standard price per item;
# the Batches API bills half.
MEASURED_COST_PER_ITEM = {'claude-opus-5-5': 0.01736, 'claude-sonnet-5-5': 0.00606,
                          'claude-haiku-5-5': 0.00061}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def load_json(path: str, default=None):
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default


def save_json(path: str, data) -> None:
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# prepare
# ---------------------------------------------------------------------------

def existing_senses(language_id: int, nl_language_id: int) -> set[int]:
    """Senses that already have a file for the current prompt version (one listing)."""
    sample = xf.file_path(language_id, 0, nl_language_id, xe.PROMPT_VERSION)
    folder, name = sample.rsplit('/', 1)
    tail = name[1:]                       # '.en.p2.json' after the sense id '0'
    out = set()
    for obj in store.backend().list(folder):
        fname = obj.path.rsplit('/', 1)[-1]
        head = fname[:-len(tail)] if fname.endswith(tail) else ''
        if head.isdigit():
            out.add(int(head))
    return out


def prepare(db, args, language_id: int, nl_language_id: int, run_dir: str, say) -> dict:
    """Write manifest.jsonl (one line per item to write) and prepare.json (counts)."""
    sense_ids = [int(s) for s in args.sense_ids.split(',')] if args.sense_ids else None
    rows = pw.list_items(db, language_id, list(xe.TYPES), sense_ids)
    units, no_sense = pw.group_by_sense(rows)
    have = existing_senses(language_id, nl_language_id)
    todo = [u for u in units if u.sense_id not in have]
    if args.limit_senses:
        todo = todo[:args.limit_senses]
    say(f'{len(rows)} items in {len(units)} senses; {len(have)} senses already have a file; '
        f'{len(todo)} to prepare')
    corrections = pw.load_corrections(db, [u.sense_id for u in todo]) or {}

    def contents(unit):
        out = {}
        for version in sorted({i['content_version'] for i in unit.items}):
            got = store.fetch_sense(language_id, unit.sense_id, version)
            if got is None:
                time.sleep(1.0)
                got = store.fetch_sense(language_id, unit.sense_id, version)
            for item in unit.items:
                if item['content_version'] == version and got and item['id'] in got:
                    out[item['id']] = got[item['id']]
        return unit, out

    counts: Counter = Counter()
    lines = []
    with ThreadPoolExecutor(FETCH_WORKERS) as pool:
        for unit, got in pool.map(contents, todo):
            for item in unit.items:
                content = got.get(item['id'])
                if content is None:
                    counts['content_unavailable'] += 1
                    continue
                sents = xe.sentences_of(content)
                if sents is None:
                    counts['skipped_not_explainable'] += 1
                    continue
                if xe.stored_entries(sents, nl_language_id) is not None:
                    counts['skipped_stored_notes'] += 1
                    continue
                corrected = (pw.match_correction(corrections.get(unit.sense_id, []), content)
                             if item['exercise_type'] == xe.SPOT else None)
                lines.append({'custom_id': item['id'], 'sense_id': unit.sense_id,
                              'exercise_type': item['exercise_type'],
                              'content_version': item['content_version'],
                              'sentences': sents, 'target_word': content.get('target_word'),
                              'corrected': corrected})
                counts['to_write'] += 1
    with open(os.path.join(run_dir, 'manifest.jsonl'), 'w', encoding='utf-8') as fh:
        for line in lines:
            fh.write(json.dumps(line, ensure_ascii=False) + '\n')
    info = {'prepared_at': now_iso(), 'language_id': language_id, 'nl_language_id': nl_language_id,
            'model': args.model, 'effort': args.effort, 'prompt_version': xe.PROMPT_VERSION,
            'senses_total': len(units), 'senses_with_file': len(have), 'senses_prepared': len(todo),
            'rows_without_sense': no_sense, 'items': dict(counts),
            'estimate_usd': round(len(lines) * MEASURED_COST_PER_ITEM.get(args.model, 0.02) / 2, 2)}
    save_json(os.path.join(run_dir, 'prepare.json'), info)
    say(f"items: {dict(counts)}; estimate ${info['estimate_usd']} (batch price, {args.model})")
    return info


def read_manifest(run_dir: str) -> list[dict]:
    with open(os.path.join(run_dir, 'manifest.jsonl'), encoding='utf-8') as fh:
        return [json.loads(line) for line in fh if line.strip()]


def item_content(rec: dict) -> dict:
    return {'sentences': rec['sentences'], 'target_word': rec.get('target_word')}


# ---------------------------------------------------------------------------
# submit
# ---------------------------------------------------------------------------

def submit(client, manifest: list[dict], info: dict, run_dir: str, say) -> list[str]:
    path = os.path.join(run_dir, 'batches.json')
    state = load_json(path, {'batches': []})
    done = sum(b['count'] for b in state['batches'])
    for start in range(done, len(manifest), BATCH_SIZE):
        chunk = manifest[start:start + BATCH_SIZE]
        requests = []
        for rec in chunk:
            params = xa.request_params(item_content(rec), info['language_id'], info['nl_language_id'],
                                       rec['exercise_type'], rec.get('corrected'), info['model'],
                                       info['effort'])
            requests.append({'custom_id': rec['custom_id'], 'params': params})
        batch = client.messages.batches.create(requests=requests)
        state['batches'].append({'id': batch.id, 'start': start, 'count': len(chunk),
                                 'created_at': now_iso()})
        save_json(path, state)
        say(f'submitted batch {batch.id}: {len(chunk)} requests ({start + len(chunk)}/{len(manifest)})')
    return [b['id'] for b in state['batches']]


# ---------------------------------------------------------------------------
# collect
# ---------------------------------------------------------------------------

def wait_until_ended(client, batch_ids: list[str], say) -> None:
    while True:
        statuses = [client.messages.batches.retrieve(b) for b in batch_ids]
        pending = [b for b in statuses if b.processing_status != 'ended']
        totals = Counter()
        for b in statuses:
            rc = b.request_counts
            totals.update(processing=rc.processing, succeeded=rc.succeeded, errored=rc.errored,
                          canceled=rc.canceled, expired=rc.expired)
        say(f'batches ended {len(statuses) - len(pending)}/{len(statuses)}; {dict(totals)}')
        if not pending:
            return
        time.sleep(POLL_S)


def collect(client, manifest: list[dict], info: dict, batch_ids: list[str], run_dir: str,
            say) -> dict:
    by_id = {rec['custom_id']: rec for rec in manifest}
    per_sense: dict[int, dict[str, dict]] = defaultdict(dict)
    outcomes: Counter = Counter()
    failures = []
    tokens = Counter()
    cost = 0.0
    for batch_id in batch_ids:
        for entry in client.messages.batches.results(batch_id):
            rec = by_id.get(entry.custom_id)
            if rec is None:
                continue
            kind = entry.result.type
            if kind != 'succeeded':
                outcomes[kind] += 1
                failures.append({'exercise_id': rec['custom_id'], 'sense_id': rec['sense_id'],
                                 'reason': kind})
                continue
            msg = entry.result.message
            tokens.update(input=msg.usage.input_tokens, output=msg.usage.output_tokens)
            cost += xa.cost_usd(info['model'], msg.usage.input_tokens, msg.usage.output_tokens,
                                batch=True)
            payload = xa.payload_from_message(msg, item_content(rec), info['nl_language_id'],
                                              rec['exercise_type'], rec.get('corrected'))
            if payload is None:
                outcomes['unusable'] += 1
                failures.append({'exercise_id': rec['custom_id'], 'sense_id': rec['sense_id'],
                                 'reason': f'unusable ({msg.stop_reason})'})
                continue
            outcomes['usable'] += 1
            per_sense[rec['sense_id']][rec['custom_id']] = {
                'content_version': rec['content_version'], 'model': msg.model, 'payload': payload}
    written = Counter()
    for sense_id, exercises in sorted(per_sense.items()):
        status = 'write_failed'
        for attempt in range(3):
            try:
                status = xf.write_file(info['language_id'], sense_id, info['nl_language_id'],
                                       xe.PROMPT_VERSION, exercises)
                break
            except Exception as exc:
                logger.warning('write failed for sense %s (attempt %d): %s', sense_id, attempt + 1, exc)
                time.sleep(2.0 * (attempt + 1))
        written[status] += 1
        if status == 'write_failed':
            failures.append({'sense_id': sense_id, 'reason': 'write_failed',
                             'exercise_ids': sorted(exercises)})
    try:
        with open(xa.LEDGER, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps({'ts': time.time(), 'model': info['model'], 'batch_ids': batch_ids,
                                 'input_tokens': tokens['input'], 'output_tokens': tokens['output'],
                                 'cost_usd': round(cost, 4), 'via': 'message-batches',
                                 'purpose': 'exercise explanations (ADR-064)'}) + '\n')
    except OSError:
        pass
    report = {'collected_at': now_iso(), **info, 'batch_ids': batch_ids,
              'answers': dict(outcomes), 'files': dict(written), 'tokens': dict(tokens),
              'cost_usd': round(cost, 4), 'failures': failures}
    save_json(os.path.join(run_dir, 'report.json'), report)
    say(f"answers {dict(outcomes)}; files {dict(written)}; cost ${report['cost_usd']} "
        f"({tokens['input']} in / {tokens['output']} out tokens)")
    return report


# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--language', default='ja')
    ap.add_argument('--nl', default='en')
    ap.add_argument('--model', default=DEFAULT_MODEL, choices=sorted(MEASURED_COST_PER_ITEM))
    ap.add_argument('--effort', default=DEFAULT_EFFORT, choices=['low', 'medium', 'high'])
    ap.add_argument('--limit-senses', type=int, default=0)
    ap.add_argument('--sense-ids', default='')
    ap.add_argument('--max-usd', type=float, default=DEFAULT_MAX_USD,
                    help='refuse to submit when the estimate exceeds this (default %(default)s)')
    ap.add_argument('--run-dir', default='', help='resume this run (default: a new directory)')
    ap.add_argument('--apply', action='store_true',
                    help='submit the batches and write the files (default: prepare only)')
    return ap


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    say = lambda msg: print(f'[{now_iso()}] {msg}', flush=True)  # noqa: E731
    language_id = Config.LANGUAGE_CODE_TO_ID[args.language]
    nl_language_id = Config.LANGUAGE_CODE_TO_ID[args.nl]
    run_dir = args.run_dir or os.path.join(
        pw.DEFAULT_REPORT_DIR,
        f'batch_{args.language}_{args.nl}_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}')
    os.makedirs(run_dir, exist_ok=True)
    say(f'run directory {run_dir}')
    db = pw.admin_db()
    with pw.batch_settings(args.model, False, FETCH_WORKERS):
        info = load_json(os.path.join(run_dir, 'prepare.json'))
        if info is None:
            info = prepare(db, args, language_id, nl_language_id, run_dir, say)
        manifest = read_manifest(run_dir)
        if not args.apply:
            say('dry run: nothing submitted (add --apply)')
            return 0
        if not manifest:
            say('nothing to write')
            return 0
        if info['estimate_usd'] > args.max_usd and not load_json(os.path.join(run_dir, 'batches.json')):
            say(f"estimate ${info['estimate_usd']} exceeds --max-usd {args.max_usd}: not submitted")
            return 2
        client = xa.make_client()
        batch_ids = submit(client, manifest, info, run_dir, say)
        wait_until_ended(client, batch_ids, say)
        collect(client, manifest, info, batch_ids, run_dir, say)
    return 0


if __name__ == '__main__':
    sys.exit(main())
