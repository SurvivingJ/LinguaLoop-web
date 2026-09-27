# Can `typesafe/jev-1.13` classify LinguaLoop content into T1–T6 tiers?

Experiment date: 2026-09-26. Budget cap: $1.00. **Actual spend: $0.0257** (432 calls, 0 errors).
All work is read-only against Supabase (project `kpfqrjtfxmujzolwsvdq`); no DB writes were made.
Scripts, raw responses, and this file live in `exp_b/` (scratchpad only — nothing in the repo was touched).

---

## 1. Method

### 1.1 Data pulled
Stratified sample from the live `tests` table (`target_age_tier` + `transcript`), read-only via
`supabase-py` (script: `pull_tests.py`), stratified across whatever tiers actually exist per language
(the live library is heavily clustered — almost nothing is labelled T3/T5):

| Lang | n pulled | Tiers present (n) | Tests with ≥1 `test_attempts` row |
|---|---|---|---|
| zh | 60 | T1(16) T2(15) T3(1) T4(14) T6(14) | 13 |
| en | 60 | T1(12) T2(16) T3(1) T4(14) T5(1) T6(16) | 0 |
| ja | 59 (all active tagged ja) | T1(11) T4(24) T6(24) | 12 |

Empirical-difficulty coverage is thin: **en has zero tests with any `test_attempts` row in the sample**,
zh/ja have only 12–13. Any empirical-signal correlation below is on a very small n and should be read
as directional at best, per the memory note that assigned tiers are known to be imperfect (ja content
tends to run easier than its label).

### 1.2 jev call design
Own thin HTTP client (`jev_client.py`) against `POST https://openrouter.ai/api/alpha/decisions`,
concurrency 8, retry on 429 (honors `Retry-After`) and transient 402 (`limit_source:
openrouter_in_flight_budget`), hard budget cutoff at $0.90. `OPENROUTER_API_KEY` loaded via
`load_dotenv` from the repo `.env` before anything else.

Each item is one request carrying **both modes at once** (jev answers independent questions in
parallel off one `state`, so this is one call, not two):
- `tier_choice` (`type: "choice"`) — `criteria` keys `T1..T6`, values = the tier's native-language
  `TIER_DISPLAY_NAMES` + `TIER_CONSTRAINTS` text pulled directly from `services/categorical_maps.py`
  (LinguaLoop's own existing rubric, not new wording).
- `tier_score` (`type: "score"`) — same descriptions as an ordered array T1→T6.

**Hard rule honored**: for zh items, `instructions`/`criteria`/the state key (`文章`) are wholly
Chinese; for ja, wholly Japanese (`文章`); for en, wholly English (`passage`). See `jev_prompts.py`.

### 1.3 Tasks run
| Task | What | n calls |
|---|---|---|
| A — main | All 179 sampled tests, native prompts, choice+score combined | 179 |
| B — test-retest | 20 items (random cross-language mix), repeated 3× each | 60 |
| C — shuffle sensitivity | Same 20 items, choice-mode only, criteria key order **reversed** (T6→T1) | 20 |
| D — English-prompt control | zh (60) + ja (59) items re-run with English instructions/criteria, native-language passage text unchanged | 119 |
| E — sanity check | 54 hand-written, deliberately-unambiguous texts (3 per tier × 6 tiers × 3 languages), authored to match `TIER_CONSTRAINTS` style | 54 |
| **Total** | | **432** |

---

## 2. Results

### 2.1 Agreement with the assigned tier label (choice mode, live generated content)

| Lang | Exact | Within-1-tier | Mean signed diff (jev − label) |
|---|---|---|---|
| zh | 51.7% | 78.3% | −0.25 (jev slightly *lower* than label) |
| en | 60.0% | 83.3% | +0.03 |
| ja | 76.3% | 88.1% | +0.32 (jev slightly *higher* than label) |
| **Combined** | **62.6%** | **83.2%** | +0.03 |

Score mode (rounded to nearest tier) tracks 8–17 points *lower* on exact match than choice mode in
every language (zh 41.7%, en 50.0%, ja 59.3%) but the same on within-1 — score mode is noisier at the
boundary, not systematically worse ordinally.

**Ordinal correlation (Spearman, probability-weighted expected tier vs. assigned tier index)**:

| Lang | choice-mode ρ | score-mode ρ | choice-vs-score ρ (internal consistency) |
|---|---|---|---|
| zh | 0.697 | 0.730 | 0.989 |
| en | 0.768 | 0.760 | 0.995 |
| ja | 0.892 | 0.893 | 0.995 |
| **Combined** | **0.805** | **0.817** | — |

Choice and score modes agree with *each other* almost perfectly (ρ ≥ 0.989) — they are not
independent signals, just two different response encodings of the same underlying judgment. ja
shows the strongest agreement with its assigned label; zh the weakest.

### 2.2 Confusion matrices (choice mode; rows = assigned tier, cols = jev's pick)

**zh** (assigned → jev):
```
        T1  T2  T3  T4  T5  T6
  T1     3  13   0   0   0   0
  T2     1  13   0   1   0   0
  T3     0   0   0   1   0   0
  T4     0   7   0   7   0   0
  T5     0   0   0   0   0   0
  T6     0   1   3   1   1   8
```
Two clear failure modes: T1 zh content is almost always called **T2** (13/16) — jev thinks the
labelled-toddler content already uses compound sentences — and T4 zh content is a 50/50 split
between T4 and T2, i.e. half the "high-schooler" zh tests read as primary-school level to jev.

**en**:
```
        T1  T2  T3  T4  T5  T6
  T1     5   6   0   1   0   0
  T2     1  12   0   3   0   0
  T3     0   1   0   0   0   0
  T4     0   1   0   9   3   1
  T5     0   0   0   0   0   1
  T6     1   1   0   2   2  10
```

**ja**:
```
        T1  T2  T3  T4  T5  T6
  T1     4   3   0   4   0   0
  T2     0   0   0   0   0   0
  T3     0   0   0   0   0   0
  T4     0   0   0  20   1   3
  T5     0   0   0   0   0   0
  T6     0   0   0   0   3  21
```
ja's T4/T6 blocks are clean (20/24 and 21/24 exact); the only real confusion is at T1, where 4/11
labelled-toddler ja tests are called T4 — consistent with the memory note that ja content tends to be
generated easier than intended **or** harder in specific cases; jev doesn't resolve this ambiguity,
it just reflects the same surface signal the label was built from.

**Caveat on what "disagreement" means here**: because assigned tiers are known to be imperfect
(memory: ja content runs too easy for its label), a jev/label disagreement is not evidence jev is
wrong — see §2.4 for the (thin) empirical cross-check.

### 2.3 Test-retest stability (20 items × 3 identical repeated calls)
- **Choice mode**: all 3 repeats picked the same tier for **85%** of items (17/20).
- **Score mode**: essentially deterministic — mean score range across repeats = **0.029** (on a
  0–5 scale), max range 0.09, mean std 0.013. jev's stated non-reasoning, typed-answer design shows
  up here as very low sampling variance; the 3/20 choice flips were all boundary cases (adjacent-tier
  ties), not wild jumps.

### 2.4 Order-shuffle sensitivity (same 20 items, criteria key order reversed T6→T1)
- **Choice flipped for 5%** of items (1/20) when the option order was reversed.
- Mean L1 distance between the two probability vectors: **0.17** (out of a max of 2.0), max 0.48.
- Interpretation: jev is *not* perfectly order-invariant (a JSON object's key order shouldn't matter
  semantically, but it evidently reaches the underlying model in some order-sensitive form), but the
  effect is small and rarely flips the final answer. For a production pipeline, average two calls
  with reversed criteria order if the very last bit of stability matters; not necessary for routine use.

### 2.5 Native-language vs. English-prompt control (zh, ja)
| Lang | Native vs. English choice **match rate** | Exact agreement w/ assigned (native) | Exact agreement w/ assigned (English) | Mean \|Δexpected tier\| |
|---|---|---|---|---|
| zh | 95.0% | 51.7% | 51.7% | 0.12 |
| ja | 89.8% | 76.3% | 76.3% | 0.10 |

**Headline: native-language prompts made no measurable difference.** Same exact-agreement rate to
the decimal point in both languages, >89% of individual item-level choices identical between the
native and English-prompt runs, and the expected-tier gap between the two prompt styles (~0.1 tier)
is far smaller than jev's disagreement with the assigned label (~0.7–0.8 tiers of mean abs diff).
Two readings are possible: (a) jev handles the native passage text on its merits regardless of what
language the rubric is phrased in, or (b) with only ~60 items per language the test lacks power to
detect a small native-language benefit. Given how close the numbers are (95%/90% match, <0.5% gap
in exact-agreement), (a) is the more likely explanation, but this is not a strong-power test — treat
as a soft finding, not a settled one.

### 2.6 Sanity check: can jev separate deliberately unambiguous texts at all?
54 hand-authored texts (3/tier × 6 tiers × 3 languages), written to unambiguously match each tier's
`TIER_CONSTRAINTS` description (see `sanity_texts.json`).

| Lang | Exact agreement | Monotonic T1→T6 (choice) | Monotonic (score) | Mean expected tier T1 → T6 |
|---|---|---|---|---|
| zh | 94.4% | ✅ | ✅ | 1.00 → 1.99 → 2.94 → 4.02 → 5.18 → 5.99 |
| en | 100% | ✅ | ✅ | 1.00 → 2.00 → 3.03 → 4.05 → 4.98 → 5.98 |
| ja | 88.9% | ✅ | ✅ | 1.00 → 2.07 → 3.10 → 4.41 → 5.17 → 5.99 |

**Yes — jev separates extremes cleanly and monotonically in all three languages** when the input
text is actually unambiguous. This is the key contrast with §2.1–2.2: jev's classifier mechanism
works; the 38–48% "disagreement" rate on live generated content reflects that **real generated test
transcripts are genuinely more ambiguous / boundary-straddling than the tier system's own textbook
examples**, not that jev can't do the task. T1 and T6 in particular are essentially perfectly
separated (mean expected tier lands within 0.01 of the true endpoint in every language).

### 2.7 Empirical-difficulty cross-check (thin data — read with caution)
Only 12–13 sampled tests per language (zh, ja) have any `test_attempts` rows; en has none in-sample.
Spearman correlation of jev's expected tier against `mean(test_elo_before)` for attempted tests:

| Lang | n | choice-mode ρ vs. empirical ELO | score-mode ρ vs. empirical ELO |
|---|---|---|---|
| zh | 13 | −0.005 (≈ none) | −0.038 (≈ none) |
| ja | 12 | +0.371 | +0.350 |

zh shows no relationship between jev's tier call and the empirical difficulty users actually
experienced; ja shows a weak positive one. Given n≈12, neither number should be trusted as more than
a hint — but it is at least consistent with the standing memory finding that assigned-tier agreement
is not a proxy for real-world accuracy, and that jev (like the label itself) may be reading surface
features that don't track empirical difficulty, especially for zh.

---

## 3. Cost / latency, and a re-tiering estimate

Measured from Task A (179 calls, both modes combined, real generated-test-length transcripts,
avg. 1,548 input tokens/call — transcripts run 50–6,829 chars):

| Metric | Value |
|---|---|
| Mean cost/call (both modes) | **$0.0000650** |
| Mean latency/call | **0.557 s** (p50 0.531 s, p95 0.641 s) — real round-trip is ~2.5× OpenRouter's quoted 0.22 s P50 for the model itself; the gap is network/overhead on this end, not the model |
| Mean cost/call, choice-only | $0.0000455 |
| Mean cost/call, English-control (both modes) | $0.0000542 |

**Full-library re-tiering estimate** (active tests with a tier label in the DB today: zh 125 + en 121
+ ja 59 = **305 tests**):

| | Both modes | Choice mode only |
|---|---|---|
| Projected total cost | **$0.0198** | **$0.0109 (est.)** |
| Projected wall-clock @ concurrency 8 | **~21 seconds** | ~15 seconds (est.) |

This is negligible against the $1 cap — cost is a non-issue at this library size; it would remain
negligible even at 100× the current library (~$2, ~35 minutes at concurrency 8).

**Comparison to the existing LLM tier judge**: the closest analog in the repo is
`services/topic_generation/agents/tier_fit_judge.py`'s `TierFitJudge.best_tier()`, which walks tiers
ascending with **up to 6 sequential binary chat-completion calls per topic** (no native multi-choice
mode exists there today, and per the judge inventory it has **no dedicated cost/latency figure logged
separately** — it shares `call_llm`'s general instrumentation, not something isolated in `llm_calls`).
Structurally: jev replaces up to 6 sequential calls with **1 parallel-question call**, at a per-call
cost roughly **an order of magnitude below** typical small-model judge calls in this repo (e.g. the
distractor-plausibility judge's zh/ja model, `gemini-3.1-flash-lite`, is described elsewhere in the
codebase's own memory as "6.7× cheaper" than its qwen predecessor and is still a chat-completions
model billed on both input *and* output tokens — jev is input-only and typically returns in under a
tenth of the token budget because there's no output generation to pay for). We do not have a
directly-measured dollar figure for `tier_fit_judge` itself to give an exact multiplier — flagging
this as the one number in this report that would need a live side-by-side run to pin down precisely.

---

## 4. Honest caveats

1. **Assigned tiers are not ground truth.** Per standing project memory, ja content is known to run
   easier than its label; the label itself was produced by a different (or no) LLM judge at
   generation time. A jev/label disagreement in §2.1–2.2 is therefore ambiguous evidence — it could
   mean jev is wrong, or that jev is right and the label is wrong. §2.6 (sanity check) is the only
   task here with real ground truth, and jev passes it cleanly.
2. **Empirical cross-check is underpowered.** n=12–13 for zh/ja, n=0 for en. The near-zero zh
   correlation and weak positive ja correlation (§2.7) are suggestive, not conclusive.
3. **English-vs-native control is a soft null result**, not a proof of "language doesn't matter" —
   see the power caveat in §2.5.
4. **Documentation gap on jev's language support.** OpenRouter's own docs (per `jev_api_summary.md`)
   do not explicitly document non-English support one way or the other. This experiment is now a
   much larger (432-call) empirical data point than the original single-item smoke test, and shows
   jev handling zh/ja content coherently (monotonic sanity-check separation, low retest variance) —
   but it remains an empirical finding on top of undocumented behavior, not a documented guarantee.
5. **Latency here (~0.56s) is call-round-trip from this machine**, not the model's own P50 — don't
   conflate the two when estimating a different environment's throughput.
6. **The `criteria`-order effect (§2.4) is real but small** — average two reversed-order calls if a
   downstream decision is genuinely on a knife's edge; not needed for routine tiering.
7. **Cost/latency for `tier_fit_judge` was not independently measured** in this pass (see §3) — the
   "order of magnitude cheaper" claim is a structural/reasoned estimate from token-billing mechanics,
   not a measured side-by-side numbers.
8. Only 432 of a possible much larger call budget were used ($0.0257 of $1.00) — there is ample
   remaining budget if a reviewer wants a larger sample, more retest repeats, or a full 305-test live
   re-tier as a follow-up (not run here per the "no DB writes" instruction — re-tiering the live
   `target_age_tier` column was out of scope, this report only estimates its cost).

---

## 5. Files
- `pull_tests.py` — stratified Supabase pull (read-only)
- `jev_prompts.py` — native-language prompt builder (reuses `services/categorical_maps.py`)
- `jev_client.py` — thin HTTP client, concurrency, retry, budget cap
- `run_experiment.py` — orchestrates Tasks A–E
- `analyze.py` — all metrics in this report
- `sanity_texts.json` — the 54 hand-authored deliberately-levelled texts
- `sample_{zh,en,ja}.json`, `raw/task_{a..e}_*.json`, `metrics.json` — data and full raw results
