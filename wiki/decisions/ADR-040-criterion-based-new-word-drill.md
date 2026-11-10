---
title: "ADR-040: Criterion-based intro drill for new words (5 / 3 / 2 / 2), replacing ladder ring 1"
status: accepted
date: 2026-11-09
---

# ADR-040: Criterion-based intro drill for new words (5 / 3 / 2 / 2), replacing ladder ring 1

## Context

A new ladder word gets one exercise per practice session, and words seen earlier the same day
are filtered out ([[algorithms/vocabulary-ladder]]). So on day 1 a new word is seen once. The
test prestudy word prime drills each word 5–7 ways, interleaved with the other words
([[features/test-prestudy]]), and the developer found it far more effective. The developer
proposed hammering new words on a tapering schedule ("10, 10, 7, 5 questions"). The options were
evaluated against the literature on 2026-11-09 (log entry of that date).

Evidence:

- **Encounters:** about 10+ encounters to learn a word, more for full knowledge (Webb 2007,
  *Applied Linguistics* 28(1)). The meta-analysis of 26 studies found r = .34 for repetition, with
  needs ranging from 2 to 20 encounters and spaced encounters helping (Uchihara, Webb & Yanagisawa
  2019, *Language Learning* 69(3)).
- **Within-session repetition:** 5 and 7 retrievals beat 1 and 3, but with time controlled one
  retrieval was the most efficient (Nakata 2017, *SSLA* 39(4)).
- **Overlearning fades:** extra same-session practice gives benefits that "diminish sharply over
  time" (Rohrer, Taylor, Pashler, Wixted & Cepeda 2005, *Applied Cognitive Psychology* 19).
- **Successive relearning:** practise to a criterion, then relearn to a criterion in later
  sessions. Extra sessions matter more than extra reps (Rawson & Dunlosky 2011, *JEP: General*;
  Rawson, Dunlosky & Sciartelli 2013, *Educational Psychology Review*).
- **Spacing within and across sessions:** one interleaved stack beat small stacks for 90% of
  learners (Kornell 2009, *Applied Cognitive Psychology* 23). Long spacing helped in initial
  learning and relearning (Nakata, Suzuki & He 2022, *Language Learning*).
- **Effortful success:** harder correct retrievals (longer lag) produce better retention
  (Pyc & Rawson 2009, *Journal of Memory and Language* 60).
- **Retrieval over re-exposure and form first:** retrieval opportunities help L2 word learning
  (Barcroft 2007, *Language Learning* 57). Under high load, meaning-heavy tasks can crowd out
  form-meaning mapping (Barcroft 2015, TOPRA model).
- **Varied encounters and retrieval** are core conditions for learning (Nation & Webb, Technique
  Feature Analysis). Productive tasks build more knowledge (Webb 2005, *SSLA* 27).
- **Adaptive retirement** (3 fast correct answers in a row, with spacing set from response time)
  beat fixed schedules (Mettler, Massey & Kellman 2016, *JEP: General*).
- **The first retrieval matters more than the shape of the schedule** (Karpicke & Roediger 2007,
  2010; Kang et al. 2014).

## Decision

1. Every newly admitted word passes through **four intro sessions** before the ladder: day 0, 1,
   2 and 4. Each next session is scheduled from the date the previous one was completed.
2. Each session runs **until a target number of counted correct answers**: **5 / 3 / 2 / 2**. A
   correct answer counts only after ≥ 4 intervening items, in a format different from the last
   counted one, and not via "I don't know".
3. Sessions 2–4 open with a **cold typed recall**. Missing it raises that session's target by 1.
4. Per-session item caps of **12 / 8 / 6 / 6**. Reaching the cap without the target repeats the
   stage the next day.
5. The intro **replaces ring 1** for new admissions. Passing session 4 places the word on ring 2
   with `form_recognition ≥ 0.55`, and its intro dates satisfy the 2-distinct-days gate. A word
   demoted from ring 2 makes a full restart at intro session 1.
6. **One knowledge-evidence point per word per session.** Stage 1 uses the majority rule;
   stages 2–4 use the cold recall.
7. **Test prestudy words enter the ladder through this drill.** A prime that meets the stage-1
   criterion counts as session 1. This reverses the 2026-10-29 decision that prestudy never
   admits words to the ladder. Prestudy words count against the daily quota. Words over it are
   queued for later days unless the learner chooses to overload, after a notice that shows the
   extra daily minutes.
8. The `new_words_per_day` default rises from 5 to 10, and plans still at the old default of 5
   move to 10.

## Consequences

- **Easier:** every new word gets prestudy-strength drilling. Easy words cost little and hard
  words get more. Admission no longer waits on 3+ generated exercises, because stage 1 runs on
  gloss + sentence + reading.
- **Harder:** a second progression state machine sits in front of the ladder. Session time rises
  sharply: at 10 new words a day, about 40 words are in intro on a typical day, about 170 items or
  25–30 minutes. The review-load governor and the session estimate must count it.
- **Constrained:** intro words must be excluded from the ladder pool. BKT must not be updated per
  intro item. Legacy ring-1 words keep the old path until they clear ring 1.
- The targets are above the minimum the relearning studies needed, because those studies tested
  one kind of knowledge (definition recall). Here a word must gain reading, meaning and use. That
  is the deliberate reason for 5 in session 1 (one per format).

## Alternatives Considered

- **Fixed tapering counts (10 / 10 / 7 / 5 questions):** predictable session length, but it
  over-drills easy words, may under-drill hard ones, and spends most of its time on same-session
  reps, which fade. Rejected.
- **Prestudy-style day-1 prime only:** the smallest change, but days 1–4 stay at one question a
  day. Kept as the first build step, not the end state.
- **Fully adaptive retirement on response time (ARTS-style):** strongest evidence, but needs
  response-time baselines per learner and format. Deferred. `time_taken_ms` is recorded on every
  intro attempt so it can be added later.
- **Lower targets (1–3 / 1 / 1 / 1, per the relearning literature):** cheaper, but rejected by the
  developer for the reason above (several knowledge aspects per word).
