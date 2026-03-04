# Static Assets Reference

> **Source files:** `static/css/styles.css` (666 lines), `static/js/utils.js` (316 lines)

Both files are loaded by `base.html` and available on every page.

---

## `styles.css` -- Design System

### CSS Custom Properties (Lines 7-47)

The design system is built on CSS custom properties defined in `:root`:

#### Primary Colors

| Variable | Value | Usage |
|----------|-------|-------|
| `--primary` | `#1e40af` | Buttons, links, active states, badges |
| `--primary-hover` | `#1e3a8a` | Button hover states |
| `--success` | `#059669` | Correct answers, success alerts |
| `--success-hover` | `#047857` | Success button hover |
| `--danger` | `#dc2626` | Incorrect answers, error alerts |
| `--danger-hover` | `#b91c1c` | Danger button hover |
| `--warning` | `#ea580c` | Warning alerts, advanced difficulty |
| `--info` | `#0284c7` | Info alerts, progress bars |
| `--accent` | `#f59e0b` | Level badges, milestones |

#### Neutral Slate Scale (10 stops)

| Variable | Value | Typical Usage |
|----------|-------|---------------|
| `--slate-900` | `#0f172a` | Headings |
| `--slate-800` | `#1e293b` | H2 headings |
| `--slate-700` | `#334155` | H3 headings, body text emphasis |
| `--slate-600` | `#475569` | Default body text |
| `--slate-500` | `#64748b` | Labels, secondary text |
| `--slate-400` | `#94a3b8` | Subtle borders on hover |
| `--slate-300` | `#cbd5e1` | Input borders, dividers |
| `--slate-200` | `#e2e8f0` | Card borders, separators |
| `--slate-100` | `#f1f5f9` | Secondary button background |
| `--slate-50` | `#f8fafc` | Page background |

#### Semantic Backgrounds

| Variable | Value | Usage |
|----------|-------|-------|
| `--success-bg` | `#d1fae5` | Correct answer background |
| `--danger-bg` | `#fee2e2` | Incorrect answer background |
| `--warning-bg` | `#fed7aa` | Warning alert background |
| `--info-bg` | `#e0f2fe` | Info alert background |
| `--selected-bg` | `#dbeafe` | Selected answer/card background |

#### Shadows

| Variable | Value |
|----------|-------|
| `--shadow-sm` | `0 1px 2px rgba(15, 23, 42, 0.05)` |
| `--shadow-md` | `0 4px 12px rgba(15, 23, 42, 0.08)` |
| `--shadow-lg` | `0 20px 60px rgba(15, 23, 42, 0.15)` |

#### Transitions

| Variable | Value |
|----------|-------|
| `--transition-fast` | `all 0.15s ease` |
| `--transition-base` | `all 0.2s ease` |
| `--transition-slow` | `all 0.3s ease` |

### Component Styles

#### Base & Global (Lines 49-77)
- Body: `background: var(--slate-50)`, `color: var(--slate-600)`, `font-size: 16px`
- Headings: `color: var(--slate-900)`, `font-weight: 600`
- H1: 28px/700, H2: 24px, H3: 20px
- Links: `color: var(--primary)`, underline on hover

#### Buttons (Lines 82-173)
- `.btn` -- Base: `border-radius: 8px`, `padding: 12px 24px`, `font-weight: 600`
- `.btn-primary` -- `var(--primary)`, hover lifts 1px with blue shadow
- `.btn-success` -- `var(--success)`, hover lifts 1px with green shadow
- `.btn-secondary` -- `var(--slate-100)` background, `var(--slate-200)` border
- `.btn-danger` -- `var(--danger)` with red shadow
- `.btn-icon` -- 40px circle, transparent background
- `.btn:disabled` -- `var(--slate-300)`, `opacity: 0.6`, `cursor: not-allowed`

#### Cards (Lines 178-244)
- `.card` -- `border-radius: 12px`, `border: 1px solid var(--slate-200)`, `shadow-sm`
- `.question-card` -- White, 2px border, 24px padding
- `.answer-option` -- 2px border, 16px padding, 12px margin-bottom
  - `.selected` -- 3px primary border, selected-bg, `scaleIn` animation
  - `.correct` -- 4px green left border, success-bg
  - `.incorrect` -- 4px red left border, danger-bg
- `.dashboard-card` -- White, 8px radius, 20px padding
- `.audio-player` -- slate-50 background, 12px radius

#### Forms (Lines 249-304)
- `.form-control` -- 2px slate-300 border, 8px radius, 12px/16px padding
  - Focus: primary border, 3px blue shadow ring
  - Invalid: danger border with red shadow ring
- `.form-check-input` -- 20px square, 2px slate-300 border
  - Checked: primary background and border

#### Navigation (Lines 309-348)
- `.navbar` -- White, bottom border, 16px padding, shadow-sm
- `.nav-link` -- slate-500 text, 500 weight, 3px transparent bottom border
  - `.active` -- primary color, primary bottom border
- `.breadcrumb` -- Transparent, 14px font

#### Progress Indicators (Lines 353-397)
- `.progress` -- 8px height, slate-200 background
- `.progress-bar` -- Linear gradient primary-to-info
- `.milestone` -- 16px circle; `.completed` gets accent color with glow
- `.spinner` -- 24px, 3px border, primary top color, `spin` animation
- `.spinner-lg` -- 40px variant

#### Alerts (Lines 402-434)
- All alerts: 8px radius, 16px padding, 4px left border
- Success: green-on-green
- Danger: red-on-red
- Warning: orange-on-orange
- Info: blue-on-blue

#### Badges & Tags (Lines 439-492)
- `.badge` -- 6px/12px padding, 14px font, 6px radius
- `.badge-score` -- Success background/color
- `.tag-easy` / `.tag-medium` / `.tag-hard` -- 4px/10px padding, 12px font
- `.badge-level` -- Gradient accent background, 20px radius, glow shadow
  - `.level-up` -- `burst` animation

#### Modals (Lines 497-514)
- `.modal-content` -- No border, 12px radius, large shadow
- `.modal-backdrop` -- Dark slate overlay, 2px blur

#### Audio Player (Lines 519-560)
- `.audio-play-btn` -- 56px circle, primary background
- `.waveform-bar` -- 3px wide bars; `.active` turns blue
- `.audio-timer` -- 14px, tabular-nums

#### Stats (Lines 565-588)
- `.stat-number` -- 32px/700 weight
- `.stat-label` -- 14px uppercase with letter spacing
- `.chart-bar` -- Gradient primary-to-info, top-rounded

### Animations (Lines 593-619)

| Animation | Keyframes | Usage |
|-----------|-----------|-------|
| `spin` | 0deg to 360deg | Spinners |
| `pulse` | Scale 1 to 1.2 and back | Milestone completion |
| `slideUp` | 20px down + opacity to normal | Slide-in entrance |
| `burst` | Scale/rotate wobble | Level-up badge |
| `scaleIn` | Scale 0.98 to 1 | Selected answers/cards |

### Utility Classes (Lines 624-666)

| Class | Property |
|-------|----------|
| `.text-slate-900/600/500` | Color utilities |
| `.bg-slate-50/100` | Background utilities |
| `.border-slate-200` | Border color |
| `.shadow-sm/md` | Box shadow |
| `.transition-fast/base` | Transition timing |
| `.animate-slide-up` | `slideUp 0.3s ease` |
| `.logo` | 32px/700 primary text |
| `.tagline` | 14px slate-500 text |
| `.login-container` | 100vh min-height |
| `.login-card` | No border, 12px radius |

---

## `utils.js` -- Shared Utility Library

### Constants (Lines 10-31)

#### `ELO_RANGES` (Lines 13-19)

```javascript
const ELO_RANGES = {
    BEGINNER:     { min: 0,    max: 1199, label: 'Beginner',     class: 'badge-beginner' },
    ELEMENTARY:   { min: 1200, max: 1399, label: 'Elementary',   class: 'badge-elementary' },
    INTERMEDIATE: { min: 1400, max: 1599, label: 'Intermediate', class: 'badge-intermediate' },
    ADVANCED:     { min: 1600, max: 1799, label: 'Advanced',     class: 'badge-advanced' },
    EXPERT:       { min: 1800, max: 9999, label: 'Expert',       class: 'badge-expert' }
};
```

#### `LANGUAGE_FLAGS` (Lines 22-28)

Maps language codes (`en`, `zh`, `ja`, `ko`, `fr`), alternate codes (`cn`, `jp`), and full names (both cases) to flag emojis.

#### `DEBUG` (Line 31)

Boolean flag. When `false`, `debugLog()` calls are silently ignored. Set to `true` during development.

### Security (Lines 36-47)

#### `escapeHtml(text) -> string`
Prevents XSS by creating a temporary DOM element, setting `textContent`, and reading `innerHTML`. Returns empty string for falsy input.

### Difficulty / ELO Helpers (Lines 52-94)

#### `getDifficultyLabel(elo) -> string`
Returns: `'Beginner'` (< 1200), `'Elementary'` (< 1400), `'Intermediate'` (< 1600), `'Advanced'` (< 1800), `'Expert'` (>= 1800).

#### `getDifficultyInfo(elo) -> { label, class, color }`
Returns full difficulty metadata combining `getDifficultyLabel()` and `getDifficultyColor()`.

#### `getDifficultyColor(level) -> string`
| Level | Color |
|-------|-------|
| Beginner | `#22c55e` |
| Elementary | `#84cc16` |
| Intermediate | `#eab308` |
| Advanced | `#f97316` |
| Expert | `#ef4444` |
| Default | `#6b7280` |

### Language Helpers (Lines 100-107)

#### `getLanguageFlag(langCode) -> string`
Looks up `LANGUAGE_FLAGS[langCode]`, returns globe emoji as fallback.

### DOM Helpers (Lines 113-138)

#### `show(el)`
Removes `d-none` class. Accepts an HTMLElement or CSS selector string.

#### `hide(el)`
Adds `d-none` class. Accepts an HTMLElement or CSS selector string.

#### `toggle(el, visible)`
Calls `show()` or `hide()` based on boolean `visible` parameter.

### API Helpers (Lines 144-199)

#### `getAuthHeaders() -> object`
Returns `{ 'Content-Type': 'application/json', 'Authorization': 'Bearer <token>' }` using token from `localStorage` or `LINGUADOJO.jwt_token`.

#### `apiRequest(url, options) -> Promise<object>`
General-purpose authenticated fetch. JSON-stringifies object bodies. Throws on non-OK responses with error message from response body.

#### `apiGet(url) -> Promise<object>`
Shorthand for `apiRequest(url, { method: 'GET' })`.

#### `apiPost(url, body) -> Promise<object>`
Shorthand for `apiRequest(url, { method: 'POST', body })`.

### Storage Helpers (Lines 205-227)

#### `getStorageItem(key, defaultValue = null) -> any`
Reads from `localStorage` and JSON-parses. Returns `defaultValue` on missing key or parse error.

#### `setStorageItem(key, value)`
JSON-stringifies and stores in `localStorage`.

### Logging (Lines 233-241)

#### `debugLog(...args)`
Calls `console.log()` only when `DEBUG === true`. Silent in production.

### Date/Time Helpers (Lines 247-270)

#### `formatTime(seconds) -> string`
Formats seconds to `M:SS` (e.g., `3:05`).

#### `formatDate(date) -> string`
Formats a date string or Date object to US locale short format (e.g., `Feb 13, 2026`).

### Global Export (Lines 277-315)

All functions and constants are exposed via `window.LinguaUtils`:

```javascript
window.LinguaUtils = {
    ELO_RANGES, LANGUAGE_FLAGS, DEBUG,
    escapeHtml,
    getDifficultyLabel, getDifficultyInfo, getDifficultyColor,
    getLanguageFlag,
    show, hide, toggle,
    getAuthHeaders, apiRequest, apiGet, apiPost,
    getStorageItem, setStorageItem,
    debugLog,
    formatTime, formatDate
};
```

All functions are also available as bare globals (not namespaced) since the file does not use ES modules.

---

## Related Documents

- [01-frontend-overview.md](01-frontend-overview.md) -- Architecture overview
- [02-templates/01-base-template.md](02-templates/01-base-template.md) -- Base template (loads both files)
- [04-client-auth-flow.md](04-client-auth-flow.md) -- Auth flow using these utilities
