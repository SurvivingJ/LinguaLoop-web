---
title: "ADR-056: Knowledge Report actions reuse existing study paths (word-list import, Practice, prestudy)"
status: proposed
date: 2026-11-17
---

# ADR-056: Knowledge Report actions reuse existing study paths (word-list import, Practice, prestudy)

## Context
A report that shows missing or missed words with no way to study them is a dead end (product review
P2). Practice has no "practise these specific words" input (`routes/practice.py:44-80`; `/extra` takes
only an exclude list), so a true targeted drill is new work. But three existing paths already do most
of the job (MEASURED, [[features/knowledge-report.tech]] F18–F20):
- **Word-list import** (`POST /api/word-list/submit`, ≤ 50 words, 5 batches a day) puts words on the
  learner's watchlist so the vocabulary ladder shows them regularly, generating ladder exercises for
  senses that have none. Pricing already prices it: dictionary words free for Core and Pro, words not
  in the dictionary 8 credits each, and Pro's 300 monthly credits have few other uses.
- **Practice mode** (`/session?mode=practice`) serves today's queue and, when it is empty, offers an
  extra review round with reviews preselected (`static/js/session/controller.js:119`, `:1093-1112`).
- **Prestudy** computes a test's share of key words that are new (`services/prestudy.py:872-882`) and
  has a page per test; the owner named prestudy as a link target.

The draft's buttons also promised more than their targets do: "Review the 46 words due" opened a
Practice session that does not serve those 46, and "Practise {family}" landed on generic Practice.

## Decision
1. **"Add these {n} words to my word list"** (Pro Lists tab, buckets *no evidence* and *seen, not yet
   rated known*; Missed recently tab): posts up to 50 lemmas, most common first, to the existing submit
   endpoint and shows its own limits and errors. Words not in the dictionary get a separate,
   credit-priced button later (TASK-1060), once billing's credit path exists and the size question
   (OQ30) is answered.
2. **"Review in Practice"** links to `/session?mode=practice` with no number; an optional deep link
   (`&extra=reviews`) starts the extra review round when today's queue is empty (TASK-1043).
3. **"Prepare for {test}: {u} of its {n} key words are new to you"** links to `/test/<slug>/prestudy`
   for the top recommended reading or listening test when its share exceeds the 0.25 auto threshold
   (and, once TASK-980 exists, a weekly prestudy use remains). It comes from a separate endpoint so the
   summary never waits for the recommender.
4. The Skills comparison is informational; there is no "practise this kind of exercise" button.
5. A targeted drill of an explicit word set stays a separate, owner-gated task (TASK-1064).

## Consequences
- Easier: the paid view has a real study action in v1 at almost no new code, priced the way the
  pricing plan already prices imports; next steps never promise what their target does not do.
- Harder: imported words arrive through the ladder's schedule, not immediately; each tap uses one of
  the learner's five daily import batches; importing in-dictionary words that lack exercises makes the
  existing pipeline generate them, which adds database bytes (counted under OQ30).
- Constrained: report actions depend on the import, Practice and prestudy contracts; changes there must
  keep these entry points working.

## Alternatives Considered
- **Build targeted practice first:** the most direct action, but new Practice work blocked on scope;
  it would hold the Pro view back.
- **No actions in v1 (draft):** leaves list coverage and missed words as dead ends.
- **Numbered review button:** the Practice pool is a different set; the number would be false.
- **"Practise {family}" button:** nothing in Practice targets a family today.
