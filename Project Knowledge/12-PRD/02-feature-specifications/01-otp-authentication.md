# Feature Specification: OTP Authentication

**Status**: Production
**Last Updated**: 2026-02-14
**Owner**: Backend Team
**Version**: 1.0

---

## Overview

The OTP (One-Time Password) authentication system provides passwordless login and registration for LinguaLoop/LinguaDojo users. Users receive a 6-digit code via email to authenticate, eliminating the need for password management while maintaining security through JWT-based session management.

---

## User Stories

### As a new user
- I want to sign up without creating a password
- I want to receive a verification code via email
- I want to be redirected to the welcome screen after first login

### As a returning user
- I want to log in using only my email address
- I want my session to persist across page reloads
- I want to be automatically logged back in when my token expires (silent refresh)

### As a user
- I want clear error messages when something goes wrong
- I want to resend my OTP if it doesn't arrive
- I want the flexibility to go back and change my email if needed

---

## Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant LP as Login Page
    participant API as Backend API
    participant SB as Supabase Auth
    participant Email as Email Service

    U->>LP: Enter email address
    LP->>LP: Validate email format
    LP->>API: POST /api/auth/send-otp
    API->>SB: Generate OTP
    SB->>Email: Send 6-digit code
    Email->>U: Email with OTP

    U->>LP: Enter 6-digit OTP
    LP->>API: POST /api/auth/verify-otp
    API->>SB: Verify OTP code

    alt Valid OTP
        SB-->>API: JWT + refresh token + user data
        API-->>LP: Return tokens + user profile
        LP->>LP: Store in localStorage

        alt First time user (0 tests taken)
            LP->>U: Redirect to /welcome
        else Returning user
            LP->>U: Redirect to /language-selection
        end
    else Invalid OTP
        API-->>LP: Error response
        LP->>U: Display error message
    end
```

---

## Acceptance Criteria

### Email Entry Screen
- Email field validates format using standard regex pattern
- Submit button disabled until valid email entered
- Error messages display for invalid email format
- Loading state shown while OTP is being sent

### OTP Entry Screen
- OTP input accepts exactly 6 numeric digits
- Auto-submit when 6th digit is entered
- Visual feedback for each digit entered
- "Resend OTP" button with rate limiting (60 seconds)
- "Back" button to return to email entry step
- Clear error messages for:
  - Invalid OTP code
  - Expired OTP code
  - Too many failed attempts

### Post-Authentication
- **New users** (total_tests_taken = 0) → redirect to `/welcome`
- **Returning users** (total_tests_taken > 0) → redirect to `/language-selection`
- Tokens stored in localStorage:
  - `jwt_token`: JWT access token
  - `refresh_token`: Refresh token for silent renewal
  - `user_data`: User profile object

### Session Management
- Silent token refresh before expiration
- Automatic logout on refresh token expiration
- Session persists across browser tabs
- Session survives page reload

---

## API Endpoints

### POST /api/auth/send-otp

Send OTP to user's email for authentication.

**Request Body**:
```json
{
  "email": "user@example.com",
  "is_registration": false
}
```

**Response (200 OK)**:
```json
{
  "success": true,
  "message": "OTP sent successfully"
}
```

**Response (400 Bad Request)**:
```json
{
  "success": false,
  "error": "Valid email is required"
}
```

---

### POST /api/auth/verify-otp

Verify OTP code and authenticate user.

**Request Body**:
```json
{
  "email": "user@example.com",
  "otp_code": "123456"
}
```

**Response (200 OK)**:
```json
{
  "success": true,
  "message": "Authentication successful",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "emailVerified": true,
    "subscriptionTier": "free",
    "tokenBalance": 100,
    "totalTestsTaken": 5,
    "totalTestsGenerated": 2
  },
  "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "v1.a3d8f7..."
}
```

**Response (400 Bad Request)**:
```json
{
  "success": false,
  "message": "Invalid or expired OTP code",
  "user": null,
  "jwt_token": null
}
```

---

### POST /api/auth/refresh-token

Refresh JWT token using a refresh token.

**Request Body**:
```json
{
  "refresh_token": "v1.a3d8f7..."
}
```

**Response (200 OK)**:
```json
{
  "success": true,
  "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "v1.b9e2c4..."
}
```

**Response (401 Unauthorized)**:
```json
{
  "success": false,
  "error": "Invalid or expired refresh token"
}
```

---

### GET /api/auth/profile

Get user profile (requires JWT authentication).

**Headers**:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK)**:
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

---

### POST /api/auth/logout

Logout user (requires JWT authentication).

**Headers**:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Implementation**: Client-side only - clears localStorage items:
- `jwt_token`
- `refresh_token`
- `user_data`

**Response (200 OK)**:
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## Data Model

### users table
Managed by Supabase Auth. Contains:
- `id` (UUID): Primary key
- `email` (text): User's email address
- `email_verified` (boolean): Email verification status
- `subscription_tier` (text): User's subscription level
- `token_balance` (integer): Available tokens
- `total_tests_taken` (integer): Count of tests completed
- `total_tests_generated` (integer): Count of custom tests created
- `created_at` (timestamp): Account creation time
- `updated_at` (timestamp): Last profile update

### user_languages table
Tracks per-language activity and ELO ratings:
- `user_id` (UUID): FK to users
- `language_id` (integer): FK to dim_languages
- `elo_rating` (integer): User's skill rating
- `tests_taken` (integer): Tests completed in this language
- `created_at` (timestamp)
- `updated_at` (timestamp)

---

## Edge Cases & Error Handling

### Expired OTP
- **Timeout**: OTP codes expire after 10 minutes
- **Behavior**: Display "OTP expired, please request a new one"
- **Action**: Show "Resend OTP" button

### Wrong OTP Code
- **Max attempts**: 3 attempts per OTP
- **Behavior**: Display "Invalid OTP code (X attempts remaining)"
- **After 3 failures**: OTP invalidated, must request new code

### Already Logged In
- **Check**: Verify JWT token on page load
- **Behavior**: If valid token exists, redirect to app
- **Skip**: Don't show login page to authenticated users

### Network Error During Verification
- **Retry strategy**: Display "Network error, please try again"
- **User action**: Allow manual retry
- **Timeout**: 30 second timeout on API calls

### Rate Limiting on send-otp
- **Limit**: Max 3 OTP requests per email per hour
- **Response**: 429 Too Many Requests
- **Message**: "Too many requests, please try again in X minutes"

### Invalid Email Format
- **Validation**: Regex pattern check on client-side
- **Behavior**: Disable submit button until valid
- **Server-side**: Re-validate and return 400 if invalid

### Refresh Token Expiration
- **Lifetime**: Refresh tokens expire after 30 days
- **Behavior**: Silent refresh fails, redirect to login
- **Message**: Optional "Session expired, please log in again"

---

## Security Considerations

### OTP Generation
- **Length**: 6 numeric digits
- **Randomness**: Cryptographically secure random generation
- **Uniqueness**: One active OTP per email at a time
- **Rate limiting**: Prevent brute force attacks

### JWT Tokens
- **Algorithm**: HS256 (HMAC-SHA256)
- **Expiration**: 1 hour (configurable)
- **Claims**: User ID, email, subscription tier
- **Secret**: Stored in environment variables

### Refresh Tokens
- **Storage**: Supabase auth system
- **Rotation**: New refresh token issued on each use
- **Revocation**: Invalidated on logout

### Data Storage
- **localStorage**: Used for convenience (not httpOnly cookies)
- **XSS Protection**: Sanitize all user inputs
- **HTTPS Only**: All auth endpoints require HTTPS in production

---

## Frontend Implementation Notes

### State Management
- Track authentication state globally (context or store)
- Persist user data in localStorage
- Clear all auth data on logout

### Silent Refresh
- Check token expiration on app initialization
- Refresh token 5 minutes before expiration
- Handle refresh failures gracefully

### Loading States
- Show spinner during OTP send
- Disable inputs during verification
- Display progress indicators

---

## Testing Requirements

### Unit Tests
- Email validation logic
- OTP format validation
- Token storage/retrieval
- Token expiration checks

### Integration Tests
- Full OTP flow (send → verify → login)
- Token refresh flow
- Logout flow
- Error handling scenarios

### E2E Tests
- New user registration flow
- Returning user login flow
- Session persistence across page reload
- Silent token refresh

---

## Performance Considerations

- OTP delivery typically < 30 seconds
- Token verification < 500ms
- Silent refresh < 200ms
- Client-side validation (no server round-trip)

---

## Related Documents

- [Product Requirements Document](../01-product-requirements.md)
- [Authentication Service](../../04-Backend/services/auth_service.md)
- [API Reference: Auth Routes](../../07-API-Reference/auth-endpoints.md)
- [Database Schema: users](../../03-Database/tables/users.md)
- [Frontend: Login Component](../../06-Frontend/components/login.md)

---

## Source Files

- Backend: `c:\Users\James\Documents\Coding\LinguaLoop\WebApp\routes\auth.py`
- Frontend: `c:\Users\James\Documents\Coding\LinguaLoop\WebApp\templates\login.html`
- Middleware: `c:\Users\James\Documents\Coding\LinguaLoop\WebApp\middleware\auth.py`
- Service: `c:\Users\James\Documents\Coding\LinguaLoop\WebApp\services\auth_service.py`
- Validation: `c:\Users\James\Documents\Coding\LinguaLoop\WebApp\utils\validation.py`

---

## Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2026-02-14 | 1.0 | Initial specification | Backend Team |
