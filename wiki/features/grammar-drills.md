---
title: Chinese Grammar Drills
type: feature
status: in-progress
tech_page: ./grammar-drills.tech.md
last_updated: 2026-11-27
open_questions:
  - "GQ2 (OPEN): Should grammar drills appear in the Study Plan / daily session, and should they feed ELO or any other learner model? Today they are a separate page with no link to either (TASK-1260)."
  - "GQ3 (OPEN): No native speaker has audited the content. Reviewer agents left borderline items in place and listed them in `data/grammar_drills/zh/review_concerns.md` (TASK-1261)."
  - "GQ4 (OPEN): Guides and per-item explanations are English only. Which other languages, and does that include the 10,209 `why` texts? (TASK-1262)"
  - "GQ5 (OPEN): The es / ja / zh interface strings for this page are machine translations nobody has reviewed (TASK-1263)."
  - "GQ6 (OPEN): The Recall time is self-reported: the clock stops when the learner taps \"Show choices\". Is that an acceptable basis for the \"instant\" badge? (TASK-1264)"
  - "GQ7 (OPEN): Generated sentences are grammatical but sometimes semantically flat. How much curation of the generator word lists is wanted? (TASK-1265)"
  - "GQ8 (OPEN): The Japanese particle counterpart is work in progress elsewhere and should reuse this contract; the script is hard-wired to `zh` today (TASK-1266)."
  - "GQ9 (OPEN): There is no audio. Is audio wanted, and from what source? (TASK-1267)"
  - "GQ11 (OPEN): A daily tracking row costs about 246 bytes with its index, not the 150 budgeted; the sub-point keys are the difference. Accept, or store sub-point misses more compactly? (ADR-066)"
  - "GQ12 (OPEN): How long are daily tracking rows kept? The page reads the last 180 days; nothing deletes older rows."
  - "GQ10 (OPEN): The measure-words topic overlaps the existing database-backed Measure Word Trainer (`/classifier-drill`). Keep both, link them, or merge? (TASK-1268)"
---

# Chinese Grammar Drills

## Purpose

Grammar drills let a learner of Chinese practise one grammar point at a time (了, 把, 的/得/地,
measure words, word order and so on) until choosing the right form takes no thought. The feature
exists because some grammar is learned by repetition rather than by explanation: the owner's
request (2026-11-27) was for "a drill drill drill thing … drill them so it becomes instantaneous".

**State on 2026-11-27:** built on branch `claude/happy-gates-qp9ifs`; not deployed. Chinese only.
Progress tracking (daily history on the server, stages across devices, progress views) was built
the same day; its database migration is not applied yet
([[decisions/ADR-066-grammar-drill-daily-tracking]]).

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

### Progress over time (2026-11-27; needs the tracking migration)

After each finished round, Mixed review or stopped Endless session, the page sends that session's
totals to the server: per topic, how many items were answered and how many were right first time,
how long the right answers took, and which sub-points were missed. A session left part-way sends
what was answered. If the send fails (offline, signed out) it waits in the browser and is sent on
a later visit; the server counts it once.

On opening the page, the learner's stages and totals are fetched and merged with what the browser
has: the higher unlocked stage wins, and the more recent of the two sets of recent results. So a
second device continues at the same stage.

Two views appear once there is history:

- **Topic screen, "Progress" card.** Accuracy and average recall time for each day the topic was
  practised (the last 30 such days), each as a small line with the latest value in figures and
  the change since the first week in words (since the first day while still in the first week).
  Below it, "Needs work": the three sub-points missed most in the last 14 days. One recorded day
  shows the figures and a note that a trend needs a second day.
- **Hub, "Your progress".** Days practised in the last 30, total answers, the number of topics
  that are instant, and a strip of the last 30 days shaded by how much was practised.

Without a server history (not signed in, offline, tracking not applied) neither view is drawn
and the page is as before.

## Constraints & Edge Cases

- **Chinese only.** Simplified characters, mainland standard usage. A Japanese particle
  counterpart is being built elsewhere (GQ8).
- **Progress follows the account once tracking is applied** (built 2026-11-27, migration
  pending: TASK-1259). Stages, recent results and totals are copied to the server after each
  session and merged on load. Until the migration is applied, or when the learner is signed out
  or offline, progress is per browser as before, and nothing is shown about it. The per-item
  review schedule always stays in the browser: a new device knows the stage but treats every
  item as unseen. If the browser blocks storage the drills still work but nothing is remembered
  locally.
- **Progress history is by day.** The server keeps one summary per topic and day, never single
  answers. History starts when tracking is applied; earlier practice is uploaded as the current
  state only.
- **A reload ends the running round.** The page returns to the topic (or the hub for Mixed review).
- **No connection to the rest of the app.** Drills are not part of the daily session or Study
  Plan, do not change ELO, and do not appear in the Knowledge Report (GQ2). The tracking above is
  the feature's own.
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
  the database ([[decisions/ADR-065-grammar-drills-static-content-local-progress]]).
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
- Tracking keeps daily summaries and one state row per topic; never a row per answer or per item
  ([[decisions/ADR-066-grammar-drill-daily-tracking]]). The database stop line is 480 MB.
- A day is the app's review day (Sydney time), the same day the flashcards use.
- A finished session is counted once, however often the browser has to resend it.
- Local progress is never lost to the server copy: the unlocked stage and the totals only go up.
- A failure of tracking is never shown to the learner and never blocks a drill.

## Open Questions

- **GQ1 — ANSWERED 2026-11-27.** Yes: daily summaries plus a state row per topic, owner decision "Do daily with the current space limit raised to 480mb" ([[decisions/ADR-066-grammar-drill-daily-tracking]]). Built; the migration is pending (TASK-1259).
- **GQ2 — OPEN.** Study Plan / daily session integration and ELO (TASK-1260).
- **GQ3 — OPEN.** Native-speaker audit of the content (TASK-1261).
- **GQ4 — OPEN.** Guide and explanation text in languages other than English (TASK-1262).
- **GQ5 — OPEN.** Review of the es / ja / zh interface strings (TASK-1263).
- **GQ6 — OPEN.** Self-reported Recall time (TASK-1264).
- **GQ7 — OPEN.** Semantic quality of generated sentences (TASK-1265).
- **GQ8 — OPEN.** Reuse of the contract for Japanese particles (TASK-1266).
- **GQ9 — OPEN.** Audio (TASK-1267).
- **GQ10 — OPEN.** Overlap with the Measure Word Trainer (TASK-1268).
- **GQ11 — OPEN.** A daily row costs about 246 bytes, not the 150 budgeted. Accept, or store sub-point misses more compactly?
- **GQ12 — OPEN.** Retention of daily rows (the page reads 180 days; nothing deletes older rows).

## Related Pages

- [[features/grammar-drills.tech]] — technical specification
- [[decisions/ADR-065-grammar-drills-static-content-local-progress]] — why static files, client-side generators and localStorage
- [[decisions/ADR-066-grammar-drill-daily-tracking]] — server-side daily summaries and state; the 480 MB line
- [[tasklist/grammar-drill-tracking-runbook]] — apply steps and the owner's SQL queries
- [[tasklist/grammar-drills.tasks]] — TASK-1254 to TASK-1268
- [[features/measure-word-trainer]] — database-backed measure-word drill that overlaps the measure-words topic
- [[features/new-word-drill]] — the other "drill to a criterion" feature (vocabulary, database-backed)
- [[pages/pages-overview]] — route table (`/grammar-drill`)
