---
title: First paint — self-hosted vendor CSS and lazy CJK fonts (2026-11-11)
type: evaluation
status: complete
last_updated: 2026-11-11
---

# First paint — self-hosted vendor CSS and lazy CJK fonts (2026-11-11)

Measures TASK-933 ([[tasklist/latency.tasks]]): Bootstrap 5.3.2, Font Awesome 6.5.1 and Bootstrap
Icons 1.11.2 served from `static/vendor/` instead of jsdelivr/cdnjs; Google Fonts' Latin
families loaded without blocking first paint; Noto Sans SC/JP loaded lazily and only for the
learner's study/UI language. See [[decisions/ADR-042-request-scoped-caching-and-static-asset-caching]].

## Summary

| | Before | After |
|---|---|---|
| First Contentful Paint, cold, phone network (median, 7 logged-in pages) | 2.11–2.23 s | **0.85–0.92 s** (−58 to −62%) |
| Render-blocking requests | 4 (3 third-party) | 3 (all same-origin, cached a year) |
| Third-party requests per page | 5–6 | 2 (Google Fonts CSS + one woff2) |
| Bytes per cold load | 478–583 KB | 393–497 KB (≈ −85 KB) |
| Cumulative Layout Shift | unchanged | unchanged (identical medians on every page) |
| Repeat visits | ~0.26–0.33 s FCP | unchanged |

The Google Fonts stylesheet alone was **186 KB gzipped** (697 KB raw, 721 `@font-face`
rules, 99% Noto Sans SC + JP) and blocked every page. A Japanese learner now downloads 91 KB
of it (JP only, plus 1 KB Latin), and not before first paint.

## Method

- Old code (commit 5896204) and new code served side by side by gunicorn (2 sync workers, as
  in production), live database, the test account (Japanese).
- Third-party origins replaced by a **local HTTPS mock** (`harness/mockcdn/server.js`):
  jsdelivr/cdnjs files from the npm packages (byte-identical, SRI verified), Google Fonts CSS
  and woff2 fetched once from Google and replayed. Each new connection pays **450 ms setup**
  (DNS + TCP + TLS on a phone network), because DevTools throttling delays requests, not
  handshakes. Chromium is forced onto direct connections (`--proxy-server=direct://`, proxy
  env vars removed): an earlier attempt silently went through the sandbox proxy, which refused
  jsdelivr/cdnjs and made the "before" page unstyled — discarded.
- Phone network: Lighthouse "Slow 4G" (150 ms RTT, 1.6 Mbps down) via CDP. Each page loaded
  10× cold (fresh context) and 10× warm (same context), fresh session per page.
- Metrics: FCP and LCP (paint / largest-contentful-paint entries), CLS (layout-shift entries
  without recent input), bytes (`transferSize`, the mock sends `Timing-Allow-Origin`).
- `/login` lands on `/language-selection` for this account in both runs. Its byte count is
  not comparable: the mock 404'd Bootstrap Icons' woff2 in the "before" run (128 KB missing);
  counted, before ≈ 599 KB vs after 513 KB.

## Results


### First Contentful Paint (ms), cold cache, phone network

| Page | run | n | mean | median | p90 | p95 | p99 | max | Δ median |
|---|---|---|---|---|---|---|---|---|---|
| `/login` | before | 10 | 790 | 790 | 796 | 798 | 800 | 800 | |
| | after | 10 | 498 | 494 | 513 | 516 | 519 | 520 | **-37%** |
| `/session` | before | 10 | 2227 | 2228 | 2241 | 2244 | 2247 | 2248 | |
| | after | 10 | 848 | 848 | 853 | 859 | 863 | 864 | **-62%** |
| `/tests` | before | 10 | 2136 | 2140 | 2152 | 2154 | 2156 | 2156 | |
| | after | 10 | 896 | 896 | 904 | 906 | 908 | 908 | **-58%** |
| `/test/<slug>/preview` | before | 10 | 2123 | 2134 | 2148 | 2148 | 2148 | 2148 | |
| | after | 10 | 864 | 860 | 872 | 872 | 872 | 872 | **-60%** |
| `/test/<slug>` | before | 10 | 2170 | 2174 | 2189 | 2195 | 2199 | 2200 | |
| | after | 10 | 916 | 916 | 924 | 924 | 924 | 924 | **-58%** |
| `/test/<slug>/prestudy` | before | 10 | 2116 | 2118 | 2128 | 2130 | 2132 | 2132 | |
| | after | 10 | 856 | 858 | 861 | 864 | 867 | 868 | **-59%** |
| `/flashcards` | before | 10 | 2112 | 2114 | 2136 | 2136 | 2136 | 2136 | |
| | after | 10 | 865 | 868 | 872 | 874 | 876 | 876 | **-59%** |
| `/study-plan` | before | 10 | 2148 | 2152 | 2164 | 2166 | 2168 | 2168 | |
| | after | 10 | 898 | 896 | 908 | 908 | 908 | 908 | **-58%** |

### First Contentful Paint (ms), warm cache, phone network

| Page | run | n | mean | median | p90 | p95 | p99 | max | Δ median |
|---|---|---|---|---|---|---|---|---|---|
| `/login` | before | 10 | 256 | 254 | 261 | 264 | 267 | 268 | |
| | after | 10 | 258 | 258 | 260 | 260 | 260 | 260 | **+2%** |
| `/session` | before | 10 | 256 | 256 | 260 | 260 | 260 | 260 | |
| | after | 10 | 262 | 260 | 269 | 272 | 275 | 276 | **+2%** |
| `/tests` | before | 10 | 300 | 300 | 308 | 308 | 308 | 308 | |
| | after | 10 | 295 | 296 | 300 | 300 | 300 | 300 | **-1%** |
| `/test/<slug>/preview` | before | 10 | 280 | 280 | 284 | 286 | 288 | 288 | |
| | after | 10 | 278 | 276 | 284 | 286 | 288 | 288 | **-1%** |
| `/test/<slug>` | before | 10 | 328 | 328 | 332 | 334 | 336 | 336 | |
| | after | 10 | 333 | 330 | 341 | 347 | 351 | 352 | **+1%** |
| `/test/<slug>/prestudy` | before | 10 | 272 | 272 | 276 | 276 | 276 | 276 | |
| | after | 10 | 274 | 272 | 280 | 282 | 284 | 284 | **+0%** |
| `/flashcards` | before | 10 | 272 | 272 | 277 | 280 | 283 | 284 | |
| | after | 10 | 272 | 272 | 276 | 278 | 280 | 280 | **+0%** |
| `/study-plan` | before | 10 | 308 | 308 | 312 | 314 | 316 | 316 | |
| | after | 10 | 306 | 306 | 309 | 312 | 315 | 316 | **-1%** |

### Largest Contentful Paint (ms), cold cache, phone network

| Page | run | n | mean | median | p90 | p95 | p99 | max | Δ median |
|---|---|---|---|---|---|---|---|---|---|
| `/login` | before | 10 | 790 | 790 | 796 | 798 | 800 | 800 | |
| | after | 10 | 498 | 494 | 513 | 516 | 519 | 520 | **-37%** |
| `/session` | before | 10 | 7262 | 7204 | 7985 | 8150 | 8283 | 8316 | |
| | after | 10 | 7176 | 7132 | 7818 | 7987 | 8122 | 8156 | **-1%** |
| `/tests` | before | 10 | 2136 | 2140 | 2152 | 2154 | 2156 | 2156 | |
| | after | 10 | 896 | 896 | 904 | 906 | 908 | 908 | **-58%** |
| `/test/<slug>/preview` | before | 10 | 4362 | 4172 | 5175 | 5187 | 5197 | 5200 | |
| | after | 10 | 3948 | 3840 | 4424 | 4512 | 4582 | 4600 | **-8%** |
| `/test/<slug>` | before | 10 | 3963 | 3900 | 4000 | 4288 | 4518 | 4576 | |
| | after | 10 | 3845 | 3756 | 4247 | 4496 | 4694 | 4744 | **-4%** |
| `/test/<slug>/prestudy` | before | 10 | 4654 | 4492 | 4898 | 5233 | 5501 | 5568 | |
| | after | 10 | 3873 | 3824 | 4063 | 4168 | 4251 | 4272 | **-15%** |
| `/flashcards` | before | 10 | 3148 | 3126 | 3826 | 3837 | 3846 | 3848 | |
| | after | 10 | 2233 | 1986 | 2876 | 2894 | 2908 | 2912 | **-36%** |
| `/study-plan` | before | 10 | 4679 | 4442 | 4858 | 5571 | 6141 | 6284 | |
| | after | 10 | 3858 | 3672 | 4054 | 4657 | 5139 | 5260 | **-17%** |

### Largest Contentful Paint (ms), warm cache, phone network

| Page | run | n | mean | median | p90 | p95 | p99 | max | Δ median |
|---|---|---|---|---|---|---|---|---|---|
| `/login` | before | 10 | 256 | 254 | 261 | 264 | 267 | 268 | |
| | after | 10 | 258 | 258 | 260 | 260 | 260 | 260 | **+2%** |
| `/session` | before | 10 | 4910 | 5036 | 5404 | 5582 | 5724 | 5760 | |
| | after | 10 | 4951 | 4724 | 5747 | 5903 | 6029 | 6060 | **-6%** |
| `/tests` | before | 10 | 300 | 300 | 308 | 308 | 308 | 308 | |
| | after | 10 | 295 | 296 | 300 | 300 | 300 | 300 | **-1%** |
| `/test/<slug>/preview` | before | 10 | 2336 | 2124 | 2899 | 2986 | 3055 | 3072 | |
| | after | 10 | 2170 | 2032 | 2662 | 2761 | 2840 | 2860 | **-4%** |
| `/test/<slug>` | before | 10 | 1894 | 1838 | 1929 | 2187 | 2393 | 2444 | |
| | after | 10 | 1891 | 1784 | 2218 | 2337 | 2432 | 2456 | **-3%** |
| `/test/<slug>/prestudy` | before | 10 | 2534 | 2322 | 2940 | 3154 | 3325 | 3368 | |
| | after | 10 | 2428 | 2292 | 2717 | 2990 | 3209 | 3264 | **-1%** |
| `/flashcards` | before | 10 | 908 | 872 | 921 | 1104 | 1251 | 1288 | |
| | after | 10 | 925 | 852 | 1215 | 1227 | 1237 | 1240 | **-2%** |
| `/study-plan` | before | 10 | 2627 | 2556 | 2758 | 2945 | 3095 | 3132 | |
| | after | 10 | 2604 | 2528 | 2637 | 2982 | 3259 | 3328 | **-1%** |

### Cumulative Layout Shift, cold cache, phone network

| Page | run | n | mean | median | p90 | p95 | p99 | max | Δ median |
|---|---|---|---|---|---|---|---|---|---|
| `/login` | before | 10 | 0.003 | 0.004 | 0.004 | 0.004 | 0.004 | 0.004 | |
| | after | 10 | 0.003 | 0.002 | 0.003 | 0.004 | 0.004 | 0.004 | **-40%** |
| `/session` | before | 10 | 0.040 | 0.040 | 0.040 | 0.041 | 0.041 | 0.041 | |
| | after | 10 | 0.040 | 0.040 | 0.040 | 0.040 | 0.040 | 0.040 | **+0%** |
| `/tests` | before | 10 | 0.310 | 0.293 | 0.311 | 0.387 | 0.447 | 0.463 | |
| | after | 10 | 0.298 | 0.298 | 0.298 | 0.298 | 0.298 | 0.298 | **+2%** |
| `/test/<slug>/preview` | before | 10 | 0.063 | 0.063 | 0.063 | 0.063 | 0.063 | 0.063 | |
| | after | 10 | 0.063 | 0.063 | 0.063 | 0.063 | 0.063 | 0.063 | **+0%** |
| `/test/<slug>` | before | 10 | 0.348 | 0.348 | 0.348 | 0.348 | 0.348 | 0.348 | |
| | after | 10 | 0.348 | 0.348 | 0.348 | 0.348 | 0.348 | 0.348 | **-0%** |
| `/test/<slug>/prestudy` | before | 10 | 0.051 | 0.050 | 0.051 | 0.051 | 0.052 | 0.052 | |
| | after | 10 | 0.050 | 0.050 | 0.050 | 0.050 | 0.050 | 0.050 | **+0%** |
| `/flashcards` | before | 10 | 0.092 | 0.092 | 0.092 | 0.092 | 0.092 | 0.092 | |
| | after | 10 | 0.092 | 0.092 | 0.092 | 0.092 | 0.092 | 0.092 | **+0%** |
| `/study-plan` | before | 10 | 0.155 | 0.155 | 0.155 | 0.155 | 0.155 | 0.155 | |
| | after | 10 | 0.155 | 0.155 | 0.155 | 0.155 | 0.155 | 0.155 | **+0%** |

### Per cold load (median)

| Page | KB before | KB after | render-blocking before | after | third-party requests before | after |
|---|---|---|---|---|---|---|
| `/login` | 180 | 310 | 5 | 4 | 8 | 4 |
| `/session` | 583 | 497 | 4 | 3 | 5 | 2 |
| `/tests` | 491 | 406 | 4 | 3 | 5 | 2 |
| `/test/<slug>/preview` | 484 | 398 | 4 | 3 | 5 | 2 |
| `/test/<slug>` | 522 | 437 | 4 | 3 | 6 | 2 |
| `/test/<slug>/prestudy` | 515 | 430 | 4 | 3 | 5 | 2 |
| `/flashcards` | 478 | 393 | 4 | 3 | 5 | 2 |
| `/study-plan` | 491 | 406 | 4 | 3 | 5 | 2 |

## What did not change, and why

- **LCP** moves little: on most pages the largest element is content that waits for API data.
- **CLS** is the same before and after. The values are pre-existing: on `/tests` (≈0.29),
  "Today's Test Load" (`#dailyLoadSection`, hidden until `/api/tests/daily-load` returns) is
  inserted *above* "Recommended for You" and pushes the page down; similar late insertions on
  `/test/<slug>` and `/study-plan`. Fixing that means reserving the space or moving the
  section — a layout decision, filed as TASK-934. Separately, the `/tests` skeleton shimmer
  animated `left` (a layout shift every frame while visible); it now animates `transform`.
- **Repeat visits** were already served from the HTTP cache in both versions.

## Checks

- Same-data screenshots, old vs new code: 20/22 identical (calibration differs only by its
  random word); `/language-selection` (Bootstrap Icons) identical at desktop and phone width.
- Walkthrough (`harness/walkthrough.js`): 16/16 — expired/rejected-token renewal, session start,
  practice answer, preview → test hand-off, UI language switch, all learner pages free of
  console errors, 4xx/5xx and raw i18n keys.
- Font routing: a Japanese learner requests only Noto Sans JP, a Chinese learner only SC, a
  Japanese learner with a Chinese UI both, no study language → neither; nothing third-party
  is render-blocking.

## Related Pages
- [[tasklist/latency.tasks]]
- [[evaluations/latency-2026-11-11]]
- [[decisions/ADR-042-request-scoped-caching-and-static-asset-caching]]
