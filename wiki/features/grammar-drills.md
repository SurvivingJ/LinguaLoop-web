---
title: Chinese Grammar Drills
type: feature
status: in-progress
tech_page: ./grammar-drills.tech.md
last_updated: 2026-11-27
open_questions:
  - "GQ1 (OPEN): Should progress be synced to the server? Today it lives in one browser's localStorage; a second device or a cleared browser starts again (TASK-1239)."
  - "GQ2 (OPEN): Should grammar drills appear in the Study Plan / daily session, and should they feed ELO or any other learner model? Today they are a separate page with no link to either (TASK-1240)."
  - "GQ3 (OPEN): No native speaker has audited the content. Reviewer agents left borderline items in place and listed them in `data/grammar_drills/zh/review_concerns.md` (TASK-1241)."
  - "GQ4 (OPEN): Guides and per-item explanations are English only. Which other languages, and does that include the 10,209 `why` texts? (TASK-1242)"
  - "GQ5 (OPEN): The es / ja / zh interface strings for this page are machine translations nobody has reviewed (TASK-1243)."
  - "GQ6 (OPEN): The Recall time is self-reported: the clock stops when the learner taps \"Show choices\". Is that an acceptable basis for the \"instant\" badge? (TASK-1244)"
  - "GQ7 (OPEN): Generated sentences are grammatical but sometimes semantically flat. How much curation of the generator word lists is wanted? (TASK-1245)"
  - "GQ8 (OPEN): The Japanese particle counterpart is work in progress elsewhere and should reuse this contract; the script is hard-wired to `zh` today (TASK-1246)."
  - "GQ9 (OPEN): There is no audio. Is audio wanted, and from what source? (TASK-1247)"
  - "GQ10 (OPEN): The measure-words topic overlaps the existing database-backed Measure Word Trainer (`/classifier-drill`). Keep both, link them, or merge? (TASK-1248)"
---

# Chinese Grammar Drills

## Purpose

Grammar drills let a learner of Chinese practise one grammar point at a time (了, 把, 的/得/地,
measure words, word order and so on) until choosing the right form takes no thought. The feature
exists because some grammar is learned by repetition rather than by explanation: the owner's
request (2026-11-27) was for "a drill drill drill thing … drill them so it becomes instantaneous".

**State on 2026-11-27:** built on branch `claude/happy-gates-qp9ifs`; not deployed. Chinese only.

## User Story

As an English-speaking learner of Chinese at about HSK 1 to 4, I know the rule for 了 when I read
it, but I still hesitate or get it wrong when I have to produce it. I want a place where I can pick
one grammar point, read a short guide, and then answer a large number of short exercises on that
one point, getting faster, until the right form comes out at once.

## How It Works

1. **Open the page.** A Chinese learner finds "Grammar Drills" on the Me (profile) page. The link
   is shown only when the study language is Chinese.
2. **Hub.** The hub shows a "continue" card for the topic to work on next, a Mixed review button,
   two settings (pinyin, typed answers) and all 39 topics in seven groups: Aspect and time; 的 得
   地; Complements; Word order and constructions; Easily confused pairs; Particles and questions;
   Measures, verbs and connectors. Each topic shows its item count, the learner's current stage,
   recent accuracy and median answer time. A topic that is fully mastered carries an "Instant" tag.
3. **Topic screen.** Each topic has a guide (a summary, the rules with patterns and examples,
   wrong/right contrast pairs and a short cheat sheet) and four stage buttons. The learner starts
   a round at any stage that is open.
4. **A round** holds 20 items. There are four kinds of item:
   - **Fill the blank** — a sentence with a gap and two to four options.
   - **Build the sentence** — shuffled tiles to tap into the right order (some items have one or
     two tiles that must not be used).
   - **Rewrite** — a starting sentence and an instruction ("Rewrite with 把."), answered with tiles.
   - **Right or wrong?** — a sentence the learner judges as correct or not.
   After each answer the learner sees the correct sentence, its English meaning and a short
   explanation of the rule that decides this item.
5. **Missed items come back.** An item answered wrong returns three items later in the same round
   and keeps returning until it is answered right. Only the first answer to each item counts in
   the score.
6. **The four-stage ladder** (per topic):
   1. **Recognise** — fill-the-blank and right-or-wrong items only.
   2. **Build** — all four kinds; half the round is build and rewrite items.
   3. **Recall** — all four kinds, mostly fill-the-blank. The options are hidden: the learner
      thinks of the answer first, taps "Show choices" and then picks it from the item's own
      options, or (with the typed-answers setting on) types the missing word.
   4. **Speed** — like Recall, but every item has a countdown. It starts at 8 seconds, tightens by
      half a second after every five right answers in a row down to 4 seconds, and loosens by half
      a second after a miss. Build and rewrite items get 1.2 seconds more per tile. Running out of
      time counts as a miss.
   A stage opens the next one when the learner's last 30 answers at that stage are at least 85%
   correct. Opening a stage does not force the learner onto it; any open stage can be chosen.
7. **Instant.** A topic is "Instant" when the last 30 answers at the Speed stage are at least 90%
   correct with a median recall time under 3 seconds.
8. **Difficulty.** Items come in three levels. A topic starts at level 1; level 2 is added after
   ten answers at 75% and level 3 after thirty answers at 80%.
9. **What a round contains.** Items missed earlier come first (up to about a third of the round),
   then items never seen, then items seen long enough ago to be due again. The round is spread
   across the topic's sub-points.
10. **Pinyin on demand.** Pinyin is off by default. A button (or the P key) shows it above the
    characters.
11. **Mixed review** draws 20 items across the learner's five most recently practised topics, each
    at its own stage. It does not count toward opening stages.
12. **Endless mode** is offered for the 13 topics that have sentence generators. It mixes freshly
    generated items with the topic's written items, has no end, and shows a running streak. It
    does not count toward opening stages. The tone-change topic (不 and 一 tone sandhi, third-tone
    rules) has a guide and Endless mode only; it has no written items.

## Constraints & Edge Cases

- **Chinese only.** Simplified characters, mainland standard usage. A Japanese particle
  counterpart is being built elsewhere (GQ8).
- **Progress is per browser.** Nothing is saved to the account. Clearing site data, or using
  another device, starts from zero (GQ1). If the browser blocks storage the drills still work but
  nothing is remembered.
- **A reload ends the running round.** The page returns to the topic (or the hub for Mixed review).
- **No connection to the rest of the app.** Drills are not part of the daily session or Study
  Plan, do not change ELO, and do not appear in the Knowledge Report (GQ2).
- **Content has not been checked by a native speaker** (GQ3). It was written and reviewed by
  Claude agents; the reviewers' notes name items they judged odd but left in.
- **Explanations are in English** whatever the interface language (GQ4).
- **Recall time is self-reported** (GQ6): the learner decides when they have "thought of the
  answer".
- **Generated sentences** can be grammatical but dull or slightly odd in meaning (GQ7).
- **No audio** (GQ9).
- **Overlap:** the measure-words topic covers ground that [[features/measure-word-trainer]]
  already trains from the database (GQ10).

## Business Rules

- The content is static files shipped with the app. No drill item, guide or answer is stored in
  the database ([[decisions/ADR-064-grammar-drills-static-content-local-progress]]).
- A sentence is drilled once: the build leaves out any item whose sentence already appears in
  another item, whatever the item type (312 left out; 10,209 remain).
- Every fill-the-blank item must have exactly one acceptable option; every build item lists every
  other correct order of its tiles.
- Stage unlock: last 30 answers at the stage, at least 85% correct. Instant: last 30 Speed-stage
  answers, at least 90% correct, median recall time under 3 seconds.
- Only the first answer to an item in a round is recorded.
- Mixed review and Endless mode never open a stage.
- Content was produced with Claude subagents only: no OpenRouter and no Anthropic API key
  (owner instruction).

## Open Questions

- **GQ1 — OPEN.** Server sync of progress (TASK-1239).
- **GQ2 — OPEN.** Study Plan / daily session integration and ELO (TASK-1240).
- **GQ3 — OPEN.** Native-speaker audit of the content (TASK-1241).
- **GQ4 — OPEN.** Guide and explanation text in languages other than English (TASK-1242).
- **GQ5 — OPEN.** Review of the es / ja / zh interface strings (TASK-1243).
- **GQ6 — OPEN.** Self-reported Recall time (TASK-1244).
- **GQ7 — OPEN.** Semantic quality of generated sentences (TASK-1245).
- **GQ8 — OPEN.** Reuse of the contract for Japanese particles (TASK-1246).
- **GQ9 — OPEN.** Audio (TASK-1247).
- **GQ10 — OPEN.** Overlap with the Measure Word Trainer (TASK-1248).

## Related Pages

- [[features/grammar-drills.tech]] — technical specification
- [[decisions/ADR-064-grammar-drills-static-content-local-progress]] — why static files, client-side generators and localStorage
- [[tasklist/grammar-drills.tasks]] — TASK-1234 to TASK-1248
- [[features/measure-word-trainer]] — database-backed measure-word drill that overlaps the measure-words topic
- [[features/new-word-drill]] — the other "drill to a criterion" feature (vocabulary, database-backed)
- [[pages/pages-overview]] — route table (`/grammar-drill`)
