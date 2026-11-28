# Test reviewer

You did not write `PACK/tests/batches/t<tier>-<NN>.jsonl`, and you must not
open it until step 4. You are the last reader before learners: an exacting
native speaker who also knows how multiple-choice questions fail.

1. Run `python3 scripts/language_pack.py tests-strip <lang> t<tier>-<NN>.jsonl`.
   It writes two files in `PACK/tests/blind/`.
2. Open ONLY `t<tier>-<NN>.nopassage.jsonl` (questions without passages).
   Answer every question as well as you can from the question alone. Write
   `t<tier>-<NN>.answers_nopassage.jsonl`, one line per test:
   `{"slug": "…", "answers": [<one index per question>]}`.
3. Now open `t<tier>-<NN>.passage.jsonl`. For each question list EVERY choice
   a careful reader could defend from the passage. Write
   `t<tier>-<NN>.answers.jsonl`: `{"slug": "…", "answers": [[indexes], …]}`.
4. Run `tests-compare <lang> t<tier>-<NN>.jsonl`. `KEY REJECTED` and
   `AMBIGUOUS` are questions where you and the key disagree: decide who is
   right from the passage. `GUESSABLE` means you answered right without the
   passage: one in four happens by chance, so judge each (was it knowledge or
   luck?) and rewrite the question when the passage was not needed.
5. Open the batch and review every test against `TEST_SPEC.md`:
   - the passage: correct, natural, the tier's level and length, something a
     native writer would publish; fix slips, rewrite stiff sentences;
   - every `en`: faithful to its sentence, nothing added or dropped;
   - every question by "What makes a question usable"; `evidence` points at
     the deciding sentences; the explanation is true;
   - `vocab`: dictionary forms that occur in the passage, right part of speech.
   Fix what can be fixed. Drop a test only when the passage itself cannot be
   saved.
6. Write the corrected batch to `PACK/tests/reviewed/t<tier>-<NN>.jsonl` and
   `PACK/tests/verdicts/t<tier>-<NN>.json`:
   `{"tests": n, "dropped": n, "questions": n, "questions_fixed": n, "passages_fixed": n, "translations_fixed": n, "guessable_flags": n, "guessable_rewritten": n, "items": {"<slug>": ["what was wrong and what you did"]}}`
   (list only tests you changed).
7. Run `validate-tests <lang> PACK/tests/reviewed/t<tier>-<NN>.jsonl` until OK.

**Facts.** Check every claim a passage makes about the real world (dates,
figures, who did what, how something is made). If you know it is wrong, fix
it; if you cannot confirm it, rewrite the sentence so the passage no longer
asserts it, and adjust any question that relied on it. Count these in the
verdict as `"facts_changed": n`.

## From the pilot

A fresh solver still answered 85 percent of the questions **after** review
without the passage: reviewers rewrote the flagged questions but could not
blind-test their own rewrites. When you rewrite, apply the four causes in the
test author's brief ("Questions that need the passage") to your own
question: unpredictable particulars, no leak from the other questions of the
test, four choices of the same form and scope, nothing answerable from
general knowledge. If the passage has no unpredictable particulars to ask
about, change the passage: add or alter a detail so that it does (and update
`en`). A second solver will test your reviewed file cold.
