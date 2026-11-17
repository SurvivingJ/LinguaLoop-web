---
title: "ADR-048: Mobile app shell — one task per screen, header / stage / dock, bottom tabs, dvh sizing, new default theme"
status: accepted
date: 2026-11-16
---

# ADR-048: Mobile app shell — one task per screen, header / stage / dock, bottom tabs, dvh sizing, new default theme

## Context

LinguaDojo is used mostly on phones, but every page was laid out as a desktop page that
happened to shrink: a sticky Bootstrap navbar with a hamburger menu (`#mobileNavBtn`), the
page content, then a footer. The primary action of most screens (Check, Next, Submit) sat at
the end of the content, so on a phone the learner scrolled to reach it, and the document was
usually taller than the screen. The approved mockup
(`wiki/demos/mobile-redesign-mockup.html`, committed `d9c737d`) set out a different model in its
first comment: "a one-screen app shell. Header and action dock never move; only the stage
between them may scroll. One task per screen, answer controls in the thumb zone, bottom tabs
instead of a hamburger."

**Why the earlier scroll fix did not hold.** The only earlier no-scroll work was local to one
overlay: the DT guided self-repair sheet (2026-11-14, `14d554a`,
[[features/dt-guided-self-repair.tech]] §8.3). It pinned `html`/`body` (`overflow: hidden`, then
`position: fixed; top: -scrollY`) only while that sheet was open, and its no-scroll harness ran on
a test page that already fitted the screen, so it could not see the real DT page scrolling
(1079 px at 390×844, found in integration). Everything underneath stayed as it was:

- the page frame itself was taller than the screen — sticky header + content + footer in normal
  flow, with no height limit on `main`;
- heights in `vh` (`.session-stage { min-height: 50vh }` in `study_session.html`,
  `.login-container { min-height: 100vh }` in `styles.css`), and on iOS Safari `100vh` is the
  height with the browser toolbars hidden, so a "full-height" element is taller than what is
  visible;
- actions were placed at the end of the content, so reaching them required scrolling by design;
- no shared layout primitive existed, so each page or overlay had to re-solve the problem, and
  each fix only covered the case it was written for.

A fix that pins the body around one overlay cannot stop pages from scrolling; the frame had to
change.

## Decision

1. **One shell for every page** (`templates/base.html`, `body.ld-body`), in one of three modes:
   `ld-has-tabs` (normal app pages: Today, Tests, Me and the session start card — these scroll
   by design), `ld-task` (one task per screen) and `ld-bare` (`hide_navbar`: login, onboarding).
2. **One task per screen.** A task screen is a fixed three-part column: a header (labelled Back
   pill, optional seal glyph, title / subtitle, right-hand slot), a **stage** (`.ld-stage`, the
   only element allowed to scroll) and a **dock** (`.ld-dock`, the pinned action area in the thumb
   zone). In task mode there is no app bar, tab bar or footer, and the document never scrolls.
   Pages opt in statically (`{% set task_mode = true %}` plus `task_*` / `dock` blocks); the
   single-page `/session` runner switches at runtime with `window.LinguaShell.setTaskMode()`, and
   its players get `ctx.frame` (`setHeader`, `onBack`, `stage`).
3. **Bottom tabs on phones** (< 768 px): Today → `/session`, Practice → `/session?mode=practice`,
   Tests → `/tests`, Me → `/profile`, plus a slim top bar (study-language chip, Report, light/dark
   toggle). The hamburger and the footer are removed on phones. From 768 px the tabs move into the
   top bar with Calibration, Measure Words / Counters, Report and the language, theme and account
   menus, and the footer returns. Everything the phone top bar no longer holds (Study Plan, Word
   List, Calibration, drills, Language Selection, DT error profile, theme / mode / UI-language
   pickers, Report, Logout) is reachable from the Me page.
4. **Viewport sizing with `dvh` and the visual viewport.** The viewport meta carries
   `viewport-fit=cover` and the shell pads itself with `env(safe-area-inset-*)`. Task screens are
   `height: var(--ld-vvh, 100dvh)`; while the on-screen keyboard is open, `base.js` sets `--ld-vvh`
   from `window.visualViewport.height` so the dock stays above the keyboard. `100vh` and `vh`-based
   minimum heights are not used in new CSS.
5. **New default theme with light and dark; the five earlier themes kept.** The mockup palette is
   the default theme ("Dojo", id `default`). It follows the system light/dark setting unless the
   learner forces one (`html[data-mode="light"|"dark"]`, stored in `linguadojo-theme-mode`). The five
   earlier themes are kept with their colours unchanged as fixed-scheme named themes: Still Water
   (`stillwater`, the previous default), Midnight (dark), Sakura, Forest and Inkstone & Vermilion.
   The stored value `default` used to mean Still Water and now means the new palette, so learners
   who never picked a theme get the new look. All earlier colour variables (`--primary`,
   `--slate-*`, `--bg-*`, `--text-*`, `--bs-*`, `--teal`, …) are mapped onto the new tokens, and
   Bootstrap components are restyled to match, so untouched markup follows the theme.
6. **A shared component layer** (`.ld-*` classes in `styles.css`) built on tokens only (no hex in
   page CSS); per-area stylesheets in `static/css/redesign/` scoped to their page or player root.

## Consequences

- Easier: every task screen gets the same header, Back behaviour and dock; the action is always
  on screen; a player written once renders the same inside `/session` and on its standalone page.
  A no-scroll check is now a property of the shell and can be asserted on every page
  (`tests/e2e/redesign/preview.cjs`, `walk.py`).
- Harder / constrained: players must put their primary action in the dock and must not use
  `vh` heights, `position: fixed` docks or `window.scrollTo`; they scroll the stage instead. New
  CSS must use tokens; selectors on `[data-theme]` for dark mode are not allowed (use tokens or
  `[data-bs-theme='dark']`). Absolutely positioned descendants of a stage resolve against it
  (`.ld-stage { position: relative }`).
- The global restyle changes untouched pages (body text colour, heading sizes, 44 px minimum
  buttons, colour utilities following the theme); pages with tight layouts need checking.
- The behaviour depends on `dvh`, safe-area insets and `visualViewport`, which have only been
  exercised in Chromium so far; iOS Safari is the main target and is unverified
  ([[tasklist/mobile-redesign.tasks]]).
- Learners who had the old default saved see a new palette without choosing it; Still Water
  remains one tap away in Me → Colour theme.

## Alternatives Considered

- **Keep pinning the body per overlay / per page** (the 2026-11-14 approach). Rejected: it fixes
  only the screen it is written for and leaves the frame taller than the viewport.
- **`100vh` / `-webkit-fill-available` heights.** Rejected: `100vh` overshoots the visible area
  on iOS Safari; `dvh` with a visual-viewport override is the supported way.
- **Keep the hamburger menu on phones.** Rejected by the approved mockup: the four main
  destinations should be one tap away; the rest lives on the Me page.
- **A client-side SPA shell.** Rejected: the app stays server-rendered (Jinja + vanilla JS);
  only `/session` switches task mode at runtime.
- **Replace the old themes with the new palette only.** Rejected: the five themes are kept so
  that learners who chose one keep it.

## Related Pages

- [[pages/app-shell]] / [[pages/app-shell.tech]]
- [[pages/pages-overview]], [[pages/study-session]]
- [[features/dt-guided-self-repair.tech]] §8.3 (the earlier, local no-scroll rule)
- [[tasklist/mobile-redesign.tasks]]
