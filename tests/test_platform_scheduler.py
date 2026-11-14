"""The declarative job table and the scheduler's start-up guards."""

import logging
import sys
import types

import pytest

from web import scheduler as sched

# id -> (day_of_week, hour, minute). The schedule production has always run.
EXPECTED = {
    'dt_error_synthesis_nightly': ('*', 3, 50),
    'irt_calibration_nightly': ('*', 4, 0),
    'exercise_time_estimate_refresh': ('*', 4, 5),
    'slug_health_nightly': ('*', 4, 10),
    'generation_queue_drain_nightly': ('*', 4, 15),
    'word_upload_watchlist_sweep_nightly': ('*', 4, 20),
    'study_plan_weekly_recompute': ('sun', 23, 0),
}


class _App:
    def __init__(self):
        self.logger = logging.getLogger('test-scheduler')


@pytest.fixture()
def started(monkeypatch):
    """Start the real scheduler paused, so no job can fire."""
    monkeypatch.delenv(sched.DISABLE_ENV, raising=False)
    monkeypatch.setattr(sched, '_running', None)
    from apscheduler.schedulers.background import BackgroundScheduler
    real_start = BackgroundScheduler.start
    monkeypatch.setattr(BackgroundScheduler, 'start',
                        lambda self, *a, **k: real_start(self, paused=True))
    app = _App()
    sched.init_scheduler(app)
    yield app
    app.scheduler.shutdown(wait=False)


def test_job_table_matches_the_production_schedule(started):
    jobs = {job.id: job for job in started.scheduler.get_jobs()}
    assert set(jobs) == set(EXPECTED)
    for job_id, (day, hour, minute) in EXPECTED.items():
        fields = {f.name: str(f) for f in jobs[job_id].trigger.fields}
        assert (fields['day_of_week'], int(fields['hour']), int(fields['minute'])) == (day, hour, minute)
        assert jobs[job_id].coalesce is True
        assert jobs[job_id].max_instances == 1
        assert str(jobs[job_id].trigger.timezone) in ('UTC', 'Etc/UTC')


def test_every_job_target_is_importable():
    import importlib
    for job in sched.JOBS:
        module_name, func_name = job.target.split(':')
        assert callable(getattr(importlib.import_module(module_name), func_name)), job.id


def test_second_start_in_the_same_process_reuses_the_running_scheduler(started):
    second = _App()
    sched.init_scheduler(second)
    assert second.scheduler is started.scheduler
    assert len(started.scheduler.get_jobs()) == len(EXPECTED)


@pytest.mark.parametrize('value', ['true', '1', 'YES'])
def test_env_switch_disables_the_scheduler(monkeypatch, value):
    monkeypatch.setenv(sched.DISABLE_ENV, value)
    monkeypatch.setattr(sched, '_running', None)
    app = _App()
    sched.init_scheduler(app)
    assert not hasattr(app, 'scheduler')
    assert sched._running is None


# ---------------------------------------------------------------------------
# The job runner
# ---------------------------------------------------------------------------

@pytest.fixture()
def fake_target(monkeypatch):
    """A module the runner can import, plus a no-op timeout switch."""
    module = types.ModuleType('_fake_job_module')
    monkeypatch.setitem(sys.modules, '_fake_job_module', module)
    monkeypatch.setattr(sched, '_use_job_timeout', lambda: None)
    return module


def _job(report=sched._log_summary, args=tuple):
    return sched.Job('fake_job', '_fake_job_module:run', {'hour': 1, 'minute': 2},
                     'Fake job', report, args)


def test_runner_logs_the_summary(fake_target, caplog):
    fake_target.run = lambda: {'done': 3}
    with caplog.at_level(logging.INFO):
        sched._runner(_job(), logging.getLogger('t'))()
    assert "Fake job: {'done': 3}" in caplog.text


def test_runner_reports_a_skipped_run(fake_target, caplog):
    fake_target.run = lambda: {'skipped': True, 'reason': 'lock held'}
    with caplog.at_level(logging.INFO):
        sched._runner(_job(sched._log_skippable), logging.getLogger('t'))()
    assert 'Fake job: skipped (lock held)' in caplog.text


def test_runner_passes_arguments_resolved_at_fire_time(fake_target):
    seen = []
    fake_target.run = lambda db: seen.append(db) or {}
    sched._runner(_job(sched._log_skippable, lambda: ('client',)), logging.getLogger('t'))()
    assert seen == ['client']


def test_runner_swallows_a_crash(fake_target, caplog):
    def run():
        raise RuntimeError('boom')
    fake_target.run = run
    with caplog.at_level(logging.ERROR):
        sched._runner(_job(), logging.getLogger('t'))()
    assert 'Fake job crashed: boom' in caplog.text


def test_slug_health_report_flags_dead_models(caplog):
    with caplog.at_level(logging.INFO):
        sched._log_slug_health(logging.getLogger('t'), 'x', {'dead': [{'model': 'a/b'}]})
        sched._log_slug_health(logging.getLogger('t'), 'x', {'probed': 4})
    assert '1 dead model slug(s) — a/b' in caplog.text
    assert '4 slug(s) probed, all live' in caplog.text


def test_job_times_are_described_for_the_startup_log():
    by_id = {job.id: job.when for job in sched.JOBS}
    assert by_id['dt_error_synthesis_nightly'] == '03:50 UTC'
    assert by_id['study_plan_weekly_recompute'] == 'Sun 23:00 UTC'
