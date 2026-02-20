# Auth Endpoints

All authentication endpoints are prefixed with `/api/auth/`.

---

### `POST /api/auth/send-otp`

**Auth:** None

**Request:**
```json
{
  "email": "user@example.com",
  "is_registration": true
}
```

**Response 200:**
```json
{
  "success": true,
  "message": "OTP sent successfully"
}
```

**Error responses:**
- `400` - Missing or invalid email
- `500` - Failed to send OTP

---

### `POST /api/auth/verify-otp`

**Auth:** None

**Request:**
```json
{
  "email": "user@example.com",
  "otp_code": "123456"
}
```

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

**Error responses:**
- `400` - Missing email or OTP code
- `401` - Invalid or expired OTP
- `500` - Verification failure

---

### `POST /api/auth/refresh-token`

**Auth:** None

**Request:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response 200:**
```json
{
  "success": true,
  "jwt_token": "eyJ...",
  "refresh_token": "eyJ..."
}
```

**Error responses:**
- `400` - Missing refresh token
- `401` - Invalid or expired refresh token
- `500` - Token refresh failure

---

### `GET /api/auth/profile`

**Auth:** Required (Bearer token)

**Request:** No body or params.

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

**Error responses:**
- `401` - Missing or invalid JWT
- `404` - User not found
- `500` - Server error

---

### `POST /api/auth/logout`

**Auth:** Required (Bearer token)

**Request:** No body or params.

**Response 200:**
```json
{
  "success": true
}
```

**Error responses:**
- `401` - Missing or invalid JWT
- `500` - Logout failure

---

## Related Documents

- [API Overview](01-api-overview.md)
- [Auth Routes (Backend)](../04-Backend/03-routes/01-auth-routes.md)
