# tests/conftest.py
"""Shared fixtures for the LinguaDojo test suite."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from types import SimpleNamespace

from config import Config


# ---------------------------------------------------------------------------
# Test configuration
# ---------------------------------------------------------------------------

class TestConfig(Config):
    """Test-specific overrides — disables external services."""
    TESTING = True
    DEBUG = False
    SECRET_KEY = 'test-secret-key'
    JWT_SECRET_KEY = 'test-jwt-secret'

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
def app(mock_supabase):
    """Create a Flask test app with all external services mocked out."""

    with patch('services.supabase_factory.SupabaseFactory') as MockFactory, \
         patch('services.supabase_factory.get_supabase', return_value=mock_supabase), \
         patch('services.supabase_factory.get_supabase_admin', return_value=mock_supabase), \
         patch('services.dimension_service.DimensionService') as MockDimSvc, \
         patch('app.DimensionService') as MockDimSvcApp, \
         patch('app.ServiceFactory'), \
         patch('app.R2Service'), \
         patch('app.PromptService'), \
         patch('app.AuthService'):

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
