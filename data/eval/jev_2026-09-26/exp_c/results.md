# Can `typesafe/jev-1.13` grade LinguaLoop's Dual Translation rubric?

**Date:** 2026-09-26 · **Budget:** $1.00 cap, **spent $0.0153** (110 API calls) · **No DB writes.**

## 1. Method

**Model under test:** `typesafe/jev-1.13` via OpenRouter's Decisions API
(`POST /api/alpha/decisions`, `{model, state, questions}`) — not a chat model,
no free-text/reasoning output, $0.042/M input tokens, $0/M output tokens.
Client: a standalone thin HTTP wrapper (`exp_c/jev_client.py`, `requests`,
concurrency 6, retry on 429/5xx honoring `Retry-After`), reading
`OPENROUTER_API_KEY` from the repo `.env` — no `services.*` module was
imported for anything that touches the network or DB.

**Gold data:** all 90 items in `tests/fixtures/dt_gold/{en,zh,ja}.json`
(30/language, 10 clean / 15 single-error / 5 multi-error), human-adjudicated,
with `expected_bands` for all 5 rubric dimensions derived by the live scoring
formula (rubric v5/v6, unchanged in v6 except band-descriptor wording).

**Rubric source:** band descriptors were transcribed verbatim from the live
`migrations/dt_rubric_v6_seed.sql` (the exact config a `--rubric-file` harness
run against this same gold set used on 2026-07-19 — see §2 for that run's
numbers). Dimension names, REFERENCE/LEARNER labels, and instruction phrasing
were sourced from `services/dual_translation/prompts.py`'s per-`l2_code`
strings. **Age tier per gold set** (`tests/fixtures/dt_gold/README.md`):
en/ja = tier 3 (naturalness descriptors: "the way a native young teen would
say it"), zh = tier 6 (naturalness descriptors: "an educated native writer").
Naturalness is the one tier-varying dimension (ADR-018); accuracy/fidelity/
understandability/range are tier-invariant in the live config.

**HARD RULE compliance:** for the native-language runs, every `instructions`
string, every `criteria` level description, and the `state` object's own key
names (e.g. `"参考译文"`/`"学习者译文"` for zh, `"参照文"`/`"学習者文"` for ja)
are wholly in the L2 being graded — nothing in English leaks into the zh/ja
native prompts except the internal `questions` object's key names
(`score_accuracy`, `noul_omission`, …), which are pure machine identifiers
never surfaced to the model as rubric content, mirroring OpenRouter's own
tutorial convention (`is_bug`, `team`, `urgency`).

**Per-item request (one Decisions API call per item, 12 questions batched):**
- 5 dimensions × **score mode** — `criteria` = the 4 band descriptors,
  ascending band1(worst)→band4(best), `score ∈ [0,3]` mapped to band = round(score)+1.
- 5 dimensions × **choice mode** variant — same 4 descriptors as `criteria`
  keys `band1..band4`.
- 2 **noul** (yes/no) error-detection questions: *"does the `learner` text
  omit meaning present in the `reference` text?"* and *"does the `learner`
  text contain a grammar error?"*, phrased natively per language.

Ground truth for the noul questions (not directly in the gold schema, so
derived): **omission** = gold has an `expected_errors[].subtype == "omission"`
entry (literally present in all three languages' v5 taxonomies); **grammar**
= gold `expected_bands.accuracy < 4` (accuracy is a pure penalty function of
grammar-dimension-tagged errors, so a sub-4 band implies at least one such
error existed).

**English-prompt control:** 10 of 30 items per zh/ja (every 3rd item,
spanning clean/single/multi), same content, full English `instructions`/
`criteria`/dimension names/state keys (`"reference"`/`"learner"`) instead of
native.

Total: 90 native calls + 20 control calls = **110 calls**, cost **$0.0153**,
mean latency **0.53s** (p50 0.50s, p95 0.63s) — comfortably inside the $1 cap
and fast enough that concurrency wasn't needed to stay in budget.

## 2. Live-stack baseline being compared against

Reused, not re-run (per instructions — the live harness is expensive and
already has a run against this exact gold set + this exact rubric v6
candidate): **`wiki/evaluations/dt-grading-v2-2026-07-19.md`**, TASK-632, the
Detector/Verifier v2 cascade graded with `--rubric-file
migrations/dt_rubric_v6_seed.sql` (the same v6 this experiment uses) against
the same 90 gold items. Slugs: EN `gemini-2.5-flash-lite`+`gemini-3.5-flash`;
JA/ZH `qwen3.6-flash`+`qwen3.7-plus`. Cost: EN **$0.74 measured** (54 calls /
30 items ⇒ **≈$0.025/item**); JA+ZH **≈$2.5–3.5 estimated whole-pass** (60
items ⇒ **≈$0.042–0.058/item**), dominated by `qwen3.7-plus` output tokens.
Latency: JA items ran **~2–3 min each** (sequential Detector→Verifier+Explainer
on a reasoning-heavy slug); EN/ZH per-item latency isn't broken out in that
report.

**Live-stack per-dimension QWK (EN / JA / ZH):**

| dim | EN | JA | ZH |
|---|---|---|---|
| accuracy | .778 | .412 | .570 |
| understandability | .746 | .332 | .577 |
| fidelity | .487 | .371 | **.891** |
| range | .000 | .000 | 1.000 (degenerate — constant rater) |
| naturalness | .099 | .053 | .020 |
| **overall** | **.824** | .419 | .245 |

## 3. jev results — per-dimension QWK vs the same gold

| dim | lang | jev score-mode QWK | jev choice-mode QWK | live-stack QWK | jev exact-match |
|---|---|---|---|---|---|
| accuracy | EN | .095 | .095 | **.778** | 60% |
| accuracy | ZH | **.661** | .661 | .570 | 87% |
| accuracy | JA | .308 | .206 | .412 | 70% |
| fidelity | EN | .314 | .521 | .487 | 73–77% |
| fidelity | ZH | .893 | .893 | .891 | 87% |
| fidelity | JA | **.740** | **.830** | .371 | 70–83% |
| understandability | EN | .205 | −.105 | **.746** | 77–80% |
| understandability | ZH | .571 | −.085 | .577 | 83% |
| understandability | JA | .332 | .000 | .332 | 83% |
| range | EN | .000 | .000 | .000 | 77–60% |
| range | ZH | .000 | .000 | 1.000 (degenerate) | 93% |
| range | JA | .000 | .000 | .000 | 77–70% |
| naturalness | EN | .065 | .000 | .099 | 33–37% |
| naturalness | ZH | .091 | .151 | .020 | 47–60% |
| naturalness | JA | .059 | .079 | .053 | 37–43% |

**Overall band (weighted mean of jev's own 5 raw dimension guesses, same
per-language weights as production — see caveat below):**

| lang | jev score-mode QWK | jev choice-mode QWK | live-stack overall QWK |
|---|---|---|---|
| EN | .467 | −.024 | **.824** |
| ZH | **.714** | .259 | .245 |
| JA | **.655** | .590 | .419 |

### Where jev is close vs. far

- **Far (badly):** EN accuracy (.095 vs .778) and EN understandability (.205
  vs .746) — jev's single-shot classification misses exactly the kind of
  single-word, grammatically-valid-but-meaning-inverting error the EN gold set
  is built around (§4 example). EN is also the one language where the live
  stack's dedicated Detector/Verifier cascade is strongest, so this is the
  widest gap in either direction.
- **Close or better:** ZH accuracy (.661 vs .570), ZH fidelity (.893 vs .891,
  essentially tied), **JA fidelity (.740–.830 vs .371 — jev clearly better)**,
  JA understandability (exactly tied at .332). On the two languages where the
  live stack pays for a slow, expensive reasoning-heavy `qwen3.7-plus` verifier
  and still gets middling overall QWK (.245 ZH, .419 JA), jev's near-zero-cost
  single call is competitive to better on 3 of 5 dimensions.
- **Both approaches equally weak:** naturalness (QWK ≈ 0–0.15 everywhere,
  both methods) and range (QWK = 0 everywhere except ZH's live-stack 1.000,
  itself flagged "degenerate — constant rater" in the original report). The
  gold set's own README doesn't vary these two dimensions much per-item, so
  low QWK here is largely a **gold-set signal problem, not evidence against
  either grader** (the 2026-07-19 report flags this too, under Finding #3).
- **Score mode > choice mode**, especially for understandability, which goes
  *negative* under choice mode in EN/ZH — a sign of choice-mode collapsing
  onto one favored option more than the probability-weighted score mode does.
  Fidelity is the one dimension where choice mode sometimes clearly beats
  score mode (JA .830 vs .740).

**Methodological caveat on "overall":** the live stack's real overall band is
NOT a weighted mean of 5 independently model-judged dimensions — accuracy/
fidelity/understandability are *derived* in Python from severity-weighted
error penalties (`services/dual_translation/scoring.py`), and only
naturalness/range are model-judged in production. The "jev overall" row above
is the weighted mean of jev's own 5 *raw* per-dimension guesses (same
`weights.default`/`weights.by_language` as production), which is a different
computation from what the live stack actually reports as "overall QWK." Take
the overall-band row as a rough gauge, not an apples-to-apples number — the
**per-dimension table is the fair comparison**.

## 4. Example: a confidently-wrong jev call (EN, `en_seed_15`)

```
REFERENCE: "... You can make many things with it. ..."
LEARNER:   "... You can make many things without it. ..."
```
Gold: one **critical**, meaning-inverting `preposition` error → `accuracy` band **1**.
jev: `score_accuracy` = 4 (confidence 0.75), `noul_grammar` = 0.14 ("no error").

"without it" is grammatically perfect English — there is no syntactic signal
to catch, only a semantic one, and jev has no reasoning trace to compare
meaning across the two texts the way a chat-model verifier does. Tellingly,
jev's **fidelity** judgment on the same item *did* pick up something wrong:
`score_fidelity` = 2, but at **confidence 0.13** (probabilities split
0.41/0.03/0.55/0.01 across bands 1–4) — a genuinely uncertain, half-right
signal on the wrong dimension, rather than a clean catch. This is the
representative failure mode: single-token semantic inversions that don't
disturb grammar are largely invisible to jev's typed-decision format.

## 5. Noul error-detection (yes/no)

| question | lang | n | base rate | accuracy@0.5 | AUC |
|---|---|---|---|---|---|
| omission | EN | 30 | 7% | 93% | .96 |
| omission | ZH | 30 | 3% | 87% | .62 (n=1 positive — unreliable) |
| omission | JA | 30 | 10% | 87% | .86 |
| grammar | EN | 30 | 30% | 70% | .76 |
| grammar | ZH | 30 | 30% | 90% | .89 |
| grammar | JA | 30 | 30% | 67% | .85 |

AUC (rank-separation) is decent-to-good everywhere except ZH-omission (which
has only 1 true positive in 30 items — not a usable estimate). Accuracy@0.5
lags AUC on JA-grammar (67% acc vs .85 AUC), which is a **threshold
miscalibration** signature, not a lack of signal — consistent with jev's own
documented guidance to pick per-question thresholds from a labeled sample
rather than assume 0.5 is right.

## 6. Hybrid tier-0 pre-filter: how much could route away?

Simulated rule: an item is a routing candidate if **every** dimension's
choice-mode band is unanimously 4 ("confidently perfect") or unanimously ≤2
("confidently bad") **and** every dimension's choice confidence ≥ τ. Routed
items skip the expensive live cascade; error = jev's weighted-mean overall
band disagreeing with gold's.

| lang | τ=0.7 routed | error among routed | τ=0.8 routed | τ=0.9 routed |
|---|---|---|---|---|
| EN | 2/30 (6.7%) | 0/2 | 0/30 | 0/30 |
| ZH | 3/30 (10%) | 0/3 | 1/30 (3.3%) | 0/30 |
| JA | 2/30 (6.7%) | 0/2 | 1/30 (3.3%) | 0/30 |

**Honest read:** the *all-5-dimensions-must-agree* gate as tested is too
strict to route much volume on this gold set — at most 10% of items qualify
even at the loosest threshold tried, and 0% at τ≥0.9. Where it does fire, it
is error-free in this sample, but **n=2–3 routed items per language is far
too small to trust that 0% as a real error rate** — it is a hint, not an
estimate. A more promising design not built here for budget/time reasons:
gate on only the two highest-weighted dimensions (accuracy 30–40%,
understandability 30%) rather than requiring unanimous agreement across all
5 — naturalness and range are both near-random signal (§3) and are very
likely what's disqualifying otherwise-confident items from the all-5 gate.

## 7. Cost / latency vs. the live stack

| | jev (this experiment) | live stack (2026-07-19 run) |
|---|---|---|
| cost/item, EN | **$0.00014** (12 Qs/item) | ≈$0.025 |
| cost/item, JA/ZH | **$0.00014** | ≈$0.042–0.058 |
| → cost ratio | | **~180×–420× more expensive** than jev |
| latency/item, JA | **0.53s mean** (p50 .50s / p95 .63s) | ~2–3 min |
| → latency ratio | | **~250×+ slower** than jev on JA |

jev's own documented $0/M-output pricing means its cost is driven entirely by
the (fairly verbose, since it embeds full 4-level band descriptors ×5 dims ×2
modes) input tokens — mean 3,313 input / 371 output tokens per 12-question
call. A leaner single-mode (score-only, no choice-mode duplicate) design would
roughly halve this again.

## 8. Native-language vs. English-prompt control (zh/ja, n=10/language)

| dim | ZH native QWK | ZH English-control QWK | JA native QWK | JA English-control QWK |
|---|---|---|---|---|
| accuracy | .615 | .615 (tied) | **.412** | **−.154** |
| fidelity | **.941** | .844 | .747 | .805 (control slightly better) |
| understandability | **.615** | **−.087** | 0 | 0 (degenerate, n=10) |
| range | 0 | 0 | 0 | 0 |
| naturalness | 0 | 0 | 0 | 0 |

Native-language prompting clearly wins on ZH-understandability and
JA-accuracy (the English control is actively *worse than chance-correlated*
on both — negative QWK). It is roughly tied on ZH-accuracy and slightly
*behind* on JA-fidelity — not a clean sweep. **Caveat:** n=10/language is very
small; several cells are 0 or wildly negative simply because so few distinct
gold labels exist in a 10-item slice (the same degenerate-QWK problem as
naturalness/range in §3, now happening to more dimensions because of the
smaller n). Treat this section as a directional signal (native phrasing
plausibly helps, sometimes by a lot) rather than a precise effect size.

## 9. Overall caveats

- **n=30/language (n=10 for the control) is small.** The 2026-07-19 live-stack
  report itself notes QWK swings of ±0.1 between identical-code runs at this
  sample size — treat every QWK above as having that much noise baked in.
- Several QWK values of exactly **0.000** are the "degenerate constant rater"
  case (near-zero variance in gold labels for that dim/lang/n slice), not
  necessarily "no signal" — this affects range everywhere and naturalness/
  understandability in the n=10 control slices.
- The **grammar/omission noul ground truth was derived, not hand-labeled** —
  a reasonable proxy from the gold's own scoring formula, but not an
  independent human judgment of "is there a grammar error."
- jev's documented lack of a language-support guarantee (§1 of
  `jev_api_summary.md`) held up fine in this test (all three languages parsed
  and returned sensible answers), but this is 90+20 items, not a stress test.
- No confidence-weighted ensembling, few-shot exemplars, or prompt iteration
  was attempted — this is jev's out-of-the-box behavior on a first-pass
  prompt design, not a ceiling on what jev could do here.

## Files

- `exp_c/rubric_data.py` — hand-transcribed v6 band descriptors + L2 strings
- `exp_c/build_requests.py` — per-item request builder + answer decoder
- `exp_c/jev_client.py` — thin Decisions-API HTTP client (concurrency 6, retry)
- `exp_c/run_experiment.py` — orchestrator (110 calls, `raw/results.jsonl`)
- `exp_c/analyze.py` — all metrics in this report (`raw/analysis.json`)
