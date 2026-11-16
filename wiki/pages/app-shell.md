---
title: App Shell and Design System (mobile redesign)
type: page
status: in-progress
tech_page: app-shell.tech.md
last_updated: 2026-11-16
open_questions:
  - "OPEN — Does the shell behave on real iOS Safari (dvh, safe-area insets, keyboard handling)? Only Chromium has been tested. TASK-975."
  - "OPEN — Do the derived colours (tertiary text, dark-mode brand button text, etc.) meet WCAG AA contrast in every theme? Chosen by hand, not measured. TASK-981."
  - "OPEN — Is the redesign ready to ship? It is built in the working tree but not committed, reviewed or deployed. TASK-988."
---

# App Shell and Design System (mobile redesign)

## Purpose

The frame every LinguaDojo page sits in — navigation, the one-task-per-screen layout, colour
themes, fonts and the shared visual components — rebuilt on 2026-11-16 to the approved mobile
mockup so the app works as a phone app first. The decision record is
[[decisions/ADR-046-mobile-app-shell]].

## User Story

As a learner on my phone, I want each screen to show one thing to do, with the button I need
always under my thumb and never below the fold, and I want to move between today's session,
practice, tests and my settings with one tap. I want the app to follow my phone's light or dark
setting, and to keep the colour theme I picked before.

## How It Works

**Navigation on a phone.** A slim bar at the top shows the language I am studying (tap it to
change), a Report button and a light/dark switch. A tab bar at the bottom has four tabs:
**Today** (the daily session), **Practice** (practice only), **Tests** (browse tests) and **Me**
(profile and settings). The tab for the area I am in is highlighted. There is no hamburger menu
and no footer. Everything else — Study Plan, Word List, Calibration, Measure Words (Chinese) or
Counters (Japanese), Language Selection, my translation error profile, the colour theme, light /
dark / system appearance, interface language, Report and Logout — is on the Me page.

**Navigation on a wide screen (tablet or desktop, 768 px and up).** The tabs move into the top
bar next to Calibration and the drill for my language, with menus for interface language, theme
and my account. The footer comes back.

**One task per screen.** When I start a test, a drill, a translation or a session item, the
screen changes to a task screen: no tabs and no top bar, just a header with a **Back** button,
an optional seal character, a title and a subtitle, and sometimes a counter or clock on the
right. Under the header is the task itself; if it is long (a reading passage), only that middle
part scrolls. At the bottom is the action area — Check, Next, Submit, or the feedback I must read
before going on. It is always on screen, including when the keyboard is open.

Back goes where I came from: inside the daily session it returns to the Today card (which then
offers "Resume session"); on standalone pages it goes to the page's usual parent, or back in
history when I came from another page of the app.

**Normal pages** (Today's start card, Browse Tests, Me) scroll like ordinary pages, with the tab
bar fixed at the bottom.

**Themes.** The default theme ("Dojo") has a light and a dark version and follows my phone's
setting unless I choose Light or Dark on the Me page. The five themes that existed before —
Still Water (the old default), Midnight (dark), Sakura, Forest and Inkstone & Vermilion — are
still there with the same colours; each is either light or dark. If I had never chosen a theme,
I now see the new default; if I had chosen one of the others, I keep it. The theme is applied
before the page draws, so there is no flash of the wrong colours.

**Fonts.** Headings use Bricolage Grotesque, body text Instrument Sans, numbers JetBrains Mono;
Chinese or Japanese study text uses Noto Serif SC or JP, loaded only for the language I study.

**Pop-ups.** On a phone, dialogs (Report, the native-language prompt and others) open as bottom
sheets that slide up from the bottom of the screen.

## Constraints & Edge Cases

- **Keyboard open.** While the on-screen keyboard is open, the task screen shrinks to the
  visible area so the action area stays above the keyboard. Tested only in Chromium so far, not
  on a real iPhone (TASK-975).
- **Notches and home indicators.** The shell pads itself around the phone's safe areas.
- **Old saved theme.** The stored value that meant Still Water now means the new default; a
  learner who wants the old look picks Still Water once.
- **Untouched pages change too.** The new styles apply to every page, so text is now darker,
  phone headings are smaller and buttons are at least 44 px tall everywhere. Pages with tight
  layouts may need checking (TASK-979).
- **Hard-coded colours do not follow the theme.** Page styles must use the shared colour tokens.
- **Interface language.** All shell strings are translated in English, Chinese, Japanese and
  Spanish; a missing key would show the raw key name.

## Business Rules

- On a task screen the page itself never scrolls; only the middle (stage) may.
- The primary action of a task screen is in the bottom action area, never at the end of the
  scrolling content.
- Every tappable control is at least 44 × 44 px; text inputs use at least a 16 px font (so iOS
  does not zoom).
- Every feature that leaves the phone top bar must be reachable from the Me page.
- Colours come from theme tokens only, so every theme and both schemes render correctly.

## Open Questions

- **OPEN** — real iOS Safari / Android behaviour (TASK-975).
- **OPEN** — measured colour contrast of the derived tokens (TASK-981).
- **OPEN** — commit, review and deploy (TASK-988).
- **ANSWERED** — Where do the links that left the phone top bar go? The Me page (built 2026-11-16).
- **ANSWERED** — Are the old themes kept? Yes, all five, unchanged, as named themes.

## Related Pages

- [[pages/app-shell.tech]] — technical counterpart
- [[decisions/ADR-046-mobile-app-shell]] — the decision
- [[pages/pages-overview]] — route map, with each page's shell mode
- [[pages/study-session]] — the daily session, which switches task mode at runtime
- [[features/dt-guided-self-repair]] — the repair sheet, whose own no-scroll rule came first
- [[tasklist/mobile-redesign.tasks]] — open work
- Mockup: `wiki/demos/mobile-redesign-mockup.html`
