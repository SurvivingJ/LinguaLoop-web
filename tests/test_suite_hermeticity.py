"""The offline suite cannot reach the live database (tests/conftest.py guard).

A test that is not marked ``live`` runs with no Supabase or OpenRouter
credentials in the environment or on ``Config``, with ``SupabaseFactory``
uninitialised, and with ``.env`` never loaded by ``config.py``. Code that asks
the factory for a client without the test supplying a fake gets an error
instead of a client for the real project. These tests pin that guard.
"""

import os
import subprocess
import sys

import pytest

from config import Config
from services import supabase_factory
from services.supabase_factory import SupabaseFactory

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS = ('SUPABASE_URL', 'SUPABASE_KEY', 'SUPABASE_SERVICE_ROLE_KEY',
               'SUPABASE_ANON_KEY', 'SUPABASE_ACCESS_TOKEN', 'OPENROUTER_API_KEY')


@pytest.mark.parametrize('name', CREDENTIALS)
def test_no_credential_is_in_the_environment(name):
    assert name not in os.environ


@pytest.mark.parametrize('name', ['SUPABASE_URL', 'SUPABASE_KEY', 'SUPABASE_SERVICE_ROLE_KEY',
                                  'OPENROUTER_API_KEY'])
def test_no_credential_is_on_config(name):
    assert not getattr(Config, name)


def test_the_factory_starts_uninitialised():
    assert not SupabaseFactory.is_initialized()


@pytest.mark.parametrize('getter', ['get_supabase', 'get_supabase_admin', 'get_supabase_auth'])
def test_an_unmocked_client_request_fails_closed(getter):
    with pytest.raises(RuntimeError, match='not available in tests'):
        getattr(supabase_factory, getter)()


def test_initialising_from_the_environment_fails(monkeypatch):
    # Even a credential that reappears mid-test (a script's bootstrap() loading
    # .env) cannot be turned into a client: the factory refuses the env fallback.
    monkeypatch.setenv('SUPABASE_URL', 'https://example.invalid')
    monkeypatch.setenv('SUPABASE_KEY', 'a.b.c')
    with pytest.raises(RuntimeError, match='not available in tests'):
        SupabaseFactory.initialize()
    assert not SupabaseFactory.is_initialized()


def test_explicit_fake_credentials_still_build_a_client():
    # Tests of the factory itself pass their own (fake) URL and keys.
    SupabaseFactory.initialize('https://example.supabase.co', 'a.b.c', 'a.b.c')
    assert SupabaseFactory.get_service_client() is not None


def test_a_test_that_initialised_the_factory_does_not_leave_it_initialised():
    # Pairs with the test above in either order: every test starts reset.
    assert not SupabaseFactory.is_initialized()


def test_a_test_can_supply_its_own_fake(monkeypatch):
    monkeypatch.setattr(supabase_factory, 'get_supabase_admin', lambda: 'fake')
    assert supabase_factory.get_supabase_admin() == 'fake'


def test_config_skips_dotenv_when_asked(tmp_path):
    """LINGUADOJO_SKIP_DOTENV keeps config.py from loading .env; unset, it loads it."""
    (tmp_path / '.env').write_text('LINGUADOJO_DOTENV_PROBE=loaded\n')
    code = ('import os, config; '
            'print(os.environ.get("LINGUADOJO_DOTENV_PROBE", "absent"))')
    env = {k: v for k, v in os.environ.items() if k != 'LINGUADOJO_SKIP_DOTENV'}
    env['PYTHONPATH'] = REPO_ROOT

    def probe(**extra):
        out = subprocess.run([sys.executable, '-c', code], cwd=tmp_path, env={**env, **extra},
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()

    assert probe() == 'loaded'
    assert probe(LINGUADOJO_SKIP_DOTENV='1') == 'absent'
