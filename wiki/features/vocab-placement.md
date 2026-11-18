---
title: Vocabulary placement
type: feature
status: planned
tech_page: ./vocab-placement.tech.md
last_updated: 2026-11-18
open_questions:
  - "PQ1 OPEN: For Chinese and Japanese, lead the ranges with 'meaning and reading' (default) or with 'meaning'?"
  - "PQ2 ANSWERED (owner, 2026-11-18): no exam-level output, 'not at the moment'. TASK-1090 stays parked."
  - "PQ3 ANSWERED for Chinese (owner, 2026-11-18): 'Yes, but only the existing tones, just wrong combos' — wrong options may be the right syllables with a wrong tone combination, using only syllable+tone pairs that exist in Mandarin (ADR-060). Japanese long-vowel/っ/ん/voicing variants were not asked about and stay unscored."
  - "PQ4 OPEN: Up to 4 extra questions per test, clearly labelled 'not scored', to check how the scoring behaves? Default: yes."
  - "PQ5 ANSWERED (owner, 2026-11-18): approved — placement answers are their own kind of evidence, written per word, never 'rated known' on their own, and words with the meaning but not the reading go to reading practice (ADR-059 accepted)."
  - "PQ6 OPEN: Offer the placement to English learners at launch (meaning only)? Default: yes, once the pre-launch simulation includes English."
  - "PQ7 OPEN: Offer it during onboarding, after asking 'Have you studied {language} before?' (no placement for 'No' or 'Only a few words')? Default: yes, skippable."
  - "PQ8 OPEN: Retakes. Default: any time, at most 3 starts per language per day, never the same words within 180 days; a retake is compared with the previous placement."
  - "PQ9 OPEN: Keep the report's quality labels (a placement alone is usually 'Rough')? Default: yes."
  - "PQ10 ANSWERED for Chinese and Japanese (owner, 2026-11-18): about 60 questions (about 7 minutes; no new word after 9 minutes of answering). English was not part of the question and stays at 40 (about 5 minutes) unless the owner says otherwise."
  - "PQ11 OPEN: Change the open-ended vocabulary check's meaning questions to match the placement (no reading under the word, no leading 'equivalent word' in Chinese/Japanese definitions), so both kinds of answer can be combined? Default: yes (TASK-1091)."
  - "PQ12 OPEN: Name: 'Vocabulary placement' (es 'Prueba de nivel de vocabulario', ja '語彙レベルチェック', zh '词汇水平测试'); needs native review."
  - "PQ13 OPEN: Japanese waits for its word-pool refresh and the readiness check. Default: yes."
  - "PQ14 OPEN: Chinese launches on today's word pool (3,623 words) before the Chinese pool refresh. Default: yes."
  - "PQ15 OPEN: Proceed although the database is at its size limit (about 20–25 KB per placement)? Default: yes."
  - "PQ16 OPEN: Exclude account 110fb390 (looks automated) from every validation. Default: yes."
  - "PQ17 OPEN: Use the learner's stated exam level as a starting guess? Default: not in v1."
  - "PQ18 OPEN: Does the placement replace the open-ended check in navigation? Default: no."
  - "PQ19 OPEN: May a placement move the learner's test level? Default: not until the report's OQ33 (how 'I don't know' is scored there) is answered."
  - "PQ20 OPEN: 'Practise these readings' for every tier in v1? Default: yes."
  - "PQ21 OPEN: Which of a word's dictionary rows a placement answer updates (the same row as the check, or the word's own-language row where its exercises live)? Default: the same row as the check; admission to practice uses the own-language row."
---

# Vocabulary placement

## Purpose
A short test, about seven minutes on a phone, that tells a new or returning learner which of the
words it asked they recognise, and estimates with an honest range how many of the vocabulary
check's words they recognise. For Chinese and Japanese it asks both the meaning and the reading
of each word, and for Chinese the reading includes the tones. It is the vocabulary check ([[features/calibration]]) made adaptive and given an
end.

## User Story
> I passed HSK 3 two years ago and I am Japanese, so I can guess the meaning of a lot of Chinese
> words from the characters. I want to see where I stand: which words I recognise with their
> pinyin and which only by their characters. I don't want to spend twenty minutes, and I don't
> want an app telling me I know 3,000 words because I can read kanji.

## How It Works
1. **Before it starts.** When the placement is offered during onboarding, the learner is first
   asked "Have you studied {language} before?". If they answer "No" or "Only a few words", there
   is no test. The placement stays on offer in My vocabulary for whenever they want it later.
   Otherwise the first screen says how long it takes (about 7 minutes
   for Chinese and Japanese, about 5 for English) and how to answer: "If you have no idea,
   choose I don't know. If you think you know it, answer."
2. **Each word is shown on its own, in characters only**, with no reading underneath. The learner
   picks its meaning from four, or chooses "I don't know". The four meanings are the vocabulary
   check's usual ones: the three wrong options are close in meaning to the right one and about as
   common.
3. **Chinese and Japanese: if the meaning was right, the same word asks for its reading next.**
   Chinese shows four pinyin spellings: the right one, the same syllables with the wrong tones,
   another word's pinyin with the same number of syllables, and that one with the wrong tones. Every
   syllable-and-tone shown exists in Mandarin; nothing is a made-up syllable. Because each set of
   syllables appears twice, the look of the options does not give the answer away, and the question
   tests the tones as well as the sounds. Japanese shows four kana readings that fit any kana already
   visible in the word. Words written only in kana have no separate reading, so their meaning is
   enough. Because a reading question
   only follows a right meaning, its appearance tells the learner the meaning was right. That is
   harmless, because the meaning answer is already locked in.
4. **Occasionally an extra question, clearly labelled "Extra question, not scored"**, follows a
   word. It may ask for the reading after a missed meaning, ask for a best guess after "I don't
   know", ask the learner to choose between the right reading and one that differs only in a long
   vowel, small っ, ん or voicing (Japanese), or, at the start of a later
   placement, ask again for the reading of a word answered right a week or more before. These questions never change
   the result. They tell the team whether the scoring's assumptions hold. There are at most 4 per
   test.
5. **The answers are revealed together** once a word is finished: the meaning, the reading, and
   which parts were right. A fully correct word moves on by itself; anything else waits for "Next
   word".
6. **The test adapts.** It starts with two words from each of seven frequency levels, commonest
   first. After that it asks more words where the learner's answers are mixed and fewer where they
   are clearly all known or all unknown, because that is where another answer narrows the result
   most.
7. **It ends by itself** after 60 questions for Chinese and Japanese (40 for English), or once 9
   minutes of answering have passed. From question 40 on it can also end earlier if the result is
   already narrow enough, which happens mostly for English-speaking beginners. The progress bar
   shows "about N minutes left". After the first 14 words and at least 20 questions, "Stop here and
   see your result" ends the test with a result, labelled "You ended early, so the range is wider".
   If the learner leaves, the test can be resumed for 24 hours. After that it is closed, and if it
   had enough answers, its result is shown on the next visit.
8. **The result**, in this order:
   - **Your answers (guesses included).** "Of the 39 words you were asked: 12 meaning and reading
     · 3 meaning and pinyin, not the tones · 4 meaning, not the reading · 20 not yet recognised."
     (The tones group is Chinese only.) Each group opens its word list with an action: "Practise
     these readings" for the tones and reading groups and "Learn these" for the last. A lucky
     guess can put a word in the wrong group, which is why the heading says guesses are included.
     For English: "recognised" and "not yet recognised".
   - **The range.** "Across the 3,623 Chinese words the check draws from, you recognised the
     meaning and the reading of about X–Y (rough estimate)", drawn as a band. If the lower end is
     0, it says "Most of the check's words are still new to you (fewer than {hi} of 3,623)".
   - **The gaps**, each shown only when it is clearly more than zero. Chinese first: "You also
     recognised the meaning and the pinyin, but not the tones, of about C–D more." Then: "You also
     recognised the meaning, but not the reading, of about A–B more."
   - **On a retake:** this placement's range next to the previous placement's, with "clearly up",
     "clearly down" or "not clearly different", then "Combined with your earlier answers" (a
     narrower range).
   - **What to do next:** practise the readings, learn the new words, start today's session, or
     narrow the range with the open-ended vocabulary check.
   - **How this works:** what was measured (recognising the right meaning or reading among four),
     how guesses and "I don't know" are counted, why it is a range, and, for Chinese, that the
     reading includes the tones.
9. On the day it is taken, the combined range matches the one at the top of **My vocabulary**
   ([[features/knowledge-report]]). Later answers change My vocabulary, while the placement result
   stays as it was. Daily practice uses the answers: words with a missed meaning become candidates
   to learn, words with the meaning but not the reading (or not the tones) get reading practice, and
   words with both
   are treated as probably known until practice checks them.

## Constraints & Edge Cases
- **A seven-minute test gives a wide range.** At the usual 95% confidence it is about ±14–18% of
  the check's word pool either way for "meaning and reading" (roughly ±550–630 Chinese words with
  tones, ±440–490 Japanese words), and about the same for meaning alone. Scoring the tones costs about
  2 points of the pool against testing the syllables only. That is the limit of four-option questions, not a defect,
  and the page says "Rough". Answering more words in the open-ended check narrows it.
- **The count is of the check's own word pool**, not of the language or of an exam list: 3,623
  Chinese, 3,175 Japanese and 3,754 English words today. The Chinese pool will grow when it is
  refreshed, and the result then says the pool changed.
- **No exam level** (the owner's choice for now). In simulation an estimated "HSK k" was within one level of the truth for
  only 3–41% of learners whose true level was HSK 2–5 (21–48% for N4–N2), usually placing them two
  or more levels too low. The displayed range always read "up to HSK k at most". The goal path
  keeps its measured word counts per level ([[decisions/ADR-054-exam-word-lists-in-storage]]).
- **It measures recognition**: choosing the right meaning or reading from four. It does not
  measure recalling a word, saying it, or hearing it.
- **Guessing.** A blind guess is right one time in four, and the score subtracts that on average.
  Real guesses are often half-informed. If readings can be partly guessed, the "meaning and
  reading" range may be a little high. The extra questions measure how much.
- **"I don't know" counts as not known.** If the learner partly knew those words, the true figure
  is higher. Learners who use "I don't know" a lot can score a little lower than learners who guess
  on the same knowledge.
- **Chinese tones are tested.** A learner who knows a word's syllables but not its tones is counted
  in "meaning and pinyin, not the tones", not in "meaning and reading". Someone who half-remembers
  tones gets some of those words counted as known; in simulation that made the count up to about
  2% of the pool too high. Tone changes that happen in speech (a third tone before another third
  tone; 一 and 不) are never used as wrong options, because they can be correct.
- **Japanese and Chinese speakers learning the other language** recognise many meanings through
  shared characters without knowing the word's sound. In simulation a meaning-only test over-stated
  Japanese speakers learning Chinese by about 1,000 words. The reading question corrects this. The
  "meaning, not the reading" figure is just the difference: for English speakers it is mostly
  readings they have forgotten or never learned.
- **Beginners** answer most questions with "I don't know". With English as their first language,
  about four in ten stop a few questions early. With Chinese or Japanese as their first language, almost
  none do. The onboarding question and "Stop here and see your result" are their way out.
- **Japanese needs a word-pool refresh first.** Today only half of the rarest Japanese words have a
  usable reading question. Japanese stays off until at least 90% of its words (80% of every
  frequency level) are ready, and until the ready words are shown to look like the rest.
- **A retake never repeats a word answered in the last six months.** Retakes are compared with the
  previous placement and also combined with it.
- **Very fast answering** (median under 0.8 s a word) is flagged on the result.

## Business Rules
- Every range carries a quality label; no single number, no exam level, no pass, fail or readiness
  claim.
- Copy says "recognised", never "know" on its own.
- Placement answers never make a word "rated known after a direct check" on their own.
- A meaning question never shows the word's reading, and no answer of a word is revealed before
  all of its questions are answered.
- No made-up words and no "do you know this word?" self-report. Every wrong meaning is a real word's
  meaning. Every wrong reading is a real word's reading or, for Chinese, a real reading with a wrong
  combination of tones, using only syllable-and-tone pairs that exist in Mandarin.
- Answers are combined only with answers to the same kind of question, in the same definition
  language.
- Unscored extra questions are always labelled as such and never change any result.
- No placement launches unless its answers actually reach practice, because the result screen says
  they do.

## Open Questions
PQ2, PQ3 (Chinese), PQ5 and PQ10 were answered by the owner on 2026-11-18; the rest are OPEN with
defaults. See frontmatter. The full list with defaults and reasons is in
[[features/vocab-placement.tech]] §22.

## Related Pages
- [[features/vocab-placement.tech]] — technical specification
- [[features/calibration]] — the vocabulary check it is built on
- [[features/knowledge-report]] — My vocabulary and the goal path, where the ranges appear
- [[decisions/ADR-057-adaptive-placement-with-conditional-reading]] — test design
- [[decisions/ADR-058-meaning-and-reading-recognition-pair-estimator]] — what the result claims and how it is scored
- [[decisions/ADR-059-placement-evidence-kind]] — how answers reach practice
- [[decisions/ADR-060-zh-placement-scores-tones]] — how Chinese tones are scored
- [[decisions/ADR-051-vocabulary-size-from-calibration-frame]] — the estimator it extends
- [[decisions/ADR-054-exam-word-lists-in-storage]] — exam lists and why no estimated level
- [[evaluations/vocab-placement-research-2026-11-18]] — research, simulation and review record
- [[tasklist/vocab-placement.tasks]] — task breakdown
