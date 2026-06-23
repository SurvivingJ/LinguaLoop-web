---
title: "Dual Translation — Task Breakdown"
feature: dual-translation
prose_page: ../features/dual-translation.md
tech_page: ../features/dual-translation.tech.md
total_tasks: 19
done: 4
last_updated: 2026-06-23
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

**Tally:** Opus 4.8 × 6 (603, 604, 606, 610, 616, 618) · Sonnet 4.6 × 11 · Haiku 4.5 × 2 (609, 612).
Thinking: ultrathink × 2 (606, 616) · think hard × 9 · think × 8.

### Execution waves (dependency-ordered; each wave internally parallel)
- **Wave 0 (foundation):** 600 · 602
- **Wave 1 (← 600/602):** 601 · 603 · 604 · 605 · 609
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
**Status:** [ ] Not Started · **Type:** feature · **Complexity:** L · **Model:** Opus 4.8 · **Thinking:** think hard · **Depends On:** 600, 602
**Description:** Extract 2–4 sentence spans from `tests.transcript` **only** (not mystery scenes)
into `dt_passage` (carry `age_tier`, `register`); generate one `dt_passage_reference` per supported
L1 via OpenRouter (off hot path). Source from existing corpus only. Serving (TASK-607) restricts to
tests the learner has already completed, so the at-level guarantee comes from selection.
**Acceptance Criteria:**
- [ ] Only `test_transcript` sources; `source_kind` CHECK has no `mystery_scene`.
- [ ] Passages carry age_tier inherited from source; no CEFR.
- [ ] L1 references generated for each supported L1; provenance slug stored.
- [ ] Idempotent re-run (no duplicate passages).
**Files:** `services/dual_translation/passage_builder.py`, `scripts/build_dt_passages.py`.
**Verification:** run over a small fixture; rows present with all L1 refs.

## TASK-604: Versioned rubric + age-tier band descriptors (config)
**Status:** [ ] Not Started · **Type:** feature · **Complexity:** M · **Model:** Opus 4.8 · **Thinking:** think hard · **Depends On:** TASK-602
**Description:** Seed `dt_rubric_version` with the 5 dimensions, default weights, and 4-band
descriptors written **per age tier** (1–6), plus per-language weight overrides (JA fidelity/
particle, ZH classifier/aspect). Grading is **level-neutral** ([[decisions/ADR-018-level-neutral-grading]]):
descriptors calibrate the model, they are not a per-tier leniency curve. `naturalness` is hidden at
age tiers 1–2.
**Acceptance Criteria:**
- [ ] Descriptors reference age tiers, not CEFR.
- [ ] `understandability`+`accuracy` highest weight; `naturalness` lowest and hidden at tiers 1–2.
**Files:** `migrations/dt_rubric_v1_seed.sql`.
**Verification:** load active rubric; weights and bands match spec.

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
**Status:** [x] Done (2026-06-23, unit-tested; live smoke still outstanding) · **Type:** feature · **Complexity:** L · **Model:** Opus 4.8 · **Thinking:** ultrathink · **Depends On:** 600,604,605
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
**Status:** [ ] Not Started · **Type:** feature · **Complexity:** M · **Model:** Sonnet 4.6 · **Thinking:** think · **Depends On:** TASK-606
**Description:** `GET /api/dual-translation/next`, `POST /api/dual-translation/<sub>/submit`
(idempotent), ownership checks, persist grade+errors, enqueue systematic errors.
**Acceptance Criteria:**
- [ ] Submit returns the full §2.2 contract; duplicate key returns cached grade.
- [ ] Non-owner submission rejected.
**Files:** `routes/dual_translation.py`, register blueprint in `app.py`.
**Verification:** curl the endpoints against a seeded passage.

## TASK-608: Diff-centric result UI (feed-up / feed-back / feed-forward)
**Status:** [ ] Not Started · **Type:** feature · **Complexity:** L · **Model:** Sonnet 4.6 · **Thinking:** think hard · **Depends On:** TASK-607
**Description:** Reproduction page shows L1 reference + rubric **feed-up** (cached client-side) and
optional self-rating before reveal; result page makes the **diff the centrepiece** with per-dim
bands and the eager **explanation** per error (feed-forward: corrected form + "drill this").
**Acceptance Criteria:**
- [ ] Diff is the visual focus; each error shows which-rule-and-why explanation.
- [ ] Naturalness shown as low-stakes/optional with a learner-override affordance.
- [ ] Correction style (direct+metalinguistic vs flag-only) behind a config/A-B flag.
**Files:** `templates/dual_translation.html`, `static/js/dual_translation.js`.
**Verification:** manual click-through of submit → result.

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
**Status:** [ ] Not Started · **Type:** feature · **Complexity:** L · **Model:** Opus 4.8 · **Thinking:** ultrathink · **Depends On:** TASK-606
**Description:** Seed `dt_taxonomy_version` per-pair subtype tables + weight overrides per
[[business-rules/translation-error-taxonomy]]. EN articles/prepositions; JA particles/keigo
(keigo = first-class fidelity); ZH classifiers/aspect. Per-language cached prefixes.
**Acceptance Criteria:**
- [ ] Subtypes resolved from config, not code.
- [ ] JA keigo_register scored under fidelity; ZH classifier/aspect up-weighted.
**Files:** `migrations/dt_taxonomy_*_seed.sql`.
**Verification:** grade a JA keigo-wrong reproduction → fidelity penalised + keigo_register error.

## TASK-617: Correction-style A/B flag wiring
**Status:** [ ] Not Started · **Type:** feature · **Complexity:** S · **Model:** Sonnet 4.6 · **Thinking:** think · **Depends On:** TASK-608
**Description:** Config flag for direct+metalinguistic vs indirect/flag-only correction; the
Truscott–Ferris debate is unresolved, so this is A/B-tested, not hardcoded.
**Files:** `config.py`, `static/js/dual_translation.js`.
**Verification:** toggling the flag changes the feedback presentation.

---

## Related Pages
- [[features/dual-translation]] / [[features/dual-translation.tech]] / [[features/dual-translation-remediation.tech]]
- [[algorithms/translation-grading-cascade.tech]]
- [[business-rules/translation-error-taxonomy]]
