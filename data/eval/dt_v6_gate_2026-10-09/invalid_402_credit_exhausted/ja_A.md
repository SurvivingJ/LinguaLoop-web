# DT Grading Eval — v2 (JA)

- **Run date:** 2026-10-09
- **L2 / L1:** ja / en
- **Items graded:** 30 (clean 10 / single 15 / multi 5)
- **Grader:** v2 Detector/Verifier cascade (`grade_submission(framework_v2=True)`), slugs: qwen/qwen3.6-flash
- **Fixture set:** v5
- **Taxonomy:** live (active DB row, or the DT_TAXONOMY_VERSION pin)
- **Tokens:** 1,740 in / 2,878 out — model calls: 1
- **Est. cost:** $0.0036 USD (model-arena pricing)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 0.000 | 0.000 | 0.000 | 0 | 0 | 27 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | n/a (0/0) |
| Severity exact (triad minor/major/critical) | n/a (n=0) |
| **Severity within-one (triad)** | n/a |
| **Clean-passage FP rate (items flagged)** | 0.000 (10 clean items) |
| Clean-passage mean spurious errors/item | 0.000 (0 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 1.000 | 1.000 | 1.000 | 2 |
| understandability | 1.000 | 1.000 | 1.000 | 2 |
| fidelity | 1.000 | 1.000 | 1.000 | 2 |
| range | 1.000 | 1.000 | 1.000 | 1 |
| naturalness | 1.000 | 1.000 | 1.000 | 1 |
| **overall_band** | 1.000 | 1.000 | 1.000 | 2 |

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
| omission | 0 | 0 | 0 | 0 | 0 | 0 |
| word_choice | 0 | 0 | 0 | 0 | 0 | 0 |
| preposition | 0 | 0 | 0 | 0 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 0 | 0 | 0 | 0 | 0 |

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
    "precision": 0.0,
    "recall": 0.0,
    "f1": 0.0,
    "tp": 0,
    "fp": 0,
    "fn": 27
  },
  "subtype_accuracy": {
    "correct": 0,
    "total": 0,
    "accuracy": NaN
  },
  "severity": {
    "exact": NaN,
    "within_one": NaN,
    "n": 0
  },
  "clean_fp": {
    "item_fp_rate": 0.0,
    "mean_errors": 0.0,
    "total_errors": 0,
    "n": 10
  },
  "bands": {
    "accuracy": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 2
    },
    "understandability": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 2
    },
    "fidelity": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 2
    },
    "range": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 1
    },
    "naturalness": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 1
    }
  },
  "overall": {
    "qwk": 1.0,
    "exact": 1.0,
    "adjacent": 1.0,
    "n": 2
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
          "omission": 0,
          "word_choice": 0,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        },
        "word_choice": {
          "meaning_inversion": 0,
          "omission": 0,
          "word_choice": 0,
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
          "omission": 0,
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
