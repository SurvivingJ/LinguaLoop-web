---
title: Word-Upload Queue
type: feature
status: in-progress
tech_page: word-upload-queue.tech.md
last_updated: 2026-11-28
open_questions:
  - "Should a failed word tell the learner why (today the page shows only 'Can't add')?"
  - "Should the operator be notified when the queue grows (e.g. a daily count), or is checking `status` enough?"
---

# Word-Upload Queue

## Purpose
Learners can upload their own words on the Word List page. Instead of generating content for
those words inside the website, the words wait in a queue until the operator builds every
asset they need, using the same authoring skills as the rest of the content.

## User Story
As a learner, I type the words I want to practise and submit them. I see them straight away
on my list as "Queued", then "Being prepared", and once they are ready they join my vocabulary
ladder and the app starts looking for tests that use them.

As the operator, I see every uploaded word before it enters the dictionary, run my usual
authoring skills over just those words, and the system finishes them onto each learner's list.

## How It Works
1. The learner submits up to 50 words in one language. Each word is checked (right writing
   system, at most 40 characters) and stored in the queue. The page answers at once.
2. Straight after, the website looks each word up in the dictionary. A word that already has
   all of its content (definition, translation in the learner's language, practice exercises,
   audio) is finished immediately and appears on the learner's watchlist.
3. Every other word waits. The website re-checks the queue every hour and finishes any word
   whose content has appeared since.
4. The operator runs the queue script for a language. It adds missing words to the
   dictionary, then writes the to-do lists for the next missing step of every word (write
   definitions, write translations, write ladder exercises, record audio) and a plan saying
   which skill to run on each.
5. The operator answers those lists with the skills and uploads them, then runs the script
   again for the next step, until nothing is left.
6. When a word's last piece lands, it moves to the learner's watchlist and the app looks for an
   existing test at the learner's level that uses it.

The old behaviour, where the website itself generated exercises for a word in the background,
is still there as a switch (off by default).

## Constraints & Edge Cases
- The same learner submitting a word twice in one language queues it once.
- Two learners submitting the same word get one queue entry each; the operator builds the
  word's content once and both learners receive it.
- The translation is written in the learner's native language; English if they have not set
  one; none if they study their own native language.
- A word that cannot be split into a dictionary form, or that the operator rejects (not a
  real word, offensive), is marked "Can't add".
- Japanese words typed with an ending (食べた, 走ります) are stored under their dictionary form.
- Until the queue table exists in the database, submitting answers "unavailable, try later";
  the page itself still loads.

## Business Rules
- Nothing a learner types reaches the shared dictionary until the operator's run.
- No AI model is called by the website for uploads (in the default mode).
- A word joins the watchlist only once every asset exists, and only once per learner.
- Daily limit: 5 uploads a day per learner, counted from the queue itself.
- No credits are charged for uploads for now (owner, 2026-11-28).

## Open Questions
- OPEN: should a failed word show the learner its reason?
- OPEN: should the operator get a notification when words are waiting?

## Related Pages
- [[features/word-upload-queue.tech]]
- [[decisions/ADR-069-word-upload-queue]]
- [[tasklist/word-list-import.plan]] — the original upload feature (watchlist, match sweep)
- [[tasklist/word-upload-queue.tasks]]
- [[database/schema.tech]]
- [[api/rpcs.tech]]
