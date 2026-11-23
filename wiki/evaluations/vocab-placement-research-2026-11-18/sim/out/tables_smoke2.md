# Simulation tables — run `raw_smoke2.json`

Learners per population: 6. Config: `{"max_m": 70, "max_tot": 90, "designs": "D0,D1,D1S,D1L,D2,D3,D4,D3S,D3L", "pops": "zh:E:0.3,zh:E:0.7,zh:J:0.3,zh:J:0.7,ja:E:0.3,ja:E:0.7,ja:Z:0.3,ja:Z:0.7", "sig_eps": 1.2, "a_med": 1.6, "gamma_max": 1.0, "tau_lo": 2.5, "tau_hi": 7.0, "partial": 0, "seed": 11}`. Runtime 17.2 s.

All numbers are ESTIMATES from simulation. Errors are in % of the check pool (N words). Intervals are 90%. "e5..e95" is the 90% range of the error across learners.

## Populations (truth)

| population | skip | N | mean known by meaning (% of N) | mean known by meaning+reading (%) | meaning-only words (% of known) | true placement by meaning: share at 0 / at max | by meaning+reading: 0 / max |
|---|---|---|---|---|---|---|---|
| zh, English L1 | 0.3 | 3623 | 38.8 | 33.9 | 12.7 | 50% / 17% | 50% / 17% |
| zh, English L1 | 0.7 | 3623 | 24.1 | 20.0 | 17.0 | 50% / 0% | 83% / 0% |
| zh, Japanese L1 (cognates) | 0.3 | 3623 | 64.7 | 40.9 | 36.8 | 17% / 50% | 33% / 33% |
| zh, Japanese L1 (cognates) | 0.7 | 3623 | 61.2 | 29.4 | 51.9 | 33% / 33% | 83% / 17% |
| ja, English L1 | 0.3 | 3175 | 41.7 | 38.4 | 8.0 | 50% / 0% | 67% / 0% |
| ja, English L1 | 0.7 | 3175 | 39.5 | 37.5 | 5.1 | 67% / 17% | 67% / 17% |
| ja, Chinese L1 (cognates) | 0.3 | 3175 | 56.7 | 39.1 | 31.0 | 83% / 17% | 83% / 17% |
| ja, Chinese L1 (cognates) | 0.7 | 3175 | 70.0 | 57.8 | 17.5 | 33% / 50% | 33% / 50% |

## At a fixed budget (D0 70, meaning-only 40, with readings 60 items)

### zh, English L1, skip-if-unknown 0.3

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 5.9 | -3.6, 6.7, -13.3..6.1 | 83 / 11.1 | (reports meaning) 1.4 | 83 / — | 67 / 67 | 67 / 67 | 17% | 32.1% / 19.6% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.4 | -0.5, 5.9, -7.9..7.3 | 100 / 11.4 | (reports meaning) 4.5 | 100 / — | 67 / 67 | 67 / 67 | 0% | 36.6% / 19.5% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.4 | -6.0, 8.8, -15.8..4.4 | 67 / 12.8 | (reports meaning) -1.1 | 100 / — | 67 / 67 | 67 / 67 | 0% | 34.6% / 24.3% |
| D1L adaptive exam levels, meaning | 40 (0) | 4.0 / 3.4 | 1.9, 7.4, -7.9..17.3 | 100 / 18.6 | (reports meaning) 6.8 | 83 / — | 83 / 83 | 50 / 67 | 17% | 21.9% / 10.6% |
| D2 IRT, meaning+reading every word | 60 (30) | 5.5 / 5.3 | 0.4, 2.9, -4.3..3.5 | 100 / 14.3 | 11.5, 17.4, -12.8..25.7 | 67 / 24.3 | 67 / 67 | 50 / 50 | 17% | 8.1% / 6.5% |
| D3 IRT, reading after correct meaning | 60 (20) | 5.7 / 5.1 | 5.4, 8.8, -6.4..17.7 | 67 / 11.2 | 6.8, 8.6, -3.3..16.1 | 83 / 17.9 | 67 / 67 | 50 / 67 | 17% | 10.1% / 9.0% |
| D4 IRT, reading on half the words | 60 (20) | 5.7 / 5.2 | 0.0, 3.1, -3.3..6.6 | 100 / 10.9 | 12.1, 15.1, -6.3..24.1 | 100 / 27.7 | 67 / 67 | 50 / 50 | 0% | 22.2% / 6.5% |
| D3S adaptive bands, reading after correct meaning | 60 (18) | 5.7 / 5.1 | -1.2, 5.5, -7.6..7.4 | 100 / 12.8 | -4.9, 5.0, -11.6..0.1 | 67 / 10.9 | 67 / 83 | 67 / 67 | 0% | 9.3% / 6.7% |
| D3L adaptive exam levels, reading after correct meaning | 60 (23) | 5.7 / 4.9 | 2.9, 8.0, -10.9..24.0 | 83 / 19.8 | 7.5, 9.2, -3.8..22.3 | 83 / 17.4 | 50 / 83 | 67 / 83 | 17% | 8.4% / 5.0% |

### zh, English L1, skip-if-unknown 0.7

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 6.3 | 0.6, 6.1, -9.6..9.5 | 67 / 9.6 | (reports meaning) 4.6 | 83 / — | 50 / 67 | 83 / 83 | 17% | 24.5% / 11.9% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.6 | 1.7, 2.1, -0.8..4.4 | 100 / 10.5 | (reports meaning) 5.7 | 100 / — | 50 / 67 | 83 / 83 | 0% | 23.3% / 3.5% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.6 | 0.2, 5.5, -7.5..10.4 | 83 / 11.5 | (reports meaning) 4.2 | 83 / — | 50 / 67 | 83 / 83 | 17% | 31.6% / 17.7% |
| D1L adaptive exam levels, meaning | 40 (0) | 4.0 / 3.5 | -4.6, 7.4, -11.0..5.4 | 100 / 16.4 | (reports meaning) -0.5 | 100 / — | 67 / 83 | 67 / 83 | 0% | 25.7% / 9.5% |
| D2 IRT, meaning+reading every word | 60 (30) | 5.5 / 6.2 | 1.9, 5.8, -6.9..9.6 | 100 / 15.3 | 12.9, 13.6, -1.2..23.6 | 83 / 25.4 | 50 / 67 | 83 / 100 | 17% | 4.8% / 0.0% |
| D3 IRT, reading after correct meaning | 60 (11) | 5.8 / 5.4 | -2.5, 4.0, -7.3..3.3 | 100 / 10.8 | 12.4, 12.4, 5.6..21.3 | 100 / 23.5 | 50 / 67 | 83 / 83 | 0% | 6.4% / 4.3% |
| D4 IRT, reading on half the words | 60 (20) | 5.7 / 6.0 | 2.1, 5.1, -5.7..8.7 | 100 / 10.8 | 11.2, 11.4, 0.2..26.5 | 100 / 26.8 | 50 / 67 | 83 / 83 | 0% | 22.4% / 9.0% |
| D3S adaptive bands, reading after correct meaning | 60 (14) | 5.8 / 5.5 | 2.0, 6.5, -7.5..10.6 | 100 / 11.4 | -1.6, 6.5, -9.6..8.3 | 100 / 9.7 | 50 / 67 | 83 / 83 | 0% | 3.6% / 3.6% |
| D3L adaptive exam levels, reading after correct meaning | 60 (21) | 5.7 / 5.0 | -1.1, 10.1, -10.6..15.5 | 100 / 16.7 | -0.0, 6.1, -7.5..9.8 | 100 / 14.2 | 50 / 67 | 83 / 83 | 0% | 1.9% / 0.9% |

### zh, Japanese L1 (cognates), skip-if-unknown 0.3

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 5.9 | 6.3, 6.3, 2.7..13.8 | 83 / 10.8 | (reports meaning) 30.1 | 0 / — | 67 / 83 | 67 / 83 | 100% | 44.3% / 10.1% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.4 | -0.2, 4.2, -7.0..4.2 | 100 / 11.3 | (reports meaning) 23.6 | 17 / — | 67 / 67 | 67 / 67 | 83% | 41.8% / 11.2% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.3 | 0.5, 3.7, -5.6..7.1 | 100 / 14.1 | (reports meaning) 24.3 | 0 / — | 50 / 67 | 67 / 100 | 100% | 43.2% / 10.7% |
| D1L adaptive exam levels, meaning | 40 (0) | 4.0 / 3.3 | 8.7, 10.5, -4.0..26.2 | 83 / 18.7 | (reports meaning) 32.4 | 17 / — | 83 / 83 | 50 / 67 | 83% | 34.7% / 8.0% |
| D2 IRT, meaning+reading every word | 60 (30) | 5.5 / 5.1 | -6.8, 9.1, -14.4..3.9 | 100 / 13.8 | 1.3, 8.1, -7.5..16.7 | 100 / 14.7 | 33 / 50 | 33 / 50 | 0% | 15.5% / 2.4% |
| D3 IRT, reading after correct meaning | 60 (25) | 5.6 / 5.0 | -0.9, 4.1, -8.0..6.6 | 100 / 12.8 | -3.8, 8.5, -19.8..9.7 | 67 / 11.0 | 50 / 50 | 33 / 33 | 17% | 6.2% / 3.1% |
| D4 IRT, reading on half the words | 60 (20) | 5.7 / 5.1 | -4.7, 10.7, -20.5..13.2 | 50 / 11.9 | -3.7, 10.6, -18.3..9.2 | 67 / 16.2 | 67 / 67 | 33 / 33 | 0% | 31.7% / 5.0% |
| D3S adaptive bands, reading after correct meaning | 60 (24) | 5.7 / 5.0 | -4.3, 6.4, -18.7..3.9 | 83 / 14.8 | -2.2, 5.7, -10.7..5.4 | 100 / 13.6 | 67 / 83 | 33 / 83 | 0% | 7.5% / 2.2% |
| D3L adaptive exam levels, reading after correct meaning | 61 (26) | 5.6 / 4.9 | 1.7, 7.3, -7.0..12.0 | 100 / 21.5 | 4.7, 7.2, -3.9..13.6 | 100 / 18.5 | 83 / 100 | 50 / 50 | 0% | 5.6% / 1.6% |

### zh, Japanese L1 (cognates), skip-if-unknown 0.7

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 6.1 | 2.9, 3.5, -1.0..9.8 | 83 / 10.4 | (reports meaning) 34.7 | 0 / — | 67 / 100 | 67 / 67 | 100% | 55.8% / 4.6% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.5 | -1.3, 5.3, -9.2..5.6 | 83 / 11.6 | (reports meaning) 30.4 | 17 / — | 67 / 83 | 83 / 83 | 83% | 59.5% / 4.7% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.5 | -0.6, 4.4, -5.4..6.8 | 100 / 12.9 | (reports meaning) 31.1 | 0 / — | 83 / 100 | 67 / 67 | 100% | 55.6% / 4.0% |
| D1L adaptive exam levels, meaning | 40 (0) | 4.0 / 3.5 | -0.6, 13.7, -15.4..16.3 | 83 / 17.3 | (reports meaning) 31.2 | 0 / — | 50 / 83 | 50 / 50 | 100% | 38.2% / 2.4% |
| D2 IRT, meaning+reading every word | 60 (30) | 5.5 / 5.8 | 0.2, 3.8, -7.6..7.1 | 100 / 13.1 | -4.3, 6.4, -17.1..3.5 | 83 / 9.3 | 50 / 67 | 83 / 83 | 0% | 5.6% / 0.0% |
| D3 IRT, reading after correct meaning | 60 (24) | 5.7 / 5.6 | 1.7, 3.7, -3.9..7.8 | 100 / 11.5 | 2.4, 3.4, -1.6..8.0 | 83 / 9.2 | 83 / 100 | 100 / 100 | 17% | 13.7% / 2.7% |
| D4 IRT, reading on half the words | 60 (20) | 5.7 / 5.5 | -2.8, 5.9, -7.5..6.4 | 100 / 11.6 | 8.3, 8.3, 3.1..16.2 | 100 / 14.2 | 50 / 83 | 100 / 100 | 0% | 46.4% / 4.0% |
| D3S adaptive bands, reading after correct meaning | 60 (23) | 5.7 / 5.6 | -2.4, 8.8, -15.5..13.9 | 50 / 13.7 | -2.3, 4.7, -10.1..4.2 | 100 / 11.7 | 67 / 83 | 100 / 100 | 0% | 4.6% / 1.5% |
| D3L adaptive exam levels, reading after correct meaning | 60 (24) | 5.6 / 5.3 | -7.2, 8.5, -22.8..2.6 | 83 / 19.0 | -6.3, 6.3, -16.0..-0.8 | 100 / 15.6 | 67 / 100 | 50 / 67 | 0% | 5.5% / 1.1% |

### ja, English L1, skip-if-unknown 0.3

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 5.8 | 0.5, 8.6, -16.8..10.5 | 67 / 12.5 | (reports meaning) 3.9 | 67 / — | 50 / 50 | 67 / 100 | 17% | 23.2% / 17.9% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.3 | -2.8, 9.3, -14.2..10.1 | 83 / 12.6 | (reports meaning) 0.6 | 83 / — | 50 / 50 | 67 / 100 | 17% | 35.1% / 22.9% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.3 | 5.2, 7.3, -4.3..17.4 | 83 / 14.8 | (reports meaning) 8.5 | 83 / — | 50 / 50 | 67 / 83 | 17% | 24.1% / 17.0% |
| D1L adaptive exam levels, meaning | 40 (0) | 4.0 / 3.3 | -5.6, 13.3, -22.4..13.7 | 67 / 17.2 | (reports meaning) -2.3 | 67 / — | 50 / 50 | 50 / 50 | 17% | 22.9% / 15.3% |
| D2 IRT, meaning+reading every word | 60 (30) | 5.5 / 5.0 | -1.8, 6.1, -14.1..4.9 | 83 / 14.7 | 6.2, 6.5, -0.4..13.7 | 100 / 16.5 | 50 / 50 | 67 / 100 | 0% | 7.1% / 5.7% |
| D3 IRT, reading after correct meaning | 60 (16) | 5.8 / 4.9 | -3.1, 4.1, -6.8..1.7 | 100 / 12.5 | -0.6, 9.7, -10.9..10.0 | 83 / 14.8 | 50 / 50 | 67 / 100 | 0% | 13.7% / 12.1% |
| D4 IRT, reading on half the words | 60 (20) | 5.7 / 5.1 | -4.1, 5.4, -13.2..2.5 | 83 / 12.1 | 0.2, 6.6, -10.5..7.4 | 100 / 18.6 | 50 / 50 | 67 / 100 | 0% | 13.4% / 10.7% |
| D3S adaptive bands, reading after correct meaning | 60 (14) | 5.8 / 4.9 | 0.2, 2.9, -4.3..3.9 | 100 / 14.1 | 2.3, 6.4, -8.0..9.5 | 100 / 13.0 | 50 / 50 | 67 / 100 | 0% | 9.8% / 9.1% |
| D3L adaptive exam levels, reading after correct meaning | 60 (19) | 5.7 / 4.8 | -2.2, 7.2, -15.0..5.9 | 83 / 17.6 | -7.8, 9.1, -19.5..2.3 | 50 / 15.6 | 50 / 67 | 67 / 83 | 0% | 9.9% / 9.1% |

### ja, English L1, skip-if-unknown 0.7

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 6.2 | -1.3, 2.3, -4.1..2.3 | 100 / 10.0 | (reports meaning) 0.7 | 100 / — | 83 / 83 | 83 / 83 | 0% | 14.2% / 10.2% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.6 | -2.2, 2.8, -5.0..1.2 | 100 / 10.3 | (reports meaning) -0.2 | 100 / — | 83 / 83 | 83 / 83 | 0% | 11.9% / 4.6% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.6 | 1.7, 9.4, -10.1..17.1 | 67 / 11.9 | (reports meaning) 3.7 | 67 / — | 83 / 100 | 83 / 83 | 33% | 13.8% / 9.2% |
| D1L adaptive exam levels, meaning | 40 (0) | 4.0 / 3.6 | -1.0, 5.3, -9.0..6.5 | 100 / 13.7 | (reports meaning) 1.0 | 100 / — | 83 / 100 | 83 / 83 | 0% | 13.2% / 8.8% |
| D2 IRT, meaning+reading every word | 60 (30) | 5.5 / 5.9 | -2.8, 7.6, -12.4..10.2 | 83 / 12.9 | -1.2, 8.0, -13.7..12.7 | 83 / 13.3 | 83 / 83 | 67 / 83 | 0% | 1.9% / 1.9% |
| D3 IRT, reading after correct meaning | 60 (13) | 5.8 / 5.3 | -1.0, 5.2, -9.1..7.1 | 100 / 9.7 | 0.1, 6.4, -8.1..9.7 | 100 / 13.9 | 83 / 100 | 67 / 67 | 0% | 9.6% / 7.4% |
| D4 IRT, reading on half the words | 60 (20) | 5.7 / 5.7 | -0.5, 5.2, -9.4..7.0 | 100 / 10.5 | 4.3, 10.1, -8.9..18.2 | 83 / 17.2 | 83 / 83 | 67 / 67 | 17% | 10.8% / 4.9% |
| D3S adaptive bands, reading after correct meaning | 60 (14) | 5.8 / 5.2 | 0.8, 5.7, -6.8..9.5 | 100 / 11.2 | 1.5, 4.7, -3.8..7.5 | 100 / 10.6 | 83 / 83 | 83 / 83 | 0% | 5.4% / 5.4% |
| D3L adaptive exam levels, reading after correct meaning | 60 (13) | 5.8 / 5.2 | -2.0, 10.2, -16.7..12.7 | 83 / 12.7 | -0.1, 8.5, -10.9..13.4 | 83 / 12.1 | 83 / 83 | 67 / 83 | 0% | 3.7% / 3.7% |

### ja, Chinese L1 (cognates), skip-if-unknown 0.3

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 5.8 | 0.0, 3.2, -3.4..6.4 | 100 / 12.0 | (reports meaning) 17.6 | 17 / — | 100 / 100 | 100 / 100 | 83% | 37.7% / 9.4% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.3 | 2.0, 5.8, -7.5..7.0 | 100 / 12.9 | (reports meaning) 19.5 | 17 / — | 83 / 83 | 83 / 83 | 83% | 45.9% / 11.3% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.3 | -7.9, 8.7, -14.9..1.5 | 100 / 15.0 | (reports meaning) 9.6 | 67 / — | 100 / 100 | 100 / 100 | 33% | 36.6% / 10.6% |
| D1L adaptive exam levels, meaning | 40 (0) | 4.0 / 3.3 | -8.2, 11.2, -29.2..4.9 | 67 / 17.3 | (reports meaning) 9.4 | 33 / — | 83 / 100 | 83 / 100 | 50% | 40.4% / 12.6% |
| D2 IRT, meaning+reading every word | 60 (30) | 5.5 / 5.1 | 4.5, 8.2, -8.2..12.0 | 100 / 14.5 | -0.9, 7.0, -16.5..6.1 | 83 / 9.8 | 67 / 67 | 83 / 83 | 0% | 17.8% / 2.7% |
| D3 IRT, reading after correct meaning | 60 (21) | 5.7 / 5.1 | 4.6, 7.5, -4.4..13.6 | 83 / 12.9 | 0.3, 3.8, -6.7..7.0 | 100 / 9.5 | 83 / 83 | 83 / 83 | 0% | 18.1% / 8.6% |
| D4 IRT, reading on half the words | 60 (20) | 5.7 / 5.0 | 1.7, 4.4, -2.8..10.2 | 100 / 13.2 | 5.2, 5.4, 0.1..13.0 | 83 / 11.2 | 83 / 100 | 83 / 83 | 17% | 28.5% / 10.2% |
| D3S adaptive bands, reading after correct meaning | 60 (18) | 5.7 / 4.9 | -1.8, 12.9, -20.9..18.0 | 50 / 14.1 | 0.5, 10.6, -10.0..20.9 | 83 / 13.5 | 67 / 100 | 83 / 83 | 17% | 17.9% / 12.2% |
| D3L adaptive exam levels, reading after correct meaning | 60 (19) | 5.7 / 5.0 | 3.8, 13.7, -20.8..20.7 | 50 / 16.3 | 8.2, 11.1, -6.3..23.6 | 83 / 16.0 | 83 / 100 | 83 / 100 | 17% | 12.7% / 6.7% |

### ja, Chinese L1 (cognates), skip-if-unknown 0.7

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 6.0 | -0.3, 4.8, -8.1..8.3 | 83 / 10.5 | (reports meaning) 12.0 | 50 / — | 83 / 100 | 83 / 83 | 50% | 18.3% / 2.2% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.4 | 2.7, 3.5, -1.4..6.9 | 83 / 9.5 | (reports meaning) 14.9 | 17 / — | 83 / 83 | 83 / 100 | 83% | 22.1% / 4.4% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.4 | 4.3, 7.9, -6.0..14.2 | 83 / 12.8 | (reports meaning) 16.6 | 50 / — | 83 / 100 | 83 / 83 | 50% | 20.8% / 3.3% |
| D1L adaptive exam levels, meaning | 40 (0) | 4.0 / 3.4 | -1.9, 6.1, -9.6..9.1 | 100 / 16.5 | (reports meaning) 10.3 | 83 / — | 83 / 83 | 100 / 100 | 17% | 16.8% / 3.8% |
| D2 IRT, meaning+reading every word | 60 (30) | 5.5 / 5.3 | 0.7, 3.4, -4.3..7.5 | 100 / 11.8 | -0.4, 4.6, -7.3..5.5 | 83 / 7.9 | 83 / 83 | 67 / 83 | 0% | 1.8% / 0.9% |
| D3 IRT, reading after correct meaning | 60 (22) | 5.7 / 5.2 | 0.9, 6.5, -8.8..10.2 | 100 / 10.7 | -1.3, 7.6, -14.0..9.4 | 67 / 8.6 | 67 / 67 | 50 / 67 | 17% | 5.5% / 3.4% |
| D4 IRT, reading on half the words | 60 (20) | 5.7 / 5.3 | -4.0, 6.6, -10.3..4.4 | 83 / 10.8 | -7.2, 8.4, -16.8..2.3 | 67 / 10.1 | 67 / 67 | 33 / 50 | 0% | 11.4% / 2.7% |
| D3S adaptive bands, reading after correct meaning | 60 (20) | 5.7 / 5.1 | -0.0, 2.6, -2.9..4.1 | 100 / 13.0 | -1.0, 4.8, -7.1..5.8 | 100 / 12.5 | 67 / 67 | 67 / 83 | 0% | 3.5% / 1.4% |
| D3L adaptive exam levels, reading after correct meaning | 60 (23) | 5.7 / 5.1 | 1.8, 5.2, -5.8..6.3 | 100 / 16.9 | 0.5, 2.0, -1.9..3.3 | 100 / 16.9 | 67 / 83 | 83 / 100 | 0% | 2.7% / 0.7% |

## Precision vs number of items (fixed-length snapshots)

Mean 90% half-width and MAE of the meaning count (and of the meaning+reading count for reading designs), % of N, averaged over all populations of the language; coverage in brackets.

### zh

| design | n=20 | n=30 | n=40 | n=50 | n=60 | n=70 | n=90 |
|---|---|---|---|---|---|---|---|
| D0 | m ±20.4 MAE 9.6 (96%) | m ±16.5 MAE 6.9 (96%) | m ±14.1 MAE 7.5 (88%) | m ±12.5 MAE 6.8 (83%) | m ±11.3 MAE 5.9 (83%) | m ±10.5 MAE 5.7 (79%) | — |
| D1 | m ±15.1 MAE 6.2 (96%) | m ±12.6 MAE 4.6 (92%) | m ±11.2 MAE 4.4 (96%) | m ±10.1 MAE 4.2 (100%) | m ±9.3 MAE 3.5 (96%) | m ±8.6 MAE 2.7 (100%) | — |
| D1S | m ±19.1 MAE 8.6 (96%) | m ±15.0 MAE 6.6 (92%) | m ±12.8 MAE 5.6 (88%) | m ±11.3 MAE 5.5 (92%) | m ±10.2 MAE 5.1 (92%) | m ±9.5 MAE 4.9 (92%) | — |
| D1L | m ±28.2 MAE 11.4 (92%) | m ±22.0 MAE 10.7 (92%) | m ±17.8 MAE 9.7 (92%) | m ±15.2 MAE 9.0 (92%) | m ±13.5 MAE 7.9 (92%) | m ±12.1 MAE 6.8 (88%) | — |
| D2 | m ±20.7 MAE 7.6 (100%); m+r ±23.0 MAE 13.3 (88%) | m ±17.8 MAE 7.1 (100%); m+r ±20.9 MAE 12.3 (83%) | m ±16.1 MAE 5.6 (100%); m+r ±19.8 MAE 12.3 (75%) | m ±15.2 MAE 5.5 (100%); m+r ±19.1 MAE 11.6 (83%) | m ±14.1 MAE 5.4 (100%); m+r ±18.4 MAE 11.4 (83%) | m ±13.3 MAE 5.4 (96%); m+r ±18.1 MAE 11.4 (83%) | m ±12.1 MAE 5.2 (83%); m+r ±16.9 MAE 9.9 (88%) |
| D3 | m ±17.7 MAE 9.1 (83%); m+r ±20.6 MAE 9.9 (96%) | m ±15.3 MAE 8.5 (79%); m+r ±19.3 MAE 9.3 (96%) | m ±13.7 MAE 6.7 (88%); m+r ±17.8 MAE 9.8 (88%) | m ±12.5 MAE 6.1 (92%); m+r ±16.2 MAE 9.4 (88%) | m ±11.6 MAE 5.2 (92%); m+r ±15.4 MAE 8.2 (83%) | m ±10.9 MAE 4.9 (88%); m+r ±14.5 MAE 8.4 (83%) | m ±9.9 MAE 5.7 (83%); m+r ±12.6 MAE 7.3 (83%) |
| D4 | m ±18.0 MAE 10.2 (83%); m+r ±26.7 MAE 14.4 (96%) | m ±15.2 MAE 7.7 (88%); m+r ±24.9 MAE 13.0 (92%) | m ±13.5 MAE 6.3 (96%); m+r ±22.6 MAE 11.5 (92%) | m ±12.3 MAE 6.2 (88%); m+r ±21.6 MAE 11.6 (92%) | m ±11.3 MAE 6.2 (88%); m+r ±21.2 MAE 11.3 (92%) | m ±10.6 MAE 5.5 (88%); m+r ±19.3 MAE 9.8 (92%) | m ±9.4 MAE 4.6 (88%); m+r ±17.9 MAE 9.7 (88%) |
| D3S | m ±26.0 MAE 15.5 (79%); m+r ±23.7 MAE 10.5 (88%) | m ±19.4 MAE 7.9 (92%); m+r ±17.4 MAE 6.9 (96%) | m ±16.3 MAE 7.3 (92%); m+r ±14.3 MAE 6.6 (92%) | m ±14.3 MAE 7.8 (88%); m+r ±12.6 MAE 6.6 (92%) | m ±13.2 MAE 6.8 (83%); m+r ±11.5 MAE 5.5 (92%) | m ±12.1 MAE 6.7 (88%); m+r ±10.5 MAE 5.0 (92%) | m ±10.8 MAE 5.0 (92%); m+r ±9.2 MAE 4.0 (92%) |
| D3L | m ±38.5 MAE 17.5 (88%); m+r ±34.2 MAE 12.1 (96%) | m ±28.6 MAE 14.2 (92%); m+r ±24.5 MAE 11.0 (96%) | m ±24.9 MAE 13.2 (88%); m+r ±21.0 MAE 9.2 (96%) | m ±22.5 MAE 9.8 (92%); m+r ±19.1 MAE 8.6 (96%) | m ±19.3 MAE 8.5 (92%); m+r ±16.4 MAE 7.2 (96%) | m ±17.4 MAE 7.2 (96%); m+r ±14.7 MAE 5.8 (100%) | m ±14.9 MAE 5.8 (100%); m+r ±12.4 MAE 5.4 (92%) |

### ja

| design | n=20 | n=30 | n=40 | n=50 | n=60 | n=70 | n=90 |
|---|---|---|---|---|---|---|---|
| D0 | m ±21.8 MAE 9.6 (88%) | m ±17.4 MAE 8.8 (88%) | m ±15.1 MAE 6.5 (88%) | m ±13.5 MAE 6.2 (88%) | m ±12.3 MAE 5.5 (92%) | m ±11.3 MAE 4.7 (88%) | — |
| D1 | m ±15.1 MAE 7.7 (83%) | m ±13.0 MAE 5.4 (92%) | m ±11.3 MAE 5.3 (92%) | m ±10.3 MAE 5.4 (88%) | m ±9.4 MAE 5.2 (83%) | m ±8.8 MAE 5.1 (79%) | — |
| D1S | m ±20.0 MAE 11.6 (88%) | m ±15.9 MAE 8.8 (88%) | m ±13.6 MAE 8.3 (83%) | m ±12.0 MAE 7.6 (79%) | m ±10.9 MAE 6.8 (79%) | m ±10.1 MAE 6.3 (92%) | — |
| D1L | m ±24.4 MAE 13.0 (88%) | m ±19.1 MAE 8.9 (92%) | m ±16.2 MAE 9.0 (83%) | m ±14.1 MAE 8.8 (83%) | m ±12.6 MAE 7.8 (79%) | m ±11.6 MAE 6.6 (88%) | — |
| D2 | m ±20.1 MAE 7.7 (96%); m+r ±16.1 MAE 10.0 (83%) | m ±17.5 MAE 6.2 (100%); m+r ±14.6 MAE 8.0 (96%) | m ±15.8 MAE 6.4 (100%); m+r ±13.1 MAE 7.6 (92%) | m ±14.4 MAE 6.1 (96%); m+r ±12.2 MAE 7.0 (83%) | m ±13.5 MAE 6.3 (92%); m+r ±11.9 MAE 6.5 (88%) | m ±12.8 MAE 6.4 (96%); m+r ±11.5 MAE 6.5 (83%) | m ±11.6 MAE 4.9 (92%); m+r ±11.0 MAE 5.3 (88%) |
| D3 | m ±17.7 MAE 8.6 (92%); m+r ±16.5 MAE 8.2 (96%) | m ±15.4 MAE 5.0 (100%); m+r ±14.4 MAE 7.0 (92%) | m ±13.8 MAE 5.0 (100%); m+r ±13.3 MAE 7.2 (88%) | m ±12.6 MAE 5.0 (100%); m+r ±12.2 MAE 6.7 (88%) | m ±11.5 MAE 5.8 (96%); m+r ±11.7 MAE 6.9 (88%) | m ±10.7 MAE 4.9 (96%); m+r ±11.4 MAE 5.5 (92%) | m ±9.7 MAE 4.0 (92%); m+r ±10.6 MAE 4.9 (96%) |
| D4 | m ±17.9 MAE 8.5 (92%); m+r ±17.9 MAE 10.8 (79%) | m ±15.4 MAE 6.3 (92%); m+r ±16.5 MAE 9.0 (83%) | m ±13.7 MAE 6.1 (96%); m+r ±15.4 MAE 7.9 (83%) | m ±12.7 MAE 6.0 (92%); m+r ±15.0 MAE 7.5 (92%) | m ±11.6 MAE 5.4 (92%); m+r ±14.3 MAE 7.6 (83%) | m ±10.9 MAE 4.5 (100%); m+r ±13.8 MAE 6.9 (83%) | m ±9.7 MAE 4.3 (96%); m+r ±13.1 MAE 6.1 (88%) |
| D3S | m ±25.7 MAE 13.5 (92%); m+r ±24.9 MAE 8.8 (100%) | m ±19.3 MAE 9.5 (96%); m+r ±18.6 MAE 8.1 (88%) | m ±16.2 MAE 7.6 (88%); m+r ±15.6 MAE 7.2 (100%) | m ±14.4 MAE 6.2 (88%); m+r ±13.8 MAE 6.8 (96%) | m ±13.1 MAE 6.0 (88%); m+r ±12.4 MAE 6.6 (96%) | m ±12.0 MAE 5.5 (88%); m+r ±11.4 MAE 5.8 (88%) | m ±10.4 MAE 4.8 (88%); m+r ±9.9 MAE 5.1 (88%) |
| D3L | m ±28.3 MAE 18.2 (79%); m+r ±27.1 MAE 15.6 (83%) | m ±23.2 MAE 15.6 (75%); m+r ±22.1 MAE 14.7 (75%) | m ±19.8 MAE 13.6 (71%); m+r ±18.9 MAE 13.1 (75%) | m ±17.5 MAE 12.3 (71%); m+r ±16.5 MAE 11.8 (79%) | m ±15.9 MAE 9.1 (79%); m+r ±15.1 MAE 7.7 (79%) | m ±14.3 MAE 8.7 (83%); m+r ±13.7 MAE 8.0 (83%) | m ±12.0 MAE 9.1 (67%); m+r ±11.6 MAE 7.5 (83%) |

## Stopping rules (applied to the snapshots; stop at the first checkpoint where every reported 90% half-width <= h x N, after a minimum, else at the cap)

### h = 0.1, min 20, cap 40 (meaning-only) / 60 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.3 | D1 | 39 (36..40) | 17% | 3.3 / 3.4 | 5.9 / 100% | — | 67 |
| zh, English L1 s=0.3 | D1S | 40 (40..40) | 0% | 3.4 / 3.5 | 8.8 / 67% | — | 67 |
| zh, English L1 s=0.3 | D1L | 40 (40..40) | 0% | 3.4 / 3.5 | 7.4 / 100% | — | 67 |
| zh, English L1 s=0.3 | D2 | 60 (60..60) | 0% | 5.3 / 6.0 | 2.9 / 100% | 17.4 / 67% | 50 |
| zh, English L1 s=0.3 | D3 | 60 (60..61) | 0% | 5.1 / 5.5 | 8.8 / 67% | 8.6 / 83% | 67 |
| zh, English L1 s=0.3 | D4 | 60 (60..60) | 0% | 5.2 / 5.6 | 3.1 / 100% | 15.1 / 100% | 50 |
| zh, English L1 s=0.3 | D3S | 60 (60..61) | 0% | 5.1 / 5.4 | 5.5 / 100% | 5.0 / 67% | 67 |
| zh, English L1 s=0.3 | D3L | 60 (60..61) | 0% | 4.9 / 5.2 | 8.0 / 83% | 9.2 / 83% | 83 |
| zh, English L1 s=0.7 | D1 | 37 (25..40) | 17% | 3.3 / 3.7 | 2.2 / 100% | — | 83 |
| zh, English L1 s=0.7 | D1S | 40 (40..40) | 0% | 3.6 / 3.7 | 5.5 / 83% | — | 83 |
| zh, English L1 s=0.7 | D1L | 40 (40..40) | 0% | 3.5 / 3.7 | 7.4 / 100% | — | 83 |
| zh, English L1 s=0.7 | D2 | 60 (60..60) | 0% | 6.2 / 6.9 | 5.8 / 100% | 13.6 / 83% | 100 |
| zh, English L1 s=0.7 | D3 | 60 (60..61) | 0% | 5.4 / 5.7 | 4.0 / 100% | 12.4 / 100% | 83 |
| zh, English L1 s=0.7 | D4 | 60 (60..60) | 0% | 6.0 / 6.6 | 5.1 / 100% | 11.4 / 100% | 83 |
| zh, English L1 s=0.7 | D3S | 58 (52..61) | 17% | 5.3 / 5.6 | 6.3 / 100% | 6.4 / 100% | 83 |
| zh, English L1 s=0.7 | D3L | 60 (60..61) | 0% | 5.0 / 5.2 | 10.1 / 100% | 6.1 / 100% | 83 |
| zh, Japanese L1 (cognates) s=0.3 | D1 | 37 (25..40) | 17% | 3.1 / 3.4 | 3.9 / 100% | — | 67 |
| zh, Japanese L1 (cognates) s=0.3 | D1S | 40 (40..40) | 0% | 3.3 / 3.4 | 3.7 / 100% | — | 100 |
| zh, Japanese L1 (cognates) s=0.3 | D1L | 40 (40..40) | 0% | 3.3 / 3.4 | 10.5 / 83% | — | 67 |
| zh, Japanese L1 (cognates) s=0.3 | D2 | 60 (60..60) | 0% | 5.1 / 5.6 | 9.1 / 100% | 8.1 / 100% | 50 |
| zh, Japanese L1 (cognates) s=0.3 | D3 | 60 (60..61) | 0% | 5.0 / 5.3 | 4.1 / 100% | 8.5 / 67% | 33 |
| zh, Japanese L1 (cognates) s=0.3 | D4 | 60 (60..60) | 0% | 5.1 / 5.3 | 10.7 / 50% | 10.6 / 67% | 33 |
| zh, Japanese L1 (cognates) s=0.3 | D3S | 60 (60..61) | 0% | 5.0 / 5.2 | 6.4 / 83% | 5.7 / 100% | 83 |
| zh, Japanese L1 (cognates) s=0.3 | D3L | 61 (60..61) | 0% | 4.9 / 5.4 | 7.3 / 100% | 7.2 / 100% | 50 |
| zh, Japanese L1 (cognates) s=0.7 | D1 | 40 (40..40) | 0% | 3.5 / 3.6 | 5.3 / 83% | — | 83 |
| zh, Japanese L1 (cognates) s=0.7 | D1S | 40 (40..40) | 0% | 3.5 / 3.6 | 4.4 / 100% | — | 67 |
| zh, Japanese L1 (cognates) s=0.7 | D1L | 40 (40..40) | 0% | 3.5 / 3.6 | 13.7 / 83% | — | 50 |
| zh, Japanese L1 (cognates) s=0.7 | D2 | 60 (60..60) | 0% | 5.8 / 6.3 | 3.8 / 100% | 6.4 / 83% | 83 |
| zh, Japanese L1 (cognates) s=0.7 | D3 | 60 (60..61) | 0% | 5.6 / 6.0 | 3.7 / 100% | 3.4 / 83% | 100 |
| zh, Japanese L1 (cognates) s=0.7 | D4 | 60 (60..60) | 0% | 5.5 / 6.0 | 5.9 / 100% | 8.3 / 100% | 100 |
| zh, Japanese L1 (cognates) s=0.7 | D3S | 60 (60..61) | 0% | 5.6 / 6.1 | 8.8 / 50% | 4.7 / 100% | 100 |
| zh, Japanese L1 (cognates) s=0.7 | D3L | 60 (60..61) | 0% | 5.3 / 5.8 | 8.5 / 83% | 6.3 / 100% | 67 |
| ja, English L1 s=0.3 | D1 | 40 (40..40) | 0% | 3.3 / 3.3 | 9.3 / 83% | — | 100 |
| ja, English L1 s=0.3 | D1S | 40 (40..40) | 0% | 3.3 / 3.4 | 7.3 / 83% | — | 83 |
| ja, English L1 s=0.3 | D1L | 40 (40..40) | 0% | 3.3 / 3.4 | 13.3 / 67% | — | 50 |
| ja, English L1 s=0.3 | D2 | 60 (60..60) | 0% | 5.0 / 5.4 | 6.1 / 83% | 6.5 / 100% | 100 |
| ja, English L1 s=0.3 | D3 | 60 (60..61) | 0% | 4.9 / 5.1 | 4.1 / 100% | 9.7 / 83% | 100 |
| ja, English L1 s=0.3 | D4 | 60 (60..60) | 0% | 5.1 / 5.3 | 5.4 / 83% | 6.6 / 100% | 100 |
| ja, English L1 s=0.3 | D3S | 60 (60..61) | 0% | 4.9 / 5.1 | 2.9 / 100% | 6.4 / 100% | 100 |
| ja, English L1 s=0.3 | D3L | 60 (60..61) | 0% | 4.8 / 5.0 | 7.2 / 83% | 9.1 / 50% | 83 |
| ja, English L1 s=0.7 | D1 | 38 (29..40) | 17% | 3.3 / 3.6 | 2.9 / 100% | — | 83 |
| ja, English L1 s=0.7 | D1S | 39 (36..40) | 17% | 3.5 / 3.7 | 9.2 / 67% | — | 83 |
| ja, English L1 s=0.7 | D1L | 40 (40..40) | 0% | 3.6 / 3.8 | 5.3 / 100% | — | 83 |
| ja, English L1 s=0.7 | D2 | 60 (60..60) | 0% | 5.9 / 6.9 | 7.6 / 83% | 8.0 / 83% | 83 |
| ja, English L1 s=0.7 | D3 | 59 (52..61) | 17% | 5.2 / 5.6 | 5.1 / 100% | 6.6 / 100% | 67 |
| ja, English L1 s=0.7 | D4 | 60 (60..60) | 0% | 5.7 / 6.5 | 5.2 / 100% | 10.1 / 83% | 67 |
| ja, English L1 s=0.7 | D3S | 57 (45..61) | 17% | 4.9 / 5.4 | 6.0 / 100% | 5.6 / 100% | 83 |
| ja, English L1 s=0.7 | D3L | 58 (49..61) | 17% | 5.0 / 5.5 | 10.3 / 83% | 8.8 / 83% | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D1 | 40 (40..40) | 0% | 3.3 / 3.4 | 5.8 / 100% | — | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D1S | 40 (40..40) | 0% | 3.3 / 3.4 | 8.7 / 100% | — | 100 |
| ja, Chinese L1 (cognates) s=0.3 | D1L | 40 (40..40) | 0% | 3.3 / 3.4 | 11.2 / 67% | — | 100 |
| ja, Chinese L1 (cognates) s=0.3 | D2 | 60 (60..60) | 0% | 5.1 / 5.3 | 8.2 / 100% | 7.0 / 83% | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D3 | 60 (60..61) | 0% | 5.1 / 5.3 | 7.5 / 83% | 3.8 / 100% | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D4 | 60 (60..60) | 0% | 5.0 / 5.3 | 4.4 / 100% | 5.4 / 83% | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D3S | 60 (60..61) | 0% | 4.9 / 5.1 | 12.9 / 50% | 10.6 / 83% | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D3L | 60 (60..60) | 0% | 5.0 / 5.3 | 13.7 / 50% | 11.1 / 83% | 100 |
| ja, Chinese L1 (cognates) s=0.7 | D1 | 34 (22..40) | 50% | 2.9 / 3.5 | 2.5 / 100% | — | 100 |
| ja, Chinese L1 (cognates) s=0.7 | D1S | 40 (40..40) | 0% | 3.4 / 3.5 | 7.9 / 83% | — | 83 |
| ja, Chinese L1 (cognates) s=0.7 | D1L | 40 (40..40) | 0% | 3.4 / 3.5 | 6.1 / 100% | — | 100 |
| ja, Chinese L1 (cognates) s=0.7 | D2 | 60 (60..60) | 0% | 5.3 / 5.9 | 3.4 / 100% | 4.6 / 83% | 83 |
| ja, Chinese L1 (cognates) s=0.7 | D3 | 58 (49..61) | 17% | 4.9 / 5.4 | 6.4 / 100% | 6.9 / 67% | 67 |
| ja, Chinese L1 (cognates) s=0.7 | D4 | 60 (60..60) | 0% | 5.3 / 5.8 | 6.6 / 83% | 8.4 / 67% | 50 |
| ja, Chinese L1 (cognates) s=0.7 | D3S | 60 (60..61) | 0% | 5.1 / 5.6 | 2.6 / 100% | 4.8 / 100% | 83 |
| ja, Chinese L1 (cognates) s=0.7 | D3L | 60 (60..61) | 0% | 5.1 / 5.5 | 5.2 / 100% | 2.0 / 100% | 100 |

### h = 0.12, min 20, cap 40 (meaning-only) / 60 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.3 | D1 | 36 (28..40) | 50% | 3.0 / 3.4 | 5.8 / 100% | — | 67 |
| zh, English L1 s=0.3 | D1S | 39 (36..40) | 17% | 3.3 / 3.5 | 8.5 / 83% | — | 67 |
| zh, English L1 s=0.3 | D1L | 40 (40..40) | 0% | 3.4 / 3.5 | 7.4 / 100% | — | 67 |
| zh, English L1 s=0.3 | D2 | 60 (60..60) | 0% | 5.3 / 6.0 | 2.9 / 100% | 17.4 / 67% | 50 |
| zh, English L1 s=0.3 | D3 | 59 (52..61) | 17% | 5.0 / 5.4 | 8.7 / 67% | 8.8 / 83% | 67 |
| zh, English L1 s=0.3 | D4 | 60 (60..60) | 0% | 5.2 / 5.6 | 3.1 / 100% | 15.1 / 100% | 50 |
| zh, English L1 s=0.3 | D3S | 54 (41..61) | 33% | 4.5 / 5.0 | 6.1 / 100% | 4.9 / 83% | 67 |
| zh, English L1 s=0.3 | D3L | 60 (60..61) | 0% | 4.9 / 5.2 | 8.0 / 83% | 9.2 / 83% | 83 |
| zh, English L1 s=0.7 | D1 | 33 (22..40) | 67% | 3.0 / 3.5 | 2.4 / 100% | — | 83 |
| zh, English L1 s=0.7 | D1S | 38 (31..40) | 33% | 3.3 / 3.6 | 5.4 / 83% | — | 83 |
| zh, English L1 s=0.7 | D1L | 38 (31..40) | 33% | 3.3 / 3.5 | 7.0 / 100% | — | 83 |
| zh, English L1 s=0.7 | D2 | 60 (60..60) | 0% | 6.2 / 6.9 | 5.8 / 100% | 13.6 / 83% | 100 |
| zh, English L1 s=0.7 | D3 | 60 (60..61) | 0% | 5.4 / 5.7 | 4.0 / 100% | 12.4 / 100% | 83 |
| zh, English L1 s=0.7 | D4 | 60 (60..60) | 0% | 6.0 / 6.6 | 5.1 / 100% | 11.4 / 100% | 83 |
| zh, English L1 s=0.7 | D3S | 54 (41..61) | 33% | 4.8 / 5.6 | 6.1 / 100% | 6.0 / 100% | 83 |
| zh, English L1 s=0.7 | D3L | 60 (60..61) | 0% | 5.0 / 5.2 | 10.1 / 100% | 6.1 / 100% | 83 |
| zh, Japanese L1 (cognates) s=0.3 | D1 | 35 (24..40) | 50% | 2.9 / 3.4 | 3.9 / 100% | — | 67 |
| zh, Japanese L1 (cognates) s=0.3 | D1S | 40 (40..40) | 0% | 3.3 / 3.4 | 3.7 / 100% | — | 100 |
| zh, Japanese L1 (cognates) s=0.3 | D1L | 40 (40..40) | 0% | 3.3 / 3.4 | 10.5 / 83% | — | 67 |
| zh, Japanese L1 (cognates) s=0.3 | D2 | 58 (50..60) | 17% | 4.9 / 5.6 | 8.7 / 100% | 7.4 / 100% | 50 |
| zh, Japanese L1 (cognates) s=0.3 | D3 | 59 (53..61) | 17% | 4.9 / 5.3 | 4.1 / 100% | 9.0 / 67% | 33 |
| zh, Japanese L1 (cognates) s=0.3 | D4 | 60 (60..60) | 0% | 5.1 / 5.3 | 10.7 / 50% | 10.6 / 67% | 33 |
| zh, Japanese L1 (cognates) s=0.3 | D3S | 60 (60..61) | 0% | 5.0 / 5.2 | 6.4 / 83% | 5.7 / 100% | 83 |
| zh, Japanese L1 (cognates) s=0.3 | D3L | 61 (60..61) | 0% | 4.9 / 5.4 | 7.3 / 100% | 7.2 / 100% | 50 |
| zh, Japanese L1 (cognates) s=0.7 | D1 | 36 (26..40) | 33% | 3.1 / 3.6 | 5.8 / 83% | — | 83 |
| zh, Japanese L1 (cognates) s=0.7 | D1S | 40 (40..40) | 0% | 3.5 / 3.6 | 4.4 / 100% | — | 67 |
| zh, Japanese L1 (cognates) s=0.7 | D1L | 40 (40..40) | 0% | 3.5 / 3.6 | 13.7 / 83% | — | 50 |
| zh, Japanese L1 (cognates) s=0.7 | D2 | 60 (60..60) | 0% | 5.8 / 6.3 | 3.8 / 100% | 6.4 / 83% | 83 |
| zh, Japanese L1 (cognates) s=0.7 | D3 | 58 (49..61) | 17% | 5.4 / 6.0 | 3.7 / 100% | 4.2 / 83% | 83 |
| zh, Japanese L1 (cognates) s=0.7 | D4 | 60 (60..60) | 0% | 5.5 / 6.0 | 5.9 / 100% | 8.3 / 100% | 100 |
| zh, Japanese L1 (cognates) s=0.7 | D3S | 57 (45..61) | 17% | 5.3 / 6.1 | 10.1 / 50% | 4.3 / 100% | 100 |
| zh, Japanese L1 (cognates) s=0.7 | D3L | 60 (60..61) | 0% | 5.3 / 5.8 | 8.5 / 83% | 6.3 / 100% | 67 |
| ja, English L1 s=0.3 | D1 | 37 (25..40) | 17% | 3.0 / 3.3 | 9.9 / 83% | — | 100 |
| ja, English L1 s=0.3 | D1S | 40 (40..40) | 0% | 3.3 / 3.4 | 7.3 / 83% | — | 83 |
| ja, English L1 s=0.3 | D1L | 40 (40..40) | 0% | 3.3 / 3.4 | 13.3 / 67% | — | 50 |
| ja, English L1 s=0.3 | D2 | 60 (60..60) | 0% | 5.0 / 5.4 | 6.1 / 83% | 6.5 / 100% | 100 |
| ja, English L1 s=0.3 | D3 | 60 (60..61) | 0% | 4.9 / 5.1 | 4.1 / 100% | 9.7 / 83% | 100 |
| ja, English L1 s=0.3 | D4 | 60 (60..60) | 0% | 5.1 / 5.3 | 5.4 / 83% | 6.6 / 100% | 100 |
| ja, English L1 s=0.3 | D3S | 60 (60..61) | 0% | 4.9 / 5.1 | 2.9 / 100% | 6.4 / 100% | 100 |
| ja, English L1 s=0.3 | D3L | 57 (45..61) | 17% | 4.6 / 5.0 | 9.9 / 83% | 10.8 / 50% | 83 |
| ja, English L1 s=0.7 | D1 | 32 (21..40) | 67% | 2.8 / 3.5 | 4.0 / 100% | — | 83 |
| ja, English L1 s=0.7 | D1S | 37 (30..40) | 33% | 3.3 / 3.5 | 9.9 / 67% | — | 83 |
| ja, English L1 s=0.7 | D1L | 39 (36..40) | 17% | 3.5 / 3.7 | 5.0 / 100% | — | 83 |
| ja, English L1 s=0.7 | D2 | 58 (52..60) | 17% | 5.7 / 6.9 | 7.6 / 83% | 7.7 / 83% | 83 |
| ja, English L1 s=0.7 | D3 | 54 (38..61) | 33% | 4.7 / 5.6 | 6.2 / 100% | 6.2 / 100% | 67 |
| ja, English L1 s=0.7 | D4 | 57 (46..60) | 17% | 5.4 / 6.5 | 5.5 / 100% | 9.4 / 83% | 67 |
| ja, English L1 s=0.7 | D3S | 54 (35..61) | 33% | 4.6 / 5.2 | 5.2 / 100% | 5.8 / 100% | 83 |
| ja, English L1 s=0.7 | D3L | 52 (35..61) | 33% | 4.5 / 5.2 | 9.7 / 83% | 8.8 / 83% | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D1 | 40 (40..40) | 0% | 3.3 / 3.4 | 5.8 / 100% | — | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D1S | 40 (40..40) | 0% | 3.3 / 3.4 | 8.7 / 100% | — | 100 |
| ja, Chinese L1 (cognates) s=0.3 | D1L | 40 (40..40) | 0% | 3.3 / 3.4 | 11.2 / 67% | — | 100 |
| ja, Chinese L1 (cognates) s=0.3 | D2 | 60 (60..60) | 0% | 5.1 / 5.3 | 8.2 / 100% | 7.0 / 83% | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D3 | 60 (60..61) | 0% | 5.1 / 5.3 | 7.5 / 83% | 3.8 / 100% | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D4 | 60 (60..60) | 0% | 5.0 / 5.3 | 4.4 / 100% | 5.4 / 83% | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D3S | 60 (60..61) | 0% | 4.9 / 5.1 | 12.9 / 50% | 10.6 / 83% | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D3L | 60 (60..60) | 0% | 5.0 / 5.3 | 13.7 / 50% | 11.1 / 83% | 100 |
| ja, Chinese L1 (cognates) s=0.7 | D1 | 28 (20..40) | 67% | 2.4 / 3.5 | 3.1 / 100% | — | 100 |
| ja, Chinese L1 (cognates) s=0.7 | D1S | 40 (40..40) | 0% | 3.4 / 3.5 | 7.9 / 83% | — | 83 |
| ja, Chinese L1 (cognates) s=0.7 | D1L | 40 (40..40) | 0% | 3.4 / 3.5 | 6.1 / 100% | — | 100 |
| ja, Chinese L1 (cognates) s=0.7 | D2 | 53 (42..60) | 50% | 4.7 / 5.9 | 4.0 / 100% | 4.8 / 83% | 67 |
| ja, Chinese L1 (cognates) s=0.7 | D3 | 47 (32..60) | 67% | 4.0 / 5.3 | 7.0 / 100% | 8.3 / 67% | 50 |
| ja, Chinese L1 (cognates) s=0.7 | D4 | 54 (43..60) | 50% | 4.7 / 5.8 | 5.9 / 100% | 9.0 / 67% | 50 |
| ja, Chinese L1 (cognates) s=0.7 | D3S | 60 (60..61) | 0% | 5.1 / 5.6 | 2.6 / 100% | 4.8 / 100% | 83 |
| ja, Chinese L1 (cognates) s=0.7 | D3L | 60 (60..61) | 0% | 5.1 / 5.5 | 5.2 / 100% | 2.0 / 100% | 100 |

### h = 0.08, min 20, cap 60 (meaning-only) / 90 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.3 | D1 | 58 (49..60) | 17% | 4.8 / 5.1 | 4.2 / 100% | — | 67 |
| zh, English L1 s=0.3 | D1S | 60 (60..60) | 0% | 5.1 / 5.2 | 5.5 / 83% | — | 83 |
| zh, English L1 s=0.3 | D1L | 60 (60..60) | 0% | 5.1 / 5.2 | 8.2 / 100% | — | 83 |
| zh, English L1 s=0.3 | D2 | 90 (90..90) | 0% | 7.8 / 8.8 | 2.1 / 100% | 14.0 / 83% | 50 |
| zh, English L1 s=0.3 | D3 | 90 (90..91) | 0% | 7.5 / 8.1 | 9.1 / 50% | 8.2 / 83% | 50 |
| zh, English L1 s=0.3 | D4 | 90 (90..90) | 0% | 7.9 / 8.6 | 4.3 / 83% | 13.4 / 100% | 67 |
| zh, English L1 s=0.3 | D3S | 90 (90..91) | 0% | 7.6 / 8.1 | 4.4 / 100% | 3.7 / 83% | 67 |
| zh, English L1 s=0.3 | D3L | 90 (90..91) | 0% | 7.3 / 7.8 | 8.0 / 100% | 4.2 / 100% | 83 |
| zh, English L1 s=0.7 | D1 | 56 (41..60) | 17% | 5.0 / 5.6 | 2.2 / 100% | — | 83 |
| zh, English L1 s=0.7 | D1S | 60 (60..60) | 0% | 5.4 / 5.6 | 4.3 / 100% | — | 83 |
| zh, English L1 s=0.7 | D1L | 58 (52..60) | 17% | 5.2 / 5.6 | 6.7 / 100% | — | 83 |
| zh, English L1 s=0.7 | D2 | 90 (90..90) | 0% | 9.5 / 10.4 | 5.0 / 100% | 13.8 / 83% | 83 |
| zh, English L1 s=0.7 | D3 | 89 (82..91) | 17% | 8.1 / 8.6 | 3.9 / 100% | 9.7 / 100% | 83 |
| zh, English L1 s=0.7 | D4 | 90 (90..90) | 0% | 9.0 / 9.8 | 3.5 / 100% | 12.1 / 100% | 83 |
| zh, English L1 s=0.7 | D3S | 88 (82..91) | 17% | 7.9 / 8.2 | 5.3 / 83% | 4.0 / 100% | 83 |
| zh, English L1 s=0.7 | D3L | 90 (90..91) | 0% | 7.6 / 8.0 | 6.7 / 100% | 3.8 / 100% | 83 |
| zh, Japanese L1 (cognates) s=0.3 | D1 | 54 (34..60) | 17% | 4.5 / 5.1 | 3.2 / 100% | — | 67 |
| zh, Japanese L1 (cognates) s=0.3 | D1S | 60 (60..60) | 0% | 5.0 / 5.1 | 5.3 / 100% | — | 67 |
| zh, Japanese L1 (cognates) s=0.3 | D1L | 60 (60..60) | 0% | 5.0 / 5.1 | 7.2 / 83% | — | 50 |
| zh, Japanese L1 (cognates) s=0.3 | D2 | 90 (90..90) | 0% | 7.6 / 8.2 | 11.0 / 50% | 6.1 / 100% | 33 |
| zh, Japanese L1 (cognates) s=0.3 | D3 | 90 (90..91) | 0% | 7.5 / 8.0 | 6.1 / 83% | 7.8 / 67% | 33 |
| zh, Japanese L1 (cognates) s=0.3 | D4 | 90 (90..90) | 0% | 7.6 / 7.9 | 7.9 / 67% | 8.4 / 67% | 33 |
| zh, Japanese L1 (cognates) s=0.3 | D3S | 90 (90..91) | 0% | 7.5 / 8.0 | 4.3 / 83% | 4.9 / 83% | 100 |
| zh, Japanese L1 (cognates) s=0.3 | D3L | 90 (90..91) | 0% | 7.3 / 7.9 | 3.9 / 100% | 8.3 / 83% | 100 |
| zh, Japanese L1 (cognates) s=0.7 | D1 | 60 (60..60) | 0% | 5.2 / 5.4 | 4.3 / 83% | — | 83 |
| zh, Japanese L1 (cognates) s=0.7 | D1S | 60 (60..60) | 0% | 5.2 / 5.3 | 5.3 / 83% | — | 67 |
| zh, Japanese L1 (cognates) s=0.7 | D1L | 60 (60..60) | 0% | 5.2 / 5.4 | 10.3 / 83% | — | 67 |
| zh, Japanese L1 (cognates) s=0.7 | D2 | 90 (90..90) | 0% | 8.8 / 9.5 | 2.6 / 83% | 5.8 / 83% | 83 |
| zh, Japanese L1 (cognates) s=0.7 | D3 | 90 (90..91) | 0% | 8.3 / 8.9 | 3.7 / 100% | 3.5 / 83% | 100 |
| zh, Japanese L1 (cognates) s=0.7 | D4 | 90 (90..90) | 0% | 8.3 / 8.9 | 2.7 / 100% | 5.1 / 83% | 100 |
| zh, Japanese L1 (cognates) s=0.7 | D3S | 90 (90..91) | 0% | 8.3 / 9.1 | 5.9 / 100% | 3.5 / 100% | 100 |
| zh, Japanese L1 (cognates) s=0.7 | D3L | 90 (90..91) | 0% | 8.0 / 8.8 | 4.5 / 100% | 5.3 / 83% | 67 |
| ja, English L1 s=0.3 | D1 | 60 (60..60) | 0% | 4.9 / 5.0 | 8.0 / 67% | — | 100 |
| ja, English L1 s=0.3 | D1S | 60 (60..60) | 0% | 5.0 / 5.1 | 6.1 / 100% | — | 100 |
| ja, English L1 s=0.3 | D1L | 60 (60..60) | 0% | 5.0 / 5.0 | 9.3 / 67% | — | 67 |
| ja, English L1 s=0.3 | D2 | 90 (90..90) | 0% | 7.7 / 8.2 | 6.8 / 83% | 4.5 / 100% | 100 |
| ja, English L1 s=0.3 | D3 | 90 (90..91) | 0% | 7.4 / 7.6 | 5.2 / 100% | 5.1 / 100% | 100 |
| ja, English L1 s=0.3 | D4 | 90 (90..90) | 0% | 7.6 / 7.9 | 5.2 / 83% | 3.6 / 100% | 100 |
| ja, English L1 s=0.3 | D3S | 90 (90..91) | 0% | 7.3 / 7.6 | 4.1 / 100% | 5.4 / 67% | 100 |
| ja, English L1 s=0.3 | D3L | 90 (90..91) | 0% | 7.2 / 7.5 | 8.7 / 83% | 9.8 / 83% | 83 |
| ja, English L1 s=0.7 | D1 | 56 (41..60) | 17% | 5.0 / 5.5 | 4.4 / 100% | — | 83 |
| ja, English L1 s=0.7 | D1S | 58 (49..60) | 17% | 5.1 / 5.5 | 8.4 / 67% | — | 83 |
| ja, English L1 s=0.7 | D1L | 60 (60..60) | 0% | 5.4 / 5.7 | 8.8 / 83% | — | 83 |
| ja, English L1 s=0.7 | D2 | 90 (90..90) | 0% | 8.9 / 10.3 | 6.5 / 83% | 7.0 / 83% | 83 |
| ja, English L1 s=0.7 | D3 | 87 (75..91) | 17% | 7.6 / 8.4 | 2.1 / 100% | 5.3 / 100% | 67 |
| ja, English L1 s=0.7 | D4 | 90 (90..90) | 0% | 8.6 / 9.7 | 3.4 / 100% | 9.4 / 83% | 67 |
| ja, English L1 s=0.7 | D3S | 87 (75..91) | 17% | 7.5 / 8.1 | 2.4 / 100% | 1.4 / 100% | 83 |
| ja, English L1 s=0.7 | D3L | 85 (72..91) | 33% | 7.3 / 7.7 | 8.4 / 67% | 6.6 / 83% | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D1 | 60 (60..60) | 0% | 5.0 / 5.1 | 4.4 / 100% | — | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D1S | 60 (60..60) | 0% | 5.0 / 5.0 | 6.4 / 67% | — | 100 |
| ja, Chinese L1 (cognates) s=0.3 | D1L | 60 (60..60) | 0% | 5.0 / 5.1 | 8.5 / 67% | — | 100 |
| ja, Chinese L1 (cognates) s=0.3 | D2 | 90 (90..90) | 0% | 7.6 / 8.0 | 4.7 / 100% | 5.7 / 83% | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D3 | 90 (90..91) | 0% | 7.6 / 7.7 | 6.2 / 67% | 3.4 / 100% | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D4 | 90 (90..90) | 0% | 7.5 / 7.7 | 4.8 / 100% | 5.0 / 100% | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D3S | 91 (90..91) | 0% | 7.5 / 7.7 | 9.7 / 50% | 7.9 / 83% | 100 |
| ja, Chinese L1 (cognates) s=0.3 | D3L | 90 (90..90) | 0% | 7.4 / 7.8 | 13.8 / 33% | 9.2 / 67% | 100 |
| ja, Chinese L1 (cognates) s=0.7 | D1 | 48 (32..60) | 50% | 4.2 / 5.3 | 3.9 / 83% | — | 100 |
| ja, Chinese L1 (cognates) s=0.7 | D1S | 60 (60..60) | 0% | 5.2 / 5.3 | 6.2 / 83% | — | 83 |
| ja, Chinese L1 (cognates) s=0.7 | D1L | 60 (60..60) | 0% | 5.1 / 5.3 | 4.5 / 100% | — | 100 |
| ja, Chinese L1 (cognates) s=0.7 | D2 | 90 (90..90) | 0% | 8.0 / 8.9 | 1.5 / 100% | 4.0 / 83% | 83 |
| ja, Chinese L1 (cognates) s=0.7 | D3 | 89 (82..91) | 17% | 7.6 / 8.1 | 2.3 / 100% | 6.1 / 83% | 50 |
| ja, Chinese L1 (cognates) s=0.7 | D4 | 90 (90..90) | 0% | 7.9 / 8.6 | 3.8 / 100% | 6.5 / 67% | 50 |
| ja, Chinese L1 (cognates) s=0.7 | D3S | 91 (90..91) | 0% | 7.7 / 8.5 | 2.8 / 100% | 5.3 / 100% | 83 |
| ja, Chinese L1 (cognates) s=0.7 | D3L | 91 (90..91) | 0% | 7.6 / 8.3 | 5.5 / 83% | 4.8 / 100% | 100 |

### h = 0.1, min 20, cap 60 (meaning-only) / 90 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.3 | D1 | 54 (39..60) | 33% | 4.6 / 5.1 | 4.3 / 100% | — | 67 |
| zh, English L1 s=0.3 | D1S | 58 (49..60) | 17% | 4.9 / 5.2 | 5.4 / 83% | — | 83 |
| zh, English L1 s=0.3 | D1L | 60 (60..60) | 0% | 5.1 / 5.2 | 8.2 / 100% | — | 83 |
| zh, English L1 s=0.3 | D2 | 90 (90..90) | 0% | 7.8 / 8.8 | 2.1 / 100% | 14.0 / 83% | 50 |
| zh, English L1 s=0.3 | D3 | 89 (83..91) | 17% | 7.4 / 8.0 | 8.9 / 50% | 8.2 / 83% | 50 |
| zh, English L1 s=0.3 | D4 | 90 (90..90) | 0% | 7.9 / 8.6 | 4.3 / 83% | 13.4 / 100% | 67 |
| zh, English L1 s=0.3 | D3S | 80 (60..91) | 33% | 6.7 / 7.6 | 5.2 / 100% | 3.9 / 67% | 67 |
| zh, English L1 s=0.3 | D3L | 90 (90..91) | 0% | 7.3 / 7.8 | 8.0 / 100% | 4.2 / 100% | 83 |
| zh, English L1 s=0.7 | D1 | 46 (25..60) | 67% | 4.1 / 5.3 | 2.1 / 100% | — | 83 |
| zh, English L1 s=0.7 | D1S | 53 (45..60) | 50% | 4.8 / 5.4 | 4.1 / 100% | — | 83 |
| zh, English L1 s=0.7 | D1L | 53 (40..60) | 33% | 4.7 / 5.3 | 6.2 / 100% | — | 83 |
| zh, English L1 s=0.7 | D2 | 90 (90..90) | 0% | 9.5 / 10.4 | 5.0 / 100% | 13.8 / 83% | 83 |
| zh, English L1 s=0.7 | D3 | 87 (75..91) | 17% | 8.0 / 8.6 | 4.1 / 100% | 9.9 / 100% | 83 |
| zh, English L1 s=0.7 | D4 | 90 (90..90) | 0% | 9.0 / 9.8 | 3.5 / 100% | 12.1 / 100% | 83 |
| zh, English L1 s=0.7 | D3S | 78 (52..91) | 33% | 7.0 / 8.1 | 5.2 / 83% | 4.0 / 100% | 83 |
| zh, English L1 s=0.7 | D3L | 89 (82..91) | 17% | 7.5 / 7.9 | 6.6 / 100% | 4.0 / 100% | 83 |
| zh, Japanese L1 (cognates) s=0.3 | D1 | 51 (26..60) | 33% | 4.3 / 5.1 | 2.9 / 100% | — | 67 |
| zh, Japanese L1 (cognates) s=0.3 | D1S | 60 (60..60) | 0% | 5.0 / 5.1 | 5.3 / 100% | — | 67 |
| zh, Japanese L1 (cognates) s=0.3 | D1L | 60 (60..60) | 0% | 5.0 / 5.1 | 7.2 / 83% | — | 50 |
| zh, Japanese L1 (cognates) s=0.3 | D2 | 88 (82..90) | 17% | 7.5 / 8.2 | 10.9 / 67% | 5.7 / 100% | 33 |
| zh, Japanese L1 (cognates) s=0.3 | D3 | 87 (76..91) | 17% | 7.3 / 8.0 | 6.0 / 83% | 8.2 / 67% | 33 |
| zh, Japanese L1 (cognates) s=0.3 | D4 | 90 (90..90) | 0% | 7.6 / 7.9 | 7.9 / 67% | 8.4 / 67% | 33 |
| zh, Japanese L1 (cognates) s=0.3 | D3S | 90 (90..91) | 0% | 7.5 / 8.0 | 4.3 / 83% | 4.9 / 83% | 100 |
| zh, Japanese L1 (cognates) s=0.3 | D3L | 90 (90..91) | 0% | 7.3 / 7.9 | 3.9 / 100% | 8.3 / 83% | 100 |
| zh, Japanese L1 (cognates) s=0.7 | D1 | 53 (40..60) | 33% | 4.7 / 5.4 | 5.1 / 83% | — | 83 |
| zh, Japanese L1 (cognates) s=0.7 | D1S | 58 (52..60) | 17% | 5.1 / 5.3 | 5.4 / 83% | — | 67 |
| zh, Japanese L1 (cognates) s=0.7 | D1L | 60 (60..60) | 0% | 5.2 / 5.4 | 10.3 / 83% | — | 67 |
| zh, Japanese L1 (cognates) s=0.7 | D2 | 88 (82..90) | 17% | 8.7 / 9.5 | 2.6 / 83% | 5.9 / 83% | 83 |
| zh, Japanese L1 (cognates) s=0.7 | D3 | 85 (72..91) | 33% | 7.9 / 8.9 | 3.7 / 100% | 3.5 / 83% | 100 |
| zh, Japanese L1 (cognates) s=0.7 | D4 | 85 (73..90) | 33% | 7.9 / 8.9 | 3.1 / 100% | 5.0 / 83% | 100 |
| zh, Japanese L1 (cognates) s=0.7 | D3S | 90 (90..91) | 0% | 8.3 / 9.1 | 5.9 / 100% | 3.5 / 100% | 100 |
| zh, Japanese L1 (cognates) s=0.7 | D3L | 90 (90..91) | 0% | 8.0 / 8.8 | 4.5 / 100% | 5.3 / 83% | 67 |
| ja, English L1 s=0.3 | D1 | 60 (60..60) | 0% | 4.9 / 5.0 | 8.0 / 67% | — | 100 |
| ja, English L1 s=0.3 | D1S | 60 (60..60) | 0% | 5.0 / 5.1 | 6.1 / 100% | — | 100 |
| ja, English L1 s=0.3 | D1L | 60 (60..60) | 0% | 5.0 / 5.0 | 9.3 / 67% | — | 67 |
| ja, English L1 s=0.3 | D2 | 90 (90..90) | 0% | 7.7 / 8.2 | 6.8 / 83% | 4.5 / 100% | 100 |
| ja, English L1 s=0.3 | D3 | 90 (90..91) | 0% | 7.4 / 7.6 | 5.2 / 100% | 5.1 / 100% | 100 |
| ja, English L1 s=0.3 | D4 | 90 (90..90) | 0% | 7.6 / 7.9 | 5.2 / 83% | 3.6 / 100% | 100 |
| ja, English L1 s=0.3 | D3S | 90 (90..91) | 0% | 7.3 / 7.6 | 4.1 / 100% | 5.4 / 67% | 100 |
| ja, English L1 s=0.3 | D3L | 90 (90..91) | 0% | 7.2 / 7.5 | 8.7 / 83% | 9.8 / 83% | 83 |
| ja, English L1 s=0.7 | D1 | 46 (29..60) | 67% | 4.1 / 5.3 | 4.2 / 100% | — | 83 |
| ja, English L1 s=0.7 | D1S | 52 (36..60) | 33% | 4.7 / 5.3 | 8.1 / 67% | — | 83 |
| ja, English L1 s=0.7 | D1L | 54 (41..60) | 33% | 4.8 / 5.2 | 8.8 / 83% | — | 83 |
| ja, English L1 s=0.7 | D2 | 88 (82..90) | 17% | 8.8 / 10.3 | 6.6 / 83% | 7.3 / 83% | 83 |
| ja, English L1 s=0.7 | D3 | 80 (55..91) | 33% | 7.1 / 8.4 | 2.3 / 100% | 5.1 / 100% | 67 |
| ja, English L1 s=0.7 | D4 | 85 (68..90) | 17% | 8.1 / 9.7 | 3.5 / 100% | 9.7 / 83% | 67 |
| ja, English L1 s=0.7 | D3S | 75 (48..91) | 67% | 6.4 / 7.5 | 4.4 / 100% | 3.6 / 100% | 83 |
| ja, English L1 s=0.7 | D3L | 78 (49..91) | 33% | 6.6 / 7.7 | 9.4 / 67% | 7.5 / 83% | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D1 | 60 (60..60) | 0% | 5.0 / 5.1 | 4.4 / 100% | — | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D1S | 60 (60..60) | 0% | 5.0 / 5.0 | 6.4 / 67% | — | 100 |
| ja, Chinese L1 (cognates) s=0.3 | D1L | 60 (60..60) | 0% | 5.0 / 5.1 | 8.5 / 67% | — | 100 |
| ja, Chinese L1 (cognates) s=0.3 | D2 | 90 (90..90) | 0% | 7.6 / 8.0 | 4.7 / 100% | 5.7 / 83% | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D3 | 90 (90..91) | 0% | 7.6 / 7.7 | 6.2 / 67% | 3.4 / 100% | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D4 | 90 (90..90) | 0% | 7.5 / 7.7 | 4.8 / 100% | 5.0 / 100% | 83 |
| ja, Chinese L1 (cognates) s=0.3 | D3S | 91 (90..91) | 0% | 7.5 / 7.7 | 9.7 / 50% | 7.9 / 83% | 100 |
| ja, Chinese L1 (cognates) s=0.3 | D3L | 90 (90..90) | 0% | 7.4 / 7.8 | 13.8 / 33% | 9.2 / 67% | 100 |
| ja, Chinese L1 (cognates) s=0.7 | D1 | 44 (22..60) | 50% | 3.8 / 5.3 | 2.8 / 100% | — | 100 |
| ja, Chinese L1 (cognates) s=0.7 | D1S | 60 (60..60) | 0% | 5.2 / 5.3 | 6.2 / 83% | — | 83 |
| ja, Chinese L1 (cognates) s=0.7 | D1L | 60 (60..60) | 0% | 5.1 / 5.3 | 4.5 / 100% | — | 100 |
| ja, Chinese L1 (cognates) s=0.7 | D2 | 78 (60..90) | 50% | 7.0 / 8.9 | 2.0 / 100% | 4.8 / 83% | 83 |
| ja, Chinese L1 (cognates) s=0.7 | D3 | 73 (49..91) | 67% | 6.3 / 8.1 | 3.4 / 100% | 5.9 / 83% | 67 |
| ja, Chinese L1 (cognates) s=0.7 | D4 | 79 (63..90) | 50% | 6.9 / 8.6 | 4.9 / 100% | 7.1 / 67% | 50 |
| ja, Chinese L1 (cognates) s=0.7 | D3S | 91 (90..91) | 0% | 7.7 / 8.5 | 2.8 / 100% | 5.3 / 100% | 83 |
| ja, Chinese L1 (cognates) s=0.7 | D3L | 91 (90..91) | 0% | 7.6 / 8.3 | 5.5 / 83% | 4.8 / 100% | 100 |

## By ability (budget snapshot), all populations of a language pooled

Ability groups by the learner's study frontier tau (Zipf at 50% known): beginner tau >= 5.5, intermediate 4.0-5.5, advanced < 4.0.

| lang | design | group | n learners | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|
| zh | D0 | beginner | 9 | 6.1 / 78% | — | 100 |
| zh | D0 | intermediate | 9 | 6.6 / 67% | — | 56 |
| zh | D0 | advanced | 6 | 3.7 / 100% | — | 67 |
| zh | D1 | beginner | 9 | 4.2 / 100% | — | 100 |
| zh | D1 | intermediate | 9 | 3.6 / 100% | — | 56 |
| zh | D1 | advanced | 6 | 5.7 / 83% | — | 67 |
| zh | D1S | beginner | 9 | 6.6 / 89% | — | 100 |
| zh | D1S | intermediate | 9 | 7.1 / 78% | — | 56 |
| zh | D1S | advanced | 6 | 1.8 / 100% | — | 83 |
| zh | D3 | beginner | 9 | 6.7 / 89% | 7.4 / 78% | 100 |
| zh | D3 | intermediate | 9 | 3.2 / 100% | 8.4 / 100% | 67 |
| zh | D3 | advanced | 6 | 5.7 / 83% | 9.0 / 67% | 33 |
| zh | D3S | beginner | 9 | 8.2 / 78% | 4.2 / 89% | 100 |
| zh | D3S | intermediate | 9 | 8.1 / 78% | 6.9 / 89% | 67 |
| zh | D3S | advanced | 6 | 2.8 / 100% | 5.1 / 100% | 83 |
| zh | D3L | beginner | 9 | 5.9 / 100% | 4.2 / 100% | 100 |
| zh | D3L | intermediate | 9 | 7.8 / 100% | 5.6 / 100% | 56 |
| zh | D3L | advanced | 6 | 13.4 / 67% | 14.0 / 83% | 50 |
| ja | D0 | beginner | 7 | 3.6 / 100% | — | 100 |
| ja | D0 | intermediate | 8 | 4.5 / 88% | — | 100 |
| ja | D0 | advanced | 9 | 5.9 / 78% | — | 78 |
| ja | D1 | beginner | 7 | 4.0 / 100% | — | 100 |
| ja | D1 | intermediate | 8 | 5.4 / 100% | — | 100 |
| ja | D1 | advanced | 9 | 6.3 / 78% | — | 78 |
| ja | D1S | beginner | 7 | 7.1 / 100% | — | 100 |
| ja | D1S | intermediate | 8 | 7.8 / 88% | — | 100 |
| ja | D1S | advanced | 9 | 9.6 / 67% | — | 67 |
| ja | D3 | beginner | 7 | 6.4 / 86% | 5.4 / 100% | 100 |
| ja | D3 | intermediate | 8 | 6.2 / 100% | 7.7 / 75% | 100 |
| ja | D3 | advanced | 9 | 5.1 / 100% | 7.3 / 89% | 44 |
| ja | D3S | beginner | 7 | 10.0 / 71% | 9.6 / 86% | 100 |
| ja | D3S | intermediate | 8 | 5.3 / 88% | 6.2 / 100% | 100 |
| ja | D3S | advanced | 9 | 3.5 / 100% | 4.6 / 100% | 67 |
| ja | D3L | beginner | 7 | 12.2 / 57% | 10.6 / 71% | 100 |
| ja | D3L | intermediate | 8 | 8.0 / 75% | 6.6 / 75% | 100 |
| ja | D3L | advanced | 9 | 7.6 / 100% | 6.4 / 89% | 78 |
