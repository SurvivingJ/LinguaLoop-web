"""Shared by the route modules."""

from services import supabase_factory


def get_db():
    """The service-role Supabase client (bypasses RLS; one per thread)."""
    return supabase_factory.get_supabase_admin()
