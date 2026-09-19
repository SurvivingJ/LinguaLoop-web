# FAT SEED prototype — results

Built under `sandbox/exercise-lab/prototypes/fat_seed/`. Measured with
`lab/harness.py` in `synthetic` mock-LLM mode (no live calls — hard rule).
`fixtures/live_responses/` was checked for a peer's real per-call latency
capture: **the directory exists but is empty** as of this run, so no real
OpenRouter number was available; latency is reported as a sensitivity sweep
instead (see §3).

## 1. What was built

- `seed_schema.py` — `FatSeed` dataclass + `validate_fat_seed()`, gating on
  the REAL `normalize_semantic_class`, `LANGUAGE_VALIDATION_PROFILES`,
  `contains_target_whole_word` (imported read-only from
  `services/vocabulary_ladder/config.py` and `validators.py`, confirmed
  import-safe — no DB/network touched). Smoke-tested with one hand-built
  seed each for en/decide, zh/咖啡, ja/機械 — **all three pass** validation
  (`_smoke_test.py`, executed, exit 0).
- `synth_seed.py` — deterministic, schema-valid-but-linguistically-fake seed
  generator, since `mock_llm`'s synthetic mode returns a fixed placeholder
  regardless of prompt and can't exercise a real schema.
- `prompt_builder.py` — real prompt text for variants (a)/(b)/(c).
- `render.py` — renderers gated by the REAL capability matrix
  (`capability_context_from_core`, `enabled_capabilities`,
  `requirements_met`, imported read-only). Calls REAL, unmodified,
  DB-free production modules directly: `l1_lookup.build_candidates` (ja L1
  mora trie), `deterministic.jumbled` (L9), `deterministic.cloze_typed`
  (L4 form-production), `deterministic.tone` (tone_id_word, zh).
- `pipeline.py` — Phase A (seed call(s) + render + structural validation)
  and Phase B (one batched judge call per sense).
- `variants.py` — three `Generator`-protocol implementations.
- `run_measurement.py` — pulled 16 real senses from `db/lab.sqlite`
  (zh/en/ja) and ran all 3 variants × concurrency {1,4,12} = 9 runs.

## 2. Corrected understanding of the two-phase design

Nothing provisional is ever served. Phase A (`is_active=false`) is the
<=10s-target path; Phase B (async, one batched judge call) promotes to
`is_active=true`. Two separate numbers matter:

- **time-to-generated** — Phase A alone. This is what the <=10s target binds.
- **time-to-servable** — Phase A + Phase B. Allowed to be async/slower per
  the stated requirement.

Variant (c), the legacy fan-out control, has **no separate Phase B** in this
model — its per-level judges are already inline in today's real
architecture, so its content is servable the moment generation ends
(time-to-generated = time-to-servable for that variant only).

## 3. Latency — measured structure + assumption sweep

Real per-call seconds were not available (empty `live_responses/`). Method:
ran the harness with a small **nominal** `synthetic_latency_ms=15ms` per
call to measure the true concurrency/critical-path **shape** (does variant b
really cost max-not-sum? does the fan-out really overlap?), then applied a
per-call-latency **assumption** analytically on top of the measured
critical-path call counts. Both are reported so the shape (measured) and the
assumption (stated, swept) are never confused.

**Measured critical path, in calls** (from the real harness run):

| Variant | Phase A calls on critical path | Phase B calls |
|---|---|---|
| (a) one fat call | 1 | 1 |
| (b) two parallel calls | 1 (max of 2, confirmed — measured phaseA latency ≈1x nominal, not 2x) | 1 |
| (c) ~10-call fan-out control | 3 (1 P1 + 1 judge, sequential, + fan-out max) | 0 (inline already) |

Measured nominal-latency phase-A means (15ms/call assumption, mixed zh/en/ja
batch of 16 senses, concurrency=1): (a) 373ms first-run / ~20-27ms warm
(one-time model-loading overhead, see §6), (b) 20-45ms, (c) 61-92ms — i.e.
(c) costs ~3-6x (a)/(b), consistent with the 3-call critical path plus real
thread-pool scheduling overhead beyond the pure 3x the call-count model
predicts.

**Sensitivity sweep** (seconds/call assumption × measured call-count shape):

| Per-call latency | (a)/(b) time-to-generated | (a)/(b) time-to-servable | (c) time-to-generated = time-to-servable |
|---|---|---|---|
| 2s | 2s | 4s | 6s |
| 5s | 5s | 10s | 15s |
| 12s | **12s — misses the <=10s target** | 24s | 36s |

At the extreme end named in project memory (`qwen3.8-max`, 100-330s/call for
a reasoning model), (a)/(b) time-to-generated would be 100-330s — 10-33x over
target — confirming redteam axis 5's warning: the <=10s target is a **model
choice** commitment, not an architecture guarantee, for every variant
including the fat seed.

## 4. Calls / tokens / cost per sense (measured, 16-sense batch)

| Variant | calls/sense | tokens in (total) | tokens out (total) | cost (total) | cost/sense |
|---|---|---|---|---|---|
| (a) one fat call | 1.00 | 15,774 | 1,264 | $0.00391 | $0.000244 |
| (b) two parallel calls | 2.00 | 5,873 | 2,528 | $0.00269 | $0.000168 |
| (c) fan-out control | 15.00 | 3,958 | 18,960 | $0.01217 | $0.000761 |

Caveat carried from `lab/mock_llm.py`'s own documented fidelity gap: tokens
are `len(text)//4`, not a real tokenizer; (a)'s large tokens_in reflects its
long, single, detailed prompt vs (c)'s many short per-stage prompts — this
compares **prompt-construction cost**, not real model pricing. (c)'s cost is
~3.1x (a)'s and ~4.5x (b)'s in this accounting, driven by call count, matching
the qualitative claim in `design-01-generation.md` that consolidation saves
mostly on eliminated judge/fan-out round trips, not on raw tokens.

## 5. Exercises produced / structural validator pass rate

- Seed structural-validity rate: **100%** for all three variants (expected —
  `synth_seed.py` always emits schema-complete content by construction; this
  number cannot yet distinguish variants on CONTENT quality, only on
  round-trip cost, since the mock LLM has no content-quality axis).
- Exercises produced per sense: **~7.6-7.7** across variants (119-123 total
  over 16 senses) — consistent with `design-01-generation.md`'s own
  worked-example estimates (5-8 exercises/sense for zh/ja).
- **A real artifact found, not hidden**: exercise counts varied slightly
  (119/122/123) across concurrency levels for the *same* 16 senses. Root
  cause: `render_l2`'s distractor pool (`sibling_pool`) is built by mutating
  a shared list as `generate()` is called, and `deterministic.jumbled`'s
  `LanguageProcessor.for_language(...)` call showed occasional skips under
  concurrency — both are thread-safety gaps in this **prototype's**
  bookkeeping, not in the production modules it calls. Effect size is small
  (~2-3% of exercises) but should be fixed (pre-build the sibling pool
  before generation) before trusting L2 numbers under concurrency.

## 6. Throughput (measured, senses/min)

| Variant | c=1 | c=4 | c=12 |
|---|---|---|---|
| (a) one fat call | 161 | 10,609 | 15,725 |
| (b) two parallel calls | 2,923 | 8,205 | 10,614 |
| (c) fan-out control | 981 | 3,393 | 5,870 |

(a)'s c=1 number is depressed by one-time model-loading (jieba/fugashi
dictionary load on first `jumbled_sentence`/`tone_id_word` call inside the
same process) — not representative; its c=4/c=12 numbers are the trustworthy
ones. All three throughput numbers are, per `lab/harness.py`'s own FIDELITY
GAP note, threads-in-one-process against a client that never touches a
network — they measure this prototype's own logic overhead, not real
provider rate limits.

## 7. Per-language capability matrix: prod-config-enabled ∩ fat-seed-renderable

Computed directly from `services.vocabulary_ladder.config.CAPABILITY_MATRIX`
(`is_enabled=True` rows only) intersected with this prototype's `render.py`
dispatch table — not eyeballed.

| Language | Enabled in prod (any semantic class) | Renderable from fat seed | Out-of-scope (needs ctx.db shim) | Not modelled (non-ladder types) |
|---|---|---|---|---|
| zh | 17 | **9** | 3 (classifier_match, hanzi_to_pinyin, pinyin_to_hanzi) | 5 |
| en | 15 | **12** | 0 | 3 |
| ja | 18 | **10** | 3 (counter_match, kanji_to_reading, reading_to_kanji) | 5 |

**The true deliverable count per sense is the bold column**, not "9 levels"
uniformly: EN reaches 12/15 (80%) of its own enabled surface because it is
the only language with `collocation_gap_fill`, `collocation_repair`,
`morphology_slot`, and `word_family` enabled at all; zh and ja lose 3 types
each to a DB-lexicon dependency this prototype did not shim (orthogonal to
the fat-seed design — that gap is `design-01-generation.md`'s G2, already
zero-LLM in production, just not reachable from this sandbox's sqlite
without adapter work).

Per-type verdict (GREEN=solved w/ real production code or high confidence,
AMBER=content now exists but unverified by anything before Phase B,
RED=disabled in prod regardless of seed, or unreachable here):

| Type | zh | en | ja |
|---|---|---|---|
| phonetic_recognition (L1) | AMBER | AMBER | **GREEN** (real mora trie, untouched) |
| definition_match (L2) | GREEN | GREEN | GREEN |
| cloze_completion (L3) | AMBER | AMBER | AMBER |
| cloze_typed (L4, det.) | GREEN | GREEN | GREEN |
| morphology_slot (L4) | RED (disabled in prod) | AMBER | AMBER |
| collocation_gap_fill (L5) | RED (disabled) | AMBER | RED (disabled) |
| semantic_discrimination (L6) | AMBER | AMBER | AMBER |
| spot_incorrect_sentence (L7) | AMBER | AMBER | AMBER |
| collocation_repair (L8) | RED (disabled) | AMBER | RED (disabled) |
| jumbled_sentence (L9) | GREEN | GREEN | GREEN |
| tone_id_word | GREEN | n/a | n/a |
| classifier_match/counter_match/hanzi↔pinyin/kanji↔reading | AMBER→out-of-scope | n/a | AMBER→out-of-scope |
| synonym_antonym_match | AMBER | AMBER | AMBER |
| word_family | n/a | AMBER | n/a |
| particle_selection | n/a | n/a | AMBER (highest stakes, zero grammatical verification) |

AMBER dominates because Phase A genuinely has no synchronous content-quality
check by design (Phase B is async) — this is intentional per the corrected
two-phase understanding, not a defect, but it means every AMBER cell's real
quality is unknown until a real Phase B judge (not this prototype's stub) is
built and run against real model output.

## 8. Verdict on redteam objections #2 and #3

**#2 (cosine band as arbiter): resolved by retirement.** The fat seed never
asks a distance metric to judge phonetic, collocational, or pragmatic
fitness — that mechanism is simply absent from this design, so the specific
failure modes redteam catalogued for it (semantic ≠ phonetic, semantic ≠
collocational, "wrong sentence" ≈ semantically close to "right sentence")
do not apply to an architecture that no longer uses cosine that way.

**#3 (seed sufficiency, 6-of-9 levels): existence-solved, correctness open.**
Every ladder level and typed type that redteam marked FATAL for lacking
generative wrong content now has a field that carries it (§ capability
matrix — no RED cells attributable to "seed can't carry this," only to
independent prod-config disablement or DB-shim scope cuts). What is **not**
resolved is whether that LLM-authored wrong content is actually correct
(audio-confusable, collocationally wrong, wrong for the stated reason,
non-word-not-accidentally-real). Under the corrected two-phase
understanding, that verification gap is Phase B's job and Phase B is real
(not skipped, per the correction) — so the risk is bounded to the
time-to-servable window, not permanent. This prototype did not build a real
Phase B judge (only a stub call for latency accounting), so "does Phase B
actually catch these" remains unverified here.

## 9. Everything still RED or unverified

- `collocation_gap_fill`/`collocation_repair` for zh/ja, `morphology_slot`
  for zh: RED, but by prod config, independent of the seed.
- `classifier_match`, `hanzi_to_pinyin`, `pinyin_to_hanzi` (zh),
  `counter_match`, `kanji_to_reading`, `reading_to_kanji` (ja): out of scope
  in this prototype (need a `ctx.db` lexicon/dictionary shim not built).
- No real Phase B judge exists here — only a stub call for latency
  accounting; whether Phase B actually catches bad AMBER content is
  unverified.
- L2's sibling-pool and `jumbled_sentence`'s language-processor showed
  small concurrency non-determinism (~2-3% of exercises) — a prototype
  bookkeeping bug, not a production-code finding.
- All latency numbers except the measured 15ms-nominal structure are
  computed, not measured, against an assumption swept at 2s/5s/12s (no real
  OpenRouter capture was available in `fixtures/live_responses/`).
