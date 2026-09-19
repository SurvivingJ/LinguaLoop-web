# Fat-Seed Live Latency Probe — Results (2026-09-18)

## Head-to-head: gemini-3.8-flash vs gemini-3.5-flash-lite, plus gemini-3.5-flash-lite:batch economics (2026-09-18)

**Spend this leg: $0.4450** (24 real `google/gemini-3.8-flash` fat-seed calls, same 12 senses/24-sense set,
n=8/language, plus one free 404 mechanics probe on `:batch`). Combined running total across the whole
live-probe effort: **$0.6315 of the $1.00 task cap** ($0.1865 prior + $0.4450 this leg). All 24 new raw
responses cached to `fixtures/live_responses/fat_gemini-3.8-flash_<lang>_<vocab_id>_<hash>.json`.

### Step 0 — slug resolution (free /v1/models catalog check)

Both slugs **resolve**. No substitution needed.

| Slug | Resolves | Prompt $/1M | Completion $/1M | Context |
|---|---|---|---|---|
| `google/gemini-3.8-flash` | yes | $0.75 | $3.75 | 1,048,576 |
| `google/gemini-3.5-flash-lite` (baseline) | yes | $0.30 | $2.50 | 1,048,576 |
| `google/gemini-3.5-flash-lite:batch` | yes | $0.15 | $1.25 | 1,048,576 |

Nearby google/gemini flash slugs for reference (not substituted, not measured): `gemini-3.7-flash`
($0.75/$3.75), `gemini-3.6-flash` ($0.75/$3.75), `gemini-2.5-flash-lite` ($0.10/$0.40, cheapest flash-lite
tier), `gemini-3.1-flash-lite` ($0.25/$1.50).

### MODEL 1 — gemini-3.8-flash: latency (n=8/language, real wall clock)

| Model | Lang | n | p50 | p95 | max | avg output tok | avg reasoning tok | avg cost/call |
|---|---|---|---|---|---|---|---|---|
| gemini-3.5-flash-lite (baseline) | zh | 8 | 6.58s | 7.23s | 7.35s | 1,410 | n/a (no thinking) | $0.00382 |
| gemini-3.5-flash-lite (baseline) | en | 8 | 6.54s | 6.85s | 6.86s | 1,544 | n/a | $0.00416 |
| gemini-3.5-flash-lite (baseline) | ja | 8 | 6.75s | 7.66s | 7.69s | 1,609 | n/a | $0.00431 |
| **gemini-3.8-flash** | zh | 8 | **32.60s** | **50.52s** | **52.43s** | 4,501 | 2,778 | $0.01762 |
| **gemini-3.8-flash** | en | 8 | **25.55s** | **120.78s** | **168.52s** | 5,492 | 3,743 | $0.02134 |
| **gemini-3.8-flash** | ja | 8 | **29.49s** | **38.70s** | **39.08s** | 4,255 | 2,342 | $0.01667 |

**Verdict on the ≤10s target: DESTROYED, not widened.** 24/24 gemini-3.8-flash calls (100%) exceeded
10s — every single call, in every language, missed the target. The baseline's ~2.3s of p95 slack is gone
entirely; p50 alone is already 4-5x over budget, and the worst single call (English) took **168.5s** — a
16.9x overshoot on a call that was supposed to complete in under 10.

**Root cause: gemini-3.8-flash is a reasoning/thinking model by default on this route**, unlike
flash-lite. `usage.completion_tokens_details.reasoning_tokens` ranged from 0 to **20,169** across the 24
calls (avg 2,955/call — 62% of total output tokens), and it is highly non-deterministic: the *same*
prompt shape produced anywhere from 0 reasoning tokens (13.6s call) to 20,169 reasoning tokens (a single
call that alone emitted 22,192 total output tokens and took 168.5s). This is the same "reasoning-model
tax" pattern already on record for `qwen3.8-max` in this project's memory — a flash-tier slug that
silently enables hidden thinking and blows past latency budgets unpredictably, not consistently.

### Output tokens / decode rate

- Overall avg completion tokens: **4,749** (vs baseline 1,568 — **3.0x more verbose**), min 1,848 / max 22,192.
- Linear fit `elapsed = a + b*completion_tokens` across all 24 calls: **b ≈ 0.00761 s/token → ~131 tok/s
  decode**, roughly **half** of flash-lite's ~277 tok/s.
- So the latency blowup is **both** causes at once, not one: gemini-3.8-flash decodes at ~47% of
  flash-lite's speed *and* emits ~3x the tokens per call (mostly hidden reasoning). A 3x-token,
  0.47x-speed model is ~6.4x slower end-to-end for the same nominal task — consistent with the observed
  p50 ratio (~29.9s vs ~6.6s baseline ≈ 4.5x, with the extra spread coming from reasoning-token variance
  the linear model doesn't capture).

### Structural quality (n=24, matched baseline methodology)

| Check | Baseline (flash-lite) | gemini-3.8-flash |
|---|---|---|
| Valid JSON | 23/24 (96%) | **24/24 (100%)** |
| Distractor equals answer (collocate/cloze) | 0/24 | 0/24 |
| Wrong inflection equals correct inflection | 0/24 | 0/24 (after correcting for schema-shape parsing, see note) |
| `l1_audio_confusables` missing | n/a per-lang breakdown given | 8/24 — **all 8 are ja**, correctly following the prompt's instruction to omit this field for Japanese; not a defect |
| `morphological_forms` empty/missing | 14/24 (58%) | 12/24 (50%), same "invariant word" caveat as baseline |

Note on the wrong-inflection check: an initial pass flagged 12/24 "collisions" between
`morphology_wrong_forms` and `morphological_forms`. On inspection this was a **measurement artefact**
in the check itself, not a model defect — gemini-3.8-flash's `morphology_wrong_forms` is schema-varied
(sometimes an object keyed by the correct form, sometimes a list of `{form: <correct form>, wrong_forms:
[...]}` wrappers), and the correct-form label used as an organizing key was mistaken for a genuine wrong
candidate. Once the actual nested wrong-form values are checked, the true collision count is 0/24 —
matching the baseline exactly. No structural quality regression found; content quality is at least as
good as the baseline (JSON validity improved), independent of the latency verdict.

### Cost per sense

- gemini-3.8-flash avg: **$0.0185/sense** (zh $0.0176, en $0.0213, ja $0.0167) — **~4.3-4.6x more
  expensive per sense** than flash-lite's ~$0.0040 avg, driven by both the higher per-token price and the
  3x token volume.
- 25,727-sense backlog: **~$477** (vs ~$103 baseline).
- zh full 121k-vocab backlog: **~$2,132-2,243** (vs ~$484 baseline).

### MODEL 2 — gemini-3.5-flash-lite:batch: mechanics and economics

**Mechanics (verified empirically):** `:batch` is **not** a normal synchronous chat-completions call at a
discounted price. A real request to `POST /api/v1/chat/completions` with `model:
"google/gemini-3.5-flash-lite:batch"` returns an immediate **404**: *"This model is only available
through the Batch API. Use the `/api/beta/batches` endpoint instead."* Per OpenRouter's own Batch API
docs, that endpoint is a genuine **submit-then-poll** shape: you POST an inline JSON array of requests
(not a separate uploaded JSONL file, unlike OpenAI's convention), the batch is queued and returns `202
Accepted` with `status: "validating"`, and it runs on a **24-hour completion window** — that is the
*only* supported window; results are retrieved asynchronously once the whole batch finishes, not per-item
as they complete. There is no synchronous fallback and no partial/streaming retrieval.

**Interactive path verdict: DISQUALIFIED, immediately, on mechanics alone.** A 24-hour turnaround is
categorically incompatible with the ≤10s time-to-generated requirement for one-word-on-demand generation
— this needs no further measurement and none was attempted (per instruction, no batch job was submitted
or waited on).

**Backlog-drain economics (the path where this matters):**

| | Standard `gemini-3.5-flash-lite` | `:batch` | Discount |
|---|---|---|---|
| Prompt $/1M tok | $0.30 | $0.15 | 50% |
| Completion $/1M tok | $2.50 | $1.25 | 50% |
| Avg cost/sense | ~$0.0040 | **~$0.0020** | 50% |
| 25,727-sense backlog | ~$103 | **~$51.50** | -$51.50 |
| zh full 121k-vocab backlog | ~$484 | **~$242** | -$242 |

The discount is a clean, exact 50% off both prompt and completion tokens — not a tiered or
volume-dependent rate as far as the public catalog shows.

**Output quality parity: not empirically verified in this session, by design.** Confirming
byte-for-byte/quality parity would require actually submitting a batch job and waiting up to 24h for
results, which the task explicitly ruled out ("do not burn your budget or an hour of wall clock waiting
on a batch job to return... a pending job is not a result"). OpenRouter lists `:batch` as the same
underlying model (`Google: Gemini 3.5 Flash Lite (batch)`, identical name/description/context length to
the standard slug) processed via Google's own batch inference pathway — this is the standard industry
semantics for model batch tiers (same weights, asynchronous scheduling, no quality degradation), but it
is an inference from OpenRouter's catalog metadata and documented conventions, not a verified
side-by-side output comparison. If exact parity needs to be proven before flipping the backlog-drain path
over, that requires a follow-up session willing to submit one batch of ~20-50 items and wait out (part
of) the 24h window.

**Integration work required to use `:batch` for backlog drain:** the existing sense/exercise generation
pipeline calls the synchronous `chat/completions` endpoint directly; using `:batch` would need (1) a
request-array builder that batches N pending senses into one submission, (2) a submit call to
`/api/beta/batches`, (3) a polling or scheduled-retrieval step (cron-friendly, since this project already
has cron/advisory-lock infrastructure for similar batch jobs per `wiki` history) to fetch results once
`status` moves to `completed`, and (4) routing results back through the existing real write path once
retrieved — a non-trivial but bounded integration, not a drop-in swap.

---

## Follow-up run (same day): token scaling, one-vs-two split, lemma-absence diagnosis

Total additional spend: **$0.0791** (48 gemini-3.5-flash-lite calls: 12 small-seed, 12
medium-seed, 12 correct-content, 12 wrong-content). Combined with the original run:
**$0.1865 of the $2.00 cap.** Deepseek skipped entirely per coordinator instruction
(already established to fail the latency target on token bloat, not reasoning-class
labelling — no further deepseek calls needed).

### Token-scaling curve (gemini-3.5-flash-lite, SAME 12 senses at all 3 sizes: 4/language x 3 langs)

| Seed size | avg output tokens | avg latency |
|---|---|---|
| small (def + 3 sentences) | 168 | 1.75s |
| medium (def+pos+6 sentences+collocates+syn/ant) | 589 | 3.10s |
| fat (full seed, reused from original run — not re-measured) | 1,568 | 6.81s |

**Shape verdict: LINEAR, not superlinear** — once a fixed per-call overhead is accounted
for. Fitting latency = a + b*tokens on the two endpoints gives a ≈ 1.14s fixed overhead
(network + time-to-first-token) and b ≈ 0.0036 s/token (≈ 277 tokens/sec decode rate);
that same model predicts the medium point at 3.27s against an actual 3.10s (within 6%) —
a good linear fit across all three sizes. The earlier cross-model read (deepseek's 3-6x
more tokens producing 6-12x more latency) was a model-identity effect, not evidence of
inherent superlinearity in the seed's own shape — isolated on one model, decode speed is
essentially constant per token.

**Headroom under the 10s target:** at ~277 tokens/sec and ~1.14s overhead, the 10s budget
is exhausted at roughly **2,450 output tokens**. The current fat seed uses ~1,568 tokens —
about **56% of the budget**, leaving **~880 tokens (~46%) of headroom** before the fat
seed would need to add its own overhead-mitigation (e.g. the two-call split below) to stay
under 10s. This is comfortable, not a cliff — new fields can likely be added to the seed
without breaking the target, but should be re-measured once added since 46% headroom is
not unlimited.

### One-call vs two-parallel (same 12 senses, gemini-3.5-flash-lite)

| | avg latency |
|---|---|
| one fat call | 6.81s |
| two parallel calls (correct + wrong, timed as max) | 4.95s |

**~27% latency reduction** (6.81s -> 4.95s avg; per-sense range 14%-37% faster), confirming
true max-not-sum behavior. Since one call already meets the 10s target with room, this is
headroom insurance rather than a requirement today — but it is a real, non-trivial buffer
(about 1.9s average) that would matter if more fields are added later and eat into the
46% token headroom above.

### Lemma-absence diagnosis: MEASUREMENT ARTEFACT, not a prompt bug (0 genuine defects found)

All 3 of the 24 original fat-seed docs with a substring-match "failure" were re-examined
with real tokenizers (`fugashi` for Japanese; direct inspection for English). Result in
every case: the model used the target word correctly, in a natural inflected/conjugated
surface form that a bare substring check cannot see.

- **English, lemma "upheld"** (5/10 sentences flagged): the model correctly varied tense/
  voice — "uphold the law", "uphold verdicts", "uphold standards" — all genuine uses of the
  same lexeme, just not in the exact past-tense surface form pulled from `dim_vocabulary`
  as the "lemma". Root cause: the vocabulary table itself stores an inflected form as the
  lemma for this entry, not a measurement bug in the substring check per se, but the
  check's assumption that "lemma" == "surface form used" is wrong for such entries.
- **Japanese, lemma "盛り上がる"** (10/10 sentences flagged): every single sentence used a
  real conjugated form (盛り上がった, 盛り上がってきた, 盛り上がっている, 盛り上がりを見せている). Running
  `fugashi` (MeCab) morphological analysis on these sentences resolves the dictionary
  lemma back to 盛り上がる correctly for the standard verb conjugations (spot-checked 2/2
  finite-verb cases matched exactly); one case used the -masu stem as a bare noun
  (盛り上がりを見せる, "to show excitement/momentum") which MeCab lemmatizes as the noun
  盛り上がり rather than the verb — a legitimate, minor derivational form, not an error.
- **Japanese, lemma "犯す"** (8/10 sentences flagged): conjugated forms 犯した/犯して/犯さない/犯せば
  all resolve to dictionary lemma 犯す under `fugashi` (spot-checked 2/2 exact matches).
- **zh: 0/8 substring failures** — consistent with Chinese being isolating/non-inflecting,
  substring matching works natively for zh and needs no tokenizer fix.

**Conclusion: 0 of the 3 flagged docs contain a genuine content defect.** All are false
positives from naive substring matching against inflected languages, confirming the
coordinator's suspicion exactly. The fix is in the *measurement* harness, not the prompt:
Japanese needs `fugashi`/MeCab lemma resolution (not substring match) and English needs the
vocabulary table's lemma to be checked against its own base/irregular form, not assumed to
equal the surface string a model will use.

---

**Status of original run below: PARTIAL.** This run was cut short by a hard handback deadline mid-execution.
Priority-1 measurement (latency table) is essentially complete for `gemini-3.5-flash-lite`
(full 8/language) and mostly complete for `deepseek-v4-flash` (zh full 8/8, en/ja partial,
~15/24 total captured before cutoff). Steps 2 (one-vs-two-call split), 3 (output-token
scaling), and the full structural-quality pass were NOT run — only a structural check on
the 24 cached gemini fat-seed responses was completed. See "What's missing" below.

## Spend

Actual OpenRouter-reported spend at cutoff: **$0.1074** of the $2.00 cap (39 successful
calls: 24 `gemini-3.5-flash-lite` + 15 `deepseek-v4-flash`, all fat-seed prompts).
No calls errored; no budget-cap trip.

## 1. Latency — ONE fat call, per model/language (real wall-clock, n=8 unless noted)

| Model | Lang | n | p50 | p95 | max | avg output tokens | avg cost/call |
|---|---|---|---|---|---|---|---|
| gemini-3.5-flash-lite | zh | 8 | 6.58s | 7.23s | 7.35s | 1,410 | $0.00382 |
| gemini-3.5-flash-lite | en | 8 | 6.54s | 6.85s | 6.86s | 1,544 | $0.00416 |
| gemini-3.5-flash-lite | ja | 8 | 6.75s | 7.66s | 7.69s | 1,609 | $0.00431 |
| deepseek-v4-flash | zh | 8 | 57.72s | 75.21s | 79.94s | 5,768 | $0.00063 |
| deepseek-v4-flash | en | partial (n≈4 at cutoff) | ~45s | — | 82.90s | ~5,600 | ~$0.00060 |
| deepseek-v4-flash | ja | partial (n≈3 at cutoff) | ~36s | — | — | ~4,300 | ~$0.00047 |

**Verdict on the ≤10s target:** `gemini-3.5-flash-lite` clears it comfortably in every
language (p95 ≤ 7.7s — squarely in the "@5s generated=5s (met)" regime). `deepseek-v4-flash`
misses it badly — p50 alone is 5-8x over budget, max hit 83s — even though it was not a
flagged reasoning model and is far cheaper per token. The cause is output-token bloat:
deepseek produced 4,300-9,055 tokens per call vs gemini's 1,350-1,780 for the *identical*
prompt — roughly 3-6x more verbose, which is what actually drives latency, not the model
label. **Recommendation: gemini-3.5-flash-lite is the only one of the two models tested
that hits the target; deepseek-v4-flash should be treated like a reasoning-class model for
latency purposes despite its listing.**

qwen3.7-flash was dropped from the matrix (per the task's own "drop to 2 models if needed"
allowance) to keep the run inside the time budget — not tested.

## 2. One call vs two parallel (correct/wrong split)

**Not run** — cut off before step 2 started. No data.

## 3. Output-token scaling (small vs fat seed)

**Not run directly**, but the completed data indirectly answers the underlying question:
holding the prompt (and thus target output shape) fixed, latency tracked output-token count
closely — gemini's ~1,400-1,600 tokens landed at ~6.5-7.7s, deepseek's ~4,300-9,000 tokens
(same prompt, same requested fields) landed at ~36-83s. That's roughly a 3-6x token increase
producing a ~6-12x latency increase — worse than linear, consistent with the architecture
model's warning that a big generation can miss the target once output size grows, and
consistent with per-provider decode-speed differences being at least as important as raw
token count. A dedicated small-vs-fat same-model run is still needed to isolate the pure
token-scaling curve from cross-model differences.

## 4. Structural quality (gemini-3.5-flash-lite fat-seed responses, n=24, all 3 languages)

- Valid JSON: 23/24 (96%). One response had malformed trailing JSON (likely truncation/
  formatting slip, not a schema violation).
- `morphological_forms` / `morphology_wrong_forms` absent in 14/24 (58%) — likely mostly
  legitimate (prompt explicitly allows an empty list for invariant words), not verified
  per-item whether truly invariant.
- `word_family_forms` absent in 8/24 (33%) — same caveat.
- `primary_collocate` / `collocation_wrong_collocate` both absent together in 1/24 (4%).
- Sentences failing to contain the target lemma as a substring: 3/24 documents (12.5%) had
  at least one offending sentence — a real, non-trivial defect rate worth a follow-up judge
  or programmatic filter.
- Wrong inflection identical to a correct inflection: 0/24.
- Any distractor identical to the answer (collocate or cloze): 0/24.

No cross-language quality comparison is claimed (per project memory: a single-model
language gap is not trustworthy — this run only has 24 gemini + 15 deepseek fat calls, not
a matched two-model comparison per language yet).

## 5. Cost per sense and backlog extrapolation

Using the real measured fat-seed cost per call:
- gemini-3.5-flash-lite: ~$0.0038-0.0043/sense depending on language (avg ~$0.0040).
  - 25,727-sense backlog: **~$103**.
  - zh full 121k-vocab backlog (if run entirely on gemini): **~$484**.
- deepseek-v4-flash: ~$0.0005-0.0007/sense (7-8x cheaper per call) but at 50-80s/call this
  is a wall-clock, not spend, blocker for any batch at this scale (consistent with the
  project's prior finding that batch runs are clock-bound, not cost-bound) — not
  recommended given the latency numbers above regardless of its lower price.
  - 25,727-sense backlog at deepseek pricing: ~$15-18, but ~1,430-2,000 GPU-minutes of
    wall clock at zero parallelism, or proportionally less with concurrency — moot given
    it misses the latency target outright.

## What's missing (cut off by forced early handback)

- Step 2 (one-call vs two-parallel-calls latency comparison) — 0 calls made.
- Step 3 as a dedicated small-vs-fat same-model-same-sense scaling run — 0 calls made
  (only inferred indirectly from step 1's cross-model token/latency spread, see above).
- deepseek-v4-flash en/ja cells incomplete (~15/24 total deepseek calls captured, zh is
  the only fully-sampled deepseek/language cell, n=8).
- Structural quality pass only covers gemini; deepseek responses were cached but not
  parsed for field completeness given the time cutoff.
- Raw responses ARE cached for everything that completed:
  `sandbox/exercise-lab/fixtures/live_responses/fat_<model>_<lang>_<vocab_id>_<hash>.json`
  (39 files) — reusable for the missing analysis without re-spending.

## Reproduction

- `sandbox/exercise-lab/live_probe/senses.json` — the 24 mid-frequency senses drawn from
  `lab.sqlite` (8 per language, `frequency_rank` in [3.3, 4.3], real-word regex filtered).
- `sandbox/exercise-lab/live_probe/run_all.py` — the full 3-step harness (fat matrix, split,
  small-seed scaling). Steps 2/3 are implemented but were never reached this run.
- `sandbox/exercise-lab/live_probe/one_call.py` — the minimal single-call smoke test used
  to validate auth/latency before building the matrix.
