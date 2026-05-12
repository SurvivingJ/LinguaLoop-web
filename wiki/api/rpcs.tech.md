---
title: API — Technical Specification
type: api-tech
status: in-progress
prose_page: ./rpcs.md
last_updated: 2026-05-12
dependencies:
  - "Flask Blueprints"
  - "Supabase JWT middleware"
  - "Supabase Python client"
breaking_change_risk: medium
---

# API — Technical Specification

## Authentication

All `/api/*` endpoints (except health, config, metadata, and auth/login) require a valid Supabase JWT in the `Authorization: Bearer <token>` header. The `@supabase_jwt_required` decorator validates the JWT and sets `g.user_id`.

## Key Endpoints by Blueprint

### Auth (`/api/auth`)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/login` | Email/password login via Supabase Auth |
| POST | `/signup` | Create account |
| POST | `/logout` | Invalidate session |
| GET | `/session` | Validate current session |

### Tests (`/api/tests`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/recommended` | ELO-matched test recommendations |
| GET | `/<slug>` | Fetch test content |
| GET | `/<slug>/preview` | Test metadata for preview |
| POST | `/submit` | Submit answers, get graded results |

### Exercises (`/api/exercises`)

The daily mixed-session surface — combines FSRS due reviews, BKT uncertainty-zone words, new words, ladder content, and supplementary grammar/collocation. As of Phase 9 (2026-05-12), session selection lives in the [get_exercise_session](../../migrations/phase9_get_exercise_session.sql) SQL RPC (which delegates ladder picks to `get_ladder_session` internally). The Python service ([ExerciseSessionService](../../services/exercise_session_service.py)) calls the RPC, appends up to 3 virtual jumbled-sentence picks from past test transcripts, caches to `user_exercise_sessions`, and enriches for the frontend.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/session` | Cached daily mixed exercise session (per (user, language)) — calls `get_exercise_session` RPC |
| POST | `/session/complete` | Mark an exercise complete in the cached session |
| POST | `/attempt` | Record attempt (BKT + FSRS update; server-side first-attempt gating) |

### Vocab Dojo (`/api/vocab-dojo`)

The vocabulary-ladder surface — entirely ladder-specific. Backed by the `get_ladder_session` SQL RPC ([migrations/phase8_momentum_bands.sql](../../migrations/phase8_momentum_bands.sql)) and `LadderService` ([services/vocabulary_ladder/ladder_service.py](../../services/vocabulary_ladder/ladder_service.py)). See [[features/vocab-dojo.tech]].

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/session` | Build a dojo session (`get_ladder_session` RPC); lazy-inits ladder rows |
| POST | `/attempt` | Record ladder attempt (`ladder_record_attempt` RPC, atomic) |
| GET | `/word/<sense_id>/exercises` | All ladder exercises + word_assets for a sense (preview) |
| POST | `/gate` | Assemble a 3-exercise gate battery (`gate_a` or `gate_b`) |
| POST | `/gate/result` | If passed → `ladder_pass_gate` RPC; if failed → already recorded per item |
| POST | `/stress-test` | Assemble the 8-exercise pre-mastery stress test battery |
| POST | `/stress-test/result` | If passed → `ladder_graduate` (FSRS handoff); if failed → return-only |

### Flashcards (`/api/flashcards`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/due` | Cards due for review |
| POST | `/review` | Submit review rating |

### Vocabulary (`/api/vocabulary`)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/extract` | Extract vocabulary from text |
| GET | `/knowledge` | User's vocabulary knowledge state |

### Corpus (`/api/corpus`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/packs` | List packs with selection state |
| POST | `/packs/select` | Toggle pack selection |

### Mystery (`/api/mystery`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/list` | Available mysteries |
| GET | `/<slug>` | Mystery content |
| POST | `/<slug>/submit` | Submit scene answers |

### Conversations (`/api/conversations`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/list` | Available conversations |
| GET | `/<id>` | Conversation content |

### Users (`/api/users`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/profile` | User profile data |
| PUT | `/profile` | Update profile |
| GET | `/languages` | User's language list |

### Payments (`/api/payments`)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/create-checkout` | Create Stripe checkout session |
| POST | `/webhook` | Stripe webhook handler |
| GET | `/balance` | Token balance |

### Reports (`/api/reports`)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/` | Submit bug report |

## Supabase RPC Functions Called from API

| RPC | Called From | Purpose |
|-----|-----------|---------|
| `process_test_submission()` | tests/submit | Atomic test grading + ELO |
| `get_recommended_tests()` | tests/recommended | ELO-matched test list |
| `get_recommended_test()` | tests/recommended | Single test recommendation |
| `get_word_quiz_candidates()` | exercises/session | Learning-zone word selection |
| `get_vocab_recommendations()` | tests/recommended | Vocab-aware test matching |
| `get_packs_with_user_selection()` | corpus/packs | Pack list with user state |
| `process_stripe_payment()` | payments/webhook | Atomic token addition |
| `can_use_free_test()` | tests/submit | Free test eligibility |
| `bkt_update_*()` | tests/submit | Vocabulary knowledge update |
| `get_ladder_session()` | vocab-dojo/session | Vocabulary ladder session builder (Phase 8) |
| `ladder_record_attempt()` | vocab-dojo/attempt | Atomic ladder attempt + family BKT + FSRS lapse handling |
| `ladder_pass_gate()` | vocab-dojo/gate/result | Threshold gate pass: advance ring |
| `ladder_graduate()` | vocab-dojo/stress-test/result | FSRS handoff on stress test pass |
| `get_exercise_session()` | exercises/session | Daily mixed-session builder (Phase 9) |
| `get_session_senses()` | exercises/session (indirect) | BKT-decay-aware due/learning/new bucket assignment |
| `bkt_apply_lapse_penalty()` | exercises/attempt | FSRS-lapse → p_known penalty |

## Related Pages

- [[api/rpcs]] — Prose overview
- [[overview/project.tech]] — Architecture
- [[database/schema.tech]] — RPC function definitions
