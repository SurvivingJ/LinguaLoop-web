# Review 10: Portal/

Relationship: Portal/ is NOT imported, served or referenced by the main app (no hits in app.py, routes/, templates/, config.py, wsgi.py, Procfile; only hits are .claude/settings.local.json and eslint.config.js:9 which ignores 'Portal/**'). Each sub-app is an independent Flask app with its own Procfile, wsgi.py and requirements.txt (hub, FeastOptimiser, Library, MathDojo, MusicDojo have Procfiles; WorkoutDojo has none). The hub (Portal/hub/app.py:5-42) is only a static link list to separate subdomains (math./music./feast./library.linguadojo.com). 234 tracked files, 189 code files, 25 commits touching it. No tests link the two. It is a separate product sharing only a repo and a domain name.

### [HIGH] Library write/delete API has no authentication and is internet-exposed
- Category: security
- Location: Portal/Library/app.py:20-200 (POST/PATCH/DELETE /api/books, /api/videos/sync, /api/watched)
- Problem: All mutating endpoints are unauthenticated; `/api/videos/sync` replaces the entire videos file with any JSON array. Deployed publicly at library.linguadojo.com (hub/app.py:38-43). Anyone can wipe or poison the collection.
- Evidence: grep for auth/login/Authorization in Portal/**.py only matches Library/app.py (the word "Authorization"-free mentions) and WorkoutDojo/schemas.py, none enforce anything; no before_request hook.
- Fix: Add a shared token/basic-auth check (env var) on non-GET routes, or put the app behind the hub/proxy auth.

### [HIGH] Library /api/proxy-image is an open SSRF / bandwidth proxy
- Category: security
- Location: Portal/Library/app.py:211-224
- Problem: Only checks `url.startswith("https://")`; server fetches any https host (incl. internal https services, redirects followed by requests by default) and returns the body with the upstream Content-Type, so it can serve attacker-controlled HTML/JS from your origin (reflected XSS-by-proxy) and has no size limit despite `stream=True` (reads `resp.content` fully).
- Evidence: lines 214-222.
- Fix: Allowlist image hosts, resolve and block private IPs, disable redirects, force Content-Type to image/* and cap bytes.

### [MEDIUM] Every sub-app API is unauthenticated, CORS is wildcard on FeastOptimiser
- Category: security
- Location: Portal/FeastOptimiser/app.py:16 (`origins: "*"`), Portal/MusicDojo/app.py:326-380, Portal/MathDojo/app.py:101-135
- Problem: FeastOptimiser allows any origin on /api/*; MusicDojo lets anyone POST/DELETE guitar100k exercises and logs; MathDojo lets anyone write any profile. Single-user design with public deployment.
- Evidence: cited lines; no auth code anywhere.
- Fix: Restrict CORS to the sub-domain, add the same shared token as above for writes.

### [MEDIUM] MathDojo profile name used raw in a filename; unbounded profile creation
- Category: security
- Location: Portal/MathDojo/profile_store.py:17-18, 49-54; Portal/MathDojo/app.py:101-135
- Problem: `<name>` from the URL becomes `data/{name}_stats.json` with no validation. Flask's default converter blocks "/" so traversal is limited on Linux (PLAUSIBLE on Windows with backslashes), but any caller can create unlimited files (disk fill) and read any `*_stats.json`.
- Evidence: no sanitisation in _stats_path.
- Fix: Validate `^[a-z0-9_-]{1,32}$` and cap profile count.

### [MEDIUM] Weak default secrets and debug defaults
- Category: security
- Location: Portal/WorkoutDojo/app.py:24-25, 75; Portal/FeastOptimiser/config.py:8; Portal/FeastOptimiser/wsgi.py:6
- Problem: WorkoutDojo `DEBUG` defaults to "true" and `SECRET_KEY` to "workoutos-dev-secret"; FeastOptimiser defaults SECRET_KEY to 'dev-secret-change-me' and its wsgi.py `__main__` runs debug=True. If deployed without env overrides, Werkzeug debug/predictable signing keys result. No real hardcoded API keys found (FeastOptimiser keys come from os.environ, config.py:15-28).
- Evidence: cited lines.
- Fix: Default to production-safe values and fail startup if SECRET_KEY unset.

### [MEDIUM] Error messages leak internals
- Category: security
- Location: Portal/MusicDojo/app.py:343-344 and many `jsonify({'error': str(e)})` in MathDojo/MusicDojo
- Problem: Raw exception text is returned to clients.
- Evidence: line 344 returns 500 with str(e).
- Fix: Log and return generic messages.

### [MEDIUM] Third-party CDN scripts without SRI
- Category: security
- Location: Portal/Library/templates/index.html:237-238 (unpkg html5-qrcode, cdnjs color-thief); Portal/MusicDojo/templates/index.html:610-611 (jsdelivr vexflow, Tone); Portal/WorkoutDojo/templates/analytics/index.html:273 (chart.js); hub/Library font-awesome CSS
- Problem: No `integrity=` attributes anywhere (0 matches in Portal html). unpkg/jsdelivr supply-chain compromise runs JS on the origin, which in Library has write access to the data API.
- Evidence: grep integrity= returned 0.
- Fix: Add SRI hashes or vendor the files.

### [MEDIUM] Library innerHTML interpolates unescaped attribute values; esc() does not escape quotes
- Category: security
- Location: Portal/Library/static/js/library.js:434 (`src="${opt.cover_url}"`), 563-569 (esc via textContent->innerHTML)
- Problem: cover_url (from Google Books / user-posted book JSON, which the unauthenticated API accepts) is placed raw in an attribute; esc() leaves `"` unescaped so it is unsafe in attribute context. Stored XSS needs a crafted book record (reachable via the unauthenticated POST). Remaining ~65 innerHTML sites in MusicDojo and ~20 in WorkoutDojo not individually audited (PLAUSIBLE risk; mostly static strings/numbers).
- Evidence: lines cited.
- Fix: Use DOM APIs/setAttribute or an escape that handles quotes; validate cover_url scheme.

### [MEDIUM] Personal/runtime data committed to git
- Category: maintainability
- Location: Portal/MathDojo/data/james_stats.json, Portal/WorkoutDojo/data/history/*.csv, Portal/MusicDojo/local_data/*_logs.csv, Portal/FeastOptimiser/data/store/*.csv and three `*.csv.lock` files
- Problem: Live user state and filelock artifacts are tracked, producing noisy diffs and risking overwrite on deploy (FeastOptimiser comment at app.py:30 admits ephemeral storage on Railway, so tracked seeds are lost anyway). Library correctly gitignores data/.
- Evidence: `git ls-files` lists them.
- Fix: gitignore runtime data and .lock files; keep only seed fixtures.

### [MEDIUM] Recommend: split Portal/ into its own repo
- Category: maintainability
- Location: Portal/
- Problem: 189 code files with no code, import, test, CI or deploy coupling to LinguaLoop; 5 separately-deployed Flask apps with differing pinned deps (flask 3.0.0/3.0.3/>=3.0, gunicorn 21.2/22) and eslint.config.js:9 already ignores it. It inflates repo, review surface and AI-agent context for the real product.
- Evidence: zero references from app.py/routes/templates/config/Procfile/wsgi.py; independent requirements per app.
- Fix: `git filter-repo --subdirectory-filter Portal` into a new repo (keep history), then remove from this one.

### [LOW] WorkoutDojo is half-deployed (no Procfile/wsgi, hub does not list it)
- Category: legacy/dead
- Location: Portal/WorkoutDojo/ (app.py, config.py, schemas.py; no Procfile/wsgi.py), Portal/hub/app.py:5-42
- Problem: Not linked from the hub PROJECTS list and only runnable via `app.run(debug=True, port=5001)` (app.py:75). Likely local-only/unfinished; also has WorkoutOS_Addendum.md spec.
- Evidence: PROJECTS lacks WorkoutDojo; no deploy files.
- Fix: Decide: finish deploy or archive.

### [LOW] Stray prototype / duplicate artefacts
- Category: legacy/dead
- Location: Portal/MusicDojo/music-trainer(1).html (91.9K), Portal/MusicDojo/generate_slonimsky.py, committed static/data/slonimsky_library.json
- Problem: Browser-downloaded duplicate filename "(1)" single-file prototype, unreferenced by app.py/templates (grep: no refs); generated data committed with its generator.
- Evidence: grep for "music-trainer(1)" in .py/.md/.html found nothing.
- Fix: Delete the prototype; regenerate the library at build time or keep one.

### [LOW] Duplicated boilerplate and client modules across sub-apps
- Category: redundancy
- Location: Portal/{hub,Library,MathDojo,MusicDojo,FeastOptimiser}/wsgi.py, Procfile, app.py bootstrap; Portal/MathDojo/static/js/storage-manager.js vs Portal/MusicDojo/static/js/storage-manager.js; audio-manager/theme-manager patterns; `escHtml` redefined 5x in WorkoutDojo/static/js (active_session.js:1381, analytics.js:322, program_builder.js:443, progression_builder.js:423, workout_builder.js:428) plus Library esc
- Problem: Same names, near-identical roles (storage managers differ by 754 diff lines but share purpose), copy-pasted wsgi/Procfile/health route and atomic JSON store (Library/storage.py vs FeastOptimiser CSVStore vs MathDojo profile_store, which has no atomic write). No shared package.
- Evidence: diff -q; grep results above.
- Fix: Extract a shared small package/static asset if the repo is kept; otherwise accept in split-out repo.

### [LOW] Non-atomic JSON writes in MathDojo; lock only per-process
- Category: correctness
- Location: Portal/MathDojo/profile_store.py:49-56, 101
- Problem: `open(path,'w')` truncates in place under a `threading.Lock`; with 2 gunicorn workers (Procfile) concurrent record calls race across processes and a crash mid-write corrupts the profile (Library/storage.py uses tmp+os.replace, MathDojo does not).
- Evidence: lines cited; MathDojo Procfile `--workers 2`.
- Fix: Write temp file + os.replace and use file lock or one worker.

### [LOW] Library storage has same multi-worker race
- Category: correctness
- Location: Portal/Library/storage.py:12-35, app.py:32-48
- Problem: read-modify-write of books.json guarded by a threading.Lock only per call (load and save take the lock separately), so concurrent requests and 2 workers lose updates; the ISBN duplicate check is non-atomic.
- Evidence: `_load`/`_save` lock independently; Library Procfile `--workers 2`.
- Fix: Hold a (file) lock across the whole read-modify-write.

### [LOW] VexFlow loaded from the CommonJS build in a browser
- Category: correctness
- Location: Portal/MusicDojo/templates/index.html:610
- Problem: `build/cjs/vexflow.js` is the CJS bundle; in a plain script tag it may not expose the global (PLAUSIBLE; the 4.2.x docs recommend build/cjs for script tags, so verify sight-reading rendering works).
- Evidence: URL only; not run.
- Fix: Verify in-browser; pin to the documented browser build.

Counts: 0 CRITICAL, 2 HIGH, 8 MEDIUM, 6 LOW (16 total)
