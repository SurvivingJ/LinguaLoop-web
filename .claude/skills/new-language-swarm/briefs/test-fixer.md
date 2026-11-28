# Test fixer

A cold solver answered some questions of `PACK/tests/reviewed/t<tier>-<NN>.jsonl`
correctly without seeing the passage. Run
`python3 scripts/language_pack.py tests-compare <lang> PACK/tests/reviewed/t<tier>-<NN>.jsonl --tag r --cold-only`
to list them, and read the solver's reasons in
`PACK/tests/blind/t<tier>-<NN>.r.answers_nopassage.jsonl` (`why`).

About one flag in four is luck (the `why` says "pure guess" or similar):
leave those. For every other flagged question, repair the cause, following
"Questions that need the passage" in `briefs/test-author.md` and
`TEST_SPEC.md`:

- leaked by another question: reword the stem or the choices of the leaking
  question, or ask something else;
- the key stood out: give all four choices the same form, length and scope;
- common sense, stereotype or general knowledge: change the PASSAGE so the
  true detail is one nobody would predict (update the sentence's `en`, the
  `evidence` and the explanation), then ask about it; or replace the question
  with one on a particular the passage already has.

Keep everything else as it is: do not rewrite sound questions, and keep the
passage inside its tier's word range. Edit the reviewed file in place, add
`"cold_flags": n, "cold_fixed": n` to `PACK/tests/verdicts/t<tier>-<NN>.json`,
and run `validate-tests <lang> PACK/tests/reviewed/t<tier>-<NN>.jsonl` until OK.
