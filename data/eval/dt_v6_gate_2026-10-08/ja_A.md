# DT Grading Eval — v2 (JA)

- **Run date:** 2026-10-08
- **L2 / L1:** ja / en
- **Items graded:** 30 (clean 10 / single 15 / multi 5)
- **Grader:** v2 Detector/Verifier cascade (`grade_submission(framework_v2=True)`), slugs: qwen/qwen3.6-flash, qwen/qwen3.7-plus
- **Fixture set:** v5
- **Taxonomy:** live (active DB row, or the DT_TAXONOMY_VERSION pin)
- **Tokens:** 109,392 in / 280,411 out — model calls: 58
- **Est. cost:** $0.3642 USD (model-arena pricing)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 0.957 | 0.815 | 0.880 | 22 | 1 | 5 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.864 (19/22) |
| Severity exact (triad minor/major/critical) | 0.727 (n=22) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.000 (10 clean items) |
| Clean-passage mean spurious errors/item | 0.000 (0 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.149 | 0.733 | 1.000 | 30 |
| understandability | 0.701 | 0.867 | 0.967 | 30 |
| fidelity | 0.475 | 0.767 | 0.933 | 30 |
| range | 0.000 | 0.897 | 1.000 | 29 |
| naturalness | 0.099 | 0.467 | 0.867 | 30 |
| **overall_band** | 0.643 | 0.867 | 1.000 | 30 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | n/a (0/0) |
| meaning_inversion precision | n/a (0/0) |
| explanation_variant accuracy (word_choice TPs) | n/a (0/0; 0 with no predicted variant) |
| variant_basis distribution | — (not emitted) |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 1 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 0 | 0 | 0 | 0 | 0 | 0 |
| omission | 0 | 1 | 0 | 0 | 0 | 0 |
| word_choice | 0 | 0 | 6 | 0 | 0 | 0 |
| preposition | 0 | 0 | 0 | 0 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 1 | 1 | 0 | 0 | 0 |

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
    "recall": 0.8148148148148148,
    "f1": 0.8800000000000001,
    "tp": 22,
    "fp": 1,
    "fn": 5
  },
  "subtype_accuracy": {
    "correct": 19,
    "total": 22,
    "accuracy": 0.8636363636363636
  },
  "severity": {
    "exact": 0.7272727272727273,
    "within_one": 1.0,
    "n": 22
  },
  "clean_fp": {
    "item_fp_rate": 0.0,
    "mean_errors": 0.0,
    "total_errors": 0,
    "n": 10
  },
  "bands": {
    "accuracy": {
      "qwk": 0.14893617021276584,
      "exact": 0.7333333333333333,
      "adjacent": 1.0,
      "n": 30
    },
    "understandability": {
      "qwk": 0.7008547008547009,
      "exact": 0.8666666666666667,
      "adjacent": 0.9666666666666667,
      "n": 30
    },
    "fidelity": {
      "qwk": 0.47470817120622577,
      "exact": 0.7666666666666667,
      "adjacent": 0.9333333333333333,
      "n": 30
    },
    "range": {
      "qwk": 0.0,
      "exact": 0.896551724137931,
      "adjacent": 1.0,
      "n": 29
    },
    "naturalness": {
      "qwk": 0.09871244635193144,
      "exact": 0.4666666666666667,
      "adjacent": 0.8666666666666667,
      "n": 30
    }
  },
  "overall": {
    "qwk": 0.6428571428571429,
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
          "word_choice": 6,
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
          "omission": 1,
          "word_choice": 1,
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
