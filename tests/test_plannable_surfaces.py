"""TASK-714 / ADR-021 — the plannable-surface boundary.

Three things this pins, each matching an acceptance criterion:

  * flashcards / dual_translation are budgeted with EXPLICIT time estimates and
    never fall through ``test_time_estimate``'s catch-all ``ELSE 5.0``. ADR-021
    calls that catch-all a silent wrong answer of the same shape as F3.
  * listening_lab / mystery stay OUTSIDE the planner. Both are dim_test_types
    rows, so they look plannable to anything reading that table — this test
    exists precisely so a later change cannot quietly pull them in.
  * the /api/study-session queue emits mountable items for the new kinds and
    accepts their completion, which is what makes the weekly counters move
    (the F2 / TASK-701 failure mode).
"""

import re
from pathlib import Path

import pytest

from config import Config
from routes.study_session import (
    _FLASHCARD_CARDS_PER_BLOCK,
    _SURFACE_BLOCKS,
    _build_surface_items,
    _surface_skill_for,
    _valid_block_ids,
    build_session_queue,
)
from services.study_plan_service import (
    PLANNABLE_SURFACE_SKILLS,
    UNPLANNED_TEST_TYPES,
    UNSEEDED_SKILL_MINUTES,
    _test_time_estimate,
)

REPO = Path(__file__).resolve().parents[1]
TIME_ESTIMATE_SQL = (
    REPO / 'migrations' / 'task715_test_time_estimate_tiered.sql'
).read_text(encoding='utf-8')
RESOLVER_SQL = (
    REPO / 'migrations' / 'archive' / 'task714_build_daily_session_surfaces.sql'
).read_text(encoding='utf-8')
TEMPLATE_SEED_SQL = (
    REPO / 'migrations' / 'task714_seed_surface_budgets.sql'
).read_text(encoding='utf-8')
DAY_BOUNDARY_SQL = (
    REPO / 'migrations' / 'task716_local_day_boundary.sql'
).read_text(encoding='utf-8')


class _NoP50Db:
    """Stands in for a DB where dim_test_types has no row for the skill.

    That is the real situation for flashcards / dual_translation: they are not
    dim_test_types rows at all, so the COALESCE onto expected_minutes_p50 can
    never fire and only the CASE seed stands between them and ELSE 5.0.
    """

    def table(self, _name):
        return self

    def select(self, *_a):
        return self

    def eq(self, *_a):
        return self

    def limit(self, *_a):
        return self

    def execute(self):
        class R:
            data = []

        return R()


# ---------------------------------------------------------------------------
# AC: time estimates are seeded explicitly, not defaulted
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('skill', PLANNABLE_SURFACE_SKILLS)
def test_surface_skill_is_seeded_in_python_and_not_the_catch_all(skill):
    minutes = _test_time_estimate(skill, _NoP50Db())
    assert skill in Config.TEST_TYPE_MINUTES, (
        f'{skill} is planned but unseeded — it would be budgeted at the '
        f'{UNSEEDED_SKILL_MINUTES}-minute catch-all with no error (ADR-021).'
    )
    assert minutes != float(UNSEEDED_SKILL_MINUTES), (
        f'{skill} resolves to the catch-all value; seed a distinct estimate.'
    )
    assert minutes > 0


@pytest.mark.parametrize('skill', PLANNABLE_SURFACE_SKILLS)
def test_surface_skill_is_seeded_in_the_sql_case(skill):
    """The SQL twin must carry the same seed, or Tier C budgets the day at 5
    minutes a slot while Tier B sized the week at the real value."""
    assert f"WHEN '{skill}'" in TIME_ESTIMATE_SQL, (
        f'{skill} is missing from the test_time_estimate CASE; it would hit '
        'the ELSE 5.0 branch silently.'
    )


@pytest.mark.parametrize('skill', PLANNABLE_SURFACE_SKILLS)
def test_python_and_sql_seeds_agree(skill):
    """A divergence here means the week never fits its own days."""
    match = re.search(rf"WHEN '{skill}'\s+THEN\s+([0-9.]+)", TIME_ESTIMATE_SQL)
    assert match, f'could not parse the SQL seed for {skill}'
    assert float(match.group(1)) == float(Config.TEST_TYPE_MINUTES[skill])


def test_unknown_skill_still_falls_back_rather_than_raising():
    """The catch-all stays — a plan must still solve. It just has to be loud;
    the WARNING is emitted by _test_time_estimate."""
    assert _test_time_estimate('not_a_real_skill', _NoP50Db()) == float(
        UNSEEDED_SKILL_MINUTES
    )


# ---------------------------------------------------------------------------
# AC: listening_lab and mystery remain unscheduled
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('skill', UNPLANNED_TEST_TYPES)
def test_deliberately_unplanned_type_is_not_a_plannable_surface(skill):
    assert skill not in PLANNABLE_SURFACE_SKILLS
    assert skill not in _SURFACE_BLOCKS


@pytest.mark.parametrize('skill', UNPLANNED_TEST_TYPES)
def test_deliberately_unplanned_type_is_not_seeded_for_budgeting(skill):
    """Seeding a time estimate would be the first step to scheduling it.
    ADR-021 keeps both outside the planner on purpose: long-form exploratory
    content does not belong in a minute budget."""
    assert skill not in Config.TEST_TYPE_MINUTES


@pytest.mark.parametrize('skill', UNPLANNED_TEST_TYPES)
def test_deliberately_unplanned_type_is_not_in_the_resolver_surface_list(skill):
    assert f"'{skill}'" not in RESOLVER_SQL


@pytest.mark.parametrize('skill', UNPLANNED_TEST_TYPES)
def test_deliberately_unplanned_type_is_not_seeded_into_templates(skill):
    """A template key is what makes a skill reachable at all — Tier B walks
    weekly_test_counts and nothing outside it can enter target_counts."""
    assert skill not in TEMPLATE_SEED_SQL


def test_template_seed_covers_both_new_surfaces():
    for skill in PLANNABLE_SURFACE_SKILLS:
        assert f"'{skill}'" in TEMPLATE_SEED_SQL


# ---------------------------------------------------------------------------
# AC: the queue emits mountable items and accepts their completion
# ---------------------------------------------------------------------------

def test_surface_items_are_emitted_from_hydrated_counts():
    targets = {'surface_counts': {'flashcards': 2, 'dual_translation': 1}}
    items = _build_surface_items(targets, [])

    kinds = [i['kind'] for i in items]
    assert kinds.count('flashcards') == 2
    assert kinds.count('dual_translation') == 1
    assert [i['id'] for i in items] == [
        'flashcards_1', 'flashcards_2', 'dual_translation_1',
    ]
    # The flashcards player reads item.cards to size its block.
    assert all(
        i['cards'] == _FLASHCARD_CARDS_PER_BLOCK
        for i in items if i['kind'] == 'flashcards'
    )


def test_surface_items_reflect_completion():
    targets = {'surface_counts': {'flashcards': 2}}
    items = _build_surface_items(targets, ['flashcards_1'])
    assert [i['is_completed'] for i in items] == [True, False]


def test_rows_without_surface_counts_degrade_to_no_surfaces():
    """Every daily_test_loads row written before TASK-714 looks like this."""
    assert _build_surface_items({}, []) == []
    assert _build_surface_items({'practice_acquisition_min': 20}, []) == []


def test_zero_hydrated_surface_emits_nothing():
    """A budgeted-but-unhydrated surface (e.g. no cards due) must not appear as
    an empty block the learner opens and finds nothing in."""
    assert _build_surface_items({'surface_counts': {'flashcards': 0}}, []) == []


def test_valid_block_ids_covers_practice_and_surfaces():
    targets = {
        'practice_acquisition_min': 20,
        'surface_counts': {'flashcards': 1, 'dual_translation': 1},
    }
    ids = _valid_block_ids(targets)
    assert {'practice_acq_1', 'practice_acq_2'} <= ids
    assert {'flashcards_1', 'dual_translation_1'} <= ids


def test_completion_routing_identifies_surface_blocks():
    assert _surface_skill_for('flashcards_1') == 'flashcards'
    assert _surface_skill_for('dual_translation_3') == 'dual_translation'
    # Practice chunks are NOT surfaces: the practice service owns their
    # counters and crediting them here would double-count.
    assert _surface_skill_for('practice_acq_1') is None
    assert _surface_skill_for('practice_maint_2') is None


def test_flashcards_lead_the_session_and_dt_joins_the_queue():
    tests = [
        {'id': 't1', 'test_type': 'reading', 'slug': 'a'},
        {'id': 't2', 'test_type': 'reading', 'slug': 'b'},
    ]
    targets = {'surface_counts': {'flashcards': 1, 'dual_translation': 1}}
    queue = build_session_queue(tests, targets, [], 'user-1', '2026-08-07')

    kinds = [q['kind'] for q in queue]
    assert kinds[0] == 'flashcards'
    assert 'dual_translation' in kinds
    assert kinds.count('test') == 2


def test_queue_order_is_stable_across_calls():
    """Resume depends on it — same inputs, same order."""
    tests = [{'id': f't{i}', 'test_type': 'reading'} for i in range(4)]
    targets = {'surface_counts': {'flashcards': 1, 'dual_translation': 2}}
    a = build_session_queue(tests, targets, [], 'user-1', '2026-08-07')
    b = build_session_queue(tests, targets, [], 'user-1', '2026-08-07')
    assert [i['id'] for i in a] == [i['id'] for i in b]


# ---------------------------------------------------------------------------
# AC: shortfall telemetry covers the new kinds
# ---------------------------------------------------------------------------

def test_resolver_reports_surfaces_in_requested_and_hydrated_counts():
    """test_service._log_hydration_shortfalls compares requested vs hydrated
    per skill and WARNs on a gap. It needs no change to cover surfaces — but
    only if the resolver actually puts them in both maps."""
    assert 'SELECT skill, requested FROM pg_temp.surface_counts' in RESOLVER_SQL
    assert 'SELECT skill, hydrated FROM pg_temp.surface_counts' in RESOLVER_SQL


def test_resolver_clamps_surfaces_to_their_real_pools():
    """A budgeted flashcards block with nothing due is a REAL shortfall, and
    must be reported as one rather than emitted as an empty block."""
    assert 'LEAST(' in RESOLVER_SQL
    assert 'user_flashcards' in RESOLVER_SQL
    assert 'dt_passage' in RESOLVER_SQL


def test_record_session_progress_accepts_the_surface_kind():
    """Without this the completion signal never reaches the weekly counters —
    exactly the F2 / TASK-701 defect ADR-021 warns about for new surfaces."""
    assert "'test','surface','practice_maint','practice_acq'" in DAY_BOUNDARY_SQL
    assert "p_kind IN ('test','surface')" in DAY_BOUNDARY_SQL
