# DT Grading Eval — v2 (EN)

- **Run date:** 2026-10-08
- **L2 / L1:** en / zh
- **Items graded:** 31 (clean 10 / single 16 / multi 5)
- **Grader:** v2 Detector/Verifier cascade (`grade_submission(framework_v2=True)`), slugs: google/gemini-3.5-flash-lite
- **Fixture set:** v6
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 137,678 in / 8,654 out — model calls: 60
- **Est. cost:** $0.0629 USD (model-arena pricing)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 1.000 | 0.929 | 0.963 | 26 | 0 | 2 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.769 (20/26) |
| Severity exact (triad minor/major/critical) | 0.462 (n=26) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.000 (10 clean items) |
| Clean-passage mean spurious errors/item | 0.000 (0 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.510 | 0.774 | 1.000 | 31 |
| understandability | 0.815 | 0.871 | 1.000 | 31 |
| fidelity | 0.854 | 0.903 | 0.968 | 31 |
| range | 0.000 | 0.933 | 1.000 | 30 |
| naturalness | 0.183 | 0.581 | 1.000 | 31 |
| **overall_band** | 0.431 | 0.871 | 1.000 | 31 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 1.000 (2/2) |
| meaning_inversion precision | 1.000 (2/2) |
| explanation_variant accuracy (word_choice TPs) | 0.500 (1/2; 0 with no predicted variant) |
| variant_basis distribution | default=0, model=5, same_lemma=0, shared_gloss=0 |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 2 | 0 | 0 | 0 | 0 | 0 |
| omission | 0 | 2 | 0 | 0 | 0 | 0 |
| word_choice | 0 | 0 | 2 | 0 | 0 | 2 |
| preposition | 0 | 0 | 0 | 2 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 0 | 3 | 1 | 0 | 0 |

## Raw metrics (JSON)

```json
{
  "n_items": 31,
  "kind_counts": {
    "clean": 10,
    "single": 16,
    "multi": 5
  },
  "span": {
    "precision": 1.0,
    "recall": 0.9285714285714286,
    "f1": 0.962962962962963,
    "tp": 26,
    "fp": 0,
    "fn": 2
  },
  "subtype_accuracy": {
    "correct": 20,
    "total": 26,
    "accuracy": 0.7692307692307693
  },
  "severity": {
    "exact": 0.46153846153846156,
    "within_one": 1.0,
    "n": 26
  },
  "clean_fp": {
    "item_fp_rate": 0.0,
    "mean_errors": 0.0,
    "total_errors": 0,
    "n": 10
  },
  "bands": {
    "accuracy": {
      "qwk": 0.510158013544018,
      "exact": 0.7741935483870968,
      "adjacent": 1.0,
      "n": 31
    },
    "understandability": {
      "qwk": 0.8154761904761905,
      "exact": 0.8709677419354839,
      "adjacent": 1.0,
      "n": 31
    },
    "fidelity": {
      "qwk": 0.85423197492163,
      "exact": 0.9032258064516129,
      "adjacent": 0.967741935483871,
      "n": 31
    },
    "range": {
      "qwk": 0.0,
      "exact": 0.9333333333333333,
      "adjacent": 1.0,
      "n": 30
    },
    "naturalness": {
      "qwk": 0.1825557809330629,
      "exact": 0.5806451612903226,
      "adjacent": 1.0,
      "n": 31
    }
  },
  "overall": {
    "qwk": 0.4311926605504588,
    "exact": 0.8709677419354839,
    "adjacent": 1.0,
    "n": 31
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
          "omission": 2,
          "word_choice": 0,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        },
        "word_choice": {
          "meaning_inversion": 0,
          "omission": 0,
          "word_choice": 2,
          "preposition": 0,
          "contradiction": 0,
          "other": 2
        },
        "preposition": {
          "meaning_inversion": 0,
          "omission": 0,
          "word_choice": 0,
          "preposition": 2,
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
          "word_choice": 3,
          "preposition": 1,
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
      "total": 2,
      "pred_missing": 0,
      "accuracy": 0.5,
      "variant_basis": {
        "default": 0,
        "model": 5,
        "same_lemma": 0,
        "shared_gloss": 0
      }
    }
  }
}
```
