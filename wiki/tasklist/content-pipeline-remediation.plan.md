---
title: "Content Pipeline Remediation — Plan"
date: 2026-08-31
status: executed 2026-09-01
scope: test dedup, test-gen throughput, topic tier coverage, practice intake
---

# Content Pipeline Remediation

Four reported problems, ground-truthed against code and the live Supabase
project (`kpfqrjtfxmujzolwsvdq`) on 2026-08-31. **Three of the four diagnoses
changed materially once measured.** Read §0 before planning any work.

---

## 0. What the data actually says

| # | Reported | Measured | Verdict |
|---|---|---|---|
| 1 | Lots of duplicate questions | 9.4% dupe stems; choice sets ~all unique (2 of 29 groups share one) | **Reframed** — formulaic stems, not duplicate content |
| 2 | Judging calls make tests expensive | Judges ≈ $0.001/test; generation ≈ $0.015/test | **False as stated** — judges are 6% of spend; the real cost is wall clock |
| 3 | Topic gen doesn't scale with tier | T1→T6 passage 350→4802 chars, vocab 22→266 senses; T1 topics age-appropriate | **False as stated** — scaling works; coverage and novelty-threshold do not |
| 4 | Not enough words in practice engine | 12,048 active exercises; **3** attempts ever; 0 sessions | **Reframed** — starvation is 4 broken links, not content volume |

---

## 1. Duplicate questions — stems, not content

### Root cause
Duplication is concentrated in the two *topic-independent* question types:
`main_idea` (3) and `author_purpose` (6). Worst offender is a ja stem appearing
**36 times across 36 different topics**:

> この文章における筆者の態度として最も適切なものはどれか。

The choice sets behind those 36 are entirely distinct (fermentation, wine
terroir, venture capital…). So the generator is doing its job; the *surface
phrasing* is what reads as repetitive.

### Why the in-flight work won't fix it
`services/test_generation/dedup.py` (TASK-740 Phase 5) scopes both checks to
`(topic_id, target_age_tier)` and deliberately never compares across tiers.
Only **5 of 29** dupe groups are within-topic. It will catch ~17% of this.

### Tasks
- **T1.1 (S)** — Stem-template rotation. Give each `question_type` × language a
  pool of 5–8 equivalent stem phrasings; select by hash of `test_id` so it is
  deterministic and needs no extra LLM call. Zero marginal cost.
  Files: `services/test_generation/agents/question_generator.py`, prompt
  templates in DB (see `scripts/stage_task721_templates.py` for the pattern).
- **T1.2 (S)** — Recent-stem exclusion. Pass the N most recent stems for that
  `(language, question_type)` into the question prompt as a "do not reuse"
  list. Reuses the TASK-740 recency pattern.
- **T1.3 (XS)** — **Verify the new tier mix on first run.** Legacy T6 content
  shows `supporting_detail` = 0 and `author_purpose` at 2× the intended rate.
  All 307 tests predate `question_type_distributions_by_tier` (created
  2026-08-29) — **zero tests have run through the new path**. The loader
  (`database_client.py:590`) looks correct, but assert the realised mix matches
  the table on the first batch before assuming it is fixed.
- **T1.4 (XS)** — Reconsider whether `author_purpose` deserves 1 of 5 slots at
  T6 given it is inherently the most templated type.

---

## 2. Test-gen wall clock (2.9 min/test)

### Root cause
Not judging. Per-test judge spend is ~$0.001 against ~$0.015 of generation.
The wall clock is **vocab enrichment**: one LLM `generate_sense()` call per
extracted word, fanned across only 3 workers.

Enrichment volume scales brutally with tier:

| Tier | avg vocab senses/test (en) |
|---|---|
| T1 | 22 |
| T2 | 34 |
| T4 | 107 |
| T6 | **266** |

A T6 test makes ~266 sense calls at 3-way concurrency. That is the 2.9 minutes.

Concurrency is already capped for a real reason: at 5×3 workers, Supabase and
Cloudflare began rejecting requests outright (`config.py` documents this). **So
more threads is not the lever.**

### Tasks
- **T2.1 (S)** — Instrument first. Log the `prefer_existing=True` hit rate per
  batch. If most words are already seeded, the fix is pre-seeding, not batching.
  Files: `services/test_generation/orchestrator.py:940-1010`.
- **T2.2 (M)** — Batch sense generation: one LLM call per *N words* instead of
  one per word. This cuts wall clock without raising DB concurrency — the
  correct lever given the Cloudflare ceiling.
- **T2.3 (M)** — Cap inline enrichment per test (e.g. top 40 by frequency) and
  push the tail to the existing async backfill (`scripts/backfill_senses.py`).
  A T6 test does not need all 266 senses enriched synchronously.
- **T2.4 (S)** — Pre-seed a frequency-ranked shared sense bank per language so
  `prefer_existing` hits far more often.

**Do not** cut judges for cost. If throughput still binds after T2.2/T2.3,
judges skip `d≤2` already; widening that band is a last resort, and note that
no reject signal is gold-validated yet (see `distractor-judge-v3-likert`).

---

## 3. Topic generation — coverage and novelty, not scaling

### What is already fine
The per-tier Explorer (6 tier-specific prompts) works. T1 concepts are
genuinely age-appropriate: *"A red ball bouncing"*, *"Baby's first bath time"*.
Passage length and vocab load scale cleanly across tiers.

### Three real problems

**3a. Tier coverage gap.** Tests cluster at tiers 1/2/4/6 (71/61/92/80) while
T3 and T5 have **one test each** — a legacy artifact of
`target_difficulties = [1,3,6,9]`.

**3b. Low-tier novelty threshold is too loose.** Only 1 topic pair exceeds 0.90
cosine, yet T1 contains all of:
*"A child building a block tower"*, *"A child building a toy castle with
blocks"*, *"A child building with colorful blocks"*.
At T1 the legitimate concept space is small and the vocabulary is constrained,
so a fixed global threshold under-rejects. **The threshold should scale with
tier** — stricter at low tiers (~0.82), looser at high (~0.90).

**3c.** 43 of 183 topics have no `target_age_tier`.

### On the proposed per-tier topic judge

The idea: a judge that returns an age-tier-appropriate rewrite of a topic for
each tier, blanking tiers where the language would be too hard.

**The "blank if unsuitable" half is the valuable half** and should be built —
as a *tier-fit validator* on existing Explorer output, judging
`distinctive_vocabulary` against the stamped tier. That directly targets the
"we get difficult vocab" symptom and is cheap.

**The fan-one-topic-across-6-tiers half is risky** and I would not do it as the
default path, for three reasons:

1. **It amplifies problem #1.** Dedup deliberately never compares passages
   across tiers (`dedup.py` docstring). Six tier-variants of one concept become
   six topic rows that no dedup check will ever compare, and a learner
   progressing T1→T2→T3 meets the same concept repeatedly.
2. **The Explorer is not the thing that is broken.** Per-tier ideation already
   produces good, age-appropriate topics. Replacing a working generator to fix
   a coverage gap is disproportionate.
3. **Asking for all 6 tiers in one call invites over-production.** An LLM told
   "blank if unsuitable" treats blanking as failure and will fill all six. This
   is the same trap recorded in `ja-l1-judge-and-generator-doctrine` — a closed
   enumeration in a judge prompt behaves as an allow-list. Ask **per tier,
   independently**, so each decision is a real yes/no.

### Tasks
- **T3.1 (S)** — Tier-fit validator judge: given a topic + its stamped tier,
  return pass/fail plus reason, judged on `distinctive_vocabulary` difficulty.
  One call per candidate, per tier, independently. **Not** a 6-tier fan-out.
- **T3.2 (XS)** — Make the Archivist novelty threshold tier-scaled
  (~0.82 at T1 → ~0.90 at T6). Cheapest, highest-value fix in this section.
- **T3.3 (S)** — Targeted backfill for T3/T5 only, where coverage is thin.
  If fan-out is used at all, use it here — bounded, not universal.
- **T3.4 (XS)** — Backfill the 43 untiered topics.
- **T3.5 (S)** — *Prerequisite if any cross-tier fan-out ships:* concept-level
  session exclusion so one concept cannot appear at consecutive tiers.
  `ADR-023-topic-recency-session-exclusion.md` is the right home.

---

## 3d. Exercise depth — context-free types over-generate

### The measurement
Sense 9972 — 做 (zuò), frequency rank 6.08 — carries **33 active exercises
across 12 types**. That is not 33 redundant drills: it is ~2–3 variants of 12
genuinely distinct skills, and the context-bearing ones legitimately differ
because each is mined from a different source passage (`source_test_id` varies).

**An earlier draft of this plan recommended capping at 6–8 per word. That was
wrong** — it would delete whole skill types rather than trimming redundancy.

### The real redundancy
Exercise types split cleanly into two classes:

**Context-bearing** — the item is anchored to a sentence, so each variant is a
genuinely different question: `cloze_completion`, `cloze_typed`,
`text_flashcard`, `listening_flashcard`, `tl_nl_translation`,
`nl_tl_translation`, `jumbled_sentence`, `semantic_discrimination`,
`spot_incorrect_sentence`, `spot_incorrect_part`, `collocation_gap_fill`,
`collocation_repair`.

**Context-free** — the item is a property of the *word itself*, so there is
exactly one meaningful question per word: `tone_id_word`, `hanzi_to_pinyin`,
`pinyin_to_hanzi`, `kanji_to_reading`, `reading_to_kanji`,
`phonetic_recognition`, `definition_match`.

For 做 the context-free duplicates are pure waste:
- `tone_id_word` ×2 — byte-identical (`做` → `["4","3","2","1"]` → `4`)
- `hanzi_to_pinyin` ×2 — same four options, order shuffled
- `pinyin_to_hanzi` ×2 — same four options, order shuffled

A word has one tone. Option order is a render-time concern and shuffling it
costs nothing at serve time.

`definition_match` is the judgement call: its variants differ in their
*distractor definitions*, drawn from other words. It is context-free with
respect to the target word, but 2–3 variants have some value. Recommend
capping at 2 rather than 1.

### Tasks
- **T3d.1 (XS)** — Classify every `exercise_type` as context-free or
  context-bearing. `dim_exercise_types` is the natural home for the flag; a
  module-level constant is acceptable if adding a column is disproportionate.
- **T3d.2 (S)** — Enforce a per-`(word_sense_id, exercise_type)` cap at
  generation time: 1 for context-free, 2 for `definition_match`, uncapped
  (supply-limited) for context-bearing. Enforce as a DB partial unique index
  as well as an application check, so a re-run cannot reintroduce duplicates.
- **T3d.3 (XS)** — Shuffle options at render time, so a single stored
  context-free item still presents differently across sessions. Confirm the
  serve path does not already do this before adding it twice.
- **T3d.4 (S)** — Deduplicate existing content. Across 387 covered senses the
  saving is ~9% of rows; the point is not the storage, it is that the same
  generation budget then buys breadth instead of shuffled repeats.

**Sequencing note:** do T3d.2 *before* the demand-driven generation in §4,
or the new pull-based generator will reproduce the same duplication on a
much larger set of words.

---

## 4. Practice engine — intake redesign

12,048 active exercises exist. `exercise_attempts` = **3**.
`user_exercise_sessions` = **0**. This is not a content-volume problem.

### 4a. The supply ceiling is narrower than it looks
Those 12,048 exercises cover only **387 distinct senses** (~31 each). Tests
have introduced **11,994** distinct senses, of which **364** have any exercise
— **3% coverage**. So "gate subscription on senses that have exercises" is
still the right first move, but it buys ~387 words, not 12,000: enough to
bootstrap daily sessions, not a curriculum.

### 4b. Why the current intake is dead
| Link | State | Effect |
|---|---|---|
| 1. Packs exist | `collocation_packs` = **0 rows** | Nothing to draw from |
| 2. Pack→sense bridge | `pack_key_words` **does not exist** | Query throws, swallowed into `logger.warning` |
| 3. Eligibility gate | Self-locking | Intake disarmed after first seed |
| 4. Sense→exercise coverage | **3 of 24** ladder senses have exercises | 21 subscribed words unservable |

Note link 2 is not merely a wrong name: the real packs table
(`collocation_packs`, bridged by `pack_collocations`) maps packs to
*collocations*, not senses. **A pack→sense bridge was never built.**

### Link 3 — FIXED this session
`_maybe_auto_subscribe_from_packs` returned early if the user had *any*
eligible ladder row. The rows it inserts are `state='new'` — itself in the
eligible set — so the first cold-start seed permanently disarmed all later
intake. Live: 24 rows, all still `new`.

Replaced with a **top-up to `target_active_pool(daily_minutes)`**, capped at
`LADDER_TOPUP_MAX_PER_CALL` (12) per call. Also corrected a unit error: the old
code spent `target_new_rate` as a per-call count, but its own docstring defines
it as a per-**week** rate.

- `services/practice_session_service.py` — gate → floor
- `tests/test_ladder_topup.py` — 10 tests, passing

This changes nothing live on its own; it stops the lock-up recurring.

---

### 4c. Target design — two queues, one supply gate

Intake should hang off **evidence from tests the learner is already taking**,
with packs demoted from "the entire mechanism" to "the cold-start fallback".

**Queue A — Evidence (priority).** Both signals are *already recorded*;
nothing new needs collecting. `user_vocabulary_knowledge` carries, per user per
sense: `p_known`, `status`, `evidence_count`, `last_evidence_at`,
`word_test_correct/wrong` (the post-test quiz signal) and
`comprehension_correct/wrong` (the wrong-answer signal). Wrong answers also
link to senses via `question_attempt_results` → `questions.sense_ids`
(populated on 1,195 of 1,424 questions).

Nominate a sense when `status IN ('unknown','learning')`, or
`word_test_wrong > 0`, or it appears in a question answered incorrectly.
Rank by wrong-count, then `last_evidence_at`, then frequency.

**Do not subscribe on a single wrong answer** — one miss can be a careless
click or a bad distractor. Require `evidence_count >= 2` or `p_known` below a
threshold. The column already exists for exactly this.

**Queue B — Packs (backfill).** Used only when evidence is thin: a brand-new
learner with no test history, or one who has cleared Queue A. This is where
curriculum breadth comes from and is the only reason to keep packs.

**Drain A first, then top up from B to reach the pool floor.** A learner who
is actively testing gets an entirely personalised ladder; packs fill gaps.

**The supply gate (the piece that makes it work).** Between nomination and
subscription:

> nominated sense → check exercise coverage → if ≥K exercises, subscribe now;
> if fewer, enqueue for exercise generation and subscribe when ready.

Today Queue A would nominate 43 senses (11 `unknown` + 32 `learning`) of which
**3** have exercises — the exact dead-end failure already happening. The gate
is what prevents that, and it inverts generation from speculative to
**demand-driven**: budget is spent on words a learner has demonstrably failed,
instead of on a 31st variant for 做.

### Tasks (ordered — critical path to "20 items/day")
- **T4.1 (S)** — **Supply gate first.** Never admit a sense to the ladder
  without ≥K active exercises. One filter; prevents dead-end words regardless
  of which queue nominated them. Immediately makes the 387 covered senses
  reachable.
- **T4.2 (M)** — Queue A off `user_vocabulary_knowledge` +
  `question_attempt_results`. Requires `evidence_count >= 2`.
- **T4.3 (M)** — Demand-driven exercise generation for nominated senses that
  fail the gate. **Depends on T3d.2** or it will over-generate.
- **T4.4 (S)** — Queue B: seed `collocation_packs` (0 rows) and build the
  missing pack→sense bridge. Cold-start only.
- **T4.5 (S)** — Stop swallowing the failure: `except Exception:
  logger.warning` around the pack query turned a missing table into a silent
  no-op for its entire lifetime. A missing bridge must be loud.
- **T4.6 (S)** — Session-size floor: guarantee ≥20 items per daily session,
  backfilling from review/FSRS when acquisition is short.
- **T4.7 (XS)** — Add `created_at` to `user_word_ladder` so a true per-day
  intake cap is expressible. The per-call cap is an interim guard.

---

## 5. Content integrity — mangled `is_correct` keys (FIXED)

Five live `semantic_discrimination` exercises stored a sentence's correctness
flag under a hallucinated key: `is_context`, `is_equal`, `is_logger`, and
`is游戏副本` (×2). All five are zh, and all five are in the `hant` variant only
— the simplified sibling is intact.

**Not the OpenCC path.** `services/vocabulary_ladder/script_converter.py:102`
does `{k: self.convert_content(v) for k, v in obj.items()}` — keys preserved,
values converted. These `hant` blocks were LLM-authored.

They reached the database because `_check_semantic_discrimination` read
`s.get('is_correct')`, where a missing key is falsy — "a distractor" — which is
what the mangled sentences happened to be, so the correct-count still came to 1.
The sibling check defaulted the other way (`s.get('is_correct', True)`).

**Fixed:**
- `services/exercise_generation/validators.py` — new `_check_is_correct_flags`
  requires an explicit boolean on every sentence in both types; both call sites
  now use `is True` / `is False` with no default. Key drift fails closed at
  generation time.
- `migrations/repair_semantic_discrimination_is_correct_keys.sql` — idempotent
  rename of the stray key preserving its boolean value, guarded to only touch
  sentences with exactly one stray boolean `is*` key. Applied live 2026-08-31.

- **T5.1 (S)** — Find the LLM-authored `hant` producer and stop it emitting
  keys. Preferred: generate one script and derive the other with the
  deterministic converter, so keys cannot drift by construction.
- **T5.2 (XS)** — Audit other content shapes for the same defect class
  (`options`, `parts`, `valid_pairs`) — the validator hardening covers
  `sentences` only.

---

## Recommended sequence

**Phase 1 — unblock practice.** The engine is at 3 attempts ever; this is the
only workstream with a user-visible zero.
T4.1 (supply gate) → T4.2 (evidence queue) → T4.6 (session floor) → T4.4/T4.5
(packs, cold start only). T4.1 alone makes the 387 covered senses reachable
without generating anything.

**Phase 2 — cheap quality wins.** All small, all independent:
T3.2 (tier-scaled novelty), T1.1 (stem rotation), T1.3 (verify tier mix),
T3d.1/T3d.2 (context-free caps).

**Phase 3 — throughput.** T2.1 (measure the `prefer_existing` hit rate) →
T2.2 / T2.3. Do not build before measuring.

**Phase 4 — coverage and breadth.** T3.1 (tier-fit judge), T3.3 (T3/T5
backfill), T3.4, then T4.3 (demand-driven generation).

### Hard dependencies
- **T3d.2 before T4.3.** Demand-driven generation without per-type caps
  reproduces the 做-style duplication across a far larger word set.
- **T4.1 before T4.2.** The evidence queue nominates ~43 senses today of which
  3 are servable; without the gate it recreates the current dead-end failure.
- **T5.1 before any bulk zh regeneration**, or key drift is re-minted at scale.

### Deliberately not doing
- Cutting judge calls for cost — 6% of spend, and no reject signal is
  gold-validated yet.
- Fanning every topic across all 6 tiers — see §3.
- Capping exercises per word at a flat 6–8 — see §3d; the cap belongs per
  *type*, not per word.

### Applied vs pending
| Change | State |
|---|---|
| `practice_session_service.py` gate → floor | applied, tests passing |
| `validators.py` explicit `is_correct` | applied, verified fails closed |
| `repair_semantic_discrimination_is_correct_keys.sql` | applied live 2026-08-31, verified |

---

## Execution log — 2026-09-01

Everything below was built and, where noted, applied live to
`kpfqrjtfxmujzolwsvdq`. Full suite: **2220 passing**, 1 pre-existing failure
(`test_prompt_split_l4_l8.py::test_unregistered_prompt_version_is_refused_not_guessed`,
reproduces unchanged at HEAD — unrelated to this work).

### Three more diagnoses changed once measured

| # | Plan said | Measured on execution | Consequence |
|---|---|---|---|
| T3.3 | T3/T5 need a topic backfill, possibly via cross-tier fan-out | **Topics at T3/T5 are not scarce** — 26 and 23, as many as any tier. Only *tests* are thin (2 and 1) | No fan-out needed at all. The risky half of the §3 design is now moot; T3.3 is a queue operation |
| T2.1 | Unknown `prefer_existing` hit rate gates T2.2/T2.3 | **52.6%** — of 23,368 enrichment decisions, 11,080 generated, 12,288 avoided (11,374 repeats + 914 imported) | Mid-band: both levers matter. T2.3 built; T2.2 stays open pending T2.4 |
| T4.1 | "T4.1 alone makes the 387 covered senses reachable" | It does not. The live ladder holds 24 rows of which **3** are servable, against a floor of 15 — a raw row count says "already full" forever | The floor had to change from counting rows to counting *servable* rows, or the gate would stop new dead words without ever unblocking the learner who already has 21 |

Also measured: 380 senses now clear the supply gate (183 zh / 189 en / 8 ja).
The plan's figure of 387 predates the context-free dedupe.

### Phase 1 — practice intake

- **T4.1** supply gate. `_senses_with_supply` admits a sense only with ≥3
  active exercises *in the target language*; fails closed. The language check
  is free and doubles as the scope guard for senses nominated from a
  cross-language wrong answer.
- **T4.1b** (not in the plan, required by the measurement above)
  `_eligible_ladder_count` now counts servable rows, and queues the unservable
  ones for generation — a subscribed learner being served nothing is the
  strongest demand-driven candidate there is.
- **T4.2** evidence queue off `user_vocabulary_knowledge` +
  `question_attempt_results` → `questions.sense_ids`. Requires
  `evidence_count >= 2` **or** `p_known <= 0.40`; a sense with no knowledge row
  qualifies on ≥2 distinct missed questions. Ranked wrongs → recency →
  frequency (Zipf desc).
- **T4.3** starved nominations are enqueued on the existing
  `generation_queue` with `reason='subscribe_topup'`, ≤5 per call.
- **T4.4** `pack_key_words` bridge created (empty — see Open below).
- **T4.5** a missing bridge now logs `CONTENT PIPELINE FAULT` at ERROR and is
  distinguished from an empty pack, instead of a bare `logger.warning`.
- **T4.6** session floor: a session under 20 items is topped up from the
  maintenance pool, de-duplicated by `exercise_id`, and reports
  `floor_backfilled`. Never invents material — a dry maintenance pool leaves
  the session honestly short.
- **T4.7** `user_word_ladder.created_at` added.

`migrations/task741_pack_key_words_bridge.sql` — **applied live**.

### Phase 2 — quality

- **T3.2** tier-scaled novelty: 0.82 at T1 → 0.90 at T6, env-overridable,
  falling back to the flat threshold for untiered candidates. The import path
  keeps the flat value on purpose (it has no tier).
- **T1.1** stem rotation for the three topic-independent question types
  (`main_idea`, `author_purpose`, `inference`) × en/zh/ja, 6–7 phrasings each,
  selected by hash of `topic_id:tier_id`. Kill switch
  `TEST_GEN_STEM_ROTATION=0`. **zh/ja phrasings want a native review pass** —
  they are ordinary test register, but unreviewed.
- **T1.2** recent-stem exclusion via `get_recent_question_stems`, and the
  chosen stem is never also listed as forbidden.
- **T1.3** `question_mix.py` compares realised against the tier table on every
  test. Distinguishes *short* (survival floor absorbed a loss — INFO) from
  *missing* and *unrequested* (WARNING).
- **T1.4** — decided, no change. The new tier table already gives
  `author_purpose` exactly 1 of 5 at T6; the legacy 2× was pre-table content.
  Its templating problem is addressed by T1.1 at the phrasing level rather
  than by cutting the type.
- **T3d.1/T3d.2** context class on `dim_exercise_types` + Python mirror; caps
  enforced in `exercise_caps.py` at both insert paths and by a partial unique
  index. The cap key is **(sense, type, context anchor)**, which preserves the
  one legitimate exception: a polyphonic word's `context_sentence` variants.
- **T3d.3** — verified, no change needed. `mcq()` in `exercise-renderers.js`
  already shuffles for every type that has a renderer.
- **T3d.4** 190 surplus rows deactivated (not deleted) and tagged
  `retired_by=task743_context_free_cap`. Every cap-1 type now at zero surplus.

`migrations/task743_dedupe_context_free_exercises.sql` then
`migrations/task743_context_free_exercise_caps.sql` — **both applied live, in
that order** (the index cannot build over duplicates).

### Phase 3 — throughput

- **T2.1** per-test and per-batch hit-rate reporting; `senses_created` /
  `senses_reused` now persist to `tests.vocab_sense_stats` so a batch is
  reconstructable after the fact.
- **T2.3** inline enrichment capped at 80 words, frequency-ranked. Chosen
  against the measured distribution — T1 (avg 19, max 43) and T2 (avg 32, max
  64) are untouched, T4's tail is trimmed, T6 (avg 177, max 382) is roughly
  halved. The plan's opening suggestion of 40 would have bitten T4's median.
  The tail keeps its `dim_vocabulary` row, so `backfill_senses.py` picks it up,
  and `scripts/relink_deferred_vocab.py` reattaches the senses afterwards.
- **T2.2 / T2.4 open.** T2.2 (batch N words per call) is worth re-measuring
  after T2.4 pre-seeding moves the hit rate.

### Phase 4 — coverage

- **T3.1** `TierFitJudge` — one call per (topic, tier), asked independently and
  ascending, fails open. Gates the Explorer before insert; new metric
  `topics_rejected_tier_fit`. The six-tier fan-out is deliberately not built,
  for the three reasons in §3 plus the T3.3 measurement, which removes the
  coverage argument for it.
- **T3.3 / T3.4** `scripts/backfill_topic_tiers.py` — `--report` (run, output
  above), `--stamp-tiers` (T3.4), `--queue-tiers 3,5` (T3.3). Enqueues only;
  generation is left as a printed command because it costs money and hours.

### Open — needs a decision or a run

1. **Seed `collocation_packs` and `pack_key_words`.** Both are empty. The
   bridge exists and the code path works, but Queue B has nothing to draw
   from. This is a curriculum authoring decision, not a code one.
2. ~~**Ten exercise types have no front-end renderer.**~~ **FIXED
   (2026-09-01).** `tone_id_word`, `hanzi_to_pinyin`, `pinyin_to_hanzi`,
   `kanji_to_reading`, `reading_to_kanji`, `classifier_match`,
   `counter_match`, `synonym_antonym_match`, `word_family` and
   `particle_selection` are now in `dispatch()` in `exercise-renderers.js`,
   served by six renderers (the four script↔sound types share one). All 209
   rows render as real items. Three things came out of it beyond the wiring:
   `mcq()` grew an optional `extra` argument (`labels` for `tone_id_word`,
   whose options are bare tone digits; `sublabels` for measure-word readings;
   `accepted` because `classifier_match`/`counter_match` are genuinely
   multi-answer and this path grades client-side); the 26 new strings landed
   in all four `static/i18n/*.json`; and the sound→script direction now blanks
   its context sentence, which would otherwise have printed the answer — see
   item 7.
3. **Native review of the zh/ja stem pools** (T1.1).
4. **Run the T3/T5 test backfill** — `--queue-tiers 3,5`, then the printed
   `run_test_generation_cli.py` commands.
5. **T2.2 / T2.4** — see Phase 3.
6. Pre-existing test failure in `test_prompt_split_l4_l8.py` (unrelated).
7. **Polyphone context sentences leak the answer in the sound→script
   direction.** `readings._mcq` attaches `context_sentence` +
   `context_target` for all four types whenever the lemma is polyphonic, but
   for `pinyin_to_hanzi` / `reading_to_kanji` the key *is* the written form,
   so the sentence prints it verbatim. 28 of the 64 sound→script rows carry
   one (26 zh, 2 ja); in all 28 `context_target` equals `correct_answer` and
   has a literal match in the sentence. The renderer now blanks the target
   (dropping the sentence when it has no literal match, e.g. an inflected JA
   form, and blanking the key separately in case the two fields ever
   diverge), so nothing ships broken — but the generator is still writing an
   item whose stored content contains its own answer. Fixing it there —
   blank at generation time, or omit the sentence for the reverse direction —
   would remove the need for the renderer to defend itself.
