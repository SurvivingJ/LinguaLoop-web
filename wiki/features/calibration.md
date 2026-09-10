---
title: Calibration
type: feature
status: in-progress
tech_page: calibration.tech.md
last_updated: 2026-09-08
open_questions:
  - "OPEN: some dictionary entries define a phrase rather than the bare lemma. Contained by a blocklist, not fixed (TASK-757)."
  - "OPEN: the 0.75 cosine ceiling is provisional. It needs response data to set properly — see [[decisions/ADR-025-semantic-distractor-selection]]."
---

# Calibration

## Purpose

A standalone mode that measures how much vocabulary a learner actually knows, by showing a
word and four candidate meanings and asking which one is right. It is a measuring instrument,
not a lesson — nothing is taught, and it sits outside session planning entirely.

## User Story

> I have been studying Japanese on and off for two years and I have no idea where I actually
> stand. I do not want a lesson, I want a number. Give me words until you know how much I
> know.

A learner opens Calibration from the nav, picks the language they are studying, and answers
multiple-choice items one after another for as long as they like. Each item shows one word and
four definitions written in the language they read most comfortably.

## How It Works

1. The learner picks a study language. Their interface language decides which language the
   definitions are written in — an English speaker studying Japanese sees Japanese words and
   English definitions.
2. The system picks a word and shows its correct definition alongside three wrong ones.
3. The learner picks one, or says "I don't know". The right answer is shown either
   way — being told the answer is the only thing an item they could not do gives
   back — and the next item appears immediately.
4. Items keep coming; there is no fixed test length and no session plan behind it.
   The learner presses Finish when they have had enough.

The words are **not** drawn at random. They are spread evenly across frequency
bands, from very common to quite rare, because the useful thing to learn is not an
average score but *where a learner's vocabulary stops*. You cannot find that edge
without asking words on both sides of it.

The whole design rests on the three wrong options being **hard**. If they are random, a learner
who has never seen the word can still eliminate two of them on general knowledge, and the item
measures nothing. So the wrong options are chosen to be:

- **semantically near** the right answer — a plausible neighbouring meaning, not a different
  subject entirely. For 予期 ("expectation"), the wrong options are 予測 ("prediction"),
  心待ち ("eager anticipation") and 予報 ("forecast").
- **matched in difficulty** — a rare word's options are other rare words, so option
  familiarity does not give the answer away.
- **never a restatement of the right answer**, and never another definition of the same word.

## What It Tells You

The result is not a single score but a **curve**: how often the learner knew words
at each frequency level. From that, the headline figure is the frequency level at
which they still know 85% of words — a smaller number means a larger vocabulary,
because they hold up further into rarer words.

The curve is shown next to the headline figure on purpose. A number derived from
six answers should not look like a number derived from eighty, and showing the
evidence is the honest way to make that visible.

The headline figure is shown with its uncertainty — `4.31 ± 0.24`, not a bare
number. That is not decoration: after about sixty answers the figure is still good
to roughly a quarter of a frequency point, and a two-decimal number on its own
reads far more precise than the measurement actually is. Answer more words and the
range narrows.

When there is not enough evidence to say anything — too few answers, or answers
showing no relationship between word frequency and success — no figure is shown at
all, rather than a confident-looking one derived from noise.

## Constraints & Edge Cases

- **A word's own other definitions are its closest semantic neighbours.** Because each
  definition is embedded together with its own headword, the three nearest "neighbours" of
  基本 are three more definitions of 基本. They are excluded explicitly; without that, every
  wrong option would be correct.
- **"Near" is not one distance.** Two random unrelated Japanese definitions look far more
  alike than two random unrelated English ones (21% versus 4% clear the same similarity
  threshold). Each language pairing therefore has its own floor, measured rather than assumed.
- **Some options are still arguably correct.** Genuine synonyms — 因子 and 要因 both mean
  "a factor" — cannot be told apart from good distractors by similarity alone. This is a known
  and accepted limit; it needs real answer data to fix, and is the first thing Calibration's
  own results should be used for. See [[decisions/ADR-025-semantic-distractor-selection]].
- **A few dictionary entries are themselves broken.** The entry for "hand" is defined as
  "closely connected or associated with something else" — that defines *hand in hand*. The
  picker behaves correctly and the item is still bad. This is a dictionary problem to fix
  upstream.
- **Words with no definition in the reader's language cannot be shown.** As of 2026-09-08 this
  no longer excludes anything: all seven word/definition language combinations are fully
  covered.

## Business Rules

- The four options must be four **different words**, and four **different texts**.
- No option may be identical to the prompt word.
- No option may be another definition of the prompt word.
- Wrong options must be difficulty-matched where frequency data exists; where it does not,
  they are used anyway rather than discarded, but ranked below matched ones.
- Difficulty matching is relaxed **before** semantic closeness is. A wrong option that is
  tempting but badly frequency-matched beats having no option.

## Open Questions

- **OPEN** — The cosine ceiling is provisional pending response data.
- **OPEN** — Some dictionary entries define a phrase rather than the bare lemma.
  Kept out of Calibration by a blocklist, but not fixed at source.
- **ANSWERED** — Is the headline figure trustworthy? It was measurably optimistic by
  ~0.24 frequency points; that has been fixed and re-validated, and the remaining
  limit is *precision*, now reported alongside the figure.
- **ANSWERED** — Stopping rule: there is none. The run is infinite and the learner
  stops it. The result carries a confidence label (`none`/`low`/`medium`/`good`)
  derived from how many items were answered and how many bands have enough data,
  so "when is this trustworthy?" is reported rather than enforced.
- **ANSWERED** — Calibration does **not** write back to ELO or study planning. It
  writes only its own tables. A measurement that silently moved the thing it
  measures would be a feedback loop, not a calibration; wiring it in is
  the job of TASK-747 (the guarded rating writer, audited by TASK-746) and
  TASK-748 (selection), under their own guards.
- **ANSWERED** — Which language pairs are supported? All seven that exist
  (zh/zh, zh/en, zh/ja, en/en, ja/zh, ja/en, ja/ja). `es` is a UI locale, not a study language.

## Two Modes

**Meanings** shows a word and four definitions. **Readings** shows a word and four
pronunciations. They look alike and are completely different underneath: a good
wrong *meaning* is one that is semantically close, while a good wrong *reading* is
one that looks and sounds close. For 政治 (せいじ) the wrong readings are せいふ,
だいじ and せいぶ — one sound different each.

Readings mode is available for Chinese and Japanese only. English words in the
dictionary almost never carry a stored pronunciation (21 of 6,555), so the option is
visibly disabled rather than quietly missing.

## What Happens To The Result

The result does not stay in Calibration. It is written to a small record — the
frequency level the learner reaches, how confident that figure is, and the curve it
came from — which the test-selection system reads when choosing what to give them
next. Calibration never picks tests itself and never changes a learner's rating
directly; it publishes a measurement and stops there.

That separation is deliberate. A measurement that quietly moved the thing it
measures would be a feedback loop rather than a calibration, and the rules for
turning a measurement into a rating change (how big a change is allowed, how often,
and what happens when the two disagree) belong with the system that owns ratings.

Answers from **all** of a learner's runs in a language are pooled, not just the
latest, because more answers is the only thing that makes the figure more precise.
Meanings and Readings are kept apart rather than averaged — they measure different
abilities.

## Related Pages

- [[features/calibration.tech]] — technical specification
- [[decisions/ADR-025-semantic-distractor-selection]] — why distractors are chosen this way
- [[tasklist/calibration.tasks]] — task breakdown
- [[features/flashcards]] — uses the older random-distractor picker, unchanged
- [[database/schema.tech]] — `dim_word_senses`, `dim_distractor_bands`
