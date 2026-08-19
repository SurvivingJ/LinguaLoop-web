"""TASK-704 / ADR-006 — plan-path retry slot.

The RPC half (build_daily_session emitting <=1 ``slot_type='retry'`` slot with
``original_percentage``, and process_test_submission applying the ADR-006 damped
ELO on submitting one) is verified against the live DB in rollback-only
transactions — see the migration acceptance notes on TASK-704. Here we pin the
Python contract that carries a plan-path retry element through to the enriched
payload the runner renders, so a future refactor can't silently drop
``original_percentage`` or the retry ``slot_type``.
"""

from services.test_service import TestService


def test_normalize_preserves_plan_path_retry_element():
    """build_daily_session emits retry slots as dicts with original_percentage;
    normalization must pass them through untouched (not coerce to a bare 'new')."""
    item = {
        'test_id': '03f1ba3e-316b-45f2-b0c2-4bec27bc38ed',
        'test_type': 'listening',
        'slot_type': 'retry',
        'original_percentage': 50.0,
    }
    out = TestService._normalize_load_item(item)
    assert out['slot_type'] == 'retry'
    assert out['original_percentage'] == 50.0
    assert out['test_type'] == 'listening'


def test_normalize_new_slot_has_no_original_percentage():
    """A 'new' slot from the plan path carries no original_percentage key; the
    enrichment reads it via .get(), so its absence must stay falsy (not error)."""
    item = {
        'test_id': '03f1ba3e-316b-45f2-b0c2-4bec27bc38ed',
        'test_type': 'reading',
        'slot_type': 'new',
    }
    out = TestService._normalize_load_item(item)
    assert out['slot_type'] == 'new'
    assert out.get('original_percentage') is None


def test_normalize_bare_string_defaults_to_new():
    """Defensive: a legacy cached bare-UUID element must not surface as a retry."""
    out = TestService._normalize_load_item('03f1ba3e-316b-45f2-b0c2-4bec27bc38ed')
    assert out['slot_type'] == 'new'
    assert out.get('original_percentage') is None
