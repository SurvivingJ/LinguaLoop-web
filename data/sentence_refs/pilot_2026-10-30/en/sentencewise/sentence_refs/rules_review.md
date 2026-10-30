# Rules for reviewing sentence references (en -> zh)

You have NOT seen the authoring. Work in this order and do not skip ahead.

**Step 1 — blind back-translation.** For each document, read ONLY the `l1`
sentences above the line `--- GOLD BELOW, DO NOT READ YET ---`. Write your own
English version of each sentence from the Chinese alone, as a competent
learner would, into `back_translations/<test_id>.zh.json`:

```json
{"test_id": "...", "l1": "zh", "sentences": [{"idx": 0, "back": "<your English>"}, ...]}
```

Only after that file is written may you read past the line.

**Step 2 — judge against the gold.** For each sentence decide whether the `l1`
and the gold `l2` entail each other (same facts, same scope, same polarity,
same focus). Flag additions, omissions, wrong numbers or names, register drift,
and any English script in `l1`. If a sentence fails, REWRITE the `l1` so it
passes; mark `rewritten`. Use `fail` only when the gold itself is broken (a
fragment, a leaked preamble) so no faithful reference is possible.

**Step 3 — write.** `reviewed/<test_id>.zh.json` (same shape as the authored
document, `author_notes` removed, your rewrites in place) and
`verdicts/<test_id>.zh.json`:

```json
{"test_id": "...", "l1": "zh", "reviewer_model": "<your model>",
 "sentences": [{"idx": 0, "verdict": "pass|rewritten|fail", "entailment_ok": true, "changed": false, "notes": ""}, ...]}
```

Then run `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py tightness RUN`
(or ask the orchestrator to) — it scores your back-translations against the
gold and adds `tightness` to each verdict. A low tightness with `pass` is
allowed when the gold has several equally faithful renderings; say so in notes.
