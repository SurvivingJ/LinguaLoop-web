# Page Template Reference

> **Source files:** `templates/login.html`, `templates/language_selection.html`, `templates/test_list.html`, `templates/test_preview.html`, `templates/test.html`, `templates/profile.html`, `templates/onboarding.html`

All templates extend `base.html`. This document covers each child template's structure, JavaScript behavior, and API interactions.

---

## 1. `login.html` (370 lines)

**Route:** `/login`
**Layout overrides:** `hide_navbar = true`, `body_class = bg-slate-50`

### Purpose

Passwordless authentication using a two-step OTP (one-time password) flow. Users enter their email, receive a 6-digit verification code, and are logged in upon verification.

### UI States

The page has three mutually exclusive views, toggled via `d-none` class:

| State | Element ID | Visible When |
|-------|-----------|--------------|
| Email input | `email-step` | Initial state |
| OTP input | `otp-step` | After OTP sent successfully |
| Loading spinner | `loading` | During API calls |
| Error alert | `error-alert` | On any error (overlays current step) |

### Step 1: Email Submission (Lines 209-246)

1. User enters email and submits `#email-form`
2. POSTs to `/api/auth/send-otp` with `{ email, is_registration: true }`
3. On success: transitions to OTP step, displays email in `#email-display`
4. On failure: returns to email step, shows error

### Step 2: OTP Verification (Lines 249-301)

1. User enters 6-digit code in `#otp` input
2. **Auto-submit:** When input reaches 6 digits, the form auto-submits (lines 347-362) via `requestSubmit()` with fallback to dispatching a submit event
3. POSTs to `/api/auth/verify-otp` with `{ email, otp_code }`
4. On success:
   - Stores `jwt_token` in `localStorage` (line 277)
   - Stores `user_data` as JSON string (line 278)
   - Stores `refresh_token` if present (lines 281-283)
   - **Redirect logic** (lines 286-290):
     - New users (`totalTestsTaken === 0`): redirect to `/welcome`
     - Returning users: redirect to `/language-selection`
5. On failure: clears OTP input, shows error

### OTP Input Features

| Feature | Line | Behavior |
|---------|------|----------|
| Numeric-only filter | 349 | Strips non-digit characters on input |
| Auto-submit on 6 digits | 352-361 | Triggers form submission automatically |
| Centered large font | CSS `.otp-input` | `font-size: 20px`, `letter-spacing: 8px` |
| `inputmode="numeric"` | 114 | Shows numeric keyboard on mobile |
| `autocomplete="one-time-code"` | 115 | Browser auto-fill for SMS codes |

### Additional Controls

| Control | Behavior |
|---------|----------|
| Back button (`#back-btn`, line 304) | Returns to email step, clears OTP |
| Resend button (`#resend-btn`, lines 310-344) | Re-sends OTP, shows pulse animation on info alert |
| Already logged in check (lines 365-367) | If `jwt_token` exists in `localStorage`, immediately redirects to `/language-selection` |

---

## 2. `language_selection.html` (179 lines)

**Route:** `/language-selection`

### Purpose

Allows the user to choose which language they want to practice. This selection determines which tests are shown on the test list page.

### Language Cards (Lines 27-52)

Three hardcoded language options:

| Language | `data-id` | Flag |
|----------|-----------|------|
| Chinese | `1` | Flag emoji |
| English | `2` | Flag emoji |
| Japanese | `3` | Flag emoji |

### Selection Behavior (Lines 129-176)

1. Clicking a card:
   - Removes `.selected` class and hides check icon from all cards
   - Adds `.selected` class and shows check icon on clicked card
   - Stores `{ id: <number> }` in local variable
   - Enables the continue button
2. Continue button (`#continue-btn`, lines 158-165):
   - Stores selected ID as `selectedLanguageId` in `localStorage`
   - Redirects to `{{ url_for('tests') }}`
3. On page load (lines 169-175):
   - Reads `selectedLanguageId` from `localStorage`
   - If found, programmatically clicks the matching card to restore selection

### Styling

Uses Bootstrap Icons (`bi bi-check-circle-fill`) for the check mark. The `.selected` state applies:
- `border-color: var(--primary)`
- `background: var(--selected-bg)`
- `scaleIn` animation (0.15s)

---

## 3. `test_list.html` (1152 lines)

**Route:** `/tests`

### Purpose

The main test browsing page. Displays recommended tests, a random test button, filters, and a grid of all available tests.

### Page Sections

| Section | Lines | Description |
|---------|-------|-------------|
| Page header | 463-466 | Title and subtitle |
| Recommended tests | 468-510 | 3 skeleton placeholders + random test button |
| Filter section | 512-564 | Test type and difficulty dropdowns |
| Content area | 567-609 | Loading, error, empty states + test grid |

### Filter Controls (Lines 516-551)

| Filter | ID | Options | Behavior |
|--------|----|---------|----------|
| Test Type | `test-type` | All, Reading, Listening, Dictation | `onchange="applyFilters()"` |
| Difficulty | `difficulty` | All + Levels 1-9 with ELO ranges | `onchange="applyFilters()"` |
| Reset button | -- | -- | `onclick="resetFilters()"` |

### ELO Range Mapping (Lines 627-640)

Client-side difficulty levels map to ELO ranges:

| Level | Label | ELO Min | ELO Max |
|-------|-------|---------|---------|
| 1 | Beginner | 0 | 1200 |
| 2 | Elementary | 1200 | 1300 |
| 3 | Intermediate- | 1300 | 1400 |
| 4 | Intermediate | 1400 | 1500 |
| 5 | Intermediate+ | 1500 | 1600 |
| 6 | Advanced- | 1600 | 1700 |
| 7 | Advanced | 1700 | 1800 |
| 8 | Advanced+ | 1800 | 1900 |
| 9 | Expert | 1900 | 9999 |

### Test Loading (`loadTests()`, Lines 825-899)

1. Reads `jwt_token` and `selectedLanguageId` from `localStorage`
2. If missing: redirects to `/login` or `/language-selection`
3. GETs `/api/tests?language_id=<id>` with auth header
4. On success: calls `displayTests(data.tests)`
5. `displayTests()` applies client-side ELO filtering based on current filter values

### Test Card Structure (`createTestCard()`, Lines 711-757)

Each card displays:
- Title (with HTML escaping)
- Difficulty badge (beginner/elementary/intermediate/advanced/expert)
- Custom/Featured badges (conditional)
- Language code, ELO rating, attempt count
- Topic description (if available)
- Clicking navigates to `/test/<slug>/preview?type=<testType>`

### Recommended Tests (Lines 987-1128)

| Function | Description |
|----------|-------------|
| `loadRecommendedTests()` | GETs `/api/tests/recommended?language_id=<id>`, replaces skeleton cards |
| `displayRecommendedTests()` | Creates up to 3 recommended cards before the random test button |
| `createRecommendedCard()` | Builds card with type badge, title, difficulty, ELO, "Start Test" button |
| `showRecommendedEmpty()` | Shows "Complete a few tests" message in first skeleton slot |
| `showRecommendedError()` | Shows error with retry button |

### Random Test (`getRandomTest()`, Lines 904-963)

1. Gets current test type filter and language ID
2. GETs `/api/tests/random?language_id=<id>&skill_type=<type>`
3. Navigates directly to `/test/<slug>?type=<type>`
4. Shows spinning icon animation during loading

### Global Functions (Lines 1131-1137)

These functions are attached to `window` for inline event handlers:
`goToTestPreview`, `applyFilters`, `resetFilters`, `loadTests`, `getRandomTest`, `loadRecommendedTests`, `goToTestPreviewRecommended`

---

## 4. `test_preview.html` (689 lines)

**Route:** `/test/<slug>/preview`

### Purpose

Shows test metadata and lets the user select a test type (reading, listening, or dictation) before starting the test.

### Page Structure

| Section | Lines | Description |
|---------|-------|-------------|
| Breadcrumb | 180-186 | Home > Tests > Test Preview |
| Loading state | 189-194 | Spinner shown during data fetch |
| Error state | 197-203 | Error alert with "Back to Tests" button |
| Test info card | 208-244 | Title, language, topic, audio availability, difficulty, attempts |
| Test type selector | 247-289 | 3 radio buttons: Listening, Reading, Dictation (Coming Soon) |
| Difficulty display | 293-314 | Dynamic badge, ELO rating, stats |
| Start test button | 317-325 | Full-width primary button |

### Test Type Selector (Lines 251-288)

Three radio inputs styled as clickable cards:

| Option | ID | Icon | Notes |
|--------|----|------|-------|
| Listening | `listeningOption` | `bi-headphones` | Default selection |
| Reading | `readingOption` | `bi-book` | -- |
| Dictation | `dictationOption` | `bi-keyboard` | Shows "Coming Soon" badge; disables start button |

Each triggers `updateDifficultyDisplay(type)` on change.

### Initialization (`initializePage()`, Lines 629-674)

1. Parses slug from URL path and test type from query parameter (`?type=`)
2. Fetches test data and skill ratings in parallel via `Promise.all()`
   - `fetchTestData(slug)` -- GETs `/api/tests/<slug>`
   - `fetchSkillRatings(slug)` -- GETs `/api/tests/test/<slug>` (returns per-skill ELO data)
3. Populates test info, sets initial radio selection, updates difficulty display
4. Shows main content

### Difficulty Display (`updateDifficultyDisplay()`, Lines 517-583)

Updates the difficulty badge, ELO rating text, icon color, and stats based on the selected test type's ELO rating. Uses `getDifficultyInfo()` to map ELO to level/label/color:

| ELO Range | Level | Color |
|-----------|-------|-------|
| < 1200 | Beginner | `#059669` |
| 1200-1399 | Intermediate | `#d97706` |
| 1400-1599 | Advanced | `#ea580c` |
| 1600+ | Expert | `#dc2626` |

### Start Test (`startTest()`, Lines 588-624)

1. Stores test data and type in `sessionStorage`
2. Navigates to `/test/<slug>?type=<selectedTestType>`

---

## 5. `test.html` (1157 lines)

**Route:** `/test/<slug>?type=<reading|listening|dictation>`

### Purpose

The test-taking page. Supports three modes: reading (transcript shown), listening (audio player), and dictation (audio + text input). Renders questions, tracks answers, submits results, and displays scores.

### State Management (`testState`, Lines 482-495)

```javascript
const testState = {
    slug: null,
    testId: null,
    testType: null,          // 'reading', 'listening', 'dictation'
    testData: null,           // Full test object from API
    questions: [],            // Parsed question objects
    currentQuestionIndex: 0,
    answers: {},              // { questionId: selectedChoice }
    dictationText: '',
    startTime: null,
    isSubmitted: false,
    audioElement: null,
    playbackSpeed: 1.0
};
```

### Initialization Flow (Lines 500-536)

1. Parses `slug` from URL path and `type` from query parameter
2. Shows loading overlay
3. Calls `loadTestData()` -- GETs `/api/tests/test/<slug>`
4. Parses questions: extracts `id`, `text`, `choices` (JSON parsed), `correctAnswer`, `explanation`, `type`
5. Calls `initializeUI()` which branches by test type
6. Starts elapsed timer
7. Hides loading overlay

### Test Mode Initialization

| Mode | Function | Lines | What it does |
|------|----------|-------|--------------|
| Reading | `initializeReadingTest()` | 678-684 | Shows `#transcriptCard`, sets transcript text |
| Listening | `initializeListeningTest()` | 686-695 | Shows `#audioPlayerCard`, sets audio source, sets up player |
| Dictation | `initializeDictationTest()` | 697-709 | Shows both audio player and `#dictationCard` textarea |

### Audio Player (Lines 827-880)

Custom audio player with:

| Control | Element ID | Behavior |
|---------|-----------|----------|
| Play/Pause | `audioPlayBtn` | Toggles play/pause, updates icon |
| Progress bar | `audioProgressBar` | Click to seek; fill updates on `timeupdate` |
| Current time | `audioCurrentTime` | Updates every `timeupdate` event |
| Duration | `audioDuration` | Set on `loadedmetadata` |
| Speed control | `audioSpeedBtn` | Cycles through 1.0x, 1.25x, 1.5x, 0.75x |

### Question Rendering (Lines 714-797)

- `renderQuestions()` creates all question cards, shows only the first
- `createQuestionCard()` builds HTML with:
  - Question number badge
  - Answered indicator badge (conditional)
  - Question text
  - Answer options (A, B, C, D radio buttons)
  - Explanation (shown only after submission)
- `renderQuestionNavigation()` builds numbered nav buttons (`.question-nav-btn`)
  - `.active` = current question
  - `.answered` = answered question (green)
- `showQuestion(index)` hides all, shows target, updates nav

### Answer Selection (Lines 892-919)

Event delegation on `document` for `.answer-option` clicks:
1. Stores answer in `testState.answers[questionId]`
2. Highlights selected option (`.selected` class)
3. Updates radio button state
4. Refreshes navigation and progress

### Progress Tracking (`updateProgress()`, Lines 974-1001)

- For reading/listening: counts `Object.keys(testState.answers).length` vs `testState.questions.length`
- For dictation: checks if `dictationText.trim().length > 0`
- Updates progress bar width, progress text, answered count
- Enables submit button when all questions answered

### Test Submission (`submitTest()`, Lines 575-644)

1. Builds `responses` array:
   - For dictation: compares user text with transcript using 80% similarity threshold
   - For reading/listening: checks each answer against `correctAnswer`
2. Calculates `time_taken` in seconds
3. POSTs to `/api/tests/<slug>/submit` with `{ test_id, test_mode, responses, time_taken }`
4. On success: calls `showResults()`

### Levenshtein Similarity (Lines 1118-1155)

Two utility functions for dictation scoring:
- `calculateSimilarity(str1, str2)` -- Returns 0.0-1.0 similarity score
- `levenshteinDistance(str1, str2)` -- Classic dynamic programming implementation

The similarity formula: `(longerLength - editDistance) / longerLength`

### Results Display (`showResults()`, Lines 1020-1090)

1. Shows transcript for listening/dictation tests
2. Marks answers correct (green border-left) or incorrect (red border-left) using backend `question_results`
3. Replaces submit button with "Back to Test List" button (clones node to remove listeners)
4. Shows success message with score percentage
5. Scrolls to top

### Timer (`startTimer()`, Lines 1106-1116)

`setInterval` at 1-second intervals. Updates `#elapsedTime` with `MM:SS` format. Stops updating when `testState.isSubmitted` is true.

---

## 6. `profile.html` (534 lines)

**Route:** `/profile`

### Purpose

Displays user ELO ratings, test statistics, and test history organized by language and skill type.

### UI States

| State | Element ID | Shown When |
|-------|-----------|------------|
| Loading spinner | `loadingState` | Initial page load |
| Empty state | `emptyState` | No profile data (no ratings) |
| Profile content | `profileContent` | Data loaded successfully |

### Data Loading (`loadProfile()`, Lines 127-193)

1. GETs `/api/users/elo` with auth header
2. Stores `data.ratings` in `profileData`
3. If empty: shows empty state with "Browse Tests" button
4. If populated: renders language cards, auto-selects first language

### Language Selection (Lines 195-311)

- `renderLanguages()` generates language cards with flag emojis and skill counts
- `selectLanguage(langCode)` (exposed on `window`):
  - Highlights active language card
  - Shows stats section
  - Renders skill tabs
  - Auto-selects first skill

### Skill Tabs (`renderSkillTabs()`, Lines 228-274)

Dynamically generates Bootstrap nav tabs for each skill (e.g., Listening, Reading). Each tab triggers `selectSkill(skillCode)`.

### Stats Display (`renderStats()`, Lines 332-376)

Shows a card with:
- Skill name and large ELO rating number
- Skill emoji (headphones for listening, book for reading)
- Tests taken count
- Last test date (relative format)

### Test History (Lines 378-503)

| Feature | Description |
|---------|-------------|
| Pagination | 25 items per page via `HISTORY_PAGE_SIZE` |
| Caching | `testHistory` object keyed by `{languageId}_{testTypeId}` |
| API endpoint | `/api/tests/history?language_id=<id>&test_type_id=<id>&limit=25&offset=<n>` |
| Load more | `#loadMoreBtn` shown when a full page is returned |
| Score coloring | >= 80% green, >= 60% blue, >= 40% yellow, < 40% red |

### Helper Functions

| Function | Lines | Description |
|----------|-------|-------------|
| `getFlag(langCode)` | 505-518 | Maps language codes to flag emojis (supports short codes and full names) |
| `formatDate(dateStr)` | 520-529 | Relative date formatting: Today, Yesterday, N days ago, N weeks ago, or locale date |

---

## 7. `onboarding.html` (168 lines)

**Route:** `/welcome`
**Layout overrides:** `hide_navbar = true`, `body_class = bg-slate-50`

### Purpose

Welcome page shown to first-time users (those with `totalTestsTaken === 0`) after their first login. Introduces the platform and its features.

### Page Structure

| Section | Lines | Content |
|---------|-------|---------|
| Welcome header | 102-106 | Graduation cap emoji, "Welcome to LinguaDojo", tagline |
| What LinguaDojo Does | 109-116 | 3 bullet points about the platform |
| Feature cards | 119-147 | 3 cards in a row |
| How Tests Work | 150-157 | 3 bullet points about test mechanics |
| Get Started button | 160-163 | Links to `/language-selection` |

### Feature Cards (Lines 119-147)

| Card | Icon | Color | Description |
|------|------|-------|-------------|
| Report Button | `fa-flag` | Red (`#fef2f2`/`#dc2626`) | Explains how to report issues |
| Profile | `fa-user` | Blue (`#eff6ff`/`#2563eb`) | Explains ELO tracking |
| Language Selector | `fa-globe` | Green (`#f0fdf4`/`#16a34a`) | Explains language switching |

### No JavaScript

This template has no `{% block extra_js %}` -- it is a purely static informational page. The only interactive element is the "Get Started" link to `/language-selection`.

---

## Related Documents

- [01-base-template.md](01-base-template.md) -- Base template details
- [../01-frontend-overview.md](../01-frontend-overview.md) -- Architecture overview
- [../03-static-assets.md](../03-static-assets.md) -- CSS and JS utility reference
- [../04-client-auth-flow.md](../04-client-auth-flow.md) -- Authentication flow
