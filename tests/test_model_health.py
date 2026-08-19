"""TASK-510 — model-slug health probe + fail-closed batch judging.

Network-free and DB-free: the Supabase client and the provider model listing
are both stubbed. Two halves, mirroring the two halves of the task:

  1. ``services.model_health`` — does the probe correctly identify a delisted
     slug, name the prompt_templates rows using it, and refuse to cry wolf when
     the probe itself fails?
  2. ``judges.base.batch_mode`` — does a judge outage abort a generation batch
     while leaving the serve-path fail-open contract untouched?
"""

import logging

import pytest

from services import model_health
from services.exercise_generation.judges import base as jbase
from services.exercise_generation.judges import p1_sentences as p1mod
from services.exercise_generation.judges import collocation as collocmod


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

_ROWS = [
    {'task_name': 'ladder_p1_core',           'language_id': 1, 'version': 3,
     'model': 'test/live-model', 'provider': 'openrouter'},
    {'task_name': 'ladder_collocation_judge', 'language_id': 1, 'version': 2,
     'model': 'test/dead-model', 'provider': 'openrouter'},
    {'task_name': 'ladder_collocation_judge', 'language_id': 3, 'version': 2,
     'model': 'test/dead-model', 'provider': 'openrouter'},
    {'task_name': 'local_thing',              'language_id': 2, 'version': 1,
     'model': 'llama3:8b',       'provider': 'ollama'},
]


class _FakeResp:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def execute(self):
        return _FakeResp(self._rows)


class _FakeDB:
    def __init__(self, rows=_ROWS):
        self._rows = rows

    def table(self, _name):
        return _FakeTable(self._rows)


def _patch_listing(monkeypatch, ids):
    monkeypatch.setattr(model_health, '_live_model_ids', lambda provider: set(ids))


@pytest.fixture(autouse=True)
def _clear_caches():
    model_health.reset_cache()
    p1mod._cfg_cache.clear()
    collocmod._cfg_cache.clear()
    yield
    model_health.reset_cache()
    p1mod._cfg_cache.clear()
    collocmod._cfg_cache.clear()


# ---------------------------------------------------------------------------
# Probe
# ---------------------------------------------------------------------------

def test_dead_slug_is_detected_and_names_its_rows(monkeypatch):
    """A delisted slug is reported with every prompt_templates row using it."""
    _patch_listing(monkeypatch, ['test/live-model'])

    report = model_health.check_model_slugs(_FakeDB(), force=True)

    assert report['ok'] is False
    assert [e['model'] for e in report['dead']] == ['test/dead-model']
    dead = report['dead'][0]
    # Both language rows are named, so the operator knows the blast radius.
    assert {r['language_id'] for r in dead['rows']} == {1, 3}
    assert all(r['task_name'] == 'ladder_collocation_judge' for r in dead['rows'])


def test_all_live_slugs_report_ok(monkeypatch):
    _patch_listing(monkeypatch, ['test/live-model', 'test/dead-model'])

    report = model_health.check_model_slugs(_FakeDB(), force=True)

    assert report['ok'] is True
    assert report['dead'] == []
    assert report['probed'] == 2          # two distinct openrouter slugs


def test_ollama_rows_are_skipped_not_reported_dead(monkeypatch):
    """A local ollama slug missing from OpenRouter's listing is not rot."""
    _patch_listing(monkeypatch, ['test/live-model', 'test/dead-model'])

    report = model_health.check_model_slugs(_FakeDB(), force=True)

    assert [e['model'] for e in report['skipped']] == ['llama3:8b']
    assert 'llama3:8b' not in [e['model'] for e in report['dead']]


def test_routing_suffix_matches_base_slug(monkeypatch):
    """``model:free`` / ``model@preset`` resolve against the bare listing id."""
    rows = [{'task_name': 't', 'language_id': 1, 'version': 1,
             'model': 'test/live-model:free', 'provider': 'openrouter'}]
    _patch_listing(monkeypatch, ['test/live-model'])

    report = model_health.check_model_slugs(_FakeDB(rows), force=True)

    assert report['dead'] == []
    assert report['ok'] is True


def test_probe_failure_does_not_claim_dead_slugs(monkeypatch):
    """A network failure must not manufacture a false 'everything is dead'."""
    def _boom(_provider):
        raise RuntimeError('connection refused')
    monkeypatch.setattr(model_health, '_live_model_ids', _boom)

    report = model_health.check_model_slugs(_FakeDB(), force=True)

    assert report['dead'] == []
    assert report['ok'] is True
    assert 'connection refused' in report['error']


def test_report_is_memoised_until_forced(monkeypatch):
    calls = []

    def _listing(_provider):
        calls.append(1)
        return {'test/live-model', 'test/dead-model'}
    monkeypatch.setattr(model_health, '_live_model_ids', _listing)

    model_health.check_model_slugs(_FakeDB(), force=True)
    model_health.check_model_slugs(_FakeDB())          # served from cache
    assert len(calls) == 1

    model_health.check_model_slugs(_FakeDB(), force=True)
    assert len(calls) == 2


def test_nightly_run_logs_error_naming_dead_rows(monkeypatch, caplog):
    _patch_listing(monkeypatch, ['test/live-model'])
    monkeypatch.setattr(model_health, '_try_lock', lambda db: True)
    monkeypatch.setattr(model_health, '_release_lock', lambda db: None)
    monkeypatch.setattr(
        'services.supabase_factory.get_supabase_admin', lambda: _FakeDB(),
    )

    with caplog.at_level(logging.ERROR, logger='services.model_health'):
        report = model_health.run_slug_health_check()

    assert report['ok'] is False
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert errors, 'a dead slug must log at ERROR'
    message = errors[0].getMessage()
    assert 'test/dead-model' in message
    assert 'ladder_collocation_judge' in message      # names the offending rows


def test_nightly_run_skips_when_lock_held(monkeypatch):
    monkeypatch.setattr(model_health, '_try_lock', lambda db: False)
    monkeypatch.setattr(
        'services.supabase_factory.get_supabase_admin', lambda: _FakeDB(),
    )

    assert model_health.run_slug_health_check() == {'skipped': 'lock'}


# ---------------------------------------------------------------------------
# Fail-closed batch mode
# ---------------------------------------------------------------------------

def test_batch_mode_is_off_by_default():
    assert jbase.is_batch_mode() is False


def test_batch_mode_restores_previous_value():
    with jbase.batch_mode():
        assert jbase.is_batch_mode() is True
        with jbase.batch_mode(False):
            assert jbase.is_batch_mode() is False
        assert jbase.is_batch_mode() is True
    assert jbase.is_batch_mode() is False


def test_batch_mode_does_not_leak_across_threads():
    """A batch in one thread must never flip the contract for a request thread."""
    import threading
    seen = {}

    def _worker():
        seen['batch'] = jbase.is_batch_mode()

    with jbase.batch_mode():
        t = threading.Thread(target=_worker)
        t.start()
        t.join()

    assert seen['batch'] is False


def _missing_template(*_a, **_k):
    raise RuntimeError("No active prompt_templates row for 'ladder_p1_judge'")


def test_serve_path_still_fails_open_on_missing_template(monkeypatch):
    """The pre-existing contract: a dead judge never blocks a live session."""
    monkeypatch.setattr(p1mod, 'get_template_config', _missing_template)

    out = p1mod.judge_p1_sentences(
        db=None, lemma='bank', definition='financial institution',
        sense_fingerprint='bank:money', register='neutral',
        sentences=['a', 'b'], language_id=2,
    )

    assert [o.verdict for o in out] == ['accept', 'accept']


def test_batch_mode_aborts_on_missing_template(monkeypatch):
    """Same failure inside a batch aborts loudly instead of accepting."""
    monkeypatch.setattr(p1mod, 'get_template_config', _missing_template)

    with jbase.batch_mode():
        with pytest.raises(jbase.JudgeUnavailable) as exc:
            p1mod.judge_p1_sentences(
                db=None, lemma='bank', definition='financial institution',
                sense_fingerprint='bank:money', register='neutral',
                sentences=['a', 'b'], language_id=2,
            )

    # Actionable: says what to check, not just "judge failed".
    assert 'prompt_templates' in str(exc.value)


def test_batch_mode_aborts_on_llm_failure(monkeypatch):
    monkeypatch.setattr(
        p1mod, 'get_template_config',
        lambda db, task_name, language_id: {
            'template': '{lemma}{definition}{sense_fingerprint}{register}'
                        '{sentences_numbered}',
            'model': 'test-model', 'provider': 'openrouter', 'version': 1,
        },
    )

    def _boom(*_a, **_k):
        raise RuntimeError('502 from provider')
    monkeypatch.setattr(p1mod, 'call_llm', _boom)

    with jbase.batch_mode():
        with pytest.raises(jbase.JudgeUnavailable):
            p1mod.judge_p1_sentences(
                db=None, lemma='bank', definition='d', sense_fingerprint='f',
                register='neutral', sentences=['a'], language_id=2,
            )


def test_batch_mode_tolerates_a_single_unparseable_rating(monkeypatch):
    """Per-item gaps stay fail-open — one bad entry must not kill 3,000 senses."""
    monkeypatch.setattr(
        p1mod, 'get_template_config',
        lambda db, task_name, language_id: {
            'template': '{lemma}{definition}{sense_fingerprint}{register}'
                        '{sentences_numbered}',
            'model': 'test-model', 'provider': 'openrouter', 'version': 1,
        },
    )
    monkeypatch.setattr(p1mod, 'log_judge_verdict', lambda **kw: None)
    monkeypatch.setattr(p1mod, 'call_llm', lambda *a, **k: {
        '1': {'rating': 5, 'reason': 'clean'},
        '2': {'rating': 'not-a-number'},
    })

    with jbase.batch_mode():
        out = p1mod.judge_p1_sentences(
            db=None, lemma='bank', definition='d', sense_fingerprint='f',
            register='neutral', sentences=['a', 'b'], language_id=2,
        )

    assert [o.verdict for o in out] == ['accept', 'accept']


def test_collocation_judge_fails_closed_in_batch(monkeypatch):
    """The dict-returning fail-open path shares the same chokepoint."""
    monkeypatch.setattr(collocmod, 'get_template_config', _missing_template)

    # Serve path: every distractor kept, no raise.
    kept, _meta = collocmod.filter_collocation_distractors(
        db=None, sentence='s', target='t', correct_collocate='c',
        distractors=['d1', 'd2'], language_id=2,
    )
    assert kept == ['d1', 'd2']

    with jbase.batch_mode():
        with pytest.raises(jbase.JudgeUnavailable):
            collocmod.filter_collocation_distractors(
                db=None, sentence='s', target='t', correct_collocate='c',
                distractors=['d1', 'd2'], language_id=2,
            )
