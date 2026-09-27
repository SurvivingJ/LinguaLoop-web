# A1 / ja / gold

| dim | n | QWK | 95% CI | exact |
|---|---|---|---|---|
| accuracy | 30 | 0.149 | [0.000, 0.444] | 73.3% |
| fidelity | 30 | 0.541 | [0.380, 0.701] | 76.7% |
| understandability | 30 | 0.000 | [0.000, 0.000] | 83.3% |

Error detection: AUC=0.950 P=1.00 R=0.65 F1=0.79 (tp=13 fp=0 fn=7 tn=10)

Subtype accuracy (n=13): top1=69.2% top3=84.6%

meaning_changed AUC vs gold severity>=major: 0.956

Cost: $0.002369 total, $0.000079/call, n_calls=30, n_skipped=0
Latency: mean=0.29s p95=0.34s
