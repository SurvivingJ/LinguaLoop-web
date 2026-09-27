---
title: Test Tier Assignment — Technical Specification
type: feature-tech
status: complete
prose_page: test-tier-assignment.md
last_updated: 2026-09-27
dependencies:
  - "services/jev_client.py (Decisions API client, shared with the entailment judge)"
  - "services/tier_classifier.py"
  - "services/categorical_maps.py (TIER_DISPLAY_NAMES, TIER_CONSTRAINTS, DIFFICULTY_TO_TIER)"
  - "tests.age_tier_* columns; tests_tier_backup_20260926; tests_tier_backup_20260927_v1; apply_jev_retier RPC"
  - "OPENROUTER_API_KEY (same key and credit pool as every other model call)"
breaking_change_risk: medium
---

# Test Tier Assignment — Technical Specification

Decision record: [[decisions/ADR-029-jev-tier-assignment]]. Evidence:
[[evaluations/jev-tier-calibration-2026-09-27]], [[evaluations/jev-judge-feasibility-2026-09-26]].

## Architecture Overview

```
topic.target_age_tier ──► prose written for target tier (word budget, prose prompt)
                                   │
                                   ▼
        tier_classifier.classify_passage(prose, language_code)
          └─ jev_client.call_jev  POST /api/alpha/decisions  (one `score` question)
                                   │  answers.tier = {score 0-5, confidence, probabilities}
                                   ▼
        tier = 1 + count(score >= cut)   cuts = SCORE_THRESHOLDS[lang] or DEFAULT
                                   │
                                   ▼  (assigned tier replaces target from here on)
  dedup scope · tier config · initial ELO · question mix · judges gate · slug
                                   │
                                   ▼
   INSERT tests(target_age_tier, difficulty, age_tier_*)   [JevError ⇒ nothing written]
```

`TestGenerationOrchestrator._generate_test` is the only place a test row is created (both the
queue path and `run_batch`). The classification is repeated on the retry prose when the dedup
check forces a second draft. The legacy `TestService.save_test` path was removed 2026-09-26.

## Database Impact
See [[database/schema.tech]] (`tests`) and [[database/rpcs.tech]] (`apply_jev_retier`).
- `tests.target_age_tier` (smallint 1–6) — the assigned tier.
- `tests.difficulty` — derived one-way: `min(d for d, t in DIFFICULTY_TO_TIER if t == tier)`
  (`TIER_ID_TO_DIFFICULTY` = 1, 3, 5, 6, 7, 8). Still read by `dictation_max_words`,
  `get_recommended_tests`, `build_daily_session`, `tests_containing_sense`.
- `tests.age_tier_score` (real, raw 0–5), `age_tier_confidence`, `age_tier_probabilities`
  (`{"T1": p, …, "T6": p}`), `age_tier_model` (dated jev snapshot), `age_tier_calibration`
  (`default` | `ja-2026-09-27` | `zh-2026-09-27`), `age_tier_assessed_at`.
- `tests_tier_backup_20260926` (307 rows: original tier/difficulty/seeded_elo) and
  `tests_tier_backup_20260927_v1` (state after the first jev pass, before calibration).
  Both RLS-on with no policies (service role only).
- `llm_calls`: `pipeline='tier_assignment'`, `task_name` `jev_tier_passage` / `jev_tier_topic`,
  `judge_verdict='T3'`, `judge_confidence`, `cost_usd` = `usage.cost`, token counts.
  Calibration experiments log as `pipeline='diag'`, `task_name='jev_tier_calibration'`.
- ELO (`test_skill_ratings`, `tests.seeded_elo`) is not touched by any re-tier.

## API / RPC Surface

### `classify_passage(text: str, language_code: str): TierAssessment`
- **Purpose:** place one passage on the T1–T6 scale.
- **Arguments:** `language_code` ∈ zh/en/ja. Empty text → `ValueError`. Text over 24,000
  characters is truncated with a warning (longest live transcript ≈ 6.8k).
- **Returns:** `TierAssessment(tier, expected_tier, score, confidence, probabilities{1..6},
  model, cost_usd, calibration)`.
- **Errors:** `JevError` (see below) or malformed answer → `JevError`. Never a default tier.
- **Prompt:** written entirely in the content language (zh in Chinese, ja in Japanese, en in
  English): one `score` question whose ordered `criteria` array is the six
  `TIER_DISPLAY_NAMES` + `TIER_CONSTRAINTS` strings verbatim; state key `文章` / `passage`.

### `classify_topic(concept: str, vocabulary: str = ''): TierAssessment`
Same, on `concept + distinctive vocabulary`, English prompt. Used by `TierFitJudge`.

### `tier_from_score(score, language_code=None): int`
`1 + sum(score >= cut for cut in SCORE_THRESHOLDS.get(lang, DEFAULT_THRESHOLDS))`.
NaN, infinity, None, bool → `JevError`.

| Language | Cut points (0–5 score) | Label |
|---|---|---|
| default (en) | 0.5, 1.5, 2.5, 3.5, 4.5 (round half up) | `default` |
| ja | 0.95, 2.65, 3.25, 4.2, 4.4 (fitted) | `ja-2026-09-27` |
| zh | 0.75, 1.75, 2.75, 3.75, 4.75 (default shifted −0.25) | `zh-2026-09-27` |

### `TierFitJudge.judge(concept, distinctive_vocabulary, tier): TierFitVerdict`
`fits = assessed_tier <= tier` (tier is a floor on reader capability). No fail-open path: a
`JevError` propagates and aborts the topic run.

### `call_jev(state, questions, *, pipeline, task_name, language_code, summarize, …): JevResult`
([services/jev_client.py](../../services/jev_client.py))
- Retries with backoff: network errors, 429 (honours `Retry-After`), the documented 5xx set,
  and the transient 402 (`limit_source = openrouter_in_flight_budget`). Any other 4xx,
  including the permanent 402 (credits/key limit), raises immediately. Default 5 attempts.
- At most `JEV_MAX_CONCURRENCY` (default 8) requests in flight per process.
- One `llm_calls` row per success, insert serialised by a lock (concurrent inserts dropped
  ~2% of rows). `usage.cost` missing ⇒ NULL plus a warning, never an estimate.
- `JevError.status` is the last HTTP status (None for network/shape errors).
- The API key is read at call time; scripts still `load_dotenv()` before importing services.

### `apply_jev_retier(p_rows jsonb): integer`
- **Purpose:** atomically set tier, audit columns and (where the tier moved) difficulty for a
  list of active tests. **Arguments:** array of `{id, new_tier, score, confidence,
  probabilities, model, calibration}`. **Errors:** raises, rolling everything back, unless
  exactly `jsonb_array_length` rows update. **Auth:** service role only.
- `difficulty` is rewritten only where `target_age_tier` changed, to
  `dim_complexity_tiers.difficulty_min` of the new tier.

## Operations

| Task | Command |
|---|---|
| Classify every active test (read-only, saves results.json) | `python scripts/retier_tests_with_jev.py` (`--limit N` smoke test) |
| Apply a saved re-tier atomically | `python scripts/retier_tests_with_jev.py --apply` |
| Re-derive tiers from stored scores after editing a table | `python scripts/rederive_tiers.py --lang ja [--apply]` |
| Build a blind labelling sample | `python scripts/build_tier_gold_sample.py --lang zh --n 60` |
| Fit and cross-validate a table | `python scripts/fit_tier_thresholds.py --lang zh` |
| Reverse | `UPDATE … FROM tests_tier_backup_…` — statements in `migrations/task819_…sql` and `task821_…sql` |

Recalibrating a language: build the sample → two independent blind readers write
`<lang>_gold_A.json` / `_B.json` → fit → only change a table if cross-validation beats the
default by more than noise → add the table and label to `tier_classifier.py` → add a fixture
under `tests/fixtures/` → `rederive_tiers.py --apply`.

## Key Architectural Decisions
1. **Measure the passage, not the topic.** *Rationale:* the target tier is the prompt's aim,
   not the outcome. *Rejected:* keep target as stored tier (source of the bad labels).
2. **Score mode, thresholds per language.** *Rationale:* jev's ordering is right but its
   expected-tier scale is compressed and language-dependent; cut points fix that.
   *Rejected:* choice mode (argmax); a uniform offset for ja (41/59 vs 57/59); a prompt
   tweak (no gain, lower rank correlation).
3. **No fallback, fail the test.** *Rationale:* a guessed tier is indistinguishable from a
   measured one. *Rejected:* fail-open (the old topic judge), a chat-model fallback.
4. **Store the raw score.** *Rationale:* any table change is a re-derivation, not a re-call.
5. **Do not re-seed ELO of existing tests.** *Rationale:* live ELOs are not tier-anchored.

## Security Considerations
- `apply_jev_retier` and both backup tables are service-role only (function grants revoked from
  PUBLIC/anon/authenticated; RLS on, no policies).
- Passage text is sent to a third party (OpenRouter → TypeSafe); it is generated content, not
  user data.
- One provider, alpha endpoint (`/api/alpha/decisions`), no failover, undocumented zh/ja
  support (empirical only). An outage stops generation by design.

## Testing Strategy
`tests/test_jev_client.py` (status, verdict logging, concurrency bound, `cost_usd` reaching the
row), `tests/test_jev_entailment.py` (retry policy, shared client),
`tests/test_tier_classifier.py` (score→tier tables, prompts in the content language, ordering,
no-fallback, `TierFitJudge`, gold-set regression for ja and zh),
`tests/test_jev_tier_generation.py` (assigned tier reaches every stored/seeded value, failure
writes nothing and fails the queue item), `tests/test_test_gen_fail_closed.py` (fixture stubs
jev).

## Related Pages
- [[features/test-tier-assignment]]
- [[decisions/ADR-029-jev-tier-assignment]]
- [[evaluations/jev-tier-calibration-2026-09-27]]
- [[database/schema.tech]]
- [[database/rpcs.tech]]
- [[tasklist/jev-tier-assignment.tasks]]
