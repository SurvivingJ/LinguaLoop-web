# Frontend review (static/js, templates, i18n, tooling)

Prior-review status: H-3 (escapeHtml x31) STILL OPEN, reduced to 27 definitions. M-1 (attribute injection in admin dashboard) FIXED (admin-dashboard.js:370-379 now escapes quotes). M-2 (standalone template forks of session players) STILL OPEN. M-3 (inline JS) STILL OPEN (8,256 inline script lines).

### [MEDIUM] Unescaped LLM-generated question.explanation injected via innerHTML
- Category: security
- Location: templates/test.html:667 ; static/js/session/players/reading_listening.js:311
- Problem: `question.explanation` is interpolated raw into a template literal assigned to innerHTML, while every sibling field (choice text, etc.) is escaped. Explanations are generated content, so a prompt-injected or malicious string executes script in the learner's session. The JWT lives in localStorage (see next finding), so this is a token-theft path.
- Evidence: `${question.explanation}` at both sites with no escape call; `choiceAttr` on the neighbouring lines uses escapeHtmlForFurigana.
- Fix: wrap in escapeHtml (or sanitize server-side if basic markup is intended).

### [MEDIUM] JWT access token kept in localStorage and reachable from any XSS
- Category: security
- Location: templates/base.html:74,140,556 ; templates/login.html:232 ; static/js/utils.js:178
- Problem: Access JWT and user_data are in web storage; refresh is correctly HttpOnly, but the access token plus a monkey-patched `localStorage.getItem` shim (base.html ~488-500) widens exposure. No CSP was seen in the templates.
- Evidence: `localStorage.setItem('jwt_token', ...)` in base.html and login.html.
- Fix: keep short access-token TTL (already refreshes), add a strict CSP, and fix the XSS sinks above.

### [MEDIUM] Nine session.speed_* i18n keys missing from all four locales; fallback defeated
- Category: correctness
- Location: static/js/session/players/speed_round.js:82,94,114,122,129,134,208,299 (keys: speed_unavailable, speed_error, speed_no_mastered, speed_too_few, speed_empty, speed_timed_out, speed_done, speed_timeouts, speed_heading)
- Problem: Only `session.speed_round_heading` exists in en/es/ja/zh.json. The local helper `LinguaI18n.t(key) || fallback || key` never reaches the English fallback because i18n-manager.js:104-125 returns the key itself on a miss, so users see raw key strings.
- Evidence: node diff of the four JSON files: 713 keys each, identical sets (no cross-locale drift), but these 9 used keys are absent from all of them.
- Fix: add the keys to all four files; make the helper compare `result === key` before using the fallback.

### [MEDIUM] Standalone test templates are still near-forks of the session players (M-2 open)
- Category: redundancy
- Location: templates/test.html (1596 lines) vs static/js/session/players/reading_listening.js; test_pitch_accent.html vs players/pitch_accent.js; test_pinyin.html vs pinyin.js; test_dictation.html vs dictation.js; classifier_drill.html vs classifier_drill.js
- Problem: Function-name overlap is 25/34, 39/40, 20/21, 10/11, 22/24. Every bug fix (e.g. the furigana default-off fix, escaping fixes) must land twice and has already drifted (the explanation XSS exists in both; escapers differ).
- Evidence: shared-function-name count script across the five pairs.
- Fix: route the standalone pages to the session player (single-item mode) and delete the template-inlined copies.

### [MEDIUM] Inline script volume (M-3 open): 8,256 lines of inline JS, un-linted
- Category: maintainability
- Location: templates/test.html (1361 inline), test_pitch_accent.html (1003), test_list.html (633), profile.html (605), classifier_drill.html (553), test_pinyin.html (537), calibration.html (530), base.html (490)
- Problem: eslint (eslint.config.js header) and vitest (vitest.config.js:5,11) cover only static/js, so the bulk of the logic is outside lint/test/coverage. Also blocks a CSP without 'unsafe-inline'.
- Fix: extract into static/js modules page by page, starting with the forks above.

### [MEDIUM] escapeHtml / esc still defined 27 times (H-3 open); several variants do not escape quotes
- Category: redundancy
- Location: static/js: admin-dashboard.js:373, dual_translation.js:139, dual_translation_profile.js:28, word_list.js:76, utils.js:73 (canonical), session/controller.js:351, session/player_registry.js:97, players/{classifier_drill,dictation,pinyin,pitch_accent(x2),reading_listening}.js; templates: calibration:235, classifier_drill:915, counter_drill:206, profile:704, test:262, test_dictation:673, test_list:263, test_pinyin:533, test_pitch_accent:112,1071, test_preview:364 (+ admin_vocab_preview `esc`, speed_round `localEsc`)
- Problem: 27 files/definitions (23 files). The textContent/innerHTML variants (profile.html:704, test_list.html:263, test_pinyin.html:533, test_preview.html:364, players/pinyin.js:24, player_registry.js:97) leave `"` and `'` unescaped; test_dictation.html:673 and dictation.js:299 skip `'`. I found no current attribute-context use of the weak ones, so not exploitable today, but one future `value="${escapeHtml(x)}"` makes it so (this is exactly how M-1 happened).
- Evidence: grep of definitions; verified utils.js:73-76 escapes all five characters and is loaded globally by base.html:477. Comments in profile/test_pinyin/test_preview say they are "kept local because this page doesn't load" utils.js, i.e. standalone pages not extending base.
- Fix: load utils.js everywhere and delete the copies; make LinguaUtils.escapeHtml the only one.

### [LOW] admin setStatus builds HTML from server error strings
- Category: security
- Location: static/js/admin-dashboard.js:18-26 (callers 141,149,1428,1435)
- Problem: `message` (err.error / err.message) goes into innerHTML unescaped. Admin-only and error text, hence low.
- Fix: textContent for the message part.

### [LOW] Unescaped lang.name / flag in innerHTML
- Category: security
- Location: templates/profile.html:561,592 ; templates/study_plan.html:249
- Problem: names come from a static/DB dimension table, not user input. Defence-in-depth only.
- Fix: escape.

### [LOW] No SRI on CDN assets in admin_dashboard.html and language_selection.html
- Category: security
- Location: templates/admin_dashboard.html:7,8,951 ; templates/language_selection.html:82
- Problem: Bootstrap/FontAwesome/bootstrap-icons loaded without integrity attributes (base.html's equivalents span multiple lines and appear to carry them). Admin dashboard is the highest-privilege page.
- Fix: add integrity + crossorigin, or vendor locally.

### [LOW] Duplicated auth helpers
- Category: redundancy
- Location: static/js/utils.js:177 (getAuthHeaders, exported at :393, no caller found outside utils.js); templates/base.html:572 (window.authFetch); templates/admin_vocab_preview.html:67 (authFetch wrapper); static/js/admin-dashboard.js:~10 (own fetch wrapper to ADMIN_API); base.html:722,755 and login.html:449 build Authorization headers by hand
- Problem: four ways to attach a bearer token; getAuthHeaders reads localStorage directly so it skips the sessionStorage tier and the refresh flow. authFetch also forces Content-Type: application/json even for non-JSON bodies.
- Fix: delete getAuthHeaders, route everything through window.authFetch.

### [LOW] Furigana toggle logic duplicated four times
- Category: redundancy
- Location: templates/test.html, templates/test_pitch_accent.html, players/reading_listening.js:126, players/pitch_accent.js:43 (escapeHtmlForFurigana / escapeHtmlFuri variants)
- Fix: resolves automatically when the forks are merged.

### [LOW] Unused / overstated i18n keys
- Category: legacy/dead
- Location: static/i18n/*.json
- Problem: Clearly unreferenced: classifier_drill.subtitle, common.nav.exercises, common.nav.flashcards, common.nav.user_menu, common.nav.vocab_dojo, difficulty.advanced, session.dt_error_card_pending (names built dynamically for dual_translation.dim.*/category.*/highlight_reason.* are in use). Locale parity is otherwise perfect (713 keys in each of en/es/ja/zh).
- Fix: verify and prune.

### [LOW] Templates for non-existent product areas may be dead
- Category: legacy/dead
- Location: routes (render_template calls) reference templates not present in templates/ (exercises/index.html, programs/index.html, workouts/index.html, dashboard.html, planner*.html, recipes*.html, shopping_list.html, skills.html, wishlist.html, settings.html, self_assessment.html, error.html, index.html); conversely exercise_type_effectiveness.html is rendered only via routes/admin_local.py (dynamic). PLAUSIBLE: those routes belong to a different/legacy app (Portal?) and are dead or would 500.
- Fix: confirm which blueprints are registered and delete the dead ones.

### [LOW] Not found (checked)
- No `|safe`, `Markup(`, or autoescape-off anywhere in templates/routes; no JWT in URLs; no `next=` redirect parameters (login redirects are fixed paths); all JS files in static/js are referenced by at least one template or script; session players register and remove listeners/timers via cleanup arrays (no leak found). State-changing fetches use Bearer headers (CSRF mostly N/A); refresh cookies are SameSite=Lax (routes/auth.py:38-87).
