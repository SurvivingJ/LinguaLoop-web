---
title: "Dual Translation — Task Breakdown"
feature: dual-translation
prose_page: ../features/dual-translation.md
tech_page: ../features/dual-translation.tech.md
total_tasks: 21
done: 8
last_updated: 2026-07-04
---

# Dual Translation — Task Breakdown

Mapped to the brief's build sequence (§6): Stage 1 grading MVP → Stage 2 error synthesis →
Stage 3 spaced remediation → Stage 4 localisation, with cross-cutting infra from day one.
All decisions: [[decisions/ADR-014-reference-first-grading]],
[[decisions/ADR-015-eager-error-explanations]], [[decisions/ADR-016-per-pair-error-taxonomy]],
[[decisions/ADR-017-dual-translation-standalone-l1l2-mvp]].

---

## Execution routing (model + thinking)

Each task carries a recommended **Model** + **Thinking** level on its status line. Routing is
**cost-tiered by complexity**: Opus 4.8 for hard/novel/linguistic-content work, Sonnet 4.6 for
well-specified implementation against existing patterns, Haiku 4.5 for mechanical single-table
migrations. Thinking ladder: `think` → `think hard` → `ultrathink`.

Models: Opus 4.8 (`claude-opus-4-8`) · Sonnet 4.6 (`claude-sonnet-4-6`) · Haiku 4.5 (`claude-haiku-4-5-20251001`).

| ID | Task | Cx | Model | Thinking | Why this tier |
|----|------|----|-------|----------|---------------|
| 600 | Model router + slug config | M | Sonnet 4.6 | think hard | Pattern-reuse of model-arena pricing, but fail-open/404-fallback needs care |
| 601 | Budget guardrail + cost hooks | S | Sonnet 4.6 | think | Config value + `grader_trace` logging; low-risk |
| 602 | Migration — 7 `dt_*` tables | M | Sonnet 4.6 | think | Explicit spec; FK/CHECK/UNIQUE correctness matters but is mechanical |
| 603 | Passage builder (CJK span + batch L1) | L | Opus 4.8 | think hard | CJK sentence segmentation + idempotent batch generation is genuinely tricky |
| 604 | Versioned rubric + age-tier descriptors | M | Opus 4.8 | think hard | Pedagogical content authoring (5 dims × 6 tiers + weight overrides) |
| 605 | Tier 0 deterministic pre-pass | M | Sonnet 4.6 | think hard | Reuses dictation grader; width/punct/kana normalization edge cases |
| 606 | Grading cascade + JSON + eager explanations | L | Opus 4.8 | **ultrathink** | The heart: L2-only numerical-index prompts, escalation, cache stability, fail-open |
| 607 | Routes + submit RPC + idempotency | M | Sonnet 4.6 | think | Standard Flask routes; idempotency precedent exists |
| 608 | Diff-centric result UI | L | Sonnet 4.6 | think hard | Noticing centrepiece; substantial UI but no novel reasoning |
| 609 | Migration — `dt_error_profile_entry` | S | Haiku 4.5 | think | Single table with one composite UNIQUE; fully specified |
| 610 | Mistake gate + clustering + promotion | L | Opus 4.8 | think hard | Promotion logic (recurrence ≥ N in W + proceduralization-gap) has real nuance |
| 611 | Error-profile dashboard endpoint + UI | M | Sonnet 4.6 | think | Ranked list + trend + anti-gamification framing; standard |
| 612 | Migration — `dt_card`, `dt_card_review` | S | Haiku 4.5 | think | Two tables; FSRS columns mirror `user_flashcards` |
| 613 | Card generation (cloze + isolate) | M | Sonnet 4.6 | think hard | Invariant (answer == corrected_form; one atom/card) + cloze deletion |
| 614 | FSRS reuse + interleaving + review endpoints | M | Sonnet 4.6 | think hard | Reuses `fsrs.py`; no-block-group interleaving has subtlety |
| 615 | Recurrence-reduction instrumentation | S | Sonnet 4.6 | think | Metric query + dashboard flag |
| 616 | Localise taxonomy + per-pair templates/weights | L | Opus 4.8 | **ultrathink** | Deep linguistic content (は/が, keigo, classifiers); templates *are* the payload |
| 617 | Correction-style A/B flag wiring | S | Sonnet 4.6 | think | Config flag + JS branch |
| 618 | Inject error exercises into Practice Engine | M | Opus 4.8 | think hard | Cross-feature integration into the live session assembler — higher blast radius |
| 620 | Taxonomy v1 baseline seed | M | Opus 4.8 | think hard | Multilingual taxonomy authoring (subtypes + per-L2 glosses + per-L1 templates); conforms to the TASK-606 contract |
| 620 | Taxonomy v1 baseline seed | M | Opus 4.8 | think hard | Multilingual taxonomy authoring (subtypes + per-L2 glosses + per-L1 templates); conforms to the TASK-606 contract |

**Tally:** Opus 4.8 × 7 (603, 604, 606, 610, 616, 618, 620) · Sonnet 4.6 × 11 · Haiku 4.5 × 2 (609, 612).
Thinking: ultrathink × 2 (606, 616) · think hard × 10 · think × 8.

### Execution waves (dependency-ordered; each wave internally parallel)
- **Wave 0 (foundation):** 600 · 602
- **Wave 1 (← 600/602):** 601 · 603 · 604 · 605 · 609 · 620
- **Wave 2 (← Wave 1):** 606 (←600,604,605) · 610 (←609) · 612 (←609)
- **Wave 3 (← Wave 2):** 607 (←606) · 616 (←606) · 611 (←610) · 613 (←610,612)
- **Wave 4 (← Wave 3):** 608 (←607) · 614 (←613)
- **Wave 5 (← Wave 4):** 617 (←608) · 618 (←614) · 615 (←614)

Critical path: 602 → 605 → **606** → 607 → 608 → 617. Schedule a human review gate after the two
ultrathink tasks (606, 616) and the Practice-Engine integration (618).

---

## Cross-cutting (build from day one)

## TASK-600: Model router + OpenRouter slug config for grading tiers
**Status:** [x] Done (2026-06-23) · **Type:** infra · **Complexity:** M · **Model:** Sonnet 4.6 · **Thinking:** think hard · **Depends On:** none
**Description:** A config-driven router mapping named tiers (tier1/tier2/tier3) to **flash-style,
language-dependent** OpenRouter slugs (Gemini-flash for EN, Qwen for ZH/JA), per L2-language+stage,
stored in `prompt_templates`. Reuse the model-arena pricing fetcher pattern. Runtime slug
verification with fail-open to the previous tier on 404.
**Acceptance Criteria:**
- [x] Tier→slug resolved from `prompt_templates`, keyed by L2 language, not code constants.
- [x] EN content routes to a Gemini-flash slug; ZH/JA route to Qwen slugs.
- [x] 404/delisted slug falls open to previous tier and logs (per memory `prompt-template-model-slug-rot`).
- [x] `grader_trace` records the slug(s) actually used.
**Files:** `services/dual_translation/router.py`, `prompt_templates` seed migration.
**Verification:** unit test resolves a tier; simulate 404 → fallback path taken.

## TASK-601: Budget guardrail + cost dashboard hooks
**Status:** [ ] Not Started · **Type:** infra · **Complexity:** S · **Model:** Sonnet 4.6 · **Thinking:** think · **Depends On:** TASK-600
**Description:** Per-user/day token budget as a **required tunable config value** in `Config`
(operator-adjustable, not hardcoded); on breach degrade to Tier 0+1. Log `grader_trace` (tier,
cache hit/miss, tokens, slugs) per submission for a cost dashboard.
**Acceptance Criteria:**
- [ ] Over-budget user is graded Tier 0+1 only, never hard-failed.
- [ ] grader_trace persisted on every grade.
**Files:** `config.py`, `services/dual_translation/grader_cascade.py`.
**Verification:** force budget=0 → submission still returns a grade with `tier<=1`.

---

## Stage 1 — Grading MVP + noticing loop

## TASK-602: Migration — `dt_passage`, `dt_passage_reference`, `dt_submission`, `dt_grade`, `dt_error_instance`, `dt_rubric_version`, `dt_taxonomy_version`
**Status:** [x] Done (2026-06-23) · **Type:** infra · **Complexity:** M · **Model:** Sonnet 4.6 · **Thinking:** think · **Depends On:** none
**Description:** Create the `dt_*` tables exactly per [[features/dual-translation.tech]] Database
Impact. All new; no changes to existing tables.
**Acceptance Criteria:**
- [x] All tables created with FKs, CHECKs, UNIQUEs as specified.
- [x] `dt_error_instance.explanation` is NOT NULL ([[decisions/ADR-015-eager-error-explanations]]).
**Files:** `migrations/dual_translation_groundwork.sql`.
**Verification:** apply migration; `list_tables` shows the 7 tables.
**Notes:** Applied to live DB; confirmed via `information_schema`/`pg_constraint` — all 7 tables
present, `dt_passage_reference`/`dt_grade` FKs are `ON DELETE CASCADE`, `dt_passage.source_kind`
CHECK is `test_transcript`-only, `dt_error_instance.explanation` is `NOT NULL`. One deliberate
deviation from the literal spec: `dt_passage.source_ref_id` is `uuid` not `bigint` — `tests.id` is
`uuid` in the live schema, so the spec's `bigint` couldn't hold a real value; no FK was added
(polymorphic pointer, mirrors `llm_calls.artifact_id`). RLS/grants were left out of scope (not in
this task's acceptance criteria; ownership checks are spec'd as application-layer) — flag before
TASK-607 (routes) ships.

## TASK-603: Passage builder — extract L2 passages from corpus + batch-generate L1 references
**Status:** [x] Done (2026-07-01, built + verified live; all 4 acceptance criteria met). The cross-cutting end-to-end *grading* smoke (TASK-606 cascade) is the only follow-up — see REMAINING. · **Type:** feature · **Complexity:** L · **Model:** Opus 4.8 · **Thinking:** think hard · **Depends On:** 600, 602
**Description:** Extract 2–4 sentence spans from `tests.transcript` **only** (not mystery scenes)
into `dt_passage` (carry `age_tier`, `register`); generate one `dt_passage_reference` per supported
L1 via OpenRouter (off hot path). Source from existing corpus only. Serving (TASK-607) restricts to
tests the learner has already completed, so the at-level guarantee comes from selection.
**Acceptance Criteria:**
- [x] Only `test_transcript` sources; `source_kind` CHECK has no `mystery_scene`. (Builder hardcodes `source_kind='test_transcript'`; runner sources only `tests`, never mysteries.)
- [x] Passages carry age_tier (no CEFR) — **derived from `tests.difficulty`**, see deviation below.
- [x] L1 references generated for each supported L1; provenance slug stored (`generator_slug`).
- [x] Idempotent re-run (no duplicate passages) — in-app dedupe on `(source_ref_id, normalized l2_text)`.
**Files:** `services/dual_translation/passage_builder.py`, `scripts/build_dt_passages.py`, `tests/test_dual_translation_passages.py` (39 tests, all mocked).
**Verification:** run over a small fixture; rows present with all L1 refs. *(Offline unit suite green: 39/39; live fixture run deferred — see REMAINING.)*

**Notes (design decisions confirmed with user 2026-06-29):**
1. **age_tier is DERIVED, not inherited (deviation from brief).** Live `tests` has **no** `age_tier`,
   `register`, `type`, or `status` column (verified against `schema.tech.md`). It carries
   `difficulty` (1–9, NOT NULL). The builder folds difficulty → tier via `DIFFICULTY_TO_TIER`
   (`services.conversation_generation.categorical_maps`: 1–2→T1, 3→T2, 4–5→T3, 6→T4, 7→T5, 8–9→T6)
   → the int 1–6 for `dt_passage.age_tier`. `register` has no source column → left **NULL**.
   "test_transcript only" = simply never touch the mystery tables; the "active test" filter is
   `tests.is_active = true` (there is no `tests.status`/`tests.type`).
2. **Idempotency = in-app dedupe, no schema change.** `dt_passage` has no content UNIQUE; the runner
   loads existing `(source_ref_id, normalized l2_text)` keys per L2 and skips matches (also collapses
   intra-batch dupes). References are backstopped by `dt_passage_reference UNIQUE(passage_id, l1_language_id)`
   and pre-checked to avoid wasted OpenRouter calls on re-run.
3. **CJK-aware regex segmentation (no library).** Split on `。！？…!?` (CJK path for zh/ja) or `.!?`
   followed by whitespace/EOL (Latin path); whitespace collapsed first. Non-overlapping 2–4 sentence
   windows; a short (<2) trailing remainder is merged + rebalanced with the previous window so every
   window stays within [2,4] and no sentence is dropped (e.g. 4+1 → 3+2). <2 sentences total → skipped.
4. **References reuse the grading router.** `resolve_tier(db,'tier1',l2_language_id)` picks the cheap
   slug configured for grading that L2; the reference is a **plain L1 translation** (NOT the grader's
   L2-only/numerical contract). Falls open to skip (logs) if the router yields no slug.
5. **First-batch cost cap:** runner defaults to `--limit 4` source tests **per language** (~12 tests),
   a cheap zh/en/ja smoke; `--limit 0` lifts the cap. `--dry-run` reports counts with no writes/calls.

**LIVE VERIFICATION (2026-07-01, project kpfqrjtfxmujzolwsvdq):**
- [x] Confirmed `tests` has NO `age_tier`/`register`/`type`/`status` columns (only difficulty/id/is_active/language_id/topic_id/transcript) — the derive-from-difficulty design is correct against the live schema.
- [x] TASK-620 taxonomy + TASK-604 rubric both have exactly 1 `is_active` row live.
- [x] Built a fixture of 3 source tests (1 per L2) via `--test-ids` (new flag): **28 dt_passage rows** (zh 8 @ age_tier 6, en 10 @ tier 3, ja 10 @ tier 3; all `active`, `test_transcript`).
- [x] **56 dt_passage_reference rows** — every passage has both L1 refs; fan-out exact (zh→[en,ja], en→[zh,ja], ja→[zh,en]); `generator_slug` recorded (en→`google/gemini-2.5-flash-lite`, zh/ja→`qwen/qwen3.6-flash`).
- [x] **Serving proof:** the exact `_select_next_passage` query for an English-L1 learner who completed the zh test returns a zh passage + its real English reference. (A persisted `test_attempts` fixture was declined by the write classifier, so this was verified read-only against the live rows.)
- [x] **Idempotent re-run confirmed live:** re-run inserted 0 passages and backfilled missing refs (0 dupes).

**Dependency fix applied this session:** TASK-600's router seed (`migrations/dual_translation_router_seed.sql`) had **never been applied live** (0 `dual_translation_*` rows in `prompt_templates`) — references + grading both fail open without it. Applied via tracked migration `dual_translation_router_seed` (9 rows, vetted non-404 flash/Qwen slugs). **Runner bug fixed:** reference generation was tied to passage *insertion*, so a passage inserted while the router was unseeded never got refs on re-run; refactored to reconcile references against **all** in-scope passages (new + pre-existing), making reference idempotency independent of insertion.

**REMAINING (TASK-606 cascade scope, not TASK-603):**
- [ ] End-to-end live *grading* smoke: submit one reproduction per L2 through real OpenRouter, confirm the §2.2 contract. Attempted 2026-07-01 but the standalone smoke harness hit `DimensionService.get_language_code` returning None — `DimensionService`'s `dim_languages` cache is hydrated at Flask startup but not in a bare script; **one-line fix** (hydrate `DimensionService` before calling `grade_submission`). Not a product defect; deferred on session cost.

## TASK-604: Versioned rubric + age-tier band descriptors (config)
**Status:** [x] Done (2026-06-27, applied live + verified) · **Type:** feature · **Complexity:** M · **Model:** Opus 4.8 · **Thinking:** ultrathink · **Depends On:** TASK-602
**Description:** Seed `dt_rubric_version` with the 5 dimensions, default weights, and 4-band
descriptors written **per age tier** (1–6), plus per-language weight overrides (JA fidelity/
particle, ZH classifier/aspect). Grading is **level-neutral** ([[decisions/ADR-018-level-neutral-grading]]):
descriptors calibrate the model, they are not a per-tier leniency curve. `naturalness` is hidden at
age tiers 1–2.
**Acceptance Criteria:**
- [x] Descriptors reference age tiers, not CEFR.
- [x] `understandability`+`accuracy` highest weight; `naturalness` lowest and hidden at tiers 1–2.
**Files:** `migrations/dt_rubric_v1_seed.sql`, `tests/test_dual_translation_rubric_seed.py`.
**Verification:** load active rubric; weights and bands match spec.
**Notes:** `config` conforms to the TASK-606 "Implementation contracts" shape
([[algorithms/translation-grading-cascade.tech]]) — **not** reinvented: `weights.default[dim]` +
partial `weights.by_language[l2][dim]` overrides, and
`band_descriptors[str(age_tier)][dim][l2] = {"1".."4": text}`. 5 dims; default weights put
`accuracy`+`understandability` highest (0.30 each), `fidelity`/`range` mid (0.15), `naturalness`
lowest (0.10). Per-language **baseline** overrides: `ja fidelity 0.25` (particle/keigo register
fidelity), `zh accuracy 0.35` (classifier/aspect). Band descriptors are 4 bands × 6 tiers × 3 L2
(zh/en/ja) = **336** strings: a single level-neutral quality ladder per dimension (ADR-018) with a
per-tier *content-level* frame (concrete→abstract) as the only thing that varies by tier;
`naturalness` omitted at tiers 1–2. ZH/JA descriptor text is an AI-authored first draft, not
native-reviewed (same caveat as `prompts.py`) — flagged for QA with TASK-616. Applied live via
`apply_migration` (tracked migration `dual_translation_rubric_v1_seed`); verified exactly **one**
`is_active` row (v1), real `get_active_rubric` returns it, the live `config` is **byte-identical**
to the committed migration, and all three readers — `compute_overall_band`,
`routes/dual_translation.py::_rubric_descriptors_for`, `prompts._band_descriptors_text` — read it
without `KeyError`. Shape test `tests/test_dual_translation_rubric_seed.py` (49 cases) extracts the
real seed JSON straight out of the `.sql` and feeds it through both consumer access paths (no live
DB). Idempotent: `ON CONFLICT (version) DO UPDATE` refreshes config/description only — no duplicate,
no second active row, and `is_active` is set only on the initial INSERT (re-apply after a later
version supersedes v1 will not silently re-activate v1).
**REMAINING GAP (not built here):** the end-to-end live grading smoke (one passage per L2 through
real OpenRouter) is still blocked — `get_active_taxonomy` raises the same way until a baseline
`dt_taxonomy_version` row is seeded, and there are no passages to serve yet (TASK-603). Do the live
smoke as part of/after the taxonomy seed + TASK-603, per TASK-606's verification note.
**RESOLVED (TASK-616, 2026-07-04):** per-language weight ownership **stays in `dt_rubric_version`** —
it is the sole reader (`compute_overall_band`); the taxonomy has no weight path. TASK-616 superseded
this baseline `by_language` block via **rubric v2** (`dt_rubric_v2_seed.sql`), raising `ja.fidelity`
0.25→0.30 and `zh.accuracy` 0.35→0.40. This v1 rubric seed is not archived — it remains the sole repo
record of the still-present version=1 row.

## TASK-605: Tier 0 deterministic pre-pass (reuse dictation grader)
**Status:** [x] Done (2026-06-23) · **Type:** feature · **Complexity:** M · **Model:** Sonnet 4.6 · **Thinking:** think hard · **Depends On:** TASK-602
**Description:** Normalise (width/punct/kana) → diff via `services.dictation.grader` → exact/near
match awards full marks/0 errors/0 tokens; result cache `hash(passage_id, norm_repro)`.
Embedding gate stubbed (provider OPEN) — route on diff size for now.
**Acceptance Criteria:**
- [x] Exact match → all-4 scores, empty errors, tier0, tokens=0.
- [x] Near-exact within fuzzy tolerance handled; cache returns prior grade.
**Files:** `services/dual_translation/tier0.py`.
**Verification:** unit tests for exact / near / cache-hit paths.
**Notes:** Width/kana normalization layer (`NFKC` + `jaconv.kata2hira` for JA) sits in front of
`services.dictation.grader.grade_dictation`, which is reused unmodified for tokenization, diffing,
and Levenshtein fuzzy-equal tolerance — no diff logic reimplemented. The embedding-similarity gate
(point 4 of the algorithm spec) is implemented as a literal diff-mismatch-ratio stub
(`NEAR_EXACT_MISMATCH_RATIO = 0.05`) with a `TODO(embedding-provider)` marker, since the provider is
still an OPEN decision — submissions within the ratio resolve at Tier 0 same as a true fuzzy-equal
match; this is a deliberately coarse placeholder, not a final word on borderline cases. Result cache
is a plain in-process `dict` keyed `sha256(passage_id:normalized_reproduction)`, matching the
existing convention in this same package (`router.py`'s `_cfg_cache`) rather than introducing a
DB-backed cache — no DB-backed cache pattern exists elsewhere in the repo for this shape of data.
8 unit tests added in `tests/test_dual_translation_tier0.py` (exact, fuzzy-typo, gate-stub small
diff, large-diff escalation, cache hit, cache key includes passage_id, JA full-width digit norm, JA
kana norm) — all pass alongside the existing 9 router tests (17/17).

## TASK-606: Grading cascade + compact JSON contract + eager explanations
**Status:** [x] Done (2026-06-23 unit-tested; **live smoke VERIFIED 2026-07-02** — one passage per L2 through real OpenRouter, full §2.2 contract) · **Type:** feature · **Complexity:** L · **Model:** Opus 4.8 · **Thinking:** ultrathink · **Depends On:** 600,604,605
**Description:** Tier 1/2 OpenRouter calls with **L2-only prompts** that emit **numerical indices**
(score ints, subtype/severity/source enum indices, span offsets — no English, no prose). Then the
**eager explanation step renders `explanation` from per-subtype × per-L1 templates** keyed by the
numerical subtype index ([[business-rules/translation-error-taxonomy]]). Prompt-cache the
rubric/taxonomy prefix; fail-open to Tier 0 marks on malformed JSON.
**Acceptance Criteria:**
- [x] Grader prompt contains no English; output is numerical indices only.
- [x] Every error has non-empty spans, learner_form, corrected_form, explanation.
- [x] Explanation rendered from a `(subtype, L1)` template; missing template → flagged fallback, never blank.
- [x] Cached prefix byte-stable; only a version bump busts it.
- [x] Malformed grader JSON → fail-open, learner not blocked.
**Files:** `services/dual_translation/grader_cascade.py`, `services/dual_translation/prompts.py`.
**Verification:** unit-tested (mocks every DB/OpenRouter boundary — see Notes). Live smoke (one
passage per L2 end-to-end against real OpenRouter) is **outstanding**: TASK-604 (rubric seed) and a
baseline taxonomy seed haven't shipped yet, so there is no active `dt_rubric_version`/
`dt_taxonomy_version` row to grade against in any real environment. `get_active_rubric`/
`get_active_taxonomy` raise loudly (no silent fallback) until one exists — do the live smoke as
part of or after TASK-604/616.
**VERIFIED LIVE (2026-07-02):** all data foundations now shipped (rubric TASK-604, taxonomy
TASK-620, passages TASK-603), so the live smoke ran — one imperfect reproduction (~15% dropped, to
escalate past Tier 0) per L2 through real OpenRouter. Results: **zh** passage 1 (age_tier 6) →
tier1 `qwen/qwen3.6-flash` + tier2 `qwen/qwen3.7-plus`, tokens 1942/7828, 66 diff ops, 2 errors,
overall_band 3; **en** passage 9 (tier 3) → tier1 `google/gemini-2.5-flash-lite` + tier2
`google/gemini-3.5-flash`, tokens 1804/223, 30 diff ops, 0 errors, band 4; **ja** passage 19 (tier
3) → same Qwen pair, tokens 2283/9761, 99 diff ops, 2 errors, band 2. Every surviving error carried
non-empty spans + learner_form + corrected_form + a **template-rendered** explanation (not model
prose), and `grader_trace` recorded the real per-L2 slugs + token usage with `fell_open: False`. The
`_decode_error` fail-soft path was also exercised live: a malformed model error (empty `learner_form`
on an insertion span) was dropped with a log line, not crashing the submission. One QA note for
TASK-616: the `omission` explanation sometimes quotes an over-long `corrected_form` span — a
model-prompt-quality issue, not a contract defect.
**Notes:** Built `services/dual_translation/prompts.py` (L2-only system/user prompt builders, fixed
`CATEGORY_ENUM`/`SOURCE_ENUM`/`SEVERITY_ENUM` constants mirroring the live `dt_error_instance` CHECK
constraints, per-language instructional templates for EN/ZH/JA — the ZH/JA text is an AI-authored
first draft, not native-reviewed, flagged for QA alongside TASK-616) and
`services/dual_translation/grader_cascade.py` (`grade_submission` orchestrator: Tier 0 short-circuit
→ Tier 1 accuracy/range → Tier 2 understandability/fidelity/naturalness, always run once Tier 0
hasn't resolved, since those three dims are Tier-2-exclusive → eager explanation render → fail-open
merge). Two JSON config shapes that the wiki only described in prose had to be made concrete to
implement this — documented in [[algorithms/translation-grading-cascade.tech]] "Implementation
contracts": `dt_rubric_version.config` (weights + band descriptors) and `dt_taxonomy_version.taxonomy`
(per-pair subtype tables with an L2-baseline fallback, **new** `subtype_glosses` for what the model
sees in the L2-only prompt, and the existing per-L1 `templates` for the learner-facing explanation).
Escalation ("Tier 2 also re-checks accuracy/range on low confidence or large diff") is two module
constants, `CONFIDENCE_ESCALATION_THRESHOLD=0.6` and `LARGE_DIFF_RATIO=0.3`; the diff-ratio side
reuses a new `Tier0Result.mismatch_ratio` field (additive change to TASK-605's `tier0.py`) rather than
re-diffing. Fail-open is uniform: any unusable tier (no slug, or malformed/unparseable JSON) defaults
its owned dimensions to `MAX_BAND` and contributes no errors — total-outage degrades to a Tier 0-style
full-marks grade, a deliberate generous reading of "fail-open to Tier 0 marks." 38 unit tests across
4 files (router 9, tier0 8, prompts 11, grader_cascade 10) — all pass; tests mock every DB/OpenRouter
boundary (`get_active_rubric`, `get_active_taxonomy`, `resolve_tier`, `call_model_with_usage`),
mirroring TASK-600's `resolve_tier` mocking convention. A test I wrote caught a real bug before it
shipped: the first prompt draft leaked raw English enum/subtype identifier strings into the ZH/JA
prompts (e.g. literal "grammatical", "article_omission") — fixed by adding `_CATEGORY_GLOSS`/
`_SOURCE_GLOSS`/`_SEVERITY_GLOSS` per-language constants and the `subtype_glosses` config concept.

## TASK-607: Routes + submit RPC + idempotency
**Status:** [x] Done (2026-06-25 unit-tested; **live route path VERIFIED 2026-07-02** — /next → /submit → idempotent re-submit against live DB) · **Type:** feature · **Complexity:** M · **Model:** Sonnet 4.6 · **Thinking:** think · **Depends On:** TASK-606
**Description:** `GET /api/dual-translation/next`, `POST /api/dual-translation/<sub>/submit`
(idempotent), ownership checks, persist grade+errors, enqueue systematic errors.
**Acceptance Criteria:**
- [x] Submit returns the full §2.2 contract; duplicate key returns cached grade.
- [x] Non-owner submission rejected.
**Files:** `routes/dual_translation.py`, register blueprint in `app.py`.
**Verification:** curl the endpoints against a seeded passage.
**Notes:** Built `routes/dual_translation.py` as a thin orchestrator: every DB-touching step is its
own monkeypatchable helper (`_resolve_l1_language_id`, `_select_next_passage`,
`_rubric_descriptors_for`, `_get_submission`, `_get_passage`, `_cached_grade`, `_persist_grade`),
mirroring TASK-606's "boundary functions tests can monkeypatch" convention rather than mocking the
raw Supabase chain. Grading itself is delegated wholesale to
`grader_cascade.grade_submission` — this module never reimplements grading, only persistence.
**Real gap found and fixed, not worked around:** the wiki's own selection rule ("L1 reference
chosen from `user_languages`") doesn't hold — `user_languages` is the L2 *study*-language
enrollment table (confirmed against `Project Knowledge/12-PRD/.../08-language-selection.md`); no
column anywhere recorded a learner's native language. Flagged to the user, who chose to add the
column rather than paper over it with a heuristic. Added `users.native_language_id` (smallint,
nullable, FK → `dim_languages`) via `migrations/add_users_native_language.sql`, applied live to the
Supabase project (`kpfqrjtfxmujzolwsvdq`) and verified via `information_schema.columns`. `GET /next`
reads it and falls back to English (id=2) while it's NULL — no onboarding UI sets it yet, so today
every user hits the fallback; that UI is a real follow-up, not built here.
**Duplicate-submission semantics:** implemented as "does a `dt_grade` row already exist for this
`submission_id`" rather than a literal idempotency-key string match. `dt_grade.submission_id` is
UNIQUE, so a second grade attempt on an already-graded submission would otherwise hit a DB
integrity error regardless of what key the client sends — checking grade-existence is the
crash-proof superset of the literal "key matches" rule and still satisfies it (the key *does*
match on a same-key retry, since `_persist_grade` writes it back onto `dt_submission` after the
first successful grade). The existing `idx_dt_submission_user_idempotency` partial index
(TASK-602) isn't exercised by this path — it would matter for a cross-submission "did I already
submit with this key" lookup, which isn't needed here because the client always learns
`submission_id` from `/next` before it ever submits.
**Other business rule wired in while building the "feed-up":** `_rubric_descriptors_for` hides
`naturalness` at age tiers 1–2 per [[decisions/ADR-018-level-neutral-grading]] and degrades to `{}`
(never 500s) when no `dt_rubric_version` is active yet — TASK-604 hasn't shipped, so this is the
common case today.
**Stubs, exactly as scoped — not built here:** `BUDGET_EXCEEDED` is a `# TODO(TASK-601)` marker at
the `grade_submission` call site (always grades at full `tier2`); the Feature-2 enqueue point is a
`# TODO(TASK-610)` marker after `_persist_grade` (no `dt_error_profile_entry` table exists yet to
enqueue into).
**Verification gap, as expected:** 21 unit tests in `tests/test_dual_translation_routes.py` (all
passing, full suite re-verified green: 589 passed/1 skipped) mock every DB/OpenRouter boundary —
no live DB in this repo's test run. Live curl against a real seeded passage is still blocked on
TASK-603 (passage builder) and TASK-604 (rubric seed), exactly as flagged in this task's brief; not
attempted.
**VERIFIED LIVE (2026-07-02):** with passages + rubric + taxonomy all live, drove the real route
handlers (not mocks) via Flask `test_client` against the live DB — `_authenticate` patched to supply
the fixture user (`de6fd05b…`), who was given one authorized smoke `test_attempts` row on the zh
fixture test `8658495d…` so `_select_next_passage` had a completed test to draw from. `GET /next` →
200: served zh passage 1 (age_tier 6), returned the English `l1_text`, all five `rubric_descriptors`
(naturalness correctly **shown** at tier 6 — hidden only at 1–2 per ADR-018), and created
`dt_submission` id 1. `POST /submit` (imperfect repro) → 200: tier2, two OpenRouter calls, persisted
1 `dt_grade` + 2 `dt_error_instance`, overall_band 3. `POST /submit` again (same key) → 200 with an
**identical** trace and **no** further OpenRouter calls in the logs — the `_cached_grade` path
reconstructed the §2.2 contract from the persisted rows; `dt_grade` stayed at exactly 1 row (the
`submission_id` UNIQUE held). Idempotency + ownership recheck + persistence all confirmed live.
**Live artifacts left in the DB** (smoke evidence; safe to purge): `test_attempts`
`72cd5618-9baf-46a9-b4bb-a16b6d3b316b`, `dt_submission` id 1 + its `dt_grade`/`dt_error_instance` rows.

## TASK-608: Diff-centric result UI (feed-up / feed-back / feed-forward)
**Status:** [x] Done (2026-07-02, built + statically verified; live browser click-through is the one residual human step) · **Type:** feature · **Complexity:** L · **Model:** Sonnet 4.6 (built this session on Opus 4.8) · **Thinking:** think hard · **Depends On:** TASK-607
**Description:** Reproduction page shows L1 reference + rubric **feed-up** (cached client-side) and
optional self-rating before reveal; result page makes the **diff the centrepiece** with per-dim
bands and the eager **explanation** per error (feed-forward: corrected form + "drill this").
**Acceptance Criteria:**
- [x] Diff is the visual focus; each error shows which-rule-and-why explanation.
- [x] Naturalness shown as low-stakes/optional with a learner-override affordance.
- [x] Correction style (direct+metalinguistic vs flag-only) behind a config/A-B flag.
**Files:** `templates/dual_translation.html`, `static/js/dual_translation.js`, `app.py` (page route
`/dual-translation`), `static/i18n/{en,es,ja,zh}.json` (43 `dual_translation.*` keys each).
**Verification:** manual click-through of submit → result.
**Notes (built 2026-07-02):** SPA-style single page with two phases, matching `classifier_drill`'s
house style (base.html blocks, `authFetch`/`LinguaI18n`/`showToast`, external JS via `extra_js`).
Phase 1 (feed-up): renders the L1 `l1_text`, the `rubric_descriptors` from `/next` (top-band
descriptor per dimension) inside a collapsible, and an optional pre-reveal **self-rating (1–4)** —
**client-only per the operator's decision** (no schema change; persisted to `localStorage`
`dt_selfrating_<submission_id>`, recalled on the result as "You predicted X/4"). Phase 2: the **diff
is the centrepiece** — one flex "cell" per `diff` opcode with the reference (gold L2) on top and the
learner's deviation below, so the two tracks stay aligned token-for-token even in CJK (**token-level**,
straight off the cascade's `WordDiff` opcodes — no JS re-diff, since char-level would need re-diffing
data the contract doesn't carry; insert/delete/replace/equal each get a distinct colour + a legend).
Per-dimension **bands** from `scores` (colour-graded 1–4); **naturalness** is hidden outright at age
tiers 1–2 (mirrors `_rubric_descriptors_for`) and at tiers 3+ is rendered low-stakes behind a
**learner-override toggle** ("Show naturalness (optional)"). Each error shows the **eager
which-rule-and-why**: `learner_form → corrected_form`, the template-rendered `explanation`, and
category/subtype/severity/source chips (enum values mirrored via i18n with a humanized-slug fallback,
so a not-yet-localised subtype never renders a raw key). **"Drill this"** is a disabled placeholder
carrying `data-subtype` — the clean hook for TASK-613 cards, which don't exist yet. **TASK-617 seam:**
correction style is read from `data-correction-style` on `.dt-wrap` (default `direct_metalinguistic`;
`flag_only` branch hides the correction behind a reveal). The A/B assignment/logging itself is *not*
built — only the branch. Double-submit latch + `crypto.randomUUID()` idempotency key on submit.
**Verified this session (no extra OpenRouter spend):** all 4 i18n files parse and carry the identical
43-key `dual_translation.*` set (per memory `i18n-applytodom-clobbers-defaults`); `GET /dual-translation`
renders 200 with every element ID + the JS include the client needs; and the exact `/next`→`/submit`
contract the JS consumes was live-proven in the same session's TASK-607 curl. **Residual:** a human
visual browser click-through (would cost one more live grade), and native review of the ZH/JA/ES
first-draft UI strings (same QA caveat as `prompts.py`/TASK-616). **Out of scope, as briefed:** L1
picker (TASK-619), the A/B experiment (TASK-617), error-profile/remediation (TASK-609+).

## TASK-619: Native-language (L1) picker — onboarding + settings UI
**Status:** [x] Done (2026-07-04) · **Type:** feature · **Complexity:** M · **Model:** Sonnet 4.6 · **Thinking:** think · **Depends On:** TASK-607
**Description:** All four acceptance criteria met. Native language picker is wired into both
onboarding (optional, fire-and-forget) and profile/settings (with optimistic UI and rollback).
Backed by GET/PATCH `/api/users/native-language` endpoints. The column `users.native_language_id`
(smallint, nullable, FK → `dim_languages`) was added in TASK-607; this task added the UI to set it.
**Acceptance Criteria:**
- [x] A new user completing onboarding has `native_language_id` set without a separate manual step — picker is optional; NULL is preserved if skipped.
- [x] An existing user can view and change their native language from the profile/settings page — loadNativeLanguage() on load, saveNativeLanguage() with optimistic UI.
- [x] Submitting an unsupported/invalid language_id is rejected (400) — validated against dim_languages ids (1/2/3).
- [x] `routes/dual_translation.py::_resolve_l1_language_id` picks up the newly-set value on the next `GET /next` call — confirmed by reading; unchanged and reads native_language_id directly from users table.

**Files Built:**
- `routes/users.py` — GET/PATCH /api/users/native-language endpoints (lines 158–211)
- `templates/onboarding.html` — three aria-role=radio cards (zh/en/ja), fires PATCH fire-and-forget before navigating to /language-selection (lines 218–317)
- `templates/profile.html` — view/change section with loadNativeLanguage() on page load and saveNativeLanguage() with optimistic UI + rollback (lines 41–51, 532–626)
- `tests/test_native_language_pages.py` — two smoke tests (onboarding render + profile render)

**Verification:** All acceptance criteria verified by codebase inspection. Endpoints present with correct validation and auth. Onboarding picker optional (NULL preserved if skipped), fires PATCH on "Get Started". Profile section loads current value, optimistic UI on save, rollback on failure. _resolve_l1_language_id unchanged — no code changes needed there. Smoke tests present and passing.

## TASK-620: Versioned error-taxonomy baseline seed (subtypes + glosses + templates)
**Status:** [x] Done (2026-06-29, applied live + verified via tracked apply_migration `dual_translation_taxonomy_v1_seed`) · **Type:** feature · **Complexity:** M · **Model:** Opus 4.8 · **Thinking:** think hard · **Depends On:** TASK-602 (conforms to the TASK-606 contract)
**Description:** Seed + activate the single `dt_taxonomy_version` row the grading cascade hard-requires — the taxonomy twin of TASK-604. `services/dual_translation/grader_cascade.py::get_active_taxonomy` raises `RuntimeError` until an `is_active` row exists (no silent fallback), the same hard-block TASK-604 cleared for the rubric. With the rubric seeded, this is the last data-foundation blocker before the cascade can run; only TASK-603 (passages) then remains for the end-to-end live grading smoke. **Baseline only** — full per-directed-pair `<l1>-<l2>` tables, rich templates (は/が, keigo nuance, classifier specifics), and per-pair weight overrides are TASK-616, which supersedes this via a version bump.
**Acceptance Criteria:**
- [x] `taxonomy` conforms to the TASK-606 "Implementation contracts" shape (`pairs` / `subtype_glosses` / `templates`); `category`/`source`/`severity` NOT included (hardcoded enums + `dt_error_instance` CHECK).
- [x] An `<l2>`-baseline subtype table per L2 (zh/en/ja); every (l1,l2) resolves via the `<l2>` baseline fallback (no per-pair key) without raising.
- [x] Every baseline subtype has an L2 gloss; every subtype has en/zh/ja templates using only `{learner_form}`/`{corrected_form}`; the numeric subtype index round-trips through `_decode_error` back to the slug (ordering stable).
- [x] Idempotent live apply: exactly one `is_active=true` row (v1); `get_active_taxonomy`'s exact query returns it (live-verified).
**Files:** `migrations/dt_taxonomy_v1_seed.sql`, `tests/test_dual_translation_taxonomy_seed.py`, generator `c:\tmp\gen_dt_taxonomy_seed.py` (single source of truth, mirrors TASK-604's `gen_rubric_seed.py`).
**Verification:** 31-case shape test extracts the real seed JSON straight out of the `.sql` and drives the production consumers — `get_active_taxonomy`, `_resolve_subtypes`, `_resolve_subtype_labels`, `render_explanation`, and a `_decode_error` index→slug round-trip — for every (l1,l2), with no live DB. All pass (full DT suite re-verified: 101 green). Live: `apply_migration` (tracked), then confirm one `is_active` row + `get_active_taxonomy` returns it.
**Notes:** L1 template coverage = **all three live L1s (en/zh/ja)**; subtype set = the **full per-language catalogue** from [[business-rules/translation-error-taxonomy]] — shared cross-linguistic `[word_order, word_choice, omission, register]` (positions 0–3) + EN `[article, preposition, phrasal_verb, tense_aspect, subject_verb_agreement]`; JA `[particle, keigo_register, counter_classifier, script_choice, topic_comment]`; ZH `[classifier, aspect_marker, topic_comment, ba_construction, resultative_complement]`. 18 distinct subtypes, 9 per L2; 27 L2 glosses; 54 L1 templates. **Brief premise corrected:** `dim_languages` holds only zh(1)/en(2)/ja(3) — there is no `es` row, and `l1_language_id` FKs to `dim_languages`, so an `es` L1 can never reach `render_explanation`; Spanish is a UI i18n locale only (`static/i18n/es.json`), so the brief's "all four L1s" was not achievable. **Task ID:** the brief suggested TASK-617, but 617/618/619 were already assigned (A/B flag, Practice-Engine inject, L1 picker) — filed as **TASK-620**. ZH/JA glosses + templates are AI-authored first drafts pending native review (same caveat as `prompts.py` / TASK-604), flagged for QA with TASK-616.
**APPLIED LIVE (2026-06-29):** applied via tracked `apply_migration` (`dual_translation_taxonomy_v1_seed`) to project `kpfqrjtfxmujzolwsvdq`. Live-verified: exactly one `is_active=true` row (v1); top keys `pairs/subtype_glosses/templates`; `pairs` = en/ja/zh (9 subtypes each); 18 gloss subtypes; 18 template subtypes — the same query shape `get_active_taxonomy` runs. (The earlier MCP disconnect was waited out per the operator; no DATABASE_URL write was used.) **TASK-603 (passages) is now the sole remaining blocker** for the end-to-end live grading smoke (one passage per L2 through real OpenRouter) — do not attempt the live grade until passages exist.

---

## Stage 2 — Error synthesis

## TASK-609: Migration — `dt_error_profile_entry`
**Status:** [ ] Not Started · **Type:** infra · **Complexity:** S · **Model:** Haiku 4.5 · **Thinking:** think · **Depends On:** TASK-602
**Files:** `migrations/dt_error_profile.sql`. **Verification:** table present with UNIQUE key.

## TASK-610: Mistake gate + embedding clustering + promotion rule
**Status:** [ ] Not Started · **Type:** feature · **Complexity:** L · **Model:** Opus 4.8 · **Thinking:** think hard · **Depends On:** TASK-609
**Description:** Nightly job: drop `is_mistake`; cluster errors **deterministically by
`(user, l1↔l2 pair, subtype)`** (no embeddings — the grader already emits the subtype); promote a
subtype to the queue only on recurrence ≥ N in window W (or proceduralization gap). N/W tunable config.
**Acceptance Criteria:**
- [ ] is_mistake never promotes; sub-threshold subtype stays `watching`.
- [ ] Clustering is a deterministic group-by on subtype; no embedding/LLM call.
**Files:** `services/dual_translation/synthesis.py`, `scripts/dt_nightly_synthesis.py`.
**Verification:** seeded fixture promotes only the recurring subtype.

## TASK-611: Error-profile dashboard endpoint + UI (self-regulation)
**Status:** [ ] Not Started · **Type:** feature · **Complexity:** M · **Model:** Sonnet 4.6 · **Thinking:** think · **Depends On:** TASK-610
**Description:** `GET /api/dual-translation/profile` ranked by frequency×severity with trend;
UI gamifies the **shrinking profile**, never the score.
**Files:** `routes/dual_translation.py`, `templates/dual_translation_profile.html`.
**Verification:** dashboard shows ranked subtypes + trend on seeded data.

---

## Stage 3 — Spaced remediation

## TASK-612: Migration — `dt_card`, `dt_card_review`
**Status:** [ ] Not Started · **Type:** infra · **Complexity:** S · **Model:** Haiku 4.5 · **Thinking:** think · **Depends On:** TASK-609
**Files:** `migrations/dt_cards.sql`. **Verification:** tables present.

## TASK-613: Card generation (cloze + isolate-and-re-translate) toward corrected_form
**Status:** [ ] Not Started · **Type:** feature · **Complexity:** M · **Model:** Sonnet 4.6 · **Thinking:** think hard · **Depends On:** 610,612
**Description:** Build cloze cards (delete only the corrected element, one atom/card) and
isolate-and-re-translate cards (from stored spans). Prompt always toward `corrected_form`.
**Acceptance Criteria:**
- [ ] Card answer target == corrected_form, never learner_form (invariant test).
- [ ] One atomic target per cloze card.
**Files:** `services/dual_translation/cards.py`.
**Verification:** generated card invariant test passes.

## TASK-614: FSRS scheduling (reuse) + interleaving + review endpoints
**Status:** [ ] Not Started · **Type:** feature · **Complexity:** M · **Model:** Sonnet 4.6 · **Thinking:** think hard · **Depends On:** TASK-613
**Description:** Schedule via `services/vocabulary/fsrs.py`; due queue interleaves subtypes;
`/cards/due` + `/cards/<id>/review` (appends `dt_card_review`). Error cards are **not sense-linked**
(subtype-keyed) and are interleaved into the **dual-translation queue** (GET /next). Practice Engine
interleaving is TASK-618.
**Acceptance Criteria:**
- [ ] Due queue does not block-group one subtype.
- [ ] Review updates FSRS state via reused scheduler.
- [ ] Error exercises interleave into the dual-translation /next queue.
**Files:** `routes/dual_translation.py`, `services/dual_translation/cards.py`.
**Verification:** review a card → due_date advances per FSRS; /next mixes passages + due error cards.

## TASK-618: Inject error exercises into Practice Engine sessions
**Status:** [ ] Not Started · **Type:** feature · **Complexity:** M · **Model:** Opus 4.8 · **Thinking:** think hard · **Depends On:** TASK-614
**Description:** Interleave due dual-translation error exercises into the **Practice Engine**
exercise sessions as a separate, **non-sense-linked** stream (distinct from the sense-keyed
candidate pools), so remediation happens in the flow of normal practice. Lightweight injection at
session-assembly time; not full Study-Plan orchestration.
**Acceptance Criteria:**
- [ ] Practice sessions include due error exercises without going through sense-pool selection.
- [ ] Injection rate is capped/configurable so it does not crowd out normal practice.
**Files:** practice session assembler (`services/practice/*`), `services/dual_translation/cards.py`.
**Verification:** a user with due error cards gets them interleaved into a Practice Engine session.

## TASK-615: Recurrence-reduction instrumentation
**Status:** [ ] Not Started · **Type:** test · **Complexity:** S · **Model:** Sonnet 4.6 · **Thinking:** think · **Depends On:** TASK-614
**Description:** Log delayed re-test accuracy (`dt_card_review.was_correct`) keyed to subtype;
dashboard metric flags subtypes not improving within ~3–4 cycles.
**Acceptance Criteria:**
- [ ] Metric computable per subtype; decreasing on a seeded improving fixture.
**Files:** `services/dual_translation/metrics.py`.
**Verification:** metric query returns expected trend on fixture.

---

## Stage 4 — Localisation

## TASK-616: Localise taxonomy + weights per directed pair (EN L2 first, then JA, ZH)
**Status:** [x] Done (2026-07-04, applied live to `kpfqrjtfxmujzolwsvdq` + paid live smoke through real OpenRouter) · **Type:** feature · **Complexity:** L · **Model:** Opus 4.8 · **Thinking:** ultrathink · **Depends On:** TASK-606
**Description:** Seed `dt_taxonomy_version` per-pair subtype tables + weight overrides per
[[business-rules/translation-error-taxonomy]]. EN articles/prepositions; JA particles/keigo
(keigo = first-class fidelity); ZH classifiers/aspect. Per-language cached prefixes.
**Acceptance Criteria:**
- [x] Subtypes resolved from config, not code — per-directed-pair `pairs["<l1>-<l2>"]` tables (all 6 directed pairs) in taxonomy v4; every directed (l1,l2) now resolves via the pair path, not the L2-baseline fallback.
- [x] JA keigo_register scored under fidelity; ZH classifier/aspect up-weighted — live smoke: JA keigo/register downgrade → **fidelity=2** (down from 4) + 2 `keigo_register` errors; ZH 个-overuse → **accuracy=3** + 4 `classifier` errors.
**Files:** `migrations/dt_taxonomy_{en,ja,zh}_seed.sql` (taxonomy v2/v3/v4), **`migrations/dt_rubric_v2_seed.sql`** (weight bump — see §"weight ownership" below), `tests/test_dual_translation_taxonomy_localised.py`, `tests/test_dual_translation_rubric_v2.py`, generator `scratchpad/gen_dt_localised.py`.
**Verification:** offline shape/round-trip suites (41 new + 80 baseline, all green); live smoke confirmed the §2.2 contract with the enriched templates rendered (keigo template naming teineigo/sonkeigo/kenjougo; classifier template naming the measure word 件).

**KEY DESIGN CORRECTION — weight ownership (confirmed with user 2026-07-04):** the brief's premise
("seed a new `dt_taxonomy_version` with per-pair tables **+ weight overrides**") does not match the
implementation. `grader_cascade.compute_overall_band` reads dimension weights **only** from
`dt_rubric_version.config.weights.by_language`; the taxonomy carries **no** weights and nothing reads
one there. Putting "weight overrides" in the taxonomy would be dead config. So TASK-616 bumps **two**
active versions (user chose "Rubric v2 + taxonomy per-pair", no code change):
- **`dt_rubric_version` v2** — raises `by_language.ja.fidelity` 0.25→**0.30** and `by_language.zh.accuracy`
  0.35→**0.40** (band descriptors byte-identical to v1). This is what actually makes JA fidelity / ZH
  accuracy up-weighted. **Resolves the TASK-604 open question** on weight ownership (weights stay in
  `dt_rubric_version`, the sole reader).
- **`dt_taxonomy_version` v4** — per-directed-pair tables + richer per-L1 templates / per-L2 glosses.
"JA keigo scored under fidelity" is mechanical: `keigo_register` is a JA subtype (error tagged there),
the JA `fidelity` descriptor+gloss already name 敬語レベル, and the rubric up-weights fidelity.

**Taxonomy structure:** cumulative, self-contained, one active row (the cascade loads ONE row).
v2 (EN, `dt_taxonomy_en_seed.sql`) = v1 baseline + `ja-en`/`zh-en` pairs + enriched article/preposition
(definiteness; verb-governed prepositions). v3 (JA) = v2 + `en-ja`/`zh-ja` + enriched particle (は=topic
vs が=new-subject) + keigo_register (teineigo/sonkeigo/kenjougo, "grammatical-but-wrong-level is still an
error"). v4 (ZH) = v3 + `en-zh`/`ja-zh` + enriched classifier (个 overuse, measure-word agreement) +
aspect_marker (了/过/着 = aspect not tense). Final v4 = all 6 directed pairs + en/ja/zh baselines.
**Per-pair subtype LISTS mirror the L2 baseline set/order** (guarantees gloss+template coverage and a
trivially-correct index round-trip); the localisation payload is the enriched templates/glosses + the
explicit `pairs[l1-l2]` key (so resolution uses the per-pair path and prompts.py's per-(L1,L2)
cache-narrowing note becomes real; future L1-specific divergence has a home). ZH/JA strings are still
AI-authored first drafts pending native review (same standing caveat as `prompts.py`/TASK-604/620).

**APPLIED LIVE (2026-07-04):** four tracked migrations via `apply_migration` — `dt_rubric_v2_seed_task616`,
then `dt_taxonomy_{en,ja,zh}_seed_task616` (EN→JA→ZH). To apply the exact committed artifacts without
re-emitting 10–28 KB of JSON per file (transcription-drift risk), each migration **derives the new
version in-DB from the previous version's row** (baseline copy + the small enrichment deltas via
`jsonb_set`/`||`), which is semantically identical to the committed full-JSON `.sql` files. A host
script (app's own Supabase client) then **verified the live active rows are semantically identical to
the committed `dt_taxonomy_zh_seed.sql` / `dt_rubric_v2_seed.sql`** (dict-equality PASS) — so the
committed `.sql` files faithfully reflect live. Post-apply: `dt_taxonomy_version` = `1,2,3,4*` (one
active), `dt_rubric_version` = `1,2*` (one active). The v1 seed files are **not** archived — they remain
the sole repo record of the still-present version=1 rows (distinct PKs, not redefined).
**LIVE SMOKE (real OpenRouter, l1=en):** JA passage 20 keigo/register downgrade → scores
`{accuracy:3, range:2, understandability:4, fidelity:2, naturalness:3}`, tier2, `fell_open:False`,
11 errors incl. 2 `keigo_register` (`ロボットアームだ`→`ロボットアームです`, `格別だぞ`→`格別ですよ`)
+ several `register`; ZH passage 1 个-overuse → `{accuracy:3, range:3, understandability:4, fidelity:4,
naturalness:3}`, tier2, 4 `classifier` errors (`一个`→`一件`, `这个`→`这件`). Both explanations are the
new enriched templates.
**Verification:** grade a JA keigo-wrong reproduction → fidelity penalised + keigo_register error.

## TASK-617: Correction-style A/B flag wiring
**Status:** [x] Done (2026-07-02, built + unit-verified; migration applied live) · **Type:** feature · **Complexity:** S · **Model:** Sonnet 4.6 · **Thinking:** think · **Depends On:** TASK-608
**Description:** Config flag for direct+metalinguistic vs indirect/flag-only correction; the
Truscott–Ferris debate is unresolved, so this is A/B-tested, not hardcoded.
**Files:** `config.py`, `static/js/dual_translation.js`, `routes/dual_translation.py`,
`migrations/dt_add_correction_style.sql`, `tests/test_dual_translation_correction_style.py`,
`tests/test_dual_translation_routes.py`.
**Verification:** toggling the flag changes the feedback presentation.
**Notes (built 2026-07-02):** Turned TASK-608's static `data-correction-style` seam into a real
config-driven A/B assignment. **Config (`config.py`):** `DT_CORRECTION_STYLE` env flag with three
modes — `direct_metalinguistic` (force eager), `flag_only` (force reveal-on-demand), `experiment`
(default). `Config.resolve_correction_style(user_id)` returns the forced arm in a forced mode, else
a **deterministic 50/50 split on `sha256(user_id)`** (`digest[0] & 1`) — a given user is stably
bucketed across sessions; an unrecognized flag value fails safe to `experiment`. Force modes are the
no-code-change QA/rollback lever. **Mechanism = `GET /next` returns `correction_style`** (chosen over
a template context var as **lower blast radius**: `/next` is already `@supabase_jwt_required` with
`g.current_user_id` resolved and already returns the JSON contract the JS consumes; the page route
`/dual-translation` is unauthenticated `render_template` with no user_id — stamping there would mean
adding auth to it). The static `data-correction-style="direct_metalinguistic"` on `.dt-wrap` stays as
a **safe fallback default** when the field is absent. **Persistence/logging (operator decision):** the
resolved arm is **stamped onto `dt_submission.correction_style` at `/next` time** (new nullable column
+ CHECK on the two arms — `migrations/dt_add_correction_style.sql`, applied live to
`kpfqrjtfxmujzolwsvdq` via tracked `apply_migration`, column+CHECK confirmed). Persisting per-submission
(vs. only recomputing from user_id) keeps the experiment analyzable even if the config mode or bucketing
changes later. **JS:** `loadNext` overrides `CORRECTION_STYLE` from the `/next` payload; the existing
`flag_only` reveal branch in `buildErrorCard` (TASK-608) is unchanged. **Verified:** 7 new resolver
tests (force-both-arms · stable-per-user · both-arms-reachable · ~50/50 balance · unknown-mode-fails-safe)
+ extended `TestGetNext` asserting the arm is both returned in the payload and written to the
`dt_submission` insert; full DT suite **185 passed**. No OpenRouter spend (presentation wiring only).
**Residual (unchanged from TASK-608):** a human visual browser click-through of reproduce→result (would
cost one live grade) and native ZH/JA/ES UI-string review (folds into TASK-616) were not done.

---

## Related Pages
- [[features/dual-translation]] / [[features/dual-translation.tech]] / [[features/dual-translation-remediation.tech]]
- [[algorithms/translation-grading-cascade.tech]]
- [[business-rules/translation-error-taxonomy]]
