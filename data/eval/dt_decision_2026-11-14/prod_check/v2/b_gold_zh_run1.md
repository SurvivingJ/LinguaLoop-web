# DT Grading Eval — single-call (ZH)

- **Run date:** 2026-11-14
- **L2 / L1:** zh / en
- **Items graded:** 30 (clean 10 / single 15 / multi 5)
- **Grader:** single-call generative grader (`grade_submission(single_call=True)`, ADR-044); fallback flow v1; paths: {"primary": 28}, slugs: openai/gpt-6-luna
- **Rubric:** CANDIDATE config from `migrations/dt_rubric_v6_seed.sql` (pre-seeded into the config cache; live DB rubric not modified)
- **Fixture set:** v6
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 66,093 in / 3,248 out — model calls: 28
- **Cost:** $0.003158 USD (as reported by OpenRouter on usage.cost)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 0.923 | 0.923 | 0.923 | 24 | 2 | 2 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.750 (18/24) |
| Severity exact (triad minor/major/critical) | 0.708 (n=24) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.100 (10 clean items) |
| Clean-passage mean spurious errors/item | 0.100 (1 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.590 | 0.833 | 1.000 | 30 |
| understandability | 0.737 | 0.933 | 0.967 | 30 |
| fidelity | 0.842 | 0.867 | 0.967 | 30 |
| range | 1.000 | 1.000 | 1.000 | 30 |
| naturalness | 0.118 | 0.600 | 0.967 | 30 |
| **overall_band** | 0.516 | 0.900 | 1.000 | 30 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 1.000 (2/2) |
| meaning_inversion precision | 0.667 (2/3) |
| explanation_variant accuracy (word_choice TPs) | 0.000 (0/2; 0 with no predicted variant) |
| variant_basis distribution | default=5, model=0, same_lemma=0, shared_gloss=0 |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 2 | 0 | 0 | 0 | 0 | 0 |
| omission | 0 | 1 | 0 | 0 | 0 | 0 |
| word_choice | 1 | 0 | 2 | 0 | 0 | 0 |
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
    "precision": 0.9230769230769231,
    "recall": 0.9230769230769231,
    "f1": 0.9230769230769231,
    "tp": 24,
    "fp": 2,
    "fn": 2
  },
  "subtype_accuracy": {
    "correct": 18,
    "total": 24,
    "accuracy": 0.75
  },
  "severity": {
    "exact": 0.7083333333333334,
    "within_one": 1.0,
    "n": 24
  },
  "clean_fp": {
    "item_fp_rate": 0.1,
    "mean_errors": 0.1,
    "total_errors": 1,
    "n": 10
  },
  "bands": {
    "accuracy": {
      "qwk": 0.5901639344262295,
      "exact": 0.8333333333333334,
      "adjacent": 1.0,
      "n": 30
    },
    "understandability": {
      "qwk": 0.736842105263158,
      "exact": 0.9333333333333333,
      "adjacent": 0.9666666666666667,
      "n": 30
    },
    "fidelity": {
      "qwk": 0.8421052631578947,
      "exact": 0.8666666666666667,
      "adjacent": 0.9666666666666667,
      "n": 30
    },
    "range": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 30
    },
    "naturalness": {
      "qwk": 0.11764705882352944,
      "exact": 0.6,
      "adjacent": 0.9666666666666667,
      "n": 30
    }
  },
  "overall": {
    "qwk": 0.5161290322580645,
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
          "meaning_inversion": 1,
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
      "n_predicted": 3,
      "recall": 1.0,
      "precision": 0.6666666666666666
    },
    "explanation_variant": {
      "correct": 0,
      "total": 2,
      "pred_missing": 0,
      "accuracy": 0.0,
      "variant_basis": {
        "default": 5,
        "model": 0,
        "same_lemma": 0,
        "shared_gloss": 0
      }
    }
  }
}
```
