---
title: Grammar Drill and Reading Drill (Japanese)
type: feature
status: in-progress
tech_page: japanese-grammar-drill.tech.md
last_updated: 2026-11-27
open_questions:
  - "No human has checked a sample of the answer keys (TASK-1281)."
  - "Should the look-alike kanji skills get a typed rung through handwriting or an IME? Today a written form can only be chosen."
---

# Grammar Drill and Reading Drill (Japanese)

## Purpose
After the particle ladder the owner asked which other parts of Japanese could be drilled the
same way, and then: "build all of them, the same way." This is the result: a second course on
the same ladder for the grammar that is learned by choosing between look-alike options, and a
rule-generated drill for the things that are simply read (numbers, times, dates, katakana).

## User Story
As a learner of Japanese I know that あげる and くれる both mean "give", that 開く and 開ける both
mean "open", and that 4月 is not よんがつ; but I still hesitate every time. I want to be drilled on
exactly those choices until the right one comes out without thinking.

## How It Works
**Grammar (`/grammar-drill`).** The page looks and behaves like the particle drill: a hub with
stages, a guide for every skill, six rungs to Instant, a daily mix, and other skills mixed into
each drill so the answer is never obvious. It has 182 skills in twelve stages:

1. Giving and receiving (あげる, くれる, もらう, their て-forms and polite forms)
2. Transitive and intransitive pairs (開く / 開ける, 始まる / 始める …, and ている / てある)
3. Keigo (special honorific and humble verbs, お〜になる, お〜する, させていただく, set phrases)
4. こ・そ・あ・ど and question words (これ / それ / あれ, 何か / 何も / 何でも)
5. Connectors (しかし, だから, それなのに, つまり, ただし …)
6. Adverbs that set up the ending (全然〜ない, きっと〜だろう, まるで〜よう, たとえ〜ても)
7. Sound and manner words (どきどき, ぺらぺら, ぐっすり, ぴったり)
8. Conditionals in depth (と, ば, たら, なら and where each is not allowed)
9. Sentence patterns I, N5 to N4 (〜てもいい, 〜たことがある, 〜ておく, 〜ようになる …)
10. Sentence patterns II, N4 to N2 (そうだ / ようだ / らしい, わけ / はず / もの / こと, 〜ざるを得ない …)
11. Kanji readings in context (the word is shown, its reading is asked)
12. Look-alike kanji and spelling (the reading is shown, the written form is chosen)

A skill that covers a set of words (あげる / くれる / もらう; a family of connectors) rotates its
answers over the set, so even a single skill is a real choice. The blank holds what the learner
must produce: an ending when every option fits the same stem, the whole conjugated word when
the options need different stems.

**Numbers and kana (`/reading-drill`).** The learner picks what to read: numbers to 999, big
numbers (千, 万), prices, clock times, dates, durations and ages, and katakana loanwords. Every
number, time and date is generated, so the practice never runs out. Three rungs, as in the
conjugation drill: Choose, Type (in romaji or kana), Speed. Wrong options are the mistakes
learners really make (さんひゃく for 300, よんがつ for 4月, ろくふん for 6分). A wrong answer shows
the reading, its accepted variants and the rule of that category. Katakana words are matched to
their meaning, from a reviewed list of 609 words.

## Constraints & Edge Cases
- **Kanji skills have a shorter set of exercise types.** A reading is chosen, typed, then chosen
  against the clock. A written form can only be chosen (there is no handwriting input).
- **Reading questions do not show the answer's kanji in the options**, and look-alike questions
  show the options without furigana; the furigana appears after the answer.
- **Accepted variants.** しちじ / ななじ, じゅっぷん / じっぷん, はっぷん / はちふん, よえん / よんえん,
  はたち / にじゅっさい and similar are all accepted when typed; only non-standard forms are used
  as wrong options.
- **Japanese only**, English explanations, like the particle drill.
- **Progress** is shared with the particle drill: one record per learner, kept in the browser and
  (once the progress table is applied, TASK-1273) on the account.

## Business Rules
- Every sentence, guide and word list was written by one headless Claude Code worker and checked
  by a second in a separate context. No model API key and no OpenRouter were used.
- A wrong option must be plainly wrong in its sentence, and must be a well-formed word: the
  learner fails by choosing the wrong expression, not by spotting a misspelling.
- Skill ids are unique across both courses.

## Open Questions
- OPEN: native-speaker spot check of the answer keys (TASK-1281).
- OPEN: a typed rung for written forms.

## Related Pages
- [[features/japanese-grammar-drill.tech]] — technical specification
- [[features/particle-drill]] — the first course, the ladder and the authoring pipeline
- [[decisions/ADR-067-particle-drill-static-content-client-engine]] — why the content is files
- [[tasklist/japanese-grammar-drill.tasks]]
