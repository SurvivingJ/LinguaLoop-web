"""scripts/prewrite_exercise_explanations.py: the batch that writes spot/pick
explanations ahead of time as Storage files (ADR-064). Fully offline: a fake
database, the conftest's InMemoryBackend for content and explanation files, and
a fake ``call_llm`` (the real ``generate`` / ``parse`` run on its answers)."""

from __future__ import annotations

import json
import os
import re
from types import SimpleNamespace

import pytest

from config import Config
from scripts import prewrite_exercise_explanations as pw
from services import exercise_explanations as xe
from services import explanation_files as xf
from services import llm_service
from services import supabase_factory
from services.exercise_content import store

JA, EN = 3, 2


# ---------------------------------------------------------------------------
# Fake database: exercises and word_assets
# ---------------------------------------------------------------------------

class _Query:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.cols, self.filters, self.window = None, [], None

    def select(self, cols):
        self.cols = [c.strip() for c in cols.split(',')]
        return self

    def eq(self, col, val):
        self.filters.append((col, lambda v, val=val: v == val))
        return self

    def in_(self, col, vals):
        vals = set(vals)
        self.filters.append((col, lambda v, vals=vals: v in vals))
        return self

    def order(self, col):
        self.order_col = col
        return self

    def range(self, start, end):
        self.window = (start, end)
        return self

    def _project(self, row):
        out = {}
        for col in self.cols:
            alias, _, expr = col.rpartition(':')
            base, _, key = expr.partition('->')
            value = row.get(base)
            if key:
                value = (value or {}).get(key)
            out[alias or base] = value
        return out

    def execute(self):
        self.db.reads.append(self.name)
        rows = [r for r in self.db.tables.get(self.name, [])
                if all(pred(r.get(col)) for col, pred in self.filters)]
        rows.sort(key=lambda r: r[getattr(self, 'order_col', 'id')])
        if self.window:
            rows = rows[self.window[0]:self.window[1] + 1]
        return SimpleNamespace(data=[self._project(r) for r in rows])


class FakeDB:
    def __init__(self):
        self.tables = {'exercises': [], 'word_assets': []}
        self.reads = []

    def table(self, name):
        return _Query(self, name)


def spot(n=0):
    return {'sentences': [
        {'is_correct': True, 'text': f'正しい文{n}です。'},
        {'is_correct': False, 'text': f'間違い文{n}が。', 'error_description': '助詞の誤り'},
        {'is_correct': True, 'text': f'もう一つ{n}です。'},
    ]}


def pick_with_notes():
    return {'target_word': '芋', 'sentences': [
        {'is_correct': True, 'text': '芋が育つ。', 'explanation': 'Potatoes grow underground.'},
        {'is_correct': False, 'text': '芋が泳ぐ。', 'explanation': 'Potatoes do not swim.'},
    ]}


def pick_without_notes():
    return {'target_word': '芋', 'sentences': [
        {'is_correct': True, 'text': '芋を掘る。'},
        {'is_correct': False, 'text': '芋が飛ぶ。', 'explanation': 'Potatoes do not fly.'},
    ]}


def not_explainable():
    return {'sentences': [{'is_correct': True, 'text': '一文だけ。'}]}


class World:
    """Exercises, their content files and transform assets."""

    def __init__(self):
        self.db = FakeDB()
        self.backend = store.backend()
        self._files: dict[int, dict] = {}
        self._n = 0

    def add(self, sense_id, etype, content, version=0, active=True):
        self._n += 1
        eid = f'00000000-0000-4000-8000-{self._n:012d}'
        self.db.tables['exercises'].append({
            'id': eid, 'word_sense_id': sense_id, 'exercise_type': etype, 'language_id': JA,
            'content_version': version, 'is_active': active})
        self._files.setdefault((sense_id, version), {})[eid] = content
        self.backend.seed(store.content_path(JA, sense_id, version),
                          store.encode_sense_file(sense_id, JA, version,
                                                  self._files[(sense_id, version)]))
        return eid

    def correction(self, sense_id, incorrect, corrected, asset_type='prompt3_transforms_A'):
        rows = self.db.tables['word_assets']
        rows.append({'id': len(rows) + 1, 'sense_id': sense_id, 'asset_type': asset_type,
                     'content': {'level_7': {'incorrect_sentence': incorrect,
                                             'corrected_sentence': corrected}}})

    def file(self, sense_id):
        data = self.backend.objects().get(xf.file_path(JA, sense_id, EN, xe.PROMPT_VERSION))
        return None if data is None else json.loads(data)


# ---------------------------------------------------------------------------
# Fake model
# ---------------------------------------------------------------------------

class FakeLLM:
    """call_llm stand-in that answers in the shape ``parse`` accepts.

    ``bad``: exercise ids answered with an unusable reply. ``raise_for``: exercise
    id (or '*') -> exception to raise. ``cost``: what each call reports through the
    real ``_log_llm_call`` (so the cost hook and DB logging switch are exercised).
    """

    def __init__(self, bad=(), raise_for=None, cost=0.0002):
        self.bad, self.raise_for, self.cost = set(bad), dict(raise_for or {}), cost
        self.calls = []
        self.db_logging_seen = []

    def __call__(self, prompt, **kw):
        eid = kw.get('artifact_id')
        self.calls.append({'exercise_id': eid, 'model': kw.get('model'), 'prompt': prompt})
        self.db_logging_seen.append(llm_service.llm_calls_db_logging_enabled())
        exc = self.raise_for.get(eid) or self.raise_for.get('*')
        if exc is not None:
            raise exc
        llm_service._log_llm_call(
            pipeline=kw.get('pipeline'), task_name=kw.get('task_name'), template_version=2,
            model=kw.get('model'), temperature=0.2, seed=None, prompt_hash=None,
            raw_response='{}', parsed_ok=True, schema_ok=None, judge_verdict=None,
            judge_confidence=None, latency_ms=5, artifact_id=eid, cost_usd=self.cost)
        if eid in self.bad:
            return {'sentences': []}
        n = len(re.findall(r'^\d+\. \[', prompt, flags=re.M))
        return {'sentences': [{'index': i, 'meaning': f'Meaning {i}.',
                               'explanation': f'Explanation {i} in English.',
                               'correction': None} for i in range(1, n + 1)]}


class ProviderError(Exception):
    def __init__(self, status_code, message):
        super().__init__(f'Error code: {status_code} - {message}')
        self.status_code = status_code


@pytest.fixture
def world(monkeypatch):
    monkeypatch.setattr(Config, 'EXERCISE_EXPLANATION_MODEL', 'primary/model')
    monkeypatch.setattr(Config, 'EXERCISE_EXPLANATION_FALLBACK_MODEL', 'fallback/model')
    monkeypatch.setenv('LLM_CALLS_DB_LOGGING', 'true')
    inserts, csv_rows = [], []

    class _Admin:
        def table(self, name):
            class _Q:
                def insert(self, row):
                    inserts.append((name, row))
                    return self

                def execute(self):
                    return SimpleNamespace(data=[])
            return _Q()
    monkeypatch.setattr(supabase_factory, 'get_supabase_admin', lambda: _Admin())
    monkeypatch.setattr(supabase_factory, 'get_supabase', lambda: _Admin())
    monkeypatch.setattr(llm_service, '_log_llm_call_csv', csv_rows.append)
    w = World()
    w.llm_inserts, w.csv_rows = inserts, csv_rows
    return w


def run(world, *args, llm=None, monkeypatch=None):
    if llm is not None:
        monkeypatch.setattr(llm_service, 'call_llm', llm)
    else:
        def no_call(*a, **k):
            raise AssertionError('no model call expected')
        monkeypatch.setattr(llm_service, 'call_llm', no_call)
    lines = []
    out = SimpleNamespace(write=lambda s: lines.append(s), flush=lambda: None)
    report_path = os.path.join(world.tmp, 'report.json')
    code = pw.main(['--language', 'ja', '--nl', 'en', '--report', report_path,
                    '--concurrency', '2', *args], db=world.db, out=out)
    with open(report_path, encoding='utf-8') as fh:
        report = json.load(fh)
    return code, report, ''.join(lines)


@pytest.fixture
def basic(world, tmp_path):
    """Sense 10: two spot items (one will fail). Sense 20: a pick item with complete
    English notes and one without. Sense 30: only stored-notes / unexplainable items.
    Sense 40: one spot item that will fail."""
    world.tmp = str(tmp_path)
    w = world
    w.s10a = w.add(10, xe.SPOT, spot(1))
    w.s10b = w.add(10, xe.SPOT, spot(2))
    w.correction(10, '間違い文1が。', '間違い文1を直した。')
    w.s20a = w.add(20, xe.PICK, pick_with_notes())
    w.s20b = w.add(20, xe.PICK, pick_without_notes())
    w.s30a = w.add(30, xe.PICK, pick_with_notes())
    w.s30b = w.add(30, xe.SPOT, not_explainable())
    w.s40a = w.add(40, xe.SPOT, spot(4))
    w.add(50, xe.SPOT, spot(5), active=False)              # inactive: never listed
    w.add(60, 'cloze', spot(6))                             # other type: never listed
    return w


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_dry_run_makes_no_call_and_no_write(basic, monkeypatch):
    def no_generate(*a, **k):
        raise AssertionError('dry run must not generate')
    monkeypatch.setattr(xe, 'generate', no_generate)
    code, report, text = run(basic, monkeypatch=monkeypatch)
    assert code == 0
    assert basic.backend.calls_for('put') == []
    assert report['mode'] == 'dry_run'
    assert report['inventory'] == {'items': 7, 'senses': 4, 'rows_without_sense': 0,
                                   'items_by_type': {xe.SPOT: 4, xe.PICK: 3}}
    assert report['items_by_type'][xe.SPOT] == {'skipped_not_explainable': 1, 'to_generate': 3}
    assert report['items_by_type'][xe.PICK] == {'skipped_stored_notes': 2, 'to_generate': 1}
    assert report['estimate']['items_to_generate'] == 4
    assert report['estimate']['est_cost_usd'] == pytest.approx(4 * pw.EST_COST_PER_ITEM)
    assert report['estimate']['spot_items_with_reviewed_correction'] == 1
    assert report['estimate']['spot_items_without_reviewed_correction'] == 2
    assert report['senses'] == {'nothing_to_generate': 1, 'planned': 3}
    assert 'DRY RUN' in text and 'items to generate: 4' in text


def test_apply_writes_one_file_per_sense_with_only_successful_items(basic, monkeypatch):
    llm = FakeLLM(bad={basic.s10b, basic.s40a})
    code, report, text = run(basic, '--apply', llm=llm, monkeypatch=monkeypatch)
    assert code == 0 and report['stop_reason'] == 'completed'
    # one model per item: the fallback is off by default
    assert sorted(c['exercise_id'] for c in llm.calls) == sorted(
        [basic.s10a, basic.s10b, basic.s20b, basic.s40a])
    assert {c['model'] for c in llm.calls} == {'primary/model'}

    f10 = basic.file(10)
    assert list(f10['exercises']) == [basic.s10a]            # the failed item is not in it
    entry = f10['exercises'][basic.s10a]
    assert entry['content_version'] == 0 and entry['model'] == 'primary/model'
    wrong = [s for s in entry['payload']['sentences'] if not s['is_correct']]
    assert wrong[0]['correction'] == '間違い文1を直した。'     # the reviewed correction
    prompt = next(c['prompt'] for c in llm.calls if c['exercise_id'] == basic.s10a)
    assert 'Corrected sentence: 間違い文1を直した。' in prompt

    f20 = basic.file(20)
    assert list(f20['exercises']) == [basic.s20b]            # stored-notes item skipped
    assert basic.file(30) is None                            # nothing to generate
    assert basic.file(40) is None                            # no success: no file
    assert len(basic.backend.calls_for('put')) == 2

    assert report['files_written'] == 2 and report['written_sense_ids'] == [10, 20]
    assert report['senses'] == {'written': 2, 'nothing_to_generate': 1, 'no_success': 1}
    assert {f['exercise_id'] for f in report['failures']} == {basic.s10b, basic.s40a}
    assert all('no usable answer' in f['reason'] for f in report['failures'])
    assert report['cost']['calls'] == 4
    assert report['cost']['total_usd'] == pytest.approx(4 * 0.0002)
    # the files are what the serving side reads
    got = xf.read_for_senses(JA, [10, 20], EN, xe.PROMPT_VERSION)
    assert set(got) == {basic.s10a, basic.s20b}


def test_db_logging_is_off_during_apply_and_restored_after(basic, monkeypatch):
    llm = FakeLLM()
    code, report, text = run(basic, '--apply', llm=llm, monkeypatch=monkeypatch)
    assert code == 0
    assert llm.db_logging_seen and not any(llm.db_logging_seen)
    assert basic.llm_inserts == []                           # no llm_calls row
    assert len(basic.csv_rows) == len(llm.calls)             # the CSV log still has them
    assert 'DB logging is OFF' in text
    assert report['llm_calls_db_logging'] is False
    assert os.environ['LLM_CALLS_DB_LOGGING'] == 'true'      # restored
    assert Config.EXERCISE_EXPLANATION_FALLBACK_MODEL == 'fallback/model'


def test_fallback_is_opt_in(basic, monkeypatch):
    llm = FakeLLM(bad={basic.s40a})
    run(basic, '--apply', '--fallback', '--sense-ids', '40', llm=llm, monkeypatch=monkeypatch)
    assert [c['model'] for c in llm.calls] == ['primary/model', 'fallback/model']


def test_resume_skips_senses_that_have_a_file(basic, monkeypatch):
    payload = {'sentences': [{'text': 'x', 'is_correct': True, 'meaning': '', 'explanation': 'e',
                              'correction': None}], 'prompt_version': xe.PROMPT_VERSION}
    assert xf.write_file(JA, 10, EN, xe.PROMPT_VERSION,
                         {basic.s10a: {'content_version': 0, 'model': 'old', 'payload': payload}}
                         ) == 'written'
    before = basic.backend.objects()[xf.file_path(JA, 10, EN, xe.PROMPT_VERSION)]
    llm = FakeLLM()
    code, report, text = run(basic, '--apply', llm=llm, monkeypatch=monkeypatch)
    assert code == 0
    assert not {c['exercise_id'] for c in llm.calls} & {basic.s10a, basic.s10b}
    assert basic.backend.objects()[xf.file_path(JA, 10, EN, xe.PROMPT_VERSION)] == before
    assert report['senses']['existing'] == 1
    assert '1 of the 4 senses already have theirs' in text

    # a second run finds every file and makes no call
    llm2 = FakeLLM()
    code, report2, _ = run(basic, '--apply', llm=llm2, monkeypatch=monkeypatch)
    assert llm2.calls == [] and report2['senses'].get('existing') == 3


def test_resume_falls_back_to_per_sense_reads_when_the_listing_fails(basic, monkeypatch):
    payload = {'sentences': [{'text': 'x', 'is_correct': True, 'meaning': '', 'explanation': 'e',
                              'correction': None}], 'prompt_version': xe.PROMPT_VERSION}
    xf.write_file(JA, 10, EN, xe.PROMPT_VERSION,
                  {basic.s10a: {'content_version': 0, 'model': 'old', 'payload': payload}})
    basic.backend.fail_next('list', store.ContentStorageError('list failed'))
    llm = FakeLLM()
    code, report, _ = run(basic, '--apply', llm=llm, monkeypatch=monkeypatch)
    assert code == 0 and report['senses']['existing'] == 1
    assert not {c['exercise_id'] for c in llm.calls} & {basic.s10a, basic.s10b}


def test_limit_senses_counts_only_senses_without_a_file(basic, monkeypatch):
    payload = {'sentences': [{'text': 'x', 'is_correct': True, 'meaning': '', 'explanation': 'e',
                              'correction': None}], 'prompt_version': xe.PROMPT_VERSION}
    xf.write_file(JA, 10, EN, xe.PROMPT_VERSION,
                  {basic.s10a: {'content_version': 0, 'model': 'old', 'payload': payload}})
    llm = FakeLLM()
    code, report, _ = run(basic, '--apply', '--limit-senses', '1', '--concurrency', '1',
                          llm=llm, monkeypatch=monkeypatch)
    assert code == 0 and report['stop_reason'] == 'limit'
    assert [c['exercise_id'] for c in llm.calls] == [basic.s20b]   # sense 20, not 10
    assert report['written_sense_ids'] == [20]


@pytest.fixture
def many(world, tmp_path):
    world.tmp = str(tmp_path)
    world.ids = [world.add(100 + i, xe.SPOT, spot(i)) for i in range(12)]
    return world


def test_max_cost_stops_scheduling_new_senses(many, monkeypatch):
    llm = FakeLLM(cost=0.4)
    code, report, text = run(many, '--apply', '--concurrency', '1', '--max-cost-usd', '1.0',
                             llm=llm, monkeypatch=monkeypatch)
    assert code == 0 and report['stop_reason'] == 'max_cost'
    # the cap is reached on the 3rd call; at most the window (2 senses) was already queued
    assert 3 <= len(llm.calls) <= 5
    assert report['senses']['not_reached'] == 12 - len(llm.calls)
    assert report['files_written'] == len(llm.calls)        # in-flight senses finished whole
    for sid in report['written_sense_ids']:
        assert many.file(sid)['exercises']
    assert report['cost']['total_usd'] >= 1.0
    assert 'max cost reached' in text


def test_cost_without_a_reported_value_counts_at_the_estimate(many, monkeypatch):
    llm = FakeLLM(cost=None)
    code, report, _ = run(many, '--apply', '--sense-ids', '100,101', llm=llm,
                          monkeypatch=monkeypatch)
    assert report['cost']['calls_without_reported_cost'] == 2
    assert report['cost']['total_usd'] == pytest.approx(2 * pw.EST_COST_PER_ITEM)


def test_fatal_credit_error_stops_the_run(many, monkeypatch):
    llm = FakeLLM(raise_for={'*': ProviderError(402, 'Insufficient credits')})
    code, report, text = run(many, '--apply', '--concurrency', '1', llm=llm,
                             monkeypatch=monkeypatch)
    assert code == 3
    assert report['stop_reason'] == 'fatal_provider_error'
    assert '402' in report['fatal_error'] and 'Insufficient credits' in report['fatal_error']
    assert len(llm.calls) == 1                               # nothing after the first refusal
    assert many.backend.calls_for('put') == []
    assert report['failures'] == []                          # not the items' fault
    assert report['items']['interrupted'] >= 1
    assert report['senses']['not_reached'] >= 10
    assert 'FATAL provider error' in text


def test_key_limit_403_is_fatal_and_rate_limit_is_not():
    assert pw.is_fatal_provider_error(ProviderError(403, 'Key limit exceeded'))
    assert pw.is_fatal_provider_error(ProviderError(402, 'This request requires more credits'))
    assert pw.is_fatal_provider_error(ProviderError(401, 'No auth credentials found'))
    assert pw.is_fatal_provider_error(RuntimeError('Insufficient credits'))
    assert not pw.is_fatal_provider_error(ProviderError(429, 'Rate limit exceeded'))
    assert not pw.is_fatal_provider_error(ProviderError(403, 'flagged by moderation'))
    assert not pw.is_fatal_provider_error(ProviderError(500, 'Internal error'))
    assert not pw.is_fatal_provider_error(TimeoutError('timed out'))


def test_failure_breaker_stops_after_consecutive_failures(many, monkeypatch):
    llm = FakeLLM(bad=set(many.ids))
    code, report, _ = run(many, '--apply', '--concurrency', '1',
                          '--max-consecutive-failures', '3', llm=llm, monkeypatch=monkeypatch)
    assert code == 3 and report['stop_reason'] == 'consecutive_failures'
    assert len(llm.calls) == 3
    assert many.backend.calls_for('put') == []


def test_ctrl_c_finishes_in_flight_senses_and_the_run_resumes(many, monkeypatch):
    real_wait, state = pw.wait, {'n': 0}

    def interrupted_wait(*a, **k):
        state['n'] += 1
        if state['n'] == 2:
            raise KeyboardInterrupt
        return real_wait(*a, **k)
    monkeypatch.setattr(pw, 'wait', interrupted_wait)
    llm = FakeLLM()
    code, report, text = run(many, '--apply', '--concurrency', '1', llm=llm,
                             monkeypatch=monkeypatch)
    assert code == 130 and report['stop_reason'] == 'interrupted'
    assert 'Ctrl-C' in text
    written = report['written_sense_ids']
    assert 0 < len(written) < 12 and report['senses']['not_reached'] == 12 - len(written)
    for sid in written:                                      # every file is whole
        assert list(many.file(sid)['exercises']) == [many.ids[sid - 100]]

    monkeypatch.setattr(pw, 'wait', real_wait)
    llm2 = FakeLLM()
    code, report2, _ = run(many, '--apply', llm=llm2, monkeypatch=monkeypatch)
    assert code == 0 and report2['senses']['existing'] == len(written)
    assert len(llm2.calls) == 12 - len(written)
    assert sorted(written + report2['written_sense_ids']) == list(range(100, 112))


def test_content_unavailable_is_counted_and_writes_nothing(world, tmp_path, monkeypatch):
    world.tmp = str(tmp_path)
    eid = world.add(70, xe.SPOT, spot(7))
    world.backend.delete([store.content_path(JA, 70, 0)])
    monkeypatch.setattr(pw, 'CONTENT_RETRY_DELAY_S', 0.0)
    llm = FakeLLM()
    code, report, _ = run(world, '--apply', llm=llm, monkeypatch=monkeypatch)
    assert code == 0 and llm.calls == []
    assert report['items'] == {'content_unavailable': 1}
    assert world.file(70) is None and eid


def test_bulk_correction_read_matches_the_single_sense_rule(world):
    content = spot(9)
    world.correction(90, 'other sentence', 'nope')
    world.correction(90, '間違い文9が。', '間違い文9を直した。', 'prompt3_transforms_B')
    blocks = pw.load_corrections(world.db, [90])[90]
    assert pw.match_correction(blocks, content) == '間違い文9を直した。'
    assert xe.stored_correction(world.db, 90, content) == '間違い文9を直した。'


def test_types_and_languages_are_validated(world, tmp_path, monkeypatch):
    world.tmp = str(tmp_path)
    assert pw.parse_types('spot') == [xe.SPOT]
    assert pw.parse_types('pick,spot') == [xe.PICK, xe.SPOT]
    with pytest.raises(ValueError):
        pw.parse_types('cloze')
    with pytest.raises(SystemExit) as exc:
        pw.main(['--language', 'xx'], db=world.db)
    assert exc.value.code == 2
    with pytest.raises(SystemExit):
        pw.main(['--apply', '--dry-run'], db=world.db)
