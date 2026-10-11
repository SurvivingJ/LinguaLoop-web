# DT Grading Eval — v2 (JA)

- **Run date:** 2026-10-08
- **L2 / L1:** ja / en
- **Items graded:** 32 (clean 7 / single 22 / multi 3)
- **Grader:** v2 Detector/Verifier cascade (`grade_submission(framework_v2=True)`), slugs: qwen/qwen3.6-flash, qwen/qwen3.7-plus
- **Fixture set:** v6_silver
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 189,396 in / 321,871 out — model calls: 63
- **Est. cost:** $0.4346 USD (model-arena pricing)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 1.000 | 0.862 | 0.926 | 25 | 0 | 4 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.680 (17/25) |
| Severity exact (triad minor/major/critical) | 0.800 (n=25) |
| **Severity within-one (triad)** | 0.960 |
| **Clean-passage FP rate (items flagged)** | 0.000 (7 clean items) |
| Clean-passage mean spurious errors/item | 0.000 (0 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.636 | 0.938 | 1.000 | 32 |
| understandability | 0.520 | 0.906 | 0.906 | 32 |
| fidelity | 0.537 | 0.750 | 0.906 | 32 |
| range | 0.651 | 0.967 | 1.000 | 30 |
| naturalness | 0.050 | 0.533 | 0.800 | 30 |
| **overall_band** | 0.520 | 0.906 | 1.000 | 32 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 1.000 (4/4) |
| meaning_inversion precision | 0.667 (4/6) |
| explanation_variant accuracy (word_choice TPs) | n/a (0/0; 0 with no predicted variant) |
| variant_basis distribution | default=0, model=0, same_lemma=0, shared_gloss=0 |
| exemplar-drop warnings (must be 0 for en/zh) | 32 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 4 | 0 | 0 | 0 | 0 | 0 |
| omission | 0 | 0 | 0 | 0 | 0 | 0 |
| word_choice | 1 | 0 | 0 | 0 | 0 | 1 |
| preposition | 0 | 0 | 0 | 0 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 1 | 2 | 0 | 0 | 0 | 0 |

## Raw metrics (JSON)

```json
{
  "n_items": 32,
  "kind_counts": {
    "clean": 7,
    "single": 22,
    "multi": 3
  },
  "span": {
    "precision": 1.0,
    "recall": 0.8620689655172413,
    "f1": 0.9259259259259259,
    "tp": 25,
    "fp": 0,
    "fn": 4
  },
  "subtype_accuracy": {
    "correct": 17,
    "total": 25,
    "accuracy": 0.68
  },
  "severity": {
    "exact": 0.8,
    "within_one": 0.96,
    "n": 25
  },
  "clean_fp": {
    "item_fp_rate": 0.0,
    "mean_errors": 0.0,
    "total_errors": 0,
    "n": 7
  },
  "bands": {
    "accuracy": {
      "qwk": 0.6363636363636364,
      "exact": 0.9375,
      "adjacent": 1.0,
      "n": 32
    },
    "understandability": {
      "qwk": 0.52,
      "exact": 0.90625,
      "adjacent": 0.90625,
      "n": 32
    },
    "fidelity": {
      "qwk": 0.5374732334047108,
      "exact": 0.75,
      "adjacent": 0.90625,
      "n": 32
    },
    "range": {
      "qwk": 0.6511627906976745,
      "exact": 0.9666666666666667,
      "adjacent": 1.0,
      "n": 30
    },
    "naturalness": {
      "qwk": 0.04950495049504955,
      "exact": 0.5333333333333333,
      "adjacent": 0.8,
      "n": 30
    }
  },
  "overall": {
    "qwk": 0.52,
    "exact": 0.90625,
    "adjacent": 1.0,
    "n": 32
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
          "meaning_inversion": 4,
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
          "meaning_inversion": 1,
          "omission": 0,
          "word_choice": 0,
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
          "meaning_inversion": 1,
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
      "tp": 4,
      "n_expected": 4,
      "n_predicted": 6,
      "recall": 1.0,
      "precision": 0.6666666666666666
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
