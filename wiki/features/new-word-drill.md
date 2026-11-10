---
title: New-Word Drill (criterion-based intro sessions)
type: feature
status: in-progress
tech_page: ./new-word-drill.tech.md
last_updated: 2026-11-10
open_questions:
  - "ANSWERED 2026-11-09: schedule = Option B (successive relearning), targets 5 / 3 / 2 / 2 counted correct answers, +1 when the cold recall that opens sessions 2–4 is missed."
  - "ANSWERED 2026-11-09: new_words_per_day default raised to 10 (was 5)."
  - "ANSWERED 2026-11-09: tight schedule, sessions on day 0, 1, 2 and 4."
  - "ANSWERED 2026-11-09: the four intro sessions REPLACE ladder ring 1; finishing session 4 puts the word in ring 2."
  - "ANSWERED 2026-11-09: words drilled in test prestudy enter the ladder (reverses the 2026-10-29 'prestudy never admits' decision); the prime counts as session 1 when it meets the session-1 criterion."
  - "ANSWERED 2026-11-09: prestudy words count against new_words_per_day. When a prime drills more words than today's remaining quota, the learner is told and chooses: queue the extra words for later days (default) or add them all now (overload)."
  - "ANSWERED 2026-11-09: existing plans move to 10 too (rows still at the old default of 5 are updated; any other value was the learner's own choice and is kept)."
  - "ANSWERED 2026-11-09: a demoted ring-2 word makes a full restart at intro session 1."
---

# New-Word Drill (criterion-based intro sessions)

## Purpose

Give every new word a short burst of heavy, varied drilling over its first few days before it
joins the normal vocabulary ladder. Today a new word gets **one** question on its first day and
one a day after that. The prestudy word prime showed that drilling a word five or more ways,
spaced between other words, makes it stick. This feature brings that to every new word, on a
schedule that tapers off.

## User Story

> When I meet a new word I want it hammered into me — not shown once and left to the spaced
> repetition schedule. Drill it until I get it right several times, in different ways, and then
> drill it a bit less on the next few days.

## How It Works

### Four intro sessions, each "until right N times"

A new word goes through four short intro sessions inside the normal daily practice session:

| Session | When | Correct answers needed | What the questions look like |
|---|---|---|---|
| 1 | The day the word is introduced (day 0) | **5** | Type the reading → pick the meaning → type the reading again → pick the word from its meaning → fill the gap in a sentence (the five prestudy stages) |
| 2 | Next day (day 1) | **3** (4 if the first question is missed) | Starts with a cold typed recall with no hints, then real ladder exercises |
| 3 | Day 2 | **2** (3 if the first question is missed) | Cold typed recall, then an exercise type the word has not had yet |
| 4 | Day 4 | **2** (3 if the first question is missed) | Cold typed recall, then a production item (type the word into a sentence, or translate) |

After session 4 the word joins the ladder at **ring 2**. The intro sessions replace ring 1,
whose two exercise types (sound recognition and definition match) the drill already covers.

### What counts as a "correct answer"

The target is counted, not the number of questions asked. A right answer only counts when:

- **the word was not just on screen.** At least 4 other questions came since this word was last
  asked (fewer when the drill has fewer than 5 words, padded with other practice items where
  possible). A right answer seconds later shows short-term memory, not learning.
- **the format is different** from the last counted answer for that word. Five right answers to
  the same multiple-choice question do not count as five.
- **it was not "I don't know".** That button shows the answer as a lesson and brings the word
  back a few questions later, as in prestudy.

Wrong answers bring the word back 3–5 questions later. Easy words finish in about as many
questions as the target. Hard words get more, up to a cap per session (12 in session 1, 8 in
session 2, 6 in sessions 3 and 4). A word that hits the cap without reaching its target repeats
that session the next day instead of moving on.

### Starting the later sessions cold

Sessions 2–4 always start with a typed recall with no options and no hints:

- **Japanese and Chinese:** see the word, type its reading.
- **English:** see the meaning in the learner's language, type the word.

This is the most honest check of whether the word survived the gap. Missing it raises that
session's target by one.

### Where it happens

- The intro drill runs as a block inside the daily practice session, before the rest of the
  practice items.
- In "Practice" mode (exercises only), sessions 2–4 count as reviews and run as normal.
  Session 1 is for new words, so it is offered afterwards with the existing "Learn new words"
  prompt.
- Words drilled in **test prestudy** also enter the schedule. If the prime met session 1's
  target, prestudy *was* session 1, and session 2 is due the next day.

### How much time it takes

About 17 questions per word across the four sessions (≈ 7 + 4 + 3 + 3, allowing for misses).
At **10 new words a day**, a normal day carries four groups at once: today's new words plus the
groups from 1, 2 and 4 days ago. That is about 40 words and **roughly 170 questions, 25–30
minutes**, before any ring-2+ ladder practice or reviews. The existing review-load governor
cuts new words when the backlog grows. The session time estimate must include the intro block
so the plan stays honest.

## Constraints & Edge Cases

- **Missed days:** a session that is due stays due. The next session is scheduled from the date
  the previous one was *finished*, not from the date it was due. A longer gap makes the cold
  recall harder, and a miss there automatically raises the target.
- **Words without a reading** (most English words) skip the typed-reading formats and use typed
  recall from the meaning instead.
- **Words with no ladder exercises yet** can still start: session 1 needs only the word, its
  reading, its gloss and an example sentence. Exercise generation is requested when the word is
  admitted, so exercises are usually ready by session 2. Until then, sessions 2–4 fall back to
  the cheap formats.
- **Small drills:** when only 1–3 words are in the intro block, the spacing rule is met by
  placing other due practice items between repeats. If nothing else is due, the gap shrinks to
  what is possible and the session target stays the same.
- **Legacy words** already on ring 1 when this ships keep the old ring-1 path. Only newly
  admitted words use the drill.
- **Falling back from ring 2:** a word that is demoted from ring 2 (three first-try misses in a
  row on a ring-2 skill) makes a **full restart** of the intro at session 1. Words demoted from
  ring 3 or 4 stay on the ladder, as today. A mastered word that lapses follows the existing
  relearning path, not the intro.

## Business Rules

- A word is either in intro (sessions 1–4) or on the ladder (rings 2–4, or mastered), never both.
- Intro words are not served as ordinary ladder exercises.
- Only one knowledge-score update per word per intro session. Repeated right answers in one
  session must not inflate the word's score; the ladder's existing rule that a ring needs
  successes on 2 different days still applies after the intro.
- Prestudy words that enter the drill count against today's new-word quota.
- **Overload is the learner's choice.** When a prime drills more words than today's remaining
  quota, the end of the prime shows a notice: how many words fit, how many are over, and roughly
  how many extra minutes a day the overload adds for the next four days. Two buttons: **Queue the
  rest for later** (default: the extra words go to the front of the new-word queue for the coming
  days) or **Add them all now**. Overloaded words start their intro today like any other word. The
  review-load governor still reduces *future* new-word intake if the backlog grows.

## Research basis

See [[decisions/ADR-040-criterion-based-new-word-drill]] for the evidence. In short:

- About 10+ encounters are needed to learn a word (Webb 2007; Uchihara, Webb & Yanagisawa 2019).
- 5–7 retrievals in a session beat 1–3, with diminishing returns (Nakata 2017).
- Drilling to a target and then relearning across sessions works better than piling reps into
  one session (Rawson & Dunlosky 2011; overlearning fades, Rohrer et al. 2005).
- Repeats should be spaced within the session (Kornell 2009; Nakata, Suzuki & He 2022), and
  harder successful recalls teach more (Pyc & Rawson 2009).
- Form before meaning-heavy work for brand-new words (Barcroft, TOPRA); varied formats
  (Nation & Webb); adaptive retirement beats fixed counts (Mettler, Massey & Kellman 2016).

## Open Questions

All answered 2026-11-09 (see frontmatter).

## Related Pages

- [[features/new-word-drill.tech]] — technical specification
- [[decisions/ADR-040-criterion-based-new-word-drill]] — the decision and its evidence
- [[tasklist/new-word-drill.tasks]] — task breakdown (TASK-912–921)
- [[features/test-prestudy]] — the word prime this drill is built from
- [[algorithms/vocabulary-ladder]] — ring 1 is replaced by this drill
- [[features/practice-engine]] — the session that hosts the drill
- [[decisions/ADR-033-budget-scope-and-new-word-budget]] — the new-word quota
