"""Unit tests for the correction-style A/B assignment (TASK-617).

Covers config.py::Config.resolve_correction_style — the deterministic per-user
bucketing + the force-on/force-off QA levers — with no Flask app and no DB.
The route-level stamping (get_next writes the arm onto dt_submission and returns
it in the /next payload) is covered in test_dual_translation_routes.py.
"""

import pytest

from config import Config


ARMS = ('direct_metalinguistic', 'flag_only')


@pytest.fixture
def set_mode(monkeypatch):
    """Set Config.DT_CORRECTION_STYLE for the duration of a test."""
    def _set(mode):
        monkeypatch.setattr(Config, 'DT_CORRECTION_STYLE', mode)
    return _set


class TestForcedArms:
    """Force-to-one-arm must work for QA without touching code."""

    def test_force_direct_metalinguistic(self, set_mode):
        set_mode('direct_metalinguistic')
        # Every user, regardless of id, gets the forced arm.
        for uid in ('u1', 'u2', 'de6fd05b-0000-0000-0000-000000000000', ''):
            assert Config.resolve_correction_style(uid) == 'direct_metalinguistic'

    def test_force_flag_only(self, set_mode):
        set_mode('flag_only')
        for uid in ('u1', 'u2', 'de6fd05b-0000-0000-0000-000000000000', ''):
            assert Config.resolve_correction_style(uid) == 'flag_only'


class TestExperimentBucketing:

    def test_arm_is_a_valid_value(self, set_mode):
        set_mode('experiment')
        assert Config.resolve_correction_style('u1') in ARMS

    def test_same_user_is_stably_bucketed(self, set_mode):
        set_mode('experiment')
        uid = 'de6fd05b-1234-5678-9abc-def012345678'
        first = Config.resolve_correction_style(uid)
        # Re-resolving the same id many times never flips the arm.
        for _ in range(50):
            assert Config.resolve_correction_style(uid) == first

    def test_both_arms_are_reachable(self, set_mode):
        set_mode('experiment')
        seen = {Config.resolve_correction_style('user-%d' % i) for i in range(200)}
        assert seen == set(ARMS), "both arms should appear across many users"

    def test_split_is_roughly_balanced(self, set_mode):
        set_mode('experiment')
        n = 2000
        flag = sum(
            Config.resolve_correction_style('user-%d' % i) == 'flag_only'
            for i in range(n)
        )
        # SHA-256 low bit is uniform; allow a generous band around 50/50.
        assert 0.4 * n < flag < 0.6 * n

    def test_unknown_mode_falls_safe_to_experiment(self, set_mode):
        # A typo'd / unrecognized flag value must not force a single arm; it
        # falls through to deterministic bucketing rather than erroring.
        set_mode('nonsense-value')
        uid = 'de6fd05b-1234-5678-9abc-def012345678'
        assert Config.resolve_correction_style(uid) in ARMS
        # ...and matches what pure 'experiment' would assign for the same id.
        set_mode('experiment')
        expected = Config.resolve_correction_style(uid)
        set_mode('nonsense-value')
        assert Config.resolve_correction_style(uid) == expected
