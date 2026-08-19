"""A test saved without its vocabulary must never read as a clean pass.

Why this file exists: `_generate_vocabulary` is deliberately non-fatal — prose,
questions and audio are already written and paid for by the time it runs, so a
missing enrichment layer is not worth discarding a finished test over. But the
non-fatal path wrote nothing at all when it produced nothing, so a test with
NULL vocab was byte-identical to one whose vocabulary step had never been
reached, and the run summary reported it as generated. A whole batch of
NULL-vocab tests passed unnoticed that way.

Two halves are pinned here:

1. `SenseGenerator._call_llm` reaches the fallback model on ANY persistent
   primary failure, not only on malformed JSON. A delisted primary slug used to
   return None for every word in a run while a healthy fallback sat unused.
2. Every exit path of `_generate_vocabulary` records an outcome in
   `tests.vocab_sense_stats` and counts the shortfall against the run.
"""

import json
from unittest.mock import patch

import services.vocabulary.sense_generator as sg
from services.test_generation.orchestrator import TestGenerationOrchestrator


# ---------------------------------------------------------------------------
# Doubles
# ---------------------------------------------------------------------------

class _DeadDB:
    """Any table access raises — exercises the register fallback constant."""

    def table(self, _name):
        raise RuntimeError('no db in unit tests')


class _UpdateChain:
    def __init__(self, sink, table_name):
        self._sink = sink
        self._table = table_name
        self._payload = None
        self._row_id = None

    def update(self, payload):
        self._payload = payload
        return self

    def eq(self, _col, value):
        self._row_id = value
        return self

    def execute(self):
        self._sink.append((self._table, self._row_id, self._payload))
        return None


class _RecordingDB:
    """Captures every `.table(x).update(...).eq(...).execute()` write."""

    def __init__(self):
        self.writes = []

    def table(self, name):
        return _UpdateChain(self.writes, name)


class _DBClient:
    def __init__(self, client):
        self.client = client


def _make_generator(**kwargs):
    return sg.SenseGenerator(
        openai_client=None, db=_DeadDB(), db_client=None,
        language_code='zh', language_id=1, **kwargs,
    )


def _make_orchestrator(db):
    """An orchestrator without __init__ — it would need live Supabase."""
    orch = object.__new__(TestGenerationOrchestrator)
    orch.db = _DBClient(db)
    orch.vocab_shortfalls = 0
    return orch


# ---------------------------------------------------------------------------
# 1. Fallback routing
# ---------------------------------------------------------------------------

def test_fallback_fires_on_a_persistent_api_error_not_only_bad_json():
    """The regression that mattered.

    A delisted / 4xx-ing primary slug raises an ordinary Exception, not a JSON
    error. That used to return None immediately and never touch the fallback,
    so one dead slug wiped vocabulary for an entire run.
    """
    calls = []

    def fake_llm_call(_prompt, **kw):
        calls.append(kw['model'])
        if kw['model'] == 'primary-model':
            raise ValueError('404 No endpoints found for primary-model')
        return {'1': 'simple', '2': 'standard'}

    gen = _make_generator(model='primary-model', fallback_model='backup-model')
    with patch.object(sg, 'llm_call', fake_llm_call):
        result = gen._call_llm('p', task_name='vocab_definition_generation')

    assert calls == ['primary-model', 'backup-model']
    assert result == {'1': 'simple', '2': 'standard'}
    assert gen.stats['fallback_used'] == 1
    assert gen.stats['both_models_failed'] == 0


def test_fallback_still_fires_on_empty_content():
    """`call_llm` raises RuntimeError('LLM returned empty content')."""
    calls = []

    def fake_llm_call(_prompt, **kw):
        calls.append(kw['model'])
        if kw['model'] == 'primary-model':
            raise RuntimeError('LLM returned empty content')
        return {'1': 'a', '2': 'b'}

    gen = _make_generator(model='primary-model', fallback_model='backup-model')
    with patch.object(sg, 'llm_call', fake_llm_call):
        assert gen._call_llm('p', task_name='t') is not None
    assert calls == ['primary-model', 'backup-model']


def test_both_models_failing_is_counted_not_just_logged():
    """The counter is what tells a run report 'provider outage', not attrition."""

    def fake_llm_call(_prompt, **kw):
        raise RuntimeError('LLM returned empty content')

    gen = _make_generator(model='primary-model', fallback_model='backup-model')
    with patch.object(sg, 'llm_call', fake_llm_call):
        assert gen._call_llm('p', task_name='t') is None

    assert gen.stats['both_models_failed'] == 1
    assert gen.stats['fallback_used'] == 0


def test_malformed_json_from_both_models_returns_none():
    def fake_llm_call(_prompt, **kw):
        raise json.JSONDecodeError('bad', '{', 0)

    gen = _make_generator()
    with patch.object(sg, 'llm_call', fake_llm_call):
        assert gen._call_llm('p', task_name='t') is None
    assert gen.stats['both_models_failed'] == 1


# ---------------------------------------------------------------------------
# 2. Outcome recording
# ---------------------------------------------------------------------------

def _stats_written(db):
    rows = [w for w in db.writes if w[0] == 'tests']
    assert rows, 'no write to tests'
    return rows[-1][2]['vocab_sense_stats']


def test_fully_accounted_test_is_marked_complete_and_costs_no_shortfall():
    db = _RecordingDB()
    orch = _make_orchestrator(db)
    orch._record_vocab_outcome('test-1', {
        'words_attempted': 20, 'unique_senses': 18, 'senses_failed': 0,
        'senses_skipped': 2, 'both_models_failed': 0,
        'phrases': 3, 'single_words': 17,
    })

    stats = _stats_written(db)
    assert stats['complete'] is True
    assert 'shortfall_reason' not in stats
    assert orch.vocab_shortfalls == 0


def test_missing_senses_mark_the_test_incomplete():
    db = _RecordingDB()
    orch = _make_orchestrator(db)
    orch._record_vocab_outcome('test-2', {
        'words_attempted': 20, 'unique_senses': 15, 'senses_failed': 5,
        'senses_skipped': 0, 'both_models_failed': 5,
        'phrases': 2, 'single_words': 18,
    })

    stats = _stats_written(db)
    assert stats['complete'] is False
    assert stats['shortfall_reason'] == 'senses_missing'
    assert stats['senses_failed'] == 5
    assert orch.vocab_shortfalls == 1


def test_skipped_words_are_accounted_not_treated_as_failures():
    """Proper nouns and numerals legitimately produce no sense.

    Without this, a healthy test full of names would be flagged, and a report
    that cries wolf gets ignored — which is how the original silence started.
    """
    db = _RecordingDB()
    orch = _make_orchestrator(db)
    orch._record_vocab_outcome('test-3', {
        'words_attempted': 10, 'unique_senses': 4, 'senses_failed': 0,
        'senses_skipped': 6, 'both_models_failed': 0,
        'phrases': 0, 'single_words': 10,
    })

    assert _stats_written(db)['complete'] is True
    assert orch.vocab_shortfalls == 0


def test_an_explicit_reason_overrides_a_balanced_count():
    """The exception path can look balanced (0 attempted, 0 linked) yet be a
    failure. A supplied reason always wins."""
    db = _RecordingDB()
    orch = _make_orchestrator(db)
    orch._record_vocab_outcome('test-4', {
        'words_attempted': 0, 'unique_senses': 0, 'senses_failed': 0,
        'senses_skipped': 0, 'both_models_failed': 0,
        'phrases': 0, 'single_words': 0,
    }, reason='exception: APIError: boom')

    stats = _stats_written(db)
    assert stats['complete'] is False
    assert stats['shortfall_reason'].startswith('exception: APIError')
    assert orch.vocab_shortfalls == 1


def test_a_failed_stats_write_does_not_raise_into_the_pipeline():
    class _ExplodingDB:
        def table(self, _name):
            raise RuntimeError('supabase down')

    orch = _make_orchestrator(_ExplodingDB())
    orch._record_vocab_outcome('test-5', {
        'words_attempted': 5, 'unique_senses': 0, 'senses_failed': 5,
        'senses_skipped': 0, 'both_models_failed': 0,
        'phrases': 0, 'single_words': 5,
    })
    # Still counted, even though it could not be persisted.
    assert orch.vocab_shortfalls == 1


# ---------------------------------------------------------------------------
# 3. End to end through _generate_vocabulary
# ---------------------------------------------------------------------------

class _LangConfig:
    id = 1
    language_code = 'zh'


class _Pipeline:
    def __init__(self, items):
        self._items = items

    def extract_detailed(self, _transcript, _lang):
        return self._items


class _StubSenseGen:
    """Every word fails — the total-wipeout case."""

    def __init__(self, *a, **kw):
        self.stats = {
            'senses_created': 0, 'senses_reused': 0, 'senses_skipped': 0,
            'senses_failed': 2, 'rows_written': 0, 'fallback_used': 0,
            'both_models_failed': 2, 'embeddings_written': 0,
            'embeddings_failed': 0,
        }

    def generate_sense(self, **kw):
        return None


def test_a_total_vocab_wipeout_still_writes_a_row():
    """The defect in one assertion.

    Previously the `if sense_ids:` branch was the only writer, so producing
    nothing left `vocab_sense_stats` NULL — indistinguishable from a test whose
    vocabulary step never ran, and reported as a pass.
    """
    db = _RecordingDB()
    orch = _make_orchestrator(db)
    orch.vocab_pipeline = _Pipeline([
        {'lemma': '水', 'is_phrase': False},
        {'lemma': '喝水', 'is_phrase': True},
    ])
    orch.prose_writer = type('P', (), {'client': None})()
    orch._get_or_create_vocab_id = lambda *a, **kw: 1

    with patch('services.test_generation.orchestrator.SenseGenerator',
               _StubSenseGen):
        orch._generate_vocabulary(
            test_id='test-6', transcript='我喝水。', lang_config=_LangConfig(),
        )

    stats = _stats_written(db)
    assert stats['complete'] is False
    assert stats['shortfall_reason'] == 'no_senses_generated'
    assert stats['words_attempted'] == 2
    assert stats['unique_senses'] == 0
    assert stats['both_models_failed'] == 2
    assert orch.vocab_shortfalls == 1


def test_an_empty_extraction_is_recorded_rather_than_returning_quietly():
    db = _RecordingDB()
    orch = _make_orchestrator(db)
    orch.vocab_pipeline = _Pipeline([])

    orch._generate_vocabulary(
        test_id='test-7', transcript='...', lang_config=_LangConfig(),
    )

    stats = _stats_written(db)
    assert stats['complete'] is False
    assert stats['shortfall_reason'] == 'no_vocabulary_extracted'
    assert orch.vocab_shortfalls == 1
