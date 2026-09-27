# tests/test_run_exercise_gen_eval.py
"""Tests for scripts/run_exercise_gen_eval.py (TASK-808 Phase 0 prep harness).

No real Supabase client and no real LLM calls anywhere in this file --
`FakeRealClient` below is the only thing standing in for the database, and
`StubPipeline`/`StubRenderer` stand in for VocabAssetPipeline /
LadderExerciseRenderer so no generator or judge module needs to be mocked
individually. Run with:

    PYTHONPATH=. python -m pytest tests/test_run_exercise_gen_eval.py -q
"""

import importlib.util
import json
import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'scripts', 'run_exercise_gen_eval.py',
)
_spec = importlib.util.spec_from_file_location('run_exercise_gen_eval', _MODULE_PATH)
harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)

from services.vocabulary_ladder.deterministic import Skip  # noqa: E402
from services.vocabulary_ladder.exercise_renderer import LadderExerciseRenderer  # noqa: E402


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _FakeRealBuilder:
    """Chainable stand-in for a real postgrest query builder."""

    def __init__(self, on_execute):
        self._on_execute = on_execute

    def eq(self, *_a, **_kw):
        return self

    def in_(self, *_a, **_kw):
        return self

    def select(self, *_a, **_kw):
        return self

    def single(self, *_a, **_kw):
        return self

    def limit(self, *_a, **_kw):
        return self

    def execute(self):
        return self._on_execute()


class FakeRealTable:
    def __init__(self, name, recorder):
        self.name = name
        self.recorder = recorder

    def insert(self, row):
        def _on_execute():
            self.recorder.setdefault(self.name, []).append(('insert', row))
            return type('R', (), {'data': [row] if isinstance(row, dict) else row})()
        return _FakeRealBuilder(_on_execute)

    def update(self, row):
        def _on_execute():
            self.recorder.setdefault(self.name, []).append(('update', row))
            return type('R', (), {'data': []})()
        return _FakeRealBuilder(_on_execute)

    def select(self, *_a, **_kw):
        def _on_execute():
            return type('R', (), {'data': self.recorder.get(f'{self.name}__select_data', [])})()
        return _FakeRealBuilder(_on_execute)


class FakeRealClient:
    """Records every real write/rpc it is asked to perform, so tests can
    assert the real DB was (or was not) touched."""

    def __init__(self):
        self.recorder: dict = {}
        self.rpc_calls: list = []

    def table(self, name):
        return FakeRealTable(name, self.recorder)

    def rpc(self, name, params=None):
        self.rpc_calls.append((name, params))
        return _FakeRealBuilder(lambda: type('R', (), {'data': []})())


class StubPipeline:
    """Stands in for VocabAssetPipeline: same `_generate_for_sense_impl`
    signature, but performs a single, realistic `_store_asset`-shaped write
    through `self.db` so the write-capture path is exercised for real."""

    def __init__(self, db, canned_result=None, llm_cost=None):
        self.db = db
        self._canned = canned_result or {
            'status': 'success', 'errors': [], 'warnings': [],
            'stage_seconds': {'p1_generate': 0.5},
        }
        self._llm_cost = llm_cost

    def _generate_for_sense_impl(self, sense_id, language_id, force, batch_id):
        if self._llm_cost is not None:
            self.db.table('llm_calls').insert({
                'pipeline': 'vocab_ladder', 'task_name': 'vocab_prompt1_core',
                'model': 'stub-model', 'cost_usd': self._llm_cost,
                'sense_id': sense_id, 'generation_batch_id': batch_id,
            }).execute()
        self.db.table('word_assets').upsert({
            'sense_id': sense_id,
            'language_id': language_id,
            'asset_type': 'prompt1_core',
            'content': {'lemma': 'stub'},
            'model_used': 'stub-model',
            'is_valid': True,
            'validation_errors': None,
            'validation_warnings': None,
            'generation_batch_id': batch_id,
        }, on_conflict='sense_id,asset_type').execute()
        return dict(self._canned, sense_id=sense_id)


class StubRenderer:
    def __init__(self, db, rows=None, skips=None):
        self.db = db
        self._rows = rows if rows is not None else []
        self.last_skips = skips or []

    def build_rows(self, sense_id, language_id):
        return self._rows


# ---------------------------------------------------------------------------
# (a) No DB write escapes -- the guard fires on an unexpected write
# ---------------------------------------------------------------------------

def test_allowed_write_is_captured_not_executed():
    real = FakeRealClient()
    sink, lock = [], threading.Lock()
    client = harness.InterceptingClient(real, sink, lock)

    resp = (
        client.table('word_assets')
        .upsert({'sense_id': 1, 'asset_type': 'prompt1_core', 'is_valid': True},
                on_conflict='sense_id,asset_type')
        .execute()
    )

    assert resp.data == []
    assert 'word_assets' not in real.recorder, "real client must never see the write"
    assert len(sink) == 1
    assert sink[0]['table'] == 'word_assets' and sink[0]['verb'] == 'upsert'


def test_unexpected_table_write_raises():
    real = FakeRealClient()
    sink, lock = [], threading.Lock()
    client = harness.InterceptingClient(real, sink, lock)

    with pytest.raises(harness.UnexpectedWriteError):
        client.table('some_new_content_table').update({'x': 1}).eq('id', 1).execute()

    assert 'some_new_content_table' not in real.recorder


def test_unexpected_rpc_raises_but_allowlisted_rpc_passes_through():
    real = FakeRealClient()
    sink, lock = [], threading.Lock()
    client = harness.InterceptingClient(real, sink, lock)

    with pytest.raises(harness.UnexpectedWriteError):
        client.rpc('some_mutating_rpc', {})

    # An allowlisted read RPC passes straight through to the real client.
    resp = client.rpc('tests_containing_sense', {'p_sense_id': 1}).execute()
    assert resp.data == []
    assert real.rpc_calls == [('tests_containing_sense', {'p_sense_id': 1})]


def test_llm_calls_pass_through_live_and_are_observed():
    real = FakeRealClient()
    sink, lock = [], threading.Lock()
    client = harness.InterceptingClient(real, sink, lock)

    client.table('llm_calls').insert({
        'cost_usd': 0.05, 'sense_id': 42, 'generation_batch_id': 'batch-1',
    }).execute()

    # llm_calls IS real -- it's the measurement, not content.
    assert real.recorder['llm_calls'] == [
        ('insert', {'cost_usd': 0.05, 'sense_id': 42, 'generation_batch_id': 'batch-1'})
    ]
    assert sink[0]['table'] == 'llm_calls' and sink[0]['cost_usd'] == 0.05


def test_process_one_sense_never_lets_a_write_through_for_an_unknown_table():
    """A pipeline stand-in that tries to write somewhere this harness has
    not vetted must blow up the sense rather than silently succeeding."""

    class BadPipeline(StubPipeline):
        def _generate_for_sense_impl(self, sense_id, language_id, force, batch_id):
            self.db.table('some_unvetted_table').insert({'x': 1}).execute()
            return {'status': 'success', 'errors': [], 'warnings': [], 'stage_seconds': {}}

    real = FakeRealClient()
    sink, lock = [], threading.Lock()
    db = harness.InterceptingClient(real, sink, lock)
    pipeline = BadPipeline(db)
    renderer = StubRenderer(db)

    capture = harness.process_one_sense(pipeline, renderer, 7, 1, 'b1', sink, lock)

    assert capture['status'] == 'error'
    assert capture['exceptions'], "the guard's exception must be captured, not swallowed"
    assert 'UnexpectedWriteError' in capture['exceptions'][0]['error']
    assert 'some_unvetted_table' not in real.recorder


# ---------------------------------------------------------------------------
# (b) Captured JSON has the expected shape
# ---------------------------------------------------------------------------

def test_process_one_sense_capture_shape(tmp_path):
    real = FakeRealClient()
    sink, lock = [], threading.Lock()
    db = harness.InterceptingClient(real, sink, lock)

    pipeline = StubPipeline(db, canned_result={
        'status': 'success', 'errors': [], 'warnings': ['a warning'],
        'stage_seconds': {'p1_generate': 1.2, 'fan_out': 3.4},
    })
    rows = [{
        'id': 'row-1', 'exercise_type': 'phonetic_recognition', 'ladder_level': 1,
        'tags': {'ladder_level': 1, 'l1_distractor_judge': {'rejected': 1, 'kept': 3}},
    }]
    renderer = StubRenderer(db, rows=rows, skips=[Skip('form_production', 'no generated asset')])

    capture = harness.process_one_sense(pipeline, renderer, 99, 3, 'batch-1', sink, lock)

    assert capture['sense_id'] == 99
    assert capture['language_id'] == 3
    assert capture['status'] == 'success'
    assert capture['stage_seconds'] == {'p1_generate': 1.2, 'fan_out': 3.4}

    assert len(capture['assets']) == 1
    asset = capture['assets'][0]
    assert asset['asset_type'] == 'prompt1_core'
    assert asset['is_valid'] is True
    assert asset['model_used'] == 'stub-model'

    assert capture['exercise_rows'] == rows
    assert capture['judges'] == {'l1_distractor': {'ran': 1, 'rejected': 1, 'kept': 3}}
    assert capture['deterministic_skips'] == [
        {'type_code': 'form_production', 'reason': 'no generated asset'}
    ]
    assert isinstance(capture['wall_clock_s'], float) and capture['wall_clock_s'] >= 0
    assert capture['exceptions'] == []

    # Must be JSON-serializable end to end, per the harness's own writer.
    out_dir = str(tmp_path)
    harness._write_sense_json(out_dir, capture)
    with open(os.path.join(out_dir, '99.json'), encoding='utf-8') as fh:
        reloaded = json.load(fh)
    assert reloaded['sense_id'] == 99
    assert reloaded['judges']['l1_distractor']['kept'] == 3


def test_skipped_sense_does_not_call_renderer():
    real = FakeRealClient()
    sink, lock = [], threading.Lock()
    db = harness.InterceptingClient(real, sink, lock)

    pipeline = StubPipeline(db, canned_result={
        'status': 'skipped', 'errors': [], 'warnings': [], 'stage_seconds': {},
    })

    calls = []

    class TrackingRenderer(StubRenderer):
        def build_rows(self, sense_id, language_id):
            calls.append(sense_id)
            return super().build_rows(sense_id, language_id)

    renderer = TrackingRenderer(db)
    capture = harness.process_one_sense(pipeline, renderer, 5, 1, 'b1', sink, lock)

    assert capture['status'] == 'skipped'
    assert calls == [], "build_rows must not run for a skipped/failed sense"
    assert capture['exercise_rows'] == []


# ---------------------------------------------------------------------------
# (c) max-cost stop works
# ---------------------------------------------------------------------------

def test_max_cost_usd_stops_the_run(tmp_path):
    sink, lock = [], threading.Lock()

    def pipeline_factory():
        db = harness.InterceptingClient(FakeRealClient(), sink, lock)
        return StubPipeline(db, llm_cost=1.0)

    def renderer_factory():
        db = harness.InterceptingClient(FakeRealClient(), sink, lock)
        return StubRenderer(db)

    summary = harness.run_eval(
        [101, 102, 103, 104, 105], language_id=1,
        pipeline_factory=pipeline_factory, renderer_factory=renderer_factory,
        batch_id='cost-cap-batch', out_dir=str(tmp_path),
        max_cost_usd=2.5, concurrency=1,
        capture_sink=sink, lock=lock, real_client=None,
    )

    # $1 per sense, cap $2.5 -> stops once cumulative cost hits $3 (sense 3).
    assert summary['attempted_senses'] == 3
    assert summary['requested_senses'] == 5
    assert summary['stopped_due_to_cost_cap'] is True
    assert summary['cost_usd_total_observed'] == pytest.approx(3.0)

    with open(os.path.join(str(tmp_path), 'summary.json'), encoding='utf-8') as fh:
        on_disk = json.load(fh)
    assert on_disk['attempted_senses'] == 3
    assert 'cost_query_sql' in on_disk and 'cost-cap-batch' in on_disk['cost_query_sql']


def test_no_cost_cap_runs_every_sense(tmp_path):
    sink, lock = [], threading.Lock()

    def pipeline_factory():
        db = harness.InterceptingClient(FakeRealClient(), sink, lock)
        return StubPipeline(db, llm_cost=0.5)

    def renderer_factory():
        db = harness.InterceptingClient(FakeRealClient(), sink, lock)
        return StubRenderer(db)

    summary = harness.run_eval(
        [1, 2, 3], language_id=2,
        pipeline_factory=pipeline_factory, renderer_factory=renderer_factory,
        batch_id='no-cap-batch', out_dir=str(tmp_path),
        max_cost_usd=None, concurrency=1,
        capture_sink=sink, lock=lock, real_client=None,
    )

    assert summary['attempted_senses'] == 3
    assert summary['stopped_due_to_cost_cap'] is False
    assert summary['assets_per_sense'] == {1: 1, 2: 1, 3: 1}


# ---------------------------------------------------------------------------
# (d) The cost cap trips from the REAL services.llm_service call path
#
# Fixes the bug this whole test class exists to close: `_log_llm_call`
# (services/llm_service.py) always writes `llm_calls` through
# `get_supabase_admin()` directly -- never through whatever `db` a caller
# constructs -- so the OLD ledger (built only from writes captured through
# InterceptingClient) stayed at $0 even while `StubPipeline`-style stand-ins
# were the only thing ever writing through the injected db in the real
# pipeline. These tests drive the REAL `call_llm` (OpenAI client + Supabase
# admin faked out, no network, no real spend) and prove the harness now
# observes that cost via `services.llm_service.subscribe_llm_cost_hook`.
# ---------------------------------------------------------------------------

class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakePromptTokensDetails:
    def __init__(self, cached_tokens=None):
        self.cached_tokens = cached_tokens
        self.model_extra = {}


class _FakeCompletionTokensDetails:
    def __init__(self, reasoning_tokens=None):
        self.reasoning_tokens = reasoning_tokens


class _FakeUsage:
    def __init__(self, cost):
        self.cost = cost
        self.model_extra = {}
        self.prompt_tokens = 100
        self.completion_tokens = 50
        self.prompt_tokens_details = _FakePromptTokensDetails(0)
        self.completion_tokens_details = _FakeCompletionTokensDetails(None)


class _FakeLLMResponse:
    def __init__(self, cost):
        self.choices = [_FakeChoice('{"ok": true}')]
        self.usage = _FakeUsage(cost)
        self.model = 'stub/real-cost-model'


class _FakeCompletions:
    def __init__(self, cost):
        self._cost = cost

    def create(self, **_kw):
        return _FakeLLMResponse(self._cost)


class _FakeChat:
    def __init__(self, cost):
        self.completions = _FakeCompletions(cost)


class _FakeOpenAIClient:
    """Stands in for `get_client()`'s return value -- an OpenAI-compatible
    client whose base_url makes `_is_openrouter()` true, so `_make_one_call`
    exercises the same cost-extraction path a real OpenRouter response would."""

    def __init__(self, cost_per_call):
        self.base_url = 'https://openrouter.ai/api/v1'
        self.chat = _FakeChat(cost_per_call)


class RealCallLLMPipeline:
    """Unlike StubPipeline (which writes an llm_calls row directly through
    the injected `db`), this calls the REAL `services.llm_service.call_llm`
    for its one LLM call -- the code path real VocabAssetPipeline generators
    actually use, and the one the old capture_sink-based ledger could never
    see because `_log_llm_call` bypasses the injected client entirely."""

    def __init__(self, db, cost_per_call=1.0):
        self.db = db
        self._cost = cost_per_call

    def _generate_for_sense_impl(self, sense_id, language_id, force, batch_id):
        from services.llm_service import call_llm
        call_llm(
            'a prompt', model='stub/real-cost-model', provider='openrouter',
            response_format='json_object', pipeline='vocab_ladder',
            task_name='vocab_prompt1_core',
        )
        self.db.table('word_assets').upsert({
            'sense_id': sense_id, 'language_id': language_id,
            'asset_type': 'prompt1_core', 'content': {'lemma': 'stub'},
            'model_used': 'stub-model', 'is_valid': True,
            'validation_errors': None, 'validation_warnings': None,
            'generation_batch_id': batch_id,
        }, on_conflict='sense_id,asset_type').execute()
        return {'status': 'success', 'errors': [], 'warnings': [], 'stage_seconds': {}}


def test_max_cost_usd_stops_the_run_via_real_llm_service_cost_hook(tmp_path, monkeypatch):
    import services.llm_service as llm_service

    fake_client = _FakeOpenAIClient(cost_per_call=1.0)
    monkeypatch.setattr(llm_service, 'get_client', lambda *a, **kw: fake_client)
    monkeypatch.setattr('services.supabase_factory.get_supabase_admin', lambda: None)
    monkeypatch.setattr('services.supabase_factory.get_supabase', lambda: None)

    sink, lock = [], threading.Lock()

    def pipeline_factory():
        db = harness.InterceptingClient(FakeRealClient(), sink, lock)
        return RealCallLLMPipeline(db, cost_per_call=1.0)

    def renderer_factory():
        db = harness.InterceptingClient(FakeRealClient(), sink, lock)
        return StubRenderer(db)

    summary = harness.run_eval(
        [201, 202, 203, 204, 205], language_id=2,
        pipeline_factory=pipeline_factory, renderer_factory=renderer_factory,
        batch_id='real-cost-hook-batch', out_dir=str(tmp_path),
        max_cost_usd=2.5, concurrency=1,
        capture_sink=sink, lock=lock, real_client=None,
    )

    # $1/sense via the REAL call_llm path, cap $2.5 -> stops once cumulative
    # cost hits $3 (sense 3) -- same shape as test_max_cost_usd_stops_the_run,
    # but now proving the harness sees cost it never wrote into capture_sink.
    assert summary['attempted_senses'] == 3
    assert summary['stopped_due_to_cost_cap'] is True
    assert summary['cost_usd_total_observed'] == pytest.approx(3.0)

    with open(os.path.join(str(tmp_path), '201.json'), encoding='utf-8') as fh:
        sense_201 = json.load(fh)
    assert len(sense_201['llm_calls']) == 1
    call_row = sense_201['llm_calls'][0]
    assert call_row['cost_usd'] == pytest.approx(1.0)
    assert call_row['task_name'] == 'vocab_prompt1_core'
    assert call_row['sense_id'] == 201
    assert call_row['call_role'] == 'primary'

    # No leaked subscriber -- llm_service's subscriber list is process-global.
    assert llm_service._cost_hook_subscribers == []


def test_render_stage_skipped_once_cost_cap_hit_mid_sense(tmp_path, monkeypatch):
    """'Abort in-flight work between pipeline stages': a sense whose
    generation call alone already blows the budget must not also pay for
    rendering (render-time judges are LLM calls too)."""
    import services.llm_service as llm_service

    fake_client = _FakeOpenAIClient(cost_per_call=5.0)
    monkeypatch.setattr(llm_service, 'get_client', lambda *a, **kw: fake_client)
    monkeypatch.setattr('services.supabase_factory.get_supabase_admin', lambda: None)
    monkeypatch.setattr('services.supabase_factory.get_supabase', lambda: None)

    sink, lock = [], threading.Lock()
    render_calls = []

    class TrackingRenderer(StubRenderer):
        def build_rows(self, sense_id, language_id):
            render_calls.append(sense_id)
            return super().build_rows(sense_id, language_id)

    db = harness.InterceptingClient(FakeRealClient(), sink, lock)
    pipeline = RealCallLLMPipeline(db, cost_per_call=5.0)
    renderer = TrackingRenderer(db)

    ledger = harness.CostHookLedger()
    ledger.start()
    try:
        capture = harness.process_one_sense(
            pipeline, renderer, 301, 2, 'batch-mid-cap', sink, lock,
            cost_ledger=ledger, max_cost_usd=1.0,
        )
    finally:
        ledger.stop()

    assert capture['status'] == 'success'
    assert render_calls == [], "rendering must be skipped once the cap is already hit"
    assert capture['render_skipped_cost_cap'] is True
    assert capture['exercise_rows'] == []
    assert any('cost cap' in w for w in capture['warnings'])


# ---------------------------------------------------------------------------
# (e) Shadow read-back for the render stage -- the real "en prompt1_core
# fails" root cause. It doesn't: prompt1_core generates and validates fine
# (see the module-level comment above ShadowReadClient in the harness for
# the full diagnosis). What actually produced 0 exercise_rows for a
# top_up_candidates sense (any language) is that build_rows() re-queries
# word_assets fresh, and this harness blocks that write -- so a sense with no
# PRE-EXISTING valid word_assets row can never be rendered by this harness,
# even when generation just built one. These tests prove the shadow overlay
# closes that gap using the REAL LadderExerciseRenderer._load_assets.
# ---------------------------------------------------------------------------

def test_shadow_read_surfaces_a_captured_upsert_the_live_db_never_saw():
    """The exact top_up_candidates scenario: the live DB has NO word_assets
    row for this sense (fresh candidate), but this run's own (harness-
    blocked) generation just produced one. The renderer must see it."""
    real = FakeRealClient()
    real.recorder['word_assets__select_data'] = []  # nothing pre-existing
    sink, lock = [], threading.Lock()

    gen_db = harness.InterceptingClient(real, sink, lock)
    gen_db.table('word_assets').upsert({
        'sense_id': 14010, 'language_id': 2, 'asset_type': 'prompt1_core',
        'content': {'pos': 'adjective', 'definition': 'not the same'},
        'is_valid': True,
    }, on_conflict='sense_id,asset_type').execute()

    render_db = harness.ShadowReadClient(
        harness.InterceptingClient(real, sink, lock), sink, lock,
    )
    renderer = LadderExerciseRenderer(db=render_db)

    assets = renderer._load_assets(14010)
    assert assets.get('prompt1_core') == {
        'pos': 'adjective', 'definition': 'not the same',
    }


def test_shadow_read_lets_build_rows_stop_normally_when_p1_truly_absent():
    """A sense where generation itself never produced a valid prompt1_core
    (e.g. it genuinely failed) must still render nothing -- the shadow
    overlay must not fabricate content that was never captured."""
    real = FakeRealClient()
    real.recorder['word_assets__select_data'] = []
    sink, lock = [], threading.Lock()

    render_db = harness.ShadowReadClient(
        harness.InterceptingClient(real, sink, lock), sink, lock,
    )
    renderer = LadderExerciseRenderer(db=render_db)

    rows = renderer.build_rows(99999, 2)
    assert rows == []


def test_shadow_read_prefers_this_runs_write_over_a_stale_live_row():
    """A live row can exist (e.g. --force re-running a sense) -- this run's
    own fresh write must win, since it postdates whatever the DB had."""
    real = FakeRealClient()
    real.recorder['word_assets__select_data'] = [{
        'sense_id': 555, 'asset_type': 'prompt1_core',
        'content': {'definition': 'STALE'}, 'is_valid': True,
    }]
    sink, lock = [], threading.Lock()

    gen_db = harness.InterceptingClient(real, sink, lock)
    gen_db.table('word_assets').upsert({
        'sense_id': 555, 'language_id': 2, 'asset_type': 'prompt1_core',
        'content': {'definition': 'FRESH'}, 'is_valid': True,
    }, on_conflict='sense_id,asset_type').execute()

    render_db = harness.ShadowReadClient(
        harness.InterceptingClient(real, sink, lock), sink, lock,
    )
    renderer = LadderExerciseRenderer(db=render_db)

    assets = renderer._load_assets(555)
    assert assets['prompt1_core']['definition'] == 'FRESH'


def test_shadow_read_client_passes_non_word_assets_tables_through_unchanged():
    real = FakeRealClient()
    sink, lock = [], threading.Lock()
    render_db = harness.ShadowReadClient(
        harness.InterceptingClient(real, sink, lock), sink, lock,
    )

    resp = (
        render_db.table('word_assets')  # sanity: still overlays this table
        .select('asset_type, content').eq('sense_id', 1).eq('is_valid', True)
        .execute()
    )
    assert resp.data == []

    # A CAPTURED_WRITE_TABLES write on a different table is still blocked and
    # captured exactly as it would be without the shadow wrapper.
    resp2 = render_db.table('dim_vocabulary').update({'x': 1}).eq('id', 1).execute()
    assert resp2.data == []
    assert any(r['table'] == 'dim_vocabulary' for r in sink)


# ---------------------------------------------------------------------------
# --model-override (TASK-812/813 harness support)
# ---------------------------------------------------------------------------

def test_parse_model_overrides_without_language_scope():
    overrides = harness.parse_model_overrides([
        'vocab_prompt2_exercises=qwen/qwen3.7-plus',
    ])
    assert overrides == {('vocab_prompt2_exercises', None): 'qwen/qwen3.7-plus'}


def test_parse_model_overrides_with_language_scope():
    overrides = harness.parse_model_overrides([
        'vocab_prompt2_exercises:en=qwen/qwen3.7-plus',
        'vocab_prompt3_transforms:en=qwen/qwen3.7-plus',
    ])
    assert overrides == {
        ('vocab_prompt2_exercises', 2): 'qwen/qwen3.7-plus',
        ('vocab_prompt3_transforms', 2): 'qwen/qwen3.7-plus',
    }


def test_parse_model_overrides_rejects_bad_shape():
    with pytest.raises(SystemExit):
        harness.parse_model_overrides(['not-a-valid-override'])


def test_parse_model_overrides_rejects_unknown_language():
    with pytest.raises(SystemExit):
        harness.parse_model_overrides(['vocab_prompt2_exercises:fr=some/model'])


def test_apply_model_overrides_swaps_the_model_without_touching_the_template(monkeypatch):
    import services.prompt_service as prompt_service_module

    original = prompt_service_module.get_template_config
    calls = []

    def fake_original(db, task_name, language_id):
        calls.append((task_name, language_id))
        return {'template': 'T', 'model': 'anthropic/claude-sonnet-5',
                'provider': 'openrouter', 'version': 3}

    monkeypatch.setattr(prompt_service_module, 'get_template_config', fake_original)
    try:
        overrides = harness.parse_model_overrides([
            'vocab_prompt2_exercises:en=qwen/qwen3.7-plus',
        ])
        applied = harness.apply_model_overrides(overrides)
        assert applied == [
            {'task_name': 'vocab_prompt2_exercises', 'language': 'en',
             'model': 'qwen/qwen3.7-plus'},
        ]

        # The matching (task_name, language) pair is swapped...
        cfg = prompt_service_module.get_template_config(None, 'vocab_prompt2_exercises', 2)
        assert cfg['model'] == 'qwen/qwen3.7-plus'
        assert cfg['template'] == 'T'  # template text untouched
        assert cfg['provider'] == 'openrouter'

        # ...a different language for the same task_name is not.
        cfg_zh = prompt_service_module.get_template_config(None, 'vocab_prompt2_exercises', 1)
        assert cfg_zh['model'] == 'anthropic/claude-sonnet-5'

        # ...and an unrelated task_name is untouched.
        cfg_other = prompt_service_module.get_template_config(None, 'vocab_prompt1_core', 2)
        assert cfg_other['model'] == 'anthropic/claude-sonnet-5'
    finally:
        prompt_service_module.get_template_config = original


def test_apply_model_overrides_language_less_entry_applies_to_every_language(monkeypatch):
    import services.prompt_service as prompt_service_module

    original = prompt_service_module.get_template_config
    monkeypatch.setattr(
        prompt_service_module, 'get_template_config',
        lambda db, task_name, language_id: {
            'template': 'T', 'model': 'old/model',
            'provider': 'openrouter', 'version': 1,
        },
    )
    try:
        overrides = harness.parse_model_overrides(['vocab_prompt1_core=new/model'])
        harness.apply_model_overrides(overrides)

        for language_id in (1, 2, 3):
            cfg = prompt_service_module.get_template_config(
                None, 'vocab_prompt1_core', language_id)
            assert cfg['model'] == 'new/model'
    finally:
        prompt_service_module.get_template_config = original


def test_apply_model_overrides_no_overrides_is_a_no_op():
    assert harness.apply_model_overrides({}) == []


# ---------------------------------------------------------------------------
# --prompt-override-file (ADR-028 Phase 2 harness support)
# ---------------------------------------------------------------------------

_SQL_FIXTURE = """
-- a comment with an apostrophe (don't strip the row below because of it)
BEGIN;

INSERT INTO prompt_templates
    (task_name, template_text, version, is_active, description, language_id, model, provider)
VALUES (
    'vocab_bundle_generation',
    E'Line one with a brace pair {{"1": 1}} and a ' -- trailing comment on a literal line
    E'target''s escaped quote.\\nSecond physical line.',
    2, false, 'a draft row, not applied', 2, 'qwen/qwen3.7-plus', 'openrouter'
);

COMMIT;
"""


def test_parse_prompt_templates_sql_extracts_row_and_decodes_literals():
    rows = harness.parse_prompt_templates_sql(_SQL_FIXTURE)
    assert len(rows) == 1
    row = rows[0]
    assert row['task_name'] == 'vocab_bundle_generation'
    assert row['language_id'] == 2
    assert row['version'] == 2
    assert row['is_active'] is False
    assert row['model'] == 'qwen/qwen3.7-plus'
    assert row['provider'] == 'openrouter'
    # Adjacent E'...' literals concatenate; '' decodes to a literal quote;
    # \n (inside an E-string) decodes to a real newline; doubled {{ survives
    # untouched (it is JSON-brace escaping for a later str.format() call, not
    # anything this SQL-literal decoder should touch).
    assert row['template_text'] == (
        'Line one with a brace pair {{"1": 1}} and a '
        "target's escaped quote.\nSecond physical line."
    )


def test_parse_prompt_override_file_from_sql(tmp_path):
    sql_path = tmp_path / 'draft.sql'
    sql_path.write_text(_SQL_FIXTURE, encoding='utf-8')

    overrides = harness.parse_prompt_override_file(str(sql_path))
    assert list(overrides.keys()) == [('vocab_bundle_generation', 2)]
    entry = overrides[('vocab_bundle_generation', 2)]
    assert entry['model'] == 'qwen/qwen3.7-plus'
    assert entry['provider'] == 'openrouter'
    assert entry['version'] == 2
    assert "target's escaped quote" in entry['template']


def test_parse_prompt_override_file_from_json(tmp_path):
    json_path = tmp_path / 'overrides.json'
    json_path.write_text(json.dumps([
        {
            'task_name': 'ladder_bundle_judge',
            'language': 'en',
            'template': 'JSON-sourced template {target}',
            'model': 'google/gemini-3.5-flash-lite',
        },
        {
            'task_name': 'vocab_bundle_generation',
            'language_id': 1,
            'template_text': 'zh template',
            'model': 'qwen/qwen3.7-plus',
            'provider': 'openrouter',
            'version': 5,
        },
    ]), encoding='utf-8')

    overrides = harness.parse_prompt_override_file(str(json_path))
    assert overrides[('ladder_bundle_judge', 2)]['template'] == 'JSON-sourced template {target}'
    assert overrides[('ladder_bundle_judge', 2)]['provider'] == 'openrouter'  # default applied
    assert overrides[('ladder_bundle_judge', 2)]['version'] == 1  # default applied
    assert overrides[('vocab_bundle_generation', 1)] == {
        'template': 'zh template', 'model': 'qwen/qwen3.7-plus',
        'provider': 'openrouter', 'version': 5,
    }


def test_parse_prompt_override_file_rejects_incomplete_row(tmp_path):
    json_path = tmp_path / 'bad.json'
    json_path.write_text(json.dumps([{'task_name': 'x', 'language': 'en'}]), encoding='utf-8')
    with pytest.raises(SystemExit):
        harness.parse_prompt_override_file(str(json_path))


def test_apply_prompt_overrides_replaces_the_whole_config_for_a_matched_key(monkeypatch):
    import services.prompt_service as prompt_service_module

    original = prompt_service_module.get_template_config
    calls = []

    def fake_original(db, task_name, language_id):
        calls.append((task_name, language_id))
        return {'template': 'DB template', 'model': 'db/model',
                'provider': 'openrouter', 'version': 9}

    monkeypatch.setattr(prompt_service_module, 'get_template_config', fake_original)
    try:
        overrides = {
            ('vocab_bundle_generation', 2): {
                'template': 'override template', 'model': 'override/model',
                'provider': 'openrouter', 'version': 1,
            },
        }
        applied = harness.apply_prompt_overrides(overrides)
        assert applied == [{
            'task_name': 'vocab_bundle_generation', 'language': 'en',
            'language_id': 2, 'version': 1, 'model': 'override/model',
            'provider': 'openrouter',
        }]

        # Matched key: fully replaced, the real (stub) DB lookup is never called.
        cfg = prompt_service_module.get_template_config(None, 'vocab_bundle_generation', 2)
        assert cfg == {
            'template': 'override template', 'model': 'override/model',
            'provider': 'openrouter', 'version': 1,
        }
        assert calls == []

        # Unmatched key: falls through to the real (stub) lookup.
        cfg_other = prompt_service_module.get_template_config(None, 'vocab_prompt1_core', 2)
        assert cfg_other['model'] == 'db/model'
        assert calls == [('vocab_prompt1_core', 2)]
    finally:
        prompt_service_module.get_template_config = original


def test_apply_prompt_overrides_wins_over_a_same_key_model_override(monkeypatch):
    """apply_model_overrides then apply_prompt_overrides (main()'s order) --
    the prompt override, applied second, must win for a key both target."""
    import services.prompt_service as prompt_service_module

    original = prompt_service_module.get_template_config
    monkeypatch.setattr(
        prompt_service_module, 'get_template_config',
        lambda db, task_name, language_id: {
            'template': 'DB template', 'model': 'db/model',
            'provider': 'openrouter', 'version': 1,
        },
    )
    try:
        model_overrides = harness.parse_model_overrides([
            'vocab_bundle_generation:en=model-only/override',
        ])
        harness.apply_model_overrides(model_overrides)
        harness.apply_prompt_overrides({
            ('vocab_bundle_generation', 2): {
                'template': 'prompt override template', 'model': 'prompt/override',
                'provider': 'openrouter', 'version': 3,
            },
        })

        cfg = prompt_service_module.get_template_config(None, 'vocab_bundle_generation', 2)
        assert cfg['model'] == 'prompt/override'
        assert cfg['template'] == 'prompt override template'
    finally:
        prompt_service_module.get_template_config = original


def test_apply_prompt_overrides_no_overrides_is_a_no_op():
    assert harness.apply_prompt_overrides({}) == []


def test_prompt_override_file_matches_the_real_draft_migration():
    """Sanity check against the actual ADR-028 Phase 2 draft migration, so a
    future edit to that file that breaks this parser's assumptions is caught
    here rather than only at harness runtime."""
    sql_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'migrations', 'exercise_gen_bundle_prompts_draft.sql',
    )
    overrides = harness.parse_prompt_override_file(sql_path)
    assert set(overrides.keys()) == {
        ('vocab_bundle_generation', 1), ('vocab_bundle_generation', 2),
        ('vocab_bundle_generation', 3),
        ('ladder_bundle_judge', 1), ('ladder_bundle_judge', 2),
        ('ladder_bundle_judge', 3),
    }
    en_judge = overrides[('ladder_bundle_judge', 2)]
    assert en_judge['model'] == 'google/gemini-3.5-flash-lite'
    assert '{word_family_items_numbered}' in en_judge['template']


# ---------------------------------------------------------------------------
# --senses-from (TASK-812/813 harness support)
# ---------------------------------------------------------------------------

def test_load_senses_from_run_dir_reads_sense_id_filenames(tmp_path):
    for sense_id in (14010, 13898, 14090):
        (tmp_path / f'{sense_id}.json').write_text('{}', encoding='utf-8')
    (tmp_path / 'summary.json').write_text('{}', encoding='utf-8')
    (tmp_path / 'pairwise_key.json').write_text('{}', encoding='utf-8')

    sense_ids = harness.load_senses_from_run_dir(str(tmp_path))

    assert sense_ids == [13898, 14010, 14090]


def test_load_senses_from_run_dir_missing_directory_raises(tmp_path):
    with pytest.raises(SystemExit):
        harness.load_senses_from_run_dir(str(tmp_path / 'does_not_exist'))


def test_load_senses_from_run_dir_empty_directory_raises(tmp_path):
    with pytest.raises(SystemExit):
        harness.load_senses_from_run_dir(str(tmp_path))
