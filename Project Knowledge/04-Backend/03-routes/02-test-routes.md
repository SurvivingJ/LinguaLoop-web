# Test Routes (`routes/tests.py`)

## Overview

Test routes handle test listing, retrieval, submission, generation, and moderation. All endpoints are prefixed with `/api/tests/`.

## Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/tests/` | GET | JWT | List tests with ELO ratings |
| `/api/tests/<slug>` | GET | None | Get test by slug |
| `/api/tests/<slug>/submit` | POST | JWT | Submit test answers |
| `/api/tests/test/<identifier>` | GET | None | Get test with questions and ratings |
| `/api/tests/random` | GET | JWT | Get random ELO-matched test |
| `/api/tests/recommended` | GET | JWT | Get recommended tests |
| `/api/tests/generate_test` | POST | JWT | Generate new AI test |
| `/api/tests/custom_test` | POST | JWT | Create custom test |
| `/api/tests/moderate` | POST | JWT | Content moderation check |

---

## GET `/api/tests/`

Lists available tests with optional filtering. Includes ELO skill ratings for each test.

**Auth:** JWT required

**Query Parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `language_id` | string | No | Filter by language UUID |
| `difficulty` | string | No | Filter by difficulty level |
| `limit` | integer | No | Max number of tests to return |

**Response 200:**
```json
{
  "success": true,
  "tests": [
    {
      "id": "uuid",
      "slug": "test-slug",
      "title": "Test Title",
      "language_id": "uuid",
      "difficulty": "intermediate",
      "skill_ratings": {
        "listening": 1200,
        "vocabulary": 1150,
        "grammar": 1100
      }
    }
  ]
}
```

**Error Responses:**
- `401` - Missing or invalid JWT
- `500` - Server error

---

## GET `/api/tests/<slug>`

Retrieves a single test by its URL slug.

**Auth:** None

**Path Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `slug` | string | The test's URL-friendly slug |

**Response 200:**
```json
{
  "test": {
    "id": "uuid",
    "slug": "test-slug",
    "title": "Test Title",
    "language_id": "uuid",
    "difficulty": "intermediate",
    "transcript": "...",
    "audio_url": "..."
  },
  "status": "success"
}
```

**Error Responses:**
- `404` - Test not found
- `500` - Server error

---

## POST `/api/tests/<slug>/submit`

Submits answers for a test and returns scored results. Calls the `process_test_submission` RPC function.

**Auth:** JWT required

**Path Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `slug` | string | The test's URL-friendly slug |

**Service Method:** RPC `process_test_submission`

**Request Body:**
```json
{
  "responses": [
    {
      "question_id": "uuid",
      "selected_answer": "B"
    }
  ],
  "test_mode": "practice"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `responses` | array | Yes | Array of answer objects |
| `responses[].question_id` | string | Yes | UUID of the question |
| `responses[].selected_answer` | string | Yes | The selected answer option |
| `test_mode` | string | Yes | Mode of test taking (e.g., "practice") |

**Response 200:**
```json
{
  "status": "success",
  "result": {
    "score": 8,
    "total_questions": 10,
    "percentage": 80.0,
    "question_results": [
      {
        "question_id": "uuid",
        "correct": true,
        "correct_answer": "B",
        "selected_answer": "B"
      }
    ],
    "is_first_attempt": true,
    "user_elo_change": 15,
    "test_elo_change": -5
  }
}
```

**Error Responses:**
- `400` - Invalid request body or missing responses
- `401` - Missing or invalid JWT
- `404` - Test not found
- `500` - Submission processing failure

---

## GET `/api/tests/test/<identifier>`

Retrieves a test with its full question set and skill ratings. Accepts either a slug or UUID as the identifier.

**Auth:** None

**Path Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `identifier` | string | Test slug or UUID |

**Response 200:**
```json
{
  "test_data": {
    "id": "uuid",
    "slug": "test-slug",
    "title": "Test Title",
    "transcript": "...",
    "audio_url": "..."
  },
  "questions_data": [
    {
      "id": "uuid",
      "question_text": "...",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "B"
    }
  ],
  "skill_ratings": {
    "listening": 1200,
    "vocabulary": 1150,
    "grammar": 1100
  }
}
```

**Error Responses:**
- `404` - Test not found
- `500` - Server error

---

## GET `/api/tests/random`

Returns a random test matched to the user's ELO rating for the specified language.

**Auth:** JWT required

**Service Method:** RPC `get_recommended_test`

**Query Parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `language_id` | string | Yes | Language UUID to filter by |

**Response 200:**
```json
{
  "test": {
    "id": "uuid",
    "slug": "test-slug",
    "title": "Test Title",
    "difficulty": "intermediate"
  },
  "status": "success"
}
```

**Error Responses:**
- `400` - Missing language_id
- `401` - Missing or invalid JWT
- `404` - No matching test found
- `500` - Server error

---

## GET `/api/tests/recommended`

Returns a list of recommended tests based on the user's ELO rating for the specified language.

**Auth:** JWT required

**Service Method:** RPC `get_recommended_tests`

**Query Parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `language_id` | string | Yes | Language UUID to filter by |

**Response 200:**
```json
{
  "success": true,
  "recommended_tests": [
    {
      "id": "uuid",
      "slug": "test-slug",
      "title": "Test Title",
      "difficulty": "intermediate",
      "match_score": 0.95
    }
  ]
}
```

**Error Responses:**
- `400` - Missing language_id
- `401` - Missing or invalid JWT
- `500` - Server error

---

## POST `/api/tests/generate_test`

Generates a new AI-powered test. Uses AIService to create a transcript and questions, TestService to save the test, and AIService to generate audio.

**Auth:** JWT required

**Service Methods:** `AIService` (transcript + questions generation, audio generation), `TestService.save_test`

**Request Body:**
```json
{
  "language": "spanish",
  "difficulty": "intermediate",
  "topic": "Travel",
  "style": "conversation",
  "tier": "free"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `language` | string | Yes | Target language |
| `difficulty` | string | Yes | Difficulty level |
| `topic` | string | Yes | Topic for the test content |
| `style` | string | Yes | Style of the transcript |
| `tier` | string | Yes | User's subscription tier |

**Response 200:**
```json
{
  "slug": "generated-test-slug",
  "test_id": "uuid",
  "status": "success",
  "audio_generated": true,
  "test_summary": "A conversation about travel in Spain..."
}
```

**Error Responses:**
- `400` - Invalid request body or parameters
- `401` - Missing or invalid JWT
- `403` - Insufficient tokens or tier
- `500` - Generation failure

---

## POST `/api/tests/custom_test`

Creates a custom test using a user-provided transcript. Similar to `generate_test` but skips transcript generation.

**Auth:** JWT required

**Service Methods:** `AIService` (question generation, audio generation), `TestService.save_test`

**Request Body:**
```json
{
  "language": "spanish",
  "difficulty": "intermediate",
  "transcript": "User-provided transcript text...",
  "topic": "Travel",
  "style": "conversation"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `language` | string | Yes | Target language |
| `difficulty` | string | Yes | Difficulty level |
| `transcript` | string | Yes | User-provided transcript text |
| `topic` | string | Yes | Topic for the test |
| `style` | string | Yes | Style of the content |

**Response 200:**
```json
{
  "slug": "custom-test-slug",
  "test_id": "uuid",
  "status": "success",
  "audio_generated": true,
  "test_summary": "Custom test summary..."
}
```

**Error Responses:**
- `400` - Invalid request body or missing transcript
- `401` - Missing or invalid JWT
- `403` - Insufficient tokens or tier
- `500` - Generation failure

---

## POST `/api/tests/moderate`

Runs content moderation on the provided text using AIService.

**Auth:** JWT required

**Service Method:** `AIService.moderate_content()`

**Request Body:**
```json
{
  "content": "Text to moderate..."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | string | Yes | Text content to check for moderation |

**Response 200:**
```json
{
  "is_safe": true,
  "flagged_categories": [],
  "status": "success"
}
```

**Error Responses:**
- `400` - Missing content
- `401` - Missing or invalid JWT
- `500` - Moderation service failure

---

## Related Documents

- [API Overview](../../07-API-Reference/01-api-overview.md)
- [Test Endpoints API Reference](../../07-API-Reference/03-test-endpoints.md)
