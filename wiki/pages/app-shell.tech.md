---
title: App Shell and Design System — Technical Specification
type: page-tech
status: in-progress
prose_page: app-shell.md
last_updated: 2026-11-16
dependencies:
  - "templates/base.html (shell, task-mode blocks, tab bar, app bar, modals)"
  - "static/css/styles.css (tokens, themes, SHARED COMPONENTS .ld-*, Bootstrap restyle)"
  - "static/css/redesign/{auth,session,tests,prestudy,translation,trainers,settings}.css"
  - "static/js/theme-manager.js (window.LinguaTheme)"
  - "static/js/pages/base.js (window.LinguaShell, visualViewport, logout, lang gates)"
  - "static/js/pages/base-head.js (theme before first paint)"
  - "static/js/i18n-manager.js (data-ld-ui-lang-picker)"
  - "Bootstrap 5 (restyled, not replaced); Google Fonts (Bricolage Grotesque, Instrument Sans, JetBrains Mono, Noto Serif SC/JP)"
  - "tests/e2e/redesign/{serve.py,preview.cjs,walk.py,gallery.html,fixtures/}; tests/test_redesign_shell.py"
breaking_change_risk: high
---

# App Shell and Design System — Technical Specification

Decision: [[decisions/ADR-048-mobile-app-shell]]. Source of truth for the look:
`wiki/demos/mobile-redesign-mockup.html`. State on 2026-11-16: built in the working tree,
**not committed and not deployed** (TASK-988). Claims below were checked against the files.

## Architecture Overview

```
body.ld-body.{ld-has-tabs | ld-task | ld-bare}      (base.html line ~72; chosen from task_mode / hide_navbar)
 ├─ header#ldAppbar.ld-appbar      phones: logo, study-language chip, Report, mode toggle
 │                                 >=768px: + Daily Session · Practice · Browse Tests · Calibration ·
 │                                 Measure Words(zh)/Counters(ja), UI-language, theme, user menus
 ├─ header#ldTaskbar               task mode only: a#ldBack.ld-back · #ldTaskGlyph · #ldTaskTitle /
 │                                 #ldTaskSubtitle · #ldTaskEnd
 ├─ main#main-content.ld-main      normal: {% block main_class %}container py-4{% endblock %}
 │                                 task:   ld-main ld-main--task (flex column, max 720px on desktop)
 │    └─ (task) .ld-screen > [.ld-strip] + .ld-stage (only scroller) + .ld-dock (pinned)
 ├─ {% block dock %}                optional page-level dock (no empty dock is rendered without it)
 ├─ footer                          hidden < 768px and in task mode
 ├─ nav#ldTabbar.ld-tabbar          < 768px, ld-has-tabs only: Today · Practice · Tests · Me
 └─ #reportModal, #nativeLanguageModal (bottom sheets < 576px)
```

Active tab (`_tab`, base.html ~66) is derived from `request.endpoint`: `study_session_page` →
today (or practice with `?mode=practice`); `tests` and `test_*` → tests; profile, study plan,
word list, calibration, language selection, DT profile → me; flashcards, DT, drills → practice.

Shell mode per page (2026-11-16):

| Mode | Templates |
|---|---|
| `ld-task` (static `task_mode`) | `calibration`, `classifier_drill`, `counter_drill`, `dual_translation`, `dual_translation_profile`, `flashcards`, `language_selection`, `study_plan`, `test`, `test_dictation`, `test_pinyin`, `test_pitch_accent`, `test_prestudy`, `test_preview`, `word_list` |
| `ld-task` at runtime | `study_session` (`/session`) while an item runs; tab page on the start card and summary |
| `ld-has-tabs` | `test_list` (`/tests`), `profile` (`/profile` = Me), `error`, and the session start card |
| `ld-bare` (`hide_navbar`) | `login`, `onboarding` |

## Database Impact

None. No table, RPC or migration. Theme and mode live in `localStorage` only
(`linguadojo-theme`, `linguadojo-theme-mode`).

## API / RPC Surface

No HTTP routes. The preview harness adds `/__preview/components`, `/__preview/task` and
`/__preview/login` **only inside `tests/e2e/redesign/serve.py`**, never in the production app.

### Jinja task mode (child template)
```
{% set task_mode = true %}
{% set task_back = 'history' %}                       {# optional #}
{% block task_back_href %}{{ url_for('tests') }}{% endblock %}   {# default url_for('study_session_page') #}
{% block task_title %}…{% endblock %}  {% block task_subtitle %}…{% endblock %}
{% block task_glyph %}听{% endblock %}  {% block task_header_end %}2/5{% endblock %}
{% block content %}<div class="ld-stage">…</div>{% endblock %}
{% block dock %}<button class="ld-btn">Check</button>{% endblock %}
```
- `task_back == 'history'` sets `body[data-ld-back="history"]`: Back calls `history.back()` when
  `document.referrer` is same-origin and `history.length > 1`, else follows the href.
- `main_class` is ignored in task mode. Existing switches `hide_navbar`, `hide_footer`,
  `defer_base_scripts`, `load_test_intro` still work.

### `window.LinguaShell` (`static/js/pages/base.js`)
#### `setTaskMode(on: boolean): void`
- **Purpose:** switch the one-task layout at runtime (used by `/session`).
- **Side effects:** toggles `body.ld-task` / `body.ld-has-tabs`; stores `main`'s classes in
  `main.dataset.ldPageClass` and sets `ld-main ld-main--task`; restores them when turned off.
#### `isTaskMode(): boolean`
#### `setTaskHeader({title?, subtitle?, glyph?, end?, backHref?, backLabel?}): void`
- Text only (`textContent`). Omitted / null keys keep their value; `''` clears. `backLabel`
  removes the label's `data-i18n` so the UI-language switch does not overwrite it.
#### `onBack(fn: (e) => boolean|void): () => void`
- Handlers run newest first on a click of `#ldBack`; returning `true` cancels navigation.
  Returns an unsubscribe function. Exceptions are logged and treated as not handled.

### Session player frame (`static/js/session/controller.js`)
`mount(container, ctx)` players receive optional `ctx.frame = { setHeader, onBack, stage }`
(absent on standalone pages and in unit tests — guard). `onBack` handlers are removed when the
item is torn down. Back from a running item returns in-page to the Today card (resume); from an
optional round, to the summary. There is no runner-level Skip button; a skippable player renders
its own `.ld-link--quiet` "Skip for now" and calls `ctx.onSkip()`. See [[pages/study-session.tech]].

### `window.LinguaTheme` (`static/js/theme-manager.js`)
| Member | Contract |
|---|---|
| `list()` | `[{id, name, nameKey, description, descriptionKey, scheme: 'auto'|'light'|'dark', swatches:[bg,brand,accent]}]` for `default` ("Dojo (default)", auto), `stillwater` (light), `midnight` (dark), `sakura`, `forest`, `inkstone` (light) |
| `current()` / `setTheme(id)` / `apply(id)` | unknown id → `default`; writes `linguadojo-theme` |
| `mode()` / `setMode('system'|'light'|'dark')` | writes `linguadojo-theme-mode`; light/dark while a named theme is active switches the theme to `default` |
| `scheme()` / `toggleScheme()` | resolved `'light'|'dark'` |
| `onChange(fn)` | returns unsubscribe; also `document` event `lingua:themechange` `{theme, mode, scheme}` |
| `renderThemePicker(el)` / `renderModePicker(el)` | render pickers; auto-rendered into `[data-ld-theme-picker]`, `[data-ld-mode-picker]` on DOMContentLoaded and relabelled on UI-language change |

DOM written: `html[data-theme]` (named themes only), `html[data-mode]` (forced light/dark),
`html[data-bs-theme]` (resolved scheme, for Bootstrap). `base-head.js` performs the same
resolution synchronously in `<head>` before first paint. Storage changes in another tab are
picked up through the `storage` event. **Migration:** the stored value `default` meant Still
Water before 2026-11-16 and now means the new palette (no rewrite of stored values).

Declarative hooks: `[data-ld-theme-picker]`, `[data-ld-mode-picker]`, `button[data-ld-mode-toggle]`,
`[data-ld-ui-lang-picker]` (`LinguaI18n.renderPicker`), `[data-ld-logout]` (same logout as
`#logout-btn`, wired by one document-level click handler), `.lang-gate[data-lang-gate="zh|ja"]`
(un-hidden by base.js for the matching study language, anywhere on the page).

## Component Specification

### Tokens (`:root` in `styles.css`)
Surfaces and text `--bg --surface --surface-2 --ink --ink-2 --ink-3 --line --line-strong`; brand
`--brand --brand-hover --brand-ink --brand-wash`; reward `--glow --glow-text --glow-wash --glow-ink`;
status `--good* --bad* --warn --warn-core --warn-wash --info --info-wash`; tones `--t1…--t5`; hero
`--hero-a --hero-b --hero-ink --hero-dim`; `--scrim --shadow --focus-ring --nav-bg`; fonts
`--f-display --f-body --f-cjk --f-mono`; radii `--r-sm 9 --r-md 14 --r-btn 16 --r-card 20 --r-hero 24
--r-sheet 26 --r-pill`; layout `--ld-gutter 16px --ld-pad-l/-r --ld-safe-t/-b --ld-tabbar-h 60px
--ld-task-max-w 720px --ld-max-w 1140px`. Dark values: `@media (prefers-color-scheme: dark)` on
`:root:not([data-theme], [data-mode='light'])` and `:root[data-mode='dark']:not([data-theme])`.
Named themes: `:root[data-theme='stillwater'|'midnight'|'sakura'|'forest'|'inkstone']` define the
same tokens. Legacy variables (`--primary`, `--slate-*`, `--bg-*`, `--text-*`, `--border-*`,
`--bs-*`, `--teal`, `--apricot`, …) are aliases of these; no new uses. `--text-muted` = `--ink-3`;
body colour = `--ink`, 15 px.

### Sizing rules
- Viewport meta: `width=device-width, initial-scale=1.0, viewport-fit=cover`.
- Task body: `height: var(--ld-vvh, 100dvh)`; no document scroll. `base.js` sets `--ld-vvh` to
  `visualViewport.height` px when `innerHeight − visualViewport.height > 120` (keyboard open) and
  removes it otherwise.
- `.ld-stage`: `position: relative; flex: 1 1 auto; min-height: 0; overflow-y: auto` (the only
  scroller; `position: relative` keeps absolutely positioned descendants such as `.visually-hidden`
  from extending the document — found at 393×360 on `/dual-translation`).
- `.ld-dock`: pinned, column, 8 px gap, bottom padding includes the safe-area inset.
  `.ld-dock--sticky` for normal scrolling pages (sticks above the tab bar); breaks if a more
  specific rule sets `position` on it.
- Tab pages: body `padding-bottom: calc(var(--ld-tabbar-h) + var(--ld-safe-b))`.
- Breakpoints (range syntax): `width >= 768px` desktop bar/tabs; `width < 576px` modal → bottom
  sheet (handle, slide-up, scrolling body, `88dvh` max; opt out `.modal.ld-no-sheet`;
  `.modal-fullscreen*` untouched).
- Never `100vh` or `vh` minimum heights; inputs ≥ 16 px font; touch targets ≥ 44 px.

### Shared classes (`styles.css`, "SHARED COMPONENTS")
Layout `.ld-screen .ld-stage .ld-dock(--sticky) .ld-gutter .ld-row .ld-col .ld-between .ld-grow
.ld-wrap`; header `.ld-back(__chev) .ld-strip .ld-dots > i.is-done|.is-current|.is-skipped`; type
`.ld-eyebrow .ld-h1 .ld-h2 .ld-muted .ld-small .ld-num .ld-hint .ld-sech .ld-tl .ld-qtext
.ld-prompt(--big) .ld-blank(.is-filled)`; buttons `.ld-btn` (50 px; `--ghost --ok --glow --sm(44)
--icon --block`), `.ld-link(--quiet)`, `.ld-iconbtn`; chips/tags `.ld-chip(s) .ld-tag--warn|due|ok|bad|info|brand
.ld-seal(--lg --ink)`; surfaces `.ld-card(--list) .ld-note(--warn|ok|bad) .ld-hero(__wm __sub)`; lists
`.ld-rowlist .ld-trow(__glyph __mid __end .is-faded) .ld-set(__chev)`; stats `.ld-stats(--two --four)
> .ld-stat > .ld-stat__n`; controls `.ld-seg > button .ld-switch[role=switch]`; answers
`.ld-opts(--two) > .ld-opt(__key)` with `.is-selected .is-correct .is-wrong` (legacy `.answer-option`
`.selected/.correct/.incorrect` restyled the same); feedback `.ld-feedback--ok|bad|idk`; progress
`.ld-bar > i`, `.ld-pips > i`; toast `.ld-toasts > .ld-toast` (`showToast(msg, type)`); motion
`.ld-rise .ld-shake` (disabled under `prefers-reduced-motion`). Bootstrap `.btn* .card .alert-*
.badge.bg-* .form-control .form-select(48 px) .form-switch(44×26) .progress .dropdown-menu .table`
and colour utilities (`.text-*`, `.bg-white/light/body`, `.text-bg-*`, `.border*`) are restyled onto
tokens.

### Area stylesheets
`static/css/redesign/{auth,session,tests,prestudy,translation,trainers,settings}.css` load on
every page after `styles.css` and before `{% block extra_css %}`; each is scoped to its page or
player root because players render both in `/session` and on standalone pages. Tokens only (no
hex; checked 2026-11-16: no hex in `static/css/redesign/*.css`, `static/css/pages/*.css`,
`dt-repair.css`, and no `var(--x, #hex)` fallbacks in templates or JS). The comment-only stubs
`static/css/pages/{test-pinyin,drill,calibration}.css` were deleted; the dead `.test-list-page` and
`.pitch-accent-page` blocks were removed from `styles.css` (`.test-page` kept: `reading_listening.js`
and `test.html` still set it).

### Fonts
Google Fonts via the existing lazy `media="print"` swap; hosts `fonts.googleapis.com` /
`fonts.gstatic.com` only (report-only CSP in `web/security.py`). Base: Bricolage Grotesque,
Instrument Sans, JetBrains Mono. `LinguaFonts.ensureForStudyLanguage(id)` loads Noto Sans + Noto
Serif SC/JP for zh/ja; `LinguaFonts.ensureSerif(code)` the serif only. Inter and Sora removed.

### i18n
Shell keys: `common.back`, `common.close`, `common.nav.main|tab_today|tab_tests|tab_me|more`,
`common.ui_language`, `theme.picker_title`, `theme.name.default`, `theme.desc.default|light|dark`,
`theme.mode_label`, `theme.mode.system|light|dark`, `theme.mode_locked`, `theme.toggle_dark`. The
area files `static/i18n/_redesign/*.json` (65 keys) were merged into the four flat locale files and
the folder deleted. `LinguaI18n.t` returns the key for a missing key, and `applyToDOM` writes that
into `data-i18n` elements, so new keys must exist in all four locales. Re-running the integrator's
key check on 2026-11-16 still lists keys that resolve to nothing and rely on JS English fallbacks
(`session.speed_*` ×8, `dual_translation.target_word`, `dual_translation.target_words_heading`;
all pre-date the redesign) and `session.dt_repair_heading` missing in `es` only (TASK-985).

## Key Architectural Decisions

1. **Decision:** one shell, three modes, with task mode as a body class switchable at runtime.
   - **Rationale:** standalone pages and `/session` share players; the frame must be the same.
   - **Alternatives rejected:** per-page layouts; an SPA router.
2. **Decision:** `dvh` plus a visual-viewport override only while the keyboard is open.
   - **Rationale:** iOS keeps `100dvh` with the keyboard up; always tracking `visualViewport`
     would jitter with toolbar show/hide.
   - **Alternatives rejected:** `100vh`, `-webkit-fill-available`, pinning `body` per overlay.
3. **Decision:** restyle Bootstrap and alias legacy variables instead of rewriting every page.
   - **Rationale:** untouched markup follows the new look and every theme at once.
   - **Alternatives rejected:** removing Bootstrap — too large for one pass.
4. **Decision:** keep the five earlier themes with unchanged colours; reinterpret stored `default`.
   - **Rationale:** learners who chose a theme keep it; others get the approved default.

## Security Considerations

- No new routes in the production app; `/__preview/*` exists only in the test server.
- `setTaskHeader` and `ctx.frame.setHeader` write `textContent` only; server-supplied titles are
  never inserted as HTML.
- No new external hosts; CSP unchanged.
- Logout is wired by a document-level click handler on `[data-ld-logout]` and `#logout-btn`;
  any element with the attribute logs out, so the attribute must not be put on user content.

## Testing Strategy

- `tests/test_redesign_shell.py` (5 tests): tabs + `viewport-fit` on app pages; versioned,
  long-cached redesign stylesheets; no tabs on bare pages; task-mode blocks (dock, back href,
  title); no empty dock without the block.
- Preview harness: `tests/e2e/redesign/serve.py --port N` (real app over the conftest MagicMock
  Supabase; zh=1, en=2, ja=3) and `preview.cjs` (393×659 default, `--size`, `--theme`, `--mode`,
  `--lang`, `--ui`, `--fixtures`, `--click`, `--shot`, `--strict`). Reports document scroll, stage
  overflow, dock in view, horizontal overflow, touch targets < 44 px, unmocked API calls, page
  errors. `walk.py` walks every page and every session player in zh/ja × light/dark.
- Limits: Chromium only (no WebKit, so iOS `dvh`/keyboard behaviour is not reproduced), Google
  Fonts blocked by default, fixture data only, no audio, fake JWT. Needs the Python dependencies
  (a venv existed only in a scratch directory) and `node_modules`.
- Owed: TASK-976–988 and TASK-1007 in [[tasklist/mobile-redesign.tasks]].

## Related Pages

- [[pages/app-shell]] — prose counterpart
- [[decisions/ADR-048-mobile-app-shell]]
- [[pages/pages-overview]], [[pages/study-session.tech]]
- [[features/dt-guided-self-repair.tech]] §8.3
- [[tasklist/mobile-redesign.tasks]]
