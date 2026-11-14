"""Background scheduler: the nightly/weekly jobs, declared as one table.

Every job is serialised across processes inside the job itself (Postgres
advisory lock or idempotent upsert), so a scheduler in each gunicorn worker is
safe: only one acquires the lock. Set DISABLE_SCHEDULER=true to keep a process
from scheduling anything (tests, one-off CLI runs, or web workers when the jobs
run in a dedicated process).
"""

import importlib
import os
import threading
from dataclasses import dataclass
from typing import Callable

DISABLE_ENV = 'DISABLE_SCHEDULER'

_lock = threading.Lock()
_running = None


def _log_summary(logger, label, result):
    logger.info("%s: %s", label, result)


def _log_skippable(logger, label, result):
    if result.get('skipped'):
        logger.info("%s: skipped (%s)", label, result.get('reason'))
    else:
        logger.info("%s: %s", label, result)


def _log_slug_health(logger, label, report):
    dead = report.get('dead') or []
    if dead:
        logger.error(
            "Slug health: %d dead model slug(s) — %s",
            len(dead), ', '.join(e['model'] for e in dead),
        )
    else:
        logger.info("Slug health: %d slug(s) probed, all live", report.get('probed', 0))


def _admin_client():
    from services.supabase_factory import get_supabase_admin
    return (get_supabase_admin(),)


@dataclass(frozen=True)
class Job:
    id: str
    target: str                 # 'package.module:function', imported when the job fires
    cron: dict                  # CronTrigger fields, UTC
    label: str
    report: Callable = _log_summary
    args: Callable = tuple      # called at fire time; returns the positional args

    @property
    def when(self):
        day = self.cron.get('day_of_week')
        prefix = f"{day.capitalize()} " if day else ''
        return f"{prefix}{self.cron['hour']:02d}:{self.cron['minute']:02d} UTC"


# Order within the 04:xx chain is deliberate:
#   03:50 DT synthesis promotes error clusters before the morning's first request;
#   04:10 slug health runs after IRT so a slow calibration does not delay it;
#   04:15 queue drain regenerates content, so it follows the slug probe rather
#         than spending its budget on a model that is about to be flagged dead;
#   04:20 watchlist sweep scans tests created since the last run, so it runs
#         after regeneration has landed.
JOBS = (
    Job('dt_error_synthesis_nightly',
        'scripts.dt_nightly_synthesis:run_nightly_synthesis',
        {'hour': 3, 'minute': 50}, 'DT error synthesis', _log_skippable),
    Job('irt_calibration_nightly',
        'services.irt.calibrator:calibrate_all_active_languages',
        {'hour': 4, 'minute': 0}, 'Nightly IRT calibration'),
    Job('exercise_time_estimate_refresh',
        'services.study_plan_service:_refresh_exercise_time_estimates',
        {'hour': 4, 'minute': 5}, 'Time-estimate refresh'),
    Job('slug_health_nightly',
        'services.model_health:run_slug_health_check',
        {'hour': 4, 'minute': 10}, 'Nightly slug health check', _log_slug_health),
    Job('generation_queue_drain_nightly',
        'services.vocabulary_ladder.queue_drain:run_nightly_drain',
        {'hour': 4, 'minute': 15}, 'Generation queue drain', _log_skippable),
    Job('word_upload_watchlist_sweep_nightly',
        'services.word_list_import.sweep_cron:run_watchlist_sweep',
        {'hour': 4, 'minute': 20}, 'Word-upload watchlist sweep', _log_skippable,
        _admin_client),
    Job('study_plan_weekly_recompute',
        'services.study_plan_service:_run_weekly_plan_recompute',
        {'day_of_week': 'sun', 'hour': 23, 'minute': 0}, 'Weekly Study Plan recompute'),
)


def _runner(job, logger):
    """The callable APScheduler fires. A crash is logged, never raised, so one
    failing job cannot take the scheduler down."""
    def run():
        try:
            _use_job_timeout()
            module_name, func_name = job.target.split(':')
            func = getattr(importlib.import_module(module_name), func_name)
            job.report(logger, job.label, func(*job.args()))
        except Exception as exc:
            logger.exception("%s crashed: %s", job.label, exc)
    run.__name__ = f"run_{job.id}"
    return run


def _use_job_timeout():
    """Give this job thread's database clients the longer batch timeout."""
    from config import Config
    from services.supabase_factory import SupabaseFactory
    SupabaseFactory.set_thread_timeout(Config.SUPABASE_JOB_TIMEOUT)


def scheduler_disabled():
    return os.environ.get(DISABLE_ENV, '').lower() in ('1', 'true', 'yes')


def init_scheduler(app):
    """Start the scheduler once per process and attach it as ``app.scheduler``."""
    global _running

    if scheduler_disabled():
        app.logger.info("Scheduler disabled via DISABLE_SCHEDULER")
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        app.logger.warning("APScheduler not installed — nightly jobs will not run")
        return

    with _lock:
        if _running is not None and _running.running:
            app.scheduler = _running
            app.logger.warning("Scheduler already running in this process — not starting another")
            return

        scheduler = BackgroundScheduler(timezone='UTC')
        for job in JOBS:
            scheduler.add_job(
                _runner(job, app.logger),
                trigger=CronTrigger(**job.cron),
                id=job.id,
                coalesce=True,
                max_instances=1,
                replace_existing=True,
            )
        scheduler.start()
        _running = scheduler

    app.scheduler = scheduler
    app.logger.info(
        "APScheduler started — jobs: "
        + ", ".join(f"{job.id} @ {job.when}" for job in JOBS)
    )
