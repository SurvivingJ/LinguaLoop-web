# DT Grading Eval — v2 (ZH)

- **Run date:** 2026-10-08
- **L2 / L1:** zh / en
- **Items graded:** 30 (clean 10 / single 15 / multi 5)
- **Grader:** v2 Detector/Verifier cascade (`grade_submission(framework_v2=True)`), slugs: qwen/qwen3.6-flash, qwen/qwen3.7-plus
- **Fixture set:** v5
- **Taxonomy:** live (active DB row, or the DT_TAXONOMY_VERSION pin)
- **Tokens:** 87,712 in / 193,660 out — model calls: 56
- **Est. cost:** $0.2517 USD (model-arena pricing)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 0.957 | 0.846 | 0.898 | 22 | 1 | 4 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.864 (19/22) |
| Severity exact (triad minor/major/critical) | 0.636 (n=22) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.100 (10 clean items) |
| Clean-passage mean spurious errors/item | 0.100 (1 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.683 | 0.867 | 1.000 | 30 |
| understandability | 0.695 | 0.900 | 0.967 | 30 |
| fidelity | 0.794 | 0.800 | 0.967 | 30 |
| range | 1.000 | 1.000 | 1.000 | 30 |
| naturalness | 0.092 | 0.433 | 0.867 | 30 |
| **overall_band** | 0.535 | 0.867 | 1.000 | 30 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | n/a (0/0) |
| meaning_inversion precision | n/a (0/0) |
| explanation_variant accuracy (word_choice TPs) | n/a (0/0; 0 with no predicted variant) |
| variant_basis distribution | — (not emitted) |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 0 | 0 | 0 | 0 | 0 | 0 |
| omission | 0 | 1 | 0 | 0 | 0 | 0 |
| word_choice | 0 | 0 | 3 | 0 | 0 | 0 |
| preposition | 0 | 0 | 0 | 0 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 2 | 0 | 0 | 0 | 0 |

## Raw metrics (JSON)

```json
{
  "n_items": 30,
  "kind_counts": {
    "clean": 10,
    "single": 15,
    "multi": 5
  },
  "span": {
    "precision": 0.9565217391304348,
    "recall": 0.8461538461538461,
    "f1": 0.8979591836734695,
    "tp": 22,
    "fp": 1,
    "fn": 4
  },
  "subtype_accuracy": {
    "correct": 19,
    "total": 22,
    "accuracy": 0.8636363636363636
  },
  "severity": {
    "exact": 0.6363636363636364,
    "within_one": 1.0,
    "n": 22
  },
  "clean_fp": {
    "item_fp_rate": 0.1,
    "mean_errors": 0.1,
    "total_errors": 1,
    "n": 10
  },
  "bands": {
    "accuracy": {
      "qwk": 0.6825396825396826,
      "exact": 0.8666666666666667,
      "adjacent": 1.0,
      "n": 30
    },
    "understandability": {
      "qwk": 0.6949152542372881,
      "exact": 0.9,
      "adjacent": 0.9666666666666667,
      "n": 30
    },
    "fidelity": {
      "qwk": 0.7938931297709924,
      "exact": 0.8,
      "adjacent": 0.9666666666666667,
      "n": 30
    },
    "range": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 30
    },
    "naturalness": {
      "qwk": 0.09185803757828803,
      "exact": 0.43333333333333335,
      "adjacent": 0.8666666666666667,
      "n": 30
    }
  },
  "overall": {
    "qwk": 0.5348837209302326,
    "exact": 0.8666666666666667,
    "adjacent": 1.0,
    "n": 30
  },
  "v6": {
    "mi_confusion": {
      "labels": [
        "meaning_inversion",
        "omission",
        "word_choice",
        "preposition",
        "contradiction",
        "other"
      ],
      "matrix": {
        "meaning_inversion": {
          "meaning_inversion": 0,
          "omission": 0,
          "word_choice": 0,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        },
        "omission": {
          "meaning_inversion": 0,
          "omission": 1,
          "word_choice": 0,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        },
        "word_choice": {
          "meaning_inversion": 0,
          "omission": 0,
          "word_choice": 3,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        },
        "preposition": {
          "meaning_inversion": 0,
          "omission": 0,
          "word_choice": 0,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        },
        "contradiction": {
          "meaning_inversion": 0,
          "omission": 0,
          "word_choice": 0,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        },
        "other": {
          "meaning_inversion": 0,
          "omission": 2,
          "word_choice": 0,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        }
      }
    },
    "meaning_inversion": {
      "subtype": "meaning_inversion",
      "tp": 0,
      "n_expected": 0,
      "n_predicted": 0,
      "recall": NaN,
      "precision": NaN
    },
    "explanation_variant": {
      "correct": 0,
      "total": 0,
      "pred_missing": 0,
      "accuracy": NaN,
      "variant_basis": {}
    }
  }
}
```
