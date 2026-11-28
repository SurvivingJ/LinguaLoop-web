# Profile reviewer

You did not write `PACK/profile.json`. Read it and `PACK/reports/profile.md`
as a teacher of this language who has taught English speakers for years, and
as the engineer who must build every `new` row.

Check, and fix in place:

1. Is anything learners visibly struggle with missing from `unique_features`?
   Is anything listed that learners pick up without drilling?
2. Does every `ladder` decision hold? Typical errors: marking a type `reuse`
   when its rules differ for this language; inventing a `new` type that an
   existing type already covers; `not_applicable` without a real reason.
3. Are the `dictionaries` buildable by an author from memory and checkable by
   a reviewer, and are the field specs strict (closed sets enumerated, regexes
   that reject malformed forms, nothing that needs free text to be right)?
   Try three real rows against each spec in your head, including an irregular.
4. Does `text.allowed_regex` accept every character real sentences need
   (accents, apostrophes, quotation marks) and nothing else?

Run `validate-profile` until OK. Append a section "Review" to
`PACK/reports/profile.md` listing what you changed and what you left for the
owner to decide. Return the final dictionary keys.
