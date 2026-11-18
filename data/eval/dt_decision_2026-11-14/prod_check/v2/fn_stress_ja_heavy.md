# DT Grading Eval — single-call (JA)

- **Run date:** 2026-11-18
- **L2 / L1:** ja / en
- **Items graded:** 16 (clean 5 / single 10 / multi 1)
- **Grader:** single-call generative grader (`grade_submission(single_call=True)`, ADR-044); fallback flow v1; paths: {"primary": 16}, slugs: nvidia/nemotron-3.5-super-vl:free
- **Rubric:** CANDIDATE config from `migrations/dt_rubric_v6_seed.sql` (pre-seeded into the config cache; live DB rubric not modified)
- **Fixture set:** v6
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 42,528 in / 9,143 out — model calls: 16
- **Cost:** $0.000000 USD (as reported by OpenRouter on usage.cost)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 0.126 | 0.917 | 0.222 | 11 | 76 | 1 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.455 (5/11) |
| Severity exact (triad minor/major/critical) | 0.636 (n=11) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.600 (5 clean items) |
| Clean-passage mean spurious errors/item | 3.400 (17 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.525 | 0.625 | 1.000 | 16 |
| understandability | 0.802 | 0.875 | 1.000 | 16 |
| fidelity | 0.346 | 0.375 | 0.750 | 16 |
| range | 0.000 | 0.867 | 1.000 | 15 |
| naturalness | 1.000 | 1.000 | 1.000 | 8 |
| **overall_band** | 0.091 | 0.375 | 1.000 | 16 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 0.000 (0/1) |
| meaning_inversion precision | n/a (0/0) |
| explanation_variant accuracy (word_choice TPs) | n/a (0/0; 0 with no predicted variant) |
| variant_basis distribution | default=47, model=0, same_lemma=4, shared_gloss=0 |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 0 | 0 | 1 | 0 | 0 | 0 |
| omission | 0 | 1 | 1 | 0 | 0 | 0 |
| word_choice | 0 | 0 | 1 | 0 | 0 | 0 |
| preposition | 0 | 0 | 0 | 0 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 0 | 1 | 0 | 0 | 0 |

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
    "precision": 0.12643678160919541,
    "recall": 0.9166666666666666,
    "f1": 0.22222222222222224,
    "tp": 11,
    "fp": 76,
    "fn": 1
  },
  "subtype_accuracy": {
    "correct": 5,
    "total": 11,
    "accuracy": 0.45454545454545453
  },
  "severity": {
    "exact": 0.6363636363636364,
    "within_one": 1.0,
    "n": 11
  },
  "clean_fp": {
    "item_fp_rate": 0.6,
    "mean_errors": 3.4,
    "total_errors": 17,
    "n": 5
  },
  "bands": {
    "accuracy": {
      "qwk": 0.5247524752475248,
      "exact": 0.625,
      "adjacent": 1.0,
      "n": 16
    },
    "understandability": {
      "qwk": 0.8024691358024691,
      "exact": 0.875,
      "adjacent": 1.0,
      "n": 16
    },
    "fidelity": {
      "qwk": 0.34572490706319714,
      "exact": 0.375,
      "adjacent": 0.75,
      "n": 16
    },
    "range": {
      "qwk": 0.0,
      "exact": 0.8666666666666667,
      "adjacent": 1.0,
      "n": 15
    },
    "naturalness": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 8
    }
  },
  "overall": {
    "qwk": 0.09090909090909083,
    "exact": 0.375,
    "adjacent": 1.0,
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
          "meaning_inversion": 0,
          "omission": 0,
          "word_choice": 1,
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
      "n_expected": 1,
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
        "default": 47,
        "model": 0,
        "same_lemma": 4,
        "shared_gloss": 0
      }
    }
  }
}
```
