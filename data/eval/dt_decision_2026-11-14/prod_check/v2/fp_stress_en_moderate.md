# DT Grading Eval — single-call (EN)

- **Run date:** 2026-11-18
- **L2 / L1:** en / zh
- **Items graded:** 20 (clean 7 / single 10 / multi 3)
- **Grader:** single-call generative grader (`grade_submission(single_call=True)`, ADR-044); fallback flow v1; paths: {"primary": 20}, slugs: particle-ai/particle-1:free
- **Rubric:** CANDIDATE config from `migrations/dt_rubric_v6_seed.sql` (pre-seeded into the config cache; live DB rubric not modified)
- **Fixture set:** v6
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 39,832 in / 3,150 out — model calls: 20
- **Cost:** $0.000000 USD (as reported by OpenRouter on usage.cost)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 0.842 | 1.000 | 0.914 | 16 | 3 | 0 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.875 (14/16) |
| Severity exact (triad minor/major/critical) | 0.625 (n=16) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.286 (7 clean items) |
| Clean-passage mean spurious errors/item | 0.286 (2 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.769 | 0.850 | 1.000 | 20 |
| understandability | 1.000 | 1.000 | 1.000 | 20 |
| fidelity | 0.941 | 0.900 | 1.000 | 20 |
| range | 1.000 | 1.000 | 1.000 | 20 |
| naturalness | -0.111 | 0.800 | 1.000 | 20 |
| **overall_band** | 1.000 | 1.000 | 1.000 | 20 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 1.000 (2/2) |
| meaning_inversion precision | 1.000 (2/2) |
| explanation_variant accuracy (word_choice TPs) | n/a (0/0; 0 with no predicted variant) |
| variant_basis distribution | default=2, model=0, same_lemma=0, shared_gloss=0 |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 2 | 0 | 0 | 0 | 0 | 0 |
| omission | 0 | 1 | 0 | 0 | 0 | 0 |
| word_choice | 0 | 0 | 1 | 0 | 0 | 0 |
| preposition | 0 | 0 | 0 | 2 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 0 | 1 | 0 | 0 | 0 |

## Raw metrics (JSON)

```json
{
  "n_items": 20,
  "kind_counts": {
    "clean": 7,
    "single": 10,
    "multi": 3
  },
  "span": {
    "precision": 0.8421052631578947,
    "recall": 1.0,
    "f1": 0.9142857142857143,
    "tp": 16,
    "fp": 3,
    "fn": 0
  },
  "subtype_accuracy": {
    "correct": 14,
    "total": 16,
    "accuracy": 0.875
  },
  "severity": {
    "exact": 0.625,
    "within_one": 1.0,
    "n": 16
  },
  "clean_fp": {
    "item_fp_rate": 0.2857142857142857,
    "mean_errors": 0.2857142857142857,
    "total_errors": 2,
    "n": 7
  },
  "bands": {
    "accuracy": {
      "qwk": 0.7692307692307693,
      "exact": 0.85,
      "adjacent": 1.0,
      "n": 20
    },
    "understandability": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 20
    },
    "fidelity": {
      "qwk": 0.9406528189910979,
      "exact": 0.9,
      "adjacent": 1.0,
      "n": 20
    },
    "range": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 20
    },
    "naturalness": {
      "qwk": -0.11111111111111116,
      "exact": 0.8,
      "adjacent": 1.0,
      "n": 20
    }
  },
  "overall": {
    "qwk": 1.0,
    "exact": 1.0,
    "adjacent": 1.0,
    "n": 20
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
      "correct": 0,
      "total": 0,
      "pred_missing": 0,
      "accuracy": NaN,
      "variant_basis": {
        "default": 2,
        "model": 0,
        "same_lemma": 0,
        "shared_gloss": 0
      }
    }
  }
}
```
