# User Endpoints

All user endpoints are prefixed with `/api/users/`. These routes are defined in `app.py`.

---

### `GET /api/users/elo`

**Auth:** Required (Bearer token)

**Request:** No body or params.

**Response 200:**
```json
{
  "success": true,
  "elo_ratings": {
    "spanish": {
      "listening": 1200,
      "vocabulary": 1150,
      "grammar": 1100,
      "overall": 1150
    }
  }
}
```

**Error responses:**
- `401` - Missing or invalid JWT
- `500` - Server error

---

### `GET /api/users/tokens`

**Auth:** Required (Bearer token)

**Request:** No body or params.

**Response 200:**
```json
{
  "success": true,
  "token_balance": 100,
  "daily_free_eligible": true
}
```

**Error responses:**
- `401` - Missing or invalid JWT
- `500` - Server error

---

### `GET /api/users/profile`

**Auth:** Required (Bearer token)

**Request:** No body or params.

**Response 200:**
```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "subscriptionTier": "free",
    "tokenBalance": 100,
    "totalTestsTaken": 5,
    "totalTestsGenerated": 2
  }
}
```

**Error responses:**
- `401` - Missing or invalid JWT
- `404` - User not found
- `500` - Server error

---

### `GET /api/tests/history`

**Auth:** Required (Bearer token)

**Request:** Query params: `page` (optional, default 1), `per_page` (optional, default 10), `language_id` (optional).

> Note: Although this endpoint is user-specific, it is prefixed with `/api/tests/history` rather than `/api/users/`.

**Response 200:**
```json
{
  "success": true,
  "history": [
    {
      "test_id": "uuid",
      "test_slug": "test-slug",
      "test_title": "Test Title",
      "score": 8,
      "total_questions": 10,
      "percentage": 80.0,
      "completed_at": "2025-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total": 25,
    "pages": 3
  }
}
```

**Error responses:**
- `401` - Missing or invalid JWT
- `500` - Server error

---

## Related Documents

- [API Overview](01-api-overview.md)
- [Core Routes (Backend)](../04-Backend/03-routes/04-core-routes.md)
