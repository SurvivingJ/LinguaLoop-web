# tests/conftest.py
"""Shared fixtures for the LinguaDojo test suite."""

import os

# ---------------------------------------------------------------------------
# Offline by construction. This runs before anything imports config.py.
#
# * config.py does not load .env (LINGUADOJO_SKIP_DOTENV), so a developer's
#   .env cannot put live credentials into the run.
# * Credentials already in the environment are taken out of it now, before
#   Config reads them, and kept only for tests marked ``live`` (run with
#   ``-m live``; see pytest_configure below).
# * ``_offline_supabase`` (autouse) keeps every other test away from a real
#   Supabase client: see its docstring.
# ---------------------------------------------------------------------------
os.environ['LINGUADOJO_SKIP_DOTENV'] = '1'
_CREDENTIAL_VARS = (
    'SUPABASE_URL', 'SUPABASE_KEY', 'SUPABASE_SERVICE_ROLE_KEY',
    'SUPABASE_ANON_KEY', 'SUPABASE_ACCESS_TOKEN', 'OPENROUTER_API_KEY',
)
# Config attribute -> value it has with no credential in the environment.
_CONFIG_CREDENTIALS = {
    'SUPABASE_URL': None,
    'SUPABASE_KEY': None,
    'SUPABASE_SERVICE_ROLE_KEY': None,
    'OPENROUTER_API_KEY': '',
}
_LIVE_CREDENTIALS = {name: os.environ.pop(name) for name in _CREDENTIAL_VARS if name in os.environ}

import pytest  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from config import Config  # noqa: E402
from services import supabase_factory as _supabase_factory  # noqa: E402

_REAL_SUPABASE_FACTORY = _supabase_factory.SupabaseFactory
_OFFLINE_MESSAGE = (
    "Supabase is not available in tests: this test is not marked `live`, so no "
    "client for a real project can be built. Supply a fake (monkeypatch "
    "services.supabase_factory.get_supabase_admin / get_supabase, or use the "
    "`app` fixture's mock_supabase), or pass explicit fake credentials to "
    "SupabaseFactory.initialize()."
)


def _live_selected(config) -> bool:
    """True when the -m expression selects tests marked ``live``."""
    markexpr = config.getoption('markexpr', '') or ''
    if not markexpr:
        return False
    from _pytest.mark.expression import Expression
    return Expression.compile(markexpr).evaluate(lambda name: name == 'live')


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'live: reads or writes the live Supabase project; skipped unless selected with -m live',
    )
    if _live_selected(config):
        # Deliberate live run: give the live tests their credentials back,
        # including those in .env that config.py was told not to load.
        from dotenv import dotenv_values
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for name, value in dotenv_values(os.path.join(root, '.env')).items():
            if value is not None:
                os.environ.setdefault(name, value)
        os.environ.update(_LIVE_CREDENTIALS)
        for name in _CONFIG_CREDENTIALS:
            if os.environ.get(name):
                setattr(Config, name, os.environ[name])


def pytest_collection_modifyitems(config, items):
    if _live_selected(config):
        return
    skip_live = pytest.mark.skip(
        reason='live test: needs the live Supabase project; run deliberately with -m live')
    for item in items:
        if item.get_closest_marker('live'):
            item.add_marker(skip_live, append=False)


@pytest.fixture(autouse=True)
def _offline_supabase(request, monkeypatch):
    """No test outside ``-m live`` can reach a real Supabase project.

    For each such test: no credential in the environment or on Config (a
    script's ``bootstrap()`` may have loaded .env at collection), the factory
    reset before and after, and the factory refusing to build clients from
    the environment or to hand out a client it does not have. Code under test
    that asks for one without the test supplying a fake gets a RuntimeError
    (which the never-raise loggers, e.g. ``log_judge_verdict``, swallow).
    Explicit credentials are still accepted, so tests of the factory itself
    can build clients for a fake URL.
    """
    if request.node.get_closest_marker('live'):
        yield
        return

    factory = _REAL_SUPABASE_FACTORY
    for name in _CREDENTIAL_VARS:
        monkeypatch.delenv(name, raising=False)
    for name, value in _CONFIG_CREDENTIALS.items():
        monkeypatch.setattr(Config, name, value)

    real_initialize = factory.__dict__['initialize'].__func__

    def initialize(cls, supabase_url=None, supabase_key=None, *args, **kwargs):
        if not supabase_url or not supabase_key:
            raise RuntimeError(_OFFLINE_MESSAGE)
        return real_initialize(cls, supabase_url, supabase_key, *args, **kwargs)

    def guarded(getter_name):
        real = factory.__dict__[getter_name].__func__

        def getter(cls):
            if not cls._initialized:
                raise RuntimeError(_OFFLINE_MESSAGE)
            return real(cls)
        return classmethod(getter)

    monkeypatch.setattr(factory, 'initialize', classmethod(initialize))
    for getter_name in ('get_anon_client', 'get_service_client', 'get_auth_client'):
        monkeypatch.setattr(factory, getter_name, guarded(getter_name))
    factory.reset()
    yield
    factory.reset()


@pytest.fixture(autouse=True)
def _entailment_backend_llm(monkeypatch):
    """Pin the entailment judge to its LLM backend for the whole suite.

    The production default is jev (TASK-835, 2026-09-27), which makes a real HTTP
    call: the older judge tests patch ``call_llm`` and would otherwise reach the
    network. ``tests/test_jev_entailment.py`` overrides this per test.
    """
    monkeypatch.setenv('ENTAILMENT_JUDGE_BACKEND', 'llm')


@pytest.fixture(autouse=True)
def _dt_single_call_off(monkeypatch):
    """Pin the two ADR-044 flags OFF for the whole suite.

    Their production default is ON (2026-11-14). The older Dual Translation tests
    exercise the v1/v2 flows and the pre-ADR-044 persistence through
    ``grade_submission`` / ``_persist_grade`` without naming a flow; with the
    single-call grader on they would be graded by it instead - and, with an
    OpenRouter key in the environment, make a real paid call.
    ``tests/test_dual_translation_single_call_grader.py`` turns each flag on per
    test and checks the production defaults in a fresh interpreter.
    """
    monkeypatch.setattr(Config, 'DT_SINGLE_CALL_GRADER', False)
    monkeypatch.setattr(Config, 'DT_GRADING_ASSET_COLUMNS', False)


@pytest.fixture(autouse=True)
def _exercise_content_store():
    """A fresh ADR-049 exercise-content store per test, backed by an empty InMemoryBackend.

    ``store.reset_state()`` drops the backend, the caches, the warn-once flags and
    the reader's fetch pool before and after every test, so nothing leaks between
    tests and nothing reaches the network. A test that needs content seeds files
    into ``store.backend()`` (``store.encode_sense_file``) or installs its own
    backend with ``store.set_backend(...)``; ``store.set_backend(None)`` brings
    back the Config-built backend (e.g. to test missing credentials).
    """
    from services.exercise_content import store
    from services.exercise_content.backends import InMemoryBackend

    store.reset_state()
    store.set_backend(InMemoryBackend())
    yield
    store.reset_state()


# ---------------------------------------------------------------------------
# Test configuration
# ---------------------------------------------------------------------------

class TestConfig(Config):
    """Test-specific overrides — disables external services."""
    TESTING = True
    DEBUG = False
    SECRET_KEY = 'test-secret-key'

    # Disable external services
    SUPABASE_URL = 'https://fake.supabase.co'
    SUPABASE_KEY = 'fake-anon-key'
    SUPABASE_SERVICE_ROLE_KEY = 'fake-service-role-key'
    OPENAI_API_KEY = None
    STRIPE_SECRET_KEY = None
    R2_ACCESS_KEY_ID = None


# ---------------------------------------------------------------------------
# Mock builders
# ---------------------------------------------------------------------------

def _make_mock_supabase():
    """Build a mock Supabase client with chainable query interface."""
    client = MagicMock()

    # Make the table() chain work:  client.table('x').select(...).eq(...).execute()
    chain = MagicMock()
    chain.execute.return_value = MagicMock(data=[], count=0)
    client.table.return_value = chain

    # rpc() chain
    rpc_chain = MagicMock()
    rpc_chain.execute.return_value = MagicMock(data={})
    client.rpc.return_value = rpc_chain

    # auth.get_user() for JWT validation
    mock_user = SimpleNamespace(
        id='test-user-id-123',
        email='test@example.com',
    )
    client.auth.get_user.return_value = SimpleNamespace(user=mock_user)

    return client


def _make_mock_dimension_service():
    """Patch DimensionService class methods to return canned data."""
    return {
        'get_all_languages': lambda: [
            {'id': 1, 'language_code': 'es', 'language_name': 'Spanish', 'native_name': 'Espa\u00f1ol'},
        ],
        'get_all_test_types': lambda: [
            {'id': 1, 'test_type_code': 'reading', 'test_type_name': 'Reading'},
        ],
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_supabase():
    """A reusable mock Supabase client."""
    return _make_mock_supabase()


@pytest.fixture()
def app(mock_supabase, monkeypatch):
    """Create a Flask test app with all external services mocked out.

    Every replacement goes through ``monkeypatch``, never ``patch()``: a test
    that monkeypatches one of these names again (e.g. get_supabase_admin) then
    shares one undo stack with this fixture, so teardown restores the real
    object. With ``patch()`` the test's monkeypatch outlived this fixture and
    put the MagicMock back for the rest of the session (H-01).
    """
    MockFactory = MagicMock(name='SupabaseFactory')
    MockDimSvc = MagicMock(name='DimensionService')
    MockDimSvcApp = MagicMock(name='app.DimensionService')
    monkeypatch.setattr('services.supabase_factory.SupabaseFactory', MockFactory)
    monkeypatch.setattr('services.supabase_factory.get_supabase',
                        MagicMock(name='get_supabase', return_value=mock_supabase))
    monkeypatch.setattr('services.supabase_factory.get_supabase_admin',
                        MagicMock(name='get_supabase_admin', return_value=mock_supabase))
    monkeypatch.setattr('services.dimension_service.DimensionService', MockDimSvc)
    monkeypatch.setattr('app.DimensionService', MockDimSvcApp)
    monkeypatch.setattr('app.ServiceFactory', MagicMock(name='ServiceFactory'))
    monkeypatch.setattr('app.R2Service', MagicMock(name='R2Service'))
    monkeypatch.setattr('app.AuthService', MagicMock(name='AuthService'))

    # SupabaseFactory stubs
    MockFactory.initialize = MagicMock()
    MockFactory.get_anon_client.return_value = mock_supabase
    MockFactory.get_service_client.return_value = mock_supabase

    # DimensionService stubs
    dim_data = _make_mock_dimension_service()
    for target in (MockDimSvc, MockDimSvcApp):
        target.initialize = MagicMock()
        target.get_all_languages = MagicMock(side_effect=dim_data['get_all_languages'])
        target.get_all_test_types = MagicMock(side_effect=dim_data['get_all_test_types'])

    from app import create_app
    flask_app = create_app(TestConfig)

    # Attach the mock so tests can configure per-test return values
    flask_app.supabase = mock_supabase
    flask_app.supabase_service = mock_supabase
    flask_app.mock_supabase = mock_supabase

    yield flask_app


@pytest.fixture()
def client(app):
    """Flask test client — no real HTTP server needed."""
    return app.test_client()


@pytest.fixture()
def auth_headers():
    """Authorization header with a fake Bearer token.

    The jwt_required decorator is patched in the `app` fixture so that
    any token triggers the mock Supabase auth path which always succeeds.
    """
    return {'Authorization': 'Bearer fake-jwt-token-for-testing'}
