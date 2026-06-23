---
title: Dual Translation — Technical Specification (Feature 1: Grading)
type: feature-tech
status: planned
prose_page: ./dual-translation.md
last_updated: 2026-06-23
dependencies:
  - "table: tests (transcript) and mysteries/mystery_scenes — L2 source for passages"
  - "table: dim_languages (1=ZH, 2=EN, 3=JA), users, user_languages"
  - "table: prompt_templates — holds OpenRouter model slugs per language/stage (model router)"
  - "service: services.dictation.grader (Levenshtein WordDiff) — reused for Tier 0"
  - "service: shared OpenRouter client (as used by services.model_arena.llm_runner)"
  - "new tables: dt_passage, dt_submission, dt_grade, dt_error_instance, dt_rubric_version, dt_taxonomy_version"
  - "new service: services.dual_translation.* (passage_builder, grader_cascade, router)"
breaking_change_risk: low
---

# Dual Translation — Technical Specification (Feature 1: Grading)

> Scope: the shared architecture + data model + the **grading** half (Feature 1 in the brief).
> Feature 2 (error synthesis + spaced remediation) is specified in
> [[features/dual-translation-remediation.tech]]. The cost cascade detail lives in
> [[algorithms/translation-grading-cascade.tech]].

## Reconciliation of [RECONCILE] markers (resolved against repo + user notes)

| Brief marker | Resolution in this repo |
|---|---|
| Model-access layer / model IDs / pricing | **OpenRouter**, **flash-style models** for cost, **language-dependent by L2 content** (Gemini-flash for EN, Qwen for ZH/JA). Slugs stored in `prompt_templates` per language+stage (same pattern as exercise-gen and model-arena). The brief's Haiku/Sonnet/Opus tiers become **named router tiers → OpenRouter slugs**, swappable without code change. See [[algorithms/translation-grading-cascade.tech]]. |
| Prompt/output language (business rule) | Grading prompts are **target-language (L2) only — no English**; the grader **outputs numerical indices** (score ints, subtype/severity/source enum indices, span offsets), never prose. Same rule as the exercise-gen pipeline. |
| Difficulty banding (CEFR descriptors) | **Age tiers** ([[decisions/ADR-003-age-tiers]]). Rubric band descriptors are written per age tier (1–6), not CEFR. |
| Lazy explanations (§4.4) | **Overridden** — explanations are eager/first-class ([[decisions/ADR-015-eager-error-explanations]]), but **rendered from versioned per-subtype × per-L1 templates keyed by the grader's numerical subtype index** (not LLM prose). This satisfies the eager-explanation priority *and* the L2-only/numerical-output rule, and is cheaper than prose. |
| Passage source / authoring (§8 Q6) | **Existing corpus** — `tests.transcript` and mystery scenes are the L2 gold; L1 reference(s) are generated per supported L1 and stored. |
| FSRS build-vs-buy (§8 Q3) | **Reuse** `services/vocabulary/fsrs.py` (FSRS-4). No new scheduler library. |
| L1↔L2 only vs bidirectional (§8 Q1) | **L1→L2 only** for MVP ([[decisions/ADR-017-dual-translation-standalone-l1l2-mvp]]). |
| Speech modality (§8 Q5) | Out of scope; `modality='text'` only. Tone/pitch subtypes gated behind a future `modality='speech'` flag. |
| Privacy/retention (§8 Q2) | **RESOLVED** — no special posture required; learner reproduction text is **retained for analysis** (an asset). |
| Budget thresholds (§4.6) | **Required tunable config** — a per-user/day token budget value lives in `Config` (not hardcoded); on breach degrade to Tier 0 + Tier 1 only, never hard-fail. |
| Source surface (§8 Q6) | **`tests.transcript` only** (not mystery scenes); passages served from the learner's **already-completed** tests so content is at-level. |
| Grading level | **Level-neutral** against the gold (difficulty controlled at selection); only `naturalness` is level-dependent. [[decisions/ADR-018-level-neutral-grading]]. |

## Architecture Overview

```
Browser                         Flask                              Postgres / OpenRouter
────────                        ─────                              ─────────────────────
GET /dual-translation/<id>  ──► render reproduction page
                                 (shows L1 reference + rubric "feed-up")
                                 L1 ref selected for user's L1 (user_languages)

[learner types L2 reproduction + submits]

POST /api/dual-translation/      submit_reproduction()
     <submission>/submit          │
{reproduction, idempotency_key}   ▼
                            Tier 0  normalize (width/punct/kana) +
                                    grader.diff(reproduction, gold_L2)   ◄── services.dictation.grader
                                    + embedding-similarity gate
                                    + result cache: hash(passage_id, norm_repro)
                                     │
                            exact/near-exact ── full marks, 0 errors, NO model call
                                     │ else
                                     ▼
                            Cascade  Tier 1 (cheap slug): accuracy/range error tagging
                                    Tier 2 (mid slug): understandability/fidelity/naturalness
                                    (escalate only on low confidence / large diff)
                                     │  cached rubric+taxonomy prefix (OpenRouter prompt cache)
                                     ▼
                            Eager explanation pass: for EVERY error_instance,
                            generate "which rule + why" in the learner's L1
                                     │
                                     ▼
                            persist dt_grade + dt_error_instance[]  ──► INSERT rows
                                     │
                            ◄──  { scores{5 dims}, overall_band, diff[],
                                   errors[ {spans, learner_form, corrected_form,
                                            category, subtype, source, severity,
                                            explanation, confidence} ],
                                   grader_trace }
[client renders diff-centric result + per-dim bands + explanations]
```

## Database Impact (new tables — migration required)

All new, prefix `dt_`. No changes to existing tables. Mirror existing conventions
(`bigint identity` PKs, `language_id → dim_languages`, `created_at timestamptz default now()`).

> **Reconciled against the live migration** (`migrations/dual_translation_groundwork.sql`,
> TASK-602, applied + verified 2026-06-23). Three corrections to the original draft below:
> 1. `language_id` FK columns (`l2_language_id`, `l1_language_id`) are `integer`, not `bigint` —
>    matches the repo-wide convention for every other table that references `dim_languages.id`
>    (which is itself `smallint`; Postgres permits FKs across `int2`/`int4`/`int8`).
> 2. `dt_passage.source_ref_id` is `uuid`, not `bigint` — `tests.id` is `uuid` in the live schema,
>    so `bigint` could never have held a real value. **No FK** was added to `tests(id)`: this is a
>    polymorphic source pointer (mirrors `llm_calls.artifact_id`) — `source_kind` is locked to
>    `test_transcript` today via CHECK, but the column is designed to support other source kinds
>    later without a type change.
> 3. `dt_error_instance.confidence` is `real`, not bare `float` — matches the repo convention for
>    confidence-like columns (e.g. `llm_calls.judge_confidence`); Postgres bare `float` defaults to
>    `double precision`, which this repo doesn't otherwise use for this kind of column.
>
> Enumerated `notes` columns below (`CHECK:` prefix) are real CHECK constraints in the live table,
> not just documentation — added during implementation for every pipe-delimited enum and bounded
> range the original draft only described in prose.

### `dt_passage`
The L2 gold + L1 reference(s), sourced from existing corpus.
| column | type | notes |
|---|---|---|
| `id` | bigint PK | |
| `l2_language_id` | integer NOT NULL | FK → dim_languages (the studied language) |
| `source_kind` | text NOT NULL | CHECK: `test_transcript` (mystery scenes excluded per 2026-06-23 notes) |
| `source_ref_id` | uuid NOT NULL | id of the originating `tests` row (the transcript source); no FK — polymorphic pointer, see reconciliation note above |
| `l2_text` | text NOT NULL | the gold reference (2–4 sentences, extracted span of source) |
| `age_tier` | smallint NOT NULL | CHECK: BETWEEN 1 AND 6 ([[decisions/ADR-003-age-tiers]]); inherited from source |
| `register` | text | politeness/register metadata (esp. JA keigo level) |
| `status` | text NOT NULL DEFAULT 'active' | CHECK: `active` \| `draft` \| `retired` |
| `created_at` | timestamptz | |

### `dt_passage_reference`
One L1 reference per supported L1 (per-user-L1 design).
| column | type | notes |
|---|---|---|
| `id` | bigint PK | |
| `passage_id` | bigint NOT NULL | FK → dt_passage ON DELETE CASCADE |
| `l1_language_id` | integer NOT NULL | FK → dim_languages (the native language shown to learner) |
| `l1_text` | text NOT NULL | generated reference translation |
| `generator_slug` | text | OpenRouter slug used to generate it (provenance) |
| `created_at` | timestamptz | added for consistency with every other `dt_*` table (not in the original draft) |
| | | UNIQUE (passage_id, l1_language_id) |

### `dt_submission`
| column | type | notes |
|---|---|---|
| `id` | bigint PK | |
| `user_id` | uuid NOT NULL | FK → users |
| `passage_id` | bigint NOT NULL | FK → dt_passage |
| `l1_language_id` | integer NOT NULL | which reference the learner translated from |
| `reproduction` | text NOT NULL | learner's L2 attempt |
| `modality` | text NOT NULL DEFAULT 'text' | CHECK: `text` only for MVP |
| `idempotency_key` | text | dedup double-submit (see double-submit latch precedent) |
| `created_at` | timestamptz | |

### `dt_grade`  (the §2.2 contract, persisted)
| column | type | notes |
|---|---|---|
| `id` | bigint PK | |
| `submission_id` | bigint NOT NULL UNIQUE | FK → dt_submission ON DELETE CASCADE |
| `scores` | jsonb NOT NULL | `{accuracy,understandability,fidelity,range,naturalness}` each 1–4 |
| `overall_band` | smallint NOT NULL | CHECK: BETWEEN 1 AND 4 — weighted (see weights below) |
| `diff` | jsonb NOT NULL | token opcode array (equal/replace/insert/delete), capped ~200 |
| `grader_trace` | jsonb NOT NULL | `{tier, deterministic_prefilter, cache_hit, tokens{in,out}, slugs[]}` |
| `created_at` | timestamptz | |

### `dt_error_instance`
| column | type | notes |
|---|---|---|
| `id` | bigint PK | |
| `submission_id` | bigint NOT NULL | FK → dt_submission |
| `span_reproduction` | jsonb `[start,end]` | mandatory — drives diff UI + isolate-and-repeat |
| `span_reference` | jsonb `[start,end]` | mandatory |
| `category` | text NOT NULL | CHECK: `grammatical` \| `lexical` \| `pragmatic_expressional` |
| `subtype` | text NOT NULL | language-pair taxonomy key (see business-rule page); no CHECK — open-ended, versioned in `dt_taxonomy_version` |
| `source` | text NOT NULL | CHECK: `interlingual` \| `intralingual` |
| `severity` | text NOT NULL | CHECK: `global` \| `local` |
| `learner_form` | text NOT NULL | the wrong form (stored, never used as a card prompt) |
| `corrected_form` | text NOT NULL | feeds flashcards directly |
| `explanation` | text NOT NULL | eager: *which rule and why*, written in learner's L1 |
| `confidence` | real NOT NULL | drives escalation + hedge vs assertive display |
| `is_mistake` | boolean DEFAULT false | self-corrected/one-off slip — logged, not drilled |
| `created_at` | timestamptz | |

### `dt_rubric_version`
Versioned rubric config (JSONB): dimensions, default + per-language weights, band descriptors per
age tier. Never hardcoded in app code.
| column | type | notes |
|---|---|---|
| `id` | bigint PK | |
| `version` | integer NOT NULL UNIQUE | sequential version number |
| `is_active` | boolean NOT NULL DEFAULT false | exactly one row may be active — enforced by a partial unique index `(is_active) WHERE is_active` |
| `config` | jsonb NOT NULL | the 5 dimensions, default + per-language weights, band descriptors per age tier (1–6) |
| `description` | text | human-readable changelog note for the version |
| `created_at` | timestamptz | |

### `dt_taxonomy_version`
Versioned taxonomy config (JSONB): the cross-linguistic schema + per-pair subtype tables. Never
hardcoded in app code.
| column | type | notes |
|---|---|---|
| `id` | bigint PK | |
| `version` | integer NOT NULL UNIQUE | sequential version number |
| `is_active` | boolean NOT NULL DEFAULT false | exactly one row may be active — enforced by a partial unique index `(is_active) WHERE is_active` |
| `taxonomy` | jsonb NOT NULL | shared cross-linguistic schema (category/source/severity) + per-directed-pair subtype tables + per-subtype × per-L1 explanation templates ([[business-rules/translation-error-taxonomy]]) |
| `description` | text | human-readable changelog note for the version |
| `created_at` | timestamptz | |

The active row's `id` in each table is referenced by `dt_grade.grader_trace`, so re-scores are
reproducible; a config edit must bump `version` (prompt-cache prefix stability).

## Rubric (Feature 1)

Five analytic dimensions, 4-band scale, descriptors written **per age tier**:

| key | dimension | default weight | primary grader tier |
|---|---|---|---|
| `accuracy` | grammatical correctness | **high** | Tier 0 + Tier 1 |
| `understandability` | would a native grasp the meaning | **high** | Tier 2 |
| `fidelity` | meaning + register preserved (JA: keigo is first-class here) | medium | Tier 2 |
| `range` | articulateness / sophistication | medium | Tier 1→2 |
| `naturalness` | how native it sounds | **low, overridable** | Tier 2 (lazy/skippable) |

`overall_band` = weighted mean (config in `dt_rubric_version`). Per-language overrides: JA raises
`fidelity` (keigo register); ZH raises `accuracy` weight for classifier/aspect subtypes.

**Grading is level-neutral** ([[decisions/ADR-018-level-neutral-grading]]): bands are scored
against the gold at face value because difficulty is controlled at *selection* (at-level
completed tests). The only level-dependent behaviour is `naturalness` — de-emphasized at all
tiers and **hidden at the lowest age tiers** (1–2) to avoid demotivation.

## API / RPC Surface

### `POST /api/dual-translation/<submission>/submit`
- **Purpose:** grade a reproduction against its passage gold.
- **Arguments:** `reproduction` (str, required), `idempotency_key` (str). Passage + L1 implied by submission row.
- **Returns:** the §2.2 contract (scores, overall_band, diff, errors[] with eager explanations, grader_trace).
- **Errors:** `PASSAGE_RETIRED`, `BUDGET_EXCEEDED` (degrades to Tier 0+1, never hard-fails), `DUPLICATE_SUBMISSION` (returns cached grade).
- **Auth:** authenticated learner; submission must belong to user.
- **Side effects:** writes dt_grade + dt_error_instance[]; enqueues systematic errors for Feature 2; logs grader_trace cost.

### `GET /api/dual-translation/next`
- **Purpose:** serve the next passage for the user (L1 reference chosen from `user_languages`).
- **Selection rule:** draw only from `dt_passage` whose `source_ref_id` is a test the **user has
  already completed** (any of reading/listening/dictation — check `test_attempts` for the user),
  so content is inherently at-level. L1 reference chosen for the user's L1.
- **Returns:** `{submission_id, l1_text, age_tier, rubric_descriptors}` (rubric shown as "feed-up").
- **Interleaving:** the served queue **interleaves due error exercises** (isolate-and-re-translate /
  cloze) with fresh passages — see [[features/dual-translation-remediation.tech]].

### `POST /api/dual-translation/passages/build` (admin/batch)
- **Purpose:** extract L2 passages from corpus + batch-generate L1 references (async batch).
- **Auth:** admin. See [[algorithms/translation-grading-cascade.tech]] §batch.

## Key Architectural Decisions
1. **Reference-first / deterministic Tier 0.** Diff before any model call; reuse the dictation
   grader. Rationale: most cost is avoidable; alternatives (always-LLM) rejected as wasteful.
   → [[decisions/ADR-014-reference-first-grading]].
2. **Eager explanations.** "Why is this an error" is generated for every error up-front, not on
   open. Rationale: the user's explicit priority; the explanation *is* the noticing payload.
   Cost is contained by keeping the grading call compact and templating deterministic cases.
   → [[decisions/ADR-015-eager-error-explanations]].
3. **Per-pair taxonomy.** Interlingual rules are keyed by directed L1↔L2 pair because transfer
   errors depend on the L1. → [[decisions/ADR-016-per-pair-error-taxonomy]].
4. **Standalone surface, L1→L2 MVP.** Own tables/routes, integrate with Study Plans later.
   → [[decisions/ADR-017-dual-translation-standalone-l1l2-mvp]].

## Security Considerations
- Submission ownership check (user_id match) on every grade/read.
- Learner reproduction text is sent to OpenRouter and **retained for analysis** — no special
  privacy posture required (resolved 2026-06-23). Tier 0 still runs locally and avoids a model
  call for exact/near-exact matches.
- Rate-limit submissions; per-user/day token budget guardrail with graceful degrade.
- Treat model output as untrusted: validate the structured JSON shape; **fail-open to Tier 0
  marks** on malformed grader JSON (precedent: judges fail-open on 404 — see memory
  `prompt-template-model-slug-rot`).

## Testing Strategy
- **Tier 0 unit:** exact match → full marks/0 errors/0 tokens; near-exact within fuzzy tolerance;
  width/punctuation/kana normalization for ZH/JA.
- **Contract:** every error has non-empty spans, learner_form, corrected_form, explanation.
- **Cost regression:** assert rubric/taxonomy prefix is cache-stable (byte-identical) across
  submissions; a prefix edit must bump `dt_rubric_version` and is the only thing that busts cache.
- **Resilience:** malformed grader JSON → fail-open to Tier 0 marks, error logged, learner not blocked.
- **Live smoke:** one passage per L2 (ZH/EN/JA) graded end-to-end on the configured OpenRouter slug.

## Related Pages
- [[features/dual-translation]] — prose
- [[features/dual-translation-remediation.tech]] — Feature 2
- [[algorithms/translation-grading-cascade.tech]] — cascade + cost levers
- [[business-rules/translation-error-taxonomy]] — taxonomy + promotion
- [[database/schema.tech]] — current live schema (these tables are additions)
- [[features/dictation.tech]] — diff grader reused for Tier 0
- [[features/model-arena.tech]] — OpenRouter pricing/runner pattern reused for the router
