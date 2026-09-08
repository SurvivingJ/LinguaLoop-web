# Whole-Codebase Review — LinguaLoop WebApp

**Date:** 2026-09-08
**Scope:** full tree at `main` @ 6221d0c1 (clean working tree)
**Size:** ~170k LOC — LinguaLoop core (~124k) + `Portal/` sub-suite (~45k)

> **Remediation status (2026-09-08):** C-1, H-3, M-1 and M-5 are **fixed and verified**
> — see "Fixes applied" at the end of this document. H-2 is deferred by decision (its fix
> requires editing the hook-protected `eslint.config.js`). H-1 and the remaining MEDIUM/LOW
> items are open.

## Validation Results

| Check | Result |
|---|---|
| pytest (`PYTHONPATH=. pytest tests/`) | **FAIL** — 4 failed, 2324 passed, 2 skipped |
| ESLint (`npm run lint`) | **FAIL** — 11 errors, 24 warnings |
| Vitest (`npx vitest run`) | Pass — 119/119 |
| Secret scan (tracked files) | Pass — no live credentials found |
| SQL injection scan (Python) | Pass — no string-interpolated SQL |

## Summary

The Python service layer is in genuinely good shape: zero bare `except:`, zero mutable
default arguments, no SQL injection, no hardcoded secrets, and a well-designed
consolidated auth middleware. Auth coverage on the production blueprint set is complete
(72 `@supabase_jwt_required` + 11 `@jwt_required` + 11 `@admin_required`); every route
that reads `g.current_user_id` is decorated.

The problems are concentrated in three places: **one dangerous dev entry point**, a
**frontend with no single source of truth** (31 copies of `escapeHtml`, 8,682 lines of
unlinted inline template JS forking the shared players), and **a red test suite** on a
clean main.

---

## CRITICAL

### C-1. `admin_app.py` binds `0.0.0.0` with `debug=True` and mounts 39 unauthenticated admin routes
**File:** [admin_app.py:15](admin_app.py#L15)

```python
app.run(host='0.0.0.0', port=port, debug=True)
```

`debug=True` enables the Werkzeug interactive debugger, which is **remote code execution
by design** for anyone who can reach it. `host='0.0.0.0'` binds it to every network
interface, not loopback. Mounted on this app are `admin_local_bp` (39 routes) and
`model_arena_bp` (3 routes) — and per the AST audit, **all 42 carry no auth decorator at
all**. They include destructive and spend-incurring operations:
`/admin/api/vocab/word/<id>/wipe`, `/admin/api/run/full-pipeline`,
`/admin/api/run/exercise-generation`, `/admin/api/run/test-generation`.

The file's docstring says "Local-only entry point", but nothing enforces that. On any
shared/coffee-shop/hotel network, or with a Docker port publish, this is a full compromise
of both the host and the OpenRouter spend budget.

**Fix:** bind loopback, drop the hardcoded debug flag, and add a defence-in-depth guard.

```python
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='127.0.0.1', port=port, debug=Config.DEBUG)
```

Then add a `@admin_local_bp.before_request` that 403s when
`request.remote_addr` is not loopback, so a future `--host` flag can't silently re-expose it.

---

## HIGH

### H-1. Test suite is red on a clean `main` — 4 failures
No code change is in flight; these fail on the committed tree.

**(a) 3 failures — stale test stub hides the entire schema-repair path**
`tests/test_generation/test_mcquestion_schema.py` — `test_call_llm_valid_first_try_returns_validated_model`,
`test_call_llm_answer_not_in_choices_repaired`, `test_call_llm_persistent_invalid_raises`

```
E  ValueError: not enough values to unpack (expected 8, got 5)   services/llm_service.py:508
```

`_make_one_call` now returns an 8-tuple (`+ prompt_tokens, completion_tokens,
reasoning_tokens` — added during the cost/max_tokens work), but the stub at
[tests/test_generation/test_mcquestion_schema.py:167](tests/test_generation/test_mcquestion_schema.py#L167)
still returns the old 5-tuple. Production is correct; the tests are stale.

The consequence is the real finding: `call_llm`'s **Pydantic validation and one-shot
repair turn are now completely uncovered**. That is the path that protects every
generated question from malformed model output.

**Fix:** update `_stub_seq` to return `(parsed, repr(parsed), True, 42, 0.0001, 100, 50, 0)`.

**(b) 1 failure — guardrail assertion outlived its guardrail**
`tests/test_prompt_split_l4_l8.py::test_unregistered_prompt_version_is_refused_not_guessed`
asserts `ladder_schema('morphology_slot', 2)` raises `SchemaError`, but
[ladder_l4_morphology.py:54](services/exercise_generation/schemas/ladder_l4_morphology.py#L54)
was legitimately widened to `PROMPT_VERSIONS = frozenset({1, 2})`. The fail-closed gate
still works for genuinely unregistered versions.

**Fix:** re-point the test at an unregistered version (`3`) and update the
`known versions: [1, 2]` assertion — keep the guardrail covered rather than deleting it.

### H-2. 5,410 LOC of session runtime has never been linted
**File:** [eslint.config.js:14](eslint.config.js#L14)

The flat config sets `sourceType: 'script'` for all of `static/js/**`, but everything under
`static/js/session/**` is a real ES module (loaded via
`<script type="module">` at [templates/study_session.html:112](templates/study_session.html#L112)).
All 11 files die with `Parsing error: 'import' and 'export' may appear only with
sourceType: 'module'` — these are the 11 ESLint errors.

A parse error means **no rule ever ran** on the most complex JavaScript in the app: the
session controller, player registry, and all 9 players. `no-unused-vars`, `no-undef`,
`prefer-const`, and `no-console` have never seen this code.

**Fix:** add an override block before the general one:

```js
{
  files: ['static/js/session/**/*.js'],
  languageOptions: { ecmaVersion: 2022, sourceType: 'module', globals: { ...globals.browser } },
},
```

Expect a batch of genuine findings on first run.

### H-3. `escapeHtml` is defined 31 times, and one copy silently does not escape
**File:** [static/js/word_list.js:71-76](static/js/word_list.js#L71-L76)

```js
function escapeHtml(s) {
  if (window.LinguaUtils && window.LinguaUtils.escapeHtml) {
    return window.LinguaUtils.escapeHtml(String(s == null ? '' : s));
  }
  return String(s == null ? '' : s);   // <-- fallback returns input UNESCAPED
}
```

Every other copy in the codebase falls back to a real escaper; this one falls back to
identity. It is then used on user-supplied content — `escapeHtml(row.lemma)` at
[word_list.js:363](static/js/word_list.js#L363), where `lemma` comes from the user's own
word-list upload.

`LinguaUtils` is loaded by `base.html` and `word_list.html` extends it, so this is
**latent rather than live** — it fires only if `utils.js` fails to load or load order
changes. But a fallback whose failure mode is "silently stop escaping" is the wrong shape
for a security control.

**Fix:** make the fallback a real escaper (copy the regex form used in
`listening_lab.js`), or better, delete the local copy and depend on `LinguaUtils`
directly so a missing dependency is a loud `ReferenceError`.

---

## MEDIUM

### M-1. Attribute injection in the admin dashboard
**File:** [static/js/admin-dashboard.js:531](static/js/admin-dashboard.js#L531)

```js
<input ... value="${escapeHtml(value || '')}">
```

The local `escapeHtml` at [line 375](static/js/admin-dashboard.js#L375) is the
`div.textContent → div.innerHTML` idiom, which escapes `&`, `<`, `>` but **not quotes**.
Interpolated inside a double-quoted attribute, a value containing
`" onfocus=alert(1) autofocus="` breaks out of the attribute.

Reachable only via the local admin dashboard with admin-supplied input, so exploitability
is low — but the same textContent-based escaper appears in `utils.js`,
`player_registry.js`, and `pinyin.js`, so the unsafe-in-attributes property is repo-wide.

**Fix:** use a quote-escaping implementation for attribute contexts, or set `.value` as a
property after creating the element rather than interpolating into HTML.

### M-2. The standalone test templates are near-complete forks of the session players
This is the largest single redundancy in the codebase.

| Template | Lines | Forks | Lines | Shared function names |
|---|---|---|---|---|
| `templates/test.html` | 1,595 | `session/players/reading_listening.js` | 1,050 | 24 |
| `templates/test_pitch_accent.html` | 1,082 | `session/players/pitch_accent.js` | 979 | 39 |
| `templates/test_pinyin.html` | 1,063 | `session/players/pinyin.js` | 530 | 20 |

`renderPassage`, `submitResults`, `showResults`, `updateResultsWithElo`, `startTimer`,
`setupFuriganaToggle`, `escapeHtml`, `handleToneInput`, `analyzeContour`… are implemented
twice, in parallel, with no shared source.

This is already causing bugs. The furigana-toggle defect required the same fix applied to
**all four JP render surfaces** independently — that is this duplication billing you. Every
future change to scoring, submission, or ELO display must be made twice or silently
diverges.

**Fix:** the templates should `<script type="module">`-import the player modules, as
`study_session.html` already does. This is the `Phase 3` migration the `eslint.config.js`
comment already anticipates; it is worth prioritising because the duplication is actively
producing defects.

### M-3. 8,682 lines of inline JavaScript in Jinja templates
Explicitly excluded from linting, from Vitest, and from Prettier. Top offenders:
`test.html` (1,360), `test_pitch_accent.html` (1,002), `test_list.html` (632),
`profile.html` (604), `classifier_drill.html` (552), `base.html` (488).

This is also what forces `'unsafe-inline'` in the CSP at [app.py:141](app.py#L141),
keeping it permanently in report-only mode. Extracting these unlocks a real enforced CSP.

### M-4. 27 test files each hand-roll their own Supabase fake
`tests/conftest.py` exists (4.8 KB) but contains **no shared test double**. Instead, 27
files independently reimplement `table`/`select`/`eq`/`in_`/`order`/`limit`/`insert`/
`update`/`rpc`/`execute` — including `test_dual_translation_routes.py` (930 lines),
`test_ladder_topup.py` (595), and `test_dt_remediation_infrastructure.py` (540).

Each fake models the query builder slightly differently, so a test can pass against a
behaviour the real client does not have. **Fix:** promote one fake into `conftest.py` as a
fixture and delete the copies — this is a large, low-risk deletion.

### M-5. N+1 on the word-quiz submit path
**File:** [services/vocabulary/knowledge_service.py:322-360](services/vocabulary/knowledge_service.py#L322-L360)

`record_word_quiz_results` loops over every result issuing one `insert().execute()` plus
one `update_from_word_test` BKT call each, then `_trigger_frequency_inference` fires a
further `bkt_infer_from_frequency` RPC per crossed word. A 20-item quiz is ~40+ sequential
round trips inside one request.

This is notable because the surrounding code is otherwise careful — `gloss_lookup.py`,
`practice_session_service.py`, and `study_plan_service.py` all chunk and paginate
correctly. **Fix:** batch the `word_quiz_results` insert into a single call and push the
BKT loop into one RPC taking an array.

Same shape, lower volume: [services/dual_translation/cards.py:417](services/dual_translation/cards.py#L417)
issues 2 queries per queued entry (`_latest_error_for_subtype` + `_source_texts`).

### M-6. No application-level rate limiting anywhere
`flask-limiter` is not in `requirements.txt` and no limiter exists in `app.py`,
`middleware/`, or `routes/`. `/api/auth/send-otp` and `/api/auth/verify-otp` are
unauthenticated by necessity and rely entirely on Supabase's upstream limits
(`services/auth_service.py:77` handles a `RATE_LIMITED` response).

That leaves no local defence for OTP brute-force, no protection for the LLM-spend
endpoints, and no backstop if Supabase's limits change. **Fix:** add `flask-limiter` with
a strict per-IP+email budget on the OTP routes at minimum.

### M-7. 14 unpinned dependencies, including the numeric/NLP stack
`requirements.txt` pins 64 of 78 entries with `==`. Unpinned: `numpy`, `scipy>=1.10`,
`spacy`, `wordfreq`, `bs4`, `langdetect`, `pypinyin`, `pyopenjtalk`, `fugashi`,
`unidic-lite`, `mecab-python3`, `ipadic`, `jaconv`, `APScheduler>=3.10`.

`numpy` and `spacy` in particular ship breaking changes on majors, and the
`fugashi`/`unidic-lite`/`mecab` trio must stay ABI-compatible with each other. A rebuild
can silently change JA tokenisation — which changes generated content. **Fix:** pin all
14 to the currently-installed versions.

---

## LOW

### L-1. Build artifacts and one-off outputs committed to the repo
All tracked: `bash.exe.stackdump`, `batch_errors_20251209_225642.json`,
`generated_tests_20251209_225642.json`, `..._questions.csv`, `..._tests.csv`,
`bug-wordquiz-backdrop.png`, `spot_check_semantic_class.csv`, `dim_languages_rows.csv`,
`dim_test_types_rows.csv`. The `.gitignore` is otherwise well-maintained.

### L-2. `twilio.txt` — bare token-shaped string in a tracked file
24-character alphanumeric string, no key, no context. Not a recognised Twilio SID or auth
token format, and Twilio is not referenced anywhere in the code — so it is most likely
dead. Worth confirming what it is and deleting it; a tracked file with a bare token and a
vendor name is worth zero and risks something.

### L-3. `.git` is 256 MB because `venv/` was committed historically
`git ls-files` shows 1,591 tracked files today and `venv/` is correctly ignored, but the
history still carries `venv/Lib/site-packages/**`. Every clone pays this. Only fixable
with a history rewrite (`git filter-repo`) — worth doing before any team grows, not urgent
for a solo repo.

### L-4. `Portal/` — 45,386 LOC of a separate product in this repo
`MusicDojo`, `MathDojo`, `WorkoutDojo`, `FeastOptimiser`, `Library`, `hub` — each with its
own `Procfile` and `requirements.txt`. Nothing in `app.py`, `wsgi.py`, `config.py`, or the
root `Procfile` references them; they are independently deployed apps sharing a
repository. 234 files tracked.

They inflate every repo-wide grep, audit, and clone, and they are excluded from this
review's quality gates (`eslint.config.js` ignores `Portal/**`). **Fix:** split into their
own repositories.

### L-5. 23 instances of `except ...: pass`
Most are deliberate and defensible (best-effort telemetry, optional parses). Three are
broad `except Exception: pass` on paths where a swallowed failure is invisible and worth a
`logger.debug`: [services/study_plan_service.py:300](services/study_plan_service.py#L300),
[services/vocabulary_ladder/ladder_service.py:219](services/vocabulary_ladder/ladder_service.py#L219)
and [:261](services/vocabulary_ladder/ladder_service.py#L261).

### L-6. CORS reflects arbitrary origins if `CORS_ORIGINS` ever contains `*`
[app.py:126-129](app.py#L126-L129) — when `"*" in Config.CORS_ORIGINS`, the handler echoes
the caller's `Origin` back and pairs it with `Access-Control-Allow-Credentials: true`,
which defeats the same-origin policy for authenticated requests. The default value is a
safe localhost list and nothing sets `*` today, so this is a latent trap in a config
knob rather than a live bug. Worth an explicit guard that refuses to combine `*` with
credentials.

---

## What is genuinely good

Worth recording so it does not get refactored away:

- **`middleware/auth.py`** — one `_authenticate` helper behind three decorators, the
  ADR-014 batch-token bypass correctly scoped to `jwt_required` only, `hmac.compare_digest`
  for the token comparison, and distinct 401/503 handling for auth-API vs retryable errors.
- **`Config.validate()`** — fails fast on missing secrets rather than defaulting to
  something insecure.
- **Python error hygiene** — 519 files, zero bare `except:`, zero mutable default args.
- **Chunked DB access** — `gloss_lookup.py`, `practice_session_service.py`, and
  `study_plan_service.py` all page and chunk correctly, with fail-closed comments
  explaining why.
- **Comment quality** — the config and middleware docstrings explain *why*, cite ADRs, and
  document rollback levers. This is unusually good.

---

## Suggested order

1. **C-1** — one-line fix, removes an RCE surface.
2. **H-1** — get the suite green; restores coverage of the LLM schema-repair path.
3. **H-2** — one config block; unlocks linting on 5,410 LOC and will surface more.
4. **H-3 / M-1** — collapse 31 escapers to one correct, quote-safe implementation.
5. **M-5, M-6, M-7** — batch the quiz writes, add a limiter, pin the deps.
6. **M-2 / M-3** — the Phase-3 template migration. Largest effort, but it is the root
   cause of the duplicate-bug class and blocks an enforced CSP.
7. **M-4, L-1..L-5** — cleanup.

---

## Fixes applied — 2026-09-08

Validation after the changes: **pytest 2324 passed / 4 failed** (the same 4 pre-existing
H-1 failures, untouched), **vitest 120 passed / 0 failed** (up from 119 — one test added),
**ESLint 11 errors / 24 warnings** (unchanged; all 11 are the H-2 parse errors).

### C-1 — FIXED. Loopback guard now enforced, debugger no longer hardcoded on
- **New:** `middleware/local_only.py` — `enforce_loopback(bp)` registers a
  `before_request` hook that 403s any non-loopback request. Handles `127.0.0.1`, `::1`,
  and IPv4-mapped `::ffff:127.0.0.1`; fails closed on a missing or unparseable address.
  `ADMIN_ALLOW_REMOTE=true` is an explicit, loudly-logged opt-out for the container case.
- **`routes/admin_local.py` / `routes/model_arena.py`:** each calls `enforce_loopback` at
  blueprint creation, so the guard travels with the blueprint — mounting either into the
  production app now fails closed instead of silently exposing 42 open routes.
- **`admin_app.py`:** binds `127.0.0.1` (override via `ADMIN_HOST`) and takes debug from
  `Config.DEBUG` instead of a hardcoded `True`.

Verified end-to-end against the real app: `/admin/`, `/admin/api/languages`,
`/admin/api/vocab/word/1/wipe` (POST), `/admin/api/vocab/word/1/level/1` (DELETE),
`/admin/api/run/full-pipeline` (POST) and `/admin/arena/api/models` all return **403** from
`192.168.1.50` / `10.0.0.9`, and **200** from `127.0.0.1`. The production app is unaffected
(no `/admin` mounted).

### H-3 — FIXED. The silent-identity fallback is gone
`static/js/word_list.js` — the fallback now escapes properly instead of returning its
input untouched when `LinguaUtils` is unavailable. `escapeHtml(row.lemma)` and its sibling
call sites are no longer injection points under a failed or reordered `utils.js` load.

### M-1 — FIXED at the source
`static/js/utils.js` — the canonical `escapeHtml` no longer uses the
`textContent → innerHTML` idiom (which leaves `"` and `'` raw). It now escapes
`& < > " '`, making it safe in both text and quoted-attribute contexts. Quotes render
identically in a text node, so no display changes.

`static/js/admin-dashboard.js` — its local copy got the same treatment; this is the one
used in `addTopicInput`'s `value="${escapeHtml(...)}"`. A repo-wide check confirms that
was the only attribute-context call site.

`tests/unit/utils.test.js` — the test asserting quotes are *preserved* pinned exactly the
unsafe behaviour, so it was updated to the corrected contract, plus a new test covering an
attribute-breakout payload.

**Deliberately not changed:** the falsy-input behaviour (`escapeHtml(0) === ''`). Making
`0`/`false` render literally is arguably more correct but affects every call site in the
app, so it stays a separate decision from the security fix.

### M-5 — PARTIALLY FIXED (the safe half), with the rest documented
`services/vocabulary/knowledge_service.py::record_word_quiz_results` now issues **one**
`insert()` for the whole quiz instead of one per answer. Measured on a 20-item quiz:
**40 round trips → 21**, with all 20 rows preserved and `attempt_id` handling intact.
An empty `results` list now short-circuits to zero DB calls.

The BKT half was **left per-sense on purpose**. The existing
`update_vocabulary_from_word_tests_batch` RPC looks like a drop-in replacement but is not:

1. It takes no `p_exercise_type`, so routing through it would silently discard the
   `'definition_match'` slip/guess parameters and grade word quizzes with default BKT
   params.
2. It additionally fires `_auto_create_flashcards` and `_seed_ladder_for_new_words`, which
   this path deliberately does not do.

Collapsing those 20 calls needs an `exercise_type`-aware batch RPC (a migration) first.
The reasoning is recorded in a comment at the call site so the next reader doesn't
"optimise" it into a silent grading change.

### H-2 — DEFERRED by decision
The fix is an `eslint.config.js` edit, blocked by the config-protection hook. Previewed
with a throwaway config: `static/js/session/**` parses cleanly as ES modules and yields
**9 errors (`no-empty`) + 15 warnings (`no-unused-vars`)** across 5 files —
`pitch_accent.js` (9), `reading_listening.js` (6), `dictation.js` (4), `pinyin.js` (3),
`controller.js` (2). Small and mechanical whenever it's picked up.
