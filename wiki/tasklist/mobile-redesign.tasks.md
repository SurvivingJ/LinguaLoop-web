---
title: "Mobile Redesign (App Shell and Design System) — Task Breakdown"
feature: mobile-redesign
prose_page: ../pages/app-shell.md
tech_page: ../pages/app-shell.tech.md
total_tasks: 14
done: 2
---

# Mobile Redesign (App Shell and Design System) — Task Breakdown

Spec: [[pages/app-shell.tech]]. Decision: [[decisions/ADR-048-mobile-app-shell]]. Mockup:
`wiki/demos/mobile-redesign-mockup.html`.

The redesign was built on 2026-11-16 by a foundation engineer, area engineers (auth, session,
tests, prestudy, translation, trainers, settings) and an integration step. These tasks cover
**every open issue and unverified item the engineers reported**, checked against the working
tree on 2026-11-16. Drafted 2026-11-16, **not yet reviewed by the owner** (CLAUDE.md §5d). IDs
start at TASK-976 (TASK-975 was taken on main by the new-word drill; the real-device check is TASK-1007).

Note: the integration report reached the wiki truncated (its i18n paragraph and anything after
it were cut off). TASK-985 records what a re-run of the integrator's key check shows; any other
open item from the rest of that report is not captured here.

Harness used by most tasks (see tech page, Testing Strategy):
```
python -m venv V && V/bin/pip install -r requirements.txt -r requirements-dev.txt
V/bin/python tests/e2e/redesign/serve.py --port 5099 &
node tests/e2e/redesign/preview.cjs --port 5099 --path /tests --shot /tmp/x.png
PORT=5099 python3 tests/e2e/redesign/walk.py all
```

---

## TASK-1007: Real-device check — iOS Safari and Android Chrome

**Status:** [ ] Not Started
**Feature:** mobile-redesign
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
`dvh`, `env(safe-area-inset-*)` and the `visualViewport` keyboard handling were only exercised in
Chromium. iOS Safari is the main target and behaves differently (toolbars, `100dvh` with the
keyboard open). Run the app on a real iPhone (Safari, notch + home indicator) and an Android phone
(Chrome) and check the shell rules.

**Acceptance Criteria:**
- [ ] On every task page (list in tech page, "Shell mode per page") and in `/session` with a
      running item: the document does not scroll, only `.ld-stage` scrolls, the dock is fully visible
- [ ] With the keyboard open (DT, dictation, typed drills, word list search): the dock sits above
      the keyboard and `--ld-vvh` is set; it is removed when the keyboard closes
- [ ] App bar, tab bar and dock clear the notch and home indicator in portrait and landscape
- [ ] No input zooms the page on focus (16 px rule)
- [ ] Bottom-sheet modals open and close and do not leave the page scrolled
- [ ] Results (device, OS, browser, pass/fail per screen, screenshots) recorded in the log

**Technical Notes:**
Serve over the LAN (`serve.py --host 0.0.0.0 --port N`; `--host` exists, default 127.0.0.1) or use a staging deploy. Fixture
data is enough; no production credentials. Fix defects in `styles.css` / `base.js` and re-run
`tests/test_redesign_shell.py`.

**Files to Create / Modify:**
- `static/css/styles.css`, `static/js/pages/base.js` — only if defects are found

**Verification:**
Screenshots of each screen on both devices, keyboard open and closed; a log entry listing them.

---

## TASK-976: Check rendering with the real web fonts

**Status:** [ ] Not Started
**Feature:** mobile-redesign
**Type:** test
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
Every harness render blocked Google Fonts, so Bricolage Grotesque, Instrument Sans, JetBrains
Mono and Noto Serif SC/JP were never seen. Render with fonts allowed and check line heights,
truncation and CJK text against the mockup.

**Acceptance Criteria:**
- [ ] `preview.cjs --fonts` renders `/tests`, `/profile`, `/session` (one item of each player) and
      `/__preview/components` in zh and ja, light and dark
- [ ] Noto Serif SC loads for zh and Noto Serif JP for ja (Network tab), and only for the study language
- [ ] No text overflows or clips that did not in the fallback-font run; screenshots compared with the mockup

**Technical Notes:** `LinguaFonts.ensureForStudyLanguage(id)`; CSP allows only the two Google hosts.

**Files to Create / Modify:**
- `static/css/styles.css` or `static/css/redesign/*.css` — only if defects are found

**Verification:** paired screenshots (fallback vs real fonts) filed with the log entry.

---

## TASK-977: Render the Forest, Inkstone and Still Water themes

**Status:** [ ] Not Started
**Feature:** mobile-redesign
**Type:** test
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
Only the default (light and dark), Midnight and Sakura were rendered. Forest, Inkstone &
Vermilion and Still Water were checked by reading CSS, not by eye.

**Acceptance Criteria:**
- [ ] `walk.py` (or `preview.cjs --theme forest|inkstone|stillwater`) over every page and session player
- [ ] Every `.ld-*` component on `/__preview/components` is legible in all three themes
- [ ] Theme picker on `/profile` switches to each and back; reload keeps the choice; no flash on load

**Technical Notes:** themes are `:root[data-theme='…']` blocks in `styles.css`.

**Files to Create / Modify:**
- `static/css/styles.css` — only if a token is missing or wrong in a theme

**Verification:** screenshots per theme; log entry.

---

## TASK-978: Open the bottom sheets, theme dropdown and toast

**Status:** [ ] Not Started
**Feature:** mobile-redesign
**Type:** test
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
`#reportModal`, `#nativeLanguageModal`, the desktop theme dropdown and `showToast` were never
opened or screenshotted after the restyle.

**Acceptance Criteria:**
- [ ] At 393×659: Report (app bar and Me page) and the native-language prompt open as bottom sheets
      with handle, scroll inside, close by button/Escape/scrim, and the page does not scroll after closing
- [ ] At 1280×800: they open as centred modals; the theme dropdown shows the mode picker and all six themes
- [ ] `showToast(msg, 'error'|'success'|'info')` appears above the tab bar on tab pages and above the dock in task mode
- [ ] Light and dark, plus Midnight

**Technical Notes:** `preview.cjs --click '[data-bs-target="#reportModal"]' --shot …`; `.ld-no-sheet` opt-out.

**Files to Create / Modify:**
- `static/css/styles.css` — only if defects are found

**Verification:** screenshots; log entry.

---

## TASK-979: Check pages with real data against the global restyle

**Status:** [ ] Not Started
**Feature:** mobile-redesign
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
`/session`, `/tests` and `/profile` were rendered with empty API data, and the global restyle
changes untouched markup: body text is `--ink` (was the secondary colour) at 15 px, `h1` is 26 px on
phones (was 39 px), `.btn` is at least 44 px and `inline-flex`, `.alert` lost its left border, and
colour utilities (`.text-secondary`, `.bg-white`, …) follow the theme. Pages with tight layouts may
break.

**Acceptance Criteria:**
- [ ] Fixtures with realistic data (long titles, many tests, full history, long DT passages, many
      word-list rows, admin-free) written under `tests/e2e/redesign/fixtures/`
- [ ] Every page and player rendered with them at 393×659 and 1280×800: no horizontal overflow,
      no clipped buttons, no illegible text on `.bg-white`/`.text-secondary` areas
- [ ] `/admin/vocab-preview` and the admin dashboard (local admin variant) checked for breakage
      from the global styles
- [ ] Each defect fixed in the owning stylesheet or listed as a new task

**Technical Notes:** response shapes come from the route code; copy them, do not invent fields.

**Files to Create / Modify:**
- `tests/e2e/redesign/fixtures/*.json` — realistic fixtures
- `static/css/redesign/*.css`, `static/css/pages/*.css` — fixes

**Verification:** `walk.py all` with the new fixtures reports no overflow, no off-screen docks.

---

## TASK-980: Run the full Python test suite

**Status:** [ ] Not Started
**Feature:** mobile-redesign
**Type:** test
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
Only the template, route, static, i18n and session tests were run (186 passed). Run everything.

**Acceptance Criteria:**
- [ ] `pytest` over the whole `tests/` directory; failures compared with the same run on the last commit
- [ ] Every failure that the redesign introduced is fixed; pre-existing ones are listed in the log

**Files to Create / Modify:** none expected.

**Verification:** `pytest -q` output on the redesign tree and on `HEAD` without it.

---

## TASK-981: Measure colour contrast of every theme

**Status:** [ ] Not Started
**Feature:** mobile-redesign
**Type:** test
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
Derived tokens (`--ink-3`, `--brand` text on `--brand-ink` in dark, `--glow-text`, `--warn` on
`--warn-wash`, Midnight's dark-on-teal primary button, …) were chosen by hand. Measure them.

**Acceptance Criteria:**
- [ ] A script computes contrast for every text/background token pair used by the `.ld-*`
      components, in the default light, default dark and the five named themes
- [ ] Body and button text ≥ 4.5:1; large text and UI boundaries ≥ 3:1; failures fixed in `styles.css`
- [ ] Results table filed in the log or an evaluation page

**Files to Create / Modify:**
- `scripts/` or `tests/` contrast check (new) — reads the token values from `styles.css`
- `static/css/styles.css` — token fixes

**Verification:** the script exits 0.

---

## TASK-982: Run the Playwright E2E specs

**Status:** [?] Blocked — needs test credentials
**Feature:** mobile-redesign
**Type:** test
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
`npm run test:e2e` was not run because the specs need real credentials. The redesign removed the
navbar, the hamburger and changed many selectors, so the specs may target elements that no longer exist.

**Acceptance Criteria:**
- [ ] Specs run against a staging account; selector failures caused by the redesign fixed in the specs
- [ ] The three specs (`calibration`, `login`, `take-a-test`) pass; none references `#mobileNavBtn`
      or `.navbar` (checked 2026-11-16), but they may depend on page markup the area engineers rewrote

**Files to Create / Modify:**
- `tests/e2e/*.spec.js` — selector updates

**Verification:** `npm run test:e2e` passes on staging.

---

## TASK-983: Clear the remaining lint and format failures

**Status:** [ ] Not Started
**Feature:** mobile-redesign
**Type:** refactor
**Complexity:** S (1-3h)
**Depends On:** TASK-988 (do it as its own commit after the redesign commit)

**Description:**
`prettier --check` failed on 13 files the foundation did not own (session players, prestudy,
`active-timer.js`, `weekly-study.js`, …); stylelint's 107 remaining errors were in
`css/pages/drill.css` and `test-pinyin.css`, which have since been deleted. Re-run and fix.

**Acceptance Criteria:**
- [ ] `npx prettier --check` passes on `static/` and `templates/`-adjacent JS/CSS
- [ ] `npx stylelint "static/css/**/*.css"` reports 0 errors
- [ ] `npm run lint` 0 errors; formatting-only changes in a separate commit

**Files to Create / Modify:** the files prettier lists.

**Verification:** the three commands above.

---

## TASK-984: Make the preview harness reproducible

**Status:** [ ] Not Started
**Feature:** mobile-redesign
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
The harness needs the Python dependencies and `node_modules`; the only venv was in a scratch
directory that will not survive. Document and script the setup so the next person can run it.

**Acceptance Criteria:**
- [ ] npm scripts (e.g. `preview:serve`, `preview:walk`) or a short README in `tests/e2e/redesign/`
      giving the exact commands
- [ ] `serve.py` fails with a clear message when a dependency is missing
- [ ] `node_modules` stays git-ignored (it is today)

**Files to Create / Modify:**
- `package.json`, `tests/e2e/redesign/README.md` (new)

**Verification:** a fresh clone can run `walk.py all` following only the README.

---

## TASK-985: Fill the remaining i18n gaps

**Status:** [x] Done (2026-11-16)
**Feature:** mobile-redesign
**Type:** bug
**Complexity:** XS (<1h)
**Depends On:** none

**Description:**
Re-running the integrator's key check (2026-11-16) lists `session.dt_repair_heading` missing in
`es.json`, and ten keys missing in all four locales that render only through a JS English fallback:
`session.speed_done|empty|error|no_mastered|timed_out|timeouts|too_few|unavailable`,
`dual_translation.target_word`, `dual_translation.target_words_heading` (all pre-date the redesign).

**Acceptance Criteria:**
- [x] All eleven keys present in en/zh/ja/es with native text — done 2026-11-16; the full gap was
      larger than the check showed: `es` lacked 57 keys (55 `dt_repair.*` plus
      `session.dt_repair_heading` / `_none`), and the code-only keys were 17, not 10
      (`session.speed_heading`, `dual_translation.target_in_gold|in_yours|status` and the dynamic
      `dual_translation.target_produced|variant|omitted` as well). All added; en 1158→1175 keys,
      the four files have identical key sets
- [x] The key check reports nothing; `tests/test_i18n_locale_files.py` passes — a scan of
      `templates/` and `static/js` for `data-i18n*` and `t()/T()/tr()/label()` literal keys finds no
      key missing from any locale (only runtime-concatenated prefixes, whose families are complete);
      pytest 5 passed, `npm run check` clean, `npm run test:unit` 505 passed. Not done: loading the
      speed round in zh in a browser

**Files to Create / Modify:**
- `static/i18n/{en,zh,ja,es}.json`

**Verification:** run the key-check script; load the speed round in zh and see Chinese strings.

---

## TASK-986: Regression tests for the small behaviour changes

**Status:** [ ] Not Started
**Feature:** mobile-redesign
**Type:** test
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
The foundation changed three behaviours: logout is wired by one document-level click handler on
`#logout-btn` and `[data-ld-logout]`; the study-language chip now shows (it read a storage key
nothing wrote); Midnight's primary-button text is dark on teal. Pin them with tests.

**Acceptance Criteria:**
- [ ] Unit test: clicking `[data-ld-logout]` (Me page) and `#logout-btn` (desktop menu) both clear tokens and go to `/login`
- [ ] Unit test: the chip shows the language from the key the language-selection page writes
- [ ] Contrast of Midnight's primary button text covered by TASK-981

**Files to Create / Modify:**
- `tests/unit/base-shell.test.js` (new)

**Verification:** `npm run test:unit` passes.

---

## TASK-987: Integration requests — i18n merge, Me page links, hard-coded colours

**Status:** [x] Done (2026-11-16)
**Feature:** mobile-redesign
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
Open issues raised by the foundation engineer and closed during integration: merge the
`static/i18n/_redesign/*.json` files into the four locale files; add the phone-only links to the
Me page; replace hard-coded colours in page CSS.

**Acceptance Criteria:**
- [x] `static/i18n/_redesign/` merged (65 keys) and deleted — verified: the folder no longer exists
- [x] `/profile` carries Study Plan, Calibration, Word List, DT error profile, Measure Words / Counters
      (lang-gated), Language Selection, mode / theme / UI-language pickers, Report and Logout — verified in `templates/profile.html`
- [x] No hex colours in `static/css/redesign/*.css`, `static/css/pages/*.css`, `dt-repair.css`; no
      `var(--x, #hex)` fallbacks in templates or JS — verified by grep; the "Surprise Me" card is `.tl-surprise` in `tests.css`
- [x] `.ld-stage { position: relative }`; practice.js passes `#exerciseDock` to `DTErrorCard.mount`

**Files to Create / Modify:** done — see [[pages/app-shell.tech]].

**Verification:** as above.

---

## TASK-988: Commit, review and deploy the redesign

**Status:** [?] Blocked — owner decision
**Feature:** mobile-redesign
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** TASK-1007, TASK-980 (recommended before deploy)

**Description:**
The redesign (85 files changed in `templates/` and `static/`, plus new `static/css/redesign/`,
`tests/e2e/redesign/`, `tests/test_redesign_shell.py`) is in the working tree only. Prettier
reformatted all of `styles.css`, so its diff is large and mostly whitespace in page-scoped sections.

**Acceptance Criteria:**
- [ ] Committed on a branch in reviewable commits (formatting of `styles.css` separate from changes if practical)
- [ ] PR opened and reviewed by the owner
- [ ] Deployed; post-deploy smoke on a phone: tabs, one task screen, theme switch, logout
- [ ] Learners with stored `linguadojo-theme=default` see the new palette (expected, ADR-048)

**Files to Create / Modify:** none beyond the built files.

**Verification:** PR link and deploy record in the log.
