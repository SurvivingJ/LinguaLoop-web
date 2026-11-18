# DT Grading Eval — single-call (JA)

- **Run date:** 2026-11-18
- **L2 / L1:** ja / en
- **Items graded:** 20 (clean 7 / single 10 / multi 3)
- **Grader:** single-call generative grader (`grade_submission(single_call=True)`, ADR-044); fallback flow v1; paths: {"primary": 20}, slugs: nvidia/nemotron-3.5-super-vl:free
- **Rubric:** CANDIDATE config from `migrations/dt_rubric_v6_seed.sql` (pre-seeded into the config cache; live DB rubric not modified)
- **Fixture set:** v6
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 52,533 in / 7,053 out — model calls: 20
- **Cost:** $0.000000 USD (as reported by OpenRouter on usage.cost)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 0.224 | 0.765 | 0.347 | 13 | 45 | 4 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.615 (8/13) |
| Severity exact (triad minor/major/critical) | 0.692 (n=13) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.429 (7 clean items) |
| Clean-passage mean spurious errors/item | 2.143 (15 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.700 | 0.850 | 1.000 | 20 |
| understandability | 0.813 | 0.900 | 0.950 | 20 |
| fidelity | 0.632 | 0.600 | 0.900 | 20 |
| range | 1.000 | 1.000 | 1.000 | 16 |
| naturalness | 0.000 | 0.900 | 1.000 | 10 |
| **overall_band** | 0.595 | 0.850 | 0.950 | 20 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 0.000 (0/2) |
| meaning_inversion precision | n/a (0/0) |
| explanation_variant accuracy (word_choice TPs) | n/a (0/0; 0 with no predicted variant) |
| variant_basis distribution | default=29, model=0, same_lemma=3, shared_gloss=1 |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 0 | 0 | 2 | 0 | 0 | 0 |
| omission | 0 | 1 | 1 | 0 | 0 | 0 |
| word_choice | 0 | 0 | 2 | 0 | 0 | 0 |
| preposition | 0 | 0 | 0 | 0 | 0 | 0 |
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
    "precision": 0.22413793103448276,
    "recall": 0.7647058823529411,
    "f1": 0.3466666666666667,
    "tp": 13,
    "fp": 45,
    "fn": 4
  },
  "subtype_accuracy": {
    "correct": 8,
    "total": 13,
    "accuracy": 0.6153846153846154
  },
  "severity": {
    "exact": 0.6923076923076923,
    "within_one": 1.0,
    "n": 13
  },
  "clean_fp": {
    "item_fp_rate": 0.42857142857142855,
    "mean_errors": 2.142857142857143,
    "total_errors": 15,
    "n": 7
  },
  "bands": {
    "accuracy": {
      "qwk": 0.7,
      "exact": 0.85,
      "adjacent": 1.0,
      "n": 20
    },
    "understandability": {
      "qwk": 0.8134328358208955,
      "exact": 0.9,
      "adjacent": 0.95,
      "n": 20
    },
    "fidelity": {
      "qwk": 0.631578947368421,
      "exact": 0.6,
      "adjacent": 0.9,
      "n": 20
    },
    "range": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 16
    },
    "naturalness": {
      "qwk": 0.0,
      "exact": 0.9,
      "adjacent": 1.0,
      "n": 10
    }
  },
  "overall": {
    "qwk": 0.5945945945945946,
    "exact": 0.85,
    "adjacent": 0.95,
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
          "meaning_inversion": 0,
          "omission": 0,
          "word_choice": 2,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        },
        "omission": {
          "meaning_inversion": 0,
          "omission": 1,
          "word_choice": 1,
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
      "tp": 0,
      "n_expected": 2,
      "n_predicted": 0,
      "recall": 0.0,
      "precision": NaN
    },
    "explanation_variant": {
      "correct": 0,
      "total": 0,
      "pred_missing": 0,
      "accuracy": NaN,
      "variant_basis": {
        "default": 29,
        "model": 0,
        "same_lemma": 3,
        "shared_gloss": 1
      }
    }
  }
}
```
