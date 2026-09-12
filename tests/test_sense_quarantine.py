"""TASK-767 — generators skip quarantined senses before spending on them."""

from unittest.mock import MagicMock

from services.vocabulary import sense_quarantine
from services.vocabulary.sense_quarantine import quarantined_sense_ids


class _FakeTable:
    def __init__(self, rows, fail=False):
        self._rows = rows
        self._fail = fail
        self._ids = []

    def select(self, *_):
        return self

    def in_(self, _col, ids):
        self._ids = list(ids)
        return self

    def execute(self):
        if self._fail:
            raise RuntimeError('db down')
        resp = MagicMock()
        resp.data = [{'sense_id': s} for s in self._ids if s in self._rows]
        return resp


class _FakeDB:
    def __init__(self, blocked, fail=False):
        self.blocked = set(blocked)
        self.fail = fail
        self.tables = []

    def table(self, name):
        self.tables.append(name)
        return _FakeTable(self.blocked, self.fail)


def test_returns_only_blocked_subset():
    db = _FakeDB({2, 5})
    assert quarantined_sense_ids(db, [1, 2, 3, 5]) == {2, 5}
    assert db.tables == ['calibration_anchor_blocklist']


def test_chunks_large_inputs(monkeypatch):
    monkeypatch.setattr(sense_quarantine, '_CHUNK', 2)
    db = _FakeDB({1, 4})
    assert quarantined_sense_ids(db, [1, 2, 3, 4, 5]) == {1, 4}
    assert len(db.tables) == 3


def test_fails_open_on_lookup_error():
    assert quarantined_sense_ids(_FakeDB({1}, fail=True), [1]) == set()


def test_empty_input_makes_no_query():
    db = _FakeDB({1})
    assert quarantined_sense_ids(db, []) == set()
    assert db.tables == []


def test_asset_pipeline_skips_quarantined_sense_without_llm(monkeypatch):
    from services.vocabulary_ladder import asset_pipeline

    monkeypatch.setattr(asset_pipeline, 'is_quarantined', lambda db, sid: True)
    monkeypatch.setattr(asset_pipeline, 'log_stage_seconds', lambda *a, **k: None)

    def _no_llm(*_a, **_k):
        raise AssertionError('Prompt 1 must not run for a quarantined sense')

    monkeypatch.setattr(asset_pipeline.CoreAssetGenerator, 'generate', _no_llm)
    pipeline = asset_pipeline.VocabAssetPipeline(db=MagicMock())
    result = pipeline.generate_for_sense(14968, 2, force=True)

    assert result['status'] == 'skipped'
    assert result['quarantined'] is True


def test_queue_drain_treats_quarantine_as_failure(monkeypatch):
    from services.vocabulary_ladder import asset_pipeline, queue_drain

    class _Pipeline:
        def __init__(self, _db):
            pass

        def generate_for_sense(self, *_a, **_k):
            return {'status': 'skipped', 'quarantined': True, 'errors': []}

    monkeypatch.setattr(asset_pipeline, 'VocabAssetPipeline', _Pipeline)
    db = MagicMock()
    ok, _detail = queue_drain._regenerate(
        db, {'sense_id': 1, 'language_id': 2, 'detail': {}})

    assert ok is False
    # Nothing rendered, nothing deleted: the drain stopped before the renderer.
    db.table.assert_not_called()
