---
title: Dual Translation — Technical Specification (Feature 2: Error Synthesis + Spaced Remediation)
type: feature-tech
status: planned
prose_page: ./dual-translation.md
last_updated: 2026-06-22
dependencies:
  - "table: dt_error_instance (from Feature 1) — source of all remediation"
  - "service: services/vocabulary/fsrs.py (FSRS-4) — reused scheduler"
  - "table: user_flashcards (stability/difficulty/due/reps/lapses/state) — card state pattern"
  - "new tables: dt_error_profile_entry, dt_card (or extend user_flashcards), dt_card_review"
breaking_change_risk: low
---

# Dual Translation — Technical Specification (Feature 2: Error Synthesis + Spaced Remediation)

> Feeds entirely off `dt_error_instance` rows produced by Feature 1
> ([[features/dual-translation.tech]]). Implements the brief's §3.

## Pipeline

```
dt_error_instance[]                                (nightly Batch, async)
       │
       ▼
1. mistake gate     drop is_mistake=true (self-corrected/one-off slips)
       │
       ▼
2. cluster          DETERMINISTIC clustering by taxonomy subtype — cluster key
                    (user_id, l1↔l2 pair, subtype). The grader already emits a
                    structured subtype, so NO embeddings/LLM re-reads are needed for
                    MVP. (pgvector — already in-stack for sense embeddings — is an
                    optional later refinement for intra-subtype splitting.)
       │
       ▼
3. promote          an error subtype enters the SRS only when it RECURS ≥ N times
                    in window W, OR is "wrong under load but correct when attention
                    drawn" (proceduralization gap). N, W = tunable config.
       │
       ▼
4. profile          upsert dt_error_profile_entry: count, frequency×severity rank,
                    trend, remediation_status  → drives the self-regulation dashboard
       │
       ▼
5. cards            build remediation primitives (always toward corrected_form):
                    a) cloze card  — delete ONLY the corrected element inside the
                       full corrected sentence; productive recall; one atom/card
                       (SuperMemo minimum information principle)
                    b) isolate-and-re-translate — re-present the stored problem
                       sentence (via spans) for back-translation after a spaced delay
       │
       ▼
6. schedule         FSRS-4 (reuse services/vocabulary/fsrs.py); INTERLEAVE subtypes
                    within a review session (Rohrer & Taylor); immediate corrective
                    feedback within a card, spacing BETWEEN reviews
       │
       ▼
7. inject           interleave due error exercises into TWO surfaces:
                    (a) the dual-translation practice queue (GET /next), and
                    (b) the Practice Engine exercise sessions.
                    Error exercises are NOT sense-linked — they ride a separate
                    subtype-keyed stream, distinct from the sense-keyed candidate pools.
```

## Database Impact (new tables)

### `dt_error_profile_entry`
Aggregated cluster per learner per subtype — the self-regulation dashboard row.
| column | type | notes |
|---|---|---|
| `id` | bigint PK | |
| `user_id` | uuid NOT NULL | |
| `l1_language_id` | bigint NOT NULL | directed pair half |
| `l2_language_id` | bigint NOT NULL | directed pair half |
| `subtype` | text NOT NULL | taxonomy key |
| `count` | integer NOT NULL | occurrences in window |
| `severity_rank` | float NOT NULL | frequency × severity (global errors rank first) |
| `trend` | jsonb | time series for "article errors down 40% this month" |
| `remediation_status` | text NOT NULL | `watching` \| `queued` \| `drilling` \| `resolved` |
| `updated_at` | timestamptz | |
| | | UNIQUE (user_id, l1_language_id, l2_language_id, subtype) |

### `dt_card`
Remediation item built from an error_instance/profile entry. FSRS state mirrors `user_flashcards`.
| column | type | notes |
|---|---|---|
| `id` | bigint PK | |
| `user_id` | uuid NOT NULL | |
| `profile_entry_id` | bigint | FK → dt_error_profile_entry |
| `origin_error_id` | bigint | FK → dt_error_instance (provenance) |
| `card_type` | text NOT NULL | `cloze` \| `isolate_retranslate` |
| `subtype` | text NOT NULL | taxonomy subtype — the cluster/interleave key. **No `sense_id`: error cards are NOT sense-linked.** |
| `prompt_payload` | jsonb NOT NULL | built toward `corrected_form` — NEVER contains learner_form as the answer target |
| `stability` | float | FSRS |
| `difficulty` | float | FSRS |
| `due_date` | date | FSRS |
| `state` | text | new \| learning \| review \| relearning |
| `reps` | int | |
| `lapses` | int | |
| `last_review` | timestamptz | |

> Decision point for build: either add `dt_card` (clean separation) **or** extend
> `user_flashcards` with a `card_kind` discriminator. Recommendation: separate `dt_card`
> table to avoid polluting the vocab-sense-keyed `user_flashcards` (which is UNIQUE on
> `(user_id, sense_id)` and has no sense for a grammar-pattern card). Reuse the FSRS *code*,
> not the table.

### `dt_card_review`
Append-only review log — required for the recurrence-reduction instrumentation.
| column | type | notes |
|---|---|---|
| `id` | bigint PK | |
| `card_id` | bigint NOT NULL | |
| `rating` | smallint NOT NULL | FSRS grade (again/hard/good/easy) |
| `was_correct` | boolean | for delayed re-test accuracy metric |
| `reviewed_at` | timestamptz | |

## Instrumentation requirement (non-negotiable per report)
Log **delayed re-test accuracy on previously-errored items** (`dt_card_review.was_correct`
keyed back to subtype). Monitored metric: if recurrence is not dropping within ~3–4 review
cycles, the card formulation is likely violating the minimum-information principle. This is a
dashboard metric, not an assumption — the spacing/interleaving evidence generalises from
vocab/math labs and must be validated on our own remediation data.

## API / RPC Surface

### `GET /api/dual-translation/profile`
- **Purpose:** the learner's error-profile dashboard (ranked by frequency×severity, with trend).
- **Returns:** `[{subtype, count, severity_rank, trend, remediation_status}]`.
- **Note:** gamify the *shrinking profile*, never the score (Black & Wiliam reward-chasing warning).

### `GET /api/dual-translation/cards/due` / `POST /api/dual-translation/cards/<id>/review`
- Mirror the existing flashcards endpoints; interleave subtypes in the due queue.
- `review` updates FSRS state via the reused scheduler and appends `dt_card_review`.

## Key Architectural Decisions
1. **Reuse FSRS-4 code, new table.** Don't overload `user_flashcards`. Rationale: card identity
   is a grammar/lexical **subtype, not a word sense** — error cards are not sense-linked, which is
   exactly why the sense-keyed `user_flashcards` (UNIQUE on `(user_id, sense_id)`) is the wrong home.
2. **Deterministic subtype clustering, no embeddings.** The grader emits a structured subtype, so
   clustering is a plain `(user, pair, subtype)` group-by. Reserve all LLM spend for grading.
   pgvector optional for later intra-subtype refinement.
3. **Promotion gate before SRS.** Only systematic errors are drilled (Corder error-vs-mistake).
   → [[business-rules/translation-error-taxonomy]].
4. **Interleave into Practice Engine too.** Error exercises are injected into both the
   dual-translation queue and the broader Practice Engine sessions (a separate, non-sense-linked
   interleaved stream), so remediation happens in the flow of normal practice, not only in a
   dedicated review screen.

## Testing Strategy
- Mistake-gate unit: `is_mistake=true` never produces a card.
- Promotion: subtype with < N occurrences stays `watching`; crossing N → `queued`.
- Card invariant test: `prompt_payload` answer target equals `corrected_form`, never `learner_form`.
- Interleaving: due queue does not block-group a single subtype.
- Recurrence metric present and decreasing on a seeded fixture.

## Related Pages
- [[features/dual-translation]] — prose
- [[features/dual-translation.tech]] — Feature 1 (grading) + shared data model
- [[features/flashcards.tech]] — FSRS-4 implementation reused
- [[business-rules/translation-error-taxonomy]] — taxonomy, severity, promotion rule
