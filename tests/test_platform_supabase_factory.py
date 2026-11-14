"""SupabaseFactory: per-thread clients, explicit timeouts, required service key."""

import threading

import pytest

from services.supabase_factory import (
    DEFAULT_POSTGREST_TIMEOUT, SupabaseConfigError, SupabaseFactory,
)

URL = "https://example.supabase.co"
ANON_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoiYW5vbiJ9.sig"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.sig"


@pytest.fixture
def factory(monkeypatch):
    for name in ('SUPABASE_URL', 'SUPABASE_KEY', 'SUPABASE_SERVICE_ROLE_KEY'):
        monkeypatch.delenv(name, raising=False)
    SupabaseFactory.reset()
    yield SupabaseFactory
    SupabaseFactory.set_thread_timeout(None)
    SupabaseFactory.reset()


def _in_thread(fn):
    out = {}
    thread = threading.Thread(target=lambda: out.setdefault('value', fn()))
    thread.start()
    thread.join()
    return out['value']


def test_postgrest_timeout_is_applied(factory):
    factory.initialize(URL, ANON_KEY, SERVICE_KEY, postgrest_timeout=10)
    for client in (factory.get_anon_client(), factory.get_service_client(), factory.get_auth_client()):
        assert client.postgrest.session.timeout.read == 10
        assert client.postgrest.session.timeout.connect == 10


def test_timeout_defaults_to_the_library_value_for_scripts(factory):
    factory.initialize(URL, ANON_KEY, SERVICE_KEY)
    assert factory.get_service_client().postgrest.session.timeout.read == DEFAULT_POSTGREST_TIMEOUT


def test_auth_client_keeps_its_session_options(factory):
    factory.initialize(URL, ANON_KEY, SERVICE_KEY, postgrest_timeout=10)
    options = factory.get_auth_client().options
    assert options.auto_refresh_token is False
    assert options.persist_session is False


def test_missing_service_key_fails_when_required(factory):
    with pytest.raises(SupabaseConfigError, match='SUPABASE_SERVICE_ROLE_KEY'):
        factory.initialize(URL, ANON_KEY, None, require_service_role=True)
    assert not factory.is_initialized()


def test_missing_service_key_is_tolerated_when_not_required(factory):
    factory.initialize(URL, ANON_KEY, None)
    assert factory.get_service_client() is None
    assert factory.get_auth_client() is None


def test_each_running_thread_gets_its_own_connection(factory):
    factory.initialize(URL, ANON_KEY, SERVICE_KEY, postgrest_timeout=10)
    shared = factory.get_service_client()
    mine = shared.postgrest.session
    barrier = threading.Barrier(3)
    sessions = []

    def worker():
        session = shared.postgrest.session
        barrier.wait(timeout=5)
        sessions.append(session)

    threads = [threading.Thread(target=worker) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len({id(s) for s in sessions} | {id(mine)}) == 4
    assert shared.postgrest.session is mine


def test_a_finished_threads_client_is_reused(factory):
    factory.initialize(URL, ANON_KEY, SERVICE_KEY, postgrest_timeout=10)
    shared = factory.get_service_client()
    first = _in_thread(lambda: id(shared.postgrest.session))
    second = _in_thread(lambda: id(shared.postgrest.session))
    assert first == second


def test_thread_timeout_override_is_local_to_the_thread(factory):
    factory.initialize(URL, ANON_KEY, SERVICE_KEY, postgrest_timeout=10)
    shared = factory.get_service_client()

    def job():
        factory.set_thread_timeout(120)
        return shared.postgrest.session.timeout.read

    assert _in_thread(job) == 120
    assert shared.postgrest.session.timeout.read == 10
    # The long-timeout client is not handed to a later request thread.
    assert _in_thread(lambda: shared.postgrest.session.timeout.read) == 10


def test_app_startup_fails_without_the_service_key_outside_tests(monkeypatch):
    from config import Config

    class ProductionLike(Config):
        SECRET_KEY = 'k'
        SUPABASE_URL = URL
        SUPABASE_KEY = ANON_KEY
        SUPABASE_SERVICE_ROLE_KEY = None

    from app import create_app
    with pytest.raises(RuntimeError, match='SUPABASE_SERVICE_ROLE_KEY'):
        create_app(ProductionLike)
