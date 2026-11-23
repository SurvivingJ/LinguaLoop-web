# Simulation tables — run `raw_eps18.json`

Learners per population: 300. Config: `{"max_m": 70, "max_tot": 90, "designs": "D0,D1,D1S,D3,D3S", "pops": "zh:E:0.7,zh:J:0.7,ja:Z:0.7", "sig_eps": 1.8, "a_med": 1.6, "gamma_max": 1.0, "tau_lo": 2.5, "tau_hi": 7.0, "partial": 0, "seed": 11}`. Runtime 134.0 s.

All numbers are ESTIMATES from simulation. Errors are in % of the check pool (N words). Intervals are 90%. "e5..e95" is the 90% range of the error across learners.

## Populations (truth)

| population | skip | N | mean known by meaning (% of N) | mean known by meaning+reading (%) | meaning-only words (% of known) | true placement by meaning: share at 0 / at max | by meaning+reading: 0 / max |
|---|---|---|---|---|---|---|---|
| zh, English L1 | 0.7 | 3623 | 38.7 | 33.8 | 12.6 | 47% / 17% | 60% / 12% |
| zh, Japanese L1 (cognates) | 0.7 | 3623 | 63.4 | 34.3 | 45.8 | 33% / 30% | 62% / 9% |
| ja, Chinese L1 (cognates) | 0.7 | 3175 | 61.3 | 45.9 | 25.3 | 55% / 27% | 69% / 12% |

## At a fixed budget (D0 70, meaning-only 40, with readings 60 items)

### zh, English L1, skip-if-unknown 0.7

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 6.2 | 0.4, 4.9, -9.5..10.6 | 88 / 9.9 | (reports meaning) 5.3 | 80 / — | 61 / 74 | 70 / 82 | 20% | 20.4% / 9.3% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.5 | 0.9, 5.0, -8.9..11.1 | 93 / 10.6 | (reports meaning) 5.8 | 80 / — | 61 / 68 | 70 / 79 | 20% | 23.0% / 9.4% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.5 | -0.0, 6.3, -12.6..12.2 | 90 / 12.2 | (reports meaning) 4.8 | 79 / — | 62 / 73 | 69 / 80 | 19% | 21.2% / 9.8% |
| D3 IRT, reading after correct meaning | 60 (18) | 5.7 / 5.2 | 1.1, 4.8, -9.7..10.5 | 92 / 10.6 | -0.0, 4.4, -10.5..8.0 | 97 / 10.2 | 60 / 67 | 66 / 72 | 1% | 4.0% / 2.6% |
| D3S adaptive bands, reading after correct meaning | 60 (17) | 5.7 / 5.2 | -0.7, 6.0, -12.8..11.4 | 89 / 12.0 | 0.1, 5.1, -9.8..12.0 | 92 / 10.8 | 61 / 70 | 70 / 78 | 4% | 4.1% / 2.6% |

### zh, Japanese L1 (cognates), skip-if-unknown 0.7

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 6.1 | 0.1, 5.3, -10.5..11.3 | 89 / 10.6 | (reports meaning) 29.1 | 4 / — | 58 / 66 | 62 / 71 | 96% | 45.6% / 3.7% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.5 | -1.5, 5.5, -12.8..9.2 | 89 / 11.3 | (reports meaning) 27.5 | 7 / — | 54 / 63 | 67 / 75 | 93% | 52.3% / 4.5% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.5 | 0.5, 6.9, -14.6..15.1 | 85 / 13.1 | (reports meaning) 29.6 | 9 / — | 53 / 66 | 57 / 69 | 91% | 48.5% / 4.2% |
| D3 IRT, reading after correct meaning | 60 (23) | 5.6 / 5.4 | -2.6, 6.3, -14.4..10.0 | 87 / 11.8 | 0.1, 5.1, -11.0..11.8 | 91 / 11.1 | 53 / 62 | 64 / 68 | 5% | 7.4% / 1.4% |
| D3S adaptive bands, reading after correct meaning | 60 (24) | 5.6 / 5.5 | 0.1, 6.7, -12.4..12.6 | 92 / 13.9 | -0.4, 5.9, -11.8..12.1 | 90 / 12.3 | 54 / 63 | 68 / 77 | 4% | 7.8% / 1.4% |

### ja, Chinese L1 (cognates), skip-if-unknown 0.7

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 6.1 | -0.2, 5.4, -11.7..10.6 | 88 / 10.6 | (reports meaning) 15.3 | 32 / — | 75 / 82 | 74 / 82 | 68% | 25.9% / 3.9% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.5 | 0.8, 5.0, -9.2..10.6 | 95 / 11.3 | (reports meaning) 16.3 | 30 / — | 72 / 77 | 74 / 84 | 70% | 30.7% / 4.1% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.5 | -0.3, 6.3, -13.8..11.7 | 91 / 13.1 | (reports meaning) 15.2 | 41 / — | 69 / 75 | 66 / 76 | 59% | 27.4% / 4.3% |
| D3 IRT, reading after correct meaning | 60 (19) | 5.7 / 5.3 | 0.9, 5.0, -9.1..11.6 | 91 / 11.1 | 1.0, 5.0, -9.1..13.1 | 90 / 10.8 | 74 / 81 | 73 / 79 | 7% | 5.6% / 2.8% |
| D3S adaptive bands, reading after correct meaning | 60 (19) | 5.7 / 5.3 | 0.7, 6.0, -12.8..13.1 | 90 / 12.9 | 0.8, 6.5, -12.8..13.9 | 87 / 12.5 | 74 / 79 | 76 / 85 | 6% | 5.4% / 2.9% |

## Precision vs number of items (fixed-length snapshots)

Mean 90% half-width and MAE of the meaning count (and of the meaning+reading count for reading designs), % of N, averaged over all populations of the language; coverage in brackets.

### zh

| design | n=20 | n=30 | n=40 | n=50 | n=60 | n=70 | n=90 |
|---|---|---|---|---|---|---|---|
| D0 | m ±20.3 MAE 9.5 (91%) | m ±16.2 MAE 7.6 (91%) | m ±13.8 MAE 6.5 (91%) | m ±12.3 MAE 5.9 (91%) | m ±11.2 MAE 5.4 (90%) | m ±10.3 MAE 5.1 (89%) | — |
| D1 | m ±14.7 MAE 7.3 (92%) | m ±12.4 MAE 6.2 (90%) | m ±10.9 MAE 5.2 (91%) | m ±9.9 MAE 4.7 (91%) | m ±9.2 MAE 4.5 (92%) | m ±8.5 MAE 4.2 (92%) | — |
| D1S | m ±18.9 MAE 9.3 (89%) | m ±14.8 MAE 7.5 (88%) | m ±12.7 MAE 6.6 (88%) | m ±11.2 MAE 5.7 (89%) | m ±10.2 MAE 5.3 (88%) | m ±9.4 MAE 4.9 (87%) | — |
| D3 | m ±17.8 MAE 8.2 (92%); m+r ±16.7 MAE 7.2 (94%) | m ±15.2 MAE 7.3 (92%); m+r ±14.2 MAE 6.3 (94%) | m ±13.4 MAE 6.6 (91%); m+r ±12.6 MAE 5.3 (94%) | m ±12.1 MAE 6.1 (90%); m+r ±11.5 MAE 5.0 (94%) | m ±11.2 MAE 5.5 (90%); m+r ±10.6 MAE 4.7 (94%) | m ±10.4 MAE 5.1 (90%); m+r ±9.9 MAE 4.4 (94%) | m ±9.3 MAE 4.4 (91%); m+r ±8.9 MAE 3.9 (94%) |
| D3S | m ±26.1 MAE 11.5 (91%); m+r ±24.2 MAE 10.3 (94%) | m ±19.4 MAE 8.7 (92%); m+r ±17.6 MAE 7.4 (94%) | m ±16.3 MAE 7.6 (92%); m+r ±14.7 MAE 6.5 (92%) | m ±14.3 MAE 7.1 (90%); m+r ±12.8 MAE 6.1 (91%) | m ±13.0 MAE 6.3 (91%); m+r ±11.6 MAE 5.5 (91%) | m ±11.9 MAE 5.8 (90%); m+r ±10.6 MAE 5.1 (91%) | m ±10.4 MAE 5.2 (88%); m+r ±9.2 MAE 4.4 (90%) |

### ja

| design | n=20 | n=30 | n=40 | n=50 | n=60 | n=70 | n=90 |
|---|---|---|---|---|---|---|---|
| D0 | m ±20.9 MAE 10.3 (87%) | m ±16.8 MAE 8.0 (91%) | m ±14.4 MAE 7.1 (90%) | m ±12.8 MAE 6.5 (89%) | m ±11.5 MAE 6.1 (89%) | m ±10.6 MAE 5.4 (88%) | — |
| D1 | m ±15.0 MAE 6.5 (92%) | m ±12.7 MAE 5.5 (93%) | m ±11.3 MAE 5.0 (95%) | m ±10.2 MAE 4.5 (94%) | m ±9.4 MAE 4.4 (92%) | m ±8.8 MAE 4.1 (90%) | — |
| D1S | m ±19.6 MAE 9.1 (90%) | m ±15.4 MAE 7.4 (90%) | m ±13.1 MAE 6.3 (91%) | m ±11.6 MAE 5.8 (89%) | m ±10.5 MAE 5.6 (86%) | m ±9.6 MAE 5.0 (88%) | — |
| D3 | m ±17.5 MAE 7.0 (95%); m+r ±16.5 MAE 7.2 (94%) | m ±14.9 MAE 6.3 (92%); m+r ±14.2 MAE 6.3 (95%) | m ±13.2 MAE 5.9 (94%); m+r ±12.8 MAE 5.6 (94%) | m ±12.0 MAE 5.2 (92%); m+r ±11.7 MAE 5.2 (92%) | m ±11.1 MAE 5.0 (91%); m+r ±10.8 MAE 5.0 (90%) | m ±10.4 MAE 4.7 (91%); m+r ±10.1 MAE 4.6 (91%) | m ±9.3 MAE 4.3 (92%); m+r ±9.1 MAE 4.3 (90%) |
| D3S | m ±26.4 MAE 12.2 (92%); m+r ±25.2 MAE 12.3 (91%) | m ±19.5 MAE 9.1 (91%); m+r ±18.6 MAE 9.4 (87%) | m ±16.3 MAE 7.8 (89%); m+r ±15.7 MAE 8.4 (87%) | m ±14.3 MAE 6.5 (91%); m+r ±13.8 MAE 7.3 (87%) | m ±12.9 MAE 6.0 (90%); m+r ±12.5 MAE 6.5 (87%) | m ±11.8 MAE 5.4 (91%); m+r ±11.5 MAE 5.8 (88%) | m ±10.3 MAE 5.0 (90%); m+r ±10.0 MAE 5.0 (87%) |

## Stopping rules (applied to the snapshots; stop at the first checkpoint where every reported 90% half-width <= h x N, after a minimum, else at the cap)

### h = 0.1, min 20, cap 40 (meaning-only) / 60 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.7 | D1 | 38 (25..40) | 21% | 3.3 / 3.6 | 5.1 / 93% | — | 79 |
| zh, English L1 s=0.7 | D1S | 40 (40..40) | 3% | 3.5 / 3.7 | 6.3 / 90% | — | 80 |
| zh, English L1 s=0.7 | D3 | 56 (31..61) | 17% | 4.8 / 5.5 | 4.9 / 92% | 4.4 / 96% | 72 |
| zh, English L1 s=0.7 | D3S | 59 (45..61) | 12% | 5.0 / 5.5 | 6.1 / 88% | 5.2 / 92% | 78 |
| zh, Japanese L1 (cognates) s=0.7 | D1 | 39 (30..40) | 13% | 3.4 / 3.6 | 5.6 / 90% | — | 75 |
| zh, Japanese L1 (cognates) s=0.7 | D1S | 40 (40..40) | 0% | 3.5 / 3.6 | 6.9 / 85% | — | 69 |
| zh, Japanese L1 (cognates) s=0.7 | D3 | 60 (60..61) | 0% | 5.4 / 6.0 | 6.3 / 87% | 5.1 / 91% | 68 |
| zh, Japanese L1 (cognates) s=0.7 | D3S | 60 (60..61) | 0% | 5.5 / 6.1 | 6.7 / 92% | 5.9 / 90% | 77 |
| ja, Chinese L1 (cognates) s=0.7 | D1 | 39 (30..40) | 13% | 3.4 / 3.6 | 5.1 / 94% | — | 84 |
| ja, Chinese L1 (cognates) s=0.7 | D1S | 40 (40..40) | 0% | 3.5 / 3.6 | 6.3 / 91% | — | 76 |
| ja, Chinese L1 (cognates) s=0.7 | D3 | 60 (60..61) | 2% | 5.3 / 5.8 | 5.0 / 91% | 5.0 / 90% | 79 |
| ja, Chinese L1 (cognates) s=0.7 | D3S | 60 (60..61) | 0% | 5.3 / 5.7 | 6.0 / 90% | 6.5 / 87% | 85 |

### h = 0.12, min 20, cap 40 (meaning-only) / 60 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.7 | D1 | 33 (20..40) | 64% | 2.9 / 3.6 | 5.4 / 93% | — | 79 |
| zh, English L1 s=0.7 | D1S | 39 (30..40) | 20% | 3.4 / 3.6 | 6.4 / 91% | — | 80 |
| zh, English L1 s=0.7 | D3 | 50 (20..61) | 45% | 4.3 / 5.4 | 5.1 / 93% | 4.5 / 96% | 72 |
| zh, English L1 s=0.7 | D3S | 54 (35..61) | 31% | 4.7 / 5.4 | 6.4 / 90% | 5.3 / 92% | 78 |
| zh, Japanese L1 (cognates) s=0.7 | D1 | 35 (20..40) | 46% | 3.0 / 3.6 | 5.8 / 91% | — | 77 |
| zh, Japanese L1 (cognates) s=0.7 | D1S | 40 (40..40) | 2% | 3.5 / 3.6 | 6.9 / 85% | — | 69 |
| zh, Japanese L1 (cognates) s=0.7 | D3 | 60 (60..61) | 1% | 5.4 / 6.0 | 6.3 / 87% | 5.0 / 91% | 68 |
| zh, Japanese L1 (cognates) s=0.7 | D3S | 60 (60..61) | 0% | 5.5 / 6.1 | 6.8 / 92% | 5.9 / 90% | 77 |
| ja, Chinese L1 (cognates) s=0.7 | D1 | 35 (20..40) | 47% | 3.0 / 3.6 | 5.2 / 94% | — | 80 |
| ja, Chinese L1 (cognates) s=0.7 | D1S | 40 (40..40) | 1% | 3.5 / 3.6 | 6.3 / 91% | — | 76 |
| ja, Chinese L1 (cognates) s=0.7 | D3 | 57 (45..61) | 27% | 5.0 / 5.8 | 5.1 / 91% | 5.1 / 91% | 78 |
| ja, Chinese L1 (cognates) s=0.7 | D3S | 60 (60..61) | 0% | 5.3 / 5.7 | 6.0 / 90% | 6.5 / 87% | 85 |

### h = 0.08, min 20, cap 60 (meaning-only) / 90 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.7 | D1 | 58 (40..60) | 13% | 5.1 / 5.5 | 4.2 / 94% | — | 81 |
| zh, English L1 s=0.7 | D1S | 60 (60..60) | 2% | 5.3 / 5.5 | 5.2 / 86% | — | 82 |
| zh, English L1 s=0.7 | D3 | 85 (51..91) | 17% | 7.3 / 8.2 | 3.9 / 93% | 3.4 / 97% | 73 |
| zh, English L1 s=0.7 | D3S | 88 (70..91) | 11% | 7.6 / 8.3 | 5.0 / 86% | 4.1 / 92% | 78 |
| zh, Japanese L1 (cognates) s=0.7 | D1 | 58 (45..60) | 9% | 5.1 / 5.4 | 4.8 / 90% | — | 75 |
| zh, Japanese L1 (cognates) s=0.7 | D1S | 60 (60..60) | 0% | 5.2 / 5.4 | 5.4 / 90% | — | 71 |
| zh, Japanese L1 (cognates) s=0.7 | D3 | 90 (90..91) | 0% | 8.2 / 8.9 | 5.0 / 89% | 4.4 / 92% | 69 |
| zh, Japanese L1 (cognates) s=0.7 | D3S | 90 (90..91) | 0% | 8.2 / 9.0 | 5.6 / 91% | 4.7 / 90% | 76 |
| ja, Chinese L1 (cognates) s=0.7 | D1 | 58 (45..60) | 8% | 5.1 / 5.4 | 4.5 / 91% | — | 84 |
| ja, Chinese L1 (cognates) s=0.7 | D1S | 60 (60..60) | 0% | 5.2 / 5.4 | 5.6 / 86% | — | 79 |
| ja, Chinese L1 (cognates) s=0.7 | D3 | 90 (90..91) | 1% | 8.0 / 8.7 | 4.3 / 92% | 4.3 / 90% | 79 |
| ja, Chinese L1 (cognates) s=0.7 | D3S | 90 (90..91) | 0% | 7.9 / 8.5 | 5.0 / 90% | 5.0 / 87% | 87 |

### h = 0.1, min 20, cap 60 (meaning-only) / 90 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.7 | D1 | 48 (25..60) | 55% | 4.3 / 5.4 | 4.6 / 94% | — | 80 |
| zh, English L1 s=0.7 | D1S | 56 (40..60) | 22% | 5.0 / 5.4 | 5.5 / 88% | — | 82 |
| zh, English L1 s=0.7 | D3 | 74 (31..91) | 56% | 6.4 / 7.9 | 4.3 / 93% | 3.7 / 97% | 73 |
| zh, English L1 s=0.7 | D3S | 80 (45..91) | 37% | 6.8 / 8.0 | 5.2 / 86% | 4.2 / 92% | 78 |
| zh, Japanese L1 (cognates) s=0.7 | D1 | 52 (30..60) | 42% | 4.5 / 5.4 | 5.1 / 90% | — | 73 |
| zh, Japanese L1 (cognates) s=0.7 | D1S | 59 (50..60) | 6% | 5.2 / 5.4 | 5.4 / 90% | — | 71 |
| zh, Japanese L1 (cognates) s=0.7 | D3 | 90 (81..91) | 5% | 8.1 / 8.9 | 5.0 / 89% | 4.4 / 92% | 69 |
| zh, Japanese L1 (cognates) s=0.7 | D3S | 90 (90..91) | 0% | 8.2 / 9.0 | 5.5 / 91% | 4.7 / 90% | 76 |
| ja, Chinese L1 (cognates) s=0.7 | D1 | 52 (30..60) | 40% | 4.5 / 5.4 | 4.6 / 92% | — | 84 |
| ja, Chinese L1 (cognates) s=0.7 | D1S | 60 (60..60) | 4% | 5.2 / 5.4 | 5.7 / 86% | — | 79 |
| ja, Chinese L1 (cognates) s=0.7 | D3 | 85 (70..91) | 34% | 7.5 / 8.6 | 4.5 / 91% | 4.4 / 92% | 80 |
| ja, Chinese L1 (cognates) s=0.7 | D3S | 90 (90..91) | 4% | 7.9 / 8.5 | 5.0 / 90% | 5.0 / 86% | 87 |

## By ability (budget snapshot), all populations of a language pooled

Ability groups by the learner's study frontier tau (Zipf at 50% known): beginner tau >= 5.5, intermediate 4.0-5.5, advanced < 4.0.

| lang | design | group | n learners | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|
| zh | D0 | beginner | 213 | 5.0 / 89% | — | 100 |
| zh | D0 | intermediate | 204 | 5.3 / 87% | — | 64 |
| zh | D0 | advanced | 183 | 4.9 / 91% | — | 63 |
| zh | D1 | beginner | 213 | 5.2 / 92% | — | 99 |
| zh | D1 | intermediate | 204 | 5.3 / 91% | — | 74 |
| zh | D1 | advanced | 183 | 5.1 / 90% | — | 56 |
| zh | D1S | beginner | 213 | 6.7 / 85% | — | 97 |
| zh | D1S | intermediate | 204 | 7.2 / 86% | — | 63 |
| zh | D1S | advanced | 183 | 5.7 / 93% | — | 62 |
| zh | D3 | beginner | 213 | 6.1 / 89% | 3.8 / 95% | 100 |
| zh | D3 | intermediate | 204 | 4.9 / 91% | 4.6 / 94% | 78 |
| zh | D3 | advanced | 183 | 5.5 / 89% | 5.9 / 92% | 27 |
| zh | D3S | beginner | 213 | 6.0 / 89% | 4.0 / 93% | 100 |
| zh | D3S | intermediate | 204 | 7.1 / 88% | 6.3 / 88% | 78 |
| zh | D3S | advanced | 183 | 6.0 / 95% | 6.4 / 93% | 50 |
| ja | D0 | beginner | 106 | 6.7 / 83% | — | 100 |
| ja | D0 | intermediate | 92 | 5.5 / 88% | — | 88 |
| ja | D0 | advanced | 102 | 4.0 / 92% | — | 58 |
| ja | D1 | beginner | 106 | 6.3 / 94% | — | 100 |
| ja | D1 | intermediate | 92 | 5.1 / 95% | — | 86 |
| ja | D1 | advanced | 102 | 3.6 / 96% | — | 66 |
| ja | D1S | beginner | 106 | 6.7 / 87% | — | 95 |
| ja | D1S | intermediate | 92 | 6.2 / 92% | — | 75 |
| ja | D1S | advanced | 102 | 6.2 / 93% | — | 58 |
| ja | D3 | beginner | 106 | 5.5 / 90% | 5.2 / 87% | 100 |
| ja | D3 | intermediate | 92 | 5.9 / 87% | 5.3 / 89% | 95 |
| ja | D3 | advanced | 102 | 3.6 / 95% | 4.6 / 93% | 42 |
| ja | D3S | beginner | 106 | 6.1 / 89% | 6.0 / 85% | 100 |
| ja | D3S | intermediate | 92 | 6.7 / 87% | 7.3 / 88% | 93 |
| ja | D3S | advanced | 102 | 5.1 / 95% | 6.4 / 89% | 63 |
