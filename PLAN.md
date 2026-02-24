# Plan: Interface Language Switching for LinguaDojo

## Current State Analysis

### HTML Templates Inventory (7 files with hardcoded English UI text)

| Template | Purpose | Hardcoded Strings (approx.) |
|---|---|---|
| `base.html` | Layout shell, navbar, footer, report modal | ~30 strings |
| `login.html` | Email/OTP login flow | ~20 strings |
| `language_selection.html` | Choose practice language | ~8 strings |
| `onboarding.html` | Welcome/feature tour | ~25 strings |
| `profile.html` | User stats & history | ~15 strings |
| `test.html` | Test-taking page | ~30 strings |
| `test_list.html` | Browse/filter tests | ~25 strings |
| `test_preview.html` | Test preview before starting | ~20 strings |

**Total: ~173 hardcoded English UI strings across 8 templates.**

### Key Observations

1. **No existing i18n infrastructure** — zero translation files, no locale detection, no language switching mechanism for the UI.
2. **Jinja2 templating** — the project uses Flask + Jinja2 (server-rendered HTML with `{% block %}` inheritance from `base.html`).
3. **Heavy client-side rendering** — many pages (profile, test_list, test, test_preview) build UI with JavaScript template literals containing hardcoded English strings.
4. **Dual-language hints already exist** — the report modal already shows bilingual text (e.g., "Report Issue / 报告问题"), suggesting there's demand for Chinese UI.
5. **`<html lang="en">` is hardcoded** in `base.html:2`.
6. **localStorage is already used** for user preferences (theme, selected language, JWT).
7. **The `language_selection.html` page selects the *practice* language** (what you're studying), not the UI/interface language — these are separate concepts.

---

## Proposed Approach: Client-Side i18n with JSON Translation Files

Given that much of the UI text is rendered client-side via JavaScript, a **client-side i18n system** is the most practical approach. It avoids needing to refactor the Flask backend and works seamlessly with both Jinja-rendered and JS-rendered text.

### Architecture

```
static/
  i18n/
    en.json          # English (default/fallback)
    zh.json          # Chinese (Simplified)
    ja.json          # Japanese
```

A lightweight `i18n-manager.js` module that:
- Loads the appropriate translation JSON on page load
- Exposes a `t('key')` function for JS-rendered text
- Scans the DOM for `data-i18n="key"` attributes on Jinja-rendered elements and replaces their text
- Persists the user's choice in `localStorage` (key: `interfaceLanguage`)
- Falls back to English if a key is missing

### Step-by-step Implementation Plan

#### Step 1: Create the translation file structure
- Create `static/i18n/en.json` with all ~173 UI strings keyed by a dot-notation path (e.g., `"nav.languageSelection"`, `"login.emailLabel"`, `"test.submitBtn"`).
- Create placeholder `static/i18n/zh.json` and `static/i18n/ja.json` with the same keys, translated.

#### Step 2: Build `static/js/i18n-manager.js`
Core module providing:
- `initI18n()` — loads the saved locale from `localStorage.interfaceLanguage` (default `'en'`), fetches the JSON file, caches it.
- `t(key, params)` — returns the translated string for a key, with optional interpolation (e.g., `t('test.progress', {current: 3, total: 5})` → "3 of 5 answered"). Falls back to English if the key is missing.
- `setLocale(lang)` — changes the interface language, saves to localStorage, and re-renders all `data-i18n` elements on the page.
- `applyTranslations()` — scans all elements with `data-i18n` attribute and sets their `textContent` (or `placeholder`, `aria-label`, etc.) from the loaded translations.

#### Step 3: Add a language switcher UI to the navbar (`base.html`)
- Add a globe/language dropdown next to the theme switcher in the navbar.
- Options: English, 中文, 日本語.
- Clicking an option calls `setLocale(lang)` and reloads translations without a full page refresh.

#### Step 4: Refactor Jinja-rendered strings in templates
For each template, replace hardcoded English text with `data-i18n` attributes:

**Before:**
```html
<a href="..." class="nav-link">Language Selection</a>
```

**After:**
```html
<a href="..." class="nav-link" data-i18n="nav.languageSelection">Language Selection</a>
```

The English text stays as the default/fallback visible on initial load, and `applyTranslations()` replaces it once the i18n module loads.

#### Step 5: Refactor JavaScript-rendered strings
For JS template literals in test.html, test_list.html, profile.html, etc., replace hardcoded strings with `t()` calls:

**Before:**
```js
container.innerHTML = `<h5>No Test History</h5>`;
```

**After:**
```js
container.innerHTML = `<h5>${t('profile.noHistory')}</h5>`;
```

#### Step 6: Handle dynamic attributes
- `placeholder` attributes: `data-i18n-placeholder="login.emailPlaceholder"`
- `aria-label` attributes: `data-i18n-aria="nav.userMenuLabel"`
- `title` attributes: `data-i18n-title="key"`
- `<title>` / page titles: set via JS after i18n loads

#### Step 7: Update `<html lang="">` dynamically
In `i18n-manager.js`, update `document.documentElement.lang` when locale changes.

#### Step 8: Persist preference and sync
- Store in `localStorage` as `interfaceLanguage`.
- Optionally store in user profile on the backend (via API) so the preference follows the user across devices.

---

## String Key Naming Convention

```
nav.home
nav.browseTests
nav.report
nav.profile
nav.logout
nav.languageSelection

login.title
login.tagline
login.emailLabel
login.emailPlaceholder
login.sendCode
login.newUserHint
login.otpSentTo
login.verificationCode
login.verifyBtn
login.backToEmail
login.resendCode
login.processing

footer.tagline
footer.copyright

langSelect.title
langSelect.subtitle
langSelect.continueBtn

onboarding.welcome
onboarding.tagline
onboarding.whatItDoes
onboarding.feature1
...

profile.title
profile.subtitle
profile.loading
profile.noHistory
profile.selectLanguage
profile.statistics
profile.testHistory
profile.loadMore
...

test.loading
test.question
test.previous
test.next
test.submit
test.answered
test.readingPassage
test.audio
test.typeWhatYouHear
...

testList.title
testList.subtitle
testList.filterTests
testList.testType
testList.allTypes
testList.difficulty
testList.allLevels
testList.reset
testList.recommended
testList.noTests
testList.surpriseMe
...

testPreview.title
testPreview.selectType
testPreview.startTest
testPreview.listening
testPreview.reading
testPreview.dictation
...

report.title
report.issueType
report.description
report.submit
report.cancel
report.success
...
```

---

## Considerations

1. **Flash of untranslated content (FOUC):** On initial load, English text renders before JS runs. This is acceptable since English is the fallback, and the switch happens quickly. For non-English-first users, we could add a tiny inline script (like the theme script) that hides the body until translations load.

2. **SEO impact:** Minimal — this is an authenticated app, not a content site. Search engines will index the English defaults.

3. **RTL support:** Not needed for the initial three languages (English, Chinese, Japanese).

4. **Translation management:** Start with manual JSON files. If the project grows, consider a tool like i18next or a translation management platform.

5. **Performance:** Translation JSON files will be small (<10KB each). Cache them in `localStorage` or use HTTP caching headers.

6. **Incremental rollout:** Templates can be migrated one at a time — the system gracefully falls back to the hardcoded English text for any strings not yet tagged with `data-i18n`.
