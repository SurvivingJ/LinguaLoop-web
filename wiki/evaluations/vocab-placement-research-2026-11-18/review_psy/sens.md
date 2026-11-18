# partial.json [stop] extra=['partial=1'] n/pop=300

## Length, stop, counts (95% intervals, ADR-051 rules)
| pop | items | early stop | early stop: beg / int / adv | m bias / MAE / cover95 | m+r bias / MAE / cover95 | guard binds (lo or hi) |
|---|---|---|---|---|---|---|
| zh·en-L1 | 56.5 | 28% | 68% / 17% / 0% | -1.3 / 6.7 / 94% | +1.1 / 5.4 / 96% | 34% |
| zh·ja-L1 | 60.4 | 0% | 0% / 0% / 0% | +0.1 / 6.9 / 95% | +4.0 / 7.4 / 92% | 1% |
| ja·en-L1 | 56.9 | 28% | 62% / 24% / 2% | -1.0 / 6.7 / 93% | +0.0 / 6.1 / 95% | 47% |
| ja·zh-L1 | 60.2 | 3% | 5% / 1% / 1% | +0.0 / 6.8 / 94% | +2.8 / 7.4 / 92% | 5% |
## Level range of draft §5.3 (95% bounds, 80% threshold), m+r; truth = placement over pool list words
| pop | point ±1 (sim metric) | range contains truth | lower = 0 | lower=0 among true place ≥ 2 | upper = 0 | lower = upper | mean width (levels) | copy: "k" / "a–b" / "at most k" / "not yet" |
|---|---|---|---|---|---|---|---|---|
| zh·en-L1 | 78% | 98% | 100% | 100% (n=254) | 42% | 42% | 3.37 | 0% / 0% / 57% / 42% |
| zh·ja-L1 | 80% | 98% | 100% | 100% (n=241) | 36% | 36% | 3.67 | 0% / 0% / 64% / 36% |
| ja·en-L1 | 85% | 98% | 100% | 100% (n=191) | 57% | 57% | 1.77 | 0% / 0% / 43% / 57% |
| ja·zh-L1 | 86% | 99% | 100% | 100% (n=177) | 49% | 49% | 2.25 | 0% / 0% / 51% / 49% |

# gamma25.json [stop] extra=['gamma_max=2.5'] n/pop=300

## Length, stop, counts (95% intervals, ADR-051 rules)
| pop | items | early stop | early stop: beg / int / adv | m bias / MAE / cover95 | m+r bias / MAE / cover95 | guard binds (lo or hi) |
|---|---|---|---|---|---|---|
| zh·en-L1 | 56.9 | 26% | 63% / 16% / 1% | -0.8 / 7.1 / 94% | +0.4 / 5.7 / 95% | 32% |
| zh·ja-L1 | 60.4 | 0% | 0% / 0% / 0% | -0.0 / 7.2 / 95% | -0.1 / 6.1 / 95% | 0% |
| ja·en-L1 | 57.5 | 24% | 56% / 16% / 2% | -1.2 / 6.8 / 93% | -0.8 / 6.0 / 94% | 45% |
| ja·zh-L1 | 60.2 | 2% | 3% / 1% / 2% | +0.1 / 6.8 / 95% | +0.5 / 7.0 / 92% | 2% |
## Level range of draft §5.3 (95% bounds, 80% threshold), m+r; truth = placement over pool list words
| pop | point ±1 (sim metric) | range contains truth | lower = 0 | lower=0 among true place ≥ 2 | upper = 0 | lower = upper | mean width (levels) | copy: "k" / "a–b" / "at most k" / "not yet" |
|---|---|---|---|---|---|---|---|---|
| zh·en-L1 | 62% | 88% | 100% | 100% (n=332) | 39% | 39% | 3.36 | 0% / 0% / 61% / 39% |
| zh·ja-L1 | 66% | 89% | 100% | 100% (n=316) | 40% | 40% | 3.41 | 0% / 0% / 60% / 40% |
| ja·en-L1 | 67% | 85% | 100% | 100% (n=261) | 57% | 57% | 1.74 | 0% / 0% / 43% / 57% |
| ja·zh-L1 | 73% | 93% | 100% | 100% (n=247) | 50% | 50% | 2.12 | 0% / 0% / 50% / 50% |

# eps18.json [stop] extra=['sig_eps=1.8'] n/pop=300

## Length, stop, counts (95% intervals, ADR-051 rules)
| pop | items | early stop | early stop: beg / int / adv | m bias / MAE / cover95 | m+r bias / MAE / cover95 | guard binds (lo or hi) |
|---|---|---|---|---|---|---|
| zh·en-L1 | 57.0 | 25% | 62% / 14% / 0% | -1.2 / 7.0 / 93% | +0.3 / 5.4 / 95% | 31% |
| zh·ja-L1 | 60.4 | 0% | 1% / 0% / 0% | +0.5 / 7.0 / 94% | -0.2 / 6.1 / 95% | 0% |
| ja·en-L1 | 57.3 | 26% | 60% / 18% / 1% | -0.9 / 7.0 / 93% | -0.2 / 6.2 / 94% | 47% |
| ja·zh-L1 | 60.2 | 2% | 3% / 1% / 1% | +0.2 / 6.8 / 94% | +0.3 / 6.7 / 94% | 3% |
## Level range of draft §5.3 (95% bounds, 80% threshold), m+r; truth = placement over pool list words
| pop | point ±1 (sim metric) | range contains truth | lower = 0 | lower=0 among true place ≥ 2 | upper = 0 | lower = upper | mean width (levels) | copy: "k" / "a–b" / "at most k" / "not yet" |
|---|---|---|---|---|---|---|---|---|
| zh·en-L1 | 78% | 98% | 100% | 100% (n=230) | 43% | 43% | 3.23 | 0% / 0% / 57% / 43% |
| zh·ja-L1 | 76% | 98% | 100% | 100% (n=229) | 41% | 41% | 3.29 | 0% / 0% / 59% / 41% |
| ja·en-L1 | 83% | 99% | 100% | 100% (n=176) | 56% | 56% | 1.78 | 0% / 0% / 44% / 56% |
| ja·zh-L1 | 85% | 99% | 100% | 99% (n=162) | 50% | 51% | 2.07 | 0% / 0% / 49% / 50% |

