---
title: Practice Extra Rounds
type: feature
status: in-progress
tech_page: practice-extra-rounds.tech.md
last_updated: 2026-10-29
open_questions: []
---

# Practice Extra Rounds

## Purpose
Practice mode (`/session?mode=practice`) lets a learner keep practising past the daily budget,
with no limit: more reviews, more new words, or both, one round at a time.

## User Story
"I've finished today's practice and want to keep going. Let me choose to keep reviewing and/or
learn a few more new words, as many rounds as I like."

## How It Works
1. When Practice mode runs out of work (or has nothing to start with), the summary card shows
   **Keep practising**:
   - **Reviews**: a checkbox. Up to 10 review items per round: due words first, then words
     reviewed ahead of schedule (lowest predicted recall first).
   - **New words this round**: 0, 3, 5 or 10.
2. **Start round** runs one round. Choosing both mixes new words in among the reviews.
3. After each round the learner is back on the panel, with the last choice already selected.
   **Done** hides the panel.
4. If any of the chosen new words go beyond what is left of today's goal, a warning says how
   many and that they add to future reviews. There is no hard cap.
5. Today's optional extra round ("Session done — N reviews and M new words left today") appears
   once the practice part of the session is done, even if today's tests were skipped or are not
   done. This holds in both Practice mode and the daily session (changed 2026-10-29).

## Constraints & Edge Cases
- At most 10 new words per round; the learner sees the selection screen again between rounds.
- Words admitted earlier but never started are used before new ones are admitted.
- Review-ahead skips words attempted in the last 10 minutes and the previous round's words.
- If no words have exercises ready, a round can be short or empty ("No practice items right now").
- Daily-session mode (`/session`) is unchanged; the panel appears only in Practice mode.

## Business Rules
- Extra-round answers update FSRS and BKT normally, including early reviews.
- Extra new words join the ladder and the normal review schedule.
- Extra rounds count toward the week's targets, like the optional extra round.
- Extra rounds never count toward session completion.

## Open Questions
None.

## Related Pages
- [[features/practice-extra-rounds.tech]]
- [[features/session-budget-settings]]
- [[decisions/ADR-036-open-ended-practice-beyond-budget]]
- [[tasklist/practice-extra-rounds.tasks]]
