# DT Grading Eval — single-call (JA)

- **Run date:** 2026-11-14
- **L2 / L1:** ja / en
- **Items graded:** 30 (clean 10 / single 15 / multi 5)
- **Grader:** single-call generative grader (`grade_submission(single_call=True)`, ADR-044); fallback flow v1; paths: {"primary": 29}, slugs: openai/gpt-6-luna
- **Rubric:** CANDIDATE config from `migrations/dt_rubric_v6_seed.sql` (pre-seeded into the config cache; live DB rubric not modified)
- **Fixture set:** v6
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 78,019 in / 3,545 out — model calls: 29
- **Cost:** $0.003537 USD (as reported by OpenRouter on usage.cost)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 0.923 | 0.889 | 0.906 | 24 | 2 | 3 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.792 (19/24) |
| Severity exact (triad minor/major/critical) | 0.792 (n=24) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.000 (10 clean items) |
| Clean-passage mean spurious errors/item | 0.000 (0 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.841 | 0.933 | 1.000 | 30 |
| understandability | 0.758 | 0.900 | 0.933 | 30 |
| fidelity | 0.906 | 0.933 | 0.967 | 30 |
| range | 1.000 | 1.000 | 1.000 | 30 |
| naturalness | 1.000 | 1.000 | 1.000 | 26 |
| **overall_band** | 0.881 | 0.933 | 1.000 | 30 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 1.000 (2/2) |
| meaning_inversion precision | 0.500 (2/4) |
| explanation_variant accuracy (word_choice TPs) | 0.250 (1/4; 0 with no predicted variant) |
| variant_basis distribution | default=5, model=0, same_lemma=0, shared_gloss=0 |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 2 | 0 | 0 | 0 | 0 | 0 |
| omission | 0 | 2 | 0 | 0 | 0 | 0 |
| word_choice | 2 | 0 | 4 | 0 | 0 | 0 |
| preposition | 0 | 0 | 0 | 0 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 0 | 1 | 0 | 0 | 0 |

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
    "recall": 0.8888888888888888,
    "f1": 0.9056603773584906,
    "tp": 24,
    "fp": 2,
    "fn": 3
  },
  "subtype_accuracy": {
    "correct": 19,
    "total": 24,
    "accuracy": 0.7916666666666666
  },
  "severity": {
    "exact": 0.7916666666666666,
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
      "qwk": 0.8412698412698413,
      "exact": 0.9333333333333333,
      "adjacent": 1.0,
      "n": 30
    },
    "understandability": {
      "qwk": 0.7576301615798923,
      "exact": 0.9,
      "adjacent": 0.9333333333333333,
      "n": 30
    },
    "fidelity": {
      "qwk": 0.9058971141781681,
      "exact": 0.9333333333333333,
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
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 26
    }
  },
  "overall": {
    "qwk": 0.8809523809523809,
    "exact": 0.9333333333333333,
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
          "omission": 2,
          "word_choice": 0,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        },
        "word_choice": {
          "meaning_inversion": 2,
          "omission": 0,
          "word_choice": 4,
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
      "tp": 2,
      "n_expected": 2,
      "n_predicted": 4,
      "recall": 1.0,
      "precision": 0.5
    },
    "explanation_variant": {
      "correct": 1,
      "total": 4,
      "pred_missing": 0,
      "accuracy": 0.25,
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
