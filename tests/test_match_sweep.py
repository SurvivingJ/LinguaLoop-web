"""Unit tests for services/word_list_import/match_sweep.py.

Step 4 of wiki/tasklist/word-list-import.plan.md ("Word List Upload ->
Ladder Exposure + Matched Test Queueing") — the write-side match sweep.
`sweep_immediate_matches` must agree with the ALREADY-BUILT read side (the
`word_upload` slot block in migrations/word_upload_slot_scheduling.sql) on
what "closest in ELO" means: only active-test-type `test_skill_ratings` rows
count, and an unrated `user_skill_ratings` skill defaults to 1200.

No real database, no network: a minimal in-memory fake stands in for the
Supabase query-builder surface (same shape as tests/test_word_resolver.py's
FakeDB/_FakeQuery, extended here with `.overlaps(...)` for the
`tests.vocab_sense_ids` array-membership filter).
"""

import services.word_list_import.match_sweep as ms

# ---------------------------------------------------------------------------
# Fakes — minimal in-memory stand-in for the Supabase query-builder surface
# ---------------------------------------------------------------------------


class _Resp:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    """One chained Supabase query-builder call, backed by an in-memory list
    of row dicts shared with the owning FakeDB table."""

    def __init__(self, rows):
        self._rows = rows
        self._filters = []  # list of (kind, col, val)
        self._op = None

    # -- filter builders (all return self) ------------------------------
    def select(self, *_a, **_kw):
        return self

    def eq(self, col, val):
        self._filters.append(('eq', col, val))
        return self

    def in_(self, col, vals):
        self._filters.append(('in', col, set(vals)))
        return self

    def overlaps(self, col, vals):
        self._filters.append(('overlaps', col, set(vals)))
        return self

    def update(self, payload):
        self._op = ('update', payload)
        return self

    # -- matching ---------------------------------------------------------
    def _match(self, row):
        for kind, col, val in self._filters:
            row_val = row.get(col)
            if kind == 'eq':
                if row_val != val:
                    return False
            elif kind == 'in':
                if row_val not in val:
                    return False
            elif kind == 'overlaps':
                row_set = set(str(v) for v in (row_val or []))
                if not (row_set & val):
                    return False
        return True

    def execute(self):
        matched = [r for r in self._rows if self._match(r)]
        if self._op:
            kind, payload = self._op
            if kind == 'update':
                for r in matched:
                    r.update(payload)
                return _Resp(matched)
        return _Resp(matched)


class FakeDB:
    """Minimal in-memory stand-in for the Supabase client surface used by
    match_sweep's tests/test_skill_ratings/dim_test_types/user_skill_ratings/
    user_word_watchlist queries."""

    def __init__(self):
        self._tables: dict = {}

    def seed(self, table, rows):
        self._tables[table] = [dict(r) for r in rows]

    def table(self, name):
        rows = self._tables.setdefault(name, [])
        return _FakeQuery(rows)


# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

LISTENING = 10
READING = 11
INACTIVE_TYPE = 12

LANG_EN = 2
USER = 'user-1'


def _watchlist_row(**overrides):
    row = {
        'id': 1,
        'user_id': USER,
        'sense_id': 500,
        'language_id': LANG_EN,
        'last_matched_test_id': None,
    }
    row.update(overrides)
    return row


def _seed_dim_test_types(db):
    db.seed('dim_test_types', [
        {'id': LISTENING, 'is_active': True},
        {'id': READING, 'is_active': True},
        {'id': INACTIVE_TYPE, 'is_active': False},
    ])


# ---------------------------------------------------------------------------
# Clear ELO-closest match found and written, surfaced_at reset
# ---------------------------------------------------------------------------


def test_closest_elo_match_is_written_with_surfaced_at_reset():
    db = FakeDB()
    _seed_dim_test_types(db)
    db.seed('tests', [
        {'id': 'test-a', 'vocab_sense_ids': [500], 'is_active': True, 'language_id': LANG_EN},
    ])
    db.seed('test_skill_ratings', [
        {'test_id': 'test-a', 'test_type_id': LISTENING, 'elo_rating': 1210},
    ])
    db.seed('user_skill_ratings', [
        {'user_id': USER, 'language_id': LANG_EN, 'test_type_id': LISTENING, 'elo_rating': 1200},
    ])
    db.seed('user_word_watchlist', [_watchlist_row(last_matched_surfaced_at='2020-01-01T00:00:00+00:00')])

    out = ms.sweep_immediate_matches([db._tables['user_word_watchlist'][0]], db)

    assert out['matched'] == 1
    assert out['no_match'] == 0
    row = db._tables['user_word_watchlist'][0]
    assert row['last_matched_test_id'] == 'test-a'
    assert row['last_matched_surfaced_at'] is None
    assert row['last_matched_at'] is not None

    result = out['results'][0]
    assert result['matched_test_id'] == 'test-a'
    assert result['elo_diff'] == 10
    assert result['changed'] is True


# ---------------------------------------------------------------------------
# No matching test found — row left untouched, no error
# ---------------------------------------------------------------------------


def test_no_matching_test_leaves_row_untouched():
    db = FakeDB()
    _seed_dim_test_types(db)
    db.seed('tests', [
        # Different sense entirely — no overlap with sense_id=500.
        {'id': 'test-a', 'vocab_sense_ids': [999], 'is_active': True, 'language_id': LANG_EN},
    ])
    db.seed('user_word_watchlist', [_watchlist_row()])

    out = ms.sweep_immediate_matches([db._tables['user_word_watchlist'][0]], db)

    assert out['no_match'] == 1
    assert out['matched'] == 0
    row = db._tables['user_word_watchlist'][0]
    assert row['last_matched_test_id'] is None
    assert 'last_matched_at' not in row or row.get('last_matched_at') is None

    result = out['results'][0]
    assert result['matched_test_id'] is None
    assert result['changed'] is False


def test_inactive_candidate_test_is_not_matched():
    """An overlapping test that is is_active=False must never be picked."""
    db = FakeDB()
    _seed_dim_test_types(db)
    db.seed('tests', [
        {'id': 'test-inactive', 'vocab_sense_ids': [500], 'is_active': False, 'language_id': LANG_EN},
    ])
    db.seed('test_skill_ratings', [
        {'test_id': 'test-inactive', 'test_type_id': LISTENING, 'elo_rating': 1200},
    ])
    db.seed('user_word_watchlist', [_watchlist_row()])

    out = ms.sweep_immediate_matches([db._tables['user_word_watchlist'][0]], db)

    assert out['no_match'] == 1
    row = db._tables['user_word_watchlist'][0]
    assert row['last_matched_test_id'] is None


def test_candidate_with_only_inactive_skill_type_is_not_matched():
    """A test overlapping the sense exists and is active, but its only
    test_skill_ratings row is for an INACTIVE test type — no usable ELO
    exists for it (mirrors Step 6's dtt.is_active=true join), so it must not
    be picked."""
    db = FakeDB()
    _seed_dim_test_types(db)
    db.seed('tests', [
        {'id': 'test-a', 'vocab_sense_ids': [500], 'is_active': True, 'language_id': LANG_EN},
    ])
    db.seed('test_skill_ratings', [
        {'test_id': 'test-a', 'test_type_id': INACTIVE_TYPE, 'elo_rating': 1200},
    ])
    db.seed('user_word_watchlist', [_watchlist_row()])

    out = ms.sweep_immediate_matches([db._tables['user_word_watchlist'][0]], db)

    assert out['no_match'] == 1
    row = db._tables['user_word_watchlist'][0]
    assert row['last_matched_test_id'] is None


def test_candidate_beyond_elo_cutoff_is_not_matched():
    """The sole candidate exists and is otherwise eligible, but its ELO is
    far beyond ELO_MATCH_CUTOFF from the user's rating — must not surface a
    badly mismatched 'closest of a bad bunch' test."""
    db = FakeDB()
    _seed_dim_test_types(db)
    db.seed('tests', [
        {'id': 'test-far', 'vocab_sense_ids': [500], 'is_active': True, 'language_id': LANG_EN},
    ])
    db.seed('test_skill_ratings', [
        {'test_id': 'test-far', 'test_type_id': LISTENING, 'elo_rating': 1900},
    ])
    db.seed('user_skill_ratings', [
        {'user_id': USER, 'language_id': LANG_EN, 'test_type_id': LISTENING, 'elo_rating': 1200},
    ])
    db.seed('user_word_watchlist', [_watchlist_row()])
    assert abs(1900 - 1200) > ms.ELO_MATCH_CUTOFF

    out = ms.sweep_immediate_matches([db._tables['user_word_watchlist'][0]], db)

    assert out['no_match'] == 1
    row = db._tables['user_word_watchlist'][0]
    assert row['last_matched_test_id'] is None


# ---------------------------------------------------------------------------
# Re-affirming the SAME test_id — surfaced_at must be untouched
# ---------------------------------------------------------------------------


def test_reaffirming_same_test_id_leaves_surfaced_at_untouched():
    db = FakeDB()
    _seed_dim_test_types(db)
    db.seed('tests', [
        {'id': 'test-a', 'vocab_sense_ids': [500], 'is_active': True, 'language_id': LANG_EN},
    ])
    db.seed('test_skill_ratings', [
        {'test_id': 'test-a', 'test_type_id': LISTENING, 'elo_rating': 1210},
    ])
    db.seed('user_skill_ratings', [
        {'user_id': USER, 'language_id': LANG_EN, 'test_type_id': LISTENING, 'elo_rating': 1200},
    ])
    db.seed('user_word_watchlist', [
        _watchlist_row(
            last_matched_test_id='test-a',
            last_matched_surfaced_at='2026-01-01T00:00:00+00:00',
            last_matched_at='2025-12-31T00:00:00+00:00',
        ),
    ])

    out = ms.sweep_immediate_matches([db._tables['user_word_watchlist'][0]], db)

    assert out['reaffirmed'] == 1
    assert out['matched'] == 0
    row = db._tables['user_word_watchlist'][0]
    assert row['last_matched_test_id'] == 'test-a'
    # NOT reset — the write contract only resets surfaced_at on a NEW test_id.
    assert row['last_matched_surfaced_at'] == '2026-01-01T00:00:00+00:00'
    # last_matched_at IS still refreshed on a re-affirmation (it's a plain
    # "when did the sweep last confirm this" timestamp, unlike surfaced_at).
    assert row['last_matched_at'] != '2025-12-31T00:00:00+00:00'

    result = out['results'][0]
    assert result['changed'] is False
    assert result['matched_test_id'] == 'test-a'


# ---------------------------------------------------------------------------
# A DIFFERENT new match replaces an old one — surfaced_at IS reset
# ---------------------------------------------------------------------------


def test_new_match_replacing_old_one_resets_surfaced_at():
    db = FakeDB()
    _seed_dim_test_types(db)
    db.seed('tests', [
        # Only test-b overlaps the sense now; test-a (the old match) no
        # longer shows up as a candidate at all (e.g. deactivated since).
        {'id': 'test-b', 'vocab_sense_ids': [500], 'is_active': True, 'language_id': LANG_EN},
    ])
    db.seed('test_skill_ratings', [
        {'test_id': 'test-b', 'test_type_id': LISTENING, 'elo_rating': 1250},
    ])
    db.seed('user_skill_ratings', [
        {'user_id': USER, 'language_id': LANG_EN, 'test_type_id': LISTENING, 'elo_rating': 1200},
    ])
    db.seed('user_word_watchlist', [
        _watchlist_row(
            last_matched_test_id='test-a',
            last_matched_surfaced_at='2026-01-01T00:00:00+00:00',
        ),
    ])

    out = ms.sweep_immediate_matches([db._tables['user_word_watchlist'][0]], db)

    assert out['matched'] == 1
    assert out['reaffirmed'] == 0
    row = db._tables['user_word_watchlist'][0]
    assert row['last_matched_test_id'] == 'test-b'
    assert row['last_matched_surfaced_at'] is None

    result = out['results'][0]
    assert result['changed'] is True
    assert result['matched_test_id'] == 'test-b'


# ---------------------------------------------------------------------------
# Multiple candidates — the ELO-closest one wins, not just any overlap
# ---------------------------------------------------------------------------


def test_multiple_candidates_picks_elo_closest_not_first_or_last():
    db = FakeDB()
    _seed_dim_test_types(db)
    db.seed('tests', [
        {'id': 'test-far', 'vocab_sense_ids': [500], 'is_active': True, 'language_id': LANG_EN},
        {'id': 'test-closest', 'vocab_sense_ids': [500], 'is_active': True, 'language_id': LANG_EN},
        {'id': 'test-mid', 'vocab_sense_ids': [500], 'is_active': True, 'language_id': LANG_EN},
    ])
    db.seed('test_skill_ratings', [
        {'test_id': 'test-far', 'test_type_id': LISTENING, 'elo_rating': 1450},   # diff 250
        {'test_id': 'test-mid', 'test_type_id': LISTENING, 'elo_rating': 1280},   # diff 80
        {'test_id': 'test-closest', 'test_type_id': LISTENING, 'elo_rating': 1205},  # diff 5
    ])
    db.seed('user_skill_ratings', [
        {'user_id': USER, 'language_id': LANG_EN, 'test_type_id': LISTENING, 'elo_rating': 1200},
    ])
    db.seed('user_word_watchlist', [_watchlist_row()])

    out = ms.sweep_immediate_matches([db._tables['user_word_watchlist'][0]], db)

    row = db._tables['user_word_watchlist'][0]
    assert row['last_matched_test_id'] == 'test-closest'
    assert out['results'][0]['elo_diff'] == 5


def test_multiple_candidates_uses_each_tests_best_active_skill_row():
    """A candidate test with several test_skill_ratings rows (multiple
    test_type_id skills) is scored by its BEST (closest) active skill, not
    an arbitrary/first one — mirrors the word_upload slot block letting any
    qualifying skill row win."""
    db = FakeDB()
    _seed_dim_test_types(db)
    db.seed('tests', [
        {'id': 'test-multi', 'vocab_sense_ids': [500], 'is_active': True, 'language_id': LANG_EN},
        {'id': 'test-single', 'vocab_sense_ids': [500], 'is_active': True, 'language_id': LANG_EN},
    ])
    db.seed('test_skill_ratings', [
        # test-multi's reading rating is far away, but its listening rating
        # is the closest of everything in this fixture.
        {'test_id': 'test-multi', 'test_type_id': READING, 'elo_rating': 1900},
        {'test_id': 'test-multi', 'test_type_id': LISTENING, 'elo_rating': 1202},
        {'test_id': 'test-single', 'test_type_id': LISTENING, 'elo_rating': 1240},
    ])
    db.seed('user_skill_ratings', [
        {'user_id': USER, 'language_id': LANG_EN, 'test_type_id': LISTENING, 'elo_rating': 1200},
        {'user_id': USER, 'language_id': LANG_EN, 'test_type_id': READING, 'elo_rating': 1200},
    ])
    db.seed('user_word_watchlist', [_watchlist_row()])

    out = ms.sweep_immediate_matches([db._tables['user_word_watchlist'][0]], db)

    row = db._tables['user_word_watchlist'][0]
    assert row['last_matched_test_id'] == 'test-multi'
    assert out['results'][0]['elo_diff'] == 2


# ---------------------------------------------------------------------------
# Unrated user skill defaults to 1200
# ---------------------------------------------------------------------------


def test_unrated_user_skill_defaults_to_1200():
    db = FakeDB()
    _seed_dim_test_types(db)
    db.seed('tests', [
        {'id': 'test-a', 'vocab_sense_ids': [500], 'is_active': True, 'language_id': LANG_EN},
    ])
    db.seed('test_skill_ratings', [
        {'test_id': 'test-a', 'test_type_id': LISTENING, 'elo_rating': 1220},
    ])
    # No user_skill_ratings row at all for this user/type -> defaults to 1200.
    db.seed('user_word_watchlist', [_watchlist_row()])

    out = ms.sweep_immediate_matches([db._tables['user_word_watchlist'][0]], db)

    assert out['results'][0]['elo_diff'] == 20
    row = db._tables['user_word_watchlist'][0]
    assert row['last_matched_test_id'] == 'test-a'


# ---------------------------------------------------------------------------
# Multiple watchlist rows processed independently in one call
# ---------------------------------------------------------------------------


def test_multiple_watchlist_rows_processed_independently():
    db = FakeDB()
    _seed_dim_test_types(db)
    db.seed('tests', [
        {'id': 'test-a', 'vocab_sense_ids': [500], 'is_active': True, 'language_id': LANG_EN},
        {'id': 'test-b', 'vocab_sense_ids': [777], 'is_active': True, 'language_id': LANG_EN},
    ])
    db.seed('test_skill_ratings', [
        {'test_id': 'test-a', 'test_type_id': LISTENING, 'elo_rating': 1200},
        {'test_id': 'test-b', 'test_type_id': LISTENING, 'elo_rating': 1200},
    ])
    db.seed('user_word_watchlist', [
        _watchlist_row(id=1, sense_id=500),
        _watchlist_row(id=2, sense_id=999),  # no test overlaps this sense
        _watchlist_row(id=3, sense_id=777, user_id='user-2'),
    ])

    rows = db._tables['user_word_watchlist']
    out = ms.sweep_immediate_matches(rows, db)

    assert out['matched'] == 2
    assert out['no_match'] == 1
    assert len(out['results']) == 3

    by_id = {r['id']: r for r in db._tables['user_word_watchlist']}
    assert by_id[1]['last_matched_test_id'] == 'test-a'
    assert by_id[2]['last_matched_test_id'] is None
    assert by_id[3]['last_matched_test_id'] == 'test-b'


def test_sweep_is_not_upload_specific_missing_created_at_is_fine():
    """Step 5's recurring cron will call this against arbitrary active
    watchlist rows with no `created_at` assumption baked in — a row lacking
    that key entirely must not break the sweep."""
    db = FakeDB()
    _seed_dim_test_types(db)
    db.seed('tests', [
        {'id': 'test-a', 'vocab_sense_ids': [500], 'is_active': True, 'language_id': LANG_EN},
    ])
    db.seed('test_skill_ratings', [
        {'test_id': 'test-a', 'test_type_id': LISTENING, 'elo_rating': 1200},
    ])
    row = _watchlist_row()
    assert 'created_at' not in row

    out = ms.sweep_immediate_matches([row], db)

    assert out['matched'] == 1
