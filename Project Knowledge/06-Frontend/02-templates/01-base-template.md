# Base Template (`base.html`)

> **Source file:** `templates/base.html` (409 lines)

## Purpose

`base.html` is the root layout template that every page extends. It provides the HTML skeleton, navbar, footer, global JavaScript configuration, the `authFetch()` wrapper, the report modal, and flash message rendering.

---

## Template Blocks

Child templates override these blocks to inject page-specific content:

| Block | Line | Default Value | Description |
|-------|------|---------------|-------------|
| `title` | 8 | `LinguaDojo` | Page `<title>` |
| `extra_css` | 49 | empty | Additional `<style>` or `<link>` tags in `<head>` |
| `body_class` | 53 | `bg-slate-50` | CSS classes on `<body>` |
| `main_class` | 139 | `container py-4` | CSS classes on `<main>` |
| `content` | 140 | empty | Main page content |
| `extra_js` | 407 | empty | Additional `<script>` tags before `</body>` |

## Template Variables

| Variable | Type | Effect |
|----------|------|--------|
| `hide_navbar` | bool | When truthy, the entire `<nav>` is hidden (lines 57-124) |
| `hide_footer` | bool | When truthy, the `<footer>` is hidden (lines 143-159) |
| `current_user` | object | Used to build the logo href; falls back to `/` if absent (line 62) |
| `current_year` | string | Displayed in footer copyright; defaults to `'2025'` (line 153) |

---

## Head Section (Lines 1-52)

### External Dependencies

| Resource | CDN URL | Line |
|----------|---------|------|
| Bootstrap 5.3.2 CSS | `cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css` | 10 |
| Font Awesome 6.5.1 | `cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css` | 11 |
| `styles.css` | Local static file | 12 |

### Inline Styles (Lines 13-47)

The `.navbar-language-indicator` component is styled inline in `<head>`. It shows the currently selected language flag and name in the navbar. Includes a responsive breakpoint at 768px.

### Favicon (Line 51)

Uses an inline SVG data URI with a graduation cap emoji as the favicon.

---

## Navbar (Lines 57-123)

The navbar is a sticky-top bar with the following structure:

```
[Logo: "LinguaDojo"] [Language Indicator] ... [Nav Links] [User Dropdown]
```

### Navigation Links (Lines 70-88)

| Link | URL | Active When | Visibility |
|------|-----|-------------|------------|
| Language Selection | `url_for('index')` | `request.endpoint == 'home'` | Desktop only (`d-none d-md-flex`) |
| Browse Tests | `url_for('tests')` | `request.endpoint == 'test_list'` | Desktop only |
| Report (flag icon) | Opens `#reportModal` | -- | Desktop only |

### Language Indicator (Lines 65-68)

Three elements inside `#navLanguageIndicator`:
- `#navLanguageFlag` -- Flag emoji
- `#navLanguageName` -- Language name text
- Container starts hidden (`display: none`), shown by `updateLanguageIndicator()` on DOMContentLoaded

### User Dropdown Menu (Lines 89-120)

A Bootstrap dropdown triggered by a user icon button (`#userMenuButton`):

| Item | Action |
|------|--------|
| Profile | Links to `/profile` |
| Logout | Triggers `#logout-btn` click handler |

---

## Flash Messages (Lines 126-137)

Renders Flask flash messages using `get_flashed_messages(with_categories=true)`. Each message is a Bootstrap dismissible alert with the category as the alert type (e.g., `alert-success`, `alert-danger`).

---

## Footer (Lines 143-159)

A two-column footer with:
- Left: Logo and tagline
- Right: Copyright notice with `current_year`

Conditionally hidden via `hide_footer` variable.

---

## Scripts Section (Lines 161-407)

### External Scripts

| Script | Line |
|--------|------|
| Bootstrap 5.3.2 JS Bundle | 161 |
| `utils.js` | 162 |

### Global Config: `window.LINGUADOJO` (Lines 166-170)

```javascript
window.LINGUADOJO = {
    API_BASE: "{{ url_for('index') }}",
    JWT_TOKEN: localStorage.getItem('jwt_token'),
    USER_DATA: JSON.parse(localStorage.getItem('user_data') || '{}')
};
```

Provides a global namespace for configuration. Available to all page scripts.

### `window.authFetch()` (Lines 180-246)

Authenticated fetch wrapper with automatic token refresh. This is the primary function for making API calls from any page.

**Signature:** `async authFetch(url, options = {}) -> Promise<Response>`

**Behavior:**

1. Reads `jwt_token` from `localStorage`
2. Sets `Authorization: Bearer <token>` and `Content-Type: application/json` headers
3. Makes the fetch request
4. If response is **401 Unauthorized**:
   a. Reads `refresh_token` from `localStorage`
   b. POSTs to `/api/auth/refresh-token` with `{ refresh_token }`
   c. On success: stores new `jwt_token` and `refresh_token`, updates `window.LINGUADOJO.JWT_TOKEN`, retries the original request
   d. On failure: clears all tokens from `localStorage`, redirects to `/login`
5. If no refresh token exists: clears tokens, redirects to `/login`
6. Returns the response object

### `updateLanguageIndicator()` (Lines 248-276)

Reads `selectedLanguage` from `localStorage` (expects a JSON object with `.code` and `.name`), maps the code/name to a flag emoji using an internal `flagMap`, and displays the indicator in the navbar.

**Flag mappings:** `en`, `zh`, `ja`, `ko`, `fr` and their full names (English, Chinese, Japanese, Korean, French).

### DOMContentLoaded Handler (Lines 278-360)

Runs on page load and sets up three features:

#### 1. Language Indicator Update (Line 279)
Calls `updateLanguageIndicator()`.

#### 2. Logout Handler (Lines 281-292)
Attaches a click handler to `#logout-btn` that:
1. Removes `jwt_token`, `refresh_token`, and `user_data` from `localStorage`
2. Redirects to `/login`

#### 3. Report Submission (Lines 294-358)

**Submit handler** (`#submitReportBtn`, lines 297-343):
1. Validates category is selected and description is at least 10 characters
2. Disables button and shows spinner
3. POSTs to `/api/reports/submit` with:
   - `report_category` -- Selected category value
   - `description` -- User description text
   - `current_page` -- `window.location.pathname`
   - `test_id` -- Extracted from URL path via regex, or `null`
   - `user_agent` -- Browser user agent
   - `screen_resolution` -- `{width}x{height}`
4. On success: hides form, shows success alert, auto-closes modal after 1.5s
5. On error: shows error message, re-enables button

**Modal reset handler** (`hidden.bs.modal`, lines 348-358):
Resets the form, re-shows form elements, hides success/error alerts, re-enables submit button.

---

## Report Modal (Lines 363-405)

A centered Bootstrap modal (`#reportModal`) with a form containing:

### Report Categories (6 options, lines 376-383)

| Value | Label (English / Chinese) |
|-------|---------------------------|
| `test_answer_incorrect` | Test answer incorrect / ... |
| `test_load_error` | Test won't load / ... |
| `website_crash` | Website crashed / ... |
| `improvement_idea` | Improvement idea / ... |
| `audio_quality` | Audio quality poor / ... |
| `other` | Other / ... |

### Form Elements

| Element | ID | Validation |
|---------|-----|-----------|
| Category select | `reportCategory` | `required` |
| Description textarea | `reportDescription` | `required`, `minlength="10"`, 4 rows |
| Success alert | `reportSuccess` | Hidden by default (`d-none`) |
| Error alert | `reportError` | Hidden by default (`d-none`) |
| Submit button | `submitReportBtn` | In `#reportFooter` |

---

## Accessibility Features

| Feature | Location |
|---------|----------|
| Skip to content link | Line 55 (`visually-hidden-focusable`) |
| `aria-label` on user menu button | Line 95 |
| `aria-labelledby` on dropdown menu | Line 100 |
| `role="alert"` and `aria-live="polite"` on flash messages | Line 128 |
| `aria-hidden="true"` on report modal | Line 364 |

---

## Related Documents

- [../01-frontend-overview.md](../01-frontend-overview.md) -- Frontend architecture overview
- [02-page-reference.md](02-page-reference.md) -- Child template documentation
- [../03-static-assets.md](../03-static-assets.md) -- styles.css and utils.js reference
- [../04-client-auth-flow.md](../04-client-auth-flow.md) -- Full authentication flow
