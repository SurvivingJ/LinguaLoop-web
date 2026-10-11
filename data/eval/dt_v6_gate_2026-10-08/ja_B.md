# DT Grading Eval — v2 (JA)

- **Run date:** 2026-10-08
- **L2 / L1:** ja / en
- **Items graded:** 30 (clean 10 / single 15 / multi 5)
- **Grader:** v2 Detector/Verifier cascade (`grade_submission(framework_v2=True)`), slugs: qwen/qwen3.6-flash, qwen/qwen3.7-plus
- **Fixture set:** v6
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 173,683 in / 274,378 out — model calls: 58
- **Est. cost:** $0.3733 USD (model-arena pricing)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 1.000 | 0.778 | 0.875 | 21 | 0 | 6 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.810 (17/21) |
| Severity exact (triad minor/major/critical) | 0.810 (n=21) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.000 (10 clean items) |
| Clean-passage mean spurious errors/item | 0.000 (0 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.412 | 0.800 | 1.000 | 30 |
| understandability | 0.925 | 0.933 | 1.000 | 30 |
| fidelity | 0.926 | 0.900 | 1.000 | 30 |
| range | 0.000 | 0.885 | 1.000 | 26 |
| naturalness | 0.067 | 0.500 | 0.929 | 28 |
| **overall_band** | 0.839 | 0.933 | 1.000 | 30 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 1.000 (2/2) |
| meaning_inversion precision | 1.000 (2/2) |
| explanation_variant accuracy (word_choice TPs) | 0.667 (2/3; 0 with no predicted variant) |
| variant_basis distribution | default=0, model=3, same_lemma=1, shared_gloss=0 |
| exemplar-drop warnings (must be 0 for en/zh) | 29 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 2 | 0 | 0 | 0 | 0 | 0 |
| omission | 0 | 1 | 0 | 0 | 0 | 0 |
| word_choice | 0 | 0 | 3 | 0 | 0 | 1 |
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
    "precision": 1.0,
    "recall": 0.7777777777777778,
    "f1": 0.8750000000000001,
    "tp": 21,
    "fp": 0,
    "fn": 6
  },
  "subtype_accuracy": {
    "correct": 17,
    "total": 21,
    "accuracy": 0.8095238095238095
  },
  "severity": {
    "exact": 0.8095238095238095,
    "within_one": 1.0,
    "n": 21
  },
  "clean_fp": {
    "item_fp_rate": 0.0,
    "mean_errors": 0.0,
    "total_errors": 0,
    "n": 10
  },
  "bands": {
    "accuracy": {
      "qwk": 0.4117647058823529,
      "exact": 0.8,
      "adjacent": 1.0,
      "n": 30
    },
    "understandability": {
      "qwk": 0.9253731343283582,
      "exact": 0.9333333333333333,
      "adjacent": 1.0,
      "n": 30
    },
    "fidelity": {
      "qwk": 0.9263502454991817,
      "exact": 0.9,
      "adjacent": 1.0,
      "n": 30
    },
    "range": {
      "qwk": 0.0,
      "exact": 0.8846153846153846,
      "adjacent": 1.0,
      "n": 26
    },
    "naturalness": {
      "qwk": 0.06666666666666665,
      "exact": 0.5,
      "adjacent": 0.9285714285714286,
      "n": 28
    }
  },
  "overall": {
    "qwk": 0.8387096774193549,
    "exact": 0.9333333333333333,
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
          "meaning_inversion": 2,
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
          "other": 1
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
      "tp": 2,
      "n_expected": 2,
      "n_predicted": 2,
      "recall": 1.0,
      "precision": 1.0
    },
    "explanation_variant": {
      "correct": 2,
      "total": 3,
      "pred_missing": 0,
      "accuracy": 0.6666666666666666,
      "variant_basis": {
        "default": 0,
        "model": 3,
        "same_lemma": 1,
        "shared_gloss": 0
      }
    }
  }
}
```
