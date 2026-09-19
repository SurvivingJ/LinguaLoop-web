# Design 04 — Decision Matrix

Scoring basis: `design-01-generation.md` (G1-G5), `design-02-serving.md`
(S1-S5), `design-03-exercise-taxonomy.md` (new type). Scores are 1 (worst) to
5 (best) on each axis, assigned from the arithmetic and evidence already
established in those documents — not re-derived here. Where a design's true
score depends on an unmeasured named variable (`design-00` §4), the score is
marked with that variable rather than presented as more certain than it is.

## Scoring axes, defined

- **Cost**: $/sense (generation) or added compute per selection call
  (serving). 5 = free or near-free; 1 = expensive/unbounded.
- **Single-word latency**: does it move the ≤10s target? 5 = hits it; 1 =
  actively worsens today's 330s.
- **Throughput** (backlog drain / selection call volume): 5 = clears the
  56,022-sense backlog or scales to many concurrent selection calls cheaply;
  1 = bottlenecked.
- **Quality risk**: 5 = low risk of shipping bad content/rankings; 1 = high
  risk (e.g. removes a fail-closed judge with no equivalent guard).
- **Pedagogical value**: 5 = directly serves "proficient use," per
  `design-00` §3b's recognition-vs-production framing; 1 = recognition-only,
  no production skill gained.
- **Implementation effort**: 5 = small, reuses existing code paths almost
  unchanged; 1 = large new subsystem.

## Generation candidates

| Design | Cost | Latency | Throughput | Quality risk | Pedagogical value | Effort | Total /30 |
|---|---|---|---|---|---|---|---|
| **G1** Seed-and-render | 4 | **5** | 3 | 3 (judge→band tradeoff, `design-01` §"G1") | 2 (mostly MC, unchanged answer formats) | 3 (new render logic, but reuses config/deterministic scaffolding) | **20** |
| **G2** Zero-LLM cold start | **5** | 1 (not its job) | **5** (zh; 3 ja; 2 en — `p_classifier_match_coverage`/`p_counter_match_coverage`/`p_mined_sentence_coverage` unmeasured) | 4 (reuses already-shipped, tested builders) | 1 (8/10 types MC, `design-01` §"G2" correction) | **5** (zero new generation code — scheduling change only) | **21*** (*language-weighted; en alone scores ~16) |
| **G3** Batched envelope | 4 | **1** (actively worse for the interactive path) | 4 (`r_batch_amortization_factor` unmeasured) | 3 | 2 (inherits whatever G1/G-base call shape produces) | 4 (reuses existing `batch_prompting.py`) | 18 |
| **G4** Render-on-demand | 5 (marginal cost ~0 once seed exists) | N/A (serving-layer, not generation-latency) | N/A | 2 (real, unresolved IRT-calibration tension, `design-01` §"G4" Costs) | 3 (kills replay staleness — real learning-hygiene win, format unchanged) | 2 (attempt_seed persistence + IRT-model resolution both required, not optional) | 12 (excluding N/A axes; do not compare directly to the others) |
| **G5** Template library | 3 (caching helps regardless) | 2 | 2 (127-row seed corpus, `p_template_seed_pos_diversity` unmeasured) | 3 | 2 (same MC-heavy profile as whatever it templates) | 3 | 15 |

\*G2's throughput/total score is genuinely different per language and should
not be reported as a single number in practice — the table's asterisk exists
specifically so this caveat survives into any summary that quotes the table.

## Serving candidates

| Design | Cost | Latency (per selection call) | Throughput | Quality risk | Pedagogical value | Effort | Total /30 |
|---|---|---|---|---|---|---|---|
| **S1** Per-sense focus-share term | 4 | 5 (one added CTE aggregate) | 5 | 4 (rollback via weight=0, established pattern) | 3 (better-targeted review, doesn't change format) | **5** (additive term to existing ranker) | **26** |
| **S2** 3PL IRT (fixed c=1/k) | 4 | 5 | 4 | 3 (identifiability risk if `c` is fit rather than fixed — mitigated by fixing it) | 3 (better difficulty targeting, no format change) | 3 (calibrator likelihood-function change + migration column) | 22 |
| **S3** Expected-gain knapsack | 4 | 5 | 4 | 3 (new value function, needs the n=1-limited validation in `design-02`) | **4** (directly optimizes learning gain, not just proximity) | 3 (new value function inside existing knapsack loop) | 23 |
| **S4** Computed per-type difficulty | 4 (one-time reseed job) | 5 (no runtime selection-formula change) | 4 | 3 (feature set may not capture the true difficulty driver, `design-02` §"S4" kill metric) | 3 (fixes a real mis-targeting defect, ADR-024) | 3 (reseed job + feature pipeline, reuses G1/pitch-accent infra) | 22 |
| **S5** Cross-surface gate audit | 5 (audit, not a runtime cost) | N/A | N/A | 4 (closes a real gap; explicitly does NOT touch Maintenance mode, avoiding the interleaving-literature mistake) | 4 (protects existing sequencing rather than degrading it) | 4 (mostly a measurement/audit task, per `design-02` §"S5" kill metric) | 21 (excluding N/A axes) |

## The one new exercise type

| | Cost | Latency | Throughput | Quality risk | Pedagogical value | Effort | Total /30 |
|---|---|---|---|---|---|---|---|
| `constrained_production` | 5 (zero LLM in sync path) | 5 | 5 | 3 (false-accept risk on the coherence floor, named kill metric) | **5** (the only new production-format type in the set) | 4 (reuses `cloze_typed` normalization + G1's embedding band) | **27** |

---

## Recommended sequencing

Ordering below is derived from: (1) which designs are **prerequisites** for
others (a hard dependency, not just a scoring preference), (2) the
`design-00` §1 latency-arithmetic fact that only G1 can hit the ≤10s target,
and (3) the `design-00` §3b pedagogy gate, which this document treats as a
release-blocking requirement for any generation work, not an optional
nice-to-have.

1. **G2, scoped honestly per-language** (zh full, ja partial, en minimal) —
   ships immediately, zero LLM cost, no dependency on anything else. Run in
   parallel with everything below. Fix the global cost-ceiling bug
   (`design-00` §3c point 1) before running any *other* generation design
   concurrently with G2's batch sweep, since G2 itself makes no LLM calls and
   is unaffected by that bug, but subsequent designs are.
2. **`constrained_production` (design-03) ships alongside G2, not after it.**
   This is the sequencing decision that most directly answers the
   orchestrator's pedagogy requirement: shipping G2's MC-heavy coverage
   *without* simultaneously shipping the one production-format type in this
   document set would mean weeks of pure recognition-practice volume before
   any production practice improves — exactly the risk `design-00` §3b and
   `design-03`'s closing table warn against. Cost/effort for this type are
   both favorable (score 27/30) and it has no dependency on G1, so there is
   no technical reason to delay it.
3. **Build the zh phonetic trie** (initial/final/tone) as an explicit,
   scheduled prerequisite — not a side effect of G1. `design-01`'s zh worked
   example shows G1 has *no* mechanism for zh L1 without it, and the
   project's own roadmap already calls this next (project memory:
   "l1-phonetic-trie-architecture," "zh next, en lowest priority"). Sequence
   this before G1 ships for zh specifically, in parallel with steps 1-2.
4. **G1**, once the trie lands and the cosine-band thresholds
   (`band_low`/`band_high`) have been validated against whatever plausibility
   eval fixtures exist or can be adapted (`design-01` §"G1" Risks). This is
   the only design that hits the ≤10s target and should be treated as the
   central deliverable, not run concurrently with G2/production-type work as
   an equal-priority alternative — it is gated on the trie and on band
   validation, both of which are small, boundable pieces of prep work, not
   open-ended research.
5. **S1 and S4 in serving**, in parallel with G1 (they touch the test
   selector, not the generation pipeline, so there's no ordering dependency
   between them and G1). S1 is the cheapest, lowest-risk serving change in
   the whole set (26/30, purely additive, established rollback pattern) and
   should ship first among the S-designs. S4 is next because it fixes a
   concretely diagnosed defect (ADR-024's pitch-accent compression) and
   consumes G1's embedding/phonetic infra once available — sequence it
   just after G1's cosine-band mechanism is validated in step 4, so it can
   reuse rather than duplicate that work.
6. **S3**, after S1 — it depends on the same IRT probability term S2 would
   also use, so decide S2 first (step 7) if both are in flight, or accept
   that S3 ships with the cold-start `a=1,b=0` default until S2 lands.
7. **S2 (3PL)** is scored well (22/30) but gated on a **simulation-study**
   validation, not live traffic (`design-02` §"S2" — the calibrator's own
   20-attempt floor cannot be reached at n=1). Do the simulation study as a
   standalone, low-cost research task before committing calibrator code
   changes — this can run at any point, independent of the other sequencing,
   since it needs no production data.
8. **G4** is held pending resolution of the IRT-calibration tension flagged
   in `design-01` §"G4" (per-instance vs. per-seed calibration identity).
   This is a real open design question, not a scoring deficiency — do not
   schedule G4 until that question has an answer, because building it either
   way without deciding first risks throwing away work when the IRT model
   choice (step 7) is settled.
9. **G3** (batched envelope) wraps G1's seed call once G1's shape is stable
   — building G3 against a seed schema that's still changing wastes the
   batching work. Treat as the mechanism for draining whatever backlog
   remains after G2's zero-LLM sweep (the sentence-dependent types G2
   couldn't unlock, plus any sense G2's dictionary-coverage gates missed).
10. **G5** deferred indefinitely pending a larger `word_assets`/seed corpus
    (127 rows today is too thin to mine templates from with confidence,
    `design-01` §"G5") — revisit once G1+G2+G3 have materially grown that
    corpus.
11. **S5's cross-surface gate audit** can run at any time as a pure
    measurement task (no runtime changes) — recommend running it early
    (parallel with step 1) since it may surface a real defect that changes
    how urgently the rest of this sequencing should proceed.

## Where this document disagrees with the orchestrator's thesis (consolidated)

Restated from the body documents for a single reference point:

1. **G2's "≥5 exercises for every sense" is not uniform across languages.**
   True for zh, weaker for ja (kanji-less lemmas get as few as 1),
   materially false for en (no phonetic trie, no measure-word system — en's
   zero-sentence deterministic set is 2 types, `definition_match` +
   `synonym_antonym_match`, not 5). (`design-01` §"G2")
2. **G1's judge replacement (cosine band) does not cover everything the
   current judges do.** Register/formality fit and post-swap grammatical
   fluency are not distance-shaped problems; the embedding band solves
   plausibility, not those two axes, which move to an offline audit sweep —
   a real quality tradeoff, not a free win. (`design-01` §"G1")
3. **G1 has no mechanism for zh/en L1 at all**, not even a degraded one — it
   depends on the not-yet-built zh trie as a hard prerequisite, which the
   thesis frames as already-available infrastructure it is not, for zh/en.
   (`design-01` §"G1" worked example + Risks)
4. **particle_selection (ja) has no proposed deterministic or embedding
   substitute** — recommend keeping it on the LLM path as a scoped exception
   to G1 rather than silently dropping ja-specific grammatical coverage.
   (`design-01` §"G1" Risks)
5. **G4 and S2 (IRT calibration) are in tension, not naturally
   complementary.** Per-instance rendering breaks the existing
   per-`exercise_id` calibration data model; this conflict is not surfaced
   in the original thesis framing and is treated here as an open design
   question requiring a decision before G4 ships. (`design-01` §"G4",
   `design-04` step 8)
6. **S1-S4 are framed as if `get_recommended_tests` is the only selector.**
   A second, live selector (`get_practice_session`, `migrations/
   phase12_get_practice_session.sql`) already implements IRT + BKT + FSRS in
   a unified score for ladder exercises. Most of S1's and much of S2's
   groundwork already exists — the real work is extending proven patterns to
   the comprehension-test selector, not building from scratch.
   (`design-02` §0)
7. **S5's "types are interchangeable" critique is already largely addressed**
   for Acquisition mode (ring/gate sequencing is live) and should
   **not** be extended to Maintenance mode — the interleaving-practice
   literature argues for mixing types during review, which is closer to
   Maintenance's current flat-weighted design than to a S5-style enforced
   sequence. (`design-02` §"S5")
8. **The 25,727 vs. 56,022 backlog numbers do not share a denominator** and
   should not be quoted interchangeably; the true "zero exercises of any
   kind" count is unmeasured (`M_zero_exercise_senses`, `design-00` §2/§4).
9. **Determinism and pedagogy pull in opposite directions across most of
   this thesis** — G1 and G2 both add volume almost entirely on the
   recognition/MC side. This document set treats the one new production
   type (`constrained_production`, `design-03`) as a required companion
   deliverable, not an optional extra, specifically to keep the generation
   work from moving the product away from its stated "proficient use" goal
   even as it succeeds on cost/latency.
