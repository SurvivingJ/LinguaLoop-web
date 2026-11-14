# DT Grading Eval — single-call (EN)

- **Run date:** 2026-11-14
- **L2 / L1:** en / zh
- **Items graded:** 19 (clean 7 / single 9 / multi 3)
- **Grader:** single-call generative grader (`grade_submission(single_call=True)`, ADR-044); fallback flow v1; paths: {"primary": 19}, slugs: openai/gpt-6-luna
- **Rubric:** CANDIDATE config from `migrations/dt_rubric_v6_seed.sql` (pre-seeded into the config cache; live DB rubric not modified)
- **Fixture set:** v6
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 41,137 in / 1,948 out — model calls: 19
- **Cost:** $0.001734 USD (as reported by OpenRouter on usage.cost)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 0.929 | 0.867 | 0.897 | 13 | 1 | 2 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.846 (11/13) |
| Severity exact (triad minor/major/critical) | 0.846 (n=13) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.000 (7 clean items) |
| Clean-passage mean spurious errors/item | 0.000 (0 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.888 | 0.947 | 1.000 | 19 |
| understandability | 0.730 | 0.842 | 0.947 | 19 |
| fidelity | 0.746 | 0.895 | 0.947 | 19 |
| range | 1.000 | 1.000 | 1.000 | 18 |
| naturalness | -0.067 | 0.875 | 1.000 | 16 |
| **overall_band** | 0.604 | 0.895 | 1.000 | 19 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 1.000 (2/2) |
| meaning_inversion precision | 0.667 (2/3) |
| explanation_variant accuracy (word_choice TPs) | n/a (0/0; 0 with no predicted variant) |
| variant_basis distribution | default=1, model=0, same_lemma=0, shared_gloss=0 |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 2 | 0 | 0 | 0 | 0 | 0 |
| omission | 0 | 0 | 0 | 0 | 0 | 1 |
| word_choice | 0 | 0 | 0 | 0 | 0 | 0 |
| preposition | 0 | 0 | 0 | 1 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 0 | 1 | 0 | 0 | 0 |

## Raw metrics (JSON)

```json
{
  "n_items": 19,
  "kind_counts": {
    "clean": 7,
    "single": 9,
    "multi": 3
  },
  "span": {
    "precision": 0.9285714285714286,
    "recall": 0.8666666666666667,
    "f1": 0.896551724137931,
    "tp": 13,
    "fp": 1,
    "fn": 2
  },
  "subtype_accuracy": {
    "correct": 11,
    "total": 13,
    "accuracy": 0.8461538461538461
  },
  "severity": {
    "exact": 0.8461538461538461,
    "within_one": 1.0,
    "n": 13
  },
  "clean_fp": {
    "item_fp_rate": 0.0,
    "mean_errors": 0.0,
    "total_errors": 0,
    "n": 7
  },
  "bands": {
    "accuracy": {
      "qwk": 0.8875739644970414,
      "exact": 0.9473684210526315,
      "adjacent": 1.0,
      "n": 19
    },
    "understandability": {
      "qwk": 0.7298578199052133,
      "exact": 0.8421052631578947,
      "adjacent": 0.9473684210526315,
      "n": 19
    },
    "fidelity": {
      "qwk": 0.7459893048128342,
      "exact": 0.8947368421052632,
      "adjacent": 0.9473684210526315,
      "n": 19
    },
    "range": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 18
    },
    "naturalness": {
      "qwk": -0.06666666666666665,
      "exact": 0.875,
      "adjacent": 1.0,
      "n": 16
    }
  },
  "overall": {
    "qwk": 0.6041666666666667,
    "exact": 0.8947368421052632,
    "adjacent": 1.0,
    "n": 19
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
          "omission": 0,
          "word_choice": 0,
          "preposition": 0,
          "contradiction": 0,
          "other": 1
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
      "n_predicted": 3,
      "recall": 1.0,
      "precision": 0.6666666666666666
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
