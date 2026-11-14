# services/supabase_factory.py
"""
Centralized Supabase client factory - Single source of truth for all Supabase clients.
Eliminates duplicate client creation across the codebase.
"""

import os
import logging
import threading
import weakref
from typing import Callable, Optional
from postgrest.constants import DEFAULT_POSTGREST_CLIENT_TIMEOUT
from supabase import create_client, Client, ClientOptions

logger = logging.getLogger(__name__)

# PostgREST timeout (seconds) when the caller does not pass one: the library's
# own default, so scripts and batch jobs keep their long calls. The web app
# passes Config.SUPABASE_POSTGREST_TIMEOUT.
DEFAULT_POSTGREST_TIMEOUT = float(DEFAULT_POSTGREST_CLIENT_TIMEOUT)


class SupabaseConfigError(RuntimeError):
    """A credential the running configuration requires is missing."""


class _Lease:
    """One thread's hold on a client; the client goes back to the idle list
    when the thread (and with it this object) dies."""
    __slots__ = ('client', '__weakref__')

    def __init__(self, client):
        self.client = client


class _PerThreadClient:
    """Stands in for a supabase ``Client`` and gives each thread its own.

    supabase-py talks HTTP/2 over a single connection per client, and that
    connection is not safe to share between threads: concurrent calls fail
    with "[Errno 11] Resource temporarily unavailable". Every attribute access
    is forwarded to a client held by the calling thread alone, so the object
    can be stored and shared freely (app.supabase, service singletons) under
    threaded workers. Clients of finished threads are reused, so a server that
    starts a thread per request keeps its warm connections.
    """

    def __init__(self, build: Callable[[Optional[float]], Client]):
        object.__setattr__(self, '_build', build)
        object.__setattr__(self, '_local', threading.local())
        object.__setattr__(self, '_idle', [])

    def _client(self) -> Client:
        local = self._local
        lease = getattr(local, 'lease', None)
        if lease is None:
            lease = local.lease = self._acquire()
        return lease.client

    def _acquire(self) -> _Lease:
        timeout = getattr(SupabaseFactory._thread_overrides, 'timeout', None)
        if timeout is not None:
            # A client with a non-default timeout is never pooled.
            return _Lease(self._build(timeout))
        try:
            client = self._idle.pop()
        except IndexError:
            client = self._build(None)
        lease = _Lease(client)
        weakref.finalize(lease, self._idle.append, client)
        return lease

    def _discard(self) -> None:
        """Forget the calling thread's client; the next access takes a new one."""
        self._local.__dict__.pop('lease', None)

    def __getattr__(self, name):
        return getattr(self._client(), name)

    def __setattr__(self, name, value):
        setattr(self._client(), name, value)

    def __repr__(self):
        return f"<per-thread {self._client()!r}>"


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
    _timeout: float = DEFAULT_POSTGREST_TIMEOUT
    _thread_overrides = threading.local()

    @classmethod
    def initialize(cls, supabase_url: str = None, supabase_key: str = None,
                   service_role_key: str = None, postgrest_timeout: float = None,
                   require_service_role: bool = False) -> None:
        """
        Initialize the factory with credentials.
        Call this once at app startup (e.g., in create_app).

        ``postgrest_timeout`` is the per-call database timeout in seconds.
        ``require_service_role`` makes a missing service-role key a startup
        error instead of a warning.
        """
        url = supabase_url or os.getenv('SUPABASE_URL')
        anon_key = supabase_key or os.getenv('SUPABASE_KEY')
        service_key = service_role_key or os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not url or not anon_key:
            logger.error("Supabase URL and anon key are required")
            raise ValueError("Missing Supabase credentials")

        if require_service_role and not service_key:
            raise SupabaseConfigError(
                "SUPABASE_SERVICE_ROLE_KEY is not set. The app cannot run without the "
                "service-role client; set it in .env or the deployment environment."
            )

        cls._timeout = float(postgrest_timeout or DEFAULT_POSTGREST_TIMEOUT)

        try:
            cls._anon_client = cls._per_thread(url, anon_key)
            logger.info("Supabase anon client initialized")

            if service_key:
                cls._service_client = cls._per_thread(url, service_key)
                logger.info("Supabase service role client initialized")
                cls._auth_client = cls._per_thread(
                    url, service_key, auto_refresh_token=False, persist_session=False,
                )
                logger.info("Supabase auth-flow client initialized")
            else:
                logger.warning("Service role key not provided - admin operations will be unavailable")

            cls._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize Supabase clients: {e}")
            raise

    @classmethod
    def _per_thread(cls, url: str, key: str, **option_overrides) -> _PerThreadClient:
        def build(timeout: Optional[float]) -> Client:
            timeout = timeout or cls._timeout
            # GoTrue calls keep httpx's 5 s default: this supabase-py version
            # exposes no option for the auth client's timeout.
            options = ClientOptions(
                postgrest_client_timeout=timeout,
                storage_client_timeout=timeout,
                function_client_timeout=timeout,
                **option_overrides,
            )
            return create_client(url, key, options=options)

        proxy = _PerThreadClient(build)
        # Build once now so a malformed key fails at startup, not on first use.
        proxy._client()
        return proxy

    @classmethod
    def set_thread_timeout(cls, seconds: Optional[float]) -> None:
        """Use a different PostgREST timeout for the calling thread's clients
        (long-running scheduled jobs). ``None`` restores the default."""
        if getattr(cls._thread_overrides, 'timeout', None) == seconds:
            return
        cls._thread_overrides.timeout = seconds
        for proxy in (cls._anon_client, cls._service_client, cls._auth_client):
            if isinstance(proxy, _PerThreadClient):
                proxy._discard()

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
        cls._timeout = DEFAULT_POSTGREST_TIMEOUT


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
