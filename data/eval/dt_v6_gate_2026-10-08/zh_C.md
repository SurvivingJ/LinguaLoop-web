# DT Grading Eval — v2 (ZH)

- **Run date:** 2026-10-08
- **L2 / L1:** zh / en
- **Items graded:** 34 (clean 6 / single 23 / multi 5)
- **Grader:** v2 Detector/Verifier cascade (`grade_submission(framework_v2=True)`), slugs: qwen/qwen3.6-flash, qwen/qwen3.7-plus
- **Fixture set:** v6_silver
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 185,298 in / 230,439 out — model calls: 68
- **Est. cost:** $0.3199 USD (model-arena pricing)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 1.000 | 0.758 | 0.862 | 25 | 0 | 8 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.800 (20/25) |
| Severity exact (triad minor/major/critical) | 0.720 (n=25) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.000 (6 clean items) |
| Clean-passage mean spurious errors/item | 0.000 (0 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.612 | 0.853 | 1.000 | 34 |
| understandability | 0.799 | 0.941 | 0.941 | 34 |
| fidelity | 0.875 | 0.853 | 0.941 | 34 |
| range | 1.000 | 1.000 | 1.000 | 34 |
| naturalness | -0.021 | 0.500 | 0.941 | 34 |
| **overall_band** | 0.718 | 0.912 | 1.000 | 34 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 1.000 (5/5) |
| meaning_inversion precision | 0.833 (5/6) |
| explanation_variant accuracy (word_choice TPs) | 0.000 (0/1; 0 with no predicted variant) |
| variant_basis distribution | default=0, model=2, same_lemma=0, shared_gloss=0 |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 5 | 0 | 0 | 0 | 0 | 0 |
| omission | 0 | 1 | 0 | 0 | 0 | 0 |
| word_choice | 1 | 0 | 1 | 0 | 0 | 0 |
| preposition | 0 | 0 | 0 | 0 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 2 | 1 | 0 | 0 | 0 |

## Raw metrics (JSON)

```json
{
  "n_items": 34,
  "kind_counts": {
    "clean": 6,
    "single": 23,
    "multi": 5
  },
  "span": {
    "precision": 1.0,
    "recall": 0.7575757575757576,
    "f1": 0.8620689655172413,
    "tp": 25,
    "fp": 0,
    "fn": 8
  },
  "subtype_accuracy": {
    "correct": 20,
    "total": 25,
    "accuracy": 0.8
  },
  "severity": {
    "exact": 0.72,
    "within_one": 1.0,
    "n": 25
  },
  "clean_fp": {
    "item_fp_rate": 0.0,
    "mean_errors": 0.0,
    "total_errors": 0,
    "n": 6
  },
  "bands": {
    "accuracy": {
      "qwk": 0.6118721461187214,
      "exact": 0.8529411764705882,
      "adjacent": 1.0,
      "n": 34
    },
    "understandability": {
      "qwk": 0.7988165680473374,
      "exact": 0.9411764705882353,
      "adjacent": 0.9411764705882353,
      "n": 34
    },
    "fidelity": {
      "qwk": 0.8749163879598663,
      "exact": 0.8529411764705882,
      "adjacent": 0.9411764705882353,
      "n": 34
    },
    "range": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 34
    },
    "naturalness": {
      "qwk": -0.02088772845952991,
      "exact": 0.5,
      "adjacent": 0.9411764705882353,
      "n": 34
    }
  },
  "overall": {
    "qwk": 0.718232044198895,
    "exact": 0.9117647058823529,
    "adjacent": 1.0,
    "n": 34
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
          "meaning_inversion": 5,
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
          "meaning_inversion": 1,
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
          "word_choice": 1,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        }
      }
    },
    "meaning_inversion": {
      "subtype": "meaning_inversion",
      "tp": 5,
      "n_expected": 5,
      "n_predicted": 6,
      "recall": 1.0,
      "precision": 0.8333333333333334
    },
    "explanation_variant": {
      "correct": 0,
      "total": 1,
      "pred_missing": 0,
      "accuracy": 0.0,
      "variant_basis": {
        "default": 0,
        "model": 2,
        "same_lemma": 0,
        "shared_gloss": 0
      }
    }
  }
}
```
