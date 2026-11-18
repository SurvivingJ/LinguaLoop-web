# DT Grading Eval — single-call (ZH)

- **Run date:** 2026-11-18
- **L2 / L1:** zh / en
- **Items graded:** 18 (clean 7 / single 9 / multi 2)
- **Grader:** single-call generative grader (`grade_submission(single_call=True)`, ADR-044); fallback flow v1; paths: {"fallback_flow:v1": 9, "primary": 9}, slugs: baidu/ernie-5.5-flash-preview:free
- **Rubric:** CANDIDATE config from `migrations/dt_rubric_v6_seed.sql` (pre-seeded into the config cache; live DB rubric not modified)
- **Fixture set:** v6
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 39,434 in / 20,769 out — model calls: 18
- **Cost:** $0.000000 USD (as reported by OpenRouter on usage.cost)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 1.000 | 0.231 | 0.375 | 3 | 0 | 10 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 1.000 (3/3) |
| Severity exact (triad minor/major/critical) | 1.000 (n=3) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.000 (7 clean items) |
| Clean-passage mean spurious errors/item | 0.000 (0 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.265 | 0.778 | 1.000 | 18 |
| understandability | 0.640 | 0.944 | 0.944 | 18 |
| fidelity | 0.610 | 0.889 | 0.944 | 18 |
| range | 1.000 | 1.000 | 1.000 | 18 |
| naturalness | 0.000 | 0.944 | 1.000 | 18 |
| **overall_band** | 0.640 | 0.944 | 1.000 | 18 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 0.500 (1/2) |
| meaning_inversion precision | 1.000 (1/1) |
| explanation_variant accuracy (word_choice TPs) | n/a (0/0; 0 with no predicted variant) |
| variant_basis distribution | default=0, model=0, same_lemma=0, shared_gloss=0 |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 1 | 0 | 0 | 0 | 0 | 0 |
| omission | 0 | 0 | 0 | 0 | 0 | 0 |
| word_choice | 0 | 0 | 0 | 0 | 0 | 0 |
| preposition | 0 | 0 | 0 | 0 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 0 | 0 | 0 | 0 | 0 |

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
    "precision": 1.0,
    "recall": 0.23076923076923078,
    "f1": 0.375,
    "tp": 3,
    "fp": 0,
    "fn": 10
  },
  "subtype_accuracy": {
    "correct": 3,
    "total": 3,
    "accuracy": 1.0
  },
  "severity": {
    "exact": 1.0,
    "within_one": 1.0,
    "n": 3
  },
  "clean_fp": {
    "item_fp_rate": 0.0,
    "mean_errors": 0.0,
    "total_errors": 0,
    "n": 7
  },
  "bands": {
    "accuracy": {
      "qwk": 0.26530612244897966,
      "exact": 0.7777777777777778,
      "adjacent": 1.0,
      "n": 18
    },
    "understandability": {
      "qwk": 0.64,
      "exact": 0.9444444444444444,
      "adjacent": 0.9444444444444444,
      "n": 18
    },
    "fidelity": {
      "qwk": 0.6103896103896103,
      "exact": 0.8888888888888888,
      "adjacent": 0.9444444444444444,
      "n": 18
    },
    "range": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 18
    },
    "naturalness": {
      "qwk": 0.0,
      "exact": 0.9444444444444444,
      "adjacent": 1.0,
      "n": 18
    }
  },
  "overall": {
    "qwk": 0.64,
    "exact": 0.9444444444444444,
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
          "meaning_inversion": 1,
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
          "omission": 0,
          "word_choice": 0,
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
      "correct": 0,
      "total": 0,
      "pred_missing": 0,
      "accuracy": NaN,
      "variant_basis": {
        "default": 0,
        "model": 0,
        "same_lemma": 0,
        "shared_gloss": 0
      }
    }
  }
}
```
