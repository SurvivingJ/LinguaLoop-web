---
title: Dual Translation — Technical Specification (Feature 1: Grading)
type: feature-tech
status: in-progress
prose_page: ./dual-translation.md
last_updated: 2026-11-14
dependencies:
  - "table: tests (transcript) and mysteries/mystery_scenes — L2 source for passages"
  - "table: dim_languages (1=ZH, 2=EN, 3=JA), users, user_languages"
  - "table: users.native_language_id (added TASK-607, migrations/add_users_native_language.sql) — the learner's L1; user_languages only tracks L2 study languages, never recorded this"
  - "table: prompt_templates — holds OpenRouter model slugs per language/stage (model router)"
  - "service: services.dictation.grader (Levenshtein WordDiff) — reused for Tier 0"
  - "service: shared OpenRouter client (as used by services.model_arena.llm_runner)"
  - "new tables: dt_passage, dt_submission, dt_grade, dt_error_instance, dt_rubric_version, dt_taxonomy_version"
  - "new service: services.dual_translation.* (passage_builder, grader_cascade, router)"
  - "service (2026-11-14, flag-gated): services.dual_translation.single_call_grader / single_call_prompts / sentence_pairs — ADR-044"
  - "migration (applied to production 2026-11-14): migrations/dt_grading_assets.sql — dt_error_instance asset columns + dt_grading_call"
  - "migration (column part applied 2026-11-14): migrations/dt_taxonomy_v6_columns.sql — taxonomy_version / explanation_variant / remap_flag"
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
| `age_tier` | smallint NOT NULL | CHECK: BETWEEN 1 AND 6 ([[decisions/ADR-003-age-tiers]]); **derived**, not inherited — `tests` has no `age_tier` column, so the builder (TASK-603) folds `tests.difficulty` (1–9) via `DIFFICULTY_TO_TIER` to the tier int 1–6 |
| `register` | text | politeness/register metadata (esp. JA keigo level); `tests` has no `register` column, so the corpus builder (TASK-603) leaves this NULL |
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
hardcoded in app code. **Live: v6 since 2026-11-14 (TASK-853; v5 kept, inactive; before that v5 from 2026-07-13, v4 from TASK-616 2026-07-04)** — the v4 description follows — all six directed-pair tables
(`ja-en`/`zh-en`/`en-ja`/`zh-ja`/`en-zh`/`ja-zh`) + en/ja/zh baselines, with enriched per-L1 templates /
per-L2 glosses. Dimension **weights** are *not* here — they live in `dt_rubric_version` (v2 raised
`ja.fidelity` 0.30, `zh.accuracy` 0.40); see [[algorithms/translation-grading-cascade.tech]].
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
- **Purpose:** serve the next passage for the user (L1 reference chosen via `users.native_language_id`).
- **Selection rule:** draw only from `dt_passage` whose `source_ref_id` is a test the **user has
  already completed** (any of reading/listening/dictation — check `test_attempts` for the user),
  so content is inherently at-level. L1 reference chosen for the user's L1.
  **Correction (TASK-607):** the original draft said this came from `user_languages` — it doesn't;
  that table only tracks L2 *study* languages. `users.native_language_id` was added specifically
  for this (nullable; falls back to English, id=2, while unset — no onboarding UI sets it yet).
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

## Single-call grader (ADR-044) — added 2026-11-14, prompt v2, default ON

Decision: [[decisions/ADR-044-dt-single-call-generative-grader]]. Evidence:
[[evaluations/dt-decision-grading-2026-11-14]] §9 and §9.1. Tasks: [[tasklist/dt-single-call-grader.tasks]].
State: `DT_SINGLE_CALL_GRADER` and `DT_GRADING_ASSET_COLUMNS` default to on in `config.py` (owner
approval 2026-11-14). Taxonomy v6 was activated in production on 2026-11-14 (TASK-853; v5 kept,
inactive) and `migrations/dt_grading_assets.sql` was applied the same day (TASK-935), so this flow
grades live once the code is deployed and the web workers are restarted (the taxonomy is cached per
process with no TTL). `DT_TAXONOMY_COLUMNS` also defaults to on now that its columns exist. Not done:
shadow run on real submissions, native-speaker review of the model explanations, deploy. If the
migration were missing, grades would still be saved without the asset columns.

### Flow

`grader_cascade._grade_cascade` after the Tier 0 short-circuit (Tier 0 is unchanged):

```
Tier 0 resolved? ── yes ──> Tier 0 contract (no model call)
      │ no
single_call on? ── no ───> configured flow (v2 if DT_FRAMEWORK_V2, else v1)
      │ yes (default)
primary model ──ok──> decode ──> contract            (grader_trace.single_call.path = "primary")
      │ call error / not a JSON object with an `errors` list
fallback model (once) ──ok──> decode ──> contract    (path = "fallback_model")
      │ fails too, or the taxonomy's type list is not the hardcoded one, or any unexpected exception
configured flow ──> its contract + grader_trace.single_call{used:false, path:"fallback_flow:v2|v1", reason}
```

- Modules: `services/dual_translation/single_call_grader.py` (flow, decode, span location, trace,
  asset records), `single_call_prompts.py` (prompt + schema + hardcoded type list,
  `PROMPT_VERSION = "dt-single-call/v2-quotes-5dim/2026-11-14"`), `sentence_pairs.py` (sentence
  split + alignment).
- Request: system prompt = task, "not errors" paragraph, error fields, per-L2 type list, severity
  rubric, then the judgment instructions and the rubric's naturalness/range band descriptors for
  the passage's `age_tier` (last, so the cached prefix is shared across age tiers). User prompt =
  `Learner's L1: <language>.`, numbered sentence pairs (`S2 REF: …` / `S2 LRN: …`, identical
  sentences as `S2 SAME: …`), then one line repeating that explanations are written in the L1.
  Temperature 0, `max_tokens` 1400, `response_format: json_schema` strict, reasoning off,
  `usage.include`.
- Response, in this order:
  `{"errors": [{sentence, learner_quote, reference_quote, type, severity, confidence, source,
  explanation}], "naturalness": {band, evidence}, "range": {band, evidence}}`.

### Decode, per model entry

1. Not an object, or severity not minor/major/critical → dropped (`invalid_entry`).
2. **Type.** In the hardcoded list for the L2 → kept. A v5 slug that the taxonomy's
   `legacy_aliases` maps onto a listed type → mapped, counted (`type_aliased`) and logged. Anything
   else → dropped (`unknown_type`) and logged.
3. **Confidence** high / medium / low → 0.9 / 0.6 / 0.3 (`confidence`, `confidence_label`). A bare
   number in [0, 1] is accepted and bucketed. Unusable → 0.5, label null, counted
   (`defaulted.confidence`). An entry marked `low` is withheld: not in `errors`, not scored, counted
   (`dropped.low_confidence`) and listed in `withheld_low_confidence`, unless
   `DT_SINGLE_CALL_SHOW_LOW_CONFIDENCE` is on.
4. **Source** interlingual / intralingual from the model. Unusable → `intralingual`, counted
   (`defaulted.source`).
5. **Learner span** (`_locate_learner`), first hit wins; the path is `span_source`:

   | Order | Rule | `span_source` |
   |---|---|---|
   | 1 | exact match of `learner_quote` inside the named sentence; of several occurrences, the first that touches a changed region of the sentence | `exact` |
   | 2 | match after width / kana / case folding, then with punctuation dropped | `normalised` |
   | 3 | exact or normalised match elsewhere in the text, nearest the named sentence (counted in `span_other_sentence`) | `exact` / `normalised` |
   | 4 | fuzzy: the window of the named sentence most similar to the quote, ratio ≥ 0.75, window length within a third of the quote's, sentence ≤ 400 tokens, quote ≥ 2 characters (4 for English) | `fuzzy` |
   | 5 | the diff hunk of the named sentence whose learner side shares a token with the learner quote, or whose reference side shares one with the reference quote; best overlap, then smallest. A dropped word gives a zero-width point | `diff_hunk` |
   | 6 | the whole named learner sentence | `sentence` |

   No usable sentence number and no match anywhere → dropped (`span_unlocatable`).
6. **Correction** (`_reference_side`); the path is `correction_source`:
   `reference_quote` found exactly or normalised in the reference sentence, different from the
   learner form and not the whole sentence → `model_quote`; else the reference side of the diff
   hunk → `aligned_diff`; else the reference quote fuzzy-matched → `model_quote`; else the learner
   span carried across a token alignment of the two sentences → `aligned_diff`; else the whole
   reference sentence → `reference_sentence`.
7. Severity rule: gpt-6-luna → taxonomy default for en (unless the model said critical), model's
   own for zh/ja. deepseek fallback → default for en/ja, model's own for zh. Other slugs → model's own.
8. The entry goes through the shared `_decode_error` (same validation and template rendering as
   v1/v2). Rejections are counted (`decode_rejected`).
9. **Explanation.** The model's text is shown only if it passes `explainer._validated_application`
   (≤ 240 characters, one paragraph, no score-like digits, shares ≥ 2 characters with the learner
   or corrected form) and a wrong-language check (L1 en: more Latin letters than CJK characters
   outside the quoted forms; L1 zh: at least 4 Han characters and not more kana than Han; L1 ja: at
   least 2 kana). The first failing guard is recorded (`missing`, `too_long`, `multi_paragraph`,
   `score_pattern`, `no_form_mention`, `wrong_language`).

word_choice variants are resolved from the dictionary as in v2 (`word_choice_variant`).

### Scoring

- Accuracy, fidelity, understandability: `scoring.compute_dimension_bands` over the kept errors.
- Naturalness, range: the model's band, kept only if the band is an integer 1–4 and the evidence
  quote is found in the learner text (exact or normalised). A naturalness band below 4 is also
  discarded when its evidence overlaps listed errors and none of them is a naturalness-mapped type
  (`collocation`, `cohesion_connective`, `topic_comment`). Judgment status values: `ok`, `missing`,
  `bad_band`, `no_evidence`, `evidence_is_scored_error`.
- `scoring.compute_overall` over the dimensions that are present. A discarded judgment is absent
  from `scores` and listed in `unscored_dimensions`; it is never defaulted.
- Naturalness and range are not validated to the standard of the other three (gold barely varies
  them). See [[evaluations/dt-decision-grading-2026-11-14]] §9.1.

### Hardcoded type list

`single_call_prompts.TYPE_DEFINITIONS[l2]` = (slug, native name, English definition, usual
severity) for every subtype taxonomy v6 allows for that L2: 20 for en, 20 for zh, 23 for ja.
`TestTypeListExhaustive` fails on a missing or extra slug per language (baseline and every directed
pair), a different order, an empty definition or a severity hint that is not the taxonomy default.
At run time a loaded taxonomy whose list differs in either direction makes the flow fall back to
the configured flow ("taxonomy mismatch").

### Config (all env-driven, `config.py`)

| Name | Default | Effect |
|---|---|---|
| `DT_SINGLE_CALL_GRADER` | `True` | Turns the flow on. `grade_submission(single_call=True/False)` overrides it (tests, eval harness). |
| `DT_SINGLE_CALL_MODEL` | `openai/gpt-6-luna` | Primary slug. |
| `DT_SINGLE_CALL_FALLBACK_MODEL` | `deepseek/deepseek-v4.1-flash` | Tried once if the primary fails. Blank disables. |
| `DT_SINGLE_CALL_SHOW_LOW_CONFIDENCE` | `False` | Keeps entries the model marks `low` in the grade (scored like any error). For a UI with an "unsure" state. |
| `DT_SINGLE_CALL_FREE_TRANSLATION` | `False` | Appends Track E's "free translations are expected" paragraph (prompt variant `v2_mit`). Not re-measured with prompt v2. |
| `DT_SINGLE_CALL_EXPLAINER` | `False` | Also runs the v2 Explainer (one more call); its Application layer then replaces the grading model's explanation. |
| `DT_SINGLE_CALL_LOG_LLM_CALLS` | `True` | Logs each call to `llm_calls` (pipeline `dual_translation`, task `dt_single_call_grade`). |
| `DT_TAXONOMY_COLUMNS` | `True` (was `False` until 2026-11-14) | Read/write `dt_error_instance.taxonomy_version` / `.explanation_variant` and the `dt_error_profile_entry` / `dt_card` `taxonomy_version` stamps. On only because `migrations/dt_taxonomy_v6_columns.sql` (column part) is applied in production; set `false` for a database without those columns, or PostgREST rejects every graded submission. |
| `DT_GRADING_ASSET_COLUMNS` | `True` | Read/write what `migrations/dt_grading_assets.sql` adds. Safe if the migration is missing (see Persistence). |

The daily token budget (`DT_DAILY_TOKEN_BUDGET`) does not degrade this flow; its tokens still count.
`tests/conftest.py` pins `DT_SINGLE_CALL_GRADER` and `DT_GRADING_ASSET_COLUMNS` off for the suite (`DT_TAXONOMY_COLUMNS` is not pinned; tests that depend on it set it explicitly).

### Contract additions (single-call grades only; everything else is the §2.2 contract)

- `scores` has up to five keys. `highlights` is `[]`. `provisional` is `false`.
- `errors[]` additionally carry `sentence_index` (0-based aligned sentence pair), `model_severity`,
  `confidence_label`, `model_note`, `explanation_source`, `span_source`, `correction_source`.
  `source` and `confidence` are the model's judgments. A `diff_hunk` error for a dropped word has
  a zero-width `span_reproduction` and an empty `learner_form`.
- `errors[].explanation` is the template text (ADR-015), unchanged. `errors[].explanation_parts =
  {rule, application}`: `application` is the model's L1 explanation when it passed the guards,
  else null. `static/js/dual_translation.js` `buildExplanation` renders `rule` and, under it,
  `application`. `explanation_source` is `model`, `template` (model text missing or rejected) or
  `explainer`. `model_note` holds the accepted model text.
- `grader_trace`: `tier = "single_call"`, `framework_version = "single_call"`, `tokens{in,out}`,
  `slugs[]`, `prompt_version{rubric, taxonomy, single_call}`, `reason`, and
  `single_call{used, path, model, provider, prompt_version, prompt_variant, severity_rule,
  parse_status, usage{in,out,cached,reasoning}, cost_usd, latency_ms, attempts[], errors_raw,
  errors_kept, dropped{invalid_entry, unknown_type, low_confidence, span_unlocatable,
  decode_rejected}, dropped_total, withheld_low_confidence[], type_aliased,
  defaulted{confidence, source}, span_resolution{exact, normalised, fuzzy, diff_hunk, sentence},
  span_other_sentence, correction_resolution{model_quote, aligned_diff, reference_sentence},
  explanation_sources{model, template}, explanation_rejections{reason: n}, sentence_pairs{n,
  aligned_ok}, judgments{naturalness, range}, unscored_dimensions, band_descriptors,
  confidence_scale, per_error[]}`. `per_error[]` holds model severity vs applied severity,
  confidence, source, span/correction source, the raw model explanation (≤ 300 chars), the reject
  reason and `explanation_source`.
- `grading_assets` (one record per model attempt) is on the contract only between the grader and
  the route. The route removes it before the response and before `_persist_grade`.

### Persistence

Taxonomy-v6 columns (`migrations/dt_taxonomy_v6_columns.sql`, column part applied to production 2026-11-14; the five
`dt_v5_snapshot_*` tables in that file were deliberately NOT created because history was deleted rather than rewritten):

| Table | Column | Constraint |
|---|---|---|
| `dt_error_instance`, `dt_error_profile_entry`, `dt_card` | `taxonomy_version` | nullable; version whose slug vocabulary the row's `subtype` is in |
| `dt_error_instance` | `explanation_variant` | CHECK: only for `subtype = 'word_choice'` (`wrong_word` / `wrong_sense` / `false_synonym`) |
| `dt_error_instance`, `dt_error_profile_entry`, `dt_card` | `remap_flag` | CHECK: `split_needs_review` / `merged`; only the (not run) TASK-852 rewrite sets it, so it is always NULL in production |

Migration: `migrations/dt_grading_assets.sql` (**applied to production 2026-11-14**; the seven new `dt_error_instance` columns with CHECKs, the `dt_grading_call` table with indexes, RLS enabled, privileges revoked; column COMMENTs from the file were not applied except a short table comment, re-running the file adds them). Additive and idempotent,
no destructive statement: `ADD COLUMN IF NOT EXISTS`, `CREATE TABLE / INDEX IF NOT EXISTS`, each
CHECK added only if absent (`NOT VALID`, validated after commit).

`dt_error_instance` — new nullable columns:

| Column | Type | Meaning |
|---|---|---|
| `sentence_index` | smallint, ≥ 0 | 0-based aligned sentence pair containing the error |
| `model_severity` | text (minor/major/critical) | severity the model returned, before the rule |
| `model_note` | text, ≤ 240 chars | the model's L1 explanation, stored only when it passed the guards and was shown |
| `explanation_source` | text (model/template/explainer) | which this-sentence explanation the learner saw |
| `confidence_label` | text (high/medium/low) | the model's confidence; `confidence` holds 0.9/0.6/0.3 |
| `span_source` | text (exact/normalised/fuzzy/diff_hunk/sentence) | how the learner span was located |
| `correction_source` | text (model_quote/aligned_diff/reference_sentence) | how the correction was derived |

`dt_grading_call` — new table, one row per grading model call, RLS on with no policies:

| Column | Type | Meaning |
|---|---|---|
| `id` | bigint identity PK | |
| `submission_id` | bigint FK → dt_submission, ON DELETE CASCADE, indexed | |
| `flow` | text | `single_call` |
| `role` | text | primary / fallback / shadow (shadow reserved; no writer yet) |
| `model_slug`, `provider` | text | |
| `prompt_version`, `prompt_variant` | text | reproduces the prompt with the stored texts |
| `severity_rule` | text | model / prior |
| `l2_code` | text | |
| `status` | text | ok / call_failed / malformed_json / malformed_shape |
| `error`, `finish_reason` | text | error ≤ 300 chars |
| `tokens_in`, `tokens_out`, `cached_tokens`, `reasoning_tokens`, `latency_ms` | integer | |
| `cost_usd` | numeric(12,8) | as reported by OpenRouter |
| `taxonomy_version`, `rubric_version` | smallint | |
| `response` | jsonb | the model's parsed error list and two judgments (strings ≤ 300 chars, ≤ 50 entries) |
| `errors_raw`, `errors_kept` | smallint | |
| `dropped` | jsonb | drop counts by reason |
| `result` | jsonb | reserved for shadow rows (decoded grade) |
| `raw_response` | text, ≤ 4000 chars | only when parsing failed |
| `raw_truncated` | boolean | |
| `created_at` | timestamptz, indexed | |

- `routes/dual_translation.py`: `_error_columns()` adds the seven columns when
  `DT_GRADING_ASSET_COLUMNS` is on (v1/v2 errors do not carry them and keep NULLs);
  `_persist_grading_assets` inserts the `dt_grading_call` rows after `_persist_grade`, best-effort
  (a failure is logged, never surfaced).
- **Missing migration.** If the error insert fails while naming the seven columns, it is retried
  once without them; if that works the grade is saved, the columns are treated as unavailable for
  10 minutes (later submissions skip the failing attempt), and one error is logged per process
  naming the migration. After the pause the columns are probed again, so applying the migration
  needs no restart. A failure of the plain insert still propagates and leaves the submission
  ungraded, as before. The cached-grade read degrades the same way.
- **Reloaded grades.** `explanation_parts` is not a column. `_cached_grade` rebuilds it for rows
  with `explanation_source = 'model'` from `explanation` and `model_note`, so a reloaded grade
  shows the same two layers. Without the migration a reloaded grade shows the template only.
- Not stored: the prompt, and any copy of the passage or submission text.
- Size: about 1.5 KB for a clean submission, about 3 KB with two errors; worst case about 9 KB
  (both models return unparsable text). Plus one `llm_calls` row per call (about 0.3 KB).

### Still needed for the guided self-repair flow (not built; TASK-939, TASK-940)

Design: [[design/dt-feedback/option-2-guided-self-repair/SPEC]]. The grader side is ready
(`sentence_index`, located learner span, the model's local correction, error type, confidence,
template text and the model's L1 explanation). Not in this migration, by decision:

- a table for repair episodes per error or sentence: hint level reached (where / what kind / clue /
  answer), number of revisions, each revision's text and re-check result, final outcome;
- a way to re-check one revised sentence (a single-call request for one sentence pair, or the whole
  passage again) and where those calls are logged (`dt_grading_call` can hold them);
- a store or view of a learner's own erroneous sentences for daily practice: submission, sentence
  index, the reference sentence, error types, last attempt, next due.

### Verification

- `tests/test_dual_translation_single_call_grader.py` (121 tests, no network).
- Production path over v6 gold and the Track E stress set:
  [[evaluations/dt-decision-grading-2026-11-14]] §9.1; raw runs in
  `data/eval/dt_decision_2026-11-14/prod_check/v2/`. Prompt v1 check:
  `data/eval/dt_decision_2026-11-14/prod_check/REPORT.md`.
- `scripts/run_dt_grading_eval.py --single-call` grades the gold set through the production path;
  `--items-file <jsonl> --level <level>` grades any item file in the gold schema (the stress set).

## Related Pages
- [[features/dual-translation]] — prose
- [[decisions/ADR-044-dt-single-call-generative-grader]] — single-call generative grader (flag-gated, default on since 2026-11-14)
- [[tasklist/dt-single-call-grader.tasks]] — rollout tasks for the single-call grader
- [[features/dual-translation-remediation.tech]] — Feature 2
- [[algorithms/translation-grading-cascade.tech]] — cascade + cost levers
- [[business-rules/translation-error-taxonomy]] — taxonomy + promotion
- [[database/schema.tech]] — current live schema (these tables are additions)
- [[features/dictation.tech]] — diff grader reused for Tier 0
- [[features/model-arena.tech]] — OpenRouter pricing/runner pattern reused for the router
