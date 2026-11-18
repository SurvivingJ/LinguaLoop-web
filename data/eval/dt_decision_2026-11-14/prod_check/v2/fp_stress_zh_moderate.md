# DT Grading Eval — single-call (ZH)

- **Run date:** 2026-11-18
- **L2 / L1:** zh / en
- **Items graded:** 20 (clean 7 / single 10 / multi 3)
- **Grader:** single-call generative grader (`grade_submission(single_call=True)`, ADR-044); fallback flow v1; paths: {"primary": 20}, slugs: particle-ai/particle-1:free
- **Rubric:** CANDIDATE config from `migrations/dt_rubric_v6_seed.sql` (pre-seeded into the config cache; live DB rubric not modified)
- **Fixture set:** v6
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 44,964 in / 2,955 out — model calls: 20
- **Cost:** $0.000000 USD (as reported by OpenRouter on usage.cost)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 0.875 | 0.875 | 0.875 | 14 | 2 | 2 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.786 (11/14) |
| Severity exact (triad minor/major/critical) | 0.929 (n=14) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.143 (7 clean items) |
| Clean-passage mean spurious errors/item | 0.143 (1 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.722 | 0.850 | 1.000 | 20 |
| understandability | 0.933 | 0.950 | 1.000 | 20 |
| fidelity | 0.970 | 0.950 | 1.000 | 20 |
| range | 1.000 | 1.000 | 1.000 | 19 |
| naturalness | 0.000 | 0.944 | 1.000 | 18 |
| **overall_band** | 0.773 | 0.950 | 1.000 | 20 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 1.000 (2/2) |
| meaning_inversion precision | 1.000 (2/2) |
| explanation_variant accuracy (word_choice TPs) | n/a (0/0; 0 with no predicted variant) |
| variant_basis distribution | default=1, model=0, same_lemma=0, shared_gloss=0 |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 2 | 0 | 0 | 0 | 0 | 0 |
| omission | 0 | 1 | 0 | 0 | 0 | 0 |
| word_choice | 0 | 0 | 0 | 0 | 0 | 0 |
| preposition | 0 | 0 | 0 | 0 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 1 | 1 | 0 | 0 | 0 |

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
    "precision": 0.875,
    "recall": 0.875,
    "f1": 0.875,
    "tp": 14,
    "fp": 2,
    "fn": 2
  },
  "subtype_accuracy": {
    "correct": 11,
    "total": 14,
    "accuracy": 0.7857142857142857
  },
  "severity": {
    "exact": 0.9285714285714286,
    "within_one": 1.0,
    "n": 14
  },
  "clean_fp": {
    "item_fp_rate": 0.14285714285714285,
    "mean_errors": 0.14285714285714285,
    "total_errors": 1,
    "n": 7
  },
  "bands": {
    "accuracy": {
      "qwk": 0.7222222222222222,
      "exact": 0.85,
      "adjacent": 1.0,
      "n": 20
    },
    "understandability": {
      "qwk": 0.9333333333333333,
      "exact": 0.95,
      "adjacent": 1.0,
      "n": 20
    },
    "fidelity": {
      "qwk": 0.9700598802395209,
      "exact": 0.95,
      "adjacent": 1.0,
      "n": 20
    },
    "range": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 19
    },
    "naturalness": {
      "qwk": 0.0,
      "exact": 0.9444444444444444,
      "adjacent": 1.0,
      "n": 18
    }
  },
  "overall": {
    "qwk": 0.7727272727272727,
    "exact": 0.95,
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
        "default": 1,
        "model": 0,
        "same_lemma": 0,
        "shared_gloss": 0
      }
    }
  }
}
```
