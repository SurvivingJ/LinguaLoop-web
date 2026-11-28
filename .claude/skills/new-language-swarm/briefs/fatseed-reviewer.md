# Fat-seed reviewer

You did not write the documents in `PACK/fat_seed/words/`. For each one your
task names, check it as `.claude/skills/fat-seed-review/SKILL.md` describes
(read its checks; the runner commands there do not apply to this language
yet), against the cheat sheet `.claude/skills/fat-seed-authoring/cheatsheets/<lang>.md`.

The checks that find the most defects, in order: a core sentence that uses
another sense or is unnatural; a level_3 or level_4 distractor that also fits
the blank; a level_6 "wrong" sentence that is actually acceptable, or wrong
for grammar instead of meaning; a level_7 with two errors or an error off the
target; an explanation that is generic or false; B copying A.

Write the corrected document to `PACK/fat_seed/reviewed/<doc>` and one line
per document to `PACK/fat_seed/reviewed/verdicts.jsonl`:
`{"doc", "verdict": "ok"|"fixed"|"reject", "fatal": n, "minor": n, "notes": ["block: what was wrong"]}`
(`fatal` = defects that would have made an item wrong or unanswerable).
Run `validate-fatseed <lang> PACK/fat_seed/reviewed/<doc>` until OK.
