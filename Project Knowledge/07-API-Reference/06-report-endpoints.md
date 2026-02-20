# Report Endpoints

All report endpoints are prefixed with `/api/reports/`.

---

### `POST /api/reports/submit`

**Auth:** Required (Bearer token)

**Request:**
```json
{
  "report_category": "test_answer_incorrect",
  "description": "The correct answer for question 3 should be B, not C...",
  "current_page": "/tests/spanish-travel/results",
  "test_id": "uuid",
  "test_type": "ai_generated",
  "user_agent": "Mozilla/5.0...",
  "screen_resolution": "1920x1080"
}
```

Required fields: `report_category`, `description`, `current_page`.
Optional fields: `test_id`, `test_type`, `user_agent`, `screen_resolution`.

Valid categories: `test_answer_incorrect`, `test_load_error`, `website_crash`, `improvement_idea`, `audio_quality`, `other`.

Description must be at least 10 characters.

**Response 201:**
```json
{
  "status": "success",
  "report_id": "uuid"
}
```

**Error responses:**
- `400` - Invalid category, description too short, or missing required fields
- `401` - Missing or invalid JWT
- `500` - Failed to insert report

---

## Related Documents

- [API Overview](01-api-overview.md)
- [Report Routes (Backend)](../04-Backend/03-routes/03-report-routes.md)
