# Core Routes (`app.py`)

## Overview

Core routes are defined directly in `app.py` rather than in dedicated route blueprints. They provide health checks, configuration, metadata, user data, test history, and payment endpoints.

## Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/health` | GET | None | Health check with service status |
| `/api/config` | GET | None | Public feature flags and token costs |
| `/api/metadata` | GET | None | Languages and test types from dimension cache |
| `/api/users/elo` | GET | JWT | User ELO ratings across languages/skills |
| `/api/users/tokens` | GET | JWT | Token balance and daily free eligibility |
| `/api/users/profile` | GET | JWT | User profile |
| `/api/tests/history` | GET | JWT | Paginated test attempt history |
| `/api/payments/token-packages` | GET | None | Available token packages |
| `/api/payments/create-intent` | POST | JWT | Create Stripe PaymentIntent |

---

## GET `/api/health`

Returns the health status of the application and its dependent services.

**Auth:** None

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

**Error Responses:**
- `503` - One or more services are unavailable

---

## GET `/api/config`

Returns public configuration including feature flags and token costs. No authentication required.

**Auth:** None

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

---

## GET `/api/metadata`

Returns cached dimension data including available languages and test types.

**Auth:** None

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

---

## GET `/api/users/elo`

Returns the authenticated user's ELO ratings across all languages and skills.

**Auth:** JWT required

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

**Error Responses:**
- `401` - Missing or invalid JWT
- `500` - Server error

---

## GET `/api/users/tokens`

Returns the user's current token balance and whether they are eligible for daily free tokens.

**Auth:** JWT required

**Response 200:**
```json
{
  "success": true,
  "token_balance": 100,
  "daily_free_eligible": true
}
```

**Error Responses:**
- `401` - Missing or invalid JWT
- `500` - Server error

---

## GET `/api/users/profile`

Returns the authenticated user's profile information.

**Auth:** JWT required

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

**Error Responses:**
- `401` - Missing or invalid JWT
- `404` - User not found
- `500` - Server error

---

## GET `/api/tests/history`

Returns a paginated list of the user's test attempt history.

**Auth:** JWT required

**Query Parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `page` | integer | No | Page number (default: 1) |
| `per_page` | integer | No | Results per page (default: 10) |
| `language_id` | string | No | Filter by language UUID |

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

**Error Responses:**
- `401` - Missing or invalid JWT
- `500` - Server error

---

## GET `/api/payments/token-packages`

Returns available token packages for purchase.

**Auth:** None

**Response 200:**
```json
{
  "success": true,
  "packages": [
    {
      "id": "uuid",
      "name": "Starter Pack",
      "tokens": 50,
      "price_cents": 499,
      "currency": "usd"
    }
  ]
}
```

---

## POST `/api/payments/create-intent`

Creates a Stripe PaymentIntent for purchasing a token package.

**Auth:** JWT required

**Request Body:**
```json
{
  "package_id": "uuid"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `package_id` | string | Yes | UUID of the token package to purchase |

**Response 200:**
```json
{
  "success": true,
  "client_secret": "pi_..._secret_...",
  "amount": 499,
  "currency": "usd"
}
```

**Error Responses:**
- `400` - Missing or invalid package_id
- `401` - Missing or invalid JWT
- `404` - Package not found
- `500` - Stripe API error

---

## Related Documents

- [API Overview](../../07-API-Reference/01-api-overview.md)
- [User Endpoints API Reference](../../07-API-Reference/04-user-endpoints.md)
- [Payment Endpoints API Reference](../../07-API-Reference/05-payment-endpoints.md)
- [Utility Endpoints API Reference](../../07-API-Reference/07-utility-endpoints.md)
