"""An unset native language means English explanations, not explanations in
the language being learned (2026-11-11)."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from services.vocabulary.gloss_lookup import get_user_definition_language_id


def _db(native=None, fail=False):
    db = MagicMock()
    chain = db.table.return_value.select.return_value.eq.return_value.single.return_value
    if fail:
        chain.execute.side_effect = RuntimeError('down')
    else:
        chain.execute.return_value = SimpleNamespace(data={'native_language_id': native})
    return db


def test_set_native_language_is_used():
    assert get_user_definition_language_id(_db(3), 'u') == 3


def test_unset_native_language_defaults_to_english():
    assert get_user_definition_language_id(_db(None), 'u') == 2


def test_read_failure_defaults_to_english():
    assert get_user_definition_language_id(_db(fail=True), 'u') == 2
