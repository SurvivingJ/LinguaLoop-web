# main.json [stop] extra=[] n/pop=500

## Length, stop, counts (95% intervals, ADR-051 rules)
| pop | items | early stop | early stop: beg / int / adv | m bias / MAE / cover95 | m+r bias / MAE / cover95 | guard binds (lo or hi) |
|---|---|---|---|---|---|---|
| zh·en-L1 | 56.6 | 28% | 64% / 18% / 0% | -1.1 / 6.7 / 94% | +0.3 / 5.3 / 96% | 31% |
| zh·ja-L1 | 60.4 | 0% | 1% / 0% / 0% | -0.2 / 7.2 / 95% | -0.2 / 6.3 / 96% | 0% |
| ja·en-L1 | 56.9 | 28% | 62% / 22% / 2% | -1.1 / 6.6 / 94% | -0.4 / 5.9 / 94% | 44% |
| ja·zh-L1 | 60.2 | 2% | 4% / 1% / 2% | +0.1 / 6.8 / 94% | +0.3 / 6.7 / 93% | 3% |

## ADR-051 labels a placement alone receives (m+r headline / meaning)
| pop | m+r labels | meaning labels |
|---|---|---|
| zh·en-L1 | rough 50%, fewer_than 50% | rough 51%, fewer_than 48%, too_uncertain 1% |
| zh·ja-L1 | rough 46%, fewer_than 53%, too_uncertain 1% | rough 96%, fewer_than 3%, too_uncertain 2% |
| ja·en-L1 | rough 58%, fewer_than 42% | rough 56%, fewer_than 44%, too_uncertain 0% |
| ja·zh-L1 | rough 66%, fewer_than 33%, too_uncertain 1% | rough 96%, fewer_than 3%, too_uncertain 0% |

## Level range of draft §5.3 (95% bounds, 80% threshold), m+r; truth = placement over pool list words
| pop | point ±1 (sim metric) | range contains truth | lower = 0 | lower=0 among true place ≥ 2 | upper = 0 | lower = upper | mean width (levels) | copy: "k" / "a–b" / "at most k" / "not yet" |
|---|---|---|---|---|---|---|---|---|
| zh·en-L1 | 79% | 97% | 100% | 100% (n=404) | 44% | 44% | 3.19 | 0% / 0% / 56% / 44% |
| zh·ja-L1 | 78% | 98% | 100% | 100% (n=394) | 43% | 43% | 3.27 | 0% / 0% / 57% / 43% |
| ja·en-L1 | 84% | 98% | 100% | 100% (n=309) | 58% | 58% | 1.74 | 0% / 0% / 42% / 58% |
| ja·zh-L1 | 85% | 99% | 100% | 100% (n=290) | 50% | 50% | 2.15 | 0% / 0% / 50% / 50% |

## Level range by true m+r placement (all pops of a language pooled)

zh: true place -> n, mean lower, mean upper, share lower=0, share range contains truth, share point ±1
  0: n=1159, lower 0.00, upper 1.08, lower=0 100%, contains 100%, point±1 99%
  1: n=43, lower 0.00, upper 2.93, lower=0 100%, contains 60%, point±1 93%
  2: n=102, lower 0.00, upper 4.44, lower=0 100%, contains 83%, point±1 3%
  3: n=77, lower 0.00, upper 5.31, lower=0 100%, contains 86%, point±1 12%
  4: n=92, lower 0.00, upper 6.40, lower=0 100%, contains 98%, point±1 21%
  5: n=90, lower 0.00, upper 6.58, lower=0 100%, contains 97%, point±1 39%
  6: n=141, lower 0.00, upper 6.92, lower=0 100%, contains 99%, point±1 57%
  7: n=296, lower 0.00, upper 7.00, lower=0 100%, contains 100%, point±1 82%

ja: true place -> n, mean lower, mean upper, share lower=0, share range contains truth, share point ±1
  0: n=1342, lower 0.00, upper 0.68, lower=0 100%, contains 100%, point±1 99%
  1: n=59, lower 0.00, upper 3.17, lower=0 100%, contains 81%, point±1 97%
  2: n=157, lower 0.00, upper 3.96, lower=0 100%, contains 90%, point±1 26%
  3: n=81, lower 0.00, upper 4.63, lower=0 100%, contains 95%, point±1 35%
  4: n=97, lower 0.00, upper 4.89, lower=0 100%, contains 99%, point±1 44%
  5: n=264, lower 0.00, upper 5.00, lower=0 100%, contains 100%, point±1 76%

## Per-band bias of K_b (estimate minus the learner's true band share), by true share; m+r and meaning
zh m: true 0.0-0.2: bias -0.023 (n_b mean 5.7, N=2551); true 0.2-0.4: bias -0.015 (n_b mean 5.9, N=1607); true 0.4-0.6: bias -0.009 (n_b mean 5.5, N=4033); true 0.6-0.8: bias -0.002 (n_b mean 5.1, N=2817); true 0.8-1.0: bias +0.002 (n_b mean 4.0, N=2992)
zh mr: true 0.0-0.2: bias -0.004 (n_b mean 5.7, N=5766); true 0.2-0.4: bias -0.007 (n_b mean 5.4, N=2779); true 0.4-0.6: bias +0.005 (n_b mean 5.4, N=1955); true 0.6-0.8: bias +0.003 (n_b mean 4.9, N=1624); true 0.8-1.0: bias +0.003 (n_b mean 3.6, N=1876)
ja m: true 0.0-0.2: bias -0.022 (n_b mean 6.8, N=1816); true 0.2-0.4: bias -0.024 (n_b mean 6.7, N=2636); true 0.4-0.6: bias -0.002 (n_b mean 6.4, N=3548); true 0.6-0.8: bias +0.004 (n_b mean 5.6, N=2796); true 0.8-1.0: bias +0.007 (n_b mean 4.1, N=3204)
ja mr: true 0.0-0.2: bias -0.012 (n_b mean 6.8, N=2477); true 0.2-0.4: bias -0.007 (n_b mean 6.5, N=4546); true 0.4-0.6: bias +0.006 (n_b mean 5.9, N=2561); true 0.6-0.8: bias +0.015 (n_b mean 5.4, N=2084); true 0.8-1.0: bias +0.002 (n_b mean 3.8, N=2332)

## Probes
zh·en-L1: probes/test 2.60; pooled right 613, wrong 812, skip 1175 of 2600
zh·ja-L1: probes/test 2.08; pooled right 452, wrong 665, skip 963 of 2080
ja·en-L1: probes/test 2.35; pooled right 473, wrong 798, skip 1077 of 2348
ja·zh-L1: probes/test 1.72; pooled right 321, wrong 572, skip 826 of 1719
