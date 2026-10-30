---
name: sentence-reference-review
description: Review sentence-level L1 reference translations written by another subagent — first back-translate each reference blind (without the gold), then judge mutual entailment against the gold, rewrite what fails, and record a verdict per sentence; the runner scores tightness from the blind back-translation. Must run in a fresh context that has not seen the authoring. Use when handed a review pack (RUN/sentence_refs/review_packs/review_NN.md) or asked to review sentence references.
---

# Sentence-Reference Review

You are the second pair of eyes on native-language references that a learner
will translate back into the studied language. You have not seen the authoring
and you must not look for it. Read only the review pack you were given and the
rules file it names.

Models: the orchestrator sends items flagged by the deterministic checks plus a
stratified 15% sample to **Opus**, the rest to **Sonnet**. You do not choose.

## Order of work (hard rule)

1. **Blind back-translation first.** Your pack is two files: `review_NN.md`
   holds only the L1 references; `review_NN.gold.md` holds the gold. Do not
   open the gold file yet. From the references alone, write
   `RUN/sentence_refs/back_translations/<test_id>.<l1>.json` with your own L2
   version of every sentence. Save every file for the pack first. The
   tightness score is only meaningful if you did not see the gold; if you did,
   say so in that test's verdict notes (`gold_seen_early`).
2. **Judge.** Now open `review_NN.gold.md`. Per sentence: do L1 and gold entail each other
   (same facts, scope, polarity, focus, numbers, names, register)? Any L2
   script in the L1? If it fails, rewrite the L1 so it passes and mark
   `rewritten`. `fail` is only for a gold that is itself broken (fragment,
   leaked preamble).
3. **Write.** `RUN/sentence_refs/reviewed/<test_id>.<l1>.json` (the document
   with your rewrites, `author_notes` removed) and
   `RUN/sentence_refs/verdicts/<test_id>.<l1>.json`:

```json
{"test_id": "...", "l1": "en", "reviewer_model": "<your model id>",
 "sentences": [{"idx": 0, "verdict": "pass", "entailment_ok": true, "changed": false, "notes": ""}]}
```

Then run `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py tightness RUN`
(or ask the orchestrator to): it adds `tightness` and `back_translation` to
each verdict from your step-1 file. Finish with
`… check RUN --source reviewed --tests <id1,id2,…>` (comma-separated, no spaces) and fix until `ok`.

## What to check

- Meaning: nothing added, nothing dropped, no hedges the gold does not have.
- Numbers and names: digit for digit; standard L1 forms for proper nouns.
- Sentence identity: one L1 entry still maps to exactly one gold sentence.
- Register: a polite or formal gold is not rendered casual, and vice versa,
  where the L1 can mark it.
- Leakage: no kanji, kana or hanzi in English; no romaji; no translator's
  notes or parentheses.
- Tightness: if your blind back-translation landed far from the gold, ask
  whether the L1 was loose or the gold simply has several faithful renderings.
  Rewrite in the first case; `pass` with a note in the second.

## Hard rules

- Never read the authored `docs/` directory or the author briefs.
- Never open the gold file before every back-translation file for the pack exists.
- Never change `l2` or `idx`.
- Record a verdict for every sentence; `pending` is not a verdict.
