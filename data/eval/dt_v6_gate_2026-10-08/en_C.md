# DT Grading Eval — v2 (EN)

- **Run date:** 2026-10-08
- **L2 / L1:** en / zh
- **Items graded:** 35 (clean 6 / single 26 / multi 3)
- **Grader:** v2 Detector/Verifier cascade (`grade_submission(framework_v2=True)`), slugs: google/gemini-3.5-flash-lite
- **Fixture set:** v6_silver
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 161,689 in / 11,427 out — model calls: 70
- **Est. cost:** $0.0771 USD (model-arena pricing)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 0.897 | 1.000 | 0.946 | 35 | 4 | 0 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.829 (29/35) |
| Severity exact (triad minor/major/critical) | 0.657 (n=35) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.333 (6 clean items) |
| Clean-passage mean spurious errors/item | 0.333 (2 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.571 | 0.829 | 1.000 | 35 |
| understandability | 0.895 | 0.943 | 0.971 | 35 |
| fidelity | 0.901 | 0.800 | 0.971 | 35 |
| range | 0.428 | 0.935 | 0.968 | 31 |
| naturalness | 0.008 | 0.333 | 1.000 | 33 |
| **overall_band** | 0.860 | 0.943 | 1.000 | 35 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 0.875 (7/8) |
| meaning_inversion precision | 1.000 (7/7) |
| explanation_variant accuracy (word_choice TPs) | 1.000 (5/5; 0 with no predicted variant) |
| variant_basis distribution | default=0, model=10, same_lemma=0, shared_gloss=0 |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 7 | 0 | 1 | 0 | 0 | 0 |
| omission | 0 | 2 | 0 | 0 | 0 | 0 |
| word_choice | 0 | 0 | 5 | 0 | 0 | 3 |
| preposition | 0 | 0 | 0 | 1 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 0 | 1 | 1 | 0 | 0 |

## Raw metrics (JSON)

```json
{
  "n_items": 35,
  "kind_counts": {
    "clean": 6,
    "single": 26,
    "multi": 3
  },
  "span": {
    "precision": 0.8974358974358975,
    "recall": 1.0,
    "f1": 0.945945945945946,
    "tp": 35,
    "fp": 4,
    "fn": 0
  },
  "subtype_accuracy": {
    "correct": 29,
    "total": 35,
    "accuracy": 0.8285714285714286
  },
  "severity": {
    "exact": 0.6571428571428571,
    "within_one": 1.0,
    "n": 35
  },
  "clean_fp": {
    "item_fp_rate": 0.3333333333333333,
    "mean_errors": 0.3333333333333333,
    "total_errors": 2,
    "n": 6
  },
  "bands": {
    "accuracy": {
      "qwk": 0.5714285714285714,
      "exact": 0.8285714285714286,
      "adjacent": 1.0,
      "n": 35
    },
    "understandability": {
      "qwk": 0.8947684906794948,
      "exact": 0.9428571428571428,
      "adjacent": 0.9714285714285714,
      "n": 35
    },
    "fidelity": {
      "qwk": 0.9010740531373658,
      "exact": 0.8,
      "adjacent": 0.9714285714285714,
      "n": 35
    },
    "range": {
      "qwk": 0.4280442804428044,
      "exact": 0.9354838709677419,
      "adjacent": 0.967741935483871,
      "n": 31
    },
    "naturalness": {
      "qwk": 0.008196721311475308,
      "exact": 0.3333333333333333,
      "adjacent": 1.0,
      "n": 33
    }
  },
  "overall": {
    "qwk": 0.86,
    "exact": 0.9428571428571428,
    "adjacent": 1.0,
    "n": 35
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
          "meaning_inversion": 7,
          "omission": 0,
          "word_choice": 1,
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
          "word_choice": 5,
          "preposition": 0,
          "contradiction": 0,
          "other": 3
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
          "word_choice": 1,
          "preposition": 1,
          "contradiction": 0,
          "other": 0
        }
      }
    },
    "meaning_inversion": {
      "subtype": "meaning_inversion",
      "tp": 7,
      "n_expected": 8,
      "n_predicted": 7,
      "recall": 0.875,
      "precision": 1.0
    },
    "explanation_variant": {
      "correct": 5,
      "total": 5,
      "pred_missing": 0,
      "accuracy": 1.0,
      "variant_basis": {
        "default": 0,
        "model": 10,
        "same_lemma": 0,
        "shared_gloss": 0
      }
    }
  }
}
```
