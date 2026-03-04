# Test Endpoints

All test endpoints are prefixed with `/api/tests/`.

---

### `GET /api/tests/`

**Auth:** Required (Bearer token)

**Request:** Query params: `language_id` (optional), `difficulty` (optional), `limit` (optional integer).

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

**Error responses:**
- `401` - Missing or invalid JWT
- `500` - Server error

---

### `GET /api/tests/<slug>`

**Auth:** None

**Request:** Path param `slug` (string).

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

**Error responses:**
- `404` - Test not found
- `500` - Server error

---

### `POST /api/tests/<slug>/submit`

**Auth:** Required (Bearer token)

**Request:**
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

**Error responses:**
- `400` - Invalid request body or missing responses
- `401` - Missing or invalid JWT
- `404` - Test not found
- `500` - Submission processing failure

---

### `GET /api/tests/test/<identifier>`

**Auth:** None

**Request:** Path param `identifier` (slug or UUID).

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

**Error responses:**
- `404` - Test not found
- `500` - Server error

---

### `GET /api/tests/random`

**Auth:** Required (Bearer token)

**Request:** Query param: `language_id` (required).

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

**Error responses:**
- `400` - Missing language_id
- `401` - Missing or invalid JWT
- `404` - No matching test found
- `500` - Server error

---

### `GET /api/tests/recommended`

**Auth:** Required (Bearer token)

**Request:** Query param: `language_id` (required).

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

**Error responses:**
- `400` - Missing language_id
- `401` - Missing or invalid JWT
- `500` - Server error

---

### `POST /api/tests/generate_test`

**Auth:** Required (Bearer token)

**Request:**
```json
{
  "language": "spanish",
  "difficulty": "intermediate",
  "topic": "Travel",
  "style": "conversation",
  "tier": "free"
}
```

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

**Error responses:**
- `400` - Invalid request body or parameters
- `401` - Missing or invalid JWT
- `403` - Insufficient tokens or tier
- `500` - Generation failure

---

### `POST /api/tests/custom_test`

**Auth:** Required (Bearer token)

**Request:**
```json
{
  "language": "spanish",
  "difficulty": "intermediate",
  "transcript": "User-provided transcript text...",
  "topic": "Travel",
  "style": "conversation"
}
```

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

**Error responses:**
- `400` - Invalid request body or missing transcript
- `401` - Missing or invalid JWT
- `403` - Insufficient tokens or tier
- `500` - Generation failure

---

### `POST /api/tests/moderate`

**Auth:** Required (Bearer token)

**Request:**
```json
{
  "content": "Text to moderate..."
}
```

**Response 200:**
```json
{
  "is_safe": true,
  "flagged_categories": [],
  "status": "success"
}
```

**Error responses:**
- `400` - Missing content
- `401` - Missing or invalid JWT
- `500` - Moderation service failure

---

## Related Documents

- [API Overview](01-api-overview.md)
- [Test Routes (Backend)](../04-Backend/03-routes/02-test-routes.md)
