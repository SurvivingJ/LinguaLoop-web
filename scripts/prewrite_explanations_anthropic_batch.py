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
WRITE_WORKERS = 16
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


def corrections_for(db, sense_ids: list[int], say) -> dict[int, list[dict]]:
    """sense_id -> level_7 blocks, read in chunks (an ``in.()`` list of thousands of ids
    is too long for the gateway URL); a chunk that fails is read one sense at a time."""
    out: dict[int, list[dict]] = {}
    failed: list[int] = []
    for i in range(0, len(sense_ids), pw.CHUNK_SENSES):
        chunk = sense_ids[i:i + pw.CHUNK_SENSES]
        got = pw.load_corrections(db, chunk)
        if got is None:
            failed.extend(chunk)
        else:
            out.update(got)
    for sid in failed:
        rows = db.table('word_assets').select('content').eq('sense_id', sid) \
            .in_('asset_type', pw.TRANSFORM_ASSETS).execute().data or []
        out[sid] = [r['content']['level_7'] for r in rows
                    if isinstance((r.get('content') or {}).get('level_7'), dict)]
    if failed:
        say(f'corrections: {len(failed)} senses read one at a time after a chunk failed')
    return out


def prepare(db, args, language_id: int, nl_language_id: int, run_dir: str, say) -> dict:
    """Write manifest.jsonl (one line per item to write) and prepare.json (counts).

    A sense is prepared whole or not at all: if any of its items' content cannot
    be read, the sense is left for a later run (a file is immutable, so writing it
    without that item would leave the item out for good).
    """
    sense_ids = [int(s) for s in args.sense_ids.split(',')] if args.sense_ids else None
    rows = pw.list_items(db, language_id, list(xe.TYPES), sense_ids)
    units, no_sense = pw.group_by_sense(rows)
    have = existing_senses(language_id, nl_language_id)
    todo = [u for u in units if u.sense_id not in have]
    if args.limit_senses:
        todo = todo[:args.limit_senses]
    say(f'{len(rows)} items in {len(units)} senses; {len(have)} senses already have a file; '
        f'{len(todo)} to prepare')
    spot_senses = sorted({u.sense_id for u in todo
                          if any(i['exercise_type'] == xe.SPOT for i in u.items)})
    corrections = corrections_for(db, spot_senses, say)

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
    held_back = []
    with ThreadPoolExecutor(FETCH_WORKERS) as pool:
        for unit, got in pool.map(contents, todo):
            missing = [i['id'] for i in unit.items if i['id'] not in got]
            if missing:
                counts['content_unavailable'] += len(missing)
                held_back.append({'sense_id': unit.sense_id, 'reason': 'content_unavailable',
                                  'exercise_ids': missing})
                continue
            for item in unit.items:
                content = got[item['id']]
                sents = xe.sentences_of(content)
                if sents is None:
                    counts['skipped_not_explainable'] += 1
                    continue
                if xe.stored_entries(sents, nl_language_id) is not None:
                    counts['skipped_stored_notes'] += 1
                    continue
                corrected = None
                if item['exercise_type'] == xe.SPOT:
                    corrected = pw.match_correction(corrections.get(unit.sense_id, []), content)
                    counts['spot_with_correction' if corrected else 'spot_without_correction'] += 1
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
            'senses_held_back': held_back, 'rows_without_sense': no_sense, 'items': dict(counts),
            'estimate_usd': estimate_usd(args.model, len(lines))}
    save_json(os.path.join(run_dir, 'prepare.json'), info)
    say(f"items: {dict(counts)}; {len(held_back)} senses held back; "
        f"estimate ${info['estimate_usd']} (batch price, {args.model})")
    return info


def estimate_usd(model: str, n_requests: int) -> float:
    return round(n_requests * MEASURED_COST_PER_ITEM.get(model, 0.02) / 2, 2)


def read_manifest(run_dir: str) -> list[dict]:
    with open(os.path.join(run_dir, 'manifest.jsonl'), encoding='utf-8') as fh:
        return [json.loads(line) for line in fh if line.strip()]


def item_content(rec: dict) -> dict:
    return {'sentences': rec['sentences'], 'target_word': rec.get('target_word')}


# ---------------------------------------------------------------------------
# submit (state in batches.json: {"batches": [...], "pending": {...}|null,
#          "retry": [...], "ledger_written": bool})
# ---------------------------------------------------------------------------

def load_state(run_dir: str) -> dict:
    state = load_json(os.path.join(run_dir, 'batches.json'), {}) or {}
    state.setdefault('batches', [])
    state.setdefault('retry', [])
    state.setdefault('pending', None)
    state.setdefault('ledger_written', False)
    return state


def save_state(run_dir: str, state: dict) -> None:
    save_json(os.path.join(run_dir, 'batches.json'), state)


def build_requests(records: list[dict], info: dict) -> list[dict]:
    requests = []
    for rec in records:
        params = xa.request_params(item_content(rec), info['language_id'], info['nl_language_id'],
                                   rec['exercise_type'], rec.get('corrected'), info['model'],
                                   info['effort'])
        requests.append({'custom_id': rec['custom_id'], 'params': params})
    return requests


def adopt_pending(client, pending: dict, known: set[str], say) -> Optional[str]:
    """The batch a create whose response was lost may have made: one not already
    recorded (``known``), created after the marker (2 s clock allowance), with the
    same number of requests. None when there is none."""
    since = datetime.fromisoformat(pending['marked_at']).timestamp() - 2
    found = []
    for b in client.messages.batches.list(limit=50):
        if b.id in known:
            continue
        created = b.created_at.timestamp() if hasattr(b.created_at, 'timestamp') else 0
        rc = b.request_counts
        total = rc.processing + rc.succeeded + rc.errored + rc.canceled + rc.expired
        if created >= since and total == pending['count']:
            found.append(b.id)
    if len(found) > 1:
        raise SystemExit(f'several batches match the unconfirmed submission {pending}: {found}; '
                         'resolve by hand (cancel duplicates) before resuming')
    if found:
        say(f'adopted batch {found[0]} from an unconfirmed submission')
    return found[0] if found else None


def create_batch(client, records: list[dict], info: dict, run_dir: str, state: dict,
                 kind: str, start: int, say) -> str:
    """One Message Batch, recorded so that a lost response or a crash can't bill twice."""
    pending = state.get('pending')
    if pending and pending['kind'] == kind and pending['start'] == start:
        known = {b['id'] for b in state['batches'] + state['retry']}
        adopted = adopt_pending(client, pending, known, say)
        if adopted:
            batch_id = adopted
            state['pending'] = None
            state['retry' if kind == 'retry' else 'batches'].append(
                {'id': batch_id, 'start': start, 'count': len(records), 'created_at': now_iso()})
            save_state(run_dir, state)
            return batch_id
    state['pending'] = {'kind': kind, 'start': start, 'count': len(records), 'marked_at': now_iso()}
    save_state(run_dir, state)
    # No automatic retry: the SDK sends no idempotency key, so a retried create
    # after a lost response would make (and bill) a second batch.
    batch = client.with_options(max_retries=0).messages.batches.create(
        requests=build_requests(records, info))
    state['pending'] = None
    state['retry' if kind == 'retry' else 'batches'].append(
        {'id': batch.id, 'start': start, 'count': len(records), 'created_at': now_iso()})
    save_state(run_dir, state)
    say(f'submitted {kind} batch {batch.id}: {len(records)} requests')
    return batch.id


def submit(client, manifest: list[dict], info: dict, run_dir: str, state: dict, say) -> list[str]:
    done = sum(b['count'] for b in state['batches'])
    for start in range(done, len(manifest), BATCH_SIZE):
        create_batch(client, manifest[start:start + BATCH_SIZE], info, run_dir, state, 'main',
                     start, say)
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


def gather(client, by_id: dict, info: dict, batch_ids: list[str], tally: dict) -> dict[str, dict]:
    """exercise_id -> {'payload', 'model'} for usable answers; failures in ``tally``."""
    usable: dict[str, dict] = {}
    for batch_id in batch_ids:
        for entry in client.messages.batches.results(batch_id):
            rec = by_id.get(entry.custom_id)
            if rec is None:
                continue
            kind = entry.result.type
            if kind != 'succeeded':
                tally['failed'][entry.custom_id] = kind
                continue
            msg = entry.result.message
            tally['tokens'].update(input=msg.usage.input_tokens, output=msg.usage.output_tokens)
            tally['cost'] += xa.cost_usd(info['model'], msg.usage.input_tokens,
                                         msg.usage.output_tokens, batch=True)
            payload = xa.payload_from_message(msg, item_content(rec), info['nl_language_id'],
                                              rec['exercise_type'], rec.get('corrected'))
            if payload is None:
                tally['failed'][entry.custom_id] = f'unusable ({msg.stop_reason})'
                continue
            tally['failed'].pop(entry.custom_id, None)
            usable[entry.custom_id] = {'payload': payload, 'model': msg.model}
    return usable


def current_versions(db, exercise_ids: list[str]) -> dict[str, int]:
    """exercise_id -> content_version now (inactive rows are left out)."""
    out: dict[str, int] = {}
    for i in range(0, len(exercise_ids), 100):     # ~3.7 KB of ids per URL
        for r in (db.table('exercises').select('id, content_version, is_active')
                  .in_('id', exercise_ids[i:i + 100]).execute().data or []):
            if r.get('is_active', True):
                out[str(r['id'])] = int(r.get('content_version') or 0)
    return out


def collect(client, db, manifest: list[dict], info: dict, run_dir: str, state: dict, say) -> dict:
    """Results of the main batches, one retry batch for what failed, then the files.

    A sense's file is written only when every item of the sense in the manifest
    has a usable answer and its content version is still the current one;
    otherwise the sense is held back (listed in the report) for a later run.
    """
    by_id = {rec['custom_id']: rec for rec in manifest}
    tally = {'failed': {}, 'tokens': Counter(), 'cost': 0.0}
    usable = gather(client, by_id, info, [b['id'] for b in state['batches']], tally)
    failed_recs = [by_id[eid] for eid in by_id if eid not in usable]
    if failed_recs and not state['retry']:
        say(f'{len(failed_recs)} items failed; retrying them once')
        create_batch(client, failed_recs, info, run_dir, state, 'retry', 0, say)
    if state['retry']:
        retry_ids = [b['id'] for b in state['retry']]
        wait_until_ended(client, retry_ids, say)
        usable.update(gather(client, by_id, info, retry_ids, tally))
    versions = current_versions(db, list(by_id))
    per_sense: dict[int, list[dict]] = defaultdict(list)
    for rec in manifest:
        per_sense[rec['sense_id']].append(rec)
    files: Counter = Counter()
    held_back = []
    writable: list[tuple[int, dict]] = []
    for sense_id, recs in sorted(per_sense.items()):
        bad = [r['custom_id'] for r in recs if r['custom_id'] not in usable]
        stale = [r['custom_id'] for r in recs
                 if versions.get(r['custom_id']) != r['content_version']]
        if bad or stale:
            held_back.append({'sense_id': sense_id, 'failed': {e: tally['failed'].get(e, 'missing')
                                                               for e in bad},
                              'stale': stale})
            files['held_back'] += 1
            continue
        writable.append((sense_id, {r['custom_id']: {'content_version': r['content_version'],
                                                     'model': usable[r['custom_id']]['model'],
                                                     'payload': usable[r['custom_id']]['payload']}
                                    for r in recs}))

    def write_one(job):
        sense_id, exercises = job
        for attempt in range(3):
            try:
                return sense_id, xf.write_file(info['language_id'], sense_id,
                                               info['nl_language_id'], xe.PROMPT_VERSION, exercises)
            except Exception as exc:
                logger.warning('write failed for sense %s (attempt %d): %s', sense_id, attempt + 1, exc)
                time.sleep(2.0 * (attempt + 1))
        return sense_id, 'write_failed'

    say(f'writing {len(writable)} files')
    with ThreadPoolExecutor(WRITE_WORKERS) as pool:
        for sense_id, status in pool.map(write_one, writable):
            files[status] += 1
            if status == 'write_failed':
                held_back.append({'sense_id': sense_id, 'failed': {}, 'stale': [],
                                  'write_failed': True})
    cost = round(tally['cost'], 4)
    batch_ids = [b['id'] for b in state['batches'] + state['retry']]
    if not state['ledger_written']:
        try:
            with open(xa.LEDGER, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps({'ts': time.time(), 'model': info['model'], 'batch_ids': batch_ids,
                                     'input_tokens': tally['tokens']['input'],
                                     'output_tokens': tally['tokens']['output'],
                                     'cost_usd': cost, 'via': 'message-batches',
                                     'purpose': 'exercise explanations (ADR-064)'}) + '\n')
            state['ledger_written'] = True
            save_state(run_dir, state)
        except OSError:
            pass
    report = {'collected_at': now_iso(), **{k: v for k, v in info.items() if k != 'senses_held_back'},
              'batch_ids': batch_ids, 'items': len(manifest), 'usable': len(usable),
              'files': dict(files), 'tokens': dict(tally['tokens']), 'cost_usd': cost,
              'held_back': held_back,
              'held_back_at_prepare': info.get('senses_held_back', [])}
    save_json(os.path.join(run_dir, 'report.json'), report)
    say(f"usable {len(usable)}/{len(manifest)}; files {dict(files)}; cost ${cost} "
        f"({tally['tokens']['input']} in / {tally['tokens']['output']} out tokens)")
    return report


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
        state = load_state(run_dir)
        remaining = len(manifest) - sum(b['count'] for b in state['batches'])
        if remaining > 0 and estimate_usd(info['model'], remaining) > args.max_usd:
            say(f"estimate ${estimate_usd(info['model'], remaining)} for the {remaining} requests "
                f"not yet submitted exceeds --max-usd {args.max_usd}: not submitted")
            return 2
        client = xa.make_client()
        submit(client, manifest, info, run_dir, state, say)
        wait_until_ended(client, [b['id'] for b in state['batches']], say)
        collect(client, db, manifest, info, run_dir, state, say)
    return 0


if __name__ == '__main__':
    sys.exit(main())
