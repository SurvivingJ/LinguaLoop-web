# API Response Format

> Source references: `routes/tests.py`, `routes/auth.py`, `routes/reports.py`, `app.py`, `static/js/utils.js`

---

## 1. Content Type

All API responses use `Content-Type: application/json`. The client sends `Content-Type: application/json` and `Authorization: Bearer <token>` headers via the shared `getAuthHeaders()` utility.

---

## 2. Success Response Formats

### Standard Success

```json
{
    "status": "success",
    "data_field": "..."
}
```

The top-level key varies by endpoint. There is no universal `data` wrapper. Instead, each endpoint uses a descriptive key.

### Single Entity Response

```json
{
    "test": { "id": "...", "slug": "...", "title": "..." },
    "status": "success"
}
```

### List Response

```json
{
    "success": true,
    "tests": [ { ... }, { ... } ]
}
```

Note: Some endpoints use `"success": true` as a boolean, others use `"status": "success"` as a string. Both patterns exist in the codebase.

### No Pagination

List endpoints return all matching results up to a `limit` parameter (default 50, max 100). There is no cursor-based or page-based pagination. The `test_history` endpoint supports `limit` and `offset` query parameters:

```
GET /api/tests/history?limit=25&offset=0&language_id=1
```

---

## 3. Error Response Format

### Standard Error

```json
{
    "error": "Human-readable error message",
    "status": "error"
}
```

### Step-Annotated Error (Test Generation)

```json
{
    "error": "Failed to generate transcript: ...",
    "status": "error",
    "step": "transcript_generation",
    "error_type": "ValueError"
}
```

Possible `step` values: `transcript_generation`, `question_generation`, `database_save`, `unexpected_error`.

### Auth Error

```json
{
    "error": "Token missing"
}
```

Auth errors return a bare `error` key without `status`. HTTP status code is 401 or 403.

---

## 4. Endpoint-Specific Response Shapes

### POST /api/auth/verify-otp

```json
{
    "success": true,
    "message": "Authentication successful",
    "user": {
        "id": "uuid",
        "email": "user@example.com",
        "emailVerified": true,
        "subscriptionTier": "free",
        "tokenBalance": 10,
        "totalTestsTaken": 5,
        "totalTestsGenerated": 2
    },
    "jwt_token": "eyJ...",
    "refresh_token": "refresh_..."
}
```

Note: User fields use `camelCase` (frontend convention) unlike the rest of the API.

### POST /api/auth/send-otp

```json
{
    "success": true,
    "message": "OTP sent to user@example.com. Please check your inbox.",
    "email": "user@example.com"
}
```

### GET /api/tests/

```json
{
    "success": true,
    "tests": [
        {
            "id": "uuid",
            "slug": "test-slug",
            "title": "Test Title",
            "language_id": 1,
            "difficulty": 3,
            "listening_rating": 1400,
            "reading_rating": 1400,
            "dictation_rating": 1400,
            "skill_ratings": {
                "listening": { "elo_rating": 1400, "volatility": 100, "total_attempts": 0 }
            }
        }
    ]
}
```

### GET /api/tests/<slug>

```json
{
    "test": {
        "id": "uuid",
        "slug": "test-slug",
        "title": "...",
        "transcript": "...",
        "audio_url": "https://audio.linguadojo.com/slug.mp3",
        "questions": [ ... ]
    },
    "status": "success"
}
```

### POST /api/tests/<slug>/submit

```json
{
    "status": "success",
    "result": {
        "score": 4,
        "total_questions": 5,
        "percentage": 80.0,
        "question_results": [
            {
                "question_id": "uuid",
                "selected_answer": "B",
                "correct_answer": "B",
                "is_correct": true
            }
        ],
        "is_first_attempt": true,
        "user_elo_change": {
            "before": 1400,
            "after": 1420,
            "change": 20
        },
        "test_elo_change": {
            "before": 1400,
            "after": 1395,
            "change": -5
        },
        "test_mode": "reading",
        "attempt_id": "uuid"
    }
}
```

### POST /api/tests/generate_test

```json
{
    "slug": "generated-slug",
    "test_id": "uuid",
    "status": "success",
    "message": "Test generated and saved successfully",
    "audio_generated": true,
    "audio_url": "https://audio.linguadojo.com/slug.mp3",
    "test_summary": {
        "id": "uuid",
        "title": "...",
        "skill_ratings": { ... }
    }
}
```

### GET /api/users/tokens

```json
{
    "total_tokens": 12,
    "free_tokens_today": 2,
    "last_free_token_date": "2025-01-15",
    "status": "success"
}
```

### GET /api/users/elo

```json
{
    "status": "success",
    "ratings": {
        "cn": {
            "language_name": "Chinese",
            "language_id": 1,
            "skills": {
                "listening": {
                    "elo_rating": 1450,
                    "tests_taken": 12,
                    "last_test_date": "2025-01-15T10:30:00Z",
                    "volatility": 100,
                    "skill_name": "Listening"
                }
            }
        }
    }
}
```

### POST /api/reports/submit

```json
{
    "status": "success",
    "report_id": "uuid"
}
```

Response code: `201 Created`.

### GET /api/health

```json
{
    "status": "healthy",
    "timestamp": "2025-01-15T10:30:00Z",
    "version": "2.2.0",
    "services": {
        "openai": true,
        "supabase": true,
        "auth": true,
        "r2": true,
        "stripe": true
    }
}
```

### GET /api/payments/token-packages

```json
{
    "packages": {
        "starter_10": { "tokens": 10, "price_cents": 199, "price_dollars": 1.99, "description": "..." },
        "popular_50": { "tokens": 50, "price_cents": 799, "price_dollars": 7.99, "description": "..." },
        "premium_200": { "tokens": 200, "price_cents": 1999, "price_dollars": 19.99, "description": "..." }
    },
    "status": "success"
}
```

### POST /api/payments/create-intent

```json
{
    "client_secret": "pi_..._secret_...",
    "amount": 799,
    "tokens": 50,
    "status": "success"
}
```

---

## 5. Response Conventions Summary

| Convention | Pattern |
|---|---|
| Success indicator | `"status": "success"` or `"success": true` (both used) |
| Error indicator | `"error": "message"` with `"status": "error"` |
| Entity wrapping | Named key per type (e.g., `"test"`, `"tests"`, `"ratings"`, `"profile"`) |
| Pagination | No pagination; `limit` + `offset` on history endpoint only |
| Date format | ISO 8601 (`2025-01-15T10:30:00Z`) |
| IDs | UUIDs as strings |
| Null values | Explicit `null` in JSON (e.g., `"user": null` on auth failure) |

---

## Related Documents

- [02-error-handling.md](./02-error-handling.md) -- Error response details
- [01-coding-conventions.md](./01-coding-conventions.md) -- Code structure
- [../12-PRD/02-feature-specifications/02-test-taking.md](../12-PRD/02-feature-specifications/02-test-taking.md) -- Test submission flow
