# services/supabase_factory.py
"""
Centralized Supabase client factory - Single source of truth for all Supabase clients.
Eliminates duplicate client creation across the codebase.
"""

import os
import logging
from typing import Optional
from supabase import create_client, Client, ClientOptions

logger = logging.getLogger(__name__)


class SupabaseFactory:
    """
    Singleton factory for Supabase clients.
    Provides both anon (RLS-protected) and service role (admin) clients.
    """

    _anon_client: Optional[Client] = None
    _service_client: Optional[Client] = None
    # Dedicated to login-flow calls (verify_otp / refresh_session / ...). supabase-py
    # swaps a client's Authorization header to the signed-in USER's JWT on every
    # SIGNED_IN / TOKEN_REFRESHED event, so running those calls on the shared
    # service client demotes all its later database calls from service_role to
    # authenticated. Never use this client for table or RPC access.
    _auth_client: Optional[Client] = None
    _initialized: bool = False

    @classmethod
    def initialize(cls, supabase_url: str = None, supabase_key: str = None,
                   service_role_key: str = None) -> None:
        """
        Initialize the factory with credentials.
        Call this once at app startup (e.g., in create_app).
        """
        url = supabase_url or os.getenv('SUPABASE_URL')
        anon_key = supabase_key or os.getenv('SUPABASE_KEY')
        service_key = service_role_key or os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not url or not anon_key:
            logger.error("Supabase URL and anon key are required")
            raise ValueError("Missing Supabase credentials")

        try:
            cls._anon_client = create_client(url, anon_key)
            logger.info("Supabase anon client initialized")

            if service_key:
                cls._service_client = create_client(url, service_key)
                logger.info("Supabase service role client initialized")
                cls._auth_client = create_client(
                    url, service_key,
                    options=ClientOptions(auto_refresh_token=False, persist_session=False),
                )
                logger.info("Supabase auth-flow client initialized")
            else:
                logger.warning("Service role key not provided - admin operations will be unavailable")

            cls._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize Supabase clients: {e}")
            raise

    @classmethod
    def get_anon_client(cls) -> Client:
        """
        Get the anon client (RLS-protected).
        Use for user-context operations where RLS should apply.
        """
        if not cls._initialized or not cls._anon_client:
            raise RuntimeError("SupabaseFactory not initialized. Call initialize() first.")
        return cls._anon_client

    @classmethod
    def get_service_client(cls) -> Optional[Client]:
        """
        Get the service role client (bypasses RLS).
        Use for admin operations, batch processing, or when RLS must be bypassed.
        Returns None if service role key was not provided.
        """
        if not cls._initialized:
            raise RuntimeError("SupabaseFactory not initialized. Call initialize() first.")
        return cls._service_client

    @classmethod
    def get_auth_client(cls) -> Optional[Client]:
        """
        Get the client reserved for login-flow calls (OTP, refresh, session mint).
        Its auth state is allowed to change; the shared service client's must not.
        Returns None if service role key was not provided.
        """
        if not cls._initialized:
            raise RuntimeError("SupabaseFactory not initialized. Call initialize() first.")
        return cls._auth_client

    @classmethod
    def is_initialized(cls) -> bool:
        """Check if the factory has been initialized."""
        return cls._initialized

    @classmethod
    def reset(cls) -> None:
        """Reset the factory (mainly for testing purposes)."""
        cls._anon_client = None
        cls._service_client = None
        cls._auth_client = None
        cls._initialized = False


# Convenience functions for quick access
def get_supabase() -> Client:
    """Get the default (anon) Supabase client."""
    return SupabaseFactory.get_anon_client()


def get_supabase_admin() -> Optional[Client]:
    """Get the service role Supabase client."""
    return SupabaseFactory.get_service_client()


def get_supabase_auth() -> Optional[Client]:
    """Get the client reserved for login-flow calls (never for table/RPC access)."""
    return SupabaseFactory.get_auth_client()
