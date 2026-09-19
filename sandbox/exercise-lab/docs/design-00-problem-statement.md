# Design 00 — Problem Statement

Evidence base: `sandbox/exercise-lab/docs/recon-generation.md`,
`recon-serving.md`, `recon-data-surface.md` (all dated 2026-09-17), plus direct
reads of the cited source files. Every number below is either a measured figure
(cited) or an explicit assumption with a named variable.

## 1. The gap, stated as arithmetic

**Current cost per sense** (ladder path A→B, `services/vocabulary_ladder/asset_pipeline.py`):
- ~5.5 min/sense wall clock, $0.024–$0.0336/sense, "well over a dozen" LLM
  calls — the higher cost figure and the call-count language come straight from
  the runner's own docstring (`scripts/run_generation_batch.py:390-401`); the
  lower one from a 7-sense sample explicitly flagged in-doc as too small
  (`wiki/tasklist/archive/exercise-generation-v2.tasks.md:790-812`).
- Call graph: 1× P1 core (+0-1 repair, +0-N sentence repair, +1 judge) → 2
  variants × (P2, P3, L4, L8, 3 typed types) = up to 10 concurrent calls per
  variant pair, all fanned through a 12-wide thread pool
  (`asset_pipeline.py:294-346`). This is the entire cost for **one sense's
  whole ladder**, not per exercise (recon-generation §2).

**Target**: ≤10 s / word (orchestrator's stated target, single-word latency).

**Required speedup**: 330 s → 10 s = **33×**. Arithmetic, not an estimate — no
amount of prompt tuning, batching within a single call, or caching closes 33×
on a serial call chain each leg of which is a ~1-5 s network round trip. G1's
whole premise (one call replaces ten-plus) is the only candidate architecture
in this document that can reach the target number; everything else either
reduces cost/backlog time (G2, G3) without touching single-word latency, or
reduces latency partially (G5). This is stated up front because §5 of
`design-01-generation.md` returns to it with real numbers per design.

**Cost** matters less than latency for this specific target (33× is a latency
statement) but is not free: at $0.03/sense × 56,022 senses (see below) the
LLM-everything path costs ~$1,680 to cover the full lexicon once, before any
regen. G1's 1-call design cuts LLM cost by roughly the same factor as call
count (~8-10×, not 33×, since P1-core is one of the ~10 calls today and stays
roughly the same shape) — cost and latency do not scale identically, and this
document treats them as two separate axes throughout.

## 2. The backlog, with two numbers that don't reconcile cleanly

Two live snapshots exist, eight days apart, and they measure different things:

| Snapshot | zh | en | ja | Total | What it measures |
|---|---|---|---|---|---|
| 2026-09-04 (skill sizing query) | 8,031 | 10,578 | 7,118 | **25,727** | Senses with **zero exercises** at all |
| 2026-09-08 (content inventory) | 23,870 senses / 30 word_assets-backed | 10,774 / 21 | 21,378 / 76 | **56,022 senses total, 127 word_assets-backed (0.23%)** | Total sense count vs. LLM-asset coverage |

These are not the same denominator — the first counts senses with no
`exercises` rows (deterministic types can still produce some without
`word_assets`); the second counts senses with no `word_assets` row (the LLM
seed) at all. Recon flagged this explicitly (`recon-generation.md` §5,
`recon-data-surface.md` §3) rather than reconciling by guesswork, and this
document keeps that flag: **the true "senses with zero exercises of any kind"
count is unmeasured** and should be the first metric any of these designs
computes before/after, named `M_zero_exercise_senses`.

What both snapshots agree on: at ~5.5 min/sense serial, clearing either
backlog number is a multi-week wall-clock problem (`run_generation_batch.py`
docstring: 9,075 senses ≈ 35 days serial / 9 days at `--workers 4`, same
$305). Coverage of the cheap, load-bearing prerequisites is uneven and
language-asymmetric — this matters directly for G2 (§3 of `design-01`):

| | zh | en | ja |
|---|---|---|---|
| Has pronunciation | 34% | 0% | 22% |
| Has Zipf (`frequency_rank`) | 94% | 92% | 92% |
| Has any `word_assets` | 30/23,870 | 21/10,774 | 76/21,378 |

en's 0% pronunciation coverage is not a rounding artifact — no ARPAbet/cmudict
integration exists anywhere in the repo (`recon-generation.md` §8,
**UNVERIFIED / not yet built**, consistent with project memory
`l1-phonetic-trie-architecture.md`: "en lowest priority"). Any design that
assumes pronunciation-derived exercises (tone/reading types, and by extension
the phonetic-trie L1 replacement) is available uniformly across languages is
wrong for en today; this is corrected explicitly in `design-01` §3 and
`design-03`.

## 3. Constraints, restated as design gates

### 3a. Determinism
Exactly three free-text surfaces exist app-wide (`recon-data-surface.md` §5-6):

| Surface | Grading | LLM at grade time |
|---|---|---|
| `cloze_typed` | exact match post-normalization, server-side | No |
| Dictation | Levenshtein-tolerant token match, server-side | No |
| Dual Translation (DT) | Tier0 exact-match-after-normalization short-circuit → Tier1 (accuracy+range) → Tier2 (understandability+fidelity+naturalness) | **Yes, conditionally** — only submissions Tier0 cannot resolve escalate |

Recommendation per surface (justified in `design-03`): **keep** `cloze_typed`
and dictation exactly as-is — both are already deterministic and well-scoped.
**Keep, do not extend, DT's LLM tiers** — Tier0 already absorbs every
exact-and-near-exact case for free; the LLM cost there is inherent to grading
open-ended translation quality, not a design defect to fix. One new
free-text type is designed (`design-03` §"New type") with a fully
non-LLM grading path — see that document for why a genuinely new production
exercise is worth adding rather than just leaning harder on `cloze_typed`.

### 3b. Pedagogy
The product goal is stated as proficient **use** in minimum time, not
recognition scores. This cuts against the determinism preference in one
specific, citable way: retrieval practice and transfer-appropriate processing
research (Roediger & Karpicke 2006; Morris, Bransford & Franks 1977) both
predict that recognition-only practice (MC) trains recognition and transfers
weakly to production, and that free generation — even effortful, error-prone
generation — produces stronger, more durable, more transferable learning than
equivalently-timed recognition drills ("desirable difficulty," Bjork 1994).
The ladder's own level taxonomy already encodes this tension: rings 1-2
(`form_recognition`, `meaning_recall`) are MC; ring 2-4 add `form_production`
(morphology_slot — still MC!) and only `jumbled_sentence` (L9) and
`cloze_typed` are genuinely productive today. **17 of the ladder's ~20 active
type codes are multiple-choice** (`config.py:343-369`,
`EXERCISE_TYPE_FAMILY`). Any design that adds volume by leaning further into
MC (G2's deterministic registry is 8/10 MC) increases throughput and lowers
cost while doing nothing for the stated pedagogical goal, and in the worst
case reinforces a recognition-only skill profile. This is flagged again,
concretely, in `design-01` §"Pedagogical assessment per design" and is the
core justification for `design-03`'s one new production type.

### 3c. Async / concurrency
Recon identified four concrete serialization points (`recon-generation.md`
§6):
1. **Global cost-ceiling**: `spend_since()` sums *all* `llm_calls.cost_usd`
   rows since a run's start timestamp — concurrent runs corrupt each other's
   ceiling (`run_generation_batch.py:398-401` docstring, explicit rationale).
2. **Sequential language iteration**: `main()` loops `for language_id in
   languages` and calls `run_language` synchronously even under
   `--all-languages` (`run_generation_batch.py:601-604`).
3. **OpenRouter rate limit**: unquoted anywhere in-repo (UNVERIFIED exact
   QPS/RPM) — the reason `--workers` stays low in practice, not a hard
   architectural constraint.
4. **`pg_try_advisory_lock_for_queue_drain`**: serializes the queue-drain
   coverage-gap step across processes (`services/vocabulary_ladder/queue_drain.py:315`)
   — this one is a correctness lock (no double-enqueue), not a throughput
   bottleneck, and should stay.

Each design in `design-01`/`design-02` states explicitly which of #1-#4 it
removes, works around, or leaves standing (most leave #4 standing on purpose).
Point #1 is the one every generation design here should fix regardless of
which candidate ships — it is a pure implementation defect (sum-since-a-
timestamp is not how a per-run budget should be tracked) with no design
tradeoff attached; recommend switching to a `run_id`-scoped filter
immediately, independent of G1-G5.

### 3d. Measurability
Every candidate design in `design-01`/`design-02` carries an explicit "kill
metric": the single number that, if it comes back below/above a stated bar,
means the design failed and should not ship past its trial cohort. Where no
such number could be defined from what's already instrumented, that is
stated as a gap (e.g. per-ladder-level cost/latency does not exist today —
only whole-sense aggregates, `recon-generation.md` §5 "Not found" — so any
design claiming a specific level is cheap is making an assumption, named
below).

## 4. Named assumptions used throughout this document set

| Variable | Meaning | Current status |
|---|---|---|
| `M_zero_exercise_senses` | Senses with literally zero exercise rows, any type | Unmeasured (see §2) |
| `p_classifier_match_coverage` | Fraction of zh concrete nouns with a curated `dim_classifier_noun_pairs` row | Unmeasured — curated JSON covers only 44 classifiers, not all nouns |
| `p_counter_match_coverage` | Same, ja counters | Unmeasured, same caveat, 44 files |
| `p_mined_sentence_coverage` | Fraction of senses for which `fetch_corpus_sentences` (`asset_pipeline.py:668-700`) returns ≥1 usable sentence with no LLM call | Unmeasured — depends on `tests.vocab_sense_ids` linkage, itself only 78-100% per language (`recon-serving.md` §6.4) |
| `r_openrouter_rate_limit` | Provider QPS/RPM ceiling | UNVERIFIED, not quoted in-repo |
| `t_embedding_fill_rate` | Per-language `dim_word_senses.embedding` fill % | UNVERIFIED, not re-queried this session |
| `n_learners` | Active learners with ≥1 test attempt | **1**, as of 2026-09-17 (`recon-serving.md` §6.10) — this bounds every serving-side conclusion in `design-02`, stated once here and referenced there |

## 5. Metrics and targets (the scorecard every design is measured against)

| Metric | Definition | Current | Target | Owning design(s) |
|---|---|---|---|---|
| Single-word latency | Wall clock from "start generating sense S" to "S has ≥1 servable exercise" | ~330 s | ≤10 s | G1 |
| Cost per sense | `llm_calls.cost_usd` summed per sense | $0.024–0.034 | Not separately targeted; falls out of G1's call-count reduction | G1, G3 |
| Backlog drain rate | senses/hour clearable given a fixed $ or worker budget | ~0.18/hr serial (5.5 min) | Not latency-bound; throughput-bound | G3, G2 |
| Zero-LLM coverage | % of senses with ≥1 exercise from `dim_word_senses`+`dim_vocabulary` alone | ~0% measured directly (proxy: 127/56,022 word_assets-backed) | Majority of Zipf-covered senses (92-94%) | G2 |
| MC-only rate | % of a learner's served exercises that are multiple-choice | Not instrumented | Track, do not silently let it rise | design-03, S5 |
| In-band serve rate (M1) | Selection quality metric, existing script | 0.786→0.952 (w0→sum arm, one learner) | N/A — already tracked | S1-S4 baseline |
| ELO reachable ability spread | `400·log10(1/s-1)` chance-floor gap | ±191 pts cap | N/A, structural — IRT (S2) targets this directly | S2 |

Every subsequent document restates the relevant rows of this table next to
each candidate design's own arithmetic, rather than repeating the derivation.
