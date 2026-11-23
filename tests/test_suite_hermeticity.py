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


def _child_pytest(tmp_path, files, *args):
    """Run a child pytest on ``files`` with this suite's conftest; return its result."""
    (tmp_path / 'conftest.py').write_text("pytest_plugins = ['tests.conftest']\n")
    for name, text in files.items():
        (tmp_path / name).write_text(text)
    env = {k: v for k, v in os.environ.items() if k != 'PYTEST_ADDOPTS'}
    env['PYTHONPATH'] = os.pathsep.join([REPO_ROOT, env.get('PYTHONPATH', '')])
    return subprocess.run(
        [sys.executable, '-m', 'pytest', '-q', '-rs', '-p', 'no:cacheprovider', '-p', 'no:randomly',
         '--rootdir', str(tmp_path), '-c', os.devnull, *args, *map(str, files)],
        cwd=tmp_path, env=env, capture_output=True, text=True)


_LIVE_FILE = {'test_live.py': (
    'import pytest\n'
    '@pytest.mark.live\n'
    'def test_reads_the_live_project():\n'
    '    pass\n'
    'def test_offline():\n'
    '    pass\n'
)}


def test_live_tests_are_skipped_by_default(tmp_path):
    out = _child_pytest(tmp_path, _LIVE_FILE)
    assert out.returncode == 0, out.stdout + out.stderr
    assert '1 passed, 1 skipped' in out.stdout
    assert 'run deliberately with -m live' in out.stdout


def test_live_tests_run_when_selected(tmp_path):
    out = _child_pytest(tmp_path, _LIVE_FILE, '-m', 'live')
    assert out.returncode == 0, out.stdout + out.stderr
    assert '1 passed, 1 deselected' in out.stdout


def test_the_two_prompt_templates_tests_are_marked_live():
    from tests import test_ladder_validation_profiles as ladder
    from tests import test_provider_routing_and_reasoning as routing
    for fn in (ladder.test_ja_p1_prompt_enumerates_exactly_the_profile_pos_set,
               routing.test_no_active_vocab_ladder_model_resolves_to_a_reasoning_class_model):
        assert 'live' in {m.name for m in getattr(fn, 'pytestmark', [])}, fn.__name__


def test_app_fixture_and_a_test_monkeypatch_do_not_leak_a_mock(tmp_path):
    """H-01: a test that monkeypatches a name the `app` fixture also patches.

    Teardown used to restore the real function (app's ``patch()``) and then put
    the app fixture's MagicMock back (monkeypatch's undo, which outlives
    ``app`` because autouse fixtures request monkeypatch first). Runs the pair
    in a child pytest so the leak cannot reach this session.
    """
    out = _child_pytest(tmp_path, {'test_pair.py': (
        'from unittest.mock import Mock\n'
        'import services.supabase_factory as f\n'
        'REAL = (f.get_supabase, f.get_supabase_admin, f.SupabaseFactory)\n'
        'def test_1_patches_over_the_app_mock(app, monkeypatch):\n'
        '    monkeypatch.setattr("services.supabase_factory.get_supabase_admin", lambda: "x")\n'
        '    monkeypatch.setattr("services.supabase_factory.get_supabase", lambda: "x")\n'
        'def test_2_sees_the_real_functions():\n'
        '    assert not any(isinstance(o, Mock) for o in '
        '(f.get_supabase, f.get_supabase_admin, f.SupabaseFactory))\n'
        '    assert (f.get_supabase, f.get_supabase_admin, f.SupabaseFactory) == REAL\n'
    )})
    assert out.returncode == 0, out.stdout + out.stderr
    assert '2 passed' in out.stdout


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
