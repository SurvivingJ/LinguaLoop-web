"""Unit tests for services/word_list_import/sweep_cron.py.

Step 5 of wiki/tasklist/word-list-import.plan.md ("Word List Upload -> Ladder
Exposure + Matched Test Queueing") — the recurring watchlist match-sweep cron.
`run_watchlist_sweep` must:

  * acquire a cross-worker advisory lock before doing any work, and skip
    cleanly (no queries, no writes) if another worker already holds it —
    matching services.study_plan_service._try_advisory_lock's exact skip
    semantics (including its "RPC errored -> fall through to True" shape);
  * read/advance a single-row `word_upload_sweep_state.last_swept_created_at`
    watermark so a `tests` row is scanned by the sweep at most once;
  * narrow to only the `user_word_watchlist` rows whose `sense_id` could
    possibly match one of the newly-created tests, then delegate the actual
    ELO-aware matching to the already-tested `sweep_immediate_matches`.

No real database, no network: a minimal in-memory fake stands in for the
Supabase query-builder + `.rpc(...)` surface, extended from
tests/test_match_sweep.py's fixture shape with `.gt(...)` (the
`tests.created_at` watermark filter) and a queueable `.rpc(...)`.
"""

import services.word_list_import.sweep_cron as sc

# ---------------------------------------------------------------------------
# Fakes — minimal in-memory stand-in for the Supabase query-builder + rpc()
# surface
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
        self._order = None
        self._range = None

    # -- filter builders (all return self) ------------------------------
    def select(self, *_a, **_kw):
        return self

    def eq(self, col, val):
        self._filters.append(('eq', col, val))
        return self

    def gt(self, col, val):
        self._filters.append(('gt', col, val))
        return self

    def in_(self, col, vals):
        self._filters.append(('in', col, set(vals)))
        return self

    def overlaps(self, col, vals):
        self._filters.append(('overlaps', col, set(vals)))
        return self

    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def range(self, start, end):
        self._range = (start, end)
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
            elif kind == 'gt':
                if row_val is None or not (row_val > val):
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
        if self._order:
            col, desc = self._order
            matched = sorted(matched, key=lambda r: r.get(col), reverse=desc)
        if self._range:
            start, end = self._range
            matched = matched[start:end + 1]
        if self._op:
            kind, payload = self._op
            if kind == 'update':
                for r in matched:
                    r.update(payload)
                return _Resp(matched)
        return _Resp(matched)


class _RpcCall:
    def __init__(self, resp=None, raise_exc=None):
        self._resp = resp
        self._raise_exc = raise_exc

    def execute(self):
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._resp


class FakeDB:
    """Minimal in-memory stand-in for the Supabase client surface used by
    sweep_cron's tests/user_word_watchlist/word_upload_sweep_state queries
    plus the two advisory-lock RPCs."""

    def __init__(self):
        self._tables: dict = {}
        self._rpc_queue: dict = {}
        self.rpc_calls: list = []  # (name, params) — for call-count assertions

    def seed(self, table, rows):
        self._tables[table] = [dict(r) for r in rows]

    def table(self, name):
        rows = self._tables.setdefault(name, [])
        return _FakeQuery(rows)

    def queue_rpc(self, name, *behaviors):
        """Each behavior is ('value', data) or ('raise', exc). Consumed
        front-to-back, one per call to rpc(name, ...); once exhausted,
        rpc() defaults to ('value', True) — a harmless default for the
        unlock call, which no test asserts on directly."""
        self._rpc_queue.setdefault(name, []).extend(behaviors)

    def rpc(self, name, params=None):
        self.rpc_calls.append((name, params))
        queue = self._rpc_queue.get(name)
        if queue:
            kind, payload = queue.pop(0)
            if kind == 'raise':
                return _RpcCall(raise_exc=payload)
            return _RpcCall(resp=_Resp(payload))
        return _RpcCall(resp=_Resp(True))


LANG_EN = 2
USER = 'user-1'
LISTENING = 10


def _seed_dim_test_types(db):
    db.seed('dim_test_types', [{'id': LISTENING, 'is_active': True}])


def _seed_cursor(db, value):
    db.seed('word_upload_sweep_state', [
        {'id': 1, 'last_swept_created_at': value},
    ])


# ---------------------------------------------------------------------------
# Normal sweep: advances the cursor and finds a match via
# sweep_immediate_matches
# ---------------------------------------------------------------------------


def test_normal_sweep_advances_cursor_and_finds_match():
    db = FakeDB()
    _seed_dim_test_types(db)
    _seed_cursor(db, '2026-01-01T00:00:00+00:00')
    db.seed('tests', [
        {
            'id': 'test-new', 'created_at': '2026-01-05T00:00:00+00:00',
            'vocab_sense_ids': [500], 'is_active': True, 'language_id': LANG_EN,
        },
    ])
    db.seed('test_skill_ratings', [
        {'test_id': 'test-new', 'test_type_id': LISTENING, 'elo_rating': 1210},
    ])
    db.seed('user_skill_ratings', [
        {'user_id': USER, 'language_id': LANG_EN, 'test_type_id': LISTENING, 'elo_rating': 1200},
    ])
    db.seed('user_word_watchlist', [
        {'id': 1, 'user_id': USER, 'sense_id': 500, 'language_id': LANG_EN,
         'last_matched_test_id': None, 'active': True},
    ])

    result = sc.run_watchlist_sweep(db)

    assert result['skipped'] is False
    assert result['no_new_tests'] is False
    assert result['sweep']['matched'] == 1

    watchlist_row = db._tables['user_word_watchlist'][0]
    assert watchlist_row['last_matched_test_id'] == 'test-new'

    cursor_row = db._tables['word_upload_sweep_state'][0]
    assert cursor_row['last_swept_created_at'] == '2026-01-05T00:00:00+00:00'


# ---------------------------------------------------------------------------
# Lock not acquired -> short-circuit, nothing touched
# ---------------------------------------------------------------------------


def test_lock_not_acquired_skips_without_touching_anything():
    db = FakeDB()
    _seed_cursor(db, '2026-01-01T00:00:00+00:00')
    db.seed('tests', [
        {'id': 'test-new', 'created_at': '2026-01-05T00:00:00+00:00',
         'vocab_sense_ids': [500], 'is_active': True, 'language_id': LANG_EN},
    ])
    db.seed('user_word_watchlist', [
        {'id': 1, 'user_id': USER, 'sense_id': 500, 'language_id': LANG_EN,
         'last_matched_test_id': None, 'active': True},
    ])
    db.queue_rpc(sc._LOCK_RPC, ('value', False))

    result = sc.run_watchlist_sweep(db)

    assert result == {'skipped': True, 'reason': 'lock_held'}
    # Cursor untouched.
    assert db._tables['word_upload_sweep_state'][0]['last_swept_created_at'] == \
        '2026-01-01T00:00:00+00:00'
    # Watchlist row untouched.
    assert db._tables['user_word_watchlist'][0]['last_matched_test_id'] is None
    # The unlock RPC must not fire for a lock we never took.
    unlock_calls = [c for c in db.rpc_calls if c[0] == sc._UNLOCK_RPC]
    assert unlock_calls == []


# ---------------------------------------------------------------------------
# Lock-acquire RPC errors -> falls through to True (study_plan_service shape)
# ---------------------------------------------------------------------------


def test_lock_rpc_error_falls_through_to_true_and_sweep_still_runs():
    db = FakeDB()
    _seed_dim_test_types(db)
    _seed_cursor(db, '2026-01-01T00:00:00+00:00')
    db.seed('tests', [
        {'id': 'test-new', 'created_at': '2026-01-05T00:00:00+00:00',
         'vocab_sense_ids': [500], 'is_active': True, 'language_id': LANG_EN},
    ])
    db.seed('test_skill_ratings', [
        {'test_id': 'test-new', 'test_type_id': LISTENING, 'elo_rating': 1200},
    ])
    db.seed('user_word_watchlist', [
        {'id': 1, 'user_id': USER, 'sense_id': 500, 'language_id': LANG_EN,
         'last_matched_test_id': None, 'active': True},
    ])
    db.queue_rpc(sc._LOCK_RPC, ('raise', RuntimeError('RPC not deployed')))

    result = sc.run_watchlist_sweep(db)

    assert result['skipped'] is False
    assert result['sweep']['matched'] == 1
    watchlist_row = db._tables['user_word_watchlist'][0]
    assert watchlist_row['last_matched_test_id'] == 'test-new'


def test_lock_acquired_releases_lock_via_unlock_rpc():
    """A normal successful run must release the lock in a finally."""
    db = FakeDB()
    _seed_dim_test_types(db)
    _seed_cursor(db, '2026-01-01T00:00:00+00:00')
    db.seed('tests', [])

    sc.run_watchlist_sweep(db)

    unlock_calls = [c for c in db.rpc_calls if c[0] == sc._UNLOCK_RPC]
    assert len(unlock_calls) == 1


# ---------------------------------------------------------------------------
# Empty result: no new tests since cursor is a cheap no-op, not an error
# ---------------------------------------------------------------------------


def test_no_new_tests_is_a_cheap_no_op():
    db = FakeDB()
    _seed_cursor(db, '2026-01-05T00:00:00+00:00')
    db.seed('tests', [
        {'id': 'test-old', 'created_at': '2026-01-01T00:00:00+00:00',
         'vocab_sense_ids': [500], 'is_active': True, 'language_id': LANG_EN},
    ])

    # If the sweep ever queries user_word_watchlist when there are no new
    # tests, that is the "not cheap" behavior this test forbids — make any
    # such query blow up so the assertion is enforced by construction, not
    # just by an after-the-fact row-count check.
    class _ExplodingQuery(_FakeQuery):
        def execute(self):
            raise AssertionError(
                'user_word_watchlist must not be queried when there are no '
                'new tests since the cursor',
            )

    class _ExplodingDB(FakeDB):
        def table(self, name):
            if name == 'user_word_watchlist':
                return _ExplodingQuery(self._tables.setdefault(name, []))
            return super().table(name)

    exploding_db = _ExplodingDB()
    exploding_db._tables = db._tables
    exploding_db._rpc_queue = db._rpc_queue

    result = sc.run_watchlist_sweep(exploding_db)

    assert result['skipped'] is False
    assert result['no_new_tests'] is True
    assert result['sweep'] is None
    # Cursor must not move — nothing new was actually observed.
    assert exploding_db._tables['word_upload_sweep_state'][0]['last_swept_created_at'] == \
        '2026-01-05T00:00:00+00:00'


# ---------------------------------------------------------------------------
# Cursor exclusion: a pre-cursor test alongside a post-cursor test
# ---------------------------------------------------------------------------


def test_cursor_excludes_pre_cursor_test_alongside_post_cursor_test():
    db = FakeDB()
    _seed_dim_test_types(db)
    _seed_cursor(db, '2026-01-05T00:00:00+00:00')
    db.seed('tests', [
        # Pre-cursor: created_at is NOT strictly after the cursor -> excluded.
        {'id': 'test-old', 'created_at': '2026-01-05T00:00:00+00:00',
         'vocab_sense_ids': [999], 'is_active': True, 'language_id': LANG_EN},
        # Post-cursor: strictly after -> included.
        {'id': 'test-new', 'created_at': '2026-01-10T00:00:00+00:00',
         'vocab_sense_ids': [500], 'is_active': True, 'language_id': LANG_EN},
    ])
    db.seed('test_skill_ratings', [
        {'test_id': 'test-old', 'test_type_id': LISTENING, 'elo_rating': 1200},
        {'test_id': 'test-new', 'test_type_id': LISTENING, 'elo_rating': 1200},
    ])
    db.seed('user_word_watchlist', [
        # Watches the PRE-cursor test's sense only. If the sweep incorrectly
        # included test-old as a candidate, this row would get matched.
        {'id': 1, 'user_id': USER, 'sense_id': 999, 'language_id': LANG_EN,
         'last_matched_test_id': None, 'active': True},
        # Watches the POST-cursor test's sense — must get matched.
        {'id': 2, 'user_id': USER, 'sense_id': 500, 'language_id': LANG_EN,
         'last_matched_test_id': None, 'active': True},
    ])

    result = sc.run_watchlist_sweep(db)

    assert result['new_tests_found'] == 1  # only test-new
    by_id = {r['id']: r for r in db._tables['user_word_watchlist']}
    assert by_id[1]['last_matched_test_id'] is None  # test-old never considered
    assert by_id[2]['last_matched_test_id'] == 'test-new'

    cursor_row = db._tables['word_upload_sweep_state'][0]
    assert cursor_row['last_swept_created_at'] == '2026-01-10T00:00:00+00:00'


# ---------------------------------------------------------------------------
# Concurrent invocation: second call must skip, not double-process
# ---------------------------------------------------------------------------


def test_second_concurrent_invocation_skips_instead_of_double_processing():
    db = FakeDB()
    _seed_dim_test_types(db)
    _seed_cursor(db, '2026-01-01T00:00:00+00:00')
    db.seed('tests', [
        {'id': 'test-new', 'created_at': '2026-01-05T00:00:00+00:00',
         'vocab_sense_ids': [500], 'is_active': True, 'language_id': LANG_EN},
    ])
    db.seed('test_skill_ratings', [
        {'test_id': 'test-new', 'test_type_id': LISTENING, 'elo_rating': 1200},
    ])
    db.seed('user_word_watchlist', [
        {'id': 1, 'user_id': USER, 'sense_id': 500, 'language_id': LANG_EN,
         'last_matched_test_id': None, 'active': True},
    ])
    # First invocation acquires the lock; a second, concurrent invocation
    # (mocked here as the SECOND call to the same lock RPC) finds it held.
    db.queue_rpc(sc._LOCK_RPC, ('value', True), ('value', False))

    first = sc.run_watchlist_sweep(db)
    second = sc.run_watchlist_sweep(db)

    assert first['skipped'] is False
    assert first['sweep']['matched'] == 1

    assert second == {'skipped': True, 'reason': 'lock_held'}
    # Only ONE match was ever recorded — the second call did not re-process
    # (or otherwise touch) anything.
    watchlist_row = db._tables['user_word_watchlist'][0]
    assert watchlist_row['last_matched_test_id'] == 'test-new'


# ---------------------------------------------------------------------------
# New tests exist but no active watchlist row cares -> cursor still advances
# ---------------------------------------------------------------------------


def test_new_tests_with_no_matching_watchlist_rows_still_advances_cursor():
    db = FakeDB()
    _seed_cursor(db, '2026-01-01T00:00:00+00:00')
    db.seed('tests', [
        {'id': 'test-new', 'created_at': '2026-01-05T00:00:00+00:00',
         'vocab_sense_ids': [12345], 'is_active': True, 'language_id': LANG_EN},
    ])
    db.seed('user_word_watchlist', [])

    result = sc.run_watchlist_sweep(db)

    assert result['skipped'] is False
    assert result['no_new_tests'] is False
    assert result['sweep'] is None
    cursor_row = db._tables['word_upload_sweep_state'][0]
    assert cursor_row['last_swept_created_at'] == '2026-01-05T00:00:00+00:00'


# ---------------------------------------------------------------------------
# Inactive watchlist rows are never candidates, even if their sense matches
# ---------------------------------------------------------------------------


def test_inactive_watchlist_row_is_never_a_candidate():
    db = FakeDB()
    _seed_dim_test_types(db)
    _seed_cursor(db, '2026-01-01T00:00:00+00:00')
    db.seed('tests', [
        {'id': 'test-new', 'created_at': '2026-01-05T00:00:00+00:00',
         'vocab_sense_ids': [500], 'is_active': True, 'language_id': LANG_EN},
    ])
    db.seed('test_skill_ratings', [
        {'test_id': 'test-new', 'test_type_id': LISTENING, 'elo_rating': 1200},
    ])
    db.seed('user_word_watchlist', [
        {'id': 1, 'user_id': USER, 'sense_id': 500, 'language_id': LANG_EN,
         'last_matched_test_id': None, 'active': False},
    ])

    result = sc.run_watchlist_sweep(db)

    assert result['sweep'] is None
    watchlist_row = db._tables['user_word_watchlist'][0]
    assert watchlist_row['last_matched_test_id'] is None


# ---------------------------------------------------------------------------
# Chunked sense-id filter (URL-length safety) and row-cap paging
# ---------------------------------------------------------------------------


class _RecordingDB(FakeDB):
    """FakeDB that records every `.in_` call and page `.range` made against
    user_word_watchlist, and can fail the Nth watchlist query."""

    def __init__(self, fail_on_call=None):
        super().__init__()
        self.in_calls = []  # list of (col, list(vals))
        self.ranges = []
        self.fail_on_call = fail_on_call

    def table(self, name):
        q = super().table(name)
        if name != 'user_word_watchlist':
            return q
        outer = self
        orig_in, orig_range, orig_exec = q.in_, q.range, q.execute

        def in_(col, vals):
            outer.in_calls.append((col, list(vals)))
            return orig_in(col, vals)

        def range_(a, b):
            outer.ranges.append((a, b))
            return orig_range(a, b)

        def execute():
            if outer.fail_on_call == len(outer.in_calls):
                raise RuntimeError('boom')
            return orig_exec()

        q.in_, q.range, q.execute = in_, range_, execute
        return q


def _seed_big_batch(db, n_ids=4682):
    ids = list(range(1, n_ids + 1))
    db.seed('tests', [
        {'id': 't1', 'created_at': '2026-01-05T00:00:00+00:00',
         'vocab_sense_ids': ids[:3000], 'is_active': True,
         'language_id': LANG_EN},
        {'id': 't2', 'created_at': '2026-01-06T00:00:00+00:00',
         'vocab_sense_ids': ids[2000:] + [5, 5], 'is_active': True,
         'language_id': LANG_EN},
    ])
    return ids


def test_sense_id_filter_is_chunked_and_matches_single_call_result():
    db = _RecordingDB()
    _seed_cursor(db, '2026-01-01T00:00:00+00:00')
    ids = _seed_big_batch(db)
    watch_ids = [1, 150, 2500, 4682]
    db.seed('user_word_watchlist', [
        {'id': f'w{s}', 'user_id': USER, 'sense_id': s, 'language_id': LANG_EN,
         'last_matched_test_id': None, 'active': True} for s in watch_ids
    ] + [
        {'id': 'w-off', 'user_id': USER, 'sense_id': 7, 'language_id': LANG_EN,
         'last_matched_test_id': None, 'active': False},
        {'id': 'w-other', 'user_id': USER, 'sense_id': 99999,
         'language_id': LANG_EN, 'last_matched_test_id': None, 'active': True},
    ])

    tests = sc._fetch_tests_since(db, '2026-01-01T00:00:00+00:00')
    rows = sc._fetch_active_watchlist_rows_for_senses(
        db, sc._extract_sense_ids(tests))

    assert len(db.in_calls) > 1
    assert all(len(v) <= sc._SENSE_ID_CHUNK for _c, v in db.in_calls)
    sent = [x for _c, v in db.in_calls for x in v]
    assert len(sent) == len(set(sent)) == len(ids)  # distinct, complete
    assert sorted(r['sense_id'] for r in rows) == watch_ids
    assert len({r['id'] for r in rows}) == len(rows)


def test_chunk_matching_more_than_page_size_is_paged():
    db = _RecordingDB()
    db.seed('user_word_watchlist', [
        {'id': f'w{i:05d}', 'user_id': f'u{i}', 'sense_id': 1,
         'language_id': LANG_EN, 'last_matched_test_id': None, 'active': True}
        for i in range(2300)
    ])
    rows = sc._fetch_active_watchlist_rows_for_senses(db, {1, 2, 3})
    assert len(rows) == 2300
    assert len({r['id'] for r in rows}) == 2300
    assert len(db.ranges) == 3


def test_failure_in_second_chunk_leaves_watermark_unchanged():
    db = _RecordingDB(fail_on_call=2)
    _seed_cursor(db, '2026-01-01T00:00:00+00:00')
    _seed_big_batch(db)
    db.seed('user_word_watchlist', [])

    try:
        sc.run_watchlist_sweep(db)
    except RuntimeError:
        pass
    else:
        raise AssertionError('expected the chunk failure to propagate')

    assert len(db.in_calls) == 2
    row = db._tables['word_upload_sweep_state'][0]
    assert row['last_swept_created_at'] == '2026-01-01T00:00:00+00:00'
