---
title: Particle Drill (Japanese)
type: feature
status: in-progress
tech_page: ./particle-drill.tech.md
last_updated: 2026-11-27
open_questions:
  - "OPEN (owner): apply migrations/grammar_drill_tracking.sql (shared with the Chinese drills, ADR-068) so ladder progress follows the learner across devices. Until then it stays in the browser."
  - "OPEN (owner): should particle drilling count towards Studied-this-week minutes, the daily session and ELO like the counter drill does? Today it counts towards none (TASK-1273, TASK-1274)."
  - "OPEN (owner): guides and the 'why' line of every exercise are English only. Translate for zh / es interface users? (TASK-1275)"
  - "OPEN (owner): the answer keys were written and reviewed by Claude subagents only. A native-speaker spot check of a sample is recommended before promoting the drill (TASK-1272)."
---

# Particle Drill (Japanese)

> **2026-11-28, depth:** every skill was topped up to at least 50 sentences (owner: "are there
> enough drills"). The particle course now has **14,568** sentences (was 10,549; the smallest skill
> had 20). 66 more batches, each written by one worker and reviewed by another; reviewers checked
> 4,046 new entries, corrected 944 and deleted 19. Counts elsewhere on this page are from the
> first run.

## Purpose

Particles decide who did what to whom in every Japanese sentence, and a learner only owns them
when the choice is made without thinking. This feature is a drill ground for exactly that: a
guide for every use of every particle, a bank of 10,549 written exercises, sentence
generators that never run out, and a ladder that keeps a skill in rotation until the answer is
instant. A conjugation gym sits beside it, because half the particles depend on the verb form
in front of them.

## User Story

A learner of Japanese opens **Particles** (wide-screen nav, the Practice page chips, or the Me
page). The page shows the next skill on their path, for example に for a point in time, plus
how many skills are in progress, due for review, or mastered. They read a one-screen guide:
the rule in one sentence, a short explanation, examples, what に is confused with, the mistakes
English speakers make, and a quick test. They press **Start drilling** and answer sentence
after sentence: a right answer moves on by itself in under a second, a wrong one stops, shows
the correct particle and the reason, and comes back three questions later. After ten questions
the round ends with the score, the pace and any rung gained, and one button starts the next
round. They can do this for five minutes or an hour; the questions do not run out.

## How It Works

**The catalog.** 245 skills in 138 particle groups and 10 stages. A skill is one
use of one particle (に for time, に for a destination, に for the person receiving something
are three skills). The stages run from the core case particles (は が を に へ で), through
linking and listing (の と も や か から まで より), contrast clinics (は or が, に or で, を or
が, transitive and intransitive pairs, a mixed set), focus particles (だけ しか ばかり ほど
…), clause connectors (から ので のに ても たら ば なら …), the particles that change with
the verb (giving and receiving, passive, causative, potential, wanting), sentence endings (ね
よ な かな っけ …), and three stages of compound particles from について to the written N1
set (をもって, といえども …). All skills are open from the start; the page only recommends
an order.

**The ladder.** Each skill climbs six rungs, and the exercise type changes with the rung:

1. **Meet** — choose from three, translation and furigana shown.
2. **Choose** — choose from four, translation hidden until answered.
3. **Type** — type the particle (kana, or plain romaji such as `wa`, `ni`, `made`).
4. **Fill all** — every particle in the sentence is blank; fill them from a bank.
5. **Fix** — the sentence contains one wrong particle; tap it, then correct it.
6. **Speed** — choose within six seconds; running out of time counts as wrong.

Five answers at a rung with a running accuracy of 80% move the skill up; sustained misses move
it down one rung. Passing Speed (eight answers at 85%, answered in about four seconds or less
on a running average) marks the skill **Instant**. An Instant
skill returns for a short speed review after 1, 3, 7, 14, 30, 60 and 120 days; failing a review
sends it back to rung 5. The learner can also force any exercise type from the guide page;
answers given that way are counted in the statistics but do not move the ladder.

**Endless practice.** Each skill draws from its written exercises in shuffled order, previously
missed sentences first. About three questions in ten are generated on the spot from a *pattern
pack*: a sentence frame whose parts (who, where, what) are swapped at random, with every
combination checked to keep the same answer. 278 packs give well over
100,000 distinct sentences. When the written exercises run out they are reshuffled,
so a round can always be followed by another.

**Other particles are mixed in.** In the first version a drill of one skill asked only that
skill, so the answer was the same particle every time and nothing had to be chosen (owner,
2026-11-27: "the answer is clear every time"). From the Choose rung up, about half the questions
of a one-skill drill now come from other particles: the ones the learner has already started,
and the skill's listed confusers that come earlier in the course. Never three questions of the
same kind in a row. The strip no longer names the particle or the skill until the answer is
given (this also applied to the daily mix, which used to print the answer above the sentence).
The Meet rung stays on its own particle, because that is where it is introduced. A mixed-in
skill is asked at its own rung and its answers count for its own ladder; one the learner has
not started is asked as a Choose question and does not move.

**Daily mix.** One button starts a 20-question session over up to six skills: reviews that are
due, then the skills in progress (weakest first, and asked more often), then one new skill.

**Conjugation drill (its own page, `/conjugation-drill`).** The drill starts from the words
the learner already knows: every verb and adjective their vocabulary record marks as known,
probably known or being learned is offered as the pool "Words I know", and it grows by itself
as they learn more. Level lists (N5, N4, N3 and above) can be switched on beside it, and are on
by default for a learner with fewer than eight such words. The learner picks forms (ます, て, た, ない, たい, たら, ば, volitional,
potential, passive, causative, causative-passive, imperative and more for verbs; negative,
past, て, adverb and conditionals for adjectives). A word and a target form
appear; the learner chooses, then types, then answers against the clock (three rungs per
form). Words come at random from the chosen pools (the level lists hold 378 verbs and
254 adjectives), every form is computed by rule so the practice never runs out, and the wrong options are the mistakes learners really make (treating
帰る as a る-verb, the wrong て sound change). Each of the 21 conjugation guides opens from
the setup page and from the feedback after a miss.

## Constraints & Edge Cases

- **Japanese only.** The page is reachable for other study languages only by URL, and the API
  answers 400 for them.
- **More than one right particle.** Where another particle is equally natural (に or へ for a
  destination), both are accepted, in every exercise type. Wrong options are particles a
  reviewer judged plainly wrong in that sentence, not merely less common.
- **Typing without a Japanese keyboard.** Romaji turns into kana as it is typed. は, へ and を
  are accepted by their sound (`wa`, `e`, `o`) as well as by their spelling.
- **Compound particles** are shown in their normal kanji spelling with furigana (に対して) and
  accepted in kanji, kana or romaji when typed.
- **Words the conjugation drill leaves out.** A known word is skipped when rule-based
  conjugation would be wrong or doubtful for it: the honorific verbs (いらっしゃる, くださる …),
  問う, single-kanji する verbs (愛する), ～ずる verbs and multi-word expressions.
- **Short sentences.** A sentence with a single particle cannot be a Fill-all exercise; it is
  asked as Type instead.
- **Progress is per device until the migration is applied.** It is kept in the browser; with
  the progress table in place it is also saved to the account and merged on the next visit
  (the copy with more answers for a skill wins).
- **Two tabs.** The last tab to save wins for a skill answered in both.
- **Furigana** can be switched off on the ladder page.

## Business Rules

- The answer key of a written exercise is fixed content: the page never calls a model.
- Every content file was written by one subagent and checked by a second one in a separate
  context, and passes the deterministic validator; a file without a review record fails the
  test suite.
- A manually chosen exercise type never moves the ladder.
- A missed sentence is asked again within the same round and is the first one served the next
  time the skill is drilled.
- Counts shown on the page (written exercises per skill) come from the content manifest, which
  must match the files (tested).

## Open Questions

- OPEN — apply the progress migration (owner).
- OPEN — count particle drilling in weekly minutes, the daily session and ELO?
- OPEN — translate guides and reasons for non-English interfaces?
- OPEN — native-speaker spot check of the answer keys.

## Related Pages

- [[features/particle-drill.tech]] — technical specification
- [[features/japanese-grammar-drill]] — the second course on this ladder, and the reading drill
- [[features/knowledge-report]] — the vocabulary record the conjugation drill reads
- [[decisions/ADR-067-particle-drill-static-content-client-engine]] — why the content is files and the engine runs in the browser
- [[tasklist/particle-drill.tasks]] — tasks, done and open
- [[features/measure-word-trainer]] — the Chinese measure-word drill and the Japanese counter drill (the sibling trainers)
- [[algorithms/vocabulary-ladder]] — the vocabulary ladder this ladder is modelled on
- [[features/new-word-drill]] — criterion-based drilling for vocabulary
