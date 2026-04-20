---
title: API — Technical Specification
type: api-tech
status: in-progress
prose_page: ./rpcs.md
last_updated: 2026-04-10
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
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/session` | Fetch exercise batch for user |
| POST | `/submit` | Submit exercise answer |

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

## Related Pages

- [[api/rpcs]] — Prose overview
- [[overview/project.tech]] — Architecture
- [[database/schema.tech]] — RPC function definitions
