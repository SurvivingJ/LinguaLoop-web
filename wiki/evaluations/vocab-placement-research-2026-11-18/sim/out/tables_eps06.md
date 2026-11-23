# Simulation tables — run `raw_eps06.json`

Learners per population: 300. Config: `{"max_m": 70, "max_tot": 90, "designs": "D0,D1,D1S,D3,D3S", "pops": "zh:E:0.7,zh:J:0.7,ja:Z:0.7", "sig_eps": 0.6, "a_med": 1.6, "gamma_max": 1.0, "tau_lo": 2.5, "tau_hi": 7.0, "partial": 0, "seed": 11}`. Runtime 130.5 s.

All numbers are ESTIMATES from simulation. Errors are in % of the check pool (N words). Intervals are 90%. "e5..e95" is the 90% range of the error across learners.

## Populations (truth)

| population | skip | N | mean known by meaning (% of N) | mean known by meaning+reading (%) | meaning-only words (% of known) | true placement by meaning: share at 0 / at max | by meaning+reading: 0 / max |
|---|---|---|---|---|---|---|---|
| zh, English L1 | 0.7 | 3623 | 37.3 | 33.0 | 11.6 | 40% / 25% | 53% / 18% |
| zh, Japanese L1 (cognates) | 0.7 | 3623 | 62.5 | 33.4 | 46.6 | 31% / 33% | 58% / 15% |
| ja, Chinese L1 (cognates) | 0.7 | 3175 | 60.5 | 44.8 | 25.9 | 52% / 30% | 64% / 17% |

## At a fixed budget (D0 70, meaning-only 40, with readings 60 items)

### zh, English L1, skip-if-unknown 0.7

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 6.2 | -0.2, 4.7, -9.8..9.7 | 88 / 9.6 | (reports meaning) 4.1 | 80 / — | 62 / 74 | 70 / 84 | 19% | 19.6% / 9.7% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.5 | 0.9, 4.5, -8.7..10.4 | 94 / 10.1 | (reports meaning) 5.3 | 80 / — | 57 / 64 | 66 / 75 | 20% | 23.2% / 9.2% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.5 | -0.5, 5.4, -11.7..10.9 | 92 / 11.7 | (reports meaning) 3.8 | 86 / — | 63 / 76 | 71 / 84 | 13% | 21.1% / 10.0% |
| D3 IRT, reading after correct meaning | 60 (18) | 5.7 / 5.2 | 1.4, 4.7, -8.9..9.8 | 93 / 10.1 | -0.1, 4.3, -10.1..7.8 | 96 / 9.7 | 57 / 64 | 59 / 68 | 1% | 4.5% / 3.1% |
| D3S adaptive bands, reading after correct meaning | 60 (17) | 5.7 / 5.2 | -0.7, 5.4, -12.4..10.1 | 91 / 11.6 | -0.2, 4.8, -9.6..10.7 | 93 / 10.3 | 63 / 72 | 68 / 79 | 3% | 3.3% / 2.3% |

### zh, Japanese L1 (cognates), skip-if-unknown 0.7

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 6.1 | 0.1, 5.0, -10.6..11.3 | 91 / 10.5 | (reports meaning) 29.2 | 4 / — | 62 / 70 | 64 / 76 | 96% | 46.6% / 4.1% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.5 | -2.3, 6.3, -13.8..11.2 | 86 / 11.4 | (reports meaning) 26.9 | 10 / — | 54 / 61 | 71 / 83 | 90% | 53.4% / 4.7% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.5 | 0.7, 6.5, -14.2..15.1 | 86 / 13.1 | (reports meaning) 29.8 | 8 / — | 57 / 67 | 59 / 73 | 92% | 49.7% / 4.2% |
| D3 IRT, reading after correct meaning | 60 (23) | 5.7 / 5.5 | -2.9, 6.1, -15.4..9.1 | 88 / 11.9 | -0.2, 4.7, -10.4..9.8 | 93 / 10.7 | 55 / 61 | 63 / 70 | 4% | 8.6% / 1.4% |
| D3S adaptive bands, reading after correct meaning | 60 (23) | 5.6 / 5.5 | -0.5, 6.2, -12.7..11.2 | 92 / 13.9 | -0.5, 5.6, -11.3..11.5 | 92 / 12.1 | 55 / 66 | 68 / 78 | 4% | 8.1% / 1.2% |

### ja, Chinese L1 (cognates), skip-if-unknown 0.7

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 6.1 | -0.3, 5.1, -11.9..9.9 | 89 / 10.6 | (reports meaning) 15.4 | 31 / — | 75 / 83 | 77 / 85 | 69% | 25.8% / 4.1% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.5 | 0.7, 5.4, -10.5..12.6 | 90 / 11.3 | (reports meaning) 16.4 | 34 / — | 73 / 78 | 77 / 84 | 66% | 32.4% / 4.2% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.5 | -0.7, 6.5, -14.1..12.9 | 87 / 13.0 | (reports meaning) 15.0 | 41 / — | 72 / 81 | 72 / 81 | 59% | 28.1% / 4.4% |
| D3 IRT, reading after correct meaning | 60 (19) | 5.7 / 5.4 | 0.1, 5.5, -11.3..12.8 | 90 / 11.2 | 0.5, 4.9, -9.7..10.7 | 92 / 10.7 | 73 / 78 | 70 / 75 | 4% | 5.7% / 2.4% |
| D3S adaptive bands, reading after correct meaning | 60 (18) | 5.7 / 5.3 | -0.6, 5.6, -12.8..11.0 | 90 / 12.8 | 0.3, 5.4, -11.0..11.8 | 92 / 12.2 | 76 / 85 | 77 / 87 | 3% | 5.4% / 2.9% |

## Precision vs number of items (fixed-length snapshots)

Mean 90% half-width and MAE of the meaning count (and of the meaning+reading count for reading designs), % of N, averaged over all populations of the language; coverage in brackets.

### zh

| design | n=20 | n=30 | n=40 | n=50 | n=60 | n=70 | n=90 |
|---|---|---|---|---|---|---|---|
| D0 | m ±20.0 MAE 8.8 (92%) | m ±16.0 MAE 7.4 (92%) | m ±13.6 MAE 6.2 (90%) | m ±12.0 MAE 5.6 (91%) | m ±10.9 MAE 5.2 (92%) | m ±10.0 MAE 4.9 (89%) | — |
| D1 | m ±14.5 MAE 7.0 (92%) | m ±12.2 MAE 6.1 (90%) | m ±10.7 MAE 5.4 (90%) | m ±9.7 MAE 4.9 (91%) | m ±9.0 MAE 4.5 (90%) | m ±8.4 MAE 4.1 (89%) | — |
| D1S | m ±18.6 MAE 8.8 (92%) | m ±14.6 MAE 7.1 (90%) | m ±12.4 MAE 5.9 (89%) | m ±11.0 MAE 5.3 (90%) | m ±9.9 MAE 4.7 (91%) | m ±9.1 MAE 4.3 (90%) | — |
| D3 | m ±17.6 MAE 8.0 (92%); m+r ±16.1 MAE 7.0 (93%) | m ±14.9 MAE 7.2 (92%); m+r ±13.7 MAE 5.8 (95%) | m ±13.2 MAE 6.5 (91%); m+r ±12.2 MAE 5.4 (93%) | m ±11.9 MAE 5.9 (92%); m+r ±11.1 MAE 5.0 (94%) | m ±11.0 MAE 5.4 (91%); m+r ±10.2 MAE 4.5 (94%) | m ±10.3 MAE 5.1 (90%); m+r ±9.5 MAE 4.3 (93%) | m ±9.1 MAE 4.4 (92%); m+r ±8.5 MAE 3.6 (94%) |
| D3S | m ±26.0 MAE 11.4 (92%); m+r ±23.9 MAE 9.5 (96%) | m ±19.2 MAE 8.3 (93%); m+r ±17.3 MAE 7.3 (93%) | m ±16.0 MAE 6.9 (93%); m+r ±14.3 MAE 6.2 (94%) | m ±14.1 MAE 6.2 (92%); m+r ±12.5 MAE 5.5 (93%) | m ±12.7 MAE 5.8 (92%); m+r ±11.2 MAE 5.2 (93%) | m ±11.7 MAE 5.4 (92%); m+r ±10.2 MAE 4.8 (93%) | m ±10.2 MAE 4.7 (92%); m+r ±8.9 MAE 4.1 (91%) |

### ja

| design | n=20 | n=30 | n=40 | n=50 | n=60 | n=70 | n=90 |
|---|---|---|---|---|---|---|---|
| D0 | m ±20.9 MAE 9.5 (92%) | m ±16.7 MAE 7.7 (92%) | m ±14.3 MAE 6.8 (91%) | m ±12.7 MAE 6.1 (90%) | m ±11.5 MAE 5.4 (92%) | m ±10.6 MAE 5.1 (89%) | — |
| D1 | m ±15.1 MAE 6.9 (89%) | m ±12.8 MAE 6.3 (89%) | m ±11.3 MAE 5.4 (90%) | m ±10.3 MAE 4.9 (90%) | m ±9.5 MAE 4.6 (90%) | m ±8.8 MAE 4.2 (91%) | — |
| D1S | m ±19.6 MAE 9.7 (91%) | m ±15.3 MAE 7.3 (88%) | m ±13.0 MAE 6.5 (87%) | m ±11.6 MAE 5.7 (89%) | m ±10.4 MAE 5.3 (88%) | m ±9.6 MAE 4.7 (89%) | — |
| D3 | m ±17.5 MAE 7.8 (95%); m+r ±16.7 MAE 8.1 (93%) | m ±14.9 MAE 6.9 (91%); m+r ±14.2 MAE 6.8 (92%) | m ±13.3 MAE 6.4 (90%); m+r ±12.7 MAE 6.0 (91%) | m ±12.1 MAE 6.1 (87%); m+r ±11.6 MAE 5.6 (91%) | m ±11.2 MAE 5.5 (90%); m+r ±10.7 MAE 4.9 (92%) | m ±10.5 MAE 5.0 (88%); m+r ±10.0 MAE 4.4 (94%) | m ±9.3 MAE 4.4 (92%); m+r ±9.0 MAE 3.8 (93%) |
| D3S | m ±26.3 MAE 11.5 (93%); m+r ±25.1 MAE 11.6 (92%) | m ±19.4 MAE 8.6 (93%); m+r ±18.4 MAE 8.7 (93%) | m ±16.3 MAE 7.4 (91%); m+r ±15.5 MAE 7.3 (93%) | m ±14.3 MAE 6.4 (92%); m+r ±13.6 MAE 6.1 (91%) | m ±12.8 MAE 5.6 (90%); m+r ±12.2 MAE 5.4 (92%) | m ±11.8 MAE 5.2 (90%); m+r ±11.2 MAE 5.2 (91%) | m ±10.3 MAE 4.4 (91%); m+r ±9.8 MAE 4.7 (91%) |

## Stopping rules (applied to the snapshots; stop at the first checkpoint where every reported 90% half-width <= h x N, after a minimum, else at the cap)

### h = 0.1, min 20, cap 40 (meaning-only) / 60 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.7 | D1 | 37 (20..40) | 27% | 3.3 / 3.6 | 4.6 / 94% | — | 75 |
| zh, English L1 s=0.7 | D1S | 40 (40..40) | 5% | 3.5 / 3.7 | 5.5 / 92% | — | 84 |
| zh, English L1 s=0.7 | D3 | 54 (25..61) | 25% | 4.6 / 5.5 | 4.8 / 95% | 4.4 / 96% | 68 |
| zh, English L1 s=0.7 | D3S | 58 (45..61) | 17% | 5.0 / 5.6 | 5.7 / 91% | 4.9 / 93% | 79 |
| zh, Japanese L1 (cognates) s=0.7 | D1 | 38 (25..40) | 14% | 3.3 / 3.6 | 6.3 / 87% | — | 83 |
| zh, Japanese L1 (cognates) s=0.7 | D1S | 40 (40..40) | 0% | 3.5 / 3.6 | 6.5 / 86% | — | 73 |
| zh, Japanese L1 (cognates) s=0.7 | D3 | 60 (60..61) | 0% | 5.5 / 6.0 | 6.1 / 88% | 4.7 / 93% | 70 |
| zh, Japanese L1 (cognates) s=0.7 | D3S | 60 (60..61) | 0% | 5.5 / 6.1 | 6.2 / 92% | 5.6 / 92% | 78 |
| ja, Chinese L1 (cognates) s=0.7 | D1 | 39 (30..40) | 15% | 3.4 / 3.6 | 5.4 / 90% | — | 84 |
| ja, Chinese L1 (cognates) s=0.7 | D1S | 40 (40..40) | 0% | 3.5 / 3.6 | 6.5 / 87% | — | 81 |
| ja, Chinese L1 (cognates) s=0.7 | D3 | 60 (60..61) | 1% | 5.3 / 5.9 | 5.5 / 90% | 4.9 / 92% | 75 |
| ja, Chinese L1 (cognates) s=0.7 | D3S | 60 (60..61) | 0% | 5.3 / 5.8 | 5.6 / 90% | 5.4 / 92% | 87 |

### h = 0.12, min 20, cap 40 (meaning-only) / 60 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.7 | D1 | 32 (20..40) | 71% | 2.8 / 3.6 | 5.0 / 94% | — | 76 |
| zh, English L1 s=0.7 | D1S | 38 (30..40) | 30% | 3.3 / 3.6 | 5.7 / 93% | — | 84 |
| zh, English L1 s=0.7 | D3 | 48 (20..61) | 49% | 4.1 / 5.3 | 5.1 / 94% | 4.6 / 96% | 68 |
| zh, English L1 s=0.7 | D3S | 53 (35..61) | 38% | 4.5 / 5.4 | 6.0 / 91% | 5.0 / 94% | 79 |
| zh, Japanese L1 (cognates) s=0.7 | D1 | 35 (20..40) | 41% | 3.1 / 3.6 | 6.4 / 87% | — | 79 |
| zh, Japanese L1 (cognates) s=0.7 | D1S | 40 (40..40) | 3% | 3.5 / 3.6 | 6.5 / 86% | — | 73 |
| zh, Japanese L1 (cognates) s=0.7 | D3 | 60 (60..61) | 3% | 5.4 / 6.0 | 6.2 / 88% | 4.7 / 93% | 70 |
| zh, Japanese L1 (cognates) s=0.7 | D3S | 60 (60..61) | 0% | 5.5 / 6.1 | 6.2 / 92% | 5.6 / 92% | 78 |
| ja, Chinese L1 (cognates) s=0.7 | D1 | 35 (20..40) | 44% | 3.0 / 3.6 | 6.0 / 89% | — | 84 |
| ja, Chinese L1 (cognates) s=0.7 | D1S | 40 (40..40) | 1% | 3.5 / 3.6 | 6.5 / 87% | — | 81 |
| ja, Chinese L1 (cognates) s=0.7 | D3 | 57 (45..61) | 26% | 5.1 / 5.9 | 5.8 / 90% | 5.1 / 92% | 75 |
| ja, Chinese L1 (cognates) s=0.7 | D3S | 60 (60..61) | 0% | 5.3 / 5.8 | 5.6 / 90% | 5.4 / 92% | 87 |

### h = 0.08, min 20, cap 60 (meaning-only) / 90 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.7 | D1 | 55 (30..60) | 21% | 4.9 / 5.5 | 3.6 / 93% | — | 77 |
| zh, English L1 s=0.7 | D1S | 59 (60..60) | 4% | 5.3 / 5.5 | 4.5 / 92% | — | 85 |
| zh, English L1 s=0.7 | D3 | 83 (45..91) | 24% | 7.1 / 8.2 | 3.9 / 94% | 3.4 / 96% | 70 |
| zh, English L1 s=0.7 | D3S | 86 (60..91) | 19% | 7.4 / 8.2 | 4.6 / 91% | 3.9 / 93% | 79 |
| zh, Japanese L1 (cognates) s=0.7 | D1 | 58 (40..60) | 10% | 5.0 / 5.4 | 5.5 / 86% | — | 84 |
| zh, Japanese L1 (cognates) s=0.7 | D1S | 60 (60..60) | 0% | 5.2 / 5.4 | 5.0 / 90% | — | 77 |
| zh, Japanese L1 (cognates) s=0.7 | D3 | 90 (90..91) | 0% | 8.2 / 9.0 | 5.0 / 91% | 3.9 / 93% | 71 |
| zh, Japanese L1 (cognates) s=0.7 | D3S | 90 (90..91) | 0% | 8.2 / 9.1 | 4.8 / 94% | 4.4 / 90% | 82 |
| ja, Chinese L1 (cognates) s=0.7 | D1 | 58 (45..60) | 10% | 5.1 / 5.4 | 4.6 / 89% | — | 87 |
| ja, Chinese L1 (cognates) s=0.7 | D1S | 60 (60..60) | 0% | 5.2 / 5.4 | 5.3 / 88% | — | 85 |
| ja, Chinese L1 (cognates) s=0.7 | D3 | 90 (90..91) | 1% | 8.0 / 8.8 | 4.4 / 92% | 3.8 / 93% | 76 |
| ja, Chinese L1 (cognates) s=0.7 | D3S | 90 (90..91) | 0% | 7.9 / 8.6 | 4.4 / 91% | 4.7 / 91% | 84 |

### h = 0.1, min 20, cap 60 (meaning-only) / 90 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.7 | D1 | 46 (20..60) | 65% | 4.1 / 5.4 | 4.0 / 95% | — | 77 |
| zh, English L1 s=0.7 | D1S | 54 (40..60) | 36% | 4.8 / 5.4 | 4.9 / 92% | — | 85 |
| zh, English L1 s=0.7 | D3 | 70 (25..91) | 60% | 6.0 / 7.9 | 4.4 / 93% | 3.9 / 94% | 70 |
| zh, English L1 s=0.7 | D3S | 77 (45..91) | 46% | 6.6 / 8.0 | 4.9 / 92% | 4.1 / 92% | 79 |
| zh, Japanese L1 (cognates) s=0.7 | D1 | 53 (25..60) | 35% | 4.6 / 5.4 | 5.7 / 86% | — | 83 |
| zh, Japanese L1 (cognates) s=0.7 | D1S | 59 (50..60) | 7% | 5.1 / 5.4 | 5.0 / 89% | — | 77 |
| zh, Japanese L1 (cognates) s=0.7 | D3 | 90 (81..91) | 6% | 8.2 / 9.0 | 5.0 / 91% | 3.9 / 93% | 71 |
| zh, Japanese L1 (cognates) s=0.7 | D3S | 90 (90..91) | 0% | 8.2 / 9.1 | 4.8 / 94% | 4.4 / 90% | 82 |
| ja, Chinese L1 (cognates) s=0.7 | D1 | 52 (30..60) | 39% | 4.6 / 5.4 | 4.7 / 90% | — | 86 |
| ja, Chinese L1 (cognates) s=0.7 | D1S | 59 (50..60) | 6% | 5.2 / 5.4 | 5.3 / 88% | — | 85 |
| ja, Chinese L1 (cognates) s=0.7 | D3 | 85 (70..91) | 31% | 7.6 / 8.7 | 4.6 / 91% | 4.0 / 93% | 77 |
| ja, Chinese L1 (cognates) s=0.7 | D3S | 90 (81..91) | 5% | 7.9 / 8.6 | 4.5 / 90% | 4.7 / 91% | 83 |

## By ability (budget snapshot), all populations of a language pooled

Ability groups by the learner's study frontier tau (Zipf at 50% known): beginner tau >= 5.5, intermediate 4.0-5.5, advanced < 4.0.

| lang | design | group | n learners | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|
| zh | D0 | beginner | 213 | 5.4 / 86% | — | 100 |
| zh | D0 | intermediate | 204 | 4.9 / 89% | — | 55 |
| zh | D0 | advanced | 183 | 4.1 / 93% | — | 84 |
| zh | D1 | beginner | 213 | 5.5 / 89% | — | 100 |
| zh | D1 | intermediate | 204 | 5.7 / 90% | — | 63 |
| zh | D1 | advanced | 183 | 5.1 / 92% | — | 73 |
| zh | D1S | beginner | 213 | 6.5 / 87% | — | 96 |
| zh | D1S | intermediate | 204 | 6.5 / 86% | — | 55 |
| zh | D1S | advanced | 183 | 4.7 / 96% | — | 85 |
| zh | D3 | beginner | 213 | 5.5 / 89% | 3.2 / 95% | 100 |
| zh | D3 | intermediate | 204 | 5.5 / 90% | 4.6 / 95% | 66 |
| zh | D3 | advanced | 183 | 5.3 / 93% | 5.7 / 92% | 36 |
| zh | D3S | beginner | 213 | 5.5 / 91% | 3.5 / 96% | 100 |
| zh | D3S | intermediate | 204 | 6.1 / 91% | 6.3 / 90% | 67 |
| zh | D3S | advanced | 183 | 5.8 / 94% | 6.1 / 92% | 66 |
| ja | D0 | beginner | 106 | 5.6 / 88% | — | 100 |
| ja | D0 | intermediate | 92 | 5.2 / 86% | — | 87 |
| ja | D0 | advanced | 102 | 4.4 / 92% | — | 69 |
| ja | D1 | beginner | 106 | 7.0 / 85% | — | 100 |
| ja | D1 | intermediate | 92 | 5.5 / 91% | — | 87 |
| ja | D1 | advanced | 102 | 3.8 / 94% | — | 65 |
| ja | D1S | beginner | 106 | 6.8 / 84% | — | 99 |
| ja | D1S | intermediate | 92 | 7.2 / 86% | — | 72 |
| ja | D1S | advanced | 102 | 5.7 / 90% | — | 71 |
| ja | D3 | beginner | 106 | 6.5 / 86% | 5.2 / 91% | 100 |
| ja | D3 | intermediate | 92 | 5.6 / 89% | 4.7 / 93% | 90 |
| ja | D3 | advanced | 102 | 4.3 / 96% | 4.9 / 93% | 36 |
| ja | D3S | beginner | 106 | 6.0 / 87% | 5.5 / 88% | 100 |
| ja | D3S | intermediate | 92 | 6.3 / 88% | 5.5 / 93% | 88 |
| ja | D3S | advanced | 102 | 4.6 / 96% | 5.3 / 94% | 72 |
