#!/usr/bin/env python3
"""Write spot-the-error / pick-the-sentence explanations ahead of time (ADR-064).

Serving generates an item's per-option explanations lazily, the first time a
learner meets it. This batch writes them before anyone asks: for one study
language and one learner language, every active ``spot_incorrect_sentence``
and ``semantic_discrimination`` item whose own notes do not already explain
every sentence gets its explanations generated once, and each word sense gets
ONE immutable Storage file holding all of its items
(``services/explanation_files.py``: ``explanations/{lang}/{sense}.{nl}.p{v}.json``).
Files go to Storage, not the database, which is near its size cap
(wiki/evaluations/explanation-storage-2026-11-27.md).

Per sense (the work unit)
-------------------------
1. Skip the sense when its file already exists (one listing of the
   ``explanations/{lang}/`` folder at the start). Resume is the default: a
   stopped run picks up where it left off; files are never overwritten.
2. Read its exercise content (ADR-049 content file, ``store.fetch_sense``).
3. Per item: skip it when it is not an explainable shape, or when
   ``stored_entries`` says its own notes already explain every sentence in the
   learner's language (served from the notes; no file entry needed).
   Otherwise generate (spot items are given the reviewed corrected sentence
   from ``word_assets``; read in bulk, one query per chunk of senses).
4. Write one file with every item that succeeded. A failed item is listed in
   the report and left to lazy generation at serve time. A sense with no
   success writes nothing. A sense cut short (Ctrl-C twice, a fatal provider
   error, the failure breaker) writes nothing, so a resumed run redoes it whole.

Spend and limits
----------------
* ``--max-cost-usd`` (default 6.0): the provider-reported cost of every call
  is counted through ``llm_service.subscribe_llm_cost_hook`` (a call with no
  reported cost counts at the estimate, $0.00025). Once the total reaches the
  cap no new sense starts; senses in flight finish (a few cents at most).
* HTTP 402, 401, and 403 "limit"/"credit" answers (OpenRouter: insufficient
  credits, key limit reached, bad key) stop the run at once: no new sense or
  item starts and the report names the error. So does a run of
  ``--max-consecutive-failures`` failed items in a row (default 30).
* The fallback model is off by default (``--fallback`` turns it on): it costs
  about 60 times the primary, and a failed item is still served lazily.
* ``LLM_CALLS_DB_LOGGING=false`` for this process: each ``llm_calls`` row is
  ~1.3 KB and ~18k of them would push the database over its cap. Calls are
  still logged to ``logs/llm_usage/llm_calls_<date>.csv``.

Concurrency: ``--concurrency`` sense workers (own pool, threads ``prewrite_N``).
Each worker calls ``exercise_explanations.generate`` directly, which calls the
synchronous ``call_llm`` in the same thread; the module's own 4-thread warm
pool and ``services.concurrency``'s ``io`` pool are never waited on from inside
themselves, so there is no nested-pool deadlock.

Stopping: Ctrl-C once = no new senses, in-flight senses finish and are
written. Twice = in-flight senses stop after their current call and are not
written. Three times = exit at once (the report is written first). Every file
on Storage is one PUT, so it is always whole; rerun the same command to resume.

Exit codes: 0 finished (or stopped at --limit-senses / --max-cost-usd), 1 setup
error, 3 fatal provider error or failure breaker, 130 Ctrl-C.

Usage:
    python scripts/prewrite_exercise_explanations.py --language ja --nl en            # dry run
    python scripts/prewrite_exercise_explanations.py --language ja --nl en --apply    # generate + write
    python scripts/prewrite_exercise_explanations.py --language ja --apply --limit-senses 20   # pilot

The dry run (default) lists the inventory, reads each sense's content and
whether its file exists (Storage reads only), and prints counts and the
estimated cost. It makes no model call and writes nothing except the local
JSON report (``--report``; default ``data/exercise_explanations/``).
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

try:
    from _common import admin_db, base_parser, bootstrap
except ImportError:  # run or imported as scripts.<name>
    from scripts._common import admin_db, base_parser, bootstrap

ROOT = bootstrap(log_format='%(asctime)s %(levelname)-7s %(name)s: %(message)s')

from config import Config  # noqa: E402
from services import exercise_explanations as xe  # noqa: E402
from services import llm_service  # noqa: E402
from services.exercise_content import store  # noqa: E402
from services.pagination import fetch_all  # noqa: E402

logger = logging.getLogger('prewrite_explanations')

TYPE_ALIASES = {'spot': xe.SPOT, 'pick': xe.PICK}
EST_COST_PER_ITEM = 0.00025
DEFAULT_MAX_COST_USD = 6.0
DEFAULT_CONCURRENCY = 16
DEFAULT_MAX_CONSECUTIVE_FAILURES = 30
CHUNK_SENSES = 100              # senses per bulk word_assets read / per id-filtered listing
PROGRESS_EVERY_S = 30.0
FILE_READ_DEADLINE_S = 30.0     # read_for_senses deadline for the existence check
STORAGE_HTTP_TIMEOUT_S = 20.0   # the serving default (2s) is tuned for requests, not a batch
WRITE_ATTEMPTS = 3
CONTENT_RETRY_DELAY_S = 1.0
TRANSFORM_ASSETS = ['prompt3_transforms_A', 'prompt3_transforms_B']
DEFAULT_REPORT_DIR = os.path.join(ROOT, 'data', 'exercise_explanations')

# Item outcomes
GENERATED = 'generated'
FAILED = 'failed'
STORED_NOTES = 'skipped_stored_notes'
NOT_EXPLAINABLE = 'skipped_not_explainable'
NO_CONTENT = 'content_unavailable'
TO_GENERATE = 'to_generate'          # dry run
INTERRUPTED = 'interrupted'
ITEM_OUTCOMES = (GENERATED, FAILED, STORED_NOTES, NOT_EXPLAINABLE, NO_CONTENT, TO_GENERATE,
                 INTERRUPTED)

# Sense outcomes
S_WRITTEN = 'written'                # file written by this run
S_EXISTS = 'exists_at_write'         # write_file said the file was already there
S_EXISTING = 'existing'              # file found before any work (resume)
S_NOTHING = 'nothing_to_generate'    # every item skipped; no file needed
S_NO_SUCCESS = 'no_success'          # items to generate, none succeeded; no file
S_INTERRUPTED = 'interrupted'        # cut short; no file, redone on resume
S_WRITE_FAILED = 'write_failed'      # generated but the file write failed; redone on resume
S_PLANNED = 'planned'                # dry run: has items to generate
S_ERROR = 'error'                    # unexpected error in the worker
SENSE_OUTCOMES = (S_WRITTEN, S_EXISTS, S_EXISTING, S_NOTHING, S_NO_SUCCESS, S_INTERRUPTED,
                  S_WRITE_FAILED, S_PLANNED, S_ERROR)

_FATAL_TEXT = ('insufficient credits', 'insufficient_quota', 'requires more credits',
               'key limit exceeded', 'credit limit', 'out of credits')


def is_fatal_provider_error(exc: BaseException) -> bool:
    """True for an error no further call can get past: OpenRouter's 402
    (insufficient credits), 401 (bad key) and 403 key/credit limit."""
    status = getattr(exc, 'status_code', None)
    if status is None:
        status = getattr(getattr(exc, 'response', None), 'status_code', None)
    text = str(exc).lower()
    if status == 429:
        return False            # rate limited: retried inside call_llm, not fatal
    if status in (401, 402):
        return True
    if status == 403 and ('limit' in text or 'credit' in text):
        return True
    return any(t in text for t in _FATAL_TEXT)


def _describe(exc: BaseException) -> str:
    status = getattr(exc, 'status_code', None)
    head = f'{type(exc).__name__}' + (f' {status}' if status is not None else '')
    return f'{head}: {" ".join(str(exc).split())[:300]}'


def _files():
    """services.explanation_files, imported when first needed."""
    return importlib.import_module('services.explanation_files')


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

@dataclass
class SenseUnit:
    sense_id: int
    items: list[dict]              # {'id', 'exercise_type', 'content_version'}


def list_items(db, language_id: int, types: list[str],
               sense_ids: Optional[list[int]] = None) -> list[dict]:
    """Active exercises of ``types`` for the language (every page)."""
    cols = 'id, word_sense_id, exercise_type, content_version'

    def query(chunk=None):
        q = (db.table('exercises').select(cols).eq('language_id', language_id)
             .eq('is_active', True).in_('exercise_type', types))
        if chunk is not None:
            q = q.in_('word_sense_id', chunk)
        return q.order('id')

    if sense_ids is None:
        return fetch_all(query)
    rows: list[dict] = []
    for i in range(0, len(sense_ids), CHUNK_SENSES):
        chunk = sense_ids[i:i + CHUNK_SENSES]
        rows.extend(fetch_all(lambda chunk=chunk: query(chunk)))
    return rows


def group_by_sense(rows: list[dict]) -> tuple[list[SenseUnit], int]:
    """(units sorted by sense id, rows without a sense)."""
    by_sense: dict[int, list[dict]] = defaultdict(list)
    no_sense = 0
    for r in rows:
        sid = r.get('word_sense_id')
        if not sid or not r.get('id'):
            no_sense += 1
            continue
        by_sense[int(sid)].append({'id': str(r['id']), 'exercise_type': r.get('exercise_type'),
                                   'content_version': int(r.get('content_version') or 0)})
    return [SenseUnit(sid, sorted(items, key=lambda i: i['id']))
            for sid, items in sorted(by_sense.items())], no_sense


def load_corrections(db, sense_ids: list[int]) -> Optional[dict[int, list[dict]]]:
    """sense_id -> the ``level_7`` blocks of its transform assets, in one paged
    read. None when the read failed (callers fall back to one query per sense)."""
    if not sense_ids:
        return {}
    try:
        rows = fetch_all(lambda: (db.table('word_assets')
                                  .select('id, sense_id, l7:content->level_7')
                                  .in_('sense_id', sense_ids)
                                  .in_('asset_type', TRANSFORM_ASSETS).order('id')))
    except Exception as exc:
        logger.warning('corrected-sentence bulk read failed for %d senses: %s', len(sense_ids), exc)
        return None
    out: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        if r.get('sense_id') and isinstance(r.get('l7'), dict):
            out[int(r['sense_id'])].append(r['l7'])
    return dict(out)


def match_correction(l7_blocks: list[dict], content: dict) -> Optional[str]:
    """The reviewed corrected sentence for the item's wrong sentence; the same
    rule as ``exercise_explanations.stored_correction``."""
    sents = xe.sentences_of(content)
    if sents is None:
        return None
    wrong = {str(s.get('text')).strip() for s in sents if s.get('is_correct') is False}
    for l7 in l7_blocks:
        if str(l7.get('incorrect_sentence') or '').strip() in wrong and l7.get('corrected_sentence'):
            return str(l7['corrected_sentence']).strip()
    return None


# ---------------------------------------------------------------------------
# Run state
# ---------------------------------------------------------------------------

class CostMeter:
    """Running spend from the llm_service cost hook."""

    def __init__(self, cap_usd: float, on_cap):
        self.cap = cap_usd
        self._on_cap = on_cap
        self._lock = threading.Lock()
        self.reported = 0.0
        self.calls = 0
        self.unreported_calls = 0
        self._unsubscribe = None

    def start(self) -> None:
        self._unsubscribe = llm_service.subscribe_llm_cost_hook(self._on_event)

    def stop(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    def _on_event(self, event: dict) -> None:
        cost = event.get('cost_usd')
        with self._lock:
            self.calls += 1
            if isinstance(cost, (int, float)):
                self.reported += float(cost)
            else:
                self.unreported_calls += 1
            reached = self.total_locked() >= self.cap
        if reached:
            self._on_cap()

    def total_locked(self) -> float:
        return self.reported + self.unreported_calls * EST_COST_PER_ITEM

    def total(self) -> float:
        with self._lock:
            return self.total_locked()

    def as_dict(self) -> dict:
        with self._lock:
            return {'total_usd': round(self.total_locked(), 6),
                    'reported_usd': round(self.reported, 6), 'calls': self.calls,
                    'calls_without_reported_cost': self.unreported_calls,
                    'estimate_per_unreported_call_usd': EST_COST_PER_ITEM,
                    'max_cost_usd': self.cap}


class CallWatch:
    """Wraps ``llm_service.call_llm`` for the run: records each failed call's
    error for the item being generated on this thread (``generate`` logs and
    swallows them) and reports fatal provider errors at once."""

    def __init__(self, on_fatal):
        self._on_fatal = on_fatal
        self._local = threading.local()
        self._original = None

    def install(self) -> None:
        original = self._original = llm_service.call_llm
        watch = self

        def watched_call_llm(*args, **kwargs):
            try:
                return original(*args, **kwargs)
            except Exception as exc:
                errors = getattr(watch._local, 'errors', None)
                if errors is not None:
                    errors.append(f"{kwargs.get('model') or '?'}: {_describe(exc)}")
                if is_fatal_provider_error(exc):
                    watch._on_fatal(exc)
                raise

        llm_service.call_llm = watched_call_llm

    def uninstall(self) -> None:
        if self._original is not None:
            llm_service.call_llm = self._original
            self._original = None

    @contextmanager
    def capture(self):
        self._local.errors = errors = []
        try:
            yield errors
        finally:
            self._local.errors = None


@dataclass
class ItemResult:
    exercise_id: str
    exercise_type: str
    outcome: str
    reason: Optional[str] = None
    model: Optional[str] = None
    payload: Optional[dict] = None
    content_version: int = 0
    has_correction: Optional[bool] = None


@dataclass
class SenseResult:
    sense_id: int
    status: str
    items: list[ItemResult] = field(default_factory=list)
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------

class PrewriteRun:
    def __init__(self, db, *, language_id: int, nl_language_id: int, types: list[str],
                 apply: bool, concurrency: int = DEFAULT_CONCURRENCY,
                 max_cost_usd: float = DEFAULT_MAX_COST_USD, limit_senses: Optional[int] = None,
                 max_consecutive_failures: int = DEFAULT_MAX_CONSECUTIVE_FAILURES,
                 out=None):
        self.db = db
        self.language_id = language_id
        self.nl_language_id = nl_language_id
        self.types = types
        self.apply = apply
        self.concurrency = max(1, int(concurrency))
        self.limit = limit_senses
        self.max_consecutive_failures = max_consecutive_failures
        self.out = out or sys.stdout
        self.stop_scheduling = threading.Event()   # no new senses
        self.abort = threading.Event()             # no new items either
        self.stop_reason: Optional[str] = None
        self.fatal_error: Optional[str] = None
        self._state_lock = threading.Lock()
        self._consecutive_failures = 0
        self.cost = CostMeter(max_cost_usd, self._on_cost_cap)
        self.watch = CallWatch(self._on_fatal)
        self.files_available = True
        self.files_error: Optional[str] = None
        self.existing: Optional[set[int]] = None   # senses with a file (from the listing)
        # tallies (main thread only)
        self.sense_counts: Counter = Counter()
        self.item_counts: dict[str, Counter] = defaultdict(Counter)
        self.corrections_found: Counter = Counter()
        self.failures: list[dict] = []
        self.unfinished: list[dict] = []
        self.written_senses: list[int] = []
        self.absorbed = 0                          # sense results back from the workers
        self.created_at = self.started_at = time.monotonic()   # started_at: scheduling began
        self._last_progress = self.started_at
        self.total_target = 0

    # -- stop signals ------------------------------------------------------

    def _stop(self, reason: str, *, abort: bool = False) -> None:
        with self._state_lock:
            if self.stop_reason is None or reason == 'fatal_provider_error':
                self.stop_reason = reason
        self.stop_scheduling.set()
        if abort:
            self.abort.set()

    def _on_cost_cap(self) -> None:
        if not self.stop_scheduling.is_set():
            self._print(f'max cost reached (${self.cost.total():.4f} >= ${self.cost.cap:.2f}): '
                        'no new senses; in-flight senses finish')
        self._stop('max_cost')

    def _on_fatal(self, exc: BaseException) -> None:
        with self._state_lock:
            first = self.fatal_error is None
            if first:
                self.fatal_error = _describe(exc)
        if first:
            self._print(f'FATAL provider error, stopping the run: {self.fatal_error}')
        self._stop('fatal_provider_error', abort=True)

    def _item_done(self, ok: bool) -> None:
        with self._state_lock:
            self._consecutive_failures = 0 if ok else self._consecutive_failures + 1
            tripped = (not ok and self.max_consecutive_failures
                       and self._consecutive_failures >= self.max_consecutive_failures)
        if tripped and not self.abort.is_set():
            self._print(f'{self.max_consecutive_failures} items failed in a row: stopping the run')
            self._stop('consecutive_failures', abort=True)

    # -- per sense (worker threads) ------------------------------------------

    def list_existing(self, units: list[SenseUnit]) -> None:
        """Which senses already have a file, from one listing of the folder (no GET per
        sense). On a listing failure ``existing`` stays None and each worker asks
        ``read_for_senses`` instead."""
        if not self.files_available or not units:
            return
        xf = _files()
        folder = xf.file_path(self.language_id, 0, self.nl_language_id,
                              xe.PROMPT_VERSION).rsplit('/', 1)[0]
        try:
            paths = {o.path for o in store.backend().list(folder)}
        except Exception as exc:
            logger.warning('listing %s failed (%s); checking each sense instead', folder, exc)
            return
        self.existing = {u.sense_id for u in units
                         if xf.file_path(self.language_id, u.sense_id, self.nl_language_id,
                                         xe.PROMPT_VERSION) in paths}
        self._print(f'{len(paths)} files under {folder}/; {len(self.existing)} of the '
                    f'{len(units)} senses already have theirs (skipped)')

    def _exists(self, sense_id: int) -> bool:
        if not self.files_available:
            return False
        if self.existing is not None:
            return sense_id in self.existing
        found = _files().read_for_senses(self.language_id, [sense_id], self.nl_language_id,
                                         xe.PROMPT_VERSION, deadline_s=FILE_READ_DEADLINE_S)
        return bool(found)

    def _contents(self, unit: SenseUnit) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for version in sorted({i['content_version'] for i in unit.items}):
            got = store.fetch_sense(self.language_id, unit.sense_id, version)
            if got is None:            # a timeout is not negative-cached: one more try
                time.sleep(CONTENT_RETRY_DELAY_S)
                got = store.fetch_sense(self.language_id, unit.sense_id, version)
            for item in unit.items:
                if item['content_version'] == version and got and item['id'] in got:
                    out[item['id']] = got[item['id']]
        return out

    def _correction(self, unit: SenseUnit, content: dict,
                    corrections: Optional[dict[int, list[dict]]]) -> Optional[str]:
        if corrections is None:        # the bulk read failed: one query for this sense
            return xe.stored_correction(self.db, unit.sense_id, content)
        return match_correction(corrections.get(unit.sense_id, []), content)

    def process(self, unit: SenseUnit,
                corrections: Optional[dict[int, list[dict]]]) -> SenseResult:
        try:
            return self._process(unit, corrections)
        except Exception as exc:       # one bad sense never stops the run
            logger.exception('sense %s failed', unit.sense_id)
            return SenseResult(unit.sense_id, S_ERROR, error=_describe(exc))

    def _process(self, unit: SenseUnit,
                 corrections: Optional[dict[int, list[dict]]]) -> SenseResult:
        if self.abort.is_set():
            return SenseResult(unit.sense_id, S_INTERRUPTED)
        if self._exists(unit.sense_id):
            return SenseResult(unit.sense_id, S_EXISTING)
        contents = self._contents(unit)
        results: list[ItemResult] = []
        cut_short = False
        for item in unit.items:
            eid, etype, version = item['id'], item['exercise_type'], item['content_version']
            content = contents.get(eid)
            if content is None:
                results.append(ItemResult(eid, etype, NO_CONTENT, content_version=version))
                continue
            sents = xe.sentences_of(content)
            if sents is None:
                results.append(ItemResult(eid, etype, NOT_EXPLAINABLE, content_version=version))
                continue
            if xe.stored_entries(sents, self.nl_language_id) is not None:
                results.append(ItemResult(eid, etype, STORED_NOTES, content_version=version))
                continue
            corrected = (self._correction(unit, content, corrections)
                         if etype == xe.SPOT else None)
            if not self.apply:
                results.append(ItemResult(eid, etype, TO_GENERATE, content_version=version,
                                          has_correction=(corrected is not None
                                                          if etype == xe.SPOT else None)))
                continue
            if self.abort.is_set():
                cut_short = True
                results.append(ItemResult(eid, etype, INTERRUPTED, content_version=version))
                continue
            res = self._generate(eid, etype, version, content, corrected)
            cut_short = cut_short or res.outcome == INTERRUPTED
            results.append(res)
        if not self.apply:
            planned = any(r.outcome == TO_GENERATE for r in results)
            return SenseResult(unit.sense_id, S_PLANNED if planned else S_NOTHING, results)
        if cut_short:
            return SenseResult(unit.sense_id, S_INTERRUPTED, results)
        ok = [r for r in results if r.outcome == GENERATED]
        if not ok:
            wanted = any(r.outcome == FAILED for r in results)
            return SenseResult(unit.sense_id, S_NO_SUCCESS if wanted else S_NOTHING, results)
        return self._write(unit.sense_id, ok, results)

    def _generate(self, eid: str, etype: str, version: int, content: dict,
                  corrected: Optional[str]) -> ItemResult:
        with self.watch.capture() as errors:
            try:
                result = xe.generate(content, self.language_id, self.nl_language_id, eid, etype,
                                     corrected)
            except Exception as exc:   # generate catches call errors; be safe anyway
                errors.append(_describe(exc))
                if is_fatal_provider_error(exc):
                    self._on_fatal(exc)
                result = None
        if result is None:
            if self.fatal_error is not None:     # the provider refused: not this item's fault
                return ItemResult(eid, etype, INTERRUPTED, '; '.join(errors) or None,
                                  content_version=version)
            self._item_done(False)
            return ItemResult(eid, etype, FAILED,
                              '; '.join(errors) or 'no usable answer (failed validation)',
                              content_version=version)
        payload, model = result
        self._item_done(True)
        return ItemResult(eid, etype, GENERATED, model=model, payload=payload,
                          content_version=version)

    def _write(self, sense_id: int, ok: list[ItemResult], results: list[ItemResult]) -> SenseResult:
        exercises = {r.exercise_id: {'content_version': r.content_version, 'model': r.model,
                                     'payload': r.payload} for r in ok}
        last_exc: Optional[Exception] = None
        for attempt in range(WRITE_ATTEMPTS):
            try:
                status = _files().write_file(self.language_id, sense_id, self.nl_language_id,
                                             xe.PROMPT_VERSION, exercises)
                return SenseResult(sense_id, S_WRITTEN if status == 'written' else S_EXISTS,
                                   results)
            except ValueError as exc:  # encode refused the entries: a retry cannot help
                logger.error('sense %s: file not encodable: %s', sense_id, exc)
                return SenseResult(sense_id, S_WRITE_FAILED, results, error=_describe(exc))
            except Exception as exc:
                last_exc = exc
                logger.warning('write failed for sense %s (attempt %d/%d): %s', sense_id,
                               attempt + 1, WRITE_ATTEMPTS, exc)
                if attempt + 1 < WRITE_ATTEMPTS:
                    time.sleep(2.0 * (attempt + 1))
        return SenseResult(sense_id, S_WRITE_FAILED, results, error=_describe(last_exc))

    # -- scheduling (main thread) ---------------------------------------------

    def _absorb(self, res: SenseResult) -> None:
        self.sense_counts[res.status] += 1
        self.absorbed += 1
        if res.status == S_WRITTEN:
            self.written_senses.append(res.sense_id)
        if res.status in (S_INTERRUPTED, S_WRITE_FAILED, S_ERROR):
            self.unfinished.append({'sense_id': res.sense_id, 'status': res.status,
                                    'error': res.error})
        for r in res.items:
            self.item_counts[r.exercise_type][r.outcome] += 1
            if r.has_correction is not None:
                self.corrections_found['with' if r.has_correction else 'without'] += 1
            if r.outcome == FAILED:
                self.failures.append({'sense_id': res.sense_id, 'exercise_id': r.exercise_id,
                                      'exercise_type': r.exercise_type, 'reason': r.reason})

    def run(self, units: list[SenseUnit]) -> None:
        self.list_existing(units)
        if self.existing:              # known from the listing: never scheduled
            self.sense_counts[S_EXISTING] += sum(1 for u in units if u.sense_id in self.existing)
            units = [u for u in units if u.sense_id not in self.existing]
        self.total_target = min(len(units), self.limit) if self.limit is not None else len(units)
        self.started_at = self._last_progress = time.monotonic()
        if self.apply:
            self.cost.start()
            self.watch.install()
        try:
            self._schedule(units)
        finally:
            if self.apply:
                self.watch.uninstall()
                self.cost.stop()

    def _schedule(self, units: list[SenseUnit]) -> None:
        window = self.concurrency * 2
        pool = ThreadPoolExecutor(max_workers=self.concurrency, thread_name_prefix='prewrite')
        prefetch = ThreadPoolExecutor(max_workers=1, thread_name_prefix='prewrite_corr')
        chunks: dict[int, Any] = {}

        def corrections_for(index: int):
            k = index // CHUNK_SENSES
            for j in (k, k + 1):         # this chunk, and the next one in the background
                if j not in chunks and j * CHUNK_SENSES < len(units):
                    ids = [u.sense_id for u in units[j * CHUNK_SENSES:(j + 1) * CHUNK_SENSES]
                           if any(i['exercise_type'] == xe.SPOT for i in u.items)]
                    chunks[j] = prefetch.submit(load_corrections, self.db, ids)
            chunks.pop(k - 1, None)
            return chunks[k].result()

        inflight: dict[Any, SenseUnit] = {}
        next_index = 0
        effective = 0                   # submitted senses that did not come back 'existing'
        interrupts = 0
        try:
            while True:
                try:
                    while (not self.stop_scheduling.is_set() and next_index < len(units)
                           and len(inflight) < window
                           and (self.limit is None or effective < self.limit)):
                        unit = units[next_index]
                        corr = corrections_for(next_index)
                        next_index += 1
                        inflight[pool.submit(self.process, unit, corr)] = unit
                        effective += 1
                    if not inflight:
                        break
                    done, _ = wait(list(inflight), timeout=1.0, return_when=FIRST_COMPLETED)
                    for fut in done:
                        inflight.pop(fut, None)
                        res = fut.result()
                        if res.status == S_EXISTING:
                            effective -= 1
                        self._absorb(res)
                    self._progress()
                except KeyboardInterrupt:
                    interrupts += 1
                    if interrupts == 1:
                        self._stop('interrupted')
                        self._print(f'Ctrl-C: no new senses; waiting for {len(inflight)} in '
                                    'flight to finish (Ctrl-C again to abandon them)')
                    elif interrupts == 2:
                        self._stop('interrupted', abort=True)
                        self._print('Ctrl-C again: in-flight senses stop after their current '
                                    'call and are not written (Ctrl-C again to exit now)')
                    else:
                        raise
        finally:
            not_started = [f for f in inflight if f.cancel()]
            for f in not_started:
                inflight.pop(f, None)
            self.sense_counts['not_reached'] = (len(units) - next_index) + len(not_started)
            if self.limit is not None and next_index < len(units) and self.stop_reason is None:
                self.stop_reason = 'limit'
            pool.shutdown(wait=interrupts < 3)
            prefetch.shutdown(wait=False, cancel_futures=True)
        if self.stop_reason is None:
            self.stop_reason = 'completed'

    # -- output ---------------------------------------------------------------

    def _print(self, msg: str) -> None:
        stamp = datetime.now().strftime('%H:%M:%S')
        print(f'[{stamp}] {msg}', file=self.out, flush=True)

    def items_total(self, outcome: str) -> int:
        return sum(c[outcome] for c in self.item_counts.values())

    def progress_line(self) -> str:
        elapsed = time.monotonic() - self.started_at
        done = self.absorbed
        rate = done / elapsed if elapsed > 0 else 0.0
        remaining = max(0, self.total_target - done)
        eta = f'{remaining / rate / 60:.1f}m' if rate > 0 else '?'
        sc = self.sense_counts
        line = (f'senses {done}/{self.total_target} (written {sc[S_WRITTEN]}, existing '
                f'{sc[S_EXISTING]}, nothing to do {sc[S_NOTHING]}, no success {sc[S_NO_SUCCESS]}, '
                f'unfinished {sc[S_INTERRUPTED] + sc[S_WRITE_FAILED] + sc[S_ERROR]})')
        if self.apply:
            line += (f' | items generated {self.items_total(GENERATED)} failed '
                     f'{self.items_total(FAILED)} | cost ${self.cost.total():.4f}/'
                     f'${self.cost.cap:.2f}')
        else:
            line += f' | items to generate {self.items_total(TO_GENERATE)}'
        return line + f' | {rate:.1f} senses/s | ETA {eta}'

    def _progress(self, force: bool = False) -> None:
        now = time.monotonic()
        if force or now - self._last_progress >= PROGRESS_EVERY_S:
            self._last_progress = now
            self._print(self.progress_line())

    def report(self, **extra) -> dict:
        types = {t: {o: self.item_counts[t][o] for o in ITEM_OUTCOMES if self.item_counts[t][o]}
                 for t in self.types}
        out = {
            'mode': 'apply' if self.apply else 'dry_run',
            'language_id': self.language_id,
            'nl_language_id': self.nl_language_id,
            'prompt_version': xe.PROMPT_VERSION,
            'types': self.types,
            'stop_reason': self.stop_reason,
            'fatal_error': self.fatal_error,
            'duration_s': round(time.monotonic() - self.created_at, 1),
            'senses': {k: self.sense_counts[k] for k in (*SENSE_OUTCOMES, 'not_reached')
                       if self.sense_counts[k]},
            'items_by_type': types,
            'items': {o: self.items_total(o) for o in ITEM_OUTCOMES if self.items_total(o)},
            'explanation_files_available': self.files_available,
            'explanation_files_error': self.files_error,
            'failures': self.failures,
            'unfinished_senses': self.unfinished,
        }
        if self.apply:
            out['cost'] = self.cost.as_dict()
            out['files_written'] = len(self.written_senses)
            out['written_sense_ids'] = sorted(self.written_senses)
        else:
            to_gen = self.items_total(TO_GENERATE)
            out['estimate'] = {'items_to_generate': to_gen,
                               'cost_per_item_usd': EST_COST_PER_ITEM,
                               'est_cost_usd': round(to_gen * EST_COST_PER_ITEM, 4),
                               'spot_items_with_reviewed_correction':
                                   self.corrections_found['with'],
                               'spot_items_without_reviewed_correction':
                                   self.corrections_found['without']}
        out.update(extra)
        return out


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def parse_types(value: str) -> list[str]:
    out = []
    for part in (p.strip() for p in value.split(',') if p.strip()):
        name = TYPE_ALIASES.get(part, part)
        if name not in xe.TYPES:
            raise ValueError(f'unknown type {part!r} (use spot, pick)')
        if name not in out:
            out.append(name)
    if not out:
        raise ValueError('no type given')
    return out


def build_parser():
    parser = base_parser(
        description='Write spot/pick explanations ahead of time as Storage files (ADR-064)',
        apply_help='generate and write the files (default: dry run, no model call, no write)',
        dry_run_help='inventory, counts and estimated cost only (the default)')
    parser.add_argument('--language', default='ja', help='study language code (default ja)')
    parser.add_argument('--nl', default='en', help='learner language code (default en)')
    parser.add_argument('--types', default='spot,pick',
                        help='comma list: spot (spot_incorrect_sentence), pick '
                             '(semantic_discrimination); default both')
    parser.add_argument('--model', default=None,
                        help='primary model (default Config.EXERCISE_EXPLANATION_MODEL)')
    parser.add_argument('--fallback', dest='fallback', action='store_true', default=False,
                        help='also try Config.EXERCISE_EXPLANATION_FALLBACK_MODEL when the '
                             'primary fails (about 60x the cost)')
    parser.add_argument('--no-fallback', dest='fallback', action='store_false',
                        help='primary model only (the default)')
    parser.add_argument('--concurrency', type=int, default=DEFAULT_CONCURRENCY,
                        help=f'sense workers (default {DEFAULT_CONCURRENCY})')
    parser.add_argument('--limit-senses', type=int, default=None,
                        help='process at most N senses (senses whose file exists do not count)')
    parser.add_argument('--sense-ids', default=None, help='comma list of sense ids')
    parser.add_argument('--max-cost-usd', type=float, default=DEFAULT_MAX_COST_USD,
                        help=f'stop starting senses once spend reaches this '
                             f'(default {DEFAULT_MAX_COST_USD})')
    parser.add_argument('--max-consecutive-failures', type=int,
                        default=DEFAULT_MAX_CONSECUTIVE_FAILURES,
                        help='stop after this many failed items in a row (0 = never; '
                             f'default {DEFAULT_MAX_CONSECUTIVE_FAILURES})')
    parser.add_argument('--resume', action='store_true', default=True,
                        help='skip senses whose file exists (always on; files are never '
                             'overwritten)')
    parser.add_argument('--report', default=None, help='JSON report path '
                        '(default data/exercise_explanations/prewrite_<lang>_<nl>_<mode>_<time>.json)')
    parser.add_argument('--verbose', action='store_true',
                        help='keep per-call warnings from exercise_explanations')
    return parser


def _language_id(code: str) -> int:
    lid = Config.LANGUAGE_CODE_TO_ID.get((code or '').strip().lower())
    if not lid:
        raise ValueError(f'unknown language code {code!r} '
                         f'(known: {", ".join(sorted(Config.LANGUAGE_CODE_TO_ID))})')
    return int(lid)


_CONFIG_KEYS = ('EXERCISE_EXPLANATION_MODEL', 'EXERCISE_EXPLANATION_FALLBACK_MODEL',
                'EXERCISE_CONTENT_HTTP_TIMEOUT_S', 'EXERCISE_CONTENT_FETCH_CONCURRENCY')


@contextmanager
def batch_settings(model: str, fallback: bool, concurrency: int):
    """The run's models, batch-sized Storage client settings (read when the
    backend is first built) and DB logging off; restored afterwards."""
    saved = {k: getattr(Config, k, None) for k in _CONFIG_KEYS}
    saved_env = os.environ.get('LLM_CALLS_DB_LOGGING')
    Config.EXERCISE_EXPLANATION_MODEL = model
    if not fallback:
        Config.EXERCISE_EXPLANATION_FALLBACK_MODEL = ''
    Config.EXERCISE_CONTENT_HTTP_TIMEOUT_S = max(
        float(saved['EXERCISE_CONTENT_HTTP_TIMEOUT_S'] or 2.0), STORAGE_HTTP_TIMEOUT_S)
    Config.EXERCISE_CONTENT_FETCH_CONCURRENCY = max(
        int(saved['EXERCISE_CONTENT_FETCH_CONCURRENCY'] or 16), concurrency + 4)
    os.environ['LLM_CALLS_DB_LOGGING'] = 'false'
    try:
        yield
    finally:
        for k, v in saved.items():
            setattr(Config, k, v)
        if saved_env is None:
            os.environ.pop('LLM_CALLS_DB_LOGGING', None)
        else:
            os.environ['LLM_CALLS_DB_LOGGING'] = saved_env


@contextmanager
def _quiet_logs(verbose: bool):
    """Per-call warnings (the report has every failure) and per-request HTTP lines
    off for the run."""
    levels = {'httpx': logging.WARNING, 'httpcore': logging.WARNING, 'openai': logging.WARNING}
    if not verbose:
        levels['services.exercise_explanations'] = logging.ERROR
    saved = {name: logging.getLogger(name).level for name in levels}
    for name, level in levels.items():
        logging.getLogger(name).setLevel(level)
    try:
        yield
    finally:
        for name, level in saved.items():
            logging.getLogger(name).setLevel(level)


def default_report_path(lang: str, nl: str, apply: bool) -> str:
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    mode = 'apply' if apply else 'dryrun'
    return os.path.join(DEFAULT_REPORT_DIR, f'prewrite_{lang}_{nl}_{mode}_{stamp}.json')


def write_report(path: str, report: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def main(argv: Optional[list[str]] = None, *, db=None, out=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out = out or sys.stdout
    try:
        language_id, nl_language_id = _language_id(args.language), _language_id(args.nl)
        types = parse_types(args.types)
        sense_ids = ([int(s) for s in args.sense_ids.split(',') if s.strip()]
                     if args.sense_ids else None)
    except ValueError as exc:
        parser.error(str(exc))
    if args.concurrency < 1:
        parser.error('--concurrency must be at least 1')
    if args.max_cost_usd <= 0:
        parser.error('--max-cost-usd must be above 0')
    if args.limit_senses is not None and args.limit_senses < 0:
        parser.error('--limit-senses must be 0 or more')
    lang, nl = args.language.strip().lower(), args.nl.strip().lower()
    model = (args.model or Config.EXERCISE_EXPLANATION_MODEL or '').strip()
    if args.apply and not model:
        parser.error('no model: pass --model or set EXERCISE_EXPLANATION_MODEL')
    def say(msg: str) -> None:
        print(msg, file=out, flush=True)

    report_path = args.report or default_report_path(lang, nl, args.apply)
    say(f'{"APPLY" if args.apply else "DRY RUN (no model call, no write)"}: '
        f'{lang} explanations for {nl} learners, types {", ".join(types)}, '
        f'prompt v{xe.PROMPT_VERSION}')
    with batch_settings(model, args.fallback, args.concurrency), _quiet_logs(args.verbose):
        say('llm_calls DB logging is OFF for this process (LLM_CALLS_DB_LOGGING=false); '
            'calls are logged to logs/llm_usage/llm_calls_<date>.csv only')
        if args.apply:
            say(f'models: {", ".join(xe._models())} (fallback {"on" if args.fallback else "off"}); '
                f'max cost ${args.max_cost_usd:.2f}; concurrency {args.concurrency}')
        db = db if db is not None else admin_db()
        run = PrewriteRun(db, language_id=language_id, nl_language_id=nl_language_id,
                          types=types, apply=args.apply, concurrency=args.concurrency,
                          max_cost_usd=args.max_cost_usd, limit_senses=args.limit_senses,
                          max_consecutive_failures=args.max_consecutive_failures, out=out)
        try:
            _files()
        except Exception as exc:
            run.files_available = False
            run.files_error = _describe(exc)
            if args.apply:
                say(f'services.explanation_files is not usable: {run.files_error}')
                return 1
            say(f'note: services.explanation_files not importable ({run.files_error}); '
                'existing files are not checked in this dry run')
        rows = list_items(db, language_id, types, sense_ids)
        units, no_sense = group_by_sense(rows)
        by_type = Counter(r.get('exercise_type') for r in rows)
        say(f'inventory: {len(rows)} active items in {len(units)} senses '
            f'({", ".join(f"{t} {by_type[t]}" for t in types)}); {no_sense} without a sense')
        inventory = {'items': len(rows), 'senses': len(units), 'rows_without_sense': no_sense,
                     'items_by_type': {t: by_type[t] for t in types}}
        extra = {'language': lang, 'nl': nl, 'models': xe._models() if args.apply else [model],
                 'fallback': args.fallback, 'llm_calls_db_logging': False,
                 'max_cost_usd': args.max_cost_usd, 'concurrency': args.concurrency,
                 'limit_senses': args.limit_senses, 'sense_ids': sense_ids,
                 'inventory': inventory,
                 'started_at': datetime.now(timezone.utc).isoformat()}
        hard_exit = False
        try:
            run.run(units)
        except KeyboardInterrupt:
            hard_exit = True
        report = run.report(**extra, finished_at=datetime.now(timezone.utc).isoformat())
        write_report(report_path, report)
        say(run.progress_line())
        _summary(say, run, report, report_path)
        if hard_exit:
            out.flush()
            os._exit(130)
    if run.stop_reason in ('fatal_provider_error', 'consecutive_failures'):
        return 3
    if run.stop_reason == 'interrupted':
        return 130
    return 0


def _summary(say, run: PrewriteRun, report: dict, report_path: str) -> None:
    say('--- summary ---')
    say(f'stop reason: {report["stop_reason"]}'
        + (f' ({report["fatal_error"]})' if report.get('fatal_error') else ''))
    say(f'senses: {json.dumps(report["senses"])}')
    for t, counts in report['items_by_type'].items():
        say(f'items {t}: {json.dumps(counts)}')
    if run.apply:
        cost = report['cost']
        say(f'files written: {report["files_written"]}; cost ${cost["total_usd"]:.4f} '
            f'over {cost["calls"]} calls ({cost["calls_without_reported_cost"]} without a '
            f'reported cost); failures: {len(report["failures"])}')
        reasons = Counter((f.get('reason') or '')[:80] for f in report['failures'])
        for reason, n in reasons.most_common(5):
            say(f'  {n} x {reason}')
    else:
        est = report['estimate']
        say(f'items to generate: {est["items_to_generate"]}; estimated cost '
            f'${est["est_cost_usd"]:.2f} at ${EST_COST_PER_ITEM}/item '
            f'(cap --max-cost-usd {report["max_cost_usd"]:.2f}); spot items with a reviewed '
            f'correction: {est["spot_items_with_reviewed_correction"]}, without: '
            f'{est["spot_items_without_reviewed_correction"]}')
    say(f'duration: {report["duration_s"]}s; report: {report_path}')


if __name__ == '__main__':
    sys.exit(main())
