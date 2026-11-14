---
title: DT Guided Self-Repair
type: feature
status: planned
tech_page: ./dt-guided-self-repair.tech.md
last_updated: 2026-11-14
open_questions:
  - "OPEN (owner): Everyone or an A/B test? Default in this spec: every learner whose grade comes from the single-call grader gets the guided flow (DT_GUIDED_REPAIR=on). The A/B test in the design spec (§7) is not built; the existing correction-style arm is still stamped on each submission and applies to the full result screen shown after the flow."
  - "OPEN (owner): Should 'maybe' flags (the grader's own low-confidence errors) be shown as the 'This part may need another look' step? Default: no. The grader withholds them today (DT_SINGLE_CALL_SHOW_LOW_CONFIDENCE=off) because on the gold set every one was a false alarm. The step is fully specified and built, so turning it on is a config change, but it would also count those errors in the score."
  - "OPEN (owner): Hint templates (the 'what kind' name and the 'clue') are AI-drafted and unreviewed; Chinese and Japanese clue texts exist only for the English-L2 error types. Is it acceptable to ship with them before native review (TASK-938)? Default: ship; a missing template falls back to a general clue, never to model-written text."
  - "OPEN (data, not a decision): every threshold here (3 sentences per pass, 4 checks, 3 practice items a day, the 2/4-day return intervals, the confidence cut-off) is a design default, not a tuned value."
---

# DT Guided Self-Repair

## Purpose
After a learner submits a Dual Translation (DT) passage, the app does not show the correction
straight away. It points out which sentences have a problem and lets the learner fix their own
sentence, with help arriving one step at a time only when asked for. Sentences the learner could
not fix on their own come back later in daily practice, where they fix the same sentence again.
Everything the learner does along the way is recorded for later design and tuning work.

The owner chose this design on 2026-11-14 ("the guided process in mockup two is the way to go").
Design source: [[design/dt-feedback/option-2-guided-self-repair/SPEC]] (Revision 2 governs) and
its `mockup.html`.

## User Story
> "I'm a Chinese speaker learning English. I translate a short passage and press Submit. A panel
> pops up: '2 sentences to fix. The other 2 look fine.' I tap Start. I see the Chinese sentence and
> my own English sentence in an edit box, labelled 'Fix your sentence'. I'm not sure what's wrong,
> so I tap 'Need a hint?' and a word in my sentence gets underlined. I change it and press Check.
> After a second it says 'Fixed — with 1 hint' and moves on by itself. On the second sentence I
> give up and tap 'Show answer': I see what I wrote with the wrong part struck through, the
> correct sentence with the right part marked, and one line explaining why. At the end it says
> what I fixed myself and what was saved to practice. Two days later my daily session asks me to
> fix that second sentence again."

## How It Works

### In the moment (right after Submit)
1. **Submit.** The learner submits as today. The button shows "Checking…" while the grader runs
   (one or two seconds).
2. **It pops up.** A sheet opens over the exercise: full screen on a phone, a centred card on a
   larger screen. It never scrolls; each screen holds one thing to do and one main button.
3. **Result screen.** One of:
   - "No issues found" with a tick, and Done; or
   - a large number and "sentences to fix", one line "The other N look fine.", and Start.
4. **One sentence per screen.** For each flagged sentence (at most 3 that get hints, plus any
   shown directly, at most 4 screens in all), the learner sees the sentence they were asked to
   translate (in their own language, two lines at most), the label "Fix your sentence", and an
   edit box already holding their own sentence. They change the part they think is wrong and
   press Check (or Enter).
5. **Help, one step at a time.** "Need a hint?" gives, in order and each replacing the last:
   - **Where:** the suspect words are underlined inside the edit box ("Look at the underlined
     part.").
   - **What kind:** the name of the kind of problem, in the learner's own language (for example
     "Measure word (量词)").
   - **Clue:** one or two sentences that point at the rule without giving the answer.
   - Then the button says **Show answer**.
   Some kinds of problem skip hints that would not help: meaning problems only get "where"
   before the answer; word-choice problems (a word the learner does not know) get no hints, only
   the answer. If the checker could not pin down where the problem is, the "where" hint is left
   out.
6. **Checking.** Each Check sends only the edited sentence to the checker (about 1–2 s). The
   button shows a spinner; pressing again does nothing. Possible results:
   - **Fixed:** a tick, "Fixed", "On your own" or "With 2 hints"; it moves on by itself after
     about 1.6 s (or with Next; always Next when the learner prefers reduced motion).
   - **No issue found:** the checker finds nothing wrong, but the sentence is worded differently
     from the original. The learner sees their sentence and the original side by side ("No issue
     found. Compare:"). This counts as fixed.
   - **Still not quite:** the box shakes once and the hint slot says "Still not quite. Try again,
     or take a hint." If the checker now points at a different place, the underline moves there.
   - **Same sentence:** if nothing was changed: "That's the same sentence. Change something
     first." No check is made.
   - **Could not check:** "Couldn't check just now — try again." The learner's text is kept. After
     two failures in a row the main button becomes "Show answer", so the learner is never stuck.
   After the fourth "still not quite" the answer is shown automatically.
7. **Mine is fine.** On every fix screen. One tap: "Noted. Compare:" with both sentences. No
   argument, no penalty, and the flag is logged for review of the checker.
8. **The answer screen** shows two blocks, top to bottom: **You wrote** — the sentence exactly as
   the learner first submitted it, with the problem part struck through — and **Answer** — the
   correct sentence with the corrected part underlined and bold — then one line of explanation in
   the learner's language. Next goes on.
9. **Summary.** "All done" and three counts: Fixed yourself, Needed help, Saved to practice.
   Done opens the existing full result screen (scores, the whole comparison, every error with its
   explanation), which is unchanged.
10. **Closing early.** The close button (or Escape) ends the pass at any point and opens the full
    result screen. Sentences not finished are recorded as skipped and saved to practice.

### Later (daily practice)
11. Each saved sentence comes back in the learner's daily session as a short "Fix your
    sentences" block of at most 3 items. Each item uses the same screen, with one extra line
    above the prompt: "From your translation on Tuesday". The edit box again holds the learner's
    original sentence and the suspect part is already underlined, so the first hint asked for is
    "what kind". The answer is shown after 3 failed checks.
12. If the learner fixes it with no more help than the underline, it is **resolved** and leaves
    the list. If they needed "what kind" or the clue, it comes back once more after 3 days. If
    they needed the answer, it comes back after 2 days, then 4; after 3 such sittings it is
    retired. Anything still on the list after 30 days expires. "Mine is fine" removes it.

## Constraints & Edge Cases
- **Which grades get the flow.** Only grades from the single-call grader (or a passage identical
  to the original, which shows "No issues found"). If the grader fell back to the older flow, or
  the feature switch is off, the learner sees today's result screen directly.
- **Too many problems.** If 5 or more sentences are flagged, or any score is the lowest band, the
  flow is skipped and the full result screen is shown directly; those errors are still saved to
  practice. Repair would be a slog on a passage that was too hard.
- **More than one error in a sentence.** The screen works on the most serious one. The sentence
  counts as fixed when that error is gone and the checker finds no new serious error. The answer
  screen marks every problem in the sentence.
- **Low-confidence flags** (off by default) appear as a question: "This part may need another
  look", with the part underlined from the start, no hints, and two equal buttons, "Mine is fine"
  ("Kept as written") and "Check". They are never counted and never saved to practice.
- **The answer is never on the learner's device before they ask for it.** While the flow is open
  the app does not send the corrected sentence, the comparison or the explanations; the full
  result is available once the flow is finished or closed.
- **Long sentences.** The text in the box steps down in size; past the smallest size the box
  scrolls inside itself, but the screen never does. A long prompt is cut to two lines and opens in
  full on tap.
- **Chinese and Japanese typing.** Pressing Enter to pick a character in the input method never
  submits the sentence.
- **Cost.** A check costs about $0.00006–0.00009 and counts toward the learner's daily DT budget,
  with an extra allowance for repair. When that runs out, Check shows the answer instead.
- **Reloading the page** mid-flow resumes at the first unfinished sentence.

## Business Rules
- Repairs never change the score. Scores come from the first submission only.
- Every episode ends with the original sentence on screen, except when the learner fixed it
  themselves (the full result screen afterwards still shows it).
- Wording: "the checker", "Still not quite", "No issue found" — never "wrong", "correct" or "you
  made a mistake"; no exclamation marks, streaks or red crosses.
- Saved to practice: an error the learner did not fix on their own with at most the "where" hint
  (needed "what kind" or the clue, saw the answer, was shown it directly, or skipped it).
  Not saved: fixed with at most the underline, "Mine is fine", low-confidence flags.
- Hint texts come from reviewed-or-reviewable templates, never from a model at run time, and a
  clue that would contain the answer is replaced by a general clue.
- Recorded (not shown): every hint level reached, every checked revision with its result,
  latency and cost, time between actions, whether the answer was asked for or shown
  automatically, disputes, skips, and the outcome of each sentence. Prompts, raw model replies
  and copies of the passage are not stored.

## Open Questions
See frontmatter. All other choices in this page are design defaults recorded in the tech spec.

## Related Pages
- [[features/dt-guided-self-repair.tech]] — technical specification
- [[tasklist/dt-guided-self-repair.tasks]] — task breakdown
- [[design/dt-feedback/option-2-guided-self-repair/SPEC]] — the chosen design
- [[features/dual-translation]] · [[features/dual-translation.tech]]
- [[features/dual-translation-remediation.tech]] — the existing error cards (kept alongside)
- [[decisions/ADR-044-dt-single-call-generative-grader]]
- [[evaluations/dt-decision-grading-2026-11-14]]
- [[features/study-plans.tech]] — the daily session queue
