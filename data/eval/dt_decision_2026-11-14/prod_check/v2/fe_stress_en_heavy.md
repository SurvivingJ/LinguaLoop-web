# DT Grading Eval — single-call (EN)

- **Run date:** 2026-11-18
- **L2 / L1:** en / zh
- **Items graded:** 19 (clean 7 / single 9 / multi 3)
- **Grader:** single-call generative grader (`grade_submission(single_call=True)`, ADR-044); fallback flow v1; paths: {"primary": 14, "fallback_flow:v1": 5}, slugs: baidu/ernie-5.5-flash-preview:free
- **Rubric:** CANDIDATE config from `migrations/dt_rubric_v6_seed.sql` (pre-seeded into the config cache; live DB rubric not modified)
- **Fixture set:** v6
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 36,892 in / 20,624 out — model calls: 19
- **Cost:** $0.000000 USD (as reported by OpenRouter on usage.cost)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 0.692 | 0.600 | 0.643 | 9 | 4 | 6 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.889 (8/9) |
| Severity exact (triad minor/major/critical) | 0.556 (n=9) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.143 (7 clean items) |
| Clean-passage mean spurious errors/item | 0.143 (1 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.472 | 0.842 | 0.947 | 19 |
| understandability | 0.721 | 0.842 | 0.947 | 19 |
| fidelity | 0.620 | 0.895 | 0.947 | 19 |
| range | 0.000 | 0.947 | 1.000 | 19 |
| naturalness | -0.075 | 0.842 | 1.000 | 19 |
| **overall_band** | 0.313 | 0.842 | 1.000 | 19 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 0.500 (1/2) |
| meaning_inversion precision | 1.000 (1/1) |
| explanation_variant accuracy (word_choice TPs) | n/a (0/0; 0 with no predicted variant) |
| variant_basis distribution | default=0, model=0, same_lemma=0, shared_gloss=0 |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 1 | 0 | 0 | 0 | 0 | 0 |
| omission | 0 | 1 | 0 | 0 | 0 | 0 |
| word_choice | 0 | 0 | 0 | 0 | 0 | 0 |
| preposition | 0 | 0 | 0 | 1 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 0 | 0 | 0 | 0 | 0 |

## Raw metrics (JSON)

```json
{
  "n_items": 19,
  "kind_counts": {
    "clean": 7,
    "single": 9,
    "multi": 3
  },
  "span": {
    "precision": 0.6923076923076923,
    "recall": 0.6,
    "f1": 0.6428571428571429,
    "tp": 9,
    "fp": 4,
    "fn": 6
  },
  "subtype_accuracy": {
    "correct": 8,
    "total": 9,
    "accuracy": 0.8888888888888888
  },
  "severity": {
    "exact": 0.5555555555555556,
    "within_one": 1.0,
    "n": 9
  },
  "clean_fp": {
    "item_fp_rate": 0.14285714285714285,
    "mean_errors": 0.14285714285714285,
    "total_errors": 1,
    "n": 7
  },
  "bands": {
    "accuracy": {
      "qwk": 0.4722222222222222,
      "exact": 0.8421052631578947,
      "adjacent": 0.9473684210526315,
      "n": 19
    },
    "understandability": {
      "qwk": 0.7205882352941176,
      "exact": 0.8421052631578947,
      "adjacent": 0.9473684210526315,
      "n": 19
    },
    "fidelity": {
      "qwk": 0.6199999999999999,
      "exact": 0.8947368421052632,
      "adjacent": 0.9473684210526315,
      "n": 19
    },
    "range": {
      "qwk": 0.0,
      "exact": 0.9473684210526315,
      "adjacent": 1.0,
      "n": 19
    },
    "naturalness": {
      "qwk": -0.07547169811320753,
      "exact": 0.8421052631578947,
      "adjacent": 1.0,
      "n": 19
    }
  },
  "overall": {
    "qwk": 0.3132530120481928,
    "exact": 0.8421052631578947,
    "adjacent": 1.0,
    "n": 19
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
          "meaning_inversion": 1,
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
          "word_choice": 0,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        },
        "preposition": {
          "meaning_inversion": 0,
          "omission": 0,
          "word_choice": 0,
          "preposition": 1,
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
      "tp": 1,
      "n_expected": 2,
      "n_predicted": 1,
      "recall": 0.5,
      "precision": 1.0
    },
    "explanation_variant": {
      "correct": 0,
      "total": 0,
      "pred_missing": 0,
      "accuracy": NaN,
      "variant_basis": {
        "default": 0,
        "model": 0,
        "same_lemma": 0,
        "shared_gloss": 0
      }
    }
  }
}
```
