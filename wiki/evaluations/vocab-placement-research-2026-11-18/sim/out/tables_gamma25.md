# Simulation tables — run `raw_gamma25.json`

Learners per population: 300. Config: `{"max_m": 70, "max_tot": 90, "designs": "D0,D1,D1S,D1L,D3,D3S,D3L", "pops": "zh:E:0.7,ja:E:0.7", "sig_eps": 1.2, "a_med": 1.6, "gamma_max": 2.5, "tau_lo": 2.5, "tau_hi": 7.0, "partial": 0, "seed": 11}`. Runtime 90.7 s.

All numbers are ESTIMATES from simulation. Errors are in % of the check pool (N words). Intervals are 90%. "e5..e95" is the 90% range of the error across learners.

## Populations (truth)

| population | skip | N | mean known by meaning (% of N) | mean known by meaning+reading (%) | meaning-only words (% of known) | true placement by meaning: share at 0 / at max | by meaning+reading: 0 / max |
|---|---|---|---|---|---|---|---|
| zh, English L1 | 0.7 | 3623 | 37.7 | 33.0 | 12.4 | 19% / 21% | 40% / 15% |
| ja, English L1 | 0.7 | 3175 | 40.4 | 38.4 | 5.0 | 43% / 21% | 54% / 17% |

## At a fixed budget (D0 70, meaning-only 40, with readings 60 items)

### zh, English L1, skip-if-unknown 0.7

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 6.2 | -0.0, 4.9, -9.6..10.3 | 90 / 9.8 | (reports meaning) 4.7 | 76 / — | 34 / 43 | 54 / 67 | 22% | 20.4% / 9.4% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.5 | 0.4, 4.9, -10.0..9.9 | 93 / 10.7 | (reports meaning) 5.1 | 84 / — | 29 / 36 | 48 / 60 | 15% | 22.2% / 9.5% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.5 | -0.3, 5.7, -12.3..11.2 | 90 / 12.1 | (reports meaning) 4.3 | 86 / — | 38 / 46 | 54 / 69 | 13% | 21.4% / 10.1% |
| D1L adaptive exam levels, meaning | 40 (0) | 4.0 / 3.5 | -2.4, 8.0, -18.6..14.7 | 89 / 16.1 | (reports meaning) 2.2 | 89 / — | 57 / 88 | 45 / 65 | 8% | 15.0% / 3.8% |
| D3 IRT, reading after correct meaning | 60 (18) | 5.7 / 5.2 | 0.7, 5.0, -9.7..10.6 | 91 / 10.6 | -0.5, 4.6, -11.9..8.3 | 93 / 10.1 | 29 / 34 | 43 / 52 | 1% | 4.0% / 2.7% |
| D3S adaptive bands, reading after correct meaning | 60 (17) | 5.7 / 5.2 | -0.7, 5.7, -13.5..11.0 | 88 / 11.9 | -0.4, 5.0, -10.6..10.4 | 91 / 10.6 | 32 / 42 | 50 / 62 | 4% | 3.6% / 2.3% |
| D3L adaptive exam levels, reading after correct meaning | 60 (23) | 5.7 / 5.0 | -1.2, 8.8, -17.8..17.3 | 89 / 17.5 | 0.2, 6.4, -12.6..15.5 | 95 / 15.8 | 57 / 87 | 57 / 80 | 2% | 2.2% / 1.3% |

### ja, English L1, skip-if-unknown 0.7

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 6.2 | -0.4, 5.1, -11.2..11.5 | 86 / 10.3 | (reports meaning) 1.6 | 86 / — | 55 / 66 | 63 / 75 | 10% | 11.8% / 7.8% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.5 | -2.9, 4.9, -11.8..5.7 | 91 / 10.5 | (reports meaning) -0.9 | 94 / — | 48 / 59 | 59 / 68 | 1% | 16.4% / 9.9% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.5 | -0.7, 6.7, -13.1..11.6 | 87 / 12.4 | (reports meaning) 1.3 | 88 / — | 55 / 67 | 66 / 76 | 6% | 14.1% / 9.8% |
| D1L adaptive exam levels, meaning | 40 (0) | 4.0 / 3.5 | -1.4, 7.7, -15.3..15.0 | 85 / 14.1 | (reports meaning) 0.6 | 87 / — | 72 / 92 | 65 / 87 | 6% | 12.3% / 6.4% |
| D3 IRT, reading after correct meaning | 60 (14) | 5.8 / 5.2 | -2.9, 5.2, -12.6..6.5 | 88 / 10.0 | -4.3, 5.6, -13.2..4.2 | 82 / 9.7 | 50 / 60 | 57 / 64 | 1% | 5.2% / 4.6% |
| D3S adaptive bands, reading after correct meaning | 60 (13) | 5.8 / 5.2 | -0.6, 5.4, -11.8..11.2 | 88 / 11.7 | -0.0, 5.2, -10.5..11.4 | 90 / 11.0 | 56 / 66 | 65 / 74 | 4% | 5.1% / 4.8% |
| D3L adaptive exam levels, reading after correct meaning | 60 (16) | 5.8 / 5.1 | -1.5, 7.2, -14.9..12.3 | 85 / 13.7 | -1.2, 6.4, -12.9..12.4 | 90 / 12.8 | 72 / 90 | 68 / 91 | 2% | 3.5% / 3.2% |

## Precision vs number of items (fixed-length snapshots)

Mean 90% half-width and MAE of the meaning count (and of the meaning+reading count for reading designs), % of N, averaged over all populations of the language; coverage in brackets.

### zh

| design | n=20 | n=30 | n=40 | n=50 | n=60 | n=70 | n=90 |
|---|---|---|---|---|---|---|---|
| D0 | m ±19.5 MAE 8.9 (92%) | m ±15.6 MAE 7.4 (91%) | m ±13.2 MAE 6.8 (90%) | m ±11.7 MAE 6.0 (86%) | m ±10.7 MAE 5.4 (88%) | m ±9.8 MAE 4.9 (90%) | — |
| D1 | m ±14.5 MAE 7.1 (91%) | m ±12.2 MAE 5.8 (92%) | m ±10.7 MAE 4.9 (93%) | m ±9.7 MAE 4.5 (91%) | m ±8.9 MAE 4.3 (90%) | m ±8.3 MAE 4.1 (91%) | — |
| D1S | m ±18.0 MAE 9.1 (91%) | m ±14.1 MAE 6.7 (90%) | m ±12.1 MAE 5.7 (90%) | m ±10.7 MAE 5.3 (89%) | m ±9.7 MAE 4.8 (89%) | m ±8.9 MAE 4.2 (90%) | — |
| D1L | m ±25.7 MAE 12.0 (92%) | m ±19.5 MAE 9.4 (93%) | m ±16.1 MAE 8.0 (89%) | m ±13.9 MAE 7.0 (89%) | m ±12.2 MAE 6.5 (88%) | m ±11.1 MAE 6.0 (85%) | — |
| D3 | m ±17.2 MAE 8.0 (93%); m+r ±16.0 MAE 7.4 (95%) | m ±14.5 MAE 6.9 (93%); m+r ±13.7 MAE 6.3 (95%) | m ±12.8 MAE 5.9 (91%); m+r ±12.1 MAE 5.6 (95%) | m ±11.5 MAE 5.3 (89%); m+r ±11.0 MAE 5.0 (94%) | m ±10.6 MAE 5.0 (91%); m+r ±10.1 MAE 4.6 (93%) | m ±9.9 MAE 4.6 (92%); m+r ±9.5 MAE 4.4 (95%) | m ±8.8 MAE 4.1 (93%); m+r ±8.5 MAE 4.0 (93%) |
| D3S | m ±23.8 MAE 10.6 (92%); m+r ±22.3 MAE 8.3 (97%) | m ±17.7 MAE 7.8 (91%); m+r ±16.2 MAE 6.5 (95%) | m ±14.9 MAE 7.1 (92%); m+r ±13.5 MAE 6.1 (93%) | m ±13.1 MAE 6.2 (90%); m+r ±11.8 MAE 5.4 (91%) | m ±11.9 MAE 5.7 (88%); m+r ±10.6 MAE 5.0 (91%) | m ±11.0 MAE 5.2 (90%); m+r ±9.7 MAE 4.6 (91%) | m ±9.6 MAE 4.7 (89%); m+r ±8.4 MAE 4.2 (88%) |
| D3L | m ±34.7 MAE 15.9 (96%); m+r ±32.9 MAE 12.0 (98%) | m ±26.5 MAE 13.1 (91%); m+r ±24.5 MAE 9.0 (97%) | m ±22.7 MAE 11.3 (92%); m+r ±20.7 MAE 8.0 (96%) | m ±19.8 MAE 9.9 (88%); m+r ±18.0 MAE 7.1 (95%) | m ±17.5 MAE 8.8 (89%); m+r ±15.8 MAE 6.4 (95%) | m ±15.9 MAE 8.1 (88%); m+r ±14.1 MAE 5.8 (95%) | m ±13.6 MAE 6.7 (87%); m+r ±11.9 MAE 4.8 (94%) |

### ja

| design | n=20 | n=30 | n=40 | n=50 | n=60 | n=70 | n=90 |
|---|---|---|---|---|---|---|---|
| D0 | m ±20.1 MAE 9.0 (92%) | m ±16.1 MAE 7.7 (90%) | m ±13.8 MAE 6.9 (86%) | m ±12.3 MAE 5.9 (88%) | m ±11.1 MAE 5.5 (88%) | m ±10.3 MAE 5.1 (86%) | — |
| D1 | m ±14.2 MAE 6.0 (93%) | m ±11.9 MAE 5.4 (92%) | m ±10.5 MAE 4.9 (91%) | m ±9.5 MAE 4.7 (85%) | m ±8.7 MAE 4.6 (85%) | m ±8.1 MAE 4.4 (84%) | — |
| D1S | m ±18.5 MAE 9.4 (91%) | m ±14.6 MAE 7.5 (87%) | m ±12.4 MAE 6.7 (87%) | m ±11.0 MAE 5.7 (87%) | m ±10.0 MAE 5.2 (89%) | m ±9.2 MAE 5.0 (87%) | — |
| D1L | m ±21.4 MAE 11.1 (88%) | m ±16.6 MAE 9.2 (85%) | m ±14.1 MAE 7.7 (85%) | m ±12.4 MAE 6.9 (82%) | m ±11.1 MAE 6.1 (83%) | m ±10.1 MAE 5.4 (83%) | — |
| D3 | m ±16.4 MAE 7.4 (95%); m+r ±15.4 MAE 7.8 (91%) | m ±13.8 MAE 6.2 (93%); m+r ±13.1 MAE 6.6 (89%) | m ±12.1 MAE 5.6 (92%); m+r ±11.6 MAE 6.1 (86%) | m ±10.9 MAE 5.3 (90%); m+r ±10.5 MAE 5.7 (85%) | m ±10.0 MAE 5.2 (88%); m+r ±9.7 MAE 5.6 (82%) | m ±9.3 MAE 5.0 (86%); m+r ±9.0 MAE 5.4 (82%) | m ±8.2 MAE 4.7 (85%); m+r ±8.1 MAE 4.9 (82%) |
| D3S | m ±23.1 MAE 10.8 (90%); m+r ±22.2 MAE 9.8 (92%) | m ±17.4 MAE 8.2 (90%); m+r ±16.6 MAE 7.4 (91%) | m ±14.7 MAE 7.0 (90%); m+r ±13.9 MAE 6.4 (90%) | m ±12.9 MAE 5.9 (89%); m+r ±12.2 MAE 5.6 (89%) | m ±11.7 MAE 5.4 (88%); m+r ±11.0 MAE 5.2 (90%) | m ±10.7 MAE 5.5 (87%); m+r ±10.0 MAE 5.1 (87%) | m ±9.4 MAE 4.9 (86%); m+r ±8.7 MAE 4.5 (86%) |
| D3L | m ±25.5 MAE 12.9 (88%); m+r ±24.5 MAE 11.4 (91%) | m ±21.1 MAE 10.8 (86%); m+r ±20.2 MAE 9.2 (89%) | m ±17.6 MAE 9.0 (86%); m+r ±16.6 MAE 7.9 (88%) | m ±15.3 MAE 8.1 (87%); m+r ±14.4 MAE 7.0 (90%) | m ±13.7 MAE 7.2 (85%); m+r ±12.8 MAE 6.4 (90%) | m ±12.5 MAE 6.3 (87%); m+r ±11.7 MAE 5.6 (88%) | m ±10.8 MAE 5.6 (86%); m+r ±10.0 MAE 5.0 (88%) |

## Stopping rules (applied to the snapshots; stop at the first checkpoint where every reported 90% half-width <= h x N, after a minimum, else at the cap)

### h = 0.1, min 20, cap 40 (meaning-only) / 60 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.7 | D1 | 38 (25..40) | 16% | 3.4 / 3.6 | 5.0 / 92% | — | 60 |
| zh, English L1 s=0.7 | D1S | 40 (40..40) | 2% | 3.5 / 3.7 | 5.8 / 90% | — | 69 |
| zh, English L1 s=0.7 | D1L | 40 (40..40) | 2% | 3.5 / 3.6 | 8.0 / 89% | — | 65 |
| zh, English L1 s=0.7 | D3 | 57 (35..61) | 16% | 4.9 / 5.5 | 5.0 / 92% | 4.7 / 94% | 52 |
| zh, English L1 s=0.7 | D3S | 59 (45..61) | 10% | 5.1 / 5.6 | 5.8 / 88% | 5.1 / 91% | 62 |
| zh, English L1 s=0.7 | D3L | 60 (60..61) | 4% | 4.9 / 5.5 | 8.8 / 89% | 6.4 / 95% | 80 |
| ja, English L1 s=0.7 | D1 | 38 (25..40) | 21% | 3.3 / 3.6 | 4.9 / 92% | — | 68 |
| ja, English L1 s=0.7 | D1S | 40 (40..40) | 3% | 3.5 / 3.7 | 6.7 / 87% | — | 76 |
| ja, English L1 s=0.7 | D1L | 40 (40..40) | 3% | 3.5 / 3.7 | 7.8 / 85% | — | 87 |
| ja, English L1 s=0.7 | D3 | 55 (30..61) | 25% | 4.7 / 5.4 | 5.2 / 89% | 5.6 / 85% | 64 |
| ja, English L1 s=0.7 | D3S | 59 (50..61) | 11% | 5.0 / 5.5 | 5.5 / 89% | 5.2 / 89% | 74 |
| ja, English L1 s=0.7 | D3L | 59 (45..61) | 10% | 4.9 / 5.5 | 7.4 / 85% | 6.5 / 89% | 91 |

### h = 0.12, min 20, cap 40 (meaning-only) / 60 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.7 | D1 | 34 (20..40) | 60% | 3.0 / 3.6 | 5.2 / 91% | — | 60 |
| zh, English L1 s=0.7 | D1S | 38 (30..40) | 25% | 3.4 / 3.6 | 6.0 / 89% | — | 69 |
| zh, English L1 s=0.7 | D1L | 39 (35..40) | 6% | 3.4 / 3.6 | 8.0 / 89% | — | 65 |
| zh, English L1 s=0.7 | D3 | 51 (25..61) | 44% | 4.3 / 5.3 | 5.3 / 91% | 4.9 / 93% | 52 |
| zh, English L1 s=0.7 | D3S | 54 (35..61) | 33% | 4.7 / 5.4 | 6.1 / 88% | 5.2 / 91% | 62 |
| zh, English L1 s=0.7 | D3L | 59 (41..61) | 9% | 4.8 / 5.4 | 8.9 / 90% | 6.5 / 95% | 80 |
| ja, English L1 s=0.7 | D1 | 33 (20..40) | 66% | 2.9 / 3.6 | 5.0 / 91% | — | 70 |
| ja, English L1 s=0.7 | D1S | 39 (30..40) | 15% | 3.4 / 3.6 | 6.8 / 88% | — | 76 |
| ja, English L1 s=0.7 | D1L | 39 (35..40) | 16% | 3.4 / 3.6 | 7.9 / 85% | — | 87 |
| ja, English L1 s=0.7 | D3 | 46 (20..61) | 67% | 4.0 / 5.2 | 5.4 / 90% | 5.7 / 84% | 64 |
| ja, English L1 s=0.7 | D3S | 55 (35..61) | 29% | 4.7 / 5.4 | 5.8 / 90% | 5.5 / 89% | 74 |
| ja, English L1 s=0.7 | D3L | 56 (35..61) | 22% | 4.7 / 5.4 | 7.7 / 86% | 6.8 / 90% | 91 |

### h = 0.08, min 20, cap 60 (meaning-only) / 90 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.7 | D1 | 58 (45..60) | 9% | 5.1 / 5.5 | 4.3 / 90% | — | 59 |
| zh, English L1 s=0.7 | D1S | 60 (60..60) | 2% | 5.3 / 5.5 | 4.8 / 89% | — | 69 |
| zh, English L1 s=0.7 | D1L | 60 (60..60) | 3% | 5.2 / 5.4 | 6.5 / 88% | — | 64 |
| zh, English L1 s=0.7 | D3 | 86 (60..91) | 16% | 7.4 / 8.2 | 4.2 / 92% | 4.0 / 93% | 53 |
| zh, English L1 s=0.7 | D3S | 88 (70..91) | 12% | 7.6 / 8.3 | 4.8 / 90% | 4.2 / 90% | 62 |
| zh, English L1 s=0.7 | D3L | 89 (81..91) | 5% | 7.4 / 8.1 | 6.7 / 87% | 4.9 / 95% | 83 |
| ja, English L1 s=0.7 | D1 | 57 (35..60) | 14% | 5.1 / 5.5 | 4.6 / 86% | — | 69 |
| ja, English L1 s=0.7 | D1S | 60 (60..60) | 2% | 5.3 / 5.6 | 5.2 / 89% | — | 76 |
| ja, English L1 s=0.7 | D1L | 60 (60..60) | 2% | 5.2 / 5.5 | 6.2 / 82% | — | 89 |
| ja, English L1 s=0.7 | D3 | 84 (50..91) | 22% | 7.2 / 8.1 | 4.7 / 88% | 5.0 / 85% | 66 |
| ja, English L1 s=0.7 | D3S | 88 (70..91) | 13% | 7.5 / 8.2 | 4.9 / 86% | 4.5 / 86% | 73 |
| ja, English L1 s=0.7 | D3L | 88 (70..91) | 12% | 7.4 / 8.2 | 5.7 / 85% | 5.1 / 88% | 93 |

### h = 0.1, min 20, cap 60 (meaning-only) / 90 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.7 | D1 | 50 (25..60) | 49% | 4.4 / 5.4 | 4.5 / 92% | — | 60 |
| zh, English L1 s=0.7 | D1S | 56 (40..60) | 26% | 5.0 / 5.4 | 5.0 / 88% | — | 70 |
| zh, English L1 s=0.7 | D1L | 59 (45..60) | 7% | 5.1 / 5.4 | 6.5 / 88% | — | 64 |
| zh, English L1 s=0.7 | D3 | 75 (35..91) | 57% | 6.4 / 7.8 | 4.6 / 92% | 4.3 / 93% | 53 |
| zh, English L1 s=0.7 | D3S | 80 (45..91) | 42% | 6.8 / 8.0 | 5.0 / 89% | 4.3 / 91% | 62 |
| zh, English L1 s=0.7 | D3L | 87 (60..91) | 11% | 7.2 / 8.0 | 6.8 / 87% | 4.9 / 95% | 83 |
| ja, English L1 s=0.7 | D1 | 49 (25..60) | 55% | 4.3 / 5.4 | 4.7 / 89% | — | 68 |
| ja, English L1 s=0.7 | D1S | 57 (40..60) | 20% | 5.0 / 5.5 | 5.5 / 89% | — | 76 |
| ja, English L1 s=0.7 | D1L | 57 (40..60) | 15% | 5.0 / 5.4 | 6.4 / 83% | — | 89 |
| ja, English L1 s=0.7 | D3 | 68 (30..91) | 80% | 5.8 / 7.7 | 4.9 / 89% | 5.3 / 85% | 65 |
| ja, English L1 s=0.7 | D3S | 80 (50..91) | 41% | 6.8 / 7.9 | 5.1 / 86% | 4.7 / 86% | 73 |
| ja, English L1 s=0.7 | D3L | 81 (45..91) | 30% | 6.8 / 7.8 | 6.0 / 86% | 5.5 / 87% | 93 |

## By ability (budget snapshot), all populations of a language pooled

Ability groups by the learner's study frontier tau (Zipf at 50% known): beginner tau >= 5.5, intermediate 4.0-5.5, advanced < 4.0.

| lang | design | group | n learners | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|
| zh | D0 | beginner | 102 | 4.6 / 91% | — | 83 |
| zh | D0 | intermediate | 99 | 4.7 / 90% | — | 56 |
| zh | D0 | advanced | 99 | 5.4 / 89% | — | 61 |
| zh | D1 | beginner | 102 | 4.7 / 93% | — | 83 |
| zh | D1 | intermediate | 99 | 4.4 / 97% | — | 51 |
| zh | D1 | advanced | 99 | 5.8 / 90% | — | 45 |
| zh | D1S | beginner | 102 | 5.6 / 89% | — | 83 |
| zh | D1S | intermediate | 99 | 6.0 / 88% | — | 59 |
| zh | D1S | advanced | 99 | 5.6 / 93% | — | 66 |
| zh | D3 | beginner | 102 | 5.5 / 85% | 4.0 / 95% | 83 |
| zh | D3 | intermediate | 99 | 4.2 / 96% | 4.0 / 98% | 51 |
| zh | D3 | advanced | 99 | 5.2 / 92% | 6.0 / 87% | 21 |
| zh | D3S | beginner | 102 | 4.7 / 91% | 3.1 / 93% | 83 |
| zh | D3S | intermediate | 99 | 6.1 / 81% | 5.4 / 89% | 52 |
| zh | D3S | advanced | 99 | 6.4 / 91% | 6.6 / 91% | 49 |
| zh | D3L | beginner | 102 | 6.9 / 93% | 3.3 / 99% | 92 |
| zh | D3L | intermediate | 99 | 8.6 / 90% | 6.5 / 96% | 65 |
| zh | D3L | advanced | 99 | 10.9 / 84% | 9.6 / 90% | 82 |
| ja | D0 | beginner | 96 | 4.2 / 89% | — | 100 |
| ja | D0 | intermediate | 104 | 6.1 / 82% | — | 76 |
| ja | D0 | advanced | 100 | 5.1 / 89% | — | 50 |
| ja | D1 | beginner | 96 | 4.1 / 91% | — | 100 |
| ja | D1 | intermediate | 104 | 4.8 / 93% | — | 76 |
| ja | D1 | advanced | 100 | 5.8 / 88% | — | 30 |
| ja | D1S | beginner | 96 | 6.2 / 83% | — | 100 |
| ja | D1S | intermediate | 104 | 6.9 / 88% | — | 75 |
| ja | D1S | advanced | 100 | 6.9 / 89% | — | 53 |
| ja | D3 | beginner | 96 | 4.3 / 91% | 3.9 / 81% | 100 |
| ja | D3 | intermediate | 104 | 5.4 / 89% | 5.7 / 86% | 76 |
| ja | D3 | advanced | 100 | 5.9 / 84% | 7.1 / 79% | 18 |
| ja | D3S | beginner | 96 | 5.0 / 84% | 4.1 / 91% | 100 |
| ja | D3S | intermediate | 104 | 6.2 / 87% | 6.1 / 87% | 76 |
| ja | D3S | advanced | 100 | 5.0 / 94% | 5.3 / 92% | 46 |
| ja | D3L | beginner | 96 | 5.8 / 83% | 4.6 / 90% | 99 |
| ja | D3L | intermediate | 104 | 8.1 / 86% | 6.6 / 92% | 88 |
| ja | D3L | advanced | 100 | 7.7 / 87% | 7.9 / 88% | 87 |
