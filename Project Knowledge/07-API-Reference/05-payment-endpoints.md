# Payment Endpoints

All payment endpoints are prefixed with `/api/payments/`. These routes are defined in `app.py`.

---

### `GET /api/payments/token-packages`

**Auth:** None

**Request:** No body or params.

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

**Error responses:**
- `500` - Server error

---

### `POST /api/payments/create-intent`

**Auth:** Required (Bearer token)

**Request:**
```json
{
  "package_id": "uuid"
}
```

**Response 200:**
```json
{
  "success": true,
  "client_secret": "pi_..._secret_...",
  "amount": 499,
  "currency": "usd"
}
```

**Error responses:**
- `400` - Missing or invalid package_id
- `401` - Missing or invalid JWT
- `404` - Package not found
- `500` - Stripe API error

---

## Related Documents

- [API Overview](01-api-overview.md)
- [Core Routes (Backend)](../04-Backend/03-routes/04-core-routes.md)
