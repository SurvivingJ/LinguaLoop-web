# DT Grading Eval — v2 (EN)

- **Run date:** 2026-10-08
- **L2 / L1:** en / zh
- **Items graded:** 30 (clean 10 / single 15 / multi 5)
- **Grader:** v2 Detector/Verifier cascade (`grade_submission(framework_v2=True)`), slugs: google/gemini-3.5-flash-lite
- **Fixture set:** v5
- **Taxonomy:** live (active DB row, or the DT_TAXONOMY_VERSION pin)
- **Tokens:** 85,858 in / 8,125 out — model calls: 58
- **Est. cost:** $0.0461 USD (model-arena pricing)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 0.960 | 0.889 | 0.923 | 24 | 1 | 3 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.875 (21/24) |
| Severity exact (triad minor/major/critical) | 0.500 (n=24) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.000 (10 clean items) |
| Clean-passage mean spurious errors/item | 0.000 (0 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.828 | 0.767 | 1.000 | 30 |
| understandability | 0.627 | 0.867 | 0.933 | 30 |
| fidelity | 0.561 | 0.867 | 0.933 | 30 |
| range | 0.000 | 0.931 | 1.000 | 29 |
| naturalness | 0.037 | 0.607 | 1.000 | 28 |
| **overall_band** | 0.695 | 0.900 | 0.967 | 30 |

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
| omission | 0 | 2 | 0 | 0 | 0 | 0 |
| word_choice | 0 | 0 | 1 | 0 | 0 | 0 |
| preposition | 0 | 0 | 0 | 4 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 0 | 2 | 1 | 0 | 0 |

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
    "precision": 0.96,
    "recall": 0.8888888888888888,
    "f1": 0.923076923076923,
    "tp": 24,
    "fp": 1,
    "fn": 3
  },
  "subtype_accuracy": {
    "correct": 21,
    "total": 24,
    "accuracy": 0.875
  },
  "severity": {
    "exact": 0.5,
    "within_one": 1.0,
    "n": 24
  },
  "clean_fp": {
    "item_fp_rate": 0.0,
    "mean_errors": 0.0,
    "total_errors": 0,
    "n": 10
  },
  "bands": {
    "accuracy": {
      "qwk": 0.8281505728314239,
      "exact": 0.7666666666666667,
      "adjacent": 1.0,
      "n": 30
    },
    "understandability": {
      "qwk": 0.6268656716417911,
      "exact": 0.8666666666666667,
      "adjacent": 0.9333333333333333,
      "n": 30
    },
    "fidelity": {
      "qwk": 0.5614035087719298,
      "exact": 0.8666666666666667,
      "adjacent": 0.9333333333333333,
      "n": 30
    },
    "range": {
      "qwk": 0.0,
      "exact": 0.9310344827586207,
      "adjacent": 1.0,
      "n": 29
    },
    "naturalness": {
      "qwk": 0.037499999999999756,
      "exact": 0.6071428571428571,
      "adjacent": 1.0,
      "n": 28
    }
  },
  "overall": {
    "qwk": 0.6949152542372881,
    "exact": 0.9,
    "adjacent": 0.9666666666666667,
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
          "omission": 2,
          "word_choice": 0,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        },
        "word_choice": {
          "meaning_inversion": 0,
          "omission": 0,
          "word_choice": 1,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        },
        "preposition": {
          "meaning_inversion": 0,
          "omission": 0,
          "word_choice": 0,
          "preposition": 4,
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
          "omission": 0,
          "word_choice": 2,
          "preposition": 1,
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
