"""Latency fixes, 2026-11-11 ([[evaluations/latency-2026-11-11]]).

Covers the per-request cache (services.request_cache), the cached plan row
(services.day_boundary.plan_row), the memoised new-word state, the cached
dim_test_types p50 map, and static-asset versioning / caching / compression.
No live DB: every database is a counting fake.
"""

from __future__ import annotations

import gzip

import pytest
from flask import Flask

from services import request_cache
from services.day_boundary import plan_row, plan_timezone, plan_today_iso


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, data):
        self.data = data


class CountingDb:
    """Records every executed query as (table, select_arg)."""

    def __init__(self, rows=None, fail=False):
        self.rows = rows if rows is not None else {}
        self.fail = fail
        self.queries = []

    def table(self, name):
        db = self

        class Q:
            _sel = None

            def select(self, *a, **_k):
                self._sel = a[0] if a else None
                return self

            def eq(self, *_a, **_k):
                return self

            def limit(self, *_a, **_k):
                return self

            def execute(self):
                db.queries.append((name, self._sel))
                if db.fail:
                    raise RuntimeError('db down')
                return _Resp(list(db.rows.get(name, [])))

        return Q()

    def count(self, table):
        return sum(1 for t, _ in self.queries if t == table)


PLAN = {'user_id': 'u1', 'language_id': 3, 'timezone': 'Asia/Tokyo',
        'excluded_modules': ['flashcards'], 'daily_minutes': 30, 'prestudy_mode': 'ask'}


@pytest.fixture
def flask_app():
    return Flask(__name__)


# ---------------------------------------------------------------------------
# request_cache
# ---------------------------------------------------------------------------

class TestRequestCache:
    def test_get_request_computes_once(self, flask_app):
        calls = []
        with flask_app.test_request_context('/', method='GET'):
            for _ in range(3):
                assert request_cache.memo(('k',), lambda: calls.append(1) or 'v') == 'v'
        assert len(calls) == 1

    def test_post_request_never_caches(self, flask_app):
        calls = []
        with flask_app.test_request_context('/', method='POST'):
            for _ in range(3):
                request_cache.memo(('k',), lambda: calls.append(1) or 'v')
        assert len(calls) == 3

    def test_outside_a_request_never_caches(self):
        calls = []
        for _ in range(2):
            request_cache.memo(('k',), lambda: calls.append(1) or 'v')
        assert len(calls) == 2

    def test_cache_dies_with_the_request(self, flask_app):
        calls = []
        for _ in range(2):
            with flask_app.test_request_context('/', method='GET'):
                request_cache.memo(('k',), lambda: calls.append(1) or 'v')
        assert len(calls) == 2

    def test_exceptions_are_not_cached(self, flask_app):
        calls = []

        def boom():
            calls.append(1)
            raise RuntimeError('x')

        with flask_app.test_request_context('/', method='GET'):
            for _ in range(2):
                with pytest.raises(RuntimeError):
                    request_cache.memo(('k',), boom)
        assert len(calls) == 2

    def test_cache_none_false_retries_a_none(self, flask_app):
        calls = []
        with flask_app.test_request_context('/', method='GET'):
            for _ in range(2):
                request_cache.memo(('k',), lambda: calls.append(1), cache_none=False)
        assert len(calls) == 2

    def test_invalidate_by_prefix(self, flask_app):
        calls = []
        with flask_app.test_request_context('/', method='GET'):
            request_cache.memo(('a', 'u1', '3'), lambda: calls.append('a1'))
            request_cache.memo(('a', 'u2', '3'), lambda: calls.append('a2'))
            request_cache.memo(('b', 'u1'), lambda: calls.append('b'))
            request_cache.invalidate('a', 'u1')
            request_cache.memo(('a', 'u1', '3'), lambda: calls.append('a1'))
            request_cache.memo(('a', 'u2', '3'), lambda: calls.append('a2'))
            request_cache.memo(('b', 'u1'), lambda: calls.append('b'))
        assert calls == ['a1', 'a2', 'b', 'a1']


# ---------------------------------------------------------------------------
# plan_row
# ---------------------------------------------------------------------------

class TestPlanRow:
    def test_one_query_for_every_plan_read_in_a_get(self, flask_app):
        db = CountingDb({'user_study_plans': [PLAN]})
        with flask_app.test_request_context('/', method='GET'):
            assert plan_timezone(db, 'u1', 3) == 'Asia/Tokyo'
            plan_today_iso(db, 'u1', 3)
            assert plan_row(db, 'u1', 3)['daily_minutes'] == 30
            from services.prestudy import get_prestudy_mode
            assert get_prestudy_mode(db, 'u1', 3) == 'ask'
        assert db.count('user_study_plans') == 1
        assert db.queries[0] == ('user_study_plans', '*')

    def test_keyed_by_user_and_language(self, flask_app):
        db = CountingDb({'user_study_plans': [PLAN]})
        with flask_app.test_request_context('/', method='GET'):
            plan_row(db, 'u1', 3)
            plan_row(db, 'u1', 1)
            plan_row(db, 'u2', 3)
        assert db.count('user_study_plans') == 3

    def test_callers_get_copies(self, flask_app):
        db = CountingDb({'user_study_plans': [PLAN]})
        with flask_app.test_request_context('/', method='GET'):
            plan_row(db, 'u1', 3)['timezone'] = 'mutated'
            assert plan_row(db, 'u1', 3)['timezone'] == 'Asia/Tokyo'

    def test_missing_row_is_cached_as_none(self, flask_app):
        db = CountingDb({'user_study_plans': []})
        with flask_app.test_request_context('/', method='GET'):
            assert plan_row(db, 'u1', 3) is None
            assert plan_timezone(db, 'u1', 3) == 'UTC'
        assert db.count('user_study_plans') == 1

    def test_a_failure_falls_back_and_is_retried(self, flask_app):
        db = CountingDb(fail=True)
        with flask_app.test_request_context('/', method='GET'):
            assert plan_timezone(db, 'u1', 3) == 'UTC'
            assert plan_timezone(db, 'u1', 3) == 'UTC'
        assert db.count('user_study_plans') == 2

    def test_writes_are_never_served_from_cache(self, flask_app):
        db = CountingDb({'user_study_plans': [PLAN]})
        with flask_app.test_request_context('/', method='PUT'):
            plan_row(db, 'u1', 3)
            plan_row(db, 'u1', 3)
        assert db.count('user_study_plans') == 2


# ---------------------------------------------------------------------------
# new_word_state memo
# ---------------------------------------------------------------------------

class TestNewWordStateMemo:
    def _service(self, monkeypatch):
        from services.practice_session_service import PracticeSessionService
        svc = PracticeSessionService.__new__(PracticeSessionService)
        svc.db = CountingDb()
        calls = []

        def fake_state(user_id, language_id):
            calls.append((user_id, language_id))
            return {'effective': 5, 'unstarted': len(calls), 'started_today': 0}

        monkeypatch.setattr(svc, '_new_word_state', fake_state)
        return svc, calls

    def test_computed_once_per_get(self, flask_app, monkeypatch):
        svc, calls = self._service(monkeypatch)
        with flask_app.test_request_context('/', method='GET'):
            a = svc.new_word_state('u1', 3)
            b = svc.new_word_state('u1', 3)
        assert len(calls) == 1 and a == b

    def test_a_ladder_insert_forces_a_recount(self, flask_app, monkeypatch):
        svc, calls = self._service(monkeypatch)
        monkeypatch.setattr('services.intro_drill.ENABLED', False)
        with flask_app.test_request_context('/', method='GET'):
            assert svc.new_word_state('u1', 3)['unstarted'] == 1
            svc._insert_ladder_rows('u1', [101], 3)
            assert svc.new_word_state('u1', 3)['unstarted'] == 2
        assert len(calls) == 2


# ---------------------------------------------------------------------------
# dim_test_types p50 map
# ---------------------------------------------------------------------------

class TestObservedP50:
    ROWS = [{'type_code': 'reading', 'expected_minutes_p50': 7.5},
            {'type_code': 'listening', 'expected_minutes_p50': None}]

    def test_one_query_for_every_skill(self):
        from services.study_plan_service import _test_time_estimate
        db = CountingDb({'dim_test_types': self.ROWS})
        assert _test_time_estimate('reading', db) == 7.5
        _test_time_estimate('listening', db)   # NULL p50 -> seeded minutes
        _test_time_estimate('dictation', db)   # no row -> seeded minutes
        assert db.count('dim_test_types') == 1

    def test_expires_after_ttl(self, monkeypatch):
        import services.study_plan_service as sps
        db = CountingDb({'dim_test_types': self.ROWS})
        sps._test_time_estimate('reading', db)
        now = sps._time.monotonic()
        monkeypatch.setattr(sps._time, 'monotonic', lambda: now + sps._P50_TTL_SECONDS + 1)
        sps._test_time_estimate('reading', db)
        assert db.count('dim_test_types') == 2

    def test_failure_is_not_cached(self):
        from services.study_plan_service import _test_time_estimate
        from config import Config
        db = CountingDb(fail=True)
        assert _test_time_estimate('reading', db) == float(Config.TEST_TYPE_MINUTES['reading'])
        _test_time_estimate('reading', db)
        assert db.count('dim_test_types') == 2

    def test_cache_is_per_client(self):
        from services.study_plan_service import _test_time_estimate
        a = CountingDb({'dim_test_types': self.ROWS})
        b = CountingDb({'dim_test_types': [{'type_code': 'reading', 'expected_minutes_p50': 3}]})
        assert _test_time_estimate('reading', a) == 7.5
        assert _test_time_estimate('reading', b) == 3.0


# ---------------------------------------------------------------------------
# Static assets
# ---------------------------------------------------------------------------

@pytest.fixture
def static_app(tmp_path):
    from flask import render_template_string, url_for
    from services.static_assets import ONE_YEAR, init_static_assets
    (tmp_path / 'app.css').write_text('body{color:red}' * 200)
    (tmp_path / 'i18n').mkdir()
    (tmp_path / 'i18n' / 'en.json').write_text('{"a": "b"}')
    app = Flask(__name__, static_folder=str(tmp_path), static_url_path='/static')
    init_static_assets(app)

    @app.route('/page')
    def page():
        return render_template_string(
            "{{ url_for('static', filename='app.css') }}|{{ i18n_versions|tojson }}")

    app.ONE_YEAR = ONE_YEAR
    return app


class TestStaticAssets:
    def test_static_urls_carry_a_content_hash(self, static_app, tmp_path):
        body = static_app.test_client().get('/page').get_data(as_text=True)
        url, versions = body.split('|')
        assert url.startswith('/static/app.css?v=') and len(url.split('v=')[1]) == 10
        assert '"en": "' in versions or '"en":"' in versions

    def test_hash_changes_with_the_file(self, static_app, tmp_path):
        from flask import url_for
        with static_app.test_request_context():
            before = url_for('static', filename='app.css')
        (tmp_path / 'app.css').write_text('body{color:blue}')
        with static_app.test_request_context():
            after = url_for('static', filename='app.css')
        assert before != after

    def test_versioned_requests_are_cached_for_a_year(self, static_app):
        c = static_app.test_client()
        r = c.get('/static/app.css?v=abc')
        assert f'max-age={static_app.ONE_YEAR}' in r.headers['Cache-Control']
        r2 = c.get('/static/app.css')
        assert f'max-age={static_app.ONE_YEAR}' not in (r2.headers.get('Cache-Control') or '')

    def test_static_files_are_compressed(self, static_app):
        # Static files are streamed; Flask-Compress streams br/zstd/deflate.
        import brotli
        r = static_app.test_client().get(
            '/static/app.css?v=x', headers={'Accept-Encoding': 'gzip, deflate, br'})
        assert r.headers.get('Content-Encoding') == 'br'
        assert brotli.decompress(r.get_data()).decode().startswith('body{color:red}')

    def test_pages_are_gzipped(self, static_app):
        @static_app.route('/big')
        def big():
            return '<p>hello</p>' * 500

        r = static_app.test_client().get('/big', headers={'Accept-Encoding': 'gzip'})
        assert r.headers.get('Content-Encoding') == 'gzip'
        assert gzip.decompress(r.data).decode().startswith('<p>hello</p>')

    def test_vendor_files_are_immutable_without_v(self, static_app, tmp_path):
        # static/vendor/<lib>-<version>/ is versioned by directory, so the
        # fonts a vendored CSS file references (no ?v=) are cached too.
        (tmp_path / 'vendor' / 'lib-1.0' / 'fonts').mkdir(parents=True)
        (tmp_path / 'vendor' / 'lib-1.0' / 'fonts' / 'x.woff2').write_bytes(b'\x00' * 2000)
        r = static_app.test_client().get('/static/vendor/lib-1.0/fonts/x.woff2')
        assert f'max-age={static_app.ONE_YEAR}' in r.headers['Cache-Control']

    def test_paths_outside_static_are_not_hashed(self, static_app):
        from services.static_assets import file_version
        assert file_version(static_app, '../etc/passwd') is None
        assert file_version(static_app, 'missing.css') is None
