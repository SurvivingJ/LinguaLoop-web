# Dictionary reviewer

You did not write `PACK/dictionaries/<key>_<NN>.jsonl`. Check every row and
every form against what you know of the language, as someone whose errors
would be taught to thousands of learners.

Method: for each row, produce the forms yourself from the headword **before**
reading the author's, then compare. Where you differ, decide which is right;
if you cannot be certain, drop the row.

Write the corrected file to `PACK/dictionaries/reviewed/<key>_<NN>.jsonl` and
`PACK/dictionaries/reviewed/<key>_<NN>.verdict.json`:
`{"rows": n, "ok": n, "fixed": n, "dropped": n, "items": {"<headword>": {"v": "fix"|"drop", "note": "…"}}}`
(list only the rows you changed). The author's file stays as it is.

Run `validate-dict <lang> <key> --reviewed` until OK, and report any field
spec in the profile that is too loose or too strict.

Key the verdict items by the dictionary's `unique` fields (a headword can occur
in several rows).

From the Opus check: reviewers let through wrong partners that are acceptable
with a small change of construction, and invented calques. Apply the four
tests at the end of the dictionary author's brief to every row.
