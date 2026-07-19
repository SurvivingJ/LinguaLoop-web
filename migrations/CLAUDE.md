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

## Backfill migrations — keep the exclusive-lock window short

When a migration backfills columns and/or tightens constraints on a table, it can
hold an `ACCESS EXCLUSIVE` lock for the whole transaction. On a small table that's
harmless (e.g. `dt_severity_triad.sql`, applied 2026-07-06, ran two full-table
`UPDATE`s + a `count(*)` verify + a validating `ADD CONSTRAINT` in one txn — fine
then, **do not touch that history**). On a larger table (e.g. a future backfill on
`dt_error_instance`) the same shape blocks all reads/writes for the duration. Prefer
the cheaper pattern:

1. **Collapse multi-value backfills into one `UPDATE` with a `CASE` expression**
   rather than one `UPDATE` per value. One pass over the heap, one write-lock span,
   instead of N.

   ```sql
   -- instead of: UPDATE t SET sev = 'major' WHERE subtype = 'a';
   --             UPDATE t SET sev = 'minor' WHERE subtype = 'b'; ...
   UPDATE t SET sev = CASE subtype
       WHEN 'a' THEN 'major'
       WHEN 'b' THEN 'minor'
       ELSE sev
   END
   WHERE subtype IN ('a', 'b', ...);   -- keep the predicate so unaffected rows aren't rewritten
   ```

2. **Add new `CHECK` constraints as `NOT VALID`, then `VALIDATE` in a separate
   statement outside the exclusive-lock window.** `ADD CONSTRAINT ... NOT VALID`
   takes only a brief `ACCESS EXCLUSIVE` lock to record the constraint (it does not
   scan the table); the subsequent `VALIDATE CONSTRAINT` scans under a weaker
   `SHARE UPDATE EXCLUSIVE` lock that does **not** block reads or writes.

   ```sql
   ALTER TABLE t ADD CONSTRAINT t_sev_chk CHECK (sev IN ('major','minor')) NOT VALID;
   -- ... commit, or at least end the heavy-lock statement ...
   ALTER TABLE t VALIDATE CONSTRAINT t_sev_chk;   -- concurrent-friendly scan
   ```

   New rows are enforced from the moment the `NOT VALID` constraint exists; `VALIDATE`
   only confirms the pre-existing rows.

Also avoid an in-transaction `count(*)` verification on a large table just to confirm
a backfill — it forces another full scan under the same lock. Verify out-of-band after
commit instead.
