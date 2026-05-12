---
title: Vocabulary Ladder
type: algorithm
status: in-progress
tech_page: ./vocabulary-ladder.tech.md
last_updated: 2026-05-12
open_questions:
  - "Will the contextual_use family (and a Level 10 capstone) be implemented, or has it been deferred indefinitely?"
---

# Vocabulary Ladder

## Purpose

The Vocabulary Ladder takes a learner from zero knowledge of a target word to long-term memory through a sequence of exercises that escalate from receptive recognition to productive use. It is grounded in Paul Nation's nine-component model of word knowledge — recognition is acquired before recall, and form before use. As of Phase 8 (2026-04-18), progression is driven by a per-family Bayesian confidence model called **Momentum Bands**, not by counting first-try successes on a single 9-rail chain. The two earlier ladder shapes (the 10-level chain in the original spec and the simple promote-on-2-cross-session-successes counter model that the Phase 4 schema was sized for) have both been superseded — see [[decisions/ADR-005-momentum-bands]] for the rationale.

## User Story

When a learner encounters a new word — through a Language Pack, comprehension test, or Vocab Dojo — the system stores a row in `user_word_ladder` with six per-family confidence scores all initialised to 0.10. Every exercise the learner attempts updates one of those six scores via a Bayesian learn-rate / slip-rate update. The system never asks the learner to choose a difficulty level: it pulls the weakest family the word still needs to demonstrate inside the current ring, and serves an exercise that targets it.

The learner moves through four **rings** as the family confidences crest threshold lines. Between rings 2 and 3, and between rings 3 and 4, the system asks the learner to pass a short **threshold gate** — a 3-exercise battery they must clear at least 2-of-3 on. After ring 4, an 8-exercise **stress test** acts as the graduation exam. Pass it, and the word becomes `mastered` — handed off to FSRS-4.5 for long-term maintenance. Fail it, and the word drops to `relearning` and the rings rebuild confidence before another graduation attempt.

If the learner gets an exercise wrong, they see the pedagogical reasoning for why and must keep trying until they get it right. Only the first attempt counts toward family-confidence updates; subsequent retries are scheduling signal for FSRS only.

## How It Works

### Nine Levels Across Four Rings

The ladder still exposes nine exercise types, organised into four rings:

| Ring | Levels | Exercise Types | Cognitive Family |
|------|--------|----------------|------------------|
| R1 | 1, 2 | Phonetic Recognition, Definition Match | form_recognition |
| R2 | 3, 4, 5 | Cloze Completion, Morphology Slot, Collocation Gap | meaning_recall, form_production, collocation |
| R3 | 6, 7 | Semantic Discrimination, Spot Incorrect Sentence | semantic_discrimination |
| R4 | 8, 9 | Collocation Repair, Jumbled Sentence | collocation, form_production (advanced) |

Each level targets a single failure mode (semantic, structural, collocational, morphological, etc.) so an attempt is interpretable as evidence about a specific cognitive family.

### Six Cognitive Families

Every attempt updates the confidence of exactly one family. Five families are exercised by the current 9-level ladder; a sixth (`contextual_use`) is weighted into overall p_known and reserved for a future capstone level.

| Family | Levels | Weight in p_known |
|--------|--------|-------------------|
| form_recognition | 1, 2 | 0.12 |
| meaning_recall | 3 | 0.18 |
| form_production | 4, 9 | 0.20 |
| collocation | 5, 8 | 0.16 |
| semantic_discrimination | 6, 7 | 0.16 |
| contextual_use | — (future L10) | 0.18 |

Overall p_known is the weighted sum. Because `contextual_use` has no live exercise type, its confidence stays at the 0.10 default — which mathematically caps a word's overall p_known at ≈ 0.92 until the capstone ships.

### Ring Advancement

A ring is "cleared" when **both** conditions hold for every required family:

1. Family confidence ≥ its ring threshold (R1, R2 → 0.50; R3 → 0.65; R4 → 0.72).
2. The family has had first-attempt successes on at least 2 distinct calendar days. This **cross-session gate** (Phase 10, 2026-05-12) prevents a single good afternoon from racing a word up the rings. The history is stored in `family_success_dates` and trimmed to the most recent two dates per family.

When a ring clears, three things can happen:

- **R1 → R2** is automatic. No gate.
- **R2 → R3** stalls into `word_state = 'gated'` until Gate A is passed.
- **R3 → R4** stalls into `word_state = 'gated'` until Gate B is passed.
- **R4 cleared + Gate B passed + overall p_known ≥ 0.88** transitions the word to `word_state = 'pre_mastery'` and flags it stress-test-ready.

### Ring Demotion

A word loses a ring (Phase 10, 2026-05-12) when:

- The current attempt is a first-attempt failure.
- The failing family is one of the families that *gates* the current ring.
- The per-family `consecutive_failures` counter reaches 3 (resets on any success or on a different family being exercised).
- The word is not at R1 (the floor) and not in `mastered` or `new` state.

On demotion:

- `current_ring` drops by 1.
- The gate guarding exit from the dropped-into ring resets (`gate_a` on demote→R2, `gate_b` on demote→R3). Other gates survive as lifetime achievements — a word that earned Gate B once doesn't lose it on a demotion from R3 down to R2.
- `family_success_dates` for the demoted-into-ring required families is cleared; the learner must re-establish cross-session stability before climbing back.
- `consecutive_failures` resets to 0.

A word in `mastered` state that fails goes through the **lapse path** instead (described below), not the demotion path.

### Threshold Gates

A gate is a short 3-exercise battery drawn from the ring being unlocked. The learner needs at least 2 of 3 correct on first try. Gates use a gentler BKT update (learn 0.18 / slip 0.10) so passing or failing one moves the family more decisively. On pass, [ladder_pass_gate](../../migrations/phase8_momentum_bands.sql) marks `gates_passed.gate_a` (or `gate_b`) true, advances `current_ring`, and recomputes `word_state`. On fail, each battery exercise is recorded as a normal attempt, the family confidences degrade, and the learner gets another chance once the ring re-clears.

### Stress Test and Graduation

When a word reaches `pre_mastery`, an 8-exercise battery becomes available with a fixed composition: 2 form_production / 1 meaning_recall / 1 form_recognition / 1 collocation / 1 semantic_discrimination / 2 contextual_use. The learner needs ≥6/8 correct. On pass, `ladder_graduate`:

- Transitions `word_state = 'mastered'`, `review_due_at = NULL`.
- Initialises FSRS-4.5 state from the acquisition trace: stability from overall p_known plus a stress-test bonus, difficulty from p_known plus a family-variance penalty.
- Schedules the first maintenance review at `today + round(0.6 · stability)` days (deliberately earlier than the full computed interval — safer at the handoff boundary).

On fail, the word stays in `pre_mastery` and the learner can attempt the stress test again once family confidences recover.

### The Lapse Path

A word in `word_state = 'mastered'` that fails any exercise is detected by `ladder_record_attempt` as a lapse: the failed family takes an additional 30% confidence penalty, the word state drops to `relearning`, and (if a flashcard exists) FSRS is told "AGAIN." `bkt_apply_lapse_penalty` also degrades the row in `user_vocabulary_knowledge`. The word now has to climb back through the rings — but it keeps its `gates_passed` flags, so it skips the gate batteries on the way up.

### Momentum Band Scheduling

Pre-mastery scheduling lives in three bands:

| Band | Overall p_known | Next review |
|------|----------------|-------------|
| Low | < 0.45 | tomorrow |
| Medium | 0.45–0.75 | tomorrow |
| High | ≥ 0.75 | +2 days |

A first-attempt failure always overrides the band and pulls the review back to tomorrow. Post-mastery scheduling is FSRS-driven (see [[features/flashcards]]).

### Session Composition

Vocab Dojo sessions are assembled by [get_ladder_session](../../migrations/phase8_momentum_bands.sql) — a single SQL RPC that scores each candidate word by

```
priority = 0.35·overdue + 0.25·weakness + 0.20·gate_urgency + 0.10·novelty + 0.10·relapse
```

…picks the top N, then picks one exercise per word, preferring the target family for that word's current ring and rotating A/B variants. Words seen earlier the same day are filtered out; concrete-noun rows skip levels 5 and 8 via `active_levels`.

### POS and Semantic-Class Routing

Concrete nouns skip the two collocation levels (5, 8). This is stored on `user_word_ladder.active_levels`, computed at row creation from the word's `semantic_class`. `ladder_ring_families` consults `active_levels` so a concrete noun's R2 doesn't require collocation — it only needs meaning_recall and form_production to clear.

### Generate-Once, Use-Forever

All exercise assets are still generated once per word and cached permanently in `word_assets` and `exercises`. A learner who encounters the same exercise twice is being tested on the same item, making the performance trajectory meaningful. Phase 8 added A/B variants — for several exercise types the pipeline generates two parallel batteries from disjoint sentence pools, and the session builder alternates variants to reduce memorisation effects.

## Constraints & Edge Cases

- Age Tiers (not CEFR) drive the vocabulary and grammar complexity of generated sentences.
- Per-option pedagogical reasoning is generated alongside each exercise and cached, so feedback is instant without a runtime LLM call.
- `active_levels` is set at ladder-row creation and effectively immutable — a word's POS doesn't change.
- Level 2 uses database definitions (not LLM) — distractors are sampled from other senses in the same tier.
- Level 9 uses backend tokenisation (e.g. jieba for Chinese) — no LLM generation needed.
- The Phase 4 counter columns (`first_try_success_count`, `first_try_failure_count`, `consecutive_failures`, `last_success_session_date`) are still maintained on every attempt but are not read by any progression code path. They survive as observability data; consider them an open question (see frontmatter) until either wired in or dropped.

## Business Rules

- A word can be in exactly one `word_state` at a time: `new`, `active`, `gated`, `pre_mastery`, `relearning`, or `mastered`.
- Only first attempts move family confidence. Retries on the same exercise within a session affect FSRS scheduling but not BKT or family confidence.
- Once mastered, a word's `review_due_at` is `NULL` — FSRS owns it from here.
- A lapse keeps the word's `gates_passed` flags: graduation is a path the learner has walked, even after a regression.
- Ring demotion resets only the exit gate of the dropped-into ring. A demotion from R3 to R2 invalidates Gate A but leaves Gate B intact; the learner re-earns Gate A but skips Gate B when they climb back.

## Related Pages

- [[algorithms/vocabulary-ladder.tech]] — Full technical specification
- [[algorithms/ladder-implementation-analysis]] — Code audit (2026-05-11 refresh)
- [[features/exercises]] — Exercise type inventory
- [[features/vocab-dojo]] — How the ladder is served
- [[features/language-packs]] — Pack context for word introduction
- [[features/vocabulary-knowledge]] — BKT integration (overall p_known)
- [[features/flashcards]] — FSRS handoff after graduation
- [[decisions/ADR-005-momentum-bands]] — Why the system changed from counter-based to family-BKT × rings × gates
- [[decisions/ADR-003-age-tiers]] — Age Tier difficulty system
