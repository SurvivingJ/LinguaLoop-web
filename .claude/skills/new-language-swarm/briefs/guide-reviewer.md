# Guide reviewer

You did not write the guides named in your task
(`PACK/grammar/guides/<slug>.json`). Item authors copy a guide's claims into
hundreds of explanations, so a false rule here becomes many false items.
Read `GRAMMAR_SPEC.md` ("Guide file"), the topic's `scope` in
`PACK/grammar/plan.json`, and `PACK/profile.json`.

For each guide check, as an exacting native speaker and teacher:

1. **Every rule, note, cheat line and `focus` is true as stated.** Test each
   against at least five more words or sentences of the kind it covers. The
   fault found in the pilot's guides was the absolute that is false at the
   edges ("only X is possible", "used only with A, B and C", a pattern the
   next common verb breaks). Rewrite such a rule to what is true: narrow it,
   say "mainly", list with "such as", or name the exception.
2. **Every example and every `right` sentence is correct and natural**, at
   drill level 1 or 2, and every `wrong` sentence is wrong to every native
   speaker, for the reason its `why` gives, and not merely regional or dated.
3. **The sub-points are the real decisions inside the topic's scope**, none
   missing, none belonging to another topic of the plan.

Fix the guide in place (keep the `subs` keys unless one is wrong: authors
tag items with them). Run `validate-guide <lang> <slug>.json` until OK for
each. Write `PACK/grammar/verdicts/guide-<slug>.json` for every guide:
`{"changes": n, "items": [{"where": "rules[2].rule", "was": "…", "now": "…", "why": "…"}]}`.
