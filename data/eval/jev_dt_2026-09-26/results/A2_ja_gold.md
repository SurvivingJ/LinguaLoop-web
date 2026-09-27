# A2 / ja / gold

| dim | n | QWK | 95% CI | exact |
|---|---|---|---|---|
| accuracy | 29 | 0.147 | [0.000, 0.465] | 72.4% |
| fidelity | 29 | 0.575 | [0.437, 0.773] | 79.3% |
| understandability | 29 | 0.000 | [0.000, 0.000] | 82.8% |

Error detection: AUC=0.745 P=0.60 R=0.75 F1=0.67 (tp=12 fp=8 fn=4 tn=11)

Subtype accuracy (n=12): top1=75.0% top3=91.7%

meaning_changed AUC vs gold severity>=major: 0.926

Cost: $0.003174 total, $0.000091/call, n_calls=35, n_skipped=78
Latency: mean=0.31s p95=0.39s
