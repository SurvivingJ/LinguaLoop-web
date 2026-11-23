---
title: The Web Package (app wiring)
type: feature
status: complete
tech_page: ./web-package.tech.md
last_updated: 2026-11-23
open_questions:
  - "OPEN: The content-security policy is only reported, never enforced, and it still allows inline scripts and styles. When should it be enforced, and what has to be cleaned up first? (The policy lives in `web/security.py`.)"
  - "OPEN: Rate-limit counters live in each worker's memory, so two workers allow about twice each limit. Move them to Redis, or accept the doubling?"
  - "OPEN: The watchlist sweep job fails every night until its migration is applied (see [[overview/project.tech]])."
---

# The Web Package (app wiring)

## Purpose

The `web/` package holds everything that wires the application together but belongs to no single feature: which HTML pages exist, how errors look, which security headers every response carries, how often a client may call each endpoint, and which jobs run on a timer. It was lifted out of the application's main file so that each concern is small enough to read and test on its own.

## User Story

As a learner I want a wrong address to take me somewhere useful, a failure to show a calm message instead of a stack trace, and the site to stay responsive when someone hammers the sign-in form. As the developer I want one obvious place to look when a page does not exist, a header is missing, a limit is too tight or a nightly job did not run.

## How It Works

1. **Pages.** Each page of the site is one line in a table: a web address, a name and a template. The server only sends the template; the page's own scripts then call the API. Two addresses (`/` and `/logout`) just send the visitor to the login page.
2. **Errors.** Anything that goes wrong under `/api/` comes back as a small JSON message with a stable code, so scripts can react to it. For ordinary pages, an unknown address sends the visitor to the login page and a server failure shows a friendly "something went wrong" page with a link back to the tests.
3. **Security headers.** Every response says that browsers must not guess content types, that the site may only be framed by itself, and how much referrer information to send. Over HTTPS it also asks browsers to stay on HTTPS for a year. HTML pages carry a content-security policy in *report-only* mode: browsers would report violations but nothing is blocked, because the pages still use inline scripts and styles. Requests with a body larger than 1 MiB are refused before any code reads them.
4. **Rate limits.** Every API call counts against a per-user allowance (per address when not signed in). Sign-in, language-model-backed and admin calls have much stricter allowances. The health check is never limited.
5. **Scheduler.** Nine timed jobs run in the background: the nightly error clustering, difficulty calibration, time-estimate refresh, model health probe, content-queue drain, word-watchlist sweep, knowledge snapshots, placement clean-up, and the weekly study-plan recompute.

## Constraints & Edge Cases

- The package is started once per worker process, and the site runs two workers, so limits, the scheduler and some caches exist twice. The jobs protect themselves so that two workers never do the same work twice.
- A missing or broken error template must never hide the original error: the error page falls back to a plain sentence.
- Tests build the app without a scheduler and with the limiter off unless a test asks for it.

## Business Rules

- API errors always use the same JSON shape; only the older sign-in routes keep their own shape.
- A non-API 404 redirects to login; a 405 is always JSON, even on a page address.
- No page route reads the user's identity; pages are public shells.
- A job that crashes is logged and never takes the scheduler down.

## Open Questions

- OPEN: content-security policy enforcement (see frontmatter).
- OPEN: shared rate-limit storage (see frontmatter).

## Related Pages

- [[features/web-package.tech]] — Technical specification
- [[api/rpcs]] — The API in plain English
- [[api/rpcs.tech]] — Every route, including the page routes
- [[overview/project.tech]] — Architecture, scheduler table, gates
- [[features/security-hardening]] — Earlier security work
