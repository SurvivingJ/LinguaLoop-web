# Red Team: "One-Call Seed + Deterministic Render" Proposal

Adversarial review, 2026-09-17. Scope: kill-or-confirm the proposal to replace
the ~10-14-call P1/P2/P3/L4/L8/typed pipeline with one LLM seed call per sense
plus deterministic rendering, a cosine-band distractor check, and a
never-blocking async audit. All claims cite `file:line` from direct reads of
`services/vocabulary_ladder/*` and `services/exercise_generation/judges/*`,
not from the recon docs alone — recon claims are treated as unverified until
checked against code, per instructions, and two are overturned below.

---

## Verdicts by axis

| # | Axis | Verdict |
|---|---|---|
| 1 | Quality collapse (judges vs. structural+cosine) | **SERIOUS** (epistemically, not empirically — see below) |
| 2 | Cosine band as distractor gate | **FATAL** for 4 of 7 judge-guarded content types; **MANAGEABLE** for 1 |
| 3 | Seed sufficiency, level-by-level | **FATAL** for 7 of 9 ladder levels + 2 of 3 typed types |
| 4 | Coverage reality (zero-LLM backlog play) | **SERIOUS** — recon's premise is wrong; the reachable slice is smaller and requires new code |
| 5 | Latency math (≤10s/word) | **MANAGEABLE**, conditional on model choice — unverified, real risk |
| 6 | Async/concurrency traps | **NOT A PROBLEM** for the specific proposal; **existing** trap is orthogonal to it |
| 7 | Offline audit ("flag, never block") | **SERIOUS** — quantifiable BKT/ELO corruption, not just a UX nit |
| 8 | Hidden coupling to `word_assets` shape | **SERIOUS** — several call sites assume fields the seed doesn't produce |
| 9 | What the proposal gets right | Several genuinely correct diagnoses — listed below |
| 10 | Strongest alternative | "Consolidate, don't eliminate" — see below |

---

## Fatal / serious issues, in priority order

### 1. The seed's 3 sentences are undersized by ~3x against the system's own floor — this alone breaks 6 of 9 levels (FATAL, axis 3)

`services/vocabulary_ladder/config.py:202` sets
`P1_MIN_ACCEPTABLE_SENTENCES = 6` — the system's own documented floor for
"too few of P1's sentences are off-sense/off-register/not-whole-word to build
a reliable ladder from" — and that floor applies *after* judging/repair of a
starting pool of **10** sentences (`Config.VOCAB_SENTENCES_PER_WORD`,
referenced at `validators.py:92`). The proposal's seed has **3**.

Concretely, today's `DEFAULT_SENTENCE_ASSIGNMENTS` / `SENTENCE_ASSIGNMENTS_A`
/ `SENTENCE_ASSIGNMENTS_B` (`config.py:1057-1091`) assign a **distinct**
sentence index to L3, L4, L5, L6, L7 (needs 3 correct + 1 wrong), L8, L9 —
and variant B draws from *different* indices (6-9 + overflow) than variant A
(0-5) specifically so a learner who sees both variants doesn't answer the
second from memory of the first. That is 7 distinct sentence slots per
variant, 2 variants, drawn from a pool of 10, with headroom deliberately
built in for judge/tier-gate attrition. Three sentences cannot fill this
matrix once — there aren't enough distinct sentences to avoid content
collision across L3/L4/L5/L6/L7/L9, there is no A/B variant differentiation
left at all, and there is zero headroom for the tier gate
(`tier_gate.py`) or any judge to reject even one sentence before the ladder
loses a level outright.

This is not a tuning question ("ask for more sentences") — it is evidence
that whoever sized the proposal's seed at "3 tier-graded example sentences"
did not check it against the ladder's own sentence-assignment contract,
which is exactly the kind of ambiguity §3 of CLAUDE.md-equivalent specs
would flag as a defect.

### 2. Six of nine ladder levels need irreducibly *generative* wrong-content, not more corpus lookups (FATAL, axis 3 — full level-by-level)

Read against `exercise_renderer.py`, `validators.py`, `asset_pipeline.py`,
and the L4/L5/L6/L7/L8/typed judges:

| Level | What it actually needs beyond a definition+sentences | Verdict |
|---|---|---|
| **L1** phonetic_recognition | ZH/EN: LLM-invented **audio-confusable real words** + per-distractor explanations (`validators.py` L1 option gate; judged by `l1_distractor.py`). JA: already deterministic via the mora trie (`l1_lookup.py`) and untouched by any of this. | **BREAKS for ZH/EN**; JA already fine and doesn't need the seed's sentences/collocations at all. |
| **L2** definition_match | Only `definition` + a same-tier distractor pool from *other* senses (`deterministic/definition_match.py:32-66`, `lexicon.py`). | **Works** — already deterministic, seed is more than sufficient. |
| **L3** cloze_completion | One sentence (seed has it) **plus 3 authored, context-specific wrong-word distractors + explanations**, verified by `cloze.py`. | **BREAKS** — no distractor content in the seed. |
| **L4** morphology_slot | `correct_form` + `base_form` + `form_label` **plus 3 plausible-wrong inflected-form distractors + explanations** (`validators.py:238-247`), gated on `morph_forms>=2` — a real enumerated list, not prose (`config.py:481-483`, `capability_context_from_core`). | **BREAKS twice**: "1 morphology note" satisfies neither the capability *gate* (needs a countable list ≥2) nor the exercise *content* (needs invented wrong forms). |
| **L5** collocation_gap_fill (EN only; ZH/JA already disabled for lack of a grounding source, `config.py:487-493`) | One PMI-grounded collocate (grounding is already deterministic and can stay — good) **plus 3 genuine non-collocate distractors**, judged by `collocation.py`. "2 collocations" in the seed doesn't specify which is correct or supply any distractor pool. | **BREAKS** — grounding survives, distractor generation doesn't. |
| **L6** semantic_discrimination | 1 correct sentence + **3 sentences invented to be wrong for a specific labeled linguistic reason** (`judges/sentence_validity.py:5-30`). No deterministic asset — not CC-CEDICT, not embeddings, not Zipf — can invent "a sentence that misuses this word for reason X." | **BREAKS hard**, no substitute conceivable. |
| **L7** spot_incorrect_sentence | Mirror of L6: correct sentences + **one crafted wrong one with `error_description` and `corrected_sentence`** (`validators.py:267-284`). | **BREAKS hard**, same reason as L6. |
| **L8** collocation_repair (EN only) | A **planted wrong collocate** in an otherwise-correct sentence, verified non-collocate (`judges/collocation.py:121-163`) — strictly more generative than L5 (has to invent the error, not just pick a distractor). | **BREAKS**. |
| **L9** jumbled_sentence | Any one grammatical sentence with the target word; chunked deterministically (`deterministic/jumbled.py`). | **Works** — the level the seed serves best. |
| **synonym_antonym_match** | Candidate foils **anchored to this specific sense's definition**, because polysemy makes lemma-level foils wrong (`relation.py:8-16`, the documented "bank"/"shore" failure). Sourcing foils via `nearest_senses()`/embeddings is plausible; final adjudication that a candidate is genuinely NOT synonymous with *this sense* is what the judge currently does. | **PARTIAL** — foil *sourcing* could go embedding-driven; final adjudication is still a real risk without a judge. Seed doesn't attempt this at all. |
| **word_family** | **Invented non-words** ("decisionment") that aren't accidentally real. A dictionary can veto a real word; nothing can generate a *plausible fake* one deterministically. | **BREAKS hard.** |
| **particle_selection** (JA) | Grammar-specific judgment: does *exactly one* particle make this sentence natural? No particle-frequency structure analogous to the mora trie exists. | **BREAKS hard.** |

Net: **7 of 9 ladder levels, plus 2 of 3 typed types, need content the
proposed seed does not and structurally cannot contain.** Only L2, L9, the
already-deterministic ZH/JA reading/classifier/counter types, and (partially)
synonym_antonym_match survive contact with the seed. This is the single
biggest problem with the proposal as stated — "render all 9+ levels
deterministically from the seed" is not achievable; at most 2-3 levels are.

### 3. The cosine band is being asked to do a job the team already decided it can't do alone (FATAL for 4/7 content types, axis 2)

`services/vocabulary_ladder/sense_neighbours.py:1-23` is the *existing*
cosine-band implementation (`BAND_MIN=0.35`, `BAND_MAX=0.88`), and its own
docstring is explicit about scope: "Cosine similarity ... is used here as a
**sanity check rather than as the decision**. The relation judge still
rules; this only catches the two failures the judge is worst at." The team
that owns this exact mechanism already tried making it the arbiter and
pulled back to "signal, not verdict." The proposal asks to promote it back to
sole arbiter, universally, across content types the original band was never
designed for:

- **L1** needs *phonetic/audio* confusability. Cosine similarity of
  `"{lemma}: {definition}"` embeddings (the exact string embedded, per
  `sense_neighbours.py` and the migration it's built on) is a **semantic**
  signal — orthogonal to sound. A phonetically confusable word (the whole
  point of L1) can be semantically unrelated, and a semantically close word
  can sound nothing alike. The band is measuring the wrong axis entirely.
- **L5/L8** need *collocational* (syntagmatic) fit, not semantic similarity.
  "Spill" and "coffee" collocate but aren't semantically close; a
  semantically close word ("drink"/"coffee") may not be a genuine
  non-collocate. Cosine cannot distinguish a real collocation error from a
  real collocation.
- **L6/L7** need "wrong for a specific grammatical/pragmatic reason," not
  semantic distance from the target — a crafted-wrong sentence about the
  target word is, by construction, semantically *close* to a correct one.
- **synonym_antonym_match** is the *only* content type where cosine distance
  between two lemma-senses is actually the right measurement, and even
  there the existing code keeps a judge as the final word.

Antonyms compound this: classic embedding models place many antonym pairs
*closer* than true near-synonyms (they share almost all context except
polarity), so a band tuned to keep "adjacent, not equivalent" foils will
struggle to tell "confusably close synonym" from "textbook antonym" without
semantic content the vector doesn't carry — a familiar embedding failure
mode, and exactly the kind of thing `relation.py`'s judge exists to catch.

**Blast radius of a false also-correct**: an MC item with two right answers
doesn't just annoy a learner — see issue 4 below on BKT/ELO corruption.

### 4. The "judges catch almost nothing" argument imports numbers from the wrong pipeline and rests on a statistic the project's own memory says is unreliable (SERIOUS, axis 1)

The brief's "20-test run: 17 validator rejects vs 2 judge rejects" and "0.9%
production reject rate" both come from **comprehension-test generation**
(`test-gen-20-run-2026-08-21.md`, recon-generation.md §7) — a different
pipeline (entry point I) with different judges (`distractor_plausibility`,
`answer_entailment`) than the **ladder's** own judges under discussion here
(`l1_distractor`, `cloze`, `collocation`, `sentence_validity`, `relation`,
`particle`, `word_family`). Importing a low reject rate from one pipeline to
justify gutting judges in a structurally different one is an apples-to-oranges
argument.

The ladder's *own* number is worse for the proposal's case, not better: the
P1 sentence judge measured a **33% reject rate** on a 7-sense sample
(`exercise-generation-v2.tasks.md:797`, cited in recon-generation.md §7) —
correctly flagged in-doc as too small to trust, but it is the *relevant*
pipeline's data point, and it points at judges catching a lot, not nothing.

More fundamentally, the brief's own framing already contains the refutation:
project memory (`distractor-judge-v3-likert.md`) records that a judge's
reject rate swung **32% → 2%** purely from a **model swap**, with **zero
change to the actual content quality**, and that two judges scoring the same
content produce **disjoint reject sets** — meaning no reject signal in this
system has ever been gold-validated. That memory note exists precisely to
warn that low/changing reject rates are evidence of *judge miscalibration*,
not evidence that *the underlying content is clean*. Using "reject rate is
low, so removing the judge is nearly free" is applying the exact reasoning
that memory note was written to prevent. The honest position is: **we do not
know** what fraction of true defects any current judge catches, because no
gold set exists (memory: "a gold set now gates TASK-719/720"). Swapping an
unvalidated judge for an even-less-validated cosine band is not a validated
improvement — it's an untested bet stacked on an already-open question.

### 5. "Flag, but never block" already exists for one confidence band — the proposal's actual novelty is removing synchronous *reject*, and that has a concrete, non-cosmetic cost (SERIOUS, axis 7)

`judges/base.py:7-18` documents the existing verdict bands: confidence
`<0.6` → reject (sync block), `0.6-0.8` → flag (persist + review queue),
`≥0.8` → accept. So "ship it, review later" is **not new** for the
mid-confidence band — it's already how the system behaves today. What's
actually novel in the proposal is eliminating the **reject** path entirely
(no LLM judge left that can synchronously block), leaving only "flag,
review later" for everything a judge would have caught, including the worst
cases (an item with zero or two correct answers).

The harm is not just a bad learner experience once. Per project memory
(`calibration-e2e-writes-real-data.md`): "random clicking pools into the
account's ability" — user responses feed BKT (`user_vocabulary_knowledge`,
`user_word_ladder.family_confidence`) and ELO (`user_skill_ratings`,
`test_skill_ratings`) directly. An unanswerable L6/L7 item, or an L1/L5
item with two correct answers, doesn't just confuse one learner — it writes
a corrupted evidence point into that learner's ability model, potentially
blocking `gate_a`/`gate_b` progression (both require 2/3 or 6/8 correct on a
battery, `config.py:132-172`) on a defect that has nothing to do with the
learner's actual knowledge. That evidence point persists until someone
manually identifies and retires the exercise (the pattern already exists for
this — see `sense-blocklist-global-quarantine` in memory, which retires
exercises tied to a bad sense) — i.e., the fix mechanism already assumes bad
items get caught and quarantined *after* doing damage. An offline audit that
never blocks makes this the *only* mechanism, at a scale (10x the generation
throughput, since 8-10 calls become 1) that increases the number of first
exposures per unit time before any audit can run.

**A strictly better gate exists and costs little**: keep synchronous reject
for structural-defect classes only — "does the item have exactly one
correct answer" is a closed, checkable question (option counting is already
free, per `validators.py`'s own option-count checks) that doesn't need a
full semantic judge, and for the classes that genuinely need semantic
judgment to detect a defect (L6/L7's "wrong for the wrong reason," L1/L5/L8's
"distractor is actually correct") keep exactly one cheap Likert judge call
per sense, batched (see Alternative below), rather than zero.

### 6. Recon's coverage claim is wrong at the code level: today, *no* deterministic type — not even the fully-deterministic L2/L9/ZH-JA-reading types — can render without a `word_assets.prompt1_core` row already existing (SERIOUS, axis 4 — corrects recon)

`recon-data-surface.md` §4 asserts the deterministic registry types "read
only `dim_word_senses` + `dim_vocabulary` ... **no `word_assets` row
required**" and synthesizes that "a LLM-free generation pipeline could
plausibly skip `word_assets` entirely for any sense that already has
pronunciation + definition + frequency_rank" — implying the 94%/92%/92%
Zipf-covered backlog is already reachable at zero LLM cost with existing
code. This is **incorrect** on two counts, verified directly:

1. **The only call path that invokes any deterministic builder requires a
   valid `prompt1_core` word_assets row first.**
   `exercise_renderer.py:75-78`: `build_rows` returns `[]` immediately if
   `assets.get('prompt1_core')` is missing — logged as "cannot render." This
   check runs *before* `_render_deterministic` is ever reached, so
   `definition_match` (L2) — the type recon itself calls "already
   deterministic" — **cannot be produced today for a sense with only
   `dim_word_senses`/`dim_vocabulary` data and no word_assets row.** The
   claim "already runs off dim_word_senses/dim_vocabulary alone" describes
   the *builder* function in isolation, not the *reachable* code path.
2. **Two of the ten registered deterministic builders need P1's LLM-written
   sentences specifically**, not just any dictionary data:
   `jumbled.py:35-38` (`ctx.sentence_for_level(9, ...)` reads
   `core.sentences`, i.e. `word_assets.prompt1_core.sentences`, and skips
   with `'no P1 sentence available'` if absent) and `cloze_typed.py:116-130`
   (`_cloze_source` reads the same `core.sentences` via
   `ctx.sentence_for_level(4, ...)`). Both are unreachable for any sense
   whose only sentence source is `dim_word_senses.example_sentence` (a
   single field, not the P1 sentence-with-target-word-and-tier structure
   these builders expect).

Net effect: the "zero-LLM play" is real in *spirit* (the registry
architecture is sound and the recon is right that it's cheap to run) but the
specific claim that it already works today, on the existing backlog, with no
code changes, is false. Reaching it requires: (a) a new code path that
constructs a minimal `core`-shaped dict directly from
`dim_word_senses`/`dim_vocabulary` and bypasses `build_rows`'s
`prompt1_core`-existence gate, and (b) accepting that `jumbled_sentence` and
`cloze_typed` stay unreachable for the *pre-existing* backlog (no P1 sentence
ever ran) even after that fix — they only become reachable once *this
proposal's* new one-call seed exists and supplies `sentences[]`, which is a
fair point in the proposal's favor (see "gets right," below) but is a
different claim than "the current backlog is already servable this way."

This also means the coverage-reachable slice is smaller than the raw Zipf
numbers suggest: for **EN specifically** (0% pronunciation coverage,
recon-data-surface.md §3), *no* pronunciation-gated deterministic type
(hanzi_to_pinyin/pinyin_to_hanzi/tone_id_word are ZH-only;
kanji_to_reading/reading_to_kanji are JA-only) is available at all — the
only zero-LLM type EN could ever reach is `definition_match`, contingent on
fix (a) above and on the same-tier lexicon having ≥3 distractor definitions
already (itself contingent on *other* senses already having assets). EN's
10,578-sense backlog is disproportionately hard to clear for free relative to
ZH/JA.

### 7. Hidden coupling: the seed's shape doesn't match what downstream code reads off `word_assets.prompt1_core` (SERIOUS, axis 8)

Several call sites read specific fields off `core_asset` that the proposed
seed either omits or reshapes:

- `_update_vocabulary_metadata` (`asset_pipeline.py:1008-1057`) is the
  **only** writer today of `dim_vocabulary.semantic_class` /
  `part_of_speech` and of `dim_word_senses.ipa_pronunciation` /
  `morphological_forms` / `pronunciation` / `register` / `definition`
  (placeholder-replacement). It also runs `normalize_semantic_class()`
  before writing, because `dim_vocabulary.semantic_class` has a live CHECK
  constraint (`migrations/semantic_class_enum.sql`, referenced at
  `config.py:822-849`) — a raw or legacy label written without that
  normalization step **violates the constraint and fails the write**.
  Whatever writes the new seed into these columns has to reproduce this
  exact logic, or every sense silently keeps a NULL/stale semantic_class and
  falls back to the permissive "full ladder" default (`config.py:591-593`),
  quietly defeating the whole capability-matrix routing system (concrete
  nouns getting L5/L8, proper nouns staying subscribed, etc.).
- `capability_context_from_core()` (`config.py:694-711`) and
  `_collocation_is_fixed()` (`asset_pipeline.py:869-897`) both read a
  **singular** `primary_collocate` field and a `collocate_grounding` tag
  dict shape. The proposed seed's "2 collocations" doesn't specify which
  one is the graded `primary_collocate`, and there is no described
  replacement for the grounding tag's shape, which L5/L8's render code and
  the batch report both read directly (`exercise_renderer.py:231-232`).
- `morph_forms>=2` capability gating (`config.py:481-483`, `611-624`) reads
  `len(core_asset.get('morphological_forms'))` as a **countable list**. "1
  morphology note" is prose; it does not satisfy this gate mechanically
  without a parser being written to extract a form count from free text —
  an unstated, non-trivial piece of new code.
- The coverage-gap queue (`queue_drain.py`, referenced in project memory as
  re-enqueuing "every such sense for a full P1+P2+P3+judges regeneration,
  nightly, forever" when a family can't be satisfied) and
  `exercise_caps.py`'s per-(sense,type,anchor) dedup logic both assume the
  current asset_type taxonomy (`prompt1_core`, `prompt2_exercises_A/B`,
  `prompt3_transforms_A/B`, `llm_types_A/B`). None of these are addressed by
  the proposal; if the seed doesn't produce a `word_assets` row shaped like
  today's, these systems misfire silently (either re-enqueuing already-fine
  senses forever, or never flagging genuinely broken ones) until someone
  rewrites them too.

None of these are unfixable — they're scoped engineering tasks — but the
proposal as stated treats the seed as a drop-in replacement for
`prompt1_core`, and it is not one without touching at least 4 other call
sites that read fields it doesn't produce in the shape they expect.

---

## Latency and concurrency — no fatal issues found, but two real risks

**Latency (axis 5, MANAGEABLE/conditional):** No per-call latency isolated
for P1 alone exists in any doc (recon flags this as UNVERIFIED). The ≤10s
target is plausible *only* if the seed is served by a fast, non-reasoning
model. Project memory is explicit that `qwen3.8-max` — a reasoning model
used elsewhere in this codebase — needs ~16k max_tokens and takes
**100-330s per call**, and that model choice for ladder generation flows
through `prompt_templates` (DB-driven, no hardcoded slug per
recon-generation.md §4) — meaning nothing in the architecture *prevents* an
operator from routing the seed prompt to a reasoning model for quality
reasons, at which point ≤10s is not achievable by 1-2 orders of magnitude.
This is a real, foreseeable failure mode given the precedent, not a
hypothetical one, and the proposal doesn't name a model or acknowledge the
constraint.

**Concurrency (axis 6, NOT A PROBLEM for the specific change; existing trap
is orthogonal):** Collapsing the P2/P3/L4/L8/typed fan-out
(`BatchModeThreadPoolExecutor(max_workers=12)`, `asset_pipeline.py:311-346`,
up to 10 futures per sense) down to 1 call per sense is a **genuine
concurrency win** — it removes the "workers=N means up to Nx8-10 concurrent
provider calls" multiplier the current `run_generation_batch.py` docstring
explicitly warns about (recon-generation.md §6). However, the *reason*
languages are run sequentially today — `spend_since()` sums **all**
`llm_calls` rows since a start timestamp, so parallel runs corrupt each
other's cost-ceiling accounting (recon-generation.md §6, citing
`exercise-generation-v2.tasks.md:800-805`) — is a property of the batch
driver's accounting design, not of the per-sense fan-out width. Fixing the
fan-out does not fix the ceiling-accounting design; a future attempt to
parallelize across languages under the new architecture will hit the exact
same bug unless that's separately addressed. Also note: recon's phrasing
suggests a cross-run advisory lock protects the generation batch itself —
checked, and the only advisory lock found (`pg_try_advisory_lock_for_queue_drain`,
`queue_drain.py:315`) protects the *coverage-gap re-enqueue* step, not the
generation batch or its cost ceiling. Minor recon imprecision, not load-bearing.

---

## What the proposal gets right (axis 9)

1. **The diagnosis of where the money and time actually go is correct.**
   Judges are individually cheap, mostly fail-open, single-purpose calls;
   the 8-14 calls/sense figure is dominated by P1/P2/P3/L4/L8/typed
   *generation*, not judging. Attacking the generation fan-out is the
   correctly-targeted optimization even though the specific mechanism
   proposed (deterministic-from-a-thin-seed) doesn't work for most levels.
2. **The cosine band as a supplementary, non-authoritative sanity check is
   already validated production practice** (`sense_neighbours.py`) for
   exactly one relation (semantic adjacency between two sense embeddings).
   Extending that pattern — cheap pre-filter, judge still rules — to more
   places is sound; making it universal and sole-authority is not.
3. **Collapsing per-sense fan-out from up to 10 concurrent calls to 1 is a
   real concurrency and operational simplification**, independent of the
   quality debate — fewer partial-failure states, no variant A/B
   generation-side complexity, no split-level retry bookkeeping.
4. **The deterministic-registry architecture
   (`services/vocabulary_ladder/deterministic/`) is exactly the right shape**
   for the levels that can genuinely go LLM-free (L2, L9, ZH/JA
   reading/classifier/counter types), and is already built, tested, and in
   production for those types. A cheap one-call seed that supplies
   `sentences[]` would also make `jumbled_sentence` and `cloze_typed`
   reachable for senses that currently have no assets at all — a real,
   additive win the recon correctly identifies in spirit.
5. **TTS/audio and structural validation are correctly left alone** — they
   are already cheap, deterministic (given text), and run at render/admin
   time, not in the request path.

---

## The strongest alternative: consolidate, don't eliminate

1. **Keep one seed call, but size it against the ladder's own contract**:
   ≥6-8 tier-graded sentences (not 3, per issue 1), a real
   `morphological_forms` list (not a "note") when the language inflects, and
   a single `primary_collocate` (not an ambiguous "2 collocations") — all
   cheap additions in tokens, and each one is what an existing downstream
   consumer (`capability_context_from_core`, the L5 grounding gate, the
   sentence-assignment matrix) already requires by field name.
2. **Replace the 8-10 *small* P2/P3/L4/L8/typed calls with 1-2 *larger*
   batched calls**, not zero. The project already has a batching envelope
   built for exactly this (`services/batch_prompting.py`, "N rows per call,"
   per project memory) that today is wired only to sense-gen — extending it
   to ask for all of a sense's wrong-content (L1 distractors, L3/L5/L8
   foils, L6/L7 crafted-wrong sentences, L4 wrong forms, syn/ant foils,
   invented word-family non-words, JA particle foils) in one structured
   response cuts round trips from ~10 to ~2-3 without asking the model to do
   less *generative* work — round trips, not raw tokens, are the dominant
   latency cost per the test-gen eval's own finding that vocab enrichment is
   82% of wall clock but only 16% of spend (recon-generation.md §5).
3. **Keep exactly one judge call per sense, batched the same way**, covering
   the content classes that genuinely need semantic adjudication (L6/L7
   "wrong for the wrong reason," L1/L5/L8 "distractor is actually correct").
   Use the cosine band as a pre-filter ahead of it (fewer candidates reach
   the judge, cutting judge tokens) exactly as `sense_neighbours.py` already
   does — signal, not verdict.
4. **Make the reject path synchronous for structural defects specifically**
   (wrong correct-answer count, judge-flagged "no correct answer exists" or
   "two correct answers") since those are what corrupt BKT/ELO (issue 5);
   route subtler quality concerns (register, awkward phrasing) to the async
   audit, which is the right tool for *that* class of problem.
5. **Ship the zero-LLM backlog wins as an independent, immediate increment**,
   decoupled from the riskier seed/judge redesign: fix `build_rows`'s hard
   `prompt1_core`-existence gate so `definition_match` (and, for ZH/JA, the
   reading/classifier/counter types) can render directly off
   `dim_word_senses`/`dim_vocabulary` for the already-enriched slice of the
   backlog (roughly the pronunciation/Zipf-covered fractions in
   recon-data-surface.md §3, smaller than the raw Zipf numbers per issue 6
   above). This is low-risk, already-tested infrastructure, and doesn't
   require resolving any of the harder questions above before shipping.

This ordering — richer/correctly-sized seed, batched (not zero) generation
calls, one batched (not zero) judge call, synchronous block on structural
defects only, and an immediate independent backlog-clearing fix — keeps the
proposal's genuine wins (fewer round trips, cheaper judging, faster backlog
clearance) while dropping the parts that don't survive contact with the
code: a 3-sentence seed, a universal cosine-only distractor gate, and a
fully-never-blocking audit.
