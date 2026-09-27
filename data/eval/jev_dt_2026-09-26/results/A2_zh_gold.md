# A2 / zh / gold

| dim | n | QWK | 95% CI | exact |
|---|---|---|---|---|
| accuracy | 29 | -0.066 | [-0.189, 0.000] | 65.5% |
| fidelity | 29 | 0.448 | [-0.090, 0.590] | 75.9% |
| understandability | 29 | 0.379 | [0.000, 1.000] | 89.7% |

Error detection: AUC=0.551 P=0.27 R=0.44 F1=0.33 (tp=4 fp=11 fn=5 tn=12)

Subtype accuracy (n=4): top1=25.0% top3=75.0%

meaning_changed AUC vs gold severity>=major: 0.907

Cost: $0.002463 total, $0.000077/call, n_calls=32, n_skipped=80
Latency: mean=0.33s p95=0.62s
