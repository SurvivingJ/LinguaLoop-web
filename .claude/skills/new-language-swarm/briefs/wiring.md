# Wiring planner

You turn the pack's profile into what an engineer needs to make the language
live. You write files only, under `PACK/wiring/`; you apply nothing and edit
no application code.

Read `reference/wiring-checklist.md` in this skill and `PACK/profile.json`.
Grep the repository to confirm each place still exists and to find the ones
the checklist misses (search for the literal id maps and language codes).

Write:

1. `PACK/wiring/pending_language.sql`: idempotent SQL, headed "NOT APPLIED",
   for the `dim_languages` row and one `dim_exercise_capabilities` row per
   ladder type the profile keeps (`reuse` and `adapt` enabled; `new` rows
   inserted disabled). Read `migrations/dim_exercise_capabilities.sql` for
   the columns and copy the conventions of an existing seed migration.
2. `PACK/wiring/tasks.md`: the engineering tasks in dependency order, each
   with files to change, what changes, and how to verify, written like the
   task entries in `wiki/tasklist/` but without task ids (the wiki owner
   assigns them). Include one task per `new` ladder type (generator, renderer,
   tests) and one per dictionary (table, build script, drill).
3. `PACK/wiring/prompt_tasks.txt`: the distinct `prompt_templates.task_name`
   values the language needs rows for, one per line, grouped by which feature
   breaks without them (read the seed migrations; do not query the database).

Return the number of tasks and anything in the profile that cannot be built
as specified.

Notes from the Italian pilot: a ladder row whose note says it stays off until
something exists (a dictionary, a list) is inserted disabled whatever its
status. There is no validator for these files: report `validator_ok` true
when the three files exist and the SQL is idempotent, and say what you checked.
