# API Overview

## Base URL

| Environment | Base URL |
|-------------|----------|
| Development | `http://localhost:5000` |
| Production | Configurable via environment variables |

## Authentication

Authenticated endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer eyJ...
```

Tokens are obtained via the `/api/auth/verify-otp` endpoint and can be refreshed via `/api/auth/refresh-token`.

## Response Formats

### Success Responses

Response format is not fully standardized across the API. Some endpoints use `utils/responses.py` helpers while others use direct `jsonify` calls. Common patterns include:

**Pattern 1 - Standard success:**
```json
{
  "success": true,
  "status": "success",
  "data": { ... }
}
```

**Pattern 2 - Endpoint-specific:**
```json
{
  "success": true,
  "tests": [ ... ]
}
```

**Pattern 3 - Minimal:**
```json
{
  "test": { ... },
  "status": "success"
}
```

### Error Responses

**Pattern 1:**
```json
{
  "error": "Error message",
  "status": "error"
}
```

**Pattern 2:**
```json
{
  "success": false,
  "error": "Error message"
}
```

## HTTP Status Codes

| Code | Usage |
|------|-------|
| `200` | Successful request |
| `201` | Resource created (e.g., report submitted) |
| `400` | Bad request - invalid parameters or body |
| `401` | Unauthorized - missing or invalid JWT |
| `403` | Forbidden - insufficient permissions or tokens |
| `404` | Resource not found |
| `500` | Internal server error |
| `503` | Service unavailable (health check failure) |

## CORS

CORS is configured with:
- Allowed origins set via configuration
- Credentials supported (`Access-Control-Allow-Credentials: true`)

## Endpoint Groups

| Group | Prefix | Description |
|-------|--------|-------------|
| [Auth](02-auth-endpoints.md) | `/api/auth/` | Authentication, OTP, tokens |
| [Tests](03-test-endpoints.md) | `/api/tests/` | Test CRUD, submission, generation |
| [Users](04-user-endpoints.md) | `/api/users/` | User profile, ELO, tokens |
| [Payments](05-payment-endpoints.md) | `/api/payments/` | Token packages, Stripe |
| [Reports](06-report-endpoints.md) | `/api/reports/` | Bug reports, feedback |
| [Utility](07-utility-endpoints.md) | `/api/` | Health, config, metadata |

## Related Documents

- [Auth Routes](../04-Backend/03-routes/01-auth-routes.md)
- [Test Routes](../04-Backend/03-routes/02-test-routes.md)
- [Report Routes](../04-Backend/03-routes/03-report-routes.md)
- [Core Routes](../04-Backend/03-routes/04-core-routes.md)
