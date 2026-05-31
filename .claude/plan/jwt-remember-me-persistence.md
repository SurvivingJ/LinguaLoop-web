# Plan: Fix "Remember me" JWT persistence across browser restarts

**Goal:** When the user ticks "Remember this device", their session survives a full
browser close/reopen on **desktop and mobile**, with no forced re-login, until the
180-day device credential genuinely expires.

**Status:** awaiting approval — no code changed yet.

---

## How it's supposed to work (and where it breaks)

Three credentials cooperate:

- **Access token** (`jwt_token`) — short-lived (~1h Supabase token). Stored in
  `localStorage` when remembered, `sessionStorage` otherwise.
- **Refresh cookie** (`lingualoop_refresh`) — HttpOnly, path `/api/auth`, 30 days
  *only when written persistently*.
- **Device cookie** (`lingualoop_device`) — HttpOnly, path `/api/auth`, 180 days.

On reopen after the access token expires, the browser must silently renew it via
the refresh cookie (`/api/auth/refresh-token`) or, failing that, the device cookie
(`/api/auth/device-restore`). Tracing that path turned up the gaps below.

---

## Root-cause candidates (priority order)

### RC-1 — Silent `remembered=false` → token saved to `sessionStorage` (most likely)
`verify-otp` wraps `device_service.issue_device_token(...)` in a try/except that
**logs and continues with `remembered=False`** (`routes/auth.py:180-193`).
`login.html:317` then keys storage off `data.remembered`: false → the access token
goes to **`sessionStorage`**, which the browser **wipes on close**. Next visit:
no token in storage, no device cookie was set → bounce to `/login`. This is the
*exact* reported symptom.

Most common trigger: the `trusted_devices` table is **not applied** in the
environment being tested (the insert throws, gets swallowed). Migration file
exists (`migrations/trusted_devices.sql`) but may not be applied to the live
Supabase project.

### RC-2 — `refresh-token` downgrades the persistent refresh cookie to a session cookie
`routes/auth.py:252` always calls `_set_refresh_cookie(..., persistent=False)`.
So the **first** silent refresh after a restart converts the 30-day cookie into a
session cookie that dies on the **next** close. Persistence then depends entirely
on device-restore — which is impaired whenever RC-1 is in play.

### RC-3 — Stranded persistent refresh cookie on the no-token bootstrap path
When remembered but device-token issuance failed (RC-1), `verify-otp` still sets a
**persistent** refresh cookie (`persistent=remember_device`, `routes/auth.py:201-203`).
But the `base.html` head-script, when it finds no `jwt_token` in storage, only tries
`/api/auth/device-restore` — **never `/api/auth/refresh-token`**. So the one
persistent credential that *was* written is never used → bounce to `/login`.

### RC-4 — Stale-token blind spot on page load
When remembered, `localStorage` keeps an **expired** access token across restarts.
The `base.html` bootstrap treats "token present" as "logged in" (`base.html:49-51`)
and reveals the page without refreshing. Any protected page that fetches with a raw
`fetch` + stale token (instead of `authFetch`) gets a 401 and can bounce to `/login`,
looking like "didn't persist".

---

## Step 0 — Diagnose before fixing (confirm which RC is live)

1. **Confirm the table exists** in the live Supabase project (Supabase MCP
   `list_tables`, or `select count(*) from trusted_devices`). If missing → apply
   `migrations/trusted_devices.sql`. This alone likely resolves RC-1.
2. **Grep server logs** for `Failed to issue device token` — presence confirms RC-1.
3. **Browser devtools after a remembered login:**
   - Application → Cookies: `lingualoop_device` and `lingualoop_refresh` present,
     `HttpOnly` true, `Expires` a real date (not `Session`).
   - Application → Storage: `jwt_token` in **localStorage** (not sessionStorage).
   - Network: `verify-otp` response body `remembered: true`.

Record which RCs are confirmed; the fixes below are independent and safe to ship
together regardless.

---

## Step 1 — Server: keep the refresh cookie persistent for remembered devices (RC-2)
**File:** `routes/auth.py`, `refresh_token()` (~line 249-252).

The device cookie rides on every `/api/auth/*` request (path match), so its presence
is a reliable "this is a remembered device" signal. Make the rotated refresh cookie
persistent iff the device cookie is present:

```python
new_refresh = result.pop('refresh_token', None)
response = make_response(jsonify(result), 200)
if new_refresh:
    persistent = bool(request.cookies.get(Config.DEVICE_COOKIE_NAME))
    _set_refresh_cookie(response, new_refresh, persistent=persistent)
return response
```

**Acceptance:** after a remembered login, calling `/api/auth/refresh-token` returns a
`Set-Cookie` for `lingualoop_refresh` with a `Max-Age`/`Expires` (not a session cookie).

## Step 2 — Client: bootstrap tries refresh-token *and* device-restore (RC-3)
**File:** `templates/base.html` head-script (~line 101-126).

When no `jwt_token` is in storage, attempt `/api/auth/refresh-token` first (uses the
persistent refresh cookie), then fall back to `/api/auth/device-restore`, then bounce.
Both are HttpOnly-cookie exchanges invisible to JS, so we must try them, not infer.

**Acceptance:** a browser with only a valid `lingualoop_refresh` cookie (no device
cookie, no storage token) lands on a protected page and is restored without `/login`.

## Step 3 — Client: persist on the user's intent, not just `data.remembered` (RC-1 mitigation)
**File:** `templates/login.html` (~line 317).

The server sets a **persistent refresh cookie whenever remember was checked**, even if
the device-token row failed. So storage tier should follow the checkbox, not only the
server's `remembered` flag:

```js
const persist = data.remembered || rememberDevice;
const store = persist ? localStorage : sessionStorage;
const otherStore = persist ? sessionStorage : localStorage;
```

This keeps the access token in `localStorage` so it survives restart, and the
persistent refresh cookie can renew it even when RC-1 degrades the device row.

**Acceptance:** with `remember-device` checked, `jwt_token` lands in `localStorage`
even if the `verify-otp` response has `remembered:false`.

## Step 4 — Client: proactively refresh an expired token on load (RC-4)
**File:** `templates/base.html` bootstrap + `authFetch`.

Decode the stored access token's `exp` (base64 of the JWT payload). If it's
absent/expired, run the refresh→device-restore chain on page load *before* revealing
content, instead of waiting for the first `authFetch` 401. Closes the gap for pages
that use raw `fetch`.

**Acceptance:** opening a protected page with an expired-but-present `localStorage`
token silently obtains a fresh token with no 401 flash and no `/login` bounce.

## Step 5 — Tests
**File:** `tests/test_remember_me_flow.py` (extend).

- Server: `refresh-token` with a device cookie present → persistent `Set-Cookie`;
  without it → session cookie. (RC-2)
- Server/sanity: `verify-otp` with `remember_device:true` sets a persistent
  `lingualoop_refresh` cookie even when `issue_device_token` raises. (RC-1/RC-3)
- Rendered-HTML assertion: `base.html` references `/api/auth/refresh-token` in the
  no-token bootstrap path, before the `/login` redirect. (RC-3)
- Rendered-HTML assertion: `login.html` storage tier keys off the checkbox intent. (RC-1)

## Step 6 — Manual verification (desktop + mobile)
Login with remember ticked → fully quit the browser (not just the tab) → reopen
directly to a protected page after >1h. Repeat the close/reopen **twice** (catches the
RC-2 second-restart regression). Confirm no `/login` bounce on either platform.

---

## Files to modify
- `routes/auth.py` — Step 1 (refresh cookie persistence).
- `templates/base.html` — Steps 2 & 4 (bootstrap refresh+restore, proactive refresh).
- `templates/login.html` — Step 3 (persist on intent).
- `tests/test_remember_me_flow.py` — Step 5.
- `migrations/trusted_devices.sql` — apply to live env if Step 0 shows it missing.

## Out of scope / risks
- Not changing the security model (HttpOnly cookies, rotation, reuse detection stay).
- `request.is_secure` must be correct in prod (ProxyFix `x_proto=1` is already set in
  `app.py:60`); verify the proxy sends `X-Forwarded-Proto: https` so cookies get the
  `Secure` flag. Not a blocker for sending cookies, but confirm.
