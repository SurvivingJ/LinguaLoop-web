# Utility Endpoints

Utility endpoints provide health checks, configuration, and metadata. These routes are defined in `app.py`.

---

### `GET /api/health`

**Auth:** None

**Request:** No body or params.

**Response 200:**
```json
{
  "status": "healthy",
  "services": {
    "database": "connected",
    "ai_service": "available",
    "audio_service": "available"
  }
}
```

**Error responses:**
- `503` - One or more services are unavailable

---

### `GET /api/config`

**Auth:** None

**Request:** No body or params.

**Response 200:**
```json
{
  "success": true,
  "config": {
    "feature_flags": {
      "custom_tests_enabled": true,
      "ai_generation_enabled": true
    },
    "token_costs": {
      "generate_test": 10,
      "custom_test": 5
    }
  }
}
```

**Error responses:**
- `500` - Server error

---

### `GET /api/metadata`

**Auth:** None

**Request:** No body or params.

**Response 200:**
```json
{
  "success": true,
  "languages": [
    {
      "id": "uuid",
      "name": "Spanish",
      "code": "es"
    }
  ],
  "test_types": [
    {
      "id": "uuid",
      "name": "Listening Comprehension"
    }
  ]
}
```

**Error responses:**
- `500` - Server error

---

## Related Documents

- [API Overview](01-api-overview.md)
- [Core Routes (Backend)](../04-Backend/03-routes/04-core-routes.md)
