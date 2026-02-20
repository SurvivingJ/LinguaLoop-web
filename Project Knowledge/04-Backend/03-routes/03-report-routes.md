# Report Routes (`routes/reports.py`)

## Overview

Report routes handle user-submitted bug reports, feedback, and improvement suggestions. All endpoints are prefixed with `/api/reports/`.

## Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/reports/submit` | POST | JWT | Submit a bug report or feedback |

---

## POST `/api/reports/submit`

Submits a user report. Inserts a new row into the `user_reports` table with `status='pending'`.

**Auth:** JWT required

**Request Body:**
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

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `report_category` | string | Yes | Category of the report (see valid values below) |
| `description` | string | Yes | Detailed description (minimum 10 characters) |
| `current_page` | string | Yes | The page URL where the issue occurred |
| `test_id` | string | No | UUID of the related test, if applicable |
| `test_type` | string | No | Type of test (e.g., "ai_generated", "custom") |
| `user_agent` | string | No | Browser user agent string |
| `screen_resolution` | string | No | User's screen resolution |

**Valid Report Categories:**
- `test_answer_incorrect` - A test answer is marked incorrectly
- `test_load_error` - A test failed to load
- `website_crash` - The website crashed or became unresponsive
- `improvement_idea` - Suggestion for improvement
- `audio_quality` - Issues with audio playback or quality
- `other` - Any other type of report

**Validation Rules:**
- `report_category` must be one of the valid categories listed above
- `description` must be at least 10 characters long

**Response 201:**
```json
{
  "status": "success",
  "report_id": "uuid"
}
```

**Error Responses:**
- `400` - Invalid category, description too short, or missing required fields
- `401` - Missing or invalid JWT
- `500` - Failed to insert report

---

## Related Documents

- [API Overview](../../07-API-Reference/01-api-overview.md)
- [Report Endpoints API Reference](../../07-API-Reference/06-report-endpoints.md)
