---
title: Vocabulary-Aware Test Selection
type: feature
status: in-progress
tech_page: vocabulary-aware-test-selection.tech.md
last_updated: 2026-09-10
open_questions:
  - "OPEN: what unknown-word target `u*` is actually right for a learner? The dropped RPC aimed at 3-7%; live JA content cannot reach that band today (best available is ~27% unknown at difficulty 1). Shipping with u* = 0.15 as a reachable interim."
  - "OPEN/BLOCKING: what exactly is `ability_zipf`? The tier ladder it maps onto is the native-speaker AGE tier (ADR-003), whose Zipf anchors are passage means; ability_zipf is a learner knowledge threshold. On live data an 85%-known threshold maps to 1250 and a 50% crossover to 1681 — a 430-point swing from the definition alone. Contract must be pinned with the parallel Calibration build before the seed ships."
  - "OPEN: should the per-test-type ELO offset be a fixed prior table or fitted per user from their own residuals? Live evidence supports fitting, but n=1 user and 21 first attempts is not enough to fit on."
  - "ANSWERED 2026-09-08: should difficulty become a hard filter? No — see ADR-024. It stays ELO-mediated, with a soft 2-tier ceiling as a safety rail only."
---

# Vocabulary-Aware Test Selection

## Purpose

Test selection currently ignores everything LinguaDojo knows about a learner's
vocabulary. This feature makes the recommender read `user_vocabulary_knowledge`
and the new Calibration ability estimate, so a learner is handed content built
from words they mostly know, plus a controlled sprinkle of words they do not.

## User Story

> "I opened Japanese pitch accent and got 14% on the first test, 18% on the
> next. It just feels too hard, and nothing I do seems to make it easier."

That is the complaint that started this. The learner is right, but the reason is
not the one you would guess, and the fix is not "make Japanese easier".

## What's Actually Wrong

A live audit on 2026-09-08 (27 Japanese attempts, 21 of them first attempts)
found **three independent defects**, only one of which is the missing
vocabulary signal.

### 1. Test ELO is blind to test type

A test's ELO is seeded from its *prose*, which knows nothing about whether the
learner is asked to read the passage, transcribe it, or identify a word's pitch
accent. The result: **48 of 60 Japanese tests carry an identical ELO across all
eight test types.** A pitch-accent test and a reading test on the same passage
are rated equally hard. They are not remotely equally hard.

### 2. The rating system compresses ability it cannot express

Working backwards from what the learner actually scored, their true ability per
skill is:

| Skill | First attempts | Mean score | Ability the scores imply | ELO the system assigned | Error |
|---|---|---|---|---|---|
| dictation | 1 | 87.0% | ~1539 | 1209 | system is 330 too low |
| reading | 8 | 73.1% | ~1498 | 1270 | system is 228 too low |
| listening | 7 | 67.1% | ~1396 | 1248 | system is 148 too low |
| pitch accent | 5 | 35.4% | ~1091 | 1182 | system is 91 too **high** |

**The learner's true ability spans 448 points across these skills. The system
has them inside an 88-point band.** Every skill is mis-rated; they simply
disagree about the direction.

This also reframes the complaint. Japanese is mostly too *easy* — reading,
listening and dictation are all under-rated, so the learner is served content
below their level. Only pitch accent is genuinely too hard, and it dominates the
felt experience because six of seven attempts scored under 50%.

### 3. There is no way out through practice

Multiple-choice scores have a floor: a learner who knows nothing still scores
around chance, not zero. That floor puts a hard ceiling on how far ELO can ever
move a learner away from the content pool — roughly 190 points for a four-option
question. So even in principle, taking more tests cannot walk the learner to
where they belong when the gap is larger than that. The only way user ELO moves
is by taking the tests that are already mismatched, and each one shifts it by
about 2 to 10 points.

**That is why this cannot be fixed by tuning ELO. The rating system is
structurally unable to represent the gap.** Vocabulary knowledge has to enter
selection directly.

## The Signal We Already Have and Ignore

Vocabulary knowledge carries exactly the information ELO is missing. For this
learner's Japanese, the share of a test's words they already know is:

| Test difficulty | Words per test | Share the learner knows |
|---|---|---|
| 1 | 13 | 73% |
| 6 | 44 | 17% |
| 9 | 74 | 9% |

That is a clean, steep gradient — everything ELO fails to provide. It is sitting
in the database, unread by the recommender.

## How It Works

1. **Calibration seeds the starting point.** When a learner finishes Calibration
   mode, their measured vocabulary ability is translated into a starting ELO for
   each of reading, listening, dictation and pitch accent, using the same tier
   ladder the content itself was seeded from. This replaces the 1200 default
   that everyone starts at regardless of level.

2. **Selection scores vocabulary coverage.** For each candidate test, the system
   estimates what fraction of its words the learner knows, and prefers tests
   sitting near a target unknown-word rate — enough new words to learn from,
   few enough to still follow the passage.

3. **Words we have never tested get a frequency-based estimate.** This matters
   more than it sounds. At difficulty 9, **90% of a test's words have no record
   at all** for this learner — they are untested, not proven unknown. Treating
   them as unknown would score every piece of fresh content identically at the
   bottom, and would get worse as the catalogue grows. Instead, an untested word
   is estimated from how common it is, relative to the learner's calibrated
   level.

4. **Tests without linked vocabulary are not punished.** Japanese tests are 100%
   linked to the dictionary, but English is 83% and Chinese 78%. An unlinked
   test gets a neutral score — "no opinion" — rather than winning or losing by
   default. A hard vocabulary filter would silently empty the candidate pool for
   a fifth of the catalogue, so vocabulary is a ranking signal, never a gate.

## Constraints & Edge Cases

- **No calibration yet** — selection behaves exactly as it does today.
- **Test not linked to vocabulary** — neutral vocabulary score, ranked on ELO alone.
- **Word has no frequency data** — excluded from the coverage ratio rather than
  counted as unknown (~1-3% of Japanese test words).
- **Calibration disagrees with a learner's established rating** — the learner's
  own test history wins. Calibration seeds; it does not overrule.
- **The learner is mid-session** — no calibration write lands within an hour of a
  test attempt, so a rating never moves under someone.

## Business Rules

1. Vocabulary coverage **ranks** candidates. It must never remove the last
   candidate from a pool.
2. Calibration may write a skill rating **only** when the learner has few
   attempts for that skill, or when it disagrees with the live rating by a wide
   margin — and then only by a damped, capped amount, at most once a week.
3. Every calibration-driven rating write is recorded with its before value,
   after value and reason. Skipped writes are recorded too, with why.
4. A calibration-derived rating is never placed outside the tier ladder's range
   (875-1925). Outside it, we have no calibration to stand on.
5. `process_test_submission` is **not modified**. It is the other writer of user
   ELO and it has already drifted from the repo once; the two writers stay
   separated by guards, not by edits to a function nobody has a clean copy of.

## How We'll Know It Worked

The complaint is subjective, so the check is not. The primary measure is the
share of first attempts landing in a 60-85% band — challenging but passable.
Today, Japanese pitch accent puts **6 of 7 attempts under 50%**.

Because there is exactly one live learner, an A/B test is not available. The
before/after is an offline replay: re-rank the tests this learner was actually
served, at the point they were served, and compare the unknown-word rate of the
old and new selections. See the tech page for the full metric set.

## Related Pages

- [[features/vocabulary-aware-test-selection.tech]] — technical specification
- [[decisions/ADR-024-vocabulary-aware-test-selection]] — why vocabulary ranks rather than filters
- [[features/comprehension-tests]] — the surface this feeds
- [[algorithms/elo-ranking]] — the rating system being supplemented
- [[algorithms/elo-implementation-analysis]] — dual-ELO mechanics
- [[algorithms/bkt-implementation-analysis]] — where `p_known` comes from
- [[database/schema.tech]] — `user_vocabulary_knowledge`, `user_calibration_state`
- [[api/rpcs.tech]] — `get_recommended_tests`
- [[tasklist/vocabulary-aware-test-selection.tasks]] — task breakdown
