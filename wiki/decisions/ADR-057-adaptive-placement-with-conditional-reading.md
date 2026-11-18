---
title: "ADR-057: Vocabulary placement is an adaptive, band-stratified run of the vocabulary check with a conditional reading item and a cap-or-precision stop"
status: proposed
date: 2026-11-18
---

# ADR-057: Vocabulary placement is an adaptive, band-stratified run of the vocabulary check with a conditional reading item and a cap-or-precision stop

## Context
New and returning learners need an honest vocabulary result in a few minutes on a phone. The vocabulary
check ([[features/calibration]]) has the right items: four-option meanings with semantically close,
frequency-matched wrong options (ADR-025, ADR-039), and four-option readings one sound apart for zh and ja.
What it lacks:
- a stopping rule;
- adaptivity: it round-robins the least-served band;
- distinct words across sessions: anchors repeat;
- ended sessions: 74 of 79 live sessions never ended.

It also shows the reading under the word on meaning items ([[features/vocab-placement.tech]] §0, E1–E4).

The owner chose to build on this check. Fake words and Yes/No self-report are rejected. For Chinese and
Japanese, the owner asked that both meaning and reading be tested, to tell whether a learner actually knows a
word (2026-11-18).

Research ([[evaluations/vocab-placement-research-2026-11-18]]):

- **Precision is the binding limit.** A simulation of nine designs on the real word pools (4,000 synthetic
  learners) found about ±12–13% of the pool at 90% after 50–60 items. Adaptivity saves about 40% of the
  items (ESTIMATE).
- **The reading should come only after a right meaning.** That is the cheapest way to measure "meaning and
  reading". Asking the reading on every word spends about 60% more reading items for no gain (ESTIMATE).
- **Design-based scoring holds up; IRT scoring does not yet.** Adaptive band-stratified sampling scored
  with ADR-051's estimator (D3S) had bias −1.1..+0.4% of the pool and 95% coverage of 93–96% in every
  population, re-checked by an independent reviewer. IRT-style scoring had 10–20% lower error but biased
  up to −4.4% of the pool. No item difficulty can be calibrated from three users, and `services/irt/` has
  calibrated 0 exercises (MEASURED).
- **The reading items have flaws.** A tone-only wrong option exists for only 10.9% of zh anchors. 19% of
  Japanese kanji+kana reading items can be solved by matching the visible kana. Japanese words with
  Chinese definitions keep a `headword ——` prefix, which makes 10.8% of them answerable by string
  matching (MEASURED).
- **The real pace is slower than assumed.** The only real learner answers a meaning item every 6.57 s and
  a reading item every 7.50 s. A 60-item test is about 7 minutes; 50 items is about 5.8 (ESTIMATE).

## Decision
1. **A placement is a session mode of the vocabulary check** (`calibration_sessions.mode = 'placement'`).
   It uses the check's pool, distractor caches and tables. The tables gain:
   - on sessions: `stop_reason` and a frozen `result`;
   - on responses: `item_kind`, `probe_kind`, `instrument`, `pair_response_id`, packed
     `option_sense_ids` and `key_position`.

   Rank-1 senses only, one item per lemma.
2. **Adaptive band-stratified selection.**
   - Warm-up: two meaning items per Zipf band, first pass commonest band first.
   - Then the band whose next answer most reduces the variance of the reported count(s), computed from
     the tallies before the current answer.
   - Within the band, a uniformly random placement-ready lemma that the learner has not answered in the
     last 180 days.
3. **Conditional reading (zh, ja).**
   - The meaning item shows characters only.
   - Only after a right meaning is the same word's reading item asked.
   - One combined reveal per word.
   - Kana-only Japanese words are meaning-only.
4. **Item rules.**
   - Reading foils have the key's syllable or mora count.
   - Japanese foils are consistent with the word's visible kana.
   - Scored Chinese reading items never contain a tone-only foil, and the item says tones are not tested.
   - The cross-CJK leading equivalent word (`；`, `;`, `——`, `—` forms) is stripped from all definition
     options, and anchors still answerable by string matching are excluded.
   - Every option is a real word's definition or reading; generated variants need the owner (PQ3).
5. **Unscored probes.** At most 4 per placement, labelled "Extra question — not scored", never used by any
   estimate or write:
   - rechecks of earlier m+r credits;
   - a reading after a missed meaning;
   - a forced best guess after "I don't know";
   - a 2-option sound pair (tone or special mora).
6. **Stop.**
   - zh/ja: no new word after 50 scored items (a due reading is still asked); en: 40.
   - No new word after 7 minutes of active time.
   - Earlier, from 40 (zh/ja) or 20 (en) scored items, when every reported 90% half-width is ≤ 12% of the
     pool.
   - Also on exhaustion; or when the learner stops after the warm-up and ≥ 20 scored items, with a result;
     or when abandoned (closed after 24 h, result frozen if eligible).
7. **One SQL round trip per answer.** It grades the answer and builds the following item. No client
   prefetch.
8. **Scoring.**
   - **v1 is design-based**: ADR-051's estimator, extended by ADR-058.
   - **v2 is an explanatory IRT model**: fixed 1/4 floor, separate meaning and reading skip propensities,
     Zipf, exam-level, cognate and script item features, a reading step conditional on meaning, θ mean
     fixed at 0, EAP. It runs in shadow and **keeps v1's uniform within-band selection**.
   - v2 is shown only when, per (language, L1 group), ≥ 80% of frame words have ≥ 6 exposures and it beats
     v1 on retest and predictive validation within that group.
   - Model-targeted selection would need its own ADR and Horvitz–Thompson weights in the report estimator.

## Consequences
- **Easier:** no cold-start priors or item calibration at launch; one estimator for the result and the
  report; the cognate over-statement of meaning-only tests (~1,000 words for Japanese-L1 learners of
  Chinese, ESTIMATE) is removed; retakes are disjoint; abandoned and early-ended tests still give a result.
- **Harder:**
  - Results are wide: 95% ≈ ±14–17% of the pool for meaning and reading, usually labelled "Rough".
  - Japanese needs a pool refresh and a kana-consistent foil refill before launch (69% paired readiness
    today, 50% in band 1).
  - The zh reading normaliser and the intro drill's zh reading must be fixed first.
  - Each answer waits for one server round trip, because keys stay on the server.
- **Constrained:**
  - The claim is four-option recognition of the pool's words.
  - Readings are recognised, not produced.
  - Chinese tones and Japanese special morae are not part of the scored claim (PQ3).
  - Heritage learners' reading knowledge is under-measured by the meaning-first order.
  - A change of cap, probes or rules needs a `CONFIG` version bump.

## Alternatives Considered
- **IRT targeting now (D1/D3):** lower count error, but biased in one population, weak placement of
  advanced learners, and it needs calibrated item difficulties. Kept as v2, scoring only.
- **Reading on every word (D2):** about 60% more reading items for no gain. **Reading on half the words
  (D4):** credits 13–39% of words without the reading.
- **Level strata (D3L):** 20–45% wider count intervals; a candidate only for a later level output
  (TASK-1090).
- **Fixed-length check (D0, 70 items):** about 6 minutes for the precision adaptive selection reaches
  sooner. **Meaning-only placement:** rejected by owner decision 3 and by the cognate over-statement.
- **Yes/No with pseudowords:** rejected by the owner.
- **60-item cap ("about 7 minutes"):** about ±1.5 points narrower at 95%, 1.2 minutes longer. Kept as the
  PQ10 alternative.
- **Sending both possible next items to the client to remove the round trip:** the client's choice between
  them would reveal whether the tapped option was the key.
- **Including the cached tone-only foil when one exists (the draft):** tested tone on about 11% of words,
  credited segment-only knowers about 0.93 of a known reading, and made the tone diagnostic unobservable.
- **A separate `placement_*` table family:** duplicates the ledger the report and the planner already read.

## Related Pages
- [[features/vocab-placement]] · [[features/vocab-placement.tech]] §2, §3, §5.4, §6, §7
- [[decisions/ADR-058-meaning-and-reading-recognition-pair-estimator]] · [[decisions/ADR-059-placement-evidence-kind]]
- [[decisions/ADR-051-vocabulary-size-from-calibration-frame]] · [[decisions/ADR-025-semantic-distractor-selection]] · [[decisions/ADR-039-packed-calibration-distractor-cache]]
- [[evaluations/vocab-placement-research-2026-11-18]]
