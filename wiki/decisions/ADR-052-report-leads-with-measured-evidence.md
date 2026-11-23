---
title: "ADR-052: The report leads with measured evidence; model ratings are secondary and decay is not shown in v1"
status: proposed
date: 2026-11-17
---

# ADR-052: The report leads with measured evidence; model ratings are secondary and decay is not shown in v1

## Context
Each `user_vocabulary_knowledge` row holds a raw BKT `p_known`; the app computes a decayed value on
read. Measured on 2026-11-17 ([[features/knowledge-report.tech]] §0):
- Raw `p_known` is not calibrated. For the one human learner, words the model held below 0.20 were
  answered correctly 12 of 17 times and at 0.20–0.40 10 of 14 times. 66 of that learner's 251
  meanings would carry the two lowest of the five `bkt_status` labels.
- "Confirmed" in the draft (`word_test_correct > 0` and `p ≥ 0.75`) was model output: one correct
  check confirms a Zipf-5 word but not a Zipf-4 word, 47 of 72 confirmed lemmas rested on one check,
  3 had at least as many direct wrongs as rights, and one linked reading question moves a row across
  0.75 in either direction.
- Decay pulls every word toward 0.10 regardless of frequency, lifts low rows, is mislabelled
  IMMUTABLE and is erased by the next write. A decay-based "due for a check" flagged 46 meanings for
  that learner, 24 of them in the two most common bands (中, 今, 言う). Practice's review pool is a
  different set (197 rows), so a "review the 46 due words" button could not keep its promise.
- Learners and reviewers trust a number they can check against their own answers.

## Decision
1. Each Pro row **leads with the most recent measured fact**: "Last direct check ✓/✗ {date}" (from
   the per-word logs), else "Checks ✓{c} ✗{w}", else "Seen in tests only", plus test and check counts.
2. Rows carry one of **four evidence states**, first match wins: *Missed last time* (latest logged
   first-try outcome wrong), *Rated known after a direct check* (`checks_correct > checks_wrong`,
   `p_last ≥ 0.75`, not marked unknown), *Checked, not yet rated known*, *Seen in tests only*.
3. "Rated known after a direct check" is presented as a **model** figure (prefix "Model"), never as
   "confirmed" or "measured". A "checked several times" filter (`checks_correct ≥ 2`) shows the
   stricter set.
4. The five `bkt_status` labels and any numeric `p_known` are **not shown** in rows, filters, the
   summary or exports in v1. The word sheet shows a binary "App's rating: rates this word as known /
   not yet as known, after your answer on {date} — a model rating, not a probability". The labels
   return only after a next-answer-accuracy check per label band (TASK-1056(c)).
5. **No decay-based value in v1**: no effective p, no "due for a check", no "fading". Staleness is the
   measured "Not seen for {n} days" (60+ days flagged, filterable). The "Review in Practice" button
   carries no number. A model-based review flag may return with a frequency-aware decay (TASK-1067).
6. The report calls no decay function, so the volatility defect and the broken 2-argument overload do
   not affect it (their clean-up is TASK-1066, owner-gated).

## Consequences
- Easier: every prominent value is something the learner did, with its date; nothing on the page
  tells a JLPT learner that 今 is fading; the report cannot contradict Practice.
- Harder: the table does not say "you probably know this today"; learners read evidence and dates.
  For de6fd05b/ja: 10 missed last time, 69 rated known, 30 checked but not rated known, 142 seen in
  tests only (MEASURED). Practice that has no per-word log (prestudy warm-ups, flashcards, dictation,
  translation practice) is only visible as counters, and the sheet says so.
- Constrained: snapshots and growth use the same definitions (`method_version` 1); changing a rule
  bumps it.

## Alternatives Considered
- **Last-measured five-level label with its date (the draft):** leads with the least reliable number.
- **Effective (decayed) p or "due for a check":** frequency-blind and erased by writes; flags the most
  common words.
- **Three evidence states (product review P4):** leaves checked-but-not-rated words without a state;
  a fourth makes the set exhaustive.
- **Fix decay first:** changes Practice for everyone and needs validation data that does not exist.
