"""upload_sentence_references.py planning against a fake Supabase client (TASK-906).

Offline. Run: PYTHONPATH=. python -m pytest tests/test_upload_sentence_references.py -q
"""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('upload_sentence_references', os.path.join(ROOT, 'scripts', 'upload_sentence_references.py'))
usr = importlib.util.module_from_spec(spec)
sys.modules['upload_sentence_references'] = usr
spec.loader.exec_module(usr)


class _Q:
    """Minimal query builder: .select/.eq/.in_/.order/.single/.execute over an in-memory table."""

    def __init__(self, rows):
        self._rows = rows
        self._filters = []
        self._single = False

    def select(self, *_):
        return self

    def order(self, *_):
        return self

    def eq(self, col, val):
        self._filters.append(lambda r: r.get(col) == val)
        return self

    def in_(self, col, vals):
        vs = set(vals)
        self._filters.append(lambda r: r.get(col) in vs)
        return self

    def single(self):
        self._single = True
        return self

    def execute(self):
        out = [r for r in self._rows if all(f(r) for f in self._filters)]

        class R:
            pass
        res = R()
        res.data = (out[0] if out else None) if self._single else out
        return res


class FakeDB:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return _Q(self.tables.get(name, []))


def _db(test_hash='h1', sent_hash='h1', existing=None, run_rows=None):
    return FakeDB({
        'tests': [{'id': 'T1', 'transcript_hash': test_hash}],
        'test_sentences': [{'id': 11, 'test_id': 'T1', 'idx': 0, 'transcript_hash': sent_hash},
                           {'id': 12, 'test_id': 'T1', 'idx': 1, 'transcript_hash': sent_hash}],
        'test_sentence_references': (existing or []) + (run_rows or []),
    })


ROWS = [
    {'test_id': 'T1', 'idx': 0, 'l1_language_id': 2, 'l1_text': 'A.', 'review_verdict': 'pass', 'tightness': 0.9, 'entailment_ok': True, 'arm': 'aligned', 'prompt_version': 'sr-1.0', 'author_model': 'm', 'reviewer_model': 'r'},
    {'test_id': 'T1', 'idx': 1, 'l1_language_id': 2, 'l1_text': 'B.', 'review_verdict': 'fail', 'tightness': 0.2, 'entailment_ok': False, 'arm': 'aligned', 'prompt_version': 'sr-1.0', 'author_model': 'm', 'reviewer_model': 'r'},
]


def test_plan_inserts_and_activates_only_pass_rows():
    plan = usr.plan_for_test(_db(), 'T1', ROWS, 'run_00')
    assert 'skip' not in plan
    assert [r['sentence_id'] for r in plan['insert']] == [11, 12]
    assert all(r['is_active'] is False for r in plan['insert'])
    assert plan['activate'] == [(11, 2)] and plan['deactivate'] == []


def test_plan_deactivates_previous_active_row():
    db = _db(existing=[{'id': 99, 'sentence_id': 11, 'l1_language_id': 2, 'is_active': True, 'run_id': 'old'}])
    plan = usr.plan_for_test(db, 'T1', ROWS, 'run_00')
    assert plan['deactivate'] == [99] and plan['activate'] == [(11, 2)]


def test_plan_skips_on_hash_mismatch():
    assert 'skip' in usr.plan_for_test(_db(test_hash='h2'), 'T1', ROWS, 'run_00')
    assert 'skip' in usr.plan_for_test(_db(sent_hash='h2', test_hash='h1'), 'T1', ROWS, 'run_00')


def test_plan_is_idempotent_on_run_id():
    db = _db(run_rows=[{'id': 5, 'sentence_id': 11, 'l1_language_id': 2, 'is_active': True, 'run_id': 'run_00'},
                       {'id': 6, 'sentence_id': 12, 'l1_language_id': 2, 'is_active': False, 'run_id': 'run_00'}])
    plan = usr.plan_for_test(db, 'T1', ROWS, 'run_00')
    assert plan['insert'] == [] and plan['activate'] == [] and plan['deactivate'] == []


def test_plan_skips_unknown_idx():
    rows = ROWS + [dict(ROWS[0], idx=7)]
    assert usr.plan_for_test(_db(), 'T1', rows, 'run_00')['skip'].startswith('idx 7')
