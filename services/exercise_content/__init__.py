"""Exercise content storage (ADR-047).

Exercise ``content`` moves out of ``exercises.content`` into one immutable JSON
file per sense and version in the private Supabase Storage bucket
``exercise-content``. Callers import exactly one module::

    from services.exercise_content import store

``store`` is the public facade (ADR-047 §9). ``backends``, ``reader``,
``writer`` and the other modules in this package are internal: they implement
the ``storage`` / ``shadow`` reads and ``dual`` writes behind the facade.
"""
