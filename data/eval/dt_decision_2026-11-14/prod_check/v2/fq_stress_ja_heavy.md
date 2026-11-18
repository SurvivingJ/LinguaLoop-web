# DT Grading Eval — single-call (JA)

- **Run date:** 2026-11-18
- **L2 / L1:** ja / en
- **Items graded:** 16 (clean 5 / single 10 / multi 1)
- **Grader:** single-call generative grader (`grade_submission(single_call=True)`, ADR-044); fallback flow v1; paths: {"primary": 16}, slugs: particle-ai/particle-1:free
- **Rubric:** CANDIDATE config from `migrations/dt_rubric_v6_seed.sql` (pre-seeded into the config cache; live DB rubric not modified)
- **Fixture set:** v6
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 43,400 in / 3,818 out — model calls: 16
- **Cost:** $0.000000 USD (as reported by OpenRouter on usage.cost)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 1.000 | 0.833 | 0.909 | 10 | 0 | 2 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.800 (8/10) |
| Severity exact (triad minor/major/critical) | 0.700 (n=10) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.000 (5 clean items) |
| Clean-passage mean spurious errors/item | 0.000 (0 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.818 | 0.938 | 1.000 | 16 |
| understandability | 0.670 | 0.938 | 0.938 | 16 |
| fidelity | 0.810 | 0.875 | 0.938 | 16 |
| range | 0.000 | 0.938 | 1.000 | 16 |
| naturalness | 1.000 | 1.000 | 1.000 | 14 |
| **overall_band** | 0.429 | 0.938 | 0.938 | 16 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 1.000 (1/1) |
| meaning_inversion precision | 1.000 (1/1) |
| explanation_variant accuracy (word_choice TPs) | n/a (0/0; 0 with no predicted variant) |
| variant_basis distribution | default=1, model=0, same_lemma=0, shared_gloss=0 |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 1 | 0 | 0 | 0 | 0 | 0 |
| omission | 0 | 1 | 0 | 0 | 0 | 0 |
| word_choice | 0 | 0 | 0 | 0 | 0 | 0 |
| preposition | 0 | 0 | 0 | 0 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 1 | 1 | 0 | 0 | 0 |

## Raw metrics (JSON)

```json
{
  "n_items": 16,
  "kind_counts": {
    "clean": 5,
    "single": 10,
    "multi": 1
  },
  "span": {
    "precision": 1.0,
    "recall": 0.8333333333333334,
    "f1": 0.9090909090909091,
    "tp": 10,
    "fp": 0,
    "fn": 2
  },
  "subtype_accuracy": {
    "correct": 8,
    "total": 10,
    "accuracy": 0.8
  },
  "severity": {
    "exact": 0.7,
    "within_one": 1.0,
    "n": 10
  },
  "clean_fp": {
    "item_fp_rate": 0.0,
    "mean_errors": 0.0,
    "total_errors": 0,
    "n": 5
  },
  "bands": {
    "accuracy": {
      "qwk": 0.8181818181818182,
      "exact": 0.9375,
      "adjacent": 1.0,
      "n": 16
    },
    "understandability": {
      "qwk": 0.6701030927835052,
      "exact": 0.9375,
      "adjacent": 0.9375,
      "n": 16
    },
    "fidelity": {
      "qwk": 0.8095238095238095,
      "exact": 0.875,
      "adjacent": 0.9375,
      "n": 16
    },
    "range": {
      "qwk": 0.0,
      "exact": 0.9375,
      "adjacent": 1.0,
      "n": 16
    },
    "naturalness": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 14
    }
  },
  "overall": {
    "qwk": 0.4285714285714285,
    "exact": 0.9375,
    "adjacent": 0.9375,
    "n": 16
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
      "tp": 1,
      "n_expected": 1,
      "n_predicted": 1,
      "recall": 1.0,
      "precision": 1.0
    },
    "explanation_variant": {
      "correct": 0,
      "total": 0,
      "pred_missing": 0,
      "accuracy": NaN,
      "variant_basis": {
        "default": 1,
        "model": 0,
        "same_lemma": 0,
        "shared_gloss": 0
      }
    }
  }
}
```
