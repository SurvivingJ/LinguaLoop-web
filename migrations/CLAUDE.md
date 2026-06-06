# Migrations — agent rules

The live Supabase DB is the source of truth, but `migrations/` is supposed to
*reflect* the current definition of every object. To keep it trustworthy:

## When you write a new migration

After adding a migration that **redefines** an existing object (any
`CREATE OR REPLACE FUNCTION`, or an `ALTER`/redefinition of a column, table,
view, trigger, or RPC that already exists):

1. **Search `migrations/` (NOT `migrations/archive/`)** for every other file
   that defines the same object — e.g.
   `grep -rln "FUNCTION public.<name>" migrations --exclude-dir=archive`.
2. For each older file found, decide if it is now **fully superseded** — i.e.
   *every* object it defines is now defined by a newer file or has been dropped
   from the live DB. Verify against the live DB when unsure
   (`pg_get_functiondef('public.<name>(<args>)'::regprocedure)` and probe for a
   marker unique to the new version).
3. If a file is fully superseded, **move it to `migrations/archive/`** (use
   `git mv`) and add a row to `migrations/archive/README.md` recording the
   object, the new canonical file, and the marker you checked.
4. **Do not archive a multi-object file** if it is still the only repo record of
   any object that is live and not redefined elsewhere — keep it, even if one of
   its objects is now stale.

## When you read `migrations/`

Treat anything in `migrations/archive/` as history only — never as the current
definition. The newest non-archived file defining an object is canonical; if two
non-archived files define the same object, that's drift to clean up via the steps
above.
