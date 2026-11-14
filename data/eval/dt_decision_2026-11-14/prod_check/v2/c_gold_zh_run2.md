# DT Grading Eval — single-call (ZH)

- **Run date:** 2026-11-14
- **L2 / L1:** zh / en
- **Items graded:** 30 (clean 10 / single 15 / multi 5)
- **Grader:** single-call generative grader (`grade_submission(single_call=True)`, ADR-044); fallback flow v1; paths: {"primary": 28}, slugs: openai/gpt-6-luna
- **Rubric:** CANDIDATE config from `migrations/dt_rubric_v6_seed.sql` (pre-seeded into the config cache; live DB rubric not modified)
- **Fixture set:** v6
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 67,017 in / 3,237 out — model calls: 28
- **Cost:** $0.002296 USD (as reported by OpenRouter on usage.cost)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 0.960 | 0.923 | 0.941 | 24 | 1 | 2 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.833 (20/24) |
| Severity exact (triad minor/major/critical) | 0.667 (n=24) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.000 (10 clean items) |
| Clean-passage mean spurious errors/item | 0.000 (0 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.524 | 0.800 | 1.000 | 30 |
| understandability | 0.936 | 0.967 | 1.000 | 30 |
| fidelity | 0.920 | 0.900 | 1.000 | 30 |
| range | 1.000 | 1.000 | 1.000 | 30 |
| naturalness | 1.000 | 1.000 | 1.000 | 25 |
| **overall_band** | 0.783 | 0.967 | 1.000 | 30 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 1.000 (2/2) |
| meaning_inversion precision | 1.000 (2/2) |
| explanation_variant accuracy (word_choice TPs) | 0.333 (1/3; 0 with no predicted variant) |
| variant_basis distribution | default=4, model=0, same_lemma=0, shared_gloss=0 |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 2 | 0 | 0 | 0 | 0 | 0 |
| omission | 0 | 1 | 0 | 0 | 0 | 0 |
| word_choice | 0 | 0 | 3 | 0 | 0 | 0 |
| preposition | 0 | 0 | 0 | 0 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 2 | 0 | 0 | 0 | 0 |

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
    "precision": 0.96,
    "recall": 0.9230769230769231,
    "f1": 0.9411764705882353,
    "tp": 24,
    "fp": 1,
    "fn": 2
  },
  "subtype_accuracy": {
    "correct": 20,
    "total": 24,
    "accuracy": 0.8333333333333334
  },
  "severity": {
    "exact": 0.6666666666666666,
    "within_one": 1.0,
    "n": 24
  },
  "clean_fp": {
    "item_fp_rate": 0.0,
    "mean_errors": 0.0,
    "total_errors": 0,
    "n": 10
  },
  "bands": {
    "accuracy": {
      "qwk": 0.5238095238095237,
      "exact": 0.8,
      "adjacent": 1.0,
      "n": 30
    },
    "understandability": {
      "qwk": 0.9361702127659575,
      "exact": 0.9666666666666667,
      "adjacent": 1.0,
      "n": 30
    },
    "fidelity": {
      "qwk": 0.9203539823008849,
      "exact": 0.9,
      "adjacent": 1.0,
      "n": 30
    },
    "range": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 30
    },
    "naturalness": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 25
    }
  },
  "overall": {
    "qwk": 0.782608695652174,
    "exact": 0.9666666666666667,
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
          "meaning_inversion": 0,
          "omission": 0,
          "word_choice": 3,
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
      "correct": 1,
      "total": 3,
      "pred_missing": 0,
      "accuracy": 0.3333333333333333,
      "variant_basis": {
        "default": 4,
        "model": 0,
        "same_lemma": 0,
        "shared_gloss": 0
      }
    }
  }
}
```
