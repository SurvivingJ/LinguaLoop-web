---
title: Idiom Trainer (Chinese and Japanese)
type: feature
status: in-progress
tech_page: idiom-trainer.tech.md
last_updated: 2026-11-28
open_questions:
  - "No human has checked the idiom lists, the cards or the stories (TASK-1289). The owner chose not to have the lists pruned by a native speaker before authoring."
  - "Full tier: about 850 Chinese and 770 Japanese idioms. The owner asked for the core first (TASK-1290)."
  - "The page's own interface text is English only; the nav labels are translated."
---

# Idiom Trainer (Chinese and Japanese)

> **2026-11-28, full tier** (owner: "Write the full tier"). The sets were extended after their core
> entries, which kept their place and cards: Chinese **849** (成语 600, 惯用语 149, 俗语 100) and
> Japanese **768** (慣用句 450, 四字熟語 200, ことわざ 118), **1,617 idioms** in all with 9,702
> contexts and 3,234 misuses. **315 have a story** (zh 199: chengyu 162, sayings 22, colloquial
> 15; ja 116: four-character 51, idioms 41, proverbs 24), a much higher share than in the core
> because the idioms with classical origins sit in the second tier. New idioms are introduced by
> their rank within each chosen set. Three expressions were listed in two sets (半斤八两; 背水の陣,
> 漁夫の利) and are built once, in the earlier set. The counts in the text below are the core tier's.

## Purpose
Idioms are learned one at a time, as small stories, and what has to be practised is recognising
the situation that calls for one. This trainer gives every idiom a card and a short ladder of
questions that are always set in context.

## User Story
As a learner of Chinese or Japanese I meet 画蛇添足 or 腹が立つ in a drama and look it up, and a
week later I cannot use it. I want to know what it means, where it comes from, when it would
sound wrong, and then be asked about it in new situations until I reach for it by myself.

## How It Works
**The card.** Before the first question about an idiom the learner reads its card: the idiom and
its reading, what it means, what it says literally, **the story behind it when there is one**
(with the source named), how it is used (register, tone, the place it takes in a sentence), the
idioms it is confused with and how they differ, and three example contexts. The card can be
reopened from any wrong answer and from the list of a set.

**Five steps, then reviews.** Two right answers in a row move an idiom up a step.
1. *Meet*: it is shown in a context; choose what it means there.
2. *Recognise*: a new situation with the idiom left out; choose which of four fits.
3. *Complete*: the meaning and the first half; choose the second half.
4. *Right or wrong*: a sentence that uses it; half the time it is a misuse a learner would
   really write, and the reason is shown afterwards.
5. *Recall*: a situation described in English only; choose among six idioms.
6. *Mastered*: reviews after 1, 3, 7, 14, 30, 60 and 120 days, against a clock. A failed review
   sends the idiom back to step 4.

**A round** is about twelve questions: reviews that are due, then up to five idioms in progress,
each asked twice and never back to back. Every question uses a context that idiom was not just
shown in; each idiom has six contexts and two misuses.

**The sets (core tier).** Chinese, 320: 成语 chengyu (200), 惯用语 colloquial expressions (80),
俗语 sayings (40). Japanese, 332: 慣用句 idioms (200), 四字熟語 four-character idioms (80),
ことわざ proverbs (52). Each set is ordered most useful first, and the learner chooses which sets
a round draws from.

## Constraints & Edge Cases
- **Stories only where they are certain.** 98 of the 652 idioms have one (41 chengyu, 23
  four-character idioms, 10 proverbs, 10 Japanese idioms, 8 colloquial expressions, 6 sayings).
  The core lists are mostly everyday descriptive idioms (乱七八糟, 十人十色) that have no origin
  story; for those the literal image is the memory hook.
- **Wrong options are kept apart.** An idiom of the same theme, or one the card lists as a
  look-alike, is never offered as a wrong option, because it might fit.
- **Everything is chosen, nothing is typed.** Typing Chinese needs an input method the page
  cannot assume.
- **Progress** is kept in the browser and, once the shared tracking migration is applied
  (TASK-1259), on the account: one topic per idiom.

## Business Rules
- A story is included only when a real origin exists and the writer and the reviewer are both
  sure of it; it always names its source and is shown as a "traditional account". A wrong story
  is a defect; a missing one is not.
- Every list and every card was written by one headless Claude Code worker and reviewed by a
  second in a separate context, both on Opus (owner: "run on opus for authoring"). No model API
  key and no OpenRouter were used.
- Idioms are chosen for present-day use: nothing dated, bookish, regional or vulgar in the core.

## Open Questions
- OPEN: native-speaker check of lists, cards and stories (TASK-1289).
- OPEN: the full tier (TASK-1290).

## Related Pages
- [[features/idiom-trainer.tech]] — technical specification
- [[decisions/ADR-068-one-tracking-structure-for-every-language]] — where progress is recorded
- [[features/grammar-drills]], [[features/japanese-grammar-drill]] — the earlier, smaller idiom topics
- [[tasklist/idiom-trainer.tasks]]
