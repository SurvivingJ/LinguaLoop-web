---
title: Mobile walkthrough and fixes (2026-11-14)
type: evaluation
status: complete
last_updated: 2026-11-14
---

# Mobile walkthrough and fixes (2026-11-14)

Developer: "step through the app with your test account as a mobile user and optimise for
mobile. We shouldn't have to really scroll much, or have to click to open the keyboard for
the next questions."

## Method

Headless Chromium as an iPhone 13 (390 × 664 CSS px), test account, live database, local
gunicorn. An open keyboard was simulated by cutting the viewport to 390 × 360. Flows: language
selection → daily session → prestudy (preview, word prime) → reading test (cold) → new-word
drill (172 steps to the end) → practice exercises → listening and pitch-accent tests; plus
tests list, study plan, profile, flashcards, word list, dual translation.

## Findings

| # | Where | Problem on a phone | Fix |
|---|-------|--------------------|-----|
| 1 | Prestudy prime, new-word drill, practice cloze / error-correction typing, classifier and counter drills | After "Check" the text box was disabled or focus moved to Next / Continue, so the keyboard closed; every typed question needed a tap to reopen it | `static/js/answer-keys.js` (`window.LinguaKeys`): the checked box stays focused but frozen (edits undone, IME-safe), Enter / "Go" moves on, the next box takes focus while the keyboard is still up |
| 2 | Prestudy prime | Answer feedback rendered under the fixed Next bar (for a wrong answer, 300–900 px below the fold) | `LinguaKeys.reveal()` scrolls the feedback into the space above the keyboard and any `[data-bottom-bar]`; on phones the breadcrumb and step tabs hide during the quiz, the "I don't know" row hides once answered, unchosen wrong options collapse |
| 3 | Reading / listening test | All questions stacked: 3,275 px for a 4-question reading test; Submit bar 130 px tall | **Scrolling kept on purpose** (developer: tests are the one place scrolling is fine; a one-question-at-a-time version was built and reverted the same day). Compact header (timer top right), tighter question cards, one-line Submit bar: 3,275 → ~2,200 px |
| 4 | Every practice / test page | Footer and an 77 px sticky top bar took space from the work | `focus_page` template flag → `body.focus-page`: no footer, thin non-sticky top bar on phones; session progress in one thin row |
| 5 | Exercise cards (practice, drill) | 28 px padding, 300 px min height: the prompt scrolled off when the keyboard opened | Tighter card spacing under 576 px |
| 6 | Touch screens | `:hover` stuck on the last tapped answer, so the next question's option looked chosen | Hover styles neutralised under `(hover: none)` |
| 7 | Language selection | Start button below the fold after choosing | Compact cards |
| 8 | Test help "i" button | Covered the Submit button | Sits above the bottom bars on phones |

## Found, not changed

- New-word drill header "New words — 22 of 22 to go" did not count down during a 172-step run.
- `/tests` is 16,000 px on a phone (full card list); `/study-plan` 4,000 px.
- Pitch-accent legend chips are not tappable (swipe or arrow keys only).
- Real-device check still needed: iOS keeps the keyboard when focus moves between text boxes
  inside the Enter / tap handler, which is what the helper relies on; headless Chromium cannot
  show the keyboard itself.

## Verification

- Walkthrough: prestudy and drill — focus stayed in the answer box after every check and every
  Enter (0 losses in 172 drill steps, including cloze typing); feedback visible with the
  simulated keyboard; reading test answered and submitted (with the reverted paged layout; the stacked layout re-checked after the revert).
- `tests/unit/answer-keys.test.js` (9). vitest 440/440. eslint 0 errors; stylelint and prettier
  counts unchanged from the base commit.

## Test-account data changed

One reading test submitted (`ながいおしろをつくろう`, cold), prestudy sessions opened, the new-word
drill run to the end with mixed right/wrong answers, one practice item served.

## Related Pages

- [[features/test-prestudy]]
- [[features/new-word-drill]]
- [[evaluations/latency-2026-11-11]]
