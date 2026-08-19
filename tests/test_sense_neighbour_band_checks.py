"""
The embedding band check must call an RPC that exists (TASK-521 / TASK-522).

Why this file exists: `neighbour_similarities` called
`nearest_senses(p_sense_id, p_language_id, p_lemmas)` — a signature the live
function has never had — and read `lemma`/`similarity` where it returns
`out_lemma`/`out_similarity`. Every call raised PGRST202, the bare
`except Exception` turned that into "RPC unavailable", and the band check
returned "no opinion" on every foil forever. Nothing failed; the feature simply
never ran, and the log line was indistinguishable from the backfill not having
been run yet.

This is the fourth instance of the class ADR-020 describes: a symbolic reference
resolved late, failing into a silent no-op instead of an error. So the tests
below assert on the *contract* — the RPC name, its argument keys and its result
keys — not merely on the happy path.
"""

from unittest.mock import MagicMock

import pytest

from services.vocabulary_ladder import sense_neighbours as sn


class _DB:
    """Records the rpc() call and replays a canned response."""

    def __init__(self, rows=None, raises=None):
        self._rows = rows or []
        self._raises = raises
        self.calls = []

    def rpc(self, name, params):
        self.calls.append((name, params))
        if self._raises:
            raise self._raises
        result = MagicMock()
        result.data = self._rows
        result.execute = lambda: result
        return result


# ---------------------------------------------------------------------------
# The contract
# ---------------------------------------------------------------------------

def test_calls_the_similarity_rpc_not_nearest_senses():
    """`nearest_senses` takes no lemma list — calling it here always 404s."""
    db = _DB(rows=[{'lemma': 'accuracy', 'similarity': 0.71}])
    sn.neighbour_similarities(db, 1, 2, ['accuracy'])

    name, _ = db.calls[0]
    assert name == 'sense_similarity_to_lemmas'
    assert name != 'nearest_senses'


def test_passes_the_argument_names_the_function_declares():
    db = _DB(rows=[])
    sn.neighbour_similarities(db, 42, 3, ['犬', '猫'])

    _, params = db.calls[0]
    assert set(params) == {'p_sense_id', 'p_language_id', 'p_lemmas'}
    assert params['p_sense_id'] == 42
    assert params['p_language_id'] == 3
    assert params['p_lemmas'] == ['犬', '猫']


def test_reads_the_column_names_the_function_returns():
    """`lemma`/`similarity` — not the `out_`-prefixed names of nearest_senses."""
    db = _DB(rows=[{'lemma': 'accuracy', 'similarity': 0.71}])
    assert sn.neighbour_similarities(db, 1, 2, ['accuracy']) == {'accuracy': 0.71}


def test_out_prefixed_rows_yield_nothing():
    """Guards the other half of the original bug.

    If someone repoints this at nearest_senses again, the rows come back
    `out_lemma`/`out_similarity` and this returns {} — so the assertion above
    is not enough on its own to distinguish the two functions.
    """
    db = _DB(rows=[{'out_lemma': 'accuracy', 'out_similarity': 0.71}])
    assert sn.neighbour_similarities(db, 1, 2, ['accuracy']) == {}


# ---------------------------------------------------------------------------
# Degrading
# ---------------------------------------------------------------------------

def test_rpc_failure_is_logged_at_warning_not_info(caplog):
    """At INFO this hid for the feature's entire life."""
    db = _DB(raises=RuntimeError('PGRST202 no such function'))
    with caplog.at_level('WARNING'):
        assert sn.neighbour_similarities(db, 1, 2, ['accuracy']) == {}
    assert any(r.levelname == 'WARNING' for r in caplog.records)


def test_missing_candidate_is_absent_rather_than_zero():
    """A word with no sense row must read as "no opinion", never as distance 0.

    Zero would score as "utterly unrelated" and get the foil dropped, which is
    a verdict the data does not support.
    """
    db = _DB(rows=[{'lemma': 'accuracy', 'similarity': 0.71}])
    out = sn.neighbour_similarities(db, 1, 2, ['accuracy', 'nonexistentword'])
    assert 'nonexistentword' not in out

    checks = sn.band_check_foils(db, 1, 2, ['nonexistentword'])
    assert checks['nonexistentword'].in_band is None
    assert checks['nonexistentword'].usable is False


def test_no_candidates_makes_no_call():
    db = _DB()
    assert sn.neighbour_similarities(db, 1, 2, []) == {}
    assert db.calls == []


# ---------------------------------------------------------------------------
# The band itself
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('similarity, expected', [
    (0.20, False),   # unrelated — filler, not a distractor
    (0.35, True),    # lower bound is inclusive
    (0.60, True),
    (0.88, True),    # upper bound is inclusive
    (0.95, False),   # near-duplicate — probably also correct
])
def test_band_edges(similarity, expected):
    assert sn.check_band(similarity).in_band is expected


def test_band_check_of_none_is_no_opinion():
    assert sn.check_band(None).in_band is None
