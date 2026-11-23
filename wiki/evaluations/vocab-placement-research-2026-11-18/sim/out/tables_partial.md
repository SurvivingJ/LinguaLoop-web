# Simulation tables — run `raw_partial.json`

Learners per population: 300. Config: `{"max_m": 70, "max_tot": 90, "designs": "D0,D2,D3,D3S", "pops": "zh:E:0.7,zh:J:0.7,ja:E:0.7,ja:Z:0.7", "sig_eps": 1.2, "a_med": 1.6, "gamma_max": 1.0, "tau_lo": 2.5, "tau_hi": 7.0, "partial": 1, "seed": 11}`. Runtime 286.5 s.

All numbers are ESTIMATES from simulation. Errors are in % of the check pool (N words). Intervals are 90%. "e5..e95" is the 90% range of the error across learners.

## Populations (truth)

| population | skip | N | mean known by meaning (% of N) | mean known by meaning+reading (%) | meaning-only words (% of known) | true placement by meaning: share at 0 / at max | by meaning+reading: 0 / max |
|---|---|---|---|---|---|---|---|
| zh, English L1 | 0.7 | 3623 | 37.9 | 33.3 | 12.1 | 43% / 22% | 56% / 16% |
| zh, Japanese L1 (cognates) | 0.7 | 3623 | 62.8 | 33.8 | 46.2 | 34% / 32% | 59% / 13% |
| ja, English L1 | 0.7 | 3175 | 40.2 | 38.3 | 4.9 | 63% / 19% | 68% / 15% |
| ja, Chinese L1 (cognates) | 0.7 | 3175 | 60.8 | 45.3 | 25.6 | 52% / 29% | 68% / 15% |

## At a fixed budget (D0 70, meaning-only 40, with readings 60 items)

### zh, English L1, skip-if-unknown 0.7

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 6.2 | 0.2, 4.8, -9.0..9.6 | 90 / 9.8 | (reports meaning) 4.8 | 76 / — | 63 / 74 | 72 / 84 | 22% | 20.2% / 9.7% |
| D2 IRT, meaning+reading every word | 60 (30) | 5.5 / 5.6 | 1.2, 5.4, -10.6..11.6 | 95 / 11.9 | 0.2, 4.9, -12.0..9.6 | 95 / 11.3 | 56 / 65 | 62 / 69 | 2% | 6.9% / 2.3% |
| D3 IRT, reading after correct meaning | 60 (18) | 5.7 / 5.1 | 1.0, 4.6, -9.5..9.0 | 94 / 10.4 | 0.7, 4.0, -8.7..8.6 | 97 / 10.1 | 57 / 64 | 64 / 70 | 2% | 7.3% / 2.7% |
| D3S adaptive bands, reading after correct meaning | 60 (17) | 5.7 / 5.2 | -1.0, 5.7, -12.2..11.1 | 91 / 11.7 | 0.4, 5.0, -8.7..11.8 | 94 / 10.6 | 62 / 69 | 70 / 79 | 4% | 6.8% / 2.7% |

### zh, Japanese L1 (cognates), skip-if-unknown 0.7

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 6.1 | -0.4, 5.1, -12.0..8.7 | 90 / 10.6 | (reports meaning) 28.6 | 3 / — | 63 / 69 | 66 / 79 | 97% | 45.8% / 3.9% |
| D2 IRT, meaning+reading every word | 60 (30) | 5.5 / 5.5 | -3.7, 6.4, -15.1..7.2 | 91 / 13.2 | 3.7, 6.7, -7.8..17.9 | 89 / 12.5 | 53 / 61 | 66 / 71 | 10% | 21.4% / 1.4% |
| D3 IRT, reading after correct meaning | 60 (23) | 5.7 / 5.2 | -3.7, 5.9, -14.1..6.9 | 90 / 12.1 | 3.8, 6.3, -7.4..15.0 | 87 / 11.6 | 56 / 61 | 68 / 73 | 12% | 20.0% / 1.4% |
| D3S adaptive bands, reading after correct meaning | 60 (23) | 5.6 / 5.2 | -0.5, 6.8, -13.0..14.4 | 90 / 13.8 | 3.1, 6.6, -8.8..16.9 | 89 / 13.0 | 59 / 69 | 69 / 78 | 10% | 20.5% / 1.4% |

### ja, English L1, skip-if-unknown 0.7

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 6.2 | -0.5, 4.9, -11.0..9.9 | 89 / 10.2 | (reports meaning) 1.4 | 89 / — | 77 / 82 | 81 / 88 | 7% | 12.7% / 8.2% |
| D2 IRT, meaning+reading every word | 60 (30) | 5.5 / 5.6 | -2.6, 5.3, -12.0..7.5 | 93 / 11.6 | -3.8, 5.4, -12.2..5.2 | 90 / 11.0 | 72 / 77 | 73 / 77 | 0% | 3.9% / 1.5% |
| D3 IRT, reading after correct meaning | 60 (14) | 5.8 / 5.1 | -2.9, 5.0, -11.5..7.2 | 87 / 9.7 | -4.0, 5.3, -11.8..4.7 | 85 / 9.5 | 72 / 77 | 71 / 76 | 0% | 6.6% / 4.4% |
| D3S adaptive bands, reading after correct meaning | 60 (13) | 5.8 / 5.2 | -0.7, 5.5, -11.0..12.1 | 88 / 11.4 | 0.1, 5.1, -9.4..10.7 | 90 / 10.7 | 78 / 86 | 79 / 85 | 4% | 6.4% / 5.2% |

### ja, Chinese L1 (cognates), skip-if-unknown 0.7

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 6.1 | -0.1, 5.0, -10.1..10.2 | 91 / 10.6 | (reports meaning) 15.4 | 28 / — | 78 / 86 | 76 / 83 | 72% | 26.2% / 3.8% |
| D2 IRT, meaning+reading every word | 60 (30) | 5.5 / 5.5 | 0.0, 5.5, -11.1..11.4 | 94 / 13.0 | 2.8, 5.7, -8.0..14.1 | 90 / 12.2 | 71 / 78 | 75 / 79 | 9% | 15.2% / 0.8% |
| D3 IRT, reading after correct meaning | 60 (19) | 5.7 / 5.2 | -0.0, 5.2, -10.8..11.2 | 91 / 11.3 | 3.1, 5.8, -7.4..14.7 | 86 / 11.2 | 72 / 78 | 75 / 80 | 13% | 12.1% / 2.4% |
| D3S adaptive bands, reading after correct meaning | 60 (19) | 5.7 / 5.1 | -0.2, 5.9, -13.1..10.9 | 90 / 12.9 | 2.4, 6.7, -10.5..15.6 | 85 / 12.6 | 76 / 82 | 80 / 88 | 11% | 11.1% / 3.0% |

## Precision vs number of items (fixed-length snapshots)

Mean 90% half-width and MAE of the meaning count (and of the meaning+reading count for reading designs), % of N, averaged over all populations of the language; coverage in brackets.

### zh

| design | n=20 | n=30 | n=40 | n=50 | n=60 | n=70 | n=90 |
|---|---|---|---|---|---|---|---|
| D0 | m ±20.2 MAE 9.0 (93%) | m ±16.1 MAE 7.3 (92%) | m ±13.8 MAE 6.4 (90%) | m ±12.2 MAE 5.6 (91%) | m ±11.1 MAE 5.3 (91%) | m ±10.2 MAE 4.9 (90%) | — |
| D2 | m ±19.3 MAE 8.8 (94%); m+r ±17.9 MAE 8.7 (93%) | m ±16.6 MAE 7.6 (93%); m+r ±15.5 MAE 7.3 (92%) | m ±14.8 MAE 7.2 (92%); m+r ±14.0 MAE 6.9 (91%) | m ±13.6 MAE 6.5 (92%); m+r ±12.8 MAE 6.3 (92%) | m ±12.5 MAE 5.9 (93%); m+r ±11.9 MAE 5.8 (92%) | m ±11.7 MAE 5.6 (92%); m+r ±11.1 MAE 5.5 (90%) | m ±10.5 MAE 5.1 (91%); m+r ±10.0 MAE 5.0 (91%) |
| D3 | m ±17.9 MAE 8.3 (92%); m+r ±16.8 MAE 7.9 (93%) | m ±15.2 MAE 7.2 (93%); m+r ±14.4 MAE 6.8 (93%) | m ±13.5 MAE 6.4 (92%); m+r ±12.8 MAE 6.0 (91%) | m ±12.2 MAE 5.8 (92%); m+r ±11.7 MAE 5.6 (92%) | m ±11.2 MAE 5.3 (92%); m+r ±10.8 MAE 5.2 (92%) | m ±10.5 MAE 4.9 (92%); m+r ±10.1 MAE 5.0 (91%) | m ±9.4 MAE 4.5 (92%); m+r ±9.1 MAE 4.5 (90%) |
| D3S | m ±25.9 MAE 11.9 (92%); m+r ±24.3 MAE 10.7 (93%) | m ±19.2 MAE 8.8 (92%); m+r ±17.9 MAE 7.7 (92%) | m ±16.1 MAE 7.4 (91%); m+r ±14.9 MAE 6.9 (91%) | m ±14.2 MAE 6.7 (90%); m+r ±13.1 MAE 6.3 (91%) | m ±12.8 MAE 6.2 (90%); m+r ±11.8 MAE 5.8 (92%) | m ±11.7 MAE 5.7 (90%); m+r ±10.8 MAE 5.4 (89%) | m ±10.3 MAE 5.0 (90%); m+r ±9.4 MAE 4.9 (89%) |

### ja

| design | n=20 | n=30 | n=40 | n=50 | n=60 | n=70 | n=90 |
|---|---|---|---|---|---|---|---|
| D0 | m ±20.5 MAE 9.0 (91%) | m ±16.3 MAE 7.4 (91%) | m ±14.0 MAE 6.7 (89%) | m ±12.4 MAE 6.0 (89%) | m ±11.3 MAE 5.5 (89%) | m ±10.4 MAE 5.0 (90%) | — |
| D2 | m ±19.0 MAE 8.3 (93%); m+r ±17.5 MAE 8.2 (92%) | m ±16.4 MAE 7.3 (93%); m+r ±15.2 MAE 7.2 (90%) | m ±14.6 MAE 6.3 (93%); m+r ±13.6 MAE 6.6 (91%) | m ±13.3 MAE 5.9 (92%); m+r ±12.5 MAE 6.1 (89%) | m ±12.3 MAE 5.4 (94%); m+r ±11.6 MAE 5.6 (90%) | m ±11.5 MAE 5.3 (93%); m+r ±10.9 MAE 5.5 (88%) | m ±10.3 MAE 4.8 (90%); m+r ±9.8 MAE 5.3 (86%) |
| D3 | m ±16.9 MAE 7.8 (93%); m+r ±16.1 MAE 8.1 (90%) | m ±14.2 MAE 6.7 (91%); m+r ±13.8 MAE 7.0 (90%) | m ±12.6 MAE 5.9 (90%); m+r ±12.3 MAE 6.3 (89%) | m ±11.4 MAE 5.4 (90%); m+r ±11.2 MAE 5.8 (86%) | m ±10.5 MAE 5.1 (89%); m+r ±10.3 MAE 5.5 (86%) | m ±9.8 MAE 4.8 (87%); m+r ±9.7 MAE 5.2 (84%) | m ±8.7 MAE 4.5 (87%); m+r ±8.6 MAE 5.0 (82%) |
| D3S | m ±24.6 MAE 11.5 (91%); m+r ±23.8 MAE 11.0 (92%) | m ±18.2 MAE 8.5 (90%); m+r ±17.6 MAE 8.4 (91%) | m ±15.3 MAE 7.5 (88%); m+r ±14.8 MAE 7.2 (89%) | m ±13.4 MAE 6.5 (89%); m+r ±12.9 MAE 6.5 (87%) | m ±12.1 MAE 5.7 (89%); m+r ±11.7 MAE 5.9 (87%) | m ±11.1 MAE 5.1 (90%); m+r ±10.7 MAE 5.5 (88%) | m ±9.7 MAE 4.6 (90%); m+r ±9.4 MAE 4.9 (86%) |

## Stopping rules (applied to the snapshots; stop at the first checkpoint where every reported 90% half-width <= h x N, after a minimum, else at the cap)

### h = 0.1, min 20, cap 40 (meaning-only) / 60 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.7 | D2 | 58 (40..60) | 9% | 5.4 / 6.3 | 5.4 / 95% | 4.9 / 95% | 69 |
| zh, English L1 s=0.7 | D3 | 55 (30..61) | 22% | 4.6 / 5.4 | 4.8 / 95% | 4.2 / 97% | 70 |
| zh, English L1 s=0.7 | D3S | 58 (45..61) | 15% | 5.0 / 5.5 | 5.9 / 90% | 5.0 / 94% | 79 |
| zh, Japanese L1 (cognates) s=0.7 | D2 | 60 (60..60) | 0% | 5.5 / 6.3 | 6.4 / 91% | 6.7 / 89% | 71 |
| zh, Japanese L1 (cognates) s=0.7 | D3 | 60 (60..61) | 0% | 5.2 / 5.7 | 5.9 / 90% | 6.3 / 87% | 73 |
| zh, Japanese L1 (cognates) s=0.7 | D3S | 60 (60..61) | 0% | 5.2 / 5.7 | 6.8 / 90% | 6.6 / 89% | 78 |
| ja, English L1 s=0.7 | D2 | 57 (30..60) | 13% | 5.3 / 6.3 | 5.3 / 94% | 5.4 / 91% | 77 |
| ja, English L1 s=0.7 | D3 | 54 (25..61) | 28% | 4.6 / 5.3 | 4.7 / 92% | 5.1 / 90% | 76 |
| ja, English L1 s=0.7 | D3S | 58 (45..61) | 13% | 5.0 / 5.5 | 5.7 / 88% | 5.3 / 89% | 85 |
| ja, Chinese L1 (cognates) s=0.7 | D2 | 60 (60..60) | 0% | 5.5 / 6.2 | 5.5 / 94% | 5.7 / 90% | 79 |
| ja, Chinese L1 (cognates) s=0.7 | D3 | 60 (60..61) | 1% | 5.2 / 5.6 | 5.2 / 91% | 5.8 / 86% | 80 |
| ja, Chinese L1 (cognates) s=0.7 | D3S | 60 (60..61) | 0% | 5.1 / 5.5 | 5.9 / 90% | 6.7 / 85% | 88 |

### h = 0.12, min 20, cap 40 (meaning-only) / 60 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.7 | D2 | 55 (26..60) | 21% | 5.1 / 6.1 | 5.4 / 94% | 4.9 / 95% | 69 |
| zh, English L1 s=0.7 | D3 | 49 (20..61) | 45% | 4.1 / 5.2 | 4.9 / 94% | 4.4 / 96% | 70 |
| zh, English L1 s=0.7 | D3S | 53 (35..61) | 36% | 4.5 / 5.3 | 6.1 / 91% | 5.1 / 93% | 79 |
| zh, Japanese L1 (cognates) s=0.7 | D2 | 60 (60..60) | 1% | 5.5 / 6.3 | 6.4 / 91% | 6.7 / 89% | 71 |
| zh, Japanese L1 (cognates) s=0.7 | D3 | 60 (60..61) | 2% | 5.2 / 5.7 | 6.0 / 90% | 6.3 / 87% | 73 |
| zh, Japanese L1 (cognates) s=0.7 | D3S | 60 (60..61) | 1% | 5.2 / 5.6 | 6.8 / 90% | 6.6 / 89% | 78 |
| ja, English L1 s=0.7 | D2 | 53 (26..60) | 33% | 4.9 / 5.9 | 5.3 / 94% | 5.4 / 92% | 77 |
| ja, English L1 s=0.7 | D3 | 45 (20..61) | 68% | 3.8 / 5.1 | 5.0 / 93% | 5.4 / 90% | 76 |
| ja, English L1 s=0.7 | D3S | 54 (30..61) | 35% | 4.6 / 5.3 | 6.0 / 89% | 5.6 / 92% | 85 |
| ja, Chinese L1 (cognates) s=0.7 | D2 | 59 (50..60) | 8% | 5.4 / 6.2 | 5.5 / 94% | 5.8 / 89% | 79 |
| ja, Chinese L1 (cognates) s=0.7 | D3 | 57 (45..61) | 22% | 4.9 / 5.6 | 5.2 / 92% | 5.8 / 87% | 81 |
| ja, Chinese L1 (cognates) s=0.7 | D3S | 60 (60..61) | 1% | 5.1 / 5.5 | 6.0 / 90% | 6.8 / 84% | 88 |

### h = 0.08, min 20, cap 60 (meaning-only) / 90 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.7 | D2 | 88 (70..90) | 8% | 8.2 / 9.4 | 4.5 / 94% | 4.0 / 94% | 69 |
| zh, English L1 s=0.7 | D3 | 84 (45..91) | 20% | 7.1 / 8.1 | 3.8 / 94% | 3.4 / 96% | 71 |
| zh, English L1 s=0.7 | D3S | 87 (60..91) | 16% | 7.4 / 8.2 | 4.7 / 89% | 4.0 / 92% | 79 |
| zh, Japanese L1 (cognates) s=0.7 | D2 | 90 (90..90) | 0% | 8.3 / 9.4 | 5.8 / 89% | 6.0 / 87% | 72 |
| zh, Japanese L1 (cognates) s=0.7 | D3 | 90 (90..91) | 0% | 7.8 / 8.5 | 5.1 / 89% | 5.6 / 84% | 74 |
| zh, Japanese L1 (cognates) s=0.7 | D3S | 90 (90..91) | 0% | 7.8 / 8.5 | 5.3 / 91% | 5.7 / 87% | 80 |
| ja, English L1 s=0.7 | D2 | 86 (50..90) | 13% | 8.1 / 9.4 | 4.8 / 90% | 5.0 / 87% | 78 |
| ja, English L1 s=0.7 | D3 | 81 (35..91) | 30% | 6.9 / 8.0 | 4.6 / 88% | 4.7 / 87% | 78 |
| ja, English L1 s=0.7 | D3S | 87 (70..91) | 16% | 7.4 / 8.2 | 4.8 / 87% | 4.2 / 88% | 88 |
| ja, Chinese L1 (cognates) s=0.7 | D2 | 90 (90..90) | 1% | 8.2 / 9.2 | 5.0 / 91% | 5.6 / 86% | 81 |
| ja, Chinese L1 (cognates) s=0.7 | D3 | 90 (90..91) | 1% | 7.7 / 8.3 | 4.5 / 91% | 5.3 / 82% | 80 |
| ja, Chinese L1 (cognates) s=0.7 | D3S | 90 (90..91) | 0% | 7.7 / 8.2 | 4.4 / 93% | 5.7 / 85% | 87 |

### h = 0.1, min 20, cap 60 (meaning-only) / 90 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.7 | D2 | 82 (40..90) | 25% | 7.6 / 9.1 | 4.6 / 94% | 4.2 / 94% | 69 |
| zh, English L1 s=0.7 | D3 | 72 (30..91) | 58% | 6.1 / 7.7 | 4.2 / 96% | 3.7 / 96% | 72 |
| zh, English L1 s=0.7 | D3S | 78 (45..91) | 42% | 6.6 / 7.9 | 5.1 / 88% | 4.2 / 94% | 79 |
| zh, Japanese L1 (cognates) s=0.7 | D2 | 90 (90..90) | 2% | 8.3 / 9.4 | 5.8 / 89% | 6.0 / 88% | 72 |
| zh, Japanese L1 (cognates) s=0.7 | D3 | 90 (90..91) | 3% | 7.8 / 8.5 | 5.1 / 89% | 5.6 / 83% | 74 |
| zh, Japanese L1 (cognates) s=0.7 | D3S | 90 (90..91) | 1% | 7.8 / 8.4 | 5.4 / 91% | 5.7 / 88% | 80 |
| ja, English L1 s=0.7 | D2 | 79 (30..90) | 35% | 7.4 / 9.0 | 4.6 / 93% | 4.9 / 89% | 78 |
| ja, English L1 s=0.7 | D3 | 66 (25..90) | 82% | 5.6 / 7.6 | 4.5 / 91% | 4.7 / 90% | 77 |
| ja, English L1 s=0.7 | D3S | 78 (45..91) | 47% | 6.6 / 7.8 | 5.1 / 89% | 4.6 / 86% | 88 |
| ja, Chinese L1 (cognates) s=0.7 | D2 | 88 (70..90) | 12% | 8.1 / 9.2 | 5.0 / 92% | 5.6 / 86% | 83 |
| ja, Chinese L1 (cognates) s=0.7 | D3 | 86 (70..91) | 28% | 7.4 / 8.3 | 4.5 / 90% | 5.3 / 84% | 81 |
| ja, Chinese L1 (cognates) s=0.7 | D3S | 90 (90..91) | 5% | 7.7 / 8.2 | 4.5 / 93% | 5.7 / 85% | 87 |

## By ability (budget snapshot), all populations of a language pooled

Ability groups by the learner's study frontier tau (Zipf at 50% known): beginner tau >= 5.5, intermediate 4.0-5.5, advanced < 4.0.

| lang | design | group | n learners | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|
| zh | D0 | beginner | 213 | 4.9 / 89% | — | 100 |
| zh | D0 | intermediate | 204 | 5.4 / 88% | — | 66 |
| zh | D0 | advanced | 183 | 4.5 / 93% | — | 77 |
| zh | D3 | beginner | 213 | 5.5 / 90% | 5.7 / 85% | 100 |
| zh | D3 | intermediate | 204 | 5.2 / 93% | 5.1 / 94% | 71 |
| zh | D3 | advanced | 183 | 5.1 / 93% | 4.7 / 98% | 39 |
| zh | D3S | beginner | 213 | 6.1 / 90% | 4.5 / 93% | 100 |
| zh | D3S | intermediate | 204 | 6.7 / 89% | 6.5 / 90% | 73 |
| zh | D3S | advanced | 183 | 5.8 / 93% | 6.5 / 91% | 61 |
| ja | D0 | beginner | 202 | 5.4 / 87% | — | 100 |
| ja | D0 | intermediate | 196 | 5.2 / 88% | — | 90 |
| ja | D0 | advanced | 202 | 4.2 / 95% | — | 67 |
| ja | D3 | beginner | 202 | 5.3 / 86% | 5.8 / 76% | 100 |
| ja | D3 | intermediate | 196 | 5.4 / 90% | 5.4 / 89% | 95 |
| ja | D3 | advanced | 202 | 4.6 / 91% | 5.4 / 92% | 41 |
| ja | D3S | beginner | 202 | 5.9 / 86% | 5.7 / 85% | 100 |
| ja | D3S | intermediate | 196 | 6.1 / 88% | 6.0 / 87% | 95 |
| ja | D3S | advanced | 202 | 5.1 / 95% | 6.1 / 91% | 64 |
