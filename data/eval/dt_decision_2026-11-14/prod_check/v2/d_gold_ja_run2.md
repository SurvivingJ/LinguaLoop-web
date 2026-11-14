# DT Grading Eval — single-call (JA)

- **Run date:** 2026-11-14
- **L2 / L1:** ja / en
- **Items graded:** 30 (clean 10 / single 15 / multi 5)
- **Grader:** single-call generative grader (`grade_submission(single_call=True)`, ADR-044); fallback flow v1; paths: {"primary": 29}, slugs: openai/gpt-6-luna
- **Rubric:** CANDIDATE config from `migrations/dt_rubric_v6_seed.sql` (pre-seeded into the config cache; live DB rubric not modified)
- **Fixture set:** v6
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 79,498 in / 3,363 out — model calls: 29
- **Cost:** $0.002484 USD (as reported by OpenRouter on usage.cost)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 0.958 | 0.852 | 0.902 | 23 | 1 | 4 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 0.783 (18/23) |
| Severity exact (triad minor/major/critical) | 0.739 (n=23) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.000 (10 clean items) |
| Clean-passage mean spurious errors/item | 0.000 (0 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 0.769 | 0.900 | 1.000 | 30 |
| understandability | 0.758 | 0.900 | 0.933 | 30 |
| fidelity | 0.887 | 0.900 | 0.967 | 30 |
| range | 1.000 | 1.000 | 1.000 | 30 |
| naturalness | 0.000 | 0.957 | 1.000 | 23 |
| **overall_band** | 0.815 | 0.900 | 1.000 | 30 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 1.000 (2/2) |
| meaning_inversion precision | 0.667 (2/3) |
| explanation_variant accuracy (word_choice TPs) | 0.333 (1/3; 0 with no predicted variant) |
| variant_basis distribution | default=4, model=0, same_lemma=0, shared_gloss=0 |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 2 | 0 | 0 | 0 | 0 | 0 |
| omission | 0 | 2 | 0 | 0 | 0 | 0 |
| word_choice | 1 | 0 | 3 | 0 | 0 | 0 |
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
    "precision": 0.9583333333333334,
    "recall": 0.8518518518518519,
    "f1": 0.9019607843137256,
    "tp": 23,
    "fp": 1,
    "fn": 4
  },
  "subtype_accuracy": {
    "correct": 18,
    "total": 23,
    "accuracy": 0.782608695652174
  },
  "severity": {
    "exact": 0.7391304347826086,
    "within_one": 1.0,
    "n": 23
  },
  "clean_fp": {
    "item_fp_rate": 0.0,
    "mean_errors": 0.0,
    "total_errors": 0,
    "n": 10
  },
  "bands": {
    "accuracy": {
      "qwk": 0.7692307692307692,
      "exact": 0.9,
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
      "qwk": 0.8869346733668342,
      "exact": 0.9,
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
      "qwk": 0.0,
      "exact": 0.9565217391304348,
      "adjacent": 1.0,
      "n": 23
    }
  },
  "overall": {
    "qwk": 0.8148148148148148,
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
          "omission": 2,
          "word_choice": 0,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        },
        "word_choice": {
          "meaning_inversion": 1,
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
