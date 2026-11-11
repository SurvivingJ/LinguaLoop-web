"""New-word drill (services/intro_drill.py, ADR-040).

The engine fixture tests/fixtures/intro_drill/engine_cases.json is produced by
the client engine (static/js/session/players/intro_drill.js) and replayed by
tests/unit/intro-drill.test.js; here ``recount`` must reach the same verdict
on the same attempts, so client and server count the same way.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from services import intro_drill as idr

CASES = json.loads((Path(__file__).parent / 'fixtures' / 'intro_drill' / 'engine_cases.json').read_text())


@pytest.mark.parametrize('case', CASES, ids=[c['name'] for c in CASES])
def test_recount_matches_client_engine(case):
    for r in case['results']:
        rc = idr.recount(r['stage'], r['attempts'], r['n_words'], r['formats'])
        assert rc['passed'] == r['expect']['passed'], r['sense_id']
        assert rc['counted'] == r['expect']['counted'], r['sense_id']
        assert rc['target'] == r['expect']['target'], r['sense_id']


def _att(pos, fmt, ok=True, idk=False, gap=4):
    return {'pos': pos, 'format': fmt, 'correct': ok, 'idk': idk, 'gap': gap}


def test_recount_rules():
    # too soon: second right answer 2 items later does not count
    rc = idr.recount(1, [_att(0, 'def_mc'), _att(3, 'rev_mc')], 5, ['def_mc', 'rev_mc'])
    assert rc['counted'] == 1
    # same format twice in a row does not count
    rc = idr.recount(1, [_att(0, 'def_mc'), _att(5, 'def_mc')], 5, ['def_mc', 'rev_mc'])
    assert rc['counted'] == 1
    # idk never counts; cold miss raises target in stages 2-4
    rc = idr.recount(2, [_att(0, 'read_typed', False, True), _att(5, 'def_mc')], 5, ['read_typed', 'def_mc'])
    assert rc['target'] == 4 and rc['counted'] == 1 and rc['cold_correct'] is False
    # the claimed gap is clamped to 0..what the block size allows
    rc = idr.recount(1, [_att(0, 'def_mc', gap=99), _att(2, 'rev_mc', gap=99)], 2, ['def_mc', 'rev_mc'])
    assert rc['counted'] == 2        # 2 words: at most 1 item between repeats is required
    rc = idr.recount(1, [_att(0, 'def_mc', gap=99), _att(2, 'rev_mc', gap=99)], 6, ['def_mc', 'rev_mc'])
    assert rc['counted'] == 1        # 6 words: the gap is 4, one item between is too soon
    # attempts past the cap are ignored
    many = [_att(i * 5, 'def_mc' if i % 2 else 'rev_mc', ok=False) for i in range(20)]
    assert idr.recount(3, many, 5, ['def_mc', 'rev_mc'])['items'] == idr.INTRO_ITEM_CAPS[3]


def test_advance_schedule_and_graduation():
    today = date(2026, 11, 9)
    row = {'intro_history': [], 'family_confidence': {'form_recognition': 0.1}, 'family_success_dates': {}}
    up = idr.advance(row, 1, True, today, {'stage': 1, 'date': '2026-11-09', 'passed': True})
    assert up['intro_stage'] == 2 and up['intro_due_date'] == '2026-11-10'
    up = idr.advance(row, 3, True, today, {'stage': 3})
    assert up['intro_stage'] == 4 and up['intro_due_date'] == '2026-11-11'
    up = idr.advance(row, 2, False, today, {'stage': 2})
    assert 'intro_stage' not in up and up['intro_due_date'] == '2026-11-10'
    hist = [{'stage': s, 'date': d, 'passed': True} for s, d in ((1, '2026-11-05'), (2, '2026-11-06'), (3, '2026-11-07'))]
    up = idr.advance({**row, 'intro_history': hist}, 4, True, today, {'stage': 4, 'date': '2026-11-09', 'passed': True})
    assert up['word_state'] == 'active' and up['current_ring'] == 2 and up['intro_stage'] is None
    assert up['family_confidence']['form_recognition'] == idr.INTRO_GRADUATE_FORM_RECOGNITION
    assert up['family_success_dates']['form_recognition'] == ['2026-11-07', '2026-11-09']


def test_select_block_rows_quota_and_modes():
    rows = [
        {'sense_id': 1, 'intro_stage': 2, 'intro_history': [{'stage': 1}], 'created_at': 'a'},
        {'sense_id': 2, 'intro_stage': 1, 'intro_history': [], 'created_at': 'b'},
        {'sense_id': 3, 'intro_stage': 1, 'intro_history': [{'event': 'queued', 'source': 'prestudy'}], 'created_at': 'c'},
        {'sense_id': 4, 'intro_stage': 1, 'intro_history': [{'event': 'restart'}], 'created_at': 'd'},
    ]
    ids = lambda rs: [r['sense_id'] for r in rs]  # noqa: E731
    assert ids(idr.select_block_rows(rows, 'maintenance', 5)) == [1, 4]
    assert ids(idr.select_block_rows(rows, 'acquisition', 1)) == [1, 4, 3]   # prestudy-queued first
    assert ids(idr.select_block_rows(rows, 'auto', 5)) == [1, 4, 3, 2]
    assert ids(idr.select_block_rows(rows, 'acquisition', 0)) == [1, 4]


def test_word_formats():
    assert idr.word_formats(1, 'ja', True, True, set()) == ['read_typed', 'def_mc', 'read_typed2', 'rev_mc', 'cloze_mc']
    f = idr.word_formats(2, 'ja', True, False, {'use'})
    assert f[0] == 'read_typed' and 'ex_use' in f and 'ex_judge' not in f
    f = idr.word_formats(1, 'en', False, False, set())
    assert 'read_typed' not in f and 'recall_typed' in f and len(f) >= 2
    assert idr.word_formats(4, 'ja', False, False, set())[0] == 'recall_typed'


# ---------------------------------------------------------------------------
# complete_word against a small in-memory DB
# ---------------------------------------------------------------------------

class _Q:
    def __init__(self, db, table):
        self.db, self.table, self.filters, self.op, self.payload = db, table, [], 'select', None

    def select(self, *_a, **_k):
        return self

    def eq(self, k, v):
        self.filters.append(lambda r: r.get(k) == v)
        return self

    def in_(self, k, vs):
        self.filters.append(lambda r: r.get(k) in vs)
        return self

    def limit(self, *_a):
        return self

    def insert(self, rows):
        self.op, self.payload = 'insert', rows if isinstance(rows, list) else [rows]
        return self

    def update(self, upd):
        self.op, self.payload = 'update', upd
        return self

    def execute(self):
        rows = self.db.tables.setdefault(self.table, [])
        if self.op == 'insert':
            rows.extend(dict(r) for r in self.payload)
            return type('R', (), {'data': self.payload})()
        hit = [r for r in rows if all(f(r) for f in self.filters)]
        if self.op == 'update':
            for r in hit:
                r.update(self.payload)
        return type('R', (), {'data': hit})()


class _Db:
    def __init__(self):
        self.tables = {}

    def table(self, name):
        return _Q(self, name)

    def rpc(self, name, params):
        assert name == 'intro_commit_word'
        rows = [r for r in self.tables.get('user_word_ladder', [])
                if r['user_id'] == params['p_user_id'] and r['sense_id'] == params['p_sense_id']]
        ok = bool(rows) and rows[0].get('word_state') == 'intro' and rows[0].get('intro_stage') == params['p_stage']
        if ok:
            self.tables.setdefault('exercise_attempts', []).extend(
                {**a, 'user_id': params['p_user_id'], 'sense_id': params['p_sense_id'], 'source': 'intro'}
                for a in params['p_attempts'])
            rows[0].update(params['p_update'])
        return type('R', (), {'execute': lambda self_: type('D', (), {'data': ok})()})()


@pytest.fixture
def db(monkeypatch):
    d = _Db()
    d.tables['user_word_ladder'] = [{
        'user_id': 'u', 'sense_id': 5, 'word_state': 'intro', 'intro_stage': 1,
        'intro_history': [], 'family_confidence': {}, 'family_success_dates': {}}]
    d.tables['dim_word_senses'] = [{'id': 5, 'dim_vocabulary': {'language_id': 3}}]
    monkeypatch.setattr(idr, '_today', lambda *_a: date(2026, 11, 9))
    monkeypatch.setattr(idr, '_request_generation_if_short', lambda *_a: None)
    import services.study_time as st
    monkeypatch.setattr(st, 'credit_study_time', lambda *a, **k: True)
    import services.vocabulary.knowledge_service as ks
    calls = []
    monkeypatch.setattr(ks.VocabularyKnowledgeService, '__init__', lambda self, _db: None)
    monkeypatch.setattr(ks.VocabularyKnowledgeService, 'update_from_word_tests_batch',
                        lambda self, **k: calls.append(k) or [])
    d.evidence = calls
    return d


def test_complete_word_advances_and_records(db):
    fmts = ['read_typed', 'def_mc', 'read_typed2', 'rev_mc', 'cloze_mc']
    atts = [_att(i * 5, f) for i, f in enumerate(fmts)]
    out = idr.complete_word(db, 'u', {'sense_id': 5, 'stage': 1, 'n_words': 6, 'formats': fmts, 'attempts': atts})
    assert out['ok'] and out['passed'] and out['next_stage'] == 2 and out['next_due'] == '2026-11-10'
    row = db.tables['user_word_ladder'][0]
    assert row['intro_stage'] == 2 and row['intro_history'][-1]['stage'] == 1
    ea = db.tables['exercise_attempts']
    assert len(ea) == 5 and all(r['source'] == 'intro' and r['exercise_id'] is None for r in ea)
    assert db.evidence[0]['results'] == [{'sense_id': 5, 'is_correct': True}]
    assert db.evidence[0]['side_effects'] is False
    # replay of the same stage is a no-op
    again = idr.complete_word(db, 'u', {'sense_id': 5, 'stage': 1, 'n_words': 6, 'formats': fmts, 'attempts': atts})
    assert again['ok'] is False and len(db.tables['exercise_attempts']) == 5


def test_complete_word_rejects_other_users_rows(db):
    out = idr.complete_word(db, 'someone-else', {'sense_id': 5, 'stage': 1, 'attempts': []})
    assert out['ok'] is False


def test_extra_minutes_per_day():
    assert idr.extra_minutes_per_day(0) == 0
    assert idr.extra_minutes_per_day(12) == 9   # 12 words x 17 items x 10 s / 4 days


def test_restart_if_demoted_only_for_drill_words(db):
    row = db.tables['user_word_ladder'][0]
    row.update({'word_state': 'active', 'intro_stage': None, 'current_ring': 1,
                'intro_history': [{'stage': 4, 'passed': True}],
                'family_success_dates': {'form_recognition': ['2026-11-01', '2026-11-03']}})
    assert idr.restart_if_demoted(db, 'u', 5, 3, {'demoted': True, 'current_ring': 1}) is True
    assert row['word_state'] == 'intro' and row['intro_stage'] == 1 and row['intro_due_date'] == '2026-11-10'
    assert row['family_success_dates']['form_recognition'] == []
    assert row['intro_history'][-1]['event'] == 'restart'
    # restart rows bypass the new-word quota
    assert idr.bypasses_quota(row)
    # a legacy word (never in the drill) keeps the ring-1 path
    row.update({'word_state': 'active', 'intro_stage': None, 'intro_history': []})
    assert idr.restart_if_demoted(db, 'u', 5, 3, {'demoted': True, 'current_ring': 1}) is False
    # no demotion, or a demotion that is not to ring 1: nothing happens
    row['intro_history'] = [{'stage': 4}]
    assert idr.restart_if_demoted(db, 'u', 5, 3, {'demoted': False}) is False
    assert idr.restart_if_demoted(db, 'u', 5, 3, {'demoted': True, 'current_ring': 2}) is False


def test_intro_reviews_chunk_in_daily_queue(monkeypatch):
    from routes import study_session as ss
    monkeypatch.setattr(idr, 'due_review_count', lambda *_a: 6)
    queue = [{'kind': 'test', 'id': 't1', 'is_completed': False},
             {'kind': 'practice', 'id': 'practice_acq_1', 'mode': 'acquisition', 'is_completed': False}]
    out = ss._with_intro_reviews(None, 'u', 3, queue, {}, [])
    assert [q['id'] for q in out] == ['t1', 'intro_reviews', 'practice_acq_1']
    assert out[1]['mode'] == 'maintenance' and out[1]['minutes'] == 4
    # an open maintenance chunk already carries them
    maint = queue + [{'kind': 'practice', 'id': 'practice_maint_1', 'mode': 'maintenance', 'is_completed': False}]
    assert ss._with_intro_reviews(None, 'u', 3, maint, {}, []) == maint
    # vocabulary review excluded: never added
    assert ss._with_intro_reviews(None, 'u', 3, queue, {'excluded_modules': ['practice']}, []) == queue
    # done today: stays as a completed item
    done = ss._with_intro_reviews(None, 'u', 3, queue, {}, ['intro_reviews'])
    assert done[1]['is_completed'] is True


def test_review_chunk_added_for_due_prestudy_followups_alone(monkeypatch):
    # A learner with no study plan row has no practice chunks; due prestudy
    # next-day reviews still get a slot so Practice mode shows them.
    from routes import study_session as ss
    monkeypatch.setattr(idr, 'due_review_count', lambda *_a: 0)
    monkeypatch.setattr(ss, '_due_followup_count', lambda *_a: 3)
    queue = [{'kind': 'test', 'id': 't1', 'is_completed': True}]
    out = ss._with_intro_reviews(None, 'u', 1, queue, {}, [])
    assert [q['id'] for q in out] == ['t1', 'intro_reviews']
    assert out[1]['mode'] == 'maintenance' and out[1]['minutes'] == 2   # 3 x 30 s
    monkeypatch.setattr(ss, '_due_followup_count', lambda *_a: 0)
    assert ss._with_intro_reviews(None, 'u', 1, queue, {}, []) == queue
