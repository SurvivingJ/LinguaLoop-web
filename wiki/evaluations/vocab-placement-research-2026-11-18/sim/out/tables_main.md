# Simulation tables — run `raw_main.json`

Learners per population: 500. Config: `{"max_m": 70, "max_tot": 90, "designs": "D0,D1,D1S,D1L,D2,D3,D4,D3S,D3L", "pops": "zh:E:0.3,zh:E:0.7,zh:J:0.3,zh:J:0.7,ja:E:0.3,ja:E:0.7,ja:Z:0.3,ja:Z:0.7", "sig_eps": 1.2, "a_med": 1.6, "gamma_max": 1.0, "tau_lo": 2.5, "tau_hi": 7.0, "partial": 0, "seed": 11}`. Runtime 747.1 + 1417.4 s.

All numbers are ESTIMATES from simulation. Errors are in % of the check pool (N words). Intervals are 90%. "e5..e95" is the 90% range of the error across learners.

## Populations (truth)

| population | skip | N | mean known by meaning (% of N) | mean known by meaning+reading (%) | meaning-only words (% of known) | true placement by meaning: share at 0 / at max | by meaning+reading: 0 / max |
|---|---|---|---|---|---|---|---|
| zh, English L1 | 0.3 | 3623 | 37.8 | 33.1 | 12.3 | 43% / 21% | 57% / 14% |
| zh, English L1 | 0.7 | 3623 | 37.3 | 32.6 | 12.4 | 45% / 22% | 58% / 16% |
| zh, Japanese L1 (cognates) | 0.3 | 3623 | 64.3 | 36.0 | 44.1 | 32% / 37% | 57% / 17% |
| zh, Japanese L1 (cognates) | 0.7 | 3623 | 62.4 | 33.2 | 46.9 | 35% / 33% | 60% / 12% |
| ja, English L1 | 0.3 | 3175 | 40.8 | 38.8 | 4.9 | 59% / 16% | 65% / 12% |
| ja, English L1 | 0.7 | 3175 | 39.4 | 37.5 | 4.9 | 63% / 18% | 68% / 14% |
| ja, Chinese L1 (cognates) | 0.3 | 3175 | 59.9 | 44.0 | 26.6 | 56% / 26% | 69% / 14% |
| ja, Chinese L1 (cognates) | 0.7 | 3175 | 60.9 | 45.5 | 25.3 | 52% / 29% | 67% / 14% |

## At a fixed budget (D0 70, meaning-only 40, with readings 60 items)

### zh, English L1, skip-if-unknown 0.3

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 5.9 | -0.6, 5.6, -11.1..11.0 | 91 / 11.1 | (reports meaning) 4.0 | 83 / — | 61 / 71 | 74 / 84 | 16% | 29.4% / 20.0% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.4 | 2.0, 5.9, -10.9..13.2 | 90 / 11.5 | (reports meaning) 6.7 | 77 / — | 57 / 65 | 71 / 77 | 23% | 30.7% / 18.7% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.4 | -1.3, 7.1, -16.2..13.2 | 87 / 13.5 | (reports meaning) 3.3 | 86 / — | 62 / 71 | 69 / 80 | 12% | 31.8% / 21.8% |
| D1L adaptive exam levels, meaning | 40 (0) | 4.0 / 3.4 | -1.7, 9.8, -20.8..19.2 | 88 / 18.3 | (reports meaning) 2.9 | 88 / — | 63 / 82 | 58 / 74 | 9% | 22.0% / 12.6% |
| D2 IRT, meaning+reading every word | 60 (30) | 5.5 / 5.1 | 2.5, 6.7, -11.7..15.0 | 90 / 13.1 | 0.5, 5.2, -11.7..9.9 | 96 / 12.3 | 56 / 63 | 63 / 68 | 1% | 8.9% / 6.4% |
| D3 IRT, reading after correct meaning | 60 (20) | 5.7 / 4.9 | 2.1, 5.5, -9.2..13.0 | 91 / 11.6 | 0.6, 4.5, -10.0..9.1 | 97 / 11.2 | 58 / 64 | 64 / 69 | 2% | 10.5% / 7.7% |
| D4 IRT, reading on half the words | 60 (20) | 5.7 / 5.0 | 2.5, 5.6, -8.6..13.0 | 91 / 11.6 | 0.3, 5.3, -12.6..10.4 | 93 / 11.7 | 58 / 67 | 61 / 68 | 3% | 21.4% / 13.2% |
| D3S adaptive bands, reading after correct meaning | 60 (19) | 5.7 / 4.9 | -0.1, 6.8, -14.1..14.6 | 90 / 13.6 | 0.9, 5.5, -10.2..12.5 | 91 / 11.4 | 61 / 72 | 69 / 80 | 5% | 11.2% / 8.7% |
| D3L adaptive exam levels, reading after correct meaning | 60 (22) | 5.7 / 4.9 | -2.5, 10.4, -24.2..19.2 | 88 / 19.4 | -0.1, 7.5, -15.2..16.6 | 91 / 16.3 | 60 / 84 | 68 / 84 | 4% | 7.1% / 4.9% |
| D2i D2 with first m+r model (superseded) | 60 (30) | 5.5 / 5.2 | -0.3, 7.3, -15.7..13.9 | 89 / 14.1 | 7.6, 11.6, -12.6..26.6 | 93 / 22.7 | 53 / 60 | 60 / 66 | 3% | 12.6% / 9.9% |
| D3i D3 with first m+r model (superseded) | 60 (19) | 5.7 / 5.0 | 0.8, 6.3, -12.4..12.9 | 89 / 12.0 | 8.7, 12.3, -11.5..27.7 | 89 / 21.2 | 55 / 64 | 60 / 67 | 6% | 12.9% / 9.9% |
| D4i D4 with first m+r model (superseded) | 60 (20) | 5.7 / 5.1 | 1.6, 6.2, -11.6..13.4 | 89 / 11.7 | 7.1, 12.3, -15.3..27.6 | 95 / 24.1 | 56 / 64 | 59 / 63 | 2% | 22.0% / 13.2% |

### zh, English L1, skip-if-unknown 0.7

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 6.2 | 0.2, 4.8, -9.9..10.0 | 90 / 9.7 | (reports meaning) 4.8 | 78 / — | 64 / 74 | 74 / 85 | 21% | 20.5% / 9.9% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.5 | 0.9, 4.9, -10.6..11.5 | 90 / 10.4 | (reports meaning) 5.5 | 78 / — | 60 / 66 | 71 / 78 | 21% | 23.0% / 9.3% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.5 | -0.7, 5.8, -12.1..11.7 | 90 / 11.9 | (reports meaning) 3.9 | 85 / — | 66 / 75 | 72 / 82 | 13% | 21.6% / 10.2% |
| D1L adaptive exam levels, meaning | 40 (0) | 4.0 / 3.5 | -2.0, 8.4, -17.7..16.3 | 90 / 16.1 | (reports meaning) 2.6 | 89 / — | 66 / 85 | 60 / 76 | 8% | 16.2% / 5.6% |
| D2 IRT, meaning+reading every word | 60 (30) | 5.5 / 5.6 | 1.5, 5.4, -10.4..11.2 | 96 / 11.8 | -0.1, 4.9, -10.6..8.9 | 96 / 11.1 | 58 / 68 | 63 / 69 | 1% | 3.8% / 2.4% |
| D3 IRT, reading after correct meaning | 60 (18) | 5.7 / 5.2 | 1.3, 4.6, -8.4..10.6 | 92 / 10.3 | 0.2, 3.9, -8.9..8.3 | 96 / 9.9 | 59 / 66 | 64 / 69 | 2% | 3.7% / 2.4% |
| D4 IRT, reading on half the words | 60 (20) | 5.7 / 5.5 | 1.2, 4.7, -8.2..10.4 | 93 / 10.4 | -0.5, 4.4, -11.5..7.2 | 95 / 10.5 | 60 / 68 | 63 / 68 | 1% | 14.3% / 6.4% |
| D3S adaptive bands, reading after correct meaning | 60 (17) | 5.7 / 5.2 | -0.8, 5.6, -11.6..10.5 | 91 / 11.7 | 0.1, 4.9, -10.0..11.1 | 92 / 10.4 | 64 / 71 | 70 / 80 | 4% | 4.5% / 2.9% |
| D3L adaptive exam levels, reading after correct meaning | 60 (21) | 5.7 / 5.1 | -1.4, 8.6, -18.4..18.7 | 88 / 16.8 | -0.3, 6.6, -15.0..16.3 | 93 / 15.1 | 66 / 83 | 66 / 81 | 2% | 2.5% / 1.5% |
| D2i D2 with first m+r model (superseded) | 60 (30) | 5.5 / 5.9 | -1.3, 6.9, -16.4..11.8 | 90 / 14.3 | 7.4, 11.8, -12.1..26.8 | 93 / 23.1 | 54 / 61 | 61 / 67 | 3% | 4.9% / 3.5% |
| D3i D3 with first m+r model (superseded) | 60 (15) | 5.8 / 5.3 | -0.3, 5.5, -12.4..11.0 | 88 / 11.0 | 8.3, 12.2, -11.5..28.0 | 91 / 20.8 | 56 / 64 | 61 / 66 | 4% | 5.2% / 3.7% |
| D4i D4 with first m+r model (superseded) | 60 (20) | 5.7 / 5.7 | 1.1, 5.1, -10.7..11.0 | 92 / 10.6 | 6.8, 12.8, -16.7..27.0 | 92 / 24.7 | 60 / 66 | 62 / 65 | 2% | 14.5% / 5.5% |

### zh, Japanese L1 (cognates), skip-if-unknown 0.3

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 5.9 | -0.1, 5.2, -11.2..10.7 | 91 / 11.2 | (reports meaning) 28.3 | 5 / — | 64 / 72 | 65 / 74 | 95% | 46.5% / 8.2% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.4 | -1.5, 5.9, -13.3..10.7 | 91 / 11.8 | (reports meaning) 26.9 | 9 / — | 59 / 69 | 67 / 76 | 91% | 52.5% / 9.8% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.4 | 1.4, 6.8, -11.9..15.0 | 89 / 13.8 | (reports meaning) 29.8 | 9 / — | 61 / 71 | 59 / 69 | 91% | 49.6% / 9.0% |
| D1L adaptive exam levels, meaning | 40 (0) | 4.0 / 3.4 | -1.8, 10.5, -23.9..19.6 | 85 / 19.5 | (reports meaning) 26.5 | 32 / — | 62 / 77 | 48 / 59 | 68% | 35.4% / 5.9% |
| D2 IRT, meaning+reading every word | 60 (30) | 5.5 / 5.1 | -3.4, 6.7, -18.2..9.2 | 92 / 13.7 | 0.7, 5.5, -11.1..12.9 | 95 / 13.0 | 59 / 68 | 65 / 70 | 4% | 15.8% / 4.5% |
| D3 IRT, reading after correct meaning | 60 (24) | 5.6 / 5.1 | -2.4, 6.1, -14.3..10.1 | 91 / 12.7 | 0.6, 5.3, -9.7..10.9 | 95 / 12.2 | 60 / 66 | 64 / 69 | 2% | 16.9% / 4.4% |
| D4 IRT, reading on half the words | 60 (20) | 5.7 / 5.1 | -2.3, 6.2, -14.5..9.7 | 89 / 12.1 | 1.1, 6.8, -13.0..15.8 | 91 / 14.2 | 57 / 67 | 64 / 68 | 6% | 38.9% / 7.4% |
| D3S adaptive bands, reading after correct meaning | 60 (25) | 5.6 / 5.1 | 0.5, 7.3, -15.1..15.2 | 89 / 14.8 | 0.7, 6.7, -12.2..14.1 | 90 / 13.5 | 59 / 71 | 71 / 80 | 5% | 16.6% / 4.2% |
| D3L adaptive exam levels, reading after correct meaning | 60 (26) | 5.6 / 5.0 | -0.1, 10.8, -22.6..21.3 | 89 / 21.5 | 0.1, 9.7, -19.2..19.9 | 89 / 19.1 | 62 / 78 | 63 / 78 | 4% | 10.6% / 2.7% |
| D2i D2 with first m+r model (superseded) | 60 (30) | 5.5 / 5.1 | -3.8, 7.0, -16.5..9.1 | 91 / 13.8 | -2.2, 7.1, -17.0..11.2 | 82 / 11.9 | 56 / 65 | 60 / 63 | 2% | 15.0% / 4.0% |
| D3i D3 with first m+r model (superseded) | 60 (25) | 5.6 / 5.1 | -2.2, 6.3, -14.4..10.5 | 90 / 12.7 | -1.6, 6.4, -15.5..11.4 | 82 / 10.9 | 59 / 67 | 60 / 64 | 5% | 15.6% / 4.1% |
| D4i D4 with first m+r model (superseded) | 60 (20) | 5.7 / 5.1 | -1.8, 5.9, -14.2..10.0 | 89 / 12.0 | -0.6, 7.8, -16.2..14.6 | 85 / 14.2 | 60 / 68 | 59 / 63 | 5% | 38.2% / 7.2% |

### zh, Japanese L1 (cognates), skip-if-unknown 0.7

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 6.1 | -0.3, 4.9, -11.1..9.3 | 91 / 10.6 | (reports meaning) 29.0 | 3 / — | 63 / 71 | 66 / 78 | 97% | 46.3% / 4.0% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.5 | -2.0, 5.6, -13.2..9.4 | 90 / 11.4 | (reports meaning) 27.3 | 8 / — | 58 / 65 | 69 / 80 | 92% | 53.0% / 5.0% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.5 | 0.3, 6.4, -13.6..13.3 | 90 / 13.2 | (reports meaning) 29.6 | 7 / — | 61 / 70 | 60 / 70 | 93% | 49.1% / 4.3% |
| D1L adaptive exam levels, meaning | 40 (0) | 4.0 / 3.4 | -0.3, 9.3, -21.3..17.6 | 88 / 18.6 | (reports meaning) 28.9 | 23 / — | 63 / 78 | 46 / 59 | 77% | 35.5% / 2.8% |
| D2 IRT, meaning+reading every word | 60 (30) | 5.5 / 5.7 | -2.9, 6.5, -15.0..10.0 | 88 / 13.0 | -0.6, 5.3, -10.9..9.8 | 94 / 11.6 | 55 / 62 | 64 / 70 | 2% | 8.1% / 1.7% |
| D3 IRT, reading after correct meaning | 60 (23) | 5.7 / 5.5 | -2.3, 5.9, -13.7..9.7 | 90 / 11.9 | -0.4, 5.0, -10.5..10.1 | 93 / 10.8 | 56 / 62 | 64 / 70 | 4% | 8.1% / 1.6% |
| D4 IRT, reading on half the words | 60 (20) | 5.7 / 5.6 | -1.8, 5.7, -12.3..10.0 | 92 / 11.4 | 0.7, 6.1, -11.6..13.1 | 93 / 13.0 | 57 / 64 | 65 / 69 | 4% | 38.2% / 3.8% |
| D3S adaptive bands, reading after correct meaning | 60 (23) | 5.6 / 5.5 | -0.5, 6.6, -13.7..13.1 | 90 / 13.8 | -0.6, 5.7, -12.0..11.2 | 91 / 12.2 | 60 / 69 | 73 / 81 | 2% | 8.3% / 1.6% |
| D3L adaptive exam levels, reading after correct meaning | 60 (25) | 5.6 / 5.3 | -2.5, 10.7, -24.5..17.9 | 86 / 20.1 | -0.8, 8.4, -18.6..19.5 | 91 / 16.9 | 58 / 74 | 64 / 79 | 2% | 4.4% / 1.1% |
| D2i D2 with first m+r model (superseded) | 60 (30) | 5.5 / 5.7 | -2.8, 6.4, -15.2..10.2 | 91 / 13.1 | -2.5, 6.3, -15.3..8.5 | 79 / 9.9 | 57 / 64 | 62 / 66 | 3% | 7.7% / 1.9% |
| D3i D3 with first m+r model (superseded) | 60 (23) | 5.6 / 5.5 | -2.0, 5.8, -12.9..10.0 | 90 / 11.9 | -2.6, 6.2, -15.4..9.5 | 75 / 9.1 | 57 / 66 | 62 / 65 | 6% | 7.4% / 1.5% |
| D4i D4 with first m+r model (superseded) | 60 (20) | 5.7 / 5.5 | -1.5, 5.7, -13.1..10.0 | 90 / 11.4 | -0.6, 6.4, -15.8..12.2 | 86 / 12.2 | 58 / 64 | 64 / 68 | 4% | 36.6% / 3.7% |

### ja, English L1, skip-if-unknown 0.3

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 5.9 | 0.4, 5.6, -10.5..12.3 | 91 / 11.6 | (reports meaning) 2.4 | 89 / — | 70 / 77 | 76 / 82 | 9% | 21.0% / 17.2% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.4 | -2.1, 5.4, -12.7..8.6 | 92 / 11.5 | (reports meaning) -0.1 | 92 / — | 67 / 73 | 71 / 79 | 4% | 24.2% / 18.4% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.4 | -0.7, 7.8, -16.7..14.7 | 84 / 13.8 | (reports meaning) 1.3 | 84 / — | 72 / 80 | 75 / 84 | 10% | 24.0% / 19.7% |
| D1L adaptive exam levels, meaning | 40 (0) | 4.0 / 3.4 | -1.7, 9.3, -20.3..17.3 | 85 / 16.2 | (reports meaning) 0.3 | 87 / — | 68 / 83 | 67 / 82 | 7% | 19.7% / 15.3% |
| D2 IRT, meaning+reading every word | 60 (30) | 5.5 / 5.1 | -1.2, 5.4, -12.9..9.9 | 94 / 12.9 | -3.4, 5.4, -14.4..5.8 | 91 / 12.2 | 65 / 74 | 67 / 71 | 0% | 7.4% / 6.0% |
| D3 IRT, reading after correct meaning | 60 (17) | 5.7 / 4.9 | -2.0, 5.2, -12.3..8.6 | 91 / 11.1 | -3.9, 5.5, -13.8..5.6 | 88 / 10.7 | 69 / 75 | 68 / 73 | 0% | 11.0% / 9.7% |
| D4 IRT, reading on half the words | 60 (20) | 5.7 / 5.1 | -2.2, 5.1, -12.7..7.0 | 93 / 11.6 | -4.5, 5.8, -14.3..4.2 | 89 / 11.2 | 67 / 73 | 66 / 71 | 0% | 16.1% / 12.6% |
| D3S adaptive bands, reading after correct meaning | 60 (15) | 5.8 / 4.9 | -0.7, 6.7, -13.5..12.7 | 90 / 13.1 | 0.5, 5.9, -10.8..13.1 | 90 / 11.9 | 71 / 80 | 75 / 84 | 5% | 13.2% / 12.5% |
| D3L adaptive exam levels, reading after correct meaning | 60 (17) | 5.7 / 4.9 | -0.9, 8.7, -17.0..16.2 | 86 / 15.7 | -0.7, 7.5, -16.0..15.0 | 83 / 14.3 | 70 / 86 | 72 / 86 | 6% | 10.3% / 9.5% |
| D2i D2 with first m+r model (superseded) | 60 (30) | 5.5 / 5.2 | -3.3, 6.8, -16.2..9.7 | 89 / 13.6 | 1.3, 7.2, -13.0..14.5 | 92 / 15.9 | 65 / 70 | 66 / 71 | 2% | 9.3% / 7.6% |
| D3i D3 with first m+r model (superseded) | 60 (15) | 5.8 / 5.0 | -2.1, 5.4, -12.0..8.7 | 90 / 11.2 | 3.0, 7.1, -10.2..15.3 | 94 / 15.6 | 68 / 74 | 68 / 73 | 2% | 12.9% / 11.8% |
| D4i D4 with first m+r model (superseded) | 60 (20) | 5.7 / 5.1 | -2.4, 5.7, -13.2..8.9 | 90 / 11.6 | 1.0, 7.4, -13.3..14.4 | 94 / 16.8 | 66 / 73 | 66 / 70 | 1% | 17.4% / 12.9% |

### ja, English L1, skip-if-unknown 0.7

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 6.2 | -0.2, 4.8, -10.3..10.1 | 90 / 10.2 | (reports meaning) 1.7 | 88 / — | 77 / 83 | 80 / 89 | 9% | 12.8% / 8.5% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.5 | -2.7, 4.9, -12.0..6.6 | 91 / 10.2 | (reports meaning) -0.8 | 93 / — | 71 / 77 | 74 / 81 | 2% | 16.0% / 10.1% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.5 | -0.9, 6.4, -13.8..11.9 | 87 / 12.3 | (reports meaning) 1.0 | 88 / — | 76 / 85 | 77 / 88 | 8% | 14.1% / 10.2% |
| D1L adaptive exam levels, meaning | 40 (0) | 4.0 / 3.5 | -1.9, 7.6, -17.1..13.9 | 85 / 14.0 | (reports meaning) -0.0 | 86 / — | 78 / 91 | 74 / 89 | 7% | 12.7% / 7.7% |
| D2 IRT, meaning+reading every word | 60 (30) | 5.5 / 5.7 | -2.5, 5.0, -10.9..7.5 | 94 / 11.5 | -4.0, 5.3, -12.3..4.7 | 91 / 10.9 | 72 / 76 | 72 / 76 | 0% | 2.6% / 1.8% |
| D3 IRT, reading after correct meaning | 60 (14) | 5.8 / 5.2 | -3.0, 5.3, -11.9..7.4 | 86 / 9.7 | -4.4, 5.7, -12.9..4.6 | 82 / 9.4 | 71 / 78 | 71 / 75 | 0% | 5.1% / 4.5% |
| D4 IRT, reading on half the words | 60 (20) | 5.7 / 5.6 | -2.6, 4.8, -11.4..6.7 | 89 / 10.1 | -4.4, 5.5, -13.2..4.1 | 84 / 9.9 | 72 / 77 | 72 / 76 | 0% | 10.3% / 6.4% |
| D3S adaptive bands, reading after correct meaning | 60 (13) | 5.8 / 5.2 | -1.0, 5.4, -11.5..10.1 | 88 / 11.4 | -0.4, 5.0, -10.6..9.8 | 89 / 10.6 | 78 / 85 | 79 / 85 | 3% | 5.8% / 5.5% |
| D3L adaptive exam levels, reading after correct meaning | 60 (15) | 5.8 / 5.1 | -2.3, 7.2, -16.9..12.2 | 84 / 13.4 | -1.9, 6.7, -15.4..13.3 | 85 / 12.5 | 75 / 90 | 76 / 89 | 3% | 4.3% / 3.9% |
| D2i D2 with first m+r model (superseded) | 60 (30) | 5.5 / 5.9 | -5.4, 7.9, -19.4..7.2 | 84 / 13.3 | 0.5, 7.7, -14.4..15.0 | 90 / 16.4 | 69 / 74 | 70 / 74 | 2% | 3.7% / 3.0% |
| D3i D3 with first m+r model (superseded) | 60 (12) | 5.8 / 5.3 | -3.0, 5.6, -13.2..7.2 | 83 / 10.0 | 2.4, 7.2, -11.0..15.2 | 89 / 15.2 | 72 / 78 | 70 / 74 | 3% | 6.4% / 5.9% |
| D4i D4 with first m+r model (superseded) | 60 (20) | 5.7 / 5.7 | -3.6, 5.6, -13.5..6.8 | 84 / 10.3 | 1.0, 7.7, -13.6..13.6 | 93 / 17.4 | 72 / 77 | 70 / 74 | 1% | 11.0% / 6.3% |

### ja, Chinese L1 (cognates), skip-if-unknown 0.3

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 5.9 | 0.5, 5.9, -12.1..12.9 | 87 / 11.5 | (reports meaning) 16.4 | 32 / — | 75 / 84 | 78 / 84 | 68% | 30.6% / 9.1% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.4 | 1.2, 5.5, -10.3..13.0 | 91 / 12.1 | (reports meaning) 17.1 | 30 / — | 72 / 80 | 79 / 85 | 70% | 37.4% / 10.1% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.4 | 0.8, 6.8, -13.4..14.5 | 89 / 14.1 | (reports meaning) 16.7 | 40 / — | 74 / 83 | 72 / 78 | 60% | 33.6% / 10.2% |
| D1L adaptive exam levels, meaning | 40 (0) | 4.0 / 3.4 | -1.5, 9.3, -23.3..17.0 | 82 / 17.0 | (reports meaning) 14.4 | 56 / — | 67 / 81 | 61 / 73 | 44% | 31.0% / 8.7% |
| D2 IRT, meaning+reading every word | 60 (30) | 5.5 / 5.1 | 0.9, 6.4, -12.3..13.6 | 91 / 13.7 | 1.3, 5.4, -9.0..12.7 | 93 / 12.6 | 71 / 77 | 75 / 80 | 5% | 13.7% / 3.5% |
| D3 IRT, reading after correct meaning | 60 (20) | 5.7 / 5.0 | 1.5, 5.9, -11.4..12.6 | 89 / 12.1 | 2.0, 5.5, -8.9..13.4 | 92 / 11.8 | 75 / 82 | 76 / 80 | 7% | 12.7% / 6.4% |
| D4 IRT, reading on half the words | 60 (20) | 5.7 / 5.1 | 1.0, 5.7, -11.1..12.7 | 90 / 12.2 | 1.8, 5.8, -10.2..14.2 | 91 / 12.4 | 74 / 81 | 74 / 80 | 7% | 27.3% / 8.0% |
| D3S adaptive bands, reading after correct meaning | 60 (19) | 5.7 / 5.0 | -0.1, 7.2, -16.4..14.7 | 86 / 13.9 | 0.6, 6.8, -14.0..15.5 | 88 / 13.4 | 75 / 83 | 79 / 87 | 7% | 13.6% / 8.0% |
| D3L adaptive exam levels, reading after correct meaning | 60 (20) | 5.7 / 5.0 | -1.4, 9.5, -21.1..18.1 | 84 / 16.9 | -1.1, 8.8, -16.9..18.5 | 85 / 16.0 | 69 / 81 | 77 / 87 | 7% | 10.8% / 5.9% |
| D2i D2 with first m+r model (superseded) | 60 (30) | 5.5 / 5.1 | 0.9, 6.0, -11.2..12.2 | 95 / 13.9 | 0.1, 5.4, -11.1..10.2 | 87 / 10.1 | 73 / 80 | 72 / 77 | 6% | 12.3% / 3.1% |
| D3i D3 with first m+r model (superseded) | 60 (21) | 5.7 / 5.0 | 1.1, 5.7, -10.2..12.4 | 94 / 12.6 | 0.1, 5.2, -10.6..10.6 | 88 / 9.8 | 73 / 82 | 72 / 77 | 5% | 11.5% / 5.3% |
| D4i D4 with first m+r model (superseded) | 60 (20) | 5.7 / 5.1 | 0.1, 5.9, -11.9..12.6 | 91 / 12.4 | -0.4, 6.1, -13.0..11.8 | 84 / 11.1 | 73 / 80 | 72 / 76 | 6% | 26.5% / 8.1% |

### ja, Chinese L1 (cognates), skip-if-unknown 0.7

| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | m+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | "known" interval above true m+r | credited words not known m+r / not known at all |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 fixed 10/band, meaning (today) | 70 (0) | 7.0 / 6.1 | 0.1, 5.0, -10.5..10.4 | 91 / 10.6 | (reports meaning) 15.5 | 29 / — | 76 / 84 | 74 / 82 | 71% | 25.6% / 3.8% |
| D1 IRT adaptive, meaning | 40 (0) | 4.0 / 3.5 | 0.7, 5.3, -10.7..11.4 | 90 / 11.3 | (reports meaning) 16.1 | 31 / — | 71 / 77 | 76 / 83 | 69% | 32.1% / 4.6% |
| D1S adaptive bands, meaning | 40 (0) | 4.0 / 3.5 | -0.4, 6.7, -13.8..12.4 | 89 / 13.1 | (reports meaning) 15.0 | 43 / — | 73 / 81 | 68 / 77 | 57% | 28.3% / 4.2% |
| D1L adaptive exam levels, meaning | 40 (0) | 4.0 / 3.5 | -1.3, 8.0, -19.4..15.2 | 85 / 15.6 | (reports meaning) 14.1 | 56 / — | 72 / 86 | 64 / 76 | 44% | 25.5% / 3.6% |
| D2 IRT, meaning+reading every word | 60 (30) | 5.5 / 5.6 | 0.1, 5.7, -11.2..12.3 | 93 / 12.8 | 0.2, 4.7, -9.2..10.2 | 96 / 11.7 | 70 / 77 | 72 / 77 | 2% | 5.5% / 1.1% |
| D3 IRT, reading after correct meaning | 60 (19) | 5.7 / 5.3 | 0.4, 5.2, -9.9..11.2 | 92 / 11.1 | 0.5, 4.7, -8.3..10.1 | 94 / 10.7 | 74 / 80 | 71 / 76 | 4% | 5.2% / 2.3% |
| D4 IRT, reading on half the words | 60 (20) | 5.7 / 5.5 | 0.8, 5.5, -9.4..13.2 | 88 / 11.2 | 0.7, 5.1, -9.3..12.7 | 91 / 11.4 | 68 / 76 | 72 / 77 | 6% | 20.9% / 3.3% |
| D3S adaptive bands, reading after correct meaning | 60 (19) | 5.7 / 5.3 | -0.3, 6.3, -14.0..12.4 | 88 / 12.9 | -0.2, 6.3, -13.7..12.9 | 87 / 12.4 | 74 / 83 | 77 / 85 | 5% | 5.4% / 3.0% |
| D3L adaptive exam levels, reading after correct meaning | 60 (20) | 5.7 / 5.2 | -1.8, 8.1, -17.5..13.8 | 88 / 15.7 | -1.3, 7.3, -15.8..13.6 | 89 / 14.8 | 68 / 83 | 73 / 87 | 3% | 4.5% / 2.5% |
| D2i D2 with first m+r model (superseded) | 60 (30) | 5.5 / 5.6 | 0.8, 5.9, -11.2..12.8 | 92 / 12.9 | -0.8, 5.3, -12.0..9.9 | 80 / 8.9 | 70 / 77 | 70 / 75 | 7% | 4.7% / 0.8% |
| D3i D3 with first m+r model (superseded) | 60 (20) | 5.7 / 5.3 | 0.6, 5.3, -10.5..11.5 | 92 / 11.5 | -1.0, 5.1, -11.8..8.9 | 82 / 8.5 | 71 / 78 | 70 / 75 | 5% | 5.2% / 2.5% |
| D4i D4 with first m+r model (superseded) | 60 (20) | 5.7 / 5.4 | 0.0, 5.0, -9.5..12.0 | 93 / 11.4 | -1.1, 5.6, -12.9..10.8 | 82 / 9.7 | 71 / 77 | 70 / 74 | 6% | 19.5% / 3.4% |

## Precision vs number of items (fixed-length snapshots)

Mean 90% half-width and MAE of the meaning count (and of the meaning+reading count for reading designs), % of N, averaged over all populations of the language; coverage in brackets.

### zh

| design | n=20 | n=30 | n=40 | n=50 | n=60 | n=70 | n=90 |
|---|---|---|---|---|---|---|---|
| D0 | m ±20.7 MAE 9.8 (92%) | m ±16.6 MAE 7.8 (92%) | m ±14.3 MAE 6.8 (90%) | m ±12.7 MAE 6.1 (90%) | m ±11.6 MAE 5.6 (90%) | m ±10.7 MAE 5.1 (91%) | — |
| D1 | m ±15.0 MAE 7.4 (91%) | m ±12.7 MAE 6.3 (89%) | m ±11.3 MAE 5.6 (90%) | m ±10.2 MAE 5.0 (90%) | m ±9.4 MAE 4.7 (90%) | m ±8.8 MAE 4.4 (90%) | — |
| D1S | m ±19.4 MAE 9.4 (91%) | m ±15.3 MAE 7.6 (90%) | m ±13.1 MAE 6.5 (89%) | m ±11.6 MAE 5.9 (89%) | m ±10.5 MAE 5.4 (89%) | m ±9.7 MAE 5.0 (87%) | — |
| D1L | m ±28.4 MAE 14.3 (89%) | m ±21.8 MAE 11.3 (88%) | m ±18.1 MAE 9.5 (88%) | m ±15.7 MAE 8.4 (86%) | m ±14.0 MAE 7.5 (86%) | m ±12.8 MAE 6.8 (86%) | — |
| D2 | m ±19.7 MAE 9.3 (92%); m+r ±18.0 MAE 8.4 (93%) | m ±17.0 MAE 8.1 (92%); m+r ±15.7 MAE 7.1 (94%) | m ±15.2 MAE 7.3 (92%); m+r ±14.1 MAE 6.2 (95%) | m ±13.9 MAE 6.8 (92%); m+r ±12.9 MAE 5.6 (95%) | m ±12.9 MAE 6.3 (91%); m+r ±12.0 MAE 5.2 (95%) | m ±12.1 MAE 5.9 (92%); m+r ±11.2 MAE 4.9 (95%) | m ±10.9 MAE 5.3 (91%); m+r ±10.1 MAE 4.4 (95%) |
| D3 | m ±18.2 MAE 8.7 (91%); m+r ±17.0 MAE 7.8 (93%) | m ±15.6 MAE 7.6 (91%); m+r ±14.6 MAE 6.6 (94%) | m ±13.8 MAE 6.7 (91%); m+r ±13.0 MAE 5.7 (95%) | m ±12.6 MAE 6.0 (91%); m+r ±11.9 MAE 5.1 (95%) | m ±11.6 MAE 5.5 (91%); m+r ±11.0 MAE 4.7 (95%) | m ±10.9 MAE 5.2 (91%); m+r ±10.3 MAE 4.4 (94%) | m ±9.7 MAE 4.7 (91%); m+r ±9.2 MAE 3.9 (94%) |
| D4 | m ±17.9 MAE 8.6 (92%); m+r ±18.1 MAE 8.7 (92%) | m ±15.1 MAE 7.2 (91%); m+r ±15.9 MAE 7.5 (93%) | m ±13.4 MAE 6.4 (91%); m+r ±14.2 MAE 6.4 (94%) | m ±12.3 MAE 6.1 (90%); m+r ±13.2 MAE 6.0 (93%) | m ±11.4 MAE 5.5 (91%); m+r ±12.3 MAE 5.6 (93%) | m ±10.6 MAE 5.1 (91%); m+r ±11.5 MAE 5.2 (94%) | m ±9.5 MAE 4.6 (91%); m+r ±10.5 MAE 4.7 (94%) |
| D3S | m ±26.9 MAE 12.3 (92%); m+r ±24.7 MAE 10.7 (95%) | m ±20.1 MAE 9.4 (91%); m+r ±18.0 MAE 7.9 (93%) | m ±16.9 MAE 8.2 (90%); m+r ±15.0 MAE 6.9 (92%) | m ±14.9 MAE 7.3 (90%); m+r ±13.2 MAE 6.2 (92%) | m ±13.5 MAE 6.6 (90%); m+r ±11.9 MAE 5.7 (91%) | m ±12.4 MAE 6.0 (90%); m+r ±10.9 MAE 5.2 (90%) | m ±10.9 MAE 5.3 (89%); m+r ±9.5 MAE 4.5 (90%) |
| D3L | m ±37.5 MAE 18.7 (92%); m+r ±34.5 MAE 15.1 (95%) | m ±28.7 MAE 14.7 (88%); m+r ±25.7 MAE 11.7 (93%) | m ±25.0 MAE 13.0 (88%); m+r ±22.1 MAE 10.4 (92%) | m ±21.7 MAE 11.1 (87%); m+r ±19.0 MAE 9.0 (91%) | m ±19.5 MAE 10.1 (88%); m+r ±16.8 MAE 8.1 (91%) | m ±17.6 MAE 9.1 (88%); m+r ±15.1 MAE 7.3 (91%) | m ±15.1 MAE 7.8 (88%); m+r ±12.9 MAE 6.3 (90%) |
| D2i | m ±20.3 MAE 9.8 (92%); m+r ±22.3 MAE 12.1 (89%) | m ±17.8 MAE 8.5 (92%); m+r ±20.2 MAE 10.8 (89%) | m ±16.0 MAE 7.9 (91%); m+r ±18.8 MAE 10.0 (87%) | m ±14.8 MAE 7.3 (91%); m+r ±17.7 MAE 9.5 (88%) | m ±13.8 MAE 6.9 (90%); m+r ±16.9 MAE 9.2 (87%) | m ±13.0 MAE 6.6 (90%); m+r ±16.3 MAE 8.9 (87%) | m ±11.8 MAE 5.9 (89%); m+r ±15.3 MAE 8.4 (87%) |
| D3i | m ±18.2 MAE 8.8 (91%); m+r ±20.8 MAE 11.6 (89%) | m ±15.7 MAE 7.8 (90%); m+r ±18.7 MAE 10.6 (86%) | m ±14.0 MAE 6.9 (90%); m+r ±17.2 MAE 10.0 (86%) | m ±12.8 MAE 6.5 (90%); m+r ±16.3 MAE 9.6 (85%) | m ±11.9 MAE 6.0 (89%); m+r ±15.5 MAE 9.3 (84%) | m ±11.2 MAE 5.6 (90%); m+r ±14.8 MAE 8.9 (85%) | m ±10.1 MAE 5.1 (89%); m+r ±13.8 MAE 8.3 (84%) |
| D4i | m ±18.0 MAE 9.0 (90%); m+r ±24.1 MAE 12.8 (91%) | m ±15.2 MAE 7.8 (90%); m+r ±22.4 MAE 11.9 (90%) | m ±13.5 MAE 6.9 (90%); m+r ±20.6 MAE 10.8 (91%) | m ±12.4 MAE 6.2 (90%); m+r ±19.6 MAE 10.3 (91%) | m ±11.4 MAE 5.7 (90%); m+r ±18.8 MAE 9.8 (90%) | m ±10.6 MAE 5.3 (89%); m+r ±17.9 MAE 9.5 (90%) | m ±9.5 MAE 4.8 (89%); m+r ±16.9 MAE 9.0 (90%) |

### ja

| design | n=20 | n=30 | n=40 | n=50 | n=60 | n=70 | n=90 |
|---|---|---|---|---|---|---|---|
| D0 | m ±21.2 MAE 9.7 (92%) | m ±17.1 MAE 8.0 (91%) | m ±14.7 MAE 7.0 (90%) | m ±13.1 MAE 6.3 (91%) | m ±11.9 MAE 5.8 (90%) | m ±11.0 MAE 5.3 (90%) | — |
| D1 | m ±15.0 MAE 6.8 (93%) | m ±12.7 MAE 5.8 (92%) | m ±11.3 MAE 5.3 (91%) | m ±10.2 MAE 5.0 (90%) | m ±9.5 MAE 4.6 (90%) | m ±8.8 MAE 4.5 (89%) | — |
| D1S | m ±19.7 MAE 10.0 (89%) | m ±15.6 MAE 8.1 (87%) | m ±13.3 MAE 6.9 (87%) | m ±11.8 MAE 6.2 (88%) | m ±10.7 MAE 5.6 (87%) | m ±9.9 MAE 5.2 (86%) | — |
| D1L | m ±23.5 MAE 12.5 (87%) | m ±18.5 MAE 10.0 (86%) | m ±15.7 MAE 8.6 (84%) | m ±13.8 MAE 7.5 (85%) | m ±12.4 MAE 6.7 (85%) | m ±11.4 MAE 6.0 (86%) | — |
| D2 | m ±19.4 MAE 8.4 (94%); m+r ±17.7 MAE 7.9 (93%) | m ±16.7 MAE 7.4 (93%); m+r ±15.4 MAE 6.8 (93%) | m ±15.0 MAE 6.5 (93%); m+r ±13.8 MAE 6.0 (93%) | m ±13.7 MAE 6.1 (93%); m+r ±12.7 MAE 5.6 (93%) | m ±12.7 MAE 5.6 (93%); m+r ±11.8 MAE 5.2 (93%) | m ±11.9 MAE 5.4 (92%); m+r ±11.1 MAE 5.1 (92%) | m ±10.7 MAE 5.0 (90%); m+r ±10.0 MAE 4.8 (90%) |
| D3 | m ±17.3 MAE 7.9 (94%); m+r ±16.4 MAE 7.7 (92%) | m ±14.8 MAE 6.8 (92%); m+r ±14.1 MAE 6.6 (92%) | m ±13.1 MAE 6.1 (92%); m+r ±12.6 MAE 6.0 (92%) | m ±11.9 MAE 5.7 (90%); m+r ±11.5 MAE 5.6 (90%) | m ±11.0 MAE 5.4 (90%); m+r ±10.7 MAE 5.3 (89%) | m ±10.3 MAE 5.1 (89%); m+r ±10.0 MAE 5.1 (88%) | m ±9.2 MAE 4.7 (87%); m+r ±9.0 MAE 4.6 (88%) |
| D4 | m ±17.6 MAE 7.6 (94%); m+r ±16.9 MAE 7.9 (92%) | m ±15.0 MAE 6.8 (93%); m+r ±14.7 MAE 7.0 (91%) | m ±13.3 MAE 6.1 (91%); m+r ±13.1 MAE 6.3 (91%) | m ±12.2 MAE 5.6 (92%); m+r ±12.1 MAE 5.8 (90%) | m ±11.3 MAE 5.3 (90%); m+r ±11.2 MAE 5.6 (89%) | m ±10.5 MAE 5.1 (89%); m+r ±10.5 MAE 5.3 (89%) | m ±9.5 MAE 4.7 (89%); m+r ±9.5 MAE 4.9 (87%) |
| D3S | m ±25.4 MAE 12.3 (91%); m+r ±24.2 MAE 11.2 (92%) | m ±19.1 MAE 9.6 (88%); m+r ±18.0 MAE 8.9 (89%) | m ±16.1 MAE 8.2 (88%); m+r ±15.2 MAE 7.5 (89%) | m ±14.2 MAE 7.2 (88%); m+r ±13.4 MAE 6.6 (88%) | m ±12.8 MAE 6.4 (88%); m+r ±12.1 MAE 6.0 (89%) | m ±11.8 MAE 5.9 (88%); m+r ±11.1 MAE 5.6 (89%) | m ±10.3 MAE 5.3 (87%); m+r ±9.7 MAE 5.0 (88%) |
| D3L | m ±28.3 MAE 14.4 (88%); m+r ±26.8 MAE 13.4 (89%) | m ±23.2 MAE 12.2 (86%); m+r ±21.8 MAE 11.2 (87%) | m ±19.5 MAE 10.3 (86%); m+r ±18.2 MAE 9.7 (86%) | m ±17.1 MAE 9.2 (86%); m+r ±16.0 MAE 8.6 (86%) | m ±15.4 MAE 8.4 (85%); m+r ±14.4 MAE 7.6 (86%) | m ±14.1 MAE 7.6 (84%); m+r ±13.2 MAE 6.9 (85%) | m ±12.2 MAE 6.5 (85%); m+r ±11.4 MAE 5.9 (87%) |
| D2i | m ±19.8 MAE 8.9 (93%); m+r ±16.7 MAE 9.2 (86%) | m ±17.3 MAE 8.0 (92%); m+r ±15.2 MAE 7.9 (89%) | m ±15.6 MAE 7.3 (92%); m+r ±14.1 MAE 7.2 (87%) | m ±14.4 MAE 7.1 (91%); m+r ±13.4 MAE 6.8 (87%) | m ±13.4 MAE 6.7 (90%); m+r ±12.8 MAE 6.4 (87%) | m ±12.7 MAE 6.4 (89%); m+r ±12.3 MAE 6.0 (88%) | m ±11.5 MAE 6.0 (87%); m+r ±11.6 MAE 5.6 (88%) |
| D3i | m ±17.5 MAE 7.8 (93%); m+r ±16.4 MAE 8.6 (88%) | m ±15.0 MAE 6.8 (91%); m+r ±14.7 MAE 7.6 (88%) | m ±13.4 MAE 6.3 (91%); m+r ±13.7 MAE 6.9 (88%) | m ±12.2 MAE 5.8 (91%); m+r ±12.9 MAE 6.5 (89%) | m ±11.3 MAE 5.5 (90%); m+r ±12.3 MAE 6.2 (88%) | m ±10.6 MAE 5.2 (88%); m+r ±11.8 MAE 5.9 (88%) | m ±9.5 MAE 4.8 (88%); m+r ±11.1 MAE 5.4 (88%) |
| D4i | m ±17.8 MAE 7.9 (93%); m+r ±17.8 MAE 9.4 (87%) | m ±15.1 MAE 6.9 (92%); m+r ±16.3 MAE 8.4 (88%) | m ±13.4 MAE 6.3 (91%); m+r ±15.1 MAE 7.5 (89%) | m ±12.4 MAE 5.9 (90%); m+r ±14.4 MAE 7.1 (89%) | m ±11.4 MAE 5.5 (90%); m+r ±13.8 MAE 6.7 (88%) | m ±10.6 MAE 5.2 (89%); m+r ±13.2 MAE 6.4 (88%) | m ±9.6 MAE 4.8 (88%); m+r ±12.4 MAE 5.9 (89%) |

## Stopping rules (applied to the snapshots; stop at the first checkpoint where every reported 90% half-width <= h x N, after a minimum, else at the cap)

### h = 0.1, min 20, cap 40 (meaning-only) / 60 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.3 | D1 | 39 (35..40) | 9% | 3.3 / 3.5 | 5.9 / 90% | — | 77 |
| zh, English L1 s=0.3 | D1S | 40 (40..40) | 0% | 3.4 / 3.5 | 7.1 / 87% | — | 80 |
| zh, English L1 s=0.3 | D1L | 40 (40..40) | 0% | 3.4 / 3.4 | 9.8 / 88% | — | 74 |
| zh, English L1 s=0.3 | D2 | 60 (60..60) | 2% | 5.0 / 5.6 | 6.7 / 90% | 5.2 / 96% | 68 |
| zh, English L1 s=0.3 | D3 | 58 (40..61) | 8% | 4.7 / 5.2 | 5.5 / 91% | 4.6 / 97% | 69 |
| zh, English L1 s=0.3 | D4 | 59 (50..60) | 5% | 5.0 / 5.4 | 5.7 / 91% | 5.3 / 93% | 68 |
| zh, English L1 s=0.3 | D3S | 60 (60..61) | 0% | 4.9 / 5.3 | 6.8 / 90% | 5.5 / 91% | 80 |
| zh, English L1 s=0.3 | D3L | 60 (60..61) | 0% | 4.9 / 5.2 | 10.4 / 88% | 7.5 / 91% | 84 |
| zh, English L1 s=0.3 | D2i | 60 (60..60) | 0% | 5.2 / 5.8 | 7.3 / 89% | 11.6 / 93% | 66 |
| zh, English L1 s=0.3 | D3i | 60 (60..61) | 0% | 5.0 / 5.3 | 6.3 / 89% | 12.3 / 89% | 67 |
| zh, English L1 s=0.3 | D4i | 60 (60..60) | 0% | 5.1 / 5.6 | 6.2 / 89% | 12.3 / 95% | 63 |
| zh, English L1 s=0.7 | D1 | 37 (20..40) | 24% | 3.3 / 3.7 | 5.0 / 90% | — | 78 |
| zh, English L1 s=0.7 | D1S | 40 (40..40) | 5% | 3.5 / 3.7 | 5.9 / 90% | — | 82 |
| zh, English L1 s=0.7 | D1L | 40 (40..40) | 4% | 3.5 / 3.7 | 8.4 / 90% | — | 76 |
| zh, English L1 s=0.7 | D2 | 58 (40..60) | 9% | 5.4 / 6.3 | 5.4 / 96% | 4.9 / 96% | 69 |
| zh, English L1 s=0.7 | D3 | 55 (30..61) | 21% | 4.7 / 5.5 | 4.7 / 93% | 4.0 / 96% | 69 |
| zh, English L1 s=0.7 | D4 | 56 (30..60) | 16% | 5.2 / 6.0 | 4.7 / 93% | 4.4 / 95% | 68 |
| zh, English L1 s=0.7 | D3S | 58 (40..61) | 14% | 5.0 / 5.6 | 5.8 / 91% | 4.9 / 92% | 80 |
| zh, English L1 s=0.7 | D3L | 59 (45..61) | 8% | 4.9 / 5.5 | 8.7 / 88% | 6.7 / 93% | 81 |
| zh, English L1 s=0.7 | D2i | 60 (60..60) | 0% | 5.9 / 6.8 | 6.9 / 90% | 11.8 / 93% | 67 |
| zh, English L1 s=0.7 | D3i | 60 (60..61) | 1% | 5.3 / 5.7 | 5.6 / 88% | 12.2 / 91% | 66 |
| zh, English L1 s=0.7 | D4i | 60 (60..60) | 0% | 5.7 / 6.4 | 5.1 / 92% | 12.8 / 92% | 65 |
| zh, Japanese L1 (cognates) s=0.3 | D1 | 38 (25..40) | 15% | 3.2 / 3.4 | 5.9 / 91% | — | 76 |
| zh, Japanese L1 (cognates) s=0.3 | D1S | 40 (40..40) | 0% | 3.4 / 3.4 | 6.8 / 89% | — | 69 |
| zh, Japanese L1 (cognates) s=0.3 | D1L | 40 (40..40) | 0% | 3.4 / 3.4 | 10.5 / 85% | — | 59 |
| zh, Japanese L1 (cognates) s=0.3 | D2 | 60 (60..60) | 0% | 5.1 / 5.7 | 6.7 / 92% | 5.5 / 95% | 70 |
| zh, Japanese L1 (cognates) s=0.3 | D3 | 60 (60..61) | 0% | 5.1 / 5.5 | 6.1 / 91% | 5.3 / 95% | 69 |
| zh, Japanese L1 (cognates) s=0.3 | D4 | 60 (60..60) | 0% | 5.1 / 5.5 | 6.2 / 89% | 6.8 / 91% | 68 |
| zh, Japanese L1 (cognates) s=0.3 | D3S | 60 (60..61) | 0% | 5.1 / 5.5 | 7.3 / 89% | 6.7 / 90% | 80 |
| zh, Japanese L1 (cognates) s=0.3 | D3L | 60 (60..61) | 0% | 5.0 / 5.4 | 10.8 / 89% | 9.7 / 89% | 78 |
| zh, Japanese L1 (cognates) s=0.3 | D2i | 60 (60..60) | 0% | 5.1 / 5.7 | 7.0 / 91% | 7.1 / 82% | 63 |
| zh, Japanese L1 (cognates) s=0.3 | D3i | 60 (60..61) | 0% | 5.1 / 5.5 | 6.3 / 90% | 6.4 / 82% | 64 |
| zh, Japanese L1 (cognates) s=0.3 | D4i | 60 (60..60) | 0% | 5.1 / 5.5 | 5.9 / 89% | 7.8 / 85% | 63 |
| zh, Japanese L1 (cognates) s=0.7 | D1 | 39 (30..40) | 12% | 3.4 / 3.6 | 5.6 / 90% | — | 80 |
| zh, Japanese L1 (cognates) s=0.7 | D1S | 40 (40..40) | 0% | 3.5 / 3.6 | 6.4 / 90% | — | 70 |
| zh, Japanese L1 (cognates) s=0.7 | D1L | 40 (40..40) | 0% | 3.4 / 3.6 | 9.3 / 88% | — | 59 |
| zh, Japanese L1 (cognates) s=0.7 | D2 | 60 (60..60) | 0% | 5.7 / 6.5 | 6.5 / 88% | 5.3 / 94% | 70 |
| zh, Japanese L1 (cognates) s=0.7 | D3 | 60 (60..61) | 0% | 5.5 / 6.0 | 5.9 / 90% | 5.0 / 93% | 70 |
| zh, Japanese L1 (cognates) s=0.7 | D4 | 60 (60..60) | 0% | 5.6 / 6.1 | 5.7 / 92% | 6.1 / 93% | 69 |
| zh, Japanese L1 (cognates) s=0.7 | D3S | 60 (60..61) | 0% | 5.5 / 6.1 | 6.6 / 90% | 5.7 / 91% | 81 |
| zh, Japanese L1 (cognates) s=0.7 | D3L | 60 (60..61) | 0% | 5.3 / 5.9 | 10.7 / 86% | 8.4 / 91% | 79 |
| zh, Japanese L1 (cognates) s=0.7 | D2i | 60 (60..60) | 0% | 5.7 / 6.5 | 6.4 / 91% | 6.3 / 79% | 66 |
| zh, Japanese L1 (cognates) s=0.7 | D3i | 60 (60..61) | 1% | 5.5 / 6.0 | 5.8 / 90% | 6.2 / 75% | 65 |
| zh, Japanese L1 (cognates) s=0.7 | D4i | 60 (60..60) | 0% | 5.5 / 6.1 | 5.7 / 90% | 6.4 / 86% | 68 |
| ja, English L1 s=0.3 | D1 | 39 (30..40) | 11% | 3.3 / 3.5 | 5.4 / 93% | — | 79 |
| ja, English L1 s=0.3 | D1S | 40 (40..40) | 0% | 3.4 / 3.5 | 7.8 / 84% | — | 84 |
| ja, English L1 s=0.3 | D1L | 40 (40..40) | 0% | 3.4 / 3.4 | 9.3 / 85% | — | 82 |
| ja, English L1 s=0.3 | D2 | 59 (60..60) | 3% | 5.0 / 5.6 | 5.4 / 94% | 5.4 / 92% | 71 |
| ja, English L1 s=0.3 | D3 | 58 (40..61) | 12% | 4.7 / 5.2 | 5.2 / 92% | 5.5 / 89% | 73 |
| ja, English L1 s=0.3 | D4 | 59 (60..60) | 4% | 5.0 / 5.4 | 5.2 / 93% | 5.8 / 89% | 71 |
| ja, English L1 s=0.3 | D3S | 60 (60..61) | 0% | 4.9 / 5.2 | 6.7 / 90% | 5.9 / 90% | 84 |
| ja, English L1 s=0.3 | D3L | 60 (60..61) | 0% | 4.9 / 5.2 | 8.7 / 86% | 7.5 / 83% | 86 |
| ja, English L1 s=0.3 | D2i | 60 (60..60) | 1% | 5.2 / 5.8 | 6.8 / 89% | 7.2 / 92% | 71 |
| ja, English L1 s=0.3 | D3i | 60 (60..61) | 2% | 4.9 / 5.3 | 5.4 / 91% | 7.1 / 94% | 72 |
| ja, English L1 s=0.3 | D4i | 60 (60..60) | 0% | 5.1 / 5.6 | 5.7 / 90% | 7.3 / 94% | 70 |
| ja, English L1 s=0.7 | D1 | 37 (20..40) | 27% | 3.3 / 3.7 | 4.9 / 93% | — | 81 |
| ja, English L1 s=0.7 | D1S | 40 (40..40) | 2% | 3.5 / 3.7 | 6.4 / 87% | — | 88 |
| ja, English L1 s=0.7 | D1L | 40 (40..40) | 3% | 3.5 / 3.7 | 7.7 / 85% | — | 89 |
| ja, English L1 s=0.7 | D2 | 57 (30..60) | 13% | 5.4 / 6.4 | 4.9 / 95% | 5.3 / 92% | 76 |
| ja, English L1 s=0.7 | D3 | 53 (25..61) | 31% | 4.5 / 5.4 | 5.2 / 90% | 5.6 / 87% | 75 |
| ja, English L1 s=0.7 | D4 | 55 (30..60) | 22% | 5.1 / 6.0 | 4.7 / 92% | 5.5 / 88% | 76 |
| ja, English L1 s=0.7 | D3S | 58 (45..61) | 13% | 5.0 / 5.5 | 5.6 / 88% | 5.2 / 89% | 85 |
| ja, English L1 s=0.7 | D3L | 58 (40..61) | 14% | 4.9 / 5.5 | 7.5 / 83% | 6.9 / 84% | 89 |
| ja, English L1 s=0.7 | D2i | 60 (60..60) | 2% | 5.9 / 6.8 | 7.9 / 84% | 7.7 / 90% | 74 |
| ja, English L1 s=0.7 | D3i | 60 (60..61) | 3% | 5.2 / 5.7 | 5.6 / 82% | 7.2 / 89% | 74 |
| ja, English L1 s=0.7 | D4i | 60 (60..60) | 1% | 5.7 / 6.4 | 5.6 / 85% | 7.7 / 93% | 74 |
| ja, Chinese L1 (cognates) s=0.3 | D1 | 39 (30..40) | 11% | 3.3 / 3.4 | 5.5 / 91% | — | 85 |
| ja, Chinese L1 (cognates) s=0.3 | D1S | 40 (40..40) | 0% | 3.4 / 3.4 | 6.8 / 89% | — | 78 |
| ja, Chinese L1 (cognates) s=0.3 | D1L | 40 (40..40) | 0% | 3.4 / 3.4 | 9.3 / 82% | — | 73 |
| ja, Chinese L1 (cognates) s=0.3 | D2 | 60 (60..60) | 0% | 5.1 / 5.7 | 6.4 / 91% | 5.4 / 93% | 80 |
| ja, Chinese L1 (cognates) s=0.3 | D3 | 60 (60..61) | 2% | 5.0 / 5.4 | 5.9 / 89% | 5.5 / 92% | 80 |
| ja, Chinese L1 (cognates) s=0.3 | D4 | 60 (60..60) | 1% | 5.1 / 5.5 | 5.7 / 90% | 5.8 / 91% | 80 |
| ja, Chinese L1 (cognates) s=0.3 | D3S | 60 (60..61) | 0% | 5.0 / 5.4 | 7.2 / 86% | 6.8 / 88% | 87 |
| ja, Chinese L1 (cognates) s=0.3 | D3L | 60 (60..61) | 0% | 5.0 / 5.4 | 9.5 / 84% | 8.8 / 85% | 87 |
| ja, Chinese L1 (cognates) s=0.3 | D2i | 60 (60..60) | 3% | 5.1 / 5.6 | 6.1 / 95% | 5.4 / 87% | 77 |
| ja, Chinese L1 (cognates) s=0.3 | D3i | 60 (60..61) | 4% | 5.0 / 5.4 | 5.7 / 94% | 5.2 / 88% | 77 |
| ja, Chinese L1 (cognates) s=0.3 | D4i | 60 (60..60) | 2% | 5.1 / 5.4 | 5.9 / 91% | 6.1 / 83% | 76 |
| ja, Chinese L1 (cognates) s=0.7 | D1 | 39 (30..40) | 14% | 3.4 / 3.6 | 5.4 / 91% | — | 83 |
| ja, Chinese L1 (cognates) s=0.7 | D1S | 40 (40..40) | 0% | 3.5 / 3.6 | 6.7 / 89% | — | 77 |
| ja, Chinese L1 (cognates) s=0.7 | D1L | 40 (40..40) | 0% | 3.5 / 3.6 | 8.0 / 85% | — | 76 |
| ja, Chinese L1 (cognates) s=0.7 | D2 | 60 (60..60) | 0% | 5.6 / 6.4 | 5.7 / 93% | 4.7 / 96% | 77 |
| ja, Chinese L1 (cognates) s=0.7 | D3 | 60 (60..61) | 1% | 5.3 / 5.8 | 5.2 / 92% | 4.7 / 94% | 76 |
| ja, Chinese L1 (cognates) s=0.7 | D4 | 60 (60..60) | 0% | 5.5 / 6.1 | 5.5 / 88% | 5.1 / 91% | 77 |
| ja, Chinese L1 (cognates) s=0.7 | D3S | 60 (60..61) | 0% | 5.3 / 5.8 | 6.3 / 88% | 6.3 / 87% | 85 |
| ja, Chinese L1 (cognates) s=0.7 | D3L | 60 (60..61) | 0% | 5.2 / 5.8 | 8.1 / 88% | 7.3 / 89% | 87 |
| ja, Chinese L1 (cognates) s=0.7 | D2i | 60 (60..60) | 3% | 5.5 / 6.4 | 5.9 / 92% | 5.4 / 80% | 74 |
| ja, Chinese L1 (cognates) s=0.7 | D3i | 59 (51..61) | 6% | 5.2 / 5.8 | 5.3 / 92% | 5.1 / 82% | 75 |
| ja, Chinese L1 (cognates) s=0.7 | D4i | 59 (60..60) | 5% | 5.4 / 6.0 | 5.0 / 93% | 5.6 / 82% | 74 |

### h = 0.12, min 20, cap 40 (meaning-only) / 60 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.3 | D1 | 36 (20..40) | 37% | 3.0 / 3.4 | 6.0 / 89% | — | 77 |
| zh, English L1 s=0.3 | D1S | 40 (40..40) | 4% | 3.3 / 3.5 | 7.1 / 87% | — | 80 |
| zh, English L1 s=0.3 | D1L | 40 (40..40) | 2% | 3.3 / 3.4 | 9.8 / 88% | — | 74 |
| zh, English L1 s=0.3 | D2 | 58 (46..60) | 11% | 4.9 / 5.5 | 6.7 / 90% | 5.2 / 96% | 68 |
| zh, English L1 s=0.3 | D3 | 55 (26..61) | 25% | 4.4 / 5.1 | 5.5 / 92% | 4.6 / 97% | 69 |
| zh, English L1 s=0.3 | D4 | 56 (30..60) | 17% | 4.7 / 5.3 | 5.7 / 91% | 5.3 / 93% | 68 |
| zh, English L1 s=0.3 | D3S | 59 (50..61) | 8% | 4.8 / 5.3 | 7.0 / 90% | 5.6 / 91% | 80 |
| zh, English L1 s=0.3 | D3L | 60 (60..61) | 3% | 4.8 / 5.2 | 10.5 / 87% | 7.4 / 91% | 84 |
| zh, English L1 s=0.3 | D2i | 60 (60..60) | 1% | 5.2 / 5.8 | 7.3 / 89% | 11.6 / 93% | 66 |
| zh, English L1 s=0.3 | D3i | 60 (60..61) | 4% | 4.9 / 5.3 | 6.3 / 89% | 12.3 / 90% | 67 |
| zh, English L1 s=0.3 | D4i | 60 (60..60) | 0% | 5.1 / 5.6 | 6.2 / 89% | 12.3 / 95% | 63 |
| zh, English L1 s=0.7 | D1 | 32 (20..40) | 68% | 2.8 / 3.6 | 5.3 / 90% | — | 78 |
| zh, English L1 s=0.7 | D1S | 38 (30..40) | 28% | 3.3 / 3.6 | 6.1 / 90% | — | 82 |
| zh, English L1 s=0.7 | D1L | 39 (30..40) | 13% | 3.4 / 3.6 | 8.5 / 90% | — | 76 |
| zh, English L1 s=0.7 | D2 | 55 (26..60) | 22% | 5.1 / 6.1 | 5.5 / 95% | 5.0 / 96% | 69 |
| zh, English L1 s=0.7 | D3 | 49 (20..61) | 49% | 4.1 / 5.4 | 4.9 / 93% | 4.2 / 95% | 69 |
| zh, English L1 s=0.7 | D4 | 51 (26..60) | 40% | 4.6 / 5.7 | 4.8 / 93% | 4.6 / 95% | 68 |
| zh, English L1 s=0.7 | D3S | 53 (35..61) | 36% | 4.6 / 5.4 | 6.0 / 91% | 5.0 / 92% | 80 |
| zh, English L1 s=0.7 | D3L | 57 (35..61) | 18% | 4.7 / 5.4 | 8.9 / 88% | 6.8 / 93% | 81 |
| zh, English L1 s=0.7 | D2i | 60 (60..60) | 1% | 5.9 / 6.7 | 6.9 / 90% | 11.8 / 93% | 66 |
| zh, English L1 s=0.7 | D3i | 59 (50..61) | 8% | 5.2 / 5.7 | 5.6 / 89% | 12.2 / 91% | 66 |
| zh, English L1 s=0.7 | D4i | 60 (60..60) | 1% | 5.7 / 6.4 | 5.1 / 92% | 12.8 / 92% | 65 |
| zh, Japanese L1 (cognates) s=0.3 | D1 | 35 (20..40) | 41% | 3.0 / 3.4 | 6.3 / 91% | — | 74 |
| zh, Japanese L1 (cognates) s=0.3 | D1S | 40 (40..40) | 1% | 3.4 / 3.4 | 6.8 / 89% | — | 69 |
| zh, Japanese L1 (cognates) s=0.3 | D1L | 40 (40..40) | 0% | 3.4 / 3.4 | 10.5 / 85% | — | 59 |
| zh, Japanese L1 (cognates) s=0.3 | D2 | 60 (60..60) | 1% | 5.1 / 5.7 | 6.7 / 92% | 5.5 / 95% | 70 |
| zh, Japanese L1 (cognates) s=0.3 | D3 | 60 (60..61) | 1% | 5.1 / 5.5 | 6.1 / 91% | 5.3 / 95% | 69 |
| zh, Japanese L1 (cognates) s=0.3 | D4 | 60 (60..60) | 1% | 5.1 / 5.5 | 6.2 / 89% | 6.8 / 91% | 68 |
| zh, Japanese L1 (cognates) s=0.3 | D3S | 60 (60..61) | 0% | 5.1 / 5.5 | 7.3 / 89% | 6.7 / 90% | 80 |
| zh, Japanese L1 (cognates) s=0.3 | D3L | 60 (60..61) | 0% | 5.0 / 5.4 | 10.8 / 89% | 9.7 / 89% | 78 |
| zh, Japanese L1 (cognates) s=0.3 | D2i | 59 (60..60) | 4% | 5.1 / 5.7 | 7.0 / 91% | 7.1 / 82% | 63 |
| zh, Japanese L1 (cognates) s=0.3 | D3i | 60 (51..61) | 7% | 5.0 / 5.5 | 6.2 / 90% | 6.5 / 81% | 63 |
| zh, Japanese L1 (cognates) s=0.3 | D4i | 60 (60..60) | 1% | 5.1 / 5.5 | 5.9 / 89% | 7.8 / 85% | 63 |
| zh, Japanese L1 (cognates) s=0.7 | D1 | 35 (20..40) | 42% | 3.1 / 3.6 | 5.8 / 89% | — | 77 |
| zh, Japanese L1 (cognates) s=0.7 | D1S | 40 (40..40) | 1% | 3.5 / 3.6 | 6.4 / 89% | — | 70 |
| zh, Japanese L1 (cognates) s=0.7 | D1L | 40 (40..40) | 0% | 3.4 / 3.6 | 9.3 / 88% | — | 59 |
| zh, Japanese L1 (cognates) s=0.7 | D2 | 60 (60..60) | 1% | 5.7 / 6.5 | 6.5 / 88% | 5.3 / 94% | 70 |
| zh, Japanese L1 (cognates) s=0.7 | D3 | 60 (60..61) | 3% | 5.5 / 6.0 | 6.0 / 90% | 5.0 / 93% | 70 |
| zh, Japanese L1 (cognates) s=0.7 | D4 | 60 (60..60) | 1% | 5.6 / 6.1 | 5.7 / 92% | 6.1 / 93% | 69 |
| zh, Japanese L1 (cognates) s=0.7 | D3S | 60 (60..61) | 0% | 5.5 / 6.1 | 6.7 / 91% | 5.7 / 91% | 81 |
| zh, Japanese L1 (cognates) s=0.7 | D3L | 60 (60..61) | 0% | 5.3 / 5.9 | 10.7 / 86% | 8.4 / 91% | 79 |
| zh, Japanese L1 (cognates) s=0.7 | D2i | 59 (46..60) | 9% | 5.6 / 6.5 | 6.5 / 91% | 6.4 / 80% | 66 |
| zh, Japanese L1 (cognates) s=0.7 | D3i | 58 (45..61) | 20% | 5.2 / 6.0 | 5.9 / 89% | 6.5 / 75% | 65 |
| zh, Japanese L1 (cognates) s=0.7 | D4i | 59 (50..60) | 6% | 5.5 / 6.1 | 5.7 / 90% | 6.5 / 86% | 68 |
| ja, English L1 s=0.3 | D1 | 36 (20..40) | 39% | 3.0 / 3.4 | 5.4 / 93% | — | 78 |
| ja, English L1 s=0.3 | D1S | 40 (40..40) | 1% | 3.4 / 3.5 | 7.8 / 84% | — | 84 |
| ja, English L1 s=0.3 | D1L | 40 (40..40) | 1% | 3.4 / 3.4 | 9.3 / 85% | — | 82 |
| ja, English L1 s=0.3 | D2 | 57 (36..60) | 14% | 4.8 / 5.5 | 5.4 / 94% | 5.5 / 92% | 71 |
| ja, English L1 s=0.3 | D3 | 53 (26..61) | 36% | 4.3 / 5.1 | 5.2 / 93% | 5.5 / 90% | 74 |
| ja, English L1 s=0.3 | D4 | 55 (26..60) | 24% | 4.6 / 5.3 | 5.2 / 92% | 5.8 / 88% | 71 |
| ja, English L1 s=0.3 | D3S | 60 (50..61) | 5% | 4.9 / 5.2 | 6.8 / 89% | 5.9 / 90% | 84 |
| ja, English L1 s=0.3 | D3L | 60 (60..61) | 4% | 4.9 / 5.2 | 8.8 / 86% | 7.6 / 83% | 86 |
| ja, English L1 s=0.3 | D2i | 59 (60..60) | 4% | 5.1 / 5.8 | 6.9 / 89% | 7.2 / 92% | 71 |
| ja, English L1 s=0.3 | D3i | 58 (45..61) | 11% | 4.8 / 5.3 | 5.4 / 91% | 7.3 / 94% | 72 |
| ja, English L1 s=0.3 | D4i | 59 (50..60) | 7% | 5.0 / 5.6 | 5.6 / 90% | 7.4 / 94% | 70 |
| ja, English L1 s=0.7 | D1 | 31 (20..40) | 72% | 2.8 / 3.5 | 5.1 / 93% | — | 81 |
| ja, English L1 s=0.7 | D1S | 39 (30..40) | 17% | 3.4 / 3.6 | 6.6 / 88% | — | 88 |
| ja, English L1 s=0.7 | D1L | 39 (30..40) | 17% | 3.4 / 3.6 | 7.9 / 85% | — | 89 |
| ja, English L1 s=0.7 | D2 | 52 (26..60) | 33% | 4.9 / 6.1 | 4.9 / 95% | 5.3 / 93% | 76 |
| ja, English L1 s=0.7 | D3 | 44 (20..61) | 70% | 3.8 / 5.2 | 5.2 / 91% | 5.7 / 86% | 75 |
| ja, English L1 s=0.7 | D4 | 48 (20..60) | 54% | 4.4 / 5.7 | 4.8 / 93% | 5.5 / 90% | 76 |
| ja, English L1 s=0.7 | D3S | 53 (35..61) | 37% | 4.6 / 5.4 | 5.9 / 89% | 5.6 / 91% | 85 |
| ja, English L1 s=0.7 | D3L | 54 (30..61) | 32% | 4.5 / 5.3 | 7.8 / 86% | 7.1 / 86% | 89 |
| ja, English L1 s=0.7 | D2i | 59 (60..60) | 4% | 5.9 / 6.8 | 7.9 / 84% | 7.7 / 90% | 74 |
| ja, English L1 s=0.7 | D3i | 57 (40..61) | 20% | 5.0 / 5.7 | 5.7 / 82% | 7.3 / 89% | 73 |
| ja, English L1 s=0.7 | D4i | 58 (45..60) | 10% | 5.6 / 6.4 | 5.6 / 85% | 7.7 / 93% | 73 |
| ja, Chinese L1 (cognates) s=0.3 | D1 | 36 (20..40) | 35% | 3.0 / 3.4 | 5.7 / 91% | — | 84 |
| ja, Chinese L1 (cognates) s=0.3 | D1S | 40 (40..40) | 0% | 3.4 / 3.4 | 6.8 / 89% | — | 78 |
| ja, Chinese L1 (cognates) s=0.3 | D1L | 40 (40..40) | 0% | 3.4 / 3.4 | 9.3 / 82% | — | 73 |
| ja, Chinese L1 (cognates) s=0.3 | D2 | 59 (50..60) | 7% | 5.1 / 5.7 | 6.4 / 91% | 5.4 / 93% | 81 |
| ja, Chinese L1 (cognates) s=0.3 | D3 | 59 (46..61) | 11% | 4.9 / 5.4 | 5.8 / 89% | 5.5 / 92% | 80 |
| ja, Chinese L1 (cognates) s=0.3 | D4 | 59 (50..60) | 9% | 5.0 / 5.5 | 5.8 / 91% | 5.8 / 91% | 80 |
| ja, Chinese L1 (cognates) s=0.3 | D3S | 60 (60..61) | 0% | 5.0 / 5.4 | 7.2 / 86% | 6.8 / 88% | 87 |
| ja, Chinese L1 (cognates) s=0.3 | D3L | 60 (60..61) | 0% | 5.0 / 5.4 | 9.5 / 84% | 8.8 / 85% | 87 |
| ja, Chinese L1 (cognates) s=0.3 | D2i | 58 (40..60) | 13% | 4.9 / 5.6 | 6.1 / 96% | 5.5 / 87% | 76 |
| ja, Chinese L1 (cognates) s=0.3 | D3i | 57 (36..61) | 20% | 4.7 / 5.4 | 5.7 / 94% | 5.4 / 88% | 76 |
| ja, Chinese L1 (cognates) s=0.3 | D4i | 56 (41..60) | 21% | 4.8 / 5.4 | 6.0 / 90% | 6.3 / 84% | 76 |
| ja, Chinese L1 (cognates) s=0.7 | D1 | 35 (20..40) | 47% | 3.0 / 3.6 | 5.5 / 90% | — | 81 |
| ja, Chinese L1 (cognates) s=0.7 | D1S | 40 (40..40) | 1% | 3.5 / 3.6 | 6.7 / 89% | — | 77 |
| ja, Chinese L1 (cognates) s=0.7 | D1L | 40 (40..40) | 0% | 3.5 / 3.6 | 8.0 / 85% | — | 76 |
| ja, Chinese L1 (cognates) s=0.7 | D2 | 59 (50..60) | 10% | 5.5 / 6.4 | 5.7 / 93% | 4.7 / 96% | 77 |
| ja, Chinese L1 (cognates) s=0.7 | D3 | 56 (45..61) | 31% | 5.0 / 5.8 | 5.3 / 93% | 4.8 / 93% | 77 |
| ja, Chinese L1 (cognates) s=0.7 | D4 | 58 (45..60) | 16% | 5.3 / 6.1 | 5.6 / 88% | 5.2 / 92% | 76 |
| ja, Chinese L1 (cognates) s=0.7 | D3S | 60 (60..61) | 1% | 5.3 / 5.8 | 6.3 / 88% | 6.3 / 87% | 85 |
| ja, Chinese L1 (cognates) s=0.7 | D3L | 60 (60..61) | 1% | 5.2 / 5.8 | 8.1 / 87% | 7.4 / 89% | 87 |
| ja, Chinese L1 (cognates) s=0.7 | D2i | 57 (40..60) | 19% | 5.3 / 6.4 | 5.9 / 93% | 5.5 / 80% | 74 |
| ja, Chinese L1 (cognates) s=0.7 | D3i | 54 (35..61) | 35% | 4.8 / 5.8 | 5.6 / 92% | 5.4 / 82% | 73 |
| ja, Chinese L1 (cognates) s=0.7 | D4i | 54 (35..60) | 35% | 4.9 / 6.0 | 5.3 / 92% | 6.0 / 83% | 73 |

### h = 0.08, min 20, cap 60 (meaning-only) / 90 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.3 | D1 | 59 (45..60) | 7% | 4.9 / 5.2 | 4.9 / 90% | — | 77 |
| zh, English L1 s=0.3 | D1S | 60 (60..60) | 0% | 5.0 / 5.2 | 6.0 / 88% | — | 80 |
| zh, English L1 s=0.3 | D1L | 60 (60..60) | 0% | 5.0 / 5.2 | 7.9 / 87% | — | 75 |
| zh, English L1 s=0.3 | D2 | 90 (90..90) | 2% | 7.6 / 8.3 | 5.5 / 90% | 4.4 / 96% | 69 |
| zh, English L1 s=0.3 | D3 | 88 (70..91) | 8% | 7.2 / 7.8 | 4.6 / 90% | 3.8 / 96% | 69 |
| zh, English L1 s=0.3 | D4 | 89 (90..90) | 5% | 7.5 / 8.1 | 4.6 / 91% | 4.2 / 94% | 69 |
| zh, English L1 s=0.3 | D3S | 90 (90..91) | 0% | 7.4 / 7.9 | 5.6 / 87% | 4.5 / 89% | 80 |
| zh, English L1 s=0.3 | D3L | 90 (90..91) | 0% | 7.3 / 7.9 | 8.1 / 89% | 6.2 / 90% | 87 |
| zh, English L1 s=0.3 | D2i | 90 (90..90) | 0% | 7.8 / 8.7 | 6.2 / 89% | 11.2 / 94% | 67 |
| zh, English L1 s=0.3 | D3i | 90 (90..91) | 0% | 7.4 / 7.9 | 5.3 / 89% | 11.3 / 91% | 69 |
| zh, English L1 s=0.3 | D4i | 90 (90..90) | 0% | 7.7 / 8.3 | 5.0 / 88% | 11.8 / 96% | 67 |
| zh, English L1 s=0.7 | D1 | 56 (35..60) | 16% | 5.0 / 5.5 | 4.2 / 91% | — | 79 |
| zh, English L1 s=0.7 | D1S | 60 (60..60) | 3% | 5.3 / 5.5 | 4.9 / 89% | — | 84 |
| zh, English L1 s=0.7 | D1L | 59 (50..60) | 5% | 5.2 / 5.5 | 6.6 / 86% | — | 76 |
| zh, English L1 s=0.7 | D2 | 88 (70..90) | 7% | 8.3 / 9.5 | 4.4 / 96% | 4.0 / 96% | 70 |
| zh, English L1 s=0.7 | D3 | 84 (45..91) | 22% | 7.2 / 8.2 | 4.0 / 93% | 3.6 / 95% | 71 |
| zh, English L1 s=0.7 | D4 | 86 (60..90) | 15% | 7.9 / 9.0 | 3.9 / 94% | 3.8 / 96% | 70 |
| zh, English L1 s=0.7 | D3S | 86 (60..91) | 17% | 7.5 / 8.3 | 4.6 / 89% | 3.8 / 91% | 80 |
| zh, English L1 s=0.7 | D3L | 88 (70..91) | 10% | 7.4 / 8.2 | 7.0 / 88% | 5.3 / 91% | 85 |
| zh, English L1 s=0.7 | D2i | 90 (90..90) | 0% | 8.9 / 10.1 | 6.0 / 91% | 11.5 / 92% | 67 |
| zh, English L1 s=0.7 | D3i | 90 (90..91) | 1% | 7.9 / 8.6 | 4.8 / 88% | 11.2 / 90% | 68 |
| zh, English L1 s=0.7 | D4i | 90 (90..90) | 0% | 8.6 / 9.6 | 4.4 / 90% | 12.2 / 92% | 68 |
| zh, Japanese L1 (cognates) s=0.3 | D1 | 58 (40..60) | 12% | 4.8 / 5.2 | 5.3 / 90% | — | 78 |
| zh, Japanese L1 (cognates) s=0.3 | D1S | 60 (60..60) | 0% | 5.0 / 5.1 | 5.6 / 89% | — | 71 |
| zh, Japanese L1 (cognates) s=0.3 | D1L | 60 (60..60) | 0% | 5.0 / 5.1 | 7.9 / 85% | — | 59 |
| zh, Japanese L1 (cognates) s=0.3 | D2 | 90 (90..90) | 0% | 7.7 / 8.6 | 5.8 / 91% | 4.7 / 94% | 71 |
| zh, Japanese L1 (cognates) s=0.3 | D3 | 90 (90..91) | 0% | 7.6 / 8.3 | 5.2 / 91% | 4.1 / 94% | 69 |
| zh, Japanese L1 (cognates) s=0.3 | D4 | 90 (90..90) | 0% | 7.7 / 8.2 | 5.3 / 89% | 5.8 / 91% | 69 |
| zh, Japanese L1 (cognates) s=0.3 | D3S | 90 (90..91) | 0% | 7.6 / 8.2 | 5.7 / 90% | 5.4 / 90% | 82 |
| zh, Japanese L1 (cognates) s=0.3 | D3L | 90 (90..91) | 0% | 7.4 / 8.1 | 8.5 / 86% | 7.5 / 89% | 81 |
| zh, Japanese L1 (cognates) s=0.3 | D2i | 90 (90..90) | 0% | 7.7 / 8.5 | 5.9 / 88% | 5.9 / 83% | 63 |
| zh, Japanese L1 (cognates) s=0.3 | D3i | 90 (90..91) | 0% | 7.6 / 8.2 | 5.4 / 89% | 5.4 / 82% | 65 |
| zh, Japanese L1 (cognates) s=0.3 | D4i | 90 (90..90) | 0% | 7.6 / 8.2 | 5.1 / 87% | 6.3 / 86% | 64 |
| zh, Japanese L1 (cognates) s=0.7 | D1 | 58 (45..60) | 8% | 5.1 / 5.4 | 4.7 / 90% | — | 79 |
| zh, Japanese L1 (cognates) s=0.7 | D1S | 60 (60..60) | 0% | 5.2 / 5.4 | 5.0 / 89% | — | 73 |
| zh, Japanese L1 (cognates) s=0.7 | D1L | 60 (60..60) | 0% | 5.2 / 5.3 | 7.6 / 85% | — | 59 |
| zh, Japanese L1 (cognates) s=0.7 | D2 | 90 (90..90) | 0% | 8.6 / 9.7 | 5.7 / 89% | 4.5 / 93% | 70 |
| zh, Japanese L1 (cognates) s=0.7 | D3 | 90 (90..91) | 0% | 8.2 / 9.0 | 4.9 / 90% | 4.1 / 93% | 71 |
| zh, Japanese L1 (cognates) s=0.7 | D4 | 90 (90..90) | 0% | 8.3 / 9.1 | 4.5 / 91% | 5.2 / 94% | 70 |
| zh, Japanese L1 (cognates) s=0.7 | D3S | 90 (90..91) | 0% | 8.2 / 9.0 | 5.3 / 90% | 4.5 / 90% | 81 |
| zh, Japanese L1 (cognates) s=0.7 | D3L | 90 (90..91) | 0% | 7.9 / 8.9 | 7.9 / 89% | 6.3 / 89% | 83 |
| zh, Japanese L1 (cognates) s=0.7 | D2i | 90 (90..90) | 0% | 8.6 / 9.7 | 5.6 / 90% | 5.1 / 81% | 67 |
| zh, Japanese L1 (cognates) s=0.7 | D3i | 90 (90..91) | 1% | 8.2 / 9.0 | 4.8 / 90% | 5.2 / 74% | 66 |
| zh, Japanese L1 (cognates) s=0.7 | D4i | 90 (90..90) | 0% | 8.3 / 9.1 | 4.8 / 89% | 5.5 / 86% | 68 |
| ja, English L1 s=0.3 | D1 | 59 (60..60) | 5% | 4.9 / 5.2 | 4.9 / 90% | — | 79 |
| ja, English L1 s=0.3 | D1S | 60 (60..60) | 0% | 5.0 / 5.2 | 6.3 / 85% | — | 84 |
| ja, English L1 s=0.3 | D1L | 60 (60..60) | 0% | 5.0 / 5.2 | 7.2 / 86% | — | 84 |
| ja, English L1 s=0.3 | D2 | 89 (90..90) | 3% | 7.6 / 8.4 | 5.0 / 91% | 5.1 / 89% | 73 |
| ja, English L1 s=0.3 | D3 | 88 (70..91) | 9% | 7.2 / 7.8 | 4.5 / 91% | 4.8 / 88% | 75 |
| ja, English L1 s=0.3 | D4 | 89 (90..90) | 5% | 7.5 / 8.1 | 4.6 / 92% | 5.3 / 86% | 72 |
| ja, English L1 s=0.3 | D3S | 90 (90..91) | 0% | 7.4 / 7.8 | 5.8 / 86% | 5.0 / 87% | 85 |
| ja, English L1 s=0.3 | D3L | 90 (90..91) | 0% | 7.3 / 7.8 | 6.7 / 86% | 5.8 / 87% | 89 |
| ja, English L1 s=0.3 | D2i | 90 (90..90) | 1% | 7.8 / 8.7 | 6.3 / 86% | 6.4 / 94% | 71 |
| ja, English L1 s=0.3 | D3i | 90 (90..91) | 1% | 7.4 / 7.9 | 5.0 / 86% | 6.5 / 95% | 74 |
| ja, English L1 s=0.3 | D4i | 90 (90..90) | 0% | 7.7 / 8.3 | 5.0 / 88% | 6.8 / 95% | 72 |
| ja, English L1 s=0.7 | D1 | 56 (30..60) | 19% | 4.9 / 5.5 | 4.5 / 90% | — | 82 |
| ja, English L1 s=0.7 | D1S | 60 (60..60) | 2% | 5.3 / 5.5 | 5.0 / 89% | — | 89 |
| ja, English L1 s=0.7 | D1L | 60 (60..60) | 2% | 5.3 / 5.5 | 6.1 / 84% | — | 92 |
| ja, English L1 s=0.7 | D2 | 86 (60..90) | 13% | 8.1 / 9.5 | 4.8 / 89% | 5.3 / 85% | 77 |
| ja, English L1 s=0.7 | D3 | 80 (35..91) | 32% | 6.9 / 8.1 | 4.7 / 85% | 5.1 / 83% | 76 |
| ja, English L1 s=0.7 | D4 | 83 (45..90) | 21% | 7.7 / 9.0 | 4.7 / 85% | 5.1 / 80% | 78 |
| ja, English L1 s=0.7 | D3S | 87 (70..91) | 17% | 7.5 / 8.2 | 4.7 / 87% | 4.2 / 88% | 87 |
| ja, English L1 s=0.7 | D3L | 87 (60..91) | 15% | 7.4 / 8.2 | 5.8 / 84% | 5.4 / 85% | 90 |
| ja, English L1 s=0.7 | D2i | 90 (90..90) | 1% | 8.9 / 10.2 | 7.2 / 80% | 6.9 / 91% | 76 |
| ja, English L1 s=0.7 | D3i | 90 (90..91) | 2% | 7.8 / 8.5 | 5.1 / 79% | 6.5 / 92% | 78 |
| ja, English L1 s=0.7 | D4i | 90 (90..90) | 1% | 8.6 / 9.5 | 5.0 / 80% | 7.1 / 92% | 74 |
| ja, Chinese L1 (cognates) s=0.3 | D1 | 59 (50..60) | 7% | 4.9 / 5.1 | 4.8 / 92% | — | 85 |
| ja, Chinese L1 (cognates) s=0.3 | D1S | 60 (60..60) | 0% | 5.0 / 5.1 | 5.7 / 87% | — | 80 |
| ja, Chinese L1 (cognates) s=0.3 | D1L | 60 (60..60) | 0% | 5.0 / 5.1 | 7.1 / 85% | — | 76 |
| ja, Chinese L1 (cognates) s=0.3 | D2 | 90 (90..90) | 0% | 7.7 / 8.5 | 5.7 / 90% | 4.7 / 92% | 81 |
| ja, Chinese L1 (cognates) s=0.3 | D3 | 90 (90..91) | 1% | 7.5 / 8.0 | 4.9 / 89% | 4.7 / 91% | 81 |
| ja, Chinese L1 (cognates) s=0.3 | D4 | 90 (90..90) | 0% | 7.6 / 8.2 | 4.9 / 89% | 4.7 / 92% | 81 |
| ja, Chinese L1 (cognates) s=0.3 | D3S | 90 (90..91) | 0% | 7.5 / 8.0 | 5.9 / 87% | 5.6 / 87% | 87 |
| ja, Chinese L1 (cognates) s=0.3 | D3L | 90 (90..91) | 0% | 7.5 / 8.0 | 7.4 / 82% | 6.8 / 85% | 89 |
| ja, Chinese L1 (cognates) s=0.3 | D2i | 90 (90..90) | 2% | 7.6 / 8.4 | 5.2 / 92% | 4.4 / 87% | 78 |
| ja, Chinese L1 (cognates) s=0.3 | D3i | 90 (90..91) | 5% | 7.5 / 8.1 | 4.9 / 93% | 4.4 / 86% | 78 |
| ja, Chinese L1 (cognates) s=0.3 | D4i | 90 (90..90) | 2% | 7.6 / 8.1 | 4.9 / 90% | 5.1 / 85% | 77 |
| ja, Chinese L1 (cognates) s=0.7 | D1 | 59 (45..60) | 8% | 5.1 / 5.4 | 4.5 / 93% | — | 84 |
| ja, Chinese L1 (cognates) s=0.7 | D1S | 60 (60..60) | 0% | 5.2 / 5.4 | 5.3 / 88% | — | 78 |
| ja, Chinese L1 (cognates) s=0.7 | D1L | 60 (60..60) | 0% | 5.2 / 5.4 | 6.4 / 85% | — | 77 |
| ja, Chinese L1 (cognates) s=0.7 | D2 | 90 (90..90) | 0% | 8.5 / 9.5 | 4.7 / 92% | 4.0 / 95% | 77 |
| ja, Chinese L1 (cognates) s=0.7 | D3 | 90 (90..91) | 1% | 8.0 / 8.7 | 4.6 / 88% | 4.1 / 93% | 77 |
| ja, Chinese L1 (cognates) s=0.7 | D4 | 90 (90..90) | 1% | 8.2 / 9.0 | 4.6 / 90% | 4.5 / 91% | 78 |
| ja, Chinese L1 (cognates) s=0.7 | D3S | 90 (90..91) | 0% | 7.9 / 8.6 | 5.0 / 90% | 5.2 / 89% | 87 |
| ja, Chinese L1 (cognates) s=0.7 | D3L | 90 (90..91) | 0% | 7.9 / 8.7 | 6.4 / 86% | 5.7 / 89% | 88 |
| ja, Chinese L1 (cognates) s=0.7 | D2i | 89 (90..90) | 4% | 8.3 / 9.5 | 5.2 / 89% | 4.6 / 79% | 75 |
| ja, Chinese L1 (cognates) s=0.7 | D3i | 89 (81..91) | 7% | 7.9 / 8.6 | 4.4 / 92% | 4.3 / 79% | 74 |
| ja, Chinese L1 (cognates) s=0.7 | D4i | 89 (80..90) | 6% | 8.1 / 9.0 | 4.3 / 93% | 4.6 / 83% | 74 |

### h = 0.1, min 20, cap 60 (meaning-only) / 90 (with readings)

| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|
| zh, English L1 s=0.3 | D1 | 54 (35..60) | 29% | 4.6 / 5.2 | 4.9 / 90% | — | 77 |
| zh, English L1 s=0.3 | D1S | 59 (60..60) | 5% | 5.0 / 5.2 | 6.0 / 88% | — | 80 |
| zh, English L1 s=0.3 | D1L | 60 (60..60) | 2% | 5.0 / 5.2 | 7.9 / 87% | — | 75 |
| zh, English L1 s=0.3 | D2 | 88 (70..90) | 10% | 7.4 / 8.3 | 5.4 / 90% | 4.4 / 96% | 69 |
| zh, English L1 s=0.3 | D3 | 82 (40..91) | 28% | 6.7 / 7.7 | 4.7 / 90% | 3.9 / 96% | 69 |
| zh, English L1 s=0.3 | D4 | 85 (50..90) | 18% | 7.1 / 8.0 | 4.6 / 91% | 4.3 / 94% | 69 |
| zh, English L1 s=0.3 | D3S | 88 (71..91) | 13% | 7.2 / 7.8 | 5.7 / 88% | 4.5 / 89% | 80 |
| zh, English L1 s=0.3 | D3L | 90 (80..91) | 6% | 7.2 / 7.8 | 8.2 / 89% | 6.2 / 90% | 87 |
| zh, English L1 s=0.3 | D2i | 90 (90..90) | 1% | 7.8 / 8.7 | 6.2 / 89% | 11.2 / 94% | 66 |
| zh, English L1 s=0.3 | D3i | 90 (90..91) | 4% | 7.4 / 7.9 | 5.3 / 89% | 11.3 / 91% | 69 |
| zh, English L1 s=0.3 | D4i | 90 (90..90) | 0% | 7.7 / 8.3 | 5.0 / 88% | 11.8 / 96% | 67 |
| zh, English L1 s=0.7 | D1 | 47 (20..60) | 61% | 4.2 / 5.4 | 4.5 / 90% | — | 79 |
| zh, English L1 s=0.7 | D1S | 55 (40..60) | 31% | 4.9 / 5.4 | 5.3 / 89% | — | 84 |
| zh, English L1 s=0.7 | D1L | 57 (40..60) | 15% | 5.0 / 5.4 | 6.7 / 86% | — | 76 |
| zh, English L1 s=0.7 | D2 | 82 (40..90) | 26% | 7.7 / 9.0 | 4.5 / 96% | 4.1 / 96% | 70 |
| zh, English L1 s=0.7 | D3 | 72 (30..91) | 59% | 6.2 / 7.8 | 4.3 / 94% | 3.8 / 96% | 71 |
| zh, English L1 s=0.7 | D4 | 76 (30..90) | 48% | 6.9 / 8.5 | 4.2 / 93% | 3.9 / 96% | 70 |
| zh, English L1 s=0.7 | D3S | 78 (40..91) | 43% | 6.7 / 8.0 | 4.9 / 89% | 4.0 / 93% | 80 |
| zh, English L1 s=0.7 | D3L | 83 (45..91) | 24% | 7.0 / 8.0 | 7.1 / 88% | 5.4 / 91% | 85 |
| zh, English L1 s=0.7 | D2i | 90 (90..90) | 2% | 8.9 / 10.1 | 6.0 / 91% | 11.5 / 92% | 67 |
| zh, English L1 s=0.7 | D3i | 88 (70..91) | 14% | 7.7 / 8.5 | 4.9 / 88% | 11.4 / 91% | 68 |
| zh, English L1 s=0.7 | D4i | 90 (90..90) | 2% | 8.6 / 9.6 | 4.4 / 90% | 12.2 / 92% | 68 |
| zh, Japanese L1 (cognates) s=0.3 | D1 | 53 (25..60) | 32% | 4.4 / 5.1 | 5.4 / 90% | — | 77 |
| zh, Japanese L1 (cognates) s=0.3 | D1S | 59 (50..60) | 7% | 5.0 / 5.1 | 5.6 / 88% | — | 71 |
| zh, Japanese L1 (cognates) s=0.3 | D1L | 60 (60..60) | 0% | 5.0 / 5.1 | 8.0 / 85% | — | 59 |
| zh, Japanese L1 (cognates) s=0.3 | D2 | 90 (90..90) | 2% | 7.7 / 8.6 | 5.8 / 91% | 4.7 / 94% | 71 |
| zh, Japanese L1 (cognates) s=0.3 | D3 | 90 (90..91) | 0% | 7.6 / 8.3 | 5.2 / 91% | 4.1 / 94% | 69 |
| zh, Japanese L1 (cognates) s=0.3 | D4 | 90 (90..90) | 1% | 7.6 / 8.2 | 5.3 / 89% | 5.8 / 91% | 69 |
| zh, Japanese L1 (cognates) s=0.3 | D3S | 90 (90..91) | 0% | 7.6 / 8.2 | 5.7 / 90% | 5.4 / 90% | 82 |
| zh, Japanese L1 (cognates) s=0.3 | D3L | 90 (90..91) | 0% | 7.4 / 8.1 | 8.5 / 86% | 7.5 / 89% | 81 |
| zh, Japanese L1 (cognates) s=0.3 | D2i | 89 (80..90) | 7% | 7.6 / 8.5 | 5.9 / 89% | 5.9 / 83% | 63 |
| zh, Japanese L1 (cognates) s=0.3 | D3i | 89 (80..91) | 11% | 7.5 / 8.2 | 5.4 / 89% | 5.4 / 82% | 65 |
| zh, Japanese L1 (cognates) s=0.3 | D4i | 90 (90..90) | 1% | 7.6 / 8.2 | 5.1 / 87% | 6.3 / 86% | 64 |
| zh, Japanese L1 (cognates) s=0.7 | D1 | 53 (30..60) | 37% | 4.6 / 5.4 | 4.9 / 90% | — | 78 |
| zh, Japanese L1 (cognates) s=0.7 | D1S | 60 (60..60) | 4% | 5.2 / 5.4 | 5.0 / 89% | — | 73 |
| zh, Japanese L1 (cognates) s=0.7 | D1L | 60 (60..60) | 0% | 5.2 / 5.3 | 7.6 / 85% | — | 59 |
| zh, Japanese L1 (cognates) s=0.7 | D2 | 90 (90..90) | 2% | 8.6 / 9.7 | 5.7 / 89% | 4.5 / 93% | 70 |
| zh, Japanese L1 (cognates) s=0.7 | D3 | 90 (90..91) | 5% | 8.2 / 9.0 | 4.9 / 89% | 4.1 / 93% | 71 |
| zh, Japanese L1 (cognates) s=0.7 | D4 | 90 (90..90) | 1% | 8.3 / 9.1 | 4.5 / 91% | 5.2 / 93% | 70 |
| zh, Japanese L1 (cognates) s=0.7 | D3S | 90 (90..91) | 1% | 8.2 / 9.0 | 5.3 / 90% | 4.5 / 90% | 81 |
| zh, Japanese L1 (cognates) s=0.7 | D3L | 90 (90..91) | 0% | 7.9 / 8.9 | 7.9 / 89% | 6.3 / 89% | 83 |
| zh, Japanese L1 (cognates) s=0.7 | D2i | 88 (80..90) | 14% | 8.4 / 9.7 | 5.7 / 91% | 5.2 / 81% | 66 |
| zh, Japanese L1 (cognates) s=0.7 | D3i | 86 (70..91) | 26% | 7.8 / 9.0 | 4.8 / 90% | 5.3 / 74% | 66 |
| zh, Japanese L1 (cognates) s=0.7 | D4i | 89 (80..90) | 8% | 8.2 / 9.1 | 4.8 / 89% | 5.5 / 85% | 68 |
| ja, English L1 s=0.3 | D1 | 54 (30..60) | 31% | 4.5 / 5.1 | 5.0 / 91% | — | 79 |
| ja, English L1 s=0.3 | D1S | 60 (60..60) | 1% | 5.0 / 5.2 | 6.4 / 85% | — | 84 |
| ja, English L1 s=0.3 | D1L | 60 (60..60) | 0% | 5.0 / 5.2 | 7.2 / 86% | — | 84 |
| ja, English L1 s=0.3 | D2 | 87 (70..90) | 12% | 7.4 / 8.3 | 5.0 / 91% | 5.1 / 89% | 73 |
| ja, English L1 s=0.3 | D3 | 79 (40..91) | 39% | 6.5 / 7.6 | 4.6 / 91% | 4.9 / 90% | 74 |
| ja, English L1 s=0.3 | D4 | 84 (60..90) | 28% | 7.0 / 8.0 | 4.6 / 92% | 5.3 / 87% | 71 |
| ja, English L1 s=0.3 | D3S | 89 (80..91) | 11% | 7.2 / 7.7 | 5.9 / 86% | 5.0 / 87% | 85 |
| ja, English L1 s=0.3 | D3L | 89 (80..91) | 7% | 7.2 / 7.8 | 6.9 / 85% | 5.9 / 86% | 89 |
| ja, English L1 s=0.3 | D2i | 89 (90..90) | 4% | 7.7 / 8.7 | 6.3 / 86% | 6.5 / 94% | 71 |
| ja, English L1 s=0.3 | D3i | 88 (70..91) | 12% | 7.2 / 7.9 | 5.0 / 86% | 6.6 / 95% | 73 |
| ja, English L1 s=0.3 | D4i | 89 (80..90) | 5% | 7.6 / 8.3 | 5.0 / 88% | 6.8 / 96% | 72 |
| ja, English L1 s=0.7 | D1 | 46 (20..60) | 65% | 4.0 / 5.4 | 4.6 / 91% | — | 81 |
| ja, English L1 s=0.7 | D1S | 57 (40..60) | 21% | 5.0 / 5.5 | 5.3 / 89% | — | 89 |
| ja, English L1 s=0.7 | D1L | 57 (40..60) | 17% | 5.0 / 5.5 | 6.3 / 85% | — | 92 |
| ja, English L1 s=0.7 | D2 | 79 (30..90) | 37% | 7.4 / 9.1 | 4.7 / 92% | 5.1 / 88% | 77 |
| ja, English L1 s=0.7 | D3 | 65 (25..90) | 81% | 5.5 / 7.7 | 4.8 / 89% | 5.2 / 86% | 75 |
| ja, English L1 s=0.7 | D4 | 71 (30..90) | 65% | 6.5 / 8.4 | 4.6 / 90% | 5.2 / 85% | 77 |
| ja, English L1 s=0.7 | D3S | 77 (45..91) | 48% | 6.6 / 7.9 | 5.0 / 89% | 4.5 / 87% | 87 |
| ja, English L1 s=0.7 | D3L | 79 (40..91) | 38% | 6.6 / 7.8 | 6.3 / 84% | 5.7 / 86% | 90 |
| ja, English L1 s=0.7 | D2i | 89 (80..90) | 6% | 8.8 / 10.2 | 7.2 / 80% | 6.9 / 91% | 76 |
| ja, English L1 s=0.7 | D3i | 85 (60..91) | 22% | 7.5 / 8.5 | 5.2 / 79% | 6.7 / 91% | 76 |
| ja, English L1 s=0.7 | D4i | 88 (71..90) | 10% | 8.4 / 9.5 | 5.1 / 80% | 7.2 / 93% | 74 |
| ja, Chinese L1 (cognates) s=0.3 | D1 | 54 (30..60) | 27% | 4.6 / 5.1 | 4.9 / 92% | — | 86 |
| ja, Chinese L1 (cognates) s=0.3 | D1S | 60 (60..60) | 2% | 5.0 / 5.1 | 5.7 / 87% | — | 80 |
| ja, Chinese L1 (cognates) s=0.3 | D1L | 60 (60..60) | 1% | 5.0 / 5.1 | 7.1 / 85% | — | 76 |
| ja, Chinese L1 (cognates) s=0.3 | D2 | 89 (80..90) | 7% | 7.6 / 8.5 | 5.7 / 90% | 4.8 / 91% | 81 |
| ja, Chinese L1 (cognates) s=0.3 | D3 | 88 (71..91) | 13% | 7.4 / 8.0 | 4.9 / 90% | 4.7 / 92% | 81 |
| ja, Chinese L1 (cognates) s=0.3 | D4 | 88 (71..90) | 10% | 7.5 / 8.2 | 4.9 / 89% | 4.7 / 92% | 82 |
| ja, Chinese L1 (cognates) s=0.3 | D3S | 90 (90..91) | 1% | 7.5 / 8.0 | 5.9 / 87% | 5.6 / 87% | 87 |
| ja, Chinese L1 (cognates) s=0.3 | D3L | 90 (90..91) | 0% | 7.5 / 8.0 | 7.4 / 82% | 6.8 / 85% | 89 |
| ja, Chinese L1 (cognates) s=0.3 | D2i | 86 (60..90) | 14% | 7.4 / 8.4 | 5.3 / 92% | 4.5 / 87% | 76 |
| ja, Chinese L1 (cognates) s=0.3 | D3i | 85 (60..91) | 23% | 7.1 / 8.1 | 4.9 / 93% | 4.5 / 85% | 77 |
| ja, Chinese L1 (cognates) s=0.3 | D4i | 85 (60..90) | 23% | 7.2 / 8.1 | 5.0 / 91% | 5.4 / 85% | 77 |
| ja, Chinese L1 (cognates) s=0.7 | D1 | 52 (30..60) | 43% | 4.5 / 5.4 | 4.8 / 93% | — | 83 |
| ja, Chinese L1 (cognates) s=0.7 | D1S | 60 (60..60) | 5% | 5.2 / 5.4 | 5.3 / 88% | — | 78 |
| ja, Chinese L1 (cognates) s=0.7 | D1L | 60 (60..60) | 1% | 5.2 / 5.4 | 6.5 / 85% | — | 77 |
| ja, Chinese L1 (cognates) s=0.7 | D2 | 88 (80..90) | 12% | 8.3 / 9.5 | 4.8 / 93% | 4.1 / 95% | 79 |
| ja, Chinese L1 (cognates) s=0.7 | D3 | 85 (70..91) | 35% | 7.5 / 8.7 | 4.6 / 89% | 4.2 / 93% | 77 |
| ja, Chinese L1 (cognates) s=0.7 | D4 | 87 (71..90) | 18% | 8.0 / 9.0 | 4.6 / 90% | 4.5 / 91% | 77 |
| ja, Chinese L1 (cognates) s=0.7 | D3S | 90 (90..91) | 4% | 7.9 / 8.6 | 5.0 / 90% | 5.2 / 89% | 87 |
| ja, Chinese L1 (cognates) s=0.7 | D3L | 90 (90..91) | 2% | 7.8 / 8.6 | 6.4 / 86% | 5.7 / 89% | 88 |
| ja, Chinese L1 (cognates) s=0.7 | D2i | 85 (60..90) | 21% | 8.0 / 9.5 | 5.3 / 90% | 4.7 / 79% | 74 |
| ja, Chinese L1 (cognates) s=0.7 | D3i | 81 (51..91) | 41% | 7.2 / 8.6 | 4.6 / 91% | 4.5 / 80% | 75 |
| ja, Chinese L1 (cognates) s=0.7 | D4i | 81 (60..90) | 38% | 7.4 / 9.0 | 4.3 / 93% | 4.9 / 81% | 74 |

## By ability (budget snapshot), all populations of a language pooled

Ability groups by the learner's study frontier tau (Zipf at 50% known): beginner tau >= 5.5, intermediate 4.0-5.5, advanced < 4.0.

| lang | design | group | n learners | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|
| zh | D0 | beginner | 702 | 5.5 / 89% | — | 99 |
| zh | D0 | intermediate | 669 | 5.4 / 90% | — | 66 |
| zh | D0 | advanced | 629 | 4.4 / 93% | — | 74 |
| zh | D1 | beginner | 702 | 6.0 / 90% | — | 99 |
| zh | D1 | intermediate | 669 | 5.5 / 91% | — | 68 |
| zh | D1 | advanced | 629 | 5.2 / 91% | — | 65 |
| zh | D1S | beginner | 702 | 7.2 / 86% | — | 97 |
| zh | D1S | intermediate | 669 | 6.9 / 88% | — | 58 |
| zh | D1S | advanced | 629 | 5.3 / 93% | — | 70 |
| zh | D3 | beginner | 702 | 5.7 / 90% | 4.1 / 94% | 100 |
| zh | D3 | intermediate | 669 | 5.5 / 92% | 4.6 / 96% | 72 |
| zh | D3 | advanced | 629 | 5.3 / 92% | 5.5 / 94% | 32 |
| zh | D3S | beginner | 702 | 6.7 / 88% | 4.4 / 93% | 100 |
| zh | D3S | intermediate | 669 | 7.0 / 88% | 6.4 / 87% | 74 |
| zh | D3S | advanced | 629 | 6.0 / 94% | 6.4 / 92% | 64 |
| zh | D3L | beginner | 702 | 8.5 / 89% | 5.4 / 95% | 99 |
| zh | D3L | intermediate | 669 | 11.0 / 84% | 8.2 / 90% | 75 |
| zh | D3L | advanced | 629 | 11.0 / 89% | 10.9 / 87% | 66 |
| ja | D0 | beginner | 685 | 5.6 / 88% | — | 100 |
| ja | D0 | intermediate | 638 | 5.6 / 88% | — | 90 |
| ja | D0 | advanced | 677 | 4.7 / 93% | — | 63 |
| ja | D1 | beginner | 685 | 5.4 / 89% | — | 100 |
| ja | D1 | intermediate | 638 | 5.2 / 93% | — | 92 |
| ja | D1 | advanced | 677 | 5.3 / 91% | — | 53 |
| ja | D1S | beginner | 685 | 7.2 / 87% | — | 99 |
| ja | D1S | intermediate | 638 | 7.2 / 87% | — | 86 |
| ja | D1S | advanced | 677 | 6.4 / 88% | — | 60 |
| ja | D3 | beginner | 685 | 5.4 / 88% | 4.7 / 88% | 100 |
| ja | D3 | intermediate | 638 | 5.6 / 91% | 5.3 / 90% | 96 |
| ja | D3 | advanced | 677 | 5.2 / 89% | 5.9 / 88% | 33 |
| ja | D3S | beginner | 685 | 6.7 / 86% | 5.7 / 86% | 100 |
| ja | D3S | intermediate | 638 | 6.8 / 87% | 6.1 / 88% | 96 |
| ja | D3S | advanced | 677 | 5.7 / 92% | 6.2 / 91% | 60 |
| ja | D3L | beginner | 685 | 7.2 / 85% | 6.1 / 87% | 100 |
| ja | D3L | intermediate | 638 | 9.2 / 84% | 8.2 / 84% | 92 |
| ja | D3L | advanced | 677 | 8.7 / 87% | 8.6 / 85% | 70 |
