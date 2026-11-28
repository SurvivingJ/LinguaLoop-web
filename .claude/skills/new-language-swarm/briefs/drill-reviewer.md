# Drill reviewer

You did not write `PACK/grammar/batches/<slug>-<NN>.jsonl`, and you must not
open it until step 3.

1. Run `python scripts/language_pack.py strip <lang> <slug>-<NN>.jsonl`. It
   writes `PACK/grammar/blind/<slug>-<NN>.blind.jsonl` (items without answers).
2. **Solve the blind file** as a careful native speaker, writing one line per
   item to `PACK/grammar/blind/<slug>-<NN>.answers.jsonl`:
   - cloze: `{"id", "ok": [indexes of EVERY option a native speaker could accept]}`
   - order / rewrite: `{"id", "tl": "the sentence you build from the tiles"}`
   - judge: `{"id", "ok": true|false}`
3. Run `compare <lang> <slug>-<NN>.jsonl`. Every flag is an item where you and
   the key disagree: decide who is right. Then read the whole batch with the
   guide and `GRAMMAR_SPEC.md` and review each item: natural sentence, one
   acceptable answer, complete `alts`, a `why` that is true and specific,
   correct level and sub-point, English cue that matches.
4. Write the corrected batch to `PACK/grammar/reviewed/<slug>-<NN>.jsonl`
   (fix what can be fixed, drop what cannot, add replacements only if the
   batch falls under its minimum) and
   `PACK/grammar/verdicts/<slug>-<NN>.json`:
   `{"flagged": n, "fixed": n, "dropped": n, "added": n, "items": {"<id>": {"v": "fix"|"drop"|"add", "note": "…"}}, "guide_notes": ["anything the guide states wrongly or leaves out"]}`.
5. Run `validate-batch <lang> PACK/grammar/reviewed/<slug>-<NN>.jsonl
   --min-items <n>` until OK.
