# DT Grading Eval — single-call (EN)

- **Run date:** 2026-11-14
- **L2 / L1:** en / zh
- **Items graded:** 31 (clean 10 / single 16 / multi 5)
- **Grader:** single-call generative grader (`grade_submission(single_call=True)`, ADR-044); fallback flow v1; paths: {"primary": 30}, slugs: openai/gpt-6-luna
- **Rubric:** CANDIDATE config from `migrations/dt_rubric_v6_seed.sql` (pre-seeded into the config cache; live DB rubric not modified)
- **Fixture set:** v6
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 61,323 in / 3,147 out — model calls: 30
- **Cost:** $0.002820 USD (as reported by OpenRouter on usage.cost)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 1.000 | 0.964 | 0.982 | 27 | 0 | 1 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.889 (24/27) |
| Severity exact (triad minor/major/critical) | 0.889 (n=27) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.000 (10 clean items) |
| Clean-passage mean spurious errors/item | 0.000 (0 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 1.000 | 1.000 | 1.000 | 31 |
| understandability | 0.794 | 0.935 | 0.968 | 31 |
| fidelity | 0.866 | 0.903 | 0.968 | 31 |
| range | 1.000 | 1.000 | 1.000 | 28 |
| naturalness | -0.054 | 0.885 | 1.000 | 26 |
| **overall_band** | 0.839 | 0.968 | 1.000 | 31 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 1.000 (2/2) |
| meaning_inversion precision | 0.667 (2/3) |
| explanation_variant accuracy (word_choice TPs) | 0.500 (1/2; 0 with no predicted variant) |
| variant_basis distribution | default=3, model=0, same_lemma=0, shared_gloss=0 |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 2 | 0 | 0 | 0 | 0 | 0 |
| omission | 0 | 2 | 0 | 0 | 0 | 0 |
| word_choice | 1 | 0 | 2 | 0 | 0 | 0 |
| preposition | 0 | 0 | 0 | 2 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 0 | 1 | 0 | 0 | 0 |

## Raw metrics (JSON)

```json
{
  "n_items": 31,
  "kind_counts": {
    "clean": 10,
    "single": 16,
    "multi": 5
  },
  "span": {
    "precision": 1.0,
    "recall": 0.9642857142857143,
    "f1": 0.9818181818181818,
    "tp": 27,
    "fp": 0,
    "fn": 1
  },
  "subtype_accuracy": {
    "correct": 24,
    "total": 27,
    "accuracy": 0.8888888888888888
  },
  "severity": {
    "exact": 0.8888888888888888,
    "within_one": 1.0,
    "n": 27
  },
  "clean_fp": {
    "item_fp_rate": 0.0,
    "mean_errors": 0.0,
    "total_errors": 0,
    "n": 10
  },
  "bands": {
    "accuracy": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 31
    },
    "understandability": {
      "qwk": 0.7941567065073041,
      "exact": 0.9354838709677419,
      "adjacent": 0.967741935483871,
      "n": 31
    },
    "fidelity": {
      "qwk": 0.8658008658008658,
      "exact": 0.9032258064516129,
      "adjacent": 0.967741935483871,
      "n": 31
    },
    "range": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 28
    },
    "naturalness": {
      "qwk": -0.054054054054053946,
      "exact": 0.8846153846153846,
      "adjacent": 1.0,
      "n": 26
    }
  },
  "overall": {
    "qwk": 0.8393782383419689,
    "exact": 0.967741935483871,
    "adjacent": 1.0,
    "n": 31
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
          "preposition": 2,
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
      "correct": 1,
      "total": 2,
      "pred_missing": 0,
      "accuracy": 0.5,
      "variant_basis": {
        "default": 3,
        "model": 0,
        "same_lemma": 0,
        "shared_gloss": 0
      }
    }
  }
}
```
