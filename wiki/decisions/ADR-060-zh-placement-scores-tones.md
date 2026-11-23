---
title: "ADR-060: Chinese placement reading items score tones with two tone pairs built only from syllable+tone pairs that exist, and count right tones minus wrong tones"
status: proposed
date: 2026-11-18
---

# ADR-060: Chinese placement reading items score tones with two tone pairs built only from syllable+tone pairs that exist, and count right tones minus wrong tones

Supersedes ADR-057 decision 4's Chinese rule ("no tone-only foil; tones not tested") and ADR-058 decision
1's Chinese claim ("the reading means the pinyin syllables"). ADR-057 and ADR-058 are otherwise unchanged.

## Context
The placement asks a word's reading only after a right meaning ([[decisions/ADR-057-adaptive-placement-with-conditional-reading]]).
The first design took Chinese wrong readings only from real words' readings. A wrong reading that differs
from the key only in tone existed for 10.9% of Chinese anchors, so scored items said "tones are not
tested", and tones were measured only by unscored 2-option probes (PQ3).

The owner was asked whether wrong options could be made-up tone variants of a word's reading. The answer
(2026-11-18): **"Yes, but only the existing tones, just wrong combos."** Read here as: a wrong option may
be the right syllables with a wrong tone combination, provided every syllable+tone pair in it exists in
Mandarin. No made-up syllables, which fits the owner's earlier rejection of fake words. The question did
not cover Japanese long vowels, っ, ん or voicing, so those stay unscored.

Measured on the live pool (read-only SQL, [[features/vocab-placement.tech]] E32):
- 382 toneless syllables occur in zh dictionary readings, with on average 2.47 of the four full tones each.
- 3,622 of 3,656 pool readings (99.1%) have at least one valid variant (band 7: 94.8%); 89.0% have three.

The shape of the item decides what a guess means:
- With one tone variant and two segmental foils, the key is always one of the only two options that
  share syllables. A test-wise learner who knows nothing picks between them and is right half the time.
- With three tone variants, all four options share the syllables. The item gives the syllables away and
  cannot be built for 11% of words.

## Decision
1. **Tones are scored for Chinese** (the owner's answer to PQ3). The zh claim becomes "recognised the
   meaning and the pinyin with its tones". ja special morae stay out of the scored claim.
2. **Item shape: two tone pairs.** Every zh reading item shows four tone-marked pinyin strings, shuffled:
   - K, the key;
   - K′, a tone variant of K;
   - F, a cached segmental foil with the key's syllable count that is not itself a tone variant of K;
   - F′, a tone variant of F, different from K and K′.

   Each syllable set appears exactly twice, so neither pair points to the key.
3. **What counts as a tone variant.**
   - The same syllables with a different tone combination.
   - Every syllable+tone occurs in at least one zh dictionary reading (`calibration_zh_tone_inventory`).
   - Only full tones 1–4 change. A neutral syllable keeps its tone, and no syllable becomes neutral.
   - Syllables written 一 or 不 keep their tone.
   - A change that only turns tone 3 into tone 2 before another tone 3 is a sandhi form, so it is excluded.
   - Never equal to any reading of the same lemma.

   A word with no valid K′, or no cached F with a valid F′, is not reading-ready.
4. **Estimator.** Per band, over the pair sample:
   - `pc` = meaning right and K chosen; `pkt` = meaning right and K′ chosen; `pf` = meaning right and F or
     F′ chosen; `n'` = pair-sample words.
   - The full reading: `K_mr = (pc − pkt)/n'`. Variance: the multinomial variance of y ∈ {+1, −1, 0}
     with a pseudo-count of 0.25 per category and the finite-population factor.
   - The syllables: `K_syl = (pc + pkt − pf)/n'`.
   - Two gaps with their own intervals, each shown only when clearly above 0: the **tone gap**,
     K_syl − K_mr ("meaning and pinyin, not the tones"), and the **reading gap**, K_m − K_syl.
   - Per-word groups gain "Meaning and pinyin, not the tones" for K′ answers. Those words go to reading
     practice (A2r, [[decisions/ADR-059-placement-evidence-kind]]).

   Under know-or-guess with three reading states (full, syllables only, none), P(K) − P(K′) is the
   share with the full reading, whatever the "I don't know" rate. Guessed meanings and syllables-only
   knowledge both cancel.
5. **The zh `sound_pair` probe is dropped**; ja keeps it for special morae.

## Consequences
- **Easier:** the result separates three states the owner cares about: full reading, pinyin without tones,
  and meaning only. Tone coverage goes from 10.9% of words to every reading-ready word. Choosing K′ is a
  direct, per-word tone diagnostic.
- **Harder:**
  - A new table (`calibration_zh_tone_inventory`, about 15 KB), a variant generator in SQL that must match a
    reference implementation, and two option columns (`option_roles`, `option_texts`), because generated
    options have no sense id.
  - Precision costs about 2 points of the pool. In simulation the zh m+r 95% half-width is ±15.2% (English
    L1) and ±17.5% (Japanese L1) at 60 items, against ±13.4% and ±15.3% with syllables-only items
    (ESTIMATE, E31, E33).
- **Constrained:**
  - **Partial tone memory is partly credited.** If learners who know the syllables pick the right tones
    65% of the time, the count is +2.1..+2.4% of the pool high (ESTIMATE); V9 rechecks measure it.
  - A learner may reject a variant because it "sounds wrong" without knowing the word. That is knowledge
    of the word's sound pattern, close to the claim (INFERENCE). V6 compares K′ and F′ choices.
  - Tone sandhi beyond the two excluded patterns, and erhua, are not modelled; the dictionary's citation
    tones are the key.
  - The guess model assumes uniform blind guessing among the four options.

## Alternatives Considered
- **Syllables only, tones untested (the previous default):** the owner wants pronunciation including tones.
- **One tone variant plus two segmental foils:** the key is always in the only pair of similar options. A
  test-wise guess is right half the time, and the segmental information is lost.
- **Three tone variants of the key:** gives the syllables away; cannot be built for 11% of words
  (band 7: 30%).
- **The ADR-058 correction `pc − prw/3` on the new items:** credits a third of the syllables-only words;
  +1.9..+3.3% of the pool too high in simulation.
- **ADR-051's pseudo-count of 0.5:** 98–99% coverage of 95% intervals, about 2 points of the pool wider
  than needed; 0.1 under-covered (93–94%).
- **Variants that change a neutral tone, or variants built from any tone:** optional neutral tones make
  some variants arguably correct; unattested syllable+tone pairs are made-up syllables, which the owner
  excluded.

## Evidence
[[features/vocab-placement.tech]] E31–E33. Scripts and outputs are in
`wiki/evaluations/vocab-placement-research-2026-11-18/tones/`: `tone_cover.py` (coverage; reads a SELECT
export), `tone_sim.py` (simulation on the research learner model with an added tone state; the θ range is
an assumption) and `synth/stop60.py`.

## Related Pages
- [[features/vocab-placement]] · [[features/vocab-placement.tech]] §2 rule 4, §5.1, §8, §13, §14
- [[decisions/ADR-057-adaptive-placement-with-conditional-reading]] · [[decisions/ADR-058-meaning-and-reading-recognition-pair-estimator]] · [[decisions/ADR-059-placement-evidence-kind]]
- [[tasklist/vocab-placement.tasks]] TASK-1092
- [[evaluations/vocab-placement-research-2026-11-18]]
