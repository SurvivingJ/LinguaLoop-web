---
title: Vocabulary-aware selection — baseline reproduction and offline replay
type: evaluation
status: complete
last_updated: 2026-09-10
---

# Vocabulary-aware selection — baseline reproduction and offline replay (2026-09-10)

TASK-749. Produced by `scripts/measure_selection_quality.py`, which is read-only;
the full JSON was written to a scratch file and is not kept in the repo. The
ranker under test is `recommended_tests_ranked()` from
[[features/vocabulary-aware-test-selection.tech]], the same function
`get_recommended_tests` calls when `vocab_weight > 0`. **`vocab_weight` is still 0
live, and this page does not change that.**

## 1. The 2026-09-08 ja baseline, reproduced exactly

| metric | recorded baseline | reproduced |
|---|---|---|
| M1 reading | 3/8 | **3/8** |
| M1 pitch accent | 0/5 | **0/5** |
| M2 pitch accent | 6/7 | **6/7** (overall 7/27) |
| M3 | 448 vs 88 | **448 vs 88** (ratio 5.09) |

Implied ability per type: dictation 1539, reading 1498, listening 1396, pitch
accent 1091. All four match §0.3(b).

**It reproduces only under the baseline's operative definitions**, which differ
from §5.1's wording, so the tech spec now records them:
- **M1 is half-open, (60, 85].** Two ja reading first attempts are stored at
  exactly 60% (3/5), and `[60, 85]` gives 5/8.
- **M2 counts all attempts.** Pitch accent's 7 attempts include 2 retakes;
  over first attempts only it is 4/5.
- **M3 rounds** per-type implied ability to whole points before the spread;
  unrounded it is 447.x.
- The baseline's "mean %" column is the mean of the *clamped* s (73.1 / 67.1).
  Unclamped it is 74.4 / 67.9.

zh, never baselined, shows the same compression: 309 vs 70 (ratio 4.41).

## 2. Replay — 21 ja first attempts, as of each timestamp

Each attempt's candidate set is reconstructed as of its timestamp (attempts, topic
recency, test existence, per-type ELO, and uvk rows created before it) and ranked
under both arms. The numbers below are for the top-10 of the attempted type.

| arm | top-10 unknown (median, IQR) | inside u*±tol [0.05, 0.25] | top-10 difficulty (p25 / median / p75) | taken test's rank (median) |
|---|---|---|---|---|
| `vocab_weight = 0` (today) | 0.201 (0.132–0.246) | **77%** | 1 / 6 / 6 | 2 |
| `vocab_weight = 1` | 0.183 (0.142–0.207) | **93%** | 6 / 6 / 6 | 6 |

- **Served unknown share tightens around u* = 0.15.** The IQR halves (0.114 →
  0.065), and the upper tail that weight 0 serves (up to 0.41 by 09-08) is cut
  to ≤ 0.31.
- **Served difficulty consolidates on d6.** Weight 0 mixes d1 and d6. Weight 1
  drops the d1 tests, whose unknown share (~0.05–0.10) is *below* the target
  for this learner. So ja-is-too-easy shows up here as well, and the change
  moves content *up*, not down.
- **Mean top-10 overlap between arms is 0.40** (Jaccard), so the term
  materially changes what is served.
- **The signal is real.** Across the 13 attempts whose test was still a
  candidate as of its timestamp, the taken test's unknown share correlates with
  the score it got at **Spearman −0.59**. More unknown words, lower score.
- **The prior ran on the fallback throughout.** `ability_zipf` came from the
  learner's own uvk 85% crossing and rose from 4.0 (08-24) to 4.9 (09-08). No
  slot was neutral, because ja is 100% linked. Calibration has 0 rows, so this
  is the path production would take today.
- **Pitch accent is not fixed by this, as predicted.** Its top-10 unknown
  distribution is the reading one, because pitch-accent tests are the same
  passages. The defect is the type-blind test ELO (TASK-751).

**Caveats.** The replay approximates; it does not re-enact:
- Test ELOs and later-updated `p_known` values cannot be rewound, and
  TASK-732 reseeded ja dictation and pitch accent on 2026-08-22.
- 8 of 21 taken tests are not in the as-of candidate set. The main reason is
  that TASK-740's topic-recency exclusion, live since 2026-08-30, now removes
  the second type of a same-topic pair the learner took minutes apart.
- "Taken test's rank" measures agreement with the old ranking, which served
  those tests. A lower rank under weight 1 is not a defect.

## 3. M4 / M5 — served now, per arm (current state)

| learner, language | ability (source) | effect |
|---|---|---|
| ja | 5.025 (uvk crossing) | M5 10 → 10 on every type. M4 median unknown 0.31–0.33 → 0.29–0.30. Only 10–20% in band under either arm, because the remaining unattempted ja pool has little content near 0.15. |
| zh | 5.152 (uvk crossing) | M5 10 → 10 on every type. **At weight 0, 8 of 10 served zh reading/dictation/pinyin tests are unlinked**, since the nearest ELOs belong to unlinked tests. At weight 1 they give way to linked tests, and in-band goes 0% → 80–100%. |
| en, and every other user | none | Every candidate is neutral, and weight 1 ranks by ELO with a deterministic tie-break. |

**M5 never fell.** This matches the parity test's pool-health result across all 39
(user, language) pairs.

## 4. Findings outside the metric

- **zh and en tests carry `pitch_accent` rating rows** (34 and 38), and en has 8
  `pinyin` rows. So `get_recommended_tests` can serve zh learners pitch-accent
  candidates (the zh M5 row above), a pre-existing backfill artefact.
- **`process_test_submission` is NULL-permissive on auth**, and `anon` holds
  EXECUTE on it. Its `p_user_id != auth.uid()` passes when there is no JWT
  subject. Not modified here, because this feature forbids it.

## Related

- [[features/vocabulary-aware-test-selection.tech]] §5 · [[decisions/ADR-024-vocabulary-aware-test-selection]]
- [[tasklist/vocabulary-aware-test-selection.tasks]] (TASK-749, TASK-751)
