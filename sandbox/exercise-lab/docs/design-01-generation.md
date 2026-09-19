# Design 01 — Generation

Evidence: `services/vocabulary_ladder/asset_pipeline.py`, `config.py`,
`l1_lookup.py`, `deterministic/*.py` (all read in full or in relevant part),
plus `recon-generation.md` and `recon-data-surface.md`. See `design-00` §1 for
the 33× latency arithmetic this whole document works against.

---

## G1 — Seed-and-render

### Architecture

Replace the ~10-call P1/P2/P3/L4/L8/typed fan-out with **one structured LLM
call per sense** that emits a compact seed, then render every ladder level and
every deterministic type from that seed plus existing data. No per-level LLM
call, no per-level judge call at generation time.

```
sense_id, lemma, language_id
       │
       ▼
[ONE call: vocab_seed_v2]
  → { definition_simple, definition_standard,
      pos, semantic_class,
      sentences: [3, tier-graded: T-lemma_tier-1, T-lemma_tier, T-lemma_tier+1],
      collocations: [2, {text, is_fixed}],
      morphology_note: {forms: [...], invariant: bool} }
       │
       ├─ structural validator (schema shape, field presence) — no LLM
       │
       ▼
[compute_active_levels / capability matrix — unchanged, config.py:571-604]
       │
       ├─► deterministic registry (unchanged, 10 types) — reads seed.definition,
       │   pronunciation (pypinyin/fugashi, unchanged), dictionaries
       │
       └─► render_all_9_levels(seed) — NEW pure-Python renderers, replacing
           P2/P3/L4/L8/typed LLM calls:
             L1 phonetic   — ja: unchanged trie lookup (l1_lookup.py); zh/en:
                             NEW deterministic path if a trie exists (see G1
                             risk below), else this level is SKIPPED, not
                             LLM-generated — G1 does not resurrect the old L1
                             LLM call, because doing so puts one of the ten
                             calls right back in the critical path.
             L2 definition — unchanged (already deterministic)
             L3 cloze      — blank the seed's own sentence at its target word
                             (identical mechanism to cloze_typed's blanking,
                             cloze_typed.py:57), distractors from
                             semantic_distractors() RPC (HNSW + frequency-tier
                             + cosine BAND, see below) instead of an LLM judge
             L4 morphology — options ARE the seed's morphology_note.forms;
                             no LLM needed if forms.length >= 2 (English/JA
                             inflecting words); SKIPPED otherwise (matches
                             existing morph_forms>=2 requirement,
                             config.py:481-483)
             L5 collocation gap  — seed's own collocations[], blanked; only
                             offered where a collocation exists (mirrors
                             existing EN-only enablement, config.py:495-496)
             L6 semantic discrimination — 3 wrong sentences = the OTHER
                             tier-graded sentences from OTHER senses at the
                             same semantic_class + tier, drawn by embedding
                             distance (nearest_senses() RPC) rather than
                             LLM-authored "wrong" sentences
             L7 spot incorrect  — take one of the seed's correct sentences,
                             substitute the target word with an L6-style
                             embedding-near-but-wrong sense (SAME mechanism,
                             different presentation) — no LLM authors the
                             "incorrect" version
             L8 collocation repair — same swap mechanism as L7, applied to
                             the collocation sentence
             L9 jumbled    — unchanged (already deterministic, jumbled.py)
             typed (syn/ant, word_family, particle) — syn/ant from embedding
                             nearest-neighbour + antonym flag from a curated
                             small antonym table (NEW, small, one-time
                             curation cost, not per-sense); word_family from
                             seed's morphology forms directly; particle
                             selection (JA) — SKIPPED under G1 v1 (flagged
                             below as the one type G1 cannot honestly cover
                             without more data — see Risks)
       │
       ▼
[embedding-band guard + structural validators — replace all per-level judges]
       │
       ▼
exercises rows (unchanged table/shape)
```

### Distractor generation without a judge: the cosine BAND

This is the mechanism the thesis leans on hardest and the one this document
scrutinizes hardest. `semantic_distractors()` and `nearest_senses()` are real,
live, deterministic RPCs (`migrations/calibration_semantic_distractors.sql`,
`migrations/dim_word_senses_embedding.sql`, confirmed in
`recon-data-surface.md` §1). The design:

```
band_low, band_high = tunable cosine thresholds (e.g. 0.35, 0.75 — NAMED
                        ASSUMPTIONS, unmeasured against real also-correct
                        cases; see Risks)
candidates = nearest_senses(anchor_sense, k=20, same_frequency_tier=True)
accepted   = [c for c in candidates if band_low <= cosine(anchor, c) <= band_high]
```

Rationale (matches the thesis): too close (cosine > band_high) risks the
distractor also being a defensible answer (near-synonym); too far (cosine <
band_low) is "trivially wrong," giving the learner no discriminative work.
This is a real, cheap substitute for the current LLM judge's *plausibility*
axis. It is **not** a substitute for two things the current judges also do
that are not distance-shaped:

1. **Register/formality fit** — `l1_distractor`'s remaining legitimate job
   per its own docstring is "synonymy and register fit, which nothing about a
   pronunciation lookup can check" (`l1_lookup.py:18-22`). Embedding cosine
   captures topical/semantic similarity, not formality register — a cosine
   band will let register mismatches through exactly as often as the raw
   embedding space conflates them, which is an empirical unknown, not zero.
2. **Grammatical/collocational well-formedness after substitution** — for L7
   (spot-incorrect) and L8 (collocation-repair), swapping in an embedding
   neighbour does not guarantee the resulting sentence is *fluent*, only that
   the swapped word is semantically distant. A cosine-band swap can produce a
   sentence that's wrong for the wrong reason (nonsensical) rather than wrong
   for the pedagogically intended reason (a plausible-but-incorrect word
   choice). The current `sentence_validity` judge exists specifically to
   catch this class of failure.

**Judges become, exactly as the thesis specifies:**
(a) structural validators (schema/shape, synchronous, free);
(b) embedding-band guards (synchronous, one HNSW query, ~cheap — see latency
below);
(c) an **offline async audit sweep** — batched, runs after the fact, flags
for human/LLM review, never blocks serving. This is the honest place to put
the register-fit and fluency-after-swap checks the band cannot do: they
become detection, not prevention. **This is a real quality regression
relative to today's fail-closed batch judging** (`judges/base.py`, recon
§7) — today a bad L7 item never reaches a learner; under G1 it reaches
learners until the async sweep catches it. This is stated as a tradeoff, not
hidden: G1 trades some ship-time content quality for a 33× latency win, and
the audit sweep is the mitigation, not a full substitute.

### Cost/latency arithmetic

- **Calls per sense**: 1 (seed) + 0-1 repair (structural failures only, no
  LLM judge repair loop) ≈ **1.0-1.1 calls**, vs. today's 8-14.
  Speedup on **call count**: ~9-13×.
- **Latency**: today's 5.5 min is dominated by sequential stages (P1 →
  validate → repair → tier-gate → judge → fan-out P2/P3/L4/L8/typed, each a
  network round trip, `asset_pipeline.py:131-346`). G1 collapses this to: 1
  seed call (assume ~3-8 s, matching the thesis's stated target range for a
  single structured completion at this size) + rendering (pure Python,
  <200ms) + 1 embedding-band guard query per exercise needing distractors (L3,
  L6, L7, L8, syn/ant — 5 of ~9-12 types; each an indexed HNSW query, expect
  low-tens-of-ms per query, well under 1s total for all 5 in sequence, sub-100ms
  if batched). **Total: ~3-9 s**, inside the ≤10s target.
  **Named assumption**: the 3-8s figure for the seed call itself is not
  independently measured in this repo — `recon-generation.md` §5 has no
  per-call latency breakdown, only whole-sense aggregates. Call this
  `t_seed_call_latency`; it must be measured on the actual chosen model before
  claiming the target is met, not assumed from the thesis's own framing.
- **Cost**: 1 call at seed-call size (larger completion than P1-core's, since
  it now carries what used to be spread across P1+P2+P3) vs. 8-14 smaller
  calls today. Net token count is not obviously lower — G1 consolidates work,
  it does not eliminate the underlying generation. Expect cost reduction from
  removing judge calls (a real elimination — no candidate content to judge
  post-hoc at generation time) but only modest reduction from consolidation
  itself. Rough estimate: **$0.010-0.018/sense** (down from $0.024-0.034),
  driven mostly by dropping the ~5 judge calls, not by the 1-call
  consolidation. **Named assumption**, not measured.

### Worked example — zh: 咖啡 (kāfēi, "coffee")

Concrete noun, zh, language_id=1.

1. Seed call returns: `definition_simple="喝的东西，早上喝的多"`,
   `definition_standard="一种用烘焙咖啡豆制成的饮品"`, `pos="名词"`,
   `semantic_class="concrete"`, 3 sentences at T2 (its own Zipf ≈4.9 → T2 per
   `LEMMA_ZIPF_TO_TIER`, `config.py:257-263`), 1 collocation `{"喝咖啡",
   is_fixed:true}` — **but** `config.py:495-496` disables L5/L8 for zh
   entirely (no zh collocation grounding source), so this collocation is
   stored but never rendered as L5/L8; it is dead weight in the seed for zh
   specifically (a design note, not a bug: keep the field for future zh
   collocation grounding, per the code comment at those lines).
2. `compute_active_levels('concrete', language_id=1)` → zh concrete skips
   L5/L8 (`COLLOCATION_LEVELS`), keeps `[1,2,3,4,6,7,9]`.
3. Render:
   - L1: no zh phonetic trie exists yet (`l1_lookup._TRIE_REGISTRY` has only
     `{3: ja}` — `l1_lookup.py:47-49`). **G1 cannot render L1 for zh without
     either (a) an LLM call [defeats the purpose] or (b) a zh phonetic trie
     [not built, per roadmap "zh next"].** Correct choice for G1 v1: skip L1
     for zh/en, ship the deterministic/embedding-derived levels only, and
     treat "build the zh initial-final-tone trie" as a **prerequisite**, not
     an optional nice-to-have — this is the single largest correction this
     document makes to the thesis's "ready to derive everything" framing.
   - L2: deterministic same-tier lookup, unchanged.
   - L3: blank one T2 sentence at 咖啡, distractors = `nearest_senses` at
     T2/concrete filtered to cosine∈[0.35,0.75] (e.g. 茶 "tea", 牛奶 "milk" if
     they land in-band; 石头 "rock" would be cosine-far and excluded, correct
     — matches the intended "not trivially wrong" behavior).
   - L4: zh concrete routes to `classifier_match`, not morphology_slot
     (`config.py:484` is `is_enabled=False` for zh morphology_slot) —
     deterministic, needs 咖啡's classifier pairing (一杯咖啡, "cup") from
     `dim_classifier_noun_pairs`. **If 咖啡 has no curated pairing** (the 44
     curated files are not guaranteed exhaustive — `p_classifier_match_coverage`
     is an unmeasured named variable, `design-00` §4), L4 is skipped with a
     `Skip` reason, same contract as today.
   - L6/L7: embedding-neighbour swap as described above.
   - L9: jumbled from the seed's own sentence, unchanged mechanism.
   - typed: `synonym_antonym_match` via embedding nearest-neighbour (咖啡 has
     few true synonyms/antonyms as a concrete noun — likely **skipped**,
     correctly, since forcing an antonym for "coffee" would be nonsense; this
     is the deterministic path correctly reproducing what a good LLM judge
     would also reject).
4. Total renderable levels for this word: **[2,3,4(maybe),6,7,9]** + possibly
   L1 once a zh trie exists — 5-6 exercises from 1 LLM call + embedding
   queries, in an estimated 4-7 s.

### Worked example — ja: 機械 (kikai, "machine")

Concrete/abstract-leaning noun, ja, language_id=3. Chosen because this exact
lemma is already the project's live L1-trie validation case (project memory:
"live-smoke-tested on 昔/機械").

1. Seed call returns definition, `semantic_class` (likely `concrete` or
   `action`-adjacent depending on sense — machine-as-object vs. mechanism),
   3 sentences, morphology_note largely empty (機械 does not inflect — it's a
   noun in an agglutinating language where the noun itself is invariant;
   conjugation attaches to a following する, not to 機械).
2. Active levels: ja concrete also skips L5/L8 (no ja collocation grounding
   source, `config.py:496`, `is_enabled=False`); JA morphology_slot
   (`config.py:482`) is enabled for `action`/`property` only, so a concrete
   noun skips L4's morphology row — but ja concrete DOES get `counter_match`
   (`config.py:486`) if 機械 has a curated counter pairing (台, the machine
   counter — plausible, machines are a canonical 台 example) and
   `particle_selection` is gated to `concrete/abstract/action`
   (`config.py:485`) so it stays in play for concrete nouns too, **but G1 v1
   explicitly does not cover particle_selection** (see Risks) — it renders
   as skipped under G1, a real coverage loss versus today's LLM-generated
   particle drills for this exact word.
3. Render:
   - L1: **this is the one language where G1's L1 story is actually solved
     already** — the ja mora trie is live (`l1_lookup.py`), and it is
     independent of the seed-vs-fan-out question: it was already replacing
     the LLM call before G1. G1 changes nothing about ja L1 and should say so
     explicitly rather than claiming credit for pre-existing work.
   - L2: deterministic, uses the seed's definition — unchanged.
   - L3/L6/L7: embedding-band swap as above, using ja embeddings (embedding
     table is language-neutral, `dim_word_senses.embedding`, per-language
     rows).
   - L9: jumbled via fugashi chunker (`jumbled.py`'s `LanguageProcessor`),
     unchanged.
   - `kanji_to_reading`/`reading_to_kanji`: deterministic, needs only
     pronunciation (fugashi-derived, already 22% covered for ja — a real gap
     independent of G1, see `design-00` §2) — 機械 has kanji so both types
     apply.
4. Total: **[1,2,3,6,7,9] + kanji_to_reading + reading_to_kanji +
   counter_match(maybe)** = 7-8 exercises from 1 seed call + the pre-existing
   trie lookup, in an estimated 3-6 s (ja skips the collocation dead-weight
   concern zh has, and its L1 is already free).

### Risks (beyond the judge-substitution gap above)

- **particle_selection (JA) has no deterministic or embedding-derived
  substitute proposed here.** Particle choice (は/が/を/に/で...) is a
  genuinely syntactic decision that neither a cosine band nor a dictionary
  lookup addresses — this needs either (a) a rule-based particle-selection
  engine keyed on the verb's case frame (a real, scoped, buildable
  sub-project, not proposed here in detail) or (b) staying on the LLM path
  for this one type only, as a targeted exception to G1. Recommend (b) for
  v1: particle_selection keeps its existing LLM call, everything else moves
  to G1. This preserves most of the 33× win while not silently degrading a
  ja-specific, pedagogically important type.
- **zh/en L1 requires the tries the roadmap already calls for.** G1 does not
  reduce the urgency of building the zh initial/final/tone trie — it
  *increases* it, since G1 has no other proposed mechanism for zh/en L1 at
  all (not even the LLM fallback, which would defeat G1's purpose). This
  should be sequenced as a prerequisite (see `design-04`).
- **Cosine-band thresholds are unmeasured.** `band_low`/`band_high` are
  named assumptions (§ above). Shipping G1 without first validating the band
  against the existing gold/eval fixtures the project already has
  (`tests/fixtures/dt_gold/` is DT-specific and not usable here, but
  `data/eval/*` judge-eval fixtures may be adaptable — **not verified this
  session whether they cover distractor plausibility for the ladder
  specifically**) risks shipping a distractor generator no better calibrated
  than a coin flip on the plausibility axis it's replacing.
- **Seed schema drift.** One larger structured call is more failure-prone
  per-field than several smaller, single-purpose calls (more JSON keys, more
  chances for one bad field to invalidate the whole seed). The existing
  P1-core validator (`VocabAssetValidator.validate_prompt1`) already handles
  a comparably-shaped payload, so this is a known, tractable risk, not a new
  category of one.

### Kill metric

`valid_seed_rate` (structural-validation pass rate on the first attempt, no
repair) must stay ≥ the current P1 pass rate (unmeasured exactly, but the
existing `_MIN_VALID_RATE = 0.90` batch-abort threshold at
`run_generation_batch.py:71` is the right existing bar to reuse). **Negative
result**: if `valid_seed_rate` sits materially below 0.90 once the repair
path is spent, the larger single call is producing worse structural
compliance than the smaller staged calls did, and G1 should not replace them
— it should instead inform a smaller, still-consolidated seed (e.g. drop
morphology_note into its own tiny follow-up call only for inflecting
languages) rather than one monolithic call.

---

## G2 — Zero-LLM cold start

### Architecture

For every sense that already has `dim_word_senses.pronunciation` +
`definition` + `dim_vocabulary.frequency_rank` (Zipf), run the existing
deterministic registry (`services/vocabulary_ladder/deterministic/*.py`,
10 registered builders, unchanged code) **without ever calling
`VocabAssetPipeline`**. This is not a new pipeline — `deterministic_rows()` /
`generate()` in `deterministic/__init__.py:196-253` already do not require a
`word_assets` row for 8 of the 10 registered types (see correction below).
G2 is a **scheduling and gating change**, not new generation code: run the
deterministic sweep first, over the whole backlog, before any LLM call is
scheduled for a sense.

### Correction to the thesis's coverage claim

The thesis states this "clears the 25,727-sense backlog immediately... every
sense... gets ≥5 exercises." Reading the actual capability-matrix rows
(`config.py:475-514`) against what each deterministic builder actually needs
(`deterministic/*.py`, read directly) shows this is **true for zh, weaker for
ja, false for en** as stated:

| Language | Zero-sentence deterministic types available | Needs a sentence (mined or LLM) |
|---|---|---|
| zh (concrete) | `definition_match`, `hanzi_to_pinyin`, `pinyin_to_hanzi`, `tone_id_word`, `classifier_match`* = **up to 5** | `cloze_typed`, `jumbled_sentence` |
| zh (non-concrete) | `definition_match`, `hanzi_to_pinyin`, `pinyin_to_hanzi`, `tone_id_word` = **4** | `cloze_typed`, `jumbled_sentence`, `synonym_antonym_match`† |
| ja (has kanji) | `definition_match`, `kanji_to_reading`, `reading_to_kanji`, `counter_match`* (concrete only) = **up to 4** | `cloze_typed`, `jumbled_sentence` |
| ja (kana-only lemma) | `definition_match` = **1** (`kanji_to_reading`/`reading_to_kanji` both explicitly skip lemmas with no kanji, `readings.py:82-86,121-123`) | everything else |
| en | `definition_match` = **1** (no phonetic trie built — `l1_lookup._TRIE_REGISTRY` has no en entry — so none of the script/sound types exist for en at all; they are zh/ja-only capability rows, `config.py:502-506`) | `cloze_typed`, `jumbled_sentence` |

\* gated on curated-dictionary coverage, `p_classifier_match_coverage` /
`p_counter_match_coverage` — unmeasured, `design-00` §4.
† `synonym_antonym_match` needs `sense_embedding` (already computed,
zero-LLM) but is not sentence-dependent — corrected placement: it belongs in
the zero-sentence column for **all three languages** wherever an embedding
exists, since the requirement is `sense_embedding`, not `p1_sentences`
(`config.py:507`). Restated: zh non-concrete zero-sentence set is actually 5
(`definition_match`, `hanzi_to_pinyin`, `pinyin_to_hanzi`, `tone_id_word`,
`synonym_antonym_match`), ja is 4-5 depending on kanji presence, and **en's
zero-sentence set is 2** (`definition_match`, `synonym_antonym_match`) — still
well short of "≥5" without either mined or LLM-generated sentences.

**Conclusion**: G2's "≥5 exercises at zero LLM cost" claim holds for zh
(mostly) and partially for ja, but not for en, which has the least deterministic
infrastructure of the three languages by a wide margin (no phonetic trie, no
measure-word system, no morphology-slot fallback for concrete words since EN's
morphology_slot requires `morph_forms>=2` which is itself LLM-sourced today).
This is a direct, evidence-based correction to the orchestrator's framing, not
a rejection of G2 — G2 is still the right "coverage play" for zh and a
partial one for ja, but for en it functions closer to "definition_match +
synonym/antonym for everyone, richer content only once a sentence exists,"
and should be scoped and reported that way rather than promised uniformly.

### Unlocking the sentence-dependent types without an LLM

`fetch_corpus_sentences` (`asset_pipeline.py:668-700`) already mines real
transcript sentences per sense via the `tests.vocab_sense_ids` GIN index —
**zero LLM cost**, already live, already tier-screened. G2's real lever is:
run this miner standalone (decoupled from the P1 pipeline it currently feeds)
and, wherever it returns ≥1 usable sentence, unlock `cloze_typed` and
`jumbled_sentence` too — at zero incremental LLM cost. This depends on
`p_mined_sentence_coverage` (named assumption, `design-00` §4), which is
gated by how many senses are actually linked into a test transcript at all
(`vocab_sense_ids` coverage is 78-100% of *tests*, not of *senses* — a sense
with no test linkage yields nothing from this miner). **This coverage number
should be measured before G2 is sized as a coverage play**, since it directly
determines how many senses reach the "5" figure vs. the "1-4" figure above.

### Cost/latency

- **Cost: $0** per sense (no LLM call at all).
- **Latency**: dictionary lookups + one Supabase read for
  pronunciation/definition/Zipf + (optionally) one `tests_containing_sense`
  RPC call for the sentence miner. Sub-second per sense; **throughput**-bound
  by DB round trips, not LLM latency — running this over the full backlog
  (56,022 senses, or the smaller 25,727 "zero exercise" count) is a batch job
  measured in hours of DB I/O, not weeks of LLM wall clock. This is the
  correct "coverage play" framing from the thesis: it does not touch
  single-word latency (G1's job) but it clears the *backlog* number in
  `design-00` §2 essentially for free.

### Pedagogical assessment

8 of 10 registered deterministic types are multiple-choice
(`EXERCISE_TYPE_FAMILY`, `config.py:343-369` cross-referenced against each
builder). Only `cloze_typed` (form_production) and `jumbled_sentence`
(form_production) are productive, and both require the sentence G2 cannot
guarantee. **A sense that clears G2's zero-sentence bar gets recognition-only
practice** — this is the sharpest instance of the determinism-vs-pedagogy
tension named in `design-00` §3b. G2 should be framed internally as "coverage
floor, not learning ceiling" — it guarantees *something* exists to serve
(better than nothing, and strictly better than the current ~0.2%
word_assets-backed coverage) but should not be reported as closing the
pedagogical gap the product goal cares about. `design-04`'s sequencing
puts G2 first specifically because "some MC coverage now" beats "no coverage
for weeks," while flagging that G1 (or later, the new production type in
`design-03`) must follow to actually move the needle on production skill.

### Kill metric

`deterministic_exercise_count_per_sense` measured post-rollout, bucketed by
language and by whether a mined sentence was available. **Negative result**:
if the median en sense still lands at 1-2 exercises (as predicted above) after
rollout, that confirms en needs either an ARPAbet trie or an EN-specific
deterministic type before G2 can be called a "coverage play" for that
language — it should not be reported as solving en's backlog.

---

## G3 — Batched envelope

### Architecture

Reuses the existing `services/batch_prompting.py` "item_N envelope" — N
senses' worth of P1-equivalent content requested in one call, keyed by
position rather than `vocab_id` (per project memory:
"batch-prompting-via-item-envelope" — only sense-gen is wired to it today,
confirmed by recon-generation §4). Applying it to G1's seed call: instead of
1 call/sense, 1 call/N senses.

### Explicit tradeoff (per the task brief's own framing)

This is a **backlog-drain complement, not a latency competitor to G1**:

- **Per-sense amortised cost/time** improves with N (fixed per-call overhead
  spread over more senses; larger completions are typically cheaper per-token
  than N separate completions due to shared system-prompt/schema overhead).
- **Single-word latency gets strictly worse**, not just "not better": a
  learner requesting one specific new word now waits for the *whole batch's*
  generation (or for a scheduler to prioritize a batch-of-1 for them, which
  defeats the point of batching). If N=10 and each item takes ~1.5× a solo
  call's tokens-worth of latency due to a larger completion, a batch of 10
  might take ~8-12× a single call's latency for the *whole batch* — meaning
  the *specific* word a learner is waiting on could see 8-12× today's
  already-slow latency in the worst case (last item in the batch, model
  streams items in order). **This is a real, sharp regression for the
  interactive path** and must never be the mechanism serving a live "generate
  this word now" request.
- **Correct placement**: G3 belongs exclusively in the offline backlog-drain
  batch runner (`scripts/run_generation_batch.py`'s successor, generating
  G1-shaped seeds instead of P1/P2/P3), never in any user-facing "generate on
  demand" path. G1 serves the interactive/cold-word case; G3 serves "drain
  the remaining 20,000+ non-zero-LLM-eligible senses over a weekend for
  cheaper than running them one at a time."

### Cost/latency arithmetic

- Per-sense cost: expect meaningful reduction (the existing per-call
  batch-prompting memory note doesn't give a measured $/item at scale, so this
  is a **named assumption**, `r_batch_amortization_factor`, to be measured
  against a real N-sweep before committing to a specific N).
  Concurrency point #1 in `design-00` §3c still applies here — the same
  global-cost-ceiling bug affects a batched runner exactly as it affects
  today's per-sense one; fixing it is a prerequisite for running G3 workers
  in parallel across languages.
- Backlog drain time: at seed-call-sized batches with the existing per-item
  envelope mechanism, expect a similar order-of-magnitude improvement to what
  the existing sense-gen batching already demonstrates (project memory: "N
  rows per call... partial-failure retry halves to 1"); no repo-measured
  figure exists for the ladder-seed case specifically — **named assumption**,
  do not present a specific number until measured.

### Kill metric

`per_sense_amortised_cost(N)` vs. `N=1` cost, sweeping N ∈ {2,5,10,20}, with
`per_batch_p95_latency(N)` reported alongside so the interactive-path
exclusion (above) is enforced by data, not just policy. **Negative result**:
if amortised cost does not drop meaningfully past N=5 (diminishing returns
from fixed schema/system-prompt overhead already being small relative to
per-item content), there is no reason to push N higher just because it is
possible — smaller batches keep partial-failure blast radius smaller too.

---

## G4 — Render-on-demand / parametric exercises

### Architecture

Store only the seed (from G1). Render exercise **instances** at serve time
from a seeded RNG, not at generation time into fixed `exercises` rows.

```
serve_time(sense_id, level, user_id, attempt_seed):
    seed = load_word_assets_seed(sense_id)      # cached, one DB read
    rng  = Random(f'{sense_id}:{level}:{user_id}:{attempt_seed}')
    distractors = nearest_senses(seed.embedding, k=8, rng_pick=rng)  # fresh
                                                                       # draw
    difficulty  = compute_from_features(seed, distractors, rng)      # S4
    return render(level, seed, distractors, difficulty)
```

### What this genuinely buys

- **Combinatorially large pool from one seed** — real and correctly claimed.
  A single seed with 3 sentences × k-sized distractor pools × shuffle space
  produces many distinguishable instances without additional generation.
- **Fresh distractor draws per attempt kill replay staleness** — real. Today,
  a rendered `exercises` row is fixed; a learner who retries sees the exact
  same four options and can pattern-match the correct index rather than the
  content. This is a genuine, currently-unaddressed defect this design
  fixes.
- **Per-instance difficulty computed, not seeded** — this is the mechanism
  that could plausibly attack the documented "48/60 ja tests share one ELO
  across all 8 types" defect (`recon-serving.md` §4, ADR-024 point 1) —
  **but only if applied to the comprehension-test difficulty seeding
  pipeline, not just to ladder exercise instances**. G4 as scoped here
  (ladder exercise rendering) and the ja-test-ELO defect (test-generation
  time difficulty seeding, `services/test_generation/orchestrator.py`) are
  **different subsystems**. G4's difficulty-computation idea is directly
  reusable for S4 (`design-02`), and this document flags that reuse rather
  than double-counting the same fix as solving two separate problems.

### Costs the thesis names, examined

- **Caching**: rendering at serve time means every exercise view is a
  render, not a read. At current traffic (`n_learners=1`, `design-00` §4)
  this is a non-issue; at scale it is a straightforward cache-the-seed,
  compute-the-instance problem — the seed (small, one row) caches trivially;
  the instance (small, deterministic given the RNG seed) can be recomputed
  cheaply enough that caching it may not even be worth the invalidation
  complexity. **Not a blocking cost**, contrary to how "caching" costs are
  sometimes framed as heavyweight — here it is genuinely light.
- **Reproducibility for grading disputes**: this is the sharper, real cost.
  If a learner disputes a wrong-answer verdict, the exact instance they saw
  must be reconstructable. The `Random(f'{sense_id}:{level}:{user_id}:
  {attempt_seed})` scheme is reproducible **only if `attempt_seed` is
  persisted with the attempt** (e.g. on `exercise_attempts`, which does not
  currently carry one — a real schema addition, small but non-optional). Miss
  this and G4 trades a real defect (staleness) for a real support problem
  (unreconstructable disputes) — this is not optional plumbing, it is the
  load-bearing part of the design.
- **Difficulty drift between instances**: if difficulty is computed
  per-instance (S4-style), two instances of "the same" exercise can carry
  different difficulty, which complicates any consumer that assumed
  `exercises.difficulty_static`/`irt_difficulty` was a fixed property of a
  row. IRT calibration (`services/irt/calibrator.py`) fits per-`exercise_id`
  from `user_exercise_history` — **if exercise identity becomes
  per-instance rather than per-row, the existing IRT calibrator's whole
  data model (accumulate attempts against a stable `exercise_id`, fit `a`/`b`
  from that history) breaks**, since instances rarely repeat for the same
  learner. This is a real, structural conflict between G4 and the existing
  IRT calibration pipeline that the thesis does not surface: **G4 and S2 (IRT
  calibration) are in tension**, not naturally complementary as separately
  presented. Resolution requires either (a) IRT-calibrating the *seed* (fit
  difficulty on the class of instances a seed produces, not on one row), or
  (b) accepting that G4 exercises are IRT-uncalibrated and always fall back
  to the `a=1.0, b=0.0` cold default (`practice-unified-score.tech.md`
  §"Cold-start handling") — permanently, not just at cold start. This
  tension is flagged as the single most important open design question
  between the generation and serving halves of this document set.

### Kill metric

`grading_dispute_reconstruction_rate` (can support reconstruct the exact
instance shown, given the stored attempt_seed) must be 100% — this is a
correctness bar, not a quality one; any failure here is a shipped bug, not a
negative experiment result. Separately, `irt_fit_quality` for seed-level vs.
instance-level calibration (whichever resolution is chosen above) should be
compared against the existing per-row calibration's `se_b` distribution
(`services/irt/calibrator.py`) before G4 ships broadly.

---

## G5 — Template library + prompt caching

### Architecture

Mine exercise templates per (POS × language) from existing `word_assets`
rows (only 127 exist live, per `design-00` §2 — a real, small seed corpus),
fill slots deterministically, and use aggressive prompt caching / a cheap
model for whatever residue needs generation.

### Assessment

This is correctly framed by the thesis as the conservative fallback, and the
evidence supports that framing rather than complicating it: with only 127
`word_assets` rows live across 56,022 senses, there is not yet a large enough
corpus to mine templates *from* with confidence that they generalize past the
POS classes already over-represented in that small sample (`recon-data-surface.md`
§3's coverage table shows the 127 rows are not evenly spread — zh 30, en 21,
ja 76, and nothing about their POS/semantic_class distribution was
independently checked this session — **named gap**, `p_template_seed_pos_diversity`,
unmeasured). Prompt caching is a legitimate, orthogonal cost lever
(cache the system prompt / schema instructions across calls regardless of
which other design ships) and should be applied to G1's seed call
independent of whether G5 itself is pursued — it is a free latency/cost win
with no design tradeoff, unlike the other four candidates.

### Kill metric

`template_fill_success_rate` — the fraction of a fresh POS/language cell's
senses a mined template can fill without falling back to a full generation
call. **Negative result**: below ~50% for any of the six core (POS ×
concrete/abstract/action/property/function) cells, the mined-template
approach isn't earning its complexity over just running G1 for that cell.

---

## Cross-design summary table

| | Calls/sense | Latency/sense | $/sense | Fixes single-word latency? | Fixes backlog? | MC-only risk |
|---|---|---|---|---|---|---|
| G1 | ~1 | ~3-9s (assumption) | ~$0.010-0.018 (assumption) | **Yes** | Only as fast as it's run | Medium (embeds fluency risk) |
| G2 | 0 | <1s | $0 | No (not its job) | **Yes, for zh; partial ja; weak en** | **High** (8/10 types MC) |
| G3 | ~1/N | worse per-word, better per-batch | lower amortised | **No — actively worse** | Yes, cheaper | Same as underlying call shape |
| G4 | 0 (reuses G1 seed) | render-time, near-0 | $0 marginal | N/A (serving-layer) | N/A | Depends on rendered types |
| G5 | fraction <1 | Varies | Lower via caching | Partial | Slow to bootstrap (127-row seed) | Depends on templates |

See `design-04-decision-matrix.md` for the scored comparison and recommended
sequencing (short version: G2 first for immediate zh/partial-ja coverage,
G1 second and is the only one that hits the latency target, G3 wraps G1's
seed-call for backlog drain once G1 is proven, G4 layered on top of G1 once
the IRT-tension question above is resolved, G5 deferred until the corpus is
large enough to mine from).
