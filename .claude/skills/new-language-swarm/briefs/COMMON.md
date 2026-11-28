# Rules for every member of the team

You are one member of a team building the content pack for a new study
language of LinguaLoop. `PACK` is `data/language_packs/<lang>/`; the tool is
`python scripts/language_pack.py <command> <lang> …`, run from the repository
root. Your brief names the files you own.

- **Files only.** Write only the files your brief names. Never write to the
  database (no Supabase tool, no upload script), never call a hosted model API
  or the `claude` CLI, never commit or push, never edit application code,
  `wiki/` or `raw/`.
- **Do not read another member's unfinished work** unless your brief says so,
  and never edit it. A reviewer writes a reviewed copy; the author's file stays.
- **The validator decides when you are done.** Run the command your brief
  names and fix every reported problem. If a rule seems wrong for this
  language, do not work around it: say so in your report.
- **Write as a native speaker of the profile's variety would.** If you are not
  sure a sentence is natural, or a form exists, replace it with one you are
  sure of. A doubtful item costs more than a missing one.
- **English for everything said about the language** (explanations, `why`,
  notes), quoting target-language words as needed.
- **Report honestly.** Your final message is data for the orchestrator: what
  you wrote (paths, counts), the validator's last line, and every doubt you
  could not resolve. Do not describe work you did not do.
