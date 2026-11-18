# DT Grading Eval — single-call (EN)

- **Run date:** 2026-11-18
- **L2 / L1:** en / zh
- **Items graded:** 31 (clean 10 / single 16 / multi 5)
- **Grader:** single-call generative grader (`grade_submission(single_call=True)`, ADR-044); fallback flow v1; paths: {"primary": 28, "fallback_flow:v1": 2}, slugs: particle-ai/particle-1:free
- **Rubric:** CANDIDATE config from `migrations/dt_rubric_v6_seed.sql` (pre-seeded into the config cache; live DB rubric not modified)
- **Fixture set:** v6
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 58,767 in / 3,672 out — model calls: 30
- **Cost:** $0.000000 USD (as reported by OpenRouter on usage.cost)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 1.000 | 0.821 | 0.902 | 23 | 0 | 5 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.913 (21/23) |
| Severity exact (triad minor/major/critical) | 0.609 (n=23) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.000 (10 clean items) |
| Clean-passage mean spurious errors/item | 0.000 (0 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.827 | 0.903 | 1.000 | 31 |
| understandability | 0.255 | 0.839 | 0.903 | 31 |
| fidelity | 0.577 | 0.839 | 0.903 | 31 |
| range | 1.000 | 1.000 | 1.000 | 31 |
| naturalness | 0.473 | 0.931 | 1.000 | 29 |
| **overall_band** | 0.362 | 0.839 | 1.000 | 31 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 0.500 (1/2) |
| meaning_inversion precision | 1.000 (1/1) |
| explanation_variant accuracy (word_choice TPs) | 1.000 (1/1; 0 with no predicted variant) |
| variant_basis distribution | default=2, model=0, same_lemma=0, shared_gloss=0 |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 1 | 0 | 0 | 0 | 0 | 0 |
| omission | 0 | 2 | 0 | 0 | 0 | 0 |
| word_choice | 0 | 0 | 1 | 0 | 0 | 0 |
| preposition | 0 | 0 | 0 | 2 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 0 | 1 | 0 | 0 | 0 |

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
    "recall": 0.8214285714285714,
    "f1": 0.9019607843137255,
    "tp": 23,
    "fp": 0,
    "fn": 5
  },
  "subtype_accuracy": {
    "correct": 21,
    "total": 23,
    "accuracy": 0.9130434782608695
  },
  "severity": {
    "exact": 0.6086956521739131,
    "within_one": 1.0,
    "n": 23
  },
  "clean_fp": {
    "item_fp_rate": 0.0,
    "mean_errors": 0.0,
    "total_errors": 0,
    "n": 10
  },
  "bands": {
    "accuracy": {
      "qwk": 0.8268156424581006,
      "exact": 0.9032258064516129,
      "adjacent": 1.0,
      "n": 31
    },
    "understandability": {
      "qwk": 0.25537294563843227,
      "exact": 0.8387096774193549,
      "adjacent": 0.9032258064516129,
      "n": 31
    },
    "fidelity": {
      "qwk": 0.5771715721464465,
      "exact": 0.8387096774193549,
      "adjacent": 0.9032258064516129,
      "n": 31
    },
    "range": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 31
    },
    "naturalness": {
      "qwk": 0.4727272727272728,
      "exact": 0.9310344827586207,
      "adjacent": 1.0,
      "n": 29
    }
  },
  "overall": {
    "qwk": 0.36213991769547316,
    "exact": 0.8387096774193549,
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
          "meaning_inversion": 1,
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
      "tp": 1,
      "n_expected": 2,
      "n_predicted": 1,
      "recall": 0.5,
      "precision": 1.0
    },
    "explanation_variant": {
      "correct": 1,
      "total": 1,
      "pred_missing": 0,
      "accuracy": 1.0,
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
