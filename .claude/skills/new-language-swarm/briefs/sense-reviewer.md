# Sense reviewer

You did not write `PACK/senses/write_<NNN>.out.json`. Review every entry
against `write_<NNN>.in.json` and write the full corrected array to
`PACK/senses/write_<NNN>.reviewed.json` (same shape, same order), plus
`PACK/senses/write_<NNN>.verdict.json`: `{"ok": n, "fixed": n, "skipped": n, "items": {"<lemma>": {"v": "ok"|"fix", "note": "…"}}}`.

Fix an entry (rewrite only the fields that need it) when:

- it defines a different word or sense than lemma + pos + hint;
- a definition joins two or more meanings;
- `tl_simple` uses the word itself, a grammar term, or is not a child's register;
- the example is unnatural, or does not use the word;
- a gloss is a sentence, contains the target-language word, is a false friend,
  or misses the main equivalent;
- pronunciation or `lexical` facts are wrong (check each one: these are the
  errors authors make most);
- a shape rule fails.

Be strict on meaning and facts, light on style. Run `validate-senses` on the
reviewed file until OK.

When a lemma occurs twice in a batch, key the verdict items `<lemma> (<pos>)`.
