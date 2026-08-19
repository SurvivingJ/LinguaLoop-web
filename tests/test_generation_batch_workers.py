"""Concurrency contract for the ladder batch runner's ``--workers`` path.

``run_chunk`` puts N senses in flight at once (audit B3): wall clock, not
spend, is what makes a full 9,075-sense fill a multi-week job — ~5.5 minutes
per sense is ~35 days serial and ~9 at ``--workers 4``, for the same $305.

Concurrency is only worth having if it changes nothing but the clock, so these
tests hold the three things that are easy to get silently wrong:

  * the report arithmetic must be **identical** at any worker count;
  * a judge outage must still abort the whole chunk (TASK-510 fail-closed),
    and every worker must enter ``batch_mode()`` itself, because that flag is
    thread-local and cannot be inherited from the submitting thread;
  * each worker needs its **own** renderer — ``LadderExerciseRenderer`` keeps
    per-call state in ``last_skips``, so one shared instance would let two
    senses trade deterministic-skip tallies.

Everything is faked: no database, no LLM calls, no money.
"""

from __future__ import annotations

import threading
import time
from collections import namedtuple

import pytest

from scripts import run_generation_batch as batch

Skip = namedtuple('Skip', 'type_code')


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _FakeQuery:
    """Swallows the ``.delete().eq().not_.is_().execute()`` and
    ``.insert().execute()`` chains run_chunk runs against ``exercises``."""

    def __init__(self, sink=None, rows=None):
        self._sink = sink
        self._rows = rows
        self.not_ = self

    def delete(self):
        return self

    def insert(self, rows):
        return _FakeQuery(self._sink, rows)

    def eq(self, *_a, **_k):
        return self

    def is_(self, *_a, **_k):
        return self

    def execute(self):
        if self._rows is not None and self._sink is not None:
            self._sink.extend(self._rows)
        return self


class _FakeDB:
    def __init__(self):
        self.inserted: list = []

    def table(self, _name):
        return _FakeQuery(self.inserted)


class _FakePipeline:
    """Returns the status scripted for each sense_id."""

    statuses: dict = {}
    raises: dict = {}

    def __init__(self, _db=None):
        pass

    def generate_for_sense(self, sense_id, _language_id):
        exc = self.raises.get(sense_id)
        if exc is not None:
            raise exc
        return {'status': self.statuses.get(sense_id, 'success'), 'errors': []}


class _FakeRenderer:
    """Records which instances exist, and sleeps between writing ``last_skips``
    and returning — the window a shared instance would lose to a sibling."""

    instances: list = []
    lock = threading.Lock()

    def __init__(self, _db=None):
        self.last_skips: list = []
        with _FakeRenderer.lock:
            _FakeRenderer.instances.append(self)

    def build_rows(self, sense_id, _language_id):
        self.last_skips = [Skip(type_code=f'skip_{sense_id}')]
        time.sleep(0.01)          # let a sibling worker clobber a shared tally
        return [{'word_sense_id': sense_id}, {'word_sense_id': sense_id}]


@pytest.fixture(autouse=True)
def _wire_fakes(monkeypatch):
    """Point run_chunk's late imports at the fakes; neutralise cost queries."""
    import services.vocabulary_ladder.asset_pipeline as ap
    import services.vocabulary_ladder.exercise_renderer as er
    import services.vocabulary_ladder.queue_drain as qd

    _FakePipeline.statuses = {}
    _FakePipeline.raises = {}
    _FakeRenderer.instances = []

    monkeypatch.setattr(ap, 'VocabAssetPipeline', _FakePipeline)
    monkeypatch.setattr(er, 'LadderExerciseRenderer', _FakeRenderer)
    monkeypatch.setattr(qd, 'enqueue', lambda *a, **k: True)
    monkeypatch.setattr(batch, 'spend_since', lambda *a, **k: 0.0)
    monkeypatch.setattr(batch, '_judge_verdicts_since', lambda *a, **k: {})
    yield


def _senses(n: int) -> list[dict]:
    return [{'sense_id': i, 'lemma': f'word{i}'} for i in range(1, n + 1)]


def _totals(report) -> tuple:
    return (report.succeeded, report.partial, report.failed, report.skipped,
            report.exercises_created, report.queued)


# ---------------------------------------------------------------------------
# The headline invariant: worker count changes the clock, not the arithmetic
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('workers', [1, 2, 4, 8])
def test_report_arithmetic_is_independent_of_worker_count(workers):
    _FakePipeline.statuses = {2: 'skipped', 3: 'failed', 5: 'partial'}
    db = _FakeDB()

    report = batch.run_chunk(db, 1, _senses(10), None, False, workers=workers)

    # 10 senses: 1 skipped, 1 failed, 1 partial, 7 success -> 8 rendered x 2 rows
    assert _totals(report) == (7, 1, 1, 1, 16, 1)
    assert report.attempted == 10
    assert report.aborted_reason is None


@pytest.mark.parametrize('workers', [1, 4])
def test_deterministic_skips_are_attributed_to_the_right_sense(workers):
    """Every rendered sense contributes exactly its own skip tally.

    With one renderer shared across workers, a sibling overwrites `last_skips`
    during the sleep in `build_rows` and the counts come out wrong.
    """
    db = _FakeDB()
    report = batch.run_chunk(db, 1, _senses(8), None, False, workers=workers)

    assert report.skips_by_type == {f'skip_{i}': 1 for i in range(1, 9)}


def test_renderer_is_per_worker_not_per_sense():
    """One renderer per thread — not one per word, which would rebuild the
    lazy ZH script converter on every sense."""
    db = _FakeDB()
    batch.run_chunk(db, 1, _senses(12), None, False, workers=3)

    assert 0 < len(_FakeRenderer.instances) <= 3


# ---------------------------------------------------------------------------
# Fail-closed judging survives the move onto worker threads
# ---------------------------------------------------------------------------

def test_judge_outage_aborts_the_chunk():
    from services.exercise_generation.judges.base import JudgeUnavailable

    _FakePipeline.raises = {4: JudgeUnavailable('ladder_collocation_judge: dead slug')}
    db = _FakeDB()

    report = batch.run_chunk(db, 1, _senses(20), None, False, workers=4)

    assert report.aborted_reason is not None
    assert 'judge unavailable' in report.aborted_reason
    # The outage sense is not counted against the chunk, and the abort stops
    # the queue rather than draining it.
    assert report.succeeded < 20


def test_worker_thread_enters_batch_mode(monkeypatch):
    """The fail-closed flag is thread-local, so a worker that does not enter
    `batch_mode()` itself would silently judge fail-open."""
    import services.vocabulary_ladder.asset_pipeline as ap
    from services.exercise_generation.judges.base import is_batch_mode

    seen: list[bool] = []

    class _Probe(_FakePipeline):
        def generate_for_sense(self, sense_id, _language_id):
            seen.append(is_batch_mode())
            return {'status': 'success', 'errors': []}

    monkeypatch.setattr(ap, 'VocabAssetPipeline', _Probe)
    batch.run_chunk(_FakeDB(), 1, _senses(4), None, False, workers=2)

    assert seen and all(seen), 'every worker must run inside batch_mode()'
    assert not is_batch_mode(), 'batch mode must not leak to the calling thread'


# ---------------------------------------------------------------------------
# Budget ceiling
# ---------------------------------------------------------------------------

def test_ceiling_aborts_the_chunk(monkeypatch):
    monkeypatch.setattr(batch, 'spend_since', lambda *a, **k: 50.0)
    db = _FakeDB()

    report = batch.run_chunk(db, 1, _senses(40), 1.00, False, workers=4)

    assert report.aborted_reason is not None
    assert 'exceeds ceiling' in report.aborted_reason


def test_dry_run_never_starts_a_pool():
    db = _FakeDB()
    report = batch.run_chunk(db, 1, _senses(5), None, True, workers=4)

    assert report.skipped == 5
    assert report.exercises_created == 0
    assert _FakeRenderer.instances == []


# ---------------------------------------------------------------------------
# Stop button
# ---------------------------------------------------------------------------

def test_stop_request_is_recorded_and_halts_the_queue():
    db = _FakeDB()
    stop = threading.Event()

    def _should_stop():
        return stop.is_set()

    # Stop once the pool has had a moment to start.
    threading.Timer(0.05, stop.set).start()

    report = batch.run_chunk(db, 1, _senses(60), None, False,
                             should_stop=_should_stop, workers=2)

    assert report.aborted_reason == 'stop requested'
    assert report.succeeded < 60
