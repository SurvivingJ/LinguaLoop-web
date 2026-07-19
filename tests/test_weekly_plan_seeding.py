"""Regression tests for TASK-700 — weekly-plan seeding.

Covers the three legs that together ensured a study-plan user actually gets a
plan-driven daily load instead of silently degrading to the legacy 3-test load:

  Leg 1  services/test_service.py       — on E_NOWEEK, get_or_create_daily_load
                                           lazily computes the week and retries
                                           build_daily_session before falling
                                           back to legacy.
  Leg 2  services/study_plan_service.py — the Sunday 23:00 UTC cron seeds the
                                           *upcoming* week, so a fresh Monday
                                           request finds a week row.
  Leg 3  routes/study_plan.py           — the template-only PUT seeds the
                                           current week immediately after
                                           apply_study_plan_template succeeds.
"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import services.test_service as test_service
import services.study_plan_service as study_plan_service
from services.test_service import TestService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chainable_admin(execute_results):
    """A Supabase-style fluent mock whose .execute() yields each result once.

    table()/select()/eq() all return the same mock so the builder chains; only
    .execute() advances through ``execute_results``.
    """
    m = MagicMock()
    m.table.return_value = m
    m.select.return_value = m
    m.eq.return_value = m
    m.execute.side_effect = list(execute_results)
    return m


# ---------------------------------------------------------------------------
# Leg 1 — lazy Tier B compute on E_NOWEEK
# ---------------------------------------------------------------------------

class TestLazyComputeOnNoWeek:

    def test_e_noweek_triggers_compute_and_retry_returns_plan_driven_load(self):
        """E_NOWEEK → compute_weekly_plan(week) → retry → plan-driven load."""
        # daily_test_loads: (1) no existing load, (2) refetch after the RPC
        # UPSERTed the plan-driven load.
        refetched_row = {
            'load_date': '2026-07-20',
            'test_ids': ['t1', 't2'],
            'completed_test_ids': [],
        }
        admin = _chainable_admin([
            SimpleNamespace(data=[]),              # existence check → none
            SimpleNamespace(data=[refetched_row]), # refetch after success
        ])

        svc = TestService(supabase_admin=admin)
        svc._user_has_study_plan = MagicMock(return_value=True)
        svc._enrich_daily_load = MagicMock(
            side_effect=lambda row: {'enriched': True, 'row': row}
        )

        resolver = MagicMock()
        resolver.build_daily_session.side_effect = [
            {'error': 'no_week', 'code': 'E_NOWEEK', 'week_start': '2026-07-20'},
            {'load_date': '2026-07-20', 'queue': [{'kind': 'practice'}]},
        ]
        resolver.compute_weekly_plan.return_value = {'target_counts': {'r': 1}}

        with patch.object(test_service.Config, 'STUDY_PLAN_ENABLED', True), \
             patch('services.study_plan_service.StudyPlanService',
                   return_value=resolver):
            result = svc.get_or_create_daily_load('u1', 1)

        # Lazy compute fired exactly once, keyed to the week the RPC reported.
        resolver.compute_weekly_plan.assert_called_once_with(
            'u1', 1, date(2026, 7, 20),
        )
        # Resolver was retried after the compute.
        assert resolver.build_daily_session.call_count == 2
        # Result came from the refetched plan-driven row, not the legacy path.
        assert result == {'enriched': True, 'row': refetched_row}

    def test_retry_still_noweek_falls_back_to_legacy(self):
        """If the retry still declines, we fall through to the legacy load."""
        admin = _chainable_admin([
            SimpleNamespace(data=[]),  # existence check → none
        ])

        svc = TestService(supabase_admin=admin)
        svc._user_has_study_plan = MagicMock(return_value=True)
        # Legacy path returns no items → early empty-load dict (no insert).
        svc._compute_daily_load = MagicMock(return_value=[])

        resolver = MagicMock()
        resolver.build_daily_session.side_effect = [
            {'error': 'no_week', 'code': 'E_NOWEEK', 'week_start': '2026-07-20'},
            {'error': 'no_week', 'code': 'E_NOWEEK', 'week_start': '2026-07-20'},
        ]

        with patch.object(test_service.Config, 'STUDY_PLAN_ENABLED', True), \
             patch('services.study_plan_service.StudyPlanService',
                   return_value=resolver):
            result = svc.get_or_create_daily_load('u1', 1)

        resolver.compute_weekly_plan.assert_called_once()
        assert resolver.build_daily_session.call_count == 2
        # Legacy fallback ran.
        svc._compute_daily_load.assert_called_once_with('u1', 1)
        assert result['tests'] == []


# ---------------------------------------------------------------------------
# Leg 2 — Sunday cron seeds the upcoming week
# ---------------------------------------------------------------------------

class TestCronTargetsUpcomingWeek:

    def test_sunday_recompute_seeds_next_monday(self):
        sunday = date(2026, 7, 19)
        assert sunday.weekday() == 6, "fixture date must be a Sunday"
        expected_week = date(2026, 7, 20)  # the upcoming Monday
        assert expected_week.weekday() == 0

        db = MagicMock()
        db.table.return_value.select.return_value.range.return_value.execute.return_value = (
            SimpleNamespace(data=[{'user_id': 'u1', 'language_id': 1}])
        )

        fake_date = MagicMock(wraps=date)
        fake_date.today.return_value = sunday

        with patch('services.study_plan_service.get_supabase_admin',
                   return_value=db), \
             patch('services.study_plan_service.date', fake_date), \
             patch.object(study_plan_service.StudyPlanService,
                          'compute_weekly_plan') as mock_compute:
            summary = study_plan_service._run_weekly_plan_recompute()

        mock_compute.assert_called_once_with('u1', 1, expected_week)
        assert summary['week_start'] == expected_week.isoformat()
        assert summary['fired'] == 1


# ---------------------------------------------------------------------------
# Leg 3 — template-only PUT seeds the current week
# ---------------------------------------------------------------------------

class TestTemplateApplySeedsCurrentWeek:

    def test_put_template_only_triggers_current_week_compute(self, client, auth_headers):
        from routes.study_plan import _monday_of

        db = MagicMock()
        db.rpc.return_value.execute.return_value = SimpleNamespace(
            data={'template_id': 5, 'daily_minutes': 30}
        )

        resolver = MagicMock()

        with patch('routes.study_plan.get_supabase_admin', return_value=db), \
             patch('services.study_plan_service.StudyPlanService',
                   return_value=resolver):
            resp = client.put(
                '/api/study-plan',
                json={'language_id': 1, 'template_id': 5},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        # apply_study_plan_template was the RPC invoked.
        assert db.rpc.call_args[0][0] == 'apply_study_plan_template'
        # The current week was seeded immediately after the template applied.
        resolver.compute_weekly_plan.assert_called_once_with(
            'test-user-id-123', 1, _monday_of(date.today()),
        )
