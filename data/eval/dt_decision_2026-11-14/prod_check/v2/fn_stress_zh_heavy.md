# DT Grading Eval — single-call (ZH)

- **Run date:** 2026-11-18
- **L2 / L1:** zh / en
- **Items graded:** 18 (clean 7 / single 9 / multi 2)
- **Grader:** single-call generative grader (`grade_submission(single_call=True)`, ADR-044); fallback flow v1; paths: {"primary": 18}, slugs: nvidia/nemotron-3.5-super-vl:free
- **Rubric:** CANDIDATE config from `migrations/dt_rubric_v6_seed.sql` (pre-seeded into the config cache; live DB rubric not modified)
- **Fixture set:** v6
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 45,250 in / 5,111 out — model calls: 18
- **Cost:** $0.000000 USD (as reported by OpenRouter on usage.cost)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 0.257 | 0.692 | 0.375 | 9 | 26 | 4 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.778 (7/9) |
| Severity exact (triad minor/major/critical) | 0.778 (n=9) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.143 (7 clean items) |
| Clean-passage mean spurious errors/item | 0.714 (5 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.368 | 0.778 | 1.000 | 18 |
| understandability | 0.720 | 0.889 | 0.944 | 18 |
| fidelity | 0.644 | 0.778 | 0.889 | 18 |
| range | 0.000 | 0.941 | 1.000 | 17 |
| naturalness | -0.105 | 0.786 | 1.000 | 14 |
| **overall_band** | 0.609 | 0.889 | 1.000 | 18 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 1.000 (2/2) |
| meaning_inversion precision | 1.000 (2/2) |
| explanation_variant accuracy (word_choice TPs) | n/a (0/0; 0 with no predicted variant) |
| variant_basis distribution | default=16, model=0, same_lemma=0, shared_gloss=0 |
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
| other | 0 | 1 | 0 | 0 | 0 | 0 |

## Raw metrics (JSON)

```json
{
  "n_items": 18,
  "kind_counts": {
    "clean": 7,
    "single": 9,
    "multi": 2
  },
  "span": {
    "precision": 0.2571428571428571,
    "recall": 0.6923076923076923,
    "f1": 0.37499999999999994,
    "tp": 9,
    "fp": 26,
    "fn": 4
  },
  "subtype_accuracy": {
    "correct": 7,
    "total": 9,
    "accuracy": 0.7777777777777778
  },
  "severity": {
    "exact": 0.7777777777777778,
    "within_one": 1.0,
    "n": 9
  },
  "clean_fp": {
    "item_fp_rate": 0.14285714285714285,
    "mean_errors": 0.7142857142857143,
    "total_errors": 5,
    "n": 7
  },
  "bands": {
    "accuracy": {
      "qwk": 0.368421052631579,
      "exact": 0.7777777777777778,
      "adjacent": 1.0,
      "n": 18
    },
    "understandability": {
      "qwk": 0.7204968944099379,
      "exact": 0.8888888888888888,
      "adjacent": 0.9444444444444444,
      "n": 18
    },
    "fidelity": {
      "qwk": 0.6437994722955146,
      "exact": 0.7777777777777778,
      "adjacent": 0.8888888888888888,
      "n": 18
    },
    "range": {
      "qwk": 0.0,
      "exact": 0.9411764705882353,
      "adjacent": 1.0,
      "n": 17
    },
    "naturalness": {
      "qwk": -0.10526315789473695,
      "exact": 0.7857142857142857,
      "adjacent": 1.0,
      "n": 14
    }
  },
  "overall": {
    "qwk": 0.6086956521739131,
    "exact": 0.8888888888888888,
    "adjacent": 1.0,
    "n": 18
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
          "word_choice": 0,
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
        "default": 16,
        "model": 0,
        "same_lemma": 0,
        "shared_gloss": 0
      }
    }
  }
}
```
