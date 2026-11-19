"""Exercise content storage (ADR-049).

Exercise ``content`` lives in one immutable JSON file per sense and version in
the private Supabase Storage bucket ``exercise-content`` (the
``exercises.content`` column was dropped on 2026-11-19). Callers import exactly
one module::

    from services.exercise_content import store

``store`` is the public facade (ADR-049 §9). ``backends``, ``cache``,
``reader`` and ``writer`` are internal: they implement the reads and the
file-first, compare-and-swap writes behind the facade.
"""
