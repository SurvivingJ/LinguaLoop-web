# DT Grading Eval — v2 (ZH)

- **Run date:** 2026-10-08
- **L2 / L1:** zh / en
- **Items graded:** 30 (clean 10 / single 15 / multi 5)
- **Grader:** v2 Detector/Verifier cascade (`grade_submission(framework_v2=True)`), slugs: qwen/qwen3.6-flash, qwen/qwen3.7-plus
- **Fixture set:** v6
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 152,010 in / 197,151 out — model calls: 56
- **Est. cost:** $0.2712 USD (model-arena pricing)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 0.950 | 0.731 | 0.826 | 19 | 1 | 7 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.789 (15/19) |
| Severity exact (triad minor/major/critical) | 0.789 (n=19) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.100 (10 clean items) |
| Clean-passage mean spurious errors/item | 0.100 (1 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.561 | 0.833 | 1.000 | 30 |
| understandability | 0.936 | 0.967 | 1.000 | 30 |
| fidelity | 0.865 | 0.833 | 1.000 | 30 |
| range | 1.000 | 1.000 | 1.000 | 30 |
| naturalness | 0.099 | 0.533 | 0.833 | 30 |
| **overall_band** | 0.615 | 0.900 | 1.000 | 30 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 1.000 (2/2) |
| meaning_inversion precision | 1.000 (2/2) |
| explanation_variant accuracy (word_choice TPs) | 1.000 (1/1; 0 with no predicted variant) |
| variant_basis distribution | default=0, model=3, same_lemma=0, shared_gloss=0 |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 2 | 0 | 0 | 0 | 0 | 0 |
| omission | 0 | 1 | 0 | 0 | 0 | 0 |
| word_choice | 0 | 0 | 1 | 0 | 0 | 0 |
| preposition | 0 | 0 | 0 | 0 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 2 | 1 | 0 | 0 | 0 |

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
    "precision": 0.95,
    "recall": 0.7307692307692307,
    "f1": 0.8260869565217392,
    "tp": 19,
    "fp": 1,
    "fn": 7
  },
  "subtype_accuracy": {
    "correct": 15,
    "total": 19,
    "accuracy": 0.7894736842105263
  },
  "severity": {
    "exact": 0.7894736842105263,
    "within_one": 1.0,
    "n": 19
  },
  "clean_fp": {
    "item_fp_rate": 0.1,
    "mean_errors": 0.1,
    "total_errors": 1,
    "n": 10
  },
  "bands": {
    "accuracy": {
      "qwk": 0.5614035087719298,
      "exact": 0.8333333333333334,
      "adjacent": 1.0,
      "n": 30
    },
    "understandability": {
      "qwk": 0.9361702127659575,
      "exact": 0.9666666666666667,
      "adjacent": 1.0,
      "n": 30
    },
    "fidelity": {
      "qwk": 0.8648648648648649,
      "exact": 0.8333333333333334,
      "adjacent": 1.0,
      "n": 30
    },
    "range": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 30
    },
    "naturalness": {
      "qwk": 0.0993788819875775,
      "exact": 0.5333333333333333,
      "adjacent": 0.8333333333333334,
      "n": 30
    }
  },
  "overall": {
    "qwk": 0.6153846153846154,
    "exact": 0.9,
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
      "tp": 2,
      "n_expected": 2,
      "n_predicted": 2,
      "recall": 1.0,
      "precision": 1.0
    },
    "explanation_variant": {
      "correct": 1,
      "total": 1,
      "pred_missing": 0,
      "accuracy": 1.0,
      "variant_basis": {
        "default": 0,
        "model": 3,
        "same_lemma": 0,
        "shared_gloss": 0
      }
    }
  }
}
```
