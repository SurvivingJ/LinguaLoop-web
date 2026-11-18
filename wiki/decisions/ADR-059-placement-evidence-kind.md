---
title: "ADR-059: Placement answers are their own evidence kind, written per word pair; meaning-only words go to reading practice; never 'rated known' on their own"
status: accepted
date: 2026-11-18
---

# ADR-059: Placement answers are their own evidence kind, written per word pair; meaning-only words go to reading practice; never "rated known" on their own

**Accepted 2026-11-18:** the owner approved PQ5 (this ADR's evidence rules). For Chinese, a reading answer
with the right syllables but wrong tones ([[decisions/ADR-060-zh-placement-scores-tones]]) counts as
"reading not right": no BKT write, and the word goes to reading practice (A2r). PQ19 (no ability or rating
write until OQ33) and PQ21 (which sense row) keep their defaults and remain open.

## Context
Today the check writes BKT evidence at `/end` (ADR-033 revision (b), 4B) through
`update_vocabulary_from_word_tests_batch`, which increments `word_test_correct/wrong`. The report's "rated
known after a direct check" needs `word_test_correct > word_test_wrong` and `p_known ≥ 0.75`. One right
check answer on a Zipf ≥ 5 word lifts the prior 0.65 to about 0.88. In simulation, 7–13% of words answered
right on every placement item are not known as words, and up to 21% with partial reading knowledge
(ESTIMATE).

Products learners trust (Hack Chinese, Renshuu) seed declared or placed words as "assumed known, to be
checked". Learners resent a permanent "known" (Migaku).

The learner-side review traced the draft's hand-off and found that the words the feature exists to find
(meaning recognised, reading not) were **pushed out of practice** (MEASURED in code, not executed end to end):
- Writing the meaning answer as BKT "correct" lifts `p_known` above 0.40 for any Zipf ≥ 3 word.
- Queue A2 admits only wrong or skipped calibration answers (`services/practice/new_word_admission.py:648-655`).
- A1 needs ≥ 2 evidence or `p_known ≤ 0.40` (`services/practice/constants.py:37-38`).
- Admission and the supply gate use the calibration anchor sense, which for zh/en and ja/en is the
  English-gloss row. That row has 0 active exercises for every pool word, while some sense of the same
  word has ≥ 3 for 93% (zh) and 92% (ja) (MEASURED).
- The intro drill drops zh pinyin unless the reading carries a numbered `(…)` part
  (`services/intro_drill.py:248-249`), and most zh readings no longer do.

The draft also let the placement launch with the evidence hook off while its copy said practice uses the
answers.

## Decision
1. **Write per word pair, once per session at the end** (including sessions closed as abandoned):

   | outcome (scored items) | BKT | counters | admission |
   |---|---|---|---|
   | reading-ready: meaning ✓, reading ✓ | correct | `placement_correct` | none |
   | reading-ready: meaning ✓, reading ✗ or IDK | **no write** | none | **A2r** (reading gap) |
   | meaning ✗ or IDK | wrong | `placement_wrong` | **A2** |
   | reading-exempt (ja kana-only, en): meaning ✓ | correct | `placement_correct` | none |
   | probes | never | never | never |

2. **Same BKT update as the check.** Slip 0.05, guess 0.25, transit 0.05, Zipf step prior. It goes
   through `update_vocabulary_from_placement_batch`, which increments the new counters
   `user_vocabulary_knowledge.placement_correct/placement_wrong` and **never** `word_test_*`. It writes to
   the anchor sense row, as the check does (ADR-047 problem 3 unchanged; PQ21).
3. **Admission uses the native rank-1 sense of the same `vocab_id`.** The mapping happens before the status
   veto and the supply gate, for A2 and A2r.
4. **A2r, the reading-gap queue.** It takes placement words with the meaning right and the reading not
   right within `CALIBRATION_EVIDENCE_MAX_AGE_DAYS`. It has the same veto and budget as A2 and is ranked
   alternately with A2. Words enter through the new-word path, whose intro drill opens with the reading
   formats. The zh reading fix in `intro_drill._reading` (TASK-1082) is a zh launch dependency.
5. **Rated known is unchanged.** Placement evidence alone never makes a word "rated known". The report
   shows the evidence state "Placement answer only".
6. **No pooled ability or rating write from placements** until the report's OQ33 (skip scoring) is
   answered. Then the placement uses a skip-aware likelihood, or stays out of the fit.
7. **Launch dependency.** No placement launches without this evidence path, because the result screen
   says practice uses the answers. Whether the open-ended check moves to the same kind is decided in
   TASK-1065's ADR.

## Consequences
- **Easier:**
  - practice starts from the placement immediately;
  - words with the meaning but not the reading are drilled on their reading, which is the owner's target
    case;
  - "rated known" keeps meaning "checked in practice";
  - the report can say where evidence came from.
- **Harder:**
  - two counter pairs on UVK and a sibling batch function to maintain;
  - a new admission source;
  - the A2r ranking against A2 is a guess until data shows otherwise;
  - until TASK-1065 decides, the same item counts as a direct check in the open-ended check and as
    placement evidence in a placement.
- **Constrained:**
  - a placement can raise `p_known` above 0.75 for words answered right on both items, so practice may
    schedule some guessed words late, and the scheduler's normal checks correct them;
  - BKT and admission use different sense rows of the same word until ADR-047 problem 3 is solved.

## Alternatives Considered
- **Write the meaning answer as the evidence (the draft):** pushes meaning-only words out of practice.
- **Write through the existing path (`word_test` counters):** one placement answer could make a word
  rated known.
- **No BKT write at all:** practice would ignore the most informative cold-start data.
- **Write meaning-only words as BKT wrong:** misstates meaning knowledge and would re-teach meanings
  the learner has.
- **A general evidence log now (TASK-1065):** right long-term, but an open question with a byte cost.
  The two counters are its smallest compatible step.
- **Damped BKT update for placement:** hides the kind in a constant instead of recording it.
- **Launch with the hook off:** the result's copy would be untrue.
- **A Pro-only manual "meaning only" list (draft PQ20):** puts the target case behind a paywall and a
  manual step.

## Related Pages
- [[features/vocab-placement.tech]] §10, §11 · [[features/vocab-placement]]
- [[decisions/ADR-033-budget-scope-and-new-word-budget]] — Queue A2 and the new-word budget
- [[decisions/ADR-040-criterion-based-new-word-drill]] — the intro drill
- [[decisions/ADR-047-basic-word-knowledge-prior]] — sense-row multiplicity (problem 3)
- [[decisions/ADR-057-adaptive-placement-with-conditional-reading]] · [[decisions/ADR-058-meaning-and-reading-recognition-pair-estimator]]
- [[features/knowledge-report]] · [[evaluations/vocab-placement-research-2026-11-18]]
