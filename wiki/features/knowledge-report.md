---
title: Knowledge Report ("My vocabulary")
type: feature
status: planned
tech_page: ./knowledge-report.tech.md
last_updated: 2026-11-18
open_questions:
  - "OQ1 OPEN: UI name. Default 'My vocabulary' (es 'Mi vocabulario', ja 'わたしの語彙', zh '我的词汇'), because 'Report' already means 'Report an issue'. Native review needed."
  - "OQ2 OPEN: Which HSK list: the November 2025 CLEC syllabus (default) or the 2021 national standard? 41.5% of shared words differ in level."
  - "OQ3 OPEN: Are the list licences acceptable (HSK file CC BY-SA 4.0; JLPT Waller CC BY, confirmed second-hand), and may list subsets be exported? Default: load both with attribution; JLPT subsets exportable, HSK subsets not until share-alike is accepted."
  - "OQ4 OPEN: Before billing is enforced, do Free and Core learners see the word-by-word view as a preview? Default: yes, with a 'part of Pro when plans launch' note."
  - "OQ5 OPEN: May Calibration add forced-choice probe items (or a second skip button) to measure what 'I don't know' hides? Default: skips count as not known; the probe is proposed, not built."
  - "OQ6 OPEN: Is account 110fb390 a test/automated account? Default: yes; excluded from validation, but its report is still shown to it."
  - "OQ7 OPEN: Accept that 30/90-day growth starts at the first nightly snapshot (no back-fill)? Default: yes; snapshots ship first."
  - "OQ8 OPEN: Estimate thresholds: at least 10 check answers per frequency band (Rough), 20 (Medium), 30 (Good), 180-day window? Default: as stated."
  - "OQ9 OPEN: Change the vocabulary check to sample words (not meanings) so English estimates need fewer answers? Default: no change in v1."
  - "OQ10 OPEN: Snapshot day: UTC date (default) or the learner's local day?"
  - "OQ11 OPEN: Confirm how drill (intro) exercise formats are labelled when shown on a missed word."
  - "OQ12 OPEN: Is a word's first-ranked meaning reliably its most common meaning? Default: yes for v1."
  - "OQ13 OPEN: Is the database cap 500 MiB or 500,000,000 bytes? Since 2026-11-18 the exam lists do not depend on it (they are files in Storage, ADR-054). It still decides when the Chinese word-pool refresh (OQ29), seeding missing JLPT words (OQ31) and database growth from 'Add these words' (OQ30) may go ahead. Default: those wait until the database is at or below 490,000,000 bytes (or a 500 MiB cap is confirmed)."
  - "OQ14 OPEN: Approve the clean-up of the decay functions (wrong volatility, broken two-argument version)? Not needed by the report."
  - "OQ15 OPEN: Build targeted practice of a chosen word set? Default: deferred; v1 uses word-list import."
  - "OQ16 OPEN: Add evidence-kind counters or an evidence log to the knowledge writers? Default: deferred."
  - "OQ17 OPEN: Fix the decay model, and show any model-based 'review soon' flag before that? Default: no such flag in v1."
  - "OQ18 OPEN: Let learners mark 'I know this' / 'I don't know this'? Default: not in v1."
  - "OQ19 OPEN: Add a compact card to Today? Default: not in v1."
  - "OQ20 OPEN: Show JLPT at launch although every level is mostly 'not yet in LinguaDojo'? Default: show it with that share stated first, plus the import action; never use JLPT coverage in Pro marketing."
  - "OQ21 OPEN: Does 'known' mean recognition only? Default: yes."
  - "OQ22 OPEN: Which tiers see exam-list coverage counts? Default: counts for everyone; word lists, actions and export are Pro."
  - "OQ23 OPEN: Must a raw-answer export exist on every tier (data portability)? Default: not in v1; owner to check."
  - "OQ24 OPEN: First official sitting of the new HSK (13 Dec 2026 or July 2026)? Default: name the edition only."
  - "OQ25 OPEN: Task-mode page (Back header, no tab bar) or a tab page under Me? Default: task mode."
  - "OQ26 OPEN: Write a snapshot row every day for inactive learners? Default: yes, with pruning."
  - "OQ27 OPEN: Is 'rated known after a direct check' strict enough? Default: more correct than wrong direct checks and a rating of at least 0.75; measured later."
  - "OQ28 OPEN: Accept the Pro launch gate: no enforcement or Pro marketing of the report until HSK lists, the add-to-word-list action, filtered export and evidence-first rows ship? Default: yes."
  - "OQ29 OPEN: Refresh the Chinese vocabulary-check word pool (stale since the October-November seeding, about 5-7 MB) before or after the Chinese launch? Default: after the size gate."
  - "OQ30 OPEN: May 'Add these words' grow the database (exercise generation; new words at 8 credits each)? Default: dictionary words only in v1."
  - "OQ31 OPEN: Seed the ~722 missing JLPT N5-N4 words (about 3.4 MB) after the size gate? Default: a separate content task."
  - "OQ32 OPEN: Add a Pro 'Upcoming tests' card showing how many key words of each recommended test are known? Default: deferred."
  - "OQ33 OPEN: Align the vocabulary check's own result (which scores a skip as a wrong answer) with the report, or label each? Default: label each and show the report's range on the result screen."
  - "OQ34 OPEN: Show an estimated percentage per exam level after validation? Default: no."
  - "OQ35 OPEN: The goal-path layout needs a stored goal per study language (exam level, optional exam date). Where is it stored (user_languages columns or a small settings row), and is it shared with the study plan? Default: two nullable columns on user_languages."
  - "OQ36 OPEN: Show '+N rated known in the last 30 days' per exam level? It needs per-level counts in the nightly snapshot (ADR-053), a few bytes per list level per row. Default: yes, once 30 days of snapshots exist."
  - "OQ37 PARTLY ANSWERED (owner, 2026-11-18): build the placement test as an adaptive version of the vocabulary check; no fake words or Yes/No self-report; for Chinese and Japanese test both the meaning and the pronunciation of words to tell real knowledge from partial knowledge. Design research running (TASK-1073)."
---

# Knowledge Report ("My vocabulary")

## Purpose
Show learners, honestly, what LinguaDojo has measured about their vocabulary in the language they
study, how sure it is, and what to do next. Free and Core get a summary; Pro gets the word-by-word
view with the evidence behind each word, exam-list and word-list coverage with a study action, and
export. It is one of the three differences between Core and Pro.

## User Story
As a learner preparing for HSK, JLPT or professional work, I want to know roughly how many words I
can recognise, how far I am through my exam's word list, which words I missed recently and what to
study next — without being flattered by a big number the app cannot back up. As a Pro learner I want
to see *why* the app thinks I know a word, send the words I am missing into my daily practice in one
tap, and take my data with me to a spreadsheet or Anki.

## How It Works
The page is called **"My vocabulary"** in the app (not "report": the top bar's Report button already
means "report an issue"). It opens from the **Me** tab and shows one study language at a time — the
one chosen in the top bar. Every number on it carries one of three tags: **From your answers** (things
you did), **Estimated** (worked out from the vocabulary check, always as a range) or **Model** (the
app's rating, which is not a probability).

**What everyone sees (Free, Core and Pro)**
1. **How many words you recognise — as a range, never a single number.** The range comes from the
   vocabulary check (Calibration), which draws words at random from its own word pool at every
   frequency level. It reads like "In the vocabulary check you recognised about **850–1,400** of the
   3,175 Japanese words it draws from", with a label (Rough, Medium or Good) and the dates of the
   answers behind it. Words not yet in the check are not counted. If you answer "I don't know", the
   word counts as not known, and guesses are corrected for the 1-in-4 chance of being right; if some
   of the words you skipped were partly known, the true figure is higher. With too few answers, or
   answers older than six months, no number is shown; the page says how many more answers are needed
   and offers the check. For a beginner the page may say "fewer than 510 of the 3,623 words".
2. **Rated known after a direct check** — a separate, smaller count: words you have answered directly
   (a quiz, an exercise, a flashcard, the vocabulary check) more often right than wrong, and that the
   app now rates as known. It is the app's rating, so reading tests can move it. Next to it: how many
   words the app is tracking for you.
3. **By word frequency** — four groups from the most common words to rare ones, each with its size,
   and the estimated share you know shown only when there are enough check answers at that level.
4. **Exam word lists** — for Chinese, HSK 3.0 levels 1–6 and 7–9 (2025 syllabus); for Japanese, the
   JLPT N5–N1 community lists, labelled unofficial because JLPT publishes no list. Each level shows how
   many words are rated known, seen but not yet rated known, not yet seen, and not yet in LinguaDojo at
   all. **At launch, exam coverage is strong for HSK 1–5 and partial for JLPT**: about half of every
   JLPT level is not yet in LinguaDojo, and the card says so first. A note says that knowing a level's
   words is not the same as passing its exam, and a line gives the date the list was last matched to
   the dictionary. English has no exam list.
5. **Your own word list** — if you have uploaded words, how many are rated known, seen or not yet seen.
6. **Last 30 / 90 days** — words you practised (exercises and quizzes), the number of direct checks,
   words you met only in texts, the change in words rated known (always next to how many direct
   checks there were, so a change caused only by reading tests is labelled as such), and how many words
   you have not seen for 60 days or more. When you retake the vocabulary check, it says whether your
   range has clearly changed. Until enough history exists the card says when the first trend appears.
7. **Skills** — your first-try accuracy by kind of exercise over the last 90 days (recognition, telling
   similar words apart, and so on), with how many tries and words each figure rests on. A sentence such
   as "Your first-try accuracy is lower in telling-similar-words-apart exercises (53%, 32 tries on 11
   words) than in recognition exercises (94%, 84 tries on 17 words)" appears only when the difference
   is clear, with the note that some kinds of exercise are harder for everyone.
8. **What to do next** — one to three buttons, such as "Take the vocabulary check", "Prepare for
   {test}: 12 of its 40 key words are new to you", "Do today's session", "Review in Practice". No
   praise, streaks, badges or scores.

**What Pro adds**
9. **Word by word** — every word the app has evidence on, each row leading with the latest thing you
   did ("Last direct check ✓ 3 Nov", or "Seen in tests only"), its state (missed last time, rated
   known, checked but not yet rated known, or seen in tests only), right and wrong counts, frequency,
   "not seen for 75 days" when it applies, ladder ring and flashcard lapses. Search by word, reading or
   pinyin without tones; filter and sort; load more as you scroll.
10. **Why we think this** — tap a word to see the answers behind it (test questions, exercises, word
    quizzes, vocabulary-check items), what kinds of practice are not listed one by one, and the app's
    own rating, labelled as a model rating.
11. **Missed recently** — words whose latest first try was wrong in the last 90 days, most-missed
    first, with the kind of exercise; words missed 3 of the last 5 times on 2 or more days are marked.
12. **List coverage** — the actual words of any HSK or JLPT level (or your own list) in each bucket,
    most common first.
13. **Add these words to my word list** — one tap sends up to 50 missing or missed words into your
    daily practice through the existing word-list import (dictionary words are free; up to 5 lists a
    day).
14. **Export** — the current view or list as a spreadsheet (CSV that opens correctly in Excel, Chinese
    and Japanese included) or as an Anki-ready text file.

A Free or Core learner sees one card at the end of the summary that names what Pro would show *from
their own data* ("251 words with their evidence · 10 missed recently · CSV and Anki export"). Nothing
is blurred, nothing pops up, and after a downgrade nothing is deleted.

## Layout (owner preference 2026-11-18)
The owner prefers the **goal path** design (mockup C, fleshed out in `wiki/demos/knowledge-report-goal-path.html`). From the top: the vocabulary range (estimate first, with the four frequency groups); the learner's goal (exam level and optional exam date, editable) with a ring of words rated known up to that goal and a focus level; the exam levels as a path, each opening in place to show its new, seen, known and missed words with "Add to practice"; next steps; this week; words you keep missing; tests to read next; how you answer; the last 13 weeks; your own lists; then all words, export and "How these numbers work". Core learners see the same page with counts, and a Pro row wherever Pro would show the words themselves. The tech spec still describes the earlier card order; TASK-1072 brings it in line once OQ35 and OQ36 are answered.

## Constraints & Edge Cases
- **There is very little learner data today.** Three learners have any word evidence; one looks like
  a test account. Most learners will see the "not enough data yet" states, so those are designed first.
- **The range covers only the vocabulary check's word pool** (Japanese 3,175 words, Chinese 3,623,
  English 3,754 today). It never claims a learner's total vocabulary. The Chinese pool is smaller than
  the Chinese dictionary until it is refreshed (OQ29).
- **It measures recognition** (choosing the meaning from four options), not the ability to produce
  words.
- **"I don't know" counts as not known.** If skipped words were partly known, the true figure is
  higher; this is measured later with a small change to the check (OQ5).
- **The app's per-word ratings are not calibrated probabilities**, so the page leads with what you did
  and shows the app's rating only on the word sheet, labelled as a model rating. No "due for review" or
  "fading" claims appear: the app's memory-decay model treats the most common words like rare ones.
- **Words, not definitions.** Counts are of words (and, in the Pro table, of meanings), never of
  definition rows; a meaning can be stored up to six times in different languages and levels.
- **Many exam words are not in LinguaDojo yet** (about 40% of HSK overall, most of JLPT). They form
  their own bucket and are never counted as unknown.
- **No history exists before launch.** Growth starts from the first nightly snapshot.
- **New learner:** "We don't know your vocabulary yet" with two actions — never "0 words".
- **The exam lists are files kept outside the database** (in the app's file storage, ADR-054), so they
  do not wait for the database size limit (OQ13); they wait only for the choice of HSK edition and the
  licence answers (OQ2, OQ3). Pro will not be enforced or marketed on this report before the HSK list is
  in place (OQ28).
- **A list is matched to the dictionary when it is built.** Words added to LinguaDojo afterwards stay in
  "not yet in LinguaDojo" until the list is rebuilt, so the card shows the date of the last match.
- **If the list files cannot be read**, the list cards say "Word lists are unavailable right now" and
  the rest of the page works as usual.

## Business Rules
- Free and Core: summary only. Pro (and Pro trial, Professional, school and tutor seats): full view.
  Downgrade returns to the summary at the end of the paid period; data is kept.
- The word-by-word view is not enforced as Pro, and the report is not named as a Pro benefit, until the
  HSK list, the add-to-word-list action, filtered export and evidence-first rows have all shipped.
- One definition per term across the page, the exports and any future Today card.
- A range is shown only with at least 10 vocabulary-check answers at every frequency level in the last
  180 days; "Medium" needs 20 and "Good" 30 at every level.
- Skill comparisons need at least 20 first tries on at least 10 words per kind of exercise in 90 days,
  and clearly separate intervals.
- Community JLPT lists are always labelled unofficial; HSK lists name their edition; every list shows
  the date it was matched to the dictionary.
- A list's words may be exported only when that list's licence allows it (the HSK list not until
  share-alike is accepted — OQ3); exported list rows always carry the list's attribution.
- No streaks, XP, badges, leaderboards, pass probabilities or time-to-goal predictions.

## Open Questions
All OPEN; see frontmatter. Full table with defaults and affected tasks:
[[features/knowledge-report.tech]] §15.

## Related Pages
- [[features/knowledge-report.tech]] — technical specification
- Mockups: `wiki/demos/knowledge-report-pro-mockups.html` — five interactive Pro-view options on real and demo data
- Mockups: `wiki/demos/knowledge-report-full-mockups.html` — three complete learner-facing reports (scrolling report, tabbed workspace, exam-goal path)
- Mockup: `wiki/demos/knowledge-report-goal-path.html` — **preferred layout**: the goal path, fleshed out, Pro and Core, Japanese and Chinese
- [[tasklist/knowledge-report.tasks]] — task breakdown
- [[features/vocabulary-knowledge]] — where the per-word ratings come from
- [[features/calibration]] — the vocabulary check that produces the range
- [[features/test-prestudy]] — the "Prepare for {test}" next step
- [[features/practice-extra-rounds]] — the "Review in Practice" next step
- [[tasklist/word-list-import.plan]] — the "Add these words" action
- [[business/pricing-plan]] — Free/Core summary vs Pro full view
- [[decisions/ADR-051-vocabulary-size-from-calibration-frame]]
- [[decisions/ADR-052-report-leads-with-measured-evidence]]
- [[decisions/ADR-053-daily-knowledge-snapshots]]
- [[decisions/ADR-054-exam-word-lists-in-storage]]
- [[decisions/ADR-055-knowledge-report-entitlement-seam-and-launch-gate]]
- [[decisions/ADR-056-report-actions-reuse-existing-study-paths]]
