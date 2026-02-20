# Auth Routes (`routes/auth.py`)

## Overview

Authentication routes handle user registration, login via OTP, token management, and profile access. All endpoints are prefixed with `/api/auth/`.

## Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/send-otp` | POST | None | Send OTP to email |
| `/api/auth/verify-otp` | POST | None | Verify OTP, return JWT |
| `/api/auth/refresh-token` | POST | None | Refresh JWT token |
| `/api/auth/profile` | GET | JWT | Get user profile |
| `/api/auth/logout` | POST | JWT | Logout user |

---

## POST `/api/auth/send-otp`

Sends a one-time password to the provided email address. Used for both registration and login flows.

**Auth:** None

**Service Method:** `auth_service.send_otp()`

**Request Body:**
```json
{
  "email": "user@example.com",
  "is_registration": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | User's email address |
| `is_registration` | boolean | Yes | Whether this is a new registration or existing login |

**Response 200:**
```json
{
  "success": true,
  "message": "OTP sent successfully"
}
```

**Error Responses:**
- `400` - Missing or invalid email
- `500` - Failed to send OTP

---

## POST `/api/auth/verify-otp`

Verifies the OTP code submitted by the user and returns JWT authentication tokens.

**Auth:** None

**Service Method:** `auth_service.verify_otp()`

**Request Body:**
```json
{
  "email": "user@example.com",
  "otp_code": "123456"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | User's email address |
| `otp_code` | string | Yes | The OTP code received via email |

**Response 200:**
```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "emailVerified": true,
    "subscriptionTier": "free",
    "tokenBalance": 100,
    "totalTestsTaken": 5,
    "totalTestsGenerated": 2
  },
  "jwt_token": "eyJ...",
  "refresh_token": "eyJ..."
}
```

**Error Responses:**
- `400` - Missing email or OTP code
- `401` - Invalid or expired OTP
- `500` - Verification failure

---

## POST `/api/auth/refresh-token`

Exchanges a valid refresh token for a new JWT and refresh token pair.

**Auth:** None

**Service Method:** `auth_service.refresh_session()`

**Request Body:**
```json
{
  "refresh_token": "eyJ..."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `refresh_token` | string | Yes | The current refresh token |

**Response 200:**
```json
{
  "success": true,
  "jwt_token": "eyJ...",
  "refresh_token": "eyJ..."
}
```

**Error Responses:**
- `400` - Missing refresh token
- `401` - Invalid or expired refresh token
- `500` - Token refresh failure

---

## GET `/api/auth/profile`

Returns the authenticated user's profile information.

**Auth:** JWT required (Bearer token in Authorization header)

**Service Method:** `auth_service.get_user_profile(g.current_user_id)`

**Request Body:** None

**Response 200:**
```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "emailVerified": true,
    "subscriptionTier": "free",
    "tokenBalance": 100,
    "totalTestsTaken": 5,
    "totalTestsGenerated": 2
  }
}
```

**Error Responses:**
- `401` - Missing or invalid JWT token
- `404` - User not found
- `500` - Server error

---

## POST `/api/auth/logout`

Logs out the authenticated user by invalidating their session.

**Auth:** JWT required (Bearer token in Authorization header)

**Service Method:** `auth_service.logout(g.current_user_id)`

**Request Body:** None

**Response 200:**
```json
{
  "success": true
}
```

**Error Responses:**
- `401` - Missing or invalid JWT token
- `500` - Logout failure

---

## Related Documents

- [API Overview](../../07-API-Reference/01-api-overview.md)
- [Auth Endpoints API Reference](../../07-API-Reference/02-auth-endpoints.md)
